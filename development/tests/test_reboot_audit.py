# coding: utf-8
"""No reboot claimed without new original OS boot + live task/process proof."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autofab import reboot_audit as r

class RebootEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-reboot-boundary-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.folder=self.root/"CONTINUIDAD/REINICIO-SESSION-20261108"
        self.folder.mkdir(parents=True)
        self.original={"schema":1,"operationId":"AF.WIN.LOGON-REBOOT-CERTIFICATION-20261108",
           "bootUtc":"2026-11-01T00:00:00+00:00","hostname":"LASTER",
           "originalWorkerProcessBorn":9999,"originalWorkerPid":19,
           "immutableSUCCEEDEDQueues":{}}
        (self.folder/"BASELINE.json").write_text(json.dumps(self.original))
        self.engine=patch.object(r.engine,"init",return_value=self.root)
        self.engine.start()
    def tearDown(self):
        self.engine.stop()
    def test_same_os_boot_is_never_success(self):
        with patch.object(r,"_os",return_value={"bootUtc":self.original["bootUtc"],"hostname":"LASTER"}),\
             patch.object(r,"_task") as task:
            result=r.verify(self.root)
            task.assert_not_called()
        self.assertEqual(result["status"],"PENDING_REAL_WINDOWS_REBOOT_NOT_PERFORMED")
        self.assertFalse(result["physicalRebootVerified"])
        self.assertFalse((self.folder/"REBOOT-VERIFIED-READBACK.json").exists())
    def test_new_boot_but_task_not_running_is_failure(self):
        with patch.object(r,"_os",return_value={"bootUtc":"2026-11-08T00:00:00+00:00","hostname":"LASTER"}),\
             patch.object(r,"_task",return_value={"name":r.TASK,"state":"Ready","runLevel":"Limited"}),\
             patch.object(r.supervisor,"status",return_value={"status":"STOPPED","processIdentityBirthVerified":False}):
            result=r.verify(self.root)
        self.assertEqual(result["status"],"FAILED_REBOOT_ORIGINAL_TASK_OR_WORKER_NOT_RUNNING")
        self.assertFalse((self.folder/"REBOOT-VERIFIED-READBACK.json").exists())
    def test_task_did_not_run_after_boot_stays_failed(self):
        task={"name":r.TASK,"state":"Running","runLevel":"Limited",
              "lastRunUtc":"2026-11-07T23:00:00+00:00"}
        worker={"status":"RUNNING","processIdentityBirthVerified":True,"pendingQueue":0,
                "control":{"command":"RUN"}}
        with patch.object(r,"_os",return_value={"bootUtc":"2026-11-08T00:00:00+00:00","hostname":"LASTER"}),\
             patch.object(r,"_task",return_value=task),\
             patch.object(r.supervisor,"status",return_value=worker):
            result=r.verify(self.root)
        self.assertEqual(result["status"],"FAILED_NO_ORIGINAL_TASK_LAUNCH_AFTER_REBOOT")
    def test_wrong_host_is_error(self):
        with patch.object(r,"_os",return_value={"bootUtc":"2026-11-09T00:00:00+00:00","hostname":"IMPOSTOR"}):
            with self.assertRaisesRegex(RuntimeError,"WRONG_HOST"):
                r.verify(self.root)
    def test_windows_filetime_conversion_works(self):
        birth=134385967099462879
        t=r._filetime_to_datetime(birth)
        self.assertEqual(t.year,2026)
        with self.assertRaises(ValueError):
            r._filetime_to_datetime(-1)
    def test_no_baseline_cannot_claim_after_reboot(self):
        (self.folder/"BASELINE.json").unlink()
        self.assertEqual(r.verify(self.root)["status"],"NO_BASELINE_NO_REBOOT_PROOF")

if __name__=="__main__":unittest.main()
