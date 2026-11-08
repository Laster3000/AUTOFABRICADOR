# coding: utf-8
"""R87 independent tests of real PNG bytes and editable OpenRaster masters."""
from __future__ import annotations

import copy
import io
import json
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from autofab import adventure_visual_gate_r88 as G


def png_rgba(width, height, mode="background"):
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            if mode == "sprite":
                # A deliberately trivial fixture silhouette, NOT production game art.
                px = x % 24
                active = 8 <= px <= 15 and 8 <= y <= 43
                rgba = (120, 90, 60, 255) if active else (0, 0, 0, 0)
            elif mode == "ui":
                rgba = (42, 26, 38, 255) if y < 40 else (54, 38, 45, 255)
            else:
                rgba = (65, 66 + (y % 2), 85, 255)
            row.extend(rgba)
        rows.append(b"\x00" + bytes(row))
    def chunk(tag, data):
        return struct.pack(">I",len(data)) + tag + data + struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
    return (G.PNG + chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,6,0,0,0)) +
            chunk(b"IDAT",zlib.compress(b"".join(rows),level=7)) + chunk(b"IEND",b""))


def open_raster(png, w, h):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem,"w") as z:
        z.writestr("mimetype",b"image/openraster",compress_type=zipfile.ZIP_STORED)
        z.writestr("stack.xml",('<image w="%s" h="%s"><stack><layer name="Paint" src="data/layer0.png" x="0" y="0"/></stack></image>'%(w,h)).encode())
        z.writestr("data/layer0.png",png)
        z.writestr("mergedimage.png",png)
    return mem.getvalue()


