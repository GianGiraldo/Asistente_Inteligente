# app.py - Versión final con redirección funcional (indentación corregida)
import streamlit as st
import pandas as pd
from auth import AuthManager
from storage_manager import StorageManager
from message_manager import MessageManager
from datetime import datetime
from notification_manager import NotificationManager

st.set_page_config(
    page_title="Asistente Inteligente - Gestión Documental",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_managers():
    auth = AuthManager()
    storage = StorageManager()
    messages = MessageManager()
    notifications = NotificationManager()
    return auth, storage, messages, notifications

auth_manager, storage_manager, message_manager, notification_manager = init_managers()

SECCIONES = {
    "contabilidad": {
        "nombre": "📊 Contabilidad",
        "icono": "📊",
        "color": "#2ecc71",
        "descripcion": "Facturas, balances, libros contables",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "laboral": {
        "nombre": "👥 Laboral",
        "icono": "👥",
        "color": "#3498db",
        "descripcion": "Contratos, nóminas, documentos laborales",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "financiero": {
        "nombre": "💰 Financiero",
        "icono": "💰",
        "color": "#f1c40f",
        "descripcion": "Estados financieros, proyecciones",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "logistico": {
        "nombre": "🚚 Logístico",
        "icono": "🚚",
        "color": "#e67e22",
        "descripcion": "Guías, inventarios, despachos",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    },
    "excel": {
        "nombre": "📈 Excel",
        "icono": "📈",
        "color": "#1abc9c",
        "descripcion": "Plantillas, reportes, análisis",
        "subcategorias": ["Minicursos", "Formatos y Plantillas"]
    }
}

st.markdown("""
<style>
    /* Centrar verticalmente la pantalla de login */
    .stApp > .main > .block-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 90vh;
        padding-top: 0;
    }

    /* Quitar el padding extra que pueda desplazar */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* Fondo general (coordinado con tu imagen) */
    .stApp {
        background: linear-gradient(135deg, #f5f7fc 0%, #e9eef5 100%);
    }

    /* Tarjeta blanca del formulario */
    div[data-testid="stForm"] {
        background: transparent;
    }

    /* Ajuste para las tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        justify-content: center;
    }            
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #f0f7ff;  /* Azul muy claro, educativo y tranquilo */
    }
    
    /* Fondo del sidebar */
    .css-1d391kg, .stSidebar {
        background-color: #ffffff;
        border-right: 1px solid #e0e7f0;
    }
    
    /* Tarjetas de métricas (ya tienes .metric-card, puedes ajustar si es necesario) */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dce5f0;
        border-radius: 20px;
        padding: 1rem;
        color: #1e2a3e;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    .metric-card h3 {
        color: #2c3e66;
        margin: 0;
        font-size: 1.8rem;
    }
    .metric-card p {
        color: #4a627a;
        margin: 0;
        font-size: 0.9rem;
    }
    
    /* Tarjetas de secciones (dashboard) */
    .section-card, .home-card {
        background: white;
        border-radius: 20px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
        border: 1px solid #e9eef3;
    }
    .section-card:hover, .home-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        border-color: #a0c4ff;
    }
    
    /* Botones principales */
    .stButton button {
        background-color: #4a6fa5;
        color: white;
        border-radius: 30px;
        border: none;
        transition: background-color 0.2s;
    }
    .stButton button:hover {
        background-color: #2c5282;
    }
    
    /* Encabezados */
    h1, h2, h3, h4 {
        color: #1e2a3e;
    }
    
    /* Selectbox y otros inputs */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 30px;
        border-color: #cbd5e1;
    }
    
    /* Popover (campana) */
    .stPopover {
        background-color: white;
        border-radius: 20px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    
    /* Footer */
    footer {
        color: #7f8c8d;
    }

    /* Centrar completamente el encabezado del login */
.main-header {
    text-align: center !important;
    margin-left: auto !important;
    margin-right: auto !important;
    width: 100% !important;
    display: block !important;
}

/* Opcional: asegurar que el formulario de login también se centre */
.stTabs {
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
}

/* Aumentar el espacio superior en el sidebar */
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 8rem !important;  /* Ajusta el valor (2rem, 3rem, etc.) */
}                
</style>
""", unsafe_allow_html=True)

def login_screen():
    # Centrar todo el contenido usando columnas vacías a los lados
    left_pad, center_col, right_pad = st.columns([1, 2, 1])
    with center_col:
        # Mostrar el logo con un tamaño más pequeño (ajusta el ancho en píxeles)
        st.image("assets/velox.png", width=300)   # Cambia 150 por el tamaño deseado (ej: 120, 180)
        
        # Espacio entre logo y formulario
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        
        # Tarjeta blanca para el formulario
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.08);">
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email (Gmail)", placeholder="tuemail@gmail.com")
                password = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Iniciar Sesión", use_container_width=True):
                    valido, rol, nombre, secciones = auth_manager.verificar_usuario(email, password)
                    if valido:
                        st.session_state['autenticado'] = True
                        st.session_state['usuario'] = email
                        st.session_state['rol'] = rol
                        st.session_state['nombre'] = nombre
                        st.session_state['secciones'] = secciones
                        st.session_state['login_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.session_state['menu_principal'] = "🏠 Inicio"
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas")
        
        with tab2:
            with st.form("registro_form"):
                nombre = st.text_input("Nombre completo")
                email = st.text_input("Email (Gmail)", placeholder="tuemail@gmail.com")
                password = st.text_input("Contraseña", type="password")
                confirmar = st.text_input("Confirmar contraseña", type="password")
                if st.form_submit_button("Registrarse", use_container_width=True):
                    if password != confirmar:
                        st.error("Las contraseñas no coinciden")
                    elif not email.endswith('@gmail.com'):
                        st.error("Solo se permiten cuentas de Gmail")
                    else:
                        exito, msg = auth_manager.registrar_usuario(email, password, nombre)
                        if exito:
                            st.success(msg)
                            st.info("Ahora puedes iniciar sesión")
                        else:
                            st.error(msg)
        
        st.markdown("</div>", unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'seccion_seleccionada' not in st.session_state:
    st.session_state['seccion_seleccionada'] = None

if not st.session_state['autenticado']:
    login_screen()
else:
    # HEADER
    col_logo, col_user, col_logout = st.columns([1, 3, 1])

    with col_logo:
        st.markdown("""
        <style>
        .custom-title {
            font-size: 1.5rem;
            white-space: nowrap;
            margin: 0;
            padding: 0;
        }
        </style>
        <h1 class="custom-title">🌟 Asistente Inteligente</h1>
        """, unsafe_allow_html=True)

    with col_user:
        nombre = st.session_state.get('nombre', 'Usuario')
        rol = st.session_state.get('rol', 'usuario')
        rol_texto = '👑 Master' if rol == 'master' else '👁️ Usuario'
        subcol1, subcol2 = st.columns([4, 1])
        with subcol1:
            st.markdown(f"**🌟 {nombre}**  \n<small>{rol_texto}</small>", unsafe_allow_html=True)
        with subcol2:
            bell_html = '🔔'
            with st.popover(bell_html, use_container_width=True):
                st.markdown("### 📢 Últimas publicaciones")
                publicaciones = notification_manager.obtener_ultimas_publicaciones(limite=10)
                if not publicaciones:
                    st.info("No hay publicaciones recientes.")
                else:
                    for pub in publicaciones:
                        fecha = pub.get('fecha_creacion', '')
                        fecha_str = fecha[:16] if isinstance(fecha, str) else str(fecha)[:16] if fecha else "Fecha desconocida"
                        st.markdown(f"""
                        <div style="background:#f8f9fa; border-radius:12px; padding:12px; margin-bottom:12px; border-left:4px solid #667eea;">
                            <div style="font-weight:bold;">{pub['titulo']}</div>
                            <div style="font-size:0.85rem; color:#555;">{pub['mensaje']}</div>
                            <div style="font-size:0.7rem; color:#888; display:flex; justify-content:space-between;">
                                <span>📅 {fecha_str}</span>
                                <span>📂 {pub['seccion'].capitalize()} / {pub['categoria']}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"🔍 Ver contenido", key=f"ver_{pub['id']}", use_container_width=True):
                            st.session_state['seccion_seleccionada'] = pub['seccion']
                            st.session_state['categoria_seleccionada'] = pub['categoria']
                            st.session_state['menu_principal'] = "📁 Mis Documentos"
                            st.rerun()

    with col_logout:
        if st.button("🚪 Cerrar Sesión"):
            for key in ['autenticado', 'usuario', 'rol', 'nombre', 'secciones', 'login_time', 'seccion_seleccionada']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.markdown("---")

    # SIDEBAR - MENÚ PRINCIPAL (usando selectbox)
    with st.sidebar:
        st.markdown(f"### Hola, {st.session_state.get('nombre', 'Usuario')}")
        if st.session_state['rol'] == 'master':
            opciones_menu = ["🏠 Inicio", "📁 Mis Documentos", "👥 Gestión Usuarios", "📢 Publicaciones", "⚙️ Configuración"]
        else:
            opciones_menu = ["🏠 Inicio", "📁 Mis Documentos", "📬 Consultas", "👤 Mi Perfil"]

        # Asegurar que menu_principal tenga un valor válido
        if st.session_state.get('menu_principal') not in opciones_menu:
            st.session_state['menu_principal'] = opciones_menu[0]

        # Usar selectbox (evita conflictos de estado)
        seleccion = st.selectbox(
            "📋 Menú",
            opciones_menu,
            index=opciones_menu.index(st.session_state['menu_principal']),
            key="menu_select"
        )
        if seleccion != st.session_state['menu_principal']:
            st.session_state['menu_principal'] = seleccion
            st.rerun()

        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for key in ['autenticado', 'usuario', 'rol', 'nombre', 'secciones', 'login_time', 'seccion_seleccionada']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # CONTENIDO PRINCIPAL
    menu_actual = st.session_state.get('menu_principal', '🏠 Inicio')

    if menu_actual == "🏠 Inicio":
        if st.session_state['rol'] == 'master':
            st.header("🏠 Inicio")
            secciones_usuario = list(SECCIONES.keys())
            archivos_personales = storage_manager.listar_archivos_usuario(st.session_state['usuario'], incluir_publicaciones=False)
            publicaciones = storage_manager.obtener_publicaciones_usuario(st.session_state['usuario'], secciones_usuario)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-card"><h3>📄</h3><h3>{len(archivos_personales)}</h3><p>Mis Documentos</p></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card"><h3>📢</h3><h3>{len(publicaciones)}</h3><p>Documentos Disponibles</p></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-card"><h3>📂</h3><h3>{len(secciones_usuario)}</h3><p>Secciones</p></div>', unsafe_allow_html=True)
            with col4:
                usuarios_total = len(auth_manager.listar_usuarios())
                st.markdown(f'<div class="metric-card"><h3>👥</h3><h3>{usuarios_total}</h3><p>Usuarios</p></div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 📂 Todas las Secciones") 
            cols = st.columns(3)
            for i, (seccion_id, seccion_info) in enumerate(SECCIONES.items()):
                with cols[i % 3]:
                    docs_seccion = [d for d in publicaciones if d["seccion"] == seccion_id]
                    primera_categoria = seccion_info["subcategorias"][0] if seccion_info.get("subcategorias") else "General"
                    if st.button(
                        f"{seccion_info['icono']} {seccion_info['nombre']}\n\n"
                        f"{seccion_info['descripcion']}\n\n"
                        f"✅ {len(docs_seccion)} documentos disponibles",
                        key=f"dashboard_btn_{seccion_id}",
                        use_container_width=True
                    ):
                        # === CORRECCIÓN: Indentación correcta ===
                        st.session_state['menu_principal'] = "📁 Mis Documentos"
                        st.session_state['seccion_seleccionada_documentos'] = seccion_id
                        st.session_state['categoria_redirigida'] = primera_categoria
                        st.rerun()
        else:   # Usuario normal
            st.header("🏠 Inicio")
            secciones_usuario = st.session_state.get('secciones', [])
            if not secciones_usuario:
                st.warning("No tienes secciones asignadas. Contacta al administrador.")
            else:
                st.markdown("### 📂 Mis Secciones Asignadas")
                cols = st.columns(3)
                for i, sec_id in enumerate(secciones_usuario):
                    if sec_id in SECCIONES:
                        sec_info = SECCIONES[sec_id]
                        try:
                            docs_seccion = storage_manager.obtener_publicaciones_por_seccion(seccion=sec_id)
                            num_docs = len(docs_seccion)
                        except:
                            num_docs = 0
                        primera_categoria = sec_info["subcategorias"][0] if sec_info.get("subcategorias") else "General"
                        with cols[i % 3]:
                            if st.button(
                                f"{sec_info['icono']} {sec_info['nombre']}\n\n"
                                f"{sec_info['descripcion']}\n\n"
                                f"📄 {num_docs} documentos disponibles",
                                key=f"user_dashboard_btn_{sec_id}",
                                use_container_width=True
                            ):
                                # === CORRECCIÓN: Indentación correcta ===
                                st.session_state['menu_principal'] = "📁 Mis Documentos"
                                st.session_state['seccion_seleccionada_documentos'] = sec_id
                                st.session_state['categoria_redirigida'] = primera_categoria
                                st.rerun()

    elif menu_actual == "📁 Mis Documentos":
        # Procesar redirección desde el dashboard (Inicio) – usando session_state
        seccion_preseleccionada = st.session_state.pop('seccion_seleccionada_documentos', None)
        categoria_redirigida = st.session_state.pop('categoria_redirigida', None)
        # Limpiar cualquier query_params residual
        st.query_params.clear()

        st.header("📁 Mis Documentos")

        # Obtener secciones accesibles según rol
        if st.session_state['rol'] == 'master':
            secciones_usuario = list(SECCIONES.keys())
        else:
            secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])

        if not secciones_usuario:
            st.warning("⚠️ No tienes acceso a ninguna sección. Contacta al administrador.")
        else:
            opciones_secciones = [(s, SECCIONES[s]['nombre']) for s in secciones_usuario]
            indice_preseleccionado = 0
            if seccion_preseleccionada:
                for idx, (sec_id, _) in enumerate(opciones_secciones):
                    if sec_id == seccion_preseleccionada:
                        indice_preseleccionado = idx
                        break

            # Selector de sección
            seccion_seleccionada = st.selectbox(
                "Seleccionar sección:",
                options=opciones_secciones,
                format_func=lambda x: x[1],
                index=indice_preseleccionado,
                key="selector_seccion_documentos"
            )[0]
            seccion_info = SECCIONES[seccion_seleccionada]

            # Mostrar información de la sección
            st.markdown(f"""
            <div style="background: {seccion_info['color']}10; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                <h3>{seccion_info['icono']} {seccion_info['nombre']}</h3>
                <p>{seccion_info['descripcion']}</p>
            </div>
            """, unsafe_allow_html=True)

            # Botón para volver al dashboard
            if st.button("🔙 Volver al Dashboard"):
                st.rerun()

            # Subcategorías (categorías)
            subcategorias_disponibles = seccion_info.get("subcategorias", ["General"])
            st.markdown("### 📂 Categorías")

            # Inicializar o recuperar categoría preseleccionada
            if 'categoria_seleccionada' not in st.session_state:
                st.session_state['categoria_seleccionada'] = subcategorias_disponibles[0]

            # Si venimos de una redirección con categoría, sobreescribimos
            if categoria_redirigida and categoria_redirigida in subcategorias_disponibles:
                st.session_state['categoria_seleccionada'] = categoria_redirigida

            # Mostrar botones de categorías
            cols_cat = st.columns(len(subcategorias_disponibles))
            for idx, cat in enumerate(subcategorias_disponibles):
                with cols_cat[idx]:
                    if st.button(
                        cat,
                        key=f"cat_{seccion_seleccionada}_{cat}",
                        use_container_width=True,
                        type="primary" if st.session_state['categoria_seleccionada'] == cat else "secondary"
                    ):
                        st.session_state['categoria_seleccionada'] = cat
                        st.rerun()

            categoria_actual = st.session_state['categoria_seleccionada']
            st.markdown(f"**Categoría actual:** {categoria_actual}")
            st.markdown("---")

            # Buscador
            busqueda = st.text_input("🔍 Buscar por nombre o descripción:", key="buscador_mis_docs")

            # ========== DOCUMENTOS PERSONALES (solo master) ==========
            archivos_personales = []
            if st.session_state['rol'] == 'master':
                with st.expander("📤 Subir documento personal", expanded=False):
                    archivo = st.file_uploader("Seleccionar archivo", type=['pdf', 'xlsx', 'xls', 'docx', 'doc'])
                    descripcion = st.text_area("Descripción (opcional)")
                    if archivo and st.button("Subir documento personal", type="primary"):
                        exito, resultado = storage_manager.guardar_archivo(
                            archivo, seccion_seleccionada, categoria_actual,
                            st.session_state['usuario'], descripcion, es_publicacion=False
                        )
                        if exito:
                            st.success(f"✅ Documento subido: {archivo.name}")
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {resultado}")

                st.markdown("### 📄 Mis documentos personales")
                archivos_personales = storage_manager.listar_archivos_usuario(
                    st.session_state['usuario'],
                    seccion=seccion_seleccionada,
                    subcategoria=categoria_actual,
                    incluir_publicaciones=False
                )
                if busqueda:
                    archivos_personales = [a for a in archivos_personales if
                                        busqueda.lower() in a['nombre_original'].lower() or
                                        busqueda.lower() in a.get('descripcion', '').lower()]

                if archivos_personales:
                    for archivo in archivos_personales:
                        cols = st.columns([3, 2, 2, 1, 1, 1])
                        with cols[0]:
                            st.write(f"📄 **{archivo['nombre_original']}**")
                        with cols[1]:
                            st.write(f"📅 {archivo['fecha'][:10]}")
                        with cols[2]:
                            tamaño_kb = archivo.get('tamaño_kb', archivo.get('tamaño_bytes', 0) / 1024)
                            st.write(f"💾 {tamaño_kb:.1f} KB")
                        with cols[3]:
                            if st.button("📥", key=f"download_{archivo['id']}"):
                                exito, resultado = storage_manager.descargar_archivo_personal(archivo['id'], st.session_state['usuario'])
                                if exito:
                                    st.markdown(f'<a href="{resultado["url"]}" download="{resultado["nombre"]}" style="background: #667eea; color: white; padding: 4px 12px; border-radius: 6px; text-decoration: none;">📥 Descargar</a>', unsafe_allow_html=True)
                                    st.success("✅ Descarga disponible")
                                else:
                                    st.error(f"❌ {resultado}")
                        with cols[4]:
                            if st.button("🌍 Publicar", key=f"publish_{archivo['id']}"):
                                st.session_state['archivo_a_publicar'] = archivo['id']
                                st.session_state['show_publish_form'] = True
                        with cols[5]:
                            if st.button("🗑️", key=f"delete_{archivo['id']}"):
                                storage_manager.eliminar_archivo(archivo['id'], st.session_state['usuario'])
                                st.rerun()
                        st.divider()
                else:
                    st.info("No tienes documentos personales en esta categoría")

            # ========== PUBLICACIONES DEL MASTER ==========
            st.markdown("### 📢 Publicaciones del Master")
            publicaciones = storage_manager.obtener_publicaciones_por_seccion(
                seccion=seccion_seleccionada,
                subcategoria=categoria_actual
            )
            if busqueda:
                publicaciones = [p for p in publicaciones if
                                busqueda.lower() in p.get('nombre_original', '').lower() or
                                busqueda.lower() in p.get('descripcion', '').lower()]

            if publicaciones:
                for i, pub in enumerate(publicaciones):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**📢 {pub.get('nombre_original', pub.get('titulo', 'Sin título'))}**  \n"
                                    f"<small>{pub.get('fecha', pub.get('fecha_creacion', ''))[:10]}</small>\n\n"
                                    f"{pub.get('descripcion', pub.get('mensaje', ''))}", unsafe_allow_html=True)
                    with col2:
                        if st.button("📥 Descargar", key=f"down_pub_{pub['id']}_{i}"):
                            if seccion_seleccionada in secciones_usuario:
                                exito, resultado = storage_manager.descargar_archivo(pub["id"], st.session_state['usuario'], [seccion_seleccionada])
                                if exito:
                                    st.markdown(f'<a href="{resultado["url"]}" download="{resultado["nombre"]}">Descargar</a>', unsafe_allow_html=True)
                                    st.success("✅ Descarga disponible")
                                else:
                                    st.error(f"❌ {resultado}")
                            else:
                                st.error("No tienes permiso para descargar este documento")
                    if st.session_state['rol'] == 'master':
                        col_edit, col_del = st.columns(2)
                        with col_edit:
                            if st.button("✏️ Editar", key=f"edit_{pub['id']}_{i}"):
                                st.session_state[f'editando_{pub["id"]}'] = True
                            if st.session_state.get(f'editando_{pub["id"]}', False):
                                nueva_desc = st.text_area("Nueva descripción", value=pub.get('descripcion', ''), key=f"newdesc_{pub['id']}")
                                if st.button("Guardar"):
                                    exito, msg = storage_manager.editar_publicacion(pub['id'], nueva_desc)
                                    if exito:
                                        st.success(msg)
                                        st.session_state.pop(f'editando_{pub["id"]}', None)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        with col_del:
                            if st.button("🗑️ Eliminar", key=f"del_{pub['id']}_{i}"):
                                storage_manager.eliminar_publicacion(pub['id'])
                                st.rerun()
                    st.divider()
            else:
                st.info("No hay publicaciones del master en esta categoría")

            # Formulario para publicar desde personal
            if st.session_state.get('show_publish_form', False) and st.session_state['rol'] == 'master':
                with st.form("form_publish"):
                    st.markdown("### Publicar documento personal")
                    archivo_id = st.session_state['archivo_a_publicar']
                    seccion_dest = st.selectbox("Sección destino", list(SECCIONES.keys()), format_func=lambda x: SECCIONES[x]['nombre'])
                    subcat_dest = st.selectbox("Subcategoría", SECCIONES[seccion_dest]["subcategorias"])
                    comentario = st.text_area("Comentario")
                    if st.form_submit_button("Confirmar publicación"):
                        exito, msg = storage_manager.publicar_desde_personal(archivo_id, st.session_state['usuario'], seccion_dest, subcat_dest, comentario)
                        if exito:
                            st.success("Publicado")
                            del st.session_state['show_publish_form']
                            del st.session_state['archivo_a_publicar']
                            st.rerun()
                        else:
                            st.error(msg)

    elif menu_actual == "👥 Gestión Usuarios" and st.session_state['rol'] == 'master':
        st.header("👥 Gestión de Usuarios y Permisos")
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuarios", "🔐 Asignar Secciones", "📢 Publicar Documentos"])
        with tab1:
            usuarios = auth_manager.listar_usuarios()
            if usuarios:
                data = []
                for email, u in usuarios.items():
                    secciones = auth_manager.obtener_secciones_usuario(email)
                    data.append({"Email": email, "Nombre": u["nombre"], "Rol": "👑 Master" if u["rol"]=="master" else "👤 Usuario", "Acceso": f"{len(secciones)}/{len(SECCIONES)}"})
                st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)
                st.markdown("---")
                usuarios_eliminar = [e for e in usuarios if e != st.session_state['usuario']]
                if usuarios_eliminar:
                    sel = st.selectbox("Usuario a eliminar", usuarios_eliminar)
                    if st.button("Eliminar", type="secondary"):
                        auth_manager.eliminar_usuario(sel, st.session_state['usuario'])
                        st.rerun()
            else:
                st.info("No hay usuarios")
        with tab2:
            st.markdown("Asignar secciones a usuario")
            usuarios_lista = [e for e in auth_manager.listar_usuarios() if e != st.session_state['usuario']]
            if usuarios_lista:
                usuario = st.selectbox("Usuario", usuarios_lista)
                actuales = auth_manager.obtener_secciones_usuario(usuario)
                nuevas = []
                cols = st.columns(3)
                for i, (k, v) in enumerate(SECCIONES.items()):
                    with cols[i%3]:
                        if st.checkbox(f"{v['icono']} {v['nombre']}", value=(k in actuales), key=f"perm_{usuario}_{k}"):
                            nuevas.append(k)
                if st.button("Guardar permisos"):
                    auth_manager.asignar_secciones_usuario(usuario, nuevas, st.session_state['usuario'])
                    st.rerun()
            else:
                st.info("No hay otros usuarios")
        with tab3:
            st.markdown("Publicar documento para todos")
            seccion = st.selectbox("Sección", list(SECCIONES.keys()), format_func=lambda x: SECCIONES[x]['nombre'])
            subcat = st.selectbox("Subcategoría", SECCIONES[seccion]["subcategorias"])
            archivo = st.file_uploader("Archivo", type=['pdf','xlsx','xls','docx','doc'])
            desc = st.text_area("Descripción")
            if archivo and st.button("Publicar"):
                exito, msg = storage_manager.publicar_documento(archivo, seccion, subcat, desc)
                if exito:
                    st.success("Documento publicado")
                    st.rerun()
                else:
                    st.error(msg)

    elif menu_actual == "📢 Publicaciones" and st.session_state['rol'] == 'master':
        st.header("Publicaciones Realizadas")
        todas = storage_manager.obtener_publicaciones_por_seccion()
        for pub in todas:
            with st.expander(f"{pub['nombre_original']} - {pub['fecha'][:10]}"):
                st.write(f"Sección: {SECCIONES[pub['seccion']]['nombre']}")
                st.write(f"Subcategoría: {pub.get('subcategoria','General')}")
                st.write(f"Descripción: {pub.get('descripcion','')}")
                if st.button(f"Eliminar", key=f"del_all_{pub['id']}"):
                    storage_manager.eliminar_publicacion(pub['id'])
                    st.rerun()

    elif menu_actual == "⚙️ Configuración" and st.session_state['rol'] == 'master':
        st.header("Configuración")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Limpiar facturas (demo)"):
                st.warning("Función no implementada")
        with col2:
            st.info("Versión 1.0")

    elif menu_actual == "📬 Consultas":
        st.header("Sistema de Consultas")
        if st.session_state['rol'] == 'master':
            tab1, tab2 = st.tabs(["Pendientes", "Respondidas"])
            with tab1:
                pendientes = message_manager.obtener_mensajes_para_master(respondidos=False)
                for msg in pendientes:
                    st.markdown(f"**De:** {msg['nombre_usuario']} ({msg['email']})  \n**Sección:** {SECCIONES[msg['seccion']]['nombre']}  \n**Mensaje:** {msg['mensaje']}")
                    respuesta = st.text_area("Respuesta", key=f"resp_{msg['id']}")
                    if st.button("Enviar", key=f"send_{msg['id']}"):
                        message_manager.responder_mensaje(msg['id'], respuesta, st.session_state['usuario'])
                        st.rerun()
                    st.divider()
            with tab2:
                respondidos = message_manager.obtener_mensajes_para_master(respondidos=True)
                for msg in respondidos:
                    st.markdown(f"**De:** {msg['nombre_usuario']}  \n**Consulta:** {msg['mensaje']}  \n**Respuesta:** {msg.get('respuesta','')}")
        else:
            st.markdown("Enviar consulta al Master")
            secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
            if secciones_usuario:
                seccion = st.selectbox("Sección relacionada", secciones_usuario, format_func=lambda x: SECCIONES[x]['nombre'])
                mensaje = st.text_area("Tu consulta", height=150)
                if st.button("Enviar consulta"):
                    if mensaje.strip():
                        message_manager.enviar_mensaje(st.session_state['usuario'], st.session_state['nombre'], seccion, mensaje)
                        st.success("Enviado")
                        st.rerun()
                    else:
                        st.warning("Escribe tu consulta")
            st.markdown("---")
            historial = message_manager.obtener_mensajes_usuario(st.session_state['usuario'])
            for msg in historial:
                st.markdown(f"**Consulta:** {msg['mensaje']}  \n**Respuesta:** {msg.get('respuesta','Pendiente')}")

    elif menu_actual == "👤 Mi Perfil":
        st.header("Mi Perfil")
        perfil = auth_manager.obtener_perfil(st.session_state['usuario'])
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Nombre:** {perfil['nombre']}")
            st.markdown(f"**Email:** {perfil['email']}")
            st.markdown(f"**Rol:** {perfil['rol'].upper()}")
        with col2:
            st.markdown("**Secciones asignadas:**")
            secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
            for s in secciones_usuario:
                st.markdown(f"- {SECCIONES[s]['nombre']}")
        st.markdown("---")
        with st.form("edit_perfil"):
            nombre = st.text_input("Nombre completo", value=perfil['nombre'])
            telefono = st.text_input("Teléfono", value=perfil.get('telefono',''))
            celular = st.text_input("Celular", value=perfil.get('celular',''))
            empresa = st.text_input("Empresa", value=perfil.get('empresa',''))
            cargo = st.text_input("Cargo", value=perfil.get('cargo',''))
            if st.form_submit_button("Guardar cambios"):
                auth_manager.actualizar_perfil(st.session_state['usuario'], {"nombre":nombre, "telefono":telefono, "celular":celular, "empresa":empresa, "cargo":cargo})
                st.session_state['nombre'] = nombre
                st.rerun()

    st.markdown("---")
    st.markdown("<div style='text-align:center'>Tu Gestor Documental Inteligente| © 2026</div>", unsafe_allow_html=True)