# Asistente Inteligente

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen)

**Asistente Inteligente** es una aplicación web para la gestión documental inteligente, que permite organizar documentos por secciones (Contabilidad, Laboral, Financiero, Logístico, Excel), con subcategorías, buscador, sistema de publicaciones del master y consultas entre usuarios.

## 🚀 Características

- 🔐 Autenticación con cuentas de Gmail (registro y login)
- 👑 Rol de **master** y roles de **usuario** con diferentes permisos
- 📂 Secciones y subcategorías configurables
- 📤 Subida de documentos personales (solo master)
- 📢 Publicación de documentos para todos los usuarios (master)
- 🔍 Buscador general con filtros
- 📥 Descarga de documentos con control de acceso por sección
- ✏️ Edición y eliminación de publicaciones (master)
- 💬 Sistema de consultas y mensajes entre usuarios y master
- 👤 Perfil de usuario editable (datos personales, estadísticas)

## 🛠️ Tecnologías utilizadas

- [Python 3.8+](https://www.python.org/)
- [Streamlit](https://streamlit.io/) – Framework para la interfaz web
- [Pandas](https://pandas.pydata.org/) – Manejo de datos
- [Plotly](https://plotly.com/) – Visualizaciones
- JSON como base de datos ligera

## 📁 Estructura del repositorio
├── app.py # Aplicación principal
├── auth.py # Autenticación y gestión de usuarios
├── storage_manager.py # Gestión de archivos
├── message_manager.py # Mensajería
├── requirements.txt
├── README.md
├── .gitignore
├── assets/ # Imágenes y logos
├── data/ # Archivos JSON (se crean automáticamente)
├── uploads/ # Documentos personales
├── publicaciones/ # Documentos públicos
└── videos/ # Tutoriales

## 🧪 Instalación y ejecución local

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/tu-usuario/Asistente_Inteligente.git
   cd Asistente_Inteligente

   python -m venv venv
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

streamlit run app.py

## 🔑 Credenciales de acceso por defecto

- **Master**: `master@optimizo.com` / `Master2024`
- **Usuario de prueba**: `visualizador1` / `visual123`

- markdown
## 📸 Capturas de pantalla

*Próximamente*

## 🌐 Demo en vivo

*Próximamente (despliegue en Streamlit Cloud)*

## 🤝 Cómo contribuir

Las contribuciones son bienvenidas. Por favor, abre un *issue* o un *pull request* para discutir cambios importantes.

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.

## 📧 Contacto

Desarrollado por **Gian Pier Giraldo** – [GitHub](https://github.com/tu_usuario)

> **Nota sobre persistencia:** Actualmente la aplicación guarda los datos en archivos JSON locales. Para entornos de producción se recomienda migrar a una base de datos externa como Supabase (instrucciones próximamente).
