"""Tema visual Executive / Business Hub para veloX."""

VELOX_MAIN_BG = "#F8F9FA"
VELOX_MAIN_CONTAINER_BG = "#FFFFFF"

MAIN_CONTENT_AREA_CSS = f"""
<style>
    /* Área central (catálogo, inicio, contenido): fondo claro — NO afecta st.sidebar */
    [data-testid="stAppViewContainer"] > section[data-testid="stMain"],
    [data-testid="stAppViewContainer"] > section[data-testid="stMain"] > div,
    [data-testid="stMain"],
    [data-testid="stMain"] > div,
    section.main,
    section.main > div {{
        background-color: {VELOX_MAIN_BG} !important;
    }}
    [data-testid="stMainBlockContainer"],
    .main .block-container {{
        background-color: {VELOX_MAIN_CONTAINER_BG} !important;
        padding-left: 1rem !important;
        padding-right: 1.25rem !important;
    }}
    [data-testid="stAppViewContainer"] > section[data-testid="stMain"] {{
        padding-top: 0 !important;
    }}
    [data-testid="stMain"] > div:first-child {{
        padding-top: 0 !important;
    }}
    /* Contraste de texto en zona central */
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    section.main h1,
    section.main h2,
    section.main h3,
    section.main h4 {{
        color: #0f172a !important;
    }}
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stMain"] [data-testid="stCaptionContainer"],
    section.main [data-testid="stMarkdownContainer"] p {{
        color: #334155 !important;
    }}
    [data-testid="stMain"] [data-testid="stHeader"],
    section.main [data-testid="stHeader"] {{
        color: #0f172a !important;
    }}

    /* ==========================================================================
       REFINAMIENTO QUIRÚRGICO DE ESTILOS - PLATAFORMA VELOX
       ========================================================================== */

    /* 2. Botones secundarios en formularios (p. ej. Guardar cambios) */
    [data-testid="stMain"] button[data-testid="baseButton-secondary"] span,
    [data-testid="stMain"] button[data-testid="baseButton-secondary"] p,
    [data-testid="stMain"] .stButton > button[data-testid="baseButton-secondary"] * {{
        color: #1E293B !important;
        font-weight: 600 !important;
        text-shadow: none !important;
    }}

    /* 1. Catálogo: botones oscuros legibles (primary + secondary del grid) */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button,
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.velox-section-grid) .stButton > button *,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] .stButton > button,
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-section-grid) ~ [data-testid="element-container"] .stButton > button * {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    /* 3. Pestañas st.tabs (Gestión de Usuarios y similares) */
    [data-testid="stMain"] [data-testid="stTabBar"] button,
    [data-testid="stMain"] [data-testid="stTabBar"] button p,
    [data-testid="stMain"] [data-testid="stTabBar"] button span,
    [data-testid="stMain"] [data-testid="stTabBar"] p,
    [data-testid="stMain"] [data-testid="stTabs"] button,
    [data-testid="stMain"] [data-testid="stTabs"] button p,
    [data-testid="stMain"] [data-testid="stTabs"] button span,
    [data-testid="stMain"] [data-baseweb="tab-list"] button,
    [data-testid="stMain"] [data-baseweb="tab-list"] button span {{
        color: #334155 !important;
        font-weight: 600 !important;
        text-shadow: none !important;
    }}

    /* 4. Enlaces informativos de login y markdown */
    .stApp [data-testid="stMarkdownContainer"] a,
    .stApp [data-testid="stMarkdownContainer"] p a,
    .stApp a[href*="olvidaste"] span {{
        color: #0284C7 !important;
        text-decoration: underline !important;
    }}
    .stApp:has(.velox-id-bar) .st-key-btn_olvido_password .stButton > button,
    .stApp:has(.velox-id-bar) .st-key-btn_olvido_password .stButton > button * {{
        color: #C41E3A !important;
        font-weight: 500 !important;
        text-shadow: none !important;
    }}

    /* ==========================================================================
       ELIMINACIÓN DE BOTÓN REDUNDANTE "VOLVER AL DASHBOARD"
       ========================================================================== */
    [data-testid="stMain"] .st-key-btn_volver_dashboard,
    [data-testid="stMain"] [data-testid="element-container"].st-key-btn_volver_dashboard {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
        border: none !important;
    }}

    /* ==========================================================================
       ESTILIZACIÓN EDUCATIVA Y PROFESIONAL PARA BOTONES DE CATEGORÍA
       (Minicursos / Formatos y Plantillas — contenedor st-key-velox_categoria_botones)
       ========================================================================== */

    /* 1. Reposo / no seleccionado (secondary) */
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-secondary"],
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[kind="secondary"] {{
        background-color: #F1F5F9 !important;
        color: #475569 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    }}
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-secondary"] *,
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[kind="secondary"] * {{
        color: #475569 !important;
        font-weight: 500 !important;
        text-shadow: none !important;
    }}

    /* Hover */
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-secondary"]:hover,
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[kind="secondary"]:hover {{
        background-color: #E2E8F0 !important;
        color: #1E293B !important;
        border-color: #CBD5E1 !important;
        cursor: pointer;
    }}
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-secondary"]:hover *,
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[kind="secondary"]:hover * {{
        color: #1E293B !important;
        font-weight: 600 !important;
    }}

    /* 2. Activo / seleccionado (primary) */
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-primary"],
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[kind="primary"] {{
        background-color: #E0F2FE !important;
        color: #0369A1 !important;
        border: 2px solid #0EA5E9 !important;
        border-radius: 12px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.15) !important;
    }}
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-primary"] *,
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[kind="primary"] * {{
        color: #0369A1 !important;
        font-weight: 700 !important;
        text-shadow: none !important;
    }}

    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-primary"]:hover,
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[kind="primary"]:hover {{
        background-color: #BAE6FD !important;
        border-color: #0284C7 !important;
    }}
    [data-testid="stMain"] .st-key-velox_categoria_botones .stButton > button[data-testid="baseButton-primary"]:hover * {{
        color: #0C4A6E !important;
    }}
</style>
"""

