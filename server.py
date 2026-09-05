"""
Servidor ASGI: FastAPI (API) + proxy hacia Streamlit (UI).

La API arranca INMEDIATamente (sin esperar Streamlit) para que Cloud Run
acepte POST /api/* en el puerto $PORT. Streamlit corre en segundo plano.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, Iterable, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from hotmart_webhook import process_hotmart_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", "8080"))
STREAMLIT_HOST = os.getenv("STREAMLIT_INTERNAL_HOST", "127.0.0.1")
STREAMLIT_PORT = int(os.getenv("STREAMLIT_INTERNAL_PORT", "8501"))
STREAMLIT_BASE = f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}"
STREAMLIT_WS = f"ws://{STREAMLIT_HOST}:{STREAMLIT_PORT}"

WEBHOOK_PATH = "/api/v1/hotmart-webhook"

HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)

streamlit_proc: Optional[subprocess.Popen] = None
http_client: Optional[httpx.AsyncClient] = None
streamlit_ready = False
STREAMLIT_BOOT_TIMEOUT = float(os.getenv("STREAMLIT_BOOT_TIMEOUT", "180"))
STREAMLIT_PROXY_WAIT = float(os.getenv("STREAMLIT_PROXY_WAIT", "90"))

_LOADING_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="2"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>veloX — Cargando</title>
  <style>
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: system-ui, sans-serif; background: #0b1220; color: #e5e7eb;
    }}
    .box {{ text-align: center; padding: 2rem; }}
    .spinner {{
      width: 48px; height: 48px; border: 4px solid #334155;
      border-top-color: #38bdf8; border-radius: 50%;
      animation: spin 1s linear infinite; margin: 0 auto 1rem;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <h1>veloX</h1>
    <p>Iniciando plataforma…</p>
    <p><small>La página se actualizará automáticamente.</small></p>
  </div>
</body>
</html>"""


def _is_api_or_system_path(path: str) -> bool:
    normalized = (path or "/").lower().split("?", 1)[0]
    return (
        normalized.startswith("/api")
        or normalized.startswith("/docs")
        or normalized.startswith("/openapi.json")
        or normalized in ("/health", "/redoc")
    )


def _extract_hotmart_token(request: Request) -> str:
    return (
        request.headers.get("X-Hotmart-Hottok")
        or request.headers.get("X-HOTMART-HOTTOK")
        or ""
    ).strip()


def _process_hotmart_event_background(payload: Dict[str, Any], token: str) -> None:
    event = str(payload.get("event") or "").strip().upper() or "UNKNOWN"
    secret = (os.getenv("HOTMART_WEBHOOK_SECRET") or "").strip()
    if not secret:
        logger.error("Hotmart background: secret no configurado (event=%s)", event)
        return
    if not token or token != secret:
        logger.error("Hotmart background: token inválido (event=%s)", event)
        return
    logger.info("Hotmart background: procesando event=%s", event)
    try:
        ok, message = process_hotmart_webhook(payload)
        if ok:
            logger.info("Hotmart background: OK event=%s detail=%s", event, message)
        else:
            logger.error("Hotmart background: fallo event=%s detail=%s", event, message)
    except Exception:
        logger.exception("Hotmart background: excepción event=%s", event)


