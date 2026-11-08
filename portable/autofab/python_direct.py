# coding: utf-8
"""R056: original local-HTTP SSE Python agent, no Codex/Ollama retry.

One immutable owner-pinned Python source job; direct pinned localhost model,
complete SSE with finish_reason STOP and SHA, original independent 8-group
owner tests in no-network/no-tool/no-file WASI guest. Exact first-party repair
may be applied AFTER the model's original failure, separately attributed.
Unknown/truncated output is terminal for this intent, never replayed.
"""
from __future__ import annotations
import ast,json,re,sys,uuid
from pathlib import Path
from . import engine,direct_agent,local_runtime,supervisor,blackbox,wasi_isolation,repair_bridge
from .storage import load,write,write_json,sha_file,sha_bytes,event,verify_journal,utc,transition
_ID=re.compile(r"PD-[a-f0-9]{16}\Z")
_STATES=frozenset(("PASS_PURE_MODEL_WASI","PASS_TRUSTED_HYBRID_WASI",
 "FAILED_ORIGINAL_OWNER_WASI","FAILED_SOURCE_FORMAT",
 "UNKNOWN_OR_TRUNCATED_STREAM_NO_REPLAY","BLOCKED_PREMODEL",
 "STOPPED_PREMODEL","STOPPED_STREAM_SAFE_BOUNDARY"))
CASES=[
 {"id":"transport","domain":"local_provider","expect":"PASS",
  "description":"Original complete SSE, thread exited, finish_reason stop and model pinned."},
 {"id":"original-owner","domain":"python_wasi","expect":"PASS",
  "description":"Original frozen eight Python unittest groups must pass in independent WASI guest."},
 {"id":"safe-end","domain":"recovery","expect":"PASS",
  "description":"Original model server stopped, supervisor stopped and original bytes SHA preserved."}]
def _path(root,ident):
    if not isinstance(ident,str) or not _ID.fullmatch(ident):
        raise ValueError("PY_DIRECT_ID_UNSAFE")
    d=Path(root).resolve()/"pythondirect"/ident
    if not (d/"plan.json").is_file():raise FileNotFoundError("PY_DIRECT_JOB_UNKNOWN")
    return d
def _fixed_spec(root,path):
    root=Path(root).resolve()
    path=Path(path).resolve()
    if (not path.is_file() or path.is_symlink()
        or not path.is_relative_to(root/"examples")):
        raise ValueError("PY_DIRECT_PLAN_MUST_BE_OWNER_EXAMPLE")
    spec=load(path)
    if not isinstance(spec,dict) or set(spec)!={
        "schema","language","goal","sourceJob","sourceSeed","ownerTest","ownerSha","maxTokens"}:
        raise ValueError("PY_DIRECT_PLAN_SCHEMA_INVALID")
    if (spec["schema"]!=1 or spec["language"]!="python"
        or spec["sourceJob"] not in ("AF-09008dfaecca4045","AF-0201095aba0d4634")
        or spec["sourceSeed"]!="examples/py_slug_repair_seed_r053.py"
        or spec["ownerTest"]!="examples/test_owner_py_slug_r053.py"
        or spec["ownerSha"]!="c814fdbb1f3ddac8dddf7e76d1155d6c3cf4ff627ac6135e99d8de5118e7bc27"
        or type(spec["maxTokens"])!=int or not 350<=spec["maxTokens"]<=1500
        or not isinstance(spec["goal"],str) or not 100<=len(spec["goal"])<=1900):
        raise ValueError("PY_DIRECT_PLAN_UNSUPPORTED")
    owner=root/spec["ownerTest"]
    seed=root/spec["sourceSeed"]
    if not owner.is_file() or sha_file(owner)!=spec["ownerSha"] or not seed.is_file():
        raise RuntimeError("PY_DIRECT_ORIGINAL_OWNER_OR_SEED_SHA_DRIFT")
    if seed.stat().st_size>4000 or owner.stat().st_size>10000:
        raise ValueError("PY_DIRECT_PINNED_OWNER_SEED_OVERSIZE")
    source=root/"work"/spec["sourceJob"]
    if not (source/"state.json").is_file() or load(source/"state.json")["status"]!="FAILED_ATTEMPT":
        raise ValueError("PY_DIRECT_SOURCE_JOB_NOT_TERMINAL_REJECTED")
    if load(source/"spec.json")["acceptance"]["sha256"]!=spec["ownerSha"]:
        raise RuntimeError("PY_DIRECT_BASE_ORIGINAL_OWNER_SHA_DRIFT")
    verify_journal(source/"journal.jsonl")
    return spec,{"specSha":sha_file(path),"ownerSha":sha_file(owner),
                 "seedSha":sha_file(seed),"sourceJobSha":sha_file(source/"spec.json"),
                 "sourceJournalSha":sha_file(source/"journal.jsonl")}
