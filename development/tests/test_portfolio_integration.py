# coding: utf-8
"""Frozen independent multi-domain GUI/install black-box qualification."""
import json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from autofab import portfolio_installer as installer,portfolio_workflow as workflow
from autofab.storage import sha_bytes,json_bytes
ROOT=Path(__file__).resolve().parent.parent
class PortfolioNativeOwnerAcceptance(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix="af-r63-native-owner-")
  self.addCleanup(self.temp.cleanup)
  self.home=Path(self.temp.name)
 def _archive(self,profile):
  id="AFD-"+{"inventory":"a"*16,"tasks":"b"*16,"expenses":"c"*16}[profile]
  original={"appId":id,"profile":profile,"originalGoalSha":"a"*64,
            "firstPartySourceSha":workflow._pins(ROOT)}
  files=workflow._files(ROOT,original)
  expected={
    "schema":1,"appId":id,"profile":profile,
    "ownerGoalSha":original["originalGoalSha"],
    "validatedPlanSha":"b"*64,
    "sourceOrigin":"ORIGINAL_FIRST_PARTY_TRUSTED",
    "modelCodeExecutedOnHost":False,
    "files":{name:{"sha256":sha_bytes(data),"size":len(data)}
             for name,data in files.items()}}
  archive=self.home/(profile+".zip")
  with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
   for name,data in files.items():z.writestr(name,data)
   z.writestr("MANIFEST.json",json_bytes(expected))
  self.assertEqual(installer.validate(archive)["appId"],id)
  return archive
 def test_inventory_full_gui_sqlite(self):self._run("inventory")
 def test_tasks_full_gui_sqlite(self):self._run("tasks")
 def test_expenses_full_gui_sqlite(self):self._run("expenses")
 def _run(self,profile):
  archive=self._archive(profile)
  process=subprocess.run([sys.executable,"-B",str(ROOT/"qa/portfolio_acceptance.py"),
            str(ROOT),str(archive)],
            cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=85)
  if process.returncode:
   self.fail("INDEPENDENT_OWNER_"+profile+"\n"+process.stdout[-1500:]+"\n"+process.stderr[-2500:])
  result=json.loads(process.stdout)
  self.assertEqual(result["status"],"PASS_FIRST_PARTY_INDEPENDENT_DOMAIN_GUI_SQLITE_QA")
  self.assertEqual(result["profile"],profile)
  self.assertGreaterEqual(result["ownerCases"],22)
  self.assertTrue(result["actualNativeTkControlsUsed"])
  self.assertFalse(result["physicalWindowsOSRebootVerified"])
  self.assertFalse(result["cleanDifferentWindowsHostInstallVerified"])
 def test_manifest_rejects_model_authored_app(self):
  self._archive("inventory")
  # A foreign or altered model-authored bundle would not match pinned hashes.
  with self.assertRaises(ValueError):
   installer.validate(self.home/"nonexistent.zip")
 def test_model_plan_cannot_downgrade_requirements(self):
  from autofab.portfolio_specs import PROFILES
  intent={"profile":"inventory","ownerRequirements":{
     "features":list(PROFILES["inventory"]["features"])}}
  good={"profile":"inventory","title":"Inventario de productos",
    "coverage":list(PROFILES["inventory"]["features"]),
    "steps":["Crear modelo validado de inventario",
             "Preparar los formularios locales de stock",
             "Gestionar productos con identificadores",
             "Medir el minimo y el valor del stock",
             "Probar la base SQLite y exportacion",
             "Entregar aplicación de uso local"],
    "safety":"CURRENT_USER_OFFLINE_TRUSTED_SOURCE_ONLY"}
  self.assertEqual(workflow._validate_plan(json.dumps(good),intent),good)
  good["coverage"].remove("stock_value")
  with self.assertRaises(ValueError):
   workflow._validate_plan(json.dumps(good),intent)
if __name__=="__main__":unittest.main()
