"""Recoverable multi-role mission controller (not a background daemon).

Reviewers can advise only and cannot edit; the selected editor proposes a
single source file and the original owner acceptance runs in independent WASI.
Every stage has intent, SHA-bound receipt and readback. On unknown execution,
stop and require reconciliation, never replay. STOP applies at safe boundaries.
"""
from __future__ import annotations
import json
from pathlib import Path
import uuid

from . import advisors, engine, local_runtime, source_editors
from .storage import event,load,sha_file,utc,write_json,transition,verify_journal

def create(root,jobid,editor,source_name,seed_rel,reviewers):
    root=engine.init(root)
    folder=engine.jobdir(root,jobid)
    if load(folder/"state.json")["status"]!="PENDING":
        raise RuntimeError("MISSION_REQUIRES_PENDING_JOB")
    if editor not in ("aider","codex","opencode"):
        raise RuntimeError("MISSION_EDITOR_UNKNOWN")
    if reviewers not in ([],["codex"],["opencode"],["codex","opencode"],["opencode","codex"]):
        raise RuntimeError("MISSION_REVIEWERS_NOT_SUPPORTED")
    if editor in reviewers:raise RuntimeError("REVIEWER_EQUALS_EDITOR")
    if not load(folder/"spec.json").get("acceptance"):
        raise RuntimeError("MISSION_REQUIRES_PINNED_OWNER_TESTS")
    # Refuse arbitrary user paths; only allow the factory's own bounded inputs.
    import re
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,42}\.py",source_name):
        raise RuntimeError("MISSION_SOURCE_NAME_UNSAFE")
    if not re.fullmatch(r"examples/[a-z0-9_]{1,55}\.py",seed_rel):
        raise RuntimeError("MISSION_SEED_NAME_UNSAFE")
    for other in (root/"missions").glob("AM-*/plan.json"):
        if load(other).get("jobId")==jobid:
            raise RuntimeError("MISSION_ALREADY_BOUND_TO_JOB_NO_REPLAY")
    name="AM-"+uuid.uuid4().hex[:16]
    directory=root/"missions"/name
    directory.mkdir(parents=True,exist_ok=False)
    spec=folder/"spec.json"
    seed=root/seed_rel
    if not seed.is_file() or seed.is_symlink():raise RuntimeError("MISSION_SEED_ABSENT")
    plan={"schema":1,"missionId":name,"jobId":jobid,"editor":editor,
          "sourceName":source_name,"seedRel":seed_rel,
          "seedSha256":sha_file(seed),"specSha256":sha_file(spec),
          "reviewers":reviewers,"createdUtc":utc(),
          "functionalId":"AF.FACTORY","originalJobId":jobid}
    write_json(directory/"plan.json",plan,new=True)
    write_json(directory/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    write_json(directory/"state.json",{"schema":1,"status":"PENDING",
               "stageIndex":0,"planSha256":sha_file(directory/"plan.json"),
               "nextAction":"run pending stages one at a time"},new=True)
    event(directory/"journal.jsonl","MISSION_CREATED",{"planSha256":sha_file(directory/"plan.json"),
          "jobId":jobid,"specSha":sha_file(spec)})
    return {"missionId":name,"jobId":jobid,"planSha256":sha_file(directory/"plan.json")}

def _directory(root,id):
    import re
    if not re.fullmatch(r"AM-[a-f0-9]{16}",id):raise ValueError("INVALID_MISSION_ID")
    path=Path(root).resolve()/"missions"/id
    if not path.is_dir():raise RuntimeError("MISSION_NOT_FOUND")
    return path

def control(root,id,mode):
    d=_directory(root,id)
    if mode not in ("RUN","STOP"):raise ValueError("INVALID_MISSION_CONTROL")
    old=load(d/"control.json")
    if old["command"]==mode:return old
    nextstate={"schema":1,"command":mode,"atUtc":utc(),
               "priorSha256":sha_file(d/"control.json")}
    transition(d/"control.json",nextstate,d/"history")
    event(d/"journal.jsonl","MISSION_CONTROL",{"mode":mode})
    return nextstate

def summary(root,id):
    d=_directory(root,id)
    plan=load(d/"plan.json")
    state=load(d/"state.json")
    if state.get("planSha256")!=sha_file(d/"plan.json"):
        raise RuntimeError("MISSION_PLAN_SHA_DRIFT")
    verify_journal(d/"journal.jsonl")
    return {"missionId":id,"state":state,"control":load(d/"control.json"),
            "job":engine.summary(root,plan["jobId"]),
            "plan":plan,"stages":sorted(p.name for p in d.glob("stage-*.json"))}

def _write_state(d,state):
    old=load(d/"state.json")
    state.update(schema=1,updatedUtc=utc(),
                 planSha256=old["planSha256"])
    pre=sha_file(d/"state.json")
    transition(d/"state.json",state,d/"history")
    event(d/"journal.jsonl","MISSION_STATE",{"status":state["status"],
          "stageIndex":state["stageIndex"],"priorStateSha":pre,
          "stateSha":sha_file(d/"state.json")})

def _run(root,id):
    root=engine.init(root)
    d=_directory(root,id)
    current=summary(root,id)
    state=current["state"]
    plan=current["plan"]
    if state["status"]=="PASS":
        engine.verify_job(root,plan["jobId"])
        return {"status":"ALREADY_PASS_NO_REPLAY","missionId":id}
    if state["status"] in ("UNKNOWN","RUNNING","FAILED"):
        raise RuntimeError("MISSION_UNCERTAIN_OR_FAILED_RECONCILE_DO_NOT_REPLAY")
    order=[("review",advisor) for advisor in plan["reviewers"]]
    order.append(("source",plan["editor"]))
    if state["stageIndex"]>len(order):raise RuntimeError("MISSION_STAGE_INDEX_INVALID")
    if sha_file(root/plan["seedRel"])!=plan["seedSha256"]:
        raise RuntimeError("MISSION_SEED_SHA_DRIFT")
    if sha_file(root/"work"/plan["jobId"]/"spec.json")!=plan["specSha256"]:
        raise RuntimeError("MISSION_SPEC_SHA_DRIFT")
    for i in range(state["stageIndex"],len(order)):
        if load(d/"control.json")["command"]=="STOP":
            _write_state(d,{"status":"STOPPED","stageIndex":i,"nextAction":"resume from safe stage boundary"})
            return summary(root,id)
        role,tool=order[i]
        stage=d/("stage-"+str(i+1).zfill(2)+".json")
        if stage.exists():
            # A completed state and an existing receipt cannot be replayed.
            raise RuntimeError("MISSION_STAGE_ALREADY_PRESENT_RECONCILE")
        jobstate=load(root/"work"/plan["jobId"]/"state.json")["status"]
        if jobstate not in ("PENDING","DRAFT_READY_UNTESTED"):
            raise RuntimeError("MISSION_JOB_NOT_PENDING:"+jobstate)
        _write_state(d,{"status":"RUNNING","stageIndex":i,
                        "nextAction":"stage "+role+" "+tool+" in progress"})
        event(d/"journal.jsonl","MISSION_STAGE_INTENT",
              {"i":i,"role":role,"tool":tool,"jobId":plan["jobId"]})
        try:
            if role=="review":
                live=local_runtime.server_info(root)
                started_here=live["state"]=="NOT_STARTED"
                if started_here:
                    if local_runtime.start(root)["state"]!="READY":
                        raise RuntimeError("REVIEW_LOCAL_SERVER_NOT_READY")
                elif live["state"]!="READY":
                    raise RuntimeError("REVIEW_SERVER_STATE_UNCERTAIN")
                try:
                    result=advisors.advise(root,tool,plan["jobId"])
                finally:
                    if started_here:
                        closed=local_runtime.stop(root)
                        if closed["state"] not in ("STOPPED","STOPPED_RECONCILED"):
                            raise RuntimeError("REVIEW_MODEL_STOP_UNCERTAIN")
                good=result.get("status") in ("ADVICE_ONLY_NOT_APPLIED","CACHE_REUSE_NO_MODEL_CALL")
            else:
                if tool=="aider":
                    from . import aider_bridge
                    result=aider_bridge.admit(root,plan["jobId"],plan["sourceName"],plan["seedRel"])
                else:
                    result=source_editors.run(root,tool,plan["jobId"],plan["sourceName"],plan["seedRel"])
                status=result.get("state",{}).get("status")
                good=status=="PASS"
                if good:engine.verify_job(root,plan["jobId"])
        except Exception as err:
            # Store failure class and stop; NEVER replay a possibly running effect.
            receipt={"schema":1,"stage":i,"role":role,"tool":tool,
                     "status":"UNKNOWN_RECONCILE","errorType":type(err).__name__,
                     "error":str(err)[:250],"completedUtc":utc()}
            write_json(stage,receipt,new=True)
            event(d/"journal.jsonl","MISSION_STAGE_UNKNOWN",{"i":i,"receiptSha":sha_file(stage)})
            _write_state(d,{"status":"UNKNOWN","stageIndex":i,
                            "nextAction":"reconcile original child and receipt; never auto replay"})
            return summary(root,id)
        result_status=result.get("status") if role=="review" else status
        receipt={"schema":1,"stage":i,"role":role,"tool":tool,
                 "status":"PASS" if good else "FAILED_OR_UNKNOWN",
                 "originalResultStatus":result_status,
                 "jobState":load(root/"work"/plan["jobId"]/"state.json")["status"],
                 "completedUtc":utc()}
        write_json(stage,receipt,new=True)
        event(d/"journal.jsonl","MISSION_STAGE_RECEIPT",
              {"i":i,"receiptSha":sha_file(stage),"status":receipt["status"]})
        if not good:
            stop_state="UNKNOWN" if result_status in ("UNKNOWN",None) else "FAILED"
            _write_state(d,{"status":stop_state,"stageIndex":i,
                            "nextAction":"inspect original editor receipt and test acceptance"})
            return summary(root,id)
        _write_state(d,{"status":"READY","stageIndex":i+1,"nextAction":"advance to next stage"})
    manifest=root/"work"/plan["jobId"]/"manifest.json"
    verified=engine.verify_job(root,plan["jobId"])
    if not verified.get("verified") or not manifest.is_file():
        raise RuntimeError("MISSION_OWNER_VERIFIER_NOT_PROVEN")
    _write_state(d,{"status":"PASS","stageIndex":len(order),
                    "acceptedManifestSha":sha_file(manifest),
                    "nextAction":"SUCCEEDED, no replay"})
    return summary(root,id)


def run(root,id):
    """Keep a project-owned model server warm across all mission stages."""
    root=engine.init(root)
    d=_directory(root,id)
    current=summary(root,id)
    if current["state"]["status"] in ("PASS","UNKNOWN","RUNNING","FAILED"):
        return _run(root,id)
    if current["control"]["command"]=="STOP":
        return _run(root,id)
    live=local_runtime.server_info(root)
    if live["state"]=="EXITED":
        local_runtime.stop(root)
        live=local_runtime.server_info(root)
    if live["state"] not in ("READY","NOT_STARTED"):
        raise RuntimeError("MISSION_LOCAL_SERVER_NOT_RECONCILED")
    started_here=False
    if live["state"]=="NOT_STARTED":
        ready=local_runtime.start(root)
        if ready["state"]!="READY":
            raise RuntimeError("MISSION_LOCAL_SERVER_NOT_READY")
        started_here=True
    try:
        return _run(root,id)
    finally:
        if started_here:
            stopped=local_runtime.stop(root)
            if stopped.get("state") not in ("STOPPED","STOPPED_RECONCILED"):
                raise RuntimeError("MISSION_OWNED_SERVER_STOP_UNKNOWN")


def reconcile(root,id):
    """Recover only a stage that left an original SHA-bound completed receipt.

    An intent without a completed receipt becomes UNKNOWN, never replayed.
    A prior SUCCEEDED stage is not invoked again.
    """
    root=engine.init(root)
    d=_directory(root,id)
    original=summary(root,id)
    state=original["state"]
    if state["status"] in ("PASS","READY","STOPPED","PENDING"):
        return {"status":"NOTHING_TO_RECONCILE","mission":original}
    if state["status"]!="RUNNING":
        raise RuntimeError("MISSION_UNKNOWN_OR_FAILED_REQUIRES_MANUAL_RECONCILIATION")
    i=state["stageIndex"]
    plan=original["plan"]
    order=[("review",name) for name in plan["reviewers"]]+[("source",plan["editor"])]
    if not isinstance(i,int) or i<0 or i>=len(order):
        raise RuntimeError("MISSION_BAD_RECONCILE_INDEX")
    stage=d/("stage-"+str(i+1).zfill(2)+".json")
    if not stage.is_file():
        _write_state(d,{"status":"UNKNOWN","stageIndex":i,
                        "nextAction":"stage intent without original completed receipt; reconcile child"})
        return {"status":"UNKNOWN_NO_REPLAY","mission":summary(root,id)}
    receipt=load(stage)
    role,tool=order[i]
    if receipt.get("stage")!=i or receipt.get("role")!=role or receipt.get("tool")!=tool:
        raise RuntimeError("RECONCILE_STAGE_ROLE_DRIFT")
    lines=[json.loads(row) for row in (d/"journal.jsonl").read_text("utf-8").splitlines()]
    witnessed=[row for row in lines if row.get("operation")=="MISSION_STAGE_RECEIPT"
               and row["detail"].get("i")==i
               and row["detail"].get("receiptSha")==sha_file(stage)]
    if len(witnessed)!=1 or receipt.get("status")!="PASS":
        raise RuntimeError("NO_ORIGINAL_PASSED_STAGE_SHA_RECEIPT")
    if role=="source":
        manifest=root/"work"/plan["jobId"]/"manifest.json"
        verified=engine.verify_job(root,plan["jobId"])
        if not verified.get("verified") or not manifest.is_file():
            raise RuntimeError("SOURCE_STAGE_WITHOUT_ORIGINAL_ACCEPTANCE")
    else:
        found=[]
        for advice_file in (root/"work"/plan["jobId"]/"advice").glob("*.json"):
            data=load(advice_file)
            if data.get("tool")==tool and data.get("jobId")==plan["jobId"] and data.get("status")=="ADVICE_ONLY_NOT_APPLIED":
                found.append(advice_file)
        if not found:
            raise RuntimeError("REVIEW_STAGE_WITHOUT_ORIGINAL_ADVISOR_RECEIPT")
    event(d/"journal.jsonl","MISSION_STAGE_RECOVERED",
          {"i":i,"originalReceiptSha":sha_file(stage),
           "newModelCalls":0,"acceptedOriginalStage":True})
    _write_state(d,{"status":"READY","stageIndex":i+1,
                    "nextAction":"resume only next stage, no replay of accepted stage"})
    return {"status":"RECOVERED_WITH_ORIGINAL_RECEIPT_NO_REPLAY",
            "mission":summary(root,id)}
