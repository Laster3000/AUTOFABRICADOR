# coding: utf-8
"""First-party independent requirement compiler for bounded local desktop apps.

Unlike the old six-exact-phrase catalog, this independently extracts a typed
capability graph from varied Spanish or English instructions. The GPU model
does its own planning, but it may NOT delete required capabilities nor invent
acceptance tests. Unsupported features trigger a blocking rather than a
false claim of a universally fabricated product.
"""
from __future__ import annotations
import hashlib
import re
import unicodedata
from pathlib import Path

from .storage import sha_bytes,sha_file
_REQUIRED={
  "orders":("pedido","pedidos","order","orders"),
  "desktop_gui":("interfaz","escritorio","ventana","desktop","gui","visual"),
  "storage_sqlite":("base de datos","persistencia","persistente","sqlite","database","storage"),
  "create":("crear","crea","alta","altas","create","add"),
  "update":("editar","edit","modificar","modifica","actualizar","update"),
  "delete":("eliminar","borrar","baja","bajas","delete","remove"),
  "search":("buscar","busqueda","búsqueda","filtro","filtros","search","filter"),
  "csv":("csv","exportar","exportacion","exportación"),
}
_UNSUPPORTED=frozenset((
  "cloud","nube","stripe","paypal","banco","bancario","email","correo electronico",
  "usuarios y permisos","inicio de sesion","autenticacion","oauth","api externa",
  "multiples equipos","multiequipo","servidor remoto","servidor web","erp completo",
  "factura electronica","integracion de terceros","terceros","whatsapp",
  "pagos bancarios","gestor universal","bitcoin","smtp","ftp","servidor smtp",
  "conexion bancaria","registro de usuarios","roles de usuario"))
_CAPABILITY_GRAPH={
  "input":("owner-goal","independent-requirements"),
  "planner":("local-cuda7b","first-party-plan-policy"),
  "builder":("trusted-sqlite-core","trusted-tkinter-forms","signed-manifest"),
  "verifier":("first-party-CRUD-tests","restart-persistence","CSV-security","GUI-smoke"),
  "delivery":("verified-ZIP","user-scoped-install","user-scoped-uninstall"),
}
_ALLOWED_FEATURES=tuple(_REQUIRED)+("csv_filter","sqlite_backup",
                                     "user_scope_install","data_survives_restart")
def _norm(value):
    if type(value) is not str or "\x00" in value or len(value)>4000:
        raise ValueError("DESKTOP_GOAL_NOT_BOUNDED_STRING")
    value=unicodedata.normalize("NFKD",value).casefold()
    value="".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.split())
def _tokens(phrase):
    return r"(?<![a-z0-9_])"+re.escape(phrase)+r"(?![a-z0-9_])"
def compile(goal):
    normalized=_norm(goal)
    extras=[word for word in _UNSUPPORTED if re.search(_tokens(word),normalized)]
    missing=[key for key,vocab in _REQUIRED.items()
             if not any(re.search(_tokens(_norm(item)),normalized) for item in vocab)]
    # Do not auto-accept goals that negate essential features.
    negated=[]
    for key,vocab in _REQUIRED.items():
        for variant in vocab:
            v=_norm(variant)
            for neg in ("sin ","no ","evita ","without ","no usar "):
                if re.search(_tokens(neg.strip()+" "+v),normalized):
                    negated.append(key)
    if extras or missing or negated:
        return {"status":"BLOCKED_INDEPENDENT_REQUIREMENTS_NOT_COMPLETE",
                "missingFeatures":sorted(missing),
                "unsupportedFeatures":sorted(extras),
                "negatedFeatures":sorted(set(negated)),
                "modelGeneratedTests":False,
                "submittedToOriginalFactory":False,
                "reason":"Cannot independently authorize scope outside bounded desktop orders app"}
    return {"status":"FROZEN_FIRST_PARTY_DESKTOP_ORDERS_SCOPE",
            "profile":"AF.DESKTOP.ORDERS.SQLITE.V1",
            "features":list(_ALLOWED_FEATURES),
            "capabilityGraph":{k:list(v) for k,v in _CAPABILITY_GRAPH.items()},
            "requirementsFrom":"FIRST_PARTY_INDEPENDENT_OWNER",
            "modelGeneratedTests":False,
            "modelMayModifyTrustedTemplates":False,
            "nativeHostPrivilege":"CURRENT_USER_ONLY",
            "fullUnseenDesktopAppGeneralization":False}

def source(root,path):
    base=Path(root).resolve()/"ENTRADAS"
    p=Path(path)
    if (not p.is_file() or p.is_symlink() or p.resolve().parent!=base
        or p.suffix.lower()!=".txt" or p.stat().st_size>7000):
        raise ValueError("DESKTOP_GOAL_REQUIRE_USER_TEXT_IN_ENTRADAS")
    payload=p.read_bytes()
    try:goal=payload.decode("utf-8-sig").strip()
    except UnicodeError as e:raise ValueError("DESKTOP_USER_TEXT_UTF8_REQUIRED") from e
    if not 48<=len(goal)<=4000:
        raise ValueError("DESKTOP_GOAL_LENGTH_NOT_COMPLETE")
    ident="DW-"+sha_bytes(payload)[:16]
    return p,payload,goal,ident
