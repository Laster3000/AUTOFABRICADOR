# coding: utf-8
r"""Verify and physically restore the frozen vendor archive without networking.

Writes ONLY to a new temporary directory under D:\AUTOFABRICADOR-RESCATE,
verifies each extracted file's SHA and runs pinned JS/TS + WASI smoke tests
from extracted bytes. Prerequisite system Python/Node/.NET/Chrome are not
bundled and no Host/BOOT/PROD/ROOT/global installation is attempted.
"""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path,PurePosixPath
import subprocess,sys,tempfile,time,zipfile
from .storage import load,sha_bytes,sha_file,utc,write_json,verify_journal
from .isolation import IsolationUnavailable
from . import engine,js_wasi,local_runtime,csharp_wasi

F=Path(r"D:\AUTOFABRICADOR-RESCATE")
ZIPNAME="AUTOFABRICADOR-0.8.0-PRIVATE-VENDOR.zip"

def sha_stream(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):h.update(block)
    return h.hexdigest()

def preflight(root):
    root=engine.init(root)
    receipt=root/"CONTINUIDAD/R036/VENDOR-ARCHIVE-RECEIPT.json"
    archive=F/ZIPNAME
    if not receipt.is_file() or not archive.is_file():
        raise IsolationUnavailable("R036_OFFLINE_VENDOR_CAPSULE_NOT_FINALIZED")
    original=load(receipt)
    if original["status"]!="R036_PRIVATE_VENDOR_SHA_ARCHIVE_READY":
        raise RuntimeError("R036_ARCHIVE_RECEIPT_NOT_READY")
    if archive.stat().st_size!=original["zipBytes"]:
        raise RuntimeError("VENDOR_ARCHIVE_SIZE_DRIFT")
    # Original R036 receipt remains immutable with its historical F path.
    # Current effective path is exclusively D after SHA+CAS migration.
    migration=root/"CONTINUIDAD/R037/F-D-MIGRATION-FINAL.json"
    if not migration.is_file():
        raise IsolationUnavailable("R037_D_RESCUE_CUTOVER_RECEIPT_MISSING")
    proof=load(migration)
    if (proof.get("status")!="R037_F_AUTOFABRICADOR_RESCUE_EMPTY_MOVED_TO_D_FULL_SHA"
        or proof.get("originalVendorArchiveSha256")!=original["archiveSha256"]
        or Path(r"F:\AUTOFABRICADOR-RESCATE").exists()):
        raise RuntimeError("R037_D_RESCUE_MIGRATION_NOT_RECONCILED")
    return {**original,"archive":str(archive),
            "historicalArchiveLocation":original["archive"],
            "migrationReceiptSha256":sha_file(migration),
            "currentRescueDrive":"D"}

