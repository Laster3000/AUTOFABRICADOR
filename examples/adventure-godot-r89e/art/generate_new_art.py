# coding: utf-8
"""R89 additive pixel-art layers (self-contained, no model code executed).
Adds foreground depth for two original scenes and a new observatory background.
Each new asset is a PNG plus two independently editable OpenRaster paint layers.
"""
import importlib.util,json,hashlib,math,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
BASE=Path(__file__).resolve().parent/"generate_assets.py"
D=ROOT/"evidence"
D.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location("af_r88_pixel_master",BASE)
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
M.ROOT=ROOT
M.ASSET=ROOT/"assets"
M.SOURCE=ROOT/"source"
M.rnd=random.Random(8916)
P=M.Pixels
rng=random.Random(19891992)
def add(name,kind,base,detail):
 record=M.save(name,kind,base,detail)
 return record
def rnddot(p,x,y,w,h,count,c):
 for _ in range(count):p.dot(rng.randrange(x,x+w),rng.randrange(y,y+h),c)
def port_front():
 b=P(320,130); d=P(320,130)
 # weathered dock tie posts and rigging foreground. Independent occlusion asset.
 for x in [1,92,292,317]:
  d.rect(x,91,4,39,"ink");d.rect(x+1,91,2,36,"wood3")
  d.rect(x-2,96,8,2,"gold")
 d.line(1,95,93,111,"plum");d.line(92,110,294,96,"wood")
 for x in range(0,320,24):
  d.rect(x,124,21,5,"wood2");d.rect(x+2,125,18,1,"wood3")
  d.dot(x+2,126,"gold")
 # lantern in the foreground as separate glow/overlay
 d.line(145,0,144,51,"shadow");d.rect(139,50,12,15,"black")
 d.poly([(140,51),(145,47),(150,51)],"copper")
 d.rect(141,53,8,10,"gold");d.rect(143,55,4,7,"cream")
 d.dot(144,56,"white")
 for x,y in [(8,22),(11,29),(15,18),(32,42),(218,12),(279,15)]:
  d.dot(x,y,"pale")
 return add("harbor_front","foreground",b,d)
def workshop_front():
 b=P(320,130);d=P(320,130)
 # Workbench, hanging brass gears, foreground wood planks
 for x in [4,15,302,313]:
  d.rect(x,0,5,120,"wood2")
  d.rect(x+2,0,1,120,"cedar")
 for x in range(30,301,42):
  d.line(x,0,x+10,24,"shadow")
  d.ellipse(x+10,28,5,6,"gold")
  d.ellipse(x+10,28,3,4,"ink")
 d.rect(0,121,320,8,"ink")
 for x in range(0,320,18):
  d.rect(x,122,17,5,"wood3");d.rect(x+1,123,15,1,"wood2")
 d.rect(0,103,12,18,"wood")
 d.rect(3,107,8,10,"copper")
 d.ellipse(308,110,9,10,"wood")
 d.ellipse(308,109,6,6,"stone2")
 d.rect(307,109,2,2,"black")
 return add("workshop_front","foreground",b,d)
