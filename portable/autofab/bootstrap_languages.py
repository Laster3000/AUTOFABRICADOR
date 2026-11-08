# coding: utf-8
"""Private Javy/TypeScript bootstrap with origin SHA, no global npm or Host modifications."""
from __future__ import annotations
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import uuid

from . import engine,js_wasi
from .storage import load,sha_file,utc,write_json

def check(root):
    root=engine.init(root)
    lock=load(root/"LANGUAGE-TOOLS.lock.json")
    j=lock["vendors"]["javy"]
    v=root/"VENDOR/javy-v9.1.0-windows-x64"
    archive=v/"javy-x86_64-windows-v9.1.0.gz"
    binary=v/"javy.exe"
    compiler=root/"VENDOR/typescript/node_modules/typescript/lib/typescript.js"
    return {"archivePresentAndSha":archive.is_file() and sha_file(archive)==j["archiveSha256"],
            "javyPresentAndSha":binary.is_file() and sha_file(binary)==j["binarySha256"],
            "typescriptPresentAndSha":compiler.is_file() and sha_file(compiler)==js_wasi.TS_JS_SHA,
            "lockSha":sha_file(root/"LANGUAGE-TOOLS.lock.json"),
            "wasiAvailable":(root/"VENDOR/wasi-runtime/wasmtime/__init__.py").is_file()}

