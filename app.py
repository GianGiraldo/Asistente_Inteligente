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
@st.cache_resource(show_spinner=False)
def _velox_pwa_icon_data_uri() -> str:
    path = "assets/velox.png"
    if not os.path.exists(path):
        return path
    with open(path, "rb") as icon_file:
        return "data:image/png;base64," + base64.b64encode(icon_file.read()).decode("ascii")


_velox_pwa_icon_href = _velox_pwa_icon_data_uri()

st.markdown(
    f"""
    <meta name="apple-mobile-web-app-title" content="veloX">
    <meta name="application-name" content="veloX">
    <meta property="og:title" content="veloX">
    <meta property="og:description" content="veloX — plataforma de gestión documental inteligente para profesionales y empresas.">
    <meta name="description" content="veloX — plataforma de gestión documental inteligente para profesionales y empresas.">
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

inject_velox_loading_brand()

import base64
import contextlib
import html as html_module
import io
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
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
    inject_section_detail_banner_css,
    inject_sidebar_theme,
    inject_welcome_layout,
    WELCOME_LAYOUT_CSS,
    MAIN_CONTENT_AREA_CSS,
    VELOX_ULTRA_COMPACT_LAYOUT_CSS,
)

VELOX_BANNER_PATH = "assets/portada.jpeg"
VELOX_PORTADA_PATH = "assets/velox_fondo_login_sin_circulo.png"
VELOX_ICONO_LOGO_PATH = "assets/velox_icono_logo.png"


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


def inject_inicio_servicios_accesos_css() -> None:
    """CSS barra de servicios Inicio: re-inyectado en cada rerun post-login (sin flags)."""
    css_slot = st.empty()
    css_slot.markdown(INICIO_SERVICIOS_ACCESOS_CSS, unsafe_allow_html=True)


def inject_post_login_shell_layout():
    """Ordena capas y columnas del shell autenticado (sidebar vs. contenido central)."""
    st.markdown(VELOX_POST_LOGIN_SHELL_CSS, unsafe_allow_html=True)
    inject_inicio_servicios_accesos_css()
    inject_sidebar_theme()


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
    if not _velox_banner_existe():
        return
    with st.container(key="velox_top_banner"):
        st.image(VELOX_BANNER_PATH, use_container_width=True)


@st.cache_resource(show_spinner=False)
def _velox_banner_existe(path: str = VELOX_BANNER_PATH) -> bool:
    return os.path.exists(path)


@st.cache_resource(show_spinner=False)
def init_auth_manager():
    """Solo AuthManager antes del login (OAuth / sesión)."""
    return AuthManager()


@st.cache_resource(show_spinner=False)
def init_data_managers(_cache_version=4):
    """Managers de datos pesados — se instancian tras el login."""
    storage = StorageManager()
    messages = MessageManager()
    notifications = NotificationManager()
    payments = PaymentManager()
    return storage, messages, notifications, payments


auth_manager = init_auth_manager()
storage_manager = message_manager = notification_manager = payment_manager = None


VELOX_DATA_CACHE_VERSION_KEY = "velox_data_cache_version"


def _ensure_data_managers() -> None:
    """Lazy bind post-login: evita Storage/Message/Notification/Payment en pantalla de login."""
    global storage_manager, message_manager, notification_manager, payment_manager
    storage_manager, message_manager, notification_manager, payment_manager = init_data_managers()


def _velox_data_cache_version() -> int:
    return int(st.session_state.get(VELOX_DATA_CACHE_VERSION_KEY, 0))


def _invalidar_cache_consultas() -> None:
    """Refresca lecturas de consultas/notificaciones sin invalidar todo el catálogo."""
    try:
        cached_contar_consultas_no_leidas.clear()
        cached_contar_consultas_soporte_master.clear()
        cached_obtener_historial_consultas_usuario.clear()
        cached_obtener_historial_consultas_completo.clear()
        cached_obtener_consultas_pendientes_master.clear()
        cached_obtener_consultas_respondidas_master.clear()
    except Exception:
        pass


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
        cached_contar_consultas_no_leidas.clear()
        cached_contar_pagos_pendientes.clear()
        cached_contar_consultas_soporte_master.clear()
        cached_obtener_notificaciones_no_leidas.clear()
        cached_obtener_consultas_pendientes_master.clear()
        cached_obtener_consultas_respondidas_master.clear()
        cached_obtener_historial_consultas_usuario.clear()
        cached_obtener_historial_consultas_completo.clear()
        cached_obtener_perfil_usuario.clear()
    except Exception:
        pass


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_publicaciones_por_seccion(
    seccion: Optional[str] = None,
    subcategoria: Optional[str] = None,
    data_cache_version: int = 0,
):
    storage, _, _, _ = init_data_managers()
    return storage.obtener_publicaciones_por_seccion(seccion=seccion, subcategoria=subcategoria)


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_catalogo_seccion(
    seccion: str,
    subcategoria: Optional[str] = None,
    data_cache_version: int = 0,
):
    storage, _, _, _ = init_data_managers()
    return storage.listar_catalogo_seccion(seccion, subcategoria)


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_archivos_usuario(
    usuario: str,
    seccion: Optional[str] = None,
    subcategoria: Optional[str] = None,
    incluir_publicaciones: bool = False,
    data_cache_version: int = 0,
):
    storage, _, _, _ = init_data_managers()
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
    storage, _, _, _ = init_data_managers()
    return storage.obtener_publicaciones_usuario(usuario, list(secciones_usuario))


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_usuarios(data_cache_version: int = 0):
    return auth_manager.listar_usuarios()


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_secciones_usuario(email: str, data_cache_version: int = 0):
    return auth_manager.obtener_secciones_usuario(email)


@st.cache_data(show_spinner=False, ttl=300)
def cached_contar_publicaciones_por_seccion(data_cache_version: int = 0) -> dict:
    storage, _, _, _ = init_data_managers()
    conteos: dict = {}
    for pub in storage.obtener_publicaciones_por_seccion():
        seccion = pub.get("seccion") or ""
        conteos[seccion] = conteos.get(seccion, 0) + 1
    return conteos


@st.cache_data(show_spinner=False, ttl=300)
def cached_listar_pagos_pendientes(data_cache_version: int = 0):
    _, _, _, payments = init_data_managers()
    return payments.listar_pagos_pendientes()


@st.cache_data(show_spinner=False, ttl=300)
def cached_contar_consultas_no_leidas(email: str, data_cache_version: int = 0) -> int:
    _, messages, _, _ = init_data_managers()
    return messages.contar_consultas_no_leidas(email)


@st.cache_data(show_spinner=False, ttl=300)
def cached_contar_pagos_pendientes(data_cache_version: int = 0) -> int:
    _, _, _, payments = init_data_managers()
    return payments.contar_pagos_pendientes()


@st.cache_data(show_spinner=False, ttl=300)
def cached_contar_consultas_soporte_master(data_cache_version: int = 0) -> int:
    _, messages, _, _ = init_data_managers()
    return messages.contar_consultas_soporte_no_leidas_master()


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_notificaciones_no_leidas(email: str, data_cache_version: int = 0):
    _, _, notifications, _ = init_data_managers()
    return notifications.obtener_notificaciones_no_leidas(email)


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_consultas_pendientes_master(data_cache_version: int = 0):
    _, messages, _, _ = init_data_managers()
    return messages.obtener_mensajes_para_master(respondidos=False)


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_consultas_respondidas_master(data_cache_version: int = 0):
    _, messages, _, _ = init_data_managers()
    return messages.obtener_mensajes_para_master(respondidos=True)


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_historial_consultas_usuario(email: str, data_cache_version: int = 0):
    _, messages, _, _ = init_data_managers()
    return messages.obtener_mensajes_usuario(email)


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_historial_consultas_completo(data_cache_version: int = 0):
    _, messages, _, _ = init_data_managers()
    return messages.obtener_historial_completo()


@st.cache_data(show_spinner=False, ttl=300)
def cached_obtener_perfil_usuario(email: str, data_cache_version: int = 0):
    return auth_manager.obtener_perfil(email)


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
        "nombre": "Contabilidad",
        "icono": "📊",
        "color": "#2ecc71",
        "descripcion": "Facturas, balances, libros contables",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"],
        "active": True,
    },
    "power_bi": {
        "nombre": "Power BI",
        "icono": "📉",
        "color": "#3498db",
        "descripcion": "Dashboards interactivos, análisis de datos y reportes visuales",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"],
        "active": False,
    },
    "comercio_exterior": {
        "nombre": "Comercio Exterior",
        "icono": "🌐",
        "color": "#f1c40f",
        "descripcion": "Importaciones, exportaciones, aduanas y operaciones internacionales",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"],
        "active": False,
    },
    "logistico": {
        "nombre": "Logístico",
        "icono": "🚚",
        "color": "#e67e22",
        "descripcion": "Guías, inventarios, despachos",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"],
        "active": True,
    },
    "excel": {
        "nombre": "Excel",
        "icono": "📈",
        "color": "#1abc9c",
        "descripcion": "Plantillas, reportes, análisis",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"],
        "active": True,
    },
    "comercial": {
        "nombre": "Comercial",
        "icono": "💼",
        "color": "#9b59b6",
        "descripcion": "Ventas, clientes, KPIs y proyecciones.",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"],
        "active": True,
    },
    "laboral": {
        "nombre": "Laboral",
        "icono": "👥",
        "color": "#e74c3c",
        "descripcion": "Contratos, planillas, normativas y beneficios.",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"],
        "active": True,
    },
}

# Ids legacy en Supabase / publicaciones → id canónico en SECCIONES
SECCION_LEGACY_IDS = {
    "financiero": "comercio_exterior",
}

SECCION_BANNER_PATHS = {
    "contabilidad": "assets/banner_contabilidad.svg",
    "power_bi": "assets/banner_power_bi.svg",
    "comercio_exterior": "assets/banner_comercio_exterior.svg",
    "logistico": "assets/banner_logistica.svg",
    "excel": "assets/banner_excel.svg",
    "comercial": "assets/banner_comercial_ventas.svg",
    "laboral": "assets/banner_laboral.svg",
}


def _seccion_esta_activa(seccion_id: str) -> bool:
    info = SECCIONES.get(seccion_id)
    if not info:
        return False
    return bool(info.get("active", True))


def _secciones_catalogo_visibles() -> list[tuple[str, dict]]:
    return [(k, v) for k, v in SECCIONES.items() if _seccion_esta_activa(k)]


def _resolver_seccion_id(seccion_id: str) -> str:
    sid = (seccion_id or "").strip().lower()
    return SECCION_LEGACY_IDS.get(sid, sid)

MENU_SIDEBAR_MASTER = [
    ("Inicio", "house", "🏠 Inicio"),
    ("Mis Documentos", "folder", "📁 Mis Documentos"),
    ("Gestión Usuarios", "people", "👥 Gestión Usuarios"),
    ("Cobranzas", "credit-card", "💳 Cobranzas"),
    ("Consultas", "envelope", "💬 Consultas"),
    ("Configuración", "gear", "⚙️ Configuración"),
]
MENU_SIDEBAR_USER = [
    ("Inicio", "house", "🏠 Inicio"),
    ("Mis Documentos", "folder", "📁 Mis Documentos"),
    ("Consultas", "envelope", "💬 Consultas"),
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
    if st.session_state.get("_velox_text_input_css_injected"):
        return
    st.markdown(VELOX_TEXT_INPUT_CSS, unsafe_allow_html=True)
    st.session_state["_velox_text_input_css_injected"] = True


def inject_olvido_password_link_styles():
    if st.session_state.get("_velox_forgot_password_css_injected"):
        return
    st.markdown(FORGOT_PASSWORD_LINK_CSS, unsafe_allow_html=True)
    st.session_state["_velox_forgot_password_css_injected"] = True


def inject_login_portal_brand_styles():
    if st.session_state.get("_velox_login_portal_css_injected"):
        return
    st.markdown(LOGIN_PORTAL_BRAND_CSS, unsafe_allow_html=True)
    st.session_state["_velox_login_portal_css_injected"] = True


def _build_velox_auth_dark_portal_css() -> str:
    portada_uri = _velox_logo_data_uri(VELOX_PORTADA_PATH)
    bg_image = f"url('{portada_uri}')" if portada_uri else "none"
    return f"""
<style id="velox-auth-dark-portal-v5">
    html:has(.velox-id-bar),
    html:has(.velox-auth-brand),
    body:has(.velox-id-bar),
    body:has(.velox-auth-brand),
    .stApp:has(.velox-id-bar),
    .stApp:has(.velox-auth-brand),
    .stApp:has(.velox-id-bar) [data-testid="stAppViewContainer"],
    .stApp:has(.velox-auth-brand) [data-testid="stAppViewContainer"],
    .stApp:has(.velox-id-bar) [data-testid="stMain"],
    .stApp:has(.velox-auth-brand) [data-testid="stMain"] {{
        background: {bg_image} center top / cover no-repeat fixed #0A0E14 !important;
        background-color: #0A0E14 !important;
    }}

    .stApp:has(.velox-id-bar) [data-testid="stMain"] .block-container,
    .stApp:has(.velox-auth-brand) [data-testid="stMain"] .block-container {{
        background: transparent !important;
    }}

    .stApp:has(.velox-id-bar) [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(.velox-auth-brand) [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(.velox-auth-brand) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(.velox-auth-brand) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(8, 12, 22, 0.78) !important;
        border: 1px solid rgba(0, 210, 255, 0.18) !important;
        border-radius: 18px !important;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }}

    .stApp:has(.velox-id-bar) .velox-portal-form div[data-testid="stTextInput"] input,
    .stApp:has(.velox-id-bar) .velox-portal-form .stTextInput > div > div > input,
    .stApp:has(.velox-id-bar) .main .block-container .velox-portal-form div[data-testid="stTextInput"] input,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .stTextInput > div > div > input,
    .stApp:has(.velox-auth-brand) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .stTextInput > div > div > input,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) .stTextInput > div > div > input,
    .stApp:has(.velox-auth-brand) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) .stTextInput > div > div > input {{
        background: transparent !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: none !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.38) !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0.55rem 0 0.65rem !important;
    }}

    .stApp:has(.velox-id-bar) .velox-portal-form div[data-testid="stTextInput"] input::placeholder,
    .stApp:has(.velox-id-bar) .velox-portal-form .stTextInput > div > div > input::placeholder,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .stTextInput > div > div > input::placeholder,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) .stTextInput > div > div > input::placeholder {{
        color: rgba(255, 255, 255, 0.45) !important;
    }}

    .stApp:has(.velox-id-bar) .velox-portal-form div[data-testid="stTextInput"] input:focus,
    .stApp:has(.velox-id-bar) .velox-portal-form .stTextInput > div > div > input:focus,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) div[data-testid="stTextInput"] input:focus,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) div[data-testid="stTextInput"] input:focus {{
        border-bottom-color: #00E5FF !important;
        box-shadow: none !important;
        outline: none !important;
    }}

    .stApp:has(.velox-id-bar) .velox-id-bar--marker {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        overflow: hidden !important;
    }}

    .velox-auth-brand {{
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        width: 100%;
        margin: 0.35rem 0 0.85rem;
    }}

    .velox-auth-icon-ring {{
        width: 92px;
        height: 92px;
        border-radius: 50%;
        padding: 8px;
        margin: 0 auto 0.65rem;
        background: rgba(255, 255, 255, 0.08);
        border: 2px solid rgba(0, 229, 255, 0.55);
        box-shadow: 0 0 24px rgba(0, 210, 255, 0.22);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }}

    .velox-auth-icon-img {{
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
    }}

    .velox-auth-wordmark {{
        margin: 0;
        font-size: 2.15rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        line-height: 1.1;
    }}

    .velox-auth-wordmark-velo {{
        color: #E2F1FF !important;
    }}

    .velox-auth-wordmark-x {{
        color: #00E5FF;
        text-shadow: 0 0 16px rgba(0, 229, 255, 0.45);
    }}

    .velox-auth-tagline,
    .velox-brand-stack .velox-tagline--center {{
        color: #E2E8F0 !important;
        font-size: 0.92rem !important;
        line-height: 1.5 !important;
        max-width: 22rem;
        margin: 0.35rem auto 0.75rem !important;
        text-align: center !important;
    }}

    .stApp:has(.velox-id-bar) .velox-auth-field-label,
    .stApp:has(.velox-auth-brand) .velox-auth-field-label {{
        display: block;
        margin: 0.65rem 0 0.35rem;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: #FFFFFF !important;
        text-transform: uppercase;
    }}

    .stApp:has(.velox-id-bar) .velox-id-bar,
    .stApp:has(.velox-id-bar) .velox-id-bar--register {{
        background: rgba(0, 210, 255, 0.12) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(0, 210, 255, 0.25) !important;
        border-radius: 12px !important;
    }}

    .stApp:has(.velox-id-bar) .velox-section-caption,
    .stApp:has(.velox-id-bar) .velox-register-sub,
    .stApp:has(.velox-id-bar) .velox-register-header,
    .stApp:has(.velox-id-bar) [data-testid="stCaptionContainer"],
    .stApp:has(.velox-id-bar) [data-testid="stCaptionContainer"] p {{
        color: rgba(255, 255, 255, 0.78) !important;
    }}

    .stApp:has(.velox-id-bar) .velox-register-header {{
        color: #FFFFFF !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_olvido_password .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_olvido_password .stButton > button * {{
        color: rgba(255, 255, 255, 0.62) !important;
        font-weight: 500 !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_olvido_password .stButton > button:hover {{
        color: rgba(255, 255, 255, 0.88) !important;
    }}

    .velox-auth-register-footer {{
        text-align: center;
        margin-top: 1rem;
        padding-top: 0.85rem;
        border-top: 1px solid rgba(255, 255, 255, 0.12);
    }}

    .velox-auth-register-prompt {{
        color: #CBD5E1 !important;
        font-size: 0.88rem;
        margin: 0 0 0.45rem;
    }}

    .velox-login-recordarme-label {{
        color: #FFFFFF !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        padding: 0 !important;
        white-space: nowrap;
    }}

    .stApp:has(.velox-id-bar) .st-key-login_recordarme_row [data-testid="stHorizontalBlock"],
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_row [data-testid="stHorizontalBlock"] {{
        align-items: center !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-login_recordarme_row div[data-testid="column"]:last-child,
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_row div[data-testid="column"]:last-child,
    .stApp:has(.velox-id-bar) .st-key-login_recordarme_row div[data-testid="stColumn"]:last-child,
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_row div[data-testid="stColumn"]:last-child {{
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-login_recordarme_wrap [data-testid="stVerticalBlock"],
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_wrap [data-testid="stVerticalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 0.5rem !important;
        min-height: 2.4rem;
    }}

    .stApp:has(.velox-id-bar) .st-key-login_recordarme_wrap [data-testid="stElementContainer"],
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_wrap [data-testid="stElementContainer"] {{
        width: auto !important;
        flex: 0 0 auto !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-login_recordarme_wrap [data-testid="stToggle"],
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_wrap [data-testid="stToggle"] {{
        margin: 0 !important;
        padding: 0 !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-login_recordarme_wrap [data-testid="stToggle"] label,
    .stApp:has(.velox-id-bar) .st-key-login_recordarme_wrap [data-testid="stToggle"] label p,
    .stApp:has(.velox-id-bar) .st-key-login_recordarme_wrap [data-testid="stToggle"] label span,
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_wrap [data-testid="stToggle"] label,
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_wrap [data-testid="stToggle"] label p,
    .stApp:has(.velox-auth-brand) .st-key-login_recordarme_wrap [data-testid="stToggle"] label span {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_registrarme_portal .stButton > button,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .st-key-btn_registrarme_portal .stButton > button {{
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        border: none !important;
        box-shadow: none !important;
        color: #00E5FF !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        min-height: auto !important;
        padding: 0.15rem 0 !important;
        text-decoration: underline;
        text-underline-offset: 3px;
        border-radius: 0 !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_registrarme_portal .stButton > button p,
    .stApp:has(.velox-id-bar) .st-key-btn_registrarme_portal .stButton > button span {{
        color: #00E5FF !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_registro_reenviar_otp .stButton > button {{
        background: rgba(255, 255, 255, 0.06) !important;
        color: rgba(255, 255, 255, 0.88) !important;
        border: 1px solid rgba(0, 210, 255, 0.35) !important;
        border-radius: 25px !important;
        font-weight: 600 !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_registro_reenviar_otp .stButton > button:hover {{
        background: rgba(0, 210, 255, 0.12) !important;
        border-color: rgba(0, 210, 255, 0.55) !important;
    }}

    .stApp:has(.velox-id-bar) [data-testid="stToggle"] label,
    .stApp:has(.velox-id-bar) [data-testid="stToggle"] label p,
    .stApp:has(.velox-id-bar) [data-testid="stToggle"] label span,
    .stApp:has(.velox-auth-brand) [data-testid="stToggle"] label,
    .stApp:has(.velox-auth-brand) [data-testid="stToggle"] label p,
    .stApp:has(.velox-auth-brand) [data-testid="stToggle"] label span {{
        color: #F8FAFC !important;
    }}

    .stApp:has(.velox-id-bar) .google-btn-wrap a {{
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 25px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
    }}

    .stApp:has(.velox-id-bar) .velox-register-success {{
        text-align: center;
        padding: 0.5rem 0 0.25rem;
    }}

    .stApp:has(.velox-id-bar) .velox-register-success__title {{
        color: #FFFFFF !important;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0.35rem 0 0.5rem;
    }}

    .stApp:has(.velox-id-bar) .velox-register-success__text {{
        color: rgba(255, 255, 255, 0.82) !important;
        font-size: 0.88rem;
        line-height: 1.5;
    }}

    .stApp:has(.velox-id-bar) .velox-portal-scroll {{
        scrollbar-color: rgba(0, 210, 255, 0.45) rgba(8, 12, 22, 0.5);
    }}

    .stApp:has(.velox-id-bar) .velox-portal-scroll::-webkit-scrollbar-track {{
        background: rgba(8, 12, 22, 0.5);
    }}

    .stApp:has(.velox-id-bar) .velox-portal-scroll::-webkit-scrollbar-thumb {{
        background: rgba(0, 210, 255, 0.45);
    }}

    .stApp:has(.velox-id-bar) .velox-auth-footer,
    .stApp:has(.velox-id-bar) .velox-auth-footer a {{
        color: rgba(255, 255, 255, 0.62) !important;
    }}

    .stApp:has(.velox-id-bar) .velox-auth-footer a:hover {{
        color: #00E5FF !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_iniciar_sesion_velox .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_iniciar_sesion .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_registrarse .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_enviar_otp .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_validar_otp .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_guardar_password_otp .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_ir_login .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_guardar_password_velox .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_actualizar_password_recuperacion .stButton > button,
    .stApp:has(.velox-id-bar) .velox-btn-primary .stButton > button,
    .stApp:has(.velox-id-bar) .main .block-container [data-testid="stBaseButton-primary"] button,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button,
    .stApp:has(.velox-auth-brand) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button,
    .stApp:has(.velox-id-bar) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-primary"] button,
    .stApp:has(.velox-auth-brand) .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-primary"] button {{
        background: linear-gradient(90deg, #00d2ff 0%, #0052d4 100%) !important;
        background-image: linear-gradient(90deg, #00d2ff 0%, #0052d4 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 25px !important;
        box-shadow: 0 8px 24px rgba(0, 82, 212, 0.38) !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_iniciar_sesion_velox .stButton > button:hover,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_iniciar_sesion .stButton > button:hover,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_registrarse .stButton > button:hover,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_enviar_otp .stButton > button:hover,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_validar_otp .stButton > button:hover,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_guardar_password_otp .stButton > button:hover,
    .stApp:has(.velox-id-bar) .st-key-btn_registro_ir_login .stButton > button:hover,
    .stApp:has(.velox-id-bar) .velox-btn-primary .stButton > button:hover,
    .stApp:has(.velox-id-bar) .main .block-container [data-testid="stBaseButton-primary"] button:hover {{
        background: linear-gradient(90deg, #33dbff 0%, #1a66e0 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 10px 28px rgba(0, 82, 212, 0.48) !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_iniciar_sesion_velox .stButton > button:focus,
    .stApp:has(.velox-id-bar) .st-key-btn_iniciar_sesion_velox .stButton > button:active,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_iniciar_sesion .stButton > button:focus,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_iniciar_sesion .stButton > button:active,
    .stApp:has(.velox-id-bar) .main .block-container [data-testid="stBaseButton-primary"] button:focus,
    .stApp:has(.velox-id-bar) .main .block-container [data-testid="stBaseButton-primary"] button:active {{
        background: linear-gradient(90deg, #00d2ff 0%, #0052d4 100%) !important;
        color: #FFFFFF !important;
        outline: none !important;
        box-shadow: 0 8px 24px rgba(0, 82, 212, 0.38) !important;
    }}

    .stApp:has(.velox-id-bar) .st-key-btn_iniciar_sesion_velox .stButton > button p,
    .stApp:has(.velox-id-bar) .st-key-btn_iniciar_sesion_velox .stButton > button span,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_iniciar_sesion .stButton > button p,
    .stApp:has(.velox-id-bar) .st-key-btn_gate_registrarse .stButton > button p,
    .stApp:has(.velox-id-bar) .main .block-container [data-testid="stBaseButton-primary"] button p,
    .stApp:has(.velox-id-bar) .main .block-container [data-testid="stBaseButton-primary"] button span {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    .stApp:has(.velox-id-bar) .velox-divider-or span {{
        color: rgba(255, 255, 255, 0.55) !important;
        background: rgba(8, 12, 22, 0.78) !important;
    }}

    .stApp:has(.velox-id-bar) .velox-back-login .stButton > button {{
        color: rgba(255, 255, 255, 0.65) !important;
    }}

    .stApp:has(.velox-id-bar) hr {{
        border-color: rgba(255, 255, 255, 0.12) !important;
    }}
</style>
"""


def inject_velox_auth_dark_portal_styles():
    st.markdown(_build_velox_auth_dark_portal_css(), unsafe_allow_html=True)

# ==================== PASARELA DE BIENVENIDA veloX (Premium) ====================
YAPE_QR_PATH = "assets/qr_pago.png"
YAPE_TITULAR = "Gian Pier Giraldo Pariona"
MSG_YAPE_SUBIR_COMPROBANTE = "Sube tu comprobante para validar tu acceso."
MSG_YAPE_COMPROBANTE_OK = "✅ Comprobante enviado. Activaremos tu acceso a la brevedad."
YAPE_QR_SEGURIDAD_HTML = f"""
<div style="text-align:center;font-size:0.86rem;color:#334155;line-height:1.45;margin-top:0.5rem;">
<p style="margin:0.35rem 0;"><strong>Titular:</strong> {YAPE_TITULAR}</p>
<p style="margin:0.35rem 0;">⚠️ <em>Verifica que el nombre del destinatario en Yape sea exacto antes de confirmar.</em></p>
</div>
"""
WHATSAPP_ADMIN_LINK = "https://wa.me/51913827482?text=Hola,%20solicito%20información%20sobre%20la%20seccion%20.........."
YAPE_OAUTH_KEYS = ["yape_oauth_celular", "yape_comprobante_upload"]
WELCOME_TAB_GATE = -1
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

    /* Barra superior del formulario de acceso (márgenes; colores en tema dark) */
    .stApp:has(.velox-id-bar) .velox-id-bar,
    .stApp:has(.velox-id-bar) .velox-id-bar--register {{
        margin: 0.65rem 0.75rem 0.25rem !important;
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


def _build_velox_auth_portal_css_bundle() -> str:
    return (
        WELCOME_LAYOUT_CSS
        + LOGIN_PORTAL_BRAND_CSS
        + FORGOT_PASSWORD_LINK_CSS
        + _build_velox_auth_dark_portal_css()
    )


def inject_velox_auth_portal_styles():
    """Estilos auth en un solo bloque por rerun (st.empty evita conflictos DOM/React)."""
    css_slot = st.empty()
    css_slot.markdown(_build_velox_auth_portal_css_bundle(), unsafe_allow_html=True)


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
    "registro_email_confirmado",
    "registro_paso",
    "registro_otp_enviado",
    "registro_otp_verificado",
    "registro_supabase_access",
    "registro_supabase_refresh",
    "registro_completado_email",
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


@st.cache_resource(show_spinner=False)
def _velox_logo_data_uri(path: str = VELOX_LOGO_PATH) -> Optional[str]:
    """Data URI del logo local para incrustarlo en HTML sin depender de st.image."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _sidebar_mascot_src() -> Optional[str]:
    """Isotipo 3D veloX para el anillo circular del sidebar."""
    for path in (VELOX_LOGO_PATH, VELOX_LOGO_SINFONDO_PATH, VELOX_LOGO_BLANCO_PATH):
        src = _velox_logo_data_uri(path)
        if src:
            return src
    return None


def render_velox_brand_header():
    icon_src = _velox_logo_data_uri(VELOX_ICONO_LOGO_PATH) or _velox_logo_data_uri(VELOX_LOGO_PATH)
    icon_html = ""
    if icon_src:
        icon_html = (
            f'<div class="velox-auth-icon-ring">'
            f'<img src="{icon_src}" alt="veloX" class="velox-auth-icon-img" />'
            f"</div>"
        )
    st.markdown(
        f'<div class="velox-auth-brand">{icon_html}'
        f'<p class="velox-auth-wordmark"><span class="velox-auth-wordmark-velo">velo</span>'
        f'<span class="velox-auth-wordmark-x">X</span></p>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="velox-brand-stack">'
        '<p class="velox-tagline velox-tagline--center velox-auth-tagline">'
        "Accede a cursos, plantillas y herramientas "
        "profesionales con un único pago de acceso.</p>"
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
    if st.session_state.get("autenticado") and not st.session_state.get("acceso_pagado") and not _es_staff():
        nombre = st.session_state.get("nombre", "Usuario")
        st.markdown(
            f'<div class="velox-activation-banner">'
            f"<strong>{nombre}</strong>, explora el catálogo veloX. "
            f"Las secciones bloqueadas se desbloquean con el botón "
            f"<em>💎 Adquirir Plan de Cursos</em> en la cabecera o en cada tarjeta."
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
    elif st.session_state.welcome_active_tab == WELCOME_TAB_GATE:
        st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN


def _init_registro_otp_state():
    if "registro_paso" not in st.session_state:
        st.session_state.registro_paso = 1


def _reset_registro_otp_flujo():
    for key in REGISTRO_SESSION_KEYS:
        st.session_state.pop(key, None)
    st.session_state.pop("registro_email", None)
    st.session_state.registro_paso = 1


def _iniciar_registro_otp_flujo():
    _reset_registro_otp_flujo()
    st.session_state.registro_en_progreso = True
    st.session_state.registro_paso = 1


def _init_login_form_state():
    if st.session_state.get("login_recordarme") and st.session_state.get("login_email_saved"):
        if "login_email" not in st.session_state:
            st.session_state.login_email = st.session_state.login_email_saved
    elif "login_recordarme" not in st.session_state:
        st.session_state.login_recordarme = bool(st.session_state.get("login_email_saved"))


def _reset_registro_flujo():
    _reset_registro_otp_flujo()


def _iniciar_registro_flujo():
    _iniciar_registro_otp_flujo()


def _registro_bloquea_acceso_app() -> bool:
    """Evita entrar al hub hasta pulsar OK al final del registro."""
    return bool(st.session_state.get("registro_en_progreso"))


def _marcar_pago_registro_completado(metodo: str):
    st.session_state.registro_pago_ok = True
    st.session_state.registro_metodo_pago_usado = metodo


def _finalizar_registro_y_volver_login():
    email_guardado = (
        st.session_state.get("registro_completado_email")
        or st.session_state.get("registro_email_confirmado")
        or ""
    ).strip().lower()
    _reset_registro_otp_flujo()
    st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
    if email_guardado:
        st.session_state.login_email = email_guardado
    auth_manager.cerrar_sesion(silent=True)
    st.rerun()


def render_portal_id_bar():
    """Barra de contexto del portal (registro / configuración de contraseña)."""
    _init_welcome_tab_state()
    active = st.session_state.welcome_active_tab

    if active == WELCOME_TAB_LOGIN:
        return
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
        paso = st.session_state.get("registro_paso", 1)
        titulos = {
            1: "Registrarse · Paso 1 · Correo Gmail",
            2: "Registrarse · Paso 2 · Código OTP",
            3: "Registrarse · Paso 3 · Contraseña",
            4: "Registrarse · Confirmación",
        }
        st.markdown(
            f'<div class="velox-id-bar velox-id-bar--register">{titulos.get(paso, "Crear cuenta veloX")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="velox-back-login">', unsafe_allow_html=True)
        if st.button("← Volver", key="nav_volver_gate_desde_registro"):
            _reset_registro_otp_flujo()
            st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
            auth_manager.cerrar_sesion(silent=True)
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


def _transicion_login_tras_recuperacion(mensaje: str) -> None:
    """Cierra recuperación y hace rerun limpio hacia login (evita removeChild en React)."""
    email_guardado = (st.session_state.get("recovery_email") or "").strip().lower()
    auth_manager.finalizar_recuperacion_password()
    for key in ("recovery_new_password", "recovery_confirm_password"):
        st.session_state.pop(key, None)
    if mensaje:
        st.session_state["login_flash_success"] = mensaje
    if email_guardado:
        st.session_state["login_email"] = email_guardado
    st.rerun()


def render_tab_recuperar_password():
    """Formulario exclusivo tras enlace de recuperación Supabase."""
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
                _transicion_login_tras_recuperacion(msg)
            else:
                st.error(msg)


def render_tab_gate_portal():
    """Pantalla inicial: solo Iniciar Sesión y Registrarse."""
    st.markdown('<div class="velox-portal-body velox-portal-body--login">', unsafe_allow_html=True)
    st.markdown(
        '<p class="velox-section-caption" style="text-align:center;margin:1rem 0 1.25rem;">'
        "Plataforma de capacitación veloX. Elige cómo deseas continuar."
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="velox-portal-form">', unsafe_allow_html=True)

    if st.button(
        "Iniciar Sesión",
        type="primary",
        key="btn_gate_iniciar_sesion",
        use_container_width=True,
    ):
        st.session_state.welcome_active_tab = WELCOME_TAB_LOGIN
        st.rerun()

    if st.button(
        "Registrarse",
        key="btn_gate_registrarse",
        use_container_width=True,
    ):
        _iniciar_registro_otp_flujo()
        st.session_state.welcome_active_tab = WELCOME_TAB_REGISTER
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_tab_login_portal():
    """Portada: correo/contraseña, Iniciar Sesión y enlace a Registrarme."""
    _init_login_form_state()

    flash_ok = st.session_state.pop("login_flash_success", None)
    if flash_ok:
        st.success(flash_ok)

    denied = st.session_state.pop("oauth_login_denied_msg", None)
    if denied:
        st.error(denied)

    st.markdown('<label class="velox-auth-field-label">CORREO</label>', unsafe_allow_html=True)
    st.text_input(
        "Correo electrónico",
        key="login_email",
        label_visibility="collapsed",
        placeholder="tucorreo@ejemplo.com",
    )
    st.markdown('<label class="velox-auth-field-label">CONTRASEÑA</label>', unsafe_allow_html=True)
    st.text_input(
        "Contraseña",
        type="password",
        key="login_password",
        label_visibility="collapsed",
        placeholder="Ingresa tu contraseña",
    )

    with st.container(key="login_recordarme_row"):
        recordarme_col, forgot_col = st.columns([3, 1], vertical_alignment="center")
        with recordarme_col:
            with st.container(key="login_recordarme_wrap"):
                st.toggle(" ", key="login_recordarme", label_visibility="collapsed")
                st.markdown(
                    '<span class="velox-login-recordarme-label">Recordarme</span>',
                    unsafe_allow_html=True,
                )
        with forgot_col:
            if st.button("¿Olvidaste tu contraseña?", key="btn_olvido_password"):
                _dialog_recuperar_password()

    if st.session_state.get("login_recordarme") and st.session_state.get("login_email"):
        st.session_state.login_email_saved = st.session_state.login_email.strip()

    if st.button(
        "INICIAR SESIÓN",
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

    st.markdown(
        '<p class="velox-auth-register-prompt">¿Aún no tienes cuenta?</p>',
        unsafe_allow_html=True,
    )
    if st.button(
        "Regístrate",
        key="btn_registrarme_portal",
        use_container_width=True,
    ):
        _iniciar_registro_otp_flujo()
        st.session_state.welcome_active_tab = WELCOME_TAB_REGISTER
        st.rerun()


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
            st.session_state.pop("velox_setup_email", None)
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


def _procesar_culqi_si_hay_token(seccion_id: str = ""):
    token = (st.session_state.get("culqi_oauth_token") or "").strip()
    if not token:
        return
    if not st.session_state.get("autenticado"):
        st.warning("Inicia sesión antes de pagar con tarjeta.")
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
        if seccion_id:
            st.session_state.pop("seccion_paywall", None)
        st.success(f"✅ {msg}")
        st.rerun()
    else:
        st.error(f"❌ {msg}")


def _render_culqi_checkout_section(seccion_id: str = "", key_prefix: str = "culqi"):
    sec_info = SECCIONES.get(seccion_id, {})
    seccion_nombre = sec_info.get("nombre", seccion_id) if seccion_id else ""
    if seccion_nombre:
        st.caption(f"Curso / sección: **{seccion_nombre}**")

    st.markdown('<p class="velox-section-title">Pago seguro con tarjeta</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="velox-section-caption">Activación inmediata tras confirmación Culqi.</p>',
        unsafe_allow_html=True,
    )

    if _sincronizar_token_culqi_query():
        _procesar_culqi_si_hay_token(seccion_id)

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

        token_key = f"{key_prefix}_culqi_oauth_token"
        token_actual = (st.session_state.get("culqi_oauth_token") or st.session_state.get(token_key) or "").strip()
        if not token_actual:
            st.text_input(
                "Token Culqi (solo si la confirmación automática falla)",
                placeholder="tok_test_…",
                key=token_key,
                label_visibility="collapsed",
            )
            st.caption(
                "Tras pagar en Culqi, la confirmación se procesa sola. "
                "Si no ocurre, pega aquí el token y pulsa confirmar."
            )
        else:
            st.session_state["culqi_oauth_token"] = token_actual
            st.success(f"Token Culqi recibido: `{token_actual[:16]}…`")

        if st.button(
            "Confirmar pago Culqi y activar acceso",
            type="primary",
            use_container_width=True,
            key=f"{key_prefix}_btn_confirmar_culqi",
            disabled=not (st.session_state.get("culqi_oauth_token") or st.session_state.get(token_key) or "").strip(),
        ):
            if st.session_state.get(token_key):
                st.session_state["culqi_oauth_token"] = st.session_state[token_key]
            _procesar_culqi_si_hay_token(seccion_id)


def _render_yape_plim_section(seccion_id: str = "", key_prefix: str = "yape"):
    email = st.session_state.get("usuario", "")
    nombre = st.session_state.get("nombre", "")
    sec_info = SECCIONES.get(seccion_id, {})
    seccion_nombre = sec_info.get("nombre", seccion_id) if seccion_id else ""

    col_pago, col_form = st.columns([1, 1.12], gap="large")

    with col_pago:
        st.markdown('<div class="velox-qr-panel">', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<p class="velox-section-title">Escanea y paga</p>', unsafe_allow_html=True)
            if os.path.exists(YAPE_QR_PATH):
                st.image(YAPE_QR_PATH, caption="Yape / Plim", use_container_width=True)
            else:
                st.warning(f"No se encontró `{YAPE_QR_PATH}`")
            st.markdown(YAPE_QR_SEGURIDAD_HTML, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_form:
        with st.container(border=True):
            if seccion_nombre:
                st.caption(f"Curso: **{seccion_nombre}**")
            st.text_input("Nombre", value=nombre, disabled=True, key=f"{key_prefix}_nombre_display")

            comprobante = st.file_uploader(
                "Comprobante (JPG)",
                type=["jpg", "jpeg"],
                key=f"{key_prefix}_comprobante_upload",
            )

            celular = st.text_input(
                "Celular de la operación",
                placeholder="999888777",
                max_chars=9,
                key=f"{key_prefix}_celular",
            )

            st.caption(MSG_YAPE_SUBIR_COMPROBANTE)
            puede_enviar = comprobante is not None and bool(str(celular or "").strip())
            if st.button(
                "Enviar comprobante",
                use_container_width=True,
                type="primary",
                key=f"{key_prefix}_btn_enviar",
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
                        st.session_state.pop("seccion_paywall", None)
                        st.success(MSG_YAPE_COMPROBANTE_OK)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                except Exception as e:
                    st.error(f"❌ Error inesperado: {e}")


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


def _render_registro_paso_email_otp():
    st.caption("Ingresa tu correo de Gmail. Te enviaremos un código de verificación de 6 dígitos.")
    st.text_input(
        "Correo Gmail",
        key="registro_email",
        label_visibility="collapsed",
        placeholder="usuario@gmail.com",
    )
    if st.button(
        "Enviar código de verificación",
        type="primary",
        key="btn_registro_enviar_otp",
        use_container_width=True,
    ):
        with _velox_spinner("Enviando código a tu Gmail..."):
            ok, msg = auth_manager.enviar_codigo_registro_otp(
                st.session_state.get("registro_email", "")
            )
        if ok:
            st.session_state.registro_paso = 2
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _render_registro_paso_validar_otp():
    email = (st.session_state.get("registro_email_confirmado") or "").strip().lower()
    if not email:
        st.session_state.registro_paso = 1
        st.rerun()
    st.caption(f"Código enviado a **{email}**. Revisa tu bandeja de Gmail (y spam).")
    st.text_input(
        "Código OTP",
        key="registro_otp_codigo",
        label_visibility="collapsed",
        placeholder="Código de 6 dígitos",
        max_chars=6,
    )
    col_validar, col_reenviar = st.columns(2)
    with col_validar:
        if st.button(
            "Validar código",
            type="primary",
            key="btn_registro_validar_otp",
            use_container_width=True,
        ):
            with _velox_spinner("Verificando código..."):
                ok, msg = auth_manager.verificar_codigo_registro_otp(
                    email,
                    st.session_state.get("registro_otp_codigo", ""),
                )
            if ok:
                st.session_state.registro_paso = 3
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with col_reenviar:
        if st.button("Reenviar código", key="btn_registro_reenviar_otp", use_container_width=True):
            with _velox_spinner("Reenviando código..."):
                ok, msg = auth_manager.enviar_codigo_registro_otp(email)
            if ok:
                st.success(msg)
            else:
                st.error(msg)


def _render_registro_paso_password_otp():
    email = (st.session_state.get("registro_email_confirmado") or "").strip().lower()
    if not email:
        st.session_state.registro_paso = 1
        st.rerun()
    st.caption(f"Cuenta verificada: **{email}**. Define tu contraseña de acceso a veloX.")
    st.text_input(
        "Contraseña",
        type="password",
        key="registro_password_nueva",
        label_visibility="collapsed",
        placeholder="Contraseña (mín. 6 caracteres)",
    )
    st.text_input(
        "Confirmar contraseña",
        type="password",
        key="registro_password_confirmar",
        label_visibility="collapsed",
        placeholder="Confirmar contraseña",
    )
    if st.button(
        "Guardar contraseña",
        type="primary",
        key="btn_registro_guardar_password_otp",
        use_container_width=True,
    ):
        with _velox_spinner("Creando tu cuenta..."):
            ok, msg = auth_manager.completar_registro_otp_password(
                email,
                st.session_state.get("registro_password_nueva", ""),
                st.session_state.get("registro_password_confirmar", ""),
            )
        if ok:
            st.session_state.registro_paso = 4
            st.session_state.registro_completado_email = email
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _render_registro_confirmacion_otp():
    email = (
        st.session_state.get("registro_completado_email")
        or st.session_state.get("registro_email_confirmado")
        or ""
    ).strip().lower()
    st.markdown(
        f"""
        <div class="velox-register-success">
            <div class="velox-register-success__icon">✅</div>
            <div class="velox-register-success__title">¡Cuenta creada!</div>
            <p class="velox-register-success__text">
                Tu cuenta veloX con <strong>{email}</strong> fue creada exitosamente.
                Inicia sesión con tu correo y la contraseña que acabas de definir.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        "Ir a Iniciar Sesión",
        type="primary",
        key="btn_registro_ir_login",
        use_container_width=True,
    ):
        _finalizar_registro_y_volver_login()


def render_tab_registro_velox():
    """Registro por OTP: Gmail → código → contraseña → confirmación."""
    _init_registro_otp_state()
    st.session_state["registro_en_progreso"] = True

    paso = st.session_state.get("registro_paso", 1)
    if paso <= 1 and not st.session_state.get("registro_otp_enviado"):
        paso = 1
    elif paso <= 2 and st.session_state.get("registro_otp_enviado") and not st.session_state.get("registro_otp_verificado"):
        paso = max(paso, 2)
    elif st.session_state.get("registro_otp_verificado") and paso < 3:
        paso = 3
    st.session_state.registro_paso = paso

    _open_portal_scroll()
    st.markdown('<div class="velox-portal-form">', unsafe_allow_html=True)

    if paso == 1:
        _render_registro_paso_email_otp()
    elif paso == 2:
        _render_registro_paso_validar_otp()
    elif paso == 3:
        _render_registro_paso_password_otp()
    else:
        _render_registro_confirmacion_otp()

    st.markdown("</div>", unsafe_allow_html=True)
    _close_portal_scroll()


def render_pantalla_configurar_password():
    """Pantalla obligatoria tras OAuth si la cuenta aún no tiene contraseña veloX."""
    _render_auth_portal_prefix()
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        render_velox_brand_header()
        with st.container(border=True):
            render_tab_setup_password_velox()
    render_footer()


def _render_auth_portal_prefix():
    """CSS y marcador del portal auth al inicio de cada rerun (antes del árbol de widgets)."""
    inject_velox_auth_portal_styles()
    _render_velox_auth_portal_marker()


def render_pantalla_solo_recuperacion():
    """Pantalla exclusiva de restablecimiento; nunca muestra login/registro."""
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        render_velox_brand_header()
        with st.container(border=True):
            render_tab_recuperar_password()
    render_footer()


def _render_velox_auth_portal_marker():
    """Marcador oculto para activar estilos del portal en todas las vistas auth."""
    st.markdown(
        '<div class="velox-id-bar velox-id-bar--marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def render_welcome_gateway():
    """Pantalla premium centrada: login directo y registro por pasos."""
    _init_welcome_tab_state()

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        render_velox_brand_header()
        render_activation_banner()

        with st.container(border=True):
            render_portal_id_bar()

            active = st.session_state.welcome_active_tab
            if active == WELCOME_TAB_LOGIN:
                render_tab_login_portal()
            elif active == WELCOME_TAB_SETUP_PASSWORD:
                render_tab_setup_password_velox()
            else:
                render_tab_registro_velox()


def login_screen():
    render_welcome_gateway()
    render_footer()


# ==================== FOOTER LEGAL Y PÁGINAS INTERNAS ====================
LEGAL_DOCS_DIR = "data"


@st.cache_data(show_spinner=False, ttl=300)
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
        <div class='velox-auth-footer' style='text-align: center; padding: 1rem 0; font-size: 0.85rem; color: #64748b;'>
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
SHOW_CHATBOT = False

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


def _chatbot_habilitado() -> bool:
    """Interruptor global del asistente flotante. Prioriza st.secrets['app']['show_chatbot'] si existe."""
    try:
        secret_val = st.secrets.get("app", {}).get("show_chatbot")
        if secret_val is not None:
            return bool(secret_val)
    except Exception:
        pass
    return SHOW_CHATBOT


def _chatbot_visible_en_modulo_actual() -> bool:
    if not _chatbot_habilitado():
        return False
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
    if not _chatbot_habilitado():
        return
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
    if not _chatbot_habilitado() or not _chatbot_visible_en_modulo_actual():
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


def _es_master_admin_comprobantes() -> bool:
    """Panel de comprobantes: exclusivo para el correo Master principal."""
    email = (st.session_state.get("usuario") or "").strip().lower()
    return bool(email) and email == AuthManager.MASTER_EMAIL.lower()


def _es_master() -> bool:
    rol = AuthManager.normalizar_rol(st.session_state.get("rol"))
    if AuthManager.es_rol_master(rol):
        return True
    email = (st.session_state.get("usuario") or "").strip().lower()
    return bool(email) and email == AuthManager.MASTER_EMAIL.lower()


def _sincronizar_rol_master_en_sesion() -> None:
    """Alinea rol Master en memoria sin consultar Supabase en cada vista."""
    if not st.session_state.get("autenticado"):
        return
    email = (st.session_state.get("usuario") or "").strip().lower()
    if email == AuthManager.MASTER_EMAIL.lower():
        st.session_state["rol"] = "master"


def _rerun_velox(scope_fragment: bool = False) -> None:
    if scope_fragment:
        try:
            st.rerun(scope="fragment")
            return
        except TypeError:
            pass
    st.rerun()


def _ensure_sesion_perfil_local() -> None:
    """Evita re-hidratar perfil desde BD si la sesión ya trae rol y permisos."""
    if st.session_state.get("autenticado") and not st.session_state.get("_sesion_perfil_cargado"):
        st.session_state["_sesion_perfil_cargado"] = True


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
    """Branding VELOX en la parte superior del sidebar."""
    st.markdown(
        '<div class="sidebar-brand">'
        '<p class="sidebar-brand-title">VELO<span class="sidebar-brand-x">X</span></p>'
        '<p class="sidebar-brand-subtitle">Asistente Inteligente</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def _render_sidebar_value_card() -> None:
    """Tarjeta informativa inferior del sidebar."""
    st.markdown(
        '<div class="sidebar-value-card">'
        '<div class="sidebar-value-card__icon">🎓</div>'
        '<p class="sidebar-value-card__text">'
        "Aprende, organiza y crece cada día. "
        "<strong>Tu éxito comienza con conocimiento.</strong>"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )


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
        return [_resolver_seccion_id(s) for s in secciones if _resolver_seccion_id(s) in SECCIONES]
    raw = cached_obtener_secciones_usuario(
        st.session_state["usuario"],
        data_cache_version=_velox_data_cache_version(),
    )
    resueltas = []
    for s in raw:
        canon = _resolver_seccion_id(s)
        if canon in SECCIONES and canon not in resueltas:
            resueltas.append(canon)
    return resueltas


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
        total = int(conteos.get(seccion_id, 0))
        for legacy_id, canon_id in SECCION_LEGACY_IDS.items():
            if canon_id == seccion_id:
                total += int(conteos.get(legacy_id, 0))
        return total
    except Exception:
        return 0


@st.cache_resource(show_spinner=False)
def _seccion_banner_data_uri(seccion_id: str) -> Optional[str]:
    """Data URI del banner SVG de una sección para fondos de tarjeta."""
    path = SECCION_BANNER_PATHS.get(seccion_id, "")
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _html_tarjeta_catalogo_seccion(
    seccion_id: str,
    sec_info: dict,
    nombre_limpio: str,
    num_docs: int,
    *,
    tiene_acceso: bool,
) -> str:
    """HTML de tarjeta del catálogo con banner SVG y overlay de legibilidad."""
    banner_uri = _seccion_banner_data_uri(seccion_id)
    banner_style = f"background-image: url('{banner_uri}');" if banner_uri else ""
    descripcion = html_module.escape(sec_info.get("descripcion") or "")
    icono = html_module.escape(sec_info.get("icono") or "")
    nombre_seguro = html_module.escape(nombre_limpio)
    estado = "active" if tiene_acceso else "locked"

    if tiene_acceso:
        titulo_html = f'<div class="velox-section-card__title">{icono} {nombre_seguro}</div>'
        doc_label = "documento disponible" if num_docs == 1 else "documentos disponibles"
        meta = f"✅ {num_docs} {doc_label}"
        watermark = ""
    else:
        titulo_html = (
            f'<div class="velox-section-card__title">🔒 {icono} {nombre_seguro}</div>'
        )
        meta = f"Previsualización · {num_docs} recursos en catálogo"
        watermark = '<div class="velox-section-card__watermark">PREVIEW</div>'

    return (
        f'<div class="velox-section-card velox-section-card--{estado} velox-section-card--banner" '
        f'style="{banner_style}">'
        f'<div class="velox-section-card__overlay"></div>'
        f"{watermark}"
        f'<div class="velox-section-card__inner">'
        f'<div class="velox-section-card__body">{titulo_html}'
        f'<div class="velox-section-card__desc">{descripcion}</div></div>'
        f'<div class="velox-section-card__meta">{meta}</div></div></div>'
    )


def _nombre_seccion_sin_icono(seccion_info: dict) -> str:
    """Título tipográfico limpio sin emoji/icono del catálogo."""
    nombre = (seccion_info.get("nombre") or "").strip()
    icono = (seccion_info.get("icono") or "").strip()
    if icono and nombre.startswith(icono):
        return nombre[len(icono):].strip()
    return nombre


def _mis_docs_busqueda_key(seccion_id: str) -> str:
    return f"buscador_mis_docs_{seccion_id}"


def _inicializar_selector_seccion_documentos(opciones_ids: list, seccion_preseleccionada_norm: Optional[str] = None) -> None:
    """Sincroniza session_state del selectbox con IDs de sección (reactivo en cada rerun)."""
    widget_key = "selector_seccion_documentos"
    if not opciones_ids:
        return
    if seccion_preseleccionada_norm and seccion_preseleccionada_norm in opciones_ids:
        st.session_state[widget_key] = seccion_preseleccionada_norm
    elif st.session_state.get(widget_key) not in opciones_ids:
        st.session_state[widget_key] = opciones_ids[0]


def _sincronizar_cambio_seccion_mis_docs(seccion_id: str) -> None:
    """Al cambiar de sección, reinicia paginación para mostrar datos de la nueva sección."""
    prev_key = "_mis_docs_seccion_anterior"
    if st.session_state.get(prev_key) != seccion_id:
        st.session_state[prev_key] = seccion_id
        st.session_state[_docs_pagina_session_key(seccion_id, prefijo="pub")] = 1


def _render_banner_seccion_detalle(seccion_info: dict) -> None:
    """Banner centrado del detalle de sección (Mis Documentos e Inicio interno)."""
    inject_section_detail_banner_css()
    titulo = html_module.escape(_nombre_seccion_sin_icono(seccion_info).upper())
    descripcion = html_module.escape(seccion_info.get("descripcion") or "")
    st.markdown(
        f'<div class="velox-section-detail-banner">'
        f'<h2 class="velox-section-detail-banner__title">{titulo}</h2>'
        f'<p class="velox-section-detail-banner__desc">{descripcion}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


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


def _url_whatsapp_con_mensaje(mensaje: str) -> str:
    from urllib.parse import quote

    try:
        app_cfg = st.secrets.get("app", {})
        url_directa = str(app_cfg.get("whatsapp_admin_url", "")).strip()
        numero = str(app_cfg.get("whatsapp_admin", "")).strip()
    except Exception:
        url_directa = ""
        numero = ""

    if url_directa:
        if "wa.me/" in url_directa and "text=" not in url_directa:
            separador = "&" if "?" in url_directa else "?"
            return f"{url_directa}{separador}text={quote(mensaje)}"
        return url_directa

    if numero and numero.upper() != "TU_NUMERO":
        numero_limpio = numero.replace("+", "").replace(" ", "").replace("-", "")
        return f"https://wa.me/{numero_limpio}?text={quote(mensaje)}"

    return WHATSAPP_ADMIN_LINK


def _abrir_dialog_plan_cursos_desde_catalogo(_seccion_id: str = ""):
    """Abre el modal centralizado de planes (flujo unificado desde tarjetas del catálogo)."""
    _ = _seccion_id
    st.session_state["dialog_plan_cursos"] = True


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

    /* Tarjetas del catálogo: separación lateral e inferior + columnas iguales */
    .velox-section-grid {
        margin-bottom: 0.65rem !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        width: 100% !important;
    }
    .velox-section-grid .velox-section-card {
        margin-left: 0 !important;
        margin-right: 0 !important;
        margin-bottom: 0.65rem !important;
        min-height: 220px !important;
        height: 100% !important;
    }

    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) {
        gap: 1rem !important;
        align-items: stretch !important;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) > div[data-testid="column"],
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) > div[data-testid="stColumn"] {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
    }
    [data-testid="stMain"] [data-testid="stColumn"]:has(.velox-section-grid) > div:has(.stButton) {
        margin-top: auto !important;
        flex: 0 0 auto !important;
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

    /* 1. Catálogo: botones pill con degradado azul-turquesa */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button,
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button[kind="primary"],
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button[kind="secondary"],
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] .stButton > button {
        background: linear-gradient(90deg, #1A56DB 0%, #06B6D4 100%) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(26, 86, 219, 0.28) !important;
        transition: transform 0.18s ease, box-shadow 0.22s ease, filter 0.22s ease !important;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button:hover,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] .stButton > button:hover {
        filter: brightness(1.06) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(6, 182, 212, 0.32) !important;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button *,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] .stButton > button * {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    /* Refuerzo: anula stMarkdownContainer p dentro de botones del catálogo */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) button [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) button [data-testid="stMarkdownContainer"] span,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] button [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] button [data-testid="stMarkdownContainer"] span {
        color: #FFFFFF !important;
        font-weight: 600 !important;
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
    for i, (seccion_id, sec_info) in enumerate(_secciones_catalogo_visibles()):
        tiene_acceso = seccion_id in autorizadas
        num_docs = _contar_documentos_seccion(seccion_id)
        nombre_limpio = _nombre_seccion_sin_icono(sec_info)

        with cols[i % 3]:
            st.markdown('<div class="velox-section-grid">', unsafe_allow_html=True)

            if tiene_acceso:
                st.markdown(_html_tarjeta_catalogo_seccion(
                    seccion_id, sec_info, nombre_limpio, num_docs, tiene_acceso=True,
                ), unsafe_allow_html=True)
                st.button(
                    "Ingresar",
                    key=f"{key_prefix}_go_{seccion_id}",
                    use_container_width=True,
                    type="primary",
                    on_click=activar_seccion_inicio,
                    kwargs={"seccion_id": seccion_id},
                )
            else:
                st.markdown(_html_tarjeta_catalogo_seccion(
                    seccion_id, sec_info, nombre_limpio, num_docs, tiene_acceso=False,
                ), unsafe_allow_html=True)
                st.button(
                    "Adquirir Curso",
                    key=f"{key_prefix}_lock_{seccion_id}",
                    use_container_width=True,
                    type="secondary",
                    on_click=_abrir_dialog_plan_cursos_desde_catalogo,
                    kwargs={"_seccion_id": seccion_id},
                )

            st.markdown("</div>", unsafe_allow_html=True)


def _menu_sidebar_items():
    rol = st.session_state.get("rol", "usuario")
    if _es_master():
        items = auth_manager.filtrar_menu_staff(
            MENU_SIDEBAR_MASTER,
            rol,
            st.session_state.get("modulos_permitidos"),
        )
    elif _es_admin():
        items = auth_manager.filtrar_menu_staff(
            MENU_SIDEBAR_MASTER,
            rol,
            st.session_state.get("modulos_permitidos"),
        )
        if not any(valor == "👤 Mi Perfil" for _, _, valor in items):
            items = list(items) + [MENU_SIDEBAR_PERFIL]
    else:
        return MENU_SIDEBAR_USER

    if not _es_master_admin_comprobantes():
        items = [item for item in items if item[2] != AuthManager.MODULO_COBRANZAS]
    return items


_MENU_KEY_SLUGS = {
    AuthManager.MODULO_INICIO: "inicio",
    AuthManager.MODULO_DOCUMENTOS: "documentos",
    AuthManager.MODULO_GESTION_USUARIOS: "gestion_usuarios",
    AuthManager.MODULO_COBRANZAS: "cobranzas",
    AuthManager.MODULO_CONSULTAS: "consultas",
    AuthManager.MODULO_CONFIGURACION: "configuracion",
    "👤 Mi Perfil": "mi_perfil",
}


def _sidebar_menu_button_key(valor: str) -> str:
    slug = _MENU_KEY_SLUGS.get(valor)
    if not slug:
        slug = re.sub(r"[^\w]+", "_", (valor or "")).strip("_").lower() or "item"
    return f"main_menu_{slug}"


def _etiqueta_menu_sidebar(valor: str) -> str:
    return valor


def _init_sidebar_counts_si_falta() -> None:
    if not st.session_state.get("autenticado"):
        return
    usuario = (st.session_state.get("usuario") or "").strip().lower()
    if not usuario:
        return
    cache_v = _velox_data_cache_version()
    en_consultas = st.session_state.get("menu_principal") == AuthManager.MODULO_CONSULTAS
    if (
        "pending_cobranzas_count" not in st.session_state
        or st.session_state.get("_sidebar_counts_user") != usuario
    ):
        _refresh_sidebar_counts(force=True)
    else:
        if en_consultas:
            st.session_state["unread_consultas_count"] = 0
        elif _es_staff() and _puede_modulo(AuthManager.MODULO_CONSULTAS):
            st.session_state["unread_consultas_count"] = cached_contar_consultas_soporte_master(
                data_cache_version=cache_v
            )
        else:
            st.session_state["unread_consultas_count"] = cached_contar_consultas_no_leidas(
                usuario,
                data_cache_version=cache_v,
            )
        st.session_state["unread_count"] = st.session_state["unread_consultas_count"]


def _refresh_sidebar_counts(force: bool = False) -> None:
    cache_v = _velox_data_cache_version()
    usuario = (st.session_state.get("usuario") or "").strip().lower()
    if _es_master_admin_comprobantes():
        st.session_state["pending_cobranzas_count"] = cached_contar_pagos_pendientes(
            data_cache_version=cache_v
        )
    else:
        st.session_state["pending_cobranzas_count"] = 0

    if _es_staff() and _puede_modulo(AuthManager.MODULO_CONSULTAS):
        st.session_state["unread_consultas_count"] = cached_contar_consultas_soporte_master(
            data_cache_version=cache_v
        )
    else:
        st.session_state["unread_consultas_count"] = cached_contar_consultas_no_leidas(
            usuario,
            data_cache_version=cache_v,
        )
    st.session_state["unread_count"] = st.session_state["unread_consultas_count"]
    st.session_state["_sidebar_counts_user"] = usuario


def _decrementar_pending_cobranzas() -> None:
    actual = int(st.session_state.get("pending_cobranzas_count") or 0)
    st.session_state["pending_cobranzas_count"] = max(0, actual - 1)


def _decrementar_unread_consultas() -> None:
    actual = int(st.session_state.get("unread_consultas_count") or 0)
    st.session_state["unread_consultas_count"] = max(0, actual - 1)
    st.session_state["unread_count"] = st.session_state["unread_consultas_count"]


def _limpiar_notificaciones_consultas_usuario(email: str) -> None:
    message_manager.marcar_consultas_leidas(email)
    _invalidar_cache_consultas()
    st.session_state["unread_consultas_count"] = 0
    st.session_state["unread_count"] = 0


def _limpiar_notificaciones_consultas_master() -> None:
    message_manager.marcar_consultas_leidas_master()
    _invalidar_cache_consultas()
    st.session_state["unread_consultas_count"] = 0
    st.session_state["unread_count"] = 0


def _marcar_consultas_leidas_al_entrar() -> None:
    """Marca lectura en BD antes del sidebar para que el badge desaparezca al instante."""
    if st.session_state.get("menu_principal") != AuthManager.MODULO_CONSULTAS:
        return
    if not st.session_state.get("autenticado"):
        return
    if _es_staff() and _puede_modulo(AuthManager.MODULO_CONSULTAS):
        _limpiar_notificaciones_consultas_master()
    else:
        _limpiar_notificaciones_consultas_usuario(
            st.session_state.get("usuario", "")
        )


def _render_sidebar_menu_badges(badge_map: Dict[str, int]) -> None:
    rules = []
    for key, count in badge_map.items():
        if count <= 0:
            continue
        badge_text = str(count) if count < 100 else "99+"
        rules.append(
            f"""
        [data-testid="stSidebar"] div.st-key-{key} {{
            position: relative !important;
            overflow: visible !important;
        }}
        [data-testid="stSidebar"] div.st-key-{key}::after {{
            content: "{badge_text}";
            position: absolute;
            top: -6px;
            right: -6px;
            z-index: 10;
            background-color: #F59E0B;
            color: #0F172A;
            font-weight: 800;
            font-size: 11px;
            border-radius: 9999px;
            padding: 2px 7px;
            min-width: 20px;
            height: 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 3px solid #051329;
            box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.25);
            line-height: 1;
            pointer-events: none;
            box-sizing: border-box;
        }}
        """
        )
    if rules:
        st.markdown(f"<style>{''.join(rules)}</style>", unsafe_allow_html=True)


def _render_sidebar_menu_botones(menu_items, menu_principal: str) -> None:
    pending_cobranzas = int(st.session_state.get("pending_cobranzas_count") or 0)
    unread_consultas = int(st.session_state.get("unread_consultas_count") or 0)
    badge_map: Dict[str, int] = {}

    with st.container(key="sidebar_menu_panel"):
        for _etiqueta, _icono, valor in menu_items:
            label = _etiqueta_menu_sidebar(valor)
            btn_key = _sidebar_menu_button_key(valor)
            if valor == AuthManager.MODULO_COBRANZAS and pending_cobranzas > 0:
                badge_map[btn_key] = pending_cobranzas
            if valor == AuthManager.MODULO_CONSULTAS and unread_consultas > 0:
                badge_map[btn_key] = unread_consultas

            activo = valor == menu_principal
            if st.button(
                label,
                key=btn_key,
                use_container_width=True,
                type="primary" if activo else "secondary",
            ):
                if valor == AuthManager.MODULO_CONSULTAS:
                    if _es_staff() and _puede_modulo(AuthManager.MODULO_CONSULTAS):
                        _limpiar_notificaciones_consultas_master()
                    else:
                        _limpiar_notificaciones_consultas_usuario(
                            st.session_state.get("usuario", "")
                        )
                if valor != menu_principal:
                    st.session_state["menu_principal"] = valor
                    if valor == AuthManager.MODULO_INICIO:
                        st.session_state.seccion_activa = "inicio"
                    st.rerun()

    _render_sidebar_menu_badges(badge_map)


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

def volver_al_inicio():
    st.session_state.seccion_activa = "inicio"

def _formatear_fecha_notif(fecha_raw):
    if not fecha_raw:
        return "Fecha desconocida"
    try:
        from message_manager import MessageManager

        return MessageManager.formatear_fecha_lima(fecha_raw)
    except Exception:
        try:
            texto = str(fecha_raw).replace("Z", "+00:00")
            dt = datetime.fromisoformat(texto)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(ZoneInfo("America/Lima")).strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return str(fecha_raw)[:16].replace("T", " ")


def _formatear_fecha_consulta(msg_or_fecha) -> str:
    if isinstance(msg_or_fecha, dict):
        fecha_raw = (
            msg_or_fecha.get("fecha")
            or msg_or_fecha.get("created_at")
            or msg_or_fecha.get("fecha_respuesta")
        )
    else:
        fecha_raw = msg_or_fecha
    return _formatear_fecha_notif(fecha_raw) if fecha_raw else "Sin fecha"

def _formatear_cursos_comprobante(cursos_raw) -> str:
    """Etiquetas legibles para cursos_solicitados (claves Supabase)."""
    if cursos_raw is None:
        return "—"
    if isinstance(cursos_raw, str):
        texto = cursos_raw.strip()
        if not texto:
            return "—"
        try:
            cursos_raw = json.loads(texto)
        except json.JSONDecodeError:
            return CURSOS_PLAN_CATALOGO.get(texto.lower(), texto)
    if not isinstance(cursos_raw, list):
        return str(cursos_raw)
    if not cursos_raw:
        return "—"
    nombres = []
    for curso in cursos_raw:
        clave = str(curso or "").strip().lower()
        if not clave:
            continue
        nombres.append(CURSOS_PLAN_CATALOGO.get(clave, clave.replace("_", " ").title()))
    return ", ".join(nombres) if nombres else "—"


COMPROBANTES_ADMIN_CSS = """
<style>
    .velox-comprobante-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(26, 54, 93, 0.06);
    }
    .velox-comprobante-card__meta {
        color: #475569;
        font-size: 0.88rem;
        line-height: 1.55;
    }
    .st-key-btn_aprobar_comprobante .stButton > button {
        background: #16a34a !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
    }
    .st-key-btn_aprobar_comprobante .stButton > button:hover {
        background: #15803d !important;
        color: #FFFFFF !important;
    }
    .st-key-btn_rechazar_comprobante .stButton > button {
        background: #dc2626 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
    }
    .st-key-btn_rechazar_comprobante .stButton > button:hover {
        background: #b91c1c !important;
        color: #FFFFFF !important;
    }
</style>
"""


def render_gestion_comprobantes_admin():
    """Panel Master (correo exclusivo): aprobar o rechazar comprobantes pendientes."""
    if not _es_master_admin_comprobantes():
        st.error("Acceso denegado. Este panel es exclusivo del administrador Master.")
        return

    st.markdown(COMPROBANTES_ADMIN_CSS, unsafe_allow_html=True)
    st.header("💳 Gestión de Pagos / Comprobantes")
    st.caption(
        "Revisa solicitudes Yape/Plim pendientes, valida comprobantes y activa cursos en las cuentas de los alumnos."
    )
    _fragment_panel_comprobantes_pendientes()


@st.fragment
def _fragment_panel_comprobantes_pendientes():
    cache_v = _velox_data_cache_version()
    if st.session_state.get("pago_flash"):
        tipo, texto = st.session_state.pop("pago_flash")
        if tipo == "success":
            st.success(texto)
        elif tipo == "error":
            st.error(texto)

    pagos = cached_listar_pagos_pendientes(data_cache_version=cache_v)
    st.markdown(f"### ⏳ Solicitudes pendientes ({len(pagos)})")

    if not pagos:
        st.info("No hay comprobantes pendientes de revisión.")
        return

    df = pd.DataFrame(
        [
            {
                "Fecha": _formatear_fecha_notif(p.get("fecha")),
                "Email": p.get("email"),
                "Plan": p.get("plan_seleccionado") or "—",
                "Cursos": _formatear_cursos_comprobante(p.get("cursos_solicitados")),
                "Monto": f"S/ {float(p.get('monto', MONTO_SOLES)):.2f}",
                "Comprobante": "✅" if p.get("comprobante_url") else "—",
            }
            for p in pagos
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.markdown("---")

    for pago in pagos:
        pago_id = pago["id"]
        url_comprobante = (pago.get("comprobante_url") or "").strip()
        cursos_txt = _formatear_cursos_comprobante(pago.get("cursos_solicitados"))
        plan_txt = pago.get("plan_seleccionado") or "—"

        with st.container(border=True):
            st.markdown(
                f"""
                <div class="velox-comprobante-card__meta">
                <strong>{pago.get('nombre', 'Sin nombre')}</strong> · <code>{pago.get('email')}</code><br>
                <strong>Fecha:</strong> {_formatear_fecha_notif(pago.get('fecha'))} ·
                <strong>Plan:</strong> {plan_txt} ·
                <strong>Cursos:</strong> {cursos_txt} ·
                <strong>Monto:</strong> S/ {float(pago.get('monto', MONTO_SOLES)):.2f}
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_prev, col_sp = st.columns([1, 2])
            with col_prev:
                if url_comprobante:
                    es_imagen = any(
                        url_comprobante.lower().split("?")[0].endswith(ext)
                        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
                    )
                    if es_imagen:
                        st.image(url_comprobante, caption="Vista previa", width=280)
                    st.link_button(
                        "🔍 Ver comprobante",
                        url_comprobante,
                        use_container_width=True,
                    )
                else:
                    st.caption("Sin archivo adjunto.")

            with col_sp:
                col_ok, col_no = st.columns(2)
                with col_ok:
                    obs_aprobar_key = f"obs_aprobacion_{pago_id}"
                    st.text_input(
                        "Observación de aprobación (opcional)",
                        key=obs_aprobar_key,
                        placeholder="Ej. acceso activado correctamente",
                        label_visibility="collapsed",
                    )
                    st.markdown('<div class="st-key-btn_aprobar_comprobante">', unsafe_allow_html=True)
                    if st.button(
                        "Aprobar Acceso",
                        key=f"aprobar_comprobante_{pago_id}",
                        use_container_width=True,
                        disabled=st.session_state.get("pago_procesando") == pago_id,
                    ):
                        st.session_state["pago_procesando"] = pago_id
                        observacion = st.session_state.get(obs_aprobar_key, "")
                        ok, msg = payment_manager.aprobar_pago(
                            pago_id,
                            st.session_state["usuario"],
                            observacion=observacion,
                        )
                        st.session_state.pop("pago_procesando", None)
                        if ok:
                            st.session_state["pago_flash"] = (
                                "success",
                                "Acceso activado correctamente",
                            )
                            _invalidar_cache_datos()
                            _decrementar_pending_cobranzas()
                        else:
                            st.session_state["pago_flash"] = ("error", msg)
                        _rerun_velox(scope_fragment=False)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col_no:
                    motivo_key = f"motivo_comprobante_{pago_id}"
                    st.text_input(
                        "Motivo de rechazo (opcional)",
                        key=motivo_key,
                        placeholder="Ej. monto incorrecto o comprobante ilegible",
                        label_visibility="collapsed",
                    )
                    st.markdown('<div class="st-key-btn_rechazar_comprobante">', unsafe_allow_html=True)
                    if st.button(
                        "Rechazar",
                        key=f"rechazar_comprobante_{pago_id}",
                        use_container_width=True,
                        disabled=st.session_state.get("pago_procesando") == pago_id,
                    ):
                        st.session_state["pago_procesando"] = pago_id
                        motivo = st.session_state.get(motivo_key, "")
                        ok, msg = payment_manager.rechazar_pago(
                            pago_id,
                            st.session_state["usuario"],
                            motivo or "Rechazado por el administrador",
                        )
                        st.session_state.pop("pago_procesando", None)
                        st.session_state["pago_flash"] = ("success" if ok else "error", msg)
                        if ok:
                            _invalidar_cache_datos()
                            _decrementar_pending_cobranzas()
                        _rerun_velox(scope_fragment=False)
                    st.markdown("</div>", unsafe_allow_html=True)


def render_gestion_cobranzas_master():
    """Alias retrocompatible → panel exclusivo Master."""
    render_gestion_comprobantes_admin()


def _nombre_seccion_consulta(msg: dict) -> str:
    seccion = (msg.get("seccion") or "").strip().lower()
    if seccion == "cobranzas":
        return "Cobranzas / Pagos"
    if seccion in ("administracion", "general", ""):
        return "Administración veloX"
    return SECCIONES.get(seccion, {}).get("nombre", seccion.capitalize())


def _render_tarjeta_consulta(msg: dict, mostrar_email: bool = False) -> None:
    asunto = MessageManager._texto_asunto(msg)
    fecha_str = _formatear_fecha_consulta(msg)
    estado_raw = (msg.get("estado") or "").strip()
    respuesta = (msg.get("respuesta") or "").strip()
    asunto_upper = asunto.upper()
    es_cobranzas = (msg.get("seccion") or "").strip().lower() == "cobranzas"
    es_pendiente = not respuesta and estado_raw.lower() not in (
        "atendido",
        "observado",
        "respondida",
        "respondido",
    )
    if es_cobranzas and "RECHAZADO" in asunto_upper:
        badge = "❌ Solicitud Rechazada"
        badge_style = "background:#fee2e2;color:#991b1b;"
    elif es_cobranzas and "APROBADO" in asunto_upper:
        badge = "✅ Solicitud Aprobada"
        badge_style = "background:#dcfce7;color:#166534;"
    elif es_pendiente:
        badge = "⏳ Pendiente"
        badge_style = "background:#fff3cd;color:#856404;"
    elif estado_raw.lower() == "observado":
        badge = "⚠️ Observado"
        badge_style = "background:#fef3c7;color:#92400e;"
    else:
        badge = "✅ Atendido"
        badge_style = "background:#dcfce7;color:#166534;"

    email_line = ""
    if mostrar_email:
        email_line = f" · `{MessageManager._email_de_consulta(msg)}`"

    borde_tarjeta = (
        "border-left:5px solid #F59E0B;background:#FFFBEB;padding:10px 12px;border-radius:10px;margin-bottom:8px;"
        if es_cobranzas
        else ""
    )
    if es_cobranzas:
        st.markdown(
            f'<div style="{borde_tarjeta}">'
            f'<div style="font-size:0.82rem;font-weight:700;color:#B45309;margin-bottom:6px;">'
            f"💳 Notificación de Cobranzas / Pagos</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.75rem;margin-bottom:0.35rem;">
            <div><strong>{asunto}</strong><br>
            <small style="color:#64748b;">📅 {fecha_str}{email_line}</small></div>
            <span style="{badge_style}padding:4px 10px;border-radius:12px;font-size:0.78rem;white-space:nowrap;">{badge}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="background:#f8fafc;border-radius:8px;padding:10px 12px;'
        f'border-left:4px solid #2B6CB0;margin:6px 0 8px 0;">{msg.get("mensaje", "")}</div>',
        unsafe_allow_html=True,
    )
    if respuesta:
        etiqueta_resp = (
            "**Detalle del administrador:**"
            if es_cobranzas
            else "**Respuesta:**"
        )
        st.markdown(f"{etiqueta_resp} {respuesta}")
    elif es_pendiente:
        st.info("**Respuesta:** Pendiente de respuesta por el administrador.")

    if es_cobranzas:
        st.markdown("</div>", unsafe_allow_html=True)


@st.fragment
def _fragment_consultas_staff_pendientes():
    cache_v = _velox_data_cache_version()
    pendientes = cached_obtener_consultas_pendientes_master(data_cache_version=cache_v)
    st.markdown(f"### ⏳ Consultas pendientes ({len(pendientes)})")

    if not pendientes:
        st.info("No hay consultas pendientes por responder.")
        return

    for msg in pendientes:
        seccion_nombre = _nombre_seccion_consulta(msg)
        fecha_str = _formatear_fecha_consulta(msg)
        with st.container(border=True):
            col_info, col_badge = st.columns([4, 1])
            with col_info:
                st.markdown(
                    f"**👤 {msg.get('nombre_usuario', 'Usuario')}** · "
                    f"`{MessageManager._email_de_consulta(msg)}`  \n"
                    f"**📂 {seccion_nombre}** · **📅** {fecha_str}"
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
                        _invalidar_cache_datos()
                        _decrementar_unread_consultas()
                        st.success("✅ Respuesta enviada correctamente")
                        _rerun_velox(scope_fragment=True)
                    else:
                        st.error("❌ No se pudo guardar la respuesta. Intenta de nuevo.")
                else:
                    st.warning("Escribe una respuesta antes de enviar.")


@st.fragment
def _fragment_consultas_usuario_form():
    secciones_usuario = cached_obtener_secciones_usuario(
        st.session_state["usuario"],
        data_cache_version=_velox_data_cache_version(),
    )
    if secciones_usuario:
        with st.container(border=True):
            seccion = st.selectbox(
                "Sección relacionada",
                secciones_usuario,
                format_func=lambda x: SECCIONES[x]["nombre"],
            )
            mensaje = st.text_area(
                "Tu consulta",
                height=150,
                placeholder="Escribe tu pregunta aquí...",
            )
            if st.button("Enviar consulta", type="primary", key="btn_enviar_consulta_usuario"):
                if mensaje.strip():
                    exito, texto = message_manager.enviar_mensaje(
                        st.session_state["usuario"],
                        st.session_state["nombre"],
                        seccion,
                        mensaje.strip(),
                    )
                    if exito:
                        _invalidar_cache_datos()
                        st.success(texto)
                        _rerun_velox(scope_fragment=True)
                    else:
                        st.error(texto)
                else:
                    st.warning("Escribe tu consulta antes de enviar.")
    else:
        st.warning("No tienes secciones asignadas. Contacta al administrador.")


def render_historial_consultas_master_completo():
    """Trazabilidad total de tickets consultas (Master principal)."""
    st.markdown("### 🗂️ Historial completo de consultas")
    st.caption("Registro de consultas de usuarios y notificaciones automáticas de pagos/comprobantes.")
    historial = cached_obtener_historial_consultas_completo(
        data_cache_version=_velox_data_cache_version()
    )
    if not historial:
        st.info("No hay registros en la tabla consultas.")
        return
    for msg in historial:
        with st.container(border=True):
            _render_tarjeta_consulta(msg, mostrar_email=True)
            seccion_nombre = _nombre_seccion_consulta(msg)
            st.caption(f"Origen: {seccion_nombre}")


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


def _docs_pagina_session_key(seccion, prefijo="pub"):
    return f"docs_pag_{prefijo}_{seccion}"


def _docs_busqueda_session_key(seccion, prefijo="pub"):
    return f"docs_busq_ctx_{prefijo}_{seccion}"


def _sincronizar_pagina_documentos(seccion, busqueda, prefijo="pub"):
    ctx_key = _docs_busqueda_session_key(seccion, prefijo)
    pag_key = _docs_pagina_session_key(seccion, prefijo)
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


def _render_paginacion_documentos(seccion, pagina, total_paginas, total_items, prefijo="pub"):
    pag_key = _docs_pagina_session_key(seccion, prefijo)
    col_prev, col_mid, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button(
            "◀ Anterior",
            key=f"docs_prev_{prefijo}_{seccion}",
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
            key=f"docs_next_{prefijo}_{seccion}",
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


def _solicitar_eliminar_publicacion(pub_id: str):
    st.session_state["velox_confirm_del_pub_id"] = pub_id


def _cancelar_eliminar_publicacion():
    st.session_state.pop("velox_confirm_del_pub_id", None)


@st.dialog("Eliminar documento")
def _dialog_confirmar_eliminar_publicacion():
    pub_id = st.session_state.get("velox_confirm_del_pub_id", "")
    st.markdown("¿Estás seguro de eliminar este documento?")
    col_si, col_no = st.columns(2)
    with col_si:
        if st.button("Sí", type="primary", use_container_width=True, key="velox_del_pub_si"):
            try:
                exito, msg = storage_manager.eliminar_publicacion(pub_id)
                if exito:
                    st.session_state.pop(f"editando_{pub_id}", None)
                    _invalidar_cache_datos()
                    _cancelar_eliminar_publicacion()
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            except Exception as err:
                st.error(f"❌ Error al eliminar: {err}")
    with col_no:
        if st.button("No", use_container_width=True, key="velox_del_pub_no"):
            _cancelar_eliminar_publicacion()
            st.rerun()


def _abrir_dialog_eliminar_publicacion_si_pendiente():
    if st.session_state.get("velox_confirm_del_pub_id"):
        _dialog_confirmar_eliminar_publicacion()


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
            st.button(
                "🗑️",
                key=f"del_{pub['id']}_{indice}",
                help="Eliminar",
                on_click=_solicitar_eliminar_publicacion,
                kwargs={"pub_id": pub["id"]},
            )

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
    busqueda,
    prefijo,
    render_fila_fn,
    mensaje_vacio,
    es_master=False,
    incluir_publicar=False,
):
    filtrados = _filtrar_documentos_por_busqueda(documentos, busqueda)
    pagina = _sincronizar_pagina_documentos(seccion, busqueda, prefijo)
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
            _render_paginacion_documentos(seccion, pagina, total_paginas, total_items, prefijo)


def _render_bloque_publicaciones_compacto(
    seccion_id,
    busqueda,
    secciones_usuario,
    *,
    prefijo="pub",
    titulo="### 📢 Publicaciones disponibles",
    mensaje_vacio="No hay documentos disponibles.",
    seccion_info=None,
    sincronizar_chatbot=False,
):
    """Lista compacta unificada de publicaciones (Inicio y Mis Documentos)."""
    st.markdown(titulo)
    _cache_v = _velox_data_cache_version()
    publicaciones = cached_obtener_publicaciones_por_seccion(
        seccion=seccion_id,
        subcategoria=None,
        data_cache_version=_cache_v,
    )
    if sincronizar_chatbot and _chatbot_habilitado() and seccion_info:
        _actualizar_catalogo_chatbot_seccion(
            seccion_info, seccion_id, secciones_usuario
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
        busqueda,
        prefijo=prefijo,
        render_fila_fn=_render_fila_publicacion,
        mensaje_vacio=mensaje_vacio,
        es_master=_es_master(),
    )
    if _es_master():
        _abrir_dialog_eliminar_publicacion_si_pendiente()


def _actualizar_catalogo_chatbot_seccion(seccion_info, seccion_id, secciones_usuario):
    if not _chatbot_habilitado():
        return []
    catalogo = cached_listar_catalogo_seccion(
        seccion_id,
        subcategoria=None,
        data_cache_version=_velox_data_cache_version(),
    )
    st.session_state["velox_catalogo_documentos"] = [
        {
            "nombre": item["nombre"],
            "carpeta": seccion_info["nombre"],
            "subcategoria": item.get("subcategoria") or "",
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


def _notificacion_accesible_para_usuario(notif: dict, secciones_permitidas: frozenset) -> bool:
    """Avisos con sección solo si el usuario tiene acceso activo a ese curso."""
    seccion = _seccion_desde_notificacion(notif)
    if not seccion:
        return True
    return _resolver_seccion_id(seccion) in secciones_permitidas


def _filtrar_notificaciones_por_acceso_usuario(notificaciones: list) -> list:
    if _es_staff():
        return list(notificaciones or [])
    permitidas = frozenset(_secciones_efectivas())
    if not permitidas:
        return []
    return [
        n for n in (notificaciones or [])
        if _notificacion_accesible_para_usuario(n, permitidas)
    ]


def _obtener_notificaciones_visibles_usuario(usuario: str, limite: Optional[int] = None) -> list:
    cache_v = _velox_data_cache_version()
    todas = cached_obtener_notificaciones_no_leidas(usuario, data_cache_version=cache_v)
    visibles = _filtrar_notificaciones_por_acceso_usuario(todas)
    if limite is None:
        return visibles
    limite_seguro = max(1, min(int(limite or LIMITE_NOTIFICACIONES_CAMPANA), 8))
    return visibles[:limite_seguro]


MASTER_CATEGORIA_PUBLICACION_FIJA = "Formatos y Plantillas"


def abrir_notificacion(
    notificacion_id,
    seccion,
    categoria=None,
    titulo=None,
    publicacion_id=None,
):
    notification_manager.marcar_como_leida(notificacion_id, st.session_state["usuario"])
    _invalidar_cache_datos()
    st.session_state["menu_principal"] = AuthManager.MODULO_DOCUMENTOS
    seccion_norm = _resolver_seccion_id(normalizar_seccion(seccion)) if seccion else None
    st.session_state.seccion_activa = seccion_norm or "inicio"
    if seccion_norm:
        st.session_state["seccion_seleccionada_documentos"] = seccion_norm
    if titulo:
        st.session_state["notif_redirect_mensaje"] = f"✅ Has sido redirigido a la publicación: {titulo}"
        nombre_busqueda = titulo.rsplit(".", 1)[0] if "." in titulo else titulo
        if seccion_norm:
            st.session_state[_mis_docs_busqueda_key(seccion_norm)] = nombre_busqueda
    if publicacion_id:
        st.session_state["notif_redirect_publicacion_id"] = publicacion_id

def render_campana_notificaciones():
    usuario = st.session_state["usuario"]
    no_leidas = len(_obtener_notificaciones_visibles_usuario(usuario))
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
        _campana_notificaciones_lista(usuario)


def _campana_notificaciones_lista(usuario: str):
    st.markdown('<p class="notif-panel-title">Notificaciones</p>', unsafe_allow_html=True)
    st.caption("Publicaciones pendientes de leer")
    notificaciones = _obtener_notificaciones_visibles_usuario(
        usuario,
        LIMITE_NOTIFICACIONES_CAMPANA,
    )

    if not notificaciones:
        st.info("No tienes notificaciones pendientes")
        return

    for notif in notificaciones:
        metadata = _parsear_metadata_notif(notif.get("metadata"))
        seccion = _seccion_desde_notificacion(notif)
        categoria = metadata.get("subcategoria") or metadata.get("categoria") or "General"
        seccion_id = _resolver_seccion_id(seccion) if seccion else ""
        seccion_nombre = SECCIONES.get(seccion_id, {}).get("nombre", seccion.capitalize() if seccion else "General")
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

PLANES_COMPRA_CURSOS = {
    "1_curso": {
        "titulo": "Plan Individual",
        "precio": 30.0,
        "plan_label": "1 Curso",
        "max_cursos": 1,
    },
    "2_cursos": {
        "titulo": "Plan Dúo",
        "precio": 50.0,
        "plan_label": "2 Cursos",
        "max_cursos": 2,
        "ahorro": "Ahorras S/ 10",
    },
}

# Claves homologadas con Supabase (columna cursos_solicitados) — solo secciones activas
CURSOS_PLAN_CATALOGO: Dict[str, str] = {
    sec_id: sec_info["nombre"]
    for sec_id, sec_info in SECCIONES.items()
    if sec_info.get("active", True)
}

VELOX_PLAN_AZUL_OSCURO = "#1A365D"
VELOX_PLAN_AZUL_PASTEL = "#2B6CB0"
VELOX_PLAN_CIAN = "#319795"

PLAN_COMPRA_HEADER_CSS = f"""
<style>
    .velox-plan-topbar-wrap {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 0.65rem;
        margin-bottom: -0.35rem;
        padding-right: 0.15rem;
    }}
    .st-key-btn_adquirir_plan_cursos .stButton > button {{
        background: #2563EB !important;
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35) !important;
        font-weight: bold !important;
        font-size: 1rem !important;
        padding: 0.68rem 1.2rem !important;
        letter-spacing: 0.01em !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    }}
    .st-key-btn_adquirir_plan_cursos .stButton > button p,
    .st-key-btn_adquirir_plan_cursos .stButton > button span {{
        color: #FFFFFF !important;
        font-weight: bold !important;
        font-size: 1rem !important;
    }}
    .st-key-btn_adquirir_plan_cursos .stButton > button:hover {{
        transform: translateY(-1px) !important;
        background: #1E40AF !important;
        background-color: #1E40AF !important;
        box-shadow: 0 8px 22px rgba(30, 64, 175, 0.4) !important;
        color: #FFFFFF !important;
    }}
</style>
"""

PLAN_COMPRA_MODAL_CSS = f"""
<style>
    [data-testid="stDialog"] > div {{
        max-width: 520px !important;
        width: min(520px, calc(100vw - 2rem)) !important;
    }}
    [data-testid="stDialog"] [data-testid="stDialogContent"] {{
        max-height: min(640px, 88vh) !important;
        overflow-y: auto !important;
        padding-top: 0.5rem !important;
    }}
    .velox-plan-modal-title {{
        color: {VELOX_PLAN_AZUL_OSCURO};
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0.85rem 0 0.45rem 0;
        padding-bottom: 0.35rem;
        border-bottom: 2px solid {VELOX_PLAN_CIAN};
    }}
    .velox-plan-modal-sub {{
        color: #4a5568;
        font-size: 0.88rem;
        margin: 0 0 0.65rem 0;
        line-height: 1.45;
    }}
    .velox-plan-resumen {{
        background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        border: 1px solid #cbd5e0;
        border-left: 4px solid {VELOX_PLAN_CIAN};
        border-radius: 8px;
        padding: 0.75rem 0.9rem;
        margin: 0.5rem 0 0.75rem 0;
        font-size: 0.88rem;
        color: {VELOX_PLAN_AZUL_OSCURO};
    }}
    .velox-plan-resumen__total {{
        font-size: 1.15rem;
        font-weight: 800;
        color: {VELOX_PLAN_AZUL_PASTEL};
        margin-top: 0.25rem;
    }}
    .velox-plan-qr-wrap {{
        text-align: center;
        padding: 0.5rem;
        background: #fff;
        border: 1px dashed #cbd5e0;
        border-radius: 8px;
    }}
    .velox-plan-qr-wrap img {{
        max-width: 220px !important;
        width: 220px !important;
        height: auto !important;
        margin: 0 auto;
        display: block;
    }}
    .velox-plan-inst {{
        font-size: 0.82rem;
        color: #4a5568;
        line-height: 1.5;
        margin-top: 0.5rem;
    }}
    .velox-yape-seguridad {{
        text-align: center;
        font-size: 0.86rem;
        color: #334155;
        line-height: 1.45;
        margin-top: 0.5rem;
    }}
    .velox-yape-seguridad p {{
        margin: 0.35rem 0;
    }}
    .st-key-btn_plan_compra_confirmar .stButton > button {{
        background: {VELOX_PLAN_AZUL_PASTEL} !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}
    .st-key-btn_plan_compra_confirmar .stButton > button:hover {{
        background: {VELOX_PLAN_AZUL_OSCURO} !important;
    }}
    .st-key-btn_plan_compra_cerrar .stButton > button {{
        border-radius: 8px !important;
        border: 1px solid #cbd5e0 !important;
        color: {VELOX_PLAN_AZUL_OSCURO} !important;
    }}
</style>
"""


def _en_vista_inicio_home() -> bool:
    return (
        st.session_state.get("menu_principal") == "🏠 Inicio"
        and st.session_state.get("seccion_activa") == "inicio"
    )


INICIO_SERVICIOS_ACCESOS_CSS = """
<style id="velox-inicio-servicios-accesos-v4">
    .st-key-inicio_servicios_row {
        margin: 0 0 1rem 0 !important;
    }
    .st-key-inicio_servicios_row [data-testid="stHorizontalBlock"] {
        gap: 0.65rem !important;
        align-items: stretch !important;
    }

    /* Secundarios — Asesoría, Plantilla, Clases (link buttons en cols 1-3) */
    .st-key-inicio_servicios_row a[data-testid="stLinkButton"],
    .st-key-inicio_servicios_row [data-testid="stLinkButton"],
    .st-key-inicio_servicios_row a[data-testid="baseLinkButton"],
    .st-key-inicio_servicios_row [data-testid="baseLinkButton"] {
        width: 100% !important;
        min-height: 2.55rem !important;
        border-radius: 20px !important;
        background: rgba(255, 255, 255, 0.97) !important;
        background-color: rgba(255, 255, 255, 0.97) !important;
        background-image: none !important;
        color: #0F766E !important;
        font-weight: 600 !important;
        border: 1.5px solid rgba(0, 201, 167, 0.45) !important;
        box-shadow: 0 4px 14px rgba(0, 128, 128, 0.12) !important;
        white-space: normal !important;
        line-height: 1.25 !important;
        text-align: center !important;
        text-decoration: none !important;
        outline: none !important;
        -webkit-tap-highlight-color: transparent !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .st-key-inicio_servicios_row [data-testid="stLinkButton"] p,
    .st-key-inicio_servicios_row [data-testid="stLinkButton"] span,
    .st-key-inicio_servicios_row a[data-testid="stLinkButton"] p,
    .st-key-inicio_servicios_row a[data-testid="stLinkButton"] span {
        color: #0F766E !important;
        font-weight: 600 !important;
    }

    .st-key-inicio_servicios_row a[data-testid="stLinkButton"]:hover,
    .st-key-inicio_servicios_row [data-testid="stLinkButton"]:hover {
        background: rgba(240, 253, 250, 0.98) !important;
        background-color: rgba(240, 253, 250, 0.98) !important;
        color: #0D9488 !important;
        border-color: rgba(0, 201, 167, 0.62) !important;
        box-shadow: 0 6px 18px rgba(0, 201, 167, 0.18) !important;
    }

    .st-key-inicio_servicios_row a[data-testid="stLinkButton"]:focus,
    .st-key-inicio_servicios_row a[data-testid="stLinkButton"]:focus-visible,
    .st-key-inicio_servicios_row a[data-testid="stLinkButton"]:active,
    .st-key-inicio_servicios_row a[data-testid="stLinkButton"]:visited,
    .st-key-inicio_servicios_row [data-testid="stLinkButton"]:focus,
    .st-key-inicio_servicios_row [data-testid="stLinkButton"]:focus-visible,
    .st-key-inicio_servicios_row [data-testid="stLinkButton"]:active,
    .st-key-inicio_servicios_row [data-testid="baseLinkButton"]:focus,
    .st-key-inicio_servicios_row [data-testid="baseLinkButton"]:focus-visible,
    .st-key-inicio_servicios_row [data-testid="baseLinkButton"]:active {
        background: rgba(255, 255, 255, 0.97) !important;
        background-color: rgba(255, 255, 255, 0.97) !important;
        background-image: none !important;
        color: #0F766E !important;
        border: 1.5px solid rgba(0, 201, 167, 0.45) !important;
        box-shadow: 0 4px 14px rgba(0, 128, 128, 0.12) !important;
        outline: none !important;
        filter: none !important;
        transform: none !important;
    }

    /* Destacado — Adquirir Plan de Cursos */
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 [data-testid="stBaseButton-primary"] button,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 [data-testid="baseButton-primary"],
    .st-key-inicio_svc_4 .stButton > button,
    .st-key-inicio_svc_4 .stButton > button[kind="primary"],
    .st-key-inicio_svc_4 .stButton > button[data-testid="stBaseButton-primary"],
    .st-key-inicio_svc_4 .stButton > button[data-testid="baseButton-primary"] {
        width: 100% !important;
        min-height: 2.55rem !important;
        border-radius: 20px !important;
        background: linear-gradient(90deg, #008080 0%, #00C9A7 100%) !important;
        background-color: transparent !important;
        background-image: linear-gradient(90deg, #008080 0%, #00C9A7 100%) !important;
        color: #FFFFFF !important;
        font-weight: bold !important;
        border: none !important;
        box-shadow: 0 6px 20px rgba(0, 201, 167, 0.28),
                    inset 0 1px 0 rgba(255, 255, 255, 0.18) !important;
        white-space: normal !important;
        line-height: 1.25 !important;
        text-align: center !important;
        outline: none !important;
        outline-offset: 0 !important;
        -webkit-tap-highlight-color: transparent !important;
    }

    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button p,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button span,
    .st-key-inicio_svc_4 .stButton > button p,
    .st-key-inicio_svc_4 .stButton > button span {
        color: #FFFFFF !important;
        font-weight: bold !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.18) !important;
    }

    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:hover,
    .st-key-inicio_svc_4 .stButton > button:hover {
        background: linear-gradient(90deg, #00A3B1 0%, #00E5FF 100%) !important;
        background-image: linear-gradient(90deg, #00A3B1 0%, #00E5FF 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 8px 24px rgba(0, 229, 255, 0.32),
                    inset 0 1px 0 rgba(255, 255, 255, 0.18) !important;
        filter: none !important;
        transform: translateY(-1px) !important;
    }

    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:focus,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:focus-visible,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:active,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:visited,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:disabled,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 [data-testid="stBaseButton-primary"] button:focus,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 [data-testid="stBaseButton-primary"] button:focus-visible,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 [data-testid="stBaseButton-primary"] button:active,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 [data-testid="stBaseButton-primary"] button:visited,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 [data-testid="stBaseButton-primary"] button:disabled,
    .st-key-inicio_svc_4 .stButton > button:focus,
    .st-key-inicio_svc_4 .stButton > button:focus-visible,
    .st-key-inicio_svc_4 .stButton > button:active,
    .st-key-inicio_svc_4 .stButton > button:visited,
    .st-key-inicio_svc_4 .stButton > button:disabled,
    .st-key-inicio_svc_4 .stButton > button[kind="primary"]:focus,
    .st-key-inicio_svc_4 .stButton > button[kind="primary"]:focus-visible,
    .st-key-inicio_svc_4 .stButton > button[kind="primary"]:active,
    .st-key-inicio_svc_4 .stButton > button[data-testid="stBaseButton-primary"]:focus,
    .st-key-inicio_svc_4 .stButton > button[data-testid="stBaseButton-primary"]:focus-visible,
    .st-key-inicio_svc_4 .stButton > button[data-testid="stBaseButton-primary"]:active {
        background: linear-gradient(90deg, #008080 0%, #00C9A7 100%) !important;
        background-color: transparent !important;
        background-image: linear-gradient(90deg, #008080 0%, #00C9A7 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 6px 20px rgba(0, 201, 167, 0.28),
                    inset 0 1px 0 rgba(255, 255, 255, 0.18) !important;
        outline: none !important;
        outline-offset: 0 !important;
        filter: none !important;
        opacity: 1 !important;
    }

    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:focus p,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:focus span,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:active p,
    .st-key-inicio_servicios_row .st-key-inicio_svc_4 .stButton > button:active span,
    .st-key-inicio_svc_4 .stButton > button:focus p,
    .st-key-inicio_svc_4 .stButton > button:focus span,
    .st-key-inicio_svc_4 .stButton > button:active p,
    .st-key-inicio_svc_4 .stButton > button:active span {
        color: #FFFFFF !important;
        font-weight: bold !important;
    }

    @media (max-width: 1100px) {
        .st-key-inicio_servicios_row [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        .st-key-inicio_servicios_row [data-testid="column"],
        .st-key-inicio_servicios_row [data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.35rem) !important;
            min-width: calc(50% - 0.35rem) !important;
        }
    }
    @media (max-width: 640px) {
        .st-key-inicio_servicios_row [data-testid="column"],
        .st-key-inicio_servicios_row [data-testid="stColumn"] {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }
</style>
"""


def _render_inicio_servicios_accesos() -> None:
    """Fila superior de accesos a servicios en la vista Inicio (home)."""
    with st.container(key="inicio_servicios_row"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.link_button(
                "Asesoría / Negocio",
                _url_whatsapp_con_mensaje(
                    "Hola, deseo información sobre Asesoría / Negocio en veloX."
                ),
                use_container_width=True,
            )
        with col2:
            st.link_button(
                "¿Te Personalizo tu Plantilla?",
                _url_whatsapp_con_mensaje(
                    "Hola, deseo personalizar mi plantilla en veloX."
                ),
                use_container_width=True,
            )
        with col3:
            st.link_button(
                "Clases personalizadas",
                _url_whatsapp_con_mensaje(
                    "Hola, deseo información sobre clases personalizadas en veloX."
                ),
                use_container_width=True,
            )
        with col4:
            st.button(
                "Adquirir Plan de Cursos",
                key="inicio_svc_4",
                use_container_width=True,
                type="primary",
                on_click=_abrir_dialog_plan_cursos,
            )


def _opciones_cursos_plan() -> Dict[str, str]:
    return dict(CURSOS_PLAN_CATALOGO)


def _nombre_curso_plan(curso_id: str) -> str:
    return CURSOS_PLAN_CATALOGO.get(curso_id, curso_id)


def _cerrar_dialog_plan_cursos() -> None:
    st.session_state["dialog_plan_cursos"] = False


def _abrir_dialog_plan_cursos():
    st.session_state["dialog_plan_cursos"] = True


@st.dialog("💎 Adquirir Plan de Cursos", width="medium", on_dismiss=_cerrar_dialog_plan_cursos)
def _dialog_adquirir_plan_cursos():
    st.markdown(PLAN_COMPRA_MODAL_CSS, unsafe_allow_html=True)

    email_usuario = (st.session_state.get("usuario") or "").strip()
    nombre_usuario = st.session_state.get("nombre", "Usuario")

    st.markdown(
        '<p class="velox-plan-modal-sub">Selecciona tu plan, elige los cursos y adjunta el comprobante Yape/Plin.</p>',
        unsafe_allow_html=True,
    )
    st.caption(f"{nombre_usuario} · {email_usuario}")

    st.markdown('<div class="velox-plan-modal-title">1 · Plan</div>', unsafe_allow_html=True)
    plan_elegido = st.radio(
        "Plan",
        options=list(PLANES_COMPRA_CURSOS.keys()),
        format_func=lambda k: (
            f"{PLANES_COMPRA_CURSOS[k]['titulo']} — S/ {PLANES_COMPRA_CURSOS[k]['precio']:.2f}"
            + (
                f" · {PLANES_COMPRA_CURSOS[k]['ahorro']}"
                if k == "2_cursos" and PLANES_COMPRA_CURSOS[k].get("ahorro")
                else ""
            )
        ),
        key="plan_compra_plan_id",
        label_visibility="collapsed",
        horizontal=True,
    )
    plan_info = PLANES_COMPRA_CURSOS[plan_elegido]
    if st.session_state.get("_plan_compra_prev") != plan_elegido:
        st.session_state["_plan_compra_prev"] = plan_elegido
        st.session_state.pop("plan_compra_cursos_sel", None)

    st.markdown('<div class="velox-plan-modal-title">2 · Cursos</div>', unsafe_allow_html=True)
    limite_cursos = plan_info["max_cursos"]
    cursos_sel = st.multiselect(
        "Cursos",
        options=list(CURSOS_PLAN_CATALOGO.keys()),
        format_func=_nombre_curso_plan,
        max_selections=limite_cursos,
        key="plan_compra_cursos_sel",
        label_visibility="collapsed",
        placeholder=f"Elige {limite_cursos} curso(s)...",
    )
    seleccion_valida = len(cursos_sel) == limite_cursos
    if cursos_sel and not seleccion_valida:
        st.warning(f"Selecciona exactamente {limite_cursos} curso(s).")

    st.markdown('<div class="velox-plan-modal-title">3 · Pago</div>', unsafe_allow_html=True)
    nombres_cursos = [_nombre_curso_plan(c) for c in cursos_sel]
    st.markdown(
        f"""
        <div class="velox-plan-resumen">
            <div><strong>Plan:</strong> {plan_info['plan_label']} ·
            <strong>Cursos:</strong> {", ".join(nombres_cursos) if nombres_cursos else "—"}</div>
            <div class="velox-plan-resumen__total">Total: S/ {plan_info['precio']:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_qr, col_upload = st.columns([1, 1])
    with col_qr:
        st.markdown('<div class="velox-plan-qr-wrap">', unsafe_allow_html=True)
        if os.path.exists(YAPE_QR_PATH):
            st.image(YAPE_QR_PATH, width=220, caption="Yape / Plin")
        else:
            st.warning(f"QR no disponible (`{YAPE_QR_PATH}`)")
        st.markdown(YAPE_QR_SEGURIDAD_HTML, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_upload:
        comprobante = st.file_uploader(
            "Comprobante de pago",
            type=["jpg", "jpeg", "png", "pdf"],
            key="plan_compra_comprobante",
        )
        st.caption(MSG_YAPE_SUBIR_COMPROBANTE)

    puede_enviar = seleccion_valida and comprobante is not None
    col_enviar, col_cerrar = st.columns([2, 1])
    with col_enviar:
        st.markdown('<div class="st-key-btn_plan_compra_confirmar">', unsafe_allow_html=True)
        if st.button(
            "Confirmar y Enviar Comprobante",
            type="primary",
            use_container_width=True,
            key="btn_plan_compra_confirmar",
            disabled=not puede_enviar,
        ):
            with _velox_spinner("Registrando solicitud..."):
                ok, msg = payment_manager.registrar_comprobante_plan_cursos(
                    email_usuario,
                    plan_elegido,
                    list(cursos_sel),
                    comprobante_file=comprobante,
                )
            if ok:
                _cerrar_dialog_plan_cursos()
                st.session_state["plan_compra_exito_msg"] = MSG_YAPE_COMPROBANTE_OK
                st.session_state.pop("plan_compra_cursos_sel", None)
                st.session_state.pop("plan_compra_comprobante", None)
                _invalidar_cache_datos()
                st.rerun()
            else:
                st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_cerrar:
        st.markdown('<div class="st-key-btn_plan_compra_cerrar">', unsafe_allow_html=True)
        st.button(
            "Cerrar",
            use_container_width=True,
            key="btn_plan_compra_cerrar",
            on_click=_cerrar_dialog_plan_cursos,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def render_app_top_bar():
    """Barra superior post-login: campana de notificaciones."""
    st.markdown(PLAN_COMPRA_HEADER_CSS, unsafe_allow_html=True)

    menu_actual = st.session_state.get("menu_principal", "🏠 Inicio")
    if st.session_state.get("_velox_plan_dialog_menu") != menu_actual:
        _cerrar_dialog_plan_cursos()
    st.session_state["_velox_plan_dialog_menu"] = menu_actual

    _, col_bell = st.columns([11, 1])
    with col_bell:
        render_campana_notificaciones()

    plan_exito = st.session_state.pop("plan_compra_exito_msg", None)
    if plan_exito:
        st.success(plan_exito)

    if st.session_state.get("dialog_plan_cursos"):
        if _en_vista_inicio_home():
            _dialog_adquirir_plan_cursos()
        else:
            _cerrar_dialog_plan_cursos()


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

            import pygwalker as pyg

            pyg_html = pyg.to_html(df, theme="dark")
            components.html(pyg_html, height=850, scrolling=True)

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
    else:
        st.info(
            "💡 Consejo: Asegúrate de que la primera fila de tu Excel contenga los nombres "
            "de las columnas para que el diseñador las reconozca automáticamente."
        )


def _render_documentos_seccion_inicio(seccion_id, secciones_usuario, busqueda_key):
    """Lista de publicaciones de la sección (sin sub-pestañas por categoría)."""
    st.markdown(MIS_DOCS_COMPACT_CSS, unsafe_allow_html=True)
    busqueda = st.text_input(
        "🔍 Buscar por nombre o descripción:",
        key=busqueda_key,
    )
    _render_bloque_publicaciones_compacto(
        seccion_id,
        busqueda,
        secciones_usuario,
        prefijo="inicio",
        titulo="### 📢 Documentos disponibles",
        mensaje_vacio="No hay documentos disponibles en esta sección.",
    )


def render_vista_seccion_inicio(seccion_id):
    seccion_id = _resolver_seccion_id(seccion_id)
    if seccion_id not in SECCIONES or not _seccion_esta_activa(seccion_id):
        st.session_state.seccion_activa = "inicio"
        st.rerun()
        return

    seccion_info = SECCIONES[seccion_id]
    secciones_usuario = _secciones_efectivas()

    if seccion_id not in secciones_usuario:
        st.warning("🔒 Esta sección requiere acceso activo.")
        st.button(
            "💎 Adquirir Curso",
            key=f"adquirir_curso_view_{seccion_id}",
            type="primary",
            on_click=_abrir_dialog_plan_cursos_desde_catalogo,
            kwargs={"_seccion_id": seccion_id},
        )
        st.button("⬅️ Volver al Inicio", key="btn_volver_inicio_denegado", on_click=volver_al_inicio)
        return

    st.button("⬅️ Volver al Inicio", key="btn_volver_inicio", on_click=volver_al_inicio)
    _render_banner_seccion_detalle(seccion_info)

    _render_documentos_seccion_inicio(
        seccion_id,
        secciones_usuario,
        busqueda_key=f"buscador_inicio_{seccion_id}",
    )

    if seccion_id == "power_bi":
        st.markdown("---")
        with st.expander("📊 Diseñador de Dashboards", expanded=False):
            mostrar_modulo_dashboard_interactivo()

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

_usuario_con_acceso = st.session_state.get("autenticado")

if _en_vista_recuperacion_password():
    _render_auth_portal_prefix()
    render_pantalla_solo_recuperacion()
    st.stop()

if not _usuario_con_acceso:
    _render_auth_portal_prefix()
    login_screen()
    st.stop()

_ensure_data_managers()

_ensure_sesion_perfil_local()

if auth_manager.usuario_requiere_configurar_password():
    render_pantalla_configurar_password()
    st.stop()

if _sincronizar_token_culqi_query():
    _procesar_culqi_si_hay_token("")

else:
    # ==================== HEADER (solo después del login) ====================
    inject_post_login_shell_layout()
    inject_sidebar_collapse_control()
    render_velox_top_banner()
    render_app_top_bar()
    render_activation_banner()
    _marcar_consultas_leidas_al_entrar()
    _init_sidebar_counts_si_falta()

    # ==================== SIDEBAR ====================
    with st.sidebar:
        inject_sidebar_theme()
        render_sidebar_brand()

        email_sidebar = (st.session_state.get("usuario") or "").strip()
        rol_sidebar = st.session_state.get("rol", "usuario")
        rol_badge = _etiqueta_rol_sidebar(rol_sidebar)

        st.markdown('<div class="sidebar-profile sidebar-profile--compact">', unsafe_allow_html=True)
        mascot_src = _sidebar_mascot_src()
        if mascot_src:
            st.markdown(
                f'<div class="sidebar-mascot-ring">'
                f'<img src="{mascot_src}" alt="veloX" class="sidebar-mascot-img" />'
                f"</div>",
                unsafe_allow_html=True,
            )
        elif os.path.exists(VELOX_LOGO_PATH):
            _av_esp, _av_mid, _av_esp2 = st.columns([1, 1, 1])
            with _av_mid:
                st.image(VELOX_LOGO_PATH, width=68)
        if email_sidebar:
            email_seguro = html_module.escape(email_sidebar)
            st.markdown(
                f'<p class="sidebar-profile-email sidebar-profile-email--hero">{email_seguro}</p>',
                unsafe_allow_html=True,
            )
        credenciales_seguro = html_module.escape(f"✔ Gmail verificado · {rol_badge}")
        st.markdown(
            f'<p class="sidebar-profile-credentials">{credenciales_seguro}</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        menu_items = _menu_sidebar_items()
        menu_values = [item[2] for item in menu_items]

        if st.session_state.get("menu_principal") not in menu_values:
            legacy = st.session_state.get("menu_principal")
            if legacy == "📬 Consultas" and AuthManager.MODULO_CONSULTAS in menu_values:
                st.session_state["menu_principal"] = AuthManager.MODULO_CONSULTAS
            else:
                st.session_state["menu_principal"] = menu_values[0]

        _render_sidebar_menu_botones(menu_items, st.session_state["menu_principal"])

        _render_sidebar_value_card()

        st.divider()
        if st.button("Cerrar Sesión", icon="🚪", use_container_width=True, key="sidebar_logout"):
            auth_manager.cerrar_sesion()
            st.rerun()

    # ==================== CONTENIDO PRINCIPAL ====================
    menu_actual = st.session_state.get('menu_principal', '🏠 Inicio')

    if menu_actual == "🏠 Inicio":
        if st.session_state.seccion_activa == "inicio":
            _render_inicio_servicios_accesos()
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
            opciones_ids = [s for s in secciones_usuario if s in SECCIONES]
            seccion_preseleccionada_norm = (
                _resolver_seccion_id(normalizar_seccion(seccion_preseleccionada))
                if seccion_preseleccionada
                else None
            )
            if seccion_preseleccionada_norm and seccion_preseleccionada_norm in opciones_ids:
                st.session_state[
                    _docs_pagina_session_key(seccion_preseleccionada_norm, prefijo="pub")
                ] = 1
                _invalidar_cache_datos()

            _inicializar_selector_seccion_documentos(opciones_ids, seccion_preseleccionada_norm)

            seccion_seleccionada = st.selectbox(
                "Seleccionar sección:",
                options=opciones_ids,
                format_func=lambda sid: SECCIONES[sid]["nombre"],
                key="selector_seccion_documentos",
            )
            _sincronizar_cambio_seccion_mis_docs(seccion_seleccionada)
            seccion_info = SECCIONES[seccion_seleccionada]

            _render_banner_seccion_detalle(seccion_info)

            if st.button("🔙 Volver al Dashboard", key="btn_volver_dashboard"):
                st.rerun()

            subcategorias_disponibles = seccion_info.get("subcategorias", ["General"])

            st.markdown(MIS_DOCS_COMPACT_CSS, unsafe_allow_html=True)
            busqueda = st.text_input(
                "🔍 Buscar documentos",
                placeholder="Filtra por nombre, descripción o palabra clave…",
                key=_mis_docs_busqueda_key(seccion_seleccionada),
                label_visibility="collapsed",
            )
            st.caption("Búsqueda instantánea sobre los documentos de esta sección.")

            if (
                _puede_publicar_documentos()
                and seccion_seleccionada in secciones_usuario
                and _puede_modulo(AuthManager.MODULO_DOCUMENTOS)
            ):
                with st.expander("📤 Publicar documento", expanded=_es_admin()):
                    st.caption(f"Publicación en **{seccion_info['nombre']}**")
                    with st.form(
                        key=f"form_pub_{seccion_seleccionada}",
                        clear_on_submit=True,
                    ):
                        if _es_master():
                            st.markdown("**Categoría de destino**")
                            st.markdown(
                                '<p style="font-weight:700;letter-spacing:0.06em;'
                                'color:#1e2a3e;margin:0.15rem 0 0.75rem 0;">'
                                "FORMATOS Y PLANTILLAS</p>",
                                unsafe_allow_html=True,
                            )
                            categoria_publicar = MASTER_CATEGORIA_PUBLICACION_FIJA
                        else:
                            categoria_publicar = st.selectbox(
                                "Categoría de destino",
                                options=subcategorias_disponibles,
                                key=f"mis_docs_pub_categoria_{seccion_seleccionada}",
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
                                    st.session_state[
                                        _docs_pagina_session_key(
                                            seccion_seleccionada,
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
                busqueda,
                secciones_usuario,
                prefijo="pub",
                titulo=titulo_publicaciones,
                mensaje_vacio="No hay publicaciones disponibles en esta sección.",
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

    elif menu_actual == AuthManager.MODULO_COBRANZAS:
        if _es_master_admin_comprobantes():
            render_gestion_comprobantes_admin()
        else:
            st.warning("Acceso denegado. Este módulo es exclusivo del administrador Master.")
            st.session_state["menu_principal"] = AuthManager.MODULO_INICIO
            st.rerun()

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
            st.header("💬 Gestión de Consultas")
            st.caption(
                "Historial de respuestas de cobranzas y centro de soporte para consultas "
                "sobre cursos enviadas por los usuarios."
            )

            if _es_master_admin_comprobantes():
                with st.expander("🗂️ Historial completo de tickets (trazabilidad)", expanded=False):
                    render_historial_consultas_master_completo()
                st.markdown("---")

            _fragment_consultas_staff_pendientes()

            with st.expander("Ver consultas respondidas"):
                respondidas = cached_obtener_consultas_respondidas_master(
                    data_cache_version=_velox_data_cache_version()
                )
                if not respondidas:
                    st.info("Aún no hay consultas respondidas.")
                else:
                    for msg in respondidas:
                        with st.container(border=True):
                            _render_tarjeta_consulta(msg, mostrar_email=True)
        else:
            st.header("💬 Mis Consultas")
            st.markdown("Envía tu consulta al administrador y revisa las respuestas recibidas.")
            _fragment_consultas_usuario_form()
            st.markdown("---")
            st.markdown("### 📋 Historial de consultas")
            historial = cached_obtener_historial_consultas_usuario(
                st.session_state["usuario"],
                data_cache_version=_velox_data_cache_version(),
            )
            if not historial:
                st.info("Aún no tienes consultas ni notificaciones registradas.")
            else:
                for msg in historial:
                    with st.container(border=True):
                        _render_tarjeta_consulta(msg)
                        seccion_nombre = _nombre_seccion_consulta(msg)
                        st.caption(f"Origen: {seccion_nombre}")

    elif menu_actual == "👤 Mi Perfil":
        if _es_master():
            st.warning("Este módulo no está disponible para tu rol.")
        else:
            st.header("Mi Perfil")
            usuario_email = st.session_state["usuario"]
            perfil = cached_obtener_perfil_usuario(
                usuario_email,
                data_cache_version=_velox_data_cache_version(),
            )
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

    if _chatbot_habilitado() and _chatbot_visible_en_modulo_actual():
        render_chatbot_asistente()

    render_footer()
