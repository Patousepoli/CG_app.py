import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Conexión a la base de datos
conn = sqlite3.connect('cg_sistema_v3.db')
c = conn.cursor()

# Crear tablas con la estructura mejorada
c.executescript('''
CREATE TABLE IF NOT EXISTS organismos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS areas_responsables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organismo_id INTEGER,
    nombre TEXT NOT NULL,
    responsable TEXT,
    FOREIGN KEY (organismo_id) REFERENCES organismos(id)
);

CREATE TABLE IF NOT EXISTS objetivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('Estratégico', 'Operativo')),
    nombre TEXT NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS tipos_compromiso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('Institucional', 'Funcional')),
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS indicadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objetivo_id INTEGER,
    organismo_id INTEGER,
    area_id INTEGER,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    unidad_medida TEXT,
    forma_calculo TEXT,
    linea_base REAL,
    meta_anual REAL,
    plazo_vencimiento DATE,
    FOREIGN KEY (objetivo_id) REFERENCES objetivos(id),
    FOREIGN KEY (organismo_id) REFERENCES organismos(id),
    FOREIGN KEY (area_id) REFERENCES areas_responsables(id)
);

CREATE TABLE IF NOT EXISTS compromisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ficha TEXT UNIQUE,
    tipo_compromiso_id INTEGER,
    objetivo_id INTEGER,
    organismo_id INTEGER,
    area_id INTEGER,
    responsable TEXT NOT NULL,
    fecha_inicio DATE,
    fecha_termino DATE,
    clausula_salvaguarda TEXT,
    FOREIGN KEY (tipo_compromiso_id) REFERENCES tipos_compromiso(id),
    FOREIGN KEY (objetivo_id) REFERENCES objetivos(id),
    FOREIGN KEY (organismo_id) REFERENCES organismos(id),
    FOREIGN KEY (area_id) REFERENCES areas_responsables(id)
);

CREATE TABLE IF NOT EXISTS metas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compromiso_id INTEGER,
    indicador_id INTEGER,
    meta_intermedia REAL,
    meta_final REAL,
    ponderacion_intermedia REAL CHECK (ponderacion_intermedia >= 0 AND ponderacion_intermedia <= 100),
    ponderacion_final REAL CHECK (ponderacion_final >= 0 AND ponderacion_final <= 100),
    cumplimiento REAL DEFAULT 0,
    valor_actual REAL,
    fecha_medicion DATE,
    observaciones TEXT,
    FOREIGN KEY (compromiso_id) REFERENCES compromisos(id),
    FOREIGN KEY (indicador_id) REFERENCES indicadores(id)
);

CREATE TABLE IF NOT EXISTS historico_cumplimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_id INTEGER,
    valor_reportado REAL,
    fecha_reporte DATE,
    observaciones TEXT,
    FOREIGN KEY (meta_id) REFERENCES metas(id)
);
''')

conn.commit()

# Datos iniciales
def inicializar_datos():
    # Insertar organismos base si no existen
    c.execute("SELECT COUNT(*) FROM organismos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO organismos (nombre, descripcion) VALUES (?, ?)",
                      [('Organismo Principal', 'Organismo central del sistema'),
                       ('Departamento de Proyectos', 'Área encargada de la gestión de proyectos')])
    
    # Insertar áreas responsables si no existen
    c.execute("SELECT COUNT(*) FROM areas_responsables")
    if c.fetchone()[0] == 0:
        org_id = pd.read_sql("SELECT id FROM organismos WHERE nombre = 'Organismo Principal'", conn).iloc[0]['id']
        c.executemany("INSERT INTO areas_responsables (organismo_id, nombre, responsable) VALUES (?, ?, ?)",
                      [(org_id, 'Gestión Estratégica', 'Director Estratégico'),
                       (org_id, 'Operaciones', 'Gerente Operativo')])
    
    # Insertar tipos de compromiso si no existen
    c.execute("SELECT COUNT(*) FROM tipos_compromiso")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO tipos_compromiso (tipo, descripcion) VALUES (?, ?)",
                      [('Institucional', 'Compromisos alineados a los objetivos institucionales'),
                       ('Funcional', 'Compromisos específicos de áreas funcionales')])
    
    # Insertar objetivos base si no existen
    c.execute("SELECT COUNT(*) FROM objetivos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO objetivos (tipo, nombre, descripcion) VALUES (?, ?, ?)",
                      [('Estratégico', 'Objetivo Estratégico 1', 'Descripción del objetivo estratégico principal'),
                       ('Operativo', 'Objetivo Operativo 1', 'Descripción del objetivo operativo clave')])
    
    conn.commit()

