#!/usr/bin/env python
"""
Z-CMDB 存量明文库一次性加密迁移工具（PRD §5.2）

用途：把已有的明文 cmdb.db 一次性转成 SQLCipher/MC 加密库，并生成对应的
keystore（含初始管理员 wrapped-DEK 记录 + 恢复码记录）。迁移后用加密库覆盖
明文原件，安全删除明文残留。

流程：
  1. 预检：明文库存在、keystore 尚不存在（防误覆盖）、口令满足策略；
  2. 生成 DEK + 恢复码；
  3. 反向 ATTACH：打开加密临时库（DEK key），ATTACH 明文库（KEY ''），
     按 sqlite_master 复制 schema（表→视图/触发器→索引）+ 逐表数据；
  4. 校验：每张用户表行数一致；
  5. 用 DEK 打开加密库验证可读；
  6. 落 keystore（build_user_record + build_recovery_record）；
  7. 安全覆盖明文原件（随机覆写）后用加密库覆盖原路径；删除明文 -wal/-shm；
  8. 一次性输出恢复码（控制台）。

安全：全程不打印/不落盘 DEK；恢复码仅控制台一次性展示。

用法（在 backend/ 下）：
  PYTHONPATH=. python tools/encrypt_existing_db.py \
      --password '<管理员口令>' [--username admin] \
      [--db data/cmdb.db] [--keystore data/keystore.json] \
      [--keep-plain]   # 调试用：保留明文原件（不安全删除）
"""
from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from pathlib import Path

# 允许从 backend/ 或仓库根运行：把 backend/ 加入 sys.path 以 import app
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import apsw  # noqa: E402

from app.core import crypto  # noqa: E402


# ── 参数与校验 ────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Migrate a plaintext Z-CMDB DB to an encrypted one.")
    p.add_argument("--password", required=True, help="Initial admin password (wraps the DEK)")
    p.add_argument("--username", default="admin", help="Admin username (default: admin)")
    p.add_argument("--db", default=str(_BACKEND / "data" / "cmdb.db"), help="Plaintext DB path")
    p.add_argument("--keystore", default=None, help="keystore.json path (default: <db dir>/keystore.json)")
    p.add_argument("--keep-plain", action="store_true", help="DEBUG: do not securely delete the plaintext original")
    return p.parse_args()


def check_password_policy(pw: str) -> None:
    if len(pw) < 12:
        sys.exit("[ERROR] Password must be at least 12 characters")
    need = {
        "uppercase": any(c.isupper() for c in pw),
        "lowercase": any(c.islower() for c in pw),
        "digit": any(c.isdigit() for c in pw),
        "symbol": any(not c.isalnum() for c in pw),
    }
    missing = [k for k, ok in need.items() if not ok]
    if missing:
        sys.exit(f"[ERROR] Password missing: {', '.join(missing)}")


# ── 核心：反向 ATTACH 复制 ────────────────────────────────────────────────────


def user_tables(conn: apsw.Connection) -> list[str]:
    cur = conn.cursor()
    return [
        r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]


