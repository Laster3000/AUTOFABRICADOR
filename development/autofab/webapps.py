# coding: utf-8
"""Verified source-only local interactive web application exporter.

Every model-authored line must have passed the original owner-pinned WASI
tests before it can enter the app bundle. The HTML, CSS and browser event
controller are first-party trusted templates; no model-generated HTML,
lifecycle script, Node server, or unreviewed npm package executes on Host.

This implements bounded offline single-page applications with JS pure-function
backends (including pinned UMD dayjs/lodash), not arbitrary React/Node apps.
"""
from __future__ import annotations
import hashlib,html,json,os,re,subprocess,sys,tempfile,uuid,zipfile
from pathlib import Path
from . import engine,direct_agent,multilang,npm_umd
from .storage import sha_bytes,sha_file,json_bytes,load,utc,write_json,event,verify_journal
from .isolation import IsolationUnavailable

CHROME=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
NODE=Path(r"C:\Program Files\nodejs\node.exe")
PLAYWRIGHT="1.56.1"
PLAYWRIGHT_PACKAGE_SHA="428ba2490bb4eec3a9bf62838207d35318ecfb6677801ae770445bfa52007c27"

def get_original(root,jobid):
    if re.fullmatch(r"AD-[a-f0-9]{16}",jobid):
        direct_agent.verify(root,jobid)
        d=direct_agent.folder(root,jobid)
        files=load(d/"proposed.json")["files"]
        source="DIRECT_HTTP_PINNED_MODEL_NO_NATIVE_EDITOR"
        owner_receipt=d/"owner-wasi.json"
    elif re.fullmatch(r"AL-[a-f0-9]{16}",jobid):
        multilang.verify(root,jobid)
        d=multilang.jobdir(root,jobid)
        if load(d/"spec.json")["language"]!="javascript":
            raise ValueError("WEB_EXPORT_CURRENTLY_JS_ONLY")
        files=load(d/"model.json")["files"]
        source="CODEX_OPENCODE_READONLY_SOURCE_ONLY"
        owner_receipt=d/"test.json"
        if not owner_receipt.exists():
            choices=list(d.glob("*owner*.json"))
            raise RuntimeError("WEB_ORIGINAL_OWNER_TEST_RECEIPT_NOT_FOUND:"+str(choices))
    else:
        raise ValueError("WEB_EXPORT_REQUIRES_ACCEPTED_AD_OR_AL_JS_JOB")
    spec=load(d/"spec.json")
    if spec["language"]!="javascript":raise ValueError("WEB_EXPORT_ONLY_JS")
    if len(files)>6 or not files:raise ValueError("WEB_SOURCE_FILE_COUNT")
    npm_hashes=npm_umd.preflight(root,spec.get("dependencies",[]))
    for filename,text in files.items():
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,45}\.js",filename):
            raise ValueError("WEB_MODEL_FILENAME_UNSAFE")
        if any(re.search(pattern,text) for pattern in (
                r"(?m)^\s*(?:import|export)\s",
                r"(?i)\b(?:fetch|XMLHttpRequest|WebSocket|Worker|ServiceWorker|require|importScripts|document\.cookie|localStorage|sessionStorage)\b")):
            raise ValueError("WEB_RESTRICTED_MODEL_BROWSER_API")
    counts={len(row["args"]) for row in spec["acceptance"]}
    if len(counts)!=1 or not 1<=next(iter(counts))<=8:
        raise ValueError("WEB_OWNER_TEST_SIGNATURE_NOT_CONSISTENT")
    return d,spec,files,npm_hashes,source

def preflight(root):
    root=engine.init(root)
    package=root/"VENDOR/browser-qa/node_modules/playwright-core/package.json"
    entry=root/"qa/browser_probe.js"
    if (not CHROME.is_file() or not NODE.is_file() or not package.is_file()
        or not entry.is_file() or sha_file(package)!=PLAYWRIGHT_PACKAGE_SHA):
        raise IsolationUnavailable("WEBAPP_TRUSTED_CHROME_PLAYWRIGHT_PRIVATE_QA_MISSING")
    if load(package)["version"]!=PLAYWRIGHT:
        raise IsolationUnavailable("WEBAPP_PLAYWRIGHT_VERSION_MISMATCH")
    return {"browserExecutableSha256":sha_file(CHROME),
            "nodeExecutableSha256":sha_file(NODE),
            "browserHarnessSha256":sha_file(entry),
            "playwrightPackageSha256":PLAYWRIGHT_PACKAGE_SHA,
            "qaToolsUserGlobalInstall":False}

