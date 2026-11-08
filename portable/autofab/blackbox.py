# coding: utf-8
"""AUTOFABRICADOR tamper-evident BLACK BOX for test evidence.

Observer only. Never invokes the model, compiles untrusted sources, installs
Host services, copies secrets or executes user code. Existing original tools
remain owners. BLACKBOX only anchors immutable outcome and original receipts.
"""
from __future__ import annotations
import ctypes
import os
import re
import uuid
from pathlib import Path
from .storage import event,verify_journal,write_json,load,sha_file,utc,sha_bytes,json_bytes

_ID=re.compile(r"BB-[a-f0-9]{16}\Z")
_CASE=re.compile(r"[a-z][a-z0-9_-]{1,70}\Z")
_OUTCOMES=frozenset(("PASS","REJECT","FAIL","UNKNOWN","BLOCKED","SKIPPED","UNSUPPORTED"))
def _folder(root,ident):
    if not isinstance(ident,str) or not _ID.fullmatch(ident):
        raise ValueError("BLACKBOX_SESSION_ID_UNSAFE")
    folder=Path(root).resolve()/"blackbox"/ident
    if not folder.is_dir() or folder.is_symlink():
        raise FileNotFoundError("BLACKBOX_SESSION_UNKNOWN")
    return folder
def _RAM():
    if os.name!="nt":return {"measured":False}
    try:
        class Memory(ctypes.Structure):
            _fields_=[("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),
                ("ullTotalPhys",ctypes.c_ulonglong),("ullAvailPhys",ctypes.c_ulonglong),
                ("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),
                ("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
        m=Memory();m.dwLength=ctypes.sizeof(m)
        f=ctypes.WinDLL("kernel32",use_last_error=True).GlobalMemoryStatusEx
        f.argtypes=[ctypes.POINTER(Memory)];f.restype=ctypes.c_int
        if not f(ctypes.byref(m)):return {"measured":False}
        return {"measured":True,"freeBytes":int(m.ullAvailPhys),
                "totalBytes":int(m.ullTotalPhys),"memoryLoad":int(m.dwMemoryLoad)}
    except (OSError,AttributeError,ValueError):
        return {"measured":False}
def create(root,cases,*,objective,session_id=None):
    root=Path(root).resolve()
    if not isinstance(cases,list) or not 1<=len(cases)<=10000:
        raise ValueError("BLACKBOX_CASES_BOUND_INVALID")
    if not isinstance(objective,str) or not 20<=len(objective)<=250:
        raise ValueError("BLACKBOX_OBJECTIVE_INVALID")
    keys=set()
    for row in cases:
        if not isinstance(row,dict) or set(row)!={"id","domain","expect","description"}:
            raise ValueError("BLACKBOX_CASE_SCHEMA")
        if not isinstance(row["id"],str) or not _CASE.fullmatch(row["id"]) or row["id"] in keys:
            raise ValueError("BLACKBOX_CASE_DUPLICATE_OR_UNSAFE")
        keys.add(row["id"])
        if row["expect"] not in _OUTCOMES or not isinstance(row["domain"],str) or len(row["domain"])>45:
            raise ValueError("BLACKBOX_CASE_CONTRACT_INVALID")
        if not isinstance(row["description"],str) or len(row["description"])>240:
            raise ValueError("BLACKBOX_CASE_DESCRIPTION_INVALID")
    name=session_id or "BB-"+uuid.uuid4().hex[:16]
    if not _ID.fullmatch(name):raise ValueError("BLACKBOX_SESSION_ID_UNSAFE")
    d=root/"blackbox"/name
    d.mkdir(parents=True,exist_ok=False)
    (d/"cases").mkdir()
    spec={"schema":1,"createdAtUtc":utc(),"sessionId":name,
          "objective":objective,"caseCount":len(cases),"cases":cases,
          "isolation":"READ_ONLY_BLACKBOX_OBSERVER_NO_UNTRUSTED_HOST_EXECUTION",
          "rawPromptsOrSecretsLogged":False}
    write_json(d/"plan.json",spec,new=True)
    event(d/"events.jsonl","BLACKBOX_PLAN_PINNED",
      {"planSha":sha_file(d/"plan.json"),"caseCount":len(cases),
       "hostRam":_RAM()})
    return {"sessionId":name,"planSha":sha_file(d/"plan.json"),"caseCount":len(cases)}
def record(root,ident,caseid,*,actual,detail,evidence=(),duration_ms=None):
    d=_folder(root,ident);root=Path(root).resolve()
    plan=load(d/"plan.json")
    if (d/"report.json").exists():raise RuntimeError("BLACKBOX_ALREADY_FINALIZED_NO_MODIFICATION")
    originals={x["id"]:x for x in plan["cases"]}
    if caseid not in originals:raise ValueError("BLACKBOX_CASE_NOT_FROZEN")
    if actual not in _OUTCOMES:raise ValueError("BLACKBOX_OUTCOME_UNCLASSIFIED")
    if not isinstance(detail,str) or len(detail)>320:
        raise ValueError("BLACKBOX_DETAIL_LENGTH_OR_TYPE_INVALID")
    if duration_ms is not None and (type(duration_ms) is not int or duration_ms<0):
        raise ValueError("BLACKBOX_DURATION_INVALID")
    # Evidence contains no bytes or token text: only pathname and verified SHA.
    if not isinstance(evidence,(list,tuple)) or len(evidence)>35:
        raise ValueError("BLACKBOX_EVIDENCE_BOUND")
    refs=[]
    for item in evidence:
        p=Path(item).resolve()
        if not p.is_file() or p.is_symlink() or not p.is_relative_to(root):
            raise ValueError("BLACKBOX_EVIDENCE_MUST_BE_ORIGINAL_IN_ROOT")
        refs.append({"relativePath":p.relative_to(root).as_posix(),"sha":sha_file(p),
                     "bytes":p.stat().st_size})
    old=d/"cases"/(caseid+".json")
    if old.exists():raise FileExistsError("BLACKBOX_CASE_NO_REPLAY")
    case=originals[caseid]
    value={"schema":1,"sessionId":ident,"caseId":caseid,
           "domain":case["domain"],"expected":case["expect"],
           "actual":actual,"matchesExpected":case["expect"]==actual,
           "detailCode":detail,"atUtc":utc(),"durationMs":duration_ms,
           "hostRam":_RAM(),"evidence":refs,
           "source":"INDEPENDENT_ORIGINAL_RECEIPT_OR_DETERMINISTIC_PROBE"}
    write_json(old,value,new=True)
    event(d/"events.jsonl","BLACKBOX_CASE_RECORDED",
        {"caseId":caseid,"receiptSha":sha_file(old),"actual":actual,
         "matched":value["matchesExpected"],"ramMeasured":value["hostRam"]["measured"]})
    return {"caseId":caseid,"actual":actual,"matchesExpected":value["matchesExpected"],
            "receiptSha":sha_file(old)}
def finalize(root,ident):
    d=_folder(root,ident)
    plan=load(d/"plan.json")
    if (d/"report.json").exists():raise RuntimeError("BLACKBOX_REPORT_ALREADY_FINAL")
    cases=[]
    for original in plan["cases"]:
        file=d/"cases"/(original["id"]+".json")
        if file.exists():
            row=load(file)
            if row["caseId"]!=original["id"] or row["expected"]!=original["expect"]:
                raise RuntimeError("BLACKBOX_ORIGINAL_CASE_DRIFT")
            cases.append({"id":original["id"],"domain":original["domain"],
               "status":row["actual"],"expected":row["expected"],
               "matched":row["matchesExpected"],"receiptSha":sha_file(file)})
        else:
            cases.append({"id":original["id"],"domain":original["domain"],
               "status":"NOT_RUN","expected":original["expect"],
               "matched":False,"receiptSha":None})
    verify_journal(d/"events.jsonl")
    total=len(cases)
    recorded=sum(x["status"]!="NOT_RUN" for x in cases)
    satisfied=sum(x["matched"] for x in cases)
    failures=[x["id"] for x in cases if not x["matched"]]
    event(d/"events.jsonl","BLACKBOX_FINALIZED",
          {"originalPlanSha":sha_file(d/"plan.json"),"recorded":recorded,
           "satisfied":satisfied,"missed":len(failures)})
    report={"schema":1,"atUtc":utc(),"sessionId":ident,
      "status":"MEASURED_ALL_EXPECTATIONS" if satisfied==total else "MIXED_OR_INCOMPLETE",
      "scope":"BOUNDED_CAPABILITY_MATRIX_NOT_UNIVERSAL_SOFTWARE_PROOF",
      "planSha":sha_file(d/"plan.json"),"cases":cases,
      "totals":{"planned":total,"recorded":recorded,"matched":satisfied,
                "unmatched":total-satisfied},
      "caseIdsNotMeetingExpectation":failures,
      "journalSha":sha_file(d/"events.jsonl"),
      "guestClaimsAreNotCryptographicOwnerAcceptance":True,
      "noFullConversationTranscript":True,"noHostInstallation":True}
    write_json(d/"report.json",report,new=True)
    verify(root,ident)
    return {"sessionId":ident,"status":report["status"],
      "planned":total,"recorded":recorded,"matched":satisfied,
      "reportSha":sha_file(d/"report.json")}
def verify(root,ident):
    root=Path(root).resolve()
    d=_folder(root,ident)
    plan=load(d/"plan.json")
    journal=verify_journal(d/"events.jsonl")
    if not (d/"report.json").exists():
        return {"status":"BLACKBOX_NOT_FINAL","events":journal["events"]}
    report=load(d/"report.json")
    if report["planSha"]!=sha_file(d/"plan.json") or report["journalSha"]!=sha_file(d/"events.jsonl"):
        raise RuntimeError("BLACKBOX_TAMPERED_REPORT_OR_CHAIN")
    if len(report["cases"])!=plan["caseCount"]:
        raise RuntimeError("BLACKBOX_MISSING_CASES")
    seen=set()
    for expected,summary in zip(plan["cases"],report["cases"]):
        if expected["id"]!=summary["id"] or summary["id"] in seen:
            raise RuntimeError("BLACKBOX_UNEXPECTED_CASE_ORDER_OR_ID")
        seen.add(summary["id"])
        if summary["status"]=="NOT_RUN":continue
        p=d/"cases"/(expected["id"]+".json")
        if summary["receiptSha"]!=sha_file(p):raise RuntimeError("BLACKBOX_CASE_TAMPERED")
        original=load(p)
        for ref in original["evidence"]:
            path=(root/ref["relativePath"]).resolve()
            if (not path.is_relative_to(root) or not path.is_file() or
                path.is_symlink() or sha_file(path)!=ref["sha"]):
                raise RuntimeError("BLACKBOX_ORIGINAL_EVIDENCE_SHA_DRIFT")
    return {"status":"BLACKBOX_ALL_RECORDED_SHA_VERIFIED",
            "sessionId":ident,"reportSha":sha_file(d/"report.json"),
            "journalEvents":journal["events"],"verifiedCases":len(seen),
            "ownerAcceptanceNotInferredFromAssertions":True}
