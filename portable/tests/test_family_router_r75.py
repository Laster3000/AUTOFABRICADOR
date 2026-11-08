# coding: utf-8
"""R75 independent FIRST-PARTY family entrypoint unit regressions.
No actual model jobs and no installed applications created by these tests.
"""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autofab import family_router as F
class R75FamilyRouterTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix="R75-FAMILY-")
  self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name).resolve()
  (self.root/"ENTRADAS").mkdir()
 def make(self,family="library-js",owner="some-owner.json",goal=None,provider="cuda9b"):
  v={"schema":1,"family":family,"owner":owner,
      "goal":goal or ("Owner-approved offline "+family+" request with independent acceptance cases."),
      "provider":provider}
  f=self.root/"ENTRADAS"/"family-request.json"
  f.write_text(json.dumps(v),encoding="utf8")
  return f
 def owner(self,name="some-owner.json"):
  f=self.root/"ENTRADAS"/name
  f.write_text('{"schema":1}',encoding="utf8")
  return f
 def test_family_registry_universal_false(self):
  x=F.capabilities()
  self.assertEqual(x["status"],"BOUNDED_ROUTES_ONLY_NOT_UNIVERSAL")
  self.assertEqual(len(x["routes"]),8)
  self.assertEqual(len(x["blocked"]),5)
  self.assertTrue(all(not a["universalProgramSupported"] for a in x["routes"].values()))
 def test_categories_do_not_claim_game_renderer(self):
  c=F.capabilities()
  self.assertIn("NO_2D_RENDERER",c["routes"]["game-2d-rules"]["trueScope"])
  self.assertIn("NO_WEBGL_GAME",c["routes"]["game-3d-math"]["trueScope"])
  self.assertIn("MISSING",c["blocked"]["android"]["reason"])
 def test_all_blocked_do_not_call_models(self):
  for family in F.BLOCKED:
   f=self.make(family=family)
   with patch.object(F.open_orders,"preview",side_effect=AssertionError("must not be called")), \
       patch.object(F.open_orders,"submit",side_effect=AssertionError("must not be called")):
    result=F.preview(self.root,f)
    self.assertEqual(result["status"],"BLOCKED_NOT_ROUTABLE")
    self.assertFalse(result["modelCalled"])
    self.assertEqual(result["family"],family)
    self.assertEqual(F.submit(self.root,f)["status"],"BLOCKED_NOT_ROUTABLE")
 def test_preview_supported_order_delegates_original(self):
  self.owner()
  f=self.make(family="game-2d-rules")
  original={"status":"FROZEN_OWNER_INPUT_READY","jobId":"OJ-"+"a"*16}
  with patch.object(F.open_orders,"preview",return_value=original) as call:
   x=F.preview(self.root,f)
  self.assertEqual(x["status"],"ADMISSIBLE_SCOPED_OWNER_ROUTE")
  self.assertIn("NO_2D_RENDERER",x["trueScope"])
  self.assertEqual(x["ownerPath"],str(self.root/"ENTRADAS"/"some-owner.json"))
  self.assertEqual(call.call_count,1)
 def test_owner_original_rejection_is_preserved(self):
  self.owner();f=self.make()
  with patch.object(F.open_orders,"preview",return_value={"status":"BLOCKED_BAD_OWNER","detail":"foo"}):
   x=F.preview(self.root,f)
  self.assertEqual(x["status"],"BLOCKED_OWNER_POLICY")
  self.assertEqual(x["originalPreview"]["status"],"BLOCKED_BAD_OWNER")
 def test_preview_windows_routes_are_bounded(self):
  self.owner("orders.txt")
  f=self.make(family="desktop-orders",owner="orders.txt")
  with patch.object(F.desktop_workflow,"preview",return_value={"status":"FROZEN_FIRST_PARTY_DESKTOP_ORDERS_SCOPE"}):
   result=F.preview(self.root,f)
  self.assertEqual(result["status"],"ADMISSIBLE_SCOPED_OWNER_ROUTE")
  self.assertIn("BOUNDED_WINDOWS_SQLITE",result["trueScope"])
  self.owner("portfolio.txt")
  g=self.make(family="desktop-portfolio",owner="portfolio.txt")
  with patch.object(F.portfolio_workflow,"preview",return_value={"status":"PASS_FROZEN_INDEPENDENT_FIRST_PARTY_SCOPE"}):
   result=F.preview(self.root,g)
  self.assertEqual(result["status"],"ADMISSIBLE_SCOPED_OWNER_ROUTE")
 def test_submits_once_to_existing_owner(self):
  self.owner();f=self.make(family="api-route-logic")
  original={"status":"FROZEN_OWNER_INPUT_READY","jobId":"OJ-"+"b"*16}
  with patch.object(F.open_orders,"preview",return_value=original), \
       patch.object(F.open_orders,"submit",return_value={"status":"SUBMITTED_ONCE_TO_ORIGINAL_LOCAL_SUPERVISOR",
          "jobId":"OJ-"+"b"*16}) as submit:
   result=F.submit(self.root,f)
  self.assertEqual(result["status"],"SUBMITTED_TO_ORIGINAL_OWNER")
  self.assertTrue(result["notAUniversalApp"])
  self.assertEqual(submit.call_count,1)
  self.assertEqual(submit.call_args.kwargs,
                   {"provider":"cuda9b","acceptance_mode":"wasi-browser"})
 def test_blocked_submit_does_not_launch(self):
  self.owner()
  f=self.make()
  with patch.object(F.open_orders,"preview",return_value={"status":"FAIL"}),\
       patch.object(F.open_orders,"submit") as submit:
   self.assertEqual(F.submit(self.root,f)["status"],"BLOCKED_OWNER_POLICY")
  submit.assert_not_called()
 def test_guard_owner_path_escape(self):
  for name in ("../x.json","C:\\secret.json","X:/secret.json","..",".", "x/x.json"):
   f=self.make(owner=name)
   with self.assertRaises(ValueError):F.preview(self.root,f)
 def test_symlink_owner_denied(self):
  ext=self.root/"remote.json";ext.write_text("{}")
  p=self.root/"ENTRADAS"/"some-owner.json"
  try:p.symlink_to(ext)
  except OSError:self.skipTest("platform symlink restricted")
  f=self.make()
  with self.assertRaises(ValueError):F.preview(self.root,f)
 def test_request_outside_root_denied(self):
  outside=self.root/"outside.json"
  outside.write_text(json.dumps({"schema":1}),encoding="utf8")
  with self.assertRaises(ValueError):F.preview(self.root,outside)
 def test_duplicate_json_keys_denied(self):
  f=self.root/"ENTRADAS"/"bad.json"
  f.write_text('{"schema":1,"schema":1,"family":"android","owner":"x.json","provider":"cuda9b","goal":"Valid request but duplicate JSON key is prohibited."}',encoding="utf8")
  with self.assertRaisesRegex(ValueError,"DUPLICATE"):F.preview(self.root,f)
 def test_nan_denied(self):
  f=self.make(family="android")
  f.write_text(f.read_text(encoding="utf8").replace('"schema": 1','"schema": NaN'),encoding="utf8")
  with self.assertRaises(ValueError):F.preview(self.root,f)
 def test_invalid_family_denied(self):
  f=self.make(family="web-fullstack-DO-EVERYTHING")
  with self.assertRaises(ValueError):F.preview(self.root,f)
 def test_invalid_provider_denied(self):
  f=self.make(provider="cloud-unpinned")
  with self.assertRaises(ValueError):F.preview(self.root,f)
 def test_missing_owner_denied(self):
  f=self.make()
  with self.assertRaises(ValueError):F.preview(self.root,f)
 def test_owner_extension_denied(self):
  self.owner("data.exe");f=self.make(owner="data.exe")
  with self.assertRaises(ValueError):F.preview(self.root,f)
 def test_status_reads_original(self):
  with patch.object(F.open_orders,"status",return_value={"status":"PASS"}) as status:
   x=F.status(self.root,"library-js","OJ-"+"f"*16)
  self.assertEqual(x["original"]["status"],"PASS")
  self.assertEqual(status.call_count,1)
 def test_status_invalid_id_denied(self):
  with self.assertRaises(ValueError):F.status(self.root,"library-js","OJ-UNKNOWN")
 def test_desktop_portfolio_id_has_original_prefix(self):
  with patch.object(F.portfolio_workflow,"status",return_value={"status":"PENDING"}):
   x=F.status(self.root,"desktop-portfolio","DP-"+"b"*16)
  self.assertEqual(x["original"]["status"],"PENDING")
 def test_no_undefined_supported_route(self):
  self.assertTrue(set(F.ROUTES).isdisjoint(set(F.BLOCKED)))
 def test_all_positive_routes_owner_frozen(self):
  for family in ("library-js","offline-web-calculator","api-route-logic",
                 "game-2d-rules","game-3d-math","agent-decision-logic"):
   self.owner()
   f=self.make(family=family)
   with patch.object(F.open_orders,"preview",return_value={"status":"FROZEN_OWNER_INPUT_READY"}):
    self.assertTrue(F.preview(self.root,f)["ownerFrozen"])
if __name__=="__main__":unittest.main()
