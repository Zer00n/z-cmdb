# ============================================================
# Z-CMDB Application Image (COPY code only, instant rebuild)
# ============================================================
FROM z-cmdb-base:0.6

WORKDIR /app/backend
COPY backend/ /app/backend/
COPY frontend/dist/ /app/backend/static/

EXPOSE 8000

# 加密模型（PRD §6）：迁移移到解锁/setup 之后，启动前不再跑 alembic。
# 容器以 LOCKED 启动；首次需经 setup 初始化，或通过 CMDB_UNLOCK_PASSWORD 自动解锁。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
