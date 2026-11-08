# coding: utf-8
"""Rehydrate R035 pinned JS npm UMD and C# WASI toolchains privately.

Not a Windows installer/service. Third-party MSBuild toolchains execute only
when explicitly requested and trusted, never from model-provided csproj.
"""
from __future__ import annotations
import base64,gzip,hashlib,io,json,os
from pathlib import Path
import shutil,subprocess,tarfile,urllib.request,uuid,zipfile
from . import engine,csharp_wasi,npm_umd
from .storage import load,sha_file,utc,write_json

WASMTIME_URL="https://github.com/bytecodealliance/wasmtime/releases/download/v50.0.1/wasmtime-v50.0.1-x86_64-windows.zip"
WASMTIME_ZIP_SHA="c3646ee2de8cfcefe532e75852e1fd2728d78c3fcc43251794803a698d1c30ca"

def _fetch(url,dest,max_bytes,sha):
    if dest.exists():
        if sha_file(dest)!=sha:raise RuntimeError("EXISTING_PINNED_ARCHIVE_SHA_DRIFT")
        return "ALREADY_PRESENT"
    if any(dest.parent.glob(dest.name+".PART.*")):
        raise RuntimeError("UNFINISHED_DOWNLOAD_EXISTS_RECONCILE_NO_BLIND_RETRY")
    stage=dest.with_name(dest.name+".PART."+uuid.uuid4().hex[:12])
    request=urllib.request.Request(url,headers={"User-Agent":"AUTOFABRICADOR-PINNED-R035"})
    size=0
    with urllib.request.urlopen(request,timeout=60) as response,stage.open("xb") as out:
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            size+=len(chunk)
            if size>max_bytes:raise RuntimeError("PINNED_DEPENDENCY_SIZE_CAP_EXCEEDED")
            out.write(chunk)
        out.flush();os.fsync(out.fileno())
    if sha_file(stage)!=sha:raise RuntimeError("DOWNLOADED_DEPENDENCY_SHA_DRIFT")
    os.replace(stage,dest)
    return "DOWNLOADED_AND_SHA_VERIFIED"

def _wasmtime(root):
    vendor=root/"VENDOR/wasmtime-cli-50.0.1"
    vendor.mkdir(parents=True,exist_ok=True)
    archive=vendor/"wasmtime-v50.0.1-x86_64-windows.zip"
    _fetch(WASMTIME_URL,archive,30*1024*1024,WASMTIME_ZIP_SHA)
    exe=vendor/"wasmtime.exe"
    with zipfile.ZipFile(archive) as a:
        names=[n for n in a.namelist() if n.endswith("/wasmtime.exe") or n=="wasmtime.exe"]
        if len(names)!=1 or ".." in names[0].split("/"):
            raise RuntimeError("WASMTIME_ZIP_MEMBER_UNSAFE")
        content=a.read(names[0])
    if hashlib.sha256(content).hexdigest()!=csharp_wasi.WASMTIME_SHA:
        raise RuntimeError("WASMTIME_EXTRACTED_EXE_SHA_DRIFT")
    if not exe.exists():
        with exe.open("xb") as out:out.write(content);out.flush();os.fsync(out.fileno())
    if sha_file(exe)!=csharp_wasi.WASMTIME_SHA:
        raise RuntimeError("WASMTIME_INSTALLED_EXE_SHA_DRIFT")
    return {"wasmtimeCliSha256":sha_file(exe),
            "archiveSha256":sha_file(archive)}

def _npm_umd(root):
    manifest=load(root/"NPM-UMD.lock.json")
    receipts=[]
    for row in manifest["packages"]:
        if row["name"] not in npm_umd.ALLOW or row["scriptExecution"] is not False:
            raise RuntimeError("NPM_UNPINNED_OR_LIFECYCLE_SCRIPT")
        path=(root/row["relativeFile"]).resolve()
        if not path.is_relative_to(root/"VENDOR/npm-pin"):
            raise RuntimeError("NPM_VENDOR_PATH_OUTSIDE_ROOT")
        archive=root/"VENDOR/npm-pin/archives"/(row["name"]+"-"+row["version"]+".tgz")
        archive.parent.mkdir(parents=True,exist_ok=True)
        _fetch(row["registryTarball"],archive,8*1024*1024,row["tarballSha256"])
        raw=archive.read_bytes()
        sri="sha512-"+base64.b64encode(hashlib.sha512(raw).digest()).decode()
        if sri!=row["registrySRI"]:raise RuntimeError("NPM_PACKAGE_SRI_MISMATCH")
        with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as a:
            original="package/"+path.name
            member=a.getmember(original)
            if not member.isfile() or member.size>400000:
                raise RuntimeError("NPM_UMD_ARCHIVE_SOURCE_UNSAFE")
            js=a.extractfile(member).read()
        if hashlib.sha256(js).hexdigest()!=row["fileSha256"]:
            raise RuntimeError("NPM_UMD_SOURCE_SHA_MISMATCH")
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with path.open("xb") as out:out.write(js);out.flush();os.fsync(out.fileno())
        if sha_file(path)!=row["fileSha256"]:
            raise RuntimeError("NPM_UMD_SOURCE_DISK_SHA_DRIFT")
        receipts.append({"name":row["name"],"version":row["version"],"sha256":sha_file(path)})
    npm_umd.preflight(root,[r["name"] for r in receipts])
    return receipts

