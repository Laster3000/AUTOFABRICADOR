# coding: utf-8
"""R057 independent two-DOMAIN Python generalization benchmark.

New COMPLETELY DIFFERENT owner tasks from prior slugify. No external
model/test tools or Host execution. One immutable model SSE request per task,
strict original independent owner SHA, WASI guest memory-only, original
blackbox and journal, NO retry of UNKNOWN/terminal. Pure-model PASS only.
"""
from __future__ import annotations
import ast,json,re,sys,uuid
from pathlib import Path
from . import engine,python_direct,direct_agent,local_runtime,supervisor,blackbox,wasi_isolation
from .storage import (load,sha_file,sha_bytes,write,write_json,event,
                      verify_journal,utc,transition)
_ID=re.compile(r"PG-[a-f0-9]{16}\Z")
TASKS={
 "unique-positive-v1":{
   "function":"unique_positive_ints","owner":"examples/test_owner_unique_positive_r057.py",
   "seed":"examples/seed_unique_positive_r057.py","cases":12},
 "merge-intervals-v1":{
   "function":"merge_intervals","owner":"examples/test_owner_merge_intervals_r057.py",
   "seed":"examples/seed_merge_intervals_r057.py","cases":14}
}
TERMINAL={"PASS_ORIGINAL_PURE_MODEL_OWNER_WASI",
          "FAILED_ORIGINAL_OWNER","FAILED_SOURCE_FORMAT",
          "UNKNOWN_INCOMPLETE_STREAM_NO_REPLAY",
          "UNKNOWN_OWNER_OR_MODEL_STOP_NO_REPLAY","STOPPED_PREMODEL","STOPPED_STREAM_IDLE_VERIFIED"}
BOX=[
 {"id":"sse-complete","domain":"python_new_model","expect":"PASS",
  "description":"Real original local model SSE finish_reason stop and no truncation."},
 {"id":"independent-owner","domain":"python_original_owner","expect":"PASS",
  "description":"Frozen original independently authored 12 or 14 owner cases accepted by WASI."},
 {"id":"live-stop","domain":"recovery","expect":"PASS",
  "description":"Original inference model server stopped and original supervisor STOPPED."}]
def directory(root,ident):
    if not isinstance(ident,str) or not _ID.fullmatch(ident):
        raise ValueError("PY_GENERAL_JOB_ID_INVALID")
    p=Path(root).resolve()/"pygeneral"/ident
    if not (p/"plan.json").is_file():raise FileNotFoundError("PY_GENERAL_JOB_UNKNOWN")
    return p
def _spec(root,path):
    root=Path(root).resolve();path=Path(path).resolve()
    if not path.is_file() or path.is_symlink() or not path.is_relative_to(root/"examples"):
        raise ValueError("PY_GENERAL_FIRST_PARTY_EXAMPLE_ONLY")
    spec=load(path)
    if (not isinstance(spec,dict) or set(spec)!=
        {"schema","taskId","language","goal","owner","ownerSha",
         "seed","seedSha","function","maxTokens"}):
        raise ValueError("PY_GENERAL_SPEC_SCHEMA_DENIED")
    task=TASKS.get(spec["taskId"])
    if not task or spec["schema"]!=1 or spec["language"]!="python":
        raise ValueError("PY_GENERAL_UNSUPPORTED_TASK")
    if (spec["owner"]!=task["owner"] or spec["seed"]!=task["seed"] or
        spec["function"]!=task["function"] or
        type(spec["maxTokens"])!=int or not 450<=spec["maxTokens"]<=2000 or
        not isinstance(spec["goal"],str) or not 120<=len(spec["goal"])<=1900):
        raise ValueError("PY_GENERAL_PINNED_FIRST_PARTY_CONTRACT_MISMATCH")
    owner=root/spec["owner"];seed=root/spec["seed"]
    if (not owner.is_file() or owner.is_symlink() or
        not seed.is_file() or seed.is_symlink() or
        sha_file(owner)!=spec["ownerSha"] or
        sha_file(seed)!=spec["seedSha"] or
        owner.stat().st_size>11000 or seed.stat().st_size>4000):
        raise RuntimeError("PY_GENERAL_ORIGINAL_OWNER_OR_SOURCE_SHA_DRIFT")
    return spec,{"specSha":sha_file(path),"ownerSha":sha_file(owner),
                 "seedSha":sha_file(seed),"expectedCases":task["cases"]}
