"""Native editor adapters: scope, no-tool events, SHA and no duplicate expense."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autofab import advisors,aider_bridge,engine
from autofab.storage import load,write_json,sha_bytes

class AdvisorAdapterTests(unittest.TestCase):
    def test_codex_message_can_be_parsed_without_applying(self):
        response={ "type":"item.completed",
                   "item":{"type":"agent_message","text":chr(96)*3+"json\n"+
                           '{"suggestion":"Change the input validation."}'+"\n"+chr(96)*3}}
        source=(json.dumps(response)+"\n").encode()
        self.assertEqual(advisors.parse("codex",source),"Change the input validation.")

    def test_opencode_message_can_be_parsed(self):
        data={"type":"text","part":{"type":"text","text":'{"suggestion":"Run independent tests."}'}}
        self.assertEqual(advisors.parse("opencode",(json.dumps(data)+"\n").encode()),
                         "Run independent tests.")

    def test_codex_shell_event_rejected(self):
        row={"type":"item.completed","item":{"type":"command_execution","command":"dir"}}
        with self.assertRaisesRegex(RuntimeError,"CODEX_TOOL_EFFECT"):
            advisors.parse("codex",json.dumps(row).encode())

    def test_opencode_tool_event_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"OPENCODE_TOOL_EFFECT"):
            advisors.parse("opencode",b'{"type":"tool_use"}\n')

    def test_invalid_model_response_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"NO_ADVICE_TEXT"):
            advisors.parse("opencode",b"")

    def test_job_pass_never_calls_external_advisor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            engine.init(root)
            cfg=load(root/"settings.json")
            cfg["provider"]="fixture"
            write_json(root/"settings.json",cfg)
            spec=root/"spec.json"
            write_json(spec,{"goal":"Create an operation", "language":"python",
                             "test_command":["python","-m","unittest","discover","-v"]})
            job=engine.create(root,spec)
            engine.run(root,job)
            with patch("autofab.advisors.local_runtime.server_info") as status:
                self.assertEqual(advisors.advise(root,"codex",job)["status"],
                                 "ALREADY_PASSED_DO_NOT_SPEND_TOKENS")
                status.assert_not_called()

    def test_aider_owner_tests_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            engine.init(root)
            spec=root/"spec.json"
            write_json(spec,{"goal":"Edit a module", "language":"python",
                             "test_command":["python","-m","unittest","discover","-v"]})
            job=engine.create(root,spec)
            with self.assertRaisesRegex(RuntimeError,"OWNER_PINNED"):
                aider_bridge.admit(root,job,"sample.py","examples/sample.py")

if __name__=="__main__":
    unittest.main()
