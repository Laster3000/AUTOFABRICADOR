"""Multi-file original AI source accepted in WASI, interactive Chrome E2E."""
from pathlib import Path
import tempfile,unittest
from autofab import ledger_project
class LedgerProjectTests(unittest.TestCase):
    def test_strict_offline_browser_csp_and_accessible_form(self):
        page=ledger_project._index("AD-0123456789abcdef")
        self.assertIn("connect-src 'none'",page)
        self.assertIn('id="add"',page)
        self.assertIn('aria-live="polite"',page)
        self.assertIn('id="lines"',page)
        self.assertNotIn("http://",page)
    def test_user_sku_never_inserted_as_html(self):
        js=ledger_project._controller()
        self.assertIn("td.textContent=value",js)
        self.assertNotIn("innerHTML",js)
        self.assertIn('Number.isSafeInteger(qty)',js)
    def test_multiple_files_original_accepted_22_owner_tests(self):
        root=Path(__file__).resolve().parents[1]
        original=root/"directjobs/AD-fd26d0df974e49f9/manifest.json"
        if not original.exists():
            self.skipTest("Original R037 model output is intentionally excluded from source-only ZIP")
        d,spec,files,manifest=ledger_project._verify_source(root,"AD-fd26d0df974e49f9")
        self.assertEqual(set(files),{"normalize.js","cents.js","invoice.js"})
        self.assertEqual(len(spec["acceptance"]),22)
        self.assertFalse(manifest["nativeEditorLaunched"])
    def test_real_browser_integration_receipt_verify(self):
        root=Path(__file__).resolve().parents[1]
        archive=root/"projects/LEDGER-AD-fd26d0df974e49f9.zip"
        if not archive.exists():
            self.skipTest("Original R037 Chrome browser E2E is excluded from source-only ZIP")
        result=ledger_project.verify(root,"AD-fd26d0df974e49f9")
        self.assertTrue(result["verified"])
        self.assertEqual(result["ownerWasiTests"],22)
        self.assertEqual(result["browserTests"],15)
if __name__=="__main__":unittest.main()
