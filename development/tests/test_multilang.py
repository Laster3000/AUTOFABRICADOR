"""Independent JS/TS intake, original model receipts and cost-safe no-replay rules."""
import json,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from autofab import multilang,engine
from autofab.storage import load,write_json

MINIMAL={"language":"javascript","goal":"Produce a complete small JavaScript function increment(value).",
         "sources":{"inc.js":"function increment(value){return value;}\n"},
         "function":"increment",
         "acceptance":[{"args":[n],"expected":n+1} for n in range(6)]}

class LanguageAdmissionTests(unittest.TestCase):
    def test_accepts_valid_owner_pinned_spec(self):
        self.assertTrue(multilang._valid_spec(MINIMAL))

    def test_rejects_missing_tests(self):
        invalid={**MINIMAL,"acceptance":[]}
        with self.assertRaisesRegex(ValueError,"CASE_COUNT"):
            multilang._valid_spec(invalid)

    def test_rejects_path_escape(self):
        invalid={**MINIMAL,"sources":{"../escape.js":"function inc(v){return v+1;}"}}
        with self.assertRaisesRegex(ValueError,"SOURCE_SEEDS"):
            multilang._valid_spec(invalid)

    def test_rejects_command_injection_language(self):
        invalid={**MINIMAL,"language":"csharp"}
        with self.assertRaisesRegex(ValueError,"ONLY_JS_TS"):
            multilang._valid_spec(invalid)

    def test_codex_json_source_no_model_tools(self):
        code="function inc(a){return a+1;}\n"
        row={"type":"item.completed","item":{"type":"agent_message",
             "text":json.dumps({"files":{"inc.js":code}})}}
        data,tokens=multilang._parse("codex",(json.dumps(row)+"\n").encode(),["inc.js"])
        self.assertEqual(data["inc.js"],code)

    def test_rejects_tool_call_in_stdout(self):
        row={"type":"item.completed","item":{"type":"file_change","patch":"bad"}}
        with self.assertRaisesRegex(ValueError,"FORBIDDEN"):
            multilang._parse("codex",json.dumps(row).encode(),["inc.js"])

    def test_no_replay_of_accepted_job(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            engine.init(root)
            (root/"examples").mkdir()
            spec=root/"examples"/"job.json"
            write_json(spec,MINIMAL)
            with patch("autofab.multilang.js_wasi.preflight",return_value={}):
                new=multilang.create(root,spec)
            self.assertEqual(load(root/"langjobs"/new["jobId"]/"state.json")["status"],"PENDING")
            # Running a stopped job cannot call a model when the control is STOP.
            multilang.control(root,new["jobId"],"STOP")
            with patch("autofab.multilang.local_runtime.start") as started:
                result=multilang.run(root,new["jobId"],"codex")
            self.assertEqual(result["state"]["status"],"STOPPED")
            started.assert_not_called()

if __name__=="__main__":
    unittest.main()
