# coding: utf-8
"""Open natural-language local work-order intake -> ORIGINAL persistent factory.

No fixed phrase catalog. Owner-provided independent tests are frozen before
the local AI runs. Missing criteria are an explicit BLOCKED status, not
model-approved acceptance. The original supervisor/agents are sole executors.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

from . import engine, factory_pipeline, repo_graph
from .storage import event, json_bytes, load, sha_bytes, sha_file, utc, verify_journal, write_json, write

_IDENTIFIER=re.compile(r"[A-Za-z_$][A-Za-z0-9_$]{0,45}\Z")
_JOB=re.compile(r"OJ-[a-f0-9]{16}\Z")
_REQUIRED=frozenset({"schema","goal","exportName","language","acceptance"})
_ALLOWED_PROVIDERS=frozenset({"cuda7b","cuda9b","small","coder14b"})

def _load_strict(data):
    def invalid(value):
        raise ValueError("WORK_ORDER_NON_FINITE_JSON_VALUE:"+str(value))
    return json.loads(data.decode("utf-8-sig"),parse_constant=invalid)

def _path(root,path):
    root=Path(root).resolve()
    intake=root/"ENTRADAS"
    candidate=Path(path)
    if (not candidate.is_file() or candidate.is_symlink() or
        candidate.suffix.lower()!=".json" or
        candidate.resolve().parent!=intake.resolve() or
        candidate.stat().st_size>24000):
        raise ValueError("OPEN_ORDER_REQUIRE_SINGLE_REGULAR_JSON_IN_ENTRADAS")
    return candidate

def _normalize(root,path):
    candidate=_path(root,path)
    original=candidate.read_bytes()
    if not original or len(original)>24000:
        raise ValueError("OPEN_ORDER_INPUT_BYTES_INVALID")
    job="OJ-"+sha_bytes(original)[:16]
    source=_load_strict(original)
    if not isinstance(source,dict) or set(source)!=_REQUIRED:
        raise ValueError("OPEN_ORDER_KEYS_REQUIRE_GOAL_FUNCTION_LANGUAGE_AND_OWNER_ACCEPTANCE")
    if source["schema"]!=1 or source["language"]!="javascript":
        raise ValueError("OPEN_ORDER_ONLY_BOUNDED_JAVASCRIPT_ESM_V1")
    goal=source["goal"]
    fn=source["exportName"]
    if not isinstance(goal,str) or not 24<=len(goal)<=4000 or "\x00" in goal:
        raise ValueError("OPEN_ORDER_GOAL_REQUIRED_24_TO_4000")
    if not isinstance(fn,str) or not _IDENTIFIER.fullmatch(fn):
        raise ValueError("OPEN_ORDER_EXPORTED_FUNCTION_IDENTIFIER_INVALID")
    tests=source["acceptance"]
    if tests is None or tests==[]:
        return {"jobId":job,"status":"BLOCKED_OWNER_ACCEPTANCE_REQUIRED",
                "reason":"Independent examples with args and expected outputs are required before AI execution.",
                "originalInputSha":sha_bytes(original),"source":str(candidate)}
    if not isinstance(tests,list) or not 5<=len(tests)<=80:
        raise ValueError("OPEN_ORDER_OWNER_CASE_COUNT_INVALID")
    seed_rule=("export function applyRule(...args){return null;} "
               "// original empty helper module; local AI must implement\n")
    seed_index=("import {applyRule} from './rules.js'; "
                "export function "+fn+"(...args){return applyRule(...args);} "
                "// original unimplemented main module\n")
    full_goal=(goal.strip()+"\n\nOriginal owner constraints: Implement exactly two complete "
      "JavaScript ESM modules. src/rules.js exports applyRule(...args), which "
      "contains the helper implementation. src/index.js MUST import "
      "{applyRule} from './rules.js' and MUST export function "+fn+
      "(...args), which can call applyRule. Do not change exportName or "
      "source filenames. No IO, network, Node APIs, eval, dynamic import, "
      "npm installs or external dependencies. Return full source for both.")
    spec={"schema":1,"language":"javascript","goal":full_goal,
          "entry":"src/index.js","exportName":fn,
          "sources":{"src/rules.js":seed_rule,"src/index.js":seed_index},
          "acceptance":tests,"dependencies":[]}
    repo_graph._valid_spec(spec)
    return {"jobId":job,"status":"FROZEN_OWNER_INPUT_READY",
            "source":str(candidate),"originalInputSha":sha_bytes(original),
            "ownerSpec":spec,"ownerSpecSha":sha_bytes(json_bytes(spec)),
            "originalOwnerCases":len(tests),
            "meaning":"Free-form goal with independently specified owner cases; not autonomous general validation."}

def preview(root,path):
    row=_normalize(root,path)
    return {key:value for key,value in row.items() if key!="ownerSpec"}

def _folder(root,job):
    if not isinstance(job,str) or not _JOB.fullmatch(job):
        raise ValueError("OPEN_ORDER_JOB_ID_INVALID")
    return Path(root).resolve()/"workorders"/job

def status(root,job):
    d=_folder(root,job)
    if not d.is_dir():
        return {"status":"NOT_SUBMITTED","jobId":job}
    intentfile=d/"intent.json"
    if not intentfile.is_file():
        return {"jobId":job,"status":"UNKNOWN_PARTIAL_INTAKE_DO_NOT_RESUBMIT"}
    intent=load(intentfile)
    owner=Path(intent["ownerSpecPath"])
    original=Path(intent["originalInputPath"])
    if (not owner.is_file() or owner.is_symlink() or
        not original.is_file() or original.is_symlink() or
        sha_file(owner)!=intent["ownerSpecSha"] or
        sha_file(original)!=intent["originalInputSha"]):
        raise RuntimeError("OPEN_ORDER_ORIGINAL_OWNER_INPUT_DRIFT")
    verify_journal(d/"journal.jsonl")
    result={"jobId":job,"status":"ORIGINAL_OWNER_FROZEN",
            "originalOwnerCases":intent["originalOwnerCases"],
            "ownerSpecSha":intent["ownerSpecSha"],
            "provider":intent["provider"],"acceptanceMode":intent.get("acceptanceMode","wasi-native"),
            "originalInputSha":intent["originalInputSha"],
            "canBlindRetry":False}
    if not (d/"submission.json").exists():
        result["status"]="UNKNOWN_ORIGINAL_SUBMISSION_RECONCILE"
        return result
    submission=load(d/"submission.json")
    wf=submission["result"].get("workflowId")
    if wf:
        result["workflowId"]=wf
        result["originalFactory"]=factory_pipeline.reconcile(root,wf)
        result["status"]="ORIGINAL_FACTORY_"+result["originalFactory"]["status"]
    else:
        result["status"]="UNKNOWN_ORIGINAL_FACTORY_ID_NO_REPLAY"
    if result.get("originalFactory",{}).get("status")==factory_pipeline.SUCCESS_BROWSER:
        verified=result["originalFactory"].get("originalBrowserVerified") is True
        receipt=result["originalFactory"].get("originalResult") or {}
        result["portableProgram"]={
            "verified":verified,"type":"OFFLINE_BROWSER_ESM",
            "archive":receipt.get("deliveryArchive"),
            "archiveSha":receipt.get("deliveryArchiveSha"),
            "originalIndependentWasiCases":receipt.get("originalOwnerCases"),
            "originalIndependentBrowserCases":receipt.get("originalBrowserOwnerCases")}
    return result

def submit(root,path,*,provider="cuda7b",acceptance_mode="wasi-browser"):
    root=engine.init(root)
    if provider not in _ALLOWED_PROVIDERS:
        raise ValueError("OPEN_ORDER_UNPINNED_PROVIDER")
    if acceptance_mode not in ("wasi-native","wasi-browser"):
        raise ValueError("OPEN_ORDER_ACCEPTANCE_MODE_NOT_SUPPORTED")
    checked=_normalize(root,path)
    if checked["status"]=="BLOCKED_OWNER_ACCEPTANCE_REQUIRED":
        return checked
    job=checked["jobId"]
    dest=_folder(root,job)
    if dest.exists():
        return status(root,job)
    # Check exact original compiler and supervisor before creating intent.
    repo_graph.preflight(root)
    source=root/"examples"/("openorder_"+job[3:]+".json")
    if source.exists() or source.is_symlink():
        return {"jobId":job,"status":"UNKNOWN_OWNER_SOURCE_PREEXISTS_NO_REPLAY"}
    dest.mkdir(parents=True,exist_ok=False)
    (dest/"history").mkdir(exist_ok=False)
    original_path=Path(checked["source"])
    original_sha=checked["originalInputSha"]
    # Data stays immutable once copied; owner test file is freeze-before-AI.
    source_blob=json_bytes(checked["ownerSpec"])
    write(source,source_blob,new=True)
    if sha_file(source)!=checked["ownerSpecSha"] or sha_file(original_path)!=original_sha:
        raise RuntimeError("OPEN_ORDER_FROZEN_OWNER_SHA_READBACK_FAILED")
    intent={"schema":1,"jobId":job,"operationId":job+".ORIGINAL-FACTORY-SUBMISSION",
        "atUtc":utc(),"originalInputPath":str(original_path),
        "originalInputSha":original_sha,"originalInputGoal":checked["ownerSpec"]["goal"],
        "ownerSpecPath":str(source),"ownerSpecSha":checked["ownerSpecSha"],
        "originalOwnerCases":checked["originalOwnerCases"],
        "ownerAcceptanceDefinedByAI":False,
        "provider":provider,"acceptanceMode":acceptance_mode,"usingOriginalSupervisor":True,
        "hostProtectedInstallAllowed":False,
        "releaseActive":False}
    write_json(dest/"intent.json",intent,new=True)
    event(dest/"journal.jsonl","OPEN_ORDER_ORIGINAL_OWNER_FROZEN",
        {"ownerSpecSha":checked["ownerSpecSha"],
         "originalInputSha":original_sha,"caseCount":checked["originalOwnerCases"],
         "provider":provider})
    # One submission only: if tool loses connection here, status/reconcile
    # original journal, never reissue a duplicate factory effect.
    result=factory_pipeline.submit(root,source,provider=provider,acceptance_mode=acceptance_mode)
    write_json(dest/"submission.json",{"schema":1,"atUtc":utc(),"result":result,
       "originalIntentSha":sha_file(dest/"intent.json"),
       "originalOwnerSpecSha":checked["ownerSpecSha"]},new=True)
    event(dest/"journal.jsonl","OPEN_ORDER_SUBMISSION_RECORDED",
          {"originalSubmissionSha":sha_file(dest/"submission.json")})
    return {"status":"SUBMITTED_ONCE_TO_ORIGINAL_LOCAL_SUPERVISOR",
            "jobId":job,"originalOwnerCases":checked["originalOwnerCases"],
            "ownerSpecSha":checked["ownerSpecSha"],"provider":provider,
            "acceptanceMode":acceptance_mode,"factorySubmission":result}
