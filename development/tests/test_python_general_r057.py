"""R057 independent Python original-owner contracts; no model calls in tests."""
from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import python_general
from autofab.storage import sha_file,write_json
class PythonGeneralR057(unittest.TestCase):
    def test_first_party_original_owner_specs_source_portable(self):
        root=Path(__file__).resolve().parents[1]
        items=[
         ("unique_positive_v1",12,"unique_positive_ints"),
         ("merge_intervals_v1",14,"merge_intervals")]
        for name,count,fun in items:
            with self.subTest(task=name):
                spec,pins=python_general._spec(root,
                  root/"examples"/("python_general_"+name+"_r057.json"))
                self.assertEqual(spec["function"],fun)
                self.assertEqual(pins["expectedCases"],count)
                self.assertEqual(sha_file(root/spec["owner"]),pins["ownerSha"])
    def test_goal_only_v2_keeps_exact_owner_identity(self):
        root=Path(__file__).resolve().parents[1]
        for name in ("unique_positive_v1","merge_intervals_v1"):
            old=root/"examples"/("python_general_"+name+"_r057.json")
            new=root/"examples"/("python_general_"+name+"_goal_only_r057.json")
            a,pa=python_general._spec(root,old)
            b,pb=python_general._spec(root,new)
            self.assertEqual(pa["ownerSha"],pb["ownerSha"])
            self.assertNotEqual(pa["specSha"],pb["specSha"])
            self.assertTrue(b["goal"].startswith("R057_GOAL_ONLY_V2:"))
    def test_valid_model_function_parsed(self):
        sample="def unique_positive_ints(values):\n    return sorted(set(values))"
        self.assertEqual(python_general._parse(json.dumps({"source":sample}),
                           "unique_positive_ints"),sample)
    def test_doubly_escaped_newline_decoded_exactly_one_layer(self):
        original="def unique_positive_ints(values):\\n    return sorted(set(values))"
        repaired=python_general._parse(json.dumps({"source":original}),
                                        "unique_positive_ints")
        self.assertIn("\n    return ",repaired)
        self.assertNotIn("\\n",repaired)
    def test_model_wrong_key_or_name_refused(self):
        good="def unique_positive_ints(values):\n    return []"
        bad=[json.dumps({"file":good}),
             json.dumps({"source":good,"tests":"changed"}),
             json.dumps({"source":"def other(value):\n    return []"}),
             json.dumps({"source":"pass"}),
             json.dumps({"source":"def unique_positive_ints():\n    return []"}),
             json.dumps({"source":"def unique_positive_ints(x,y):\n    return []"})]
        for source in bad:
            with self.subTest(source=source),self.assertRaises((ValueError,SyntaxError)):
                python_general._parse(source,"unique_positive_ints")
    def test_unrecognized_task_and_path_denied(self):
        with tempfile.TemporaryDirectory(prefix="R057-OWNER-") as t:
            root=Path(t);(root/"examples").mkdir()
            p=root/"examples/task.json"
            write_json(p,{"schema":1,"taskId":"arbitrary","language":"python"},new=True)
            with self.assertRaises(ValueError):
                python_general._spec(root,p)
            with self.assertRaises(ValueError):
                python_general._spec(root,root/"elsewhere.json")
    def test_original_request_one_shot_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="R057-NOREPLAY-") as t:
            root=Path(t);id_="PG-0123456789abcdef"
            job=root/"pygeneral"/id_;job.mkdir(parents=True)
            write_json(job/"plan.json",{"taskId":"no-effect"},new=True)
            write_json(job/"state.json",{"status":"MODEL_PENDING"},new=True)
            write_json(job/"request.json",{"original":True},new=True)
            with patch.object(python_general.engine,"init",return_value=root):
                with patch.object(python_general.local_runtime,"start",
                                  side_effect=AssertionError("MODEL_NO_REPLAY")):
                    with self.assertRaisesRegex(RuntimeError,"NO_REPLAY"):
                        python_general.run(root,id_)
    def test_no_privilege_or_host_execution_states(self):
        self.assertNotIn("PASS_HOST_EXECUTION",python_general.TERMINAL)
        self.assertIn("PASS_ORIGINAL_PURE_MODEL_OWNER_WASI",python_general.TERMINAL)
        self.assertTrue(python_general._ID.fullmatch("PG-0123456789abcdef"))
        self.assertFalse(python_general._ID.fullmatch("PG-../../malicious"))
