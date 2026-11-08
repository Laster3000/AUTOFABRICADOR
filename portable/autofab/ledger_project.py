# coding: utf-8
"""Reproducible end-to-end inventory web app from MULTI-FILE model source.

Owner WASI acceptance is mandatory BEFORE any project packaging.
All browser DOM and scripts are trusted first-party templates; models have
no shell/network/browser script install access. The AI source executes in a
strict offline CSP Chrome renderer only AFTER verified owner WASI tests.
"""
from __future__ import annotations
from pathlib import Path,PurePosixPath
import hashlib,json,os,re,shutil,subprocess,tempfile,zipfile
from . import engine,webapps,npm_umd
from .storage import load,sha_file,sha_bytes,write_json,utc,event,verify_journal,json_bytes

def _controller():
    return r'''"use strict";
const rows = [];
function money(cents){
  if(!Number.isFinite(cents))throw Error("Invalid cents");
  return (Number(cents)/100).toFixed(2);
}
const byId=id=>document.getElementById(id);
function render(){
  const result=invoiceSummary(rows,Number(byId("tax").value));
  if(!result || !["count","subtotalCents","taxCents","totalCents"].every(
    key=>Number.isInteger(result[key])))throw Error("Invalid source contract");
  byId("summary").textContent =
    "NET="+money(result.subtotalCents)+" TAX="+money(result.taxCents)+" TOTAL="+money(result.totalCents);
  const table=byId("lines").querySelector("tbody");
  table.replaceChildren();
  rows.forEach((row,i)=>{
    const tr=document.createElement("tr");
    for(const value of [row.sku,String(row.qty),money(Math.round(row.price*100))]){
      const td=document.createElement("td");
      td.textContent=value; // never raw model or user-supplied HTML
      tr.appendChild(td);
    }
    const td=document.createElement("td");
    const remove=document.createElement("button");
    remove.textContent="Quitar";
    remove.type="button";
    remove.dataset.remove=String(i);
    remove.addEventListener("click",()=>{rows.splice(i,1);render()});
    td.appendChild(remove);
    tr.appendChild(td);
    table.appendChild(tr);
  });
  byId("status").textContent="Cálculo local actualizado";
}
byId("add").addEventListener("click",()=>{
  const sku=byId("sku").value.trim();
  const qty=Number(byId("quantity").value);
  const price=Number(byId("price").value);
  if(!sku||sku.length>100||!Number.isSafeInteger(qty)||qty<1||qty>1000||
    !Number.isFinite(price)||price<0||price>10000){
    byId("status").textContent="Datos no válidos";return;
  }
  rows.push({sku,qty,price});
  render();
  byId("sku").value="";
});
byId("tax").addEventListener("input",render);
render();
'''

def _index(jobid):
    return '''<!DOCTYPE html><html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'; worker-src 'none'">
<link rel="stylesheet" href="styles.css">
<title>Libro de inventario · AUTOFABRICADOR</title></head>
<body><main class="container"><header><div class="eyebrow">AUTOFABRICADOR • FACTORY PROJECT</div>
<h1>Libro de inventario</h1>
<p>Añade artículos y calcula importes e impuestos sin internet ni servidor.</p></header>
<section class="panel"><h2>Nuevo artículo</h2>
<div class="fields"><label>Referencia<input id="sku" maxlength="100" placeholder="Producto"></label>
<label>Unidades<input id="quantity" type="number" min="1" max="1000" step="1" value="1"></label>
<label>Precio unitario (€)<input id="price" type="number" min="0" max="10000" step="0.01" value="0"></label>
<button id="add" type="button">Añadir</button></div>
</section>
<section class="panel"><div class="heading"><h2>Artículos</h2>
<label>IVA (%) <input id="tax" type="number" min="0" max="25" value="0" step="1"></label></div>
<table id="lines"><thead><tr><th>Referencia</th><th>Unidades</th><th>Precio</th><th>Acción</th></tr></thead>
<tbody></tbody></table>
<div class="total" id="summary" aria-live="polite">NET=0.00 TAX=0.00 TOTAL=0.00</div>
<p role="status" id="status">Preparado</p>
</section><footer>Modelo local y pruebas independientes · '''+jobid+''' · Datos temporales (no se guardan)</footer></main>
<script defer src="logic.js"></script><script defer src="controller.js"></script>
</body></html>
'''

