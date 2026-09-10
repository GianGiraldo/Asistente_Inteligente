"""Alertas Telegram para el módulo de Cobranzas (server-side, no bloqueante)."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _log(msg: str) -> None:
    """Stdout con flush para que Cloud Run capture la traza de inmediato."""
    print(msg, flush=True)
    logger.info("%s", msg)


def _resumen_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Datos seguros para log (sin URLs largas ni tokens)."""
    return {
        "usuario_email": (payload.get("usuario_email") or payload.get("email") or "").strip(),
        "celular": (payload.get("celular") or "").strip(),
        "metodo_pago": (payload.get("metodo_pago") or "").strip(),
        "monto": payload.get("monto"),
        "plan_seleccionado": (payload.get("plan_seleccionado") or "").strip(),
        "cursos_solicitados": payload.get("cursos_solicitados"),
        "tiene_comprobante": bool(
            (payload.get("archivo_url") or payload.get("comprobante_url") or "").strip()
        ),
    }


def _resolve_telegram_credentials() -> Tuple[str, str, str]:
    """Lee TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID desde env o st.secrets."""
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    origen = "env" if token and chat_id else ""

    try:
        import streamlit as st

        if not token:
            token = str(st.secrets.get("TELEGRAM_BOT_TOKEN") or "").strip()
            if token:
                origen = "secrets_root"
        if not chat_id:
            chat_id = str(st.secrets.get("TELEGRAM_CHAT_ID") or "").strip()
            if chat_id and not origen:
                origen = "secrets_root"

        bloque = st.secrets.get("telegram")
        if bloque:
            if not token:
                token = str(
                    bloque.get("bot_token")
                    or bloque.get("TELEGRAM_BOT_TOKEN")
                    or ""
                ).strip()
                if token:
                    origen = "secrets_telegram"
            if not chat_id:
                chat_id = str(
                    bloque.get("chat_id")
                    or bloque.get("TELEGRAM_CHAT_ID")
                    or ""
                ).strip()
                if chat_id and not origen:
                    origen = "secrets_telegram"
    except Exception as exc:
        logger.info("Telegram: no se pudieron leer st.secrets (%s)", exc)

    if token and chat_id and origen.startswith("env"):
        origen = "env"
    elif token and chat_id and not origen:
        origen = "mixto"

    return token, chat_id, origen


def _formatear_cursos(cursos_raw: Any) -> str:
    if cursos_raw is None:
        return "—"
    if isinstance(cursos_raw, list):
        items = [str(c).strip() for c in cursos_raw if str(c).strip()]
        return ", ".join(items) if items else "—"
    if isinstance(cursos_raw, str):
        texto = cursos_raw.strip()
        if not texto:
            return "—"
        try:
            parsed = json.loads(texto)
            if isinstance(parsed, list):
                return _formatear_cursos(parsed)
        except json.JSONDecodeError:
            pass
        return texto
    return str(cursos_raw)


def _formatear_mensaje_cobranza(payload: Dict[str, Any]) -> str:
    email = (payload.get("usuario_email") or payload.get("email") or "—").strip()
    celular = (payload.get("celular") or "—").strip() or "—"
    metodo = (payload.get("metodo_pago") or "—").strip() or "—"
    plan = (payload.get("plan_seleccionado") or "—").strip() or "—"
    cursos = _formatear_cursos(payload.get("cursos_solicitados"))
    comprobante = (
        (payload.get("archivo_url") or payload.get("comprobante_url") or "").strip()
        or "Sin adjunto / pendiente de captura"
    )
    monto_raw = payload.get("monto")
    if monto_raw is None:
        monto_txt = "—"
    else:
        try:
            monto_txt = f"S/ {float(monto_raw):.2f}"
        except (TypeError, ValueError):
            monto_txt = str(monto_raw)

    return (
        "🔔 Nueva solicitud de Cobranzas — veloX\n\n"
        f"👤 Email: {email}\n"
        f"📱 Celular: {celular}\n"
        f"💳 Método: {metodo}\n"
        f"💰 Monto: {monto_txt}\n"
        f"📦 Plan: {plan}\n"
        f"📚 Cursos: {cursos}\n"
        f"🧾 Comprobante: {comprobante}\n"
        f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )


def notificar_nueva_solicitud_cobranza(payload: Optional[Dict[str, Any]] = None) -> None:
    """Envía alerta Telegram; fallos se registran en log sin afectar la app."""
    if not payload:
        _log("[velox-telegram] omitido: payload vacío")
        return

    resumen = _resumen_payload(payload)
    _log(f"[velox-telegram] disparo notificación | datos={resumen}")

    token, chat_id, origen = _resolve_telegram_credentials()
    token_ok = bool(token)
    chat_ok = bool(chat_id)
    _log(
        f"[velox-telegram] credenciales | origen={origen or 'NO'} "
        f"token={'OK' if token_ok else 'NO'} chat_id={'OK' if chat_ok else 'NO'}"
    )
    if not token or not chat_id:
        _log("[velox-telegram] abortado: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
        return

    texto = _formatear_mensaje_cobranza(payload)
    chat_id_payload: Any = chat_id
    if str(chat_id).lstrip("-").isdigit():
        chat_id_payload = int(chat_id)
    body = {"chat_id": chat_id_payload, "text": texto}
    _log(
        f"[velox-telegram] POST sendMessage | chat_id={chat_id_payload} "
        f"texto_len={len(texto)} preview={texto[:120]!r}"
    )

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, json=body, timeout=10)
        status = response.status_code
        resp_text = (response.text or "")[:500]
        _log(f"[velox-telegram] respuesta HTTP status={status} body={resp_text}")
        if not response.ok:
            logger.warning(
                "Telegram cobranzas HTTP %s: %s",
                status,
                resp_text,
            )
        else:
            _log("[velox-telegram] envío OK")
    except requests.RequestException as exc:
        _log(f"[velox-telegram] error de red: {exc}")
        logger.warning("Telegram cobranzas (red): %s", exc)
    except Exception as exc:
        _log(f"[velox-telegram] error inesperado: {exc}")
        logger.warning("Telegram cobranzas: %s", exc)
