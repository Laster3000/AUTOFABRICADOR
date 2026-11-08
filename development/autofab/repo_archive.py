# coding: utf-8
"""Import a real source repository ZIP without executing its scripts or addons.

Owner cases are supplied separately and frozen BEFORE model inference.
User-owned ZIP is read only; content is whitelisted to src JS/TS and inert
package.json/README; package dependencies must already be SRI/SHA pinned.
Symlinks, ZIP escapes, package hooks, Node builtins and unapproved npm
dependencies are rejected rather than executed on unisolated Windows.
"""
from __future__ import annotations
from pathlib import Path,PurePosixPath
import json,os,re,shutil,stat,uuid,zipfile
from . import engine,repo_graph,repo_factory,npm_umd
from .storage import load,sha_file,sha_bytes,utc,write_json,event
EXTRAS=frozenset(("package.json","README.md","README.txt"))
MAX_ARCHIVE=1300000
MAX_TOTAL=500000
def inspect(root,zip_path,owner_path):
    root=engine.init(root)
    zpath=Path(zip_path).resolve()
    if not zpath.is_file() or zpath.is_symlink() or zpath.stat().st_size>MAX_ARCHIVE:
        raise ValueError("REPO_ZIP_SOURCE_NOT_REGULAR_OR_TOO_LARGE")
    owner=Path(owner_path).resolve()
    if not owner.is_file() or owner.is_symlink() or not owner.is_relative_to(root/"examples"):
        raise ValueError("REPO_OWNER_CONTRACT_MUST_BE_SEPARATE_PROJECT_EXAMPLE")
    spec=load(owner)
    repo_graph._valid_spec(spec)
    repo_graph.preflight(root)
    npm_vendor=npm_umd.preflight(root,spec["dependencies"])
    with zipfile.ZipFile(zpath) as archive:
        info=archive.infolist()
        if len(info)<3 or len(info)>30 or len({i.filename.lower() for i in info})!=len(info):
            raise ValueError("REPO_ZIP_ENTRY_COUNT_OR_CASE_COLLISION_INVALID")
        filemap={}
        total=0
        for item in info:
            name=item.filename
            parts=PurePosixPath(name)
            if (name.startswith("/") or name.endswith("/")
                or parts.is_absolute() or ".." in parts.parts
                or "\\" in name or ":" in name or not name
                or len(name)>140 or len(parts.parts)>6
                or stat.S_ISLNK(item.external_attr>>16)
                or item.file_size<0 or item.file_size>75000):
                raise ValueError("REPO_ZIP_PATH_SYMLINK_SIZE_UNSAFE")
            if name not in spec["sources"] and name not in EXTRAS:
                raise ValueError("REPO_ZIP_UNDECLARED_OR_EXECUTABLE_FILE:"+name)
            total+=item.file_size
            if total>MAX_TOTAL:raise ValueError("REPO_ZIP_DECLARED_BYTES_EXCEED_LIMIT")
            data=archive.read(name)
            if len(data)!=item.file_size:raise ValueError("REPO_ZIP_BYTES_SIZE_DRIFT")
            filemap[name]=data
    if set(filemap)-EXTRAS!=set(spec["sources"]):
        raise ValueError("REPO_ZIP_MODEL_DECLARED_SOURCE_NOT_COMPLETE")
    if "package.json" not in filemap:
        raise ValueError("REPO_PACKAGE_JSON_REQUIRED_FOR_GRAPH_CLOSURE")
    package=json.loads(filemap["package.json"])
    if (not isinstance(package,dict) or
        not isinstance(package.get("name"),str) or
        package.get("type")!="module" or
        package.get("private") is not True):
        raise ValueError("REPO_PACKAGE_METADATA_NOT_SAFE")
    if any(key in package for key in ("bin","scripts","optionalDependencies",
                                     "devDependencies","peerDependencies",
                                     "workspaces","overrides","config",
                                     "exports","imports","directories","os","cpu","engines")):
        raise ValueError("REPO_NPM_LIFECYCLE_OR_CONFIG_NOT_ALLOWED")
    declared=package.get("dependencies",{})
    if not isinstance(declared,dict) or set(declared)!=set(spec["dependencies"]):
        raise ValueError("REPO_NPM_DEPENDENCY_GRAPH_NOT_PREAPPROVED")
    if any(declared[name]!=npm_vendor[name]["version"] for name in declared):
        raise ValueError("REPO_NPM_PACKAGE_PIN_VERSION_DIFFERS")
    source={}
    for name in spec["sources"]:
        try:source[name]=filemap[name].decode("utf-8")
        except UnicodeDecodeError:raise ValueError("REPO_NON_UTF8_SOURCE")
    new_spec={**spec,"sources":source}
    repo_graph._valid_spec(new_spec)
    repo_graph._static_source_guard(source)
    return {"schema":1,"package":package,
       "repoSpec":new_spec,
       "sourceSha256":{n:sha_bytes(raw.encode()) for n,raw in source.items()},
       "originalZipSha256":sha_file(zpath),
       "files":len(filemap),
       "trustedOwnerSpecSha256":sha_file(owner),
       "pinnedVendors":npm_vendor,
       "modelSourceNeverExecutedAtImport":True}