def bootstrap(root):
    root=engine.init(root)
    status=check(root)
    if status["javyPresentAndSha"] and status["typescriptPresentAndSha"]:
        js_wasi.preflight(root,"typescript")
        receipt=root/"CONTINUIDAD/LANGUAGE-BOOTSTRAP-RECEIPT.json"
        if receipt.exists():
            saved=load(receipt)
            if saved.get("lockSha256")!=status["lockSha"]:
                # A legitimate versioned lock amendment may retain the
                # original boot receipt. Never rewrite or erase the old proof.
                revision=root/"CONTINUIDAD/R035/LOCK-REVISION-RECEIPT.json"
                if not revision.is_file():
                    raise RuntimeError("LANGUAGE_BOOTSTRAP_RECEIPT_LOCK_DRIFT")
                amended=load(revision)
                if (amended.get("preimageSha256")!=saved.get("lockSha256") or
                    amended.get("newSha256")!=status["lockSha"]):
                    raise RuntimeError("LANGUAGE_BOOTSTRAP_LOCK_AMENDMENT_SHA_DRIFT")
                receipt=root/"CONTINUIDAD/R035/LANGUAGE-BOOTSTRAP-REVALIDATED.json"
                if not receipt.exists():
                    write_json(receipt,{"schema":1,"atUtc":utc(),
                        "status":"R035_LOCK_REVISION_SHA_VERIFIED_VENDOR_UNCHANGED",
                        "originalBootReceiptSha":sha_file(root/"CONTINUIDAD/LANGUAGE-BOOTSTRAP-RECEIPT.json"),
                        "lockRevisionReceiptSha":sha_file(revision),
                        "lockSha256":status["lockSha"],
                        "javyExeSha256":js_wasi.JAVY_EXE_SHA,
                        "typescriptSha256":js_wasi.TS_JS_SHA},new=True)
                else:
                    updated=load(receipt)
                    if updated["lockSha256"]!=status["lockSha"]:
                        raise RuntimeError("R035_REVALIDATED_RECEIPT_SHA_DRIFT")
        else:
            write_json(receipt,{"schema":1,"atUtc":utc(),
                "status":"EXISTING_LOCAL_JS_TS_TOOLCHAIN_SHA_VERIFIED",
                "lockSha256":status["lockSha"],"archiveSha256":js_wasi.JAVY_ARCHIVE_SHA,
                "javyExeSha256":js_wasi.JAVY_EXE_SHA,
                "typescriptSha256":js_wasi.TS_JS_SHA,
                "guest":"WASI-no-preopened-dirs-no-network",
                "sourceCodeExeRuntimeModified":False},new=True)
        return {"status":"ALREADY_PINNED_VERIFIED_NO_REDOWNLOAD",
                "receiptSha256":sha_file(receipt),"readback":status}
    lock=load(root/"LANGUAGE-TOOLS.lock.json")
    required=lock["vendors"]["javy"]
    folder=root/"VENDOR/javy-v9.1.0-windows-x64"
    folder.mkdir(parents=True,exist_ok=True)
    archive=folder/"javy-x86_64-windows-v9.1.0.gz"
    binary=folder/"javy.exe"
    if archive.is_file():
        if sha_file(archive)!=required["archiveSha256"]:
            raise RuntimeError("JAVY_ARCHIVE_SHA_DRIFT_NO_REDOWNLOAD")
    else:
        # Atomic staged download; no use of unverified bytes.
        tmp=folder/(".javy-"+uuid.uuid4().hex+".download")
        maximum=24*1024*1024
        count=0
        try:
            req=urllib.request.Request(required["source"],headers={"User-Agent":"AUTOFABRICADOR-R034-PINNED"})
            with urllib.request.urlopen(req,timeout=60) as source,tmp.open("xb") as dest:
                while True:
                    chunk=source.read(1024*1024)
                    if not chunk:break
                    count+=len(chunk)
                    if count>maximum:raise RuntimeError("JAVY_DOWNLOAD_TOO_LARGE")
                    dest.write(chunk)
                dest.flush();os.fsync(dest.fileno())
            if sha_file(tmp)!=required["archiveSha256"]:
                raise RuntimeError("JAVY_DOWNLOADED_SHA_MISMATCH")
            os.replace(tmp,archive)
        finally:
            if tmp.exists():tmp.unlink()
    if binary.exists():
        if sha_file(binary)!=required["binarySha256"]:
            raise RuntimeError("JAVY_BINARY_SHA_DRIFT")
    else:
        with gzip.open(archive,"rb") as unpacked:
            with binary.open("xb") as out:
                shutil.copyfileobj(unpacked,out,1024*1024)
                out.flush();os.fsync(out.fileno())
        if sha_file(binary)!=required["binarySha256"]:
            raise RuntimeError("JAVY_DECOMPRESSED_BINARY_SHA_DRIFT")
    tsc=root/"VENDOR/typescript/node_modules/typescript/lib/typescript.js"
    if tsc.exists():
        if sha_file(tsc)!=js_wasi.TS_JS_SHA:
            raise RuntimeError("TYPESCRIPT_EXISTING_BINARY_SHA_DRIFT")
    else:
        node=root/"VENDOR/typescript"
        if (node/"node_modules").exists():
            raise RuntimeError("PARTIAL_TYPESCRIPT_INSTALL_NO_BLIND_REPLAY")
        npm=shutil.which("npm.cmd")
        if not npm:raise RuntimeError("NPM_REQUIRED_FOR_PRIVATE_TYPESCRIPT")
        result=subprocess.run(
           [npm,"install","--prefix",str(node),"--cache",str(node/"download-cache"),
            "--no-save","--ignore-scripts","--no-audit","--no-fund",
            "typescript@5.9.3"],
           cwd=str(root),stdin=subprocess.DEVNULL,capture_output=True,timeout=240,
           env={**os.environ,"DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"})
        if result.returncode:raise RuntimeError("TYPESCRIPT_PRIVATE_INSTALL_FAILED:"+result.stderr.decode("utf-8","replace")[-400:])
        if not tsc.is_file() or sha_file(tsc)!=js_wasi.TS_JS_SHA:
            raise RuntimeError("TYPESCRIPT_PRIVATE_INSTALL_SHA_NOT_ACCEPTED")
    verified=js_wasi.preflight(root,"typescript")
    result={"schema":1,"atUtc":utc(),"status":"PINNED_JS_TS_TOOLCHAIN_INSTALLED_PRIVATE",
            "lockSha256":sha_file(root/"LANGUAGE-TOOLS.lock.json"),
            "archiveSha256":sha_file(archive),"javySha256":sha_file(binary),
            "typescriptSha256":sha_file(tsc),"guest":verified["guest"],
            "noGlobalPathOrServiceModified":True,
            "csharpRuntimeStillNotIsolated":True}
    receipt=root/"CONTINUIDAD/LANGUAGE-BOOTSTRAP-RECEIPT.json"
    if receipt.exists():
        original=load(receipt)
        if original.get("lockSha256")!=result["lockSha256"]:
            raise RuntimeError("EXISTING_LANGUAGE_BOOTSTRAP_RECEIPT_LOCK_DRIFT")
        return {"status":"EXISTING_RECEIPT_AND_BINARIES_VERIFIED","readback":result}
    write_json(receipt,result,new=True)
    return result
