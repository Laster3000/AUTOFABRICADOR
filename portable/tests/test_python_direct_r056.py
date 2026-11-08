"""R056 local Python SSE owner tests, zero model calls in unit tests."""
from __future__ import annotations
import json,ast,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import python_direct,local_runtime
from autofab.storage import sha_file,write_json,load
class PythonDirectR056(unittest.TestCase):
    def test_source_requires_exact_one_key(self):
        valid='import re\n\ndef slugify_ascii(value):\n    return re.sub(r"[^a-z0-9]+","-",value.lower()).strip("-")'
        self.assertEqual(python_direct._source(json.dumps({"source":valid})),valid)
        for bad in (json.dumps({"files":{"slugfunc.py":valid}}),
                    json.dumps({"source":valid,"tests":"changed"}),
                    json.dumps({"source":None}),"not json",
                    json.dumps({"source":"def other(x):\n    return x"}),
                    json.dumps({"source":"def slugify_ascii(v):\nreturn v"})):
            with self.subTest(data=bad),self.assertRaises((ValueError,SyntaxError)):
                python_direct._source(bad)
    def test_contract_and_owner_pinned(self):
        source=Path(__file__).resolve().parents[1]
        # Source-only portable proof: no installed legacy work folder needed.
        spec=load(source/"examples/owner_py_direct_r056.json")
        self.assertEqual(sha_file(source/spec["ownerTest"]),spec["ownerSha"])
        self.assertEqual(spec["sourceJob"],"AF-09008dfaecca4045")
        self.assertEqual(len(spec["ownerSha"]),64)
        self.assertEqual(spec["maxTokens"],900)
    def test_invalid_plan_and_path_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/"examples").mkdir()
            p=root/"examples/fake.json"
            write_json(p,{"schema":1,"language":"python","goal":"wrong"},new=True)
            with self.assertRaises(ValueError):
                python_direct._fixed_spec(root,p)
            with self.assertRaises(ValueError):
                python_direct._fixed_spec(root,root/"outside.json")
    def test_repair_not_universal_claim(self):
        self.assertIn("PASS_TRUSTED_HYBRID_WASI",python_direct._STATES)
        self.assertIn("UNKNOWN_OR_TRUNCATED_STREAM_NO_REPLAY",python_direct._STATES)
        self.assertNotIn("PASS_UNIVERSAL_AUTONOMY",python_direct._STATES)
        self.assertTrue(python_direct._ID.fullmatch("PD-0123456789abcdef"))
        self.assertFalse(python_direct._ID.fullmatch("PD-../../escape"))
    def test_model_not_started_for_existing_job(self):
        # All original effects are tracked by a one-shot request.json.
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);job=root/"pythondirect/PD-0123456789abcdef"
            job.mkdir(parents=True)
            write_json(job/"plan.json",{"inputSpec":"original"},new=True)
            write_json(job/"state.json",{"status":"MODEL_PENDING"},new=True)
            (job/"request.json").write_text("{}",encoding="utf-8")
            with patch.object(python_direct.local_runtime,"start",
                side_effect=AssertionError("MODEL MUST NOT START")):
                with self.assertRaisesRegex(RuntimeError,"NO_REPLAY"):
                    python_direct.run(root,job.name)
