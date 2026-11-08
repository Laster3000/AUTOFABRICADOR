# coding: utf-8
"""Project-local persistent supervisor with queue, STOP, and PID+birth readback.

Runs only exact project CLI actions; no model-supplied shell. No global service,
autostart/registry or elevated privileges. STOP is recorded immediately and
takes effect at the first safe action boundary; an in-flight model request can
complete before the stop is acknowledged, never replay UNKNOWN or SUCCEEDED.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from . import engine,mission,multilang,direct_agent,repo_factory,native_cycle,factory_pipeline
from .storage import event,load,sha_file,sha_bytes,transition,utc,write_json,verify_journal

def directory(root):
    root=engine.init(root)
    p=root/"supervisor"
    (p/"queue").mkdir(parents=True,exist_ok=True)
    (p/"history").mkdir(exist_ok=True)
    (p/"logs").mkdir(exist_ok=True)
    c=p/"control.json"
    if not c.exists():write_json(c,{"schema":1,"command":"STOP","atUtc":utc()},new=True)
    if not (p/"journal.jsonl").exists():
        event(p/"journal.jsonl","SUPERVISOR_INITIALIZED",{"root":str(root)})
    return p

def process_born(pid):
    """Windows process creation FILETIME, not merely reuse-prone PID."""
    if os.name!="nt" or not isinstance(pid,int) or pid<=0:return None
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.OpenProcess.restype=wintypes.HANDLE
    k.GetProcessTimes.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.FILETIME),
         ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),
         ctypes.POINTER(wintypes.FILETIME)]
    k.GetProcessTimes.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    h=k.OpenProcess(0x1000,False,pid) # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:return None
    try:
        born=wintypes.FILETIME()
        exit=wintypes.FILETIME(); kernel=wintypes.FILETIME(); user=wintypes.FILETIME()
        if not k.GetProcessTimes(h,ctypes.byref(born),ctypes.byref(exit),
                                 ctypes.byref(kernel),ctypes.byref(user)):return None
        return (born.dwHighDateTime<<32)|born.dwLowDateTime
    finally:
        k.CloseHandle(h)

def status(root):
    p=directory(root)
    lease=p/"lease.json"
    record=load(lease) if lease.is_file() else None
    born=process_born(record["pid"]) if record and "pid" in record else None
    live=bool(record and record.get("status")=="RUNNING" and born is not None
              and born==record.get("processBornFiletime"))
    verify_journal(p/"journal.jsonl")
    return {"status":"RUNNING" if live else
            ("UNKNOWN_LEASE_STALE_RECONCILE" if record and record.get("status")=="RUNNING" else "STOPPED"),
            "lease":record,"control":load(p/"control.json"),
            "processIdentityBirthVerified":live,
            "pendingQueue":sum(1 for f in (p/"queue").glob("SQ-*.json") if load(f).get("status")=="PENDING")}

def _control(p,mode):
    if mode not in ("RUN","STOP"):raise ValueError("SUPERVISOR_CONTROL_BAD")
    file=p/"control.json"
    before=load(file)
    if before.get("command")==mode:return before
    current={"schema":1,"command":mode,"atUtc":utc(),"previousSha":sha_file(file)}
    transition(file,current,p/"history")
    event(p/"journal.jsonl","CONTROL",{"command":mode,"controlSha":sha_file(file)})
    return current

def stop(root):
    p=directory(root)
    _control(p,"STOP")
    info=status(root)
    # STOP_REQUESTED is not STOPPED unless the verified worker has exited.
    return {"status":"STOP_REQUESTED" if info["status"]=="RUNNING" else info["status"],
            "control":info["control"],"lease":info["lease"]}

def start(root):
    root=engine.init(root);p=directory(root)
    prior=status(root)
    if prior["status"]=="RUNNING":
        return {"status":"ALREADY_RUNNING_NO_DUPLICATE","lease":prior["lease"]}
    if prior["status"]!="STOPPED":
        raise RuntimeError("STALE_SUPERVISOR_LEASE_RECONCILE_BEFORE_RESTART")
    lease=p/"lease.json"
    if lease.is_file() and load(lease).get("status") not in ("STOPPED","STOPPED_RECONCILED"):
        raise RuntimeError("SUPERVISOR_LAST_LEASE_NOT_STOPPED")
    _control(p,"RUN")
    code=root/"autofabricador.py"
    if not code.is_file():raise RuntimeError("SUPERVISOR_CLI_NOT_FOUND")
    logfile=p/"logs"/("worker-"+uuid.uuid4().hex[:12]+".log")
    with logfile.open("xb") as out:
        flags=(getattr(subprocess,"DETACHED_PROCESS",0)|
               getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))
        proc=subprocess.Popen([sys.executable,"-B",str(code),"supervisor-worker"],
                              cwd=str(root),stdin=subprocess.DEVNULL,
                              stdout=out,stderr=subprocess.STDOUT,
                              creationflags=flags,close_fds=True,
                              env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1",
                                   "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"})
    event(p/"journal.jsonl","WORKER_SPAWN_INTENT",
          {"pid":proc.pid,"cliSha":sha_file(code),"log":str(logfile)})
    for _ in range(48):
        time.sleep(0.20)
        snapshot=status(root)
        if snapshot["status"]=="RUNNING" and snapshot["lease"]["pid"]==proc.pid:
            return {"status":"RUNNING_VERIFIED","lease":snapshot["lease"]}
        if proc.poll() is not None:break
    return {"status":"UNKNOWN_WORKER_START_RECONCILE",
            "pid":proc.pid,"processExit":proc.poll()}

def enqueue(root,kind,ref=None,editor=None):
    root=engine.init(root);p=directory(root)
    if kind=="mission":
        if not ref or not re.fullmatch(r"AM-[a-f0-9]{16}",ref):
            raise ValueError("SUPERVISOR_MISSION_REF_INVALID")
        original=mission.summary(root,ref)
        if original["state"]["status"] not in ("PENDING","STOPPED","READY","PASS"):
            raise RuntimeError("MISSION_STATE_NOT_SAFE_FOR_QUEUE")
    elif kind=="language":
        if editor not in ("codex","opencode"):
            raise ValueError("LANG_SUPERVISOR_TOOL_NOT_ALLOWED")
        original=multilang.summary(root,ref)
        if original["state"]["status"] not in ("PENDING","STOPPED","PASS"):
            raise RuntimeError("LANG_JOB_STATE_NOT_SAFE_FOR_QUEUE")
    elif kind=="direct":
        if editor is not None:
            raise ValueError("DIRECT_NO_NATIVE_EDITOR_ALLOWED")
        original=direct_agent.status(root,ref)
        if original["status"]!="PENDING" or original["modelIntentWritten"]:
            raise RuntimeError("DIRECT_SUPERVISOR_REQUIRES_UNUSED_PENDING_JOB")
    elif kind=="repo":
        if editor is not None:
            raise ValueError("REPO_SUPERVISOR_DISALLOWS_NATIVE_EDITOR")
        original=repo_factory.status(root,ref)
        if original["status"]!="PENDING" or original["attemptsStarted"]:
            raise RuntimeError("REPO_SUPERVISOR_REQUIRES_ORIGINAL_UNUSED_JOB")
    elif kind=="factory":
        if editor is not None:raise ValueError("FACTORY_NO_NATIVE_EDITOR")
        current=factory_pipeline.status(root,ref)
        if current["status"]!="PENDING" or current["control"]!="RUN":
            raise RuntimeError("FACTORY_SUPERVISOR_REQUIRES_PENDING_ORIGINAL_INTENT")
    elif kind=="gui":
        from . import gui_pipeline
        if editor is not None:raise ValueError("GUI_NO_NATIVE_EDITOR")
        check=gui_pipeline.status(root,ref)
        if check["status"]!="PENDING" or check["modelCallsRecorded"]!=0:
            raise RuntimeError("GUI_ORIGINAL_UNUSED_INTENT_REQUIRED")
    elif kind=="desktop":
        from . import desktop_workflow
        if editor is not None:raise ValueError("DESKTOP_NO_NATIVE_EDITOR")
        current=desktop_workflow.status(root,ref)
        if current["status"]!="PENDING" or current["modelAttemptsStarted"]!=0:
            raise RuntimeError("DESKTOP_REQUIRES_FROZEN_UNUSED_ORIGINAL_INTENT")
    elif kind=="portfolio":
        from . import portfolio_workflow
        if editor is not None:raise ValueError("PORTFOLIO_NO_NATIVE_EDITOR")
        current=portfolio_workflow.status(root,ref)
        if current["status"]!="PENDING" or current["modelAttemptsStarted"]!=0:
            raise RuntimeError("PORTFOLIO_REQUIRES_FROZEN_UNUSED_ORIGINAL_JOB")
    elif kind=="native":
        if editor is not None:raise ValueError("NATIVE_SUPERVISOR_NO_EDITOR")
        original=native_cycle.status(root,ref)
        if original["status"]!="PENDING":
            raise RuntimeError("NATIVE_SUPERVISOR_REQUIRES_UNSTARTED_CYCLE")
    elif kind=="selfcheck":
        # An optional, safe run label permits separate documented E2E
        # fixtures without mutating an earlier immutable STOP receipt.
        if editor is not None or (ref is not None and not re.fullmatch(r"R[0-9]{3}-[A-Z0-9-]{2,48}",ref)):
            raise ValueError("SELFCHECK_NO_ARGS_ALLOWED")
    else:
        raise ValueError("SUPERVISOR_TASK_TYPE_NOT_SUPPORTED")
    for path in (p/"queue").glob("SQ-*.json"):
        existing=load(path)
        if existing.get("kind")==kind and existing.get("ref")==ref and existing.get("editor")==editor:
            return {"status":"ALREADY_QUEUED_OR_RECORDED_NO_REPLAY",
                    "queueId":existing["queueId"],"state":existing["status"]}
    identifier="SQ-"+uuid.uuid4().hex[:16]
    task={"schema":1,"queueId":identifier,"kind":kind,"ref":ref,"editor":editor,
          "createdUtc":utc(),"status":"PENDING",
          "cliSha256":sha_file(root/"autofabricador.py")}
    file=p/"queue"/(identifier+".json")
    write_json(file,task,new=True)
    event(p/"journal.jsonl","QUEUE_ACCEPTED",
          {"queueId":identifier,"taskSha":sha_file(file),"kind":kind,"ref":ref})
    return {"queueId":identifier,"status":"PENDING"}

def _task_update(p,file,data):
    old=load(file)
    new={**old,**data,"updatedUtc":utc(),"previousSha":sha_file(file)}
    transition(file,new,p/"history")
    event(p/"journal.jsonl","TASK_STATE",
          {"queueId":new["queueId"],"status":new["status"],
           "receiptSha":sha_file(file)})

def _run_one(root,p,file):
    job=load(file)
    if job["status"]!="PENDING":return
    if load(p/"control.json")["command"]!="RUN":return
    _task_update(p,file,{"status":"RUNNING","startedUtc":utc()})
    identifier=job["queueId"]
    if job["kind"]=="selfcheck":
        # Deterministic first-party fixture to prove a live STOP, no AI model.
        for _ in range(48):
            if load(p/"control.json")["command"]=="STOP":
                _task_update(p,file,{"status":"STOPPED","result":"SAFE_CANCEL_NO_SIDE_EFFECT",
                                     "modelCalls":0})
                return
            time.sleep(.20)
        _task_update(p,file,{"status":"SUCCEEDED","result":"SELFCHECK_ONLY_NO_AI", "modelCalls":0})
        return
    command=[sys.executable,"-B",str(root/"autofabricador.py")]
    if job["kind"]=="mission":
        command+=["mission-run",job["ref"]]
    elif job["kind"]=="language":
        command+=["language-run",job["ref"],job["editor"]]
    elif job["kind"]=="direct":
        command+=["direct-run",job["ref"]]
    elif job["kind"]=="repo":
        command+=["repo-run",job["ref"]]
    elif job["kind"]=="native":
        command+=["native-cycle-run",job["ref"]]
    elif job["kind"]=="factory":
        command+=["factory-run",job["ref"]]
    elif job["kind"]=="gui":
        command+=["gui-run",job["ref"]]
    elif job["kind"]=="desktop":
        command+=["desktop-run",job["ref"]]
    elif job["kind"]=="portfolio":
        command+=["portfolio-run",job["ref"]]
    logfile=p/"logs"/(identifier+".log")
    if logfile.exists():
        # Original log is immutable. A proven zero-effect resume requires
        # a NEW log name with the SAME original SQ task identifier.
        proof=job.get("resumeProofSha")
        if job["kind"]=="native":
            proofpath=native_cycle.folder(root,job["ref"])/"resume-proof.json"
        elif job["kind"]=="gui":
            from . import gui_pipeline
            proofpath=gui_pipeline.folder(root,job["ref"])/"resume-proof.json"
        else:proofpath=None
        if (job["kind"] not in ("native","gui") or not isinstance(proof,str)
            or not re.fullmatch(r"[a-f0-9]{64}",proof)
            or not proofpath.is_file() or sha_file(proofpath)!=proof):
            raise RuntimeError("ORIGINAL_SUPERVISOR_LOG_EXISTS_NO_PROVEN_RESTART")
        logfile=p/"logs"/(identifier+"-resume-"+proof[:12]+".log")
        if logfile.exists():
            raise RuntimeError("NATIVE_RESTART_LOG_ALREADY_EXISTS_NO_REPLAY")
    with logfile.open("xb") as log:
        proc=subprocess.Popen(command,cwd=str(root),stdin=subprocess.DEVNULL,
                              stdout=log,stderr=subprocess.STDOUT,
                              close_fds=True,env={**os.environ,
                                "PYTHONDONTWRITEBYTECODE":"1",
                                "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"})
        event(p/"journal.jsonl","CHILD_STARTED",{"queueId":identifier,"pid":proc.pid,
              "processBornFiletime":process_born(proc.pid)})
        requested=False
        while proc.poll() is None:
            if load(p/"control.json")["command"]=="STOP" and not requested:
                requested=True
                if job["kind"]=="mission":
                    mission.control(root,job["ref"],"STOP")
                elif job["kind"]=="direct":
                    direct_agent.control(root,job["ref"],"STOP")
                elif job["kind"]=="repo":
                    repo_factory.stop(root,job["ref"])
                elif job["kind"]=="native":
                    native_cycle.stop(root,job["ref"])
                elif job["kind"]=="factory":
                    factory_pipeline.stop(root,job["ref"])
                elif job["kind"]=="gui":
                    from . import gui_pipeline
                    gui_pipeline.control(root,job["ref"],"STOP")
                elif job["kind"]=="desktop":
                    from . import desktop_workflow
                    desktop_workflow.control(root,job["ref"],"STOP")
                elif job["kind"]=="portfolio":
                    from . import portfolio_workflow
                    portfolio_workflow.control(root,job["ref"],"STOP")
                else:
                    multilang.control(root,job["ref"],"STOP")
                event(p/"journal.jsonl","STOP_PROPAGATED",
                      {"queueId":identifier,"pid":proc.pid,
                       "mode":"first safe stage boundary, do not kill untrusted unknown process"})
            time.sleep(.25)
        rc=proc.returncode
    if job["kind"]=="mission":
        original=mission.summary(root,job["ref"])
        succeeded=original["state"]["status"]=="PASS" and rc==0
        actual=original["state"]["status"]
    elif job["kind"]=="direct":
        original=direct_agent.status(root,job["ref"])
        succeeded=original["status"]=="PASS" and rc==0
        actual=original["status"]
    elif job["kind"]=="repo":
        original=repo_factory.status(root,job["ref"])
        succeeded=original["status"]=="PASS" and rc==0
        actual=original["status"]
    elif job["kind"]=="native":
        original=native_cycle.status(root,job["ref"])
        succeeded=original["status"]==native_cycle.OK and rc==0
        actual=original["status"]
    elif job["kind"]=="factory":
        original=factory_pipeline.status(root,job["ref"])
        succeeded=(original["status"] in (factory_pipeline.SUCCESS,
                                factory_pipeline.SUCCESS_BROWSER) and
                   original["resultReceiptSha"] is not None and rc==0)
        actual=original["status"]
    elif job["kind"]=="gui":
        from . import gui_pipeline
        original=gui_pipeline.status(root,job["ref"])
        passed=gui_pipeline.verify(root,job["ref"])
        succeeded=(passed.get("verified") is True and rc==0)
        actual=original["status"]
    elif job["kind"]=="desktop":
        from . import desktop_workflow
        original=desktop_workflow.status(root,job["ref"])
        succeeded=(original["status"]=="PASS_TRUSTED_APP_OWNER_QA_AND_LOCAL_USER_INSTALL"
                   and original.get("originalReceiptSha") is not None and rc==0)
        actual=original["status"]
    elif job["kind"]=="portfolio":
        from . import portfolio_workflow
        original=portfolio_workflow.status(root,job["ref"])
        succeeded=(original["status"]==portfolio_workflow.SUCCESS
                   and original.get("originalResultSHA") is not None and rc==0)
        actual=original["status"]
    else:
        original=multilang.summary(root,job["ref"])
        succeeded=original["state"]["status"]=="PASS" and rc==0
        actual=original["state"]["status"]
    _task_update(p,file,{"status":"SUCCEEDED" if succeeded else
                       ("CANCELLED_VERIFIED" if actual=="CANCELLED_VERIFIED" else
                        ("STOPPED" if actual in ("STOPPED","STOPPED_SAFE_BOUNDARY","STOPPED_PRE_INTENT") else "UNKNOWN")),
                       "childExitCode":rc,"originalStatus":actual,
                       "stopRequestedDuringChild":requested,
                       "childLogSha256":sha_file(logfile),
                       "finishedUtc":utc()})

def worker(root):
    root=engine.init(root);p=directory(root)
    previous=p/"lease.json"
    if previous.exists() and load(previous).get("status")=="RUNNING":
        raise RuntimeError("SUPERVISOR_RUNNING_LEASE_CONFLICT")
    identity=process_born(os.getpid())
    if identity is None:raise RuntimeError("OWN_PROCESS_CREATION_IDENTITY_UNAVAILABLE")
    lease={"schema":1,"pid":os.getpid(),"processBornFiletime":identity,
           "exe":sys.executable,"exeSha256":sha_file(Path(sys.executable)),
           "cliSha256":sha_file(root/"autofabricador.py"),
           "status":"RUNNING","atUtc":utc()}
    if previous.exists():transition(previous,lease,p/"history")
    else:write_json(previous,lease,new=True)
    event(p/"journal.jsonl","WORKER_STARTED",
          {"pid":os.getpid(),"born":identity,"exeSha":lease["exeSha256"]})
    try:
        # First-party observer only: prove a future REAL Windows reboot,
        # never schedule, run, resume or replay an existing job.
        from . import logon_observer
        proof=logon_observer.begin(root,lease)
        event(p/"journal.jsonl","ORIGINAL_LOGON_READBACK_ARMED",
              {"result":proof["status"],"pid":os.getpid()})
    except Exception as observer_error:
        # Audit failure must not prevent original persistent agent work.
        event(p/"journal.jsonl","ORIGINAL_LOGON_READBACK_SETUP_FAILED",
              {"errorType":type(observer_error).__name__,"pid":os.getpid()})
    try:
        # Process remains live until STOP; no legacy jobs auto-imported.
        while load(p/"control.json")["command"]=="RUN":
            pending=sorted((path for path in (p/"queue").glob("SQ-*.json")
                             if load(path)["status"]=="PENDING"),
                            key=lambda path:path.name)
            if pending:
                try:_run_one(root,p,pending[0])
                except Exception as error:
                    path=pending[0]
                    _task_update(p,path,{"status":"UNKNOWN",
                      "errorType":type(error).__name__,"detail":str(error)[:300],
                      "nextAction":"reconcile live child and original receipt"})
            else:
                time.sleep(.35)
    finally:
        old=load(previous)
        closed={**old,"status":"STOPPED","atUtc":utc(),
                "previousSha":sha_file(previous)}
        transition(previous,closed,p/"history")
        event(p/"journal.jsonl","WORKER_STOPPED",
              {"pid":os.getpid(),"leaseSha":sha_file(previous)})
    return {"status":"STOPPED","pid":os.getpid()}


def resume_task(root,queue_id):
    """Resume *only* a STOPPED, provably non-executed task, under same SQ id."""
    root=engine.init(root)
    p=directory(root)
    if not isinstance(queue_id,str) or not re.fullmatch(r"SQ-[a-f0-9]{16}",queue_id):
        raise ValueError("SUPERVISOR_QUEUE_ID_INVALID")
    if status(root)["status"]!="STOPPED":
        raise RuntimeError("SUPERVISOR_MUST_BE_STOPPED_BEFORE_RESUME")
    file=p/"queue"/(queue_id+".json")
    if not file.is_file():raise FileNotFoundError("SUPERVISOR_TASK_NOT_FOUND")
    task=load(file)
    if task["status"]!="STOPPED":
        raise RuntimeError("ONLY_SAFE_STOPPED_TASK_CAN_RESUME")
    proof={"schema":1,"queueId":queue_id,"previousSha":sha_file(file),
           "originalStatus":task["status"],"reason":None}
    if task["kind"]=="selfcheck":
        if task.get("result")!="SAFE_CANCEL_NO_SIDE_EFFECT" or task.get("modelCalls")!=0:
            raise RuntimeError("SELFCHECK_NOT_PROVEN_NO_EFFECT")
        proof["reason"]="TRUSTED_FIXTURE_COOPERATIVE_STOP_NO_EFFECT"
    elif task["kind"]=="language":
        rootjob=multilang.jobdir(root,task["ref"])
        original=load(rootjob/"state.json")
        if original["status"]!="STOPPED" or (rootjob/"request.json").exists() or (rootjob/"original-output.json").exists():
            raise RuntimeError("LANGUAGE_MODEL_INTENT_OR_EFFECT_EXISTS_NO_REPLAY")
        multilang.control(root,task["ref"],"RUN")
        proof["reason"]="ORIGINAL_LANGUAGE_JOB_STOPPED_PRE_MODEL_INTENT"
    elif task["kind"]=="mission":
        prior=mission.summary(root,task["ref"])
        if prior["state"]["status"]!="STOPPED":
            raise RuntimeError("MISSION_NOT_STOPPED_ORIGINAL")
        mission.control(root,task["ref"],"RUN")
        proof["reason"]="ORIGINAL_MISSION_STOPPED_AT_VERIFIED_STAGE_BOUNDARY"
    elif task["kind"]=="gui":
        from . import gui_pipeline
        decision=gui_pipeline.safe_resume(root,task["ref"])
        if decision["status"]!="SAFE_RESUME_ELIGIBLE_NO_MODEL_REPLAY":
            raise RuntimeError("GUI_CANNOT_PROVE_SAFE_RESUME")
        proof["reason"]="GUI_FROZEN_OWNER_AND_ALL_STARTED_ATTEMPTS_READBACK_SAFE"
    else:
        raise RuntimeError("SUPERVISOR_UNSUPPORTED_RESUME_KIND")
    proof["atUtc"]=utc()
    receipt=p/"history"/(queue_id+"-RESUME-"+uuid.uuid4().hex[:12]+".json")
    write_json(receipt,proof,new=True)
    if task["kind"]=="gui":
        from . import gui_pipeline
        specific=gui_pipeline.folder(root,task["ref"])/"resume-proof.json"
        write_json(specific,proof,new=True)
        if sha_file(specific)!=sha_file(receipt):
            raise RuntimeError("GUI_RESUME_PROOF_READBACK_MISMATCH")
    event(p/"journal.jsonl","TASK_RESUME_PROVEN",
          {"queueId":queue_id,"proofSha":sha_file(receipt),
           "originalTaskSha":proof["previousSha"]})
    _task_update(p,file,{"status":"PENDING","resumeProofSha":sha_file(receipt),
                         "nextAction":"same task id queued after original safe stop"})
    return {"status":"PENDING_SAME_ID_PROVEN_NO_REPLAY","queueId":queue_id,
            "resumeProofSha":sha_file(receipt)}



def requeue_log_collision(root,queue_id):
    """Resume same PENDING cycle only when no child was spawned after proof."""
    root=engine.init(root)
    p=directory(root)
    if not isinstance(queue_id,str) or not re.fullmatch(r"SQ-[a-f0-9]{16}",queue_id):
        raise ValueError("SUPERVISOR_QUEUE_ID_INVALID")
    if status(root)["status"]!="STOPPED":
        raise RuntimeError("SUPERVISOR_STILL_RUNNING_NO_RECOVERY")
    file=p/"queue"/(queue_id+".json")
    task=load(file)
    if (task.get("kind")!="native" or task.get("status")!="UNKNOWN"
        or task.get("originalStatus")!="PENDING"
        or task.get("errorType")!="FileExistsError"):
        raise RuntimeError("NOT_PROVEN_NATIVE_LOG_COLLISION")
    prev_log=p/"logs"/(queue_id+".log")
    if not prev_log.is_file() or repr(str(prev_log)) not in task.get("detail",""):
        raise RuntimeError("ORIGINAL_LOG_COLLISION_NOT_VERIFIED")
    proof=native_cycle.folder(root,task["ref"])/"resume-proof.json"
    if not proof.is_file() or sha_file(proof)!=task.get("resumeProofSha"):
        raise RuntimeError("ORIGINAL_SAFE_RESUME_PROOF_DRIFT")
    state=native_cycle.status(root,task["ref"])
    if state["status"]!="PENDING" or state["sandboxJob"] is not None:
        raise RuntimeError("NATIVE_CYCLE_EFFECT_PRESENT_CANNOT_REQUEUE")
    if (native_cycle.folder(root,task["ref"])/"bridge.json").exists():
        raise RuntimeError("ORIGINAL_NATIVE_STAGE_ALREADY_EXECUTED")
    pending_log=p/"logs"/(queue_id+"-resume-"+task["resumeProofSha"][:12]+".log")
    if pending_log.exists():
        raise RuntimeError("SECOND_LOG_REPLAY_FORBIDDEN")
    rows=[json.loads(row) for row in (p/"journal.jsonl").read_text("utf-8").splitlines()]
    latest=max((i for i,row in enumerate(rows)
        if row.get("operation")=="TASK_STATE"
        and row.get("detail",{}).get("queueId")==queue_id
        and row.get("detail",{}).get("status")=="RUNNING"),default=-1)
    if latest<0 or any(row.get("operation")=="CHILD_STARTED"
        and row.get("detail",{}).get("queueId")==queue_id
        for row in rows[latest+1:]):
        raise RuntimeError("RESTART_CHILD_SPAWN_MAY_HAVE_OCCURRED")
    receipt=p/"history"/(queue_id+"-SAFE-LOG-COLLISION-RECOVERY.json")
    value={"schema":1,"queueId":queue_id,"sourceCycle":task["ref"],
        "preimageTaskSha":sha_file(file),"atUtc":utc(),
        "originalResumeProofSha":sha_file(proof),
        "originalImmutableLogSha":sha_file(prev_log),
        "journalBeforeSha":sha_file(p/"journal.jsonl"),
        "noChildStartedInLastAttempt":True,"nativeCycleStatus":"PENDING",
        "newLogPath":str(pending_log),"sameQueueId":True}
    write_json(receipt,value,new=True)
    _task_update(p,file,{"status":"PENDING","originalStatus":"PENDING",
        "logCollisionRecoverySha":sha_file(receipt),
        "nextAction":"same NC and SQ; new immutable log file, no native work repeated"})
    event(p/"journal.jsonl","SUPERVISOR_NATIVE_LOG_COLLISION_PROVEN",
          {"queueId":queue_id,"proofSha":sha_file(receipt)})
    return {"status":"PENDING_SAME_SQ_NO_NEW_NATIVE_INTENT",
        "queueId":queue_id,"recoverySha":sha_file(receipt)}

def requeue_vm_conflict(root,queue_id):
    """Same SQ ID, only exact safe pre-launch VM conflict, no blind replay."""
    root=engine.init(root)
    p=directory(root)
    if not isinstance(queue_id,str) or not re.fullmatch(r"SQ-[a-f0-9]{16}",queue_id):
        raise ValueError("SUPERVISOR_QUEUE_ID_INVALID")
    if status(root)["status"]!="STOPPED":
        raise RuntimeError("ORIGINAL_SUPERVISOR_MUST_BE_STOPPED")
    file=p/"queue"/(queue_id+".json")
    task=load(file)
    if (task.get("kind")!="native" or task.get("status")!="UNKNOWN"
        or task.get("originalStatus")!="BLOCKED_VM_CONFLICT"
        or task.get("childExitCode")!=0):
        raise RuntimeError("SUPERVISOR_NOT_PROVEN_PRELAUNCH_VM_CONFLICT")
    before=sha_file(file)
    recovery=native_cycle.resume_conflict(root,task["ref"])
    _task_update(p,file,{"status":"PENDING","originalStatus":"PENDING",
       "resumeProofSha":recovery["proofSha"],
       "resumeFromTaskSha":before,
       "nextAction":"same exact original queue ID, no native launch before conflict"})
    event(p/"journal.jsonl","NATIVE_VM_CONFLICT_QUEUE_RESUMED",
         {"queueId":queue_id,"recoveredCycle":task["ref"],
          "proofSha":recovery["proofSha"],"originalQueueSha":before})
    return {"status":"PENDING_SAME_QUEUE_NO_REPLAY",
            "queueId":queue_id,"cycleId":task["ref"],
            "proofSha":recovery["proofSha"]}

def reconcile_stale(root):
    """No worker replay after uncertain failure. Trust ONLY original receipts."""
    root=engine.init(root)
    p=directory(root)
    live=status(root)
    if live["status"]=="STOPPED":
        return {"status":"ALREADY_STOPPED_NO_RECONCILE"}
    if live["status"]=="RUNNING":
        raise RuntimeError("ACTIVE_ORIGINAL_WORKER_DO_NOT_RECONCILE")
    if live["status"]!="UNKNOWN_LEASE_STALE_RECONCILE":
        raise RuntimeError("SUPERVISOR_LEASE_NOT_RECONCILABLE")
    original=load(p/"lease.json")
    journal=[json.loads(row) for row in (p/"journal.jsonl").read_text("utf-8").splitlines()]
    child_identity={}
    for row in journal:
        if row.get("operation")=="CHILD_STARTED":
            d=row.get("detail") or {}
            child_identity[d.get("queueId")]=(d.get("pid"),d.get("processBornFiletime"))
    pending=[]
    for file in sorted((p/"queue").glob("SQ-*.json")):
        task=load(file)
        if task["status"]!="RUNNING":continue
        pid,born=child_identity.get(task["queueId"],(None,None))
        if pid and process_born(pid)==born:
            raise RuntimeError("LIVE_CHILD_STILL_RUNNING_RECONCILE_NOT_SAFE")
        passed=False
        proof=None
        if task["kind"]=="factory":
            try:
                check=factory_pipeline.reconcile(root,task["ref"])
                passed=((check["status"]==factory_pipeline.SUCCESS and
                    check.get("originalOwnerVerified") is True and
                    check.get("originalNative",{}).get("originalResultStatus")==native_cycle.OK and
                    check.get("resultReceiptSha") is not None) or
                    (check["status"]==factory_pipeline.SUCCESS_BROWSER and
                     check.get("originalOwnerVerified") is True and
                     check.get("originalBrowserVerified") is True and
                     check.get("resultReceiptSha") is not None))
                proof=check.get("resultReceiptSha")
            except (RuntimeError,FileNotFoundError,ValueError,KeyError):pass
        if task["kind"]=="gui":
            from . import gui_pipeline
            try:
                check=gui_pipeline.verify(root,task["ref"])
                passed=check.get("verified") is True
                proof=check.get("receiptSha")
            except (RuntimeError,FileNotFoundError,ValueError,KeyError):pass
        if task["kind"]=="native":
            try:
                check=native_cycle.reconcile(root,task["ref"])
                passed=(check["status"]==native_cycle.OK and
                        check.get("originalResultStatus")==native_cycle.OK)
                proof=check.get("originalResultSha")
            except (RuntimeError,FileNotFoundError,ValueError,KeyError):pass
        if task["kind"]=="direct":
            try:
                check=direct_agent.verify(root,task["ref"])
                passed=check["verified"]
                proof=sha_file(direct_agent.folder(root,task["ref"])/"manifest.json")
            except (RuntimeError,FileNotFoundError,ValueError,KeyError):pass
        if task["kind"]=="language":
            try:
                check=multilang.verify(root,task["ref"])
                passed=check["verified"]
                proof=check["modelOutputReceiptSha"]
            except (RuntimeError,FileNotFoundError,ValueError,KeyError):pass
        elif task["kind"]=="mission":
            try:
                check=mission.summary(root,task["ref"])
                passed=check["state"]["status"]=="PASS"
                proof=check["state"].get("acceptedManifestSha")
            except (RuntimeError,FileNotFoundError,ValueError,KeyError):pass
        # Never assume that a worker's exit or stdout alone proves acceptance.
        target="SUCCEEDED" if passed else "UNKNOWN"
        _task_update(p,file,{"status":target,
                "reconciledFromOriginalReceipt":bool(passed),
                "originalEvidenceSha":proof,
                "nextAction":"ALREADY_SUCCEEDED_DO_NOT_REPLAY" if passed else
                             "UNCERTAIN_EFFECT_DO_NOT_REPLAY"})
        pending.append({"queueId":task["queueId"],"status":target,
                        "originalEvidenceSha":proof})
    _control(p,"STOP")
    lease=p/"lease.json"
    transition(lease,{**original,"status":"STOPPED_RECONCILED",
                      "previousSha":sha_file(lease),"atUtc":utc()},p/"history")
    event(p/"journal.jsonl","STALE_LEASE_RECONCILED",{
          "originalLeaseSha":sha_bytes(json.dumps(original,sort_keys=True).encode()),
          "newLeaseSha":sha_file(lease),"tasks":pending,"newModelCalls":0})
    return {"status":"STOPPED_RECONCILED_NO_NEW_MODEL_CALLS","tasks":pending,
            "leaseSha256":sha_file(lease)}
