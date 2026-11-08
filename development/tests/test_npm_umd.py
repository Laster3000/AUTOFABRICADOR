"""Pinned npm UMD libraries run in Wasmtime only, never Node host."""
from pathlib import Path
import json,tempfile,unittest
from autofab import npm_umd,js_wasi
from autofab.isolation import IsolationUnavailable
ROOT=Path(__file__).resolve().parents[1]

class TrustedUmd(unittest.TestCase):
    def test_unsafe_npm_package_and_duplicates_blocked(self):
        with self.assertRaisesRegex(ValueError,"NOT_ALLOWLISTED"):
            npm_umd.trusted(ROOT,["arbitrary-user-script"])
        with self.assertRaisesRegex(ValueError,"LIST_INVALID"):
            npm_umd.trusted(ROOT,["lodash","lodash"])

    def test_missing_vendor_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(IsolationUnavailable):
                npm_umd.trusted(Path(t),["dayjs"])

    def test_original_vendor_hashes_verifiable(self):
        try:
            src,proof=npm_umd.trusted(ROOT,["dayjs","lodash"])
        except IsolationUnavailable:self.skipTest("Optional pinned vendor UMD source not installed")
        self.assertGreater(len(src),10000)
        self.assertEqual(set(proof),{"dayjs","lodash"})
        self.assertEqual(len(proof["dayjs"]["fileSha256"]),64)

    def test_both_npm_packages_execute_only_in_wasi(self):
        try:
            js_wasi.preflight(ROOT,"javascript")
            npm_umd.trusted(ROOT,["dayjs","lodash"])
        except IsolationUnavailable:self.skipTest("Optional Javy and locked UMD libs not present")
        source={"library.js":"function dateSum(s,a){return dayjs(s).format('YYYY-MM-DD')+'|'+_.sum(a);}\n"}
        cases=[{"args":["2024-03-15",[1,2,3]],"expected":"2024-03-15|6"}]*5
        result=js_wasi.execute(ROOT,"javascript",source,"dateSum",cases,dependencies=["dayjs","lodash"])
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["independentTestCount"],5)
        self.assertEqual(set(result["dependencyHashes"]),{"dayjs","lodash"})
        self.assertEqual(result["trust"]["hostFilesystemGrants"],0)
        self.assertEqual(result["trust"]["networkGrants"],0)

if __name__=="__main__":unittest.main()
