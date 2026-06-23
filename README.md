# veloX

**veloX** es una plataforma web de gestión documental inteligente para profesionales y empresas. Permite organizar documentos por secciones (Contabilidad, Laboral, Financiero, Logístico, Excel), con subcategorías, buscador, publicaciones del administrador y consultas entre usuarios.

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen)

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
- [Supabase](https://supabase.com/) – Base de datos y autenticación

## 📁 Estructura del repositorio
├── app.py # Aplicación principal
├── auth.py # Autenticación y gestión de usuarios
├── storage_manager.py # Gestión de archivos
├── message_manager.py # Mensajería
├── requirements.txt
├── README.md
├── .gitignore
├── assets/ # Imágenes y logos
├── data/ # Documentos legales y datos auxiliares
└── sql/ # Esquemas de base de datos

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

[veloxperu.streamlit.app](https://veloxperu.streamlit.app)

## 🤝 Cómo contribuir

Las contribuciones son bienvenidas. Por favor, abre un *issue* o un *pull request* para discutir cambios importantes.

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.

## 📧 Contacto

Desarrollado por **Gian Pier Giraldo** – [GitHub](https://github.com/tu_usuario)

> **Nota:** La aplicación utiliza Supabase para autenticación, almacenamiento y gestión de usuarios en producción.
