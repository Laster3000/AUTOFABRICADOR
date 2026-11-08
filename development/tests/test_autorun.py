# coding: utf-8
"""Original supervisor user-session autorun: fail-closed, no duplicate/unknown replay."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autofab import autorun

def status(mode="STOPPED",pending=0,control="STOP"):
    return {"status":mode,"lease":{"status":mode},"pendingQueue":pending,
            "control":{"command":control}}

class AutorunOriginalWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.engine=patch.object(autorun.engine,"init",return_value=self.root)
        self.engine.start()
    def tearDown(self):
        self.engine.stop()
        self.temp.cleanup()
    def test_running_worker_is_not_duplicated(self):
        with patch.object(autorun.supervisor,"status",return_value=status("RUNNING")),\
             patch.object(autorun.service_worker,"begin") as worker:
            row=autorun.boot(self.root)
            self.assertEqual(row["status"],"ALREADY_RUNNING_ORIGINAL_NO_DUPLICATE")
            worker.assert_not_called()
    def test_pending_original_job_cannot_be_auto_consumed(self):
        with patch.object(autorun.supervisor,"status",return_value=status(pending=1)),\
             patch.object(autorun.service_worker,"begin") as worker:
            with self.assertRaisesRegex(RuntimeError,"PENDING"):
                autorun.boot(self.root)
            worker.assert_not_called()
    def test_original_stopped_worker_can_start(self):
        with patch.object(autorun.supervisor,"status",return_value=status()),\
             patch.object(autorun.service_worker,"begin",return_value={"status":"STOPPED"}) as worker:
            self.assertEqual(autorun.boot(self.root)["status"],"STOPPED")
            worker.assert_called_once_with(self.root)
    def test_stale_original_lease_must_reconcile_no_replay(self):
        with patch.object(autorun.supervisor,"status",side_effect=[
             status("UNKNOWN_LEASE_STALE_RECONCILE"),status()]),\
             patch.object(autorun.supervisor,"reconcile_stale",
                 return_value={"status":"STOPPED_RECONCILED_NO_NEW_MODEL_CALLS"}) as recovery,\
             patch.object(autorun.service_worker,"begin",return_value={"status":"STOPPED"}) as worker:
            autorun.boot(self.root)
            recovery.assert_called_once()
            worker.assert_called_once()
    def test_unreconciled_original_stale_lease_blocks(self):
        with patch.object(autorun.supervisor,"status",return_value=status("UNKNOWN_LEASE_STALE_RECONCILE")),\
             patch.object(autorun.supervisor,"reconcile_stale",
                 return_value={"status":"UNKNOWN"}) as recovery,\
             patch.object(autorun.service_worker,"begin") as worker:
            with self.assertRaisesRegex(RuntimeError,"NOT_RECONCILED"):
                autorun.boot(self.root)
            recovery.assert_called_once()
            worker.assert_not_called()

if __name__=="__main__":unittest.main()
