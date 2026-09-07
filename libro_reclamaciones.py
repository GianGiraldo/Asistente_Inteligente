"""Libro de Reclamaciones Virtual — registro en Supabase (Ley N° 29571)."""
from __future__ import annotations

import re
import secrets
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from supabase_client import get_supabase

TABLA_LIBRO_RECLAMACIONES = "libro_reclamaciones"

TIPOS_BIEN = ("Producto", "Servicio")
TIPOS_RECLAMO = ("Reclamo", "Queja")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
DNI_REGEX = re.compile(r"^\d{8}$")
CE_REGEX = re.compile(r"^[A-Za-z0-9]{9,12}$")
TELEFONO_REGEX = re.compile(r"^9\d{8}$")

LIBRO_RECLAMACIONES_CSS = """
<style>
    .velox-libro-reclamaciones {
        color: #ffffff;
    }

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-header {
        text-align: center;
        margin: 0 0 1.25rem 0;
        padding: 0 0.5rem;
    }

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-header h1 {
        font-size: 1.35rem;
        font-weight: 700;
        color: #ffffff !important;
        margin: 0 0 0.5rem 0;
        line-height: 1.3;
    }

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-header p {
        font-size: 0.82rem;
        color: #ffffff !important;
        opacity: 0.92;
        margin: 0;
        line-height: 1.45;
    }

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-success,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-success p,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-success strong {
        text-align: center;
        padding: 1rem 0.5rem 0.25rem;
        color: #ffffff !important;
    }

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-success__code {
        display: inline-block;
        margin: 0.75rem 0;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        background: rgba(0, 180, 216, 0.18);
        border: 1px solid rgba(0, 229, 255, 0.35);
        color: #ffffff !important;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.03em;
    }

    /* Labels nativos de Streamlit en esta vista */
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"],
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"] p,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"] span,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"] label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stMarkdownContainer"] p,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .stSelectbox label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .stTextInput label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .stTextArea label {
        color: #ffffff !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .stTextArea textarea {
        min-height: 96px;
    }

    .stApp:has(.velox-libro-reclamaciones) .main .block-container {
        max-width: 520px !important;
        width: min(520px, calc(100vw - 1.5rem)) !important;
    }

    /* Botón superior: Volver al inicio de sesión */
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_volver_login .stButton > button,
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_volver_login .stButton > button p,
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_volver_login .stButton > button span,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-reclamaciones .velox-back-login .stButton > button,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-reclamaciones .velox-back-login .stButton > button p,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-reclamaciones .velox-back-login .stButton > button span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        font-weight: 600 !important;
    }

    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_volver_login .stButton > button:hover,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-reclamaciones .velox-back-login .stButton > button:hover {
        color: #ffffff !important;
        opacity: 0.88 !important;
    }

    /* Botón de envío y acciones secundarias */
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_btn_registrar .stButton > button,
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_btn_registrar .stButton > button p,
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_btn_registrar .stButton > button span,
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_nueva_reclamacion .stButton > button,
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_nueva_reclamacion .stButton > button p,
    .stApp:has(.velox-libro-reclamaciones) .st-key-libro_nueva_reclamacion .stButton > button span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 700 !important;
    }
</style>
"""


def _format_error(exc: Exception) -> str:
    partes = [str(exc)]
    for attr in ("message", "details", "hint", "code"):
        valor = getattr(exc, attr, None)
        if valor:
            partes.append(str(valor))
    return " | ".join(dict.fromkeys(partes))


def generar_codigo_seguimiento() -> str:
    """Genera código único REC-AAAA-XXXX."""
    year = datetime.now().year
    prefix = f"REC-{year}-"
    supabase = get_supabase()
    for _ in range(12):
        codigo = f"{prefix}{secrets.randbelow(10000):04d}"
        try:
            result = (
                supabase.table(TABLA_LIBRO_RECLAMACIONES)
                .select("id")
                .eq("codigo_seguimiento", codigo)
                .limit(1)
                .execute()
            )
            if not result.data:
                return codigo
        except Exception:
            return codigo
    return f"{prefix}{int(datetime.now().timestamp()) % 10000:04d}"


def validar_formulario_reclamacion(datos: Dict[str, str]) -> Optional[str]:
    nombres = (datos.get("nombres_apellidos") or "").strip()
    documento = (datos.get("documento_identidad") or "").strip()
    correo = (datos.get("correo") or "").strip().lower()
    telefono = (datos.get("telefono") or "").strip()
    tipo_bien = (datos.get("tipo_bien") or "").strip()
    tipo_reclamo = (datos.get("tipo") or "").strip()
    detalle = (datos.get("detalle") or "").strip()
    pedido = (datos.get("pedido") or "").strip()

    if len(nombres) < 3:
        return "Ingresa tus nombres y apellidos completos."
    if not (DNI_REGEX.match(documento) or CE_REGEX.match(documento)):
        return "El DNI debe tener 8 dígitos o el Carnet de Extranjería entre 9 y 12 caracteres."
    if not EMAIL_REGEX.match(correo):
        return "Ingresa un correo electrónico válido."
    if not TELEFONO_REGEX.match(telefono):
        return "El teléfono debe ser un celular peruano de 9 dígitos (inicia en 9)."
    if tipo_bien not in TIPOS_BIEN:
        return "Selecciona el tipo de bien (Producto o Servicio)."
    if tipo_reclamo not in TIPOS_RECLAMO:
        return "Selecciona si es Reclamo o Queja."
    if len(detalle) < 10:
        return "Describe el detalle del reclamo o queja (mínimo 10 caracteres)."
    if len(pedido) < 10:
        return "Indica tu pedido concreto (mínimo 10 caracteres)."
    return None


