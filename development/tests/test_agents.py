import tempfile
from pathlib import Path
import unittest
from autofab.agents import discover

class AgentInventoryTests(unittest.TestCase):
    def test_not_claiming_external_agents_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            status=discover(Path(tmp))
        self.assertIn("One local coding model",status["implementation"])
        self.assertEqual(len(status["stages"]),4)
        self.assertTrue(all(s["active"] for s in status["stages"]))
        self.assertEqual({x["id"] for x in status["externalCoders"]},{"aider","codex-cli","opencode"})
        self.assertTrue(all(not x["active"] for x in status["externalCoders"]))

if __name__=="__main__":
    unittest.main()
