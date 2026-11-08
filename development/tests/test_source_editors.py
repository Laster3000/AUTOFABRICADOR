"""Contract tests for native source-only CLI adapters."""
import json
import tempfile
from pathlib import Path
import unittest

from autofab import engine,source_editors
from autofab.storage import load,write_json

class NativeSourceAdapterTests(unittest.TestCase):
    def test_codex_fenced_json_admitted_without_reprompt(self):
        actual={"source":"def f(x):\n    return x + 1\n"}
        text=chr(96)*3+"json\n"+json.dumps(actual)+"\n"+chr(96)*3
        row={"type":"item.completed","item":{"type":"agent_message","text":text}}
        usage={"type":"turn.completed","usage":{"input_tokens":123,"output_tokens":20}}
        code,count=source_editors.parse_source("codex",(json.dumps(row)+"\n"+json.dumps(usage)).encode())
        self.assertEqual(code,actual["source"])
        self.assertEqual(count["input_tokens"],123)

    def test_opencode_json_admitted(self):
        body={"type":"text","part":{"text":json.dumps({"source":"def is_even(v):\n    return v % 2 == 0\n"})}}
        code,_=source_editors.parse_source("opencode",json.dumps(body).encode())
        self.assertIn("return v % 2 == 0",code)

    def test_opencode_fenced_python_admitted(self):
        text=chr(96)*3+"python\n"+"def greeting():\n    return 'hello'\n"+chr(96)*3
        body={"type":"text","part":{"text":text}}
        code,_=source_editors.parse_source("opencode",json.dumps(body).encode())
        self.assertIn("greeting",code)

    def test_shell_events_denied(self):
        row={"type":"item.completed","item":{"type":"command_execution","command":"cmd"}}
        with self.assertRaisesRegex(ValueError,"FORBIDDEN_CODEX_TOOL"):
            source_editors.parse_source("codex",json.dumps(row).encode())

    def test_opencode_tool_events_denied(self):
        with self.assertRaisesRegex(ValueError,"FORBIDDEN_OPENCODE_TOOL"):
            source_editors.parse_source("opencode",b'{"type":"tool-start"}\n')

    def test_no_source_refused(self):
        row={"type":"item.completed","item":{"type":"agent_message","text":"Done."}}
        with self.assertRaisesRegex(ValueError,"INVALID_WHOLE_SOURCE_FORMAT"):
            source_editors.parse_source("codex",json.dumps(row).encode())

    def test_no_functions_refused(self):
        row={"type":"text","part":{"text":json.dumps({"source":"value = 3\n"})}}
        with self.assertRaisesRegex(ValueError,"NO_SOURCE_FUNCTION"):
            source_editors.parse_source("opencode",json.dumps(row).encode())

    def test_pass_original_never_regenerated(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            engine.init(root)
            settings=load(root/"settings.json")
            settings["provider"]="fixture"
            write_json(root/"settings.json",settings)
            spec=root/"spec.json"
            write_json(spec,{"goal":"Create a function","language":"python",
                             "test_command":["python","-m","unittest","discover","-v"]})
            jid=engine.create(root,spec)
            engine.run(root,jid)
            response=source_editors.run(root,"codex",jid,"module.py","examples/anything.py")
            self.assertEqual(response["status"],"ALREADY_PASSED_NO_REPLAY")

if __name__=="__main__":
    unittest.main()
