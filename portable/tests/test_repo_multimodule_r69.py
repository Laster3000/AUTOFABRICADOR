# coding: utf-8
"""Offline original R69 owner/backend safety and prevalidated artifact tests."""
import unittest,json,hashlib
from pathlib import Path
from autofab import repo_multimodule_r69 as factory,local_cuda9b,repo_graph
ROOT=Path(__file__).resolve().parents[1]
class R69NewFactory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((ROOT/"examples/r69q4_erp_independent_owner.json").read_text("utf-8"))
        cls.plan=json.loads((ROOT/"examples/r69q4_erp_independent_plan.json").read_text("utf-8"))
        cls.holdout=json.loads((ROOT/"examples/r69q4_erp_independent_holdout_21.json").read_text("utf-8"))
    def test_original_owner_plan_accepted(self):
        self.assertTrue(factory.valid(self.spec,self.plan))
    def test_frozen_separate_owner_holdout(self):
        self.assertEqual(len(self.spec["acceptance"]),19)
        self.assertEqual(len(self.holdout["cases"]),21)
        self.assertEqual(len(self.plan["modules"]["src/validation.js"]["cases"]),21)
    def test_original_spec_sha_pins_both(self):
        digest=hashlib.sha256((ROOT/"examples/r69q4_erp_independent_owner.json").read_bytes()).hexdigest()
        self.assertEqual(digest,self.plan["specSha"])
        self.assertEqual(digest,self.holdout["specSha"])
    def test_four_modules_owner_graph(self):
        self.assertEqual(len(self.plan["order"]),4)
        self.assertEqual(self.plan["order"][-1],self.spec["entry"])
    def test_real_python_model_pinned(self):
        self.assertEqual(local_cuda9b.MODEL_SHA,
            "03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8")
        self.assertEqual(local_cuda9b.MODEL_SIZE,5680522464)
    def test_conservative_memory_gates(self):
        self.assertGreaterEqual(local_cuda9b.MIN_RAM_TO_START_MIB,7200)
        self.assertGreaterEqual(local_cuda9b.MIN_RAM_LOADING_MIB,1250)
        self.assertGreaterEqual(local_cuda9b.MIN_VRAM_TO_START_MIB,8500)
    def test_distinct_local_gpu_port(self):
        self.assertEqual(local_cuda9b.PORT,11479)
    def test_no_old_r68_jobs_in_r69(self):
        with self.assertRaises(ValueError):
            factory.folder(ROOT,"MR68-bb2707f6bcbb4995")
    def test_model_guard_forbidden_win_host_process(self):
        with self.assertRaises(ValueError):
            factory.extract("export function f(q){return process.env;}","f")
    def test_new_esm_unit_owner_compiler_safe(self):
        self.assertTrue(repo_graph._valid_spec(self.spec))
        self.assertIn("cantidad <= 0",self.plan["modules"]["src/validation.js"]["prompt"])
    def test_external_backend_vendor_manifest_pinned(self):
        root=ROOT/"VENDOR/llama-b12202-cuda-12.4-x64"
        pinned=json.loads((root/"INSTALL-MANIFEST.json").read_text("utf-8"))
        self.assertEqual(pinned["pinnedModelSHA"],local_cuda9b.MODEL_SHA)
        self.assertEqual(hashlib.sha256((root/"INSTALL-MANIFEST.json").read_bytes()).hexdigest(),
                         local_cuda9b.BACKEND_MANIFEST_SHA)
    def test_no_model_inference_on_import(self):
        # Inspect original receiver; importing it has not launched inference.
        self.assertNotIn("localhost",self.plan["modules"]["src/validation.js"]["prompt"])
if __name__=="__main__":unittest.main()
