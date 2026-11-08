# coding: utf-8
"""Trusted Tkinter desktop interface for original bounded local orders agent.

No model-generated Python/JS executed on Host. All data persists in local
user-scoped SQLite. An explicit CSV destination is chosen by the user; no
automatic exfiltration, browser/cloud access or shell commands.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# Installed distribution copies BOTH modules under same directory.
from desktop_orders_core import Orders,STATUSES,user_database

def create_window(db,*,exit_when_ready=False):
    import tkinter as tk
    from tkinter import ttk,messagebox,filedialog
    app=tk.Tk()
    app.title("AUTOFABRICADOR · Gestor local de pedidos")
    app.minsize(790,550)
    app.geometry("1020x680")
    app.configure(background="#ecf2f7")
    selected=[None]
    status=tk.StringVar(value="Listo. Datos guardados localmente, sin conexión a Internet.")
    search=tk.StringVar()
    search_status=tk.StringVar(value="all")
    reference=tk.StringVar()
    customer=tk.StringVar()
    cents=tk.StringVar(value="0")
    order_status=tk.StringVar(value="pending")
    frame=ttk.Frame(app,padding=16)
    frame.pack(fill="both",expand=True)
    ttk.Label(frame,text="Gestor de pedidos",font=("Segoe UI",18,"bold")).pack(anchor="w")
    ttk.Label(frame,text="Alta, edición, eliminación, búsqueda, filtros y exportación CSV · datos SQLite locales",
              wraplength=970).pack(anchor="w",pady=(1,10))
    filters=ttk.Frame(frame)
    filters.pack(fill="x")
    ttk.Label(filters,text="Buscar").pack(side="left",padx=(0,6))
    ttk.Entry(filters,textvariable=search,width=35).pack(side="left",padx=(0,10))
    ttk.Label(filters,text="Estado").pack(side="left")
    ttk.Combobox(filters,textvariable=search_status,values=("all",)+STATUSES,
                 state="readonly",width=14).pack(side="left",padx=(6,10))
    grid=ttk.Treeview(frame,show="headings",selectmode="browse",
                     columns=("id","reference","customer","amount_cents","status"),
                     height=12)
    columns={
      "id":("ID",65),
      "reference":("Referencia",185),
      "customer":("Cliente",290),
      "amount_cents":("Importe (céntimos)",160),
      "status":("Estado",120)}
    for field,(label,width) in columns.items():
        grid.heading(field,text=label)
        grid.column(field,width=width,minwidth=55,stretch=field=="customer")
    grid.pack(fill="both",expand=True,pady=(10,8))
    fields=ttk.LabelFrame(frame,text="Datos del pedido",padding=12)
    fields.pack(fill="x")
    for i in range(4):fields.columnconfigure(i,weight=1 if i%2 else 0)
    ttk.Label(fields,text="Referencia").grid(row=0,column=0,sticky="w",padx=(0,6),pady=4)
    ttk.Entry(fields,textvariable=reference).grid(row=0,column=1,sticky="ew",padx=(0,15))
    ttk.Label(fields,text="Cliente").grid(row=0,column=2,sticky="w",padx=(0,6))
    ttk.Entry(fields,textvariable=customer).grid(row=0,column=3,sticky="ew")
    ttk.Label(fields,text="Importe en céntimos").grid(row=1,column=0,sticky="w",padx=(0,6),pady=4)
    ttk.Entry(fields,textvariable=cents).grid(row=1,column=1,sticky="ew",padx=(0,15))
    ttk.Label(fields,text="Estado").grid(row=1,column=2,sticky="w",padx=(0,6))
    ttk.Combobox(fields,textvariable=order_status,values=STATUSES,
                 state="readonly").grid(row=1,column=3,sticky="ew")
    buttons=ttk.Frame(frame)
    buttons.pack(fill="x",pady=9)
    def notify(message):status.set(message)
    def refresh():
        try:
            value=search_status.get()
            rows=db.list(search.get(),None if value=="all" else value)
            for item in grid.get_children():
                grid.delete(item)
            for row in rows:
                grid.insert("","end",iid=str(row["id"]),
                    values=tuple(row[field] for field in columns))
            notify(f"{len(rows)} pedidos visibles. Base local íntegra: {db.integrity()}")
        except Exception as exc:
            messagebox.showerror("Consulta",str(exc),parent=app)
    def load_selection(_event=None):
        items=grid.selection()
        if not items:return
        row=db.get(int(items[0]))
        if row is None:return
        selected[0]=row["id"]
        reference.set(row["reference"])
        customer.set(row["customer"])
        cents.set(str(row["amount_cents"]))
        order_status.set(row["status"])
    def clear():
        selected[0]=None
        reference.set("")
        customer.set("")
        cents.set("0")
        order_status.set("pending")
        grid.selection_remove(*grid.selection())
        notify("Nuevo pedido; introduce datos y pulsa Guardar.")
    def save():
        try:
            raw=cents.get().strip()
            if not raw.isascii() or not raw.isdigit():
                raise ValueError("Introduce un importe entero en céntimos, sin signos.")
            amount=int(raw)
            if selected[0] is None:
                obj=db.create(reference.get().strip(),customer.get(),amount,order_status.get())
                notify("Pedido creado: "+obj["reference"])
            else:
                obj=db.update(selected[0],reference.get().strip(),customer.get(),amount,order_status.get())
                notify("Pedido actualizado: "+obj["reference"])
            clear()
            refresh()
        except Exception as exc:
            messagebox.showerror("Validación",str(exc),parent=app)
    def remove():
        if selected[0] is None:
            messagebox.showinfo("Eliminar","Selecciona un pedido.",parent=app)
            return
        if not messagebox.askyesno("Confirmar borrado",
                                   "¿Eliminar este pedido? La acción no se puede deshacer.",
                                   parent=app):return
        if db.delete(selected[0]):
            clear()
            refresh()
        else:messagebox.showerror("Eliminar","El pedido ya no existe.",parent=app)
    def export():
        filename=filedialog.asksaveasfilename(parent=app,title="Guardar copia CSV",
                  defaultextension=".csv",filetypes=[("CSV","*.csv")])
        if not filename:return
        try:
            path=Path(filename)
            if path.suffix.lower()!=".csv":raise ValueError("La exportación debe ser CSV.")
            data=db.export_csv(search.get(),None if search_status.get()=="all" else search_status.get())
            # User explicitly chooses this path through a native dialog. No
            # silent overwrite: ask explicitly if existing.
            if path.exists() and not messagebox.askyesno(
                    "Sobrescribir CSV","¿Sobrescribir el archivo CSV existente?",parent=app):
                return
            path.write_bytes(data)
            notify("CSV guardado en "+str(path))
        except Exception as exc:
            messagebox.showerror("Exportar",str(exc),parent=app)
    for label,callback in (
      ("Nuevo",clear),("Guardar",save),("Eliminar",remove),
      ("Actualizar",refresh),("Exportar CSV",export)):
        ttk.Button(buttons,text=label,command=callback).pack(side="left",padx=(0,7))
    grid.bind("<<TreeviewSelect>>",load_selection)
    search.trace_add("write",lambda *args:refresh())
    search_status.trace_add("write",lambda *args:refresh())
    ttk.Label(frame,textvariable=status,wraplength=980).pack(anchor="w",pady=(5,0))
    refresh()
    if exit_when_ready:
        # No model code. Used solely for deterministic GUI startup smoke.
        app.after(300,app.quit)
    def close():
        try:db.close()
        finally:app.destroy()
    app.protocol("WM_DELETE_WINDOW",close)
    return app

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description="Offline local order desktop application")
    parser.add_argument("--app-id",default="AFD-4d21cc12d45e0a33")
    parser.add_argument("--smoke",action="store_true")
    args=parser.parse_args(argv)
    with Orders(user_database(args.app_id)) as db:
        app=create_window(db,exit_when_ready=args.smoke)
        try:app.mainloop()
        finally:
            try:app.destroy()
            except Exception:pass
    return 0

if __name__=="__main__":sys.exit(main())