def _componentize(root):
    lab=root/"LAB-CSHARP-WASI-R035"
    project=lab/"WasiProbe.csproj"
    if not project.is_file() or not (lab/"NuGet.Config").is_file():
        raise RuntimeError("TRUSTED_CSHARP_WASI_BOOTSTRAP_PROJECT_MISSING")
    vendor=root/"VENDOR/componentize-packages"
    vendor.mkdir(parents=True,exist_ok=True)
    env={**os.environ,
         "NUGET_PACKAGES":str(vendor),
         "NUGET_HTTP_CACHE_PATH":str(root/"VENDOR/componentize-http-cache"),
         "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false",
         "DOTNET_CLI_HOME":str(lab/".dotnet-home"),
         "DOTNET_CLI_TELEMETRY_OPTOUT":"1",
         "DOTNET_SKIP_FIRST_TIME_EXPERIENCE":"1"}
    probe=lab/"bin/Release/net10.0/wasi-wasm/publish/WasiProbe.wasm"
    if not probe.is_file():
        # SDK source is fixed; no model-supplied MSBuild targets, analyzers or
        # plugins. Componentize-dotnet currently maintains a reusable WASI SDK
        # cache in the Windows user's .wasi-sdk folder.
        restore=subprocess.run([str(csharp_wasi.DOTNET),"restore",str(project),
            "--configfile",str(lab/"NuGet.Config"),"--disable-parallel"],
            cwd=lab,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=240)
        if restore.returncode:
            raise RuntimeError("COMPONENTIZE_NUGET_RESTORE_FAILED:"+restore.stderr.decode("utf-8","replace")[-500:])
        build=subprocess.run([str(csharp_wasi.DOTNET),"build",str(project),
            "--no-restore","-c","Release","-v","minimal"],
            cwd=lab,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=240)
        if build.returncode:
            raise RuntimeError("COMPONENTIZE_TRUSTED_BUILD_FAILED:"+build.stdout.decode("utf-8","replace")[-600:])
    if not probe.is_file() or probe.read_bytes()[:4]!=b"\x00asm":
        raise RuntimeError("CSHARP_WASI_TRUSTED_PROBE_MISSING")
    return {"trustedProbeWasmSha256":sha_file(probe),
            "trustedCsprojSha256":sha_file(project),
            "cachedToolchainsNotIncludedInSourceZip":True}

def bootstrap(root):
    root=engine.init(root)
    wasm=_wasmtime(root)
    npm=_npm_umd(root)
    csharp=_componentize(root)
    proof=csharp_wasi.preflight(root)
    record={"schema":1,"atUtc":utc(),"status":"R035_PRIVATE_VENDOR_TOOLCHAINS_SHA_AND_WASI_VERIFIED",
            "wasmtime":wasm,"npm":npm,"componentize":csharp,
            "guest":proof["backend"],
            "scope":"Project-private npm UMD and Wasmtime; .NET SDK system and user-home .wasi-sdk reused. No global PATH/Host/PROD changes.",
            "modelWeightsIncluded":False}
    receipt=root/"CONTINUIDAD/R035/EXTRA-TOOLCHAIN-RECEIPT.json"
    if receipt.exists():
        old=load(receipt)
        for key in ("wasmtime","npm","componentize","guest"):
            if old.get(key)!=record[key]:raise RuntimeError("R035_EXISTING_TOOLCHAIN_RECEIPT_DRIFT")
    else:
        write_json(receipt,record,new=True)
    return {"status":"R035_PRIVATE_VENDOR_READY_NO_REDOWNLOAD_IF_CACHED",
            "receiptSha256":sha_file(receipt),"readback":record}
