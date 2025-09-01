Sistema de Compromisos de Gestión (Streamlit) - Versión Mejorada
================================================================

Este sistema implementa la gestión de Compromisos de Gestión (CG) con acuerdos institucionales,
fichas y metas, siguiendo la ficha oficial y los criterios de ponderaciones.

------------------------------------------------
REQUISITOS
------------------------------------------------
- Python 3.9 o superior
- Librerías requeridas:
    * streamlit
    * pandas

Instalar con:
    pip install streamlit pandas

------------------------------------------------
EJECUCIÓN
------------------------------------------------
1. Guardar el archivo principal como `app.py` dentro de una carpeta de proyecto (ej. `System_CG`).
2. Colocar el logo de OPP en la misma carpeta con el nombre:
     - `logo_opp.png`   (preferido)
     - o `logo.png`     (alternativo)
3. Desde la terminal, ejecutar:
     streamlit run app.py
4. Abrir el navegador en la URL que muestre (por defecto http://localhost:8501).

------------------------------------------------
USUARIOS
------------------------------------------------
- El sistema se inicializa con un usuario administrador por defecto:
    Usuario: admin
    Contraseña: admin
- Se recomienda cambiar la contraseña al primer ingreso.
- Los usuarios se gestionan desde el menú de "Administración".

------------------------------------------------
CÓDIGOS DE IDENTIFICACIÓN
------------------------------------------------
- Acuerdos: AC_####_AÑO (ej. AC_0001_2025)
- Fichas:   F_####_AÑO (ej. F_0001_2025)
- Metas:    identificador único interno (META_xxxxx)

------------------------------------------------
FICHA DE META (Formato oficial)
------------------------------------------------
Cada ficha y meta exportada o importada en CSV sigue el formato de la ficha oficial:

Ficha de Meta incluye:
  - Identificación (N° y nombre)
  - Tipo de Meta (Institucional, Grupal, Individual)
  - Alcance de la meta
  - Objetivo
  - Indicador
  - Forma de cálculo
  - Fuentes de información
  - Valor base
  - Meta (descripción)
  - Plazo de vencimiento
  - Responsable/s de seguimiento
  - Rango de cumplimiento
  - Ponderación
  - Cláusula de Salvaguarda
  - Observaciones

------------------------------------------------
CSV - CARGA Y DESCARGA
------------------------------------------------
El sistema permite carga/descarga masiva de fichas y metas en formato CSV estructurado:

- Dos columnas: Atributo, Valor
- Orden y nombres de campos según ficha oficial
- Bloques claramente identificados para cada Ficha y cada Meta

Ejemplo:

    Atributo,Valor
    Ficha,N°1
    Identificación,F_0001_2025 - Producción
    Tipo de Meta,Institucional
    Alcance de la meta,Todos los funcionarios
    Objetivo,Mejorar eficiencia en procesos
    Indicador,% de procesos digitalizados
    Forma de cálculo,(# digitalizados / total procesos)*100
    Fuentes de información,Informe de Gestión
    Valor base,25
    Meta,Alcanzar 60%
    Plazo de vencimiento,2025-12-31
    Responsable/s de seguimiento,Director Área X
    Rango de cumplimiento,>=95%:100;75-95%:parcial;<75%:0
    Ponderación,50
    Observaciones,Ninguna
    ---

    Meta,META_123abc
    Descripción,Digitalizar procesos críticos
    Unidad,%
    Valor Objetivo,60
    Sentido,>=
    Frecuencia,Anual
    Vencimiento,2025-12-31
    Es hito,NO
    Ponderación,50
    Observaciones,N/A
    ---

El importador reconoce este formato y asigna los campos a los objetos de datos.

------------------------------------------------
PONDERACIONES
------------------------------------------------
El sistema valida automáticamente las ponderaciones según los criterios oficiales:

- CG INSTITUCIONALES:
  Para cada período de evaluación (intermedio, final, etc.), las metas deben sumar 100%.
  Puede haber más de un período (ej. mayo y noviembre), pero en cada uno la suma es 100%.

- CG FUNCIONALES:
  La distribución recomendada es:
    * Institucional: 30%
    * Grupal/Sectorial: 50%
    * Individual: 20%
  El sistema verifica que las metas en cada categoría sumen estos porcentajes (o se redistribuyan proporcionalmente si falta alguna).

------------------------------------------------
ADJUNTOS
------------------------------------------------
- Archivos asociados a acuerdos se guardan en: data/uploads/<ACUERDO_ID>/
- Pueden descargarse individualmente o como ZIP.

------------------------------------------------
PERSISTENCIA
------------------------------------------------
- Toda la información se guarda en la carpeta `data/`:
    * agreements.json   (acuerdos)
    * users.json        (usuarios)
    * counters.json     (secuencias de códigos)
    * audit.json        (registro de auditoría)

------------------------------------------------
CONTRATOS
------------------------------------------------
- Se genera automáticamente un contrato en formato RTF (Anexo II).

------------------------------------------------
CONTACTO
------------------------------------------------
Ante dudas o mejoras, revisar la documentación interna o contactar al administrador del sistema.
