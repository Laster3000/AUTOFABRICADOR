# coding: utf-8
"""No-host-effect guard tests for the integrated CUDA7B original provider."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autofab import local_cuda7b

class InternalCuda7bGuards(unittest.TestCase):
    def test_no_lease_means_not_started(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(local_cuda7b.server_info(Path(d))["state"],"NOT_STARTED")
    def test_pid_reuse_never_gets_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            lease=local_cuda7b.paths(root)["lease"]
            lease.parent.mkdir(parents=True)
            lease.write_text(json.dumps({"pid":74321,"processBornFiletime":111}),encoding="utf-8")
            with patch.object(local_cuda7b,"_pid_born",return_value=222):
                self.assertEqual(local_cuda7b.server_info(root)["state"],"PID_REUSED_OR_BIRTH_DIFFERENT")
                with self.assertRaisesRegex(RuntimeError,"UNSAFE_STOP_UNKNOWN_IDENTITY"):
                    local_cuda7b.stop(root)
    def test_ram_floor_rejects_before_spawn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            manifest=root/"INSTALL-MANIFEST.json"
            manifest.write_text("{}",encoding="utf-8")
            fake={"manifest":manifest}
            with patch.object(local_cuda7b,"pinned_assets",return_value=fake), \
                 patch.object(local_cuda7b,"_ram",return_value=4096), \
                 patch.object(local_cuda7b,"_vram",return_value={"usedMiB":2000,"freeMiB":10200}):
                with self.assertRaisesRegex(RuntimeError,"INSUFFICIENT_MEMORY"):
                    local_cuda7b.preflight(root)
    def test_constants_never_bind_public_endpoint(self):
        self.assertEqual(local_cuda7b.PORT,11469)
        self.assertEqual(len(local_cuda7b.MODEL_SHA),64)
        self.assertEqual(local_cuda7b.MIN_RAM_LOADING_MIB,2100)

if __name__=="__main__":
    unittest.main()
