# message_manager.py
from datetime import datetime
import uuid
from supabase_client import get_supabase


class MessageManager:
    def __init__(self):
        self.supabase = get_supabase()
        self.tabla = "consultas"

    def enviar_mensaje(self, email, nombre, seccion, mensaje):
        """Registra una nueva consulta de usuario en Supabase."""
        try:
            data = {
                "id": str(uuid.uuid4()),
                "email": email,
                "nombre_usuario": nombre,
                "seccion": seccion,
                "mensaje": mensaje,
                "fecha": datetime.now().isoformat(),
                "respondido": False,
                "respuesta": None,
                "respondido_por": None,
                "fecha_respuesta": None,
            }
            result = self.supabase.table(self.tabla).insert(data).execute()
            if result.data:
                return True, "Consulta enviada correctamente"
            return False, "No se pudo registrar la consulta"
        except Exception as e:
            print(f"Error enviando consulta: {e}")
            return False, str(e)

    def responder_mensaje(self, mensaje_id, respuesta, master_email):
        """Guarda la respuesta del Master y marca la consulta como respondida."""
        try:
            update = {
                "respuesta": respuesta,
                "respondido": True,
                "respondido_por": master_email,
                "fecha_respuesta": datetime.now().isoformat(),
            }
            result = (
                self.supabase.table(self.tabla)
                .update(update)
                .eq("id", mensaje_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Error respondiendo consulta: {e}")
            return False

    def obtener_consultas_pendientes(self):
        """Consultas sin respuesta (respuesta nula o marcadas como pendientes)."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .or_("respuesta.is.null,respondido.eq.false")
                .order("fecha", desc=True)
                .execute()
            )
            pendientes = result.data or []
            return [c for c in pendientes if not c.get("respuesta")]
        except Exception as e:
            print(f"Error obteniendo consultas pendientes: {e}")
            return []

    def obtener_consultas_respondidas(self):
        """Historial de consultas ya contestadas por el Master."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .eq("respondido", True)
                .not_.is_("respuesta", "null")
                .order("fecha_respuesta", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo consultas respondidas: {e}")
            return []

    def obtener_mensajes_para_master(self, respondidos=False):
        """Compatibilidad con llamadas existentes."""
        if respondidos:
            return self.obtener_consultas_respondidas()
        return self.obtener_consultas_pendientes()

    def obtener_mensajes_usuario(self, email):
        """Obtiene el historial de consultas de un usuario."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .eq("email", email)
                .order("fecha", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo consultas del usuario: {e}")
            return []

    def contar_no_leidos(self, email):
        """Cuenta consultas del usuario que aún no tienen respuesta."""
        mensajes = self.obtener_mensajes_usuario(email)
        return len([m for m in mensajes if not m.get("respondido") and not m.get("respuesta")])