def registrar_reclamacion(datos: Dict[str, str]) -> Tuple[bool, str, Optional[str]]:
    error = validar_formulario_reclamacion(datos)
    if error:
        return False, error, None

    codigo = generar_codigo_seguimiento()
    registro: Dict[str, Any] = {
        "codigo_seguimiento": codigo,
        "nombres_apellidos": datos["nombres_apellidos"].strip(),
        "documento_identidad": datos["documento_identidad"].strip(),
        "correo": datos["correo"].strip().lower(),
        "telefono": datos["telefono"].strip(),
        "tipo_bien": datos["tipo_bien"].strip(),
        "tipo": datos["tipo"].strip(),
        "detalle": datos["detalle"].strip(),
        "pedido": datos["pedido"].strip(),
        "creado_en": datetime.now().isoformat(),
    }

    try:
        supabase = get_supabase()
        result = supabase.table(TABLA_LIBRO_RECLAMACIONES).insert(registro).execute()
        if result.data:
            return True, "Reclamación registrada correctamente.", codigo
        return False, "No se pudo registrar la reclamación. Inténtalo nuevamente.", None
    except Exception as exc:
        return False, f"Error al registrar: {_format_error(exc)}", None


def render_libro_reclamaciones_auth_view() -> None:
    """Formulario nativo del Libro de Reclamaciones (vista de acceso)."""
    st.markdown(LIBRO_RECLAMACIONES_CSS, unsafe_allow_html=True)
    st.markdown('<div class="velox-libro-reclamaciones">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="velox-libro-header">
            <h1>Libro de Reclamaciones Virtual</h1>
            <p>(Ley N° 29571 - Código de Protección y Defensa del Consumidor)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="velox-back-login">', unsafe_allow_html=True)
    if st.button("← Volver al inicio de sesión", key="libro_volver_login"):
        st.query_params.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    codigo_ok = st.session_state.get("libro_reclamacion_codigo")
    if codigo_ok:
        st.markdown(
            f"""
            <div class="velox-libro-success">
                <p>Su reclamación fue registrada correctamente.</p>
                <div class="velox-libro-success__code">{codigo_ok}</div>
                <p>Conserve este código para el seguimiento de su caso.</p>
                <p><strong>Plazo legal de respuesta: 15 días hábiles</strong>, conforme a la normativa vigente.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Registrar otra reclamación", key="libro_nueva_reclamacion"):
            st.session_state.pop("libro_reclamacion_codigo", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown('<div class="velox-libro-form">', unsafe_allow_html=True)

    nombres = st.text_input(
        "Nombres y Apellidos *",
        key="libro_nombres_apellidos",
        placeholder="Ej.: Juan Pérez García",
    )
    documento = st.text_input(
        "DNI o Carnet de Extranjería *",
        key="libro_documento_identidad",
        placeholder="DNI: 8 dígitos | CE: 9-12 caracteres",
    )
    correo = st.text_input(
        "Correo Electrónico *",
        key="libro_correo",
        placeholder="tucorreo@ejemplo.com",
    )
    telefono = st.text_input(
        "Teléfono *",
        key="libro_telefono",
        placeholder="9XXXXXXXX",
    )
    tipo_bien = st.selectbox(
        "Tipo de Bien *",
        options=["", *TIPOS_BIEN],
        format_func=lambda v: "Seleccione..." if v == "" else v,
        key="libro_tipo_bien",
    )
    tipo_reclamo = st.selectbox(
        "Tipo *",
        options=["", *TIPOS_RECLAMO],
        format_func=lambda v: "Seleccione..." if v == "" else v,
        key="libro_tipo_reclamo",
    )
    detalle = st.text_area(
        "Detalle *",
        key="libro_detalle",
        placeholder="Describa con claridad los hechos de su reclamo o queja.",
    )
    pedido = st.text_area(
        "Pedido *",
        key="libro_pedido",
        placeholder="Indique qué solución o acción solicita.",
    )

    if st.button(
        "Registrar reclamación",
        type="primary",
        use_container_width=True,
        key="libro_btn_registrar",
    ):
        payload = {
            "nombres_apellidos": nombres,
            "documento_identidad": documento,
            "correo": correo,
            "telefono": telefono,
            "tipo_bien": tipo_bien,
            "tipo": tipo_reclamo,
            "detalle": detalle,
            "pedido": pedido,
        }
        ok, mensaje, codigo = registrar_reclamacion(payload)
        if ok and codigo:
            st.session_state["libro_reclamacion_codigo"] = codigo
            st.rerun()
        st.error(mensaje)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
