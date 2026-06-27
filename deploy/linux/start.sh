#!/usr/bin/env bash
# ============================================================
# Z-CMDB — Linux bare-metal start (venv + uvicorn)
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/../../backend"

PY="${PYTHON:-python3.12}"
HOST="${BIND_HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MIRROR="${PIP_MIRROR:-https://pypi.tuna.tsinghua.edu.cn/simple}"

command -v "$PY" >/dev/null 2>&1 || { echo "[ERROR] $PY not found. Install Python 3.12+ first."; exit 1; }

mkdir -p data

# ── Create venv if missing or incomplete (idempotent) ────────
if [ ! -f .venv/.ready ]; then
    echo "[INFO] Creating virtual environment ..."
    rm -rf .venv
    "$PY" -m venv .venv
    ./.venv/bin/pip install -U pip -i "$MIRROR"
    ./.venv/bin/pip install -r requirements.txt -i "$MIRROR"
    touch .venv/.ready
fi

# ── Generate .env if missing (idempotent) ────────────────────
if [ ! -f .env ]; then
    SECRET=$(./.venv/bin/python -c "import secrets;print(secrets.token_urlsafe(48))")
    cat > .env <<EOF
APP_ENV=production
DATABASE_URL=sqlite:///./data/cmdb.db
JWT_SECRET=$SECRET
CORS_ORIGINS=["http://localhost:$PORT"]
EOF
    echo "[INFO] Generated .env with random JWT_SECRET"
fi

# ── Migrate ──────────────────────────────────────────────────
echo "[INFO] Running database migrations ..."
./.venv/bin/alembic upgrade head

# ── Start ────────────────────────────────────────────────────
echo "[INFO] Starting Z-CMDB on $HOST:$PORT ..."
exec ./.venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT" --workers 1
