# coding: utf-8
"""Persistent single-intent cycle for originally accepted ESM repo -> Windows Sandbox.

Only trusted first-party commands run on Windows Host. Untrusted source executes
in WASI and in the ephemeral native guest; guest output is NOT owner attestation.
Attempts are never replayed on UNKNOWN or after a launch intent.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from . import engine, repo_factory, native_repo_bridge, windows_sandbox
from .storage import event, load, sha_file, transition, utc, verify_journal, write_json

CYCLE_ID = re.compile(r"NC-[0-9a-f]{16}\Z")
REPO_ID = re.compile(r"RJ-[0-9a-f]{16}\Z")
OK = "PASS_WASI_AND_GUEST_CORRELATED_UNTRUSTED"
FINAL = frozenset((OK, "STOPPED_PRE_LAUNCH", "STOPPED_AFTER_LAUNCH_UNVERIFIED",
                   "FAILED_GUEST", "UNKNOWN", "BLOCKED_VM_CONFLICT"))
TIMEOUT_SECONDS = 160

def folder(root, cycle):
    if not isinstance(cycle, str) or not CYCLE_ID.fullmatch(cycle):
        raise ValueError("NATIVE_CYCLE_ID_INVALID")
    return Path(root).resolve()/"nativecycles"/cycle

def _get(root,cycle):
    d=folder(root,cycle)
    if not (d/"intent.json").is_file(): raise FileNotFoundError("NATIVE_CYCLE_NOT_FOUND")
    return d

def _step(d, status, note, **details):
    original=d/"state.json"
    data={"schema":1,"status":status,"atUtc":utc(),"note":note,
          "previousSha":sha_file(original),**details}
    transition(original,data,d/"history")
    event(d/"journal.jsonl","NATIVE_CYCLE_STATE",
          {"status":status,"stateSha":sha_file(original)})
    return data

def _sessions():
    """Windows process query. Failure is UNKNOWN, never assume VM is absent."""
    if os.name!="nt":raise RuntimeError("NATIVE_VM_ONLY_ON_WINDOWS")
    cmd=["powershell.exe","-NoProfile","-NonInteractive","-Command",
         "$ErrorActionPreference='Stop';"
         "$a=@(Get-CimInstance Win32_Process -Filter \"Name='WindowsSandboxRemoteSession.exe'\" "
         "| ForEach-Object { [pscustomobject]@{ ProcessId=[int]$_.ProcessId; "
         "CreationTicks=[Int64]$_.CreationDate.ToUniversalTime().Ticks } });"
         "ConvertTo-Json -InputObject $a -Compress"]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=15,
                     stdin=subprocess.DEVNULL)
    if r.returncode:raise RuntimeError("WINDOWS_VM_PROCESS_QUERY_FAILED")
    raw=json.loads(r.stdout.strip())
    if not isinstance(raw,list):raise RuntimeError("WINDOWS_VM_LIST_NOT_ARRAY")
    if any(not isinstance(x.get("ProcessId"),int)
           or not isinstance(x.get("CreationTicks"),int)
           or x["CreationTicks"]<=0 for x in raw):
        raise RuntimeError("WINDOWS_VM_IDENTITY_UNAVAILABLE")
    return [{"pid":x["ProcessId"],"born":str(x["CreationTicks"])} for x in raw]

def _close_session_exact(session):
    """Close only the unique observed session with unchanged PID AND birth."""
    if not session:return {"closed":False,"reason":"NO_UNIQUE_VM_IDENTITY"}
    pid=session["pid"]
    birth=session["born"]
    now=_sessions()
    if len(now)!=1 or now[0]!=session:
        return {"closed":False,"reason":"WINDOWS_VM_SESSION_IDENTITY_DRIFT"}
    # Only the exact original disposable VM, never an arbitrary process ID.
    command=("$ErrorActionPreference='Stop';"
       "$p=Get-CimInstance Win32_Process -Filter \"ProcessId=%d\";"
       "if(-not $p -or $p.Name -ne 'WindowsSandboxRemoteSession.exe'"
       " -or [Int64]$p.CreationDate.ToUniversalTime().Ticks -ne [Int64]%s)"
       "{throw 'GUEST_VM_PROCESS_IDENTITY_DRIFT'};"
       "Stop-Process -Id %d -Force -ErrorAction Stop")%(pid,birth,pid)
    rc=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],
                      capture_output=True,text=True,timeout=15,stdin=subprocess.DEVNULL)
    if rc.returncode:return {"closed":False,"reason":"WINDOWS_GUEST_CLOSE_FAILED"}
    for _ in range(20):
        time.sleep(.25)
        if session not in _sessions():
            return {"closed":True,"reason":"ORIGINAL_VM_SESSION_ENDED"}
    return {"closed":False,"reason":"WINDOWS_VM_STILL_ALIVE_AFTER_CLOSE"}

def create(root, repo):
    root=engine.init(root)
    if not isinstance(repo,str) or not REPO_ID.fullmatch(repo):
        raise ValueError("NATIVE_CYCLE_REPO_ID_INVALID")
    accepted=repo_factory.verify(root,repo)
    if not accepted.get("verified") or accepted["status"]!="PASS":
        raise RuntimeError("NATIVE_CYCLE_ORIGINAL_WASI_MUST_BE_PASS")
    cycles=Path(root)/"nativecycles"
    cycles.mkdir(exist_ok=True)
    for p in cycles.glob("NC-*/intent.json"):
        row=load(p)
        if row.get("sourceRepo")==repo:
            return {"status":"ALREADY_CREATED_NO_REPLAY","cycleId":p.parent.name,
                    "originalStatus":load(p.parent/"state.json")["status"]}
    name="NC-"+uuid.uuid4().hex[:16]
    d=cycles/name
    d.mkdir(exist_ok=False)
    (d/"history").mkdir()
    original=Path(root)/"repojobs"/repo/"manifest.json"
    intent={"schema":1,"cycleId":name,"sourceRepo":repo,
            "sourceRepoManifestSha":sha_file(original),"ownerCases":accepted["ownerCases"],
            "modelAttempts":accepted["modelAttempts"],"atUtc":utc(),
            "operationId":name+".NATIVE_ORIGINAL.ONE_SHOT"}
    write_json(d/"intent.json",intent,new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    event(d/"journal.jsonl","NATIVE_CYCLE_CREATED",
          {"cycleId":name,"intentSha":sha_file(d/"intent.json"),
           "originalRepoManifestSha":intent["sourceRepoManifestSha"]})
    return {"cycleId":name,"status":"PENDING","sourceRepo":repo,
            "originalOwnerCases":intent["ownerCases"]}

def status(root,cycle):
    d=_get(root,cycle)
    verify_journal(d/"journal.jsonl")
    intent=load(d/"intent.json")
    state=load(d/"state.json")
    bridge=load(d/"bridge.json") if (d/"bridge.json").exists() else None
    return {"cycleId":cycle,"status":state["status"],"sourceRepo":intent["sourceRepo"],
            "originalOwnerCases":intent["ownerCases"],
            "sandboxJob":bridge["sandboxJob"] if bridge else None,
            "control":load(d/"control.json")["command"],
            "verifiedJournal":True,"guestClaimsAuthenticated":False}

def stop(root,cycle):
    d=_get(root,cycle)
    state=load(d/"state.json")["status"]
    if state in FINAL:return {"status":"TERMINAL_NO_ACTION","originalStatus":state}
    control=d/"control.json"
    old=load(control)
    if old["command"]!="STOP":
        transition(control,{"schema":1,"command":"STOP","previousSha":sha_file(control),
                            "atUtc":utc()},d/"history")
        event(d/"journal.jsonl","NATIVE_CYCLE_STOP",
              {"controlSha":sha_file(control),"stateWas":state})
    if (d/"bridge.json").exists():
        bridge=load(d/"bridge.json")
        job=Path(root)/"sandboxjobs"/bridge["sandboxJob"]
        if (job/"launch-intent.json").exists():
            # Original Sandbox stop is cooperative; never claim immediate stop.
            windows_sandbox.stop(root,bridge["sandboxJob"])
    return {"status":"STOP_REQUESTED_FIRST_SAFE_BOUNDARY","originalStatus":state}

def _blocked_or_stopped(d):
    return load(d/"control.json")["command"]=="STOP"

def run(root,cycle,*,timeout=TIMEOUT_SECONDS):
    root=engine.init(root)
    d=_get(root,cycle)
    intent=load(d/"intent.json")
    prior=load(d/"state.json")["status"]
    if prior!="PENDING":
        raise RuntimeError("NATIVE_CYCLE_ALREADY_INTENDED_NO_BLIND_REPLAY:"+prior)
    if (d/"bridge.json").exists():
        raise RuntimeError("NATIVE_CYCLE_ORIGINAL_BRIDGE_ALREADY_EXISTS")
    if _blocked_or_stopped(d):
        _step(d,"STOPPED_PRE_LAUNCH","STOP before native staging; no original launch")
        return {"status":"STOPPED_PRE_LAUNCH","cycleId":cycle}
    source=Path(root)/"repojobs"/intent["sourceRepo"]/"manifest.json"
    if sha_file(source)!=intent["sourceRepoManifestSha"]:
        raise RuntimeError("NATIVE_CYCLE_ORIGINAL_REPO_MANIFEST_DRIFT")
    verified=repo_factory.verify(root,intent["sourceRepo"])
    if not verified.get("verified") or verified["ownerCases"]!=intent["ownerCases"]:
        raise RuntimeError("NATIVE_CYCLE_OWNER_ACCEPTANCE_DRIFT")
    if _sessions():
        _step(d,"BLOCKED_VM_CONFLICT","Existing Sandbox VM prevents unique session attribution")
        return {"status":"BLOCKED_VM_CONFLICT","cycleId":cycle}
    _step(d,"RUNNING","original model + WASI verified, before native staging")
    try:
        staged=native_repo_bridge.stage_repo(root,intent["sourceRepo"])
        sid=staged["sandboxJob"]
        write_json(d/"bridge.json",
            {"schema":1,"sandboxJob":sid,"sourceRepo":intent["sourceRepo"],
             "sourceZipSha":staged["zipSha"],"atUtc":utc()},new=True)
        event(d/"journal.jsonl","NATIVE_CYCLE_BRIDGE_STAGED",
              {"sandboxJob":sid,"sourceSha":staged["zipSha"],
               "bridgeSha":sha_file(d/"bridge.json")})
        if _blocked_or_stopped(d):
            windows_sandbox.stop(root,sid)
            _step(d,"STOPPED_PRE_LAUNCH","STOP after staging, no VM launch",sandboxJob=sid)
            return {"status":"STOPPED_PRE_LAUNCH","cycleId":cycle,"sandboxJob":sid}
        if _sessions():
            _step(d,"BLOCKED_VM_CONFLICT","VM started by someone else before launch",
                  sandboxJob=sid)
            return {"status":"BLOCKED_VM_CONFLICT","cycleId":cycle,"sandboxJob":sid}
        _step(d,"NATIVE_LAUNCH_PENDING","original launch side effect next, do not replay",
              sandboxJob=sid)
        result=windows_sandbox.launch(root,sid)
        if result["status"]!="LAUNCHED_GUEST_NOT_ATTESTED":
            _step(d,"UNKNOWN","native OS launch unavailable or uncertain",sandboxJob=sid)
            return {"status":"UNKNOWN","cycleId":cycle,"sandboxJob":sid}
        _step(d,"NATIVE_LAUNCHED","actual Windows Sandbox launched, awaiting guest",
              sandboxJob=sid)
        guest=Path(root)/"sandboxjobs"/sid/"output/guest-report.json"
        started=time.monotonic()
        stop_sent=False
        while time.monotonic()-started < timeout:
            if _blocked_or_stopped(d) and not stop_sent:
                windows_sandbox.stop(root,sid)
                stop_sent=True
            if guest.is_file() and guest.stat().st_size>0:
                break
            time.sleep(.4)
        if not guest.is_file():
            _step(d,"UNKNOWN","no complete original guest receipt; no retry",
                  sandboxJob=sid,stopRequested=stop_sent)
            return {"status":"UNKNOWN","cycleId":cycle,"sandboxJob":sid}
        # Probe output only after source manifest and journal are rechecked.
        result=native_repo_bridge.verify_native(root,sid)
        guest_sha=sha_file(guest)
        try:
            sessions=_sessions()
            session=sessions[0] if len(sessions)==1 else None
            close=_close_session_exact(session) if session else {
                "closed":False,"reason":"SESSION_MISSING_OR_AMBIGUOUS"}
        except Exception as close_error:
            close={"closed":False,"reason":"VM_CLEANUP_UNKNOWN:"+type(close_error).__name__}
        accepted=(result.get("status")=="ORIGINAL_WASI_AND_NATIVE_GUEST_READBACK_CORRELATED"
                  and not stop_sent and not _blocked_or_stopped(d))
        state=(OK if accepted else
               "STOPPED_AFTER_LAUNCH_UNVERIFIED" if stop_sent or _blocked_or_stopped(d)
               else "FAILED_GUEST")
        receipt={"schema":1,"cycleId":cycle,"sourceRepo":intent["sourceRepo"],
                 "sandboxJob":sid,"status":state,"originalWasiAccepted":True,
                 "ownerCases":intent["ownerCases"],"originalRepoManifestSha":sha_file(source),
                 "sandboxOriginalGuestReportSha":guest_sha,
                 "nativeReported":result.get("status"),
                 "nativeCryptographicOwnerAcceptance":False,"guestOutputUntrusted":True,
                 "noModelCodeRanOnHost":True,"vmCleanup":close,"atUtc":utc()}
        write_json(d/"result.json",receipt,new=True)
        event(d/"journal.jsonl","NATIVE_CYCLE_TERMINAL_RECEIPT",
              {"receiptSha":sha_file(d/"result.json"),"status":state})
        _step(d,state,"original WASI + native guest readback; never guest attestation",
              resultSha=sha_file(d/"result.json"))
        return receipt
    except Exception as error:
        # An OS launch may already have occurred. Do not replay after exception.
        _step(d,"UNKNOWN","deterministic error or uncertain original child, reconcile only",
              errorType=type(error).__name__,errorDetail=str(error)[:240])
        raise

def reconcile(root,cycle):
    """Read-only, no model/VM replay. State and historical original receipts."""
    d=_get(root,cycle)
    out=status(root,cycle)
    if (d/"bridge.json").exists():
        sid=load(d/"bridge.json")["sandboxJob"]
        out["originalSandbox"]=windows_sandbox.reconcile(root,sid)
        if (d/"result.json").is_file():
            r=load(d/"result.json")
            out["originalResultSha"]=sha_file(d/"result.json")
            out["originalResultStatus"]=r["status"]
    return out

def resume_conflict(root,cycle):
    """Recover precisely a pre-launch VM conflict with ZERO original side effects.

    It is NOT a general resume operation and cannot be used for UNKNOWN guest,
    issued launch-intent, or any prior staged payload. Same cycle ID only.
    """
    root=engine.init(root)
    d=_get(root,cycle)
    state=load(d/"state.json")
    if state["status"]!="BLOCKED_VM_CONFLICT":
        raise RuntimeError("ONLY_PRELAUNCH_VM_CONFLICT_IS_RESUMABLE")
    if (d/"bridge.json").exists() or (d/"result.json").exists():
        raise RuntimeError("NATIVE_BRIDGE_OR_OUTPUT_EXISTS_NO_RESUME")
    if (d/"resume-proof.json").exists():
        raise RuntimeError("NATIVE_CYCLE_ONLY_ONE_PROVEN_CONFLICT_RESUME")
    if load(d/"control.json")["command"]!="RUN":
        raise RuntimeError("NATIVE_CYCLE_CONTROL_NOT_RUNNING")
    proof_journal=verify_journal(d/"journal.jsonl")
    rows=[json.loads(x) for x in (d/"journal.jsonl").read_text("utf-8").splitlines()]
    if any(row["operation"] in (
         "NATIVE_CYCLE_BRIDGE_STAGED","NATIVE_CYCLE_TERMINAL_RECEIPT")
         for row in rows):
        raise RuntimeError("ORIGINAL_NATIVE_SIDE_EFFECT_PRESENT")
    if _sessions():raise RuntimeError("NATIVE_GUEST_VM_STILL_RUNNING")
    info=load(d/"intent.json")
    repo=Path(root)/"repojobs"/info["sourceRepo"]/"manifest.json"
    if sha_file(repo)!=info["sourceRepoManifestSha"]:
        raise RuntimeError("REPO_ORIGINAL_SOURCE_MANIFEST_CHANGED")
    accepted=repo_factory.verify(root,info["sourceRepo"])
    if not accepted.get("verified") or accepted["ownerCases"]!=info["ownerCases"]:
        raise RuntimeError("OWNER_WASI_ACCEPTANCE_DRIFT")
    proof={"schema":1,"cycleId":cycle,"atUtc":utc(),
      "priorState":"BLOCKED_VM_CONFLICT","originalStateSha":sha_file(d/"state.json"),
      "originalJournalSha":sha_file(d/"journal.jsonl"),
      "journalEvents":proof_journal["events"],"originalSourceSha":sha_file(repo),
      "sideEffectsBeforeConflict":0,"nativeGuestLaunchIntent":False,
      "modelInferenceRepeated":False,"newCycleIdCreated":False}
    write_json(d/"resume-proof.json",proof,new=True)
    event(d/"journal.jsonl","NATIVE_VM_CONFLICT_RECOVERY_PROVEN",
          {"proofSha":sha_file(d/"resume-proof.json")})
    _step(d,"PENDING","recovery of pre-launch-only conflict; same original cycle",
          recoveredConflictProofSha=sha_file(d/"resume-proof.json"))
    return {"status":"PENDING_SAME_ID_ZERO_NATIVE_EFFECTS",
            "cycleId":cycle,"proofSha":sha_file(d/"resume-proof.json")}
