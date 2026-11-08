# coding: utf-8
"""Independent boundary contracts for originally accepted repo -> native VM bridge."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from autofab import native_repo_bridge as b
from autofab import engine

class NativeRepoBridgeContract(unittest.TestCase):
    def test_runner_consumes_owner_original_cases_not_model_tests(self):
        self.assertIn("owner.cases",b.RUNNER)
        self.assertIn("assert.deepStrictEqual",b.RUNNER)
        self.assertIn("vm.runInContext",b.RUNNER)
        self.assertNotIn("eval(",b.RUNNER)
        self.assertNotIn("child_process",b.RUNNER)
    def test_binary_is_explicitly_sha_and_length_pinned(self):
        self.assertEqual(b.NODE_SHA,"5c976096e04e5c2c1f091938926234cc9fbebfe9787ddd149351b3b0ecc707b5")
        self.assertGreater(b.NODE_SIZE,90000000)
    def test_build_script_checks_sha_before_execution(self):
        text=b._ps_build("a"*64,"b"*64,"c"*64).decode()
        for marker in ("NODE_SHA_DRIFT","APP_SHA_DRIFT","OWNER_SHA_DRIFT","OWNER_NATIVE_BUILD_OK"):
            self.assertIn(marker,text)
    def test_test_script_executes_only_in_guest(self):
        code=b._ps_test().decode()
        self.assertIn("OWNER_NATIVE_NODE_CASES_FAILED",code)
        self.assertIn("Split-Path -Parent $PSScriptRoot",code)
        self.assertNotIn("C:\\AUTOFABRICADOR",code)
    def test_bad_job_identifier_fails_before_node_resolution(self):
        with tempfile.TemporaryDirectory(prefix="af-native-bridge-") as t:
            engine.init(Path(t))
            with self.assertRaisesRegex(ValueError,"BAD_REPO_JOB_ID"):
                b.stage_repo(t,"RJ-../../private")
    def test_no_runtime_lock_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="af-native-bridge-") as t:
            with self.assertRaises(FileNotFoundError):
                b._pinned_node(t)
    def test_source_only_release_lock_present_without_node_bytes(self):
        root=Path(__file__).resolve().parents[1]
        lock=root/"NATIVE-NODE.lock.json"
        if not lock.is_file():
            self.skipTest("No native Node lock in historical source bundle")
        obj=json.loads(lock.read_text(encoding="utf-8"))
        self.assertEqual(obj["nodeSha256"],b.NODE_SHA)
        self.assertEqual(obj["mode"],"COPY_ONLY_TO_WINDOWS_SANDBOX")
        self.assertNotIn("privateKey",obj)
if __name__=="__main__":
    unittest.main()
