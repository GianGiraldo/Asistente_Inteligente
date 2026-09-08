import os

import streamlit as st
from supabase import Client, create_client


def _resolve_supabase_credentials() -> tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_KEY") or "").strip()
    if url and key:
        return url, key

    cfg = st.secrets["supabase"]
    if not url:
        url = str(cfg.get("url") if hasattr(cfg, "get") else getattr(cfg, "url", "")).strip()
    if not key:
        key = str(cfg.get("key") if hasattr(cfg, "get") else getattr(cfg, "key", "")).strip()
    return url, key


def _normalize_supabase_url(url: str) -> str:
    """Acepta https://xxx.supabase.co o https://xxx.supabase.co/rest/v1 sin duplicar path."""
    normalized = (url or "").strip().rstrip("/")
    suffix = "/rest/v1"
    while normalized.endswith(suffix):
        normalized = normalized[: -len(suffix)].rstrip("/")
    return normalized


def _build_supabase_client(url: str, key: str) -> Client:
    return create_client(_normalize_supabase_url(url), key)


def get_supabase_server() -> Client:
    """Cliente Supabase para procesos sin runtime Streamlit (p. ej. webhooks FastAPI)."""
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL y SUPABASE_KEY deben estar definidos en variables de entorno."
        )
    return _build_supabase_client(url, key)


def _resolve_supabase_service_key() -> str:
    """Clave service_role para operaciones server-side (sin RLS de sesión de usuario)."""
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if key:
        return key
    try:
        cfg = st.secrets["supabase"]
        for name in ("service_key", "service_role", "service_role_key"):
            raw = cfg.get(name) if hasattr(cfg, "get") else getattr(cfg, name, None)
            if raw:
                return str(raw).strip()
    except Exception:
        pass
    _, fallback = _resolve_supabase_credentials()
    return fallback


@st.cache_resource
def get_supabase() -> Client:
    url, key = _resolve_supabase_credentials()
    return _build_supabase_client(url, key)


@st.cache_resource
def get_supabase_admin() -> Client:
    """Cliente Supabase sin sesión de usuario (service_role) para escrituras server-side."""
    url, _ = _resolve_supabase_credentials()
    service_key = _resolve_supabase_service_key()
    return _build_supabase_client(url, service_key)
