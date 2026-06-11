# auth.py - Versión robusta con PBKDF2, sal y control de pago
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any

from supabase_client import get_supabase
from payment_manager import PaymentManager


class AuthManager:
    """Gestor de autenticación y usuarios con Supabase"""

    def __init__(self):
        self.supabase = get_supabase()
        self.payments = PaymentManager()

    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hashea una contraseña con sal usando PBKDF2."""
        if salt is None:
            salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return key.hex(), salt

    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verifica una contraseña contra un hash y sal almacenados."""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == stored_hash

    def registrar_usuario(self, email: str, password: str, nombre: str) -> Tuple[bool, str]:
        """Registro legacy: crea usuario pendiente de pago (sin acceso hasta activación)."""
        ok_email, email_norm = self.payments.validar_email(email)
        if not ok_email:
            return False, email_norm
        if not nombre or not nombre.strip():
            return False, "El nombre es obligatorio"
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres"

        ok, msg = self.payments._crear_usuario_pendiente(email_norm, password, nombre)
        if not ok:
            return False, msg
        if msg == "usuario_existente_pendiente":
            return True, "Cuenta registrada. Completa el pago para activar tu acceso."
        return True, "Cuenta creada. Completa el pago para activar tu acceso."

    def verificar_usuario(
        self, email: str, password: str
    ) -> Tuple[bool, Optional[str], Optional[str], List[str], Optional[str]]:
        """
        Verifica credenciales y acceso por pago.
        Retorna: (ok, rol, nombre, secciones, mensaje_error)
        """
        try:
            ok_email, email_norm = self.payments.validar_email(email)
            if not ok_email:
                return False, None, None, [], email_norm

            result = self.supabase.table("users").select("*").eq("email", email_norm).execute()
            if not result.data:
                return False, None, None, [], "Credenciales incorrectas"

            user = result.data[0]
            stored_hash = user.get("password", "")
            salt = user.get("password_salt", "")
            password_ok = False

            if not salt:
                if stored_hash.lower() == hashlib.sha256(password.encode()).hexdigest().lower():
                    new_hash, new_salt = self._hash_password(password)
                    self.supabase.table("users").update({
                        "password": new_hash,
                        "password_salt": new_salt
                    }).eq("email", email_norm).execute()
                    password_ok = True
            elif self._verify_password(password, stored_hash, salt):
                password_ok = True

            if not password_ok:
                return False, None, None, [], "Credenciales incorrectas"

            rol = user.get("rol", "usuario")
            if not self.payments.usuario_tiene_acceso(user):
                if user.get("pago_confirmado") is False or user.get("activo") is False:
                    pendiente = (
                        self.supabase.table("pagos_pendientes")
                        .select("id")
                        .eq("email", email_norm)
                        .eq("estado", "pendiente")
                        .limit(1)
                        .execute()
                    )
                    if pendiente.data:
                        return False, None, None, [], (
                            "Tu pago Yape/Plim está pendiente de verificación por el administrador."
                        )
                return False, None, None, [], (
                    "Tu cuenta no tiene acceso activo. Completa el pago de S/ 9.90 para ingresar."
                )

            return True, rol, user["nombre"], user.get("secciones", []), None
        except Exception as e:
            print(f"Error en verificación: {str(e)}")
            return False, None, None, [], "Error interno del servidor"

    def obtener_secciones_usuario(self, email: str) -> List[str]:
        try:
            result = self.supabase.table("users").select("secciones, secciones_asignadas").eq("email", email).execute()
            if result.data:
                user = result.data[0]
                if user.get("secciones_asignadas"):
                    return user["secciones_asignadas"]
                return user.get("secciones", [])
            return ["excel"]
        except Exception:
            return ["excel"]

    def asignar_secciones_usuario(self, email: str, secciones_asignadas: List[str], master_email: str) -> Tuple[bool, str]:
        try:
            if master_email != "master@optimizo.com":
                return False, "No tienes permiso para asignar secciones"
            data = {
                "secciones_asignadas": secciones_asignadas,
                "secciones": secciones_asignadas
            }
            result = self.supabase.table("users").update(data).eq("email", email).execute()
            if result.data:
                return True, f"Secciones asignadas: {', '.join(secciones_asignadas)}"
            return False, "Usuario no encontrado"
        except Exception as e:
            print(f"Error asignando secciones: {e}")
            return False, "Error interno"

    def obtener_perfil(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.supabase.table("users").select("*").eq("email", email).execute()
            if not result.data:
                return None
            user = result.data[0]
            perfil = {
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["rol"],
                "fecha_registro": user.get("creado", ""),
                "codigo_usuario": self._generar_codigo_usuario(email),
                "telefono": "",
                "celular": "",
                "direccion": "",
                "ciudad": "",
                "pais": "Perú",
                "empresa": "",
                "cargo": ""
            }
            if user.get("perfil"):
                perfil.update(user["perfil"])
            return perfil
        except Exception as e:
            print(f"Error obteniendo perfil: {e}")
            return None

    def actualizar_perfil(self, email: str, datos_perfil: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            existing = self.supabase.table("users").select("perfil").eq("email", email).execute()
            current = existing.data[0].get("perfil", {}) if existing.data else {}
            current.update(datos_perfil)
            update_data = {"perfil": current}
            if "nombre" in datos_perfil:
                update_data["nombre"] = datos_perfil["nombre"]
            result = self.supabase.table("users").update(update_data).eq("email", email).execute()
            if result.data:
                return True, "Perfil actualizado correctamente"
            return False, "No se pudo actualizar el perfil"
        except Exception as e:
            print(f"Error actualizando perfil: {e}")
            return False, "Error interno"

    def _generar_codigo_usuario(self, email: str) -> str:
        return f"OPT-{hashlib.md5(email.encode()).hexdigest()[:8].upper()}"

    def listar_usuarios(self) -> Dict[str, Dict[str, Any]]:
        try:
            result = self.supabase.table("users").select("*").execute()
            usuarios = {}
            for u in result.data or []:
                usuarios[u["email"]] = u
            return usuarios
        except Exception as e:
            print(f"Error listando usuarios: {e}")
            return {}

    def eliminar_usuario(self, email: str, master_email: str) -> Tuple[bool, str]:
        try:
            if email == master_email:
                return False, "No puedes eliminarte a ti mismo"
            result = self.supabase.table("users").delete().eq("email", email).execute()
            if result.data:
                return True, "Usuario eliminado correctamente"
            return False, "Usuario no encontrado"
        except Exception as e:
            print(f"Error eliminando usuario: {e}")
            return False, "Error interno"

    def cambiar_contrasena(self, email: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        try:
            ok, _, _, _, _ = self.verificar_usuario(email, old_password)
            if not ok:
                return False, "Contraseña actual incorrecta"
            if len(new_password) < 6:
                return False, "La nueva contraseña debe tener al menos 6 caracteres"
            new_hash, new_salt = self._hash_password(new_password)
            result = self.supabase.table("users").update({
                "password": new_hash,
                "password_salt": new_salt
            }).eq("email", email).execute()
            if result.data:
                return True, "Contraseña actualizada correctamente"
            return False, "Error al actualizar contraseña"
        except Exception as e:
            print(f"Error cambiando contraseña: {e}")
            return False, "Error interno"
