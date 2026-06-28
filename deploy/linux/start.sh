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

# 加密模型（PRD §6）：迁移移到解锁/setup 之后，启动前不再跑 alembic。
# 应用以 LOCKED 启动；首次访问走 setup，之后走解锁页。
# 无人值守：export CMDB_UNLOCK_PASSWORD=<管理员口令或恢复码> 后启动可自动解锁
#           （该变量绝不写入 .env，由运维临时注入）。
echo ""
echo "============================================================"
echo " Z-CMDB 启动中 ..."
echo " 访问地址: http://localhost:${PORT}"
echo "============================================================"
if [ ! -f data/keystore.json ]; then
    echo ""
    echo " [首次部署] 数据库尚未加密，需在浏览器完成初始化："
    echo "   1. 浏览器打开后进入 Setup 页面"
    echo "   2. 设置管理员用户名和口令（>=12位，含大小写+数字+特殊字符）"
    echo "   3. 系统会生成一次性恢复码 —— 务必立即离线保存！"
    echo "      恢复码是所有口令丢失时的唯一出路，丢失=数据不可读。"
    echo "   4. 初始化完成后自动进入正常模式"
else
    echo ""
    echo " [升级启动] 数据库已加密，需解锁后使用："
    echo "   - 浏览器打开后输入管理员口令解锁"
    echo "   - 或: CMDB_UNLOCK_PASSWORD=<口令> systemctl restart z-cmdb"
    echo ""
    echo " !! 重要：请确认已备份以下文件 !!"
    echo "   data/cmdb.db       （加密数据库）"
    echo "   data/keystore.json （密钥信封，丢失=数据不可读）"
    echo "   .env               （JWT 密钥配置）"
fi
if [ -n "${CMDB_UNLOCK_PASSWORD:-}" ]; then
    echo ""
    echo " [INFO] CMDB_UNLOCK_PASSWORD detected: will auto-unlock on startup"
fi
echo ""
echo "============================================================"

# ── Start ────────────────────────────────────────────────────
echo "[INFO] Starting Z-CMDB on $HOST:$PORT ..."
exec ./.venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT" --workers 1
