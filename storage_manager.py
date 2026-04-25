# storage_manager.py - VERSIÓN CORREGIDA CON SUBCATEGORÍAS + DESCARGA PERSONAL + PUBLICACIÓN DESDE PERSONAL
import os
import shutil
from datetime import datetime
import json
import hashlib
import base64
import mimetypes

class StorageManager:
    def __init__(self):
        self.base_path = "uploads"
        self.publicaciones_path = "publicaciones"
        self.videos_path = "videos"
        self.db_path = "data/archivos.json"
        self.publicaciones_db_path = "data/publicaciones.json"
        self.videos_db_path = "data/videos.json"
        self.extensiones_permitidas = ['pdf', 'xlsx', 'xls', 'docx', 'doc']
        self.extensiones_video = ['mp4', 'avi', 'mov', 'mkv', 'webm']
        self.subcategorias_por_seccion = {
            "contabilidad": ["Administración", "Gestión", "Control", "Reportes"],
            "laboral": ["Contratos", "Nóminas", "Evaluaciones", "Legajos"],
            "financiero": ["Presupuestos", "Flujo de Caja", "Auditoría", "Impuestos"],
            "logistico": ["Inventarios", "Despachos", "Guías de Remisión", "Almacén"],
            "excel": ["Plantillas", "Dashboards", "Análisis de Datos", "Macros"]
        }
        self.asegurar_estructura()

    def asegurar_estructura(self):
        """Crear estructura de carpetas incluyendo subcategorías"""
        secciones = list(self.subcategorias_por_seccion.keys())
        carpetas = [self.base_path, self.publicaciones_path, self.videos_path, "data"]

        for sec in secciones:
            for sub in self.subcategorias_por_seccion[sec]:
                carpetas.append(os.path.join(self.base_path, sec, sub))
                carpetas.append(os.path.join(self.publicaciones_path, sec, sub))

        for carpeta in carpetas:
            if not os.path.exists(carpeta):
                os.makedirs(carpeta)

        for db in [self.db_path, self.publicaciones_db_path, self.videos_db_path]:
            if not os.path.exists(db):
                with open(db, 'w', encoding='utf-8') as f:
                    json.dump({}, f)

    def _validar_extension(self, archivo, es_video=False):
        """Validar extensión del archivo"""
        extension = archivo.name.split('.')[-1].lower()
        if es_video:
            return extension in self.extensiones_video
        return extension in self.extensiones_permitidas

    def _generar_nombre_seguro(self, archivo, usuario):
        """Generar nombre único y seguro para el archivo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_seguro = f"{timestamp}_{usuario}_{archivo.name}"
        nombre_seguro = "".join(c for c in nombre_seguro if c.isalnum() or c in '._-')
        return nombre_seguro, timestamp

    def guardar_archivo(self, archivo, seccion, subcategoria, usuario, descripcion="", es_publicacion=False):
        """Guardar archivo con subcategoría"""
        try:
            if not archivo:
                return False, "No se ha seleccionado ningún archivo"

            if not self._validar_extension(archivo):
                return False, f"Formato no permitido. Solo: {', '.join(self.extensiones_permitidas)}"

            if seccion not in self.subcategorias_por_seccion:
                return False, "Sección no válida"

            if subcategoria not in self.subcategorias_por_seccion.get(seccion, []):
                return False, "Subcategoría no válida para esta sección"

            # Generar nombre seguro
            nombre_seguro, timestamp = self._generar_nombre_seguro(archivo, usuario)

            # Determinar rutas
            if es_publicacion:
                ruta_destino = os.path.join(self.publicaciones_path, seccion, subcategoria, nombre_seguro)
                db_path = self.publicaciones_db_path
                tipo = "publicacion"
            else:
                ruta_destino = os.path.join(self.base_path, seccion, subcategoria, nombre_seguro)
                db_path = self.db_path
                tipo = "personal"

            # Asegurar que exista la carpeta
            os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)

            # Guardar archivo físicamente
            with open(ruta_destino, 'wb') as f:
                f.write(archivo.getbuffer())

            # Crear registro
            registro = {
                "id": hashlib.md5(f"{timestamp}{usuario}{archivo.name}".encode()).hexdigest(),
                "nombre_original": archivo.name,
                "nombre_guardado": nombre_seguro,
                "seccion": seccion,
                "subcategoria": subcategoria,
                "usuario": usuario,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tamaño_bytes": os.path.getsize(ruta_destino),
                "tamaño_kb": round(os.path.getsize(ruta_destino) / 1024, 2),
                "extension": archivo.name.split('.')[-1].lower(),
                "descripcion": descripcion,
                "tipo": tipo,
                "ruta_completa": ruta_destino
            }

            # Guardar en base de datos
            with open(db_path, 'r', encoding='utf-8') as f:
                archivos_db = json.load(f)

            if usuario not in archivos_db:
                archivos_db[usuario] = []

            archivos_db[usuario].append(registro)

            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(archivos_db, f, indent=4, ensure_ascii=False)

            return True, registro
        except Exception as e:
            return False, f"Error al guardar: {str(e)}"

    def publicar_documento(self, archivo, seccion, subcategoria, descripcion=""):
        """Publicar documento para todos los usuarios (desde panel Master)"""
        return self.guardar_archivo(archivo, seccion, subcategoria, "master", descripcion, es_publicacion=True)

    def obtener_publicaciones_por_seccion(self, seccion=None, subcategoria=None):
        """Obtener publicaciones filtrando por sección y opcionalmente por subcategoría"""
        try:
            with open(self.publicaciones_db_path, 'r', encoding='utf-8') as f:
                publicaciones_db = json.load(f)

            todas_publicaciones = []
            for autor, archivos in publicaciones_db.items():
                for archivo in archivos:
                    if seccion is not None and archivo["seccion"] != seccion:
                        continue
                    if subcategoria is not None and archivo.get("subcategoria") != subcategoria:
                        continue
                    todas_publicaciones.append(archivo)

            todas_publicaciones.sort(key=lambda x: x["fecha"], reverse=True)
            return todas_publicaciones
        except Exception as e:
            return []

    def obtener_publicaciones_usuario(self, usuario, secciones_usuario):
        """Obtener publicaciones visibles para un usuario según sus permisos"""
        try:
            todas_publicaciones = self.obtener_publicaciones_por_seccion()
            publicaciones_visibles = []
            for pub in todas_publicaciones:
                if pub["seccion"] in secciones_usuario:
                    pub_con_acceso = pub.copy()
                    pub_con_acceso["es_publicacion"] = True
                    publicaciones_visibles.append(pub_con_acceso)
            return publicaciones_visibles
        except Exception as e:
            return []

    def descargar_archivo(self, archivo_id, usuario_email, secciones_usuario):
        """Permitir descarga si el usuario tiene acceso a la sección (publicaciones)"""
        try:
            todas_publicaciones = self.obtener_publicaciones_por_seccion()
            archivo = None
            for pub in todas_publicaciones:
                if pub["id"] == archivo_id:
                    archivo = pub
                    break

            if not archivo:
                return False, "Documento no encontrado"

            if archivo["seccion"] not in secciones_usuario:
                return False, f"No tienes permiso para descargar este documento. Necesitas acceso a la sección {archivo['seccion']}"

            # Construir ruta con subcategoría
            ruta_archivo = os.path.join(
                self.publicaciones_path,
                archivo["seccion"],
                archivo.get("subcategoria", ""),
                archivo["nombre_guardado"]
            )
            if not os.path.exists(ruta_archivo):
                return False, "El archivo ya no está disponible físicamente"

            with open(ruta_archivo, 'rb') as f:
                contenido = f.read()

            mime_type, _ = mimetypes.guess_type(archivo["nombre_original"])
            if not mime_type:
                mime_type = 'application/octet-stream'

            b64 = base64.b64encode(contenido).decode()

            resultado = {
                "id": archivo["id"],
                "nombre": archivo["nombre_original"],
                "contenido": contenido,
                "b64": b64,
                "mime_type": mime_type,
                "tamaño_kb": archivo.get("tamaño_kb", round(len(contenido) / 1024, 2)),
                "seccion": archivo["seccion"],
                "subcategoria": archivo.get("subcategoria", ""),
                "fecha": archivo["fecha"]
            }

            return True, resultado
        except Exception as e:
            return False, f"Error al descargar: {str(e)}"

    # ========== NUEVOS MÉTODOS PARA DOCUMENTOS PERSONALES ==========

    def descargar_archivo_personal(self, archivo_id, usuario):
        """Permite al usuario descargar su propio documento personal"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                archivos_db = json.load(f)
            archivo = None
            for u, lista in archivos_db.items():
                if u == usuario:
                    for a in lista:
                        if a["id"] == archivo_id:
                            archivo = a
                            break
                if archivo:
                    break

            if not archivo:
                return False, "Documento personal no encontrado"

            ruta_archivo = archivo.get("ruta_completa")
            if not ruta_archivo or not os.path.exists(ruta_archivo):
                return False, "El archivo ya no existe físicamente"

            with open(ruta_archivo, 'rb') as f:
                contenido = f.read()

            mime_type, _ = mimetypes.guess_type(archivo["nombre_original"])
            if not mime_type:
                mime_type = 'application/octet-stream'

            b64 = base64.b64encode(contenido).decode()

            resultado = {
                "id": archivo["id"],
                "nombre": archivo["nombre_original"],
                "contenido": contenido,
                "b64": b64,
                "mime_type": mime_type,
                "tamaño_kb": archivo.get("tamaño_kb", round(len(contenido) / 1024, 2))
            }
            return True, resultado
        except Exception as e:
            return False, f"Error al descargar documento personal: {str(e)}"

    def publicar_desde_personal(self, archivo_id, usuario, seccion_destino, subcategoria_destino):
        """Convierte un documento personal en una publicación (copia a publicaciones)"""
        try:
            # 1. Buscar el archivo personal
            with open(self.db_path, 'r', encoding='utf-8') as f:
                archivos_db = json.load(f)
            archivo = None
            for u, lista in archivos_db.items():
                if u == usuario:
                    for a in lista:
                        if a["id"] == archivo_id:
                            archivo = a
                            break
                if archivo:
                    break

            if not archivo:
                return False, "Documento personal no encontrado"

            # 2. Validar sección y subcategoría destino
            if seccion_destino not in self.subcategorias_por_seccion:
                return False, "Sección destino no válida"
            if subcategoria_destino not in self.subcategorias_por_seccion.get(seccion_destino, []):
                return False, "Subcategoría destino no válida para esa sección"

            # 3. Verificar que el archivo original exista
            ruta_original = archivo.get("ruta_completa")
            if not ruta_original or not os.path.exists(ruta_original):
                return False, "El archivo original ya no existe"

            # 4. Copiar el archivo a la carpeta de publicaciones
            nuevo_nombre = archivo["nombre_guardado"]  # reutilizamos el mismo nombre único
            ruta_destino = os.path.join(self.publicaciones_path, seccion_destino, subcategoria_destino, nuevo_nombre)
            os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
            shutil.copy2(ruta_original, ruta_destino)

            # 5. Crear el registro de publicación
            nueva_publicacion = {
                "id": hashlib.md5(f"{archivo['id']}_published_{datetime.now().timestamp()}".encode()).hexdigest(),
                "nombre_original": archivo["nombre_original"],
                "nombre_guardado": nuevo_nombre,
                "seccion": seccion_destino,
                "subcategoria": subcategoria_destino,
                "usuario": "master",  # se publica como master
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tamaño_bytes": archivo["tamaño_bytes"],
                "tamaño_kb": archivo["tamaño_kb"],
                "extension": archivo["extension"],
                "descripcion": archivo.get('descripcion', ''),
                "tipo": "publicacion",
                "ruta_completa": ruta_destino
            }

            # 6. Guardar en la base de datos de publicaciones
            with open(self.publicaciones_db_path, 'r', encoding='utf-8') as f:
                publicaciones_db = json.load(f)

            if "master" not in publicaciones_db:
                publicaciones_db["master"] = []
            publicaciones_db["master"].append(nueva_publicacion)

            with open(self.publicaciones_db_path, 'w', encoding='utf-8') as f:
                json.dump(publicaciones_db, f, indent=4, ensure_ascii=False)

            return True, nueva_publicacion
        except Exception as e:
            return False, f"Error al publicar desde personal: {str(e)}"

    # ========== FIN MÉTODOS NUEVOS ==========

    def listar_archivos_usuario(self, usuario, seccion=None, subcategoria=None, incluir_publicaciones=False, secciones_usuario=None):
        """Listar archivos del usuario (personales + publicaciones) filtrando por sección y subcategoría"""
        archivos = []

        # Archivos personales
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                archivos_db = json.load(f)
            if usuario in archivos_db:
                archivos.extend(archivos_db[usuario])
        except Exception as e:
            pass

        # Publicaciones (si tiene permisos)
        if incluir_publicaciones and secciones_usuario:
            publicaciones = self.obtener_publicaciones_usuario(usuario, secciones_usuario)
            archivos.extend(publicaciones)

        # Filtrar por sección
        if seccion:
            archivos = [a for a in archivos if a["seccion"] == seccion]

        # Filtrar por subcategoría
        if subcategoria:
            archivos = [a for a in archivos if a.get("subcategoria") == subcategoria]

        # Ordenar por fecha (más recientes primero)
        archivos.sort(key=lambda x: x["fecha"], reverse=True)
        return archivos

    def eliminar_archivo(self, archivo_id, usuario, es_publicacion=False):
        """Eliminar archivo por ID (soporta archivos personales y públicos)"""
        try:
            db_path = self.publicaciones_db_path if es_publicacion else self.db_path
            base_dir = self.publicaciones_path if es_publicacion else self.base_path

            with open(db_path, 'r', encoding='utf-8') as f:
                archivos_db = json.load(f)

            for u in list(archivos_db.keys()):
                for i, archivo in enumerate(archivos_db[u]):
                    if archivo["id"] == archivo_id:
                        # Verificar permisos
                        if not es_publicacion and u != usuario:
                            return False, "No tienes permiso para eliminar este archivo"
                        if es_publicacion and usuario != "master":
                            return False, "Solo el Master puede eliminar publicaciones"

                        # Construir ruta con subcategoría
                        ruta = os.path.join(
                            base_dir,
                            archivo["seccion"],
                            archivo.get("subcategoria", ""),
                            archivo["nombre_guardado"]
                        )
                        if os.path.exists(ruta):
                            os.remove(ruta)

                        del archivos_db[u][i]
                        if not archivos_db[u]:
                            del archivos_db[u]

                        with open(db_path, 'w', encoding='utf-8') as f:
                            json.dump(archivos_db, f, indent=4, ensure_ascii=False)

                        return True, f"Archivo '{archivo['nombre_original']}' eliminado correctamente"

            return False, "Archivo no encontrado"
        except Exception as e:
            return False, f"Error al eliminar: {str(e)}"

    def eliminar_publicacion(self, publicacion_id):
        """Eliminar publicación (solo master)"""
        return self.eliminar_archivo(publicacion_id, "master", es_publicacion=True)

    def guardar_video_tutorial(self, archivo_video, seccion, titulo):
        """Guardar video tutorial con validaciones"""
        try:
            if not archivo_video:
                return False, "No se ha seleccionado ningún video"

            if not self._validar_extension(archivo_video, es_video=True):
                return False, f"Formato de video no permitido. Solo: {', '.join(self.extensiones_video)}"

            if not titulo.strip():
                return False, "El título es obligatorio"

            nombre_video = f"tutorial_{seccion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{archivo_video.name.split('.')[-1].lower()}"
            ruta = os.path.join(self.videos_path, nombre_video)

            with open(ruta, 'wb') as f:
                f.write(archivo_video.getbuffer())

            with open(self.videos_db_path, 'r', encoding='utf-8') as f:
                videos_db = json.load(f)

            video_info = {
                "id": hashlib.md5(nombre_video.encode()).hexdigest(),
                "seccion": seccion,
                "titulo": titulo,
                "archivo": nombre_video,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "tamaño_kb": round(os.path.getsize(ruta) / 1024, 2),
                "ruta": ruta
            }

            if seccion not in videos_db:
                videos_db[seccion] = []
            videos_db[seccion].append(video_info)

            with open(self.videos_db_path, 'w', encoding='utf-8') as f:
                json.dump(videos_db, f, indent=4, ensure_ascii=False)

            return True, video_info
        except Exception as e:
            return False, f"Error al guardar video: {str(e)}"

    def obtener_videos_tutoriales(self, seccion):
        """Obtener videos tutoriales de una sección"""
        try:
            if not os.path.exists(self.videos_db_path):
                return []
            with open(self.videos_db_path, 'r', encoding='utf-8') as f:
                videos_db = json.load(f)
            return videos_db.get(seccion, [])
        except Exception as e:
            return []

    def eliminar_video_tutorial(self, video_id, seccion):
        """Eliminar video tutorial"""
        try:
            with open(self.videos_db_path, 'r', encoding='utf-8') as f:
                videos_db = json.load(f)

            if seccion in videos_db:
                for i, video in enumerate(videos_db[seccion]):
                    if video["id"] == video_id:
                        ruta = os.path.join(self.videos_path, video["archivo"])
                        if os.path.exists(ruta):
                            os.remove(ruta)
                        del videos_db[seccion][i]

                        with open(self.videos_db_path, 'w', encoding='utf-8') as f:
                            json.dump(videos_db, f, indent=4, ensure_ascii=False)
                        return True, f"Video '{video['titulo']}' eliminado"
            return False, "Video no encontrado"
        except Exception as e:
            return False, f"Error al eliminar video: {str(e)}"

    def obtener_estadisticas_almacenamiento(self):
        """Obtener estadísticas de almacenamiento (para dashboard master)"""
        try:
            total_archivos = 0
            total_publicaciones = 0
            total_tamaño_bytes = 0

            with open(self.db_path, 'r', encoding='utf-8') as f:
                archivos_db = json.load(f)
            for usuario, archivos in archivos_db.items():
                total_archivos += len(archivos)
                for archivo in archivos:
                    total_tamaño_bytes += archivo.get("tamaño_bytes", 0)

            with open(self.publicaciones_db_path, 'r', encoding='utf-8') as f:
                publicaciones_db = json.load(f)
            for autor, archivos in publicaciones_db.items():
                total_publicaciones += len(archivos)
                for archivo in archivos:
                    total_tamaño_bytes += archivo.get("tamaño_bytes", 0)

            return {
                "total_archivos_personales": total_archivos,
                "total_publicaciones": total_publicaciones,
                "total_archivos": total_archivos + total_publicaciones,
                "total_tamaño_mb": round(total_tamaño_bytes / (1024 * 1024), 2)
            }
        except Exception as e:
            return {
                "total_archivos_personales": 0,
                "total_publicaciones": 0,
                "total_archivos": 0,
                "total_tamaño_mb": 0
            }
    def editar_publicacion(self, publicacion_id, nueva_descripcion):
        """Edita la descripción de una publicación existente"""
        try:
            with open(self.publicaciones_db_path, 'r', encoding='utf-8') as f:
                publicaciones_db = json.load(f)
            
            encontrado = False
            for autor, archivos in publicaciones_db.items():
                for i, pub in enumerate(archivos):
                    if pub["id"] == publicacion_id:
                        publicaciones_db[autor][i]["descripcion"] = nueva_descripcion
                        publicaciones_db[autor][i]["fecha_edicion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        encontrado = True
                        break
                if encontrado:
                    break
            
            if not encontrado:
                return False, "Publicación no encontrada"
            
            with open(self.publicaciones_db_path, 'w', encoding='utf-8') as f:
                json.dump(publicaciones_db, f, indent=4, ensure_ascii=False)
            
            return True, "Publicación actualizada correctamente"
        
        except Exception as e:
            return False, f"Error al editar: {str(e)}"