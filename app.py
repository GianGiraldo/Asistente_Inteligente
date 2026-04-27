# app.py - VERSIÓN COMPLETA Y ESTABLE
import streamlit as st
import pandas as pd
from auth import AuthManager
from storage_manager import StorageManager
from message_manager import MessageManager
from datetime import datetime
import os
import traceback

st.set_page_config(
    page_title="Optimizo con Pier - Gestión Documental",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_managers():
    auth = AuthManager()
    storage = StorageManager()
    messages = MessageManager()
    return auth, storage, messages

auth_manager, storage_manager, message_manager = init_managers()

SECCIONES = {
    "contabilidad": {
        "nombre": "📊 Contabilidad",
        "icono": "📊",
        "color": "#2ecc71",
        "descripcion": "Facturas, balances, libros contables",
        "subcategorias": ["Administración", "Gestión", "Control", "Reportes"]
    },
    "laboral": {
        "nombre": "👥 Laboral",
        "icono": "👥",
        "color": "#3498db",
        "descripcion": "Contratos, nóminas, documentos laborales",
        "subcategorias": ["Contratos", "Nóminas", "Evaluaciones", "Legajos"]
    },
    "financiero": {
        "nombre": "💰 Financiero",
        "icono": "💰",
        "color": "#f1c40f",
        "descripcion": "Estados financieros, proyecciones",
        "subcategorias": ["Presupuestos", "Flujo de Caja", "Auditoría", "Impuestos"]
    },
    "logistico": {
        "nombre": "🚚 Logístico",
        "icono": "🚚",
        "color": "#e67e22",
        "descripcion": "Guías, inventarios, despachos",
        "subcategorias": ["Inventarios", "Despachos", "Guías de Remisión", "Almacén"]
    },
    "excel": {
        "nombre": "📈 Excel",
        "icono": "📈",
        "color": "#1abc9c",
        "descripcion": "Plantillas, reportes, análisis",
        "subcategorias": ["Plantillas", "Dashboards", "Análisis de Datos", "Macros"]
    }
}

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s;
        cursor: pointer;
        border-left: 5px solid;
    }
    .section-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        cursor: pointer;
    }
    .publicacion-card {
        background: #e8f4fd;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .mensaje-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .mensaje-respuesta {
        background: #e8f4fd;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0 0.5rem 2rem;
        border-left: 3px solid #2ecc71;
    }
    .badge-nuevo {
        background-color: #ff4757;
        color: white;
        border-radius: 20px;
        padding: 2px 8px;
        font-size: 0.7rem;
        margin-left: 8px;
    }
