# coding: utf-8
"""Read-only Windows reboot/logon proof; never restarts OS or replays jobs.

A real new OS LastBootUpTime is mandatory, together with live original
Task Scheduler and supervisor lease identity, and SHA-pinned prior successes.
Before a physical reboot, report PENDING rather than inventing PASS.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import json
import subprocess

from . import engine,supervisor
from .storage import sha_file,load,write_json,utc

TASK="AUTOFABRICADOR-AGENTES-LOCALES"
TASKPATH="\\AUTOFABRICADOR\\"
ROOTDIR="CONTINUIDAD/REINICIO-SESSION-20261108"

def _powershell_json(code):
    result=subprocess.run(["powershell","-NoProfile","-NonInteractive",
                           "-Command",code],stdin=subprocess.DEVNULL,
                          capture_output=True,text=True,timeout=18)
    if result.returncode!=0 or not result.stdout.strip():
        raise RuntimeError("REBOOT_WINDOWS_READBACK_COMMAND_FAILED")
    data=json.loads(result.stdout)
    if not isinstance(data,dict):
        raise RuntimeError("REBOOT_WINDOWS_READBACK_NOT_OBJECT")
    return data

def _os():
    code=(
      "$os=Get-CimInstance Win32_OperatingSystem -ErrorAction Stop;"
      "$boot=$os.LastBootUpTime.ToUniversalTime().ToString('o');"
      "[pscustomobject]@{bootUtc=$boot;hostname=$env:COMPUTERNAME}|ConvertTo-Json -Compress")
    return _powershell_json(code)

def _task():
    code=(
      "$t=Get-ScheduledTask -TaskName '"+TASK+"' -TaskPath '"+TASKPATH+"' -ErrorAction Stop;"
      "$i=Get-ScheduledTaskInfo -TaskName '"+TASK+"' -TaskPath '"+TASKPATH+"' -ErrorAction Stop;"
      "[pscustomobject]@{name=$t.TaskName;state=$t.State.ToString();"
      "runLevel=$t.Principal.RunLevel.ToString();principal=$t.Principal.UserId;"
      "action=$t.Actions.Execute;arguments=$t.Actions.Arguments;"
      "lastRunUtc=$i.LastRunTime.ToUniversalTime().ToString('o');"
      "lastResult=$i.LastTaskResult}|ConvertTo-Json -Compress")
    return _powershell_json(code)

def _filetime_to_datetime(value):
    if type(value) is not int or value<=0:
        raise ValueError("REBOOT_ORIGINAL_PROCESS_BIRTH_INVALID")
    from datetime import timedelta
    return datetime(1601,1,1,tzinfo=timezone.utc)+timedelta(microseconds=value//10)

def _date(value):
    return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)

def _successes(root):
    queue=Path(root)/"supervisor/queue"
    success=["SQ-e3fcea2a2e384d8c","SQ-10f68017e4094362",
             "SQ-0039207931934d0a","SQ-4098c0125f53440f",
             "SQ-90c96d46a23743d8"]
    records={}
    for name in success:
        p=queue/(name+".json")
        current=load(p)
        if current["status"]!="SUCCEEDED":
            raise RuntimeError("REBOOT_PREVIOUS_SUCCESS_NOT_SUCCEEDED:"+name)
        records[name]=sha_file(p)
    return records

def _folder(root):
    return Path(root).resolve()/ROOTDIR

def establish(root):
    root=engine.init(root)
    dest=_folder(root)
    if (dest/"BASELINE.json").exists():
        return {"status":"EXISTING_BASELINE_NO_REPLAY",
                "baselineSha":sha_file(dest/"BASELINE.json"),
                "bootUtc":load(dest/"BASELINE.json")["bootUtc"]}
    state=supervisor.status(root)
    task=_task()
    osinfo=_os()
    if (state["status"]!="RUNNING" or not state["processIdentityBirthVerified"] or
        state["pendingQueue"] or task["state"]!="Running" or
        task["runLevel"]!="Limited" or task["name"]!=TASK):
        raise RuntimeError("REBOOT_BASELINE_ORIGINAL_WORKER_NOT_VERIFIED")
    prior=_successes(root)
    original={
      "schema":1,"atUtc":utc(),
      "operationId":"AF.WIN.LOGON-REBOOT-CERTIFICATION-20261108",
      "bootUtc":osinfo["bootUtc"],"hostname":osinfo["hostname"],
      "task":TASKPATH+TASK,"taskPrincipal":task["principal"],
      "taskRunLevel":"Limited","lastTaskRunUtc":task["lastRunUtc"],
      "originalWorkerPid":state["lease"]["pid"],
      "originalWorkerProcessBorn":state["lease"]["processBornFiletime"],
      "originalCLISha":state["lease"]["cliSha256"],
      "immutableSUCCEEDEDQueues":prior,
      "pendingQueue":0,
      "noRebootInitiatedHere":True,
      "needsActualNewWindowsBoot":True,
      "modelJobsReplayed":0,"noMMC":True,"noF":True}
    dest.mkdir(parents=True,exist_ok=True)
    write_json(dest/"BASELINE.json",original,new=True)
    rescue=Path(r"D:\AUTOFABRICADOR-RESCATE")/ROOTDIR
    rescue.mkdir(parents=True,exist_ok=True)
    write_json(rescue/"BASELINE.json",original,new=True)
    if sha_file(rescue/"BASELINE.json")!=sha_file(dest/"BASELINE.json"):
        raise RuntimeError("REBOOT_BASELINE_C_D_SHA_MISMATCH")
    return {"status":"BASELINE_PINNED_WAITING_FOR_ACTUAL_PHYSICAL_REBOOT",
            "baselineSha":sha_file(dest/"BASELINE.json"),"bootUtc":osinfo["bootUtc"],
            "originalPid":state["lease"]["pid"]}

def verify(root):
    root=engine.init(root)
    dest=_folder(root)
    if not (dest/"BASELINE.json").exists():
        return {"status":"NO_BASELINE_NO_REBOOT_PROOF"}
    before=load(dest/"BASELINE.json")
    if before["operationId"]!="AF.WIN.LOGON-REBOOT-CERTIFICATION-20261108":
        raise RuntimeError("REBOOT_BASELINE_WRONG_AUTHORITY")
    osinfo=_os()
    previous=_date(before["bootUtc"])
    now=_date(osinfo["bootUtc"])
    if osinfo["hostname"]!=before["hostname"]:
        raise RuntimeError("REBOOT_WRONG_HOST")
    if now<=previous:
        return {"status":"PENDING_REAL_WINDOWS_REBOOT_NOT_PERFORMED",
                "baselineBootUtc":before["bootUtc"],
                "currentBootUtc":osinfo["bootUtc"],
                "baselineSha":sha_file(dest/"BASELINE.json"),
                "physicalRebootVerified":False}
    task=_task()
    current=supervisor.status(root)
    if (task["name"]!=TASK or task["state"]!="Running" or task["runLevel"]!="Limited" or
        current["status"]!="RUNNING" or not current["processIdentityBirthVerified"] or
        current["pendingQueue"]!=0 or current["control"]["command"]!="RUN"):
        return {"status":"FAILED_REBOOT_ORIGINAL_TASK_OR_WORKER_NOT_RUNNING",
                "physicalRebootObserved":True,"originalWorkerRecovered":False}
    if _date(task["lastRunUtc"])<now:
        return {"status":"FAILED_NO_ORIGINAL_TASK_LAUNCH_AFTER_REBOOT","physicalRebootObserved":True}
    born=_filetime_to_datetime(current["lease"]["processBornFiletime"])
    if born<now or current["lease"]["processBornFiletime"]==before["originalWorkerProcessBorn"]:
        return {"status":"FAILED_NO_NEW_AUTHENTICATED_ORIGINAL_WORKER","physicalRebootObserved":True}
    if current["lease"]["cliSha256"]!=sha_file(root/"autofabricador.py"):
        raise RuntimeError("REBOOT_LIVE_CLI_SHA_DRIFT")
    after=_successes(root)
    if after!=before["immutableSUCCEEDEDQueues"]:
        raise RuntimeError("REBOOT_PRIOR_SUCCEEDED_QUEUE_SHA_CHANGED_NO_REPLAY")
    receipt={
       "schema":1,"atUtc":utc(),"operationId":before["operationId"],
       "status":"PASS_REAL_WINDOWS_REBOOT_USER_TASK_AND_ORIGINAL_WORKER",
       "baselineSha":sha_file(dest/"BASELINE.json"),
       "beforeBootUtc":before["bootUtc"],"afterBootUtc":osinfo["bootUtc"],
       "originalTaskLastRunUtc":task["lastRunUtc"],
       "oldWorkerPid":before["originalWorkerPid"],
       "newWorkerPid":current["lease"]["pid"],
       "newWorkerBorn":current["lease"]["processBornFiletime"],
       "oldSuccessfulQueuesUnchanged":after,
       "originalJobReplayed":False,"windowsSCMServiceInstalled":False,
       "physicalWindowsBootReadback":True,"noMMC":True,"noF":True}
    target=dest/"REBOOT-VERIFIED-READBACK.json"
    if target.exists():
        if load(target)!=receipt:
            # timestamps differ; return original committed receipt without rewrite.
            return {"status":"PREVIOUS_REBOOT_RECEIPT_EXISTS_NO_REWRITE",
                    "receiptSha":sha_file(target)}
    else:
        write_json(target,receipt,new=True)
        rescue=Path(r"D:\AUTOFABRICADOR-RESCATE")/ROOTDIR
        rescue.mkdir(parents=True,exist_ok=True)
        write_json(rescue/"REBOOT-VERIFIED-READBACK.json",receipt,new=True)
        if sha_file(target)!=sha_file(rescue/"REBOOT-VERIFIED-READBACK.json"):
            raise RuntimeError("REBOOT_RECEIPT_C_D_SHA_DRIFT")
    return {"status":receipt["status"],"physicalRebootVerified":True,
            "receiptSha":sha_file(target),"originalWorkerPid":current["lease"]["pid"]}