def create(root,path):
    root=engine.init(root)
    spec,pins=_spec(root,path)
    wasi_isolation.wasi_preflight(root)
    local_runtime.pinned_assets(root)
    jobs=root/"pygeneral";jobs.mkdir(exist_ok=True)
    for existing in jobs.glob("PG-*/plan.json"):
        p=load(existing)
        if p.get("sourceSpecSha")==pins["specSha"]:
            return {"status":"PREEXISTING_ORIGINAL_OWNER_NO_MODEL_REPLAY",
                    "jobId":existing.parent.name,
                    "originalState":load(existing.parent/"state.json")["status"]}
    ident="PG-"+uuid.uuid4().hex[:16]
    d=jobs/ident;d.mkdir(exist_ok=False)
    b=blackbox.create(root,BOX,
      objective="R057 new task class Python original model generalization and independent WASI owner acceptance")
    write_json(d/"plan.json",{
      "schema":1,"atUtc":utc(),"jobId":ident,"taskId":spec["taskId"],
      "sourceSpec":str(Path(path).resolve()),"sourceSpecSha":pins["specSha"],
      "originalPins":pins,"modelSha":local_runtime.MODEL_SHA,
      "operationId":ident+".SSE.1","trustedRuleAllowed":False,
      "originalOwnerAuthorNotLocalModel":True,
      "notInstalledWindowsHostService":True},new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    write_json(d/"blackbox-ref.json",b,new=True)
    event(d/"journal.jsonl","PY_GENERAL_OWNER_PLAN_FROZEN",{
      "taskId":spec["taskId"],"planSha":sha_file(d/"plan.json"),
      "originalOwnerSha":pins["ownerSha"],"originalCases":pins["expectedCases"],
      "blackbox":b["sessionId"]})
    return {"status":"PENDING","jobId":ident,"taskId":spec["taskId"],
      "originalOwnerSha":pins["ownerSha"],"originalCases":pins["expectedCases"],
      "blackbox":b["sessionId"]}
def _parse(text,function):
    data=json.loads(text)
    if not isinstance(data,dict) or set(data)!={"source"} or not isinstance(data["source"],str):
        raise ValueError("PY_GENERAL_STRICT_SINGLE_SOURCE_JSON")
    code=data["source"]
    if not 35<=len(code)<=7500:raise ValueError("PY_GENERAL_CODE_BOUNDS")
    # The original model sometimes JSON-escapes newline twice, producing
    # literal backslash-n inside its Python source field. Unescape ONLY
    # if the first original AST parse fails, and exactly one layer. The
    # complete original model stream is kept unchanged and SHA-pinned.
    try:
        tree=ast.parse(code)
    except SyntaxError:
        if "\\n" not in code or "\n" in code:
            raise
        candidate=code.replace("\\n","\n")
        tree=ast.parse(candidate)
        code=candidate
    funcs=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==function]
    if len(funcs)!=1 or len(funcs[0].args.args)!=1:
        raise ValueError("PY_GENERAL_REQUIRED_ONE_ARG_FUNC_MISSING")
    return code
def _guest(root,spec,source,pins):
    trust=wasi_isolation.wasi_preflight(root)
    vendor=root/"VENDOR"/"wasi-runtime"
    if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
    original=(root/spec["owner"]).read_text("utf-8")
    assert sha_bytes(original.encode())==pins["ownerSha"]
    row=wasi_isolation.wasi_run_one(vendor,root,{
      "capability.py":source,"test_original_owner.py":original},
      90,"R057-independent-original-new-domain-owner")
    row["originalOwnerSha"]=pins["ownerSha"]
    row["noHostFiles"]=True;row["noHostTools"]=True;row["noNetwork"]=True
    return row
