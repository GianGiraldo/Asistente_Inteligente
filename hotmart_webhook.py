"""Procesamiento del webhook Hotmart → activación de acceso en Supabase."""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from payment_manager import (
    CURSOS_PLAN_VALIDOS,
    ESTADO_APROBADO,
    PaymentManager,
    TABLA_COMPROBANTES,
)
from supabase_client import get_supabase_server

logger = logging.getLogger(__name__)

HOTMART_EVENTS_ACTIVAR = frozenset(
    {
        "PURCHASE_APPROVED",
        "PURCHASE_COMPLETE",
    }
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class HotmartPaymentBridge(PaymentManager):
    """PaymentManager sin dependencia de Streamlit (solo variables de entorno)."""

    def __init__(self) -> None:
        self.supabase = get_supabase_server()


def _slug(text: str) -> str:
    return _SLUG_RE.sub("_", (text or "").strip().lower()).strip("_")


def _load_offer_map() -> Dict[str, List[str]]:
    """Mapeo opcional oferta Hotmart → cursos internos (JSON en HOTMART_OFFER_MAP)."""
    raw = (os.getenv("HOTMART_OFFER_MAP") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("HOTMART_OFFER_MAP no es JSON válido; se ignora.")
        return {}
    if not isinstance(parsed, dict):
        return {}

    normalizado: Dict[str, List[str]] = {}
    for clave, valor in parsed.items():
        key = _slug(str(clave))
        if isinstance(valor, list):
            normalizado[key] = [
                str(item).strip().lower()
                for item in valor
                if str(item).strip()
            ]
        elif isinstance(valor, str) and valor.strip():
            normalizado[key] = [valor.strip().lower()]
    return normalizado


def _extraer_email(payload: Dict[str, Any]) -> Optional[str]:
    data = payload.get("data") or {}
    buyer = data.get("buyer") or {}
    email = (
        buyer.get("email")
        or data.get("buyer_email")
        or payload.get("email")
    )
    if not email:
        return None
    return str(email).strip().lower()


def _extraer_oferta(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data") or {}
    purchase = data.get("purchase") or {}
    offer = purchase.get("offer") or {}
    product = data.get("product") or {}
    return {
        "code": str(offer.get("code") or "").strip(),
        "name": str(offer.get("name") or "").strip(),
        "description": str(offer.get("description") or purchase.get("offer_description") or "").strip(),
        "product_id": product.get("id"),
        "product_name": str(product.get("name") or "").strip(),
        "transaction": str(purchase.get("transaction") or payload.get("id") or "").strip(),
        "status": str(purchase.get("status") or "").strip(),
    }


def _cursos_desde_oferta(offer_info: Dict[str, Any]) -> List[str]:
    offer_map = _load_offer_map()
    claves_busqueda = [
        _slug(offer_info.get("code") or ""),
        _slug(offer_info.get("name") or ""),
        _slug(offer_info.get("description") or ""),
        _slug(offer_info.get("product_name") or ""),
    ]
    for clave in claves_busqueda:
        if clave and clave in offer_map:
            return list(offer_map[clave])

    texto = " ".join(
        filter(
            None,
            [
                offer_info.get("name"),
                offer_info.get("description"),
                offer_info.get("product_name"),
            ],
        )
    ).lower()
    detectados: List[str] = []
    for curso in CURSOS_PLAN_VALIDOS:
        tokens = {curso, curso.replace("_", " "), curso.replace("_", "-")}
        if any(token in texto for token in tokens if token):
            detectados.append(curso)
    return detectados


def _registrar_comprobante_hotmart(
    bridge: HotmartPaymentBridge,
    email: str,
    offer_info: Dict[str, Any],
    cursos: List[str],
) -> None:
    plan_label = offer_info.get("name") or offer_info.get("code") or "Hotmart"
    monto_raw = (offer_info.get("price") or {}).get("value")
    try:
        monto = float(monto_raw) if monto_raw is not None else None
    except (TypeError, ValueError):
        monto = None

    registro = {
        "usuario_email": email,
        "metodo_pago": "hotmart",
        "estado": ESTADO_APROBADO,
        "plan_seleccionado": plan_label,
        "cursos_solicitados": cursos or [],
        "archivo_url": offer_info.get("transaction") or None,
        "revisado_por": "hotmart_webhook",
        "fecha_revision": datetime.now().isoformat(),
    }
    if monto is not None:
        registro["monto"] = monto

    try:
        bridge.supabase.table(TABLA_COMPROBANTES).insert(registro).execute()
    except Exception as exc:
        logger.warning("No se pudo registrar comprobante Hotmart: %s", exc)


def _asegurar_usuario(
    bridge: HotmartPaymentBridge,
    email: str,
    nombre: Optional[str],
) -> Tuple[bool, str]:
    user = bridge._obtener_usuario(email)
    if user:
        return True, "usuario_existente"

    display = (nombre or email.split("@")[0]).strip() or email.split("@")[0]
    temp_password = secrets.token_urlsafe(16)
    password_hash, salt = bridge._hash_password(temp_password)
    data = {
        "email": email,
        "password": password_hash,
        "password_salt": salt,
        "nombre": display,
        "rol": "usuario",
        "secciones": ["excel"],
        "creado": datetime.now().isoformat(),
        "activo": False,
        "pago_confirmado": False,
        "perfil": {
            "origen_registro": "hotmart_webhook",
            "velox_password_temp": True,
            "velox_password_configured": False,
        },
    }
    try:
        result = bridge.supabase.table("users").insert(data).execute()
        if result.data:
            return True, "usuario_creado"
        return False, "No se pudo crear el usuario"
    except Exception as exc:
        return False, f"Error creando usuario: {exc}"


def process_hotmart_webhook(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Procesa el JSON de Hotmart y activa permisos en Supabase.
    Retorna (ok, mensaje).
    """
    event = str(payload.get("event") or "").strip().upper()
    if event and event not in HOTMART_EVENTS_ACTIVAR:
        logger.info("Evento Hotmart ignorado: %s", event)
        return True, f"evento_ignorado:{event}"

    email = _extraer_email(payload)
    if not email:
        return False, "Correo del comprador no encontrado en el payload"

    offer_info = _extraer_oferta(payload)
    price = ((payload.get("data") or {}).get("purchase") or {}).get("price") or {}
    offer_info["price"] = price

    buyer_name = ((payload.get("data") or {}).get("buyer") or {}).get("name")
    bridge = HotmartPaymentBridge()

    ok_user, msg_user = _asegurar_usuario(bridge, email, buyer_name)
    if not ok_user:
        return False, msg_user

    cursos = _cursos_desde_oferta(offer_info)
    if cursos:
        ok_act, msg_act = bridge._aplicar_cursos_aprobados_a_usuario(email, cursos)
    else:
        ok_act, msg_act = bridge._activar_usuario_pago(email)

    if not ok_act:
        return False, msg_act

    _registrar_comprobante_hotmart(bridge, email, offer_info, cursos)
    logger.info(
        "Hotmart OK email=%s offer=%s cursos=%s txn=%s",
        email,
        offer_info.get("code") or offer_info.get("name"),
        cursos or "acceso_completo",
        offer_info.get("transaction"),
    )
    return True, "ok"
