import json
import unicodedata
import uuid

from supabase_client import get_supabase

MENSAJE_NOTIF_NUEVO_DOCUMENTO = "Se ha publicado un nuevo documento en el curso."
LIMITE_NOTIFICACIONES_CAMPANA = 8


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

    @staticmethod
    def _listas_acceso_usuario(usuario):
        secciones = usuario.get("secciones")
        asignadas = usuario.get("secciones_asignadas")
        if secciones is None:
            secciones = []
        if asignadas is None:
            asignadas = []
        if not isinstance(secciones, list):
            secciones = []
        if not isinstance(asignadas, list):
            asignadas = []
        return secciones, asignadas

    def _usuario_tiene_seccion(self, usuario, seccion_normalizada):
        if not seccion_normalizada:
            return False
        secciones, asignadas = self._listas_acceso_usuario(usuario)
        for valor in secciones + asignadas:
            if not valor:
                continue
            if normalizar_seccion(valor) == seccion_normalizada:
                return True
            if str(valor).strip().lower() == seccion_normalizada:
                return True
        return False

    def _obtener_alumnos_por_seccion(self, seccion_normalizada, publicador_email=None):
        """
        Usuarios activos (rol=usuario) con la sección en secciones o secciones_asignadas.
        Valida arrays NULL antes de segmentar.
        """
        excluir = self._normalizar_email(publicador_email)
        try:
            result = (
                self.supabase.table("users")
                .select("email, secciones, secciones_asignadas")
                .eq("activo", True)
                .eq("rol", "usuario")
                .execute()
            )
            emails = []
            for usuario in result.data or []:
                if not self._usuario_tiene_seccion(usuario, seccion_normalizada):
                    continue
                email_bd = (usuario.get("email") or "").strip()
                if not email_bd:
                    continue
                if excluir and self._normalizar_email(email_bd) == excluir:
                    continue
                emails.append(email_bd)
            return list(dict.fromkeys(emails))
        except Exception as e:
            print(f"Error obteniendo alumnos por sección: {_format_supabase_error(e)}")
            return []

    def crear_notificacion(
        self,
        usuario_email,
        titulo,
        mensaje,
        seccion=None,
        tipo="info",
        metadata=None,
    ):
        """Inserta una notificación para un usuario específico."""
        email = (usuario_email or "").strip()
        meta_limpia = metadata if isinstance(metadata, dict) else {}
        if not meta_limpia:
            meta_limpia = {"origen": "sistema"}
        seccion_norm = normalizar_seccion(seccion or meta_limpia.get("seccion"))

        data = {
            "id": str(uuid.uuid4()),
            "usuario_email": email,
            "seccion": seccion_norm or None,
            "titulo": titulo,
            "mensaje": mensaje or MENSAJE_NOTIF_NUEVO_DOCUMENTO,
            "tipo": tipo,
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
        Filtra alumnos por secciones y secciones_asignadas (arrays NULL-safe).
        """
        try:
            meta = metadata if isinstance(metadata, dict) else {}
            seccion_documento = normalizar_seccion(meta.get("seccion"))

            if not seccion_documento:
                msg = "No se indicó una sección válida para filtrar alumnos"
                print(f"⚠️ {msg}")
                return False, 0, msg

            meta["seccion"] = seccion_documento
            mensaje_final = (mensaje or "").strip() or MENSAJE_NOTIF_NUEVO_DOCUMENTO

            print(
                f"🔍 Buscando alumnos: activo=true, rol=usuario, "
                f"sección '{seccion_documento}' en secciones/secciones_asignadas"
            )
            alumnos = self._obtener_alumnos_por_seccion(seccion_documento, publicador_email)

            if not alumnos:
                msg = (
                    f"No hay alumnos activos (rol=usuario) con la sección "
                    f"'{seccion_documento}' en users.secciones o users.secciones_asignadas"
                )
                print(f"⚠️ {msg}")
                return False, 0, msg

            registros = [
                {
                    "id": str(uuid.uuid4()),
                    "usuario_email": email,
                    "seccion": seccion_documento,
                    "titulo": titulo,
                    "mensaje": mensaje_final,
                    "tipo": tipo,
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
                .order("fecha_creacion", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo notificaciones no leídas: {_format_supabase_error(e)}")
            return []

    def obtener_ultimas_no_leidas(self, usuario_email, limite=LIMITE_NOTIFICACIONES_CAMPANA):
        email = (usuario_email or "").strip()
        limite_seguro = max(1, min(int(limite or LIMITE_NOTIFICACIONES_CAMPANA), 8))
        try:
            result = (
                self.supabase.table("notificaciones")
                .select("*")
                .eq("usuario_email", email)
                .eq("leido", False)
                .order("fecha_creacion", desc=True)
                .limit(limite_seguro)
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
