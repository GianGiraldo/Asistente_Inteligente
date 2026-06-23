# app.py — Asistente Inteligente veloX (OAuth Google + Business Hub)
import base64
import os

import streamlit as st

st.set_page_config(
    page_title="veloX",
    page_icon="assets/velox.png",
    layout="wide",
    initial_sidebar_state="expanded",  # Obliga sidebar abierta al cargar (también en móvil)
)

# Forzar nombre e ícono para aplicaciones móviles (PWA)
_velox_pwa_icon_href = "assets/velox.png"
if os.path.exists(_velox_pwa_icon_href):
    with open(_velox_pwa_icon_href, "rb") as _velox_icon_file:
        _velox_pwa_icon_href = (
            "data:image/png;base64,"
            + base64.b64encode(_velox_icon_file.read()).decode("ascii")
        )

st.markdown(
    f"""
    <meta name="apple-mobile-web-app-title" content="veloX">
    <meta name="application-name" content="veloX">
    <link rel="apple-touch-icon" href="{_velox_pwa_icon_href}">
    <link rel="icon" type="image/png" href="{_velox_pwa_icon_href}">
    <script>
    (function () {{
        var head = document.head || document.getElementsByTagName("head")[0];
        if (!head) return;
        document.title = "veloX";
        [
            ["apple-mobile-web-app-title", "veloX"],
            ["application-name", "veloX"],
        ].forEach(function (pair) {{
            var meta = document.querySelector('meta[name="' + pair[0] + '"]');
            if (!meta) {{
                meta = document.createElement("meta");
                meta.setAttribute("name", pair[0]);
                head.appendChild(meta);
            }}
            meta.setAttribute("content", pair[1]);
        }});
        [
            ["apple-touch-icon", "{_velox_pwa_icon_href}"],
            ["icon", "{_velox_pwa_icon_href}"],
        ].forEach(function (pair) {{
            var rel = pair[0];
            var href = pair[1];
            var link = document.querySelector('link[rel="' + rel + '"]');
            if (!link) {{
                link = document.createElement("link");
                link.setAttribute("rel", rel);
                if (rel === "icon") link.setAttribute("type", "image/png");
                head.appendChild(link);
            }}
            link.setAttribute("href", href);
        }});
        var manifest = {{
            name: "veloX",
            short_name: "veloX",
            icons: [{{ src: "{_velox_pwa_icon_href}", sizes: "512x512", type: "image/png" }}],
            display: "standalone",
            start_url: ".",
        }};
        var manifestLink = document.querySelector('link[rel="manifest"]');
        if (!manifestLink) {{
            manifestLink = document.createElement("link");
            manifestLink.setAttribute("rel", "manifest");
            head.appendChild(manifestLink);
        }}
        manifestLink.setAttribute(
            "href",
            "data:application/json," + encodeURIComponent(JSON.stringify(manifest))
        );
    }})();
    </script>
    """,
    unsafe_allow_html=True,
)

from ui_theme import inject_velox_loading_brand

if not st.session_state.get("_velox_loading_brand_injected"):
    inject_velox_loading_brand()
    st.session_state["_velox_loading_brand_injected"] = True

import base64
import contextlib
import html as html_module
import io
import json
import os
import re
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import pygwalker as pyg
import streamlit.components.v1 as components
from streamlit_option_menu import option_menu

from analytics_charts import (
    chart_acceso_usuarios,
    chart_actividad_secciones_usuario,
    chart_cobranzas_pendientes,
    chart_documentos_por_seccion,
)
from auth import AuthManager, SETUP_PASSWORD_REQUIRED
from message_manager import MessageManager
from notification_manager import (
    LIMITE_NOTIFICACIONES_CAMPANA,
    NotificationManager,
    normalizar_seccion,
)
from payment_manager import PaymentManager, MONTO_SOLES
from storage_manager import StorageManager
from ui_theme import (
    inject_global_theme,
    inject_section_catalog_css,
    inject_sidebar_theme,
    inject_welcome_layout,
    MAIN_CONTENT_AREA_CSS,
    VELOX_ULTRA_COMPACT_LAYOUT_CSS,
)

VELOX_BANNER_PATH = "assets/nuevo_banner_2026.png"


@contextlib.contextmanager
def _velox_spinner(detail: str = ""):
    """Spinner unificado con marca veloX."""
    mensaje = "⚡ Cargando veloX..."
    if detail:
        mensaje = f"⚡ Cargando veloX... {detail}"
    with st.spinner(mensaje):
        yield


VELOX_SIDEBAR_COLLAPSE_CONTROL_CSS = """
<style>
    /* Control de colapso gestionado centralizadamente por ui_theme.py */
</style>
"""


def inject_sidebar_collapse_control():
    """Placeholder: estilos de collapsedControl en VELOX_ULTRA_COMPACT_LAYOUT_CSS (ui_theme)."""
    st.markdown(VELOX_SIDEBAR_COLLAPSE_CONTROL_CSS, unsafe_allow_html=True)


VELOX_POST_LOGIN_SHELL_CSS = """
<style>
    /*
     * Shell post-login: respetar layout nativo de Streamlit.
     * Sin flex/margin-left/position:fixed en stAppViewContainer.
     */
    .stApp:not(:has(.velox-id-bar)) .main .block-container,
    .stApp:not(:has(.velox-id-bar)) [data-testid="stMain"] .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }

    .stApp:not(:has(.velox-id-bar)) [data-testid="stMain"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="stMainBlockContainer"],
    .stApp:not(:has(.velox-id-bar)) section.main,
    .stApp:not(:has(.velox-id-bar)) section.main > div {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }

    /* Banner elevado: compactación solo sobre el bloque del banner, no todo el main */
    .stApp:not(:has(.velox-id-bar)) .st-key-velox_top_banner,
    .stApp:not(:has(.velox-id-bar)) .st-key-velox_top_banner [data-testid="stElementContainer"],
    .stApp:not(:has(.velox-id-bar)) .st-key-velox_top_banner [data-testid="stImage"] {
        position: relative !important;
        z-index: 1 !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        padding-top: 0 !important;
        transform: none !important;
    }

    @media (min-width: 769px) {
        .stApp:not(:has(.velox-id-bar)) .st-key-velox_top_banner {
            margin-top: -20px !important;
            margin-bottom: 0 !important;
        }

        .stApp:not(:has(.velox-id-bar)) .st-key-velox_top_banner [data-testid="stImage"],
        .stApp:not(:has(.velox-id-bar)) .st-key-velox_top_banner [data-testid="stImage"] img {
            margin-top: 0 !important;
            padding-top: 0 !important;
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
        }
    }

    .stApp:not(:has(.velox-id-bar)) .st-key-velox_top_banner [data-testid="stImage"] img {
        max-width: 100% !important;
        object-fit: contain !important;
        display: block !important;
    }
</style>
"""


def inject_post_login_shell_layout():
    """Ordena capas y columnas del shell autenticado (sidebar vs. contenido central)."""
    st.markdown(VELOX_POST_LOGIN_SHELL_CSS, unsafe_allow_html=True)


VELOX_TOP_AREA_COMPACT_CSS = """
<style>
    /* Ocultación de decoración superior estándar */
    [data-testid="stDecoration"] {
        display: none !important;
    }

    /* Toolbar: ocultar solo con sidebar expandido (stExpandSidebarButton vive en stToolbar) */
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="true"]) [data-testid="stToolbar"] {
        display: none !important;
    }

    /* Reset estructural para compactar el main view */
    .stApp {
        margin-top: 0px !important;
    }
    [data-testid="stMainBlockContainer"], .main .block-container {
        padding-top: 0.5rem !important;
    }
</style>
"""


def render_velox_top_banner():
    """Banner principal post-login, compactado al tope del área central."""
    st.markdown(VELOX_TOP_AREA_COMPACT_CSS, unsafe_allow_html=True)
    if not os.path.exists(VELOX_BANNER_PATH):
        return
    with st.container(key="velox_top_banner"):
        st.image(VELOX_BANNER_PATH, use_container_width=True)


@st.cache_resource(show_spinner=False)
def init_managers(_cache_version=4):
    """Instancias singleton de managers (Supabase, Culqi, etc.) — una sola vez por proceso."""
    auth = AuthManager()
    storage = StorageManager()
    messages = MessageManager()
    notifications = NotificationManager()
    payments = PaymentManager()
    return auth, storage, messages, notifications, payments


VELOX_DATA_CACHE_VERSION_KEY = "velox_data_cache_version"


def _velox_data_cache_version() -> int:
    return int(st.session_state.get(VELOX_DATA_CACHE_VERSION_KEY, 0))


def _invalidar_cache_datos():
    """Fuerza recarga de lecturas cacheadas (documentos, usuarios, pagos)."""
    st.session_state[VELOX_DATA_CACHE_VERSION_KEY] = _velox_data_cache_version() + 1
    try:
        cached_obtener_publicaciones_por_seccion.clear()
        cached_listar_catalogo_seccion.clear()
        cached_listar_archivos_usuario.clear()
        cached_obtener_publicaciones_usuario.clear()
        cached_listar_usuarios.clear()
        cached_listar_pagos_pendientes.clear()
        cached_obtener_secciones_usuario.clear()
        cached_contar_publicaciones_por_seccion.clear()
    except Exception:
        pass


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_publicaciones_por_seccion(
    seccion: Optional[str] = None,
    subcategoria: Optional[str] = None,
    data_cache_version: int = 0,
):
    _, storage, _, _, _ = init_managers()
    return storage.obtener_publicaciones_por_seccion(seccion=seccion, subcategoria=subcategoria)


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_catalogo_seccion(
    seccion: str,
    subcategoria: Optional[str] = None,
    data_cache_version: int = 0,
):
    _, storage, _, _, _ = init_managers()
    return storage.listar_catalogo_seccion(seccion, subcategoria)


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_archivos_usuario(
    usuario: str,
    seccion: Optional[str] = None,
    subcategoria: Optional[str] = None,
    incluir_publicaciones: bool = False,
    data_cache_version: int = 0,
):
    _, storage, _, _, _ = init_managers()
    return storage.listar_archivos_usuario(
        usuario,
        seccion=seccion,
        subcategoria=subcategoria,
        incluir_publicaciones=incluir_publicaciones,
    )


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_publicaciones_usuario(
    usuario: str,
    secciones_usuario: tuple,
    data_cache_version: int = 0,
):
    _, storage, _, _, _ = init_managers()
    return storage.obtener_publicaciones_usuario(usuario, list(secciones_usuario))


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_usuarios(data_cache_version: int = 0):
    auth, _, _, _, _ = init_managers()
    return auth.listar_usuarios()


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_secciones_usuario(email: str, data_cache_version: int = 0):
    auth, _, _, _, _ = init_managers()
    return auth.obtener_secciones_usuario(email)


@st.cache_data(show_spinner=False, ttl=300)
def cached_contar_publicaciones_por_seccion(data_cache_version: int = 0) -> dict:
    _, storage, _, _, _ = init_managers()
    conteos: dict = {}
    for pub in storage.obtener_publicaciones_por_seccion():
        seccion = pub.get("seccion") or ""
        conteos[seccion] = conteos.get(seccion, 0) + 1
    return conteos


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_pagos_pendientes(data_cache_version: int = 0):
    _, _, _, _, payments = init_managers()
    return payments.listar_pagos_pendientes()

auth_manager, storage_manager, message_manager, notification_manager, payment_manager = init_managers()

# ==================== AUTH TEMPRANO (antes de UI de login) ====================
auth_manager.inicializar_estado_auth()
try:
    _auth_ok, _auth_msg = auth_manager.procesar_retorno_auth_url()
    if _auth_ok:
        st.rerun()
    if _auth_msg:
        st.session_state["auth_callback_error"] = _auth_msg
except Exception as e:
    st.session_state["auth_callback_error"] = f"Error de autenticación: {e}"

if not st.session_state.get("_velox_global_theme_injected"):
    inject_global_theme()
    st.session_state["_velox_global_theme_injected"] = True

