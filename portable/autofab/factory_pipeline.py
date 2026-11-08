# coding: utf-8
"""One immutable owner -> original model/WASI then native guest OR offline Chrome.

All effects are implemented by the existing original repo_factory, native_cycle,
and the original supervisor. A factory workflow is NOT an independent runner.
No unknown state is replayable, and native reports remain untrusted.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from . import engine, repo_factory, repo_graph, native_cycle
from .storage import event, load, sha_file, transition, utc, verify_journal, write_json

IDENTIFIER = re.compile(r"FC-[a-f0-9]{16}\Z")
TERMINAL = frozenset({
    "PASS_SCOPED_WASI_NATIVE_UNTRUSTED", "PASS_SCOPED_WASI_BROWSER_OFFLINE", "STOPPED_PRE_INTENT",
    "STOPPED_SAFE_BOUNDARY", "FAILED_OWNER_ACCEPTANCE", "FAILED_REPO",
    "FAILED_NATIVE", "BLOCKED_VM_CONFLICT", "UNKNOWN"
})
SUCCESS = "PASS_SCOPED_WASI_NATIVE_UNTRUSTED"
SUCCESS_BROWSER = "PASS_SCOPED_WASI_BROWSER_OFFLINE"


def folder(root, workflow_id):
    if not isinstance(workflow_id, str) or not IDENTIFIER.fullmatch(workflow_id):
        raise ValueError("FACTORY_WORKFLOW_ID_INVALID")
    target = Path(root).resolve()/"factoryjobs"/workflow_id
    if not (target/"intent.json").is_file():
        raise FileNotFoundError("FACTORY_WORKFLOW_NOT_FOUND")
    return target


def _set(d, state, description, **extra):
    statefile = d/"state.json"
    value = {"schema":1, "status":state, "atUtc":utc(),
             "detail":description, "previousSha":sha_file(statefile), **extra}
    transition(statefile, value, d/"history")
    event(d/"journal.jsonl", "FACTORY_STATE",
          {"status":state, "stateSha":sha_file(statefile)})
    return value


def create(root, spec_path, *, provider="small", acceptance_mode="wasi-native"):
    root = engine.init(root)
    source = Path(spec_path).resolve()
    if (not source.is_file() or source.is_symlink()
        or not source.is_relative_to(root/"examples")):
        raise ValueError("FACTORY_OWNER_SPEC_MUST_BE_PROJECT_EXAMPLES")
    spec = load(source)
    if provider not in ("small","coder14b","cuda7b","cuda9b"):
        raise ValueError("FACTORY_PROVIDER_NOT_PINNED")
    if acceptance_mode not in ("wasi-native","wasi-browser"):
        raise ValueError("FACTORY_ACCEPTANCE_MODE_NOT_PINNED")
    repo_graph._valid_spec(spec)
    repo_graph.preflight(root)
    jobs = root/"factoryjobs"
    jobs.mkdir(exist_ok=True)
    target_sha = sha_file(source)
    for intent_file in jobs.glob("FC-*/intent.json"):
        previous = load(intent_file)
        if previous.get("ownerOriginalSha")==target_sha:
            return {"workflowId":intent_file.parent.name,
                    "status":"EXISTING_INTENT_NO_DUPLICATE",
                    "originalStatus":load(intent_file.parent/"state.json")["status"]}
    uid = "FC-"+uuid.uuid4().hex[:16]
    dest = jobs/uid
    dest.mkdir(exist_ok=False)
    (dest/"history").mkdir()
    intent={"schema":1,"workflowId":uid,"operationId":uid+(".AI-WASI-BROWSER.ONE" if acceptance_mode=="wasi-browser" else ".AI-WASI-NATIVE.ONE"),
            "sourceOriginalPath":str(source),"ownerOriginalSha":target_sha,
            "ownerCases":len(spec["acceptance"]),"sourceModules":len(spec["sources"]),
            "provider":provider,"acceptanceMode":acceptance_mode,"maxAttempts":3,"maxTokens":2300,
            "atUtc":utc(),"protectedHostInstallation":False}
    write_json(dest/"intent.json",intent,new=True)
    write_json(dest/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    write_json(dest/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    event(dest/"journal.jsonl","FACTORY_ORIGINAL_INTENT",
          {"workflowId":uid,"ownerOriginalSha":target_sha,
           "originalIntentSha":sha_file(dest/"intent.json")})
    return {"workflowId":uid,"status":"PENDING","ownerCases":len(spec["acceptance"]),
            "originalOwnerSpecSha":target_sha}


def status(root, workflow_id):
    d=folder(root,workflow_id)
    journal=verify_journal(d/"journal.jsonl")
    current=load(d/"state.json")
    repo_ref=load(d/"repo-ref.json") if (d/"repo-ref.json").is_file() else None
    native_ref=load(d/"native-ref.json") if (d/"native-ref.json").is_file() else None
    return {"workflowId":workflow_id,"status":current["status"],
            "ownerOriginalSpecSha":load(d/"intent.json")["ownerOriginalSha"],
            "repoJob":repo_ref.get("jobId") if repo_ref else None,
            "nativeCycle":native_ref.get("cycleId") if native_ref else None,
            "control":load(d/"control.json")["command"],
            "journalEvents":journal["events"],"nativeGuestAuthenticated":False,
            "resultReceiptSha":sha_file(d/"result.json") if (d/"result.json").exists() else None}


def stop(root, workflow_id):
    d=folder(root,workflow_id)
    original=load(d/"state.json")["status"]
    if original in TERMINAL:
        return {"workflowId":workflow_id,"status":"TERMINAL_NO_REPLAY",
                "originalState":original}
    ctl=d/"control.json"
    c=load(ctl)
    if c["command"]!="STOP":
        transition(ctl,{"schema":1,"command":"STOP","atUtc":utc(),
                        "previousSha":sha_file(ctl)},d/"history")
        event(d/"journal.jsonl","FACTORY_STOP_REQUESTED",
              {"controlSha":sha_file(ctl),"originalState":original})
    # Forward STOP through original task owners, never terminate unknown child.
    if (d/"native-ref.json").is_file():
        native_cycle.stop(root,load(d/"native-ref.json")["cycleId"])
    elif (d/"repo-ref.json").is_file():
        repo_factory.stop(root,load(d/"repo-ref.json")["jobId"])
    return {"workflowId":workflow_id,"status":"STOP_REQUESTED_FIRST_SAFE_BOUNDARY",
            "originalState":original}


def _stopped(d):
    return load(d/"control.json")["command"]=="STOP"


def _receipt(d, workflow_id, repo, cycle, report):
    root=d.parent.parent
    spec_file=Path(load(d/"intent.json")["sourceOriginalPath"])
    owner_spec_sha=load(d/"intent.json")["ownerOriginalSha"]
    if sha_file(spec_file)!=owner_spec_sha:
        raise RuntimeError("OWNER_ORIGINAL_SPEC_DRIFT_AT_FINAL_READBACK")
    verified=repo_factory.verify(root,repo)
    native=native_cycle.reconcile(root,cycle)
    if (not verified["verified"] or verified["status"]!="PASS"
        or native["status"]!=native_cycle.OK
        or native.get("originalResultStatus")!=native_cycle.OK):
        raise RuntimeError("ORIGINAL_REPO_OR_NATIVE_RECEIPT_NOT_VERIFIED")
    native_result=load(native_cycle.folder(root,cycle)/"result.json")
    if (native_result["sourceRepo"]!=repo
        or native_result["ownerCases"]!=verified["ownerCases"]
        or native_result["nativeCryptographicOwnerAcceptance"]):
        raise RuntimeError("FACTORY_ORIGINAL_OWNER_CORRELATION_DRIFT")
    repo_manifest=root/"repojobs"/repo/"manifest.json"
    result={
      "schema":1,"atUtc":utc(),"workflowId":workflow_id,
      "status":SUCCESS,"originalOwnerSpecSha":owner_spec_sha,
      "originalRepoJobId":repo,
      "originalRepoManifestSha":sha_file(repo_manifest),
      "originalModelSha":load(repo_manifest)["modelSha"],
      "originalModelAttempts":verified["modelAttempts"],
      "originalOwnerWasiAccepted":True,
      "originalOwnerCases":verified["ownerCases"],
      "nativeCycleId":cycle,"nativeSandboxId":native_result["sandboxJob"],
      "nativeOriginalGuestReportSha":native_result["sandboxOriginalGuestReportSha"],
      "originalNativeCycleReceiptSha":sha_file(native_cycle.folder(root,cycle)/"result.json"),
      "nativeGuestOutputUntrusted":True,
      "nativeGuestCryptographicOwnerAcceptance":False,
      "untrustedModelCodeExecutedOnHost":False,
      "protectedHostInstallationPerformed":False,
      "sandboxGuestSessionClosed":native_result["vmCleanup"]["closed"],
      "scope":"OWNER_PINNED_ESM_PROJECT_WASI_AND_NATIVE_GUEST_NOT_UNIVERSAL"}
    write_json(d/"result.json",result,new=True)
    event(d/"journal.jsonl","FACTORY_FINAL_ORIGINAL_EVIDENCE",
          {"receiptSha":sha_file(d/"result.json"),
           "originalRepoManifestSha":sha_file(repo_manifest)})
    _set(d,SUCCESS,"original owner WASI independently PASS, native guest correlated only",
         resultSha=sha_file(d/"result.json"))
    # Deliver source as immutable static package: NEVER execute model JS on
    # Windows Host. A delivery failure never overwrites the original PASS;
    # it is explicitly an UNKNOWN artifact and requires original reconciliation.
    try:
        from . import portable_delivery
        delivered=portable_delivery.deliver(root,workflow_id)
        event(d/"journal.jsonl","FACTORY_PORTABLE_ARTIFACT_CREATED",
              {"deliveryStatus":delivered["status"],
               "archiveSha":delivered["result"]["archiveSha"]})
        return {**result,"deliveryStatus":delivered["status"],
                "deliveryArchiveSha":delivered["result"]["archiveSha"]}
    except (RuntimeError,ValueError,FileNotFoundError,OSError,KeyError,AssertionError) as error:
        event(d/"journal.jsonl","FACTORY_PORTABLE_ARTIFACT_UNKNOWN",
              {"status":"UNKNOWN_DO_NOT_REGENERATE",
               "errorType":type(error).__name__,
               "errorText":str(error)[:220]})
        return {**result,"deliveryStatus":"UNKNOWN_DELIVERY_READBACK_ONLY",
                "deliveryErrorType":type(error).__name__}



def _receipt_browser(d, workflow_id, repo):
    """Original repo/WASI -> original offline Chrome owner; NO native guest claim.

    Existing repo_export gives an independently pinned owner Chrome browser
    result and a portable browser program ZIP. Never install generated code
    on the Host or treat Chrome's OS sandbox as cryptographic attestation.
    """
    from . import repo_export
    root=d.parent.parent
    original_intent=load(d/"intent.json")
    specfile=Path(original_intent["sourceOriginalPath"])
    if original_intent.get("acceptanceMode")!="wasi-browser":
        raise RuntimeError("BROWSER_MODE_NOT_ORIGINALLY_FROZEN")
    if sha_file(specfile)!=original_intent["ownerOriginalSha"]:
        raise RuntimeError("BROWSER_ORIGINAL_OWNER_SPEC_DRIFT")
    pinned=repo_factory.verify(root,repo)
    if not pinned["verified"] or pinned["ownerCases"]!=original_intent["ownerCases"]:
        raise RuntimeError("BROWSER_INDEPENDENT_ORIGINAL_WASI_DRIFT")
    if _stopped(d):
        _set(d,"STOPPED_SAFE_BOUNDARY","STOP before Chrome owner intent",repo=repo)
        return {"workflowId":workflow_id,"status":"STOPPED_SAFE_BOUNDARY"}
    _set(d,"BROWSER_OWNER_INTENT","original repo Chrome owner E2E with offline network")
    result=repo_export.export(root,repo)
    if result.get("status")!="REPO_BROWSER_WASI_E2E_PASS":
        raise RuntimeError("BROWSER_ORIGINAL_EXPORT_NOT_NEW_PASS_NO_REPLAY")
    readback=repo_export.verify(root,repo)
    if (readback["verified"] is not True or
        readback["ownerWasiCases"]!=original_intent["ownerCases"] or
        readback["browserE2eCases"]!=original_intent["ownerCases"]):
        raise RuntimeError("BROWSER_ORIGINAL_OWNER_CASE_COUNT_MISMATCH")
    if _stopped(d):
        _set(d,"STOPPED_SAFE_BOUNDARY","STOP after Chrome execution; preserve original zip and evidence")
        return {"workflowId":workflow_id,"status":"STOPPED_SAFE_BOUNDARY"}
    source=root/"repojobs"/repo/"manifest.json"
    archive=root/"repoexports"/("AF-REPO-"+repo+".zip")
    original_browser=root/"repoexports"/("AF-REPO-"+repo+"-receipts")/"BROWSER-RECEIPT.json"
    if sha_file(archive)!=readback["archiveSha256"]:
        raise RuntimeError("BROWSER_DELIVERY_ZIP_SHA_DRIFT")
    evidence={
      "schema":1,"atUtc":utc(),"workflowId":workflow_id,
      "status":SUCCESS_BROWSER,
      "originalOwnerSpecSha":original_intent["ownerOriginalSha"],
      "originalRepoJobId":repo,
      "originalRepoManifestSha":sha_file(source),
      "originalModelSha":load(source)["modelSha"],
      "originalModelAttempts":pinned["modelAttempts"],
      "originalOwnerWasiAccepted":True,
      "originalOwnerCases":pinned["ownerCases"],
      "originalBrowserOwnerAccepted":True,
      "originalBrowserOwnerCases":readback["browserE2eCases"],
      "originalBrowserReceiptSha":sha_file(original_browser),
      "deliveryArchive":str(archive),
      "deliveryArchiveSha":sha_file(archive),
      "browserNetworkBlocked":True,
      "nativeGuestNotInvoked":True,
      "nativeCryptographicOwnerAcceptance":False,
      "browserOSIsolationNotIndependentlyAttested":True,
      "modelCodeOnHostUnrestricted":False,
      "modelCodeExecutedOnlyInWasiAndChromiumSandbox":True,
      "npmLifecycleScriptsExecuted":False,
      "protectedHostInstallationPerformed":False,
      "scope":"OWNER_PINNED_TWO_MODULE_ESM_WASI_AND_CHROME_OFFLINE_NOT_NATIVE_GUEST_NOT_UNIVERSAL"
    }
    write_json(d/"result.json",evidence,new=True)
    event(d/"journal.jsonl","FACTORY_BROWSER_INDEPENDENT_OWNER_ACCEPTED",
      {"originalBrowserReceiptSha":sha_file(original_browser),
       "repoManifestSha":sha_file(source),
       "resultSha":sha_file(d/"result.json"),
       "originalWasiCases":pinned["ownerCases"],
       "originalChromeCases":readback["browserE2eCases"],
       "deliveryArchiveSha":sha_file(archive)})
    _set(d,SUCCESS_BROWSER,
       "original independent WASI and offline Chrome PASS, no native guest needed",
       resultSha=sha_file(d/"result.json"))
    return {**evidence,"deliveryStatus":"REPO_BROWSER_WASI_E2E_PASS"}



def run(root, workflow_id):
    root=engine.init(root)
    d=folder(root,workflow_id)
    original=load(d/"state.json")["status"]
    if original!="PENDING":
        raise RuntimeError("FACTORY_ORIGINAL_OPERATION_ALREADY_INTENDED_NO_REPLAY:"+original)
    if (d/"repo-ref.json").exists() or (d/"native-ref.json").exists():
        raise RuntimeError("FACTORY_EXISTING_CHILD_REF_NO_REPLAY")
    original_intent=load(d/"intent.json")
    source=Path(original_intent["sourceOriginalPath"])
    if sha_file(source)!=original_intent["ownerOriginalSha"]:
        raise RuntimeError("FACTORY_OWNER_SPEC_CHANGED_BEFORE_INFERENCE")
    if _stopped(d):
        _set(d,"STOPPED_PRE_INTENT","STOP before original repo and model intent")
        return {"status":"STOPPED_PRE_INTENT","workflowId":workflow_id}
    _set(d,"REPO_CREATE_INTENT","original child repo creation follows; never retry unknown")
    try:
        repo_created=repo_factory.create(root,source)
        if repo_created["status"]!="PENDING":
            raise RuntimeError("FACTORY_REPO_SPEC_ALREADY_USED_NO_NEW_INFERENCE")
        repo=repo_created["jobId"]
        write_json(d/"repo-ref.json",
                   {"schema":1,"jobId":repo,
                    "originalRepoSpecSha":sha_file(root/"repojobs"/repo/"spec.json"),
                    "atUtc":utc()},new=True)
        event(d/"journal.jsonl","FACTORY_REPO_ORIGINAL_ATTACHED",
              {"repo":repo,"refSha":sha_file(d/"repo-ref.json")})
        if _stopped(d):
            repo_factory.stop(root,repo)
            _set(d,"STOPPED_SAFE_BOUNDARY","original repo not inferred; STOP forwarded")
            return {"status":"STOPPED_SAFE_BOUNDARY","workflowId":workflow_id,"repo":repo}
        _set(d,"REPO_MODEL_WASI_INTENT","three bounded model attempts at most",repo=repo)
        model=repo_factory.run(root,repo,max_tokens=original_intent["maxTokens"],
                               max_attempts=original_intent["maxAttempts"],
                               provider=original_intent["provider"])
        check=repo_factory.status(root,repo)
        if model.get("status")!="PASS" or check["status"]!="PASS":
            final=("STOPPED_SAFE_BOUNDARY" if check["status"].startswith("STOPPED")
                   else "UNKNOWN" if check["status"]=="UNKNOWN" else "FAILED_REPO")
            _set(d,final,"original model/WASI not accepted; native VM MUST NOT launch",
                 originalRepoStatus=check["status"],repo=repo)
            return {"status":final,"workflowId":workflow_id,
                    "originalRepoStatus":check["status"],"repo":repo}
        accepted=repo_factory.verify(root,repo)
        if (not accepted["verified"] or accepted["ownerCases"]!=original_intent["ownerCases"]):
            raise RuntimeError("FACTORY_INDEPENDENT_OWNER_ACCEPTANCE_DRIFT")
        event(d/"journal.jsonl","FACTORY_WASI_OWNER_ACCEPTED",
              {"manifestSha":sha_file(root/"repojobs"/repo/"manifest.json"),
               "ownerCases":accepted["ownerCases"]})
        if _stopped(d):
            _set(d,"STOPPED_SAFE_BOUNDARY","STOP after WASI, before native cycle",repo=repo)
            return {"status":"STOPPED_SAFE_BOUNDARY","workflowId":workflow_id,"repo":repo}
        if original_intent.get("acceptanceMode","wasi-native")=="wasi-browser":
            return _receipt_browser(d,workflow_id,repo)
        _set(d,"NATIVE_CREATE_INTENT","native original one-shot cycle creation follows",repo=repo)
        cycle_created=native_cycle.create(root,repo)
        if cycle_created["status"]!="PENDING":
            raise RuntimeError("FACTORY_NATIVE_CYCLE_DUPLICATE_NO_REPLAY")
        cycle=cycle_created["cycleId"]
        write_json(d/"native-ref.json",
                   {"schema":1,"cycleId":cycle,
                    "originalNativeIntentSha":sha_file(native_cycle.folder(root,cycle)/"intent.json"),
                    "atUtc":utc()},new=True)
        event(d/"journal.jsonl","FACTORY_NATIVE_ORIGINAL_ATTACHED",
              {"cycle":cycle,"refSha":sha_file(d/"native-ref.json")})
        if _stopped(d):
            native_cycle.stop(root,cycle)
            _set(d,"STOPPED_SAFE_BOUNDARY","STOP before native guest")
            return {"status":"STOPPED_SAFE_BOUNDARY","workflowId":workflow_id,"cycle":cycle}
        _set(d,"NATIVE_GUEST_INTENT","original isolated VM run follows",cycle=cycle)
        output=native_cycle.run(root,cycle)
        if output.get("status")!=native_cycle.OK:
            state=("BLOCKED_VM_CONFLICT" if output.get("status")=="BLOCKED_VM_CONFLICT"
                   else "UNKNOWN" if output.get("status")=="UNKNOWN"
                   else "FAILED_NATIVE")
            _set(d,state,"native original result not PASS; do not replay",
                 nativeOriginalStatus=output.get("status"),cycle=cycle)
            return {"status":state,"workflowId":workflow_id,"cycle":cycle,
                    "nativeOriginalStatus":output.get("status")}
        if _stopped(d):
            _set(d,"STOPPED_SAFE_BOUNDARY","STOP supersedes native untrusted report")
            return {"status":"STOPPED_SAFE_BOUNDARY","workflowId":workflow_id,"cycle":cycle}
        return _receipt(d,workflow_id,repo,cycle,output)
    except Exception as ex:
        # Once a side effect may have been attempted, never rerun this workflow.
        _set(d,"UNKNOWN","original child may have side effects, reconcile receipts",
             errorType=type(ex).__name__,errorMessage=str(ex)[:220])
        raise




def submit(root, spec_path, *, provider="small", acceptance_mode="wasi-native"):
    """A single user action creates original intent, queues it, starts original worker.

    Never treat a duplicate as permission to restart a prior operation.
    """
    from . import supervisor
    root=engine.init(root)
    live=supervisor.status(root)
    if live["status"] not in ("STOPPED","RUNNING"):
        raise RuntimeError("FACTORY_SUPERVISOR_LEASE_UNKNOWN_RECONCILE_FIRST")
    created=create(root,spec_path,provider=provider,acceptance_mode=acceptance_mode)
    if created["status"]!="PENDING":
        return created
    queued=supervisor.enqueue(root,"factory",created["workflowId"])
    if queued["status"]!="PENDING":
        raise RuntimeError("FACTORY_EXISTING_QUEUE_DO_NOT_RESTART")
    started=(supervisor.start(root) if live["status"]=="STOPPED"
             else {"status":"RUNNING_VERIFIED_EXISTING","lease":live.get("lease")})
    return {"status":"SUPERVISOR_RUNNING_VERIFIED"
                    if started["status"] in ("RUNNING_VERIFIED","RUNNING_VERIFIED_EXISTING")
                    else "UNKNOWN_SUPERVISOR_START_RECONCILE",
            "workflowId":created["workflowId"],
            "queueId":queued["queueId"],"start":started,
            "nativeResultAlreadyClaimed":False}


def reconcile(root, workflow_id):
    """Read-only original receipt inspection; never calls model or native launch."""
    root=engine.init(root)
    d=folder(root,workflow_id)
    ret=status(root,workflow_id)
    if (d/"repo-ref.json").exists():
        ref=load(d/"repo-ref.json")["jobId"]
        ret["originalRepo"]=repo_factory.status(root,ref)
        if ret["originalRepo"]["status"]=="PASS":
            ret["originalOwnerVerified"]=repo_factory.verify(root,ref)["verified"]
    if (d/"native-ref.json").exists():
        ret["originalNative"]=native_cycle.reconcile(root,load(d/"native-ref.json")["cycleId"])
    if (d/"result.json").is_file():
        ret["originalResult"]=load(d/"result.json")
    if ret["status"]==SUCCESS_BROWSER:
        from . import repo_export
        if not (d/"repo-ref.json").is_file():
            raise RuntimeError("BROWSER_ORIGINAL_REPO_REF_MISSING")
        job=load(d/"repo-ref.json")["jobId"]
        ret["originalBrowserVerified"]=repo_export.verify(root,job)["verified"]
    return ret
