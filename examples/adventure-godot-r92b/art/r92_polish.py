# coding: utf-8
"""AF R92 authored scenic/character polisher. Fully editable deterministic ORA masters.
Use R91 as immutable input; remove R91 random-long-line overlays. Never alter R91.
"""
from __future__ import annotations
import io,os,hashlib,json,math,random,sys,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"art"/"base_r91"
OUT=Path(os.environ.get("AF_R92_ART_OUT",str(ROOT)))
sys.path.insert(0,os.environ.get("AF_R92_PIL",r"D:\AUTOFABRICADOR-RESCATE\R90-VISUAL-FACTORY-20261108\pyvendor"))
from PIL import Image,ImageDraw
IDENTIFIERS=("harbor_back","harbor_front","workshop_back","workshop_front",
 "observatory_back","observatory_front","young_sailor","elder_whitebeard","interface","lens","compass")
COL={"dark":"#192238","dark2":"#11172a","navy":"#29354b","ink":"#1d2539",
"coat":"#286e79","lightcoat":"#4da7a4","shadowcoat":"#214855",
"vest":"#ba664f","skin":"#e8ac87","skinshade":"#ba7567",
"skinlight":"#ffd2a5","hair":"#453044","hairlight":"#7d4b51","paper":"#f5e0bd",
"boots":"#372f3d","gold":"#e9b775","goldshadow":"#a47050",
"beard":"#e9eee1","beardshadow":"#aabac2","beardbright":"#fff7dc",
"eldercoat":"#566a80","elderlight":"#8395a3","wine":"#743d54",
"sea":"#305b6e","wood":"#70414a","woodlight":"#a16558",
"stone":"#777f8d","stoneshine":"#a8a7a1","sky":"#232d4d",
"ui":"#25263a","uipanel":"#332e42","uiedge":"#d8a76f"}
def sha(b):return hashlib.sha256(b).hexdigest()
def png(im):
 t=io.BytesIO();im.save(t,format="PNG",compress_level=9,optimize=False)
 return t.getvalue()
def new(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())
 if sha(p.read_bytes())!=sha(data):raise RuntimeError("R92_ART_POST_SHA_FAILED")
def layer(size):return Image.new("RGBA",size,(0,0,0,0))
def paint(im):return ImageDraw.Draw(im)
def rr(im,coords,colour):paint(im).rectangle(coords,fill=COL.get(colour,colour))
def pp(im,pts,colour):paint(im).polygon(pts,fill=COL.get(colour,colour))
def ln(im,pts,colour,w=1):paint(im).line(pts,fill=COL.get(colour,colour),width=w)
def ee(im,coords,colour):paint(im).ellipse(coords,fill=COL.get(colour,colour))
def read_ora(name):
 path=SOURCE/"source"/(name+".ora")
 with zipfile.ZipFile(path) as z:
  root=ET.fromstring(z.read("stack.xml"))
  images=[]
  for tag in root.iter("layer"):
   label=tag.get("name")
   if label.startswith("R91 "):continue  # remove random outlines/streaks
   i=Image.open(io.BytesIO(z.read(tag.get("src")))).convert("RGBA")
   images.append((label,i))
 return list(reversed(images))
def expand_layers(layers,new_size):
 old_w,old_h=layers[0][1].size
 if new_size==(old_w,old_h):return layers
 grown=[]
 for name,im in layers:
  target=layer(new_size);target.paste(im,(0,0))
  grown.append((name,target))
 return grown
