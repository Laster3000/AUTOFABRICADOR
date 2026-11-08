# coding: utf-8
"""Read-only guest Windows Service rehearsal, NEVER protected Host installer.

This validates original staged source/owner/policy SHA and correlates guest
output. Guest service manager reports can be forged by guest; no native
cryptographic owner acceptance or Host-install authority can be inferred.
"""
from __future__ import annotations
from pathlib import Path
import json
from . import engine,windows_sandbox
from .storage import load,sha_file,verify_journal

EXPECTED_PHASES=(
 "INSTALL","START","STOP","RESTART","STOP_AFTER_RESTART","UNINSTALL_ROLLBACK"
)
RESULT="GUEST_REPORTED_SERVICE_LIFECYCLE_CORRELATED_UNATTESTED"

def verify(root,jid):
    root=engine.init(root)
    job=windows_sandbox._path(root,jid)
    staged=windows_sandbox.verify(root,jid)
    manifest=load(job/"manifest.json")
    permitted={
       (root/"examples/windows_sandbox_service_r048.zip").resolve(),
       (root/"examples/windows_sandbox_service_r048_v2.zip").resolve(),
       (root/"examples/windows_sandbox_service_r048_v3.zip").resolve()
    }
    if (Path(manifest["originalSourcePath"]).resolve() not in permitted
        or Path(manifest["ownerOriginalPath"]).resolve()!=
        (root/"examples/windows_sandbox_service_r048_owner.json").resolve()):
        raise RuntimeError("SERVICE_REHEARSAL_WRONG_ORIGINAL_INPUT")
    step=load(job/"input/owner.json")
    if (step["steps"]!=[{"script":"src/service_rehearsal.ps1"}]):
        raise RuntimeError("SERVICE_REHEARSAL_OWNER_SCRIPT_DRIFT")
    original=windows_sandbox.reconcile(root,jid)
    if original["status"]=="NO_ORIGINAL_GUEST_RECEIPT":
        return {"jobId":jid,"status":"NO_ORIGINAL_GUEST_RECEIPT",
                "originalInputSha":manifest["sourceOriginalSha"],
                "serviceGuestAttested":False,"hostServiceInstalled":False}
    if (original["status"]!="UNTRUSTED_GUEST_REPORT_READBACK_ONLY"
        or original["nativeAcceptance"] is not False):
        raise RuntimeError("SERVICE_REHEARSAL_INVALID_ORIGINAL_READBACK")
    report=load(job/"output/guest-report.json")
    if (report.get("status")!="GUEST_REPORTED_ALL_OK_UNATTESTED"
        or len(report.get("steps",[]))!=1
        or report["steps"][0].get("exitCode")!=0
        or report["steps"][0].get("script")!="src/service_rehearsal.ps1"):
        return {"jobId":jid,
                "status":"GUEST_SERVICE_REHEARSAL_UNCONFIRMED",
                "guestOriginalReportSha":original["guestReceiptSha"],
                "guestOriginalReportedStatus":original["reported"],
                "serviceGuestAttested":False,"hostServiceInstalled":False}
    extra=job/"output/service-lifecycle.json"
    if not extra.is_file() or extra.is_symlink() or extra.stat().st_size>18000:
        raise RuntimeError("GUEST_SERVICE_EXTRA_RECEIPT_UNSAFE_OR_MISSING")
    payload=load(extra)
    values={
        "schema":1,"status":"GUEST_SERVICE_INSTALL_START_STOP_RESTART_DELETE_REPORTED",
        "service":"AFR048GuestProbe","guestReportUntrusted":True,
        "hostProtectedInstall":False}
    if any(payload.get(key)!=value for key,value in values.items()):
        raise RuntimeError("GUEST_SERVICE_REPORTED_CORE_CONTRACT_INVALID")
    phases=payload.get("steps")
    if (not isinstance(phases,list)
        or tuple(x.get("phase") for x in phases)!=EXPECTED_PHASES
        or not isinstance(payload.get("child1"),int)
        or not isinstance(payload.get("child2"),int)
        or payload["child1"]<=0 or payload["child2"]<=0
        or payload["child1"]==payload["child2"]
        or not isinstance(payload.get("auditCount"),int)
        or payload["auditCount"]<4
        or not isinstance(payload.get("auditSha256"),str)
        or len(payload["auditSha256"])!=64
        or any(char not in "0123456789abcdef"
               for char in payload["auditSha256"])):
        raise RuntimeError("GUEST_SERVICE_ORIGINAL_LIFECYCLE_EVIDENCE_INVALID")
    source_bin=root/"qa/service_r048/AFR048GuestService.exe"
    if not source_bin.is_file() or sha_file(source_bin)!=payload["serviceBinarySha"]:
        raise RuntimeError("GUEST_SERVICE_ORIGINAL_BINARY_SHA_DRIFT")
    verify_journal(job/"journal.jsonl")
    return {"jobId":jid,"status":RESULT,"originalInputSha":manifest["sourceOriginalSha"],
        "originalStagingVerified":staged["verified"],
        "guestReportedSixPhases":list(EXPECTED_PHASES),
        "guestOriginalReportSha":original["guestReceiptSha"],
        "guestExtraReportSha":sha_file(extra),
        "originalCompiledBinarySha":sha_file(source_bin),
        "serviceGuestAttested":False,"nativeCryptographicOwnerAttested":False,
        "hostServiceInstalled":False,
        "hostRollbackProven":False,
        "needIndependentOriginalServiceControlManagerAttestation":True,
        "nativeAcceptance":False}