def _page(jobid,spec,npm_hashes):
    count=len(spec["acceptance"][0]["args"])
    fn=spec["function"]
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]{0,45}",fn):
        raise ValueError("WEB_SOURCE_FUNCTION_NAME_UNSAFE")
    inputs=[]
    for i,value in enumerate(spec["acceptance"][0]["args"]):
        # Input is JSON, so users can enter arrays and strings as well.
        seed=json.dumps(value,ensure_ascii=True)
        inputs.append('<label class="input-label" for="arg-'+str(i)+'">'
                      '<span>Argumento '+str(i+1)+'</span>'
                      '<textarea data-argument="'+str(i)+'" id="arg-'+str(i)+
                      '" rows="2" spellcheck="false">'+html.escape(seed)+'</textarea></label>')
    scripts="".join('<script defer src="'+html.escape(name,quote=True)+'"></script>\n'
                    for name in [x+".min.js" for x in npm_hashes]+["logic.js","controller.js"])
    # Node browser receives and executes the JS only through Chromium renderer,
    # never via Node require/eval. Browser network blocked and page CSP fixed.
    return ('<!DOCTYPE html>\n<html lang="es"><head><meta charset="utf-8">\n'
     '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
     '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
     'script-src \'self\'; style-src \'self\'; img-src \'self\' data:; '
     'connect-src \'none\'; object-src \'none\'; base-uri \'none\'; '
     'form-action \'none\'; frame-src \'none\'; worker-src \'none\'">\n'
     '<title>'+html.escape(fn)+' · AUTOFABRICADOR</title>\n'
     '<link rel="stylesheet" href="styles.css">\n'
     '</head><body><main class="shell">'
     '<header><p class="eyebrow">AUTOFABRICADOR · APP LOCAL</p>'
     '<h1>'+html.escape(fn)+'</h1>'
     '<p class="lede">Aplicación interactiva, sin conexión a internet. '
     'Introduce valores JSON válidos y ejecuta el cálculo.</p></header>'
     '<section class="panel"><h2>Datos de entrada</h2>'
     '<div class="inputs">'+"".join(inputs)+'</div>'
     '<button id="run" type="button">Calcular</button></section>'
     '<section class="panel results" aria-live="polite"><h2>Resultado</h2>'
     '<output id="result" tabindex="0">Esperando datos</output>'
     '<p id="status" class="status" role="status">Los cálculos se ejecutan en tu navegador.</p>'
     '</section><footer>Paquete '+html.escape(jobid)+' · '
     'código original verificado en WebAssembly antes del empaquetado.</footer>'
     '</main>'+scripts+'</body></html>\n')

def _css():
    return """*{box-sizing:border-box}html{color-scheme:light dark}
body{margin:0;font:16px/1.5 system-ui,Segoe UI,sans-serif;background:#0c1324;color:#ebf4ff}
.shell{width:min(940px,94vw);margin:48px auto;display:grid;gap:22px}
header,.panel{border:1px solid #314561;border-radius:18px;padding:25px;background:#19263b}
h1{font-size:clamp(28px,4vw,50px);letter-spacing:-1px;margin:4px 0}
h2{font-size:18px;margin:0 0 16px}.eyebrow{color:#85d5e0;letter-spacing:2px;font-size:12px;font-weight:bold}
.lede{color:#b4c5da;margin:0}.inputs{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px;margin:10px 0 22px}
.input-label{display:grid;gap:8px;font-size:14px;color:#dbe9f8}
textarea{min-width:0;width:100%;resize:vertical;min-height:58px;border-radius:9px;border:1px solid #54718d;background:#0b1627;color:#fff;padding:12px;font:15px ui-monospace,monospace}
button{border:none;background:#69cfb7;color:#082a27;border-radius:10px;padding:12px 24px;font-weight:800;cursor:pointer;font-size:16px}
button:focus-visible,textarea:focus-visible{outline:3px solid #f8c66a;outline-offset:3px}
.results output{display:block;padding:14px 16px;background:#101e32;min-height:54px;border-radius:10px;white-space:pre-wrap;overflow-wrap:anywhere;font:18px ui-monospace,monospace}
.status,footer{font-size:13px;color:#b1c7dc}footer{text-align:center}
@media(max-width:600px){.shell{margin:15px auto}.panel,header{padding:18px}}
"""

def _controller(fn,num):
    # IMPORTANT: fn and arg count are validated by original contract.
    return ('"use strict";\n'
      'document.getElementById("run").addEventListener("click",()=>{\n'
      ' const target=document.getElementById("result");\n'
      ' const state=document.getElementById("status");\n'
      ' try{\n'
      '  const params=Array.from({length:'+str(num)+'},(_,i)=>'
      'JSON.parse(document.querySelector("[data-argument=\\\""+i+"\\\"]").value));\n'
      '  const value='+fn+'(...params);\n'
      '  target.textContent=typeof value==="string"?value:JSON.stringify(value);\n'
      '  state.textContent="Cálculo completado localmente";\n'
      ' }catch(error){target.textContent="Error de entrada";'
      'state.textContent="Revisa los argumentos JSON";}\n'
      '});\n')

