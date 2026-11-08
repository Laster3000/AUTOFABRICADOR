import gzip
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autofab import housekeeping

class HousekeepingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"autofabricador.py").write_text("# own test stub\n",encoding="utf-8")
        (self.root/"autofab"/"__pycache__").mkdir(parents=True)
        (self.root/"VENDOR"/"models").mkdir(parents=True)
        (self.root/"work"/"AF-123").mkdir(parents=True)
        (self.root/"CONTINUIDAD").mkdir()
        (self.root/"logs").mkdir()

    def test_dry_run_reports_without_deletion(self):
        binary=self.root/"autofab"/"__pycache__"/"mod.pyc"
        binary.write_bytes(b"x")
        report=housekeeping.maintain(self.root)
        self.assertEqual(report["mode"],"DRY_RUN")
        self.assertTrue(binary.exists())
        self.assertEqual(len(report["scan"]["safeBytecodeCandidates"]),1)

    def test_auto_removes_only_owned_bytecode(self):
        binary=self.root/"autofab"/"__pycache__"/"mod.pyc"
        binary.write_bytes(b"\x00\xff")
        real=self.root/"autofab"/"__pycache__"/"note.py"
        real.write_text("important")
        keep=self.root/"work"/"AF-123"/"source.py"
        keep.write_text("code")
        model=self.root/"VENDOR"/"models"/"weights.gguf"
        model.write_bytes(b"model")
        out=housekeeping.maintain(self.root,apply=True)
        self.assertTrue(out["changed"])
        self.assertFalse(binary.exists())
        self.assertTrue(real.exists())
        self.assertTrue(keep.exists())
        self.assertTrue(model.exists())
        self.assertTrue((self.root/"CONTINUIDAD"/"HOUSEKEEPING-JOURNAL.jsonl").exists())

    def test_large_log_rotates_with_exact_recovery(self):
        body=b"LOG " * 1500
        file=self.root/"logs"/"local-model.stderr.log"
        file.write_bytes(body)
        with patch.object(housekeeping,"LOG_ROTATE_BYTES",100):
            result=housekeeping.maintain(self.root,apply=True)
        self.assertTrue(result["changed"])
        self.assertEqual(file.read_bytes(),b"")
        archives=list((self.root/"logs"/"ARCHIVE").glob("*.gz"))
        self.assertEqual(len(archives),1)
        self.assertEqual(gzip.decompress(archives[0].read_bytes()),body)

    def test_active_lease_prevents_log_rotation(self):
        file=self.root/"logs"/"local-model.stderr.log"
        file.write_bytes(b"x"*2048)
        lease=self.root/"CONTINUIDAD"/"LOCAL-SERVER.json"
        lease.write_text('{"pid":1}')
        with patch.object(housekeeping,"LOG_ROTATE_BYTES",100):
            report=housekeeping.maintain(self.root,apply=True)
        self.assertFalse(report["changed"])
        self.assertEqual(file.stat().st_size,2048)

    def test_unknown_partial_download_preserved(self):
        partial=self.root/"VENDOR"/"models"/"download.gguf.PART.abc"
        partial.write_bytes(b"unknown")
        scan=housekeeping.inspect(self.root)
        self.assertIn(str(partial),scan["unknownVendorPartialsRequiringManualReconciliation"])
        housekeeping.maintain(self.root,apply=True)
        self.assertTrue(partial.exists())

    def test_safety_no_touch_outside_root(self):
        outside=Path(self.tmp.name).parent/"AUTOFABRICADOR-NOT-MY-PROJECT"
        with self.assertRaisesRegex(RuntimeError,"HOUSEKEEPING_ONLY_FACTORY_PROJECT_ROOT"):
            housekeeping.maintain(outside,apply=True)

if __name__=="__main__":
    unittest.main()


class OptionalEditorSafety(unittest.TestCase):
    def test_editor_vendor_and_original_mission_receipts_not_auto_cleaned(self):
        with tempfile.TemporaryDirectory() as root_name:
            root=Path(root_name)
            (root/"autofabricador.py").write_text("# test\n",encoding="utf-8")
            paths=[
                root/"VENDOR/editors/download-cache/a.tgz",
                root/"VENDOR/editors/node/node_modules/editor/index.js",
                root/"VENDOR/editors/aider-venv/Scripts/python.exe",
                root/"missions/AM-test/stage-01.json",
                root/"work/AF-test/attempt-01/EDITOR-STDOUT.bin",
                root/"CONTINUIDAD/R033/MANIFEST.json",
            ]
            for path in paths:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b"important")
            report=housekeeping.maintain(root,apply=True)
            self.assertFalse(report["changed"])
            self.assertTrue(all(path.read_bytes()==b"important" for path in paths))
            scan=housekeeping.inspect(root)
            self.assertGreater(scan["classes"]["private_code_editors_node"]["bytes"],0)
            self.assertGreater(scan["classes"]["recoverable_multiagent_missions"]["bytes"],0)