def create(root,plan):
    root=engine.init(root)
    spec,pins=_fixed_spec(root,plan)
    local_runtime.pinned_assets(root)
    folder=root/"pythondirect"
    folder.mkdir(exist_ok=True)
    for prior in folder.glob("PD-*/plan.json"):
        if load(prior).get("inputSpecSha")==pins["specSha"]:
            return {"status":"EXISTING_PY_DIRECT_INTENT_NO_REPLAY",
                    "jobId":prior.parent.name,
                    "originalState":load(prior.parent/"state.json")["status"]}
    ident="PD-"+uuid.uuid4().hex[:16]
    d=folder/ident
    d.mkdir(exist_ok=False)
    write_json(d/"owner.json",{"schema":1,"originalOwnerFile":spec["ownerTest"],
       "originalOwnerSha":pins["ownerSha"],"declaredUnittestGroups":8},new=True)
    write_json(d/"plan.json",{"schema":1,"atUtc":utc(),"jobId":ident,
       "inputSpec":str(Path(plan).resolve()),"inputSpecSha":pins["specSha"],
       "originalPins":pins,"modelSha":local_runtime.MODEL_SHA,
       "operationId":ident+".FIRST_PARTY_LOCAL_SSE.1",
       "noNativeModelEditor":True,"modelCodeOnlyGuest":True,
       "oldHistoricalUnknownJobsNeverReplayed":True},new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    b=blackbox.create(root,CASES,objective="R056 independent local Python stream completion and original owner-only WASI")
    write_json(d/"blackbox-ref.json",b,new=True)
    event(d/"journal.jsonl","PY_DIRECT_OWNER_AND_MODEL_PINNED",
      {"operationId":ident+".FIRST_PARTY_LOCAL_SSE.1",
       "planSha":sha_file(d/"plan.json"),"ownerSha":pins["ownerSha"],
       "blackbox":b["sessionId"]})
    return {"status":"PENDING","jobId":ident,"blackbox":b["sessionId"],
            "originalOwnerSha":pins["ownerSha"],"inputSpecSha":pins["specSha"]}
def _owner_guest(root,source,owner_text,owner_sha):
    root=Path(root).resolve()
    trust=wasi_isolation.wasi_preflight(root)
    vendor=root/"VENDOR/wasi-runtime"
    if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
    raw=wasi_isolation.wasi_run_one(vendor,root,{
        "slugfunc.py":source,
        "test_original_owner.py":owner_text},85,"original-owner-eight-group-guest")
    raw["originalOwnerSha"]=owner_sha
    raw["trust"]=trust
    raw["networkCapabilities"]=0
    raw["hostTools"]=0
    raw["hostFilesystemGrants"]=0
    return raw
def _source(text):
    data=json.loads(text)
    if not isinstance(data,dict) or set(data)!={"source"} or not isinstance(data["source"],str):
        raise ValueError("PY_DIRECT_RESPONSE_MUST_BE_SOURCE_ONLY_JSON")
    source=data["source"]
    if not 30<=len(source)<=5000:
        raise ValueError("PY_DIRECT_MODEL_SOURCE_LENGTH_INVALID")
    tree=ast.parse(source)
    if not any(isinstance(n,ast.FunctionDef) and n.name=="slugify_ascii"
               and len(n.args.args)==1 for n in tree.body):
        raise ValueError("PY_DIRECT_MODEL_MUST_IMPLEMENT_SLUGIFY_ASCII")
    # No imports or function calls are executed on Host (only parsed).
    return source
def _close(root,d,status,details,streamok,ownerok):
    root=Path(root).resolve()
    if status not in _STATES:raise ValueError("PY_DIRECT_INVALID_TERMINAL_STATE")
    plan=load(d/"plan.json")
    if sha_file(Path(plan["inputSpec"]))!=plan["inputSpecSha"]:
        status="UNKNOWN_OR_TRUNCATED_STREAM_NO_REPLAY"
        details={**details,"cause":"PY_DIRECT_INPUT_SPEC_SHA_CHANGED"}
    rec={"schema":1,"atUtc":utc(),"jobId":d.name,
         "status":status,"ownerOriginalSha":plan["originalPins"]["ownerSha"],
         "pureModelAccepted":status=="PASS_PURE_MODEL_WASI",
         "trustedRuleAccepted":status=="PASS_TRUSTED_HYBRID_WASI",
         "originalModelCalls":int((d/"request.json").exists()),
         "oldHistoricalUnknownJobsReplayed":0,
         "modelCodeExecutedOnHost":False,"details":details,
         "originalStreamSha":sha_file(d/"stream-receipt.json") if
            (d/"stream-receipt.json").is_file() else None,
         "ownerReceiptSha":sha_file(d/"owner-result.json") if
            (d/"owner-result.json").is_file() else None,
         "hybridReceiptSha":sha_file(d/"hybrid-owner-result.json") if
            (d/"hybrid-owner-result.json").is_file() else None}
    write_json(d/"report.json",rec,new=True)
    transition(d/"state.json",{"schema":1,"status":status,"atUtc":utc(),
                    "reportSha":sha_file(d/"report.json")},d/"history")
    event(d/"journal.jsonl","PY_DIRECT_TERMINAL",
       {"status":status,"reportSha":sha_file(d/"report.json")})
    bb=load(d/"blackbox-ref.json")["sessionId"]
    evidence=[d/"plan.json",d/"report.json",d/"journal.jsonl"]
    for case,actual,detail in (
      ("transport","PASS" if streamok else "UNKNOWN","ORIGINAL_STREAM_FINISH_STOP" if streamok else "ORIGINAL_STREAM_NOT_COMPLETE"),
      ("original-owner","PASS" if ownerok else "FAIL","INDEPENDENT_ORIGINAL_OWNER_PASS" if ownerok else "OWNER_WASI_NOT_ACCEPTED"),
      ("safe-end","PASS" if local_runtime.server_info(root)["state"]=="NOT_STARTED" and
           supervisor.status(root)["status"]=="STOPPED" else "UNKNOWN",
           "ORIGINAL_MODEL_AND_SUPERVISOR_STOPPED")):
        # Only the original sources from this job: owner evidence external to model.
        blackbox.record(root,bb,case,actual=actual,detail=detail,evidence=evidence)
    blackbox.finalize(root,bb)
    return verify(root,d.name)
def run(root,ident):
    root=engine.init(root);d=_path(root,ident)
    if load(d/"state.json")["status"]!="PENDING" or (d/"request.json").exists():
        raise RuntimeError("PY_DIRECT_ORIGINAL_MODEL_INTENT_ALREADY_STARTED_NO_REPLAY")
    if load(d/"control.json")["command"]=="STOP":
        return _close(root,d,"STOPPED_PREMODEL",
                      {"reason":"ORIGINAL_STOP_BEFORE_MODEL_SOCKET"},False,False)
    plan=load(d/"plan.json")
    spec,pins=_fixed_spec(root,plan["inputSpec"])
    if pins!=plan["originalPins"] or sha_file(d/"owner.json") is None:
        raise RuntimeError("PY_DIRECT_ORIGINAL_OWNER_PIN_DRIFT")
    if supervisor.status(root)["status"]!="STOPPED" or supervisor.status(root)["pendingQueue"]!=0:
        raise RuntimeError("PY_DIRECT_SUPERVISOR_OR_QUEUE_ACTIVE")
    if local_runtime.server_info(root)["state"]!="NOT_STARTED":
        raise RuntimeError("PY_DIRECT_MODEL_SERVER_UNCERTAIN_NO_REPLAY")
    wasi_isolation.wasi_preflight(root)
    local_runtime.pinned_assets(root)
    request_goal=("Write ONLY JSON with one key source containing COMPLETE Python source "
       "for slugfunc.py. No markdown, no tests, no commands, no tools. "
       "Implement slugify_ascii(value): EXACT ASCII [a-z0-9] and re.sub runs, "
       "return empty string for non-string values. Import re from standard library. "
       "Remember: str.replace is NOT regex. Use re.sub(r'[^a-z0-9]+','-', value.lower()).strip('-'). "
       "Preserve all original functionality. "
       "Owner goal: "+spec["goal"]+
       "\nCURRENT BROKEN SOURCE (DATA ONLY): "+
       (root/spec["sourceSeed"]).read_text("utf-8")+
       "\nOutput JSON exact format: {\"source\":\"import re\\n\\ndef slugify_ascii(value):\\n    ...\"}")
    request={"model":local_runtime.ALIAS,"stream":True,
       "stream_options":{"include_usage":True},
       "temperature":0,"max_tokens":spec["maxTokens"],
       "response_format":{"type":"json_object"},
       "messages":[{"role":"system","content":
          "Only strict JSON, Python code as escaped string, no shell commands or tests."},
                   {"role":"user","content":request_goal}]}
    # Exact request is committed BEFORE socket effects; this intent is 1-shot.
    write_json(d/"request.json",{"schema":1,"atUtc":utc(),
       "promptSha":sha_bytes(request_goal.encode()),
       "inputSpecSha":pins["specSha"],"ownerSha":pins["ownerSha"],
       "modelSha":local_runtime.MODEL_SHA,"maxTokens":spec["maxTokens"],
       "operationId":plan["operationId"],"transport":"localhost-HTTP-1-SSE"},new=True)
    event(d/"journal.jsonl","PY_DIRECT_ORIGINAL_MODEL_INTENT",
         {"operationId":plan["operationId"],"requestSha":sha_file(d/"request.json")})
    streamok=False;ownerok=False
    transport=None;start_error=None
    try:
        started=local_runtime.start(root)
        if started["state"]!="READY":
            raise RuntimeError("PY_DIRECT_MODEL_NOT_READY_AFTER_ORIGINAL_INTENT")
        transition(d/"state.json",{"schema":1,"status":"MODEL_PENDING","atUtc":utc()},d/"history")
        transport=direct_agent._stream_text(root,d,request,deadline=120)
        write_json(d/"stream-receipt.json",transport,new=True)
        event(d/"journal.jsonl","PY_DIRECT_ORIGINAL_SSE_READBACK",
              {"streamSha":sha_file(d/"stream-receipt.json"),
               "done":transport["done"],"lastFinishReason":transport.get("lastFinishReason")})
    except Exception as err:
        start_error=type(err).__name__
    finally:
        stop=local_runtime.stop(root)
        write_json(d/"model-stop.json",stop,new=True)
        event(d/"journal.jsonl","PY_DIRECT_ORIGINAL_MODEL_STOP",
              {"status":stop["state"],"modelStopSha":sha_file(d/"model-stop.json")})
    if transport and transport.get("cancelObserved"):
        if (transport.get("threadExited") and
            transport.get("idleAfterClientDisconnect",{}).get("idleVerified") and
            load(d/"model-stop.json")["state"] in ("STOPPED","STOPPED_RECONCILED")):
            return _close(root,d,"STOPPED_STREAM_SAFE_BOUNDARY",
                {"reason":"ORIGINAL_SSE_STOP_DISCONNECTED_IDLE"},False,False)
        return _close(root,d,"UNKNOWN_OR_TRUNCATED_STREAM_NO_REPLAY",
                {"reason":"ORIGINAL_STOP_BUT_NOT_PROVEN_IDLE"},False,False)
    if start_error is not None or not transport or not (transport.get("done")
        and transport.get("threadExited") and not transport.get("errors")
        and not transport.get("cancelObserved")
        and transport.get("lastFinishReason")=="stop"):
        return _close(root,d,"UNKNOWN_OR_TRUNCATED_STREAM_NO_REPLAY",
            {"errorType":start_error,"finishReason":transport.get("lastFinishReason") if transport else None,
             "streamDone":transport.get("done") if transport else False,
             "modelStopped":load(d/"model-stop.json")["state"]},False,False)
    streamok=True
    if sha_bytes(transport["resultText"].encode())!=transport["partialOrCompleteSha256"]:
        return _close(root,d,"UNKNOWN_OR_TRUNCATED_STREAM_NO_REPLAY",
             {"reason":"ORIGINAL_STREAM_CONTENT_SHA_DRIFT"},False,False)
    try:source=_source(transport["resultText"])
    except (ValueError,SyntaxError,TypeError) as err:
        return _close(root,d,"FAILED_SOURCE_FORMAT",{"errorType":type(err).__name__},True,False)
    write(d/"model-source.py",source.encode("utf-8"),new=True)
    owner_text=(root/spec["ownerTest"]).read_text("utf-8")
    accepted=_owner_guest(root,source,owner_text,pins["ownerSha"])
    write_json(d/"owner-result.json",accepted,new=True)
    event(d/"journal.jsonl","PY_DIRECT_PURE_MODEL_ORIGINAL_WASI",
          {"receiptSha":sha_file(d/"owner-result.json"),
           "passed":accepted["exitCode"]==0 and accepted["testCount"]==8})
    if accepted["exitCode"]==0 and accepted["testCount"]==8:
        return _close(root,d,"PASS_PURE_MODEL_WASI",
            {"pureModelSourceSha":sha_file(d/"model-source.py"),
             "originalOwnerGroups":8},True,True)
    # A trusted first-party repair is separately attributed. It must only
    # match the original two failed known shapes; never edit original owner.
    try:fixed,rule=repair_bridge._py_apply(
        {"goal":spec["goal"],"acceptance":{"relativePath":spec["ownerTest"]}},source)
    except (ValueError,SyntaxError):
        return _close(root,d,"FAILED_ORIGINAL_OWNER_WASI",
            {"pureModelOriginalOwnerGroups":accepted["testCount"],
             "trustedHybridRuleMatched":False},True,False)
    write(d/"hybrid-source.py",fixed.encode(),new=True)
    result=_owner_guest(root,fixed,owner_text,pins["ownerSha"])
    write_json(d/"hybrid-owner-result.json",result,new=True)
    event(d/"journal.jsonl","PY_DIRECT_FIRST_PARTY_HYBRID_OWNER",
       {"receiptSha":sha_file(d/"hybrid-owner-result.json"),
        "rule":rule,"pureModelFailedOriginalOwner":True})
    if result["exitCode"]==0 and result["testCount"]==8:
        return _close(root,d,"PASS_TRUSTED_HYBRID_WASI",
            {"rule":rule,"pureModelOriginalOwnerAccepted":False,
             "trustedHybridOwnerGroups":8},True,True)
    return _close(root,d,"FAILED_ORIGINAL_OWNER_WASI",
        {"trustedHybridAttempted":True,"trustedHybridOriginalOwnerAccepted":False},
        True,False)
def verify(root,ident):
    root=Path(root).resolve();d=_path(root,ident)
    verify_journal(d/"journal.jsonl")
    p=load(d/"plan.json")
    spec,pins=_fixed_spec(root,p["inputSpec"])
    if pins!=p["originalPins"] or p["modelSha"]!=local_runtime.MODEL_SHA:
        raise RuntimeError("PY_DIRECT_SHA_PIN_DRIFT")
    bb=load(d/"blackbox-ref.json")["sessionId"]
    state=load(d/"state.json")
    if not (d/"report.json").is_file():
        return {"status":"PY_DIRECT_PENDING_OR_UNKNOWN_NO_REPLAY",
                "jobId":ident,"state":state["status"],"blackbox":bb}
    b=blackbox.verify(root,bb)
    rec=load(d/"report.json")
    if state["reportSha"]!=sha_file(d/"report.json"):
        raise RuntimeError("PY_DIRECT_FINAL_REPORT_SHA_DRIFT")
    for key,name in (("originalStreamSha","stream-receipt.json"),
                      ("ownerReceiptSha","owner-result.json"),
                      ("hybridReceiptSha","hybrid-owner-result.json")):
        if rec[key] is not None and rec[key]!=sha_file(d/name):
            raise RuntimeError("PY_DIRECT_OWNER_OR_STREAM_TAMPERED:"+key)
    if rec["status"] in ("PASS_PURE_MODEL_WASI","PASS_TRUSTED_HYBRID_WASI"):
        receipt=load(d/("owner-result.json" if rec["pureModelAccepted"] else "hybrid-owner-result.json"))
        if not (receipt["exitCode"]==0 and receipt["testCount"]==8
            and receipt["originalOwnerSha"]==pins["ownerSha"]
            and receipt["hostFilesystemGrants"]==0 and receipt["hostTools"]==0
            and receipt["networkCapabilities"]==0):
            raise RuntimeError("PY_DIRECT_INDEPENDENT_GUEST_OWNER_NOT_ACCEPTED")
    return {"status":"PY_DIRECT_ORIGINAL_EVIDENCE_SHA_VERIFIED",
            "jobId":ident,"finalState":rec["status"],
            "pureModelAccepted":rec["pureModelAccepted"],
            "trustedHybridAccepted":rec["trustedRuleAccepted"],
            "ownerTestGroups":8,"modelCalls":rec["originalModelCalls"],
            "reportSha":sha_file(d/"report.json"),
            "blackboxSha":sha_file(root/"blackbox"/bb/"report.json"),
            "blackbox":bb}

def stop(root,ident):
    root=Path(root).resolve();d=_path(root,ident)
    state=load(d/"state.json")["status"]
    if state in _STATES or (d/"report.json").exists():
        return {"status":"TERMINAL_NO_REPLAY","jobId":ident,"originalState":state}
    ctrl=load(d/"control.json")
    if ctrl["command"]=="STOP":
        return {"status":"STOP_ALREADY_REQUESTED","jobId":ident}
    new={"schema":1,"command":"STOP","atUtc":utc(),
         "previousControlSha":sha_file(d/"control.json")}
    transition(d/"control.json",new,d/"history")
    event(d/"journal.jsonl","PY_DIRECT_ORIGINAL_STOP_REQUESTED",
          {"controlSha":sha_file(d/"control.json"),"jobId":ident})
    return {"status":"STOP_REQUESTED","jobId":ident,
            "controlSha":sha_file(d/"control.json")}
def status(root,ident):
    root=Path(root).resolve();d=_path(root,ident)
    verify_journal(d/"journal.jsonl")
    state=load(d/"state.json")["status"]
    return {"jobId":ident,"status":state,
            "control":load(d/"control.json")["command"],
            "requestRecorded":(d/"request.json").is_file(),
            "modelStreamRecorded":(d/"stream-receipt.json").is_file(),
            "originalOwnerReceipt":sha_file(d/"owner-result.json") if
                  (d/"owner-result.json").is_file() else None,
            "verified":verify(root,ident) if
                  (d/"report.json").is_file() else None}
