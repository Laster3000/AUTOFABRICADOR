# coding: utf-8
"""R90 original manually designed high-detail 16:9 pixel art; repeatable, no network/model.
All assets are new, with editable semantic OpenRaster layers, fixed ZIP metadata.
Pure Python + Pillow 12.0 in isolated rescue directory; does NOT touch R89E.
"""
from __future__ import annotations
import hashlib,io,json,math,random,sys,zipfile,os
from pathlib import Path
PIL=Path(os.environ.get("R90_PIL_VENDOR",r"D:\AUTOFABRICADOR-RESCATE\R90-VISUAL-FACTORY-20261108\pyvendor"))
sys.path.insert(0,str(PIL))
from PIL import Image,ImageDraw,ImageFont
OUT=Path(os.environ.get("R90_ART_OUT",r"D:\AUTOFABRICADOR-RESCATE\R90-VISUAL-FACTORY-20261108\generated"))
NAMES=["harbor_back","harbor_front","workshop_back","workshop_front",
       "observatory_back","observatory_front","young_sailor","elder_whitebeard",
       "interface","lens","compass"]
INK="#141828";BLACK="#0b1024";GOLD="#e5b668";WARM="#f8dda5"
PAL={
 "sky0":"#111733","sky1":"#212949","sky2":"#493b58","sky3":"#94556a",
 "sky4":"#d98077","sky5":"#f7b988","deep":"#0c243f","sea":"#16435d",
 "sea2":"#27677b","sea3":"#3e8a89","foam":"#83a6a1","cream":"#fff0bd",
 "dark":"#1a2034","navy":"#263047","plum":"#43304a","wood":"#70423e",
 "wood2":"#99544a","wood3":"#bd7860","wood4":"#e5a16b","copper":"#d9a05f",
 "copper2":"#785244","rust":"#ae5552","stone":"#6f7786","stone2":"#9aa6a8",
 "stone3":"#c1b9aa","teal":"#32777e","glass":"#65b0ab","green":"#417567",
 "hair":"#533b3c","hair2":"#8c5044","skin":"#e1a17b","skin2":"#b97265",
 "light":"#ffd47e","white":"#e9e6d3","ice":"#aebcc5","coat":"#28636e",
 "coat2":"#3e9292","sleeve":"#1e4b5c","boots":"#3b3440","belt":"#5c363c",
 "beard":"#d6dbd8","beard2":"#9faeb7","eldercoat":"#4a586e",
 "eldercoat2":"#68798a","night":"#11152e","paper":"#e1c7a0",
 "paper2":"#f2d7a4","purple":"#6f5067","wine":"#7b354c"
}
rng=random.Random(19911208)
def P(key):return PAL.get(key,key)
def canvas(w=320,h=130):return Image.new("RGBA",(w,h),(0,0,0,0))
def d(img):return ImageDraw.Draw(img)
def rect(img,xy,color,outline=None,width=1):
 d(img).rectangle(tuple(map(int,xy)),fill=P(color),outline=P(outline) if outline else None,width=width)
def line(img,pts,color,width=1):d(img).line(pts,fill=P(color),width=width,joint="curve")
def poly(img,pts,color,outline=None):d(img).polygon(pts,fill=P(color),outline=P(outline) if outline else None)
def ell(img,xy,color,outline=None,width=1):d(img).ellipse(xy,fill=P(color),outline=P(outline) if outline else None,width=width)
def dot(img,x,y,color):d(img).point((int(x),int(y)),fill=P(color))
def txt(img,xy,value,color):
 d(img).text(xy,value,fill=P(color),font=ImageFont.load_default())
def io_png(img):
 b=io.BytesIO();img.save(b,"PNG",compress_level=9,optimize=False);return b.getvalue()
def sha(data):return hashlib.sha256(data).hexdigest()
def written(path,blob):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open("xb") as f:f.write(blob);f.flush();os.fsync(f.fileno())
 if sha(path.read_bytes())!=sha(blob):raise RuntimeError("R90_WRITE_SHA_BAD "+str(path))
def blend(images):
 out=canvas(*images[0].size)
 for layer in images:out=Image.alpha_composite(out,layer)
 return out
def ora(name,kind,layers,frame=None,semantic=None):
 imgs=[v for k,v in layers]
 final=blend(imgs)
 raw=io_png(final)
 op=OUT/"assets"/(name+".png")
 master=OUT/"source"/(name+".ora")
 written(op,raw)
 out=io.BytesIO()
 with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  def entry(path,data,compress=zipfile.ZIP_DEFLATED):
   info=zipfile.ZipInfo(path,date_time=(2026,11,8,12,0,0))
   info.compress_type=compress
   info.external_attr=0o644<<16
   z.writestr(info,data)
  entry("mimetype",b"image/openraster",zipfile.ZIP_STORED)
  import xml.sax.saxutils as xs
  parts=[f'<layer name="{xs.escape(title)}" src="data/{i:02d}.png" x="0" y="0"/>' for i,(title,_) in reversed(list(enumerate(layers)))]
  xml=(f'<?xml version="1.0" encoding="UTF-8"?><image w="{final.width}" h="{final.height}" name="{name}"><stack>'+"".join(parts)+"</stack></image>").encode()
  entry("stack.xml",xml)
  for i,(label,img) in enumerate(layers):entry(f"data/{i:02d}.png",io_png(img))
  entry("mergedimage.png",raw)
 written(master,out.getvalue())
 return {"id":name,"kind":kind,"png":"assets/"+name+".png","pngSHA256":sha(raw),
    "master":"source/"+name+".ora","masterSHA256":sha(out.getvalue()),"frame":frame,
    "editableLayers":[k for k,v in layers],"parts":semantic or []}
