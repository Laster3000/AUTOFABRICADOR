"use strict";
/* R88 original 16:9 point-and-click vertical slice. No network dependencies.
   320x180 native art grid -> 640x360 reference display, integer 2x scale.
   All graphics and narrative are original. Artistic acceptance is separate. */
(() => {
  const c=document.getElementById("game");
  const g=c.getContext("2d",{alpha:false});
  const dialog=document.getElementById("dialog");
  const ending=document.getElementById("ending");
  const error=document.getElementById("error");
  const STORE="autofabricador-r88-bruma-16-9-v1";
  const VERBS=["IR","MIRAR","COGER","USAR","HABLAR"];
  const ACTIVITIES=["idle","walk","talk","look","pick","use","react"];
  const FRAMES={idle:[0,1],walk:[2,3,4,5],talk:[6,7],look:[8],pick:[9],use:[10,11],react:[12,13]};
  const pics={};
  const initial=()=>({
    version:1,scene:"harbor",verb:"IR",selected:null,
    inventory:[],flags:{talked:false,lensInstalled:false,compassInstalled:false,calibrated:false,lit:false},
    hero:{x:43,y:117,target:null},
    bubble:"El puerto duerme. El faro necesita otra luz.",bubbleUntil:performance.now()+8000,
    hover:null,dialogOpen:false,done:false,action:null,speed:55,
    animation:"idle",animationUntil:0,lastAction:"START"
  });
  let state=initial();
  let ready=false;
  let last=0;
  let soundContext=null;
  const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
  function tell(message,ms=4200){
    state.bubble=String(message).slice(0,160);
    state.bubbleUntil=performance.now()+ms;
  }
  function beep(freq=520,ms=65){
    try{
      const Audio=window.AudioContext||window.webkitAudioContext;
      if(!Audio)return;
      soundContext=soundContext||new Audio();
      if(soundContext.state==="suspended")soundContext.resume().catch(()=>{});
      const osc=soundContext.createOscillator(),gain=soundContext.createGain();
      osc.type="triangle";osc.frequency.value=freq;
      gain.gain.setValueAtTime(0.017,soundContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001,soundContext.currentTime+ms/1000);
      osc.connect(gain);gain.connect(soundContext.destination);
      osc.start();osc.stop(soundContext.currentTime+ms/1000);
    }catch(_){}
  }
  const has=item=>state.inventory.includes(item);
  const add=item=>{if(!has(item))state.inventory.push(item);};
  const remove=item=>{state.inventory=state.inventory.filter(x=>x!==item);};
  function anim(name,ms=600){
    state.animation=ACTIVITIES.includes(name)?name:"react";
    state.animationUntil=performance.now()+ms;
  }
  function persist(){
    try{
      const serial={
        version:1,scene:state.scene,inventory:[...state.inventory],
        flags:{...state.flags},hero:{x:state.hero.x,y:state.hero.y},
        done:state.done
      };
      localStorage.setItem(STORE,JSON.stringify(serial));
      tell("La partida ha quedado guardada.",2300);beep(780,90);
      return true;
    }catch(e){tell("No puedo guardar: revisa el almacenamiento.",4000);return false;}
  }
  function load(){
    try{
      const raw=localStorage.getItem(STORE);
      if(!raw){tell("No hay una partida guardada.");return false;}
      const o=JSON.parse(raw);
      if(!o||o.version!==1||!["harbor","workshop"].includes(o.scene)||
        !Array.isArray(o.inventory)||o.inventory.some(x=>!["lens","compass"].includes(x))||
        typeof o.flags!=="object"||!o.flags)throw Error("BAD_SAVE");
      const validFlags=["talked","lensInstalled","compassInstalled","calibrated","lit"];
      if(validFlags.some(x=>typeof o.flags[x]!=="boolean")||
         o.flags.calibrated && !(o.flags.lensInstalled&&o.flags.compassInstalled) ||
         (o.flags.lit && !o.flags.calibrated) || (Boolean(o.done)!==o.flags.lit))throw Error("BAD_FLAGS");
      if(!o.hero||!Number.isFinite(o.hero.x)||!Number.isFinite(o.hero.y)||
        o.hero.x<0||o.hero.x>320||o.hero.y<90||o.hero.y>=130)throw Error("BAD_POSITION");
      state=initial();state.scene=o.scene;
      state.inventory=[...new Set(o.inventory)];
      state.flags={...o.flags};state.done=Boolean(o.done);
      state.hero.x=o.hero.x;state.hero.y=o.hero.y;
      closeDialog();ending.classList.add("hidden");
      tell("Partida cargada. El mundo vuelve a su sitio.");
      if(state.done)finish(true);
      return true;
    }catch(e){tell("El guardado es incompatible o está dañado.",4400);return false;}
  }
  function reset(){
    state=initial();closeDialog();ending.classList.add("hidden");
    try{localStorage.removeItem(STORE);}catch(_){}
    tell("La aventura comienza de nuevo.",3500);
  }
  function closeDialog(){dialog.classList.add("hidden");dialog.replaceChildren();state.dialogOpen=false;}
  function openDialogue(){
    state.dialogOpen=true;beep(620,90);anim("talk",1000);
    dialog.classList.remove("hidden");
    dialog.innerHTML="";
    const h=document.createElement("h2");
    h.textContent="El guardafaro";
    const p=document.createElement("p");
    p.textContent="«Hace años que no veo una noche tan oscura. ¿Qué quieres saber, marinero?»";
    const choices=document.createElement("div");choices.className="dialog-options";
    const options=[
      ["¿Por qué se apagó el faro?",()=>{
        state.flags.talked=true;
        tell("«El mecanismo perdió su lente... y la brújula dejó de señalar el norte.»",9000);
        closeDialog();persistSilently();
      }],
      ["Háblame de esa vieja torre.",()=>{
        state.flags.talked=true;
        tell("«Construí su luz cuando todavía creía que el mar podía guardar secretos.»",9500);
        closeDialog();persistSilently();
      }],
      ["Volveré cuando descubra algo.",()=>{
        tell("«Las buenas respuestas llegan a quien sabe escuchar.»",5500);
        closeDialog();
      }]
    ];
    for(const [label,action] of options){
      const b=document.createElement("button");b.type="button";b.textContent=label;
      b.addEventListener("click",action);choices.append(b);
    }
    dialog.append(h,p,choices);
    choices.querySelector("button")?.focus();
  }
  function persistSilently(){
    try{localStorage.setItem(STORE,JSON.stringify({
      version:1,scene:state.scene,inventory:[...state.inventory],
      flags:{...state.flags},hero:{x:state.hero.x,y:state.hero.y},
      done:state.done
    }));}catch(_){}
  }
  function finish(isLoad=false){
    state.done=true;
    ending.classList.remove("hidden");
    ending.innerHTML="";
    const h=document.createElement("h2");h.textContent="LA LUZ DE BRUMA";
    const p=document.createElement("p");
    p.textContent="El faro vuelve a encenderse. Los barcos encuentran su camino y el anciano sonríe por primera vez en muchos años.";
    const foot=document.createElement("p");foot.textContent="Fin del prólogo · Aventura original 16:9";
    const b=document.createElement("button");b.textContent="Jugar de nuevo";b.onclick=reset;
    ending.append(h,p,foot,b);
    if(!isLoad){tell("¡El faro vuelve a iluminar el puerto!",11000);beep(900,150);persistSilently();}
  }
  function enter(where){
    state.scene=where;
    state.hero={x:where==="harbor"?74:287,y:116,target:null};
    state.selected=null;state.animation="idle";state.action=null;
    tell(where==="harbor"?"Una brisa salada recorre el muelle.":"El taller huele a cobre y madera vieja.",5200);
    persistSilently();
  }
  function use(target){
    if(target==="mechanism"){
      if(state.selected==="lens"&&has("lens")&&!state.flags.lensInstalled){
        remove("lens");state.flags.lensInstalled=true;state.selected=null;
        anim("use");tell("La lente encaja y devuelve un reflejo dorado.",5500);
        beep(720,95);persistSilently();return;
      }
      if(state.selected==="compass"&&has("compass")&&!state.flags.compassInstalled){
        remove("compass");state.flags.compassInstalled=true;state.selected=null;
        anim("use");
        state.flags.calibrated=state.flags.lensInstalled&&state.flags.compassInstalled;
        tell(state.flags.calibrated?"El engranaje despierta. Ya puedes encender el faro.":"La brújula está puesta. Falta instalar una lente.",6800);
        beep(810,110);persistSilently();return;
      }
      if(state.flags.calibrated){tell("El mecanismo ya funciona. Falta encender el faro.");return;}
      tell("Necesitas colocar una lente y una brújula. Selecciona cada objeto del inventario.",7200);return;
    }
    if(target==="lighthouse"){
      if(!state.flags.calibrated){tell("El faro necesita su mecanismo reparado. Busca en el taller.",7000);return;}
      if(state.flags.lit){tell("La luz sigue encendida.");return;}
      state.flags.lit=true;anim("use",1000);finish();return;
    }
    tell("No parece que esos objetos encajen.",4400);
  }
  function perform(hot){
    const id=hot.id;const v=state.verb;state.lastAction=v+":"+id;
    if(v==="MIRAR"){
      const lines={
        lens_pickup:state.inventory.includes("lens")?"El lugar donde estaba la lente.":"Una lente de cobre con cristal azul.",
        elder:"Su barba es blanca como la espuma. Mira el faro con preocupación.",
        tavern_door:"La puerta del taller. Huele a madera y aceite.",
        lighthouse:state.flags.lit?"Una luz cálida atraviesa la niebla.":"La torre perdió su luz.",
        mechanism:"Parece una máquina de orientación náutica.",
        compass_pickup:has("compass")?"Queda la marca de una vieja brújula.":"Una brújula de latón, pequeña pero precisa.",
        exit_door:"El puerto espera al otro lado.",
        bookshelf:"Manuales, mapas marítimos y viejos secretos."
      };
      anim("look");tell(lines[id]||hot.feedback,5800);return;
    }
    if(v==="HABLAR"&&id==="elder"){openDialogue();return;}
    if(v==="COGER"&&id==="lens_pickup"){
      if(state.flags.lensInstalled){tell("La lente sigue encajada en el mecanismo.");return;}
      if(has("lens")){tell("Ya tienes la lente en tu mochila.");return;}
      add("lens");anim("pick");beep(760,90);
      tell("Guardas la lente de latón. Puede servir para el mecanismo.",5700);
      persistSilently();return;
    }
    if(v==="COGER"&&id==="compass_pickup"){
      if(state.flags.compassInstalled){tell("La brújula ya forma parte del mecanismo.");return;}
      if(has("compass")){tell("Ya tienes la brújula.");return;}
      add("compass");anim("pick");beep(820,80);
      tell("Coges la brújula. La aguja aún parece viva.",6000);
      persistSilently();return;
    }
    if((v==="IR"||v==="ABRIR")&&id==="tavern_door"){enter("workshop");return;}
    if((v==="IR"||v==="ABRIR")&&id==="exit_door"){enter("harbor");return;}
    if(v==="USAR"){use(id);return;}
    if(v==="IR"){tell("Llegas hasta "+hot.name.toLowerCase()+".");return;}
    tell(hot.feedback,5000);
  }
  function walkTo(x,y,after=null){
    if(state.dialogOpen||state.done)return;
    state.hero.target=[clamp(x,5,315),clamp(y,92,128)];
    state.action=after;
    state.animation="walk";state.lastAction="WALKING";
  }
  function pointIn(poly,x,y){
    let inside=false;
    for(let i=0,j=poly.length-1;i<poly.length;j=i++){
      const [xi,yi]=poly[i],[xj,yj]=poly[j];
      if(yi>y!==yj>y && x<(xj-xi)*(y-yi)/(yj-yi)+xi)inside=!inside;
    }
    return inside;
  }
  function hotspot(x,y){
    const list=WORLD.scenes[state.scene].hotspots;
    return list.slice().reverse().find(it=>pointIn(it.polygon,x,y))||null;
  }
  function clickWorld(x,y){
    if(state.done||state.dialogOpen)return;
    if(y>=130){
      if(y<152){
        let slot=Math.floor(x/64);
        if(slot>=0&&slot<VERBS.length){
          state.verb=VERBS[slot];
          if(state.verb!=="USAR")state.selected=null;
          beep(380+slot*50,35);
        }
      }else if(y<177){
        const slot=Math.floor(x/50);
        const item=state.inventory[slot];
        if(item){state.selected=item;state.verb="USAR";tell("Usar "+(item==="lens"?"lente":"brújula")+" con...",3000);}
      }
      return;
    }
    const target=hotspot(x,y);
    if(!target){walkTo(x,Math.max(y,93));return;}
    if(state.verb==="IR"&&!["tavern_door","exit_door"].includes(target.id)){
      walkTo(...target.walkTo,()=>perform(target));return;
    }
    walkTo(...target.walkTo,()=>perform(target));
  }
  function frameAt(){
    const ids=FRAMES[state.animation]||FRAMES.idle;
    return ids[Math.floor(performance.now()/260)%ids.length];
  }
  function drawCharacter(id,x,y,animation=frameAt()){
    const img=pics[id];if(!img)return;
    g.drawImage(img,animation*24,0,24,48,Math.round(x-12),Math.round(y-47),24,48);
  }
  function drawMessage(){
    if(!state.bubble||performance.now()>state.bubbleUntil)return;
    g.fillStyle="#080d23";
    g.fillRect(7,5,306,29);
    g.fillStyle="#c29d6d";
    g.fillRect(7,5,306,1);g.fillRect(7,33,306,1);
    const words=state.bubble.split(/\s+/);
    let line="",rows=[];
    for(const word of words){
      if((line+" "+word).length>54){rows.push(line);line=word;}
      else line+=(line?" ":"")+word;
    }
    if(line)rows.push(line);
    g.fillStyle="#f6dfad";g.font="7px monospace";
    rows.slice(0,3).forEach((row,i)=>g.fillText(row,12,14+i*8));
  }
  function drawInterface(){
    if(pics.interface)g.drawImage(pics.interface,0,130);
    g.font="bold 9px monospace";
    VERBS.forEach((verb,i)=>{
      if(verb===state.verb){
        g.fillStyle="#b77d59";g.fillRect(i*64+3,136,57,15);
        g.fillStyle="#f8e2a2";
      }else g.fillStyle="#d5b28b";
      g.fillText(verb,i*64+6,146);
    });
    g.font="7px monospace";g.fillStyle="#e4c78e";
    state.inventory.forEach((item,i)=>{
      if(i>=6)return;
      if(item===state.selected){g.fillStyle="#956357";g.fillRect(i*50+4,154,45,20);}
      if(pics[item])g.drawImage(pics[item],i*50+8,155);
      g.fillStyle="#f1ddac";
      g.fillText(item==="lens"?"LENTE":"BRUJULA",i*50+27,166);
    });
    g.fillStyle="#b8a48b";g.fillText((WORLD.scenes[state.scene].id==="harbor"?"PUERTO DE BRUMA":"TALLER DEL FARO"),165,175);
  }
  function draw(t){
    g.imageSmoothingEnabled=false;
    g.fillStyle="#080c1b";g.fillRect(0,0,320,180);
    if(pics[WORLD.sceneBackgrounds[state.scene]])
      g.drawImage(pics[WORLD.sceneBackgrounds[state.scene]],0,0);
    if(state.scene==="harbor"){
      if(!has("lens")&&!state.flags.lensInstalled)g.drawImage(pics.lens,98,95);
      const elderFrame=FRAMES.idle[Math.floor(t/800)%2];
      drawCharacter("elder_whitebeard",168,117,elderFrame);
      if(state.flags.lit){
        g.fillStyle="#f4d19c";g.fillRect(283,35,10,2);
        for(let x=290;x<320;x+=4)g.fillRect(x,35-Math.round((x-290)*.22),2,1);
      }
    }else{
      if(!has("compass")&&!state.flags.compassInstalled)g.drawImage(pics.compass,83,99);
      if(state.flags.lensInstalled){g.fillStyle="#b0e5d2";g.fillRect(250,84,6,5);}
      if(state.flags.compassInstalled){g.fillStyle="#f6cf87";g.fillRect(241,83,5,3);}
    }
    drawCharacter("young_sailor",state.hero.x,state.hero.y);
    drawMessage();
    drawInterface();
    if(state.hover&&state.hover.name){
      g.fillStyle="#eddfb2";g.font="7px monospace";
      g.fillText(state.hover.name,clamp(160-state.hover.name.length*2,4,252),126);
    }
  }
  function loop(t){
    if(!ready)return;
    const dt=Math.min(.06,(t-last)/1000||0.016);last=t;
    if(state.hero.target&&!state.dialogOpen){
      const [x,y]=state.hero.target;
      const dx=x-state.hero.x,dy=y-state.hero.y,len=Math.hypot(dx,dy);
      const dist=state.speed*dt;
      if(len<=dist||len<1){
        state.hero.x=x;state.hero.y=y;state.hero.target=null;
        state.animation="idle";
        const follow=state.action;state.action=null;
        if(typeof follow==="function")follow();
      }else{
        state.hero.x+=dx/len*dist;state.hero.y+=dy/len*dist;
        state.animation="walk";
      }
    }else if(t>state.animationUntil){state.animation="idle";}
    draw(t);requestAnimationFrame(loop);
  }
  function coords(event){
    const r=c.getBoundingClientRect();
    return [(event.clientX-r.left)*320/r.width,(event.clientY-r.top)*180/r.height];
  }
  c.addEventListener("pointermove",e=>{
    const [x,y]=coords(e);state.hover=y<130?hotspot(x,y):null;
    c.style.cursor=state.hover?"pointer":"crosshair";
  });
  c.addEventListener("pointerleave",()=>{state.hover=null;});
  c.addEventListener("pointerdown",e=>{
    e.preventDefault();
    if(!ready)return;
    const [x,y]=coords(e);
    clickWorld(x,y);c.focus();
  });
  document.addEventListener("keydown",e=>{
    if(e.target instanceof HTMLButtonElement)return;
    if(e.key>="1"&&e.key<="5"){
      state.verb=VERBS[Number(e.key)-1];if(state.verb!=="USAR")state.selected=null;
      e.preventDefault();
    }else if(e.key.toLowerCase()==="s"&&e.ctrlKey){e.preventDefault();persist();}
    else if(e.key.toLowerCase()==="l"&&e.ctrlKey){e.preventDefault();load();}
    else if(e.key==="Escape"){closeDialog();}
    else if(e.code==="Space"){state.bubbleUntil=0;e.preventDefault();}
  });
  document.getElementById("btn-save").onclick=persist;
  document.getElementById("btn-load").onclick=load;
  document.getElementById("btn-new").onclick=reset;
  document.getElementById("btn-fullscreen").onclick=()=>{
    const root=document.getElementById("shell");
    if(!document.fullscreenElement)root.requestFullscreen?.().catch(()=>{});
    else document.exitFullscreen?.().catch(()=>{});
  };
  function start(){
    const entries=Object.entries(WORLD.assets);
    Promise.all(entries.map(([id,path])=>new Promise((resolve,reject)=>{
      const img=new Image();
      img.onload=()=>{pics[id]=img;resolve();};
      img.onerror=()=>reject(Error("Falta recurso "+path));
      img.src=path;
    }))).then(()=>{
      ready=true;
      c.focus({preventScroll:true});
      requestAnimationFrame(loop);
    }).catch(e=>{error.classList.remove("hidden");error.textContent=e.message;});
  }
  Object.defineProperty(window,"AF_R88_READONLY",{
    get:()=>Object.freeze(JSON.parse(JSON.stringify({
      ready,aspect:"16:9",artGrid:[320,180],presentation:[640,360],
      scene:state.scene,verb:state.verb,selected:state.selected,
      inventory:[...state.inventory],flags:{...state.flags},hero:{x:state.hero.x,y:state.hero.y},
      lastAction:state.lastAction,dialogOpen:state.dialogOpen,done:state.done,
      assetLoaded:Object.keys(pics).length,canvas:[c.width,c.height],
      availableObjects:{lens:!has("lens")&&!state.flags.lensInstalled,compass:!has("compass")&&!state.flags.compassInstalled}
    }))),configurable:false
  });
  start();
})();