"""Real local inference cancellation is evidenced by original slot readback."""
import tempfile,unittest
from pathlib import Path
from autofab import engine,cancel_probe
from autofab.storage import write_json,sha_file,event
class CancellationTests(unittest.TestCase):
 def test_no_fake_stop_on_already_terminal(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engine.init(root)
   d=root/"cancelprobes/CP-0123456789abcdef";d.mkdir(parents=True)
   write_json(d/"state.json",{"schema":1,"status":"CANCELLED_VERIFIED"})
   write_json(d/"control.json",{"schema":1,"command":"STOP"})
   result=cancel_probe.stop(root,d.name)
   self.assertEqual(result["status"],"NO_ACTIVE_MODEL_TO_STOP")
 def test_original_real_cancel_has_proven_idle_slots(self):
  root=Path(__file__).resolve().parents[1]
  d=root/"cancelprobes/CP-6be9f4d5874c4405"
  if not d.is_dir():self.skipTest("Host original cancel receipt not present")
  import json
  data=json.loads((d/"stream.json").read_text("utf-8"))
  self.assertTrue(data["cancelObserved"])
  self.assertTrue(data["threadExited"])
  self.assertTrue(data["idleAfterClientDisconnect"]["idleVerified"])
  self.assertGreater(data["receivedChunks"],5)
  self.assertEqual(cancel_probe.status(root,d.name)["state"],"CANCELLED_VERIFIED")
if __name__=="__main__":unittest.main()