</style>
""", unsafe_allow_html=True)

def login_screen():
    st.markdown("""
    <div class="main-header">
        <h1>📁 Optimizo con Pier</h1>
        <p>Tu gestor documental inteligente</p>
    </div>
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

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    login_screen()
else:
    try:
        if 'ir_a' in st.query_params and st.query_params['ir_a'] == 'mis_documentos':
            if 'seccion' in st.query_params:
                st.session_state['seccion_seleccionada_documentos'] = st.query_params['seccion']
            st.session_state['menu_principal'] = "📁 Mis Documentos"
            st.query_params.clear()

        col_logo, col_user, col_logout = st.columns([1, 3, 1])
        with col_logo:
            st.markdown("## 📁 Optimizo con Pier")
        with col_user:
            mensajes_no_leidos = message_manager.contar_no_leidos(st.session_state['usuario'])
            badge = f'<span class="badge-nuevo">{mensajes_no_leidos}</span>' if mensajes_no_leidos > 0 else ''
            st.markdown(f"""
            <div style="text-align: right;">
                <strong>👤 {st.session_state['nombre']}</strong><br>
                <small>{'👑 Master' if st.session_state['rol'] == 'master' else '👁️ Usuario'}</small>
                {badge}
            </div>
            """, unsafe_allow_html=True)
        with col_logout:
            if st.button("🚪 Cerrar Sesión"):
                for key in ['autenticado', 'usuario', 'rol', 'nombre', 'secciones', 'login_time']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        st.markdown("---")

        with st.sidebar:
            st.image("https://via.placeholder.com/200x80/667eea/ffffff?text=Optimizo", use_container_width=True)
            st.markdown("---")
            if st.session_state['rol'] == 'master':
                menu = ["🏠 Inicio", "📁 Mis Documentos", "👥 Gestión Usuarios", "📬 Consultas"]
            else:
                menu = ["🏠 Inicio", "📁 Mis Documentos", "📬 Consultas", "👤 Mi Perfil"]
            if 'menu_principal' not in st.session_state:
                st.session_state['menu_principal'] = menu[0]
            if st.session_state['menu_principal'] not in menu:
                st.session_state['menu_principal'] = menu[0]
            opcion = st.radio("📋 Menú", menu, key="menu_principal", index=menu.index(st.session_state['menu_principal']))
            st.markdown("---")
            if st.session_state['rol'] != 'master':
                secciones_asignadas = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
                st.markdown("### 📂 Mis Accesos")
                for sec in secciones_asignadas:
                    if sec in SECCIONES:
                        st.markdown(f"{SECCIONES[sec]['icono']} {SECCIONES[sec]['nombre']}")

        # DASHBOARD
        if opcion == "🏠 Inicio":
            st.header("🏠 Inicio")
            if st.session_state['rol'] == 'master':
                secciones_usuario = list(SECCIONES.keys())
            else:
                secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
            col1, col2, col3, col4 = st.columns(4)
            archivos_personales = storage_manager.listar_archivos_usuario(st.session_state['usuario'], incluir_publicaciones=False)
            publicaciones = storage_manager.obtener_publicaciones_usuario(st.session_state['usuario'], secciones_usuario)
            with col1:
                st.metric("📄 Mis Documentos", len(archivos_personales))
            with col2:
                st.metric("📢 Documentos Disponibles", len(publicaciones))
            with col3:
                st.metric("📂 Secciones", len(secciones_usuario))
            with col4:
                if st.session_state['rol'] == 'master':
                    st.metric("👥 Usuarios", len(auth_manager.listar_usuarios()))
                else:
                    st.metric("📬 Mensajes", message_manager.contar_no_leidos(st.session_state['usuario']))
            st.markdown("---")
            st.markdown("### 📂 Mis Secciones Asignadas")
            st.info("💡 **Haz clic en cualquier sección para ver sus documentos**")
            cols = st.columns(3)
            for i, (seccion_id, seccion_info) in enumerate(SECCIONES.items()):
                with cols[i % 3]:
                    if seccion_id in secciones_usuario:
                        docs_seccion = [d for d in publicaciones if d["seccion"] == seccion_id]
                        if st.button(
                            f"{seccion_info['icono']} {seccion_info['nombre']}\n\n"
                            f"{seccion_info['descripcion']}\n\n"
                            f"✅ {len(docs_seccion)} documentos disponibles",
                            key=f"dashboard_btn_{seccion_id}",
                            use_container_width=True
                        ):
                            st.query_params["seccion"] = seccion_id
                            st.query_params["ir_a"] = "mis_documentos"
                            st.rerun()
                    else:
                        st.markdown(f"""
                        <div class="section-card" style="border-left-color: #ccc; opacity: 0.7;">
                            <h3>{seccion_info['icono']} {seccion_info['nombre']}</h3>
                            <p>{seccion_info['descripcion']}</p>
                            <small>🔒 Sin acceso</small>
                        </div>
                        """, unsafe_allow_html=True)

        # ============================================
        # MIS DOCUMENTOS - VERSIÓN REFACTORIZADA (ESTABLE)
        # ============================================
        elif opcion == "📁 Mis Documentos":
            st.header("📁 Mis Documentos")
            if st.session_state['rol'] == 'master':
                secciones_usuario = list(SECCIONES.keys())
            else:
                secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
            if not secciones_usuario:
                st.warning("⚠️ No tienes acceso a ninguna sección. Contacta al administrador.")
            else:
                if 'seccion_seleccionada_documentos' in st.session_state:
                    seccion_preseleccionada = st.session_state.pop('seccion_seleccionada_documentos', None)
                else:
                    seccion_preseleccionada = None
                opciones_secciones = [(s, SECCIONES[s]['nombre']) for s in secciones_usuario]
                indice = 0
                if seccion_preseleccionada:
                    for idx, (sec_id, _) in enumerate(opciones_secciones):
                        if sec_id == seccion_preseleccionada:
                            indice = idx
                            break
                seccion_seleccionada = st.selectbox("Seleccionar sección:", opciones_secciones, format_func=lambda x: x[1], index=indice, key="selector_seccion")[0]
                seccion_info = SECCIONES[seccion_seleccionada]
                st.markdown(f"""
                <div style="background: {seccion_info['color']}10; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                    <h3>{seccion_info['icono']} {seccion_info['nombre']}</h3>
                    <p>{seccion_info['descripcion']}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("🔙 Volver al Dashboard"):
                    st.rerun()
                subcategorias_disponibles = seccion_info.get("subcategorias", ["General"])
                st.markdown("### 📂 Categorías")
                if 'categoria_seleccionada' not in st.session_state:
                    st.session_state['categoria_seleccionada'] = subcategorias_disponibles[0]
                st.markdown('<div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
                for cat in subcategorias_disponibles:
                    if st.button(cat, key=f"cat_{seccion_seleccionada}_{cat}", type="primary" if st.session_state['categoria_seleccionada'] == cat else "secondary"):
                        st.session_state['categoria_seleccionada'] = cat
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                categoria_actual = st.session_state['categoria_seleccionada']
                st.markdown(f"**Categoría actual:** {categoria_actual}")
                st.markdown("---")
                st.markdown("### 🔍 Buscador General")
                busqueda = st.text_input("Buscar por nombre de archivo o descripción:", key="buscador_general")

                # Documentos personales (solo master)
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
                        st.session_state['usuario'], seccion=seccion_seleccionada, subcategoria=categoria_actual, incluir_publicaciones=False
                    )
                    if busqueda:
                        archivos_personales = [a for a in archivos_personales if busqueda.lower() in a['nombre_original'].lower() or busqueda.lower() in a.get('descripcion', '').lower()]

                    if archivos_personales:
                        df_personal = pd.DataFrame([{
                            "ID": a['id'],
                            "Documento": a['nombre_original'],
                            "Fecha": a['fecha'][:10],
                            "Tamaño (KB)": round(a.get('tamaño_kb', a.get('tamaño_bytes', 0)/1024), 1)
                        } for a in archivos_personales])
                        st.dataframe(df_personal[["Documento", "Fecha", "Tamaño (KB)"]], use_container_width=True, hide_index=True)

                        opciones_docs = {a['nombre_original']: a['id'] for a in archivos_personales}
                        doc_seleccionado = st.selectbox("Selecciona un documento personal para gestionar:", list(opciones_docs.keys()), key="selector_doc_personal")
                        if doc_seleccionado:
                            doc_id = opciones_docs[doc_seleccionado]
                            archivo_data = next(a for a in archivos_personales if a['id'] == doc_id)
                            st.markdown(f"**Acciones para {doc_seleccionado}:**")
                            col_btn1, col_btn2, col_btn3 = st.columns(3)
                            with col_btn1:
                                if st.button("📥 Descargar", key=f"download_{doc_id}"):
                                    exito, resultado = storage_manager.descargar_archivo_personal(doc_id, st.session_state['usuario'])
                                    if exito:
                                        st.markdown(f'<a href="data:{resultado["mime_type"]};base64,{resultado["b64"]}" download="{resultado["nombre"]}">📥 Hacer clic para descargar</a>', unsafe_allow_html=True)
                                        st.success("✅ Descarga disponible")
                                    else:
                                        st.error(f"❌ {resultado}")
                            with col_btn2:
                                if st.button("🌍 Publicar", key=f"publish_{doc_id}"):
                                    st.session_state['archivo_a_publicar'] = doc_id
                                    st.session_state['show_publish_form'] = True
                            with col_btn3:
                                if st.button("🗑️ Eliminar", key=f"delete_{doc_id}"):
                                    exito, msg = storage_manager.eliminar_archivo(doc_id, st.session_state['usuario'])
                                    if exito:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                    else:
                        st.info("No tienes documentos personales en esta categoría")

                # Publicaciones del master
                st.markdown("### 📢 Publicaciones del Master")
                publicaciones = storage_manager.obtener_publicaciones_por_seccion(seccion=seccion_seleccionada, subcategoria=categoria_actual)
                if busqueda:
                    publicaciones = [p for p in publicaciones if busqueda.lower() in p['nombre_original'].lower() or busqueda.lower() in p.get('descripcion', '').lower()]

                if publicaciones:
                    df_pub = pd.DataFrame([{
                        "ID": p['id'],
                        "Documento": p['nombre_original'],
                        "Fecha": p['fecha'][:10],
                        "Descripción": (p.get('descripcion', '')[:50] + '...') if len(p.get('descripcion', '')) > 50 else p.get('descripcion', ''),
                        "Tamaño (KB)": round(p.get('tamaño_kb', 0), 1)
                    } for p in publicaciones])
                    st.dataframe(df_pub[["Documento", "Fecha", "Descripción", "Tamaño (KB)"]], use_container_width=True, hide_index=True)

                    if st.session_state['rol'] == 'master':
                        opciones_pub = {p['nombre_original']: p['id'] for p in publicaciones}
                        pub_seleccionada = st.selectbox("Selecciona una publicación para editar/eliminar:", list(opciones_pub.keys()), key="selector_pub")
                        if pub_seleccionada:
                            pub_id = opciones_pub[pub_seleccionada]
                            pub_data = next(p for p in publicaciones if p['id'] == pub_id)
                            st.markdown(f"**Acciones para {pub_seleccionada}:**")
                            col_pub1, col_pub2, col_pub3, col_pub4 = st.columns(4)
                            with col_pub1:
                                if st.button("📥 Descargar", key=f"download_pub_{pub_id}"):
                                    if seccion_seleccionada in secciones_usuario:
                                        exito, resultado = storage_manager.descargar_archivo(pub_id, st.session_state['usuario'], [seccion_seleccionada])
                                        if exito:
                                            st.markdown(f'<a href="data:{resultado["mime_type"]};base64,{resultado["b64"]}" download="{resultado["nombre"]}">📥 Descargar {resultado["nombre"]}</a>', unsafe_allow_html=True)
                                            st.success("✅ Descarga disponible")
                                        else:
                                            st.error(f"❌ {resultado}")
                                    else:
                                        st.error("No tienes permiso para descargar este documento")
                            with col_pub2:
                                with st.popover("✏️ Editar descripción"):
                                    nueva_desc = st.text_area("Nueva descripción", value=pub_data.get('descripcion', ''), height=100, key=f"edit_{pub_id}")
                                    if st.button("💾 Guardar", key=f"save_edit_{pub_id}"):
                                        exito, msg = storage_manager.editar_publicacion(pub_id, nueva_desc)
                                        if exito:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                            with col_pub3:
                                with st.popover("🗑️ Eliminar"):
                                    st.warning(f"¿Eliminar {pub_seleccionada}?")
                                    if st.button("✅ Sí, eliminar", key=f"confirm_del_{pub_id}"):
                                        exito, msg = storage_manager.eliminar_publicacion(pub_id)
                                        if exito:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                    if st.button("❌ Cancelar", key=f"cancel_del_{pub_id}"):
                                        st.rerun()
                            with col_pub4:
                                pass
                    else:
                        opciones_pub = {p['nombre_original']: p['id'] for p in publicaciones}
                        pub_seleccionada = st.selectbox("Selecciona una publicación para descargar:", list(opciones_pub.keys()), key="selector_pub_user")
                        if pub_seleccionada:
                            pub_id = opciones_pub[pub_seleccionada]
                            if st.button("📥 Descargar", key=f"download_user_{pub_id}"):
                                if seccion_seleccionada in secciones_usuario:
                                    exito, resultado = storage_manager.descargar_archivo(pub_id, st.session_state['usuario'], [seccion_seleccionada])
                                    if exito:
                                        st.markdown(f'<a href="data:{resultado["mime_type"]};base64,{resultado["b64"]}" download="{resultado["nombre"]}">📥 Descargar {resultado["nombre"]}</a>', unsafe_allow_html=True)
                                        st.success("✅ Descarga disponible")
                                    else:
                                        st.error(f"❌ {resultado}")
                                else:
                                    st.error("No tienes permiso para descargar este documento")
                else:
                    st.info("No hay publicaciones del master en esta categoría")

                # Formulario para publicar desde personal
                if st.session_state.get('show_publish_form', False) and st.session_state['rol'] == 'master':
                    with st.form("form_publicar_personal"):
                        st.markdown("### 📢 Publicar documento para todos los usuarios")
                        archivo_id = st.session_state['archivo_a_publicar']
                        archivo_nombre = "desconocido"
                        for a in archivos_personales:
                            if a["id"] == archivo_id:
                                archivo_nombre = a["nombre_original"]
                                break
                        st.info(f"Documento a publicar: **{archivo_nombre}**")
                        seccion_destino = st.selectbox("Sección destino:", options=list(SECCIONES.keys()), format_func=lambda x: SECCIONES[x]['nombre'], key="seccion_destino_pub")
                        subcategorias_destino = SECCIONES[seccion_destino].get("subcategorias", ["General"])
                        subcategoria_destino = st.selectbox("Subcategoría destino:", subcategorias_destino, key="subcat_destino_pub")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("✅ Confirmar publicación", use_container_width=True):
                                exito, resultado = storage_manager.publicar_desde_personal(archivo_id, st.session_state['usuario'], seccion_destino, subcategoria_destino)
                                if exito:
                                    st.success("✅ Documento publicado exitosamente para todos los usuarios")
                                    st.session_state.pop('show_publish_form', None)
                                    st.session_state.pop('archivo_a_publicar', None)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error: {resultado}")
                        with col2:
                            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                st.session_state.pop('show_publish_form', None)
                                st.session_state.pop('archivo_a_publicar', None)
                                st.rerun()

        # ============================================
        # GESTIÓN DE USUARIOS (Master) - CÓDIGO ORIGINAL
        # ============================================
        elif opcion == "👥 Gestión Usuarios" and st.session_state['rol'] == 'master':
            st.header("👥 Gestión de Usuarios y Permisos")
            tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuarios", "🔐 Asignar Secciones", "📢 Publicar Documentos"])
            with tab1:
                st.markdown("### Lista de Usuarios Registrados")
                usuarios = auth_manager.listar_usuarios()
                if usuarios:
                    datos_usuarios = []
                    for email, data in usuarios.items():
                        secciones = auth_manager.obtener_secciones_usuario(email)
                        datos_usuarios.append({
                            "Email": email,
                            "Nombre": data["nombre"],
                            "Rol": "👑 Master" if data["rol"] == "master" else "👤 Usuario",
                            "Secciones Acceso": f"{len(secciones)}/{len(SECCIONES)}"
                        })
                    df_usuarios = pd.DataFrame(datos_usuarios)
                    st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.markdown("### Eliminar Usuario")
                    usuarios_eliminar = [email for email in usuarios.keys() if email != st.session_state['usuario']]
                    if usuarios_eliminar:
                        usuario_a_eliminar = st.selectbox("Seleccionar usuario a eliminar:", usuarios_eliminar)
                        if st.button(f"🗑️ Eliminar Usuario", type="secondary"):
                            exito, msg = auth_manager.eliminar_usuario(usuario_a_eliminar, st.session_state['usuario'])
                            if exito:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                else:
                    st.info("No hay usuarios registrados")
            with tab2:
                st.markdown("### Asignar Secciones a Usuario")
                st.info("👑 El master puede asignar secciones específicas a cada usuario")
                usuarios_lista = [email for email in auth_manager.listar_usuarios().keys() if email != st.session_state['usuario']]
                if usuarios_lista:
                    usuario_seleccionado = st.selectbox("Seleccionar usuario:", usuarios_lista, key="select_usuario_permisos")
                    secciones_actuales = auth_manager.obtener_secciones_usuario(usuario_seleccionado)
                    st.markdown(f"**Secciones actuales de {usuario_seleccionado}:**")
                    if secciones_actuales:
                        for sec in secciones_actuales:
                            if sec in SECCIONES:
                                st.markdown(f"- {SECCIONES[sec]['icono']} {SECCIONES[sec]['nombre']}")
                    else:
                        st.warning("No tiene acceso a ninguna sección")
                    st.markdown("---")
                    st.markdown("### Seleccionar nuevas secciones:")
                    if not isinstance(secciones_actuales, list):
                        secciones_actuales = []
                    cols = st.columns(3)
                    nuevas_secciones = []
                    for i, (seccion_id, seccion_info) in enumerate(SECCIONES.items()):
                        col_idx = i % 3
                        with cols[col_idx]:
                            checkbox_key = f"perm_{usuario_seleccionado}_{seccion_id}"
                            if st.checkbox(
                                f"{seccion_info['icono']} {seccion_info['nombre']}",
                                value=(seccion_id in secciones_actuales),
                                key=checkbox_key
                            ):
                                nuevas_secciones.append(seccion_id)
                    if st.button("✅ Guardar Permisos", type="primary", use_container_width=True):
                        exito, msg = auth_manager.asignar_secciones_usuario(
                            usuario_seleccionado, nuevas_secciones, st.session_state['usuario']
                        )
                        if exito:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.info("No hay otros usuarios registrados para asignar permisos")
            with tab3:
                st.markdown("### Publicar Documento para Usuarios")
                st.info("📢 Los documentos publicados serán visibles y DESCARGABLES para los usuarios con acceso a la sección")
                seccion_publicacion = st.selectbox(
                    "Seleccionar sección para publicar:",
                    options=list(SECCIONES.keys()),
                    format_func=lambda x: f"{SECCIONES[x]['icono']} {SECCIONES[x]['nombre']}",
                    key="seccion_publicacion"
                )
                subcategorias = SECCIONES[seccion_publicacion].get("subcategorias", ["General"])
                subcategoria_publicacion = st.selectbox(
                    "Subcategoría:",
                    options=subcategorias,
                    key="subcategoria_publicacion"
                )
                archivo_publicacion = st.file_uploader(
                    "Seleccionar documento (PDF, Excel, Word)",
                    type=['pdf', 'xlsx', 'xls', 'docx', 'doc'],
                    key="publicacion_upload"
                )
                descripcion_publicacion = st.text_area(
                    "Descripción del documento (opcional)", 
                    placeholder="Ej: Facturas del mes de marzo 2026 - Documento importante para revisión",
                    height=100
                )
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                with col_btn2:
                    if archivo_publicacion and st.button("📢 Publicar Documento", type="primary", use_container_width=True):
                        exito, resultado = storage_manager.publicar_documento(
                            archivo_publicacion,
                            seccion_publicacion,
                            subcategoria_publicacion,
                            descripcion_publicacion
                        )
                        if exito:
                            st.success(f"✅ Documento publicado: {archivo_publicacion.name}")
                            st.info("Los usuarios con acceso a esta sección podrán DESCARGARLO desde su Dashboard")
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {resultado}")
                st.markdown("---")
                st.markdown("### 📢 Publicaciones Realizadas")
                todas_publicaciones = storage_manager.obtener_publicaciones_por_seccion()
                if todas_publicaciones:
                    for pub in todas_publicaciones:
                        with st.expander(f"📄 {pub['nombre_original']} - {pub['fecha'][:10]}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Sección:** {SECCIONES[pub['seccion']]['icono']} {SECCIONES[pub['seccion']]['nombre']}")
                                st.write(f"**Subcategoría:** {pub.get('subcategoria', 'General')}")
                                st.write(f"**Descripción:** {pub.get('descripcion', 'Sin descripción')}")
                                st.write(f"**Tamaño:** {pub.get('tamaño_kb', 0):.1f} KB")
                                st.write(f"**Publicado:** {pub['fecha']}")
                            with col2:
                                if st.button(f"🗑️ Eliminar", key=f"del_pub_{pub['id']}"):
                                    exito, msg = storage_manager.eliminar_publicacion(pub['id'])
                                    if exito:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                else:
                    st.info("No hay publicaciones aún")

        # ============================================
        # SISTEMA DE CONSULTAS - CÓDIGO ORIGINAL
        # ============================================
        elif opcion == "📬 Consultas":
            st.header("📬 Sistema de Consultas")
            if st.session_state['rol'] == 'master':
                tab1, tab2 = st.tabs(["📥 Consultas Recibidas", "📤 Respondidas"])
                with tab1:
                    st.markdown("### Consultas Pendientes")
                    mensajes_pendientes = message_manager.obtener_mensajes_para_master(respondidos=False)
                    if mensajes_pendientes:
                        for msg in mensajes_pendientes:
                            with st.container():
                                st.markdown(f"""
                                <div class="mensaje-card">
                                    <strong>👤 De: {msg['nombre_usuario']}</strong><br>
                                    <strong>📧 {msg['email']}</strong><br>
                                    <strong>📂 Sección: {SECCIONES[msg['seccion']]['icono']} {SECCIONES[msg['seccion']]['nombre']}</strong><br>
                                    <strong>📅 {msg['fecha']}</strong>
                                    <hr>
                                    <p><strong>Consulta:</strong> {msg['mensaje']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                with st.expander("✏️ Responder consulta"):
                                    respuesta = st.text_area("Escribe tu respuesta:", key=f"respuesta_{msg['id']}")
                                    if st.button("📤 Enviar Respuesta", key=f"enviar_{msg['id']}"):
                                        exito = message_manager.responder_mensaje(msg['id'], respuesta, st.session_state['usuario'])
                                        if exito:
                                            st.success("✅ Respuesta enviada al usuario")
                                            st.rerun()
                                        else:
                                            st.error("Error al enviar respuesta")
                                st.divider()
                    else:
                        st.info("No hay consultas pendientes")
                with tab2:
                    st.markdown("### Consultas Respondidas")
                    mensajes_respondidos = message_manager.obtener_mensajes_para_master(respondidos=True)
                    if mensajes_respondidos:
                        for msg in mensajes_respondidos:
                            st.markdown(f"""
                            <div class="mensaje-card">
                                <strong>👤 {msg['nombre_usuario']}</strong> - <strong>{msg['email']}</strong><br>
                                <strong>📂 Sección: {SECCIONES[msg['seccion']]['icono']} {SECCIONES[msg['seccion']]['nombre']}</strong><br>
                                <strong>📅 {msg['fecha']}</strong>
                                <hr>
                                <p><strong>Consulta:</strong> {msg['mensaje']}</p>
                                <div class="mensaje-respuesta">
                                    <strong>✅ Respuesta:</strong><br>
                                    {msg.get('respuesta', 'Sin respuesta')}
                                    <br>
                                    <small>Respondido por Master</small>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No hay consultas respondidas")
            else:
                st.markdown("### 📝 Enviar Consulta al Master")
                st.info("¿Tienes dudas sobre algún documento o necesitas asistencia? Envía tu consulta y el Master te responderá.")
                secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
                if not secciones_usuario:
                    st.warning("No tienes acceso a ninguna sección. Contacta al administrador.")
                else:
                    seccion_consulta = st.selectbox(
                        "Sección relacionada:",
                        options=secciones_usuario,
                        format_func=lambda x: f"{SECCIONES[x]['icono']} {SECCIONES[x]['nombre']}"
                    )
                    mensaje_consulta = st.text_area(
                        "Tu consulta:",
                        placeholder="Escribe aquí tu pregunta o comentario...",
                        height=150
                    )
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                    with col_btn2:
                        if st.button("📤 Enviar Consulta", type="primary", use_container_width=True):
                            if mensaje_consulta.strip():
                                exito, resultado = message_manager.enviar_mensaje(
                                    st.session_state['usuario'],
                                    st.session_state['nombre'],
                                    seccion_consulta,
                                    mensaje_consulta
                                )
                                if exito:
                                    st.success("✅ Consulta enviada correctamente. El Master te responderá pronto.")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error: {resultado}")
                            else:
                                st.warning("Por favor escribe tu consulta antes de enviar")
                st.markdown("---")
                st.markdown("### 📋 Mis Consultas Anteriores")
                historial = message_manager.obtener_mensajes_usuario(st.session_state['usuario'])
                if historial:
                    for msg in historial:
                        estado = "✅ Respondida" if msg.get('respondido') else "⏳ Pendiente"
                        st.markdown(f"""
                        <div class="mensaje-card">
                            <strong>📂 {SECCIONES[msg['seccion']]['icono']} {SECCIONES[msg['seccion']]['nombre']}</strong>
                            <span style="float: right;">{estado}</span><br>
                            <strong>📅 {msg['fecha']}</strong>
                            <hr>
                            <p><strong>Consulta:</strong> {msg['mensaje']}</p>
                        """, unsafe_allow_html=True)
                        if msg.get('respondido') and msg.get('respuesta'):
                            st.markdown(f"""
                            <div class="mensaje-respuesta">
                                <strong>✅ Respuesta del Master:</strong><br>
                                {msg['respuesta']}
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("No tienes consultas previas")

        # ============================================
        # MI PERFIL - CÓDIGO ORIGINAL (SIN PLANES)
        # ============================================
        elif opcion == "👤 Mi Perfil":
            st.header("👤 Mi Perfil")
            perfil = auth_manager.obtener_perfil(st.session_state['usuario'])
            tab_perfil, tab_editar, tab_estadisticas = st.tabs(["📋 Mi Información", "✏️ Editar Perfil", "📊 Estadísticas"])
            with tab_perfil:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                padding: 2rem;
                                border-radius: 15px;
                                text-align: center;
                                color: white;">
                        <h1 style="font-size: 3rem; margin: 0;">👤</h1>
                        <h3 style="margin: 0.5rem 0;">{perfil['nombre']}</h3>
                        <p style="margin: 0; opacity: 0.8;">{perfil['rol'].upper()}</p>
                        <hr style="margin: 1rem 0;">
                        <p><strong>Código:</strong><br>{perfil['codigo_usuario']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown("### 📋 Información Personal")
                    st.markdown("**📧 Correo Electrónico:**")
                    st.write(perfil['email'])
                    st.markdown("**📱 Teléfono:**")
                    st.write(perfil.get('telefono', 'No registrado'))
                    st.markdown("**📞 Celular:**")
                    st.write(perfil.get('celular', 'No registrado'))
                    st.markdown("**🏢 Empresa:**")
                    st.write(perfil.get('empresa', 'No registrada'))
                    st.markdown("**💼 Cargo:**")
                    st.write(perfil.get('cargo', 'No registrado'))
                    st.markdown("**📅 Fecha de Registro:**")
                    st.write(perfil.get('fecha_registro', 'No registrada')[:10])
                st.markdown("---")
                st.markdown("### 📂 Secciones con Acceso")
                secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
                if secciones_usuario:
                    cols = st.columns(4)
                    for i, sec in enumerate(secciones_usuario):
                        if sec in SECCIONES:
                            with cols[i % 4]:
                                st.markdown(f"""
                                <div style="background: {SECCIONES[sec]['color']}20;
                                            padding: 0.5rem;
                                            border-radius: 8px;
                                            margin: 0.25rem;
                                            text-align: center;">
                                    {SECCIONES[sec]['icono']} {SECCIONES[sec]['nombre']}
                                </div>
                                """, unsafe_allow_html=True)
                else:
                    st.warning("No tienes acceso a ninguna sección")
                st.markdown("---")
                st.markdown("### 📍 Dirección")
                st.write(f"**Dirección:** {perfil.get('direccion', 'No registrada')}")
                st.write(f"**Ciudad:** {perfil.get('ciudad', 'No registrada')}")
                st.write(f"**País:** {perfil.get('pais', 'Perú')}")
            with tab_editar:
                st.markdown("### ✏️ Editar Información Personal")
                st.info("Completa tus datos para mejorar tu experiencia")
                with st.form("editar_perfil_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nombre = st.text_input("Nombre completo", value=perfil.get('nombre', ''))
                        telefono = st.text_input("Teléfono", value=perfil.get('telefono', ''))
                        celular = st.text_input("Celular", value=perfil.get('celular', ''))
                        empresa = st.text_input("Empresa", value=perfil.get('empresa', ''))
                    with col2:
                        cargo = st.text_input("Cargo", value=perfil.get('cargo', ''))
                        direccion = st.text_input("Dirección", value=perfil.get('direccion', ''))
                        ciudad = st.text_input("Ciudad", value=perfil.get('ciudad', ''))
                        pais = st.selectbox("País", ["Perú", "Argentina", "Chile", "Colombia", "México", "España", "Otro"], 
                                           index=["Perú", "Argentina", "Chile", "Colombia", "México", "España", "Otro"].index(perfil.get('pais', 'Perú')))
                    st.markdown("---")
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                    with col_btn2:
                        if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                            datos_actualizados = {
                                "nombre": nombre,
                                "telefono": telefono,
                                "celular": celular,
                                "empresa": empresa,
                                "cargo": cargo,
                                "direccion": direccion,
                                "ciudad": ciudad,
                                "pais": pais
                            }
                            exito, msg = auth_manager.actualizar_perfil(st.session_state['usuario'], datos_actualizados)
                            if exito:
                                st.success(msg)
                                st.session_state['nombre'] = nombre
                                st.rerun()
                            else:
                                st.error(f"Error: {msg}")
            with tab_estadisticas:
                st.markdown("### 📊 Mis Estadísticas")
                archivos_personales = storage_manager.listar_archivos_usuario(st.session_state['usuario'], incluir_publicaciones=False)
                publicaciones = storage_manager.obtener_publicaciones_usuario(
                    st.session_state['usuario'], 
                    auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
                )
                secciones_usuario = auth_manager.obtener_secciones_usuario(st.session_state['usuario'])
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📄 Documentos Subidos", len(archivos_personales))
                with col2:
                    st.metric("📢 Documentos Disponibles", len(publicaciones))
                with col3:
                    st.metric("📂 Secciones Activas", len(secciones_usuario))
                with col4:
                    mensajes = message_manager.contar_no_leidos(st.session_state['usuario'])
                    st.metric("📬 Mensajes", mensajes)
                st.markdown("---")
                st.markdown("### 💾 Almacenamiento")
                espacio_usado_bytes = 0
                for archivo in archivos_personales:
                    espacio_usado_bytes += archivo.get('tamaño_bytes', 0)
                limite_mb = 2000
                espacio_usado_mb = espacio_usado_bytes / (1024 * 1024)
                porcentaje = min(100, (espacio_usado_mb / limite_mb) * 100)
                st.progress(porcentaje / 100)
                st.write(f"**Usado:** {espacio_usado_mb:.2f} MB de {limite_mb} MB")
                st.markdown("---")
                st.markdown("### 📋 Últimas Publicaciones")
                if publicaciones:
                    for pub in publicaciones[:5]:
                        st.markdown(f"""
                        <div style="background: #e8f4fd; padding: 0.5rem; border-radius: 8px; margin: 0.25rem 0;">
                            📢 <strong>{pub['nombre_original']}</strong><br>
                            <small>📅 {pub['fecha'][:10]} | 📂 {SECCIONES[pub['seccion']]['nombre']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No hay publicaciones disponibles")

        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; padding: 1rem;">
            <p>Optimizo con Pier - Gestión Documental Inteligente | © 2026</p>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error("❌ Ha ocurrido un error inesperado en la aplicación.")
        st.code(traceback.format_exc())