class VisualGate(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="AF-R88-WIDE-")
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        (self.root/"assets").mkdir()
        (self.root/"source").mkdir()
        self.doc={
            "schema":1,
            "profile":{"canvas":[320,180],"presentation":[640,360],"renderScale":2,"aspect":"16:9","sceneHeight":130,
                       "sampling":"nearest","startMode":"manual","pixelArt":True},
            "assets":[],
            "characters":[],
            "scene":{"id":"abandoned_workshop","background":"workshop_back",
                     "walkable":[[10,75],[308,75],[308,129],[10,129]],
                     "playerStart":[34,110],
                     "hotspots":[
                        {"id":"wooden_door","name":"Puerta","polygon":[[230,22],[270,22],[270,88],[230,88]],
                         "walkTo":[239,110],"verbs":["LOOK","OPEN","USE"],
                         "feedback":"No se abre sin una llave."},
                        {"id":"old_lamp","name":"Lampara","polygon":[[82,20],[106,20],[106,50],[82,50]],
                         "walkTo":[90,100],"verbs":["LOOK","TAKE"],
                         "feedback":"Ilumina la mesa."},
                        {"id":"small_chest","name":"Baul","polygon":[[120,91],[150,91],[150,118],[120,118]],
                         "walkTo":[133,122],"verbs":["LOOK","USE"],
                         "feedback":"Es un baul oxidado."}
                     ]},
            "ui":{"asset":"classic_bottom","verbs":["WALK","LOOK","TAKE","USE","TALK","OPEN"],
                  "inventorySlots":6,"minTargetPx":12,"fontPx":7}
        }
        self.write_asset("workshop_back","background",320,130,"background")
        self.write_asset("classic_bottom","ui",320,50,"ui")
        for aid in ("hero_original","elder_whitebeard"):
            self.write_asset(aid,"character",24*14,48,"sprite",
                             {"width":24,"height":48,"count":14})
            self.doc["characters"].append(
                {"id":aid,"asset":aid,"pivot":[12,47],"baselineY":112,
                 "animations":{"idle":[0,1],"walk":[2,3,4,5],"talk":[6,7],
                               "look":[8],"pick":[9],"use":[10,11],"react":[12,13]}})
        self.write_doc()

    def write_asset(self,aid,kind,w,h,mode,frame=None):
        png=png_rgba(w,h,mode)
        master=open_raster(png,w,h)
        path=self.root/"assets"/(aid+".png")
        source=self.root/"source"/(aid+".ora")
        path.write_bytes(png)
        source.write_bytes(master)
        self.doc["assets"].append({"id":aid,"kind":kind,
            "png":"assets/"+aid+".png","pngSHA256":G.sha(png),
            "master":"source/"+aid+".ora","masterSHA256":G.sha(master),
            "frame":frame})

    def write_doc(self):
        self.manifest=self.root/"scene-visual-contract.json"
        self.manifest.write_text(json.dumps(self.doc,ensure_ascii=False,indent=2),encoding="utf-8")

    def fail_reason(self,term):
        self.write_doc()
        result=G.audit(self.manifest)
        self.assertFalse(result["technicalPass"],result)
        self.assertEqual(result["status"],"BLOCKED_TECHNICAL_VISUAL_CONTRACT")
        self.assertIn(term, " | ".join(result["errors"]))
        self.assertFalse(result["artisticQualityAccepted"])

    def test_genuine_png_and_ora_pass_technical(self):
        result=G.audit(self.manifest)
        self.assertTrue(result["technicalPass"],result)
        self.assertEqual(result["assetCountVerified"],4)
        self.assertEqual(result["assets"]["elder_whitebeard"]["master"]["editableLayers"],1)
        self.assertFalse(result["artisticQualityAccepted"])
        self.assertTrue(result["requiresHumanVisualReview"])
        self.assertFalse(result["fullGameAccepted"])

    def test_screen_profile_fail_closed(self):
        for key,val,reason in [
            ("canvas",[320,200],"VGA_PROFILE_MISMATCH"),
            ("presentation",[800,600],"VGA_PROFILE_MISMATCH"),
            ("renderScale",3,"VGA_PROFILE_MISMATCH"),
            ("aspect","4:3","VGA_PROFILE_MISMATCH"),
            ("sampling","linear","VGA_PROFILE_MISMATCH"),
            ("startMode","windows_autostart","VGA_PROFILE_MISMATCH"),
            ("pixelArt",False,"VGA_PROFILE_MISMATCH")
        ]:
            with self.subTest(key=key):
                old=self.doc["profile"][key]
                self.doc["profile"][key]=val
                self.fail_reason(reason)
                self.doc["profile"][key]=old

    def test_missing_editable_master_is_blocked(self):
        (self.root/"source"/"hero_original.ora").unlink()
        self.fail_reason("ASSET_MISSING_OR_REPARSE_DENIED")

    def test_master_bytes_changed_detected(self):
        f=self.root/"source"/"elder_whitebeard.ora"
        f.write_bytes(f.read_bytes()+b"tamper")
        self.fail_reason("ASSET_MASTER_SHA_DRIFT")

    def test_image_bytes_changed_detected(self):
        f=self.root/"assets"/"classic_bottom.png"
        f.write_bytes(f.read_bytes()+b"tamper")
        self.fail_reason("ASSET_PNG_SHA_DRIFT")

    def test_bad_crc_detected_even_when_sha_refrozen(self):
        f=self.root/"assets"/"workshop_back.png"
        data=bytearray(f.read_bytes())
        data[31]^=1
        f.write_bytes(data)
        self.doc["assets"][0]["pngSHA256"]=G.sha(bytes(data))
        self.fail_reason("PNG_CRC_BAD")

    def test_bad_png_filter_detected(self):
        data=png_rgba(2,2)
        # Construct an otherwise valid PNG with an illegal scanline filter.
        payload=bytes([5])+bytes(2*4)+bytes([0])+bytes(2*4)
        def chunk(tag,v):
            return struct.pack(">I",len(v))+tag+v+struct.pack(">I",zlib.crc32(tag+v)&0xffffffff)
        ihdr=struct.pack(">IIBBBBB",2,2,8,6,0,0,0)
        invalid=G.PNG+chunk(b"IHDR",ihdr)+chunk(b"IDAT",zlib.compress(payload))+chunk(b"IEND",b"")
        with self.assertRaisesRegex(G.ContractError,"PNG_FILTER_BAD"):
            G.png_info(invalid)

    def test_png_unexpected_trailing_bytes_blocked(self):
        with self.assertRaisesRegex(G.ContractError,"PNG_TRAILING_OR_IEND_BAD"):
            G.png_info(png_rgba(2,2)+b"other")

    def test_png_interlace_not_accepted(self):
        data=bytearray(png_rgba(2,2))
        # IHDR last field is interlace method at PNG offset 28.
        data[28]=1
        data[29:33]=struct.pack(">I",zlib.crc32(data[12:29])&0xffffffff)
        with self.assertRaisesRegex(G.ContractError,"PNG_FORMAT_NOT_PINNED"):
            G.png_info(bytes(data))

    def test_aesthetic_pass_not_claimed_from_fixture(self):
        self.assertFalse(G.audit(self.manifest)["artisticQualityAccepted"])

    def test_missing_animation_blocked(self):
        del self.doc["characters"][1]["animations"]["react"]
        self.fail_reason("CHARACTER_ANIMATION_REQUIRED")

    def test_animation_frame_bounds(self):
        self.doc["characters"][1]["animations"]["walk"]=[100]
        self.fail_reason("CHARACTER_ANIMATION_FRAME_BAD")

    def test_character_reference_not_present(self):
        self.doc["characters"][1]["asset"]="missing_sprite"
        self.fail_reason("CHARACTER_ASSET_MISSING")

    def test_pivot_out_of_bounds(self):
        self.doc["characters"][0]["pivot"]=[99,47]
        self.fail_reason("CHARACTER_PIVOT_INVALID")

    def test_missing_character_source(self):
        self.doc["assets"][2]["master"]="source/not_there.ora"
        self.fail_reason("ASSET_MISSING_OR_REPARSE_DENIED")

    def test_path_traversal_denied(self):
        self.doc["assets"][0]["png"]="assets/../../secret.png"
        self.fail_reason("ASSET_PATH_ESCAPE")

    def test_absolute_path_denied(self):
        self.doc["assets"][0]["png"]="C:/Windows/Temp/a.png"
        self.fail_reason("ASSET_PATH_ESCAPE")

    def test_scene_hotspot_too_small(self):
        self.doc["scene"]["hotspots"][0]["polygon"]=[[10,10],[12,10],[12,12]]
        self.fail_reason("POLYGON_TOO_SMALL")

    def test_scene_hotspot_walkto_reachability(self):
        self.doc["scene"]["hotspots"][0]["walkTo"]=[240,20]
        self.fail_reason("HOTSPOT_WALKTO_NOT_REACHABLE")

    def test_scene_player_spawn_must_be_walkable(self):
        self.doc["scene"]["playerStart"]=[20,20]
        self.fail_reason("PLAYER_START_NOT_WALKABLE")

    def test_scene_hotspot_duplicate(self):
        self.doc["scene"]["hotspots"][2]["id"]="old_lamp"
        self.fail_reason("HOTSPOT_ID_DUPLICATE")

    def test_interaction_must_provide_feedback(self):
        self.doc["scene"]["hotspots"][0]["feedback"]=""
        self.fail_reason("HOTSPOT_FEEDBACK_REQUIRED")

    def test_interaction_unsupported_verb(self):
        self.doc["scene"]["hotspots"][0]["verbs"]=["FLY"]
        self.fail_reason("HOTSPOT_VERBS_INVALID")

    def test_ui_missing_essential_verb(self):
        self.doc["ui"]["verbs"]=["WALK","LOOK","TALK"]
        self.fail_reason("UI_VERBS_INCOMPLETE")

    def test_ui_click_targets_not_micro(self):
        self.doc["ui"]["minTargetPx"]=4
        self.fail_reason("UI_HIT_TARGET_TOO_SMALL")

    def test_ui_font_legibility_minimum(self):
        self.doc["ui"]["fontPx"]=3
        self.fail_reason("UI_HIT_TARGET_TOO_SMALL")

    def test_sprite_must_have_transparency(self):
        png=png_rgba(336,48,"ui")
        f=self.root/"assets"/"hero_original.png"
        f.write_bytes(png)
        self.doc["assets"][2]["pngSHA256"]=G.sha(png)
        self.fail_reason("SPRITE_TRANSPARENCY_REQUIRED")

    def test_sprite_sheet_grid_must_match(self):
        self.doc["assets"][2]["frame"]["count"]=12
        self.fail_reason("SPRITE_GRID_BAD")

    def test_background_dimensions_must_match(self):
        p=self.root/"assets"/"workshop_back.png"
        png=png_rgba(319,130)
        p.write_bytes(png)
        self.doc["assets"][0]["pngSHA256"]=G.sha(png)
        self.fail_reason("SCENE_LAYER_DIMENSIONS")

    def test_no_opaque_binary_master_lie(self):
        f=self.root/"source"/"elder_whitebeard.ora"
        f.write_bytes(b"not a layered source")
        self.doc["assets"][3]["masterSHA256"]=G.sha(f.read_bytes())
        self.fail_reason("MASTER_NOT_OPENRASTER")

    def test_owner_manifest_rejects_extra_fields(self):
        self.doc["modelMayAutoAcceptArtwork"]=True
        self.fail_reason("MANIFEST_SCHEMA_KEYS")

    def test_duplicate_json_keys_denied(self):
        data=self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(data.replace('"schema": 1,','"schema": 1, "schema": 1,',1),encoding="utf-8")
        self.assertIn("DUPLICATE_JSON_KEY",str(G.audit(self.manifest)["errors"]))

    def test_nonfinite_json_denied(self):
        data=self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(data.replace('"schema": 1','"schema": NaN',1),encoding="utf-8")
        self.assertIn("NONFINITE_JSON_VALUE",str(G.audit(self.manifest)["errors"]))

    def test_manifest_does_not_execute_source(self):
        self.assertEqual(G.audit(self.manifest)["sourceExecution"],"NONE_READ_ONLY")

    def test_png_palette_conforms(self):
        info=G.png_info((self.root/"assets"/"elder_whitebeard.png").read_bytes())
        self.assertLessEqual(info["colors"],64)
        self.assertTrue(info["alphaSupported"])


if __name__=="__main__":
    unittest.main()
