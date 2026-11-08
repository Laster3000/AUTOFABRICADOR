# coding: utf-8
"""AF R91 reusable navigation/art factory contract unit tests, no destructive effects."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(r"C:\AUTOFABRICADOR")
sys.path.insert(0,str(ROOT))
from autofab import adventure_navigation_r91 as nav
GAME=ROOT/"SHOWCASES"/"R91-AVENTURA-HD-NAV-169"
class TestR91NavigationFactory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=nav.load(GAME/"navigation_r91.json")
        cls.rooms={k:nav.nav_section(v) for k,v in cls.doc["scenes"].items()}
    def test_01_original_game_audit(self):
        self.assertEqual(nav.audit(GAME)["status"],"PASS_REUSABLE_WALKMESH_AND_HD_ART_CONTRACT")
    def test_02_all_three_rooms(self):
        self.assertEqual(set(self.rooms),{"harbor","workshop","old_observatory"})
    def test_03_native_16_by_9(self):
        self.assertEqual(nav.NATIVE,(640,360))
        self.assertEqual(nav.PRESENTATION,(1280,720))
    def test_04_spawns_safe(self):
        for x in self.rooms.values():self.assertTrue(nav.permitted(x,x["start"]))
    def test_05_water_is_forbidden(self):
        self.assertFalse(nav.permitted(self.rooms["harbor"],(150,52)))
    def test_06_screen_edges_are_forbidden(self):
        for p in ((0,124),(320,118),(147,180),(100,-5)):
            self.assertFalse(nav.permitted(self.rooms["harbor"],p))
    def test_07_no_teleport_into_elder(self):
        for p in ((168,118),(162,119),(175,120)):
            self.assertFalse(nav.permitted(self.rooms["harbor"],p))
    def test_08_nearest_projects_invalid_points(self):
        for scene in self.rooms.values():
            for q in ((-100,-100),(900,900),(165,0),(319,179)):
                self.assertTrue(nav.permitted(scene,nav.nearest(scene,q)))
    def test_09_all_hotspots_reachable(self):
        for name,section in self.rooms.items():
            visited=nav.bfs_reachable(section)
            for item in nav.load(GAME/"game_data.json")["scenes"][name]["hotspots"]:
                p=nav.point(item["walkTo"])
                self.assertTrue(nav.permitted(section,p),item["id"])
                cell=(round(p[0]/2)*2,round(p[1]/2)*2)
                self.assertIn(cell,visited,item["id"])
    def test_10_reusable_compiler(self):
        generated=nav.build_contract([
            GAME/"scene-harbor.json",GAME/"scene-workshop.json",GAME/"scene-observatory.json"])
        self.assertEqual(set(generated["scenes"]),set(self.rooms))
        self.assertTrue(generated["pixelScale"]==2)
    def test_11_no_symlink_path_escape(self):
        with self.assertRaises(nav.NavContractError):
            nav.safe_path(GAME,"../../Windows/system.ini")
    def test_12_forbid_short_polygons(self):
        with self.assertRaises(nav.NavContractError):nav.polygon([[5,5],[12,12]])
    def test_13_reject_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.json";p.write_text('{"x":1,"x":2}')
            with self.assertRaises(nav.NavContractError):nav.load(p)
    def test_14_reject_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.json";p.write_text('{"x":NaN}')
            with self.assertRaises(nav.NavContractError):nav.load(p)
    def test_15_reject_degenerate_polygon(self):
        with self.assertRaises(nav.NavContractError):
            nav.polygon([[3,3],[6,6],[9,9]])
    def test_16_png_dimensions_hd(self):
        self.assertEqual(nav.image_dimensions(GAME/"assets/harbor_back.png"),(640,260))
    def test_17_character_14_frames(self):
        self.assertEqual(nav.image_dimensions(GAME/"assets/young_sailor.png"),(672,96))
    def test_18_ora_semantic_layers(self):
        w,h,count=nav.source_layers(GAME/"source/young_sailor.ora")
        self.assertEqual((w,h),(672,96))
        self.assertGreaterEqual(count,6)
    def test_19_ora_recovers_scene(self):
        self.assertEqual(nav.source_layers(GAME/"source/harbor_back.ora")[:2],(640,260))
    def test_20_navigation_not_empty(self):
        self.assertGreater(len(nav.bfs_reachable(self.rooms["harbor"])),100)
    def test_21_shadow_and_footprint_clearance(self):
        for x in (14,145,306):
            p=nav.nearest(self.rooms["harbor"],(x,116))
            self.assertTrue(p[0]-12>=0 and p[0]+12<=320)
    def test_22_adversarial_blocked_route(self):
        self.assertFalse(nav.permitted(self.rooms["harbor"],(168,120)))
    def test_23_no_touch_offline_original(self):
        self.assertNotEqual(nav.sha(GAME/"assets/harbor_back.png"),
                            nav.sha(GAME/"art/base_r90/assets/harbor_back.png"))
    def test_24_narrative_provenance_present(self):
        self.assertEqual(nav.load(GAME/"game_data.json")["AIOriginalNarrative"]["sceneId"],
                         "old_observatory")
if __name__=="__main__":
    unittest.main(verbosity=2)
