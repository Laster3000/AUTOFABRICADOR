# coding: utf-8
"""AUTOFABRICADOR R87: independent, read-only VGA scene/art/UX contract validator.

This is an engineering gate, not an aesthetic judge, editor or separate factory.
It never runs model code and never auto-approves artistic quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

VERSION = "AF.R87.ADVENTURE-VISUAL.1"
PNG = b"\x89PNG\r\n\x1a\n"
MAX_FILE = 8 * 1024 * 1024
MAX_PIXELS = 1_000_000
MAX_SOURCE = 16 * 1024 * 1024
IDS = re.compile(r"[a-z][a-z0-9_-]{2,62}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
ANIMATIONS = {"idle", "walk", "talk", "look", "pick", "use", "react"}
VERBS = {"WALK", "LOOK", "TAKE", "USE", "TALK", "OPEN", "CLOSE", "PUSH", "PULL", "GIVE"}


class ContractError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes):
    def obj(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ContractError("DUPLICATE_JSON_KEY:" + str(k))
            out[k] = v
        return out

    def nonfinite(v):
        raise ContractError("NONFINITE_JSON_VALUE:" + v)
    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=obj, parse_constant=nonfinite)


def check(cond, reason):
    if not cond:
        raise ContractError(reason)


def regular_path(root: Path, name: str, *, prefix: str, expected: str):
    check(type(name) is str and len(name) <= 160 and "\\" not in name, "ASSET_PATH_INVALID")
    pure = PurePosixPath(name)
    check(not pure.is_absolute() and ".." not in pure.parts and len(pure.parts) >= 2
          and pure.parts[0] == prefix, "ASSET_PATH_ESCAPE")
    check(pure.suffix.lower() == expected, "ASSET_EXTENSION_INVALID")
    path = root.joinpath(*pure.parts)
    check(path.is_file() and not path.is_symlink() and
          path.resolve().is_relative_to(root.resolve()), "ASSET_MISSING_OR_REPARSE_DENIED")
    check(0 < path.stat().st_size <= (MAX_SOURCE if prefix == "source" else MAX_FILE),
          "ASSET_BYTES_LIMIT")
    return path


def png_info(data: bytes):
    check(len(data) >= 45 and data[:8] == PNG, "PNG_HEADER_BAD")
    pos = 8
    ihdr = None
    palette = None
    transparency = None
    blocks = []
    seen = []
    while pos + 12 <= len(data):
        n = struct.unpack_from(">I", data, pos)[0]
        tag = data[pos + 4:pos + 8]
        check(n <= MAX_FILE and pos + n + 12 <= len(data), "PNG_CHUNK_LENGTH_BAD")
        chunk = data[pos + 8:pos + 8 + n]
        crc = struct.unpack_from(">I", data, pos + 8 + n)[0]
        check(zlib.crc32(tag + chunk) & 0xffffffff == crc, "PNG_CRC_BAD")
        if tag == b"IHDR":
            check(ihdr is None and pos == 8 and len(chunk) == 13, "PNG_IHDR_BAD")
            w, h, depth, kind, comp, filt, inter = struct.unpack(">IIBBBBB", chunk)
            check(1 <= w <= 4096 and 1 <= h <= 4096 and w*h <= MAX_PIXELS,
                  "PNG_DIMENSIONS_BAD")
            check(depth == 8 and kind in (2, 3, 6) and
                  comp == 0 and filt == 0 and inter == 0, "PNG_FORMAT_NOT_PINNED")
            ihdr = (w, h, kind)
        elif tag == b"PLTE":
            check(ihdr is not None and palette is None and len(chunk) % 3 == 0
                  and 3 <= len(chunk) <= 768, "PNG_PALETTE_BAD")
            palette = [tuple(chunk[i:i + 3]) for i in range(0, len(chunk), 3)]
        elif tag == b"tRNS":
            check(ihdr is not None and transparency is None, "PNG_TRNS_BAD")
            transparency = chunk
        elif tag == b"IDAT":
            check(ihdr is not None, "PNG_IDAT_BEFORE_IHDR")
            blocks.append(chunk)
        elif tag == b"IEND":
            check(ihdr is not None and n == 0 and pos + 12 == len(data),
                  "PNG_TRAILING_OR_IEND_BAD")
            break
        elif tag[:1].isupper():
            raise ContractError("PNG_UNKNOWN_CRITICAL_CHUNK")
        seen.append(tag)
        pos += n + 12
    else:
        raise ContractError("PNG_IEND_MISSING")
    w, h, kind = ihdr
    check(blocks and (kind != 3 or palette is not None), "PNG_PALETTE_OR_DATA_MISSING")
    check(transparency is None or (kind == 3 and len(transparency) <= len(palette)),
          "PNG_ALPHA_ENCODING_UNSUPPORTED")
    bpp = {2:3, 3:1, 6:4}[kind]
    stride = w * bpp
    expected = h * (stride + 1)
    # Bounded inflate prevents decompression bombs, oversize trailing data.
    decoder = zlib.decompressobj()
    raw = decoder.decompress(b"".join(blocks), expected + 1)
    check(len(raw) == expected and not decoder.unconsumed_tail and decoder.eof and
          not decoder.unused_data, "PNG_DEFLATE_LENGTH_OR_TAIL")
    previous = bytearray(stride)
    unique = set()
    opaque = 0
    colored = 0
    bounds = [w, h, -1, -1]
    for y in range(h):
        row = raw[y * (stride + 1): (y + 1) * (stride + 1)]
        filt = row[0]
        check(filt in (0, 1, 2, 3, 4), "PNG_FILTER_BAD")
        current = bytearray(row[1:])
        for i in range(stride):
            left = current[i-bpp] if i >= bpp else 0
            above = previous[i]
            upper_left = previous[i-bpp] if i >= bpp else 0
            if filt == 1: predictor = left
            elif filt == 2: predictor = above
            elif filt == 3: predictor = (left + above)//2
            elif filt == 4:
                p = left + above - upper_left
                da, db, dc = abs(p-left), abs(p-above), abs(p-upper_left)
                predictor = left if da <= db and da <= dc else above if db <= dc else upper_left
            else: predictor = 0
            current[i] = (current[i] + predictor) & 255
        for x in range(w):
            start = x*bpp
            if kind == 2:
                color = tuple(current[start:start+3])
                a = 255
            elif kind == 6:
                color = tuple(current[start:start+3])
                a = current[start+3]
            else:
                index = current[start]
                check(index < len(palette), "PNG_PALETTE_INDEX_BAD")
                color = palette[index]
                a = transparency[index] if transparency is not None and index < len(transparency) else 255
            if a:
                colored += 1
                unique.add(color)
                bounds[0] = min(bounds[0], x)
                bounds[1] = min(bounds[1], y)
                bounds[2] = max(bounds[2], x)
                bounds[3] = max(bounds[3], y)
                if a == 255: opaque += 1
        previous = current
    return {"width":w,"height":h,"colorType":kind,"colors":len(unique),
            "visiblePixels":colored,"fullyOpaquePixels":opaque,
            "bounds":bounds if colored else None, "alphaSupported":kind != 2}


def source_info(blob: bytes, expected_width: int, expected_height: int):
    # Only OpenRaster is actually validated as an editable layered master.
    # Other editor formats require a future per-format parser before acceptance.
    import io
    check(len(blob) < MAX_SOURCE and zipfile.is_zipfile(io.BytesIO(blob)),
          "MASTER_NOT_OPENRASTER")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)) and len(names) <= 64
              and len(names) >= 4, "MASTER_ZIP_ENTRIES_INVALID")
        for member in archive.infolist():
            check(not member.is_dir() and not member.filename.startswith("/")
                  and "\\" not in member.filename
                  and ".." not in PurePosixPath(member.filename).parts
                  and member.file_size <= MAX_FILE, "MASTER_ZIP_PATH_OR_SIZE_BAD")
        check("mimetype" in names and "stack.xml" in names and
              "mergedimage.png" in names, "MASTER_OPENRASTER_STRUCTURE_BAD")
        check(archive.read("mimetype") == b"image/openraster", "MASTER_MIMETYPE_BAD")
        xml = ElementTree.fromstring(archive.read("stack.xml"))
        check(xml.tag == "image" and xml.get("w") == str(expected_width)
              and xml.get("h") == str(expected_height), "MASTER_CANVAS_MISMATCH")
        layers = [a.get("src") for a in xml.iter("layer")]
        check(bool(layers) and all(name in names and name.startswith("data/") for name in layers),
              "MASTER_LAYERS_MISSING")
        master_png = png_info(archive.read("mergedimage.png"))
        check(master_png["width"] == expected_width and
              master_png["height"] == expected_height, "MASTER_MERGED_DIMENSIONS_MISMATCH")
        for layer in layers:
            layer_img = png_info(archive.read(layer))
            check(layer_img["width"] <= expected_width and
                  layer_img["height"] <= expected_height, "MASTER_LAYER_SIZE_BAD")
        return {"format":"OPENRASTER","editableLayers":len(layers),
                "masterPixelsValidated":True}


def inside(poly, x, y):
    hit = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ax, ay = a
        bx, by = b
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay) + ax:
            hit = not hit
    return hit


def polygon(points, width, height):
    check(type(points) is list and 3 <= len(points) <= 32, "POLYGON_POINTS_BAD")
    for point in points:
        check(type(point) is list and len(point) == 2 and
              all(type(v) is int for v in point) and
              0 <= point[0] < width and 0 <= point[1] < height,
              "POLYGON_VERTEX_OUTSIDE")
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
    check(abs(area) >= 24, "POLYGON_TOO_SMALL")
    return points


def audit(manifest: Path):
    errors = []
    assets = {}
    try:
        file = Path(manifest).resolve()
        root = file.parent
        check(file.is_file() and not file.is_symlink()
              and file.stat().st_size <= 150_000, "MANIFEST_NOT_REGULAR")
        raw = file.read_bytes()
        doc = strict_json(raw)
        check(type(doc) is dict and set(doc) == {
            "schema","profile","assets","characters","scene","ui"}, "MANIFEST_SCHEMA_KEYS")
        check(doc["schema"] == 1, "MANIFEST_SCHEMA_VERSION")
        profile = doc["profile"]
        check(type(profile) is dict and profile == {
            "canvas":[320,200],"aspect":"4:3","sceneHeight":140,
            "sampling":"nearest","startMode":"manual","pixelArt":True}, "VGA_PROFILE_MISMATCH")
        asset_defs = doc["assets"]
        check(type(asset_defs) is list and 2 <= len(asset_defs) <= 80, "ASSET_COUNT_BAD")
        for item in asset_defs:
            try:
                check(type(item) is dict and set(item) == {
                    "id","kind","png","pngSHA256","master","masterSHA256","frame"}, "ASSET_FIELDS_BAD")
                key = item["id"]
                check(type(key) is str and IDS.fullmatch(key) is not None
                      and key not in assets, "ASSET_ID_BAD_OR_DUPLICATE")
                check(item["kind"] in ("background","foreground","character","object","ui"),
                      "ASSET_KIND_UNKNOWN")
                for label in ("pngSHA256","masterSHA256"):
                    check(type(item[label]) is str and SHA.fullmatch(item[label]) is not None,
                          "ASSET_SHA_UNPINNED")
                png = regular_path(root,item["png"],prefix="assets",expected=".png")
                master = regular_path(root,item["master"],prefix="source",expected=".ora")
                check(sha(png.read_bytes()) == item["pngSHA256"], "ASSET_PNG_SHA_DRIFT")
                check(sha(master.read_bytes()) == item["masterSHA256"], "ASSET_MASTER_SHA_DRIFT")
                dimensions = png_info(png.read_bytes())
                check(dimensions["colors"] <= 256, "ASSET_OVER_256_COLORS")
                frame = item["frame"]
                if item["kind"] in ("background","ui","foreground"):
                    check(frame is None, "NONSPRITE_HAS_FRAME_GRID")
                    expected = (320, 140 if item["kind"] != "ui" else 60)
                    check((dimensions["width"],dimensions["height"]) == expected,
                          "SCENE_LAYER_DIMENSIONS")
                else:
                    check(type(frame) is dict and set(frame) == {"width","height","count"},
                          "SPRITE_FRAME_FIELDS")
                    check(all(type(frame[k]) is int for k in frame)
                          and 8 <= frame["width"] <= 128
                          and 8 <= frame["height"] <= 140
                          and 1 <= frame["count"] <= 96, "SPRITE_FRAME_SIZE_BAD")
                    check(dimensions["width"] == frame["width"] * frame["count"]
                          and dimensions["height"] == frame["height"], "SPRITE_GRID_BAD")
                    check(dimensions["alphaSupported"] and
                          dimensions["visiblePixels"] < dimensions["width"]*dimensions["height"],
                          "SPRITE_TRANSPARENCY_REQUIRED")
                    check(dimensions["colors"] <= 64, "SPRITE_PALETTE_TOO_LARGE")
                source = source_info(master.read_bytes(),dimensions["width"],dimensions["height"])
                assets[key] = {"kind":item["kind"],"png":dimensions,
                               "master":source,"pngSHA256":item["pngSHA256"],
                               "masterSHA256":item["masterSHA256"]}
            except (ContractError,ValueError,KeyError,TypeError,zipfile.BadZipFile,
                    ElementTree.ParseError,zlib.error) as exc:
                errors.append("ASSET:" + str(item.get("id","UNKNOWN") if isinstance(item,dict) else "UNKNOWN")
                              + ":" + str(exc))
        chars = doc["characters"]
        check(type(chars) is list and chars and len(chars) <= 20, "CHARACTER_COUNT_BAD")
        seen = set()
        for c in chars:
            check(type(c) is dict and set(c) == {
                "id","asset","pivot","baselineY","animations"}, "CHARACTER_SCHEMA")
            check(type(c["id"]) is str and IDS.fullmatch(c["id"]) is not None and
                  c["id"] not in seen, "CHARACTER_ID_DUPLICATE")
            seen.add(c["id"])
            check(c["asset"] in assets and assets[c["asset"]]["kind"] == "character",
                  "CHARACTER_ASSET_MISSING")
            f = next(x["frame"] for x in asset_defs if x["id"] == c["asset"])
            check(type(c["pivot"]) is list and len(c["pivot"]) == 2 and
                  all(type(x) is int for x in c["pivot"]) and
                  0 <= c["pivot"][0] < f["width"] and
                  0 <= c["pivot"][1] <= f["height"], "CHARACTER_PIVOT_INVALID")
            check(type(c["baselineY"]) is int and 0 <= c["baselineY"] < 140,
                  "CHARACTER_BASELINE_INVALID")
            anim = c["animations"]
            check(type(anim) is dict and ANIMATIONS.issubset(anim), "CHARACTER_ANIMATION_REQUIRED")
            for action, frames in anim.items():
                check(action in ANIMATIONS and type(frames) is list and frames
                      and len(frames) <= 48 and
                      all(type(n) is int and 0 <= n < f["count"] for n in frames),
                      "CHARACTER_ANIMATION_FRAME_BAD")
        scene = doc["scene"]
        check(type(scene) is dict and set(scene) == {
            "id","background","walkable","playerStart","hotspots"}, "SCENE_FIELDS")
        check(type(scene["id"]) is str and IDS.fullmatch(scene["id"]) is not None,
              "SCENE_ID_BAD")
        check(scene["background"] in assets and assets[scene["background"]]["kind"] == "background",
              "SCENE_BACKGROUND_MISSING")
        zone = polygon(scene["walkable"],320,140)
        check(type(scene["playerStart"]) is list and len(scene["playerStart"]) == 2 and
              inside(zone,*scene["playerStart"]), "PLAYER_START_NOT_WALKABLE")
        spots = scene["hotspots"]
        check(type(spots) is list and 3 <= len(spots) <= 64, "HOTSPOT_COUNT_BAD")
        ids=set()
        for item in spots:
            check(type(item) is dict and set(item) == {
                "id","name","polygon","walkTo","verbs","feedback"}, "HOTSPOT_FIELDS")
            check(type(item["id"]) is str and IDS.fullmatch(item["id"]) is not None and
                  item["id"] not in ids, "HOTSPOT_ID_DUPLICATE")
            ids.add(item["id"])
            polygon(item["polygon"],320,140)
            check(type(item["walkTo"]) is list and len(item["walkTo"]) == 2 and
                  inside(zone,*item["walkTo"]), "HOTSPOT_WALKTO_NOT_REACHABLE")
            check(type(item["verbs"]) is list and item["verbs"] and
                  all(x in VERBS for x in item["verbs"]), "HOTSPOT_VERBS_INVALID")
            check(type(item["name"]) is str and item["name"].strip(), "HOTSPOT_NAME_MISSING")
            check(type(item["feedback"]) is str and item["feedback"].strip(),
                  "HOTSPOT_FEEDBACK_REQUIRED")
        ui = doc["ui"]
        check(type(ui) is dict and set(ui) == {
            "asset","verbs","inventorySlots","minTargetPx","fontPx"}, "UI_FIELDS")
        check(ui["asset"] in assets and assets[ui["asset"]]["kind"] == "ui", "UI_IMAGE_REQUIRED")
        check(type(ui["verbs"]) is list and {"WALK","LOOK","TAKE","USE","TALK"}.issubset(ui["verbs"])
              and all(x in VERBS for x in ui["verbs"]), "UI_VERBS_INCOMPLETE")
        check(type(ui["inventorySlots"]) is int and ui["inventorySlots"] >= 4 and
              type(ui["minTargetPx"]) is int and ui["minTargetPx"] >= 10 and
              type(ui["fontPx"]) is int and ui["fontPx"] >= 6, "UI_HIT_TARGET_TOO_SMALL")
    except (ContractError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError) as exc:
        errors.append("CONTRACT:" + str(exc))
    return {
        "schema":1,"version":VERSION,
        "status":"BLOCKED_TECHNICAL_VISUAL_CONTRACT" if errors else
                 "PASS_TECHNICAL_VISUAL_REVIEW_REQUIRED",
        "technicalPass":not errors,
        "artisticQualityAccepted":False,
        "requiresHumanVisualReview":True,
        "fullGameAccepted":False,
        "modelGeneratedTestsCount":0,
        "assetCountVerified":len(assets),
        "assets":assets,
        "errors":errors,
        "manifestSHA256":sha(Path(manifest).read_bytes()) if Path(manifest).is_file() else None,
        "sourceExecution":"NONE_READ_ONLY"
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="R87 read-only independent art/UX gate")
    p.add_argument("manifest",type=Path,help="Visual scene manifest with frozen image/master SHA")
    a = p.parse_args(argv)
    result=audit(a.manifest)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if result["technicalPass"] else 2


if __name__ == "__main__":
    sys.exit(main())
