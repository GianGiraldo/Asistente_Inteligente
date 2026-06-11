import json
import unicodedata
import uuid

from supabase_client import get_supabase


def normalizar_seccion(seccion):
    """Normaliza sección: strip, lower y sin tildes (ej. 'Contabilidad' -> 'contabilidad')."""
    if not seccion:
        return ""
    texto = unicodedata.normalize("NFKD", str(seccion).strip().lower())
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = "".join(c for c in texto if c.isalnum() or c.isspace()).strip()
    if " " in texto:
        texto = texto.split()[-1]
    return texto


def _format_supabase_error(exc):
    """Extrae el mensaje más detallado posible de un error de Supabase."""
    partes = [str(exc)]
    for attr in ("message", "details", "hint", "code"):
        valor = getattr(exc, attr, None)
        if valor:
            partes.append(str(valor))
    return " | ".join(dict.fromkeys(partes))


class NotificationManager:
    def __init__(self):
        self.supabase = get_supabase()

    @staticmethod
    def _normalizar_email(email):
        return (email or "").strip().lower()

    def _obtener_alumnos_por_seccion(self, seccion_normalizada, publicador_email=None):
        """
        Consulta users con activo=true, rol=usuario y secciones JSONB que contengan la sección.
        Retorna lista de emails tal como están en BD (respeta FK).
        """
        excluir = self._normalizar_email(publicador_email)
        query = (
            self.supabase.table("users")
            .select("email")
            .eq("activo", True)
            .eq("rol", "usuario")
            .contains("secciones", [seccion_normalizada])
        )
        result = query.execute()
        emails = []
        for usuario in result.data or []:
            email_bd = (usuario.get("email") or "").strip()
            if not email_bd:
                continue
            if excluir and self._normalizar_email(email_bd) == excluir:
                continue
            emails.append(email_bd)
        return list(dict.fromkeys(emails))

    def crear_notificacion(self, usuario_email, titulo, mensaje, tipo="info", metadata=None):
        """Inserta una notificación para un usuario específico."""
        email = (usuario_email or "").strip()
        meta_limpia = metadata if isinstance(metadata, dict) else {}
        if not meta_limpia:
            meta_limpia = {"origen": "sistema"}

        data = {
            "id": str(uuid.uuid4()),
            "usuario_email": email,
            "titulo": titulo,
            "mensaje": mensaje,
            "leido": False,
            "metadata": meta_limpia,
        }
        try:
            result = self.supabase.table("notificaciones").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error insertando notificación individual: {_format_supabase_error(e)}")
            raise

    def obtener_emails_alumnos(self, excluir_email=None):
        """Obtiene correos de alumnos activos con rol 'usuario'."""
        excluir = self._normalizar_email(excluir_email)
        try:
            result = (
                self.supabase.table("users")
                .select("email")
                .eq("activo", True)
                .eq("rol", "usuario")
                .execute()
            )
            emails = []
            for usuario in result.data or []:
                email_bd = (usuario.get("email") or "").strip()
                if not email_bd or self._normalizar_email(email_bd) == excluir:
                    continue
                emails.append(email_bd)
            return list(dict.fromkeys(emails))
        except Exception as e:
            print(f"Error obteniendo alumnos desde users: {_format_supabase_error(e)}")
            return []

    def crear_notificacion_para_alumnos(
        self, titulo, mensaje, tipo="publicacion", metadata=None, publicador_email=None
    ):
        """
        Inserta notificaciones en lote: una fila por usuario_email en la tabla notificaciones.
        Filtra alumnos vía query Supabase (.contains sobre JSONB secciones).
        """
        try:
            meta = metadata if isinstance(metadata, dict) else {}
            seccion_documento = normalizar_seccion(meta.get("seccion"))

            if not seccion_documento:
                msg = "No se indicó una sección válida para filtrar alumnos"
                print(f"⚠️ {msg}")
                return False, 0, msg

            meta["seccion"] = seccion_documento

            print(
                f"🔍 Buscando alumnos: activo=true, rol=usuario, "
                f"secciones contiene ['{seccion_documento}']"
            )
            alumnos = self._obtener_alumnos_por_seccion(seccion_documento, publicador_email)

            if not alumnos:
                msg = (
                    f"No hay alumnos activos (rol=usuario) con la sección "
                    f"'{seccion_documento}' en users.secciones"
                )
                print(f"⚠️ {msg}")
                return False, 0, msg

            registros = [
                {
                    "id": str(uuid.uuid4()),
                    "usuario_email": email,
                    "titulo": titulo,
                    "mensaje": mensaje,
                    "leido": False,
                    "metadata": meta,
                }
                for email in alumnos
            ]

            print(f"📨 Insertando {len(registros)} notificaciones en lote...")
            result = self.supabase.table("notificaciones").insert(registros).execute()

            if not result.data:
                msg = "Supabase no devolvió datos tras el insert masivo de notificaciones"
                print(f"❌ {msg}")
                return False, 0, msg

            print(
                f"✅ Éxito: {len(result.data)} notificaciones creadas "
                f"para la sección '{seccion_documento}'"
            )
            return True, len(result.data), None

        except Exception as e:
            err = _format_supabase_error(e)
            print(f"❌ Error en notificación masiva a alumnos: {err}")
            return False, 0, err

    def crear_notificacion_para_todos(self, titulo, mensaje, tipo="publicacion", metadata=None, publicador_email=None):
        return self.crear_notificacion_para_alumnos(
            titulo, mensaje, tipo, metadata, publicador_email=publicador_email
        )

    def obtener_notificaciones_no_leidas(self, usuario_email):
        email = (usuario_email or "").strip()
        try:
            result = (
                self.supabase.table("notificaciones")
                .select("*")
                .eq("usuario_email", email)
                .eq("leido", False)
                .order("id", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo notificaciones no leídas: {_format_supabase_error(e)}")
            return []

    def obtener_ultimas_no_leidas(self, usuario_email, limite=10):
        email = (usuario_email or "").strip()
        try:
            result = (
                self.supabase.table("notificaciones")
                .select("*")
                .eq("usuario_email", email)
                .eq("leido", False)
                .order("id", desc=True)
                .limit(limite)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo últimas notificaciones: {_format_supabase_error(e)}")
            return []

    def contar_no_leidas(self, usuario_email):
        email = (usuario_email or "").strip()
        try:
            result = (
                self.supabase.table("notificaciones")
                .select("id", count="exact")
                .eq("usuario_email", email)
                .eq("leido", False)
                .execute()
            )
            return result.count or 0
        except Exception as e:
            print(f"Error contando notificaciones: {_format_supabase_error(e)}")
            return 0

    def marcar_como_leida(self, notificacion_id, usuario_email):
        email = (usuario_email or "").strip()
        try:
            result = (
                self.supabase.table("notificaciones")
                .update({"leido": True})
                .eq("id", notificacion_id)
                .eq("usuario_email", email)
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            print(f"Error marcando notificación como leída: {_format_supabase_error(e)}")
            return False

    def marcar_todas_como_leidas(self, usuario_email):
        email = (usuario_email or "").strip()
        try:
            self.supabase.table("notificaciones").update({"leido": True}).eq(
                "usuario_email", email
            ).eq("leido", False).execute()
            return True
        except Exception as e:
            print(f"Error marcando todas como leídas: {_format_supabase_error(e)}")
            return False

    def obtener_ultimas_publicaciones(self, limite=10):
        try:
            response = (
                self.supabase.table("publicaciones")
                .select("*")
                .order("id", desc=True)
                .limit(limite)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error obteniendo publicaciones: {_format_supabase_error(e)}")
            return []
