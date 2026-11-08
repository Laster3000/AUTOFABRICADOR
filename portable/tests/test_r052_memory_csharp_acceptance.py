"""R052 selective large model memory guard and original owner syntax tests."""
from __future__ import annotations
import json,os
from pathlib import Path
from unittest import TestCase,mock
from autofab import local_escalation,csharp_wasi
from autofab.storage import load,sha_file

class R052MemoryOwnerTests(TestCase):
    def test_escalation_rejects_insufficient_memory(self):
        with self.assertRaisesRegex(RuntimeError,"INSUFFICIENT_FREE_RAM"):
            local_escalation.memory_gate(available=7*1024**3)

    def test_escalation_passes_only_above_conservative_threshold(self):
        x=local_escalation.memory_gate(available=14*1024**3)
        self.assertEqual(x["status"],"ESCALATION_RAM_PREFLIGHT_PASS")
        self.assertGreaterEqual(x["availableBytes"],x["minimumBytes"])

    def test_no_model_sha_scan_or_spawn_if_ram_insufficient(self):
        with mock.patch.object(local_escalation,"memory_gate",
          side_effect=RuntimeError("ESCALATION_14B_INSUFFICIENT_FREE_RAM_NO_SPAWN")):
            with mock.patch.object(local_escalation,"pinned") as secret:
                with self.assertRaisesRegex(RuntimeError,"NO_SPAWN"):
                    local_escalation.start(Path("C:/no_source"))
                secret.assert_not_called()

    def test_real_first_party_csharp_acceptance_remains_frozen(self):
        root=Path(__file__).resolve().parents[1]
        spec=root/"examples/csharp_distinct_positives_r052.json"
        if not spec.exists():
            self.skipTest("R052 original independent C# contract not in this checkout")
        frozen=load(spec)
        self.assertTrue(csharp_wasi.validate_contract(frozen["acceptance"]))
        self.assertEqual(len(frozen["acceptance"]["cases"]),21)
        p=root/"csharpjobs/AC-41d34477f42d4097/WASI-ACCEPTED-MANIFEST.json"
        if not p.exists():
            self.skipTest("R052 true-model owner original receipt absent in portable ZIP")
        original=load(p)
        self.assertEqual(original["status"],"CANDIDATE_ACCEPTED_NOT_INSTALLED")
        self.assertEqual(original["ownerTestCount"],21)
        self.assertTrue(original["noNativeModelAssemblyOnHost"])
        self.assertEqual(original["ownerReceiptSha"],
          sha_file(p.parent/"owner-acceptance.json"))