def observatory():
 base=P(320,130); d=P(320,130)
 sky=["night","night","night","sky","sky2","violet","rose","dusk","plum","ink"]
 for y in range(130):
  if y<93:base.rect(0,y,320,1,sky[min(9,int(y/10))])
  else:base.rect(0,y,320,1,"wood")
 # sky beyond the domed window
 d.ellipse(159,59,133,69,"black")
 d.ellipse(159,59,128,66,"sky2")
 for y in range(13,105):
  frac=y/105
  c="sky" if frac<.3 else ("violet" if frac<.65 else "dusk")
  d.rect(32,y,254,1,c)
 # starfield
 for _ in range(94):
  x=rng.randrange(40,281);y=rng.randrange(12,86)
  if ((x-159)/124)**2+((y-59)/64)**2<.9:
   d.dot(x,y,rng.choice(("ivory","cream","pale","gold")))
 for star in [(69,20),(97,52),(144,24),(200,31),(246,60),(237,15)]:
  x,y=star
  d.line(x-2,y,x+2,y,"cream");d.line(x,y-2,x,y+2,"cream");d.dot(x,y,"white")
 # Mountains and distant coast below horizon.
 d.poly([(30,87),(65,65),(89,77),(119,55),(151,84),(180,69),(221,81),(254,63),(288,88),(288,101),(30,101)],"navy")
 d.poly([(43,94),(100,78),(129,91),(180,74),(220,92),(270,82),(288,100),(35,101)],"sea2")
 # Vigorous structural arch in warm bronze.
 d.ellipse(159,65,142,75,"wood")
 d.ellipse(159,63,137,70,"ink")
 d.ellipse(159,61,132,66,"wood2")
 d.ellipse(159,59,126,62,"sky")
 # Reapply distant sky in arch as layered fill
 for y in range(17,98):
  maxx=int(125*math.sqrt(max(0,1-((y-61)/62)**2)))
  col="sky" if y<45 else "sky2" if y<70 else "violet"
  d.rect(159-maxx,y,2*maxx+1,1,col)
 for _ in range(55):
  x=rng.randrange(40,279);y=rng.randrange(17,85)
  if ((x-159)/125)**2+((y-61)/62)**2<.96:d.dot(x,y,rng.choice(("cream","ivory","pale")))
 # six constellations in the dome
 for x0,y0 in [(65,25),(110,41),(164,18),(214,33),(249,57)]:
  d.line(x0,y0,x0+11,y0+4,"pale")
  d.line(x0+11,y0+4,x0+17,y0-3,"gold")
  for xx,yy in [(x0,y0),(x0+11,y0+4),(x0+17,y0-3)]:
   d.ellipse(xx,yy,1,1,"cream")
 # Vertical architectural pillars
 for x in (23,296):
  d.rect(x,22,10,97,"shadow")
  d.rect(x+2,22,4,97,"wood3")
  for y in range(35,110,18):d.rect(x-2,y,14,3,"gold")
 # Astronomical disc on back wall, gears
 d.ellipse(93,82,28,26,"shadow");d.ellipse(93,82,23,22,"gold")
 d.ellipse(93,82,19,18,"plum");d.ellipse(93,82,14,13,"stone2")
 for a in range(12):
  angle=a*math.tau/12
  xx=int(93+23*math.cos(angle));yy=int(82+22*math.sin(angle))
  d.rect(xx,yy,2,2,"ivory")
 d.line(93,82,107,71,"ink")
 d.line(93,82,85,93,"wood2")
 # Giant hand-crafted telescope on articulated wooden tripod
 d.poly([(162,77),(190,65),(204,69),(178,85)],"black")
 d.poly([(160,77),(188,66),(202,68),(178,82)],"copper")
 d.line(169,79,195,70,"gold")
 d.ellipse(199,68,6,4,"ivory")
 d.rect(174,80,6,8,"stone")
 d.line(176,87,158,121,"gold")
 d.line(176,87,192,123,"gold")
 d.line(176,87,176,123,"copper")
 d.ellipse(176,87,6,5,"wood3")
 # Table with chart, candle, quill and brass measuring instruments
 d.poly([(208,100),(289,99),(299,105),(203,106)],"wood3")
 d.poly([(203,106),(299,106),(294,114),(210,114)],"wood2")
 for x in (216,284):d.rect(x,112,7,17,"wood")
 d.poly([(229,94),(269,93),(277,99),(222,100)],"ivory")
 for x in (234,242,249,261):
  d.line(x,95,x+3,98,"ink")
 d.ellipse(246,96,2,2,"rose")
 d.rect(282,91,2,8,"ivory");d.rect(280,90,6,2,"gold")
 d.ellipse(283,87,3,4,"amber");d.dot(283,85,"cream")
 # Floor and stepped shadow perspective
 d.poly([(0,97),(320,97),(320,130),(0,130)],"wood")
 for y in [101,108,117,125]:d.line(0,y,320,y+1,"wood2")
 for x in range(-50,380,31):d.line(x,100,x+21,129,"shadow")
 # Fine decorative screws, scratches, rivets, tesselation
 for x in range(7,319,11):
  d.dot(x,113,"wood3");d.dot(x+2,115,"gold")
 for i in range(100):
  x=rng.randrange(40,300);y=rng.randrange(101,130)
  d.dot(x,y,rng.choice(("wood2","wood3","shadow")))
 return add("observatory_back","background",base,d)
def observatory_front():
 b=P(320,130);d=P(320,130)
 # Small railings and hanging wires in front of player, real depth occlusion.
 for x in [6,55,272,313]:
  d.rect(x,107,4,23,"black");d.rect(x+1,106,2,22,"wood3")
 for x in range(0,56,6):
  d.line(x,107,x+7,113,"copper")
 for x in range(274,320,6):
  d.line(x,111,x+6,107,"wood2")
 d.rect(0,121,55,3,"copper");d.rect(273,121,47,3,"copper")
 d.line(8,0,7,34,"black");d.rect(4,34,8,11,"gold")
 d.rect(6,36,4,7,"cream")
 return add("observatory_front","foreground",b,d)
def main():
 target=D/"R89-NEW-ART-ASSETS.json"
 if target.exists():raise RuntimeError("R89_NEW_ART_ALREADY_CREATED_NO_REPLAY")
 r=[port_front(),workshop_front(),observatory(),observatory_front()]
 receipt={"schema":1,"status":"PASS_FOUR_LAYERED_ORIGINAL_ART_ASSETS_CREATED",
   "artFormat":"PNG_RGBA_PLUS_EDITABLE_2_LAYER_OPENRASTER",
   "sceneGrid":[320,130],"assets":r,
   "legacySourceUnmodified":True,"humanVisualApproved":False}
 target.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(json.dumps({"status":receipt["status"],"assets":[x["id"] for x in r]},indent=2))
if __name__=="__main__":main()
