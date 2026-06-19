"""
应用内 CLI 模块
提供 init-db 与 reset-admin 子命令，容器内统一使用：
    python -m app.cli init-db
    python -m app.cli reset-admin [--password <pwd>]
"""
import argparse
import subprocess
import sys


def _init_db() -> None:
    """执行 alembic upgrade head 并创建初始管理员"""
    print("=" * 50)
    print("  Z-CMDB Lite 数据库初始化")
    print("=" * 50)

    print("\n[1/2] 执行数据库迁移...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  迁移失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("  迁移完成")

    print("\n[2/2] 检查初始管理员账号...")
    from app.core.database import SessionLocal
    from app.services.auth_service import ensure_initial_admin

    with SessionLocal() as db:
        ensure_initial_admin(db)

    print("\n初始化完成！")
    print("=" * 50)


def _reset_admin(password: str | None = None) -> None:
    """重置 admin 密码，可选 --password；否则随机生成"""
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.repositories import user_repo
    from app.services.auth_service import (
        _check_password_policy,
        _persist_initial_password,
        generate_initial_password,
    )

    print("=" * 50)
    print("  Z-CMDB Lite 管理员密码重置")
    print("=" * 50)

    with SessionLocal() as db:
        user = user_repo.get_by_username(db, "admin")
        if user is None:
            print("\n  错误：admin 用户不存在，请先执行 init-db", file=sys.stderr)
            sys.exit(1)

        if password:
            if not _check_password_policy(password):
                print(
                    "\n  错误：密码不满足策略（>=8位，含大小写/数字/符号）",
                    file=sys.stderr,
                )
                sys.exit(1)
            new_password = password
        else:
            new_password = generate_initial_password()

        new_hash = hash_password(new_password)
        user_repo.update_password(db, user, new_hash)
        db.commit()

    _persist_initial_password(new_password)
    print("  密码重置成功，请使用新密码登录。")
    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Z-CMDB Lite 管理工具",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init-db", help="初始化数据库并创建初始管理员")
    rp = sub.add_parser("reset-admin", help="重置 admin 密码")
    rp.add_argument(
        "--password",
        default=None,
        help="指定新密码（留空则随机生成）",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "init-db":
        _init_db()
    elif args.command == "reset-admin":
        _reset_admin(args.password)


if __name__ == "__main__":
    main()