def _filtered_headers(headers: Iterable[tuple[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, value in headers:
        if key.lower() in HOP_BY_HOP_HEADERS:
            continue
        out[key] = value
    return out


async def _probe_streamlit_health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as probe:
            resp = await probe.get(f"{STREAMLIT_BASE}/_stcore/health")
            return resp.status_code < 500
    except httpx.HTTPError:
        return False


async def _wait_for_streamlit_ready(timeout: float) -> bool:
    global streamlit_ready
    if streamlit_ready:
        return True
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if streamlit_proc is not None and streamlit_proc.poll() is not None:
            logger.error(
                "Streamlit terminó inesperadamente (exit=%s)",
                streamlit_proc.returncode,
            )
            return False
        if await _probe_streamlit_health():
            streamlit_ready = True
            logger.info("Streamlit listo (proxy wait)")
            return True
        await asyncio.sleep(1.0)
    return streamlit_ready


def _loading_page_response() -> Response:
    return Response(
        content=_LOADING_HTML,
        status_code=200,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


async def _proxy_request_to_streamlit(request: Request) -> Response:
    if http_client is None:
        if request.method in ("GET", "HEAD") and (request.url.path or "/") == "/":
            return _loading_page_response()
        raise HTTPException(status_code=503, detail="Streamlit proxy not ready")

    if not streamlit_ready:
        ready = await _wait_for_streamlit_ready(STREAMLIT_PROXY_WAIT)
        if not ready:
            if request.method in ("GET", "HEAD"):
                return _loading_page_response()
            raise HTTPException(status_code=503, detail="Streamlit aún iniciando")

    path = request.url.path or "/"
    body = await request.body()
    headers = _filtered_headers(request.headers.items())

    upstream = await http_client.request(
        request.method,
        path,
        params=request.query_params,
        content=body,
        headers=headers,
    )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_filtered_headers(upstream.headers.items()),
        media_type=upstream.headers.get("content-type"),
    )


def _streamlit_cmd() -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        f"--server.port={STREAMLIT_PORT}",
        f"--server.address={STREAMLIT_HOST}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]


def _streamlit_env() -> Dict[str, str]:
    """Evita que Streamlit herede PORT=8080 de Cloud Run (conflicto con Uvicorn)."""
    env = os.environ.copy()
    env.pop("PORT", None)
    env["STREAMLIT_SERVER_PORT"] = str(STREAMLIT_PORT)
    env["STREAMLIT_SERVER_ADDRESS"] = STREAMLIT_HOST
    return env


async def _bootstrap_streamlit() -> None:
    """Arranca Streamlit en background; la API no espera bloqueada."""
    global streamlit_proc, http_client, streamlit_ready

    import time

    logger.info("Bootstrap Streamlit en %s:%s (background)", STREAMLIT_HOST, STREAMLIT_PORT)
    streamlit_proc = subprocess.Popen(
        _streamlit_cmd(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=_streamlit_env(),
    )
    http_client = httpx.AsyncClient(
        base_url=STREAMLIT_BASE,
        timeout=httpx.Timeout(120.0, connect=10.0),
        follow_redirects=False,
    )

    deadline = time.monotonic() + STREAMLIT_BOOT_TIMEOUT
    while time.monotonic() < deadline:
        if streamlit_proc.poll() is not None:
            logger.error(
                "Streamlit falló al arrancar (exit=%s)",
                streamlit_proc.returncode,
            )
            return
        if await _probe_streamlit_health():
            streamlit_ready = True
            logger.info("Streamlit listo (background)")
            return
        await asyncio.sleep(1.0)

    logger.error(
        "Streamlit no respondió en %ss — la UI puede no estar disponible",
        int(STREAMLIT_BOOT_TIMEOUT),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_task = asyncio.create_task(_bootstrap_streamlit())
    logger.info("FastAPI API lista en puerto %s (Streamlit en background)", PORT)
    try:
        yield
    finally:
        bootstrap_task.cancel()
        if http_client is not None:
            await http_client.aclose()
        if streamlit_proc is not None:
            streamlit_proc.terminate()
            try:
                streamlit_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                streamlit_proc.kill()


app = FastAPI(title="veloX API", lifespan=lifespan, redirect_slashes=False)

# ---------------------------------------------------------------------------
# ROUTER API — montado con prefijo /api (aislamiento total del proxy UI)
# ---------------------------------------------------------------------------
api_router = APIRouter(prefix="/api", tags=["api"])


@api_router.get("/v1/hotmart-webhook")
async def hotmart_webhook_get():
    logger.info("Hotmart GET ping → 200 JSON")
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "Webhook active"},
    )


@api_router.post("/v1/hotmart-webhook")
async def hotmart_webhook_post(request: Request, background_tasks: BackgroundTasks):
    logger.info("Hotmart POST recibido path=%s", request.url.path)
    try:
        data = await request.json()
    except Exception:
        data = {}

    if isinstance(data, dict) and data:
        event = str(data.get("event") or "").strip().upper() or "UNKNOWN"
        token = _extract_hotmart_token(request)
        logger.info("Hotmart POST event=%s", event)
        background_tasks.add_task(_process_hotmart_event_background, data, token)

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "Event received", "data": data},
    )


# Variante con barra final (redirect_slashes=False)
@api_router.get("/v1/hotmart-webhook/")
async def hotmart_webhook_get_slash():
    return await hotmart_webhook_get()


@api_router.post("/v1/hotmart-webhook/")
async def hotmart_webhook_post_slash(request: Request, background_tasks: BackgroundTasks):
    return await hotmart_webhook_post(request, background_tasks)


app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "service": "velox-api",
        "streamlit_ready": streamlit_ready,
    }


# ---------------------------------------------------------------------------
# MIDDLEWARE — /api/* NUNCA va a Streamlit
# ---------------------------------------------------------------------------
@app.middleware("http")
async def streamlit_proxy_guard(request: Request, call_next):
    path = request.url.path.lower()

    if _is_api_or_system_path(path):
        logger.info("FastAPI route: %s %s", request.method, path)
        return await call_next(request)

    if request.method not in ("GET", "HEAD"):
        logger.debug("Proxy Streamlit (non-API): %s %s", request.method, path)
        return await _proxy_request_to_streamlit(request)

    return await call_next(request)


# ---------------------------------------------------------------------------
# CATCH-ALL UI — solo GET/HEAD, al final del archivo
# ---------------------------------------------------------------------------
@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def proxy_streamlit_get(request: Request, full_path: str) -> Response:
    path = request.url.path
    if _is_api_or_system_path(path):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return await _proxy_request_to_streamlit(request)


@app.websocket("/{full_path:path}")
async def proxy_streamlit_ws(websocket: WebSocket, full_path: str) -> None:
    path = f"/{full_path}" if full_path else "/"
    if _is_api_or_system_path(path):
        await websocket.close(code=1008)
        return

    import websockets

    query = websocket.scope.get("query_string", b"").decode()
    target = f"{STREAMLIT_WS}{path}"
    if query:
        target = f"{target}?{query}"

    subprotocols = websocket.scope.get("subprotocols") or []
    await websocket.accept(subprotocol=subprotocols[0] if subprotocols else None)

    extra_headers = _filtered_headers(
        (name.decode(), value.decode())
        for name, value in websocket.headers.raw
    )

    try:
        async with websockets.connect(
            target,
            additional_headers=extra_headers,
            subprotocols=subprotocols or None,
            open_timeout=15,
        ) as upstream:
            async def client_to_upstream() -> None:
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        await upstream.close()
                        break
                    if "text" in message:
                        await upstream.send(message["text"])
                    elif "bytes" in message:
                        await upstream.send(message["bytes"])

            async def upstream_to_client() -> None:
                async for payload in upstream:
                    if isinstance(payload, bytes):
                        await websocket.send_bytes(payload)
                    else:
                        await websocket.send_text(payload)

            await asyncio.gather(client_to_upstream(), upstream_to_client())
    except WebSocketDisconnect:
        return
    except Exception as exc:
        logger.debug("WebSocket proxy cerrado: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
