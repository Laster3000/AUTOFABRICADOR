# coding: utf-8
"""Reusable local-model ESM/TypeScript multi-file repository factory.

One project job: SHA-pinned owner functional cases, SHA-pinned local model,
HTTP SSE original stream receipts, up to three distinct model attempts with
compiler/owner error feedback, trusted esbuild-wasm parser ONLY on Node,
all generated code executed ONLY in WASI guest with zero FS/network grants.
No native editor or npm lifecycle process can be launched by the model.

No automatic replay after UNKNOWN/timeout. Every attempt has original
intent, SHA+CAS source/receipt, append-only journal and control STOP.
"""
from __future__ import annotations
from pathlib import Path
import json,os,re,time,uuid
from . import engine,repo_graph,local_runtime,direct_agent,local_escalation,local_cuda7b,local_cuda9b
from .storage import load,sha_bytes,sha_file,utc,write_json,transition,event,verify_journal
from .isolation import IsolationUnavailable

JOB=re.compile(r"RJ-[a-f0-9]{16}\Z")
def directory(root,jobid):
    if not isinstance(jobid,str) or not JOB.fullmatch(jobid):
        raise ValueError("REPO_JOB_ID_INVALID")
    d=Path(root).resolve()/"repojobs"/jobid
    if not d.is_dir():raise FileNotFoundError("REPO_JOB_NOT_FOUND")
    return d

def _state(d,status,detail):
    transition(d/"state.json",{"schema":1,"status":status,"atUtc":utc(),
                                "detail":detail},d/"history")
    event(d/"journal.jsonl","REPO_STATE",
          {"status":status,"stateSha256":sha_file(d/"state.json")})

def create(root,spec_path):
    root=engine.init(root)
    path=Path(spec_path).resolve()
    # A new user-supplied project is accepted only after separate trusted
    # spec/owner intake. Arbitrary project paths cannot select Host files.
    if not path.is_file() or path.is_symlink() or not path.is_relative_to(root/"examples"):
        raise ValueError("REPO_OWNER_SPEC_MUST_BE_PROJECT_EXAMPLE")
    spec=load(path)
    repo_graph._valid_spec(spec)
    repo_graph.preflight(root)
    for existing in (root/"repojobs").glob("RJ-*/spec.json"):
        if load(existing)!=spec:continue
        parent=existing.parent
        state=load(parent/"state.json")["status"]
        if state=="PASS" and verify(root,parent.name)["verified"]:
            return {"jobId":parent.name,"status":"EXISTING_VERIFIED_PASS_NO_MODEL_REPLAY"}
        raise RuntimeError("DUPLICATE_REPO_INTENT_REQUIRES_RECONCILIATION_NO_REPLAY")
    jid="RJ-"+uuid.uuid4().hex[:16]
    d=root/"repojobs"/jid
    d.mkdir(parents=True)
    write_json(d/"spec.json",spec,new=True)
    owner={"schema":1,"function":spec["exportName"],"entry":spec["entry"],
           "language":spec["language"],"cases":spec["acceptance"],
           "dependencies":spec["dependencies"]}
    write_json(d/"owner-acceptance.json",owner,new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","version":1,"atUtc":utc()},new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc(),
                               "detail":"pinned owner cases, no network intent"},new=True)
    (d/"attempts").mkdir()
    event(d/"journal.jsonl","REPO_INTAKE",
       {"jobId":jid,"ownerSha256":sha_file(d/"owner-acceptance.json"),
        "specSha256":sha_file(d/"spec.json"),
        "moduleCount":len(spec["sources"]),
        "compilerSha256":repo_graph.preflight(root)["compilerWasmSha256"],
        "localModelSha256":local_runtime.MODEL_SHA})
    return {"jobId":jid,"status":"PENDING",
            "originalOwnerSha256":sha_file(d/"owner-acceptance.json")}

