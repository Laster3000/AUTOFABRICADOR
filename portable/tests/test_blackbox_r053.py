"""R053 blackbox originality, adversarial integrity, SHA chain, no raw prompts."""
from __future__ import annotations
import tempfile,unittest,json
from pathlib import Path
from autofab import blackbox
from autofab.storage import load,sha_file,verify_journal

class BlackBoxOriginalOwnerBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="R053-BLACKBOX-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"owner-original.json"
        self.source.write_text(json.dumps({"status":"PASS","marker":"frozen_before_model"}),
                               encoding="utf-8")
        self.cases=[
         {"id":"original_owner","domain":"original-receipt","expect":"PASS",
          "description":"original independently SHA pinned acceptance"},
         {"id":"traversal_guard","domain":"safety","expect":"REJECT",
          "description":"reject untrusted traversal"},
        ]
        self.session=blackbox.create(self.root,self.cases,objective="Bounded exhaustive adversarial software factory blackbox checks")
        self.ident=self.session["sessionId"]
    def test_report_verified_with_original_sha(self):
        a=blackbox.record(self.root,self.ident,"original_owner",actual="PASS",
             detail="FIRST_PARTY_FROZEN",evidence=[self.source],duration_ms=8)
        self.assertTrue(a["matchesExpected"])
        blackbox.record(self.root,self.ident,"traversal_guard",actual="REJECT",
             detail="PATH_DENIED")
        final=blackbox.finalize(self.root,self.ident)
        self.assertEqual(final["status"],"MEASURED_ALL_EXPECTATIONS")
        self.assertEqual(final["matched"],2)
        verified=blackbox.verify(self.root,self.ident)
        self.assertEqual(verified["status"],"BLACKBOX_ALL_RECORDED_SHA_VERIFIED")
        folder=self.root/"blackbox"/self.ident
        self.assertEqual(verify_journal(folder/"events.jsonl")["events"],4)
        self.assertEqual(load(folder/"cases/original_owner.json")["evidence"][0]["sha"],
                         sha_file(self.source))
    def test_failing_case_never_claims_full_pass(self):
        blackbox.record(self.root,self.ident,"original_owner",
            actual="FAIL",detail="ORIGINAL_OWNER_REJECTED",evidence=[self.source])
        final=blackbox.finalize(self.root,self.ident)
        self.assertEqual(final["status"],"MIXED_OR_INCOMPLETE")
        self.assertIn("original_owner",load(self.root/"blackbox"/self.ident/"report.json")["caseIdsNotMeetingExpectation"])
    def test_evidence_tampering_detected(self):
        blackbox.record(self.root,self.ident,"original_owner",
             actual="PASS",detail="ORIGINAL_OWNER_SHA",evidence=[self.source])
        blackbox.record(self.root,self.ident,"traversal_guard",
             actual="REJECT",detail="PATH_DENIED")
        blackbox.finalize(self.root,self.ident)
        self.source.write_text("tampered",encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"EVIDENCE_SHA_DRIFT"):
            blackbox.verify(self.root,self.ident)
    def test_no_duplicate_no_replay(self):
        blackbox.record(self.root,self.ident,"original_owner",
              actual="PASS",detail="FIRST_ORIGINAL")
        with self.assertRaises((FileExistsError,RuntimeError)):
            blackbox.record(self.root,self.ident,"original_owner",
               actual="PASS",detail="REPLAY_ATTEMPT")
        blackbox.finalize(self.root,self.ident)
        with self.assertRaisesRegex(RuntimeError,"FINALIZED"):
            blackbox.record(self.root,self.ident,"traversal_guard",
             actual="REJECT",detail="WRITTEN_AFTER_FINAL")
    def test_unknown_case_and_injection_rejected(self):
        with self.assertRaisesRegex(ValueError,"NOT_FROZEN"):
            blackbox.record(self.root,self.ident,"inject_another",
                            actual="PASS",detail="SPOOFED")
        with self.assertRaisesRegex(ValueError,"OUTCOME_UNCLASSIFIED"):
            blackbox.record(self.root,self.ident,"original_owner",
                            actual="FAKE_SUCCESS",detail="SPOOFED")
        with self.assertRaisesRegex(ValueError,"EVIDENCE_MUST_BE_ORIGINAL"):
            blackbox.record(self.root,self.ident,"original_owner",
                            actual="PASS",detail="UNTRUSTED_PATH",
                            evidence=[self.root.parent/"not-within.json"])
    def test_duplicate_case_plan_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_UNSAFE"):
            blackbox.create(self.root,[self.cases[0],self.cases[0]],
                            objective="Bounded exhaustive adversarial software factory blackbox checks")
    def test_ambiguous_case_ids_rejected(self):
        with self.assertRaises(ValueError):
            blackbox.create(self.root,[{"id":"..\\etc","domain":"test",
                         "expect":"PASS","description":"bad"}],
                         objective="Bounded exhaustive adversarial software factory blackbox checks")
    def test_unchanged_existing_original_evidence(self):
        original_sha=sha_file(self.source)
        blackbox.record(self.root,self.ident,"original_owner",
             actual="PASS",detail="HASH_ONLY",evidence=[self.source])
        self.assertEqual(original_sha,sha_file(self.source))
        self.assertNotIn("frozen_before_model",
            (self.root/"blackbox"/self.ident/"cases/original_owner.json").read_text("utf-8"))
