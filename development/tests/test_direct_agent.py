"""Direct localhost model lifecycle (no native source-editor subprocess) and original CAS."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from autofab import engine,direct_agent
from autofab.storage import load,write_json,sha_file,event

class DirectAgentTests(unittest.TestCase):
 def test_cancelled_and_completed_jobs_never_allow_replay(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engine.init(root)
   job=root/"directjobs"/"AD-0123456789abcdef";job.mkdir(parents=True)
   write_json(job/"control.json",{"schema":1,"command":"RUN","version":1})
   write_json(job/"state.json",{"schema":1,"status":"PASS"})
   old=sha_file(job/"control.json")
   result=direct_agent.control(root,job.name,"STOP")
   self.assertEqual(result["status"],"TERMINAL_NO_CONTROL_CHANGE")
   self.assertEqual(sha_file(job/"control.json"),old)
   with self.assertRaisesRegex(RuntimeError,"NOT_PENDING_OR_ALREADY_SENT"):
    direct_agent.run(root,job.name)
 def test_unsafe_job_id_rejected(self):
  with self.assertRaisesRegex(ValueError,"DIRECT_JOB_ID_INVALID"):
   direct_agent.folder(Path("C:/"),"../../HOST")
 def test_local_transport_uses_loopback_only(self):
  import inspect
  s=inspect.getsource(direct_agent._stream_text)
  self.assertIn('"127.0.0.1"',s)
  self.assertIn('"POST","/v1/chat/completions"',s)
  self.assertNotIn('source_editors._command',s)
 def test_original_direct_model_and_wasi_are_reverifiable(self):
  root=Path(__file__).resolve().parents[1]
  d=root/"directjobs/AD-d97a5e0f778944da"
  if not d.is_dir():self.skipTest("Original real E2E receipts only on connected Host")
  from autofab.isolation import IsolationUnavailable
  try:result=direct_agent.verify(root,d.name)
  except IsolationUnavailable:self.skipTest("Original WASI dependency not available")
  self.assertTrue(result["verified"])
  self.assertEqual(result["ownerTestCount"],11)
  self.assertIs(result["nativeEditorLaunched"],False)

if __name__=="__main__":unittest.main()