VELOX_ULTRA_COMPACT_LAYOUT_CSS = """
<style>
    /* —— Área central: pegada al tope —— */
    [data-testid="stMainBlockContainer"],
    section.main .block-container,
    .main .block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    /* Ocultar decoración; toolbar solo cuando el sidebar está expandido (ver bloque toggle) */
    [data-testid="stDecoration"],
    .stDecoration {
        display: none !important;
        height: 0 !important;
    }
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="true"]) [data-testid="stToolbar"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    [data-testid="stAppViewContainer"] > section[data-testid="stMain"] {
        padding-top: 0 !important;
    }
    /* Post-login: sidebar sobre fondo; main sin desbordar horizontalmente */
    .stApp:not(:has(.velox-id-bar)) [data-testid="stAppViewContainer"] > section[data-testid="stMain"] {
        z-index: 1 !important;
    }
    .stApp:not(:has(.velox-id-bar)) section[data-testid="stSidebar"] {
        z-index: 100 !important;
        position: relative !important;
    }
    [data-testid="stMain"] [data-testid="stImage"] {
        margin-bottom: 0 !important;
    }
    [data-testid="stMain"] [data-testid="stElementContainer"] {
        margin-bottom: 0.15rem !important;
    }
    [data-testid="stMain"] [data-testid="stHeading"] {
        margin-top: 0.15rem !important;
        margin-bottom: 0.25rem !important;
        padding-top: 0 !important;
    }
    [data-testid="stMain"] hr {
        margin: 0.15rem 0 0.35rem !important;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        gap: 0.35rem !important;
    }
    /* —— Sidebar: pegado al tope —— */
    [data-testid="stSidebarUserContent"] {
        padding-top: 0rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding-top: 0rem !important;
    }
    [data-testid="stSidebar"] .sidebar-brand {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* --- TOGGLE SIDEBAR POST-LOGIN (Streamlit 1.54+: stExpandSidebarButton en stToolbar) --- */

    /* Sidebar colapsada: mostrar header/toolbar nativos (contienen el botón reabrir) */
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stHeader"],
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stToolbar"],
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stHeader"] > div {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        overflow: visible !important;
        pointer-events: auto !important;
    }

    /* Contenedores del botón (legacy + Streamlit 1.54) */
    .stApp:not(:has(.velox-id-bar)) [data-testid="stSidebarCollapse"],
    .stApp:not(:has(.velox-id-bar)) div:has(> [data-testid="collapsedControl"]),
    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] [data-testid="stSidebarCollapse"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="stToolbar"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] > div:has([data-testid="stExpandSidebarButton"]) {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    /* Botón flotante reabrir — Streamlit 1.54 (stExpandSidebarButton) + legacy (collapsedControl) */
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"],
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stHeader"] > div:has([data-testid="stExpandSidebarButton"]),
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stToolbar"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="collapsedControl"],
    .stApp:not(:has(.velox-id-bar)) div:has(> [data-testid="collapsedControl"]),
    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] [data-testid="stSidebarCollapse"] {
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        z-index: 9999999 !important;
        width: 42px !important;
        height: 42px !important;
        min-width: 42px !important;
        min-height: 42px !important;
        margin: 0 !important;
        padding: 0 !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Estilo cyan corporativo — botón reabrir (Streamlit 1.54) */
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        z-index: 9999999 !important;
        pointer-events: auto !important;
        width: 42px !important;
        height: 42px !important;
        min-width: 42px !important;
        min-height: 42px !important;
        background-color: #0F3D3C !important;
        border: 2px solid #00E5FF !important;
        border-radius: 6px !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"] svg,
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
        fill: #00E5FF !important;
        color: #00E5FF !important;
        width: 22px !important;
        height: 22px !important;
    }

    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"]:hover {
        background-color: #00E5FF !important;
        border-color: #ffffff !important;
    }

    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"]:hover svg,
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"]:hover [data-testid="stIconMaterial"] {
        fill: #0F3D3C !important;
        color: #0F3D3C !important;
    }

    /* Legacy collapsedControl (Streamlit < 1.54) */
    .stApp:not(:has(.velox-id-bar)) [data-testid="collapsedControl"] {
        background-color: #0F3D3C !important;
        border: 2px solid #00E5FF !important;
        border-radius: 6px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 42px !important;
        height: 42px !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        cursor: pointer !important;
    }

    .stApp:not(:has(.velox-id-bar)) [data-testid="collapsedControl"] button,
    .stApp:not(:has(.velox-id-bar)) [data-testid="stExpandSidebarButton"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="stSidebarCollapse"] button,
    .stApp:not(:has(.velox-id-bar)) [data-testid="stSidebarCollapseButton"] {
        display: block !important;
        width: 100% !important;
        height: 100% !important;
        min-width: 0 !important;
        min-height: 0 !important;
        background: transparent !important;
        border: none !important;
        cursor: pointer !important;
        pointer-events: auto !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    .stApp:not(:has(.velox-id-bar)) [data-testid="collapsedControl"] svg {
        fill: #00E5FF !important;
        color: #00E5FF !important;
        width: 22px !important;
        height: 22px !important;
        pointer-events: none !important;
    }

    .stApp:not(:has(.velox-id-bar)) [data-testid="collapsedControl"]:hover {
        background-color: #00E5FF !important;
        border-color: #ffffff !important;
    }

    .stApp:not(:has(.velox-id-bar)) [data-testid="collapsedControl"]:hover svg {
        fill: #0F3D3C !important;
        color: #0F3D3C !important;
    }

    /* Chevron « colapsar » dentro del sidebar expandido */
    .stApp:not(:has(.velox-id-bar)) section[data-testid="stSidebar"] [data-testid="stSidebarCollapse"],
    .stApp:not(:has(.velox-id-bar)) section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: relative !important;
        top: auto !important;
        left: auto !important;
        z-index: 101 !important;
        width: auto !important;
        height: auto !important;
        min-width: 0 !important;
        min-height: 0 !important;
    }

    /* Header: altura cero cuando sidebar abierto; visible al colapsar */
    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="true"]) [data-testid="stHeader"] {
        background-color: transparent !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: visible !important;
        pointer-events: none !important;
        z-index: 9999998 !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
    }

    .stApp:not(:has(.velox-id-bar)):has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stHeader"] {
        background-color: transparent !important;
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
        overflow: visible !important;
        pointer-events: none !important;
        position: relative !important;
        z-index: 9999998 !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
    }

    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] [data-testid="stSidebarCollapse"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] [data-testid="collapsedControl"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] div:has(> [data-testid="collapsedControl"]),
    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] [data-testid="stExpandSidebarButton"],
    .stApp:not(:has(.velox-id-bar)) [data-testid="stHeader"] > div:has([data-testid="stExpandSidebarButton"]) {
        pointer-events: auto !important;
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
</style>
"""

