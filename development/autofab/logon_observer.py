# coding: utf-8
"""Original worker one-shot proof of a NEW Windows boot without replaying work.

Runs once on a separate daemon thread in the existing scheduled-task process,
and only if the OS boot time really advanced beyond the immutable baseline.
Never schedules tasks, restarts Windows, executes models, or writes after STOP.
The authoritative original reboot_audit.verify still decides PASS/FAILED.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import os
import threading

from . import reboot_audit
from .storage import load,sha_bytes,sha_file,utc

def _save_new(path,body):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    if sha_file(path)!=sha_bytes(body):
        raise RuntimeError("LOGON_PROBE_RECEIPT_SHA_DRIFT")

def _write_outcome(root,result,before,boot,lease):
    folder=Path(root).resolve()/reboot_audit.ROOTDIR
    original=folder/"AUTO-LOGON-REBOOT-READBACK.json"
    rescue=Path(r"D:\AUTOFABRICADOR-RESCATE")/reboot_audit.ROOTDIR/"AUTO-LOGON-REBOOT-READBACK.json"
    if original.exists():
        # No reissue from another worker or process.
        return {"status":"ORIGINAL_LOGON_PROBE_ALREADY_RECEIPTED_NO_REPLAY",
                "receiptSha":sha_file(original)}
    if rescue.exists():
        raise RuntimeError("LOGON_RESCUE_PREEXISTS_WITHOUT_ORIGINAL_RECONCILE")
    data={
      "schema":1,"atUtc":utc(),
      "operationId":"AF.WIN.NEW-LOGON.REBOOT-PROBE.ORIGINAL-WORKER-20261108",
      "status":result["status"],
      "physicalRebootObserved":True,
      "baselineSha":sha_file(folder/"BASELINE.json"),
      "originalBaselineBootUtc":before["bootUtc"],
      "newWindowsBootUtc":boot,
      "workerPid":lease["pid"],
      "workerBornFiletime":lease["processBornFiletime"],
      "originalCliSha":lease["cliSha256"],
      "originalVerification":result,
      "noRepeatOfPriorJobs":True,
      "noHostScheduledTaskChanges":True,"noPhysicalRebootInitiated":True,
      "noMMC":True,"noF":True}
    binary=(json.dumps(data,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode()
    _save_new(original,binary)
    _save_new(rescue,binary)
    if sha_file(original)!=sha_file(rescue):
        raise RuntimeError("LOGON_REBOOT_D_RESCUE_READBACK_FAILED")
    return {"status":result["status"],"receiptSha":sha_file(original)}

def check(root,lease):
    """Exposed for deterministic tests, invoked once in local worker thread."""
    folder=Path(root).resolve()/reboot_audit.ROOTDIR
    baseline=folder/"BASELINE.json"
    if not baseline.is_file() or baseline.is_symlink():
        return {"status":"NO_REBOOT_BASELINE"}
    prior=load(baseline)
    now=reboot_audit._os()
    if now["hostname"]!=prior["hostname"]:
        raise RuntimeError("LOGON_REBOOT_WRONG_HOST")
    if reboot_audit._date(now["bootUtc"])<=reboot_audit._date(prior["bootUtc"]):
        return {"status":"PENDING_REAL_WINDOWS_REBOOT_NOT_PERFORMED"}
    if not isinstance(lease,dict) or not isinstance(lease.get("pid"),int):
        raise ValueError("LOGON_ORIGINAL_WORKER_LEASE_INVALID")
    # Original verification requires TaskScheduler, PID+birth, immutable
    # SUCCEEDED hashes and new OS boot. A failed probe is NOT a PASS.
    result=reboot_audit.verify(root)
    if result["status"]=="PENDING_REAL_WINDOWS_REBOOT_NOT_PERFORMED":
        raise RuntimeError("LOGON_NEW_BOOT_BUT_AUDIT_STILL_PENDING")
    return _write_outcome(root,result,prior,now["bootUtc"],lease)

def begin(root,lease):
    """No extra executable/service. Existing original worker owns this thread."""
    r=Path(root).resolve()
    if not (r/reboot_audit.ROOTDIR/"BASELINE.json").is_file():
        return {"status":"NO_REBOOT_BASELINE_NO_THREAD"}
    def run():
        try:
            check(r,lease)
        except Exception as err:
            # The untrusted/failed probe does not take the supervisor down,
            # and it cannot declare M6 PASS. Never issue a duplicate result.
            folder=r/reboot_audit.ROOTDIR
            issue=folder/"AUTO-LOGON-REBOOT-ERROR.json"
            if issue.exists():return
            payload={"schema":1,"atUtc":utc(),
                     "status":"UNKNOWN_ORIGINAL_REBOOT_PROBE",
                     "errorType":type(err).__name__,
                     "detail":str(err)[:200],
                     "originalWorkerPid":lease.get("pid")}
            blob=(json.dumps(payload,sort_keys=True,indent=2)+"\n").encode()
            try:
                _save_new(issue,blob)
                d=Path(r"D:\AUTOFABRICADOR-RESCATE")/reboot_audit.ROOTDIR/issue.name
                _save_new(d,blob)
            except Exception:
                # Preserve original failure; no arbitrary retry or host action.
                pass
    threading.Thread(target=run,daemon=True,
       name="AF-Original-Worker-Logon-Readback").start()
    return {"status":"ORIGINAL_WORKER_ONE_SHOT_REBOOT_PROBE_THREAD_STARTED",
            "noJobReplay":True,"noNewService":True}
