"""Truthful local editor/agent role inventory; original MMC7 owner never imported."""
from pathlib import Path
from . import VERSION

def discover(root):
    root=Path(root).resolve()
    from .advisors import registry
    tools=registry(root)["tools"]
    stages=[
        {"id":"intake","kind":"deterministic-stage","active":True,
         "role":"Persist bounded goal, STOP, acceptance SHA and journal"},
        {"id":"local-coder","kind":"local-AI-stage","active":True,
         "role":"Generate code through local model or project-private Aider"},
        {"id":"independent-verifier","kind":"deterministic-stage","active":True,
         "role":"Run factory/owner tests in isolated WASI guests"},
        {"id":"promoter","kind":"deterministic-stage","active":True,
         "role":"Verify source/receipt SHA, not protected Host publication"},
    ]
    editors=[
        {"id":"aider","version":"0.86.2",
         "active":bool(tools["aider"]["sourceOwnerAcceptanceVerified"]),
         "integration":"Single-file source proposal through private Aider Python; accepted only after independent WASI tests",
         "fullGeneralPurposeAgent":False},
        {"id":"codex-cli","version":"0.167.0",
         "active":bool(tools["codex"]["localInferenceReadOnlyVerified"]),
         "integration":"Read-only adviser and source-text generator, ephemeral/no shell; candidate accepted by SHA and separate WASI tests",
         "sourceOwnerAcceptanceVerified":bool(tools["codex"]["sourceOwnerAcceptanceVerified"]),
         "canAutonomouslyEditSources":False},
        {"id":"opencode","version":"1.19.5",
         "active":bool(tools["opencode"]["localInferenceReadOnlyVerified"]),
         "integration":"Read-only adviser and source-text generator with all tools denied; candidate accepted by SHA and separate WASI tests",
         "sourceOwnerAcceptanceVerified":bool(tools["opencode"]["sourceOwnerAcceptanceVerified"]),
         "canAutonomouslyEditSources":False},
    ]
    return {
        "schema":2,"product":"AUTOFABRICADOR","version":VERSION,
        "projectRoot":str(root),"implementation":"One local coding model integrated with original supervisor and deterministic owner-pinned stages; not independent parallel multiagent intelligence",
        "stages":stages,"externalCoders":editors,
        "originalMmc7CodeImported":False,
        "reusedPrinciples":["SHA/CAS source admission","fail-closed UNKNOWN/STOP",
                            "semantic repeated-failure guard","owner-pinned acceptance",
                            "Aider proposal-only capture without apply/shell",
                            "native Codex/OpenCode local advisory interfaces",
                            "model call receipts and response deduplication"],
        "unverified":["Parallel autonomous multi-agent orchestration",
                      "Codex/OpenCode privileged source writing (only source-text proposals have acceptance)",
                      "arbitrary npm package graphs, native Node/npm execution, React build plugin execution or untrusted npm install hooks",
                      "general C# apps requiring host filesystem/network/GUI APIs or arbitrary NuGet/MSBuild scripts",
                      "general service installation and protected Host effects","physical Windows reboot and actual new interactive logon E2E not tested","general arbitrary natural-language tasks without independently owned acceptance not implemented"],
        "additionalLanguageContracts":{"javascript":"AI source proposals, independent owner acceptance in pinned Javy/Wasmtime WASI",
                                      "typescript":"AI source proposals, tsc 5.9.3 then Javy/Wasmtime owner acceptance",
                                      "csharp":"Roslyn + componentize-dotnet WASI2 + SHA-pinned Wasmtime 50.0.1: pre-inference owner-pinned functional C# acceptance verified"},
        "supervisor":"Persistent original local worker with PID+creation-time lease, STOP/reconciliation. Verified user-session Task Scheduler auto-logon and STOP/restart with fresh PID, not Windows SCM service or reboot E2E",
        "openWorkOrders":"Original supervisor accepts arbitrary Spanish/English task goal text with user-supplied independently frozen JSON owner cases via order-submit in ENTRADAS; no owner tests means BLOCKED, not autonomous generic acceptance",
        "localGPUCUDA7B":"Qwen2.5-Coder 7B SHA 509287f7..., CUDA12.4 internal on-demand provider: original free-goal parking order 26/26 WASI and 26/26 independent Chrome offline, original queue SUCCEEDED and portable ZIP verified; no full general-purpose agent guarantee",
        "directHttpSourceOnly":"Pinned llama.cpp localhost SSE and safe TCP cancellation with original slot-readback; no native editor process required for JS proposal",
        "webApplications":"Bounded offline ESM project packages and Chrome E2E, including new 26/26 parking order with original Wasmtime owner acceptance; native Windows Sandbox guest outputs remain untrusted",
        "offlinePrivateVendors":"Full SHA archive now exclusively at D:\\AUTOFABRICADOR-RESCATE of project-private vendor and user-home WASI SDK; system runtimes not bundled; F backup deleted after SHA migration", 
        "multiModuleProject":"Real ESM JS/TS import/export graphs from pinned esbuild-wasm, SHA-allowlisted Day.js/Lodash, no untrusted npm hooks or host source execution. 14B local model corrected three-module repository (12 WASI,12 Chrome) and supervised imported repository (10 WASI,10 Chrome). Previously ledger 22 WASI,15 Chrome; not arbitrary native npm/React apps.",
        "localEscalation":"Pinned existing Qwen2.5-Coder 14B original Ollama GGUF SHA, separate on-demand localhost port 11436, no model download or double copy; stop and original lease reconciliation.",
        "windowsSandboxNative":"Windows Sandbox feature enabled and real original guest launched for local open order; original guest report correlated SHA only, NOT authenticated cryptographic acceptance. No model code on Host.", 
        "note":"Bounded source-to-app acceptance verified; not arbitrary Node/React/npm execution. Native editors are still not independently OS-sandboxed; direct HTTP bypasses them."
    }