def stop(root,jobid):
    d=directory(root,jobid)
    state=load(d/"state.json")["status"]
    if state in ("PASS","FAILED_OWNER_ACCEPTANCE","FAILED_MODEL_FORMAT",
        "FAILED_COMPILER","CANCELLED_VERIFIED","STOPPED_PRE_INTENT","STOPPED_SAFE_BOUNDARY","UNKNOWN"):
        return {"jobId":jobid,"status":"TERMINAL_NO_STOP_MUTATION",
                "originalState":state}
    current=load(d/"control.json")
    if current["command"]=="STOP":
        return {"jobId":jobid,"status":"ALREADY_STOP_REQUESTED"}
    new={"schema":1,"command":"STOP","version":current["version"]+1,
         "atUtc":utc(),"previousSha256":sha_file(d/"control.json")}
    transition(d/"control.json",new,d/"history")
    event(d/"journal.jsonl","REPO_STOP_REQUESTED",
          {"controlSha":sha_file(d/"control.json"),"stateWas":state})
    return {"jobId":jobid,"status":"STOP_REQUESTED_ORIGINAL_CONTROL"}

def status(root,jobid):
    d=directory(root,jobid)
    verify_journal(d/"journal.jsonl")
    state=load(d/"state.json")["status"]
    attempt_data=list(sorted((d/"attempts").glob("A-*-intent.json")))
    return {"jobId":jobid,"status":state,"attemptsStarted":len(attempt_data),
      "control":load(d/"control.json")["command"],
      "originalOwnerSha":sha_file(d/"owner-acceptance.json"),
      "resultManifestExists":(d/"manifest.json").exists(),
      "originalSourceAccepted":verify(root,jobid)["verified"] if state=="PASS" else False}

def _proposal(raw,spec):
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("REPO_MODEL_RESPONSE_NOT_JSON_OBJECT")
    if set(obj)=={"files"} and isinstance(obj["files"],dict):
        files=obj["files"]
    elif set(obj)==set(spec["sources"]):
        files=obj
    else:
        raise ValueError("REPO_MODEL_FILES_WRAPPER_MISSING_OR_BAD")
    if set(files)!=set(spec["sources"]):
        raise ValueError("REPO_MODEL_SOURCE_NAMES_CHANGED")
    if any(not isinstance(text,str) or len(text)<12 or len(text)>14000 for text in files.values()):
        raise ValueError("REPO_MODEL_SOURCE_CONTENT_LENGTH")
    if sum(len(x.encode()) for x in files.values())>90000:
        raise ValueError("REPO_MODEL_SOURCE_TOTAL_BUDGET")
    return files

def _prompt(spec,previous,feedback):
    """R74 owner-independent compiler-aware repair prompt, no model test edits."""
    allowed=", ".join(spec["dependencies"]) if spec["dependencies"] else "NONE"
    goal=(
      "You are an offline JavaScript/TypeScript ESM programmer. Solve the "
      "requested GENERAL business rule correctly, including boundary input "
      "values, integer rounding and mixed types, with builtin JS only. "
      'Return ONE strict JSON object with a top-level key named "files". '
      "(or matching .ts paths) with exactly the declared source paths, "
      "complete code string values and valid JSON escapes. "
      "No Markdown, prose, shell commands, tests, tool calls or tool names. "
      "ALL source files must be used: entry MUST import the relative helper "
      "and export EXACTLY the requested function with correct arity. "
      "Do not import 'mathjs', 'lodash', Node builtins, an external library "
      "or ANY package unless it appears explicitly in the allowed dependencies. "
      "You can compute math with Math.max, Math.min, Math.ceil, Math.floor, "
      "Math.trunc and arithmetic; strings with trim, split, replace and "
      "toUpperCase. No eval, process, require, fs, network, top-level await "
      "or dynamic imports. Allowed external dependencies: "+allowed+
      ". Export: "+spec["exportName"]+". Entry: "+spec["entry"]+
      ". Language: "+spec["language"]+". USER CONTRACT: "+spec["goal"]+
      ". Replace both starter files with full implementation: "+
      json.dumps(previous,sort_keys=True,ensure_ascii=True))
    if feedback:
        goal+=(
          ". PREVIOUS ORIGINAL OWNER/COMPILER FAILURE - DO NOT REPEAT THE SAME "
          "INCORRECT SOURCE. Apply a SEMANTIC correction with valid JavaScript "
          "and no forbidden imports: "+feedback[:2400])
    return goal

