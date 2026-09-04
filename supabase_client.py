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


def _build_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase_server() -> Client:
    """Cliente Supabase para procesos sin runtime Streamlit (p. ej. webhooks FastAPI)."""
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL y SUPABASE_KEY deben estar definidos en variables de entorno."
        )
    return _build_supabase_client(url, key)


@st.cache_resource
def get_supabase() -> Client:
    url, key = _resolve_supabase_credentials()
    return _build_supabase_client(url, key)
