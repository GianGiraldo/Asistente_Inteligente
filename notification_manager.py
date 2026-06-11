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
        data = {
            "id": str(uuid.uuid4()),
            "usuario_email": email,
            "titulo": titulo,
            "mensaje": mensaje,
            "tipo": tipo,
            "leido": False,
            "fecha_creacion": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        result = self.supabase.table("notificaciones").insert(data).execute()
        return result.data[0] if result.data else None

    def obtener_emails_alumnos(self, excluir_email=None):
        """Obtiene correos de alumnos desde la tabla real 'users' (Excluye al Master)."""
        excluir = self._normalizar_email(excluir_email)
        try:
            # Apuntamos a la tabla 'users' que es la real de tu app
            result = self.supabase.table("users").select("email, rol").execute()
            emails = []
            for usuario in result.data or []:
                email = self._normalizar_email(usuario.get("email"))
                rol = (usuario.get("rol") or "usuario").strip().lower()
                
                # Filtramos para no mandarle la notificación al propio Master
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
            meta = metadata or {}
            # 1. Normalizamos la sección del documento (ej: "Excel " -> "excel")
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
                
                # Obtener y normalizar las secciones del usuario
                secciones_usuario_raw = usuario.get("secciones") or []
                
                # Nos aseguramos de que sea una lista y limpiamos cada elemento
                if isinstance(secciones_usuario_raw, str):
                    # Por si Supabase lo devuelve como string plano ej: '["excel","laboral"]'
                    import json
                    try:
                        secciones_usuario_raw = json.loads(secciones_usuario_raw)
                    except:
                        secciones_usuario_raw = [secciones_usuario_raw]
                
                # Convertimos toda la lista a minúsculas y sin espacios laterales
                secciones_usuario = [str(s).strip().lower() for s in secciones_usuario_raw]

                # Validaciones de exclusión básicas
                if not email or email == excluir or rol == "master":
                    continue
                
                # Segmentación: Si el documento tiene sección, validamos de forma limpia
                if seccion_documento and (seccion_documento not in secciones_usuario):
                    continue

                alumnos.append(email)

            if not alumnos:
                print(f"⚠️ Alerta: No se encontraron alumnos asignados a la sección '{seccion_documento}'")
                return True, 0, None

            ahora = datetime.now().isoformat()
            registros = [
                {
                    "id": str(uuid.uuid4()),
                    "usuario_email": email,
                    "titulo": titulo,
                    "mensaje": mensaje,
                    "tipo": tipo,
                    "leido": False,
                    "fecha_creacion": ahora,
                    "metadata": meta,
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
        """Compatibilidad: redirige a notificación solo para alumnos."""
        return self.crear_notificacion_para_alumnos(
            titulo, mensaje, tipo, metadata, publicador_email=publicador_email
        )

    def obtener_notificaciones_no_leidas(self, usuario_email):
        """Obtiene todas las notificaciones no leídas de un usuario."""
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
        """Últimas notificaciones pendientes de leer para el panel de la campana."""
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
            print(f"Error obteniendo últimas notificaciones: {e}")
            return []

    def contar_no_leidas(self, usuario_email):
        """Cuenta cuántas notificaciones no leídas tiene un usuario."""
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
        """Marca una notificación como leída (solo si pertenece al usuario)."""
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
        """Marca todas las notificaciones de un usuario como leídas."""
        email = self._normalizar_email(usuario_email)
        self.supabase.table("notificaciones").update({"leido": True}).eq("usuario_email", email).eq("leido", False).execute()
        return True

    def obtener_ultimas_publicaciones(self, limite=10):
        """Obtiene las últimas publicaciones generales desde la tabla publicaciones."""
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
