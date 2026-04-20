#!/bin/bash
set -euo pipefail

ROOT="/Users/owenlau/projects/data_analyze"
API_HOST="127.0.0.1"
API_PORT="8000"
WEB_HOST="127.0.0.1"
WEB_PORT="3000"
PYTHON_BIN="$ROOT/.venv/bin/python"

cd "$ROOT"

if [ ! -x "$PYTHON_BIN" ]; then
  python3 -m venv "$ROOT/.venv"
fi

"$PYTHON_BIN" -m pip install -r "$ROOT/requirements.txt"

echo "启动 FastAPI 分析服务..."
"$PYTHON_BIN" -m uvicorn src.webapi.app:app --host "$API_HOST" --port "$API_PORT" &
API_PID=$!

cleanup() {
  if kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "启动 Next.js 前端..."
cd "$ROOT/web"
if [ ! -d node_modules ]; then
  npm install
fi

NEXT_PUBLIC_API_BASE_URL="http://$API_HOST:$API_PORT" npm run dev -- --hostname "$WEB_HOST" --port "$WEB_PORT"
