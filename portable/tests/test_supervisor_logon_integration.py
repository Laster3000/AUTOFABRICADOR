# coding: utf-8
"""Prove the ORIGINAL supervisor, not a parallel daemon, arms boot readback."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autofab import supervisor,logon_observer
from autofab.storage import load,verify_journal

class OriginalSupervisorLogonObserverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="af-sup-logon-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"autofabricador.py").write_text("test CLI fixture",encoding="utf-8")
        self.engine=patch.object(supervisor.engine,"init",return_value=self.root)
        self.engine.start()
        self.addCleanup(self.engine.stop)
    def test_original_worker_arms_readback_after_authenticated_lease(self):
        with patch.object(supervisor,"process_born",return_value=1000000),\
             patch.object(logon_observer,"begin",return_value={"status":"NO_REBOOT_BASELINE_NO_THREAD"}) as begin:
            result=supervisor.worker(self.root)
            begin.assert_called_once()
        self.assertEqual(result["status"],"STOPPED")
        passed_root,lease=begin.call_args.args
        self.assertEqual(passed_root,self.root)
        self.assertEqual(lease["processBornFiletime"],1000000)
        self.assertEqual(lease["status"],"RUNNING")
        self.assertEqual(load(self.root/"supervisor"/"lease.json")["status"],"STOPPED")
        verify_journal(self.root/"supervisor"/"journal.jsonl")
    def test_observer_failure_does_not_spawn_job_or_kill_original_worker(self):
        with patch.object(supervisor,"process_born",return_value=123),\
             patch.object(logon_observer,"begin",side_effect=RuntimeError("OBS_ERR")):
            result=supervisor.worker(self.root)
        self.assertEqual(result["status"],"STOPPED")
        self.assertEqual(list((self.root/"supervisor"/"queue").glob("SQ-*.json")),[])
        j=(self.root/"supervisor"/"journal.jsonl").read_text()
        self.assertIn("ORIGINAL_LOGON_READBACK_SETUP_FAILED",j)
        verify_journal(self.root/"supervisor"/"journal.jsonl")

if __name__=="__main__": unittest.main()
