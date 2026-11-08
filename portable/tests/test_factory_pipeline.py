# coding: utf-8
"""Single original owner request -> model -> WASI -> native, no blind replay.

Only mocks in these boundary tests; real OS VM must be independently observed.
"""
from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

from autofab import engine, factory_pipeline as f, native_cycle, supervisor
from autofab.storage import load,write_json,verify_journal,sha_file


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-r046-pipeline-")
        self.addCleanup(self.tmp.cleanup)
        self.root=engine.init(Path(self.tmp.name))
        (self.root/"autofabricador.py").write_text("first-party fixture",encoding="utf-8")
        self.spec=self.root/"examples"/"single_intent.json"
        self.spec.parent.mkdir(parents=True,exist_ok=True)
        self.spec.write_text(json.dumps({
            "schema":1,"language":"javascript","dependencies":[],
            "entry":"src/index.js","exportName":"add",
            "goal":"Implement simple add(a,b) in ESM","sources":{"src/index.js":"export function add(a,b){return 0;}"},
            "acceptance":[{"args":[i,i],"expected":2*i} for i in range(5)]
        }),encoding="utf-8")

    def _create(self):
        with patch.object(f.repo_graph,"preflight",return_value={"status":"READY"}),\
             patch.object(f.repo_graph,"_valid_spec",return_value=None):
            return f.create(self.root,self.spec)

    def test_one_owner_spec_one_intent_and_no_alias(self):
        a=self._create()
        b=self._create()
        self.assertEqual(a["status"],"PENDING")
        self.assertEqual(b["status"],"EXISTING_INTENT_NO_DUPLICATE")
        self.assertEqual(a["workflowId"],b["workflowId"])
        self.assertEqual(f.status(self.root,a["workflowId"])["status"],"PENDING")
        verify_journal(f.folder(self.root,a["workflowId"])/"journal.jsonl")

    def test_rejects_foreign_owner_spec_paths_and_invalid_ids(self):
        with self.assertRaisesRegex(ValueError,"WORKFLOW_ID_INVALID"):
            f.status(self.root,"FC-../../bad")
        with tempfile.TemporaryDirectory() as foreign:
            p=Path(foreign)/"owner.json"
            p.write_bytes(self.spec.read_bytes())
            with self.assertRaisesRegex(ValueError,"MUST_BE_PROJECT_EXAMPLES"):
                f.create(self.root,p)

    def test_stop_before_any_original_model_intent(self):
        uid=self._create()["workflowId"]
        self.assertEqual(f.stop(self.root,uid)["status"],
                         "STOP_REQUESTED_FIRST_SAFE_BOUNDARY")
        with patch.object(f.repo_factory,"create") as create:
            result=f.run(self.root,uid)
            create.assert_not_called()
        self.assertEqual(result["status"],"STOPPED_PRE_INTENT")
        self.assertEqual(f.status(self.root,uid)["status"],"STOPPED_PRE_INTENT")
        with self.assertRaisesRegex(RuntimeError,"NO_REPLAY"):
            f.run(self.root,uid)

    def test_model_failure_never_enters_native_vm(self):
        uid=self._create()["workflowId"]
        repo="RJ-0011223344556677"
        rp=self.root/"repojobs"/repo
        rp.mkdir(parents=True)
        write_json(rp/"spec.json",load(self.spec),new=True)
        with patch.object(f.repo_factory,"create",
                          return_value={"status":"PENDING","jobId":repo}),\
             patch.object(f.repo_factory,"run",
                          return_value={"status":"FAILED_OWNER_ACCEPTANCE"}),\
             patch.object(f.repo_factory,"status",
                          return_value={"status":"FAILED_OWNER_ACCEPTANCE"}),\
             patch.object(f.native_cycle,"create") as native:
            r=f.run(self.root,uid)
            native.assert_not_called()
        self.assertEqual(r["status"],"FAILED_REPO")
        self.assertEqual(f.status(self.root,uid)["repoJob"],repo)

    def test_full_chain_mock_correlates_original_wasi_and_guest(self):
        uid=self._create()["workflowId"]
        repo="RJ-0011223344556677"
        cycle="NC-0011223344556677"
        rp=self.root/"repojobs"/repo
        rp.mkdir(parents=True)
        write_json(rp/"spec.json",load(self.spec),new=True)
        write_json(rp/"manifest.json",{"modelSha":"a"*64},new=True)
        native=self.root/"nativecycles"/cycle
        native.mkdir(parents=True)
        write_json(native/"intent.json",{"schema":1},new=True)
        write_json(native/"result.json",{
           "sourceRepo":repo,"ownerCases":5,
           "nativeCryptographicOwnerAcceptance":False,
           "sandboxJob":"SX-0011223344556677",
           "sandboxOriginalGuestReportSha":"b"*64,
           "vmCleanup":{"closed":True}
        },new=True)
        owner={"verified":True,"status":"PASS","ownerCases":5,"modelAttempts":1}
        with patch.object(f.repo_factory,"create",
                return_value={"status":"PENDING","jobId":repo}),\
             patch.object(f.repo_factory,"run",
                return_value={"status":"PASS"}),\
             patch.object(f.repo_factory,"status",return_value={"status":"PASS"}),\
             patch.object(f.repo_factory,"verify",return_value=owner),\
             patch.object(f.native_cycle,"create",
                return_value={"status":"PENDING","cycleId":cycle}),\
             patch.object(f.native_cycle,"run",
                return_value={"status":f.native_cycle.OK}),\
             patch.object(f.native_cycle,"reconcile",
                return_value={"status":f.native_cycle.OK,
                              "originalResultStatus":f.native_cycle.OK}):
            r=f.run(self.root,uid)
        self.assertEqual(r["status"],f.SUCCESS)
        self.assertTrue(r["originalOwnerWasiAccepted"])
        self.assertEqual(r["originalOwnerCases"],5)
        self.assertFalse(r["nativeGuestCryptographicOwnerAcceptance"])
        self.assertTrue(r["nativeGuestOutputUntrusted"])
        self.assertTrue(r["sandboxGuestSessionClosed"])
        self.assertEqual(f.status(self.root,uid)["status"],f.SUCCESS)
        verify_journal(f.folder(self.root,uid)/"journal.jsonl")
        with self.assertRaisesRegex(RuntimeError,"NO_REPLAY"):
            f.run(self.root,uid)

    def test_supervisor_accepts_only_original_pending_pipeline_and_no_editor(self):
        uid=self._create()["workflowId"]
        q=supervisor.enqueue(self.root,"factory",uid)
        self.assertEqual(q["status"],"PENDING")
        same=supervisor.enqueue(self.root,"factory",uid)
        self.assertEqual(same["queueId"],q["queueId"])
        with self.assertRaisesRegex(ValueError,"FACTORY_NO_NATIVE_EDITOR"):
            supervisor.enqueue(self.root,"factory",uid,editor="codex")
        f.stop(self.root,uid)
        with self.assertRaisesRegex(RuntimeError,"FACTORY_SUPERVISOR_REQUIRES_PENDING"):
            supervisor.enqueue(self.root,"factory",uid)

    def test_submit_reuses_original_supervisor_never_queues_duplicate(self):
        with patch.object(f,"create",
            side_effect=[{"status":"PENDING","workflowId":"FC-0011223344556677"},
                         {"status":"EXISTING_INTENT_NO_DUPLICATE",
                          "workflowId":"FC-0011223344556677"}]),\
             patch.object(supervisor,"enqueue",
                return_value={"queueId":"SQ-0011223344556677","status":"PENDING"}) as enqueue,\
             patch.object(supervisor,"start",return_value={"status":"RUNNING_VERIFIED"}) as start:
            a=f.submit(self.root,self.spec)
            b=f.submit(self.root,self.spec)
        self.assertEqual(a["status"],"SUPERVISOR_RUNNING_VERIFIED")
        self.assertEqual(b["status"],"EXISTING_INTENT_NO_DUPLICATE")
        self.assertEqual(enqueue.call_count,1)
        self.assertEqual(start.call_count,1)


if __name__=="__main__":
    unittest.main()
