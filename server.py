"""
Servidor ASGI: FastAPI (webhook Hotmart) + proxy reverso hacia Streamlit.
No modifica app.py; Streamlit corre como subproceso interno en puerto local.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from typing import Dict, Iterable, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from hotmart_webhook import process_hotmart_webhook

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


def _filtered_headers(headers: Iterable[tuple[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, value in headers:
        if key.lower() in HOP_BY_HOP_HEADERS:
            continue
        out[key] = value
    return out


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


app = FastAPI(title="veloX API", lifespan=lifespan)


@app.post("/api/v1/hotmart-webhook")
async def hotmart_webhook(
    request: Request,
    x_hotmart_hottok: Optional[str] = Header(default=None, alias="X-Hotmart-Hottok"),
):
    secret = (os.getenv("HOTMART_WEBHOOK_SECRET") or "").strip()
    token = (x_hotmart_hottok or request.headers.get("X-Hotmart-Hottok") or "").strip()

    if not secret:
        logger.error("HOTMART_WEBHOOK_SECRET no configurado")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    if not token or token != secret:
        raise HTTPException(status_code=401, detail="Invalid Hotmart token")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    ok, message = process_hotmart_webhook(payload)
    if not ok:
        logger.warning("Hotmart webhook rechazado: %s", message)
        raise HTTPException(status_code=422, detail=message)

    return JSONResponse(content={"status": "ok"}, status_code=200)


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_streamlit(request: Request, full_path: str) -> Response:
    if http_client is None:
        raise HTTPException(status_code=503, detail="Streamlit proxy not ready")

    path = f"/{full_path}" if full_path else "/"
    body = await request.body()
    headers = _filtered_headers(request.headers.items())

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


@app.websocket("/{full_path:path}")
async def proxy_streamlit_ws(websocket: WebSocket, full_path: str) -> None:
    import websockets

    path = f"/{full_path}" if full_path else "/"
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
