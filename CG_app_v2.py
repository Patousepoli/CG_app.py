# app.py - VERSIÓN CORREGIDA CON MANEJO DE PERMISOS

import streamlit as st
import sys
import os, json, hashlib, pandas as pd, secrets, datetime, csv, io, zipfile, shutil, uuid, time, tempfile
import base64
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import webbrowser  # ✅ ESTÁNDAR - NO INSTALAR

import warnings  # ← LIBRERÍA ESTÁNDAR, NO INSTALAR
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*MediaFileStorageError.*")

# 🔹 Constantes de configuración - VERSIÓN CORREGIDA
APP_TITLE = "Sistema de Compromisos de Gestión"

# Usar carpeta en directorio temporal para evitar problemas de permisos
DATA_DIR = os.path.join(tempfile.gettempdir(), "sistema_cg_data")

USERS_FILE = os.path.join(DATA_DIR, "users.json")
AGREEMENTS_FILE = os.path.join(DATA_DIR, "agreements.json")
AUDIT_FILE = os.path.join(DATA_DIR, "audit.json")
NATURALEZA_MAP_FILE = os.path.join(DATA_DIR, "naturaleza_map.json")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
COUNTERS_FILE = os.path.join(DATA_DIR, "counters.json")
LOGO_FILES = ["logo_opp.png", "logo.png"]
# 🆕 RANGOS POR DEFECTO FLEXIBLES 
RANGOS_DEFAULT = {"cumplido": 90, "parcial": 60}

