import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    try:
        from supabase.lib.client_options import ClientOptions

        return create_client(
            url,
            key,
            options=ClientOptions(flow_type="pkce"),
        )
    except Exception:
        return create_client(url, key)
