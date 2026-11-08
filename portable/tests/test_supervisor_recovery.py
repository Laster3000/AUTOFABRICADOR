"""Supervisor durable safe resume and dead-worker reconciliation; no blind replay."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from autofab import engine,supervisor
from autofab.storage import load,write_json,sha_file
class SupervisorRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        engine.init(self.root)
        (self.root/"autofabricador.py").write_text("# fixture cli\n",encoding="utf-8")
    def test_resume_same_queue_id_only_after_safe_no_effect_stop(self):
        info=supervisor.enqueue(self.root,"selfcheck")
        p=supervisor.directory(self.root)
        file=p/"queue"/(info["queueId"]+".json")
        supervisor._task_update(p,file,{"status":"STOPPED","result":"SAFE_CANCEL_NO_SIDE_EFFECT","modelCalls":0})
        original_sha=sha_file(file)
        answer=supervisor.resume_task(self.root,info["queueId"])
        self.assertEqual(answer["status"],"PENDING_SAME_ID_PROVEN_NO_REPLAY")
        self.assertEqual(load(file)["status"],"PENDING")
        self.assertNotEqual(original_sha,sha_file(file))
        with self.assertRaisesRegex(RuntimeError,"ONLY_SAFE_STOPPED"):
            supervisor.resume_task(self.root,info["queueId"])
    def test_stale_worker_lease_without_original_receipt_preserves_unknown(self):
        info=supervisor.enqueue(self.root,"selfcheck")
        p=supervisor.directory(self.root)
        file=p/"queue"/(info["queueId"]+".json")
        supervisor._task_update(p,file,{"status":"RUNNING"})
        write_json(p/"lease.json",{"schema":1,"status":"RUNNING","pid":2147483640,
                                   "processBornFiletime":12345},new=True)
        with patch("autofab.supervisor.process_born",return_value=None):
            result=supervisor.reconcile_stale(self.root)
        self.assertEqual(result["status"],"STOPPED_RECONCILED_NO_NEW_MODEL_CALLS")
        self.assertEqual(load(file)["status"],"UNKNOWN")
        self.assertEqual(load(p/"lease.json")["status"],"STOPPED_RECONCILED")
        with self.assertRaisesRegex(RuntimeError,"ONLY_SAFE_STOPPED"):
            supervisor.resume_task(self.root,info["queueId"])
    def test_no_reconcile_while_real_process_alive(self):
        p=supervisor.directory(self.root)
        write_json(p/"lease.json",{"schema":1,"status":"RUNNING",
                                  "pid":1234,"processBornFiletime":5678},new=True)
        with patch("autofab.supervisor.process_born",return_value=5678):
            with self.assertRaisesRegex(RuntimeError,"ACTIVE_ORIGINAL"):
                supervisor.reconcile_stale(self.root)
if __name__=="__main__":unittest.main()
