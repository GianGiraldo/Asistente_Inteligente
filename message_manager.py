# message_manager.py
import json
import os
from datetime import datetime
import uuid

class MessageManager:
    def __init__(self):
        self.archivo_mensajes = "data/mensajes.json"
        self.asegurar_archivo()
    
    def asegurar_archivo(self):
        """Crear archivo de mensajes si no existe"""
        if not os.path.exists("data"):
            os.makedirs("data")
        
        if not os.path.exists(self.archivo_mensajes):
            with open(self.archivo_mensajes, 'w') as f:
                json.dump({}, f)
    
    def enviar_mensaje(self, email, nombre, seccion, mensaje):
        """Enviar mensaje de usuario a master"""
        try:
            with open(self.archivo_mensajes, 'r') as f:
                mensajes = json.load(f)
            
            nuevo_mensaje = {
                "id": str(uuid.uuid4())[:8],
                "email": email,
                "nombre_usuario": nombre,
                "seccion": seccion,
                "mensaje": mensaje,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "respondido": False,
                "respuesta": None,
                "respondido_por": None,
                "fecha_respuesta": None
            }
            
            # Guardar mensaje
            if email not in mensajes:
                mensajes[email] = []
            
            mensajes[email].append(nuevo_mensaje)
            
            with open(self.archivo_mensajes, 'w') as f:
                json.dump(mensajes, f, indent=4)
            
            return True, "Mensaje enviado"
        except Exception as e:
            return False, str(e)
    
    def responder_mensaje(self, mensaje_id, respuesta, master_email):
        """Responder a un mensaje específico"""
        try:
            with open(self.archivo_mensajes, 'r') as f:
                mensajes = json.load(f)
            
            # Buscar el mensaje por ID
            for email, lista in mensajes.items():
                for i, msg in enumerate(lista):
                    if msg["id"] == mensaje_id:
                        mensajes[email][i]["respondido"] = True
                        mensajes[email][i]["respuesta"] = respuesta
                        mensajes[email][i]["respondido_por"] = master_email
                        mensajes[email][i]["fecha_respuesta"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        with open(self.archivo_mensajes, 'w') as f:
                            json.dump(mensajes, f, indent=4)
                        
                        return True
            
            return False
        except Exception as e:
            return False
    
    def obtener_mensajes_para_master(self, respondidos=False):
        """Obtener todos los mensajes para el master (filtrado por respondidos)"""
        try:
            with open(self.archivo_mensajes, 'r') as f:
                mensajes = json.load(f)
            
            todos = []
            for email, lista in mensajes.items():
                for msg in lista:
                    if msg["respondido"] == respondidos:
                        todos.append(msg)
            
            # Ordenar por fecha (más recientes primero)
            todos.sort(key=lambda x: x["fecha"], reverse=True)
            return todos
        except:
            return []
    
    def obtener_mensajes_usuario(self, email):
        """Obtener mensajes de un usuario específico"""
        try:
            with open(self.archivo_mensajes, 'r') as f:
                mensajes = json.load(f)
            
            if email in mensajes:
                # Ordenar por fecha (más recientes primero)
                return sorted(mensajes[email], key=lambda x: x["fecha"], reverse=True)
            return []
        except:
            return []
    
    def contar_no_leidos(self, email):
        """Contar mensajes no respondidos de un usuario"""
        mensajes = self.obtener_mensajes_usuario(email)
        no_respondidos = [m for m in mensajes if not m.get("respondido", False)]
        return len(no_respondidos)