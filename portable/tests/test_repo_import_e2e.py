"""Real import ZIP SHA, model supervisor and both original browser receipts."""
from pathlib import Path
import unittest
from autofab import repo_archive,repo_factory,repo_export
from autofab.storage import load,sha_file
class ImportedESME2E(unittest.TestCase):
 def test_imported_source_pre_inference_owner_and_no_npm_hooks(self):
  root=Path(__file__).resolve().parents[1]
  link=root/"repoimports/RI-071016a636a340cb.json"
  if not link.is_file():self.skipTest("Original imported source ZIP not in portable source-only restore")
  meta=load(link)
  self.assertEqual(meta["status"],"REPO_IMPORT_SHA_PINNED_NO_HOST_EXECUTION")
  self.assertTrue(meta["metadataNoScripts"])
  self.assertEqual(meta["modelCalls"],0)
  self.assertEqual(meta["sourceOriginalZipSha256"],
      sha_file(root/"repoimports/RI-071016a636a340cb.zip"))
  job=repo_factory.verify(root,meta["repoJobId"])
  self.assertTrue(job["verified"])
  self.assertEqual(job["ownerCases"],10)
 def test_true_browser_accepted_no_external_network(self):
  root=Path(__file__).resolve().parents[1]
  a=root/"repoexports/AF-REPO-RJ-0a8141a5fbb844aa.zip"
  if not a.exists():self.skipTest("Original Chrome guest output not in source-only ZIP")
  out=repo_export.verify(root,"RJ-0a8141a5fbb844aa")
  self.assertTrue(out["verified"])
  self.assertEqual(out["browserE2eCases"],10)
  self.assertEqual(out["ownerWasiCases"],10)
if __name__=="__main__":unittest.main()
