# app.py
# Sistema de Compromisos de Gestión -- Streamlit
# Incluye: export CSV vertical, detección import vertical/horizontal, IDs AC_xxx_año / F_xxx_año,
# logo OPP en encabezado, manejo robusto de adjuntos (upload/download zip).
# Autor: Generado para usuario (mejoras solicitadas)

import streamlit as st
import os, json, hashlib, pandas, secrets, datetime, csv, io, zipfile, shutil, uuid, time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# --------------------------
# Configuración básica
# --------------------------
APP_TITLE = "Sistema de Compromisos de Gestión"
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
AGREEMENTS_FILE = os.path.join(DATA_DIR, "agreements.json")
AUDIT_FILE = os.path.join(DATA_DIR, "audit.json")
NATURALEZA_MAP_FILE = os.path.join(DATA_DIR, "naturaleza_map.json")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
COUNTERS_FILE = os.path.join(DATA_DIR, "counters.json")
LOGO_FILES = ["logo_opp.png", "logo.png"]  # intenta cargar en este orden

# --------------------------
# Helper: asegurar storage
# --------------------------
def ensure_storage():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        # asegurar archivos base
        if not os.path.exists(USERS_FILE):
            save_json(USERS_FILE, {})
        if not os.path.exists(AGREEMENTS_FILE):
            save_json(AGREEMENTS_FILE, {})
        if not os.path.exists(COUNTERS_FILE):
            save_json(COUNTERS_FILE, {"agreements": {}, "fichas": {}})
        return True
    except Exception as e:
        print("ERROR ensure_storage:", e)
        return False

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

PERSIST_OK = ensure_storage()

# --------------------------
# Contadores persistentes (para numeración AC_ / F_)
# --------------------------
def get_next_counter(kind: str, year: int) -> int:
    counters = load_json(COUNTERS_FILE, {"agreements": {}, "fichas": {}})
    if kind not in counters:
        counters[kind] = {}
    year_str = str(year)
    counters[kind].setdefault(year_str, 0)
    counters[kind][year_str] += 1
    save_json(COUNTERS_FILE, counters)
    return counters[kind][year_str]

def format_counter_number(n: int, width: int = 4) -> str:
    return str(n).zfill(width)

def generate_agreement_code(year: int) -> str:
    n = get_next_counter("agreements", year)
    return f"AC_{format_counter_number(n)}_{year}"

def generate_ficha_code(year: int) -> str:
    n = get_next_counter("fichas", year)
    return f"F_{format_counter_number(n)}_{year}"

# --------------------------
# Seguridad / Usuarios
# --------------------------
DEFAULT_ROLES = ["Administrador","Responsable","Supervisor","Comisión de CG"]

