# coding: utf-8
"""R91: original 2x native 640x360 artwork, semantic ORA layers and fine details.
Retains each original individually editable layer, adds scene-specific detail layers.
Deterministic, no neural-net art substituted for implementation or external fonts.
"""
import hashlib,io,json,math,os,random,sys,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
OUT=Path(os.environ.get("R91_ART_OUT",str(ROOT)))
PIL_VENDOR=os.environ.get("R91_PIL_VENDOR",r"D:\AUTOFABRICADOR-RESCATE\R90-VISUAL-FACTORY-20261108\pyvendor")
sys.path.insert(0,PIL_VENDOR)
from PIL import Image,ImageDraw
SOURCE=Path(os.environ.get("R91_SOURCE_ROOT",str(ROOT/"art/base_r90")))
SCALE=2
NAME_ORDER=("harbor_back","harbor_front","workshop_back","workshop_front",
            "observatory_back","observatory_front","young_sailor","elder_whitebeard",
            "interface","lens","compass")
COLORS={
 "wood":"#71413d","wood2":"#a25b4c","wood3":"#d68c65","brass":"#e6b76b",
 "navy":"#20253b","shadow":"#272a42","paper":"#f9ddb0",
 "foam":"#82a6ae","sea":"#306c79","cream":"#ffe8bd",
 "stone":"#acb8bb","dark":"#17263c","sky":"#4c6581",
 "ruby":"#a44f59","teal":"#5bb6b0","silver":"#dce5d8"
}
def digest(data):return hashlib.sha256(data).hexdigest()
def write_new(p,blob):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb") as f:f.write(blob);f.flush();os.fsync(f.fileno())
 if digest(p.read_bytes())!=digest(blob):raise RuntimeError("R91_ART_SHA_READBACK_FAILED:"+str(p))
def encoded(im):
 tmp=io.BytesIO();im.save(tmp,format="PNG",optimize=False,compress_level=9)
 return tmp.getvalue()
def rgba(size):return Image.new("RGBA",size,(0,0,0,0))
def rdraw(img):return ImageDraw.Draw(img)
def rect(img,p,c,width=1):
 rdraw(img).rectangle(p,fill=c,width=width)
def line(img,pts,color,width=1):
 rdraw(img).line(pts,fill=color,width=width)
def dot(img,x,y,col):
 rdraw(img).point((x,y),fill=col)
def parse_layers(ora):
 with zipfile.ZipFile(ora) as z:
  root=ET.fromstring(z.read("stack.xml"))
  entries=[]
  for a in root.iter("layer"):
   data=z.read(a.attrib["src"])
   im=Image.open(io.BytesIO(data)).convert("RGBA")
   entries.append((a.attrib["name"],im))
  entries.reverse() # R90 ZIP stack is front-to-back, paint bottom-to-top.
 return entries
