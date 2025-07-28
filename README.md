# 📋 Sistema de Compromisos de Gestión (CG)

Aplicación web para el registro, seguimiento y evaluación de compromisos institucionales, desarrollado para la OPP con tecnología Streamlit.

![Logo OPP](https://www.opp.gub.uy/wp-content/uploads/2020/06/logo-opp-blanco.png)

## 🚀 Características principales

- **Registro de indicadores** con metas anuales y trimestrales
- **Gestión de compromisos** con etapas de revisión/validación/aprobación
- **Sistema de ponderación** automática de avances
- **Seguimiento detallado** con historial de progreso
- **Reportes exportables** en formato CSV
- **Interfaz intuitiva** con diseño responsivo

## 🔧 Requisitos técnicos

- Python 3.8+
- Dependencias:
  ```bash
  streamlit==1.17.0
  pandas==1.5.3
  pillow==9.5.0
  sqlite3==3.39.0 (incluido en Python)
🛠 Instalación local
Clonar el repositorio:

bash
git clone https://github.com/tu-usuario/sistema-cg.git
cd sistema-cg
Instalar dependencias:

bash
pip install -r requirements.txt
Ejecutar la aplicación:

bash
streamlit run CG_app.py
🖥️ Despliegue en Streamlit Cloud
https://static.streamlit.io/badges/streamlit_badge_black_white.svg

Requiere cuenta en Streamlit Cloud

Conectar con repositorio GitHub

Especificar ruta del archivo principal: CG_app.py

📂 Estructura del proyecto
text
sistema-cg/
├── CG_app.py            # Código principal
├── logo_opp.png         # Logo institucional
├── compromisos.db       # Base de datos (auto-generada)
├── requirements.txt     # Dependencias
└── README.md            # Este archivo
🧩 Módulos incluidos
Módulo	Funcionalidades
📊 Indicadores	Metas anuales/trimestrales, ponderación
📝 Compromisos	Etapas de gestión, áreas responsables
🔍 Seguimiento	Registro de avances, cálculo automático
📑 Reportes	Exportación a CSV, visualización de datos
👨‍💻 Desarrollo
Contribuciones
Haz fork del proyecto

Crea tu rama (git checkout -b feature/nueva-funcionalidad)

Realiza commits descriptivos

Abre un Pull Request

Variables de entorno
Crear archivo .env para configuración:

text
DB_NAME=compromisos.db
DEBUG_MODE=False
📄 Licencia
Este proyecto está bajo licencia MIT.

✉️ Contacto
fpoli@opp.gub.uy
