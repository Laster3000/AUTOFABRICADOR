"""Original local-model job STOP, owner immutability and receipt integrity."""
from pathlib import Path
from unittest import TestCase
import tempfile
from autofab import engine,repo_factory
from autofab.storage import load,write_json,sha_file
class RepoFactoryTests(TestCase):
 def test_rejects_bad_job_identifier(self):
  with self.assertRaisesRegex(ValueError,"JOB_ID_INVALID"):
   repo_factory.directory(Path("C:/"),"../../../Windows")
 def test_stop_before_model_intent_cas(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);engine.init(root)
   d=root/"repojobs/RJ-0123456789abcdef";d.mkdir(parents=True)
   write_json(d/"state.json",{"schema":1,"status":"PENDING"})
   write_json(d/"control.json",{"schema":1,"command":"RUN","version":1})
   out=repo_factory.stop(root,d.name)
   self.assertEqual(out["status"],"STOP_REQUESTED_ORIGINAL_CONTROL")
   self.assertEqual(load(d/"control.json")["command"],"STOP")
   self.assertEqual(repo_factory.stop(root,d.name)["status"],"ALREADY_STOP_REQUESTED")
   self.assertEqual(list(d.glob("attempts/*")),[])
 def test_terminal_failure_cannot_be_reactivated(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);engine.init(root)
   d=root/"repojobs/RJ-0123456789abcdef";d.mkdir(parents=True)
   write_json(d/"state.json",{"schema":1,"status":"FAILED_OWNER_ACCEPTANCE"})
   write_json(d/"control.json",{"schema":1,"command":"RUN","version":1})
   before=sha_file(d/"control.json")
   self.assertEqual(repo_factory.stop(root,d.name)["status"],"TERMINAL_NO_STOP_MUTATION")
   self.assertEqual(sha_file(d/"control.json"),before)
 def test_strict_model_sources_no_extra_file(self):
  spec={"sources":{"src/a.js":"const a=1;\n","src/b.js":"const b=2;\n"}}
  self.assertEqual(set(repo_factory._proposal('{"files":{"src/a.js":"export const a=1;","src/b.js":"export const b=2;"}}',spec)),set(spec["sources"]))
  with self.assertRaisesRegex(ValueError,"SOURCE_NAMES_CHANGED"):
   repo_factory._proposal('{"files":{"src/a.js":"A","src/attack.js":"B"}}',spec)
 def test_original_rejected_small_model_is_not_promoted(self):
  root=Path(__file__).resolve().parents[1]
  d=root/"repojobs/RJ-e548f679d85b4f8b"
  if not d.is_dir():self.skipTest("Original failed 1.5B model job not in source ZIP")
  self.assertEqual(load(d/"state.json")["status"],"FAILED_OWNER_ACCEPTANCE")
  self.assertEqual(len(list((d/"attempts").glob("A-*-stream.json"))),3)
  with self.assertRaisesRegex(RuntimeError,"NOT_ORIGINALLY_ACCEPTED"):
   repo_factory.verify(root,d.name)
if __name__=="__main__":
 import unittest;unittest.main()
