# coding: utf-8
"""Independent owner acceptance for trusted offline desktop orders engine."""
import csv,io,sqlite3,tempfile,unittest
from pathlib import Path
from autofab.desktop_orders_core import Orders,_csv_safe,user_database

class OrdersOwnerAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="af-owner-desktop-orders-")
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"orders.sqlite3"
        self.db=Orders(self.path)
        self.addCleanup(lambda: self.db.close())
    def test_create_read_update_delete(self):
        a=self.db.create("ORD-001","Cliente A",1250)
        self.assertIsInstance(a["id"],int)
        self.assertEqual(a["reference"],"ORD-001")
        self.assertEqual(a["status"],"pending")
        self.assertEqual(self.db.count(),1)
        b=self.db.update(a["id"],"ORD-001B","Cliente B",3000,"paid")
        self.assertEqual(b["customer"],"Cliente B")
        self.assertEqual(b["status"],"paid")
        self.assertEqual(self.db.get(a["id"])["amount_cents"],3000)
        self.assertTrue(self.db.delete(a["id"]))
        self.assertFalse(self.db.delete(a["id"]))
        self.assertIsNone(self.db.get(a["id"]))
    def test_durable_after_close_and_reopen(self):
        a=self.db.create("DURABLE-9","Cliente",700)
        self.db.close()
        self.db=Orders(self.path)
        self.assertEqual(self.db.get(a["id"])["amount_cents"],700)
        self.assertTrue(self.db.integrity())
    def test_duplicate_case_insensitive_rollback(self):
        self.db.create("CASE-A","Test",25)
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            self.db.create("case-a","Other",40)
        self.assertEqual(self.db.count(),1)
    def test_updates_are_parameterized(self):
        malicious="O'Reilly'); DROP TABLE orders;--"
        obj=self.db.create("SAFE-1",malicious,125)
        self.assertEqual(self.db.get(obj["id"])["customer"],malicious)
        rows=self.db.list("x OR 1=1 --")
        self.assertEqual(rows,[])
        self.assertEqual(self.db.count(),1)
    def test_query_like_escape_literal(self):
        self.db.create("REF-100","100% válido",400)
        self.db.create("REF_200","Zeta",200)
        self.assertEqual(len(self.db.list("%")),1)
        self.assertEqual(len(self.db.list("_")),1)
    def test_status_filters_and_search(self):
        self.db.create("REF-A","Juan",200,"pending")
        self.db.create("REF-B","Juana",500,"paid")
        self.db.create("REF-C","Luis",800,"cancelled")
        self.assertEqual(len(self.db.list("Jua")),2)
        self.assertEqual(len(self.db.list(status="paid")),1)
        self.assertEqual(len(self.db.list("Jua",status="paid")),1)
        self.assertEqual(len(self.db.list(status="pending")),1)
        self.assertEqual(len(self.db.list(status="cancelled")),1)
    def test_amount_bool_negative_overflow_bad(self):
        for amount in (-1,True,1000000000,12.3,"100",None):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.db.create("AMOUNT-X","Client",amount)
        self.assertEqual(self.db.count(),0)
    def test_invalid_reference_empty_or_unicode_bad(self):
        for ref in ("","/../","A B","ñ","a"*50,"'\n"):
            with self.subTest(ref=ref),self.assertRaises(ValueError):
                self.db.create(ref,"Test",100)
    def test_status_validation(self):
        for status in ("PAID","deleted","",None):
            with self.subTest(status=status),self.assertRaises(ValueError):
                self.db.create("VALID-REF","One",100,status)
    def test_search_injection_does_not_expose_all(self):
        self.db.create("SEARCH1","Name 1",10)
        self.db.create("SEARCH2","Name 2",20)
        self.assertEqual(self.db.list("x' OR 1=1 --"),[])
        self.assertEqual(self.db.count(),2)
    def test_prevent_boolean_id(self):
        with self.assertRaises(ValueError):
            self.db.get(True)
        with self.assertRaises(ValueError):
            self.db.delete(-1)
    def test_export_csv_complete(self):
        self.db.create("CSV-1","Cliente, Uno",100,"paid")
        self.db.create("CSV-2","Dos",200,"pending")
        data=self.db.export_csv()
        parsed=list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
        self.assertEqual(len(parsed),2)
        self.assertEqual(parsed[1]["customer"],"Cliente, Uno")
        self.assertEqual(parsed[1]["status"],"paid")
    def test_csv_formula_injection_neutralized(self):
        self.db.create("INJ-1","=HYPERLINK(1)",200)
        self.db.create("INJ-2","  +SUM(A1:A2)",400)
        data=self.db.export_csv().decode("utf-8-sig")
        parsed=list(csv.DictReader(io.StringIO(data)))
        self.assertEqual(parsed[0]["customer"],"'+SUM(A1:A2)")
        self.assertEqual(parsed[1]["customer"],"'=HYPERLINK(1)")
    def test_backup_is_atomic_verified_sqlite(self):
        self.db.create("BAK-1","Backup",450)
        dest=Path(self.tmp.name)/"saved.sqlite3"
        self.assertEqual(self.db.backup(dest),dest)
        with Orders(dest) as other:
            self.assertEqual(other.count(),1)
            self.assertTrue(other.integrity())
        with self.assertRaises(ValueError):
            self.db.backup(dest)
    def test_backup_with_WAL_updates(self):
        self.db.create("WAL-1","One",400)
        self.db.create("WAL-2","Two",500)
        dest=Path(self.tmp.name)/"walbackup.sqlite3"
        self.db.backup(dest)
        with Orders(dest) as cp:
            self.assertEqual(cp.count(),2)
        self.assertTrue(self.db.integrity())
    def test_close_requires_fail_closed(self):
        self.db.close()
        with self.assertRaises(RuntimeError):
            self.db.create("CLOSED","Closed",1)
    def test_parent_symlink_rejected(self):
        folder=Path(self.tmp.name)/"sym"
        try:folder.symlink_to(Path(self.tmp.name),target_is_directory=True)
        except (OSError,NotImplementedError):return
        with self.assertRaises(ValueError):
            Orders(folder/"sub.sqlite3")
    def test_path_must_be_sqlite(self):
        for val in ("orders.sqlite3",Path(self.tmp.name)/"x.json",b"str"):
            with self.assertRaises(ValueError):
                Orders(val)
    def test_export_with_filters(self):
        self.db.create("A111","a",150,"paid")
        self.db.create("B111","b",150,"cancelled")
        blob=self.db.export_csv(status="paid")
        rows=list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["reference"],"A111")
    def test_invalid_customer_controls(self):
        for name in ("","\nabc","x"*101):
            with self.assertRaises(ValueError):
                self.db.create("TEST-1",name,1)
    def test_reopen_concurrent_reads(self):
        self.db.create("MULTI","A",22)
        with Orders(self.path) as other:
            self.assertEqual(other.count(),1)
            other.update(1,"MULTI","B",33,"paid")
        self.assertEqual(self.db.get(1)["customer"],"B")

if __name__=="__main__":
    unittest.main()
