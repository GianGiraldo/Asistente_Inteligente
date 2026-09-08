"""Libro de Reclamaciones Virtual — registro en Supabase (Ley N° 29571)."""
from __future__ import annotations

import html
import logging
import os
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from supabase_client import get_supabase

logger = logging.getLogger(__name__)

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

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .velox-auth-field-label,
    .stApp:has(.velox-libro-reclamaciones) .velox-auth-field-label {
        display: block;
        margin: 0.65rem 0 0.35rem;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }

    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"],
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"] p,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"] span,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stWidgetLabel"] label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stTextInput"] label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stTextArea"] label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form [data-testid="stSelectbox"] label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .stTextInput label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .stTextArea label,
    .stApp:has(.velox-libro-reclamaciones) .velox-libro-form .stSelectbox label {
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


def _resolve_smtp_settings() -> Dict[str, Any]:
    """Lee SMTP desde variables de entorno o st.secrets[smtp] (mismo patrón del proyecto)."""
    cfg: Dict[str, Any] = {}
    try:
        bloque = st.secrets.get("smtp")
        if bloque:
            cfg = dict(bloque)
    except Exception:
        cfg = {}

    def _pick(*keys: str, default: str = "") -> str:
        for key in keys:
            env_val = (os.getenv(key) or "").strip()
            if env_val:
                return env_val
        for key in keys:
            secret_key = key.lower().replace("smtp_", "")
            if secret_key in cfg and str(cfg[secret_key]).strip():
                return str(cfg[secret_key]).strip()
        return default

    port_raw = _pick("SMTP_PORT", default=str(cfg.get("port") or "587"))
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 587

    return {
        "host": _pick("SMTP_HOST", default=str(cfg.get("host") or "")),
        "port": port,
        "user": _pick("SMTP_USER", default=str(cfg.get("user") or "")),
        "password": _pick("SMTP_PASSWORD", default=str(cfg.get("password") or "")),
        "from_email": _pick(
            "SMTP_FROM",
            default=str(cfg.get("from_email") or cfg.get("from") or ""),
        ),
        "from_name": _pick(
            "SMTP_FROM_NAME",
            default=str(cfg.get("from_name") or "veloX"),
        ),
        "use_tls": str(cfg.get("use_tls", os.getenv("SMTP_USE_TLS", "true"))).lower()
        not in ("0", "false", "no"),
    }


def _parse_correlativo_codigo(codigo: str, year: int) -> int:
    prefix = f"REC-{year}-"
    if not codigo.startswith(prefix):
        return 0
    suffix = codigo[len(prefix) :]
    if not suffix.isdigit():
        return 0
    try:
        return int(suffix)
    except ValueError:
        return 0


def generar_codigo_seguimiento() -> str:
    """Genera código secuencial REC-AAAA-0001 según registros del año."""
    year = datetime.now().year
    prefix = f"REC-{year}-"
    supabase = get_supabase()

    try:
        result = (
            supabase.table(TABLA_LIBRO_RECLAMACIONES)
            .select("codigo_seguimiento")
            .like("codigo_seguimiento", f"{prefix}%")
            .execute()
        )
        max_correlativo = 0
        for row in result.data or []:
            correlativo = _parse_correlativo_codigo(
                str(row.get("codigo_seguimiento") or ""),
                year,
            )
            max_correlativo = max(max_correlativo, correlativo)
        return f"{prefix}{max_correlativo + 1:04d}"
    except Exception as exc:
        logger.warning("No se pudo calcular correlativo secuencial: %s", exc)
        fallback = (
            supabase.table(TABLA_LIBRO_RECLAMACIONES)
            .select("id", count="exact")
            .execute()
        )
        total = int(getattr(fallback, "count", None) or 0)
        return f"{prefix}{total + 1:04d}"


def _build_reclamacion_email_html(registro: Dict[str, Any], codigo: str) -> str:
    nombre = html.escape(str(registro.get("nombres_apellidos") or ""))
    documento = html.escape(str(registro.get("documento_identidad") or ""))
    correo = html.escape(str(registro.get("correo") or ""))
    telefono = html.escape(str(registro.get("telefono") or ""))
    tipo_bien = html.escape(str(registro.get("tipo_bien") or ""))
    tipo = html.escape(str(registro.get("tipo") or ""))
    detalle = html.escape(str(registro.get("detalle") or "")).replace("\n", "<br>")
    pedido = html.escape(str(registro.get("pedido") or "")).replace("\n", "<br>")
    codigo_safe = html.escape(codigo)
    fecha = html.escape(
        datetime.now().strftime("%d/%m/%Y %H:%M")
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Confirmación Libro de Reclamaciones — veloX</title>
</head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:Arial,Helvetica,sans-serif;color:#1e293b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef2f7;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="620" cellspacing="0" cellpadding="0" style="max-width:620px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #dbe3ef;">
          <tr>
            <td style="background:#1A2332;padding:24px 28px;text-align:center;">
              <div style="font-size:24px;font-weight:700;color:#00E5FF;letter-spacing:0.08em;">veloX</div>
              <div style="font-size:18px;font-weight:700;color:#ffffff;margin-top:8px;">Libro de Reclamaciones Virtual</div>
              <div style="font-size:12px;color:#cbd5e1;margin-top:6px;">Ley N° 29571 — Código de Protección y Defensa del Consumidor</div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;">
              <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">Estimado(a) <strong>{nombre}</strong>,</p>
              <p style="margin:0 0 20px;font-size:15px;line-height:1.6;">
                Hemos registrado correctamente su {'reclamo' if tipo.lower() == 'reclamo' else 'queja'} en nuestro Libro de Reclamaciones Virtual.
              </p>
              <div style="text-align:center;margin:0 0 24px;">
                <div style="display:inline-block;padding:12px 20px;border-radius:8px;background:#ecfdf5;border:1px solid #86efac;">
                  <div style="font-size:12px;color:#047857;text-transform:uppercase;letter-spacing:0.08em;">Código de seguimiento</div>
                  <div style="font-size:22px;font-weight:700;color:#065f46;margin-top:4px;">{codigo_safe}</div>
                </div>
              </div>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px;">
                <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;"><strong>Fecha de registro:</strong></td><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{fecha}</td></tr>
                <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;"><strong>Documento:</strong></td><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{documento}</td></tr>
                <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;"><strong>Correo:</strong></td><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{correo}</td></tr>
                <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;"><strong>Teléfono:</strong></td><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{telefono}</td></tr>
                <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;"><strong>Tipo de bien:</strong></td><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{tipo_bien}</td></tr>
                <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;"><strong>Tipo:</strong></td><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{tipo}</td></tr>
                <tr><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;vertical-align:top;"><strong>Detalle:</strong></td><td style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{detalle}</td></tr>
                <tr><td style="padding:10px 0;vertical-align:top;"><strong>Pedido:</strong></td><td style="padding:10px 0;">{pedido}</td></tr>
              </table>
              <div style="margin-top:24px;padding:16px;border-radius:8px;background:#fff7ed;border:1px solid #fdba74;">
                <p style="margin:0;font-size:14px;line-height:1.6;color:#9a3412;">
                  <strong>Plazo legal de respuesta:</strong> su caso será atendido en un plazo máximo de
                  <strong>15 días hábiles</strong>, conforme a la normativa vigente de protección al consumidor.
                </p>
              </div>
              <p style="margin:24px 0 0;font-size:13px;line-height:1.6;color:#64748b;">
                Conserve este correo y su código de seguimiento para futuras consultas.
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#f8fafc;padding:16px 28px;text-align:center;font-size:12px;color:#64748b;">
              © {datetime.now().year} veloX — Todos los derechos reservados
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def enviar_correo_confirmacion_reclamacion(
    registro: Dict[str, Any],
    codigo: str,
) -> Tuple[bool, str]:
    """Envía correo HTML de confirmación al consumidor."""
    destinatario = (registro.get("correo") or "").strip().lower()
    if not destinatario:
        return False, "Correo del destinatario vacío."

    smtp = _resolve_smtp_settings()
    if not smtp["host"] or not smtp["from_email"]:
        return False, "SMTP no configurado."

    subject = f"Confirmación Libro de Reclamaciones — {codigo}"
    html_body = _build_reclamacion_email_html(registro, codigo)
    plain_body = (
        f"Su reclamación fue registrada correctamente.\n\n"
        f"Código de seguimiento: {codigo}\n"
        f"Plazo legal de respuesta: 15 días hábiles.\n\n"
        f"Tipo: {registro.get('tipo')}\n"
        f"Tipo de bien: {registro.get('tipo_bien')}\n"
        f"Detalle: {registro.get('detalle')}\n"
        f"Pedido: {registro.get('pedido')}\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{smtp['from_name']} <{smtp['from_email']}>"
    msg["To"] = destinatario
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp["host"], smtp["port"], timeout=30) as server:
            if smtp["use_tls"]:
                server.starttls()
            if smtp["user"] and smtp["password"]:
                server.login(smtp["user"], smtp["password"])
            server.sendmail(smtp["from_email"], [destinatario], msg.as_string())
        return True, "Correo enviado."
    except Exception as exc:
        logger.exception("Error enviando correo de reclamación a %s", destinatario)
        return False, f"Error enviando correo: {exc}"


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

    supabase = get_supabase()
    registro_base: Dict[str, Any] = {
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

    for _ in range(3):
        codigo = generar_codigo_seguimiento()
        registro = {"codigo_seguimiento": codigo, **registro_base}
        try:
            result = supabase.table(TABLA_LIBRO_RECLAMACIONES).insert(registro).execute()
            if not result.data:
                return False, "No se pudo registrar la reclamación. Inténtalo nuevamente.", None

            mail_ok, mail_msg = enviar_correo_confirmacion_reclamacion(registro, codigo)
            if mail_ok:
                return True, "Reclamación registrada correctamente.", codigo
            logger.warning("Reclamación %s registrada pero correo falló: %s", codigo, mail_msg)
            return (
                True,
                "Reclamación registrada correctamente. No pudimos enviar el correo de confirmación; conserve su código en pantalla.",
                codigo,
            )
        except Exception as exc:
            detalle_error = _format_error(exc).lower()
            if "duplicate" in detalle_error or "unique" in detalle_error:
                continue
            return False, f"Error al registrar: {_format_error(exc)}", None

    return False, "No se pudo asignar un código de seguimiento. Inténtalo nuevamente.", None


def _render_campo_texto(label: str, key: str, placeholder: str, *, area: bool = False) -> str:
    st.markdown(
        f'<label class="velox-auth-field-label">{html.escape(label)}</label>',
        unsafe_allow_html=True,
    )
    if area:
        return st.text_area(
            label,
            key=key,
            label_visibility="collapsed",
            placeholder=placeholder,
        )
    return st.text_input(
        label,
        key=key,
        label_visibility="collapsed",
        placeholder=placeholder,
    )


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
                <div class="velox-libro-success__code">{html.escape(str(codigo_ok))}</div>
                <p>Conserve este código para el seguimiento de su caso.</p>
                <p>Le enviamos un correo de confirmación con el detalle de su registro.</p>
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

    nombres = _render_campo_texto(
        "Nombres y Apellidos *",
        "libro_nombres_apellidos",
        "Ej.: Juan Pérez García",
    )
    documento = _render_campo_texto(
        "DNI o Carnet de Extranjería *",
        "libro_documento_identidad",
        "DNI: 8 dígitos | CE: 9-12 caracteres",
    )
    correo = _render_campo_texto(
        "Correo Electrónico *",
        "libro_correo",
        "tucorreo@ejemplo.com",
    )
    telefono = _render_campo_texto(
        "Teléfono *",
        "libro_telefono",
        "9XXXXXXXX",
    )

    st.markdown(
        '<label class="velox-auth-field-label">Tipo de Bien *</label>',
        unsafe_allow_html=True,
    )
    tipo_bien = st.selectbox(
        "Tipo de Bien *",
        options=["", *TIPOS_BIEN],
        format_func=lambda v: "Seleccione..." if v == "" else v,
        key="libro_tipo_bien",
        label_visibility="collapsed",
    )

    st.markdown(
        '<label class="velox-auth-field-label">Tipo *</label>',
        unsafe_allow_html=True,
    )
    tipo_reclamo = st.selectbox(
        "Tipo *",
        options=["", *TIPOS_RECLAMO],
        format_func=lambda v: "Seleccione..." if v == "" else v,
        key="libro_tipo_reclamo",
        label_visibility="collapsed",
    )

    detalle = _render_campo_texto(
        "Detalle *",
        "libro_detalle",
        "Describa con claridad los hechos de su reclamo o queja.",
        area=True,
    )
    pedido = _render_campo_texto(
        "Pedido *",
        "libro_pedido",
        "Indique qué solución o acción solicita.",
        area=True,
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