def hdetail(name,size):
 fine=rgba(size); light=rgba(size)
 rnd=random.Random(int(digest(name.encode())[:8],16)+91731)
 W,H=size
 if name=="harbor_back":
  # Continuous plank path from tavern across the pier to the lighthouse.
  rdraw(fine).polygon([(244,226),(316,212),(420,215),(534,209),(639,213),(639,259),(250,259)],fill=COLORS["wood"],outline=COLORS["navy"])
  rdraw(fine).polygon([(249,223),(317,216),(421,218),(535,212),(639,216),(639,231),(250,236)],fill=COLORS["wood2"])
  for y in (226,239,252):
   line(fine,[(250,y),(639,y-2)],COLORS["shadow"],2)
  for x in range(252,640,23):
   line(fine,[(x,221),(x+11,259)],COLORS["wood3"])
   for y in (225,246):
    dot(light,x+4,y,COLORS["brass"])
  for x in (273,370,526,617):
   rect(fine,(x,202,x+6,258),COLORS["shadow"])
   rect(fine,(x+2,203,x+4,251),COLORS["wood3"])
   rect(light,(x-4,207,x+10,211),COLORS["brass"])
  for _ in range(130):
   x=rnd.randrange(0,W);y=rnd.randrange(172,225)
   if x>250 and y>208:continue
   line(light,[(x,y),(min(W-1,x+rnd.randrange(2,9)),y)],rnd.choice([COLORS["foam"],COLORS["sea"]]))
  # Granular masonry on lighthouse, sign and boarding.
  for x in range(545,603,9):
   for y in range(124,208,7):
    if rnd.randrange(4)==0:line(light,[(x,y),(x+4,y)],COLORS["stone"])
 elif name=="workshop_back":
  for y in range(18,198,10):
   for x in range(4,635,30):
    if rnd.random()<0.6:
     line(fine,[(x,y),(x+rnd.randrange(4,20),y)],COLORS["wood3"])
  for cx,cy in [(496,144),(542,168),(457,177)]:
   for k in range(24):
    angle=k*math.tau/24
    xx=cx+round(35*math.cos(angle)); yy=cy+round(33*math.sin(angle))
    dot(light,xx,yy,COLORS["brass"])
  # Spilled warm light across floor, broken into small pixellated glints.
  for _ in range(215):
   x=rnd.randrange(180,540);y=rnd.randrange(201,259)
   line(light,[(x,y),(x+rnd.randrange(1,6),y)],rnd.choice([COLORS["brass"],COLORS["wood3"]]))
 elif name=="observatory_back":
  for _ in range(135):
   x=rnd.randrange(76,572);y=rnd.randrange(48,177)
   col=rnd.choice([COLORS["cream"],COLORS["silver"],COLORS["sky"]])
   dot(light,x,y,col)
  # Chart on table: etched contour lines, diagram labels in small pixels.
  for x in range(468,534,8):
   line(fine,[(x,185),(x+rnd.randrange(2,8),195)],COLORS["wood"])
  for cy in range(215,255,9):
   for x in range(15,625,24):
    if rnd.random()<0.4:
     line(light,[(x,cy),(x+5,cy)],COLORS["wood3"])
 elif name.endswith("_front"):
  for _ in range(24):
   x=rnd.randrange(0,W);y=rnd.randrange(max(0,H-51),H)
   dot(light,x,y,COLORS["wood3"])
 elif name=="interface":
  for x in range(8,W,9):
   dot(light,x,H-3,COLORS["brass"])
  for x in (128,256,384,512):
   line(fine,[(x,5),(x,H-7)],COLORS["wood3"])
 elif name in ("lens","compass"):
  for x,y in ((8,5),(12,3),(17,5),(13,12)):
   dot(light,x,y,COLORS["cream"])
 return fine,light
def character_details(name,size):
 fine=rgba(size);highlight=rgba(size)
 elder=name=="elder_whitebeard"
 for frame in range(14):
  x=frame*48
  bob=(-2 if frame in (3,5) else 0)
  # Original sprites occupy 48x96 source pixels. Add single-pixel detailed shading.
  if elder:
   for yy in range(40,76,4):
    line(fine,[(x+18,yy+bob),(x+19,yy+bob+3)],COLORS["silver"])
    dot(highlight,x+31,yy+bob+1,COLORS["stone"])
   for px,py in [(17,28),(21,29),(32,29),(35,30)]:
    dot(highlight,x+px,py+bob,COLORS["cream"])
   line(fine,[(x+23,53),(x+29,55)],COLORS["shadow"])
   line(fine,[(x+15,70),(x+16,77)],COLORS["stone"])
   line(highlight,[(x+29,70),(x+32,74)],COLORS["silver"])
  else:
   # Facial eyes with iris, cheek and contour; coat embroidered thread.
   for px,py,col in [(20,17,COLORS["navy"]),(22,17,COLORS["cream"]),
                     (33,17,COLORS["navy"]),(35,17,COLORS["cream"]),
                     (29,22,COLORS["ruby"]),(25,28,COLORS["brass"])]:
    dot(highlight,x+px,py+bob,col)
   for yy in range(58,78,5):
    dot(fine,x+35,yy+bob,COLORS["brass"])
   line(fine,[(x+15,67),(x+22,69)],COLORS["ruby"])
   line(highlight,[(x+8,57),(x+10,61)],COLORS["teal"])
   line(highlight,[(x+37,56),(x+37,61)],COLORS["teal"])
  if frame in (6,7):
   line(fine,[(x+25,35+bob),(x+31,35+bob)],COLORS["ruby"])
  if frame in (10,11):
   for j in range(3):dot(highlight,x+42+j,53-2*j,COLORS["cream"])
 return fine,highlight
