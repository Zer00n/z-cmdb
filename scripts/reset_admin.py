#!/usr/bin/env python3
"""
重置 admin 密码（本地开发用）
用法：cd backend && python ../scripts/reset_admin.py
需要在 backend 目录、已激活 venv 的环境下运行。
"""
import sys
from pathlib import Path

# 本地开发：将 backend 目录加入 sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def main():
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.repositories import user_repo
    from app.services.auth_service import (
        _persist_initial_password,
        generate_initial_password,
    )

    print("=" * 50)
    print("  Z-CMDB Lite 管理员密码重置")
    print("=" * 50)

    with SessionLocal() as db:
        user = user_repo.get_by_username(db, "admin")
        if user is None:
            print("\n  错误：admin 用户不存在，请先执行 init_db.py")
            sys.exit(1)

        new_password = generate_initial_password()
        new_hash = hash_password(new_password)
        user_repo.update_password(db, user, new_hash)
        db.commit()

    _persist_initial_password(new_password)
    print("  密码重置成功，请使用新密码登录。")
    print("=" * 50)


if __name__ == "__main__":
    main()