def _close(root,d,state,info,transport_ok,owner_ok):
    if state not in TERMINAL:raise ValueError("PY_GENERAL_TERMINAL_STATUS_INVALID")
    bb=load(d/"blackbox-ref.json")["sessionId"]
    verifiedStop=local_runtime.server_info(root)["state"]=="NOT_STARTED"
    superState=supervisor.status(root)
    verifiedStop=verifiedStop and superState["status"]=="STOPPED" and superState["pendingQueue"]==0
    receipt={"schema":1,"atUtc":utc(),"jobId":d.name,
      "status":state,"taskId":load(d/"plan.json")["taskId"],
      "originalOwnerSha":load(d/"plan.json")["originalPins"]["ownerSha"],
      "originalOwnerCases":load(d/"plan.json")["originalPins"]["expectedCases"],
      "pureModelAccepted":state=="PASS_ORIGINAL_PURE_MODEL_OWNER_WASI",
      "trustedRepairApplied":False,"modelCalls":int((d/"request.json").is_file()),
      "oldUnknownModelJobsReplayed":0,
      "originalStreamSha":sha_file(d/"stream-receipt.json") if
          (d/"stream-receipt.json").is_file() else None,
      "originalOwnerReceiptSha":sha_file(d/"owner-result.json") if
          (d/"owner-result.json").is_file() else None,
      "originalSourceSha":sha_file(d/"model-source.py") if
          (d/"model-source.py").is_file() else None,
      "modelCodeRanOnHost":False,
      "modelWasStopped":verifiedStop,"detail":info}
    write_json(d/"report.json",receipt,new=True)
    transition(d/"state.json",{"schema":1,"status":state,"atUtc":utc(),
      "reportSha":sha_file(d/"report.json")},d/"history")
    event(d/"journal.jsonl","PY_GENERAL_ORIGINAL_OWNER_FINAL",
      {"finalState":state,"reportSha":sha_file(d/"report.json"),
       "pureModelAccepted":receipt["pureModelAccepted"]})
    evidence=[d/"plan.json",d/"report.json",d/"journal.jsonl"]
    for label,actual,detail in (
      ("sse-complete","PASS" if transport_ok else "UNKNOWN","R057_ORIGINAL_SSE_STOP" if transport_ok else "SSE_UNKNOWN_OR_TRUNCATED"),
      ("independent-owner","PASS" if owner_ok else "FAIL","WASI_ORIGINAL_TESTS_PASS" if owner_ok else "ORIGINAL_OWNER_WASI_REJECTED"),
      ("live-stop","PASS" if verifiedStop else "UNKNOWN","MODEL_AND_SUPERVISOR_STOPPED" if verifiedStop else "MODEL_STATE_UNKNOWN")):
        blackbox.record(root,bb,label,actual=actual,detail=detail,evidence=evidence)
    blackbox.finalize(root,bb)
    return verify(root,d.name)
