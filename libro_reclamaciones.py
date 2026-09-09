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
from email.utils import formataddr
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from supabase_client import get_supabase_admin

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
    """Lee SMTP desde variables de entorno o st.secrets[smtp]."""
    cfg: Dict[str, Any] = {}
    try:
        bloque = st.secrets["smtp"]
        cfg = dict(bloque) if bloque else {}
    except Exception:
        try:
            bloque = st.secrets.get("smtp")
            if bloque:
                cfg = dict(bloque)
        except Exception:
            cfg = {}

    def _env(*names: str) -> str:
        for name in names:
            valor = (os.getenv(name) or "").strip()
            if valor:
                return valor
        return ""

    port_raw = _env("SMTP_PORT") or str(cfg.get("port") or "587")
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 587

    user = _env("SMTP_USER") or str(cfg.get("user") or "").strip()
    from_email = (
        _env("SMTP_FROM")
        or str(cfg.get("from_email") or cfg.get("from") or user).strip()
    )
    admin_email = (
        _env("SMTP_ADMIN")
        or str(cfg.get("admin_email") or user or from_email).strip()
    )
    use_tls_raw = _env("SMTP_USE_TLS") or str(cfg.get("use_tls", "true"))
    use_tls = use_tls_raw.lower() not in ("0", "false", "no")
    use_ssl = port == 465 or str(cfg.get("use_ssl", "")).lower() in ("1", "true", "yes")

    return {
        "host": _env("SMTP_HOST") or str(cfg.get("host") or "").strip(),
        "port": port,
        "user": user,
        "password": _env("SMTP_PASSWORD") or str(cfg.get("password") or "").strip(),
        "from_email": from_email or user,
        "from_name": _env("SMTP_FROM_NAME") or str(cfg.get("from_name") or "veloX").strip(),
        "admin_email": admin_email or from_email or user,
        "use_tls": use_tls and not use_ssl,
        "use_ssl": use_ssl,
    }


def _validar_config_smtp(smtp: Dict[str, Any]) -> List[str]:
    errores: List[str] = []
    if not smtp.get("host"):
        errores.append("SMTP: falta `host` en secrets [smtp] o variable SMTP_HOST.")
    if not smtp.get("user"):
        errores.append("SMTP: falta `user` en secrets [smtp] o variable SMTP_USER.")
    if not smtp.get("password"):
        errores.append("SMTP: falta `password` en secrets [smtp] o variable SMTP_PASSWORD.")
    if not smtp.get("from_email"):
        errores.append("SMTP: falta `from_email` en secrets [smtp] o variable SMTP_FROM.")
    if not smtp.get("admin_email"):
        errores.append("SMTP: falta correo administrativo (user/from_email/admin_email).")
    return errores


def _format_smtp_exception(exc: Exception, smtp: Dict[str, Any]) -> str:
    host = smtp.get("host") or "?"
    port = smtp.get("port") or "?"
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return (
            f"Autenticación SMTP rechazada en {host}:{port}. "
            f"Verifique user/password (Gmail requiere contraseña de aplicación). Detalle: {exc}"
        )
    if isinstance(exc, smtplib.SMTPConnectError):
        return f"No se pudo conectar al servidor SMTP {host}:{port}. Detalle: {exc}"
    if isinstance(exc, smtplib.SMTPException):
        return f"Error SMTP ({host}:{port}): {exc}"
    if isinstance(exc, TimeoutError):
        return f"Tiempo de espera agotado al conectar con SMTP {host}:{port}."
    if isinstance(exc, OSError):
        return f"Error de red/puerto SMTP ({host}:{port}): {exc}"
    return f"Error enviando correo ({host}:{port}): {exc}"


def _enviar_mensaje_smtp(
    smtp: Dict[str, Any],
    msg: MIMEMultipart,
    destinatarios: List[str],
) -> Tuple[bool, str]:
    destinatarios_limpios = [d.strip() for d in destinatarios if (d or "").strip()]
    if not destinatarios_limpios:
        return False, "No hay destinatarios válidos para el envío."

    try:
        if smtp.get("use_ssl"):
            server = smtplib.SMTP_SSL(smtp["host"], smtp["port"], timeout=30)
        else:
            server = smtplib.SMTP(smtp["host"], smtp["port"], timeout=30)

        with server:
            server.ehlo()
            if smtp.get("use_tls"):
                server.starttls()
                server.ehlo()
            if smtp.get("user") and smtp.get("password"):
                server.login(smtp["user"], smtp["password"])
            server.send_message(msg, from_addr=smtp["from_email"], to_addrs=destinatarios_limpios)
        return True, f"Enviado a {', '.join(destinatarios_limpios)}"
    except Exception as exc:
        logger.exception(
            "Fallo SMTP hacia %s via %s:%s",
            destinatarios_limpios,
            smtp.get("host"),
            smtp.get("port"),
        )
        return False, _format_smtp_exception(exc, smtp)


