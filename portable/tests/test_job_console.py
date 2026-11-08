# coding: utf-8
"""No-window tests of GUI data flow and human review boundary."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autofab import job_console as c

def example():
    return {"schema":1,"language":"javascript",
      "goal":"Calcular el importe de cada unidad de pedido sin consultas externas.",
      "exportName":"charge",
      "argTypes":["number","integer"],"maxCases":64,
      "oracle":{"op":"mul","args":[
       {"op":"nonnegative","args":[{"op":"arg","index":0}]},
       {"op":"nonnegative","args":[{"op":"arg","index":1}]}]}}

class LocalJobConsoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-gui-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"ENTRADAS").mkdir()
        self.hook=patch.object(c,"ROOT",self.root)
        self.hook.start()
        self.addCleanup(self.hook.stop)
    def test_owner_goal_idempotent_and_no_overwrite(self):
        first=c.save_goal("Quiero calcular tarifas locales de pedidos en una función independiente.")
        second=c.save_goal("Quiero calcular tarifas locales de pedidos en una función independiente.")
        self.assertEqual(first[0],second[0])
        self.assertTrue(first[2])
        self.assertFalse(second[2])
        self.assertEqual(first[1],second[1])
        self.assertEqual(len(list((self.root/"ENTRADAS").glob("*.txt"))),1)
    def test_input_outside_entradas_cannot_write(self):
        with self.assertRaisesRegex(ValueError,"ENTRADAS"):
            c._stable_file(self.root,"gui_idea_",".txt",b"data")
    def test_review_produces_deterministic_owner_cases_without_model(self):
        obj,raw,n=c.review_contract(json.dumps(example()))
        self.assertEqual(n,64)
        self.assertEqual(json.loads(raw),obj)
        self.assertTrue(obj["oracle"]["op"]=="mul")
        receipt=c.save_owner_contract(json.dumps(example()))
        self.assertTrue(receipt["created"])
        self.assertTrue(receipt["ownerReviewDeclared"])
        self.assertEqual(receipt["cases"],64)
        again=c.save_owner_contract(json.dumps(example()))
        self.assertFalse(again["created"])
        self.assertEqual(receipt["sha"],again["sha"])
    def test_injection_unknown_operator_rejected(self):
        model=example()
        model["oracle"]={"op":"__import__","args":[]}
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED"):
            c.review_contract(json.dumps(model))
    def test_invalid_nonfinite_and_malformed_contract_rejected(self):
        obj=example()
        obj["oracle"]={"op":"const","value":float("nan")}
        with self.assertRaises(ValueError):
            c.review_contract(json.dumps(obj))
        obj=example();obj["modelApproved"]=True
        with self.assertRaisesRegex(ValueError,"KEYS"):
            c.review_contract(json.dumps(obj))
    def test_goal_requires_real_description(self):
        with self.assertRaisesRegex(ValueError,"LENGTH"):
            c.save_goal("hey")
        with self.assertRaisesRegex(ValueError,"LENGTH"):
            c.save_goal("a"*4000)
    def test_preexisting_sha_filename_mismatch_blocks(self):
        file,sha,new=c.save_goal("Crear una función pura para calcular importes de inventario local.")
        file.write_text("tampered",encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"DRIFT"):
            c.save_goal("Crear una función pura para calcular importes de inventario local.")
    def test_model_task_cannot_call_shell(self):
        with self.assertRaisesRegex(ValueError,"ALLOWLISTED"):
            c._call("cmd.exe","whoami")
    def test_model_draft_does_not_count_as_human_review(self):
        # The GUI's review method is pure validation; approval is only the
        # human-confirmation action in the GUI, not an inference result.
        self.assertFalse((self.root/"ENTRADAS"/"gui_reviewed_auto.json").exists())
        self.assertIn("askyesno",c.main.__code__.co_consts[0] if isinstance(c.main.__code__.co_consts[0],str) else
                      __import__("inspect").getsource(c.main))
if __name__=="__main__":unittest.main()