def run(root,ident):
    root=engine.init(root);d=directory(root,ident)
    if load(d/"state.json")["status"]!="PENDING" or (d/"request.json").is_file():
        raise RuntimeError("PY_GENERAL_ORIGINAL_MODEL_ALREADY_SENT_NO_REPLAY")
    plan=load(d/"plan.json")
    spec,pins=_spec(root,plan["sourceSpec"])
    if pins!=plan["originalPins"]:raise RuntimeError("PY_GENERAL_ORIGINAL_SHA_CHANGED")
    if supervisor.status(root)["status"]!="STOPPED" or supervisor.status(root)["pendingQueue"]!=0:
        raise RuntimeError("PY_GENERAL_SUPERVISOR_NOT_STOPPED")
    if local_runtime.server_info(root)["state"]!="NOT_STARTED":
        raise RuntimeError("PY_GENERAL_MODEL_LEASE_UNCERTAIN")
    if load(d/"control.json")["command"]=="STOP":
        return _close(root,d,"STOPPED_PREMODEL",
             {"reason":"ORIGINAL_STOP_BEFORE_INFERENCE"},False,False)
    goal_only=spec["goal"].startswith("R057_GOAL_ONLY_V2:")
    prompt=("Output ONLY a strict JSON object with exactly key source, containing "
      "complete Python source for capability.py (escaped newlines). No markdown, "
      "no tests, no shell commands, no tool use or external files. Function "+
      spec["function"]+" must be implemented with exactly one argument. "
      "Use Python standard library only. Goal: "+spec["goal"]+
      ("\nDo NOT copy initial placeholder; write full working algorithm from scratch."
       if goal_only else
       "\nOriginal defective seed (DATA ONLY): "+
       (root/spec["seed"]).read_text("utf-8"))+
      "\nReturn one JSON source field containing a full Python function.")
    payload={"model":local_runtime.ALIAS,"stream":True,
      "stream_options":{"include_usage":True},
      "temperature":0,"max_tokens":spec["maxTokens"],
      "response_format":{"type":"json_object"},
      "messages":[{"role":"system","content":
        "Only strict JSON containing one complete Python source string; no tools."},
        {"role":"user","content":prompt}]}
    write_json(d/"request.json",{"schema":1,"atUtc":utc(),
      "operationId":plan["operationId"],"promptSha":sha_bytes(prompt.encode()),
      "modelSha":plan["modelSha"],"ownerSha":pins["ownerSha"],
      "specSha":pins["specSha"],"budgetTokens":spec["maxTokens"]},new=True)
    event(d/"journal.jsonl","PY_GENERAL_ORIGINAL_SSE_INTENT",
      {"operationId":plan["operationId"],"requestSha":sha_file(d/"request.json")})
    transport=None;exception=None
    try:
        launched=local_runtime.start(root)
        if launched["state"]!="READY":
            raise RuntimeError("PY_GENERAL_MODEL_NOT_READY")
        transition(d/"state.json",{"schema":1,"status":"MODEL_PENDING","atUtc":utc()},d/"history")
        transport=direct_agent._stream_text(root,d,payload,deadline=125)
        write_json(d/"stream-receipt.json",transport,new=True)
        event(d/"journal.jsonl","PY_GENERAL_ORIGINAL_SSE_READBACK",
          {"streamSha":sha_file(d/"stream-receipt.json"),
           "finish":transport.get("lastFinishReason"),
           "done":transport.get("done")})
    except Exception as err:exception=type(err).__name__
    finally:
        stopped=local_runtime.stop(root)
        write_json(d/"model-stop.json",stopped,new=True)
        event(d/"journal.jsonl","PY_GENERAL_ORIGINAL_LOCAL_MODEL_STOPPED",
          {"stopSha":sha_file(d/"model-stop.json"),"status":stopped["state"]})
    if transport and transport.get("cancelObserved"):
        if (transport.get("threadExited") and
            transport.get("idleAfterClientDisconnect",{}).get("idleVerified")
            and local_runtime.server_info(root)["state"]=="NOT_STARTED"):
            return _close(root,d,"STOPPED_STREAM_IDLE_VERIFIED",
              {"reason":"DIRECT_SSE_STOP_ORIGINAL_SOCKET_IDLE"},False,False)
        return _close(root,d,"UNKNOWN_INCOMPLETE_STREAM_NO_REPLAY",
              {"reason":"STOP_REQUESTED_IDLE_NOT_PROVEN"},False,False)
    if (exception or not transport or not transport.get("done")
        or not transport.get("threadExited") or transport.get("errors")
        or transport.get("cancelObserved")
        or transport.get("lastFinishReason")!="stop"):
        return _close(root,d,"UNKNOWN_INCOMPLETE_STREAM_NO_REPLAY",
           {"errorType":exception,"reason":transport.get("lastFinishReason") if transport else None},
           False,False)
    if sha_bytes(transport["resultText"].encode())!=transport["partialOrCompleteSha256"]:
        return _close(root,d,"UNKNOWN_INCOMPLETE_STREAM_NO_REPLAY",
          {"reason":"MODEL_STREAM_SHA_DRIFT"},False,False)
    try:source=_parse(transport["resultText"],spec["function"])
    except (ValueError,TypeError,SyntaxError) as err:
        return _close(root,d,"FAILED_SOURCE_FORMAT",{"errorType":type(err).__name__},True,False)
    write(d/"model-source.py",source.encode("utf-8"),new=True)
    tested=_guest(root,spec,source,pins)
    write_json(d/"owner-result.json",tested,new=True)
    good=tested["exitCode"]==0 and tested["testCount"]==pins["expectedCases"]
    event(d/"journal.jsonl","PY_GENERAL_ORIGINAL_WASI_OWNER",
         {"receiptSha":sha_file(d/"owner-result.json"),
          "accepted":good,"count":tested["testCount"]})
    return _close(root,d,"PASS_ORIGINAL_PURE_MODEL_OWNER_WASI" if good else
      "FAILED_ORIGINAL_OWNER",
      {"modelSourceSha":sha_file(d/"model-source.py"),
       "originalWasiExecuted":tested["testCount"],"expected":pins["expectedCases"]},
      True,good)
