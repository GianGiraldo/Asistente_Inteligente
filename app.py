# app.py - Versión limpia y funcional (sin CSS conflictivo)
import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from auth import AuthManager
from message_manager import MessageManager
from notification_manager import NotificationManager
from storage_manager import StorageManager

st.set_page_config(
    page_title="Asistente Inteligente - Gestión Documental",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_managers():
    auth = AuthManager()
    storage = StorageManager()
    messages = MessageManager()
    notifications = NotificationManager()
    return auth, storage, messages, notifications

auth_manager, storage_manager, message_manager, notification_manager = init_managers()

SECCIONES = {
    "contabilidad": {
        "nombre": "📊 Contabilidad",
        "icono": "📊",
        "color": "#2ecc71",
        "descripcion": "Facturas, balances, libros contables",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "laboral": {
        "nombre": "👥 Laboral",
        "icono": "👥",
        "color": "#3498db",
        "descripcion": "Contratos, nóminas, documentos laborales",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "financiero": {
        "nombre": "💰 Financiero",
        "icono": "💰",
        "color": "#f1c40f",
        "descripcion": "Estados financieros, proyecciones",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "logistico": {
        "nombre": "🚚 Logístico",
        "icono": "🚚",
        "color": "#e67e22",
        "descripcion": "Guías, inventarios, despachos",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "excel": {
        "nombre": "📈 Excel",
        "icono": "📈",
        "color": "#1abc9c",
        "descripcion": "Plantillas, reportes, análisis",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    }
}

MENU_SIDEBAR_MASTER = [
    ("Inicio", "house", "🏠 Inicio"),
    ("Mis Documentos", "folder", "📁 Mis Documentos"),
    ("Gestión Usuarios", "people", "👥 Gestión Usuarios"),
    ("Consultas", "envelope", "📬 Consultas"),
    ("Configuración", "gear", "⚙️ Configuración"),
]
MENU_SIDEBAR_USER = [
    ("Inicio", "house", "🏠 Inicio"),
    ("Mis Documentos", "folder", "📁 Mis Documentos"),
    ("Consultas", "envelope", "📬 Consultas"),
    ("Mi Perfil", "person", "👤 Mi Perfil"),
]
SIDEBAR_MENU_STYLES = {
    "container": {"padding": "0!important", "background-color": "transparent"},
    "icon": {"color": "#b8c5d6", "font-size": "17px"},
    "nav-icon": {"font-size": "17px"},
    "nav-link": {
        "font-size": "15px",
        "text-align": "left",
        "margin": "4px 0",
        "padding": "10px 14px",
        "border-radius": "8px",
        "color": "#e2e8f0",
        "--hover-color": "#2a3f5f",
    },
    "nav-link-selected": {
        "background-color": "#ffffff",
        "color": "#1a2744",
        "font-weight": "600",
        "border-left": "4px solid #4a6fa5",
        "padding-left": "10px",
    },
}

# ==================== ESTILOS GLOBALES (solo estética, sin alterar layout) ====================
st.markdown("""
<style>
    /* Fondo general */
    .stApp {
        background: linear-gradient(135deg, #f5f7fc 0%, #e9eef5 100%);
    }
    /* Sidebar: el fondo oscuro se aplica tras el login en el bloque st.sidebar */
    /* Tarjetas de métricas */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dce5f0;
        border-radius: 20px;
        padding: 1rem;
        color: #1e2a3e;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    .metric-card h3 {
        color: #2c3e66;
        margin: 0;
        font-size: 1.8rem;
    }
    .metric-card p {
        color: #4a627a;
        margin: 0;
        font-size: 0.9rem;
    }
    /* Tarjetas de secciones */
    .section-card, .home-card {
        background: white;
        border-radius: 20px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
        border: 1px solid #e9eef3;
    }
    .section-card:hover, .home-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        border-color: #a0c4ff;
    }
    /* Botones */
    .stButton button {
        background-color: #4a6fa5;
        color: white;
        border-radius: 30px;
        border: none;
        transition: background-color 0.2s;
    }
    .stButton button:hover {
        background-color: #2c5282;
    }
    /* Encabezados */
    h1, h2, h3, h4 {
        color: #1e2a3e;
    }
    /* Selectbox */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 30px;
        border-color: #cbd5e1;
    }
    /* Popover */
    .stPopover {
        background-color: white;
        border-radius: 20px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    /* Footer */
    footer {
        color: #7f8c8d;
    }
</style>
""", unsafe_allow_html=True)

# ==================== PANTALLA DE LOGIN ====================
def login_screen():
    st.markdown("""
    <style>
        .login-subtitle {
            text-align: center;
            color: #4a627a;
            font-size: 0.95rem;
            line-height: 1.6;
            margin: 0.5rem 0 1.75rem 0;
        }
        [data-testid="stImage"] {
            display: flex;
            justify-content: center;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05);
            border: 1px solid #eef1f5 !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.25rem;
            margin-bottom: 0.5rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stFormSubmitButton"] button {
            width: 100% !important;
            background-color: #4a6fa5 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.65rem 1rem !important;
            font-weight: 600 !important;
            transition: background-color 0.2s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stFormSubmitButton"] button:hover {
            background-color: #2c5282 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col_login, col3 = st.columns([1.2, 1.5, 1.2])
    with col_login:
        # Logo centrado
        _l, logo_col, _r = st.columns([1, 1, 1])
        with logo_col:
            if os.path.exists("assets/velox.png"):
                st.image("assets/velox.png", width=200)
            else:
                st.warning("Logo no encontrado. Asegúrate de que assets/velox.png existe.")
                st.markdown("<h1 style='text-align:center; margin:0;'>velox</h1>", unsafe_allow_html=True)

        # Subtítulo centrado
        st.markdown("""
        <p class="login-subtitle">
            Encuentra cursos y plantillas personalizables<br>
            para potenciar tus habilidades
        </p>
        """, unsafe_allow_html=True)

        # Tarjeta del formulario
        with st.container(border=True):
            tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])

            with tab1:
                with st.form("login_form"):
                    email = st.text_input("Email (Gmail)", placeholder="tuemail@gmail.com")
                    password = st.text_input("Contraseña", type="password")
                    if st.form_submit_button("Iniciar Sesión", use_container_width=True):
                        valido, rol, nombre, secciones = auth_manager.verificar_usuario(email, password)
                        if valido:
                            st.session_state['autenticado'] = True
                            st.session_state['usuario'] = email
                            st.session_state['rol'] = rol
                            st.session_state['nombre'] = nombre
                            st.session_state['secciones'] = secciones
                            st.session_state['login_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            st.session_state['menu_principal'] = "🏠 Inicio"
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas")

            with tab2:
                with st.form("registro_form"):
                    nombre = st.text_input("Nombre completo")
                    email = st.text_input("Email (Gmail)", placeholder="tuemail@gmail.com")
                    password = st.text_input("Contraseña", type="password")
                    confirmar = st.text_input("Confirmar contraseña", type="password")
                    if st.form_submit_button("Registrarse", use_container_width=True):
                        if password != confirmar:
                            st.error("Las contraseñas no coinciden")
                        elif not email.endswith('@gmail.com'):
                            st.error("Solo se permiten cuentas de Gmail")
                        else:
                            exito, msg = auth_manager.registrar_usuario(email, password, nombre)
                            if exito:
                                st.success(msg)
                                st.info("Ahora puedes iniciar sesión")
                            else:
                                st.error(msg)

# ==================== NAVEGACIÓN INTERNA - INICIO ====================
def activar_seccion_inicio(seccion_id):
    st.session_state.seccion_activa = seccion_id
    subcategorias = SECCIONES.get(seccion_id, {}).get("subcategorias", ["General"])
    st.session_state.categoria_inicio = subcategorias[0]

def volver_al_inicio():
    st.session_state.seccion_activa = "inicio"

def seleccionar_categoria_inicio(categoria):
    st.session_state.categoria_inicio = categoria

def _formatear_fecha_notif(fecha_raw):
    if not fecha_raw:
        return "Fecha desconocida"
    try:
        texto = str(fecha_raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(texto)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return str(fecha_raw)[:16].replace("T", " ")

def _parsear_metadata_notif(metadata):
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str) and metadata.strip():
        try:
            return json.loads(metadata)
        except json.JSONDecodeError:
            return {}
    return {}

def _mostrar_alerta_publicacion(exito, resultado):
    """Muestra feedback de publicación según cuántas notificaciones se crearon."""
    if not exito:
        st.error(f"❌ Error en la publicación: {resultado}")
        return

    if isinstance(resultado, dict):
        count = resultado.get("notificaciones_creadas", 0)
        err = resultado.get("notificacion_error")
    else:
        count = 0
        err = None

    if count > 0:
        st.success(f"✅ Documento publicado. {count} alumno(s) notificado(s).")
    else:
        detalle = err or "Verifica que haya alumnos activos con acceso a esa sección."
        st.warning(f"⚠️ Documento publicado, pero no se notificó a ningún alumno. {detalle}")

def abrir_notificacion(notificacion_id, seccion, categoria=None):
    notification_manager.marcar_como_leida(notificacion_id, st.session_state["usuario"])
    st.session_state["menu_principal"] = "🏠 Inicio"
    st.session_state.seccion_activa = seccion or "inicio"
    if categoria and seccion:
        st.session_state.categoria_inicio = categoria

def render_campana_notificaciones():
    usuario = st.session_state["usuario"]
    no_leidas = notification_manager.contar_no_leidas(usuario)
    badge_text = str(no_leidas) if no_leidas < 100 else "99+"

    st.markdown("""
    <style>
        .notif-bell-anchor {
            position: relative;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            margin-bottom: -2.4rem;
            padding-right: 0.35rem;
            pointer-events: none;
            z-index: 2;
        }
        .notif-badge-pill {
            background: linear-gradient(135deg, #f5c518 0%, #f0a500 100%);
            color: #1a2744;
            border-radius: 999px;
            min-width: 22px;
            height: 22px;
            padding: 0 6px;
            font-size: 11px;
            font-weight: 800;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #ffffff;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
        }
        div[data-testid="stPopover"] > button {
            background: #f1f5f9 !important;
            border: 1px solid #dce5f0 !important;
            border-radius: 12px !important;
            font-size: 1.35rem !important;
            padding: 0.45rem 0.85rem !important;
            box-shadow: 0 2px 8px rgba(30, 42, 62, 0.08) !important;
        }
        div[data-testid="stPopover"] > button:hover {
            background: #e8eef5 !important;
            border-color: #4a6fa5 !important;
        }
        .notif-panel-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #1e2a3e;
            margin: 0 0 0.25rem 0;
        }
        .notif-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 8px;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #4a6fa5;
        }
        .notif-card-title {
            font-weight: 700;
            color: #1e2a3e;
            font-size: 0.95rem;
            margin-bottom: 4px;
        }
        .notif-card-msg {
            font-size: 0.82rem;
            color: #475569;
            margin-bottom: 6px;
            line-height: 1.45;
        }
        .notif-card-meta {
            font-size: 0.75rem;
            color: #64748b;
        }
    </style>
    """, unsafe_allow_html=True)

    if no_leidas > 0:
        st.markdown(
            f'<div class="notif-bell-anchor"><span class="notif-badge-pill">{badge_text}</span></div>',
            unsafe_allow_html=True,
        )

    with st.popover("🔔", use_container_width=True, help="Notificaciones pendientes"):
        st.markdown('<p class="notif-panel-title">Notificaciones</p>', unsafe_allow_html=True)
        st.caption("Publicaciones pendientes de leer")
        notificaciones = notification_manager.obtener_ultimas_no_leidas(usuario, limite=10)

        if not notificaciones:
            st.info("No tienes notificaciones pendientes.")
            return

        for notif in notificaciones:
            metadata = _parsear_metadata_notif(notif.get("metadata"))
            seccion = metadata.get("seccion", "")
            categoria = metadata.get("subcategoria") or metadata.get("categoria") or "General"
            seccion_nombre = SECCIONES.get(seccion, {}).get("nombre", seccion.capitalize() if seccion else "General")
            fecha_str = _formatear_fecha_notif(notif.get("fecha_creacion"))
            titulo = notif.get("titulo", "Nueva publicación")
            mensaje = notif.get("mensaje", "")

            st.markdown(f"""
            <div class="notif-card">
                <div class="notif-card-title">{titulo}</div>
                <div class="notif-card-msg">{mensaje}</div>
                <div class="notif-card-meta">📂 {seccion_nombre} · 🕐 {fecha_str}</div>
            </div>
            """, unsafe_allow_html=True)

            st.button(
                "Ver publicación →",
                key=f"notif_btn_{notif['id']}",
                use_container_width=True,
                on_click=abrir_notificacion,
                kwargs={
                    "notificacion_id": notif["id"],
                    "seccion": seccion,
                    "categoria": categoria,
                },
            )

def render_vista_seccion_inicio(seccion_id):
    if seccion_id not in SECCIONES:
        st.session_state.seccion_activa = "inicio"
        st.rerun()
        return

    seccion_info = SECCIONES[seccion_id]
    subcategorias = seccion_info.get("subcategorias", ["General"])
    if "categoria_inicio" not in st.session_state:
        st.session_state.categoria_inicio = subcategorias[0]

    if st.session_state["rol"] == "master":
        secciones_usuario = list(SECCIONES.keys())
    else:
        secciones_usuario = st.session_state.get("secciones", [])

    if seccion_id not in secciones_usuario:
        st.warning("No tienes acceso a esta sección.")
        st.button("⬅️ Volver al Inicio", key="btn_volver_inicio_denegado", on_click=volver_al_inicio)
        return

    st.button("⬅️ Volver al Inicio", key="btn_volver_inicio", on_click=volver_al_inicio)
    st.header(seccion_info["nombre"])
    st.markdown(f"""
    <div style="background: {seccion_info['color']}10; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <p style="margin:0;">{seccion_info['descripcion']}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📂 Categorías")
    categoria_actual = st.session_state.categoria_inicio
    cols_cat = st.columns(len(subcategorias))
    for idx, cat in enumerate(subcategorias):
        with cols_cat[idx]:
            st.button(
                cat,
                key=f"cat_inicio_{seccion_id}_{cat}",
                use_container_width=True,
                type="primary" if categoria_actual == cat else "secondary",
                on_click=seleccionar_categoria_inicio,
                kwargs={"categoria": cat},
            )

    st.markdown("---")
    busqueda = st.text_input("🔍 Buscar por nombre o descripción:", key=f"buscador_inicio_{seccion_id}")

    st.markdown("### 📢 Documentos disponibles")
    publicaciones = storage_manager.obtener_publicaciones_por_seccion(
        seccion=seccion_id,
        subcategoria=categoria_actual,
    )
    if busqueda:
        publicaciones = [
            p for p in publicaciones
            if busqueda.lower() in p.get("nombre_original", "").lower()
            or busqueda.lower() in p.get("descripcion", "").lower()
        ]

    if publicaciones:
        for i, pub in enumerate(publicaciones):
            col1, col2 = st.columns([4, 1])
            with col1:
                fecha = pub.get("fecha", pub.get("fecha_creacion", ""))[:10]
                st.markdown(
                    f"**📢 {pub.get('nombre_original', pub.get('titulo', 'Sin título'))}**  \n"
                    f"<small>{fecha}</small>\n\n"
                    f"{pub.get('descripcion', pub.get('mensaje', ''))}",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("📥 Descargar", key=f"down_inicio_{seccion_id}_{pub['id']}_{i}"):
                    exito, resultado = storage_manager.descargar_archivo(
                        pub["id"], st.session_state["usuario"], secciones_usuario
                    )
                    if exito:
                        st.markdown(
                            f'<a href="{resultado["url"]}" download="{resultado["nombre"]}">Descargar</a>',
                            unsafe_allow_html=True,
                        )
                        st.success("✅ Descarga disponible")
                    else:
                        st.error(f"❌ {resultado}")
            st.divider()
    else:
        st.info("No hay documentos en esta categoría.")

    if st.session_state["rol"] == "master":
        st.markdown("### 📄 Mis documentos personales")
        archivos_personales = storage_manager.listar_archivos_usuario(
            st.session_state["usuario"],
            seccion=seccion_id,
            subcategoria=categoria_actual,
            incluir_publicaciones=False,
        )
        if busqueda:
            archivos_personales = [
                a for a in archivos_personales
                if busqueda.lower() in a["nombre_original"].lower()
                or busqueda.lower() in a.get("descripcion", "").lower()
            ]
        if archivos_personales:
            for archivo in archivos_personales:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📄 **{archivo['nombre_original']}** — {archivo['fecha'][:10]}")
                with col2:
                    if st.button("📥", key=f"down_personal_inicio_{archivo['id']}"):
                        exito, resultado = storage_manager.descargar_archivo_personal(
                            archivo["id"], st.session_state["usuario"]
                        )
                        if exito:
                            st.markdown(
                                f'<a href="{resultado["url"]}" download="{resultado["nombre"]}">Descargar</a>',
                                unsafe_allow_html=True,
                            )
                            st.success("✅ Descarga disponible")
                        else:
                            st.error(f"❌ {resultado}")
                st.divider()
        else:
            st.info("No tienes documentos personales en esta categoría.")

# ==================== ESTADO DE AUTENTICACIÓN ====================
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'seccion_seleccionada' not in st.session_state:
    st.session_state['seccion_seleccionada'] = None
if 'seccion_activa' not in st.session_state:
    st.session_state.seccion_activa = "inicio"

if not st.session_state['autenticado']:
    login_screen()
else:
    # ==================== HEADER (solo después del login) ====================
    col_logo, col_user, col_logout = st.columns([1, 3, 1])
    with col_logo:
        st.markdown("<h1 style='font-size:1.5rem; margin:0;'>🌟 Asistente Inteligente</h1>", unsafe_allow_html=True)
    with col_user:
        nombre = st.session_state.get('nombre', 'Usuario')
        rol = st.session_state.get('rol', 'usuario')
        rol_texto = '👑 Master' if rol == 'master' else '👁️ Usuario'
        subcol1, subcol2 = st.columns([4, 1])
        with subcol1:
            st.markdown(f"**🌟 {nombre}**  \n<small>{rol_texto}</small>", unsafe_allow_html=True)
        with subcol2:
            render_campana_notificaciones()
    with col_logout:
        if st.button("🚪 Cerrar Sesión"):
            for key in ['autenticado', 'usuario', 'rol', 'nombre', 'secciones', 'login_time', 'seccion_seleccionada', 'seccion_activa', 'categoria_inicio']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    st.markdown("---")

    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.markdown("""
        <style>
            [data-testid="stSidebar"],
            [data-testid="stSidebar"] > div:first-child {
                background-color: #1a2744 !important;
                border-right: 1px solid #243656;
            }
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
                color: #f1f5f9 !important;
            }
            [data-testid="stSidebar"] hr {
                border-color: #2d3f5f;
            }
            [data-testid="stSidebar"] .stButton > button {
                background-color: #2d3f5f !important;
                color: #f1f5f9 !important;
                border: 1px solid #3d5278 !important;
                border-radius: 8px !important;
            }
            [data-testid="stSidebar"] .stButton > button:hover {
                background-color: #3d5278 !important;
                border-color: #4a6fa5 !important;
            }
            [data-testid="stSidebar"] iframe {
                width: 100% !important;
            }
            [data-testid="stSidebar"] .nav.flex-column {
                width: 100%;
            }
        </style>
        """, unsafe_allow_html=True)

        nombre_sidebar = st.session_state.get("nombre", "Usuario")
        rol_sidebar = st.session_state.get("rol", "usuario")
        rol_badge = "Administrador" if rol_sidebar == "master" else "Usuario"
        st.markdown(f"### Hola, {nombre_sidebar}")
        st.caption(f"Panel de navegación · {rol_badge}")

        menu_items = MENU_SIDEBAR_MASTER if rol_sidebar == "master" else MENU_SIDEBAR_USER
        menu_labels = [item[0] for item in menu_items]
        menu_icons = [item[1] for item in menu_items]
        menu_values = [item[2] for item in menu_items]
        label_to_value = dict(zip(menu_labels, menu_values))
        value_to_label = dict(zip(menu_values, menu_labels))

        if st.session_state.get("menu_principal") not in menu_values:
            st.session_state["menu_principal"] = menu_values[0]

        current_label = value_to_label.get(st.session_state["menu_principal"], menu_labels[0])
        default_index = menu_labels.index(current_label) if current_label in menu_labels else 0

        seleccion_label = option_menu(
            menu_title=None,
            options=menu_labels,
            icons=menu_icons,
            menu_icon="list",
            default_index=default_index,
            orientation="vertical",
            styles=SIDEBAR_MENU_STYLES,
            key="sidebar_option_menu",
        )

        seleccion = label_to_value[seleccion_label]
        if seleccion != st.session_state["menu_principal"]:
            st.session_state["menu_principal"] = seleccion
            if seleccion_label == "Inicio":
                st.session_state.seccion_activa = "inicio"
            st.rerun()

        st.divider()
        if st.button("Cerrar Sesión", icon="🚪", use_container_width=True, key="sidebar_logout"):
            for key in [
                "autenticado", "usuario", "rol", "nombre", "secciones",
                "login_time", "seccion_seleccionada", "seccion_activa", "categoria_inicio",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # ==================== CONTENIDO PRINCIPAL ====================
    menu_actual = st.session_state.get('menu_principal', '🏠 Inicio')

    if menu_actual == "🏠 Inicio":
        if st.session_state.seccion_activa == "inicio":
            if st.session_state['rol'] == 'master':
                st.header("🏠 Inicio")
                secciones_usuario = list(SECCIONES.keys())
                archivos_personales = storage_manager.listar_archivos_usuario(st.session_state['usuario'], incluir_publicaciones=False)
                publicaciones = storage_manager.obtener_publicaciones_usuario(st.session_state['usuario'], secciones_usuario)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'<div class="metric-card"><h3>📄</h3><h3>{len(archivos_personales)}</h3><p>Mis Documentos</p></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-card"><h3>📢</h3><h3>{len(publicaciones)}</h3><p>Documentos Disponibles</p></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-card"><h3>📂</h3><h3>{len(secciones_usuario)}</h3><p>Secciones</p></div>', unsafe_allow_html=True)
                with col4:
                    usuarios_total = len(auth_manager.listar_usuarios())
                    st.markdown(f'<div class="metric-card"><h3>👥</h3><h3>{usuarios_total}</h3><p>Usuarios</p></div>', unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📂 Todas las Secciones")
                cols = st.columns(3)
                for i, (seccion_id, seccion_info) in enumerate(SECCIONES.items()):
                    with cols[i % 3]:
                        docs_seccion = [d for d in publicaciones if d["seccion"] == seccion_id]
                        st.button(
                            f"{seccion_info['icono']} {seccion_info['nombre']}\n\n"
                            f"{seccion_info['descripcion']}\n\n"
                            f"✅ {len(docs_seccion)} documentos disponibles",
                            key=f"dashboard_btn_{seccion_id}",
                            use_container_width=True,
                            on_click=activar_seccion_inicio,
                            kwargs={"seccion_id": seccion_id},
                        )
            else:
                st.header("🏠 Inicio")
                secciones_usuario = st.session_state.get('secciones', [])
                if not secciones_usuario:
                    st.warning("No tienes secciones asignadas. Contacta al administrador.")
                else:
                    st.markdown("### 📂 Mis Secciones Asignadas")
                    cols = st.columns(3)
                    for i, sec_id in enumerate(secciones_usuario):
                        if sec_id in SECCIONES:
                            sec_info = SECCIONES[sec_id]
                            try:
                                docs_seccion = storage_manager.obtener_publicaciones_por_seccion(seccion=sec_id)
                                num_docs = len(docs_seccion)
                            except Exception:
                                num_docs = 0
                            with cols[i % 3]:
                                st.button(
                                    f"{sec_info['icono']} {sec_info['nombre']}\n\n"
                                    f"{sec_info['descripcion']}\n\n"
                                    f"📄 {num_docs} documentos disponibles",
                                    key=f"user_dashboard_btn_{sec_id}",
                                    use_container_width=True,
                                    on_click=activar_seccion_inicio,
                                    kwargs={"seccion_id": sec_id},
                                )
        else:
            render_vista_seccion_inicio(st.session_state.seccion_activa)

    elif menu_actual == "📁 Mis Documentos":
        seccion_preseleccionada = st.session_state.pop('seccion_seleccionada_documentos', None)
        categoria_redirigida = st.session_state.pop('categoria_redirigida', None)
        st.query_params.clear()

        st.header("📁 Mis Documentos")

        if st.session_state['rol'] == 'master':
            secciones_usuario = list(SECCIONES.keys())
        else:
            secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])

        if not secciones_usuario:
            st.warning("⚠️ No tienes acceso a ninguna sección. Contacta al administrador.")
        else:
            opciones_secciones = [(s, SECCIONES[s]['nombre']) for s in secciones_usuario]
            indice_preseleccionado = 0
            if seccion_preseleccionada:
                for idx, (sec_id, _) in enumerate(opciones_secciones):
                    if sec_id == seccion_preseleccionada:
                        indice_preseleccionado = idx
                        break

            seccion_seleccionada = st.selectbox(
                "Seleccionar sección:",
                options=opciones_secciones,
                format_func=lambda x: x[1],
                index=indice_preseleccionado,
                key="selector_seccion_documentos"
            )[0]
            seccion_info = SECCIONES[seccion_seleccionada]

            st.markdown(f"""
            <div style="background: {seccion_info['color']}10; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                <h3>{seccion_info['icono']} {seccion_info['nombre']}</h3>
                <p>{seccion_info['descripcion']}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔙 Volver al Dashboard"):
                st.rerun()

            subcategorias_disponibles = seccion_info.get("subcategorias", ["General"])
            st.markdown("### 📂 Categorías")

            if 'categoria_seleccionada' not in st.session_state:
                st.session_state['categoria_seleccionada'] = subcategorias_disponibles[0]

            if categoria_redirigida and categoria_redirigida in subcategorias_disponibles:
                st.session_state['categoria_seleccionada'] = categoria_redirigida

            cols_cat = st.columns(len(subcategorias_disponibles))
            for idx, cat in enumerate(subcategorias_disponibles):
                with cols_cat[idx]:
                    if st.button(cat, key=f"cat_{seccion_seleccionada}_{cat}", use_container_width=True,
                                 type="primary" if st.session_state['categoria_seleccionada'] == cat else "secondary"):
                        st.session_state['categoria_seleccionada'] = cat
                        st.rerun()

            categoria_actual = st.session_state['categoria_seleccionada']
            st.markdown(f"**Categoría actual:** {categoria_actual}")
            st.markdown("---")

            busqueda = st.text_input("🔍 Buscar por nombre o descripción:", key="buscador_mis_docs")

            # Documentos personales (solo master)
            archivos_personales = []
            if st.session_state['rol'] == 'master':
                with st.expander("📤 Subir documento personal", expanded=False):
                    archivo = st.file_uploader("Seleccionar archivo", type=['pdf', 'xlsx', 'xls', 'docx', 'doc'])
                    descripcion = st.text_area("Descripción (opcional)")
                    if archivo and st.button("Subir documento personal", type="primary"):
                        exito, resultado = storage_manager.guardar_archivo(
                            archivo, seccion_seleccionada, categoria_actual,
                            st.session_state['usuario'], descripcion, es_publicacion=False
                        )
                        if exito:
                            st.success(f"✅ Documento subido: {archivo.name}")
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {resultado}")

                st.markdown("### 📄 Mis documentos personales")
                archivos_personales = storage_manager.listar_archivos_usuario(
                    st.session_state['usuario'],
                    seccion=seccion_seleccionada,
                    subcategoria=categoria_actual,
                    incluir_publicaciones=False
                )
                if busqueda:
                    archivos_personales = [a for a in archivos_personales if
                                        busqueda.lower() in a['nombre_original'].lower() or
                                        busqueda.lower() in a.get('descripcion', '').lower()]

                if archivos_personales:
                    for archivo in archivos_personales:
                        cols = st.columns([3, 2, 2, 1, 1, 1])
                        with cols[0]:
                            st.write(f"📄 **{archivo['nombre_original']}**")
                        with cols[1]:
                            st.write(f"📅 {archivo['fecha'][:10]}")
                        with cols[2]:
                            tamaño_kb = archivo.get('tamaño_kb', archivo.get('tamaño_bytes', 0) / 1024)
                            st.write(f"💾 {tamaño_kb:.1f} KB")
                        with cols[3]:
                            if st.button("📥", key=f"download_{archivo['id']}"):
                                exito, resultado = storage_manager.descargar_archivo_personal(archivo['id'], st.session_state['usuario'])
                                if exito:
                                    st.markdown(f'<a href="{resultado["url"]}" download="{resultado["nombre"]}" style="background: #667eea; color: white; padding: 4px 12px; border-radius: 6px; text-decoration: none;">📥 Descargar</a>', unsafe_allow_html=True)
                                    st.success("✅ Descarga disponible")
                                else:
                                    st.error(f"❌ {resultado}")
                        with cols[4]:
                            if st.button("🌍 Publicar", key=f"publish_{archivo['id']}"):
                                st.session_state['archivo_a_publicar'] = archivo['id']
                                st.session_state['show_publish_form'] = True
                        with cols[5]:
                            if st.button("🗑️", key=f"delete_{archivo['id']}"):
                                storage_manager.eliminar_archivo(archivo['id'], st.session_state['usuario'])
                                st.rerun()
                        st.divider()
                else:
                    st.info("No tienes documentos personales en esta categoría")

            # Publicaciones del master
            st.markdown("### 📢 Publicaciones del Master")
            publicaciones = storage_manager.obtener_publicaciones_por_seccion(
                seccion=seccion_seleccionada,
                subcategoria=categoria_actual
            )
            if busqueda:
                publicaciones = [p for p in publicaciones if
                                busqueda.lower() in p.get('nombre_original', '').lower() or
                                busqueda.lower() in p.get('descripcion', '').lower()]

            if publicaciones:
                for i, pub in enumerate(publicaciones):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**📢 {pub.get('nombre_original', pub.get('titulo', 'Sin título'))}**  \n"
                                    f"<small>{pub.get('fecha', pub.get('fecha_creacion', ''))[:10]}</small>\n\n"
                                    f"{pub.get('descripcion', pub.get('mensaje', ''))}", unsafe_allow_html=True)
                    with col2:
                        if st.button("📥 Descargar", key=f"down_pub_{pub['id']}_{i}"):
                            if seccion_seleccionada in secciones_usuario:
                                exito, resultado = storage_manager.descargar_archivo(pub["id"], st.session_state['usuario'], [seccion_seleccionada])
                                if exito:
                                    st.markdown(f'<a href="{resultado["url"]}" download="{resultado["nombre"]}">Descargar</a>', unsafe_allow_html=True)
                                    st.success("✅ Descarga disponible")
                                else:
                                    st.error(f"❌ {resultado}")
                            else:
                                st.error("No tienes permiso para descargar este documento")
                    if st.session_state['rol'] == 'master':
                        col_edit, col_del = st.columns(2)
                        with col_edit:
                            if st.button("✏️ Editar", key=f"edit_{pub['id']}_{i}"):
                                st.session_state[f'editando_{pub["id"]}'] = True
                            if st.session_state.get(f'editando_{pub["id"]}', False):
                                nueva_desc = st.text_area("Nueva descripción", value=pub.get('descripcion', ''), key=f"newdesc_{pub['id']}")
                                if st.button("Guardar"):
                                    exito, msg = storage_manager.editar_publicacion(pub['id'], nueva_desc)
                                    if exito:
                                        st.success(msg)
                                        st.session_state.pop(f'editando_{pub["id"]}', None)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        with col_del:
                            if st.button("🗑️ Eliminar", key=f"del_{pub['id']}_{i}"):
                                storage_manager.eliminar_publicacion(pub['id'])
                                st.rerun()
                    st.divider()
            else:
                st.info("No hay publicaciones del master en esta categoría")

            if st.session_state.get('show_publish_form', False) and st.session_state['rol'] == 'master':
                with st.form("form_publish"):
                    st.markdown("### Publicar documento personal")
                    archivo_id = st.session_state['archivo_a_publicar']
                    seccion_dest = st.selectbox("Sección destino", list(SECCIONES.keys()), format_func=lambda x: SECCIONES[x]['nombre'])
                    subcat_dest = st.selectbox("Subcategoría", SECCIONES[seccion_dest]["subcategorias"])
                    comentario = st.text_area("Comentario")
                    if st.form_submit_button("Confirmar publicación"):
                        with st.spinner("Publicando y generando alertas..."):
                            exito, resultado = storage_manager.publicar_desde_personal(
                                archivo_id, st.session_state['usuario'], seccion_dest, subcat_dest, comentario
                            )
                        if exito:
                            _mostrar_alerta_publicacion(exito, resultado)
                            del st.session_state['show_publish_form']
                            del st.session_state['archivo_a_publicar']
                            st.rerun()
                        else:
                            st.error(resultado)

    # ==================== RESTO DE SECCIONES (sin cambios) ====================
    elif menu_actual == "👥 Gestión Usuarios" and st.session_state['rol'] == 'master':
        st.header("👥 Gestión de Usuarios y Permisos")
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuarios", "🔐 Asignar Secciones", "📢 Publicar Documentos"])
        with tab1:
            usuarios = auth_manager.listar_usuarios()
            if usuarios:
                data = []
                for email, u in usuarios.items():
                    secciones = auth_manager.obtener_secciones_usuario(email)
                    data.append({"Email": email, "Nombre": u["nombre"], "Rol": "👑 Master" if u["rol"]=="master" else "👤 Usuario", "Acceso": f"{len(secciones)}/{len(SECCIONES)}"})
                st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)
                st.markdown("---")
                usuarios_eliminar = [e for e in usuarios if e != st.session_state['usuario']]
                if usuarios_eliminar:
                    sel = st.selectbox("Usuario a eliminar", usuarios_eliminar)
                    if st.button("Eliminar", type="secondary"):
                        auth_manager.eliminar_usuario(sel, st.session_state['usuario'])
                        st.rerun()
            else:
                st.info("No hay usuarios")
        with tab2:
            st.markdown("Asignar secciones a usuario")
            usuarios_lista = [e for e in auth_manager.listar_usuarios() if e != st.session_state['usuario']]
            if usuarios_lista:
                usuario = st.selectbox("Usuario", usuarios_lista)
                actuales = auth_manager.obtener_secciones_usuario(usuario)
                nuevas = []
                cols = st.columns(3)
                for i, (k, v) in enumerate(SECCIONES.items()):
                    with cols[i%3]:
                        if st.checkbox(f"{v['icono']} {v['nombre']}", value=(k in actuales), key=f"perm_{usuario}_{k}"):
                            nuevas.append(k)
                if st.button("Guardar permisos"):
                    auth_manager.asignar_secciones_usuario(usuario, nuevas, st.session_state['usuario'])
                    st.rerun()
            else:
                st.info("No hay otros usuarios")
        with tab3:
            st.markdown("Publicar documento para todos")
            seccion = st.selectbox("Sección", list(SECCIONES.keys()), format_func=lambda x: SECCIONES[x]['nombre'])
            subcat = st.selectbox("Subcategoría", SECCIONES[seccion]["subcategorias"])
            archivo = st.file_uploader("Archivo", type=['pdf','xlsx','xls','docx','doc'])
            desc = st.text_area("Descripción")
            if archivo and st.button("Publicar", key="btn_publicar_gestion_usuarios"):
                with st.spinner("Subiendo archivo y notificando a los alumnos..."):
                    exito, resultado = storage_manager.publicar_documento(
                        archivo, seccion, subcat, desc,
                        publicador_email=st.session_state["usuario"],
                    )

                if exito:
                    _mostrar_alerta_publicacion(exito, resultado)
                    st.rerun()
                else:
                    st.error(f"❌ Error en la publicación: {resultado}")

    elif menu_actual == "⚙️ Configuración" and st.session_state['rol'] == 'master':
        st.header("Configuración")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Limpiar facturas (demo)"):
                st.warning("Función no implementada")
        with col2:
            st.info("Versión 1.0")

    elif menu_actual == "📬 Consultas":
        if st.session_state['rol'] == 'master':
            st.header("📬 Gestión de Consultas")
            st.caption("Revisa y responde las consultas enviadas por los usuarios de la plataforma.")

            # Consultas pendientes (no respondidas)
            pendientes = message_manager.obtener_mensajes_para_master(respondidos=False)
            st.markdown(f"### ⏳ Consultas pendientes ({len(pendientes)})")

            if not pendientes:
                st.info("No hay consultas pendientes por responder.")
            else:
                for msg in pendientes:
                    seccion_nombre = SECCIONES.get(msg["seccion"], {}).get("nombre", msg["seccion"].capitalize())
                    fecha = msg.get("fecha", "")
                    fecha_str = fecha[:16].replace("T", " ") if fecha else "Sin fecha"
                    with st.container(border=True):
                        col_info, col_badge = st.columns([4, 1])
                        with col_info:
                            st.markdown(
                                f"**👤 {msg['nombre_usuario']}** · `{msg['email']}`  \n"
                                f"**📂 Sección:** {seccion_nombre}  \n"
                                f"**📅** {fecha_str}"
                            )
                        with col_badge:
                            st.markdown(
                                '<span style="background:#fff3cd;color:#856404;padding:4px 10px;'
                                'border-radius:12px;font-size:0.8rem;">Pendiente</span>',
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f'<div style="background:#f8f9fa;border-radius:10px;padding:12px;'
                            f'border-left:4px solid #4a6fa5;margin:8px 0;">{msg["mensaje"]}</div>',
                            unsafe_allow_html=True,
                        )
                        respuesta = st.text_area(
                            "Escribir respuesta...",
                            key=f"resp_master_{msg['id']}",
                            height=100,
                            placeholder="Escribe aquí la respuesta para el usuario...",
                        )
                        if st.button("Enviar Respuesta", key=f"send_master_{msg['id']}", type="primary"):
                            if respuesta.strip():
                                exito = message_manager.responder_mensaje(
                                    msg["id"], respuesta.strip(), st.session_state["usuario"]
                                )
                                if exito:
                                    st.success("✅ Respuesta enviada correctamente")
                                    st.rerun()
                                else:
                                    st.error("❌ No se pudo guardar la respuesta. Intenta de nuevo.")
                            else:
                                st.warning("Escribe una respuesta antes de enviar.")

            # Consultas respondidas
            with st.expander("Ver consultas respondidas"):
                respondidas = message_manager.obtener_mensajes_para_master(respondidos=True)
                if not respondidas:
                    st.info("Aún no hay consultas respondidas.")
                else:
                    for msg in respondidas:
                        seccion_nombre = SECCIONES.get(msg["seccion"], {}).get("nombre", msg["seccion"].capitalize())
                        fecha_resp = msg.get("fecha_respuesta", "")
                        fecha_resp_str = fecha_resp[:16].replace("T", " ") if fecha_resp else ""
                        st.markdown(
                            f"**👤 {msg['nombre_usuario']}** · **📂 {seccion_nombre}**  \n"
                            f"**Consulta:** {msg['mensaje']}  \n"
                            f"**Respuesta:** {msg.get('respuesta', '')}  \n"
                            f"<small>Respondida el {fecha_resp_str}</small>",
                            unsafe_allow_html=True,
                        )
                        st.divider()
        else:
            # Usuario normal: enviar consulta
            st.header("📬 Mis Consultas")
            st.markdown("Envía tu consulta al administrador y revisa las respuestas recibidas.")
            secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
            if secciones_usuario:
                with st.container(border=True):
                    seccion = st.selectbox(
                        "Sección relacionada",
                        secciones_usuario,
                        format_func=lambda x: SECCIONES[x]['nombre'],
                    )
                    mensaje = st.text_area("Tu consulta", height=150, placeholder="Escribe tu pregunta aquí...")
                    if st.button("Enviar consulta", type="primary"):
                        if mensaje.strip():
                            exito, texto = message_manager.enviar_mensaje(
                                st.session_state['usuario'],
                                st.session_state['nombre'],
                                seccion,
                                mensaje.strip(),
                            )
                            if exito:
                                st.success(texto)
                                st.rerun()
                            else:
                                st.error(texto)
                        else:
                            st.warning("Escribe tu consulta antes de enviar.")
            else:
                st.warning("No tienes secciones asignadas. Contacta al administrador.")

            st.markdown("---")
            st.markdown("### 📋 Historial de consultas")
            historial = message_manager.obtener_mensajes_usuario(st.session_state['usuario'])
            if not historial:
                st.info("Aún no has enviado consultas.")
            else:
                for msg in historial:
                    seccion_nombre = SECCIONES.get(msg["seccion"], {}).get("nombre", msg["seccion"].capitalize())
                    respuesta = msg.get("respuesta")
                    estado = "✅ Respondida" if respuesta else "⏳ Pendiente"
                    with st.container(border=True):
                        st.markdown(f"**📂 {seccion_nombre}** · {estado}")
                        st.markdown(f"**Consulta:** {msg['mensaje']}")
                        if respuesta:
                            st.success(f"**Respuesta:** {respuesta}")
                        else:
                            st.info("**Respuesta:** Pendiente de respuesta por el administrador.")

    elif menu_actual == "👤 Mi Perfil":
        st.header("Mi Perfil")
        perfil = auth_manager.obtener_perfil(st.session_state['usuario'])
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Nombre:** {perfil['nombre']}")
            st.markdown(f"**Email:** {perfil['email']}")
            st.markdown(f"**Rol:** {perfil['rol'].upper()}")
        with col2:
            st.markdown("**Secciones asignadas:**")
            secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
            for s in secciones_usuario:
                st.markdown(f"- {SECCIONES[s]['nombre']}")
        st.markdown("---")
        with st.form("edit_perfil"):
            nombre = st.text_input("Nombre completo", value=perfil['nombre'])
            telefono = st.text_input("Teléfono", value=perfil.get('telefono',''))
            celular = st.text_input("Celular", value=perfil.get('celular',''))
            empresa = st.text_input("Empresa", value=perfil.get('empresa',''))
            cargo = st.text_input("Cargo", value=perfil.get('cargo',''))
            if st.form_submit_button("Guardar cambios"):
                auth_manager.actualizar_perfil(st.session_state['usuario'], {"nombre":nombre, "telefono":telefono, "celular":celular, "empresa":empresa, "cargo":cargo})
                st.session_state['nombre'] = nombre
                st.rerun()

    st.markdown("---")
    st.markdown("<div style='text-align:center'>Tu Gestor Documental Inteligente | © 2026</div>", unsafe_allow_html=True)