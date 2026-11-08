"""One-command lifecycle: generate with model, stop owned server, test in WASI.

Only the local service spawned by this invocation is automatically stopped.
Persisted jobs in UNCERTAIN states are never replayed.
"""
from . import draft, engine, local_runtime
from .storage import load

def _run_job(root,jobid):
    root=engine.init(root)
    cfg=engine.settings(root)
    folder=engine.jobdir(root,jobid)
    previous=load(folder/"state.json")
    if cfg["provider"]!="llama_cpp":
        return engine.run(root,jobid)
    if previous["status"] in ("PASS","PASS_FIXTURE","FAILED","UNKNOWN","STAGNATED",
                               "RUNNING","MODEL_PENDING","TEST_PENDING","DRAFT_READY_UNTESTED"):
        return engine.run(root,jobid)
    attempt=previous.get("attempt",0)
    if attempt and (folder/f"attempt-{attempt:02d}"/"model.json").is_file() and not (
            folder/f"attempt-{attempt:02d}"/"test.json").is_file():
        return engine.run(root,jobid)
    if previous["status"]=="STOPPED":
        return engine.run(root,jobid)
    # The singular source-generation pipeline is DRAFT -> isolated verifier;
    # engine.run does not generate a second response after DRAFT has receipts.
    status=local_runtime.server_info(root)
    if status["state"]=="EXITED":
        local_runtime.stop(root)
        status=local_runtime.server_info(root)
    if status["state"] not in ("READY","NOT_STARTED"):
        raise RuntimeError("LOCAL_SERVER_STATUS_UNCERTAIN:"+status["state"])
    started_here=False
    if status["state"]=="NOT_STARTED":
        ready=local_runtime.start(root)
        if ready["state"]!="READY":
            raise RuntimeError("LOCAL_SERVER_NOT_READY:"+ready["state"])
        started_here=True
    try:
        generated=draft.draft(root,jobid)
    finally:
        if started_here:
            stopped=local_runtime.stop(root)
            if stopped.get("state") not in ("STOPPED","STOPPED_RECONCILED"):
                raise RuntimeError("LOCAL_SERVER_NOT_CLEANLY_STOPPED")
    latest=load(folder/"state.json")
    if latest["status"]=="DRAFT_READY_UNTESTED":
        return engine.run(root,jobid)
    return generated


def run_job(root,jobid):
    """Perform one bounded job and auto-clean only regenerable local litter."""
    result=_run_job(root,jobid)
    from . import housekeeping
    try:
        clean=housekeeping.maintain(root,apply=True)
        if isinstance(result,dict):
            result["housekeeping"]={
                "status":"PASS" if clean["mode"]=="APPLY" else clean["mode"],
                "changed":clean["changed"],"filesAffected":clean["filesAffected"],
                "policy":"No work/receipt/model/cache/rollback deletion"}
    except Exception as error:
        # Maintenance failure cannot turn original PASS into fake failure or
        # silently erase evidence. Explicit warning is returned for escalation.
        if isinstance(result,dict):
            result["housekeeping"]={"status":"ERROR","errorType":type(error).__name__,
                                    "detail":str(error)[:350]}
    return result
