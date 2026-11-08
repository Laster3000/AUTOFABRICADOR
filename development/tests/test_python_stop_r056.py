"""R056 Python original STOP control never launches or replays local inference."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import python_direct
from autofab.storage import write_json,event,sha_file,verify_journal
class PythonStopR056(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="R056-PYSTOP-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.ident="PD-0123456789abcdef"
        self.d=self.root/"pythondirect"/self.ident
        self.d.mkdir(parents=True)
        write_json(self.d/"plan.json",{"schema":1,"original":"test"},new=True)
        write_json(self.d/"state.json",{"schema":1,"status":"PENDING"},new=True)
        write_json(self.d/"control.json",{"schema":1,"command":"RUN"},new=True)
        event(self.d/"journal.jsonl","ORIGINAL_INTENT_PINNED",{"new":True})
    def test_pre_stop_cas_no_model_and_journal(self):
        before=sha_file(self.d/"control.json")
        with patch.object(python_direct.local_runtime,"start",
                          side_effect=AssertionError("MODEL_START_FORBIDDEN")):
            first=python_direct.stop(self.root,self.ident)
            second=python_direct.stop(self.root,self.ident)
        self.assertEqual(first["status"],"STOP_REQUESTED")
        self.assertEqual(second["status"],"STOP_ALREADY_REQUESTED")
        self.assertNotEqual(before,sha_file(self.d/"control.json"))
        self.assertTrue((self.d/"history"/("control-"+before+".json")).is_file())
        self.assertEqual(verify_journal(self.d/"journal.jsonl")["events"],2)
        self.assertFalse((self.d/"request.json").exists())
    def test_terminal_stop_refuses_edit(self):
        from autofab.storage import transition,load
        transition(self.d/"state.json",{"schema":1,"status":"FAILED_SOURCE_FORMAT"},self.d/"history")
        before=sha_file(self.d/"control.json")
        stop=python_direct.stop(self.root,self.ident)
        self.assertEqual(stop["status"],"TERMINAL_NO_REPLAY")
        self.assertEqual(sha_file(self.d/"control.json"),before)
    def test_status_prepending_reflects_original_journal(self):
        status=python_direct.status(self.root,self.ident)
        self.assertEqual(status["status"],"PENDING")
        self.assertFalse(status["requestRecorded"])
        self.assertIsNone(status["verified"])
