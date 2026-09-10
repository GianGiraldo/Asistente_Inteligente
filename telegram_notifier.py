"""Alertas Telegram para el módulo de Cobranzas (server-side, no bloqueante)."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def _resolve_telegram_credentials() -> Tuple[str, str]:
    """Lee TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID desde env o st.secrets."""
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    try:
        import streamlit as st

        if not token:
            token = str(st.secrets.get("TELEGRAM_BOT_TOKEN") or "").strip()
        if not chat_id:
            chat_id = str(st.secrets.get("TELEGRAM_CHAT_ID") or "").strip()

        bloque = st.secrets.get("telegram")
        if bloque:
            if not token:
                token = str(
                    bloque.get("bot_token")
                    or bloque.get("TELEGRAM_BOT_TOKEN")
                    or ""
                ).strip()
            if not chat_id:
                chat_id = str(
                    bloque.get("chat_id")
                    or bloque.get("TELEGRAM_CHAT_ID")
                    or ""
                ).strip()
    except Exception:
        pass

    return token, chat_id


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
        return

    token, chat_id = _resolve_telegram_credentials()
    if not token or not chat_id:
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": _formatear_mensaje_cobranza(payload),
            },
            timeout=10,
        )
        if not response.ok:
            logger.warning(
                "Telegram cobranzas HTTP %s: %s",
                response.status_code,
                (response.text or "")[:300],
            )
    except requests.RequestException as exc:
        logger.warning("Telegram cobranzas (red): %s", exc)
    except Exception as exc:
        logger.warning("Telegram cobranzas: %s", exc)
