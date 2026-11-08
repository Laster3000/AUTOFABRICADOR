"""Reject ZIP traversal, executable npm scripts and unapproved dependency graph."""
from pathlib import Path
from unittest import TestCase
import tempfile,zipfile,json
from autofab import repo_archive
class RepoArchiveTests(TestCase):
 def setUp(self):
  root=Path(__file__).resolve().parents[1]
  if not (root/"VENDOR/module-bundler/package/esbuild.wasm").is_file():
   self.skipTest("Private vetted compiler not included in small source-only restore")
 def test_invalid_package_json_scripts_rejected(self):
  root=Path(__file__).resolve().parents[1]
  source=root/"examples/repo_sales_esm_dayjs.json"
  if not source.is_file():self.skipTest("No real owner example in restored source")
  spec=json.loads(source.read_text("utf-8"))
  with tempfile.TemporaryDirectory() as tmp:
   z=Path(tmp)/"unsafe.zip"
   with zipfile.ZipFile(z,"w") as out:
    for rel,code in spec["sources"].items():out.writestr(rel,code)
    out.writestr("package.json",json.dumps({"name":"unsafe-repo","type":"module",
     "private":True,"dependencies":{"dayjs":"1.11.13"},
     "scripts":{"postinstall":"echo bad"}}))
   with self.assertRaisesRegex(ValueError,"LIFECYCLE_OR_CONFIG"):
    repo_archive.inspect(root,z,source)
 def test_zip_traversal_rejected(self):
  root=Path(__file__).resolve().parents[1]
  source=root/"examples/repo_sales_esm_dayjs.json"
  if not source.is_file():self.skipTest("No owner fixture")
  spec=json.loads(source.read_text("utf-8"))
  with tempfile.TemporaryDirectory() as tmp:
   z=Path(tmp)/"escape.zip"
   with zipfile.ZipFile(z,"w") as out:
    for rel,code in spec["sources"].items():out.writestr(rel,code)
    out.writestr("../evil.js","do not import this")
    out.writestr("package.json",json.dumps({"name":"safe-repo","type":"module",
    "private":True,"dependencies":{"dayjs":"1.11.13"}}))
   with self.assertRaisesRegex(ValueError,"PATH_SYMLINK_SIZE_UNSAFE"):
    repo_archive.inspect(root,z,source)
 def test_wrong_npm_pin_rejected(self):
  root=Path(__file__).resolve().parents[1]
  source=root/"examples/repo_sales_esm_dayjs.json"
  if not source.is_file():self.skipTest("No owner fixture")
  spec=json.loads(source.read_text("utf-8"))
  with tempfile.TemporaryDirectory() as tmp:
   z=Path(tmp)/"unpin.zip"
   with zipfile.ZipFile(z,"w") as out:
    for rel,code in spec["sources"].items():out.writestr(rel,code)
    out.writestr("package.json",json.dumps({"name":"unsafe-repo","type":"module",
      "private":True,"dependencies":{"dayjs":"latest"}}))
   with self.assertRaisesRegex(ValueError,"PIN_VERSION"):
    repo_archive.inspect(root,z,source)
if __name__=="__main__":
 import unittest;unittest.main()
