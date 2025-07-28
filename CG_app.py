import os
import sqlite3
import pandas as pd
import streamlit as st
from PIL import Image

# --- Configuración inicial --- #
st.set_page_config(
    page_title="Sistema de Compromisos de Gestión - OPP",
    page_icon="📋",
    layout="wide"
)

def cargar_logotipo():
    try:
        logo = Image.open("LOGO_OPP.png")  # nombre exacto del archivo en GitHub
        st.image(logo, width=200)
    except FileNotFoundError:
        # Logo alternativo si no se encuentra el archivo
        st.image("https://via.placeholder.com/200x100?text=LOGO+OPP", width=200)

# Mostrar logotipo y título
cargar_logotipo()
st.title("Sistema de Compromisos de Gestión")

# --- Conexión a la base de datos --- #
def get_db_connection():
    conn = sqlite3.connect('compromisos.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Inicialización de la base de datos --- #
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        codigo TEXT NOT NULL UNIQUE,
        organismo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        descripcion TEXT,
        meta_anual REAL,
        meta_trimestral1 REAL,
        meta_trimestral2 REAL,
        meta_trimestral3 REAL,
        meta_trimestral4 REAL,
        ponderacion REAL,
        frecuencia TEXT,
        unidad_medida TEXT,
        fuente_informacion TEXT,
        responsable_nombre TEXT,
        responsable_cargo TEXT,
        responsable_email TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS compromisos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        codigo TEXT NOT NULL UNIQUE,
        id_indicador INTEGER,
        area_responsable TEXT,
        descripcion TEXT,
        objetivo_estrategico TEXT,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        meta_final REAL,
        ponderacion REAL,
        etapa_revision TEXT DEFAULT 'Pendiente',
        etapa_validacion TEXT DEFAULT 'Pendiente',
        etapa_aprobacion TEXT DEFAULT 'Pendiente',
        FOREIGN KEY (id_indicador) REFERENCES indicadores(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS responsables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        cargo TEXT NOT NULL,
        area TEXT NOT NULL,
        rol TEXT NOT NULL,
        email TEXT,
        telefono TEXT,
        id_compromiso INTEGER,
        FOREIGN KEY (id_compromiso) REFERENCES compromisos(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS seguimiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_compromiso INTEGER,
        fecha TEXT,
        avance REAL,
        meta_cumplida REAL,
        ponderacion_avance REAL,
        observaciones TEXT,
        FOREIGN KEY (id_compromiso) REFERENCES compromisos(id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- Pestañas principales --- #
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Indicadores y Metas", 
    "📝 Compromisos", 
    "🔍 Seguimiento",
    "📑 Reportes"
])

# --- Pestaña 1: Indicadores y Metas --- #
with tab1:
    st.header("Registro de Indicadores y Metas")
    
    with st.form("form_indicador", clear_on_submit=True):
        st.subheader("Información Básica")
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre del Indicador*")
        codigo = col2.text_input("Código del Indicador*")
        organismo = col1.selectbox("Organismo*", ["MEF", "MIEM", "MSP", "MTOP", "OTROS"])
        tipo = col2.selectbox("Tipo de Indicador*", ["Eficiencia", "Eficacia", "Economía", "Calidad", "Satisfacción"])
        descripcion = st.text_area("Descripción*")
        
        st.subheader("Metas y Ponderación")
        col1, col2 = st.columns(2)
        meta_anual = col1.number_input("Meta Anual*", min_value=0.0)
        ponderacion = col2.number_input("Ponderación (%)*", min_value=0, max_value=100, value=100)
        
        st.subheader("Metas Trimestrales")
        col1, col2, col3, col4 = st.columns(4)
        meta_trimestral1 = col1.number_input("Trimestre 1", min_value=0.0, value=0.0)
        meta_trimestral2 = col2.number_input("Trimestre 2", min_value=0.0, value=0.0)
        meta_trimestral3 = col3.number_input("Trimestre 3", min_value=0.0, value=0.0)
        meta_trimestral4 = col4.number_input("Trimestre 4", min_value=0.0, value=0.0)
        
        st.subheader("Medición y Responsable")
        col1, col2 = st.columns(2)
        frecuencia = col1.selectbox("Frecuencia de Medición*", ["Diaria", "Semanal", "Mensual", "Trimestral", "Semestral", "Anual"])
        unidad_medida = col2.text_input("Unidad de Medida*")
        fuente_informacion = st.text_input("Fuente de Información*")
        
        col1, col2 = st.columns(2)
        responsable_nombre = col1.text_input("Nombre del Responsable*")
        responsable_cargo = col2.text_input("Cargo del Responsable*")
        responsable_email = col1.text_input("Email del Responsable*")
        
        if st.form_submit_button("Guardar Indicador"):
            if nombre and codigo and organismo:
                conn = get_db_connection()
                conn.execute('''
                INSERT INTO indicadores (
                    nombre, codigo, organismo, tipo, descripcion,
                    meta_anual, meta_trimestral1, meta_trimestral2, meta_trimestral3, meta_trimestral4,
                    ponderacion, frecuencia, unidad_medida, fuente_informacion,
                    responsable_nombre, responsable_cargo, responsable_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    nombre, codigo, organismo, tipo, descripcion,
                    meta_anual, meta_trimestral1, meta_trimestral2, meta_trimestral3, meta_trimestral4,
                    ponderacion, frecuencia, unidad_medida, fuente_informacion,
                    responsable_nombre, responsable_cargo, responsable_email
                ))
                conn.commit()
                conn.close()
                st.success("¡Indicador registrado correctamente!")
            else:
                st.error("Por favor complete los campos obligatorios (*)")

# --- Pestaña 2: Compromisos --- #
with tab2:
    st.header("Registro de Compromisos")
    
    conn = get_db_connection()
    indicadores = conn.execute("SELECT id, nombre FROM indicadores").fetchall()
    conn.close()
    
    with st.form("form_compromiso", clear_on_submit=True):
        st.subheader("Información General")
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre del Compromiso*")
        codigo = col2.text_input("Código del Compromiso*")
        
        if indicadores:
            id_indicador = col1.selectbox(
                "Indicador Asociado*",
                options=[i['id'] for i in indicadores],
                format_func=lambda x: next(i['nombre'] for i in indicadores if i['id'] == x)
            )
        else:
            st.warning("No hay indicadores registrados. Cree uno primero.")
            id_indicador = None
        
        area_responsable = col2.text_input("Área Responsable*")
        descripcion = st.text_area("Descripción*")
        objetivo_estrategico = st.text_area("Objetivo Estratégico*")
        
        st.subheader("Plazos y Metas")
        col1, col2, col3 = st.columns(3)
        fecha_inicio = col1.text_input("Fecha de Inicio* (AAAA-MM-DD)")
        fecha_fin = col2.text_input("Fecha de Finalización* (AAAA-MM-DD)")
        meta_final = col3.number_input("Meta Final*", min_value=0.0)
        ponderacion = st.number_input("Ponderación (%)*", min_value=0, max_value=100, value=100)
        
        st.subheader("Etapas")
        col1, col2, col3 = st.columns(3)
        etapa_revision = col1.selectbox("Revisión", ["Pendiente", "En Proceso", "Completado"])
        etapa_validacion = col2.selectbox("Validación", ["Pendiente", "En Proceso", "Completado"])
        etapa_aprobacion = col3.selectbox("Aprobación", ["Pendiente", "En Proceso", "Completado"])
        
        if st.form_submit_button("Guardar Compromiso"):
            if nombre and codigo and id_indicador:
                conn = get_db_connection()
                conn.execute('''
                INSERT INTO compromisos (
                    nombre, codigo, id_indicador, area_responsable,
                    descripcion, objetivo_estrategico,
                    fecha_inicio, fecha_fin, meta_final, ponderacion,
                    etapa_revision, etapa_validacion, etapa_aprobacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    nombre, codigo, id_indicador, area_responsable,
                    descripcion, objetivo_estrategico,
                    fecha_inicio, fecha_fin, meta_final, ponderacion,
                    etapa_revision, etapa_validacion, etapa_aprobacion
                ))
                conn.commit()
                conn.close()
                st.success("¡Compromiso registrado correctamente!")
            else:
                st.error("Por favor complete los campos obligatorios (*)")

# --- Pestaña 3: Seguimiento --- #
with tab3:
    st.header("Seguimiento de Compromisos")
    
    conn = get_db_connection()
    compromisos = conn.execute("SELECT id, nombre FROM compromisos").fetchall()
    
    if compromisos:
        with st.form("form_seguimiento"):
            id_compromiso = st.selectbox(
                "Seleccione Compromiso*",
                options=[c['id'] for c in compromisos],
                format_func=lambda x: next(c['nombre'] for c in compromisos if c['id'] == x)
            )
            
            col1, col2, col3 = st.columns(3)
            fecha = col1.text_input("Fecha (AAAA-MM-DD)*")
            avance = col2.number_input("Avance (%)*", min_value=0, max_value=100)
            meta_cumplida = col3.number_input("Meta Cumplida*", min_value=0.0)
            
            # Calcular ponderación del avance automáticamente
            ponderacion_compromiso = conn.execute(
                "SELECT ponderacion FROM compromisos WHERE id = ?", 
                (id_compromiso,)
            ).fetchone()['ponderacion']
            
            ponderacion_avance = (avance / 100) * ponderacion_compromiso
            
            st.metric("Ponderación del Avance", f"{ponderacion_avance:.2f}%")
            
            observaciones = st.text_area("Observaciones")
            
            if st.form_submit_button("Registrar Seguimiento"):
                conn.execute('''
                INSERT INTO seguimiento (
                    id_compromiso, fecha, avance, meta_cumplida,
                    ponderacion_avance, observaciones
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    id_compromiso, fecha, avance, meta_cumplida,
                    ponderacion_avance, observaciones
                ))
                conn.commit()
                st.success("¡Seguimiento registrado correctamente!")
    else:
        st.warning("No hay compromisos registrados para hacer seguimiento.")
    
    conn.close()

# --- Pestaña 4: Reportes --- #
with tab4:
    st.header("Reportes")
    
    conn = get_db_connection()
    
    st.subheader("Indicadores")
    df_indicadores = pd.read_sql("SELECT * FROM indicadores", conn)
    if not df_indicadores.empty:
        st.dataframe(df_indicadores)
        
        # Exportar a CSV
        csv = df_indicadores.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Indicadores (CSV)",
            data=csv,
            file_name="indicadores.csv",
            mime="text/csv"
        )
    
    st.subheader("Compromisos")
    df_compromisos = pd.read_sql("SELECT * FROM compromisos", conn)
    if not df_compromisos.empty:
        st.dataframe(df_compromisos)
        
        csv = df_compromisos.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Compromisos (CSV)",
            data=csv,
            file_name="compromisos.csv",
            mime="text/csv"
        )
    
    st.subheader("Seguimientos")
    df_seguimiento = pd.read_sql("SELECT * FROM seguimiento", conn)
    if not df_seguimiento.empty:
        st.dataframe(df_seguimiento)
        
        csv = df_seguimiento.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Seguimientos (CSV)",
            data=csv,
            file_name="seguimientos.csv",
            mime="text/csv"
        )
    
    conn.close()

# --- Instrucciones para el usuario --- #
st.sidebar.markdown("""
### Instrucciones:
1. **Logo OPP**: Coloca el archivo `logo_opp.png` en la misma carpeta que este script.
2. **Base de datos**: Se creará automáticamente (`compromisos.db`).
3. **Exportación**: Los reportes se pueden descargar en formato CSV.
""")
