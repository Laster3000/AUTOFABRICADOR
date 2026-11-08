"""Pinned project-only dependencies installer. Use CLI bootstrap on a fresh copy."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
import zipfile

from .storage import load, sha_file, utc, write_json

def _download(root,dep):
    url=urllib.parse.urlparse(dep["url"])
    if url.scheme!="https" or url.hostname not in ("github.com","huggingface.co","files.pythonhosted.org"):
        raise RuntimeError("UNTRUSTED_DEPENDENCY_HOST")
    rel=Path(dep["dest"])
    if rel.is_absolute() or ".." in rel.parts or rel.parts[0]!="VENDOR":
        raise RuntimeError("DEPENDENCY_PATH_INVALID")
    target=root/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.stat().st_size!=dep["size"] or sha_file(target)!=dep["sha256"]:
            raise RuntimeError("EXISTING_DEPENDENCY_SHA_DRIFT")
        return
    if list(target.parent.glob(target.name+".PART.*")):
        raise RuntimeError("PRIOR_UNKNOWN_PARTIAL_DOWNLOAD")
    part=target.with_name(target.name+".PART."+uuid.uuid4().hex)
    try:
        req=urllib.request.Request(dep["url"],headers={"User-Agent":"AUTOFABRICADOR-BOOTSTRAP"})
        h=hashlib.sha256()
        size=0
        with urllib.request.urlopen(req,timeout=50) as response,part.open("xb") as f:
            while block:=response.read(1024*1024):
                size+=len(block)
                if size>dep["size"]:raise RuntimeError("DOWNLOAD_SIZE_OVERFLOW")
                h.update(block);f.write(block)
            f.flush();os.fsync(f.fileno())
        if size!=dep["size"] or h.hexdigest()!=dep["sha256"]:
            raise RuntimeError("DEPENDENCY_SHA_OR_SIZE_MISMATCH")
        os.replace(part,target)
        if sha_file(target)!=dep["sha256"]:raise RuntimeError("DEPENDENCY_READBACK_FAILED")
    except Exception:
        # Keep partial evidence, do not blindly replay.
        raise

def _unpack(root):
    folder=root/"VENDOR"/"llama-b12142-cpu-x64"
    if folder.exists():
        if not (folder/"llama-server.exe").is_file():raise RuntimeError("INCOMPLETE_VENDOR_TREE")
        return
    archive=root/"VENDOR"/"llama-b12142-bin-win-cpu-x64.zip"
    stage=folder.with_name(folder.name+".STAGE."+uuid.uuid4().hex)
    stage.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        total=0
        for x in z.infolist():
            pp=PurePosixPath(x.filename)
            if pp.is_absolute() or ".." in pp.parts or "\\" in x.filename or ":" in x.filename or stat.S_ISLNK((x.external_attr>>16)&0xffff):
                raise RuntimeError("ZIP_EXTRACTION_UNSAFE")
            total+=x.file_size
            if total>300000000:raise RuntimeError("ZIP_EXPANSION_OVER_LIMIT")
        z.extractall(stage)
    if not (stage/"llama-server.exe").is_file():raise RuntimeError("VENDOR_LAYOUT_UNKNOWN")
    os.replace(stage,folder)

def _wasi_install(root):
    target=root/"VENDOR"/"wasi-runtime"
    if target.exists():
        if not (target/"wasi_python"/"__init__.py").is_file():raise RuntimeError("WASI_RUNTIME_INCOMPLETE")
        return
    stage=target.with_name(target.name+".STAGE."+uuid.uuid4().hex)
    stage.mkdir(parents=True,exist_ok=False)
    cmd=[sys.executable,"-m","pip","install","--no-index","--no-deps","--no-cache-dir",
         "--disable-pip-version-check","--no-warn-script-location",
         "--find-links",str(root/"VENDOR"/"wheels"),"--target",str(stage),
         "wasi-python==0.1.4","wasmtime==50.0.1"]
    proc=subprocess.run(cmd,stdin=subprocess.DEVNULL,capture_output=True,timeout=180)
    if proc.returncode:raise RuntimeError("PROJECT_ONLY_WASI_PIP_FAILED:"+proc.stderr.decode("utf-8","replace")[-400:])
    os.replace(stage,target)

def _negative(root):
    vendor=root/"VENDOR"/"wasi-runtime"
    if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
    from wasi_python import run
    code=(
        "import json,socket,subprocess\n"
        "r={}\n"
        "for name,path in [('root','/workspace/README.md'),('drive',r'C:\\AUTOFABRICADOR\\README.md'),('user',r'C:\\Users\\laste\\.ollama\\server.json')]:\n"
        " try: open(path,'rb').read(1);r[name]='ACCESS_GRANTED'\n"
        " except Exception as e:r[name]=type(e).__name__\n"
        "try:socket.socket().connect(('127.0.0.1',11435));r['network']='ACCESS_GRANTED'\n"
        "except Exception as e:r['network']=type(e).__name__\n"
        "try:subprocess.run(['cmd','/c','echo','bad']);r['process']='ACCESS_GRANTED'\n"
        "except Exception as e:r['process']=type(e).__name__\n"
        "print('NEGATIVE='+json.dumps(r,sort_keys=True))\n"
    )
    result=run(["-c",code],root=False,grants=(),mounts=(),host=None,tools=None,
               deadline_s=25,memory_bytes=536870912,output_bytes=16000,
               fuel=500000000,cache_dir=str(root/"VENDOR"/"wasi-cache"))
    lines=result.stdout.decode("utf-8","replace").splitlines()
    marks=[l for l in lines if l.startswith("NEGATIVE=")]
    if result.exit_code!=0 or result.trapped is not None or len(marks)!=1:
        raise RuntimeError("WASI_NEGATIVE_TEST_NOT_PROVEN")
    cases=json.loads(marks[0].split("=",1)[1])
    if len(cases)!=5 or "ACCESS_GRANTED" in cases.values():
        raise RuntimeError("WASI_ISOLATION_NEGATIVE_FAILED:"+str(cases))
    return {"atUtc":utc(),"status":"NEGATIVE_ISOLATION_TESTS_PASS","negativeCases":cases,
            "fuelUsed":result.fuel_used}

def bootstrap(root):
    root=Path(root).resolve()
    lock=load(root/"DEPENDENCIES.lock.json")
    if lock.get("schema")!=1 or lock.get("product")!="AUTOFABRICADOR" or len(lock.get("deps",[]))!=4:
        raise RuntimeError("INVALID_DEPENDENCY_LOCK")
    for dep in lock["deps"]:_download(root,dep)
    _unpack(root)
    _wasi_install(root)
    receipts=root/"CONTINUIDAD"/"R023"
    receipts.mkdir(parents=True,exist_ok=True)
    negative=receipts/"WASI-ISOLATION-RECEIPT.json"
    if not negative.exists():write_json(negative,_negative(root),new=True)
    from .wasi_isolation import WASI_INIT_SHA,WASMTIME_INIT_SHA,wasi_preflight
    vendor=root/"VENDOR"/"wasi-runtime"
    if sha_file(vendor/"wasi_python"/"__init__.py")!=WASI_INIT_SHA or sha_file(vendor/"wasmtime"/"__init__.py")!=WASMTIME_INIT_SHA:
        raise RuntimeError("RUNTIME_SHA_DRIFT")
    installed=receipts/"WASI-INSTALL-RECEIPT.json"
    if not installed.exists():
        write_json(installed,{"status":"WASI_PORTABLE_INSTALLED_SHA_VERIFIED",
                             "target":str(vendor),"atUtc":utc()},new=True)
    from .local_runtime import MODEL_SHA, SERVER_SHA
    if sha_file(root/"VENDOR"/"llama-b12142-cpu-x64"/"llama-server.exe")!=SERVER_SHA:
        raise RuntimeError("LLAMA_SERVER_SHA_DRIFT")
    if sha_file(root/"VENDOR"/"models"/"qwen2.5-coder-1.5b-instruct-q4_k_m.gguf")!=MODEL_SHA:
        raise RuntimeError("LLAMA_MODEL_SHA_DRIFT")
    result={"status":"PROJECT_DEPENDENCIES_VERIFIED","atUtc":utc(),
            "root":str(root),"lockSha256":sha_file(root/"DEPENDENCIES.lock.json"),
            "runner":wasi_preflight(root),"hostProtectedChanges":False}
    receipt=receipts/"BOOTSTRAP-COMPLETE.json"
    if not receipt.exists():write_json(receipt,result,new=True)
    return result
