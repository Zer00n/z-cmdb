#!/usr/bin/env python3
"""
初始化数据库：执行 alembic upgrade head + 创建初始 admin 账号
用法：python scripts/init_db.py
"""
import subprocess
import sys
from pathlib import Path

# 确保在 backend 目录下执行
backend_dir = Path(__file__).parent.parent / "backend"


def main():
    print("=" * 50)
    print("  CMDB Lite 数据库初始化")
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
        print(f"  迁移失败: {result.stderr}")
        sys.exit(1)
    print("  迁移完成 ✓")

    # 2. 创建初始 admin（通过启动应用的 ensure_initial_admin）
    print("\n[2/2] 检查初始管理员账号...")
    sys.path.insert(0, str(backend_dir))
    from app.core.database import SessionLocal
    from app.services.auth_service import ensure_initial_admin

    with SessionLocal() as db:
        ensure_initial_admin(db)

    print("\n初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
