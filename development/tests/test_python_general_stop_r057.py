"""R057 original general Python STOP no model call/no original replay."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import python_general
from autofab.storage import write_json,sha_file,event,verify_journal,transition
class GeneralStopR057(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="R057-PG-STOP-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.ident="PG-0123456789abcdef"
        self.d=self.root/"pygeneral"/self.ident
        self.d.mkdir(parents=True)
        write_json(self.d/"plan.json",{"schema":1,"taskId":"test"},new=True)
        write_json(self.d/"state.json",{"schema":1,"status":"PENDING"},new=True)
        write_json(self.d/"control.json",{"schema":1,"command":"RUN"},new=True)
        event(self.d/"journal.jsonl","FIRST_PARTY_OWNER_PINNED",{"ok":True})
    def test_stop_preintent_is_sha_cas_and_idempotent(self):
        before=sha_file(self.d/"control.json")
        with patch.object(python_general.local_runtime,"start",
                          side_effect=AssertionError("MODEL_WOULD_BE_REPLAYED")):
            first=python_general.stop(self.root,self.ident)
            second=python_general.stop(self.root,self.ident)
        self.assertEqual(first["status"],"STOP_REQUESTED")
        self.assertEqual(second["status"],"STOP_ALREADY_REQUESTED")
        self.assertTrue((self.d/"history"/("control-"+before+".json")).is_file())
        self.assertEqual(verify_journal(self.d/"journal.jsonl")["events"],2)
        self.assertFalse((self.d/"request.json").exists())
    def test_stop_terminal_does_not_change_original(self):
        transition(self.d/"state.json",{"schema":1,
            "status":"FAILED_ORIGINAL_OWNER"},self.d/"history")
        before=sha_file(self.d/"control.json")
        self.assertEqual(python_general.stop(self.root,self.ident)["status"],
                         "ORIGINAL_TERMINAL_NO_REPLAY")
        self.assertEqual(sha_file(self.d/"control.json"),before)
    def test_status_preintention_readback(self):
        current=python_general.status(self.root,self.ident)
        self.assertEqual(current["status"],"PENDING")
        self.assertFalse(current["originalModelIntentRecorded"])
        self.assertIsNone(current["verified"])
