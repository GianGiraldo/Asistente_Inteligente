# storage_manager.py - Versión definitiva con obtener_publicaciones_usuario
import streamlit as st
from supabase_client import get_supabase
import uuid
from datetime import datetime
import mimetypes
import unicodedata
from notification_manager import NotificationManager

def limpiar_ruta(texto):
    # Convierte caracteres como 'ó' a 'o', 'ó' a 'o', etc., y lo pasa a minúsculas
    texto_normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    # Opcional: Reemplazar espacios por guiones si prefieres rutas más limpias
    return texto_normalizado.lower().strip()

class StorageManager:
    def __init__(self):
        self.supabase = get_supabase()
        self.bucket_name = "documentos"

    def _subir_archivo(self, archivo, carpeta):
        # 1. Limpiamos la carpeta para quitar tildes, espacios raros o mayúsculas antes de subir
        # Si 'carpeta' viene como "personales/master@optimizo.com/contabilidad/Administración"
        # lo separamos por "/" para limpiar cada fragmento individualmente
        partes_carpeta = [limpiar_ruta(parte) for parte in carpeta.split("/")]
        carpeta_limpia = "/".join(partes_carpeta)
        
        # 2. Procesamos el archivo de forma normal
        extension = archivo.name.split('.')[-1].lower()
        nombre_unico = f"{uuid.uuid4()}.{extension}"
        
        # 3. Construimos la ruta de destino usando la carpeta limpia
        ruta_destino = f"{carpeta_limpia}/{nombre_unico}"
        
        self.supabase.storage.from_(self.bucket_name).upload(
            ruta_destino, archivo.getvalue(), {"content-type": archivo.type}
        )
        url = self.supabase.storage.from_(self.bucket_name).get_public_url(ruta_destino)
        return url, nombre_unico

    def guardar_archivo(self, archivo, seccion, subcategoria, usuario, descripcion="", es_publicacion=False):
        if not archivo:
            return False, "No se ha seleccionado ningún archivo"
        if es_publicacion:
            carpeta = f"publicaciones/{seccion}/{subcategoria}"
            tabla = "publicaciones"
            data_insert = {
                "id": str(uuid.uuid4()),
                "nombre_original": archivo.name,
                "nombre_guardado": None,
                "seccion": seccion,
                "subcategoria": subcategoria,
                "descripcion": descripcion,
                "titulo": archivo.name,                
                "mensaje": descripcion or "",          
                "categoria": subcategoria,             
                "creado_por": "master" if es_publicacion else usuario
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
        return (True, data_insert) if result.data else (False, "Error al guardar")

    def publicar_documento(self, archivo, seccion, subcategoria, descripcion=""):
        exito, resultado = self.guardar_archivo(archivo, seccion, subcategoria, "master", descripcion, es_publicacion=True)
        if exito:
            notif_mgr = NotificationManager()
            notif_mgr.crear_notificacion_para_todos(
                titulo="📢 Nueva publicación",
                mensaje=f"Se ha publicado un nuevo documento: {archivo.name} en la sección {seccion}",
                tipo="publicacion",
                metadata={"seccion": seccion, "subcategoria": subcategoria, "archivo_id": resultado["id"]}
            )
            return exito, resultado

    def listar_archivos_usuario(self, usuario, seccion=None, subcategoria=None, incluir_publicaciones=False):
        archivos = []
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
        archivos.sort(key=lambda x: x["fecha"], reverse=True)
        return archivos

    def obtener_publicaciones_por_seccion(self, seccion=None, subcategoria=None):
        try:
            query = self.supabase.table('publicaciones').select('*')
            if seccion:
                query = query.eq('seccion', seccion)
            # La columna se llama 'categoría' (con tilde) o 'categoria'? Verifica en Supabase.
            # Si tiene tilde, usa 'categoría', si no, 'categoria'.
            if subcategoria:
                query = query.eq('subcategoria', subcategoria)  # Ajusta el nombre exacto de la columna
            query = query.order('fecha_creacion', desc=True)
            return query.execute().data or []
        except Exception as e:
            print(f"Error: {e}")
            return []

    def obtener_publicaciones_usuario(self, usuario, secciones_usuario):
        """Obtiene las publicaciones a las que el usuario tiene acceso según sus secciones asignadas."""
        todas = self.obtener_publicaciones_por_seccion()
        visibles = []
        for pub in todas:
            if pub.get("seccion") in secciones_usuario:
                pub_copy = pub.copy()
                pub_copy["es_publicacion"] = True
                visibles.append(pub_copy)
        return visibles

    def descargar_archivo(self, archivo_id, usuario_email, secciones_usuario):
        result = self.supabase.table("publicaciones").select("*").eq("id", archivo_id).execute()
        if not result.data:
            result = self.supabase.table("archivos_personales").select("*").eq("id", archivo_id).execute()
        if result.data:
            archivo = result.data[0]
            if usuario_email != "master@optimizo.com" and archivo.get("seccion") not in secciones_usuario:
                return False, "No tienes permiso"
            url = archivo["ruta_completa"]
            mime, _ = mimetypes.guess_type(archivo["nombre_original"])
            return True, {"nombre": archivo["nombre_original"], "url": url, "mime_type": mime or "application/octet-stream"}
        return False, "Archivo no encontrado"

    def descargar_archivo_personal(self, archivo_id, usuario):
        result = self.supabase.table("archivos_personales").select("*").eq("id", archivo_id).eq("usuario_email", usuario).execute()
        if result.data:
            archivo = result.data[0]
            url = archivo["ruta_completa"]
            mime, _ = mimetypes.guess_type(archivo["nombre_original"])
            return True, {"nombre": archivo["nombre_original"], "url": url, "mime_type": mime or "application/octet-stream"}
        return False, "Documento no encontrado"

    def eliminar_archivo(self, archivo_id, usuario, es_publicacion=False):
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
            pass
        supabase.table(tabla).delete().eq("id", archivo_id).execute()
        return True, "Archivo eliminado"

    def eliminar_publicacion(self, publicacion_id):
        return self.eliminar_archivo(publicacion_id, "master", es_publicacion=True)

    def editar_publicacion(self, publicacion_id, nueva_descripcion):
        try:
            # Al hacer el update, Supabase aplica el cambio directamente si encuentra el ID
            result = self.supabase.table("publicaciones").update({"descripcion": nueva_descripcion}).eq("id", publicacion_id).execute()
            
            # Verificamos si la operación no lanzó error y si afectó a un registro
            if result.data:
                return True, "Descripción actualizada exitosamente."
            else:
                return False, "No se encontró la publicación para editar."
        except Exception as e:
            return False, f"Error al editar en la base de datos: {str(e)}"
    
    def publicar_desde_personal(self, archivo_id, usuario, seccion, subcategoria, descripcion=""):
        try:
            # 1. Obtener el registro del archivo personal
            result = self.supabase.table("archivos_personales").select("*").eq("id", archivo_id).execute()
            if not result.data:
                return False, "Documento personal no encontrado"
            doc = result.data[0]

            # 2. Verificar que el usuario sea el propietario
            if doc["usuario_email"] != usuario:
                return False, "No tienes permiso para publicar este documento"

            # 3. Extraer la ruta relativa real desde la URL almacenada
            ruta_completa = doc["ruta_completa"]
            if f"/object/public/{self.bucket_name}/" in ruta_completa:
                ruta_relativa = ruta_completa.split(f"/object/public/{self.bucket_name}/")[-1]
            else:
                return False, "No se pudo determinar la ruta del archivo en Storage"

            # 4. Descargar el contenido original usando esa ruta exacta
            contenido = self.supabase.storage.from_(self.bucket_name).download(ruta_relativa)

            # 5. Preparar la nueva ruta en publicaciones (usando limpiar_ruta)
            carpeta_dest = f"publicaciones/{seccion}/{subcategoria}"
            partes_limpias = [limpiar_ruta(p) for p in carpeta_dest.split("/")]
            ruta_nueva = "/".join(partes_limpias) + "/" + doc["nombre_guardado"]

            # 6. Subir el archivo a la carpeta de publicaciones
            self.supabase.storage.from_(self.bucket_name).upload(
                path=ruta_nueva,
                file=contenido,
                file_options={"content-type": "application/octet-stream"}
            )
            url_publica = self.supabase.storage.from_(self.bucket_name).get_public_url(ruta_nueva)

            # 7. Insertar registro en "publicaciones" con los mismos campos que usa tu app
            nuevo_id = str(uuid.uuid4())
            registro_pub = {
                "id": nuevo_id,
                "nombre_original": doc["nombre_original"],
                "nombre_guardado": doc["nombre_guardado"],
                "seccion": seccion,
                "subcategoria": subcategoria,
                "fecha": datetime.now().isoformat(),
                "descripcion": descripcion or doc.get("descripcion", ""),
                "tamaño_bytes": doc["tamaño_bytes"],
                "tamaño_kb": doc["tamaño_kb"],
                "extension": doc["extension"],
                "ruta_completa": url_publica,
                "titulo": doc["nombre_original"],                     # ✅ Añadido
                "mensaje": descripcion or doc.get("descripcion", ""), # ✅ Añadido
                "categoria": subcategoria,                            # ✅ Añadido
                "creado_por": usuario
            }
            self.supabase.table("publicaciones").insert(registro_pub).execute()

            return True, "Documento publicado exitosamente"

        except Exception as e:
            return False, f"Error al publicar: {str(e)}"