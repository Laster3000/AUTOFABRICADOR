# coding: utf-8
"""R68 original independent owner contract and safe model parser tests."""
import unittest,json
from pathlib import Path
from autofab import repo_multimodule as r68

ROOT=Path(__file__).resolve().parents[1]
class TestR68(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((ROOT/"examples/r68_erp_multipieza_transaccional_nuevo.json").read_text("utf-8"))
        cls.plan=json.loads((ROOT/"examples/r68_erp_multipieza_plan.json").read_text("utf-8"))
    def test_owner_plan_has_three_modules(self):
        self.assertTrue(r68.valid(self.spec,self.plan))
        self.assertEqual(len(self.plan["order"]),3)
    def test_independent_owner_and_stage_counts(self):
        self.assertEqual(len(self.spec["acceptance"]),19)
        self.assertEqual(len(self.plan["modules"]["src/stock.js"]["cases"]),18)
        self.assertEqual(len(self.plan["modules"]["src/pricing.js"]["cases"]),14)
    def test_stage_wasi_uses_trusted_shim(self):
        code=dict(self.spec["sources"])
        code["src/stock.js"]="export function evaluarStock(q){return q;}\n"
        stage=r68.module_spec(self.spec,"src/stock.js",self.plan["modules"]["src/stock.js"],code)
        self.assertEqual(set(stage["sources"]),{"src/index.js","src/stock.js"})
        self.assertIn("qaOwner",stage["sources"]["src/index.js"])
    def test_no_incomplete_markdown(self):
        fence=chr(96)*3
        with self.assertRaises(ValueError):
            r68.extract(fence+"javascript\nexport function evaluarStock(q){return q;}","evaluarStock")
        with self.assertRaises(ValueError):
            r68.extract("export function evaluarStock(q){throw new Error('PENDIENTE_STOCK')}","evaluarStock")
    def test_complete_fenced_source_allowed(self):
        fence=chr(96)*3
        body=r68.extract(fence+"javascript\nexport function evaluarStock(q){return {error:null};}\n"+fence,"evaluarStock")
        self.assertIn("export function evaluarStock",body)
    def test_export_name_not_replaced(self):
        with self.assertRaises(ValueError):
            r68.extract("export function foo(q) { return q; }","evaluarStock")
    def test_native_process_api_forbidden(self):
        with self.assertRaises(ValueError):
            r68.extract("export function evaluarStock(q) { return process.env; }","evaluarStock")
    def test_entry_last(self):
        self.assertEqual(self.plan["order"][-1],self.spec["entry"])
    def test_job_id_path_no_escape(self):
        with self.assertRaises(ValueError):
            r68.folder(ROOT,"../../supervisor")
if __name__=="__main__":unittest.main()
