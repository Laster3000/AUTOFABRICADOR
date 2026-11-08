# coding: utf-8
"""Independent first-party original portfolio contracts and SQLite acceptance."""
import csv,io,os,tempfile,unittest
from pathlib import Path
from autofab import portfolio_core,portfolio_specs

class PortfolioOwnerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="af-r63-owner-tests-")
  self.addCleanup(self.tmp.cleanup)
  self.home=Path(self.tmp.name)
 def db(self,profile):
  return portfolio_core.Portfolio(profile,self.home/(profile+".sqlite3"))
 def test_domains_distinct_schemas(self):
  p=portfolio_specs.PROFILES
  self.assertEqual(set(p),{"inventory","tasks","expenses"})
  self.assertEqual(len({tuple(x["fields"]) for x in p.values()}),3)
  self.assertNotEqual(p["inventory"]["extra"],p["tasks"]["extra"])
 def test_inventory_metrics(self):
  with self.db("inventory") as db:
   for row in portfolio_specs.PROFILES["inventory"]["sample"]:db.create(row)
   self.assertEqual(db.metrics()["totalCents"],19700)
   self.assertEqual(db.metrics()["lowStock"],1)
 def test_tasks_deadline_and_completion(self):
  with self.db("tasks") as db:
   for row in portfolio_specs.PROFILES["tasks"]["sample"]:db.create(row)
   self.assertEqual(db.metrics()["overdueOpen"],1)
   self.assertEqual(db.metrics()["completed"],1)
 def test_expenses_month_and_categories(self):
  with self.db("expenses") as db:
   for row in portfolio_specs.PROFILES["expenses"]["sample"]:db.create(row)
   self.assertEqual(db.metrics()["monthlyTotals"]["2026-11"],9950)
   self.assertEqual(db.metrics()["categoryTotals"],{"office":1250,"travel":8700})
 def test_create_update_delete_unique(self):
  for profile,spec in portfolio_specs.PROFILES.items():
   with self.subTest(profile=profile),self.db(profile) as db:
    a=db.create(spec["sample"][0])
    self.assertEqual(db.count(),1)
    self.assertEqual(db.get(a["id"])[spec["fields"][0][0]],spec["sample"][0][spec["fields"][0][0]])
    with self.assertRaises(ValueError):db.create(spec["sample"][0])
    update=dict(spec["sample"][1])
    new=db.update(a["id"],update)
    self.assertEqual(new[spec["fields"][0][0]],update[spec["fields"][0][0]])
    self.assertTrue(db.delete(a["id"]))
    self.assertFalse(db.delete(a["id"]))
 def test_wrong_fields_rejected(self):
  with self.db("inventory") as db:
   invalid={"sku":"X","name":"N","quantity":1,"minimum":1}
   with self.assertRaises(ValueError):db.create(invalid)
 def test_bool_subclass_not_integer(self):
  for profile,spec in portfolio_specs.PROFILES.items():
   names=[n for n,t in spec["fields"] if t in ("positive","nonnegative","bool")]
   with self.subTest(profile=profile),self.db(profile) as db:
    for name in names:
     b=dict(spec["sample"][0]);b[name]=True
     with self.assertRaises(ValueError):db.create(b)
 def test_invalid_date(self):
  for profile in ("tasks","expenses"):
   spec=portfolio_specs.PROFILES[profile]
   name=next(n for n,k in spec["fields"] if k=="date")
   with self.subTest(profile=profile),self.db(profile) as db:
    value=dict(spec["sample"][0]);value[name]="2026-02-30"
    with self.assertRaises(ValueError):db.create(value)
 def test_sql_injection_is_just_text(self):
  spec=portfolio_specs.PROFILES["expenses"]
  with self.db("expenses") as db:
   row=dict(spec["sample"][0]);row["merchant"]="O'Reilly'); DROP TABLE records;--"
   db.create(row)
   self.assertEqual(db.count(),1)
   self.assertTrue(db.integrity())
   self.assertEqual(db.list("xyz' OR 1=1 --"),[])
 def test_search_wildcard_literal(self):
  with self.db("inventory") as db:
   db.create({"sku":"PCT-1","name":"50% Desc.","quantity":2,"minimum":1,"unit_cents":100})
   db.create({"sku":"BAR-1","name":"Other","quantity":2,"minimum":1,"unit_cents":100})
   self.assertEqual(len(db.list("%")),1)
   self.assertEqual(len(db.list("_")),0)
 def test_csv_bom_and_fields(self):
  for profile,spec in portfolio_specs.PROFILES.items():
   with self.subTest(profile=profile),self.db(profile) as db:
    db.create(spec["sample"][0])
    raw=db.export_csv()
    self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
    parsed=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    self.assertEqual(len(parsed),1)
    self.assertEqual(set(n for n,t in spec["fields"])<=set(parsed[0]),True)
 def test_csv_formula_guard(self):
  with self.db("inventory") as db:
   db.create({"sku":"SAN-01","name":"=1+1","quantity":2,"minimum":1,"unit_cents":100})
   text=db.export_csv().decode("utf-8-sig")
   self.assertIn("'=1+1",text)
 def test_reopen_is_durable(self):
  spec=portfolio_specs.PROFILES["tasks"]
  with self.db("tasks") as db:db.create(spec["sample"][0])
  with self.db("tasks") as db:
   self.assertEqual(db.count(),1)
   self.assertTrue(db.integrity())
 def test_backup_is_valid(self):
  with self.db("expenses") as db:
   db.create(portfolio_specs.PROFILES["expenses"]["sample"][0])
   target=self.home/"copied.sqlite3"
   db.backup(target)
   with portfolio_core.Portfolio("expenses",target) as b:
    self.assertEqual(b.count(),1)
    self.assertTrue(b.integrity())
 def test_unknown_profile_fails_closed(self):
  with self.assertRaises(ValueError):
   portfolio_core.Portfolio("alien",self.home/"unknown.sqlite3")
 def test_bad_boolean_and_limit(self):
  with self.db("tasks") as db:
   for value in (True,0,-1,2**80):
    with self.assertRaises(ValueError):db.get(value)
   for value in (True,-1,100000):
    with self.assertRaises(ValueError):db.list(limit=value)
 def test_out_of_scope_goals_rejected(self):
  for request in (
    "Programa el sistema operativo Windows completo con internet.",
    "Quiero una aplicación de inventario y tareas y gastos a la vez con interfaz de escritorio local sqlite csv.",
    "Desarrolla inventario con interfaz de escritorio local sqlite csv y OAuth en la nube.",
   ):
   self.assertEqual(portfolio_specs.scope(request)["status"],
     "BLOCKED_INDEPENDENT_OWNER_UNSUPPORTED_OR_AMBIGUOUS")
 def test_independent_natural_language_scopes(self):
  examples=(
    ("inventory","Crea una interfaz de escritorio local para inventario y control de stock con sqlite y csv, gestionando SKU, cantidad, mínimo y valoración."),
    ("tasks","Desarrolla una interfaz de escritorio local para tareas y agenda con sqlite y csv, prioridades y fechas de entrega."),
    ("expenses","Construye una interfaz de escritorio local de gastos y categorías con sqlite y csv, fechas, comerciantes, acumulados mensuales."),
   )
  for expected,goal in examples:
   with self.subTest(expected=expected):
    self.assertEqual(portfolio_specs.scope(goal)["profile"],expected)
 def test_original_three_inputs_distinct(self):
  paths=(
   "af_r63_inventario_stock_local.txt","af_r63_gestor_tareas_agenda.txt",
   "af_r63_gastos_categorias_mensuales.txt")
  root=Path(__file__).resolve().parent.parent
  seen=set()
  for filename in paths:
   item=portfolio_specs.from_file(root,root/"ENTRADAS"/filename)
   self.assertEqual(item["scope"]["status"],"PASS_FROZEN_INDEPENDENT_FIRST_PARTY_SCOPE")
   seen.add(item["scope"]["profile"])
  self.assertEqual(seen,set(portfolio_specs.PROFILES))
if __name__=="__main__":unittest.main()
