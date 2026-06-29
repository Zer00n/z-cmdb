#!/usr/bin/env bash
# ============================================================
# Z-CMDB Docker Release Script
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

APP_VERSION="${APP_VERSION:-0.6}"
BASE_IMAGE="z-cmdb-base:${APP_VERSION}"
APP_IMAGE="z-cmdb-app:${APP_VERSION}"

# ── Pre-flight: JWT_SECRET must be set ───────────────────────
if [ -z "${JWT_SECRET:-}" ]; then
    echo "[ERROR] JWT_SECRET environment variable is not set."
    echo "  Usage: JWT_SECRET=<your-secret> ./release.sh"
    exit 1
fi

# ── Build frontend if dist/index.html missing ────────────────
if [ ! -f ../../frontend/dist/index.html ]; then
    echo "[INFO] Frontend not built. Building ..."
    if command -v pnpm >/dev/null 2>&1; then
        (cd ../../frontend && pnpm install --frozen-lockfile && pnpm build)
    elif command -v npm >/dev/null 2>&1; then
        (cd ../../frontend && npm install && npm run build)
    else
        echo "[ERROR] Neither pnpm nor npm found. Install one and retry."
        exit 1
    fi
    echo "[INFO] Frontend built successfully."
fi

# ── Build base image (only when deps change) ─────────────────
echo "[1/4] Building base image ${BASE_IMAGE} ..."
docker build -f Dockerfile.base -t "${BASE_IMAGE}" ../..

# ── Optional: save for offline distribution ──────────────────
if [ "${OFFLINE:-0}" = "1" ]; then
    echo "[2/4] Saving base image for offline distribution ..."
    docker save "${BASE_IMAGE}" | gzip > "z-cmdb-base-${APP_VERSION}.tar.gz"
    echo "  Saved: z-cmdb-base-${APP_VERSION}.tar.gz"
    echo "  To load on target: docker load < z-cmdb-base-${APP_VERSION}.tar.gz"
else
    echo "[2/4] Skipping offline save (set OFFLINE=1 to enable)"
fi

# ── Build app image ──────────────────────────────────────────
echo "[3/4] Building app image ${APP_IMAGE} ..."
docker compose build

# ── Start ────────────────────────────────────────────────────
echo "[4/4] Starting containers ..."
mkdir -p data
docker compose up -d

echo ""
echo "============================================================"
echo " Z-CMDB ${APP_VERSION} is running at http://localhost:8000"
echo " Data volume: ./data → /app/backend/data"
echo "============================================================"
echo ""
echo " 首次部署：浏览器打开后完成 Setup（设密码 + 保存恢复码）"
echo " 升级部署：容器重启后需解锁，用管理员口令或："
echo "   CMDB_UNLOCK_PASSWORD=<口令> docker compose up -d"
echo ""
echo " !! 请确认已备份以下文件（bind mount 在宿主机 ./data/）!!"
echo "   ./data/cmdb.db       （加密数据库）"
echo "   ./data/keystore.json （密钥信封，丢失 = 数据不可读）"
echo "   ./data/.env          （JWT 密钥配置）"
echo ""
echo " 恢复码是所有口令丢失时的唯一出路，请妥善离线保管。"
echo "============================================================"
