"""JS/TS generated source actually runs only inside bounded Wasmtime guest."""
import json,os
from pathlib import Path
import unittest
from autofab import js_wasi
from autofab.isolation import IsolationUnavailable

ROOT=Path(__file__).resolve().parents[1]

class JsWasiContract(unittest.TestCase):
    def test_stable_owner_test_harness(self):
        text=js_wasi.owner_harness("add",[{"args":[2,3],"expected":5}]*5)
        self.assertIn("AF_WASI_JS_ACCEPTANCE",text)
        self.assertIn("const __af_fn=add;",text)

    def test_untrusted_function_name_rejected(self):
        with self.assertRaisesRegex(ValueError,"FUNCTION_NAME_UNSAFE"):
            js_wasi.owner_harness("process.exit(0)",[{"args":[],"expected":0}]*5)

    def test_preflight_blocks_missing_vendor_without_download(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(IsolationUnavailable):
                js_wasi.preflight(Path(t),"javascript")

    def test_unknown_language_is_not_silently_accepted(self):
        with self.assertRaises(IsolationUnavailable):
            js_wasi.preflight(ROOT,"csharp")

    def test_actual_guest_has_no_node_process_require_fetch(self):
        try:js_wasi.preflight(ROOT,"javascript")
        except IsolationUnavailable:self.skipTest("Pinned Javy/Wasmtime are optional external dependencies")
        source={"probe.js":"function probe(){ return [typeof require,typeof process,typeof fetch].join(','); }\n"}
        cases=[{"args":[],"expected":"undefined,undefined,undefined"}]*5
        report=js_wasi.execute(ROOT,"javascript",source,"probe",cases)
        self.assertEqual(report["status"],"PASS")
        self.assertEqual(report["independentTestCount"],5)
        self.assertEqual(report["trust"]["networkGrants"],0)
        self.assertEqual(report["trust"]["hostFilesystemGrants"],0)

    def test_wrong_owner_acceptance_cannot_pass(self):
        try:js_wasi.preflight(ROOT,"javascript")
        except IsolationUnavailable:self.skipTest("Pinned Javy/Wasmtime are optional external dependencies")
        source={"sum.js":"function sum(a,b){return a+b;}\n"}
        cases=[{"args":[1,1],"expected":200}]*5
        report=js_wasi.execute(ROOT,"javascript",source,"sum",cases)
        self.assertEqual(report["status"],"FAILED_OWNER_ACCEPTANCE")
        self.assertNotEqual(report["exitCode"],0)

    def test_untrusted_guest_infinite_loop_exhausts_fuel(self):
        try:js_wasi.preflight(ROOT,"javascript")
        except IsolationUnavailable:self.skipTest("Pinned Javy/Wasmtime are optional external dependencies")
        source={"loop.js":"function forever(){while(true){} return 42;}\n"}
        cases=[{"args":[],"expected":42}]*5
        report=js_wasi.execute(ROOT,"javascript",source,"forever",cases)
        self.assertNotEqual(report["status"],"PASS")
        self.assertNotEqual(report["exitCode"],0)
        self.assertGreater(report["fuelConsumed"],0)

if __name__=="__main__":
    unittest.main()