def _css():
    return '''*{box-sizing:border-box}html{color-scheme:light}body{background:#0c1424;color:#e7efff;margin:0;font:16px/1.5 system-ui,Segoe UI,sans-serif}
.container{width:min(1080px,94vw);margin:36px auto;display:grid;gap:20px}
header,.panel{background:#1c2c41;border:1px solid #435a76;border-radius:18px;padding:23px}
.eyebrow{color:#84ded4;letter-spacing:2px;font-size:11px;font-weight:700}
h1{font-size:clamp(27px,5vw,44px);margin:4px 0}h2{font-size:19px;margin:0 0 14px}
p{color:#c5d7e9}.fields{display:grid;gap:12px;grid-template-columns:2fr 1fr 1fr auto;align-items:end}
label{display:flex;flex-direction:column;gap:5px;font-weight:600;font-size:13px}
input{min-width:0;border:1px solid #7890a9;border-radius:9px;background:#0c1729;color:white;padding:11px;font:inherit;width:100%}
button{padding:12px 16px;border:0;border-radius:9px;background:#70dec4;color:#092622;font-weight:800;cursor:pointer}
button:focus-visible,input:focus-visible{outline:3px solid #ffca70}
.heading{display:flex;justify-content:space-between;gap:20px;align-items:center}
.heading input{width:115px}table{border-collapse:collapse;width:100%;margin:15px 0}
td,th{text-align:left;padding:12px;border-bottom:1px solid #3f5370;overflow-wrap:anywhere}
td button{font-size:12px;padding:8px 12px}
.total{background:#101d31;border-radius:10px;font:700 18px ui-monospace,monospace;padding:18px;overflow-wrap:anywhere}
footer{color:#95a9c7;text-align:center;font-size:12px}
@media(max-width:800px){.fields{grid-template-columns:1fr 1fr}.container{margin:12px auto}}
@media(max-width:500px){.fields{grid-template-columns:1fr}td,th{padding:6px;font-size:13px}}
'''

def _verify_source(root,jobid):
    root=engine.init(root)
    d,spec,files,vendor,origin=webapps.get_original(root,jobid)
    if (not jobid.startswith("AD-") or spec["function"]!="invoiceSummary"
        or len(files)<3 or len(spec["acceptance"])<12
        or set(spec["sources"])!={"normalize.js","cents.js","invoice.js"}
        or spec.get("dependencies")):
        raise RuntimeError("LEDGER_REQUIRES_ORIGINAL_MULTI_MODULE_DIRECT_WASI_JOB")
    # Ensure the project is attached to ONE model-accepted original owner set,
    # not a new acceptance invented after seeing source.
    receipt=load(d/"manifest.json")
    if receipt["ownerTestCount"]!=len(spec["acceptance"]):
        raise RuntimeError("LEDGER_ORIGINAL_OWNER_CASE_COUNT_DRIFT")
    return d,spec,files,receipt

def _verify_package(root,jobid):
    folder=root/"projects"/("LEDGER-"+jobid)
    receipt_file=folder/"PROJECT-RECEIPT.json"
    if not receipt_file.is_file():raise RuntimeError("LEDGER_RECEIPT_MISSING")
    receipt=load(receipt_file)
    zipfile_path=root/"projects"/("LEDGER-"+jobid+".zip")
    if not zipfile_path.is_file() or sha_file(zipfile_path)!=receipt["archiveSha256"]:
        raise RuntimeError("LEDGER_ZIP_SHA_DRIFT")
    origin,spec,files,_=_verify_source(root,jobid)
    if (sha_file(origin/"manifest.json")!=receipt["originalWasiManifestSha"]
        or sha_file(origin/"proposed.json")!=receipt["originalAiSourceSha"]):
        raise RuntimeError("LEDGER_ORIGINAL_AI_ACCEPTANCE_SHA_DRIFT")
    with zipfile.ZipFile(zipfile_path) as archive:
        for name,sha in receipt["files"].items():
            if sha_bytes(archive.read(name))!=sha:
                raise RuntimeError("LEDGER_PACKAGE_FILE_SHA_DRIFT:"+name)
    browser=load(folder/"BROWSER-RECEIPT.json")
    if browser["status"]!="PASS" or browser["testCount"]<12:
        raise RuntimeError("LEDGER_BROWSER_OWNER_NOT_PASS")
    if sha_file(folder/"BROWSER-RECEIPT.json")!=receipt["browserReceiptSha"]:
        raise RuntimeError("LEDGER_BROWSER_RECEIPT_SHA_DRIFT")
    verify_journal(folder/"journal.jsonl")
    return {"verified":True,"status":"LEDGER_PROJECT_PASS",
            "browserTests":browser["testCount"],
            "ownerWasiTests":len(spec["acceptance"]),
            "originalAiJob":jobid,"zipSha256":sha_file(zipfile_path),
            "archive":str(zipfile_path)}