def floor_extension(name,canvas,highlight):
 w,h=canvas.size
 if name.endswith("_back"):
  cols={"harbor_back":("#493b4c","#725164"),
   "workshop_back":("#443646","#65465b"),
   "observatory_back":("#382d45","#584058")}
  a,b=cols[name]
  for y in range(260,h):
   colour=a if ((y-260)//8)%2==0 else b
   ln(canvas,[(0,y),(w-1,y)],colour)
  rng=random.Random(92+len(name))
  # Manually controlled SHORT floor-panel joints, not diagonal full-screen lines.
  for y in range(264,h,8):
   for x in range((y%3)*11,w,38):
    ln(highlight,[(x,y),(x+5,y)],"#a07570",1)
    if rng.randrange(3)==0:
     rr(highlight,(x+9,y+3,x+10,y+4),"#ba8870")
  # Darken the floor edge to give characters a grounded foreground.
  ln(highlight,[(0,288),(639,288)],"#392838",2)
def scenic(name,base):
 size=(640,290) if name.endswith(("_back","_front")) else (640,70) if name=="interface" else (32,32)
 if name=="interface":
  a=layer(size);b=layer(size);c=layer(size)
  rr(a,(0,0,639,69),"ui")
  rr(a,(0,0,639,3),"uiedge")
  rr(a,(0,5,639,31),"uipanel")
  rr(a,(0,34,639,69),"dark2")
  for i in range(5):
   x=i*128
   rr(b,(x+4,8,x+123,29),"navy")
   rr(c,(x+7,9,x+120,10),"goldshadow")
   rr(c,(x+4,31,x+123,32),"uiedge")
  for i in range(6):
   x=i*100
   rr(b,(x+3,38,min(639,x+96),64),"uipanel")
   ln(c,[(x+5,39),(min(639,x+94),39)],"goldshadow")
  return [("Compact full-width backdrop",a),("Verb and inventory surfaces",b),
    ("Tiny inset brass borders",c),("Transparent effects",layer(size)),
    ("Transparent accent layer",layer(size)),("Transparency edit mask",layer(size))]
 if name in ("lens","compass"):
  layers=expand_layers(base,size)
  return layers+[("Fine artifact contour",layer(size)),("Jewelled glints",layer(size))]
 layers=expand_layers(base,size)
 lights=layer(size);materials=layer(size)
 if name.endswith("_back"):
  floor_extension(name,materials,lights)
  if name=="harbor_back":
   # Remove the geometrical R91 plank lattice; add discretely spaced dock posts.
   for x in (265,356,468,580):
    rr(materials,(x,232,x+5,260),"dark2")
    rr(lights,(x+1,235,x+2,258),"woodlight")
   for x,y in ((455,202),(479,209),(522,208),(576,205)):
    rr(lights,(x,y,x+3,y+2),"gold")
  elif name=="workshop_back":
   # Bookshelf flares and separate dimensional tool grips.
   for x in (48,66,87,111,134,164,188):
    rr(lights,(x,87,x+2,94),"goldshadow")
   for x,y in ((460,164),(506,145),(543,165)):
    ee(lights,(x-2,y-2,x+3,y+3),"gold")
  elif name=="observatory_back":
   # Restrict stars to window zone; no stripes spanning the architecture.
   rr(lights,(310,81,313,84),"paper")
   rr(lights,(375,117,378,119),"paper")
   for x in (479,494,513):
    rr(lights,(x,186,x+3,188),"gold")
 elif name.endswith("_front"):
  if name=="harbor_front":
   for x in (18,127,239,578):
    rr(lights,(x,252,x+6,254),"goldshadow")
 return layers+[("Controlled material accents",materials),("Localised tiny highlights",lights)]
def sprite(name):
 """New 48x96 sprite drawn at full sheet resolution, rather than scaling R90 24x48.
 Every frame is independently composed; boot shadows and face details remain editable.
 """
 elder=name=="elder_whitebeard";size=(14*48,96)
 silhouette,coat,face,details,expression,glints=[layer(size) for _ in range(6)]
 for frame in range(14):
  x=frame*48
  walking=2<=frame<=5
  talking=frame in (6,7)
  acting=frame in (8,9,10,11,12,13)
  phase=(frame-2)%4 if walking else 0
  bob=-2 if walking and phase in (1,3) else 0
  lean=2 if frame==9 else (-1 if frame in (12,13) else 0)
  # World floor is at sprite y95.
  ee(silhouette,(x+7,91,x+40,95),"#16223670")
  if walking and phase in (1,3):
   pp(silhouette,[(x+13,73),(x+23,76),(x+16,92),(x+8,92)],"boots")
   pp(silhouette,[(x+26,74),(x+35,76),(x+41,92),(x+31,92)],"boots")
  else:
   pp(silhouette,[(x+14,71),(x+23,71),(x+21,93),(x+11,93)],"boots")
   pp(silhouette,[(x+27,71),(x+36,70),(x+39,93),(x+28,93)],"boots")
  rr(details,(x+10,91,x+21,94),"dark2")
  rr(details,(x+29,91,x+41,94),"dark2")
  pp(silhouette,[(x+10,39+bob),(x+38,38+bob),(x+44,80),(x+6,81)],"dark2")
  pp(coat,[(x+11,40+bob),(x+35,39+bob),(x+41,75),(x+6,79)],"eldercoat" if elder else "coat")
  pp(coat,[(x+23,42+bob),(x+35,41+bob),(x+38,74),(x+24,76)],"elderlight" if elder else "lightcoat")
  pp(coat,[(x+11,43+bob),(x+17,44+bob),(x+12,76),(x+7,76)],"eldercoat" if elder else "shadowcoat")
  # distinctive shaped collar, vest, belts, shiny clasps
  pp(details,[(x+17,40+bob),(x+24,45+bob),(x+30,40+bob),(x+29,49+bob),(x+22,55+bob)],"paper")
  pp(details,[(x+19,48+bob),(x+32,48+bob),(x+31,62),(x+19,62)],"wine" if elder else "vest")
  ln(details,[(x+11,65),(x+38,65)],"goldshadow",3)
  rr(glints,(x+24,64,x+28,67),"gold")
  # asymmetrical arms react to frame mode.
  arm=-10 if frame in (10,11) else (-5 if frame==8 else (3 if walking and phase%2 else 0))
  pp(coat,[(x+9,44+bob),(x+13,43+bob),(x+11+arm//4,69+arm),(x+6+arm//4,72+arm)],"elderlight" if elder else "coat")
  pp(coat,[(x+36,43+bob),(x+40,45+bob),(x+44,69-arm),(x+39,73-arm)],"eldercoat" if elder else "shadowcoat")
  rr(face,(x+7+arm//4,71+arm,x+11+arm//4,76+arm),"skin")
  rr(face,(x+40,72-arm,x+44,77-arm),"skin")
  # face is painted with nose/eye/cheek/chin at physical pixel resolution.
  pp(face,[(x+14,17+bob+lean),(x+21,13+bob+lean),(x+32,16+bob+lean),
          (x+38,23+bob+lean),(x+36,38+bob+lean),(x+30,44+bob+lean),
          (x+17,41+bob+lean),(x+11,34+bob+lean)],"skin")
  pp(face,[(x+11,28+bob+lean),(x+16,30+bob+lean),(x+16,36+bob+lean),
           (x+13,36+bob+lean)],"skinshade")
  rr(glints,(x+19,18+bob+lean,x+31,19+bob+lean),"skinlight")
  pp(face,[(x+35,29+bob+lean),(x+41,34+bob+lean),(x+35,36+bob+lean)],"skin")
  # exact eye geometry; pupils separate from brows and facial highlights
  for px in (19,32):
   rr(details,(x+px-3,24+bob+lean,x+px+3,25+bob+lean),"hair" if not elder else "beardshadow")
   rr(details,(x+px-2,28+bob+lean,x+px+2,30+bob+lean),"paper")
   rr(expression,(x+px,28+bob+lean,x+px+1,30+bob+lean),"dark2")
   rr(glints,(x+px,28+bob+lean,x+px,28+bob+lean),"paper")
  if elder:
   # exaggerated distinct white mustache, long beard and eyebrows.
   pp(details,[(x+10,28+bob),(x+15,16+bob),(x+23,11+bob),
               (x+34,16+bob),(x+39,28+bob),(x+36,25+bob),
               (x+30,19+bob),(x+16,25+bob)],"beardshadow")
   pp(details,[(x+12,32+bob),(x+21,36+bob),(x+28,35+bob),
               (x+39,32+bob),(x+38,54+bob),(x+31,63+bob),
               (x+21,61+bob),(x+12,54+bob)],"beardshadow")
   pp(details,[(x+14,34+bob),(x+23,39+bob),(x+27,39+bob),
               (x+36,34+bob),(x+34,53+bob),(x+26,60+bob),
               (x+17,54+bob)],"beard")
   ln(glints,[(x+19,43+bob),(x+19,53+bob)],"beardbright",2)
   ln(glints,[(x+29,42+bob),(x+28,56+bob)],"beardbright",2)
   pp(glints,[(x+14,30+bob),(x+22,30+bob),(x+19,34+bob)],"beardbright")
   pp(glints,[(x+26,30+bob),(x+36,30+bob),(x+31,34+bob)],"beardbright")
   # old captain's simple cane
   ln(details,[(x+43,65),(x+43,91)],"goldshadow",2)
   rr(details,(x+41,64,x+45,66),"gold")
  else:
   pp(details,[(x+11,25+bob),(x+12,16+bob),(x+18,9+bob),(x+31,9+bob),
      (x+39,16+bob),(x+39,24+bob),(x+32,17+bob),(x+26,20+bob),
      (x+22,16+bob),(x+14,24+bob)],"hair")
   pp(glints,[(x+16,14+bob),(x+22,10+bob),(x+30,10+bob),(x+24,14+bob)],"hairlight")
   rr(details,(x+22,38+bob,x+31,39+bob),"skinshade")
   ln(details,[(x+17,52+bob),(x+29,54+bob)],"gold")
   # red sash across torso gives distinctive recognizable silhouette.
   pp(expression,[(x+10,51+bob),(x+17,48+bob),(x+35,60+bob),(x+32,65+bob)],"vest")
  if talking:
   rr(expression,(x+24,36+bob+lean,x+29,39+bob+lean),"wine")
   rr(glints,(x+24,36+bob+lean,x+29,36+bob+lean),"paper")
  if frame==8:
   ln(expression,[(x+39,51),(x+45,31)],"skin",4)
  if frame==9:
   pp(expression,[(x+41,70),(x+46,74),(x+41,83)],"skin")
  if frame in (12,13):
   rr(expression,(x+25,35+bob,x+30,40+bob),"dark2")
  # coat seam/stitch details at unique pixel scale (not copied 2x blocks).
  for y in range(71,83,4):
   rr(glints,(x+14,y,x+16,y+1),"goldshadow")
  for y in range(50,64,5):
   rr(glints,(x+35,y,x+36,y),"gold")
 return [("Silhouette feet & shadow",silhouette),("Asymmetric coat",coat),
  ("Face, hands and nose",face),("Hair / beard and fabric stitching",details),
  ("Independent expressions and reactions",expression),("Specular accents",glints)]
def generate(name):
 original=read_ora(name)
 if name in ("young_sailor","elder_whitebeard"):layers=sprite(name)
 else:layers=scenic(name,original)
 sizes={img.size for _,img in layers}
 if len(sizes)!=1:raise RuntimeError("R92_LAYER_SIZE_INCONSISTENT")
 w,h=layers[0][1].size
 merged=layer((w,h))
 for _,img in layers:
  merged=Image.alpha_composite(merged,img)
 raw=png(merged)
 output=io.BytesIO()
 with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  def entry(path,data,compress=zipfile.ZIP_DEFLATED):
   item=zipfile.ZipInfo(path,date_time=(2026,11,8,12,0,0));item.compress_type=compress
   item.external_attr=0o644<<16
   z.writestr(item,data)
  entry("mimetype",b"image/openraster",zipfile.ZIP_STORED)
  import xml.sax.saxutils as xs
  nodes="".join(f'<layer name="{xs.escape(label)}" src="data/{i:02d}.png" x="0" y="0"/>'
   for i,(label,_) in reversed(list(enumerate(layers))))
  entry("stack.xml",(f'<?xml version="1.0" encoding="UTF-8"?><image w="{w}" h="{h}" name="{name}"><stack>{nodes}</stack></image>').encode())
  for i,(_,img) in enumerate(layers):entry(f"data/{i:02d}.png",png(img))
  entry("mergedimage.png",raw)
 master=output.getvalue()
 new(OUT/"assets"/(name+".png"),raw)
 new(OUT/"source"/(name+".ora"),master)
 return {"id":name,"png":"assets/"+name+".png","pngSHA256":sha(raw),
  "master":"source/"+name+".ora","masterSHA256":sha(master),
  "size":[w,h],"layers":[label for label,_ in layers]}
def main():
 if (OUT/"R92-ART-MANIFEST.json").exists():raise RuntimeError("R92_ART_OUTPUT_ALREADY_EXISTS_NO_REPLAY")
 if not (SOURCE/"source/harbor_back.ora").is_file():raise RuntimeError("R92_IMMUTABLE_R91_MASTERS_MISSING")
 rows=[generate(i) for i in IDENTIFIERS]
 receipt={"schema":1,"operationId":"AF.R92.CLEAN-ART-AND-ACTOR-20261108",
  "status":"PASS_ELEVEN_ORIGINAL_REEDITABLE_ART_MASTERS",
  "scene":[640,290],"ui":[640,70],"frame":[48,96],"count":14,
  "sourceArtRoot":"art/base_r91","originalR91Retained":True,
  "approvalHuman":False,"assets":rows}
 new(OUT/"R92-ART-MANIFEST.json",(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode())
 print(json.dumps({"status":receipt["status"],"assets":len(rows),
   "generatorSha256":sha(Path(__file__).read_bytes()),"layersMin":min(len(r["layers"]) for r in rows)},indent=2))
if __name__=="__main__":main()
