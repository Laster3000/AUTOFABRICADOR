# coding: utf-8
"""R76 first-party bounded reference package interface tests, no install."""
import tempfile,unittest,shutil,json,hashlib
from pathlib import Path
from autofab import reference_suite_r76 as ref
class R76ReferenceSuiteTests(unittest.TestCase):
 def root(self):
  return Path(__file__).resolve().parents[1]
 def test_scoped_capabilities(self):
  a=ref.capabilities()
  self.assertEqual(a["status"],ref.STATUS)
  self.assertFalse(a["generalFactoryActive"])
  self.assertEqual(len(a["families"]),5)
 def test_android_device_e2e_not_fake(self):
  a=ref.capabilities()
  self.assertFalse(a["androidPhysicalDeviceE2E"])
  self.assertFalse(a["secondPhysicalPCVerified"])
  self.assertIn("DEVICE_E2E_BLOCKED",a["families"]["android-csharp"])
 def test_model_not_bundled(self):
  a=ref.capabilities()
  self.assertFalse(a["packageFullySelfContained"])
  self.assertTrue(a["requiresExternalModelForAI"])
  self.assertTrue(a["requiresPythonRuntime"])
 def test_pinned_assets_declared(self):
  self.assertEqual(ref.R75_2D_SHA,"20ff069b2506c99d9c74d9cc804169d99f548baa1adbe5da17bfb77934350412")
  self.assertEqual(ref.R75_3D_SHA,"aeeff001662f47210319c5fcc28ec6409088209441f7f433466ec8152575d124")
  self.assertEqual(ref.APK_SHA,"ce33408272e14db655cb3137b7f568755b5dc4c59e8a109b35b9f47020e0295a")
 def test_original_source_package_preflight(self):
  row=ref.preflight(self.root())
  self.assertEqual(row["archiveSha"],ref.PIN)
  self.assertEqual(row["entryCount"],29)
  self.assertTrue(row["notUniversal"])
 def test_no_export_has_no_effect(self):
  row=ref.verify(self.root())
  self.assertEqual(row["deliveryStatus"],"NOT_EXPORTED_YET")
 def test_missing_source_denied(self):
  with tempfile.TemporaryDirectory(prefix="AF-R76-NEG-") as temp:
   with self.assertRaisesRegex(RuntimeError,"PINNED"):
    ref.preflight(temp)
 def test_fake_archive_denied(self):
  with tempfile.TemporaryDirectory(prefix="AF-R76-NEG-") as temp:
   p=Path(temp)/"TEMPLATES"/"R76"/ref.NAME
   p.parent.mkdir(parents=True)
   p.write_bytes(b"NOT A ZIP")
   with self.assertRaisesRegex(RuntimeError,"PINNED"):
    ref.preflight(temp)
 def test_temp_export_and_verify_no_replay(self):
  with tempfile.TemporaryDirectory(prefix="AF-R76-PACK-") as temp:
   source=self.root()/"TEMPLATES"/"R76"/ref.NAME
   copied=Path(temp)/"TEMPLATES"/"R76"/ref.NAME
   copied.parent.mkdir(parents=True)
   shutil.copy2(source,copied)
   first=ref.export(temp)
   self.assertEqual(first["deliveryStatus"],"PASS_EXPORTED_BOUND_REFERENCE_NOT_ACTIVE")
   self.assertFalse(first["replayed"])
   original_sha=ref._sha(copied)
   second=ref.export(temp)
   self.assertEqual(second["deliveryStatus"],"PASS_EXPORTED_BOUND_REFERENCE_NOT_ACTIVE")
   self.assertTrue(second["replayed"] is False)
   self.assertEqual(ref._sha(Path(temp)/"apps"/ref.DEST),original_sha)
 def test_old_jobs_never_read(self):
  original=ref.preflight(self.root())
  self.assertNotIn("originalJobReplay",original)
  self.assertTrue(original["notUniversal"])
 def test_immutable_zip_hash(self):
  p=self.root()/"TEMPLATES"/"R76"/ref.NAME
  self.assertEqual(ref._sha(p),ref.PIN)
 def test_unknown_model_code_denied_as_universal(self):
  a=ref.capabilities()
  self.assertTrue(a["notGeneralAutonomousCodeGeneration"])
  self.assertTrue(a["noBootServiceOrAutoStart"])
if __name__=="__main__":unittest.main()
