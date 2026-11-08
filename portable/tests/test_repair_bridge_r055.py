"""R055 first-party hybrid repair unit boundaries; no model or untrusted Host eval."""
from __future__ import annotations
import unittest
from pathlib import Path
from autofab import repair_bridge
class HybridR055(unittest.TestCase):
    def test_dummy(self):
        self.assertTrue(repair_bridge._REPAIR.fullmatch("AR-0123456789abcdef"))
        self.assertFalse(repair_bridge._REPAIR.fullmatch("AR-../escape"))
    def test_ts_rewrite_exact_entry_and_preserve_others(self):
        spec={"schema":1,"language":"typescript","entry":"src/index.ts",
          "exportName":"describePort","dependencies":[],
          "sources":{"src/index.ts":"export function describePort(v: unknown): string {return 'bad';}",
           "src/normalize.ts":"export function normalizePort(x){return -1;}",
           "src/rules.ts":"export function isValidPort(x){return false;}"},
          "goal":"isValidPort normalizePort describePort 65535 and invalid output",
          "acceptance":[{"args":[x],"expected":"invalid"} for x in (None,False,True,-1,"1")]+
            [{"args":[x],"expected":"port:"+str(x)} for x in (1,80,65535,100,8080)]}
        files={
          "src/index.ts":"import {normalizePort} from './normalize'; export function describePort(value: unknown): string { return 'port:' + normalizePort(value); }",
          "src/normalize.ts":"import {isValidPort} from './rules'; export function normalizePort(v:unknown){return isValidPort(v) ? v : -1;}",
          "src/rules.ts":"export function isValidPort(v:unknown){return typeof v === 'number';}"}
        repaired,rule=repair_bridge._ts_apply(spec,files)
        self.assertIn("port === -1 ? 'invalid' : 'port:' + port",repaired["src/index.ts"])
        self.assertEqual(repaired["src/normalize.ts"],files["src/normalize.ts"])
        self.assertEqual(repaired["src/rules.ts"],files["src/rules.ts"])
        self.assertEqual(rule,"TS_ENTRY_SENTINEL_MINUS_ONE_TO_TYPED_STRING")
    def test_unrecognized_js_or_wrong_owner_denied(self):
        spec={"language":"javascript","goal":"isValidPort normalizePort describePort 65535 invalid",
          "entry":"src/index.ts","exportName":"describePort",
          "sources":{x:"broken" for x in repair_bridge._TSS},
          "acceptance":[{"args":[x],"expected":"invalid"} for x in range(6)]+
            [{"args":[x],"expected":"port:"+str(x)} for x in range(10,16)]}
        files={x:"export function normalizePort(x){return -1;}" for x in repair_bridge._TSS}
        with self.assertRaisesRegex(ValueError,"SPEC_NOT_SUPPORTED"):
            repair_bridge._ts_apply(spec,files)
    def test_python_corrects_literal_replace_and_wrong_type(self):
        spec={"goal":"slugfunc.py slugify_ascii regex","acceptance":{"relativePath":"examples/test_owner_py_slug_r053.py"}}
        for failed in (
          "def slugify_ascii(value):\n    if not isinstance(value, str):\n        return None\n    return value.lower().replace(r'[^a-z0-9]', '-').lstrip('-').rstrip('-')",
          "def slugify_ascii(value):\n    if not isinstance(value, str):\n        return None\n    return value.lower().replace(r'[^a-z0-9]+', '-', value.lower()).lstrip('-').rstrip('-')"
          ):
            with self.subTest(source=failed):
                good,why=repair_bridge._py_apply(spec,failed)
                self.assertIn("import re",good)
                self.assertIn("re.sub(",good)
                self.assertIn("return ''",good)
                self.assertEqual(why,"PY_LITERAL_STR_REPLACE_TO_ASCII_REGEX")
    def test_python_rejects_arbitrary_untrusted_statements(self):
        spec={"goal":"slugfunc.py slugify_ascii","acceptance":{"relativePath":"examples/test_owner_py_slug_r053.py"}}
        for source in ("import os\n"+'def slugify_ascii(value):\n    return os.system(value)',
                       'def slugify_ascii(value):\n    return eval(value)',
                       'def slugify_ascii(value):\n    return value.replace("abc","def")',
                       'def other(value):\n    return value'):
            with self.subTest(source=source),self.assertRaises(ValueError):
                repair_bridge._py_apply(spec,source)
