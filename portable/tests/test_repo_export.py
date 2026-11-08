"""Portable repository package accepted only with owner WASI+Chrome E2E."""
from pathlib import Path
from unittest import TestCase
from autofab import repo_export
from autofab.storage import load
class RepoExportTests(TestCase):
 def test_original_real_repo_browser_receipt_after_acceptance(self):
  root=Path(__file__).resolve().parents[1]
  exports=list((root/"repoexports").glob("AF-REPO-RJ-*.zip")) if (root/"repoexports").is_dir() else []
  if not exports:self.skipTest("Original real model+browser output not present in source-only restoration")
  jid=exports[0].stem.removeprefix("AF-REPO-")
  result=repo_export.verify(root,jid)
  self.assertTrue(result["verified"])
  self.assertGreaterEqual(result["ownerWasiCases"],6)
  self.assertEqual(result["ownerWasiCases"],result["browserE2eCases"])
  self.assertFalse(result["nativeEditorRan"])
if __name__=="__main__":
 import unittest;unittest.main()
