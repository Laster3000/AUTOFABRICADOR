# coding: utf-8
"""Service worker is the original supervisor worker, not a second factory."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from autofab import engine,service_worker,supervisor
from autofab.storage import load,verify_journal


class ServiceWorkerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="af-r049-service-")
        self.addCleanup(t.cleanup)
        self.root=engine.init(Path(t.name))
        supervisor.directory(self.root)

    def test_original_worker_exits_and_stops_without_duplicate(self):
        def original(root):
            self.assertEqual(supervisor.status(root)["control"]["command"],"RUN")
            self.assertEqual(root,self.root)
            return {"status":"ORIGINAL_WORKER_STOPPED_FIXTURE"}
        with patch.object(service_worker.supervisor,"worker",side_effect=original) as worker:
            result=service_worker.begin(self.root)
        worker.assert_called_once_with(self.root)
        self.assertEqual(result["status"],"ORIGINAL_WORKER_STOPPED_FIXTURE")
        self.assertEqual(supervisor.status(self.root)["control"]["command"],"STOP")
        verify_journal(self.root/"supervisor/journal.jsonl")

    def test_original_worker_exception_stops_fail_closed(self):
        with patch.object(service_worker.supervisor,"worker",side_effect=RuntimeError("SIMULATED_ABNORMAL_EXIT")):
            with self.assertRaisesRegex(RuntimeError,"ABNORMAL_EXIT"):
                service_worker.begin(self.root)
        self.assertEqual(supervisor.status(self.root)["control"]["command"],"STOP")

    def test_cannot_start_original_service_when_original_running(self):
        with patch.object(service_worker.supervisor,"status",return_value={
             "status":"RUNNING","control":{"command":"RUN"},
             "pendingQueue":0,"lease":{"status":"RUNNING"}}),\
             patch.object(service_worker.supervisor,"worker") as worker:
            with self.assertRaisesRegex(RuntimeError,"NOT_STOPPED"):
                service_worker.begin(self.root)
        worker.assert_not_called()

    def test_original_preexisting_run_control_rejected(self):
        p=supervisor.directory(self.root)
        supervisor._control(p,"RUN")
        with patch.object(service_worker.supervisor,"worker") as worker:
            with self.assertRaisesRegex(RuntimeError,"STOP_PREIMAGE"):
                service_worker.begin(self.root)
        worker.assert_not_called()
        supervisor._control(p,"STOP")

    def test_existing_pending_original_jobs_cannot_be_consumed_implicitly(self):
        with patch.object(service_worker.supervisor,"status",return_value={
             "status":"STOPPED","control":{"command":"STOP"},
             "pendingQueue":1,"lease":None}),\
             patch.object(service_worker.supervisor,"worker") as worker:
            with self.assertRaisesRegex(RuntimeError,"PENDING_QUEUE"):
                service_worker.begin(self.root)
        worker.assert_not_called()

    def test_unknown_prior_lease_never_started(self):
        with patch.object(service_worker.supervisor,"status",return_value={
             "status":"STOPPED","control":{"command":"STOP"},
             "pendingQueue":0,"lease":{"status":"UNKNOWN"}}),\
             patch.object(service_worker.supervisor,"worker") as worker:
            with self.assertRaisesRegex(RuntimeError,"LEASE_NOT_STOPPED"):
                service_worker.begin(self.root)
        worker.assert_not_called()


if __name__=="__main__":unittest.main()
