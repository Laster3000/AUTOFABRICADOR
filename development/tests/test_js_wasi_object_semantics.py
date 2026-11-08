# coding: utf-8
"""Regression for original independent WASI owner: object key order not semantics."""
import unittest
from pathlib import Path
from autofab import js_wasi

ROOT=Path(r"C:\AUTOFABRICADOR")

class OriginalOwnerObjectSemantics(unittest.TestCase):
    def test_equivalent_object_property_order_is_accepted(self):
        source={"source.js":"function data(x){return {b:x+1,a:x};}"}
        cases=[{"args":[x],"expected":{"a":x,"b":x+1}} for x in (0,1,10)]
        result=js_wasi.execute(ROOT,"javascript",source,"data",cases)
        self.assertEqual(result["status"],"PASS",result["stdoutTail"])
        self.assertEqual(result["testResult"]["passed"],3)
    def test_mismatched_values_still_fail_independent_acceptance(self):
        source={"source.js":"function data(x){return {b:x+1,a:x};}"}
        cases=[{"args":[0],"expected":{"a":0,"b":1}},
               {"args":[1],"expected":{"a":1,"b":999}},
               {"args":[10],"expected":{"a":10,"b":11}}]
        result=js_wasi.execute(ROOT,"javascript",source,"data",cases)
        self.assertEqual(result["status"],"FAILED_OWNER_ACCEPTANCE")
        self.assertEqual(result["testResult"]["passed"],2)
        self.assertEqual(result["testResult"]["failed"][0]["i"],1)

if __name__=="__main__":unittest.main()
