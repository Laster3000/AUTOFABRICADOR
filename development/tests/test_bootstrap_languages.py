"""Private language-toolchain bootstrap is SHA-locked and never global."""
import tempfile
from pathlib import Path
import unittest
from autofab import bootstrap_languages,engine
from autofab.storage import write_json

class BootstrapLanguageTests(unittest.TestCase):
    def test_optional_tools_absent_do_not_automatically_download(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            engine.init(root)
            write_json(root/"LANGUAGE-TOOLS.lock.json",
                       {"schema":1,"vendors":{"javy":{"archiveSha256":"a"*64,
                                                       "binarySha256":"b"*64}}})
            result=bootstrap_languages.check(root)
            self.assertFalse(result["javyPresentAndSha"])
            self.assertFalse(result["typescriptPresentAndSha"])
            self.assertFalse((root/"VENDOR").exists())

    def test_malformed_lock_fails_without_global_modifications(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            engine.init(root)
            write_json(root/"LANGUAGE-TOOLS.lock.json",{"schema":0})
            with self.assertRaises(KeyError):
                bootstrap_languages.check(root)

if __name__=="__main__":
    unittest.main()
