# coding: utf-8
"""User-scoped offline installation and reversible restore of trusted app bundle.

Never elevates Windows privileges, never installs SCM services, registry,
scheduled tasks, third-party packages, or model-authored executable Python.
Existing installation and unknown preimages are immutable. Deletion requires
explicit user confirmation and is confined to an original install whose
readback hashes still match; SQLite user data lives elsewhere and is retained.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import zipfile
from pathlib import Path,PurePosixPath

_ID=re.compile(r"AFD-[a-f0-9]{16}\Z")
_ALLOWED=frozenset({
 "desktop_orders_core.py","desktop_orders_ui.py",
 "run.py","README.txt","LAUNCH.cmd"
})

def _sha(b):return hashlib.sha256(b).hexdigest()
def _sha_file(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for x in iter(lambda:f.read(1<<20),b""):h.update(x)
 return h.hexdigest()
def _manifest(archive):
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=6 or len(set(names))!=len(names) or set(names)!=_ALLOWED|{"MANIFEST.json"}:
            raise ValueError("DESKTOP_INSTALL_ARCHIVE_MEMBER_SET_INVALID")
        m=json.loads(z.read("MANIFEST.json"))
        if (not isinstance(m,dict) or m.get("schema")!=1 or
            m.get("profile")!="AF.DESKTOP.ORDERS.SQLITE.V1" or
            not isinstance(m.get("appId"),str) or not _ID.fullmatch(m["appId"]) or
            not isinstance(m.get("files"),dict) or set(m["files"])!=_ALLOWED or
            m.get("execSource")!="ORIGINAL_FIRST_PARTY_TRUSTED_TEMPLATES_ONLY" or
            m.get("modelCodeOnWindowsHost") is not False):
            raise ValueError("DESKTOP_INSTALL_MANIFEST_UNTRUSTED")
        for name in _ALLOWED:
            member=m["files"][name]
            data=z.read(name)
            if (not isinstance(member,dict) or set(member)!={"size","sha256"} or
                member["size"]!=len(data) or member["sha256"]!=_sha(data) or
                len(data)>30000):
                raise ValueError("DESKTOP_INSTALL_MEMBER_HASH_OR_SIZE_INVALID:"+name)
    return m

def _root(root):
    r=Path(root).resolve()
    if not r.is_dir():
        raise ValueError("DESKTOP_INSTALL_BASE_NOT_EXIST")
    if r.is_symlink():
        raise ValueError("DESKTOP_INSTALL_BASE_SYMLINK")
    return r

def install(root,archive):
    """Install under root/APPS only (current user), no executable launched."""
    root=_root(root)
    file=Path(archive)
    if not file.is_file() or file.is_symlink():
        raise ValueError("DESKTOP_INSTALL_ARCHIVE_NOT_REGULAR_FILE")
    m=_manifest(file)
    app=m["appId"]
    base=root/"APPS"
    base.mkdir(exist_ok=True)
    if base.is_symlink():raise ValueError("DESKTOP_APPS_SYMLINK")
    target=base/app
    if target.exists() or target.is_symlink():
        # Explicit no overwrite. Live projects / modifications preserved.
        return {"status":"EXISTING_INSTALLATION_NO_REPLAY_OR_OVERWRITE",
                "appId":app,"installedPath":str(target),
                "verified":verify(root,app).get("verified",False)}
    staged=base/(".STAGE-"+app)
    if staged.exists() or staged.is_symlink():
        raise RuntimeError("DESKTOP_INSTALL_UNCERTAIN_STAGE_NO_REPLAY")
    staged.mkdir(exist_ok=False)
    try:
        with zipfile.ZipFile(file) as z:
            for name in sorted(_ALLOWED):
                path=staged/name
                with path.open("xb") as f:
                    f.write(z.read(name));f.flush();os.fsync(f.fileno())
            (staged/"MANIFEST.json").write_bytes(z.read("MANIFEST.json"))
        if any(_sha_file(staged/name)!=m["files"][name]["sha256"] for name in _ALLOWED):
            raise RuntimeError("DESKTOP_STAGE_READBACK_SHA_MISMATCH")
        os.replace(staged,target)
        evidence=verify(root,app)
        if not evidence["verified"]:raise RuntimeError("DESKTOP_POSTINSTALL_VERIFICATION_FAILED")
        return {"status":"PASS_LOCAL_USER_INSTALL_SHA_READBACK",
                "appId":app,"installedPath":str(target),
                "archiveSha":_sha_file(file),
                "installedFilesVerified":evidence["fileCount"],
                "windowsServiceInstalled":False,
                "pythonRuntimeBundled":False,
                "osPrivilegesModified":False,
                "userSQLiteDataChanged":False}
    except Exception:
        # Do not delete uncertain target or re-run unknown install.
        # Temp stage is kept for explicit reconciliation if an error occurs.
        raise

def verify(root,app):
    root=_root(root)
    if not isinstance(app,str) or not _ID.fullmatch(app):
        raise ValueError("DESKTOP_INSTALL_APP_ID_INVALID")
    folder=root/"APPS"/app
    if not folder.is_dir() or folder.is_symlink():
        return {"verified":False,"status":"NOT_INSTALLED"}
    manifest=folder/"MANIFEST.json"
    if not manifest.is_file() or manifest.is_symlink():
        return {"verified":False,"status":"UNKNOWN_INSTALL_WITHOUT_MANIFEST"}
    m=json.loads(manifest.read_text("utf-8"))
    if m.get("appId")!=app or set(m.get("files",{}))!=_ALLOWED:
        raise RuntimeError("DESKTOP_INSTALL_MANIFEST_SCOPE_DRIFT")
    existing={p.name for p in folder.iterdir()}
    if existing!=_ALLOWED|{"MANIFEST.json"} or any(p.is_symlink() for p in folder.iterdir()):
        raise RuntimeError("DESKTOP_INSTALL_UNEXPECTED_FILES_OR_SYMLINK")
    verified=all(
        _sha_file(folder/name)==m["files"][name]["sha256"]
        and (folder/name).stat().st_size==m["files"][name]["size"]
        for name in _ALLOWED)
    return {"verified":verified,"status":"PASS" if verified else "DRIFT_NO_AUTOREPAIR",
            "appId":app,"fileCount":len(_ALLOWED),
            "sourceManifestSha":_sha_file(manifest),
            "installedPath":str(folder),
            "modelCodeExecuted":False}

def uninstall(root,app,*,confirm=False):
    if confirm is not True:raise PermissionError("DESKTOP_UNINSTALL_REQUIRES_EXPLICIT_OWNER_CONFIRMATION")
    state=verify(root,app)
    if not state["verified"]:
        raise RuntimeError("DESKTOP_UNINSTALL_ORIGINAL_SHA_NOT_VALID_NO_DELETE")
    folder=Path(state["installedPath"])
    # Delete ONLY known installed sources and original manifest, never
    # anything else. User's SQLite database is outside APPS and retained.
    for name in sorted(_ALLOWED|{"MANIFEST.json"}):
        (folder/name).unlink()
    folder.rmdir()
    return {"status":"PASS_REMOVED_VERIFIED_APP_CODE_ONLY",
            "appId":app,"sqliteUserDataDeleted":False,
            "otherProjectsDeleted":False,"originalSourceZipPreserved":True}
