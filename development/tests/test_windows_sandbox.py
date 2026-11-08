"""Windows Sandbox native runner is fail-closed on Windows without VM feature.

No untrusted native test source is run on HOST. All tests are static,
SHA/CAS, XML policy, forging and launch-block tests.
"""
import json,os,re,shutil,subprocess,tempfile,unittest,zipfile,stat
from pathlib import Path
from unittest.mock import patch
from autofab import engine,windows_sandbox
from autofab.storage import load,sha_file

class WindowsSandboxBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="af-sandbox-test-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        engine.init(self.root)
        (self.root/"examples").mkdir(exist_ok=True)
        (self.root/"qa").mkdir(exist_ok=True)
        first=Path(__file__).resolve().parents[1]/"qa/windows_sandbox_guest.ps1"
        shutil.copyfile(first,self.root/"qa/windows_sandbox_guest.ps1")
        self.zip=self.root/"examples/repo.zip"
        self.owner=self.root/"examples/owner.json"
        with zipfile.ZipFile(self.zip,"w") as z:
            z.writestr("src/build.ps1","Write-Output 'Inside the VM only'\n")
            z.writestr("src/test.ps1","Write-Output 'Inside the VM only'\n")
            z.writestr("package.json",'{"private":true,"name":"af-r039-sandbox-test"}')
        self.owner.write_text(json.dumps({
            "schema":1,"kind":"powershell",
            "goal":"Demonstrate a native PowerShell script in a disposable isolated Windows VM.",
            "steps":[{"script":"src/build.ps1"},{"script":"src/test.ps1"}]}),encoding="utf-8")

    def stage(self):
        return windows_sandbox.stage(self.root,self.zip,self.owner)

    def test_owner_frozen_wsb_secure(self):
        r=self.stage()
        self.assertEqual(r["status"],"STAGED_NO_VM_EXECUTION")
        self.assertTrue(r["verify"]["verified"])
        self.assertFalse(r["verify"]["nativeCodeExecuted"])
        self.assertTrue(r["verify"]["networkDisabled"])
        self.assertTrue(r["verify"]["clipboardDisabled"])
        self.assertEqual(r["verify"]["mappedPaths"],2)
        self.assertTrue(windows_sandbox._assert_profile(
            self.root/"sandboxjobs"/r["jobId"]))

    def test_guest_boot_does_not_depend_on_powershell_archive_module(self):
        boot = (Path(__file__).resolve().parents[1]/'qa/windows_sandbox_guest.ps1').read_text(encoding='utf-8')
        self.assertNotIn('Expand-Archive', boot)
        self.assertIn('System.IO.Compression.ZipFile]::ExtractToDirectory', boot)
        self.assertIn('Add-Type -AssemblyName System.IO.Compression.FileSystem', boot)

    def test_guest_managed_exit_code_snapshot_and_null_guard(self):
        boot=(Path(__file__).resolve().parents[1]/'qa/windows_sandbox_guest.ps1').read_text(encoding='utf-8')
        self.assertIn('$child.StartInfo = $psi',boot)
        self.assertIn('if ($null -eq $rawExitCode)',boot)
        self.assertIn('exitCode=$code',boot)
        self.assertNotIn('exitCode=[int]$child.ExitCode',boot)

    def test_guest_runs_with_managed_process_and_dual_async_drains(self):
        boot=(Path(__file__).resolve().parents[1]/'qa/windows_sandbox_guest.ps1').read_text(encoding='utf-8')
        self.assertIn('New-Object System.Diagnostics.ProcessStartInfo',boot)
        self.assertIn('$child.StartInfo = $psi',boot)
        self.assertIn('StandardOutput.ReadToEndAsync()',boot)
        self.assertIn('StandardError.ReadToEndAsync()',boot)
        self.assertIn('$child.ExitCode',boot)
        self.assertIn('GUEST_STEP_OUTPUT_OVER_FIXED_LIMIT',boot)
        self.assertNotIn('$child = Start-Process',boot)

    def test_r043_frozen_demo_five_stage_source_and_owner_contract(self):
        root=Path(__file__).resolve().parents[1]
        archive=root/'examples/windows_sandbox_native_demo_r043.zip'
        owner=root/'examples/windows_sandbox_native_owner_r043.json'
        self.assertTrue(archive.is_file())
        self.assertTrue(owner.is_file())
        entries=windows_sandbox._zip_info(archive)
        data=windows_sandbox._owner_contract(owner,entries)
        self.assertEqual(len(data['steps']),5)
        self.assertIn('src/managed_process_probe.ps1',entries)

    def test_attempted_launch_when_disabled_has_zero_host_execution(self):
        task=self.stage()
        with patch.object(windows_sandbox,"_feature_status",
                          return_value={"state":"Disabled"}):
            with patch.object(windows_sandbox.subprocess,"Popen",
                              side_effect=AssertionError("HOST PROCESS FORBIDDEN")):
                outcome=windows_sandbox.launch(self.root,task["jobId"])
        self.assertEqual(outcome["status"],"BLOCKED_OS_SANDBOX_FEATURE_DISABLED")
        self.assertFalse(outcome["launchIntentWritten"])
        self.assertFalse((self.root/"sandboxjobs"/task["jobId"]/"launch-intent.json").exists())
        self.assertEqual(load(self.root/"sandboxjobs"/task["jobId"]/"state.json")["status"],"STAGED")

    def test_duplicate_same_intent_no_extra_staging(self):
        original=self.stage()
        second=self.stage()
        self.assertEqual(original["jobId"],second["jobId"])
        self.assertEqual(second["status"],"EXISTING_STAGED_NO_DUPLICATE_SOURCE")
        self.assertEqual(len(list((self.root/"sandboxjobs").glob("SX-*"))),1)

    def test_no_symlinks_escape_zip(self):
        with zipfile.ZipFile(self.root/"examples"/"symlink.zip","w") as z:
            link=zipfile.ZipInfo("src/evil.ps1")
            link.create_system=3
            link.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(link,"../../Windows/System32")
            z.writestr("src/build.ps1","Write-Output x")
        with self.assertRaisesRegex(ValueError,"LINK_OR_DIRECTORY"):
            windows_sandbox._zip_info(self.root/"examples/symlink.zip")

    def test_rejects_zip_traversal_and_windows_devices(self):
        for unsafe in ("../outside.ps1","/root.ps1","src/../break.ps1",
                       "src//evil.ps1","src/./evil.ps1","src/NUL.txt",
                       "src/CON.ps1","src/file.ps1:evil"):
            z=self.root/"examples"/"unsafe.zip"
            with zipfile.ZipFile(z,"w") as writer:
                writer.writestr("src/ok.ps1","Write-Output ok")
                writer.writestr(unsafe,"Write-Output unsafe")
            with self.subTest(unsafePath=unsafe):
                with self.assertRaisesRegex(ValueError,"UNSAFE_WIN_PATH"):
                    windows_sandbox._zip_info(z)
            z.unlink()

    def test_raw_backslash_member_name_rejected_even_if_zipfile_normalizes(self):
        # Python ZipInfo normalizes backslashes to slash on Windows when WRITING.
        # Directly enforce the RAW reader-side filename guard regardless.
        with self.assertRaisesRegex(ValueError,"UNSAFE_WIN_PATH"):
            windows_sandbox._check_entry_name("src\\evil.ps1")

    def test_zip_bomb_rejected(self):
        z=self.root/"examples"/"bomb.zip"
        with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as writer:
            writer.writestr("src/expand.ps1","X"*500000)
            writer.writestr("src/ok.ps1","Write-Output 'guest'")
        with self.assertRaisesRegex(ValueError,"ZIP_BOMB"):
            windows_sandbox._zip_info(z)

    def test_owner_arbitrary_script_outside_zip_rejected(self):
        bad=load(self.owner)
        bad["steps"]=[{"script":"../../Windows/system.ps1"}]
        self.owner.write_text(json.dumps(bad),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"OWNER_SCRIPT_NOT_SOURCE_PINNED"):
            self.stage()

    def test_owner_contract_script_must_exist(self):
        bad=load(self.owner)
        bad["steps"]=[{"script":"src/missing.ps1"}]
        self.owner.write_text(json.dumps(bad),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"OWNER_SCRIPT_NOT_SOURCE_PINNED"):
            self.stage()

    def test_tampered_network_policy_refused(self):
        j=self.stage()["jobId"]
        profile=self.root/"sandboxjobs"/j/"launch.wsb"
        profile.write_bytes(profile.read_bytes().replace(
             b"<Networking>Disable</Networking>",
             b"<Networking>Enable</Networking>"))
        with self.assertRaisesRegex(RuntimeError,"WSB_SHA_DRIFT"):
            windows_sandbox.verify(self.root,j)
        with self.assertRaisesRegex(RuntimeError,"SECURITY_DOWNGRADED"):
            windows_sandbox._assert_profile(self.root/"sandboxjobs"/j)

    def test_tampered_extra_host_mapping_refused(self):
        j=self.stage()["jobId"]
        profile=self.root/"sandboxjobs"/j/"launch.wsb"
        content=profile.read_text("utf-8")
        content=content.replace("</MappedFolders>",
             "<MappedFolder><HostFolder>C:\\Users</HostFolder>"
             "<SandboxFolder>C:\\Bad</SandboxFolder><ReadOnly>false</ReadOnly>"
             "</MappedFolder></MappedFolders>")
        profile.write_text(content,encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"EXTRA_MOUNT"):
            windows_sandbox._assert_profile(self.root/"sandboxjobs"/j)

    def test_tampered_source_hash_refused(self):
        j=self.stage()["jobId"]
        file=self.root/"sandboxjobs"/j/"input/source.zip"
        with file.open("ab") as f:f.write(b"UNTRUSTED EXTRA")
        with self.assertRaisesRegex(RuntimeError,"INPUT_PREIMAGE_DRIFT"):
            windows_sandbox.verify(self.root,j)

    def test_tampered_original_owner_refused(self):
        j=self.stage()["jobId"]
        with self.owner.open("a",encoding="utf-8") as f:f.write(" ")
        with self.assertRaisesRegex(RuntimeError,"ORIGINAL_OWNER_SHA_DRIFT"):
            windows_sandbox.verify(self.root,j)

    def test_prelaunch_stop_cas_proven_no_replay(self):
        j=self.stage()["jobId"]
        first=windows_sandbox.stop(self.root,j)
        self.assertEqual(first["status"],"STOP_REQUESTED_PRE_LAUNCH")
        self.assertEqual(windows_sandbox.stop(self.root,j)["status"],"ALREADY_STOPPED_BEFORE_LAUNCH")
        with patch.object(windows_sandbox,"_feature_status",
                          return_value={"state":"Enabled"}):
            with patch.object(windows_sandbox.subprocess,"Popen",
                              side_effect=AssertionError("SHOULD_NOT_LAUNCH")):
                result=windows_sandbox.launch(self.root,j)
        self.assertEqual(result["status"],"STOPPED_PRE_SANDBOX_INTENT")

    def test_output_receipt_untrusted_even_if_says_pass(self):
        j=self.stage()["jobId"]
        d=self.root/"sandboxjobs"/j
        original=load(d/"input/owner.json")
        forged={"schema":1,"status":"PASS",
                "originalJobId":j,"nonce":original["nonce"],
                "originalZipSha256":original["sourceSha256"]}
        (d/"output/guest-report.json").write_text(json.dumps(forged),encoding="utf-8")
        result=windows_sandbox.reconcile(self.root,j)
        self.assertEqual(result["status"],"UNTRUSTED_GUEST_REPORT_READBACK_ONLY")
        self.assertFalse(result["nativeAcceptance"])
        self.assertTrue(result["needIndependentOwnerAcceptance"])

    def test_forged_guest_wrong_nonce_refused(self):
        j=self.stage()["jobId"]
        d=self.root/"sandboxjobs"/j
        owner=load(d/"input/owner.json")
        forged={"originalJobId":j,"nonce":"fake",
                "originalZipSha256":owner["sourceSha256"],"status":"PASS"}
        (d/"output/guest-report.json").write_text(json.dumps(forged),encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"WRONG_JOB_OR_SOURCE"):
            windows_sandbox.reconcile(self.root,j)

    def test_original_r039_guest_script_parses_without_running(self):
        if os.name!="nt":self.skipTest("powershell.exe unavailable outside Windows")
        path=Path(__file__).resolve().parents[1]/"qa/windows_sandbox_guest.ps1"
        escaped=str(path).replace("'","''")
        command=(
           "$tokens=$null;$errors=$null;"
           "[System.Management.Automation.Language.Parser]::ParseFile("
           "'"+escaped+"',[ref]$tokens,[ref]$errors) |Out-Null;"
           "if($errors.Count -ne 0){$errors |Out-String;exit 9};'POWERSHELL_AST_ONLY_OK'")
        p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],
                     capture_output=True,stdin=subprocess.DEVNULL,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr.decode(errors="replace"))
        self.assertIn("POWERSHELL_AST_ONLY_OK",p.stdout.decode(errors="replace"))

    def test_original_feature_disabled_from_windows_host(self):
        root=Path(__file__).resolve().parents[1]
        if not (root/"CONTINUIDAD/R039").exists():
            self.skipTest("R039 original Host state not in source-only archive")
        result=windows_sandbox.preflight(root)
        self.assertIn(result["featureState"],
                     ("Disabled","Enabled","EnablePending","DisablePending","UNKNOWN_FEATURE_READBACK"))
        self.assertFalse(result["nativeHostCodeExecutionAllowed"])

    def test_original_r039_staging_receipts_host(self):
        root=Path(__file__).resolve().parents[1]
        job=root/"sandboxjobs"/"SX-c042df1442744109"
        if not job.is_dir():self.skipTest("No original native sandbox job on restored source-only installation")
        result=windows_sandbox.verify(root,job.name)
        self.assertTrue(result["verified"])
        self.assertFalse(result["guestE2ePass"])
        intent=job/"launch-intent.json"
        if intent.exists():
            launch=json.loads(intent.read_text(encoding="utf-8"))
            self.assertEqual(launch["operationId"],job.name+".WINDOWS_SANDBOX.LAUNCH.1")
            self.assertEqual(launch["sourceManifestSha"],sha_file(job/"manifest.json"))
            self.assertEqual(launch["wsbSha"],sha_file(job/"launch.wsb"))
            self.assertFalse(launch["hostNativeCodeExecuted"])
        else:
            self.assertEqual(load(job/"state.json")["status"],"STAGED")

if __name__=="__main__":unittest.main()