SECCIONES = {
    "contabilidad": {
        "nombre": "📊 Contabilidad",
        "icono": "📊",
        "color": "#2ecc71",
        "descripcion": "Facturas, balances, libros contables",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "laboral": {
        "nombre": "📉 Power BI",
        "icono": "📉",
        "color": "#3498db",
        "descripcion": "Dashboards interactivos, análisis de datos y reportes visuales",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "financiero": {
        "nombre": "🌐 Comercio Exterior",
        "icono": "🌐",
        "color": "#f1c40f",
        "descripcion": "Importaciones, exportaciones, aduanas y operaciones internacionales",
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
    ("Cobranzas", "credit-card", "💳 Cobranzas"),
    ("Consultas", "envelope", "📬 Consultas"),
    ("Configuración", "gear", "⚙️ Configuración"),
]
MENU_SIDEBAR_USER = [
    ("Inicio", "house", "🏠 Inicio"),
    ("Mis Documentos", "folder", "📁 Mis Documentos"),
    ("Consultas", "envelope", "📬 Consultas"),
    ("Mi Perfil", "person", "👤 Mi Perfil"),
]
MENU_SIDEBAR_PERFIL = ("Mi Perfil", "person", "👤 Mi Perfil")
SIDEBAR_MENU_STYLES = {
    "container": {
        "padding": "8px 10px !important",
        "background-color": "#ffffff !important",
        "border-radius": "16px !important",
        "overflow": "hidden !important",
    },
    "icon": {"color": "#4a70a8", "font-size": "17px"},
    "nav-icon": {"font-size": "17px", "color": "#4a70a8"},
    "nav-link": {
        "display": "flex",
        "align-items": "center",
        "gap": "12px",
        "font-size": "14px",
        "text-align": "left",
        "white-space": "nowrap",
        "margin": "0 0 6px 0",
        "padding": "10px 12px",
        "border-radius": "12px",
        "color": "#1a2744",
        "background-color": "#F1F3F5",
        "font-weight": "600",
        "--hover-color": "#E4E8EE",
    },
    "nav-link-selected": {
        "display": "flex",
        "align-items": "center",
        "gap": "12px",
        "white-space": "nowrap",
        "text-align": "left",
        "background-color": "#1a2744",
        "color": "#ffffff",
        "font-weight": "700",
        "border-left": "none",
        "padding-left": "12px",
        "border-radius": "12px",
        "margin": "0 0 6px 0",
        "box-shadow": "0 4px 14px rgba(0, 0, 0, 0.22)",
    },
}

SIDEBAR_NAV_CAPSULE_CSS = """
<style>
    /* Panel blanco exterior del menú de módulos (option_menu) */
    [data-testid="stSidebar"] .st-key-sidebar_menu_panel {
        background-color: #ffffff !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        padding: 6px 8px !important;
        margin: 6px 0 10px !important;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.1) !important;
        border: 1px solid rgba(226, 232, 240, 0.95) !important;
    }
    [data-testid="stSidebar"] .st-key-sidebar_menu_panel [data-testid="stElementContainer"],
    [data-testid="stSidebar"] .st-key-sidebar_menu_panel [data-testid="stVerticalBlock"] {
        background: transparent !important;
    }
    [data-testid="stSidebar"] .st-key-sidebar_menu_panel iframe {
        display: block !important;
        width: 100% !important;
        border: none !important;
        border-radius: 14px !important;
    }
    /* Módulos del menú lateral — cápsulas redondeadas (solo sidebar) */
    [data-testid="stSidebar"] .nav,
    [data-testid="stSidebar"] .nav-pills,
    [data-testid="stSidebar"] .navbar-nav {
        background: transparent !important;
        gap: 6px;
    }
    [data-testid="stSidebar"] .nav-item {
        border-radius: 12px !important;
        overflow: hidden;
        margin: 0 0 6px 0 !important;
    }
    /* Inactivos: fondo gris claro delimitado sobre panel blanco */
    [data-testid="stSidebar"] .nav-link:not(.nav-link-selected),
    [data-testid="stSidebar"] a.nav-link:not(.nav-link-selected) {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        flex-wrap: nowrap !important;
        white-space: nowrap !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        background-color: #F1F3F5 !important;
        color: #1a2744 !important;
        border: 1px solid #E4E7EB !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
        font-weight: 600 !important;
        margin: 0 0 6px 0 !important;
        padding: 10px 12px !important;
        min-height: 2.65rem;
        line-height: 1.35 !important;
        text-align: left !important;
    }
    [data-testid="stSidebar"] .nav-link:not(.nav-link-selected):hover,
    [data-testid="stSidebar"] a.nav-link:not(.nav-link-selected):hover {
        background-color: #E4E8EE !important;
        color: #1a2744 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1) !important;
        border-color: #CBD5E1 !important;
    }
    [data-testid="stSidebar"] .nav-link-selected,
    [data-testid="stSidebar"] a.nav-link-selected {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        flex-wrap: nowrap !important;
        white-space: nowrap !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        background-color: #1a2744 !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.24), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        font-weight: 700 !important;
        margin: 0 0 6px 0 !important;
        padding: 10px 12px !important;
        text-align: left !important;
    }
    [data-testid="stSidebar"] .nav-link-selected:hover,
    [data-testid="stSidebar"] a.nav-link-selected:hover {
        background-color: #243556 !important;
        color: #ffffff !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28) !important;
    }
    [data-testid="stSidebar"] .nav-link .nav-icon,
    [data-testid="stSidebar"] .nav-link svg,
    [data-testid="stSidebar"] .nav-link-selected .nav-icon,
    [data-testid="stSidebar"] .nav-link-selected svg {
        display: inline-flex !important;
        align-items: center !important;
        flex-shrink: 0 !important;
        margin-right: 0 !important;
    }
    [data-testid="stSidebar"] .nav-link .nav-icon,
    [data-testid="stSidebar"] .nav-link svg {
        color: #4a70a8 !important;
        fill: #4a70a8 !important;
    }
    [data-testid="stSidebar"] .nav-link-selected .nav-icon,
    [data-testid="stSidebar"] .nav-link-selected svg {
        color: #ffffff !important;
        fill: #ffffff !important;
    }
    [data-testid="stSidebar"] .nav-link p,
    [data-testid="stSidebar"] .nav-link-selected p {
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        text-align: left !important;
        white-space: nowrap !important;
        flex: 1 1 auto !important;
        line-height: 1.2 !important;
    }
    /* Cerrar sesión y otros botones del sidebar (misma cápsula) */
    [data-testid="stSidebar"] .stButton > button {
        border-radius: 14px !important;
        transition: all 0.3s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 2.65rem !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.14) !important;
    }
    /* Logo y perfil compacto del sidebar */
    [data-testid="stSidebar"] .sidebar-brand-logo {
        display: block;
        margin: 0 auto;
        max-width: 112px;
        width: 100%;
        height: auto;
    }
    [data-testid="stSidebar"] .sidebar-profile--compact {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        text-align: center !important;
    }
    [data-testid="stSidebar"] .sidebar-profile-email--hero {
        color: #FFFFFF !important;
        text-align: center !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .sidebar-profile--compact [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] .sidebar-profile--compact [data-testid="stCaptionContainer"] p {
        color: rgba(255, 255, 255, 0.92) !important;
        text-align: center !important;
    }
</style>
"""

# ==================== ESTILOS GLOBALES (solo estética, sin alterar layout) ====================
st.markdown("""
<style>
    /* Shell general (sidebar conserva su azul vía SIDEBAR_CSS en ui_theme) */
    .stApp {
        background-color: #F8F9FA;
    }
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
    /* Encabezados — solo área central (no sidebar) */
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    section.main h1,
    section.main h2,
    section.main h3,
    section.main h4 {
        color: #0f172a;
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
    /* Campos de texto — fondo blanco y borde gris oscuro (global) */
    div[data-testid="stTextInput"] input,
    .stTextInput > div > div > input,
    .velox-portal-form div[data-testid="stTextInput"] input,
    .velox-portal-form .stTextInput > div > div > input,
    .main .block-container div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        color: #1A2332 !important;
        border: 1.5px solid #555555 !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
    }
    div[data-testid="stTextInput"] input:focus,
    .stTextInput > div > div > input:focus,
    .velox-portal-form div[data-testid="stTextInput"] input:focus,
    .velox-portal-form .stTextInput > div > div > input:focus,
    .main .block-container div[data-testid="stTextInput"] input:focus {
        border-color: #1A2332 !important;
        box-shadow: 0 0 0 1px #1A2332 !important;
        outline: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(MAIN_CONTENT_AREA_CSS, unsafe_allow_html=True)
st.markdown(VELOX_ULTRA_COMPACT_LAYOUT_CSS, unsafe_allow_html=True)
st.markdown(SIDEBAR_NAV_CAPSULE_CSS, unsafe_allow_html=True)

VELOX_TEXT_INPUT_CSS = """
<style>
    div[data-testid="stTextInput"] input,
    .stTextInput > div > div > input,
    .velox-portal-form div[data-testid="stTextInput"] input,
    .velox-portal-form .stTextInput > div > div > input,
    .main .block-container div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        color: #1A2332 !important;
        border: 1.5px solid #555555 !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
    }
    div[data-testid="stTextInput"] input:focus,
    .stTextInput > div > div > input:focus,
    .velox-portal-form div[data-testid="stTextInput"] input:focus,
    .velox-portal-form .stTextInput > div > div > input:focus,
    .main .block-container div[data-testid="stTextInput"] input:focus {
        border-color: #1A2332 !important;
        box-shadow: 0 0 0 1px #1A2332 !important;
        outline: none !important;
    }
</style>
"""


def inject_velox_text_input_styles():
    st.markdown(VELOX_TEXT_INPUT_CSS, unsafe_allow_html=True)


def inject_olvido_password_link_styles():
    st.markdown(FORGOT_PASSWORD_LINK_CSS, unsafe_allow_html=True)


def inject_login_portal_brand_styles():
    st.markdown(LOGIN_PORTAL_BRAND_CSS, unsafe_allow_html=True)

# ==================== PASARELA DE BIENVENIDA veloX (Premium) ====================
YAPE_QR_PATH = "assets/qr_pago.png"
WHATSAPP_ADMIN_LINK = "https://w.app/s58dpa"
YAPE_OAUTH_KEYS = ["yape_oauth_celular", "yape_comprobante_upload"]
WELCOME_TAB_LOGIN = 0
WELCOME_TAB_REGISTER = 1
WELCOME_TAB_SETUP_PASSWORD = 2
VISTA_LOGIN = "login"
VISTA_RECUPERAR_PASSWORD = "recuperar_password"
MIN_PASSWORD_RECUPERACION = 6
VELOX_ROJO_CORPORATIVO = "#C41E3A"
VELOX_ROJO_CORPORATIVO_HOVER = "#9B1830"
VELOX_AZUL_MARCA = "#1A2332"
VELOX_AZUL_MARCA_HOVER = "#243044"
VELOX_CIAN_MARCA = "#00B4D8"
VELOX_CIAN_MARCA_HOVER = "#0096B8"

LOGIN_PORTAL_BRAND_CSS = f"""
<style>
    /* Portal de autenticación: flex-start en contenedor elástico (responsivo a zoom) */
    html:has(.velox-id-bar),
    body:has(.velox-id-bar),
    .stApp:has(.velox-id-bar),
    .stApp:has(.velox-id-bar) div.stAppViewContainer,
    .stApp:has(.velox-id-bar) [data-testid="stAppViewContainer"] {{
        padding-top: 0px !important;
        margin-top: 0px !important;
        top: 0 !important;
    }}
    .stApp:has(.velox-id-bar) [data-testid="stHeader"],
    .stApp:has(.velox-id-bar) header {{
        display: none !important;
        height: 0px !important;
        opacity: 0 !important;
        margin: 0px !important;
        padding: 0px !important;
    }}
    .stApp:has(.velox-id-bar) [data-testid="stMain"] > div,
    .stApp:has(.velox-id-bar) section.main > div {{
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        align-items: center !important;
        height: 100vh !important;
        min-height: 100vh !important;
        padding-top: 0px !important;
        margin-top: 0px !important;
    }}
    .stApp:has(.velox-id-bar) div.stAppViewContainer > section.main > div.block-container,
    .stApp:has(.velox-id-bar) [data-testid="stAppViewContainer"] > section.main > div.block-container,
    .stApp:has(.velox-id-bar) .main .block-container {{
        padding-top: 20px !important;
        margin-top: 0px !important;
        transform: none !important;
        max-width: 440px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: block !important;
        position: static !important;
        width: min(440px, calc(100vw - 1.5rem)) !important;
    }}
    .stApp:has(.velox-id-bar) .main .block-container [data-testid="stVerticalBlock"],
    .stApp:has(.velox-id-bar) .velox-portal-body [data-testid="stVerticalBlock"],
    .stApp:has(.velox-id-bar) .velox-portal-form [data-testid="stVerticalBlock"] {{
        transform: none !important;
        gap: 0.5rem !important;
        width: 100% !important;
        padding-top: 0px !important;
        margin-top: 0px !important;
    }}
    .stApp:has(.velox-id-bar) [data-testid="stVerticalBlock"] > div:first-child,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > div:first-child,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"]:first-child {{
        margin-top: 0px !important;
        margin-bottom: -10px !important;
        padding-top: 0px !important;
    }}
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > div:nth-child(even),
    .stApp:has(.velox-id-bar) .velox-portal-form [data-testid="element-container"]:first-of-type,
    .stApp:has(.velox-id-bar) [data-testid="stVerticalBlockBorderWrapper"] + [data-testid="element-container"] {{
        margin-top: -2px !important;
    }}
    .stApp:has(.velox-id-bar) .velox-brand-stack {{
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }}

    /* Tarjeta blanca del login: columna central al ancho completo del bloque */
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type {{
        width: 100% !important;
        justify-content: center !important;
    }}
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(1),
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(1),
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(3),
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(3) {{
        display: none !important;
    }}
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2),
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) {{
        max-width: 440px !important;
        width: 100% !important;
        flex: 1 1 100% !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }}
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] {{
        max-width: 440px !important;
        width: 100% !important;
        margin: 0 auto !important;
    }}

    /* Barra superior del formulario de acceso */
    .stApp:has(.velox-id-bar) .velox-id-bar,
    .stApp:has(.velox-id-bar) .velox-id-bar--register {{
        margin: 0.65rem 0.75rem 0.25rem !important;
    }}
    .velox-id-bar,
    .velox-id-bar--register,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] .velox-id-bar,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] .velox-id-bar {{
        background: {VELOX_CIAN_MARCA} !important;
        background-image: none !important;
        border: none !important;
        border-bottom: none !important;
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        margin: 0.65rem 0.75rem 0.85rem !important;
        padding: 0.72rem 1rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}

    /* Botones principales: Iniciar Sesión y Registrarme */
    .st-key-btn_iniciar_sesion_velox [data-testid="stBaseButton-primary"] button,
    .st-key-btn_iniciar_sesion_velox .stButton > button,
    .st-key-btn_registrarme_portal .stButton > button,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-primary"] button,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .st-key-btn_registrarme_portal .stButton > button {{
        background: {VELOX_CIAN_MARCA} !important;
        background-color: {VELOX_CIAN_MARCA} !important;
        background-image: none !important;
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        border: 1px solid {VELOX_CIAN_MARCA} !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 14px rgba(0, 180, 216, 0.35) !important;
        transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    .st-key-btn_iniciar_sesion_velox [data-testid="stBaseButton-primary"] button p,
    .st-key-btn_iniciar_sesion_velox .stButton > button p,
    .st-key-btn_registrarme_portal .stButton > button p,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button p,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-primary"] button p,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .st-key-btn_registrarme_portal .stButton > button p,
    .st-key-btn_iniciar_sesion_velox [data-testid="stBaseButton-primary"] button span,
    .st-key-btn_iniciar_sesion_velox .stButton > button span,
    .st-key-btn_registrarme_portal .stButton > button span,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button span,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-primary"] button span,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .st-key-btn_registrarme_portal .stButton > button span {{
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
    }}

    .st-key-btn_iniciar_sesion_velox [data-testid="stBaseButton-primary"] button:hover,
    .st-key-btn_iniciar_sesion_velox .stButton > button:hover,
    .st-key-btn_registrarme_portal .stButton > button:hover,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button:hover,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-primary"] button:hover,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .st-key-btn_registrarme_portal .stButton > button:hover {{
        background: {VELOX_CIAN_MARCA_HOVER} !important;
        background-color: {VELOX_CIAN_MARCA_HOVER} !important;
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        border-color: {VELOX_CIAN_MARCA_HOVER} !important;
        box-shadow: 0 6px 18px rgba(0, 150, 184, 0.42) !important;
    }}

    .st-key-btn_iniciar_sesion_velox [data-testid="stBaseButton-primary"] button:focus,
    .st-key-btn_iniciar_sesion_velox .stButton > button:focus,
    .st-key-btn_registrarme_portal .stButton > button:focus,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button:focus,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-primary"] button:focus,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .st-key-btn_registrarme_portal .stButton > button:focus {{
        background: {VELOX_CIAN_MARCA} !important;
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        border-color: {VELOX_CIAN_MARCA} !important;
        box-shadow: 0 0 0 2px rgba(0, 180, 216, 0.35) !important;
    }}

    /* Campos del formulario de login: foco alineado con el cian de marca */
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) div[data-testid="stTextInput"] input:focus,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) div[data-testid="stTextInput"] input:focus,
    .velox-portal-form div[data-testid="stTextInput"] input:focus,
    .velox-portal-form .stTextInput > div > div > input:focus {{
        border-color: {VELOX_CIAN_MARCA} !important;
        box-shadow: 0 0 0 1px {VELOX_CIAN_MARCA} !important;
    }}
