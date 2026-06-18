# storage_manager.py - Versión robusta y profesional
import streamlit as st
from supabase_client import get_supabase
import uuid
from datetime import datetime
import mimetypes
import unicodedata
from notification_manager import NotificationManager, MENSAJE_NOTIF_NUEVO_DOCUMENTO, normalizar_seccion

def limpiar_ruta(texto):
    """Limpia una ruta eliminando tildes y convirtiendo a minúsculas."""
    texto_normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto_normalizado.lower().strip()

class StorageManager:
    def __init__(self):
        self.supabase = get_supabase()
        self.bucket_name = "documentos"

    def _notificar_publicacion_alumnos(self, titulo, mensaje, metadata, publicador_email=None):
        """Notifica a alumnos. Retorna (ok, cantidad, error)."""
        try:
            notif_mgr = NotificationManager()
            ok, count, err = notif_mgr.crear_notificacion_para_alumnos(
                titulo=titulo,
                mensaje=mensaje,
                metadata=metadata,
                publicador_email=publicador_email,
            )
            if not ok and err:
                st.error(f"Error al crear notificaciones en Supabase: {err}")
            return ok, count, err
        except Exception as e:
            err = str(e)
            print(f"Error al notificar publicación: {err}")
            st.error(f"Error al crear notificaciones en Supabase: {err}")
            return False, 0, err

    def _subir_archivo(self, archivo, carpeta):
        """Sube un archivo al bucket y retorna (url, nombre_guardado)."""
        partes_carpeta = [limpiar_ruta(parte) for parte in carpeta.split("/")]
        carpeta_limpia = "/".join(partes_carpeta)
        extension = archivo.name.split('.')[-1].lower()
        nombre_unico = f"{uuid.uuid4()}.{extension}"
        ruta_destino = f"{carpeta_limpia}/{nombre_unico}"
        self.supabase.storage.from_(self.bucket_name).upload(
            ruta_destino, archivo.getvalue(), {"content-type": archivo.type}
        )
        url = self.supabase.storage.from_(self.bucket_name).get_public_url(ruta_destino)
        return url, nombre_unico

    def guardar_archivo(self, archivo, seccion, subcategoria, usuario, descripcion="", es_publicacion=False):
        """
        Guarda un archivo (personal o publicación).
        Retorna (éxito, resultado) donde resultado es dict con datos o mensaje de error.
        """
        if not archivo:
            return False, "No se ha seleccionado ningún archivo"

        descripcion_texto = (descripcion or "").strip()

        try:
            if es_publicacion:
                seccion_limpia = normalizar_seccion(seccion)
                carpeta = f"publicaciones/{seccion_limpia}/{subcategoria}"
                tabla = "publicaciones"
                data_insert = {
                    "id": str(uuid.uuid4()),
                    "nombre_original": archivo.name,
                    "seccion": seccion_limpia, # <-- Esto garantiza consistencia con la tabla users
                    "subcategoria": subcategoria,
                    "descripcion": descripcion_texto,
                    "titulo": archivo.name,
                    "mensaje": descripcion_texto,
                    "categoria": subcategoria,          
                    "creado_por": "master"
                }
            else:
                carpeta = f"personales/{usuario}/{seccion}/{subcategoria}"
                tabla = "archivos_personales"
                data_insert = {
                    "id": str(uuid.uuid4()),
                    "usuario_email": usuario,
                    "nombre_original": archivo.name,
                    "nombre_guardado": None,
                    "seccion": seccion,
                    "subcategoria": subcategoria,
                    "descripcion": descripcion,
                }

            url, nombre_guardado = self._subir_archivo(archivo, carpeta)
            tamaño_bytes = len(archivo.getvalue())
            tamaño_kb = round(tamaño_bytes / 1024, 2)
            extension = archivo.name.split('.')[-1].lower()

            data_insert.update({
                "nombre_guardado": nombre_guardado,
                "fecha": datetime.now().isoformat(),
                "tamaño_bytes": tamaño_bytes,
                "tamaño_kb": tamaño_kb,
                "extension": extension,
                "ruta_completa": url
            })

            result = self.supabase.table(tabla).insert(data_insert).execute()
            if result.data:
                return True, data_insert
            else:
                return False, "Error al insertar en la base de datos"
        except Exception as e:
            return False, f"Error al guardar archivo: {str(e)}"

    def publicar_documento(self, archivo, seccion, subcategoria, descripcion="", publicador_email=None):
        """Publica un documento directamente desde el panel de administración."""
        descripcion_texto = (descripcion or "").strip()
        exito, resultado = self.guardar_archivo(
            archivo, seccion, subcategoria, "master", descripcion_texto, es_publicacion=True
        )
        if exito and isinstance(resultado, dict):
            seccion_guardada = normalizar_seccion(resultado.get("seccion") or seccion)
            resultado["seccion"] = seccion_guardada
            titulo_notif = resultado.get("nombre_original") or archivo.name
            ok, count, err = self._notificar_publicacion_alumnos(
                titulo=titulo_notif,
                mensaje=MENSAJE_NOTIF_NUEVO_DOCUMENTO,
                metadata={
                    "seccion": seccion_guardada,
                    "subcategoria": subcategoria,
                    "archivo_id": resultado["id"],
                },
                publicador_email=publicador_email,
            )
            resultado["notificaciones_creadas"] = count
            resultado["notificacion_error"] = err
            resultado["notificaciones_ok"] = ok
        return exito, resultado

    def listar_archivos_usuario(self, usuario, seccion=None, subcategoria=None, incluir_publicaciones=False):
        """Lista archivos personales (y opcionalmente publicaciones) de un usuario."""
        archivos = []
        try:
            query = self.supabase.table("archivos_personales").select("*").eq("usuario_email", usuario)
            if seccion:
                query = query.eq("seccion", seccion)
            if subcategoria:
                query = query.eq("subcategoria", subcategoria)
            archivos.extend(query.execute().data or [])

            if incluir_publicaciones:
                qpub = self.supabase.table("publicaciones").select("*")
                if seccion:
                    qpub = qpub.eq("seccion", seccion)
                archivos.extend(qpub.execute().data or [])

            archivos.sort(key=lambda x: x.get("fecha", ""), reverse=True)
        except Exception as e:
            print(f"Error listando archivos: {e}")
        return archivos

    def obtener_publicaciones_por_seccion(self, seccion=None, subcategoria=None):
        """Obtiene publicaciones filtradas por sección y subcategoría (opcionales)."""
        try:
            query = self.supabase.table('publicaciones').select('*')
            if seccion:
                query = query.eq('seccion', seccion)
            if subcategoria:
                query = query.eq('subcategoria', subcategoria)
            query = query.order('fecha_creacion', desc=True)
            return query.execute().data or []
        except Exception as e:
            print(f"Error en obtener_publicaciones_por_seccion: {e}")
            return []

    @staticmethod
    def _icono_tipo_archivo(nombre_archivo: str) -> str:
        ext = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        iconos = {
            "pdf": "📕",
            "xlsx": "📊",
            "xls": "📊",
            "docx": "📘",
            "doc": "📘",
            "pptx": "📙",
            "ppt": "📙",
        }
        return iconos.get(ext, "📄")

    def normalizar_metadatos_documento(self, registro, es_publicacion=True):
        """Metadatos uniformes para UI compacta y catálogo del chatbot."""
        nombre = (registro.get("nombre_original") or registro.get("titulo") or "Sin título").strip()
        fecha_raw = registro.get("fecha") or registro.get("fecha_creacion") or ""
        ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        return {
            "id": registro.get("id"),
            "nombre": nombre,
            "nombre_original": nombre,
            "descripcion": (registro.get("descripcion") or registro.get("mensaje") or "").strip(),
            "fecha": str(fecha_raw)[:10],
            "fecha_raw": fecha_raw,
            "seccion": registro.get("seccion", ""),
            "subcategoria": registro.get("subcategoria", ""),
            "extension": ext,
            "icono": self._icono_tipo_archivo(nombre),
            "es_publicacion": es_publicacion,
            "tamaño_kb": registro.get("tamaño_kb"),
        }

    def listar_catalogo_seccion(self, seccion, subcategoria=None):
        """Lista de diccionarios normalizados para UI y chatbot."""
        publicaciones = self.obtener_publicaciones_por_seccion(seccion, subcategoria)
        return [self.normalizar_metadatos_documento(p, es_publicacion=True) for p in publicaciones]

    def listar_metadatos_personales(self, usuario, seccion=None, subcategoria=None):
        """Metadatos normalizados de archivos personales del usuario."""
        archivos = self.listar_archivos_usuario(
            usuario,
            seccion=seccion,
            subcategoria=subcategoria,
            incluir_publicaciones=False,
        )
        return [self.normalizar_metadatos_documento(a, es_publicacion=False) for a in archivos]

    def listar_catalogo_seccion_dataframe(self, seccion, subcategoria=None):
        """DataFrame limpio para consultas del chatbot o exportación."""
        import pandas as pd

        catalogo = self.listar_catalogo_seccion(seccion, subcategoria)
        columnas = [
            "id", "nombre", "descripcion", "fecha", "seccion",
            "subcategoria", "extension", "icono", "es_publicacion",
        ]
        if not catalogo:
            return pd.DataFrame(columns=columnas)
        return pd.DataFrame(catalogo)[columnas]

    def obtener_publicaciones_usuario(self, usuario, secciones_usuario):
        """Filtra publicaciones según las secciones a las que el usuario tiene acceso."""
        todas = self.obtener_publicaciones_por_seccion()
        visibles = []
        for pub in todas:
            if pub.get("seccion") in secciones_usuario:
                pub_copy = pub.copy()
                pub_copy["es_publicacion"] = True
                visibles.append(pub_copy)
        return visibles

    def _usuario_es_master(self, usuario_email: str) -> bool:
        try:
            result = self.supabase.table("users").select("rol").eq("email", usuario_email).execute()
            if not result.data:
                return False
            return (result.data[0].get("rol") or "").lower() == "master"
        except Exception:
            return False

    def descargar_archivo(self, archivo_id, usuario_email, secciones_usuario):
        """Descarga un archivo (público o personal) verificando permisos."""
        try:
            # Buscar primero en publicaciones
            result = self.supabase.table("publicaciones").select("*").eq("id", archivo_id).execute()
            if not result.data:
                result = self.supabase.table("archivos_personales").select("*").eq("id", archivo_id).execute()
            if not result.data:
                return False, "Archivo no encontrado"

            archivo = result.data[0]
            # Verificar permiso si no es master
            if not self._usuario_es_master(usuario_email) and archivo.get("seccion") not in secciones_usuario:
                return False, "No tienes permiso para descargar este documento"

            url = archivo["ruta_completa"]
            mime, _ = mimetypes.guess_type(archivo["nombre_original"])
            return True, {"nombre": archivo["nombre_original"], "url": url, "mime_type": mime or "application/octet-stream"}
        except Exception as e:
            return False, f"Error al descargar: {str(e)}"

    def descargar_archivo_personal(self, archivo_id, usuario):
        """Descarga un archivo personal del usuario."""
        try:
            result = self.supabase.table("archivos_personales").select("*").eq("id", archivo_id).eq("usuario_email", usuario).execute()
            if not result.data:
                return False, "Documento no encontrado"
            archivo = result.data[0]
            url = archivo["ruta_completa"]
            mime, _ = mimetypes.guess_type(archivo["nombre_original"])
            return True, {"nombre": archivo["nombre_original"], "url": url, "mime_type": mime or "application/octet-stream"}
        except Exception as e:
            return False, f"Error al descargar: {str(e)}"

    def eliminar_archivo(self, archivo_id, usuario, es_publicacion=False):
        """Elimina un archivo (personal o publicación) y su registro en BD."""
        try:
            supabase = self.supabase
            tabla = "publicaciones" if es_publicacion else "archivos_personales"
            query = supabase.table(tabla).select("*").eq("id", archivo_id)
            if not es_publicacion:
                query = query.eq("usuario_email", usuario)
            result = query.execute()
            if not result.data:
                return False, "Archivo no encontrado"

            archivo = result.data[0]
            ruta_url = archivo["ruta_completa"]
            try:
                path = ruta_url.split(f"/object/public/{self.bucket_name}/")[-1]
                supabase.storage.from_(self.bucket_name).remove([path])
            except Exception:
                pass  # El archivo podría no existir en storage, se omite

            supabase.table(tabla).delete().eq("id", archivo_id).execute()
            return True, "Archivo eliminado correctamente"
        except Exception as e:
            return False, f"Error al eliminar: {str(e)}"

    def eliminar_publicacion(self, publicacion_id):
        """Elimina una publicación (wrapper)."""
        return self.eliminar_archivo(publicacion_id, "master", es_publicacion=True)

    def editar_publicacion(self, publicacion_id, nueva_descripcion):
        """Edita la descripción de una publicación."""
        try:
            result = self.supabase.table("publicaciones").update({"descripcion": nueva_descripcion}).eq("id", publicacion_id).execute()
            if result.data:
                return True, "Descripción actualizada exitosamente."
            else:
                return False, "No se encontró la publicación para editar."
        except Exception as e:
            return False, f"Error al editar: {str(e)}"

    def publicar_desde_personal(self, archivo_id, usuario, seccion, subcategoria, descripcion=""):
        """Publica un documento que originalmente era personal, convirtiéndolo en publicación global."""
        try:
            # Obtener el documento personal
            result = self.supabase.table("archivos_personales").select("*").eq("id", archivo_id).execute()
            if not result.data:
                return False, "Documento personal no encontrado"
            doc = result.data[0]

            if doc["usuario_email"] != usuario:
                return False, "No tienes permiso para publicar este documento"

            # Extraer ruta relativa
            ruta_completa = doc["ruta_completa"]
            if f"/object/public/{self.bucket_name}/" in ruta_completa:
                ruta_relativa = ruta_completa.split(f"/object/public/{self.bucket_name}/")[-1]
            else:
                return False, "No se pudo determinar la ruta del archivo en Storage"

            # Descargar contenido original
            contenido = self.supabase.storage.from_(self.bucket_name).download(ruta_relativa)

            # Preparar nueva ruta en publicaciones
            seccion_limpia = normalizar_seccion(seccion)
            carpeta_dest = f"publicaciones/{seccion_limpia}/{subcategoria}"
            partes_limpias = [limpiar_ruta(p) for p in carpeta_dest.split("/")]
            ruta_nueva = "/".join(partes_limpias) + "/" + doc["nombre_guardado"]

            # Subir a la carpeta de publicaciones
            self.supabase.storage.from_(self.bucket_name).upload(
                path=ruta_nueva,
                file=contenido,
                file_options={"content-type": "application/octet-stream"}
            )
            url_publica = self.supabase.storage.from_(self.bucket_name).get_public_url(ruta_nueva)

            # Crear registro en publicaciones
            nuevo_id = str(uuid.uuid4())
            registro_pub = {
                "id": nuevo_id,
                "nombre_original": doc["nombre_original"],
                "nombre_guardado": doc["nombre_guardado"],
                "seccion": seccion_limpia,
                "subcategoria": subcategoria,
                "fecha": datetime.now().isoformat(),
                "descripcion": descripcion or doc.get("descripcion", ""),
                "tamaño_bytes": doc["tamaño_bytes"],
                "tamaño_kb": doc["tamaño_kb"],
                "extension": doc["extension"],
                "ruta_completa": url_publica,
                "titulo": doc["nombre_original"],
                "mensaje": descripcion or doc.get("descripcion", ""),
                "categoria": subcategoria,
                "creado_por": usuario
            }
            self.supabase.table("publicaciones").insert(registro_pub).execute()
        except Exception as e:
            return False, f"Error al publicar: {str(e)}"

        ok, count, err = self._notificar_publicacion_alumnos(
            titulo=registro_pub["titulo"],
            mensaje=MENSAJE_NOTIF_NUEVO_DOCUMENTO,
            metadata={
                "seccion": seccion_limpia,
                "subcategoria": subcategoria,
                "archivo_id": nuevo_id,
            },
            publicador_email=usuario,
        )
        return True, {
            "mensaje": "Documento publicado exitosamente",
            "notificaciones_creadas": count,
            "notificacion_error": err,
            "notificaciones_ok": ok,
        }