def sky_gradient(img,top,bottom,height):
 a=tuple(int(top[i:i+2],16) for i in (1,3,5))
 b=tuple(int(bottom[i:i+2],16) for i in (1,3,5))
 for y in range(height):
  u=y/max(1,height-1)
  u=u*u*(3-2*u)
  if height==94: u=round(u*64)/64  # original VGA pixel palette cap
  color=tuple(round((1-u)*a[j]+u*b[j]) for j in range(3))
  line(img,[(0,y),(319,y)],(*color,255))
def specks(img,xlo,ylo,xhi,yhi,n,colors,mask=None,seed=1):
 r=random.Random(seed)
 for _ in range(n):
  x=r.randrange(xlo,xhi);y=r.randrange(ylo,yhi)
  if mask and not mask(x,y):continue
  dot(img,x,y,r.choice(colors))
def harbor():
 sky,arch,objects,detail,lighting=[canvas() for _ in range(5)]
 sky_gradient(sky,"#0b1734","#e5a07d",94)
 # Vertical cloud banks and dramatic peach backlighting.
 for x,y,w,h in [(14,23,61,7),(78,31,50,8),(139,21,63,6),(242,29,55,7)]:
  ell(sky,(x,y,x+w,y+h),"#55415e")
  ell(sky,(x+9,y+2,x+w+7,y+h+3),"#74506b")
  line(sky,[(x+6,y+h+2),(x+w-12,y+h+2)],"#ce7778")
 ell(sky,(235,11,260,36),"#f9cf91")
 ell(sky,(241,14,257,30),"#ffe5aa")
 specks(sky,2,2,316,43,68,["#fff0cf","#f9d6a0","#a59ab7"],seed=9)
 poly(sky,[(0,75),(17,69),(36,72),(55,61),(76,72),(95,69),(129,79),(165,65),(189,74),(216,67),(247,78),(284,62),(319,71),(319,106),(0,107)],"#24364f")
 poly(sky,[(0,88),(23,83),(42,90),(65,81),(101,93),(147,81),(178,91),(214,84),(270,86),(297,81),(319,85),(319,130),(0,130)],"#193953")
 # Water has color bands, asymmetric specular reflections, ripples.
 for y in range(87,130):
  shade=["#124059","#1a5367","#22566b","#2b626e"][min(3,(y-87)//11)]
  line(sky,[(0,y),(319,y)],shade)
 for y in range(91,127,2):
  for k in range(42):
   x=rng.randrange(0,320)
   w=rng.choice([1,2,2,3,5,6])
   col=rng.choice(["#2d6976","#367786","#437e7d","#3d7280","#5d8786"])
   line(sky,[(x,y),(min(x+w,319),y)],col)
 # Lighthouse illumination and watery path
 for y in range(79,117):
  center=287+(y-79)//12
  for i in range(5):
   x=center+rng.randrange(-3*(y-76)//5,3*(y-76)//5+1)
   line(lighting,[(x,y),(x+rng.randrange(1,5),y)],rng.choice(["#f0b77a","#ffe2a0","#bca278"]))
 # Left tavern 0..96, plankwork and stylized facade.
 poly(arch,[(0,66),(18,55),(74,56),(95,68),(96,110),(0,113)],"wood",INK)
 poly(arch,[(0,62),(23,43),(69,44),(97,66),(93,69),(70,54),(23,53),(0,73)],"#24283e",BLACK)
 for x in range(-5,99,12):
  poly(arch,[(x+17,49),(x+28,53),(x+27,56),(x+13,52)],rng.choice(["#49374d","#624054","#784456"]))
 for y in range(69,108,9):
  line(detail,[(0,y),(96,y)],"wood2")
  for x in range(1,94,18):rect(detail,(x+((y//9)%2)*5,y+1,x+9,y+2),"wood3")
 for x in (9,27,44,72,90):
  rect(arch,(x,58,x+3,109),"#4e353b",BLACK)
  line(detail,[(x+2,59),(x+2,105)],"wood3")
 poly(arch,[(22,65),(78,63),(76,76),(25,77)],"wood3",INK)
 rect(arch,(28,65,69,72),"#754840",INK)
 txt(detail,(32,64),"EL FAROL","paper2")
 # Tavern arched amber window.
 rect(arch,(15,80,36,104),"#2c2737",BLACK)
 poly(arch,[(16,84),(18,79),(32,79),(35,84),(34,102),(17,102)],"#dc965b",INK)
 rect(lighting,(20,85,31,101),"#ffcf7e")
 line(detail,[(25,81),(25,103)],"wood")
 line(detail,[(16,91),(34,91)],"wood")
 # Door is hit polygon at x53..70.
 rect(arch,(51,77,71,114),"#201e30",BLACK)
 poly(arch,[(55,80),(64,77),(67,81),(67,111),(55,112)],"wood2")
 for x in (57,60,64):
  line(detail,[(x,83),(x,108)],"wood3")
 ell(detail,(63,96,65,98),"copper")
 # chimney roof, weather vane
 rect(arch,(43,35,50,46),"#433143",BLACK)
 rect(arch,(45,32,48,35),"rust")
 line(detail,[(50,32),(58,28)],"#887489")
 # Mooring boxes/net on left
 for x,y in [(4,112),(76,109)]:
  rect(objects,(x,y,x+14,y+12),"wood2",INK)
  for yy in (y+3,y+8):line(detail,[(x+2,yy),(x+13,yy)],"wood4")
  line(detail,[(x+1,y+1),(x+13,y+11)],"wood")
 # Ship mid distance. hull, deck, cabin, sail 166..243
 poly(objects,[(164,103),(242,102),(234,116),(181,120),(169,113)],"#3a273c",INK)
 poly(objects,[(171,108),(236,108),(230,115),(182,116)],"wood2")
 for x in range(174,233,12):line(detail,[(x,110),(x+3,115)],"wood4")
 poly(objects,[(177,103),(190,92),(215,91),(221,103)],"#614854",INK)
 rect(objects,(193,87,215,95),"#4b4b58",INK)
 rect(lighting,(202,91,208,94),"light")
 line(objects,[(206,48),(206,106)],"#3c3345",2)
 poly(objects,[(204,50),(182,98),(204,101)],"paper",INK)
 poly(detail,[(202,54),(190,90),(203,90)],"#fff1ce")
 poly(objects,[(210,59),(233,97),(211,99)],"#d4b7a2",INK)
 line(detail,[(210,56),(241,100)],"paper2")
 line(detail,[(210,50),(224,47)],"rust",2)
 line(detail,[(206,47),(178,102)],"#817184")
 line(detail,[(205,48),(236,103)],"#817184")
 for x in range(172,240,7):rect(detail,(x,101,x+2,102),"copper")
 # Lighthouse and cliffs far right.
 poly(arch,[(268,56),(284,45),(304,50),(309,105),(271,106)],"stone2",INK)
 poly(arch,[(280,47),(288,39),(298,42),(305,51),(304,58),(277,57)],"stone",BLACK)
 rect(arch,(279,36,300,45),"#36334a",INK)
 rect(lighting,(282,38,297,43),"light")
 rect(arch,(285,33,296,37),"#4f414f",INK)
 rect(detail,(278,55,304,57),"wood2")
 for y in range(61,103,8):
  line(detail,[(272,y),(306,y-1)],"stone")
  for x in range(278+(y%3)*3,305,8):line(detail,[(x,y),(x,y+4)],"stone3")
 rect(arch,(284,83,295,106),"#27273b",INK)
 poly(detail,[(288,83),(293,86),(292,106),(286,106)],"#555265")
 ell(lighting,(282,38,288,44),"#fff0b3")
 poly(lighting,[(290,38),(319,23),(319,52),(293,44)],(239,194,125,90))
 # Starboard pier and kelp detail mostly behind characters
 poly(objects,[(0,112),(110,104),(145,118),(145,130),(0,130)],"#4c3946",INK)
 for y in (112,117,123,128):line(detail,[(0,y),(145,y)],"wood2")
 for x in range(7,140,12):
  line(detail,[(x,111),(x+9,130)],"wood3")
 # R90C original fix: continuous timber jetty grounds the guardafaro at x168
 poly(objects,[(126,116),(153,110),(188,113),(199,121),(198,129),(126,129)],"wood2",INK)
 poly(objects,[(132,117),(159,113),(187,115),(193,120),(129,123)],"wood3",INK)
 for y in (118,123,127):line(detail,[(134,y),(194,y)],"wood")
 for x in range(138,196,11):line(detail,[(x,116),(x+7,129)],"wood4")
 for x in (141,185):
  rect(objects,(x,109,x+4,128),"#31293a",INK)
  line(detail,[(x+2,109),(x+2,126)],"wood3")
 # island structure near far right
 poly(objects,[(248,102),(265,96),(275,105),(267,113),(240,113)],"#252f45")
 # Rail lantern reflections and distant gulls
 for x,y in [(116,31),(123,28),(145,43)]:
  line(detail,[(x,y),(x+4,y+1),(x+7,y)],"#34344c")
 specks(detail,2,63,92,107,190,["#965849","#8d534f","#ab6855"],seed=174)
 return ora("harbor_back","background",list(zip(
  ["Sky and water", "Tavern and lighthouse", "Ships and dock architecture","Hand-painted detail","Warm environmental lighting"],
  [sky,arch,objects,detail,lighting])),semantic=["sky","sea","tavern","door","tavern_sign","ship","lighthouse","pier"])
def harbor_front():
 a,b,c,d=[canvas() for _ in range(4)]
 for x in (8,104,315):
  rect(a,(x-2,92,x+2,128),"#292637",BLACK)
  line(b,[(x-1,92),(x-1,123)],"wood3")
  rect(b,(x-4,97,x+4,100),"wood4")
 for x in range(0,320,18):
  line(a,[(x,127),(x+16,127)],"#573947",2)
 line(b,[(6,99),(104,114)],"wood3")
 line(b,[(105,113),(317,97)],"wood3")
 # Chain loops along wharf
 for x in range(10,106,14):
  line(b,[(x,102),(x+7,107),(x+14,104)],"#8c7571")
 # Hanging copper lamp left of main character, tiny warm flame
 line(a,[(117,0),(117,21)],BLACK)
 poly(a,[(112,21),(122,21),(125,26),(109,26)],"wood2",INK)
 rect(b,(112,27,121,37),"copper",INK)
 rect(c,(114,28,119,35),"light")
 dot(d,116,30,"paper2")
 line(b,[(109,37),(124,37)],"wood4")
 # Foreground stacked barrel w/highlights
 ell(a,(284,109,304,125),"wood2",INK)
 rect(b,(286,113,302,121),"wood3")
 line(b,[(287,115),(301,115)],"gold",2)
 line(b,[(287,121),(301,121)],"gold",2)
 return ora("harbor_front","foreground",list(zip(
  ["Near pier silhouette","Ropes and fixtures","Lantern and highlights","Specular flecks"],[a,b,c,d])),
  semantic=["rope","lamp","barrel","pier"])
def workshop():
 base,wood,objects,details,light=[canvas() for _ in range(5)]
 sky_gradient(base,"#31243d","#78565a",105)
 rect(base,(0,102,319,129),"#3d3444")
 for y in range(10,100,12):
  line(base,[(0,y),(319,y)],"#8d5c66")
  for x in range(-6,320,26):
   bx=x+(13 if y%24 else 0)
   line(base,[(bx,y),(bx,y+12)],"#754653")
 # structural rafters and exposed timber
 for x in (4,114,193,312):
  rect(wood,(x,0,x+8,103),"#4a3342",BLACK)
  line(wood,[(x+5,0),(x+5,101)],"wood2")
 poly(wood,[(0,0),(320,0),(319,14),(0,17)],"#29263b")
 line(details,[(3,15),(315,12)],"gold")
 # Detailed arched window, sea view
 poly(wood,[(126,86),(127,34),(138,24),(176,24),(188,37),(189,89)],"#22283c",INK)
 poly(base,[(131,82),(133,35),(145,29),(173,29),(181,38),(184,83)],"#213b56")
 for y in range(59,82):
  line(base,[(133,y),(183,y)],"#326475" if y%3 else "#63858a")
 ell(light,(166,37,180,51),"light")
 rect(details,(155,27,158,86),"wood4",INK)
 rect(details,(129,56,184,59),"wood3")
 rect(details,(127,84,188,88),"wood4")
 for y in range(36,84,7):dot(details,155,y,"copper")
 # Shelves left of scene and clusters of books/flasks
 rect(wood,(14,31,107,103),"#382f43",BLACK)
 for y in (38,55,73,91):
  rect(wood,(19,y,104,y+4),"wood3",BLACK)
 for shelf_y in (37,54,72):
  x=23
  while x<103:
   w=rng.randint(3,7)
   if rng.random()<0.25:
    rect(objects,(x,shelf_y-12,x+w,shelf_y-2),rng.choice(["stone2","teal","rust","wood4"]),BLACK)
    ell(details,(x+1,shelf_y-10,x+w-1,shelf_y-8),"glass")
   else:
    rect(objects,(x,shelf_y-13,x+w,shelf_y-2),rng.choice(["wood2","rust","teal","stone","coat"]),INK)
    rect(details,(x+1,shelf_y-11,x+1,shelf_y-3),"paper")
    if w>5:line(details,[(x+3,shelf_y-8),(x+w-1,shelf_y-8)],"gold")
   x+=w+1
 # Brass astronomical machine in correct hotspot x233..270
 for cx,cy,r in [(248,72,22),(271,84,13),(229,89,9)]:
  ell(objects,(cx-r-3,cy-r-3,cx+r+3,cy+r+3),"#352d42",INK)
  ell(objects,(cx-r,cy-r,cx+r,cy+r),"copper",INK)
  ell(objects,(cx-r+5,cy-r+5,cx+r-5,cy+r-5),"#465264",INK)
  ell(objects,(cx-3,cy-3,cx+3,cy+3),"light",INK)
  for i in range(12):
   theta=i*math.tau/12
   x=int(cx+(r+1)*math.cos(theta));y=int(cy+(r+1)*math.sin(theta))
   rect(details,(x-1,y-1,x+1,y+1),"wood4")
  line(details,[(cx,cy),(cx+int(r*.6),cy-int(r*.4))],"paper")
 # workbench x185-310
 poly(wood,[(182,103),(318,100),(319,111),(180,115)],"wood3",INK)
 poly(wood,[(182,113),(318,110),(316,118),(184,120)],"wood2",INK)
 for x in (192,303):
  rect(wood,(x,117,x+7,130),"#3e3443",INK)
  line(details,[(x+1,118),(x+1,128)],"wood4")
 # Small tools and scientific devices
 rect(objects,(198,82,211,102),"stone",INK)
 ell(objects,(198,78,211,84),"glass",INK)
 line(details,[(203,81),(203,94)],"light")
 rect(objects,(285,85,296,100),"wine",INK)
 rect(details,(288,87,293,95),"paper2")
 ell(light,(285,81,297,88),"light")
 poly(objects,[(215,98),(229,93),(234,99),(226,103)],"paper")
 line(details,[(217,99),(229,96)],"wood")
 # Storage drawers near compass, preserve pickup x83..99
 rect(wood,(63,101,111,121),"wood",INK)
 for x in (66,88):
  rect(details,(x,104,x+18,117),"wood2",INK)
  rect(details,(x+8,109,x+10,111),"gold")
 # Exit door at x300
 rect(wood,(299,54,319,123),"#25273e",BLACK)
 poly(wood,[(303,58),(315,59),(315,121),(302,121)],"wood2",INK)
 for y in range(65,117,12):line(details,[(303,y),(314,y)],"wood3")
 ell(details,(306,95,309,98),"gold")
 # floor with perspective and scattered dust
 for y in range(103,130,5):
  line(base,[(0,y),(319,y)],"#635064")
 for x in range(-10,320,18):
  line(details,[(x,105),(x+18,129)],"#5e4857")
 specks(details,0,105,319,129,175,["#84606b","#6f5261","#966e68"],seed=312)
 # lantern glow
 ell(light,(95,12,113,32),(248,186,105,82))
 ell(light,(102,19,107,24),"paper2")
 return ora("workshop_back","background",list(zip(
  ["Stone and dusk window","Timber and architectural structure","Books, devices and machinery",
   "Gears and floor detail","Candle and brass highlights"],[base,wood,objects,details,light])),
  semantic=["bookshelf","arched_window","mechanism","workbench","compass_cabinet","exit"])
def workshop_front():
 a,b,c,d=[canvas() for _ in range(4)]
 rect(a,(0,123,319,129),"#3f3444")
 line(b,[(0,121),(319,121)],"wood4")
 for x in range(0,319,19):line(b,[(x,124),(x+8,129)],"wood2")
 # Hanging chain / ropes
 for x in (9,311):
  line(a,[(x,0),(x,39)],INK)
  for y in range(6,39,4):rect(b,(x,y,x+1,y+2),"copper")
 # foreground tool handles & hanging small lamp
 rect(c,(7,111,17,120),"wood2",INK)
 line(c,[(12,106),(12,117)],"gold",2)
 rect(c,(305,106,315,117),"wood3",INK)
 return ora("workshop_front","foreground",list(zip(
  ["Floor edge shadow","Chains and flooring","Small tools","Distant reflection"],[a,b,c,d])),
  semantic=["chains","floor","tools"])
def observatory():
 sky,arch,objects,details,glow=[canvas() for _ in range(5)]
 sky_gradient(sky,"#0d1838","#7d506b",95)
 for i in range(145):
  x=rng.randrange(35,294);y=rng.randrange(9,89)
  dot(sky,x,y,rng.choice(["paper","#f9d2bb","#9da8c7","#becde1"]))
 for cx,cy in [(67,20),(103,44),(187,26),(259,38)]:
  for a,b in [((-3,0),(3,0)),((0,-3),(0,3))]:
   line(details,[(cx+a[0],cy+a[1]),(cx+b[0],cy+b[1])],"paper")
 poly(sky,[(0,87),(28,82),(54,71),(91,85),(120,68),(145,80),(196,72),(228,85),(267,74),(319,80),(319,104),(0,104)],"#343c5b")
 # huge vaulted copper dome & grand angular window
 poly(arch,[(10,102),(15,45),(39,20),(96,8),(203,8),(271,21),(304,53),(309,104)],"#292e45",INK)
 poly(arch,[(21,99),(26,44),(47,28),(102,16),(199,16),(267,29),(293,54),(300,102)],"#455269",INK)
 poly(arch,[(29,98),(33,46),(53,32),(107,22),(197,22),(261,34),(286,57),(293,98)],"#192946",INK)
 # insert celestial sky into window opening, segmented crystal panes
 for y in range(34,94):
  spread=min(124,int(121*math.sqrt(max(0.001,1-((y-94)/98)**2))))
  line(arch,[(158-spread,y),(158+spread,y)],rng.choice(["#293558","#2b3b60","#293b5d"]))
 for i in range(78):
  x=rng.randrange(43,285);y=rng.randrange(31,91)
  dot(details,x,y,rng.choice(["paper","paper2","#b0b8d9"]))
 # gothic window arch and ribs
 for x0,y0 in [(28,101),(74,32),(152,23),(229,31),(292,101)]:
  line(details,[(x0,y0),(x0+(158-x0)//3,17)],"#99765f",2)
 line(arch,[(153,23),(153,100)],"copper",3)
 line(details,[(157,23),(157,100)],"wood4")
 for yy in (44,64,83):
  line(details,[(33,yy),(286,yy)],"#4e5870")
 # ornate side columns and wooden floor
 for x in (11,299):
  rect(arch,(x,34,x+11,113),"#564154",INK)
  line(details,[(x+3,38),(x+3,104)],"wood4")
  for y in (42,61,84,102):
   rect(details,(x-3,y,x+13,y+3),"copper2")
 poly(arch,[(0,96),(319,96),(319,130),(0,130)],"#443648")
 for y in (99,106,115,123):line(details,[(0,y),(319,y)],"wood")
 for x in range(-35,350,17):line(details,[(x,98),(x+23,129)],"#634759")
 # telescope brass x160..204
 poly(objects,[(160,76),(192,54),(211,61),(175,84)],"#292b3c",INK)
 poly(objects,[(165,74),(190,58),(207,62),(175,80)],"#b27b55",INK)
 line(details,[(168,75),(200,62)],"light",2)
 ell(objects,(204,56,212,65),"paper2",INK)
 ell(glow,(205,58,211,63),"light")
 rect(objects,(177,78,184,86),"wood3",INK)
 for x,y in [(164,120),(183,126),(199,123)]:
  line(objects,[(180,85),(x,y)],"wood4",2)
 ell(objects,(176,81,185,90),"gold",INK)
 # giant astro clock left
 ell(objects,(61,58,116,111),"#26283e",INK)
 ell(objects,(64,61,113,108),"gold",INK)
 ell(objects,(70,67,107,102),"#5b4257",INK)
 for i in range(12):
  a=i*math.tau/12;x=89+int(19*math.cos(a));y=86+int(18*math.sin(a))
  rect(details,(x-1,y-1,x+1,y+1),"paper")
 line(details,[(89,86),(101,74)],"paper2")
 line(details,[(89,86),(79,93)],"paper")
 # desk, star chart at x224..276
 poly(objects,[(218,95),(284,92),(296,101),(217,105)],"wood3",INK)
 poly(objects,[(218,104),(298,100),(296,110),(220,115)],"wood2",INK)
 for x in (228,282):line(objects,[(x,111),(x+1,129)],"wood4",4)
 poly(objects,[(230,91),(265,88),(274,97),(230,100)],"paper",INK)
 for cx,cy in [(238,93),(250,94),(262,92)]:
  line(details,[(cx,cy),(cx+5,cy+2)],"wood")
  dot(details,cx+2,cy+1,"rust")
 rect(objects,(280,81,288,95),"copper2",INK)
 ell(glow,(280,77,287,86),"light")
 # large ceiling compass rose and detailed cables
 for a in range(8):
  angle=a*math.tau/8
  x=152+int(18*math.cos(angle));y=21+int(9*math.sin(angle))
  line(details,[(152,21),(x,y)],"gold")
 ell(details,(150,19,154,23),"paper2")
 specks(details,10,105,310,129,155,["#775368","#6a4c60","#a0776e"],seed=411)
 return ora("observatory_back","background",list(zip(
  ["Sky and distant mountain range","Vault, stained windows and floor",
   "Brass astronomy instruments","Hand-detailed map and star constellations",
   "Glass and lamplight"],[sky,arch,objects,details,glow])),
  semantic=["celestial_window","telescope","celestial_chart","clock","stairs","star_map"])
def observatory_front():
 a,b,c,d=[canvas() for _ in range(4)]
 for x in (3,45,271,313):
  rect(a,(x,113,x+4,130),"#28253c",INK)
  rect(b,(x+1,110,x+2,126),"wood4")
 for x in range(0,48,7):
  line(b,[(x,116),(x+6,119)],"copper2")
 for x in range(273,320,7):
  line(b,[(x,119),(x+5,115)],"wood2")
 line(a,[(4,120),(47,120)],"#583947",2)
 line(a,[(273,120),(318,120)],"#583947",2)
 # one hanging astrolabe
 line(a,[(9,0),(9,26)],INK)
 ell(b,(4,24,15,36),"copper",INK)
 ell(c,(7,27,12,33),"paper2")
 return ora("observatory_front","foreground",list(zip(
  ["Architectural near rail","Warm rails and gilding","Hanging star medallion","Light sparkle"],[a,b,c,d])),
  semantic=["rail","star_medallion"])
def hero_frame(layers,frame,elder=False):
 base,cloth,face,details=layers
 x=frame*24
 mode="idle"
 if frame in (2,3,4,5):mode="walk"
 if frame in (6,7):mode="talk"
 if frame==8:mode="look"
 if frame==9:mode="pick"
 if frame in (10,11):mode="use"
 if frame in (12,13):mode="react"
 phase=frame%4
 bob=(-1 if mode=="walk" and phase in (1,3) else 0)
 bend=6 if mode=="pick" else 0
 heady=8+bob+bend
 for i in (0,):
  pass
 # Feet and simple dimensional cast shadow
 ell(base,(x+3,44,x+21,47),(24,22,35,98))
 poly(base,[(x+7,30+bob),(x+12,29+bob),(x+11,44),(x+5,44)],"boots",INK)
 poly(base,[(x+13,29+bob),(x+18,29+bob),(x+20,44),(x+13,44)],"boots",INK)
 if mode=="walk":
  if phase%2:
   poly(base,[(x+6,36),(x+12,35),(x+9,44),(x+3,44)],"boots")
   poly(base,[(x+15,37),(x+20,38),(x+22,43),(x+17,44)],"#493f45")
  else:
   line(base,[(x+6,44),(x+8,38),(x+12,39)],"#5c3e44",3)
   line(base,[(x+19,44),(x+16,38),(x+15,39)],"#5c3e44",3)
 rect(details,(x+4,43,x+11,45),BLACK)
 rect(details,(x+15,43,x+22,45),BLACK)
 if elder:
  # billowing plum/navy longcoat with high collar, asymmetric shoulder.
  poly(cloth,[(x+5,25+bob),(x+19,25+bob),(x+23,42),(x+4,43)],"eldercoat",INK)
  poly(cloth,[(x+12,27+bob),(x+20,27+bob),(x+19,42),(x+14,42)],"eldercoat2")
  line(details,[(x+12,28),(x+13,40)],"copper")
  poly(face,[(x+8,heady+6),(x+9,heady+2),(x+17,heady),(x+21,heady+7),(x+18,heady+18),(x+9,heady+18)],"skin",INK)
  # rich beard shape in four shades
  poly(face,[(x+7,heady+13),(x+10,heady+15),(x+18,heady+14),(x+20,heady+16),(x+20,heady+25),(x+15,heady+30),(x+9,heady+27),(x+6,heady+19)],"beard2",INK)
  poly(face,[(x+8,heady+15),(x+13,heady+18),(x+18,heady+15),(x+17,heady+24),(x+13,heady+28),(x+9,heady+25)],"beard")
  line(details,[(x+9,heady+16),(x+9,heady+22)],"white")
  line(details,[(x+15,heady+17),(x+15,heady+25)],"white")
  # sweeping sideburns and eyebrows
  poly(face,[(x+7,heady+5),(x+8,heady-2),(x+16,heady-3),(x+20,heady+3),(x+20,heady+8),(x+16,heady+5)],"beard2")
  line(details,[(x+7,heady+9),(x+11,heady+9)],"white",2)
  line(details,[(x+15,heady+8),(x+18,heady+8)],"white",2)
  if frame!=1:dot(details,x+10,heady+11,BLACK)
  dot(details,x+17,heady+10,BLACK)
  line(details,[(x+10,heady+15),(x+16,heady+16)],"white")
  poly(cloth,[(x+3,27+bob),(x+8,27+bob),(x+9,38+bob),(x+4,41+bob)],"eldercoat2",INK)
  poly(cloth,[(x+19,27+bob),(x+22,30+bob),(x+22,41+bob),(x+17,38+bob)],"eldercoat",INK)
  # old brass cane, unique separate accessory
  line(details,[(x+22,27),(x+22,45)],"wood4",2)
  line(details,[(x+20,27),(x+24,27)],"gold")
 else:
  # swashbuckler silhouette: asymmetrical teal frock coat, vivid crimson sash.
  poly(cloth,[(x+5,26+bob),(x+9,23+bob),(x+18,25+bob),(x+22,34+bob),(x+20,42),(x+5,42)],"coat",INK)
  poly(cloth,[(x+11,27+bob),(x+17,27+bob),(x+20,40),(x+13,42)],"coat2")
  poly(cloth,[(x+7,25+bob),(x+13,26+bob),(x+15,33+bob),(x+7,32+bob)],"wine",INK)
  line(details,[(x+8,30+bob),(x+20,31+bob)],"rust",2)
  rect(details,(x+10,34+bob,x+20,36+bob),"belt")
  rect(details,(x+13,34+bob,x+15,36+bob),"gold")
  # 3/4 face with expressive longer nose
  poly(face,[(x+7,heady+1),(x+11,heady-1),(x+17,heady),(x+20,heady+5),(x+20,heady+14),(x+17,heady+17),(x+9,heady+17),(x+5,heady+12)],"skin",INK)
  poly(face,[(x+6,heady+10),(x+11,heady+10),(x+8,heady+14),(x+5,heady+12)],"skin2")
  # swept hair and pointy long fringe: more expressive character shape
  poly(face,[(x+5,heady+6),(x+5,heady+0),(x+9,heady-4),(x+18,heady-3),(x+22,heady+1),
             (x+21,heady+5),(x+18,heady+2),(x+14,heady+5),(x+9,heady+4)],"hair",INK)
  poly(details,[(x+6,heady+2),(x+10,heady-3),(x+16,heady-3),(x+12,heady+1)],"hair2")
  rect(face,(x+17,heady+10,x+22,heady+12),"skin")
  if frame!=1:dot(details,x+11,heady+8,BLACK)
  dot(details,x+17,heady+8,BLACK)
  dot(details,x+18,heady+7,"white")
  line(details,[(x+8,heady+5),(x+12,heady+6)],"hair")
  if mode=="react":
   rect(details,(x+10,heady+11,x+12,heady+14),BLACK)
  elif mode=="talk" and frame==7:
   rect(details,(x+13,heady+13,x+17,heady+14),"wine")
  else:
   line(details,[(x+12,heady+14),(x+16,heady+14)],"skin2")
  # bright shirt collar
  poly(face,[(x+10,heady+18),(x+16,heady+18),(x+13,heady+23)],"paper2",INK)
  # asymmetric sleeve animation and bare hand
  arm_offset=(4 if mode=="use" else (-4 if mode=="react" else (phase%3-1 if mode=="walk" else 0)))
  poly(cloth,[(x+4,27+bob),(x+7,27+bob),(x+8,37+arm_offset),(x+4,39+arm_offset)],"coat2",INK)
  poly(cloth,[(x+19,26+bob),(x+23,28+bob),(x+22,37-arm_offset),(x+19,39-arm_offset)],"sleeve",INK)
  rect(face,(x+4,39+arm_offset,x+7,42+arm_offset),"skin",INK)
  rect(face,(x+19,38-arm_offset,x+22,41-arm_offset),"skin",INK)
  if mode=="look":
   line(details,[(x+20,29),(x+23,21)],"skin",3)
  elif mode=="use":
   line(details,[(x+19,30),(x+23,28)],"skin",2)
  if mode=="walk":
   line(details,[(x+10,28+bob),(x+18,30+bob)],"wood4")
 # highlights on silhouette for hand-painted dimensional shading
 dot(details,x+8,27+bob,"gold")
 if mode in ("talk","react"):
  if elder:
   line(details,[(x+12,heady+23),(x+15,heady+24)],"wine")
def sprites(name,elder):
 base=canvas(336,48);cloth=canvas(336,48);face=canvas(336,48);details=canvas(336,48)
 for i in range(14):hero_frame([base,cloth,face,details],i,elder)
 return ora(name,"character",[
  ("Footsteps and silhouette",base),("Coat and clothing",cloth),
  ("Skin, beard and hair",face),("Expression, accessories and glints",details)],
  {"width":24,"height":48,"count":14},
  ["idle","walk","talk","look","pick","use","react"])
def ui():
 b,ornament,engraving,shine=[canvas(320,50) for _ in range(4)]
 rect(b,(0,0,319,49),"#292339")
 rect(b,(0,0,319,3),"copper")
 rect(b,(0,4,319,24),"#37273a")
 rect(b,(0,25,319,49),"#221f34")
 for i in range(5):
  x=i*64
  rect(ornament,(x+2,6,x+60,22),"#62414e",BLACK)
  rect(ornament,(x+4,8,x+58,20),"#2c2c40")
  line(engraving,[(x+5,8),(x+57,8)],"wood3")
  line(engraving,[(x+5,20),(x+57,20)],"#644253")
  for xx in (x+4,x+58):
   dot(shine,xx,7,"gold")
   dot(shine,xx,21,"wood4")
 for i in range(6):
  x=i*50
  rect(ornament,(x+2,27,x+46,46),"#433348",BLACK)
  line(engraving,[(x+4,29),(x+44,29)],"copper2")
 line(shine,[(0,48),(319,48)],"copper")
 for x in range(3,319,17):dot(shine,x,48,"paper2")
 return ora("interface","ui",list(zip(
  ["Midnight purple panel","Engraved verb buttons","Inventory compartments","Brass edge details"],
  [b,ornament,engraving,shine])),
  semantic=["verbs","inventory","caption","panel"])
def obj(name):
 b,metal,glass,reflection=[canvas(16,16) for _ in range(4)]
 if name=="lens":
  ell(b,(1,1,12,12),"copper2",INK)
  ell(metal,(2,2,11,11),"gold",INK)
  ell(glass,(4,4,9,9),"glass",INK)
  line(metal,[(11,11),(15,15)],"wood4",2)
  line(reflection,[(4,5),(6,4)],"paper2")
 else:
  ell(b,(0,0,15,15),"copper",INK)
  ell(metal,(2,2,13,13),"paper",INK)
  poly(glass,[(7,3),(11,10),(8,9)],"rust")
  poly(glass,[(8,13),(4,5),(8,8)],"deep")
  dot(reflection,8,8,INK)
  for x,y in [(8,2),(2,8),(13,8),(8,13)]:dot(reflection,x,y,"gold")
 return ora(name,"object",list(zip(
  ["Artifact silhouette","Metalwork","Glass and enamel","Hand-painted reflected light"],
  [b,metal,glass,reflection])),
  {"width":16,"height":16,"count":1},[name])
def main():
 if OUT.exists():raise RuntimeError("R90_OUTPUT_ALREADY_EXISTS_NO_REPLAY")
 records=[harbor(),harbor_front(),workshop(),workshop_front(),
  observatory(),observatory_front(),sprites("young_sailor",False),
  sprites("elder_whitebeard",True),ui(),obj("lens"),obj("compass")]
 if [r["id"] for r in records]!=NAMES:raise RuntimeError("R90_ORDER_WRONG")
 # every source master remains editable in >=4 independent semantic layers.
 import xml.etree.ElementTree as ET
 for r in records:
  with zipfile.ZipFile(OUT/r["master"]) as z:
   xml=ET.fromstring(z.read("stack.xml"))
   layers=list(xml.iter("layer"))
   if len(layers)<4:raise RuntimeError("R90_EDITABLE_LAYERS_TOO_FEW")
  if (OUT/r["png"]).stat().st_size > 8*1024*1024:raise RuntimeError("R90_PNG_TOO_BIG")
 receipt={"schema":1,"operationId":"AF.R90.FROZEN-PALETTE-11-SEPARATE-ASSETS-20261108",
  "status":"PASS_ELEVEN_NEW_LAYERED_ART_SOURCES","nativeGrid":[320,180],
  "sceneGrid":[320,130],"spritesheet":[336,48],
  "pixelArtNotHumanApproved":True,"modelDidNotDrawAssets":True,
  "assets":records,"assetCount":len(records)}
 written(OUT/"R90-ART-MANIFEST.json",
   (json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode())
 print(json.dumps({"status":receipt["status"],"count":len(records),
   "sha256":sha((OUT/"R90-ART-MANIFEST.json").read_bytes()),
   "layers":{r["id"]:len(r["editableLayers"]) for r in records}},indent=2))
if __name__=="__main__":main()