def _same_owner_failure(previous,current):
    """Detect exact repeated owner failure, never a model-self-reported score.

    Owner tests and their results were signed off before model execution.
    Use the same full (index, expected, actual) signature, not just count or
    model-generated failure text; changed failures still allow an iteration.
    """
    def fingerprint(receipt):
        if receipt.get("status")!="FAILED_OWNER_WASI":
            return None
        result=receipt.get("originalOwnerResult") or {}
        cases=result.get("testResult") or {}
        failures=cases.get("failed") or []
        if not failures:
            return None
        return (cases.get("count"),cases.get("passed"),
                json.dumps(failures,sort_keys=True,ensure_ascii=True))
    first=fingerprint(previous)
    return first is not None and first==fingerprint(current)


def _feedback(result,spec=None):
    status=result.get("status","UNKNOWN")
    if status=="FAILED_ESM_GRAPH_COMPILE":
        error=result.get("compiler",{}).get("compilerStderrTail","")[-1300:]
        if "AF_BUNDLER_REJECTED_REMOTE_OR_UNAPPROVED_IMPORT" in error:
            return ("Original first-party bundler DENIED external package. "
                    "Remove the offending import entirely. Re-implement the "
                    "math or string logic with builtin Math.ceil/Math.floor/"
                    "Math.max, String.replace and array helpers; only relative "
                    "imports between the declared files are permitted. "
                    "Exact compiler error: "+error)
        return "Fix exact esbuild syntax/import errors; do not reuse invalid source. "+error
    if status=="FAILED_OWNER_WASI":
        row=result.get("originalOwnerResult",{})
        expected=row.get("testResult") or {}
        first=(expected.get("failed") or [])[:4]
        # Original owner pre-pins cases BEFORE the model call. Failed indices
        # alone were not actionable in R050: two identical IPv4 defects.
        cases=[]
        if spec is not None:
            source=spec.get("acceptance",[])
            for item in first:
                idx=item.get("i")
                if type(idx) is int and 0<=idx<len(source):
                    test=source[idx]
                    cases.append({"args":test["args"],"expected":test["expected"],
                                  "got":item.get("got")})
        return ("Original WASI owner tests FAILED. Fix the GENERAL RULE, not just cases. "
                "Owner failure examples: "+json.dumps(cases or first,ensure_ascii=True)[:1550]+
                ". Review edge cases and types, especially exact syntax and normalization. "
                "Return both full corrected modules.")
    if status=="FAILED_COMPILE_GRAPH_SHA_OR_SOURCE_CLOSURE":
        return "All source modules must be referenced, imported by the declared entry and SHA-identical; use relative imports."
    if status=="FAILED_JAVY_COMPILE":
        return "Javy failed; ensure portable ESM JavaScript only."
    return status

