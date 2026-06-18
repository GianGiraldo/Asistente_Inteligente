# message_manager.py
from datetime import datetime
import uuid
from supabase_client import get_supabase


class MessageManager:
    def __init__(self):
        self.supabase = get_supabase()
        self.tabla = "consultas"

    def _es_consulta_pendiente(self, consulta: dict) -> bool:
        """True solo si la consulta aún no fue contestada."""
        if consulta.get("respuesta"):
            return False
        if consulta.get("respondido") is True:
            return False
        estado = (consulta.get("estado") or "").strip().lower()
        if estado in ("respondida", "respondido", "cerrada", "closed"):
            return False
        return True

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
                "estado": "pendiente",
            }
            result = self.supabase.table(self.tabla).insert(data).execute()
            if result.data:
                return True, "Consulta enviada correctamente"
            return False, "No se pudo registrar la consulta"
        except Exception as e:
            if "estado" in str(e).lower() or "column" in str(e).lower():
                try:
                    data.pop("estado", None)
                    result = self.supabase.table(self.tabla).insert(data).execute()
                    if result.data:
                        return True, "Consulta enviada correctamente"
                except Exception as retry_err:
                    print(f"Error enviando consulta (reintento sin estado): {retry_err}")
            print(f"Error enviando consulta: {e}")
            return False, str(e)

    def _consulta_actualizada_tras_respuesta(self, mensaje_id: str, respuesta: str) -> bool:
        """Verifica en BD que la respuesta quedó persistida (Supabase puede no devolver filas en UPDATE)."""
        campos = "id, respuesta, respondido, estado"
        try:
            check = (
                self.supabase.table(self.tabla)
                .select(campos)
                .eq("id", mensaje_id)
                .limit(1)
                .execute()
            )
        except Exception:
            check = (
                self.supabase.table(self.tabla)
                .select("id, respuesta, respondido")
                .eq("id", mensaje_id)
                .limit(1)
                .execute()
            )
        row = (check.data or [{}])[0]
        if not row or row.get("id") != mensaje_id:
            return False
        return (row.get("respuesta") or "").strip() == respuesta.strip()

    def responder_mensaje(self, mensaje_id, respuesta, master_email):
        """Guarda la respuesta del Master y marca la consulta como respondida."""
        respuesta = (respuesta or "").strip()
        if not respuesta:
            return False
        try:
            update = {
                "respuesta": respuesta,
                "respondido": True,
                "respondido_por": master_email,
                "fecha_respuesta": datetime.now().isoformat(),
                "estado": "respondida",
            }
            try:
                result = (
                    self.supabase.table(self.tabla)
                    .update(update)
                    .eq("id", mensaje_id)
                    .execute()
                )
            except Exception as estado_err:
                if "estado" not in str(estado_err).lower() and "column" not in str(estado_err).lower():
                    raise
                update.pop("estado", None)
                result = (
                    self.supabase.table(self.tabla)
                    .update(update)
                    .eq("id", mensaje_id)
                    .execute()
                )
            if result.data:
                return True
            return self._consulta_actualizada_tras_respuesta(mensaje_id, respuesta)
        except Exception as e:
            print(f"Error respondiendo consulta: {e}")
            return False

    def obtener_consultas_pendientes(self):
        """Consultas estrictamente pendientes: sin respuesta y sin estado respondida."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .is_("respuesta", "null")
                .eq("respondido", False)
                .order("fecha", desc=True)
                .execute()
            )
            return [c for c in (result.data or []) if self._es_consulta_pendiente(c)]
        except Exception as e:
            print(f"Error obteniendo consultas pendientes (filtro respondido): {e}")
            try:
                result = (
                    self.supabase.table(self.tabla)
                    .select("*")
                    .is_("respuesta", "null")
                    .order("fecha", desc=True)
                    .execute()
                )
                return [c for c in (result.data or []) if self._es_consulta_pendiente(c)]
            except Exception as fallback_err:
                print(f"Error obteniendo consultas pendientes: {fallback_err}")
                return []

    def obtener_consultas_respondidas(self):
        """Historial de consultas ya contestadas por el Master."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .or_("respondido.eq.true,estado.eq.respondida")
                .order("fecha_respuesta", desc=True)
                .execute()
            )
            respondidas = [c for c in (result.data or []) if not self._es_consulta_pendiente(c)]
            if respondidas:
                return respondidas
        except Exception as e:
            print(f"Error obteniendo consultas respondidas (filtro compuesto): {e}")
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .not_.is_("respuesta", "null")
                .order("fecha_respuesta", desc=True)
                .execute()
            )
            return [c for c in (result.data or []) if not self._es_consulta_pendiente(c)]
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
        return len([m for m in mensajes if self._es_consulta_pendiente(m)])
