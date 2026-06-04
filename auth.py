# auth.py - Versión robusta con PBKDF2 y sal
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any
from supabase_client import get_supabase

class AuthManager:
    """Gestor de autenticación y usuarios con Supabase"""

    def __init__(self):
        self.supabase = get_supabase()

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
        try:
            if not email or not password or not nombre:
                return False, "Todos los campos son obligatorios"
            if not email.endswith('@gmail.com'):
                return False, "Solo se permiten cuentas de Gmail"
            if len(password) < 6:
                return False, "La contraseña debe tener al menos 6 caracteres"

            existing = self.supabase.table("users").select("*").eq("email", email).execute()
            if existing.data:
                return False, "El usuario ya existe"

            password_hash, salt = self._hash_password(password)
            data = {
                "email": email,
                "password": password_hash,
                "password_salt": salt,
                "nombre": nombre,
                "rol": "usuario",
                "secciones": ["excel"],
                "creado": datetime.now().isoformat(),
                "activo": True
            }
            result = self.supabase.table("users").insert(data).execute()
            if result.data:
                return True, "Usuario registrado exitosamente"
            return False, "Error al registrar usuario"
        except Exception as e:
            print(f"Error en registro: {str(e)}")
            return False, "Error interno del servidor"

    def verificar_usuario(self, email: str, password: str) -> Tuple[bool, Optional[str], Optional[str], List[str]]:
        try:
            result = self.supabase.table("users").select("*").eq("email", email).execute()
            if not result.data:
                return False, None, None, []

            user = result.data[0]
            stored_hash = user.get("password", "")
            salt = user.get("password_salt", "")

            # Migración de contraseñas antiguas (sin sal)
            if not salt:
                if stored_hash.lower() == hashlib.sha256(password.encode()).hexdigest().lower():
                    new_hash, new_salt = self._hash_password(password)
                    self.supabase.table("users").update({
                        "password": new_hash,
                        "password_salt": new_salt
                    }).eq("email", email).execute()
                    return True, user["rol"], user["nombre"], user.get("secciones", [])
                return False, None, None, []

            if self._verify_password(password, stored_hash, salt):
                return True, user["rol"], user["nombre"], user.get("secciones", [])
            return False, None, None, []
        except Exception as e:
            print(f"Error en verificación: {str(e)}")
            return False, None, None, []

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
            ok, _, _, _ = self.verificar_usuario(email, old_password)
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