def _crear_mensaje_email(
    smtp: Dict[str, Any],
    destinatario: str,
    subject: str,
    plain_body: str,
    html_body: str,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((smtp["from_name"], smtp["from_email"]))
    msg["To"] = destinatario
    msg["Reply-To"] = smtp["from_email"]
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


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
    db = get_supabase_admin()

    try:
        result = (
            db.table(TABLA_LIBRO_RECLAMACIONES)
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
            db.table(TABLA_LIBRO_RECLAMACIONES)
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


def enviar_correos_reclamacion(
    registro: Dict[str, Any],
    codigo: str,
) -> Tuple[List[str], List[str]]:
    """
    Envía correo HTML al consumidor y copia idéntica al administrador.
    Retorna (mensajes_exito, mensajes_error).
    """
    exitos: List[str] = []
    errores: List[str] = []

    destinatario = (registro.get("correo") or "").strip().lower()
    if not destinatario:
        errores.append("Correo del consumidor vacío; no se pudo enviar confirmación.")
        return exitos, errores

    smtp = _resolve_smtp_settings()
    errores.extend(_validar_config_smtp(smtp))
    if errores:
        return exitos, errores

    if smtp["from_email"].lower() != smtp["user"].lower():
        smtp["from_email"] = smtp["user"]

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

    msg_user = _crear_mensaje_email(smtp, destinatario, subject, plain_body, html_body)
    ok_user, detalle_user = _enviar_mensaje_smtp(smtp, msg_user, [destinatario])
    if ok_user:
        exitos.append(f"Correo de confirmación enviado al consumidor ({destinatario}).")
    else:
        errores.append(f"Correo al consumidor: {detalle_user}")

    admin = (smtp["admin_email"] or smtp["user"] or smtp["from_email"]).strip().lower()
    if admin == destinatario:
        exitos.append("Copia administrativa omitida (mismo correo que el consumidor).")
    else:
        msg_admin = _crear_mensaje_email(smtp, admin, subject, plain_body, html_body)
        ok_admin, detalle_admin = _enviar_mensaje_smtp(smtp, msg_admin, [admin])
        if ok_admin:
            exitos.append(f"Copia de alerta enviada al administrador ({admin}).")
        else:
            errores.append(f"Correo administrativo: {detalle_admin}")

    return exitos, errores


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


def registrar_reclamacion(
    datos: Dict[str, str],
) -> Tuple[bool, str, Optional[str], List[str], List[str]]:
    """Retorna ok, mensaje, código, avisos_correo_ok, errores_correo."""
    error = validar_formulario_reclamacion(datos)
    if error:
        return False, error, None, [], []

    db = get_supabase_admin()
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
            result = db.table(TABLA_LIBRO_RECLAMACIONES).insert(registro).execute()
            if not result.data:
                return False, "No se pudo registrar la reclamación. Inténtalo nuevamente.", None, [], []

            exitos_mail, errores_mail = enviar_correos_reclamacion(registro, codigo)
            if not errores_mail:
                return True, "Reclamación registrada correctamente.", codigo, exitos_mail, []
            logger.warning(
                "Reclamación %s registrada con fallos SMTP: %s",
                codigo,
                "; ".join(errores_mail),
            )
            return (
                True,
                "Reclamación registrada correctamente.",
                codigo,
                exitos_mail,
                errores_mail,
            )
        except Exception as exc:
            detalle_error = _format_error(exc).lower()
            if "duplicate" in detalle_error or "unique" in detalle_error:
                continue
            return False, f"Error al registrar: {_format_error(exc)}", None, [], []

    return False, "No se pudo asignar un código de seguimiento. Inténtalo nuevamente.", None, [], []


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
        mail_exitos = st.session_state.pop("libro_reclamacion_mail_exitos", []) or []
        mail_errores = st.session_state.pop("libro_reclamacion_mail_errores", []) or []

        st.markdown(
            f"""
            <div class="velox-libro-success">
                <p>Su reclamación fue registrada correctamente.</p>
                <div class="velox-libro-success__code">{html.escape(str(codigo_ok))}</div>
                <p>Conserve este código para el seguimiento de su caso.</p>
                <p><strong>Plazo legal de respuesta: 15 días hábiles</strong>, conforme a la normativa vigente.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for aviso in mail_exitos:
            st.success(aviso)
        for fallo in mail_errores:
            st.error(f"Error de correo: {fallo}")
        if mail_exitos and not mail_errores:
            st.success("Los correos de confirmación fueron enviados correctamente.")
        elif not mail_exitos and not mail_errores:
            st.warning(
                "La reclamación quedó registrada, pero no hay confirmación de envío de correos."
            )

        if st.button("Registrar otra reclamación", key="libro_nueva_reclamacion"):
            st.session_state.pop("libro_reclamacion_codigo", None)
            st.session_state.pop("libro_reclamacion_mail_exitos", None)
            st.session_state.pop("libro_reclamacion_mail_errores", None)
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
        ok, mensaje, codigo, mail_exitos, mail_errores = registrar_reclamacion(payload)
        if ok and codigo:
            st.session_state["libro_reclamacion_codigo"] = codigo
            st.session_state["libro_reclamacion_mail_exitos"] = mail_exitos
            st.session_state["libro_reclamacion_mail_errores"] = mail_errores
            st.rerun()
        for fallo in mail_errores:
            st.error(f"Error de correo: {fallo}")
        st.error(mensaje)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
