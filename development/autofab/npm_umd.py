# coding: utf-8
"""Strict npm allowlist: integrity-pinned standalone UMD libraries only.

No npm install, require(), package hooks, native add-ons, build plugins, or
arbitrary source evaluation occurs on the Windows host. Each library is loaded
as JS text only inside the Javy->Wasmtime guest, with no WASI FS/network grants.
"""
from pathlib import Path
import hashlib,json
from .storage import load,sha_file,sha_bytes
from .isolation import IsolationUnavailable

ALLOW=frozenset(("dayjs","lodash"))
MAX_VENDORED_SOURCE=160000

def trusted(root,dependencies):
    root=Path(root).resolve()
    if dependencies is None:dependencies=[]
    if not isinstance(dependencies,list) or len(dependencies)>2 or len(set(dependencies))!=len(dependencies):
        raise ValueError("DEPENDENCY_LIST_INVALID")
    if any(type(name) is not str or name not in ALLOW for name in dependencies):
        raise ValueError("NPM_DEPENDENCY_NOT_ALLOWLISTED")
    if not dependencies:
        return "",{}
    lock=root/"NPM-UMD.lock.json"
    if not lock.is_file():raise IsolationUnavailable("NPM_UMD_LOCK_MISSING")
    manifest=load(lock)
    recorded=manifest.get("packages",[])
    entries={p["name"]:p for p in recorded}
    source=[]
    hashes={}
    for name in dependencies:
        if name not in entries:raise IsolationUnavailable("NPM_UMD_DEPENDENCY_NOT_IN_LOCK")
        p=entries[name]
        if p.get("installStatus")!="VETTED_UMD_SINGLE_SOURCE_ONLY" or p.get("scriptExecution") is not False:
            raise IsolationUnavailable("NPM_UMD_UNSAFE_LOCK_ENTRY")
        rel=Path(p["relativeFile"])
        if rel.is_absolute() or ".." in rel.parts or len(rel.parts)>7:
            raise IsolationUnavailable("NPM_UMD_LOCK_PATH_UNSAFE")
        file=(root/rel).resolve()
        if not file.is_relative_to(root/"VENDOR/npm-pin") or not file.is_file() or file.is_symlink():
            raise IsolationUnavailable("NPM_UMD_SOURCE_OUTSIDE_PINNED_VENDOR")
        if sha_file(file)!=p["fileSha256"]:
            raise IsolationUnavailable("NPM_UMD_LIB_SHA_DRIFT:"+name)
        text=file.read_text("utf-8")
        if len(text.encode())>MAX_VENDORED_SOURCE:
            raise IsolationUnavailable("NPM_UMD_LIB_SIZE")
        source.append(text)
        hashes[name]={"version":p["version"],"fileSha256":sha_file(file),
                      "registrySRI":p["registrySRI"]}
    return "\n;\n".join(source),hashes

def preflight(root,dependencies):
    _,hashes=trusted(root,dependencies)
    return hashes
