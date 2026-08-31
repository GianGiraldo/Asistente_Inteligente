# payment_manager.py — Cobros Culqi, Yape/Plim y activaciones Master
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from supabase_client import get_supabase

TABLA_USUARIOS = "users"
TABLA_COMPROBANTES = "comprobantes"
BUCKET_COMPROBANTES = "documentos"
CARPETA_COMPROBANTES = "comprobantes_pago"

MONTO_SOLES = 9.90
MONTO_CENTIMOS = 990
MONEDA = "PEN"
PLAN_1_CURSO_MONTO = 30.00
PLAN_2_CURSOS_MONTO = 50.00
PLAN_1_CURSO_LABEL = "1 Curso"
PLAN_2_CURSOS_LABEL = "2 Cursos"
CURSOS_PLAN_VALIDOS = frozenset({
    "contabilidad",
    "power_bi",
    "comercio_exterior",
    "logistico",
    "excel",
})
# Mapeo claves Supabase (cursos_solicitados) → ids internos de SECCIONES en app.py
CURSO_PLAN_A_SECCION_APP = {
    "contabilidad": "contabilidad",
    "power_bi": "laboral",
    "comercio_exterior": "financiero",
    "logistico": "logistico",
    "excel": "excel",
}
EXTENSIONES_COMPROBANTE = ("jpg", "jpeg", "png", "pdf")
CULQI_SCRIPT_URLS = (
    "https://checkout.culqi.com/js/v4",
    "https://js.culqi.com/v4",
)
CULQI_CHECKOUT_HEIGHT = 280
METODO_CULQI = "culqi"
METODO_YAPE = "yape"
METODO_YAPE_PLIM = "yape_plim"
ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_RECHAZADO = "rechazado"

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
CELULAR_REGEX = re.compile(r"^9\d{8}$")
CODIGO_OPERACION_REGEX = re.compile(r"^\d{6,8}$")


def _format_error(exc: Exception) -> str:
    partes = [str(exc)]
    for attr in ("message", "details", "hint", "code"):
        valor = getattr(exc, attr, None)
        if valor:
            partes.append(str(valor))
    return " | ".join(dict.fromkeys(partes))


