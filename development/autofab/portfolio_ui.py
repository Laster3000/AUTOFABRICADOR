# coding: utf-8
"""First-party reusable offline local desktop interface for three app domains."""
from __future__ import annotations
import sys
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from pathlib import Path
if __package__:
 from .portfolio_specs import PROFILES
 from .portfolio_core import Portfolio,user_database
else:
 from portfolio_specs import PROFILES
 from portfolio_core import Portfolio,user_database

def create_window(db,*,exit_when_ready=False):
 p=PROFILES[db.profile]
 app=tk.Tk()
 app.title("AUTOFABRICADOR · "+p["title"])
 app.minsize(780,530)
 app.geometry("1090x720")
 selected=[None]
 message=tk.StringVar(value="Sin conexión a servicios externos. Los datos quedan en SQLite local.")
 search=tk.StringVar()
 form={name:tk.StringVar(value="") for name,kind in p["fields"]}
 widget_by_field={}
 root=ttk.Frame(app,padding=14)
 root.pack(fill="both",expand=True)
 ttk.Label(root,text=p["title"],font=("Segoe UI",18,"bold")).pack(anchor="w")
 ttk.Label(root,text="Aplicación local: registrar, modificar, eliminar, buscar y exportar CSV.",
           wraplength=990).pack(anchor="w",pady=(2,10))
 search_area=ttk.Frame(root)
 search_area.pack(fill="x")
 ttk.Label(search_area,text="Buscar").pack(side="left",padx=(0,8))
 ttk.Entry(search_area,textvariable=search,width=40).pack(side="left",padx=(0,8))
 table=ttk.Treeview(root,show="headings",selectmode="browse",
       columns=("id",)+tuple(name for name,kind in p["fields"]),height=10)
 names=("id",)+tuple(name for name,kind in p["fields"])
 for name in names:
  table.heading(name,text=name.replace("_"," ").title())
  table.column(name,width=110 if name!="id" else 45,stretch=True)
 table.pack(fill="both",expand=True,pady=10)
 area=ttk.LabelFrame(root,text="Editar registro",padding=8)
 area.pack(fill="x")
 for col in range(4):
  area.columnconfigure(col,weight=1 if col%2==1 else 0)
 for ix,(name,kind) in enumerate(p["fields"]):
  row=ix//2
  col=(ix%2)*2
  ttk.Label(area,text=name.replace("_"," ").title()).grid(
      row=row,column=col,sticky="w",padx=4,pady=5)
  if kind=="priority": 
   control=ttk.Combobox(area,textvariable=form[name],values=("low","medium","high"),state="readonly")
   form[name].set("medium")
  elif kind=="category":
   control=ttk.Combobox(area,textvariable=form[name],values=("office","travel","other"),state="readonly")
   form[name].set("other")
  elif kind=="bool":
   control=ttk.Combobox(area,textvariable=form[name],values=("0","1"),state="readonly")
   form[name].set("0")
  else:control=ttk.Entry(area,textvariable=form[name])
  control.grid(row=row,column=col+1,sticky="ew",padx=(4,14),pady=5)
  widget_by_field[name]=control
 actions=ttk.Frame(root)
 actions.pack(fill="x",pady=9)
 def refresh():
  try:
   rows=db.list(search.get())
   for item in table.get_children():table.delete(item)
   for row in rows:
    table.insert("","end",iid=str(row["id"]),values=[row[n] for n in names])
   stats=db.metrics()
   message.set(f"Registros: {stats['records']}. Resumen: "+", ".join(
       f"{k}={v}" for k,v in stats.items() if k!="records"))
  except Exception as exc:messagebox.showerror("Consulta local",str(exc),parent=app)
 def clear():
  selected[0]=None
  for name,kind in p["fields"]:
   form[name].set(
    "0" if kind in ("nonnegative","bool") else
    "1" if kind=="positive" else
    "medium" if kind=="priority" else
    "other" if kind=="category" else
    "2026-11-08" if kind=="date" else "")
  table.selection_remove(*table.selection())
 def fill(_event=None):
  ids=table.selection()
  if not ids:return
  row=db.get(int(ids[0]))
  if row is None:return
  selected[0]=row["id"]
  for name,_kind in p["fields"]:form[name].set(str(row[name]))
 def collect():
  result={}
  for name,kind in p["fields"]:
   value=form[name].get()
   if kind in ("nonnegative","positive","bool"):
    if not value.isascii() or not value.isdigit():
     raise ValueError(f"Valor entero positivo obligatorio: {name}")
    result[name]=int(value)
   else:result[name]=value
  return result
 def save():
  try:
   data=collect()
   if selected[0] is None:db.create(data)
   else:db.update(selected[0],data)
   clear();refresh()
  except Exception as exc:messagebox.showerror("Validación",str(exc),parent=app)
 def delete():
  if selected[0] is None:return
  if not messagebox.askyesno("Eliminar","¿Eliminar este registro? No se puede deshacer.",parent=app):
   return
  db.delete(selected[0]);clear();refresh()
 def export():
  filename=filedialog.asksaveasfilename(parent=app,title="Exportar CSV",
   defaultextension=".csv",filetypes=[("CSV","*.csv")])
  if not filename:return
  try:
   pth=Path(filename)
   if pth.suffix.lower()!=".csv":raise ValueError("Se requiere un CSV")
   if pth.exists() and not messagebox.askyesno("Sobrescribir","¿Sobrescribir CSV existente?",parent=app):
    return
   pth.write_bytes(db.export_csv(search.get()))
   message.set("Exportado CSV local: "+str(pth))
  except Exception as exc:messagebox.showerror("CSV",str(exc),parent=app)
 for label,cb in (("Nuevo",clear),("Guardar",save),("Eliminar",delete),
                  ("Actualizar",refresh),("Exportar CSV",export)):
  ttk.Button(actions,text=label,command=cb).pack(side="left",padx=(0,8))
 ttk.Label(root,textvariable=message,wraplength=990).pack(anchor="w")
 table.bind("<<TreeviewSelect>>",fill)
 search.trace_add("write",lambda *_:refresh())
 clear();refresh()
 if exit_when_ready:app.after(300,app.quit)
 return app,{"table":table,"form":form,"widgets":widget_by_field,
             "actions":{b.cget("text"):b for b in actions.winfo_children() if isinstance(b,ttk.Button)},
             "search":search,"selected":selected}

def main(args=None):
 import argparse
 cli=argparse.ArgumentParser()
 cli.add_argument("--profile",required=True,choices=sorted(PROFILES))
 cli.add_argument("--app-id",required=True)
 cli.add_argument("--smoke",action="store_true")
 opts=cli.parse_args(args)
 with Portfolio(opts.profile,user_database(opts.app_id)) as db:
  app,controls=create_window(db,exit_when_ready=opts.smoke)
  try:app.mainloop()
  finally:
   try:app.destroy()
   except tk.TclError:pass
 return 0
if __name__=="__main__":sys.exit(main())