def _create_files(root,jobid,spec,files,vendor,where):
    where.mkdir(parents=True,exist_ok=False)
    (where/"index.html").write_text(_page(jobid,spec,vendor),encoding="utf-8")
    (where/"styles.css").write_text(_css(),encoding="utf-8")
    (where/"controller.js").write_text(_controller(spec["function"],len(spec["acceptance"][0]["args"])),encoding="utf-8")
    concatenated="\n;\n".join(files.values())
    (where/"logic.js").write_text(concatenated,encoding="utf-8")
    for name in vendor:
        source=root/"VENDOR/npm-pin"/name/vendor[name]["version"]/(name+".min.js" if name=="dayjs" else "lodash.min.js")
        if not source.is_file() or sha_file(source)!=vendor[name]["fileSha256"]:
            raise IsolationUnavailable("WEB_VENDOR_SOURCE_SHA_DRIFT")
        (where/(name+".min.js")).write_bytes(source.read_bytes())
    return {p.name:sha_file(p) for p in where.iterdir() if p.is_file()}

def _run_browser(root,folder,spec):
    acceptance=folder/"owner-browser-cases.json"
    write_json(acceptance,spec["acceptance"],new=True)
    dest=folder/"browser-result.json"
    cmd=[str(NODE),str(root/"qa/browser_probe.js"),
         str(folder),str(acceptance),str(CHROME),str(dest)]
    try:
        result=subprocess.run(cmd,cwd=str(root),stdin=subprocess.DEVNULL,
                              capture_output=True,timeout=120,
                              env={**os.environ,"DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false",
                                   "NODE_OPTIONS":"","PLAYWRIGHT_BROWSERS_PATH":"0"})
    except subprocess.TimeoutExpired:
        raise RuntimeError("WEBAPP_BROWSER_TIMEOUT_UNKNOWN_RECONCILE")
    if result.returncode or not dest.is_file():
        raise RuntimeError("WEBAPP_BROWSER_E2E_REJECTED:"+result.stderr.decode("utf-8","replace")[-1000:])
    report=load(dest)
    if report["status"]!="PASS" or report["passed"]!=len(spec["acceptance"]) or not report["externalFetchBlocked"]:
        raise RuntimeError("WEBAPP_BROWSER_OWNER_OR_NETWORK_NOT_ACCEPTED")
    return report

