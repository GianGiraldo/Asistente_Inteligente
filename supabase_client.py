import os

import streamlit as st
from supabase import Client, create_client


def _normalize_supabase_url(url: str) -> str:
    """Acepta https://xxx.supabase.co o https://xxx.supabase.co/rest/v1 sin duplicar path."""
    normalized = (url or "").strip().rstrip("/")
    suffix = "/rest/v1"
    while normalized.endswith(suffix):
        normalized = normalized[: -len(suffix)].rstrip("/")
    return normalized


def _resolve_supabase_url() -> str:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    if url:
        return _normalize_supabase_url(url)
    try:
        cfg = st.secrets["supabase"]
        raw = cfg.get("url") if hasattr(cfg, "get") else getattr(cfg, "url", "")
        return _normalize_supabase_url(str(raw or "").strip())
    except Exception:
        return ""


def _resolve_supabase_anon_key() -> str:
    """Clave anon/public para OAuth y sesión de usuario en Streamlit."""
    key = (os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
    if key:
        return key
    try:
        cfg = st.secrets["supabase"]
        raw = cfg.get("key") if hasattr(cfg, "get") else getattr(cfg, "key", "")
        return str(raw or "").strip()
    except Exception:
        return ""


def _resolve_supabase_service_key() -> str:
    """Clave service_role — bypass RLS para cobranzas/comprobantes (server-side)."""
    for env_name in ("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY"):
        key = (os.getenv(env_name) or "").strip()
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
    return ""


def _resolve_supabase_credentials() -> tuple[str, str]:
    return _resolve_supabase_url(), _resolve_supabase_anon_key()


def get_supabase_service_credentials() -> tuple[str, str]:
    """URL + service_role para REST/Storage sin JWT de usuario (pagos, webhooks)."""
    url = _resolve_supabase_url()
    key = _resolve_supabase_service_key()
    if not url or not key:
        raise RuntimeError(
            "Configura SUPABASE_URL y SUPABASE_SERVICE_KEY (service_role) en Cloud Run o secrets.toml."
        )
    return url, key


def _build_supabase_client(url: str, key: str) -> Client:
    return create_client(_normalize_supabase_url(url), key)


def get_supabase_server() -> Client:
    """Cliente Supabase para procesos sin runtime Streamlit (p. ej. webhooks FastAPI)."""
    url, key = get_supabase_service_credentials()
    return _build_supabase_client(url, key)


@st.cache_resource
def get_supabase() -> Client:
    url, key = _resolve_supabase_credentials()
    return _build_supabase_client(url, key)


@st.cache_resource
def get_supabase_admin() -> Client:
    """Cliente Supabase service_role sin sesión de usuario."""
    url, key = get_supabase_service_credentials()
    client = _build_supabase_client(url, key)
    try:
        client.auth.sign_out()
    except Exception:
        pass
    return client
