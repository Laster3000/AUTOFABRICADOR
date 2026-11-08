# coding: utf-8
"""New browser acceptance branch remains original supervisor pipeline, no native VM."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autofab import engine, factory_pipeline as f, repo_export
from autofab.storage import write_json,sha_file,verify_journal

class OriginalFactoryBrowserMode(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-browser-factory-")
        self.addCleanup(self.tmp.cleanup)
        self.root=engine.init(Path(self.tmp.name))
        (self.root/"autofabricador.py").write_text("original-cli-fixture",encoding="utf-8")
        self.spec=self.root/"examples"/"browser_owner.json"
        self.spec.parent.mkdir(parents=True,exist_ok=True)
        self.spec.write_text(json.dumps({
         "schema":1,"language":"javascript","dependencies":[],
         "entry":"src/index.js","exportName":"multiply",
         "goal":"Compute correct pure JavaScript multiplication in original source files.",
         "sources":{"src/index.js":"import {mul} from './rules.js'; export function multiply(a,b){return mul(a,b);}",
                    "src/rules.js":"export function mul(a,b){return a*b;}"},
         "acceptance":[{"args":[i,3],"expected":i*3} for i in range(5)]}),encoding="utf-8")
    def create(self,mode="wasi-browser"):
        with patch.object(f.repo_graph,"preflight",return_value={"status":"READY"}),\
             patch.object(f.repo_graph,"_valid_spec",return_value=True):
            return f.create(self.root,self.spec,provider="cuda7b",acceptance_mode=mode)
    def test_browser_is_pinned_before_inference(self):
        a=self.create()
        original=json.loads((f.folder(self.root,a["workflowId"])/"intent.json").read_text())
        self.assertEqual(original["acceptanceMode"],"wasi-browser")
        self.assertIn("AI-WASI-BROWSER.ONE",original["operationId"])
        self.assertEqual(a["status"],"PENDING")
        self.assertIn(f.SUCCESS_BROWSER,f.TERMINAL)
        self.assertEqual(self.create()["status"],"EXISTING_INTENT_NO_DUPLICATE")
    def test_browser_mode_uses_original_owner_without_native_guest(self):
        wf=self.create()["workflowId"]
        repo="RJ-0011223344556677"
        rp=self.root/"repojobs"/repo
        rp.mkdir(parents=True)
        write_json(rp/"spec.json",json.loads(self.spec.read_text()),new=True)
        write_json(rp/"manifest.json",{"modelSha":"a"*64},new=True)
        store=self.root/"repoexports"
        store.mkdir()
        browser=store/("AF-REPO-"+repo+"-receipts")
        browser.mkdir()
        write_json(browser/"BROWSER-RECEIPT.json",
                   {"status":"PASS","passed":5,"testCount":5,"externalFetchBlocked":True},new=True)
        archive=store/("AF-REPO-"+repo+".zip")
        archive.write_bytes(b"original trusted mock browser zip")
        from autofab import repo_export
        owner={"verified":True,"status":"PASS","ownerCases":5,"modelAttempts":1}
        review={"verified":True,"status":"REPO_BROWSER_WASI_E2E_PASS",
          "ownerWasiCases":5,"browserE2eCases":5,"archiveSha256":sha_file(archive),
          "archive":str(archive)}
        with patch.object(f.repo_factory,"create",
                 return_value={"status":"PENDING","jobId":repo}),\
             patch.object(f.repo_factory,"run",return_value={"status":"PASS"}),\
             patch.object(f.repo_factory,"status",return_value={"status":"PASS"}),\
             patch.object(f.repo_factory,"verify",return_value=owner),\
             patch.object(repo_export,"export",return_value={"status":"REPO_BROWSER_WASI_E2E_PASS"}),\
             patch.object(repo_export,"verify",return_value=review),\
             patch.object(f.native_cycle,"create") as native:
            result=f.run(self.root,wf)
            native.assert_not_called()
            self.assertEqual(result["status"],f.SUCCESS_BROWSER)
            self.assertEqual(result["originalOwnerCases"],5)
            self.assertEqual(result["originalBrowserOwnerCases"],5)
            self.assertEqual(result["deliveryArchiveSha"],sha_file(archive))
            self.assertTrue(result["nativeGuestNotInvoked"])
            self.assertFalse(result["nativeCryptographicOwnerAcceptance"])
            self.assertEqual(f.status(self.root,wf)["status"],f.SUCCESS_BROWSER)
            self.assertTrue(f.reconcile(self.root,wf)["originalBrowserVerified"])
        verify_journal(f.folder(self.root,wf)/"journal.jsonl")
        with self.assertRaisesRegex(RuntimeError,"NO_REPLAY"):
            f.run(self.root,wf)
    def test_bad_mode_rejected_without_intent(self):
        with self.assertRaisesRegex(ValueError,"MODE_NOT_PINNED"):
            self.create("claims-universal-host")
        self.assertFalse((self.root/"factoryjobs").exists())

if __name__=="__main__":
    unittest.main()
