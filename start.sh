#!/bin/sh
set -e

export NGINX_PROXY=1

python -c "
from server import _ensure_streamlit_config, _ensure_streamlit_secrets
_ensure_streamlit_config()
_ensure_streamlit_secrets()
"

echo "Iniciando Streamlit en 127.0.0.1:8501..."
python -m streamlit run app.py \
  --server.port=8501 \
  --server.address=127.0.0.1 \
  --server.headless=true \
  --browser.gatherUsageStats=false \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.enableWebsocketCompression=false \
  2>&1 &

echo "Iniciando API FastAPI en 127.0.0.1:8502..."
python -m uvicorn server:app \
  --host 127.0.0.1 \
  --port 8502 \
  --proxy-headers \
  --forwarded-allow-ips '*' \
  2>&1 &

sleep 5

echo "Iniciando nginx en puerto ${PORT:-8080}..."
exec nginx -g 'daemon off;'
