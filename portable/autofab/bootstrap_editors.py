"""Project-only pinned editor bootstrap, no global PATH/pip/registry changes."""
from __future__ import annotations
import json,os
from pathlib import Path
import shutil,subprocess,sys
from .storage import load,sha_file,utc,write_json
from .advisors import binaries,CODEX_SHA,OPEN_SHA

def version_aider(root):
    python=root/"VENDOR/editors/aider-venv/Scripts/python.exe"
    if not python.is_file():return None
    result=subprocess.run([str(python),"-B","-c",
       "import importlib.metadata;print(importlib.metadata.version('aider-chat'))"],
       stdin=subprocess.DEVNULL,capture_output=True,timeout=25)
    return result.stdout.decode("utf-8","replace").strip() if result.returncode==0 else None

def check(root):
    root=Path(root).resolve()
    lock=load(root/"EDITORS.lock.json")
    if lock.get("schema")!=1 or lock.get("platform")!="win32-x64":
        raise RuntimeError("EDITORS_LOCK_SCHEMA")
    native=binaries(root)
    current={
       "aider":version_aider(root)=="0.86.2",
       "codex":native["codex"].is_file() and sha_file(native["codex"])==CODEX_SHA,
       "opencode":native["opencode"].is_file() and sha_file(native["opencode"])==OPEN_SHA
    }
    return {"installed":current,"allVerified":all(current.values()),
            "lockSha256":sha_file(root/"EDITORS.lock.json")}

def _run(cmd,*,timeout,cwd=None,env=None):
    result=subprocess.run(cmd,cwd=cwd,env=env,stdin=subprocess.DEVNULL,
                          capture_output=True,timeout=timeout)
    if result.returncode:
        raise RuntimeError("EDITOR_BOOTSTRAP_COMMAND_FAILED rc="+str(result.returncode)+
                           " stderr="+result.stderr.decode("utf-8","replace")[-500:])
    return result

def bootstrap(root):
    root=Path(root).resolve()
    initial=check(root)
    vendor=root/"VENDOR/editors"
    vendor.mkdir(parents=True,exist_ok=True)
    receipt=root/"CONTINUIDAD"/"EDITORS-BOOTSTRAP-RECEIPT.json"
    if receipt.exists():
        old=load(receipt)
        if not initial["allVerified"] or old["lockSha256"]!=initial["lockSha256"]:
            raise RuntimeError("EDITOR_BOOTSTRAP_RECEIPT_OR_BINARY_DRIFT")
        return {"status":"ALREADY_VERIFIED_NO_REINSTALL","readback":initial}
    # No blind reinstall over partial unverified or foreign trees.
    node=vendor/"node"
    aider=vendor/"aider-venv"
    if not initial["allVerified"]:
        if node.exists() or aider.exists():
            raise RuntimeError("PARTIAL_EDITOR_INSTALL_REQUIRES_RECONCILIATION")
        npm=shutil.which("npm.cmd")
        if not npm:raise RuntimeError("NPM_NOT_AVAILABLE")
        env={**os.environ,"npm_config_cache":str(vendor/"download-cache"),
             "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"}
        _run([npm,"install","--prefix",str(node),"--no-save","--ignore-scripts",
              "--no-audit","--no-fund",
              "@openai/codex@0.167.0","opencode-ai@1.19.5"],
              timeout=900,env=env,cwd=str(root))
        _run([sys.executable,"-m","venv",str(aider)],timeout=120,cwd=str(root))
        _run([str(aider/"Scripts/python.exe"),"-m","pip","install","--no-cache-dir",
              "--disable-pip-version-check","--no-input","aider-chat==0.86.2"],
              timeout=1200,cwd=str(root))
    # Create configs from source with SHA/readback; no global user files.
    for source,dest in ((root/"configs/codex-local.toml",vendor/"codex-home/config.toml"),
                        (root/"configs/opencode-local.json",vendor/"opencode-config.json")):
        if dest.exists():
            if sha_file(dest)!=sha_file(source):
                raise RuntimeError("EDITOR_CONFIG_SHA_DRIFT")
        else:
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(source.read_bytes())
            if sha_file(dest)!=sha_file(source):raise RuntimeError("EDITOR_CONFIG_READBACK_FAILED")
    result=check(root)
    if not result["allVerified"]:
        raise RuntimeError("EDITOR_TOOLCHAIN_NOT_QUALIFIED")
    info={"schema":1,"atUtc":utc(),"status":"PROJECT_PRIVATE_EDITOR_BINARIES_VERIFIED",
          "lockSha256":result["lockSha256"],"readback":result,
          "thirdPartyModelRunsRequireSeparateOriginalReceipts":True,
          "globalPATHRegistryServicesChanged":False,
          "sourceRecoveryIndependentOfEditorDownloads":True}
    write_json(receipt,info,new=True)
    return info
