# coding: utf-8
"""Bounded independent C# AI repair jobs preserving original failed evidence."""
from __future__ import annotations
import json,re
from pathlib import Path
from . import csharp_jobs,engine
from .storage import event,load,sha_bytes,sha_file,json_bytes,utc,write_json

def canonical(text):
    # Only for stagnation fingerprint, never used to rewrite a source.
    return re.sub(r"\s+","",text)

def create(root,original_id):
    root=engine.init(root)
    old=csharp_jobs.folder(root,original_id)
    state=load(old/"state.json")["status"]
    if state!="FAILED_WASI_OWNER":
        raise RuntimeError("REPAIR_ONLY_AFTER_INDEPENDENT_OWNER_FAIL")
    if not (old/"owner-acceptance.json").is_file() or not (old/"proposed.json").is_file():
        raise RuntimeError("REPAIR_REQUIRES_PREPINNED_OWNER_AND_MODEL_SOURCE")
    owner=load(old/"owner-acceptance.json")
    spec=load(old/"spec.json")
    if spec.get("acceptance")!=owner:
        raise RuntimeError("REPAIR_ORIGINAL_ACCEPTANCE_DRIFT")
    evidence=load(old/"owner-wasi.json")
    if evidence["status"]!="FAILED_OWNER_ACCEPTANCE":
        raise RuntimeError("REPAIR_FAILURE_RECEIPT_INCONSISTENT")
    parentlink=load(old/"repair-parent.json") if (old/"repair-parent.json").is_file() else {}
    if parentlink:
        # Maximum two attempts (original + one child), no endless model churn.
        raise RuntimeError("REPAIR_RETRY_BUDGET_EXHAUSTED")
    for other in (root/"csharpjobs").glob("AC-*/repair-parent.json"):
        link=load(other)
        if link.get("parentJobId")==original_id:
            return {"status":"CHILD_ALREADY_CREATED_NO_DUPLICATE",
                    "jobId":other.parent.name}
    previous=load(old/"proposed.json")["files"]
    seeds=spec["sources"]
    unchanged=[name for name in seeds if canonical(seeds[name])==canonical(previous.get(name,""))]
    # The explicit contract is the diagnosis; owner test cases remain hidden
    # from model prompt. Include only pass ratio and unchanged source names.
    information=(" Earlier model attempt produced compiled source but failed "
            +str(evidence["testCount"]-evidence["independentTestCount"])
            +" independent functional cases; previous pass marker: "
            +str(evidence.get("stdoutTail","").split("=")[-1][:30])
            +". Do not repeat the former proposal SHA "
            +sha_bytes(json_bytes(previous))+". "
            +"Previously unchanged seed files: "+",".join(unchanged)+". "
            +"In particular, ensure EVERY method implements the original stated "
            "behavior rather than simply returning a seed placeholder. "
            "Return the complete two-file corrected C# source map.")
    new_spec={**spec,"goal":spec["goal"]+"\nREPAIR FEEDBACK:"+information,
              "sources":previous}
    path=root/"examples"/("csharp-repair-from-"+original_id+".json")
    if path.exists():
        if load(path)!=new_spec:raise RuntimeError("REPAIR_SPEC_EXISTING_SHA_DRIFT")
    else:
        write_json(path,new_spec,new=True)
    created=csharp_jobs.create(root,path)
    new_id=created["jobId"]
    child=csharp_jobs.folder(root,new_id)
    link={"schema":1,"atUtc":utc(),"parentJobId":original_id,
          "parentOriginalModelSha":sha_file(old/"original-output.json"),
          "parentOwnerAcceptanceSha":sha_file(old/"owner-acceptance.json"),
          "parentFailureReceiptSha":sha_file(old/"owner-wasi.json"),
          "previousSourcePayloadSha":sha_bytes(json_bytes(previous)),
          "unchangedSourceNames":unchanged,
          "newJobFrozenOwnerSha":sha_file(child/"owner-acceptance.json"),
          "newModelCallsBeforeChildRun":0,
          "maximumGenerationsInLineage":2}
    if link["newJobFrozenOwnerSha"]!=link["parentOwnerAcceptanceSha"]:
        raise RuntimeError("OWNER_PREPINNED_CONTRACT_COPY_SHA_DRIFT")
    write_json(child/"repair-parent.json",link,new=True)
    event(child/"journal.jsonl","REPAIR_PARENT_SHA_BOUND",
          {"linkSha":sha_file(child/"repair-parent.json"),
           "originalFailureReceiptSha":link["parentFailureReceiptSha"],
           "sourceShaMustChange":link["previousSourcePayloadSha"]})
    return {"jobId":new_id,"status":"REPAIR_CHILD_OWNER_FROZEN",
            "parentJobId":original_id,"ownerSha":link["newJobFrozenOwnerSha"],
            "changedRequiredSourceFiles":unchanged}
