"""C# WASI 0.2 trust boundaries and independent owner acceptance."""
from pathlib import Path
import unittest
from autofab import csharp_wasi,csharp_jobs
from autofab.isolation import IsolationUnavailable
ROOT=Path(__file__).resolve().parents[1]
CONTRACT={"class":"AfFixture.Calculation","method":"Double",
          "parameterTypes":["int"],"returnType":"int",
          "cases":[{"args":[v],"expected":v*2} for v in (-8,-2,0,1,2,7,99)]}

class CsharpWasiTests(unittest.TestCase):
    def test_contract_prepin_schema_valid(self):
        self.assertTrue(csharp_wasi.validate_contract(CONTRACT))
        src=csharp_wasi.harness(CONTRACT,"a"*32)
        self.assertIn("AF_CS_WASI_OWNER_"+"a"*32,src)
        self.assertIn("AfFixture.Calculation.Double",src)

    def test_path_and_type_injection_rejected(self):
        wrong={**CONTRACT,"class":"Environment.Exit(0)"}
        with self.assertRaisesRegex(ValueError,"CLASS_UNSAFE"):
            csharp_wasi.validate_contract(wrong)
        wrong={**CONTRACT,"parameterTypes":["object"]}
        with self.assertRaisesRegex(ValueError,"TYPES_UNSUPPORTED"):
            csharp_wasi.validate_contract(wrong)

    def test_csharp_previously_compiled_without_owner_cannot_be_retroactive_pass(self):
        original=ROOT/"csharpjobs/AC-aa1970e969314730"
        if not original.is_dir():self.skipTest("Prior original C# job exists only on project host")
        with self.assertRaisesRegex(RuntimeError,"CANNOT_RETROACTIVELY"):
            csharp_jobs.admit_wasi(ROOT,"AC-aa1970e969314730")

    def test_wasmtime_csharp_wasi_native_guest_pass(self):
        try:csharp_wasi.preflight(ROOT)
        except IsolationUnavailable:self.skipTest("Optional 3rd party componentize-dotnet runtime not present")
        code={"math.cs":"namespace AfFixture;\npublic static class Calculation { public static int Double(int n) => n * 2; }\n"}
        result=csharp_wasi.run(ROOT,code,CONTRACT)
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["independentTestCount"],7)
        self.assertTrue(result["noNativeAssemblyExecuted"])
        self.assertEqual(result["hostDirectoryGrants"],0)
        self.assertEqual(result["networkCapabilities"],0)

    def test_csharp_wasi_wrong_result_is_not_accepted(self):
        try:csharp_wasi.preflight(ROOT)
        except IsolationUnavailable:self.skipTest("Optional 3rd party componentize-dotnet runtime not present")
        code={"math.cs":"namespace AfFixture;\npublic static class Calculation { public static int Double(int n) => n; }\n"}
        result=csharp_wasi.run(ROOT,code,CONTRACT)
        self.assertEqual(result["status"],"FAILED_OWNER_ACCEPTANCE")
        self.assertFalse(result["ownerAcceptance"])
        self.assertNotEqual(result["guestExitCode"],0)

if __name__=="__main__":unittest.main()
