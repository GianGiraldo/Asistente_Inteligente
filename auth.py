# auth.py
import streamlit as st
import json
import os
import hashlib
from datetime import datetime, timedelta
import re

class AuthManager:
    def actualizar_perfil(self, email, datos_perfil):
        """Actualizar información de perfil del usuario"""
        try:
            with open(self.archivo_usuarios, 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
            
            if email in usuarios:
                # Actualizar datos del perfil
                if 'perfil' not in usuarios[email]:
                    usuarios[email]['perfil'] = {}
                
                usuarios[email]['perfil'].update(datos_perfil)
                usuarios[email]['perfil']['ultima_actualizacion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # También actualizar el nombre principal si cambió
                if 'nombre' in datos_perfil:
                    usuarios[email]['nombre'] = datos_perfil['nombre']
                
                with open(self.archivo_usuarios, 'w', encoding='utf-8') as f:
                    json.dump(usuarios, f, indent=4, ensure_ascii=False)
                
                return True, "Perfil actualizado correctamente"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, str(e)
    
    def obtener_perfil(self, email):
        """Obtener información de perfil del usuario"""
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
                
                # Agregar datos de perfil si existen
                if 'perfil' in usuarios[email]:
                    perfil_base.update(usuarios[email]['perfil'])
                
                return perfil_base
            return None
        except Exception as e:
            print(f"Error en obtener_perfil: {e}")
            return None
    
    def generar_codigo_usuario(self, email):
        """Generar código único de usuario"""
        import hashlib
        # Generar código a partir del email
        codigo_hash = hashlib.md5(email.encode()).hexdigest()[:8].upper()
        return f"OPT-{codigo_hash}"
    
    def obtener_plan_usuario(self, email, payment_manager):
        """Obtener información del plan del usuario"""
        try:
            suscripcion = payment_manager.obtener_suscripcion(email)
            if suscripcion:
                return {
                    "nombre": suscripcion['plan_nombre'],
                    "fecha_inicio": suscripcion['fecha_inicio'],
                    "fecha_fin": suscripcion['fecha_fin'],
                    "precio": suscripcion['precio'],
                    "secciones": suscripcion['secciones']
                }
            return {
                "nombre": "Gratuito",
                "fecha_inicio": datetime.now().strftime("%Y-%m-%d"),
                "fecha_fin": "Sin expiración",
                "precio": 0,
                "secciones": ["excel"]
            }
        except Exception as e:
            return {
                "nombre": "Gratuito",
                "fecha_inicio": datetime.now().strftime("%Y-%m-%d"),
                "fecha_fin": "Sin expiración",
                "precio": 0,
                "secciones": ["excel"]
            }
    def __init__(self):
        self.archivo_usuarios = "data/usuarios.json"
        self.asegurar_archivos()
    
    def asegurar_archivos(self):
        """Crear estructura de archivos"""
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
        """Validar formato de email"""
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(patron, email) is not None
    
    def registrar_usuario(self, email, password, nombre):
        """Registrar nuevo usuario con Gmail"""
        if not self.validar_email(email):
            return False, "Email inválido"
        
        if not email.endswith('@gmail.com'):
            return False, "Solo se permiten cuentas de Gmail"
        
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            
            if email in usuarios:
                return False, "El usuario ya existe"
            
            # Usuario gratuito: solo 1 sección básica
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
        """Verificar credenciales"""
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            
            if email in usuarios:
                if usuarios[email]["password"] == self.hash_password(password):
                    return True, usuarios[email]["rol"], usuarios[email]["nombre"], usuarios[email].get("secciones", [])
            return False, None, None, []
        except:
            return False, None, None, []
    
    def obtener_usuario(self, email):
        """Obtener datos de usuario"""
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            return usuarios.get(email, None)
        except:
            return None
    
    def actualizar_secciones(self, email, secciones):
        """Actualizar secciones del usuario"""
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            
            if email in usuarios:
                usuarios[email]["secciones"] = secciones
                
                with open(self.archivo_usuarios, 'w') as f:
                    json.dump(usuarios, f, indent=4)
                return True
            return False
        except:
            return False
    
    def listar_usuarios(self):
        """Listar todos los usuarios (solo master)"""
        try:
            with open(self.archivo_usuarios, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def eliminar_usuario(self, email, master_email):
        """Eliminar usuario (solo master)"""
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

    # ESTAS FUNCIONES AHORA ESTÁN CORRECTAMENTE DENTRO DE LA CLASE
    def asignar_secciones_usuario(self, email, secciones_asignadas, master_email):
        """Master asigna secciones a un usuario (sobrescribe plan gratuito)"""
        if master_email != "master@optimizo.com":
            return False, "Solo el master puede asignar secciones"
        
        try:
            with open(self.archivo_usuarios, 'r') as f:
                usuarios = json.load(f)
            
            if email in usuarios:
                # Guardar secciones asignadas manualmente
                usuarios[email]["secciones_asignadas"] = secciones_asignadas
                usuarios[email]["secciones"] = secciones_asignadas
                
                with open(self.archivo_usuarios, 'w') as f:
                    json.dump(usuarios, f, indent=4)
                return True, f"Secciones asignadas: {', '.join(secciones_asignadas)}"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, str(e)

    def obtener_secciones_usuario(self, email):
        """Obtener secciones a las que tiene acceso un usuario"""
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
        

        # auth.py - Agregar estas funciones a la clase AuthManager

    def actualizar_perfil(self, email, datos_perfil):
        """Actualizar información de perfil del usuario"""
        try:
            with open(self.archivo_usuarios, 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
            
            if email in usuarios:
                # Actualizar datos del perfil
                if 'perfil' not in usuarios[email]:
                    usuarios[email]['perfil'] = {}
                
                usuarios[email]['perfil'].update(datos_perfil)
                usuarios[email]['perfil']['ultima_actualizacion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open(self.archivo_usuarios, 'w', encoding='utf-8') as f:
                    json.dump(usuarios, f, indent=4, ensure_ascii=False)
                
                return True, "Perfil actualizado correctamente"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, str(e)
    
    def obtener_perfil(self, email):
        """Obtener información de perfil del usuario"""
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
                
                # Agregar datos de perfil si existen
                if 'perfil' in usuarios[email]:
                    perfil_base.update(usuarios[email]['perfil'])
                
                return perfil_base
            return None
        except Exception as e:
            return None
    
    def generar_codigo_usuario(self, email):
        """Generar código único de usuario"""
        import hashlib
        # Generar código a partir del email
        codigo_hash = hashlib.md5(email.encode()).hexdigest()[:8].upper()
        return f"OPT-{codigo_hash}"
    
    def obtener_plan_usuario(self, email, payment_manager):
        """Obtener información del plan del usuario"""
        suscripcion = payment_manager.obtener_suscripcion(email)
        if suscripcion:
            return {
                "nombre": suscripcion['plan_nombre'],
                "fecha_inicio": suscripcion['fecha_inicio'],
                "fecha_fin": suscripcion['fecha_fin'],
                "precio": suscripcion['precio'],
                "secciones": suscripcion['secciones']
            }
        return {
            "nombre": "Gratuito",
            "fecha_inicio": datetime.now().strftime("%Y-%m-%d"),
            "fecha_fin": "Sin expiración",
            "precio": 0,
            "secciones": ["excel"]
        }