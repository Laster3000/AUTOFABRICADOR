# coding: utf-8
"""Internal on-demand CUDA7B provider for ORIGINAL AUTOFABRICADOR supervisor.

Local model only. Original job/queue/WASI/package flows remain original owners.
Lease PID+Windows creation time identity; no arbitrary shell, autostart, OS service.
"""
from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

from .storage import load, sha_file, sha_bytes, utc, write_json, write, event

PORT=11479
ALIAS="r69-qwen35-9b"
MODEL_SHA="03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8"
SERVER_SHA="e3009ccf4f0623c73d25db49f9f8bdcfd387b053c30adc89d9f48b2f9e88e3f6"
CUDA_SHA="d0dd084481b7456d6d9e84269a956f24eb39a4a9e9c27b937fe4b288be1b1865"
MODEL_SIZE=5680522464
BACKEND_MANIFEST_SHA="1f9255ec205dea8e2cfab37ad3a295da712d1fe5579e091f96de266149a560cd"
MIN_RAM_TO_START_MIB=7200
MIN_VRAM_TO_START_MIB=8500
MIN_RAM_LOADING_MIB=1350
MIN_VRAM_LOADING_MIB=220

def paths(root):
    r=Path(root).resolve()
    return {"root":r,"model":r/"VENDOR/models/Qwen3.5-9B-Unsloth-Q4_K_M-R69.gguf",
            "exe":r/"VENDOR/llama-b12202-cuda-12.4-x64/llama-server.exe",
            "cuda":r/"VENDOR/llama-b12202-cuda-12.4-x64/ggml-cuda.dll",
            "manifest":r/"VENDOR/llama-b12202-cuda-12.4-x64/INSTALL-MANIFEST.json",
            "lease":r/"CONTINUIDAD/LOCAL-GPU-QWEN35-9B-SERVER.json",
            "journal":r/"CONTINUIDAD/R69-QWEN35-BACKEND-20261108/QWEN35-9B-ORIGINAL-JOURNAL.jsonl",
            "archive":r/"CONTINUIDAD/R69-QWEN35-BACKEND-20261108/GPU-LEASE-HISTORY",
            "logs":r/"logs"}

def pinned_assets(root):
    p=paths(root)
    for k,expected in (("model",MODEL_SHA),("exe",SERVER_SHA),
                       ("cuda",CUDA_SHA),("manifest",BACKEND_MANIFEST_SHA)):
        if not p[k].is_file() or p[k].is_symlink():
            raise RuntimeError("QWEN35_9B_PINNED_FILE_MISSING:"+k)
        if k=="model" and p[k].stat().st_size!=MODEL_SIZE:
            raise RuntimeError("QWEN35_9B_MODEL_BYTES_CHANGED")
        if sha_file(p[k])!=expected:
            raise RuntimeError("QWEN35_9B_SHA_DRIFT:"+k)
    return p

