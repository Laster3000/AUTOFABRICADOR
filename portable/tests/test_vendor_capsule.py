"""Vendor archive admits no fake offline status and no partial replay."""
from pathlib import Path
import tempfile,unittest
from autofab import vendor_capsule,engine
from autofab.isolation import IsolationUnavailable
from autofab.storage import load
class OfflineVendorTests(unittest.TestCase):
 def test_absent_original_archive_receipt_is_not_offline_complete(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engine.init(root)
   with self.assertRaises(IsolationUnavailable):
    vendor_capsule.preflight(root)
 def test_original_archive_receipt_is_immutable_and_versioned(self):
  root=Path(__file__).resolve().parents[1]
  r=root/"CONTINUIDAD/R036/VENDOR-ARCHIVE-RECEIPT.json"
  if not r.exists():self.skipTest("Source-only restoration has no original F vendor archive receipt")
  p=vendor_capsule.preflight(root)
  self.assertEqual(p["status"],"R036_PRIVATE_VENDOR_SHA_ARCHIVE_READY")
  self.assertEqual(p["files"],38439)
  self.assertIn("DotNet10.0.401",p["externalPrerequisitesNotBundled"])
 def test_streaming_sha_helper_matches_small_file_hash(self):
  import hashlib
  with tempfile.TemporaryDirectory() as tmp:
   f=Path(tmp)/"fixture.txt"
   f.write_bytes(b"sha"*10000)
   self.assertEqual(vendor_capsule.sha_stream(f),hashlib.sha256(f.read_bytes()).hexdigest())
if __name__=="__main__":unittest.main()