def export(root,jobid):
    root=engine.init(root)
    trust=webapps.preflight(root)
    d,spec,files,owner=_verify_source(root,jobid)
    projects=root/"projects";projects.mkdir(parents=True,exist_ok=True)
    folder=projects/("LEDGER-"+jobid)
    if folder.exists():
        return {"status":"EXISTING_VERIFIED_NO_REPLAY","verify":_verify_package(root,jobid)}
    folder.mkdir()
    event(folder/"journal.jsonl","LEDGER_INTENT",{
      "originalModelSourceSha":sha_file(d/"proposed.json"),
      "originalOwnerManifestSha":sha_file(d/"manifest.json"),
      "model":"original direct source-only localhost"})
    bundle=projects/("LEDGER-"+jobid+".zip")
    if bundle.exists():raise RuntimeError("LEDGER_UNREGISTERED_PREEXISTING_ZIP")
    with tempfile.TemporaryDirectory(prefix="AF-LEDGER-",dir=projects) as tmp:
        stage=Path(tmp)
        (stage/"index.html").write_text(_index(jobid),encoding="utf-8")
        (stage/"styles.css").write_text(_css(),encoding="utf-8")
        (stage/"logic.js").write_text("\n;\n".join(files.values()),encoding="utf-8")
        (stage/"controller.js").write_text(_controller(),encoding="utf-8")
        (stage/"README.txt").write_text(
            "AUTOFABRICADOR ledger: extraer el ZIP y abrir index.html.\n"
            "No usa internet ni servidor. Datos en memoria, no persistidos.\n"
            "La logica JS fue aceptada con los casos originales en WASI.\n",encoding="utf-8")
        result=stage/"browser-result.json"
        probe=root/"qa/ledger_browser_probe.js"
        node=webapps.NODE
        try:
            testing=subprocess.run([str(node),str(probe),str(stage),
                   str(webapps.CHROME),str(result)],cwd=root,
                   stdin=subprocess.DEVNULL,capture_output=True,timeout=90)
        except subprocess.TimeoutExpired:
            raise RuntimeError("LEDGER_BROWSER_TIMEOUT_RECONCILE")
        if testing.returncode or not result.exists():
            raise RuntimeError("LEDGER_BROWSER_TEST_FAILED:"+
                testing.stderr.decode("utf-8","replace")[-1200:])
        browser=load(result)
        if (browser["status"]!="PASS" or browser["passed"]!=browser["testCount"]
            or browser["testCount"]<12 or not browser["noExternalNetworkAllowed"]):
            raise RuntimeError("LEDGER_BROWSER_NOT_ACCEPTED")
        write_json(folder/"BROWSER-RECEIPT.json",browser,new=True)
        screenshot=stage/"owner-browser-screenshot.png"
        shutil.copyfile(screenshot,folder/"BROWSER-ACCEPTED.png")
        if sha_file(screenshot)!=sha_file(folder/"BROWSER-ACCEPTED.png"):
            raise RuntimeError("LEDGER_SCREENSHOT_SHA_DRIFT")
        content={p.name:sha_file(p) for p in stage.iterdir() if p.is_file() and p.name not in (
             "browser-result.json","owner-browser-screenshot.png")}
        contract={"schema":1,"kind":"MULTI_MODULE_OFFLINE_LEDGER_SPA",
         "originalAiJob":jobid,
         "originalWasiManifestSha":sha_file(d/"manifest.json"),
         "originalAiSourceSha":sha_file(d/"proposed.json"),
         "originalPreModelOwnerSha":sha_file(d/"owner-acceptance.json"),
         "ownerWasiTests":len(spec["acceptance"]),
         "independentOriginalBrowserTests":browser["testCount"],
         "browserReceiptSha":sha_file(folder/"BROWSER-RECEIPT.json"),
         "browserScreenSha":sha_file(folder/"BROWSER-ACCEPTED.png"),
         "files":content,"browserOffline":True,
         "sourcesAreModelGenerated":sorted(files),
         "browserControllerIsTrustedNotModelGenerated":True,
         "nativeEditorLaunched":False,"atUtc":utc()}
        write_json(folder/"PROJECT-MANIFEST.json",contract,new=True)
        event(folder/"journal.jsonl","LEDGER_BROWSER_OWNER_PASS",
              {"passed":browser["passed"],"receiptSha":sha_file(folder/"BROWSER-RECEIPT.json")})
        with zipfile.ZipFile(bundle,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in sorted(stage.iterdir()):
                if p.name in content:z.write(p,p.name)
            z.write(folder/"PROJECT-MANIFEST.json","PROJECT-MANIFEST.json")
        receipt={"schema":1,"status":"LEDGER_PROJECT_PASS",
           "archiveSha256":sha_file(bundle),
           "originalWasiManifestSha":contract["originalWasiManifestSha"],
           "originalAiSourceSha":contract["originalAiSourceSha"],
           "browserReceiptSha":contract["browserReceiptSha"],
           "files":content,"atUtc":utc(),
           "browserTests":browser["testCount"]}
        write_json(folder/"PROJECT-RECEIPT.json",receipt,new=True)
        event(folder/"journal.jsonl","LEDGER_PROJECT_PACKAGE_ACCEPTED",
              {"archiveSha":receipt["archiveSha256"],
               "receiptSha":sha_file(folder/"PROJECT-RECEIPT.json")})
    return {"status":"LEDGER_PROJECT_PASS","originalAiJob":jobid,
            "verify":_verify_package(root,jobid)}
verify=_verify_package
