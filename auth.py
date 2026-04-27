# auth.py - VERSIÓN CORREGIDA (sin duplicados ni referencias a payment_manager)
import json
import os
import hashlib
from datetime import datetime
import re

class AuthManager:
    def __init__(self):
        self.archivo_usuarios = "data/usuarios.json"
        self.asegurar_archivos()
    
    def asegurar_archivos(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.archivo_usuarios):
            usuarios_default = {
                "master@optimizo.com": {
                    "password": self.hash_password("Master2024"),
                    "nombre": "Administrador Master",
                    "rol": "master",
                    "email": "master@optimizo.com",
                    "secciones": ["contabilidad", "laboral", "financiero", "logistico", "excel"],
                    "creado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "activo": True
                }
            }
            with open(self.archivo_usuarios, 'w') as f:
                json.dump(usuarios_default, f, indent=4)
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validar_email(self, email):
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(patron, email) is not None
    
    def registrar_usuario(self, email, password, nombre):
        if not self.validar_email(email):
            return False, "Email inválido"
        if not email.endswith('@gmail.com'):
            return False, "Solo se permiten cuentas de Gmail"
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            if email in usuarios:
                return False, "El usuario ya existe"
            secciones_base = ["excel"]
            usuarios[email] = {
                "password": self.hash_password(password),
                "nombre": nombre,
                "rol": "usuario",
                "email": email,
                "secciones": secciones_base,
                "creado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "activo": True,
                "plan": "gratuito"
            }
            with open(self.archivo_usuarios, 'w') as f:
                json.dump(usuarios, f, indent=4)
            return True, "Usuario registrado exitosamente"
        except Exception as e:
            return False, str(e)
    
    def verificar_usuario(self, email, password):
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            if email in usuarios and usuarios[email]["password"] == self.hash_password(password):
                return True, usuarios[email]["rol"], usuarios[email]["nombre"], usuarios[email].get("secciones", [])
            return False, None, None, []
        except:
            return False, None, None, []
    
    def obtener_usuario(self, email):
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            return usuarios.get(email, None)
        except:
            return None
    
    def listar_usuarios(self):
        try:
            with open(self.archivo_usuarios, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def eliminar_usuario(self, email, master_email):
        if email == master_email:
            return False, "No puedes eliminarte a ti mismo"
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            if email in usuarios:
                del usuarios[email]
                with open(self.archivo_usuarios, 'w') as f:
                    json.dump(usuarios, f, indent=4)
                return True, "Usuario eliminado"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, str(e)
    
    def asignar_secciones_usuario(self, email, secciones_asignadas, master_email):
        if master_email != "master@optimizo.com":
            return False, "Solo el master puede asignar secciones"
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            if email in usuarios:
                usuarios[email]["secciones_asignadas"] = secciones_asignadas
                usuarios[email]["secciones"] = secciones_asignadas
                with open(self.archivo_usuarios, 'w') as f:
                    json.dump(usuarios, f, indent=4)
                return True, f"Secciones asignadas: {', '.join(secciones_asignadas)}"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, str(e)
    
    def obtener_secciones_usuario(self, email):
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            if email in usuarios:
                if "secciones_asignadas" in usuarios[email]:
                    return usuarios[email]["secciones_asignadas"]
                return usuarios[email].get("secciones", ["excel"])
            return ["excel"]
        except:
            return ["excel"]
    
    # ===== FUNCIONES PARA PERFIL (sin duplicados) =====
    def actualizar_perfil(self, email, datos_perfil):
        try:
            with open(self.archivo_usuarios, 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
            if email in usuarios:
                if 'perfil' not in usuarios[email]:
                    usuarios[email]['perfil'] = {}
                usuarios[email]['perfil'].update(datos_perfil)
                usuarios[email]['perfil']['ultima_actualizacion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if 'nombre' in datos_perfil:
                    usuarios[email]['nombre'] = datos_perfil['nombre']
                with open(self.archivo_usuarios, 'w', encoding='utf-8') as f:
                    json.dump(usuarios, f, indent=4, ensure_ascii=False)
                return True, "Perfil actualizado correctamente"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, str(e)
    
    def obtener_perfil(self, email):
        try:
            with open(self.archivo_usuarios, 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
            if email in usuarios:
                perfil_base = {
                    "nombre": usuarios[email].get("nombre", ""),
                    "email": email,
                    "rol": usuarios[email].get("rol", "usuario"),
                    "fecha_registro": usuarios[email].get("creado", datetime.now().strftime("%Y-%m-%d")),
                    "telefono": "",
                    "celular": "",
                    "direccion": "",
                    "ciudad": "",
                    "pais": "Perú",
                    "empresa": "",
                    "cargo": "",
                    "codigo_usuario": self.generar_codigo_usuario(email)
                }
                if 'perfil' in usuarios[email]:
                    perfil_base.update(usuarios[email]['perfil'])
                return perfil_base
            return None
        except Exception as e:
            print(f"Error en obtener_perfil: {e}")
            return None
    
    def generar_codigo_usuario(self, email):
        import hashlib
        codigo_hash = hashlib.md5(email.encode()).hexdigest()[:8].upper()
        return f"OPT-{codigo_hash}"
    
    # OBS: La función obtener_plan_usuario ha sido eliminada porque ya no se usa
