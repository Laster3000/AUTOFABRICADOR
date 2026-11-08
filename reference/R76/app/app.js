"use strict";
(() => {
 let csrf="",username="",serverReady=false,aiEnabled=false;
 const $=id=>document.getElementById(id);
 const tabs=[...document.querySelectorAll(".tabs button")];
 function activate(name){
  const allowed=["inventory","game2d","game3d","ai","about"];
  if(!allowed.includes(name))name="inventory";
  for(const tab of tabs){
   const on=tab.dataset.tab===name;
   tab.classList.toggle("active",on);tab.setAttribute("aria-selected",on?"true":"false");
   const panel=$("tab-"+tab.dataset.tab);
   panel.classList.toggle("active",on);panel.hidden=!on;
  }
  if(name==="game3d" && window.AF3D)window.AF3D.render();
  history.replaceState(null,"","#"+name);
 }
 tabs.forEach(b=>b.addEventListener("click",()=>activate(b.dataset.tab)));
 async function api(path,opts={}){
  const method=opts.method||"GET";
  const headers={"Content-Type":"application/json"};
  if(csrf && method!=="GET")headers["X-CSRF-Token"]=csrf;
  const res=await fetch(path,{method,headers,credentials:"same-origin",
    body:opts.data===undefined?undefined:JSON.stringify(opts.data),
    cache:"no-store"});
  let data;
  try{data=await res.json()}catch(e){data={error:"INVALID_SERVER_REPLY"}}
  if(!res.ok){
   const error=new Error(data.error||"HTTP_"+res.status);
   error.httpStatus=res.status;throw error;
  }
  return data;
 }
 function authUI(logged){
  $("auth-login").hidden=logged;$("auth-content").hidden=!logged;
  if(logged)$("user-welcome").textContent="Sesión local: "+username;
 }
 async function refresh(){
  try{
   const data=await api("/api/items");
   const body=$("items-body");body.replaceChildren();
   for(const item of data.items){
    const tr=document.createElement("tr");
    for(const field of ["sku","name","qty","version"]){
     const cell=document.createElement("td");cell.textContent=String(item[field]);tr.append(cell);
    }
    const actions=document.createElement("td");
    for(const [label,callback] of [
     ["+1",()=>changeQuantity(item,Math.min(100000,item.qty+1))],
     ["−1",()=>changeQuantity(item,Math.max(0,item.qty-1))],
     ["Eliminar",()=>removeItem(item)]]){
     const button=document.createElement("button");
     button.textContent=label;
     button.setAttribute("aria-label",label+" "+item.sku);
     button.addEventListener("click",callback);actions.append(button);
    }
    tr.append(actions);body.append(tr);
   }
   $("inventory-msg").textContent=data.items.length+" producto(s) actualizados.";
   const audit=await api("/api/audit");
   $("audit-log").textContent=audit.events.map(x=>x.ts+" "+x.action+" "+x.sku).join("\n")||"Sin eventos";
  }catch(error){$("inventory-msg").textContent="No se pudo consultar: "+error.message;}
 }
 async function changeQuantity(item,newQty){
  try{
   await api("/api/items/"+encodeURIComponent(item.sku),
      {method:"PATCH",data:{qty:newQty,expectedVersion:item.version}});
   await refresh();
  }catch(error){$("inventory-msg").textContent="Cambio rechazado: "+error.message;await refresh();}
 }
 async function removeItem(item){
  try{
   await api("/api/items/"+encodeURIComponent(item.sku),
      {method:"DELETE",data:{expectedVersion:item.version}});
   await refresh();
  }catch(error){$("inventory-msg").textContent="Eliminación rechazada: "+error.message;await refresh();}
 }
 $("login-form").addEventListener("submit",async event=>{
  event.preventDefault();$("login-msg").textContent="Comprobando credenciales...";
  try{
   const user=$("login-user").value;
   const result=await api("/api/login",{method:"POST",
      data:{username:user,password:$("login-password").value}});
   $("login-password").value="";csrf=result.csrf;username=result.username;
   authUI(true);$("login-msg").textContent="";await refresh();
  }catch(error){$("login-password").value="";$("login-msg").textContent="Acceso denegado: "+error.message;}
 });
 $("create-form").addEventListener("submit",async event=>{
  event.preventDefault();
  try{
   const payload={sku:$("sku").value.trim().toUpperCase(),
                 name:$("item-name").value.trim(),qty:Number($("item-qty").value)};
   if(typeof window.routeApi!=="function")throw new Error("R76_VERIFIED_API_MODEL_NOT_LOADED");
   const modelCheck=window.routeApi("POST","/items",{sku:payload.sku,qty:payload.qty});
   if(!modelCheck || modelCheck.status!==201)throw new Error("R76_MODEL_RULE_REJECTED_INPUT");
   await api("/api/items",{method:"POST",data:payload});
   $("sku").value="";$("item-name").value="";$("item-qty").value="5";
   await refresh();
  }catch(error){$("inventory-msg").textContent="No añadido: "+error.message;}
 });
 $("refresh-items").addEventListener("click",refresh);
 $("logout").addEventListener("click",async()=>{
  try{await api("/api/logout",{method:"POST",data:{}})}catch(e){}
  csrf="";username="";authUI(false);
 });
 $("ai-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const out=$("ai-result");
  if(!csrf){out.textContent="Inicia sesión en Inventario antes de consultar la IA.";return;}
  const message=$("ai-prompt").value.trim();
  if(!message){out.textContent="Escribe una consulta.";return;}
  out.textContent="Solicitando respuesta al modelo local...";
  try{
   const answer=await api("/api/ai",{method:"POST",data:{prompt:message}});
   out.textContent=answer.text+"\n\n("+answer.mode+")";
  }catch(error){out.textContent="IA no disponible: "+error.message;}
 });
 async function initialize(){
  try{
   const h=await api("/api/health");
   serverReady=h.status==="ok";aiEnabled=h.aiEnabled===true;
   $("server-pill").textContent=serverReady?"Servidor local · operativo":"Error de conexión";
   $("ai-availability").textContent=aiEnabled?
      "Motor local disponible bajo petición; se comprobará GPU y memoria antes de arrancar.":
      "Motor desactivado. El servidor debe arrancarse expresamente con --enable-local-ai.";
   try{
    const data=await api("/api/session");
    csrf=data.csrf;username=data.username;authUI(true);await refresh();
   }catch(e){authUI(false);}
  }catch(e){
   $("server-pill").textContent="Servidor local no accesible";
   $("ai-availability").textContent="Servidor no disponible";
  }
  activate(location.hash.slice(1)||"inventory");
  // PWA caches only first-party static resources, never sessions or API data.
  if("serviceWorker" in navigator && location.hostname==="127.0.0.1"){
   navigator.serviceWorker.register("/service-worker.js").catch(()=>{});
  }
 }
 window.AFAPP={get status(){return {serverReady,aiEnabled,username,sessionActive:!!csrf}},
   activate,refresh};
 initialize();
})();
