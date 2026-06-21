"""
In-app CLI module
Provides init-db and reset-admin subcommands for container usage:
    python -m app.cli init-db
    python -m app.cli reset-admin [--password <pwd>]
"""
import argparse
import subprocess
import sys


def _init_db() -> None:
    """Run alembic upgrade head and create initial admin"""
    print("=" * 50)
    print("  Z-CMDB Lite Database Initialization")
    print("=" * 50)

    print("\n[1/2] Running database migrations...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  Migration failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("  Migration complete")

    print("\n[2/2] Checking initial admin account...")
    from app.core.database import SessionLocal
    from app.services.auth_service import ensure_initial_admin

    with SessionLocal() as db:
        ensure_initial_admin(db)

    print("\nInitialization complete!")
    print("=" * 50)


def _reset_admin(password: str | None = None) -> None:
    """Reset admin password; use --password or generate a random one"""
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.repositories import user_repo
    from app.services.auth_service import (
        _check_password_policy,
        _persist_initial_password,
        generate_initial_password,
    )

    print("=" * 50)
    print("  Z-CMDB Lite Admin Password Reset")
    print("=" * 50)

    with SessionLocal() as db:
        user = user_repo.get_by_username(db, "admin")
        if user is None:
            print("\n  Error: admin user does not exist. Please run init-db first.", file=sys.stderr)
            sys.exit(1)

        if password:
            if not _check_password_policy(password):
                print(
                    "\n  Error: password does not meet policy (>=8 chars, must include upper/lowercase, digits, and symbols)",
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
    print("  Password reset successful. Please log in with the new password.")
    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Z-CMDB Lite admin tool",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init-db", help="Initialize database and create initial admin")
    rp = sub.add_parser("reset-admin", help="Reset admin password")
    rp.add_argument(
        "--password",
        default=None,
        help="Specify new password (randomly generated if omitted)",
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
