"""Mission lifecycle and STOP/recovery tests with no model or network."""
import hashlib,json,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from autofab import engine,mission
from autofab.storage import load,write_json

class MissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        engine.init(self.root)
        sample=self.root/"examples"
        sample.mkdir()
        (sample/"sample.py").write_text("def f(x):\n    return x\n",encoding="utf-8")
        owner=sample/"test_owner_sample.py"
        owner.write_text("import unittest\nfrom sample import f\nclass Owner(unittest.TestCase):\n def test_one(self): self.assertEqual(f(1),1)\n",encoding="utf-8")
        expected=hashlib.sha256(owner.read_bytes()).hexdigest()
        spec=self.root/"spec.json"
        write_json(spec,{"goal":"Edit only sample.py to pass the tests",
                         "language":"python","test_command":["python","-m","unittest","discover","-v"],
                         "acceptance":{"relativePath":"examples/test_owner_sample.py","sha256":expected}})
        self.job=engine.create(self.root,spec)

    def test_plan_is_persisted_with_sha_and_journal(self):
        item=mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",["codex","opencode"])
        state=mission.summary(self.root,item["missionId"])
        self.assertEqual(state["state"]["status"],"PENDING")
        self.assertEqual(state["plan"]["reviewers"],["codex","opencode"])
        self.assertEqual(item["planSha256"],state["state"]["planSha256"])

    def test_duplicate_mission_for_same_job_not_allowed(self):
        mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",[])
        with self.assertRaisesRegex(RuntimeError,"ALREADY_BOUND"):
            mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",[])

    def test_stop_does_not_start_model_or_execute_stage(self):
        created=mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",["codex"])
        mid=created["missionId"]
        mission.control(self.root,mid,"STOP")
        with patch("autofab.mission.local_runtime.start") as started:
            summary=mission.run(self.root,mid)
        self.assertEqual(summary["state"]["status"],"STOPPED")
        self.assertEqual(summary["state"]["stageIndex"],0)
        started.assert_not_called()
        self.assertEqual(load(self.root/"work"/self.job/"state.json")["status"],"PENDING")
        mission.control(self.root,mid,"RUN")
        self.assertEqual(mission.summary(self.root,mid)["control"]["command"],"RUN")

    def test_unknown_mission_does_not_replay(self):
        created=mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",[])
        mid=created["missionId"]
        path=self.root/"missions"/mid
        mission._write_state(path,{"status":"UNKNOWN","stageIndex":0,"nextAction":"reconcile"})
        with self.assertRaisesRegex(RuntimeError,"DO_NOT_REPLAY"):
            mission.run(self.root,mid)

    def test_plan_cas_drift_rejected(self):
        created=mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",[])
        path=self.root/"missions"/created["missionId"]/"plan.json"
        bad=load(path)
        bad["sourceName"]="changed.py"
        write_json(path,bad)
        with self.assertRaisesRegex(RuntimeError,"PLAN_SHA_DRIFT"):
            mission.summary(self.root,created["missionId"])

    def test_arbitrary_readers_and_paths_denied(self):
        with self.assertRaisesRegex(RuntimeError,"NOT_SUPPORTED"):
            mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",["arbitrary"])
        with self.assertRaisesRegex(RuntimeError,"SEED_NAME_UNSAFE"):
            mission.create(self.root,self.job,"aider","sample.py","../../escape.py",[])

if __name__=="__main__":
    unittest.main()


class MissionReconciliationTests(MissionTests):
    def test_persisted_completed_stage_is_not_reinvoked(self):
        from autofab.storage import event,sha_file
        created=mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",["codex"])
        d=self.root/"missions"/created["missionId"]
        advice=self.root/"work"/self.job/"advice"
        advice.mkdir()
        write_json(advice/"codex-original.json",{"status":"ADVICE_ONLY_NOT_APPLIED",
                                               "tool":"codex","jobId":self.job,
                                               "suggestion":"Change the source."})
        file=d/"stage-01.json"
        write_json(file,{"schema":1,"stage":0,"role":"review","tool":"codex",
                         "status":"PASS","jobState":"PENDING","originalResultStatus":"ADVICE_ONLY_NOT_APPLIED"})
        event(d/"journal.jsonl","MISSION_STAGE_RECEIPT",
              {"i":0,"receiptSha":sha_file(file),"status":"PASS"})
        mission._write_state(d,{"status":"RUNNING","stageIndex":0,"nextAction":"was interrupted after receipt"})
        with patch("autofab.mission.advisors.advise") as model:
            outcome=mission.reconcile(self.root,created["missionId"])
        self.assertEqual(outcome["status"],"RECOVERED_WITH_ORIGINAL_RECEIPT_NO_REPLAY")
        self.assertEqual(outcome["mission"]["state"]["stageIndex"],1)
        self.assertEqual(outcome["mission"]["state"]["status"],"READY")
        model.assert_not_called()

    def test_intent_without_original_receipt_becomes_unknown(self):
        created=mission.create(self.root,self.job,"aider","sample.py","examples/sample.py",["codex"])
        d=self.root/"missions"/created["missionId"]
        mission._write_state(d,{"status":"RUNNING","stageIndex":0,"nextAction":"crash before receipt"})
        with patch("autofab.mission.advisors.advise") as model:
            response=mission.reconcile(self.root,created["missionId"])
        self.assertEqual(response["status"],"UNKNOWN_NO_REPLAY")
        self.assertEqual(response["mission"]["state"]["status"],"UNKNOWN")
        model.assert_not_called()
