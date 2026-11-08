"""Aider proposal-only admission into the existing durable AUTOFABRICADOR verifier.

No original MMC7 authority imported. Only user-provided project example seed,
one source file and one pre-frozen independent unittest acceptance contract.
The Aider worker is sandboxed at the *tool policy* layer (no shell/no write);
the final Python it proposes is executed ONLY in WASI.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import time

from . import engine, local_runtime
from .storage import (atomic_snapshot,event,json_bytes,load,safe_source,sha_bytes,
                      sha_file,utc,write,write_json)

SMOKE=(
    "import unittest\n"
    "class FactorySmoke(unittest.TestCase):\n"
    "    def test_import(self):\n"
    "        import importlib\n"
    "        self.assertIsNotNone(importlib.import_module('TARGET_MODULE'))\n"
)

def admit(root,jobid,source_name,seed_rel):
    root=engine.init(root)
    folder=engine.jobdir(root,jobid)
    cfg=engine.settings(root)
    previous=load(folder/"state.json")
    if previous["status"]=="PASS":
        return {"status":"ALREADY_PASSED_NO_REPLAY","jobId":jobid}
    if previous["status"]!="PENDING":
        raise RuntimeError("AIDER_REQUIRES_FRESH_PENDING_JOB_NO_REPLAY:"+previous["status"])
    engine.gate(folder)
    spec=load(folder/"spec.json")
    if not spec.get("acceptance"):
        raise RuntimeError("AIDER_REQUIRES_OWNER_PINNED_ACCEPTANCE")
    if cfg["provider"]!="llama_cpp":
        raise RuntimeError("AIDER_CANDIDATE_REQUIRES_LOCAL_PINNED_MODEL")
    if not isinstance(source_name,str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,42}\.py",source_name):
        raise RuntimeError("AIDER_SOURCE_NAME_NOT_ALLOWLISTED")
    if not isinstance(seed_rel,str) or not re.fullmatch(r"examples/[a-z0-9_]{1,55}\.py",seed_rel):
        raise RuntimeError("AIDER_SEED_PATH_NOT_ALLOWLISTED")
    seed=root/seed_rel
    if seed.is_symlink() or not seed.is_file() or seed.stat().st_size>70000:
        raise RuntimeError("AIDER_SOURCE_SEED_MISSING_OR_UNSAFE")
    seed_sha=sha_file(seed)
    if not (root/cfg["llama_cpp_model_path"]).is_file() or sha_file(root/cfg["llama_cpp_model_path"])!=cfg["llama_cpp_model_sha256"]:
        raise RuntimeError("AIDER_MODEL_IDENTITY_DRIFT")
    executable=root/"VENDOR"/"editors"/"aider-venv"/"Scripts"/"python.exe"
    worker=root/"autofab"/"aider_worker.py"
    if not executable.is_file() or not worker.is_file():
        engine.set_state(folder,"BLOCKED_EDITOR",0,"bootstrap private Aider 0.86.2 first")
        return engine.summary(root,jobid)
    attempt=folder/"attempt-01"
    if attempt.exists():raise RuntimeError("AIDER_ATTEMPT_PREEXISTING_NO_REPLAY")
    attempt.mkdir()
    target=attempt/source_name
    write(target,seed.read_bytes(),new=True)
    if sha_file(target)!=seed_sha:raise RuntimeError("AIDER_SEED_READBACK_FAILED")
    request={
        "projectRoot":str(root),"target":str(target),
        "response":str(attempt/"AIDER-RECEIPT.json"),
        "expectedSourceSha256":seed_sha,
        "goal":spec["goal"]+" Return the COMPLETE "+source_name+" file only. Do not invoke tools or commands."
    }
    write_json(attempt/"AIDER-REQUEST.json",request,new=True)
    engine.set_state(folder,"MODEL_PENDING",1,"Aider source proposal pending")
    event(folder/"journal.jsonl","CODER_INTENT",
          {"operationId":jobid+".AIDER.1","editor":"aider","seedSha":seed_sha,
           "promptSha":sha_bytes(request["goal"].encode("utf-8")),
           "modelDigest":"sha256:"+cfg["llama_cpp_model_sha256"],
           "workerSha":sha_file(worker),"requestSha":sha_file(attempt/"AIDER-REQUEST.json")})
    status=local_runtime.server_info(root)
    if status["state"]=="EXITED":
        local_runtime.stop(root)
        status=local_runtime.server_info(root)
    if status["state"] not in ("READY","NOT_STARTED"):
        raise RuntimeError("EXTERNAL_MODEL_SERVER_STATUS_UNCERTAIN")
    started=False
    if status["state"]=="NOT_STARTED":
        live=local_runtime.start(root)
        if live["state"]!="READY":raise RuntimeError("LOCAL_MODEL_NOT_READY")
        started=True
    env={k:v for k,v in os.environ.items() if not (k.endswith(("_API_KEY","_TOKEN")) or k=="OPENAI_API_KEY")}
    env.update(PYTHONDONTWRITEBYTECODE="1",DOTNET_ADD_GLOBAL_TOOLS_TO_PATH="false",
               DO_NOT_TRACK="1",HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",NO_COLOR="1")
    env.pop("TERM",None)
    began=time.monotonic()
    try:
        done=subprocess.run([str(executable),"-B",str(worker),str(attempt/"AIDER-REQUEST.json")],
                            cwd=str(attempt),env=env,stdin=subprocess.DEVNULL,
                            capture_output=True,timeout=155)
    except Exception as error:
        engine.set_state(folder,"UNKNOWN",1,"reconcile Aider process/journal before any replay",
                         {"errorType":type(error).__name__,"error":str(error)[:330]})
        return engine.summary(root,jobid)
    finally:
        if started:
            closed=local_runtime.stop(root)
            if closed["state"] not in ("STOPPED","STOPPED_RECONCILED"):
                raise RuntimeError("OWNED_LOCAL_MODEL_STOP_NOT_VERIFIED")
    record={
        "editor":"aider","exitCode":done.returncode,
        "stdoutSha256":sha_bytes(done.stdout),"stderrSha256":sha_bytes(done.stderr),
        "stdoutTail":done.stdout.decode("utf-8","replace")[-1800:],
        "stderrTail":done.stderr.decode("utf-8","replace")[-1300:],
        "elapsedMs":int((time.monotonic()-began)*1000)}
    write_json(attempt/"EDITOR-EXECUTION.json",record,new=True)
    if done.returncode!=0 or not (attempt/"AIDER-RECEIPT.json").is_file():
        engine.set_state(folder,"UNKNOWN",1,"Aider response incomplete or failed; no blind replay",
                         {"editorExitCode":done.returncode,
                          "executionReceiptSha":sha_file(attempt/"EDITOR-EXECUTION.json")})
        return engine.summary(root,jobid)
    proposed=load(attempt/"AIDER-RECEIPT.json")
    if proposed.get("status")!="PROPOSED_UNTESTED" or not proposed.get("sourceUnchanged"):
        engine.set_state(folder,"UNKNOWN",1,"Aider proposal not trustworthy")
        return engine.summary(root,jobid)
    if sha_file(target)!=seed_sha or proposed["sourcePreimageSha256"]!=seed_sha:
        raise RuntimeError("AIDER_SEED_CAS_DRIFT")
    code=proposed["proposedSource"]
    if sha_bytes(code.encode("utf-8"))!=proposed["proposedSha256"]:
        raise RuntimeError("AIDER_PROPOSAL_SHA_MISMATCH")
    smoke=SMOKE.replace("TARGET_MODULE",source_name[:-3])
    payload={"files":{source_name:code,"test_factory_import.py":smoke}}
    work=attempt/"code"
    work.mkdir()
    files=engine.validate_payload(work,payload,cfg["max_source_bytes"])
    for name,content in files.items():
        write(safe_source(work,name),content.encode("utf-8"),new=True)
    actual=atomic_snapshot(work)
    usage={
        "provider":"aider","editorVersion":proposed["editorVersion"],
        "promptTokens":proposed.get("promptTokens"),
        "completionTokens":proposed.get("completionTokens"),
        "elapsedMs":proposed.get("elapsedMs"),
        "smokeAuthorship":"factory-first-party-not-model",
        "modelSha256":cfg["llama_cpp_model_sha256"],
        "editorExecutionReceiptSha":sha_file(attempt/"EDITOR-EXECUTION.json")
    }
    write_json(attempt/"model.json",{"payload":payload,"usage":usage,
                                   "cached":False,"modelDigest":"sha256:"+cfg["llama_cpp_model_sha256"]},new=True)
    event(folder/"journal.jsonl","CODER_READBACK",{"attempt":1,"responseSha":sha_file(attempt/"model.json"),
               "editor":"aider","aiderReceiptSha":sha_file(attempt/"AIDER-RECEIPT.json")})
    event(folder/"journal.jsonl","VERIFIER_SOURCE",{"attempt":1,"sha":sha_bytes(json_bytes(actual)),
          "factorySmokeNotAuthoredByModel":True})
    engine.set_state(folder,"DRAFT_READY_UNTESTED",1,"verify Aider proposal in WASI with owner-pinned tests",
                     {"editor":"aider","editorProposalSha":proposed["proposedSha256"]})
    result=engine.run(root,jobid)
    from . import housekeeping
    try:
        clean=housekeeping.maintain(root,apply=True)
        result["housekeeping"]={"changed":clean["changed"],"filesAffected":clean["filesAffected"]}
    except Exception as error:
        result["housekeeping"]={"status":"ERROR","detail":str(error)[:220]}
    return result
