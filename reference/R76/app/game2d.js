"use strict";
(() => {
 const W=8,H=8,walls=["2:1","2:2","2:3","3:3","4:3","5:1","5:2","0:5","1:5","2:5","4:5","5:5"];
 const canvas=document.getElementById("game2d-canvas");
 const g=canvas.getContext("2d",{alpha:false});
 const target={x:6,y:6};
 let state,steps,won;
 function reset(){
  state={x:1,y:1,width:W,height:H,walls:[...walls]};
  steps=0;won=false;draw();update();
 }
 function update(){
  document.getElementById("game2d-steps").textContent=String(steps);
  document.getElementById("game2d-status").textContent=won?"¡Objetivo alcanzado!":"En juego";
  document.getElementById("game2d-goal").textContent=won?"Completado":"Recoge la estrella";
 }
 function draw(){
  if(!g)return;
  const cell=canvas.width/W;
  g.fillStyle="#091426";g.fillRect(0,0,canvas.width,canvas.height);
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){
   g.fillStyle=(x+y)%2===0?"#122b42":"#10273b";
   g.fillRect(x*cell+1,y*cell+1,cell-2,cell-2);
  }
  for(const item of walls){
   const [x,y]=item.split(":").map(Number);
   g.fillStyle="#476578";
   g.fillRect(x*cell+4,y*cell+4,cell-8,cell-8);
   g.fillStyle="#6d91a0";g.fillRect(x*cell+6,y*cell+7,cell-12,4);
  }
  g.save();g.translate((target.x+.5)*cell,(target.y+.5)*cell);
  g.fillStyle="#ffd27c";g.shadowColor="#ffc761";g.shadowBlur=20;
  g.beginPath();
  for(let i=0;i<10;i++){
   const a=-Math.PI/2+i*Math.PI/5,r=i%2?9:22;
   const px=Math.cos(a)*r,py=Math.sin(a)*r;
   if(i===0)g.moveTo(px,py);else g.lineTo(px,py);
  }
  g.closePath();g.fill();g.restore();
  const cx=(state.x+.5)*cell,cy=(state.y+.5)*cell;
  g.fillStyle="#9debd1";g.shadowColor="#74ffcd";g.shadowBlur=18;
  g.beginPath();g.arc(cx,cy,cell*.31,0,Math.PI*2);g.fill();g.shadowBlur=0;
  g.fillStyle="#0d3740";g.fillRect(cx-cell*.12,cy-cell*.09,cell*.24,cell*.18);
  g.fillStyle="#0a1320";g.beginPath();g.arc(cx-cell*.06,cy,2.8,0,Math.PI*2);g.arc(cx+cell*.06,cy,2.8,0,Math.PI*2);g.fill();
  if(won){
   g.fillStyle="#0b2437dd";g.fillRect(20,194,440,85);
   g.fillStyle="#b4ffe0";g.font="bold 27px system-ui";g.textAlign="center";
   g.fillText("¡Nivel completado!",240,245);
  }
 }
 function move(dir){
  if(won)return snapshot();
  if(typeof window.stepRobot!=="function")throw Error("R75_2D_MODEL_FUNCTION_UNAVAILABLE");
  const old=state;
  const next=window.stepRobot(old,dir);
  if(next && next.moved && Number.isInteger(next.x) && Number.isInteger(next.y)
       && next.x>=0 && next.x<W && next.y>=0 && next.y<H){
   state={...state,x:next.x,y:next.y};steps++;
   won=state.x===target.x&&state.y===target.y;
  }
  draw();update();return snapshot();
 }
 function snapshot(){
  const px=g.getImageData((state.x+.5)*(canvas.width/W),(state.y+.5)*(canvas.height/H),1,1).data;
  return {x:state.x,y:state.y,steps,won,
    walls:[...state.walls],modelFunctionUsed:typeof window.stepRobot==="function",
    pixel:Array.from(px),canvas2D:true};
 }
 document.getElementById("game2d-reset").addEventListener("click",reset);
 for(const b of document.querySelectorAll("[data-move]")){
  b.addEventListener("click",()=>move(b.dataset.move));
 }
 document.addEventListener("keydown",event=>{
  if(["INPUT","TEXTAREA"].includes(document.activeElement?.tagName))return;
  const map={ArrowUp:"N",ArrowDown:"S",ArrowLeft:"W",ArrowRight:"E"};
  if(map[event.key]&&document.getElementById("tab-game2d").classList.contains("active")){
   event.preventDefault();move(map[event.key]);
  }
 });
 window.AF2D={move,reset,snapshot};
 reset();
})();
