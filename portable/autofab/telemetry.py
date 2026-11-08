"""Reconciled per-language cost ledger from original immutable receipts only."""
from pathlib import Path
import json
from . import engine,csharp_jobs,multilang,direct_agent,webapps,repo_factory,repo_export
from .storage import load,sha_file

def combined(root):
    root=engine.init(root)
    base=engine.metrics(root)
    lang=[]
    source_calls=0
    ts_pass=js_pass=0
    for folder in sorted((root/"langjobs").glob("AL-*")):
        state=load(folder/"state.json")
        spec=load(folder/"spec.json")
        origin=folder/"original-output.json"
        present=origin.is_file()
        if present:
            source_calls+=1
        passed=state["status"]=="PASS" and (folder/"manifest.json").is_file()
        if passed:multilang.verify(root,folder.name)
        if passed and spec["language"]=="javascript":js_pass+=1
        if passed and spec["language"]=="typescript":ts_pass+=1
        lang.append({"jobId":folder.name,"language":spec["language"],
                     "status":state["status"],
                     "originalModelCallRecorded":present,
                     "acceptanceTests":len(spec["acceptance"]) if passed else 0})
    cs=[]
    cs_calls=0
    for folder in sorted((root/"csharpjobs").glob("AC-*")):
        s=load(folder/"state.json")["status"]
        cs_calls+=int((folder/"original-output.json").is_file())
        accepted=s=="PASS" and csharp_jobs.verify(root,folder.name).get("verified") is True
        cs.append({"jobId":folder.name,"status":s,"functionalAcceptanceProven":accepted,
                   "ownerTestCount":load(folder/"WASI-ACCEPTED-MANIFEST.json")["ownerTestCount"] if accepted else 0,
                   "originalModelCallRecorded":(folder/"original-output.json").is_file()})
    direct=[]
    direct_calls=0
    for folder in sorted((root/"directjobs").glob("AD-*")):
        state=load(folder/"state.json")["status"]
        original=(folder/"stream-receipt.json").exists()
        direct_calls+=int(original)
        accepted=state=="PASS" and direct_agent.verify(root,folder.name)["verified"]
        direct.append({"jobId":folder.name,"status":state,
                       "accepted":accepted,"originalStreamRecorded":original,
                       "ownerTestCount":len(load(folder/"spec.json")["acceptance"]) if accepted else 0})
    repo=[]
    repo_calls=0
    for folder in sorted((root/"repojobs").glob("RJ-*")):
        state=load(folder/"state.json")["status"]
        original=sorted((folder/"attempts").glob("A-*-stream.json"))
        repo_calls+=len(original)
        accepted=state=="PASS" and repo_factory.verify(root,folder.name)["verified"]
        exported=(root/"repoexports"/("AF-REPO-"+folder.name+".zip")).is_file()
        if exported:repo_export.verify(root,folder.name)
        repo.append({"jobId":folder.name,"status":state,
               "accepted":accepted,"modelCallsFromOriginalStreamReceipts":len(original),
               "originalOwnerCount":len(load(folder/"spec.json")["acceptance"]) if accepted else 0,
               "modelProvider":load(folder/"manifest.json").get("provider") if accepted else None,
               "browserAppOwnerAccepted":exported})
    probes=[]
    for folder in sorted((root/"cancelprobes").glob("CP-*")):
        probes.append({"jobId":folder.name,"status":load(folder/"state.json")["status"],
                       "originalModelStreamRecorded":(folder/"stream.json").is_file()})
    supervisor=[]
    sup=root/"supervisor"
    if sup.is_dir():
        for task in sorted((sup/"queue").glob("SQ-*.json")):
            item=load(task)
            supervisor.append({"queueId":item["queueId"],"kind":item["kind"],
                               "status":item["status"],"stopDuringChild":item.get("stopRequestedDuringChild",False)})
    base["additionalLanguageJobs"]=lang
    base["additionalCsharpJobs"]=cs
    base["additionalDirectNoNativeEditorJobs"]=direct
    base["additionalESMRepositoryJobs"]=repo
    base["cancelDiagnosticProbesNotAccepted"]=probes
    base["supervisorTasks"]=supervisor
    base["scopeNote"]="Original model streams count each distinct attempt, including failed 1.5B repo attempts; deterministic compiler, packaging and cache readback are not model inference. Repo source is accepted only from pinned WASI owner receipt."
    base["combinedTotals"]={
        "nativePythonAccepted":base["totals"]["completedRealAI"],
        "javascriptAccepted":js_pass+sum(x["accepted"] for x in direct)+sum(x["accepted"] and load(root/"repojobs"/x["jobId"]/"spec.json")["language"]=="javascript" for x in repo),
        "esmRepoOriginalAiAccepted":sum(x["accepted"] for x in repo),
        "esmRepoModel14bAccepted":sum(x["accepted"] and x["modelProvider"]=="coder14b" for x in repo),
        "javascriptAcceptedThroughNativeEditors":js_pass,
        "javascriptAcceptedThroughDirectHTTP":sum(x["accepted"] for x in direct),
        "typescriptAccepted":ts_pass,
        "csharpCompiledButNotAccepted":sum(x["status"]=="COMPILED_UNEXECUTED" for x in cs),
        "csharpOwnerAccepted":sum(x["functionalAcceptanceProven"] for x in cs),
        "totalAccepted":base["totals"]["completedRealAI"]+js_pass+ts_pass+sum(x["functionalAcceptanceProven"] for x in cs)+sum(x["accepted"] for x in direct)+sum(x["accepted"] for x in repo),
        "offlineWebApplicationsPackaged":sum(1 for f in (root/"apps").glob("AF-WEB-*.zip") if f.is_file()) if (root/"apps").exists() else 0,
        "multiModuleWebProjectsAccepted":sum(1 for f in (root/"projects").glob("LEDGER-AD-*.zip") if f.is_file()) if (root/"projects").exists() else 0,
        "esmGraphPortableBrowserAppsAccepted":sum(x["browserAppOwnerAccepted"] for x in repo),
        "esmRepoFailuresPreserved":sum(x["status"]=="FAILED_OWNER_ACCEPTANCE" for x in repo),
        "activeInferenceCancellationProbesVerified":sum(x["status"]=="CANCELLED_VERIFIED" for x in probes),
        "originalModelCallsRecorded":base["totals"]["modelCalls"]+source_calls+cs_calls+direct_calls+repo_calls+sum(x["originalModelStreamRecorded"] for x in probes),
        "originalESMRepoModelCalls":repo_calls,
        "directHTTPStreamOriginalCalls":direct_calls,
        "cancellationDiagnosticModelCalls":sum(x["originalModelStreamRecorded"] for x in probes),
        "originalAdvisoryCalls":base["totals"]["advisorCalls"],
        "unknownLegacyJobs":sum(x["status"]=="UNKNOWN" for x in base["jobs"]),
        "cloudApiBillEurKnown":0,
        "electricityAndHardwareCost":"UNMEASURED"}
    staged=[]
    for folder in sorted((root/"sandboxjobs").glob("SX-*")):
        state=load(folder/"state.json")["status"]
        staged.append({"jobId":folder.name,"status":state,
                       "hostNativeModelCodeExecuted":False,
                       "independentlyAcceptedNativeGuestTests":0})
    base["windowsSandboxNativeJobs"]=staged
    base["combinedTotals"]["nativeWindowsSandboxGuestAccepted"]=0
    base["combinedTotals"]["nativeWindowsSandboxJobsStaged"]=len(staged)
    return base
