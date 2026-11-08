"""Higher model source is original user cache, pinned SHA and stopped on Host."""
from pathlib import Path
import tempfile,unittest
from autofab import local_escalation
from autofab.storage import load,sha_file
class ModelEscalationTests(unittest.TestCase):
 def test_large_model_is_not_fake_local_1_5b(self):
  self.assertEqual(local_escalation.MODEL_SHA,"ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed")
  self.assertNotEqual(local_escalation.PORT,11435)
  self.assertEqual(local_escalation.PORT,11436)
 def test_large_model_original_sha_cache_provenance(self):
  root=Path(__file__).resolve().parents[1]
  p=root/"CONTINUIDAD/R038/14B-MODEL-SHA-CACHE.json"
  if not p.exists():self.skipTest("original user Ollama model cache not present")
  value=load(p)
  self.assertEqual(value["status"],"FULL_ORIGINAL_SHA_VERIFIED_CACHED_METADATA")
  self.assertEqual(value["originalModelSha"],local_escalation.MODEL_SHA)
  self.assertEqual(value["bytes"],local_escalation.MODEL_SIZE)
  original=Path(value["originalSource"])
  self.assertTrue(original.is_file())
  self.assertEqual(original.stat().st_mtime_ns,value["mtimeNs"])
 def test_real_escalated_model_owner_12(self):
  root=Path(__file__).resolve().parents[1]
  result=root/"repojobs/RJ-ca8e3c3d64a541ba/manifest.json"
  if not result.exists():self.skipTest("original 14B real model job not part of source-only ZIP")
  from autofab import repo_factory
  verified=repo_factory.verify(root,"RJ-ca8e3c3d64a541ba")
  self.assertTrue(verified["verified"])
  self.assertEqual(verified["ownerCases"],12)
  self.assertEqual(verified["modelAttempts"],1)
if __name__=="__main__":unittest.main()
