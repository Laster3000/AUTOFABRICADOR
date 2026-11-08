# coding: utf-8
"""R88 original 16:9 pixel art assets, editable masters and owner-frozen manifests.
No external art, no imported LucasArts resources, no network and no model access.
The deterministic art is a technical prototype, subject to HUMAN visual acceptance.
"""
from __future__ import annotations
import hashlib, json, math, random, struct, zipfile, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
ASSET=ROOT/"assets"
SOURCE=ROOT/"source"
ASSET.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
rnd=random.Random(1987)
C={
"void":(9,12,32),"night":(17,24,48),"sky":(32,43,71),"sky2":(47,50,77),
"violet":(72,49,75),"rose":(101,55,75),"dusk":(147,73,77),"amber":(212,119,80),
"glow":(240,171,99),"cream":(252,215,145),"gold":(197,143,65),
"navy":(19,42,64),"sea":(22,64,81),"sea2":(36,88,99),"teal":(47,117,118),
"surf":(84,143,135),"pale":(152,177,162),
"black":(14,19,32),"ink":(31,29,43),"plum":(66,40,59),"wood":(91,51,55),
"wood2":(118,63,57),"wood3":(151,83,65),"cedar":(182,110,73),
"brick":(100,57,67),"brick2":(137,75,76),"wall":(118,80,91),
"stone":(95,107,110),"stone2":(140,139,129),
"ivory":(237,220,184),"white":(247,237,209),"grey":(170,169,165),
"shadow":(49,36,52),"hair":(54,39,45),"hair2":(86,47,49),
"skin":(218,149,112),"skinshade":(176,104,88),"nose":(240,174,120),
"coat":(39,88,102),"coat2":(62,126,129),"robe":(46,83,107),
"robe2":(72,111,123),"scarf":(191,72,61),"boot":(56,39,52),
"rust":(139,67,54),"copper":(195,130,72),"green":(55,102,82),
"glass":(107,188,176),"blue":(80,153,167),"lens":(140,222,190)
}
def rgba(c,a=255):
 if isinstance(c,str):return (*C[c],a)
 return (*c,a)
class Pixels:
 def __init__(self,w,h):
  self.w=w;self.h=h;self.data=bytearray(w*h*4)
 def dot(self,x,y,c):
  x=int(x);y=int(y)
  if 0<=x<self.w and 0<=y<self.h:
   i=4*(y*self.w+x);self.data[i:i+4]=bytes(rgba(c))
 def rect(self,x,y,w,h,c):
  for yy in range(max(0,int(y)),min(self.h,int(y+h))):
   for xx in range(max(0,int(x)),min(self.w,int(x+w))):self.dot(xx,yy,c)
 def line(self,x0,y0,x1,y1,c):
  x0,y0,x1,y1=map(int,(x0,y0,x1,y1))
  dx=abs(x1-x0);sx=1 if x0<x1 else -1
  dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
  while True:
   self.dot(x0,y0,c)
   if x0==x1 and y0==y1:break
   e=2*err
   if e>=dy:err+=dy;x0+=sx
   if e<=dx:err+=dx;y0+=sy
 def poly(self,pts,c):
  for y in range(max(0,min(p[1] for p in pts)),min(self.h,max(p[1] for p in pts)+1)):
   intersects=[]
   for (ax,ay),(bx,by) in zip(pts,pts[1:]+pts[:1]):
    if (ay>y)!=(by>y):
     x=ax+(y-ay)*(bx-ax)/(by-ay);intersects.append(x)
   intersects.sort()
   for a,b in zip(intersects[::2],intersects[1::2]):
    self.rect(math.ceil(a),y,max(0,math.floor(b)-math.ceil(a)+1),1,c)
 def ellipse(self,cx,cy,rx,ry,c):
  if rx<=0 or ry<=0:return
  for y in range(max(0,int(cy-ry)),min(self.h,int(cy+ry)+1)):
   f=1-((y-cy)/ry)**2
   if f>=0:
    dx=int(rx*math.sqrt(f))
    self.rect(cx-dx,y,2*dx+1,1,c)
 def merge(self,over):
  out=Pixels(self.w,self.h);out.data[:]=self.data
  for i in range(0,len(out.data),4):
   if over.data[i+3]:
    out.data[i:i+4]=over.data[i:i+4]
  return out
 def png(self):
  b=bytes(self.data)
  def chunk(tag,part):
   return struct.pack(">I",len(part))+tag+part+struct.pack(">I",zlib.crc32(tag+part)&0xffffffff)
  scan=b"".join(b"\0"+b[y*self.w*4:(y+1)*self.w*4] for y in range(self.h))
  return (b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",self.w,self.h,8,6,0,0,0))+
   chunk(b"IDAT",zlib.compress(scan,8))+chunk(b"IEND",b""))
