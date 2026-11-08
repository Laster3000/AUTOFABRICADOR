# coding: utf-8
"""Fail-closed current-user offline installer for original portfolio apps.

No privilege escalation, third-party lifecycle, system registry, service,
network or model-authored Python. Does not delete existing user records.
"""
from __future__ import annotations
import hashlib,json,os,re,zipfile
from pathlib import Path
FILES=("portfolio_specs.py","portfolio_core.py","portfolio_ui.py",
       "run.py","LAUNCH.cmd","README.txt")
_ID=re.compile(r"AFD-[a-f0-9]{16}\Z")
def sha(b):return hashlib.sha256(b).hexdigest()
def fsha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def validate(archive):
 file=Path(archive)
 if not file.is_file() or file.is_symlink():raise ValueError("PORTFOLIO_ARCHIVE_NOT_REGULAR")
 with zipfile.ZipFile(file) as z:
  infos=z.infolist()
  if (len(infos)!=len(FILES)+1 or len(set(x.filename for x in infos))!=len(infos)
      or set(x.filename for x in infos)!=set(FILES)|{"MANIFEST.json"}
      or any(x.is_dir() for x in infos)):
   raise ValueError("PORTFOLIO_ARCHIVE_MEMBERS_OUTSIDE_CONTRACT")
  m=json.loads(z.read("MANIFEST.json"))
  if (set(m)!={"schema","appId","profile","ownerGoalSha","validatedPlanSha",
                "files","sourceOrigin","modelCodeExecutedOnHost"}
      or m["schema"]!=1 or type(m["appId"]) is not str
      or not _ID.fullmatch(m["appId"])
      or m["profile"] not in ("inventory","tasks","expenses")
      or m["sourceOrigin"]!="ORIGINAL_FIRST_PARTY_TRUSTED"
      or m["modelCodeExecutedOnHost"] is not False
      or set(m["files"])!=set(FILES)):
   raise ValueError("PORTFOLIO_ORIGINAL_TRUST_MANIFEST_INVALID")
  for name in FILES:
   entry=m["files"][name]
   data=z.read(name)
   if (set(entry)!={"sha256","size"} or len(data)!=entry["size"]
       or sha(data)!=entry["sha256"] or len(data)>40000):
    raise ValueError("PORTFOLIO_ARCHIVE_SHA_DRIFT:"+name)
 return m
def _base(root):
 p=Path(root).resolve()
 if not p.is_dir() or p.is_symlink():raise ValueError("PORTFOLIO_INSTALL_ROOT_UNSAFE")
 return p
def verify(root,app):
 root=_base(root)
 if type(app) is not str or not _ID.fullmatch(app):
  raise ValueError("PORTFOLIO_APP_ID_INVALID")
 folder=root/"APPS"/app
 if not folder.is_dir() or folder.is_symlink():
  return {"verified":False,"status":"NOT_INSTALLED"}
 manifest=folder/"MANIFEST.json"
 if not manifest.is_file() or manifest.is_symlink():
  return {"verified":False,"status":"UNKNOWN_SOURCE_NO_MANIFEST"}
 m=json.loads(manifest.read_text("utf-8"))
 if m.get("appId")!=app or set(m.get("files",{}))!=set(FILES):
  raise RuntimeError("PORTFOLIO_INSTALLED_MANIFEST_SPOOF_OR_SCHEMA_DRIFT")
 if {x.name for x in folder.iterdir()}!=set(FILES)|{"MANIFEST.json"}:
  raise RuntimeError("PORTFOLIO_UNTRUSTED_INSTALLED_EXTRA_FILES")
 if any(x.is_symlink() for x in folder.iterdir()):
  raise RuntimeError("PORTFOLIO_INSTALLED_SYMLINK_DENIED")
 valid=all(fsha(folder/name)==m["files"][name]["sha256"]
           and (folder/name).stat().st_size==m["files"][name]["size"]
           for name in FILES)
 return {"verified":valid,"status":"PASS" if valid else "SOURCE_DRIFT_DENIED",
  "appId":app,"profile":m["profile"],
  "installedPath":str(folder),"sourceManifestSHA":fsha(manifest),
  "fileCount":len(FILES),"modelHostCode":False}
def install(root,archive):
 root=_base(root)
 m=validate(archive)
 base=root/"APPS"
 base.mkdir(exist_ok=True)
 if base.is_symlink():raise RuntimeError("PORTFOLIO_BASE_APPS_LINK_DENIED")
 target=base/m["appId"]
 if target.exists() or target.is_symlink():
  original=verify(root,m["appId"])
  return {"status":"EXISTING_INSTALL_NO_REPLAY","originalVerified":original["verified"],
          "appId":m["appId"]}
 stage=base/(".STAGE-"+m["appId"])
 if stage.exists() or stage.is_symlink():
  raise RuntimeError("PORTFOLIO_UNCERTAIN_INSTALL_STAGE_RECONCILE")
 stage.mkdir(exist_ok=False)
 with zipfile.ZipFile(archive) as z:
  for name in sorted(FILES):
   data=z.read(name)
   with (stage/name).open("xb") as out:
    out.write(data);out.flush();os.fsync(out.fileno())
  (stage/"MANIFEST.json").write_bytes(z.read("MANIFEST.json"))
 if not all(fsha(stage/name)==m["files"][name]["sha256"] for name in FILES):
  raise RuntimeError("PORTFOLIO_STAGE_ORIGINAL_SHA_DRIFT")
 os.replace(stage,target)
 final=verify(root,m["appId"])
 if not final["verified"]:
  raise RuntimeError("PORTFOLIO_INSTALL_AFTER_SHA_UNKNOWN")
 return {"status":"PASS_CURRENT_USER_INSTALL_SHA_READBACK",
   "appId":m["appId"],"profile":m["profile"],
   "archiveSHA":fsha(archive),"manifestSHA":final["sourceManifestSHA"],
   "installed":str(target),"verified":True,
   "noSystemService":True,"pythonRuntimeNotBundled":True,
   "userDataUnchanged":True}
def uninstall(root,app,*,confirm=False):
 if confirm is not True:raise PermissionError("PORTFOLIO_UNINSTALL_EXPLICIT_CONFIRM_REQUIRED")
 state=verify(root,app)
 if not state["verified"]:raise RuntimeError("PORTFOLIO_UNINSTALL_SOURCE_SHA_DRIFT")
 folder=Path(state["installedPath"])
 for name in sorted(set(FILES)|{"MANIFEST.json"}):
  (folder/name).unlink()
 folder.rmdir()
 return {"status":"PASS_INSTALLED_CODE_REMOVED_ONLY",
  "appId":app,"userDataPreserved":True,"otherProjectsRemoved":False}