def _ram():
    class M(ctypes.Structure):
        _fields_=[("length",ctypes.c_ulong),("load",ctypes.c_ulong),
            ("total",ctypes.c_ulonglong),("avail",ctypes.c_ulonglong),
            ("pgtotal",ctypes.c_ulonglong),("pgavail",ctypes.c_ulonglong),
            ("virtual",ctypes.c_ulonglong),("vavail",ctypes.c_ulonglong),
            ("extended",ctypes.c_ulonglong)]
    m=M();m.length=ctypes.sizeof(M)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        raise RuntimeError("QWEN35_9B_WIN_MEMORY_QUERY_FAILED")
    return int(m.avail//1048576)

def _vram():
    result=subprocess.run(["nvidia-smi",
        "--query-gpu=memory.used,memory.free",
        "--format=csv,noheader,nounits"],
        text=True,capture_output=True,timeout=12)
    if result.returncode:raise RuntimeError("QWEN35_9B_GPU_METRICS_UNAVAILABLE")
    cols=[int(v.strip()) for v in result.stdout.strip().splitlines()[0].split(",")]
    if len(cols)!=2:raise RuntimeError("QWEN35_9B_GPU_METRICS_INVALID")
    return {"usedMiB":cols[0],"freeMiB":cols[1]}

def preflight(root):
    p=pinned_assets(root)
    ram=_ram()
    gpu=_vram()
    if ram<MIN_RAM_TO_START_MIB or gpu["freeMiB"]<MIN_VRAM_TO_START_MIB:
        raise RuntimeError("QWEN35_9B_INSUFFICIENT_MEMORY_NO_START")
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        if s.connect_ex(("127.0.0.1",PORT))==0:
            raise RuntimeError("QWEN35_9B_PORT_ALREADY_LISTENING_NO_START")
    return {"state":"PREFLIGHT_PASS","ramFreeMiB":ram,"gpu":gpu,
            "backendSha":sha_file(p["manifest"]),"modelSha":MODEL_SHA}

def _pid_born(pid):
    from . import supervisor
    return supervisor.process_born(pid)

def server_info(root):
    p=paths(root)
    if not p["lease"].is_file():return {"state":"NOT_STARTED"}
    lease=load(p["lease"])
    pid=lease.get("pid")
    if type(pid) is not int or pid<=0:return {"state":"UNKNOWN_BAD_LEASE"}
    birth=_pid_born(pid)
    if birth is None:return {"state":"EXITED","pid":pid,"lease":lease}
    if birth!=lease.get("processBornFiletime"):
        return {"state":"PID_REUSED_OR_BIRTH_DIFFERENT","pid":pid}
    command=("Get-CimInstance Win32_Process -Filter 'ProcessId = "+str(pid)+
             "' | Select-Object ExecutablePath,CommandLine,ProcessId | ConvertTo-Json -Compress")
    try:
        result=subprocess.run(["powershell","-NoProfile","-NonInteractive","-Command",command],
                              capture_output=True,text=True,timeout=12)
        data=json.loads(result.stdout) if result.returncode==0 and result.stdout.strip() else None
    except Exception:
        return {"state":"UNKNOWN_PROCESS_IDENTITY","pid":pid}
    if not isinstance(data,dict):return {"state":"UNKNOWN_PROCESS_IDENTITY","pid":pid}
    exe=(data.get("ExecutablePath") or "").casefold()
    line=(data.get("CommandLine") or "").casefold()
    if (exe!=str(p["exe"]).casefold() or str(p["model"]).casefold() not in line
        or str(PORT) not in line or ALIAS.casefold() not in line):
        return {"state":"PID_REUSED_OR_COMMAND_DRIFT","pid":pid}
    try:
        with urllib.request.urlopen("http://127.0.0.1:"+str(PORT)+"/health",timeout=2) as f:
            status=json.loads(f.read(2048))
        if status.get("status")=="ok":
            return {"state":"READY","pid":pid,"lease":lease}
    except Exception:
        pass
    return {"state":"STARTING","pid":pid,"lease":lease}

def start(root):
    p=paths(root)
    if p["lease"].exists():
        old=server_info(root)
        if old["state"] in ("READY","STARTING"):return old
        raise RuntimeError("QWEN35_9B_EXISTING_LEASE_RECONCILE_REQUIRED:"+old["state"])
    from . import local_runtime, local_escalation, local_cuda7b
    for name,status in (("small",local_runtime.server_info(root)),
                        ("14b",local_escalation.info(root)),
                        ("7b",local_cuda7b.server_info(root))):
        if status["state"]!="NOT_STARTED":
            raise RuntimeError("QWEN35_9B_OTHER_MODEL_LEASE_BLOCKS_START:"+name+":"+status["state"])
    before=preflight(root)
    p["logs"].mkdir(parents=True,exist_ok=True)
    p["archive"].mkdir(parents=True,exist_ok=True)
    p["journal"].parent.mkdir(parents=True,exist_ok=True)
    intent={"schema":1,"operationId":"AF.GPU.QWEN35_9B.ORIGINAL-R69",
            "atUtc":utc(),"preflight":before,"modelSha":MODEL_SHA,
            "cudaSha":CUDA_SHA,"binarySha":SERVER_SHA,
            "localOnly":True,"owner":"original-repo-factory"}
    intent_file=p["archive"]/("START-INTENT-"+__import__("uuid").uuid4().hex+".json")
    write_json(intent_file,intent,new=True)
    args=[str(p["exe"]),"--model",str(p["model"]),"--alias",ALIAS,
          "--host","127.0.0.1","--port",str(PORT),
          "--ctx-size","4096","--threads","4","--threads-batch","4",
          "--parallel","1","--batch-size","64","--ubatch-size","32",
          "--gpu-layers","99","--reasoning","off","--no-webui","--offline","--no-warmup"]
    logpath=p["logs"]/("qwen35-9b-local-"+__import__("uuid").uuid4().hex[:12]+".log")
    with logpath.open("xb") as log:
        proc=subprocess.Popen(args,cwd=p["exe"].parent,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1",
                 "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"},
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    birth=None
    for _ in range(12):
        birth=_pid_born(proc.pid)
        if birth is not None:break
        if proc.poll() is not None:break
        time.sleep(.08)
    if birth is None:
        # Unknown spawn identity: do not kill arbitrary PID.
        event(p["journal"],"UNKNOWN_SPAWN_BIRTH",
              {"pid":proc.pid,"intentSha":sha_file(intent_file)})
        raise RuntimeError("QWEN35_9B_PROCESS_BIRTH_UNKNOWN_RECONCILE")
    lease={"schema":1,"operationId":intent["operationId"],"pid":proc.pid,
           "processBornFiletime":birth,"port":PORT,"alias":ALIAS,
           "modelSha256":MODEL_SHA,"serverSha256":SERVER_SHA,
           "startedUtc":utc(),"intentSha":sha_file(intent_file),
           "log":str(logpath)}
    write_json(p["lease"],lease,new=True)
    event(p["journal"],"CHILD_STARTED",{"pid":proc.pid,"born":birth,
                                        "leaseSha":sha_file(p["lease"])})
    for i in range(110):
        current=server_info(root)
        if current["state"]=="READY":
            event(p["journal"],"CHILD_READY",{"pid":proc.pid,
                     "gpuFreeMiB":_vram()["freeMiB"],"ramFreeMiB":_ram()})
            return current
        if current["state"] not in ("STARTING","READY"):
            event(p["journal"],"CHILD_NOT_READY",
                  {"status":current["state"],"pid":proc.pid})
            # Process may already have exited; only reconcile own lease.
            if current["state"]=="EXITED":stop(root)
            raise RuntimeError("QWEN35_9B_SERVER_NOT_READY:"+current["state"])
        if _ram()<MIN_RAM_LOADING_MIB or _vram()["freeMiB"]<MIN_VRAM_LOADING_MIB:
            event(p["journal"],"MEMORY_SAFETY_STOP",{"pid":proc.pid})
            stop(root)
            raise RuntimeError("QWEN35_9B_MEMORY_FLOOR_DURING_LOADING")
        time.sleep(.8)
    event(p["journal"],"UNKNOWN_START_TIMEOUT",{"pid":proc.pid})
    # A live READY process is not necessarily proven. Stop only after identity.
    stop(root)
    raise RuntimeError("QWEN35_9B_LOAD_TIMEOUT_STAGING_STOPPED")

def stop(root):
    p=paths(root)
    info=server_info(root)
    if info["state"]=="NOT_STARTED":return info
    if info["state"] not in ("READY","STARTING","EXITED"):
        raise RuntimeError("QWEN35_9B_UNSAFE_STOP_UNKNOWN_IDENTITY:"+info["state"])
    pid=info["pid"]
    if info["state"]!="EXITED":
        proc=subprocess.run(["taskkill","/PID",str(pid),"/T","/F"],
             capture_output=True,text=True,timeout=20)
        if proc.returncode!=0:raise RuntimeError("QWEN35_9B_STOP_FAILED:"+proc.stderr[:180])
        for _ in range(15):
            if server_info(root)["state"]=="EXITED":break
            time.sleep(.25)
        if server_info(root)["state"]!="EXITED":
            raise RuntimeError("QWEN35_9B_STOP_READBACK_UNCERTAIN")
    data=p["lease"].read_bytes()
    before=sha_bytes(data)
    p["archive"].mkdir(parents=True,exist_ok=True)
    archived=p["archive"]/("STOP-"+str(pid)+"-"+before[:12]+".json")
    if archived.exists():
        if sha_file(archived)!=before:raise RuntimeError("QWEN35_9B_ARCHIVE_COLLISION")
    else:write(archived,data,new=True)
    p["lease"].unlink()
    event(p["journal"],"CHILD_STOPPED",{"pid":pid,"preimageSha":before})
    return {"state":"STOPPED_VERIFIED","pid":pid,"leaseSha":before}
