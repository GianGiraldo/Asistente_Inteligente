# message_manager.py
from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional, Tuple

from supabase_client import get_supabase


class MessageManager:
    def __init__(self):
        self.supabase = get_supabase()
        self.tabla = "consultas"

    @staticmethod
    def _email_de_consulta(consulta: Dict[str, Any]) -> str:
        return (
            (consulta.get("usuario_email") or consulta.get("email") or "")
            .strip()
            .lower()
        )

    @staticmethod
    def _texto_asunto(consulta: Dict[str, Any]) -> str:
        asunto = (consulta.get("asunto") or "").strip()
        if asunto:
            return asunto
        seccion = (consulta.get("seccion") or "").strip()
        if seccion and seccion not in ("administracion", "general"):
            return f"Consulta · {seccion}"
        return "Consulta"

    def registrar_notificacion_comprobante(
        self,
        usuario_email: str,
        asunto: str,
        mensaje: str,
        respuesta: str,
        estado: str,
        master_email: str = "",
        nombre_usuario: str = "",
    ) -> Tuple[bool, str]:
        """Registra notificación admin (aprobación/rechazo de comprobante) en consultas."""
        email_norm = (usuario_email or "").strip().lower()
        if not email_norm:
            return False, "Email de usuario inválido"

        now = datetime.now().isoformat()
        base: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "usuario_email": email_norm,
            "email": email_norm,
            "asunto": (asunto or "").strip(),
            "mensaje": (mensaje or "").strip(),
            "respuesta": (respuesta or "").strip(),
            "estado": (estado or "Atendido").strip(),
            "fecha": now,
            "respondido": True,
            "respondido_por": (master_email or "").strip() or None,
            "fecha_respuesta": now,
            "nombre_usuario": (nombre_usuario or email_norm.split("@")[0]).strip(),
            "seccion": "administracion",
            "leido": False,
            "leido_master": True,
        }
        candidatos = [
            base,
            {k: v for k, v in base.items() if k not in ("usuario_email", "asunto")},
        ]
        ultimo_error = ""
        for data in candidatos:
            try:
                result = self.supabase.table(self.tabla).insert(data).execute()
                if result.data:
                    return True, "Notificación registrada en consultas"
                return False, "No se pudo registrar la notificación"
            except Exception as e:
                ultimo_error = str(e)
                if any(x in ultimo_error.lower() for x in ("column", "pgrst", "schema")):
                    continue
                print(f"Error registrando notificación comprobante: {e}")
                return False, ultimo_error
        print(f"Error registrando notificación comprobante: {ultimo_error}")
        return False, ultimo_error or "No se pudo registrar en consultas"

    def registrar_aprobacion_comprobante(
        self, usuario_email: str, master_email: str = "", nombre_usuario: str = ""
    ) -> Tuple[bool, str]:
        return self.registrar_notificacion_comprobante(
            usuario_email=usuario_email,
            asunto="¡Pago Aprobado y Acceso Activado!",
            mensaje=(
                "Hemos validado tu comprobante. Tus cursos solicitados han sido "
                "activados correctamente en la plataforma."
            ),
            respuesta="Notificación enviada por administración.",
            estado="Atendido",
            master_email=master_email,
            nombre_usuario=nombre_usuario,
        )

    def registrar_rechazo_comprobante(
        self,
        usuario_email: str,
        observacion: str,
        master_email: str = "",
        nombre_usuario: str = "",
    ) -> Tuple[bool, str]:
        texto_obs = (observacion or "").strip() or (
            "Tu comprobante no pudo ser validado. Revisa el monto, la captura "
            "y vuelve a enviar una solicitud si corresponde."
        )
        return self.registrar_notificacion_comprobante(
            usuario_email=usuario_email,
            asunto="Observación en tu comprobante de pago",
            mensaje=texto_obs,
            respuesta="Notificación enviada por administración.",
            estado="Observado",
            master_email=master_email,
            nombre_usuario=nombre_usuario,
        )

    def obtener_historial_completo(self) -> List[Dict[str, Any]]:
        """Historial total de consultas (solo panel Master / trazabilidad)."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .order("fecha", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo historial completo de consultas: {e}")
            return []

    @staticmethod
    def _es_consulta_no_leida(consulta: Dict[str, Any]) -> bool:
        """True si el usuario aún no abrió una respuesta/notificación en Consultas."""
        if consulta.get("leido") is True:
            return False
        if consulta.get("respuesta"):
            return True
        estado = (consulta.get("estado") or "").strip().lower()
        return estado in ("atendido", "observado", "respondida", "respondido")

    def _es_consulta_pendiente(self, consulta: dict) -> bool:
        """True solo si la consulta aún no fue contestada."""
        if consulta.get("respuesta"):
            return False
        if consulta.get("respondido") is True:
            return False
        estado = (consulta.get("estado") or "").strip().lower()
        if estado in (
            "respondida",
            "respondido",
            "cerrada",
            "closed",
            "atendido",
            "observado",
        ):
            return False
        return True

    @staticmethod
    def _es_consulta_soporte_usuario(consulta: Dict[str, Any]) -> bool:
        seccion = (consulta.get("seccion") or "").strip().lower()
        return seccion not in ("administracion", "general", "")

    def _es_soporte_no_leido_master(self, consulta: Dict[str, Any]) -> bool:
        if not self._es_consulta_soporte_usuario(consulta):
            return False
        if consulta.get("leido_master") is True:
            return False
        if consulta.get("leido_master") is False:
            return True
        return self._es_consulta_pendiente(consulta)

    def contar_consultas_soporte_no_leidas_master(self) -> int:
        """Mensajes de soporte enviados por usuarios que el Master aún no revisó."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("id", count="exact")
                .eq("leido_master", False)
                .execute()
            )
            if result.count is not None:
                return int(result.count)
        except Exception:
            pass
        try:
            historial = self.obtener_historial_completo()
            return len(
                [
                    c
                    for c in historial
                    if self._es_soporte_no_leido_master(c)
                ]
            )
        except Exception as e:
            print(f"Error contando soporte master no leído: {e}")
            return 0

    def marcar_consultas_leidas_master(self) -> None:
        """Marca como revisadas las consultas de soporte entrantes (vista Master)."""
        try:
            self.supabase.table(self.tabla).update({"leido_master": True}).eq(
                "leido_master", False
            ).execute()
            return
        except Exception as e:
            print(f"Error marcando consultas leídas master (SQL): {e}")
        for consulta in self.obtener_historial_completo():
            if not self._es_soporte_no_leido_master(consulta):
                continue
            cid = consulta.get("id")
            if not cid:
                continue
            try:
                self.supabase.table(self.tabla).update({"leido_master": True}).eq(
                    "id", cid
                ).execute()
            except Exception as row_err:
                print(f"Error marcando consulta master {cid}: {row_err}")

    def contar_consultas_no_leidas(self, email: str) -> int:
        """Cantidad de respuestas/notificaciones no leídas del usuario (leido = false)."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return 0
        try:
            for col in ("usuario_email", "email"):
                try:
                    result = (
                        self.supabase.table(self.tabla)
                        .select("id", count="exact")
                        .eq(col, email_norm)
                        .eq("leido", False)
                        .execute()
                    )
                    if result.count is not None:
                        return int(result.count)
                except Exception:
                    continue
        except Exception as e:
            print(f"Error contando consultas no leídas (SQL): {e}")
        mensajes = self.obtener_mensajes_usuario(email_norm)
        return len([m for m in mensajes if self._es_consulta_no_leida(m)])

    def marcar_consultas_leidas(self, email: str) -> None:
        """Marca como leídas todas las consultas pendientes de lectura del usuario."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return
        try:
            for col in ("usuario_email", "email"):
                try:
                    self.supabase.table(self.tabla).update({"leido": True}).eq(
                        col, email_norm
                    ).eq("leido", False).execute()
                except Exception:
                    continue
            return
        except Exception as e:
            print(f"Error marcando consultas leídas (SQL): {e}")
        for consulta in self.obtener_mensajes_usuario(email_norm):
            if not self._es_consulta_no_leida(consulta):
                continue
            cid = consulta.get("id")
            if not cid:
                continue
            try:
                self.supabase.table(self.tabla).update({"leido": True}).eq(
                    "id", cid
                ).execute()
            except Exception as row_err:
                print(f"Error marcando consulta {cid} como leída: {row_err}")

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
                "leido": True,
                "leido_master": False,
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
                "leido": False,
                "leido_master": True,
            }
            try:
                result = (
                    self.supabase.table(self.tabla)
                    .update(update)
                    .eq("id", mensaje_id)
                    .execute()
                )
            except Exception as col_err:
                err_text = str(col_err).lower()
                if (
                    "estado" not in err_text
                    and "leido" not in err_text
                    and "leido_master" not in err_text
                    and "column" not in err_text
                ):
                    raise
                update.pop("estado", None)
                update.pop("leido", None)
                update.pop("leido_master", None)
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
        """Obtiene el historial de consultas de un usuario (email o usuario_email)."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return []
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .order("fecha", desc=True)
                .execute()
            )
            return [
                c
                for c in (result.data or [])
                if self._email_de_consulta(c) == email_norm
            ]
        except Exception as e:
            print(f"Error obteniendo consultas del usuario: {e}")
            return []

    def contar_no_leidos(self, email):
        """Cuenta consultas del usuario que aún no tienen respuesta."""
        mensajes = self.obtener_mensajes_usuario(email)
        return len([m for m in mensajes if self._es_consulta_pendiente(m)])