def run(root,jobid,*,max_tokens=2300,max_attempts=3,provider="small"):
    root=engine.init(root)
    d=directory(root,jobid)
    if load(d/"state.json")["status"]!="PENDING" or list((d/"attempts").glob("*")):
        raise RuntimeError("REPO_JOB_ALREADY_STARTED_NO_BLIND_REPLAY")
    if provider not in ("small","coder14b","cuda7b","cuda9b"):
        raise ValueError("REPO_LOCAL_MODEL_PROVIDER_NOT_PINNED")
    if not 400<=max_tokens<=3600 or not 1<=max_attempts<=3:
        raise ValueError("REPO_TOKEN_OR_ATTEMPT_BUDGET_INVALID")
    spec=load(d/"spec.json")
    repo_graph._valid_spec(spec)
    prep=repo_graph.preflight(root)
    if provider=="coder14b":
        local_escalation.pinned(root)
        model_sha=local_escalation.MODEL_SHA
        model_alias=local_escalation.ALIAS
        model_port=local_escalation.PORT
        model_server=local_escalation
    elif provider=="cuda9b":
        local_cuda9b.pinned_assets(root)
        model_sha=local_cuda9b.MODEL_SHA
        model_alias=local_cuda9b.ALIAS
        model_port=local_cuda9b.PORT
        model_server=local_cuda9b
    elif provider=="cuda7b":
        local_cuda7b.pinned_assets(root)
        model_sha=local_cuda7b.MODEL_SHA
        model_alias=local_cuda7b.ALIAS
        model_port=local_cuda7b.PORT
        model_server=local_cuda7b
    else:
        local_runtime.pinned_assets(root)
        model_sha=local_runtime.MODEL_SHA
        model_alias=local_runtime.ALIAS
        model_port=local_runtime.PORT
        model_server=local_runtime
    owner_sha=sha_file(d/"owner-acceptance.json")
    spec_sha=sha_file(d/"spec.json")
    if load(d/"control.json")["command"]=="STOP":
        _state(d,"STOPPED_PRE_INTENT","no network call, owner remains original")
        return {"status":"STOPPED_PRE_INTENT","jobId":jobid}
    server=(model_server.info(root) if provider=="coder14b" else model_server.server_info(root))
    if server["state"]=="EXITED":
        model_server.stop(root)
        server=(model_server.info(root) if provider=="coder14b" else model_server.server_info(root))
    if server["state"] not in ("READY","NOT_STARTED"):
        raise RuntimeError("REPO_UNRECONCILED_INFERENCE_SERVER_NO_REPLAY")
    owned=server["state"]=="NOT_STARTED"
    if owned and model_server.start(root)["state"]!="READY":
        raise RuntimeError("REPO_MODEL_LOCAL_SERVER_NOT_READY")
    last_src=dict(spec["sources"])
    feedback=""
    try:
        for i in range(1,max_attempts+1):
            if load(d/"control.json")["command"]=="STOP":
                _state(d,"STOPPED_SAFE_BOUNDARY","STOP before next model intent; prior complete calls retained")
                return {"jobId":jobid,"status":"STOPPED_SAFE_BOUNDARY",
                        "modelCalls":i-1,"originalOwnerSha":owner_sha}
            if sha_file(d/"owner-acceptance.json")!=owner_sha or sha_file(d/"spec.json")!=spec_sha:
                _state(d,"UNKNOWN","immutable owner case or spec drift before model call")
                return {"jobId":jobid,"status":"UNKNOWN_OWNER_DRIFT"}
            aid=f"A-{i:02d}"
            prompt=_prompt(spec,last_src,feedback)
            request={"model":model_alias,"stream":True,
                "stream_options":{"include_usage":True},"temperature":0,
                "max_tokens":max_tokens,"response_format":{"type":"json_object"},
                "messages":[{"role":"system","content":"Return only complete strict JSON. You have no tool or host access."},
                            {"role":"user","content":prompt}]}
            intent={"schema":1,"atUtc":utc(),"operationId":jobid+"."+aid+".MODEL",
               "attempt":i,"ownerSha":owner_sha,"specSha":spec_sha,
               "modelSha":model_sha,"provider":provider,"port":model_port,
               "promptSha":sha_bytes(prompt.encode()),
               "compilerWasmSha":prep["compilerWasmSha256"],
               "maxTokens":max_tokens,"maxAttempts":max_attempts,
               "nativeEditorSubprocessAllowed":False}
            prefix=d/"attempts"/aid
            write_json(Path(str(prefix)+"-intent.json"),intent,new=True)
            _state(d,"MODEL_PENDING","model attempt "+str(i))
            event(d/"journal.jsonl","REPO_MODEL_INTENT",
                {"intentSha":sha_file(Path(str(prefix)+"-intent.json")),
                 "operationId":intent["operationId"],"attempt":i})
            stream=direct_agent._stream_text(root,d,request,deadline=220 if provider in ("coder14b","cuda7b","cuda9b") else 115,port=model_port)
            sp=Path(str(prefix)+"-stream.json")
            write_json(sp,stream,new=True)
            event(d/"journal.jsonl","REPO_MODEL_STREAM_READBACK",
                {"streamSha":sha_file(sp),"modelChunks":stream["receivedChunks"],
                 "attempt":i,"done":stream["done"]})
            if stream["cancelObserved"]:
                if stream["threadExited"] and stream.get("idleAfterClientDisconnect",{}).get("idleVerified"):
                    _state(d,"CANCELLED_VERIFIED","TCP disconnected; original llama slot proven idle")
                    return {"jobId":jobid,"status":"CANCELLED_VERIFIED",
                            "modelCalls":i,"streamSha":sha_file(sp)}
                _state(d,"UNKNOWN","could not establish client disconnect and slot idle")
                return {"jobId":jobid,"status":"UNKNOWN_RECONCILE_NO_REPLAY"}
            if not stream["done"] or stream["errors"]:
                _state(d,"UNKNOWN","SSE incomplete, no blind replay")
                return {"jobId":jobid,"status":"UNKNOWN_STREAM_NOT_COMPLETE"}
            if sha_file(d/"owner-acceptance.json")!=owner_sha:
                _state(d,"UNKNOWN","owner drift after model stream")
                return {"jobId":jobid,"status":"UNKNOWN_OWNER_CONTRACT_CHANGED"}
            try:
                files=_proposal(stream["resultText"],spec)
            except (ValueError,TypeError) as e:
                failure={"schema":1,"status":"FAILED_MODEL_FORMAT","detail":str(e)[:150],
                         "originalStreamSha":sha_file(sp),"atUtc":utc()}
                write_json(Path(str(prefix)+"-failure.json"),failure,new=True)
                event(d/"journal.jsonl","REPO_MODEL_FORMAT_REJECTED",
                      {"sha":sha_file(Path(str(prefix)+"-failure.json")),"attempt":i})
                feedback="Original response was not valid exact-source-map JSON; return ONLY {\"files\":{...}}. "+str(e)
                if i==max_attempts:
                    _state(d,"FAILED_MODEL_FORMAT","max complete responses, all bad JSON")
                    return {"jobId":jobid,"status":"FAILED_MODEL_FORMAT","modelCalls":i}
                continue
            proposed=Path(str(prefix)+"-source.json")
            write_json(proposed,{"schema":1,"files":files},new=True)
            _state(d,"COMPILING","trusted bundler and WASI owner tests attempt "+str(i))
            event(d/"journal.jsonl","REPO_UNTRUSTED_SOURCE_SAVED",
                  {"sourceSha":sha_file(proposed),"attempt":i})
            try:
                result=repo_graph.build_owner(root,spec,files)
            except (ValueError,IsolationUnavailable) as exc:
                result={"status":"FAILED_COMPILER_INPUT_OR_PRECONDITION",
                        "compilerError":str(exc)[:300],
                        "originalOwnerCases":len(spec["acceptance"]),
                        "modelCodeRanOnHost":False}
            except Exception:
                # No repeat if native compiler process or WASI guest returns
                # unexpected exception; preserve original intent and sources.
                _state(d,"UNKNOWN","unclassified compiler/WASI exception; reconcile saved bytes")
                raise
            if result["status"].startswith("UNKNOWN"):
                write_json(Path(str(prefix)+"-unknown.json"),
                           {k:v for k,v in result.items() if k!="compiledSource"},new=True)
                _state(d,"UNKNOWN","unknown compile child state, no replay")
                return {"jobId":jobid,"status":"UNKNOWN_COMPILER_CHILD_NO_REPLAY"}
            to_save={k:v for k,v in result.items() if k!="compiledSource"}
            out=Path(str(prefix)+"-owner.json")
            write_json(out,to_save,new=True)
            event(d/"journal.jsonl","REPO_OWNER_WASI_TESTED",
                  {"originalOwnerReceiptSha":sha_file(out),
                   "result":result["status"],"attempt":i})
            if result["status"]=="PASS":
                bundle=Path(str(prefix)+"-bundle.js")
                data=result["compiledSource"].encode()
                with bundle.open("xb") as fd:fd.write(data)
                if sha_file(bundle)!=result["compiledSha256"]:
                    _state(d,"UNKNOWN","compiler output bytes different from receipt")
                    raise RuntimeError("REPO_BUNDLE_SOURCE_SHA_DRIFT_AFTER_WRITE")
                manifest={"schema":1,"release":"REPO_CANDIDATE_NOT_INSTALLED",
                    "atUtc":utc(),"jobId":jobid,
                    "originalOwnerSha":owner_sha,"specSha":spec_sha,
                    "selectedAttempt":i,"modelSha":model_sha,"provider":provider,
                    "compilerWasmSha":prep["compilerWasmSha256"],
                    "compilerLockSha":prep["bundlerLockSha256"],
                    "compilerHarnessSha":prep["firstPartyBundlerSha256"],
                    "originalModelIntentSha":sha_file(Path(str(prefix)+"-intent.json")),
                    "originalStreamSha":sha_file(sp),
                    "originalSourceSha":sha_file(proposed),
                    "originalWasiReceiptSha":sha_file(out),
                    "bundleSha":sha_file(bundle),
                    "ownerCaseCount":len(spec["acceptance"]),
                    "sourceFileCount":len(files),"language":spec["language"],
                    "dependencies":result["npmPinnedDependencies"],
                    "modelGeneratedHostCommandsExecuted":False,
                    "npmLifecycleScriptsExecuted":False,
                    "wasmNoFilesystemNetworkGuest":True}
                write_json(d/"manifest.json",manifest,new=True)
                event(d/"journal.jsonl","REPO_ORIGINAL_OWNER_ACCEPTANCE",
                     {"manifestSha":sha_file(d/"manifest.json"),
                      "bundleSha":sha_file(bundle),
                      "originalOwnerCases":len(spec["acceptance"]),"attempt":i})
                _state(d,"PASS","all owner tests passed under original WASI guest")
                return {"jobId":jobid,"status":"PASS",
                        "modelAttempts":i,"ownerTestsPassed":len(spec["acceptance"]),
                        "verify":verify(root,jobid)}
            # Preserve original failed test and provide deterministic compiler
            # feedback to the next DISTINCT model attempt.
            last_src=files
            feedback=_feedback(result,spec)
            if result["status"]=="FAILED_COMPILER_INPUT_OR_PRECONDITION":
                feedback+=" "+result["compilerError"]
            # The same source and same first-party failure in two attempts
            # is no progress: do not issue a third GPU request blindly.
            if i>=2 and i<max_attempts:
                prior_source=Path(str(d/"attempts"/f"A-{i-1:02d}")+"-source.json")
                prior_owner=Path(str(d/"attempts"/f"A-{i-1:02d}")+"-owner.json")
                if (prior_source.is_file() and prior_owner.is_file()
                    and sha_file(prior_source)==sha_file(proposed)
                    and load(prior_owner).get("status")==result["status"]):
                    stagnation={"schema":1,"atUtc":utc(),
                        "status":"STAGNATED_IDENTICAL_SOURCE_AND_OWNER_RESULT",
                        "previousSourceSha":sha_file(prior_source),
                        "currentSourceSha":sha_file(proposed),
                        "previousOwnerReceiptSha":sha_file(prior_owner),
                        "currentOwnerReceiptSha":sha_file(out),
                        "originalOwnerSha":owner_sha,"originalSpecSha":spec_sha,
                        "lastModelAttempt":i,"safeToRetryOriginalJob":False}
                    receipt=d/"stagnation.json"
                    write_json(receipt,stagnation,new=True)
                    event(d/"journal.jsonl","REPO_IDENTICAL_SOURCE_STAGNATION",
                          {"receiptSha":sha_file(receipt),"attempt":i})
                    _state(d,"STAGNATED_IDENTICAL_SOURCE",
                          "repeated full source and first-party failure")
                    return {"jobId":jobid,"status":"STAGNATED_IDENTICAL_SOURCE",
                            "modelCalls":i,"stagnationReceiptSha":sha_file(receipt)}
            # A second IDENTICAL original owner failure means no observed
            # semantic progress. Do not burn another local model call. This
            # only applies when a fresh attempt would otherwise be available.
            if i>=2 and i<max_attempts and result["status"]=="FAILED_OWNER_WASI":
                prior=Path(str(d/"attempts"/f"A-{i-1:02d}")+"-owner.json")
                if prior.is_file() and _same_owner_failure(load(prior),to_save):
                    stagnation={"schema":1,"atUtc":utc(),
                        "status":"STAGNATED_OWNER_NO_PROGRESS",
                        "originalOwnerSha":owner_sha,"originalSpecSha":spec_sha,
                        "previousOwnerReceiptSha":sha_file(prior),
                        "currentOwnerReceiptSha":sha_file(out),
                        "lastModelAttempt":i,
                        "reason":"TWO_IDENTICAL_ORIGINAL_OWNER_FAILURES_NO_THIRD_MODEL_CALL",
                        "safeToRetryOriginalJob":False}
                    receipt=d/"stagnation.json"
                    write_json(receipt,stagnation,new=True)
                    event(d/"journal.jsonl","REPO_STAGNATED_DETECTED",
                          {"receiptSha":sha_file(receipt),"attempt":i})
                    _state(d,"STAGNATED_OWNER_NO_PROGRESS",
                           "original owner failure identical twice; replan NEW job")
                    return {"jobId":jobid,"status":"STAGNATED_OWNER_NO_PROGRESS",
                            "modelCalls":i,"ownerSha":owner_sha,
                            "stagnationReceiptSha":sha_file(receipt)}
            if i==max_attempts:
                _state(d,"FAILED_OWNER_ACCEPTANCE",
                       "max owner-bound attempts exhausted with original receipts")
                return {"jobId":jobid,"status":"FAILED_OWNER_ACCEPTANCE",
                        "modelCalls":i,"lastFailure":result["status"],
                        "ownerSha":owner_sha}
        raise AssertionError("REPO_LOOP_BOUND_EXCEEDED")
    finally:
        if owned:
            model_server.stop(root)

