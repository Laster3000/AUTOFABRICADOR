"""Supervisor direct source-only jobs do not give AI a native editor subprocess."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import engine,supervisor
from autofab.storage import load,write_json
class DirectSupervisorTests(unittest.TestCase):
 def test_enqueue_only_fresh_direct_job_without_native_editor(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engine.init(root)
   (root/"autofabricador.py").write_text("# trusted test fixture\n")
   with patch("autofab.supervisor.direct_agent.status",return_value={
       "status":"PENDING","modelIntentWritten":False}):
    task=supervisor.enqueue(root,"direct","AD-0123456789abcdef")
   self.assertEqual(task["status"],"PENDING")
   row=load(root/"supervisor/queue"/(task["queueId"]+".json"))
   self.assertIsNone(row["editor"])
   with patch("autofab.supervisor.direct_agent.status",return_value={
       "status":"PASS","modelIntentWritten":True}):
    with self.assertRaisesRegex(RuntimeError,"UNUSED_PENDING"):
     supervisor.enqueue(root,"direct","AD-1123456789abcdef")
 def test_direct_editor_flag_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engine.init(root)
   (root/"autofabricador.py").write_text("# trusted fixture\n")
   with self.assertRaisesRegex(ValueError,"NO_NATIVE_EDITOR"):
    supervisor.enqueue(root,"direct","AD-0123456789abcdef","codex")
 def test_original_queue_real_direct_ai_pass(self):
  root=Path(__file__).resolve().parents[1]
  file=root/"supervisor/queue/SQ-003279882d2e4f5f.json"
  if not file.is_file():self.skipTest("Original real queue absent in ZIP-only restoration")
  row=load(file)
  self.assertEqual(row["kind"],"direct")
  self.assertEqual(row["status"],"SUCCEEDED")
  self.assertEqual(row["ref"],"AD-d9b755d157ef455c")
if __name__=="__main__":unittest.main()
