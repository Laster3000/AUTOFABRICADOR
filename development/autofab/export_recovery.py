# coding: utf-8
"""R057 FINAL disposition of one original incomplete browser APP_INTENT.

This is not a browser retry or source promotion. It is an original immutable
evidence-backed closure for a prior single REPO_APP_INTENT without original
Chrome receipt or ZIP. Separate original passed new Chrome job is preserved.
"""
from __future__ import annotations
import uuid,re
from pathlib import Path
from . import engine,repo_factory,repo_export
from .storage import load,write_json,sha_file,event,verify_journal,utc
_ID="RJ-f356972ec4854742"
_CLOSE_ID=re.compile(r"EC-[a-f0-9]{16}\Z")
def _observed(root,jobId):
    root=Path(root).resolve()
    if jobId!=_ID:raise ValueError("ORIGINAL_BROWSER_CLOSURE_ID_NOT_SUPPORTED")
    original=repo_factory.verify(root,jobId)
    if original["status"]!="PASS" or not original["verified"]:
        raise RuntimeError("ORIGINAL_BROWSER_SOURCE_NOT_ACCEPTED")
    d=repo_factory.directory(root,jobId)
    source=load(d/"manifest.json")
    folder=root/"repoexports"/("AF-REPO-"+jobId+"-receipts")
    journal=folder/"journal.jsonl"
    archive=root/"repoexports"/("AF-REPO-"+jobId+".zip")
    assert folder.is_dir() and journal.is_file()
    verified=verify_journal(journal)
    original_lines=journal.read_text("utf-8").strip().splitlines()
    if (verified["events"]!=1 or len(original_lines)!=1 or
        '"REPO_APP_INTENT"' not in original_lines[0]):
        raise RuntimeError("ORIGINAL_BROWSER_COMPLETION_EVENTS_UNKNOWN")
    if (archive.is_file() or
        any((folder/n).exists() for n in ("BROWSER-RECEIPT.json",
             "PACKAGE-RECEIPT.json","PROJECT-MANIFEST.json"))):
        raise RuntimeError("ORIGINAL_BROWSER_HAS_ARTIFACTS_MUST_VERIFY_NOT_CLOSE")
    return {"jobId":jobId,"originalJournalSha":sha_file(journal),
     "originalRepoManifestSha":sha_file(d/"manifest.json"),
     "originalRepoOwnerSha":sha_file(d/"owner-acceptance.json"),
     "originalCompiledSha":source["bundleSha"],
     "originalJournalEvents":verified["events"],
     "originalArchiveExists":False,"originalBrowserReceiptExists":False,
     "originalSourceIsAccepted":True}
def classify(root,jobId):
    root=Path(root).resolve()
    observed=_observed(root,jobId)
    close_dir=root/"exportclosures"
    if close_dir.is_dir():
        for row in close_dir.glob("EC-*/report.json"):
            rec=load(row)
            if rec["originalJobId"]==jobId:
                return verify(root,row.parent.name)
    return {"status":"ORIGINAL_BROWSER_INCOMPLETE_UNCLOSED_NO_REPLAY",
            **observed}
def close(root,jobId):
    root=engine.init(root)
    observation=_observed(root,jobId)
    existing=classify(root,jobId)
    if existing["status"]!="ORIGINAL_BROWSER_INCOMPLETE_UNCLOSED_NO_REPLAY":
        return {"status":"PREEXISTING_ORIGINAL_CLOSURE_NO_REPLAY","original":existing}
    store=root/"exportclosures";store.mkdir(exist_ok=True)
    ident="EC-"+uuid.uuid4().hex[:16]
    d=store/ident;d.mkdir(exist_ok=False)
    plan={"schema":1,"atUtc":utc(),
      "operationId":ident+".ORIGINAL_APP_INTENT_DISPOSITION",
      "closureId":ident,"originalJobId":jobId,"originalEvidence":observation,
      "noPriorAppEffectReplay":True,"notSuccessfulBrowserExport":True,
      "existingOriginalJournalLeftUnchanged":True,
      "noOriginalBrowserReceiptsReconstructed":True}
    write_json(d/"plan.json",plan,new=True)
    event(d/"journal.jsonl","ORIGINAL_INCOMPLETE_BROWSER_INTENT_OWNER_FROZEN",
      {"planSha":sha_file(d/"plan.json"),
       "originalAppIntentJournalSha":observation["originalJournalSha"]})
    report={"schema":1,"atUtc":utc(),
      "operationId":plan["operationId"],
      "status":"CLOSED_INCOMPLETE_ORIGINAL_BROWSER_APP_INTENT_NO_REPLAY",
      "closureId":ident,"originalJobId":jobId,
      "originalSourceStillAccepted":True,
      "originalBrowserSuccessfullyExported":False,
      "originalBrowserE2eTested":False,
      "originalArchiveExists":False,
      "originalObservedAppJournalSha":observation["originalJournalSha"],
      "originalOwnerSha":observation["originalRepoOwnerSha"],
      "originalRepoManifestSha":observation["originalRepoManifestSha"],
      "noModelCalls":True,"noBrowserCalls":True,"noOriginalAppIntentReplay":True,
      "closureIsDispositionalNotOriginalReconstructedReceipt":True}
    write_json(d/"report.json",report,new=True)
    event(d/"journal.jsonl","ORIGINAL_BROWSER_INCOMPLETE_DISPOSITION_READBACK",
      {"reportSha":sha_file(d/"report.json"),"notBrowserPass":True})
    return verify(root,ident)
def verify(root,ident):
    root=Path(root).resolve()
    if not isinstance(ident,str) or not _CLOSE_ID.fullmatch(ident):
        raise ValueError("ORIGINAL_BROWSER_CLOSURE_ID_INVALID")
    d=root/"exportclosures"/ident
    if not (d/"plan.json").is_file() or not (d/"report.json").is_file():
        raise FileNotFoundError("ORIGINAL_BROWSER_CLOSURE_UNKNOWN")
    verify_journal(d/"journal.jsonl")
    plan=load(d/"plan.json")
    current=_observed(root,plan["originalJobId"])
    if current!=plan["originalEvidence"]:
        raise RuntimeError("ORIGINAL_BROWSER_APP_INTENT_SHA_OR_STATE_CHANGED")
    report=load(d/"report.json")
    if (report["originalObservedAppJournalSha"]!=current["originalJournalSha"] or
        report["originalBrowserSuccessfullyExported"] is not False):
        raise RuntimeError("ORIGINAL_BROWSER_CLOSURE_RECEIPT_DRIFT")
    return {"status":report["status"],"closureId":ident,
      "originalJobId":plan["originalJobId"],
      "originalOwnerUnchanged":True,
      "originalAppIntentReplayed":False,
      "originalBrowserCompleted":False,
      "originalAppJournalSha":current["originalJournalSha"],
      "dispositionReceiptSha":sha_file(d/"report.json")}
