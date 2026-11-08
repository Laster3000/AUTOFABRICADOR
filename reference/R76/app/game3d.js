"use strict";
(() => {
 const canvas=document.getElementById("game3d-canvas");
 const fail=document.getElementById("game3d-fail");
 const gl=canvas.getContext("webgl2",{antialias:false,preserveDrawingBuffer:true});
 const target={x:0,y:0,z:6};
 let camera,won,frames=0,t=0,glError=null;
 if(!gl){
  fail.hidden=false;glError="WEBGL2_UNAVAILABLE";
  window.AF3D={snapshot:()=>({available:false,error:glError})};
  return;
 }
 const vert="#version 300 es\nprecision highp float;\nin vec3 pos;\nin vec3 color;\nuniform float angle;\nuniform vec3 camera;\nout vec3 vcolor;\nvoid main(){float c=cos(angle),s=sin(angle);vec3 r=vec3(pos.x*c+pos.z*s,pos.y,-pos.x*s+pos.z*c);vec3 p=r+vec3(0.,0.,6.)-camera;float z=max(0.1,p.z);gl_Position=vec4(p.x*1.8,p.y*1.8,p.z*0.75,z);vcolor=color;}";
 const frag="#version 300 es\nprecision highp float;\nin vec3 vcolor;\nout vec4 outColor;\nvoid main(){outColor=vec4(vcolor,1.0);}";
 function shader(type,src){
  const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);
  if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));
  return s;
 }
 const program=gl.createProgram();
 gl.attachShader(program,shader(gl.VERTEX_SHADER,vert));
 gl.attachShader(program,shader(gl.FRAGMENT_SHADER,frag));
 gl.linkProgram(program);
 if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
 const faces=[
 [[-.8,-.8,.8],[.8,-.8,.8],[.8,.8,.8],[-.8,.8,.8],[.25,.92,.77]],
 [[.8,-.8,-.8],[-.8,-.8,-.8],[-.8,.8,-.8],[.8,.8,-.8],[.15,.6,.8]],
 [[-.8,-.8,-.8],[-.8,-.8,.8],[-.8,.8,.8],[-.8,.8,-.8],[.96,.46,.52]],
 [[.8,-.8,.8],[.8,-.8,-.8],[.8,.8,-.8],[.8,.8,.8],[.65,.5,.91]],
 [[-.8,.8,.8],[.8,.8,.8],[.8,.8,-.8],[-.8,.8,-.8],[.95,.76,.34]],
 [[-.8,-.8,-.8],[.8,-.8,-.8],[.8,-.8,.8],[-.8,-.8,.8],[.37,.75,.53]]
 ];
 const vertices=[];
 for(const face of faces){
  for(const i of [0,1,2,0,2,3])vertices.push(...face[i],...face[4]);
 }
 const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
 gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
 gl.useProgram(program);
 const pos=gl.getAttribLocation(program,"pos");
 const color=gl.getAttribLocation(program,"color");
 gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,3,gl.FLOAT,false,24,0);
 gl.enableVertexAttribArray(color);gl.vertexAttribPointer(color,3,gl.FLOAT,false,24,12);
 const uniformAngle=gl.getUniformLocation(program,"angle");
 const uniformCam=gl.getUniformLocation(program,"camera");
 gl.enable(gl.DEPTH_TEST);
 function projection(){
  if(typeof window.projectPoint!=="function")return null;
  return window.projectPoint(target,{x:camera.x,y:camera.y,z:camera.z,focal:100});
 }
 function distance(){return Math.hypot(target.x-camera.x,target.z-camera.z);}
 function display(){
  document.getElementById("game3d-x").textContent=camera.x.toFixed(1);
  document.getElementById("game3d-dist").textContent=distance().toFixed(1);
  const p=projection();
  document.getElementById("game3d-projection").textContent=p?p.u+", "+p.v:"Fuera de visión";
  document.getElementById("game3d-status").textContent=won?"¡Objetivo recogido!":"Explorando";
 }
 function reset(){camera={x:0,y:0,z:0};won=false;t=0;display();render();}
 function move(direction){
  const next={...camera};
  if(direction==="left")next.x=Math.max(-3,next.x-.5);
  if(direction==="right")next.x=Math.min(3,next.x+.5);
  if(direction==="forward")next.z=Math.min(5,next.z+.5);
  if(direction==="back")next.z=Math.max(-3,next.z-.5);
  // Invisible world perimeter and nearby target bounds are hard collision limits.
  camera=next;display();render();return snapshot();
 }
 function collect(){if(distance()<=1.5){won=true;display();render()}return snapshot();}
 function render(){
  if(!gl)return;
  gl.viewport(0,0,canvas.width,canvas.height);
  gl.clearColor(.035,.085,.14,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.useProgram(program);gl.uniform1f(uniformAngle,t);
  gl.uniform3f(uniformCam,camera.x,camera.y,camera.z);
  gl.drawArrays(gl.TRIANGLES,0,36);
  frames++;glError=gl.getError();
 }
 function frame(){
  if(!document.hidden && document.getElementById("tab-game3d").classList.contains("active")){
   t+=.012;render();
  }
  requestAnimationFrame(frame);
 }
 function snapshot(){
  const pixels=new Uint8Array(4);
  gl.readPixels(canvas.width/2,canvas.height/2,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
  return {available:true,webglVersion:String(gl.getParameter(gl.VERSION)).slice(0,100),
    x:camera.x,z:camera.z,distance:distance(),won,
    projection:projection(),usesR75ModelProjection:typeof window.projectPoint==="function",
    centerPixel:Array.from(pixels),drawError:glError,frames};
 }
 document.getElementById("game3d-reset").addEventListener("click",reset);
 document.getElementById("game3d-collect").addEventListener("click",collect);
 for(const b of document.querySelectorAll("[data-3d]")){
  b.addEventListener("click",()=>move(b.dataset["3d"]));
 }
 document.addEventListener("keydown",event=>{
  if(["INPUT","TEXTAREA"].includes(document.activeElement?.tagName))return;
  if(!document.getElementById("tab-game3d").classList.contains("active"))return;
  const map={ArrowUp:"forward",ArrowDown:"back",ArrowLeft:"left",ArrowRight:"right"};
  if(map[event.key]){event.preventDefault();move(map[event.key]);}
  if(event.key===" "){event.preventDefault();collect();}
 });
 window.AF3D={snapshot,move,collect,reset,render};
 reset();requestAnimationFrame(frame);
})();
