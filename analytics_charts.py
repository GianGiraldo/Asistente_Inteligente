"""Gráficos Plotly ejecutivos para el dashboard veloX."""
from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

EXECUTIVE_PALETTE = ["#1e3a5f", "#2563eb", "#0ea5e9", "#10b981", "#6366f1", "#64748b"]
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#334155"),
    margin=dict(l=24, r=24, t=48, b=24),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hoverlabel=dict(bgcolor="#0f172a", font_size=12, font_family="Inter"),
)


def _apply_layout(fig, title: str, height: int = 340):
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=16, color="#0f172a")), height=height, **PLOTLY_LAYOUT)
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,0.2)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.2)", zeroline=False)
    return fig


def chart_documentos_por_seccion(publicaciones: List[dict], secciones: Dict) -> go.Figure:
    counts = {}
    for pub in publicaciones or []:
        sec = pub.get("seccion", "otros")
        counts[sec] = counts.get(sec, 0) + 1
    if not counts:
        counts = {k: 0 for k in secciones.keys()}
    labels = [secciones.get(k, {}).get("nombre", k.replace("_", " ").title()) for k in counts.keys()]
    df = pd.DataFrame({"Sección": labels, "Documentos": list(counts.values())})
    fig = px.bar(
        df, x="Sección", y="Documentos", color="Documentos",
        color_continuous_scale=["#cbd5e1", "#1e3a5f"],
        text="Documentos",
    )
    fig.update_traces(textposition="outside", hovertemplate="<b>%{x}</b><br>Documentos: %{y}<extra></extra>")
    return _apply_layout(fig, "Distribución documental por área")


def chart_acceso_usuarios(usuarios: Dict) -> go.Figure:
    activos = sum(1 for u in usuarios.values() if u.get("activo") and u.get("pago_confirmado"))
    pendientes = sum(1 for u in usuarios.values() if not u.get("activo") or not u.get("pago_confirmado"))
    df = pd.DataFrame({"Estado": ["Activos", "Pendientes / Inactivos"], "Usuarios": [activos, pendientes]})
    fig = px.pie(df, names="Estado", values="Usuarios", hole=0.55, color="Estado", color_discrete_sequence=["#10b981", "#94a3b8"])
    fig.update_traces(hovertemplate="<b>%{label}</b><br>%{value} usuarios (%{percent})<extra></extra>")
    return _apply_layout(fig, "Estado de suscripciones", height=320)


def chart_cobranzas_pendientes(pagos: List[dict]) -> go.Figure:
    if not pagos:
        df = pd.DataFrame({"Método": ["Sin pendientes"], "Solicitudes": [0]})
    else:
        agrupado = {}
        for p in pagos:
            m = (p.get("metodo_pago") or "yape_plim").replace("_", " ").upper()
            agrupado[m] = agrupado.get(m, 0) + 1
        df = pd.DataFrame({"Método": list(agrupado.keys()), "Solicitudes": list(agrupado.values())})
    fig = px.bar(df, x="Método", y="Solicitudes", color="Método", color_discrete_sequence=EXECUTIVE_PALETTE, text="Solicitudes")
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Solicitudes: %{y}<extra></extra>")
    return _apply_layout(fig, "Pagos manuales pendientes de revisión", height=300)


def chart_actividad_secciones_usuario(secciones_usuario: List[str], secciones: Dict, publicaciones: List[dict]) -> go.Figure:
    data = []
    for sec in secciones_usuario:
        if sec not in secciones:
            continue
        n = len([p for p in publicaciones if p.get("seccion") == sec])
        data.append({"Sección": secciones[sec]["nombre"], "Recursos": n})
    if not data:
        data = [{"Sección": "Sin asignación", "Recursos": 0}]
    df = pd.DataFrame(data)
    fig = px.bar(df, x="Recursos", y="Sección", orientation="h", color="Recursos", color_continuous_scale=["#e2e8f0", "#2563eb"], text="Recursos")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>Recursos: %{x}<extra></extra>")
    return _apply_layout(fig, "Recursos disponibles en tus secciones", height=320)
