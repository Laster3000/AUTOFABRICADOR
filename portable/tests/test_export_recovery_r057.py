"""R057 original incomplete APP_INTENT closure, without browser rerun."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import export_recovery
from autofab.storage import write_json,event,sha_file
class BrowserClosureR057(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="R057-EC-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.job="RJ-f356972ec4854742"
        self.source=self.root/"repojobs"/self.job
        self.source.mkdir(parents=True)
        write_json(self.source/"manifest.json",{"bundleSha":"abc123"},new=True)
        write_json(self.source/"owner-acceptance.json",{"owner":"test"},new=True)
        self.evidence=self.root/"repoexports"/("AF-REPO-"+self.job+"-receipts")
        self.evidence.mkdir(parents=True)
        event(self.evidence/"journal.jsonl","REPO_APP_INTENT",{"jobId":self.job})
        self.original_sha=sha_file(self.evidence/"journal.jsonl")
        self.mock_verify=patch.object(export_recovery.repo_factory,"verify",
                return_value={"status":"PASS","verified":True})
        self.mock_dir=patch.object(export_recovery.repo_factory,"directory",
                return_value=self.source)
        self.mock_init=patch.object(export_recovery.engine,"init",
                return_value=self.root)
        for p in (self.mock_verify,self.mock_dir,self.mock_init):
            p.start();self.addCleanup(p.stop)
    def test_original_one_event_closed_separately_no_replay(self):
        self.assertEqual(export_recovery.classify(self.root,self.job)["status"],
                         "ORIGINAL_BROWSER_INCOMPLETE_UNCLOSED_NO_REPLAY")
        closed=export_recovery.close(self.root,self.job)
        self.assertEqual(closed["status"],
                 "CLOSED_INCOMPLETE_ORIGINAL_BROWSER_APP_INTENT_NO_REPLAY")
        self.assertFalse(closed["originalBrowserCompleted"])
        self.assertEqual(sha_file(self.evidence/"journal.jsonl"),self.original_sha)
        again=export_recovery.close(self.root,self.job)
        self.assertEqual(again["status"],"PREEXISTING_ORIGINAL_CLOSURE_NO_REPLAY")
        self.assertEqual(sha_file(self.evidence/"journal.jsonl"),self.original_sha)
    def test_missing_browser_receipt_is_never_pass(self):
        disposition=export_recovery.close(self.root,self.job)
        self.assertNotIn("PASS_BROWSER",disposition["status"])
        self.assertFalse((self.evidence/"BROWSER-RECEIPT.json").exists())
        self.assertFalse((self.root/"repoexports"/("AF-REPO-"+self.job+".zip")).exists())
    def test_tampering_original_journal_denied(self):
        receipt=export_recovery.close(self.root,self.job)
        event(self.evidence/"journal.jsonl","ADDED_AFTER","{}" if False else {"fake":True})
        with self.assertRaisesRegex(RuntimeError,"ORIGINAL_BROWSER"):
            export_recovery.verify(self.root,receipt["closureId"])
    def test_bad_job_id_rejected(self):
        with self.assertRaises(ValueError):
            export_recovery.classify(self.root,"RJ-../wrong")
