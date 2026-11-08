"""Active AUTOFABRICADOR recovery is only on D, prior F SHA still provenance."""
from pathlib import Path
import unittest
from autofab import vendor_capsule
from autofab.storage import load,sha_file
class DRescueTests(unittest.TestCase):
    def test_live_rescue_path_points_to_d_not_f(self):
        self.assertEqual(str(vendor_capsule.F),r"D:\AUTOFABRICADOR-RESCATE")
        self.assertFalse(str(vendor_capsule.F).startswith("F:"))
    def test_migration_original_sha_and_f_absence_on_host(self):
        root=Path(__file__).resolve().parents[1]
        p=root/"CONTINUIDAD/R037/F-D-MIGRATION-FINAL.json"
        if not p.exists():
            self.skipTest("F migration receipt only stored in original project")
        receipt=load(p)
        self.assertEqual(receipt["status"],"R037_F_AUTOFABRICADOR_RESCUE_EMPTY_MOVED_TO_D_FULL_SHA")
        self.assertTrue(receipt["DOriginalFilesReadbackVerified"])
        self.assertFalse(Path(r"F:\AUTOFABRICADOR-RESCATE").exists())
        d=Path(r"D:\AUTOFABRICADOR-RESCATE")
        self.assertTrue((d/"AUTOFABRICADOR-0.8.0-PRIVATE-VENDOR.zip").is_file())
        self.assertEqual(load(root/"OFFLINE-TOOLS.lock.json")["currentRescueDrive"],"D")
if __name__=="__main__":unittest.main()