def export(root,jobid):
    root=engine.init(root)
    vendor_info=preflight(root)
    d,spec,files,vendor,origin=get_original(root,jobid)
    root_apps=root/"apps";root_apps.mkdir(exist_ok=True)
    package=root_apps/("AF-WEB-"+jobid+".zip")
    if package.is_file():
        return {"status":"ALREADY_BUILT_NO_REPLAY","jobId":jobid,"verify":verify(root,jobid)}
    local=root_apps/(jobid+"-receipts")
    if local.exists():raise RuntimeError("WEBAPP_PREEXISTING_EVIDENCE_RECONCILE_BEFORE_REBUILD")
    local.mkdir()
    event(local/"journal.jsonl","WEBAPP_BUILD_INTENT",
          {"originalJobId":jobid,
           "originalOwnerSha":sha_file(d/"owner-acceptance.json"),
           "originalSourceSha":sha_file(d/("proposed.json" if jobid.startswith("AD-") else "model.json")),
           "browserHarnessSha":vendor_info["browserHarnessSha256"]})
    with tempfile.TemporaryDirectory(prefix="af-webapp-build-") as tmp:
        stage=Path(tmp)/"web"
        file_hashes=_create_files(root,jobid,spec,files,vendor,stage)
        browser=_run_browser(root,stage,spec)
        # Keep first-party trace, not huge ephemeral Chrome profiles.
        write_json(local/"browser-original.json",browser,new=True)
        event(local/"journal.jsonl","WEBAPP_BROWSER_OWNER_PASS",
              {"receiptSha":sha_file(local/"browser-original.json"),
               "passed":browser["passed"],"deniedNetwork":True})
        original=sha_file(d/"manifest.json")
        manifest={"schema":1,"jobId":jobid,"appType":"OFFLINE_SINGLE_PAGE_WEB",
                  "entry":"index.html","files":file_hashes,
                  "originalAIJobManifestSha":original,
                  "originalModelProposedSha":sha_file(d/("proposed.json" if jobid.startswith("AD-") else "model.json")),
                  "originalOwnerAcceptanceSha":sha_file(d/"owner-acceptance.json"),
                  "originalOwnerTests":len(spec["acceptance"]),
                  "browserE2eTests":browser["testCount"],
                  "browserReceiptSha":sha_file(local/"browser-original.json"),
                  "dependencyHashes":vendor,
                  "nativeEditorProcessForApp":"none" if origin.startswith("DIRECT") else "CLI source-only",
                  "networkDisabledByCSP":True,"browserProcessSandboxNotOSIndependentlyAttested":True,
                  "atUtc":utc()}
        write_json(local/"APP-MANIFEST.json",manifest,new=True)
        event(local/"journal.jsonl","WEBAPP_PACKAGE_INTENT",
              {"manifestSha":sha_file(local/"APP-MANIFEST.json")})
        with zipfile.ZipFile(package,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for entry in sorted(stage.iterdir()):
                if entry.is_file() and entry.name not in ("owner-browser-cases.json","browser-result.json"):
                    z.write(entry,entry.name)
            z.writestr("MANIFEST.json",json_bytes(manifest))
            z.writestr("BROWSER-RECEIPT.json",json_bytes(browser))
        proof={"status":"WEBAPP_ACCEPTED_BROWSER_E2E",
               "archiveSha":sha_file(package),"originalJobId":jobid,
               "manifestSha":sha_file(local/"APP-MANIFEST.json"),
               "browserReceiptSha":sha_file(local/"browser-original.json"),
               "ownerTestCount":len(spec["acceptance"]),"atUtc":utc()}
        write_json(local/"package-receipt.json",proof,new=True)
        event(local/"journal.jsonl","WEBAPP_PACKAGE_READBACK",
              {"archiveSha":sha_file(package),
               "receiptSha":sha_file(local/"package-receipt.json")})
    return {"status":"WEBAPP_ACCEPTED_BROWSER_E2E",
            "jobId":jobid,"webAppZip":str(package),"verify":verify(root,jobid)}

def verify(root,jobid):
    root=engine.init(root)
    d,spec,code,vendor,origin=get_original(root,jobid)
    pkg=root/"apps"/("AF-WEB-"+jobid+".zip")
    records=root/"apps"/(jobid+"-receipts")
    if not pkg.is_file() or not records.is_dir():
        raise RuntimeError("WEBAPP_ORIGINAL_PACKAGE_RECEIPTS_MISSING")
    verify_journal(records/"journal.jsonl")
    manifest=load(records/"APP-MANIFEST.json")
    if sha_file(d/"manifest.json")!=manifest["originalAIJobManifestSha"]:
        raise RuntimeError("WEBAPP_ORIGINAL_AI_ACCEPTANCE_SHA_DRIFT")
    if sha_file(d/"owner-acceptance.json")!=manifest["originalOwnerAcceptanceSha"]:
        raise RuntimeError("WEBAPP_OWNER_SHA_DRIFT")
    if sha_file(d/("proposed.json" if jobid.startswith("AD-") else "model.json"))!=manifest["originalModelProposedSha"]:
        raise RuntimeError("WEBAPP_SOURCE_SHA_DRIFT")
    if manifest["dependencyHashes"]!=vendor:
        raise RuntimeError("WEBAPP_VENDOR_SHA_DRIFT")
    if sha_file(records/"browser-original.json")!=manifest["browserReceiptSha"]:
        raise RuntimeError("WEBAPP_BROWSER_RECEIPT_SHA_DRIFT")
    receipt=load(records/"package-receipt.json")
    if sha_file(pkg)!=receipt["archiveSha"]:
        raise RuntimeError("WEBAPP_PACKAGE_SHA_DRIFT")
    with zipfile.ZipFile(pkg) as z:
        names=z.namelist()
        if set(names)!=set(manifest["files"])|{"MANIFEST.json","BROWSER-RECEIPT.json"}:
            raise RuntimeError("WEBAPP_ZIP_CONTENT_SET_DRIFT")
        if json.loads(z.read("MANIFEST.json"))!=manifest:
            raise RuntimeError("WEBAPP_MANIFEST_CONTENT_DRIFT")
        for name,sha in manifest["files"].items():
            if sha_bytes(z.read(name))!=sha:raise RuntimeError("WEBAPP_FILE_SHA_DRIFT:"+name)
        b=json.loads(z.read("BROWSER-RECEIPT.json"))
        if b!=load(records/"browser-original.json"):
            raise RuntimeError("WEBAPP_BROWSER_RECEIPT_CONTENT_DRIFT")
    return {"verified":True,"status":"WEBAPP_ACCEPTED_BROWSER_E2E",
            "jobId":jobid,"archiveSha256":sha_file(pkg),
            "originalWasiTests":manifest["originalOwnerTests"],
            "originalBrowserTests":manifest["browserE2eTests"],
            "externalNetworkBlocked":True,
            "browserNativeSandboxIndependentAttestation":False}
