# coding: utf-8
"""R052 regression for original owner-no-progress and definitive truncation."""
from __future__ import annotations
import tempfile,json
from pathlib import Path
from unittest import TestCase,mock
from autofab import engine,repo_factory
from autofab.providers import ProviderError
from autofab.storage import load,sha_file,verify_journal

class R052Robustness(TestCase):
    def test_identical_original_owner_failures_detect_stagnation(self):
        owner={"status":"FAILED_OWNER_WASI",
          "originalOwnerResult":{"testResult":{
              "count":47,"passed":34,"failed":[
                 {"i":13,"expected":False,"got":True},
                 {"i":14,"expected":False,"got":True}]}}}
        self.assertTrue(repo_factory._same_owner_failure(owner,owner))
        edited=json.loads(json.dumps(owner))
        edited["originalOwnerResult"]["testResult"]["failed"][0]["got"]=False
        self.assertFalse(repo_factory._same_owner_failure(owner,edited))
        edited=json.loads(json.dumps(owner))
        edited["originalOwnerResult"]["testResult"]["passed"]=35
        self.assertFalse(repo_factory._same_owner_failure(owner,edited))
        edited["status"]="UNKNOWN"
        self.assertFalse(repo_factory._same_owner_failure(owner,edited))

    def test_replay_existing_immutable_original_owner_receipts(self):
        root=Path(__file__).resolve().parents[1]
        a=root/"repojobs/RJ-2b2bcf03301a4802/attempts/A-01-owner.json"
        b=root/"repojobs/RJ-2b2bcf03301a4802/attempts/A-02-owner.json"
        if not a.exists() or not b.exists():
            self.skipTest("Original R051 AI attempts absent from portable source")
        h1,h2=sha_file(a),sha_file(b)
        self.assertTrue(repo_factory._same_owner_failure(load(a),load(b)))
        self.assertEqual(sha_file(a),h1)
        self.assertEqual(sha_file(b),h2)

    def test_true_owner_progress_not_misclassified(self):
        root=Path(__file__).resolve().parents[1]
        a=root/"repojobs/RJ-723100d9e7e2432c/attempts/A-01-owner.json"
        b=root/"repojobs/RJ-723100d9e7e2432c/attempts/A-02-owner.json"
        if not a.exists() or not b.exists():
            self.skipTest("Original R051 owner progress receipt absent")
        self.assertFalse(repo_factory._same_owner_failure(load(a),load(b)))

    def test_provider_finish_reason_length_terminal_not_unknown(self):
        class CompleteTruncatedReply:
            def __init__(self,*a,**kw):pass
            def available_model(self):return {"digest":"sha256:verified-fake-deterministic","model":"test"}
            def generate(self,*a,**kw):
                raise ProviderError("LOCAL_MODEL_OUTPUT_TRUNCATED")

        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            engine.init(root)
            spec=root/"safe-owner-spec.json"
            spec.write_text(json.dumps({
                "goal":"Create Python unit-tested safe integer adder",
                "language":"python",
                "test_command":["python","-m","unittest","discover","-v"]
            }),encoding="utf-8")
            job=engine.create(root,spec)
            with mock.patch.object(engine,"LlamaCpp",CompleteTruncatedReply),mock.patch.object(
                    engine,"runner_preflight",return_value={"status":"PASS"}):
                result=engine.run(root,job)
            original=load(root/"work"/job/"state.json")
            self.assertEqual(original["status"],"FAILED_MODEL_OUTPUT_TRUNCATED")
            self.assertEqual(original["attempt"],1)
            self.assertTrue(original["noBlindReplay"])
            verify_journal(root/"work"/job/"journal.jsonl")
            self.assertFalse((root/"work"/job/"attempt-01"/"model.json").exists())
            with self.assertRaisesRegex(RuntimeError,"PREVIOUS_ATTEMPT_REQUIRES_RECONCILIATION"):
                with mock.patch.object(engine,"LlamaCpp",CompleteTruncatedReply),mock.patch.object(
                    engine,"runner_preflight",return_value={}):
                    engine.run(root,job)
