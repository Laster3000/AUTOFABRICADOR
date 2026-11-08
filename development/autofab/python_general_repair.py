# coding: utf-8
"""R057 trusted first-party exact TS/Python type guard repair, new domain.

Original NEW local model failed its independently authored 12-case owner
because Python isinstance(True,int) is True. Fix ONLY one recognized exact
source template, never other generated code or tests. New distinct GR
original receipt, original model PG remains FAILED and immutable.
"""
from __future__ import annotations
import ast,uuid,re
from pathlib import Path
from . import engine,python_general,local_runtime,supervisor
from .storage import (load,write,write_json,sha_file,event,verify_journal,utc,transition)
_ID=re.compile(r"GR-[a-f0-9]{16}\Z")
EXACT_SOURCE=(
 "def unique_positive_ints(values):\n"
 "    if not isinstance(values, list):\n"
 "        return []\n"
 "    return sorted(list(set([item for item in values if isinstance(item, int) and item > 0])))"
)
def _original(root,jobId):
    d=python_general.directory(root,jobId)
    owner=python_general.verify(root,jobId)
    if (owner["taskId"]!="unique-positive-v1" or
        owner["finalState"]!="FAILED_ORIGINAL_OWNER" or
        owner["pureModelAccepted"] is not False or
        owner["originalOwnerCases"]!=12):
        raise RuntimeError("GRIGINAL_REPAIR_REQUIRES_FAILED_NEW_DOMAIN_OWNER")
    plan=load(d/"plan.json")
    spec,pins=python_general._spec(root,plan["sourceSpec"])
    if pins["ownerSha"]!="69aec98dbf131c258baf189e7e838449837e2e4b82733f1800e0bdae17b6ee77":
        raise RuntimeError("GRIGINAL_ORIGINAL_OWNER_SHA_NOT_RECOGNIZED")
    original=d/"model-source.py"
    if not original.is_file() or original.read_text("utf-8").strip()!=EXACT_SOURCE:
        raise ValueError("GRIGINAL_SOURCE_NOT_EXACT_RECOGNIZED_MODEL_FAILURE")
    return d,spec,pins
def create(root,originalJobId):
    root=engine.init(root)
    d,spec,pins=_original(root,originalJobId)
    work=root/"generalrepairs";work.mkdir(exist_ok=True)
    for f in work.glob("GR-*/plan.json"):
        existing=load(f)
        if existing.get("originalJobId")==originalJobId:
            return {"status":"PREEXISTING_GR_OWNER_NO_REPLAY",
                    "repairId":f.parent.name,
                    "originalState":load(f.parent/"state.json")["status"]}
    ident="GR-"+uuid.uuid4().hex[:16]
    folder=work/ident;folder.mkdir(exist_ok=False)
    plan={"schema":1,"atUtc":utc(),
      "operationId":ident+".FIRST_PARTY_OWNER_WASI.1",
      "repairId":ident,"originalJobId":originalJobId,
      "originalStreamSha":sha_file(d/"stream-receipt.json"),
      "originalSourceSha":sha_file(d/"model-source.py"),
      "originalJobReportSha":sha_file(d/"report.json"),
      "originalSpecSha":pins["specSha"],"originalOwnerSha":pins["ownerSha"],
      "originalOwnerCases":12,"noNewModelInference":True,
      "notPureModelOwnerPass":True}
    write_json(folder/"plan.json",plan,new=True)
    write_json(folder/"state.json",{"schema":1,"status":"PENDING"},new=True)
    event(folder/"journal.jsonl","GRIGINAL_FIRST_PARTY_ORIGINAL_OWNER_FROZEN",
      {"planSha":sha_file(folder/"plan.json"),
       "modelFailedOwnerReceiptSha":plan["originalJobReportSha"]})
    return {"status":"PENDING","repairId":ident,
      "originalJob":originalJobId,"originalOwnerSha":pins["ownerSha"]}
