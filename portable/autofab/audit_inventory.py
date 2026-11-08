# coding: utf-8
"""Read-only whole-product capability audit; does not infer original owner PASS.

No model calls, Host installs, shell execution of model text or replay.
All observations are timestamped and scopes/unknowns explicit.
"""
from __future__ import annotations
import json,os,subprocess
from collections import Counter
from pathlib import Path
from . import blackbox,local_runtime,supervisor,repo_graph,repo_factory
from .storage import load,sha_file,utc
def _states(root,folder,glob):
    rows=[]
    base=root/folder
    for f in sorted(base.glob(glob)) if base.is_dir() else ():
        if f.is_symlink() or not f.is_file():continue
        try:
            state=load(f)
            rows.append({"jobId":f.parent.name,"state":state.get("status","UNKNOWN"),
                         "originalStateSha":sha_file(f)})
        except (OSError,ValueError,TypeError,KeyError):
            rows.append({"jobId":f.parent.name,"state":"UNKNOWN_CORRUPT_RECORD",
                         "originalStateSha":sha_file(f)})
    counter=Counter(x["state"] for x in rows)
    return {"count":len(rows),"byOriginalState":dict(sorted(counter.items())),
            "jobs":rows}
def _host_service():
    if os.name!="nt":
        return {"status":"NOT_CHECKED_NON_WINDOWS","serviceCount":None}
    script=(
      "$ErrorActionPreference='Stop';"+
      "$s=@(Get-Service -ErrorAction SilentlyContinue |"+
      "Where-Object {$_.Name -match 'AUTOFABRICADOR|AFR049'});"+
      "@{names=@($s|ForEach-Object {$_.Name});count=$s.Count} | ConvertTo-Json -Compress")
    try:
        result=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
          "-Command",script],stdin=subprocess.DEVNULL,
          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
          timeout=15)
        if result.returncode:
            return {"status":"UNKNOWN_SERVICE_ENUMERATION_FAILED",
                    "serviceCount":None}
        data=json.loads(result.stdout.decode("utf-8-sig"))
        return {"status":"HOST_SERVICES_ORIGINALLY_ENUMERATED",
                "serviceCount":data["count"],"matchingNames":data["names"]}
    except (OSError,ValueError,subprocess.TimeoutExpired,TypeError,KeyError):
        return {"status":"UNKNOWN_SERVICE_ENUMERATION_FAILED",
                "serviceCount":None}
def snapshot(root,*,strict=False):
    root=Path(root).resolve()
    original=blackbox._RAM()
    local=local_runtime.server_info(root)
    supervisor_status=supervisor.status(root)
    source={"python":_states(root,"work","AF-*/state.json"),
            "javascript_typescript_repositories":_states(root,"repojobs","RJ-*/state.json"),
            "csharp":_states(root,"csharpjobs","AC-*/state.json"),
            "autonomous_audit":_states(root,"auditjobs","SA-*/state.json")}
    r053=root/"blackbox/BB-5e7cdf7922974edf"
    if r053.is_dir():
        try:
            first=blackbox.verify(root,"BB-5e7cdf7922974edf")
            report=load(r053/"report.json")
            r053_data={"integrity":first["status"],
                 "planned":report["totals"]["planned"],
                 "met":report["totals"]["matched"],
                 "missed":report["totals"]["unmatched"],
                 "reportSha":sha_file(r053/"report.json")}
        except Exception as ex:
            r053_data={"integrity":"UNKNOWN_OR_TAMPERED",
                 "errorType":type(ex).__name__}
    else:r053_data={"integrity":"NOT_IN_SOURCE_ONLY_RESTORE"}
    native=root/"nativecycles"
    states=_states(root,"nativecycles","NC-*/state.json")
    r053_diag=root/"CONTINUIDAD/R053-MEGATEST-BLACKBOX-20261107/R053-DIAGNOSTICO-CUADRO-NEGRO-CAUSAS.json"
    causes=[]
    if r053_diag.is_file():
        diagnostics=load(r053_diag)
        causes=[{"priority":x["priority"],"class":x["class"],
                 "status":x["status"],"needed":x["needed"]}
                for x in diagnostics["improvementAndBlockerMatrix"]]
    trusted={"repoGraphPreflight":"NOT_RUN",
             "localModelPinned":"NOT_RUN"}
    if strict:
        try:
            pre=repo_graph.preflight(root)
            trusted["repoGraphPreflight"]="PASS_PINNED"
            trusted["compilerSha"]=pre["compilerWasmSha256"]
        except Exception as exc:
            trusted["repoGraphPreflight"]="BLOCKED_"+type(exc).__name__
        try:
            local_runtime.pinned_assets(root)
            trusted["localModelPinned"]="PASS_PINNED"
        except Exception as exc:
            trusted["localModelPinned"]="BLOCKED_"+type(exc).__name__
    release=root/"DIST/AUTOFABRICADOR-0.9.13.zip"
    declared={"path":str(release),"available":release.is_file(),
              "sourceSHA":sha_file(release) if release.is_file() else None,
              "newCandidateInstalled":False}
    service=_host_service()
    policy=[
      {"id":"owner_js_ts","state":"AUTONOMOUS_SCOPED",
       "reason":"Can autonomously diagnose and create NEW original WASI-tested source jobs; cannot alter owner tests"},
      {"id":"python","state":"DIAGNOSE_BUT_DO_NOT_AUTOMATICALLY_REPLAY_UNKNOWN",
       "reason":"Provider truncation/UNKNOWN; requires new original provider protocol and pinned Python owner"},
      {"id":"web_export","state":"BLOCKED_RECONCILE_ORIGINAL_INTENT",
       "reason":"Original browser export APP_INTENT without ZIP; no automatic blind replay"},
      {"id":"windows_host_service","state":"BLOCKED_PROTECTED_HOST",
       "reason":"No original authenticated OS restore preimage and full rollback rehearsal; no MMC dependencies"},
      {"id":"untrusted_model_code","state":"WASI_OR_GUEST_ONLY",
       "reason":"Cannot execute local-model-written code in Windows Host or allow extra filesystem/network rights"},
    ]
    return {"schema":1,"atUtc":utc(),
      "operationId":"AF.READONLY.AUTONOMOUS-WHOLE-SYSTEM-AUDIT",
      "status":"READONLY_EVIDENCE_SNAPSHOT_WITH_UNRESOLVED_GAPS",
      "root":str(root),"productIndependentOfMMC":True,
      "modelServer":local["state"],
      "supervisor":supervisor_status["status"],
      "supervisorPending":supervisor_status["pendingQueue"],
      "physicalRAM":original,"hostServices":service,
      "trustedPreflight":trusted,
      "latestKnownOriginalBlackbox":r053_data,
      "originalJobStates":source,
      "nativeCycleStates":states,
      "previousRootCauses":causes,
      "currentRelease":declared,
      "automationPolicy":policy,
      "neverClaimsPerfect":True,"neverClaimsActive":True,
      "noModelCalls":True,"noHostEffects":True,
      "nextAction":"Run bounded self-audit on a NEW reproducible JS/TS original failure; address Python provider and browser export as independent new contracts with original receipts; full Host service rollback remains blocked."}
