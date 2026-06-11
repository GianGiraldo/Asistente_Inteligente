from supabase_client import get_supabase
from datetime import datetime
import uuid

class NotificationManager:
    def __init__(self):
        self.supabase = get_supabase()

    @staticmethod
    def _normalizar_email(email):
        return (email or "").strip().lower()

    def crear_notificacion(self, usuario_email, titulo, mensaje, tipo="info", metadata=None):
        """Inserta una notificación para un usuario específico."""
        email = self._normalizar_email(usuario_email)
        
        # Estructuramos la metadata obligando a que lleve datos mínimos útiles
        meta_limpia = metadata if isinstance(metadata, dict) else {}
        if not meta_limpia:
            meta_limpia = {"origen": "sistema"}

        data = {
            "id": str(uuid.uuid4()),
            "usuario_email": email,
            "titulo": titulo,
            "mensaje": mensaje,
            "tipo": tipo,
            "leido": False,
            "fecha_creacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "metadata": meta_limpia, # Supabase-py lo convierte a JSONB automáticamente
        }
        result = self.supabase.table("notificaciones").insert(data).execute()
        return result.data[0] if result.data else None

    def obtener_emails_alumnos(self, excluir_email=None):
        """Obtiene correos de alumnos desde la tabla real 'users' (Excluye al Master)."""
        excluir = self._normalizar_email(excluir_email)
        try:
            result = self.supabase.table("users").select("email, rol").execute()
            emails = []
            for usuario in result.data or []:
                email = self._normalizar_email(usuario.get("email"))
                rol = (usuario.get("rol") or "usuario").strip().lower()
                
                if not email or email == excluir or rol == "master":
                    continue
                emails.append(email)
            return list(dict.fromkeys(emails))
        except Exception as e:
            print(f"Error obteniendo alumnos desde la tabla users: {e}")
            return []

    def crear_notificacion_para_alumnos(
        self, titulo, mensaje, tipo="publicacion", metadata=None, publicador_email=None
    ):
        """
        Inserta notificaciones en bloque solo para alumnos que tengan acceso 
        a la sección específica del documento (Ignora mayúsculas y espacios).
        """
        try:
            meta = metadata if isinstance(metadata, dict) else {}
            
            # 1. Normalizamos la sección del documento
            seccion_documento = meta.get("seccion")
            if seccion_documento:
                seccion_documento = str(seccion_documento).strip().lower()

            # Traemos todos los usuarios activos
            result = self.supabase.table("users").select("email, rol, secciones").eq("activo", True).execute()
            
            alumnos = []
            excluir = self._normalizar_email(publicador_email)

            for usuario in result.data or []:
                email = self._normalizar_email(usuario.get("email"))
                rol = (usuario.get("rol") or "usuario").strip().lower()
                
                # Recuperar y limpiar las secciones del usuario
                secciones_usuario_raw = usuario.get("secciones") or []
                if isinstance(secciones_usuario_raw, str):
                    import json
                    try:
                        secciones_usuario_raw = json.loads(secciones_usuario_raw)
                    except:
                        secciones_usuario_raw = secciones_usuario_raw.replace("{", "").replace("}", "").split(",")
                
                secciones_usuario = [str(s).strip().lower() for s in secciones_usuario_raw]
                
                if not email or email == excluir or rol == "master":
                    continue
                
                # Filtrado Ultra-Flexible de la Sección del Documento
                if seccion_documento:
                    seccion_doc_min = str(seccion_documento).lower().strip()
                    seccion_doc_limpia = "".join(c for c in seccion_doc_min if c.isalnum() or c.isspace()).strip()
                    
                    coincide = False
                    for su in secciones_usuario:
                        if su in seccion_doc_limpia or seccion_doc_limpia in su:
                            coincide = True
                            break
                    
                    if not coincide:
                        continue 

                alumnos.append(email)

            if not alumnos:
                print(f"⚠️ Alerta: No se encontraron alumnos asignados a la sección '{seccion_documento}'")
                return True, 0, None

            # Si la metadata va vacía, le asignamos valores por defecto para que no falle el JSONB
            if not meta:
                meta = {"seccion": seccion_documento or "general", "modulo": "publicaciones"}

            ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            registros = [
                {
                    "id": str(uuid.uuid4()),
                    "usuario_email": email,
                    "titulo": titulo,
                    "mensaje": mensaje,
                    "tipo": tipo,
                    "leido": False,
                    "fecha_creacion": ahora,
                    "metadata": meta, # Pasamos el diccionario directamente
                }
                for email in alumnos
            ]
            
            self.supabase.table("notificaciones").insert(registros).execute()
            print(f"✅ Éxito: Se crearon {len(registros)} notificaciones para la sección '{seccion_documento}'")
            return True, len(registros), None
            
        except Exception as e:
            print(f"❌ Error en notificación masiva a alumnos: {e}")
            return False, 0, str(e)

    def crear_notificacion_para_todos(self, titulo, mensaje, tipo="publicacion", metadata=None, publicador_email=None):
        return self.crear_notificacion_para_alumnos(
            titulo, mensaje, tipo, metadata, publicador_email=publicador_email
        )

    def obtener_notificaciones_no_leidas(self, usuario_email):
        email = self._normalizar_email(usuario_email)
        result = (
            self.supabase.table("notificaciones")
            .select("*")
            .eq("usuario_email", email)
            .eq("leido", False)
            .order("fecha_creacion", desc=True)
            .execute()
        )
        return result.data or []

    def obtener_ultimas_no_leidas(self, usuario_email, limite=10):
        email = self._normalizar_email(usuario_email)
        try:
            result = (
                self.supabase.table("notificaciones")
                .select("*")
                .eq("usuario_email", email)
                .eq("leido", False)
                .order("fecha_creacion", desc=True)
                .limit(limite)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obtuvo últimas notificaciones: {e}")
            return []

    def contar_no_leidas(self, usuario_email):
        email = self._normalizar_email(usuario_email)
        result = (
            self.supabase.table("notificaciones")
            .select("id", count="exact")
            .eq("usuario_email", email)
            .eq("leido", False)
            .execute()
        )
        return result.count or 0

    def marcar_como_leida(self, notificacion_id, usuario_email):
        email = self._normalizar_email(usuario_email)
        result = (
            self.supabase.table("notificaciones")
            .update({"leido": True})
            .eq("id", notificacion_id)
            .eq("usuario_email", email)
            .execute()
        )
        return len(result.data) > 0

    def marcar_todas_como_leidas(self, usuario_email):
        email = self._normalizar_email(usuario_email)
        self.supabase.table("notificaciones").update({"leido": True}).eq("usuario_email", email).eq("leido", False).execute()
        return True

    def obtener_ultimas_publicaciones(self, limite=10):
        try:
            response = (
                self.supabase.table("publicaciones")
                .select("*")
                .order("fecha_creacion", desc=True)
                .limit(limite)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error obteniendo publicaciones: {e}")
            return []