import json
import os
from pathlib import Path
import tempfile
import unittest

from autofab import engine
from autofab.storage import (event, load, safe_source, sha_file, verify_journal,
                             write, write_json)
from autofab.providers import validate_endpoint, ProviderError

SPEC = {"goal":"Build a Python addition function and unittest","language":"python",
        "test_command":["python","-m","unittest","discover","-v"]}

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        engine.init(self.root)
        self.cfg=self.root/"settings.json"

    def config(self,provider="fixture",**kwargs):
        conf=load(self.cfg)
        conf["provider"]=provider
        conf.update(kwargs)
        write_json(self.cfg,conf)

    def create(self):
        spec=self.root/"task.json";write_json(spec,SPEC)
        return engine.create(self.root,spec)

    def test_fixture_end_to_end_and_no_replay(self):
        self.config()
        j=self.create()
        result=engine.run(self.root,j)
        self.assertEqual(result["state"]["status"],"PASS_FIXTURE")
        self.assertFalse(result["manifest"]["realAI"])
        self.assertEqual(result["manifest"]["isolation"],"PINNED_FIXTURE_ONLY_NOT_SANDBOX")
        self.assertTrue(engine.verify_job(self.root,j)["verified"])
        self.assertEqual(engine.run(self.root,j)["status"],"ALREADY_PASSED_NO_REPLAY")
        self.assertEqual(result["manifest"]["usage"]["modelCalls"],0)
        self.assertGreater(load(self.root/"work"/j/"attempt-01"/"test.json")["testCount"],0)
        self.assertGreater(result["journal"]["events"],5)

    def test_cache_and_sha_identity(self):
        self.config()
        a=self.create()
        engine.run(self.root,a)
        b=self.create()
        result=engine.run(self.root,b)
        self.assertEqual(result["manifest"]["usage"]["cacheHits"],1)
        self.assertEqual(result["manifest"]["usage"]["modelCalls"],0)

    def test_stop_resume_at_boundary(self):
        self.config()
        j=self.create()
        engine.control(self.root,j,"STOP")
        self.assertEqual(engine.run(self.root,j)["state"]["status"],"STOPPED")
        engine.control(self.root,j,"RUN")
        self.assertEqual(engine.run(self.root,j)["state"]["status"],"PASS_FIXTURE")
        self.assertGreater(engine.verify_job(self.root,j)["journal"]["events"],5)

    def test_resume_pending_test_without_regenerating(self):
        from unittest.mock import patch
        self.config()
        j=self.create()
        original=engine.gate
        calls=[0]
        def interrupt_at_test_boundary(folder):
            calls[0]+=1
            if calls[0]==3:
                engine.control(self.root,j,"STOP")
                raise InterruptedError("STOP_AT_SAFE_BOUNDARY")
            return original(folder)
        with patch.object(engine,"gate",side_effect=interrupt_at_test_boundary):
            stopped=engine.run(self.root,j)
        self.assertEqual(stopped["state"]["status"],"STOPPED")
        self.assertEqual(stopped["state"]["attempt"],1)
        engine.control(self.root,j,"RUN")
        result=engine.run(self.root,j)
        self.assertEqual(result["state"]["status"],"PASS_FIXTURE")
        self.assertTrue(result["manifest"]["resumedWithoutModelReplay"])
        self.assertEqual(len(list((self.root/"work"/j).glob("attempt-*"))),1)

    def test_tampered_source_detected(self):
        self.config()
        j=self.create()
        result=engine.run(self.root,j)
        path=self.root/"work"/j/"attempt-01"/"code"/"program.py"
        path.write_text("def add(a,b):return 999\n")
        with self.assertRaisesRegex(RuntimeError,"SOURCE_RECEIPT_DRIFT"):
            engine.verify_job(self.root,j)

    def test_invalid_spec_rejected(self):
        spec=self.root/"bad.json";write_json(spec,{"goal":"hi","language":"javascript","test_command":[]})
        with self.assertRaisesRegex(ValueError,"ONLY_PYTHON_UNITTEST"):
            engine.create(self.root,spec)

    def test_journal_chain_tampering_detected(self):
        log=self.root/"log.jsonl"
        event(log,"ONE",{"a":1});event(log,"TWO",{"b":2})
        self.assertEqual(verify_journal(log)["events"],2)
        log.write_bytes(log.read_bytes().replace(b'"a":1',b'"a":9'))
        with self.assertRaisesRegex(RuntimeError,"BROKEN_JOURNAL"):
            verify_journal(log)

    def test_cas_rejects_drift(self):
        p=self.root/"cas.json"
        write(p,b"old",new=True)
        with self.assertRaisesRegex(RuntimeError,"CAS_MISMATCH"):
            write(p,b"new",expected_sha="0000")

    def test_source_escape_rejected(self):
        folder=self.root/"x";folder.mkdir()
        for path in ("../x.py","C:/Windows/Temp/file.py","..\\evil.py","/tmp/evil.py",".git/config.py","hello.txt"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):safe_source(folder,path)

    def test_payload_requires_tests_and_syntax(self):
        folder=self.root/"c";folder.mkdir()
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_UNIT_TEST"):
            engine.validate_payload(folder,{"files":{"program.py":"x=1"}},1000)
        with self.assertRaises(SyntaxError):
            engine.validate_payload(folder,{"files":{"program.py":"def ()", "test_program.py":"pass"}},1000)

    def test_uncertain_job_no_blind_replay(self):
        self.config()
        j=self.create()
        engine.set_state(self.root/"work"/j,"UNKNOWN",1,"reconcile")
        with self.assertRaisesRegex(RuntimeError,"RECONCILE_DO_NOT_REPLAY"):
            engine.run(self.root,j)

    def test_real_model_fails_closed_without_docker(self):
        self.config(provider="ollama")
        j=self.create()
        from autofab.isolation import docker_preflight, IsolationUnavailable
        try:
            docker_preflight()
        except IsolationUnavailable:
            result=engine.run(self.root,j)
            self.assertEqual(result["state"]["status"],"BLOCKED_ISOLATION")
            self.assertEqual(result["state"]["attempt"],0)
            return
        self.skipTest("Docker available: test environment not suitable for missing-daemon assertion")

