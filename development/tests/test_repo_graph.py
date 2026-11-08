"""Real ESM graph compiler uses no source execution in native Windows Node."""
from pathlib import Path
from unittest import TestCase
import tempfile,json
from autofab import repo_graph
from autofab.isolation import IsolationUnavailable
from autofab.storage import load
class RepoGraphTests(TestCase):
 def spec(self):
  return {"schema":1,"language":"javascript","goal":"Return twice the integer argument from actual two source modules with exports and relative imports.","entry":"src/main.js","exportName":"double","sources":{
    "src/main.js":"import {sum} from './math.js';export function double(n){return sum(n,n)};\n",
    "src/math.js":"export function sum(a,b){return a+b};\n"},
   "acceptance":[{"args":[k],"expected":2*k} for k in [-5,-1,0,1,2,7]],
   "dependencies":[]}
 def test_rejects_non_owner_files(self):
  spec=self.spec()
  extra=dict(spec["sources"]);extra["../windows.js"]="export function x(){return 1};\n"
  spec["sources"]=extra
  with self.assertRaisesRegex(ValueError,"SOURCE_PATH_INVALID"):
   repo_graph._valid_spec(spec)
 def test_rejects_dangerous_npm(self):
  spec=self.spec();spec["dependencies"]=["child_process"]
  with self.assertRaisesRegex(ValueError,"UNPINNED_NPM"):
   repo_graph._valid_spec(spec)
 def test_rejects_dynamic_import_or_host_commands(self):
  with self.assertRaisesRegex(ValueError,"DYNAMIC_IMPORT"):
   repo_graph._static_source_guard({"src/a.js":"export function f(){return import('fs')}\n"})
  with self.assertRaisesRegex(ValueError,"REQUIRE_IMPORT"):
   repo_graph._static_source_guard({"src/a.js":"export function f(){return require('fs')}\n"})
 def test_rejects_missing_owner_cases(self):
  spec=self.spec();spec["acceptance"]=[]
  with self.assertRaisesRegex(ValueError,"OWNER_TEST_COUNT"):
   repo_graph._valid_spec(spec)
 def test_real_original_wasm_bundle_guest(self):
  root=Path(__file__).resolve().parents[1]
  if not (root/"MODULE-BUNDLER.lock.json").is_file():
   self.skipTest("Pin sources not shipped in small portable source ZIP")
  try:repo_graph.preflight(root)
  except IsolationUnavailable:self.skipTest("Vetted esbuild-wasm and Wasmtime not installed in this restore")
  result=repo_graph.build_owner(root,self.spec(),self.spec()["sources"])
  self.assertEqual(result["status"],"PASS")
  self.assertEqual(result["ownerCaseCount"],6)
  self.assertTrue(result["compiledSha256"])
  self.assertFalse(result["modelCodeRanOnNode"])
  self.assertEqual(result["compileReceipt"]["moduleCount"],2)
if __name__=="__main__":
 import unittest;unittest.main()
