# app.py - VERSIÓN CORREGIDA CON MANEJO DE PERMISOS

# IMPORTS CORREGIDOS 
import streamlit as st
import sys
import os
import json
import hashlib
import pandas as pd
import secrets
import csv
import io
import zipfile
import shutil
import uuid
import tempfile
import base64
import time  # ← ESTE DEBE ESTAR ANTES DE datetime
import warnings
import webbrowser
from typing import List, Dict, Any, Optional

# 📌 SOLO UN IMPORT DE DATETIME - ELIMINA "import datetime"
from datetime import datetime, timedelta, date  # ← ESTE ES EL CORRECTO
# 👉 IMPORT DEL MÓDULO NUEVO (ACÁ)
from ponderaciones import calcular_ponderaciones_ficha, calcular_aportes

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*MediaFileStorageError.*")

# ==================== PROTECCIÓN ANTI-PROBLEMAS FUTUROS ====================
sys.dont_write_bytecode = True  # 🔥 EVITA .pyc

# ================= CONFIGURACIÓN METODOLÓGICA =================

CONFIG_METODOLOGIA = {
    "cumplimiento": {
        "valor_maximo": 100
    },
    "riesgo": {
        "umbral_bajo_cumplimiento": 50,
        "peso_meta_riesgo": 10,
        "peso_acuerdo_activo": 5
    }
}


def safe_print(msg):
    """Print safely to console replacing characters that can't be encoded in the terminal encoding."""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            # Prefer writing bytes to stdout buffer
            sys.stdout.buffer.write(str(msg).encode('utf-8', errors='replace'))
            sys.stdout.buffer.write(b"\n")
        except Exception:
            try:
                # Fallback: print a best-effort decoded string
                print(str(msg).encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
            except Exception:
                pass

def limpiar_cache_streamlit():
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
        
        posibles_rutas = [
            os.path.expanduser("~/.streamlit/cache"),
            os.path.expanduser("~/.cache/streamlit"),
            "./.streamlit/cache",
        ]
        
        for ruta in posibles_rutas:
            if os.path.exists(ruta):
                shutil.rmtree(ruta)
                safe_print(f"✅ Eliminada carpeta cache: {ruta}")
                
        safe_print("✅ Cache limpiado completamente")
        
    except Exception as e:
        safe_print(f"⚠️ Error limpiando cache: {e}")

limpiar_cache_streamlit()

# ==================== CONFIGURACIÓN DIRECTA ====================
DATA_DIR = "datos_sistema"
os.makedirs(DATA_DIR, exist_ok=True)  # 📁 CREA DIRECTORIO SIN MIGRACIÓN

# PROTECCIÓN CONTRA TRADUCCIÓN MEJORADA
st.markdown("""
<meta name="google" content="notranslate">
<meta name="google" content="nopagerecrawl">
<meta http-equiv="Content-Language" content="es">
<script>
// Forzar no traducción
if (window.google && google.translate) {
    google.translate.TranslateElement = null;
}
document.documentElement.lang = 'es';
document.addEventListener('DOMContentLoaded', function() {
    var meta = document.createElement('meta');
    meta.name = 'google';
    meta.content = 'notranslate';
    document.head.appendChild(meta);
});
</script>
<style>
.translated-ltr, .translated-rtl, .skiptranslate {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# 🔹 Constantes de configuración - VERSIÓN CORREGIDA
APP_TITLE = "Sistema de Compromisos de Gestión"

# 🚀 MIGRACIÓN A DIRECTORIO PERSISTENTE
import shutil
OLD_DATA_DIR = os.path.join(tempfile.gettempdir(), "sistema_cg_data")
DATA_DIR = os.path.join(os.getcwd(), "sistema_cg_datos_definitivos")

# Asegurar que el directorio de datos existe
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "usuarios.json")
AGREEMENTS_FILE = os.path.join(DATA_DIR, "agreements.json")
AUDIT_FILE = os.path.join(DATA_DIR, "audit.json")
NATURALEZA_MAP_FILE = os.path.join(DATA_DIR, "naturaleza_map.json")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
COUNTERS_FILE = os.path.join(DATA_DIR, "counters.json")
LOGO_FILES = ["logotipo_opp.png", "logotipo.png"]
# 🆕 RANGOS POR DEFECTO FLEXIBLES 
RANGOS_DEFAULT = {"cumplido": 90, "parcial": 60}

# 🆕 CONSTANTES PARA TIPOS DE CG
TIPOS_CG = ["Institucional", "Funcional"]
CATEGORIAS_FUNCIONALES = ["Institucional", "Grupal", "Individual"]
PONDERACIONES_SUGERIDAS = {
    "Institucional": 30.0,
    "Grupal": 50.0, 
    "Individual": 20.0
}

# 🆕 INICIALIZACIÓN MEJORADA DE DIRECTORIOS
def initialize_directories():
    """Inicializa todos los directorios necesarios con verificación de permisos"""
    
    # 🚀 MOSTRAR INFORMACIÓN DE MIGRACIÓN
    if os.path.exists(OLD_DATA_DIR) and DATA_DIR != OLD_DATA_DIR:
        st.sidebar.success(f"✅ Datos migrados a: {DATA_DIR}")
    
    directories = [DATA_DIR, UPLOADS_DIR, 'data', 'reportes']
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            # 🆕 VERIFICAR PERMISOS DE ESCRITURA
            test_file = os.path.join(directory, f"test_write_{int(time.time())}.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            st.error(f"❌ Error creando directorio {directory}: {e}")
            return False
    return True

# 🆕 EJECUTAR INICIALIZACIÓN Y GUARDAR RESULTADO
PERSIST_OK = initialize_directories()

if not PERSIST_OK:
    st.error("❌ Error crítico: No se pudieron crear los directorios necesarios")

if "show_import_export" not in st.session_state:
    st.session_state.show_import_export = False

if "mostrar_vista_previa" not in st.session_state:
    st.session_state.mostrar_vista_previa = False

# 🆕 DIAGNÓSTICO PARA ADMINISTRADORES - AGREGAR AQUÍ

# 🆕 FUNCIÓN DE DIAGNÓSTICO DE PERMISOS

def check_permissions():
    """Verifica permisos y muestra información de diagnóstico en el sidebar"""
    try:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔧 Diagnóstico del Sistema")
        
        # 🚀 INFORMACIÓN DE MIGRACIÓN (AGREGAR ESTO)
        st.sidebar.write(f"**📁 Directorio persistente:** `{DATA_DIR}`")
        if OLD_DATA_DIR != DATA_DIR and os.path.exists(OLD_DATA_DIR):
            st.sidebar.info(f"**📂 Directorio temporal anterior:** `{OLD_DATA_DIR}`")

        # Información de rutas y permisos
        st.sidebar.write(f"**Directorio data:** `{DATA_DIR}`")
        st.sidebar.write(f"**Directorio actual:** `{os.getcwd()}`")
        st.sidebar.write(f"**Usuario OS:** `{os.getlogin() if hasattr(os, 'getlogin') else 'N/A'}`")
        
        # Verificar permisos de escritura
        can_write = False
        try:
            test_file = os.path.join(DATA_DIR, "test_permission.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            can_write = True
        except PermissionError:
            can_write = False
        
        if can_write:
            st.sidebar.success("✅ Permisos de escritura: OK")
        else:
            st.sidebar.error("❌ Permisos de escritura: DENEGADO")
        
        # Verificar existencia de archivos críticos
        st.sidebar.markdown("**Archivos del sistema:**")
        critical_files = [
            (USERS_FILE, "Usuarios"),
            (AGREEMENTS_FILE, "Acuerdos"), 
            (COUNTERS_FILE, "Contadores"),
            (AUDIT_FILE, "Auditoría")
        ]
        
        for file_path, description in critical_files:
            exists = os.path.exists(file_path)
            size = os.path.getsize(file_path) if exists else 0
            status = "✅" if exists else "❌"
            st.sidebar.write(f"{status} {description}: {os.path.basename(file_path)} ({size} bytes)")
        
        # Información del almacenamiento
        if os.path.exists(DATA_DIR):
            total_size = 0
            total_files = 0
            for dirpath, dirnames, filenames in os.walk(DATA_DIR):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
                    total_files += 1
            
            st.sidebar.markdown("**Uso de almacenamiento:**")
            st.sidebar.write(f"📁 Archivos: {total_files}")
            st.sidebar.write(f"💾 Espacio: {total_size / 1024 / 1024:.2f} MB")
        
        # Botón para forzar verificación
        if st.sidebar.button("🔄 Actualizar diagnóstico", key="refresh_diagnostic"):
            st.rerun()
            
        # Botón para reparar permisos (solo si hay problemas)
        if not can_write:
            if st.sidebar.button("🔧 Intentar reparar permisos", key="fix_permissions"):
                try:
                    # Intentar crear la carpeta data con permisos amplios
                    os.makedirs(DATA_DIR, exist_ok=True)
                    # Dar permisos de escritura
                    if os.name == 'nt':  # Windows
                        os.system(f'icacls "{DATA_DIR}" /grant Everyone:F')
                    st.success("Reparación intentada. Recargue la página.")
                except Exception as e:
                    st.error(f"Error en reparación: {e}")

        # DIAGNÓSTICO DE PERMISOS DE USUARIO
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔐 Diagnóstico de Permisos")
        
        usuario_actual = st.session_state.user
        if usuario_actual:
            rol = usuario_actual["role"]
            st.sidebar.write(f"**Rol del usuario:** {rol}")
            
            # Estados del sistema
            estados = ["Borrador", "Pendiente de Revisión", "En Revisión OPP", "En Revisión Comisión CG", "Aprobado", "Rechazado", "Archivado"]
            
            for estado in estados:
                acciones = permisos_sistema.obtener_acciones_permitidas(rol, estado)
                puede_cambiar = []
                
                # Verificar a qué estados puede cambiar desde este estado
                for estado_destino in estados:
                    if estado_destino != estado and puede_cambiar_estado(estado, estado_destino, rol):
                        puede_cambiar.append(estado_destino)
                
                st.sidebar.write(f"**{estado}:**")
                st.sidebar.write(f"  Acciones: {', '.join(acciones) if acciones else 'NINGUNA'}")
                if puede_cambiar:
                    st.sidebar.write(f"  Puede cambiar a: {', '.join(puede_cambiar)}")
                st.sidebar.write("")  # Espacio entre estados

    except Exception as e:
        st.sidebar.error(f"Error en diagnóstico: {e}")

def cargar_indicadores_json():
    """Carga los indicadores desde el archivo JSON con manejo de errores"""
    try:
        with open("data/indicadores.json", "r", encoding='utf-8') as f:
            datos = json.load(f)
            
        # Verificar estructura del archivo
        if not isinstance(datos, dict) or "indicadores" not in datos:
            # Si la estructura es incorrecta, crear una nueva
            datos = {
                "indicadores": [],
                "metadata": {
                    "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total": 0
                }
            }

            guardar_indicadores_json(datos)
            st.warning("⚠️ Estructura de archivo corregida")
            
        return datos
        
    except (FileNotFoundError, json.JSONDecodeError):
        # Si el archivo no existe o está corrupto, crear uno nuevo
        datos = {
            "indicadores": [],
            "metadata": {
                "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total": 0
            }
        }
        guardar_indicadores_json(datos)
        st.info("📁 Archivo de indicadores creado nuevo")
        return datos

def guardar_indicadores_json(datos):
    """Guarda indicadores en JSON"""
    datos["metadata"]["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos["metadata"]["total"] = len(datos["indicadores"])
    with open('data/indicadores.json', 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def cargar_indicadores():
    """Interfaz para cargar nuevos indicadores"""
    st.header("📥 Carga de Nuevos Indicadores")

    # 🆕 CARGAR ACUERDOS PARA VINCULACIÓN
    db = agreements_load()
    acuerdos_lista = list(db.values()) if db else []
    
    # 🆕 SECCIÓN PARA ELIMINAR INDICADORES EXISTENTES
    st.subheader("🗑️ Eliminar Indicadores Existentes")
    datos = cargar_indicadores_json()
    
    if datos["indicadores"]:
        # Mostrar indicadores existentes con opción de eliminar
        for indicador in datos["indicadores"]:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{indicador['nombre']}** - Valor: {indicador['valor']} - Fecha: {indicador['fecha']}")
            with col2:
                if st.button("👁️", key=f"view_{indicador['id']}", help="Ver detalles"):
                    st.json(indicador)
            with col3:
                if st.button("🗑️", key=f"delete_{indicador['id']}", help="Eliminar indicador"):
                    # Eliminar el indicador
                    datos["indicadores"] = [ind for ind in datos["indicadores"] if ind['id'] != indicador['id']]
                    # Actualizar metadata
                    datos["metadata"]["total"] = len(datos["indicadores"])
                    datos["metadata"]["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # Guardar cambios
                    guardar_indicadores_json(datos)
                    st.success(f"✅ Indicador '{indicador['nombre']}' eliminado")
                    st.rerun()
        
        st.markdown("---")
    
    # 🆕 FORMULARIO MEJORADO CON VINCULACIÓN A ACUERDOS
    with st.form("form_carga_indicadores"):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre del Indicador*")
            valor = st.number_input("Valor*", min_value=0.0, step=0.1)
            meta = st.number_input("Meta", min_value=0.0, step=0.1)
            
        with col2:
            unidad = st.selectbox("Unidad de Medida", ["", "%", "unidades", "pesos", "horas", "días", "personas"])
            fecha = st.date_input("Fecha de medición")
            departamento = st.selectbox("Departamento", ["", "Ventas", "Producción", "Calidad", "Logística", "RH", "TI"])
            
        # 🆕 SECCIÓN DE VINCULACIÓN CON ACUERDOS
        if acuerdos_lista:
            st.subheader("🔗 Vincular a Acuerdo (Opcional)")
            acuerdo_options = ["No vincular"] + [a["id"] for a in acuerdos_lista]
            acuerdo_seleccionado = st.selectbox(
                "Seleccionar acuerdo",
                options=acuerdo_options,
                format_func=lambda x: "No vincular" if x == "No vincular" else f"{x} - {db[x].get('organismo_nombre', 'Sin nombre')}"
            )
        else:
            acuerdo_seleccionado = "No vincular"
            
        comentarios = st.text_area("Comentarios")
        
        if st.form_submit_button("💾 Guardar Indicador"):
            if nombre and valor is not None:
                datos = cargar_indicadores_json()
                
                # Generar nuevo ID
                if datos["indicadores"]:
                    nuevo_id = max(ind['id'] for ind in datos["indicadores"]) + 1
                else:
                    nuevo_id = 1
                
                nuevo_indicador = {
                    "id": nuevo_id,
                    "nombre": nombre,
                    "valor": float(valor),
                    "meta": float(meta) if meta else None,
                    "unidad": unidad,
                    "departamento": departamento,
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "comentarios": comentarios,
                    "timestamp": datetime.now().isoformat(),
                    "acuerdo_id": acuerdo_seleccionado if acuerdo_seleccionado != "No vincular" else ""  # 🆕 VINCULACIÓN
                }
                
                datos["indicadores"].append(nuevo_indicador)
                datos["metadata"]["total"] = len(datos["indicadores"])
                datos["metadata"]["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                guardar_indicadores_json(datos)
                st.success(f"✅ Indicador '{nombre}' guardado exitosamente")
                st.rerun()
            else:
                st.error("❌ Nombre y valor son obligatorios")

def generar_indicadores_desde_metas(acuerdo):
    """Genera indicadores automáticamente desde las metas de las fichas"""
    
    indicadores_generados = []
    
    for ficha in acuerdo.get('fichas', []):
        ficha_nombre = ficha.get('nombre', '')
        ficha_indicador = ficha.get('indicador', '')
        
        # Crear indicador principal de la ficha
        if ficha_indicador:
            indicador_principal = {
                'id': f"IND_{acuerdo['id']}_{ficha['id']}",
                'nombre': f"{ficha_indicador} - {ficha_nombre}",
                'tipo': 'Principal',
                'meta': 100,  # Meta del 100% de cumplimiento
                'unidad_medida': '%',
                'ficha_id': ficha['id'],
                'acuerdo_id': acuerdo['id'],
                'fecha_creacion': datetime.now().isoformat(),
                'automatico': True
            }
            indicadores_generados.append(indicador_principal)
        
        # Crear indicadores para cada meta
        for meta in ficha.get('metas', []):
            indicador_meta = {
                'id': f"IND_{acuerdo['id']}_{ficha['id']}_M{meta['numero']}",
                'nombre': f"Meta {meta['numero']} - {meta.get('descripcion', '')}",
                'tipo': 'Meta Específica',
                'meta': float(meta.get('valor_objetivo', 100)),
                'unidad_medida': meta.get('unidad', 'unidades'),
                'ficha_id': ficha['id'],
                'meta_id': meta['id'],
                'acuerdo_id': acuerdo['id'],
                'ponderacion': float(meta.get('ponderacion', 0)),
                'fecha_creacion': datetime.now().isoformat(),
                'automatico': True
            }
            indicadores_generados.append(indicador_meta)
    
    return indicadores_generados

def actualizar_indicadores_desde_metas(acuerdo, datos_indicadores, todas_las_metas=None):
    """Actualiza indicadores desde las metas"""
    
    safe_print("🚨 DEBUG: EJECUTANDO actualizar_indicadores_desde_metas")
    
    # 🆕 CORREGIR METAS SIN NOMBRE PRIMERO
    acuerdo = corregir_metas_sin_nombre(acuerdo)
    
    # 🆕 EXTRAER METAS (SOLO UNA VEZ)
    if todas_las_metas is None:
        safe_print("🔍 DEBUG: Extrayendo metas del acuerdo")
        todas_las_metas = []
        for ficha in acuerdo.get('fichas', []):
            todas_las_metas.extend(ficha.get('metas', []))
    else:
        safe_print(f"🔍 DEBUG: Metas recibidas como parámetro: {len(todas_las_metas)}")
    
    safe_print(f"🔍 DEBUG: Total metas a procesar: {len(todas_las_metas)}")
    
    if not todas_las_metas:
        safe_print("🔍 DEBUG: No hay metas para procesar")
        return datos_indicadores
    
    # Calcular factor de normalización
    suma_ponderaciones = sum(meta.get('ponderacion', 0) for meta in todas_las_metas)
    factor_normalizacion = 1.0 if suma_ponderaciones == 0 else 100.0 / suma_ponderaciones
    
    safe_print(f"🔍 DEBUG: Factor normalización = {factor_normalizacion}")
    
    # 🆕 BUSCAR INDICADORES EXISTENTES Y ACTUALIZAR NOMBRES
    indicadores_actualizados = []
    creados = 0
    actualizados = 0
    
    for meta in todas_las_metas:
        # 🆕 Calcular y anotar cumplimiento calculado para la meta
        try:
            cumpl_calc = calcular_cumplimiento(meta)
            if cumpl_calc is not None:
                meta['cumplimiento_calc'] = round(cumpl_calc, 2)
        except Exception:
            meta['cumplimiento_calc'] = None
        # 🆕 BUSCAR SI YA EXISTE UN INDICADOR PARA ESTA META
        indicador_existente = None
        for ind in datos_indicadores.get('indicadores', []):
            if ind.get('meta_id') == meta.get('id'):
                indicador_existente = ind
                break
        
        if indicador_existente:
            # ✅ ACTUALIZAR INDICADOR EXISTENTE
            indicador = indicador_existente
            indicador['nombre'] = meta.get('nombre', 'Sin nombre')
            indicador['ponderacion'] = round(meta.get('ponderacion', 0) * factor_normalizacion, 2)
            # 🆕 ACTUALIZAR VALORES DE CUMPLIMIENTO
            indicador['valor'] = meta.get('cumplimiento_valor', 0)  # ← VALOR REAL
            indicador['meta'] = meta.get('valor_objetivo', 1)       # ← VALOR META
            actualizados += 1
        else:
            # ✅ CREAR NUEVO INDICADOR
            ponderacion_normalizada = meta.get('ponderacion', 0) * factor_normalizacion
            indicador = {
                'id': meta.get('id', f"ind_{hash(str(meta))}"),
                'nombre': meta.get('nombre', 'Sin nombre'),
                'ponderacion': round(ponderacion_normalizada, 2),
                'valor': meta.get('cumplimiento_valor', 0),  # 🆕 VALOR REAL
                'meta': meta.get('valor_objetivo', 1),       # 🆕 VALOR META
                'valor_objetivo': meta.get('valor_objetivo', 0),
                'unidad': meta.get('unidad', ''),
                'frecuencia': meta.get('frecuencia', 'Anual'),
                'meta_id': meta.get('id', ''),
                'ficha_nombre': '...',
                'acuerdo_origen': acuerdo.get('id', '')
            }
        
        indicadores_actualizados.append(indicador)
        if not indicador_existente:
            creados += 1

    # VERIFICAR TOTAL NORMALIZADO
    total_normalizado = sum(ind['ponderacion'] for ind in indicadores_actualizados)
    safe_print(f"🔍 DEBUG: Total ponderación normalizada: {total_normalizado}%")
    
    # ACTUALIZAR DATOS
    datos_indicadores['indicadores'] = indicadores_actualizados

    # Actualizar metadata con resumen de cambios
    if 'metadata' not in datos_indicadores or not isinstance(datos_indicadores['metadata'], dict):
        datos_indicadores['metadata'] = {}
    datos_indicadores['metadata']['automaticos'] = creados + actualizados
    datos_indicadores['metadata']['ultima_actualizacion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    safe_print(f"🔍 DEBUG: Indicadores actualizados: {len(indicadores_actualizados)} (creados={creados}, actualizados={actualizados})")
    return datos_indicadores

# 🆕 🆕 🆕 FUNCIÓN DE CÁLCULO AUTOMÁTICO DE PONDERACIONES 🆕 🆕 🆕
# ⚠️ DEPRECATED
# Reemplazado por:
#   for ficha in acuerdo["fichas"]:
#       calcular_ponderaciones_ficha(ficha)
def calcular_ponderaciones_automaticas(acuerdo: Dict[str, Any]) -> Dict[str, Any]:
    """
    ⚠️ DEPRECATED.
    No usar.
    Reemplazado por calcular_ponderaciones_ficha (módulo ponderaciones.py).
    Se mantiene solo por compatibilidad histórica.
    """
    ...
            
    # 🆕 VERIFICAR ESTADO - SOLO MODIFICAR SI ESTÁ EN BORRADOR
    estado = acuerdo.get('estado', 'Borrador')
    if estado != 'Borrador':
        st.warning(f"⚠️ Acuerdo en estado '{estado}' - No se modifican ponderaciones automáticamente")
        return acuerdo
    
    # 🆕 CREAR UNA COPIA MODIFICABLE DEL ACUERDO
    acuerdo_modificado = acuerdo.copy()
    
    for ficha_idx, ficha in enumerate(acuerdo_modificado.get('fichas', [])):
        if 'metas' not in ficha:
            continue
                    
        # 🆕 MODIFICAR DIRECTAMENTE LAS METAS EN EL ACUERDO
        for meta_idx, meta in enumerate(ficha['metas']):
            # 🎯 FÓRMULA SIMPLIFICADA PARA PRUEBA
            ponderacion_simple = 100.0 / len(ficha['metas'])
                                    
            # MODIFICAR DIRECTAMENTE EN EL ACUERDO
            acuerdo_modificado['fichas'][ficha_idx]['metas'][meta_idx]['ponderacion'] = round(ponderacion_simple, 2)
                
    return acuerdo_modificado


# ⚠️ DEPRECATED
# Reemplazado por cálculo normativo en ponderaciones.py
def distribuir_ponderaciones_por_tipo(acuerdo: Dict[str, Any]) -> Dict[str, Any]:
    """
    ⚠️ DEPRECATED.
    No usar desde UI ni lógica principal.
    El cálculo debe realizarse por ficha mediante calcular_ponderaciones_ficha.
    """
    ...
   
    import copy
    agr_mod = copy.deepcopy(acuerdo)

    # Helper para mapear tipos a keys en PONDERACIONES_SUGERIDAS
    def tipo_a_key(tipo_raw: str) -> str:
        if not tipo_raw:
            return 'Institucional'
        t = str(tipo_raw).strip().lower()
        if 'grupal' in t or 'sectorial' in t:
            return 'Grupal'
        if 'individual' in t:
            return 'Individual'
        return 'Institucional'

    for ficha in agr_mod.get('fichas', []):
        metas = ficha.get('metas', [])
        if not metas:
            continue

        # Agrupar metas por periodo
        metas_por_periodo = {}
        for m in metas:
            periodo = periodo_label(m)
            metas_por_periodo.setdefault(periodo, []).append(m)

        # Procesar cada periodo independiente
        for periodo, metas_periodo in metas_por_periodo.items():
            # Respetar ponderaciones manuales ya asignadas (>0). Solo distribuir entre metas sin ponderación.
            manual_total = 0.0
            manual_assigned = []
            to_assign = []
            for m in metas_periodo:
                pval = float(m.get('ponderacion', 0) or 0)
                if pval > 0:
                    manual_total += pval
                    manual_assigned.append((m, pval))
                else:
                    to_assign.append(m)

            remaining_pct = max(0.0, 100.0 - manual_total)

            # Si no hay metas a asignar, solo ajustar redondeo si hace falta
            if not to_assign:
                # Ajustar si manual_total no suma 100
                if abs(manual_total - 100.0) > 0.01 and manual_assigned:
                    # normalizar manuales proporcionalmente
                    factor_norm = 100.0 / manual_total if manual_total > 0 else 0
                    for m, orig in manual_assigned:
                        m['ponderacion'] = round(orig * factor_norm, 2)
                continue

            # Calcular pesos base solo para metas sin ponderacion
            base_weights = []
            for m in to_assign:
                tipo = m.get('tipo_meta') or m.get('categoria_funcional') or ''
                key = tipo_a_key(tipo)
                pct = PONDERACIONES_SUGERIDAS.get(key, 30.0) / 100.0
                base_weights.append(pct)

            total_base = sum(base_weights)
            if total_base == 0:
                # repartir equitativamente entre no-asignadas
                per = round(remaining_pct / len(to_assign), 2) if to_assign else 0
                for m in to_assign:
                    m['ponderacion'] = per
            else:
                factor = remaining_pct / total_base
                assigned = [round(bw * factor, 2) for bw in base_weights]

                # Ajustar residuo por redondeo
                residuo = round(remaining_pct - sum(assigned), 2)
                if abs(residuo) >= 0.01 and len(assigned) > 0:
                    assigned[0] = round(assigned[0] + residuo, 2)

                for m, p in zip(to_assign, assigned):
                    m['ponderacion'] = p

            # Finalmente, si hay manuales, asegurar que sum total sea 100 (ajustar el primero)
            total_period = sum(float(x.get('ponderacion', 0) or 0) for x in metas_periodo)
            if abs(total_period - 100.0) > 0.01 and metas_periodo:
                diff = round(100.0 - total_period, 2)
                metas_periodo[0]['ponderacion'] = round(float(metas_periodo[0].get('ponderacion', 0) or 0) + diff, 2)

    return agr_mod

def componente_firma_imagen(key_suffix="", acuerdo=None):
    """Subir imagen escaneada de firma y retornar datos completos incluyendo imagen en base64"""
    
    st.markdown("**✍️ Firma Digitalizada**")
    
    # 🆕 INICIALIZAR session_state si no existe
    if f'firma_{key_suffix}' not in st.session_state:
        st.session_state[f'firma_{key_suffix}'] = {
            'nombre': '', 'cargo': '', 'institucion': '', 'imagen_base64': None
        }
    
    # Subir imagen de firma
    firma_imagen = st.file_uploader(
        "Subir imagen de firma escaneada", 
        type=['png', 'jpg', 'jpeg'],
        key=f"upload_firma_{key_suffix}",
        help="Suba una imagen PNG/JPG de su firma escaneada"
    )
    
    # Convertir imagen a base64 para guardar
    imagen_base64 = None
    if firma_imagen:
        try:
            imagen_bytes = firma_imagen.getvalue()
            imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
            st.image(firma_imagen, width=200, caption="Vista previa de la firma")
            st.success("✅ Imagen de firma cargada correctamente")
            
            # 🆕 ACTUALIZAR SESSION_STATE CON LA IMAGEN
            st.session_state[f'firma_{key_suffix}']['imagen_base64'] = imagen_base64
            st.session_state[f'firma_{key_suffix}']['nombre_archivo_firma'] = firma_imagen.name
            st.session_state[f'firma_{key_suffix}']['tiene_imagen_firma'] = True
            
        except Exception as e:
            st.error(f"❌ Error al procesar la imagen: {e}")
    
    # 🆕 DATOS DEL FIRMANTE CON session_state
    nombre = st.text_input(
        "Nombre completo*", 
        value=st.session_state[f'firma_{key_suffix}']['nombre'],
        key=f"nombre_{key_suffix}",
        on_change=lambda: st.session_state[f'firma_{key_suffix}'].update({
            'nombre': st.session_state[f"nombre_{key_suffix}"]
        })
    )
    
    cargo = st.text_input(
        "Cargo*", 
        value=st.session_state[f'firma_{key_suffix}']['cargo'],
        key=f"cargo_{key_suffix}",
        on_change=lambda: st.session_state[f'firma_{key_suffix}'].update({
            'cargo': st.session_state[f"cargo_{key_suffix}"]
        })
    )
    
    institucion = st.text_input(
        "Institución*", 
        value=st.session_state[f'firma_{key_suffix}']['institucion'],
        key=f"institucion_{key_suffix}",
        on_change=lambda: st.session_state[f'firma_{key_suffix}'].update({
            'institucion': st.session_state[f"institucion_{key_suffix}"]
        })
    )
    
    # 🆕 CARGAR DATOS DESDE FIRMAS GUARDADAS SI EXISTEN (solo si se pasa el acuerdo)
    if acuerdo and acuerdo.get("firmas", {}).get(key_suffix):
        datos_guardados = acuerdo["firmas"][key_suffix]
        
        # Solo actualizar si no hay datos actuales
        if not st.session_state[f'firma_{key_suffix}']['nombre'] and datos_guardados.get('nombre'):
            st.session_state[f'firma_{key_suffix}']['nombre'] = datos_guardados['nombre']
        if not st.session_state[f'firma_{key_suffix}']['cargo'] and datos_guardados.get('cargo'):
            st.session_state[f'firma_{key_suffix}']['cargo'] = datos_guardados['cargo']
        if not st.session_state[f'firma_{key_suffix}']['institucion'] and datos_guardados.get('institucion'):
            st.session_state[f'firma_{key_suffix}']['institucion'] = datos_guardados['institucion']
        if not st.session_state[f'firma_{key_suffix}']['imagen_base64'] and datos_guardados.get('imagen_base64'):
            st.session_state[f'firma_{key_suffix}']['imagen_base64'] = datos_guardados['imagen_base64']
    
    # 🆕 MOSTRAR RESUMEN DE LO QUE SE GUARDARÁ
    if (st.session_state[f'firma_{key_suffix}']['imagen_base64'] or 
        st.session_state[f'firma_{key_suffix}']['nombre'] or 
        st.session_state[f'firma_{key_suffix}']['cargo'] or 
        st.session_state[f'firma_{key_suffix}']['institucion']):
        
        with st.expander("📋 Resumen de datos a guardar", expanded=False):
            st.write(f"**Imagen cargada:** {'✅ Sí' if st.session_state[f'firma_{key_suffix}']['imagen_base64'] else '❌ No'}")
            st.write(f"**Nombre:** {st.session_state[f'firma_{key_suffix}']['nombre'] if st.session_state[f'firma_{key_suffix}']['nombre'] else 'No ingresado'}")
            st.write(f"**Cargo:** {st.session_state[f'firma_{key_suffix}']['cargo'] if st.session_state[f'firma_{key_suffix}']['cargo'] else 'No ingresado'}")
            st.write(f"**Institución:** {st.session_state[f'firma_{key_suffix}']['institucion'] if st.session_state[f'firma_{key_suffix}']['institucion'] else 'No ingresado'}")
    
    # 🆕 RETORNAR DIRECTAMENTE DEL SESSION_STATE PARA GARANTIZAR PERSISTENCIA
    return {
        "tiene_imagen_firma": bool(st.session_state[f'firma_{key_suffix}'].get('imagen_base64')),
        "nombre_archivo_firma": st.session_state[f'firma_{key_suffix}'].get('nombre_archivo_firma'),
        "imagen_base64": st.session_state[f'firma_{key_suffix}'].get('imagen_base64'),
        "nombre": st.session_state[f'firma_{key_suffix}']['nombre'],
        "cargo": st.session_state[f'firma_{key_suffix}']['cargo'],
        "institucion": st.session_state[f'firma_{key_suffix}']['institucion'],
        "fecha_captura": datetime.now().isoformat()
    }
   
def cargar_resultados_unificada():
    """Carga de resultados para METAS e INDICADORES de un acuerdo específico"""
    st.header("📊 Carga de Resultados - Metas e Indicadores")
    
    # ✅ Cargar datos del sistema
    db = agreements_load()
    datos_indicadores = cargar_indicadores_json()
    
    if not db:
        st.error("""
        ❌ No hay acuerdos en el sistema.
        
        **Para usar esta función:**
        1. Ve a **Generar Acuerdos** y crea un acuerdo
        2. Agrega fichas y metas al acuerdo  
        3. Vuelve aquí para cargar resultados
        """)
        return
        
    # 1. SELECCIONAR ACUERDO
    acuerdos_activos = list(db.values())
    
    acuerdo_seleccionado = st.selectbox(
        "Seleccionar Acuerdo",
        options=[a["id"] for a in acuerdos_activos],
        format_func=lambda x: f"{x} - {db[x].get('organismo_nombre', 'Sin nombre')} ({db[x].get('estado', 'Sin estado')})",
        key="acuerdo_seleccionado_carga"
    )
    
    if not acuerdo_seleccionado:
        return
        
    acuerdo = db[acuerdo_seleccionado]
    
    # 🆕 PESTAÑAS PARA METAS E INDICADORES
    tab1, tab2 = st.tabs(["🎯 Cargar Resultados por Metas", "📈 Cargar Resultados por Indicadores"])
    
    with tab1:
        st.subheader("Carga de Resultados por Metas")
        _cargar_resultados_metas(acuerdo, db)
    
    with tab2:
        st.subheader("Carga de Resultados por Indicadores")
        _cargar_resultados_indicadores(acuerdo, datos_indicadores, db)

def _cargar_resultados_metas(acuerdo, db):
    """Carga resultados para metas del acuerdo"""
    fichas = acuerdo.get("fichas", [])
    
    if not fichas:
        st.info("ℹ️ Este acuerdo no tiene fichas. Agrega fichas en 'Generar Acuerdos'.")
        return
        
    # 2. SELECCIONAR FICHA
    ficha_seleccionada = st.selectbox(
        "Seleccionar Ficha",
        options=[f["id"] for f in fichas],
        format_func=lambda x: f"{x} - {next((f['nombre'] for f in fichas if f['id'] == x), '')}",
        key="ficha_seleccionada_metas"
    )
    
    if not ficha_seleccionada:
        return
        
    ficha = next((f for f in fichas if f["id"] == ficha_seleccionada), None)
    
    if not ficha:
        st.error("Ficha no encontrada")
        return
        
    # 3. SELECCIONAR META
    metas = ficha.get("metas", [])
    
    if not metas:
        st.info("ℹ️ Esta ficha no tiene metas. Agrega metas en 'Generar Acuerdos'.")
        return
        
    meta_seleccionada = st.selectbox(
        "Seleccionar Meta",
        options=[m["id"] for m in metas],
        format_func=lambda x: f"Meta {next((m['numero'] for m in metas if m['id'] == x), '')}: {next((m['descripcion'] for m in metas if m['id'] == x), '')}",
        key="meta_seleccionada"
    )
    
    if not meta_seleccionada:
        return
        
    meta = next((m for m in metas if m["id"] == meta_seleccionada), None)
    
    if not meta:
        st.error("Meta no encontrada")
        return
        
    # 4. FORMULARIO DE CARGA PARA META
    with st.form("form_carga_resultado_meta"):
        st.subheader(f"Cargar resultado para: {meta['descripcion']}")
        
        # Mostrar info de la meta
        col1, col2 = st.columns(2)
        col1.write(f"**Valor objetivo:** {meta.get('valor_objetivo')}")
        col1.write(f"**Unidad:** {meta.get('unidad')}")
        col2.write(f"**Sentido:** {meta.get('sentido')}")
        col2.write(f"**Rangos:** {len(meta.get('rango', []))} configurados")
        
        # Campo para valor alcanzado
        valor_actual = meta.get('cumplimiento_valor', '')
        valor_alcanzado = st.number_input(
            "Valor Alcanzado",
            value=float(valor_actual) if valor_actual else 0.0,
            step=0.1,
            key="valor_alcanzado_meta"
        )
        
        periodo = st.selectbox("Período", ["Mensual", "Trimestral", "Semestral", "Anual"], key="periodo_meta")
        fecha_medicion = st.date_input("Fecha de medición", key="fecha_meta")
        comentarios = st.text_area("Comentarios", value=meta.get('comentarios_cumplimiento', ''), key="comentarios_meta")
        
        if st.form_submit_button("💾 Guardar Resultado de Meta"):
            # Guardar valor
            meta["cumplimiento_valor"] = str(valor_alcanzado)
            meta["fecha_medicion"] = fecha_medicion.isoformat()
            meta["periodo"] = periodo
            meta["comentarios_cumplimiento"] = comentarios
            
            # CALCULAR CUMPLIMIENTO
            meta["cumplimiento_calc"] = calcular_cumplimiento(meta)
            
            # Guardar acuerdo
            agreements_save(db)
            
            cumplimiento = meta.get('cumplimiento_calc')
            if cumplimiento is not None:
                st.success(f"✅ Resultado de meta guardado - Cumplimiento: {cumplimiento:.1f}%")
            else:
                st.success("✅ Resultado de meta guardado - Cumplimiento: Pendiente")

def _cargar_resultados_indicadores(acuerdo, datos_indicadores, db):
    """Carga resultados para indicadores del acuerdo"""
    
    # 🆕 FILTRAR INDICADORES POR ACUERDO
    indicadores_acuerdo = []
    for indicador in datos_indicadores.get("indicadores", []):
        # Si el indicador está vinculado a este acuerdo o no tiene acuerdo (mostrar todos)
        if not indicador.get("acuerdo_id") or indicador.get("acuerdo_id") == acuerdo["id"]:
            indicadores_acuerdo.append(indicador)
    
    if not indicadores_acuerdo:
        st.info("""
        ℹ️ No hay indicadores para este acuerdo.
        
        **Para crear indicadores vinculados a este acuerdo:**
        1. Ve a **📥 Carga de Indicadores**
        2. Crea un nuevo indicador 
        3. Asocia el indicador a este acuerdo: **{}**
        """.format(acuerdo["id"]))
        return

    # SELECCIONAR INDICADOR
    indicador_seleccionado = st.selectbox(
        "Seleccionar Indicador",
        options=[i["id"] for i in indicadores_acuerdo],
        format_func=lambda x: f"{next((i.get('nombre', 'Sin nombre') for i in indicadores_acuerdo if i['id'] == x), '')} (Valor: {next((i.get('valor', 'N/A') for i in indicadores_acuerdo if i['id'] == x), 'N/A')})",
        key="indicador_seleccionado"
    )
    
    if not indicador_seleccionado:
        return
        
    indicador = next((i for i in indicadores_acuerdo if i["id"] == indicador_seleccionado), None)
    
    if not indicador:
        st.error("Indicador no encontrado")
        return
        
    # FORMULARIO DE CARGA PARA INDICADOR
    with st.form("form_carga_resultado_indicador"):
        st.subheader(f"Cargar resultado para: {indicador['nombre']}")
        
        # Mostrar info del indicador
        col1, col2 = st.columns(2)
        col1.write(f"**Valor actual:** {indicador.get('valor', 'N/A')}")
        col1.write(f"**Meta:** {indicador.get('meta', 'N/A')}")
        col2.write(f"**Unidad:** {indicador.get('unidad', 'N/A')}")
        col2.write(f"**Departamento:** {indicador.get('departamento', 'N/A')}")
        
        # Campos para actualizar indicador
        nuevo_valor = st.number_input(
            "Nuevo Valor del Indicador",
            value=float(indicador.get('valor', 0)),
            step=0.1,
            key="nuevo_valor_indicador"
        )
        
        nueva_meta = st.number_input(
            "Nueva Meta (opcional)",
            value=float(indicador.get('meta', 0)) if indicador.get('meta') else 0.0,
            step=0.1,
            key="nueva_meta_indicador"
        )
        
        fecha_medicion = st.date_input("Fecha de medición", key="fecha_indicador")
        comentarios = st.text_area("Comentarios", value=indicador.get('comentarios', ''), key="comentarios_indicador")
        
        # 🆕 OPCIONAL: Vincular indicador a ficha/meta específica
        st.subheader("🔗 Vincular a Ficha/Meta (Opcional)")
        fichas_acuerdo = acuerdo.get("fichas", [])
        
        if fichas_acuerdo:
            ficha_options = ["No vincular"] + [f["id"] for f in fichas_acuerdo]
            ficha_seleccionada = st.selectbox(
                "Vincular a ficha específica",
                options=ficha_options,
                format_func=lambda x: "No vincular" if x == "No vincular" else f"{x} - {next((f['nombre'] for f in fichas_acuerdo if f['id'] == x), '')}",
                key="vincular_ficha"
            )
            
            if ficha_seleccionada and ficha_seleccionada != "No vincular":
                ficha = next((f for f in fichas_acuerdo if f["id"] == ficha_seleccionada), None)
                if ficha:
                    metas_ficha = ficha.get("metas", [])
                    if metas_ficha:
                        meta_options = ["No vincular"] + [m["id"] for m in metas_ficha]
                        meta_seleccionada = st.selectbox(
                            "Vincular a meta específica",
                            options=meta_options,
                            format_func=lambda x: "No vincular" if x == "No vincular" else f"Meta {next((m['numero'] for m in metas_ficha if m['id'] == x), '')}: {next((m['descripcion'] for m in metas_ficha if m['id'] == x), '')}",
                            key="vincular_meta"
                        )
        
        if st.form_submit_button("💾 Guardar Resultado de Indicador"):
            # Actualizar indicador
            indicador["valor"] = float(nuevo_valor)
            if nueva_meta:
                indicador["meta"] = float(nueva_meta)
            indicador["fecha"] = fecha_medicion.strftime("%Y-%m-%d")
            indicador["comentarios"] = comentarios
            indicador["timestamp"] = datetime.now().isoformat()
            
            # 🆕 Vincular al acuerdo si no está vinculado
            if not indicador.get("acuerdo_id"):
                indicador["acuerdo_id"] = acuerdo["id"]
            
            # Vincular a ficha/meta si se seleccionó
            if ficha_seleccionada and ficha_seleccionada != "No vincular":
                indicador["ficha_id"] = ficha_seleccionada
                if meta_seleccionada and meta_seleccionada != "No vincular":
                    indicador["meta_id"] = meta_seleccionada
            
            # Guardar cambios
            guardar_indicadores_json(datos_indicadores)
            
            st.success(f"✅ Resultado de indicador '{indicador['nombre']}' guardado exitosamente")

def cargar_resultados_por_metas():
    """Función para el menú de seguimiento - Versión independiente para METAS"""
    
    # 🎯 BOTÓN EN HEADER
    col1 = st.columns(1)[0]
    with col1:
        st.header("🎯 Cargar Resultados por Metas")
        
    # Cargar datos del sistema
    db = agreements_load()
    
    if not db:
        st.error("""
        ❌ No hay acuerdos en el sistema.
        
        **Para usar esta función:**
        1. Ve a **Generar Acuerdos** y crea un acuerdo
        2. Agrega fichas y metas al acuerdo  
        3. Vuelve aquí para cargar resultados
        """)
        return
        
    # 1. SELECCIONAR ACUERDO
    acuerdos_activos = list(db.values())
    
    acuerdo_seleccionado = st.selectbox(
        "Seleccionar Acuerdo",
        options=[a["id"] for a in acuerdos_activos],
        format_func=lambda x: f"{x} - {db[x].get('organismo_nombre', 'Sin nombre')} ({db[x].get('estado', 'Sin estado')})",
        key="acuerdo_seleccionado_metas_ind"
    )
    
    if not acuerdo_seleccionado:
        return
        
    acuerdo = db[acuerdo_seleccionado]
    
    # 2. LLAMAR A LA FUNCIÓN EXISTENTE DE METAS
    _cargar_resultados_metas(acuerdo, db)   

def cargar_resultados_por_indicadores():
    """Función para el menú de seguimiento - Versión independiente para INDICADORES"""
    st.header("📈 Carga por Indicadores")
       
    # 🆕 CARGAR DATOS DEL SISTEMA
    db = agreements_load()
    datos_indicadores = cargar_indicadores_json()
    
    if not db:
        st.error("No hay acuerdos en el sistema")
        return

    # 🆕 CARGAR DATOS DEL SISTEMA
    db = agreements_load()
    datos_indicadores = cargar_indicadores_json()
    
    if not db:
        st.error("No hay acuerdos en el sistema")
        return
        
    # Seleccionar acuerdo
    acuerdo_seleccionado = st.selectbox(
        "Seleccionar Acuerdo",
        options=[a["id"] for a in db.values()],
        format_func=lambda x: f"{x} - {db[x].get('organismo_nombre', 'Sin nombre')}",
        key="acuerdo_para_indicadores_menu"
    )
    
    if acuerdo_seleccionado:
        acuerdo = db[acuerdo_seleccionado]
       
        # 🆕 CORRECCIÓN DEFINITIVA - AGREGA ESTO
        acuerdo_corregido = corregir_metas_sin_nombre(acuerdo)
        if acuerdo != acuerdo_corregido:
            db[acuerdo_seleccionado] = acuerdo_corregido
            agreements_save(db)
            st.success("✅ Nombres de metas corregidos automáticamente")
            acuerdo = acuerdo_corregido
               
        # 🆕 ACTUALIZAR INDICADORES AUTOMÁTICAMENTE DESDE METAS
        with st.spinner("🔄 Actualizando indicadores desde metas..."):
            datos_actualizados = actualizar_indicadores_desde_metas(acuerdo, datos_indicadores)
            
            # Guardar si hay cambios
            if datos_actualizados["metadata"]["automaticos"] > 0:
                guardar_indicadores_json(datos_actualizados)
                st.success(f"✅ {datos_actualizados['metadata']['automaticos']} indicadores actualizados desde metas")
        
        # VERIFICAR SI HAY CAMBIOS PARA GUARDAR
        cambios = datos_actualizados["metadata"]["automaticos"] > 0

        if cambios:
            guardar_indicadores_json(datos_actualizados)
            st.success(f"✅ {datos_actualizados['metadata']['automaticos']} indicadores guardados")
        else:
            st.warning("⚠️ No se guardaron cambios - ¿los indicadores ya existían?")

        # 🆕 MOSTRAR FORMULARIO DE CARGA
        nombres_fichas = [ficha.get('nombre', 'Sin nombre') for ficha in acuerdo.get('fichas', [])]
                
        ficha_seleccionada_nombre = st.selectbox(
            "Seleccionar Ficha",
            options=nombres_fichas,
            key="ficha_para_carga_indicadores"
        )
               
        # ENCONTRAR LA FICHA SELECCIONADA
        ficha_actual = None
        for ficha in acuerdo['fichas']:
            if ficha['nombre'] == ficha_seleccionada_nombre:
                ficha_actual = ficha
                break
        
        if ficha_actual:
            st.success(f"✅ Ficha encontrada: {ficha_actual.get('nombre')}")
            st.success(f"📊 Metas en esta ficha: {len(ficha_actual.get('metas', []))}")
            
            # 🆕 SELECTOR DE METAS SOLO DE ESTA FICHA
            if ficha_actual.get('metas'):
                nombres_metas = [meta.get('nombre', 'Sin nombre') for meta in ficha_actual['metas']]  # ✅ CORREGIDO
                st.success(f"🎯 Opciones del selector de metas: {nombres_metas}")
                
                meta_seleccionada_nombre = st.selectbox(
                    "Seleccionar Meta",
                    options=nombres_metas,
                    key="meta_para_carga_indicadores"
                )
                
                st.success(f"🎯 Meta seleccionada: {meta_seleccionada_nombre}")
                
                # ENCONTRAR LA META SELECCIONADA
                meta_actual = None
                for meta in ficha_actual['metas']:
                    if meta.get('nombre', 'Sin nombre') == meta_seleccionada_nombre:
                        meta_actual = meta
                        break
                
                if meta_actual:
                    st.success(f"✅ Meta encontrada: {meta_actual.get('nombre')}")
                    
                    # FORMULARIO DE CARGA DE RESULTADOS
                    st.subheader(f"📊 Cargar Resultados para: {meta_actual.get('nombre')}")
                    
                    # Mostrar información de la meta
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Valor Objetivo", f"{meta_actual.get('valor_objetivo', 0)} {meta_actual.get('unidad', '')}")
                    with col2:
                        st.metric("Ponderación", f"{meta_actual.get('ponderacion', 0)}%")
                    with col3:
                        st.metric("Frecuencia", meta_actual.get('frecuencia', 'Anual'))
                    
                    # Formulario para cargar resultado
                    with st.form(key=f"form_carga_{meta_actual.get('id')}"):
                        periodo = st.selectbox("Período", options=["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                                                                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
                        valor_alcanzado = st.number_input("Valor Alcanzado", value=0.0)
                        observaciones = st.text_area("Observaciones")
                        
                        if st.form_submit_button("💾 Guardar Resultado"):
                            # ✅ LÓGICA UNIFICADA - GUARDA META E INDICADOR
                            try:
                                # 1. GUARDAR EN SISTEMA DE METAS (acuerdo)
                                meta_actual['valor_alcanzado'] = valor_alcanzado
                                meta_actual['ultima_actualizacion'] = datetime.now().isoformat()
                                
                                # Guardar acuerdo actualizado
                                db[acuerdo_seleccionado] = acuerdo
                                agreements_save(db)
                                
                                # 2. GUARDAR EN SISTEMA DE INDICADORES (automáticamente)
                                datos_actualizados = actualizar_indicadores_desde_metas(acuerdo, datos_indicadores)
                                
                                if datos_actualizados["metadata"]["automaticos"] > 0:
                                    guardar_indicadores_json(datos_actualizados)
                                    st.success(f"✅ {datos_actualizados['metadata']['automaticos']} indicadores actualizados automáticamente")
                                
                                # 3. ACTUALIZAR EL INDICADOR ESPECÍFICO CON EL VALOR EXACTO
                                for indicador in datos_actualizados.get('indicadores', []):
                                    # Buscar el indicador vinculado a esta meta específica
                                    if (indicador.get('meta_id') == meta_actual['id'] or 
                                        indicador.get('nombre') == meta_actual.get('nombre')):
                                        
                                        indicador['valor'] = valor_alcanzado  # Valor exacto del formulario
                                        indicador['ultima_actualizacion'] = datetime.now().isoformat()
                                        indicador['comentarios'] = observaciones
                                        break
                                
                                # Guardar indicadores con el valor específico
                                guardar_indicadores_json(datos_actualizados)
                                
                                st.success(f"✅ Sistema unificado: Meta e indicador actualizados para {meta_actual.get('nombre')}")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error al guardar: {str(e)}")
                else:
                    st.error("❌ No se encontró la meta seleccionada")
            else:
                st.warning("⚠️ Esta ficha no tiene metas")
        else:
            st.error("❌ No se encontró la ficha seleccionada")           

def mostrar_graficos_streamlit(df):
    """Muestra visualizaciones usando solo componentes Streamlit"""
   
    # Barras de progreso para cada indicador
    st.subheader("📊 Progreso de Indicadores")
   
    for _, row in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
           
            with col1:
                st.write(f"**{row['nombre']}**")
                if pd.notna(row.get('meta')) and row['meta'] > 0:
                    progreso = min((row['valor'] / row['meta']) * 100, 100)
                    st.progress(int(progreso))
                    st.write(f"{row['valor']} {row.get('unidad', '')} de {row['meta']} ({progreso:.1f}%)")
                else:
                    st.write(f"Valor: {row['valor']} {row.get('unidad', '')}")
           
            with col2:
                st.metric("Actual", f"{row['valor']}")
           
            with col3:
                if pd.notna(row.get('meta')):
                    st.metric("Meta", f"{row['meta']}")
           
            st.write("---")

@st.cache_data(ttl=60, show_spinner=False)
def generar_reporte_html_streamlit():
    """Genera reporte HTML básico sin gráficos complejos - VERSIÓN CORREGIDA"""
    # SOLO CÁLCULOS, SIN WIDGETS ✅
    datos = cargar_indicadores_json()
    if not datos["indicadores"]:
        return None, None  # Retorna datos en lugar de mostrar widgets
    
    df = pd.DataFrame(datos["indicadores"])
    
    try:
        # Crear HTML simple y efectivo
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Indicadores - Sistema de Seguimiento</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f6fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .metricas {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metrica {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metrica h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .metrica .valor {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .tabla {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .tabla th {{
            background: #34495e;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        .tabla td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .tabla tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        .tabla tr:hover {{
            background: #e8f4f8;
        }}
        .resumen {{
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 REPORTE DE INDICADORES</h1>
            <p>Sistema de Seguimiento - Generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}</p>
        </div>
        
        <div class="resumen">
            <h2>🎯 RESUMEN EJECUTIVO</h2>
            <p>Reporte consolidado de todos los indicadores del sistema con análisis de cumplimiento y tendencias.</p>
        </div>
        
        <div class="metricas">
            <div class="metrica">
                <h3>Total de Indicadores</h3>
                <div class="valor">{len(df)}</div>
                <p>Métricas en seguimiento</p>
            </div>
            <div class="metrica">
                <h3>Valor Promedio</h3>
                <div class="valor">{df['valor'].mean():.2f}</div>
                <p>Promedio general</p>
            </div>
            <div class="metrica">
                <h3>Última Actualización</h3>
                <div class="valor">{datos['metadata']['ultima_actualizacion'][:10]}</div>
                <p>Fecha de modificación</p>
            </div>
"""
        
        # Agregar métrica de cumplimiento si hay metas
        if 'meta' in df.columns and df['meta'].notna().any():
            cumplimiento = (df['valor'] / df['meta'] * 100).mean()
            html_content += f"""
            <div class="metrica">
                <h3>Cumplimiento General</h3>
                <div class="valor">{cumplimiento:.1f}%</div>
                <p>Porcentaje de cumplimiento</p>
            </div>
"""
        
        html_content += """
        </div>
        
        <h2>📋 DETALLE DE INDICADORES</h2>
        <table class="tabla">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Nombre del Indicador</th>
                    <th>Valor Actual</th>
                    <th>Meta</th>
                    <th>% Cumplimiento</th>
                    <th>Unidad</th>
                    <th>Departamento</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Agregar filas de datos
        for _, row in df.iterrows():
            cumplimiento = "N/A"
            if pd.notna(row.get('meta')) and row['meta'] > 0:
                cumplimiento = f"{(row['valor'] / row['meta'] * 100):.1f}%"
            
            html_content += f"""
                <tr>
                    <td>{row.get('id', '')}</td>
                    <td><strong>{row.get('nombre', '')}</strong></td>
                    <td>{row.get('valor', '')}</td>
                    <td>{row.get('meta', 'N/A')}</td>
                    <td>{cumplimiento}</td>
                    <td>{row.get('unidad', '')}</td>
                    <td>{row.get('departamento', '')}</td>
                    <td>{row.get('fecha', '')}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <div style="text-align: center; margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
            <p><em>📄 Reporte generado automáticamente por el Sistema de Seguimiento de Indicadores</em></p>
            <p><strong>Para más información, consulte la plataforma digital del sistema.</strong></p>
        </div>
    </div>
</body>
</html>
"""
        
        return html_content, df
        
    except Exception as e:
        st.error(f"❌ Error generando reporte: {str(e)}")
        return None, None

# 🆕 FUNCIÓN SEPARADA PARA MOSTRAR LOS WIDGETS
def mostrar_reporte_completo():
    """Función que muestra la interfaz completa del reporte"""
    st.header("📊 Generar Reporte HTML")
    
    with st.status("Generando reporte HTML...") as status:
        html_content, df = generar_reporte_html_streamlit()
        
        if html_content is None or df is None:
            st.warning("No hay indicadores para generar reporte")
            return
        
        status.update(label="✅ Reporte generado!", state="complete")
        st.success("📄 Reporte HTML generado exitosamente")
        
        # 🎯 WIDGETS FUERA DE LA FUNCIÓN CACHEADA ✅
        st.markdown("""
### 🎯 Reporte Generado

**Vista previa del reporte:**
""")
        
        # Mostrar el HTML en un componente
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # Opción para descargar el HTML
        st.download_button(
            label="📥 Descargar Reporte HTML",
            data=html_content,
            file_name="dashboard_indicadores.html",
            mime="text/html"
        )
        
        # También mostrar los datos en tabla de Streamlit
        st.subheader("📋 Datos en Tabla")
        st.dataframe(df, use_container_width=True)

@st.cache_data(ttl=60, show_spinner=False)
def dashboard_indicadores():
    """Dashboard principal usando solo Streamlit"""
    st.header("📈 Dashboard de Indicadores")
   
    datos = cargar_indicadores_json()
   
    if not datos["indicadores"]:
        st.info("""
        ## 📊 Bienvenido al Sistema de Seguimiento
       
        **Para comenzar:**
        1. 🎯 **Carga de Indicadores** - Agrega tus primeros indicadores
        2. 📄 **Generar Reporte HTML** - Crea reportes ejecutivos
        3. 📈 **Dashboard** - Visualiza y monitorea aquí
       
        *No hay indicadores cargados aún. Comienza por el paso 1.*
        """)
        return
   
    df = pd.DataFrame(datos["indicadores"])
   
    # Métricas principales
    st.subheader("🎯 Métricas Principales")
    col1, col2, col3, col4 = st.columns(4)
   
    with col1:
        st.metric("Total Indicadores", len(df))
    with col2:
        st.metric("Valor Promedio", f"{df['valor'].mean():.1f}")
    with col3:
        if 'meta' in df.columns and df['meta'].notna().any():
            cumplimiento = (df['valor'] / df['meta'] * 100).mean()
            st.metric("Cumplimiento", f"{cumplimiento:.1f}%")
        else:
            st.metric("Cumplimiento", "N/A")
    with col4:
        st.metric("Última Actualización", datos["metadata"]["ultima_actualizacion"].split()[0])
   
    # Visualizaciones con componentes nativos
    mostrar_graficos_streamlit(df)
   
    # Tabla de datos detallada
    st.subheader("📋 Datos Detallados")
    st.dataframe(df, use_container_width=True)

# 🆕 FUNCIÓN ALTERNATIVA SIMPLE PARA REPORTES HTML
def generar_reporte_html_simple():
    """Versión simplificada que siempre funciona"""
    st.header("📊 Generar Reporte HTML - Versión Simple")
    
    datos = cargar_indicadores_json()
    if not datos["indicadores"]:
        st.warning("No hay indicadores para generar reporte")
        return
    
    df = pd.DataFrame(datos["indicadores"])
    
    # Crear HTML mínimo pero funcional
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Reporte de Indicadores</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #34495e; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Reporte de Indicadores</h1>
    <p><strong>Generado:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
    <p><strong>Total indicadores:</strong> {len(df)}</p>
    
    <table>
        <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Valor</th>
            <th>Meta</th>
            <th>Unidad</th>
            <th>Departamento</th>
            <th>Fecha</th>
        </tr>
"""
    
    for _, row in df.iterrows():
        html_content += f"""
        <tr>
            <td>{row.get('id', '')}</td>
            <td>{row.get('nombre', '')}</td>
            <td>{row.get('valor', '')}</td>
            <td>{row.get('meta', 'N/A')}</td>
            <td>{row.get('unidad', '')}</td>
            <td>{row.get('departamento', '')}</td>
            <td>{row.get('fecha', '')}</td>
        </tr>
"""
    
    html_content += """
    </table>
    <p><em>Generado por Sistema de Seguimiento</em></p>
</body>
</html>
"""
    
    # Mostrar vista previa
    st.components.v1.html(html_content, height=600, scrolling=True)
    
    # Botón de descarga
    st.download_button(
        label="📥 Descargar Reporte HTML Simple",
        data=html_content,
        file_name="reporte_indicadores_simple.html",
        mime="text/html"
    )

def modulo_seguimiento_indicadores():
    """Módulo mejorado de seguimiento que considera ponderaciones"""
            
    st.header("📊 Seguimiento de Indicadores con Ponderaciones")

    # 🆕 VERIFICAR DATOS
    db = agreements_load()
    datos_indicadores = cargar_indicadores_json()
         
    if not db:
        st.error("No hay acuerdos en el sistema")
        return

    # Seleccionar acuerdo
    acuerdo_opciones = {k: f"{v.get('id', '')} - {v.get('organismo_nombre', '')}" for k, v in db.items()}
    selected_acuerdo_key = st.selectbox(
        "Seleccionar Acuerdo", 
        options=list(acuerdo_opciones.keys()),
        format_func=lambda x: acuerdo_opciones[x],
        key="seguimiento_acuerdo"
    )

    if selected_acuerdo_key:
        acuerdo = db[selected_acuerdo_key]
        
        # 🆕 EXTRAER TODAS LAS METAS DEL ACUERDO
        todas_las_metas = []
        for ficha in acuerdo.get('fichas', []):
            todas_las_metas.extend(ficha.get('metas', []))
               
        if not todas_las_metas:
            st.error("❌ No se encontraron metas en este acuerdo")
            return
    
        # 🆕 ACTUALIZAR INDICADORES AUTOMÁTICAMENTE (PASAR LAS METAS)
        datos_actualizados = actualizar_indicadores_desde_metas(acuerdo, datos_indicadores, todas_las_metas)
        guardar_indicadores_json(datos_actualizados)
                
        indicadores_acuerdo = [
            ind for ind in datos_actualizados.get('indicadores', [])
            if ind.get('acuerdo_origen') == acuerdo['id']  # ✅ CORREGIDO
        ]

        # 🆕 COMENTAR TEMPORALMENTE EL RETURN PARA VER EL DEBUG
        if not indicadores_acuerdo:
            st.error("No hay indicadores para este acuerdo")
            # ❌ COMENTA TEMPORALMENTE ESTE RETURN PARA VER EL DEBUG COMPLETO
            # return
        
        if not indicadores_acuerdo:
            st.error("No hay indicadores para este acuerdo")
            return
               
        # 🆕 CALCULAR PONDERACIONES Y CUMPLIMIENTO GLOBAL
        st.subheader("📈 Cumplimiento Global con Ponderaciones")
        
        cumplimiento_global = 0
        total_ponderacion = 0
        resultados = []
        
        for indicador in indicadores_acuerdo:
            ponderacion = indicador.get('ponderacion', 0)
            
            # 🆕 CONVERTIR VALORES A NÚMEROS
            try:
                valor_actual = float(indicador.get('valor', 0)) if indicador.get('valor') not in [None, ''] else 0
                valor_meta = float(indicador.get('meta', 1)) if indicador.get('meta') not in [None, ''] else 1
            except (ValueError, TypeError):
                valor_actual = 0
                valor_meta = 1
            
            # ✅ PROTECCIÓN: Evitar división por cero
            if valor_meta > 0:
                cumplimiento_individual = (valor_actual / valor_meta) * 100
                
                # ✅ APLICAR TOPE AL 100% - CORRECCIÓN CLAVE
                cumplimiento_topeado = min(cumplimiento_individual, 100.0)
                aporte_ponderado = (cumplimiento_topeado * ponderacion) / 100 if ponderacion > 0 else cumplimiento_topeado
                
                cumplimiento_global += aporte_ponderado
                total_ponderacion += ponderacion
                
                resultados.append({
                    'indicador': indicador['nombre'],
                    'indicador_id': indicador['id'],
                    'ponderacion': ponderacion,
                    'valor_actual': valor_actual,
                    'valor_meta': valor_meta,
                    'cumplimiento_individual': cumplimiento_individual,
                    'aporte_ponderado': aporte_ponderado
                })
        
        # Mostrar métricas globales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if total_ponderacion > 0:
                # 🚨 CORRECCIÓN: NO dividir nuevamente, ya está en porcentaje
                cumplimiento_final = cumplimiento_global  # ← YA ESTÁ CALCULADO CORRECTAMENTE
                st.metric("📊 Cumplimiento Global", f"{cumplimiento_final:.1f}%")
            else:
                st.metric("📊 Cumplimiento Global", "N/A")
                
        with col2:
            st.metric("🎯 Total Ponderación", f"{total_ponderacion:.1f}%")
        
        with col3:
            st.metric("📈 Indicadores", len(indicadores_acuerdo))
        
        # 🆕 TABLA DETALLADA CON PONDERACIONES
        st.subheader("🎯 Detalle de Indicadores con Ponderaciones")
        
        for i, resultado in enumerate(resultados):  # 🆕 CAMBIO: agregar enumerate
            with st.expander(f"{resultado['indicador']} - Ponderación: {resultado['ponderacion']}%", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.write("**Valores**")
                    st.write(f"Actual: {resultado['valor_actual']}")
                    st.write(f"Meta: {resultado['valor_meta']}")
                
                with col2:
                    st.write("**Cumplimiento**")
                    st.write(f"Individual: {resultado['cumplimiento_individual']:.1f}%")
                    if resultado['ponderacion'] > 0:
                        st.write(f"Aporte: {resultado['aporte_ponderado']:.1f}%")
                
                with col3:
                    # Gráfico simple de progreso
                    progreso = min(resultado['cumplimiento_individual'] / 100, 1.0)
                    st.progress(progreso)
                    st.write(f"{resultado['cumplimiento_individual']:.1f}%")
                
                with col4:
                    st.button(
                        "✏️ Editar",
                        disabled=True,
                        help="La edición se realiza desde Fichas y Metas",
                        key=f"edit_disabled_{resultado['indicador_id']}_{i}"
                    )
        
        # 🆕 GRÁFICO DE PONDERACIONES
        st.subheader("📊 Distribución de Ponderaciones")
        
        if resultados:
            # Preparar datos para el gráfico
            nombres = [r['indicador'] for r in resultados]
            ponderaciones = [r['ponderacion'] for r in resultados]
            cumplimientos = [r['cumplimiento_individual'] for r in resultados]
            
            # Mostrar tabla resumen
            st.dataframe({
                'Indicador': nombres,
                'Ponderación (%)': ponderaciones,
                'Cumplimiento (%)': [f"{c:.1f}%" for c in cumplimientos],
                'Aporte': [f"{r['aporte_ponderado']:.1f}%" for r in resultados]
            })

# ==================== CLASES ====================

# ==================== SISTEMA DE PERMISOS MEJORADO ====================

class SistemaPermisos:
    def __init__(self):
        self.definir_permisos()
    
    def definir_permisos(self):
        # 🆕 CORRECIÓN: Usar los estados EXACTOS de tu sistema
        self.permisos = {
            "Responsable de Acuerdo": {
                "Borrador": ['editar', 'enviar_revision', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar'],
                "Pendiente de Revisión": ['editar', 'ver', 'guardar', 'crear_ficha', 'crear_meta'],
                "En Revisión OPP": ['ver'],
                "En Revisión Comisión CG": ['ver'],
                "Aprobado": ['ver'],
                "Rechazado": ['editar', 'reingresar', 'guardar', 'crear_ficha', 'crear_meta'],
                "Archivado": ['ver']
            },
            "Supervisor OPP": {
                "Borrador": ['ver'],
                "Pendiente de Revisión": ['editar', 'validar', 'rechazar', 'devolver', 'guardar', 'ver'],
                "En Revisión OPP": ['editar', 'validar', 'rechazar', 'devolver', 'guardar', 'ver'],
                "En Revisión Comisión CG": ['editar', 'ver', 'guardar'],
                "Aprobado": ['ver'],
                "Rechazado": ['editar', 'ver', 'guardar'],
                "Archivado": ['ver']
            },
            "Comisión CG": {
                "Borrador": ['ver'],
                "Pendiente de Revisión": ['ver'],
                "En Revisión OPP": ['ver'],
                "En Revisión Comisión CG": ['editar', 'aprobar', 'rechazar', 'archivar', 'guardar', 'ver'],
                "Aprobado": ['editar', 'archivar', 'guardar', 'ver'],
                "Rechazado": ['editar', 'ver', 'guardar'],
                "Archivado": ['editar', 'reactivar', 'guardar', 'ver']
            },
            "Administrador": {
                "Borrador": ['editar', 'enviar_revision', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar', 'cambiar_estado'],
                "Pendiente de Revisión": ['editar', 'validar', 'rechazar', 'devolver', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar', 'cambiar_estado'],
                "En Revisión OPP": ['editar', 'validar', 'rechazar', 'devolver', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar', 'cambiar_estado'],
                "En Revisión Comisión CG": ['editar', 'aprobar', 'rechazar', 'archivar', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar', 'cambiar_estado'],
                "Aprobado": ['editar', 'archivar', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar', 'cambiar_estado'],
                "Rechazado": ['editar', 'reingresar', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar', 'cambiar_estado'],
                "Archivado": ['editar', 'reactivar', 'guardar', 'ver', 'crear_ficha', 'crear_meta', 'eliminar', 'cambiar_estado']
            }
        }
    
    def puede_editar(self, rol: str, estado: str) -> bool:
        """Verifica si el rol puede editar en el estado actual"""
        return rol in self.permisos and estado in self.permisos[rol] and 'editar' in self.permisos[rol][estado]
    
    def obtener_acciones_permitidas(self, rol: str, estado: str) -> list:
        """Obtiene todas las acciones permitidas para un rol en un estado"""
        return self.permisos.get(rol, {}).get(estado, [])
    
    def tiene_permiso(self, rol: str, estado: str, accion: str) -> bool:
        """Verifica si un rol tiene permiso para una acción específica en un estado"""
        return accion in self.obtener_acciones_permitidas(rol, estado)

# Instancia global del sistema de permisos
permisos_sistema = SistemaPermisos()

# ==================== FUNCIONES DE VERIFICACIÓN INTEGRADAS ====================

def verificar_permiso_edicion(rol: str, estado: str) -> bool:
    """Función utilitaria para verificar permiso de edición"""
    return permisos_sistema.puede_editar(rol, estado)

def verificar_permiso_accion(rol: str, estado: str, accion: str) -> bool:
    """Verifica permiso para una acción específica"""
    return permisos_sistema.tiene_permiso(rol, estado, accion)

class GestorSeguimientos:
    def __init__(self):
        self.archivo_seguimientos = "seguimientos.json"
    
    def cargar_seguimientos(self):  # ← Agregar _ antes de self
        if os.path.exists(self.archivo_seguimientos):
            with open(self.archivo_seguimientos, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"seguimientos": []}
    
    def guardar_seguimiento(self, datos):
        seguimientos = self.cargar_seguimientos()
        
        nuevo_seguimiento = {
            "id": len(seguimientos["seguimientos"]) + 1,
            "fecha_creacion": datetime.now().isoformat(),
            "estado": "pendiente_revision",
            **datos
        }
        
        seguimientos["seguimientos"].append(nuevo_seguimiento)
        
        with open(self.archivo_seguimientos, 'w', encoding='utf-8') as f:
            json.dump(seguimientos, f, indent=2, ensure_ascii=False)
        
        return nuevo_seguimiento

# ==================== FUNCIONES DE CARGA ====================
def abrir_carga_resultados():
    """Abre el formulario HTML de carga de resultados"""
    archivo_html = "seguimiento-resultados.html"
    
    if os.path.exists(archivo_html):
        st.info("Abriendo formulario de carga de resultados en el navegador...")
        webbrowser.open(archivo_html)
    else:
        st.error(f"❌ Archivo {archivo_html} no encontrado. Crea el archivo HTML.")

def mostrar_dashboard_seguro():
    """Dashboard que FUNCIONA SEGURO sin instalaciones adicionales"""
    
    # 🎯 BOTÓN EN HEADER
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📈 Dashboard de Control - Compromisos de Gestión")
    with col2:
        if st.button("🏠 Volver al Inicio", use_container_width=True, key="volver_inicio"):
            st.session_state.current_page = "Inicio"
            page_home_mejorada()
            return
        
    # ==================== MÉTRICAS PRINCIPALES ====================
    st.header("📊 Métricas Principales")
    
    # 🆕 CARGAR DATOS REALES DE ACUERDOS
    db = agreements_load()
    
    if not db:
        st.info("📝 No hay acuerdos cargados en el sistema")
        return
    
    # 🆕 CALCULAR MÉTRICAS REALES
    total_acuerdos = len(db)
    total_fichas = sum(len(acuerdo.get('fichas', [])) for acuerdo in db.values())
    total_metas = sum(len(ficha.get('metas', [])) for acuerdo in db.values() for ficha in acuerdo.get('fichas', []))
    
    # 🆕 CALCULAR CUMPLIMIENTO PROMEDIO REAL
    cumplimientos = []
    for acuerdo in db.values():
        for ficha in acuerdo.get('fichas', []):
            for meta in ficha.get('metas', []):
                if meta.get('cumplimiento_calc') is not None:
                    cumplimientos.append(meta['cumplimiento_calc'])
    
    cumplimiento_promedio = sum(cumplimientos) / len(cumplimientos) if cumplimientos else 0
    
    # 🆕 CALCULAR METAS COMPLETADAS vs PENDIENTES
    metas_completadas = len([
        m for acuerdo in db.values() 
        for ficha in acuerdo.get('fichas', []) 
        for m in ficha.get('metas', []) 
        if isinstance(m.get('cumplimiento_calc'), (int, float)) and m.get('cumplimiento_calc', 0) >= 90
    ])
    metas_pendientes = total_metas - metas_completadas
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Acuerdos", total_acuerdos)
    with col2:
        st.metric("Cumplimiento Promedio", f"{cumplimiento_promedio:.1f}%")
    with col3:
        st.metric("Metas Completadas", metas_completadas)
    with col4:
        st.metric("Metas Pendientes", metas_pendientes)
    
    # ==================== GRÁFICOS CON DATOS REALES ====================
    st.header("📈 Visualización de Datos")
    
    # 📍 GRÁFICO 1: Tendencia de cumplimiento por acuerdo
    st.subheader("Cumplimiento por Acuerdo")
    
    datos_acuerdos = []
    for acuerdo_id, acuerdo in db.items():
        cumplimientos_acuerdo = []
        for ficha in acuerdo.get('fichas', []):
            for meta in ficha.get('metas', []):
                if meta.get('cumplimiento_calc') is not None:
                    cumplimientos_acuerdo.append(meta['cumplimiento_calc'])
        
        if cumplimientos_acuerdo:
            promedio_acuerdo = sum(cumplimientos_acuerdo) / len(cumplimientos_acuerdo)
            datos_acuerdos.append({
                'Acuerdo': acuerdo_id[:15] + "...",  # Acortar ID largo
                'Cumplimiento': promedio_acuerdo
            })
    
    if datos_acuerdos:
        df_acuerdos = pd.DataFrame(datos_acuerdos)
        st.bar_chart(df_acuerdos.set_index('Acuerdo'))
    else:
        st.info("📊 Cargue resultados en 'Carga por Metas' para ver gráficos")
    
    # 📍 GRÁFICO 2: Distribución de estados de metas
    st.subheader("Estados de Metas")
    
    estados_metas = {
        'Cumplidas (≥90%)': 0,
        'Parciales (70-89%)': 0,
        'En Progreso (50-69%)': 0,
        'Pendientes (<50%)': 0,
        'Sin Datos': 0
    }
    
    for acuerdo in db.values():
        for ficha in acuerdo.get('fichas', []):
            for meta in ficha.get('metas', []):
                cumplimiento = meta.get('cumplimiento_calc')
                if cumplimiento is None:
                    estados_metas['Sin Datos'] += 1
                elif cumplimiento >= 90:
                    estados_metas['Cumplidas (≥90%)'] += 1
                elif cumplimiento >= 70:
                    estados_metas['Parciales (70-89%)'] += 1
                elif cumplimiento >= 50:
                    estados_metas['En Progreso (50-69%)'] += 1
                else:
                    estados_metas['Pendientes (<50%)'] += 1
    
    df_estados = pd.DataFrame({
        'Estado': list(estados_metas.keys()),
        'Cantidad': list(estados_metas.values())
    })
    
    st.bar_chart(df_estados.set_index('Estado'))
    
    # ==================== TABLA DE METAS RECIENTES ====================
    st.header("📋 Metas con Resultados")
    
    metas_con_resultados = []
    for acuerdo in db.values():
        for ficha in acuerdo.get('fichas', []):
            for meta in ficha.get('metas', []):
                if meta.get('cumplimiento_calc') is not None:
                    metas_con_resultados.append({
                        "Acuerdo": acuerdo['id'],
                        "Ficha": ficha.get('nombre', 'Sin nombre'),
                        "Meta": f"Meta {meta.get('numero', '')}",
                        "Cumplimiento": f"{meta.get('cumplimiento_calc', 0):.1f}%",
                        "Estado": "✅ Cumplida" if meta.get('cumplimiento_calc', 0) >= 90 else 
                                 "🟡 Parcial" if meta.get('cumplimiento_calc', 0) >= 70 else
                                 "🔴 Pendiente"
                    })
    
    if metas_con_resultados:
        df_metas = pd.DataFrame(metas_con_resultados)
        st.dataframe(df_metas, use_container_width=True)
    else:
        st.info("📝 No hay metas con resultados cargados. Use 'Carga por Metas' para comenzar.")
    
    # ==================== ANÁLISIS Y RECOMENDACIONES MEJORADO ====================
    st.header("📋 Estado General")
    
    if cumplimientos:
        cumplimiento_promedio_real = sum(cumplimientos) / len(cumplimientos)
        
        if cumplimiento_promedio_real >= 90:
            estado = "✅ EXCELENTE - Cumplimiento sobresaliente"
            recomendacion = "Mantener las estrategias actuales"
        elif cumplimiento_promedio_real >= 80:
            estado = "🟢 BUENO - Cumplimiento satisfactorio"
            recomendacion = "Focalizar en metas con menor cumplimiento"
        elif cumplimiento_promedio_real >= 70:
            estado = "🟡 REGULAR - Necesita mejora"
            recomendacion = "Revisar estrategias de metas críticas"
        else:
            estado = "🔴 INSUFICIENTE - Acción correctiva necesaria"
            recomendacion = "Reunión urgente con comisión de seguimiento"
        
        st.info(f"**Estado General:** {estado}")
        st.success(f"**Recomendación:** {recomendacion}")
        
        # 🆕 MÉTRICAS ADICIONALES
        col_anal1, col_anal2, col_anal3 = st.columns(3)
        with col_anal1:
            st.metric("Metas con datos", f"{len(cumplimientos)}/{total_metas}")
        with col_anal2:
            st.metric("Tasa de Cumplimiento", f"{cumplimiento_promedio_real:.1f}%")
        with col_anal3:
            porcentaje_completadas = (metas_completadas / total_metas * 100) if total_metas > 0 else 0
            st.metric("Metas Completadas", f"{porcentaje_completadas:.1f}%")
    else:
        st.warning("⚠️ **No hay datos de cumplimiento cargados**")
        st.info("💡 Use 'Carga por Metas' o 'Carga por Indicadores' para cargar resultados")
    
    # ==================== ACCIONES RÁPIDAS ====================
    st.header("🚀 Acciones Disponibles")
    
    col1 = st.columns(1)[0]

    with col1:
        if st.button("🔄 Actualizar Dashboard", key="refresh_dashboard"):
            st.rerun()

def format_counter_number(n: int) -> str:
    """Devuelve el número con 4 dígitos (ej: 1 -> '0001')."""
    return f"{n:04d}"

def get_next_ficha_number(year: int) -> int:
    """
    Obtiene el siguiente número global de ficha para un año determinado.
    Usa el archivo counters.json para recordar el último número usado.
    """
    import json, os
    COUNTERS_FILE = "data/counters.json"
    
    # Si no existe counters.json, lo creamos vacío
    if not os.path.exists(COUNTERS_FILE):
        counters = {}
    else:
        with open(COUNTERS_FILE, "r", encoding="utf-8") as f:
            try:
                counters = json.load(f)
            except json.JSONDecodeError:
                counters = {}
    
    # Obtener último número usado para el año
    last = counters.get(str(year), 0)
    next_num = last + 1
    
    # Guardar el nuevo valor
    counters[str(year)] = next_num
    with open(COUNTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(counters, f, indent=2, ensure_ascii=False)
    
    return next_num

def generate_ficha_code(year: int, agr_id: str) -> str:
    """Genera código único de ficha con validación"""
    try:
        db = agreements_load()
        
        # Buscar el máximo número de ficha existente para este año
        max_num = 0
        for agr in db.values():
            if agr.get("año") == year:
                for ficha in agr.get("fichas", []):
                    ficha_id = ficha.get("id", "")
                    if ficha_id.startswith("F_"):
                        try:
                            # Extraer número: F_0001_AC0001_2024 -> 0001
                            parts = ficha_id.split("_")
                            if len(parts) >= 2:
                                num = int(parts[1])
                                max_num = max(max_num, num)
                        except ValueError:
                            continue
        
        next_num = max_num + 1
        base = format_counter_number(next_num)
        return f"F_{base}_{agr_id}_{year}"
    
    except Exception as e:
        st.error(f"Error generando código de ficha: {e}")
        # Código de emergencia
        return f"F_EMG_{int(time.time())}_{agr_id}_{year}"        

def registrar_notificacion_local(acuerdo, usuario):
    """Registra la notificación localmente sin enviar email"""
    try:
        # 📁 CREAR ARCHIVO DE LOG LOCAL
        log_file = "notificaciones_firmas.txt"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"""
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}
📝 ACUERDO FIRMADO
├─ Acuerdo: {acuerdo['id']}
├─ Organismo: {acuerdo.get('organismo_nombre', 'N/A')}
├─ Año: {acuerdo.get('año', 'N/A')}
├─ Firmado por: {usuario['username']} ({usuario.get('role', 'N/A')})
├─ Fecha firma: {acuerdo.get('firmas', {}).get('fecha_firma', 'N/A')}
└─ Estado: {acuerdo.get('estado', 'N/A')}
{'='*50}
""")
        
        return True, "Notificación registrada en archivo local"
        
    except Exception as e:
        return False, f"Error registrando notificación: {str(e)}"

# 🆕 FUNCIÓN PARA MOSTRAR ESTADO DEL SISTEMA EN HOME
def system_status_card():
    """Muestra una tarjeta con el estado del sistema en la página de inicio"""
    if st.session_state.user and st.session_state.user.get("role") == "Administrador":
        with st.expander("📊 Estado del Sistema (Admin)", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            # Contadores del sistema
            try:
                counters = load_json(COUNTERS_FILE, {"agreements": {}, "fichas": {}, "metas": {}})
                total_agreements = sum(len(v) for v in counters.get("agreements", {}).values())
                total_fichas = sum(len(v) for v in counters.get("fichas", {}).values())
                total_metas = sum(len(v) for v in counters.get("metas", {}).values())
                
                col1.metric("📋 Acuerdos", total_agreements)
                col2.metric("📝 Fichas", total_fichas)
                col3.metric("🎯 Metas", total_metas)
            except:
                col1.write("📋 Acuerdos: N/A")
                col2.write("📝 Fichas: N/A")
                col3.write("🎯 Metas: N/A")
            
            # Verificación de permisos
            try:
                test_file = os.path.join(DATA_DIR, "test.tmp")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                st.success("✅ Sistema operativo correctamente")
            except PermissionError:
                st.error("❌ Problemas de permisos detectados")
            
            # Espacio en disco
            if os.path.exists(DATA_DIR):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(DATA_DIR):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
                st.info(f"💾 Uso de disco: {total_size / 1024 / 1024:.2f} MB")    

# 🔹 Funciones de almacenamiento corregidas

def save_json(path, obj):
    """Guarda un objeto JSON con manejo robusto de errores de permisos"""
    try:
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        tmp = path + ".tmp"
        
        # Intentar guardar en archivo temporal
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        
        # Intentar reemplazar el archivo original
        try:
            if os.path.exists(path):
                os.remove(path)  # Eliminar primero el archivo existente
            os.rename(tmp, path)  # Usar rename en lugar de replace
        except PermissionError:
            # Si falla, usar método alternativo
            with open(path, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            if os.path.exists(tmp):
                os.remove(tmp)
                
    except Exception as e:
        st.error(f"Error al guardar {path}: {e}")
        # Guardar en memoria como último recurso
        if "memory_backup" not in st.session_state:
            st.session_state.memory_backup = {}
        st.session_state.memory_backup[path] = obj

def load_json(path, default):
    """Carga un archivo JSON con respaldo en memoria"""
    try:
        # Primero intentar cargar desde memoria
        if hasattr(st.session_state, 'memory_backup') and path in st.session_state.memory_backup:
            return st.session_state.memory_backup[path]
            
        # Luego intentar cargar desde archivo
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return default
    except Exception:
        return default

def ensure_storage():
    """Asegura que la estructura de almacenamiento existe"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        
        # Crear archivos básicos si no existen
        if not os.path.exists(USERS_FILE):
            save_json(USERS_FILE, {})
        if not os.path.exists(AGREEMENTS_FILE):
            save_json(AGREEMENTS_FILE, {})
        if not os.path.exists(COUNTERS_FILE):
            counters = {"agreements": {}, "fichas": {}, "metas": {}}
            save_json(COUNTERS_FILE, counters)
        if not os.path.exists(NATURALEZA_MAP_FILE):
            save_json(NATURALEZA_MAP_FILE, {})
            
        return True
    except Exception as e:
        st.error(f"Error inicializando almacenamiento: {e}")
        return False

PERSIST_OK = ensure_storage()

def format_counter_number(n: int, width: int = 4) -> str:
    return str(n).zfill(width)

def find_max_existing_number(kind: str, year: int) -> int:
    """
    Encuentra el número máximo existente para un tipo y año específicos.
    """
    db = agreements_load()
    max_num = 0
    found_any = False
    
    if kind == "agreements":
        for agr in db.values():
            if agr.get("año") == year:
                code = agr.get("id", "")
                if code.startswith("AC_"):
                    parts = code.split("_")
                    if len(parts) >= 3:
                        try:
                            # Manejar ambos formatos: AC_0001_2024 y AC_PREF_0001_2024
                            if len(parts) == 4: # Formato con prefijo: AC_PREF_0001_2024
                                num = int(parts[2])
                            else: # Formato simple: AC_0001_2024
                                num = int(parts[1])
                            max_num = max(max_num, num)
                            found_any = True
                        except ValueError:
                            continue
    elif kind == "fichas":
        for agr in db.values():
            if agr.get("año") == year:
                for ficha in agr.get("fichas", []):
                    ficha_id = ficha.get("id", "")
                    if ficha_id.startswith("F_"):
                        parts = ficha_id.split("_")
                        if len(parts) >= 2:
                            try:
                                num = int(parts[1])
                                max_num = max(max_num, num)
                                found_any = True
                            except ValueError:
                                continue
    elif kind == "metas":
        for agr in db.values():
            for ficha in agr.get("fichas", []):
                for meta in ficha.get("metas", []):
                    meta_id = meta.get("id", "")
                    if meta_id.startswith("M_"):
                        parts = meta_id.split("_")
                        if len(parts) >= 2:
                            try:
                                num = int(parts[1])
                                max_num = max(max_num, num)
                                found_any = True
                            except ValueError:
                                continue
    
    # Si no se encontró ningún elemento, devolver 0 para empezar desde 1
    return max_num if found_any else 0

def get_next_counter(kind: str, year: int, prefix: Optional[str]=None) -> int:
    counters = load_json(COUNTERS_FILE, {"agreements": {}, "fichas": {}, "metas": {}})
    if kind not in counters:
        counters[kind] = {}
    ys = str(year)
    
    # Para todos los tipos, usar el máximo existente + 1
    max_existing = find_max_existing_number(kind, year)
    
    # Si no hay elementos existentes, empezar desde 1, sino desde max_existing + 1
    next_num = 1 if max_existing == 0 else max_existing + 1
    
    counters[kind][ys] = next_num
    save_json(COUNTERS_FILE, counters)
    return next_num

# === FUNCIONES DE EXPORTACIÓN/IMPRESIÓN ===

def exportar_html_imprimible(agr: Dict[str, Any]) -> str:
    """Genera HTML optimizado para impresión con diseño responsive"""
    
    # Preparar datos
    organismo_nombre = agr.get('organismo_nombre', 'No especificado')
    acuerdo_id = agr.get('id', 'Sin código')
    año = agr.get('año', 'No especificado')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Acuerdo {acuerdo_id} - {organismo_nombre}</title>
        <style>
            /* RESET Y CONFIGURACIÓN GENERAL */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                background: #fff;
                margin: 0;
                padding: 0;
                width: 100%;
            }}
            
            /* CONTENEDOR PRINCIPAL - ANCHO COMPLETO */
            .container {{
                width: 100%;
                max-width: 100%;
                margin: 0 auto;
                padding: 20px;
            }}
            
            /* ENCABEZADO */
            .header {{
                text-align: center;
                border-bottom: 3px solid #007bff;
                padding: 30px 20px;
                margin-bottom: 30px;
                background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                color: white;
                border-radius: 10px;
            }}
            
            .header h1 {{
                font-size: 28px;
                margin-bottom: 10px;
                font-weight: bold;
            }}
            
            .header h2 {{
                font-size: 22px;
                margin-bottom: 5px;
                font-weight: normal;
            }}
            
            .header h3 {{
                font-size: 18px;
                margin-bottom: 15px;
                opacity: 0.9;
            }}
            
            .header p {{
                font-size: 14px;
                opacity: 0.8;
            }}
            
            /* SECCIONES */
            .section {{
                margin: 30px 0;
                padding: 25px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: #fafafa;
                page-break-inside: avoid;
            }}
            
            .section h3 {{
                color: #007bff;
                border-bottom: 2px solid #007bff;
                padding-bottom: 10px;
                margin-bottom: 20px;
                font-size: 20px;
            }}
            
            /* TABLAS MEJORADAS */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 14px;
            }}
            
            th {{
                background: #007bff;
                color: white;
                padding: 12px 15px;
                text-align: left;
                font-weight: bold;
            }}
            
            td {{
                padding: 10px 15px;
                border: 1px solid #ddd;
            }}
            
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            
            /* FICHAS */
            .ficha {{
                background: white;
                margin: 20px 0;
                padding: 20px;
                border-left: 5px solid #28a745;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                page-break-inside: avoid;
            }}
            
            .ficha h4 {{
                color: #28a745;
                margin-bottom: 15px;
                font-size: 18px;
            }}
            
            /* METAS */
            .meta {{
                background: #f8f9fa;
                margin: 15px 0;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #e9ecef;
            }}
            
            .meta.hito {{
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
            }}
            
            .cumplimiento {{
                font-weight: bold;
                color: #28a745;
            }}
            
            /* ESTADOS DE META */
            .estado-meta {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            
            .estado-cumplida {{ background: #d4edda; color: #155724; }}
            .estado-parcial {{ background: #fff3cd; color: #856404; }}
            .estado-no-cumplida {{ background: #f8d7da; color: #721c24; }}
            
            /* FOOTER */
            .footer {{
                text-align: center;
                margin-top: 50px;
                padding: 20px;
                border-top: 2px solid #ddd;
                color: #666;
                font-size: 12px;
            }}
            
            /* ESTILOS PARA IMPRESIÓN */
            @media print {{
                body {{
                    margin: 0;
                    padding: 0;
                    background: white;
                }}
                
                .container {{
                    width: 100%;
                    margin: 0;
                    padding: 15px;
                    box-shadow: none;
                }}
                
                .header {{
                    background: white !important;
                    color: black !important;
                    border-bottom: 3px solid black;
                }}
                
                .section {{
                    border: 1px solid #000;
                    margin: 20px 0;
                }}
                
                .no-print {{
                    display: none !important;
                }}
                
                .ficha, .meta {{
                    page-break-inside: avoid;
                }}
                
                h1, h2, h3 {{
                    page-break-after: avoid;
                }}
            }}
            
            /* RESPONSIVE */
            @media (max-width: 768px) {{
                .container {{
                    padding: 10px;
                }}
                
                .header h1 {{
                    font-size: 24px;
                }}
                
                table {{
                    font-size: 12px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 SISTEMA DE COMPROMISOS DE GESTIÓN</h1>
                <h2>ACUERDO: {acuerdo_id}</h2>
                <h3>{organismo_nombre}</h3>
                <p>Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Año: {año}</p>
            </div>
    """
    
    # SECCIÓN DE INFORMACIÓN GENERAL
    html_content += f"""
            <div class="section">
                <h3>📋 INFORMACIÓN GENERAL DEL ACUERDO</h3>
                <table>
                    <tr><th style="width: 30%;">Organismo:</th><td>{organismo_nombre}</td></tr>
                    <tr><th>Tipo de Organismo:</th><td>{agr.get('organismo_tipo', 'No especificado')}</td></tr>
                    <tr><th>Naturaleza Jurídica:</th><td>{agr.get('naturaleza_juridica', 'No especificado')}</td></tr>
                    <tr><th>Año:</th><td>{año}</td></tr>
                    <tr><th>Vigencia:</th><td>{agr.get('vigencia_desde', '')} al {agr.get('vigencia_hasta', '')}</td></tr>
                    <tr><th>Estado:</th><td>{agr.get('estado', 'No especificado')}</td></tr>
                    <tr><th>Organismo de Enlace:</th><td>{agr.get('organismo_enlace', 'No especificado')}</td></tr>
                    <tr><th>Tipo de Compromiso:</th><td>{agr.get('tipo_compromiso', 'No especificado')}</td></tr>
                </table>
            </div>
    """
    
    # SECCIÓN DE OBJETO DEL ACUERDO
    if agr.get('objeto'):
        html_content += f"""
            <div class="section">
                <h3>🎯 OBJETO DEL ACUERDO</h3>
                <p style="text-align: justify; line-height: 1.8;">{agr.get('objeto', 'No especificado')}</p>
            </div>
        """
    
    # SECCIÓN DE PARTES FIRMANTES
    if agr.get('partes_firmantes'):
        html_content += f"""
            <div class="section">
                <h3>📝 PARTES FIRMANTES</h3>
                <p style="text-align: justify; line-height: 1.8;">{agr.get('partes_firmantes', 'No especificado')}</p>
            </div>
        """
    
    # SECCIÓN DE CLAÚSULAS (NUEVA)
    if agr.get('clausulas'):
        clausulas_no_vacias = [c for c in agr.get('clausulas', []) if c.strip()]
        if clausulas_no_vacias:
            html_content += """
                <div class="section">
                    <h3>📝 CLAÚSULAS DEL ACUERDO</h3>
            """
            for i, clausula in enumerate(clausulas_no_vacias, 1):
                html_content += f"""
                    <div style="margin: 15px 0; padding: 10px; background: white; border-radius: 5px;">
                        <strong>Cláusula {i}:</strong> {clausula}
                    </div>
                """
            html_content += "</div>"
    
    # 🆕 SECCIÓN DE FIRMAS - USANDO DATOS REALES DEL ACUERDO
    firmas = agr.get("firmas", {})
    contraparte = firmas.get("contraparte", {})
    institucion = firmas.get("institucion", {})
    
    html_content += """
    <div class="section" style="page-break-before: always; margin-top: 50px;">
        <h3 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #007bff; padding-bottom: 15px;">
            FIRMAS DEL ACUERDO
        </h3>
        
        <div style="display: flex; justify-content: space-between; margin: 50px 0; align-items: flex-start;">
            <!-- FIRMA CONTRAPARTE -->
            <div style="text-align: center; width: 45%; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;">
                <h4 style="color: #34495e; margin-bottom: 30px;">👤 CONTRAPARTE</h4>
                
                <div style="border-bottom: 2px solid #7f8c8d; padding: 20px; margin: 20px 0; min-height: 120px; background: white; display: flex; align-items: center; justify-content: center;">
    """
    
    # IMAGEN DE FIRMA CONTRAPARTE
    if contraparte.get("imagen_base64"):
        html_content += f'<img src="data:image/png;base64,{contraparte["imagen_base64"]}" style="max-width: 200px; max-height: 100px;" alt="Firma Contraparte">'
    else:
        html_content += '<p style="color: #95a5a6; font-style: italic;">Espacio para firma y sello</p>'
    
    html_content += f"""
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <p><strong>Nombre:</strong> {contraparte.get('nombre', '________________________________')}</p>
                    <p><strong>Cargo:</strong> {contraparte.get('cargo', '_________________________________')}</p>
                    <p><strong>Institución:</strong> {contraparte.get('institucion', '___________________________')}</p>
                </div>
            </div>
            
            <!-- FIRMA INSTITUCIÓN -->
            <div style="text-align: center; width: 45%; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;">
                <h4 style="color: #34495e; margin-bottom: 30px;">👤 INSTITUCIÓN</h4>
                
                <div style="border-bottom: 2px solid #7f8c8d; padding: 20px; margin: 20px 0; min-height: 120px; background: white; display: flex; align-items: center; justify-content: center;">
    """
    
    # IMAGEN DE FIRMA INSTITUCIÓN
    if institucion.get("imagen_base64"):
        html_content += f'<img src="data:image/png;base64,{institucion["imagen_base64"]}" style="max-width: 200px; max-height: 100px;" alt="Firma Institución">'
    else:
        html_content += '<p style="color: #95a5a6; font-style: italic;">Espacio para firma y sello</p>'
    
    html_content += f"""
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <p><strong>Nombre:</strong> {institucion.get('nombre', '________________________________')}</p>
                    <p><strong>Cargo:</strong> {institucion.get('cargo', '_________________________________')}</p>
                    <p><strong>Institución:</strong> {institucion.get('institucion', '___________________________')}</p>
                </div>
            </div>
        </div>
        
        <!-- FECHA DE FIRMA -->
        <div style="text-align: center; margin-top: 40px; padding: 20px; background: #e8f4f8; border-radius: 8px;">
    """
    
    # FECHA DE FIRMA REAL
    fecha_firma = firmas.get("fecha_firma", "")
    if fecha_firma:
        html_content += f"""
            <p style="font-size: 16px; font-weight: bold; color: #2c3e50;">
                FECHA DE FIRMA: {fecha_firma}
            </p>
        """
    else:
        html_content += """
            <p style="font-size: 16px; font-weight: bold; color: #2c3e50;">
                FECHA DE FIRMA: _________________________
            </p>
            <p style="color: #7f8c8d; font-size: 14px; margin-top: 10px;">
                (dd/mm/aaaa)
            </p>
        """
    
    html_content += """
        </div>
    </div>
    """


    # SECCIÓN DE FICHAS DE COMPROMISO
    if agr.get('fichas'):
        html_content += """
            <div class="section">
                <h3>📊 FICHAS DE COMPROMISO</h3>
        """
        
        for ficha in agr.get('fichas', []):
            # Determinar clase CSS para el estado de la ficha
            estado_ficha = "estado-pendiente"
            if any(meta.get('cumplimiento_calc') for meta in ficha.get('metas', [])):
                estado_ficha = "estado-en-progreso"
            
            html_content += f"""
                <div class="ficha">
                    <h4>📋 {ficha.get('id', '')} - {ficha.get('nombre', 'Sin nombre')}</h4>
                    <table>
                        <tr><th style="width: 25%;">Tipo de Meta:</th><td>{ficha.get('tipo_meta', 'No especificado')}</td></tr>
                        <tr><th>Responsables de Cumplimiento:</th><td>{ficha.get('responsables_cumpl', 'No especificado')}</td></tr>
                        <tr><th>Objetivo:</th><td>{ficha.get('objetivo', 'No especificado')}</td></tr>
                        <tr><th>Indicador:</th><td>{ficha.get('indicador', 'No especificado')}</td></tr>
                        <tr><th>Forma de Cálculo:</th><td>{ficha.get('forma_calculo', 'No especificado')}</td></tr>
                        <tr><th>Fuente de Información:</th><td>{ficha.get('fuente', 'No especificado')}</td></tr>
                        <tr><th>Valor Base:</th><td>{ficha.get('valor_base', 'No especificado')}</td></tr>
                        <tr><th>Responsables de Seguimiento:</th><td>{ficha.get('responsables_seguimiento', 'No especificado')}</td></tr>
                        <tr><th>Observaciones:</th><td>{ficha.get('observaciones', 'No especificado')}</td></tr>
                        <tr><th>Requiere Salvaguarda:</th><td>{"SÍ" if ficha.get('salvaguarda_flag') else "NO"}</td></tr>
            """
            
            if ficha.get('salvaguarda_flag'):
                html_content += f"""<tr><th>Texto de Salvaguarda:</th><td>{ficha.get('salvaguarda_text', '')}</td></tr>"""
            
            html_content += """
                    </table>
            """
            
            # METAS ASOCIADAS
            if ficha.get('metas'):
                html_content += """
                    <h5 style="margin-top: 20px; color: #007bff;">🎯 METAS ASOCIADAS:</h5>
                """
                
                for meta in ficha.get('metas', []):
                    # Determinar estado de la meta para el color
                    cumplimiento_meta = meta.get('cumplimiento_calc')
                    estado_clase = "estado-no-cumplida"
                    estado_texto = "No Cumplida"
                    
                    if cumplimiento_meta is not None:
                        if cumplimiento_meta >= 95:
                            estado_clase = "estado-cumplida"
                            estado_texto = "Cumplida"
                        elif cumplimiento_meta >= 60:
                            estado_clase = "estado-parcial"
                            estado_texto = "Parcial"
                    
                    html_content += f"""
                        <div class="meta {'hito' if meta.get('es_hito') else ''}">
                            <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 10px;">
                                <h6 style="margin: 0; flex-grow: 1;">Meta {meta.get('numero', '')}: {meta.get('descripcion', 'Sin descripción')}</h6>
                                <span class="estado-meta {estado_clase}">{estado_texto}</span>
                            </div>
                            <table>
                                <tr>
                                    <th style="width: 20%;">Unidad:</th><td>{meta.get('unidad', 'No especificado')}</td>
                                    <th style="width: 20%;">Valor Objetivo:</th><td>{meta.get('valor_objetivo', 'No especificado')}</td>
                                </tr>
                                <tr>
                                    <th>Sentido:</th><td>{meta.get('sentido', 'No especificado')}</td>
                                    <th>Frecuencia:</th><td>{meta.get('frecuencia', 'No especificado')}</td>
                                </tr>
                                <tr>
                                    <th>Vencimiento:</th><td>{meta.get('vencimiento', 'No especificado')}</td>
                                    <th>Es Hito:</th><td>{"SÍ" if meta.get('es_hito') else "NO"}</td>
                                </tr>
                                <tr>
                                    <th>Ponderación:</th><td>{meta.get('ponderacion', 0)}%</td>
                                    <th class="cumplimiento">Cumplimiento Calculado:</th>
                                    <td class="cumplimiento">{f"{meta.get('cumplimiento_calc', 0):.2f}%" if meta.get('cumplimiento_calc') is not None else "No calculado"}</td>
                                </tr>
                                <tr><th>Observaciones:</th><td colspan="3">{meta.get('observaciones', 'No especificado')}</td></tr>
                    """
                    
                    # RANGOS DE CUMPLIMIENTO
                    if meta.get('rango'):
                        html_content += """
                                <tr><td colspan="4">
                                    <h7 style="display: block; margin: 10px 0 5px 0; font-weight: bold;">📈 Rangos de Cumplimiento:</h7>
                                    <table style="width: 100%; margin: 5px 0;">
                                        <tr><th>Mínimo</th><th>Máximo</th><th>Porcentaje</th></tr>
                        """
                        for rango in meta.get('rango', []):
                            html_content += f"""
                                        <tr>
                                            <td>{rango.get('min', '-')}</td>
                                            <td>{rango.get('max', '-')}</td>
                                            <td>{rango.get('porcentaje', '-')}%</td>
                                        </tr>
                            """
                        html_content += """
                                    </table>
                                </td></tr>
                        """
                    
                    html_content += """
                            </table>
                        </div>
                    """
            
            html_content += "</div>"  # Cierre de ficha
        
        html_content += "</div>"  # Cierre de sección de fichas
    
    # FOOTER
    html_content += f"""
            <div class="footer">
                <p>Documento generado automáticamente por el Sistema de Compromisos de Gestión</p>
                <p>Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p>Este documento es confidencial y para uso exclusivo de las partes involucradas</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def generate_agreement_code(year: int, external_prefix: Optional[str]=None) -> str:
    db = agreements_load()
    existing_codes = [agr["id"] for agr in db.values() if "id" in agr]
    
    # 🆕 Pasar el external_prefix como organism_prefix
    n = get_next_sequential_number("AC", year, existing_codes, organism_prefix=external_prefix)
    base = format_counter_number(n)
    
    if external_prefix:
        return f"AC_{external_prefix.upper()}_{base}_{year}"
    return f"AC_{base}_{year}"  # ← AC_0001_2023

def generate_meta_code(year: int, ficha_id: str) -> str:
    db = agreements_load()
    metas = []
    for agr in db.values():
        for ficha in agr.get("fichas", []):
            if ficha.get("id") == ficha_id:
                metas.extend(ficha.get("metas", []))
    existing_codes = [m["id"] for m in metas if "id" in m]
    n = get_next_sequential_number("M", year, existing_codes)
    base = format_counter_number(n)
    return f"M_{base}_{ficha_id}"

# === SISTEMA DE VERSIONADO ===

def crear_version_acuerdo(agr: Dict[str, Any], usuario: str, motivo: str,
                         cambios: Dict[str, Any] = None) -> Dict[str, Any]:
    """Crea una nueva versión del acuerdo con snapshot completo"""
    # Snapshot del acuerdo actual (sin referencias)
    import copy
    snapshot = copy.deepcopy(agr)
    
    # Remover datos temporales del snapshot
    snapshot.pop("versions", None)
    snapshot.pop("approval_flow", None)
    snapshot.pop("current_version", None)
    
    version = {
        "version_id": f"V{len(agr.get('versions', [])) + 1:04d}",
        "version_number": len(agr.get('versions', [])) + 1,
        "timestamp": datetime.now().isoformat(),
        "usuario": usuario,
        "motivo": motivo,
        "estado_anterior": agr.get('estado'),
        "estado_nuevo": agr.get('estado'), # Puede cambiar después
        "cambios_detectados": cambios or {},
        "snapshot": snapshot
    }
    return version

def registrar_cambio_estado(agr: Dict[str, Any], usuario: str, rol: str,
                           estado_anterior: str, estado_nuevo: str,
                           comentario: str = "") -> Dict[str, Any]:
    """Registra un cambio de estado en el flujo de aprobación"""
    cambio = {
        "action_id": gen_uuid("CHG"),
        "timestamp": datetime.now().isoformat(),
        "usuario": usuario,
        "rol": rol,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "comentario": comentario,
        "action_type": "cambio_estado"
    }
    return cambio

def puede_cambiar_estado(estado_actual: str, estado_nuevo: str, rol_usuario: str) -> bool:
    """Define qué transiciones de estado son permitidas por cada rol - VERSIÓN CORREGIDA"""
    
    # 🆕 CORRECIÓN: Usar los estados EXACTOS de tu sistema
    flujo_aprobacion = {
        "Borrador": {
            "allowed_roles": ["Administrador", "Responsable de Acuerdo"],
            "transiciones": ["Pendiente de Revisión"]
        },
        "Pendiente de Revisión": {
            "allowed_roles": ["Administrador", "Supervisor OPP"],
            "transiciones": ["En Revisión OPP", "Rechazado"]
        },
        "En Revisión OPP": {
            "allowed_roles": ["Administrador", "Supervisor OPP", "Comisión CG"],
            "transiciones": ["En Revisión Comisión CG", "Validado", "Rechazado"]
        },
        "Validado": {
            "allowed_roles": ["Administrador", "Supervisor OPP", "Comisión CG"],
            "transiciones": ["En Revisión Comisión CG", "Validado", "Rechazado"]
        },    
        "En Revisión Comisión CG": {
            "allowed_roles": ["Administrador", "Comisión CG"],
            "transiciones": ["Aprobado", "Rechazado"]
        },
        "Aprobado": {
            "allowed_roles": ["Administrador", "Comisión CG"],
            "transiciones": ["Archivado"]
        },
        "Rechazado": {
            "allowed_roles": ["Administrador", "Responsable de Acuerdo"],
            "transiciones": ["Borrador", "Pendiente de Revisión"]
        },
        "Archivado": {
            "allowed_roles": ["Administrador"],
            "transiciones": ["Aprobado"]  # Reactivar desde archivado
        }
    }
    
    if estado_actual not in flujo_aprobacion:
        return False
    
    reglas = flujo_aprobacion[estado_actual]
    
    # Verificar rol y transición permitida
    if (rol_usuario in reglas["allowed_roles"] and 
        estado_nuevo in reglas["transiciones"]):
        return True
    
    # Administrador puede hacer cualquier cambio
    if rol_usuario == "Administrador":
        return True
    
    return False

def reset_counters(kind: Optional[str] = None, year: Optional[int] = None):
    """
    Reinicia los contadores basándose en los datos existentes.
    Útil para corregir inconsistencias.
    Args:
        kind: Tipo de contador ("agreements", "fichas", "metas") o None para todos
        year: Año específico o None para todos los años
    """
    counters = load_json(COUNTERS_FILE, {"agreements": {}, "fichas": {}, "metas": {}})
    
    if kind is None:
        # Reiniciar todos los contadores
        for k in ["agreements", "fichas", "metas"]:
            if year is None:
                # Reiniciar todos los años para este tipo
                counters[k] = {}
                # Opcional: puedes recorrer todos los años existentes y resetearlos
                # Pero vaciar el diccionario es más simple
            else:
                ys = str(year)
                counters[k][ys] = find_max_existing_number(k, year)
    else:
        # Reiniciar contador específico
        if year is None:
            counters[kind] = {}
        else:
            ys = str(year)
            counters[kind][ys] = find_max_existing_number(kind, year)
            
    save_json(COUNTERS_FILE, counters)
    print(f"Contadores reinicializados: {kind if kind else 'todos'} - año {year if year else 'todos'}")

def reset_counters_force_start():
    """
    Fuerza a que los contadores empiecen desde 1 para el año actual
    """
    year = date.today().year
    counters = load_json(COUNTERS_FILE, {"agreements": {}, "fichas": {}, "metas": {}})
    ys = str(year)
    counters["agreements"][ys] = 0
    counters["fichas"][ys] = 0
    counters["metas"][ys] = 0
    save_json(COUNTERS_FILE, counters)
    st.success("Contadores reiniciados para empezar desde 1")

def gen_uuid(prefix:str="ID") -> str:
    return f"{prefix}_{secrets.token_hex(6)}"

def agreements_load() -> Dict[str, Any]:
    """Cargar acuerdos desde JSON con cache manual - VERSIÓN SEGURA"""
    
    # 🆕 VERIFICAR CACHE PRIMERO
    if 'acuerdos_db' in st.session_state:
        cached_db = st.session_state['acuerdos_db']
        # 🆕 VALIDACIÓN ESTRICTA DEL TIPO
        if isinstance(cached_db, dict) and all(isinstance(k, str) for k in cached_db.keys()):
            return cached_db
        else:
            # Cache corrupto - limpiar
            try:
                del st.session_state['acuerdos_db']
            except:
                pass
    
    # 🆕 CARGAR DESDE JSON
    db = load_json(AGREEMENTS_FILE, {})
    
    # 🆕 GARANTIZAR QUE SEA Dict[str, Any]
    if not isinstance(db, dict):
        db = {}
    else:
        # Filtrar keys que no sean strings
        db = {str(k): v for k, v in db.items()}
    
    # 🆕 GUARDAR EN CACHE
    st.session_state['acuerdos_db'] = db
    
    return db

def agreements_save(db):
    """
    💾 Guarda acuerdos en la base de datos y limpia caches relevantes
    CON DEBUG MEJORADO PARA FIRMAS + CACHE NUEVO
    """
    try:
        # 🆕 DIAGNÓSTICO DETALLADO DE FIRMAS (MANTENER)
        print(f"🔍 AGREEMENTS_SAVE - Iniciando guardado...")
        print(f"   📊 Acuerdos en memoria: {len(db)}")
        
        # 🆕 VERIFICAR FIRMAS EN CADA ACUERDO (MANTENER)
        acuerdos_con_firmas = 0
        for acuerdo_id, acuerdo in db.items():
            if acuerdo.get('firmas'):
                acuerdos_con_firmas += 1
                firmas = acuerdo['firmas']
                print(f"   📝 ACUERDO CON FIRMAS: {acuerdo_id}")
                print(f"      - Contraparte: {firmas.get('contraparte', {}).get('nombre', 'No hay')}")
                print(f"      - Institución: {firmas.get('institucion', {}).get('nombre', 'No hay')}")
                print(f"      - Fecha firma: {firmas.get('fecha_firma', 'No hay')}")
                print(f"      - Imagen contraparte: {'✅' if firmas.get('contraparte', {}).get('imagen_base64') else '❌'}")
                print(f"      - Imagen institución: {'✅' if firmas.get('institucion', {}).get('imagen_base64') else '❌'}")
        
        print(f"   📋 Resumen: {acuerdos_con_firmas} acuerdos tienen firmas")
        
        # 🆕 LIMPIAR CACHES DE STREAMLIT ANTES DE GUARDAR (MANTENER)
        try:
            st.cache_data.clear()
        except:
            pass

        # 🆕 GUARDAR CON VERIFICACIÓN (MANTENER)
        print(f"   💾 Guardando en: {AGREEMENTS_FILE}")
        # Guardado atómico: escribir a archivo temporal y renombrar
        try:
            tmp_file = AGREEMENTS_FILE + ".tmp"
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, AGREEMENTS_FILE)
        except Exception:
            # Fallback al método original si falla
            save_json(AGREEMENTS_FILE, db)
        
        # 🆕 VERIFICACIÓN EXHAUSTIVA (MANTENER)
        if os.path.exists(AGREEMENTS_FILE):
            file_size = os.path.getsize(AGREEMENTS_FILE)
            print(f"   ✅ Archivo creado - Tamaño: {file_size} bytes")
            
            # Leer y verificar contenido
            with open(AGREEMENTS_FILE, 'r', encoding='utf-8') as f:
                datos_guardados = json.load(f)
            
            # 🆕 VERIFICAR FIRMAS EN ARCHIVO GUARDADO (MANTENER)
            acuerdos_con_firmas_guardadas = 0
            for acuerdo_id, acuerdo in datos_guardados.items():
                if acuerdo.get('firmas'):
                    acuerdos_con_firmas_guardadas += 1
            
            print(f"   📋 Acuerdos en archivo: {len(datos_guardados)}")
            print(f"   📝 Acuerdos con firmas guardadas: {acuerdos_con_firmas_guardadas}")
            
            # 🆕 AGREGAR CACHE NUEVO AQUÍ:
            st.session_state['acuerdos_db'] = db
            print(f"   🔄 Cache actualizado en session_state")
            
            st.success(f"💾 Acuerdos guardados correctamente (tamaño: {file_size} bytes)")
            
            # 🆕 FORZAR ACTUALIZACIÓN DE DATOS EN MEMORIA (MANTENER SI LO NECESITAS)
            # global agreements
            # agreements = agreements_load()
            
            return True
        else:
            print(f"   ❌ ERROR: El archivo no se creó correctamente")
            st.error("❌ Error: El archivo no se creó correctamente")
            return False
            
    except Exception as e:
        print(f"   ❌ EXCEPCIÓN en agreements_save: {str(e)}")
        import traceback
        print(f"   📍 Traceback: {traceback.format_exc()}")
        st.error(f"❌ Error al guardar acuerdos: {str(e)}")
        return False

# 🆕 MANTENER TU FUNCIÓN DE DEBUG
def debug_firmas_acuerdo(db, acuerdo_id):
    """Función rápida para debug de firmas de un acuerdo específico"""
    acuerdo = db.get(acuerdo_id)
    if not acuerdo:
        print(f"🔍 DEBUG: Acuerdo {acuerdo_id} no encontrado")
        return
    
    firmas = acuerdo.get('firmas', {})
    print(f"🔍 DEBUG FIRMAS para {acuerdo_id}:")
    print(f"   - Existen firmas: {'✅' if firmas else '❌'}")
    print(f"   - Contraparte: {firmas.get('contraparte', {}).get('nombre', 'No hay')}")
    print(f"   - Institución: {firmas.get('institucion', {}).get('nombre', 'No hay')}")
    print(f"   - Imagen contraparte: {'✅' if firmas.get('contraparte', {}).get('imagen_base64') else '❌'}")
    print(f"   - Imagen institución: {'✅' if firmas.get('institucion', {}).get('imagen_base64') else '❌'}")

def limpiar_caches():
    """
    🗑️ Limpia todos los caches de Streamlit
    """
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("✅ Caches limpiados correctamente")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error limpiando caches: {str(e)}")

def verificar_archivos_indicadores():
    """Muestra qué archivos de indicadores existen"""
    import glob
    import os
    
    archivos_json = glob.glob("*.json")
    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 Archivos JSON")
    for archivo in archivos_json:
        tamaño = os.path.getsize(archivo)
        st.sidebar.write(f"📄 {archivo} ({tamaño} bytes)")
    
    # Botón para limpiar indicadores
    if st.sidebar.button("🗑️ Limpiar TODOS los indicadores"):
        limpiar_indicadores()

def limpiar_indicadores():
    """Elimina todos los archivos de indicadores"""
    try:
        import glob
        import os
        
        # Buscar archivos comunes de indicadores
        archivos_indicadores = [
            "indicadores.json",
            "seguimiento_indicadores.json", 
            "resultados_metas.json",
            "datos_indicadores.json"
        ]
        
        # Agregar cualquier archivo que contenga "indicador" o "seguimiento"
        otros_archivos = glob.glob("*indicador*.json") + glob.glob("*seguimiento*.json")
        archivos_indicadores.extend(otros_archivos)
        
        eliminados = 0
        for archivo in archivos_indicadores:
            if os.path.exists(archivo):
                os.remove(archivo)
                eliminados += 1
                st.sidebar.success(f"✅ Eliminado: {archivo}")
        
        st.sidebar.success(f"🗑️ {eliminados} archivos de indicadores eliminados")
        st.rerun()
        
    except Exception as e:
        st.sidebar.error(f"❌ Error limpiando indicadores: {str(e)}")

def audit_log(event: str, details: Dict[str, Any]):
    audit = load_json(AUDIT_FILE, [])
    audit.append({"ts": datetime.now().isoformat(), "event": event, "details": details})
    save_json(AUDIT_FILE, audit)

DEFAULT_ROLES = ["Administrador","Responsable de Acuerdo","Supervisor OPP","Comisión CG"]

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
    """Solo crea admin si no existe ningún usuario"""
    users = load_json(USERS_FILE, {})
    
    # Solo crear admin si NO hay usuarios o si admin no existe
    if not users or "admin" not in users:
        if not users:
            users = {}
        users["admin"] = {
            "username": "admin",
            "name": "Administrador", 
            "role": "Administrador",
            "active": True,
            "password": hash_password("admin")  # Contraseña: "admin"
        }
        save_json(USERS_FILE, users)
        print("Usuario admin creado por primera vez")

bootstrap_admin()

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

ESTADOS_ACUERDO = ["Borrador","Pendiente de Revisión", "En Revisión OPP", "Validado", "En Revisión Comisión CG", "Aprobado","Rechazado","Archivado"]
ESTADOS_META = ["No Iniciada","En Progreso","Cumplida","Parcialmente Cumplida","No Cumplida","Verificada"]
ROLES_SISTEMA = ["Administrador","Responsable de Acuerdo","Supervisor OPP","Comisión CG","Consulta"]

def today_str():
    return date.today().isoformat()

def dt_parse(dstr: str) -> Optional[date]:
    try:
        return date.fromisoformat(dstr)
    except Exception:
        return None

def default_agreement(created_by, external_prefix:Optional[str]=None, año_seleccionado:Optional[int]=None):
    # Usar el año seleccionado, o el año actual por defecto
    año = año_seleccionado if año_seleccionado is not None else date.today().year
    code = generate_agreement_code(año, external_prefix=external_prefix)
    return {
        "id": code,
        "tipo_compromiso": TIPO_COMPROMISO[0],
        "organismo_tipo": ORGANISMO_TIPOS[0],
        "organismo_nombre": "",
        "naturaleza_jurídica": "",
        "año": año,  # ← Este es el año correcto
        "vigencia_desde": f"{año}-01-01",
        "vigencia_hasta": f"{año}-12-31",
        "organismo_enlace": "",
        "objeto": "",
        "partes_firmantes": "",
        "normativa_vigente": "",
        "antecedentes": "",
        "estado": "Borrador",
        "created_by": created_by,
        "attachments": [],
        "fichas": [],
        "versions": [],
        "current_version": None,
        "approval_flow": []
    }

def create_sample_agreement(created_by, external_prefix:Optional[str]=None, año_seleccionado:Optional[int]=None):
    """Genera un acuerdo de ejemplo completo para pruebas UI y de distribución de ponderaciones."""
    año = año_seleccionado if año_seleccionado is not None else date.today().year
    code = generate_agreement_code(año, external_prefix=external_prefix)

    sample = default_agreement(created_by, external_prefix=external_prefix, año_seleccionado=año)
    sample.update({
        "id": code,
        "organismo_nombre": "Instituto Ejemplo de Gestión",
        "organismo_tipo": "Institucional",
        "objeto": "Mejorar la gestión interna mediante indicadores y metas claras.",
        "partes_firmantes": "Instituto Ejemplo / Contraparte Demo",
        "estado": "Borrador",
        "fichas": [],
        "firmas": {
            "contraparte": {"nombre": "Juan Contraparte", "cargo": "Gerente", "imagen_base64": ""},
            "institucion": {"nombre": "Instituto Ejemplo", "cargo": "Director", "imagen_base64": ""},
            "fecha_firma": ""
        }
    })

    # Ficha 1 - Institucional
    ficha1 = {
        "id": gen_uuid("FIC"),
        "nombre": "Fortalecimiento Institucional",
        "tipo_meta": "Institucional",
        "metas": []
    }

    ficha1["metas"].append({
        "id": gen_uuid("META"),
        "numero": 1,
        "descripcion": "Implementar un sistema de seguimiento de indicadores institucionales.",
        "unidad_medida": "%",
        "valor_objetivo": 90,
        "frecuencia_medicion": "Mensual",
        "tipo_meta": "Institucional",
        "ponderacion": 0,  # dejar 0 para que el distribuidor calcule
        "estado": "No Iniciada"
    })

    ficha1["metas"].append({
        "id": gen_uuid("META"),
        "numero": 2,
        "descripcion": "Capacitar al 80% del personal en gestión por resultados.",
        "unidad_medida": "%",
        "valor_objetivo": 80,
        "frecuencia_medicion": "Trimestral",
        "tipo_meta": "Grupal",
        "ponderacion": 0,
        "estado": "No Iniciada"
    })

    # Ficha 2 - Operativa
    ficha2 = {
        "id": gen_uuid("FIC"),
        "nombre": "Mejora de Procesos Operativos",
        "tipo_meta": "Funcional",
        "metas": []
    }

    ficha2["metas"].append({
        "id": gen_uuid("META"),
        "numero": 1,
        "descripcion": "Reducir tiempo promedio de atención en 20%.",
        "unidad_medida": "%",
        "valor_objetivo": 20,
        "frecuencia_medicion": "Mensual",
        "tipo_meta": "Individual",
        "ponderacion": 0,
        "estado": "No Iniciada"
    })

    ficha2["metas"].append({
        "id": gen_uuid("META"),
        "numero": 2,
        "descripcion": "Implementar 3 mejoras en procesos críticos.",
        "unidad_medida": "cantidad",
        "valor_objetivo": 3,
        "frecuencia_medicion": "Semestral",
        "tipo_meta": "Grupal",
        "ponderacion": 0,
        "estado": "No Iniciada"
    })

    sample["fichas"].extend([ficha1, ficha2])

    return sample

def parse_bool_si_no(x: str) -> bool:
    return str(x or "").strip().lower() in ["si","sí","true","1","yes"]

def export_csv_horizontal_agreement(acuerdo: Dict[str, Any]) -> str:
    """
    📊 Exporta acuerdo a formato CSV horizontal premium - VERSIÓN CORREGIDA
    
    Args:
        acuerdo: Diccionario con datos del acuerdo
        
    Returns:
        str: Contenido CSV formateado
    """
    
    # 🎨 ENCABEZADOS MEJORADOS CON ESTRUCTURA JERÁRQUICA
    encabezados = [
        # === BLOQUE INFORMACIÓN GENERAL ===
        "id_acuerdo", "año_vigencia", "tipo_compromiso", "estado_actual",
        "tipo_organismo", "nombre_organismo", "organismo_enlace",
        "vigencia_desde", "vigencia_hasta", "creado_por", "responsable_asignado",
        
        # === BLOQUE FICHA COMPROMISO ===
        "id_ficha", "nombre_ficha", "tipo_meta",
        "responsables_cumplimiento", "objetivo_estrategico", "indicador_principal",
        "metodologia_calculo", "fuente_informacion", "valor_linea_base",
        "responsables_seguimiento", "observaciones_ficha",
        "requiere_salvaguarda", "texto_salvaguarda",
        
        # === BLOQUE META ESPECÍFICA ===
        "id_meta", "numero_meta", "descripcion_meta", "estado_meta",
        "unidad_medida", "valor_objetivo", "sentido_cumplimiento",
        "frecuencia_medicion", "fecha_vencimiento", "es_hito_critico",
        "ponderacion_porcentual", "valor_alcanzado", "porcentaje_cumplimiento",
        "observaciones_meta",
        
        # === BLOQUE RANGOS MEJORADO ===
        "cantidad_rangos",
        "rango_1_intervalo", "rango_1_porcentaje", "rango_1_clasificacion",
        "rango_2_intervalo", "rango_2_porcentaje", "rango_2_clasificacion",
        "rango_3_intervalo", "rango_3_porcentaje", "rango_3_clasificacion",
        "rango_4_intervalo", "rango_4_porcentaje", "rango_4_clasificacion",
        "rango_5_intervalo", "rango_5_porcentaje", "rango_5_clasificacion"
    ]

    # 📝 CONFIGURACIÓN CSV AVANZADA
    buffer = io.StringIO()
    escritor = csv.writer(
        buffer,
        delimiter=',',
        quotechar='"',
        quoting=csv.QUOTE_NONNUMERIC,
        lineterminator='\n'
    )

    # ✨ ESCRIBIR ENCABEZADOS
    escritor.writerow(encabezados)

    # 🔄 PROCESAR CADA FICHA Y META
    for ficha in acuerdo.get("fichas", []):
        for meta in ficha.get("metas", []):
            # 🎯 PROCESAMIENTO MEJORADO DE RANGOS
            rangos = meta.get("rango", [])
            datos_rangos_mejorados = [""] * 16  # 5 rangos × 3 campos + cantidad
            
            # Agregar cantidad de rangos como primer campo
            datos_rangos_mejorados[0] = len(rangos)
            
            for indice, rango in enumerate(rangos[:5]):  # Máximo 5 rangos
                if indice < 5:
                    posicion_base = 1 + (indice * 3)  # Saltar campo cantidad
                    
                    # 🆕 FORMATEO INTELIGENTE DE INTERVALOS
                    min_val = rango.get('min', '')
                    max_val = rango.get('max', '')
                    porcentaje = rango.get('porcentaje', '')
                    
                    # Crear intervalo legible
                    if min_val and max_val:
                        intervalo = f"[{min_val} - {max_val}]"
                    elif min_val and not max_val:
                        intervalo = f"[{min_val} → ∞]"
                    elif not min_val and max_val:
                        intervalo = f"[∞ ← {max_val}]"
                    else:
                        intervalo = "[Sin definir]"
                    
                    # 🆕 CLASIFICACIÓN AUTOMÁTICA DEL RANGO
                    try:
                        pct_num = float(porcentaje) if porcentaje else 0
                        if pct_num >= 90:
                            clasificacion = "CUMPLIDO"
                        elif pct_num >= 60:
                            clasificacion = "PARCIAL"
                        else:
                            clasificacion = "BAJO"
                    except (ValueError, TypeError):
                        clasificacion = "NO DEFINIDO"
                    
                    datos_rangos_mejorados[posicion_base] = intervalo
                    datos_rangos_mejorados[posicion_base + 1] = f"{porcentaje}%" if porcentaje else ""
                    datos_rangos_mejorados[posicion_base + 2] = clasificacion

            # 📅 FORMATEADOR DE FECHAS MEJORADO
            def formatear_fecha_legible(fecha_str: str) -> str:
                """Convierte fecha ISO a formato español legible"""
                if not fecha_str:
                    return "No definida"
                try:
                    fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
                    return fecha_obj.strftime("%d/%m/%Y")
                except (ValueError, TypeError):
                    return fecha_str  # Mantener original si hay error

            # 🔢 FORMATEADOR DE VALORES NUMÉRICOS
            def formatear_valor_numerico(valor: Any) -> str:
                """Formatea valores numéricos para mejor legibilidad"""
                if valor is None or valor == "":
                    return "No definido"
                try:
                    num = float(valor)
                    if num.is_integer():
                        return str(int(num))
                    return f"{num:.2f}"
                except (ValueError, TypeError):
                    return str(valor)

            # 🏷️ PREPARAR VALORES LEGIBLES Y CONSISTENTES
            vencimiento_formateado = formatear_fecha_legible(meta.get("vencimiento", ""))
            vigencia_desde_formateado = formatear_fecha_legible(acuerdo.get("vigencia_desde", ""))
            vigencia_hasta_formateado = formatear_fecha_legible(acuerdo.get("vigencia_hasta", ""))
            ponderacion_formateada = formatear_valor_numerico(meta.get("ponderacion", 0))
            cumplimiento_formateado = formatear_valor_numerico(meta.get("cumplimiento_calc", ""))
            valor_objetivo_formateado = formatear_valor_numerico(meta.get("valor_objetivo", ""))

            # ✅ VALORES BOOLEANOS LEGIBLES
            requiere_salvaguarda = "SÍ" if ficha.get("salvaguarda_flag") else "NO"
            es_hito_meta = "SÍ" if meta.get("es_hito") else "NO"

            # ✍️ CONSTRUIR FILA DE DATOS PREMIUM
            fila_datos = [
                # === BLOQUE INFORMACIÓN GENERAL ===
                acuerdo.get("id", "N/D"),
                acuerdo.get("año", "N/D"),  # 🆕 CORREGIDO: 'anio' → 'año'
                acuerdo.get("tipo_compromiso", "No especificado"),
                acuerdo.get("estado", "Sin estado"),
                acuerdo.get("organismo_tipo", "No especificado"),
                acuerdo.get("organismo_nombre", "No especificado"),
                acuerdo.get("organismo_enlace", "No especificado"),
                vigencia_desde_formateado,
                vigencia_hasta_formateado,
                acuerdo.get("created_by", "No especificado"),
                acuerdo.get("responsable_username", "No asignado"),

                # === BLOQUE FICHA COMPROMISO ===
                ficha.get("id", "N/D"),
                ficha.get("nombre", "Sin nombre"),
                ficha.get("tipo_meta", "No especificado"),
                ficha.get("responsables_cumpl", "No asignado"),
                ficha.get("objetivo", "No definido"),
                ficha.get("indicador", "No definido"),
                ficha.get("forma_calculo", "No especificado"),
                ficha.get("fuente", "No definida"),
                ficha.get("valor_base", "No establecido"),
                ficha.get("responsables_seguimiento", "No asignado"),
                ficha.get("observaciones", "Sin observaciones"),
                requiere_salvaguarda,
                ficha.get("salvaguarda_text", "No aplica"),

                # === BLOQUE META ESPECÍFICA ===
                meta.get("id", "N/D"),
                meta.get("numero", "N/D"),
                meta.get("descripcion", "Sin descripción"),
                meta.get("estado", "No iniciada"),
                meta.get("unidad", "No definida"),
                valor_objetivo_formateado,
                meta.get("sentido", "No definido"),
                meta.get("frecuencia", "No definida"),
                vencimiento_formateado,
                es_hito_meta,
                f"{ponderacion_formateada}%",
                formatear_valor_numerico(meta.get("cumplimiento_valor", "")),
                f"{cumplimiento_formateado}%" if cumplimiento_formateado != "No definido" else "No calculado",
                meta.get("observaciones", "Sin observaciones"),

                # === BLOQUE RANGOS MEJORADO ===
                *datos_rangos_mejorados
            ]

            escritor.writerow(fila_datos)

    return buffer.getvalue()

def import_csv_horizontal_to_ficha(df, acuerdo_id):  # ← Simple, 2 parámetros
    """
    📥 Importa una ficha desde formato CSV horizontal
    """
    try:
        if df.empty:
            st.error("❌ El archivo CSV está vacío")
            return None
            
        row = df.iloc[0]
        
        
        # 🆕 ID ÚNICO BASADO EN TIMESTAMP - NO DEPENDE DE CONTAR FICHAS
        timestamp = int(datetime.now().timestamp() * 1000)
        unique_id = timestamp % 100000  # Últimos 5 dígitos
        fid = f"{acuerdo_id}_F{unique_id}"
        
        # 🎯 MAPEO DE CAMPOS BASADO EN TU ESTRUCTURA DE EXPORTACIÓN
        nueva_ficha = {
            "id": fid,
            "nombre": row.get('nombre_ficha', f'Ficha {unique_id}'),
            "tipo_meta": row.get('tipo_meta', 'Institucional'),
            "responsables_cumpl": row.get('responsables_cumplimiento', ''),
            "objetivo": row.get('objetivo_estrategico', ''),
            "indicador": row.get('indicador_principal', ''),
            "forma_calculo": row.get('metodologia_calculo', ''),
            "fuente": row.get('fuente_informacion', ''),
            "valor_base": row.get('valor_linea_base', ''),
            "responsables_seguimiento": row.get('responsables_seguimiento', ''),
            "observaciones": row.get('observaciones_ficha', ''),
            "salvaguarda_flag": row.get('requiere_salvaguarda', 'NO').upper() == 'SÍ',
            "salvaguarda_text": row.get('texto_salvaguarda', ''),
            "metas": []
        }
        
        # 🔄 PROCESAR METAS DESDE EL CSV
        # Agrupar filas por meta (pueden venir múltiples filas para una ficha con diferentes metas)
        metas_dict = {}
        for _, fila in df.iterrows():
            meta_id = fila.get('id_meta')
            if meta_id and meta_id != 'N/D':
                if meta_id not in metas_dict:
                    metas_dict[meta_id] = fila
                else:
                    # Si ya existe, tomar la primera ocurrencia
                    pass
        
        # Si no hay metas específicas, crear una meta por defecto
        if not metas_dict:
            # Crear una meta básica con datos de la primera fila
            meta_id = f"{fid}_M1"
            metas_dict[meta_id] = row
        
        # 🎯 CREAR ESTRUCTURA DE METAS
        for i, (meta_id, meta_data) in enumerate(metas_dict.items()):
            # Procesar fecha de vencimiento
            vencimiento_str = meta_data.get('fecha_vencimiento', '')
            vencimiento = None
            try:
                if vencimiento_str and vencimiento_str != "No definida":
                    # Intentar parsear formato dd/mm/yyyy
                    if '/' in vencimiento_str:
                        day, month, year = map(int, vencimiento_str.split('/'))
                        vencimiento = f"{year:04d}-{month:02d}-{day:02d}"
                    else:
                        vencimiento = vencimiento_str
            except:
                vencimiento = f"{datetime.now().year}-12-31"
            
            # Procesar ponderación
            ponderacion_str = meta_data.get('ponderacion_porcentual', '0%')
            try:
                ponderacion = float(ponderacion_str.replace('%', '').strip())
            except:
                ponderacion = 0.0
            
            # Procesar valor objetivo
            valor_objetivo = meta_data.get('valor_objetivo', '')
            if valor_objetivo == 'No definido':
                valor_objetivo = ''
            
            # Procesar es_hito
            es_hito_str = meta_data.get('es_hito_critico', 'NO')
            es_hito = es_hito_str.upper() == 'SÍ'
            
            # 🆕 PROCESAR RANGOS DE CUMPLIMIENTO
            rangos_importados = []
            try:
                cantidad_rangos = int(meta_data.get('cantidad_rangos', 0))
                for rango_idx in range(min(cantidad_rangos, 5)):
                    base_idx = 1 + (rango_idx * 3)  # Posición base del rango
                    
                    intervalo_str = meta_data.get(f'rango_{rango_idx+1}_intervalo', '')
                    porcentaje_str = meta_data.get(f'rango_{rango_idx+1}_porcentaje', '')
                    
                    if intervalo_str and porcentaje_str:
                        # Parsear intervalo [min - max]
                        intervalo_limpio = intervalo_str.strip('[]')
                        partes = intervalo_limpio.split(' - ')
                        
                        if len(partes) == 2:
                            min_val = partes[0].strip()
                            max_val = partes[1].strip()
                            
                            # Manejar símbolos infinitos
                            min_val = '' if min_val in ['∞', '∞ ←'] else min_val
                            max_val = '' if max_val in ['∞', '→ ∞'] else max_val
                            
                            # Extraer porcentaje numérico
                            porcentaje_num = float(porcentaje_str.replace('%', '').strip())
                            
                            rango = {
                                'min': min_val if min_val else None,
                                'max': max_val if max_val else None,
                                'porcentaje': porcentaje_num
                            }
                            rangos_importados.append(rango)
            except Exception as e:
                st.warning(f"⚠️ No se pudieron importar los rangos de cumplimiento: {str(e)}")
            
            meta = {
                "id": meta_id if meta_id != 'N/D' else f"{fid}_M{i+1}",
                "numero": i + 1,
                "descripcion": meta_data.get('descripcion_meta', f'Meta {i+1}'),
                "unidad": meta_data.get('unidad_medida', '%'),
                "valor_objetivo": valor_objetivo,
                "sentido": meta_data.get('sentido_cumplimiento', '>='),
                "frecuencia": meta_data.get('frecuencia_medicion', 'Anual'),
                "vencimiento": vencimiento or f"{datetime.now().year}-12-31",
                "es_hito": es_hito,
                "ponderacion": ponderacion,
                "observaciones": meta_data.get('observaciones_meta', ''),
                "estado": meta_data.get('estado_meta', 'No Iniciada'),
                "historial_estados": [],
                "rango": rangos_importados,
                "rangos_cumplimiento": rangos_importados.copy() if rangos_importados else [],
                "cumplimiento_valor": meta_data.get('valor_alcanzado', ''),
                "cumplimiento_calc": None
            }
            nueva_ficha["metas"].append(meta)
        
        st.success(f"✅ Ficha '{nueva_ficha['nombre']}' importada exitosamente con {len(nueva_ficha['metas'])} meta(s)")
        return nueva_ficha
        
    except Exception as e:
        st.error(f"❌ Error en importación de CSV: {str(e)}")
        import traceback
        st.error(f"Detalles: {traceback.format_exc()}")
        return None

def crear_plantilla_csv_vacia():
    """
    📝 Crea una plantilla CSV vacía basada en la estructura de exportación
    """
    # Usar los mismos encabezados que tu función de exportación
    encabezados = [
        # === BLOQUE INFORMACIÓN GENERAL ===
        "id_acuerdo", "año_vigencia", "tipo_compromiso", "estado_actual",
        "tipo_organismo", "nombre_organismo", "organismo_enlace",
        "vigencia_desde", "vigencia_hasta", "creado_por", "responsable_asignado",
        
        # === BLOQUE FICHA COMPROMISO ===
        "id_ficha", "nombre_ficha", "tipo_meta",
        "responsables_cumplimiento", "objetivo_estrategico", "indicador_principal",
        "metodologia_calculo", "fuente_informacion", "valor_linea_base",
        "responsables_seguimiento", "observaciones_ficha",
        "requiere_salvaguarda", "texto_salvaguarda",
        
        # === BLOQUE META ESPECÍFICA ===
        "id_meta", "numero_meta", "descripcion_meta", "estado_meta",
        "unidad_medida", "valor_objetivo", "sentido_cumplimiento",
        "frecuencia_medicion", "fecha_vencimiento", "es_hito_critico",
        "ponderacion_porcentual", "valor_alcanzado", "porcentaje_cumplimiento",
        "observaciones_meta",
        
        # === BLOQUE RANGOS MEJORADO ===
        "cantidad_rangos",
        "rango_1_intervalo", "rango_1_porcentaje", "rango_1_clasificacion",
        "rango_2_intervalo", "rango_2_porcentaje", "rango_2_clasificacion",
        "rango_3_intervalo", "rango_3_porcentaje", "rango_3_clasificacion",
        "rango_4_intervalo", "rango_4_porcentaje", "rango_4_clasificacion",
        "rango_5_intervalo", "rango_5_porcentaje", "rango_5_clasificacion"
    ]
    
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(encabezados)
    
    # Fila vacía para que el usuario la llene
    fila_vacia = [""] * len(encabezados)
    writer.writerow(fila_vacia)
    
    return buffer.getvalue()

def calcular_cumplimiento(meta: Dict[str, Any]) -> Optional[float]:
    """
    Calcula el cumplimiento considerando:
    1. Cumplimiento lineal cuando hay un solo rango
    2. Interpolación lineal cuando hay múltiples rangos
    3. Rangos discretos cuando se especifican
    """
    try:
        # 🚨 DEBUG TEMPORAL
        print(f"🔍 DEBUG - Meta: {meta.get('descripcion', 'Sin nombre')}")
        print(f"  - valor_objetivo: '{meta.get('valor_objetivo')}'")
        print(f"  - cumplimiento_valor: '{meta.get('cumplimiento_valor')}'")
        print(f"  - es_hito: {meta.get('es_hito')}")
        
        # ✅ PROTECCIÓN: Verificar que meta no esté vacía
        if not meta or not isinstance(meta, dict):
            print("  ❌ Meta vacía o no es dict")
            return None
        
        v_obj = str(meta.get("valor_objetivo", "")).strip()
        val = str(meta.get("cumplimiento_valor", "")).strip()
        
        print(f"  - v_obj: '{v_obj}', val: '{val}'")
        
        if v_obj == "" or val == "":
            print("  ❌ Valores vacíos")
            return None
        
        # ✅ PROTECCIÓN: Verificar que meta no esté vacía
        if not meta or not isinstance(meta, dict):
            return None
        
        v_obj = str(meta.get("valor_objetivo", "")).strip()
        val = str(meta.get("cumplimiento_valor", "")).strip()
        
        if v_obj == "" or val == "":
            return None
        
        try:
            objetivo = float(v_obj.replace(",", "."))
            valor = float(val.replace(",", "."))
        except:
            if meta.get("es_hito"):
                return 100.0 if val.strip().lower() in ["1", "true", "si", "sí"] else 0.0
            return None
        
        if meta.get("es_hito"):
            return 100.0 if valor >= 1.0 else 0.0
        
        sentido = meta.get("sentido", ">=")
        
        # CALCULAR PORCENTAJE BASE SEGÚN SENTIDO
        if sentido == ">=":
            if objetivo == 0:
                base_pct = 100.0 if valor >= 0 else 0.0
            else:
                base_pct = min((valor / objetivo) * 100.0, 100.0) if objetivo > 0 else 0.0
                
        elif sentido == "<=":
            if objetivo == 0:
                base_pct = 100.0 if valor <= 0 else 0.0
            else:
                base_pct = min((objetivo / valor) * 100.0, 100.0) if valor > 0 else 0.0
        else:  # ==
            if objetivo == 0:
                base_pct = 100.0 if abs(valor - objetivo) < 1e-9 else 0.0
            else:
                diff = abs(valor - objetivo) / abs(objetivo)
                base_pct = max(0.0, 100.0 * (1.0 - diff))
        
        rango = meta.get("rango") or []
        
        # PREPARAR RANGOS VÁLIDOS
        rangos_ordenados = []
        for rg in rango:
            try:
                min_val = float(str(rg.get("min", "")).replace(",", ".")) if str(rg.get("min", "")).strip() != "" else -float('inf')
                max_val = float(str(rg.get("max", "")).replace(",", ".")) if str(rg.get("max", "")).strip() != "" else float('inf')
                pct = float(str(rg.get("porcentaje", "")).replace(",", ".")) if str(rg.get("porcentaje", "")).strip() != "" else None
                
                if pct is not None:
                    rangos_ordenados.append({
                        "min": min_val,
                        "max": max_val,
                        "porcentaje": pct
                    })
            except:
                continue
        
        # ✅ PROTECCIÓN CRÍTICA: Si no hay rangos válidos, usar cumplimiento lineal
        if not rangos_ordenados:
            return max(0.0, min(100.0, base_pct))
        
        # CASO 2: SOLO UN RANGO - CUMPLIMIENTO LINEAL ENTRE 0% Y EL PORCENTAJE DEL RANGO
        if len(rangos_ordenados) == 1:
            rg = rangos_ordenados[0]
            if rg["min"] <= base_pct <= rg["max"]:
                # Si el rango cubre desde 0, usar porcentaje directo
                if rg["min"] <= 0:
                    return max(0.0, min(100.0, rg["porcentaje"]))
                else:
                    # Calcular progreso lineal desde 0 hasta el rango
                    progreso = min(base_pct / rg["min"], 1.0) if rg["min"] > 0 else 0.0
                    return max(0.0, min(100.0, progreso * rg["porcentaje"]))
            elif base_pct < rg["min"]:
                # Por debajo del rango mínimo - progreso lineal desde 0
                progreso = base_pct / rg["min"] if rg["min"] > 0 else 0.0
                return max(0.0, min(100.0, progreso * rg["porcentaje"]))
            else:  # base_pct > rg["max"]
                # Por encima del rango máximo - usar porcentaje máximo
                return max(0.0, min(100.0, rg["porcentaje"]))
        
        # ORDENAR RANGOS POR VALOR MÍNIMO
        rangos_ordenados.sort(key=lambda x: x["min"])
        
        # ✅ PROTECCIÓN: Verificar que el primer rango tenga la clave "min"
        if "min" not in rangos_ordenados[0]:
            return max(0.0, min(100.0, base_pct))
        
        # CASO 3: MÚLTIPLES RANGOS - BUSCAR RANGO EXACTO O INTERPOLAR
        for i, rg in enumerate(rangos_ordenados):
            if rg["min"] <= base_pct <= rg["max"]:
                # VERIFICAR SI PODEMOS INTERPOLAR DENTRO DEL RANGO
                if i < len(rangos_ordenados) - 1:
                    next_rg = rangos_ordenados[i + 1]
                    # Si hay espacio para interpolación dentro del mismo rango
                    if base_pct > rg["min"] and base_pct < rg["max"]:
                        # Interpolación lineal dentro del rango actual
                        rango_ancho = rg["max"] - rg["min"]
                        if rango_ancho > 0:
                            progreso = (base_pct - rg["min"]) / rango_ancho
                            # Si el siguiente rango es continuo, interpolar entre porcentajes
                            if next_rg["min"] == rg["max"]:
                                porcentaje_interpolado = rg["porcentaje"] + progreso * (next_rg["porcentaje"] - rg["porcentaje"])
                                return max(0.0, min(100.0, porcentaje_interpolado))
                
                # Si está exactamente en el rango o no necesita interpolación
                return max(0.0, min(100.0, rg["porcentaje"]))
        
        # CASO 4: INTERPOLACIÓN ENTRE RANGOS (VALOR ENTRE RANGOS)
        for i in range(len(rangos_ordenados) - 1):
            rg_actual = rangos_ordenados[i]
            rg_siguiente = rangos_ordenados[i + 1]
            
            # Si base_pct está entre el máximo del rango actual y el mínimo del siguiente
            if rg_actual["max"] < base_pct < rg_siguiente["min"]:
                # Calcular interpolación lineal entre rangos
                rango_total = rg_siguiente["min"] - rg_actual["max"]
                if rango_total > 0:  # ✅ PROTECCIÓN: Evitar división por cero
                    progreso = (base_pct - rg_actual["max"]) / rango_total
                    porcentaje_interpolado = rg_actual["porcentaje"] + progreso * (rg_siguiente["porcentaje"] - rg_actual["porcentaje"])
                    return max(0.0, min(100.0, porcentaje_interpolado))
        
        # CASO 5: VALORES FUERA DE LOS RANGOS DEFINIDOS
        # ✅ PROTECCIÓN: Verificar que rangos_ordenados no esté vacío antes de acceder
        if rangos_ordenados:
            if base_pct < rangos_ordenados[0]["min"]:
                # Por debajo del primer rango - progreso lineal desde 0
                primer_rango = rangos_ordenados[0]
                if primer_rango["min"] > 0:  # ✅ PROTECCIÓN: Evitar división por cero
                    progreso = base_pct / primer_rango["min"]
                    return max(0.0, min(100.0, progreso * primer_rango["porcentaje"]))
                else:
                    return 0.0
            elif base_pct > rangos_ordenados[-1]["max"]:
                # Por encima del último rango - usar el porcentaje máximo
                return max(0.0, min(100.0, rangos_ordenados[-1]["porcentaje"]))
        
        return 0.0
        
    except Exception as e:
        # ✅ PROTECCIÓN FINAL: Manejo de cualquier error inesperado
        print(f"Error en calcular_cumplimiento: {str(e)}")
        return None

def generar_rangos_automaticos(tipo_meta: str, unidad: str, valor_objetivo: float) -> List[Dict[str, Any]]:
    """
    Genera rangos de cumplimiento automáticos según el tipo de meta
    """
    if not valor_objetivo or valor_objetivo <= 0:
        return []
    
    if tipo_meta.lower() in ["porcentaje", "%"]:
        # Rangos para porcentajes (0-100%)
        return [
            {"min": "0", "max": "60", "porcentaje": "50", "etiqueta": "Bajo"},
            {"min": "60", "max": "80", "porcentaje": "75", "etiqueta": "Medio"},
            {"min": "80", "max": "100", "porcentaje": "100", "etiqueta": "Alto"}
        ]
    
    elif tipo_meta.lower() in ["numerico", "número", "cantidad"]:
        # Rangos para valores numéricos
        return [
            {"min": "0", "max": str(valor_objetivo * 0.6), "porcentaje": "50", "etiqueta": "Bajo"},
            {"min": str(valor_objetivo * 0.6), "max": str(valor_objetivo * 0.8), "porcentaje": "75", "etiqueta": "Medio"},
            {"min": str(valor_objetivo * 0.8), "max": str(valor_objetivo), "porcentaje": "100", "etiqueta": "Alto"}
        ]
    
    elif tipo_meta.lower() in ["sí/no", "binario", "hito"]:
        # Rangos para metas binarias
        return [
            {"min": "0", "max": "0", "porcentaje": "0", "etiqueta": "No cumplido"},
            {"min": "1", "max": "1", "porcentaje": "100", "etiqueta": "Cumplido"}
        ]
    
    else:
        # Rangos genéricos
        return [
            {"min": "0", "max": str(valor_objetivo * 0.5), "porcentaje": "50", "etiqueta": "Parcial"},
            {"min": str(valor_objetivo * 0.5), "max": str(valor_objetivo), "porcentaje": "100", "etiqueta": "Total"}
        ]

def validar_rangos_continuos(rangos: List[Dict[str, Any]]) -> bool:
    """
    Valida que los rangos sean continuos y no se solapen
    """
    if not rangos:
        return True
    
    # Ordenar rangos por valor mínimo
    rangos_ordenados = sorted(rangos, key=lambda x: float(x.get("min", 0)))
    
    for i in range(len(rangos_ordenados) - 1):
        rango_actual = rangos_ordenados[i]
        rango_siguiente = rangos_ordenados[i + 1]
        
        max_actual = float(rango_actual.get("max", 0))
        min_siguiente = float(rango_siguiente.get("min", 0))
        
        if abs(max_actual - min_siguiente) > 0.001:  # Pequeño margen de error
            return False
    
    return True

def clasificar_cumplimiento_meta(porcentaje, clasificacion):
    """Clasifica el porcentaje según los operadores configurados en la clasificación"""
    if porcentaje is None or not isinstance(porcentaje, (int, float)):
        return "⚪ Sin evaluar"
    
    # Obtener configuración de cada categoría
    cumplido = clasificacion["cumplido"]
    parcial = clasificacion["parcial"]
    no_cumplido = clasificacion["no_cumplido"]
    
    # Evaluar cada categoría con su operador específico
    if evaluar_operador_clasificacion(porcentaje, cumplido["operador"], cumplido["valor"]):
        return f"{cumplido['color']} Cumplido"
    elif evaluar_operador_clasificacion(porcentaje, parcial["operador"], parcial["valor"]):
        return f"{parcial['color']} Parcial"
    elif evaluar_operador_clasificacion(porcentaje, no_cumplido["operador"], no_cumplido["valor"]):
        return f"{no_cumplido['color']} No Cumplido"
    else:
        return "⚪ Sin clasificar"

def evaluar_operador_clasificacion(valor, operador, referencia):
    """Evalúa la condición según el operador de clasificación"""
    if operador == "≥": 
        return valor >= referencia
    elif operador == ">": 
        return valor > referencia
    elif operador == "=": 
        return valor == referencia
    elif operador == "≤": 
        return valor <= referencia
    elif operador == "<": 
        return valor < referencia
    return False
    
def periodo_label(meta: Dict[str,Any]) -> str:
    v = dt_parse(meta.get("vencimiento","")) or date.today()
    freq = meta.get("frecuencia","Anual")
    
    if freq == "Mensual":
        # Retorna el mes y año: "ENE-2024", "FEB-2024", etc.
        meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", 
                "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        return f"{meses[v.month-1]}-{v.year}"
    elif freq == "Trimestral":
        # Retorna trimestre: "T1-2024", "T2-2024", etc.
        t = 1 if v.month<=3 else 2 if v.month<=6 else 3 if v.month<=9 else 4
        return f"T{t}-{v.year}"
    elif freq == "Semestral":
        # Retorna semestre: "S1-2024", "S2-2024"
        sem = 1 if v.month<=6 else 2
        return f"S{sem}-{v.year}"
    else:  # Anual
        return f"ANUAL-{v.year}"

def calcular_ponderacion_automatica(ficha: Dict[str, Any]) -> Dict[str, float]:
    """
    Calcula ponderación automática equitativa para las metas de una ficha
    """
    metas = ficha.get("metas", [])
    if not metas:
        return {}
    
    # Agrupar metas por período
    metas_por_periodo = {}
    for meta in metas:
        periodo = periodo_label(meta)
        if periodo not in metas_por_periodo:
            metas_por_periodo[periodo] = []
        metas_por_periodo[periodo].append(meta)
    
    # Calcular ponderación equitativa por período
    ponderaciones = {}
    for periodo, metas_periodo in metas_por_periodo.items():
        if metas_periodo:
            ponderacion_equitativa = 100.0 / len(metas_periodo)
            for i, meta in enumerate(metas_periodo):
                meta_id = meta.get("id", f"meta_{i}")
                ponderaciones[meta_id] = round(ponderacion_equitativa, 2)
    
    return ponderaciones

# ⚠️ DEPRECATED
# La validación y normalización ahora está centralizada en ponderaciones.py
def validar_y_ajustar_ponderaciones(ficha: Dict[str, Any]) -> Dict[str, Any]:
    """
    ⚠️ DEPRECATED.
    No usar.
    La lógica normativa fue centralizada en ponderaciones.py.
    """
    ...

    metas = ficha.get("metas", [])
    if not metas:
        return ficha
    
    # Agrupar por período
    periodos = {}
    for meta in metas:
        periodo = periodo_label(meta)
        if periodo not in periodos:
            periodos[periodo] = []
        periodos[periodo].append(meta)
    
    # Validar cada período
    for periodo, metas_periodo in periodos.items():
        total_ponderacion = sum(float(m.get("ponderacion", 0)) for m in metas_periodo)
        
        if abs(total_ponderacion - 100.0) > 0.1:  # Margen de error
            # Ajustar automáticamente
            if total_ponderacion == 0:
                # Distribución equitativa
                ponderacion_individual = 100.0 / len(metas_periodo)
                for meta in metas_periodo:
                    meta["ponderacion"] = round(ponderacion_individual, 2)
            else:
                # Ajuste proporcional
                factor_ajuste = 100.0 / total_ponderacion
                for meta in metas_periodo:
                    meta["ponderacion"] = round(float(meta.get("ponderacion", 0)) * factor_ajuste, 2)
    
    return ficha    

def agregar_tipo_cg(ficha: Dict[str, Any]) -> Dict[str, Any]:
    """Agrega el tipo de Compromiso de Gestión a la ficha"""
    if "tipo_cg" not in ficha:
        ficha["tipo_cg"] = "Institucional"  # Por defecto
    return ficha

def validar_estructura_cg(acuerdo: Dict[str, Any]) -> Dict[str, Any]:
    """Valida la estructura completa de CG según el documento"""
    resultados = {
        "valido": True,
        "errores": [],
        "advertencias": []
    }
    
    for ficha in acuerdo.get("fichas", []):
        tipo_cg = ficha.get("tipo_cg", "Institucional")
        
        if tipo_cg == "Institucional":
            # Validar que las ponderaciones por período sumen 100%
            periodos = {}
            for meta in ficha.get("metas", []):
                periodo = periodo_label(meta)
                if periodo not in periodos:
                    periodos[periodo] = 0.0
                periodos[periodo] += float(meta.get("ponderacion", 0.0))
            
            for periodo, suma in periodos.items():
                if abs(suma - 100.0) > 0.01:
                    resultados["valido"] = False
                    resultados["errores"].append(
                        f"Ficha {ficha.get('nombre', ficha['id'])}: Período {periodo} suma {suma:.1f}% (debe ser 100%)"
                    )
        
        elif tipo_cg == "Funcional":
            # Validar distribución de categorías
            categorias = {"Institucional": 0.0, "Grupal": 0.0, "Individual": 0.0}
            for meta in ficha.get("metas", []):
                categoria = meta.get("categoria_funcional", "Institucional")
                if categoria in categorias:
                    categorias[categoria] += float(meta.get("ponderacion", 0.0))
            
            # Verificar distribución sugerida
            if abs(categorias["Institucional"] - 30.0) > 1.0:
                resultados["advertencias"].append(
                    f"Ficha {ficha.get('nombre', ficha['id'])}: Institucional {categorias['Institucional']:.1f}% (sugerido 30%)"
                )
            if abs(categorias["Grupal"] - 50.0) > 1.0:
                resultados["advertencias"].append(
                    f"Ficha {ficha.get('nombre', ficha['id'])}: Grupal {categorias['Grupal']:.1f}% (sugerido 50%)"
                )
            if categorias["Individual"] > 0 and abs(categorias["Individual"] - 20.0) > 1.0:
                resultados["advertencias"].append(
                    f"Ficha {ficha.get('nombre', ficha['id'])}: Individual {categorias['Individual']:.1f}% (sugerido 20%)"
                )
    
    return resultados

def ajustar_ponderaciones_por_tipo(ficha: Dict[str, Any], acuerdo: Dict[str, Any]) -> Dict[str, Any]:
    """Ajusta automáticamente las ponderaciones según el tipo de CG"""
    ficha = agregar_tipo_cg(ficha)
    tipo_cg = ficha["tipo_cg"]
    
    if tipo_cg == "Institucional":
        # Usar la función existente de ajuste por períodos
        return calcular_ponderaciones_ficha(ficha)
    
    elif tipo_cg == "Funcional":
        # Ajustar para CG Funcionales
        metas = ficha.get("metas", [])
        if not metas:
            return ficha
        
        # Agrupar por categoría funcional
        categorias = {}
        for meta in metas:
            categoria = meta.get("categoria_funcional", "Institucional")
            if categoria not in categorias:
                categorias[categoria] = []
            categorias[categoria].append(meta)
        
        # Ajustar cada categoría para que sume el porcentaje sugerido
        for categoria, metas_categoria in categorias.items():
            ponderacion_sugerida = PONDERACIONES_SUGERIDAS.get(categoria, 0.0)
            total_actual = sum(float(m.get("ponderacion", 0)) for m in metas_categoria)
            
            if total_actual == 0:
                # Distribuir equitativamente
                ponderacion_individual = ponderacion_sugerida / len(metas_categoria)
                for meta in metas_categoria:
                    meta["ponderacion"] = round(ponderacion_individual, 2)
            else:
                # Ajustar proporcionalmente
                factor = ponderacion_sugerida / total_actual
                for meta in metas_categoria:
                    meta["ponderacion"] = round(float(meta.get("ponderacion", 0)) * factor, 2)
        
        return ficha
    
    return ficha        

# ==================================================
# FUNCIONES NUEVAS PARA PONDERACIONES
# ==================================================
def validar_ponderaciones_institucionales(ficha, acuerdo=None):
    """
    VALIDA compromisos INSTITUCIONALES - Metas por plazos
    """
    errores = []
    advertencias = []
    
    for plazo_key in ['plazo1', 'plazo2', 'plazo3']:
        if plazo_key in ficha and ficha[plazo_key]:
            metas_plazo = ficha[plazo_key]
            if isinstance(metas_plazo, list) and len(metas_plazo) > 0:
                total_plazo = sum(meta.get('ponderacion', 0) for meta in metas_plazo)
                
                if abs(total_plazo - 100.0) > 1.0:
                    errores.append(f"❌ Plazo institucional {plazo_key} no suma 100%: {total_plazo:.1f}%")
                else:
                    advertencias.append(f"✅ Plazo institucional {plazo_key}: {total_plazo:.1f}%")
                
                # CALCULAR APORTES (CON TOPE AL 100%)
                for meta in metas_plazo:
                    ponderacion = meta.get('ponderacion', 0)
                    cumplimiento = meta.get('cumplimiento', 0)
                    
                    # ✅ APLICAR TOPE AL 100% - CORRECCIÓN CLAVE
                    cumplimiento_topeado = min(cumplimiento, 100.0)
                    aporte = (ponderacion * cumplimiento_topeado) / 100.0
                    meta['aporte'] = round(aporte, 2)
    
    return ficha, errores, advertencias

def validar_ponderaciones_funcionales(ficha, acuerdo=None):
    """
    VALIDA compromisos FUNCIONALES - Metas por plazos
    """
    errores = []
    advertencias = []
    
    for plazo_key in ['plazo1', 'plazo2', 'plazo3']:
        if plazo_key in ficha and ficha[plazo_key]:
            metas_plazo = ficha[plazo_key]
            if isinstance(metas_plazo, list) and len(metas_plazo) > 0:
                total_plazo = sum(meta.get('ponderacion', 0) for meta in metas_plazo)
                
                if abs(total_plazo - 100.0) > 1.0:
                    errores.append(f"❌ Plazo funcional {plazo_key} no suma 100%: {total_plazo:.1f}%")
                else:
                    advertencias.append(f"✅ Plazo funcional {plazo_key}: {total_plazo:.1f}%")
                
                # CALCULAR APORTES (CON TOPE AL 100%)
                for meta in metas_plazo:
                    ponderacion = meta.get('ponderacion', 0)
                    cumplimiento = meta.get('cumplimiento', 0)
                    
                    # ✅ APLICAR TOPE AL 100% - CORRECCIÓN CLAVE
                    cumplimiento_topeado = min(cumplimiento, 100.0)
                    aporte = (ponderacion * cumplimiento_topeado) / 100.0
                    meta['aporte'] = round(aporte, 2)
    
    return ficha, errores, advertencias

def mostrar_esquema_institucional():
    """
    Muestra el esquema de ponderaciones del documento institucional
    """
    st.markdown("---")
    with st.expander("🏛️ **ESQUEMA INSTITUCIONAL DE PONDERACIONES**", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**### Ponderaciones Funcionales**")
            st.metric("Institucional", "30%", delta="SUGERIDO", delta_color="off")
            st.metric("Grupal/Sectorial", "50%", delta="SUGERIDO", delta_color="off") 
            st.metric("Individual", "20%", delta="SUGERIDO", delta_color="off")
            st.metric("**TOTAL**", "**100%**", delta="OBLIGATORIO", delta_color="off")
        
        with col2:
            st.markdown("**### Reglas de Validación**")
            st.write("• ✅ Cada plazo debe sumar 100%")
            st.write("• ℹ️ Individual es opcional")
            st.write("• 🔧 Si Individual = 0%, se redistribuye")
            st.write("• 📊 Tolerancia: ±1% para validación")
        
        with col3:
            st.markdown("**### Aplicación por Plazos**")
            st.write("**Plazo 1:** 100% interno")
            st.write("**Plazo 2:** 100% interno") 
            st.write("**Plazo n:** 100% interno")
            st.write("**Total General:** 100%")
    
    st.markdown("---")

def try_load_logo():
    for fname in LOGO_FILES:
        if os.path.exists(fname):
            try:
                return open(fname, "rb").read()
            except:
                continue
    return None

def header_with_logo():
    logo_data = try_load_logo()
    if logo_data:
        try:
            st.image(logo_data, width=200)
        except:
            pass  # Si el logo no se puede cargar, no se muestra nada.
    # Si no hay logo, no mostramos ningún título, solo la imagen
    st.markdown("---")

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

# ---------------
# NUEVO: helper para índices seguros en selectbox
# ---------------

def safe_index(options: List[Any], value: Any, default: int = 0) -> int:
    """
    Devuelve index de value si está en options, si no devuelve default.
    Previene ValueError cuando value=='' u otro valor inesperado.
    """
    try:
        if value in options:
            return options.index(value)
    except Exception:
        pass
        
    # Si value no está, intentar normalizaciones simples para acentos/minúsculas (opcional)
    sval = str(value or "").strip()
    if not sval:
        return default
        
    # coincidencias por equivalencia simple (ignorando mayúsculas/acentos)
    low = sval.lower()
    for i,opt in enumerate(options):
        if str(opt).lower() == low:
            return i
            
    return default

def get_next_sequential_number(prefix: str, year: int, existing_codes: List[str], organism_prefix: Optional[str] = None) -> int:
    """
    Busca el menor número disponible para el prefijo, año y organismo.
    Ejemplo: 
    - prefix='AC', year=2023, organism_prefix='ATS'
    - existing_codes=['AC_ATS_0001_2023','AC_ATS_0003_2023','AC_OTRO_0001_2023']
    Devuelve: 2 (porque 0001 ya existe para ATS en 2023)
    """
    used_numbers = set()
    
    for code in existing_codes:
        parts = code.split('_')
        
        # Para códigos con prefijo de organismo: AC_ATS_0001_2023
        if len(parts) == 4 and parts[0] == prefix and parts[3] == str(year):
            if organism_prefix and parts[1] == organism_prefix:
                try:
                    used_numbers.add(int(parts[2]))  # El número está en la posición 2
                except ValueError:
                    pass
        # Para códigos sin prefijo de organismo: AC_0001_2023        
        elif len(parts) == 3 and parts[0] == prefix and parts[2] == str(year):
            if not organism_prefix:  # Solo contar si no hay prefijo de organismo
                try:
                    used_numbers.add(int(parts[1]))
                except ValueError:
                    pass
                
    n = 1
    while n in used_numbers:
        n += 1
    return n

# 🆕 FUNCIÓN PARA CORREGIR NUMERACIÓN DE FICHAS
def reset_fichas_counter(year: int):
    """Resetea el contador de fichas para un año específico basado en datos existentes"""
    db = agreements_load()
    max_num = 0
    
    for agr in db.values():
        if agr.get("año") == year:
            for ficha in agr.get("fichas", []):
                ficha_id = ficha.get("id", "")
                if ficha_id.startswith("F_"):
                    try:
                        parts = ficha_id.split("_")
                        if len(parts) >= 2:
                            num = int(parts[1])
                            max_num = max(max_num, num)
                    except ValueError:
                        continue
    
    counters = load_json(COUNTERS_FILE, {"agreements": {}, "fichas": {}, "metas": {}})
    counters["fichas"][str(year)] = max_num
    save_json(COUNTERS_FILE, counters)
    return max_num

def render_fichas_y_metas(acuerdo, editable=False):
    st.markdown("### 📋 Fichas")

    if not acuerdo.get("fichas"):
        st.info("ℹ️ Este acuerdo no tiene fichas")
        return

    for ficha in acuerdo["fichas"]:
        with st.expander(
            f"📄 {ficha.get('nombre', 'Sin nombre')} ({ficha.get('id', 'N/D')})",
            expanded=editable
        ):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.write(f"**Objetivo:** {ficha.get('objetivo', 'N/D')}")
                st.write(f"**Indicador:** {ficha.get('indicador', 'N/D')}")
            with col_f2:
                st.write(f"**Tipo meta:** {ficha.get('tipo_meta', 'N/D')}")
                st.write(f"**Responsables:** {ficha.get('responsables_cumpl', 'N/D')}")

            st.markdown("#### 🎯 Metas")

            if not ficha.get("metas"):
                st.info("ℹ️ Esta ficha no tiene metas")
                continue

            for meta in ficha["metas"]:
                with st.expander(
                    f"🎯 {meta.get('nombre', meta.get('descripcion', 'Sin nombre'))}",
                    expanded=editable
                ):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        st.write(f"**Descripción:** {meta.get('descripcion', 'N/D')}")
                        st.write(f"**Valor objetivo:** {meta.get('valor_objetivo', 'N/D')}")
                        st.write(f"**Unidad:** {meta.get('unidad', 'N/D')}")
                        st.write(f"**Vencimiento:** {meta.get('vencimiento', 'N/D')}")
                    with col_m2:
                        st.write(f"**Ponderación:** {meta.get('ponderacion', 0)}%")
                        st.write(f"**Estado:** {meta.get('estado', 'N/D')}")

def page_login():
    header_with_logo()
     # Mostrar el logo antes del título
    logo_path = "C:/Sys_CG/LOGO OPP.png" 
    st.image(logo_path, width=200)  # Ajusta el tamaño según sea necesario
    
    st.title(APP_TITLE)
    if not PERSIST_OK:
        st.info("⚠️ No hay permisos de escritura. Se trabajará sin persistencia.")
        
    st.subheader("Ingreso")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    colA, colB = st.columns(2)
    if colA.button("Ingresar", use_container_width=True, type="primary"):
        users = load_json(USERS_FILE, {})
        u = users.get(username)
        if u and u.get("active") and check_password(password, u["password"]):
            st.session_state.user = u
            st.session_state.user["username"] = username  # ← IMPORTANTE
            st.success(f"✅ Bienvenido/a, {u.get('name','')} ({u['role']})")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña inválidos, o usuario inactivo.")
            
    if colB.button("Salir", use_container_width=True):
        st.session_state.user = None
        st.rerun()

def page_admin():
    st.title("Administración del Sistema")
    
    # Cargar usuarios
    users = load_json(USERS_FILE, {})
    current_user = st.session_state.user.get('username')
    
    # ==================== SECCIÓN 1: CAMBIAR CONTRASEÑAS ====================
    st.header("🔐 Cambiar Contraseñas")
    
    col_pass1, col_pass2 = st.columns(2)
    with col_pass1:
        usuario_password = st.selectbox(
            "Seleccionar usuario:",
            options=list(users.keys()),
            key="user_password_select"
        )
    
    with col_pass2:
        if usuario_password:
            st.write(f"**Usuario actual:** {usuario_password}")
            st.write(f"**Rol:** {users[usuario_password].get('role', 'N/A')}")
    
    if usuario_password:
        nueva_password = st.text_input("Nueva contraseña:", type="password", key="new_password_input")
        confirmar_password = st.text_input("Confirmar contraseña:", type="password", key="confirm_password_input")
        
        if st.button("🔄 Cambiar Contraseña", type="primary", key="change_password_btn"):
            if nueva_password and nueva_password == confirmar_password:
                users[usuario_password]["password"] = hash_password(nueva_password)
                save_json(USERS_FILE, users)
                st.success(f"✅ Contraseña de {usuario_password} cambiada exitosamente")
                st.rerun()
            elif nueva_password != confirmar_password:
                st.error("❌ Las contraseñas no coinciden")
            else:
                st.error("❌ La contraseña no puede estar vacía")
    
    st.markdown("---")
    
    # ==================== SECCIÓN 2: EDITAR USUARIOS ====================
    st.header("👥 Gestión de Usuarios")
    
    if users:
        for username, user_data in users.items():
            with st.expander(f"**{username}** - {user_data.get('name', 'Sin nombre')} ({user_data.get('role', 'Sin rol')})", expanded=False):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    nuevo_nombre = st.text_input(
                        "Nombre completo:",
                        value=user_data.get('name', ''),
                        key=f"name_{username}"
                    )
                
                with col2:
                    nuevo_rol = st.selectbox(
                        "Rol:",
                        options=ROLES_SISTEMA,
                        index=ROLES_SISTEMA.index(user_data.get('role', 'Usuario')) if user_data.get('role') in ROLES_SISTEMA else 0,
                        key=f"role_{username}"
                    )
                
                with col3:
                    activo = st.checkbox(
                        "Usuario activo",
                        value=user_data.get('active', True),
                        key=f"active_{username}"
                    )
                
                with col4:
                    # Botones de acción
                    if username != current_user:
                        if st.button("🗑️", key=f"delete_{username}", help="Eliminar usuario"):
                            if f"confirm_delete_{username}" not in st.session_state:
                                st.session_state[f"confirm_delete_{username}"] = True
                                st.warning(f"¿Estás seguro de eliminar a {username}? Presiona eliminar nuevamente para confirmar.")
                            else:
                                del users[username]
                                save_json(USERS_FILE, users)
                                st.success(f"Usuario {username} eliminado")
                                st.rerun()
                    else:
                        st.write("👤 **Tú**")
                
                # Botón guardar cambios
                if st.button("💾 Guardar Cambios", key=f"save_{username}"):
                    users[username]["name"] = nuevo_nombre
                    users[username]["role"] = nuevo_rol
                    users[username]["active"] = activo
                    save_json(USERS_FILE, users)
                    st.success(f"✅ Usuario {username} actualizado")
                    st.rerun()
                
                # Información adicional
                st.caption(f"Última modificación: {user_data.get('last_modified', 'N/A')}")
    else:
        st.info("No hay usuarios en el sistema")
    
    st.markdown("---")
    
    # ==================== SECCIÓN 3: CREAR NUEVO USUARIO ====================
    st.header("➕ Crear Nuevo Usuario")
    
    col_new1, col_new2 = st.columns(2)
    with col_new1:
        nuevo_usuario = st.text_input("Usuario*", key="new_user_input")
        nombre_completo = st.text_input("Nombre completo*", key="new_name_input")
    
    with col_new2:
        contraseña = st.text_input("Contraseña*", type="password", key="new_pass_input")
        rol = st.selectbox("Rol*", ROLES_SISTEMA, key="new_role_select")
    
    if st.button("✅ CREAR USUARIO", type="primary", key="create_user_btn"):
        if nuevo_usuario and contraseña and nombre_completo:
            if nuevo_usuario in users:
                st.error("❌ El usuario ya existe")
            else:
                users[nuevo_usuario] = {
                    "password": hash_password(contraseña),
                    "name": nombre_completo,
                    "role": rol,
                    "active": True,
                    "last_modified": datetime.now().isoformat()
                }
                save_json(USERS_FILE, users)
                st.success(f"✅ Usuario '{nuevo_usuario}' creado exitosamente")
                st.info(f"🔑 Credenciales: Usuario: {nuevo_usuario} | Contraseña: {contraseña}")
                st.rerun()
        else:
            st.error("❌ Todos los campos marcados con * son obligatorios")

def page_agreements():
    require_login()
    header_with_logo()
    
    # ✅ CORRECCIÓN: BOTÓN VOLVER CORREGIDO
    st.header("📝 Generar Nuevo Acuerdo")
    
    # 🆕 INICIALIZAR GUARDADO AUTOMÁTICO
    setup_autosave()
    
    # 🆕 SOLUCIÓN SEGURA PARA FECHAS - SIN datetime
    def get_current_year():
        """Obtiene el año actual sin usar datetime directamente"""
        import time
        return time.localtime().tm_year
    
    # Asegurar que 'fy' (año filtro) esté definido
    fy = st.session_state.get("filter_year") or st.session_state.get("fy")
    if not fy:
        try:
            years = sorted({int(agr.get("anio")) for agr in db.values() if agr.get("anio")}, reverse=True)
            fy = years[0] if years else get_current_year()
        except Exception:
            fy = get_current_year()
        st.session_state["filter_year"] = fy
   
    if 'action' in st.session_state and st.session_state.action == "open_agreement":
        st.success("🔵 DEBUG: Detecté clic en 'Abrir'")
        
        if 'selected_agreement' in st.session_state:
            agr_id = st.session_state.selected_agreement
            st.success(f"🟢 DEBUG: ID del acuerdo a abrir: {agr_id}")
            
            # Cargar acuerdo
            acuerdo_actualizado = db.get(agr_id)
            st.success(f"🔴 DEBUG: Acuerdo cargado de DB: {acuerdo_actualizado is not None}")
            
            if acuerdo_actualizado:
                st.success(f"🟡 DEBUG: Nombre acuerdo: {acuerdo_actualizado.get('nombre', 'No name')}")
            else:
                st.error("❌ DEBUG: No se pudo cargar el acuerdo de la DB")
        else:
            st.error("❌ DEBUG: No hay selected_agreement en session_state")
    # ✅ === FIN DEBUG === ✅   
    
            
    # 🆕 INICIALIZAR GUARDADO AUTOMÁTICO
    setup_autosave()
    
    # 🆕 SOLUCIÓN SEGURA PARA FECHAS - SIN datetime
    def get_current_year():
        """Obtiene el año actual sin usar datetime directamente"""
        import time
        return time.localtime().tm_year
    
    # Asegurar que 'fy' (año filtro) esté definido
    fy = st.session_state.get("filter_year") or st.session_state.get("fy")
    if not fy:
        try:
            years = sorted({int(agr.get("anio")) for agr in db.values() if agr.get("anio")}, reverse=True)
            fy = years[0] if years else get_current_year()
        except Exception:
            fy = get_current_year()
        st.session_state["filter_year"] = fy

    # 🆕 VERSIÓN SIN FILTROS - CARGA DIRECTA
    db = agreements_load()
    user = st.session_state.user

    if not db:
        st.info("No hay acuerdos para mostrar")
    
    # 🆕 BOTÓN DE CREACIÓN DE ACUERDOS
    with st.expander("➕ Crear nuevo acuerdo", expanded=False):
        cola, colb = st.columns([2,2])
        use_custom = cola.checkbox("Personalizar código (p.ej. OPP)", value=False)
        external_prefix = None
        if use_custom:
            external_prefix = cola.text_input("Prefijo externo (p.ej. OPP)").strip()

        # 🆕 CAMPO PARA SELECCIONAR EL AÑO
        año_creacion = colb.number_input(
            "Año del acuerdo",
            min_value=2000,
            max_value=2030,
            value=get_current_year(),  # 🆕 Usar la función segura
            step=1,
            help="Seleccione el año para el cual se crea el acuerdo"
        )
        
        if colb.button("Crear nuevo acuerdo"):
            agr = default_agreement(
                st.session_state.user["username"],
                external_prefix=external_prefix if external_prefix else None,
                año_seleccionado=año_creacion  # 🆕 Pasar el año seleccionado
            )
            db[agr["id"]] = agr
            agreements_save(db)
            audit_log("create_agreement", {"id": agr["id"], "by": st.session_state.user["username"]})
            st.success(f"Acuerdo {agr['id']} creado")
            st.rerun()

        # Botón para insertar un acuerdo de ejemplo completo (útil para pruebas)
        if colb.button("Insertar ejemplo completo", key="insert_sample_agreement"):
            try:
                sample = create_sample_agreement(st.session_state.user["username"], año_seleccionado=año_creacion)
                db[sample["id"]] = sample
                agreements_save(db)
                audit_log("create_sample_agreement", {"id": sample["id"], "by": st.session_state.user["username"]})
                st.success(f"Ejemplo insertado: {sample['id']}")
                st.rerun()
            except Exception as e:
                st.error(f"Error al insertar ejemplo: {e}")

    # 🆕 INFORMACIÓN SOBRE CLONACIÓN
    st.info("""
    💡 **¿Necesitas clonar un acuerdo existente?** 
    Ve a la opción **"📋 Clonar Acuerdos"** en el menú lateral para clonar acuerdos de años anteriores.
    """)

    # 🆕 SIN FILTROS TEMPORALES - MOSTRAR TODOS LOS ACUERDOS
    try:
        # Intentar con date
        years = sorted({a.get("año", date.today().year) for a in db.values()}) if db else [date.today().year]
    except AttributeError:
        # Fallback a datetime
        years = sorted({a.get("año", datetime.now().year) for a in db.values()}) if db else [datetime.now().year]
    fy = st.selectbox("Filtrar por año", options=years, index=len(years)-1)
    ft = st.selectbox("Tipo de compromiso", options=TIPO_COMPROMISO, 
                     index=safe_index(TIPO_COMPROMISO, TIPO_COMPROMISO[0]))
    
    # ==============================================
    # 🆕 INSTRUCCIONES PARA EL USUARIO
    # ==============================================
    st.markdown("### 📋 ¿Cómo ver un acuerdo?")
    st.markdown("""
    - **📂 Ver**: Muestra una vista rápida del acuerdo aquí mismo
    - **📂 Abrir acuerdo completo**: Lleva a la edición completa con todos los formularios
    """)
    st.markdown("---")
       
    # 🆕 MOSTRAR TODOS LOS ACUERDOS SIN FILTRAR POR USUARIO
    for current_agr_id, current_agr in db.items():
        if current_agr.get("año") != fy or current_agr.get("tipo_compromiso") != ft:
            continue
            
        st.markdown("---")
        cols = st.columns([3, 2, 2, 1, 1])  # ← 5 columnas (sin el botón "Ver")
        
        with cols[0]:
            st.write(f"**{current_agr.get('organismo_nombre') or 'Sin nombre'}**")
            st.write(f"*Código: {current_agr_id}*")
            
        with cols[1]:
            st.write(f"**Año:** {current_agr.get('año')}")
            st.write(f"**Tipo:** {current_agr.get('tipo_compromiso')}")
            
        with cols[2]:
            st.write(f"**Estado:** {current_agr.get('estado')}")
            st.write(f"**Fichas:** {len(current_agr.get('fichas', []))}")
            
        with cols[3]:
            # 🆕 🆕 🆕 CAMBIO 1: BOTÓN MEJORADO - VER RÁPIDO 🆕 🆕 🆕
            if st.session_state.get("vista_rapida") == current_agr_id:
                if st.button("📂 Cerrar vista", key=f"close_quick_{current_agr_id}"):
                    st.session_state["vista_rapida"] = None
            else:
                if st.button("📂 Ver", key=f"view_{current_agr_id}"):
                    # Solo muestra vista rápida, no cambia open_agr
                    st.session_state["vista_rapida"] = current_agr_id
                        
        with cols[4]:
            # Solo mostrar botón eliminar para administradores
            if st.session_state.user["role"] in ["Administrador", "Supervisor OPP"]:
                if st.button("🗑️", key=f"delete_{current_agr_id}"):
                    if f"confirm_delete_{current_agr_id}" not in st.session_state:
                        st.session_state[f"confirm_delete_{current_agr_id}"] = True
                        st.warning(f"¿Eliminar {current_agr_id}? Presiona eliminar nuevamente.")
                    else:
                        # Eliminar archivos adjuntos primero
                        for att in current_agr.get("attachments", []):
                            try:
                                if os.path.exists(att.get("path", "")):
                                    os.remove(att["path"])
                            except:
                                pass
                        # Eliminar el acuerdo de la base de datos
                        del db[current_agr_id]
                        agreements_save(db)
                        audit_log("delete_agreement", {"id": current_agr_id, "by": st.session_state.user["username"]})
                        st.success(f"Acuerdo {current_agr_id} eliminado correctamente")
                        st.rerun()

        # ==============================================
        # 🆕 VISTA RÁPIDA DEL ACUERDO (SOLO LECTURA)
        # ==============================================
        if st.session_state.get("vista_rapida") == current_agr_id:
            st.markdown("<hr style='border: 2px solid #4CAF50;'>", unsafe_allow_html=True)
            
            with st.container():
                st.markdown(f"### 📄 **VISTA RÁPIDA: {current_agr_id}**")
                
                # 🆕 INDICAR QUE ES SOLO LECTURA
                estado = current_agr.get('estado', 'Borrador')
                if estado == "Borrador":
                    st.info("🔵 **Acuerdo en borrador** - Para editar usa 'Abrir acuerdo completo'")
                else:
                    st.info("🔒 **Acuerdo aprobado/finalizado** - Solo lectura")
                
                # Crear columnas para la información
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write(f"**Organismo:** {current_agr.get('organismo_nombre', 'No especificado')}")
                    st.write(f"**Año:** {current_agr.get('año', 'No especificado')}")
                    st.write(f"**Código:** {current_agr_id}")
                    
                with col_info2:
                    st.write(f"**Tipo:** {current_agr.get('tipo_compromiso', 'No especificado')}")
                    st.write(f"**Estado:** {current_agr.get('estado', 'No especificado')}")
                    st.write(f"**Fichas:** {len(current_agr.get('fichas', []))}")
                
                # Mostrar más detalles si los tienes
                if current_agr.get('descripcion'):
                    st.markdown("---")
                    st.write(f"**Descripción:** {current_agr.get('descripcion')}")
                
                # Mostrar fichas si existen
                if current_agr.get('fichas'):
                    st.markdown("---")
                    st.write(f"**📋 Fichas ({len(current_agr['fichas'])}):**")
                    for i, ficha in enumerate(current_agr['fichas'], 1):
                        with st.expander(f"{i}. {ficha.get('nombre', 'Ficha sin nombre')}", expanded=False):
                            st.write(f"**Objetivo:** {ficha.get('objetivo', 'N/D')}")
                            st.write(f"**Metas:** {len(ficha.get('metas', []))}")
                
                # 🆕 🆕 🆕 CAMBIO 2: BOTÓN PARA EDITAR COMPLETO 🆕 🆕 🆕
                st.markdown("---")
                col_btn_edit, col_btn_close = st.columns([2, 1])
                
                with col_btn_edit:
                    if st.button("📂 Abrir acuerdo completo para editar", key=f"open_full_{current_agr_id}", use_container_width=True):
                        # Esto llevará a la edición completa
                        st.session_state["open_agr"] = current_agr_id
                        st.session_state["vista_rapida"] = None  # Cerrar vista rápida
                        st.rerun()
                
                with col_btn_close:
                    if st.button("❌ Cerrar vista", key=f"close_view_{current_agr_id}", use_container_width=True):
                        st.session_state["vista_rapida"] = None
                
                st.markdown("<hr style='border: 1px solid #ccc; margin-top: 20px;'>", unsafe_allow_html=True)

    # ==============================================
    # 🆕 VISOR RÁPIDO DE FICHAS Y METAS
    # ==============================================

    st.markdown("---")
    st.subheader("👀 Visor Rápido de Fichas y Metas")

    # Seleccionar acuerdo para ver
    acuerdos_disponibles = list(db.keys())
    if acuerdos_disponibles:
        acuerdo_visor = st.selectbox(
            "Seleccionar acuerdo para ver:",
            options=acuerdos_disponibles,
            format_func=lambda x: f"{x} - {db[x].get('organismo_nombre', 'Sin nombre')}",
            key="acuerdo_visor"
        )
        
        if acuerdo_visor:
            acuerdo = db[acuerdo_visor]
            
            # Información básica del acuerdo
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.write(f"**Organismo:** {acuerdo.get('organismo_nombre', 'N/D')}")
                st.write(f"**Año:** {acuerdo.get('año', 'N/D')}")
            with col_info2:
                st.write(f"**Tipo:** {acuerdo.get('tipo_compromiso', 'N/D')}")
                st.write(f"**Estado:** {acuerdo.get('estado', 'N/D')}")
            
            # Mostrar fichas
            st.markdown("### 📋 Fichas")
            if acuerdo.get("fichas"):
                for ficha in acuerdo["fichas"]:
                    with st.expander(f"📄 {ficha.get('nombre', 'Sin nombre')} ({ficha.get('id', 'N/D')})", expanded=False):
                        # Información de la ficha
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            st.write(f"**Objetivo:** {ficha.get('objetivo', 'N/D')}")
                            st.write(f"**Indicador:** {ficha.get('indicador', 'N/D')}")
                        with col_f2:
                            st.write(f"**Tipo meta:** {ficha.get('tipo_meta', 'N/D')}")
                            st.write(f"**Responsables:** {ficha.get('responsables_cumpl', 'N/D')}")
                        
                        # Mostrar metas
                        st.markdown("#### 🎯 Metas")
                        if ficha.get("metas"):
                            for meta in ficha["metas"]:
                                with st.expander(f"🎯 {meta.get('nombre', meta.get('descripcion', 'Sin nombre'))}", expanded=False):
                                    col_m1, col_m2 = st.columns(2)
                                    with col_m1:
                                        st.write(f"**Descripción:** {meta.get('descripcion', 'N/D')}")
                                        st.write(f"**Valor objetivo:** {meta.get('valor_objetivo', 'N/D')}")
                                        st.write(f"**Unidad:** {meta.get('unidad', 'N/D')}")
                                        st.write(f"**Vencimiento:** {meta.get('vencimiento', 'N/D')}")
                                    with col_m2:
                                        st.write(f"**Ponderación:** {meta.get('ponderacion', 0)}%")
                                        st.write(f"**Estado:** {meta.get('estado', 'N/D')}")
                                        cumplimiento = meta.get('cumplimiento_calc')
                                        if cumplimiento is not None:
                                            st.write(f"**Cumplimiento:** {cumplimiento:.1f}%")
                                        else:
                                            st.write("**Cumplimiento:** Pendiente")
                                    
                                    # Botones de acción
                                    col_btn1, col_btn2 = st.columns(2)
                                    with col_btn1:
                                        # 🆕 🆕 🆕 CAMBIO 3: BOTÓN PARA EDITAR META 🆕 🆕 🆕
                                        if st.button("✏️ Editar", key=f"editar_{meta['id']}"):
                                            st.session_state["open_agr"] = acuerdo_visor
                                            st.rerun()
                                    with col_btn2:
                                        if st.button("🖨️ Imprimir", key=f"imprimir_{meta['id']}"):
                                            # Generar HTML imprimible para esta meta específica
                                            html_content = f"""
                                            <html>
                                            <head><title>Meta {meta['id']}</title></head>
                                            <body>
                                                <h1>Meta: {meta.get('nombre', meta.get('descripcion', 'Sin nombre'))}</h1>
                                                <p><strong>Acuerdo:</strong> {acuerdo['id']}</p>
                                                <p><strong>Ficha:</strong> {ficha.get('nombre', 'N/D')}</p>
                                                <p><strong>Descripción:</strong> {meta.get('descripcion', 'N/D')}</p>
                                                <p><strong>Valor objetivo:</strong> {meta.get('valor_objetivo', 'N/D')}</p>
                                                <p><strong>Ponderación:</strong> {meta.get('ponderacion', 0)}%</p>
                                                <p><strong>Estado:</strong> {meta.get('estado', 'N/D')}</p>
                                            </body>
                                            </html>
                                            """
                                            st.download_button(
                                                "📄 Descargar HTML",
                                                data=html_content.encode('utf-8'),
                                                file_name=f"meta_{meta['id']}.html",
                                                mime="text/html"
                                            )
                        else:
                            st.info("ℹ️ Esta ficha no tiene metas")
            else:
                st.info("ℹ️ Este acuerdo no tiene fichas")
            
            # Botón para abrir acuerdo completo
            st.markdown("---")
            # 🆕 🆕 🆕 CAMBIO 4: BOTÓN MEJORADO EN VISOR RÁPIDO 🆕 🆕 🆕
            if st.button("📂 Abrir Acuerdo Completo", use_container_width=True, key="open_from_visor"):
                st.session_state["open_agr"] = acuerdo_visor
                st.rerun()
    else:
        st.info("📝 No hay acuerdos para mostrar")

    # ------------------------------------------------------------------
    # 🆕 🆕 🆕 CAMBIO 5: AQUÍ COMIENZA LA EDICIÓN COMPLETA 🆕 🆕 🆕
    # ------------------------------------------------------------------
    
    # 🆕 VARIABLE PARA SABER SI MOSTRAMOS EDICIÓN COMPLETA
    mostrar_edicion_completa = False
    acuerdo_editar_id = None
    
    # Verificar si debemos mostrar edición completa
    if "open_agr" in st.session_state and st.session_state["open_agr"] in db:
        acuerdo_editar_id = st.session_state["open_agr"]
        mostrar_edicion_completa = True
    
    # También verificar si venimos del botón "Abrir acuerdo completo" en vista rápida
    elif "acuerdo_para_editar" in st.session_state and st.session_state["acuerdo_para_editar"] in db:
        acuerdo_editar_id = st.session_state["acuerdo_para_editar"]
        mostrar_edicion_completa = True
        # Limpiar para futuras veces
        del st.session_state["acuerdo_para_editar"]
    
    # 🆕 SI HAY ACUERDO PARA EDITAR COMPLETAMENTE
    if mostrar_edicion_completa and acuerdo_editar_id:
        agr = db[acuerdo_editar_id]
        user = st.session_state.user
        
        # 🆕 ENCABEZADO CON BOTÓN PARA VOLVER
        st.markdown("---")
        col_back, col_title = st.columns([1, 4])
        
        with col_back:
            if st.button("← Volver a lista", use_container_width=True, key=f"volver_lista_{agr['id']}"):
                if "open_agr" in st.session_state:
                    del st.session_state["open_agr"]
                st.rerun()
        
        with col_title:
            st.title(f"📝 Editando Acuerdo: {agr['id']}")
        
        # Verificar permisos de edición
        editable = True
        if agr.get("estado") == "Aprobado" and user["role"] not in ["Administrador", "Supervisor OPP", "Responsable de Acuerdo"]:
            editable = False
            st.info("Acuerdo aprobado. Edición limitada.")
            
        # === CÓDIGO DE SEGURIDAD ===
        if st.session_state.user["role"] in ["Administrador", "Supervisor OPP"]:
            col_top1, col_top2, col_top3 = st.columns([4,1,1])
        else:
            col_top1, col_top2 = st.columns([4,1])
        # === FIN CÓDIGO DE SEGURIDAD ===
            
        # ==============================================
        # 🆕 ACCESO DIRECTO A FICHAS Y METAS
        # ==============================================

        # 🆕 BOTÓN PARA IR DIRECTAMENTE A FICHAS
        st.markdown("---")
        col_salto1, col_salto2, col_salto3 = st.columns([1, 2, 1])

        with col_salto2:
            if st.button("🚀 Ir Directamente a Fichas y Metas", use_container_width=True, type="primary", key=f"salto_fichas_{agr['id']}"):
                st.session_state["modo_rapido_fichas"] = True
                st.rerun()

        # 🆕 MODO RÁPIDO ACTIVADO - MOSTRAR SOLO FICHAS
        if st.session_state.get("modo_rapido_fichas"):

            st.title(f"📋 Edición Rápida - {agr['id']}")
            st.info("🔧 **Modo edición directa** - Solo se muestran fichas y metas")

            # ✅ AQUÍ SE MUESTRAN REALMENTE LAS FICHAS
            render_fichas_y_metas(agr, editable=True)

            if st.button("← Volver a vista completa del acuerdo", use_container_width=True):
                st.session_state["modo_rapido_fichas"] = False
                st.rerun()

            st.markdown("---")
            if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                agreements_save(db)
                st.session_state["modo_rapido_fichas"] = False
                st.rerun()

            st.stop()

        # ==============================================
        # CONTINÚA VISTA NORMAL DEL ACUERDO (EDICIÓN COMPLETA)
        # ==============================================
        col_top1.subheader(f"Editar Acuerdo: {agr['id']}")
        if col_top2.button("💾 Guardar Todo"):
            print(f"🎯 BOTÓN GUARDAR TODO PRESIONADO")
            print(f"   Acuerdo actual: {agr['id']}")
            print(f"   Organismo: {agr.get('organismo_nombre', 'No definido')}")
            print(f"   Estado: {agr.get('estado', 'No definido')}")
            
            if agreements_save(db):
                print(f"✅ GUARDADO EXITOSO DESDE BOTÓN")
            else:
                print(f"❌ GUARDADO FALLÓ DESDE BOTÓN")
            
        # === CÓDIGO DE SEGURIDAD ===
        if st.session_state.user["role"] in ["Administrador", "Supervisor OPP"]:
            # Botón de eliminar en vista detallada
            if col_top3.button("🗑️ Eliminar Acuerdo", type="secondary"):
                if st.session_state.get(f"confirm_delete_detailed_{agr['id']}") != True:
                    st.session_state[f"confirm_delete_detailed_{agr['id']}"] = True
                    st.warning(f"¿Estás seguro de eliminar el acuerdo {agr['id']}? Esta acción no se puede deshacer. Presiona eliminar nuevamente para confirmar.")
                else:
                    # Eliminar archivos adjuntos
                    for att in agr.get("attachments", []):
                        try:
                            if os.path.exists(att.get("path", "")):
                                os.remove(att["path"])
                        except:
                            pass
                    # Eliminar el acuerdo
                    del db[agr["id"]]
                    agreements_save(db)
                    audit_log("delete_agreement", {"id": agr["id"], "by": user["username"]})
                    st.success(f"Acuerdo {agr['id']} eliminado correctamente")
                    # Limpiar el estado para volver a la lista
                    if "open_agr" in st.session_state:
                        del st.session_state["open_agr"]
                    st.rerun()

    # ✅ DEFINIR acuerdo_actualizado AQUÍ
    if 'open_agr' in st.session_state and st.session_state.open_agr:
        acuerdo_actualizado = db.get(st.session_state.open_agr)
    else:
        acuerdo_actualizado = None

    # 🆕 🆕 🆕 BOTÓN ACTUALIZAR SISTEMA 🆕 🆕 🆕
    if st.button("🔄 Actualizar Sistema de Indicadores", type="secondary", key="actualizar_sistema_btn"):
        
        # ✅ VERIFICAR QUE HAY ACUERDO ABIERTO
        if acuerdo_actualizado is None:
            st.error("❌ No hay ningún acuerdo abierto para actualizar")
            return
        
        with st.spinner("🔄 Calculando ponderaciones y actualizando indicadores..."):
    
            st.success("🎯 INICIANDO ACTUALIZACIÓN DEL SISTEMA")
            
            # 1. CALCULAR PONDERACIONES SEGÚN NORMATIVA
            for ficha in acuerdo_actualizado.get("fichas", []):
                calcular_ponderaciones_ficha(ficha)
            
            # 🆕 VERIFICAR RESULTADO
            st.success(f"✅ Acuerdo actualizado: {acuerdo_actualizado is not None}")
            if acuerdo_actualizado:
                for ficha in acuerdo_actualizado.get('fichas', []):
                    total_pond = sum(meta.get('ponderacion', 0) for meta in ficha.get('metas', []))
                    st.success(f"📋 Ficha '{ficha.get('nombre')}': {total_pond}% total")
            
            # 2. ACTUALIZAR INDICADORES
            datos_indicadores = cargar_indicadores_json()
            datos_actualizados = actualizar_indicadores_desde_metas(acuerdo_actualizado, datos_indicadores)
            guardar_indicadores_json(datos_actualizados)

            # 3. GUARDAR ACUERDO
            agreements_save(db)
        
        st.success("✅ Sistema actualizado correctamente!")

    # ✅ ✅ ✅ VALIDACIÓN AUTOMÁTICA AL ABRIR ACUERDO ✅ ✅ ✅
    if 'open_agr' in st.session_state and st.session_state.open_agr:
        
        # Verificar si el acuerdo existe (SIN return)
        if acuerdo_actualizado is None:
            st.error("❌ No se pudo cargar el acuerdo")

        # Verificar estructura (SIN return)  
        elif 'fichas' not in acuerdo_actualizado:
            st.error("❌ El acuerdo no tiene fichas")

        else:
            fichas = acuerdo_actualizado['fichas']

            # PROCESAR CADA FICHA SILENCIOSAMENTE
            for fi in fichas:
                # DETECCIÓN MEJORADA DEL TIPO
                es_institucional = any(plazo in fi and fi[plazo] for plazo in ['plazo1', 'plazo2', 'plazo3'])
                es_funcional = any(fi.get(f'ponderacion_{key}', 0) > 0 for key in ['institucional', 'grupal_o_sectorial', 'individual'])

                # DETECCIÓN PARA ESTRUCTURAS ANTIGUAS
                if not es_institucional and not es_funcional:
                    tiene_metas = any('meta' in str(key).lower() for key in fi.keys())
                    tiene_ponderaciones = any('ponderacion' in str(key).lower() for key in fi.keys())
                    
                    if tiene_metas or tiene_ponderaciones:
                        es_institucional = True

                # EJECUTAR VALIDACIONES
                if es_institucional:
                    fi, errores, advertencias = validar_ponderaciones_institucionales(fi, agr)
                    for err in errores:
                        st.error(f"❌ {err}")
                        
                elif es_funcional:
                    fi, errores, advertencias = validar_ponderaciones_funcionales(fi, agr)
                    for err in errores:
                        st.error(f"❌ {err}")
      
        with st.expander("Datos del Acuerdo", expanded=True):
            agr["tipo_compromiso"] = st.selectbox("Tipo de Compromiso", TIPO_COMPROMISO, index=safe_index(TIPO_COMPROMISO, agr.get("tipo_compromiso", TIPO_COMPROMISO[0])), disabled=not editable, on_change=mark_unsaved_changes )
            agr["organismo_tipo"] = st.selectbox("Tipo de Organismo", ORGANISMO_TIPOS, index=safe_index(ORGANISMO_TIPOS, agr.get("organismo_tipo", ORGANISMO_TIPOS[0])), disabled=not editable, on_change=mark_unsaved_changes)
            agr["organismo_nombre"] = st.text_input("Organismo", value=agr.get("organismo_nombre",""), disabled=not editable, on_change=mark_unsaved_changes)
            natmap = load_json(NATURALEZA_MAP_FILE, {})
            def_auto_nat = natmap.get(agr.get("organismo_nombre",""), "")
            agr["naturaleza_juridica"] = st.text_input("Naturaleza Jurídica", value=agr.get("naturaleza_juridica", def_auto_nat), disabled=not editable, on_change=mark_unsaved_changes)
            col4, col5, col6 = st.columns(3)
            agr["año"] = col4.number_input("Año", value=int(agr.get("año", date.today().year)), step=1, disabled=not editable, on_change=mark_unsaved_changes)
            agr["vigencia_desde"] = col5.date_input("Vigencia desde", value=dt_parse(agr.get("vigencia_desde")) or date(agr["año"],1,1), disabled=not editable, on_change=mark_unsaved_changes).isoformat()
            agr["vigencia_hasta"] = col6.date_input("Vigencia hasta", value=dt_parse(agr.get("vigencia_hasta")) or date(agr["año"],12,31), disabled=not editable, on_change=mark_unsaved_changes).isoformat()
            agr["organismo_enlace"] = st.text_input("Organismo de Enlace", value=agr.get("organismo_enlace",""), disabled=not editable, on_change=mark_unsaved_changes)
            agr["objeto"] = st.text_area("Objeto", value=agr.get("objeto",""), disabled=not editable, on_change=mark_unsaved_changes)
            agr["partes_firmantes"] = st.text_area("Partes firmantes", value=agr.get("partes_firmantes",""), disabled=not editable, on_change=mark_unsaved_changes)
            agr["normativa_vigente"] = st.text_area("Normativa Vigente", value=agr.get("normativa_vigente",""), disabled=not editable, on_change=mark_unsaved_changes)
            agr["antecedentes"] = st.text_area("Antecedentes", value=agr.get("antecedentes",""), disabled=not editable, on_change=mark_unsaved_changes)
            
        st.markdown("**Cláusulas del Acuerdo**")
        
        # ✅ CLAÚSULAS POR TIPO DE COMPROMISO (TEXTO REAL COMPLETO)
        clausulas_por_tipo = {
            "Institucional": [
                "CLAÚSULA 1RA. FECHA Y LUGAR DE SUSCRIPCIÓN.\nEl presente Compromiso de Gestión se firma en Montevideo, el _____ de ______ de____",
                
                "CLAÚSULA 2DA. PARTES QUE LO SUSCRIBEN.\nEl presente Compromiso de Gestión se suscribe entre ____________________, en calidad de Organismo Comprometido, representado por __________________ y el Poder Ejecutivo a través de _____________________, representado por___________________.",
                
                "CLAÚSULA 3RA. OBJETO.\nEl objeto de este compromiso de gestión es fijar, de común acuerdo, metas e indicadores que redunden en un mejor cumplimiento de los cometidos sustantivos del organismo comprometido, estableciendo la forma de pago de la contrapartida correspondiente al cumplimiento de dichas metas de gestión.",
                
                "CLAÚSULA 4TA. PERÍODO DE VIGENCIA DEL COMPROMISO.\nEl presente Compromiso de Gestión tendrá vigencia desde 1º de enero de ____ al 31 de diciembre de ____.",
                
                "CLAÚSULA 5TA. NORMAS ESPECÍFICAS A APLICAR.\n• Ley Nº 18.719, del 27 de diciembre de 2010, art. 752.\n• Ley 19.149, del 24 de octubre de 2013, arts. 57 a 60.\n• Decreto Nº 163/014, del 4 de junio de 2014.\n• Ley ______, del __ de____ de _____, art. ____",
                
                "CLAÚSULA 6TA. COMPROMISOS DE LAS PARTES.\nEl ______________________ se compromete a cumplir con las siguientes metas, que se detallan en el anexo __: \n1. …..\n2. …..\n3. …..\n4. …..\n\nPor su parte el Poder Ejecutivo, a través _____________________, transferirá a ________________ el total de las partidas presupuestales con destino a esa Institución por concepto de subsidio y/o subvención, correspondientes al año ______.",
                
                "CLAÚSULA 7MA. FORMA DE PAGO DEL SUBSIDIO.\nContra la firma del presente compromiso y el cumplimiento de las metas finales que forman parte del Compromiso de Gestión vigente para el ejercicio ________, se habilitará el pago del 50 % del crédito apertura. En caso de que la Comisión de Compromisos de Gestión (CCG) constate un incumplimiento en las metas finales de ________, el porcentaje de ajuste correspondiente será aplicado al momento de liberar el primer pago para ________.\n\nEl cumplimiento de las metas acordadas para el mes de ____________, previa aprobación de la Comisión de Seguimiento y Evaluación (CSE) y el aval de la CCG, habilitará el pago del 40% del crédito vigente, aplicando el porcentaje de ajuste por incumplimiento en caso de corresponder, y el crédito restante se liberará con la presentación de las metas finales.\n\nEl cumplimiento de las metas finales de ______________, previa aprobación de la CSE y el aval de la CCG, así como la suscripción del compromiso para el año _____, serán condicionantes para liberar las partidas correspondientes a ________ en la forma y condiciones que se pacten en el compromiso que se suscriba para dicho ejercicio. En caso de que la CCG constate un incumplimiento en las metas finales de _____________, el porcentaje de ajuste correspondiente será aplicado al momento de liberar el primer pago para ________.\n\nEn todos los casos, los pagos se distribuirán de acuerdo al cronograma a acordar con el Ministerio _____________ y el Ministerio de Economía y Finanzas.\n\nEn caso de autorizarse asignaciones de créditos adicionales con posterioridad a la aprobación del compromiso de gestión, que no refieran a incrementos por ajuste de precios, la Comisión de Seguimiento deberá informar de esta autorización a la CCG, para que la misma se expida sobre las metas a aplicar. La presentación a la CCG deberá acompañarse de una propuesta sobre las metas e indicadores a aplicar para esos créditos adicionales y del período propuesto de vigencia.\n\nEn todos los casos, cuando existan partidas extraordinarias para cubrir demandas judiciales, su pago no estará sujeto a las condiciones establecidas en la presente cláusula.",
                
                "CLAÚSULA 8VA. COMISIÓN DE SEGUIMIENTO Y EVALUACIÓN.\nSe constituirá una Comisión de Seguimiento y Evaluación del Compromiso de Gestión, integrada por las siguientes personas en carácter de titular:\n\nNombre\tInstitución\temail\tTeléfono institucional\n\n\n\n\nY las siguientes personas en carácter de alternos:\n\nNombre\tInstitución\temail\tTeléfono institucional\n\n\n\n\nLa Comisión de Seguimiento y Evaluación tiene como cometido evaluar el grado de cumplimiento de las metas en los plazos establecidos en el compromiso, a partir de la documentación pertinente. El informe de la Comisión de Seguimiento se emitirá en un plazo no superior a 30 días luego de la fecha límite para el cumplimiento de la meta, remitiéndose inmediatamente a la Comisión de Compromisos de Gestión, junto con la documentación y/o informes respaldantes.\n\nEl informe de la Comisión de Seguimiento y Evaluación deberá estar firmado por la totalidad de sus miembros. Las decisiones serán tomadas por mayoría simple del total de sus integrantes.\nLa Comisión de Compromisos de Gestión podrá solicitar en cualquier momento a la Comisión de Seguimiento informes sobre el avance en el cumplimiento del compromiso.",
                
                "CLAÚSULA 9NA. TRANSPARENCIA.\n______________ se compromete a poner a disposición toda información que la Comisión de Seguimiento y Evaluación requiera para el análisis, seguimiento y verificación de los compromisos asumidos a través del presente Compromiso de Gestión.\n\nUna vez suscrito el presente compromiso, se remitirá copia digital a la Comisión de Compromisos de Gestión y se publicará en la página web de la institución.\n\nPor otro lado, ______________ comunicará los resultados del presente Compromiso al Ministerio _______________________ y _____________________, y los publicará en la página web de la Institución.",
                
                "CLAÚSULA 10MA. SALVAGUARDAS.\nLa Comisión de Seguimiento y Evaluación podrá, por consenso y con previa aprobación de la CCG, ajustar las metas establecidas en la cláusula 6ª si su cumplimiento fuera impedido por razones de fuerza mayor o casos fortuitos fuera del control de la organización que presenta el CG, que no puedan ser razonablemente contemplados al momento de formular las metas y/o el indicador.\nLa solicitud de aplicación de una cláusula de salvaguarda deberá ser elevada por la Comisión de Seguimiento y Evaluación a la CCG, con aval de las autoridades correspondientes. Dicha solicitud deberá ser acompañada de la propuesta de sustitución planteada y la fundamentación correspondiente.\nPara ser considerada por la CCG, la solicitud deberá ser presentada, como máximo, antes de transcurrido la mitad del plazo establecido para el cumplimiento de la meta (por ejemplo, en metas semestrales, tres meses antes del vencimiento). La decisión de aceptación o no de la solicitud presentada será competencia de la CCG.",
                
                "CLAÚSULA 11VA. EXCEPCIONES.\nEn caso de verificarse un nivel de incumplimiento superior al 10% en las metas intermedias o finales, la Comisión de Seguimiento y Evaluación deberá presentar ante la CCG un informe explicativo de las causas que motivaron los desvíos observados.\nTomando en consideración las fundamentaciones presentadas, la CCG podra autorizar que los pagos previstos en la Cláusula 7ª se ajusten en una proporción menor al porcentaje de incumplimiento constatado. En caso de aplicar la presente excepción, el pago no podrá ser superior al 90%."
            ],
            "Funcional": [
                "CLAÚSULA 1RA. FECHA Y LUGAR DE SUSCRIPCIÓN.\nEl presente Compromiso de Gestión se firma en Montevideo, el _____ de ______ de____",
                
                "CLAÚSULA 2DA. PARTES QUE LO SUSCRIBEN.\nEl presente Compromiso de Gestión se suscribe entre el Ministerio ______________, representado por _____________ y por la otra parte _______________, representada por _____________________",
                
                "CLAÚSULA 3RA. OBJETO.\nEl objeto de este compromiso de gestión es fijar, de común acuerdo, metas e indicadores que redunden en un mejor cumplimiento de los cometidos sustantivos del organismo comprometido, estableciendo la forma de pago de la contrapartida correspondiente al cumplimiento de dichas metas de gestión.",
                
                "CLAÚSULA 4TA. PERÍODO DE VIGENCIA DEL COMPROMISO.\nEl presente Compromiso de Gestión tendrá vigencia desde 1º de enero de ____ al 31 de diciembre de ____.",
                
                "CLAÚSULA 5TA. NORMAS ESPECÍFICAS A APLICAR.\nSe deberán identificar las Leyes, Decretos y Resoluciones que habiliten el cobro del Compromiso de Gestión y establezcan sus condiciones y reglamentación.",
                
                "CLAÚSULA 6TA. MONTO DEL COMPROMISO DE GESTIÓN.\nSe deberá identificar el monto total y por persona que se podrá cobrar por concepto de Compromiso de Gestión, incluyendo el detalle de diferencias que pudiesen existir por escalafones, grados, roles o niveles salariales, según corresponda.",
                
                "CLAÚSULA 7TA. ALCANCE.\nSe deberá identificar de forma clara que personas tienen derecho al cobro del beneficio, y si existen exclusiones al mismo (generales o voluntarias).",
                
                "CLAÚSULA 8VA. COMPROMISOS DE LAS PARTES.\n______________________ se compromete a cumplir con las siguientes metas, que se detallan en el anexo __: \n1. …..\n2. …..\n3. …..\n4. …..\n\nPor la otra, _______________ se compromete al pago (semestral/anual) de una partida a los funcionarios indicados en la cláusula 7ta como compensación especial.",
                
                "CLAÚSULA 9NA. COMISIÓN DE SEGUIMIENTO Y EVALUACIÓN.\nSe constituirá una Comisión de Seguimiento y Evaluación del Compromiso de Gestión, integrada por las siguientes personas en carácter de titular:\n\nNombre\tInstitución\temail\tTeléfono institucional\n\n\n\n\nY las siguientes personas en carácter de alternos:\n\nNombre\tInstitución\temail\tTeléfono institucional\n\n\n\n\nLa Comisión de Seguimiento y Evaluación tiene como cometido evaluar el grado de cumplimiento de las metas en los plazos establecidos en el compromiso, a partir de la documentación pertinente. El informe de la Comisión de Seguimiento se emitirá en un plazo no superior a 45 días luego de la fecha límite para el cumplimiento de la meta, remitiéndose inmediatamente a la Comisión de Compromisos de Gestión, junto con la documentación y/o informes respaldantes.\n\nEl informe de la Comisión de Seguimiento y Evaluación deberá estar firmado por la totalidad de sus miembros. Las decisiones serán tomadas por mayoría simple del total de sus integrantes.\n\nLa Comisión de Compromisos de Gestión podra solicitar en cualquier momento a la Comisión de Seguimiento informes sobre el avance en el cumplimiento del compromiso.",
                
                "CLAÚSULA 10MA. FORMA DE PAGO.\nEl pago de la partida por CG estará supeditado al rango de cumplimiento de las metas dispuestas en el Anexo, previa aprobación de la CSE y el aval de la CCG.\n\nIdentificar condiciones específicas vinculadas al pago, incluyendo forma y fecha de pago, descuentos vinculados a presentismo y aplicación de topes y exclusiones, entre otras, según corresponda.",
                
                "CLAÚSULA 11VA. TRANSPARENCIA.\n______________ se compromete a poner a disposición toda información que la Comisión de Seguimiento y Evaluación requiera para el análisis, seguimiento y verificación de los compromisos asumidos a través del presente Compromiso de Gestión.\n\nUna vez suscrito el presente compromiso, se remitirá copia digital a la Comisión de Compromisos de Gestión y se publicará en la página web de la institución.\n\nPor otro lado, ______________ publicará los resultados del presente Compromiso en la página web de la Institución.",
                
                "CLAÚSULA 12VA. SALVAGUARDAS Y EXCEPCIONES.\nLa Comisión de Seguimiento y Evaluación podrá, por consenso y con previa aprobación de la CCG, ajustar las metas establecidas en la cláusula 8ª si su cumplimiento fuera impedido por razones de fuerza mayor o casos fortuitos fuera del control de la organización que presenta el CG, que no puedan ser razonablemente contemplados al momento de formular las metas y/o el indicador.\nLa solicitud de aplicación de una cláusula de salvaguarda deberá ser elevada por la Comisión de Seguimiento y Evaluación a la CCG, con aval de las autoridades correspondientes. Dicha solicitud deberá ser acompañada de la propuesta de sustitución planteada y la fundamentación correspondiente.\nPara ser considerada por la CCG, la solicitud deberá ser presentada, como máximo, antes de transcurrido la mitad del plazo establecido para el cumplimiento de la meta (por ejemplo, en metas semestrales, tres meses antes del vencimiento). La decisión de aceptación o no de la solicitud presentada será competencia de la CCG."
            ]
        }

        # Obtener el tipo de compromiso del acuerdo
        tipo_compromiso = agr.get("tipo_compromiso", "Institucional")

        # Si no hay cláusulas o el tipo de compromiso cambió, usar las cláusulas por defecto
        if ("clausulas" not in agr or 
            not agr["clausulas"] or 
            agr.get("_tipo_clausulas") != tipo_compromiso):
            
            agr["clausulas"] = clausulas_por_tipo.get(tipo_compromiso, clausulas_por_tipo["Institucional"]).copy()
            agr["_tipo_clausulas"] = tipo_compromiso  # Marcar qué tipo se usó

        # Mostrar información del tipo seleccionado
        st.info(f"🔹 **Tipo de compromiso:** {tipo_compromiso}")

        # Mostrar cláusulas editables
        for i, clausula in enumerate(agr["clausulas"]):
            agr["clausulas"][i] = st.text_area(
                f"Cláusula {i+1}", 
                value=clausula,
                key=f"clausula_{agr['id']}_{i}", 
                disabled=not editable,
                height=150,  # 👈 Más alto por el texto extenso
                on_change=mark_unsaved_changes
            )

        # Botón para cambiar tipo de cláusulas manualmente
        if editable and st.button("🔄 Actualizar cláusulas según tipo de compromiso"):
            agr["clausulas"] = clausulas_por_tipo.get(tipo_compromiso, clausulas_por_tipo["Institucional"]).copy()
            agr["_tipo_clausulas"] = tipo_compromiso
            st.success("Cláusulas actualizadas según el tipo de compromiso")
            st.rerun()

        # Agregar botón para añadir cláusula vacía
        if editable and st.button("➕ Agregar cláusula adicional"):
            agr["clausulas"].append("Nueva cláusula adicional...")
            st.rerun()

        # 🆕 BOTÓN PARA ELIMINAR CLAÚSULAS (SOLO SI HAY MÁS DE LAS MÍNIMAS)
        if editable and len(agr["clausulas"]) > 1:  # No permitir eliminar todas
            st.markdown("---")
            st.subheader("🗑️ Eliminar Cláusulas")
            
            # Mostrar selectbox para elegir qué cláusula eliminar
            clausulas_options = [f"Cláusula {i+1}" for i in range(len(agr["clausulas"]))]
            clausula_a_eliminar = st.selectbox(
                "Selecciona la cláusula a eliminar:",
                options=clausulas_options,
                key=f"eliminar_select_{agr['id']}"
            )
            
            # Obtener el índice de la cláusula seleccionada
            idx_eliminar = clausulas_options.index(clausula_a_eliminar)
            
            # Mostrar preview de la cláusula a eliminar
            with st.expander("📄 Vista previa de la cláusula seleccionada"):
                texto_preview = agr["clausulas"][idx_eliminar]
                # Mostrar solo los primeros 200 caracteres para no saturar
                if len(texto_preview) > 200:
                    st.text(f"{texto_preview[:200]}...")
                else:
                    st.text(texto_preview)
            
            # Botón de eliminación con confirmación
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🗑️ ELIMINAR CLAÚSULA SELECCIONADA", 
                           type="secondary", 
                           key=f"confirmar_eliminar_{agr['id']}"):
                    
                    # Eliminar la cláusula
                    clausula_eliminada = agr["clausulas"].pop(idx_eliminar)
                    
                    # Guardar cambios
                    agreements_save(db)
                    mark_unsaved_changes()
                    
                    st.success(f"✅ Cláusula {idx_eliminar + 1} eliminada correctamente")
                    st.rerun()

        # 📍 UBICACIÓN: REEMPLAZAR la sección de firmas existente
        # ✅ === SECCIÓN DE FIRMAS CON DEBUG COMPLETO ===
        st.markdown("---")
        st.subheader("📝 Firmas del Acuerdo")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👤 Contraparte**")
            firma_contraparte = componente_firma_imagen("contraparte", agr)
                
        with col2:
            st.markdown("**👤 Institución**") 
            firma_institucion = componente_firma_imagen("institucion", agr)

        # 🆕 CARGAR FECHA EXISTENTE O USAR FECHA POR DEFECTO PARA ACUERDOS NUEVOS
        fecha_firma_existente = None
        if agr.get("firmas", {}).get("fecha_firma"):
            try:
                # Cargar fecha existente del acuerdo
                fecha_str = agr["firmas"]["fecha_firma"]
                # Convertir "2023-03-30" a objeto date
             
                fecha_firma_existente = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except:
                fecha_firma_existente = None

        if fecha_firma_existente:
            # 🆕 ACUERDO VIEJO - Usar fecha existente
            fecha_firma = st.date_input(
                "Fecha de firma del acuerdo*", 
                value=fecha_firma_existente,  # Fecha real del acuerdo
                disabled=not editable, 
                on_change=mark_unsaved_changes
            )
        else:
            # 🆕 ACUERDO NUEVO - Usar fecha actual
            fecha_firma = st.date_input(
                "Fecha de firma del acuerdo*", 
                value=None,  # Esto hará que use la fecha actual
                disabled=not editable, 
                on_change=mark_unsaved_changes
            )


        # 🆕 BOTÓN DE PRUEBA - GUARDADO SIMPLE
        if st.button("💾 GUARDADO DE PRUEBA (Sin firmar)", type="secondary"):
            # Guardar datos de firmas básicos
            agr["firmas"] = {
                "contraparte": firma_contraparte,
                "institucion": firma_institucion,
                "fecha_firma": fecha_firma.isoformat() if fecha_firma else None
            }
                        
            # Guardar
            agreements_save(db)
            st.success("✅ Datos guardados (modo prueba)")
            
        # 🆕 BOTÓN PARA FIRMAR CON NOTIFICACIÓN
        if st.button("📝 Firmar Acuerdo", type="primary", key=f"firmar_{agr['id']}"):
            # Guardar datos de firmas
            agr["firmas"] = {
                "contraparte": firma_contraparte,
                "institucion": firma_institucion,
                "fecha_firma": fecha_firma.strftime("%Y-%m-%d") if fecha_firma else None,
                "firmado_por": st.session_state.user['username'],
                "fecha_firma_completa": datetime.now().isoformat()
            }
             
            # 🆕 REGISTRAR NOTIFICACIÓN LOCAL
            success, mensaje = registrar_notificacion_local(agr, st.session_state.user)
            
            if success:
                agreements_save(db)
                st.success("✅ Acuerdo firmado correctamente")
                st.info(f"📋 {mensaje}")
            else:
                agreements_save(db)
                st.success("✅ Acuerdo firmado")
                st.warning(f"⚠️ {mensaje}")

        # ✅ GUARDADO AUTOMÁTICO MEJORADO
        else:
            # Crear objeto con firmas actuales
            firmas_actualizadas = {
                "contraparte": firma_contraparte,
                "institucion": firma_institucion,
                "fecha_firma": fecha_firma.strftime("%Y-%m-%d") if fecha_firma else None
            }
            
            # Solo guardar si las firmas cambiaron
            if agr.get("firmas") != firmas_actualizadas:
                agr["firmas"] = firmas_actualizadas
                agreements_save(db)
                mark_unsaved_changes()
                st.info("💾 Guardado automático ejecutado")

        # ✅ === FIN SECCIÓN FIRMAS ===
        
        st.markdown("**Adjuntos**")

        # 🆕 VERSIÓN MEJORADA QUE EVITA MEDIA FILES
        up = st.file_uploader("Subir archivos (máx. 5 archivos a la vez)", 
                            accept_multiple_files=True, 
                            key=f"upload_adjuntos_{agr['id']}",
                            disabled=not editable)

        if up and editable:
            if st.button("💾 Guardar Archivos Seleccionados", key=f"save_adjuntos_{agr['id']}"):
                successful_uploads = 0
                    
                for i, file in enumerate(up[:5]):
                    try:
                        # Verificar y crear directorio
                        upload_dir = os.path.join(UPLOADS_DIR, agr["id"])
                        os.makedirs(upload_dir, exist_ok=True)
                            
                        # Generar nombre seguro
                        safe_filename = file.name
                        file_path = os.path.join(upload_dir, safe_filename)
                            
                        # Si el archivo ya existe, agregar timestamp
                        if os.path.exists(file_path):
                            name, ext = os.path.splitext(file.name)
                            safe_filename = f"{name}_{int(time.time())}_{i}{ext}"
                            file_path = os.path.join(upload_dir, safe_filename)
                            
                        # Guardar archivo en disco
                        with open(file_path, "wb") as f:
                            f.write(file.getvalue())
                            
                        # Agregar a la lista de adjuntos del acuerdo
                        if "attachments" not in agr:
                            agr["attachments"] = []
                            
                        # Verificar que no exista ya este archivo
                        existing_files = [a["name"] for a in agr["attachments"]]
                        if safe_filename not in existing_files:
                            agr["attachments"].append({
                                "name": safe_filename,
                                "path": file_path,
                                "upload_time": datetime.now().isoformat()
                            })
                            successful_uploads += 1
                            
                    except Exception as e:
                        st.error(f"Error subiendo {file.name}: {str(e)}")
                    
                if successful_uploads > 0:
                    agreements_save(db)
                    st.success(f"✅ {successful_uploads} archivo(s) guardado(s)")
                    st.rerun()
                else:
                    st.warning("⚠️ No se guardaron nuevos archivos")
                
        if agr.get("attachments"):
            st.markdown("Archivos:")
            uniq=[]; seen=set()
            for att in agr.get("attachments", []):
                if att["name"] not in seen: uniq.append(att); seen.add(att["name"])
            for i, att in enumerate(uniq):
                c1,c2,c3 = st.columns([3,1,1])
                c1.write(f"📄 {att['name']}")
                try:
                    with open(att["path"], "rb") as f:
                        file_data = f.read()
                    c2.download_button("⬇️ Descargar", data=file_data, file_name=att["name"], key=f"dl_{agr['id']}_{i}")
                except:
                    c2.error("No encontrado")
                if c3.button("🗑️", key=f"del_att_{agr['id']}_{i}"):
                    if editable:
                        try:
                            if os.path.exists(att.get("path","")): os.remove(att["path"])
                        except: pass
                        agr["attachments"] = [a for a in agr.get("attachments", []) if a["path"] != att["path"]]
                        agreements_save(db); st.success("Archivo eliminado"); st.rerun()
                    else:
                        st.error("No tienes permisos para eliminar archivos")
                            
        st.subheader("Fichas")
        col_add1, col_add2 = st.columns(2)
        if editable and col_add1.button("➕ Crear Ficha Manual"):
            fid = generate_ficha_code(agr.get("año", date.today().year), agr["id"])
            new_ficha = {
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
            
            agr.setdefault("fichas", []).append(new_ficha)
            agreements_save(db)
            audit_log("create_ficha", {"agr": agr["id"], "ficha": fid, "by": user["username"]})
            st.success(f"Ficha {fid} creada exitosamente")  # ✅ MENSAJE DE CONFIRMACIÓN
            st.rerun()  # ✅ ESTA LÍNEA ES CLAVE
        # 🆕 BOTÓN PARA DISTRIBUIR PONDERACIONES (PREVIEW)
        if editable and col_add2.button("⚖️ Distribuir ponderaciones (Preview)", key=f"preview_dist_{agr['id']}"):
            import copy

            propuesta = copy.deepcopy(agr)

            for ficha in propuesta.get("fichas", []):
                calcular_ponderaciones_ficha(ficha)

            with st.expander("🔎 Vista previa: distribución propuesta", expanded=True):
                for f in propuesta.get('fichas', []):
                    st.markdown(f"**Ficha {f.get('id')} - {f.get('nombre','(sin nombre)')}**")
                    rows = []
                    for m in f.get('metas', []):
                        rows.append({
                            'id': m.get('id',''),
                            'nombre': m.get('nombre',''),
                            'periodo': periodo_label(m),
                            'ponderacion': m.get('ponderacion', 0)
                        })
                    if rows:
                        df_preview = pd.DataFrame(rows)
                        st.dataframe(df_preview, use_container_width=True)
                st.markdown('')
                if st.button('Aplicar distribución propuesta', key=f'apply_dist_{agr["id"]}'):
                    # Crear backup del acuerdo antes de aplicar
                    try:
                        backups_dir = os.path.join(DATA_DIR, 'backups')
                        os.makedirs(backups_dir, exist_ok=True)
                        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                        backup_file = os.path.join(backups_dir, f"{agr['id']}_before_dist_{ts}.json")
                        with open(backup_file, 'w', encoding='utf-8') as bf:
                            json.dump(agr, bf, ensure_ascii=False, indent=2)
                    except Exception:
                        backup_file = None

                    # Calcular cambios por meta
                    cambios = []
                    for f_new in propuesta.get('fichas', []):
                        fid = f_new.get('id')
                        f_old = next((f for f in agr.get('fichas', []) if f.get('id') == fid), None)
                        for m_new in f_new.get('metas', []):
                            mid = m_new.get('id')
                            old_p = None
                            if f_old:
                                m_old = next((m for m in f_old.get('metas', []) if m.get('id') == mid), None)
                                old_p = float(m_old.get('ponderacion', 0) or 0) if m_old else None
                            new_p = float(m_new.get('ponderacion', 0) or 0)
                            if old_p is None or abs((old_p or 0) - new_p) > 0.0001:
                                cambios.append({
                                    'ficha_id': fid,
                                    'meta_id': mid,
                                    'old': old_p,
                                    'new': new_p
                                })

                    # Aplicar y guardar
                    db[agr['id']] = propuesta
                    agreements_save(db)

                    # Registrar auditoría
                    detalles = {
                        'acuerdo': agr['id'],
                        'by': st.session_state.user.get('username') if st.session_state.get('user') else 'unknown',
                        'timestamp': datetime.now().isoformat(),
                        'cambios': cambios,
                        'backup': backup_file
                    }
                    try:
                        audit_log('apply_distribution', detalles)
                    except Exception:
                        pass

                    st.success('✅ Distribución aplicada al acuerdo (audit registrada)')
                    st.rerun()
                # UI para restaurar desde backups: mostrar lista y permitir elegir cuál restaurar
                backups_dir = os.path.join(DATA_DIR, 'backups')
                pattern = f"{agr['id']}_before_dist_"
                candidates = []
                if os.path.exists(backups_dir):
                    for fn in os.listdir(backups_dir):
                        if fn.startswith(pattern) and fn.endswith('.json'):
                            candidates.append(fn)

                if not candidates:
                    st.info('No hay backups de distribución disponibles para este acuerdo')
                else:
                    # Ordenar por nombre (timestamp en filename) descendente
                    candidates_sorted = sorted(candidates, reverse=True)
                    choice = st.selectbox('Seleccionar backup a restaurar', options=candidates_sorted, key=f'backup_choice_{agr["id"]}')
                    if st.button('↩️ Restaurar backup seleccionado', key=f'restore_choice_{agr["id"]}'):
                        try:
                            selected_path = os.path.join(backups_dir, choice)
                            with open(selected_path, 'r', encoding='utf-8') as lf:
                                original = json.load(lf)
                            db[agr['id']] = original
                            agreements_save(db)
                            audit_log('undo_distribution', {
                                'acuerdo': agr['id'],
                                'by': st.session_state.user.get('username') if st.session_state.get('user') else 'unknown',
                                'restored_from': selected_path,
                                'timestamp': datetime.now().isoformat()
                            })
                            st.success(f'↩️ Restaurado desde: {choice}')
                            st.rerun()
                        except Exception as e:
                            st.error(f'❌ Error al restaurar backup: {e}')

                    # ------------------ Vista de Auditoría (por acuerdo) ------------------
                    try:
                        with st.expander("🧾 Ver auditoría de cambios", expanded=False):
                            audit_data = load_json(AUDIT_FILE, []) or []
                            if not isinstance(audit_data, list):
                                audit_data = list(audit_data)

                            # Filtrar por acuerdo o mostrar todo
                            opciones_filtro = ["Todos"] + sorted({(e.get('details', {}).get('acuerdo') or e.get('details', {}).get('acuerdo_id') or '') for e in audit_data if e})
                            filtro = st.selectbox("Filtrar por acuerdo", options=opciones_filtro, key=f'audit_filter_{agr["id"]}')

                            # Número de entradas a mostrar
                            limite = st.number_input("Mostrar últimas entradas", min_value=1, max_value=500, value=50, step=1, key=f'audit_limit_{agr["id"]}')

                            # Preparar entries
                            entries = []
                            for e in reversed(audit_data):  # mostrar más recientes primero
                                if filtro and filtro != "Todos":
                                    detalle = e.get('details', {}) or {}
                                    acuerdo_rel = detalle.get('acuerdo') or detalle.get('acuerdo_id') or ''
                                    if acuerdo_rel != filtro:
                                        continue
                                details_str = json.dumps(e.get('details', {}), ensure_ascii=False)
                                entries.append({
                                    'ts': e.get('ts'),
                                    'event': e.get('event'),
                                    'details': details_str
                                })
                                if len(entries) >= limite:
                                    break

                            if entries:
                                df_audit = pd.DataFrame(entries)
                                st.dataframe(df_audit, use_container_width=True)
                                # Descargar selección
                                st.download_button(
                                    label='📥 Descargar selección (JSON)',
                                    data=json.dumps(entries, ensure_ascii=False, indent=2),
                                    file_name=f'audit_selection_{agr["id"]}.json',
                                    mime='application/json',
                                    key=f'download_audit_{agr["id"]}'
                                )
                            else:
                                st.info('No hay entradas de auditoría para los filtros seleccionados')

                            if st.button('🔄 Recargar auditoría', key=f'reload_audit_{agr["id"]}'):
                                st.rerun()
                    except Exception as e:
                        st.error(f'Error mostrando auditoría: {e}')
            
        # 🆕 SOLUCIÓN: MOSTRAR SIEMPRE LAS HERRAMIENTAS DE CARGA MASIVA - INSERTAR AQUÍ
        if editable:
            with st.expander("📊 Herramientas de Carga Masiva - Formato Horizontal", expanded=False):
                st.info("""
                **📥 Cargar múltiples fichas y metas usando formato CSV horizontal**
                    
                **Pasos:**
                1. Descargue la plantilla CSV horizontal
                2. Complete los datos de fichas y metas
                3. Suba el archivo CSV completado
                """)
                    
                # 🆕 DESCARGAR PLANTILLA MEJORADA
                sample_horiz = export_csv_horizontal_agreement(agr)
                st.download_button(
                    "⬇️ Descargar Plantilla CSV Horizontal",
                    data=sample_horiz.encode("utf-8"),
                    file_name=f"{agr['id']}_plantilla_horizontal.csv",
                    mime="text/csv",
                    key=f"download_template_{agr['id']}"
                )
                    
                # 🆕 SUBIR ARCHIVO CSV
                upl = st.file_uploader(
                    "Subir CSV con fichas y metas", 
                    type=["csv"],
                    key=f"csv_upload_{agr['id']}"
                )
                    
                if upl:
                    try:
                        with st.spinner("Procesando archivo CSV..."):
                            fichas_antes = len(agr.get("fichas", []))
                            imported = detectar_y_importar_csv(upl.getvalue(), agr)
                            agreements_save(db)
                            fichas_despues = len(agr.get("fichas", []))
                                
                            if imported > 0:
                                st.success(f"✅ Importación completada. {imported} registros procesados")
                                st.metric("Fichas agregadas", fichas_despues - fichas_antes)
                                    
                                # Mostrar resumen
                                st.info("📊 Resumen de importación:")
                                st.write(f"• Fichas antes: {fichas_antes}")
                                st.write(f"• Fichas después: {fichas_despues}")
                                st.write(f"• Registros procesados: {imported}")
                                    
                                # Botón para ver fichas
                                if st.button("👀 Ver fichas importadas", key=f"view_imported_{agr['id']}"):
                                    st.rerun()
                            else:
                                st.warning("⚠️ No se importaron nuevos registros")
                                    
                    except Exception as e:
                        st.error(f"❌ Error en la importación: {str(e)}")
                        st.info("💡 Asegúrese de que el archivo CSV tenga el formato correcto.")
            
        # 🆕 SOLUCIÓN PROBLEMA 6: BOTONES DE IMPORTACIÓN/EXPORTACIÓN SIEMPRE VISIBLES
        if editable:
            # 🆕 BOTÓN PARA MOSTRAR/OCULTAR HERRAMIENTAS AVANZADAS
            show_tools = st.session_state.get('show_import_export', False)
            if col_add2.button("📊 🔄 Mostrar Herramientas Avanzadas" if not show_tools else "📊 🔄 Ocultar Herramientas Avanzadas"):
                st.session_state.show_import_export = not show_tools
                st.rerun()

        # 🆕 HERRAMIENTAS AVANZADAS SIEMPRE ACCESIBLES PERO COLAPSABLES
        if editable and st.session_state.get('show_import_export', False):
            with st.expander("🛠️ HERRAMIENTAS AVANZADAS - Importación/Exportación Masiva", expanded=True):
                
                st.markdown("### 📥 Importación Masiva")
                
                col_imp1, col_imp2 = st.columns([2, 1])
                
                with col_imp1:
                    # 🆕 SUBIR ARCHIVO CSV CON MEJOR UI
                    upl = st.file_uploader(
                        "Subir archivo CSV con fichas y metas", 
                        type=["csv"],
                        help="Suba un archivo CSV con el formato de plantilla horizontal",
                        key=f"csv_upload_advanced_{agr['id']}"
                    )
                    
                    if upl:
                        try:
                            with st.spinner("🔄 Procesando archivo CSV..."):
                                fichas_antes = len(agr.get("fichas", []))
                                imported = detectar_y_importar_csv(upl.getvalue(), agr)
                                agreements_save(db)
                                fichas_despues = len(agr.get("fichas", []))
                                
                                if imported > 0:
                                    st.success(f"✅ Importación completada exitosamente!")
                                    st.balloons()
                                    
                                    # 🆕 PANEL DE RESULTADOS DETALLADO
                                    with st.container():
                                        st.markdown("#### 📊 Resultados de la Importación")
                                        col_res1, col_res2, col_res3 = st.columns(3)
                                        with col_res1:
                                            st.metric("Fichas antes", fichas_antes)
                                        with col_res2:
                                            st.metric("Fichas después", fichas_despues)
                                        with col_res3:
                                            st.metric("Registros importados", imported)
                                    
                                    # 🆕 BOTÓN PARA ACTUALIZAR VISTA
                                    if st.button("🔄 Actualizar vista para ver cambios", key=f"refresh_view_{agr['id']}"):
                                        st.rerun()
                                else:
                                    st.warning("⚠️ No se importaron nuevos registros. Verifique el formato del archivo.")
                                    
                        except Exception as e:
                            st.error(f"❌ Error en la importación: {str(e)}")
                            # 🆕 AYUDA PARA RESOLUCIÓN DE PROBLEMAS
                            with st.expander("🔧 Ayuda para solución de problemas"):
                                st.markdown("""
                                **Problemas comunes:**
                                - El archivo debe estar en formato CSV
                                - Debe usar la plantilla descargada del sistema
                                - Verifique que los encabezados sean correctos
                                - Asegúrese de que el archivo no esté vacío
                                """)
                
                with col_imp2:
                    # 🆕 BOTÓN DE CERRAR MEJORADO
                    if st.button("❌ Cerrar herramientas", use_container_width=True):
                        st.session_state.show_import_export = False
                        st.rerun()
                
                st.markdown("---")
                st.markdown("### 📤 Exportación Masiva")
                
                # 🆕 MÚLTIPLES OPCIONES DE EXPORTACIÓN
                col_exp1, col_exp2, col_exp3 = st.columns(3)
                
                with col_exp1:
                    # Exportar plantilla
                    sample_horiz = export_csv_horizontal_agreement(agr)
                    st.download_button(
                        "⬇️ Descargar Plantilla",
                        data=sample_horiz.encode("utf-8"),
                        file_name=f"{agr['id']}_plantilla_horizontal.csv",
                        mime="text/csv",
                        help="Descargue esta plantilla para cargar datos masivamente",
                        use_container_width=True
                    )
                
                with col_exp2:
                    # Exportar datos actuales
                    current_data = export_csv_horizontal_agreement(agr)
                    st.download_button(
                        "💾 Exportar Datos Actuales",
                        data=current_data.encode("utf-8"),
                        file_name=f"{agr['id']}_datos_actuales.csv",
                        mime="text/csv",
                        help="Exporte todos los datos actuales del acuerdo",
                        use_container_width=True
                    )
                
                with col_exp3:
                    # Exportar JSON completo
                    json_data = json.dumps(agr, ensure_ascii=False, indent=2)
                    st.download_button(
                        "📄 Exportar JSON",
                        data=json_data.encode("utf-8"),
                        file_name=f"{agr['id']}_completo.json",
                        mime="application/json",
                        help="Exporte el acuerdo completo en formato JSON",
                        use_container_width=True
                    )
                
                # 🆕 ESTADÍSTICAS RÁPIDAS
                st.markdown("---")
                st.markdown("### 📈 Estadísticas del Acuerdo")
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Total Fichas", len(agr.get("fichas", [])))
                with col_stat2:
                    total_metas = sum(len(f.get("metas", [])) for f in agr.get("fichas", []))
                    st.metric("Total Metas", total_metas)
                with col_stat3:
                    metas_con_cumplimiento = sum(
                        1 for f in agr.get("fichas", []) 
                        for m in f.get("metas", []) 
                        if m.get("cumplimiento_calc") is not None
                    )
                    st.metric("Metas con Cumplimiento", metas_con_cumplimiento)
                    
        if agr.get("fichas"):
            # Selector de fichas para descarga personalizada
            ficha_ids = [f["id"] for f in agr["fichas"]]
            ficha_nombres = [f"{f['id']} - {f.get('nombre','')}" for f in agr["fichas"]]
            id_to_nombre = dict(zip(ficha_nombres, ficha_ids))
            seleccionadas = st.multiselect(
                "Selecciona fichas para descargar (CSV)",
                options=ficha_nombres,
                default=ficha_nombres if len(ficha_nombres)==1 else []
            )
            
            # SECCIÓN CARGA DESDE CSV
            st.markdown("---")
            st.subheader("📤 Cargar Ficha desde Plantilla CSV")

            col_plantilla1, col_plantilla2, col_plantilla3 = st.columns(3)

            with col_plantilla1:
                plantilla_vacia = crear_plantilla_csv_vacia()
                st.download_button(
                    "📝 Descargar Plantilla Vacía",
                    data=plantilla_vacia.encode("utf-8"),
                    file_name="plantilla_ficha_vacia.csv",
                    key=f"dl_plantilla_{agr['id']}"
                )

            with col_plantilla2:
                uploaded_file = st.file_uploader(
                    "📤 Subir plantilla CSV completada",
                    type=["csv"],
                    key=f"upload_ficha_{agr['id']}"
                )

            with col_plantilla3:
                if uploaded_file is not None:
                    if st.button("📥 Cargar Ficha desde CSV", key=f"btn_cargar_ficha_{agr['id']}"):
                        try:
                            df = pd.read_csv(uploaded_file)
                            nueva_ficha = import_csv_horizontal_to_ficha(df, agr["id"])
                            
                            if nueva_ficha:
                                agr.setdefault("fichas", []).append(nueva_ficha)
                                agreements_save(db)
                                st.success("✅ Ficha cargada exitosamente")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

            # SOLO UN BOTÓN PARA CREAR FICHA MANUAL
            if editable and st.button("➕ Crear Ficha Manual", key=f"add_ficha_manual_{agr['id']}"):
                numero = len(agr.get("fichas", [])) + 1
                fid = f"{agr['id']}_F{numero}"
                
                nueva_ficha = {
                    "id": fid,
                    "nombre": f"Ficha {numero}",
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
                agr.setdefault("fichas", []).append(nueva_ficha)
                agreements_save(db)
                st.rerun() 
                
            for fi_index, fi in enumerate(agr.get("fichas", [])):
                st.markdown("---")
                with st.expander(f"📋 Ficha {fi.get('id')} - {fi.get('nombre','(sin nombre)')}", expanded=False):
                    # Botón de descarga individual de ficha
                    csv_ficha = export_csv_horizontal_agreement({
                        "id": agr["id"],
                        "año": agr["año"],
                        "tipo_compromiso": agr["tipo_compromiso"],
                        "organismo_tipo": agr["organismo_tipo"],
                        "organismo_nombre": agr["organismo_nombre"],
                        "fichas": [fi]
                    })
                    st.download_button(
                        "⬇️ Descargar esta ficha (CSV)",
                        data=csv_ficha.encode("utf-8"),
                        file_name=f"{fi['id']}_ficha.csv",
                        key=f"dl_ficha_{agr['id']}_{fi_index}_{int(time.time())}"
                    )
                    
                    col_f1, col_f2 = st.columns([2,1])
                    fi["nombre"] = col_f1.text_input(
                        "Nombre de la ficha",
                        value=fi.get("nombre",""),
                        key=f"nombre_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    
                    # 🆕 SELECTOR DE TIPO DE COMPROMISO DE GESTIÓN (AGREGAR DESPUÉS DEL NOMBRE)
                    col_tipo1, col_tipo2 = st.columns([2, 1])
                    with col_tipo1:
                        fi["tipo_cg"] = st.selectbox(
                            "Tipo de Compromiso de Gestión",
                            options=["Institucional", "Funcional"],
                            index=0 if fi.get("tipo_cg", "Institucional") == "Institucional" else 1,
                            key=f"tipo_cg_{agr['id']}_{fi_index}"
                        )
                    with col_tipo2:
                        if fi["tipo_cg"] == "Funcional":
                            st.info("🏷️ CG Funcional")
                        else:
                            st.info("🏛️ CG Institucional")

                    tipo_opts = ["Institucional","Grupal/Sectorial","Individual"]
                    fi["tipo_meta"] = col_f2.selectbox(
                        "Tipo de meta",
                        options=tipo_opts,
                        index=safe_index(tipo_opts, fi.get("tipo_meta","Institucional")),
                        key=f"tipo_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    fi["responsables_cumpl"] = st.text_input(
                        "Responsables de cumplimiento",
                        value=fi.get("responsables_cumpl",""),
                        key=f"resp_cumpl_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    fi["objetivo"] = st.text_area(
                        "Objetivo",
                        value=fi.get("objetivo",""),
                        key=f"objetivo_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    fi["indicador"] = st.text_input(
                        "Indicador",
                        value=fi.get("indicador",""),
                        key=f"indicador_{agr['id']}_{fi_index}",
                        disabled=not editable,
                        on_change=mark_unsaved_changes
                    )

                    fi["forma_calculo"] = st.text_area(
                        "Forma de cálculo",
                        value=fi.get("forma_calculo",""),
                        key=f"calc_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    fi["fuente"] = st.text_input(
                        "Fuente de información",
                        value=fi.get("fuente",""),
                        key=f"fuente_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    fi["valor_base"] = st.text_input(
                        "Valor base",
                        value=fi.get("valor_base",""),
                        key=f"base_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    fi["responsables_seguimiento"] = st.text_input(
                        "Responsables de seguimiento",
                        value=fi.get("responsables_seguimiento",""),
                        key=f"resp_seg_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    fi["observaciones"] = st.text_area(
                        "Observaciones",
                        value=fi.get("observaciones",""),
                        key=f"obs_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    col_s1, col_s2 = st.columns(2)
                    fi["salvaguarda_flag"] = col_s1.checkbox(
                        "Requiere salvaguarda",
                        value=fi.get("salvaguarda_flag", False),
                        key=f"salv_flag_{agr['id']}_{fi_index}",
                        disabled=not editable
                    )
                    if fi["salvaguarda_flag"]:
                        fi["salvaguarda_text"] = col_s2.text_area(
                            "Texto de salvaguarda",
                            value=fi.get("salvaguarda_text",""),
                            key=f"salv_text_{agr['id']}_{fi_index}",
                            disabled=not editable
                        )
                        
                    st.markdown("**Metas**")
                    
                    # 🆕 FORMULARIO PARA CREAR NUEVAS METAS
                    with st.form(key=f"form_meta_{agr['id']}_{fi_index}"):
                        nombre_meta = st.text_input("Nombre de la Meta*", 
                                                placeholder="Ej: Entregar 185 viviendas nuevas",
                                                key=f"input_meta_{agr['id']}_{fi_index}")
                        
                        if st.form_submit_button("✅ Crear Nueva Meta", use_container_width=True):
                            if not nombre_meta:
                                st.error("❌ El nombre de la meta es obligatorio")
                            else:
                                numero = len(fi.get("metas", [])) + 1
                                mid = f"{fi['id']}_M{numero}"

                                meta = {
                                    "id": mid,
                                    "numero": numero,
                                    'nombre': nombre_meta,
                                    "unidad": "%",
                                    "valor_objetivo": "",
                                    "sentido": ">=",
                                    "descripcion": f"Meta {numero}",
                                    "frecuencia": "Anual",
                                    "vencimiento": f"{agr.get('año')}-12-31",
                                    "es_hito": False,
                                    "rango": [],
                                    "rangos_cumplimiento": RANGOS_DEFAULT.copy(),
                                    "ponderacion": 0.0,
                                    "cumplimiento_valor": "",
                                    "cumplimiento_calc": None,
                                    "observaciones": "",
                                    "estado": "No Iniciada",
                                    "historial_estados": []
                                }
                                
                                fi.setdefault("metas", []).append(meta)
                                agreements_save(db)
                                st.success(f"✅ Meta '{nombre_meta}' creada")
                                st.rerun()
                        
                    if fi.get("metas"):
                        for m_index, m in enumerate(fi.get("metas", [])):
                            with st.expander(f"🎯 Meta {m.get('numero', m_index+1)} - {m.get('descripcion','(sin descripción)')}", expanded=False):
                                col_m1, col_m2 = st.columns(2)
                                m["descripcion"] = col_m1.text_input("Descripción", value=m.get("descripcion",""), key=f"desc_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                unidad_opts = ["%","Número","Días","Sí/No","Otro"]
                                m["unidad"] = col_m2.selectbox("Unidad", options=unidad_opts, index=safe_index(unidad_opts, m.get("unidad","%")), key=f"unidad_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                col_m3, col_m4 = st.columns(2)
                                m["valor_objetivo"] = col_m3.text_input("Valor objetivo", value=m.get("valor_objetivo",""), key=f"obj_{agr['id']}_{fi_index}_{m_index}", disabled=not editable, on_change=mark_unsaved_changes) 
                                sentido_opts = [">=", "<=", "=="]
                                m["sentido"] = col_m4.selectbox("Sentido", options=sentido_opts, index=safe_index(sentido_opts, m.get("sentido",">=")), key=f"sentido_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                col_m5, col_m6 = st.columns(2)
                                freq_opts = ["Anual","Semestral","Trimestral","Mensual"]
                                m["frecuencia"] = col_m5.selectbox("Frecuencia", options=freq_opts, index=safe_index(freq_opts, m.get("frecuencia","Anual")), key=f"freq_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                venc = dt_parse(m.get("vencimiento", f"{agr.get('año')}-12-31")) or date(agr.get("año"),12,31)
                                m["vencimiento"] = col_m6.date_input("Vencimiento", value=venc, key=f"venc_{agr['id']}_{fi_index}_{m_index}", disabled=not editable).isoformat()
                                m["es_hito"] = st.checkbox("Es hito", value=m.get("es_hito", False), key=f"hito_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)

                                # 🆕 SI ES CG FUNCIONAL, MOSTRAR CATEGORÍA (AGREGAR JUSTO DESPUÉS DEL CHECKBOX)
                                if fi.get("tipo_cg") == "Funcional":
                                    st.markdown("---")
                                    st.subheader("🏷️ Categoría Funcional")
                                    col_cat1, col_cat2 = st.columns([3, 1])
                                    with col_cat1:
                                        m["categoria_funcional"] = st.selectbox(
                                            "Categoría Funcional",
                                            options=["Institucional", "Grupal", "Individual"],
                                            index=["Institucional", "Grupal", "Individual"].index(m.get("categoria_funcional", "Institucional")),
                                            key=f"cat_func_{agr['id']}_{fi_index}_{m_index}",
                                            disabled=not editable
                                        )
                                    with col_cat2:
                                        peso_sugerido = 30 if m["categoria_funcional"] == "Institucional" else 50 if m["categoria_funcional"] == "Grupal" else 20
                                        st.metric("Peso Sugerido", f"{peso_sugerido}%")
                                    st.markdown("---")

                                # ==================================================
                                # 🆕 ESTADOS DE META - AGREGAR JUSTO DESPUÉS DE "Es hito"
                                # ==================================================
                                col_estado_meta1, col_estado_meta2 = st.columns(2)
                                with col_estado_meta1:
                                    estado_meta_actual = m.get("estado", "No Iniciada")
                                    nuevo_estado_meta = st.selectbox(
                                        "Estado de la meta:",
                                        options=ESTADOS_META,
                                        index=ESTADOS_META.index(estado_meta_actual) if estado_meta_actual in ESTADOS_META else 0,
                                        key=f"estado_meta_{agr['id']}_{fi_index}_{m_index}",
                                        disabled=not editable
                                    )
                                with col_estado_meta2:
                                    if nuevo_estado_meta != estado_meta_actual:
                                        # Registrar el cambio de estado
                                        if "historial_estados" not in m:
                                            m["historial_estados"] = []
                                        m["historial_estados"].append({
                                            "fecha": datetime.now().isoformat(),
                                            "estado_anterior": estado_meta_actual,
                                            "estado_nuevo": nuevo_estado_meta,
                                            "usuario": st.session_state.user["username"]
                                        })
                                        m["estado"] = nuevo_estado_meta
                                        m["fecha_cambio_estado"] = datetime.now().isoformat()
                                        st.info(f"Estado cambiado a: {nuevo_estado_meta}")
                                        
                                # Mostrar historial de la meta si existe
                                if m.get("historial_estados"):
                                    with st.expander("📊 Historial de estados de esta meta", expanded=False):
                                        for i, hist in enumerate(reversed(m["historial_estados"][-3:])): # Últimos 3
                                            st.write(f"**{hist['fecha'][:10]}**: {hist['estado_anterior']} → {hist['estado_nuevo']}")
                                            st.write(f"*Por: {hist['usuario']}*")
                                            if i < len(m["historial_estados"][-3:]) - 1: # No poner línea después del último
                                                st.markdown("---")
                                # ==================================================
                                # 🆕 FIN DE ESTADOS DE META
                                # ==================================================
                                
                                if fi.get("tipo_cg") == "Funcional":
                                    st.markdown("---")
                                    st.subheader("🏷️ Categoría Funcional")
                                    col_cat1, col_cat2 = st.columns([3, 1])
                                    with col_cat1:
                                        # Generar clave única con timestamp
                                        unique_timestamp = int(time.time() * 1000)
                                        unique_key = f"cat_func_{agr['id']}_{fi_index}_{m_index}_{unique_timestamp}"
                                        
                                        m["categoria_funcional"] = st.selectbox(
                                            "Categoría Funcional",
                                            options=["Institucional", "Grupal", "Individual"],
                                            index=["Institucional", "Grupal", "Individual"].index(m.get("categoria_funcional", "Institucional")),
                                            key=unique_key,  # ← USAR CLAVE ÚNICA
                                            disabled=not editable
                                        )
                                    
                                    with col_cat2:
                                        peso_sugerido = 30 if m["categoria_funcional"] == "Institucional" else 50 if m["categoria_funcional"] == "Grupal" else 20
                                        st.metric("Peso Sugerido", f"{peso_sugerido}%")
                                    st.markdown("---")

                                st.markdown("**Rangos de cumplimiento**")
                                if not m.get("rango"):
                                    m["rango"] = [{"min":"", "max":"", "porcentaje":""}]
                                for r_index, rango in enumerate(m.get("rango")):
                                    cr1, cr2, cr3, cr4 = st.columns([2,2,2,1])
                                    rango["min"] = cr1.text_input("Mínimo", value=rango.get("min",""), key=f"min_{agr['id']}_{fi_index}_{m_index}_{r_index}", disabled=not editable)
                                    rango["max"] = cr2.text_input("Máximo", value=rango.get("max",""), key=f"max_{agr['id']}_{fi_index}_{m_index}_{r_index}", disabled=not editable)
                                    rango["porcentaje"] = cr3.text_input("Porcentaje", value=rango.get("porcentaje",""), key=f"pct_{agr['id']}_{fi_index}_{m_index}_{r_index}", disabled=not editable)
                                    if cr4.button("🗑️", key=f"del_rango_{agr['id']}_{fi_index}_{m_index}_{r_index}", disabled=not editable) and len(m["rango"])>1:
                                        m["rango"].pop(r_index)
                                        agreements_save(db)
                                        st.rerun()
                                if editable and st.button("➕ Agregar rango", key=f"add_rango_{agr['id']}_{fi_index}_{m_index}"):
                                    m.setdefault("rango",[]).append({"min":"","max":"","porcentaje":""})
                                    agreements_save(db)
                                    st.rerun()
                                    
                                col_p1, col_p2 = st.columns(2)
                                m["ponderacion"] = col_p1.number_input("Ponderación (%)", min_value=0.0, max_value=100.0, value=float(m.get("ponderacion",0.0)), key=f"pond_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                m["cumplimiento_valor"] = col_p2.text_input(
                                    "Valor de PRUEBA para simulación",  # 👈 TEXTO ACLARATORIO
                                    value=m.get("cumplimiento_valor",""), 
                                    key=f"cumpl_{agr['id']}_{fi_index}_{m_index}", 
                                    disabled=not editable,
                                    help="⚠️ Solo para pruebas - ingresa un valor simulado para ver cómo se clasificaría"
                                )

                                if st.button("🎯 SIMULAR clasificación", key=f"calc_{agr['id']}_{fi_index}_{m_index}"):  # 👈 TEXTO ACLARATORIO
                                    m["cumplimiento_calc"] = calcular_cumplimiento(m)
                                    if m["cumplimiento_calc"] is not None:
                                        # 🆕 USAR LA NUEVA FUNCIÓN DE CLASIFICACIÓN CON SIGNOS EDITABLES
                                        clasificacion = clasificar_cumplimiento_meta(m["cumplimiento_calc"], m["clasificacion"])
                                        st.success(f"📊 Simulación: {m['cumplimiento_calc']:.2f}% → {clasificacion}")
                                    else:
                                        st.warning("No se pudo simular - verifica los rangos de cumplimiento")
                                        
                                m["observaciones"] = st.text_area("Observaciones", value=m.get("observaciones",""), key=f"obsmeta_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                
                                # 🆕 SECCIÓN MEJORADA - CLASIFICACIÓN CON SIGNOS EDITABLES
                                st.markdown("---")
                                st.subheader("🎯 Clasificación del Resultado")

                                # Asegurar que la meta tenga configuración de clasificación
                                if "clasificacion" not in m:
                                    m["clasificacion"] = {
                                        "cumplido": {"operador": "≥", "valor": 95, "color": "✅"},
                                        "parcial": {"operador": "≥", "valor": 75, "color": "🟡"},
                                        "no_cumplido": {"operador": "<", "valor": 75, "color": "🔴"}
                                    }

                                col_clas1, col_clas2, col_clas3 = st.columns(3)

                                with col_clas1:
                                    st.write("**✅ Cumplido**")
                                    cumplido = m["clasificacion"]["cumplido"]
                                    
                                    # SELECTOR DE SIGNO PARA CUMPLIDO
                                    operador_cumplido = st.selectbox(
                                        "Operador",
                                        options=["≥", ">", "=", "≤", "<"],
                                        index=["≥", ">", "=", "≤", "<"].index(cumplido.get("operador", "≥")),
                                        key=f"clas_op_cumplido_{agr['id']}_{fi_index}_{m_index}",
                                        help="Signo de comparación para 'Cumplido'"
                                    )
                                    
                                    valor_cumplido = st.number_input(
                                        "Valor (%)", 
                                        min_value=0, max_value=100, 
                                        value=int(cumplido.get("valor", 95)),
                                        key=f"clas_val_cumplido_{agr['id']}_{fi_index}_{m_index}",
                                        help="Umbral para clasificar como CUMPLIDO"
                                    )
                                    
                                    m["clasificacion"]["cumplido"] = {
                                        "operador": operador_cumplido, 
                                        "valor": valor_cumplido, 
                                        "color": "✅"
                                    }

                                with col_clas2:
                                    st.write("**🟡 Parcial**")
                                    parcial = m["clasificacion"]["parcial"]
                                    
                                    # SELECTOR DE SIGNO PARA PARCIAL
                                    operador_parcial = st.selectbox(
                                        "Operador",
                                        options=["≥", ">", "=", "≤", "<"],
                                        index=["≥", ">", "=", "≤", "<"].index(parcial.get("operador", "≥")),
                                        key=f"clas_op_parcial_{agr['id']}_{fi_index}_{m_index}",
                                        help="Signo de comparación para 'Parcial'"
                                    )
                                    
                                    valor_parcial = st.number_input(
                                        "Valor (%)", 
                                        min_value=0, max_value=100, 
                                        value=int(parcial.get("valor", 75)),
                                        key=f"clas_val_parcial_{agr['id']}_{fi_index}_{m_index}",
                                        help="Umbral para clasificar como PARCIAL"
                                    )
                                    
                                    m["clasificacion"]["parcial"] = {
                                        "operador": operador_parcial, 
                                        "valor": valor_parcial, 
                                        "color": "🟡"
                                    }

                                with col_clas3:
                                    st.write("**🔴 No Cumplido**")
                                    no_cumplido = m["clasificacion"]["no_cumplido"]
                                    
                                    # SELECTOR DE SIGNO PARA NO CUMPLIDO
                                    operador_nc = st.selectbox(
                                        "Operador",
                                        options=["<", "≤", "=", ">", "≥"],
                                        index=["<", "≤", "=", ">", "≥"].index(no_cumplido.get("operador", "<")),
                                        key=f"clas_op_nc_{agr['id']}_{fi_index}_{m_index}",
                                        help="Signo de comparación para 'No Cumplido'"
                                    )
                                    
                                    valor_nc = st.number_input(
                                        "Valor (%)", 
                                        min_value=0, max_value=100, 
                                        value=int(no_cumplido.get("valor", 75)),
                                        key=f"clas_val_nc_{agr['id']}_{fi_index}_{m_index}",
                                        help="Umbral para clasificar como NO CUMPLIDO"
                                    )
                                    
                                    m["clasificacion"]["no_cumplido"] = {
                                        "operador": operador_nc, 
                                        "valor": valor_nc, 
                                        "color": "🔴"
                                    }

                                # Botón de reset
                                if st.button("🔄 Restablecer clasificación por defecto", key=f"reset_clas_{agr['id']}_{fi_index}_{m_index}"):
                                    m["clasificacion"] = {
                                        "cumplido": {"operador": "≥", "valor": 95, "color": "✅"},
                                        "parcial": {"operador": "≥", "valor": 75, "color": "🟡"},
                                        "no_cumplido": {"operador": "<", "valor": 75, "color": "🔴"}
                                    }
                                    st.rerun()

                                # 🆕 MOSTRAR CLASIFICACIÓN ACTUAL CON SIGNOS EDITADOS
                                clas_cumplido = f"✅ {m['clasificacion']['cumplido']['operador']}{m['clasificacion']['cumplido']['valor']}%"
                                clas_parcial = f"🟡 {m['clasificacion']['parcial']['operador']}{m['clasificacion']['parcial']['valor']}%"
                                clas_nc = f"🔴 {m['clasificacion']['no_cumplido']['operador']}{m['clasificacion']['no_cumplido']['valor']}%"

                                st.success(f"**Clasificación configurada:** {clas_cumplido} | {clas_parcial} | {clas_nc}")

                                colmA, colmB = st.columns([1,1])
                                if colmA.button("💾 Guardar meta", key=f"save_meta_{agr['id']}_{fi_index}_{m_index}", disabled=not editable):
                                    agreements_save(db); audit_log("save_meta", {"agr":agr["id"], "ficha":fi["id"], "meta":m["id"], "by":user["username"]}); st.success("Meta guardada")
                                if colmB.button("🗑️ Eliminar meta", key=f"del_meta_{agr['id']}_{fi_index}_{m_index}"):
                                    if st.session_state.get(f"confirm_del_meta_{m['id']}") != True:
                                        st.session_state[f"confirm_del_meta_{m['id']}"] = True
                                        st.warning("Confirma eliminar meta (presiona eliminar nuevamente).")
                                    else:
                                        fi["metas"].pop(m_index); agreements_save(db); audit_log("delete_meta", {"agr":agr["id"], "ficha":fi["id"], "meta":m["id"], "by":user["username"]}); st.success("Meta eliminada"); st.rerun()
                                        
                    # ✅ BOTÓN ÚNICO QUE DETECTA AUTOMÁTICAMENTE
                    if st.button("📊 Validar Ponderaciones", key=f"valid_{agr['id']}_{fi_index}"):
                        # 🆕 DETECCIÓN MEJORADA - Verifica ponderaciones en METAS
                        total_ponderacion = sum(meta.get('ponderacion', 0) for meta in fi.get('metas', []))
                        tiene_metas_con_ponderacion = total_ponderacion > 0
                        
                        if tiene_metas_con_ponderacion:
                            fi = validar_y_ajustar_ponderaciones(fi)
                            st.subheader("📊 Resultado - Validación de Ponderaciones")
                            
                            # Calcular total después de la validación
                            total_final = sum(meta.get('ponderacion', 0) for meta in fi.get('metas', []))
                            
                            # Mostrar resultados simples
                            if total_final == 100:
                                st.success("✅ Ponderaciones validadas correctamente (100%)")
                            elif total_final > 100:
                                st.error(f"❌ Sobrepasa 100%: {total_final}%")
                            elif total_final < 100:
                                st.warning(f"⚠️ No alcanza 100%: {total_final}%")
                            else:
                                st.info(f"📊 Total ponderación: {total_final}%")
                                
                        else:
                            st.warning("ℹ️ Esta ficha no tiene metas con ponderación asignada")
                                         
                    # 🆕 AQUÍ VAN LOS BOTONES MEJORADOS PARA PONDERACIONES Y RANGOS
                    col_tools1, col_tools2, col_tools3 = st.columns(3)

                    with col_tools1:
                        if st.button("⚖️ Calcular Ponderación Automática", key=f"auto_pond_{fi_index}"):
                            ponderaciones = calcular_ponderacion_automatica(fi)
                            for meta_idx, meta in enumerate(fi.get("metas", [])):
                                meta_id = meta.get("id", f"meta_{meta_idx}")
                                if meta_id in ponderaciones:
                                    meta["ponderacion"] = ponderaciones[meta_id]
                            agreements_save(db)
                            st.success("Ponderación calculada automáticamente")
                            st.rerun()

                    with col_tools2:
                        if st.button("🔄 Validar Ponderaciones", key=f"valid_pond_{fi_index}"):
                            fi = validar_y_ajustar_ponderaciones(fi)
                            agreements_save(db)
                            st.success("Ponderaciones validadas y ajustadas")
                            st.rerun()

                    with col_tools3:
                        if st.button("🎯 Generar Rangos Automáticos", key=f"auto_rangos_{fi_index}"):
                            # Aplicar a todas las metas de la ficha
                            for meta in fi.get("metas", []):
                                meta["rango"] = generar_rangos_automaticos(
                                    fi.get("tipo_meta", ""),
                                    meta.get("unidad", ""),
                                    float(meta.get("valor_objetivo", 0)) if meta.get("valor_objetivo") else 0
                                )
                            agreements_save(db)
                            st.success("Rangos generados automáticamente para todas las metas")
                            st.rerun()

                    colfA, colfB = st.columns([1,1])
                    # 🆕 CORREGIR CLAVE DEL BOTÓN GUARDAR FICHA
                    if colfA.button("💾 Guardar ficha", key=f"save_ficha_{agr['id']}_{fi_index}"):
                        agreements_save(db); audit_log("save_ficha", {"agr":agr["id"], "ficha":fi["id"], "by":user["username"]}); st.success("Ficha guardada")
                    # 🆕 CORREGIR CLAVE DEL BOTÓN ELIMINAR FICHA
                    if colfB.button("🗑️ Eliminar ficha", key=f"del_ficha_{agr['id']}_{fi_index}"):
                        if st.session_state.get(f"confirm_del_ficha_{fi['id']}") != True:
                            st.session_state[f"confirm_del_ficha_{fi['id']}"] = True; st.warning("Confirma eliminar ficha (presiona eliminar nuevamente).")
                        else:
                            agr["fichas"].pop(fi_index); agreements_save(db); audit_log("delete_ficha", {"agr":agr["id"], "ficha":fi["id"], "by":user["username"]}); st.success("Ficha eliminada"); st.rerun()
        
                    # 🆕 BOTONES ESPECÍFICOS PARA CG (AGREGAR DESPUÉS DE LOS BOTONES EXISTENTES)
                    col_cg1, col_cg2 = st.columns(2)

                    with col_cg1:
                        if st.button("📋 Validar Estructura CG", key=f"valid_struct_{agr['id']}_{fi_index}"):
                            resultado = validar_estructura_cg(agr)
                            if resultado["valido"]:
                                st.success("✅ Estructura de CG válida")
                            else:
                                st.error("❌ Problemas en la estructura:")
                                for error in resultado["errores"]:
                                    st.error(f" - {error}")
                            for advertencia in resultado["advertencias"]:
                                st.warning(f"⚠️ {advertencia}")

                    with col_cg2:
                        if st.button("🔄 Ajustar Ponderaciones CG", key=f"ajustar_cg_{agr['id']}_{fi_index}"):
                            fi = ajustar_ponderaciones_por_tipo(fi, agr)
                            agreements_save(db)
                            st.success("Ponderaciones ajustadas según tipo de CG")
                            st.rerun()
        
        else:
            st.info("No hay fichas. Usa 'Crear Ficha Manual' o la carga masiva.")
            
        with st.expander("🔄 Flujo de Aprobación y Versionado", expanded=True):
            st.subheader("Estado Actual del Acuerdo")
            estado_actual = agr.get("estado", "Borrador")
            st.markdown(f"### 📊 Estado: **{estado_actual}**")
            
            # Mostrar historial de estados
            if agr.get("approval_flow"):
                st.markdown("#### 📈 Historial de Estados:")
                for i, cambio in enumerate(reversed(agr["approval_flow"][-5:])): # Últimos 5
                    with st.expander(f"{cambio['timestamp'][:10]} - {cambio['estado_nuevo']}", expanded=False):
                        st.write(f"**Usuario:** {cambio['usuario']} ({cambio['rol']})")
                        st.write(f"**Cambio:** {cambio['estado_anterior']} → {cambio['estado_nuevo']}")
                        if cambio.get('comentario'):
                            st.write(f"**Comentario:** {cambio['comentario']}")
                            
            # Selector de nuevo estado (solo si tiene permisos)
            rol_usuario = st.session_state.user["role"]
            col_estado1, col_estado2 = st.columns([2, 1])
            with col_estado1:
                nuevo_estado = st.selectbox(
                    "Cambiar estado a:",
                    options=ESTADOS_ACUERDO,
                    index=ESTADOS_ACUERDO.index(estado_actual) if estado_actual in ESTADOS_ACUERDO else 0,
                    key=f"estado_select_{agr['id']}"
                )
            with col_estado2:
                comentario_estado = st.text_input("Comentario (opcional)", key=f"comentario_{agr['id']}")
                
            # Validar y aplicar cambio de estado
            if nuevo_estado != estado_actual:
                if puede_cambiar_estado(estado_actual, nuevo_estado, rol_usuario):
                    if st.button("✅ Aplicar Cambio de Estado", key=f"apply_estado_{agr['id']}"):
                        # Registrar cambio
                        cambio = registrar_cambio_estado(
                            agr,
                            st.session_state.user["username"],
                            rol_usuario,
                            estado_actual,
                            nuevo_estado,
                            comentario_estado
                        )
                        agr.setdefault("approval_flow", []).append(cambio)
                        agr["estado"] = nuevo_estado
                        
                        # Crear versión si el cambio es significativo
                        if nuevo_estado in ["Aprobado", "Rechazado"]:
                            version = crear_version_acuerdo(
                                agr,
                                st.session_state.user["username"],
                                f"Cambio de estado a {nuevo_estado}",
                                {"estado": f"{estado_actual} → {nuevo_estado}"}
                            )
                            agr.setdefault("versions", []).append(version)
                            
                        agreements_save(db)
                        audit_log("cambio_estado", {
                            "acuerdo": agr["id"],
                            "de": estado_actual,
                            "a": nuevo_estado,
                            "por": st.session_state.user["username"]
                        })
                        st.success(f"Estado cambiado a {nuevo_estado}")
                        st.rerun()
                else:
                    st.warning(f"❌ Su rol ({rol_usuario}) no permite cambiar de {estado_actual} a {nuevo_estado}")
                    
            # Crear versión manual
            st.markdown("---")
            st.subheader("📸 Crear Versión Manual")
            col_ver1, col_ver2 = st.columns([3, 1])
            with col_ver1:
                motivo_version = st.text_input("Motivo de la versión", placeholder="Ej: Revisión trimestral, Correcciones, etc.")
            with col_ver2:
                if st.button("📷 Crear Versión", key=f"version_{agr['id']}"):
                    if motivo_version:
                        version = crear_version_acuerdo(
                            agr,
                            st.session_state.user["username"],
                            motivo_version
                        )
                        agr.setdefault("versions", []).append(version)
                        agr["current_version"] = len(agr["versions"]) - 1
                        agreements_save(db)
                        audit_log("crear_version", {
                            "acuerdo": agr["id"],
                            "version": version["version_id"],
                            "motivo": motivo_version
                        })
                        st.success(f"Versión {version['version_id']} creada")
                        st.rerun()
                    else:
                        st.error("Debe especificar un motivo")
                        
            # Listar versiones existentes
            if agr.get("versions"):
                st.markdown("---")
                st.subheader("📚 Historial de Versiones")
                for version in reversed(agr["versions"]):
                    with st.expander(f"Versión {version['version_id']} - {version['timestamp'][:10]}", expanded=False):
                        col_ver_info1, col_ver_info2 = st.columns(2)
                        with col_ver_info1:
                            st.write(f"**Usuario:** {version['usuario']}")
                            st.write(f"**Motivo:** {version['motivo']}")
                            st.write(f"**Estado:** {version.get('estado_nuevo', 'N/A')}")
                        with col_ver_info2:
                            st.write(f"**Fecha:** {version['timestamp'][:19]}")
                            st.write(f"**N°:** {version['version_number']}")
                            
                        # Botón para comparar con actual
                        if st.button("🔍 Comparar con actual", key=f"compare_{version['version_id']}"):
                            st.session_state.version_comparar = version
                            st.info("Función de comparación en desarrollo")
                            
                        # Botón para restaurar (solo admin)
                        if rol_usuario == "Administrador":
                            if st.button("↩️ Restaurar esta versión", key=f"restore_{version['version_id']}"):
                                if st.confirm("¿Restaurar esta versión? Se perderán los cambios posteriores."):
                                    # Implementar restauración
                                    st.warning("Función de restauración en desarrollo")
                                    
            st.markdown("---")
            st.markdown("Historial de versiones y aprobaciones")
            if agr.get("versions"):
                info = [{"número": v.get("version_number", i+1), "fecha": v.get("version_ts",""), "usuario": v.get("version_by",""), "motivo": v.get("version_motivo","")} for i,v in enumerate(agr.get("versions"))]
                st.dataframe(info)
            if agr.get("approval_flow"):
                st.markdown("Registro de acciones de aprobación")
                st.json(agr.get("approval_flow"))
                
            if st.button("📄 Generar reporte completo (JSON + CSV)"):
                json_data = json.dumps(agr, ensure_ascii=False, indent=2).encode("utf-8")
                csv_h = export_csv_horizontal_agreement(agr).encode("utf-8")
                mem = io.BytesIO()
                with zipfile.ZipFile(mem, mode="w") as z:
                    z.writestr(f"{agr['id']}.json", json_data)
                    z.writestr(f"{agr['id']}_horizontal.csv", csv_h)
                mem.seek(0)
                st.download_button("⬇️ Descargar paquete de reporte (zip)", data=mem, file_name=f"{agr['id']}_reporte.zip")
                
        # === SECCIÓN DE IMPRESIÓN ===
        st.markdown("---")
        st.subheader("📊 Opciones de Impresión y Exportación")
        
        # Generar el contenido HTML una sola vez
        html_content = exportar_html_imprimible(agr)
        col_imp1, col_imp2, col_imp3 = st.columns([1, 1, 1])
        
        with col_imp1:
            st.download_button(
                "💾 Descargar HTML",
                data=html_content.encode('utf-8'),
                file_name=f"{agr['id']}.html",
                mime="text/html"
            )
        with col_imp2:
            if st.button("👁️ Vista Previa"):
                st.components.v1.html(html_content, height=600, scrolling=True)
        with col_imp3:
            if st.button("🖨️ Imprimir"):
                st.download_button(
                    "📄 Descargar para Imprimir",
                    data=html_content.encode('utf-8'),
                    file_name=f"{agr['id']}_imprimir.html",
                    mime="text/html"
                )
        st.info("💡 Descargue el HTML y ábralo en su navegador. Use Ctrl+P para imprimir.")

        # 🆕 AQUÍ VA EL GUARDADO AUTOMÁTICO - JUSTO ANTES DEL FINAL
        if "open_agr" in st.session_state and st.session_state["open_agr"] in db:
            autosave(db, st.session_state["open_agr"])
        
        # 🆕 INDICADOR DE ESTADO DE GUARDADO EN SIDEBAR
        if st.session_state.get("unsaved_changes", False):
            st.sidebar.warning("⚠️ **Cambios sin guardar**")
        else:
            st.sidebar.success("✅ **Todo guardado**")

def detectar_y_importar_csv(upl_bytes: bytes, agr: Dict[str, Any]) -> int:
    """
    Detecta y importa datos desde CSV - VERSIÓN MEJORADA
    
    Args:
        upl_bytes: Bytes del archivo CSV
        agr: Acuerdo donde importar los datos
        
    Returns:
        int: Número de registros importados
    """
    try:
        # 🆕 DETECCIÓN MEJORADA DE CODIFICACIÓN
        try:
            s = upl_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                s = upl_bytes.decode("latin-1")
            except UnicodeDecodeError:
                s = upl_bytes.decode("utf-8", errors="replace")
        
        # 🆕 VERIFICAR SI EL CSV TIENE DATOS
        lines = s.strip().split('\n')
        if len(lines) <= 1:
            st.warning("El archivo CSV está vacío o solo tiene encabezados")
            return 0
            
        # 🆕 PROCESAR CSV
        reader = csv.DictReader(io.StringIO(s))
        imported = importar_csv_en_acuerdo(reader, agr)
        
        if imported == 0:
            st.warning("No se pudieron importar registros. Verifique el formato del CSV.")
            
        return imported
        
    except Exception as e:
        st.error(f"❌ Error procesando CSV: {str(e)}")
        # 🆕 INFORMACIÓN ADICIONAL PARA DEBUG
        st.info("💡 Formato esperado: CSV con encabezados compatibles con export_csv_horizontal_agreement")
        return 0

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
            year = agr.get("año") or date.today().year
            new_fid = fid if fid else generate_ficha_code(year, agr.get("id"))
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
            
        mid = (row.get("meta_id(blank_new)") or "").strip()
        es_hito = parse_bool_si_no(row.get("es_hito[SI/NO]","NO"))
        rango_str = row.get("rango(min1|max1|pct1;min2|max2|pct2;...)", "").strip()
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
                    meta = m; break
        if not meta:
            numero = len(f.get("metas", [])) + 1
            new_mid = mid if mid else f"{f['id']}_M{numero}"
            meta = {
                "id": new_mid,
                "numero": numero,
                "unidad": row.get("unidad",""),
                "valor_objetivo": row.get("valor_objetivo",""),
                "sentido": row.get("sentido[>=|<=|==]",">="),
                "descripcion": row.get("descripcion",""),
                "frecuencia": row.get("frecuencia[Mensual|Trimestral|Semestral|Anual]","Anual"),
                "vencimiento": row.get("vencimiento(YYYY-MM-DD)", f"{agr.get('año')}-12-31"),
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
                "frecuencia": row.get("frecuencia[Mensual|Trimestral|Semestral|Anual]", meta.get("frecuencia","Anual")),
                "vencimiento": row.get("vencimiento(YYYY-MM-DD)", meta.get("vencimiento", f"{agr.get('año')}-12-31")),
                "es_hito": es_hito,
                "rango": rlist or meta.get("rango",[]),
                "ponderacion": float(row.get("ponderacion(%)", meta.get("ponderacion",0)) or 0),
                "cumplimiento_valor": row.get("cumplimiento_valor", meta.get("cumplimiento_valor","")),
                "observaciones": row.get("meta_observaciones", meta.get("observaciones",""))
            })
            count += 1
            
    return count

def clonar_acuerdo(acuerdo_original: Dict[str, Any], nuevo_año: int, usuario: str) -> Dict[str, Any]:
    """
    Clona un acuerdo existente para un nuevo año
    
    Args:
        acuerdo_original: Acuerdo a clonar
        nuevo_año: Año para el nuevo acuerdo
        usuario: Usuario que realiza la clonación
    
    Returns:
        Dict: Nuevo acuerdo clonado
    """
    
    # Generar nuevo código para el acuerdo clonado
    external_prefix = None
    acuerdo_id_original = acuerdo_original.get("id", "")
    
    # Extraer prefijo si existe (ej: AC_OPP_0001_2023 -> OPP)
    if "_" in acuerdo_id_original:
        partes = acuerdo_id_original.split("_")
        if len(partes) >= 3 and partes[1] not in ["", "0001", "0002"]:  # Evitar números como prefijos
            external_prefix = partes[1]
    
    nuevo_codigo = generate_agreement_code(nuevo_año, external_prefix=external_prefix)
    
    # Crear copia profunda del acuerdo original
    import copy
    acuerdo_clonado = copy.deepcopy(acuerdo_original)
    
    # Actualizar información básica
    acuerdo_clonado["id"] = nuevo_codigo
    acuerdo_clonado["año"] = nuevo_año
    acuerdo_clonado["created_by"] = usuario
    acuerdo_clonado["created_date"] = datetime.now().isoformat()
    acuerdo_clonado["clonado_desde"] = acuerdo_original["id"]  # Registrar origen
    
    # Reiniciar estados y flujos de aprobación
    acuerdo_clonado["estado"] = "Borrador"
    acuerdo_clonado["approval_flow"] = []
    acuerdo_clonado["versions"] = []
    acuerdo_clonado["current_version"] = None
    
    # Actualizar fechas de vigencia
    acuerdo_clonado["vigencia_desde"] = f"{nuevo_año}-01-01"
    acuerdo_clonado["vigencia_hasta"] = f"{nuevo_año}-12-31"
    
    # Actualizar códigos de fichas y metas
    for ficha in acuerdo_clonado.get("fichas", []):
        # Generar nuevo ID de ficha CORREGIDO
        ficha_id_original = ficha["id"]
        
        # 🆕 CORRECIÓN: Extraer solo el número de ficha sin el año
        if "_" in ficha_id_original:
            partes_ficha = ficha_id_original.split("_")
            # Buscar la parte que contiene "F" seguido de números
            for parte in partes_ficha:
                if parte.startswith("F") and parte[1:].isdigit():
                    numero_ficha = parte[1:]  # Extraer solo el número
                    break
            else:
                numero_ficha = "1"  # Fallback
        else:
            numero_ficha = "1"  # Fallback
        
        # 🆕 GENERAR NUEVO ID CON AÑO CORRECTO
        nuevo_ficha_id = f"{nuevo_codigo}_F{numero_ficha}"
        ficha["id"] = nuevo_ficha_id
        ficha["origen_clonado"] = ficha_id_original
        
        # Actualizar metas de la ficha
        for meta in ficha.get("metas", []):
            meta_id_original = meta["id"]
            nuevo_meta_id = f"{nuevo_ficha_id}_M{meta['numero']}"
            meta["id"] = nuevo_meta_id
            meta["origen_clonado"] = meta_id_original
            
            # Reiniciar información de cumplimiento
            meta["cumplimiento_valor"] = ""
            meta["cumplimiento_calc"] = None
            meta["fecha_medicion"] = None
            meta["periodo"] = ""
            meta["comentarios_cumplimiento"] = ""
            meta["estado"] = "No Iniciada"
            meta["historial_estados"] = []
    
    # Limpiar adjuntos (no se clonan)
    acuerdo_clonado["attachments"] = []
    
    # Registrar en auditoría
    audit_log("clonar_acuerdo", {
        "acuerdo_original": acuerdo_original["id"],
        "acuerdo_nuevo": nuevo_codigo,
        "año_original": acuerdo_original.get("año"),
        "año_nuevo": nuevo_año,
        "usuario": usuario
    })
    
    return acuerdo_clonado

def generar_reporte_riesgos_csv(resultados, acuerdo):
    """
    Genera reporte CSV de riesgos - simple y funcional
    """
    import csv
    import io
    
    # Crear contenido CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Encabezados
    writer.writerow(["REPORTE DE RIESGOS - SISTEMA CG"])
    writer.writerow([f"Acuerdo: {acuerdo.get('id', '')}"])
    writer.writerow([f"Organismo: {acuerdo.get('organismo_nombre', '')}"])
    writer.writerow([f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
    writer.writerow([])  # Línea vacía
    
    # Resumen de riesgos
    writer.writerow(["RESUMEN DE RIESGOS"])
    writer.writerow(["Tipo", "Cantidad"])
    writer.writerow(["Metas sin ponderación", resultados.get('metas_sin_ponderacion', 0)])
    writer.writerow(["Metas vencimiento próximo", resultados.get('metas_vencimiento_proximo', 0)])
    writer.writerow(["Metas bajo cumplimiento", resultados.get('metas_bajo_cumplimiento', 0)])
    writer.writerow(["Total riesgos identificados", resultados.get('total_riesgos', 0)])
    writer.writerow([])
    
    # Matriz de riesgos
    matriz = resultados.get('matriz_riesgos', {})
    writer.writerow(["MATRIZ DE RIESGOS"])
    writer.writerow(["Nivel", "Cantidad"])
    writer.writerow(["Crítico", matriz.get('critico', 0)])
    writer.writerow(["Alto", matriz.get('alto', 0)])
    writer.writerow(["Medio", matriz.get('medio', 0)])
    writer.writerow(["Bajo", matriz.get('bajo', 0)])
    writer.writerow([])
    
    # Detalle de metas con riesgo
    if resultados.get('metas_detalle'):
        writer.writerow(["DETALLE DE METAS CON RIESGO"])
        writer.writerow(["Código", "Descripción", "Estado", "Nivel Riesgo", "Problemas Detectados"])
        
        for meta in resultados['metas_detalle']:
            writer.writerow([
                meta.get('codigo', 'N/A'),
                meta.get('descripcion', 'N/A')[:50],  # Limitar longitud
                meta.get('estado', 'N/A'),
                meta.get('nivel_riesgo', 'N/A'),
                ', '.join(meta.get('problemas', []))[:100]  # Limitar longitud
            ])
    
    # Obtener el contenido CSV
    csv_content = output.getvalue()
    output.close()
    
    return csv_content

def page_clonar_acuerdo():
    """Página para clonar acuerdos existentes"""
    require_login()
    
    # 🆕 LIMPIAR CACHÉ AL ENTRAR A LA PÁGINA
    try:
        # Limpiar caché específico de acuerdos
        if 'acuerdos_db' in st.session_state:
            del st.session_state['acuerdos_db']
    except:
        pass
    
    # 🆕 CARGAR DATOS FRESCOS
    db = agreements_load()

    # 🆕 AGREGAR BOTÓN DE REPARACIÓN AQUÍ (NUEVO)
    if st.sidebar.button("🔧 REPARAR IDs FICHAS EXISTENTES (Una vez)", type="primary"):
        with st.spinner("Buscando y reparando IDs de fichas..."):
            acuerdos_reparados = 0
            total_fichas_reparadas = 0
            
            for acuerdo_id, acuerdo in db.items():
                fichas_reparadas = 0
                for i, ficha in enumerate(acuerdo.get("fichas", [])):
                    ficha_id_actual = ficha["id"]
                    
                    # DETECTAR SI EL ID TIENE PATRÓN INCORRECTO (_F2023, _F2024, etc.)
                    if "_F20" in ficha_id_actual:
                        # GENERAR NUEVO ID CORRECTO
                        partes = ficha_id_actual.split("_")
                        acuerdo_base = "_".join(partes[:4])  # AC_MEVIR_001_2024
                        nuevo_ficha_id = f"{acuerdo_base}_F{i+1}"
                        
                        # ACTUALIZAR
                        ficha_original = ficha["id"]
                        ficha["id"] = nuevo_ficha_id
                        fichas_reparadas += 1
                        total_fichas_reparadas += 1
                        
                        st.write(f"🔧 **Reparado:** `{ficha_original}` → `{nuevo_ficha_id}`")
                
                if fichas_reparadas > 0:
                    acuerdos_reparados += 1
                    st.success(f"✅ **{acuerdo_id}**: {fichas_reparadas} fichas reparadas")
            
            if acuerdos_reparados > 0:
                agreements_save(db)
                st.balloons()
                st.success(f"🎉 **¡REPARACIÓN COMPLETADA!**")
                st.success(f"**{acuerdos_reparados}** acuerdos reparados")
                st.success(f"**{total_fichas_reparadas}** fichas corregidas")
            else:
                st.info("✅ Todos los IDs de fichas ya están correctos")
        
        st.stop()

    st.header("📋 Clonar Acuerdo Existente")
    st.info("""
    **¿Para qué sirve esta función?**
    
    - Clona acuerdos de años anteriores para crear nuevos acuerdos
    - Mantiene la estructura de fichas y metas
    - Reinicia estados y cumplimientos
    - Actualiza automáticamente fechas y códigos
    """)
    
    # Cargar acuerdos existentes
    db = agreements_load()
    
    if not db:
        st.warning("No hay acuerdos existentes para clonar.")
        return
    
    # Filtrar acuerdos que no sean del año actual
    año_actual = datetime.now().year
    acuerdos_para_clonar = {k: v for k, v in db.items() if v.get("año") != año_actual}
    
    if not acuerdos_para_clonar:
        st.warning("No hay acuerdos de años anteriores para clonar.")
        return
    
    # Selección de acuerdo a clonar
    st.subheader("1. Seleccionar Acuerdo a Clonar")
    
    # Crear opciones para el selectbox
    opciones_acuerdos = []
    for acuerdo_id, acuerdo in acuerdos_para_clonar.items():
        año = acuerdo.get("año", "N/D")
        organismo = acuerdo.get("organismo_nombre", "Sin nombre")
        tipo = acuerdo.get("tipo_compromiso", "Sin tipo")
        opciones_acuerdos.append(f"{acuerdo_id} - {organismo} ({año}) - {tipo}")
    
    acuerdo_seleccionado = st.selectbox(
        "Seleccione el acuerdo a clonar:",
        options=opciones_acuerdos,
        help="Seleccione un acuerdo de año anterior para usar como base"
    )
    
    if acuerdo_seleccionado:
        # Obtener ID del acuerdo seleccionado
        acuerdo_id_original = acuerdo_seleccionado.split(" - ")[0]
        acuerdo_original = db[acuerdo_id_original]
        
        # Mostrar información del acuerdo seleccionado
        with st.expander("📊 Información del Acuerdo Seleccionado", expanded=True):
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.write(f"**Código:** {acuerdo_original['id']}")
                st.write(f"**Organismo:** {acuerdo_original.get('organismo_nombre', 'N/D')}")
                st.write(f"**Tipo:** {acuerdo_original.get('tipo_compromiso', 'N/D')}")
                st.write(f"**Año:** {acuerdo_original.get('año', 'N/D')}")
            
            with col_info2:
                st.write(f"**Fichas:** {len(acuerdo_original.get('fichas', []))}")
                st.write(f"**Metas:** {sum(len(f.get('metas', [])) for f in acuerdo_original.get('fichas', []))}")
                st.write(f"**Estado:** {acuerdo_original.get('estado', 'N/D')}")
                st.write(f"**Creado por:** {acuerdo_original.get('created_by', 'N/D')}")
        
        # Configuración del nuevo acuerdo
        st.subheader("2. Configurar Nuevo Acuerdo")
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            # Año del nuevo acuerdo
            año_default = año_actual
            nuevo_año = st.number_input(
                "Año del nuevo acuerdo:",
                min_value=2000,
                max_value=2030,
                value=año_default,
                step=1,
                help="Seleccione el año para el nuevo acuerdo"
            )
        
        with col_info2:
            # Prefijo personalizado (opcional)
            usar_prefijo = st.checkbox("Usar prefijo personalizado", value=False)
            prefijo_personalizado = ""
            if usar_prefijo:
                prefijo_personalizado = st.text_input(
                    "Prefijo para el código:",
                    value=acuerdo_original["id"].split("_")[1] if "_" in acuerdo_original["id"] and len(acuerdo_original["id"].split("_")) >= 3 else "",
                    help="Ej: OPP, MEF, etc."
                ).strip().upper()
        
        # Vista previa del nuevo código
        if prefijo_personalizado:
            codigo_preview = f"AC_{prefijo_personalizado}_XXXX_{nuevo_año}"
        else:
            codigo_preview = f"AC_XXXX_{nuevo_año}"
        
        st.info(f"**Código estimado del nuevo acuerdo:** `{codigo_preview}`")
        
        # Opciones de clonación
        st.subheader("3. Opciones de Clonación")
        
        col_opts1, col_opts2 = st.columns(2)
        
        with col_opts1:
            mantener_estructura = st.checkbox(
                "Mantener estructura completa", 
                value=True,
                help="Conserva todas las fichas y metas del acuerdo original"
            )
            
            mantener_clausulas = st.checkbox(
                "Mantener cláusulas", 
                value=True,
                help="Conserva las cláusulas del acuerdo original"
            )
        
        with col_opts2:
            reiniciar_estados = st.checkbox(
                "Reiniciar estados", 
                value=True,
                help="Establece todas las metas como 'No Iniciada'"
            )
            
            limpiar_cumplimientos = st.checkbox(
                "Limpiar cumplimientos", 
                value=True,
                help="Elimina todos los valores de cumplimiento anteriores"
            )
        
        # Resumen de cambios
        st.subheader("4. Resumen de Cambios")
        
        cambios = [
            f"✅ Año actualizado: {acuerdo_original.get('año')} → {nuevo_año}",
            f"✅ Código nuevo: {acuerdo_original['id']} → {codigo_preview.replace('XXXX', 'NNNN')}",
            f"✅ Estado reiniciado: {acuerdo_original.get('estado')} → Borrador",
            f"✅ Fechas de vigencia actualizadas al año {nuevo_año}",
            f"✅ Cumplimientos reiniciados" if limpiar_cumplimientos else "⚠️ Cumplimientos conservados",
            f"✅ {len(acuerdo_original.get('fichas', []))} fichas clonadas",
            f"✅ {sum(len(f.get('metas', [])) for f in acuerdo_original.get('fichas', []))} metas clonadas"
        ]
        
        for cambio in cambios:
            st.write(cambio)
        
        # Botón de clonación
        st.subheader("5. Confirmar Clonación")

        if st.button("🚀 Clonar Acuerdo", type="primary", use_container_width=True):
            with st.spinner("Clonando acuerdo..."):
                try:
                    # 🆕 PRIMERO: MOSTRAR INTERFAZ PARA EDITAR NOMBRES DE METAS
                    st.subheader("📝 Editando nombres de metas para el nuevo año")
                    st.info("💡 **Edita los nombres de las metas para el nuevo año. Los cambios se guardarán cuando confirmes al final.**")
                    
                    # Crear el acuerdo clonado base
                    acuerdo_clonado = clonar_acuerdo(
                        acuerdo_original, 
                        nuevo_año, 
                        st.session_state.user["username"]
                    )
                    
                    # 🆕 PERMITIR EDICIÓN DE NOMBRES DE METAS CON KEYS ESTABLES
                    if "fichas" in acuerdo_clonado:
                        for i, ficha in enumerate(acuerdo_clonado["fichas"]):
                            with st.expander(f"📋 Ficha {i+1}: {ficha.get('nombre', 'Sin nombre')}", expanded=True):
                                
                                if "metas" in ficha and ficha["metas"]:
                                    for j, meta in enumerate(ficha["metas"]):
                                        col_meta1, col_meta2 = st.columns([3, 1])
                                        
                                        with col_meta1:
                                            # 🆕 KEY ÚNICA Y ESTABLE
                                            nuevo_nombre = st.text_input(
                                                f"**Meta {j+1}**",
                                                value=meta.get("nombre", f"Meta {j+1}"),
                                                key=f"meta_edit_{acuerdo_original['id']}_{i}_{j}_{nuevo_año}",
                                                help="Modifica el nombre de la meta para el nuevo año"
                                            )
                                            # Actualizar inmediatamente en el acuerdo clonado
                                            acuerdo_clonado["fichas"][i]["metas"][j]["nombre"] = nuevo_nombre
                                        
                                        with col_meta2:
                                            st.markdown("**Original:**")
                                            nombre_original = acuerdo_original["fichas"][i]["metas"][j].get("nombre", "Sin nombre")
                                            st.caption(nombre_original[:30] + "..." if len(nombre_original) > 30 else nombre_original)
                                else:
                                    st.write("ℹ️ Esta ficha no tiene metas")
                    
                    # 🆕 RESUMEN DE CAMBIOS ANTES DE CONFIRMAR
                    st.subheader("📊 Resumen de cambios")
                    
                    total_metas = sum(len(f.get("metas", [])) for f in acuerdo_clonado.get("fichas", []))
                    st.write(f"**Total de metas a clonar:** {total_metas}")
                    st.write(f"**Nuevo código:** {acuerdo_clonado['id']}")
                    st.write(f"**Año nuevo:** {acuerdo_clonado['año']}")
                    
                    # 🆕 BOTÓN PARA CONFIRMAR Y GUARDAR
                    st.markdown("---")
                    col_conf1, col_conf2 = st.columns([1, 2])
                    
                    with col_conf2:
                        if st.button("💾 **Guardar Acuerdo Clonado**", type="primary", use_container_width=True):
                            # Aplicar opciones adicionales
                            if not mantener_clausulas:
                                acuerdo_clonado["clausulas"] = []
                            
                            if not reiniciar_estados:
                                acuerdo_clonado["estado"] = acuerdo_original.get("estado", "Borrador")
                            
                            if not limpiar_cumplimientos:
                                for ficha in acuerdo_clonado.get("fichas", []):
                                    for meta in ficha.get("metas", []):
                                        # Buscar el cumplimiento original
                                        ficha_orig_idx = next((idx for idx, f in enumerate(acuerdo_original.get("fichas", [])) 
                                                             if f.get("origen_clonado", "") == ficha.get("origen_clonado", "")), None)
                                        if ficha_orig_idx is not None:
                                            meta_orig_idx = next((idx for idx, m in enumerate(acuerdo_original["fichas"][ficha_orig_idx].get("metas", [])) 
                                                                if m.get("origen_clonado", "") == meta.get("origen_clonado", "")), None)
                                            if meta_orig_idx is not None:
                                                meta_orig = acuerdo_original["fichas"][ficha_orig_idx]["metas"][meta_orig_idx]
                                                meta["cumplimiento_valor"] = meta_orig.get("cumplimiento_valor", "")
                                                meta["cumplimiento_calc"] = meta_orig.get("cumplimiento_calc", None)
                            
                            # Guardar el nuevo acuerdo
                            db[acuerdo_clonado["id"]] = acuerdo_clonado
                            agreements_save(db)
                            
                            # Auditoría
                            audit_log("acuerdo_clonado_editado", {
                                "original": acuerdo_original["id"],
                                "nuevo": acuerdo_clonado["id"],
                                "usuario": st.session_state.user["username"],
                                "metas_editadas": total_metas
                            })
                            
                            st.success(f"✅ Acuerdo clonado exitosamente!")
                            st.balloons()
                            
                            # Mostrar información del nuevo acuerdo
                            st.info(f"""
                            **Nuevo acuerdo creado:**
                            - **Código:** {acuerdo_clonado['id']}
                            - **Organismo:** {acuerdo_clonado.get('organismo_nombre', 'N/D')}
                            - **Año:** {acuerdo_clonado.get('año', 'N/D')}
                            - **Fichas:** {len(acuerdo_clonado.get('fichas', []))}
                            - **Metas:** {total_metas}
                            """)
                            
                            # Botones de acción
                            col_acc1, col_acc2, col_acc3 = st.columns(3)
                            
                            with col_acc1:
                                if st.button("📂 Abrir nuevo acuerdo", use_container_width=True):
                                    st.session_state["open_agr"] = acuerdo_clonado["id"]
                                    st.rerun()
                            
                            with col_acc2:
                                if st.button("🔄 Clonar otro acuerdo", use_container_width=True):
                                    st.rerun()
                            
                            with col_acc3:
                                if st.button("📋 Volver a acuerdos", use_container_width=True):
                                    if "open_agr" in st.session_state:
                                        del st.session_state["open_agr"]
                                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error al clonar el acuerdo: {str(e)}")
                    import traceback
                    st.error(f"Detalles: {traceback.format_exc()}")

    st.markdown("---")
    st.subheader("🔧 Reparación de IDs de Fichas")
    st.warning("**Ejecutar solo UNA VEZ para corregir IDs de fichas con año 2023**")
    
    if st.button("🚨 REPARAR IDs FICHAS 2023→2024", type="primary", use_container_width=True):
        with st.spinner("Reparando IDs de fichas..."):
            acuerdos_reparados = 0
            total_fichas_reparadas = 0
            
            for acuerdo_id, acuerdo in db.items():
                if "2024" in acuerdo_id:
                    fichas_reparadas = 0
                    for i, ficha in enumerate(acuerdo.get("fichas", [])):
                        ficha_id_actual = ficha["id"]
                        
                        if "_F2023" in ficha_id_actual:
                            nuevo_ficha_id = f"{acuerdo_id}_F{i+1}"
                            ficha_original = ficha["id"]
                            ficha["id"] = nuevo_ficha_id
                            fichas_reparadas += 1
                            total_fichas_reparadas += 1
                            st.write(f"🔧 **Reparado:** `{ficha_original}` → `{nuevo_ficha_id}`")
                    
                    if fichas_reparadas > 0:
                        acuerdos_reparados += 1
                        st.success(f"✅ **{acuerdo_id}**: {fichas_reparadas} fichas reparadas")
            
            if acuerdos_reparados > 0:
                agreements_save(db)
                # Limpiar cache
                try:
                    if 'acuerdos_db' in st.session_state:
                        del st.session_state['acuerdos_db']
                except:
                    pass
                st.balloons()
                st.success(f"🎉 **¡REPARACIÓN COMPLETADA!**")
                st.success(f"**{acuerdos_reparados}** acuerdos reparados")
                st.success(f"**{total_fichas_reparadas}** fichas corregidas")
            else:
                st.info("✅ No se encontraron fichas con IDs de 2023")


def exportar_listado_html(acuerdo):
    """Genera HTML imprimible para un acuerdo específico - VERSIÓN CORREGIDA"""
    
    # Calcular métricas CON MANEJO DE ERRORES
    total_metas = 0
    metas_cumplidas = 0
    cumplimiento_total = 0.0
    
    for ficha in acuerdo.get("fichas", []):
        for meta in ficha.get("metas", []):
            total_metas += 1
            cumplimiento = meta.get("cumplimiento_calc", 0)
            
            # 🆕 MANEJAR VALORES NULOS Y NO VÁLIDOS
            if cumplimiento is None:
                cumplimiento = 0
            try:
                cumplimiento = float(cumplimiento)
            except (TypeError, ValueError):
                cumplimiento = 0
                
            cumplimiento_total += cumplimiento
            if cumplimiento >= 90:
                metas_cumplidas += 1
    
    # 🆕 CÁLCULO SEGURO DEL PROMEDIO
    cumplimiento_promedio = 0
    if total_metas > 0:
        cumplimiento_promedio = cumplimiento_total / total_metas
    
    # 🆕 MANEJAR VALORES FALTANTES EN EL ACUERDO
    organismo = acuerdo.get('organismo_nombre', 'Organismo no especificado')
    año = acuerdo.get('año', 'N/A')
    estado = acuerdo.get('estado', 'N/A')
    fecha_creacion = acuerdo.get('fecha_creacion', '')[:10] if acuerdo.get('fecha_creacion') else 'N/A'
    last_modified = acuerdo.get('last_modified', '')[:10] if acuerdo.get('last_modified') else 'N/A'
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte - {acuerdo.get('id', '')}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #333;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #2c3e50;
                margin-bottom: 5px;
            }}
            .header .subtitle {{
                color: #7f8c8d;
                font-size: 18px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .info-card {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #3498db;
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: #e8f4fd;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
                border: 1px solid #b3d9ff;
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #2980b9;
            }}
            .fichas-container {{
                margin-top: 30px;
            }}
            .ficha {{
                background: #fff;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
                page-break-inside: avoid;
            }}
            .ficha h3 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 5px;
            }}
            .meta {{
                background: #f8f9fa;
                margin: 10px 0;
                padding: 10px;
                border-left: 3px solid #27ae60;
                border-radius: 3px;
            }}
            .meta.cumplida {{ border-left-color: #27ae60; }}
            .meta.parcial {{ border-left-color: #f39c12; }}
            .meta.no-cumplida {{ border-left-color: #e74c3c; }}
            .meta.sin-datos {{ border-left-color: #95a5a6; }}
            .meta-header {{
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .meta-details {{
                font-size: 14px;
                color: #666;
            }}
            .footer {{
                margin-top: 50px;
                text-align: center;
                font-size: 12px;
                color: #7f8c8d;
                border-top: 1px solid #ddd;
                padding-top: 20px;
            }}
            @media print {{
                body {{ margin: 0; }}
                .ficha {{ page-break-inside: avoid; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>ACUERDO DE GESTIÓN</h1>
            <div class="subtitle">{organismo} - Año {año}</div>
        </div>
        
        <div class="info-grid">
            <div class="info-card">
                <strong>ID del Acuerdo:</strong> {acuerdo.get('id', 'N/A')}<br>
                <strong>Organismo:</strong> {organismo}<br>
                <strong>Estado:</strong> {estado}
            </div>
            <div class="info-card">
                <strong>Año:</strong> {año}<br>
                <strong>Fecha creación:</strong> {fecha_creacion}<br>
                <strong>Última modificación:</strong> {last_modified}
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{total_metas}</div>
                <div>Total Metas</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metas_cumplidas}</div>
                <div>Metas Cumplidas</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{cumplimiento_promedio:.1f}%</div>
                <div>Cumplimiento Promedio</div>
            </div>
        </div>
        
        <div class="fichas-container">
            <h2>Fichas y Metas del Acuerdo</h2>
            {"".join([f"""
            <div class="ficha">
                <h3>📋 {ficha.get('nombre', 'Ficha sin nombre')}</h3>
                <p><strong>Descripción:</strong> {ficha.get('descripcion', 'Sin descripción')}</p>
                {"".join([f"""
                <div class="meta { 'cumplida' if (meta.get('cumplimiento_calc', 0) or 0) >= 90 else 'parcial' if (meta.get('cumplimiento_calc', 0) or 0) >= 60 else 'no-cumplida' if (meta.get('cumplimiento_calc', 0) or 0) > 0 else 'sin-datos' }">
                    <div class="meta-header">🎯 {meta.get('descripcion', 'Meta sin descripción')}</div>
                    <div class="meta-details">
                        <strong>Objetivo:</strong> {meta.get('valor_objetivo', 'N/A')} {meta.get('unidad', '')} | 
                        <strong>Cumplimiento:</strong> {meta.get('cumplimiento_calc', 0) or 0:.1f}% | 
                        <strong>Ponderación:</strong> {meta.get('ponderacion', 0)}%
                    </div>
                </div>
                """ for meta in ficha.get('metas', [])])}
            </div>
            """ for ficha in acuerdo.get('fichas', [])])}
        </div>
        
        <div class="footer">
            <p>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | Sistema de Compromisos de Gestión</p>
        </div>
    </body>
    </html>
    """
    return html_content

def page_listados_completo():
    """Página principal para listados y reportes de acuerdos - VERSIÓN COMPLETA"""

    # 🎯 BOTÓN EN HEADER
    col1 = st.columns(1)[0] 
    with col1:
        st.header("📊 Listados y Reportes de Acuerdos")
       
    # Cargar datos
    db = agreements_load()
    
    if not db:
        st.info("No hay acuerdos en el sistema. Ve a 'Generar Acuerdos' para crear el primero.")
        return
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        estados = list(set(agr.get("estado", "Borrador") for agr in db.values()))
        estado_filtro = st.multiselect("Filtrar por estado", options=estados, default=estados)
    
    with col2:
        organismos = list(set(agr.get("organismo_nombre", "Sin nombre") for agr in db.values()))
        organismo_filtro = st.multiselect("Filtrar por organismo", options=organismos, default=organismos)
    
    with col3:
        años = list(set(agr.get("año", datetime.now().year) for agr in db.values()))
        año_filtro = st.multiselect("Filtrar por año", options=años, default=años)
    
    # Aplicar filtros
    acuerdos_filtrados = []
    for acuerdo in db.values():
        if (acuerdo.get("estado", "Borrador") in estado_filtro and 
            acuerdo.get("organismo_nombre", "Sin nombre") in organismo_filtro and
            acuerdo.get("año", datetime.now().year) in año_filtro):
            acuerdos_filtrados.append(acuerdo)
    
    st.subheader(f"📋 Acuerdos Encontrados: {len(acuerdos_filtrados)}")
    
    # Mostrar tabla resumen
    if acuerdos_filtrados:
        datos_tabla = []
        for acuerdo in acuerdos_filtrados:
            # Calcular cumplimiento
            cumplimiento = calcular_cumplimiento_acuerdo(acuerdo)
            
            # Contar metas
            total_metas = 0
            for ficha in acuerdo.get("fichas", []):
                total_metas += len(ficha.get("metas", []))
            
            datos_tabla.append({
                "ID": acuerdo["id"],
                "Organismo": acuerdo.get("organismo_nombre", ""),
                "Año": acuerdo.get("año", ""),
                "Estado": acuerdo.get("estado", ""),
                "Metas": total_metas,
                "Cumplimiento %": f"{cumplimiento:.1f}%" if cumplimiento else "N/A"
            })
        
        if datos_tabla:
            st.dataframe(datos_tabla, use_container_width=True)
        
        # Detalle por acuerdo
        st.subheader("🔍 Detalle por Acuerdo")
        acuerdo_detalle = st.selectbox(
            "Seleccionar acuerdo para ver detalle",
            options=[a["id"] for a in acuerdos_filtrados],
            format_func=lambda x: f"{x} - {db[x].get('organismo_nombre', '')}"
        )
        
        if acuerdo_detalle:
            acuerdo = db[acuerdo_detalle]

            # 🆕 BOTONES DE IMPRESIÓN Y EXPORTACIÓN
            st.subheader("🖨️ Opciones de Impresión y Exportación")
            
            col_print1, col_print2, col_print3 = st.columns(3)
            
            with col_print1:
                # Generar HTML imprimible
                html_content = exportar_listado_html(acuerdo)
                st.download_button(
                    label="📄 Descargar HTML",
                    data=html_content.encode('utf-8'),
                    file_name=f"{acuerdo_detalle}_reporte.html",
                    mime="text/html",
                    help="Descargar reporte en formato HTML para imprimir"
                )
            
            with col_print2:
                # Vista previa
                if st.button("👁️ Vista Previa", help="Ver vista previa del reporte"):
                    st.components.v1.html(html_content, height=800, scrolling=True)
            
            with col_print3:
                # Exportar JSON
                json_data = json.dumps(acuerdo, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📊 Descargar JSON",
                    data=json_data.encode('utf-8'),
                    file_name=f"{acuerdo_detalle}_datos.json",
                    mime="application/json",
                    help="Descargar datos completos en formato JSON"
                )    
            
            with st.expander(f"Detalle completo de {acuerdo_detalle}", expanded=False):
                st.json(acuerdo)
    else:
        st.warning("No hay acuerdos que coincidan con los filtros aplicados.")

def generar_listado_completo(db):
    """Genera listado completo de todos los acuerdos"""
    st.subheader("📊 Listado Completo de Acuerdos")
    
    # Crear datos para la tabla
    datos = []
    for acuerdo_id, acuerdo in db.items():
        datos.append({
            "Código": acuerdo_id,
            "Organismo": acuerdo.get("organismo_nombre", "No especificado"),
            "Año": acuerdo.get("año", "N/D"),
            "Tipo": acuerdo.get("tipo_compromiso", "N/D"),
            "Estado": acuerdo.get("estado", "N/D"),
            "Fichas": len(acuerdo.get("fichas", [])),
            "Metas": sum(len(f.get("metas", [])) for f in acuerdo.get("fichas", []))
        })
    
    if datos:
        df = pd.DataFrame(datos)
        st.dataframe(df, use_container_width=True)
        
        # Estadísticas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Acuerdos", len(datos))
        col2.metric("Organismos", df["Organismo"].nunique())
        col3.metric("Años", df["Año"].nunique())
        col4.metric("Fichas Totales", df["Fichas"].sum())
    else:
        st.info("No hay acuerdos para mostrar")

def generar_listado_por_organismo(db):
    """Genera listado agrupado por organismo"""
    st.subheader("🏢 Acuerdos por Organismo")
    
    # Agrupar por organismo
    organismos = {}
    for acuerdo_id, acuerdo in db.items():
        organismo = acuerdo.get("organismo_nombre", "No especificado")
        if organismo not in organismos:
            organismos[organismo] = []
        organismos[organismo].append(acuerdo)
    
    for organismo, acuerdos in sorted(organismos.items()):
        with st.expander(f"🏢 {organismo} ({len(acuerdos)} acuerdos)", expanded=False):
            for acuerdo in acuerdos:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{acuerdo['id']}**")
                    st.write(f"Año: {acuerdo.get('año', 'N/D')} | Tipo: {acuerdo.get('tipo_compromiso', 'N/D')}")
                with col2:
                    st.write(f"Estado: {acuerdo.get('estado', 'N/D')}")
                    st.write(f"Fichas: {len(acuerdo.get('fichas', []))}")
                with col3:
                    if st.button("📂 Abrir", key=f"open_{acuerdo['id']}"):
                        st.session_state["open_agr"] = acuerdo['id']
                        st.rerun()

def generar_listado_por_año(db):
    """Genera listado agrupado por año"""
    st.subheader("📅 Acuerdos por Año")
    
    # Agrupar por año
    años = {}
    for acuerdo_id, acuerdo in db.items():
        año = acuerdo.get("año", "No especificado")
        if año not in años:
            años[año] = []
        años[año].append(acuerdo)
    
    for año, acuerdos in sorted(años.items(), reverse=True):
        with st.expander(f"📅 Año {año} ({len(acuerdos)} acuerdos)", expanded=False):
            for acuerdo in acuerdos:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{acuerdo['id']}**")
                    st.write(f"Organismo: {acuerdo.get('organismo_nombre', 'N/D')}")
                with col2:
                    st.write(f"Tipo: {acuerdo.get('tipo_compromiso', 'N/D')}")
                    st.write(f"Estado: {acuerdo.get('estado', 'N/D')}")
                with col3:
                    if st.button("📂 Abrir", key=f"open_{acuerdo['id']}"):
                        st.session_state["open_agr"] = acuerdo['id']
                        st.rerun()                    

def agregar_opcion_clonar_menu():
    """Agrega la opción de clonar al menú principal"""
    # Esta función se integrará en el menú principal
    pass

def setup_autosave():
    """Configura el sistema de guardado automático"""
    if "autosave_enabled" not in st.session_state:
        st.session_state.autosave_enabled = True
    if "last_save_time" not in st.session_state:
        st.session_state.last_save_time = 0
    if "unsaved_changes" not in st.session_state:
        st.session_state.unsaved_changes = False

def autosave(db, agreement_id, force_save=False):
    """Guarda automáticamente si hay cambios pendientes"""
    if not st.session_state.get("autosave_enabled", True):
        return False
    
    current_time = time.time()
    last_save = st.session_state.get("last_save_time", 0)
    
    # 🆕 VERIFICAR QUE last_save NO SEA None
    if last_save is None:
        last_save = 0

    # Guardar si: forzado, o pasaron 30 segundos desde último guardado, o hay cambios no guardados
    if (force_save or 
        (current_time - last_save > 30 and st.session_state.get("unsaved_changes", False))):
        
        try:
            if agreements_save(db):
                st.session_state.last_save_time = current_time
                st.session_state.unsaved_changes = False
                print(f"💾 Guardado automático: {agreement_id}")
                return True
        except Exception as e:
            print(f"❌ Error guardado automático: {e}")
    
    return False

def mark_unsaved_changes():
    """Marca que hay cambios pendientes de guardar"""
    st.session_state.unsaved_changes = True

def page_reportes():
    require_login()
    
    # AGREGAR ESTAS VALIDACIONES AL INICIO
    if 'acuerdos_db' not in st.session_state:
        st.warning("⚠️ No hay datos cargados. Ve a 'Balanced Scorecard' primero.")
        
        # Intentar cargar datos
        try:
            datos = agreements_load()
            if isinstance(datos, dict):
                acuerdos = []
                for key, value in datos.items():
                    if isinstance(value, dict):
                        value['id'] = key
                        acuerdos.append(value)
                st.session_state['acuerdos_db'] = acuerdos
                st.success(f"✅ {len(acuerdos)} acuerdos cargados")
                st.rerun()
        except:
            st.error("No se pudieron cargar los datos")
            return
    
    acuerdos = st.session_state.get('acuerdos_db', [])
    
    if not acuerdos:
        st.warning("No hay acuerdos para generar reportes")
        return
    
    # 🆕 ESTILOS CSS PARA MEJORAR LA VISUALIZACIÓN
    st.markdown("""
    <style>
    /* Mejorar el ancho del contenido principal */
    .main .block-container {
        max-width: 95% !important;
        padding-left: 5% !important;
        padding-right: 5% !important;
    }
    
    /* Botones más grandes y visibles */
    .stButton button {
        width: 100%;
        margin: 5px 0;
    }
    
    /* Mejorar las métricas */
    .stMetric {
        background: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        border-left: 4px solid #007bff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("📊 Informes y Reportes")
    
    db = agreements_load()
    if not db:
        st.info("No hay acuerdos para generar reportes.")
        return

    # 🆕 NUEVA SECCIÓN: CREACIÓN DE INFORME PERSONALIZADO
    with st.expander("🆕 Crear Nuevo Informe Personalizado", expanded=False):
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            # Filtros para el informe
            years = sorted({a.get("año", date.today().year) for a in db.values()})
            selected_year = st.selectbox("Año del informe", options=years, index=len(years)-1, key="report_year")
            
            organismo_filter = st.text_input("Filtrar por Organismo (contiene)", key="report_org")
            
            tipos_seleccionados = st.multiselect(
                "Tipos de compromiso a incluir", 
                options=TIPO_COMPROMISO, 
                default=TIPO_COMPROMISO,
                key="report_types"
            )
        
        with col_config2:
            # Configuración del informe
            formato_reporte = st.selectbox(
                "Formato de salida",
                options=["PDF", "Excel", "HTML", "Pantalla"],
                key="report_format"
            )
            
            incluir_metricas = st.checkbox("Incluir métricas de cumplimiento", value=True)
            incluir_detalles = st.checkbox("Incluir detalles completos", value=True)
        
        # 🆕 BOTÓN PARA CREAR INFORME
        if st.button("📈 Generar Informe Personalizado", type="primary", key="generate_custom_report"):
            generar_informe_personalizado(db, selected_year, organismo_filter, tipos_seleccionados, 
                                        formato_reporte, incluir_metricas, incluir_detalles)

    st.markdown("---")
    
    # 🆕 SECCIÓN MEJORADA: REPORTES RÁPIDOS POR AÑO
    st.subheader("📋 Reportes por Año")
    
    col_filtros1, col_filtros2 = st.columns(2)
    
    with col_filtros1:
        years = sorted({a.get("año", date.today().year) for a in db.values()})
        selected_year = st.selectbox("Año", options=years, index=len(years)-1, key="year_filter")
    
    with col_filtros2:
        organismo_filter = st.text_input("Filtrar por Organismo (contiene)", key="org_filter")
    
    tipos_seleccionados = st.multiselect(
        "Tipo de compromiso", 
        options=TIPO_COMPROMISO, 
        default=TIPO_COMPROMISO,
        key="type_filter"
    )
    
    # Filtrar acuerdos
    acuerdos_filtrados = []
    for agr in db.values():
        if agr.get("año") != selected_year:
            continue
        if agr.get("tipo_compromiso") not in tipos_seleccionados:
            continue
        if organismo_filter and organismo_filter.strip().lower() not in (agr.get("organismo_nombre", "") or "").lower():
            continue
        acuerdos_filtrados.append(agr)
    
    st.success(f"✅ Acuerdos encontrados: {len(acuerdos_filtrados)}")
    
    # 🆕 BOTONES DE ACCIÓN PRINCIPALES
    col_acciones1, col_acciones2, col_acciones3, col_acciones4 = st.columns(4)
    
    with col_acciones1:
        if st.button("📊 Generar Reporte Consolidado", key="gen_consolidated"):
            generar_reporte_consolidado(acuerdos_filtrados, selected_year)
    
    with col_acciones2:
        if st.button("📈 Calcular Cumplimientos", key="calc_compliance"):
            calcular_todos_los_cumplimientos(acuerdos_filtrados)
            st.rerun()
    
    with col_acciones3:
        # Botón de impresión mejorado
        if st.button("🖨️ Vista para Imprimir", key="print_view"):
            mostrar_vista_imprimible(acuerdos_filtrados, selected_year)
    
    with col_acciones4:
        if st.button("📥 Exportar Todo", key="export_all"):
            exportar_reportes_completos(acuerdos_filtrados, selected_year)
    
        # 🆕 SECCIÓN DE MÉTRICAS DE CUMPLIMIENTO MEJORADA - VERSIÓN CORREGIDA
        if acuerdos_filtrados:
            st.subheader("📈 Métricas de Cumplimiento")
            
            # 🔧 CORRECCIÓN COMPLETA CON MANEJO DE None
            total_acuerdos = len(acuerdos_filtrados)
            total_metas = 0
            metas_cumplidas = 0
            metas_parciales = 0
            metas_no_cumplidas = 0
            cumplimiento_total = 0
            contador_cumplimientos = 0
            
            # Recorrer todos los acuerdos y calcular métricas
            for acuerdo in acuerdos_filtrados:
                for ficha in acuerdo.get('fichas', []):
                    for meta in ficha.get('metas', []):
                        total_metas += 1
                        estado = meta.get('estado', '').lower()
                        cumplimiento = meta.get('cumplimiento_calc')
                        
                        # 🛡️ MANEJO SEGURO DE VALORES None
                        if cumplimiento is not None:
                            try:
                                cumplimiento_valor = float(cumplimiento)
                                cumplimiento_total += cumplimiento_valor
                                contador_cumplimientos += 1
                                
                                if cumplimiento_valor >= 90:
                                    metas_cumplidas += 1
                                elif cumplimiento_valor >= 50:
                                    metas_parciales += 1
                                else:
                                    metas_no_cumplidas += 1
                            except (ValueError, TypeError):
                                # Si no se puede convertir a float, usar estado de texto
                                if 'cumplid' in estado:
                                    metas_cumplidas += 1
                                elif 'proceso' in estado or 'parcial' in estado:
                                    metas_parciales += 1
                                else:
                                    metas_no_cumplidas += 1
                        else:
                            # Si no hay valor de cumplimiento, usar estado de texto
                            if 'cumplid' in estado:
                                metas_cumplidas += 1
                            elif 'proceso' in estado or 'parcial' in estado:
                                metas_parciales += 1
                            else:
                                metas_no_cumplidas += 1
            
            # Calcular porcentajes
            porcentaje_cumplidas = (metas_cumplidas / total_metas * 100) if total_metas > 0 else 0
            porcentaje_parciales = (metas_parciales / total_metas * 100) if total_metas > 0 else 0
            porcentaje_no_cumplidas = (metas_no_cumplidas / total_metas * 100) if total_metas > 0 else 0
            cumplimiento_promedio = (cumplimiento_total / contador_cumplimientos) if contador_cumplimientos > 0 else 0
            
            # 🆕 MÉTRICAS MEJORADAS CON BARRAS DE PROGRESO
            col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)

            with col_metric1:
                st.metric(
                    "Cumplimiento Promedio", 
                    f"{cumplimiento_promedio:.1f}%"
                )
                # Barra de progreso
                if cumplimiento_promedio > 0:
                    st.progress(cumplimiento_promedio / 100)

            with col_metric2:
                st.metric("Acuerdos Evaluados", total_acuerdos)

            with col_metric3:
                st.metric("Total Metas", total_metas)

            with col_metric4:
                st.metric("Metas Cumplidas", 
                    f"{metas_cumplidas} ({porcentaje_cumplidas:.1f}%)")
    
        # 🆕 GRÁFICO DE DISTRIBUCIÓN DE CUMPLIMIENTO (SIN MATPLOTLIB)
        with st.expander("📊 Distribución de Cumplimiento de Metas", expanded=True):    
            col_dist1, col_dist2 = st.columns(2)
    
            with col_dist1:
                # 🆕 GRÁFICO DE BARRAS HORIZONTAL CON STREAMLIT NATIVO
                datos_grafico = {
                    'Categoría': ['Cumplidas', 'Parciales', 'No Cumplidas'],
                    'Cantidad': [metas_cumplidas, metas_parciales, metas_no_cumplidas],
                    'Porcentaje': [porcentaje_cumplidas, porcentaje_parciales, porcentaje_no_cumplidas]
                }
        
                df_grafico = pd.DataFrame(datos_grafico)
        
                # Mostrar como gráfico de barras horizontal
                st.bar_chart(df_grafico.set_index('Categoría')['Cantidad'])
        
                # Alternativa: mostrar como métricas visuales
                st.write("**Distribución Visual:**")
                for i, (categoria, cantidad, porcentaje) in enumerate(zip(
                    datos_grafico['Categoría'], 
                    datos_grafico['Cantidad'], 
                    datos_grafico['Porcentaje']
                )):
                    col_bar1, col_bar2, col_bar3 = st.columns([1, 4, 2])
                    with col_bar1:
                        st.write("✅" if i == 0 else "🟡" if i == 1 else "🔴")
                    with col_bar2:
                        st.progress(porcentaje / 100)
                    with col_bar3:
                        st.write(f"{porcentaje:.1f}%")
    
            with col_dist2:
                # Tabla resumen
                st.write("**Resumen de Metas:**")
                st.write(f"✅ **Cumplidas:** {metas_cumplidas} ({porcentaje_cumplidas:.1f}%)")
                st.write(f"🟡 **Parciales:** {metas_parciales} ({porcentaje_parciales:.1f}%)")
                st.write(f"🔴 **No Cumplidas:** {metas_no_cumplidas} ({porcentaje_no_cumplidas:.1f}%)")
        
                # 🆕 INDICADORES DE ESTADO
                if porcentaje_cumplidas >= 80:
                    st.success("🎉 **Excelente cumplimiento general**")
                elif porcentaje_cumplidas >= 60:
                    st.warning("⚠️ **Cumplimiento aceptable, requiere atención**")
                else:
                    st.error("🚨 **Cumplimiento bajo, necesita intervención**")
    
    # 🆕 LISTA MEJORADA DE ACUERDOS CON MÉTRICAS
    for i, agr in enumerate(acuerdos_filtrados):
        st.markdown("---")
        
        col_acuerdo1, col_acuerdo2, col_acuerdo3 = st.columns([3, 2, 1])
        
        with col_acuerdo1:
            st.subheader(f"{agr.get('id')} - {agr.get('organismo_nombre', 'Sin nombre')}")
            st.write(f"**Tipo:** {agr.get('tipo_compromiso')} | **Estado:** {agr.get('estado')}")
        
        with col_acuerdo2:
            # Calcular cumplimiento para este acuerdo
            cumplimiento_acuerdo = calcular_cumplimiento_acuerdo(agr)
            if cumplimiento_acuerdo is not None:
                st.metric(
                    "Cumplimiento Ponderado", 
                    f"{cumplimiento_acuerdo:.1f}%",
                    help="Calculado en base a las ponderaciones de cada meta"
                )
            else:
                st.info("Sin datos de cumplimiento")
        
        with col_acuerdo3:
            # 🆕 BOTONES DE ACCIÓN POR ACUERDO
            if st.button("📄 Reporte", key=f"rep_{agr['id']}"):
                generar_reporte_individual(agr)
            
            if st.button("🖨️ Imprimir", key=f"print_{agr['id']}"):
                generar_vista_imprimible_individual(agr)

# 🆕 FUNCIONES AUXILIARES NUEVAS - AGREGAR DESPUÉS DE page_reportes()

def calcular_cumplimiento_acuerdo_simple(acuerdo):
    """
    Calcula el cumplimiento general de un acuerdo de manera robusta
    """
    try:
        # ✅ PROTECCIÓN: Verificar que el acuerdo tenga metas
        if not acuerdo or 'metas' not in acuerdo or not acuerdo['metas']:
            return 0
        
        metas = acuerdo['metas']
        if not isinstance(metas, list) or len(metas) == 0:
            return 0
        
        total_metas = len(metas)
        suma_cumplimiento = 0
        metas_validas = 0
        
        # Calcular cumplimiento para cada meta
        for meta in metas:
            cumplimiento = calcular_cumplimiento(meta)
            if cumplimiento is not None:  # Solo contar metas válidas
                suma_cumplimiento += cumplimiento
                metas_validas += 1
        
        # ✅ PROTECCIÓN: Evitar división por cero
        if metas_validas == 0:
            return 0
        
        # Calcular promedio
        cumplimiento_promedio = suma_cumplimiento / metas_validas
        
        # Normalizar a porcentaje si es necesario
        return min(100.0, cumplimiento_promedio)
            
    except Exception as e:
        print(f"Error en calcular_cumplimiento_acuerdo: {str(e)}")
        return 0
    
def calcular_cumplimiento_acuerdo(agr: Dict[str, Any]) -> Optional[float]:
    """Calcula el cumplimiento ponderado considerando tipos de CG"""
    total_ponderacion = 0.0
    total_ponderado = 0.0
    metas_con_datos = 0
    
    for ficha in agr.get("fichas", []):
        ficha = agregar_tipo_cg(ficha)
        tipo_cg = ficha["tipo_cg"]
        
        for meta in ficha.get("metas", []):
            # Calcular cumplimiento si no está calculado
            if meta.get("cumplimiento_calc") is None:
                meta["cumplimiento_calc"] = calcular_cumplimiento(meta)
            
            if meta.get("cumplimiento_calc") is not None:
                # 🆕 AJUSTAR PONDERACIÓN SEGÚN TIPO DE CG
                ponderacion_base = float(meta.get("ponderacion", 0.0))
                
                if tipo_cg == "Funcional":
                    # Aplicar ponderación de categoría funcional
                    categoria = meta.get("categoria_funcional", "Institucional")
                    factor_categoria = {
                        "Institucional": 0.30,
                        "Grupal": 0.50,
                        "Individual": 0.20
                    }.get(categoria, 1.0)
                    
                    ponderacion_efectiva = ponderacion_base * factor_categoria
                else:
                    ponderacion_efectiva = ponderacion_base
                
                cumplimiento = meta["cumplimiento_calc"]
                total_ponderacion += ponderacion_efectiva
                total_ponderado += cumplimiento * ponderacion_efectiva
                metas_con_datos += 1
    
    if total_ponderacion > 0 and metas_con_datos > 0:
        return total_ponderado / total_ponderacion
    return None   

def calcular_metricas_globales(acuerdos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula métricas globales usando rangos configurables por meta"""
    total_acuerdos = len(acuerdos)
    total_metas = 0
    metas_cumplidas = 0
    metas_parciales = 0
    metas_no_cumplidas = 0
    cumplimientos = []
    
    if not acuerdos:
        return {
            'total_acuerdos': 0,
            'total_metas': 0,
            'metas_cumplidas': 0,
            'metas_parciales': 0,
            'metas_no_cumplidas': 0,
            'porcentaje_cumplidas': 0,
            'porcentaje_parciales': 0,
            'porcentaje_no_cumplidas': 0,
            'cumplimiento_promedio': 0
        }
    
    for agr in acuerdos:
        # Contar metas y clasificar por cumplimiento
        for ficha in agr.get("fichas", []):
            for meta in ficha.get("metas", []):
                total_metas += 1
                
                # 🆕 CLASIFICACIÓN FLEXIBLE CON SIGNOS EDITABLES
                clasificacion = clasificar_cumplimiento_meta(
                    meta.get("cumplimiento_calc"), 
                    meta.get("clasificacion", {
                        "cumplido": {"operador": "≥", "valor": 95, "color": "✅"},
                        "parcial": {"operador": "≥", "valor": 75, "color": "🟡"},
                        "no_cumplido": {"operador": "<", "valor": 75, "color": "🔴"}
                    })
                )
                
                # 🆕 CONTAR SEGÚN LA NUEVA CLASIFICACIÓN (que incluye emojis)
                if "Cumplido" in clasificacion:
                    metas_cumplidas += 1
                elif "Parcial" in clasificacion:
                    metas_parciales += 1
                elif "No Cumplido" in clasificacion:
                    metas_no_cumplidas += 1
                # "Sin evaluar" no se cuenta en ninguna categoría
        
        # Calcular cumplimiento del acuerdo
        cumplimiento_acuerdo = calcular_cumplimiento_acuerdo(agr)
        if cumplimiento_acuerdo is not None:
            cumplimientos.append(cumplimiento_acuerdo)
    
    # 🆕 CÁLCULO SEGURO DEL PROMEDIO
    cumplimiento_promedio = sum(cumplimientos) / len(cumplimientos) if cumplimientos else 0
    
    return {
        'total_acuerdos': total_acuerdos,
        'total_metas': total_metas,
        'metas_cumplidas': metas_cumplidas,
        'metas_parciales': metas_parciales,
        'metas_no_cumplidas': metas_no_cumplidas,
        'porcentaje_cumplidas': (metas_cumplidas / total_metas * 100) if total_metas > 0 else 0,
        'porcentaje_parciales': (metas_parciales / total_metas * 100) if total_metas > 0 else 0,
        'porcentaje_no_cumplidas': (metas_no_cumplidas / total_metas * 100) if total_metas > 0 else 0,
        'cumplimiento_promedio': cumplimiento_promedio
    }

def promedio_solo_con_datos(valores):
    """
    Calcula promedio excluyendo valores no numéricos.
    """
    valores_validos = [
        v for v in valores if isinstance(v, (int, float))
    ]
    if not valores_validos:
        return None
    return sum(valores_validos) / len(valores_validos)

def promedio_ponderado_metas(metas):
    """
    Calcula cumplimiento ponderado usando meta['ponderacion'].
    """
    suma = 0
    peso_total = 0

    for meta in metas:
        valor = meta.get("cumplimiento_calc")
        peso = meta.get("ponderacion", 0)

        if isinstance(valor, (int, float)) and peso > 0:
            suma += valor * peso
            peso_total += peso

    if peso_total == 0:
        return None

    return suma / peso_total

def generar_reporte_consolidado(acuerdos: List[Dict[str, Any]], año: int):
    """Genera un reporte consolidado de todos los acuerdos"""
    with st.spinner("Generando reporte consolidado..."):
        # Crear datos para Excel
        datos_excel = []
        
        for agr in acuerdos:
            cumplimiento = calcular_cumplimiento_acuerdo(agr)
            
            for ficha in agr.get("fichas", []):
                for meta in ficha.get("metas", []):
                    datos_excel.append({
                        'Año': año,
                        'Acuerdo': agr.get('id'),
                        'Organismo': agr.get('organismo_nombre'),
                        'Tipo': agr.get('tipo_compromiso'),
                        'Estado': agr.get('estado'),
                        'Ficha': ficha.get('id'),
                        'Meta': meta.get('descripcion'),
                        'Ponderación': meta.get('ponderacion', 0),
                        'Cumplimiento': meta.get('cumplimiento_calc', 'No calculado'),
                        'Cumplimiento Acuerdo': f"{cumplimiento:.1f}%" if cumplimiento else "No calculado"
                    })
        
        if datos_excel:
            df = pd.DataFrame(datos_excel)
            
            # Crear archivo Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte Consolidado', index=False)
                
                # Formato
                workbook = writer.book
                worksheet = writer.sheets['Reporte Consolidado']
                format_header = workbook.add_format({'bold': True, 'bg_color': '#007BFF', 'color': 'white'})
                
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, format_header)
            
            output.seek(0)
            
            st.download_button(
                "📥 Descargar Reporte Consolidado (Excel)",
                data=output.getvalue(),
                file_name=f"reporte_consolidado_{año}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No hay datos para generar el reporte")

def mostrar_vista_imprimible(acuerdos: List[Dict[str, Any]], año: int):
    """Muestra una vista optimizada para impresión incluyendo firmas"""
    st.info("🔍 **Vista para Imprimir** - Use Ctrl+P en su navegador para imprimir")
    
    for agr in acuerdos:
        st.markdown("---")
        st.header(f"ACUERDO: {agr.get('id')}")
        st.subheader(f"Organismo: {agr.get('organismo_nombre')}")
        st.write(f"**Tipo:** {agr.get('tipo_compromiso')}")
        st.write(f"**Estado:** {agr.get('estado')}")
        
        # 🆕 MOSTRAR INFORMACIÓN DE FIRMAS
        if agr.get("firmas"):
            st.markdown("---")
            st.subheader("📝 FIRMAS DEL ACUERDO")
            
            col_firma1, col_firma2 = st.columns(2)
            
            with col_firma1:
                st.markdown("**👤 CONTRAPARTE**")
                firma_contra = agr["firmas"].get("contraparte", {})
                if firma_contra.get("imagen_base64"):
                    st.image(f"data:image/png;base64,{firma_contra['imagen_base64']}", 
                            width=200, caption="Firma Contraparte")
                st.write(f"**Nombre:** {firma_contra.get('nombre', 'No registrado')}")
                st.write(f"**Cargo:** {firma_contra.get('cargo', 'No registrado')}")
                st.write(f"**Institución:** {firma_contra.get('institucion', 'No registrada')}")
            
            with col_firma2:
                st.markdown("**👤 INSTITUCIÓN**")
                firma_inst = agr["firmas"].get("institucion", {})
                if firma_inst.get("imagen_base64"):
                    st.image(f"data:image/png;base64,{firma_inst['imagen_base64']}", 
                            width=200, caption="Firma Institución")
                st.write(f"**Nombre:** {firma_inst.get('nombre', 'No registrado')}")
                st.write(f"**Cargo:** {firma_inst.get('cargo', 'No registrado')}")
                st.write(f"**Institución:** {firma_inst.get('institucion', 'No registrada')}")
            
            # 🆕 FECHA DE FIRMA
            if agr["firmas"].get("fecha_firma"):
                st.write(f"**📅 Fecha de Firma:** {agr['firmas']['fecha_firma']}")
        
        cumplimiento = calcular_cumplimiento_acuerdo(agr)
        if cumplimiento:
            st.metric("**Cumplimiento Ponderado Total**", f"{cumplimiento:.1f}%")
        
        # Mostrar fichas y metas
        for ficha in agr.get("fichas", []):
            st.markdown("---")
            st.subheader(f"FICHA: {ficha.get('id')} - {ficha.get('nombre')}")
            
            for meta in ficha.get("metas", []):
                with st.expander(f"Meta {meta.get('numero')}: {meta.get('descripcion')}", expanded=False):
                    col_meta1, col_meta2, col_meta3 = st.columns([3, 1, 1])
                    with col_meta1:
                        st.write(f"**Descripción:** {meta.get('descripcion')}")
                        st.write(f"**Unidad:** {meta.get('unidad', 'No especificada')}")
                        st.write(f"**Valor Objetivo:** {meta.get('valor_objetivo', 'No definido')}")
                    with col_meta2:
                        st.write(f"**Ponderación:** {meta.get('ponderacion', 0)}%")
                    with col_meta3:
                        cumplimiento_meta = meta.get('cumplimiento_calc')
                        if cumplimiento_meta is not None:
                            # 🆕 USAR CLASIFICACIÓN CON SIGNOS EDITABLES
                            clasificacion = clasificar_cumplimiento_meta(
                                cumplimiento_meta,
                                meta.get("clasificacion", {
                                    "cumplido": {"operador": "≥", "valor": 95, "color": "✅"},
                                    "parcial": {"operador": "≥", "valor": 75, "color": "🟡"},
                                    "no_cumplido": {"operador": "<", "valor": 75, "color": "🔴"}
                                })
                            )
                            st.write(f"**Cumplimiento:** {cumplimiento_meta:.1f}%")
                            st.write(f"**Estado:** {clasificacion}")
                        else:
                            st.write("**Cumplimiento:** No calculado")
                    
                    # 🆕 MOSTRAR RANGOS DE CLASIFICACIÓN CONFIGURADOS
                    if meta.get("clasificacion"):
                        clasif = meta["clasificacion"]
                        st.write("**🎯 Criterios de Clasificación:**")
                        st.write(f"- Cumplido: {clasif['cumplido']['operador']}{clasif['cumplido']['valor']}%")
                        st.write(f"- Parcial: {clasif['parcial']['operador']}{clasif['parcial']['valor']}%") 
                        st.write(f"- No Cumplido: {clasif['no_cumplido']['operador']}{clasif['no_cumplido']['valor']}%")

def calcular_todos_los_cumplimientos(acuerdos: List[Dict[str, Any]]):
    """Calcula los cumplimientos de todas las metas"""
    with st.spinner("Calculando cumplimientos..."):
        total_calculadas = 0
        for agr in acuerdos:
            for ficha in agr.get("fichas", []):
                for meta in ficha.get("metas", []):
                    if meta.get("cumplimiento_valor"):
                        meta["cumplimiento_calc"] = calcular_cumplimiento(meta)
                        if meta["cumplimiento_calc"] is not None:
                            total_calculadas += 1
        
        st.success(f"✅ Se calcularon {total_calculadas} cumplimientos")

@st.cache_data(ttl=60, show_spinner=False)
def generar_informe_personalizado(db, año, organismo_filter, tipos_seleccionados, formato, incluir_metricas, incluir_detalles):
    """Genera un informe personalizado según los filtros especificados"""
    with st.spinner("Generando informe personalizado..."):
        # Filtrar acuerdos
        acuerdos_filtrados = []
        for agr in db.values():
            if agr.get("año") != año:
                continue
            if agr.get("tipo_compromiso") not in tipos_seleccionados:
                continue
            if organismo_filter and organismo_filter.strip().lower() not in (agr.get("organismo_nombre", "") or "").lower():
                continue
            acuerdos_filtrados.append(agr)
        
        if not acuerdos_filtrados:
            st.warning("No hay acuerdos que coincidan con los filtros seleccionados.")
            return
        
        # Generar según formato
        if formato == "PDF":
            generar_pdf_informe(acuerdos_filtrados, año, organismo_filter)
        elif formato == "Excel":
            generar_excel_informe(acuerdos_filtrados, año)
        elif formato == "HTML":
            generar_html_informe(acuerdos_filtrados, año)
        else:  # Pantalla
            mostrar_informe_pantalla(acuerdos_filtrados, año, incluir_metricas, incluir_detalles)

def exportar_reportes_completos(acuerdos, año):
    """Exporta todos los reportes en un paquete ZIP"""
    with st.spinner("Preparando paquete de exportación..."):
        # Crear archivo en memoria
        mem_zip = io.BytesIO()
        
        with zipfile.ZipFile(mem_zip, mode='w') as zf:
            # 1. Reporte consolidado Excel
            datos_excel = []
            for agr in acuerdos:
                cumplimiento = calcular_cumplimiento_acuerdo(agr)
                for ficha in agr.get("fichas", []):
                    for meta in ficha.get("metas", []):
                        datos_excel.append({
                            'Año': año,
                            'Acuerdo_ID': agr.get('id'),
                            'Organismo': agr.get('organismo_nombre'),
                            'Tipo_Compromiso': agr.get('tipo_compromiso'),
                            'Estado': agr.get('estado'),
                            'Ficha_ID': ficha.get('id'),
                            'Ficha_Nombre': ficha.get('nombre'),
                            'Meta_Descripcion': meta.get('descripcion'),
                            'Meta_Numero': meta.get('numero'),
                            'Ponderacion': meta.get('ponderacion', 0),
                            'Cumplimiento_Meta': meta.get('cumplimiento_calc', 'No calculado'),
                            'Cumplimiento_Acuerdo': f"{cumplimiento:.1f}%" if cumplimiento else "No calculado"
                        })
            
            if datos_excel:
                df_excel = pd.DataFrame(datos_excel)
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_excel.to_excel(writer, sheet_name='Reporte_Consolidado', index=False)
                excel_buffer.seek(0)
                zf.writestr(f"reporte_consolidado_{año}.xlsx", excel_buffer.getvalue())
            
            # 2. Reportes individuales en JSON
            for agr in acuerdos:
                json_data = json.dumps(agr, ensure_ascii=False, indent=2, default=str)
                zf.writestr(f"{agr['id']}_completo.json", json_data)
            
            # 3. Archivo de resumen
            resumen = f"""RESUMEN DE REPORTES - AÑO {año}
Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Total acuerdos: {len(acuerdos)}
Total fichas: {sum(len(agr.get('fichas', [])) for agr in acuerdos)}
Total metas: {sum(len(ficha.get('metas', [])) for agr in acuerdos for ficha in agr.get('fichas', []))}

Acuerdos incluidos:
"""
            for agr in acuerdos:
                cumplimiento = calcular_cumplimiento_acuerdo(agr)
                resumen += f"- {agr['id']}: {agr.get('organismo_nombre')} (Cumplimiento: {cumplimiento:.1f}%)\n"
            
            zf.writestr("RESUMEN.txt", resumen)
        
        mem_zip.seek(0)
        
        st.download_button(
            "📦 Descargar Paquete Completo (ZIP)",
            data=mem_zip.getvalue(),
            file_name=f"reportes_completos_{año}.zip",
            mime="application/zip"
        )

def generar_reporte_individual(agr):
    """Genera un reporte individual para un acuerdo específico"""
    with st.spinner(f"Generando reporte para {agr['id']}..."):
        # Crear múltiples formatos
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # JSON completo
            json_data = json.dumps(agr, ensure_ascii=False, indent=2, default=str)
            st.download_button(
                "📄 JSON Completo",
                data=json_data.encode('utf-8'),
                file_name=f"{agr['id']}.json",
                mime="application/json"
            )
        
        with col2:
            # CSV horizontal
            csv_data = export_csv_horizontal_agreement(agr)
            st.download_button(
                "📊 CSV Horizontal",
                data=csv_data.encode('utf-8'),
                file_name=f"{agr['id']}.csv",
                mime="text/csv"
            )
        
        with col3:
            # HTML imprimible
            html_data = exportar_html_imprimible(agr)
            st.download_button(
                "🌐 HTML Imprimible",
                data=html_data.encode('utf-8'),
                file_name=f"{agr['id']}.html",
                mime="text/html"
            )
        
        # Mostrar resumen en pantalla
        st.subheader(f"Resumen del Acuerdo: {agr['id']}")
        
        cumplimiento = calcular_cumplimiento_acuerdo(agr)
        if cumplimiento:
            st.metric("Cumplimiento Ponderado Total", f"{cumplimiento:.1f}%")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write(f"**Organismo:** {agr.get('organismo_nombre')}")
            st.write(f"**Tipo:** {agr.get('tipo_compromiso')}")
            st.write(f"**Estado:** {agr.get('estado')}")
        
        with col_res2:
            st.write(f"**Fichas:** {len(agr.get('fichas', []))}")
            st.write(f"**Metas:** {sum(len(f.get('metas', [])) for f in agr.get('fichas', []))}")
            st.write(f"**Año:** {agr.get('año')}")

# ✅ FUNCIÓN NUEVA - CON CACHE (solo para generar contenido)
@st.cache_data(ttl=60, show_spinner=False)
def generar_contenido_html_imprimible(agr):
    """Genera el contenido HTML - esta función SÍ puede estar cacheada"""
    return exportar_html_imprimible(agr)

# ✅ FUNCIÓN ACTUAL MODIFICADA - SIN CACHE (para widgets)
def generar_vista_imprimible_individual(agr):
    """Genera vista optimizada para impresión de un acuerdo individual"""
    
    # 🆕 GENERAR EL HTML MEJORADO (desde función cacheada)
    html_content = generar_contenido_html_imprimible(agr)
    
    # 🆕 BOTONES DE ACCIÓN PRINCIPALES (FUERA del cache)
    st.info("**📄 Vista Optimizada para Impresión** - Descargue el HTML y ábralo en su navegador para imprimir (Ctrl+P)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            "💾 Descargar HTML Completo",
            data=html_content.encode('utf-8'),
            file_name=f"{agr['id']}_completo.html",
            mime="text/html",
            help="Descargue y abra en su navegador para mejor calidad de impresión",
            key=f"download_completo_{agr['id']}"  # Key única
        )
    
    with col2:
        st.download_button(
            "🖨️ Versión para Imprimir",
            data=html_content.encode('utf-8'),
            file_name=f"{agr['id']}_imprimir.html",
            mime="text/html",
            help="Optimizado específicamente para impresión",
            key=f"download_imprimir_{agr['id']}"  # Key única
        )
    
    with col3:
        if st.button("👁️ Vista Previa Rápida", key=f"preview_{agr['id']}"):
            # Mostrar vista previa expandida
            with st.expander("🔍 Vista Previa del Documento", expanded=True):
                st.components.v1.html(html_content, height=600, scrolling=True)
    
    # 🆕 BOTÓN PARA OCULTAR/MOSTRAR CONTENIDO
    if st.button("📋 Mostrar/Ocultar Contenido del Acuerdo", key=f"toggle_{agr['id']}"):
        if "mostrar_contenido_acuerdo" not in st.session_state:
            st.session_state.mostrar_contenido_acuerdo = True
        else:
            st.session_state.mostrar_contenido_acuerdo = not st.session_state.mostrar_contenido_acuerdo
    
    # 🆕 CONTENIDO COMPLETO DEL ACUERDO (SOLO SI SE MUESTRA)
    if st.session_state.get("mostrar_contenido_acuerdo", True):
        st.markdown("---")
        st.subheader(f"📋 Contenido Completo del Acuerdo: {agr['id']}")
        
        # 🆕 INFORMACIÓN GENERAL
        with st.expander("Información General del Acuerdo", expanded=False):
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.write(f"**Organismo:** {agr.get('organismo_nombre', 'No especificado')}")
                st.write(f"**Tipo de Organismo:** {agr.get('organismo_tipo', 'No especificado')}")
                st.write(f"**Naturaleza Jurídica:** {agr.get('naturaleza_juridica', 'No especificado')}")
                st.write(f"**Año:** {agr.get('año', 'No especificado')}")
            
            with col_info2:
                st.write(f"**Estado:** {agr.get('estado', 'No especificado')}")
                st.write(f"**Tipo de Compromiso:** {agr.get('tipo_compromiso', 'No especificado')}")
                st.write(f"**Vigencia:** {agr.get('vigencia_desde', '')} al {agr.get('vigencia_hasta', '')}")
                st.write(f"**Organismo de Enlace:** {agr.get('organismo_enlace', 'No especificado')}")
        
        # 🆕 OBJETO DEL ACUERDO
        if agr.get('objeto'):
            with st.expander("Objeto del Acuerdo", expanded=False):
                st.write(agr.get('objeto'))
        
        # 🆕 PARTES FIRMANTES
        if agr.get('partes_firmantes'):
            with st.expander("Partes Firmantes", expanded=False):
                st.write(agr.get('partes_firmantes'))
        
        # 🆕 CLAÚSULAS
        if agr.get('clausulas'):
            clausulas_no_vacias = [c for c in agr.get('clausulas', []) if c.strip()]
            if clausulas_no_vacias:
                with st.expander("Cláusulas del Acuerdo", expanded=False):
                    for i, clausula in enumerate(clausulas_no_vacias, 1):
                        st.write(f"**{i}.** {clausula}")
        
        # 🆕 FICHAS Y METAS
        if agr.get('fichas'):
            st.subheader("Fichas de Compromiso")
            
            for ficha_index, ficha in enumerate(agr.get('fichas', [])):
                with st.expander(f"Ficha {ficha.get('id')} - {ficha.get('nombre', 'Sin nombre')}", expanded=False):
                    
                    # Información de la ficha
                    col_ficha1, col_ficha2 = st.columns(2)
                    
                    with col_ficha1:
                        st.write(f"**Tipo de Meta:** {ficha.get('tipo_meta', 'No especificado')}")
                        st.write(f"**Responsables de Cumplimiento:** {ficha.get('responsables_cumpl', 'No especificado')}")
                        st.write(f"**Objetivo:** {ficha.get('objetivo', 'No especificado')}")
                        st.write(f"**Indicador:** {ficha.get('indicador', 'No especificado')}")
                    
                    with col_ficha2:
                        st.write(f"**Forma de Cálculo:** {ficha.get('forma_calculo', 'No especificado')}")
                        st.write(f"**Fuente de Información:** {ficha.get('fuente', 'No especificado')}")
                        st.write(f"**Valor Base:** {ficha.get('valor_base', 'No especificado')}")
                        st.write(f"**Requiere Salvaguarda:** {'SÍ' if ficha.get('salvaguarda_flag') else 'NO'}")
                    
                    if ficha.get('observaciones'):
                        st.write(f"**Observaciones:** {ficha.get('observaciones')}")
                    
                    # 🆕 METAS DE LA FICHA
                    if ficha.get('metas'):
                        st.subheader(f"Metas de la Ficha ({len(ficha['metas'])})")
                        
                        for meta_index, meta in enumerate(ficha.get('metas', [])):
                            with st.expander(f"Meta {meta.get('numero')}: {meta.get('descripcion', 'Sin descripción')}", expanded=False):
                                
                                col_meta1, col_meta2 = st.columns(2)
                                
                                with col_meta1:
                                    st.write(f"**Unidad:** {meta.get('unidad', 'No especificado')}")
                                    st.write(f"**Valor Objetivo:** {meta.get('valor_objetivo', 'No especificado')}")
                                    st.write(f"**Sentido:** {meta.get('sentido', 'No especificado')}")
                                    st.write(f"**Frecuencia:** {meta.get('frecuencia', 'No especificado')}")
                                
                                with col_meta2:
                                    st.write(f"**Vencimiento:** {meta.get('vencimiento', 'No especificado')}")
                                    st.write(f"**Es Hito:** {'SÍ' if meta.get('es_hito') else 'NO'}")
                                    st.write(f"**Ponderación:** {meta.get('ponderacion', 0)}%")
                                    
                                    # 🆕 CUMPLIMIENTO CON INDICADOR VISUAL
                                    cumplimiento = meta.get('cumplimiento_calc')
                                    if cumplimiento is not None:
                                        if cumplimiento >= 95:
                                            estado = "✅ Cumplida"
                                            color = "green"
                                        elif cumplimiento >= 60:
                                            estado = "🟡 Parcial"
                                            color = "orange"
                                        else:
                                            estado = "🔴 No Cumplida"
                                            color = "red"
                                        
                                        st.write(f"**Cumplimiento:** {cumplimiento:.1f}%")
                                        st.write(f"**Estado:** :{color}[{estado}]")
                                    else:
                                        st.write("**Cumplimiento:** No calculado")
                                
                                # 🆕 RANGOS DE CUMPLIMIENTO
                                if meta.get('rango'):
                                    st.write("**Rangos de Cumplimiento:**")
                                    for rango_index, rango in enumerate(meta.get('rango', [])):
                                        st.write(f"  - {rango.get('min', '')} a {rango.get('max', '')} → {rango.get('porcentaje', '')}%")
                                
                                if meta.get('observaciones'):
                                    st.write(f"**Observaciones:** {meta.get('observaciones')}")
    
    # 🆕 INSTRUCCIONES DE IMPRESIÓN (SIEMPRE VISIBLES)
    with st.expander("📋 Instrucciones para Imprimir", expanded=True):
        st.markdown("""
        **Para obtener la mejor calidad de impresión:**
        
        1. **📥 Descargue el archivo HTML** usando el botón arriba
        2. **🔓 Ábralo en su navegador** (Chrome, Firefox, Edge)
        3. **🖨️ Use Ctrl+P** para imprimir
        4. **⚙️ Configure la impresión:**
           - Orientación: Horizontal (recomendado)
           - Márgenes: Mínimos
           - Escala: 100%
           - Opción: "Antecedentes de gráficos" (activar)
        
        **💡 Consejos:**
        - El diseño está optimizado para papel A4
        - Use calidad de impresión alta para mejores resultados
        - Puede ocultar este contenido usando el botón "Mostrar/Ocultar Contenido"
        """)
    
    # 🆕 ESTADÍSTICAS RÁPIDAS
    with st.expander("📈 Estadísticas Rápidas", expanded=False):
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            total_fichas = len(agr.get('fichas', []))
            st.metric("Total Fichas", total_fichas)
        
        with col_stat2:
            total_metas = sum(len(f.get('metas', [])) for f in agr.get('fichas', []))
            st.metric("Total Metas", total_metas)
        
        with col_stat3:
            cumplimiento = calcular_cumplimiento_acuerdo(agr)
            if cumplimiento:
                st.metric("Cumplimiento General", f"{cumplimiento:.1f}%")
            else:
                st.metric("Cumplimiento General", "No calculado")

# FUNCIONES AUXILIARES PARA FORMATOS ESPECÍFICOS
@st.cache_data(ttl=60, show_spinner=False)
def generar_pdf_informe(acuerdos, año, filtro_organismo):
    """Genera informe en formato PDF (simulado)"""
    # Nota: Para PDF real necesitarías librerías como reportlab o weasyprint
    # Esta es una simulación que genera un HTML mejorado
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reporte PDF - Año {año}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }}
            .acuerdo {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
            .metricas {{ background: #f5f5f5; padding: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>REPORTE DE COMPROMISOS DE GESTIÓN</h1>
            <h2>Año: {año}</h2>
            <p>Filtro organismo: {filtro_organismo or 'Todos'}</p>
            <p>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
    """
    
    for agr in acuerdos:
        cumplimiento = calcular_cumplimiento_acuerdo(agr)
        html_content += f"""
        <div class="acuerdo">
            <h3>{agr.get('id')} - {agr.get('organismo_nombre')}</h3>
            <div class="metricas">
                <strong>Cumplimiento: {cumplimiento:.1f}% si está disponible</strong> |
                Fichas: {len(agr.get('fichas', []))} | 
                Metas: {sum(len(f.get('metas', [])) for f in agr.get('fichas', []))}
            </div>
        </div>
        """
    
    html_content += "</body></html>"
    
    st.download_button(
        "📄 Descargar PDF (HTML)",
        data=html_content.encode('utf-8'),
        file_name=f"reporte_{año}.html",
        mime="text/html",
        help="Para PDF real, se necesita configuración adicional del servidor"
    )

@st.cache_data(ttl=60, show_spinner=False)
def generar_excel_informe(acuerdos, año):
    """Genera informe en formato Excel"""
    # Reutilizar la función de exportación existente
    exportar_reportes_completos(acuerdos, año)

@st.cache_data(ttl=60, show_spinner=False)
def generar_html_informe(acuerdos, año):
    """Genera informe en formato HTML SIN EMOJIS"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reporte Completo - Año {año}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .acuerdo {{ page-break-inside: avoid; margin: 30px 0; }}
            .ficha {{ background: #f9f9f9; padding: 15px; margin: 10px 0; }}
            .meta {{ border-left: 3px solid #007cba; padding-left: 10px; }}
        </style>
    </head>
    <body>
        <h1>Reporte Completo - Año {año}</h1>
    """
    
    for agr in acuerdos:
        html_content += f"<div class='acuerdo'><h2>{agr.get('id')} - {agr.get('organismo_nombre')}</h2>"
        
        for ficha in agr.get("fichas", []):
            html_content += f"<div class='ficha'><h3>Ficha: {ficha.get('nombre')}</h3>"
            
            for meta in ficha.get("metas", []):
                html_content += f"""
                <div class='meta'>
                    <h4>Meta {meta.get('numero')}: {meta.get('descripcion')}</h4>
                    <p>Ponderación: {meta.get('ponderacion')}% | Cumplimiento: {meta.get('cumplimiento_calc', 'N/A')}%</p>
                </div>
                """
            
            html_content += "</div>"
        html_content += "</div>"
    
    html_content += "</body></html>"
    
    st.download_button(
        "📄 Descargar HTML Completo",
        data=html_content.encode('utf-8'),
        file_name=f"reporte_completo_{año}.html",
        mime="text/html"
    )

def mostrar_informe_pantalla(acuerdos, año, incluir_metricas, incluir_detalles):
    """Muestra el informe directamente en pantalla"""
    st.success(f"📊 Informe generado para {len(acuerdos)} acuerdos del año {año}")
    
    if incluir_metricas:
        metricas = calcular_metricas_globales(acuerdos)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Acuerdos", metricas['total_acuerdos'])
        col2.metric("Metas", metricas['total_metas'])
        col3.metric("Metas Cumplidas", metricas['metas_cumplidas'])
        col4.metric("Cumplimiento Prom.", f"{metricas['cumplimiento_promedio']:.1f}%")
    
    if incluir_detalles:
        for agr in acuerdos:
            with st.expander(f"{agr.get('id')} - {agr.get('organismo_nombre')}"):
                cumplimiento = calcular_cumplimiento_acuerdo(agr)
                st.write(f"**Cumplimiento:** {cumplimiento:.1f}% si está disponible")
                st.write(f"**Fichas:** {len(agr.get('fichas', []))}")
                st.write(f"**Metas:** {sum(len(f.get('metas', [])) for f in agr.get('fichas', []))}")

def corregir_metas_sin_nombre(acuerdo):
    """Asigna nombres automáticos a metas que no tienen nombre"""
    for ficha in acuerdo.get('fichas', []):
        for i, meta in enumerate(ficha.get('metas', [])):
            if not meta.get('nombre') or meta.get('nombre') == 'Sin nombre':
                # Asignar nombre automático basado en la ficha y número
                nombre_ficha = ficha.get('nombre', 'Ficha')
                meta['nombre'] = f"{nombre_ficha} - Meta {i+1}"
    return acuerdo

def sidebar():
    st.sidebar.title("Menú")
    
    if st.session_state.user:
        st.sidebar.write(
            f"👤 {st.session_state.user.get('name','')} -- {st.session_state.user['role']}"
        )
        
        st.sidebar.markdown("---")
        st.sidebar.caption("🔬 **Sistema en Fase de Pruebas**")
        st.sidebar.caption("Datos visibles para todos los usuarios")

        options = [
            "Inicio", 
            "Generar Acuerdos",
            "📋 Clonar Acuerdos",  
            "📊 Listados de Acuerdos",
            "🎯 Carga por Metas",           
            "📈 Carga por Indicadores",     
            "Seguimiento de Indicadores", 
            "📈 Dashboard Control",
            "📊 Balanced Scorecard",
            "🎓 Tutorial",
            "Reportes",
            "📊 Análisis Comparativo",
            "🔴 Análisis de Riesgos"
        ]
        
        if st.session_state.user["role"] == "Administrador":
            options.append("Administración")
        
        choice = st.sidebar.radio(
            "Ir a",
            options,
            key="sidebar_navigation"
        )
        
        if st.session_state.user["role"] in ["Administrador", "Supervisor OPP"]:
            check_permissions()
        
        if st.session_state.user["role"] == "Administrador":
            verificar_archivos_indicadores()
        
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.user = None
            st.rerun()
        
        return choice
    
    return "Login"
    
def mostrar_acciones_rapidas():
    """Muestra los botones de acciones rápidas en todas las subpáginas del home"""
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 **Ver y Gestionar Acuerdos**", 
                    use_container_width=True,
                    type="primary" if st.session_state.home_subpage == "acuerdos" else "secondary",
                    key="btn_acuerdos_global"):
            st.session_state.home_subpage = "acuerdos"
            st.rerun()
    
    with col2:
        if st.button("📊 **Generar Informes y Reportes**", 
                    use_container_width=True,
                    type="primary" if st.session_state.home_subpage == "reportes" else "secondary", 
                    key="btn_reportes_global"):
            st.session_state.home_subpage = "reportes"
            st.rerun()
    
    with col3:
        if st.button("📈 **Seguimiento de Indicadores**", 
                    use_container_width=True,
                    type="primary" if st.session_state.home_subpage == "seguimiento" else "secondary",
                    key="btn_seguimiento_global"):
            st.session_state.home_subpage = "seguimiento"
            st.rerun()
    
    # Botón para volver al home principal (solo visible cuando estamos en subpáginas)
    if st.session_state.home_subpage != "main":
        st.markdown("---")
        if st.button("← **Volver al Inicio Principal**", use_container_width=True):
            st.session_state.home_subpage = "main"
            st.rerun()   
 
# 🆕 FUNCIÓN HOME MEJORADA 
def page_home_mejorada():
    """Página de inicio mejorada visualmente"""
    
    # 🚨 AGREGA ESTA LÍNEA AL PRINCIPIO
    st.session_state.current_page = "Inicio"

    # HEADER ATRACTIVO
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.title("🏛️ Sistema de Compromisos de Gestión")
        st.markdown("### Plataforma de OPP")
        st.markdown("*Herramienta integral para la gestión y seguimiento de Compromisos de Gestión*")
          
    # MÉTRICAS PRINCIPALES CON DATOS REALES
    st.subheader("📊 Dashboard de Gestión - Resumen Ejecutivo")
    
    # 🆕 CARGAR DATOS REALES
    db = agreements_load()
    
    # Calcular métricas REALES
    total_acuerdos = len(db) if db else 0
    
    total_metas = 0
    metas_cumplidas = 0
    total_indicadores = 0
    total_seguimientos = 0
    organismos_unicos = set()
    
    for acuerdo in db.values() if db else []:
        # Contar organismos únicos
        organismo = acuerdo.get('organismo_nombre')
        if organismo:
            organismos_unicos.add(organismo)
        
        # Contar metas e indicadores
        for ficha in acuerdo.get("fichas", []):
            metas_ficha = len(ficha.get("metas", []))
            total_metas += metas_ficha
            total_indicadores += metas_ficha  # Cada meta es un indicador
            
            # Contar metas cumplidas
            for meta in ficha.get("metas", []):
                cumplimiento = meta.get("cumplimiento_calc")
                # 🆕 VERIFICAR SEGURO QUE NO SEA None Y SEA NÚMERO
                if cumplimiento is not None and isinstance(cumplimiento, (int, float)):
                    # 🆕 USAR LA NUEVA CLASIFICACIÓN CON SIGNOS EDITABLES
                    clasificacion = clasificar_cumplimiento_meta(
                        cumplimiento, 
                        meta.get("clasificacion", {
                            "cumplido": {"operador": "≥", "valor": 95, "color": "✅"},
                            "parcial": {"operador": "≥", "valor": 75, "color": "🟡"},
                            "no_cumplido": {"operador": "<", "valor": 75, "color": "🔴"}
                        })
                    )
                    # Contar como cumplida si la clasificación es "Cumplido"
                    if "Cumplido" in clasificacion:
                        metas_cumplidas += 1
                
                # Contar seguimientos (metas con datos de cumplimiento)
                if meta.get("cumplimiento_valor") or meta.get("cumplimiento_calc") is not None:
                    total_seguimientos += 1
    
    # Calcular porcentajes
    porcentaje_cumplidas = (metas_cumplidas / total_metas * 100) if total_metas > 0 else 0
    tasa_exito = porcentaje_cumplidas  # Usar mismo porcentaje por ahora
    
    # Fila 1 de métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🏢 Acuerdos Activos", 
            value=total_acuerdos, 
            delta=None,
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="🎯 Metas Cumplidas", 
            value=f"{porcentaje_cumplidas:.1f}%", 
            delta=None,
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="📈 Indicadores", 
            value=total_indicadores, 
            delta=None,
            delta_color="normal"
        )
    
    with col4:
        st.metric(
            label="👥 Usuarios Activos", 
            value="1", 
            delta=None,
            delta_color="normal"
        )
    
    # Fila 2 de métricas
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            label="📋 Seguimientos", 
            value=total_seguimientos, 
            delta=None,
            delta_color="normal"
        )
    
    with col6:
        # Contar reportes (acuerdos con estado diferente a Borrador)
        reportes_generados = sum(1 for a in db.values() if db and a.get('estado') != 'Borrador')
        st.metric(
            label="📄 Reportes", 
            value=reportes_generados, 
            delta=None,
            delta_color="normal"
        )
    
    with col7:
        st.metric(
            label="⚡ Tasa de Éxito", 
            value=f"{tasa_exito:.1f}%", 
            delta=None,
            delta_color="normal"
        )
    
    with col8:
        st.metric(
            label="🏭 Organismos", 
            value=len(organismos_unicos), 
            delta=None,
            delta_color="off"
        )
    
    # SISTEMA DE ALERTAS MEJORADO CON DATOS REALES
    st.markdown("---")
    st.subheader("🔔 Sistema de Alertas y Notificaciones")
    
    alert_col1, alert_col2 = st.columns(2)
    
    with alert_col1:
        # 🆕 ALERTAS BASADAS EN DATOS REALES
        if total_acuerdos == 0:
            st.info("""
            ℹ️ **Sistema Listo**
            - No hay acuerdos en el sistema
            - Puede crear el primer acuerdo
            """)
        else:
            # Contar acuerdos próximos a vencer
            acuerdos_proximos_vencer = []
            for acuerdo_id, acuerdo in db.items():
                vencimiento = acuerdo.get('vigencia_hasta', '')
                if vencimiento:
                    try:
                        fecha_venc = datetime.strptime(vencimiento[:10], "%Y-%m-%d").date()
                        dias_restantes = (fecha_venc - date.today()).days
                        if 0 < dias_restantes <= 30:  # Próximos 30 días
                            acuerdos_proximos_vencer.append(f"{acuerdo_id} ({dias_restantes} días)")
                    except:
                        pass
            
            if acuerdos_proximos_vencer:
                lista_vencimientos = "\n".join([f"- {acuerdo}" for acuerdo in acuerdos_proximos_vencer[:3]])  # Mostrar máximo 3
                st.warning(f"""
                ⚠️ **Acuerdos Próximos a Vencer**
                {lista_vencimientos}
                """)
            else:
                st.success("""
                ✅ **Sin Vencimientos Próximos**
                - Todos los acuerdos tienen vigencia adecuada
                """)
            
            # Alertas de actualizaciones pendientes
            actualizaciones_pendientes = sum(
                1 for acuerdo in db.values()
                for ficha in acuerdo.get('fichas', [])
                for meta in ficha.get('metas', [])
                if meta.get('cumplimiento_calc') is None
            )
            
            if actualizaciones_pendientes > 0:
                st.info(f"""
                ℹ️ **Seguimientos Pendientes**
                - {actualizaciones_pendientes} meta(s) sin datos de cumplimiento
                """)
            else:
                st.success("""
                ✅ **Seguimientos al Día**
                - Todas las metas tienen datos actualizados
                """)
    
    with alert_col2:
        # 🆕 ESTADO DEL SISTEMA BASADO EN DATOS REALES
        if total_acuerdos == 0:
            st.info("""
            📋 **Sistema Vacío**
            - Base de datos sin acuerdos
            - Estado inicial del sistema
            """)
        else:
            # Calcular estado general del sistema
            acuerdos_aprobados = sum(1 for a in db.values() if a.get('estado') == 'Aprobado')
            acuerdos_borrador = sum(1 for a in db.values() if a.get('estado') == 'Borrador')
            
            st.success(f"""
            ✅ **Sistema Operativo**
            - {acuerdos_aprobados} acuerdo(s) aprobados
            - {acuerdos_borrador} acuerdo(s) en borrador
            - Sistema funcionando correctamente
            """)
            
            # Alertas de atención requerida
            indicadores_fuera_rango = 0
            for acuerdo in db.values():
                for ficha in acuerdo.get("fichas", []):
                    for meta in ficha.get("metas", []):
                        cumplimiento = meta.get('cumplimiento_calc')
                        if (cumplimiento is not None and 
                            isinstance(cumplimiento, (int, float)) and 
                            cumplimiento < 60):
                            indicadores_fuera_rango += 1
            
            if indicadores_fuera_rango > 0:
                st.error(f"""
                🚨 **Atención Requerida**
                - {indicadores_fuera_rango} indicador(es) con cumplimiento < 60%
                """)
            else:
                st.success("""
                ✅ **Rendimiento Adecuado**
                - Sin indicadores críticos
                """)
    
    # --- FECHAS ACTUALES (VISIBLES SIEMPRE) ---
    ahora = datetime.now()
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**🕐 Última actualización:** {ahora.strftime('%d/%m/%Y %H:%M')}")
    with col2:
        st.write(f"**📅 Próxima revisión:** {(ahora + timedelta(days=30)).strftime('%d/%m/%Y')}")
    
    st.markdown("---")  # Línea separadora
    
    # INFORMACIÓN DEL SISTEMA MEJORADA
    with st.expander("📋 Información del Sistema y Soporte", expanded=False):
        tab1, tab2, tab3 = st.tabs(["🏛️ Sistema", "📞 Soporte", "🔒 Seguridad"])
        
        with tab1:
            st.write("""
            **Sistema de Compromisos de Gestión v2.1.0**
            
            **Características principales:**
            - Gestión integral de compromisos institucionales
            - Seguimiento de indicadores en tiempo real  
            - Sistema de firmas digitales y escaneadas
            - Reportes ejecutivos automatizados
            - Control de acceso por roles y permisos
            - Dashboard interactivo de métricas
            """)
            
            # Fecha de compilación/versión dentro del sistema
            st.write(f"**🔧 Compilado el:** {ahora.strftime('%d/%m/%Y %H:%M')}")
        
        with tab2:
            st.write("""
            **Soporte Técnico y Asistencia**
            
            📧 **Email:
            📞 **Teléfono:** +598 2 150 
            🕒 **Horario:** Lunes a Viernes 9:00 - 17:00
            """)

        with tab3:
            st.write("""
            **Políticas de Seguridad y Acceso**
            
            🔒 **Certificaciones:**
            - ISO 27001:2013
            - Nivel de seguridad: ALTO
            - Encriptación: AES-256
            
            **Accesos:**
            - Autenticación de dos factores
            - Registro de auditoría completo
            - Backup diario automático
            - Monitoreo 24/7
            """)

# FUNCIONES FALTANTES

def setup_autosave():
    """Configuración básica de autoguardado - REEMPLAZO"""
    if "autosave_setup" not in st.session_state:
        st.session_state.autosave_setup = True

def mark_unsaved_changes():
    """Marca cambios no guardados - REEMPLAZO"""
    st.session_state.unsaved_changes = True

# Variable global agreements faltante
agreements = {}

# ============================================================================
# BALANCED SCORECARD - ADAPTADO PARA TU agreements.json
# ============================================================================

def generar_bsc_organismo(organismo_id):
    """Genera Balanced Scorecard para un organismo - USANDO TU agreements.json"""
    import json
    import streamlit as st
    
    # 🎯 USAR TU ARCHIVO EXACTO: agreements.json
    archivo_bd = 'agreements.json'
    
    try:
        with open(archivo_bd, 'r', encoding='utf-8') as f:
            db = json.load(f)
        
        # DEBUG: Mostrar estructura para verificar
        st.sidebar.info(f"📂 BD cargada: {archivo_bd}")
        if 'acuerdos' in db:
            st.sidebar.success(f"✅ {len(db['acuerdos'])} acuerdos encontrados")
            
    except Exception as e:
        st.error(f"❌ Error al cargar {archivo_bd}: {str(e)}")
        return {"error": f"No se pudo cargar {archivo_bd}"}
    
    # Buscar el organismo
    organismo_info = obtener_info_organismo_bsc(db, organismo_id)
    if not organismo_info:
        # Intentar buscar por nombre aproximado
        organismo_info = buscar_organismo_aproximado_bsc(db, organismo_id)
        if not organismo_info:
            return {"error": f"Organismo '{organismo_id}' no encontrado"}
    
    datos_historicos = obtener_datos_historicos_organismo_bsc(db, organismo_id)
    
    bsc = {
        'metadata': {
            'organismo_id': organismo_id,
            'nombre_organismo': organismo_info.get('nombre', organismo_id),
            'fecha_generacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'periodo_analizado': datos_historicos.get('periodo_analizado', 'Últimos años'),
            'archivo_fuente': archivo_bd
        },
        'resumen_ejecutivo': calcular_resumen_ejecutivo_bsc(datos_historicos),
        'perspectivas': generar_perspectivas_tu_sistema_bsc(datos_historicos),
        'recomendaciones': generar_recomendaciones_tu_sistema_bsc(datos_historicos),
        'datos_fuente': {
            'total_acuerdos': len(datos_historicos.get('acuerdos', [])),
            'total_metas': datos_historicos.get('total_metas', 0),
            'metas_analizadas': datos_historicos.get('metas_analizadas', 0),
            'años_analizados': list(datos_historicos.get('estadisticas_por_año', {}).keys())
        }
    }
    
    return bsc

def obtener_info_organismo_bsc(db, organismo_id):
    """Obtiene información del organismo desde TU agreements.json"""
    # Primero buscar por ID exacto
    for acuerdo in db.get('acuerdos', []):
        if acuerdo.get('organismo_id') == organismo_id:
            return {
                'nombre': acuerdo.get('organismo_nombre', organismo_id),
                'sigla': acuerdo.get('organismo_sigla', ''),
                'sector': acuerdo.get('sector', 'General'),
                'acuerdo_id': acuerdo.get('id'),
                'año': acuerdo.get('año')
            }
    
    # Si no encuentra, buscar por nombre que contenga el ID
    for acuerdo in db.get('acuerdos', []):
        org_nombre = acuerdo.get('organismo_nombre', '').lower()
        if organismo_id.lower() in org_nombre:
            return {
                'nombre': acuerdo.get('organismo_nombre'),
                'sigla': acuerdo.get('organismo_sigla', ''),
                'sector': acuerdo.get('sector', 'General'),
                'acuerdo_id': acuerdo.get('id'),
                'año': acuerdo.get('año')
            }
    
    return None

def buscar_organismo_aproximado_bsc(db, texto_busqueda):
    """Busca organismo por texto aproximado"""
    texto = texto_busqueda.lower()
    
    for acuerdo in db.get('acuerdos', []):
        # Buscar en varios campos
        campos = [
            acuerdo.get('organismo_id', ''),
            acuerdo.get('organismo_nombre', ''),
            acuerdo.get('organismo_sigla', ''),
            acuerdo.get('id', '')  # ID del acuerdo también puede contener referencia
        ]
        
        for campo in campos:
            if campo and texto in campo.lower():
                return {
                    'nombre': acuerdo.get('organismo_nombre', 'Organismo'),
                    'sigla': acuerdo.get('organismo_sigla', ''),
                    'sector': acuerdo.get('sector', 'General'),
                    'acuerdo_id': acuerdo.get('id'),
                    'año': acuerdo.get('año')
                }
    
    return None

def obtener_datos_historicos_organismo_bsc(db, organismo_id):
    """Obtiene datos históricos del organismo desde TU agreements.json"""
    
    acuerdos_organismo = []
    todas_metas = []
    año_actual = datetime.now().year
    
    # Buscar TODOS los acuerdos de este organismo
    for acuerdo in db.get('acuerdos', []):
        org_id = acuerdo.get('organismo_id', '')
        org_nombre = acuerdo.get('organismo_nombre', '')
        
        # Verificar si es el organismo buscado
        es_organismo = (
            org_id == organismo_id or 
            organismo_id.lower() in org_nombre.lower() or
            (org_id and organismo_id.lower() in org_id.lower())
        )
        
        if es_organismo:
            fichas = acuerdo.get('fichas', [])
            metas_acuerdo = []
            
            for ficha in fichas:
                metas = ficha.get('metas', [])
                for meta in metas:
                    meta_info = {
                        'id': meta.get('id', ''),
                        'codigo': meta.get('id', '')[:20],  # Usar ID como código
                        'descripcion': meta.get('descripcion', meta.get('nombre', 'Sin descripción')),
                        'estado': meta.get('estado', 'No Iniciada'),
                        'ponderacion': float(meta.get('ponderacion', 0)),
                        'cumplimiento_calc': meta.get('cumplimiento_calc'),
                        'valor_objetivo': meta.get('valor_objetivo', ''),
                        'unidad': meta.get('unidad', '%'),
                        'vencimiento': meta.get('vencimiento', ''),
                        'categoria_funcional': meta.get('categoria_funcional', ''),
                        'historial_estados': meta.get('historial_estados', []),
                        'problemas': []  # Se llenará después
                    }
                    
                    # Detectar problemas automáticamente
                    problemas = detectar_problemas_meta_bsc(meta)
                    meta_info['problemas'] = problemas
                    
                    metas_acuerdo.append(meta_info)
                    todas_metas.append(meta_info)
            
            acuerdos_organismo.append({
                'id': acuerdo.get('id', ''),
                'nombre': acuerdo.get('nombre', 'Sin nombre'),
                'año': acuerdo.get('año', año_actual),
                'estado_acuerdo': acuerdo.get('estado', 'Borrador'),
                'total_metas': len(metas_acuerdo),
                'metas': metas_acuerdo
            })
    
    # Calcular estadísticas por año
    años = {}
    for acuerdo in acuerdos_organismo:
        año = acuerdo['año']
        if año not in años:
            años[año] = {
                'total_metas': 0,
                'metas_cumplidas': 0,
                'metas_en_proceso': 0,
                'metas_no_iniciadas': 0,
                'total_ponderacion': 0,
                'metas_sin_ponderacion': 0,
                'metas_con_problemas': 0
            }
        
        años[año]['total_metas'] += acuerdo['total_metas']
        
        for meta in acuerdo['metas']:
            estado = meta.get('estado', '').lower()
            
            # Contar por estado
            if 'cumplid' in estado:
                años[año]['metas_cumplidas'] += 1
            elif 'proceso' in estado or 'ejecución' in estado:
                años[año]['metas_en_proceso'] += 1
            elif 'no iniciad' in estado:
                años[año]['metas_no_iniciadas'] += 1
            
            # Contar ponderación
            ponderacion = meta.get('ponderacion', 0)
            años[año]['total_ponderacion'] += ponderacion
            if ponderacion == 0:
                años[año]['metas_sin_ponderacion'] += 1
            
            # Contar problemas
            if meta.get('problemas'):
                años[año]['metas_con_problemas'] += 1
    
    # Ordenar años
    años_ordenados = dict(sorted(años.items(), key=lambda x: x[0], reverse=True))
    
    return {
        'organismo_id': organismo_id,
        'acuerdos': acuerdos_organismo,
        'metas_analizadas': len(todas_metas),
        'total_metas': sum(len(a['metas']) for a in acuerdos_organismo),
        'estadisticas_por_año': años_ordenados,
        'periodo_analizado': f"{min(años.keys()) if años else año_actual}-{max(años.keys()) if años else año_actual}",
        'detalle_metas': todas_metas
    }

def detectar_problemas_meta_bsc(meta):
    """Detecta problemas automáticamente en una meta"""
       
    problemas = []
    
    # 1. Sin ponderación
    if meta.get('ponderacion', 0) == 0:
        problemas.append("Sin ponderación asignada")
    
    # 2. Estado no iniciado
    estado = meta.get('estado', '').lower()
    if 'no iniciad' in estado:
        problemas.append("No iniciada")
    
    # 3. Sin valor objetivo
    if not meta.get('valor_objetivo'):
        problemas.append("Sin valor objetivo")
    
    # 4. Vencimiento próximo (si tiene fecha)
    vencimiento = meta.get('vencimiento', '')
    if vencimiento:
        try:
            hoy = date.today()
            venc = datetime.strptime(vencimiento[:10], '%Y-%m-%d').date()
            dias_restantes = (venc - hoy).days
            
            if 0 < dias_restantes <= 30:
                problemas.append(f"Vencimiento próximo ({dias_restantes} días)")
            elif dias_restantes < 0:
                problemas.append("Vencida")
        except:
            pass
    
    return problemas

def calcular_resumen_ejecutivo_bsc(datos_historicos):
    """Calcula el resumen ejecutivo del BSC"""
    if not datos_historicos.get('estadisticas_por_año'):
        return {
            'score_estrategico': 0,
            'nivel_rendimiento': '🔴 SIN DATOS',
            'tendencia_general': 'SIN DATOS',
            'total_metas': 0,
            'metas_cumplidas': 0,
            'tasa_cumplimiento': 0
        }
    
    años = datos_historicos['estadisticas_por_año']
    años_lista = sorted(años.keys())
    año_actual = años_lista[-1] if años_lista else None
    
    if not año_actual:
        return {"error": "No hay datos"}
    
    stats = años[año_actual]
    total_metas = stats['total_metas']
    metas_cumplidas = stats['metas_cumplidas']
    
    # Calcular score simple
    if total_metas > 0:
        tasa_cumplimiento = (metas_cumplidas / total_metas) * 100
        puntaje_ponderacion = min(30, (stats['total_ponderacion'] / 100) * 30)
        puntaje_proceso = (stats['metas_en_proceso'] / total_metas) * 20
        score = min(100, tasa_cumplimiento * 0.5 + puntaje_ponderacion + puntaje_proceso)
    else:
        tasa_cumplimiento = 0
        score = 0
    
    # Determinar nivel
    if score >= 80:
        nivel = "🟢 EXCELENTE"
    elif score >= 60:
        nivel = "🟡 BUENO"
    elif score >= 40:
        nivel = "🟠 ACEPTABLE"
    else:
        nivel = "🔴 CRÍTICO"
    
    # Tendencia
    if len(años_lista) > 1:
        año_anterior = años_lista[-2]
        tasa_actual = (años[año_actual]['metas_cumplidas'] / años[año_actual]['total_metas']) * 100 if años[año_actual]['total_metas'] > 0 else 0
        tasa_anterior = (años[año_anterior]['metas_cumplidas'] / años[año_anterior]['total_metas']) * 100 if años[año_anterior]['total_metas'] > 0 else 0
        
        if tasa_actual > tasa_anterior + 5:
            tendencia = "MEJORANDO ↗"
        elif tasa_actual < tasa_anterior - 5:
            tendencia = "EMPEORANDO ↘"
        else:
            tendencia = "ESTABLE →"
    else:
        tendencia = "DATOS INSUFICIENTES"
    
    return {
        'score_estrategico': round(score, 1),
        'nivel_rendimiento': nivel,
        'tendencia_general': tendencia,
        'total_metas': total_metas,
        'metas_cumplidas': metas_cumplidas,
        'tasa_cumplimiento': round(tasa_cumplimiento, 1)
    }

def generar_perspectivas_tu_sistema_bsc(datos_historicos):
    """Genera las 4 perspectivas del BSC"""
    if not datos_historicos.get('estadisticas_por_año'):
        return {
            'financiera': {'nombre': 'Gestión de Recursos', 'objetivo': 'Sin datos', 'kpis': []},
            'impacto': {'nombre': 'Resultados', 'objetivo': 'Sin datos', 'kpis': []},
            'procesos': {'nombre': 'Procesos', 'objetivo': 'Sin datos', 'kpis': []},
            'aprendizaje': {'nombre': 'Aprendizaje', 'objetivo': 'Sin datos', 'kpis': []}
        }
    
    años = datos_historicos['estadisticas_por_año']
    año_actual = max(años.keys())
    stats = años[año_actual]
    
    total_metas = stats.get('total_metas', 0)
    metas_cumplidas = stats.get('metas_cumplidas', 0)
    ponderacion_total = stats.get('total_ponderacion', 0)
    metas_sin_ponderacion = stats.get('metas_sin_ponderacion', 0)
    metas_con_problemas = stats.get('metas_con_problemas', 0)
    
    return {
        'financiera': {
            'nombre': 'Gestión de Recursos',
            'objetivo': 'Uso eficiente de recursos y priorización',
            'kpis': [
                {
                    'nombre': 'Ponderación Asignada',
                    'valor': f"{ponderacion_total:.1f}%",
                    'meta': '100%',
                    'estado': '🟢' if ponderacion_total >= 80 else '🟡' if ponderacion_total >= 50 else '🔴',
                    'interpretacion': f"De {total_metas} metas, {metas_sin_ponderacion} sin ponderación"
                },
                {
                    'nombre': 'Metas con Problemas',
                    'valor': f"{metas_con_problemas}",
                    'meta': 'Minimizar',
                    'estado': '🟢' if metas_con_problemas == 0 else '🟡' if metas_con_problemas <= 3 else '🔴',
                    'interpretacion': 'Metas que requieren atención'
                }
            ]
        },
        'impacto': {
            'nombre': 'Resultados e Impacto',
            'objetivo': 'Cumplimiento de objetivos estratégicos',
            'kpis': [
                {
                    'nombre': 'Tasa de Cumplimiento',
                    'valor': f"{(metas_cumplidas / total_metas * 100) if total_metas > 0 else 0:.1f}%",
                    'meta': '≥80%',
                    'estado': '🟢' if (metas_cumplidas / total_metas * 100) >= 80 else '🟡' if (metas_cumplidas / total_metas * 100) >= 50 else '🔴',
                    'interpretacion': f"{metas_cumplidas} de {total_metas} metas cumplidas"
                },
                {
                    'nombre': 'Metas en Ejecución',
                    'valor': f"{stats.get('metas_en_proceso', 0)}",
                    'meta': 'Máximo posible',
                    'estado': '🟢' if stats.get('metas_en_proceso', 0) > 0 else '🔴',
                    'interpretacion': 'Metas activamente en proceso'
                }
            ]
        },
        'procesos': {
            'nombre': 'Excelencia Operativa',
            'objetivo': 'Procesos eficientes y gestión efectiva',
            'kpis': [
                {
                    'nombre': 'Metas No Iniciadas',
                    'valor': f"{stats.get('metas_no_iniciadas', 0)}",
                    'meta': '0',
                    'estado': '🟢' if stats.get('metas_no_iniciadas', 0) == 0 else '🔴',
                    'interpretacion': 'Metas pendientes de activación'
                },
                {
                    'nombre': 'Tasa de Activación',
                    'valor': f"{((total_metas - stats.get('metas_no_iniciadas', 0)) / total_metas * 100) if total_metas > 0 else 0:.1f}%",
                    'meta': '100%',
                    'estado': '🟢' if stats.get('metas_no_iniciadas', 0) == 0 else '🟡',
                    'interpretacion': 'Porcentaje de metas iniciadas'
                }
            ]
        },
        'aprendizaje': {
            'nombre': 'Innovación y Desarrollo',
            'objetivo': 'Mejora continua y capacidades organizacionales',
            'kpis': [
                {
                    'nombre': 'Seguimiento de Metas',
                    'valor': f"{total_metas - stats.get('metas_no_iniciadas', 0)}/{total_metas}",
                    'meta': '100%',
                    'estado': '🟡',
                    'interpretacion': 'Metas con seguimiento activo'
                },
                {
                    'nombre': 'Metas con Historial',
                    'valor': 'Por analizar',
                    'meta': 'Todas las metas',
                    'estado': '🟡',
                    'interpretacion': 'Metas con historial de estados registrado'
                }
            ]
        }
    }

def generar_recomendaciones_tu_sistema_bsc(datos_historicos):
    """Genera recomendaciones basadas en datos"""
    recomendaciones = []
    
    if not datos_historicos.get('estadisticas_por_año'):
        recomendaciones.append({
            'prioridad': 'ALTA',
            'area': 'Datos Básicos',
            'accion': 'Completar información de metas en el sistema',
            'responsable': 'Responsable del organismo',
            'plazo': 'Inmediato'
        })
        return recomendaciones
    
    años = datos_historicos['estadisticas_por_año']
    año_actual = max(años.keys())
    stats = años[año_actual]
    
    # Recomendación 1: Ponderaciones
    if stats.get('total_ponderacion', 0) < 80:
        recomendaciones.append({
            'prioridad': 'ALTA' if stats['total_ponderacion'] < 50 else 'MEDIA',
            'area': 'Gestión de Metas',
            'accion': f'Completar ponderaciones (actual: {stats["total_ponderacion"]:.1f}%, meta: 100%)',
            'responsable': 'Coordinador de CG',
            'plazo': '1 mes'
        })
    
    # Recomendación 2: Metas no iniciadas
    if stats.get('metas_no_iniciadas', 0) > 0:
        recomendaciones.append({
            'prioridad': 'ALTA',
            'area': 'Ejecución',
            'accion': f'Activar {stats["metas_no_iniciadas"]} metas no iniciadas',
            'responsable': 'Jefes de área',
            'plazo': '15 días'
        })
    
    # Recomendación 3: Metas con problemas
    if stats.get('metas_con_problemas', 0) > 0:
        recomendaciones.append({
            'prioridad': 'MEDIA',
            'area': 'Gestión de Calidad',
            'accion': f'Revisar {stats["metas_con_problemas"]} metas con problemas detectados',
            'responsable': 'Unidad de Control',
            'plazo': '2 semanas'
        })
    
    if not recomendaciones:
        recomendaciones.append({
            'prioridad': 'MEDIA',
            'area': 'Mejora Continua',
            'accion': 'Documentar y replicar mejores prácticas exitosas',
            'responsable': 'Todos los equipos',
            'plazo': 'Continuo'
        })
    
    return recomendaciones

def mostrar_bsc_en_streamlit():
    """Muestra el Balanced Scorecard (BSC) para visualizar el desempeño de los acuerdos."""
    
        
    st.title("📊 Balanced Scorecard (BSC) - Sistema de Control de Gestión")
    st.markdown("### Visualización Integral del Desempeño por Organismo")
    
    # 🎯 CARGAR DATOS DE TU ESTRUCTURA ESPECÍFICA
    try:
        # Tu agreements_load() devuelve dict donde cada clave es un ID de acuerdo
        datos_dict = agreements_load()
        
        st.success(f"✅ Sistema CG: {len(datos_dict)} acuerdos cargados")
        
        # CONVERTIR: De diccionario de acuerdos a lista de acuerdos
        acuerdos = []
        for acuerdo_id, acuerdo_data in datos_dict.items():
            # Asegurar que cada acuerdo tenga su ID
            acuerdo_data['id'] = acuerdo_id  # Agregar el ID si no está
            acuerdos.append(acuerdo_data)
        
        st.info(f"📋 Convertidos {len(acuerdos)} acuerdos a formato lista")
        
    except Exception as e:
        st.error(f"❌ Error al cargar acuerdos: {e}")
        
        # Botón para intentar cargar directamente
        if st.button("🔄 Intentar cargar desde archivo JSON"):
            try:
                # Intentar cargar de diferentes formas
                datos = load_json("agreements.json")
                if isinstance(datos, dict):
                    # Convertir dict a lista
                    acuerdos = []
                    for key, value in datos.items():
                        if isinstance(value, dict):
                            value['id'] = key
                            acuerdos.append(value)
                    st.success(f"✅ {len(acuerdos)} acuerdos cargados desde JSON")
                else:
                    st.error("Formato de archivo no reconocido")
                    return
            except Exception as json_error:
                st.error(f"Error JSON: {json_error}")
                return
    
    # 🛡️ VERIFICAR DATOS
    if 'acuerdos' not in locals() or not acuerdos:
        st.error("❌ No se pudieron cargar los acuerdos")
        return
    
    if len(acuerdos) == 0:
        st.warning("📭 No hay acuerdos en la base de datos")
        return
    
    # Mostrar ejemplo de estructura
    with st.expander("🔍 Ver estructura de un acuerdo de ejemplo", expanded=False):
        if acuerdos:
            st.json(acuerdos[0])
    
    # Guardar en session_state
    st.session_state['acuerdos_db'] = acuerdos
    
    # 🔍 INFORMACIÓN DEL SISTEMA
    st.sidebar.write("---")
    st.sidebar.write("📊 Información del sistema:")
    st.sidebar.write(f"Total acuerdos: {len(acuerdos)}")
    
    if len(acuerdos) > 0:
        primer_acuerdo = acuerdos[0]
        st.sidebar.write(f"Ejemplo ID: {primer_acuerdo.get('id', 'N/A')}")
    
    # 1. FILTROS PARA EL BSC
    st.sidebar.header("🔍 Filtros BSC")
    
    # Extraer organismos únicos
    organismos_unicos = []
    for acuerdo in acuerdos:
        organismo = acuerdo.get('organismo_nombre')  # En tu caso es 'organismo_nombre'
        if organismo and organismo not in organismos_unicos:
            organismos_unicos.append(organismo)
    
    if organismos_unicos:
        organismos_unicos = sorted(organismos_unicos)
    else:
        organismos_unicos = ["Sin organismo especificado"]
    
    organismo_seleccionado = st.sidebar.selectbox(
        "Seleccionar Organismo:",
        options=["TODOS LOS ORGANISMOS"] + organismos_unicos,
        index=0
    )
    
    # Filtro por año
    años = []
    for acuerdo in acuerdos:
        año = acuerdo.get('año')
        if año and año not in años:
            años.append(año)
    
    if años:
        años = sorted(años)
        año_seleccionado = st.sidebar.selectbox(
            "Filtrar por año:",
            options=["TODOS"] + años
        )
    else:
        año_seleccionado = "TODOS"
    
    # 2. FILTRAR ACUERDOS
    acuerdos_filtrados = []
    for acuerdo in acuerdos:
        # Verificar organismo
        if organismo_seleccionado != "TODOS LOS ORGANISMOS":
            if acuerdo.get('organismo_nombre') != organismo_seleccionado:
                continue
        
        # Verificar año
        if año_seleccionado != "TODOS":
            if acuerdo.get('año') != año_seleccionado:
                continue
        
        acuerdos_filtrados.append(acuerdo)
    
    if not acuerdos_filtrados:
        st.warning(f"⚠️ No hay acuerdos para los filtros seleccionados.")
        st.info(f"Organismos disponibles: {', '.join(organismos_unicos)}")
        return
    
    # 3. MÉTRICAS PRINCIPALES BASADAS EN TUS ACUERDOS
    st.header("📈 Métricas de Desempeño")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Contar acuerdos activos (basado en vigencia)
        hoy = datetime.now()
        activos = 0
        for acuerdo in acuerdos_filtrados:
            vigencia_hasta = acuerdo.get('vigencia_hasta')
            if vigencia_hasta:
                try:
                    fecha_fin = datetime.strptime(vigencia_hasta, '%Y-%m-%d')
                    if fecha_fin > hoy:
                        activos += 1
                except:
                    pass
        
        st.metric("📅 Acuerdos Activos", activos, f"de {len(acuerdos_filtrados)}")
    
    with col2:
        # Calcular métricas de fichas
        total_fichas = 0
        for acuerdo in acuerdos_filtrados:
            fichas = acuerdo.get('fichas', [])
            total_fichas += len(fichas)
        
        st.metric("📁 Fichas Totales", total_fichas)
    
    with col3:
        # Calcular métricas de metas
        total_metas = 0
        metas_cumplidas = 0
        
        for acuerdo in acuerdos_filtrados:
            for ficha in acuerdo.get('fichas', []):
                metas = ficha.get('metas', [])
                total_metas += len(metas)
                
                for meta in metas:
                    estado = meta.get('estado', '')
                    if 'cumplid' in estado.lower():
                        metas_cumplidas += 1
        
        tasa_cumplimiento = (metas_cumplidas / total_metas * 100) if total_metas > 0 else 0
        st.metric("🎯 Cumplimiento Metas", f"{tasa_cumplimiento:.1f}%", f"{metas_cumplidas}/{total_metas}")
    
    with col4:
        # Días promedio hasta vencimiento
        dias_totales = 0
        contador = 0
        
        for acuerdo in acuerdos_filtrados:
            vigencia_hasta = acuerdo.get('vigencia_hasta')
            if vigencia_hasta:
                try:
                    fecha_fin = datetime.strptime(vigencia_hasta, '%Y-%m-%d')
                    dias = (fecha_fin - hoy).days
                    if dias >= 0:
                        dias_totales += dias
                        contador += 1
                except:
                    pass
        
        dias_prom = dias_totales / contador if contador > 0 else 0
        st.metric("⏳ Días Promedio", f"{dias_prom:.0f}")
    
    # 4. PERSPECTIVAS DEL BSC ADAPTADAS A TUS DATOS
    st.header("🎯 Perspectivas del Balanced Scorecard")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Financiera", 
        "👥 Impacto Social", 
        "🔄 Procesos", 
        "🧠 Aprendizaje"
    ])
    
    with tab1:
        st.subheader("Perspectiva Financiera")
        
        # Análisis por tipo de compromiso
        tipos_compromiso = {}
        for acuerdo in acuerdos_filtrados:
            tipo = acuerdo.get('tipo_compromiso', 'No especificado')
            if tipo not in tipos_compromiso:
                tipos_compromiso[tipo] = 0
            tipos_compromiso[tipo] += 1
        
        if tipos_compromiso:
            import pandas as pd
            df_tipos = pd.DataFrame({
                'Tipo de Compromiso': list(tipos_compromiso.keys()),
                'Cantidad': list(tipos_compromiso.values())
            })
            st.dataframe(df_tipos, use_container_width=True)
        
        st.markdown("**Indicadores Clave:**")
        st.markdown("""
        - Distribución por tipo de compromiso
        - Eficiencia en asignación de recursos
        - Cumplimiento de plazos contractuales
        """)
    
    with tab2:
        st.subheader("Perspectiva de Impacto Social")
        
        # Análisis por organismo
        org_metas = {}
        for acuerdo in acuerdos_filtrados:
            org = acuerdo.get('organismo_nombre', 'Sin especificar')
            if org not in org_metas:
                org_metas[org] = {'total_metas': 0, 'cumplidas': 0}
            
            for ficha in acuerdo.get('fichas', []):
                metas = ficha.get('metas', [])
                org_metas[org]['total_metas'] += len(metas)
                
                for meta in metas:
                    if 'cumplid' in meta.get('estado', '').lower():
                        org_metas[org]['cumplidas'] += 1
        
        if org_metas:
            data_impacto = []
            for org, stats in org_metas.items():
                tasa = (stats['cumplidas'] / stats['total_metas'] * 100) if stats['total_metas'] > 0 else 0
                data_impacto.append({
                    'Organismo': org,
                    'Metas Totales': stats['total_metas'],
                    'Metas Cumplidas': stats['cumplidas'],
                    'Tasa %': round(tasa, 1)
                })
            
            import pandas as pd
            df_impacto = pd.DataFrame(data_impacto)
            st.dataframe(df_impacto.sort_values('Tasa %', ascending=False), use_container_width=True)
    
    with tab3:
        st.subheader("Perspectiva de Procesos Internos")
        
        col_proc1, col_proc2 = st.columns(2)
        
        with col_proc1:
            # Contar fichas con metas
            fichas_con_metas = 0
            total_fichas = 0
            
            for acuerdo in acuerdos_filtrados:
                fichas = acuerdo.get('fichas', [])
                total_fichas += len(fichas)
                for ficha in fichas:
                    if ficha.get('metas'):
                        fichas_con_metas += 1
            
            tasa_fichas = (fichas_con_metas / total_fichas * 100) if total_fichas > 0 else 0
            st.metric("📋 Fichas con Metas", f"{tasa_fichas:.1f}%", f"{fichas_con_metas}/{total_fichas}")
        
        with col_proc2:
            # Metas con indicadores
            metas_con_indicadores = 0
            total_metas = 0
            
            for acuerdo in acuerdos_filtrados:
                for ficha in acuerdo.get('fichas', []):
                    for meta in ficha.get('metas', []):
                        total_metas += 1
                        if meta.get('indicadores'):
                            metas_con_indicadores += 1
            
            tasa_indicadores = (metas_con_indicadores / total_metas * 100) if total_metas > 0 else 0
            st.metric("📊 Metas con Indicadores", f"{tasa_indicadores:.1f}%", f"{metas_con_indicadores}/{total_metas}")
    
    with tab4:
        st.subheader("Perspectiva de Aprendizaje y Crecimiento")
        
        # Evolución por año
        evolucion_años = {}
        for acuerdo in acuerdos_filtrados:
            año = acuerdo.get('año')
            if año not in evolucion_años:
                evolucion_años[año] = {'acuerdos': 0, 'fichas': 0, 'metas': 0}
            
            evolucion_años[año]['acuerdos'] += 1
            evolucion_años[año]['fichas'] += len(acuerdo.get('fichas', []))
            
            for ficha in acuerdo.get('fichas', []):
                evolucion_años[año]['metas'] += len(ficha.get('metas', []))
        
        if evolucion_años:
            data_evolucion = []
            for año, stats in sorted(evolucion_años.items()):
                data_evolucion.append({
                    'Año': año,
                    'Acuerdos': stats['acuerdos'],
                    'Fichas': stats['fichas'],
                    'Metas': stats['metas']
                })
            
            import pandas as pd
            df_evolucion = pd.DataFrame(data_evolucion)
            st.dataframe(df_evolucion, use_container_width=True)
            
            st.markdown("**Tendencia de Crecimiento:**")
            if len(data_evolucion) > 1:
                crecimiento = data_evolucion[-1]['Metas'] - data_evolucion[0]['Metas']
                st.write(f"Las metas han {'aumentado' if crecimiento > 0 else 'disminuido'} en {abs(crecimiento)} desde {data_evolucion[0]['Año']}")
    
    # 5. TABLA RESUMEN DE ACUERDOS
    st.header("📋 Resumen de Acuerdos Analizados")
    
    datos_resumen = []
    for acuerdo in acuerdos_filtrados[:20]:  # Limitar a 20 para rendimiento
        # Contar fichas y metas
        total_fichas = len(acuerdo.get('fichas', []))
        total_metas = 0
        for ficha in acuerdo.get('fichas', []):
            total_metas += len(ficha.get('metas', []))
        
        datos_resumen.append({
            'ID': acuerdo.get('id', ''),
            'Organismo': acuerdo.get('organismo_nombre', ''),
            'Año': acuerdo.get('año', ''),
            'Tipo': acuerdo.get('tipo_compromiso', ''),
            'Fichas': total_fichas,
            'Metas': total_metas,
            'Vigencia': acuerdo.get('vigencia_hasta', '')
        })
    
    if datos_resumen:
        import pandas as pd
        df_resumen = pd.DataFrame(datos_resumen)
        st.dataframe(df_resumen, use_container_width=True, height=300)
    
    # 6. BOTONES DE ACCIÓN CORREGIDOS
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        # Botón exportar CSV
        if st.button("📥 Exportar Resumen CSV", use_container_width=True, key="export_csv_bsc"):
            if 'df_resumen' in locals():
                try:
                    csv = df_resumen.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="⬇️ Descargar CSV",
                        data=csv,
                        file_name=f"bsc_resumen_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        key="download_csv_bsc"
                    )
                except Exception as e:
                    st.error(f"Error al exportar CSV: {e}")
            else:
                st.warning("No hay datos para exportar")
    
    with col_btn2:
        # Botón actualizar datos
        if st.button("🔄 Actualizar Datos", use_container_width=True, key="refresh_bsc"):
            # Limpiar cache y recargar
            if 'acuerdos_db' in st.session_state:
                del st.session_state['acuerdos_db']
            st.rerun()
    
    with col_btn3:
        # SOLO instrucciones - NADA MÁS
        st.write("---")
        st.markdown("**🏠 Para volver al Inicio:**")
        st.markdown("Usa el menú lateral 👈")
        st.write("---")
    
    # 7. BOTÓN IMPRIMIR/EXPORTAR HTML
    st.markdown("---")
    col_print1, col_print2 = st.columns(2)
    
    with col_print1:
        if st.button("🖨️ Generar Reporte HTML", use_container_width=True, key="print_html"):
            html_content = generar_reporte_bsc_html(acuerdos_filtrados, organismos_unicos, 
                                                   total_metas, tasa_cumplimiento, activos, 
                                                   total_fichas, dias_prom)
            st.download_button(
                label="⬇️ Descargar Reporte HTML",
                data=html_content.encode('utf-8'),
                file_name=f"reporte_bsc_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                key="download_html_bsc"
            )
    
    with col_print2:
        if st.button("📊 Vista para Impresión", use_container_width=True, key="print_view"):
            # Mostrar versión simplificada para imprimir
            mostrar_version_impresion(acuerdos_filtrados, organismos_unicos, 
                                     total_metas, tasa_cumplimiento, activos)
    
    # 8. RESUMEN EJECUTIVO
    with st.expander("📄 Resumen Ejecutivo", expanded=False):
        hoy_str = datetime.now().strftime('%d/%m/%Y')
        
        st.markdown(f"""
        ### 📊 Resumen Ejecutivo BSC
        
        **Fecha de análisis:** {hoy_str}
        **Total acuerdos analizados:** {len(acuerdos_filtrados)}
        **Organismos involucrados:** {len(organismos_unicos)}
        
        **Hallazgos Principales:**
        
        1. **Cobertura Institucional:** {len(organismos_unicos)} organismos tienen acuerdos activos
        2. **Profundidad de Compromisos:** {total_metas} metas distribuidas en {total_fichas} fichas
        3. **Cumplimiento:** {tasa_cumplimiento:.1f}% de metas reportadas como cumplidas
        4. **Vigencia:** {activos} acuerdos activos de {len(acuerdos_filtrados)} totales
        
        **Recomendaciones Estratégicas:**
        
        • **Fortalecer monitoreo** de metas en proceso
        • **Documentar lecciones aprendidas** por organismo
        • **Planificar renovaciones** considerando vencimientos
        • **Establecer indicadores** para medir impacto real
        
        **Próximos pasos sugeridos:**
        
        1. Revisión trimestral de avance de metas
        2. Análisis comparativo entre organismos
        3. Identificación de mejores prácticas
        4. Actualización de sistema de seguimiento
        """)
    
    st.markdown("---")
    st.caption("⚖️ Sistema de Control de Gestión - Balanced Scorecard | Versión adaptada a estructura CG")

def generar_bsc_organismo_simple(organismo_id, db):
    """Genera BSC simple para tu estructura"""
     
    # Buscar acuerdos del organismo
    acuerdos_del_organismo = []
    todas_metas = []
    
    for acuerdo in db.get('acuerdos', []):
        # Verificar si es del organismo (AC_FITE_0001_2025 → FITE)
        acuerdo_id = acuerdo.get('id', '')
        if '_' in acuerdo_id:
            partes = acuerdo_id.split('_')
            if len(partes) >= 2 and partes[1] == organismo_id:
                
                # Procesar fichas y metas
                fichas = acuerdo.get('fichas', [])
                metas_acuerdo = []
                
                for ficha in fichas:
                    metas = ficha.get('metas', [])
                    for meta in metas:
                        meta_info = {
                            'estado': meta.get('estado', 'No Iniciada'),
                            'ponderacion': float(meta.get('ponderacion', 0)),
                            'cumplimiento_calc': meta.get('cumplimiento_calc')
                        }
                        metas_acuerdo.append(meta_info)
                        todas_metas.append(meta_info)
                
                acuerdos_del_organismo.append({
                    'id': acuerdo_id,
                    'año': acuerdo.get('año', datetime.now().year),
                    'total_metas': len(metas_acuerdo)
                })
    
    if not acuerdos_del_organismo:
        return {"error": f"No hay acuerdos para {organismo_id}"}
    
    # 🎯 CALCULAR ESTADÍSTICAS
    total_metas = len(todas_metas)
    metas_cumplidas = sum(1 for m in todas_metas if 'cumplid' in m.get('estado', '').lower())
    metas_en_proceso = sum(1 for m in todas_metas if 'proceso' in m.get('estado', '').lower())
    ponderacion_promedio = sum(m.get('ponderacion', 0) for m in todas_metas) / total_metas if total_metas > 0 else 0
    
    # 🎯 CALCULAR SCORE (0-100)
    if total_metas > 0:
        tasa_cumplimiento = (metas_cumplidas / total_metas) * 100
        score = min(100, tasa_cumplimiento * 0.6 + ponderacion_promedio * 0.4)
    else:
        tasa_cumplimiento = 0
        score = 0
    
    # 🎯 DETERMINAR NIVEL
    if score >= 80:
        nivel = "🟢 EXCELENTE"
    elif score >= 60:
        nivel = "🟡 BUENO"
    elif score >= 40:
        nivel = "🟠 ACEPTABLE"
    else:
        nivel = "🔴 CRÍTICO"
    
    # 🎯 CONSTRUIR BSC
    org_nombre = next(
        (a.get('organismo_nombre', organismo_id) 
         for a in db.get('acuerdos', []) 
         if '_' in a.get('id', '') and a.get('id', '').split('_')[1] == organismo_id),
        organismo_id
    )
    
    return {
        'metadata': {
            'organismo_id': organismo_id,
            'nombre_organismo': org_nombre,
            'fecha_generacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'periodo_analizado': '2025',
            'archivo_fuente': 'agreements.json'
        },
        'resumen_ejecutivo': {
            'score_estrategico': round(score, 1),
            'nivel_rendimiento': nivel,
            'tendencia_general': 'INICIAL',
            'total_metas': total_metas,
            'metas_cumplidas': metas_cumplidas,
            'tasa_cumplimiento': round(tasa_cumplimiento, 1)
        },
        'perspectivas': {
            'financiera': {
                'nombre': 'Gestión de Recursos',
                'objetivo': 'Optimizar uso de recursos',
                'kpis': [
                    {
                        'nombre': 'Ponderación Promedio',
                        'valor': f"{ponderacion_promedio:.1f}%",
                        'meta': '100%',
                        'estado': '🟢' if ponderacion_promedio >= 80 else '🟡' if ponderacion_promedio >= 50 else '🔴'
                    }
                ]
            },
            'impacto': {
                'nombre': 'Resultados',
                'objetivo': 'Lograr objetivos estratégicos',
                'kpis': [
                    {
                        'nombre': 'Tasa Cumplimiento',
                        'valor': f"{tasa_cumplimiento:.1f}%",
                        'meta': '≥80%',
                        'estado': '🟢' if tasa_cumplimiento >= 80 else '🟡' if tasa_cumplimiento >= 60 else '🔴'
                    }
                ]
            },
            'procesos': {
                'nombre': 'Procesos',
                'objetivo': 'Eficiencia operativa',
                'kpis': [
                    {
                        'nombre': 'Metas en Proceso',
                        'valor': f"{metas_en_proceso}",
                        'meta': 'Máximo',
                        'estado': '🟢' if metas_en_proceso > 0 else '🔴'
                    }
                ]
            },
            'aprendizaje': {
                'nombre': 'Aprendizaje',
                'objetivo': 'Mejora continua',
                'kpis': [
                    {
                        'nombre': 'Acuerdos Activos',
                        'valor': f"{len(acuerdos_del_organismo)}",
                        'meta': '≥1',
                        'estado': '🟢'
                    }
                ]
            }
        },
        'recomendaciones': [
            {
                'prioridad': 'ALTA' if total_metas == 0 else 'MEDIA',
                'area': 'Gestión Inicial',
                'accion': f'{"Definir metas" if total_metas == 0 else f"Revisar {total_metas} metas"}',
                'responsable': 'Coordinador CG',
                'plazo': '1 mes'
            }
        ]
    }

def mostrar_resultados_bsc(bsc_data):
    """Muestra los resultados del BSC (adaptada para tu sistema)"""
    import streamlit as st
    
    metadata = bsc_data['metadata']
    resumen = bsc_data['resumen_ejecutivo']
    perspectivas = bsc_data['perspectivas']
    recomendaciones = bsc_data['recomendaciones']
    
    # Header con información de tu sistema
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #2c3e50, #4a6491); padding:25px; border-radius:10px;color:white;margin-bottom:25px;box-shadow:0 4px 6px rgba(0,0,0,0.1)">
        <h1 style="margin:0">🏛️ {metadata['nombre_organismo']}</h1>
        <h3 style="margin:0;font-weight:300">Balanced Scorecard Organizacional</h3>
        <div style="margin-top:15px; display:flex; justify-content:space-between; font-size:14px;">
            <div>
                <strong>📅 Período analizado:</strong> {metadata['periodo_analizado']}<br>
                <strong>📂 Fuente:</strong> {metadata.get('archivo_fuente', 'agreements.json')}
            </div>
            <div style="text-align:right">
                <strong>🕒 Generado:</strong> {metadata['fecha_generacion']}<br>
                <strong>🎯 ID Organismo:</strong> {metadata['organismo_id']}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 🎯 SCORECARD PRINCIPAL
    st.subheader("📊 PUNTUACIÓN ESTRATÉGICA")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="SCORE GLOBAL",
            value=f"{resumen['score_estrategico']}/100",
            delta=resumen['nivel_rendimiento'],
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="CUMPLIMIENTO",
            value=f"{resumen['tasa_cumplimiento']}%",
            delta=resumen['tendencia_general']
        )
    
    with col3:
        st.metric(
            label="METAS TOTALES",
            value=f"{resumen['total_metas']}",
            delta=f"{resumen['metas_cumplidas']} cumplidas"
        )
    
    with col4:
        # Mostrar años analizados
        años = bsc_data['datos_fuente'].get('años_analizados', [])
        st.metric(
            label="AÑOS ANALIZADOS",
            value=f"{len(años)}",
            delta=f"{min(años)}-{max(años)}" if años else "N/A"
        )
    
    # 🎯 PERSPECTIVAS ESTRATÉGICAS
    st.markdown("---")
    st.subheader("📈 PERSPECTIVAS ESTRATÉGICAS")
    
    cols = st.columns(4)
    colores = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
    emojis = ['💰', '🎯', '⚙️', '🧠']
    
    for idx, (key, pers) in enumerate(perspectivas.items()):
        with cols[idx]:
            color = colores[idx]
            emoji = emojis[idx]
            
            st.markdown(f"""
            <div style="background-color:{color}15;padding:15px;border-radius:8px;border-left:4px solid {color};margin-bottom:15px">
                <h4 style="margin:0;color:{color}">{emoji} {pers['nombre']}</h4>
                <p style="font-size:12px;margin:5px 0;color:#666"><em>{pers['objetivo']}</em></p>
            </div>
            """, unsafe_allow_html=True)
            
            for kpi in pers.get('kpis', []):
                st.markdown(f"""
                <div style="background-color:#f8f9fa;padding:10px;margin:8px 0;border-radius:5px;border-left:3px solid {color}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <strong style="font-size:13px">{kpi['nombre']}</strong><br>
                            <span style="font-size:18px;font-weight:bold">{kpi['valor']}</span>
                        </div>
                        <div style="font-size:24px">{kpi['estado']}</div>
                    </div>
                    <div style="font-size:11px;color:#666;margin-top:3px">
                        Meta: {kpi['meta']}
                        {f'<br>{kpi["interpretacion"]}' if kpi.get('interpretacion') else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # 🎯 RECOMENDACIONES
    st.markdown("---")
    st.subheader("🚀 RECOMENDACIONES PRIORITARIAS")
    
    for rec in recomendaciones:
        color_map = {'ALTA': '#e74c3c', 'MEDIA': '#f39c12', 'BAJA': '#3498db'}
        color = color_map.get(rec['prioridad'], '#95a5a6')
        
        st.markdown(f"""
        <div style="border-left:5px solid {color};padding:15px;margin:12px 0;background-color:#f8f9fa;border-radius:4px">
            <div style="display:flex;justify-content:space-between;align-items:start">
                <div>
                    <strong style="color:{color};font-size:14px">[{rec['prioridad']}] {rec['area']}</strong><br>
                    <div style="margin:5px 0">{rec['accion']}</div>
                </div>
                <div style="text-align:right;min-width:150px">
                    <div style="font-size:12px;color:#666">
                        <strong>👤 Responsable:</strong><br>
                        {rec['responsable']}
                    </div>
                    <div style="font-size:12px;color:#666;margin-top:3px">
                        <strong>📅 Plazo:</strong><br>
                        {rec['plazo']}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 🎯 BOTÓN DE EXPORTACIÓN
    st.markdown("---")
    col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
    
    with col_exp1:
        st.info(f"**Resumen:** {metadata['nombre_organismo']} tiene un score de {resumen['score_estrategico']}/100")
    
    with col_exp2:
        if st.button("📥 Exportar HTML", use_container_width=True):
            html_content = generar_html_bsc_simple(bsc_data)
            st.download_button(
                label="Descargar Reporte",
                data=html_content,
                file_name=f"BSC_{metadata['organismo_id']}_{metadata['fecha_generacion'][:10].replace('/', '-')}.html",
                mime="text/html",
                use_container_width=True
            )
    
    with col_exp3:
        if st.button("🔄 Nuevo análisis", use_container_width=True):
            if 'bsc_resultados' in st.session_state:
                del st.session_state['bsc_resultados']
            st.rerun()

def generar_html_bsc_simple(bsc_data):
    """Genera HTML básico para exportar el BSC"""
    metadata = bsc_data['metadata']
    resumen = bsc_data['resumen_ejecutivo']
    perspectivas = bsc_data['perspectivas']
    recomendaciones = bsc_data['recomendaciones']
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>BSC - {metadata['nombre_organismo']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 10px; }}
            .score {{ font-size: 36px; font-weight: bold; text-align: center; margin: 20px; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
            .perspectiva {{ margin: 20px 0; padding: 15px; border-radius: 5px; }}
            .financiera {{ background: #3498db20; border-left: 4px solid #3498db; }}
            .impacto {{ background: #2ecc7120; border-left: 4px solid #2ecc71; }}
            .procesos {{ background: #e74c3c20; border-left: 4px solid #e74c3c; }}
            .aprendizaje {{ background: #f39c1220; border-left: 4px solid #f39c12; }}
            .kpi {{ margin: 10px 0; padding: 10px; background: white; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .recomendacion {{ margin: 10px 0; padding: 15px; border-left: 4px solid; border-radius: 5px; }}
            .alta {{ border-left-color: #e74c3c; background: #e74c3c10; }}
            .media {{ border-left-color: #f39c12; background: #f39c1210; }}
            .baja {{ border-left-color: #3498db; background: #3498db10; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏛️ Balanced Scorecard</h1>
            <h2>{metadata['nombre_organismo']}</h2>
            <p>Período: {metadata['periodo_analizado']} | Generado: {metadata['fecha_generacion']} | Fuente: {metadata.get('archivo_fuente', 'agreements.json')}</p>
        </div>
        
        <div class="score">
            SCORE ESTRATÉGICO: {resumen['score_estrategico']}/100<br>
            <small style="font-size: 20px;">{resumen['nivel_rendimiento']}</small>
        </div>
        
        <div style="display: flex; gap: 20px; margin: 20px 0;">
            <div style="flex: 1; background: #f8f9fa; padding: 15px; border-radius: 5px;">
                <h3>📊 Resumen</h3>
                <p><strong>Tasa cumplimiento:</strong> {resumen['tasa_cumplimiento']}%</p>
                <p><strong>Tendencia:</strong> {resumen['tendencia_general']}</p>
                <p><strong>Metas totales:</strong> {resumen['total_metas']}</p>
                <p><strong>Metas cumplidas:</strong> {resumen['metas_cumplidas']}</p>
            </div>
        </div>
        
        <h2>📈 Perspectivas Estratégicas</h2>
        """
    
    # Agregar perspectivas
    perspectivas_html = ""
    for key, pers in perspectivas.items():
        emoji = {'financiera': '💰', 'impacto': '🎯', 'procesos': '⚙️', 'aprendizaje': '🧠'}.get(key, '📊')
        clase = {'financiera': 'financiera', 'impacto': 'impacto', 'procesos': 'procesos', 'aprendizaje': 'aprendizaje'}.get(key, '')
        
        kpis_html = ""
        for kpi in pers.get('kpis', []):
            kpis_html += f"""
            <div class="kpi">
                <strong>{kpi['nombre']}</strong><br>
                <span style="font-size: 18px; font-weight: bold;">{kpi['valor']}</span> {kpi['estado']}<br>
                <small>Meta: {kpi['meta']}</small>
                {f'<br><small style="color: #666;">{kpi.get("interpretacion", "")}</small>' if kpi.get('interpretacion') else ''}
            </div>
            """
        
        perspectivas_html += f"""
        <div class="perspectiva {clase}">
            <h3>{emoji} {pers['nombre']}</h3>
            <p><em>{pers['objetivo']}</em></p>
            {kpis_html}
        </div>
        """
    
    html += perspectivas_html
    
    # Agregar recomendaciones
    html += """
        <h2>🚀 Recomendaciones Prioritarias</h2>
    """
    
    for rec in recomendaciones:
        clase = {'ALTA': 'alta', 'MEDIA': 'media', 'BAJA': 'baja'}.get(rec['prioridad'], '')
        html += f"""
        <div class="recomendacion {clase}">
            <strong>[{rec['prioridad']}] {rec['area']}</strong><br>
            {rec['accion']}<br>
            <small><strong>Responsable:</strong> {rec['responsable']} | <strong>Plazo:</strong> {rec['plazo']}</small>
        </div>
        """
    
    # Pie de página
    html += f"""
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
            <p><em>Generado por Sistema de Control de Gestión - Balanced Scorecard</em></p>
            <p><small>Basado en datos de {metadata['periodo_analizado']} | Archivo fuente: {metadata.get('archivo_fuente', 'agreements.json')}</small></p>
        </div>
    </body>
    </html>
    """
    
    return html

def generar_reporte_bsc_html(acuerdos, organismos, total_metas, tasa_cumplimiento, 
                           activos, total_fichas, dias_promedio):
    """Genera un reporte HTML imprimible del BSC"""
    
       
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reporte BSC - Sistema CG</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 10px; text-align: center; }}
            .metric {{ background: #f8f9fa; padding: 15px; margin: 10px; border-radius: 5px; border-left: 4px solid #3498db; }}
            .perspectiva {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f2f2f2; }}
            .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; }}
            @media print {{
                .no-print {{ display: none; }}
                body {{ margin: 0; padding: 10px; }}
                .header {{ background: #2c3e50 !important; -webkit-print-color-adjust: exact; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Balanced Scorecard (BSC)</h1>
            <h2>Sistema de Control de Gestión</h2>
            <p>Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p>Total acuerdos analizados: {len(acuerdos)}</p>
        </div>
        
        <h2>📈 Métricas Principales</h2>
        <div style="display: flex; flex-wrap: wrap;">
            <div class="metric" style="flex: 1; min-width: 200px;">
                <h3>🎯 Cumplimiento</h3>
                <p style="font-size: 24px; font-weight: bold;">{tasa_cumplimiento:.1f}%</p>
                <p>de {total_metas} metas totales</p>
            </div>
            <div class="metric" style="flex: 1; min-width: 200px;">
                <h3>📅 Acuerdos Activos</h3>
                <p style="font-size: 24px; font-weight: bold;">{activos}</p>
                <p>de {len(acuerdos)} totales</p>
            </div>
            <div class="metric" style="flex: 1; min-width: 200px;">
                <h3>📁 Estructura</h3>
                <p style="font-size: 24px; font-weight: bold;">{total_fichas} fichas</p>
                <p>{total_metas} metas</p>
            </div>
            <div class="metric" style="flex: 1; min-width: 200px;">
                <h3>⏳ Vigencia</h3>
                <p style="font-size: 24px; font-weight: bold;">{dias_promedio:.0f} días</p>
                <p>promedio restantes</p>
            </div>
        </div>
        
        <h2>🏛️ Organismos Analizados</h2>
        <ul>
    """
    
    # Listar organismos
    for org in organismos:
        html += f"<li>{org}</li>"
    
    html += """
        </ul>
        
        <h2>📋 Resumen de Acuerdos</h2>
        <table>
            <thead>
                <tr>
                    <th>ID Acuerdo</th>
                    <th>Organismo</th>
                    <th>Año</th>
                    <th>Fichas</th>
                    <th>Metas</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Agregar primeros 10 acuerdos
    for acuerdo in acuerdos[:10]:
        total_fichas_ac = len(acuerdo.get('fichas', []))
        total_metas_ac = sum(len(ficha.get('metas', [])) for ficha in acuerdo.get('fichas', []))
        
        html += f"""
                <tr>
                    <td>{acuerdo.get('id', '')}</td>
                    <td>{acuerdo.get('organismo_nombre', '')}</td>
                    <td>{acuerdo.get('año', '')}</td>
                    <td>{total_fichas_ac}</td>
                    <td>{total_metas_ac}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <div class="perspectiva">
            <h3>🎯 Perspectiva Financiera</h3>
            <p>Distribución por tipo de compromiso y eficiencia en uso de recursos.</p>
        </div>
        
        <div class="perspectiva">
            <h3>👥 Perspectiva de Impacto Social</h3>
            <p>Análisis de cumplimiento por organismo y distribución de metas.</p>
        </div>
        
        <div class="perspectiva">
            <h3>🔄 Perspectiva de Procesos</h3>
            <p>Eficiencia operativa y estructura de fichas y metas.</p>
        </div>
        
        <div class="perspectiva">
            <h3>🧠 Perspectiva de Aprendizaje</h3>
            <p>Evolución temporal y crecimiento institucional.</p>
        </div>
        
        <div class="footer">
            <p><em>Reporte generado automáticamente por el Sistema de Control de Gestión</em></p>
            <p><strong>© Sistema CG - Balanced Scorecard</strong></p>
            <p>Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        
        <div class="no-print" style="margin-top: 20px; text-align: center;">
            <button onclick="window.print()" style="padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">
                🖨️ Imprimir Reporte
            </button>
        </div>
    </body>
    </html>
    """
    
    return html

def mostrar_version_impresion(acuerdos, organismos, total_metas, tasa_cumplimiento, activos):
    """Muestra una versión simplificada para imprimir"""
    
    with st.expander("🖨️ VISTA PARA IMPRESIÓN - Click para expandir", expanded=True):
        st.markdown(f"""
        <div style="font-family: Arial, sans-serif;">
            <h1 style="text-align: center;">📊 BALANCED SCORECARD</h1>
            <h2 style="text-align: center;">Sistema de Control de Gestión</h2>
            <hr>
            
            <h3>📈 RESUMEN EJECUTIVO</h3>
            <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y')}</p>
            <p><strong>Total Acuerdos:</strong> {len(acuerdos)}</p>
            <p><strong>Organismos:</strong> {len(organismos)}</p>
            <p><strong>Cumplimiento:</strong> {tasa_cumplimiento:.1f}% de {total_metas} metas</p>
            <p><strong>Acuerdos Activos:</strong> {activos}</p>
            
            <h3>🏛️ ORGANISMOS</h3>
            <ul>
        """, unsafe_allow_html=True)
        
        for org in organismos:
            st.markdown(f"<li>{org}</li>", unsafe_allow_html=True)
        
        st.markdown("""
            </ul>
            
            <h3>📋 ACUERDOS ANALIZADOS</h3>
            <table border="1" style="width:100%; border-collapse:collapse;">
                <tr>
                    <th>ID</th>
                    <th>Organismo</th>
                    <th>Año</th>
                    <th>Estado</th>
                </tr>
        """, unsafe_allow_html=True)
        
        # Mostrar primeros 15 acuerdos
        for acuerdo in acuerdos[:15]:
            st.markdown(f"""
                <tr>
                    <td>{acuerdo.get('id', '')}</td>
                    <td>{acuerdo.get('organismo_nombre', '')}</td>
                    <td>{acuerdo.get('año', '')}</td>
                    <td>{'Activo' if acuerdo.get('vigencia_hasta') else 'No especificado'}</td>
                </tr>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
            </table>
            
            <div style="margin-top: 30px; text-align: center;">
                <p><em>Para imprimir: Ctrl+P o usar el botón de impresión del navegador</em></p>
                <p><strong>Sistema de Control de Gestión - BSC</strong></p>
                <p>Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# FIN DEL CÓDIGO DEL BALANCED SCORECARD
# ============================================================================

def page_analisis_comparativo():
    """Página para análisis comparativo de acuerdos por organismo"""
    require_login()
    header_with_logo()
    st.title("📊 Análisis Comparativo por Organismo")
       
    # Cargar acuerdos
    db = agreements_load()
    if not db:
        st.warning("No hay acuerdos para analizar")
        return
    
    # ==============================================
    # 🆕 SELECCIÓN DE ORGANISMO Y AÑOS
    # ==============================================
    
    st.header("1. Seleccionar Organismo para Análisis")
    
    # Obtener lista de organismos únicos
    organismos = sorted(list({acuerdo.get('organismo_nombre', '') for acuerdo in db.values() if acuerdo.get('organismo_nombre')}))
    
    organismo_seleccionado = st.selectbox(
        "Seleccionar organismo:",
        options=organismos,
        help="Seleccione el organismo para analizar sus acuerdos a través de los años"
    )
    
    if not organismo_seleccionado:
        st.info("Seleccione un organismo para continuar")
        return
    
    # Filtrar acuerdos del organismo seleccionado
    acuerdos_organismo = {k: v for k, v in db.items() if v.get('organismo_nombre') == organismo_seleccionado}
    
    if not acuerdos_organismo:
        st.warning(f"No se encontraron acuerdos para {organismo_seleccionado}")
        return
    
    # Obtener años disponibles
    años = sorted(list({acuerdo.get('año') for acuerdo in acuerdos_organismo.values() if acuerdo.get('año')}))
    
    st.subheader("2. Seleccionar Años para Comparar")
    
    col_años1, col_años2 = st.columns(2)
    
    with col_años1:
        año_inicio = st.selectbox(
            "Año de inicio:",
            options=años,
            index=0,
            help="Año inicial para el análisis"
        )
    
    with col_años2:
        año_fin = st.selectbox(
            "Año final:",
            options=años,
            index=len(años)-1 if años else 0,
            help="Año final para el análisis"
        )
    
    # Filtrar acuerdos por rango de años
    acuerdos_filtrados = {
        k: v for k, v in acuerdos_organismo.items() 
        if año_inicio <= v.get('año', 0) <= año_fin
    }
    
    if not acuerdos_filtrados:
        st.warning(f"No hay acuerdos de {organismo_seleccionado} entre {año_inicio} y {año_fin}")
        return
    
    # ==============================================
    # 🆕 ANÁLISIS COMPARATIVO
    # ==============================================
    
    st.header("3. Análisis Comparativo")
    
    # Métricas principales por año
    st.subheader("📈 Evolución de Métricas Principales")
    
    # Preparar datos para el análisis
    datos_anuales = []
    for acuerdo_id, acuerdo in acuerdos_filtrados.items():
        año = acuerdo.get('año')
        total_fichas = len(acuerdo.get('fichas', []))
        total_metas = sum(len(ficha.get('metas', [])) for ficha in acuerdo.get('fichas', []))
        
        # Calcular cumplimiento promedio
        cumplimientos = []
        for ficha in acuerdo.get('fichas', []):
            for meta in ficha.get('metas', []):
                if meta.get('cumplimiento_calc') is not None:
                    cumplimientos.append(meta['cumplimiento_calc'])
        
        cumplimiento_promedio = sum(cumplimientos) / len(cumplimientos) if cumplimientos else 0
        
        datos_anuales.append({
            'año': año,
            'acuerdo_id': acuerdo_id,
            'total_fichas': total_fichas,
            'total_metas': total_metas,
            'cumplimiento_promedio': cumplimiento_promedio,
            'estado': acuerdo.get('estado', 'N/D')
        })
    
    # Ordenar por año
    datos_anuales.sort(key=lambda x: x['año'])
    
    # Mostrar métricas en columnas
    # Inicializar variables para evitar UnboundLocalError cuando hay pocos años
    crecimiento_metas = 0.0
    crecimiento_fichas = 0.0
    crecimiento_cumplimiento = 0.0
    años_analizados = len(datos_anuales)

    if len(datos_anuales) >= 2:
        col_met1, col_met2, col_met3, col_met4 = st.columns(4)
        
        with col_met1:
            crecimiento_fichas = ((datos_anuales[-1]['total_fichas'] - datos_anuales[0]['total_fichas']) / datos_anuales[0]['total_fichas'] * 100) if datos_anuales[0]['total_fichas'] > 0 else 0
            st.metric(
                "Fichas", 
                f"{datos_anuales[-1]['total_fichas']}",
                f"{crecimiento_fichas:+.1f}%"
            )
        
        with col_met2:
            crecimiento_metas = ((datos_anuales[-1]['total_metas'] - datos_anuales[0]['total_metas']) / datos_anuales[0]['total_metas'] * 100) if datos_anuales[0]['total_metas'] > 0 else 0
            st.metric(
                "Metas", 
                f"{datos_anuales[-1]['total_metas']}",
                f"{crecimiento_metas:+.1f}%"
            )
        
        with col_met3:
            crecimiento_cumplimiento = datos_anuales[-1]['cumplimiento_promedio'] - datos_anuales[0]['cumplimiento_promedio']
            st.metric(
                "Cumplimiento Promedio", 
                f"{datos_anuales[-1]['cumplimiento_promedio']:.1f}%",
                f"{crecimiento_cumplimiento:+.1f}%"
            )
        
        with col_met4:
            años_analizados = len(datos_anuales)
            st.metric("Años Analizados", años_analizados)
    
    # ==============================================
    # 🆕 GRÁFICOS DE TENDENCIAS
    # ==============================================
    
    st.subheader("📊 Tendencias por Año")
    
    # Preparar datos para gráficos
    años = [d['año'] for d in datos_anuales]
    fichas = [d['total_fichas'] for d in datos_anuales]
    metas = [d['total_metas'] for d in datos_anuales]
    cumplimientos = [d['cumplimiento_promedio'] for d in datos_anuales]
    
    # Crear DataFrame para gráficos
    import pandas as pd
    df_tendencias = pd.DataFrame(datos_anuales)
    
    # Gráfico de tendencias
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.markdown("**Evolución de Cantidad**")
        chart_data = pd.DataFrame({
            'Año': años,
            'Fichas': fichas,
            'Metas': metas
        }).set_index('Año')
        st.line_chart(chart_data)
    
    with col_graf2:
        st.markdown("**Evolución de Cumplimiento**")
        chart_cumplimiento = pd.DataFrame({
            'Año': años,
            'Cumplimiento (%)': cumplimientos
        }).set_index('Año')
        st.line_chart(chart_cumplimiento)
    
    # ==============================================
    # 🆕 ANÁLISIS DE OPORTUNIDADES
    # ==============================================
    
    st.header("4. Oportunidades de Mejora")
    
    # Análisis de áreas de oportunidad
    oportunidades = []
    
    # 1. Análisis de cumplimiento
    if len(cumplimientos) >= 2:
        if cumplimientos[-1] < cumplimientos[0]:
            oportunidades.append({
                'tipo': '⚠️ Atención',
                'mensaje': f'El cumplimiento promedio disminuyó de {cumplimientos[0]:.1f}% a {cumplimientos[-1]:.1f}%',
                'recomendacion': 'Revisar metas con bajo cumplimiento y ajustar estrategias'
            })
        elif cumplimientos[-1] > 85:
            oportunidades.append({
                'tipo': '✅ Fortaleza',
                'mensaje': f'Alto nivel de cumplimiento: {cumplimientos[-1]:.1f}%',
                'recomendacion': 'Mantener estrategias exitosas y considerar aumentar la ambición de metas'
            })
    
    # 2. Análisis de complejidad
    if len(metas) >= 2:
        crecimiento_metas_por_año = (metas[-1] - metas[0]) / (años[-1] - años[0]) if años[-1] != años[0] else 0
        if crecimiento_metas_por_año > 5:
            oportunidades.append({
                'tipo': '📈 Crecimiento',
                'mensaje': f'Crecimiento significativo en número de metas: {crecimiento_metas_por_año:.1f} metas/año',
                'recomendacion': 'Evaluar si el aumento en complejidad es sostenible'
            })
    
    # 3. Análisis de tipos de compromiso
    tipos_compromiso = {}
    for acuerdo in acuerdos_filtrados.values():
        tipo = acuerdo.get('tipo_compromiso', 'No especificado')
        tipos_compromiso[tipo] = tipos_compromiso.get(tipo, 0) + 1
    
    if len(tipos_compromiso) == 1:
        tipo_principal = list(tipos_compromiso.keys())[0]
        oportunidades.append({
            'tipo': '🔄 Diversificación',
            'mensaje': f'Solo se utiliza el tipo de compromiso: {tipo_principal}',
            'recomendacion': 'Considerar diversificar tipos de compromiso según necesidades'
        })
    
    # Mostrar oportunidades
    if oportunidades:
        for op in oportunidades:
            with st.expander(f"{op['tipo']} - {op['mensaje']}", expanded=True):
                st.info(f"**Recomendación:** {op['recomendacion']}")
    else:
        st.success("✅ No se identificaron áreas críticas de mejora")
    
    # ==============================================
    # 🆕 COMPARACIÓN DETALLADA POR AÑO
    # ==============================================
    
    st.header("5. Comparación Detallada por Año")
    
    # Crear tabla comparativa
    st.subheader("📋 Resumen por Año")
    
    datos_tabla = []
    for dato in datos_anuales:
        acuerdo = acuerdos_filtrados[dato['acuerdo_id']]
        datos_tabla.append({
            'Año': dato['año'],
            'Acuerdo': dato['acuerdo_id'],
            'Fichas': dato['total_fichas'],
            'Metas': dato['total_metas'],
            'Cumplimiento (%)': f"{dato['cumplimiento_promedio']:.1f}%",
            'Estado': dato['estado'],
            'Tipo': acuerdo.get('tipo_compromiso', 'N/D')
        })
    
    st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True)
    
    # ==============================================
    # 🆕 EXPORTACIÓN DE REPORTE
    # ==============================================
    
    st.header("6. Exportar Análisis")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        # Exportar a CSV
        csv_data = pd.DataFrame(datos_tabla).to_csv(index=False).encode('utf-8')
        st.download_button(
            "📊 Descargar CSV",
            data=csv_data,
            file_name=f"analisis_{organismo_seleccionado}_{año_inicio}_{año_fin}.csv",
            mime="text/csv"
        )
    
    with col_exp2:
        # Generar reporte HTML
        # Asegurar valor seguro para crecimiento_metas en caso de que no esté asociado
        try:
            safe_crecimiento_metas = float(crecimiento_metas)
        except Exception:
            safe_crecimiento_metas = 0.0

        html_content = f"""
        <html>
        <head>
            <title>Análisis Comparativo - {organismo_seleccionado}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f2f6; padding: 20px; border-radius: 10px; }}
                .metric {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }}
                .oportunidad {{ background: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #ffc107; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Análisis Comparativo</h1>
                <h2>Organismo: {organismo_seleccionado}</h2>
                <p>Período: {año_inicio} - {año_fin}</p>
            </div>
            
            <h3>Resumen Ejecutivo</h3>
            <div class="metric">
                <strong>Años analizados:</strong> {len(datos_anuales)}<br>
                <strong>Crecimiento de metas:</strong> {safe_crecimiento_metas:+.1f}%<br>
                <strong>Cumplimiento actual:</strong> {datos_anuales[-1]['cumplimiento_promedio']:.1f}%
            </div>
            
            <h3>Oportunidades Identificadas</h3>
        """
        
        for op in oportunidades:
            html_content += f"""
            <div class="oportunidad">
                <strong>{op['tipo']}</strong><br>
                {op['mensaje']}<br>
                <em>{op['recomendacion']}</em>
            </div>
            """
        
        html_content += "</body></html>"
        
        st.download_button(
            "📄 Descargar Reporte HTML",
            data=html_content.encode('utf-8'),
            file_name=f"reporte_analisis_{organismo_seleccionado}.html",
            mime="text/html"
        )

    st.markdown("---")
    st.info("💡 **Sugerencia:** Use esta herramienta periódicamente para monitorear la evolución de los acuerdos y identificar patrones de mejora.")

def page_analisis_riesgos_tendencias():
    """Página para análisis de riesgos y tendencias avanzado"""
    require_login()
    header_with_logo()
    st.title("🔴 Análisis de Riesgos y Tendencias")
    
    
    
    # Cargar acuerdos
    db = agreements_load()
    if not db:
        st.warning("No hay acuerdos para analizar")
        return
    
    # ==============================================
    # 🆕 SELECTOR DE MODO DE ANÁLISIS
    # ==============================================
    
    st.header("1. Tipo de Análisis")
    
    modo_analisis = st.radio(
        "Seleccionar tipo de análisis:",
        options=["🔴 Análisis de Riesgos", "📈 Análisis de Tendencias", "📊 Dashboard Integrado"],
        horizontal=True
    )
    
    # ==============================================
    # 🆕 ANÁLISIS DE RIESGOS
    # ==============================================
    
    if modo_analisis == "🔴 Análisis de Riesgos":
        st.header("2. Evaluación de Riesgos por Acuerdo")
        
        # Seleccionar acuerdo
        acuerdos_activos = {k: v for k, v in db.items() if v.get('estado') in ['Borrador', 'En Revisión', 'Aprobado']}
        
        if not acuerdos_activos:
            st.warning("No hay acuerdos activos para análisis de riesgos")
            return
        
        acuerdo_seleccionado = st.selectbox(
            "Seleccionar acuerdo para análisis:",
            options=list(acuerdos_activos.keys()),
            format_func=lambda x: f"{x} - {db[x].get('organismo_nombre', '')}",
            help="Seleccione un acuerdo activo para evaluar riesgos"
        )
        
        if acuerdo_seleccionado:
            acuerdo = db[acuerdo_seleccionado]
            
            with st.spinner("🔍 Evaluando riesgos..."):
                # Ejecutar análisis de riesgos
                resultados_riesgo = analizar_riesgos_acuerdo(acuerdo)
                
                # Mostrar resultados
                st.subheader("📋 Resultados del Análisis de Riesgos")
                
                # Métricas rápidas
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1:
                    st.metric("Metas sin ponderación", resultados_riesgo['metas_sin_ponderacion'])
                with col_r2:
                    st.metric("Metas cerca de vencimiento", resultados_riesgo['metas_vencimiento_proximo'])
                with col_r3:
                    st.metric("Metas bajo cumplimiento", resultados_riesgo['metas_bajo_cumplimiento'])
                with col_r4:
                    st.metric("Riesgos identificados", resultados_riesgo['total_riesgos'])
                
                # Matriz de riesgos
                st.subheader("📊 Matriz de Riesgos")
                mostrar_matriz_riesgos_simple(resultados_riesgo['matriz_riesgos'])
                
                # Recomendaciones
                st.subheader("🎯 Recomendaciones Prioritarias")
                for i, rec in enumerate(resultados_riesgo['recomendaciones'][:5], 1):
                    with st.expander(f"Recomendación #{i}: {rec['titulo']}", expanded=i==1):
                        st.write(f"**Descripción:** {rec['descripcion']}")
                        st.write(f"**Prioridad:** {rec['prioridad']}")
                        st.write(f"**Acción sugerida:** {rec['accion']}")
                
                # Exportar reporte
                st.subheader("📄 Exportar Reporte de Riesgos")
                col_exp_r1, col_exp_r2 = st.columns(2)
                with col_exp_r1:
                    if st.button("📋 Generar Reporte HTML", use_container_width=True, key="btn_html_riesgos"):
                        reporte_html = generar_reporte_riesgos_html(resultados_riesgo, acuerdo)
                        st.download_button(
                            "⬇️ Descargar HTML",
                            data=reporte_html.encode('utf-8'),
                            file_name=f"reporte_riesgos_{acuerdo_seleccionado}.html",
                            mime="text/html",
                            key="dl_html_riesgos"
                        )
                
                with col_exp_r2:
                    if st.button("📊 Exportar a CSV", use_container_width=True, key="btn_csv_riesgos"):
                        csv_data = generar_reporte_riesgos_csv(resultados_riesgo)
                        st.download_button(
                            "⬇️ Descargar CSV",
                            data=csv_data.encode('utf-8'),
                            file_name=f"riesgos_{acuerdo_seleccionado}.csv",
                            mime="text/csv",
                            key="dl_csv_riesgos"
                        )
    
    # ==============================================
    # 🆕 ANÁLISIS DE TENDENCIAS
    # ==============================================
    
    elif modo_analisis == "📈 Análisis de Tendencias":
        st.header("2. Análisis de Tendencias por Organismo")
        
        # Seleccionar organismo
        organismos = sorted(list({acuerdo.get('organismo_nombre', '') for acuerdo in db.values() if acuerdo.get('organismo_nombre')}))
        
        organismo_seleccionado = st.selectbox(
            "Seleccionar organismo:",
            options=organismos,
            key="org_tendencias"
        )
        
        if organismo_seleccionado:
            # Filtrar acuerdos del organismo
            acuerdos_organismo = {k: v for k, v in db.items() if v.get('organismo_nombre') == organismo_seleccionado}
            
            # Obtener años
            años = sorted(list({acuerdo.get('año') for acuerdo in acuerdos_organismo.values() if acuerdo.get('año')}))
            
            if len(años) < 2:
                st.warning("Se necesitan al menos 2 años de datos para análisis de tendencias")
                return
            
            # Seleccionar rango de años
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                año_inicio = st.selectbox("Año inicio", options=años, index=0, key="año_ini")
            with col_a2:
                año_fin = st.selectbox("Año fin", options=años, index=len(años)-1, key="año_fin")
            
            if st.button("📈 Analizar Tendencias", type="primary", key="btn_analizar_tendencias"):
                with st.spinner("Analizando tendencias..."):
                    # Ejecutar análisis de tendencias
                    tendencias = analizar_tendencias_organismo(organismo_seleccionado, año_inicio, año_fin, db)
                    
                    # Mostrar resultados
                    st.subheader("📊 Resultados del Análisis de Tendencias")
                    
                    # Métricas de tendencia
                    col_t1, col_t2, col_t3 = st.columns(3)
                    with col_t1:
                        tendencia_cumplimiento = tendencias.get('tendencia_cumplimiento', 'estable')
                        icono = "↗️" if tendencia_cumplimiento == 'positiva' else "↘️" if tendencia_cumplimiento == 'negativa' else "➡️"
                        st.metric("Tendencia Cumplimiento", icono)
                    with col_t2:
                        st.metric("Crecimiento Metas", f"{tendencias.get('crecimiento_metas', 0):+.0f}%")
                    with col_t3:
                        st.metric("Mejora Eficiencia", f"{tendencias.get('mejora_eficiencia', 0):+.1f}%")
                    
                    # Gráficos con Streamlit nativo
                    st.subheader("📈 Gráficos de Tendencias")
                    
                    if tendencias.get('datos_grafico'):
                        # Convertir a formato para Streamlit
                        import pandas as pd
                        df_tendencias = pd.DataFrame(tendencias['datos_grafico'])
                        
                        # Gráfico de líneas nativo de Streamlit
                        st.line_chart(df_tendencias.set_index('Año'))
                        
                        # También mostrar como tabla
                        with st.expander("📋 Ver datos detallados"):
                            st.dataframe(df_tendencias)
                    
                    # Alertas detectadas
                    if tendencias.get('alertas'):
                        st.subheader("🔔 Alertas Detectadas")
                        for alerta in tendencias['alertas']:
                            with st.expander(f"{alerta['tipo']}: {alerta['titulo']}"):
                                st.write(alerta['descripcion'])
                                st.write(f"**Recomendación:** {alerta.get('recomendacion', '')}")
    
    # ==============================================
    # 🆕 DASHBOARD INTEGRADO
    # ==============================================
    
    else:  # Dashboard Integrado
        st.header("2. Dashboard Integrado de Riesgos y Tendencias")
        
        # Métricas globales
        st.subheader("🌍 Vista Global del Sistema")
        
        # Calcular métricas globales
        metricas_globales = calcular_metricas_globales(db)
        
        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        with col_g1:
            st.metric("Acuerdos Activos", metricas_globales['acuerdos_activos'])
        with col_g2:
            st.metric("Riesgos Altos", metricas_globales['riesgos_altos'])
        with col_g3:
            st.metric("Tendencias +", metricas_globales['tendencias_positivas'])
        with col_g4:
            st.metric("Alertas", metricas_globales['alertas_activas'])
        
        # Top 5 organismos con más riesgos
        st.subheader("🔴 Top 5 Organismos con Mayor Riesgo")
        top_riesgos = obtener_top_organismos_riesgo(db)
        
        if top_riesgos:
            for org in top_riesgos[:5]:
                with st.expander(f"{org['organismo']} - {org['puntaje_riesgo']:.1f} pts", expanded=False):
                    st.write(f"**Metas en riesgo:** {org['metas_riesgo']}")
                    st.write(f"**Cumplimiento promedio:** {org['cumplimiento_promedio']:.1f}%")
                    st.write(f"**Recomendación principal:** {org.get('recomendacion', 'N/A')}")
        
        # Tendencias mensuales (simuladas)
        st.subheader("📈 Tendencia Mensual de Cumplimiento")
        
        # Generar datos de tendencia simulados
        datos_mensuales = generar_datos_tendencia_mensual_simple()
        if datos_mensuales is not None and not datos_mensuales.empty:
            # Usar gráfico nativo de Streamlit
            st.line_chart(datos_mensuales.set_index('Mes'))
            
            # Mostrar tabla también
            with st.expander("📋 Ver datos mensuales"):
                st.dataframe(datos_mensuales)
    
    st.markdown("---")
    st.info("💡 **Sugerencia:** Revise este análisis mensualmente para identificar riesgos tempranos y oportunidades de mejora.")

import streamlit as st

def page_tutorial():
    """Tutorial GUIADO - Explica cómo usar tu sistema real"""
    
    # ===== INICIALIZAR ESTADOS DE SESIÓN =====
    if 'imprimir_tutorial' not in st.session_state:
        st.session_state.imprimir_tutorial = False
    if 'tutorial_paso' not in st.session_state:
        st.session_state.tutorial_paso = 0
    
    # ===== VERIFICAR SI SE ACTIVÓ LA IMPRESIÓN =====
    if st.session_state.get('imprimir_tutorial', False):
        mostrar_version_imprimible()
        return  # Salir de la función después de mostrar la versión imprimible
    
    # ===== TUTORIAL INTERACTIVO =====
    st.title("🎓 Tutorial Guiado")
    
    # ===== BOTONES DE ACCIÓN PRINCIPALES (arriba) =====
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🖨️ **Imprimir tutorial**", 
                    use_container_width=True,
                    help="Genera versión completa para imprimir o guardar"):
            st.session_state.imprimir_tutorial = True
            st.rerun()
    
    with col2:
        # Generar y descargar HTML inmediatamente
        html_content = generar_html_tutorial_completo()
        st.download_button(
            label="📥 **Descargar guía**",
            data=html_content,
            file_name=f"tutorial_cg_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True
        )
              
    st.markdown("---")
    
    # Definir pasos del tutorial COMPLETOS
    pasos = [
        {
            "titulo": "🏛️ Introducción al Sistema",
            "contenido": """
            ## Bienvenido al Sistema de Compromisos de Gestión
            
            **🎯 Objetivo:** Aprender a gestionar acuerdos, fichas y metas institucionales.
            
            ### **📁 Estructura del sistema:**
            1. **Acuerdos** → Contratos/compromisos con organismos
            2. **Fichas** → Áreas de trabajo dentro de cada acuerdo  
            3. **Metas** → Objetivos específicos a cumplir
            4. **Indicadores** → Medición del cumplimiento
            
            ### **🔧 Pestañas principales:**
            - **📝 Generar Acuerdos**: Crear y gestionar acuerdos
            - **📈 Dashboard Control**: Ver métricas y cumplimiento
            - **📊 Reportes**: Generar documentación ejecutiva
            
            ### **📚 Lo que verás en este tutorial:**
            - Cómo navegar por el sistema
            - Estructura de un acuerdo completo
            - Proceso paso a paso para crear contenido
            - Consejos y mejores prácticas
            
            ### **👤 Usuarios objetivo:**
            - Equipos técnicos del Organismo XX
            - Gestores y coordinadores
            - Directivos y tomadores de decisiones
            
            ### **⏱️ Tiempo estimado:**
            - Tutorial completo: 15-20 minutos
            - Implementación inicial: 1-2 horas
            - Dominio completo: 1-2 semanas de uso
            """
        },
        {
            "titulo": "📝 Cómo crear un Acuerdo",
            "contenido": """
            ## Paso 1: Crear un nuevo acuerdo
            
            **📍 Ubicación:** Pestaña **"Generar Acuerdos"**
            
            ### **📋 Información básica requerida:**
            1. **Organismo** → Institución con la que se firma (ej: OPP, Ministerio XX)
            2. **Año** → Período de vigencia (ej: 2024, 2025)  
            3. **Tipo de compromiso** → Institucional/Programático
            4. **Objeto** → Descripción detallada del acuerdo
            5. **Fecha de inicio** → Cuando comienza la vigencia
            6. **Fecha de fin** → Cuando finaliza la vigencia
            
            ### **🛠️ Proceso en el sistema real:**
            1. Navega a la pestaña **"Generar Acuerdos"**
            2. Haz clic en el botón **"➕ Crear nuevo acuerdo"**
            3. Completa todos los campos del formulario
            4. Revisa la información ingresada
            5. Haz clic en **"Guardar acuerdo"**
            6. El sistema asignará automáticamente un ID único
            
            ### **📝 Ejemplo de objeto bien redactado:**
            "Desarrollar capacidades tecnológicas en el equipo del Orgsnismo XX mediante programas de capacitación en herramientas digitales y modernización de procesos internos, con el objetivo de mejorar la eficiencia en la gestión de proyectos habitacionales."
            
            ### **💡 Consejo práctico:** 
            Usa nombres claros que incluyan organismo y año.
            **Ejemplo:** `"Mnisterio XX - Acuerdo Institucional 2024"`
            **Ejemplo:** `"OPP - Programa de Modernización 2024"`
            
            ### **⚠️ Errores comunes a evitar:**
            - No completar todos los campos obligatorios
            - Usar objetos demasiado genéricos
            - No asignar fechas realistas
            - Olvidar guardar los cambios
            """
        },
        {
            "titulo": "📋 Cómo agregar Fichas",
            "contenido": """
            ## Paso 2: Diseñar las fichas del acuerdo
            
            **📍 Dónde hacerlo:** Dentro de cada acuerdo creado → Sección **"Fichas"**
            
            ### **🎯 ¿Qué son las fichas?**
            - **Áreas temáticas** específicas del acuerdo
            - Cada ficha agrupa **metas relacionadas**
            - Permiten organizar el trabajo por categorías
            - Facilitan el seguimiento por especialistas
            
            ### **📊 Tipos comunes de fichas:**
            1. **Capacitación** → Formación y desarrollo de habilidades
            2. **Infraestructura** → Mejora de instalaciones y equipos
            3. **Gestión** → Optimización de procesos administrativos
            4. **Transferencia** → Compartir conocimientos y tecnología
            5. **Investigación** → Estudios y análisis especializados
            
            ### **📋 Información de cada ficha:**
            1. **Nombre** → Identificación clara (ej: "Capacitación en herramientas digitales")
            2. **Tipo de meta** → Capacitación/Transferencia/Gestión/Infraestructura/Otro
            3. **Objetivo específico** → Qué se busca lograr con esta ficha
            4. **Indicador principal** → Cómo se medirá el éxito
            5. **Responsables** → Personas o áreas encargadas
            6. **Presupuesto asignado** → Recursos financieros (opcional)
            
            ### **🛠️ En el sistema real:**
            1. Abre el acuerdo existente desde la lista
            2. Busca la sección **"Fichas"** (usualmente en pestañas o acordeón)
            3. Haz clic en **"➕ Agregar ficha"**
            4. Completa todos los campos del formulario
            5. Guarda la ficha
            6. Repite para cada área de trabajo necesaria
            
            ### **💡 Recomendación:**
            Limita a **3-5 fichas por acuerdo** para mantener el enfoque y facilitar el seguimiento.
            
            ### **📈 Ejemplo de ficha bien estructurada:**
            - **Nombre:** Capacitación en herramientas de gestión de proyectos
            - **Tipo:** Capacitación
            - **Objetivo:** Fortalecer las capacidades del equipo en metodologías ágiles
            - **Indicador:** Número de personas certificadas
            - **Responsable:** Departamento de Desarrollo Organizacional
            """
        },
        {
            "titulo": "🎯 Cómo definir Metas",
            "contenido": """
            ## Paso 3: Establecer metas específicas
            
            **📍 Dónde:** Dentro de cada ficha creada → Sección **"Metas"**
            
            ### **📈 Características de una buena meta (principio SMART):**
            - **S** → Específica (clara y sin ambigüedades)
            - **M** → Medible (con valor numérico objetivo)
            - **A** → Alcanzable (realista y posible)
            - **R** → Relevante (alineada con objetivos institucionales)
            - **T** → Temporal (con fecha límite clara)
            
            ### **📋 Datos requeridos por meta:**
            1. **Nombre descriptivo** → Ej: "Capacitar 200 personas en IoT"
            2. **Valor objetivo** → Ej: 200 (el número a alcanzar)
            3. **Unidad de medida** → Ej: personas, talleres, documentos, horas
            4. **Fecha de vencimiento** → Cuándo debe cumplirse (ej: 30/11/2024)
            5. **Ponderación** → Importancia relativa (1-100%)
            6. **Valor base inicial** → Situación al comenzar (ej: 0)
            7. **Fórmula de cálculo** → Cómo se calcula el avance (opcional)
            
            ### **📊 Ejemplo de meta SMART:**
            - **Nombre:** Capacitar al personal en herramientas de análisis de datos
            - **Objetivo:** 150 personas capacitadas
            - **Unidad:** Personas
            - **Vencimiento:** 30 de septiembre de 2024
            - **Ponderación:** 25%
            - **Base inicial:** 0 personas capacitadas
            
            ### **🛠️ En el sistema:**
            1. Abre la ficha donde se agregará la meta
            2. Haz clic en **"➕ Agregar meta"**
            3. Completa el formulario detallado con todos los campos
            4. Define rangos de cumplimiento si aplica (opcional)
            5. Guarda la meta
            6. Repite para cada objetivo específico
            
            ### **⚖️ Ponderación de metas:**
            - La suma de ponderaciones de todas las metas en una ficha debe ser **100%**
            - El sistema ayuda con cálculos automáticos y validaciones
            - Asigna mayor ponderación a metas críticas
            
            ### **💡 Consejo importante:**
            Comienza con metas **realistas y alcanzables**. Es mejor cumplir metas modestas que fallar en metas ambiciosas.
            
            ### **📅 Planificación temporal:**
            - **Metas a corto plazo:** 1-3 meses
            - **Metas a mediano plazo:** 4-6 meses  
            - **Metas a largo plazo:** 7-12 meses
            
            ### **🔄 Metas recurrentes:**
            Para actividades periódicas (ej: reuniones mensuales), puedes crear metas con seguimiento continuo.
            """
        },
        {
            "titulo": "📊 Cómo registrar cumplimiento",
            "contenido": """
            ## Paso 4: Registrar avances y cumplimiento
            
            **📍 Dos formas disponibles:**
            
            ### **Opción A: Por metas (RECOMENDADO para usuarios)**
            **Ubicación:** Menú principal → **"🎯 Carga por Metas"**
            
            **Proceso:**
            1. Selecciona el acuerdo específico
            2. Elige la ficha correspondiente
            3. Selecciona la meta a actualizar
            4. Ingresa el **valor logrado** en el período
            5. El sistema calcula automáticamente:
               - Porcentaje de cumplimiento
               - Estado (Cumplida/En Progreso/Pendiente)
               - Impacto en el cumplimiento global
            6. Agrega observaciones si es necesario
            7. Guarda el registro
            
            ### **Opción B: Por indicadores (para datos técnicos)**
            **Ubicación:** Menú principal → **"📈 Carga por Indicadores"**
            
            **Proceso:**
            1. Crea nuevo indicador o selecciona existente
            2. Asocia a una meta específica
            3. Registra valores periódicos (mensuales, trimestrales)
            4. El sistema actualiza automáticamente la meta asociada
            
            ### **🎯 Rangos de cumplimiento (estándar):**
            
            <div style="background: #ffebee; padding: 15px; border-radius: 5px; border-left: 4px solid #f44336; margin: 10px 0;">
            <strong>🔴 INCUMPLIDO:</strong> Menos del 60% de avance
            - Requiere atención inmediata
            - Posible revisión de estrategia
            - Notificación a responsables
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 5px; border-left: 4px solid #ff9800; margin: 10px 0;">
            <strong>🟡 PARCIALMENTE CUMPLIDO:</strong> Entre 60% y 89% de avance
            - En camino pero requiere seguimiento
            - Posibles ajustes menores
            - Mantener esfuerzo actual
            </div>
            
            <div style="background: #e8f5e9; padding: 15px; border-radius: 5px; border-left: 4px solid #4caf50; margin: 10px 0;">
            <strong>🟢 CUMPLIDO:</strong> 90% o más de avance
            - Objetivo alcanzado satisfactoriamente
            - Documentar lecciones aprendidas
            - Celebrar el éxito
            </div>
            
            ### **📅 Frecuencia RECOMENDADA de registro:**
            
            **📆 Mensual (Operativo):**
            - Registro de avances cada mes
            - Revisión rápida de progreso
            - Detección temprana de desviaciones
            
            **📊 Trimestral (Estratégico):**
            - Análisis profundo de tendencias
            - Ajuste de estrategias si es necesario
            - Reporte a dirección
            
            **📈 Anual (Evaluativo):**
            - Evaluación completa del año
            - Cierre formal de metas
            - Preparación para siguiente ciclo
            
            ### **📝 Documentación y evidencia:**
            - Guarda documentos de respaldo
            - Registra evidencias fotográficas
            - Documenta reuniones y acuerdos
            - Mantén un historial completo
            
            ### **🔔 Sistema de alertas:**
            - Notificaciones por metas próximas a vencer
            - Alertas por bajo cumplimiento
            - Recordatorios automáticos
            - Reportes de excepción
            
            ### **💡 Mejores prácticas:**
            1. **Consistencia:** Registra avances regularmente
            2. **Exactitud:** Usa datos verificados
            3. **Transparencia:** Documenta desviaciones
            4. **Oportunidad:** Actualiza en tiempo real
            5. **Colaboración:** Involucra a todos los responsables
            """
        },
        {
            "titulo": "📈 Cómo usar el Dashboard",
            "contenido": """
            ## Paso 5: Monitorear y visualizar
            
            **📍 Ve a:** Menú principal → **"📈 Dashboard Control"**
            
            ### **🎯 Lo que puedes visualizar:**
            
            **📊 Métricas principales (vista de resumen):**
            - **Cumplimiento global del sistema** → Porcentaje promedio de todas las metas
            - **Metas cumplidas vs pendientes** → Distribución por estado
            - **Acuerdos por estado** → Cantidad en cada fase (Borrador, Aprobado, etc.)
            - **Distribución por organismo** → Comparativa entre OPP, Organismo XX, etc.
            - **Evolución temporal** → Progreso a lo largo del tiempo
            
            **📈 Gráficos y visualizaciones:**
            - **Gráfico de líneas:** Evolución del cumplimiento mensual
            - **Gráfico de barras:** Comparativa entre organismos o acuerdos
            - **Gráfico de torta:** Distribución de metas por estado
            - **Mapa de calor:** Concentración de actividades
            - **Tablas interactivas:** Datos detallados con filtros
            
            **📋 Listados y detalles:**
            - **Acuerdos con bajo cumplimiento** → Para atención prioritaria
            - **Metas próximas a vencer** → Alertas tempranas (7, 15, 30 días)
            - **Indicadores críticos** → Requieren seguimiento especial
            - **Recomendaciones automáticas** → Basadas en análisis de datos
            - **Historial de cambios** → Auditoría completa
            
            ### **🔧 Funcionalidades del dashboard:**
            
            **🔄 Actualización en tiempo real:**
            - Los cambios en acuerdos y metas se reflejan inmediatamente
            - Datos siempre actualizados
            - Sin necesidad de refrescar manualmente
            
            **⚙️ Filtros avanzados:**
            - **Por año:** 2023, 2024, 2025...
            - **Por organismo:** OPP, Ministerio XX...
            - **Por estado:** Cumplido, En progreso, Pendiente, Atrasado
            - **Por tipo:** Institucional, Programático
            - **Por responsable:** Persona o área específica
            - **Por rango de fechas:** Períodos personalizados
            
            **📥 Exportación de datos:**
            - **PDF:** Para presentaciones ejecutivas
            - **Excel/CSV:** Para análisis detallado y procesamiento externo
            - **Imágenes:** Para incluir en reportes
            - **Datos crudos:** Para integración con otros sistemas
            
            **🔍 Búsqueda inteligente:**
            - Búsqueda por palabras clave
            - Filtrado por múltiples criterios
            - Historial de búsquedas frecuentes
            - Sugerencias automáticas
            
            ### **📱 Vista responsiva:**
            - Optimizado para computadoras
            - Adaptado para tablets
            - Visualización móvil básica
            
            ### **👥 Compartición:**
            - Compartir vistas específicas
            - Generar enlaces temporales
            - Configurar permisos por vista
            
            ### **💡 Consejos para usar el dashboard:**
            
            1. **Establece una rutina:**
               - Revisa diariamente por 5 minutos
               - Análisis profundo semanal
               - Reporte ejecutivo mensual
            
            2. **Personaliza tu vista:**
               - Guarda filtros frecuentes
               - Crea vistas personalizadas
               - Configura alertas personalizadas
            
            3. **Usa los datos para decisiones:**
               - Identifica tendencias
               - Detecta problemas temprano
               - Mide impacto de cambios
               - Justifica recursos adicionales
            
            4. **Colabora con el equipo:**
               - Comparte hallazgos
               - Discute soluciones
               - Coordina acciones
               - Celebra logros
            
            ### **📊 Ejemplo de uso efectivo:**
            
            **Lunes por la mañana:**
            1. Abre el dashboard
            2. Revisa alertas y notificaciones
            3. Filtra por "Metas próximas a vencer (7 días)"
            4. Identifica 3 metas críticas
            5. Asigna acciones específicas
            6. Programa seguimiento para miércoles
            
            **Reunión mensual:**
            1. Prepara reporte del dashboard
            2. Analiza tendencias del mes
            3. Identifica lecciones aprendidas
            4. Planifica acciones correctivas
            5. Establece objetivos para próximo mes
            
            ### **⚠️ Errores comunes:**
            - No revisar el dashboard regularmente
            - Ignorar alertas tempranas
            - No compartir información con el equipo
            - No usar datos para tomar decisiones
            - No capacitar a nuevos usuarios
            
            ### **🚀 Características avanzadas:**
            - **Comparativa histórica:** Comparar con años anteriores
            - **Pronósticos:** Proyecciones basadas en tendencias
            - **Benchmarking:** Comparar con estándares del sector
            - **Análisis de causa raíz:** Identificar problemas profundos
            - **Simulaciones:** Probar escenarios hipotéticos
            """
        },
        {
            "titulo": "🚀 Comenzar con datos reales",
            "contenido": """
            ## ¡Estás listo para comenzar!
            
            ### **📋 Checklist de IMPLEMENTACIÓN:**
            
            **✅ PRIMERA SEMANA (Fase de configuración):**
            1. **Crear 1-2 acuerdos piloto** → Comienza con acuerdos reales pero simples
            2. **Agregar 2-3 fichas por acuerdo** → Enfócate en áreas prioritarias
            3. **Definir 3-5 metas por ficha** → Metas realistas y medibles
            4. **Registrar valores base iniciales** → Estado actual al comenzar
            5. **Asignar responsables claros** → Quién hará seguimiento de cada meta
            6. **Configurar alertas básicas** → Notificaciones por vencimientos
            7. **Capacitar al equipo clave** → Al menos 2 personas por área
            
            **✅ PRIMER MES (Fase operativa inicial):**
            1. **Revisar el dashboard semanalmente** → Establecer rutina de seguimiento
            2. **Registrar primeros avances** → Valores logrados en el primer mes
            3. **Generar primer reporte de avance** → Para revisión del equipo
            4. **Ajustar metas si es necesario** → Basado en experiencia inicial
            5. **Capacitar a usuarios adicionales** → Ampliar el círculo de usuarios
            6. **Documentar lecciones aprendidas** → Qué funcionó y qué no
            7. **Planificar expansión** → Qué acuerdos agregar después
            
            **✅ PRIMER TRIMESTRE (Fase de consolidación):**
            1. **Evaluar cumplimiento parcial** → Análisis trimestral completo
            2. **Generar reporte ejecutivo** → Para presentación a dirección
            3. **Incorporar más acuerdos** → Ampliar cobertura del sistema
            4. **Optimizar procesos** → Mejorar basado en lecciones aprendidas
            5. **Planificar siguiente ciclo** → Preparar acuerdos para próximo año
            6. **Evaluar ROI del sistema** → Beneficios vs esfuerzo invertido
            7. **Celebrar logros** → Reconocer avances y esfuerzos
            
            ### **🎯 Próximos pasos RECOMENDADOS:**
            
            1. **Comenzar HOY mismo** con datos reales del Organismo
            2. **Usar el sistema diariamente** para familiarizarte
            3. **Consultar la ayuda en línea** si tienes dudas específicas
            4. **Compartir experiencias** con el equipo
            5. **Sugerir mejoras** basadas en tu uso real
            6. **Participar en comunidades** de usuarios
            7. **Mantener actualizado** el sistema
            
            ### **🔒 Aspectos de seguridad y confidencialidad:**
            
            - **Tus datos están 100% seguros** → Sistema con respaldo automático
            - **Acceso controlado** → Permisos por rol y responsabilidad
            - **Historial completo** → Auditoría de todos los cambios
            - **Cumplimiento normativo** → Alineado con regulaciones aplicables
            - **Privacidad protegida** → Datos sensibles adecuadamente manejados
            
            ### **🔄 Características clave del sistema:**
            
            - **Modificación flexible** → Puedes cambiar acuerdos en cualquier momento
            - **Guardado automático** → No pierdes información por olvido
            - **Trabajo colaborativo** → Múltiples usuarios simultáneamente
            - **Interfaz intuitiva** → Diseñada para facilidad de uso
            - **Soporte técnico** → Equipo disponible para ayudar
            
            ### **📞 Canales de soporte:**
            
            1. **Ayuda en línea** → Tutoriales y documentación
            2. **Foros de usuarios** → Compartir con otros usuarios
            3. **Soporte técnico** → Asistencia especializada
            4. **Capacitaciones** → Sesiones de formación
            5. **Mejoras continuas** → Sistema en constante evolución
            
            ### **🌟 Consejos finales para el éxito:**
            
            <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <strong>🎯 EMPIEZA PEQUEÑO:</strong> No intentes cargar todos los acuerdos a la vez. Comienza con los más importantes y expande gradualmente.
            </div>
            
            <div style="background: #f3e5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <strong>🤝 INVOLUCRA AL EQUIPO:</strong> El sistema funciona mejor cuando todos participan. Designa "campeones" en cada área.
            </div>
            
            <div style="background: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <strong>📊 USA LOS DATOS:</strong> No solo registres información, úsala para tomar decisiones y demostrar resultados.
            </div>
            
            <div style="background: #fff3e0; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <strong>🔄 ITERA Y MEJORA:</strong> Perfecciona tus procesos basándote en lo que aprendes usando el sistema.
            </div>
            
            <div style="background: #fce4ec; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <strong>🎉 CELEBRA LOS LOGROS:</strong> Reconoce y celebra cuando se alcanzan metas. Motiva al equipo a seguir adelante.
            </div>
            
            ### **🏁 ¡FELICITACIONES!**
            
            <div style="text-align: center; background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 30px; border-radius: 10px; margin: 30px 0;">
            <h2 style="color: white;">🎉 ¡HAS COMPLETADO EL TUTORIAL!</h2>
            <p style="font-size: 18px;">Estás ahora preparado para usar el Sistema de Compromisos de Gestión con datos reales.</p>
            <p><strong>¡Éxito en tu implementación y en el logro de todos tus objetivos!</strong></p>
            </div>
            
            **Recuerda:** El sistema es una herramienta, pero el éxito depende de cómo la uses. Sé consistente, sé colaborativo, y usa los datos para impulsar mejoras reales.
            """
        }
    ]
    
    # Controles de navegación
    st.markdown(f"### Paso {st.session_state.tutorial_paso + 1} de {len(pasos)}")
    st.progress((st.session_state.tutorial_paso + 1) / len(pasos))
    
    # Mostrar contenido del paso actual
    paso_actual = pasos[st.session_state.tutorial_paso]
    st.markdown(f"## {paso_actual['titulo']}")
    st.markdown(paso_actual['contenido'])
    
    # Botones de navegación
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.session_state.tutorial_paso > 0:
            if st.button("◀ Anterior", use_container_width=True):
                st.session_state.tutorial_paso -= 1
                st.rerun()
    
    with col2:
        if st.session_state.tutorial_paso < len(pasos) - 1:
            if st.button("Siguiente ▶", use_container_width=True):
                st.session_state.tutorial_paso += 1
                st.rerun()
        else:
            if st.button("🏁 Completado", use_container_width=True, type="primary"):
                st.session_state.tutorial_paso = 0
                st.session_state.current_page = "Generar Acuerdos"
                st.rerun()
    
    with col3:
        if st.button("🔄 Reiniciar tutorial", use_container_width=True):
            st.session_state.tutorial_paso = 0
            st.rerun()
        
    # Barra lateral con índice
    with st.sidebar:
        st.markdown("### 📚 Índice del Tutorial")
        for i, paso in enumerate(pasos):
            emoji = "✅" if i < st.session_state.tutorial_paso else "🟢" if i == st.session_state.tutorial_paso else "⚪"
            if st.button(f"{emoji} {paso['titulo']}", key=f"paso_{i}", use_container_width=True):
                st.session_state.tutorial_paso = i
                st.rerun()
        
        st.markdown("---")
        st.info("""
        **🎓 Tutorial Guiado**
        
        Este tutorial explica CÓMO usar tu sistema real.
        
        **No crea datos de ejemplo.**
        **No modifica tu base de datos.**
        **Explica funcionalidades existentes.**
        """)
    
    st.markdown("---")
    st.subheader("📋 ¿Listo para comenzar?")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🖨️ **Exportar este tutorial**", use_container_width=True):
            st.session_state.imprimir_tutorial = True
            st.rerun()
    
    with col_b:
        if st.button("📚 **Ver versión imprimible**", use_container_width=True):
            st.info("""
            **Versión imprimible incluye:**
            • Todo el contenido del tutorial
            • Formato limpio para imprimir
            • Checklist interactivos
            • Estilos optimizados para PDF
            """)
            if st.button("Abrir versión completa", key="abrir_imprimible"):
                st.session_state.imprimir_tutorial = True
                st.rerun()

def mostrar_version_imprimible():
    """Versión completa para imprimir - se muestra cuando se activa imprimir_tutorial"""
    
    st.title("🖨️ Tutorial Completo - Versión para Imprimir")
    
    # Botones de control en esta vista
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("◀ **Volver al tutorial interactivo**", use_container_width=True):
            st.session_state.imprimir_tutorial = False
            st.rerun()
    
    with col2:
        # Generar contenido HTML
        html_content = generar_html_tutorial_completo()
        
        st.download_button(
            label="📥 **Descargar como HTML**",
            data=html_content,
            file_name=f"tutorial_sistema_cg_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True
        )
    
    with col3:
        if st.button("🖶 **Previsualizar impresión**", use_container_width=True):
            st.info("Para imprimir: Presiona Ctrl+P o usa el menú de impresión de tu navegador")
            # Mostrar el contenido HTML directamente
            st.components.v1.html(html_content, height=800, scrolling=True)
    
    st.markdown("---")
    
    # Mostrar vista previa del contenido
    st.subheader("📄 Vista previa del contenido")
    with st.expander("Ver contenido completo", expanded=True):
        st.markdown(generar_markdown_completo(), unsafe_allow_html=True)

def generar_html_tutorial_completo():
    """Genera HTML completo con TODOS los pasos - VERSIÓN COMPLETA"""
    
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    html = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tutorial Sistema CG - {fecha}</title>
        <style>
            /* Estilos para impresión */
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ margin: 0.5in; font-size: 11pt; line-height: 1.4; }}
                h1 {{ page-break-before: always; }}
                h2 {{ page-break-after: avoid; }}
                .page-break {{ page-break-after: always; }}
                .paso {{ page-break-inside: avoid; }}
            }}
            
            /* Estilos generales */
            * {{
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial', 'Helvetica', sans-serif;
                line-height: 1.6;
                color: #333;
                background: #fff;
                max-width: 210mm; /* A4 */
                margin: 0 auto;
                padding: 15mm;
                counter-reset: paso;
            }}
            
            .header {{
                text-align: center;
                padding: 25px;
                background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
                color: white;
                border-radius: 8px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            
            .header h2 {{
                margin: 10px 0;
                font-size: 22px;
                opacity: 0.9;
            }}
            
            .header p {{
                margin: 10px 0 0;
                opacity: 0.9;
            }}
            
            .paso {{
                background: #f8f9fa;
                padding: 25px;
                margin: 25px 0;
                border-radius: 8px;
                border-left: 6px solid #2e7d32;
                position: relative;
                counter-increment: paso;
                page-break-inside: avoid;
            }}
            
            .paso::before {{
                content: "Paso " counter(paso);
                position: absolute;
                top: -12px;
                left: 20px;
                background: #2e7d32;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }}
            
            .paso h2 {{
                color: #1a237e;
                margin-top: 5px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e0e0e0;
            }}
            
            .consejo {{
                background: #e3f2fd;
                padding: 18px;
                border-radius: 6px;
                margin: 20px 0;
                border-left: 5px solid #1976d2;
                font-style: italic;
            }}
            
            .consejo strong {{
                color: #0d47a1;
            }}
            
            .checklist {{
                background: #e8f5e9;
                padding: 20px;
                border-radius: 6px;
                margin: 20px 0;
                border: 1px solid #c8e6c9;
            }}
            
            .checklist h4 {{
                color: #1b5e20;
                margin-top: 0;
            }}
            
            .meta-info {{
                background: #fff3e0;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
                border-left: 4px solid #f57c00;
            }}
            
            .ubicacion {{
                background: #f3e5f5;
                padding: 12px 18px;
                border-radius: 6px;
                margin: 15px 0;
                font-weight: bold;
                color: #4a148c;
                border-left: 4px solid #7b1fa2;
            }}
            
            .botones-accion {{
                text-align: center;
                margin: 30px 0;
                padding: 20px;
                background: #f5f5f5;
                border-radius: 8px;
            }}
            
            .boton-imprimir {{
                display: inline-block;
                background: #2196f3;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                text-decoration: none;
                margin: 10px;
                transition: background 0.3s;
            }}
            
            .boton-imprimir:hover {{
                background: #0d8bf2;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #e0e0e0;
                color: #666;
                font-size: 14px;
            }}
            
            /* Estilos para tablas */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            
            th {{
                background: #1a237e;
                color: white;
                padding: 10px;
                text-align: left;
            }}
            
            td {{
                padding: 8px;
                border: 1px solid #ddd;
            }}
            
            tr:nth-child(even) {{
                background: #f5f5f5;
            }}
            
            /* Estilos para listas */
            ul, ol {{
                padding-left: 20px;
                margin: 15px 0;
            }}
            
            li {{
                margin: 8px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎓 TUTORIAL COMPLETO DEL SISTEMA</h1>
            <h2>Sistema de Compromisos de Gestión</h2>
            <p>Versión para impresión • Generado: {fecha}</p>
            <p><em>Para uso interno • Sistema desarrollado por OPP</em></p>
        </div>
        
        <div class="botones-accion no-print">
            <button class="boton-imprimir" onclick="window.print()">
                🖨️ IMPRIMIR ESTE DOCUMENTO
            </button>
        </div>
        
        <!-- ========== PASO 1 ========== -->
        <div class="paso">
            <h2>🏛️ 1. Introducción al Sistema</h2>
            
            <p><strong>🎯 Objetivo principal:</strong> Aprender a gestionar acuerdos, fichas y metas institucionales dentro del Sistema de Compromisos de Gestión.</p>
            
            <div class="ubicacion">
                📍 <strong>Usuarios objetivo:</strong> Equipos técnicos, gestores y directivos del Organismo
            </div>
            
            <h3>📁 Estructura jerárquica del sistema:</h3>
            <ol>
                <li><strong>ACUERDOS</strong> → Compromisos formales con organismos
                    <ul>
                        <li>Contienen fichas de trabajo</li>
                        <li>Tienen vigencia anual</li>
                        <li>Pueden ser Institucionales o Programáticos</li>
                    </ul>
                </li>
                <li><strong>FICHAS</strong> → Áreas temáticas dentro de cada acuerdo
                    <ul>
                        <li>Agrupan metas relacionadas</li>
                        <li>Tipos: Capacitación, Transferencia, Gestión, etc.</li>
                        <li>Cada ficha tiene indicadores específicos</li>
                    </ul>
                </li>
                <li><strong>METAS</strong> → Objetivos cuantificables
                    <ul>
                        <li>Deben ser MEDIBLES, ALCANZABLES y TEMPORALES</li>
                        <li>Tienen valores objetivo y ponderación</li>
                        <li>Se registra cumplimiento periódico</li>
                    </ul>
                </li>
                <li><strong>INDICADORES</strong> → Medición del desempeño
                    <ul>
                        <li>Asociados a metas específicas</li>
                        <li>Permiten seguimiento detallado</li>
                        <li>Generan datos para dashboards</li>
                    </ul>
                </li>
            </ol>
            
            <h3>🔧 Pestañas principales:</h3>
            <table>
                <tr>
                    <th>Pestaña</th>
                    <th>Función</th>
                    <th>Uso frecuente</th>
                </tr>
                <tr>
                    <td><strong>📝 Generar Acuerdos</strong></td>
                    <td>Crear y gestionar acuerdos</td>
                    <td>Inicio de cada ciclo</td>
                </tr>
                <tr>
                    <td><strong>📈 Dashboard Control</strong></td>
                    <td>Ver métricas y cumplimiento</td>
                    <td>Seguimiento diario/semanal</td>
                </tr>
                <tr>
                    <td><strong>📊 Reportes</strong></td>
                    <td>Generar documentación ejecutiva</td>
                    <td>Reuniones y presentaciones</td>
                </tr>
                <tr>
                    <td><strong>🎯 Carga por Metas</strong></td>
                    <td>Registrar avances de metas</td>
                    <td>Actualización mensual</td>
                </tr>
            </table>
            
            <div class="consejo">
                <strong>💡 CONSEJO INICIAL:</strong> Comienza con 1-2 acuerdos de prueba para familiarizarte con el sistema antes de cargar todos los datos operativos reales.
            </div>
            
            <h3>📚 Lo que verás en este tutorial:</h3>
            <ul>
                <li>Cómo navegar por el sistema</li>
                <li>Estructura de un acuerdo completo</li>
                <li>Proceso paso a paso para crear contenido</li>
                <li>Consejos y mejores prácticas</li>
                <li>Uso del dashboard de control</li>
                <li>Generación de reportes</li>
            </ul>
        </div>
        
        <!-- ========== PASO 2 ========== -->
        <div class="paso">
            <h2>📝 2. Cómo crear un Acuerdo</h2>
            
            <div class="ubicacion">
                📍 <strong>Ubicación en el sistema:</strong> Pestaña principal → <strong>"Generar Acuerdos"</strong>
            </div>
            
            <h3>📋 Información básica REQUERIDA:</h3>
            <div class="checklist">
                <h4>Datos obligatorios:</h4>
                <ul>
                    <li><strong>Organismo contraparte</strong> → Institución con la que se firma el acuerdo (ej: OPP, Ministerio XX)</li>
                    <li><strong>Año de vigencia</strong> → Período para el cual aplica el acuerdo (ej: 2024)</li>
                    <li><strong>Tipo de compromiso</strong> → Institucional (general) o Programático (específico)</li>
                    <li><strong>Objeto del acuerdo</strong> → Descripción clara y completa del propósito</li>
                    <li><strong>Fecha de inicio</strong> → Cuándo comienza la vigencia</li>
                    <li><strong>Fecha de fin</strong> → Cuándo finaliza la vigencia</li>
                </ul>
            </div>
            
            <h3>🛠️ Proceso paso a paso:</h3>
            <ol>
                <li>Acceder a la pestaña <strong>"Generar Acuerdos"</strong></li>
                <li>Hacer clic en <strong>"➕ Crear nuevo acuerdo"</strong></li>
                <li>Completar el formulario con todos los campos obligatorios</li>
                <li>Revisar la información ingresada</li>
                <li>Hacer clic en <strong>"Guardar acuerdo"</strong></li>
                <li>El sistema asignará automáticamente un ID único</li>
            </ol>
            
            <div class="meta-info">
                <strong>📝 EJEMPLO de objeto bien redactado:</strong><br><br>
                "Desarrollar capacidades tecnológicas en el equipo del Organismo XX mediante programas de capacitación en herramientas digitales y modernización de procesos internos, con el objetivo de mejorar la eficiencia en la gestión de proyectos habitacionales y optimizar el uso de recursos durante el año fiscal 2024."
            </div>
            
            <h3>⚠️ Errores comunes a evitar:</h3>
            <ul>
                <li>No completar todos los campos obligatorios</li>
                <li>Usar objetos demasiado genéricos o vagos</li>
                <li>No asignar fechas realistas de inicio y fin</li>
                <li>Olvidar guardar los cambios antes de salir</li>
                <li>No revisar la información antes de guardar</li>
            </ul>
            
            <div class="consejo">
                <strong>💡 BUENA PRÁCTICA:</strong> Usa nombres de acuerdos que incluyan organismo y año. Ejemplo: <em>"Organismo XX - Acuerdo Institucional 2024"</em> o <em>"OPP - Programa de Modernización 2024"</em>.
            </div>
            
            <h3>📊 Tipos de compromiso:</h3>
            <table>
                <tr>
                    <th>Tipo</th>
                    <th>Descripción</th>
                    <th>Ejemplo</th>
                </tr>
                <tr>
                    <td><strong>Institucional</strong></td>
                    <td>Acuerdos generales de colaboración</td>
                    <td>Marco de cooperación Organismo XX-OPP</td>
                </tr>
                <tr>
                    <td><strong>Programático</strong></td>
                    <td>Acuerdos específicos por programa</td>
                    <td>Programa de modernización tecnológica</td>
                </tr>
            </table>
        </div>
        
        <!-- ========== PASO 3 ========== -->
        <div class="paso">
            <h2>📋 3. Cómo agregar Fichas a un Acuerdo</h2>
            
            <div class="ubicacion">
                📍 <strong>Dónde hacerlo:</strong> Dentro de cada acuerdo creado → Sección <strong>"Fichas"</strong>
            </div>
            
            <h3>🎯 ¿Qué son las fichas?</h3>
            <ul>
                <li><strong>Áreas temáticas</strong> específicas del acuerdo</li>
                <li>Cada ficha agrupa <strong>metas relacionadas</strong></li>
                <li>Permiten organizar el trabajo por categorías</li>
                <li>Facilitan el seguimiento por especialistas</li>
            </ul>
            
            <h3>📊 Tipos comunes de fichas:</h3>
            <ol>
                <li><strong>Capacitación</strong> → Formación y desarrollo de habilidades</li>
                <li><strong>Infraestructura</strong> → Mejora de instalaciones y equipos</li>
                <li><strong>Gestión</strong> → Optimización de procesos administrativos</li>
                <li><strong>Transferencia</strong> → Compartir conocimientos y tecnología</li>
                <li><strong>Investigación</strong> → Estudios y análisis especializados</li>
                <li><strong>Otro</strong> → Categorías específicas según necesidad</li>
            </ol>
            
            <h3>📋 Información de cada ficha:</h3>
            <div class="checklist">
                <h4>Campos requeridos:</h4>
                <ul>
                    <li><strong>Nombre descriptivo</strong> → Identificación clara del área (ej: "Capacitación en herramientas digitales")</li>
                    <li><strong>Tipo de meta</strong> → Capacitación, Transferencia, Gestión, Infraestructura, Otro</li>
                    <li><strong>Objetivo específico</strong> → Qué se busca lograr con esta ficha</li>
                    <li><strong>Indicador principal</strong> → Cómo se medirá el éxito de esta ficha</li>
                    <li><strong>Responsables</strong> → Personas o áreas encargadas</li>
                    <li><strong>Presupuesto asignado</strong> → Recursos financieros (opcional)</li>
                </ul>
            </div>
            
            <h3>🛠️ Proceso en el sistema:</h3>
            <ol>
                <li>Abrir el acuerdo existente desde la lista de acuerdos</li>
                <li>Ir a la sección <strong>"Fichas"</strong> (usualmente en pestañas o acordeón)</li>
                <li>Hacer clic en <strong>"➕ Agregar ficha"</strong></li>
                <li>Completar todos los campos del formulario</li>
                <li>Guardar la ficha</li>
                <li>Repetir para cada área de trabajo necesaria</li>
            </ol>
            
            <div class="meta-info">
                <strong>📈 Ejemplo de ficha bien estructurada:</strong><br><br>
                • <strong>Nombre:</strong> Capacitación en herramientas de gestión de proyectos<br>
                • <strong>Tipo:</strong> Capacitación<br>
                • <strong>Objetivo:</strong> Fortalecer las capacidades del equipo en metodologías ágiles<br>
                • <strong>Indicador:</strong> Número de personas certificadas<br>
                • <strong>Responsable:</strong> Departamento de Desarrollo Organizacional<br>
                • <strong>Presupuesto:</strong> $500,000
            </div>
            
            <div class="consejo">
                <strong>💡 RECOMENDACIÓN:</strong> Limita a 3-5 fichas por acuerdo para mantener el enfoque y facilitar el seguimiento. Demasiadas fichas pueden dispersar los esfuerzos.
            </div>
        </div>
        
        <!-- ========== PASO 4 ========== -->
        <div class="paso">
            <h2>🎯 4. Cómo definir Metas específicas</h2>
            
            <div class="ubicacion">
                📍 <strong>Dónde:</strong> Dentro de cada ficha creada → Sección <strong>"Metas"</strong>
            </div>
            
            <h3>📈 Características de una BUENA meta (principio SMART):</h3>
            <div class="checklist">
                <h4>✅ S - Específica</h4>
                <p>Clara, sin ambigüedades. Ej: <em>"Capacitar al equipo en uso de Excel avanzado"</em> en lugar de <em>"Mejorar habilidades"</em>.</p>
                
                <h4>✅ M - Medible</h4>
                <p>Con valor numérico objetivo. Ej: <em>"200 personas capacitadas"</em>, <em>"15 talleres realizados"</em>.</p>
                
                <h4>✅ A - Alcanzable</h4>
                <p>Realista y posible con los recursos disponibles.</p>
                
                <h4>✅ R - Relevante</h4>
                <p>Alineada con los objetivos institucionales.</p>
                
                <h4>✅ T - Temporal</h4>
                <p>Con fecha límite clara. Ej: <em>"Para el 30 de noviembre de 2024"</em>.</p>
            </div>
            
            <h3>📋 Datos REQUERIDOS por meta:</h3>
            <table>
                <tr>
                    <th>Campo</th>
                    <th>Descripción</th>
                    <th>Ejemplo</th>
                </tr>
                <tr>
                    <td><strong>Nombre</strong></td>
                    <td>Identificación clara de la meta</td>
                    <td>"Capacitar 200 personas en IoT"</td>
                </tr>
                <tr>
                    <td><strong>Valor objetivo</strong></td>
                    <td>Número a alcanzar</td>
                    <td>200</td>
                </tr>
                <tr>
                    <td><strong>Unidad</strong></td>
                    <td>Tipo de medida</td>
                    <td>personas, talleres, documentos</td>
                </tr>
                <tr>
                    <td><strong>Fecha vencimiento</strong></td>
                    <td>Límite para cumplir</td>
                    <td>30/11/2024</td>
                </tr>
                <tr>
                    <td><strong>Ponderación</strong></td>
                    <td>Importancia relativa (1-100%)</td>
                    <td>25%</td>
                </tr>
                <tr>
                    <td><strong>Valor base</strong></td>
                    <td>Situación inicial</td>
                    <td>0 (si se parte de cero)</td>
                </tr>
            </table>
            
            <h3>🛠️ En el sistema:</h3>
            <ol>
                <li>Abrir la ficha donde se agregará la meta</li>
                <li>Hacer clic en <strong>"➕ Agregar meta"</strong></li>
                <li>Completar el formulario detallado con todos los campos</li>
                <li>Definir rangos de cumplimiento si aplica (opcional)</li>
                <li>Guardar la meta</li>
                <li>Repetir para cada objetivo específico</li>
            </ol>
            
            <h3>⚖️ Ponderación de metas:</h3>
            <ul>
                <li>La suma de ponderaciones de todas las metas en una ficha debe ser <strong>100%</strong></li>
                <li>El sistema ayuda con cálculos automáticos y validaciones</li>
                <li>Asigna mayor ponderación a metas críticas o estratégicas</li>
                <li>Revisa periódicamente la distribución de ponderaciones</li>
            </ul>
            
            <div class="consejo">
                <strong>💡 IMPORTANTE:</strong> Comienza con metas <strong>realistas y alcanzables</strong>. Es mejor cumplir metas modestas que fallar en metas ambiciosas. Puedes ajustar las metas más adelante según la experiencia.
            </div>
            
            <h3>📅 Planificación temporal recomendada:</h3>
            <ul>
                <li><strong>Metas a corto plazo:</strong> 1-3 meses (para avances rápidos)</li>
                <li><strong>Metas a mediano plazo:</strong> 4-6 meses (para proyectos importantes)</li>
                <li><strong>Metas a largo plazo:</strong> 7-12 meses (para objetivos estratégicos)</li>
            </ul>
        </div>
        
        <!-- ========== PASO 5 ========== -->
        <div class="paso">
            <h2>📊 5. Cómo registrar cumplimiento</h2>
            
            <div class="ubicacion">
                📍 <strong>Dos formas disponibles. Nota: Deberán cargarse ambas formas ya que son necesarias para el seguimiento tanto de las metas como de los indicadores:</strong><br>
                1. <strong>"🎯 Carga por Metas"</strong>
                2. <strong>"📈 Carga por Indicadores"</strong>
            </div>
            
            <h3>📋 1: Carga por Metas </h3>
            <ol>
                <li>Acceder a <strong>"🎯 Carga por Metas"</strong> desde el menú principal</li>
                <li>Seleccionar el acuerdo → ficha → meta específica</li>
                <li>Ingresar el <strong>valor logrado</strong> en el período</li>
                <li>El sistema calcula automáticamente:
                    <ul>
                        <li>Porcentaje de cumplimiento</li>
                        <li>Estado (Cumplida/En Progreso/Pendiente)</li>
                        <li>Impacto en el cumplimiento global</li>
                        <li>Variación respecto al período anterior</li>
                    </ul>
                </li>
                <li>Agregar observaciones si es necesario</li>
                <li>Guardar el registro</li>
            </ol>
            
            <h3>📈 2: Carga por Indicadores</h3>
            <ol>
                <li>Acceder a <strong>"📈 Carga por Indicadores"</strong></li>
                <li>Crear nuevo indicador o seleccionar existente</li>
                <li>Asociar a una meta específica</li>
                <li>Registrar valores periódicos (mensuales, trimestrales)</li>
                <li>El sistema actualiza automáticamente la meta asociada</li>
                <li>Visualizar tendencias y análisis</li>
            </ol>
            
            <h3>🎯 Rangos de cumplimiento (estándar):</h3>
            <div class="meta-info">
                <div style="display: flex; align-items: center; margin: 10px 0; padding: 10px; background: #ffebee; border-radius: 5px;">
                    <div style="width: 20px; height: 20px; background: #f44336; border-radius: 50%; margin-right: 10px;"></div>
                    <div><strong>🔴 INCUMPLIDO:</strong> Menos del 60% de avance - Requiere atención inmediata</div>
                </div>
                <div style="display: flex; align-items: center; margin: 10px 0; padding: 10px; background: #fff3e0; border-radius: 5px;">
                    <div style="width: 20px; height: 20px; background: #ff9800; border-radius: 50%; margin-right: 10px;"></div>
                    <div><strong>🟡 PARCIALMENTE CUMPLIDO:</strong> Entre 60% y 89% de avance - En camino pero requiere seguimiento</div>
                </div>
                <div style="display: flex; align-items: center; margin: 10px 0; padding: 10px; background: #e8f5e9; border-radius: 5px;">
                    <div style="width: 20px; height: 20px; background: #4caf50; border-radius: 50%; margin-right: 10px;"></div>
                    <div><strong>🟢 CUMPLIDO:</strong> 90% o más de avance - Objetivo alcanzado satisfactoriamente</div>
                </div>
            </div>
            
            <h3>📅 Frecuencia RECOMENDADA de registro:</h3>
            <div class="checklist">
                <h4>📆 Mensual (Operativo)</h4>
                <p><strong>Registro de avances:</strong> Ingresar valores logrados cada mes para mantener datos actualizados.</p>
                
                <h4>📊 Trimestral (Estratégico)</h4>
                <p><strong>Revisión de cumplimiento:</strong> Analizar tendencias y ajustar estrategias si es necesario.</p>
                
                <h4>📈 Anual (Evaluativo)</h4>
                <p><strong>Cierre y reporte final:</strong> Evaluación completa del año y preparación para el siguiente ciclo.</p>
            </div>
            
            <h3>📝 Documentación y evidencia:</h3>
            <ul>
                <li>Guardar documentos de respaldo (informes, fotos, actas)</li>
                <li>Registrar evidencias fotográficas cuando aplique</li>
                <li>Documentar reuniones y acuerdos relevantes</li>
                <li>Mantener un historial completo de todos los registros</li>
                <li>Archivar documentación según normas institucionales</li>
            </ul>
            
            <div class="consejo">
                <strong>💡 BUENA PRÁCTICA:</strong> Programa recordatorios en tu calendario para el registro periódico. La consistencia en el registro es clave para datos confiables y toma de decisiones informada.
            </div>
        </div>
        
        <!-- ========== PASO 6 ========== -->
        <div class="paso">
            <h2>📈 6. Cómo usar el Dashboard de Control</h2>
            
            <div class="ubicacion">
                📍 <strong>Acceso:</strong> Menú principal → <strong>"📈 Dashboard Control"</strong>
            </div>
            
            <h3>🎯 Qué puedes visualizar:</h3>
            
            <h4>📊 Métricas principales (vista de resumen):</h4>
            <ul>
                <li><strong>Cumplimiento global del sistema</strong> → Porcentaje promedio de todas las metas</li>
                <li><strong>Metas cumplidas vs pendientes</strong> → Distribución por estado</li>
                <li><strong>Acuerdos por estado</strong> → Cantidad en cada fase (Borrador, Aprobado, etc.)</li>
                <li><strong>Distribución por organismo</strong> → Comparativa entre OPP, Organismo XX, etc.</li>
                <li><strong>Evolución temporal</strong> → Progreso a lo largo del tiempo</li>
                <li><strong>Alertas y notificaciones</strong> → Metas próximas a vencer o con problemas</li>
            </ul>
            
            <h4>📈 Gráficos y visualizaciones:</h4>
            <table>
                <tr>
                    <th>Tipo de gráfico</th>
                    <th>Propósito</th>
                    <th>Uso recomendado</th>
                </tr>
                <tr>
                    <td><strong>Gráfico de líneas</strong></td>
                    <td>Mostrar evolución en el tiempo</td>
                    <td>Seguimiento de tendencias mensuales</td>
                </tr>
                <tr>
                    <td><strong>Gráfico de barras</strong></td>
                    <td>Comparar diferentes categorías</td>
                    <td>Comparativa entre organismos o áreas</td>
                </tr>
                <tr>
                    <td><strong>Gráfico de torta</strong></td>
                    <td>Mostrar proporciones</td>
                    <td>Distribución de metas por estado</td>
                </tr>
                <tr>
                    <td><strong>Tablas interactivas</strong></td>
                    <td>Detalle de datos</td>
                    <td>Análisis específico y exportación</td>
                </tr>
            </table>
            
            <h3>🔧 Funcionalidades del dashboard:</h3>
            
            <h4>🔄 Actualización en tiempo real</h4>
            <p>Los cambios en acuerdos y metas se reflejan inmediatamente en el dashboard.</p>
            
            <h4>⚙️ Filtros avanzados</h4>
            <p>Puedes filtrar por múltiples criterios:</p>
            <ul>
                <li><strong>Año:</strong> 2023, 2024, 2025...</li>
                <li><strong>Organismo:</strong> OPP, Ministerio XX...</li>
                <li><strong>Estado:</strong> Cumplido, En progreso, Pendiente, Atrasado</li>
                <li><strong>Tipo:</strong> Institucional, Programático</li>
                <li><strong>Responsable:</strong> Persona o área específica</li>
                <li><strong>Rango de fechas:</strong> Períodos personalizados</li>
            </ul>
            
            <h4>📥 Exportación de datos</h4>
            <p>Descarga reportes en diferentes formatos:</p>
            <ul>
                <li><strong>PDF:</strong> Para presentaciones ejecutivas y reportes formales</li>
                <li><strong>Excel/CSV:</strong> Para análisis detallado y procesamiento externo</li>
                <li><strong>Imágenes:</strong> Para incluir en presentaciones o documentos</li>
                <li><strong>Datos crudos:</strong> Para integración con otros sistemas</li>
            </ul>
            
            <div class="consejo">
                <strong>💡 RECOMENDACIÓN:</strong> Revisa el dashboard al menos una vez por semana para mantener control sobre el avance global. Usa los filtros para enfocarte en lo más relevante para tu rol y responsabilidades.
            </div>
            
            <h3>📊 Ejemplo de uso efectivo:</h3>
            <div class="meta-info">
                <strong>Lunes por la mañana (10 minutos):</strong><br>
                1. Abre el dashboard principal<br>
                2. Revisa alertas y notificaciones<br>
                3. Filtra por "Metas próximas a vencer (7 días)"<br>
                4. Identifica 3-5 metas críticas<br>
                5. Asigna acciones específicas<br>
                6. Programa seguimiento para miércoles<br><br>
                
                <strong>Reunión mensual de equipo:</strong><br>
                1. Prepara reporte del dashboard<br>
                2. Analiza tendencias del mes<br>
                3. Identifica lecciones aprendidas<br>
                4. Planifica acciones correctivas<br>
                5. Establece objetivos para próximo mes
            </div>
        </div>
        
        <!-- ========== PASO 7 ========== -->
        <div class="paso">
            <h2>🚀 7. Comenzar con datos REALES - Plan de implementación</h2>
            
            <div class="ubicacion">
                📍 <strong>Ahora estás listo para:</strong> Usar el sistema con información REAL del Organismo
            </div>
            
            <h3>📋 Checklist de IMPLEMENTACIÓN:</h3>
            
            <div class="checklist">
                <h4>✅ PRIMERA SEMANA (Fase de configuración)</h4>
                <ul>
                    <li><strong>Crear 1-2 acuerdos piloto</strong> → Comienza con acuerdos reales pero simples</li>
                    <li><strong>Agregar 2-3 fichas por acuerdo</strong> → Enfócate en áreas prioritarias</li>
                    <li><strong>Definir 3-5 metas por ficha</strong> → Metas realistas y medibles</li>
                    <li><strong>Registrar valores base iniciales</strong> → Estado actual al comenzar</li>
                    <li><strong>Asignar responsables claros</strong> → Quién hará seguimiento de cada meta</li>
                    <li><strong>Configurar alertas básicas</strong> → Notificaciones por vencimientos</li>
                    <li><strong>Capacitar al equipo clave</strong> → Al menos 2 personas por área</li>
                </ul>
            </div>
            
            <div class="checklist">
                <h4>✅ PRIMER MES (Fase operativa inicial)</h4>
                <ul>
                    <li><strong>Revisar el dashboard semanalmente</strong> → Establecer rutina de seguimiento</li>
                    <li><strong>Registrar primeros avances</strong> → Valores logrados en el primer mes</li>
                    <li><strong>Generar primer reporte de avance</strong> → Para revisión del equipo</li>
                    <li><strong>Ajustar metas si es necesario</strong> → Basado en experiencia inicial</li>
                    <li><strong>Capacitar a usuarios adicionales</strong> → Ampliar el círculo de usuarios</li>
                    <li><strong>Documentar lecciones aprendidas</strong> → Qué funcionó y qué no</li>
                    <li><strong>Planificar expansión</strong> → Qué acuerdos agregar después</li>
                </ul>
            </div>
            
            <div class="checklist">
                <h4>✅ PRIMER TRIMESTRE (Fase de consolidación)</h4>
                <ul>
                    <li><strong>Evaluar cumplimiento parcial</strong> → Análisis trimestral completo</li>
                    <li><strong>Generar reporte ejecutivo</strong> → Para presentación a dirección</li>
                    <li><strong>Incorporar más acuerdos</strong> → Ampliar cobertura del sistema</li>
                    <li><strong>Optimizar procesos</strong> → Mejorar basado en lecciones aprendidas</li>
                    <li><strong>Planificar siguiente ciclo</strong> → Preparar acuerdos para próximo año</li>
                    <li><strong>Evaluar ROI del sistema</strong> → Beneficios vs esfuerzo invertido</li>
                    <li><strong>Celebrar logros</strong> → Reconocer avances y esfuerzos</li>
                </ul>
            </div>
            
            <h3>🎯 Próximos pasos RECOMENDADOS:</h3>
            <ol>
                <li><strong>Comenzar HOY mismo</strong> con datos reales del Organismo</li>
                <li><strong>Usar el sistema diariamente</strong> para familiarizarte</li>
                <li><strong>Consultar la ayuda en línea</strong> si tienes dudas específicas</li>
                <li><strong>Compartir experiencias</strong> con el equipo</li>
                <li><strong>Sugerir mejoras</strong> basadas en tu uso real</li>
                <li><strong>Participar en comunidades</strong> de usuarios</li>
                <li><strong>Mantener actualizado</strong> el sistema y tus conocimientos</li>
            </ol>
            
            <div class="consejo">
                <strong>🔒 RECUERDA:</strong><br>
                • Puedes <strong>modificar acuerdos</strong> en cualquier momento<br>
                • El sistema <strong>guarda automáticamente</strong> todos los cambios<br>
                • Tus datos están <strong>100% seguros y respaldados</strong><br>
                • El equipo de soporte está disponible para ayudarte<br>
                • El sistema cumple con todas las normativas de seguridad
            </div>
            
            <div style="text-align: center; background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 30px; border-radius: 10px; margin: 30px 0;">
                <h2 style="color: white; margin-top: 0;">🎉 ¡FELICITACIONES!</h2>
                <p style="font-size: 18px; margin-bottom: 10px;">Has completado el tutorial completo del Sistema de Compromisos de Gestión</p>
                <p style="font-size: 16px; margin-bottom: 0;">Estás ahora preparado para implementar y usar el sistema con datos reales del Organismo.</p>
                <p style="font-size: 18px; margin-top: 15px;"><strong>¡Éxito en tu implementación y en el logro de todos tus objetivos!</strong></p>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>🎓 Tutorial Completo del Sistema de Compromisos de Gestión</strong></p>
            <p>Versión {datetime.now().strftime('%Y.%m.%d')} • Generado automáticamente</p>
            <p><em>Para uso interno • Sistema desarrollado y mantenido por OPP</em></p>
            <p><small>© {datetime.now().strftime('%Y')} - Todos los derechos reservados</small></p>
        </div>
        
        <script>
            // Script para imprimir
            function prepararImpresion() {{
                // Aquí puedes agregar lógica adicional antes de imprimir si es necesario
                window.print();
            }}
            
            // Configurar el botón de impresión
            document.querySelector('.boton-imprimir').addEventListener('click', prepararImpresion);
        </script>
    </body>
    </html>
    '''
    
    return html

def generar_markdown_completo():
    """Versión en markdown para mostrar en Streamlit"""
    
    fecha = datetime.now().strftime('%d/%m/%Y')
    
    contenido = f"""
    # 🎓 Tutorial Completo - Sistema de Compromisos de Gestión
    
    ## 🏛️ 1. Introducción al Sistema
    
    **🎯 Objetivo:** Aprender a gestionar acuerdos, fichas y metas institucionales dentro del Sistema de Compromisos de Gestión.
    
    ### 📁 Estructura del sistema:
    1. **Acuerdos** → Compromisos formales con organismos
    2. **Fichas** → Áreas temáticas dentro de cada acuerdo  
    3. **Metas** → Objetivos cuantificables a cumplir
    4. **Indicadores** → Medición del desempeño
    
    ### 🔧 Pestañas principales:
    - **📝 Generar Acuerdos**: Crear y gestionar acuerdos
    - **📈 Dashboard Control**: Ver métricas y cumplimiento
    - **📊 Reportes**: Generar documentación ejecutiva
    - **🎯 Carga por Metas**: Registrar avances
    
    ---
    
    ## 📝 2. Cómo crear un Acuerdo
    
    **📍 Ubicación:** Pestaña **"Generar Acuerdos"**
    
    ### 📋 Información básica requerida:
    1. **Organismo** → Institución con la que se firma
    2. **Año** → Período de vigencia  
    3. **Tipo de compromiso** → Institucional/Programático
    4. **Objeto** → Descripción detallada
    
    ### 💡 Consejo práctico:
    Usa nombres que incluyan organismo y año. Ejemplo: `"OPP - Acuerdo Institucional 2024"`
    
    ---
    
    ## 📋 3. Cómo agregar Fichas
    
    **📍 Dónde hacerlo:** Dentro de cada acuerdo creado
    
    ### 🎯 Qué son las fichas:
    - **Áreas temáticas** del acuerdo
    - Cada ficha agrupa **metas relacionadas**
    - Ejemplos: "Capacitación", "Infraestructura", "Gestión"
    
    ### 📊 Información de cada ficha:
    1. **Nombre** → Identificación clara
    2. **Tipo de meta** → Capacitación/Transferencia/etc.
    3. **Objetivo** → Qué se busca lograr
    4. **Indicador** → Cómo se medirá
    
    ---
    
    ## 🎯 4. Cómo definir Metas
    
    **📍 Dónde:** Dentro de cada ficha creada
    
    ### 📈 Características SMART:
    - **Específica**: Clara y sin ambigüedades
    - **Medible**: Con valor numérico objetivo
    - **Alcanzable**: Realista y posible
    - **Relevante**: Alineada con objetivos
    - **Temporal**: Con fecha límite clara
    
    ### 📋 Datos requeridos:
    1. **Nombre** → Ej: "Capacitar 200 personas"
    2. **Valor objetivo** → Ej: 200
    3. **Unidad** → personas, talleres, documentos
    4. **Fecha vencimiento** → Cuándo cumplir
    5. **Ponderación** → Importancia (1-100%)
    
    ---
    
    ## 📊 5. Cómo registrar cumplimiento
    
    **📍 Dos formas disponibles:**
    Nota: Deberán cargarse ambas ya que es necesario obtener información para el seguimiento tanto de metas como de indicadores.
    ### A: Por metas 
    1. Ve a **"🎯 Carga por Metas"**
    2. Selecciona acuerdo → ficha → meta
    3. Ingresa **valor logrado**
    4. Sistema calcula automáticamente
    
    
    ### B: Por indicadores 
    1. Ve a **"📈 Carga por Indicadores"**
    2. Asocia a meta existente
    3. Registra valores periódicos
    
    ### 🎯 Rangos de cumplimiento:
    - **🔴 < 60%** → Incumplido
    - **🟡 60-89%** → Parcialmente cumplido  
    - **🟢 ≥ 90%** → Cumplido
    
    ---
    
    ## 📈 6. Cómo usar el Dashboard
    
    **📍 Ve a:** **"📈 Dashboard Control"**
    
    ### 🎯 Lo que puedes ver:
    - Cumplimiento global del sistema
    - Metas cumplidas vs pendientes
    - Acuerdos por estado
    - Evolución temporal
    - Alertas y notificaciones
    
    ### 🔧 Funcionalidades:
    - Filtros avanzados por año, organismo, estado
    - Exportación a PDF, Excel, CSV
    - Actualización en tiempo real
    - Vistas personalizables
    
    ---
    
    ## 🚀 7. Comenzar con datos reales
    
    ### 📋 Checklist de implementación:
    
    **✅ PRIMERA SEMANA:**
    - [ ] Crear 1-2 acuerdos piloto
    - [ ] Agregar 2-3 fichas por acuerdo
    - [ ] Definir 3-5 metas por ficha
    - [ ] Registrar valores iniciales
    - [ ] Asignar responsables
    
    **✅ PRIMER MES:**
    - [ ] Revisar dashboard semanalmente
    - [ ] Registrar avances de metas
    - [ ] Generar primer reporte
    - [ ] Ajustar metas si necesario
    
    **✅ PRIMER TRIMESTRE:**
    - [ ] Evaluar cumplimiento parcial
    - [ ] Generar reporte ejecutivo
    - [ ] Incorporar más acuerdos
    - [ ] Optimizar procesos
    
    ---
    
    *Documento generado el {fecha} • Para uso interno del Organismo*
    
    ### 🎉 ¡FELICITACIONES!
    **Has completado el tutorial y estás listo para implementar el sistema con datos reales.**
    
    **Recuerda:** 
    - Puedes modificar acuerdos en cualquier momento
    - El sistema guarda automáticamente
    - Tus datos están seguros y respaldados
    - El equipo de soporte está disponible
    """
    
    return contenido

def analizar_riesgos_acuerdo(acuerdo):
    """Analiza riesgos en un acuerdo específico - SIN dependencias externas"""
   
    riesgos = {
        'metas_sin_ponderacion': 0,
        'metas_vencimiento_proximo': 0,
        'metas_bajo_cumplimiento': 0,
        'metas_sin_rangos': 0,
        'total_riesgos': 0,
        'matriz_riesgos': {'bajo': 0, 'medio': 0, 'alto': 0, 'critico': 0},
        'recomendaciones': []
    }
    
    hoy = datetime.now()
    
    # Analizar cada ficha y meta
    for ficha in acuerdo.get('fichas', []):
        for meta in ficha.get('metas', []):
            # Riesgo 1: Meta sin ponderación
            if meta.get('ponderacion', 0) == 0:
                riesgos['metas_sin_ponderacion'] += 1
                riesgos['recomendaciones'].append({
                    'titulo': f"Asignar ponderación a '{meta.get('nombre', 'meta sin nombre')}'",
                    'descripcion': 'Meta sin ponderación asignada afecta cálculo general',
                    'prioridad': 'Alta',
                    'accion': 'Asignar ponderación entre 1-100%'
                })
            
            # Riesgo 2: Vencimiento próximo (30 días)
            if meta.get('vencimiento'):
                try:
                    vencimiento = datetime.strptime(meta['vencimiento'], '%Y-%m-%d')
                    dias_restantes = (vencimiento - hoy).days
                    if 0 < dias_restantes <= 30:
                        riesgos['metas_vencimiento_proximo'] += 1
                        riesgos['recomendaciones'].append({
                            'titulo': f"Meta próxima a vencer: '{meta.get('nombre', '')}'",
                            'descripcion': f'Vence en {dias_restantes} días ({meta["vencimiento"]})',
                            'prioridad': 'Alta' if dias_restantes <= 7 else 'Media',
                            'accion': 'Acelerar seguimiento y reporte'
                        })
                except:
                    pass
            
            # Riesgo 3: Bajo cumplimiento histórico
            if meta.get('cumplimiento_calc') is not None and meta['cumplimiento_calc'] < 50:
                riesgos['metas_bajo_cumplimiento'] += 1
                riesgos['recomendaciones'].append({
                    'titulo': f"Bajo cumplimiento: '{meta.get('nombre', '')}'",
                    'descripcion': f'Cumplimiento actual: {meta["cumplimiento_calc"]:.1f}%',
                    'prioridad': 'Alta',
                    'accion': 'Revisar causas y ajustar estrategia'
                })
            
            # Riesgo 4: Sin rangos de cumplimiento configurados
            if not meta.get('rango') or len(meta['rango']) == 0:
                riesgos['metas_sin_rangos'] += 1
                riesgos['recomendaciones'].append({
                    'titulo': f"Meta sin rangos: '{meta.get('nombre', '')}'",
                    'descripcion': 'No tiene rangos de cumplimiento configurados',
                    'prioridad': 'Media',
                    'accion': 'Configurar rangos para cálculo automático'
                })
            
            # Riesgo 5: Meta sin valor objetivo
            if not meta.get('valor_objetivo'):
                riesgos['recomendaciones'].append({
                    'titulo': f"Meta sin valor objetivo: '{meta.get('nombre', '')}'",
                    'descripcion': 'No tiene valor objetivo definido',
                    'prioridad': 'Media',
                    'accion': 'Definir valor objetivo cuantificable'
                })
    
    # Calcular total de riesgos
    riesgos['total_riesgos'] = sum([
        riesgos['metas_sin_ponderacion'],
        riesgos['metas_vencimiento_proximo'],
        riesgos['metas_bajo_cumplimiento'],
        riesgos['metas_sin_rangos']
    ])
    
    # Clasificar en matriz de riesgos
    if riesgos['total_riesgos'] > 10:
        riesgos['matriz_riesgos']['critico'] = 1
    elif riesgos['total_riesgos'] > 5:
        riesgos['matriz_riesgos']['alto'] = 1
    elif riesgos['total_riesgos'] > 2:
        riesgos['matriz_riesgos']['medio'] = 1
    else:
        riesgos['matriz_riesgos']['bajo'] = 1
    
    # Ordenar recomendaciones por prioridad
    prioridad_orden = {'Alta': 1, 'Media': 2, 'Baja': 3}
    riesgos['recomendaciones'].sort(key=lambda x: prioridad_orden.get(x['prioridad'], 4))
    
    return riesgos

def mostrar_matriz_riesgos_simple(matriz):
    """Muestra matriz de riesgos visualmente SIN plotly"""
    
    st.write("### Distribución de Niveles de Riesgo")
    
    # Barras con texto simple
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.progress(matriz['bajo'] / 10 if matriz['bajo'] > 0 else 0)
        st.write(f"**Bajo:** {matriz['bajo']}")
        
    with col2:
        st.progress(matriz['medio'] / 10 if matriz['medio'] > 0 else 0)
        st.write(f"**Medio:** {matriz['medio']}")
        
    with col3:
        st.progress(matriz['alto'] / 10 if matriz['alto'] > 0 else 0)
        st.write(f"**Alto:** {matriz['alto']}")
        
    with col4:
        st.progress(matriz['critico'] / 10 if matriz['critico'] > 0 else 0)
        st.write(f"**Crítico:** {matriz['critico']}")
    
    # Tabla simple
    st.write("**Resumen:**")
    st.write(f"- 🔵 Bajo riesgo: {matriz['bajo']} área(s)")
    st.write(f"- 🟡 Riesgo medio: {matriz['medio']} área(s)")
    st.write(f"- 🟠 Alto riesgo: {matriz['alto']} área(s)")
    st.write(f"- 🔴 Riesgo crítico: {matriz['critico']} área(s)")

def analizar_tendencias_organismo(organismo, año_inicio, año_fin, db):
    """Analiza tendencias de un organismo en un período - SIN pandas"""
    
    # Filtrar acuerdos del organismo en el período
    acuerdos_periodo = []
    for acuerdo_id, acuerdo in db.items():
        if (acuerdo.get('organismo_nombre') == organismo and 
            año_inicio <= acuerdo.get('año', 0) <= año_fin):
            acuerdos_periodo.append(acuerdo)
    
    if len(acuerdos_periodo) < 2:
        return {'error': 'Insuficientes datos para análisis'}
    
    # Ordenar por año
    acuerdos_periodo.sort(key=lambda x: x.get('año', 0))
    
    tendencias = {
        'organismo': organismo,
        'periodo': f"{año_inicio}-{año_fin}",
        'total_acuerdos': len(acuerdos_periodo),
        'datos_grafico': [],
        'alertas': []
    }
    
    # Calcular métricas por año
    datos_anuales = []
    for acuerdo in acuerdos_periodo:
        año = acuerdo.get('año')
        
        # Calcular cumplimiento promedio del año
        cumplimientos = []
        total_metas = 0
        metas_completadas = 0
        
        for ficha in acuerdo.get('fichas', []):
            for meta in ficha.get('metas', []):
                total_metas += 1
                if meta.get('cumplimiento_calc') is not None:
                    cumplimientos.append(meta['cumplimiento_calc'])
                    if meta['cumplimiento_calc'] >= 90:
                        metas_completadas += 1
        
        cumplimiento_promedio = sum(cumplimientos) / len(cumplimientos) if cumplimientos else 0
        
        datos_anuales.append({
            'año': año,
            'cumplimiento': cumplimiento_promedio,
            'metas': total_metas,
            'completadas': metas_completadas
        })
    
    # Agregar a datos para gráfico
    for dato in datos_anuales:
        tendencias['datos_grafico'].append({
            'Año': dato['año'],
            'Cumplimiento (%)': dato['cumplimiento'],
            'Metas': dato['metas'],
            'Metas Completadas': dato['completadas']
        })
    
    # Detectar tendencias
    if len(datos_anuales) >= 2:
        # Tendencia de cumplimiento
        primer = datos_anuales[0]['cumplimiento']
        ultimo = datos_anuales[-1]['cumplimiento']
        diferencia = ultimo - primer
        
        if diferencia > 5:
            tendencias['tendencia_cumplimiento'] = 'positiva'
            tendencias['alertas'].append({
                'tipo': '✅ Positiva',
                'titulo': 'Mejora en cumplimiento',
                'descripcion': f'Cumplimiento aumentó {diferencia:.1f}% ({primer:.1f}% → {ultimo:.1f}%)',
                'recomendacion': 'Mantener estrategias exitosas'
            })
            tendencias['mejora_eficiencia'] = diferencia
        elif diferencia < -5:
            tendencias['tendencia_cumplimiento'] = 'negativa'
            tendencias['alertas'].append({
                'tipo': '⚠️ Negativa',
                'titulo': 'Disminución en cumplimiento',
                'descripcion': f'Cumplimiento disminuyó {abs(diferencia):.1f}% ({primer:.1f}% → {ultimo:.1f}%)',
                'recomendacion': 'Revisar causas y ajustar metas'
            })
            tendencias['mejora_eficiencia'] = diferencia
        else:
            tendencias['tendencia_cumplimiento'] = 'estable'
            tendencias['mejora_eficiencia'] = 0
        
        # Tendencia de número de metas
        primer_metas = datos_anuales[0]['metas']
        ultimo_metas = datos_anuales[-1]['metas']
        
        if primer_metas > 0:
            crecimiento = ((ultimo_metas - primer_metas) / primer_metas) * 100
            tendencias['crecimiento_metas'] = crecimiento
            
            if crecimiento > 20:
                tendencias['alertas'].append({
                    'tipo': '📈 Crecimiento',
                    'titulo': 'Aumento significativo en metas',
                    'descripcion': f'Metas aumentaron {crecimiento:.1f}% ({primer_metas} → {ultimo_metas})',
                    'recomendacion': 'Evaluar capacidad de seguimiento'
                })
            elif crecimiento < -20:
                tendencias['alertas'].append({
                    'tipo': '📉 Reducción',
                    'titulo': 'Reducción significativa en metas',
                    'descripcion': f'Metas redujeron {abs(crecimiento):.1f}% ({primer_metas} → {ultimo_metas})',
                    'recomendacion': 'Revisar si se mantiene la ambición adecuada'
                })
        
        # Detectar patrón estacional (simplificado)
        if len(datos_anuales) >= 3:
            # Verificar si hay patrón de mejoras consistentes
            mejoras = all(datos_anuales[i]['cumplimiento'] <= datos_anuales[i+1]['cumplimiento'] 
                         for i in range(len(datos_anuales)-1))
            
            if mejoras:
                tendencias['alertas'].append({
                    'tipo': '🌟 Excelente',
                    'titulo': 'Mejora consistente año tras año',
                    'descripcion': 'Cumplimiento ha mejorado consistentemente cada año',
                    'recomendacion': 'Documentar prácticas exitosas para replicar'
                })
    
    return tendencias

def calcular_metricas_globales(db):
    """Calcula métricas globales del sistema - VERSIÓN CORREGIDA"""
    
    metricas = {
        'acuerdos_activos': 0,
        'riesgos_altos': 0,
        'tendencias_positivas': 0,
        'alertas_activas': 0,
        'cumplimiento_promedio': 0,
        'metas_totales': 0,
        'metas_completadas': 0
    }
    
    # 🛡️ VERIFICAR TIPO DE DATOS
    if isinstance(db, dict):
        # Es un diccionario (formato original)
        acuerdos_lista = list(db.values())
    elif isinstance(db, list):
        # Ya es una lista (nuevo formato)
        acuerdos_lista = db
    else:
        st.error(f"❌ Tipo de datos no soportado en calcular_metricas_globales: {type(db)}")
        return metricas
    
    # Contar acuerdos activos y analizar riesgos
    for acuerdo in acuerdos_lista:
        if acuerdo.get('estado') in ['Borrador', 'En Revisión', 'Aprobado', 'Vigente']:
            metricas['acuerdos_activos'] += 1
        
        # Contar metas y cumplimiento
        for ficha in acuerdo.get('fichas', []):
            for meta in ficha.get('metas', []):
                metricas['metas_totales'] += 1
                if meta.get('cumplimiento_calc') is not None:
                    metricas['cumplimiento_promedio'] += meta['cumplimiento_calc']
                    if meta['cumplimiento_calc'] >= 90:
                        metricas['metas_completadas'] += 1
    
    # Calcular promedio
    todas_las_metas = []

    for acuerdo in acuerdos_lista:
        for ficha in acuerdo.get("fichas", []):
            todas_las_metas.extend(ficha.get("metas", []))

    metricas['cumplimiento_promedio'] = (
        promedio_ponderado_metas(todas_las_metas) or 0
    )

    
    # Simular alertas activas
    metricas['alertas_activas'] = metricas['acuerdos_activos'] // 2
    
    # Simular tendencias positivas
    metricas['tendencias_positivas'] = metricas['acuerdos_activos'] // 3
    
    return metricas

def obtener_top_organismos_riesgo(db):
    """Obtiene top de organismos con mayor riesgo - SIN pandas"""
    
    organismos_riesgo = []
    
    # Agrupar acuerdos por organismo
    acuerdos_por_organismo = {}
    for acuerdo in db.values():
        organismo = acuerdo.get('organismo_nombre')
        if organismo:
            if organismo not in acuerdos_por_organismo:
                acuerdos_por_organismo[organismo] = []
            acuerdos_por_organismo[organismo].append(acuerdo)
    
    # Calcular puntaje de riesgo por organismo
    for organismo, acuerdos in acuerdos_por_organismo.items():
        # Métricas simples de riesgo
        metas_riesgo = 0
        cumplimiento_total = 0
        total_metas = 0
        acuerdos_activos = 0
        
        for acuerdo in acuerdos:
            if acuerdo.get('estado') in ['Borrador', 'En Revisión', 'Aprobado']:
                acuerdos_activos += 1
            
            for ficha in acuerdo.get('fichas', []):
                for meta in ficha.get('metas', []):
                    total_metas += 1
                    if meta.get('cumplimiento_calc') is not None:
                        cumplimiento_total += meta['cumplimiento_calc']
                        if (
                            isinstance(meta.get('cumplimiento_calc'), (int, float)) and
                            meta['cumplimiento_calc'] < CONFIG_METODOLOGIA["riesgo"]["umbral_bajo_cumplimiento"]
                        ):
                            metas_riesgo += 1

        cumplimiento_promedio = cumplimiento_total / total_metas if total_metas > 0 else 0
        
        # Puntaje de riesgo (más alto = más riesgo)
        # Fórmula: (metas en riesgo * 10) + (100 - cumplimiento) + (acuerdos activos * 5)
        cfg = CONFIG_METODOLOGIA["riesgo"]

        puntaje_riesgo = (
            metas_riesgo * cfg["peso_meta_riesgo"]
            + (CONFIG_METODOLOGIA["cumplimiento"]["valor_maximo"] - cumplimiento_promedio)
            + acuerdos_activos * cfg["peso_acuerdo_activo"]
        )

        # Determinar nivel de riesgo
        if puntaje_riesgo > 200:
            nivel = "🔴 Crítico"
        elif puntaje_riesgo > 150:
            nivel = "🟠 Alto"
        elif puntaje_riesgo > 100:
            nivel = "🟡 Medio"
        else:
            nivel = "🟢 Bajo"
        
        organismos_riesgo.append({
            'organismo': organismo,
            'metas_riesgo': metas_riesgo,
            'cumplimiento_promedio': cumplimiento_promedio,
            'puntaje_riesgo': puntaje_riesgo,
            'nivel_riesgo': nivel,
            'acuerdos_activos': acuerdos_activos,
            'recomendacion': f'{nivel}: {"Revisión urgente" if puntaje_riesgo > 150 else "Monitorear"} {metas_riesgo} metas en riesgo'
        })
    
    # Ordenar por puntaje de riesgo (descendente)
    organismos_riesgo.sort(key=lambda x: x['puntaje_riesgo'], reverse=True)
    
    return organismos_riesgo

def generar_datos_tendencia_mensual_simple():
    """Genera datos de tendencia mensual simulados - SIN pandas"""
    
    # Datos simulados para demostración
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    
    datos = []
    cumplimiento_base = 70
    
    for i, mes in enumerate(meses):
        # Simular tendencia creciente con variación estacional
        cumplimiento = cumplimiento_base + (i * 2.5) + (5 if i in [5, 6, 11] else 0)  # Mejora en junio, julio, diciembre
        metas_completadas = 8 + i + (2 if i in [5, 11] else 0)  # Más completadas en junio y diciembre
        
        datos.append({
            'Mes': mes,
            'Cumplimiento (%)': min(cumplimiento, 95),
            'Metas Completadas': metas_completadas,
            'Metas Nuevas': 3 + (i % 4)
        })
    
    # Convertir a DataFrame si pandas está disponible, sino a lista de diccionarios
    try:
        import pandas as pd
        return pd.DataFrame(datos)
    except:
        return datos  # Devolver lista de diccionarios

def generar_reporte_riesgos_html(resultados, acuerdo):
    """Genera reporte HTML de riesgos - SIN dependencias"""
    
    html = f"""
    <html>
    <head>
        <title>Reporte de Riesgos - {acuerdo.get('id', '')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .header {{ background: #f8d7da; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .metric {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .riesgo-alto {{ border-left: 4px solid #dc3545; }}
            .riesgo-medio {{ border-left: 4px solid #ffc107; }}
            .riesgo-bajo {{ border-left: 4px solid #28a745; }}
            .matriz-riesgo {{ display: flex; gap: 10px; margin: 20px 0; }}
            .nivel-riesgo {{ flex: 1; text-align: center; padding: 10px; border-radius: 5px; }}
            .critico {{ background: #dc3545; color: white; }}
            .alto {{ background: #fd7e14; color: white; }}
            .medio {{ background: #ffc107; }}
            .bajo {{ background: #28a745; color: white; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔴 Reporte de Análisis de Riesgos</h1>
            <h2>Acuerdo: {acuerdo.get('id', '')}</h2>
            <p><strong>Organismo:</strong> {acuerdo.get('organismo_nombre', '')}</p>
            <p><strong>Estado:</strong> {acuerdo.get('estado', 'N/A')}</p>
            <p><strong>Fecha de generación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p><strong>Generado por:</strong> Sistema CG - OPP</p>
        </div>
        
        <h3>📊 Resumen Ejecutivo</h3>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <div class="metric riesgo-alto">
                <strong>Metas sin ponderación:</strong><br>
                <span style="font-size: 24px;">{resultados['metas_sin_ponderacion']}</span>
            </div>
            <div class="metric riesgo-medio">
                <strong>Metas vencimiento próximo:</strong><br>
                <span style="font-size: 24px;">{resultados['metas_vencimiento_proximo']}</span>
            </div>
            <div class="metric riesgo-bajo">
                <strong>Metas bajo cumplimiento:</strong><br>
                <span style="font-size: 24px;">{resultados['metas_bajo_cumplimiento']}</span>
            </div>
            <div class="metric">
                <strong>Total riesgos identificados:</strong><br>
                <span style="font-size: 24px;">{resultados['total_riesgos']}</span>
            </div>
        </div>
        
        <h3>📈 Matriz de Riesgos</h3>
        <div class="matriz-riesgo">
            <div class="nivel-riesgo bajo">
                <strong>BAJO</strong><br>
                <span style="font-size: 20px;">{resultados['matriz_riesgos']['bajo']}</span>
            </div>
            <div class="nivel-riesgo medio">
                <strong>MEDIO</strong><br>
                <span style="font-size: 20px;">{resultados['matriz_riesgos']['medio']}</span>
            </div>
            <div class="nivel-riesgo alto">
                <strong>ALTO</strong><br>
                <span style="font-size: 20px;">{resultados['matriz_riesgos']['alto']}</span>
            </div>
            <div class="nivel-riesgo critico">
                <strong>CRÍTICO</strong><br>
                <span style="font-size: 20px;">{resultados['matriz_riesgos']['critico']}</span>
            </div>
        </div>
        
        <h3>📋 Detalle de Metas con Riesgos</h3>
        <table>
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Descripción</th>
                    <th>Estado</th>
                    <th>Nivel Riesgo</th>
                    <th>Problemas Detectados</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Agregar filas para cada meta con riesgo
    for meta in resultados.get('metas_detalle', []):
        html += f"""
                <tr>
                    <td>{meta.get('codigo', 'N/A')}</td>
                    <td>{meta.get('descripcion', 'N/A')}</td>
                    <td>{meta.get('estado', 'N/A')}</td>
                    <td>
                        <span class="nivel-riesgo {meta.get('nivel_riesgo', '').lower()}" 
                              style="padding: 5px 10px; display: inline-block;">
                            {meta.get('nivel_riesgo', 'N/A')}
                        </span>
                    </td>
                    <td>{', '.join(meta.get('problemas', []))}</td>
                </tr>
        """
    
    # Cerrar la tabla y el HTML
    html += """
            </tbody>
        </table>
        
        <h3>🚨 Recomendaciones</h3>
        <div class="metric">
            <ul>
                <li><strong>Priorizar atención</strong> a metas en riesgo crítico y alto</li>
                <li><strong>Revisar ponderaciones</strong> de metas sin asignar</li>
                <li><strong>Actualizar estado</strong> de metas con vencimiento próximo</li>
                <li><strong>Definir acciones correctivas</strong> para metas con bajo cumplimiento</li>
                <li><strong>Monitoreo continuo</strong> de todas las metas identificadas</li>
            </ul>
        </div>
        
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center;">
            <p><em>Reporte generado automáticamente por el Sistema de Control de Gestión - OPP</em></p>
            <p><small>Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small></p>
        </div>
    </body>
    </html>
    """
    
    return html

def main():
    st.set_page_config(
        page_title="Sistema CG - Uruguay", 
        layout="wide",
        page_icon="🏛️"
    )
    
    current_page = sidebar()
           
    # DEBUG (opcional - puedes quitar después)
    st.sidebar.write(f"🔍 Página: {current_page}")
    
    if current_page != "Inicio":
        st.session_state.home_subpage = "main"
        
    # NAVEGACIÓN - SISTEMA COMPLETO CON ROLES
   
    if current_page == "Login" or not st.session_state.get('user'):
        page_login()
    elif current_page == "Inicio":
        page_home_mejorada()  # ← NUEVA FUNCIÓN MEJORADA
    elif current_page == "Generar Acuerdos":
        page_agreements()
    elif current_page == "📋 Clonar Acuerdos":
        page_clonar_acuerdo()
    elif current_page == "📊 Listados de Acuerdos":
        page_listados_completo()
    elif current_page == "🎯 Carga por Metas":
        cargar_resultados_por_metas()
    elif current_page == "📈 Carga por Indicadores":
        cargar_resultados_por_indicadores()
    elif current_page == "Seguimiento de Indicadores":
        modulo_seguimiento_indicadores()
    elif current_page == "📈 Dashboard Control":
        mostrar_dashboard_seguro()
    elif current_page == "📊 Balanced Scorecard":
        mostrar_bsc_en_streamlit()
    elif current_page == "🎓 Tutorial":
        page_tutorial()        
    elif current_page == "Reportes":
        page_reportes()
    elif current_page == "Administración":
        page_admin()
    elif current_page == "📊 Análisis Comparativo":
        page_analisis_comparativo()
    elif current_page == "🔴 Análisis de Riesgos":
        page_analisis_riesgos_tendencias()        
    else:
        page_home_mejorada()

# ==================== EJECUCIÓN (LÍNEAS 222-224) ====================
if __name__ == "__main__":
    main()


