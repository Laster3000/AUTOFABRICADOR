"""Lifecycle and integrity tests without starting external model services."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autofab import engine, operate
from autofab.storage import load, write_json

class ManagedLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        engine.init(self.root)
        cfg=load(self.root/"settings.json")
        cfg["provider"]="llama_cpp"
        write_json(self.root/"settings.json",cfg)
        spec=self.root/"spec.json"
        write_json(spec,{"goal":"small test","language":"python",
                         "test_command":["python","-m","unittest","discover","-v"]})
        self.job=engine.create(self.root,spec)

    def test_start_stop_only_owned_new_model(self):
        with patch("autofab.operate.local_runtime.server_info",return_value={"state":"NOT_STARTED"}), \
             patch("autofab.operate.local_runtime.start",return_value={"state":"READY"}) as start, \
             patch("autofab.operate.local_runtime.stop",return_value={"state":"STOPPED"}) as stop, \
             patch("autofab.operate.draft.draft",return_value={"status":"mocked_draft"}):
            result=operate.run_job(self.root,self.job)
        self.assertEqual(result["status"],"mocked_draft")
        start.assert_called_once()
        stop.assert_called_once()

    def test_preexisting_model_not_stopped(self):
        with patch("autofab.operate.local_runtime.server_info",return_value={"state":"READY"}), \
             patch("autofab.operate.local_runtime.start") as start, \
             patch("autofab.operate.local_runtime.stop") as stop, \
             patch("autofab.operate.draft.draft",return_value={"status":"mocked_draft"}):
            self.assertEqual(operate.run_job(self.root,self.job)["status"],"mocked_draft")
        start.assert_not_called()
        stop.assert_not_called()

    def test_unknown_never_automatically_replayed(self):
        engine.set_state(self.root/"work"/self.job,"UNKNOWN",1,"manual reconciliation")
        with patch("autofab.operate.local_runtime.start") as start:
            with self.assertRaisesRegex(RuntimeError,"RECONCILE_DO_NOT_REPLAY"):
                operate.run_job(self.root,self.job)
        start.assert_not_called()

    def test_prepared_draft_does_not_start_model(self):
        engine.set_state(self.root/"work"/self.job,"DRAFT_READY_UNTESTED",1,"test")
        with patch("autofab.operate.local_runtime.start") as start, \
             patch("autofab.operate.engine.run",return_value={"status":"PASS"}) as verify:
            out=operate.run_job(self.root,self.job)
        self.assertEqual(out["status"],"PASS")
        verify.assert_called_once()
        start.assert_not_called()

    def test_manifest_mutation_is_detected(self):
        cfg=load(self.root/"settings.json")
        cfg["provider"]="fixture"
        write_json(self.root/"settings.json",cfg)
        engine.run(self.root,self.job)
        path=self.root/"work"/self.job/"manifest.json"
        manifest=load(path)
        manifest["attempt"]=999
        write_json(path,manifest)
        with self.assertRaisesRegex(RuntimeError,"MANIFEST_STATE_SHA_DRIFT"):
            engine.verify_job(self.root,self.job)

if __name__=="__main__":
    unittest.main()


class AutoHousekeepingSmoke(unittest.TestCase):
    def test_run_auto_cleans_only_disposable_bytecode(self):
        import tempfile
        from pathlib import Path
        from autofab import engine, operate
        from autofab.storage import load,write_json
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            engine.init(root)
            cfg=load(root/"settings.json")
            cfg["provider"]="fixture"
            write_json(root/"settings.json",cfg)
            spec=root/"spec.json"
            write_json(spec,{"goal":"a function","language":"python",
                             "test_command":["python","-m","unittest","discover","-v"]})
            job=engine.create(root,spec)
            bytecode=root/"autofab"/"__pycache__"
            bytecode.mkdir(parents=True)
            disposable=bytecode/"generated.pyc"
            disposable.write_bytes(b"example")
            receipt=operate.run_job(root,job)
            self.assertEqual(receipt["state"]["status"],"PASS_FIXTURE")
            self.assertFalse(disposable.exists())
            self.assertEqual(receipt["housekeeping"]["status"],"PASS")
            self.assertTrue((root/"work"/job/"manifest.json").exists())