def generate(name):
 layers=parse_layers(SOURCE/"source"/(name+".ora"))
 expected_base=Image.open(SOURCE/"assets"/(name+".png")).convert("RGBA")
 old=rgba(expected_base.size)
 for label,im in layers:
  old=Image.alpha_composite(old,im)
 if old.tobytes()!=expected_base.tobytes():
  raise RuntimeError("R91_R90_ORA_PREIMAGE_DIFFERS_FROM_PNG:"+name)
 expanded=[(label,im.resize((im.width*2,im.height*2),resample=Image.Resampling.NEAREST))
           for label,im in layers]
 size=(expected_base.width*2,expected_base.height*2)
 if name in ("young_sailor","elder_whitebeard"):
  a,b=character_details(name,size)
 else:a,b=hdetail(name,size)
 expanded += [("R91 fine-pixel surface details",a),("R91 highlights and material definition",b)]
 final=rgba(size)
 for _,img in expanded:final=Image.alpha_composite(final,img)
 png=encoded(final)
 output=io.BytesIO()
 with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  def put(path,b,compress=zipfile.ZIP_DEFLATED):
   info=zipfile.ZipInfo(path,date_time=(2026,11,8,12,0,0))
   info.compress_type=compress
   info.external_attr=0o644<<16
   z.writestr(info,b)
  put("mimetype",b"image/openraster",zipfile.ZIP_STORED)
  import xml.sax.saxutils as xs
  xml_layers="".join(
   f'<layer name="{xs.escape(title)}" src="data/{i:02d}.png" x="0" y="0"/>'
   for i,(title,_) in reversed(list(enumerate(expanded))))
  xml=(f'<?xml version="1.0" encoding="UTF-8"?><image w="{size[0]}" h="{size[1]}" name="{name}"><stack>'+xml_layers+"</stack></image>").encode()
  put("stack.xml",xml)
  for index,(label,layer) in enumerate(expanded):
   put(f"data/{index:02d}.png",encoded(layer))
  put("mergedimage.png",png)
 master=output.getvalue()
 write_new(OUT/"assets"/(name+".png"),png)
 write_new(OUT/"source"/(name+".ora"),master)
 return {"id":name,"png":"assets/"+name+".png","pngSHA256":digest(png),
  "master":"source/"+name+".ora","masterSHA256":digest(master),
  "pixels":[size[0],size[1]],"layers":[label for label,_ in expanded]}
def main():
 if not (SOURCE/"source/young_sailor.ora").is_file():
  raise RuntimeError("R91_ORIGINAL_R90_SOURCE_NOT_AVAILABLE")
 if (OUT/"R91-HD-ART-MANIFEST.json").exists():
  raise RuntimeError("R91_ART_MANIFEST_ALREADY_EXISTS")
 assets=[generate(name) for name in NAME_ORDER]
 manifest={"schema":1,"operationId":"AF.R91.HD-PIXEL-LAYERED-20261108",
  "status":"PASS_HD_11_ASSETS_11_EDITABLE_ORA",
  "nativeRender":[640,360],"scenePixels":[640,260],"uiPixels":[640,100],
  "framePixels":[48,96],"frameCount":14,
  "physicalPresentation":[1280,720],"assetCount":len(assets),
  "independentHumanArtApproval":False,"modelGeneratedArt":False,
  "assets":assets}
 write_new(OUT/"R91-HD-ART-MANIFEST.json",(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode())
 print(json.dumps({"status":manifest["status"],"files":22,"assets":len(assets),
 "sourceSha":digest(Path(__file__).read_bytes()),"layersMin":min(len(x["layers"]) for x in assets)},indent=2))
if __name__=="__main__":main()
