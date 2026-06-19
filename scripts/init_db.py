#!/usr/bin/env python3
"""
初始化数据库（本地开发用）
用法：cd backend && python ../scripts/init_db.py
需要在 backend 目录、已激活 venv 的环境下运行。
"""
import subprocess
import sys
from pathlib import Path

# 本地开发：将 backend 目录加入 sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def main():
    print("=" * 50)
    print("  Z-CMDB Lite 数据库初始化")
    print("=" * 50)

    # 1. 执行 alembic upgrade head
    print("\n[1/2] 执行数据库迁移...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  迁移失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("  迁移完成")

    # 2. 创建初始 admin
    print("\n[2/2] 检查初始管理员账号...")
    from app.core.database import SessionLocal
    from app.services.auth_service import ensure_initial_admin

    with SessionLocal() as db:
        ensure_initial_admin(db)

    print("\n初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
