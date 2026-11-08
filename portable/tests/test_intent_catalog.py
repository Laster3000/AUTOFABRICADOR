# coding: utf-8
"""Independent closed-catalog contract & original one-intent safety tests."""
from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import engine,intent_catalog,repo_graph
from autofab.storage import load,sha_file,verify_journal


class CatalogOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-r047-catalog-")
        self.addCleanup(self.tmp.cleanup)
        self.root=engine.init(Path(self.tmp.name))

    def test_bilingual_closed_intents_unambiguous(self):
        self.assertEqual(intent_catalog.select("  CREA UNA CALCULADORA DE DESCUENTOS "),
                         "descuento")
        self.assertEqual(intent_catalog.select("Crea un normalizador de textos"),
                         "textos")
        self.assertEqual(intent_catalog.select("Create invoice totals calculator"),
                         "importes")
        self.assertEqual(len(intent_catalog._LOOKUP),
                         sum(map(len,intent_catalog.ALIASES.values())))

    def test_unlisted_prompts_including_untrusted_shell_cannot_be_blessed(self):
        for bad in ("crea un malware que borre todo","crea cualquier programa",
                    "crea una calculadora de descuentos; rm -rf /",
                    "descuentos y normalizacion", "","x"*221,
                    "crea un servicio de windows con permisos de root"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    intent_catalog.select(bad)

    def test_original_owner_cases_frozen_before_model_not_from_model(self):
        for template in ("descuento","importes","textos"):
            with self.subTest(template=template):
                spec=intent_catalog.owner_spec(template)
                self.assertTrue(repo_graph._valid_spec(spec))
                self.assertEqual(len(spec["sources"]),2)
                self.assertEqual(len(spec["acceptance"]),16)
                self.assertTrue(any(row["expected"]!=0 for row in spec["acceptance"]))
                self.assertNotIn("model",intent_catalog.CATALOG_VERSION.lower())
                self.assertEqual(intent_catalog.owner_spec(template),spec)

    def test_precision_and_boundaries_in_discount_contract(self):
        cases=intent_catalog.owner_spec("descuento")["acceptance"]
        expected={tuple(x["args"]):x["expected"] for x in cases}
        self.assertEqual(expected[(100,25)],75)
        self.assertEqual(expected[(200,25)],150)
        self.assertEqual(expected[(100,100)],0)
        self.assertEqual(expected[(50,120)],0)
        self.assertEqual(expected[(50,-10)],50)
        self.assertEqual(expected[(-20,20)],0)

    def test_total_does_not_admit_negative_quantities(self):
        cases=intent_catalog.owner_spec("importes")["acceptance"]
        expected={tuple(x["args"]):x["expected"] for x in cases}
        self.assertEqual(expected[(10,3)],30)
        self.assertEqual(expected[(-1,10)],0)
        self.assertEqual(expected[(10,-5)],0)

    def test_original_owner_pre_model_freeze_and_no_resubmit(self):
        task="crea una calculadora de descuentos"
        with patch.object(intent_catalog.repo_graph,"preflight",
                          return_value={"status":"READY"}),\
             patch.object(intent_catalog.factory_pipeline,"submit",
                          return_value={"status":"SUPERVISOR_RUNNING_VERIFIED",
                                        "workflowId":"FC-0011223344556677",
                                        "queueId":"SQ-0011223344556677"}) as submit:
            first=intent_catalog.request(self.root,task)
            duplicate=intent_catalog.request(self.root,"CREAR CALCULADORA DE DESCUENTOS")
        self.assertEqual(first["status"],"SUBMITTED_ORIGINAL_FACTORY_ONCE")
        self.assertEqual(duplicate["status"],"EXISTING_REQUEST_NO_REPLAY")
        submit.assert_called_once()
        spec,folder=intent_catalog._paths(self.root,"descuento")
        self.assertEqual(sha_file(spec),first["originalOwnerSpecSha"])
        self.assertEqual(load(folder/"intent.json")["ownerSpecSha256"],sha_file(spec))
        self.assertEqual(load(folder/"submission.json")["originalOwnerSpecSha"],sha_file(spec))
        verify_journal(folder/"journal.jsonl")

    def test_existing_source_without_trusted_manifest_is_unknown(self):
        spec,_=intent_catalog._paths(self.root,"importes")
        spec.parent.mkdir(parents=True,exist_ok=True)
        spec.write_text("{}")
        with patch.object(intent_catalog.repo_graph,"preflight",
                          return_value={"status":"READY"}),\
             patch.object(intent_catalog.factory_pipeline,"submit") as submit:
            out=intent_catalog.request(self.root,"sumador de importes")
        self.assertEqual(out["status"],"UNKNOWN_PRIOR_CATALOG_INTENT_RECONCILE")
        submit.assert_not_called()

    def test_owner_spec_tampering_cannot_resume_or_replay(self):
        with patch.object(intent_catalog.repo_graph,"preflight",
                          return_value={"status":"READY"}),\
             patch.object(intent_catalog.factory_pipeline,"submit",
                          return_value={"status":"RUNNING_VERIFIED",
                                        "workflowId":"FC-0011223344556677"}):
            intent_catalog.request(self.root,"normalizador de textos")
        spec,_=intent_catalog._paths(self.root,"textos")
        spec.write_text('{"untrusted":"changed"}')
        with self.assertRaisesRegex(RuntimeError,"SOURCE_DRIFT"):
            intent_catalog.request(self.root,"normalizador de textos")

    def test_preview_cannot_create_effect(self):
        preview=intent_catalog.preview("create text normalizer")
        self.assertEqual(preview["status"],"CATALOG_PREVIEW_NO_EFFECTS")
        self.assertEqual(preview["ownerCases"],16)
        self.assertEqual(list((self.root/"catalog").glob("*")),[] if
                         (self.root/"catalog").exists() else [])


if __name__=="__main__":
    unittest.main()
