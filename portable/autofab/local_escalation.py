# coding: utf-8
"""Opt-in high-quality local model from existing user Ollama GGUF bytes.

No model download, no duplicate weights, no Ollama service or global install.
Original 14B model is pinned by its SHA-256 manifest; same private llama.cpp
CPU server is bound only to 127.0.0.1:11436, launched on demand and
identity-checked before stop. 16GB RAM machine: no concurrent default server.
"""
from pathlib import Path
import json,os,subprocess,time
from .storage import load,sha_file,sha_bytes,utc,write_json,write,event,transition
from . import local_runtime
PORT=11436
ALIAS="af-qwen-coder-14b"
MODEL_SHA="ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed"
MODEL_SIZE=8988110784
def paths(root):
    root=Path(root).resolve()
    return {"model":Path.home()/".ollama/models/blobs"/("sha256-"+MODEL_SHA),
            "manifest":Path.home()/".ollama/models/manifests/registry.ollama.ai/library/qwen2.5-coder/14b",
            "exe":root/"VENDOR/llama-b12142-cpu-x64/llama-server.exe",
            "lease":root/"CONTINUIDAD/R038/ESCALATION-SERVER.json",
            "journal":root/"CONTINUIDAD/R038/ESCALATION-SERVER-JOURNAL.jsonl",
            "log":root/"logs/large-repair-server.log"}
def pinned(root):
    p=paths(root)
    original=load(p["manifest"])
    if not any(row.get("digest")=="sha256:"+MODEL_SHA for row in original.get("layers",[])):
        raise RuntimeError("ESCALED_MODEL_ORIGINAL_OLLAMA_MANIFEST_SHA_DIFFERS")
    if not p["model"].is_file() or p["model"].stat().st_size!=MODEL_SIZE:
        raise RuntimeError("ESCALED_14B_GGUF_SOURCE_SIZE_CHANGED")
    # Full SHA is calculated once and checked against the content-addressed
    # Ollama manifest; subsequent unchanged file-ID+mtime/size checks reuse
    # that ORIGINAL_SHA_VERIFIED receipt. This avoids re-reading 9GB every
    # time a small job is verified. Never label cached metadata as fresh hash.
    st=p["model"].stat()
    identity={"originalModelSha":MODEL_SHA,"originalSource":str(p["model"]),
       "bytes":st.st_size,"mtimeNs":st.st_mtime_ns,
       "ctimeNs":st.st_ctime_ns,"fileId":st.st_ino}
    receipt=Path(root).resolve()/"CONTINUIDAD/R038/14B-MODEL-SHA-CACHE.json"
    previous=load(receipt) if receipt.exists() else None
    if not (previous and previous.get("status")=="FULL_ORIGINAL_SHA_VERIFIED_CACHED_METADATA"
        and all(previous.get(key)==value for key,value in identity.items())):
        if sha_file(p["model"])!=MODEL_SHA:
            raise RuntimeError("ESCALED_14B_ORIGINAL_GGUF_SHA_MISMATCH")
        data={"schema":1,"status":"FULL_ORIGINAL_SHA_VERIFIED_CACHED_METADATA",
              "firstFullHashAtUtc":previous.get("firstFullHashAtUtc",utc()) if previous else utc(),
              "lastFullHashAtUtc":utc(),**identity}
        receipt.parent.mkdir(parents=True,exist_ok=True)
        if previous:transition(receipt,data,receipt.parent/"SHA-CACHE-HISTORY")
        else:write_json(receipt,data,new=True)
    if sha_file(p["exe"])!=local_runtime.SERVER_SHA:
        raise RuntimeError("ESCALATION_SERVER_EXE_ORIGINAL_SHA_DIFFERS")
    return p
def info(root):
    p=paths(root)
    if not p["lease"].is_file():
        return {"state":"NOT_STARTED"}
    lease=load(p["lease"])
    pid=lease["pid"]
    cmd=f"Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' | Select-Object ExecutablePath,CommandLine,ProcessId,CreationDate | ConvertTo-Json -Compress"
    try:
        out=subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,timeout=12)
        data=json.loads(out.stdout) if out.stdout.strip() else None
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return {"state":"UNKNOWN_PROCESS_QUERY", "pid":pid}
    if not data:return {"state":"EXITED","pid":pid,"lease":lease}
    line=data.get("CommandLine") or ""
    if (str(p["exe"]).casefold() not in line.casefold()
        or str(p["model"]).casefold() not in line.casefold()
        or str(PORT) not in line
        or data.get("ExecutablePath","").casefold()!=str(p["exe"]).casefold()):
        return {"state":"PID_REUSED_OR_COMMAND_DRIFT","pid":pid}
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health",timeout=3) as r:
            health=json.loads(r.read(1024))
        if health.get("status")=="ok":
            return {"state":"READY","pid":pid,"lease":lease}
    except (OSError,TimeoutError,ValueError):
        pass
    return {"state":"STARTING","pid":pid,"lease":lease}
