# coding: utf-8
"""Adversarial portable delivery checks: source is never run on Windows Host."""
from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import engine,portable_delivery
from autofab.storage import load,write_json,sha_file


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-r047-delivery-")
        self.addCleanup(self.tmp.cleanup)
        self.root=engine.init(Path(self.tmp.name))
        self.fc="FC-0011223344556677"
        self.repo="RJ-0011223344556677"
        self.work=self.root/"factoryjobs"/self.fc
        self.work.mkdir(parents=True)
        self.model=self.root/"repojobs"/self.repo
        self.model.mkdir(parents=True)
        self.src={"src/index.js":"import {add} from './rules.js'; export function addValues(a,b){return add(a,b);}\n",
                  "src/rules.js":"export function add(a,b){return a+b;}\n"}
        self.spec={"schema":1,"language":"javascript",
                   "goal":"Combine original two numbers with addition",
                   "dependencies":[],"entry":"src/index.js",
                   "exportName":"addValues",
                   "sources":dict(self.src),
                   "acceptance":[{"args":[i,i],"expected":i*2} for i in range(7)]}
        self.bundle=self.model/"bundle.js"
        self.bundle.write_text("var AFProject = {addValues:(a,b)=>a+b};\n")
        self.result={"schema":1,"status":"PASS_SCOPED_WASI_NATIVE_UNTRUSTED",
          "originalRepoJobId":self.repo,"originalOwnerCases":7,
          "originalOwnerWasiAccepted":True,
          "nativeGuestCryptographicOwnerAcceptance":False,
          "sandboxGuestSessionClosed":True,
          "originalNativeCycleReceiptSha":"c"*64}
        write_json(self.work/"result.json",self.result,new=True)
        write_json(self.model/"manifest.json",{"bundleSha":sha_file(self.bundle),
          "originalWasiReceiptSha":"b"*64},new=True)
        self.manifest=load(self.model/"manifest.json")
        self.patch=patch.object(portable_delivery,"_source",
              return_value=(self.root,self.result,self.spec,self.src,
                            self.bundle,self.manifest))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_exports_model_source_and_static_wrapper_no_execution(self):
        with patch("subprocess.run") as run,patch("os.system") as shell:
            result=portable_delivery.deliver(self.root,self.fc)
            run.assert_not_called()
            shell.assert_not_called()
        self.assertEqual(result["status"],"DELIVERED_PORTABLE_SOURCE_CANDIDATE")
        v=portable_delivery.verify(self.root,self.fc)
        self.assertTrue(v["verified"])
        self.assertEqual(v["ownerWasiCases"],7)
        self.assertTrue(v["nativeGuestUntrusted"])
        self.assertTrue(v["browserRuntimeNotOwnerVerified"])
        self.assertIn("PORTABLE.zip",v["archive"])

    def test_existing_delivery_returns_original_no_replay(self):
        original=portable_delivery.deliver(self.root,self.fc)
        same=portable_delivery.deliver(self.root,self.fc)
        self.assertEqual(same["status"],"PREEXISTING_VERIFIED_NO_REPLAY")
        self.assertEqual(same["result"]["archiveSha"],
                         original["result"]["archiveSha"])

    def test_corrupted_zip_is_detected_by_external_readback(self):
        portable_delivery.deliver(self.root,self.fc)
        _,archive=portable_delivery._base(self.root,self.fc)
        archive.write_bytes(archive.read_bytes()+b"BAD")
        with self.assertRaisesRegex(RuntimeError,"MISMATCH"):
            portable_delivery.verify(self.root,self.fc)

    def test_partial_export_is_unknown_and_never_regenerated(self):
        folder,_=portable_delivery._base(self.root,self.fc)
        folder.mkdir(parents=True,exist_ok=False)
        with self.assertRaisesRegex(RuntimeError,"PARTIAL_RECONCILE"):
            portable_delivery.deliver(self.root,self.fc)

    def test_invalid_workflow_path_fails_before_side_effect(self):
        with self.assertRaises(ValueError):
            portable_delivery.deliver(self.root,"FC-../outside")

    def test_manifest_never_claims_browser_owner_acceptance(self):
        portable_delivery.deliver(self.root,self.fc)
        folder,_=portable_delivery._base(self.root,self.fc)
        m=load(folder/"manifest.json")
        self.assertTrue(m["nativeGuestOutputUntrusted"])
        self.assertFalse(m["nativeGuestCryptographicOwnerAcceptance"])
        self.assertFalse(m["browserExecutionClaimed"])
        self.assertTrue(m["noModelCodeExecutedOnHostByExporter"])


if __name__=="__main__":unittest.main()