def create(root,zip_path,owner_path):
    root=engine.init(root)
    inspected=inspect(root,zip_path,owner_path)
    ident="RI-"+uuid.uuid4().hex[:16]
    snapshots=root/"repoimports"
    snapshots.mkdir(exist_ok=True)
    zip_dest=snapshots/(ident+".zip")
    # Byte-preserving user-provided zip for exact restore/reconciliation.
    with Path(zip_path).open("rb") as inp,zip_dest.open("xb") as out:
        shutil.copyfileobj(inp,out,1024*1024)
        out.flush();os.fsync(out.fileno())
    if sha_file(zip_dest)!=inspected["originalZipSha256"]:
        raise RuntimeError("REPO_SOURCE_ZIP_READBACK_SHA_CHANGED")
    owner_file=root/"examples"/(ident+"-preinference-owner.json")
    write_json(owner_file,inspected["repoSpec"],new=True)
    result=repo_factory.create(root,owner_file)
    jobdir=repo_factory.directory(root,result["jobId"])
    original=load(jobdir/"owner-acceptance.json")
    if original["cases"]!=inspected["repoSpec"]["acceptance"]:
        raise RuntimeError("ORIGINAL_REPO_OWNER_WAS_NOT_FROZEN")
    link={"schema":1,"status":"REPO_IMPORT_SHA_PINNED_NO_HOST_EXECUTION",
          "atUtc":utc(),"importId":ident,"repoJobId":result["jobId"],
          "sourceOriginalZipSha256":sha_file(zip_dest),
          "separateOwnerSpecSha256":inspected["trustedOwnerSpecSha256"],
          "ownerAcceptanceOriginalSha256":sha_file(jobdir/"owner-acceptance.json"),
          "sourceSha256":inspected["sourceSha256"],
          "npmPinnedVendors":inspected["pinnedVendors"],
          "metadataNoScripts":True,"modelCalls":0}
    write_json(snapshots/(ident+".json"),link,new=True)
    event(snapshots/"journal.jsonl","REPO_IMPORT_PINNED_WITHOUT_NPM_SCRIPTS",
          {"importId":ident,"jobId":result["jobId"],
           "originalUserZipSha":sha_file(zip_dest),
           "originalOwnerSha":link["ownerAcceptanceOriginalSha256"]})
    return {"status":"REPO_IMPORTED_SOURCE_ONLY_NOT_EXECUTED",
            "importId":ident,"jobId":result["jobId"],
            "originalOwnerSha256":link["ownerAcceptanceOriginalSha256"],
            "sourceFiles":len(inspected["sourceSha256"]),
            "untrustedNpmScriptsExecuted":0}
