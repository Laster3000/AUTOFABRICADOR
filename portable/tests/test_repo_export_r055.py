"""R055 original export readback guards; no browser effect in these unit tests."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import repo_export
from autofab.storage import event,sha_file,write_json
class ExportR055(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="R055-EXPORT-")
        self.addCleanup(self.tmp.cleanup)
        self.r=Path(self.tmp.name)
        self.job="RJ-0123456789abcdef"
        self.ev=self.r/"repoexports"/("AF-REPO-"+self.job+"-receipts")
        self.ev.mkdir(parents=True)
        self.original=(
           patch.object(repo_export.engine,"init",return_value=self.r),
           patch.object(repo_export.webapps,"preflight",return_value={"ok":True}),
           patch.object(repo_export,"_original",
             return_value=(self.r,{"source":"trusted"}, {"bundleSha":"known"},self.r/"fake.js",{})),
           patch.object(repo_export.subprocess,"run",
             side_effect=AssertionError("NO_BROWSER_MAY_LAUNCH_FOR_OLD_INTENT")))
        for x in self.original:self.addCleanup(x.stop);x.start()
    def test_original_incomplete_journal_never_replayed(self):
        event(self.ev/"journal.jsonl","REPO_APP_INTENT",{"jobId":self.job})
        sha=sha_file(self.ev/"journal.jsonl")
        r=repo_export.export(self.r,self.job)
        self.assertEqual(r["status"],"ORIGINAL_EXPORT_INCOMPLETE_INTENT_NO_REPLAY")
        self.assertEqual(r["originalJournalEvents"],1)
        self.assertEqual(r["originalJournalSha"],sha)
        self.assertFalse(r["archiveExists"])
        self.assertTrue(r["manualOriginalReconciliationRequired"])
        self.assertEqual(sha_file(self.ev/"journal.jsonl"),sha)
        self.assertEqual(len(list(self.ev.iterdir())),1)
    def test_existing_archive_without_receipt_is_unknown(self):
        (self.r/"repoexports"/("AF-REPO-"+self.job+".zip")).write_bytes(b"incomplete")
        event(self.ev/"journal.jsonl","REPO_APP_INTENT",{"jobId":self.job})
        a=repo_export.export(self.r,self.job)
        self.assertEqual(a["status"],"ORIGINAL_EXPORT_INCOMPLETE_INTENT_NO_REPLAY")
        self.assertTrue(a["archiveExists"])
    def test_complete_original_package_goes_to_verify_not_execute(self):
        (self.r/"repoexports"/("AF-REPO-"+self.job+".zip")).write_bytes(b"old")
        event(self.ev/"journal.jsonl","REPO_APP_INTENT",{"jobId":self.job})
        for p in ("PACKAGE-RECEIPT.json","PROJECT-MANIFEST.json","BROWSER-RECEIPT.json"):
            write_json(self.ev/p,{"trusted":True},new=True)
        with patch.object(repo_export,"verify",
           return_value={"verified":True,"status":"REPO_BROWSER_WASI_E2E_PASS"}) as v:
            outcome=repo_export.export(self.r,self.job)
        self.assertEqual(outcome["status"],"PREEXISTING_RECONCILE_NO_REPLAY")
        self.assertTrue(outcome["verify"]["verified"])
        self.assertEqual(v.call_count,1)
    def test_unknown_archive_without_receipts_directory_fail_closed(self):
        self.ev.rmdir()
        (self.r/"repoexports"/("AF-REPO-"+self.job+".zip")).write_bytes(b"untracked")
        x=repo_export.export(self.r,self.job)
        self.assertEqual(x["status"],"UNKNOWN_ORIGINAL_EXPORT_ARTIFACT_NO_REPLAY")
        self.assertTrue(x["requiresOriginalReadback"])
