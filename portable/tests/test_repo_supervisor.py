"""Supervised imported ESM source job, original leases and owner CAS."""
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from autofab import engine,supervisor,repo_factory
from autofab.storage import load,write_json
class RepoSupervisorTests(unittest.TestCase):
 def test_repo_enqueue_refuses_native_editor(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engine.init(root)
   (root/"autofabricador.py").write_text("trusted fixture\n")
   with self.assertRaisesRegex(ValueError,"DISALLOWS_NATIVE_EDITOR"):
    supervisor.enqueue(root,"repo","RJ-0123456789abcdef",editor="codex")
 def test_queue_requires_original_pending_no_model_attempts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engine.init(root)
   (root/"autofabricador.py").write_text("fixture\n")
   with patch("autofab.supervisor.repo_factory.status",return_value={
     "status":"PASS","attemptsStarted":1}):
    with self.assertRaisesRegex(RuntimeError,"UNUSED_JOB"):
     supervisor.enqueue(root,"repo","RJ-0123456789abcdef")
 def test_original_supervised_zip_import_complete(self):
  root=Path(__file__).resolve().parents[1]
  file=root/"supervisor/queue/SQ-4eb380e338274995.json"
  if not file.is_file():self.skipTest("original queue only on connected Windows Host")
  task=load(file)
  self.assertEqual(task["kind"],"repo")
  self.assertEqual(task["status"],"SUCCEEDED")
  self.assertEqual(task["ref"],"RJ-0a8141a5fbb844aa")
  self.assertEqual(repo_factory.verify(root,task["ref"])["ownerCases"],10)
if __name__=="__main__":unittest.main()
