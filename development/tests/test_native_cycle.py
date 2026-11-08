# coding: utf-8
"""Contract tests for original bounded persistent native cycle. No real VM here."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autofab import engine,native_cycle,supervisor
from autofab.storage import load,write_json,verify_journal,sha_file

class NativeCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-r045-cycle-")
        self.addCleanup(self.tmp.cleanup)
        self.root=engine.init(Path(self.tmp.name))
        (self.root/'autofabricador.py').write_text('first party CLI fixture',encoding='utf-8')
        self.repo="RJ-0011223344556677"
        self.accept={"verified":True,"status":"PASS","ownerCases":10,"modelAttempts":1,
                     "compiledSha256":"a"*64}
        d=self.root/"repojobs"/self.repo
        d.mkdir(parents=True,exist_ok=True)
        write_json(d/"manifest.json",{"schema":1,"originalOwnerSha":"a"*64},new=True)

    def _create(self):
        with patch.object(native_cycle.repo_factory,"verify",return_value=self.accept):
            return native_cycle.create(self.root,self.repo)

    def test_invalid_id_and_nonaccepted_repo(self):
        with self.assertRaisesRegex(ValueError,"REPO_ID_INVALID"):
            native_cycle.create(self.root,"../../private")
        with patch.object(native_cycle.repo_factory,"verify",return_value={"verified":False}):
            with self.assertRaisesRegex(RuntimeError,"MUST_BE_PASS"):
                native_cycle.create(self.root,self.repo)

    def test_original_once_and_stop_before_staging(self):
        first=self._create()
        second=self._create()
        self.assertEqual(second["status"],"ALREADY_CREATED_NO_REPLAY")
        self.assertEqual(first["cycleId"],second["cycleId"])
        result=native_cycle.stop(self.root,first["cycleId"])
        self.assertEqual(result["status"],"STOP_REQUESTED_FIRST_SAFE_BOUNDARY")
        with patch.object(native_cycle.native_repo_bridge,"stage_repo") as stage:
            outcome=native_cycle.run(self.root,first["cycleId"])
            stage.assert_not_called()
        self.assertEqual(outcome["status"],"STOPPED_PRE_LAUNCH")
        self.assertEqual(native_cycle.status(self.root,first["cycleId"])["status"],
                         "STOPPED_PRE_LAUNCH")
        verify_journal(native_cycle.folder(self.root,first["cycleId"])/"journal.jsonl")
        with self.assertRaisesRegex(RuntimeError,"NO_BLIND_REPLAY"):
            native_cycle.run(self.root,first["cycleId"])

    def test_conflicting_vm_fails_closed_without_original_staging(self):
        cycle=self._create()["cycleId"]
        with patch.object(native_cycle.repo_factory,"verify",return_value=self.accept),\
             patch.object(native_cycle,"_sessions",return_value=[{"pid":123,"born":"x"}]),\
             patch.object(native_cycle.native_repo_bridge,"stage_repo") as stage:
            result=native_cycle.run(self.root,cycle)
            stage.assert_not_called()
        self.assertEqual(result["status"],"BLOCKED_VM_CONFLICT")
        with self.assertRaisesRegex(RuntimeError,"NO_BLIND_REPLAY"):
            native_cycle.run(self.root,cycle)

    def test_original_wasi_then_guest_untrusted_result_and_no_replay(self):
        cycle=self._create()["cycleId"]
        sid="SX-0011223344556677"
        output=self.root/"sandboxjobs"/sid/"output"
        output.mkdir(parents=True)
        (output/"guest-report.json").write_text('{"schema":1,"untrusted":true}',
                                                 encoding="utf-8")
        with patch.object(native_cycle.repo_factory,"verify",return_value=self.accept),\
             patch.object(native_cycle,"_sessions",return_value=[]),\
             patch.object(native_cycle.native_repo_bridge,"stage_repo",
                          return_value={"sandboxJob":sid,"zipSha":"a"*64}),\
             patch.object(native_cycle.windows_sandbox,"launch",
                          return_value={"status":"LAUNCHED_GUEST_NOT_ATTESTED"}),\
             patch.object(native_cycle.native_repo_bridge,"verify_native",
                          return_value={"status":"ORIGINAL_WASI_AND_NATIVE_GUEST_READBACK_CORRELATED"}),\
             patch.object(native_cycle,"_close_session_exact",return_value={"closed":True}):
            result=native_cycle.run(self.root,cycle,timeout=3)
        self.assertEqual(result["status"],native_cycle.OK)
        self.assertFalse(result["nativeCryptographicOwnerAcceptance"])
        self.assertTrue(result["guestOutputUntrusted"])
        self.assertEqual(result["ownerCases"],10)
        self.assertEqual(native_cycle.status(self.root,cycle)["status"],native_cycle.OK)
        verify_journal(native_cycle.folder(self.root,cycle)/"journal.jsonl")
        with self.assertRaisesRegex(RuntimeError,"NO_BLIND_REPLAY"):
            native_cycle.run(self.root,cycle)

    def test_supervisor_native_queue_is_unique_and_never_native_editor(self):
        cycle=self._create()["cycleId"]
        with patch.object(supervisor.native_cycle,"status",
                          return_value={"status":"PENDING","sourceRepo":self.repo,
                                        "originalOwnerCases":10}):
            one=supervisor.enqueue(self.root,"native",cycle)
            duplicate=supervisor.enqueue(self.root,"native",cycle)
        self.assertEqual(one["queueId"],duplicate["queueId"])
        self.assertEqual(duplicate["status"],"ALREADY_QUEUED_OR_RECORDED_NO_REPLAY")
        with self.assertRaisesRegex(ValueError,"NATIVE_SUPERVISOR_NO_EDITOR"):
            supervisor.enqueue(self.root,"native",cycle,editor="codex")

    def test_vm_conflict_requeues_same_supervisor_id_with_proof(self):
        cycle=self._create()["cycleId"]
        queued=supervisor.enqueue(self.root,"native",cycle)
        with patch.object(native_cycle.repo_factory,"verify",return_value=self.accept),\
             patch.object(native_cycle,"_sessions",return_value=[{"pid":123,"born":"x"}]):
            blocked=native_cycle.run(self.root,cycle)
        self.assertEqual(blocked["status"],"BLOCKED_VM_CONFLICT")
        p=supervisor.directory(self.root)
        f=p/"queue"/(queued["queueId"]+".json")
        supervisor._task_update(p,f,{"status":"UNKNOWN",
                                    "originalStatus":"BLOCKED_VM_CONFLICT",
                                    "childExitCode":0})
        with patch.object(native_cycle.repo_factory,"verify",return_value=self.accept),\
             patch.object(native_cycle,"_sessions",return_value=[]):
            recovered=supervisor.requeue_vm_conflict(self.root,queued["queueId"])
        self.assertEqual(recovered["status"],"PENDING_SAME_QUEUE_NO_REPLAY")
        self.assertEqual(recovered["queueId"],queued["queueId"])
        self.assertEqual(native_cycle.status(self.root,cycle)["status"],"PENDING")
        self.assertTrue((native_cycle.folder(self.root,cycle)/"resume-proof.json").exists())
        self.assertEqual(load(f)["status"],"PENDING")
        with self.assertRaisesRegex(RuntimeError,"NOT_PROVEN_PRELAUNCH"):
            supervisor.requeue_vm_conflict(self.root,queued["queueId"])

    def test_vm_conflict_with_staged_bridge_cannot_resume(self):
        cycle=self._create()["cycleId"]
        d=native_cycle.folder(self.root,cycle)
        native_cycle._step(d,"BLOCKED_VM_CONFLICT","fixture")
        write_json(d/"bridge.json",{"sandboxJob":"SX-0011223344556677"},new=True)
        with self.assertRaisesRegex(RuntimeError,"NO_RESUME"):
            native_cycle.resume_conflict(self.root,cycle)

    def test_original_log_collision_requeues_without_child_replay(self):
        cycle=self._create()["cycleId"]
        queued=supervisor.enqueue(self.root,"native",cycle)
        with patch.object(native_cycle.repo_factory,"verify",return_value=self.accept),\
             patch.object(native_cycle,"_sessions",return_value=[{"pid":1,"born":"x"}]):
            native_cycle.run(self.root,cycle)
        with patch.object(native_cycle.repo_factory,"verify",return_value=self.accept),\
             patch.object(native_cycle,"_sessions",return_value=[]):
            native_cycle.resume_conflict(self.root,cycle)
        p=supervisor.directory(self.root)
        logfile=p/"logs"/(queued["queueId"]+".log")
        logfile.write_text("original immutable queue log",encoding="utf-8")
        qfile=p/"queue"/(queued["queueId"]+".json")
        proof=native_cycle.folder(self.root,cycle)/"resume-proof.json"
        supervisor._task_update(p,qfile,{"status":"RUNNING","resumeProofSha":sha_file(proof)})
        supervisor._task_update(p,qfile,{"status":"UNKNOWN","errorType":"FileExistsError",
            "detail":f"[Errno 17] File exists: {str(logfile)!r}",
            "originalStatus":"PENDING"})
        recovered=supervisor.requeue_log_collision(self.root,queued["queueId"])
        self.assertEqual(recovered["queueId"],queued["queueId"])
        self.assertEqual(recovered["status"],"PENDING_SAME_SQ_NO_NEW_NATIVE_INTENT")
        self.assertEqual(load(qfile)["status"],"PENDING")
        self.assertEqual(native_cycle.status(self.root,cycle)["status"],"PENDING")
        with self.assertRaisesRegex(RuntimeError,"NOT_PROVEN_NATIVE_LOG_COLLISION"):
            supervisor.requeue_log_collision(self.root,queued["queueId"])

if __name__=="__main__":unittest.main()
