#!/usr/bin/env python3
"""
重置 admin 密码
用法：python scripts/reset_admin.py
需要服务器权限（直接操作数据库）
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def main():
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.repositories import user_repo
    from app.services.auth_service import generate_initial_password

    print("=" * 50)
    print("  Z-CMDB Lite 管理员密码重置")
    print("=" * 50)

    with SessionLocal() as db:
        user = user_repo.get_by_username(db, "admin")
        if user is None:
            print("\n  错误：admin 用户不存在")
            sys.exit(1)

        new_password = generate_initial_password()
        new_hash = hash_password(new_password)
        user_repo.update_password(db, user, new_hash)
        db.commit()

        print(f"\n  用户名: admin")
        print(f"  新密码: {new_password}")
        print(f"\n  请登录后立即修改密码！")
        print("=" * 50)


if __name__ == "__main__":
    main()
