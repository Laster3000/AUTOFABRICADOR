"""Housekeeping for disposable *owned* artifacts only.

Never delete work, jobs, sources, editors, missions, receipts, continuity, snapshots,
journals, unknown download partials, rollback files, or backups.
Reversible log rotation and safe bytecode disposal are the only apply effects.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import uuid

from .storage import event, sha_file, utc

OWNED_BYTECODE_DIRS = ("__pycache__", "autofab/__pycache__", "tests/__pycache__")
LOG_ROTATE_BYTES = 2 * 1024 * 1024

def _measure(folder):
    if not folder.exists():
        return {"files":0, "bytes":0}
    files=0
    total=0
    for base,dirs,leaf in os.walk(folder,followlinks=False):
        dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink()]
        for name in leaf:
            path=Path(base)/name
            if path.is_symlink():continue
            try:
                total+=path.stat().st_size
                files+=1
            except FileNotFoundError:
                continue
    return {"files":files,"bytes":total}

def _bytecode(root):
    candidates=[]
    for name in OWNED_BYTECODE_DIRS:
        p=root/name
        if not p.exists() or not p.is_dir() or p.is_symlink():continue
        for item in sorted(p.iterdir()):
            if not item.is_symlink() and item.is_file() and item.suffix==".pyc":
                candidates.append(item)
    return candidates

def inspect(root):
    root=Path(root).resolve()
    if root.name.upper()!="AUTOFABRICADOR" and not (root/"autofabricador.py").exists() and not ((root/"settings.json").exists() and (root/"work").is_dir()):
        raise RuntimeError("HOUSEKEEPING_ONLY_FACTORY_PROJECT_ROOT")
    paths={
        "indispensable_model":root/"VENDOR"/"models",
        "indispensable_binary":root/"VENDOR"/"llama-b12142-cpu-x64",
        "installed_isolation_runtime":root/"VENDOR"/"wasi-runtime",
        "offline_dependency_wheels":root/"VENDOR"/"wheels",
        "offline_vendor_archive":root/"VENDOR"/"llama-b12142-bin-win-cpu-x64.zip",
        "reusable_compiled_wasi_cache":root/"VENDOR"/"wasi-cache",
        "reusable_response_cache":root/"cache",
        "recoverable_work_and_attempts":root/"work",
        "journals_and_checkpoints":root/"CONTINUIDAD",
        "release_archives":root/"DIST",
        "recoverable_multiagent_missions":root/"missions",
        "recoverable_javascript_typescript_jobs":root/"langjobs",
        "recoverable_csharp_compilation_jobs":root/"csharpjobs",
        "recoverable_persistent_supervisor_queue":root/"supervisor",
        "recoverable_direct_http_model_jobs":root/"directjobs",
        "recoverable_real_model_cancel_probes":root/"cancelprobes",
        "browser_accepted_portable_webapps":root/"apps",
        "browser_accepted_multi_file_projects":root/"projects",
        "recoverable_esm_repository_job_receipts":root/"repojobs",
        "recoverable_untrusted_zip_imports":root/"repoimports",
        "browser_accepted_module_graph_app_exports":root/"repoexports",
        "recoverable_windows_vm_sandbox_native_jobs":root/"sandboxjobs",
        "pinned_javy_compiler_runtime":root/"VENDOR"/"javy-v9.1.0-windows-x64",
        "pinned_typescript_compiler_runtime":root/"VENDOR"/"typescript",
        "pinned_npm_umd_single_file_libraries":root/"VENDOR"/"npm-pin",
        "pinned_wasmtime_cli_for_csharp_wasi":root/"VENDOR"/"wasmtime-cli-50.0.1",
        "reusable_componentize_dotnet_packages":root/"VENDOR"/"componentize-packages",
        "private_browser_qa_runtime":root/"VENDOR"/"browser-qa",
        "private_pinned_wasm_bundler":root/"VENDOR"/"module-bundler",
        "reusable_wasm_bundler_tar_cache":root/"VENDOR"/"module-bundler-cache",
        "reusable_browser_qa_download_cache":root/"VENDOR"/"browser-qa-cache",
        "reusable_componentize_dotnet_http_cache":root/"VENDOR"/"componentize-http-cache",
        "trusted_csharp_wasi_probe_and_build_cache":root/"LAB-CSHARP-WASI-R035",
        "private_code_editors_node":root/"VENDOR"/"editors"/"node",
        "private_code_editor_aider_venv":root/"VENDOR"/"editors"/"aider-venv",
        "reusable_editor_package_download_cache":root/"VENDOR"/"editors"/"download-cache",
        "reusable_editor_local_home":root/"VENDOR"/"editors"/"opencode-home",
        "runtime_logs":root/"logs",
        "generated_bytecode":root/"__pycache__"
    }
    size={}
    for label,path in paths.items():
        if path.is_dir():size[label]=_measure(path)
        elif path.is_file():size[label]={"files":1,"bytes":path.stat().st_size}
        else:size[label]={"files":0,"bytes":0}
    bytecode=_bytecode(root)
    unknown=[]
    for base in (root/"VENDOR",root/"VENDOR"/"wheels",root/"VENDOR"/"models"):
        if base.is_dir():
            unknown.extend(str(p) for p in base.iterdir() if ".PART." in p.name or ".STAGE." in p.name or p.name.endswith(".part"))
    logs=[]
    active_lease=(root/"CONTINUIDAD"/"LOCAL-SERVER.json").exists()
    logdir=root/"logs"
    if logdir.is_dir():
        for p in sorted(logdir.glob("*.log")):
            if p.is_file() and not p.is_symlink() and p.stat().st_size>LOG_ROTATE_BYTES:
                logs.append(str(p))
    return {
        "schema":1,"root":str(root),
        "classes":size,
        "safeBytecodeCandidates":[{"path":str(p),"size":p.stat().st_size} for p in bytecode],
        "largeLogCandidates":logs,
        "logRotationBlockedByActiveOrUnreconciledLease":active_lease,
        "unknownVendorPartialsRequiringManualReconciliation":unknown,
        "policy":"Never remove useful code/data, source jobs, receipts, journals, model, wheels, WASI cache, package archives or backups automatically.",
        "automaticEffects":"Only exact temporary .pyc files in source/test cache folders, and losslessly rotated logs when no model lease exists."
    }

def _rotate_log(root,path):
    if (root/"CONTINUIDAD"/"LOCAL-SERVER.json").exists():
        return {"status":"SKIP_LEASE_EXISTS"}
    logs=root/"logs"
    if path.parent!=logs or not path.name.endswith(".log") or path.is_symlink():
        raise RuntimeError("LOG_PATH_UNSAFE")
    initial=sha_file(path)
    archive=logs/"ARCHIVE"
    archive.mkdir(parents=True,exist_ok=True)
    destination=archive/(path.name+"."+initial[:24]+".gz")
    if destination.exists():
        raise RuntimeError("LOG_ARCHIVE_COLLISION_RECONCILE")
    tmp=archive/("PENDING-"+uuid.uuid4().hex+".gz")
    original_size=path.stat().st_size
    try:
        with path.open("rb") as src,gzip.open(tmp,"wb",compresslevel=9) as out:
            shutil.copyfileobj(src,out,1024*1024)
        with gzip.open(tmp,"rb") as check:
            observed=hashlib.sha256()
            restored=0
            while block:=check.read(1024*1024):
                observed.update(block)
                restored+=len(block)
        if observed.hexdigest()!=initial or restored!=original_size or sha_file(path)!=initial:
            raise RuntimeError("LOG_ROTATION_SHA_READBACK_FAILED")
        os.replace(tmp,destination)
        empty=logs/("EMPTY-"+uuid.uuid4().hex+".log")
        empty.write_bytes(b"")
        if sha_file(path)!=initial:
            raise RuntimeError("LOG_CHANGED_DURING_ROTATION")
        os.replace(empty,path)
        if path.stat().st_size!=0:
            raise RuntimeError("LOG_EMPTY_READBACK_FAILED")
        return {"status":"ARCHIVED_LOSSLESSLY","originalSha256":initial,
                "archive":str(destination),"archiveSha256":sha_file(destination),
                "originalBytes":original_size,"archivedBytes":destination.stat().st_size}
    finally:
        if tmp.exists():
            # Unknown temporary artifact is left for reconciled cleanup.
            pass

def maintain(root, *, apply=False):
    root=Path(root).resolve()
    plan=inspect(root)
    if not apply:
        return {"mode":"DRY_RUN","scan":plan,"changed":False}
    actions=[]
    # Restrict removal to our own regenerable .pyc files.
    for obj in plan["safeBytecodeCandidates"]:
        file=Path(obj["path"])
        if not file.exists():continue
        if file.is_symlink() or file.suffix!=".pyc" or file.parent not in [root/x for x in OWNED_BYTECODE_DIRS]:
            raise RuntimeError("BYTECODE_NOT_ALLOWLISTED")
        pre=sha_file(file)
        size=file.stat().st_size
        # No receipts, source, or user files have .pyc extensions in allowlisted dirs.
        file.unlink()
        if file.exists():raise RuntimeError("BYTECODE_DISPOSAL_READBACK_FAILED")
        actions.append({"operation":"DELETE_REGENERABLE_PYC","path":str(file),"sha256":pre,"bytes":size})
    if not plan["logRotationBlockedByActiveOrUnreconciledLease"]:
        for path in plan["largeLogCandidates"]:
            result=_rotate_log(root,Path(path))
            actions.append({"operation":"ROTATE_LOG","path":path,**result})
    if actions:
        event(root/"CONTINUIDAD"/"HOUSEKEEPING-JOURNAL.jsonl","HOUSEKEEPING_APPLIED",
              {"atUtc":utc(),"actions":actions})
    return {"mode":"APPLY","changed":bool(actions),"actions":actions,
            "filesAffected":len(actions),
            "policy":"All job evidence, journals, caches, model binaries, archived logs and backups retained."}