def run(root,ident):
    root=engine.init(root)
    d=root/"generalrepairs"/ident
    if not _ID.fullmatch(ident) or not (d/"plan.json").is_file():
        raise ValueError("GRIGINAL_ID_UNSAFE")
    if load(d/"state.json")["status"]!="PENDING" or (d/"report.json").exists():
        raise RuntimeError("GRIGINAL_ORIGINAL_REPAIR_ALREADY_RUN_NO_REPLAY")
    plan=load(d/"plan.json")
    parent,spec,pins=_original(root,plan["originalJobId"])
    if (sha_file(parent/"model-source.py")!=plan["originalSourceSha"] or
       sha_file(parent/"report.json")!=plan["originalJobReportSha"] or
       sha_file(parent/"stream-receipt.json")!=plan["originalStreamSha"] or
       pins["ownerSha"]!=plan["originalOwnerSha"]):
        raise RuntimeError("GRIGINAL_PARENT_ORIGINAL_SOURCE_DRIFT_NO_REPLAY")
    assert supervisor.status(root)["status"]=="STOPPED"
    assert local_runtime.server_info(root)["state"]=="NOT_STARTED"
    before=(parent/"model-source.py").read_text("utf-8")
    assert before.strip()==EXACT_SOURCE
    # Safe type guard: Python bool inherits from int, exact type check
    # is the independent owner contract. No code beyond this one exact
    # known source shape and original task is supported.
    fixed=before.replace("isinstance(item, int)","type(item) is int")
    assert fixed!=before and "type(item) is int" in fixed
    ast.parse(fixed)
    write(d/"repaired-source.py",fixed.encode("utf-8"),new=True)
    event(d/"journal.jsonl","GRIGINAL_TRUSTED_RULE_INTENT",
          {"repairRule":"R057_PY_BOOL_EXACT_INT_TYPE_GUARD",
           "sourceSha":sha_file(d/"repaired-source.py"),
           "modelInferenceCalls":0})
    tested=python_general._guest(root,spec,fixed,pins)
    write_json(d/"original-owner-wasi.json",tested,new=True)
    accepted=tested["exitCode"]==0 and tested["testCount"]==12
    outcome={"schema":1,"atUtc":utc(),"repairId":ident,
      "status":"PASS_TRUSTED_BOOL_TYPE_WASI_OWNER" if accepted else
          "FAILED_TRUSTED_BOOL_TYPE_WASI_OWNER",
      "originalJobId":plan["originalJobId"],
      "originalFailedPureModelOwner":True,
      "trustedFirstPartyRepairRule":"R057_PY_BOOL_EXACT_INT_TYPE_GUARD",
      "originalOwnerSha":pins["ownerSha"],"originalOwnerCases":12,
      "originalWasiPassedGroups":tested["testCount"] if accepted else 0,
      "repairSourceSha":sha_file(d/"repaired-source.py"),
      "originalOwnerWasiSha":sha_file(d/"original-owner-wasi.json"),
      "modelCallsAdded":0,"modelCodeNeverExecutedOnHost":True}
    write_json(d/"report.json",outcome,new=True)
    transition(d/"state.json",{"schema":1,"status":outcome["status"],
        "reportSha":sha_file(d/"report.json"),"atUtc":utc()},d/"history")
    event(d/"journal.jsonl","GRIGINAL_TRUSTED_WASI_OWNER_READBACK",
          {"status":outcome["status"],
           "reportSha":sha_file(d/"report.json")})
    return verify(root,ident)
def verify(root,ident):
    root=Path(root).resolve()
    if not isinstance(ident,str) or not _ID.fullmatch(ident):
        raise ValueError("GRIGINAL_ID_UNSAFE")
    d=root/"generalrepairs"/ident
    if not (d/"plan.json").is_file():
        raise FileNotFoundError("GRIGINAL_UNKNOWN")
    verify_journal(d/"journal.jsonl")
    plan=load(d/"plan.json")
    parent,spec,pins=_original(root,plan["originalJobId"])
    if (sha_file(parent/"model-source.py")!=plan["originalSourceSha"] or
        sha_file(parent/"report.json")!=plan["originalJobReportSha"] or
        pins["ownerSha"]!=plan["originalOwnerSha"]):
        raise RuntimeError("GRIGINAL_PARENT_SOURCE_OR_OWNER_SHA_DRIFT")
    if not (d/"report.json").is_file():
        return {"status":"GRIGINAL_PENDING_NO_REPLAY","repairId":ident}
    result=load(d/"report.json")
    if (sha_file(d/"report.json")!=load(d/"state.json")["reportSha"] or
        sha_file(d/"repaired-source.py")!=result["repairSourceSha"] or
        sha_file(d/"original-owner-wasi.json")!=result["originalOwnerWasiSha"]):
        raise RuntimeError("GRIGINAL_SHA_ORIGINAL_WASI_RECEIPT_DRIFT")
    owner=load(d/"original-owner-wasi.json")
    if result["status"]=="PASS_TRUSTED_BOOL_TYPE_WASI_OWNER":
        assert (owner["exitCode"]==0 and owner["testCount"]==12 and
                owner["originalOwnerSha"]==pins["ownerSha"] and
                owner["noHostFiles"] and owner["noHostTools"] and owner["noNetwork"])
    return {"status":"GRIGINAL_ORIGINAL_OWNER_SHA_VERIFIED",
            "repairId":ident,"outcome":result["status"],
            "originalJobId":plan["originalJobId"],
            "originalOwnerCases":12,
            "trustedFirstPartyRepair":True,"pureModelPassed":False,
            "receiptSha":sha_file(d/"report.json")}