def verify(root,ident):
    root=Path(root).resolve();d=directory(root,ident)
    verify_journal(d/"journal.jsonl")
    plan=load(d/"plan.json")
    spec,pins=_spec(root,plan["sourceSpec"])
    if pins!=plan["originalPins"] or local_runtime.MODEL_SHA!=plan["modelSha"]:
        raise RuntimeError("PY_GENERAL_ORIGINAL_OWNER_OR_MODEL_SHA_DRIFT")
    state=load(d/"state.json")
    if not (d/"report.json").is_file():
        return {"status":"PY_GENERAL_ORIGINAL_PENDING_NO_REPLAY",
          "jobId":ident,"state":state["status"]}
    receipt=load(d/"report.json")
    if state["reportSha"]!=sha_file(d/"report.json"):
        raise RuntimeError("PY_GENERAL_ORIGINAL_REPORT_TAMPERED")
    for key,name in (("originalStreamSha","stream-receipt.json"),
                     ("originalOwnerReceiptSha","owner-result.json"),
                     ("originalSourceSha","model-source.py")):
        if receipt[key] is not None and receipt[key]!=sha_file(d/name):
            raise RuntimeError("PY_GENERAL_ORIGINAL_EVIDENCE_SHA_DRIFT:"+key)
    if receipt["pureModelAccepted"]:
        ow=load(d/"owner-result.json")
        if (ow["exitCode"]!=0 or ow["testCount"]!=pins["expectedCases"] or
            ow["originalOwnerSha"]!=pins["ownerSha"] or
            ow["noHostFiles"] is not True or ow["noHostTools"] is not True):
            raise RuntimeError("PY_GENERAL_WASI_OWNER_MISMATCH")
    blackboxid=load(d/"blackbox-ref.json")["sessionId"]
    blackbox_receipt=blackbox.verify(root,blackboxid)
    return {"status":"PY_GENERAL_ORIGINAL_EVIDENCE_SHA_VERIFIED",
      "jobId":ident,"taskId":spec["taskId"],
      "finalState":receipt["status"],"originalOwnerCases":pins["expectedCases"],
      "pureModelAccepted":receipt["pureModelAccepted"],
      "originalSourceSha":receipt["originalSourceSha"],
      "blackbox":blackboxid,
      "originalBlackboxStatus":blackbox_receipt["status"],
      "reportSha":sha_file(d/"report.json")}


