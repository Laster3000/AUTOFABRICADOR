# coding: utf-8
"""Project-only llama.cpp server lifecycle. No Windows service, PATH, or privileges."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid
import urllib.error
import urllib.request
from .storage import load, sha_file, utc, write_json, transition, event

SERVER_SHA = "adf06772b919f299d71656b481736544752657b5266fd484744b7db08e3665c2"
MODEL_SHA = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
ALIAS = "af-qwen-coder-1.5b"
PORT = 11435

def paths(root):
    root=Path(root).resolve()
    return {
        "exe":root/"VENDOR"/"llama-b12142-cpu-x64"/"llama-server.exe",
        "model":root/"VENDOR"/"models"/"qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "lease":root/"CONTINUIDAD"/"LOCAL-SERVER.json",
        "history":root/"CONTINUIDAD"/"R023",
        "logs":root/"logs"
    }

def pinned_assets(root):
    p=paths(root)
    for name,sha in (("exe",SERVER_SHA),("model",MODEL_SHA)):
        if not p[name].is_file():raise RuntimeError(f"LOCAL_{name.upper()}_NOT_FOUND")
        if sha_file(p[name])!=sha:raise RuntimeError(f"LOCAL_{name.upper()}_SHA_DRIFT")
    return p

def server_info(root):
    p=paths(root)
    if not p["lease"].is_file():return {"state":"NOT_STARTED"}
    lease=load(p["lease"])
    pid=lease.get("pid")
    if not isinstance(pid,int) or pid<=0:raise RuntimeError("LEASE_PID_INVALID")
    cmd=["powershell","-NoProfile","-Command",
         f"Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' | Select-Object ExecutablePath,CommandLine,ProcessId | ConvertTo-Json -Compress"]
    try:
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
        result=json.loads(proc.stdout) if proc.stdout.strip() and proc.stdout.strip()!="null" else None
    except (ValueError,subprocess.TimeoutExpired) as err:
        return {"state":"PROCESS_IDENTITY_UNKNOWN","pid":pid,"error":str(err)[:200]}
    if not result:return {"state":"EXITED","pid":pid,"lease":lease}
    fullpath=(result.get("ExecutablePath") or "").casefold()
    expected=str(p["exe"]).casefold()
    command=(result.get("CommandLine") or "").casefold()
    if fullpath!=expected or str(PORT) not in command or str(p["model"]).casefold() not in command:
        return {"state":"PID_REUSED_OR_COMMAND_DRIFT","pid":pid}
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health",timeout=3) as response:
            health=json.loads(response.read(1000))
        return {"state":"READY" if health.get("status")=="ok" else "STARTING",
                "pid":pid,"health":health,"lease":lease}
    except (OSError,TimeoutError,ValueError,urllib.error.HTTPError):
        return {"state":"STARTING","pid":pid,"lease":lease}

def start(root):
    p=pinned_assets(root)
    p["logs"].mkdir(parents=True,exist_ok=True)
    p["history"].mkdir(parents=True,exist_ok=True)
    if p["lease"].exists():
        status=server_info(root)
        if status["state"] in ("READY","STARTING"):
            return status
        raise RuntimeError("EXISTING_SERVER_LEASE_REQUIRES_RECONCILIATION:"+status["state"])
    intent={"operationId":"AF.R023.LLAMACPP.SERVE.ONDEMAND","atUtc":utc(),"bind":"127.0.0.1",
            "port":PORT,"exeSha":SERVER_SHA,"modelSha":MODEL_SHA}
    # Persistent intent and no replay on unknown.
    write_json(p["history"]/("SERVER-START-INTENT-"+uuid.uuid4().hex+".json"),intent,new=True)
    args=[str(p["exe"]),"--model",str(p["model"]),"--alias",ALIAS,
          "--host","127.0.0.1","--port",str(PORT),
          "--ctx-size","12288","--threads","3",
          "--threads-batch","3","--gpu-layers","0",
          "--no-webui","--offline","--no-warmup"]
    stdout=p["logs"]/"local-model.stdout.log"
    stderr=p["logs"]/"local-model.stderr.log"
    with stdout.open("ab") as out,stderr.open("ab") as err:
        flags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
        proc=subprocess.Popen(args,cwd=p["exe"].parent,stdout=out,stderr=err,
                              stdin=subprocess.DEVNULL,creationflags=flags)
    lease={"schema":1,"pid":proc.pid,"launchedUtc":utc(),"exe":str(p["exe"]),
           "exeSha256":SERVER_SHA,"model":str(p["model"]),"modelSha256":MODEL_SHA,
           "port":PORT,"alias":ALIAS,"launcher":"C:\\AUTOFABRICADOR\\autofab\\local_runtime.py"}
    write_json(p["lease"],lease,new=True)
    event(p["history"]/"local-server-journal.jsonl","LAUNCHED",{"pid":proc.pid,"exeSha256":SERVER_SHA,"modelSha256":MODEL_SHA})
    for _ in range(30):
        status=server_info(root)
        if status["state"]=="READY":return status
        if status["state"] not in ("STARTING","READY"):return status
        time.sleep(1)
    return {"state":"STARTING_NOT_YET_READY","pid":proc.pid}

def stop(root):
    p=paths(root)
    status=server_info(root)
    if status["state"]=="NOT_STARTED":return status
    if status["state"]=="EXITED":
        from .storage import sha_bytes, write
        old=p["lease"].read_bytes()
        history=p["history"]/(f"LOCAL-SERVER-STOPPED-{status['pid']}-{sha_bytes(old)[:16]}.json")
        if not history.exists():
            write(history,old,new=True)
        elif sha_file(history)!=sha_bytes(old):
            raise RuntimeError("STOPPED_LEASE_SHA_COLLISION_UNKNOWN")
        p["lease"].unlink()
        event(p["history"]/'local-server-journal.jsonl',"RECONCILED_ALREADY_EXITED",{"pid":status['pid'],"leaseSha256":sha_bytes(old)})
        return {"state":"STOPPED_RECONCILED","pid":status['pid'],"leaseSha256":sha_bytes(old)}
    if status["state"] not in ("READY","STARTING","STARTING_NOT_YET_READY"):
        raise RuntimeError("UNSAFE_TO_STOP_NONIDENTICAL_PROCESS:"+status["state"])
    pid=status["pid"]
    action=subprocess.run(["taskkill","/PID",str(pid),"/T","/F"],capture_output=True,text=True,timeout=15)
    if action.returncode!=0:raise RuntimeError("SERVER_STOP_FAILED:"+action.stderr[:200])
    previous=p["lease"].read_bytes()
    from .storage import sha_bytes, write
    readback=server_info(root)
    for _ in range(8):
        if readback["state"]=="EXITED":break
        time.sleep(0.3)
        readback=server_info(root)
    if readback["state"]!="EXITED":
        raise RuntimeError("STOP_READBACK_NOT_EXITED:"+readback["state"])
    history=p["history"]/(f"LOCAL-SERVER-STOPPED-{pid}-{sha_bytes(previous)[:16]}.json")
    if not history.exists():
        write(history,previous,new=True)
    elif sha_file(history)!=sha_bytes(previous):
        raise RuntimeError("STOPPED_LEASE_SHA_COLLISION_UNKNOWN")
    # Move lease into record only after proving stopped.
    p["lease"].unlink()
    event(p["history"]/"local-server-journal.jsonl","STOPPED",{"pid":pid,"leaseSha256":sha_bytes(previous)})
    return {"state":"STOPPED","pid":pid,"leaseSha256":sha_bytes(previous)}