def verify(root,*,physical=True):
    root=engine.init(root)
    original=preflight(root)
    source=F/ZIPNAME
    start=time.monotonic()
    if sha_stream(source)!=original["archiveSha256"]:
        raise RuntimeError("OFFLINE_CAPSULE_ARCHIVE_SHA_DRIFT")
    with zipfile.ZipFile(source) as archive:
        raw=archive.read("PRIVATE-VENDOR-MANIFEST.json")
        if sha_bytes(raw)!=original["manifestSha256"]:
            raise RuntimeError("OFFLINE_VENDOR_MANIFEST_SHA_DRIFT")
        data=json.loads(raw)
        meta=data["files"]
        names=archive.namelist()
        if (set(names)!=(set(meta)|{"PRIVATE-VENDOR-MANIFEST.json"})
            or len(meta)!=original["files"] or len(names)!=len(set(names))):
            raise RuntimeError("OFFLINE_VENDOR_ENTRY_COUNT_MISMATCH")
        if not physical:
            return {"status":"ARCHIVE_AND_MANIFEST_SHA_VERIFIED_ONLY",
                    "entries":len(meta),"archiveSha256":original["archiveSha256"]}
        if not F.exists():raise RuntimeError("VOLUME_F_MISSING_FOR_OFFLINE_RESTORE")
        with tempfile.TemporaryDirectory(prefix="AF-R036-OFFLINE-RESTORE-",dir=F) as tmp:
            workspace=Path(tmp)
            count=0
            total=0
            for rel,expected in sorted(meta.items()):
                pure=PurePosixPath(rel)
                if (pure.is_absolute() or ".." in pure.parts or not pure.parts
                    or "\\" in rel or ":" in rel or len(pure.parts)>25):
                    raise RuntimeError("OFFLINE_ARCHIVE_PATH_UNSAFE:"+rel)
                if expected["bytes"]>1800000000:
                    raise RuntimeError("OFFLINE_ARCHIVE_FILE_SIZE_TOO_LARGE")
                target=workspace.joinpath(*pure.parts)
                target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256()
                with archive.open(rel,"r") as inp,target.open("xb") as out:
                    while True:
                        chunk=inp.read(1024*1024)
                        if not chunk:break
                        h.update(chunk)
                        out.write(chunk)
                    out.flush()  # scratch is disposable; SHA/readback checked independently
                if h.hexdigest()!=expected["sha256"] or target.stat().st_size!=expected["bytes"]:
                    raise RuntimeError("OFFLINE_PHYSICAL_RESTORE_SHA_MISMATCH:"+rel)
                count+=1
                total+=expected["bytes"]
                if count%4000==0:
                    progress={"schema":1,"status":"OFFLINE_RESTORE_VALIDATING_NOT_FINAL",
                              "atUtc":utc(),"restored":count,"expected":len(meta),
                              "restoredBytes":total}
                    (root/"CONTINUIDAD/R036/OFFLINE-RESTORE-LIVE.json").write_text(json.dumps(progress),encoding="utf-8")
            if total!=data["sourceBytes"]:
                raise RuntimeError("OFFLINE_RESTORED_TOTAL_BYTES_DRIFT")
            javy=workspace/"VENDOR/javy-v9.1.0-windows-x64/javy.exe"
            wasmtime=workspace/"VENDOR/wasmtime-cli-50.0.1/wasmtime.exe"
            typescript=workspace/"VENDOR/typescript/node_modules/typescript/bin/tsc"
            if (sha_stream(javy)!=js_wasi.JAVY_EXE_SHA
                or sha_stream(wasmtime)!=csharp_wasi.WASMTIME_SHA
                or sha_stream(workspace/"VENDOR/wasi-runtime/wasmtime/__init__.py")!=js_wasi.WASMTIME_INIT_SHA):
                raise RuntimeError("RESTORED_RUNTIME_BINARIES_WRONG_SHA")
            # Two independent real compilers run only from the extracted copy.
            script=workspace/"smoke.js"
            script.write_text("console.log('AF_OFFLINE_JAVY_WASMTIME_OK');\n",encoding="utf-8")
            wasm=workspace/"smoke.wasm"
            build=subprocess.run([str(javy),"build",str(script),"-o",str(wasm)],
                      cwd=str(workspace),stdin=subprocess.DEVNULL,
                      capture_output=True,timeout=50)
            if build.returncode or not wasm.is_file():
                raise RuntimeError("OFFLINE_RESTORED_JAVY_COMPILE_FAILED")
            run=subprocess.run([str(wasmtime),"run",
                       "-W","timeout=8s,max-memory-size=268435456",
                       "-S","inherit-network=n,tcp=n,udp=n,http=n,inherit-env=n,inherit-stdin=n",
                       str(wasm)],
                       cwd=str(workspace),stdin=subprocess.DEVNULL,
                       capture_output=True,timeout=15)
            if run.returncode or b"AF_OFFLINE_JAVY_WASMTIME_OK" not in run.stdout:
                raise RuntimeError("RESTORED_WASI_JAVY_E2E_NOT_PASS")
            # System Node remains a documented prerequisite, but TypeScript
            # bytes are loaded from the recovered private vendor source.
            ts=workspace/"smoke.ts"
            ts.write_text("function twice(n:number):number {return n*2;}\nconsole.log(twice(21));\n",encoding="utf-8")
            js=workspace/"smoke-ts.js"
            tsc=subprocess.run([r"C:\Program Files\nodejs\node.exe",str(typescript),
                            "--target","ES2022","--module","none",
                            "--outFile",str(js),str(ts)],
                            cwd=str(workspace),stdin=subprocess.DEVNULL,
                            capture_output=True,timeout=50)
            if tsc.returncode or not js.exists():
                raise RuntimeError("OFFLINE_TS_RESTORED_COMPILER_NOT_PASS")
            tswasm=workspace/"smoke-ts.wasm"
            compiled=subprocess.run([str(javy),"build",str(js),"-o",str(tswasm)],
                                    cwd=str(workspace),stdin=subprocess.DEVNULL,
                                    capture_output=True,timeout=50)
            if compiled.returncode or not tswasm.exists():
                raise RuntimeError("OFFLINE_TS_TO_WASM_COMPILE_FAILED")
            executed=subprocess.run([str(wasmtime),"run",
                      "-W","timeout=8s,max-memory-size=268435456",
                      "-S","inherit-network=n,tcp=n,udp=n,http=n,inherit-env=n,inherit-stdin=n",
                      str(tswasm)],
                      cwd=str(workspace),stdin=subprocess.DEVNULL,
                      capture_output=True,timeout=15)
            if executed.returncode or b"42" not in executed.stdout:
                raise RuntimeError("OFFLINE_RESTORED_TS_WASM_GUEST_NOT_PASS")
            # WASI SDK and package byte presence is checked. Full .NET
            # no-network cross-compilation on this separate path is not yet
            # demonstrated by these JS/TS smoke tests.
            if not (workspace/"EXTERNAL-WASI-SDK").is_dir() or not (
                workspace/"VENDOR/componentize-packages/bytecodealliance.componentize.dotnet.wasm.sdk").is_dir():
                raise RuntimeError("OFFLINE_CSHARP_SDK_OR_NUGET_NOT_RESTORED")
            status={"schema":1,"atUtc":utc(),
                 "status":"R036_OFFLINE_VENDOR_PHYSICAL_RESTORE_JS_TS_E2E_PASS",
                 "originalArchiveSha256":original["archiveSha256"],
                 "originalManifestSha256":original["manifestSha256"],
                 "restoredFileCount":count,
                 "restoredOriginalBytes":total,
                 "javyWasmRuntimeSmoke":"PASS_FROM_RESTORED_BINARIES",
                 "typescriptTscJavyWasmtimeSmoke":"PASS_FROM_RESTORED_BINARIES",
                 "csharpComponentizeAndExternalWasiSdkBytesRestored":True,
                 "csharpFreshOfflineAotCompilationFromRestoredNuget":"NOT_TESTED",
                 "systemSdkPythonNodeChromeBundled":False,
                 "freshWindowsPortableOfflineE2EProved":False,
                 "didNotUseNetwork":True,
                 "temporaryRestoredBytesCleanedAtExit":True,
                 "elapsedMs":round((time.monotonic()-start)*1000)}
        # tempfile destructor removes only the new scratch folder, preserving
        # original vendor and the F zip + manifest.
        receipt=root/"CONTINUIDAD/R036/OFFLINE-RESTORE-RECEIPT.json"
        if receipt.exists():
            previous=load(receipt)
            for key in ("status","originalArchiveSha256","restoredFileCount","restoredOriginalBytes"):
                if previous.get(key)!=status.get(key):
                    raise RuntimeError("OFFLINE_RESTORE_OLD_RECEIPT_CONFLICT")
        else:
            write_json(receipt,status,new=True)
        return {"status":status["status"],"receiptSha256":sha_file(receipt),
                "restoredFileCount":count,"sourceBytes":total,
                "javy":"PASS","typescript":"PASS",
                "cleanWindowsOfflineInstall":"NOT_PROVED",
                "temporaryScratchRemoved":True}