def reconcile_saved(root,ident,original_stop_receipt):
    """One-shot original source owner evaluation FROM saved complete SSE, no AI."""
    root=engine.init(root)
    d=directory(root,ident)
    if (load(d/"state.json")["status"]!="MODEL_PENDING" or
        (d/"report.json").exists() or (d/"reconciliation.json").exists() or
        (d/"owner-result.json").exists() or (d/"model-source.py").exists()):
        raise RuntimeError("PY_GENERAL_ORIGINAL_RECONCILE_ALREADY_APPLIED_NO_REPLAY")
    original=verify_journal(d/"journal.jsonl")
    assert original["events"]>=3
    if not (d/"request.json").is_file() or not (d/"stream-receipt.json").is_file():
        raise RuntimeError("PY_GENERAL_ORIGINAL_STREAM_MISSING")
    plan=load(d/"plan.json")
    spec,pins=_spec(root,plan["sourceSpec"])
    if pins!=plan["originalPins"] or plan["modelSha"]!=local_runtime.MODEL_SHA:
        raise RuntimeError("PY_GENERAL_ORIGINAL_PIN_DRIFT")
    request=load(d/"request.json")
    if (request["ownerSha"]!=pins["ownerSha"] or
        request["specSha"]!=pins["specSha"] or
        request["operationId"]!=plan["operationId"]):
        raise RuntimeError("PY_GENERAL_ORIGINAL_REQUEST_OR_OWNER_MISMATCH")
    if local_runtime.server_info(root)["state"]!="NOT_STARTED":
        raise RuntimeError("PY_GENERAL_SERVER_LEASE_STILL_ACTIVE_OR_UNKNOWN")
    sup=supervisor.status(root)
    if sup["status"]!="STOPPED" or sup["pendingQueue"]!=0:
        raise RuntimeError("PY_GENERAL_ORIGINAL_SUPERVISOR_BUSY")
    stopped=Path(original_stop_receipt).resolve()
    if (not stopped.is_file() or
        not stopped.is_relative_to(root/"CONTINUIDAD") or
        load(stopped)["status"]!="PASS_RECONCILED_EXITED_ORIGINAL_LOCAL_SERVER_LEASE_NO_MODEL_REPLAY"):
        raise RuntimeError("PY_GENERAL_ORIGINAL_MODEL_STOP_NOT_PROVEN")
    stream=load(d/"stream-receipt.json")
    if (not stream["done"] or not stream["threadExited"] or
        stream["errors"] or stream["cancelObserved"] or
        stream.get("lastFinishReason")!="stop" or
        sha_bytes(stream["resultText"].encode())!=stream["partialOrCompleteSha256"]):
        raise RuntimeError("PY_GENERAL_ORIGINAL_STREAM_NOT_COMPLETE")
    details={"schema":1,"atUtc":utc(),
       "jobId":ident,"savedOriginalRequestSha":sha_file(d/"request.json"),
       "savedOriginalStreamSha":sha_file(d/"stream-receipt.json"),
       "reconciledOriginalStopSha":sha_file(stopped),
       "originalJournalBeforeReconcileSha":sha_file(d/"journal.jsonl"),
       "noSecondModelCall":True,"originalOwnerUnchanged":True}
    write_json(d/"reconciliation.json",details,new=True)
    event(d/"journal.jsonl","PY_GENERAL_SAVED_ORIGINAL_STREAM_RECONCILED_NO_MODEL_REPLAY",
        {"originalStreamSha":details["savedOriginalStreamSha"],
         "reconciliationReceiptSha":sha_file(d/"reconciliation.json")})
    try:
        source=_parse(stream["resultText"],spec["function"])
    except (ValueError,SyntaxError,TypeError) as err:
        return _close(root,d,"FAILED_SOURCE_FORMAT",
             {"recoveredFromOriginalSavedSSE":True,"parseErrorType":type(err).__name__,
              "reconciliationSha":sha_file(d/"reconciliation.json")},True,False)
    write(d/"model-source.py",source.encode(),new=True)
    owner=_guest(root,spec,source,pins)
    write_json(d/"owner-result.json",owner,new=True)
    pass_=(owner["exitCode"]==0 and owner["testCount"]==pins["expectedCases"])
    event(d/"journal.jsonl","PY_GENERAL_RECONCILED_ORIGINAL_OWNER_WASI",
          {"ownerReceiptSha":sha_file(d/"owner-result.json"),
           "pass":pass_,"cases":owner["testCount"],
           "noNewModelCall":True})
    return _close(root,d,
          "PASS_ORIGINAL_PURE_MODEL_OWNER_WASI" if pass_ else
          "FAILED_ORIGINAL_OWNER",
          {"recoveredFromOriginalSavedSSE":True,
           "reconciliationSha":sha_file(d/"reconciliation.json"),
           "ownerCasesExecuted":owner["testCount"],
           "modelCallsAdded":0},True,pass_)

def stop(root,ident):
    root=Path(root).resolve();d=directory(root,ident)
    state=load(d/"state.json")["status"]
    if state in TERMINAL or (d/"report.json").is_file():
        return {"status":"ORIGINAL_TERMINAL_NO_REPLAY","jobId":ident,
                "originalState":state}
    prior=load(d/"control.json")
    if prior["command"]=="STOP":
        return {"status":"STOP_ALREADY_REQUESTED","jobId":ident}
    updated={"schema":1,"atUtc":utc(),"command":"STOP",
             "priorControlSha":sha_file(d/"control.json")}
    transition(d/"control.json",updated,d/"history")
    event(d/"journal.jsonl","PY_GENERAL_ORIGINAL_STOP_REQUESTED",
          {"controlSha":sha_file(d/"control.json")})
    return {"status":"STOP_REQUESTED","jobId":ident,
            "controlSha":sha_file(d/"control.json")}
def status(root,ident):
    root=Path(root).resolve();d=directory(root,ident)
    verify_journal(d/"journal.jsonl")
    state=load(d/"state.json")["status"]
    return {"status":state,"jobId":ident,
            "control":load(d/"control.json")["command"],
            "originalModelIntentRecorded":(d/"request.json").is_file(),
            "originalStreamRecorded":(d/"stream-receipt.json").is_file(),
            "originalOwnerReceiptSha":sha_file(d/"owner-result.json")
                if (d/"owner-result.json").is_file() else None,
            "verified":verify(root,ident) if (d/"report.json").is_file() else None}
