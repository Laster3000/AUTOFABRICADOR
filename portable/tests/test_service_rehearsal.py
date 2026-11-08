# coding: utf-8
"""Service rehearsal verifier is read-only and guest reports stay untrusted."""
from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from autofab import engine,service_rehearsal
from autofab.storage import load,sha_file,write_json,event


class ServiceRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-r048-service-")
        self.addCleanup(self.tmp.cleanup)
        self.root=engine.init(Path(self.tmp.name))
        self.jid="SX-0011223344556677"
        self.job=self.root/"sandboxjobs"/self.jid
        (self.job/"input").mkdir(parents=True)
        (self.job/"output").mkdir()
        (self.root/"qa/service_r048").mkdir(parents=True,exist_ok=True)
        self.program=self.root/"qa/service_r048/AFR048GuestService.exe"
        self.program.write_bytes(b"trusted first-party fixture not executable")
        for target in ("windows_sandbox_service_r048.zip",
                       "windows_sandbox_service_r048_owner.json"):
            (self.root/"examples"/target).parent.mkdir(exist_ok=True)
            (self.root/"examples"/target).write_text(target)
        write_json(self.job/"manifest.json",
          {"originalSourcePath":str(self.root/"examples/windows_sandbox_service_r048.zip"),
           "ownerOriginalPath":str(self.root/"examples/windows_sandbox_service_r048_owner.json"),
           "sourceOriginalSha":"a"*64},new=True)
        write_json(self.job/"input/owner.json",
            {"steps":[{"script":"src/service_rehearsal.ps1"}]},new=True)
        event(self.job/"journal.jsonl","GUEST_REHEARSAL_FIXTURE",{"owner":"test"})
        self.original={
            "schema":1,"originalJobId":self.jid,"nonce":"fixture",
            "originalZipSha256":"a"*64,
            "status":"GUEST_REPORTED_ALL_OK_UNATTESTED",
            "steps":[{"script":"src/service_rehearsal.ps1",
                      "status":"GUEST_REPORTED_OK","exitCode":0}]
        }
        write_json(self.job/"output/guest-report.json",self.original,new=True)
        self.lifecycle={
            "schema":1,
            "status":"GUEST_SERVICE_INSTALL_START_STOP_RESTART_DELETE_REPORTED",
            "service":"AFR048GuestProbe",
            "guestReportUntrusted":True,
            "hostProtectedInstall":False,
            "steps":[{"phase":p,"atUtc":"fixture","evidence":"guest claimed"}
                     for p in service_rehearsal.EXPECTED_PHASES],
            "child1":1010,"child2":2020,"auditCount":4,
            "auditSha256":"a"*64,"serviceBinarySha":sha_file(self.program)
        }
        write_json(self.job/"output/service-lifecycle.json",self.lifecycle,new=True)
        self.patch1=patch.object(service_rehearsal.windows_sandbox,"verify",
                         return_value={"verified":True})
        self.patch2=patch.object(service_rehearsal.windows_sandbox,"reconcile",
                         return_value={
                             "status":"UNTRUSTED_GUEST_REPORT_READBACK_ONLY",
                             "nativeAcceptance":False,"guestReceiptSha":"b"*64,
                             "reported":"GUEST_REPORTED_ALL_OK_UNATTESTED"
                         })
        self.patch1.start();self.addCleanup(self.patch1.stop)
        self.patch2.start();self.addCleanup(self.patch2.stop)

    def _overwrite(self,path,obj):
        path.write_text(json.dumps(obj),encoding="utf-8")

    def test_success_is_correlated_and_never_authenticated(self):
        result=service_rehearsal.verify(self.root,self.jid)
        self.assertEqual(result["status"],service_rehearsal.RESULT)
        self.assertFalse(result["serviceGuestAttested"])
        self.assertFalse(result["nativeCryptographicOwnerAttested"])
        self.assertFalse(result["hostServiceInstalled"])
        self.assertFalse(result["nativeAcceptance"])
        self.assertEqual(len(result["guestReportedSixPhases"]),6)

    def test_guest_lifecycle_missing_cannot_pass(self):
        (self.job/"output/service-lifecycle.json").unlink()
        with self.assertRaisesRegex(RuntimeError,"UNSAFE_OR_MISSING"):
            service_rehearsal.verify(self.root,self.jid)

    def test_forged_phase_order_detected(self):
        self.lifecycle["steps"][0]["phase"]="FAKE_INSTALLED"
        self._overwrite(self.job/"output/service-lifecycle.json",self.lifecycle)
        with self.assertRaisesRegex(RuntimeError,"EVIDENCE_INVALID"):
            service_rehearsal.verify(self.root,self.jid)

    def test_guest_claiming_host_install_is_rejected(self):
        self.lifecycle["hostProtectedInstall"]=True
        self._overwrite(self.job/"output/service-lifecycle.json",self.lifecycle)
        with self.assertRaisesRegex(RuntimeError,"CORE_CONTRACT_INVALID"):
            service_rehearsal.verify(self.root,self.jid)

    def test_tampered_original_compiled_exe_rejected(self):
        self.program.write_bytes(b"modified")
        with self.assertRaisesRegex(RuntimeError,"BINARY_SHA_DRIFT"):
            service_rehearsal.verify(self.root,self.jid)

    def test_wrong_original_service_source_rejected(self):
        m=load(self.job/"manifest.json")
        m["originalSourcePath"]=str(self.root/"examples/other.zip")
        self._overwrite(self.job/"manifest.json",m)
        with self.assertRaisesRegex(RuntimeError,"WRONG_ORIGINAL_INPUT"):
            service_rehearsal.verify(self.root,self.jid)

    def test_failed_original_guest_claim_never_upgrade(self):
        with patch.object(service_rehearsal.windows_sandbox,"reconcile",
                          return_value={
                           "status":"UNTRUSTED_GUEST_REPORT_READBACK_ONLY",
                           "nativeAcceptance":False,
                           "guestReceiptSha":"b"*64,"reported":"GUEST_STEP_FAILED"
                          }):
            self.original["status"]="GUEST_STEP_FAILED_NOT_ATTESTED"
            self._overwrite(self.job/"output/guest-report.json",self.original)
            result=service_rehearsal.verify(self.root,self.jid)
        self.assertEqual(result["status"],"GUEST_SERVICE_REHEARSAL_UNCONFIRMED")
        self.assertFalse(result["hostServiceInstalled"])

    def test_original_absent_returns_no_claim(self):
        with patch.object(service_rehearsal.windows_sandbox,"reconcile",
                          return_value={"status":"NO_ORIGINAL_GUEST_RECEIPT"}):
            result=service_rehearsal.verify(self.root,self.jid)
        self.assertEqual(result["status"],"NO_ORIGINAL_GUEST_RECEIPT")
        self.assertFalse(result["serviceGuestAttested"])
        self.assertFalse(result["hostServiceInstalled"])


if __name__=="__main__":unittest.main()
