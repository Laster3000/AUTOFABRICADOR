# coding: utf-8
"""An internal model can SUGGEST a contract, never approve its own oracle."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autofab import owner_proposals as p

def draft():
    return {"exportName":"chargeTotal","argTypes":["number","integer"],
      "oracle":{"op":"mul","args":[
         {"op":"nonnegative","args":[{"op":"arg","index":0}]},
         {"op":"nonnegative","args":[{"op":"arg","index":1}]}]}}
def stream(text,done=True):
    return {"schema":1,"resultText":text,"done":done,"receivedChunks":2,
            "errors":[],"cancelObserved":False,"threadExited":True}

class ProposalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-proposal-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"ENTRADAS").mkdir()
        self.goal=self.root/"ENTRADAS"/"idea.txt"
        self.goal.write_text("Quiero una función local que calcule importe por unidades a partir de precio y cantidad no negativos.",encoding="utf-8")
    def test_readonly_preview_never_uses_gpu(self):
        with patch.object(p.local_cuda7b,"start") as gpu:
            x=p.preview(self.root,self.goal)
            gpu.assert_not_called()
        self.assertTrue(x["notIndependentOwnerAcceptance"])
        self.assertTrue(x["humanReviewRequired"])
        self.assertFalse(x["canRunAI"])
    def test_model_draft_exact_DSL_is_valid_but_never_independent_owner(self):
        spec=p._validate_candidate(draft(),"Calcula importe de inventario en el programa local.")
        self.assertEqual(spec["maxCases"],64)
        self.assertEqual(len(p.owner_oracles._make_cases(spec)),64)
    def test_unknown_operator_rejected(self):
        data=draft()
        data["oracle"]={"op":"powershell","args":[{"op":"const","value":1}]}
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED"):
            p._validate_candidate(data,"Calcular importe de inventario")
    def test_foreign_goal_path_disallowed(self):
        other=self.root/"bad.txt"
        other.write_bytes(self.goal.read_bytes())
        with self.assertRaisesRegex(ValueError,"ENTRADAS"):
            p.preview(self.root,other)
    def _run(self,message,model_state="READY"):
        with patch.object(p.supervisor,"status",return_value={"status":"RUNNING","pendingQueue":0}),\
             patch.object(p.local_cuda7b,"server_info",return_value={"state":model_state}),\
             patch.object(p.local_cuda7b,"pinned_assets",return_value={}),\
             patch.object(p.local_cuda7b,"start",return_value={"state":"READY"}) as start,\
             patch.object(p.local_cuda7b,"stop",return_value={"state":"STOPPED_VERIFIED"}) as stop,\
             patch.object(p.direct_agent,"_stream_text",return_value=message) as http,\
             patch.object(p.owner_oracles,"submit") as owner_dispatch:
            result=p.propose(self.root,self.goal)
            owner_dispatch.assert_not_called()
        return result,start,stop,http
    def test_valid_proposal_never_dispatches_without_owner_signoff(self):
        result,start,stop,http=self._run(stream(json.dumps(draft())))
        self.assertEqual(result["status"],"UNTRUSTED_DRAFT_REVIEW_REQUIRED")
        self.assertTrue(result["reviewRequired"])
        self.assertFalse(result["dispatchToOriginalFactory"])
        self.assertIsNotNone(result["untrustedDraftSha"])
        start.assert_not_called()
        stop.assert_not_called()
        assert not list((self.root/"ENTRADAS").glob("*.json"))
        with patch.object(p.local_cuda7b,"start") as gpu:
            again=p.propose(self.root,self.goal)
            gpu.assert_not_called()
        self.assertEqual(again["proposalId"],result["proposalId"])
    def test_invalid_oracle_is_review_not_acceptance(self):
        faulty={"exportName":"out","argTypes":["number"],
                "oracle":{"op":"shell","args":[]}}
        result,*_=self._run(stream(json.dumps(faulty)))
        self.assertEqual(result["status"],"UNTRUSTED_DRAFT_INVALID_REVIEW_REQUIRED")
        self.assertIsNone(result["untrustedDraftSha"])
    def test_incomplete_stream_terminal_unknown_no_replay(self):
        result,*_=self._run(stream('{"exportName":"x"}',done=False))
        self.assertEqual(result["status"],"UNKNOWN_INCOMPLETE_MODEL_NO_REPLAY")
        with patch.object(p.local_cuda7b,"start") as start:
            second=p.propose(self.root,self.goal)
            start.assert_not_called()
        self.assertEqual(second["status"],"UNKNOWN_INCOMPLETE_MODEL_NO_REPLAY")
    def test_owned_GPU_lease_stop_with_original_identity(self):
        result,start,stop,http=self._run(stream(json.dumps(draft())),model_state="NOT_STARTED")
        start.assert_called_once_with(self.root)
        stop.assert_called_once_with(self.root)
        self.assertEqual(result["status"],"UNTRUSTED_DRAFT_REVIEW_REQUIRED")
    def test_busy_original_supervisor_blocks_external_gpu(self):
        with patch.object(p.supervisor,"status",return_value={"status":"RUNNING","pendingQueue":1}),\
             patch.object(p.local_cuda7b,"start") as start:
            with self.assertRaisesRegex(RuntimeError,"BUSY"):
                p.propose(self.root,self.goal)
            start.assert_not_called()

if __name__=="__main__":unittest.main()
