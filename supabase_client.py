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


@st.cache_resource
def get_supabase() -> Client:
    url, key = _resolve_supabase_credentials()
    try:
        from supabase.lib.client_options import ClientOptions

        return create_client(
            url,
            key,
            options=ClientOptions(flow_type="pkce"),
        )
    except Exception:
        return create_client(url, key)
