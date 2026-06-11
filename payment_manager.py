# payment_manager.py — Cobros Culqi, Yape/Plim y activaciones Master
import hashlib
import re
import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from supabase_client import get_supabase

MONTO_SOLES = 9.90
MONTO_CENTIMOS = 990
MONEDA = "PEN"
METODO_CULQI = "culqi"
METODO_YAPE = "yape"
ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_RECHAZADO = "rechazado"

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
CELULAR_REGEX = re.compile(r"^9\d{8}$")
CODIGO_OPERACION_REGEX = re.compile(r"^[A-Za-z0-9\-]{4,30}$")


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
        limpio = str(codigo or "").strip().upper()
        if not CODIGO_OPERACION_REGEX.match(limpio):
            return False, "El código de operación debe tener entre 4 y 30 caracteres alfanuméricos"
        return True, limpio

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return key.hex(), salt

    def _obtener_usuario(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.supabase.table("users").select("*").eq("email", email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error obteniendo usuario: {_format_error(e)}")
            return None

    def codigo_operacion_existe(self, codigo: str) -> bool:
        try:
            result = (
                self.supabase.table("pagos_pendientes")
                .select("id")
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
            "metodo_pago": None,
            "codigo_operacion": None,
        }
        try:
            result = self.supabase.table("users").insert(data).execute()
            if result.data:
                return True, "usuario_creado"
            return False, "No se pudo crear el usuario en Supabase"
        except Exception as e:
            return False, f"Error al registrar usuario: {_format_error(e)}"

    def _activar_usuario_pago(
        self,
        email: str,
        metodo_pago: str,
        codigo_operacion: Optional[str] = None,
    ) -> Tuple[bool, str]:
        update_data = {
            "pago_confirmado": True,
            "activo": True,
            "metodo_pago": metodo_pago,
        }
        if codigo_operacion:
            update_data["codigo_operacion"] = codigo_operacion
        try:
            result = (
                self.supabase.table("users")
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
        ok_act, msg_act = self._activar_usuario_pago(
            email_norm,
            METODO_CULQI,
            codigo_operacion=charge_id or None,
        )
        if not ok_act:
            return False, f"Pago recibido pero error al activar cuenta: {msg_act}. Contacta soporte con ID {charge_id}"

        return True, "¡Pago confirmado! Tu cuenta está activa. Ya puedes iniciar sesión."

    def registrar_pago_manual_yape(
        self,
        email: str,
        celular: str,
        codigo_operacion: str,
        nombre: str,
        password: str,
        confirmar_password: str,
        metodo: str = METODO_YAPE,
    ) -> Tuple[bool, str]:
        ok_email, email_norm = self.validar_email(email)
        if not ok_email:
            return False, email_norm
        ok_cel, cel_norm = self.validar_celular_peru(celular)
        if not ok_cel:
            return False, cel_norm
        ok_cod, cod_norm = self.validar_codigo_operacion(codigo_operacion)
        if not ok_cod:
            return False, cod_norm
        if not nombre or not nombre.strip():
            return False, "El nombre es obligatorio"
        if password != confirmar_password:
            return False, "Las contraseñas no coinciden"

        if self.codigo_operacion_existe(cod_norm):
            return False, "Este código de operación ya fue registrado. Verifica o contacta soporte."

        pendiente_existente = (
            self.supabase.table("pagos_pendientes")
            .select("id")
            .eq("email", email_norm)
            .eq("estado", ESTADO_PENDIENTE)
            .limit(1)
            .execute()
        )
        if pendiente_existente.data:
            return False, "Ya tienes un pago pendiente de revisión con este correo"

        ok_user, msg_user = self._crear_usuario_pendiente(email_norm, password, nombre)
        if not ok_user:
            return False, msg_user

        registro = {
            "id": str(uuid.uuid4()),
            "email": email_norm,
            "celular": cel_norm,
            "codigo_operacion": cod_norm,
            "monto": MONTO_SOLES,
            "fecha": datetime.now().isoformat(),
            "estado": ESTADO_PENDIENTE,
            "nombre": nombre.strip(),
            "metodo_pago": metodo,
        }
        try:
            result = self.supabase.table("pagos_pendientes").insert(registro).execute()
            if not result.data:
                return False, "No se pudo guardar la solicitud de pago"
            return True, (
                "Solicitud registrada. Tu pago será verificado por el administrador. "
                "Recibirás acceso cuando sea aprobado."
            )
        except Exception as e:
            err = _format_error(e)
            if "duplicate" in err.lower() or "unique" in err.lower():
                return False, "Este código de operación ya fue registrado"
            return False, f"Error guardando pago pendiente: {err}"

    def listar_pagos_pendientes(self) -> List[Dict[str, Any]]:
        try:
            result = (
                self.supabase.table("pagos_pendientes")
                .select("*")
                .eq("estado", ESTADO_PENDIENTE)
                .order("fecha", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error listando pagos pendientes: {_format_error(e)}")
            return []

    def aprobar_pago(self, pago_id: str, master_email: str) -> Tuple[bool, str]:
        try:
            pago_res = (
                self.supabase.table("pagos_pendientes")
                .select("*")
                .eq("id", pago_id)
                .eq("estado", ESTADO_PENDIENTE)
                .limit(1)
                .execute()
            )
            if not pago_res.data:
                return False, "El pago ya fue procesado o no existe"

            pago = pago_res.data[0]
            email = pago["email"]
            codigo = pago["codigo_operacion"]

            ok_act, msg_act = self._activar_usuario_pago(
                email,
                pago.get("metodo_pago") or METODO_YAPE,
                codigo_operacion=codigo,
            )
            if not ok_act:
                return False, msg_act

            update_res = (
                self.supabase.table("pagos_pendientes")
                .update(
                    {
                        "estado": ESTADO_APROBADO,
                        "revisado_por": master_email,
                        "fecha_revision": datetime.now().isoformat(),
                    }
                )
                .eq("id", pago_id)
                .eq("estado", ESTADO_PENDIENTE)
                .execute()
            )
            if not update_res.data:
                return False, "No se pudo marcar el pago como aprobado (posible doble clic)"

            return True, f"Pago aprobado. Acceso activado para {email}"
        except Exception as e:
            return False, f"Error al aprobar pago: {_format_error(e)}"

    def rechazar_pago(
        self, pago_id: str, master_email: str, motivo: str
    ) -> Tuple[bool, str]:
        if not motivo or not motivo.strip():
            return False, "Debes indicar el motivo del rechazo"
        try:
            result = (
                self.supabase.table("pagos_pendientes")
                .update(
                    {
                        "estado": ESTADO_RECHAZADO,
                        "motivo_rechazo": motivo.strip(),
                        "revisado_por": master_email,
                        "fecha_revision": datetime.now().isoformat(),
                    }
                )
                .eq("id", pago_id)
                .eq("estado", ESTADO_PENDIENTE)
                .execute()
            )
            if not result.data:
                return False, "El pago ya fue procesado o no existe"
            return True, "Pago rechazado correctamente"
        except Exception as e:
            return False, f"Error al rechazar pago: {_format_error(e)}"

    def usuario_tiene_acceso(self, user: Dict[str, Any]) -> bool:
        if (user.get("rol") or "").lower() == "master":
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
        return pagos.get("yape_qr_path", "assets/yape_qr.png")

    @staticmethod
    def html_culqi_checkout(public_key: str) -> str:
        if not public_key:
            return "<p style='color:#c0392b;'>Configura culqi.public_key en secrets.toml</p>"
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://js.culqi.com/checkout-js/v4"></script>
            <style>
                body {{ font-family: system-ui, sans-serif; margin: 0; padding: 8px; }}
                button {{
                    width: 100%; padding: 14px; background: #4a6fa5; color: white;
                    border: none; border-radius: 10px; font-size: 16px; cursor: pointer;
                    font-weight: 600;
                }}
                button:hover {{ background: #2c5282; }}
                #token-box {{
                    margin-top: 12px; padding: 10px; background: #f0f4f8;
                    border-radius: 8px; font-size: 13px; word-break: break-all;
                }}
            </style>
        </head>
        <body>
            <button type="button" id="btn-culqi">💳 Pagar S/ 9.90 con tarjeta</button>
            <div id="token-box">Tras pagar, copia el token que aparecerá aquí y pégalo en el campo de abajo.</div>
            <script>
                const CulqiPublicKey = "{public_key}";
                function initCulqi() {{
                    if (typeof Culqi === "undefined") {{
                        document.getElementById("token-box").innerText = "Error cargando Culqi.js";
                        return;
                    }}
                    Culqi.publicKey = CulqiPublicKey;
                    Culqi.settings({{
                        title: "Acceso Velox",
                        currency: "PEN",
                        amount: {MONTO_CENTIMOS},
                        order: "",
                    }});
                    document.getElementById("btn-culqi").onclick = function() {{
                        Culqi.open();
                    }};
                    window.culqi = function() {{
                        if (Culqi.token) {{
                            document.getElementById("token-box").innerHTML =
                                "<strong>Token generado (cópialo):</strong><br>" + Culqi.token.id;
                        }} else if (Culqi.error) {{
                            document.getElementById("token-box").innerText =
                                "Error: " + (Culqi.error.user_message || Culqi.error.merchant_message);
                        }}
                    }};
                }}
                if (document.readyState === "loading") {{
                    document.addEventListener("DOMContentLoaded", initCulqi);
                }} else {{
                    initCulqi();
                }}
            </script>
        </body>
        </html>
        """