inicializar_datos()

# Funciones auxiliares
def calcular_cumplimiento(valor_actual, meta):
    return (valor_actual / meta) * 100 if meta != 0 else 0

def validar_ponderaciones(ponderacion_intermedia, ponderacion_final):
    return abs((ponderacion_intermedia + ponderacion_final) - 100) < 0.01

# Interfaz Streamlit
st.title('Sistema de Control de Gestión')

# Menú principal
menu = st.sidebar.selectbox('Menú', [
    'Registro de Indicadores',
    'Registro de CG',
    'Seguimiento',
    'Reportes'
], key='menu_principal')

if menu == 'Registro de Indicadores':
    st.header('Registro de Nuevo Indicador')
    
    with st.form(key='form_nuevo_indicador'):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre del Indicador*")
            objetivo = st.selectbox(
                "Objetivo Asociado*",
                options=pd.read_sql("SELECT nombre FROM objetivos", conn)['nombre'],
                key='select_objetivo_indicador'
            )
            organismo = st.selectbox(
                "Organismo Reportante*",
                options=pd.read_sql("SELECT nombre FROM organismos", conn)['nombre'],
                key='select_organismo'
            )
            area = st.selectbox(
                "Área Responsable*",
                options=pd.read_sql("SELECT nombre FROM areas_responsables WHERE organismo_id = (SELECT id FROM organismos WHERE nombre = ?)", 
                                   conn, params=(organismo,))['nombre'],
                key='select_area'
            )
            
        with col2:
            unidad_medida = st.text_input("Unidad de Medida*")
            forma_calculo = st.text_area("Fórmula de Cálculo*", height=100)
            linea_base = st.number_input("Valor Base*", min_value=0.0)
            plazo_vencimiento = st.date_input("Plazo de Vencimiento*", value=datetime.today())
        
        descripcion = st.text_area("Descripción del Indicador")
        
        if st.form_submit_button("Guardar Indicador"):
            if not all([nombre, objetivo, organismo, area, unidad_medida, forma_calculo]):
                st.error("Complete los campos obligatorios (*)")
            else:
                try:
                    # Obtener IDs necesarios
                    objetivo_id = pd.read_sql("SELECT id FROM objetivos WHERE nombre = ?", 
                                            conn, params=(objetivo,)).iloc[0]['id']
                    organismo_id = pd.read_sql("SELECT id FROM organismos WHERE nombre = ?", 
                                             conn, params=(organismo,)).iloc[0]['id']
                    area_id = pd.read_sql("SELECT id FROM areas_responsables WHERE nombre = ? AND organismo_id = ?", 
                                         conn, params=(area, organismo_id)).iloc[0]['id']
                    
                    # Insertar indicador
                    c.execute('''INSERT INTO indicadores
                                (objetivo_id, organismo_id, area_id, nombre, descripcion, 
                                 unidad_medida, forma_calculo, linea_base, plazo_vencimiento)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                             (objetivo_id, organismo_id, area_id, nombre, descripcion, 
                              unidad_medida, forma_calculo, linea_base, plazo_vencimiento))
                    
                    conn.commit()
                    st.success("Indicador registrado exitosamente!")
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error al guardar: {str(e)}")

elif menu == 'Registro de CG':
    st.header('Registro de Nuevo Compromiso')
    
    with st.form(key='form_nuevo_cg'):
        col1, col2 = st.columns(2)
        
        with col1:
            ficha = st.text_input("Número de Ficha*")
            tipo_compromiso = st.selectbox(
                "Tipo de Compromiso*",
                options=['Institucional', 'Funcional'],
                key='tipo_compromiso'
            )
            objetivo = st.selectbox(
                "Objetivo Asociado*",
                options=pd.read_sql("SELECT nombre FROM objetivos", conn)['nombre'],
                key='select_objetivo'
            )
            organismo = st.selectbox(
                "Organismo Reportante*",
                options=pd.read_sql("SELECT nombre FROM organismos", conn)['nombre'],
                key='select_organismo_cg'
            )
            
        with col2:
            area = st.selectbox(
                "Área Responsable*",
                options=pd.read_sql("SELECT nombre FROM areas_responsables WHERE organismo_id = (SELECT id FROM organismos WHERE nombre = ?)", 
                                   conn, params=(organismo,))['nombre'],
                key='select_area_cg'
            )
            responsable = st.text_input("Responsable*")
            fecha_inicio = st.date_input("Fecha Inicio*", value=datetime.today())
            fecha_termino = st.date_input("Fecha Término*", value=datetime.today())
        
        # Sección de indicadores y metas
        st.subheader("Indicadores y Metas")
        
        indicador = st.selectbox(
            "Indicador*",
            options=pd.read_sql("SELECT nombre FROM indicadores WHERE objetivo_id = (SELECT id FROM objetivos WHERE nombre = ?)", 
                              conn, params=(objetivo,))['nombre'],
            key='select_indicador'
        )
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            meta_intermedia = st.number_input("Meta Intermedia*", min_value=0.0)
        with col_m2:
            ponderacion_intermedia = st.number_input("Ponderación Intermedia (%)*", 
                                                   min_value=0.0, max_value=100.0, value=50.0)
        with col_m3:
            meta_final = st.number_input("Meta Final*", min_value=0.0)
        with col_m4:
            ponderacion_final = st.number_input("Ponderación Final (%)*", 
                                              min_value=0.0, max_value=100.0, value=50.0)
        
        clausula = st.text_area("Cláusula de Salvaguarda", height=100)
        observaciones = st.text_area("Observaciones")
        
        if st.form_submit_button("Guardar Compromiso"):
            if not all([ficha, responsable, objetivo, indicador, meta_intermedia, meta_final]):
                st.error("Complete los campos obligatorios (*)")
            elif not validar_ponderaciones(ponderacion_intermedia, ponderacion_final):
                st.error("La suma de ponderaciones debe ser 100%")
            else:
                try:
                    # Obtener IDs necesarios
                    tipo_id = pd.read_sql("SELECT id FROM tipos_compromiso WHERE tipo = ?",
                                         conn, params=(tipo_compromiso,)).iloc[0]['id']
                    objetivo_id = pd.read_sql("SELECT id FROM objetivos WHERE nombre = ?",
                                           conn, params=(objetivo,)).iloc[0]['id']
                    organismo_id = pd.read_sql("SELECT id FROM organismos WHERE nombre = ?",
                                             conn, params=(organismo,)).iloc[0]['id']
                    area_id = pd.read_sql("SELECT id FROM areas_responsables WHERE nombre = ? AND organismo_id = ?",
                                        conn, params=(area, organismo_id)).iloc[0]['id']
                    indicador_id = pd.read_sql("SELECT id FROM indicadores WHERE nombre = ?",
                                            conn, params=(indicador,)).iloc[0]['id']
                    
                    # Insertar compromiso
                    c.execute('''INSERT INTO compromisos
                                (ficha, tipo_compromiso_id, objetivo_id, organismo_id, area_id,
                                 responsable, fecha_inicio, fecha_termino, clausula_salvaguarda)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                             (ficha, tipo_id, objetivo_id, organismo_id, area_id,
                              responsable, fecha_inicio, fecha_termino, clausula))
                    
                    compromiso_id = c.lastrowid
                    
                    # Insertar meta
                    c.execute('''INSERT INTO metas
                                (compromiso_id, indicador_id, meta_intermedia, meta_final,
                                 ponderacion_intermedia, ponderacion_final, observaciones)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                             (compromiso_id, indicador_id, meta_intermedia, meta_final,
                              ponderacion_intermedia, ponderacion_final, observaciones))
                    
                    conn.commit()
                    st.success("Compromiso registrado exitosamente!")
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error al guardar: {str(e)}")

elif menu == 'Seguimiento':
    st.header('Seguimiento de Compromisos')
    
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        tipo_filtro = st.selectbox(
            "Filtrar por tipo",
            options=['Todos'] + pd.read_sql("SELECT DISTINCT tipo FROM tipos_compromiso", conn)['tipo'].tolist(),
            key='filtro_tipo'
        )
    
    with col_f2:
        objetivo_filtro = st.selectbox(
            "Filtrar por objetivo",
            options=['Todos'] + pd.read_sql("SELECT DISTINCT nombre FROM objetivos", conn)['nombre'].tolist(),
            key='filtro_objetivo'
        )
    
    with col_f3:
        organismo_filtro = st.selectbox(
            "Filtrar por organismo",
            options=['Todos'] + pd.read_sql("SELECT DISTINCT nombre FROM organismos", conn)['nombre'].tolist(),
            key='filtro_organismo'
        )
    
    # Construir consulta SQL dinámica
    query = '''SELECT c.ficha, tc.tipo AS tipo_compromiso, o.nombre AS objetivo,
               org.nombre AS organismo, ar.nombre AS area, c.responsable, 
               c.fecha_inicio, c.fecha_termino
               FROM compromisos c
               JOIN tipos_compromiso tc ON c.tipo_compromiso_id = tc.id
               JOIN objetivos o ON c.objetivo_id = o.id
               JOIN organismos org ON c.organismo_id = org.id
               JOIN areas_responsables ar ON c.area_id = ar.id'''
    
    conditions = []
    params = []
    
    if tipo_filtro != 'Todos':
        conditions.append("tc.tipo = ?")
        params.append(tipo_filtro)
    
    if objetivo_filtro != 'Todos':
        conditions.append("o.nombre = ?")
        params.append(objetivo_filtro)
    
    if organismo_filtro != 'Todos':
        conditions.append("org.nombre = ?")
        params.append(organismo_filtro)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # Mostrar resultados
    df_compromisos = pd.read_sql(query, conn, params=params)
    
    if not df_compromisos.empty:
        st.dataframe(df_compromisos)
        
        # Seleccionar un compromiso para ver detalles
        selected_ficha = st.selectbox(
            "Seleccione un compromiso para ver detalles",
            options=df_compromisos['ficha'],
            key='select_detalle'
        )
        
        if selected_ficha:
            # Obtener detalles del compromiso seleccionado
            detalle = pd.read_sql('''SELECT m.meta_intermedia, m.meta_final,
                                    m.ponderacion_intermedia, m.ponderacion_final,
                                    m.cumplimiento, m.valor_actual, m.fecha_medicion,
                                    i.nombre AS indicador, i.unidad_medida, i.forma_calculo,
                                    i.linea_base, i.plazo_vencimiento, m.observaciones
                                    FROM metas m
                                    JOIN indicadores i ON m.indicador_id = i.id
                                    JOIN compromisos c ON m.compromiso_id = c.id
                                    WHERE c.ficha = ?''',
                                conn, params=(selected_ficha,))
            
            st.subheader("Metas Asociadas")
            st.dataframe(detalle)
            
            # Actualización de seguimiento
            with st.expander("Actualizar Seguimiento"):
                with st.form(key='form_actualizar_seguimiento'):
                    meta_id = detalle.index[0]  # Asumimos una meta por compromiso para simplificar
                    valor_actual = st.number_input(
                        "Valor Actual*",
                        min_value=0.0,
                        value=float(detalle.iloc[0]['valor_actual']) if detalle.iloc[0]['valor_actual'] else 0.0
                    )
                    fecha_medicion = st.date_input(
                        "Fecha de Medición*",
                        value=datetime.today()
                    )
                    obs_seguimiento = st.text_area("Observaciones de Seguimiento")
                    
                    if st.form_submit_button("Actualizar Seguimiento"):
                        try:
                            # Calcular cumplimiento
                            cumplimiento = calcular_cumplimiento(
                                valor_actual,
                                detalle.iloc[0]['meta_final']
                            )
                            
                            # Actualizar meta
                            c.execute('''UPDATE metas
                                        SET valor_actual = ?,
                                            fecha_medicion = ?,
                                            cumplimiento = ?,
                                            observaciones = ?
                                        WHERE id = ?''',
                                     (valor_actual, fecha_medicion, cumplimiento, obs_seguimiento, meta_id))
                            
                            # Registrar en histórico
                            c.execute('''INSERT INTO historico_cumplimiento
                                        (meta_id, valor_reportado, fecha_reporte, observaciones)
                                        VALUES (?, ?, ?, ?)''',
                                     (meta_id, valor_actual, fecha_medicion, obs_seguimiento))
                            
                            conn.commit()
                            st.success("Seguimiento actualizado exitosamente!")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Error al actualizar: {str(e)}")
            
            # Gráfico de avance
            if not detalle.empty:
                st.subheader("Avance de Metas")
                chart_data = detalle.set_index('indicador')[['meta_intermedia', 'meta_final', 'cumplimiento']]
                st.bar_chart(chart_data)
                
                # Mostrar histórico de cumplimiento
                historico = pd.read_sql('''SELECT valor_reportado, fecha_reporte, observaciones
                                         FROM historico_cumplimiento
                                         WHERE meta_id = ?
                                         ORDER BY fecha_reporte''',
                                      conn, params=(meta_id,))
                
                if not historico.empty:
                    st.subheader("Histórico de Cumplimiento")
                    st.line_chart(historico.set_index('fecha_reporte')['valor_reportado'])
                    st.dataframe(historico)
    else:
        st.info("No hay compromisos con los filtros seleccionados")

elif menu == 'Reportes':
    st.header('Reportes de Gestión')
    
    # Generar reporte consolidado
    if st.button("Generar Reporte Consolidado", key='btn_reporte'):
        reporte = pd.read_sql('''SELECT org.nombre AS organismo, 
                                COUNT(DISTINCT c.id) AS total_compromisos,
                                AVG(m.cumplimiento) AS avance_promedio,
                                SUM(CASE WHEN m.cumplimiento >= 100 THEN 1 ELSE 0 END) AS cumplidos,
                                SUM(CASE WHEN m.cumplimiento < 100 AND 
                                    (julianday('now') - julianday(c.fecha_termino)) > 0 THEN 1 ELSE 0 END) AS atrasados
                                FROM compromisos c
                                JOIN organismos org ON c.organismo_id = org.id
                                JOIN metas m ON m.compromiso_id = c.id
                                GROUP BY org.nombre''', conn)
        
        st.subheader("Reporte Consolidado por Organismo")
        st.dataframe(reporte)
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            st.bar_chart(reporte.set_index('organismo')['total_compromisos'])
        
        with col2:
            st.bar_chart(reporte.set_index('organismo')['avance_promedio'])
        
        # Reporte detallado por indicador
        st.subheader("Detalle por Indicador")
        detalle_indicadores = pd.read_sql('''SELECT i.nombre AS indicador, 
                                            org.nombre AS organismo, 
                                            ar.nombre AS area,
                                            i.linea_base, i.meta_anual,
                                            AVG(m.cumplimiento) AS cumplimiento_promedio,
                                            i.plazo_vencimiento
                                            FROM indicadores i
                                            JOIN organismos org ON i.organismo_id = org.id
                                            JOIN areas_responsables ar ON i.area_id = ar.id
                                            LEFT JOIN metas m ON m.indicador_id = i.id
                                            GROUP BY i.id''', conn)
        
        st.dataframe(detalle_indicadores)

# Cerrar conexión
conn.close()