def sha(b):return hashlib.sha256(b).hexdigest()
def write_new(path,b):
 if path.exists():raise RuntimeError("R88_ASSET_EXISTS_NO_REPLAY "+str(path))
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open("xb") as f:f.write(b)
 if sha(path.read_bytes())!=sha(b):raise RuntimeError("R88_WRITE_SHA_BAD")
def save(name,kind,base,detail,frame=None):
 combined=base.merge(detail)
 raw=combined.png()
 write_new(ASSET/(name+".png"),raw)
 ora=SOURCE/(name+".ora")
 with zipfile.ZipFile(ora,"x",compression=zipfile.ZIP_DEFLATED) as z:
  z.writestr("mimetype",b"image/openraster",compress_type=zipfile.ZIP_STORED)
  z.writestr("stack.xml",('<?xml version="1.0"?><image w="%d" h="%d" name="%s"><stack>'
   '<layer name="Ink and details" src="data/details.png" x="0" y="0"/>'
   '<layer name="Base colors" src="data/base.png" x="0" y="0"/></stack></image>' %
   (base.w,base.h,name)).encode())
  z.writestr("data/details.png",detail.png())
  z.writestr("data/base.png",base.png())
  z.writestr("mergedimage.png",raw)
 return {"id":name,"kind":kind,"png":"assets/"+name+".png","pngSHA256":sha(raw),
         "master":"source/"+name+".ora","masterSHA256":sha(ora.read_bytes()),"frame":frame}
assets={}
def add(*args):
 record=save(*args)
 assets[record["id"]]=record