class PaymentManager:
    def __init__(self):
        self.supabase = get_supabase()

    @staticmethod
    def validar_email(email: str) -> Tuple[bool, str]:
        """Validación estricta de correo. Retorna (ok, email_normalizado|mensaje_error)."""
        if not email or not str(email).strip():
            return False, "El correo electrónico es obligatorio"
        normalizado = str(email).strip().lower()
        if len(normalizado) > 254:
            return False, "El correo es demasiado largo"
        if not EMAIL_REGEX.match(normalizado):
            return False, "Ingresa un correo electrónico válido (ej. nombre@dominio.com)"
        return True, normalizado

    @staticmethod
    def validar_celular_peru(celular: str) -> Tuple[bool, str]:
        limpio = re.sub(r"\D", "", str(celular or ""))
        if not CELULAR_REGEX.match(limpio):
            return False, "El celular debe ser un número peruano de 9 dígitos (ej. 987654321)"
        return True, limpio

    @staticmethod
    def validar_codigo_operacion(codigo: str) -> Tuple[bool, str]:
        limpio = re.sub(r"\D", "", str(codigo or "").strip())
        if not CODIGO_OPERACION_REGEX.match(limpio):
            return False, "El código de operación debe ser numérico de 6 a 8 dígitos (como en Yape o Plim)"
        return True, limpio

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return key.hex(), salt

    def _obtener_usuario(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.supabase.table(TABLA_USUARIOS).select("*").eq("email", email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error obteniendo usuario: {_format_error(e)}")
            return None

    @staticmethod
    def _perfil_usuario(user: Dict[str, Any]) -> Dict[str, Any]:
        perfil = user.get("perfil")
        if isinstance(perfil, dict):
            return dict(perfil)
        if isinstance(perfil, str) and perfil.strip():
            try:
                return dict(json.loads(perfil))
            except json.JSONDecodeError:
                return {}
        return {}

    def _obtener_comprobante_pendiente(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            result = (
                self.supabase.table(TABLA_COMPROBANTES)
                .select("*")
                .eq("usuario_email", email)
                .eq("estado", ESTADO_PENDIENTE)
                .order("creado", desc=True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error consultando comprobante pendiente: {_format_error(e)}")
            return None

    def _obtener_comprobante_por_id(self, comprobante_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = (
                self.supabase.table(TABLA_COMPROBANTES)
                .select("*")
                .eq("id", comprobante_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error obteniendo comprobante: {_format_error(e)}")
            return None

    def _comprobante_a_pago_pendiente(
        self, comprobante: Dict[str, Any], user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        email = comprobante.get("usuario_email", "")
        return {
            "id": comprobante.get("id"),
            "email": email,
            "nombre": (user or {}).get("nombre", email.split("@")[0]),
            "celular": comprobante.get("celular", ""),
            "comprobante_url": (
                comprobante.get("archivo_url")
                or comprobante.get("url")
                or comprobante.get("voucher_url")
            ),
            "monto": float(comprobante.get("monto") or MONTO_SOLES),
            "fecha": comprobante.get("creado"),
            "metodo_pago": comprobante.get("metodo_pago") or METODO_YAPE_PLIM,
            "estado": comprobante.get("estado", ESTADO_PENDIENTE),
            "plan_seleccionado": comprobante.get("plan_seleccionado") or "—",
            "cursos_solicitados": comprobante.get("cursos_solicitados") or [],
        }

    def _insertar_comprobante(
        self,
        email_norm: str,
        cel_norm: str,
        comprobante_url: str,
        comprobante_ruta: str = "",
        metodo_pago: str = METODO_YAPE_PLIM,
        monto: Optional[float] = None,
        plan_seleccionado: Optional[str] = None,
        cursos_solicitados: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Inserta registro en tabla comprobantes (payload mínimo compatible con Supabase)."""
        monto_final = float(monto if monto is not None else MONTO_SOLES)
        base = {
            "usuario_email": email_norm,
            "celular": cel_norm or None,
            "metodo_pago": metodo_pago,
            "archivo_url": comprobante_url,
            "estado": ESTADO_PENDIENTE,
            "monto": monto_final,
        }
        if comprobante_ruta:
            base["archivo_ruta"] = comprobante_ruta
        if plan_seleccionado:
            base["plan_seleccionado"] = plan_seleccionado
        if cursos_solicitados is not None:
            base["cursos_solicitados"] = cursos_solicitados

        candidatos = [base, {k: v for k, v in base.items() if v is not None}]
        candidatos.extend(
            [
                {
                    "usuario_email": email_norm,
                    "celular": cel_norm,
                    "metodo_pago": metodo_pago,
                    "archivo_url": comprobante_url,
                    "estado": ESTADO_PENDIENTE,
                    "monto": monto_final,
                },
                {
                    "usuario_email": email_norm,
                    "celular": cel_norm,
                    "metodo_pago": metodo_pago,
                    "archivo_url": comprobante_url,
                    "estado": ESTADO_PENDIENTE,
                },
                {
                    "usuario_email": email_norm,
                    "celular": cel_norm,
                    "metodo_pago": metodo_pago,
                    "archivo_url": comprobante_url,
                },
            ]
        )
        ultimo_error = ""
        for data in candidatos:
            try:
                result = self.supabase.table(TABLA_COMPROBANTES).insert(data).execute()
                if result.data:
                    return True, "ok"
                return False, "No se pudo registrar el comprobante en Supabase"
            except Exception as e:
                ultimo_error = _format_error(e)
                if "PGRST204" in ultimo_error or "could not find" in ultimo_error.lower():
                    continue
                return False, f"Error guardando comprobante: {ultimo_error}"
        return False, (
            f"Error guardando comprobante: {ultimo_error}. "
            "Ejecuta sql/payments_schema.sql en Supabase para alinear la tabla comprobantes."
        )

    def _subir_comprobante_pago(
        self, email: str, archivo: Any
    ) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """Sube captura Yape/Plim a Supabase Storage. Retorna (ok, msg, url, ruta)."""
        try:
            extension = (archivo.name or "captura.jpg").split(".")[-1].lower()
            if extension not in EXTENSIONES_COMPROBANTE:
                return (
                    False,
                    "Formatos permitidos: JPG, PNG o PDF.",
                    None,
                    None,
                )
            email_slug = re.sub(r"[^a-z0-9]+", "_", email.lower()).strip("_")
            nombre_unico = f"{uuid.uuid4()}.{extension}"
            ruta = f"{CARPETA_COMPROBANTES}/{email_slug}/{nombre_unico}"
            content_types = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "pdf": "application/pdf",
            }
            content_type = getattr(archivo, "type", None) or content_types.get(
                extension, "application/octet-stream"
            )
            self.supabase.storage.from_(BUCKET_COMPROBANTES).upload(
                ruta,
                archivo.getvalue(),
                {"content-type": content_type, "upsert": "false"},
            )
            url = self.supabase.storage.from_(BUCKET_COMPROBANTES).get_public_url(ruta)
            return True, "Comprobante subido", url, ruta
        except Exception as e:
            return False, f"No se pudo subir la captura: {_format_error(e)}", None, None

    def codigo_operacion_existe(self, codigo: str) -> bool:
        try:
            result = (
                self.supabase.table(TABLA_USUARIOS)
                .select("email")
                .eq("codigo_operacion", codigo)
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Error verificando código de operación: {_format_error(e)}")
            return True

    def _crear_usuario_pendiente(
        self, email: str, password: str, nombre: str
    ) -> Tuple[bool, str]:
        existente = self._obtener_usuario(email)
        if existente:
            if existente.get("pago_confirmado") and existente.get("activo"):
                return False, "Ya existe una cuenta activa con este correo"
            return True, "usuario_existente_pendiente"

        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres"

        password_hash, salt = self._hash_password(password)
        data = {
            "email": email,
            "password": password_hash,
            "password_salt": salt,
            "nombre": nombre.strip(),
            "rol": "usuario",
            "secciones": ["excel"],
            "creado": datetime.now().isoformat(),
            "activo": False,
            "pago_confirmado": False,
            "perfil": {"velox_password_configured": True},
        }
        try:
            result = self.supabase.table(TABLA_USUARIOS).insert(data).execute()
            if result.data:
                return True, "usuario_creado"
            return False, "No se pudo crear el usuario en Supabase"
        except Exception as e:
            return False, f"Error al registrar usuario: {_format_error(e)}"

    def _activar_usuario_pago(self, email: str) -> Tuple[bool, str]:
        update_data = {
            "pago_confirmado": True,
            "activo": True,
        }
        try:
            result = (
                self.supabase.table(TABLA_USUARIOS)
                .update(update_data)
                .eq("email", email)
                .execute()
            )
            if result.data:
                return True, "Cuenta activada correctamente"
            return False, "No se encontró el usuario para activar"
        except Exception as e:
            return False, f"Error activando usuario: {_format_error(e)}"

    def _cobrar_culqi(
        self, email: str, token_id: str, descripcion: str = "Acceso aplicativo Velox"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        import streamlit as st

        secret_key = st.secrets.get("culqi", {}).get("secret_key")
        if not secret_key:
            return False, "Culqi no configurado: falta culqi.secret_key en secrets.toml", None

        payload = {
            "amount": MONTO_CENTIMOS,
            "currency_code": MONEDA,
            "email": email,
            "source_id": token_id.strip(),
            "description": descripcion,
        }
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                "https://api.culqi.com/v2/charges",
                json=payload,
                headers=headers,
                timeout=30,
            )
            data = response.json()
            if response.status_code in (200, 201):
                outcome = (data.get("outcome") or {}).get("type", "")
                if data.get("object") == "charge" and outcome not in ("failed", "rechazo"):
                    return True, "Pago procesado correctamente", data
                return False, data.get("user_message") or data.get("merchant_message") or "Pago rechazado", data
            mensaje = (
                data.get("user_message")
                or data.get("merchant_message")
                or data.get("message")
                or response.text
            )
            return False, f"Culqi rechazó el pago: {mensaje}", data
        except requests.RequestException as e:
            return False, f"Error de conexión con Culqi: {e}", None

    def procesar_registro_culqi(
        self,
        email: str,
        nombre: str,
        password: str,
        confirmar_password: str,
        token_culqi: str,
    ) -> Tuple[bool, str]:
        ok_email, email_norm = self.validar_email(email)
        if not ok_email:
            return False, email_norm
        if not nombre or not nombre.strip():
            return False, "El nombre es obligatorio"
        if password != confirmar_password:
            return False, "Las contraseñas no coinciden"
        if not token_culqi or not token_culqi.strip():
            return False, "Completa el pago con tarjeta antes de continuar (token Culqi requerido)"

        ok_user, msg_user = self._crear_usuario_pendiente(email_norm, password, nombre)
        if not ok_user:
            return False, msg_user

        ok_culqi, msg_culqi, charge = self._cobrar_culqi(email_norm, token_culqi)
        if not ok_culqi:
            return False, msg_culqi

        charge_id = (charge or {}).get("id", "")
        ok_act, msg_act = self._activar_usuario_pago(email_norm)
        if not ok_act:
            return False, f"Pago recibido pero error al activar cuenta: {msg_act}. Contacta soporte con ID {charge_id}"

        return True, "¡Pago confirmado! Tu cuenta está activa. Ya puedes iniciar sesión."

    def registrar_verificacion_yape_plim(
        self,
        nombre: str,
        email: str,
        password: str,
        celular: str,
        codigo_operacion: str,
    ) -> Tuple[bool, str]:
        """Registro + pago pendiente Yape/Plim (usuario inactivo en tabla users)."""
        campos_obligatorios = {
            "Nombre completo": nombre,
            "Correo electrónico": email,
            "Contraseña": password,
            "Celular de la operación": celular,
            "Código de operación": codigo_operacion,
        }
        vacios = [etiqueta for etiqueta, valor in campos_obligatorios.items() if not str(valor or "").strip()]
        if vacios:
            return False, f"Completa todos los campos obligatorios: {', '.join(vacios)}"

        ok_email, email_norm = self.validar_email(email)
        if not ok_email:
            return False, email_norm
        ok_cel, cel_norm = self.validar_celular_peru(celular)
        if not ok_cel:
            return False, cel_norm
        ok_cod, cod_norm = self.validar_codigo_operacion(codigo_operacion)
        if not ok_cod:
            return False, cod_norm
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres"

        return self._guardar_registro_yape_plim(email_norm, cel_norm, cod_norm, nombre.strip(), password)

    def registrar_comprobante_yape_oauth(
        self,
        email: str,
        nombre: str,
        celular: str,
        comprobante_file: Any = None,
    ) -> Tuple[bool, str]:
        """Registra solicitud Yape/Plim con captura JPEG y celular (sin codigo_operacion)."""
        if not comprobante_file:
            return False, "Adjunta la captura de tu comprobante en formato JPEG."

        ok_email, email_norm = self.validar_email(email)
        if not ok_email:
            return False, email_norm

        if not str(celular or "").strip():
            return False, "El celular de la operación es obligatorio"
        ok_cel, cel_norm = self.validar_celular_peru(celular)
        if not ok_cel:
            return False, cel_norm

        user = self._obtener_usuario(email_norm)
        if not user:
            return False, "No encontramos tu perfil. Vuelve a iniciar sesión con Google."
        if user.get("pago_confirmado") and user.get("activo"):
            return False, "Tu suscripción ya está activa."
        if self._obtener_comprobante_pendiente(email_norm):
            return False, "Ya tienes una solicitud pendiente de revisión."

        ok_up, msg_up, url, ruta = self._subir_comprobante_pago(email_norm, comprobante_file)
        if not ok_up:
            return False, msg_up

        return self._insertar_comprobante(email_norm, cel_norm, url, ruta)

    def registrar_comprobante_plan_cursos(
        self,
        email: str,
        plan_id: str,
        cursos_ids: List[str],
        comprobante_file: Any = None,
    ) -> Tuple[bool, str]:
        """Registra solicitud de plan de cursos con comprobante Yape/Plim."""
        planes = {
            "1_curso": (PLAN_1_CURSO_MONTO, PLAN_1_CURSO_LABEL, 1),
            "2_cursos": (PLAN_2_CURSOS_MONTO, PLAN_2_CURSOS_LABEL, 2),
        }
        plan = planes.get((plan_id or "").strip())
        if not plan:
            return False, "Selecciona un plan válido."

        monto, plan_label, max_cursos = plan
        ok_email, email_norm = self.validar_email(email)
        if not ok_email:
            return False, email_norm

        if not comprobante_file:
            return False, "Adjunta la captura o comprobante de tu transferencia."

        cursos_limpios = []
        for curso_id in cursos_ids or []:
            curso_norm = str(curso_id or "").strip().lower()
            if curso_norm and curso_norm not in cursos_limpios:
                cursos_limpios.append(curso_norm)

        if len(cursos_limpios) != max_cursos:
            if max_cursos == 1:
                return False, "Debes seleccionar exactamente 1 curso para el Plan Individual."
            return False, "Debes seleccionar exactamente 2 cursos para el Plan Dúo."

        invalidos = [c for c in cursos_limpios if c not in CURSOS_PLAN_VALIDOS]
        if invalidos:
            return False, f"Cursos no válidos: {', '.join(invalidos)}."

        user = self._obtener_usuario(email_norm)
        if not user:
            return False, "No encontramos tu perfil. Vuelve a iniciar sesión."

        if self._obtener_comprobante_pendiente(email_norm):
            return False, "Ya tienes una solicitud pendiente de revisión."

        ok_up, msg_up, url, ruta = self._subir_comprobante_pago(email_norm, comprobante_file)
        if not ok_up:
            return False, msg_up

        ok_ins, msg_ins = self._insertar_comprobante(
            email_norm,
            "",
            url,
            ruta or "",
            metodo_pago=METODO_YAPE_PLIM,
            monto=monto,
            plan_seleccionado=plan_label,
            cursos_solicitados=cursos_limpios,
        )
        if not ok_ins:
            return False, msg_ins

        nombres = ", ".join(cursos_limpios)
        return (
            True,
            f"Solicitud enviada correctamente. Plan {plan_label} · S/ {monto:.2f} · Cursos: {nombres}. "
            "Un administrador revisará tu comprobante y activará el acceso.",
        )

    def procesar_pago_culqi_oauth(self, email: str, nombre: str, token_culqi: str) -> Tuple[bool, str]:
        """Culqi vinculado al correo Google de la sesión actual."""
        ok_email, email_norm = self.validar_email(email)
        if not ok_email:
            return False, email_norm
        if not token_culqi or not token_culqi.strip():
            return False, "Completa el pago con tarjeta (token Culqi requerido)."

        user = self._obtener_usuario(email_norm)
        if user and user.get("pago_confirmado") and user.get("activo"):
            return False, "Tu suscripción ya está activa."

        ok_culqi, msg_culqi, charge = self._cobrar_culqi(email_norm, token_culqi)
        if not ok_culqi:
            return False, msg_culqi

        charge_id = (charge or {}).get("id", "")
        ok_act, msg_act = self._activar_usuario_pago(email_norm)
        if not ok_act:
            return False, f"Pago recibido pero error al activar: {msg_act}"
        return True, "¡Pago confirmado! Tu acceso está activo."

    def _guardar_registro_yape_plim(
        self,
        email_norm: str,
        cel_norm: str,
        cod_norm: str,
        nombre: str,
        password: str,
    ) -> Tuple[bool, str]:

        if self.codigo_operacion_existe(cod_norm):
            return False, "Este código de operación ya fue registrado. Verifica o contacta soporte."

        if self._obtener_comprobante_pendiente(email_norm):
            return False, "Ya tienes un pago pendiente de revisión con este correo"

        ok_user, msg_user = self._crear_usuario_pendiente(email_norm, password, nombre)
        if not ok_user:
            return False, msg_user

        return self._insertar_comprobante(
            email_norm,
            cel_norm,
            comprobante_url="",
            comprobante_ruta="",
        )

    def listar_pagos_pendientes(self) -> List[Dict[str, Any]]:
        """Lista comprobantes pendientes desde tabla comprobantes."""
        try:
            result = (
                self.supabase.table(TABLA_COMPROBANTES)
                .select("*")
                .eq("estado", ESTADO_PENDIENTE)
                .order("creado", desc=True)
                .execute()
            )
            pagos = []
            for comprobante in result.data or []:
                user = self._obtener_usuario(comprobante.get("usuario_email", ""))
                pagos.append(self._comprobante_a_pago_pendiente(comprobante, user))
            return pagos
        except Exception as e:
            print(f"Error listando comprobantes pendientes: {_format_error(e)}")
            return []

    def contar_pagos_pendientes(self) -> int:
        """Cantidad de solicitudes de compra/acceso pendientes de revisión."""
        for tabla in ("pagos", TABLA_COMPROBANTES):
            try:
                result = (
                    self.supabase.table(tabla)
                    .select("id", count="exact")
                    .eq("estado", ESTADO_PENDIENTE)
                    .execute()
                )
                if result.count is not None:
                    return int(result.count)
            except Exception:
                continue
        return len(self.listar_pagos_pendientes())

    def aprobar_pago(
        self, pago_id: str, master_email: str, observacion: str = ""
    ) -> Tuple[bool, str]:
        """Aprueba comprobante; pago_id = UUID del registro en tabla comprobantes."""
        try:
            comprobante = self._obtener_comprobante_por_id((pago_id or "").strip())
            if not comprobante or comprobante.get("estado") != ESTADO_PENDIENTE:
                return False, "El pago ya fue procesado o no existe"

            email = (comprobante.get("usuario_email") or "").strip().lower()
            cursos_aprobados = self._normalizar_lista_cursos(
                comprobante.get("cursos_solicitados")
            )
            if cursos_aprobados:
                ok_act, msg_act = self._aplicar_cursos_aprobados_a_usuario(
                    email, cursos_aprobados
                )
            else:
                ok_act, msg_act = self._activar_usuario_pago(email)
            if not ok_act:
                return False, msg_act

            update_payload: Dict[str, Any] = {
                "estado": ESTADO_APROBADO,
                "revisado_por": master_email,
                "fecha_revision": datetime.now().isoformat(),
            }
            obs = (observacion or "").strip()
            if obs:
                update_payload["motivo_rechazo"] = obs
            try:
                self.supabase.table(TABLA_COMPROBANTES).update(update_payload).eq(
                    "id", comprobante["id"]
                ).execute()
            except Exception:
                self.supabase.table(TABLA_COMPROBANTES).update(
                    {"estado": ESTADO_APROBADO}
                ).eq("id", comprobante["id"]).execute()

            ok_consulta, msg_consulta = self._registrar_consulta_aprobacion_comprobante(
                email, master_email, comprobante, observacion=observacion
            )
            if not ok_consulta:
                print(
                    "Aviso: INSERT consultas vía Python falló; el trigger SQL en "
                    f"comprobantes debe crear el aviso al alumno. Detalle: {msg_consulta}"
                )

            if cursos_aprobados:
                secciones = [
                    s
                    for s in (
                        self._mapear_curso_plan_a_seccion(c) for c in cursos_aprobados
                    )
                    if s
                ]
                return (
                    True,
                    f"Pago aprobado. Cursos activados para {email}: {', '.join(secciones)}",
                )
            return True, f"Pago aprobado. Acceso activado para {email}"
        except Exception as e:
            return False, f"Error al aprobar pago: {_format_error(e)}"

    def rechazar_pago(
        self, pago_id: str, master_email: str, motivo: str
    ) -> Tuple[bool, str]:
        motivo_l = (motivo or "").strip() or "Rechazado por el administrador"
        try:
            comprobante = self._obtener_comprobante_por_id((pago_id or "").strip())
            if not comprobante or comprobante.get("estado") != ESTADO_PENDIENTE:
                return False, "El pago ya fue procesado o no existe"

            try:
                result = (
                    self.supabase.table(TABLA_COMPROBANTES)
                    .update(
                        {
                            "estado": ESTADO_RECHAZADO,
                            "motivo_rechazo": motivo_l,
                            "revisado_por": master_email,
                            "fecha_revision": datetime.now().isoformat(),
                        }
                    )
                    .eq("id", comprobante["id"])
                    .execute()
                )
            except Exception:
                result = (
                    self.supabase.table(TABLA_COMPROBANTES)
                    .update({"estado": ESTADO_RECHAZADO})
                    .eq("id", comprobante["id"])
                    .execute()
                )
            if not result.data:
                return False, "No se pudo registrar el rechazo"

            email = (comprobante.get("usuario_email") or "").strip().lower()
            ok_consulta, msg_consulta = self._registrar_consulta_rechazo_comprobante(
                email, motivo_l, master_email, comprobante
            )
            if not ok_consulta:
                print(
                    "Aviso: INSERT consultas vía Python falló; el trigger SQL en "
                    f"comprobantes debe crear el aviso al alumno. Detalle: {msg_consulta}"
                )
            return True, "Pago rechazado correctamente"
        except Exception as e:
            return False, f"Error al rechazar pago: {_format_error(e)}"

    @staticmethod
    def _texto_cursos_comprobante(comprobante: Optional[Dict[str, Any]]) -> str:
        if not comprobante:
            return "sin especificar"
        raw = comprobante.get("cursos_solicitados")
        if raw is None:
            return "sin especificar"
        if isinstance(raw, str):
            texto = raw.strip()
            if not texto:
                return "sin especificar"
            try:
                parsed = json.loads(texto)
                if isinstance(parsed, list):
                    raw = parsed
                else:
                    return texto
            except json.JSONDecodeError:
                return texto
        if isinstance(raw, list):
            cursos = PaymentManager._normalizar_lista_cursos(raw)
            if not cursos:
                return "sin especificar"
            return ", ".join(cursos)
        return str(raw)

    def _registrar_consulta_aprobacion_comprobante(
        self,
        email: str,
        master_email: str,
        comprobante: Optional[Dict[str, Any]] = None,
        observacion: str = "",
    ) -> Tuple[bool, str]:
        try:
            from message_manager import MessageManager

            user = self._obtener_usuario(email)
            nombre = (user or {}).get("nombre") or email.split("@")[0]
            return MessageManager().registrar_aprobacion_comprobante(
                email,
                master_email=master_email,
                nombre_usuario=nombre,
                observacion=observacion,
                cursos_solicitados=self._texto_cursos_comprobante(comprobante),
                comprobante_id=(comprobante or {}).get("id"),
            )
        except Exception as e:
            err = _format_error(e)
            print(f"No se pudo registrar consulta de aprobación: {err}")
            return False, err

    def _registrar_consulta_rechazo_comprobante(
        self,
        email: str,
        observacion: str,
        master_email: str,
        comprobante: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        try:
            from message_manager import MessageManager

            user = self._obtener_usuario(email)
            nombre = (user or {}).get("nombre") or email.split("@")[0]
            return MessageManager().registrar_rechazo_comprobante(
                email,
                observacion,
                master_email=master_email,
                nombre_usuario=nombre,
                cursos_solicitados=self._texto_cursos_comprobante(comprobante),
                comprobante_id=(comprobante or {}).get("id"),
            )
        except Exception as e:
            err = _format_error(e)
            print(f"No se pudo registrar consulta de rechazo: {err}")
            return False, err

    def registrar_verification_yape_lim(
        self,
        nombre: str,
        email: str,
        password: str,
        celular: str,
        codigo_operacion: str,
    ) -> Tuple[bool, str]:
        """Alias de compatibilidad — delega en registrar_verificacion_yape_plim."""
        return self.registrar_verificacion_yape_plim(
            nombre, email, password, celular, codigo_operacion
        )

    def registrar_pago_manual_yape(
        self,
        email: str,
        celular: str,
        codigo_operacion: str,
        nombre: str,
        password: str,
        confirmar_password: str,
        metodo: str = METODO_YAPE_PLIM,
    ) -> Tuple[bool, str]:
        if password != confirmar_password:
            return False, "Las contraseñas no coinciden"
        ok, msg = self.registrar_verificacion_yape_plim(
            nombre, email, password, celular, codigo_operacion
        )
        if not ok:
            return False, msg
        return True, msg

    def _mapear_curso_plan_a_seccion(self, curso_id: str) -> Optional[str]:
        curso_norm = (curso_id or "").strip().lower()
        if curso_norm in CURSO_PLAN_A_SECCION_APP:
            return CURSO_PLAN_A_SECCION_APP[curso_norm]
        if curso_norm in CURSO_PLAN_A_SECCION_APP.values():
            return curso_norm
        return None

    @staticmethod
    def _normalizar_lista_cursos(valor: Any) -> List[str]:
        if valor is None:
            return []
        if isinstance(valor, str):
            texto = valor.strip()
            if not texto:
                return []
            try:
                parsed = json.loads(texto)
                if isinstance(parsed, list):
                    return [str(x).strip().lower() for x in parsed if str(x).strip()]
            except json.JSONDecodeError:
                return [texto.lower()]
            return []
        if isinstance(valor, list):
            return [str(x).strip().lower() for x in valor if str(x).strip()]
        return []

    def _secciones_desde_comprobantes_aprobados(self, email: str) -> List[str]:
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return []
        try:
            result = (
                self.supabase.table(TABLA_COMPROBANTES)
                .select("cursos_solicitados")
                .eq("usuario_email", email_norm)
                .eq("estado", ESTADO_APROBADO)
                .execute()
            )
            secciones: List[str] = []
            for row in result.data or []:
                for curso in self._normalizar_lista_cursos(row.get("cursos_solicitados")):
                    sec = self._mapear_curso_plan_a_seccion(curso)
                    if sec and sec not in secciones:
                        secciones.append(sec)
            return secciones
        except Exception as e:
            print(f"Error leyendo comprobantes aprobados: {_format_error(e)}")
            return []

    def obtener_secciones_acceso_usuario(self, email: str) -> List[str]:
        """Secciones efectivas: users.secciones_asignadas/secciones + cursos de comprobantes aprobados."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return []
        user = self._obtener_usuario(email_norm)
        base: List[str] = []
        if user:
            raw = user.get("secciones_asignadas") or user.get("secciones") or []
            base = [str(s).strip() for s in raw if str(s).strip()]
        extra = self._secciones_desde_comprobantes_aprobados(email_norm)
        return list(dict.fromkeys(base + extra))

    def _aplicar_cursos_aprobados_a_usuario(
        self, email: str, cursos_plan: List[str]
    ) -> Tuple[bool, str]:
        email_norm = (email or "").strip().lower()
        secciones_nuevas: List[str] = []
        for curso in cursos_plan or []:
            sec = self._mapear_curso_plan_a_seccion(curso)
            if sec and sec not in secciones_nuevas:
                secciones_nuevas.append(sec)

        if not secciones_nuevas:
            return self._activar_usuario_pago(email_norm)

        user = self._obtener_usuario(email_norm)
        if not user:
            return False, "Usuario no encontrado"

        actuales = list(user.get("secciones_asignadas") or user.get("secciones") or [])
        merged = list(dict.fromkeys(actuales + secciones_nuevas))
        update_data: Dict[str, Any] = {
            "secciones_asignadas": merged,
            "secciones": merged,
            "activo": True,
            "pago_confirmado": True,
        }
        try:
            result = (
                self.supabase.table(TABLA_USUARIOS)
                .update(update_data)
                .eq("email", email_norm)
                .execute()
            )
            if result.data:
                return True, "ok"
            return False, "No se pudo actualizar las secciones del usuario"
        except Exception as e:
            return False, f"Error actualizando secciones: {_format_error(e)}"

    def usuario_tiene_acceso(self, user: Dict[str, Any]) -> bool:
        rol = (user.get("rol") or "").lower()
        if rol in ("master", "administrador"):
            return True
        return bool(user.get("pago_confirmado")) and bool(user.get("activo"))

    @staticmethod
    def obtener_public_key_culqi() -> str:
        import streamlit as st

        return st.secrets.get("culqi", {}).get("public_key", "")

    @staticmethod
    def obtener_ruta_qr_yape() -> str:
        import streamlit as st

        pagos = st.secrets.get("payments", {})
        return pagos.get("yape_qr_path", "assets/qr_pago.png")

    @staticmethod
    def culqi_checkout_height() -> int:
        return CULQI_CHECKOUT_HEIGHT

    @staticmethod
    def html_culqi_checkout(public_key: str) -> str:
        if not public_key:
            return "<p style='color:#c0392b;font-family:system-ui;padding:12px;'>Configura culqi.public_key en secrets.toml</p>"

        pk = public_key.replace("\\", "\\\\").replace('"', '\\"')
        script_urls = json.dumps(list(CULQI_SCRIPT_URLS))

        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: system-ui, -apple-system, sans-serif;
    margin: 0;
    padding: 10px 8px 16px;
    background: transparent;
  }}
  #btn-culqi {{
    width: 100%;
    padding: 14px 16px;
    background: linear-gradient(180deg, #1e3a5f 0%, #152a45 100%);
    color: #fff;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(30, 58, 95, 0.28);
  }}
  #btn-culqi:hover {{ filter: brightness(1.06); }}
  #btn-culqi:disabled {{
    opacity: 0.65;
    cursor: wait;
  }}
  #token-box {{
    margin-top: 12px;
    padding: 10px 12px;
    background: #f0f4f8;
    border: 1px solid #dce5f0;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.45;
    color: #334155;
    word-break: break-word;
  }}
  #token-box.ok {{ background: #ecfdf5; border-color: #6ee7b7; color: #065f46; }}
  #token-box.err {{ background: #fef2f2; border-color: #fecaca; color: #991b1b; }}
</style>
</head>
<body>
  <button type="button" id="btn-culqi">💳 Pagar S/ {MONTO_SOLES:.2f} con tarjeta</button>
  <div id="token-box">Pulsa el botón para abrir la pasarela segura de Culqi.</div>
  <script>
    (function () {{
      const PUBLIC_KEY = "{pk}";
      const AMOUNT = {MONTO_CENTIMOS};
      const SCRIPT_URLS = {script_urls};
      const box = document.getElementById("token-box");
      const btn = document.getElementById("btn-culqi");

      function setBox(text, cls) {{
        box.className = cls || "";
        box.textContent = text;
      }}

      function sendTokenToApp(token) {{
        setBox("Token generado. Confirmando pago…", "ok");
        btn.disabled = true;
        try {{
          window.parent.postMessage({{
            isStreamlitMessage: true,
            type: "streamlit:setComponentValue",
            value: token,
          }}, "*");
        }} catch (e) {{}}
        try {{
          const topWin = window.top || window.parent || window;
          const url = new URL(topWin.location.href);
          url.searchParams.set("culqi_token", token);
          topWin.location.assign(url.toString());
        }} catch (err) {{
          setBox("Token generado. Pégalo en el campo de abajo: " + token, "ok");
          btn.disabled = false;
        }}
      }}

      window.culqi = function culqiCallback() {{
        if (window.Culqi && Culqi.token && Culqi.token.id) {{
          const token = Culqi.token.id;
          try {{ Culqi.close(); }} catch (e) {{}}
          sendTokenToApp(token);
          return;
        }}
        if (window.Culqi && Culqi.order) {{
          try {{ Culqi.close(); }} catch (e) {{}}
          setBox("Orden creada. Revisa tu método de pago.", "ok");
          return;
        }}
        if (window.Culqi && Culqi.error) {{
          const msg = Culqi.error.user_message || Culqi.error.merchant_message || "Error en Culqi";
          setBox("Error: " + msg, "err");
        }}
      }};

      function bootCulqi() {{
        if (typeof Culqi === "undefined") {{
          setBox("No se pudo cargar Culqi. Revisa tu conexión e intenta de nuevo.", "err");
          return;
        }}
        Culqi.publicKey = PUBLIC_KEY;
        Culqi.settings({{
          title: "Acceso veloX",
          currency: "PEN",
          amount: AMOUNT,
        }});
        Culqi.options({{
          lang: "es",
          installments: false,
          paymentMethods: {{ tarjeta: true, yape: false, bancaMovil: false, agente: false, billetera: false, cuotealo: false }},
        }});
        btn.disabled = false;
        btn.onclick = function (e) {{
          e.preventDefault();
          setBox("Abriendo pasarela Culqi…", "");
          Culqi.open();
        }};
        setBox("Listo. Pulsa el botón para pagar con tarjeta.", "");
      }}

      function loadScript(index) {{
        if (index >= SCRIPT_URLS.length) {{
          setBox("No se pudo cargar el script de Culqi.", "err");
          return;
        }}
        const src = SCRIPT_URLS[index];
        const existing = document.querySelector('script[data-culqi-src="' + src + '"]');
        if (existing) {{
          bootCulqi();
          return;
        }}
        const tag = document.createElement("script");
        tag.src = src;
        tag.async = true;
        tag.defer = true;
        tag.setAttribute("data-culqi-src", src);
        tag.onload = function () {{
          if (typeof Culqi === "undefined") {{
            loadScript(index + 1);
            return;
          }}
          bootCulqi();
        }};
        tag.onerror = function () {{
          loadScript(index + 1);
        }};
        document.head.appendChild(tag);
      }}

      btn.disabled = true;
      setBox("Cargando pasarela Culqi…", "");
      loadScript(0);
    }})();
  </script>
</body>
</html>
"""
