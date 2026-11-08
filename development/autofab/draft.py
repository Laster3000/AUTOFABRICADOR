"""Generate real source without executing it; hand off to Docker when available."""
from __future__ import annotations
import json
import os
from pathlib import Path

from . import engine, progress_guard
from .providers import Ollama, LlamaCpp, ProviderError
from .storage import (atomic_snapshot,event,json_bytes,load,safe_source,sha_bytes,
                      sha_file,utc,write,write_json)

def provider_for(root,cfg):
    if cfg["provider"]=="ollama":
        return Ollama(cfg["ollama_endpoint"],cfg["model"],timeout=cfg["model_timeout_seconds"],
                      max_response_bytes=cfg["max_response_bytes"])
    if cfg["provider"]=="llama_cpp":
        return LlamaCpp(cfg["llama_cpp_endpoint"],cfg["model"],root/cfg["llama_cpp_model_path"],
                        cfg["llama_cpp_model_sha256"],timeout=cfg["model_timeout_seconds"],
                        max_response_bytes=cfg["max_response_bytes"])
    raise RuntimeError("DRAFT_REQUIRES_REAL_AI_PROVIDER")

def draft(root,jobid):
    root=engine.init(root)
    cfg=engine.settings(root)
    folder=engine.jobdir(root,jobid)
    previous=load(folder/"state.json")
    if previous["status"]=="DRAFT_READY_UNTESTED":
        return engine.summary(root,jobid)
    if previous["status"] in ("PASS","PASS_FIXTURE"):
        return {"status":"ALREADY_VERIFIED_NO_NEW_DRAFT","jobId":jobid}
    if previous["status"] in ("UNKNOWN","MODEL_PENDING","TEST_PENDING","RUNNING"):
        raise RuntimeError("UNCERTAIN_MODEL_OPERATION_NO_BLIND_REPLAY")
    if previous["status"] not in ("PENDING","BLOCKED_ISOLATION","BLOCKED_PROVIDER","FAILED_ATTEMPT","STOPPED"):
        raise RuntimeError("DRAFT_INELIGIBLE_STATE:"+previous["status"])
    engine.gate(folder)
    model=provider_for(root,cfg)
    if cfg["provider"]=="llama_cpp":
        local_path=root/cfg["llama_cpp_model_path"]
        if not local_path.is_file() or sha_file(local_path)!=cfg["llama_cpp_model_sha256"]:
            engine.set_state(folder,"BLOCKED_PROVIDER",previous["attempt"],"restore SHA-pinned local GGUF")
            return engine.summary(root,jobid)
        model_digest="sha256:"+cfg["llama_cpp_model_sha256"]
    else:
        try:
            model_digest=model.available_model()["digest"]
        except Exception as error:
            engine.set_state(folder,"BLOCKED_PROVIDER",previous["attempt"],
                             "start/verify local inference service",{"error":str(error)[:350]})
            return engine.summary(root,jobid)
    spec=load(folder/"spec.json")
    feedback=""
    if previous["attempt"]>0:
        previous_test=folder/f"attempt-{previous['attempt']:02d}"/"test.json"
        if previous_test.is_file():
            feedback=json.dumps(load(previous_test),ensure_ascii=False)[-3500:]
    for attempt_no in range(previous["attempt"]+1,min(cfg["max_attempts"],cfg["max_model_calls"])+1):
        try:engine.gate(folder)
        except InterruptedError:
            engine.set_state(folder,"STOPPED",attempt_no-1,"resume control")
            return engine.summary(root,jobid)
        attempt=folder/f"attempt-{attempt_no:02d}"
        if attempt.exists():raise RuntimeError("ATTEMPT_PREEXISTING_NO_REPLAY")
        attempt.mkdir()
        prompt=json.dumps({"goal":spec["goal"],"language":"python","previousTestFailure":feedback,
                           "requirements":"Python standard library only, tests in test_*.py using unittest"},ensure_ascii=False)
        if len(prompt)>cfg["max_prompt_chars"]:
            engine.set_state(folder,"BLOCKED_BUDGET",attempt_no-1,"reduce input context",
                             {"promptChars":len(prompt)})
            return engine.summary(root,jobid)
        key=sha_bytes(json_bytes({"prompt":prompt,"system":engine.SYSTEM,"modelDigest":model_digest,
                                  "provider":cfg["provider"],"version":engine.VERSION,
                                  "maxOutputTokens":cfg["max_output_tokens"]}))
        engine.set_state(folder,"MODEL_PENDING",attempt_no,"local coding model request pending")
        event(folder/"journal.jsonl","CODER_INTENT",{"attempt":attempt_no,"operationId":f"{jobid}.DRAFT.MODEL.{attempt_no}",
                           "promptSha":sha_bytes(prompt.encode()),"modelDigest":model_digest,"cacheKey":key})
        payload=None;cached=False
        if cfg["cache_enabled"]:
            payload=engine.cache_lookup(root,key)
            cached=payload is not None
        if cached:
            usage={"provider":cfg["provider"],"model":cfg["model"],"promptTokens":0,
                   "completionTokens":0,"elapsedMs":0,"cacheHit":True}
        else:
            try:
                model.available_model()
                payload,usage=model.generate(engine.SYSTEM,prompt,cfg["max_output_tokens"])
            except Exception as error:
                engine.set_state(folder,"UNKNOWN",attempt_no,"inspect model reply/journal before rerunning",
                                 {"errorType":type(error).__name__,"error":str(error)[:350]})
                return engine.summary(root,jobid)
        write_json(attempt/"model.json",{"payload":payload,"usage":usage,"cached":cached,
                                        "modelDigest":model_digest},new=True)
        event(folder/"journal.jsonl","CODER_READBACK",{"attempt":attempt_no,"responseSha":sha_file(attempt/"model.json")})
        repeated=progress_guard.repeated_failed_candidate(folder,payload)
        if repeated:
            evidence={"reason":"REPEATED_FAILED_SOURCE","attempt":attempt_no,"prior":repeated,"candidateSha":sha_file(attempt/"model.json")}
            write_json(attempt/"STAGNATION-RECEIPT.json",evidence,new=True)
            event(folder/"journal.jsonl","STAGNATION_GUARD",{"receiptSha":sha_file(attempt/"STAGNATION-RECEIPT.json")})
            engine.set_state(folder,"STAGNATED",attempt_no,"replan source, budget or model: identical deterministic failed candidate")
            return engine.summary(root,jobid)
        work=attempt/"code"
        work.mkdir()
        try:
            files=engine.validate_payload(work,payload,cfg["max_source_bytes"])
            for name,content in files.items():
                write(safe_source(work,name),content.encode("utf-8"),new=True)
        except (ValueError,SyntaxError,TypeError) as error:
            failure={"exitCode":-1,"reason":"STATIC_VALIDATION_ONLY","errorType":type(error).__name__,
                     "error":str(error)[:2000],"testsExecuted":False}
            write_json(attempt/"test.json",failure,new=True)
            event(folder/"journal.jsonl","STATIC_VALIDATION_FAILED",{"attempt":attempt_no,
                         "receiptSha":sha_file(attempt/"test.json")})
            feedback=json.dumps(failure,ensure_ascii=False)
            engine.set_state(folder,"FAILED_ATTEMPT",attempt_no,"retry statically invalid code")
            continue
        files_sha=atomic_snapshot(work)
        event(folder/"journal.jsonl","VERIFIER_SOURCE",{"attempt":attempt_no,"sha":sha_bytes(json_bytes(files_sha))})
        if not cached and cfg["cache_enabled"]:
            engine.cache_store(root,key,payload,usage)
        receipt={"schema":1,"attempt":attempt_no,"atUtc":utc(),
                 "status":"DRAFT_READY_UNTESTED","realAI":True,
                 "provider":cfg["provider"],"model":cfg["model"],"modelDigest":model_digest,
                 "sourceHashes":files_sha,"modelReceiptSha":sha_file(attempt/"model.json"),
                 "usage":usage,"cacheHit":cached,"testsExecuted":0,
                 "nextAction":"Verified WASI/Docker isolation required before executing generated Python"}
        write_json(attempt/"DRAFT-RECEIPT.json",receipt,new=True)
        engine.set_state(folder,"DRAFT_READY_UNTESTED",attempt_no,
                         "run tests in configured verified isolation backend",
                         {"draftReceiptSha":sha_file(attempt/"DRAFT-RECEIPT.json"),
                          "realModel":cfg["provider"]!="fixture","modelDigest":model_digest})
        return engine.summary(root,jobid)
    engine.set_state(folder,"FAILED",cfg["max_attempts"],
                     "model did not meet static validation within budget")
    return engine.summary(root,jobid)
