# auth.py - Con Supabase (tabla "users" con minuscula)
import hashlib
from datetime import datetime
from supabase_client import get_supabase

class AuthManager:
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def registrar_usuario(self, email, password, nombre):
        supabase = get_supabase()
        existing = supabase.table("users").select("*").eq("email", email).execute()
        if existing.data:
            return False, "El usuario ya existe"
        data = {
            "email": email,
            "password": self.hash_password(password),
            "nombre": nombre,
            "rol": "usuario",
            "secciones": ["excel"],
            "creado": datetime.now().isoformat(),
            "activo": True
        }
        result = supabase.table("users").insert(data).execute()
        if result.data:
            return True, "Usuario registrado exitosamente"
        return False, "Error al registrar"
    
    def verificar_usuario(self, email, password):
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("email", email).execute()
        if result.data:
            # Normalizar ambos hashes a minúsculas
            hash_almacenado = result.data[0]["password"].lower()
            hash_calculado = self.hash_password(password).lower()
            if hash_almacenado == hash_calculado:
                user = result.data[0]
                return True, user["rol"], user["nombre"], user.get("secciones", [])
        return False, None, None, []
    
    def obtener_secciones_usuario(self, email):
        supabase = get_supabase()
        result = supabase.table("users").select("secciones, secciones_asignadas").eq("email", email).execute()
        if result.data:
            user = result.data[0]
            if user.get("secciones_asignadas"):
                return user["secciones_asignadas"]
            return user.get("secciones", [])
        return ["excel"]
    
    def asignar_secciones_usuario(self, email, secciones_asignadas, master_email):
        if master_email != "master@optimizo.com":
            return False, "Solo el master puede asignar secciones"
        supabase = get_supabase()
        data = {
            "secciones_asignadas": secciones_asignadas,
            "secciones": secciones_asignadas
        }
        result = supabase.table("users").update(data).eq("email", email).execute()
        if result.data:
            return True, f"Secciones asignadas: {', '.join(secciones_asignadas)}"
        return False, "Usuario no encontrado"
    
    def obtener_perfil(self, email):
        supabase = get_supabase()
        result = supabase.table("users").select("nombre, email, rol, creado, perfil").eq("email", email).execute()
        if result.data:
            user = result.data[0]
            perfil = {
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["rol"],
                "fecha_registro": user["creado"],
                "codigo_usuario": self.generar_codigo_usuario(email),
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
        return None
    
    def actualizar_perfil(self, email, datos_perfil):
        supabase = get_supabase()
        existing = supabase.table("users").select("perfil").eq("email", email).execute()
        current = existing.data[0].get("perfil", {}) if existing.data else {}
        current.update(datos_perfil)
        update_data = {"perfil": current}
        if "nombre" in datos_perfil:
            update_data["nombre"] = datos_perfil["nombre"]
        result = supabase.table("users").update(update_data).eq("email", email).execute()
        if result.data:
            return True, "Perfil actualizado"
        return False, "Error al actualizar"
    
    def generar_codigo_usuario(self, email):
        import hashlib
        return f"OPT-{hashlib.md5(email.encode()).hexdigest()[:8].upper()}"
    
    def listar_usuarios(self):
        supabase = get_supabase()
        result = supabase.table("users").select("*").execute()
        usuarios = {}
        for u in result.data or []:
            usuarios[u["email"]] = u
        return usuarios
    
    def eliminar_usuario(self, email, master_email):
        if email == master_email:
            return False, "No puedes eliminarte a ti mismo"
        supabase = get_supabase()
        result = supabase.table("users").delete().eq("email", email).execute()
        if result.data:
            return True, "Usuario eliminado"
        return False, "Usuario no encontrado"