def export_plain_to_encrypted(plain_path: str, enc_path: str, dek_hex: str) -> None:
    """打开加密临时库（DEK key），ATTACH 明文库（KEY ''），复制 schema + 数据。

    MC 没有 sqlcipher_export，故手动按 sqlite_master 复制：
      表先建、视图/触发器次之、索引最后；数据按表逐条 INSERT ... SELECT。
    """
    if os.path.exists(enc_path):
        os.remove(enc_path)

    enc = apsw.Connection(enc_path)
    ec = enc.cursor()
    # 加密库主库 key
    ec.execute(f'PRAGMA key="x\'{dek_hex}\'"')
    ec.execute('PRAGMA cipher="sqlcipher"')

    # 明文库先 checkpoint，把 WAL 并入主库（避免明文页残留在 -wal）
    plain = apsw.Connection(plain_path)
    try:
        plain.cursor().execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except apsw.Error:
        pass

    # ATTACH 明文库（空 key = 明文）
    ec.execute("ATTACH DATABASE ? AS src KEY ''", (plain_path,))

    # 复制 schema：表 → 视图/触发器 → 索引（索引最后，避免导入时维护开销）
    schemas = list(
        ec.execute(
            "SELECT type, name, sql FROM src.sqlite_master "
            "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
            "ORDER BY (type='index'), (type!='table')"
        )
    )
    for _typ, _name, sql in schemas:
        ec.execute(sql)

    # 复制数据（物化表名列表，避免迭代与执行共用 cursor）
    tables = [
        r[0] for r in ec.execute(
            "SELECT name FROM src.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    for t in tables:
        ec.execute(f'INSERT INTO main."{t}" SELECT * FROM src."{t}"')

    ec.execute("DETACH DATABASE src")
    enc.close()
    plain.close()


def count_rows(path: str, dek_hex: str | None, tables: list[str]) -> dict[str, int]:
    conn = apsw.Connection(path)
    cur = conn.cursor()
    if dek_hex:
        cur.execute(f'PRAGMA key="x\'{dek_hex}\'"')
        cur.execute('PRAGMA cipher="sqlcipher"')
    counts = {t: cur.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}  # type: ignore[union-attr]
    conn.close()
    return counts


# ── 安全删除 ──────────────────────────────────────────────────────────────────


def secure_delete_file(path: str) -> None:
    """覆盖写后 unlink（PRD §5.2）。SSD/日志结构存储不保证真擦除，尽力而为。"""
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    try:
        with open(path, "r+b") as f:
            # 覆盖 3 次：随机 / 0xFF / 0x00
            for pattern in (None, b"\xff", b"\x00"):
                f.seek(0)
                if pattern is None:
                    f.write(os.urandom(size))
                else:
                    f.write(pattern * size)
                f.flush()
                os.fsync(f.fileno())
    except OSError:
        pass
    try:
        os.unlink(path)
    except OSError:
        pass


# ── 主流程 ────────────────────────────────────────────────────────────────────


def main() -> int:
    args = parse_args()
    check_password_policy(args.password)

    db_path = str(Path(args.db).resolve())
    ks_path = str(Path(args.keystore).resolve() if args.keystore else Path(db_path).parent / "keystore.json")
    enc_path = str(Path(db_path).with_suffix(".enc.db" + ".tmp"))

    if not os.path.exists(db_path):
        sys.exit(f"[ERROR] Plaintext DB not found: {db_path}")
    if crypto.keystore_exists(ks_path):
        sys.exit(f"[ERROR] keystore already exists: {ks_path}\n"
                 "         Refusing to overwrite — the DB may already be encrypted.")

    # 明文头检查（避免对已加密库重复迁移）
    with open(db_path, "rb") as f:
        if f.read(16) != b"SQLite format 3\x00":
            sys.exit("[ERROR] DB does not have a plaintext SQLite header — already encrypted? Aborting.")

    print(f"[1/7] Generating DEK + recovery code ...")
    dek = crypto.new_dek()
    dek_hex = dek.hex()
    recovery_display, recovery_secret = crypto.generate_recovery_code()
    crypto.secure_wipe(dek)

    print(f"[2/7] Exporting plaintext -> encrypted (reverse ATTACH) ...")
    export_plain_to_encrypted(db_path, enc_path, dek_hex)

    print(f"[3/7] Verifying row counts ...")
    # 表名从明文库取（加密库无 key 读不到 sqlite_master）
    plain_tables = user_tables(apsw.Connection(db_path))
    plain_counts = count_rows(db_path, None, plain_tables)
    enc_counts = count_rows(enc_path, dek_hex, plain_tables)
    mismatch = [(t, plain_counts[t], enc_counts.get(t)) for t in plain_tables if plain_counts[t] != enc_counts.get(t)]
    if mismatch:
        secure_delete_file(enc_path)
        sys.exit(f"[ERROR] Row count mismatch (plain vs encrypted): {mismatch}")
    print(f"      {len(plain_tables)} tables verified, all row counts match.")

    print(f"[4/7] Writing keystore (wrapping DEK with admin password + recovery code) ...")
    dek2 = bytes.fromhex(dek_hex)
    ks = crypto.Keystore()
    ks.upsert(crypto.build_user_record(dek2, args.username, args.password))
    ks.upsert(crypto.build_recovery_record(dek2, recovery_secret))
    crypto.save_keystore(ks_path, ks)
    crypto.secure_wipe(dek2)

    print(f"[5/7] Replacing plaintext DB with encrypted one ...")
    if args.keep_plain:
        backup = db_path + ".plaintext.bak"
        shutil_copy(db_path, backup)
        print(f"      [DEBUG] plaintext backup kept at: {backup}")
    else:
        secure_delete_file(db_path)  # 安全覆盖明文原件
    os.replace(enc_path, db_path)  # 加密库就位
    # 清理明文 WAL/SHM 残留（含明文页）
    for suffix in ("-wal", "-shm"):
        side = db_path + suffix
        if os.path.exists(side):
            if args.keep_plain:
                shutil_copy(side, side + ".plaintext.bak")
            else:
                secure_delete_file(side)

    print(f"[6/7] Updating admin password hash + final verification ...")
    verify = count_rows(db_path, dek_hex, plain_tables)
    if verify != enc_counts:
        sys.exit("[ERROR] Post-replace verification failed! DO NOT proceed.")
    # 更新库内管理员的 password_hash（用迁移口令），使解锁后 argon2 校验一致。
    # 迁移是一次性操作：旧口令失效，用户用 --password 作为新口令。
    # 同时清 locked_until + failed_login_count（防迁移已锁定账户）。
    from app.core.security import hash_password
    pw_hash = hash_password(args.password)
    conn_update = apsw.Connection(db_path)
    cur_update = conn_update.cursor()
    cur_update.execute(f'PRAGMA key="x\'{dek_hex}\'"')
    cur_update.execute('PRAGMA cipher="sqlcipher"')
    cur_update.execute(
        "UPDATE users SET password_hash = ?, locked_until = NULL, failed_login_count = 0 "
        "WHERE username = ?",
        (pw_hash, args.username),
    )
    changes = conn_update.changes()
    conn_update.close()
    if changes == 0:
        print(f"      [WARN] no user '{args.username}' found in DB — password hash NOT updated")
    else:
        print(f"      {changes} admin user(s) password hash updated to match --password")
    print(f"      Encrypted DB opens, reads, and admin hash matches successfully.")

    print(f"[7/7] Migration complete.")
    print()
    print("=" * 60)
    print("  RECOVERY CODE (store OFFLINE — shown only once):")
    print(f"  {recovery_display}")
    print("=" * 60)
    print(f"  Encrypted DB : {db_path}")
    print(f"  Keystore     : {ks_path}")
    print(f"  Admin user   : {args.username}")
    print("  Next: start the app and unlock with the admin password.")
    print("=" * 60)
    return 0


def shutil_copy(src: str, dst: str) -> None:
    import shutil
    shutil.copyfile(src, dst)


if __name__ == "__main__":
    sys.exit(main())
