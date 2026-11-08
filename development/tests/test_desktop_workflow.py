# coding: utf-8
"""Independent plan policy, owner scope, model trust boundary and app UI E2E."""
import json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from autofab import desktop_requirements as r,desktop_workflow as w,desktop_installer as i
from autofab.storage import json_bytes,sha_bytes

ROOT=Path(__file__).resolve().parent.parent
GOAL="Construye una aplicación de escritorio para gestionar pedidos con interfaz visual, base de datos persistente; crear, editar, eliminar, buscar y filtros; exportación CSV, instalador y desinstalador, sin red, en local."

class DesktopIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-desktop-owner-workflow-")
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
    def test_goal_requirements_compiled_independently(self):
        result=r.compile(GOAL)
        self.assertEqual(result["status"],"FROZEN_FIRST_PARTY_DESKTOP_ORDERS_SCOPE")
        self.assertFalse(result["modelGeneratedTests"])
        self.assertFalse(result["modelMayModifyTrustedTemplates"])
        self.assertEqual(len(result["features"]),12)
    def test_foreign_authority_fail_closed(self):
        for attempt in (
          GOAL+" Integra correo electrónico y pagos bancarios.",
          GOAL+" Incluye OAuth con inicio de sesión.",
          "Construye un sistema operativo desde cero.",
          "Escribe un poema corto.",
        ):
            with self.subTest(attempt=attempt):
                self.assertEqual(r.compile(attempt)["status"],
                  "BLOCKED_INDEPENDENT_REQUIREMENTS_NOT_COMPLETE")
    def test_missing_crud_feature_blocked(self):
        for text in ("crear, ","editar, ","eliminar, ","exportación CSV, "):
            with self.subTest(missing=text):
                self.assertIn(r.compile(GOAL.replace(text,""))["status"],
                    ("BLOCKED_INDEPENDENT_REQUIREMENTS_NOT_COMPLETE",))
    def test_negated_feature_blocked(self):
        problem=GOAL+" No crear pedidos y sin interfaz."
        s=r.compile(problem)
        self.assertIn("create",s["negatedFeatures"])
        self.assertIn("desktop_gui",s["negatedFeatures"])
    def test_model_plan_never_omits_first_party_features(self):
        scope=r.compile(GOAL)
        intent={"originalScope":scope,"goalText":GOAL}
        proposal={
          "implementationProfile":w.PROFILE,
          "appName":"Gestor interno de pedidos",
          "featureCoverage":scope["features"],
          "steps":["Crear esquema SQLite con integridad",
                   "Preparar formularios de altas y cambios",
                   "Incluir filtros y búsquedas locales",
                   "Exportar filas seleccionadas a CSV",
                   "Probar y preparar instalador local"],
          "safety":"CURRENT_USER_NO_NETWORK_NO_MODEL_HOST_EXEC"
        }
        self.assertEqual(w._validate_model_plan(json.dumps(proposal),intent),proposal)
        proposal["featureCoverage"]=scope["features"][:-1]
        with self.assertRaisesRegex(ValueError,"FROZEN_CAPABILITY"):
            w._validate_model_plan(json.dumps(proposal),intent)
        proposal["featureCoverage"]=scope["features"]
        proposal["newPermission"]="SYSTEM"
        with self.assertRaisesRegex(ValueError,"KEYS"):
            w._validate_model_plan(json.dumps(proposal),intent)
    def test_user_goal_path_cannot_escape_entradas(self):
        (self.home/"ENTRADAS").mkdir()
        goal=(self.home/"ENTRADAS"/"job.txt")
        goal.write_text(GOAL,encoding="utf-8")
        self.assertTrue(r.source(self.home,goal)[3].startswith("DW-"))
        other=self.home/"other.txt"
        other.write_text(GOAL,encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"ENTRADAS"):
            r.source(self.home,other)
    def test_real_trusted_gui_sqlite_and_temp_user_install(self):
        intent={"appId":"AFD-69db24718e53ac40",
                "trustedTemplateSha":w._trusted(ROOT),
                "originalGoalSha":"c"*64}
        files=w._artifact_files(ROOT,intent)
        self.assertEqual(set(files),i._ALLOWED)
        owner={"schema":1,"appId":intent["appId"],"profile":w.PROFILE,
               "execSource":"ORIGINAL_FIRST_PARTY_TRUSTED_TEMPLATES_ONLY",
               "modelCodeOnWindowsHost":False,
               "files":{name:{"size":len(b),"sha256":sha_bytes(b)} for name,b in files.items()}}
        archive=self.home/"first-party-app.zip"
        with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
            for name,b in files.items():z.writestr(name,b)
            z.writestr("MANIFEST.json",json_bytes(owner))
        test=subprocess.run(
            [sys.executable,"-B",str(ROOT/"qa/desktop_acceptance.py"),
             str(ROOT),str(archive),str(ROOT)],
            cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,text=True,
            timeout=90)
        if test.returncode:
            self.fail("Desktop owner UI QA failed: "+test.stderr[-2000:])
        result=json.loads(test.stdout)
        self.assertEqual(result["status"],"PASS_INDEPENDENT_DESKTOP_GUI_SQLITE_INSTALL_QA")
        self.assertGreaterEqual(result["cases"],18)
        self.assertTrue(result["realGUIControlsExercised"])
        self.assertFalse(result["physicalWindowsOSRebootProven"])
        self.assertFalse(result["cleanDifferentHostInstallProven"])

if __name__=="__main__":unittest.main()