</style>
"""

FORGOT_PASSWORD_LINK_CSS = f"""
<style>
    .st-key-btn_olvido_password {{
        display: flex !important;
        justify-content: flex-end !important;
        width: 100% !important;
    }}
    .st-key-btn_olvido_password [data-testid="stButton"],
    .st-key-btn_olvido_password .stButton {{
        width: auto !important;
        margin: 0 !important;
    }}
    .st-key-btn_olvido_password .stButton > button {{
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: {VELOX_ROJO_CORPORATIVO} !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        text-decoration: underline !important;
        text-underline-offset: 2px;
        padding: 0 !important;
        min-height: auto !important;
        height: auto !important;
        line-height: 1.4 !important;
        width: auto !important;
        white-space: nowrap;
    }}
    .st-key-btn_olvido_password .stButton > button:hover,
    .st-key-btn_olvido_password .stButton > button:focus,
    .st-key-btn_olvido_password .stButton > button:active {{
        color: {VELOX_ROJO_CORPORATIVO_HOVER} !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
</style>
"""

GOOGLE_SVG_ICON = (
    '<svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">'
    '<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.13 13.09 17.62 9.5 24 9.5z"/>'
    '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.56 2.95-2.24 5.46-4.72 7.15l7.19 5.58C43.98 37.13 48 31.18 48 24.55z"/>'
    '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C2.38 15.62 0 20.94 0 26.5s2.38 10.88 6.44 14.79l7.98-6.19z"/>'
    '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.19-5.58c-2.01 1.35-4.59 2.15-8.7 2.15-6.38 0-11.78-4.25-13.71-10.07l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>'
    "</svg>"
)

MSG_REGISTRO_YAPE_OK = (
    "🎉 ¡Registro recibido correctamente! Tu código de operación ya fue enviado al panel "
    "del Administrador Master. Procesaremos tu activación en unos minutos. ¡Bienvenido!"
)
MSG_REGISTRO_COMPLETADO = (
    "¡Registro completado con éxito! Tu acceso a veloX está siendo procesado. "
    "Si pagaste con Tarjeta tu acceso ya está activo; si pagaste con Yape/Plim, "
    "estará habilitado en breve tras la confirmación de la captura."
)
REGISTRO_SESSION_KEYS = (
    "registro_en_progreso",
    "registro_email_ok",
    "registro_pago_ok",
    "registro_metodo_pago_usado",
    "registro_password_ok",
    "registro_listo_confirmacion",
    "registro_email",
)


def render_google_oauth_button(
    label: str = "Iniciar sesión con Google",
    oauth_url: Optional[str] = None,
) -> bool:
    if st.session_state.pop("google_oauth_force_refresh", False):
        auth_manager.ensure_google_oauth_url(force_refresh=True)

    redirect_esperado = auth_manager.obtener_redirect_url()
    if st.session_state.get("google_oauth_redirect") not in (None, redirect_esperado):
        auth_manager.ensure_google_oauth_url(force_refresh=True)

    url = oauth_url or st.session_state.get("google_oauth_url")
    if not url:
        url = auth_manager.ensure_google_oauth_url(force_refresh=True)
    if url:
        st.markdown(
            f'<div class="google-btn-wrap"><a href="{url}" target="_self">'
            f"{GOOGLE_SVG_ICON} {label}</a></div>",
            unsafe_allow_html=True,
        )
        return True

    detalle = st.session_state.pop("google_oauth_error", None)
    st.error(
        detalle
        or (
            "No se pudo iniciar OAuth. Define `[app].base_url` en secrets (o `VELOX_BASE_URL`) "
            "y agrega esa URL en Supabase → Authentication → Redirect URLs."
        )
    )
    with st.expander("Diagnóstico OAuth (sin secretos)", expanded=False):
        for clave, valor in auth_manager.obtener_diagnostico_oauth().items():
            st.text(f"{clave}: {valor}")
        st.caption(
            "Flujo: Supabase Auth (no Google directo). redirect_to activo: "
            f"{redirect_esperado} — raíz de la app, sin /oauth2callback."
        )
    return False


VELOX_LOGO_PATH = "assets/velox.png"
VELOX_LOGO_BLANCO_PATH = "assets/logo_blanco.png"
VELOX_LOGO_SINFONDO_PATH = "assets/logo_blanco_sinfondo.png"


@st.cache_data(show_spinner=False)
def _velox_logo_data_uri(path: str = VELOX_LOGO_PATH) -> Optional[str]:
    """Data URI del logo local para incrustarlo en HTML sin depender de st.image."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_velox_brand_header():
    logo_src = _velox_logo_data_uri()
    if logo_src:
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; width: 100%; margin-top: 10px; margin-bottom: 5px;">
                <img src="{logo_src}" width="190" alt="veloX" style="display: block; margin: 0 auto; max-width: 190px; height: auto;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="display: flex; justify-content: center; align-items: center; width: 100%; '
            'margin-top: 10px; margin-bottom: 5px;">'
            '<div class="velox-logo-fallback">⚡ veloX</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="velox-brand-stack">'
        '<p class="velox-tagline velox-tagline--center">Accede a cursos, plantillas y herramientas '
        "profesionales con un único pago de acceso</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def _open_portal_scroll():
    st.markdown('<div class="velox-portal-scroll">', unsafe_allow_html=True)
    st.markdown('<div class="velox-portal-body">', unsafe_allow_html=True)


def _close_portal_scroll():
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_activation_banner():
    if st.session_state.get("autenticado") and not st.session_state.get("acceso_pagado"):
        nombre = st.session_state.get("nombre", "Usuario")
        st.markdown(
            f'<div class="velox-activation-banner">'
            f"<strong>{nombre}</strong>, completa tu activación en "
            f"<em>Registro (pago)</em> para ingresar al hub veloX."
            f"</div>",
            unsafe_allow_html=True,
        )


def render_divider_or(text: str = "o ingresa con tu cuenta administradora"):
    st.markdown(
        f'<div class="velox-divider-or"><span>{text}</span></div>',
        unsafe_allow_html=True,
    )


def _init_welcome_tab_state():
    if "welcome_active_tab" not in st.session_state:
        st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN


def _init_login_form_state():
    if st.session_state.get("login_recordarme") and st.session_state.get("login_email_saved"):
        if "login_email" not in st.session_state:
            st.session_state.login_email = st.session_state.login_email_saved
    elif "login_recordarme" not in st.session_state:
        st.session_state.login_recordarme = bool(st.session_state.get("login_email_saved"))


def _reset_registro_flujo():
    for key in REGISTRO_SESSION_KEYS:
        st.session_state.pop(key, None)


def _iniciar_registro_flujo():
    _reset_registro_flujo()
    st.session_state.registro_en_progreso = True


def _registro_bloquea_acceso_app() -> bool:
    """Evita entrar al hub hasta pulsar OK al final del registro."""
    return bool(st.session_state.get("registro_en_progreso"))


def _marcar_pago_registro_completado(metodo: str):
    st.session_state.registro_pago_ok = True
    st.session_state.registro_metodo_pago_usado = metodo


def _finalizar_registro_y_volver_login():
    _reset_registro_flujo()
    st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
    auth_manager.cerrar_sesion(silent=True)
    st.rerun()


def render_portal_id_bar():
    """Barra corporativa de identificación (sin botón Registro flotante)."""
    _init_welcome_tab_state()
    active = st.session_state.welcome_active_tab

    if active == WELCOME_TAB_LOGIN:
        st.markdown(
            '<div class="velox-id-bar">Correo Electrónico</div>',
            unsafe_allow_html=True,
        )
    elif active == WELCOME_TAB_SETUP_PASSWORD:
        st.markdown(
            '<div class="velox-id-bar velox-id-bar--register">Configura tu acceso veloX</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="velox-back-login">', unsafe_allow_html=True)
        if st.button("← Volver al inicio de sesión", key="nav_volver_login_setup"):
            st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
            st.session_state.pop("velox_setup_email", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="velox-id-bar velox-id-bar--register">Registro y activación</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="velox-back-login">', unsafe_allow_html=True)
        if st.button("← Volver al inicio de sesión", key="nav_volver_login"):
            _reset_registro_flujo()
            auth_manager.cerrar_sesion(silent=True)
            st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


@st.dialog("Recuperar contraseña")
def _dialog_recuperar_password():
    st.markdown(
        "Ingresa tu correo electrónico y te enviaremos un enlace para restablecer tu contraseña."
    )
    email_recuperacion = st.text_input(
        "Correo electrónico",
        value=(st.session_state.get("login_email") or "").strip(),
        key="recuperar_password_email",
        placeholder="Correo electrónico",
    )
    if st.button(
        "Enviar enlace de recuperación",
        type="primary",
        use_container_width=True,
        key="btn_enviar_recuperacion_password",
    ):
        with _velox_spinner("Enviando enlace..."):
            ok, msg = auth_manager.enviar_enlace_recuperacion_password(email_recuperacion)
        if ok:
            st.success(msg)
        else:
            st.error(msg)


def _en_vista_recuperacion_password() -> bool:
    return auth_manager.en_modo_recuperacion_password()


def _validar_passwords_recuperacion(nueva: str, confirmar: str) -> Optional[str]:
    nueva_l = (nueva or "").strip()
    confirmar_l = (confirmar or "").strip()
    if not nueva_l or not confirmar_l:
        return "Completa ambos campos de contraseña."
    if len(nueva_l) < MIN_PASSWORD_RECUPERACION:
        return f"La contraseña debe tener al menos {MIN_PASSWORD_RECUPERACION} caracteres."
    if nueva_l != confirmar_l:
        return "Las contraseñas no coinciden."
    return None


def render_tab_recuperar_password():
    """Formulario exclusivo tras enlace de recuperación Supabase."""
    st.markdown('<div class="velox-portal-body velox-portal-body--login">', unsafe_allow_html=True)
    st.markdown('<div class="velox-portal-form">', unsafe_allow_html=True)

    st.markdown(
        '<div class="velox-id-bar velox-id-bar--register">Restablecer Contraseña</div>',
        unsafe_allow_html=True,
    )
    st.caption("Define una nueva contraseña para tu cuenta veloX.")

    email_recuperacion = (st.session_state.get("recovery_email") or "").strip()
    if email_recuperacion:
        st.caption(f"Cuenta: **{email_recuperacion}**")

    nueva_password = st.text_input(
        "Nueva Contraseña",
        type="password",
        key="recovery_new_password",
        placeholder="Mínimo 6 caracteres",
    )
    confirmar_password = st.text_input(
        "Confirmar Contraseña",
        type="password",
        key="recovery_confirm_password",
        placeholder="Repite la contraseña",
    )

    if st.button(
        "Actualizar Contraseña",
        type="primary",
        key="btn_actualizar_password_recuperacion",
        use_container_width=True,
    ):
        error_validacion = _validar_passwords_recuperacion(nueva_password, confirmar_password)
        if error_validacion:
            st.error(error_validacion)
        else:
            with _velox_spinner("Actualizando contraseña..."):
                ok, msg = auth_manager.completar_recuperacion_password(nueva_password.strip())
            if ok:
                st.success(msg)
                st.info("Redirigiendo al inicio de sesión...")
                time.sleep(2)
                auth_manager.finalizar_recuperacion_password()
                st.rerun()
            else:
                st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_tab_login_portal(oauth_url: Optional[str] = None):
    """Portada: correo/contraseña, Iniciar Sesión y enlace a Registrarme."""
    _ = oauth_url
    _init_login_form_state()
    st.session_state["oauth_intent"] = "login"

    denied = st.session_state.pop("oauth_login_denied_msg", None)
    if denied:
        st.error(denied)

    st.markdown('<div class="velox-portal-body velox-portal-body--login">', unsafe_allow_html=True)
    st.markdown('<div class="velox-portal-form">', unsafe_allow_html=True)

    st.text_input(
        "Correo electrónico",
        key="login_email",
        label_visibility="collapsed",
        placeholder="Correo electrónico",
    )
    st.text_input(
        "Contraseña",
        type="password",
        key="login_password",
        label_visibility="collapsed",
        placeholder="Contraseña",
    )

    inject_olvido_password_link_styles()
    recordarme_col, forgot_col = st.columns([3, 1], vertical_alignment="center")
    with recordarme_col:
        st.toggle("Recordarme", key="login_recordarme")
    with forgot_col:
        if st.button("¿Olvidaste tu contraseña?", key="btn_olvido_password"):
            _dialog_recuperar_password()

    if st.session_state.get("login_recordarme") and st.session_state.get("login_email"):
        st.session_state.login_email_saved = st.session_state.login_email.strip()

    if st.button(
        "Iniciar Sesión",
        type="primary",
        key="btn_iniciar_sesion_velox",
        use_container_width=True,
    ):
        with _velox_spinner("Validando credenciales..."):
            exito, msg = auth_manager.iniciar_sesion_velox(
                st.session_state.get("login_email", ""),
                st.session_state.get("login_password", ""),
            )
        if msg == SETUP_PASSWORD_REQUIRED:
            st.session_state.welcome_active_tab = WELCOME_TAB_SETUP_PASSWORD
            st.rerun()
        elif exito:
            st.rerun()
        else:
            st.error(msg)

    if st.button("Registrarme", key="btn_registrarme_portal", use_container_width=True):
        _iniciar_registro_flujo()
        st.session_state.welcome_active_tab = WELCOME_TAB_REGISTER
        st.session_state["oauth_intent"] = "register"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_tab_setup_password_velox():
    """Primera configuración de contraseña veloX para cuentas ya aprobadas."""
    email = (st.session_state.get("velox_setup_email") or st.session_state.get("login_email") or "").strip().lower()
    if not email:
        st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
        st.rerun()

    _open_portal_scroll()
    st.markdown(
        '<p class="velox-section-caption" style="text-align:center;margin-bottom:1rem;">'
        "Configura tu contraseña exclusiva para veloX. "
        "Tus permisos actuales (rol, acceso y pago) se mantienen intactos."
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="velox-identity-badge" style="margin-bottom:1rem;">'
        f"✅ Cuenta verificada: <strong>{email}</strong></div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="velox-portal-form">', unsafe_allow_html=True)
    st.text_input(
        "Nueva contraseña veloX",
        type="password",
        key="velox_setup_password",
        label_visibility="collapsed",
        placeholder="Nueva contraseña (mín. 6 caracteres)",
    )
    st.text_input(
        "Confirmar contraseña veloX",
        type="password",
        key="velox_setup_password_confirm",
        label_visibility="collapsed",
        placeholder="Confirmar contraseña",
    )

    st.markdown('<div class="velox-btn-primary">', unsafe_allow_html=True)
    if st.button("Guardar contraseña y continuar", key="btn_guardar_password_velox", use_container_width=True):
        with _velox_spinner("Guardando contraseña de forma segura..."):
            exito, msg = auth_manager.configurar_password_velox(
                email,
                st.session_state.get("velox_setup_password", ""),
                st.session_state.get("velox_setup_password_confirm", ""),
            )
        if exito:
            st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    _close_portal_scroll()


def _permitir_navegacion_iframe_componentes():
    """Permite redirección top-level desde iframes de componentes (token Culqi)."""
    components.html(
        """
<script>
(function () {
  function patchIframes() {
    document.querySelectorAll("iframe[sandbox]").forEach(function (iframe) {
      if (!iframe.sandbox.contains("allow-top-navigation-by-user-activation")) {
        iframe.sandbox.add("allow-top-navigation-by-user-activation");
      }
    });
  }
  patchIframes();
  new MutationObserver(patchIframes).observe(document.body, { childList: true, subtree: true });
})();
</script>
""",
        height=0,
    )


def _sincronizar_token_culqi_query() -> bool:
    """Lee culqi_token de la URL (iframe Culqi) y lo guarda en session_state."""
    raw = st.query_params.get("culqi_token")
    if not raw:
        return False
    token = str(raw).strip()
    if not token:
        return False
    st.session_state["culqi_oauth_token"] = token
    try:
        del st.query_params["culqi_token"]
    except Exception:
        pass
    return True


def _procesar_culqi_si_hay_token():
    token = (st.session_state.get("culqi_oauth_token") or "").strip()
    if not token:
        return
    if not st.session_state.get("autenticado"):
        st.warning("Verifica tu cuenta con Google antes de pagar con tarjeta.")
        return
    with _velox_spinner("Procesando cargo Culqi y activando acceso..."):
        exito, msg = payment_manager.procesar_pago_culqi_oauth(
            st.session_state["usuario"],
            st.session_state.get("nombre", ""),
            token,
        )
    if exito:
        auth_manager.refrescar_estado_acceso()
        st.session_state.pop("culqi_oauth_token", None)
        if st.session_state.get("registro_en_progreso"):
            _marcar_pago_registro_completado("culqi")
            st.rerun()
        st.success(f"✅ {msg}")
        st.rerun()
    else:
        st.error(f"❌ {msg}")


def _render_culqi_checkout_section():
    st.markdown('<p class="velox-section-title">Pago seguro con tarjeta</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="velox-section-caption">Activación inmediata tras confirmación Culqi.</p>',
        unsafe_allow_html=True,
    )

    if _sincronizar_token_culqi_query():
        _procesar_culqi_si_hay_token()

    _permitir_navegacion_iframe_componentes()

    _, culqi_col, _ = st.columns([0.2, 1.6, 0.2])
    with culqi_col:
        public_key = payment_manager.obtener_public_key_culqi()
        if not public_key:
            st.error("Configura culqi.public_key en `.streamlit/secrets.toml`.")
            return

        components.html(
            payment_manager.html_culqi_checkout(public_key),
            height=payment_manager.culqi_checkout_height(),
            scrolling=False,
        )

        token_actual = (st.session_state.get("culqi_oauth_token") or "").strip()
        if not token_actual:
            st.text_input(
                "Token Culqi (solo si la confirmación automática falla)",
                placeholder="tok_test_…",
                key="culqi_oauth_token",
                label_visibility="collapsed",
            )
            st.caption(
                "Tras pagar en Culqi, la confirmación se procesa sola. "
                "Si no ocurre, pega aquí el token y pulsa confirmar."
            )
        else:
            st.success(f"Token Culqi recibido: `{token_actual[:16]}…`")

        if st.button(
            "Confirmar pago Culqi y activar acceso",
            type="primary",
            use_container_width=True,
            key="btn_confirmar_culqi",
            disabled=not (st.session_state.get("culqi_oauth_token") or "").strip(),
        ):
            _procesar_culqi_si_hay_token()


def _render_yape_plim_section():
    email = st.session_state.get("usuario", "")
    nombre = st.session_state.get("nombre", "")

    col_pago, col_form = st.columns([1, 1.12], gap="large")

    with col_pago:
        st.markdown('<div class="velox-qr-panel">', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<p class="velox-section-title">Escanea y paga</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="velox-section-caption">Transferencia con Yape o Plim. '
                "El pago puede ser tuyo o de un tercero.</p>",
                unsafe_allow_html=True,
            )
            if os.path.exists(YAPE_QR_PATH):
                st.image(YAPE_QR_PATH, caption="Escanea con Yape o Plim", use_container_width=True)
            else:
                st.warning(f"No se encontró `{YAPE_QR_PATH}`")
            st.caption("💡 Conserva la captura de tu comprobante.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_form:
        with st.container(border=True):
            st.markdown(
                '<p class="velox-section-title">Datos de verificación</p>',
                unsafe_allow_html=True,
            )
            if nombre:
                st.text_input("Nombre (desde Google)", value=nombre, disabled=True)

            comprobante = st.file_uploader(
                "📸 Adjunta la captura o foto de tu comprobante de pago",
                type=["jpg", "jpeg"],
                key="yape_comprobante_upload",
            )

            celular = st.text_input(
                "Celular de la operación",
                placeholder="999888777",
                max_chars=9,
                key="yape_oauth_celular",
            )

            puede_enviar = comprobante is not None and bool(str(celular or "").strip())
            if st.button(
                "🚀 Enviar verificación y registrarme",
                use_container_width=True,
                type="primary",
                key="btn_enviar_yape",
                disabled=not puede_enviar,
            ):
                try:
                    progress = st.progress(0, text="Subiendo comprobante...")
                    progress.progress(35, text="Conectando con Supabase...")
                    exito, msg = payment_manager.registrar_comprobante_yape_oauth(
                        email=email,
                        nombre=nombre,
                        celular=celular,
                        comprobante_file=comprobante,
                    )
                    progress.progress(100, text="Listo")
                    if exito:
                        for k in YAPE_OAUTH_KEYS:
                            st.session_state.pop(k, None)
                        _marcar_pago_registro_completado("yape")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                except Exception as e:
                    st.error(f"❌ Error inesperado: {e}")
            elif not comprobante:
                st.caption("Adjunta tu captura JPEG para habilitar el envío.")
            elif not str(celular or "").strip():
                st.caption("Ingresa el celular de la operación para continuar.")


def _render_registro_paso_password():
    st.markdown("---")
    st.markdown(
        """
        <div style="background-color: rgba(255, 255, 255, 0.85); padding: 10px 15px; border-radius: 6px; font-size: 1.15rem; font-weight: bold; color: #1A2332; display: inline-block; margin-bottom: 10px; border: 1px solid #E0E0E0;">
            PASO 3 · CREAR CONTRASEÑA
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="velox-section-caption">Define tu contraseña exclusiva para ingresar a veloX '
        "con correo y clave en futuros accesos.</p>",
        unsafe_allow_html=True,
    )

    email = st.session_state.get("usuario", "")
    st.markdown(
        f'<div class="velox-identity-badge">✅ Pago registrado · <strong>{email}</strong></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="velox-portal-form" style="margin-top:1rem;">', unsafe_allow_html=True)
    st.text_input(
        "Crea tu contraseña de acceso",
        type="password",
        key="registro_password",
        label_visibility="collapsed",
        placeholder="Crea tu contraseña de acceso",
    )
    st.text_input(
        "Confirma tu contraseña",
        type="password",
        key="registro_password_confirm",
        label_visibility="collapsed",
        placeholder="Confirma tu contraseña",
    )

    st.markdown('<div class="velox-btn-primary">', unsafe_allow_html=True)
    if st.button("Guardar Contraseña", key="btn_guardar_password_registro", use_container_width=True):
        with _velox_spinner("Guardando contraseña de forma segura..."):
            exito, msg = auth_manager.guardar_password_registro(
                email,
                st.session_state.get("registro_password", ""),
                st.session_state.get("registro_password_confirm", ""),
                email,
            )
        if exito:
            st.session_state.registro_password_ok = True
            st.session_state.registro_listo_confirmacion = True
            st.rerun()
        else:
            st.error(msg)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_registro_confirmacion_final():
    st.markdown(
        f"""
        <div class="velox-register-success">
            <div class="velox-register-success__icon">✅</div>
            <div class="velox-register-success__title">¡Registro completado!</div>
            <p class="velox-register-success__text">{MSG_REGISTRO_COMPLETADO}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="velox-btn-primary">', unsafe_allow_html=True)
    if st.button("OK", key="btn_registro_ok_final", use_container_width=True):
        _finalizar_registro_y_volver_login()
    st.markdown("</div>", unsafe_allow_html=True)


def render_tab_adquirir_acceso(oauth_url: Optional[str] = None):
    _ = oauth_url
    if not st.session_state.get("registro_en_progreso"):
        _iniciar_registro_flujo()

    _open_portal_scroll()
    st.markdown(
        """
        <div style="background-color: #1A2332; color: #FFFFFF; text-align: center; padding: 12px 24px; border-radius: 10px; font-weight: bold; font-size: 1.1rem; margin-top: 15px; margin-bottom: 20px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05);">
            Completa paso 1, paso 2 y paso 3 ¡Rapido y Seguro!
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("registro_listo_confirmacion"):
        _render_registro_confirmacion_final()
        _close_portal_scroll()
        return

    if st.session_state.get("registro_pago_ok"):
        _render_registro_paso_password()
        _close_portal_scroll()
        return

    logo_blanco_src = _velox_logo_data_uri(VELOX_LOGO_BLANCO_PATH)
    logo_blanco_html = (
        f'<img src="{logo_blanco_src}" width="65" alt="veloX" '
        f'style="display: block; border-radius: 4px;">'
        if logo_blanco_src
        else ""
    )
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 15px; background-color: rgba(255, 255, 255, 0.85); padding: 12px 20px; border-radius: 8px; border: 1px solid #E0E0E0;">
            <div style="font-size: 1.15rem; font-weight: bold; color: #1A2332;">
                PASO 1 · CORREO ELECTRÓNICO
            </div>
            <div>
                {logo_blanco_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<p class="velox-section-title">Correo electrónico</p>', unsafe_allow_html=True)

    paso1_ok = bool(st.session_state.get("registro_email_ok"))

    if not paso1_ok:
        st.markdown(
            '<p class="velox-section-caption">Ingresa tu correo electrónico para continuar con el registro.</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="velox-portal-form">', unsafe_allow_html=True)
        st.text_input(
            "Correo electrónico",
            key="registro_email",
            label_visibility="collapsed",
            placeholder="Correo electrónico",
        )
        st.markdown('<div class="velox-btn-primary">', unsafe_allow_html=True)
        if st.button("Continuar", key="btn_registro_continuar_email", use_container_width=True):
            email_ingresado = (st.session_state.get("registro_email") or "").strip()
            with _velox_spinner("Validando correo..."):
                ok, msg, ir_login = auth_manager.continuar_registro_manual(email_ingresado)
            if ir_login:
                st.error(msg)
                _reset_registro_flujo()
                auth_manager.cerrar_sesion(silent=True)
                st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
                if email_ingresado:
                    st.session_state.login_email = email_ingresado.strip().lower()
                st.rerun()
            elif ok:
                st.rerun()
            else:
                st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        _close_portal_scroll()
        return

    email = st.session_state.get("usuario", "")
    st.markdown(
        f'<div class="velox-identity-badge">✅ Correo registrado: '
        f"<strong>{email}</strong></div>",
        unsafe_allow_html=True,
    )

    col_spacer, col_logout = st.columns([5, 1])
    with col_logout:
        st.markdown('<div class="velox-logout-link">', unsafe_allow_html=True)
        if st.button("Salir", key="btn_logout_adquirir", use_container_width=True):
            _reset_registro_flujo()
            auth_manager.cerrar_sesion()
            st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        """
        <div style="background-color: rgba(255, 255, 255, 0.85); padding: 10px 15px; border-radius: 6px; font-size: 1.15rem; font-weight: bold; color: #1A2332; display: inline-block; margin-bottom: 10px; border: 1px solid #E0E0E0;">
            PASO 2 · PAGO DEL SERVICIO
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="velox-section-caption">Elige cómo deseas activar tu acceso veloX.</p>',
        unsafe_allow_html=True,
    )

    if "gateway_metodo_pago" not in st.session_state:
        st.session_state["gateway_metodo_pago"] = "yape"

    metodo = st.radio(
        "Método de pago",
        options=["yape", "culqi"],
        format_func=lambda x: "📱 Yape / Plim" if x == "yape" else "💳 Tarjeta (Culqi)",
        horizontal=True,
        key="gateway_metodo_pago",
        label_visibility="collapsed",
    )

    if metodo == "yape":
        _render_yape_plim_section()
    else:
        _render_culqi_checkout_section()
    _close_portal_scroll()


def render_pantalla_solo_recuperacion():
    """Pantalla exclusiva de restablecimiento; nunca muestra login/registro."""
    inject_welcome_layout()
    inject_velox_text_input_styles()
    inject_login_portal_brand_styles()
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        render_velox_brand_header()
        with st.container(border=True):
            render_tab_recuperar_password()
    render_footer()


def render_welcome_gateway():
    """Pantalla premium centrada: login y adquisición de acceso."""
    inject_welcome_layout()
    inject_velox_text_input_styles()
    inject_login_portal_brand_styles()
    oauth_url = auth_manager.ensure_google_oauth_url(
        force_refresh=st.session_state.get("google_oauth_redirect")
        != auth_manager.obtener_redirect_url()
    )

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        render_velox_brand_header()
        render_activation_banner()

        with st.container(border=True):
            render_portal_id_bar()

            if st.session_state.welcome_active_tab == WELCOME_TAB_LOGIN:
                render_tab_login_portal(oauth_url=oauth_url)
            elif st.session_state.welcome_active_tab == WELCOME_TAB_SETUP_PASSWORD:
                render_tab_setup_password_velox()
            else:
                render_tab_adquirir_acceso(oauth_url=oauth_url)


def login_screen():
    render_welcome_gateway()
    render_footer()


# ==================== FOOTER LEGAL Y PÁGINAS INTERNAS ====================
LEGAL_DOCS_DIR = "data"


def _leer_documento_legal(nombre_archivo: str) -> str:
    path = os.path.join(LEGAL_DOCS_DIR, nombre_archivo)
    if not os.path.exists(path):
        return (
            "El documento legal no está disponible en este momento. "
            "Por favor, contacte a soporte@veloxperu.com."
        )
    with open(path, encoding="utf-8") as f:
        return f.read()


def render_footer() -> None:
    """Footer legal centrado para login y dashboard."""
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; padding: 1rem 0; font-size: 0.85rem; color: #64748b;'>
            <a href='https://docs.google.com/forms/d/e/1FAIpQLSexps1r4DvjE4EgNYzCw6e8G7SomSupJVikKnKADA8nVhRW5w/viewform?usp=public+editor' target='_blank' style='color: #4a6fa5; text-decoration: none; margin: 0 10px;'>📖 Libro de Reclamaciones</a>
            <span style='color: #cbd5e1;'>|</span>
            <a href='https://drive.google.com/file/d/1EGm93-Y3S3RD6pbw4J1AzTyrNI2goiyg/view?usp=sharing' target='_blank' style='color: #4a6fa5; text-decoration: none; margin: 0 10px;'>📄 Términos y Condiciones</a>
            <span style='color: #cbd5e1;'>|</span>
            <a href='https://drive.google.com/file/d/11pns9IKiw3cRR_b9WpSaT00cWAEkM3NG/view?usp=sharing' target='_blank' style='color: #4a6fa5; text-decoration: none; margin: 0 10px;'>🔒 Política de Privacidad</a>
            <br>
            <span style='font-size: 0.75rem;'>© 2026 veloX - Todos los derechos reservados</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_terminos_condiciones() -> None:
    inject_welcome_layout()
    inject_global_theme()
    st.markdown(
        '<div style="max-width:820px;margin:0 auto;padding:1rem 1.25rem 2rem;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="velox-legal-back">'
        '<a href="?" style="color:#5c6370;text-decoration:none;">← Volver al inicio</a>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_leer_documento_legal("terminos_condiciones.txt"))
    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()


def mostrar_politica_privacidad() -> None:
    inject_welcome_layout()
    inject_global_theme()
    st.markdown(
        '<div style="max-width:820px;margin:0 auto;padding:1rem 1.25rem 2rem;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="velox-legal-back">'
        '<a href="?" style="color:#5c6370;text-decoration:none;">← Volver al inicio</a>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_leer_documento_legal("politica_privacidad.txt"))
    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()


# ==================== CHATBOT ASISTENTE IA (flotante) ====================
CHATBOT_MENUS_PERMITIDOS = frozenset({"🏠 Inicio", "📁 Mis Documentos"})

MOCK_CATALOGO_CHATBOT = [
    {"nombre": "Plantilla_Calculo_CTS_Mype.xlsx", "carpeta": "Contabilidad", "acceso": True},
    {"nombre": "Dashboard_Finanzas_Master.pbix", "carpeta": "Power BI", "acceso": False},
    {"nombre": "Matriz_Costos_Importacion.xlsx", "carpeta": "Comercio Exterior", "acceso": True},
    {"nombre": "Guia_Control_Inventarios.xlsx", "carpeta": "Logístico", "acceso": True},
    {"nombre": "Formatos_Analisis_Procesos.xlsx", "carpeta": "Excel", "acceso": False},
]

CHATBOT_SYSTEM_PROMPT = """
Eres el Asistente Inteligente veloX. Ante consultas sobre documentos del catálogo debes aplicar SIEMPRE estas reglas:

1. UBICACIÓN: Indica de forma explícita en qué carpeta/categoría se encuentra el archivo recomendado
   (ejemplo: "Este archivo se encuentra en la sección de Contabilidad").

2. CON ACCESO (acceso=True): Explica brevemente la utilidad del archivo y ofrece un enlace o botón simulado de descarga.

3. SIN ACCESO (acceso=False): Está PROHIBIDO ofrecer descargas o alternativas. Responde únicamente con:
   "Acceso Bloqueado. Este documento se encuentra en una sección que no tienes disponible en tu plan actual."

Catálogo disponible:
{catalogo}
""".strip()

CHATBOT_DOC_KEYWORDS = {
    "Plantilla_Calculo_CTS_Mype.xlsx": ("cts", "mype", "calculo", "plantilla cts", "liquidacion"),
    "Dashboard_Finanzas_Master.pbix": ("dashboard", "finanzas", "power bi", "pbix", "master"),
    "Matriz_Costos_Importacion.xlsx": ("matriz", "importacion", "costos", "comercio exterior", "aduana"),
    "Guia_Control_Inventarios.xlsx": ("inventario", "inventarios", "logistico", "logístico", "control stock"),
    "Formatos_Analisis_Procesos.xlsx": ("formatos", "analisis", "análisis", "procesos", "excel"),
}

CHATBOT_MSG_BLOQUEADO = (
    "Acceso Bloqueado. Este documento se encuentra en una sección que no tienes disponible en tu plan actual."
)


def _chatbot_visible_en_modulo_actual() -> bool:
    menu = st.session_state.get("menu_principal", "🏠 Inicio")
    return menu in CHATBOT_MENUS_PERMITIDOS


CHATBOT_MAX_MENSAJES = 12


def _build_chatbot_panel_css() -> str:
    """CSS del pop-up: un solo st.container(key=velox_chat_panel) anclado al viewport."""
    return """
<style>
    /* Anclar solo el panel (evita que :has() fije contenedores ancestros) */
    .stApp div[data-testid="stElementContainer"]:has(> div.st-key-velox_chat_panel),
    .stApp div[data-testid="stElementContainer"]:has(> [data-testid="stVerticalBlock"].st-key-velox_chat_panel) {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
        border: none !important;
        background: transparent !important;
    }

    .stApp .st-key-velox_chat_panel {
        position: fixed !important;
        bottom: 100px !important;
        right: 25px !important;
        left: auto !important;
        z-index: 999990 !important;
        width: 380px !important;
        max-width: 380px !important;
        background: #ffffff !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15) !important;
        border: 1px solid #e8ecf1 !important;
        padding: 12px 14px 10px !important;
        box-sizing: border-box !important;
        gap: 8px !important;
    }

    .stApp .st-key-velox_chat_panel [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 6px !important;
        margin: 0 !important;
    }

    .stApp .st-key-velox_chat_panel p {
        font-size: 18px !important;
        font-weight: bold !important;
        color: #31333F !important;
        margin: 0 !important;
        padding-top: 2px !important;
    }

    .stApp .st-key-velox_chat_panel
    [data-testid="stHorizontalBlock"]:first-of-type
    div[data-testid="column"]:last-child div.stButton > button {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
        border-radius: 50% !important;
        width: 30px !important;
        min-width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        float: right !important;
        box-shadow: none !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
    }

    .stApp .st-key-velox_chat_panel
    [data-testid="stHorizontalBlock"]:first-of-type
    div[data-testid="column"]:last-child div.stButton > button:hover {
        background-color: #ff4b4b !important;
        color: #ffffff !important;
    }

    .stApp .st-key-velox_chat_historial {
        border: none !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    .stApp .st-key-velox_chat_historial [data-testid="stMarkdown"] {
        padding: 0 !important;
    }

    .stApp .st-key-velox_chat_inputs div[data-testid="stTextInput"] label {
        display: none !important;
    }

    .stApp .st-key-velox_chat_inputs div[data-testid="stTextInput"] input {
        background-color: #ffffff !important;
        color: #31333f !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        font-size: 0.86rem !important;
        height: 42px !important;
    }

    .stApp .st-key-velox_chat_inputs div.stButton > button {
        width: 100% !important;
        height: 42px !important;
        min-height: 42px !important;
        background-color: #f0f2f6 !important;
        border: 1px solid #e0e0e0 !important;
        color: #31333f !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    .stApp .st-key-velox_chat_inputs div.stButton > button:hover {
        background-color: #4F75A8 !important;
        color: #ffffff !important;
        border-color: #4F75A8 !important;
    }

    /* Ocultar FAB mientras el chat está abierto */
    .stApp:has(.st-key-velox_chat_panel)
    div[data-testid="stElementContainer"]:has(.velox-chat-fab-marker)
    + div[data-testid="stElementContainer"] {
        display: none !important;
    }

    .velox-chat-msg {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 10px;
    }

    .velox-chat-msg--user { justify-content: flex-end; }

    .velox-chat-msg-avatar {
        width: 26px;
        height: 26px;
        object-fit: contain;
        border-radius: 6px;
        flex-shrink: 0;
    }

    .velox-chat-msg-avatar--fallback {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #1A2332;
        color: #fff;
        font-size: 0.75rem;
    }

    .velox-chat-msg-bubble {
        max-width: 82%;
        padding: 8px 11px;
        border-radius: 12px;
        font-size: 0.86rem;
        line-height: 1.45;
        color: #1A2332;
    }

    .velox-chat-msg--assistant .velox-chat-msg-bubble {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
    }

    .velox-chat-msg--user .velox-chat-msg-bubble {
        background: #4F75A8;
        color: #ffffff;
    }
</style>
"""


def _init_chatbot_state():
    if "chat_abierto" not in st.session_state:
        st.session_state.chat_abierto = False
    if "chat_historial" not in st.session_state:
        st.session_state.chat_historial = [
            {
                "role": "assistant",
                "content": (
                    "¡Hola! Soy tu **Asistente veloX**. Puedo orientarte sobre documentos en "
                    "**Contabilidad**, **Power BI**, **Comercio Exterior**, **Logístico** y **Excel**. "
                    "¿Qué plantilla o reporte necesitas?"
                ),
            }
        ]


def _es_mensaje_bienvenida_chat(mensaje: dict) -> bool:
    return mensaje.get("role") == "assistant" and "Asistente veloX" in mensaje.get("content", "")


def _podar_chat_historial():
    """Ventana rotativa: conserva el saludo inicial y como máximo 12 mensajes en total."""
    historial = st.session_state.chat_historial
    if len(historial) <= CHATBOT_MAX_MENSAJES:
        return
    if historial and _es_mensaje_bienvenida_chat(historial[0]):
        cola = historial[1:][-(CHATBOT_MAX_MENSAJES - 1):]
        st.session_state.chat_historial = [historial[0]] + cola
    else:
        st.session_state.chat_historial = historial[-CHATBOT_MAX_MENSAJES:]


def _agregar_mensaje_chat(role: str, content: str):
    st.session_state.chat_historial.append({"role": role, "content": content})
    _podar_chat_historial()


def _obtener_catalogo_chatbot_documentos():
    return st.session_state.get("velox_catalogo_documentos") or MOCK_CATALOGO_CHATBOT


def _build_chatbot_system_prompt() -> str:
    catalogo = _obtener_catalogo_chatbot_documentos()
    lineas = [
        f"- {d['nombre']} → {d['carpeta']} (acceso={'Sí' if d['acceso'] else 'No'})"
        for d in catalogo
    ]
    return CHATBOT_SYSTEM_PROMPT.format(catalogo="\n".join(lineas))


def _buscar_documentos_chatbot(consulta: str) -> list:
    texto = (consulta or "").strip().lower()
    if not texto:
        return []

    catalogo = _obtener_catalogo_chatbot_documentos()
    resultados = []
    for doc in catalogo:
        nombre_norm = doc["nombre"].lower().replace("_", " ")
        carpeta_norm = doc["carpeta"].lower()
        desc_norm = doc.get("descripcion", "").lower()
        sub_norm = doc.get("subcategoria", "").lower()
        keywords = CHATBOT_DOC_KEYWORDS.get(doc["nombre"], ())

        coincide = (
            doc["nombre"].lower() in texto
            or nombre_norm in texto
            or carpeta_norm in texto
            or sub_norm in texto
            or desc_norm in texto
            or any(kw in texto for kw in keywords)
            or any(token in nombre_norm or token in desc_norm for token in texto.split() if len(token) > 2)
        )
        if coincide:
            resultados.append(doc)
    return resultados


def _describir_utilidad_documento(doc: dict) -> str:
    if doc.get("descripcion"):
        return doc["descripcion"][:300]
    utilidades = {
        "Plantilla_Calculo_CTS_Mype.xlsx": (
            "Calcula y estandariza la liquidación de CTS para MYPE con fórmulas listas para auditoría."
        ),
        "Dashboard_Finanzas_Master.pbix": (
            "Consolida indicadores financieros clave en tableros ejecutivos de Power BI."
        ),
        "Matriz_Costos_Importacion.xlsx": (
            "Desglosa costos de importación (FOB, fletes, aranceles) para cotizaciones precisas."
        ),
        "Guia_Control_Inventarios.xlsx": (
            "Controla entradas, salidas y stock mínimo con formatos listos para operaciones logísticas."
        ),
        "Formatos_Analisis_Procesos.xlsx": (
            "Plantillas Excel para mapear, medir y optimizar procesos administrativos."
        ),
    }
    return utilidades.get(doc["nombre"], "Recurso profesional de apoyo para tu operación diaria.")


def _generar_respuesta_chatbot(consulta: str) -> str:
    _ = _build_chatbot_system_prompt()
    coincidencias = _buscar_documentos_chatbot(consulta)

    if coincidencias:
        bloques = []
        for doc in coincidencias:
            ubicacion = (
                f"📂 **Ubicación:** Este archivo se encuentra en la sección de **{doc['carpeta']}**.\n\n"
                f"**{doc['nombre']}**"
            )
            if doc["acceso"]:
                bloques.append(
                    f"{ubicacion}\n\n"
                    f"{_describir_utilidad_documento(doc)}\n\n"
                    f"⬇️ **[Descargar {doc['nombre']} (simulado)](#velox-descarga-{doc['nombre']})**"
                )
            else:
                bloques.append(f"{ubicacion}\n\n{CHATBOT_MSG_BLOQUEADO}")
        return "\n\n---\n\n".join(bloques)

    categorias = ", ".join(sorted({d["carpeta"] for d in _obtener_catalogo_chatbot_documentos()}))
    return (
        f"Puedo ayudarte a ubicar recursos en: **{categorias}**. "
        "Menciona el nombre del archivo o la categoría (por ejemplo: «plantilla CTS», "
        "«dashboard Power BI» o «control de inventarios»)."
    )


def _chat_content_to_html(text: str) -> str:
    escaped = html_module.escape(text or "")
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped.replace("\n", "<br>")


def _render_chat_historial_html(historial: list, logo_src: str) -> str:
    bloques = []
    for mensaje in historial:
        role = mensaje.get("role", "assistant")
        contenido = _chat_content_to_html(mensaje.get("content", ""))
        if role == "assistant":
            avatar = (
                f'<img src="{logo_src}" alt="veloX" class="velox-chat-msg-avatar">'
                if logo_src
                else '<span class="velox-chat-msg-avatar velox-chat-msg-avatar--fallback">⚡</span>'
            )
            bloques.append(
                f'<div class="velox-chat-msg velox-chat-msg--assistant">'
                f'{avatar}<div class="velox-chat-msg-bubble">{contenido}</div></div>'
            )
        else:
            bloques.append(
                f'<div class="velox-chat-msg velox-chat-msg--user">'
                f'<div class="velox-chat-msg-bubble">{contenido}</div></div>'
            )
    return "".join(bloques)


def _inject_chatbot_floating_css(logo_data_uri: str = ""):
    logo_bg = (
        f"url('{logo_data_uri}') center/76% no-repeat, #1A2332"
        if logo_data_uri
        else "#1A2332"
    )
    fab_css = f"""
        <style>
            @keyframes veloxChatFloat {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-5px); }}
            }}
            @keyframes veloxChatPulse {{
                0%, 100% {{ box-shadow: 0 6px 18px rgba(26, 35, 50, 0.35); }}
                50% {{ box-shadow: 0 10px 26px rgba(79, 117, 168, 0.55); }}
            }}

            div[data-testid="stElementContainer"]:has(.velox-chat-fab-marker),
            div[data-testid="stElementContainer"]:has(.velox-chat-fab-marker) + div[data-testid="stElementContainer"] {{
                height: 0 !important;
                min-height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow: visible !important;
                border: none !important;
                background: transparent !important;
            }}

            div[data-testid="stElementContainer"]:has(.velox-chat-fab-marker) + div[data-testid="stElementContainer"] {{
                position: fixed !important;
                bottom: 20px !important;
                right: 20px !important;
                left: auto !important;
                z-index: 100002 !important;
                width: auto !important;
                height: auto !important;
            }}

            div[data-testid="stElementContainer"]:has(.velox-chat-fab-marker) + div[data-testid="stElementContainer"] button {{
                width: 64px !important;
                min-width: 64px !important;
                height: 64px !important;
                min-height: 64px !important;
                border-radius: 50% !important;
                padding: 0 !important;
                font-size: 0 !important;
                color: transparent !important;
                border: 2px solid rgba(255, 255, 255, 0.9) !important;
                background: {logo_bg} !important;
                animation: veloxChatFloat 2.4s ease-in-out infinite, veloxChatPulse 2.4s ease-in-out infinite !important;
                cursor: pointer !important;
                box-shadow: 0 8px 22px rgba(26, 35, 50, 0.28) !important;
            }}
        </style>
    """
    st.markdown(fab_css, unsafe_allow_html=True)


def _render_chatbot_panel_abierto(logo_src: str):
    """Pop-up flotante: widgets nativos dentro de st.container(key=velox_chat_panel)."""
    # Control de limpieza diferida para evitar el StreamlitAPIException
    if st.session_state.get("limpiar_input_chat", False):
        st.session_state.chat_input_fijo = ""
        st.session_state["limpiar_input_chat"] = False

    historial_html = _render_chat_historial_html(st.session_state.chat_historial[-12:], logo_src)

    st.markdown(_build_chatbot_panel_css(), unsafe_allow_html=True)

    with st.container(key="velox_chat_panel", height=560, width=380):
        col_tit, col_btn = st.columns([4, 1])
        with col_tit:
            st.markdown(
                '<p style="font-size: 18px; font-weight: bold; color: #31333F; margin: 0; padding-top: 2px;">'
                "🤖 Asistente veloX</p>",
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("X", key="cerrar_chat_definitivo_fijo", help="Cerrar conversación"):
                st.session_state.chat_abierto = False
                st.rerun(scope="fragment")

        with st.container(key="velox_chat_historial", height=410):
            st.markdown(historial_html, unsafe_allow_html=True)

        with st.container(key="velox_chat_inputs"):
            col_in, col_send = st.columns([4, 1])
            with col_in:
                st.text_input(
                    "Escribe tu consulta aquí...",
                    key="chat_input_fijo",
                    label_visibility="collapsed",
                    placeholder="Escribe tu consulta aquí...",
                )
            with col_send:
                if st.button("➤", key="btn_enviar_chat_fijo", use_container_width=True):
                    texto = (st.session_state.get("chat_input_fijo") or "").strip()
                    if texto:
                        _agregar_mensaje_chat("user", texto)
                        respuesta = _generar_respuesta_chatbot(texto)
                        _agregar_mensaje_chat("assistant", respuesta)
                        st.session_state["limpiar_input_chat"] = True
                        st.rerun(scope="fragment")


@st.fragment
def render_chatbot_asistente():
    """Chat flotante con IA simulada — solo en Inicio y Mis Documentos."""
    if not _chatbot_visible_en_modulo_actual():
        return

    _init_chatbot_state()
    logo_src = _velox_logo_data_uri(VELOX_LOGO_SINFONDO_PATH) or ""
    chat_abierto = bool(st.session_state.chat_abierto)
    _inject_chatbot_floating_css(logo_src)

    st.markdown('<span class="velox-chat-fab-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    if st.button(" ", key="velox_chat_fab_btn", help="Asistente Inteligente veloX"):
        st.session_state.chat_abierto = not st.session_state.chat_abierto
        st.rerun(scope="fragment")

    if chat_abierto:
        _render_chatbot_panel_abierto(logo_src)


def _etiqueta_rol_sidebar(rol: str) -> str:
    etiquetas = {
        "master": "👑 Master",
        "administrador": "🛡️ Administrador",
        "usuario": "👤 Miembro",
    }
    return etiquetas.get((rol or "usuario").lower(), "👤 Miembro")


def _es_master() -> bool:
    rol = AuthManager.normalizar_rol(st.session_state.get("rol"))
    if AuthManager.es_rol_master(rol):
        return True
    email = (st.session_state.get("usuario") or "").strip().lower()
    return bool(email) and email == AuthManager.MASTER_EMAIL.lower()


def _sincronizar_rol_master_en_sesion() -> None:
    """Alinea session_state.rol con la BD para que Master tenga permisos de publicación."""
    if not st.session_state.get("autenticado"):
        return
    email = (st.session_state.get("usuario") or "").strip().lower()
    if not email:
        return
    if email == AuthManager.MASTER_EMAIL.lower():
        st.session_state["rol"] = "master"
        return
    try:
        res = (
            auth_manager.supabase.table("users")
            .select("rol")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        if res.data:
            st.session_state["rol"] = AuthManager.normalizar_rol(res.data[0].get("rol"))
    except Exception:
        pass


def _es_admin() -> bool:
    return AuthManager.es_rol_administrador(st.session_state.get("rol"))


def _es_staff() -> bool:
    return AuthManager.es_staff(st.session_state.get("rol"))


_PANORAMA_RECURSOS_EMAILS = frozenset(
    {
        AuthManager.MASTER_EMAIL.lower(),
        "ggiraldoasesor@gmail.com",
    }
)


def _puede_ver_panorama_recursos() -> bool:
    """Dashboard «Tu panorama de recursos»: solo Master y Administrador."""
    email = (st.session_state.get("usuario") or "").strip().lower()
    rol = st.session_state.get("rol", "usuario")
    if email in _PANORAMA_RECURSOS_EMAILS:
        return True
    return AuthManager.es_rol_master(rol) or AuthManager.es_rol_administrador(rol)


def render_sidebar_brand():
    """Logo veloX centrado en la parte superior del sidebar."""
    logo_src = _velox_logo_data_uri()
    st.markdown('<div class="sidebar-brand">', unsafe_allow_html=True)
    if logo_src:
        st.markdown(
            f'<img src="{logo_src}" alt="veloX" class="sidebar-brand-logo" />',
            unsafe_allow_html=True,
        )
    elif os.path.exists(VELOX_LOGO_PATH):
        _col_esp, _col_logo, _col_esp2 = st.columns([1, 2, 1])
        with _col_logo:
            st.image(VELOX_LOGO_PATH, width=112)
    else:
        st.markdown('<div class="sidebar-brand-fallback">⚡ veloX</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _puede_modulo(modulo: str) -> bool:
    return auth_manager.puede_acceder_modulo(
        modulo,
        st.session_state.get("rol"),
        st.session_state.get("modulos_permitidos"),
    )


def _secciones_efectivas() -> list:
    rol = st.session_state.get("rol", "usuario")
    if AuthManager.es_rol_master(rol):
        return list(SECCIONES.keys())
    if AuthManager.es_rol_administrador(rol):
        secciones = st.session_state.get("secciones_staff") or []
        return [s for s in secciones if s in SECCIONES]
    return cached_obtener_secciones_usuario(
        st.session_state["usuario"],
        data_cache_version=_velox_data_cache_version(),
    )


def _puede_publicar_documentos() -> bool:
    if _es_master():
        return True
    if _es_admin():
        return bool(st.session_state.get("puede_publicar"))
    return False


def _contar_documentos_seccion(seccion_id: str) -> int:
    try:
        conteos = cached_contar_publicaciones_por_seccion(
            data_cache_version=_velox_data_cache_version(),
        )
        return int(conteos.get(seccion_id, 0))
    except Exception:
        return 0


def _texto_solicitud_whatsapp(seccion_nombre: str) -> str:
    limpio = seccion_nombre or "veloX"
    for prefijo in ("📊 ", "📈 ", "📉 ", "🌐 ", "🚚 ", "👥 ", "💰 "):
        limpio = limpio.replace(prefijo, "")
    return f"Hola Pier, deseo adquirir la siguiente sección de {limpio.strip()} en veloX."


def _url_whatsapp_admin(seccion_nombre: str = "") -> str:
    from urllib.parse import quote

    try:
        app_cfg = st.secrets.get("app", {})
        url_directa = str(app_cfg.get("whatsapp_admin_url", "")).strip()
        numero = str(app_cfg.get("whatsapp_admin", "")).strip()
    except Exception:
        url_directa = ""
        numero = ""

    mensaje = _texto_solicitud_whatsapp(seccion_nombre)

    if url_directa:
        if "wa.me/" in url_directa and "text=" not in url_directa:
            separador = "&" if "?" in url_directa else "?"
            return f"{url_directa}{separador}text={quote(mensaje)}"
        return url_directa

    if numero and numero.upper() != "TU_NUMERO":
        numero_limpio = numero.replace("+", "").replace(" ", "").replace("-", "")
        return f"https://wa.me/{numero_limpio}?text={quote(mensaje)}"

    return WHATSAPP_ADMIN_LINK


def _abrir_paywall_seccion(seccion_id: str):
    st.session_state["seccion_paywall"] = seccion_id


@st.dialog("🔒 Desbloquear sección")
def _dialog_paywall_seccion():
    seccion_id = st.session_state.get("seccion_paywall", "")
    sec_info = SECCIONES.get(seccion_id, {})
    nombre = sec_info.get("nombre", seccion_id)

    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                    border: 1px solid #bae6fd; border-left: 4px solid #0284c7;
                    padding: 1.25rem 1.35rem; border-radius: 12px; margin-bottom: 1.25rem;
                    color: #0f172a; line-height: 1.65; font-size: 0.95rem;">
            👋 <b>¡Bienvenido a esta sección!</b> Para acceder a ella necesitas comunicarte
            con el administrador al siguiente enlace vía WhatsApp.<br><br>
            🔥 <b>¡Aprovecha esta oportunidad! ¡No la dejes pasar!</b><br>
            Con gusto te atenderé 😀...
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.link_button(
        "💬 Contactar al Administrador por WhatsApp",
        _url_whatsapp_admin(nombre),
        use_container_width=True,
        type="primary",
    )
    st.caption(
        f"Se abrirá tu chat con Pier Giraldo Asesor · "
        f"[{WHATSAPP_ADMIN_LINK}]({WHATSAPP_ADMIN_LINK})"
    )

    if st.button("Cerrar", key="paywall_cerrar"):
        st.session_state.pop("seccion_paywall", None)
        st.rerun()


VELOX_CATALOG_LAYOUT_CSS = """
<style>
    /* Encabezado listado (Master / Admin): título + descripción */
    .velox-catalogo-header {
        margin-top: 20px !important;
        margin-bottom: 20px !important;
    }
    .velox-catalogo-header__titulo {
        margin: 0 0 0.55rem 0 !important;
        padding: 0 !important;
        color: #1A2332 !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        line-height: 1.3 !important;
    }
    .velox-catalogo-header__desc {
        margin: 0 !important;
        padding: 0 !important;
        color: #475569 !important;
        font-size: 0.9rem !important;
        font-weight: 400 !important;
        line-height: 1.5 !important;
    }

    /* Tarjetas del catálogo: separación lateral e inferior */
    .velox-section-grid {
        margin-bottom: 20px !important;
        margin-left: 10px !important;
        margin-right: 10px !important;
    }
    .velox-section-grid .velox-section-card {
        margin-left: 0 !important;
        margin-right: 0 !important;
        margin-bottom: 0.65rem !important;
    }

    /* Restaurar gap entre columnas del grid del catálogo */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) {
        gap: 1rem !important;
        align-items: stretch !important;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) > div[data-testid="column"],
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) > div[data-testid="stColumn"] {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-catalogo-header),
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) {
        margin-bottom: 0.5rem !important;
    }

    /* Tarjetas oscuras activas: texto blanco puro y legible */
    .velox-section-card--active,
    .velox-section-card--active .velox-section-card__title,
    .velox-section-card--active .velox-section-card__desc,
    .velox-section-card--active .velox-section-card__meta,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] .velox-section-card--active,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] .velox-section-card--active div,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] .velox-section-card--active span,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] .velox-section-card--active p {
        color: #FFFFFF !important;
    }

    /* ==========================================================================
       REFINAMIENTO QUIRÚRGICO DE ESTILOS - PLATAFORMA VELOX
       ========================================================================== */

    /* 2. Botones secundarios en formularios (p. ej. Guardar cambios) */
    [data-testid="stMain"] button[data-testid="baseButton-secondary"] span,
    [data-testid="stMain"] button[data-testid="baseButton-secondary"] p,
    [data-testid="stMain"] .stButton > button[data-testid="baseButton-secondary"] * {
        color: #1E293B !important;
        font-weight: 600 !important;
        text-shadow: none !important;
    }

    /* 1. Catálogo: botones oscuros legibles (primary + secondary del grid) */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button,
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button *,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] .stButton > button,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] .stButton > button * {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Refuerzo: anula stMarkdownContainer p dentro de botones del catálogo */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) button [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) button [data-testid="stMarkdownContainer"] span,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] button [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] button [data-testid="stMarkdownContainer"] span {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* 3. Pestañas st.tabs (Gestión de Usuarios y similares) */
    [data-testid="stMain"] [data-testid="stTabBar"] button,
    [data-testid="stMain"] [data-testid="stTabBar"] button p,
    [data-testid="stMain"] [data-testid="stTabBar"] button span,
    [data-testid="stMain"] [data-testid="stTabBar"] p,
    [data-testid="stMain"] [data-testid="stTabs"] button,
    [data-testid="stMain"] [data-testid="stTabs"] button p,
    [data-testid="stMain"] [data-testid="stTabs"] button span,
    [data-testid="stMain"] [data-baseweb="tab-list"] button,
    [data-testid="stMain"] [data-baseweb="tab-list"] button span {
        color: #334155 !important;
        font-weight: 600 !important;
        text-shadow: none !important;
    }

    /* 4. Enlaces informativos de login y markdown */
    .stApp [data-testid="stMarkdownContainer"] a,
    .stApp [data-testid="stMarkdownContainer"] p a,
    .stApp a[href*="olvidaste"] span {
        color: #0284C7 !important;
        text-decoration: underline !important;
    }
    .stApp:has(.velox-id-bar) .st-key-btn_olvido_password .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_olvido_password .stButton > button * {
        color: #C41E3A !important;
        font-weight: 500 !important;
        text-shadow: none !important;
    }
</style>
"""


def inject_catalog_layout_css():
    st.markdown(VELOX_CATALOG_LAYOUT_CSS, unsafe_allow_html=True)


def _titulo_catalogo_a_texto(titulo: str) -> str:
    return re.sub(r"^#+\s*", "", titulo or "").strip()


def render_catalogo_secciones_freemium(
    secciones_autorizadas: list,
    titulo: str = "### 📂 Catálogo de secciones",
    key_prefix: str = "sec_cat",
    catalogo_centrado: bool = False,
):
    """Muestra todo el catálogo: activo (navy) o bloqueado (marca de agua)."""
    inject_section_catalog_css()
    inject_catalog_layout_css()
    autorizadas = set(secciones_autorizadas or [])
    if catalogo_centrado:
        st.markdown(
            """
            <div class="velox-catalogo-hero">
                <h1 class="velox-catalogo-hero__titulo velox-titulo-chip">SECCIONES</h1>
                <p class="velox-catalogo-hero__desc">
                    Explora el catálogo completo veloX. Las secciones con candado requieren activación de acceso.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        titulo_texto = html_module.escape(_titulo_catalogo_a_texto(titulo))
        st.markdown(
            f"""
            <div class="velox-catalogo-header">
                <h3 class="velox-catalogo-header__titulo">{titulo_texto}</h3>
                <p class="velox-catalogo-header__desc">
                    Explora el catálogo completo veloX. Las secciones con candado requieren activación de acceso.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    cols = st.columns(3)
    for i, (seccion_id, sec_info) in enumerate(SECCIONES.items()):
        tiene_acceso = seccion_id in autorizadas
        num_docs = _contar_documentos_seccion(seccion_id)
        nombre_limpio = sec_info["nombre"]
        if nombre_limpio.startswith(sec_info["icono"]):
            nombre_limpio = nombre_limpio[len(sec_info["icono"]):].strip()

        with cols[i % 3]:
            st.markdown('<div class="velox-section-grid">', unsafe_allow_html=True)

            if tiene_acceso:
                st.markdown(
                    f"""
                    <div class="velox-section-card velox-section-card--active">
                        <div class="velox-section-card__title">{sec_info['icono']} {nombre_limpio}</div>
                        <div class="velox-section-card__desc">{sec_info['descripcion']}</div>
                        <div class="velox-section-card__meta">✅ {num_docs} documentos disponibles</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button(
                    "Ingresar",
                    key=f"{key_prefix}_go_{seccion_id}",
                    use_container_width=True,
                    type="primary",
                    on_click=activar_seccion_inicio,
                    kwargs={"seccion_id": seccion_id},
                )
            else:
                st.markdown(
                    f"""
                    <div class="velox-section-card velox-section-card--locked">
                        <div class="velox-section-card__watermark">PREVIEW</div>
                        <div class="velox-section-card__title">🔒 {sec_info['icono']} {nombre_limpio}</div>
                        <div class="velox-section-card__desc">{sec_info['descripcion']}</div>
                        <div class="velox-section-card__meta">Previsualización · {num_docs} recursos en catálogo</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button(
                    "Desbloquear acceso",
                    key=f"{key_prefix}_lock_{seccion_id}",
                    use_container_width=True,
                    type="secondary",
                    on_click=_abrir_paywall_seccion,
                    kwargs={"seccion_id": seccion_id},
                )

            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("seccion_paywall"):
        _dialog_paywall_seccion()


def _menu_sidebar_items():
    rol = st.session_state.get("rol", "usuario")
    if _es_master():
        return auth_manager.filtrar_menu_staff(
            MENU_SIDEBAR_MASTER,
            rol,
            st.session_state.get("modulos_permitidos"),
        )
    if _es_admin():
        items = auth_manager.filtrar_menu_staff(
            MENU_SIDEBAR_MASTER,
            rol,
            st.session_state.get("modulos_permitidos"),
        )
        if not any(valor == "👤 Mi Perfil" for _, _, valor in items):
            return list(items) + [MENU_SIDEBAR_PERFIL]
        return items
    return MENU_SIDEBAR_USER


def render_lista_usuarios_solo_lectura():
    """Vista de usuarios sin edición de roles (Administrador)."""
    usuarios = cached_listar_usuarios(data_cache_version=_velox_data_cache_version())
    if not usuarios:
        st.info("No hay usuarios registrados.")
        return

    data = []
    for email, u in sorted(usuarios.items(), key=lambda item: (item[1].get("nombre") or item[0]).lower()):
        secciones = cached_obtener_secciones_usuario(
            email, data_cache_version=_velox_data_cache_version()
        )
        data.append(
            {
                "Email": email,
                "Nombre": u.get("nombre", ""),
                "Rol": AuthManager.etiqueta_rol(u.get("rol")),
                "Pago": "✅" if u.get("pago_confirmado") else "⏳",
                "Activo": "✅" if u.get("activo") else "❌",
                "Acceso": f"{len(secciones)}/{len(SECCIONES)}",
            }
        )
    st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)


def render_permisos_administrador_tab():
    """Master: define módulos y secciones permitidos para cada Administrador."""
    if not _es_master():
        st.error("Solo el Master puede configurar permisos de administradores.")
        return

    usuarios = cached_listar_usuarios(data_cache_version=_velox_data_cache_version())
    admins = [
        email for email, u in usuarios.items() if AuthManager.es_rol_administrador(u.get("rol"))
    ]
    if not admins:
        st.info("No hay usuarios con rol Administrador. Asigna el rol en la pestaña **Lista de Usuarios**.")
        return

    st.markdown("Configura qué **módulos del menú** y **secciones de contenido** puede usar cada administrador.")
    st.caption("Cobranzas y Configuración están reservados exclusivamente para el Master.")

    admin_sel = st.selectbox("Administrador", admins, key="perm_admin_select")
    permisos = AuthManager.permisos_admin_desde_usuario(usuarios[admin_sel])

    st.markdown("#### Módulos permitidos")
    modulos_sel = []
    cols_mod = st.columns(2)
    for idx, modulo in enumerate(AuthManager.MODULOS_CONFIGURABLES_ADMIN):
        with cols_mod[idx % 2]:
            if st.checkbox(
                modulo.replace("🏠 ", "").replace("📁 ", "").replace("👥 ", "").replace("📬 ", ""),
                value=modulo in permisos["modulos"],
                key=f"perm_mod_{admin_sel}_{modulo}",
            ):
                modulos_sel.append(modulo)

    st.markdown("#### Secciones de contenido permitidas")
    secciones_sel = []
    cols_sec = st.columns(3)
    for idx, (sec_id, sec_info) in enumerate(SECCIONES.items()):
        with cols_sec[idx % 3]:
            if st.checkbox(
                f"{sec_info['nombre']}",
                value=sec_id in permisos["secciones"],
                key=f"perm_sec_{admin_sel}_{sec_id}",
            ):
                secciones_sel.append(sec_id)

    st.markdown("#### Permisos de publicación")
    puede_publicar = st.checkbox(
        "Puede publicar documentos en Mis Documentos",
        value=permisos.get("puede_publicar", False),
        help="Habilita la subida y publicación en las secciones autorizadas arriba.",
        key=f"perm_pub_{admin_sel}",
    )

    if st.button("💾 Guardar permisos del administrador", type="primary", key="btn_guardar_perm_admin"):
        ok, msg = auth_manager.guardar_permisos_administrador(
            admin_sel,
            modulos_sel,
            secciones_sel,
            st.session_state["usuario"],
            puede_publicar=puede_publicar,
        )
        if ok:
            st.success(msg)
            _invalidar_cache_datos()
            st.rerun()
        else:
            st.error(msg)


def render_lista_usuarios_master():
    """Tabla interactiva de usuarios con cambio de rol en tiempo real (solo Master)."""
    actor = st.session_state.get("usuario", "")
    if not AuthManager.es_rol_master(st.session_state.get("rol")):
        st.error("Solo usuarios con rol Master pueden gestionar roles.")
        return

    usuarios = cached_listar_usuarios(data_cache_version=_velox_data_cache_version())
    if not usuarios:
        st.info("No hay usuarios registrados.")
        return

    st.caption(
        "Edita la columna **Rol** para actualizar permisos. "
        "Los cambios se guardan automáticamente en Supabase."
    )

    rows = []
    for email, u in sorted(usuarios.items(), key=lambda item: (item[1].get("nombre") or item[0]).lower()):
        secciones = cached_obtener_secciones_usuario(
            email, data_cache_version=_velox_data_cache_version()
        )
        rows.append(
            {
                "Email": email,
                "Nombre": u.get("nombre", ""),
                "Rol": AuthManager.etiqueta_rol(u.get("rol")),
                "Pago": "✅" if u.get("pago_confirmado") else "⏳",
                "Activo": "✅" if u.get("activo") else "❌",
                "Acceso": f"{len(secciones)}/{len(SECCIONES)}",
            }
        )

    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df,
        column_config={
            "Email": st.column_config.TextColumn("Email", disabled=True),
            "Nombre": st.column_config.TextColumn("Nombre", disabled=True),
            "Rol": st.column_config.SelectboxColumn(
                "Rol",
                options=AuthManager.ROLES_ETIQUETAS,
                required=True,
            ),
            "Pago": st.column_config.TextColumn("Pago", disabled=True),
            "Activo": st.column_config.TextColumn("Activo", disabled=True),
            "Acceso": st.column_config.TextColumn("Acceso", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        key="master_users_role_editor",
    )

    for idx in edited.index:
        email = edited.at[idx, "Email"]
        rol_nuevo = edited.at[idx, "Rol"]
        rol_actual = df.at[idx, "Rol"]
        if rol_nuevo == rol_actual:
            continue
        ok, msg = auth_manager.actualizar_rol_usuario(email, rol_nuevo, actor)
        if ok:
            st.toast(msg, icon="✅")
            _invalidar_cache_datos()
            st.rerun()
        else:
            st.error(msg)
            break

    st.markdown("---")
    usuarios_eliminar = [e for e in usuarios if e != actor]
    if usuarios_eliminar:
        sel = st.selectbox("Usuario a eliminar", usuarios_eliminar)
        if st.button("Eliminar", type="secondary"):
            auth_manager.eliminar_usuario(sel, actor)
            _invalidar_cache_datos()
            st.rerun()


def render_dashboard_analytics_master(publicaciones, usuarios):
    st.markdown("### 📊 Panel analítico ejecutivo")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_documentos_por_seccion(publicaciones, SECCIONES), use_container_width=True)
    with c2:
        st.plotly_chart(chart_acceso_usuarios(usuarios), use_container_width=True)
    pagos = cached_listar_pagos_pendientes(data_cache_version=_velox_data_cache_version())
    st.plotly_chart(chart_cobranzas_pendientes(pagos), use_container_width=True)


def render_dashboard_analytics_user(secciones_usuario, publicaciones):
    st.markdown("### 📊 Tu panorama de recursos")
    st.plotly_chart(
        chart_actividad_secciones_usuario(secciones_usuario, SECCIONES, publicaciones),
        use_container_width=True,
    )


# ==================== NAVEGACIÓN INTERNA - INICIO ====================
def activar_seccion_inicio(seccion_id):
    st.session_state.seccion_activa = seccion_id
    subcategorias = SECCIONES.get(seccion_id, {}).get("subcategorias", ["General"])
    st.session_state.categoria_inicio = subcategorias[0]

def volver_al_inicio():
    st.session_state.seccion_activa = "inicio"

def seleccionar_categoria_inicio(categoria):
    st.session_state.categoria_inicio = categoria


def _mis_docs_categoria_key(seccion_id: str) -> str:
    return f"mis_docs_categoria_{seccion_id}"


def seleccionar_categoria_mis_docs(seccion_id: str, categoria: str) -> None:
    st.session_state[_mis_docs_categoria_key(seccion_id)] = categoria
    st.session_state[_docs_pagina_session_key(seccion_id, categoria, prefijo="pub")] = 1


def _obtener_categoria_mis_docs(seccion_id: str, subcategorias: list) -> str:
    cat_key = _mis_docs_categoria_key(seccion_id)
    if cat_key not in st.session_state:
        st.session_state[cat_key] = subcategorias[0]
    categoria = st.session_state[cat_key]
    if categoria not in subcategorias:
        st.session_state[cat_key] = subcategorias[0]
        categoria = subcategorias[0]
    return categoria

def _formatear_fecha_notif(fecha_raw):
    if not fecha_raw:
        return "Fecha desconocida"
    try:
        texto = str(fecha_raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(texto)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return str(fecha_raw)[:16].replace("T", " ")

def render_gestion_cobranzas_master():
    """Panel Master: aprobar o rechazar pagos Yape/Plim pendientes."""
    st.header("💳 Gestión de Cobranzas y Activaciones")
    st.caption("Revisa pagos manuales Yape/Plim y activa el acceso de los alumnos.")

    if st.session_state.get("pago_flash"):
        tipo, texto = st.session_state.pop("pago_flash")
        if tipo == "success":
            st.success(texto)
        elif tipo == "error":
            st.error(texto)

    pagos = cached_listar_pagos_pendientes(data_cache_version=_velox_data_cache_version())
    st.markdown(f"### ⏳ Pagos pendientes ({len(pagos)})")

    if not pagos:
        st.info("No hay pagos manuales pendientes de revisión.")
        return

    df = pd.DataFrame([
        {
            "Email": p.get("email"),
            "Nombre": p.get("nombre", "—"),
            "Celular": p.get("celular") or "—",
            "Captura": "✅" if p.get("comprobante_url") else "—",
            "Monto": f"S/ {float(p.get('monto', MONTO_SOLES)):.2f}",
            "Método": (p.get("metodo_pago") or "yape_plim").replace("_", " ").upper(),
            "Fecha": _formatear_fecha_notif(p.get("fecha")),
        }
        for p in pagos
    ])
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.markdown("---")

    for pago in pagos:
        pago_id = pago["id"]
        with st.container(border=True):
            ref = "Captura adjunta" if pago.get("comprobante_url") else "—"
            st.markdown(
                f"**{pago.get('nombre', 'Sin nombre')}** · `{pago.get('email')}`  \n"
                f"Celular: **{pago.get('celular') or '—'}** · Comprobante: **{ref}** · "
                f"Método: **{(pago.get('metodo_pago') or 'yape_plim').replace('_', ' ').upper()}**"
            )
            if pago.get("comprobante_url"):
                st.image(
                    pago["comprobante_url"],
                    caption="Comprobante Yape / Plim — validación visual",
                    width=360,
                )
            col_ok, col_no = st.columns(2)
            with col_ok:
                if st.button(
                    "✅ Aprobar Pago",
                    key=f"aprobar_{pago_id}",
                    type="primary",
                    use_container_width=True,
                    disabled=st.session_state.get("pago_procesando") == pago_id,
                ):
                    st.session_state["pago_procesando"] = pago_id
                    ok, msg = payment_manager.aprobar_pago(pago_id, st.session_state["usuario"])
                    st.session_state.pop("pago_procesando", None)
                    st.session_state["pago_flash"] = ("success" if ok else "error", msg)
                    if ok:
                        _invalidar_cache_datos()
                    st.rerun()
            with col_no:
                motivo_key = f"motivo_{pago_id}"
                motivo = st.text_input(
                    "Motivo de rechazo",
                    key=motivo_key,
                    placeholder="Ej. Código incorrecto o monto no coincide",
                )
                if st.button(
                    "❌ Rechazar Pago",
                    key=f"rechazar_{pago_id}",
                    use_container_width=True,
                    disabled=st.session_state.get("pago_procesando") == pago_id,
                ):
                    st.session_state["pago_procesando"] = pago_id
                    ok, msg = payment_manager.rechazar_pago(
                        pago_id, st.session_state["usuario"], motivo
                    )
                    st.session_state.pop("pago_procesando", None)
                    st.session_state["pago_flash"] = ("success" if ok else "error", msg)
                    if ok:
                        _invalidar_cache_datos()
                    st.rerun()

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
        ok_notif = resultado.get("notificaciones_ok", count > 0)
    else:
        count = 0
        err = None
        ok_notif = False

    if count > 0:
        st.success(f"✅ Documento publicado. {count} alumno(s) notificado(s).")
    elif err and not ok_notif and "No hay alumnos" not in err:
        st.error(f"❌ Documento publicado, pero Supabase rechazó las notificaciones: {err}")
    else:
        detalle = err or "Verifica usuarios activos con rol 'usuario' y la sección en users.secciones."
        st.warning(f"⚠️ Documento publicado, pero no se notificó a ningún alumno. {detalle}")


DOCS_ITEMS_POR_PAGINA = 12

MIS_DOCS_COMPACT_CSS = """
<style>
/* ==========================================================================
   ESTILO PROFESIONAL BLANCO PARA FILAS DE DOCUMENTOS DISPONIBLES
   ========================================================================== */
.velox-docs-toolbar { margin-bottom: 0.35rem !important; }

[data-testid="stMain"] [class*="st-key-velox_publicaciones_tabla_"],
[data-testid="stMain"] [class*="st-key-velox_publicaciones_tabla_"] > div,
[data-testid="stMain"] [class*="st-key-velox_publicaciones_tabla_"] [data-testid="stVerticalBlock"],
[data-testid="stMain"] [class*="st-key-velox_publicaciones_tabla_"] [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stMain"] [class*="st-key-velox_doc_row_"] [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

.velox-doc-table-head,
.document-row-container .velox-doc-table-head {
    color: #64748B !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 0.35rem;
    margin-bottom: 0.25rem;
    background-color: #FFFFFF !important;
}

/* 1. Fila individual de cada documento */
.document-row-container,
[data-testid="stMain"] [class*="st-key-velox_doc_row_"],
[data-testid="stMain"] [data-testid="element-container"][class*="st-key-velox_doc_row_"] {
    background-color: #FFFFFF !important;
    border-bottom: 1px solid #E2E8F0 !important;
    padding: 12px 16px !important;
    margin-bottom: 0 !important;
    transition: background-color 0.2s ease, box-shadow 0.2s ease !important;
}

[data-testid="stMain"] [class*="st-key-velox_doc_row_"] [data-testid="stHorizontalBlock"],
[data-testid="stMain"] [class*="st-key-velox_doc_row_"] [data-testid="column"],
[data-testid="stMain"] [class*="st-key-velox_doc_row_"] [data-testid="stColumn"] {
    background-color: transparent !important;
    background: transparent !important;
}

[data-testid="stMain"] [class*="st-key-velox_doc_row_"] [data-testid="column"],
[data-testid="stMain"] [class*="st-key-velox_doc_row_"] [data-testid="stColumn"] {
    display: flex !important;
    align-items: center !important;
    min-height: 36px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

/* 2. Hover por fila */
.document-row-container:hover,
[data-testid="stMain"] [class*="st-key-velox_doc_row_"]:hover {
    background-color: #F8FAFC !important;
    box-shadow: inset 3px 0 0 #0EA5E9 !important;
    cursor: default;
}

.velox-doc-row__icon { font-size: 1.05rem; line-height: 1; flex-shrink: 0; }
.velox-doc-row__info { min-width: 0; width: 100%; }

/* 3. Contraste de textos */
.velox-doc-row__name,
.document-row-title {
    color: #0F172A !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    line-height: 1.15 !important;
    margin: 0 !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.velox-doc-row__desc,
.document-row-description {
    color: #475569 !important;
    font-size: 0.9rem !important;
    line-height: 1.3 !important;
    margin: 4px 0 0 0 !important;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
}

.velox-doc-row__meta {
    color: #64748B !important;
    font-size: 0.78rem !important;
}

.velox-docs-pagination {
    text-align: center;
    color: #475569 !important;
    font-size: 0.84rem !important;
    margin: 0.65rem 0 0.25rem !important;
    background-color: #FFFFFF !important;
}
</style>
"""


def _docs_pagina_session_key(seccion, subcategoria, prefijo="pub"):
    return f"docs_pag_{prefijo}_{seccion}_{subcategoria}"


def _docs_busqueda_session_key(seccion, subcategoria, prefijo="pub"):
    return f"docs_busq_ctx_{prefijo}_{seccion}_{subcategoria}"


def _sincronizar_pagina_documentos(seccion, subcategoria, busqueda, prefijo="pub"):
    ctx_key = _docs_busqueda_session_key(seccion, subcategoria, prefijo)
    pag_key = _docs_pagina_session_key(seccion, subcategoria, prefijo)
    ctx = (busqueda or "").strip().lower()
    if st.session_state.get(ctx_key) != ctx:
        st.session_state[ctx_key] = ctx
        st.session_state[pag_key] = 1
    if pag_key not in st.session_state:
        st.session_state[pag_key] = 1
    return st.session_state[pag_key]


def _filtrar_documentos_por_busqueda(documentos, busqueda):
    termino = (busqueda or "").strip().lower()
    if not termino:
        return list(documentos)
    tokens = [t for t in termino.split() if len(t) > 1]
    filtrados = []
    for doc in documentos:
        nombre = (doc.get("nombre") or doc.get("nombre_original") or "").lower()
        desc = (doc.get("descripcion") or doc.get("mensaje") or "").lower()
        sub = (doc.get("subcategoria") or "").lower()
        if (
            termino in nombre
            or termino in desc
            or termino in sub
            or all(t in nombre or t in desc for t in tokens)
        ):
            filtrados.append(doc)
    return filtrados


def _paginar_lista_documentos(documentos, pagina, por_pagina=DOCS_ITEMS_POR_PAGINA):
    total = len(documentos)
    if total == 0:
        return [], 1, 1, 0
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    pagina = max(1, min(pagina, total_paginas))
    inicio = (pagina - 1) * por_pagina
    return documentos[inicio:inicio + por_pagina], pagina, total_paginas, total


def _render_paginacion_documentos(seccion, subcategoria, pagina, total_paginas, total_items, prefijo="pub"):
    pag_key = _docs_pagina_session_key(seccion, subcategoria, prefijo)
    col_prev, col_mid, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button(
            "◀ Anterior",
            key=f"docs_prev_{prefijo}_{seccion}_{subcategoria}",
            disabled=pagina <= 1,
            use_container_width=True,
        ):
            st.session_state[pag_key] = max(1, pagina - 1)
            st.rerun()
    with col_mid:
        st.markdown(
            f'<div class="velox-docs-pagination">Página <strong>{pagina}</strong> de '
            f'<strong>{total_paginas}</strong> · {total_items} documento(s)</div>',
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button(
            "Siguiente ▶",
            key=f"docs_next_{prefijo}_{seccion}_{subcategoria}",
            disabled=pagina >= total_paginas,
            use_container_width=True,
        ):
            st.session_state[pag_key] = min(total_paginas, pagina + 1)
            st.rerun()


def _render_encabezado_tabla_documentos(es_master=False, incluir_publicar=False):
    if incluir_publicar:
        cols = st.columns([0.35, 4.4, 1.2, 0.75, 0.65, 0.65])
        labels = ["", "Documento", "Fecha", "Descargar", "Publicar", "Eliminar"]
    elif es_master:
        cols = st.columns([0.35, 4.5, 1.2, 0.75, 0.65, 0.65])
        labels = ["", "Documento", "Fecha", "Descargar", "Editar", "Eliminar"]
    else:
        cols = st.columns([0.35, 5.2, 1.2, 0.85])
        labels = ["", "Documento", "Fecha", "Descargar"]
    for col, label in zip(cols, labels):
        with col:
            if label:
                st.markdown(f'<div class="velox-doc-table-head">{label}</div>', unsafe_allow_html=True)


def _html_celda_documento_compacto(meta):
    """Nombre + descripción secundaria para la columna Documento de la tabla compacta."""
    nombre = html_module.escape(meta["nombre"])
    descripcion = (meta.get("descripcion") or "").strip()
    if descripcion:
        desc_html = html_module.escape(descripcion)
        return (
            f'<div class="velox-doc-row__info">'
            f'<p class="velox-doc-row__name document-row-title">{nombre}</p>'
            f'<p class="velox-doc-row__desc document-row-description">{desc_html}</p>'
            f"</div>"
        )
    return f'<p class="velox-doc-row__name document-row-title">{nombre}</p>'


def _render_fila_documento_publicacion(pub, meta, seccion_seleccionada, secciones_usuario, indice, es_master):
    if es_master:
        cols = st.columns([0.35, 4.5, 1.2, 0.75, 0.65, 0.65])
    else:
        cols = st.columns([0.35, 5.2, 1.2, 0.85])

    with cols[0]:
        st.markdown(f'<span class="velox-doc-row__icon">{meta["icono"]}</span>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_html_celda_documento_compacto(meta), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f'<span class="velox-doc-row__meta">{meta["fecha"]}</span>', unsafe_allow_html=True)
    with cols[3]:
        if st.button("📥", key=f"down_pub_{pub['id']}_{indice}", help="Descargar / Ver"):
            if seccion_seleccionada in secciones_usuario:
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
            else:
                st.error("No tienes permiso para descargar este documento")

    if es_master:
        with cols[4]:
            if st.button("✏️", key=f"edit_{pub['id']}_{indice}", help="Editar descripción"):
                st.session_state[f"editando_{pub['id']}"] = True
                st.rerun()
        with cols[5]:
            if st.button("🗑️", key=f"del_{pub['id']}_{indice}", help="Eliminar"):
                try:
                    exito, msg = storage_manager.eliminar_publicacion(pub["id"])
                    if exito:
                        st.session_state.pop(f"editando_{pub['id']}", None)
                        _invalidar_cache_datos()
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                except Exception as err:
                    st.error(f"❌ Error al eliminar: {err}")

    if es_master and st.session_state.get(f"editando_{pub['id']}", False):
        nueva_desc = st.text_area(
            "Nueva descripción",
            value=pub.get("descripcion") or pub.get("mensaje", ""),
            key=f"newdesc_{pub['id']}_{indice}",
        )
        if st.button("Guardar cambios", key=f"save_desc_{pub['id']}_{indice}"):
            try:
                exito, msg = storage_manager.editar_publicacion(pub["id"], nueva_desc)
                if exito:
                    st.success(msg)
                    st.session_state.pop(f"editando_{pub['id']}", None)
                    _invalidar_cache_datos()
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            except Exception as err:
                st.error(f"❌ Error al editar: {err}")


def _render_fila_documento_personal(archivo, meta, indice):
    cols = st.columns([0.35, 4.4, 1.2, 0.75, 0.65, 0.65])
    with cols[0]:
        st.markdown(f'<span class="velox-doc-row__icon">{meta["icono"]}</span>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_html_celda_documento_compacto(meta), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f'<span class="velox-doc-row__meta">{meta["fecha"]}</span>', unsafe_allow_html=True)
    with cols[3]:
        if st.button("📥", key=f"download_{archivo['id']}_{indice}", help="Descargar"):
            exito, resultado = storage_manager.descargar_archivo_personal(
                archivo["id"], st.session_state["usuario"]
            )
            if exito:
                st.markdown(
                    f'<a href="{resultado["url"]}" download="{resultado["nombre"]}" '
                    f'style="background: #667eea; color: white; padding: 4px 12px; '
                    f'border-radius: 6px; text-decoration: none;">📥 Descargar</a>',
                    unsafe_allow_html=True,
                )
                st.success("✅ Descarga disponible")
            else:
                st.error(f"❌ {resultado}")
    with cols[4]:
        if st.button("🌍", key=f"publish_{archivo['id']}_{indice}", help="Publicar"):
            st.session_state["archivo_a_publicar"] = archivo["id"]
            st.session_state["show_publish_form"] = True
    with cols[5]:
        if st.button("🗑️", key=f"delete_{archivo['id']}_{indice}", help="Eliminar"):
            storage_manager.eliminar_archivo(archivo["id"], st.session_state["usuario"])
            _invalidar_cache_datos()
            st.rerun()


def _render_lista_documentos_compacta(
    documentos,
    seccion,
    subcategoria,
    busqueda,
    prefijo,
    render_fila_fn,
    mensaje_vacio,
    es_master=False,
    incluir_publicar=False,
):
    filtrados = _filtrar_documentos_por_busqueda(documentos, busqueda)
    pagina = _sincronizar_pagina_documentos(seccion, subcategoria, busqueda, prefijo)
    lote, pagina, total_paginas, total_items = _paginar_lista_documentos(filtrados, pagina)

    if not filtrados:
        st.info(mensaje_vacio)
        return

    with st.container(key=f"velox_publicaciones_tabla_{prefijo}"):
        _render_encabezado_tabla_documentos(es_master=es_master, incluir_publicar=incluir_publicar)
        for i, doc in enumerate(lote):
            doc_id = doc.get("id") or f"{i}_{pagina}"
            with st.container(key=f"velox_doc_row_{prefijo}_{doc_id}"):
                render_fila_fn(doc, i + (pagina - 1) * DOCS_ITEMS_POR_PAGINA)

        if total_paginas > 1 or total_items > DOCS_ITEMS_POR_PAGINA:
            _render_paginacion_documentos(seccion, subcategoria, pagina, total_paginas, total_items, prefijo)


def _render_bloque_publicaciones_compacto(
    seccion_id,
    categoria_actual,
    busqueda,
    secciones_usuario,
    *,
    prefijo="pub",
    titulo="### 📢 Publicaciones disponibles",
    mensaje_vacio="No hay documentos en esta categoría.",
    seccion_info=None,
    sincronizar_chatbot=False,
):
    """Lista compacta unificada de publicaciones (Inicio y Mis Documentos)."""
    st.markdown(titulo)
    _cache_v = _velox_data_cache_version()
    publicaciones = cached_obtener_publicaciones_por_seccion(
        seccion=seccion_id,
        subcategoria=categoria_actual,
        data_cache_version=_cache_v,
    )
    if sincronizar_chatbot and seccion_info:
        _actualizar_catalogo_chatbot_seccion(
            seccion_info, seccion_id, categoria_actual, secciones_usuario
        )

    def _render_fila_publicacion(pub, indice):
        meta = storage_manager.normalizar_metadatos_documento(pub, es_publicacion=True)
        _render_fila_documento_publicacion(
            pub,
            meta,
            seccion_id,
            secciones_usuario,
            indice,
            _es_master(),
        )

    _render_lista_documentos_compacta(
        publicaciones,
        seccion_id,
        categoria_actual,
        busqueda,
        prefijo=prefijo,
        render_fila_fn=_render_fila_publicacion,
        mensaje_vacio=mensaje_vacio,
        es_master=_es_master(),
    )


def _actualizar_catalogo_chatbot_seccion(seccion_info, seccion_id, subcategoria, secciones_usuario):
    catalogo = cached_listar_catalogo_seccion(
        seccion_id,
        subcategoria,
        data_cache_version=_velox_data_cache_version(),
    )
    st.session_state["velox_catalogo_documentos"] = [
        {
            "nombre": item["nombre"],
            "carpeta": seccion_info["nombre"],
            "subcategoria": item.get("subcategoria") or subcategoria,
            "acceso": seccion_id in secciones_usuario,
            "id": item.get("id"),
            "descripcion": item.get("descripcion", ""),
        }
        for item in catalogo
    ]
    return catalogo


def _seccion_desde_notificacion(notif):
    """Resuelve la sección desde la columna dedicada o metadata legacy."""
    seccion = normalizar_seccion(notif.get("seccion"))
    if seccion:
        return seccion
    metadata = _parsear_metadata_notif(notif.get("metadata"))
    return normalizar_seccion(metadata.get("seccion"))


def abrir_notificacion(
    notificacion_id,
    seccion,
    categoria=None,
    titulo=None,
    publicacion_id=None,
):
    notification_manager.marcar_como_leida(notificacion_id, st.session_state["usuario"])
    st.session_state["menu_principal"] = "📁 Mis Documentos"
    seccion_norm = normalizar_seccion(seccion) if seccion else None
    st.session_state.seccion_activa = seccion_norm or "inicio"
    if seccion_norm:
        st.session_state["seccion_seleccionada_documentos"] = seccion_norm
    if categoria and seccion_norm:
        st.session_state["categoria_redirigida"] = categoria
    if titulo:
        st.session_state["notif_redirect_mensaje"] = f"✅ Has sido redirigido a la publicación: {titulo}"
        nombre_busqueda = titulo.rsplit(".", 1)[0] if "." in titulo else titulo
        st.session_state["buscador_mis_docs"] = nombre_busqueda
    if publicacion_id:
        st.session_state["notif_redirect_publicacion_id"] = publicacion_id

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
            margin-bottom: -0.85rem;
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
        notificaciones = notification_manager.obtener_ultimas_no_leidas(
            usuario, limite=LIMITE_NOTIFICACIONES_CAMPANA
        )

        if not notificaciones:
            st.info("No tienes notificaciones pendientes")
            return

        for notif in notificaciones:
            metadata = _parsear_metadata_notif(notif.get("metadata"))
            seccion = _seccion_desde_notificacion(notif)
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
                "Revisar",
                key=f"notif_btn_{notif['id']}",
                use_container_width=True,
                on_click=abrir_notificacion,
                kwargs={
                    "notificacion_id": notif["id"],
                    "seccion": seccion,
                    "categoria": categoria,
                    "titulo": titulo,
                    "publicacion_id": metadata.get("archivo_id"),
                },
            )

def render_app_top_bar():
    """Barra superior post-login: campana de notificaciones alineada a la derecha."""
    _, col_bell = st.columns([11, 1])
    with col_bell:
        render_campana_notificaciones()


def mostrar_modulo_dashboard_interactivo():
    st.markdown("### 📊 Diseñador de Dashboards Estadísticos")
    st.markdown(
        "Sube tu archivo de Excel o CSV para activar el lienzo interactivo. "
        "Podrás arrastrar variables, crear filtros y diseñar tus reportes a medida para tu uso personal o laboral."
    )

    archivo_subido = st.file_uploader(
        "Adjunta tu tabla de datos (.xlsx, .xls, .csv)",
        type=["xlsx", "xls", "csv"],
        key="uploader_dashboard_dinamico",
    )

    def _generar_informe_pdf_velox(dataframe: pd.DataFrame) -> bytes:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as exc:
            raise ImportError(
                "La librería 'reportlab' no está instalada. Ejecuta: pip install reportlab"
            ) from exc

        def _truncar_texto(valor, max_len: int = 48) -> str:
            texto = str(valor) if valor is not None else ""
            return texto if len(texto) <= max_len else texto[: max_len - 3] + "..."

        def _tabla_estilo_encabezado(num_filas: int, num_cols: int) -> TableStyle:
            return TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F3D3C")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8FA")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )

        buffer_pdf = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer_pdf,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title="Informe veloX",
        )
        estilos = getSampleStyleSheet()
        titulo_estilo = ParagraphStyle(
            "VeloxTitulo",
            parent=estilos["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=colors.HexColor("#0F3D3C"),
            spaceAfter=12,
        )
        subtitulo_estilo = ParagraphStyle(
            "VeloxSubtitulo",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.HexColor("#1A2744"),
            spaceBefore=14,
            spaceAfter=8,
        )
        cuerpo_estilo = ParagraphStyle(
            "VeloxCuerpo",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
        )

        elementos = []
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        elementos.append(Paragraph("Informe de Análisis de Datos - veloX", titulo_estilo))
        elementos.append(Paragraph(f"<b>Fecha y hora de generación:</b> {ahora}", cuerpo_estilo))
        elementos.append(Spacer(1, 0.2 * inch))

        elementos.append(Paragraph("Resumen del conjunto de datos", subtitulo_estilo))
        columnas = [str(c) for c in dataframe.columns.tolist()]
        resumen_lineas = [
            f"<b>Filas:</b> {dataframe.shape[0]}",
            f"<b>Columnas:</b> {dataframe.shape[1]}",
            f"<b>Nombres de columnas:</b> {', '.join(columnas) if columnas else '—'}",
        ]
        for linea in resumen_lineas:
            elementos.append(Paragraph(linea, cuerpo_estilo))
        elementos.append(Spacer(1, 0.15 * inch))

        numericas = dataframe.select_dtypes(include="number")
        if not numericas.empty:
            elementos.append(Paragraph("Estadísticas descriptivas (columnas numéricas)", subtitulo_estilo))
            filas_stats = [["Columna", "Media", "Mediana", "Desv. est.", "Mín", "Máx", "Q1", "Q3"]]
            for col in numericas.columns:
                serie = pd.to_numeric(numericas[col], errors="coerce").dropna()
                if serie.empty:
                    continue
                filas_stats.append(
                    [
                        _truncar_texto(col, 28),
                        f"{serie.mean():.4f}",
                        f"{serie.median():.4f}",
                        f"{serie.std():.4f}",
                        f"{serie.min():.4f}",
                        f"{serie.max():.4f}",
                        f"{serie.quantile(0.25):.4f}",
                        f"{serie.quantile(0.75):.4f}",
                    ]
                )
            tabla_stats = Table(filas_stats, repeatRows=1)
            tabla_stats.setStyle(_tabla_estilo_encabezado(len(filas_stats), len(filas_stats[0])))
            elementos.append(tabla_stats)
            elementos.append(Spacer(1, 0.2 * inch))

        categoricas = dataframe.select_dtypes(include=["object", "string", "category"])
        if not categoricas.empty:
            elementos.append(Paragraph("Análisis de variables categóricas", subtitulo_estilo))
            for col in categoricas.columns:
                elementos.append(
                    Paragraph(f"<b>Variable:</b> {_truncar_texto(col, 60)}", cuerpo_estilo)
                )
                conteos = categoricas[col].astype(str).value_counts().head(10)
                filas_cat = [["Valor", "Frecuencia"]]
                for valor, freq in conteos.items():
                    filas_cat.append([_truncar_texto(valor, 40), str(int(freq))])
                tabla_cat = Table(filas_cat, colWidths=[3.8 * inch, 1.2 * inch], repeatRows=1)
                tabla_cat.setStyle(_tabla_estilo_encabezado(len(filas_cat), 2))
                elementos.append(tabla_cat)
                elementos.append(Spacer(1, 0.12 * inch))

        if numericas.shape[1] >= 2:
            elementos.append(PageBreak())
            elementos.append(Paragraph("Matriz de correlación", subtitulo_estilo))
            corr = numericas.corr(numeric_only=True)
            encabezados_corr = [""] + [_truncar_texto(c, 14) for c in corr.columns]
            filas_corr = [encabezados_corr]
            for idx, fila in corr.iterrows():
                filas_corr.append(
                    [_truncar_texto(idx, 14)]
                    + [f"{v:.3f}" if pd.notna(v) else "—" for v in fila.tolist()]
                )
            tabla_corr = Table(filas_corr, repeatRows=1)
            tabla_corr.setStyle(_tabla_estilo_encabezado(len(filas_corr), len(filas_corr[0])))
            elementos.append(tabla_corr)
            elementos.append(Spacer(1, 0.2 * inch))

        elementos.append(Paragraph("Conclusiones", subtitulo_estilo))
        elementos.append(
            Paragraph(
                "Este informe resume las principales métricas del conjunto de datos cargado. "
                "Para visualizaciones interactivas, utiliza las herramientas de PyGWalker.",
                cuerpo_estilo,
            )
        )

        doc.build(elementos)
        buffer_pdf.seek(0)
        return buffer_pdf.getvalue()

    if archivo_subido:
        try:
            if archivo_subido.name.endswith(".csv"):
                df = pd.read_csv(archivo_subido)
            else:
                df = pd.read_excel(archivo_subido)

            st.success(f"¡Lienzo activado! Se detectaron {df.shape[1]} columnas y {df.shape[0]} filas.")

            col_pdf, _ = st.columns([1, 2])
            with col_pdf:
                if st.button(
                    "📊 Generar informe profesional en PDF",
                    type="primary",
                    key="btn_generar_pdf_dashboard_velox",
                ):
                    try:
                        pdf_bytes = _generar_informe_pdf_velox(df)
                        st.session_state["velox_dashboard_pdf_bytes"] = pdf_bytes
                        st.session_state["velox_dashboard_pdf_nombre"] = (
                            f"informe_velox_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        )
                    except ImportError as err:
                        st.error(str(err))
                    except Exception as err:
                        st.error(f"No se pudo generar el informe PDF: {err}")

            if st.session_state.get("velox_dashboard_pdf_bytes"):
                st.download_button(
                    label="📄 Descargar informe PDF",
                    data=st.session_state["velox_dashboard_pdf_bytes"],
                    file_name=st.session_state.get(
                        "velox_dashboard_pdf_nombre",
                        f"informe_velox_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    ),
                    mime="application/pdf",
                    type="secondary",
                    key="btn_descarga_pdf_dashboard_velox",
                )

            st.write("---")

            pyg_html = pyg.to_html(df, theme="dark")
            components.html(pyg_html, height=850, scrolling=True)

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
    else:
        st.info(
            "💡 Consejo: Asegúrate de que la primera fila de tu Excel contenga los nombres "
            "de las columnas para que el diseñador las reconozca automáticamente."
        )


def _render_documentos_categoria_inicio(seccion_id, categoria_actual, secciones_usuario, busqueda_key):
    """Lista de publicaciones por subcategoría dentro de la vista Inicio de una sección."""
    st.markdown(MIS_DOCS_COMPACT_CSS, unsafe_allow_html=True)
    busqueda = st.text_input(
        "🔍 Buscar por nombre o descripción:",
        key=busqueda_key,
    )
    _render_bloque_publicaciones_compacto(
        seccion_id,
        categoria_actual,
        busqueda,
        secciones_usuario,
        prefijo="inicio",
        titulo="### 📢 Documentos disponibles",
        mensaje_vacio="No hay documentos en esta categoría.",
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

    secciones_usuario = _secciones_efectivas()

    if seccion_id not in secciones_usuario:
        st.warning("🔒 Esta sección requiere acceso activo.")
        if st.button("💬 Contactar al administrador", key=f"paywall_from_view_{seccion_id}"):
            _abrir_paywall_seccion(seccion_id)
            st.rerun()
        st.button("⬅️ Volver al Inicio", key="btn_volver_inicio_denegado", on_click=volver_al_inicio)
        if st.session_state.get("seccion_paywall"):
            _dialog_paywall_seccion()
        return

    st.button("⬅️ Volver al Inicio", key="btn_volver_inicio", on_click=volver_al_inicio)
    st.header(seccion_info["nombre"])
    st.markdown(f"""
    <div style="background: {seccion_info['color']}10; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <p style="margin:0;">{seccion_info['descripcion']}</p>
    </div>
    """, unsafe_allow_html=True)

    if seccion_id == "laboral":
        tab_minicursos, tab_formatos, tab_dashboard = st.tabs(
            ["📚 Mini Cursos", "🗂️ Formatos y Plantillas", "📊 Diseñador de Dashboards"]
        )
        with tab_minicursos:
            _render_documentos_categoria_inicio(
                seccion_id,
                "Minicursos",
                secciones_usuario,
                busqueda_key=f"buscador_inicio_{seccion_id}_minicursos",
            )
        with tab_formatos:
            _render_documentos_categoria_inicio(
                seccion_id,
                "Formatos y Plantillas",
                secciones_usuario,
                busqueda_key=f"buscador_inicio_{seccion_id}_formatos",
            )
        with tab_dashboard:
            mostrar_modulo_dashboard_interactivo()
        return

    st.markdown("### 📂 Categorías")
    categoria_actual = st.session_state.categoria_inicio
    with st.container(key="velox_categoria_botones"):
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

    _render_documentos_categoria_inicio(
        seccion_id,
        categoria_actual,
        secciones_usuario,
        busqueda_key=f"buscador_inicio_{seccion_id}",
    )

# ==================== PUERTA DE ACCESO (post-definiciones) ====================
_legal_page = (st.query_params.get("page") or "").strip().lower()
if _legal_page == "terminos":
    mostrar_terminos_condiciones()
    st.stop()
if _legal_page == "privacidad":
    mostrar_politica_privacidad()
    st.stop()

auth_manager.inicializar_estado_auth()
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "inicio"

_auth_err = st.session_state.pop("auth_callback_error", None)
if _auth_err:
    st.error(_auth_err)

if not st.session_state.get("autenticado"):
    auth_manager.bootstrap_session()

auth_manager.sincronizar_vista_auth()

_usuario_con_acceso = (
    st.session_state.get("autenticado")
    and (st.session_state.get("acceso_pagado") or _es_staff())
    and not _registro_bloquea_acceso_app()
)

if _en_vista_recuperacion_password():
    render_pantalla_solo_recuperacion()
    st.stop()

if not _usuario_con_acceso:
    login_screen()
    st.stop()

else:
    # ==================== HEADER (solo después del login) ====================
    inject_post_login_shell_layout()
    inject_sidebar_collapse_control()
    render_velox_top_banner()
    render_app_top_bar()

    # ==================== SIDEBAR ====================
    with st.sidebar:
        inject_sidebar_theme()
        render_sidebar_brand()

        avatar = st.session_state.get("avatar_url")
        email_sidebar = (st.session_state.get("usuario") or "").strip()
        rol_sidebar = st.session_state.get("rol", "usuario")
        rol_badge = _etiqueta_rol_sidebar(rol_sidebar)

        st.markdown('<div class="sidebar-profile sidebar-profile--compact">', unsafe_allow_html=True)
        if avatar:
            _av_esp, _av_mid, _av_esp2 = st.columns([1, 1, 1])
            with _av_mid:
                st.image(avatar, width=64)
        if email_sidebar:
            email_seguro = html_module.escape(email_sidebar)
            st.markdown(
                f'<p class="sidebar-profile-email sidebar-profile-email--hero">{email_seguro}</p>',
                unsafe_allow_html=True,
            )
        st.caption(f"🔐 Gmail verificado · {rol_badge}")
        st.markdown("</div>", unsafe_allow_html=True)

        menu_items = _menu_sidebar_items()
        menu_labels = [item[0] for item in menu_items]
        menu_icons = [item[1] for item in menu_items]
        menu_values = [item[2] for item in menu_items]
        label_to_value = dict(zip(menu_labels, menu_values))
        value_to_label = dict(zip(menu_values, menu_labels))

        if st.session_state.get("menu_principal") not in menu_values:
            st.session_state["menu_principal"] = menu_values[0]

        current_label = value_to_label.get(st.session_state["menu_principal"], menu_labels[0])
        default_index = menu_labels.index(current_label) if current_label in menu_labels else 0

        with st.container(key="sidebar_menu_panel"):
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
            auth_manager.cerrar_sesion()
            st.rerun()

    # ==================== CONTENIDO PRINCIPAL ====================
    menu_actual = st.session_state.get('menu_principal', '🏠 Inicio')

    if menu_actual == "🏠 Inicio":
        if st.session_state.seccion_activa == "inicio":
            if _es_master():
                st.header("🏠 Inicio")
                secciones_usuario = list(SECCIONES.keys())
                _cache_v = _velox_data_cache_version()
                archivos_personales = cached_listar_archivos_usuario(
                    st.session_state["usuario"],
                    incluir_publicaciones=False,
                    data_cache_version=_cache_v,
                )
                publicaciones = cached_obtener_publicaciones_usuario(
                    st.session_state["usuario"],
                    tuple(secciones_usuario),
                    data_cache_version=_cache_v,
                )

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'<div class="metric-card"><h3>📄</h3><h3>{len(archivos_personales)}</h3><p>Mis Documentos</p></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-card"><h3>📢</h3><h3>{len(publicaciones)}</h3><p>Documentos Disponibles</p></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-card"><h3>📂</h3><h3>{len(secciones_usuario)}</h3><p>Secciones</p></div>', unsafe_allow_html=True)
                with col4:
                    usuarios_map = cached_listar_usuarios(data_cache_version=_cache_v)
                    usuarios_total = len(usuarios_map)
                    st.markdown(f'<div class="metric-card"><h3>👥</h3><h3>{usuarios_total}</h3><p>Usuarios</p></div>', unsafe_allow_html=True)

                todas_pubs = cached_obtener_publicaciones_por_seccion(data_cache_version=_cache_v)
                render_dashboard_analytics_master(todas_pubs, usuarios_map)

                st.markdown("---")
                render_catalogo_secciones_freemium(
                    list(SECCIONES.keys()),
                    titulo="### 📂 Todas las Secciones",
                    key_prefix="master",
                )
            elif _es_admin():
                st.header("🏠 Inicio — Administrador")
                secciones_usuario = _secciones_efectivas()
                if not secciones_usuario:
                    st.info(
                        "Aún no tienes secciones asignadas. El Master puede habilitarlas en "
                        "**Gestión Usuarios → Permisos Administrador**."
                    )
                elif _puede_ver_panorama_recursos():
                    publicaciones_user = cached_obtener_publicaciones_usuario(
                        st.session_state["usuario"],
                        tuple(secciones_usuario),
                        data_cache_version=_velox_data_cache_version(),
                    )
                    render_dashboard_analytics_user(secciones_usuario, publicaciones_user)
                    st.markdown("---")
                render_catalogo_secciones_freemium(
                    secciones_usuario,
                    titulo="### 📂 Secciones autorizadas",
                    key_prefix="admin",
                )
            else:
                st.header("🏠 Inicio")
                secciones_usuario = _secciones_efectivas()
                render_catalogo_secciones_freemium(
                    secciones_usuario,
                    key_prefix="user",
                    catalogo_centrado=True,
                )
        else:
            render_vista_seccion_inicio(st.session_state.seccion_activa)

    elif menu_actual == "📁 Mis Documentos":
        seccion_preseleccionada = st.session_state.pop("seccion_seleccionada_documentos", None)
        categoria_redirigida = st.session_state.pop("categoria_redirigida", None)
        notif_redirect_mensaje = st.session_state.pop("notif_redirect_mensaje", None)
        notif_redirect_publicacion_id = st.session_state.pop("notif_redirect_publicacion_id", None)
        st.query_params.clear()

        st.header("📁 Mis Documentos")
        if notif_redirect_mensaje:
            st.success(notif_redirect_mensaje)
        _sincronizar_rol_master_en_sesion()

        if _es_staff():
            with st.expander("🔧 Diagnóstico de permisos", expanded=False):
                st.write("Rol en session_state:", st.session_state.get("rol"))
                st.write("¿Es master?", _es_master())
                st.write("¿Puede publicar?", _puede_publicar_documentos())

        if _es_master():
            secciones_usuario = list(SECCIONES.keys())
        else:
            secciones_usuario = _secciones_efectivas()

        if not secciones_usuario:
            st.warning("⚠️ No tienes acceso a ninguna sección. Contacta al administrador.")
        else:
            opciones_secciones = [(s, SECCIONES[s]['nombre']) for s in secciones_usuario]
            seccion_preseleccionada_norm = (
                normalizar_seccion(seccion_preseleccionada) if seccion_preseleccionada else None
            )

            if categoria_redirigida and seccion_preseleccionada_norm:
                subs_redirect = SECCIONES.get(seccion_preseleccionada_norm, {}).get(
                    "subcategorias", ["General"]
                )
                if categoria_redirigida in subs_redirect:
                    st.session_state[
                        _mis_docs_categoria_key(seccion_preseleccionada_norm)
                    ] = categoria_redirigida

            indice_preseleccionado = 0
            if seccion_preseleccionada_norm:
                for idx, (sec_id, _) in enumerate(opciones_secciones):
                    if sec_id == seccion_preseleccionada_norm:
                        indice_preseleccionado = idx
                        st.session_state["selector_seccion_documentos"] = opciones_secciones[idx]
                        break

            seccion_seleccionada = st.selectbox(
                "Seleccionar sección:",
                options=opciones_secciones,
                format_func=lambda x: x[1],
                index=indice_preseleccionado,
                key="selector_seccion_documentos",
            )[0]
            seccion_info = SECCIONES[seccion_seleccionada]

            st.markdown(f"""
            <div style="background: {seccion_info['color']}10; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                <h3>{seccion_info['nombre']}</h3>
                <p>{seccion_info['descripcion']}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔙 Volver al Dashboard", key="btn_volver_dashboard"):
                st.rerun()

            subcategorias_disponibles = seccion_info.get("subcategorias", ["General"])
            st.markdown("### 📂 Categorías")

            cat_key = _mis_docs_categoria_key(seccion_seleccionada)
            categoria_actual = _obtener_categoria_mis_docs(
                seccion_seleccionada, subcategorias_disponibles
            )

            if seccion_preseleccionada_norm:
                st.session_state[
                    _docs_pagina_session_key(seccion_seleccionada, categoria_actual, prefijo="pub")
                ] = 1
                _invalidar_cache_datos()

            with st.container(key="velox_categoria_botones"):
                cols_cat = st.columns(len(subcategorias_disponibles))
                for idx, cat in enumerate(subcategorias_disponibles):
                    with cols_cat[idx]:
                        st.button(
                            cat,
                            key=f"cat_{seccion_seleccionada}_{idx}_{cat}",
                            use_container_width=True,
                            type="primary" if categoria_actual == cat else "secondary",
                            on_click=seleccionar_categoria_mis_docs,
                            kwargs={"seccion_id": seccion_seleccionada, "categoria": cat},
                        )

            st.markdown(f"**Categoría actual:** {categoria_actual}")

            st.markdown(MIS_DOCS_COMPACT_CSS, unsafe_allow_html=True)
            busqueda = st.text_input(
                "🔍 Buscar documentos",
                placeholder="Filtra por nombre, descripción o palabra clave…",
                key="buscador_mis_docs",
                label_visibility="collapsed",
            )
            st.caption("Búsqueda instantánea sobre los documentos de la categoría seleccionada.")

            if (
                _puede_publicar_documentos()
                and seccion_seleccionada in secciones_usuario
                and _puede_modulo(AuthManager.MODULO_DOCUMENTOS)
            ):
                with st.expander("📤 Publicar documento", expanded=_es_admin()):
                    st.caption(
                        f"Publicación en **{seccion_info['nombre']}** · categoría **{categoria_actual}**"
                    )
                    # Categoría fijada al renderizar el formulario (evita desfase al enviar)
                    st.session_state[f"mis_docs_pub_target_{seccion_seleccionada}"] = categoria_actual
                    with st.form(
                        key=f"form_pub_{seccion_seleccionada}",
                        clear_on_submit=True,
                    ):
                        st.text_input(
                            "Categoría de destino",
                            value=categoria_actual,
                            disabled=True,
                        )
                        archivo_pub = st.file_uploader(
                            "Seleccionar archivo",
                            type=["pdf", "xlsx", "xls", "docx", "doc"],
                        )
                        descripcion_texto = st.text_area(
                            "Descripción",
                            height=120,
                            placeholder="Enlaces, comentarios o instrucciones para los alumnos…",
                        )
                        submitted = st.form_submit_button(
                            "Publicar documento",
                            type="primary",
                        )

                    if submitted:
                        categoria_publicar = (
                            st.session_state.get(f"mis_docs_pub_target_{seccion_seleccionada}")
                            or st.session_state.get(cat_key)
                            or categoria_actual
                        )
                        descripcion_guardar = (descripcion_texto or "").strip()
                        if not archivo_pub:
                            st.error("❌ Selecciona un archivo antes de publicar.")
                        else:
                            try:
                                with _velox_spinner("Publicando y notificando a los alumnos..."):
                                    exito, resultado = storage_manager.publicar_documento(
                                        archivo_pub,
                                        seccion_seleccionada,
                                        categoria_publicar,
                                        descripcion_guardar,
                                        publicador_email=st.session_state["usuario"],
                                    )
                                if exito:
                                    _mostrar_alerta_publicacion(exito, resultado)
                                    _invalidar_cache_datos()
                                    st.session_state[cat_key] = categoria_publicar
                                    st.session_state[
                                        _docs_pagina_session_key(
                                            seccion_seleccionada,
                                            categoria_publicar,
                                            prefijo="pub",
                                        )
                                    ] = 1
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error en la publicación: {resultado}")
                            except Exception as err:
                                st.error(f"❌ Error inesperado al publicar: {err}")
                st.markdown("---")

            # Publicaciones disponibles
            titulo_publicaciones = (
                "### 📢 Publicaciones del Master" if _es_master() else "### 📢 Publicaciones disponibles"
            )
            _render_bloque_publicaciones_compacto(
                seccion_seleccionada,
                categoria_actual,
                busqueda,
                secciones_usuario,
                prefijo="pub",
                titulo=titulo_publicaciones,
                mensaje_vacio="No hay publicaciones del master en esta categoría",
                seccion_info=seccion_info,
                sincronizar_chatbot=True,
            )

    # ==================== RESTO DE SECCIONES (sin cambios) ====================
    elif menu_actual == AuthManager.MODULO_GESTION_USUARIOS and _puede_modulo(AuthManager.MODULO_GESTION_USUARIOS):
        st.header("👥 Gestión de Usuarios y Permisos")
        tab_labels = ["📋 Lista de Usuarios", "🔐 Asignar Secciones"]
        if _es_master():
            tab_labels.append("🛡️ Permisos Administrador")
        tabs = st.tabs(tab_labels)
        tab1, tab2 = tabs[0], tabs[1]
        tab_perm_admin = tabs[2] if _es_master() else None

        with tab1:
            if _es_master():
                render_lista_usuarios_master()
            else:
                render_lista_usuarios_solo_lectura()
        with tab2:
            st.markdown("Asignar secciones a usuario")
            usuarios_lista = [
                e
                for e in cached_listar_usuarios(data_cache_version=_velox_data_cache_version())
                if e != st.session_state["usuario"]
            ]
            if usuarios_lista:
                usuario = st.selectbox("Usuario", usuarios_lista)
                actuales = cached_obtener_secciones_usuario(
                    usuario, data_cache_version=_velox_data_cache_version()
                )
                nuevas = []
                cols = st.columns(3)
                for i, (k, v) in enumerate(SECCIONES.items()):
                    with cols[i%3]:
                        if st.checkbox(f"{v['nombre']}", value=(k in actuales), key=f"perm_{usuario}_{k}"):
                            nuevas.append(k)
                if st.button("Guardar permisos"):
                    auth_manager.asignar_secciones_usuario(usuario, nuevas, st.session_state['usuario'])
                    _invalidar_cache_datos()
                    st.rerun()
            else:
                st.info("No hay otros usuarios")

        if tab_perm_admin is not None:
            with tab_perm_admin:
                render_permisos_administrador_tab()

    elif menu_actual == AuthManager.MODULO_COBRANZAS and _puede_modulo(AuthManager.MODULO_COBRANZAS):
        render_gestion_cobranzas_master()

    elif menu_actual == AuthManager.MODULO_CONFIGURACION and _puede_modulo(AuthManager.MODULO_CONFIGURACION):
        st.header("Configuración")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Limpiar facturas (demo)"):
                st.warning("Función no implementada")
        with col2:
            st.info("Versión 1.0")

    elif menu_actual == AuthManager.MODULO_CONSULTAS:
        if _es_staff() and _puede_modulo(AuthManager.MODULO_CONSULTAS):
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
            secciones_usuario = cached_obtener_secciones_usuario(
                st.session_state["usuario"],
                data_cache_version=_velox_data_cache_version(),
            )
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
        if _es_master():
            st.warning("Este módulo no está disponible para tu rol.")
        else:
            st.header("Mi Perfil")
            usuario_email = st.session_state["usuario"]
            perfil = auth_manager.obtener_perfil(usuario_email)
            if not perfil:
                st.warning("No se pudo cargar tu perfil.")
            else:
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if perfil.get("avatar_url"):
                        st.image(perfil["avatar_url"], width=100)
                with col_b:
                    st.markdown(f"**Nombre:** {perfil['nombre']}")
                    st.markdown(f"**Email Google verificado:** {perfil['email']}")
                    st.markdown(f"**Rol:** {perfil['rol'].upper()}")
                    st.markdown(f"**ID veloX:** {perfil.get('codigo_usuario', '—')}")
                    st.markdown("**Secciones asignadas:**")
                    secciones_usuario = cached_obtener_secciones_usuario(
                        usuario_email,
                        data_cache_version=_velox_data_cache_version(),
                    )
                    for s in secciones_usuario:
                        if s in SECCIONES:
                            st.markdown(f"- {SECCIONES[s]['nombre']}")

                st.markdown("---")
                st.subheader("Datos de contacto")
                with st.form("edit_perfil"):
                    st.text_input("Nombre completo", value=perfil["nombre"], disabled=True)

                    col_correo_1, col_correo_2 = st.columns([1, 1])
                    with col_correo_1:
                        correo_personal = st.text_input(
                            "Correo Personal Principal",
                            value=perfil.get("correo_personal", ""),
                        )
                    with col_correo_2:
                        correo_secundario = st.text_input(
                            "Correo Secundario (Opcional)",
                            value=perfil.get("correo_secundario", ""),
                        )

                    col_cel_1, col_cel_2 = st.columns([1, 1])
                    with col_cel_1:
                        celular = st.text_input(
                            "Celular Principal",
                            value=perfil.get("celular", ""),
                        )
                    with col_cel_2:
                        celular_secundario = st.text_input(
                            "Celular Secundario (Opcional)",
                            value=perfil.get("celular_secundario", ""),
                        )

                    if st.form_submit_button("Guardar cambios"):
                        ok, msg = auth_manager.actualizar_perfil(
                            usuario_email,
                            {
                                "correo_personal": correo_personal,
                                "correo_secundario": correo_secundario,
                                "celular": celular,
                                "celular_secundario": celular_secundario,
                            },
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    if _chatbot_visible_en_modulo_actual():
        render_chatbot_asistente()

    render_footer()
