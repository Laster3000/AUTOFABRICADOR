"""C# safe compile-only, no generated assembly execution or fake acceptance."""
import os,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from autofab import csharp_compile,csharp_jobs,engine
from autofab.isolation import IsolationUnavailable

class CsharpCompileContract(unittest.TestCase):
    def test_compilation_never_means_functional_pass(self):
        try:csharp_compile.preflight(Path(__file__).resolve().parents[1])
        except IsolationUnavailable:self.skipTest("Optional system .NET SDK not installed")
        result=csharp_compile.compile_only(Path(__file__).resolve().parents[1],
           {"hello.cs":"using System;\npublic static class Hello { public static int Double(int n) => n*2; }\n"})
        self.assertEqual(result["status"],"COMPILED_UNEXECUTED")
        self.assertEqual(result["functionalTests"],0)
        self.assertIs(result["noAssemblyExecuted"],True)
        self.assertEqual(len(result["assemblySha256"]),64)

    def test_csharp_path_traversal_denied_before_compile(self):
        try:csharp_compile.preflight(Path(__file__).resolve().parents[1])
        except IsolationUnavailable:self.skipTest("Optional .NET SDK missing")
        with self.assertRaisesRegex(ValueError,"SOURCE_FILENAME_UNSAFE"):
            csharp_compile.compile_only(Path(__file__).resolve().parents[1],
              {"../../evil.cs":"public static class Evil { }\n"})

    def test_csharp_script_directives_denied(self):
        try:csharp_compile.preflight(Path(__file__).resolve().parents[1])
        except IsolationUnavailable:self.skipTest("Optional .NET SDK missing")
        with self.assertRaisesRegex(ValueError,"REFERENCE_DIRECTIVES_FORBIDDEN"):
            csharp_compile.compile_only(Path(__file__).resolve().parents[1],
             {"script.cs":"#r \"evil.dll\"\npublic static class Test { }\n"})

    def test_no_functional_acceptance_from_csharp_status(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            engine.init(root)
            (root/"csharpjobs"/"AC-1234567890abcdef").mkdir(parents=True)
            from autofab.storage import write_json
            write_json(root/"csharpjobs"/"AC-1234567890abcdef"/"state.json",
                 {"schema":1,"status":"COMPILED_UNEXECUTED"})
            from autofab.storage import event
            event(root/"csharpjobs"/"AC-1234567890abcdef"/"journal.jsonl","FIXTURE",{})
            self.assertFalse(csharp_jobs.inspect(root,"AC-1234567890abcdef")["functionalAcceptanceProven"])

if __name__=="__main__":
    unittest.main()
