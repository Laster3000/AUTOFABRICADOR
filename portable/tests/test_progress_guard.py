import tempfile
from pathlib import Path
import unittest
from autofab.progress_guard import semantic_source, candidate_fingerprint, repeated_failed_candidate
from autofab.storage import write_json

class ProgressGuardTests(unittest.TestCase):
    def test_ignores_irrelevant_comments_and_spaces(self):
        a="def f(x):\n    return x+1\n"
        b="def f(x): # note\n    return x + 1\n"
        self.assertEqual(semantic_source(a),semantic_source(b))

    def test_preserves_semantic_indentation(self):
        a="def f(x):\n    if x:\n        return 1\n    return 2\n"
        b="def f(x):\n    if x:\n        return 1\n        return 2\n"
        self.assertNotEqual(semantic_source(a),semantic_source(b))

    def test_preserves_string_literals(self):
        self.assertNotEqual(semantic_source("x='hello'"),semantic_source("x='world'"))

    def test_same_failed_code_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp)
            old=job/"attempt-01";old.mkdir()
            write_json(old/"model.json",{"payload":{"files":{"mod.py":"def f():\n    return 1\n",
                                "test_mod.py":"import unittest\n"}}})
            write_json(old/"test.json",{"exitCode":-7,"testCount":3,"reason":"TEST_FAILED"})
            found=repeated_failed_candidate(job,{"files":{"mod.py":"def f():  # comment\n    return 1\n",
                                "test_mod.py":"import unittest\n"}})
            self.assertEqual(found["attempt"],"attempt-01")

    def test_unknown_does_not_count_as_deterministic_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp)
            old=job/"attempt-01";old.mkdir()
            payload={"files":{"mod.py":"def f(): return 1\n","test_mod.py":"import unittest\n"}}
            write_json(old/"model.json",{"payload":payload})
            write_json(old/"test.json",{"exitCode":-7,"testCount":0,"reason":"INFRASTRUCTURE_UNKNOWN"})
            self.assertIsNone(repeated_failed_candidate(job,payload))

if __name__=="__main__":
    unittest.main()


class IntegrationGuardTests(unittest.TestCase):
    def test_local_draft_stagnates_on_equivalent_failed_source(self):
        from unittest.mock import patch
        from autofab import draft, engine
        from autofab.storage import load, write_json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            engine.init(root)
            config=load(root/"settings.json")
            config.update(provider="ollama",model="test-model",max_attempts=2)
            write_json(root/"settings.json",config)
            spec=root/"spec.json"
            write_json(spec,{"goal":"make function","language":"python",
                             "test_command":["python","-m","unittest","discover","-v"]})
            job=engine.create(root,spec)
            folder=root/"work"/job
            original={"files":{"module.py":"def f():\n    return 99\n",
                               "test_module.py":"import unittest\nclass Trial(unittest.TestCase):\n    def test_bad(self): self.assertEqual(1,2)\n"}}
            prior=folder/"attempt-01"
            prior.mkdir()
            write_json(prior/"model.json",{"payload":original,
                                           "usage":{"provider":"ollama"},"modelDigest":"sha256:testing"})
            write_json(prior/"test.json",{"exitCode":-7,"testCount":1,
                                         "reason":"MODEL_TEST_FAILURE"})
            engine.set_state(folder,"FAILED_ATTEMPT",1,"model repair")
            repeated={"files":{"module.py":"def f(): # same result\n    return 99\n",
                               "test_module.py":original["files"]["test_module.py"]}}
            mock_model=__import__("unittest.mock",fromlist=["Mock"]).Mock()
            mock_model.available_model.return_value={"digest":"sha256:testing"}
            mock_model.generate.return_value=(repeated,{"provider":"ollama","promptTokens":10,
                                                          "completionTokens":15,"elapsedMs":25})
            with patch("autofab.draft.provider_for",return_value=mock_model):
                result=draft.draft(root,job)
            self.assertEqual(result["state"]["status"],"STAGNATED")
            self.assertTrue((folder/"attempt-02"/"STAGNATION-RECEIPT.json").is_file())
            self.assertEqual(mock_model.generate.call_count,1)
            self.assertFalse((folder/"attempt-02"/"code").exists())

