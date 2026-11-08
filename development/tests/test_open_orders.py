# coding: utf-8
"""Open-language work orders are owner-pinned, idempotent and delegated once."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autofab import open_orders

class OpenOrdersTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-open-orders-")
        self.root=Path(self.tmp.name)
        (self.root/"ENTRADAS").mkdir()
        self.test=self.root/"ENTRADAS"/"encargo.json"
    def tearDown(self):
        self.tmp.cleanup()
    def make(self,owner=True):
        data={"schema":1,"language":"javascript",
              "goal":"Quiero un programa que calcule el triple de un importe local sin redes.",
              "exportName":"tripleUserTotal",
              "acceptance":[{"args":[x],"expected":x*3} for x in (0,1,2,3,4,10,-2)] if owner else []}
        self.test.write_text(json.dumps(data),encoding="utf-8")
        return data
    def test_ownerless_request_fails_closed_without_gpu(self):
        self.make(False)
        preview=open_orders.preview(self.root,self.test)
        self.assertEqual(preview["status"],"BLOCKED_OWNER_ACCEPTANCE_REQUIRED")
        with patch.object(open_orders.engine,"init",return_value=self.root),\
             patch.object(open_orders.factory_pipeline,"submit") as original:
            result=open_orders.submit(self.root,self.test)
            original.assert_not_called()
        self.assertEqual(result["status"],"BLOCKED_OWNER_ACCEPTANCE_REQUIRED")
    def test_arbitrary_goal_not_catalog_phrase(self):
        data=self.make(True)
        preview=open_orders.preview(self.root,self.test)
        self.assertEqual(preview["status"],"FROZEN_OWNER_INPUT_READY")
        self.assertEqual(preview["originalOwnerCases"],len(data["acceptance"]))
        self.assertNotIn("ownerSpec",preview)
        self.assertTrue(preview["ownerSpecSha"])
    def test_original_factory_called_once_and_idempotent(self):
        self.make(True)
        fake={"status":"SUPERVISOR_RUNNING_VERIFIED",
              "workflowId":"FC-"+"a"*16}
        with patch.object(open_orders.engine,"init",return_value=self.root),\
             patch.object(open_orders.repo_graph,"preflight",return_value={}),\
             patch.object(open_orders.factory_pipeline,"submit",return_value=fake) as runner,\
             patch.object(open_orders.factory_pipeline,"reconcile",return_value={"status":"PENDING"}):
            first=open_orders.submit(self.root,self.test,provider="cuda7b")
            again=open_orders.submit(self.root,self.test,provider="cuda7b")
            self.assertEqual(runner.call_count,1)
        self.assertEqual(first["status"],"SUBMITTED_ONCE_TO_ORIGINAL_LOCAL_SUPERVISOR")
        self.assertEqual(again["status"],"ORIGINAL_FACTORY_PENDING")
        self.assertEqual(first["jobId"],again["jobId"])
        frozen=self.root/"workorders"/first["jobId"]/"intent.json"
        self.assertTrue(frozen.exists())
        self.assertEqual(len(list((self.root/"examples").glob("*.json"))),1)
    def test_rejects_foreign_paths_and_unsafe_function(self):
        self.make(True)
        self.assertRaises(ValueError,open_orders.preview,self.root,
                          self.root/"outside.json")
        data=json.loads(self.test.read_text())
        data["exportName"]="danger;exit"
        self.test.write_text(json.dumps(data),encoding="utf-8")
        with self.assertRaises(ValueError):
            open_orders.preview(self.root,self.test)
    def test_immutability_sha_drift_blocks_readback(self):
        self.make(True)
        with patch.object(open_orders.engine,"init",return_value=self.root),\
             patch.object(open_orders.repo_graph,"preflight",return_value={}),\
             patch.object(open_orders.factory_pipeline,"submit",
                               return_value={"workflowId":"FC-"+"b"*16}):
            row=open_orders.submit(self.root,self.test)
        self.test.write_text(self.test.read_text()+"  ",encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"DRIFT"):
            open_orders.status(self.root,row["jobId"])

if __name__=="__main__":unittest.main()
