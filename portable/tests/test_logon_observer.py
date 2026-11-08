# coding: utf-8
"""Original worker verifies only a new OS boot, without rerunning old work."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autofab import logon_observer as p

class LogonObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-logon-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.folder=self.root/"CONTINUIDAD/REINICIO-SESSION-20261108"
        self.folder.mkdir(parents=True)
        self.baseline={"schema":1,"hostname":"LASTER","bootUtc":"2026-11-08T06:18:56Z"}
        (self.folder/"BASELINE.json").write_text(json.dumps(self.baseline))
        self.lease={"pid":123,"processBornFiletime":11111,"cliSha256":"1"*64}
    def test_same_os_boot_never_calls_real_verify(self):
        with patch.object(p.reboot_audit,"_os",return_value={"hostname":"LASTER","bootUtc":"2026-11-08T06:18:56Z"}),\
             patch.object(p.reboot_audit,"verify") as verify:
            actual=p.check(self.root,self.lease)
            verify.assert_not_called()
        self.assertEqual(actual["status"],"PENDING_REAL_WINDOWS_REBOOT_NOT_PERFORMED")
    def test_new_os_boot_routes_to_original_verifier(self):
        with patch.object(p.reboot_audit,"_os",return_value={"hostname":"LASTER","bootUtc":"2026-11-09T08:20:00Z"}),\
             patch.object(p.reboot_audit,"verify",return_value={"status":"PASS_REAL_WINDOWS_REBOOT_USER_TASK_AND_ORIGINAL_WORKER"}) as verify,\
             patch.object(p,"_write_outcome",return_value={"status":"PASS_REAL_WINDOWS_REBOOT_USER_TASK_AND_ORIGINAL_WORKER"}) as outcome:
            result=p.check(self.root,self.lease)
            verify.assert_called_once_with(self.root)
            outcome.assert_called_once()
            self.assertIn("PASS_REAL_WINDOWS",result["status"])
    def test_failed_original_verification_stays_failed(self):
        with patch.object(p.reboot_audit,"_os",return_value={"hostname":"LASTER","bootUtc":"2026-11-09T08:20:00Z"}),\
             patch.object(p.reboot_audit,"verify",return_value={"status":"FAILED_REBOOT_ORIGINAL_TASK_OR_WORKER_NOT_RUNNING"}),\
             patch.object(p,"_write_outcome",return_value={"status":"FAILED_REBOOT_ORIGINAL_TASK_OR_WORKER_NOT_RUNNING"}):
            result=p.check(self.root,self.lease)
        self.assertTrue(result["status"].startswith("FAILED"))
    def test_wrong_host_is_blocked(self):
        with patch.object(p.reboot_audit,"_os",return_value={"hostname":"DIFFERENT","bootUtc":"2026-11-09T08:20:00Z"}):
            with self.assertRaisesRegex(RuntimeError,"WRONG_HOST"):
                p.check(self.root,self.lease)
    def test_absent_baseline_does_not_spawn_thread(self):
        (self.folder/"BASELINE.json").unlink()
        with patch.object(p.threading,"Thread") as thread:
            r=p.begin(self.root,self.lease)
            thread.assert_not_called()
        self.assertEqual(r["status"],"NO_REBOOT_BASELINE_NO_THREAD")
    def test_baseline_creates_only_one_daemon_worker_thread(self):
        with patch.object(p.threading,"Thread") as thread:
            a=p.begin(self.root,self.lease)
            thread.assert_called_once()
            self.assertTrue(thread.call_args.kwargs["daemon"])
            thread.return_value.start.assert_called_once()
        self.assertEqual(a["status"],"ORIGINAL_WORKER_ONE_SHOT_REBOOT_PROBE_THREAD_STARTED")

if __name__=="__main__":unittest.main()