EXECUTIVE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp {
        background-color: #F8F9FA;
    }
    .velox-hero {
        text-align: center; padding: 1.5rem 1rem 0.5rem;
    }
    .velox-hero h1 {
        font-size: 1.85rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;
    }
    .velox-hero p { color: #475569; font-size: 0.95rem; }
    .velox-welcome-brand {
        text-align: center;
        padding: 2rem 1rem 1.25rem;
    }
    .velox-welcome-brand img {
        display: block;
        margin: 0 auto 1rem auto;
    }
    .velox-welcome-brand [data-testid="stImage"] {
        display: flex;
        justify-content: center;
        width: 100%;
    }
    .velox-welcome-brand [data-testid="stImage"] img {
        margin: 0 auto;
    }
    .velox-logo-fallback {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a5f;
        margin-bottom: 0.75rem;
    }
    .velox-tagline {
        color: #475569;
        font-size: 1.05rem;
        line-height: 1.55;
        max-width: 520px;
        margin: 0 auto;
        font-weight: 500;
    }
    .velox-gateway-shell {
        background: rgba(255,255,255,0.96);
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 1.5rem 1.75rem 1.75rem;
        box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
    }
    .velox-welcome-tabs .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f1f5f9;
        border-radius: 12px;
        padding: 6px;
    }
    .velox-welcome-tabs .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: 600;
        color: #475569;
        padding: 0.45rem 0.85rem;
    }
    .velox-welcome-tabs .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #1e3a5f !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
    }
    .velox-section-title {
        color: #1e293b;
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .velox-section-caption {
        color: #64748b;
        font-size: 0.88rem;
        margin-bottom: 1rem;
    }
    .velox-identity-badge {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        color: #065f46;
        border-radius: 10px;
        padding: 0.65rem 0.85rem;
        font-size: 0.88rem;
        margin-bottom: 1rem;
    }
    .velox-divider-or {
        display: flex;
        align-items: center;
        text-align: center;
        margin: 1.35rem 0 1.1rem;
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 500;
    }
    .velox-divider-or::before,
    .velox-divider-or::after {
        content: "";
        flex: 1;
        border-bottom: 1px solid #e2e8f0;
    }
    .velox-divider-or span {
        padding: 0 14px;
        white-space: nowrap;
    }
    .velox-activation-banner {
        background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        color: #1e3a5f;
        font-size: 0.9rem;
        line-height: 1.5;
        margin-bottom: 1.25rem;
        text-align: center;
    }
    .velox-activation-banner strong { color: #0f172a; font-weight: 600; }
    .velox-activation-banner em { font-style: normal; font-weight: 600; color: #2563eb; }
    .velox-step-label {
        display: inline-block;
        background: #f1f5f9;
        color: #475569;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 999px;
        margin-bottom: 0.5rem;
    }
    .velox-qr-panel {
        background: linear-gradient(160deg, #faf5ff 0%, #f3e8ff 45%, #ffffff 100%);
        border: 1px solid #e9d5ff;
        border-radius: 14px;
        padding: 0.25rem;
    }
    .velox-logout-link button {
        background: transparent !important;
        color: #64748b !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: none !important;
        font-size: 0.82rem !important;
        padding: 0.35rem 0.75rem !important;
        min-height: auto !important;
    }
    .velox-tab-selector [data-testid="stHorizontalBlock"] {
        gap: 0.5rem;
    }
    .velox-tab-selector .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    .velox-register-cta .stButton > button {
        background: transparent !important;
        color: #2563eb !important;
        border: 1px dashed #bfdbfe !important;
        box-shadow: none !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
    }
    .velox-register-cta .stButton > button:hover {
        background: #eff6ff !important;
        border-color: #93c5fd !important;
    }
    .velox-login-bottom {
        margin-top: 0.25rem;
    }
    /* —— Portal de acceso veloX (portada profesional) —— */
    .velox-portal-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 0 0 1.75rem;
        box-shadow: 0 8px 32px rgba(15, 23, 42, 0.07);
        overflow: hidden;
    }
    .velox-id-bar {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        color: #f1f5f9;
        text-align: center;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 0.72rem 1rem;
        margin: 0 0 1.35rem 0;
        border-bottom: 1px solid #334155;
    }
    .velox-id-bar--register {
        background: linear-gradient(180deg, #1e3a5f 0%, #152a45 100%);
    }
    .velox-portal-body {
        padding: 0 1.75rem;
    }
    .velox-portal-nav {
        display: none;
    }
    .velox-nav-tab-label {
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        color: #64748b;
        text-transform: uppercase;
        padding-bottom: 0.55rem;
        border-bottom: 3px solid transparent;
    }
    .velox-nav-tab-active {
        color: #1e293b;
        border-bottom-color: #f97316;
    }
    .velox-portal-form .stTextInput > div > div > input {
        border-radius: 10px !important;
        border: 1px solid #d1d5db !important;
        padding: 0.72rem 0.9rem !important;
        font-size: 0.95rem !important;
        background: #ffffff !important;
    }
    .velox-portal-form .stTextInput > div > div > input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    }
    .velox-portal-form .stCheckbox label span {
        font-size: 0.88rem !important;
        color: #475569 !important;
    }
    .velox-portal-form [data-testid="stToggle"] label span {
        font-size: 0.88rem !important;
        color: #475569 !important;
    }
    .velox-portal-form [data-testid="stToggle"] [data-baseweb="checkbox"] {
        background-color: #f97316 !important;
    }
    .velox-portal-actions {
        margin-top: 1.15rem;
    }
    .velox-portal-actions .google-btn-wrap a {
        display: flex !important;
        align-items: center;
        justify-content: center;
        gap: 10px;
        width: 100%;
        min-height: 2.75rem;
        padding: 0.72rem 1rem !important;
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        text-decoration: none !important;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.28) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .velox-portal-actions .google-btn-wrap a:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.34) !important;
    }
    .velox-btn-premium .stButton > button {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 0.72rem 1rem !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        min-height: 2.75rem !important;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.28) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .velox-btn-premium .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.34) !important;
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
    }
    .velox-back-login .stButton > button {
        background: transparent !important;
        color: #475569 !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 0.82rem !important;
        padding: 0.25rem 0 !important;
        min-height: auto !important;
    }
    .velox-btn-primary .stButton > button {
        background: linear-gradient(180deg, #1e3a5f 0%, #152a45 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.72rem 1rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 4px 14px rgba(30, 58, 95, 0.25) !important;
    }
    .velox-btn-primary .stButton > button:hover {
        background: linear-gradient(180deg, #234e7d 0%, #1a3352 100%) !important;
    }
    .velox-btn-secondary .stButton > button {
        background: linear-gradient(180deg, #1e3a5f 0%, #152a45 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.72rem 1rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    .velox-btn-nav-registro .stButton > button {
        background: #1e3a5f !important;
        color: #fff !important;
        border-radius: 8px !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        padding: 0.45rem 0.75rem !important;
        min-height: auto !important;
    }
    .velox-btn-nav-registro-off .stButton > button {
        background: #f1f5f9 !important;
        color: #475569 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
    }
    .st-key-btn_olvido_password {
        display: flex !important;
        justify-content: flex-end !important;
        width: 100% !important;
    }
    .st-key-btn_olvido_password .stButton > button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #C41E3A !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        text-decoration: underline !important;
        padding: 0 !important;
        min-height: auto !important;
        width: auto !important;
    }
    .st-key-btn_olvido_password .stButton > button:hover {
        color: #9B1830 !important;
        background: transparent !important;
    }
    .velox-register-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.25rem;
    }
    .velox-register-sub {
        color: #64748b;
        font-size: 0.88rem;
        margin-bottom: 1.25rem;
    }
    .velox-portal-register-row {
        margin-top: 0.35rem;
        padding-top: 0.85rem;
        border-top: 1px solid #e8eef5;
    }
    .velox-register-success {
        text-align: center;
        padding: 1.75rem 1.25rem 1.25rem;
        background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
        border: 1px solid #bbf7d0;
        border-radius: 16px;
        margin: 0.5rem 0 1.25rem;
    }
    .velox-register-success__icon {
        font-size: 2.5rem;
        line-height: 1;
        margin-bottom: 0.75rem;
    }
    .velox-register-success__title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #14532d;
        margin-bottom: 0.65rem;
    }
    .velox-register-success__text {
        color: #334155;
        font-size: 0.92rem;
        line-height: 1.55;
        max-width: 34rem;
        margin: 0 auto;
    }
    .velox-nav-correo-btn .stButton > button {
        background: transparent !important;
        color: #64748b !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        padding: 0 0 0.55rem 0 !important;
        min-height: auto !important;
    }
    .velox-nav-correo-btn .stButton > button:hover {
        color: #1e293b !important;
    }
    .welcome-hide-sidebar [data-testid="stSidebar"] {
        display: none;
    }
    .welcome-hide-sidebar [data-testid="stAppViewContainer"] > section {
        max-width: 100%;
    }
    .executive-card {
        background: rgba(255,255,255,0.92);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
    }
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dce5f0;
        border-radius: 16px;
        padding: 1rem;
        color: #1e2a3e;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    }
    .metric-card h3 { color: #1e3a5f; margin: 0; font-size: 1.75rem; font-weight: 700; }
    .metric-card p { color: #64748b; margin: 0; font-size: 0.85rem; }
    .paywall-badge {
        display: inline-block;
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #e2e8f0;
        padding: 6px 14px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600;
    }
    .google-btn-wrap a {
        display: inline-flex; align-items: center; justify-content: center; gap: 10px;
        width: 100%; padding: 0.75rem 1rem; background: #fff; color: #1f2937;
        border: 1px solid #dadce0; border-radius: 10px; font-weight: 600;
        text-decoration: none; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: box-shadow 0.2s;
    }
    .google-btn-wrap a:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
    .sidebar-profile {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .sidebar-profile-email { font-size: 0.78rem; color: #cbd5e1; word-break: break-all; }
    [data-testid="stSidebar"] .stButton > button {
        border-radius: 14px !important;
        transition: all 0.3s ease !important;
    }
    /* —— Catálogo freemium de secciones (colores sidebar #0f172a / #1e293b) —— */
    .velox-section-grid { margin-bottom: 0.15rem; }
    .velox-section-card {
        border-radius: 16px;
        padding: 1.15rem 1.2rem;
        min-height: 148px;
        margin-bottom: 0.4rem;
        position: relative;
        overflow: hidden;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .velox-section-card--active {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        color: #FFFFFF;
        box-shadow: 0 8px 26px rgba(15, 23, 42, 0.24);
    }
    .velox-section-card--active:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 32px rgba(15, 23, 42, 0.3);
    }
    .velox-section-card--locked {
        background: #FFFFFF !important;
        border: 1px dashed #94a3b8;
        color: #475569;
        opacity: 1;
        filter: none;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.07);
    }
    .velox-section-card__watermark {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-16deg);
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: 0.14em;
        color: rgba(100, 116, 139, 0.2);
        pointer-events: none;
        user-select: none;
    }
    .velox-section-card__title {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.35rem;
        line-height: 1.3;
    }
    .velox-section-card--active .velox-section-card__title { color: #FFFFFF; }
    .velox-section-card--locked .velox-section-card__title { color: #475569; }
    .velox-section-card__desc {
        font-size: 0.82rem;
        line-height: 1.45;
        opacity: 0.92;
    }
    .velox-section-card--active .velox-section-card__desc,
    .velox-section-card--active .velox-section-card__meta { color: #FFFFFF; }
    .velox-section-card__meta {
        font-size: 0.78rem;
        margin-top: 0.7rem;
        font-weight: 600;
        opacity: 0.88;
    }
    .velox-section-grid .stButton > button {
        border-radius: 14px !important;
        font-weight: 600 !important;
        min-height: 2.65rem !important;
    }
    .velox-section-grid .stButton > button[kind="primary"],
    .velox-section-grid .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border: 1px solid #334155 !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.2) !important;
    }
    .velox-section-grid .stButton > button[kind="primary"] p,
    .velox-section-grid .stButton > button[kind="primary"] span,
    .velox-section-grid .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"],
    .velox-section-grid .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] p,
    .velox-section-grid .stButton > button[data-testid="baseButton-primary"] p,
    .velox-section-grid .stButton > button[data-testid="baseButton-primary"] span,
    .velox-section-grid .stButton > button[data-testid="baseButton-primary"] [data-testid="stMarkdownContainer"],
    .velox-section-grid .stButton > button[data-testid="baseButton-primary"] [data-testid="stMarkdownContainer"] p,
    .velox-section-grid .stButton > button[kind="secondary"] p,
    .velox-section-grid .stButton > button[kind="secondary"] span,
    .velox-section-grid .stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"],
    .velox-section-grid .stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"] p,
    .velox-section-grid .stButton > button[data-testid="baseButton-secondary"] p,
    .velox-section-grid .stButton > button[data-testid="baseButton-secondary"] span,
    .velox-section-grid .stButton > button[data-testid="baseButton-secondary"] [data-testid="stMarkdownContainer"],
    .velox-section-grid .stButton > button[data-testid="baseButton-secondary"] [data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.2) !important;
    }
    .velox-section-grid .stButton > button[kind="secondary"],
    .velox-section-grid .stButton > button[data-testid="baseButton-secondary"] {
        background: rgba(241, 245, 249, 0.85) !important;
        color: #334155 !important;
        border: 1px dashed #94a3b8 !important;
    }
</style>
"""

SIDEBAR_CSS = """
<style>
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #4a70a8 0%, #456ba0 100%) !important;
        border-right: 1px solid #3d5f8f;
        z-index: 100 !important;
        position: relative !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #f8fafc !important;
    }

    [data-testid="stSidebar"] .stMarkdown:not(.sidebar-profile .stMarkdown) {
        color: #f8fafc !important;
    }

    .sidebar-brand {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        width: 100%;
        padding: 0 8px 10px;
        margin-top: 0;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.28);
    }

    .sidebar-brand-logo {
        display: block;
        margin: 0 auto;
        max-width: 112px;
        width: 100%;
        height: auto;
        object-fit: contain;
        filter: drop-shadow(0 2px 8px rgba(15, 23, 42, 0.18));
    }

    .sidebar-brand [data-testid="stElementContainer"],
    .sidebar-brand [data-testid="stImage"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        margin: 0 auto !important;
    }

    .sidebar-brand [data-testid="stImage"] img {
        display: block;
        margin: 0 auto;
        max-width: 112px;
        width: 100%;
        height: auto;
        object-fit: contain;
        filter: drop-shadow(0 2px 8px rgba(15, 23, 42, 0.18));
    }

    .sidebar-brand-fallback {
        font-size: 1.12rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        color: #ffffff;
    }

    .sidebar-profile {
        background: rgba(255, 255, 255, 0.92) !important;
        border: 1px solid rgba(255, 255, 255, 0.98) !important;
        border-radius: 14px !important;
        padding: 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.12) !important;
    }

    .sidebar-profile .stMarkdown,
    .sidebar-profile p,
    .sidebar-profile strong {
        color: #0f172a !important;
    }

    .sidebar-profile-email {
        font-size: 0.78rem !important;
        color: #475569 !important;
        word-break: break-all;
    }

    .sidebar-profile--compact {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 4px 8px 12px !important;
        margin-bottom: 8px !important;
        text-align: center !important;
    }

    .sidebar-profile--compact [data-testid="stImage"],
    .sidebar-profile--compact [data-testid="stElementContainer"]:has([data-testid="stImage"]) {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
        margin: 0 auto 0.35rem auto !important;
    }

    .sidebar-profile-email--hero {
        color: #FFFFFF !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        text-align: center !important;
        word-break: break-all;
        margin: 0.15rem 0 0.35rem !important;
        line-height: 1.35 !important;
        text-shadow: 0 1px 2px rgba(15, 23, 42, 0.35);
    }

    .sidebar-profile--compact [data-testid="stCaptionContainer"],
    .sidebar-profile--compact [data-testid="stCaptionContainer"] p {
        color: rgba(255, 255, 255, 0.92) !important;
        text-align: center !important;
    }

    /* Panel blanco exterior del menú de módulos */
    [data-testid="stSidebar"] .st-key-sidebar_menu_panel {
        background-color: #ffffff !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        padding: 6px 8px !important;
        margin: 6px 0 10px !important;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.1) !important;
        border: 1px solid rgba(226, 232, 240, 0.95) !important;
    }
    [data-testid="stSidebar"] .st-key-sidebar_menu_panel iframe {
        display: block !important;
        width: 100% !important;
        border: none !important;
        border-radius: 14px !important;
    }

    /* Menú option_menu — cápsulas redondeadas con hover suave */
    [data-testid="stSidebar"] .nav,
    [data-testid="stSidebar"] .nav-pills,
    [data-testid="stSidebar"] .navbar-nav {
        background: transparent !important;
        gap: 6px;
    }
    [data-testid="stSidebar"] .nav-item {
        border-radius: 12px !important;
        overflow: hidden;
        margin: 0 0 6px 0 !important;
    }
    [data-testid="stSidebar"] .nav-link:not(.nav-link-selected),
    [data-testid="stSidebar"] a.nav-link:not(.nav-link-selected) {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        flex-wrap: nowrap !important;
        white-space: nowrap !important;
        background-color: #F1F3F5 !important;
        color: #1a2744 !important;
        border-radius: 12px !important;
        border: 1px solid #E4E7EB !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
        font-weight: 600 !important;
        margin: 0 0 6px 0 !important;
        padding: 10px 12px !important;
        min-height: 2.65rem;
        line-height: 1.35 !important;
        text-align: left !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stSidebar"] .nav-link:not(.nav-link-selected):hover,
    [data-testid="stSidebar"] a.nav-link:not(.nav-link-selected):hover {
        background-color: #E4E8EE !important;
        color: #1a2744 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1) !important;
        border-color: #CBD5E1 !important;
    }

    [data-testid="stSidebar"] .nav-link-selected,
    [data-testid="stSidebar"] a.nav-link-selected {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        flex-wrap: nowrap !important;
        white-space: nowrap !important;
        background-color: #1a2744 !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        font-weight: 700 !important;
        margin: 0 0 6px 0 !important;
        padding: 10px 12px !important;
        text-align: left !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stSidebar"] .nav-link-selected:hover,
    [data-testid="stSidebar"] a.nav-link-selected:hover {
        background-color: #243556 !important;
        color: #ffffff !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28) !important;
    }

    [data-testid="stSidebar"] .nav-link .nav-icon,
    [data-testid="stSidebar"] .nav-link svg {
        color: #4a70a8 !important;
        fill: #4a70a8 !important;
        display: inline-flex !important;
        align-items: center !important;
        flex-shrink: 0 !important;
        margin-right: 0 !important;
    }

    [data-testid="stSidebar"] .nav-link-selected .nav-icon,
    [data-testid="stSidebar"] .nav-link-selected svg {
        color: #ffffff !important;
        fill: #ffffff !important;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.25));
        display: inline-flex !important;
        align-items: center !important;
        flex-shrink: 0 !important;
        margin-right: 0 !important;
    }

    [data-testid="stSidebar"] .nav-link p {
        font-weight: 600 !important;
        color: #1a2744 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        text-align: left !important;
        white-space: nowrap !important;
        flex: 1 1 auto !important;
        line-height: 1.2 !important;
    }

    [data-testid="stSidebar"] .nav-link-selected p {
        font-weight: 700 !important;
        color: #ffffff !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.22);
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        text-align: left !important;
        white-space: nowrap !important;
        flex: 1 1 auto !important;
        line-height: 1.2 !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: #ffffff !important;
        color: #1a2744 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08) !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 2.65rem !important;
    }

    [data-testid="stSidebar"] .stButton > button p {
        color: #1a2744 !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: #f1f5f9 !important;
        border-color: #cbd5e1 !important;
        color: #1a2744 !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.14) !important;
    }
</style>
"""


def inject_global_theme():
    import streamlit as st
    st.markdown(EXECUTIVE_CSS, unsafe_allow_html=True)
    st.markdown(MAIN_CONTENT_AREA_CSS, unsafe_allow_html=True)
    st.markdown(VELOX_ULTRA_COMPACT_LAYOUT_CSS, unsafe_allow_html=True)


def inject_main_content_area_styles():
    """Fondo blanco/gris claro solo en el área central (post-login)."""
    import streamlit as st
    st.markdown(MAIN_CONTENT_AREA_CSS, unsafe_allow_html=True)


WELCOME_LAYOUT_CSS = """
<style>
    .stApp:has(.velox-id-bar) [data-testid="stSidebar"] { display: none !important; }
    .stApp:has(.velox-id-bar) [data-testid="collapsedControl"] { display: none !important; }

    /* Portada: ancho completo del canvas para que st.columns reparta márgenes */
    .main .block-container {
        width: 100% !important;
        max-width: 100% !important;
        padding-top: 0.75rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    /* Columna central estrecha (col2 de [1, 1.5, 1]) — solo fila raíz de la portada */
    .velox-portal-center-col div[data-testid="stColumn"],
    div[data-testid="stColumn"] {
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }

    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type {
        align-items: flex-start !important;
        justify-content: center !important;
        gap: 0 !important;
    }

    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) {
        max-width: 420px !important;
        min-width: 260px !important;
        flex: 0 1 420px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(1),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(3),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(1),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(3) {
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }

    .velox-brand-stack {
        width: 100%;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 0 0 0.35rem;
        padding: 0;
        box-sizing: border-box;
    }

    .velox-brand-stack .velox-logo-fallback,
    .velox-brand-stack .velox-tagline--center {
        text-align: center !important;
        width: 100%;
        margin-left: 0 !important;
        margin-right: 0 !important;
    }

    /* Logo HTML en portada: evitar offset lateral de contenedores Streamlit */
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stMarkdown"],
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stMarkdown"] {
        width: 100% !important;
    }

    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="element-container"]:has(img[alt="veloX"]),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="element-container"]:has(img[alt="veloX"]) {
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        justify-content: center !important;
    }

    /* Ocultar div vacío legacy de velox-portal-card si quedara en caché */
    div.velox-portal-card:empty {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
    }

    /* Tarjeta nativa Streamlit (st.container border=True) */
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] {
        max-width: 420px !important;
        width: 100% !important;
        margin: 0 auto !important;
        padding: 0 !important;
        overflow: hidden !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.07) !important;
        border: 1px solid #e5e7eb !important;
    }

    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] .velox-id-bar,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] .velox-id-bar {
        margin: 0 !important;
        border-radius: 0 !important;
        border-left: none !important;
        border-right: none !important;
        border-top: none !important;
    }

    .velox-portal-center-col .velox-tagline--center,
    .velox-portal-center-col .velox-logo-fallback,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .velox-tagline--center,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .velox-logo-fallback {
        text-align: center !important;
    }

    .velox-portal-center-col .stTextInput > div > div > input,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .stTextInput > div > div > input {
        max-width: 420px !important;
        width: 100% !important;
        padding: 0.55rem 0.7rem !important;
        font-size: 0.86rem !important;
        border-radius: 10px !important;
    }

    .velox-portal-center-col .stButton > button,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .stButton > button {
        width: 100% !important;
        max-width: 420px !important;
        margin-top: 2px !important;
        margin-bottom: 2px !important;
        min-height: 2.3rem !important;
        padding: 0.48rem 0.7rem !important;
        font-size: 0.86rem !important;
        border-radius: 10px !important;
    }

    .velox-portal-center-col [data-testid="element-container"]:has([data-testid="stBaseButton-primary"]),
    .velox-portal-center-col [data-testid="element-container"]:has([data-testid="stBaseButton-secondary"]),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="element-container"]:has([data-testid="stBaseButton-primary"]),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="element-container"]:has([data-testid="stBaseButton-secondary"]) {
        margin-top: 0 !important;
        margin-bottom: 0.04rem !important;
        padding-bottom: 0 !important;
    }

    .velox-portal-center-col [data-testid="element-container"]:has([data-testid="stBaseButton-primary"]),
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="element-container"]:has([data-testid="stBaseButton-primary"]) {
        margin-top: 0.3rem !important;
    }

    .velox-portal-center-col [data-testid="stBaseButton-primary"] button,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-primary"] button {
        background: linear-gradient(180deg, #1e3a5f 0%, #152a45 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(30, 58, 95, 0.22) !important;
    }

    .velox-portal-center-col [data-testid="stBaseButton-secondary"] button,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stBaseButton-secondary"] button {
        background: #ffffff !important;
        color: #1e3a5f !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: none !important;
    }

    .velox-portal-center-col .velox-register-header,
    .velox-portal-center-col .velox-register-sub,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .velox-register-header,
    .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .velox-register-sub {
        text-align: center;
    }

    .main .block-container > div > [data-testid="stVerticalBlock"] {
        gap: 0.4rem !important;
    }

    .main .block-container [data-testid="element-container"] {
        margin-bottom: 0.08rem !important;
    }

    .velox-tagline--center {
        font-size: 0.86rem;
        line-height: 1.45;
        color: #475569;
        font-weight: 500;
        margin: 0.2rem 0 0.55rem;
        padding: 0 0.35rem;
        text-align: center;
    }

    .velox-logo-fallback {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1e3a5f;
        margin: 0.15rem 0 0.25rem;
    }

    .velox-portal-card {
        width: 100%;
        max-width: 420px;
        margin: 0 auto;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.07);
        overflow: hidden;
    }

    /* No usar st.markdown('<div class="velox-portal-card">') — genera barra blanca vacía */

    .velox-portal-scroll {
        max-height: 580px;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 0 0.15rem 0.35rem 0;
        scrollbar-width: thin;
        scrollbar-color: #94a3b8 #f1f5f9;
    }

    .velox-portal-scroll::-webkit-scrollbar { width: 6px; }
    .velox-portal-scroll::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 999px; }
    .velox-portal-scroll::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 999px; }

    .velox-portal-body,
    .velox-portal-body--login {
        padding: 0 0.95rem 0.45rem;
        margin-top: 0 !important;
    }

    .velox-id-bar {
        margin-bottom: 0 !important;
        font-size: 0.74rem;
        padding: 0.55rem 0.65rem;
        text-align: center;
    }

    .velox-register-header { font-size: 0.96rem; margin-bottom: 0.1rem; }
    .velox-register-sub { font-size: 0.8rem; margin-bottom: 0.65rem; color: #64748b; }
    .velox-activation-banner { margin-bottom: 0.65rem; font-size: 0.8rem; text-align: center; }
</style>
"""


def inject_welcome_layout():
    import streamlit as st
    st.markdown(WELCOME_LAYOUT_CSS, unsafe_allow_html=True)


def inject_section_catalog_css():
    import streamlit as st
    st.markdown(SECTION_CATALOG_CSS, unsafe_allow_html=True)
    st.markdown(MAIN_CONTENT_AREA_CSS, unsafe_allow_html=True)


SECTION_CATALOG_CSS = """
<style>
    .velox-catalogo-hero {
        text-align: center !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0.15rem auto 1rem !important;
        max-width: 100% !important;
        padding: 0 0.5rem !important;
        box-sizing: border-box !important;
    }
    /* Contenedor Streamlit del hero (solo usuarios normales / catalogo_centrado) */
    [data-testid="stMain"] [data-testid="element-container"]:has(.velox-catalogo-hero),
    [data-testid="stMain"] [data-testid="stMarkdownContainer"]:has(.velox-catalogo-hero),
    section.main [data-testid="element-container"]:has(.velox-catalogo-hero),
    section.main [data-testid="stMarkdownContainer"]:has(.velox-catalogo-hero) {
        text-align: center !important;
        width: 100% !important;
        display: block !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    .velox-catalogo-hero__titulo {
        color: #1A2332 !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.06em;
        margin: 0 0 0.45rem 0 !important;
        padding: 0 !important;
        text-align: center !important;
        line-height: 1.15 !important;
        width: 100% !important;
    }
    /* Chip ovalado: solo vista Inicio usuario normal (catalogo_centrado + velox-titulo-chip) */
    .velox-catalogo-hero__titulo.velox-titulo-chip {
        display: inline-block !important;
        width: auto !important;
        background-color: #E0F2FE !important;
        color: #0F172A !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
        letter-spacing: 0.04em !important;
        padding: 8px 32px !important;
        border-radius: 40px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        margin: 0 auto 0.65rem auto !important;
        line-height: 1.25 !important;
        border: 1px solid rgba(0, 180, 216, 0.22) !important;
        cursor: default !important;
        user-select: none !important;
        text-align: center !important;
    }
    .velox-catalogo-hero__desc {
        color: #1A2332 !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        opacity: 0.88 !important;
        margin: 0 auto 1.5rem auto !important;
        max-width: 38rem !important;
        width: 100% !important;
        line-height: 1.5 !important;
        text-align: center !important;
        display: block !important;
    }
    .velox-section-grid { margin-bottom: 0.15rem; }
    .velox-section-card {
        border-radius: 16px;
        padding: 1.15rem 1.2rem;
        min-height: 148px;
        margin-bottom: 0.4rem;
        position: relative;
        overflow: hidden;
    }
    .velox-section-card--active {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        color: #FFFFFF;
        box-shadow: 0 8px 26px rgba(15, 23, 42, 0.24);
    }
    .velox-section-card--locked {
        background: #FFFFFF !important;
        border: 1px dashed #94a3b8;
        color: #475569;
        opacity: 1;
        filter: none;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.07);
    }
    .velox-section-card__watermark {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-16deg);
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: 0.14em;
        color: rgba(100, 116, 139, 0.2);
        pointer-events: none;
    }
    .velox-section-card__title { font-weight: 700; font-size: 1rem; margin-bottom: 0.35rem; }
    .velox-section-card--active .velox-section-card__title { color: #FFFFFF; }
    .velox-section-card--locked .velox-section-card__title { color: #475569; }
    .velox-section-card__desc { font-size: 0.82rem; line-height: 1.45; }
    .velox-section-card--active .velox-section-card__desc,
    .velox-section-card--active .velox-section-card__meta { color: #FFFFFF; }
    .velox-section-card__meta { font-size: 0.78rem; margin-top: 0.7rem; font-weight: 600; }
    .velox-section-grid .stButton > button {
        border-radius: 14px !important;
        font-weight: 600 !important;
    }
    .velox-section-grid .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: 1px solid #334155 !important;
    }
    .velox-section-grid .stButton > button[kind="primary"] p,
    .velox-section-grid .stButton > button[kind="primary"] span,
    .velox-section-grid .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"],
    .velox-section-grid .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] p,
    .velox-section-grid .stButton > button[kind="secondary"] p,
    .velox-section-grid .stButton > button[kind="secondary"] span,
    .velox-section-grid .stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"],
    .velox-section-grid .stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.2) !important;
    }
    .velox-section-grid .stButton > button[kind="secondary"] {
        background: rgba(241, 245, 249, 0.9) !important;
        color: #334155 !important;
        border: 1px dashed #94a3b8 !important;
    }
</style>
"""


def inject_sidebar_theme():
    import streamlit as st
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
