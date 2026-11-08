"""R053 original static/Windows edge hardening regression (no model execution)."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from autofab import repo_graph,windows_sandbox
from autofab.storage import safe_source

class R053SecurityRoundTwo(unittest.TestCase):
    def test_optional_bracket_process_denied(self):
        for danger in (
          "globalThis?.['process'].exit(1)",
          'globalThis?.["process"].env',
          "globalThis?.process.exit(1)",
          "process?.exit(1)",
          "globalThis['process'].exit(1)"
        ):
            with self.subTest(danger=danger):
                with self.assertRaisesRegex(ValueError,"FORBIDDEN|UNSUPPORTED"):
                    repo_graph._static_source_guard({
                       "src/index.js":"export function f(){ "+danger+"; return 2; }"})

    def test_windows_devices_not_names_for_host_python(self):
        with tempfile.TemporaryDirectory() as t:
            for name in ("CON.py","AUX.py","PRN.py","LPT1.py",
                         "COM1.py","NUL.py","lpt9.py","com9.py"):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(ValueError,"DEVICE|ESCAPE"):
                        safe_source(Path(t),name)

    def test_raw_empty_and_dot_segments_denied(self):
        with tempfile.TemporaryDirectory() as t:
            for name in ("a/./b.py","x//b.py",
                         "a/../b.py","..\\evil.py","x.py:ads"):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        safe_source(Path(t),name)

    def test_safe_nested_python_sources_still_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            for name in ("snake.py","a/normal.py","a/b/valid.py"):
                with self.subTest(name=name):
                    actual=safe_source(Path(t),name)
                    self.assertTrue(actual.is_relative_to(Path(t).resolve()))

    def test_real_sandbox_zip_path_rejections(self):
        for name in ("../escape.zip","CON.dll","aux.exe",
                     "foo\\bar.txt","a/./b.txt","C:/windows/file.txt"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    windows_sandbox._check_entry_name(name)

    def test_false_positive_conservative_guard_not_broken(self):
        for src in ("export function processText(x){return x.trim();}",
                    "export function progress(v){return v+1;}",
                    "export function idx(x){return x===2;}"):
            with self.subTest(source=src):
                repo_graph._static_source_guard({"src/x.js":src})

    def test_first_party_old_null_case_is_preserved(self):
        root=Path(__file__).resolve().parents[1]
        r=root/"examples/mega_js_collapse_runs_r053.json"
        if not r.exists():self.skipTest("Original independent R053 source spec not in this installation")
        from autofab.storage import load
        contract=load(r)
        self.assertTrue(any("\x00" in x for t in contract["acceptance"] for x in t["args"] if isinstance(x,str)))
        self.assertEqual(len(contract["acceptance"]),78)
