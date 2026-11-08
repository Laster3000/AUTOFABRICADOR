"""R056 actual observed Python local model failure: only safe re prefix admitted."""
import unittest
from pathlib import Path
from autofab import repair_bridge
class R056PythonRepairRealOutput(unittest.TestCase):
    def setUp(self):
        self.spec={"goal":"Repair slugfunc.py slugify_ascii(value) with re.sub for original owner",
                   "acceptance":{"relativePath":"examples/test_owner_py_slug_r053.py"}}
        self.source=(
          "def slugify_ascii(value):\n"
          "    if not isinstance(value, str):\n"
          "        return None\n"
          "    return value.lower().replace(r'[^a-z0-9]', '-').lstrip('-').rstrip('-')")
    def test_import_re_as_only_allowed_prefix(self):
        repaired,rule=repair_bridge._py_apply(self.spec,"import re\n\n"+self.source+"\n")
        self.assertIn("re.sub(r'[^a-z0-9]+'",repaired)
        self.assertIn("return ''",repaired)
        self.assertEqual(rule,"PY_LITERAL_STR_REPLACE_TO_ASCII_REGEX")
    def test_no_import_and_old_source_still_supported(self):
        repaired,_=repair_bridge._py_apply(self.spec,self.source)
        self.assertIn("import re",repaired)
    def test_import_alias_unauthorized(self):
        for expr in ("import re as alias","import os","import sys",
                     "import re, os","from os import system","import re\nimport os",
                     "x=1\nimport re"):
            with self.subTest(prefix=expr),self.assertRaises((ValueError,SyntaxError)):
                repair_bridge._py_apply(self.spec,expr+"\n\n"+self.source)
    def test_extra_payload_after_known_function_rejected(self):
        for postfix in ("\nprint('ran on host')","\nopen('x','w')",
                        "\nimport os","\ndef extra():\n    return 1"):
            with self.subTest(postfix=postfix),self.assertRaises(ValueError):
                repair_bridge._py_apply(self.spec,"import re\n"+self.source+postfix)
    def test_original_owner_sha_is_not_synthesized(self):
        p=Path(__file__).resolve().parents[1]/"examples/test_owner_py_slug_r053.py"
        from autofab.storage import sha_file
        self.assertEqual(sha_file(p),"c814fdbb1f3ddac8dddf7e76d1155d6c3cf4ff627ac6135e99d8de5118e7bc27")
