"""R054 whole-system inventory tests: exact original states, no model calls."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import audit_inventory
from autofab.storage import write_json,load,sha_file

class InventoryR054(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="R054-INVENTORY-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for rel in ("work/AF-0001/state.json","work/AF-0002/state.json",
                    "repojobs/RJ-0001/state.json"):
            target=self.root/rel;target.parent.mkdir(parents=True,exist_ok=True)
        write_json(self.root/"work/AF-0001/state.json",{"status":"UNKNOWN"},new=True)
        write_json(self.root/"work/AF-0002/state.json",{"status":"PASS"},new=True)
        write_json(self.root/"repojobs/RJ-0001/state.json",{"status":"FAILED_OWNER_ACCEPTANCE"},new=True)
    def test_readonly_original_sha_and_counts(self):
        old=sha_file(self.root/"work/AF-0001/state.json")
        with (patch.object(audit_inventory.supervisor,"status",
                 return_value={"status":"STOPPED","pendingQueue":0}),
              patch.object(audit_inventory.local_runtime,"server_info",
                 return_value={"state":"NOT_STARTED"}),
              patch.object(audit_inventory,"_host_service",
                 return_value={"status":"HOST_SERVICES_ORIGINALLY_ENUMERATED","serviceCount":0})):
            outcome=audit_inventory.snapshot(self.root)
        self.assertEqual(outcome["originalJobStates"]["python"]["byOriginalState"]["UNKNOWN"],1)
        self.assertEqual(outcome["originalJobStates"]["python"]["byOriginalState"]["PASS"],1)
        self.assertEqual(outcome["originalJobStates"]["javascript_typescript_repositories"]["byOriginalState"]["FAILED_OWNER_ACCEPTANCE"],1)
        self.assertTrue(outcome["noHostEffects"] and outcome["neverClaimsActive"])
        self.assertEqual(old,sha_file(self.root/"work/AF-0001/state.json"))
    def test_missing_blackbox_never_inferred_as_pass(self):
        with (patch.object(audit_inventory.supervisor,"status",
                 return_value={"status":"STOPPED","pendingQueue":0}),
              patch.object(audit_inventory.local_runtime,"server_info",
                 return_value={"state":"NOT_STARTED"}),
              patch.object(audit_inventory,"_host_service",
                 return_value={"status":"UNKNOWN","serviceCount":None})):
            outcome=audit_inventory.snapshot(self.root)
        self.assertEqual(outcome["latestKnownOriginalBlackbox"]["integrity"],"NOT_IN_SOURCE_ONLY_RESTORE")
        self.assertEqual(outcome["hostServices"]["status"],"UNKNOWN")
        self.assertTrue(all(x["state"]!="UNIVERSAL_PASS" for x in outcome["automationPolicy"]))
    def test_corrupt_state_not_counted_as_pass(self):
        target=self.root/"work/AF-0002/state.json"
        target.write_text("{broken json",encoding="utf-8")
        statuses=audit_inventory._states(self.root,"work","AF-*/state.json")
        self.assertEqual(statuses["byOriginalState"]["UNKNOWN_CORRUPT_RECORD"],1)
        self.assertEqual(statuses["byOriginalState"]["UNKNOWN"],1)
    def test_root_cause_schema_contains_original_recipes(self):
        with (patch.object(audit_inventory.supervisor,"status",
                 return_value={"status":"STOPPED","pendingQueue":0}),
              patch.object(audit_inventory.local_runtime,"server_info",
                 return_value={"state":"NOT_STARTED"}),
              patch.object(audit_inventory,"_host_service",
                 return_value={"status":"UNKNOWN","serviceCount":None})):
            o=audit_inventory.snapshot(self.root)
        names={x["id"] for x in o["automationPolicy"]}
        self.assertIn("windows_host_service",names)
        self.assertIn("python",names)
        self.assertIn("web_export",names)
        self.assertIn("owner_js_ts",names)
