"""Persistent supervisor protocol and STOP safety. Full daemon E2E verified separately."""
import os,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from autofab import engine,supervisor
from autofab.storage import load

class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        engine.init(self.root)
        (self.root/"autofabricador.py").write_text("# trusted CLI fixture\n",encoding="utf-8")

    def test_process_identity_filetime(self):
        if os.name=="nt":
            self.assertIsInstance(supervisor.process_born(os.getpid()),int)
            self.assertIsNone(supervisor.process_born(-1))
        else:
            self.assertIsNone(supervisor.process_born(os.getpid()))

    def test_stop_without_runner_writes_durable_control(self):
        result=supervisor.stop(self.root)
        self.assertEqual(result["status"],"STOPPED")
        self.assertEqual(load(self.root/"supervisor/control.json")["command"],"STOP")

    def test_selfcheck_queue_is_exactly_once(self):
        first=supervisor.enqueue(self.root,"selfcheck")
        second=supervisor.enqueue(self.root,"selfcheck")
        self.assertEqual(second["status"],"ALREADY_QUEUED_OR_RECORDED_NO_REPLAY")
        self.assertEqual(first["queueId"],second["queueId"])

    def test_no_user_supplied_shell_commands(self):
        with self.assertRaisesRegex(ValueError,"NOT_SUPPORTED"):
            supervisor.enqueue(self.root,"powershell","command")
        with self.assertRaisesRegex(ValueError,"SELFCHECK_NO_ARGS"):
            supervisor.enqueue(self.root,"selfcheck","../../sensitive.txt")

    def test_stop_during_fixture_marks_cancel_without_model(self):
        p=supervisor.directory(self.root)
        task=supervisor.enqueue(self.root,"selfcheck")
        supervisor._control(p,"RUN")
        # Cancel before first step: cannot mark a fake SUCCEEDED.
        supervisor._control(p,"STOP")
        supervisor._run_one(self.root,p,p/"queue"/(task["queueId"]+".json"))
        self.assertEqual(load(p/"queue"/(task["queueId"]+".json"))["status"],"PENDING")

if __name__=="__main__":
    unittest.main()
