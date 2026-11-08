# coding: utf-8
"""Local AI C# proposal + Roslyn compilation-only admission.

NO generated .NET assembly is ever loaded/executed. The result state is
COMPILED_UNEXECUTED, never PASS, until an independently isolated C# guest
runtime with owner-frozen functional tests is installed and E2E-qualified.
"""
from __future__ import annotations
import json,os
from pathlib import Path
import re
import subprocess
import time
import uuid
from . import csharp_compile,csharp_wasi,engine,local_runtime,source_editors,multilang
from .storage import load,sha_bytes,sha_file,utc,write_json,event,transition,verify_journal,json_bytes

def folder(root,id):
    if not re.fullmatch(r"AC-[a-f0-9]{16}",id):raise ValueError("CS_JOB_ID_UNSAFE")
    path=Path(root).resolve()/"csharpjobs"/id
    if not path.is_dir():raise RuntimeError("CS_JOB_UNKNOWN")
    return path

def create(root,specfile):
    root=engine.init(root)
    path=Path(specfile).resolve()
    if not path.is_file() or path.is_symlink() or not path.is_relative_to(root/"examples"):
        raise ValueError("CS_SPEC_MUST_BE_PROJECT_EXAMPLE")
    spec=load(path)
    basic={"language","goal","sources","targetFramework"}
    if (set(spec) not in (basic,basic|{"acceptance"})) or spec["language"]!="csharp":
        raise ValueError("CS_SPEC_SCHEMA_INVALID")
    if spec["targetFramework"]!="net10.0" or not 20<len(spec["goal"])<2500:
        raise ValueError("CS_FRAMEWORK_OR_GOAL_INVALID")
    sources=spec["sources"]
    if not isinstance(sources,dict) or not 1<=len(sources)<=5 or not all(
          re.fullmatch(r"[a-z][a-z0-9_-]{0,40}\.cs",key) and
          isinstance(val,str) and 10<=len(val)<=4000 for key,val in sources.items()):
        raise ValueError("CS_SOURCE_SEEDS_BAD")
    csharp_compile.preflight(root)
    if "acceptance" in spec:
        csharp_wasi.validate_contract(spec["acceptance"])
        csharp_wasi.preflight(root)
    ident="AC-"+uuid.uuid4().hex[:16]
    d=root/"csharpjobs"/ident
    d.mkdir(parents=True)
    write_json(d/"spec.json",spec,new=True)
    if "acceptance" in spec:
        write_json(d/"owner-acceptance.json",spec["acceptance"],new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    owner_sha=sha_file(d/"owner-acceptance.json") if "acceptance" in spec else None
    event(d/"journal.jsonl","CS_INTAKE",{"jobId":ident,"specSha":sha_file(d/"spec.json"),
          "ownerAcceptanceSha":owner_sha,
          "acceptance":"OWNER_FROZEN_PRE_INFERENCE_WASI" if owner_sha else "COMPILE_ONLY_NO_FUNCTIONAL_TESTS"})
    return {"jobId":ident,"status":"PENDING", "ownerAcceptanceSha":owner_sha,
            "purpose":"OWNER_PINNED_WASI_FUNCTIONAL" if owner_sha else "COMPILE_ONLY"}

def _state(d,status,detail):
    transition(d/"state.json",{"schema":1,"status":status,"atUtc":utc(),
               "detail":detail},d/"history")
    event(d/"journal.jsonl","CS_STATE",{"status":status,"stateSha":sha_file(d/"state.json")})

def run(root,jobid,tool):
    root=engine.init(root)
    d=folder(root,jobid)
    if load(d/"state.json")["status"]!="PENDING":
        raise RuntimeError("CS_ORIGINAL_AI_CALL_NOT_NEW_NO_REPLAY")
    if tool not in ("codex","opencode"):raise ValueError("CS_UNSUPPORTED_GENERATOR")
    spec=load(d/"spec.json")
    csharp_compile.preflight(root)
    cfg=engine.settings(root)
    if sha_file(root/cfg["llama_cpp_model_path"])!=cfg["llama_cpp_model_sha256"]:
        raise RuntimeError("CS_LOCAL_MODEL_SHA_DRIFT")
    prompt=("Complete this C# 10 / .NET 10 library. Return JSON only with key files, "
            "a map of EACH source file to COMPLETE C# source. No Markdown, no "
            "commands, no third-party packages, no analyzers, no NuGet or build scripts. "
            "Use only basic C# and built-in System namespaces. Goal: "+spec["goal"]+
            "\nOriginal source files:\n"+json.dumps(spec["sources"],ensure_ascii=False))
    record={"schema":1,"tool":tool,"promptSha":sha_bytes(prompt.encode()),
            "specSha":sha_file(d/"spec.json"),
            "ownerAcceptanceSha":sha_file(d/"owner-acceptance.json") if (d/"owner-acceptance.json").exists() else None,
            "modelSha":cfg["llama_cpp_model_sha256"]}
    write_json(d/"request.json",record,new=True)
    cmd=source_editors._command(root,tool,prompt,d/"model-final.txt")
    _state(d,"MODEL_PENDING","C# source proposal pending")
    event(d/"journal.jsonl","CS_MODEL_INTENT",{"tool":tool,
          "requestSha":sha_file(d/"request.json"),"operationId":jobid+"."+tool+".1"})
    live=local_runtime.server_info(root)
    if live["state"]=="EXITED":
        local_runtime.stop(root);live=local_runtime.server_info(root)
    if live["state"] not in ("READY","NOT_STARTED"):
        raise RuntimeError("CS_LOCAL_SERVER_UNCERTAIN")
    owned=live["state"]=="NOT_STARTED"
    if owned and local_runtime.start(root)["state"]!="READY":
        raise RuntimeError("CS_MODEL_SERVER_NOT_READY")
    try:
        started=time.monotonic()
        try:
            result=subprocess.run(cmd,cwd=str(root/"LAB-ADAPTERS"),
                              env=source_editors._env(root),stdin=subprocess.DEVNULL,
                              capture_output=True,timeout=170)
        except subprocess.TimeoutExpired:
            _state(d,"UNKNOWN","timeout: reconcile child, do not replay")
            return {"status":"UNKNOWN","jobId":jobid}
    finally:
        if owned:local_runtime.stop(root)
    output={
      "schema":1,"tool":tool,"returnCode":result.returncode,
      "stdoutSha":sha_bytes(result.stdout),"stderrSha":sha_bytes(result.stderr),
      "stdout":result.stdout.decode("utf-8","replace")[-95000:],
      "durationMs":int((time.monotonic()-started)*1000)}
    write_json(d/"original-output.json",output,new=True)
    if result.returncode:
        _state(d,"FAILED_EDITOR","original tool failed")
        return {"status":"FAILED_EDITOR","jobId":jobid}
    try:
        files,tokens=multilang._parse(tool,result.stdout,list(spec["sources"]))
    except Exception as error:
        _state(d,"FAILED_FORMAT",type(error).__name__+":"+str(error)[:120])
        return {"status":"FAILED_FORMAT","jobId":jobid}
    if (d/"repair-parent.json").is_file():
        from . import csharp_repair
        parent=load(d/"repair-parent.json")
        old_payload_sha=parent["previousSourcePayloadSha"]
        failed_same_source=(sha_bytes(json_bytes(files))==old_payload_sha)
        unchanged_required=[name for name in parent["unchangedSourceNames"]
                            if csharp_repair.canonical(files.get(name,""))==
                               csharp_repair.canonical(spec["sources"][name])]
        if failed_same_source or unchanged_required:
            event(d/"journal.jsonl","STAGNATION_REJECTED",
                  {"previousSourceSha":old_payload_sha,
                   "newProposedSha":sha_bytes(json_bytes(files)),
                   "unchangedRequiredFiles":unchanged_required})
            _state(d,"FAILED_STAGNATION","repeated unchanged failed source; no more inference in this lineage")
            return {"jobId":jobid,"status":"FAILED_STAGNATION","noReplayedOriginal":True}
    if (sha_file(d/"spec.json")!=record["specSha"] or
        ((sha_file(d/"owner-acceptance.json") if (d/"owner-acceptance.json").exists() else None)!=record["ownerAcceptanceSha"])):
        _state(d,"UNKNOWN","source or owner acceptance changed during inference")
        return {"status":"UNKNOWN","jobId":jobid}
    write_json(d/"proposed.json",{"schema":1,"files":files,"tokens":tokens},new=True)
    event(d/"journal.jsonl","CS_MODEL_READBACK",
          {"sourceSha":sha_bytes(json_bytes(files)),
           "originalOutputSha":sha_file(d/"original-output.json")})
    compiled=csharp_compile.compile_only(root,files)
    write_json(d/"compile.json",compiled,new=True)
    event(d/"journal.jsonl","CS_COMPILE",
          {"receiptSha":sha_file(d/"compile.json"),"status":compiled["status"],
           "tests":0,"noGeneratedAssemblyExecuted":True})
    if compiled["status"]=="COMPILED_UNEXECUTED":
        _state(d,"COMPILED_UNEXECUTED","admit with pinned WASI acceptance if original owner contract exists")
        if "acceptance" in spec:
            return admit_wasi(root,jobid)
    elif compiled["status"]=="FAILED_COMPILATION":
        _state(d,"FAILED_COMPILE","new job after deterministic compiler repair")
    else:
        _state(d,"UNKNOWN","compiler timeout; reconcile original execution")
    return {"jobId":jobid,"status":load(d/"state.json")["status"],
            "compile":compiled,
            "originalAIOutputSha":sha_file(d/"original-output.json")}

def inspect(root,jobid):
    d=folder(root,jobid)
    verify_journal(d/"journal.jsonl")
    return {"jobId":jobid,"state":load(d/"state.json"),
            "compile":load(d/"compile.json") if (d/"compile.json").exists() else None,
            "functionalAcceptanceProven":False,
            "originalOutputSha":sha_file(d/"original-output.json") if (d/"original-output.json").exists() else None}


def reconcile_saved(root,jobid):
    """Recover a *complete* original C# source map without a second model call."""
    root=engine.init(root)
    d=folder(root,jobid)
    state=load(d/"state.json")["status"]
    if state=="COMPILED_UNEXECUTED":
        return {"status":"ALREADY_COMPILED_NO_MODEL_REPLAY","jobId":jobid}
    if state!="FAILED_FORMAT":
        raise RuntimeError("CS_RECONCILE_ONLY_DETERMINISTIC_FORMAT_FAILURE")
    if (d/"proposed.json").exists() or (d/"compile.json").exists() or (d/"RECONCILED.json").exists():
        raise RuntimeError("CS_MODEL_RESULT_ALREADY_RECONCILED")
    request=load(d/"request.json")
    origin=load(d/"original-output.json")
    raw=origin["stdout"].encode("utf-8")
    if sha_bytes(raw)!=origin["stdoutSha"] or origin["returnCode"]!=0:
        raise RuntimeError("ORIGINAL_CODEX_STDOUT_INCOMPLETE_OR_NONZERO")
    if sha_file(d/"spec.json")!=request["specSha"]:
        raise RuntimeError("CS_REQUEST_SPEC_SHA_DRIFT")
    spec=load(d/"spec.json")
    code,tokens=multilang._parse(request["tool"],raw,list(spec["sources"]))
    if not set(code)==set(spec["sources"]):
        raise RuntimeError("CS_SOURCE_MAP_DRIFT")
    write_json(d/"proposed.json",{"schema":1,"files":code,"tokens":tokens},new=True)
    proof={"schema":1,"status":"SOURCE_RECOVERED_WITHOUT_MODEL_CALL",
           "originalOutputReceiptSha":sha_file(d/"original-output.json"),
           "sourceProposalSha":sha_bytes(json_bytes(code)),
           "modelCallsAdded":0,
           "cause":"original Codex emitted exact bare source map rather than wrapper files"}
    write_json(d/"RECONCILED.json",proof,new=True)
    event(d/"journal.jsonl","MODEL_RESPONSE_RECONCILED",{"receiptSha":sha_file(d/"RECONCILED.json"),
          "sourceSha":proof["sourceProposalSha"],"newModelCalls":0})
    compiled=csharp_compile.compile_only(root,code)
    write_json(d/"compile.json",compiled,new=True)
    event(d/"journal.jsonl","CS_COMPILE",{"receiptSha":sha_file(d/"compile.json"),
             "status":compiled["status"],"ownerTests":0})
    if compiled["status"]=="COMPILED_UNEXECUTED":
        _state(d,"COMPILED_UNEXECUTED","C# compiled by trusted compiler; functional WASI acceptance unavailable")
    elif compiled["status"]=="FAILED_COMPILATION":
        _state(d,"FAILED_COMPILE","correct new source in a separate operation")
    else:
        _state(d,"UNKNOWN","compile uncertain reconcile")
    return {"jobId":jobid,"status":load(d/"state.json")["status"],
            "newModelCalls":0,"compile":compiled,"originalReceiptSha":sha_file(d/"original-output.json")}


def repair_compiler_delta(root,jobid):
    """Repair exactly one missing terminal '}' after original Roslyn CS1513.

    This is a first-party deterministic delta, not a new AI call. The original
    model response and failed compiler receipt remain immutable and auditable.
    """
    root=engine.init(root)
    d=folder(root,jobid)
    state=load(d/"state.json")
    if state["status"]=="COMPILED_UNEXECUTED":
        return {"status":"ALREADY_COMPILED_NO_REPLAY","jobId":jobid}
    if state["status"]!="FAILED_COMPILE":
        raise RuntimeError("ONLY_DETERMINISTIC_COMPILER_FAILURE_REPAIRABLE")
    pre=load(d/"compile.json")
    if pre.get("status")!="FAILED_COMPILATION" or "CS1513" not in pre.get("compilerStdoutTail",""):
        raise RuntimeError("ONLY_CS1513_MISSING_END_BRACE_REPAIR_ALLOWED")
    if (d/"repair.json").exists() or (d/"repair-compile.json").exists():
        raise RuntimeError("PRIOR_REPAIR_EXISTS_RECONCILE")
    model=load(d/"proposed.json")
    proposed=model["files"]
    excess=[(name,code) for name,code in proposed.items()
            if code.count("{")-code.count("}")==1 and not code.rstrip().endswith("}")]
    if not excess:
        # A single missing class brace after an already-closed method can end in '}'.
        excess=[(name,code) for name,code in proposed.items()
                if code.count("{")-code.count("}")==1]
    if len(excess)!=1:
        raise RuntimeError("CS_REPAIR_NOT_UNAMBIGUOUS")
    name,old_code=excess[0]
    new_code=old_code.rstrip()+"\n}\n"
    patched={**proposed,name:new_code}
    if not old_code or len(patched)!=len(proposed) or not new_code.startswith(old_code.rstrip()):
        raise RuntimeError("CS_ONLY_APPEND_BRACE_DELTA_REQUIRED")
    change={"schema":1,"operationId":jobid+".CS1513.DETERMINISTIC-REPAIR.1",
            "atUtc":utc(),"cause":"original Roslyn CS1513 single missing terminal class brace",
            "originalModelOutputSha":sha_file(d/"original-output.json"),
            "originalFailedCompilerReceiptSha":sha_file(d/"compile.json"),
            "sourceName":name,"originalSourceSha":sha_bytes(old_code.encode()),
            "patchedSourceSha":sha_bytes(new_code.encode()),
            "newModelCalls":0,"delta":"\\n}\\n"}
    write_json(d/"repair.json",change,new=True)
    write_json(d/"repaired-sources.json",{"files":patched},new=True)
    event(d/"journal.jsonl","DETERMINISTIC_REPAIR_INTENT",
          {"repairSha":sha_file(d/"repair.json"),
           "failedCompilerSha":sha_file(d/"compile.json"),"modelCallsAdded":0})
    repaired=csharp_compile.compile_only(root,patched)
    write_json(d/"repair-compile.json",repaired,new=True)
    event(d/"journal.jsonl","DETERMINISTIC_REPAIR_READBACK",
          {"receiptSha":sha_file(d/"repair-compile.json"),
           "result":repaired["status"]})
    if repaired["status"]=="COMPILED_UNEXECUTED":
        _state(d,"COMPILED_UNEXECUTED",
               "C# fixed deterministic brace and compiled; functional WASI owner tests blocked")
    else:
        _state(d,"FAILED_COMPILE_REPAIR",
               "repair insufficient: preserve source/receipts and plan new operation")
    return {"status":load(d/"state.json")["status"],
            "jobId":jobid,"modelCallsAdded":0,
            "originalModelReceiptSha":sha_file(d/"original-output.json"),
            "repairReceiptSha":sha_file(d/"repair.json"),
            "compiledReceiptSha":sha_file(d/"repair-compile.json"),
            "compile":repaired}


def reconcile_compiler_references(root,jobid):
    """No new model call or source change. Retry only after trusted Roslyn refs fix."""
    root=engine.init(root)
    d=folder(root,jobid)
    if load(d/"state.json")["status"]=="COMPILED_UNEXECUTED":
        return {"status":"ALREADY_COMPILED_NO_REPLAY","jobId":jobid}
    if load(d/"state.json")["status"]!="FAILED_COMPILE_REPAIR":
        raise RuntimeError("CS_NOT_WAITING_FOR_REFERENCES_FIX")
    prior=load(d/"repair-compile.json")
    if "CS0103" not in prior["compilerStdoutTail"] or "Math" not in prior["compilerStdoutTail"]:
        raise RuntimeError("CS_ORIGINAL_ERROR_NOT_MISSING_MATH_REFERENCE")
    if (d/"repair-compile-references.json").exists():
        raise RuntimeError("ORIGINAL_REFERENCE_REPAIR_ALREADY_ATTEMPTED")
    project=load(d/"repaired-sources.json")
    original=load(d/"proposed.json")["files"]
    original_delta=load(d/"repair.json")
    name=original_delta["sourceName"]
    if sha_bytes(original[name].encode())!=original_delta["originalSourceSha"]:
        raise RuntimeError("CS_ORIGINAL_SOURCE_DRIFT")
    if sha_bytes(project["files"][name].encode())!=original_delta["patchedSourceSha"]:
        raise RuntimeError("CS_PATCHED_SOURCE_DRIFT")
    event(d/"journal.jsonl","CS_TRUSTED_COMPILER_REFERENCES_CORRECTION",
          {"priorCompilerReceiptSha":sha_file(d/"repair-compile.json"),
           "sourcesUnchanged":True,"modelCallsAdded":0})
    outcome=csharp_compile.compile_only(root,project["files"])
    write_json(d/"repair-compile-references.json",outcome,new=True)
    event(d/"journal.jsonl","CS_TRUSTED_COMPILER_READBACK",
          {"receiptSha":sha_file(d/"repair-compile-references.json"),
           "result":outcome["status"]})
    if outcome["status"]=="COMPILED_UNEXECUTED":
        _state(d,"COMPILED_UNEXECUTED","original C# source+deterministic brace patch compiled; no functional guest")
    else:
        _state(d,"FAILED_COMPILE_REFERENCES","cannot claim completion; check original compiler receipts")
    return {"status":load(d/"state.json")["status"],"jobId":jobid,
            "newModelCalls":0,"compiler":outcome}


def repair_missing_using(root,jobid):
    """Second and final deterministic repair: CS0103 Math, missing using System.

    Original source and both failed compiler attempts are never overwritten.
    No third heuristic repair permitted. Never execute .NET assembly on Host.
    """
    root=engine.init(root)
    d=folder(root,jobid)
    if load(d/"state.json")["status"]=="COMPILED_UNEXECUTED":
        return {"status":"ALREADY_COMPILED_NO_REPLAY","jobId":jobid}
    if load(d/"state.json")["status"]!="FAILED_COMPILE_REFERENCES":
        raise RuntimeError("CS_FINAL_REPAIR_REQUIRES_ORIGINAL_ERROR_STATE")
    err=load(d/"repair-compile-references.json")
    if "CS0103" not in err.get("compilerStdoutTail","") or "Math" not in err["compilerStdoutTail"]:
        raise RuntimeError("CS_FINAL_ERROR_NOT_SPECIFIC_MISSING_SYSTEM")
    if (d/"repair-compile-using.json").exists():
        raise RuntimeError("CS_FINAL_REPAIR_ALREADY_RECORDED_NO_REPLAY")
    src=load(d/"repaired-sources.json")["files"]
    matches=[(name,text) for name,text in src.items()
             if "Math." in text and "using System;" not in text]
    if len(matches)!=1:
        raise RuntimeError("CS_MISSING_SYSTEM_NOT_UNAMBIGUOUS")
    name,text=matches[0]
    after="using System;\n"+text
    patched={**src,name:after}
    proof={"schema":1,"operationId":jobid+".CS0103-USING-REPAIR.1",
           "sourceName":name,"previousCompilerReceiptSha":sha_file(d/"repair-compile-references.json"),
           "originalSourceSha":sha_bytes(text.encode()),
           "patchedSourceSha":sha_bytes(after.encode()),
           "delta":"using System; newline at file start",
           "newModelCalls":0,"atUtc":utc()}
    write_json(d/"repair-using.json",proof,new=True)
    write_json(d/"sources-using.json",{"files":patched},new=True)
    event(d/"journal.jsonl","CS_FINAL_DETERMINISTIC_INTENT",{
          "operationId":proof["operationId"],
          "preimageSha":proof["originalSourceSha"],
          "patchSha":proof["patchedSourceSha"],"newModelCalls":0})
    result=csharp_compile.compile_only(root,patched)
    write_json(d/"repair-compile-using.json",result,new=True)
    event(d/"journal.jsonl","CS_FINAL_COMPILER_RESULT",{
          "compilerReceiptSha":sha_file(d/"repair-compile-using.json"),
          "status":result["status"],"ownerTestCount":0})
    if result["status"]=="COMPILED_UNEXECUTED":
        _state(d,"COMPILED_UNEXECUTED",
               "Source compiled after two bounded deterministic fixes; owner functional tests BLOCKED")
    else:
        _state(d,"FAILED_FINAL","two deterministic fixes exhausted; no further auto replay")
    return {"jobId":jobid,"status":load(d/"state.json")["status"],
            "newModelCalls":0,"proofSha256":sha_file(d/"repair-using.json"),
            "compilerReceiptSha":sha_file(d/"repair-compile-using.json"),
            "result":result}


def admit_wasi(root,jobid):
    """Accept C# only from an owner-frozen pre-inference WASI contract.

    A post-hoc fixture can be diagnostic, but can never grant PASS for an
    older COMPILED_UNEXECUTED job that has no original pinned owner receipt.
    """
    root=engine.init(root)
    d=folder(root,jobid)
    state=load(d/"state.json")["status"]
    if state=="PASS":
        return {"status":"ALREADY_PASS_NO_REPLAY","verify":verify(root,jobid)}
    if state!="COMPILED_UNEXECUTED":
        raise RuntimeError("CS_WASI_REQUIRES_COMPILED_UNEXECUTED")
    spec=load(d/"spec.json")
    if "acceptance" not in spec or not (d/"owner-acceptance.json").is_file():
        raise RuntimeError("CS_CANNOT_RETROACTIVELY_INVENT_OWNER_ACCEPTANCE")
    if (d/"owner-wasi.json").is_file() or (d/"WASI-ACCEPTED-MANIFEST.json").is_file():
        raise RuntimeError("CS_WASI_PRIOR_GUEST_EXECUTION_RECONCILE")
    req=load(d/"request.json")
    owner=load(d/"owner-acceptance.json")
    if owner!=spec["acceptance"] or req.get("specSha")!=sha_file(d/"spec.json") or req.get("ownerAcceptanceSha")!=sha_file(d/"owner-acceptance.json"):
        raise RuntimeError("CS_OWNER_CONTRACT_SHA_DRIFT")
    # Sources were returned by the model and are retained. Valid deterministic
    # repairs may be included only if their source SHA receipts were verified.
    code=load(d/"proposed.json")["files"]
    source_file=d/"proposed.json"
    if (d/"sources-using.json").is_file():
        patched=load(d/"sources-using.json")["files"]
        delta=load(d/"repair-using.json")
        if sha_bytes(patched[delta["sourceName"]].encode())!=delta["patchedSourceSha"]:
            raise RuntimeError("CS_DETERMINISTIC_DELTA_SHA_DRIFT")
        code=patched;source_file=d/"sources-using.json"
    elif (d/"repaired-sources.json").is_file():
        patched=load(d/"repaired-sources.json")["files"]
        delta=load(d/"repair.json")
        if sha_bytes(patched[delta["sourceName"]].encode())!=delta["patchedSourceSha"]:
            raise RuntimeError("CS_DETERMINISTIC_DELTA_SHA_DRIFT")
        code=patched;source_file=d/"repaired-sources.json"
    event(d/"journal.jsonl","CS_WASI_OWNER_INTENT",
          {"sourceReceiptSha":sha_file(source_file),
           "ownerReceiptSha":sha_file(d/"owner-acceptance.json"),
           "operationId":jobid+".WASI.1"})
    try:
        result=csharp_wasi.run(root,code,owner,timeout=180)
    except Exception as err:
        _state(d,"UNKNOWN","WASI owner runtime uncertainty: "+type(err).__name__+"; reconcile original state")
        raise
    write_json(d/"owner-wasi.json",result,new=True)
    event(d/"journal.jsonl","CS_WASI_OWNER_RECEIPT",
          {"receiptSha":sha_file(d/"owner-wasi.json"),
           "backend":result.get("backend"),"status":result["status"],
           "ownerTestCount":result.get("independentTestCount",0)})
    if result["status"]=="PASS":
        manifest={"schema":1,"status":"CANDIDATE_ACCEPTED_NOT_INSTALLED",
                  "jobId":jobid,"editor":req["tool"],
                  "sourceReceiptSha":sha_file(source_file),
                  "sourcePayloadSha":sha_bytes(json_bytes(code)),
                  "ownerReceiptSha":sha_file(d/"owner-acceptance.json"),
                  "ownerWasiReceiptSha":sha_file(d/"owner-wasi.json"),
                  "originalModelReceiptSha":sha_file(d/"original-output.json"),
                  "originalRequestSha":sha_file(d/"request.json"),
                  "ownerTestCount":len(owner["cases"]),
                  "noNativeModelAssemblyOnHost":True,
                  "wasmSha256":result["wasmSha256"],
                  "acceptedAtUtc":utc()}
        write_json(d/"WASI-ACCEPTED-MANIFEST.json",manifest,new=True)
        event(d/"journal.jsonl","CS_WASI_OWNER_ACCEPTED",
              {"manifestSha":sha_file(d/"WASI-ACCEPTED-MANIFEST.json"),
               "originalOwnerSha":manifest["ownerReceiptSha"]})
        _state(d,"PASS","pre-inference owner-frozen functional tests passed in isolated Wasmtime")
        return {"status":"PASS","jobId":jobid,"verify":verify(root,jobid)}
    if result["status"] in ("UNKNOWN_BUILD_TIMEOUT_RECONCILE","UNKNOWN_GUEST_TIMEOUT_RECONCILE"):
        _state(d,"UNKNOWN","original WASI execution uncertain, no replay")
    else:
        _state(d,"FAILED_WASI_OWNER","original owner acceptance failed, no replay")
    return {"jobId":jobid,"status":load(d/"state.json")["status"],
            "testResult":result}

def verify(root,jobid):
    root=engine.init(root)
    d=folder(root,jobid)
    if load(d/"state.json")["status"]!="PASS":
        raise RuntimeError("CS_FUNCTIONAL_ACCEPTANCE_NOT_PASS")
    spec=load(d/"spec.json")
    if "acceptance" not in spec or load(d/"owner-acceptance.json")!=spec["acceptance"]:
        raise RuntimeError("CS_OWNER_CONTRACT_MISSING_OR_DRIFT")
    req=load(d/"request.json")
    if req["specSha"]!=sha_file(d/"spec.json") or req["ownerAcceptanceSha"]!=sha_file(d/"owner-acceptance.json"):
        raise RuntimeError("CS_OWNER_OR_SPEC_SHA_DRIFT")
    manifest=load(d/"WASI-ACCEPTED-MANIFEST.json")
    if manifest["originalModelReceiptSha"]!=sha_file(d/"original-output.json") or manifest["originalRequestSha"]!=sha_file(d/"request.json"):
        raise RuntimeError("CS_ORIGINAL_GENERATION_SHA_DRIFT")
    if manifest["ownerReceiptSha"]!=sha_file(d/"owner-acceptance.json"):
        raise RuntimeError("CS_ORIGINAL_OWNER_SHA_DRIFT")
    if manifest["ownerWasiReceiptSha"]!=sha_file(d/"owner-wasi.json"):
        raise RuntimeError("CS_WASI_RESULT_SHA_DRIFT")
    results=load(d/"owner-wasi.json")
    if (results.get("status")!="PASS" or results.get("ownerAcceptance") is not True
        or results.get("independentTestCount")!=len(spec["acceptance"]["cases"])
        or results.get("noNativeAssemblyExecuted") is not True
        or results.get("wasmSha256")!=manifest["wasmSha256"]
        or results.get("privateWasmtimeExeSha256")!=csharp_wasi.WASMTIME_SHA):
        raise RuntimeError("CS_OWNER_WASI_RECEIPT_UNVERIFIED")
    source=d/"proposed.json"
    if (d/"sources-using.json").is_file():source=d/"sources-using.json"
    elif (d/"repaired-sources.json").is_file():source=d/"repaired-sources.json"
    if sha_file(source)!=manifest["sourceReceiptSha"]:
        raise RuntimeError("CS_MODEL_SOURCE_RECEIPT_DRIFT")
    if sha_bytes(json_bytes(load(source)["files"]))!=manifest["sourcePayloadSha"]:
        raise RuntimeError("CS_SOURCE_PAYLOAD_SHA_DRIFT")
    csharp_wasi.preflight(root)
    verify_journal(d/"journal.jsonl")
    return {"verified":True,"status":"PASS","jobId":jobid,
            "ownerTestCount":len(spec["acceptance"]["cases"]),
            "wasmSha256":results["wasmSha256"],
            "nativeExecution":False}

def status(root,jobid):
    d=folder(root,jobid)
    verify_journal(d/"journal.jsonl")
    state=load(d/"state.json")
    return {"jobId":jobid,"state":state,
            "functionalAcceptanceProven":verify(root,jobid)["verified"] if state["status"]=="PASS" else False,
            "ownerPinnedAtIntake":(d/"owner-acceptance.json").exists(),
            "originalModelOutputSha":sha_file(d/"original-output.json") if (d/"original-output.json").exists() else None,
            "wasiResultSha":sha_file(d/"owner-wasi.json") if (d/"owner-wasi.json").exists() else None}
