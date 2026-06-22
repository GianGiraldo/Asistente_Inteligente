# auth.py — Autenticación Google OAuth + Supabase (identidad única Gmail)
import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from payment_manager import PaymentManager
from supabase_client import get_supabase

SESSION_KEYS = (
    "autenticado", "usuario", "rol", "nombre", "secciones", "avatar_url",
    "access_token", "refresh_token", "session_string", "acceso_pagado",
    "login_time", "menu_principal", "seccion_activa", "categoria_inicio",
    "modulos_permitidos", "secciones_staff", "puede_publicar",
    "velox_setup_email",
)

SETUP_PASSWORD_REQUIRED = "__VELOX_SETUP_PASSWORD__"
VISTA_LOGIN = "login"
VISTA_RECUPERAR_PASSWORD = "recuperar_password"
# Plantilla recomendada en Supabase → Authentication → Email Templates → Reset password:
# <a href="{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=recovery">Restablecer contraseña</a>
PLANTILLA_ENLACE_RECUPERACION_SUPABASE = (
    '{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=recovery'
)


class AuthManager:
    """Gestor OAuth Google vía Supabase Auth."""

    MASTER_EMAIL = "gianpiergiraldo@gmail.com"
    ROLES_ETIQUETAS = ["Usuario", "Administrador", "Master"]
    _ROL_ETIQUETA_A_DB = {
        "Usuario": "usuario",
        "Administrador": "administrador",
        "Master": "master",
    }
    _ROL_DB_A_ETIQUETA = {v: k for k, v in _ROL_ETIQUETA_A_DB.items()}

    MODULO_INICIO = "🏠 Inicio"
    MODULO_DOCUMENTOS = "📁 Mis Documentos"
    MODULO_GESTION_USUARIOS = "👥 Gestión Usuarios"
    MODULO_COBRANZAS = "💳 Cobranzas"
    MODULO_CONSULTAS = "📬 Consultas"
    MODULO_CONFIGURACION = "⚙️ Configuración"
    MODULOS_SOLO_MASTER = frozenset({MODULO_COBRANZAS, MODULO_CONFIGURACION})
    MODULOS_ADMIN_DEFAULT = [
        MODULO_INICIO,
        MODULO_DOCUMENTOS,
        MODULO_GESTION_USUARIOS,
        MODULO_CONSULTAS,
    ]
    MODULOS_CONFIGURABLES_ADMIN = list(MODULOS_ADMIN_DEFAULT)

    def __init__(self):
        self.supabase = get_supabase()
        self.payments = PaymentManager()

    @classmethod
    def normalizar_rol(cls, rol: Optional[str]) -> str:
        return (rol or "usuario").strip().lower()

    @classmethod
    def es_rol_master(cls, rol: Optional[str]) -> bool:
        return cls.normalizar_rol(rol) == "master"

    @classmethod
    def es_rol_administrador(cls, rol: Optional[str]) -> bool:
        return cls.normalizar_rol(rol) == "administrador"

    @classmethod
    def es_staff(cls, rol: Optional[str]) -> bool:
        return cls.normalizar_rol(rol) in ("master", "administrador")

    @classmethod
    def etiqueta_rol(cls, rol: Optional[str]) -> str:
        return cls._ROL_DB_A_ETIQUETA.get(cls.normalizar_rol(rol), "Usuario")

    @classmethod
    def rol_desde_etiqueta(cls, etiqueta: str) -> str:
        return cls._ROL_ETIQUETA_A_DB.get(etiqueta, "usuario")

    @classmethod
    def permisos_admin_desde_usuario(cls, user: Dict[str, Any]) -> Dict[str, Any]:
        perfil = user.get("perfil") or {}
        raw = perfil.get("permisos_admin") or {}
        modulos = [
            m for m in (raw.get("modulos") or cls.MODULOS_ADMIN_DEFAULT)
            if m in cls.MODULOS_CONFIGURABLES_ADMIN
        ]
        if not modulos:
            modulos = list(cls.MODULOS_ADMIN_DEFAULT)
        secciones = [s for s in (raw.get("secciones") or []) if isinstance(s, str) and s.strip()]
        return {
            "modulos": modulos,
            "secciones": secciones,
            "puede_publicar": bool(raw.get("puede_publicar", False)),
        }

    def _aplicar_permisos_a_sesion(self, user: Dict[str, Any]) -> None:
        rol = self.normalizar_rol(user.get("rol"))
        if self.es_rol_master(rol):
            st.session_state.pop("modulos_permitidos", None)
            st.session_state.pop("secciones_staff", None)
            st.session_state.pop("puede_publicar", None)
            return
        if self.es_rol_administrador(rol):
            permisos = self.permisos_admin_desde_usuario(user)
            st.session_state["modulos_permitidos"] = permisos["modulos"]
            st.session_state["secciones_staff"] = permisos["secciones"]
            st.session_state["puede_publicar"] = permisos["puede_publicar"]
            return
        st.session_state.pop("modulos_permitidos", None)
        st.session_state.pop("secciones_staff", None)
        st.session_state.pop("puede_publicar", None)

    def puede_acceder_modulo(
        self, modulo: str, rol: Optional[str], modulos_permitidos: Optional[List[str]] = None
    ) -> bool:
        rol_norm = self.normalizar_rol(rol)
        if self.es_rol_master(rol_norm):
            return True
        if modulo in self.MODULOS_SOLO_MASTER:
            return False
        if self.es_rol_administrador(rol_norm):
            permitidos = modulos_permitidos or self.MODULOS_ADMIN_DEFAULT
            return modulo in permitidos
        return modulo in {self.MODULO_INICIO, self.MODULO_DOCUMENTOS, self.MODULO_CONSULTAS, "👤 Mi Perfil"}

    def filtrar_menu_staff(
        self, menu_master: List[tuple], rol: Optional[str], modulos_permitidos: Optional[List[str]] = None
    ) -> List[tuple]:
        rol_norm = self.normalizar_rol(rol)
        if self.es_rol_master(rol_norm):
            return menu_master
        if self.es_rol_administrador(rol_norm):
            permitidos = set(modulos_permitidos or self.MODULOS_ADMIN_DEFAULT)
            return [item for item in menu_master if item[2] in permitidos]
        return []

    def guardar_permisos_administrador(
        self,
        email_admin: str,
        modulos: List[str],
        secciones: List[str],
        actor_email: str,
        puede_publicar: bool = False,
    ) -> Tuple[bool, str]:
        if not self._actor_es_master(actor_email):
            return False, "Solo un Master puede configurar permisos de administradores."

        email_norm = (email_admin or "").strip().lower()
        if not email_norm:
            return False, "Correo de administrador inválido."

        modulos_validos = [
            m for m in modulos if m in self.MODULOS_CONFIGURABLES_ADMIN and m not in self.MODULOS_SOLO_MASTER
        ]
        if not modulos_validos:
            return False, "Debes seleccionar al menos un módulo permitido."

        try:
            result = self.supabase.table("users").select("rol, perfil").eq("email", email_norm).execute()
            if not result.data:
                return False, "Usuario no encontrado."
            if not self.es_rol_administrador(result.data[0].get("rol")):
                return False, "El usuario seleccionado no tiene rol Administrador."

            perfil = result.data[0].get("perfil") or {}
            perfil["permisos_admin"] = {
                "modulos": modulos_validos,
                "secciones": [s for s in secciones if s],
                "puede_publicar": puede_publicar,
            }
            update = self.supabase.table("users").update({"perfil": perfil}).eq("email", email_norm).execute()
            if not update.data:
                return False, "No se pudieron guardar los permisos."

            if email_norm == (actor_email or "").strip().lower():
                st.session_state["modulos_permitidos"] = modulos_validos
                st.session_state["secciones_staff"] = perfil["permisos_admin"]["secciones"]
                st.session_state["puede_publicar"] = puede_publicar

            return True, f"Permisos actualizados para {email_norm}."
        except Exception as e:
            return False, f"Error al guardar permisos: {self._format_error(e)}"

    def _actor_puede_gestionar_usuarios(self, actor_email: str) -> bool:
        if self._actor_es_master(actor_email):
            return True
        try:
            result = self.supabase.table("users").select("rol, perfil").eq("email", actor_email).execute()
            if not result.data:
                return False
            user = result.data[0]
            if not self.es_rol_administrador(user.get("rol")):
                return False
            permisos = self.permisos_admin_desde_usuario(user)
            return self.MODULO_GESTION_USUARIOS in permisos["modulos"]
        except Exception:
            return False

    @staticmethod
    def _format_error(exc: Exception) -> str:
        return str(getattr(exc, "message", None) or exc)

    @staticmethod
    def _ruta_secrets_toml() -> str:
        return os.path.join(os.getcwd(), ".streamlit", "secrets.toml")

    @staticmethod
    def _secciones_secrets() -> List[str]:
        try:
            return list(st.secrets.keys())
        except Exception:
            return []

    @staticmethod
    def _valor_seccion(seccion: str, clave: str) -> str:
        try:
            bloque = st.secrets[seccion]
            valor = bloque[clave] if hasattr(bloque, "__getitem__") else getattr(bloque, clave, None)
            return str(valor or "").strip()
        except (KeyError, TypeError, AttributeError):
            return ""

    def _obtener_credenciales_google(self) -> Tuple[str, str]:
        return (
            self._valor_seccion("google_oauth", "client_id"),
            self._valor_seccion("google_oauth", "client_secret"),
        )

    def obtener_redirect_url(self) -> str:
        """URL pública donde Supabase devuelve ?code= (debe estar en Redirect URLs)."""
        return self.resolver_base_url_app()

    @staticmethod
    def _normalizar_url_base(url: str) -> str:
        return (url or "").strip().rstrip("/")

    @staticmethod
    def _url_es_localhost(url: str) -> bool:
        u = (url or "").lower()
        return u.startswith("http://localhost") or u.startswith("http://127.0.0.1")

    @staticmethod
    def _base_url_desde_entorno() -> str:
        for var in ("VELOX_BASE_URL", "STREAMLIT_APP_BASE_URL", "APP_BASE_URL"):
            valor = (os.getenv(var) or "").strip()
            if valor:
                return AuthManager._normalizar_url_base(valor)
        return ""

    @staticmethod
    def _base_url_desde_contexto_streamlit() -> str:
        """Inferir URL en Streamlit Cloud u otros despliegues desde headers HTTP."""
        try:
            ctx = getattr(st, "context", None)
            headers = getattr(ctx, "headers", None) if ctx is not None else None
            if not headers:
                return ""
            host = (headers.get("Host") or headers.get("host") or "").strip()
            if not host:
                return ""
            proto = (
                headers.get("X-Forwarded-Proto")
                or headers.get("x-forwarded-proto")
                or "https"
            ).strip()
            return AuthManager._normalizar_url_base(f"{proto}://{host}")
        except Exception:
            return ""

    @staticmethod
    def _host_remoto_produccion() -> bool:
        try:
            ctx = getattr(st, "context", None)
            headers = getattr(ctx, "headers", None) if ctx is not None else None
            if not headers:
                return False
            host = (headers.get("Host") or headers.get("host") or "").lower()
            return bool(host) and host not in ("localhost", "127.0.0.1") and not host.startswith(
                "localhost:"
            )
        except Exception:
            return False

    def resolver_base_url_app(self) -> str:
        """
        URL base pública de la app (redirect_to de Supabase OAuth).
        Jerarquía: secrets → variables de entorno → headers Streamlit → localhost.
        """
        en_produccion = self._host_remoto_produccion()

        try:
            app_secrets = st.secrets.get("app", {})
        except Exception:
            app_secrets = {}

        for key in ("base_url", "redirect_url"):
            raw = ""
            try:
                if hasattr(app_secrets, "get"):
                    raw = app_secrets.get(key) or ""
                else:
                    raw = getattr(app_secrets, key, "") or ""
            except (KeyError, TypeError, AttributeError):
                raw = self._valor_seccion("app", key)
            url = self._normalizar_url_base(str(raw or ""))
            if not url:
                continue
            if en_produccion and self._url_es_localhost(url):
                continue
            return url

        env_url = self._base_url_desde_entorno()
        if env_url and not (en_produccion and self._url_es_localhost(env_url)):
            return env_url

        ctx_url = self._base_url_desde_contexto_streamlit()
        if ctx_url:
            return ctx_url

        return "http://localhost:8501"

    def _detectar_base_url_app(self) -> str:
        """Alias interno; usar resolver_base_url_app()."""
        return self.resolver_base_url_app()

    def _supabase_oauth_callback_url(self) -> str:
        """URI que Google debe tener registrada (callback de Supabase, no la app)."""
        supabase_base = self._normalizar_url_base(self._valor_seccion("supabase", "url"))
        if not supabase_base:
            return ""
        return f"{supabase_base}/auth/v1/callback"

    def obtener_diagnostico_oauth(self) -> Dict[str, str]:
        """Metadatos útiles para depurar OAuth (sin exponer secretos)."""
        client_id = self._valor_seccion("google_oauth", "client_id")
        redirect_to = self.obtener_redirect_url()
        return {
            "redirect_to_activo": redirect_to,
            "google_callback_registrar_en_cloud": self._supabase_oauth_callback_url() or "(vacío)",
            "supabase_redirect_urls_debe_incluir": redirect_to,
            "secrets_app_base_url": self._valor_seccion("app", "base_url") or "(vacío)",
            "secrets_app_redirect_url": self._valor_seccion("app", "redirect_url") or "(vacío)",
            "env_VELOX_BASE_URL": os.getenv("VELOX_BASE_URL") or "(vacío)",
            "contexto_streamlit": self._base_url_desde_contexto_streamlit() or "(vacío)",
            "supabase_url": self._valor_seccion("supabase", "url") or "(vacío)",
            "google_client_id_secrets": "configurado" if client_id else "no requerido p/ Supabase OAuth",
            "oauth_redirect_cache": str(st.session_state.get("google_oauth_redirect") or "(vacío)"),
        }

    @staticmethod
    def limpiar_estado_oauth() -> None:
        for key in (
            "google_oauth_url",
            "google_oauth_redirect",
            "google_oauth_error",
            "google_oauth_force_refresh",
            "oauth_last_code",
        ):
            st.session_state.pop(key, None)

    def _validar_precondiciones_oauth(self) -> Tuple[bool, str]:
        if not self._valor_seccion("supabase", "url"):
            return False, "Falta [supabase].url en .streamlit/secrets.toml (o Secrets de Streamlit Cloud)."
        if not self._valor_seccion("supabase", "key"):
            return False, "Falta [supabase].key en .streamlit/secrets.toml (o Secrets de Streamlit Cloud)."
        redirect_to = self.obtener_redirect_url()
        if not redirect_to.startswith("http"):
            return (
                False,
                "URL base inválida. Define [app].base_url en secrets o VELOX_BASE_URL en el entorno.",
            )
        if "supabase.co/auth/v1/callback" in redirect_to:
            return (
                False,
                "redirect_to apunta al callback de Supabase; debe ser la URL pública de tu app "
                "(p. ej. https://veloxperu.streamlit.app). "
                "En Google Cloud registra el callback de Supabase, no la URL de Streamlit.",
            )
        if self._host_remoto_produccion() and self._url_es_localhost(redirect_to):
            return (
                False,
                "redirect_to es localhost en producción. Define [app].base_url en Streamlit Cloud Secrets.",
            )
        return True, redirect_to

    @staticmethod
    def _query_param(key: str) -> Optional[str]:
        """Normaliza st.query_params (str o list) a un único valor."""
        val = st.query_params.get(key)
        if val is None:
            return None
        if isinstance(val, list):
            return (val[0] or "").strip() if val else None
        return str(val).strip() if val else None

    @staticmethod
    def _es_flujo_recuperacion(
        auth_type: Optional[str],
        access: Optional[str],
        refresh: Optional[str],
        code: Optional[str],
    ) -> bool:
        if auth_type == "recovery":
            return True
        # Retorno implícito (#access_token) sin OAuth code: flujo de recuperación veloX
        if access and refresh and not code and auth_type in (None, "", "recovery"):
            return True
        return False

    def sincronizar_vista_auth(self) -> None:
        """Mantiene vista_actual alineada con password_recovery_mode."""
        if st.session_state.get("password_recovery_mode"):
            st.session_state["vista_actual"] = VISTA_RECUPERAR_PASSWORD
        elif not st.session_state.get("autenticado"):
            if st.session_state.get("vista_actual") == VISTA_RECUPERAR_PASSWORD:
                st.session_state["vista_actual"] = VISTA_LOGIN

    def inicializar_estado_auth(self) -> None:
        """Estado mínimo de auth antes de renderizar cualquier pantalla."""
        if "autenticado" not in st.session_state:
            st.session_state["autenticado"] = False
        if "acceso_pagado" not in st.session_state:
            st.session_state["acceso_pagado"] = False
        if "vista_actual" not in st.session_state:
            st.session_state["vista_actual"] = VISTA_LOGIN
        if st.session_state.get("password_recovery_mode"):
            st.session_state["vista_actual"] = VISTA_RECUPERAR_PASSWORD

    def en_modo_recuperacion_password(self) -> bool:
        return bool(
            st.session_state.get("password_recovery_mode")
            or st.session_state.get("vista_actual") == VISTA_RECUPERAR_PASSWORD
        )

    def hay_callback_auth_en_url(self) -> bool:
        """Indica si la URL trae parámetros de retorno OAuth o recuperación."""
        if self._query_param("code") or self._query_param("error"):
            return True
        if self._query_param("access_token"):
            return True
        token_hash = self._query_param("token_hash")
        auth_type = self._query_param("type")
        return bool(token_hash and auth_type == "recovery")

    @staticmethod
    def _limpiar_parametros_oauth() -> None:
        for key in (
            "code",
            "error",
            "error_description",
            "access_token",
            "refresh_token",
            "state",
            "type",
            "token_hash",
        ):
            if key in st.query_params:
                del st.query_params[key]

    @staticmethod
    def _es_error_pkce(exc: Exception) -> bool:
        texto = AuthManager._format_error(exc).lower()
        return any(
            fragmento in texto
            for fragmento in (
                "code challenge",
                "code verifier",
                "pkce",
                "verifier",
            )
        )

    def ensure_google_oauth_url(self, force_refresh: bool = False) -> Optional[str]:
        """
        URL de autorización Google vía Supabase Auth (PKCE).
        La URL base (redirect_to) se resuelve dinámicamente; no hay dominios hardcodeados.
        """
        redirect_actual = self.obtener_redirect_url()
        cached_redirect = st.session_state.get("google_oauth_redirect")
        cached_url = st.session_state.get("google_oauth_url")
        if (
            not force_refresh
            and cached_url
            and cached_redirect == redirect_actual
        ):
            return cached_url

        if force_refresh or cached_redirect != redirect_actual:
            self.limpiar_estado_oauth()

        url = self._generar_google_oauth_url()
        if url:
            st.session_state["google_oauth_url"] = url
            st.session_state["google_oauth_redirect"] = redirect_actual
            st.session_state.pop("google_oauth_error", None)
        return url

    def get_google_oauth_url(self) -> Optional[str]:
        """Retorna URL OAuth cacheada o la genera si aún no existe."""
        return self.ensure_google_oauth_url()

    def _generar_google_oauth_url(self) -> Optional[str]:
        """
        Genera URL de Supabase Auth (?provider=google).

        redirect_to = URL de la app (donde Supabase devuelve ?code=).
        Google Cloud debe registrar el callback de Supabase (.../auth/v1/callback), no la app.
        """
        ok, redirect_or_msg = self._validar_precondiciones_oauth()
        if not ok:
            st.session_state["google_oauth_error"] = redirect_or_msg
            print(f"OAuth precondiciones: {redirect_or_msg}")
            return None

        redirect_to = redirect_or_msg
        try:
            print(
                f"OAuth Supabase redirect_to (app): {redirect_to} | "
                f"Google callback esperado: {self._supabase_oauth_callback_url()}"
            )
            response = self.supabase.auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {
                        "redirect_to": redirect_to,
                        "query_params": {
                            "access_type": "offline",
                            "prompt": "consent",
                        },
                        "scopes": "email profile openid",
                    },
                }
            )
            url = getattr(response, "url", None) or (
                response.get("url") if isinstance(response, dict) else None
            )
            if not url:
                st.session_state["google_oauth_error"] = (
                    "Supabase no devolvió URL de autorización. "
                    f"En Supabase → Authentication → URL Configuration, agrega Redirect URL: "
                    f"{redirect_to}"
                )
            return url
        except Exception as e:
            err = self._format_error(e)
            print(f"Error generando URL OAuth Google: {err}")
            st.session_state["google_oauth_error"] = (
                f"No se pudo generar la URL OAuth: {err}. "
                f"redirect_to usado: {redirect_to}. "
                "Verifica Site URL y Redirect URLs en Supabase, y que Google esté habilitado "
                "en Supabase → Authentication → Providers → Google."
            )
            return None

    def _persistir_sesion_supabase(self, session) -> None:
        if not session:
            return
        access = getattr(session, "access_token", None) or session.get("access_token")
        refresh = getattr(session, "refresh_token", None) or session.get("refresh_token")
        if access and refresh:
            try:
                self.supabase.auth.set_session(access, refresh)
            except Exception as e:
                print(f"Aviso set_session: {self._format_error(e)}")
        st.session_state["access_token"] = access
        st.session_state["refresh_token"] = refresh
        st.session_state["session_string"] = json.dumps(
            {"access_token": access, "refresh_token": refresh},
            ensure_ascii=False,
        )

    def _aplicar_usuario_sesion(self, auth_user) -> Tuple[bool, str]:
        """Sincroniza perfil OAuth con tabla users y session_state."""
        try:
            email = (auth_user.email or "").strip().lower()
            if not email:
                return False, "No se pudo obtener el correo verificado de Google"

            meta = auth_user.user_metadata or {}
            nombre = (
                meta.get("full_name")
                or meta.get("name")
                or (email.split("@")[0].replace(".", " ").title())
            )
            avatar = meta.get("avatar_url") or meta.get("picture")

            db_user = self._sincronizar_usuario_google(email, nombre, avatar)
            acceso = self.payments.usuario_tiene_acceso(db_user)

            st.session_state.update(
                {
                    "autenticado": True,
                    "usuario": email,
                    "nombre": db_user.get("nombre", nombre),
                    "rol": db_user.get("rol", "usuario"),
                    "secciones": db_user.get("secciones") or ["excel"],
                    "avatar_url": avatar,
                    "acceso_pagado": acceso,
                    "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "menu_principal": "🏠 Inicio",
                    "seccion_activa": "inicio",
                }
            )
            self._aplicar_permisos_a_sesion(db_user)
            if not acceso and not self.es_staff(db_user.get("rol")):
                intent = st.session_state.get("oauth_intent", "register")
                if intent == "login":
                    st.session_state["welcome_active_tab"] = 0
                    st.session_state["oauth_login_denied_msg"] = (
                        "⏳ Tu acceso aún no está activo. Completa el registro y pago, "
                        "o espera la aprobación del administrador."
                    )
                else:
                    st.session_state["welcome_active_tab"] = 1
            else:
                st.session_state.pop("oauth_login_denied_msg", None)
                if st.session_state.get("oauth_intent") == "register":
                    st.session_state["welcome_active_tab"] = 1
                    st.session_state["registro_en_progreso"] = True
            return True, "Sesión iniciada"
        except Exception as e:
            return False, f"Error aplicando sesión: {self._format_error(e)}"

    def _verificar_password_usuario(self, password: str, user: Dict[str, Any]) -> bool:
        stored_hash = user.get("password")
        salt = user.get("password_salt")
        if not stored_hash or not salt:
            return False
        computed, _ = self.payments._hash_password(password, salt)
        return secrets.compare_digest(computed, stored_hash)

    @staticmethod
    def _perfil_usuario(user: Dict[str, Any]) -> Dict[str, Any]:
        perfil = user.get("perfil")
        return dict(perfil) if isinstance(perfil, dict) else {}

    @staticmethod
    def _primera_fila(result) -> Optional[Dict[str, Any]]:
        """Extrae la primera fila de una respuesta Supabase sin KeyError/IndexError."""
        data = getattr(result, "data", None)
        if not data:
            return None
        if isinstance(data, list):
            return data[0] if data else None
        if isinstance(data, dict) and any(k in data for k in ("email", "id", "rol")):
            return data
        return None

    @staticmethod
    def _nombre_desde_email(email: str) -> str:
        local = (email or "").split("@")[0]
        return local.replace(".", " ").replace("_", " ").title() or "Usuario"

    def _obtener_usuario_db(self, email: str) -> Optional[Dict[str, Any]]:
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return None
        try:
            result = self.supabase.table("users").select("*").eq("email", email_norm).execute()
            return self._primera_fila(result)
        except Exception as e:
            print(f"Error obteniendo usuario {email_norm}: {self._format_error(e)}")
            return None

    def _crear_registro_usuario_inicial(
        self,
        email: str,
        nombre: Optional[str] = None,
        avatar: Optional[str] = None,
        auth_provider: Optional[str] = "google",
    ) -> Dict[str, Any]:
        """Inserta un usuario nuevo en public.users con valores por defecto seguros."""
        email_norm = (email or "").strip().lower()
        nombre_final = (nombre or self._nombre_desde_email(email_norm)).strip()
        perfil: Dict[str, Any] = {
            "velox_password_configured": False,
            "velox_password_temp": True,
        }
        if auth_provider:
            perfil["auth_provider"] = auth_provider
        if avatar:
            perfil["avatar_url"] = avatar

        es_master = email_norm == self.MASTER_EMAIL
        pw_hash, salt = self._password_temporal_oauth(email_norm)
        nuevo = {
            "email": email_norm,
            "password": pw_hash,
            "password_salt": salt,
            "nombre": nombre_final,
            "rol": "master" if es_master else "usuario",
            "secciones": list(SECCIONES_DEFAULT()),
            "creado": datetime.now().isoformat(),
            "activo": es_master,
            "pago_confirmado": es_master,
            "perfil": perfil,
        }
        try:
            insert = self.supabase.table("users").insert(nuevo).execute()
            row = self._primera_fila(insert)
            if row:
                return row
        except Exception as e:
            texto = self._format_error(e).lower()
            if not any(fragmento in texto for fragmento in ("duplicate", "unique", "already exists")):
                print(f"Error creando usuario {email_norm}: {self._format_error(e)}")

        existente = self._obtener_usuario_db(email_norm)
        return existente if existente else nuevo

    def _asegurar_usuario_db(
        self,
        email: str,
        nombre: Optional[str] = None,
        avatar: Optional[str] = None,
        auth_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Obtiene el registro en users o lo crea en caliente si aún no existe."""
        email_norm = (email or "").strip().lower()
        user = self._obtener_usuario_db(email_norm)
        if user:
            return user
        return self._crear_registro_usuario_inicial(
            email_norm,
            nombre=nombre,
            avatar=avatar,
            auth_provider=auth_provider or "google",
        )

    def requiere_configurar_password_velox(self, user: Dict[str, Any]) -> bool:
        """True si la cuenta aún no tiene contraseña definitiva veloX."""
        perfil = self._perfil_usuario(user)
        if perfil.get("velox_password_configured"):
            return False
        if perfil.get("velox_password_temp"):
            return True
        stored_hash = user.get("password")
        salt = user.get("password_salt")
        if not stored_hash or not salt:
            return True
        if perfil.get("auth_provider") == "google":
            return True
        return False

    def _intentar_supabase_auth_password(self, email: str, password: str) -> bool:
        try:
            res = self.supabase.auth.sign_in_with_password({"email": email, "password": password})
            session = getattr(res, "session", None) or (
                res.get("session") if isinstance(res, dict) else None
            )
            if session:
                self._persistir_sesion_supabase(session)
                return True
        except Exception as e:
            print(f"Supabase Auth (email/contraseña): {self._format_error(e)}")
        return False

    def _registrar_password_supabase_auth(self, email: str, password: str) -> None:
        """Puente aislado: crea credencial en Supabase Auth sin tocar activo/rol/pago."""
        try:
            self.supabase.auth.sign_up({"email": email, "password": password})
        except Exception as e:
            texto = self._format_error(e).lower()
            if any(fragmento in texto for fragmento in ("already", "registered", "exists", "duplicate")):
                return
            print(f"Aviso sign_up Supabase Auth: {self._format_error(e)}")

    def _password_temporal_oauth(self, email: str) -> Tuple[str, str]:
        """Placeholder hasheado para cumplir NOT NULL hasta el Paso 3 del registro."""
        raw = f"temp_veloX_{secrets.token_urlsafe(24)}_{hashlib.sha256(email.encode()).hexdigest()[:8]}"
        pw_hash, salt = self.payments._hash_password(raw)
        return pw_hash, salt

    def _persistir_password_velox(
        self, email_norm: str, password: str, user: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Actualiza solo hash de contraseña y perfil. No toca activo/rol/pago."""
        pw_hash, salt = self.payments._hash_password(password)
        perfil = self._perfil_usuario(user)
        perfil["velox_password_configured"] = True
        perfil["velox_password_configured_at"] = datetime.now().isoformat()
        perfil["velox_password_temp"] = False

        update_data = {
            "password": pw_hash,
            "password_salt": salt,
            "perfil": perfil,
        }
        updated = (
            self.supabase.table("users")
            .update(update_data)
            .eq("email", email_norm)
            .execute()
        )
        if not updated.data:
            return False, "No se pudo guardar la contraseña. Intenta de nuevo."

        self._registrar_password_supabase_auth(email_norm, password)
        return True, "Contraseña guardada correctamente."

    def guardar_password_registro(
        self,
        email: str,
        password: str,
        confirmar_password: str,
        sesion_email: str,
    ) -> Tuple[bool, str]:
        """Paso 3 del registro: guarda contraseña sin alterar activo/rol/pago existentes."""
        email_norm = (email or "").strip().lower()
        sesion_norm = (sesion_email or "").strip().lower()
        if not email_norm or email_norm != sesion_norm:
            return False, "El correo no coincide con tu sesión verificada."
        if password != confirmar_password:
            return False, "Las contraseñas no coinciden"
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres"

        try:
            user = self._obtener_usuario_db(email_norm)
            if not user:
                user = self._asegurar_usuario_db(
                    email_norm,
                    auth_provider="google",
                )
            if not self.requiere_configurar_password_velox(user):
                return True, "Tu contraseña veloX ya estaba configurada."

            return self._persistir_password_velox(email_norm, password, user)
        except Exception as e:
            return False, f"Error al guardar contraseña: {self._format_error(e)}"

    def configurar_password_velox(
        self, email: str, password: str, confirmar_password: str
    ) -> Tuple[bool, str]:
        """Guarda contraseña veloX (hash local + Supabase Auth). No altera activo/rol/pago."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return False, "Correo inválido"
        if password != confirmar_password:
            return False, "Las contraseñas no coinciden"
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres"

        try:
            user = self._obtener_usuario_db(email_norm)
            if not user:
                return False, "No encontramos tu cuenta. Verifica el correo o contacta soporte."

            puede, msg = self._usuario_puede_ingresar_clasico(user)
            if not puede:
                return False, msg

            if not self.requiere_configurar_password_velox(user):
                return False, "Tu contraseña veloX ya está configurada. Inicia sesión con ella."

            ok_save, msg_save = self._persistir_password_velox(email_norm, password, user)
            if not ok_save:
                return False, msg_save

            user_actualizado = self._obtener_usuario_db(email_norm) or user
            ok, msg_aplicar = self._aplicar_usuario_db(user_actualizado)
            if ok:
                st.session_state.pop("velox_setup_email", None)
            return ok, (
                "Contraseña configurada. Bienvenido a veloX."
                if ok
                else f"Contraseña guardada, pero hubo un problema al iniciar sesión: {msg_aplicar}"
            )
        except Exception as e:
            return False, f"Error al configurar contraseña: {self._format_error(e)}"

    def _aplicar_usuario_db(
        self, user: Dict[str, Any], avatar: Optional[str] = None
    ) -> Tuple[bool, str]:
        email = (user.get("email") or "").strip().lower()
        if not email:
            return False, "Usuario inválido"

        perfil = user.get("perfil") or {}
        if not isinstance(perfil, dict):
            perfil = {}

        pago_confirmado = bool(user.get("pago_confirmado", False))
        activo = bool(user.get("activo", False))

        try:
            res_pagos = (
                self.supabase.table("users")
                .select("pago_confirmado, activo")
                .eq("email", email)
                .execute()
            )
            info_pago = self._primera_fila(res_pagos) or {
                "pago_confirmado": pago_confirmado,
                "activo": activo,
            }
            pago_confirmado = bool(info_pago.get("pago_confirmado", pago_confirmado))
            activo = bool(info_pago.get("activo", activo))
        except Exception as e:
            print(f"Aviso refrescando pago para {email}: {self._format_error(e)}")

        user_para_acceso = {
            **user,
            "pago_confirmado": pago_confirmado,
            "activo": activo,
        }
        acceso = self.payments.usuario_tiene_acceso(user_para_acceso)
        st.session_state.update(
            {
                "autenticado": True,
                "usuario": email,
                "nombre": user.get("nombre", email.split("@")[0]),
                "rol": user.get("rol", "usuario"),
                "secciones": user.get("secciones") or ["excel"],
                "avatar_url": avatar or perfil.get("avatar_url"),
                "acceso_pagado": acceso,
                "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "menu_principal": "🏠 Inicio",
                "seccion_activa": "inicio",
            }
        )
        self._aplicar_permisos_a_sesion(user_para_acceso)
        return True, "Sesión iniciada"

    def _usuario_puede_ingresar_clasico(self, user: Dict[str, Any]) -> Tuple[bool, str]:
        """Master o usuario con activo=true y pago_confirmado/habilitado=true."""
        rol = self.normalizar_rol(user.get("rol"))
        if self.es_rol_master(rol):
            return True, ""
        activo = bool(user.get("activo"))
        pago_ok = bool(user.get("pago_confirmado"))
        habilitado = user.get("habilitado")
        if habilitado is not None:
            pago_ok = pago_ok or bool(habilitado)
        if activo and pago_ok:
            return True, ""
        return False, (
            "⏳ Tu acceso está en proceso de verificación. "
            "El administrador revisará tu pago y te habilitará pronto."
        )

    def iniciar_sesion_velox(self, email: str, password: str) -> Tuple[bool, str]:
        """Login híbrido: Supabase Auth + hash local. Respeta activo/pago existentes."""
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return False, "El correo electrónico es obligatorio"

        try:
            user = self._obtener_usuario_db(email_norm)
            autenticado_supabase = False
            if password:
                autenticado_supabase = self._intentar_supabase_auth_password(
                    email_norm, password
                )

            if not user and autenticado_supabase:
                user = self._asegurar_usuario_db(
                    email_norm,
                    auth_provider="email",
                )

            if not user:
                return False, "Correo o contraseña incorrectos"

            puede, msg = self._usuario_puede_ingresar_clasico(user)
            if not puede:
                return False, msg

            if self.requiere_configurar_password_velox(user):
                st.session_state["velox_setup_email"] = email_norm
                return False, SETUP_PASSWORD_REQUIRED

            if not password:
                return False, "La contraseña es obligatoria"

            autenticado_local = self._verificar_password_usuario(password, user)
            if not autenticado_supabase and not autenticado_local:
                return False, "Correo o contraseña incorrectos"

            return self._aplicar_usuario_db(user)
        except Exception as e:
            return False, f"Error al iniciar sesión: {self._format_error(e)}"

    def iniciar_sesion_clasico(self, email: str, password: str) -> Tuple[bool, str]:
        """Alias retrocompatible del login email/contraseña veloX."""
        return self.iniciar_sesion_velox(email, password)

    def _mensaje_error_recuperacion_password(self, exc: Exception) -> str:
        texto = self._format_error(exc).lower()
        if "rate limit" in texto or "too many requests" in texto:
            return (
                "Supabase bloqueó el envío temporalmente por límite de correos "
                "(demasiados intentos seguidos). Espera unos minutos e inténtalo de nuevo. "
                "Si ya recibiste un enlace antes, revisa también spam o correo no deseado."
            )
        if "invalid" in texto and "email" in texto:
            return "El correo ingresado no es válido."
        return f"No se pudo enviar el enlace: {self._format_error(exc)}"

    def enviar_enlace_recuperacion_password(self, email: str) -> Tuple[bool, str]:
        """Envía enlace de restablecimiento vía Supabase Auth.

        Requiere plantilla de correo en Supabase con enlace server-side, p. ej.:
        <a href="{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=recovery">...</a>
        """
        email_norm = (email or "").strip().lower()
        if not email_norm or "@" not in email_norm:
            return False, "Ingresa un correo electrónico válido."

        try:
            result = self.supabase.table("users").select("email").eq("email", email_norm).execute()
            if not result.data:
                return False, "No encontramos una cuenta registrada con ese correo."

            redirect_to = self.obtener_redirect_url()
            self.supabase.auth.reset_password_for_email(
                email_norm,
                {"redirect_to": redirect_to},
            )
            return True, f"Te enviamos un enlace de recuperación a {email_norm}. Revisa tu bandeja de entrada."
        except Exception as e:
            return False, self._mensaje_error_recuperacion_password(e)

    @staticmethod
    def _extraer_tokens_sesion_auth(res) -> Tuple[Optional[str], Optional[str]]:
        session = getattr(res, "session", None)
        if session is None and isinstance(res, dict):
            session = res.get("session")
        if not session:
            return None, None
        access = getattr(session, "access_token", None) or (
            session.get("access_token") if isinstance(session, dict) else None
        )
        refresh = getattr(session, "refresh_token", None) or (
            session.get("refresh_token") if isinstance(session, dict) else None
        )
        return access, refresh

    def _activar_recuperacion_desde_token_hash(self, token_hash: str) -> Tuple[bool, str]:
        """Valida enlace de recuperación con verify_otp (query ?token_hash=&type=recovery)."""
        try:
            res = self.supabase.auth.verify_otp({"token_hash": token_hash, "type": "recovery"})
            access, refresh = self._extraer_tokens_sesion_auth(res)
            if not access or not refresh:
                self._limpiar_parametros_oauth()
                return False, "No se pudo validar el enlace de recuperación."
            return self._activar_modo_recuperacion_password(access, refresh)
        except Exception as e:
            self._limpiar_parametros_oauth()
            return False, f"Enlace de recuperación inválido o expirado: {self._format_error(e)}"

    def _activar_modo_recuperacion_password(self, access: str, refresh: str) -> Tuple[bool, str]:
        """Establece sesión Supabase de recuperación sin iniciar el hub veloX."""
        try:
            self.supabase.auth.set_session(access, refresh)
            self._persistir_sesion_supabase({"access_token": access, "refresh_token": refresh})
            user_res = self.supabase.auth.get_user()
            user = getattr(user_res, "user", None) or (
                user_res.get("user") if isinstance(user_res, dict) else None
            )
            email = (getattr(user, "email", None) or "").strip().lower()
            if not email and isinstance(user, dict):
                email = (user.get("email") or "").strip().lower()
            if not email:
                self._limpiar_parametros_oauth()
                return False, "No se pudo validar el enlace de recuperación."

            st.session_state["password_recovery_mode"] = True
            st.session_state["recovery_email"] = email
            st.session_state["vista_actual"] = VISTA_RECUPERAR_PASSWORD
            st.session_state["autenticado"] = False
            st.session_state["acceso_pagado"] = False
            st.session_state.pop("google_oauth_url", None)
            self._limpiar_parametros_oauth()
            return True, ""
        except Exception as e:
            self._limpiar_parametros_oauth()
            return False, f"Enlace de recuperación inválido o expirado: {self._format_error(e)}"

    def completar_recuperacion_password(self, nueva_password: str) -> Tuple[bool, str]:
        """Actualiza contraseña en Supabase Auth y sincroniza hash local."""
        if not st.session_state.get("password_recovery_mode"):
            return False, "No hay una recuperación de contraseña activa."
        if len(nueva_password or "") < 6:
            return False, "La contraseña debe tener al menos 6 caracteres."

        try:
            self.supabase.auth.update_user({"password": nueva_password})
            email_norm = (st.session_state.get("recovery_email") or "").strip().lower()
            if email_norm:
                user = self._obtener_usuario_db(email_norm)
                if user:
                    ok_local, msg_local = self._persistir_password_velox(
                        email_norm, nueva_password, user
                    )
                    if not ok_local:
                        return False, msg_local
            return True, "¡Tu contraseña ha sido actualizada con éxito!"
        except Exception as e:
            texto = self._format_error(e).lower()
            if any(p in texto for p in ("jwt", "expired", "expir", "invalid session", "session not found")):
                return False, (
                    "La sesión de recuperación expiró o ya no es válida. "
                    "Solicita un nuevo enlace desde «¿Olvidaste tu contraseña?»."
                )
            return False, f"No se pudo actualizar la contraseña: {self._format_error(e)}"

    def finalizar_recuperacion_password(self) -> None:
        """Cierra sesión temporal de recuperación y vuelve al login."""
        try:
            self.supabase.auth.sign_out()
        except Exception:
            pass
        for key in (
            "password_recovery_mode",
            "recovery_email",
            "access_token",
            "refresh_token",
            "session_string",
        ):
            st.session_state.pop(key, None)
        st.session_state["autenticado"] = False
        st.session_state["acceso_pagado"] = False
        st.session_state["vista_actual"] = VISTA_LOGIN
        st.session_state["welcome_active_tab"] = 0
        self._limpiar_parametros_oauth()

    def _actor_es_master(self, actor_email: str) -> bool:
        try:
            result = self.supabase.table("users").select("rol").eq("email", actor_email).execute()
            if not result.data:
                return False
            return self.es_rol_master(result.data[0].get("rol"))
        except Exception:
            return False

    def actualizar_rol_usuario(
        self, email_objetivo: str, rol_etiqueta: str, actor_email: str
    ) -> Tuple[bool, str]:
        """Actualiza users.rol. Solo ejecutable por un usuario con rol Master."""
        if not self._actor_es_master(actor_email):
            return False, "Solo un usuario con rol Master puede cambiar roles."

        email_norm = (email_objetivo or "").strip().lower()
        actor_norm = (actor_email or "").strip().lower()
        if not email_norm:
            return False, "Correo de usuario inválido."

        nuevo_rol = self.rol_desde_etiqueta(rol_etiqueta)
        if rol_etiqueta not in self.ROLES_ETIQUETAS:
            return False, "Rol inválido."

        try:
            actual = self.supabase.table("users").select("rol").eq("email", email_norm).execute()
            if not actual.data:
                return False, "Usuario no encontrado."

            rol_actual = self.normalizar_rol(actual.data[0].get("rol"))
            if rol_actual == nuevo_rol:
                return True, f"El rol de {email_norm} ya es {rol_etiqueta}."

            if self.es_rol_master(rol_actual) and not self.es_rol_master(nuevo_rol):
                masters = self.supabase.table("users").select("email").eq("rol", "master").execute()
                emails_master = [m["email"] for m in (masters.data or [])]
                if len(emails_master) <= 1 and email_norm in emails_master:
                    return False, "Debe existir al menos un usuario Master en el sistema."

            update_data: Dict[str, Any] = {"rol": nuevo_rol}
            if self.es_rol_master(nuevo_rol) or self.es_rol_administrador(nuevo_rol):
                update_data["activo"] = True
                update_data["pago_confirmado"] = True

            if self.es_rol_administrador(nuevo_rol):
                existing = self.supabase.table("users").select("perfil").eq("email", email_norm).execute()
                perfil = (existing.data[0].get("perfil") if existing.data else {}) or {}
                if not (perfil.get("permisos_admin") or {}).get("modulos"):
                    perfil["permisos_admin"] = {
                        "modulos": list(self.MODULOS_ADMIN_DEFAULT),
                        "secciones": [],
                        "puede_publicar": False,
                    }
                    update_data["perfil"] = perfil

            result = self.supabase.table("users").update(update_data).eq("email", email_norm).execute()
            if not result.data:
                return False, "No se pudo actualizar el rol."

            if email_norm == actor_norm:
                st.session_state["rol"] = nuevo_rol
                if self.es_rol_master(nuevo_rol):
                    st.session_state["acceso_pagado"] = True

            return True, f"Rol actualizado: {email_norm} → {rol_etiqueta}."
        except Exception as e:
            return False, f"Error al actualizar rol: {self._format_error(e)}"

    def _sincronizar_usuario_google(self, email: str, nombre: str, avatar: Optional[str]) -> Dict[str, Any]:
        email_norm = (email or "").strip().lower()
        perfil_oauth = (
            {"avatar_url": avatar, "auth_provider": "google"}
            if avatar
            else {"auth_provider": "google"}
        )

        user = self._obtener_usuario_db(email_norm)
        if not user:
            return self._crear_registro_usuario_inicial(
                email_norm,
                nombre=nombre,
                avatar=avatar,
                auth_provider="google",
            )

        perfil = {**self._perfil_usuario(user), **perfil_oauth}
        update_data: Dict[str, Any] = {"nombre": nombre, "perfil": perfil}
        if email_norm == self.MASTER_EMAIL:
            update_data["rol"] = "master"
            update_data["activo"] = True
            update_data["pago_confirmado"] = True
        if not perfil.get("velox_password_configured") and (
            not user.get("password") or not user.get("password_salt")
        ):
            pw_hash, salt = self._password_temporal_oauth(email_norm)
            update_data["password"] = pw_hash
            update_data["password_salt"] = salt
            perfil["velox_password_temp"] = True
            perfil["velox_password_configured"] = False
            update_data["perfil"] = perfil
        self.supabase.table("users").update(update_data).eq("email", email_norm).execute()
        user.update(update_data)
        return user

    def procesar_retorno_auth_url(self) -> Tuple[bool, str]:
        """Intercepta callbacks de URL antes de renderizar login (OAuth, recovery, tokens)."""
        oauth_error = self._query_param("error")
        if oauth_error:
            self._limpiar_parametros_oauth()
            st.session_state.pop("google_oauth_url", None)
            st.session_state.pop("oauth_last_code", None)
            return False, ""

        try:
            token_hash = self._query_param("token_hash")
            auth_type = self._query_param("type")
            if token_hash and auth_type == "recovery":
                with st.spinner("Validando enlace..."):
                    return self._activar_recuperacion_desde_token_hash(token_hash)

            code = self._query_param("code")
            if code:
                if st.session_state.get("oauth_last_code") == code:
                    self._limpiar_parametros_oauth()
                    return False, ""

                with st.spinner("Validando cuenta Google con Supabase..."):
                    res = self.supabase.auth.exchange_code_for_session({"auth_code": code})
                    session = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)
                    user = getattr(res, "user", None) or getattr(session, "user", None)
                    if not user and session:
                        user = getattr(session, "user", None)
                    if not user:
                        self._limpiar_parametros_oauth()
                        st.session_state.pop("google_oauth_url", None)
                        return False, ""

                    st.session_state["oauth_last_code"] = code
                    self._persistir_sesion_supabase(session)
                    ok, msg = self._aplicar_usuario_sesion(user)
                    if ok:
                        st.session_state.pop("google_oauth_url", None)
                        self._limpiar_parametros_oauth()
                    return ok, msg

            access = self._query_param("access_token")
            refresh = self._query_param("refresh_token")
            auth_type = self._query_param("type")

            if access:
                if self._es_flujo_recuperacion(auth_type, access, refresh, code):
                    if not refresh:
                        self._limpiar_parametros_oauth()
                        return False, (
                            "El enlace de recuperación está incompleto. "
                            "Solicita uno nuevo desde la pantalla de inicio de sesión."
                        )
                    with st.spinner("Validando enlace..."):
                        return self._activar_modo_recuperacion_password(access, refresh)

                if refresh:
                    self.supabase.auth.set_session(access, refresh)
                    self._persistir_sesion_supabase({"access_token": access, "refresh_token": refresh})
                    user_res = self.supabase.auth.get_user()
                    user = getattr(user_res, "user", None) or (user_res.get("user") if isinstance(user_res, dict) else None)
                    if user:
                        ok, msg = self._aplicar_usuario_sesion(user)
                        if ok:
                            st.session_state.pop("google_oauth_url", None)
                            self._limpiar_parametros_oauth()
                        return ok, msg
        except Exception as e:
            self._limpiar_parametros_oauth()
            st.session_state.pop("google_oauth_url", None)
            if self._es_error_pkce(e):
                print(f"OAuth PKCE reiniciado: {self._format_error(e)}")
                AuthManager.limpiar_estado_oauth()
                st.session_state["google_oauth_force_refresh"] = True
                return False, ""
            return False, f"Error en callback OAuth: {self._format_error(e)}"
        return False, ""

    def handle_oauth_callback(self) -> Tuple[bool, str]:
        """Alias retrocompatible de procesar_retorno_auth_url()."""
        return self.procesar_retorno_auth_url()

    def bootstrap_session(self) -> bool:
        """Restaura sesión Supabase desde session_state (evita desconexión al recargar)."""
        if st.session_state.get("password_recovery_mode"):
            access = st.session_state.get("access_token")
            refresh = st.session_state.get("refresh_token")
            if access and refresh:
                try:
                    self.supabase.auth.set_session(access, refresh)
                except Exception as e:
                    print(f"Sesión de recuperación inválida: {self._format_error(e)}")
            return False

        if st.session_state.get("autenticado") and st.session_state.get("usuario"):
            try:
                email = st.session_state["usuario"]
                user = self._obtener_usuario_db(email)
                if not user:
                    user = self._asegurar_usuario_db(
                        email,
                        nombre=st.session_state.get("nombre"),
                        avatar=st.session_state.get("avatar_url"),
                        auth_provider="google",
                    )
                st.session_state["acceso_pagado"] = self.payments.usuario_tiene_acceso(user)
                st.session_state["rol"] = user.get("rol", "usuario")
                st.session_state["secciones"] = user.get("secciones") or ["excel"]
                st.session_state["nombre"] = user.get("nombre", st.session_state.get("nombre"))
                self._aplicar_permisos_a_sesion(user)
                return True
            except Exception as e:
                print(f"Error refrescando sesión local: {self._format_error(e)}")

        access = st.session_state.get("access_token")
        refresh = st.session_state.get("refresh_token")
        if not access or not refresh:
            session_string = st.session_state.get("session_string")
            if session_string:
                try:
                    data = json.loads(session_string)
                    access = data.get("access_token")
                    refresh = data.get("refresh_token")
                except json.JSONDecodeError:
                    pass
        if access and refresh:
            try:
                self.supabase.auth.set_session(access, refresh)
                user_res = self.supabase.auth.get_user()
                user = getattr(user_res, "user", None)
                if user:
                    self._persistir_sesion_supabase({"access_token": access, "refresh_token": refresh})
                    self._aplicar_usuario_sesion(user)
                    return True
            except Exception as e:
                print(f"Sesión expirada o inválida: {self._format_error(e)}")
                self.cerrar_sesion(silent=True)
        return False

    def refrescar_estado_acceso(self) -> bool:
        email = st.session_state.get("usuario")
        if not email:
            return False
        try:
            res = self.supabase.table("users").select("*").eq("email", email).execute()
            if res.data:
                acceso = self.payments.usuario_tiene_acceso(res.data[0])
                st.session_state["acceso_pagado"] = acceso
                return acceso
        except Exception as e:
            print(f"Error refrescando acceso: {self._format_error(e)}")
        return False

    def cerrar_sesion(self, silent: bool = False) -> None:
        try:
            self.supabase.auth.sign_out()
        except Exception:
            pass
        for key in SESSION_KEYS:
            if key in st.session_state:
                del st.session_state[key]
        for extra in ("google_oauth_url", "oauth_last_code", "velox_setup_email", "password_recovery_mode", "recovery_email"):
            st.session_state.pop(extra, None)
        if not silent:
            st.toast("Sesión cerrada correctamente", icon="👋")

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
            if not self._actor_puede_gestionar_usuarios(master_email):
                return False, "No tienes permiso para asignar secciones"
            data = {"secciones_asignadas": secciones_asignadas, "secciones": secciones_asignadas}
            result = self.supabase.table("users").update(data).eq("email", email).execute()
            if result.data:
                return True, f"Secciones asignadas: {', '.join(secciones_asignadas)}"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, f"Error interno: {self._format_error(e)}"

    def obtener_perfil(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            email_norm = (email or "").strip().lower()
            result = (
                self.supabase.table("users")
                .select(
                    "nombre, email, rol, creado, perfil, "
                    "correo_personal, correo_secundario, celular, celular_secundario"
                )
                .eq("email", email_norm)
                .execute()
            )
            user = self._primera_fila(result)
            if not user:
                return None
            perfil_json = user.get("perfil") or {}
            return {
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["rol"],
                "fecha_registro": user.get("creado", ""),
                "codigo_usuario": self._generar_codigo_usuario(email_norm),
                "avatar_url": st.session_state.get("avatar_url") or perfil_json.get("avatar_url"),
                "correo_personal": user.get("correo_personal") or "",
                "correo_secundario": user.get("correo_secundario") or "",
                "celular": user.get("celular") or "",
                "celular_secundario": user.get("celular_secundario") or "",
            }
        except Exception as e:
            print(f"Error obteniendo perfil: {e}")
            return None

    def actualizar_perfil(self, email: str, datos_perfil: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            email_norm = (email or "").strip().lower()
            if not email_norm:
                return False, "Email de sesión no válido"

            def _nullable(valor: Any) -> Optional[str]:
                limpio = str(valor or "").strip()
                return limpio if limpio else None

            update_data = {
                "correo_personal": _nullable(datos_perfil.get("correo_personal")),
                "correo_secundario": _nullable(datos_perfil.get("correo_secundario")),
                "celular": _nullable(datos_perfil.get("celular")),
                "celular_secundario": _nullable(datos_perfil.get("celular_secundario")),
            }

            result = (
                self.supabase.table("users")
                .update(update_data)
                .eq("email", email_norm)
                .execute()
            )
            if result.data:
                return True, "Perfil actualizado correctamente"
            return False, "No se pudo actualizar el perfil"
        except Exception as e:
            return False, f"Error interno: {self._format_error(e)}"

    def _generar_codigo_usuario(self, email: str) -> str:
        return f"VLX-{hashlib.md5(email.encode()).hexdigest()[:8].upper()}"

    def listar_usuarios(self) -> Dict[str, Dict[str, Any]]:
        try:
            result = self.supabase.table("users").select("*").execute()
            return {u["email"]: u for u in result.data or []}
        except Exception as e:
            print(f"Error listando usuarios: {e}")
            return {}

    def eliminar_usuario(self, email: str, master_email: str) -> Tuple[bool, str]:
        try:
            if not self._actor_es_master(master_email):
                return False, "Solo un Master puede eliminar usuarios"
            if email == master_email:
                return False, "No puedes eliminarte a ti mismo"
            result = self.supabase.table("users").delete().eq("email", email).execute()
            if result.data:
                return True, "Usuario eliminado correctamente"
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, f"Error interno: {self._format_error(e)}"


def SECCIONES_DEFAULT():
    return ["excel"]