def memory_gate(*,available=None):
    """Fail closed if Windows does not have enough available RAM for 14B.

    This is a conservative preflight, not a model-performance benchmark.
    The pinned source model occupies about 8.4 GiB and startup also needs
    operating-system, inference cache and toolchain headroom.
    """
    threshold=max(MODEL_SIZE+2*1024**3,11*1024**3)
    if available is None:
        if os.name!="nt":
            raise RuntimeError("ESCALATION_WINDOWS_RAM_QUERY_UNAVAILABLE")
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_=[("dwLength",ctypes.c_ulong),
                ("dwMemoryLoad",ctypes.c_ulong),
                ("ullTotalPhys",ctypes.c_ulonglong),
                ("ullAvailPhys",ctypes.c_ulonglong),
                ("ullTotalPageFile",ctypes.c_ulonglong),
                ("ullAvailPageFile",ctypes.c_ulonglong),
                ("ullTotalVirtual",ctypes.c_ulonglong),
                ("ullAvailVirtual",ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
        data=MemoryStatus()
        data.dwLength=ctypes.sizeof(data)
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.GlobalMemoryStatusEx.argtypes=[ctypes.POINTER(MemoryStatus)]
        kernel.GlobalMemoryStatusEx.restype=ctypes.c_int
        if not kernel.GlobalMemoryStatusEx(ctypes.byref(data)):
            raise RuntimeError("ESCALATION_RAM_QUERY_FAILED")
        available=int(data.ullAvailPhys)
    if type(available) is not int or available<0:
        raise ValueError("ESCALATION_RAM_READING_INVALID")
    if available<threshold:
        raise RuntimeError("ESCALATION_14B_INSUFFICIENT_FREE_RAM_NO_SPAWN")
    return {"status":"ESCALATION_RAM_PREFLIGHT_PASS",
            "availableBytes":available,"minimumBytes":threshold}

def start(root):
    # Deliberately before model SHA scan, lease creation or process spawn.
    memory_gate()
    p=pinned(root)
    if p["lease"].exists():
        live=info(root)
        if live["state"] in ("READY","STARTING"):
            return live
        raise RuntimeError("ESCALATION_ORIGINAL_LEASE_UNRECONCILED:"+live["state"])
    default=local_runtime.server_info(root)
    if default["state"]!="NOT_STARTED":
        raise RuntimeError("DONT_RUN_1_5B_AND_14B_CONCURRENTLY")
    intent={"schema":1,"atUtc":utc(),"operationId":"AF.R038.LOCAL_QWEN14B_ESCALATION_1",
            "modelOriginalSha":MODEL_SHA,"originalGGUFBytes":MODEL_SIZE,
            "modelSourceLocation":str(p["model"]),
            "downloadedExtraModel":False,"port":PORT,
            "originalServerSha":local_runtime.SERVER_SHA,
            "sandbox":"Source-only generation, output WASI owner tests"}
    path=p["lease"].parent
    path.mkdir(parents=True,exist_ok=True)
    write_json(path/"ESCALATION-START-INTENT.json",intent,new=True)
    args=[str(p["exe"]),"--model",str(p["model"]),"--alias",ALIAS,
          "--host","127.0.0.1","--port",str(PORT),
          "--ctx-size","6144","--threads","5",
          "--threads-batch","5","--gpu-layers","0",
          "--no-webui","--offline","--no-warmup"]
    p["log"].parent.mkdir(parents=True,exist_ok=True)
    with p["log"].open("ab") as out:
        flags=(getattr(subprocess,"CREATE_NO_WINDOW",0)|
               getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))
        proc=subprocess.Popen(args,cwd=str(p["exe"].parent),stdin=subprocess.DEVNULL,
              stdout=out,stderr=subprocess.STDOUT,creationflags=flags)
    lease={"schema":1,"pid":proc.pid,"atUtc":utc(),
           "exe":str(p["exe"]),"exeSha":local_runtime.SERVER_SHA,
           "model":str(p["model"]),"modelSha":MODEL_SHA,
           "port":PORT,"alias":ALIAS}
    write_json(p["lease"],lease,new=True)
    event(p["journal"],"STARTED",{"pid":proc.pid,"modelSha":MODEL_SHA})
    for _ in range(80):
        result=info(root)
        if result["state"]=="READY":return result
        if result["state"] not in ("READY","STARTING"):return result
        time.sleep(.7)
    return {"state":"STARTING_NOT_READY","pid":proc.pid}
def stop(root):
    p=paths(root)
    live=info(root)
    if live["state"]=="NOT_STARTED":return live
    if live["state"]=="EXITED":
        pre=p["lease"].read_bytes()
        archived=p["lease"].parent/("ESCALATION-STOPPED-"+str(live["pid"])+".json")
        if not archived.exists():write(archived,pre,new=True)
        p["lease"].unlink()
        event(p["journal"],"RECONCILED_EXITED",{"pid":live["pid"],"preimageSha":sha_bytes(pre)})
        return {"state":"STOPPED_RECONCILED","pid":live["pid"]}
    if live["state"] not in ("READY","STARTING"):
        raise RuntimeError("ESCALATION_PID_IDENTITY_NOT_SAFE_TO_STOP:"+live["state"])
    pid=live["pid"]
    proc=subprocess.run(["taskkill","/PID",str(pid),"/T","/F"],
                         capture_output=True,text=True,timeout=20)
    if proc.returncode:raise RuntimeError("ESCALATION_KILL_FAILED:"+proc.stderr[:300])
    checked=info(root)
    for _ in range(12):
        if checked["state"]=="EXITED":break
        time.sleep(.25);checked=info(root)
    if checked["state"]!="EXITED":
        raise RuntimeError("ESCALATION_STOP_PROCESS_READBACK_UNKNOWN")
    original=p["lease"].read_bytes()
    archived=p["lease"].parent/("ESCALATION-STOPPED-"+str(pid)+".json")
    write(archived,original,new=True)
    p["lease"].unlink()
    event(p["journal"],"STOPPED",{"pid":pid,"preimageSha":sha_bytes(original)})
    return {"state":"STOPPED","pid":pid}
