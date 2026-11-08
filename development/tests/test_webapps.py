"""First-party CSP webapp and browser E2E package receipts, no npm hooks."""
from pathlib import Path
import tempfile,unittest
from autofab import webapps
from autofab.storage import load
class WebAppTests(unittest.TestCase):
 def test_trusted_html_has_strict_csp_and_accessible_button(self):
  app={"language":"javascript","function":"triple","acceptance":[{"args":[5],"expected":15}]}
  html=webapps._page("AD-0123456789abcdef",app,{})
  self.assertIn("connect-src 'none'",html)
  self.assertIn('id="run"',html)
  self.assertIn('aria-live="polite"',html)
  self.assertNotIn('<script>eval',html)
 def test_name_must_not_escape_into_html(self):
  with self.assertRaisesRegex(ValueError,"FUNCTION_NAME_UNSAFE"):
   webapps._page("AD-0123456789abcdef",{"function":"</title><script>","acceptance":[{"args":[2],"expected":2}]},{})
 def test_original_browser_app_is_reverifiable(self):
  root=Path(__file__).resolve().parents[1]
  if not (root/"apps/AF-WEB-AD-d97a5e0f778944da.zip").is_file():
   self.skipTest("Host model-generated app is absent in source-only restore")
  result=webapps.verify(root,"AD-d97a5e0f778944da")
  self.assertTrue(result["verified"])
  self.assertEqual(result["originalBrowserTests"],11)
 def test_original_npm_browser_app_is_reverifiable(self):
  root=Path(__file__).resolve().parents[1]
  if not (root/"apps/AF-WEB-AL-11447b7cc20e45da.zip").is_file():
   self.skipTest("Host app ZIP absent in source-only restore")
  result=webapps.verify(root,"AL-11447b7cc20e45da")
  self.assertTrue(result["verified"])
  self.assertEqual(result["originalBrowserTests"],12)
if __name__=="__main__":unittest.main()
