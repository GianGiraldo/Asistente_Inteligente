import json
import unicodedata
import uuid
from datetime import datetime

from supabase_client import get_supabase


def normalizar_seccion(seccion):
    """Normaliza una sección: minúsculas, sin tildes/emojis y clave canónica."""
    if not seccion:
        return ""
    texto = unicodedata.normalize("NFKD", str(seccion).strip().lower())
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = "".join(c for c in texto if c.isalnum() or c.isspace()).strip()
    if " " in texto:
        texto = texto.split()[-1]
    return texto


class NotificationManager:
    def __init__(self):
        self.supabase = get_supabase()

    @staticmethod
    def _normalizar_email(email):
        return (email or "").strip().lower()

    @staticmethod
    def _parsear_secciones(secciones_raw):
        if not secciones_raw:
            return []
        if isinstance(secciones_raw, str):
            try:
                secciones_raw = json.loads(secciones_raw)
            except json.JSONDecodeError:
                secciones_raw = secciones_raw.replace("{", "").replace("}", "").split(",")
        if not isinstance(secciones_raw, (list, tuple)):
            secciones_raw = [secciones_raw]
        return [str(s).strip() for s in secciones_raw if str(s).strip()]

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
            seccion_documento = normalizar_seccion(meta.get("seccion"))
            if seccion_documento:
                meta["seccion"] = seccion_documento

            result = self.supabase.table("users").select(
                "email, rol, secciones, secciones_asignadas, activo"
            ).execute()

            alumnos = []
            excluir = self._normalizar_email(publicador_email)

            for usuario in result.data or []:
                if usuario.get("activo") is False:
                    continue

                email = self._normalizar_email(usuario.get("email"))
                rol = (usuario.get("rol") or "usuario").strip().lower()

                secciones_raw = usuario.get("secciones_asignadas") or usuario.get("secciones")
                secciones_norm = {
                    normalizar_seccion(s)
                    for s in self._parsear_secciones(secciones_raw)
                    if normalizar_seccion(s)
                }

                if not email or email == excluir or rol == "master":
                    continue

                if seccion_documento and seccion_documento not in secciones_norm:
                    continue

                alumnos.append(email)

            if not alumnos:
                msg = f"No hay alumnos activos asignados a la sección '{seccion_documento or 'general'}'"
                print(f"⚠️ Alerta: {msg}")
                return False, 0, msg

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