class ProviderTests(unittest.TestCase):
    def test_only_loopback(self):
        for endpoint in ("https://127.0.0.1:11434","http://example.com","http://127.0.0.1:11434/a",
                         "http://user:secret@127.0.0.1:11434"):
            with self.assertRaises(ProviderError):validate_endpoint(endpoint)
        self.assertEqual(validate_endpoint("http://127.0.0.1:11434"),("127.0.0.1",11434))

if __name__=="__main__":
    unittest.main()


class OwnerAcceptanceTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        from autofab import engine
        engine.init(self.root)
        (self.root/"examples").mkdir()

    def make_spec(self, accepted=True):
        import hashlib
        from autofab.storage import write_json
        source=self.root/"examples"/"test_user.py"
        source.write_text("import unittest\nclass Owner(unittest.TestCase):\n    def test_owner(self): self.assertEqual(1,1)\n",encoding="utf-8")
        checksum=hashlib.sha256(source.read_bytes()).hexdigest()
        if not accepted:checksum="0"*64
        spec={"goal":"build a function","language":"python","test_command":["python","-m","unittest","discover","-v"],
              "acceptance":{"relativePath":"examples/test_user.py","sha256":checksum}}
        path=self.root/"task.json";write_json(path,spec)
        return path,source,checksum

    def test_owner_bytes_pinned_at_intake(self):
        from autofab import engine
        from autofab.storage import sha_file, load
        spec,source,checksum=self.make_spec()
        job=engine.create(self.root,spec)
        self.assertEqual(sha_file(self.root/"work"/job/"acceptance"/"test_owner_acceptance.py"),checksum)
        self.assertEqual(load(self.root/"work"/job/"spec.json")["acceptance"]["sha256"],checksum)

    def test_wrong_acceptance_sha_fails_closed(self):
        from autofab import engine
        spec,_,_=self.make_spec(accepted=False)
        with self.assertRaisesRegex(ValueError,"ACCEPTANCE_SHA_MISMATCH"):
            engine.create(self.root,spec)
        self.assertEqual(list((self.root/"work").glob("AF-*")),[])

    def test_fixture_cannot_claim_owner_acceptance(self):
        from autofab import engine
        from autofab.storage import load, write_json
        spec,_,_=self.make_spec()
        cfg=load(self.root/"settings.json")
        cfg["provider"]="fixture"
        write_json(self.root/"settings.json",cfg)
        job=engine.create(self.root,spec)
        result=engine.run(self.root,job)
        self.assertEqual(result["state"]["status"],"FAILED")
        self.assertFalse((self.root/"work"/job/"manifest.json").exists())
        for path in (self.root/"work"/job).glob("attempt-*/test.json"):
            self.assertEqual(load(path).get("failureReason"),"PINNED_OWNER_ACCEPTANCE_NOT_EXECUTED")

    def test_owner_spec_path_escape_rejected(self):
        from autofab import engine
        from autofab.storage import load,write_json
        spec,_,_=self.make_spec()
        obj=load(spec)
        obj["acceptance"]["relativePath"]="examples/../test_bad.py"
        write_json(spec,obj)
        with self.assertRaisesRegex(ValueError,"ACCEPTANCE_FILENAME_INVALID"):
            engine.create(self.root,spec)

    def test_metrics_actual_elapsed(self):
        from autofab import engine
        from autofab.storage import write_json
        spec,_,_=self.make_spec()
        job=engine.create(self.root,spec)
        attempt=self.root/"work"/job/"attempt-01"
        attempt.mkdir()
        write_json(attempt/"model.json",{"usage":{"provider":"llama_cpp","elapsedMs":1234,
                   "promptTokens":10,"completionTokens":20},"cached":False})
        totals=engine.metrics(self.root)["totals"]
        self.assertEqual(totals["modelCalls"],1)
        self.assertEqual(totals["elapsedModelMs"],1234)
