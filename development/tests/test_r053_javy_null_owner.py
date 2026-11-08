"""R053 independent real WASI proof for owner data containing NUL Unicode."""
from __future__ import annotations
import json,unittest
from pathlib import Path
from autofab import js_wasi
from autofab.isolation import IsolationUnavailable
from autofab.storage import sha_file,load

class OwnerHarnessAdversarialR053(unittest.TestCase):
    def test_frozen_null_and_unicode_cases_survive_real_javy(self):
        root=Path(__file__).resolve().parents[1]
        try:js_wasi.preflight(root,"javascript")
        except IsolationUnavailable:self.skipTest("Optional pinned Javy runtime absent from source-only archive")
        cases=[
          {"args":["x\x00\x00y"],"expected":"x\x00\x00y"},
          {"args":["\x00"],"expected":"\x00"},
          {"args":["👨‍🚀👨‍🚀"],"expected":"👨‍🚀👨‍🚀"},
          {"args":["\n\x00\r"],"expected":"\n\x00\r"},
          {"args":["a\\u0000b"],"expected":"a\\u0000b"},
          {"args":["中文\x00🙂"],"expected":"中文\x00🙂"},
          {"args":[None],"expected":None},
          {"args":[123],"expected":123}
        ]
        before=json.dumps(cases,sort_keys=True,ensure_ascii=True)
        harness=js_wasi.owner_harness("identity",cases)
        self.assertNotIn("\x00",harness)
        self.assertIn("JSON.parse(__af_json)",harness)
        verified=js_wasi.execute(root,"javascript",
              {"src.js":"function identity(v){ return v; }\n"},
              "identity",cases,timeout=75)
        self.assertEqual(verified["status"],"PASS",verified.get("compilerStderrTail"))
        self.assertEqual(verified["testCount"],len(cases))
        self.assertEqual(verified["testResult"]["passed"],len(cases))
        self.assertEqual(json.dumps(cases,sort_keys=True,ensure_ascii=True),before)
        self.assertEqual(verified["trust"]["networkGrants"],0)

    def test_historical_broken_original_owner_receipt_not_mutated(self):
        root=Path(__file__).resolve().parents[1]
        p=root/"repojobs/RJ-267632ae995143b1/attempts/A-01-owner.json"
        if not p.exists():self.skipTest("R053 original model failure not present in source checkout")
        before=sha_file(p)
        j=load(p)
        self.assertEqual(j["originalOwnerResult"]["status"],"FAILED_JAVY_COMPILE")
        self.assertEqual(j["originalOwnerResult"]["testCount"],0)
        self.assertEqual(before,sha_file(p))
