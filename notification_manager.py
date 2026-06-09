from supabase_client import get_supabase
from datetime import datetime
import uuid

class NotificationManager:
    def __init__(self):
        self.supabase = get_supabase()

    def crear_notificacion(self, usuario_email, titulo, mensaje, tipo="info", metadata=None):
        """Inserta una notificación para un usuario específico"""
        data = {
            "id": str(uuid.uuid4()),
            "usuario_email": usuario_email,
            "titulo": titulo,
            "mensaje": mensaje,
            "tipo": tipo,
            "leido": False,
            "fecha_creacion": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        result = self.supabase.table("notificaciones").insert(data).execute()
        return result.data[0] if result.data else None

    def crear_notificacion_para_todos(self, titulo, mensaje, tipo="publicacion", metadata=None):
        """Crea una notificación para todos los usuarios (útil para publicaciones del master)"""
        usuarios = self.supabase.table("users").select("email").execute()
        if not usuarios.data:
            return
        for user in usuarios.data:
            self.crear_notificacion(user["email"], titulo, mensaje, tipo, metadata)

    def obtener_notificaciones_no_leidas(self, usuario_email):
        """Obtiene todas las notificaciones no leídas de un usuario"""
        result = self.supabase.table("notificaciones") \
            .select("*") \
            .eq("usuario_email", usuario_email) \
            .eq("leido", False) \
            .order("fecha_creacion", desc=True) \
            .execute()
        return result.data or []

    def obtener_ultimas_no_leidas(self, usuario_email, limite=10):
        """Últimas notificaciones pendientes de leer para el panel de la campana."""
        try:
            result = (
                self.supabase.table("notificaciones")
                .select("*")
                .eq("usuario_email", usuario_email)
                .eq("leido", False)
                .order("fecha_creacion", desc=True)
                .limit(limite)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error obteniendo últimas notificaciones: {e}")
            return []

    def contar_no_leidas(self, usuario_email):
        """Cuenta cuántas notificaciones no leídas tiene un usuario"""
        result = self.supabase.table("notificaciones") \
            .select("id", count="exact") \
            .eq("usuario_email", usuario_email) \
            .eq("leido", False) \
            .execute()
        return result.count or 0

    def marcar_como_leida(self, notificacion_id, usuario_email):
        """Marca una notificación como leída (solo si pertenece al usuario)"""
        result = self.supabase.table("notificaciones") \
            .update({"leido": True}) \
            .eq("id", notificacion_id) \
            .eq("usuario_email", usuario_email) \
            .execute()
        return len(result.data) > 0

    def marcar_todas_como_leidas(self, usuario_email):
        """Marca todas las notificaciones de un usuario como leídas"""
        result = self.supabase.table("notificaciones") \
            .update({"leido": True}) \
            .eq("usuario_email", usuario_email) \
            .eq("leido", False) \
            .execute()
        return True

    # ============= NUEVO MÉTODO PARA PUBLICACIONES GENERALES =============
    def obtener_ultimas_publicaciones(self, limite=10):
        """
        Obtiene las últimas publicaciones generales desde la tabla 'publicaciones'.
        Retorna una lista de diccionarios con las columnas:
        id, titulo, mensaje, seccion, categoria, fecha_creacion, creado_por
        """
        try:
            response = self.supabase.table('publicaciones')\
                .select('*')\
                .order('fecha_creacion', desc=True)\
                .limit(limite)\
                .execute()
            return response.data or []
        except Exception as e:
            print(f"Error obteniendo publicaciones: {e}")
            return []