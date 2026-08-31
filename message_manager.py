# message_manager.py
from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional, Tuple

from supabase_client import get_supabase


class MessageManager:
    def __init__(self):
        self.supabase = get_supabase()
        self.tabla = "consultas"
        self.tabla_comprobantes = "comprobantes"

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
        seccion: str = "cobranzas",
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
            "seccion": (seccion or "cobranzas").strip(),
            "leido": False,
            "leido_master": True,
        }
        ultimo_error = ""
        for data in self._candidatos_insert_consulta(base):
            try:
                result = self.supabase.table(self.tabla).insert(data).execute()
                if result.data:
                    return True, "Notificación registrada en consultas"
            except Exception as e:
                ultimo_error = str(e)
                if any(x in ultimo_error.lower() for x in ("column", "pgrst", "schema")):
                    continue
                print(f"Error registrando notificación comprobante: {e}")
                return False, ultimo_error
        print(f"Error registrando notificación comprobante: {ultimo_error}")
        return False, ultimo_error or "No se pudo registrar en consultas"

    def _candidatos_insert_consulta(self, base: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Variantes progresivas por si faltan columnas opcionales en Supabase."""
        omitir_etapas = (
            [],
            ["leido_master"],
            ["leido_master", "leido"],
            ["leido_master", "leido", "asunto", "usuario_email"],
            [
                "leido_master",
                "leido",
                "asunto",
                "usuario_email",
                "comprobante_id",
                "created_at",
                "estado",
                "respondido_por",
                "fecha_respuesta",
                "nombre_usuario",
                "respondido",
            ],
        )
        candidatos: List[Dict[str, Any]] = []
        vistos: set = set()
        for omitir in omitir_etapas:
            data = {k: v for k, v in base.items() if k not in omitir and v is not None}
            key = tuple(sorted(data.keys()))
            if key not in vistos:
                vistos.add(key)
                candidatos.append(data)

        mensaje_min = base.get("mensaje") or ""
        if base.get("asunto") and "asunto" not in (candidatos[-1] if candidatos else {}):
            mensaje_min = f"{base['asunto']}\n\n{mensaje_min}".strip()

        minimo: Dict[str, Any] = {
            "id": base["id"],
            "email": base["email"],
            "mensaje": mensaje_min,
            "respuesta": (base.get("respuesta") or "").strip(),
            "seccion": (base.get("seccion") or "cobranzas").strip(),
            "fecha": base["fecha"],
            "respondido": True,
        }
        key_min = tuple(sorted(minimo.keys()))
        if key_min not in vistos:
            candidatos.append(minimo)
        return candidatos

    def insertar_notificacion_cobranza(
        self,
        usuario_email: str,
        estado_acceso: str,
        cursos_solicitados: str,
        respuesta_master: str,
        master_email: str = "",
        nombre_usuario: str = "",
        comprobante_id: Optional[str] = None,
        leido: bool = False,
    ) -> Tuple[bool, str]:
        """INSERT en consultas tras aprobar/rechazar comprobante (badge + historial alumno)."""
        email_norm = (usuario_email or "").strip().lower()
        if not email_norm:
            return False, "Email de usuario inválido"

        estado_txt = (estado_acceso or "").strip().upper()
        if estado_txt not in ("APROBADO", "RECHAZADO"):
            return False, "Estado de acceso inválido"

        cursos_txt = (cursos_solicitados or "").strip() or "sin especificar"
        respuesta = (respuesta_master or "").strip()
        if not respuesta:
            respuesta = (
                "Tu pago ha sido verificado y aprobado con éxito."
                if estado_txt == "APROBADO"
                else "Rechazado por el administrador."
            )

        now = datetime.now().isoformat()
        base: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "email": email_norm,
            "usuario_email": email_norm,
            "asunto": f"Estado de Solicitud: {estado_txt}",
            "mensaje": (
                f"Revisión de comprobante de pago para el plan/curso seleccionado. "
                f"(Cursos: {cursos_txt})"
            ),
            "respuesta": respuesta,
            "estado": "Atendido" if estado_txt == "APROBADO" else "Observado",
            "fecha": now,
            "created_at": now,
            "respondido": True,
            "respondido_por": (master_email or "").strip() or None,
            "fecha_respuesta": now,
            "nombre_usuario": (nombre_usuario or email_norm.split("@")[0]).strip(),
            "seccion": "cobranzas",
            "leido": leido,
            "leido_master": True,
        }
        if comprobante_id:
            base["comprobante_id"] = str(comprobante_id).strip()

        ultimo_error = ""
        for data in self._candidatos_insert_consulta(base):
            try:
                result = self.supabase.table(self.tabla).insert(data).execute()
                if result.data:
                    return True, "Notificación de cobranza registrada en consultas"
            except Exception as e:
                ultimo_error = str(e)
                if any(x in ultimo_error.lower() for x in ("column", "pgrst", "schema")):
                    continue
                print(f"Error insertando notificación cobranza: {e}")
                return False, ultimo_error
        print(f"Error insertando notificación cobranza: {ultimo_error}")
        return False, ultimo_error or "No se pudo insertar en consultas"

    def registrar_aprobacion_comprobante(
        self,
        usuario_email: str,
        master_email: str = "",
        nombre_usuario: str = "",
        observacion: str = "",
        cursos_solicitados: str = "",
        comprobante_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        texto_resp = (observacion or "").strip() or (
            "Tu pago ha sido verificado y aprobado con éxito."
        )
        return self.insertar_notificacion_cobranza(
            usuario_email=usuario_email,
            estado_acceso="APROBADO",
            cursos_solicitados=cursos_solicitados,
            respuesta_master=texto_resp,
            master_email=master_email,
            nombre_usuario=nombre_usuario,
            comprobante_id=comprobante_id,
        )

    def registrar_rechazo_comprobante(
        self,
        usuario_email: str,
        observacion: str,
        master_email: str = "",
        nombre_usuario: str = "",
        cursos_solicitados: str = "",
        comprobante_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        return self.insertar_notificacion_cobranza(
            usuario_email=usuario_email,
            estado_acceso="RECHAZADO",
            cursos_solicitados=cursos_solicitados,
            respuesta_master=observacion,
            master_email=master_email,
            nombre_usuario=nombre_usuario,
            comprobante_id=comprobante_id,
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
        return seccion not in ("administracion", "general", "cobranzas", "")

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
        """Cantidad de respuestas/notificaciones no leídas (consultas + fallback comprobantes)."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return 0
        return len(
            [
                m
                for m in self.obtener_mensajes_usuario(email_norm)
                if self._es_consulta_no_leida(m)
            ]
        )

    def _sincronizar_comprobantes_leidos_en_consultas(self, email_norm: str) -> None:
        """Persiste filas leídas para comprobantes sin registro previo en consultas."""
        try:
            por_email = (
                self.supabase.table(self.tabla)
                .select("*")
                .eq("email", email_norm)
                .execute()
            )
            consultas = list(por_email.data or [])
        except Exception:
            consultas = []

        for comprobante in self._obtener_comprobantes_revisados_usuario(email_norm):
            if self._consulta_cubre_comprobante(comprobante, consultas):
                continue
            estado = (comprobante.get("estado") or "").strip().upper()
            if estado not in ("APROBADO", "RECHAZADO"):
                continue
            respuesta = (comprobante.get("motivo_rechazo") or "").strip()
            if not respuesta:
                respuesta = (
                    "Tu pago ha sido verificado y aprobado con éxito."
                    if estado == "APROBADO"
                    else "Rechazado por el administrador."
                )
            self.insertar_notificacion_cobranza(
                usuario_email=email_norm,
                estado_acceso=estado,
                cursos_solicitados="sin especificar",
                respuesta_master=respuesta,
                comprobante_id=comprobante.get("id"),
                leido=True,
            )

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
        except Exception as e:
            print(f"Error marcando consultas leídas (SQL): {e}")

        self._sincronizar_comprobantes_leidos_en_consultas(email_norm)

        for consulta in self.obtener_mensajes_usuario(email_norm):
            if not self._es_consulta_no_leida(consulta):
                continue
            cid = consulta.get("id")
            if not cid or str(cid).startswith("fallback-comprobante-"):
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

    def _obtener_comprobantes_revisados_usuario(self, email_norm: str) -> List[Dict[str, Any]]:
        """Salvaguarda: comprobantes aprobados/rechazados del alumno."""
        try:
            result = (
                self.supabase.table(self.tabla_comprobantes)
                .select("*")
                .eq("usuario_email", email_norm)
                .in_("estado", ["aprobado", "rechazado"])
                .order("fecha_revision", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo comprobantes revisados del usuario: {e}")
            return []

    @staticmethod
    def _comprobante_a_consulta_fallback(comprobante: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte un comprobante revisado en tarjeta compatible con Consultas."""
        estado = (comprobante.get("estado") or "").strip().lower()
        estado_txt = estado.upper() if estado else "REVISADO"
        email = (
            (comprobante.get("usuario_email") or comprobante.get("email") or "")
            .strip()
            .lower()
        )
        respuesta = (comprobante.get("motivo_rechazo") or "").strip()
        if not respuesta:
            respuesta = (
                "Tu pago ha sido verificado y aprobado con éxito."
                if estado == "aprobado"
                else "Rechazado por el administrador."
            )
        fecha = (
            comprobante.get("fecha_revision")
            or comprobante.get("creado")
            or datetime.now().isoformat()
        )
        return {
            "id": f"fallback-comprobante-{comprobante.get('id')}",
            "comprobante_id": comprobante.get("id"),
            "email": email,
            "usuario_email": email,
            "asunto": f"Estado de Solicitud: {estado_txt}",
            "mensaje": "Revisión de comprobante de pago para el plan/curso seleccionado.",
            "respuesta": respuesta,
            "seccion": "cobranzas",
            "respondido": True,
            "leido": False,
            "leido_master": True,
            "estado": "Atendido" if estado == "aprobado" else "Observado",
            "fecha": fecha,
            "_origen_fallback": "comprobantes",
        }

    def _consulta_cubre_comprobante(
        self, comprobante: Dict[str, Any], consultas: List[Dict[str, Any]]
    ) -> bool:
        """True si ya existe una fila en consultas equivalente al comprobante."""
        cid = comprobante.get("id")
        estado_txt = (comprobante.get("estado") or "").strip().upper()
        respuesta_comp = (comprobante.get("motivo_rechazo") or "").strip()
        for consulta in consultas:
            if cid and consulta.get("comprobante_id") == cid:
                return True
            if (consulta.get("seccion") or "").strip().lower() != "cobranzas":
                continue
            asunto = (consulta.get("asunto") or "").upper()
            if estado_txt and estado_txt in asunto:
                respuesta_cons = (consulta.get("respuesta") or "").strip()
                if not respuesta_comp or respuesta_cons == respuesta_comp:
                    return True
        return False

    def _fusionar_consultas_con_comprobantes(
        self, consultas: List[Dict[str, Any]], email_norm: str
    ) -> List[Dict[str, Any]]:
        """Unifica consultas + comprobantes revisados (fallback defensivo)."""
        fusion: Dict[str, Dict[str, Any]] = {}
        for row in consultas:
            rid = str(row.get("id") or id(row))
            fusion[rid] = row

        for comprobante in self._obtener_comprobantes_revisados_usuario(email_norm):
            if self._consulta_cubre_comprobante(comprobante, consultas):
                continue
            virtual = self._comprobante_a_consulta_fallback(comprobante)
            fusion[str(virtual["id"])] = virtual

        return sorted(
            fusion.values(),
            key=lambda c: c.get("fecha") or c.get("created_at") or "",
            reverse=True,
        )

    def obtener_mensajes_usuario(self, email):
        """Historial unificado: consultas + cobranzas (consultas + fallback comprobantes)."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return []
        filas: Dict[str, Dict[str, Any]] = {}

        def _agregar_filas(rows: Optional[List[Dict[str, Any]]]) -> None:
            for row in rows or []:
                rid = str(row.get("id") or id(row))
                filas[rid] = row

        try:
            por_email = (
                self.supabase.table(self.tabla)
                .select("*")
                .eq("email", email_norm)
                .order("fecha", desc=True)
                .execute()
            )
            _agregar_filas(por_email.data)
        except Exception as e:
            print(f"Error consultando consultas por email: {e}")

        try:
            por_usuario_email = (
                self.supabase.table(self.tabla)
                .select("*")
                .eq("usuario_email", email_norm)
                .order("fecha", desc=True)
                .execute()
            )
            _agregar_filas(por_usuario_email.data)
        except Exception:
            pass

        consultas = list(filas.values()) if filas else []

        if not consultas:
            try:
                result = (
                    self.supabase.table(self.tabla)
                    .select("*")
                    .order("fecha", desc=True)
                    .execute()
                )
                consultas = [
                    c
                    for c in (result.data or [])
                    if self._email_de_consulta(c) == email_norm
                ]
            except Exception as e:
                print(f"Error obteniendo consultas del usuario: {e}")
                consultas = []

        return self._fusionar_consultas_con_comprobantes(consultas, email_norm)

    def contar_no_leidos(self, email):
        """Cuenta consultas del usuario que aún no tienen respuesta."""
        mensajes = self.obtener_mensajes_usuario(email)
        return len([m for m in mensajes if self._es_consulta_pendiente(m)])
