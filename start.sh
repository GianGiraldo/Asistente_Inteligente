#!/bin/sh
set -eu

export NGINX_PROXY=1

ST_LOG=/tmp/streamlit.log
API_LOG=/tmp/api.log
: >"$ST_LOG"
: >"$API_LOG"

echo "[velox] Generando config Streamlit..."
python -c "
from server import _ensure_streamlit_config, _ensure_streamlit_secrets
_ensure_streamlit_config()
_ensure_streamlit_secrets()
"

echo "[velox] Iniciando Streamlit en 127.0.0.1:8501..."
python -m streamlit run app.py \
  --server.port=8501 \
  --server.address=127.0.0.1 \
  --server.headless=true \
  --browser.gatherUsageStats=false \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.enableWebsocketCompression=false \
  >>"$ST_LOG" 2>&1 &
ST_PID=$!

echo "[velox] Iniciando API FastAPI en 127.0.0.1:8502..."
python -m uvicorn server:app \
  --host 127.0.0.1 \
  --port 8502 \
  --proxy-headers \
  --forwarded-allow-ips='*' \
  >>"$API_LOG" 2>&1 &
API_PID=$!

probe_url() {
  python -c "
import sys
import urllib.request
url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=3) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
" "$1"
}

wait_service() {
  url=$1
  name=$2
  max=${3:-60}
  i=0
  while [ "$i" -lt "$max" ]; do
    if ! kill -0 "$ST_PID" 2>/dev/null && [ "$name" = "Streamlit" ]; then
      echo "[velox] ERROR: Streamlit terminó antes de arrancar"
      tail -60 "$ST_LOG" || true
      exit 1
    fi
    if ! kill -0 "$API_PID" 2>/dev/null && [ "$name" = "API" ]; then
      echo "[velox] ERROR: API terminó antes de arrancar"
      tail -30 "$API_LOG" || true
      exit 1
    fi
    if probe_url "$url"; then
      echo "[velox] $name listo (${i}s)"
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  return 1
}

if ! wait_service "http://127.0.0.1:8502/health" "API" 90; then
  echo "[velox] ERROR: API no respondió"
  tail -40 "$API_LOG" || true
  exit 1
fi

# Streamlit puede tardar; nginx arranca igual y muestra loading.html si aún no está listo.
if wait_service "http://127.0.0.1:8501/_stcore/health" "Streamlit" 120; then
  echo "[velox] Streamlit health OK"
else
  if probe_url "http://127.0.0.1:8501/"; then
    echo "[velox] Streamlit responde en / (aún compilando scripts)"
  else
    echo "[velox] AVISO: Streamlit aún iniciando; nginx mostrará pantalla de carga"
    tail -20 "$ST_LOG" || true
  fi
fi

echo "[velox] Iniciando nginx en puerto ${PORT:-8080}..."
exec nginx -g 'daemon off;'