def verify(root,jobid):
    root=engine.init(root)
    d=directory(root,jobid)
    if load(d/"state.json")["status"]!="PASS":
        raise RuntimeError("REPO_JOB_NOT_ORIGINALLY_ACCEPTED")
    manifest=load(d/"manifest.json")
    spec=load(d/"spec.json")
    owner=load(d/"owner-acceptance.json")
    repo_graph._valid_spec(spec)
    if not (owner["cases"]==spec["acceptance"] and
        owner["function"]==spec["exportName"] and
        owner["entry"]==spec["entry"] and
        manifest["ownerCaseCount"]==len(owner["cases"])):
        raise RuntimeError("REPO_ORIGINAL_OWNER_CONTRACT_DRIFT")
    pre=repo_graph.preflight(root)
    provider=manifest.get("provider","small")
    if provider=="coder14b":
        original_model_sha=local_escalation.MODEL_SHA
        local_escalation.pinned(root)
    elif provider=="small":
        original_model_sha=local_runtime.MODEL_SHA
    elif provider=="cuda9b":
        original_model_sha=local_cuda9b.MODEL_SHA
        local_cuda9b.pinned_assets(root)
    elif provider=="cuda7b":
        original_model_sha=local_cuda7b.MODEL_SHA
        local_cuda7b.pinned_assets(root)
    else:
        raise RuntimeError("REPO_UNKNOWN_MODEL_PROVIDER")
    if (manifest["compilerWasmSha"]!=pre["compilerWasmSha256"]
        or manifest["compilerLockSha"]!=pre["bundlerLockSha256"]
        or manifest["compilerHarnessSha"]!=pre["firstPartyBundlerSha256"]
        or manifest["modelSha"]!=original_model_sha):
        raise RuntimeError("REPO_PINNED_COMPILER_OR_MODEL_SHA_DRIFT")
    attempt=manifest["selectedAttempt"]
    prefix=d/"attempts"/f"A-{attempt:02d}"
    for key,path in (
      ("originalOwnerSha",d/"owner-acceptance.json"),
      ("specSha",d/"spec.json"),
      ("originalModelIntentSha",Path(str(prefix)+"-intent.json")),
      ("originalStreamSha",Path(str(prefix)+"-stream.json")),
      ("originalSourceSha",Path(str(prefix)+"-source.json")),
      ("originalWasiReceiptSha",Path(str(prefix)+"-owner.json")),
      ("bundleSha",Path(str(prefix)+"-bundle.js"))):
        if sha_file(path)!=manifest[key]:
            raise RuntimeError("REPO_ORIGINAL_RECEIPT_SHA_DRIFT:"+key)
    original=load(Path(str(prefix)+"-owner.json"))
    if (original["status"]!="PASS" or
        original["originalOwnerResult"]["status"]!="PASS" or
        original["originalOwnerResult"]["testCount"]!=len(owner["cases"]) or
        original["compiledSha256"]!=manifest["bundleSha"] or
        original["modelCodeRanOnNode"] is not False or
        original["npmPinnedDependencies"]!=manifest["dependencies"] or
        original["compileReceipt"]["moduleCount"]<2):
        raise RuntimeError("REPO_WASI_OR_COMPILER_RESULT_NOT_ORIGINAL")
    stream=load(Path(str(prefix)+"-stream.json"))
    if not stream["done"] or stream["cancelObserved"] or stream["errors"]:
        raise RuntimeError("REPO_ORIGINAL_MODEL_STREAM_NOT_COMPLETE")
    intent=load(Path(str(prefix)+"-intent.json"))
    if (intent["modelSha"]!=original_model_sha
       or intent["ownerSha"]!=manifest["originalOwnerSha"]
       or intent["specSha"]!=manifest["specSha"]):
        raise RuntimeError("REPO_MODEL_INTENT_OR_OWNER_DIFFERENT")
    for i in range(1,attempt):
        prior=d/"attempts"/f"A-{i:02d}"
        if not Path(str(prior)+"-intent.json").is_file() or not Path(str(prior)+"-stream.json").is_file():
            raise RuntimeError("REPO_ORIGINAL_PREVIOUS_MODEL_ATTEMPT_RECEIPTS_MISSING")
    verify_journal(d/"journal.jsonl")
    return {"verified":True,"jobId":jobid,"status":"PASS",
            "modelAttempts":attempt,"ownerCases":len(owner["cases"]),
            "sourceModules":original["compileReceipt"]["moduleCount"],
            "dependenciesPinned":list(manifest["dependencies"]),
            "compiledSha256":manifest["bundleSha"],
            "noNativeEditorOrNpmLifecycle":True}