def port():
 b=Pixels(320,130);d=Pixels(320,130)
 bands=["night","night","night","sky","sky","sky2","violet","rose","dusk","amber"]
 for y in range(90):
  col=bands[min(9,int(y/9))];b.rect(0,y,320,1,col)
 # celestial light, clouds, islands
 b.ellipse(256,22,10,10,"glow");b.ellipse(255,20,8,8,"cream")
 for x,y in [(13,12),(31,23),(55,8),(114,15),(188,24),(225,8),(280,35),(300,12)]:
  d.rect(x,y,1,1,"cream")
 for cx,cy in [(42,26),(145,38),(286,51)]:
  b.ellipse(cx,cy,23,6,"violet");b.ellipse(cx-11,cy-2,10,5,"sky2")
 b.poly([(0,83),(25,78),(47,81),(63,73),(99,79),(134,86),(180,84),(201,79),(228,85),(257,78),(290,81),(320,76),(320,130),(0,130)],"sea")
 b.poly([(0,82),(22,76),(39,78),(54,73),(72,81),(82,86),(0,97)],"shadow")
 b.poly([(218,86),(247,74),(269,82),(287,78),(320,84),(320,91)],"navy")
 for y in range(91,130):
  for _ in range(15):
   x=rnd.randrange(320)
   col=("sea2" if rnd.randrange(5)<2 else "surf") if y%3==0 else "sea2"
   d.rect(x,y,rnd.randrange(1,6),1,col)
 for y in range(84,121,4):
  for x in range(239+(y%8)//3,276,5):d.rect(x,y,2,1,"glow")
 # left tavern and arched roof
 d.poly([(0,64),(21,51),(65,52),(85,65),(86,117),(0,117)],"wood")
 d.poly([(0,62),(22,43),(66,45),(88,64),(86,68),(22,51),(0,70)],"ink")
 for yy in range(67,116,8):
  d.line(4,yy,80,yy,"wood2")
 for xx in (15,38,64,82):d.rect(xx,57,3,60,"wood2")
 d.rect(24,76,17,25,"shadow");d.rect(27,77,12,21,"glow");d.rect(29,79,8,16,"amber")
 d.rect(52,82,17,34,"black");d.rect(54,86,12,29,"wood2")
 d.poly([(15,62),(65,60),(65,70),(16,72)],"cedar")
 d.rect(29,62,26,7,"wood3")
 # pier and wooden floor
 d.poly([(0,111),(125,104),(151,125),(0,129)],"wood2")
 for y in (110,116,122,128):d.line(0,y,155,y+3,"ink")
 for x in (5,31,61,93,121):d.line(x,109,x+13,129,"wood3")
 for x in (18,74,128,167):
  d.rect(x,107,4,22,"ink");d.rect(x+1,102,2,25,"wood3")
 # right lighthouse
 d.poly([(270,52),(279,39),(297,41),(303,55),(301,110),(268,111)],"stone")
 d.poly([(267,54),(276,48),(302,49),(308,55)],"ink")
 d.rect(274,45,24,8,"plum")
 d.rect(280,38,14,10,"amber");d.rect(281,39,12,7,"cream")
 d.ellipse(288,44,25,9,"glow")
 d.rect(286,65,5,9,"black");d.rect(287,67,3,5,"glass")
 d.rect(282,91,8,19,"shadow")
 for yy in (76,83,90,101):
  d.line(271,yy,301,yy-1,"stone2")
 # suspended lamp, boat, ocean foreground
 d.line(97,50,97,72,"black");d.rect(93,71,9,11,"gold");d.rect(95,73,5,7,"cream")
 d.poly([(193,109),(239,109),(231,117),(200,118)],"wood2")
 d.poly([(214,64),(215,106),(217,106)],"ink")
 d.poly([(214,70),(213,105),(183,104)],"ivory")
 d.line(182,104,214,74,"wood")
 d.line(214,77,245,106,"black")
 d.line(199,112,228,112,"gold")
 # atmospheric pixel speckle across shadows
 for _ in range(280):
  x=rnd.randrange(320);y=rnd.randrange(120)
  if x<85 and 66<y<110:d.dot(x,y,rnd.choice(("wood2","wood3","shadow")))
 add("harbor_back","background",b,d)
def workshop():
 b=Pixels(320,130);d=Pixels(320,130)
 b.rect(0,0,320,110,"plum")
 b.rect(0,8,320,92,"wall")
 for y in range(10,100,13):
  d.line(0,y,320,y,"wood")
 for x in range(0,320,30):
  d.rect(x,8,3,96,"wood2")
 b.poly([(0,101),(320,101),(320,130),(0,130)],"wood")
 for y in range(104,130,7):d.line(0,y,320,y,"ink")
 for x in range(0,320,20):d.line(x,102,x+7,129,"wood2")
 # arched window
 d.rect(122,23,65,64,"ink");d.rect(127,27,56,56,"night")
 d.ellipse(155,39,28,14,"sky2")
 d.rect(130,41,50,39,"sky")
 d.rect(153,28,3,56,"wood3");d.rect(128,51,53,3,"wood3")
 d.ellipse(173,38,8,7,"glow")
 for i in range(7):d.line(132+i*7,79,140+i*7,78,"dusk")
 # shelves
 d.rect(11,32,94,65,"shadow")
 for y in (43,61,79,95):d.rect(15,y,84,4,"wood3")
 for y in (47,65,83):
  x=18
  while x<95:
   width=rnd.randrange(3,8)
   d.rect(x,y,width,13,rnd.choice(("rust","green","navy","wood3","stone2","gold")))
   d.rect(x+1,y+2,1,5,"ivory")
   x+=width+2
 # clock gear hanging
 d.ellipse(252,47,26,27,"black");d.ellipse(252,47,21,22,"gold")
 d.ellipse(252,47,17,18,"plum");d.ellipse(252,47,13,14,"stone2")
 d.line(252,47,252,37,"black");d.line(252,47,262,52,"black")
 for angle in range(12):
  theta=math.pi*2*angle/12
  d.ellipse(int(252+22*math.cos(theta)),int(47+23*math.sin(theta)),3,3,"gold")
 # workbench
 d.rect(184,94,132,12,"wood3");d.rect(189,104,9,24,"shadow");d.rect(299,104,9,24,"shadow")
 d.rect(192,86,103,9,"wood2")
 for x in (203,230,279):d.rect(x,87,2,7,"gold")
 d.rect(208,71,17,16,"stone");d.rect(210,68,13,4,"copper")
 d.ellipse(213,81,8,5,"teal")
 d.rect(280,64,12,21,"copper");d.rect(283,66,6,15,"glass")
 # cabinet and doorway
 d.rect(60,95,46,25,"wood2");d.rect(65,98,38,18,"wood")
 d.rect(83,106,3,3,"gold")
 d.poly([(300,65),(317,65),(319,122),(297,121)],"shadow")
 d.rect(300,69,15,49,"wood2")
 d.line(301,88,315,88,"gold")
 # lamp flare
 d.rect(107,92,11,7,"copper");d.rect(110,86,5,6,"cream")
 d.ellipse(113,85,11,7,"amber")
 add("workshop_back","background",b,d)
def interface():
 b=Pixels(320,50);d=Pixels(320,50)
 b.rect(0,0,320,50,"ink");b.rect(0,0,320,3,"gold")
 for x in range(0,320,64):
  d.rect(x+2,5,60,17,"plum");d.rect(x+3,6,58,15,"night")
  d.rect(x+2,23,60,20,"wood");d.rect(x+4,25,56,16,"shadow")
 d.line(0,45,320,45,"gold")
 add("interface","ui",b,d)
def draw_character_frame(base,det,frame,elder=False):
 x=24*frame
 phase=frame%4
 motion=frame in range(2,6)
 shift=[0,-2,0,1][phase] if motion else 0
 arm=([-1,0,2,0][phase] if motion else 0)
 # shadow feet on transparent layer
 base.ellipse(x+12,45,9,2,"shadow")
 if elder:
  base.rect(x+7,29+shift,12,13,"robe")
  base.poly([(x+8,31+shift),(x+18,31+shift),(x+21,43),(x+6,43)],"robe2")
  base.rect(x+8,41+shift,4,6,"boot");base.rect(x+15,41-shift,4,6,"boot")
  base.ellipse(x+12,18+shift,9,10,"skin")
  det.ellipse(x+12,23+shift,8,8,"ivory")
  det.rect(x+5,20+shift,4,7,"grey");det.rect(x+17,20+shift,4,7,"grey")
  det.rect(x+9,14+shift,3,2,"white");det.rect(x+15,14+shift,3,2,"white")
  det.dot(x+11,16+shift,"black");det.dot(x+16,16+shift,"black")
  det.rect(x+10,25+shift,6,2,"grey")
  base.poly([(x+4,13+shift),(x+6,9+shift),(x+17,7+shift),(x+21,12+shift),(x+20,16+shift),(x+5,16+shift)],"grey")
  det.rect(x+5,9+shift,15,3,"white")
  det.rect(x+4,32+shift+arm,4,11,"robe")
  det.rect(x+19,32+shift-arm,3,10,"robe2")
  det.line(x+22,29,x+22,47,"copper")
 else:
  base.rect(x+7,26+shift,12,17,"coat")
  base.rect(x+7,40+shift,5,7,"boot");base.rect(x+15,40-shift,5,7,"boot")
  det.rect(x+10,27+shift,6,14,"coat2")
  base.ellipse(x+12,17+shift,8,11,"skin")
  det.rect(x+6,10+shift,13,5,"hair");det.rect(x+5,13+shift,3,5,"hair2")
  det.rect(x+14,10+shift,5,4,"hair2")
  det.dot(x+10,18+shift,"black");det.dot(x+16,18+shift,"black")
  det.rect(x+12,20+shift,3,2,"skinshade")
  det.rect(x+7,27+shift,11,4,"scarf");det.rect(x+15,29+shift,3,8,"rust")
  det.rect(x+4,29+shift+arm,3,11,"coat2")
  det.rect(x+19,28+shift-arm,3,12,"coat")
  det.rect(x+4,39+shift+arm,4,3,"skin")
  det.rect(x+19,39+shift-arm,4,3,"skin")
 if frame in (6,7):
  det.rect(x+11,22+shift,4,2,"black" if frame==6 else "skinshade")
 if frame == 12: det.rect(x+8,17+shift,2,2,"white")
 if frame == 9: det.rect(x+3,35,5,3,"skin")
def sprites(aid,elder):
 base=Pixels(24*14,48);detail=Pixels(24*14,48)
 for n in range(14):draw_character_frame(base,detail,n,elder)
 add(aid,"character",base,detail,{"width":24,"height":48,"count":14})
def object_asset(name):
 b=Pixels(16,16);d=Pixels(16,16)
 if name=="lens":
  b.ellipse(8,7,6,6,"copper");d.ellipse(8,7,4,4,"glass");d.line(11,12,15,15,"gold")
  d.dot(6,4,"cream");d.dot(7,5,"white")
 else:
  b.ellipse(8,8,7,7,"gold");d.ellipse(8,8,5,5,"ivory")
  d.poly([(8,3),(11,11),(7,9)],"scarf");d.poly([(8,13),(5,5),(9,7)],"navy")
  d.dot(8,8,"ink")
 add(name,"object",b,d,{"width":16,"height":16,"count":1})
def hotspot(aid,name,points,walkto,verbs,feedback):
 return {"id":aid,"name":name,"polygon":points,"walkTo":walkto,"verbs":verbs,"feedback":feedback}
def manifest(scene,name,bg,hotspots):
 selected=[assets[n] for n in (bg,"interface","young_sailor","elder_whitebeard","lens","compass")]
 d={
  "schema":1,
  "profile":{"canvas":[320,180],"presentation":[640,360],"renderScale":2,
             "aspect":"16:9","sceneHeight":130,"sampling":"nearest",
             "startMode":"manual","pixelArt":True},
  "assets":selected,
  "characters":[{"id":name,"asset":name,"pivot":[12,47],"baselineY":112,
    "animations":{"idle":[0,1],"walk":[2,3,4,5],"talk":[6,7],
      "look":[8],"pick":[9],"use":[10,11],"react":[12,13]}}
     for name in ("young_sailor","elder_whitebeard")],
  "scene":{"id":scene,"background":bg,
    "walkable":[[3,91],[317,91],[317,129],[3,129]],
    "playerStart":[45,116],"hotspots":hotspots},
  "ui":{"asset":"interface",
        "verbs":["WALK","LOOK","TAKE","USE","TALK","OPEN","GIVE"],
        "inventorySlots":6,"minTargetPx":12,"fontPx":7}
 }
 file=ROOT/("scene-"+scene+".json")
 write_new(file,(json.dumps(d,indent=2,ensure_ascii=False,sort_keys=True)+"\n").encode())
 return d
def main():
 port();workshop();interface()
 sprites("young_sailor",False);sprites("elder_whitebeard",True)
 object_asset("lens");object_asset("compass")
 harbor=[
  hotspot("lens_pickup","Lente de laton",[[98,96],[114,96],[114,112],[98,112]],[114,116],["LOOK","TAKE","USE"],"Una lente cubierta de salitre."),
  hotspot("elder","Anciano de barba blanca",[[158,66],[178,66],[178,122],[158,122]],[150,112],["LOOK","TALK","GIVE"],"El guardafaro observa el mar."),
  hotspot("tavern_door","Puerta del taller",[[53,74],[70,74],[70,116],[53,116]],[74,115],["WALK","OPEN","LOOK"],"Una puerta da al taller del puerto."),
  hotspot("lighthouse","Faro de Bruma",[[271,38],[303,38],[303,111],[271,111]],[247,112],["LOOK","USE"],"El faro lleva tiempo apagado.")
 ]
 shop=[
  hotspot("mechanism","Mecanismo de orientacion",[[233,63],[270,63],[270,104],[233,104]],[225,113],["LOOK","USE"],"Las ruedas dentadas esperan su lente."),
  hotspot("compass_pickup","Brujula de mar",[[81,93],[99,93],[99,117],[81,117]],[117,116],["LOOK","TAKE"],"Una brujula olvidada."),
  hotspot("exit_door","Regresar al puerto",[[298,72],[319,72],[319,125],[298,125]],[282,116],["WALK","OPEN"],"Se oye el mar desde fuera."),
  hotspot("bookshelf","Biblioteca del maestro",[[11,31],[105,31],[105,98],[11,98]],[106,112],["LOOK","USE"],"Manuales de cartografia y relojeria.")
 ]
 a=manifest("harbor","Puerto de la Bruma","harbor_back",harbor)
 b=manifest("workshop","Taller de los relojes","workshop_back",shop)
 world={"schema":1,"title":"LA LUZ DE BRUMA","sceneOrder":["harbor","workshop"],
  "sceneBackgrounds":{"harbor":"harbor_back","workshop":"workshop_back"},
  "scenes":{"harbor":a["scene"],"workshop":b["scene"]},
  "characters":a["characters"],
  "assets":{x["id"]:x["png"] for x in assets.values()},
  "storyGoal":"Restaurar la luz del faro con una lente y una brujula.",
  "fictionalOriginalArt":True,"humanArtApproved":False}
 write_new(ROOT/"data.js",("const WORLD = "+json.dumps(world,ensure_ascii=False,sort_keys=True)+";\n").encode("utf-8"))
 print(json.dumps({"status":"ASSET_GENERATED_CANDIDATE","assets":len(assets),
   "scenes":2,"artGrid":[320,180],"display":[640,360],
   "files":sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file())},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
