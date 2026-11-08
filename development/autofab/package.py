"""Deterministic portable source bundle with SHA256 + restore rehearsal."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import uuid
import zipfile

from . import VERSION
from .storage import json_bytes, sha_bytes, sha_file, utc, write_json

FILES = [
    "autofabricador.py",
    "autofab/__init__.py",
    "autofab/engine.py",
    "autofab/providers.py",
    "autofab/isolation.py",
    "autofab/storage.py",
    "autofab/package.py",
    "autofab/bootstrap.py",
    "autofab/local_runtime.py",
    "autofab/draft.py",
    "autofab/operate.py",
    "autofab/wasi_isolation.py",
    "autofab/agents.py",
    "autofab/housekeeping.py",
    "autofab/progress_guard.py",
    "autofab/aider_bridge.py",
    "autofab/aider_worker.py",
    "autofab/advisors.py",
    "autofab/bootstrap_editors.py",
    "autofab/source_editors.py",
    "autofab/mission.py",
    "autofab/js_wasi.py",
    "autofab/multilang.py",
    "autofab/csharp_compile.py",
    "autofab/csharp_jobs.py",
    "autofab/supervisor.py",
    "autofab/telemetry.py",
    "autofab/bootstrap_languages.py",
    "autofab/csharp_wasi.py",
    "autofab/csharp_repair.py",
    "autofab/npm_umd.py",
    "autofab/bootstrap_extra.py",
    "autofab/direct_agent.py",
    "autofab/cancel_probe.py",
    "autofab/webapps.py",
    "autofab/vendor_capsule.py",
    "autofab/ledger_project.py",
    "autofab/repo_graph.py",
    "autofab/repo_factory.py",
    "autofab/repo_export.py",
    "autofab/repo_archive.py",
    "autofab/local_escalation.py",
    "autofab/local_cuda7b.py",
    "autofab/open_orders.py",
    "autofab/owner_oracles.py",
    "autofab/autonomous_intake.py",
    "autofab/desktop_orders_core.py",
    "autofab/desktop_orders_ui.py",
    "autofab/desktop_requirements.py",
    "autofab/desktop_installer.py",
    "autofab/desktop_workflow.py",
    "autofab/portfolio_specs.py",
    "autofab/portfolio_core.py",
    "autofab/portfolio_ui.py",
    "autofab/portfolio_installer.py",
    "autofab/portfolio_workflow.py",
    "qa/portfolio_acceptance.py",
    "qa/desktop_acceptance.py",
    "autofab/owner_proposals.py",
    "autofab/job_console.py",
    "autofab/logon_observer.py",
    "autofab/reboot_audit.py",
    "autofab/autorun.py",
    "autofab/windows_sandbox.py",
    "autofab/native_repo_bridge.py",
    "autofab/native_cycle.py",
    "autofab/factory_pipeline.py",
    "autofab/intent_catalog.py",
    "autofab/portable_delivery.py",
    "autofab/service_rehearsal.py",
    "autofab/service_worker.py",
    "autofab/blackbox.py",
    "autofab/self_audit.py",
    "autofab/audit_inventory.py",
    "autofab/repair_bridge.py",
    "autofab/python_direct.py",
    "autofab/python_general.py",
    "autofab/python_general_repair.py",
    "autofab/export_recovery.py",
    "examples/calculadora.json",
    "examples/calculadora_con_aceptacion.json",
    "examples/test_aceptacion_calculadora.py",
    "examples/slugger_con_aceptacion.json",
    "examples/capability_ipv4_typescript_r051_feedback.json",
    "examples/capability_duration_javascript_r051.json",
    "examples/capability_supervisor_clamp_score_r051.json",
    "examples/temperature_owner_acceptance_r051.json",
    "examples/test_owner_temperature_r051.py",
    "examples/test_owner_normalize_words_r052.py",
    "examples/normalize_words_new_r052.json",
    "examples/csharp_distinct_positives_r052.json",
    "examples/self_audit_ts_r054.json",
    "examples/self_audit_js_r054.json",
    "examples/self_audit_ts_strategy_r054.json",
    "examples/self_audit_ts_hybrid_r055.json",
    "examples/self_audit_ts_hybrid_type_r055.json",
    "examples/owner_py_direct_r056.json",
    "examples/owner_py_direct_hybrid_r056.json",
    "examples/test_owner_unique_positive_r057.py",
    "examples/test_owner_merge_intervals_r057.py",
    "examples/seed_unique_positive_r057.py",
    "examples/seed_merge_intervals_r057.py",
    "examples/python_general_unique_positive_v1_r057.json",
    "examples/python_general_merge_intervals_v1_r057.json",
    "examples/python_general_unique_positive_v1_goal_only_r057.json",
    "examples/python_general_merge_intervals_v1_goal_only_r057.json",
    "examples/test_owner_py_slug_r053.py",
    "examples/py_slug_seed_r053.py",
    "examples/mega_js_collapse_runs_r053.json",
    "examples/mega_ts_port_3modules_r053.json",
    "examples/mega_py_slug_codex_r053.json",
    "examples/mega_js_collapse_runs_r053_recovery.json",
    "examples/mega_ts_port_r053_recovery.json",
    "examples/mega_py_slug_codex_r053_recovery.json",
    "examples/py_slug_repair_seed_r053.py",
    "examples/test_owner_slugger.py",
    "examples/slugger_seed.py",
    "examples/aider_normalize_con_aceptacion.json",
    "examples/bound_seed.py",
    "examples/test_owner_bound.py",
    "examples/codex_clamp_aceptacion.json",
    "examples/parity_seed.py",
    "examples/test_owner_parity.py",
    "examples/opencode_parity_aceptacion.json",
    "examples/mission_parity_aceptacion.json",
    "examples/odd_seed.py",
    "examples/test_owner_odd.py",
    "examples/mission_stop_odd_aceptacion.json",
    "examples/js_bounded_sum.json",
    "examples/ts_even_sum.json",
    "examples/js_simple_increment.json",
    "examples/supervisor_triple.json",
    "examples/csharp_bounded_sum.json",
    "examples/csharp_wasi_sum_doubles.json",
    "examples/csharp-repair-from-AC-7c5bac4a13774f1f.json",
    "examples/js_pinned_dayjs_lodash.json",
    "examples/direct_triple.json",
    "examples/direct_cancel_long.json",
    "examples/supervisor_direct_quadruple.json",
    "examples/direct_multifile_invoice_project.json",
    "examples/direct_repair_invoice_r037.json",
    "examples/repo_sales_esm_dayjs.json",
    "examples/encargo_planificador_pedidos_20261108.json",
    "examples/repo_sales_esm_dayjs_repair_from_RJ_e548.json",
    "examples/repo_import_owner_discount.json",
    "examples/repo_import_discount_source.zip",
    "examples/windows_sandbox_native_demo.zip",
    "examples/windows_sandbox_native_owner.json",
    "examples/windows_sandbox_native_demo_r043.zip",
    "examples/windows_sandbox_native_owner_r043.json",
    "tests/test_engine.py",
    "tests/test_provider_http.py",
    "tests/test_isolation.py",
    "tests/test_operate.py",
    "tests/test_housekeeping.py",
    "tests/test_progress_guard.py",
    "tests/test_agents.py",
    "tests/test_advisors.py",
    "tests/test_bootstrap_editors.py",
    "tests/test_source_editors.py",
    "tests/test_mission.py",
    "tests/test_js_wasi.py",
    "tests/test_js_wasi_object_semantics.py",
    "tests/test_local_cuda7b_guard.py",
    "tests/test_open_orders.py",
    "tests/test_owner_oracles.py",
    "tests/test_autonomous_intake.py",
    "tests/test_desktop_orders_core.py",
    "tests/test_desktop_workflow.py",
    "tests/test_portfolio_core.py",
    "tests/test_portfolio_integration.py",
    "tests/test_owner_proposals.py",
    "tests/test_job_console.py",
    "tests/test_logon_observer.py",
    "tests/test_supervisor_logon_integration.py",
    "tests/test_reboot_audit.py",
    "tests/test_autorun.py",
    "tests/test_multilang.py",
    "tests/test_csharp_compile.py",
    "tests/test_supervisor.py",
    "tests/test_bootstrap_languages.py",
    "tests/test_csharp_wasi.py",
    "tests/test_npm_umd.py",
    "tests/test_supervisor_recovery.py",
    "tests/test_direct_agent.py",
    "tests/test_cancel_probe.py",
    "tests/test_webapps.py",
    "tests/test_supervisor_direct.py",
    "tests/test_vendor_capsule.py",
    "tests/test_ledger_project.py",
    "tests/test_rescue_d.py",
    "tests/test_repo_graph.py",
    "tests/test_repo_factory.py",
    "tests/test_repo_export.py",
    "tests/test_repo_archive.py",
    "tests/test_repo_supervisor.py",
    "tests/test_repo_import_e2e.py",
    "tests/test_local_escalation.py",
    "tests/test_windows_sandbox.py",
    "tests/test_native_repo_bridge.py",
    "tests/test_native_cycle.py",
    "tests/test_factory_pipeline.py",
    "tests/test_factory_browser_mode.py",
    "tests/test_intent_catalog.py",
    "tests/test_portable_delivery.py",
    "tests/test_service_rehearsal.py",
    "tests/test_service_worker.py",
    "tests/test_r051_integrated_feedback_security.py",
    "tests/test_r052_model_stagnation_truncation.py",
    "tests/test_r052_memory_csharp_acceptance.py",
    "tests/test_blackbox_r053.py",
    "tests/test_r053_javy_null_owner.py",
    "tests/test_r053_security_round_two.py",
    "tests/test_self_audit_r054.py",
    "tests/test_audit_inventory_r054.py",
    "tests/test_r054_adaptive_feedback.py",
    "tests/test_repair_bridge_r055.py",
    "tests/test_repo_export_r055.py",
    "tests/test_python_direct_r056.py",
    "tests/test_sse_finish_reason_r056.py",
    "tests/test_python_repair_import_r056.py",
    "tests/test_python_stop_r056.py",
    "tests/test_python_general_r057.py",
    "tests/test_python_general_repair_r057.py",
    "tests/test_export_recovery_r057.py",
    "tests/test_python_general_stop_r057.py",
    "README.md",
    "AGENTS.md",
    "DEPENDENCIES.lock.json",
    "NATIVE-NODE.lock.json",
    "EDITORS.lock.json",
    "LANGUAGE-TOOLS.lock.json",
    "NPM-UMD.lock.json",
    "OFFLINE-TOOLS.lock.json",
    "MODULE-BUNDLER.lock.json",
    "LAB-CSHARP-WASI-R035/global.json",
    "LAB-CSHARP-WASI-R035/NuGet.Config",
    "LAB-CSHARP-WASI-R035/Program.cs",
    "qa/browser_probe.js",
    "qa/ledger_browser_probe.js",
    "qa/esm_bundle.js",
    "qa/install_esbuild_vetted.py",
    "qa/windows_sandbox_guest.ps1",
    "qa/service_r048/AFR048GuestService.cs",
    "qa/service_r048/AFR048GuestService.exe",
    "qa/service_r048/service_rehearsal.ps1",
    "qa/service_r048/service_rehearsal_bounded.ps1",
    "qa/service_r048/service_rehearsal_final.ps1",
    "qa/service_r049/AFOriginalSupervisorService.cs",
    "qa/service_r049/AFOriginalSupervisorService.exe",
    "examples/windows_sandbox_service_r048.zip",
    "examples/windows_sandbox_service_r048_v2.zip",
    "examples/windows_sandbox_service_r048_v3.zip",
    "examples/windows_sandbox_service_r048_owner.json",
    "qa/archive_vendor.py",
    "LAB-CSHARP-WASI-R035/WasiProbe.csproj",
    "configs/codex-local.toml",
    "configs/opencode-local.json",
]

def trusted_name(name):
    p=PurePosixPath(name)
    if p.is_absolute() or not p.parts or len(p.parts)>6 or any(x in ("..",".","") for x in p.parts) or "\\" in name or ":" in name:
        raise RuntimeError("ZIP_PATH_TRAVERSAL")
    return p

def verify_bundle(archive):
    archive=Path(archive)
    with zipfile.ZipFile(archive,"r") as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or any(name.endswith("/") for name in names):
            raise RuntimeError("DUPLICATE_OR_DIRECTORY_ENTRIES")
        for n in names:trusted_name(n)
        if "MANIFEST.json" not in names:
            raise RuntimeError("BUNDLE_MANIFEST_MISSING")
        m=json.loads(z.read("MANIFEST.json"))
        expected=m.get("files",{})
        if set(names)!=(set(expected)|{"MANIFEST.json"}):
            raise RuntimeError("BUNDLE_CONTENT_NOT_MANIFESTED")
        # Bound archive growth without falsely rejecting an explicitly pinned
        # new first-party source file. Per-entry SHA and exact set are checked.
        if len(expected)>288:
            raise RuntimeError("BUNDLE_UNEXPECTED_FILE_COUNT")
        for name,details in expected.items():
            content=z.read(name)
            if len(content)>500000 or len(content)!=details["size"] or sha_bytes(content)!=details["sha256"]:
                raise RuntimeError("BUNDLE_SOURCE_MISMATCH:"+name)
        return {"status":"VERIFIED_BYTES_ONLY","path":str(archive),
                "zipSha256":sha_file(archive),"files":len(expected),
                "version":m.get("version"),"manifestSha256":sha_bytes(z.read("MANIFEST.json"))}

def build_bundle(root):
    root=Path(root).resolve()
    entries={}
    for name in FILES:
        trusted_name(name)
        content=(root/name).read_bytes()
        if len(content)>500000:raise RuntimeError("SOURCE_TOO_LARGE_FOR_PACKAGE")
        entries[name]=content
    manifest={"schema":2,"product":"AUTOFABRICADOR","version":VERSION,
              "files":{n:{"sha256":sha_bytes(raw),"size":len(raw)} for n,raw in entries.items()},
              "installationStatus":"PORTABLE_CANDIDATE_NOT_HOST_INSTALLED",
              "modelBundle":False}
    entries["MANIFEST.json"]=json_bytes(manifest)
    output=root/"DIST"/f"AUTOFABRICADOR-{VERSION}.zip"
    if output.exists():
        raise FileExistsError("RELEASE_ALREADY_EXISTS_NO_OVERWRITE")
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_name(output.name+".NEW."+uuid.uuid4().hex)
    try:
        with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,content in sorted(entries.items()):
                info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=(0o644<<16)
                z.writestr(info,content,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        os.replace(temp,output)
    finally:
        if temp.exists():temp.unlink()
    audit=verify_bundle(output)
    # Rehearse actual restoration from package and run trusted first-party tests
    with tempfile.TemporaryDirectory(prefix="autofab-restore-") as temp_root:
        dest=Path(temp_root)
        with zipfile.ZipFile(output) as z:
            for name in entries:
                path=dest.joinpath(*PurePosixPath(name).parts)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(z.read(name))
                if sha_bytes(path.read_bytes())!=sha_bytes(entries[name]):
                    raise RuntimeError("RESTORE_READBACK_MISMATCH")
        process=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=dest,
                               stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90,
                               env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
        audit["restoredTestExitCode"]=process.returncode
        audit["restoredTestOutputTail"]=process.stderr.decode("utf-8","replace")[-1300:]
        if process.returncode:
            raise RuntimeError("RESTORE_TEST_FAILED:"+audit["restoredTestOutputTail"])
    audit["restoration"]="RESTORED_AND_TESTED"
    audit["testedUtc"]=utc()
    write_json(root/"DIST"/f"RELEASE-RECEIPT-{VERSION}.json",audit,new=True)
    return audit
