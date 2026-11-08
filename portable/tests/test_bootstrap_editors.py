"""Project-private editor bootstrap never replays ambiguous installs."""
import tempfile
from pathlib import Path
import unittest

from autofab import bootstrap_editors
from autofab.storage import write_json

class EditorBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        write_json(self.root/"EDITORS.lock.json",
                   {"schema":1,"platform":"win32-x64","product":"AUTOFABRICADOR"})

    def test_absent_editors_report_not_verified(self):
        state=bootstrap_editors.check(self.root)
        self.assertFalse(state["allVerified"])
        self.assertEqual(state["installed"],{"aider":False,"codex":False,"opencode":False})

    def test_partial_tree_stops_before_install(self):
        (self.root/"VENDOR/editors/node").mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError,"PARTIAL_EDITOR_INSTALL"):
            bootstrap_editors.bootstrap(self.root)

if __name__=="__main__":
    unittest.main()
