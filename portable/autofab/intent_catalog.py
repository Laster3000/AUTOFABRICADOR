# coding: utf-8
"""Closed, independently owned natural-language intent catalog.

This is deliberately not a generic NLP interpretation engine. Unknown or
ambiguous requests must fail closed. Each selected owner acceptance contract
is deterministic and is frozen BEFORE local model generation. Only the
original factory_pipeline and original supervisor can launch jobs.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata

from . import engine, factory_pipeline, repo_graph
from .storage import event, load, sha_file, sha_bytes, utc, verify_journal, write_json

CATALOG_VERSION = "OWNER-INTENT-CATALOG.1"
ALIASES = {
    "descuento": (
        "calculadora de descuentos", "crea una calculadora de descuentos",
        "crear calculadora de descuentos", "create discount calculator",
        "fabrica calculadora de descuentos",
    ),
    "importes": (
        "sumador de importes", "crea un sumador de importes",
        "crear sumador de importes", "create invoice totals calculator",
    ),
    "textos": (
        "normalizador de textos", "crea un normalizador de textos",
        "crear normalizador de textos", "create text normalizer",
    ),
}

def _norm(text):
    if not isinstance(text,str) or not 4<=len(text)<=220:
        raise ValueError("CATALOG_REQUEST_LENGTH_INVALID")
    reduced=unicodedata.normalize("NFKD",text.casefold())
    reduced="".join(ch for ch in reduced if not unicodedata.combining(ch))
    reduced=" ".join(reduced.split())
    if not re.fullmatch(r"[a-z0-9 ]{4,220}", reduced):
        raise ValueError("CATALOG_REQUEST_FORBIDDEN_OR_AMBIGUOUS_CHARACTERS")
    return reduced

_LOOKUP={_norm(phrase):key for key,aliases in ALIASES.items() for phrase in aliases}
assert len(_LOOKUP)==sum(len(v) for v in ALIASES.values()), "CATALOG_ALIAS_COLLISION"

def select(text):
    normalized=_norm(text)
    if normalized not in _LOOKUP:
        raise ValueError("UNSUPPORTED_NATURAL_LANGUAGE_REQUEST_NEEDS_OWNER_CRITERIA")
    return _LOOKUP[normalized]

def _cases(template):
    if template=="descuento":
        rows=[(100,0),(100,10),(100,25),(100,50),(100,100),
              (200,25),(80,50),(0,50),(-20,20),(50,-10),
              (50,120),(250,60),(40,75),(12,50),(120,25),(300,100)]
        def fn(a,b):
            price=max(0,a);percent=min(100,max(0,b))
            return price-price*percent/100
    elif template=="importes":
        rows=[(0,0),(1,1),(10,3),(3,10),(-1,10),(10,-5),
              (100,0),(7,7),(2,99),(50,2),(12,12),
              (-15,-9),(200,4),(25,8),(17,3),(40,7)]
        def fn(a,b):return max(0,a)*max(0,b)
    elif template=="textos":
        rows=[(" HOLA ","hola"),("ABC","abc"),("  Casa  ","casa"),
              ("EJEMPLO","ejemplo"),(" 123 ","123"),(" TEXTO","texto"),
              ("",""),(" ",""),("MaDrId","madrid"),("  Sol","sol"),
              ("LUNA  ","luna"),("AZUL","azul"),(" un DOS ","un dos"),
              ("  OPEN AI ","open ai"),(" CASA ROJA ","casa roja"),
              (" a ","a")]
        return [{"args":[a],"expected":b} for a,b in rows]
    else:
        raise ValueError("UNKNOWN_CATALOG_TEMPLATE")
    return [{"args":[a,b],"expected":fn(a,b)} for a,b in rows]

def owner_spec(template):
    cases=_cases(template)
    common={"schema":1,"language":"javascript","dependencies":[],
            "entry":"src/index.js","acceptance":cases}
    if template=="descuento":
        common.update({
            "exportName":"discountTotal",
            "goal":("Repair the TWO original ESM modules. src/rules.js MUST export "
              "clampPercent(percent) returning Math.min(100,Math.max(0,percent)). "
              "src/index.js MUST import clampPercent from './rules.js' and "
              "export discountTotal(price,percent) returning "
              "Math.max(0,price)-Math.max(0,price)*clampPercent(percent)/100. "
              "The current source is intentionally wrong. Return complete "
              "modules, no npm or unlisted sources."),
            "sources":{
                "src/rules.js":"export function clampPercent(x){return 0;} // broken original\n",
                "src/index.js":("import {clampPercent} from './rules.js'; "
                                "export function discountTotal(a,b){return 0;} // broken\n")
            }})
    elif template=="importes":
        common.update({
            "exportName":"invoiceTotal",
            "goal":("Repair both original ESM modules. src/rules.js MUST export "
              "nonNegative(n) returning Math.max(0,n). src/index.js MUST "
              "import nonNegative from './rules.js' and export "
              "invoiceTotal(quantity,price), returning "
              "nonNegative(quantity)*nonNegative(price). Return complete "
              "source for BOTH modules. No extra files or npm."),
            "sources":{
                "src/rules.js":"export function nonNegative(n){return 0;} // broken original\n",
                "src/index.js":("import {nonNegative} from './rules.js'; "
                                "export function invoiceTotal(a,b){return 0;} // broken\n")
            }})
    elif template=="textos":
        common.update({
            "exportName":"cleanText",
            "goal":("Repair TWO original ESM files. src/rules.js MUST export "
              "normalizeText(value), returning value.trim().toLowerCase() for "
              "strings. src/index.js MUST import normalizeText from './rules.js' "
              "and export cleanText(value) returning normalizeText(value). "
              "Do not add packages, files or Node APIs; return full source "
              "for both modules, with exact export names."),
            "sources":{
                "src/rules.js":"export function normalizeText(value){return '';} // broken original\n",
                "src/index.js":("import {normalizeText} from './rules.js'; "
                                "export function cleanText(value){return '';} // broken\n")
            }})
    else:raise ValueError("UNKNOWN_CATALOG_TEMPLATE")
    assert len(cases)==16
    repo_graph._valid_spec(common)
    return common

def _paths(root,template):
    root=Path(root).resolve()
    return (root/"examples"/("catalog_"+template+"_v1.json"),
            root/"catalog"/("CAT-"+template+"-v1"))

def preview(text):
    template=select(text)
    spec=owner_spec(template)
    encoded=(json.dumps(spec,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
    return {"schema":1,"status":"CATALOG_PREVIEW_NO_EFFECTS",
            "template":template,"catalogVersion":CATALOG_VERSION,
            "ownerCases":len(spec["acceptance"]),
            "ownerSpecSha256":sha_bytes(encoded),
            "acceptanceSource":"DETERMINISTIC_CATALOG_NOT_MODEL",
            "scope":"BOUNDED_TWO_MODULE_JAVASCRIPT_ESM"}

def request(root,text):
    root=engine.init(root)
    key=select(text)
    spec=owner_spec(key)
    previewed=preview(text)
    source,folder=_paths(root,key)
    if source.is_symlink() or folder.is_symlink():
        raise RuntimeError("CATALOG_ORIGINAL_OWNER_SYMLINK_REJECTED")
    if folder.exists() or source.exists():
        # NO replay: even if last submission crashed, readback only.
        if not folder.is_dir() or not (folder/"intent.json").is_file():
            return {"status":"UNKNOWN_PRIOR_CATALOG_INTENT_RECONCILE",
                    "template":key,"nativeWorkRelaunched":False}
        intent=load(folder/"intent.json")
        if intent.get("ownerSpecSha256")!=sha_file(source):
            raise RuntimeError("CATALOG_ORIGINAL_OWNER_SOURCE_DRIFT")
        verify_journal(folder/"journal.jsonl")
        status="EXISTING_REQUEST_NO_REPLAY"
        return {"status":status,"template":key,"intentSha":sha_file(folder/"intent.json"),
                "sourceSha":sha_file(source),"nativeWorkRelaunched":False}
    # The existing immutable original is verified before optional environment
    # dependencies; a tampered source must be rejected even when offline.
    repo_graph.preflight(root)
    # Deterministic immutable contract staged BEFORE any model or repo intent.
    blob=(json.dumps(spec,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
    source.parent.mkdir(parents=True,exist_ok=True)
    with source.open("xb") as f:
        f.write(blob);f.flush();os.fsync(f.fileno())
    if sha_file(source)!=previewed["ownerSpecSha256"]:
        raise RuntimeError("CATALOG_PREMODEL_OWNER_SHA_READBACK_FAILED")
    folder.mkdir(parents=True,exist_ok=False)
    intent={"schema":1,"atUtc":utc(),"catalogVersion":CATALOG_VERSION,
            "template":key,"originalInput":text,"normalized":_norm(text),
            "ownerSpecSha256":sha_file(source),
            "source":str(source),"preModelOwnerCases":16,
            "ownerAcceptanceCreatedByAI":False,
            "hostProtectedInstallApproved":False,
            "nextAction":"invoke_original_factory_pipeline_submit_once"}
    write_json(folder/"intent.json",intent,new=True)
    event(folder/"journal.jsonl","CATALOG_ORIGINAL_OWNER_FROZEN",
          {"template":key,"intentSha":sha_file(folder/"intent.json"),
           "specSha":sha_file(source)})
    # At this point a crash requires reconcile; do not blindly invoke again.
    result=factory_pipeline.submit(root,source)
    write_json(folder/"submission.json",
               {"schema":1,"atUtc":utc(),"result":result,
                "originalIntentSha":sha_file(folder/"intent.json"),
                "originalOwnerSpecSha":sha_file(source)},new=True)
    event(folder/"journal.jsonl","CATALOG_ORIGINAL_SUBMISSION",
          {"submissionSha":sha_file(folder/"submission.json")})
    return {"status":"SUBMITTED_ORIGINAL_FACTORY_ONCE","template":key,
            "ownerCases":16,"originalOwnerSpecSha":sha_file(source),
            "catalogIntentSha":sha_file(folder/"intent.json"),
            "submission":result}

def status(root,text):
    key=select(text)
    source,folder=_paths(root,key)
    if not folder.is_dir():return {"status":"CATALOG_NOT_SUBMITTED","template":key}
    intent=load(folder/"intent.json")
    verify_journal(folder/"journal.jsonl")
    if sha_file(source)!=intent["ownerSpecSha256"]:
        raise RuntimeError("CATALOG_OWNER_SPEC_DRIFT")
    original=load(folder/"submission.json") if (folder/"submission.json").exists() else None
    result={"status":"SUBMITTED" if original else "UNKNOWN_SUBMISSION_RECONCILE",
            "template":key,"intentSha":sha_file(folder/"intent.json"),
            "ownerSpecSha":sha_file(source),"nativeGuestTrusted":False}
    if original:
        result["originalSubmission"]=original["result"]
        fid=original["result"].get("workflowId")
        if fid:
            result["originalFactory"]=factory_pipeline.status(root,fid)
            from . import portable_delivery
            where,archive=portable_delivery._base(root,fid)
            if archive.is_file():
                result["portableProgram"]=portable_delivery.verify(root,fid)
    return result