# 🆕 INICIALIZACIÓN MEJORADA DE DIRECTORIOS
def initialize_directories():
    """Inicializa todos los directorios necesarios con verificación de permisos"""
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
    from datetime import datetime  # 🆕 IMPORTAR AQUÍ TAMBIÉN POR SEGURIDAD
    datos["metadata"]["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos["metadata"]["total"] = len(datos["indicadores"])
    with open('data/indicadores.json', 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def cargar_indicadores():
    """Interfaz para cargar nuevos indicadores"""
    st.header("📥 Carga de Nuevos Indicadores")
    
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
    
    # 🆕 FORMULARIO ORIGINAL DE CARGA (tu código actual)
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
            
        comentarios = st.text_area("Comentarios")
        
        if st.form_submit_button("💾 Guardar Indicador"):
            if nombre and valor is not None:
                datos = cargar_indicadores_json()
                
                # Generar nuevo ID (máximo ID existente + 1)
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
                    "timestamp": datetime.now().isoformat()
                }
                
                datos["indicadores"].append(nuevo_indicador)
                datos["metadata"]["total"] = len(datos["indicadores"])
                datos["metadata"]["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                guardar_indicadores_json(datos)
                st.success(f"✅ Indicador '{nombre}' guardado exitosamente")
                st.rerun()
            else:
                st.error("❌ Nombre y valor son obligatorios")

def componente_firma_imagen(key_suffix=""):
    """Subir imagen escaneada de firma"""
    
    st.markdown("**✍️ Firma Digitalizada**")
    
    # Subir imagen de firma
    firma_imagen = st.file_uploader(
        "Subir imagen de firma escaneada", 
        type=['png', 'jpg', 'jpeg'],
        key=f"upload_firma_{key_suffix}",
        help="Suba una imagen PNG/JPG de su firma escaneada"
    )
    
    # Mostrar preview si hay imagen
    if firma_imagen:
        st.image(firma_imagen, width=200, caption="Vista previa de la firma")
    
    # Datos del firmante
    nombre = st.text_input("Nombre completo*", key=f"nombre_{key_suffix}")
    cargo = st.text_input("Cargo*", key=f"cargo_{key_suffix}") 
    institucion = st.text_input("Institución*", key=f"institucion_{key_suffix}")
    
    return {
        "tiene_imagen_firma": firma_imagen is not None,
        "nombre_archivo_firma": firma_imagen.name if firma_imagen else None,
        "nombre": nombre,
        "cargo": cargo,
        "institucion": institucion,
        "fecha_captura": datetime.now().isoformat()
    }

def cargar_resultados_por_metas():
    st.header("📥 Carga de Resultados por Meta")
    
    # ✅ Mensaje informativo
    db = agreements_load()
    
    if not db:
        st.error("""
        ❌ No hay acuerdos en el sistema.
        
        **Para usar esta función:**
        1. Ve a **Acuerdos** y crea un acuerdo
        2. Agrega fichas y metas al acuerdo  
        3. Vuelve aquí para cargar resultados
        """)
        return
        
    # 1. SELECCIONAR ACUERDO
    acuerdos_activos = list(db.values())
    
    acuerdo_seleccionado = st.selectbox(
        "Seleccionar Acuerdo",
        options=[a["id"] for a in acuerdos_activos],
        format_func=lambda x: f"{x} - {db[x].get('organismo_nombre', 'Sin nombre')} ({db[x].get('estado', 'Sin estado')})"
    )
    
    if acuerdo_seleccionado:
        acuerdo = db[acuerdo_seleccionado]
        
        # 2. SELECCIONAR FICHA
        fichas = acuerdo.get("fichas", [])
        ficha_seleccionada = st.selectbox(
            "Seleccionar Ficha",
            options=[f["id"] for f in fichas],
            format_func=lambda x: f"{x} - {next((f['nombre'] for f in fichas if f['id'] == x), '')}"
        )
        
        if ficha_seleccionada:
            ficha = next((f for f in fichas if f["id"] == ficha_seleccionada), None)
            
            # 3. SELECCIONAR META
            metas = ficha.get("metas", [])
            meta_seleccionada = st.selectbox(
                "Seleccionar Meta",
                options=[m["id"] for m in metas],
                format_func=lambda x: f"Meta {next((m['numero'] for m in metas if m['id'] == x), '')}: {next((m['descripcion'] for m in metas if m['id'] == x), '')}"
            )
            
            if meta_seleccionada:
                meta = next((m for m in metas if m["id"] == meta_seleccionada), None)
                
                # 4. FORMULARIO DE CARGA
                with st.form("form_carga_resultado"):
                    st.subheader(f"Cargar resultado para: {meta['descripcion']}")
                    
                    # Mostrar info de la meta
                    col1, col2 = st.columns(2)
                    col1.write(f"**Valor objetivo:** {meta.get('valor_objetivo')}")
                    col1.write(f"**Unidad:** {meta.get('unidad')}")
                    col2.write(f"**Sentido:** {meta.get('sentido')}")
                    col2.write(f"**Rangos:** {len(meta.get('rango', []))} configurados")
                    
                    # Campo para valor alcanzado
                    valor_alcanzado = st.number_input(
                        "Valor Alcanzado",
                        value=float(meta.get('cumplimiento_valor', 0)) if meta.get('cumplimiento_valor') else 0.0,
                        step=0.1
                    )
                    
                    periodo = st.selectbox("Período", ["Mensual", "Trimestral", "Semestral", "Anual"])
                    fecha_medicion = st.date_input("Fecha de medición")
                    comentarios = st.text_area("Comentarios")
                    
                    if st.form_submit_button("💾 Guardar Resultado y Calcular"):
                        # Guardar valor
                        meta["cumplimiento_valor"] = str(valor_alcanzado)
                        meta["fecha_medicion"] = fecha_medicion.isoformat()
                        meta["periodo"] = periodo
                        meta["comentarios_cumplimiento"] = comentarios
                        
                        # CALCULAR CUMPLIMIENTO CON RANGOS DE LA META
                        meta["cumplimiento_calc"] = calcular_cumplimiento(meta)
                        
                        # Guardar acuerdo
                        agreements_save(db)
                        
                        st.success(f"✅ Resultado guardado - Cumplimiento: {meta['cumplimiento_calc']:.1f}%")
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
    opcion = st.sidebar.radio(
        "Navegación",
        [
            "📈 Dashboard",
            "📥 Cargar Indicadores", 
            "🎯 Cargar Resultados por Meta",
            "📄 Generar Reporte",
            "📄 Generar Reporte Simple",  # 🆕 NUEVA OPCIÓN
            "⚙️ Ver Datos"
        ]
    )
   
    if opcion == "📈 Dashboard":
        dashboard_indicadores()
    elif opcion == "📥 Cargar Indicadores":
        cargar_indicadores()
    elif opcion == "🎯 Cargar Resultados por Meta":
        cargar_resultados_por_metas()  # ← NUEVA función    
    elif opcion == "📄 Generar Reporte":
        mostrar_reporte_completo()  # ✅ Esta función sí muestra la interfaz
    elif opcion == "📄 Generar Reporte Simple":  # 🆕 NUEVA OPCIÓN
        generar_reporte_html_simple()    
    elif opcion == "⚙️ Ver Datos":
        st.header("📊 Datos en JSON")
        datos = cargar_indicadores_json()
        st.json(datos) 

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
    
    @st.cache_data(ttl=30, show_spinner=False)
    def cargar_seguimientos(self):
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

# ==================== FUNCIONES DEL DASHBOARD (LÍNEAS 47-150) ====================
@st.cache_data(ttl=60, show_spinner=False)
def mostrar_dashboard_seguro():
    """Dashboard que FUNCIONA SEGURO sin instalaciones adicionales"""
    
    st.title("📈 Dashboard de Control - Compromisos de Gestión")
    
    # ==================== MÉTRICAS PRINCIPALES ====================
    st.header("📊 Métricas Principales")
    
    # Cargar datos reales si existen, sino usar ejemplo
    gestor = GestorSeguimientos()
    seguimientos = gestor.cargar_seguimientos()
    
    if seguimientos["seguimientos"]:
        # 📍 DATOS REALES - cuando tengas seguimientos cargados
        total_seguimientos = len(seguimientos["seguimientos"])
        # Aquí irían cálculos reales de cumplimiento
        metricas = {
            "total_seguimientos": total_seguimientos,
            "cumplimiento_promedio": 85.3,  # Por ahora estático
            "metas_completadas": total_seguimientos,  # Ejemplo
            "metas_pendientes": 0
        }
    else:
        # 📍 DATOS DE EJEMPLO - hasta que tengas datos reales
        metricas = {
            "total_seguimientos": 0,
            "cumplimiento_promedio": 0,
            "metas_completadas": 0,
            "metas_pendientes": 0
        }
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Seguimientos", metricas["total_seguimientos"])
    with col2:
        st.metric("Cumplimiento Promedio", f"{metricas['cumplimiento_promedio']}%")
    with col3:
        st.metric("Metas Completadas", metricas["metas_completadas"])
    with col4:
        st.metric("Metas Pendientes", metricas["metas_pendientes"])
    
    # ==================== GRÁFICOS SIMPLES ====================
    st.header("📈 Visualización de Datos")
    
    # 📍 GRÁFICO 1: Tendencia (Streamlit nativo)
    st.subheader("Tendencia de Cumplimiento")
    
    if seguimientos["seguimientos"]:
        # Cuando tengas datos reales, aquí los procesarías
        datos_tendencia = pd.DataFrame({
            'Periodo': ['Ene-Mar', 'Abr-Jun', 'Jul-Sep', 'Oct-Dic'],
            'Cumplimiento': [75, 80, 90, 85]
        })
    else:
        datos_tendencia = pd.DataFrame({
            'Periodo': ['Cargue datos para ver gráficos'],
            'Cumplimiento': [0]
        })
    
    st.line_chart(datos_tendencia.set_index('Periodo'))
    
    # 📍 GRÁFICO 2: Barras (Streamlit nativo)
    st.subheader("Cumplimiento por Meta")
    
    if seguimientos["seguimientos"]:
        datos_metas = pd.DataFrame({
            'Meta': ['Capacitación', 'Eficiencia', 'Calidad', 'Innovación'],
            'Cumplimiento': [85, 78, 92, 65]
        })
    else:
        datos_metas = pd.DataFrame({
            'Meta': ['Sin datos aún'],
            'Cumplimiento': [0]
        })
    
    st.bar_chart(datos_metas.set_index('Meta'))
    
    # ==================== TABLA DE SEGUIMIENTOS ====================
    st.header("📋 Seguimientos Recientes")
    
    if seguimientos["seguimientos"]:
        # Crear tabla con datos reales
        datos_tabla = []
        for seg in seguimientos["seguimientos"][-10:]:  # Últimos 10
            datos_tabla.append({
                "ID": seg["id"],
                "Fecha": seg["fecha_creacion"][:10],
                "Estado": seg["estado"],
                "Responsable": seg.get("responsable", "No especificado")
            })
        
        df = pd.DataFrame(datos_tabla)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("📝 No hay seguimientos cargados aún. Use 'Carga Resultados' para comenzar.")
    
    # ==================== ANÁLISIS Y RECOMENDACIONES ====================
    st.header("📋 Análisis Ejecutivo")
    
    cumplimiento_promedio = metricas["cumplimiento_promedio"]
    
    if cumplimiento_promedio >= 90:
        estado = "✅ EXCELENTE - Cumplimiento sobresaliente"
        recomendacion = "Mantener las estrategias actuales"
    elif cumplimiento_promedio >= 80:
        estado = "🟢 BUENO - Cumplimiento satisfactorio"
        recomendacion = "Focalizar en metas con menor cumplimiento"
    elif cumplimiento_promedio >= 70:
        estado = "🟡 REGULAR - Necesita mejora"
        recomendacion = "Revisar estrategias de metas críticas"
    else:
        estado = "🔴 INSUFICIENTE - Acción correctiva necesaria"
        recomendacion = "Reunión urgente con comisión de seguimiento"
    
    st.info(f"**Estado General:** {estado}")
    st.success(f"**Recomendación:** {recomendacion}")
    
    # ==================== ACCIONES RÁPIDAS ====================
    st.header("🚀 Acciones Disponibles")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Cargar Nuevos Resultados", type="primary"):
            abrir_carga_resultados()
    
    with col2:
        if st.button("🔄 Actualizar Dashboard"):
            st.rerun()
    
    with col3:
        if st.button("📄 Exportar Reporte CSV"):
            if seguimientos["seguimientos"]:
                df = pd.DataFrame(seguimientos["seguimientos"])
                df.to_csv("reporte_seguimientos.csv", index=False, encoding='utf-8')
                st.success("Reporte exportado como 'reporte_seguimientos.csv'")
            else:
                st.warning("No hay datos para exportar")

# ==================== FUNCIÓN MAIN (LÍNEAS 152-220) ====================
def main():
    st.set_page_config(page_title="Sistema CG", layout="wide")
    
    # Menú principal en sidebar
    st.sidebar.title("🇺🇾 Sistema CG")
    menu_option = st.sidebar.selectbox(
        "Menú Principal",
        [
            "Inicio", 
            "Seguimiento de Indicadores",
            "Análisis Existente", 
            "Generar Acuerdos",
            "📊 Carga Resultados",
            "📈 Dashboard Control",  # 📍 NUEVA OPCIÓN
            "Reportes"
        ]
    )
    
    if menu_option == "Inicio":
        st.title("Sistema de Compromisos de Gestión")
        st.write("Bienvenido al sistema oficial del Estado Uruguayo")

    elif menu_option == "Seguimiento Indicadores":
        # ... tu código existente de análisis
        st.title("Seguimiento Indicadores")
        # ... (mantener tu código actual)    
    
    elif menu_option == "Análisis Existente":
        # ... tu código existente de análisis
        st.title("Análisis Existente")
        # ... (mantener tu código actual)
        
    elif menu_option == "Generar Acuerdos":
        # ... tu código existente de generación de acuerdos
        st.title("Generar Nuevos Acuerdos")
        # ... (mantener tu código actual)
        
    elif menu_option == "📊 Carga Resultados":
        st.title("📊 Carga de Resultados de Seguimiento")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Instrucciones:")
            st.write("""
            1. Haga clic en 'Abrir Formulario' para cargar resultados
            2. Complete los indicadores de cada meta
            3. El sistema calculará automáticamente los cumplimientos
            4. Envíe los resultados a la Comisión de Seguimiento
            """)
            
            if st.button("🖥️ Abrir Formulario de Carga", type="primary"):
                abrir_carga_resultados()
        
        with col2:
            st.subheader("Estadísticas")
            gestor = GestorSeguimientos()
            seguimientos = gestor.cargar_seguimientos()
            st.metric("Seguimientos Realizados", len(seguimientos["seguimientos"]))
    
    # 📍 NUEVA SECCIÓN - DASHBOARD DE CONTROL
    elif menu_option == "📈 Dashboard Control":
        mostrar_dashboard_seguro()  # 📍 LLAMAR AL DASHBOARD SEGURO
    
    elif menu_option == "Reportes":
        # ... tu código existente de reportes
        st.title("Reportes del Sistema")
        # ... (mantener tu código actual)

# 🔹 Funciones de utilidad para generar códigos de ficha CORREGIDAS

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
    
    # 🆕 SECCIÓN DE FIRMAS - AGREGAR JUSTO DESPUÉS DE LAS CLAÚSULAS
    html_content += """
    <div class="section" style="page-break-before: always; margin-top: 50px;">
        <h3 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #007bff; padding-bottom: 15px;">
            📝 FIRMAS DEL ACUERDO
        </h3>
        
        <div style="display: flex; justify-content: space-between; margin: 50px 0; align-items: flex-start;">
            <!-- FIRMA CONTRAPARTE -->
            <div style="text-align: center; width: 45%; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;">
                <h4 style="color: #34495e; margin-bottom: 30px;">👤 CONTRAPARTE</h4>
                
                <div style="border-bottom: 2px solid #7f8c8d; padding: 80px 20px 30px 20px; margin: 20px 0; min-height: 120px; background: white;">
                    <p style="color: #95a5a6; font-style: italic;">Espacio para firma y sello</p>
                </div>
                
                <div style="text-align: left; margin-top: 20px;">
                    <p><strong>Nombre:</strong> ________________________________</p>
                    <p><strong>Cargo:</strong> _________________________________</p>
                    <p><strong>Institución:</strong> ___________________________</p>
                </div>
            </div>
            
            <!-- FIRMA INSTITUCIÓN -->
            <div style="text-align: center; width: 45%; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;">
                <h4 style="color: #34495e; margin-bottom: 30px;">👤 INSTITUCIÓN</h4>
                
                <div style="border-bottom: 2px solid #7f8c8d; padding: 80px 20px 30px 20px; margin: 20px 0; min-height: 120px; background: white;">
                    <p style="color: #95a5a6; font-style: italic;">Espacio para firma y sello</p>
                </div>
                
                <div style="text-align: left; margin-top: 20px;">
                    <p><strong>Nombre:</strong> ________________________________</p>
                    <p><strong>Cargo:</strong> _________________________________</p>
                    <p><strong>Institución:</strong> ___________________________</p>
                </div>
            </div>
        </div>
        
        <!-- FECHA DE FIRMA -->
        <div style="text-align: center; margin-top: 40px; padding: 20px; background: #e8f4f8; border-radius: 8px;">
            <p style="font-size: 16px; font-weight: bold; color: #2c3e50;">
                FECHA DE FIRMA: _________________________
            </p>
            <p style="color: #7f8c8d; font-size: 14px; margin-top: 10px;">
                (dd/mm/aaaa)
            </p>
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
    return f"AC_{base}_{year}"

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
    return load_json(AGREEMENTS_FILE, {})

def agreements_save(db):
    """
    💾 Guarda acuerdos en la base de datos y limpia caches relevantes
    """
    try:
        # 🆕 LIMPIAR CACHES DE STREAMLIT ANTES DE GUARDAR
        try:
            # Limpiar cache de datos
            st.cache_data.clear()
        except:
            pass
        
        # 🆕 GUARDAR CON VERIFICACIÓN
        save_json(AGREEMENTS_FILE, db)
        
        # 🆕 VERIFICAR QUE SE GUARDÓ CORRECTAMENTE
        if os.path.exists(AGREEMENTS_FILE):
            file_size = os.path.getsize(AGREEMENTS_FILE)
            st.success(f"💾 Acuerdos guardados correctamente (tamaño: {file_size} bytes)")
            
            # 🆕 FORZAR ACTUALIZACIÓN DE DATOS EN MEMORIA
            global agreements
            agreements = agreements_load()  # O como cargues tus acuerdos
            
            # 🆕 AGREGAR ESTO - LIMPIAR INDICADORES SI NO HAY ACUERDOS
            if len(db) == 0:  # Si no hay acuerdos
                try:
                    limpiar_indicadores()
                except:
                    pass  # Si no existe la función aún, ignorar
            
            return True
        else:
            st.error("❌ Error: El archivo no se creó correctamente")
            return False
            
    except Exception as e:
        st.error(f"❌ Error al guardar acuerdos: {str(e)}")
        return False

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
    return datetime.date.today().isoformat()

def dt_parse(dstr: str) -> Optional[datetime.date]:
    try:
        return date.fromisoformat(dstr)
    except Exception:
        return None

def default_agreement(created_by, external_prefix:Optional[str]=None, año_seleccionado:Optional[int]=None):
    # Usar el año seleccionado, o el año actual por defecto
    año = año_seleccionado if año_seleccionado is not None else datetime.today().year
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
        
        import datetime
        
        # 🆕 ID ÚNICO BASADO EN TIMESTAMP - NO DEPENDE DE CONTAR FICHAS
        timestamp = int(datetime.datetime.now().timestamp() * 1000)
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
                vencimiento = f"{datetime.datetime.now().year}-12-31"
            
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
                "vencimiento": vencimiento or f"{datetime.datetime.now().year}-12-31",
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
    
    # 🆕 CALCULAR PORCENTAJE BASE SEGÚN SENTIDO
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
    
    # 🆕 CASO 1: SIN RANGOS - CUMPLIMIENTO LINEAL DIRECTO
    if not rango:
        return max(0.0, min(100.0, base_pct))
    
    # 🆕 PREPARAR RANGOS VÁLIDOS
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
    
    # 🆕 CASO 2: SOLO UN RANGO - CUMPLIMIENTO LINEAL ENTRE 0% Y EL PORCENTAJE DEL RANGO
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
    
    # 🆕 ORDENAR RANGOS POR VALOR MÍNIMO
    rangos_ordenados.sort(key=lambda x: x["min"])
    
    # 🆕 CASO 3: MÚLTIPLES RANGOS - BUSCAR RANGO EXACTO O INTERPOLAR
    for i, rg in enumerate(rangos_ordenados):
        if rg["min"] <= base_pct <= rg["max"]:
            # 🆕 VERIFICAR SI PODEMOS INTERPOLAR DENTRO DEL RANGO
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
    
    # 🆕 CASO 4: INTERPOLACIÓN ENTRE RANGOS (VALOR ENTRE RANGOS)
    for i in range(len(rangos_ordenados) - 1):
        rg_actual = rangos_ordenados[i]
        rg_siguiente = rangos_ordenados[i + 1]
        
        # Si base_pct está entre el máximo del rango actual y el mínimo del siguiente
        if rg_actual["max"] < base_pct < rg_siguiente["min"]:
            # Calcular interpolación lineal entre rangos
            rango_total = rg_siguiente["min"] - rg_actual["max"]
            progreso = (base_pct - rg_actual["max"]) / rango_total
            porcentaje_interpolado = rg_actual["porcentaje"] + progreso * (rg_siguiente["porcentaje"] - rg_actual["porcentaje"])
            return max(0.0, min(100.0, porcentaje_interpolado))
    
    # 🆕 CASO 5: VALORES FUERA DE LOS RANGOS DEFINIDOS
    if base_pct < rangos_ordenados[0]["min"]:
        # Por debajo del primer rango - progreso lineal desde 0
        primer_rango = rangos_ordenados[0]
        progreso = base_pct / primer_rango["min"] if primer_rango["min"] > 0 else 0.0
        return max(0.0, min(100.0, progreso * primer_rango["porcentaje"]))
    elif base_pct > rangos_ordenados[-1]["max"]:
        # Por encima del último rango - usar el porcentaje máximo
        return max(0.0, min(100.0, rangos_ordenados[-1]["porcentaje"]))
    
    return 0.0

def clasificar_cumplimiento_meta(meta: Dict[str, Any]) -> str:
    """
    Clasifica una meta según sus rangos de cumplimiento configurables
    Retorna: 'cumplida', 'parcial', o 'no_cumplida'
    """
    cumplimiento = meta.get("cumplimiento_calc")
    
    # Si no hay cumplimiento calculado, se considera no cumplida
    if cumplimiento is None or not isinstance(cumplimiento, (int, float)):
        return "no_cumplida"
    
    # 🆕 USAR RANGOS CONFIGURADOS DE LA META O LOS POR DEFECTO
    rangos = meta.get("rangos_cumplimiento", RANGOS_DEFAULT)
    
    cumplido_min = rangos.get("cumplido", 90)
    parcial_min = rangos.get("parcial", 60)
    
    if cumplimiento >= cumplido_min:
        return "cumplida"
    elif cumplimiento >= parcial_min:
        return "parcial"
    else:
        return "no_cumplida"
    
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

def validar_ponderaciones_ficha(ficha: Dict[str,Any], agr: Dict[str,Any]):
    metas = ficha.get("metas",[])
    per_sums: Dict[str,float] = {}
    for m in metas:
        lbl = periodo_label(m)
        per_sums[lbl] = per_sums.get(lbl,0.0) + float(m.get("ponderacion",0.0))
        
    for lbl, s in per_sums.items():
        if abs(s - 100.0) > 1e-6:
            st.warning(f"⚠️ En {ficha['id']} ({ficha.get('nombre','')}) el período {lbl} suma {s:.1f}% (debe sumar 100%).")

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
            st.markdown(f"### {APP_TITLE}")
    else:
        st.markdown("## OPP - Sistema de Compromisos de Gestión")
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

def page_login():
    header_with_logo()
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
    st.header("Acuerdos")
    
    # 🆕 VERSIÓN SIN FILTROS - CARGA DIRECTA
    db = agreements_load()
    user = st.session_state.user

    if not db:
        st.info("No hay acuerdos para mostrar")
    
    # CREACIÓN DE NUEVOS ACUERDOS (mantener tu código original)
    with st.expander("➕ Crear nuevo acuerdo", expanded=False):
        cola, colb = st.columns([2,2])
        use_custom = cola.checkbox("Personalizar código (p.ej. OPP)", value=False)
        external_prefix = None
        
        if use_custom:
            external_prefix = cola.text_input("Prefijo externo (p.ej. OPP)").strip()
            
        if colb.button("Crear nuevo acuerdo"):
            agr = default_agreement(
                st.session_state.user["username"], 
                external_prefix=external_prefix if external_prefix else None,
                año_seleccionado=fy  # ← Pasar el año del filtro
            )
            
            db[agr["id"]] = agr
            agreements_save(db)
            audit_log("create_agreement", {"id": agr["id"], "by": st.session_state.user["username"]})
            st.success(f"Acuerdo {agr['id']} creado")
            st.rerun()
    
    # 🆕 SIN FILTROS TEMPORALES - MOSTRAR TODOS LOS ACUERDOS
    years = sorted({a.get("año", date.today().year) for a in db.values()}) if db else [date.today().year]
    fy = st.selectbox("Filtrar por año", options=years, index=len(years)-1)
    ft = st.selectbox("Tipo de compromiso", options=TIPO_COMPROMISO, 
                     index=safe_index(TIPO_COMPROMISO, TIPO_COMPROMISO[0]))
    
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
            if st.button("📂 Abrir", key=f"open_{current_agr_id}"):
                st.session_state["open_agr"] = current_agr_id
                st.rerun()
                
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
                  
    # ------------------------------------------------------------------
    # Expander con herramientas avanzadas
    # ------------------------------------------------------------------
    
    if "open_agr" in st.session_state and st.session_state["open_agr"] in db:
        agr = db[st.session_state["open_agr"]]
        editable = True
        if agr.get("estado")=="Aprobado" and user["role"] not in ["Administrador","Supervisor OPP", "Responsable de Acuerdo"]:
            editable = False
            st.info("Acuerdo aprobado. Edición limitada.")
            
        # === CÓDIGO DE SEGURIDAD AQUÍ ===
        # Configurar columnas según permisos
        if st.session_state.user["role"] in ["Administrador", "Supervisor OPP"]:
            col_top1, col_top2, col_top3 = st.columns([4,1,1]) # 3 columnas si tiene permisos
        else:
            col_top1, col_top2 = st.columns([4,1]) # 2 columnas si no tiene permisos
        # === FIN CÓDIGO DE SEGURIDAD ===
            
        col_top1.subheader(f"Editar Acuerdo: {agr['id']}")
        if col_top2.button("💾 Guardar Todo"):
            db[agr["id"]] = agr; agreements_save(db); audit_log("save_agreement", {"id":agr["id"], "by":user["username"]}); st.success("Guardado"); st.rerun()
            
        # === CÓDIGO DE SEGURIDAD AQUÍ ===
        # Solo mostrar botón de eliminar si el usuario tiene permisos
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
        # === FIN CÓDIGO DE SEGURIDAD ===
            
        with st.expander("Datos del Acuerdo", expanded=True):
            agr["tipo_compromiso"] = st.selectbox("Tipo de Compromiso", TIPO_COMPROMISO, index=safe_index(TIPO_COMPROMISO, agr.get("tipo_compromiso", TIPO_COMPROMISO[0])), disabled=not editable)
            agr["organismo_tipo"] = st.selectbox("Tipo de Organismo", ORGANISMO_TIPOS, index=safe_index(ORGANISMO_TIPOS, agr.get("organismo_tipo", ORGANISMO_TIPOS[0])), disabled=not editable)
            agr["organismo_nombre"] = st.text_input("Organismo", value=agr.get("organismo_nombre",""), disabled=not editable)
            natmap = load_json(NATURALEZA_MAP_FILE, {})
            def_auto_nat = natmap.get(agr.get("organismo_nombre",""), "")
            agr["naturaleza_juridica"] = st.text_input("Naturaleza Jurídica", value=agr.get("naturaleza_juridica", def_auto_nat), disabled=not editable)
            col4, col5, col6 = st.columns(3)
            agr["año"] = col4.number_input("Año", value=int(agr.get("año", date.today().year)), step=1, disabled=not editable)
            agr["vigencia_desde"] = col5.date_input("Vigencia desde", value=dt_parse(agr.get("vigencia_desde")) or datetime.date(agr["año"],1,1), disabled=not editable).isoformat()
            agr["vigencia_hasta"] = col6.date_input("Vigencia hasta", value=dt_parse(agr.get("vigencia_hasta")) or datetime.date(agr["año"],12,31), disabled=not editable).isoformat()
            agr["organismo_enlace"] = st.text_input("Organismo de Enlace", value=agr.get("organismo_enlace",""), disabled=not editable)
            agr["objeto"] = st.text_area("Objeto", value=agr.get("objeto",""), disabled=not editable)
            agr["partes_firmantes"] = st.text_area("Partes firmantes", value=agr.get("partes_firmantes",""), disabled=not editable)
            agr["normativa_vigente"] = st.text_area("Normativa Vigente", value=agr.get("normativa_vigente",""), disabled=not editable)
            agr["antecedentes"] = st.text_area("Antecedentes", value=agr.get("antecedentes",""), disabled=not editable)
            
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
                height=150  # 👈 Más alto por el texto extenso
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

        # ✅ === SECCIÓN DE FIRMAS - INSERTAR AQUÍ ===
        st.markdown("---")
        st.subheader("📝 Firmas del Acuerdo")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👤 Contraparte**")
            firma_contraparte = componente_firma_imagen("contraparte")
                
        with col2:
            st.markdown("**👤 Institución**") 
            firma_institucion = componente_firma_imagen("institucion")

        fecha_firma = st.date_input("Fecha de firma del acuerdo*", disabled=not editable)

        # Guardar datos de firmas en el acuerdo
        agr["firmas"] = {
            "contraparte": firma_contraparte,
            "institucion": firma_institucion,
            "fecha_firma": fecha_firma.strftime("%Y-%m-%d") if fecha_firma else None
        }
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
                        disabled=not editable
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
                    if editable and st.button("➕ Agregar meta", key=f"add_meta_{agr['id']}_{fi_index}"):
                        numero = len(fi.get("metas", [])) + 1
                        mid = f"{fi['id']}_M{numero}"
    
                        meta = {
                            "id": mid,
                            "numero": numero,
                            "unidad": "%",
                            "valor_objetivo": "",
                            "sentido": ">=",
                            "descripcion": f"Meta {numero}",
                            "frecuencia": "Anual",
                            "vencimiento": f"{agr.get('año')}-12-31",
                            "es_hito": False,
                            "rango": [],
                            "rangos_cumplimiento": RANGOS_DEFAULT.copy(),  # 🆕 AGREGAR RANGOS FLEXIBLES
                            "ponderacion": 0.0,
                            "cumplimiento_valor": "",
                            "cumplimiento_calc": None,
                            "observaciones": "",
                            "estado": "No Iniciada",
                            "historial_estados": []
                        }
                        fi.setdefault("metas", []).append(meta)
                        agreements_save(db)
                        st.rerun()
                        
                    if fi.get("metas"):
                        for m_index, m in enumerate(fi.get("metas")):
                            with st.expander(f"🎯 Meta {m.get('numero', m_index+1)} - {m.get('descripcion','(sin descripción)')}", expanded=False):
                                col_m1, col_m2 = st.columns(2)
                                m["descripcion"] = col_m1.text_input("Descripción", value=m.get("descripcion",""), key=f"desc_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                unidad_opts = ["%","Número","Días","Sí/No","Otro"]
                                m["unidad"] = col_m2.selectbox("Unidad", options=unidad_opts, index=safe_index(unidad_opts, m.get("unidad","%")), key=f"unidad_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                col_m3, col_m4 = st.columns(2)
                                m["valor_objetivo"] = col_m3.text_input("Valor objetivo", value=m.get("valor_objetivo",""), key=f"obj_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                sentido_opts = [">=", "<=", "=="]
                                m["sentido"] = col_m4.selectbox("Sentido", options=sentido_opts, index=safe_index(sentido_opts, m.get("sentido",">=")), key=f"sentido_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                col_m5, col_m6 = st.columns(2)
                                freq_opts = ["Anual","Semestral","Trimestral","Mensual"]
                                m["frecuencia"] = col_m5.selectbox("Frecuencia", options=freq_opts, index=safe_index(freq_opts, m.get("frecuencia","Anual")), key=f"freq_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                venc = dt_parse(m.get("vencimiento", f"{agr.get('año')}-12-31")) or datetime.date(agr.get("año"),12,31)
                                m["vencimiento"] = col_m6.date_input("Vencimiento", value=venc, key=f"venc_{agr['id']}_{fi_index}_{m_index}", disabled=not editable).isoformat()
                                m["es_hito"] = st.checkbox("Es hito", value=m.get("es_hito", False), key=f"hito_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                
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
                                m["cumplimiento_valor"] = col_p2.text_input("Valor de cumplimiento", value=m.get("cumplimiento_valor",""), key=f"cumpl_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                
                                if st.button("📊 Calcular cumplimiento", key=f"calc_{agr['id']}_{fi_index}_{m_index}"):
                                    m["cumplimiento_calc"] = calcular_cumplimiento(m)
                                    if m["cumplimiento_calc"] is not None:
                                        st.success(f"Cumplimiento: {m['cumplimiento_calc']:.2f}%")
                                    else:
                                        st.warning("No se pudo calcular cumplimiento")
                                        
                                m["observaciones"] = st.text_area("Observaciones", value=m.get("observaciones",""), key=f"obsmeta_{agr['id']}_{fi_index}_{m_index}", disabled=not editable)
                                
                                # 🆕 SECCIÓN DE CONFIGURACIÓN DE RANGOS (AGREGAR DESPUÉS DE LOS CAMPOS EXISTENTES DE LA META)
                                st.markdown("---")
                                st.subheader("⚙️ Rangos de Clasificación")

                                # Asegurar que la meta tenga rangos
                                if "rangos_cumplimiento" not in m:
                                    m["rangos_cumplimiento"] = RANGOS_DEFAULT.copy()

                                col_rango1, col_rango2, col_rango3 = st.columns(3)

                                with col_rango1:
                                    cumplido_actual = m["rangos_cumplimiento"].get("cumplido", 90)
                                    nuevo_cumplido = st.number_input(
                                        "✅ Cumplido (≥ %)", 
                                        min_value=0, max_value=100, 
                                        value=int(cumplido_actual),
                                        key=f"cumplido_{agr['id']}_{fi_index}_{m_index}",
                                        help="Porcentaje mínimo para considerar esta meta como CUMPLIDA"
                                    )
                                    m["rangos_cumplimiento"]["cumplido"] = nuevo_cumplido

                                with col_rango2:
                                    parcial_actual = m["rangos_cumplimiento"].get("parcial", 60)
                                    nuevo_parcial = st.number_input(
                                        "🟡 Parcial (≥ %)", 
                                        min_value=0, max_value=100, 
                                        value=int(parcial_actual),
                                        key=f"parcial_{agr['id']}_{fi_index}_{m_index}",
                                        help="Porcentaje mínimo para considerar esta meta como PARCIALMENTE CUMPLIDA"
                                    )
                                    m["rangos_cumplimiento"]["parcial"] = nuevo_parcial

                                with col_rango3:
                                    st.write("**🔴 No Cumplido:**")
                                    st.write(f"< {nuevo_parcial}%")
    
                                    if st.button("🔄 Valores por defecto", key=f"reset_rangos_{agr['id']}_{fi_index}_{m_index}"):
                                        m["rangos_cumplimiento"] = RANGOS_DEFAULT.copy()
                                        st.rerun()

                                # 🆕 MOSTRAR RANGOS ACTUALES
                                st.info(f"**Rangos actuales:** ✅ ≥{nuevo_cumplido}% | 🟡 ≥{nuevo_parcial}% | 🔴 <{nuevo_parcial}%")

                                colmA, colmB = st.columns([1,1])
                                if colmA.button("💾 Guardar meta", key=f"save_meta_{agr['id']}_{fi_index}_{m_index}", disabled=not editable):
                                    agreements_save(db); audit_log("save_meta", {"agr":agr["id"], "ficha":fi["id"], "meta":m["id"], "by":user["username"]}); st.success("Meta guardada")
                                if colmB.button("🗑️ Eliminar meta", key=f"del_meta_{agr['id']}_{fi_index}_{m_index}"):
                                    if st.session_state.get(f"confirm_del_meta_{m['id']}") != True:
                                        st.session_state[f"confirm_del_meta_{m['id']}"] = True
                                        st.warning("Confirma eliminar meta (presiona eliminar nuevamente).")
                                    else:
                                        fi["metas"].pop(m_index); agreements_save(db); audit_log("delete_meta", {"agr":agr["id"], "ficha":fi["id"], "meta":m["id"], "by":user["username"]}); st.success("Meta eliminada"); st.rerun()
                                        
                    # 🆕 CORREGIR CLAVE DEL BOTÓN DE VALIDACIÓN
                    if st.button("✅ Validar ponderaciones de ficha", key=f"valid_{agr['id']}_{fi_index}_{int(time.time())}"):
                        validar_ponderaciones_ficha(fi, agr)
                        
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

def page_reportes():
    require_login()
    
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
    
    # 🆕 SECCIÓN DE MÉTRICAS DE CUMPLIMIENTO MEJORADA
    if acuerdos_filtrados:
        st.subheader("📈 Métricas de Cumplimiento")
    
        # Calcular métricas generales
        metricas_totales = calcular_metricas_globales(acuerdos_filtrados)
    
        # 🆕 MÉTRICAS MEJORADAS CON BARRAS DE PROGRESO
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
    
        with col_metric1:
            st.metric(
                "Cumplimiento Promedio", 
                f"{metricas_totales['cumplimiento_promedio']:.1f}%"
            )
            # Barra de progreso
            st.progress(metricas_totales['cumplimiento_promedio'] / 100)
    
        with col_metric2:
            st.metric("Acuerdos Evaluados", metricas_totales['total_acuerdos'])
    
        with col_metric3:
            st.metric("Total Metas", metricas_totales['total_metas'])
    
        with col_metric4:
            st.metric("Metas Cumplidas", 
                 f"{metricas_totales['metas_cumplidas']} ({metricas_totales['porcentaje_cumplidas']:.1f}%)")
    
        # 🆕 GRÁFICO DE DISTRIBUCIÓN DE CUMPLIMIENTO (SIN MATPLOTLIB)
        with st.expander("📊 Distribución de Cumplimiento de Metas", expanded=True):    
            col_dist1, col_dist2 = st.columns(2)
    
            with col_dist1:
                # 🆕 GRÁFICO DE BARRAS HORIZONTAL CON STREAMLIT NATIVO
                datos_grafico = {
                    'Categoría': ['Cumplidas', 'Parciales', 'No Cumplidas'],
                    'Cantidad': [
                        metricas_totales['metas_cumplidas'],
                        metricas_totales['metas_parciales'],
                        metricas_totales['metas_no_cumplidas']
                    ],
                    'Porcentaje': [
                        metricas_totales['porcentaje_cumplidas'],
                        metricas_totales['porcentaje_parciales'],
                        metricas_totales['porcentaje_no_cumplidas']
                    ]
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
                st.write(f"✅ **Cumplidas:** {metricas_totales['metas_cumplidas']} ({metricas_totales['porcentaje_cumplidas']:.1f}%)")
                st.write(f"🟡 **Parciales:** {metricas_totales['metas_parciales']} ({metricas_totales['porcentaje_parciales']:.1f}%)")
                st.write(f"🔴 **No Cumplidas:** {metricas_totales['metas_no_cumplidas']} ({metricas_totales['porcentaje_no_cumplidas']:.1f}%)")
        
                # 🆕 INDICADORES DE ESTADO
                if metricas_totales['porcentaje_cumplidas'] >= 80:
                    st.success("🎉 **Excelente cumplimiento general**")
                elif metricas_totales['porcentaje_cumplidas'] >= 60:
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

def calcular_cumplimiento_acuerdo(agr: Dict[str, Any]) -> Optional[float]:
    """Calcula el cumplimiento ponderado de un acuerdo"""
    total_ponderacion = 0.0
    total_ponderado = 0.0
    metas_con_datos = 0
    
    for ficha in agr.get("fichas", []):
        for meta in ficha.get("metas", []):
            # Calcular cumplimiento si no está calculado
            if meta.get("cumplimiento_calc") is None:
                meta["cumplimiento_calc"] = calcular_cumplimiento(meta)
            
            if meta.get("cumplimiento_calc") is not None:
                ponderacion = float(meta.get("ponderacion", 0.0))
                cumplimiento = meta["cumplimiento_calc"]
                
                total_ponderacion += ponderacion
                total_ponderado += cumplimiento * ponderacion
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
                
                # 🆕 CLASIFICACIÓN FLEXIBLE (REEMPLAZA LOS RANGOS FIJOS)
                clasificacion = clasificar_cumplimiento_meta(meta)
                
                if clasificacion == "cumplida":
                    metas_cumplidas += 1
                elif clasificacion == "parcial":
                    metas_parciales += 1
                else:
                    metas_no_cumplidas += 1
        
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

@st.cache_data(ttl=60, show_spinner=False)
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
    """Muestra una vista optimizada para impresión"""
    st.info("🔍 **Vista para Imprimir** - Use Ctrl+P en su navegador para imprimir")
    
    for agr in acuerdos:
        st.markdown("---")
        st.header(f"ACUERDO: {agr.get('id')}")
        st.subheader(f"Organismo: {agr.get('organismo_nombre')}")
        
        cumplimiento = calcular_cumplimiento_acuerdo(agr)
        if cumplimiento:
            st.metric("**Cumplimiento Ponderado Total**", f"{cumplimiento:.1f}%")
        
        # Mostrar fichas y metas
        for ficha in agr.get("fichas", []):
            with st.expander(f"FICHA: {ficha.get('id')} - {ficha.get('nombre')}", expanded=True):
                for meta in ficha.get("metas", []):
                    col_meta1, col_meta2, col_meta3 = st.columns([3, 1, 1])
                    with col_meta1:
                        st.write(f"**Meta {meta.get('numero')}:** {meta.get('descripcion')}")
                    with col_meta2:
                        st.write(f"Ponderación: {meta.get('ponderacion')}%")
                    with col_meta3:
                        cumplimiento_meta = meta.get('cumplimiento_calc', 'No calc.')
                        st.write(f"Cumplimiento: {cumplimiento_meta}%")

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

@st.cache_data(ttl=60, show_spinner=False)
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

@st.cache_data(ttl=60, show_spinner=False)
def generar_vista_imprimible_individual(agr):
    """Genera vista optimizada para impresión de un acuerdo individual"""
    
    # 🆕 GENERAR EL HTML MEJORADO
    html_content = exportar_html_imprimible(agr)
    
    # 🆕 BOTONES DE ACCIÓN PRINCIPALES
    st.info("**📄 Vista Optimizada para Impresión** - Descargue el HTML y ábralo en su navegador para imprimir (Ctrl+P)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            "💾 Descargar HTML Completo",
            data=html_content.encode('utf-8'),
            file_name=f"{agr['id']}_completo.html",
            mime="text/html",
            help="Descargue y abra en su navegador para mejor calidad de impresión"
        )
    
    with col2:
        st.download_button(
            "🖨️ Versión para Imprimir",
            data=html_content.encode('utf-8'),
            file_name=f"{agr['id']}_imprimir.html",
            mime="text/html",
            help="Optimizado específicamente para impresión"
        )
    
    with col3:
        if st.button("👁️ Vista Previa Rápida"):
            # Mostrar vista previa expandida
            with st.expander("🔍 Vista Previa del Documento", expanded=True):
                st.components.v1.html(html_content, height=600, scrolling=True)
    
    # 🆕 BOTÓN PARA OCULTAR/MOSTRAR CONTENIDO
    if st.button("📋 Mostrar/Ocultar Contenido del Acuerdo"):
        if "mostrar_contenido_acuerdo" not in st.session_state:
            st.session_state.mostrar_contenido_acuerdo = True
        else:
            st.session_state.mostrar_contenido_acuerdo = not st.session_state.mostrar_contenido_acuerdo
    
    # 🆕 CONTENIDO COMPLETO DEL ACUERDO (SOLO SI SE MUESTRA)
    if st.session_state.get("mostrar_contenido_acuerdo", True):
        st.markdown("---")
        st.subheader(f"📋 Contenido Completo del Acuerdo: {agr['id']}")
        
        # 🆕 INFORMACIÓN GENERAL
        with st.expander("📊 Información General del Acuerdo", expanded=False):
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
            with st.expander("🎯 Objeto del Acuerdo", expanded=False):
                st.write(agr.get('objeto'))
        
        # 🆕 PARTES FIRMANTES
        if agr.get('partes_firmantes'):
            with st.expander("📝 Partes Firmantes", expanded=False):
                st.write(agr.get('partes_firmantes'))
        
        # 🆕 CLAÚSULAS
        if agr.get('clausulas'):
            clausulas_no_vacias = [c for c in agr.get('clausulas', []) if c.strip()]
            if clausulas_no_vacias:
                with st.expander("📝 Cláusulas del Acuerdo", expanded=False):
                    for i, clausula in enumerate(clausulas_no_vacias, 1):
                        st.write(f"**{i}.** {clausula}")
        
        # 🆕 FICHAS Y METAS
        if agr.get('fichas'):
            st.subheader("📊 Fichas de Compromiso")
            
            for ficha_index, ficha in enumerate(agr.get('fichas', [])):
                with st.expander(f"📋 Ficha {ficha.get('id')} - {ficha.get('nombre', 'Sin nombre')}", expanded=False):
                    
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
                        st.subheader(f"🎯 Metas de la Ficha ({len(ficha['metas'])})")
                        
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
                                    st.write("**📈 Rangos de Cumplimiento:**")
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
    """Genera informe en formato HTML"""
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
        "🌐 Descargar HTML Completo",
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
def sidebar():
    st.sidebar.title("Menú")
    if st.session_state.user:
        st.sidebar.write(f"👤 {st.session_state.user.get('name','')} -- {st.session_state.user['role']}")
        
        # 🎯 MENSAJE DEMOSTRATIVO - SOLO ESTAS 4 LÍNEAS NUEVAS
        st.sidebar.markdown("---")
        st.sidebar.caption("🔬 **Sistema en Fase de Pruebas**")
        st.sidebar.caption("Datos visibles para todos los usuarios")

        # OPCIONES PARA TODOS LOS USUARIOS AUTENTICADOS
        options = ["Inicio", "Acuerdos", "Seguimiento de Indicadores", "Informes"]
        
        # ✅ ACTUALIZADO: INCLUIR SUPERVISOR EN ROLES AUTORIZADOS
        roles_autorizados = ["Administrador", "Supervisor OPP", "Responsable de Acuerdo", "Comisión CG"]
        if st.session_state.user["role"] in roles_autorizados:
            # Opciones adicionales para roles autorizados
            pass  # Aquí puedes agregar opciones especiales para supervisors
        
        # OPCIONES ADICIONALES SOLO PARA ADMINISTRADORES
        if st.session_state.user["role"] == "Administrador":
            options.append("Administración")
        
        choice = st.sidebar.radio("Ir a", options)
        
        # 🆕 DIAGNÓSTICO PARA ADMINISTRADORES Y SUPERVISORES
        if st.session_state.user["role"] in ["Administrador", "Supervisor OPP"]:
            check_permissions()  
        
        # 🆕 AGREGAR VERIFICACIÓN DE ARCHIVOS SOLO PARA ADMINISTRADORES
        if st.session_state.user["role"] == "Administrador":
            verificar_archivos_indicadores()
        
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.user = None
            st.rerun()
        return choice
    else:
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
 
def page_home():
    require_login()
    header_with_logo()
    
   # 🎯 CONTROL DE SUBPÁGINAS DENTRO DEL HOME
    if 'home_subpage' not in st.session_state:
        st.session_state.home_subpage = "main"
    
    # 🎯 MOSTRAR BOTONES DE ACCIONES RÁPIDAS EN TODAS LAS SUBPÁGINAS
    mostrar_acciones_rapidas()
    
    # 🎯 SUBPÁGINAS
    if st.session_state.home_subpage == "acuerdos":
        page_agreements()
        
    elif st.session_state.home_subpage == "reportes":
        page_reportes()
        
    elif st.session_state.home_subpage == "seguimiento":
        modulo_seguimiento_indicadores() 
    
    # 🎯 PÁGINA PRINCIPAL DEL HOME (solo se ejecuta si no hay subpágina)
    st.title("🏠 Sistema de Compromisos de Gestión")
    st.success(f"👤 Usuario: {st.session_state.user.get('name','')} ({st.session_state.user['role']})")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Estado del Sistema")
        try:
            db = agreements_load()
            total_acuerdos = len(db)
            total_fichas = sum(len(agr.get("fichas", [])) for agr in db.values())
            total_metas = sum(len(ficha.get("metas", [])) for agr in db.values() for ficha in agr.get("fichas", []))
            
            st.metric("📋 Acuerdos Activos", total_acuerdos)
            st.metric("📝 Fichas Creadas", total_fichas) 
            st.metric("🎯 Metas Registradas", total_metas)
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
    
    with col2:  
        # 🎯 ACUERDOS RECIENTES (VERSIÓN ORIGINAL - SIN FILTROS)
        st.markdown("---")
        try:
            db = agreements_load()
            if db:
                st.markdown("### 📋 Acuerdos Recientes")
                # Mostrar últimos 3 acuerdos de TODOS los usuarios
                for i, (agr_id, agr) in enumerate(list(db.items())[-3:]):
                    with st.expander(f"{agr_id} - {agr.get('organismo_nombre', 'Sin nombre')}", expanded=False):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.write(f"**Tipo:** {agr.get('tipo_compromiso')}")
                            st.write(f"**Año:** {agr.get('año')}")
                        with col_b:
                            st.write(f"**Estado:** {agr.get('estado')}")
                            st.write(f"**Fichas:** {len(agr.get('fichas', []))}")
                        with col_c:
                            if st.button("🔍 Abrir", key=f"home_open_{agr_id}"):
                                st.session_state.home_subpage = "acuerdos"
                                st.session_state.open_agr = agr_id
                                st.rerun()
            else:
                st.info("📝 No hay acuerdos creados. Use 'Ver y Gestionar Acuerdos' para crear el primero.")
        except Exception as e:
            st.error(f"Error mostrando acuerdos: {e}")
    
    # 🎯 INSTRUCCIONES PARA NUEVOS USUARIOS
    st.markdown("---")
    st.markdown("### 💡 ¿Cómo comenzar?")
    col_help1, col_help2, col_help3 = st.columns(3)
    
    with col_help1:
        st.markdown("""
        **1. Crear Acuerdos**
        - Ve a **Acuerdos**
        - Crea nuevo acuerdo
        - Agrega fichas y metas
        """)
    
    with col_help2:
        st.markdown("""
        **2. Gestionar Datos**  
        - Edita acuerdos existentes
        - Actualiza cumplimientos
        - Gesta estados
        """)
    
    with col_help3:
        st.markdown("""
        **3. Generar Reportes**
        - Ve a **Informes**
        - Genera reportes consolidados
        - Exporta en múltiples formatos
        """)

def main():
    st.set_page_config(page_title="Sistema CG", layout="wide")
    
    # 🎯 RESETEAR SUBPÁGINA AL CAMBIAR DE PÁGINA PRINCIPAL
    current_page = sidebar()
    
    if current_page != "Inicio":
        st.session_state.home_subpage = "main"  # Resetear al salir del home
    
    # 🎯 NAVEGACIÓN NORMAL
    if current_page == "Login" or not st.session_state.get('user'):
        page_login()
    elif current_page == "Inicio":
        page_home()
    elif current_page == "Acuerdos":
        page_agreements()
    elif current_page == "Reportes":
        page_reportes()
    elif current_page == "Administración":
        page_admin()
    elif current_page == "Seguimiento de Indicadores":
        modulo_seguimiento_indicadores()
    else:
        page_home()

# ==================== EJECUCIÓN (LÍNEAS 222-224) ====================
if __name__ == "__main__":
    main()

