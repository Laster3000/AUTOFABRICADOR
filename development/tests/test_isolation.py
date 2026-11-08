"""Isolated-runner contract tests without requiring Docker or running untrusted code."""
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import patch

from autofab.isolation import docker_preflight, run_tests

IMAGE_ID="sha256:"+"a"*64

class DockerIsolationContract(TestCase):
    def test_immutable_image_id_required(self):
        info=subprocess.CompletedProcess(["docker"],0,stdout="linux\n",stderr="")
        image=subprocess.CompletedProcess(["docker"],0,stdout=IMAGE_ID+"\n",stderr="")
        with patch("autofab.isolation.shutil.which",return_value="docker"), \
             patch("autofab.isolation.subprocess.run",side_effect=[info,image]) as invoke:
            self.assertEqual(docker_preflight("python:3.12-slim"),("docker",IMAGE_ID))
            self.assertEqual(invoke.call_count,2)

    def test_sandbox_command_properties_and_test_count(self):
        info=subprocess.CompletedProcess(["docker"],0,stdout="linux\n",stderr="")
        image=subprocess.CompletedProcess(["docker"],0,stdout=IMAGE_ID+"\n",stderr="")
        execute=subprocess.CompletedProcess(["docker"],0,stdout=b"",stderr=b"Ran 2 tests in 0.004s\n\nOK\n")
        with tempfile.TemporaryDirectory() as tmp:
            with patch("autofab.isolation.shutil.which",return_value="docker"), \
                 patch("autofab.isolation.subprocess.run",side_effect=[info,image,execute]) as invoke:
                receipt=run_tests(Path(tmp))
                argv=invoke.call_args.args[0]
                self.assertIn("--network",argv)
                self.assertIn("none",argv)
                self.assertIn("--read-only",argv)
                self.assertIn("--cap-drop",argv)
                self.assertIn("--pids-limit",argv)
                self.assertIn("--memory",argv)
                self.assertIn(IMAGE_ID,argv)
                self.assertNotIn("python:3.12-slim",argv)
                self.assertEqual(receipt["testCount"],2)
                self.assertEqual(receipt["exitCode"],0)

    def test_zero_tests_is_failure_even_with_exit_zero(self):
        info=subprocess.CompletedProcess(["docker"],0,stdout="linux\n",stderr="")
        image=subprocess.CompletedProcess(["docker"],0,stdout=IMAGE_ID+"\n",stderr="")
        execute=subprocess.CompletedProcess(["docker"],0,stdout=b"",stderr=b"Ran 0 tests in 0.000s\n\nOK\n")
        with tempfile.TemporaryDirectory() as tmp:
            with patch("autofab.isolation.shutil.which",return_value="docker"), \
                 patch("autofab.isolation.subprocess.run",side_effect=[info,image,execute]):
                receipt=run_tests(Path(tmp))
                self.assertEqual(receipt["testCount"],0)
                self.assertNotEqual(receipt["exitCode"],0)
