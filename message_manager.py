<<<<<<< HEAD
# message_manager.py
from datetime import datetime
import uuid
from supabase_client import get_supabase


class MessageManager:
    def __init__(self):
        self.supabase = get_supabase()
        self.tabla = "consultas"

    def _es_consulta_pendiente(self, consulta: dict) -> bool:
        """True solo si la consulta aún no fue contestada."""
        if consulta.get("respuesta"):
            return False
        if consulta.get("respondido") is True:
            return False
        estado = (consulta.get("estado") or "").strip().lower()
        if estado in ("respondida", "respondido", "cerrada", "closed"):
            return False
        return True

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
            }
            try:
                result = (
                    self.supabase.table(self.tabla)
                    .update(update)
                    .eq("id", mensaje_id)
                    .execute()
                )
            except Exception as estado_err:
                if "estado" not in str(estado_err).lower() and "column" not in str(estado_err).lower():
                    raise
                update.pop("estado", None)
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
        """Obtiene el historial de consultas de un usuario."""
        try:
            result = (
                self.supabase.table(self.tabla)
                .select("*")
                .eq("email", email)
                .order("fecha", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo consultas del usuario: {e}")
            return []

    def contar_no_leidos(self, email):
        """Cuenta consultas del usuario que aún no tienen respuesta."""
        mensajes = self.obtener_mensajes_usuario(email)
        return len([m for m in mensajes if self._es_consulta_pendiente(m)])
=======
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
>>>>>>> d6862f9c6b4fbf4844246d3690a0754ccb992bc2