def hash_password(pw: str, salt: Optional[str]=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    return f"{salt}${h}"

def check_password(pw: str, hashed: str):
    try:
        salt, h = hashed.split("$",1)
        return hash_password(pw, salt) == hashed
    except Exception:
        return False

def bootstrap_admin():
    users = load_json(USERS_FILE, {})
    if not users:
        users["admin"] = {
            "username":"admin",
            "name":"Administrador",
            "role":"Administrador",
            "active": True,
            "password": hash_password("admin")
        }
        save_json(USERS_FILE, users)

bootstrap_admin()

# --------------------------
# Modelos / Defaults
# --------------------------
ORGANISMO_TIPOS = [
    "Administración Central",
    "Organismos del Art. 220",
    "PPNoE",
    "Empresas Públicas",
    "Otros",
]

TIPO_COMPROMISO = [
    "CG - Institucional",
    "CG - Funcional",
    "EEPP - SRV",
    "EEPP - SRCM",
    "EEPP - Compromisos de Gestión",
]

ESTADOS = ["Borrador","En revisión","Aprobado"]

def today_str():
    return datetime.date.today().isoformat()

def dt_parse(dstr: str) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat(dstr)
    except Exception:
        return None

# legacy id generator for internal unique ids (still usable)
def gen_uuid(prefix:str="ID") -> str:
    return f"{prefix}_{secrets.token_hex(6)}"

def agreements_load() -> Dict[str, Any]:
    return load_json(AGREEMENTS_FILE, {})

def agreements_save(db: Dict[str, Any]):
    save_json(AGREEMENTS_FILE, db)

def audit_log(event: str, details: Dict[str, Any]):
    audit = load_json(AUDIT_FILE, [])
    audit.append({"ts": datetime.datetime.now().isoformat(), "event": event, "details": details})
    save_json(AUDIT_FILE, audit)

# --------------------------
# CSV vertical export/import helpers
# --------------------------
def export_csv_vertical_agreement_template() -> str:
    """
    Devuelve una plantilla vertical clara y amigable para carga de acuerdos, fichas y metas.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    # Encabezado
    w.writerow(["atributo", "valor"])
    # Fila de ejemplo
    w.writerow(["# Instrucción:", "Complete cada atributo con el valor correspondiente. No modifique los nombres de los atributos."])
    # Acuerdo - cabecera
    w.writerow(["agreement_code", "AC_0001_2025"])
    w.writerow(["agreement_anio", "2025"])
    w.writerow(["agreement_tipo", "CG - Institucional"])
    w.writerow(["organismo_tipo", "Administración Central"])
    w.writerow(["organismo_nombre", "Nombre del organismo"])
    w.writerow(["naturaleza_juridica", "Ejemplo: Ente Autónomo"])
    w.writerow(["vigencia_desde", "2025-01-01"])
    w.writerow(["vigencia_hasta", "2025-12-31"])
    w.writerow(["organismo_enlace", "Nombre del organismo de enlace"])
    w.writerow(["objeto", "Descripción del objeto del acuerdo"])
    w.writerow(["partes_firmantes", "Firmante1; Firmante2"])
    w.writerow(["estado", "Borrador"])
    w.writerow(["created_by", "usuario_creador"])
    w.writerow(["---", "---"])  # separador legible

    # Ficha de ejemplo
    w.writerow(["ficha_code", "F_0001_2025"])
    w.writerow(["ficha_nombre", "Nombre de la ficha"])
    w.writerow(["ficha_tipo_meta", "Institucional"])
    w.writerow(["ficha_responsables_cumpl", "Responsable1; Responsable2"])
    w.writerow(["ficha_objetivo", "Objetivo de la ficha"])
    w.writerow(["ficha_indicador", "Indicador de la ficha"])
    w.writerow(["ficha_forma_calculo", "Descripción de la forma de cálculo"])
    w.writerow(["ficha_fuente", "Fuente de información"])
    w.writerow(["ficha_valor_base", "Valor base"])
    w.writerow(["ficha_responsables_seguimiento", "Responsable seguimiento"])
    w.writerow(["ficha_observaciones", "Observaciones"])
    w.writerow(["ficha_salvaguarda", "SI/NO"])
    w.writerow(["---", "---"])

    # Meta de ejemplo
    w.writerow(["meta_id", "META_001"])
    w.writerow(["meta_unidad", "%"])
    w.writerow(["meta_valor_objetivo", "100"])
    w.writerow(["meta_sentido", ">="])
    w.writerow(["meta_descripcion", "Descripción de la meta"])
    w.writerow(["meta_frecuencia", "Anual"])
    w.writerow(["meta_vencimiento", "2025-12-31"])
    w.writerow(["meta_es_hito", "NO"])
    w.writerow(["meta_rango", "0|100|100"])
    w.writerow(["meta_ponderacion", "100"])
    w.writerow(["meta_cumplimiento_valor", ""])
    w.writerow(["meta_cumplimiento_calc", ""])
    w.writerow(["meta_observaciones", ""])
    w.writerow(["---", "---"])
    w.writerow(["###", "###"])  # separador fichas
    return buf.getvalue()

def parse_bool_si_no(x: str) -> bool:
    return str(x or "").strip().lower() in ["si","sí","true","1","yes"]

def importar_csv_vertical_to_agreement(stream: io.StringIO, agr: Dict[str,Any]) -> int:
    """
    Importa CSV vertical (atributo,valor). 
    Actualiza el acuerdo/crea fichas/metas si corresponde.
    Devuelve número de metas importadas/actualizadas.
    """
    reader = csv.reader(stream)
    rows = [r for r in reader if r]
    # Convertir a pares
    pairs = []
    for r in rows:
        if len(r) >= 2:
            pairs.append((r[0].strip(), "|".join([c.strip() for c in r[1:]])))
        elif len(r) == 1:
            pairs.append((r[0].strip(), ""))
    # Procesar secuencialmente: si ficha_code aparece, preparar nueva ficha; meta_id crea meta etc.
    imported = 0
    current_ficha = None
    for key, val in pairs:
        if key in ["agreement_code","agreement_anio","agreement_tipo","organismo_tipo","organismo_nombre",
                   "naturaleza_juridica","vigencia_desde","vigencia_hasta","organismo_enlace",
                   "objeto","partes_firmantes","estado"]:
            # asignar a agr si aplicable
            if key == "agreement_code":
                agr["id"] = val or agr.get("id", agr.get("id",""))
            elif key == "agreement_anio":
                try:
                    agr["anio"] = int(val)
                except:
                    pass
            else:
                agr[key.replace("agreement_","")] = val
        elif key == "ficha_code":
            # encontrar ficha por id, si existe usarla, sino crear
            fid = val or ""
            found = None
            for f in agr.get("fichas",[]):
                if f.get("id") == fid:
                    found = f
                    break
            if not found:
                # crear ficha con id sugerido (si fid vacío -> crear con generate_ficha_code)
                if not fid:
                    fid = generate_ficha_code(agr.get("anio", datetime.date.today().year))
                found = {
                    "id": fid,
                    "nombre": "",
                    "tipo_meta": "Institucional",
                    "responsables_cumpl": "",
                    "objetivo": "",
                    "indicador": "",
                    "forma_calculo": "",
                    "fuente": "",
                    "valor_base": "",
                    "responsables_seguimiento": "",
                    "observaciones": "",
                    "salvaguarda_flag": False,
                    "salvaguarda_text": "",
                    "metas": []
                }
                agr.setdefault("fichas",[]).append(found)
            current_ficha = found
        elif key.startswith("ficha_") and current_ficha is not None:
            subkey = key.replace("ficha_","")
            if subkey == "salvaguarda":
                current_ficha["salvaguarda_flag"] = parse_bool_si_no(val)
            else:
                current_ficha[subkey] = val
        elif key == "meta_id" and current_ficha is not None:
            # buscar meta por id
            mid = val or ""
            foundm = None
            for m in current_ficha.get("metas",[]):
                if m.get("id")==mid:
                    foundm = m
                    break
            if not foundm:
                if not mid:
                    mid = gen_uuid("META")
                foundm = {
                    "id": mid,
                    "unidad": "%",
                    "valor_objetivo": "",
                    "sentido": ">=",
                    "descripcion": "",
                    "frecuencia": "Anual",
                    "vencimiento": f"{agr.get('anio', datetime.date.today().year)}-12-31",
                    "es_hito": False,
                    "rango": [],
                    "ponderacion": 0.0,
                    "cumplimiento_valor": "",
                    "cumplimiento_calc": None,
                    "observaciones": ""
                }
                current_ficha.setdefault("metas",[]).append(foundm)
                imported += 1
            current_meta = foundm
        elif key.startswith("meta_") and current_ficha is not None:
            # aplicar a la última meta creada/actual
            if not current_ficha.get("metas"):
                continue
            current_meta = current_ficha["metas"][-1]
            subk = key.replace("meta_","")
            if subk == "es_hito":
                current_meta["es_hito"] = parse_bool_si_no(val)
            elif subk == "rango":
                rlist = []
                if val:
                    for part in val.split(";"):
                        if "|" in part:
                            a,b,c = (part.split("|")+["","",""])[:3]
                            rlist.append({"min":a,"max":b,"porcentaje":c})
                current_meta["rango"] = rlist
            elif subk == "ponderacion":
                try:
                    current_meta["ponderacion"] = float(val)
                except:
                    current_meta["ponderacion"] = 0.0
            else:
                current_meta[subk] = val
    return imported

# --------------------------
# Export horizontal CSV (legacy) and detection
# --------------------------
def export_csv_horizontal_agreement(agr: Dict[str,Any]) -> str:
    headers = [
        "agreement_id","agreement_anio","agreement_tipo","organismo_type","organismo_nombre",
        "ficha_id","ficha_nombre","ficha_tipo_meta","responsables_cumpl","objetivo","indicador","forma_calculo",
        "fuente","valor_base","resp_seguimiento","ficha_observaciones","salvaguarda",
        "meta_id","unidad","valor_objetivo","sentido","descripcion","frecuencia","vencimiento","es_hito",
        "rango_serializado","ponderacion","cumplimiento_valor","cumplimiento_calc","meta_observaciones"
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for f in agr.get("fichas",[]):
        for m in f.get("metas",[]):
            rango_s = ";".join([f"{rg.get('min','')}|{rg.get('max','')}|{rg.get('porcentaje','')}" for rg in (m.get("rango") or [])])
            w.writerow([
                agr.get("id",""), agr.get("anio",""), agr.get("tipo_compromiso",""), agr.get("organismo_tipo",""), agr.get("organismo_nombre",""),
                f.get("id",""), f.get("nombre",""), f.get("tipo_meta",""), f.get("responsables_cumpl",""), f.get("objetivo",""),
                f.get("indicador",""), f.get("forma_calculo",""), f.get("fuente",""), f.get("valor_base",""),
                f.get("responsables_seguimiento",""), f.get("observaciones",""), "SI" if f.get("salvaguarda_flag") else "NO",
                m.get("id",""), m.get("unidad",""), m.get("valor_objetivo",""), m.get("sentido",""), m.get("descripcion",""),
                m.get("frecuencia",""), m.get("vencimiento",""), "SI" if m.get("es_hito") else "NO",
                rango_s, m.get("ponderacion",0), m.get("cumplimiento_valor",""), m.get("cumplimiento_calc",""), m.get("observaciones","")
            ])
    return buf.getvalue()

def detect_csv_format_and_import(upl_bytes: bytes, agr: Dict[str,Any]) -> int:
    """
    Detecta si CSV es vertical (atributo,valor) o horizontal (fila/meta).
    Importa y devuelve cantidad de metas afectadas.
    """
    s = upl_bytes.decode("utf-8", errors="replace")
    # chequeo simple: si primera línea contiene 'atributo' -> vertical
    first_line = s.splitlines()[0] if s.splitlines() else ""
    imported = 0
    if "atributo" in first_line.lower() or ("," in first_line and len(first_line.split(","))==2):
        # considerar como vertical
        buf = io.StringIO(s)
        imported = importar_csv_vertical_to_agreement(buf, agr)
    else:
        # interpretar como horizontal (legacy)
        reader = csv.DictReader(io.StringIO(s))
        imported = importar_csv_en_acuerdo(reader, agr)
    return imported

# --------------------------
# Importador legacy (por filas => metas)
# --------------------------
def importar_csv_en_acuerdo(reader: csv.DictReader, agr: Dict[str,Any]) -> int:
    fichas_by_id = {f["id"]: f for f in agr.get("fichas",[])}
    fichas_by_name = { (f.get("nombre","") or "").lower(): f for f in agr.get("fichas",[])}
    count = 0
    for row in reader:
        fid = (row.get("ficha_id(blank_new)") or "").strip()
        fname = (row.get("ficha_nombre") or "").strip()
        f = None
        if fid and fid in fichas_by_id:
            f = fichas_by_id[fid]
        elif fname and fname.lower() in fichas_by_name:
            f = fichas_by_name[fname.lower()]
        else:
            # crear ficha con id generación nueva en formato F_xxx_año
            year = agr.get("anio") or datetime.date.today().year
            new_fid = fid if fid else generate_ficha_code(year)
            f = {
                "id": new_fid,
                "nombre": fname,
                "tipo_meta": row.get("ficha_tipo_meta[Institucional|Grupal/Sectorial|Individual]","Institucional"),
                "responsables_cumpl": row.get("responsables_cumpl",""),
                "objetivo": row.get("objetivo",""),
                "indicador": row.get("indicador(*)",""),
                "forma_calculo": row.get("forma_calculo",""),
                "fuente": row.get("fuente(*)",""),
                "valor_base": row.get("valor_base",""),
                "responsables_seguimiento": row.get("resp_seguimiento",""),
                "observaciones": row.get("ficha_observaciones",""),
                "salvaguarda_flag": parse_bool_si_no(row.get("salvaguarda[SI/NO]","NO")),
                "salvaguarda_text": "",
                "metas":[]
            }
            agr.setdefault("fichas",[]).append(f)
            fichas_by_id[f["id"]] = f
            fichas_by_name[(fname or "").lower()] = f
        # Meta
        mid = (row.get("meta_id(blank_new)") or "").strip()
        es_hito = parse_bool_si_no(row.get("es_hito[SI/NO]","NO"))
        rango_str = row.get("rango(min1|max1|pct1;min2|max2|pct2;...)","").strip()
        rlist=[]
        if rango_str:
            for part in rango_str.split(";"):
                if "|" in part:
                    a,b,c = (part.split("|")+["","",""])[:3]
                    rlist.append({"min":a,"max":b,"porcentaje":c})
        meta = None
        if mid:
            for m in f["metas"]:
                if m["id"]==mid:
                    meta = m
                    break
        if not meta:
            meta = {
                "id": gen_uuid("META"),
                "unidad": row.get("unidad",""),
                "valor_objetivo": row.get("valor_objetivo",""),
                "sentido": row.get("sentido[>=|<=|==]",">="),
                "descripcion": row.get("descripcion",""),
                "frecuencia": row.get("frecuencia[Trimestral|Semestral|Anual]","Anual"),
                "vencimiento": row.get("vencimiento(YYYY-MM-DD)", f"{agr.get('anio')}-12-31"),
                "es_hito": es_hito,
                "rango": rlist,
                "ponderacion": float(row.get("ponderacion(%)","0") or 0),
                "cumplimiento_valor": row.get("cumplimiento_valor",""),
                "cumplimiento_calc": None,
                "observaciones": row.get("meta_observaciones","")
            }
            f["metas"].append(meta)
            count += 1
        else:
            meta.update({
                "unidad": row.get("unidad", meta.get("unidad","")),
                "valor_objetivo": row.get("valor_objetivo", meta.get("valor_objetivo","")),
                "sentido": row.get("sentido[>=|<=|==]", meta.get("sentido",">=")),
                "descripcion": row.get("descripcion", meta.get("descripcion","")),
                "frecuencia": row.get("frecuencia[Trimestral|Semestral|Anual]", meta.get("frecuencia","Anual")),
                "vencimiento": row.get("vencimiento(YYYY-MM-DD)", meta.get("vencimiento", f"{agr.get('anio')}-12-31")),
                "es_hito": es_hito,
                "rango": rlist or meta.get("rango",[]),
                "ponderacion": float(row.get("ponderacion(%)", meta.get("ponderacion",0)) or 0),
                "cumplimiento_valor": row.get("cumplimiento_valor", meta.get("cumplimiento_valor","")),
                "observaciones": row.get("meta_observaciones", meta.get("observaciones",""))
            })
            count += 1
    return count

# --------------------------
# Cálculo cumplimiento y utilidades
# --------------------------
def calcular_cumplimiento(meta: Dict[str,Any]) -> Optional[float]:
    v_obj = str(meta.get("valor_objetivo","")).strip()
    val = str(meta.get("cumplimiento_valor","")).strip()
    if v_obj=="" or val=="":
        return None
    try:
        objetivo = float(v_obj.replace(",","."))
        valor = float(val.replace(",","."))
    except:
        if meta.get("es_hito"):
            return 100.0 if val.strip().lower() in ["1","true","si","sí"] else 0.0
        return None
    if meta.get("es_hito"):
        return 100.0 if valor>=1.0 else 0.0
    sentido = meta.get("sentido", ">=")
    if sentido == ">=":
        base_pct = 0.0 if objetivo==0 else (valor/objetivo)*100.0
    elif sentido == "<=":
        base_pct = 0.0 if valor==0 else (objetivo/valor)*100.0
    else:
        if objetivo==0:
            base_pct = 100.0 if abs(valor-objetivo)<1e-9 else 0.0
        else:
            diff = abs(valor-objetivo)/abs(objetivo)
            base_pct = max(0.0, 100.0*(1.0 - diff))
    rango = meta.get("rango") or []
    if rango:
        for rg in rango:
            try:
                mn = float(str(rg.get("min","")).replace(",",".")) if str(rg.get("min","")).strip()!="" else -1e9
                mx = float(str(rg.get("max","")).replace(",",".")) if str(rg.get("max","")).strip()!="" else 1e9
                pct = float(str(rg.get("porcentaje","")).replace(",",".")) if str(rg.get("porcentaje","")).strip()!="" else None
            except:
                continue
            if pct is None:
                continue
            if mn <= base_pct <= mx:
                return max(0.0, min(100.0, pct))
        return 0.0
    if base_pct >= 95.0:
        return 100.0
    elif base_pct >= 75.0:
        return (base_pct - 75.0) * (100.0/20.0)
    else:
        return 0.0

def periodo_label(meta: Dict[str,Any]) -> str:
    v = dt_parse(meta.get("vencimiento","")) or datetime.date.today()
    freq = meta.get("frecuencia","Anual")
    if freq == "Anual":
        return f"ANUAL-{v.year}"
    elif freq == "Semestral":
        sem = 1 if v.month<=6 else 2
        return f"S{sem}-{v.year}"
    else:
        q = 1 if v.month<=3 else 2 if v.month<=6 else 3 if v.month<=9 else 4
        return f"Q{q}-{v.year}"

def validar_ponderaciones_ficha(ficha: Dict[str,Any], agr: Dict[str,Any]):
    metas = ficha.get("metas",[])
    per_sums: Dict[str,float] = {}
    for m in metas:
        lbl = periodo_label(m)
        per_sums[lbl] = per_sums.get(lbl,0.0) + float(m.get("ponderacion",0.0))
    for lbl, s in per_sums.items():
        if abs(s - 100.0) > 1e-6:
            st.warning(f"⚠️ En {ficha['id']} ({ficha['tipo_meta']}) el período {lbl} suma {s:.1f}% (debe sumar 100%).")

# --------------------------
# UI / Layout helpers (logo)
# --------------------------
def try_load_logo():
    for fname in LOGO_FILES:
        if os.path.exists(fname):
            try:
                return open(fname, "rb").read()
            except:
                continue
    return None

def header_with_logo():
    # Muestra logo si existe; si no, muestra título textual
    logo_data = try_load_logo()
    if logo_data:
        try:
            st.image(logo_data, width=200)
        except:
            st.markdown(f"### {APP_TITLE}")
    else:
        st.markdown("## OPP - Sistema de Compromisos de Gestión")
        st.markdown("---")

# --------------------------
# Páginas: login, admin, acuerdos, reportes
# --------------------------
if "user" not in st.session_state:
    st.session_state.user = None

def require_login():
    if not st.session_state.user:
        st.warning("Por favor, inicia sesión.")
        st.stop()

def require_role(roles: List[str]):
    user = st.session_state.user
    if not user or user["role"] not in roles:
        st.error("No tienes permisos para acceder a esta sección.")
        st.stop()

def page_login():
    header_with_logo()
    st.title(APP_TITLE)
    if not PERSIST_OK:
        st.info("⚠️ No hay permisos de escritura. Se trabajará sin persistencia.")
    st.subheader("Ingreso")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    colA, colB = st.columns(2)
    if colA.button("Ingresar", use_container_width=True):
        users = load_json(USERS_FILE, {})
        u = users.get(username)
        if u and u.get("active") and check_password(password, u["password"]):
            st.session_state.user = u
            st.success(f"Bienvenido/a, {u.get('name','')} ({u['role']})")
            st.rerun()
        else:
            st.error("Usuario o contraseña inválidos, o usuario inactivo.")
    if colB.button("Salir", use_container_width=True):
        st.session_state.user = None
        st.rerun()

def page_admin():
    require_role(["Administrador"])
    st.header("Administración")
    tab_usuarios, tab_roles = st.tabs(["Usuarios", "Roles"])
    with tab_usuarios:
        st.subheader("Usuarios")
        users = load_json(USERS_FILE, {})
        cols = st.columns([2,2,2,2,1,1])
        cols[0].markdown("**Usuario**")
        cols[1].markdown("**Nombre**")
        cols[2].markdown("**Rol**")
        cols[3].markdown("**Activo**")
        cols[4].markdown("**Reset**")
        cols[5].markdown("**Borrar**")
        for uname, u in list(users.items()):
            c = st.columns([2,2,2,2,1,1])
            c[0].write(uname)
            name = c[1].text_input(f"Nombre_{uname}", u.get("name",""))
            role = c[2].selectbox(f"Rol_{uname}", DEFAULT_ROLES, index=DEFAULT_ROLES.index(u.get("role","Responsable")))
            active = c[3].checkbox(f"Activo_{uname}", value=u.get("active",True))
            if c[4].button("Reset", key=f"reset_{uname}"):
                users[uname]["password"] = hash_password("123456")
                st.toast(f"Contraseña de {uname} reiniciada a 123456")
            if c[5].button("Borrar", key=f"del_{uname}"):
                if uname == "admin":
                    st.warning("No se puede borrar el admin inicial.")
                else:
                    users.pop(uname, None)
                    st.toast(f"Usuario {uname} eliminado")
            users[uname]["name"]=name
            users[uname]["role"]=role
            users[uname]["active"]=active
        st.button("Guardar cambios", on_click=lambda: save_json(USERS_FILE, users))
        st.markdown("---")
        st.subheader("Crear nuevo usuario")
        with st.form("new_user"):
            nu = st.text_input("Usuario nuevo").strip()
            nn = st.text_input("Nombre y Apellido")
            nr = st.selectbox("Rol", DEFAULT_ROLES, index=1)
            np = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Crear")
        if submitted:
            if not nu or not np:
                st.error("Usuario y contraseña son obligatorios.")
            else:
                if nu in users:
                    st.error("El usuario ya existe.")
                else:
                    users[nu]={
                        "username": nu,
                        "name": nn or nu,
                        "role": nr,
                        "active": True,
                        "password": hash_password(np)
                    }
                    save_json(USERS_FILE, users)
                    st.success("Usuario creado.")
        st.markdown("---")
        st.subheader("Mapa de Naturaleza Jurídica por Organismo (autocompletar)")
        natmap = load_json(NATURALEZA_MAP_FILE, {})
        org = st.text_input("Nombre de Organismo")
        nat = st.text_input("Naturaleza Jurídica")
        colx, coly = st.columns(2)
        if colx.button("Agregar/Actualizar"):
            if org and nat:
                natmap[org]=nat
                save_json(NATURALEZA_MAP_FILE, natmap)
                st.success("Guardado.")
        if coly.button("Limpiar mapa"):
            save_json(NATURALEZA_MAP_FILE, {})
            st.success("Mapa limpiado.")
        st.write("Mapa actual:", natmap)

    with tab_roles:
        st.subheader("Gestión de Roles")
        roles = load_json("roles.json", DEFAULT_ROLES)
        new_role = st.text_input("Nuevo rol")
        if st.button("Agregar rol"):
            if new_role and new_role not in roles:
                roles.append(new_role)
                save_json("roles.json", roles)
                st.success("Rol agregado.")
        if st.button("Limpiar roles personalizados"):
            save_json("roles.json", DEFAULT_ROLES)
        st.write("Roles actuales:", roles)

# Default agreement object (usa código AC_xxx_year al crear)
def default_agreement(created_by):
    anio = datetime.date.today().year
    code = generate_agreement_code(anio)
    return {
        "id": code,
        "tipo_compromiso": TIPO_COMPROMISO[0],
        "organismo_tipo": ORGANISMO_TIPOS[0],
        "organismo_nombre": "",
        "naturaleza_juridica": "",
        "anio": anio,
        "vigencia_desde": f"{anio}-01-01",
        "vigencia_hasta": f"{anio}-12-31",
        "organismo_enlace": "",
        "objeto": "",
        "partes_firmantes": "",
        "estado": "Borrador",
        "created_by": created_by,
        "attachments": [],
        "fichas": [],
        "versions": [],
        "current_version": None,
    }

def page_agreements():
    require_login()
    header_with_logo()
    st.header("Acuerdos")
    db = agreements_load()
    user = st.session_state.user

    # Crear
    if user["role"] in ["Administrador","Responsable","Supervisor"]:
        if st.button("➕ Crear nuevo acuerdo"):
            agr = default_agreement(user["username"])
            db[agr["id"]] = agr
            agreements_save(db)
            audit_log("create_agreement", {"id": agr["id"], "by": user["username"]})
            st.rerun()

    # Filtros
    years = sorted({ a.get("anio", datetime.date.today().year) for a in db.values() }) if db else [datetime.date.today().year]
    if years:
        fy = st.selectbox("Filtrar por año", options=years, index=len(years)-1)
    else:
        fy = datetime.date.today().year
    ft = st.multiselect("Tipo de compromiso", options=TIPO_COMPROMISO, default=TIPO_COMPROMISO)

    # Lista
    for agr_id, agr in db.items():
        if agr.get("anio") != fy or agr.get("tipo_compromiso") not in ft:
            continue
        st.markdown("---")
        cols = st.columns([2,2,2,2,2,1])
        cols[0].write(f"**{agr.get('organismo_nombre') or 'Sin nombre'}**")
        cols[1].write(agr.get("tipo_compromiso"))
        cols[2].write(f"Año: {agr.get('anio')}")
        cols[3].write(f"Estado: {agr.get('estado')}")
        cols[4].write(f"Código: {agr_id}")
        if cols[5].button("Abrir", key=f"open_{agr_id}"):
            st.session_state["open_agr"]=agr_id
            st.rerun()

    # Editor
    if "open_agr" in st.session_state and st.session_state["open_agr"] in db:
        agr = db[st.session_state["open_agr"]]
        st.subheader(f"Editar Acuerdo: {agr['id']}")
        editable = True
        if agr.get("estado")=="Aprobado" and not any(f.get("salvaguarda_flag") for f in agr.get("fichas",[])):
            st.info("✅ Acuerdo aprobado. Edición bloqueada (salvo que actives Salvaguarda en alguna ficha).")
            editable = False

        # Datos generales
        with st.expander("Datos del Acuerdo", expanded=True):
            col1, col2, col3 = st.columns(3)
            agr["tipo_compromiso"] = col1.selectbox("Tipo de Compromiso", TIPO_COMPROMISO, index=TIPO_COMPROMISO.index(agr.get("tipo_compromiso",TIPO_COMPROMISO[0])), disabled=not editable)
            agr["organismo_tipo"] = col2.selectbox("Tipo de Organismo", ORGANISMO_TIPOS, index=ORGANISMO_TIPOS.index(agr.get("organismo_tipo",ORGANISMO_TIPOS[0])), disabled=not editable)
            agr["organismo_nombre"] = col3.text_input("Organismo", value=agr.get("organismo_nombre",""), disabled=not editable)

            natmap = load_json(NATURALEZA_MAP_FILE, {})
            def_auto_nat = natmap.get(agr.get("organismo_nombre",""), "")
            agr["naturaleza_juridica"] = st.text_input("Naturaleza Jurídica (autocompletable)", value=agr.get("naturaleza_juridica", def_auto_nat), disabled=not editable)

            col4, col5, col6 = st.columns(3)
            agr["anio"] = col4.number_input("Año del acuerdo", value=int(agr.get("anio", datetime.date.today().year)), step=1, disabled=not editable)
            agr["vigencia_desde"] = col5.date_input("Vigencia desde", value=dt_parse(agr.get("vigencia_desde")) or datetime.date(agr["anio"],1,1), disabled=not editable).isoformat()
            agr["vigencia_hasta"] = col6.date_input("Vigencia hasta", value=dt_parse(agr.get("vigencia_hasta")) or datetime.date(agr["anio"],12,31), disabled=not editable).isoformat()

            agr["organismo_enlace"] = st.text_input("Organismo de Enlace (si corresponde)", value=agr.get("organismo_enlace",""), disabled=not editable)
            agr["partes_firmantes"] = st.text_area("Partes firmantes", value=agr.get("partes_firmantes", ""), disabled=not editable)
            agr["objeto"] = st.text_area("Objeto del acuerdo", value=agr.get("objeto", ""), disabled=not editable)

            # Adjuntos - subida
            st.markdown("**Adjuntar archivos (PDF/Word/otros)**")
            up = st.file_uploader("Sube archivos del acuerdo", accept_multiple_files=True, disabled=not editable)
            if up and editable:
                updir = os.path.join(UPLOADS_DIR, agr["id"])
                os.makedirs(updir, exist_ok=True)
                for f in up:
                    safe_name = f.name
                    path = os.path.join(updir, safe_name)
                    # evitar sobreescritura simple: si existe agregar sufijo timestamp
                    if os.path.exists(path):
                        basename, ext = os.path.splitext(safe_name)
                        path = os.path.join(updir, f"{basename}_{int(time.time())}{ext}")
                    with open(path, "wb") as wf:
                        wf.write(f.read())
                    agr.setdefault("attachments",[]).append({"name": os.path.basename(path), "path": path})
                st.success("Adjuntos cargados.")
            # Descarga adjuntos individuales
            if agr.get("attachments"):
                for att in agr.get("attachments"):
                    try:
                        if os.path.exists(att.get("path","")):
                            with open(att["path"], "rb") as f:
                                file_data = f.read()
                            st.download_button(
                                f"Descargar: {att['name']}", 
                                data=file_data, 
                                file_name=att["name"],
                                key=f"dl_{agr['id']}_{att['name']}_{int(time.time())}"
                            )
                        else:
                            st.error(f"No se puede localizar archivo: {att.get('name')}")
                    except Exception as e:
                        st.error(f"No se puede descargar {att.get('name')}: {e}")

        # Fichas
        st.subheader("Fichas")
        if editable and st.button("➕ Añadir nueva ficha"):
            # crear ficha con código F_xxx_año
            fid = generate_ficha_code(agr.get("anio", datetime.date.today().year))
            agr.setdefault("fichas",[]).append({
                "id": fid,
                "nombre": "",
                "tipo_meta": "Institucional",
                "responsables_cumpl": "",
                "objetivo": "",
                "indicador": "",
                "forma_calculo": "",
                "fuente": "",
                "valor_base": "",
                "responsables_seguimiento": "",
                "observaciones": "",
                "salvaguarda_flag": False,
                "salvaguarda_text": "",
                "metas": []
            })
            st.rerun()

        for fi in agr.get("fichas",[]):
            st.markdown("---")
            st.markdown(f"**Ficha {fi['id']}**")
            c1, c2, c3 = st.columns([2,2,1])
            fi["nombre"] = c1.text_input(f"Nombre de Ficha ({fi['id']})", value=fi.get("nombre",""), disabled=not editable)
            fi["tipo_meta"] = c2.selectbox(f"Tipo de meta ({fi['id']})", ["Institucional","Grupal/Sectorial","Individual"], index=["Institucional","Grupal/Sectorial","Individual"].index(fi.get("tipo_meta","Institucional")), disabled=not editable)
            if editable and c3.button("Borrar ficha", key=f"del_f_{fi['id']}"):
                agr["fichas"] = [x for x in agr["fichas"] if x["id"]!=fi["id"]]
                st.rerun()
            fi["responsables_cumpl"] = st.text_input(f"Responsable/s del cumplimiento ({fi['id']})", value=fi.get("responsables_cumpl",""), disabled=not editable)
            fi["objetivo"] = st.text_area(f"Objetivo ({fi['id']})", value=fi.get("objetivo",""), disabled=not editable)
            fi["indicador"] = st.text_input(f"Indicador ({fi['id']}) *", value=fi.get("indicador",""), disabled=not editable)
            fi["forma_calculo"] = st.text_area(f"Forma de cálculo ({fi['id']})", value=fi.get("forma_calculo",""), disabled=not editable)
            fi["fuente"] = st.text_input(f"Fuentes de información ({fi['id']}) *", value=fi.get("fuente",""), disabled=not editable)
            fi["valor_base"] = st.text_input(f"Valor base ({fi['id']})", value=fi.get("valor_base",""), disabled=not editable)
            fi["responsables_seguimiento"] = st.text_input(f"Responsables de seguimiento ({fi['id']})", value=fi.get("responsables_seguimiento",""), disabled=not editable)
            fi["observaciones"] = st.text_area(f"Observaciones ({fi['id']})", value=fi.get("observaciones",""), disabled=False)
            colS1, colS2 = st.columns([1,3])
            fi["salvaguarda_flag"] = colS1.checkbox(f"Salvaguarda ({fi['id']})", value=fi.get("salvaguarda_flag",False), disabled=not editable and not fi.get("salvaguarda_flag",False))
            fi["salvaguarda_text"] = colS2.text_input(f"Detalle salvaguarda ({fi['id']})", value=fi.get("salvaguarda_text",""), disabled=not (editable or fi.get("salvaguarda_flag",False)))
            st.markdown("**Metas**")
            if (editable or fi.get("salvaguarda_flag")) and st.button("➕ Añadir meta", key=f"add_meta_{fi['id']}"):
                fi.setdefault("metas",[]).append({
                    "id": gen_uuid("META"),
                    "unidad": "%",
                    "valor_objetivo": "",
                    "sentido": ">=",
                    "descripcion": "",
                    "frecuencia": "Anual",
                    "vencimiento": f"{agr.get('anio', datetime.date.today().year)}-12-31",
                    "es_hito": False,
                    "rango": [],
                    "ponderacion": 0.0,
                    "cumplimiento_valor": "",
                    "cumplimiento_calc": None,
                    "observaciones": ""
                })
            for me in fi.get("metas",[]):
                st.markdown(f"- Meta **{me['id']}**")
                cm1, cm2, cm3, cm4 = st.columns([1,1,1,1])
                me["unidad"] = cm1.text_input(f"Unidad ({me['id']})", value=me.get("unidad",""), disabled=not (editable or fi.get("salvaguarda_flag")))
                me["valor_objetivo"] = cm2.text_input(f"Valor objetivo ({me['id']})", value=me.get("valor_objetivo",""), disabled=not (editable or fi.get("salvaguarda_flag")))
                me["sentido"] = cm3.selectbox(f"Sentido ({me['id']})", [">=","<=","=="], index={">=":0,"<=":1,"==":2}[me.get("sentido",">=")], disabled=not (editable or fi.get("salvaguarda_flag")))
                me["frecuencia"] = cm4.selectbox(f"Frecuencia ({me['id']})", ["Trimestral","Semestral","Anual"], index={"Trimestral":0,"Semestral":1,"Anual":2}[me.get("frecuencia","Anual")], disabled=not (editable or fi.get("salvaguarda_flag")))
                me["descripcion"] = st.text_input(f"Descripción ({me['id']})", value=me.get("descripcion",""), disabled=not (editable or fi.get("salvaguarda_flag")))
                me["vencimiento"] = st.date_input(f"Vencimiento ({me['id']})", value=dt_parse(me.get("vencimiento")) or datetime.date(agr["anio"],12,31), disabled=not (editable or fi.get("salvaguarda_flag"))).isoformat()
                me["es_hito"] = st.checkbox(f"¿Es hito? ({me['id']})", value=me.get("es_hito",False), disabled=not (editable or fi.get("salvaguarda_flag")))
                st.caption("Rangos (min|max|pct separados por ';'). Para hitos, usar 1/0.")
                rango_list = me.get("rango", [])
                colr = st.columns([1,1,1,1,1])
                colr[0].markdown("**Mín**")
                colr[1].markdown("**Máx**")
                colr[2].markdown("**%**")
                colr[3].markdown("**Agregar**")
                colr[4].markdown("**Limpiar**")
                if (editable or fi.get("salvaguarda_flag")) and colr[3].button("➕", key=f"add_r_{me['id']}"):
                    rango_list.append({"min":"","max":"","porcentaje":""})
                if (editable or fi.get("salvaguarda_flag")) and colr[4].button("🗑️", key=f"clr_r_{me['id']}"):
                    rango_list.clear()
                for i, rg in enumerate(list(rango_list)):
                    cr = st.columns([1,1,1,1])
                    rg["min"] = cr[0].text_input(f"min_{me['id']}_{i}", value=str(rg.get("min","")))
                    rg["max"] = cr[1].text_input(f"max_{me['id']}_{i}", value=str(rg.get("max","")))
                    rg["porcentaje"] = cr[2].text_input(f"pct_{me['id']}_{i}", value=str(rg.get("porcentaje","")))
                    if (editable or fi.get("salvaguarda_flag")) and cr[3].button("Eliminar", key=f"delr_{me['id']}_{i}"):
                        rango_list.pop(i)
                me["rango"] = rango_list
                try:
                    me["ponderacion"] = float(st.number_input(f"Ponderación % ({me['id']})", value=float(me.get("ponderacion",0.0)), step=1.0, min_value=0.0, max_value=100.0, disabled=not (editable or fi.get("salvaguarda_flag"))))
                except:
                    me["ponderacion"] = 0.0
                me["cumplimiento_valor"] = st.text_input(f"Valor de cumplimiento ({me['id']})", value=me.get("cumplimiento_valor",""))
                me["cumplimiento_calc"] = calcular_cumplimiento(me)
                me["observaciones"] = st.text_input(f"Observaciones ({me['id']})", value=me.get("observaciones",""), disabled=False)
                if (editable or fi.get("salvaguarda_flag")) and st.button("Borrar meta", key=f"del_meta_{me['id']}"):
                    fi["metas"] = [m for m in fi["metas"] if m["id"]!=me["id"]]
                    st.rerun()
            validar_ponderaciones_ficha(fi, agr)

        # Flujo y acciones
        with st.expander("Flujo y Versionado", expanded=True):
            st.write(f"**Estado actual:** {agr.get('estado')}")
            colf1, colf2, colf3, colf4 = st.columns(4)
            if colf1.button("Guardar"):
                db[agr["id"]] = agr
                agreements_save(db)
                audit_log("save_agreement", {"id": agr["id"], "by": user["username"]})
                st.success("Guardado.")
            if user["role"] in ["Administrador","Responsable","Supervisor"] and agr.get("estado")=="Borrador":
                if colf2.button("Enviar a revisión (CSE/Comisión)"):
                    agr["estado"]="En revisión"
                    # snapshot
                    snap = json.loads(json.dumps(agr))
                    snap["snapshot_ts"] = datetime.datetime.now().isoformat()
                    agr.setdefault("versions",[]).append(snap)
                    agr["current_version"] = len(agr["versions"]) - 1
                    agreements_save(db)
                    audit_log("submit_for_review", {"id": agr["id"], "by": user["username"]})
                    st.success("Enviado a revisión.")
                    st.rerun()
            if user["role"] in ["Administrador","Comisión de CG"] and agr.get("estado")=="En revisión":
                if colf3.button("Aprobar (CCG)"):
                    agr["estado"]="Aprobado"
                    snap = json.loads(json.dumps(agr))
                    snap["snapshot_ts"] = datetime.datetime.now().isoformat()
                    agr.setdefault("versions",[]).append(snap)
                    agr["current_version"] = len(agr["versions"]) - 1
                    agreements_save(db)
                    audit_log("approve", {"id": agr["id"], "by": user["username"]})
                    st.success("Acuerdo Aprobado.")
                    st.rerun()
            if colf4.button("Crear snapshot manual"):
                snap = json.loads(json.dumps(agr))
                snap["snapshot_ts"] = datetime.datetime.now().isoformat()
                agr.setdefault("versions",[]).append(snap)
                agr["current_version"] = len(agr["versions"]) - 1
                agreements_save(db)
                st.info("Snapshot guardado.")
            st.markdown("**Historial de versiones (solo lectura):**")
            for i, snap in enumerate(agr.get("versions",[])):
                st.write(f"- Versión {i} - {snap.get('snapshot_ts','')}")
            if agr.get("versions"):
                vi = st.number_input("Ver versión", value=agr.get("current_version") or 0, step=1, min_value=0, max_value=max(0, len(agr.get("versions",[]))-1))
                if st.button("Mostrar versión"):
                    st.json(agr["versions"][int(vi)])

        # Import/Export masivo
        with st.expander("Carga/Descarga masiva (CSV)", expanded=False):
            # ...otros botones...
            colw, colc = st.columns(2)
        with colw:
            with open("FICHA_PARA_METAS_CG.docx", "rb") as f:
                st.download_button(
                    "Descargar plantilla Word",
                    data=f.read(),
                    file_name="FICHA_PARA_METAS_CG.docx",
                    key=f"tpl_word_{agr['id']}"
                )
        with colc:
            with open("FICHA_PARA_METAS_CG.csv", "rb") as f:
                st.download_button(
                    "Descargar plantilla CSV",
                    data=f.read(),
                    file_name="FICHA_PARA_METAS_CG.csv",
                    key=f"tpl_csv_{agr['id']}"
                )
           
            # Generar plantilla horizontal (legacy)
            sample_horiz = export_csv_horizontal_agreement(agr)
            st.download_button(
                "Descargar plantilla (horizontal) - filas por meta",
                data=sample_horiz.encode("utf-8"),
                file_name=f"{agr['id']}_plantilla_horizontal.csv",
                key=f"tpl_horiz_{agr['id']}"
            )

            upl = st.file_uploader("Subir CSV con fichas+metas (vertical u horizontal)", type=["csv"])
            if upl:
                try:
                    imported = detect_csv_format_and_import(upl.getvalue(), agr)
                    agreements_save(db)
                    st.success(f"Importadas/actualizadas {imported} metas (fichas creadas/actualizadas).")
                except Exception as e:
                    st.error(f"Error importando CSV: {e}")

            # Export vertical
            sample_vertical = export_csv_vertical_agreement_template()
            st.download_button(
                "Descargar plantilla (vertical) - 2 columnas",
                data=sample_vertical.encode("utf-8"),
                file_name=f"{agr['id']}_plantilla_vertical.csv",
                key=f"tpl_vert_{agr['id']}"
            )
            # Export horizontal (compatibilidad)
            csv_horiz = export_csv_horizontal_agreement(agr)
            st.download_button(
                "Descargar fichas+metas (CSV - horizontal)",
                data=csv_horiz.encode("utf-8"),
                file_name=f"{agr['id']}_fichas_metas_horizontal.csv",
                key=f"export_horiz_{agr['id']}"
            )

            # ZIP de adjuntos
            if st.button("Descargar adjuntos (ZIP)"):
                zip_bytes = io.BytesIO()
                with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
                    for att in agr.get("attachments",[]):
                        if os.path.exists(att.get("path","")):
                            zf.write(att["path"], arcname=os.path.basename(att["path"]))
                st.download_button(
                    "Descargar ZIP",
                    data=zip_bytes.getvalue(),
                    file_name=f"{agr['id']}_adjuntos.zip",
                    key=f"zip_att_{agr['id']}"
                )

        # Contrato (RTF)
        with st.expander("Generar Contrato (RTF - Anexo II)", expanded=False):
            rtf = generar_rtf_contrato(agr)
            fname = f"Contrato_{agr.get('organismo_nombre') or agr['id']}_{agr.get('anio')}.rtf"
            st.download_button(
                "Descargar Contrato RTF",
                data=rtf.encode("utf-8"),
                file_name=fname,
                key=f"rtf_{agr['id']}"
            )

def page_reportes():
    require_login()
    st.header("Reportes")
    db = agreements_load()
    if not db:
        st.info("No hay acuerdos.")
        return
    years = sorted({ a.get("anio", datetime.date.today().year) for a in db.values() })
    fy = st.selectbox("Año", options=years, index=len(years)-1)
    fo = st.text_input("Filtrar por Organismo (contiene)")
    ft = st.multiselect("Tipo de compromiso", options=TIPO_COMPROMISO, default=TIPO_COMPROMISO)
    total_cumpl_by_period: Dict[str, float] = {}
    total_pond_by_period: Dict[str, float] = {}
    for agr in db.values():
        if agr.get("anio") != fy or agr.get("tipo_compromiso") not in ft:
            continue
        if fo and fo.lower() not in (agr.get("organismo_nombre","") or "").lower():
            continue
        st.markdown("---")
        st.write(f"**{agr.get('organismo_nombre') or agr.get('id')}** --- {agr.get('tipo_compromiso')} --- Estado: {agr.get('estado')}")
        rows = []
        for f in agr.get("fichas",[]):
            for m in f.get("metas",[]):
                per = periodo_label(m)
                pond = float(m.get("ponderacion",0.0))
                cump = m.get("cumplimiento_calc")
                if cump is not None:
                    total_cumpl_by_period[per] = total_cumpl_by_period.get(per,0.0) + pond * (float(cump)/100.0)
                    total_pond_by_period[per] = total_pond_by_period.get(per,0.0) + pond
                rows.append({
                    "Ficha": f.get("nombre") or f.get("id"),
                    "Indicador": f.get("indicador",""),
                    "Meta": m.get("descripcion",""),
                    "Frecuencia": m.get("frecuencia",""),
                    "Vencimiento": m.get("vencimiento",""),
                    "Ponderación %": pond,
                    "Cumplimiento %": cump,
                })
        if rows:
            colnames = ["Ficha","Indicador","Meta","Frecuencia","Vencimiento","Ponderación %","Cumplimiento %"]
            st.write("| " + " | ".join(colnames) + " |")
            st.write("|" + "|".join(["---"]*len(colnames)) + "|")
            for r in rows:
                st.write("| " + " | ".join([str(r[c]) for c in colnames]) + " |")
    st.markdown("### Cumplimiento total por período (ponderado)")
    if total_pond_by_period:
        for per in sorted(total_pond_by_period.keys()):
            pond = total_pond_by_period[per]
            val = total_cumpl_by_period.get(per,0.0)
            total_pct = 0.0 if pond==0 else (val/pond)*100.0
            st.write(f"- {per}: **{total_pct:.2f}%** (ponderación total {pond:.1f})")
    else:
        st.info("No hay datos de cumplimiento.")
    if st.button("Descargar consolidado CSV"):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Periodo","Ponderación total","Cumplimiento total (%)"])
        for per in sorted(total_pond_by_period.keys()):
            pond = total_pond_by_period[per]
            val = total_cumpl_by_period.get(per,0.0)
            total_pct = 0.0 if pond==0 else (val/pond)*100.0
            w.writerow([per, pond, f"{total_pct:.2f}"])
        st.download_button(
            "Descargar", 
            data=buf.getvalue().encode("utf-8"),
            file_name="consolidado_cumplimiento.csv",
            key=f"consol_{int(time.time())}"
        )

# Generación RTF (contrato)
def generar_rtf_contrato(agr: Dict[str,Any]) -> str:
    org = agr.get("organismo_nombre","________________")
    anio = agr.get("anio", "_____")
    vig_desde = agr.get("vigencia_desde", f"{anio}-01-01")
    vig_hasta = agr.get("vigencia_hasta", f"{anio}-12-31")
    normativa = agr.get("normativa_especifica","")
    body = rf"""
{{\rtf1\ansi\deff0
\b COMPROMISO DE GESTIÓN entre el Poder Ejecutivo y {org}\b0\line
AÑO {anio}\line\line
\b Tipo de Compromiso:\b0 {agr.get('tipo_compromiso','Institucional')}\line
\b Período de vigencia del CG:\b0 {vig_desde} -- {vig_hasta}\line
\b Normativa específica:\b0 {normativa}\line\line
\b Cláusula 3ra. Objeto.\b0\line
El objeto de este compromiso de gestión es fijar, de común acuerdo, metas e indicadores (...)\line\line
\b Cláusula 6ta. Compromisos de las partes.\b0\line
Se compromete a cumplir con las siguientes metas (ver anexo de fichas/metas).\line\line
\b Cláusula 7ma. Forma de pago del subsidio.\b0\line
(Ver modelo y condiciones según Anexo II y resoluciones vigentes.)\line\line
\b Cláusula 8va. Comisión de Seguimiento y Evaluación.\b0\line
(Integrantes según define el organismo y CCG.)\line\line
\b Cláusula 10ma. Salvaguardas y excepciones.\b0\line
(Conforme a lo establecido para ajustes de metas por fuerza mayor.)\line\line
\b Firmas:\b0\line\line\line
________________________________\line
Poder Ejecutivo\line\line
________________________________\line
{org}\line
}}
"""
    return body

# Sidebar y router
def sidebar():
    st.sidebar.title("Menú")
    if st.session_state.user:
        st.sidebar.write(f"👤 {st.session_state.user.get('name','')} --- {st.session_state.user['role']}")
        choice = st.sidebar.radio("Ir a", ["Inicio","Acuerdos","Reportes"] + (["Administración"] if st.session_state.user["role"]=="Administrador" else []))
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.user = None
            st.rerun()
        return choice
    else:
        return "Login"

def page_home():
    require_login()
    header_with_logo()
    st.title(APP_TITLE)
    st.success(f"Usuario: {st.session_state.user.get('name','')} ({st.session_state.user['role']})")
    st.write("Usa el menú lateral para navegar.")

def main():
    page = sidebar()
    if page == "Login":
        page_login()
    elif page == "Inicio":
        page_home()
    elif page == "Acuerdos":
        page_agreements()
    elif page == "Reportes":
        page_reportes()
    elif page == "Administración":
        page_admin()
    else:
        page_home()

if __name__ == "__main__":
    main()
