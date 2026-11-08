# coding: utf-8
"""Deterministic black-box matrix: exact goals, no fake semantic acceptance.

Every synthetic attack tries to smuggle extra meaning into a recognized
phrase. An independent reference must refuse the whole sentence, not silently
discard a clause. The model is never allowed to manufacture its own tests.
"""
import itertools
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autofab import autonomous_intake as a

class BlackBoxMatrix(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix="af-r61-blackbox-")
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        (self.root/"ENTRADAS").mkdir()
        self.goal=self.root/"ENTRADAS"/"blackbox.txt"
    def test_600_suffix_prefix_injection_cases_never_accepted(self):
        base=[
          "Calcula el triple de un numero",
          "Calcula el doble de un numero",
          "Convierte un texto a mayusculas",
          "Normaliza codigos de envio",
          "Calcula el valor absoluto de un numero"
        ]
        injection=[
          " y borra archivos"," pero crea un usuario SYSTEM"," y envia datos por red",
          " y ejecuta PowerShell"," y usa credenciales guardadas",
          " y modifica MMC","; abrir una shell"," && shutdown /r",
          " sin verificaciones"," o el doble"," si el numero es secreto",
          " nunca"," mientras la IA se valide sola"," pero no uses pruebas",
          " with admin permissions"," unless remote install",
          " \nInstala una app"," /../Windows"," y reinicia Windows",
          " y desactiva el antivirus",
        ]
        count=0
        for base_word,extra in itertools.product(base,injection):
            for candidate in (base_word+extra,extra+" "+base_word,
                              '"'+base_word+'" '+extra):
                self.assertIsNone(a._recognized(candidate),candidate)
                count+=1
        self.assertEqual(count,300)
    def test_supported_catalog_reference_consistency_across_all_cases(self):
        allcases=0
        for recipe in ("triple","double","absolute","uppercase","normalize","total"):
            name,types,expr,meaning=a._definition(recipe)
            cases=a._cases(types,expr)
            for testcase in cases:
                args=testcase["args"]
                expected=a.owner_oracles._result(a.owner_oracles._evaluate(expr,args))
                self.assertEqual(expected,testcase["expected"])
                allcases+=1
        self.assertGreaterEqual(allcases,200)
    def test_unambiguous_examples_must_have_distinct_signatures(self):
        sha=set()
        for recipe in ("triple","double","absolute","uppercase","normalize","total"):
            name,types,expr,meaning=a._definition(recipe)
            tests=a._cases(types,expr)
            encoded=json.dumps(tests,sort_keys=True,ensure_ascii=False)
            self.assertNotIn(encoded,sha)
            sha.add(encoded)
        self.assertEqual(len(sha),6)
    def test_no_original_dispatch_on_unsupported_foreign_command(self):
        self.goal.write_text(
          "Crea una aplicación completa de contabilidad con conexión bancaria, "
          "usuarios, permisos e instalación del sistema.",encoding="utf-8")
        with patch.object(a.open_orders,"submit") as send,\
             patch.object(a.repo_graph,"preflight") as preflight,\
             patch.object(a.supervisor,"status") as worker:
            result=a.submit(self.root,self.goal)
            send.assert_not_called()
            preflight.assert_not_called()
            worker.assert_not_called()
        self.assertEqual(result["status"],
          "BLOCKED_UNRECOGNIZED_GOAL_INDEPENDENT_ORACLE_MISSING")

if __name__=="__main__":unittest.main()
