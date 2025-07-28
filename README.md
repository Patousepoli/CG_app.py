# Sistema de Compromisos de Gestión - OPP

Aplicación para gestión de compromisos institucionales con seguimiento de metas.

## 🚀 Cómo ejecutarlo localmente

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/tu-repositorio.git
   ```

2. Instala dependencias:
   ```bash
   pip install streamlit pandas pillow
   ```

3. Ejecuta la aplicación:
   ```bash
   streamlit run CG_app.py
   ```

## ☁️ Versión en línea
Accede a la aplicación desplegada:  
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tu-app.streamlit.app)

## 📌 Requisitos
- Python 3.8+
- Archivo `logo_opp.png` en la misma carpeta

## 📊 Estructura del proyecto
```
tu-repositorio/
├── CG_app.py         # Código principal
├── logo_opp.png      # Logo institucional
├── compromisos.db    # Base de datos (se crea automáticamente)
└── README.md         # Este archivo
```
☁️ Paso 3: Desplegar en Streamlit Cloud
Ve a Streamlit Cloud e inicia sesión con tu cuenta GitHub.

Haz clic en "New app" y configura:

Repository: Selecciona tu repositorio

Branch: main o master

Main file path: CG_app.py

Configuración avanzada (opcional):

En "Advanced settings" agrega estas dependencias:

text
pillow==9.5.0
pandas==1.5.3
Haz clic en "Deploy" y espera 1-2 minutos.

🔍 Paso 4: Verificación final
Prueba tu app en línea:

Abre la URL que te proporcionó Streamlit Cloud (ej: https://tu-app.streamlit.app)

Verifica que el logo se muestre correctamente

Actualiza el README con la URL de tu app:

markdown
## 🌐 App en producción
[Acceder a la aplicación](https://tu-app.streamlit.app)
💡 Consejos adicionales
Para futuras actualizaciones:

Haz cambios en tu código local

Usa git push para subirlos a GitHub

Streamlit Cloud se actualiza automáticamente

Si el logo no aparece:

Verifica que esté en el repositorio

Usa rutas relativas en el código ("logo_opp.png")

Para manejar la base de datos:

Streamlit Cloud no persiste archivos locales entre despliegues

Considera usar SQLite en memoria o conectarte a una DB externa

¡Listo! Ahora tienes tu aplicación completa en GitHub y disponible en la nube. Si necesitas hacer ajustes adicionales, solo repite el proceso de git push.

Cuando dices clona el repositorio es en github que debo hacerlo?
¡Buena pregunta! Vamos a aclarar exactamente dónde y cómo clonar el repositorio, con capturas de pantalla conceptuales:

🔷 Paso 1: Clonar el repositorio (desde GitHub a tu computadora)
Ve a tu repositorio en GitHub:

Abre https://github.com/tu-usuario/tu-repositorio

Haz clic en el botón verde "Code" (arriba a la derecha de la lista de archivos).

https://docs.github.com/assets/cb-20363/images/help/repository/code-button.png

Copia la URL HTTPS (asegúrate que termina en .git):

text
https://github.com/tu-usuario/tu-repositorio.git
Abre VS Code y luego:

Abre una terminal nueva (Terminal > New Terminal).

Navega a la carpeta donde quieres guardar el proyecto (ej: cd Documentos/Proyectos).

Ejecuta:

bash
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
🔷 Paso 2: Modificar archivos localmente
En VS Code:

Abre la carpeta del proyecto (File > Open Folder).

Edita los archivos directamente (CG_app.py, README.md, etc.).

Asegúrate de que logo_opp.png esté en esta misma carpeta.

Verifica cambios localmente (opcional pero recomendado):

bash
streamlit run CG_app.py
🔷 Paso 3: Subir cambios a GitHub
Desde la terminal en VS Code:

bash
git add .
git commit -m "Agrega logo OPP y actualiza funcionalidades"
git push origin main
Esto enviará tus cambios desde tu computadora a GitHub.

🔷 Paso 4: Streamlit Cloud se actualiza automáticamente
No necesitas hacer nada más:

Streamlit Cloud detectará los cambios en GitHub.

Re-desplegará la app automáticamente en 1-2 minutos.

https://streamlit.io/images/sharing/connect-github.png

📌 Notas clave:
Clonar = Descargar el repositorio de GitHub a tu máquina.

Push = Subir tus cambios locales a GitHub.

Streamlit Cloud siempre usa la versión más reciente de tu repositorio.

¿Necesitas ayuda con algún paso en específico? 😊

New chat

