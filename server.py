"""
Servidor ASGI: FastAPI (API backend) + proxy reverso hacia Streamlit (UI).

Orden crítico:
  1) Rutas API (/api/v1/hotmart-webhook, /health) registradas primero.
  2) Middleware excluye /api, /docs, /openapi.json del proxy.
  3) Catch-all GET/HEAD al final para Streamlit.
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
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
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


def _is_fastapi_reserved_path(path: str) -> bool:
    return (
        path.startswith("/api")
        or path.startswith("/docs")
        or path.startswith("/openapi.json")
        or path == "/health"
        or path == "/redoc"
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


async def _proxy_request_to_streamlit(request: Request) -> Response:
    if http_client is None:
        raise HTTPException(status_code=503, detail="Streamlit proxy not ready")

    path = request.url.path or "/"
    body = await request.body()
    headers = _filtered_headers(request.headers.items())

    logger.debug("Proxy Streamlit %s %s", request.method, path)
    upstream = await http_client.request(
        request.method,
        path,
        params=request.query_params,
        content=body,
        headers=headers,
    )
    response_headers = _filtered_headers(upstream.headers.items())
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
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


async def _wait_streamlit_ready(timeout: float = 90.0) -> None:
    import time

    deadline = time.monotonic() + timeout
    health_urls = (
        f"{STREAMLIT_BASE}/_stcore/health",
        f"{STREAMLIT_BASE}/",
    )
    async with httpx.AsyncClient(timeout=2.0) as client:
        while time.monotonic() < deadline:
            for url in health_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code < 500:
                        logger.info("Streamlit listo en %s", url)
                        return
                except httpx.HTTPError:
                    pass
            await asyncio.sleep(0.5)
    raise RuntimeError("Streamlit no respondió a tiempo en el puerto interno.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global streamlit_proc, http_client

    logger.info("Iniciando Streamlit en %s:%s", STREAMLIT_HOST, STREAMLIT_PORT)
    streamlit_proc = subprocess.Popen(
        _streamlit_cmd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    await _wait_streamlit_ready()
    http_client = httpx.AsyncClient(
        base_url=STREAMLIT_BASE,
        timeout=httpx.Timeout(120.0, connect=10.0),
        follow_redirects=False,
    )
    logger.info("FastAPI escuchando en puerto %s", PORT)
    try:
        yield
    finally:
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
# RUTAS API — declaradas ANTES del middleware/catch-all (orden crítico)
# ---------------------------------------------------------------------------

@app.api_route("/api/v1/hotmart-webhook", methods=["GET", "POST"], tags=["hotmart"])
@app.api_route("/api/v1/hotmart-webhook/", methods=["GET", "POST"], include_in_schema=False)
async def hotmart_webhook(request: Request, background_tasks: BackgroundTasks):
    path = request.url.path
    logger.info("Hotmart webhook handler method=%s path=%s", request.method, path)

    if request.method == "GET":
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "message": "Webhook active"},
        )

    try:
        data = await request.json()
    except Exception:
        data = {}

    if isinstance(data, dict) and data:
        event = str(data.get("event") or "").strip().upper() or "UNKNOWN"
        token = _extract_hotmart_token(request)
        logger.info("Hotmart POST event=%s path=%s", event, path)
        background_tasks.add_task(_process_hotmart_event_background, data, token)

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "Event received", "data": data},
    )


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "velox-api"}


# ---------------------------------------------------------------------------
# MIDDLEWARE — excluye rutas API del proxy Streamlit
# ---------------------------------------------------------------------------

@app.middleware("http")
async def streamlit_proxy_guard(request: Request, call_next):
    path = request.url.path

    # 1. Si es cualquier ruta de la API o documentación, NUNCA la envíes a Streamlit
    if _is_fastapi_reserved_path(path):
        return await call_next(request)

    # 2. Si no es GET ni HEAD (y no es API), responder con 405 directo de FastAPI o dejar pasar a FastAPI
    if request.method not in ("GET", "HEAD"):
        return await call_next(request)

    # 3. Solo las peticiones GET/HEAD de la interfaz se delegan a Streamlit
    return await call_next(request)


# ---------------------------------------------------------------------------
# CATCH-ALL — AL FINAL, solo GET/HEAD hacia Streamlit
# ---------------------------------------------------------------------------

@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def proxy_streamlit_get(request: Request, full_path: str) -> Response:
    path = request.url.path

    if _is_fastapi_reserved_path(path):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    if not path.startswith("/api"):
        return await _proxy_request_to_streamlit(request)

    return JSONResponse(status_code=404, content={"detail": "Not Found"})


@app.websocket("/{full_path:path}")
async def proxy_streamlit_ws(websocket: WebSocket, full_path: str) -> None:
    path = f"/{full_path}" if full_path else "/"
    if _is_fastapi_reserved_path(path):
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
                    msg_type = message.get("type")
                    if msg_type == "websocket.disconnect":
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
