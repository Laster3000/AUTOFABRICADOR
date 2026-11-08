# coding: utf-8
"""Independent declarative owner-oracle intake; no model self-approval."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autofab import owner_oracles as o

def arg(i):return {"op":"arg","index":i}
def const(value):return {"op":"const","value":value}
def expr(op,*args):return {"op":op,"args":list(args)}
def example(oracle=None,types=None):
    return {"schema":1,"language":"javascript",
       "goal":"Calcular importes de almacén localmente y sin consultar servicios externos.",
       "exportName":"computeWarehouseAmount",
       "argTypes":types or ["number","integer","number"],
       "oracle":oracle or expr("clamp",expr("sub",expr("mul",expr("nonnegative",arg(0)),
                 expr("nonnegative",arg(1))),expr("nonnegative",arg(2))),
               const(0),const(100)),"maxCases":64}

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="af-owner-oracle-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"ENTRADAS").mkdir()
        self.path=self.root/"ENTRADAS"/"new_owner.json"
    def make(self,spec=None):
        data=example() if spec is None else spec
        self.path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        return data
    def test_deterministic_no_model_and_broad_domain(self):
        self.make()
        a=o.preview(self.root,self.path)
        b=o.preview(self.root,self.path)
        self.assertEqual(a,b)
        self.assertEqual(a["status"],"OWNER_DECLARATIVE_ORACLE_COMPILED_READ_ONLY")
        self.assertEqual(a["ownerCaseCount"],64)
        self.assertNotIn("derivedBytes",a)
        self.assertTrue(a["ownerAuthoredOracle"])
        self.assertFalse(a["modelGeneratedAcceptance"])
        self.assertFalse((self.root/"workorders").exists())
    def test_metamorphic_reference_examples(self):
        self.make()
        data=o._prepare(self.root,self.path)
        generated=json.loads(data["derivedBytes"])
        self.assertEqual(len(generated["acceptance"]),64)
        for x in generated["acceptance"]:
            p,q,d=x["args"]
            expected=max(0,min(100,max(0,p)*max(0,q)-max(0,d)))
            self.assertEqual(x["expected"],expected)
    def test_text_rules_are_first_party_independent(self):
        spec=example(expr("upper",expr("collapse_space_hyphen",expr("trim",arg(0)))),["text"])
        self.make(spec)
        preview=o.preview(self.root,self.path)
        self.assertEqual(preview["ownerCaseCount"],10)
        result=o._prepare(self.root,self.path)
        d=json.loads(result["derivedBytes"])
        self.assertEqual(d["acceptance"][0]["expected"],"")
        self.assertEqual(d["acceptance"][4]["expected"],"A-B")
    def test_bad_oracle_operator_and_extra_keys_block(self):
        spec=example({"op":"exec","args":[arg(0)]})
        self.make(spec)
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED"):
            o.preview(self.root,self.path)
        spec=example()
        spec["approveMyself"]=True
        self.make(spec)
        with self.assertRaisesRegex(ValueError,"SCHEMA_KEYS"):
            o.preview(self.root,self.path)
    def test_negative_arg_index_must_not_escape(self):
        spec=example(arg(-1))
        self.make(spec)
        with self.assertRaisesRegex(ValueError,"ARG_INDEX"):
            o.preview(self.root,self.path)
    def test_nonfinite_and_huge_numbers_blocked(self):
        spec=example(const(float("inf")))
        self.make(spec)
        with self.assertRaises(ValueError):
            o.preview(self.root,self.path)
        spec=example(const(10**20))
        self.make(spec)
        with self.assertRaisesRegex(ValueError,"DOMAIN"):
            o.preview(self.root,self.path)
    def test_divide_by_zero_fails_closed_before_any_ai(self):
        spec=example(expr("div",arg(0),arg(1)))
        self.make(spec)
        with self.assertRaisesRegex(ValueError,"ZERO"):
            o.preview(self.root,self.path)
    def test_no_bool_as_numeric_and_bad_type(self):
        spec=example(expr("mul",arg(0),arg(1)),["boolean","integer"])
        self.make(spec)
        with self.assertRaisesRegex(ValueError,"NUMERIC_DOMAIN"):
            o.preview(self.root,self.path)
    def test_no_foreign_path_or_symlink(self):
        self.make()
        wrong=self.root/"foreign.json"
        wrong.write_bytes(self.path.read_bytes())
        with self.assertRaisesRegex(ValueError,"ENTRADAS"):
            o.preview(self.root,wrong)
        link=self.root/"ENTRADAS"/"link.json"
        try:link.symlink_to(self.path)
        except (OSError,NotImplementedError):return
        with self.assertRaisesRegex(ValueError,"ENTRADAS"):
            o.preview(self.root,link)
    def test_one_submission_to_original_worker_only(self):
        self.make()
        fake={"status":"SUBMITTED_ONCE_TO_ORIGINAL_LOCAL_SUPERVISOR","jobId":"OJ-fake"}
        with patch.object(o.repo_graph,"preflight",return_value={}),\
             patch.object(o.open_orders,"submit",return_value=fake) as submitted,\
             patch.object(o.open_orders,"status",return_value={"status":"ORIGINAL_FACTORY_PENDING"}):
            result=o.submit(self.root,self.path)
            follow=o.submit(self.root,self.path)
            self.assertEqual(submitted.call_count,1)
        self.assertEqual(result["status"],"SUBMITTED_ONCE_TO_ORIGINAL_SUPERVISOR")
        self.assertIn("CONTRACT_",follow["status"])
        record=json.loads((self.root/"contractorders"/result["contractId"]/"intent.json").read_text())
        self.assertEqual(record["oracleSource"],"OWNER_DECLARATIVE_DSL_NOT_LOCAL_AI")
        self.assertTrue((self.root/"ENTRADAS"/("owner_contract_"+result["contractId"][3:]+".json")).exists())
    def test_missing_submission_never_replayed(self):
        self.make()
        with patch.object(o.repo_graph,"preflight",return_value={}),\
             patch.object(o.open_orders,"submit",side_effect=RuntimeError("ORIGINAL_UNKNOWN")) as sent,\
             patch.object(o.open_orders,"status",return_value={"status":"UNKNOWN"}):
            with self.assertRaisesRegex(RuntimeError,"ORIGINAL_UNKNOWN"):
                o.submit(self.root,self.path)
            result=o.submit(self.root,self.path)
            self.assertEqual(sent.call_count,1)
        self.assertEqual(result["status"],"UNKNOWN_ORIGINAL_SUBMISSION_RECONCILE_NO_REPLAY")
    def test_drift_in_original_owner_blocks_readback(self):
        self.make()
        with patch.object(o.repo_graph,"preflight",return_value={}),\
             patch.object(o.open_orders,"submit",return_value={"jobId":"OJ-X"}):
            answer=o.submit(self.root,self.path)
        self.path.write_text(self.path.read_text()+" ",encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"INPUT_DRIFT"):
            o.status(self.root,answer["contractId"])
    def test_cannot_submit_same_oracle_another_mode(self):
        self.make()
        with patch.object(o.repo_graph,"preflight",return_value={}),\
             patch.object(o.open_orders,"submit",return_value={"jobId":"OJ-X"}) as submit,\
             patch.object(o.open_orders,"status",return_value={"status":"PENDING"}):
            o.submit(self.root,self.path,acceptance_mode="wasi-browser")
            o.submit(self.root,self.path,acceptance_mode="wasi-native")
            self.assertEqual(submit.call_count,1)

if __name__=="__main__":
    unittest.main()
