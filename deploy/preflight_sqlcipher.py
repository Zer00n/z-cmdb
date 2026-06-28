#!/usr/bin/env python
"""
Z-CMDB SQLite 静态加密 — P0 驱动预检（apsw-sqlite3mc 方案）

PRD §3.3 / 操作指南任务 1 的回退情形已发生：``sqlcipher3-binary`` 在 PyPI 上
**没有任何 Windows (win_amd64) wheel**（0.6.0 仅有 manylinux），桌面嵌入式打包
（``--only-binary=:all:``）无法落地。因此本方案改用 ``apsw-sqlite3mc``——
APSW 编译了 SQLite3 Multiple Ciphers 的自包含分发包，Windows 全平台 wheel 覆盖
（cp312/cp313/cp314 win_amd64/arm64/win32 + manylinux）。

本脚本在「当前运行平台」实测验证：
  1) apsw-sqlite3mc 已安装且可 import；
  2) Multiple Ciphers 加密真正生效（不是静默忽略 PRAGMA key）；
  3) raw key 创建加密库 → 错 key 被拒 → 对 key 读回 → 无 key 被拒 → 文件头是密文；
  4) 目标打包平台 (cp312 / win_amd64) 的 wheel 在 PyPI 上存在（桌面打包前提）。

用法：python deploy/preflight_sqlcipher.py
退出码 0 = 全部通过（GO）；非 0 = 有项失败（NO-GO，按文档要求停下排查）。

注意：本脚本自包含，不依赖项目 app 包，可在部署前/打包前单独运行。
"""
from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
import urllib.request

CHECKS: list[tuple[str, bool, str]] = []  # (name, passed, detail)


def record(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append((name, ok, detail))
    flag = "OK  " if ok else "FAIL"
    line = f"[{flag}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    return ok


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ── 1) import + 版本 ─────────────────────────────────────────────────────────


def check_import() -> bool:
    try:
        import apsw  # noqa: F401
    except Exception as exc:  # pragma: no cover
        record("import apsw", False, f"{type(exc).__name__}: {exc}")
        return False
    try:
        ver = apsw.apswversion()  # type: ignore[attr-defined]
    except Exception:
        ver = getattr(apsw, "__version__", "?")
    sqlite_ver = apsw.sqlitelibversion()
    record("import apsw", True, f"apsw={ver} sqlite={sqlite_ver}")
    return True


# ── 2) Multiple Ciphers 真正生效 ─────────────────────────────────────────────


def _raw_key_open(path: str, hexkey: str):
    """打开加密库并应用 raw key（PRAGMA key 必须第一条）。"""
    import apsw

    conn = apsw.Connection(path)
    cur = conn.cursor()
    cur.execute(f'PRAGMA key="x\'{hexkey}\'"')  # raw key，跳过 KDF
    cur.execute('PRAGMA cipher="sqlcipher"')  # 显式 MC 的 sqlcipher 算法
    cur.close()
    return conn


def check_encryption() -> bool:
    import apsw

    dek = bytes.fromhex("00112233445566778899aabbccddeeff" * 2)  # 32B
    hexkey = dek.hex()
    wrong = ("ff" * 32)
    tmp = tempfile.mkdtemp(prefix="preflight_")
    enc_db = os.path.join(tmp, "preflight_enc.db")

    ok_all = True

    # 2a) create + write
    try:
        if os.path.exists(enc_db):
            os.remove(enc_db)
        conn = _raw_key_open(enc_db, hexkey)
        cur = conn.cursor()
        cur.execute("CREATE TABLE probe(id INTEGER PRIMARY KEY, secret TEXT)")
        cur.execute("INSERT INTO probe(secret) VALUES('classified')")
        conn.close()
        create_ok = os.path.exists(enc_db)
    except Exception as exc:  # pragma: no cover
        record("create encrypted DB", False, f"{type(exc).__name__}: {exc}")
        return False
    ok_all &= record("create encrypted DB (raw key + write)", create_ok)
    if not create_ok:
        return False

    # 2b) wrong key rejected
    try:
        conn = _raw_key_open(enc_db, wrong)
        list(conn.cursor().execute("SELECT count(*) FROM sqlite_master"))
        wk_ok, wk_detail = False, "wrong key was NOT rejected — encryption ineffective"
        conn.close()
    except apsw.NotADBError:
        wk_ok, wk_detail = True, "apsw.NotADBError (file is not a database)"
    except Exception as exc:  # pragma: no cover
        wk_ok, wk_detail = False, f"{type(exc).__name__}: {exc}"
    ok_all &= record("wrong key rejected", wk_ok, wk_detail)

    # 2c) correct key reads back
    try:
        conn = _raw_key_open(enc_db, hexkey)
        row = list(conn.cursor().execute("SELECT secret FROM probe WHERE id=1"))
        conn.close()
        rk_ok = row == [("classified",)]
        rk_detail = "read back" if rk_ok else f"unexpected: {row}"
    except Exception as exc:  # pragma: no cover
        rk_ok, rk_detail = False, f"{type(exc).__name__}: {exc}"
    ok_all &= record("correct key reads data", rk_ok, rk_detail)

    # 2d) no key rejected
    try:
        conn = apsw.Connection(enc_db)
        list(conn.cursor().execute("SELECT count(*) FROM sqlite_master"))
        nk_ok, nk_detail = False, "no key was NOT rejected — encryption ineffective"
        conn.close()
    except apsw.NotADBError:
        nk_ok, nk_detail = True, "apsw.NotADBError"
    except Exception as exc:  # pragma: no cover
        nk_ok, nk_detail = False, f"{type(exc).__name__}: {exc}"
    ok_all &= record("no-key open rejected", nk_ok, nk_detail)

    # 2e) file header is ciphertext
    try:
        with open(enc_db, "rb") as f:
            header = f.read(16)
        h_ok = header != b"SQLite format 3\x00"
        h_detail = f"first bytes={header[:8].hex()}" if h_ok else "PLAINTEXT header!"
    except Exception as exc:  # pragma: no cover
        h_ok, h_detail = False, f"{type(exc).__name__}: {exc}"
    ok_all &= record("file header is ciphertext", h_ok, h_detail)

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return ok_all


# ── 3) 目标打包平台 wheel 可用性 ──────────────────────────────────────────────


def check_target_wheel() -> bool:
    """桌面嵌入式打包用 Python 3.12 / win_amd64（见 deploy/windows/python312._pth）。
    确认 apsw-sqlite3mc 在 PyPI 上有该 wheel（pip --only-binary 能装上）。
    """
    targets = [
        ("cp312", "win_amd64"),   # 桌面嵌入式打包（关键）
        ("cp314", "win_amd64"),   # 当前开发机
    ]
    try:
        with urllib.request.urlopen(
            "https://pypi.org/pypi/apsw-sqlite3mc/json", timeout=20
        ) as resp:
            data = json.load(resp)
    except Exception as exc:  # pragma: no cover
        record("PyPI wheel availability", False, f"network error: {exc}")
        return False

    version = data["info"]["version"]
    files = data["releases"][version]
    details = []
    all_ok = True
    for abi, plat in targets:
        found = any(
            f"cp{abi[2:]}" in f["filename"] and plat in f["filename"]
            for f in files
        )
        details.append(f"{abi}/{plat}={'yes' if found else 'MISSING'}")
        all_ok &= found
    record(f"PyPI wheels (apsw-sqlite3mc {version})", all_ok, ", ".join(details))
    return all_ok


# ── 4) SQLAlchemy 集成路径（适配器存在性 + 加密 ORM 往返）──────────────────────


def check_sqlalchemy_integration() -> bool:
    """验证 DBAPI 适配器能驱动 SQLAlchemy 完成加密 ORM 往返。
    失败不阻断（因为适配器属本项目代码，部署机若未装 app 包则跳过），仅提示。
    """
    try:
        from sqlalchemy import Column, Integer, String, create_engine, select
        from sqlalchemy.orm import DeclarativeBase, Session

        # 适配器在 app 包内；部署预检若不在 backend cwd 下则跳过此项
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        import app.core._apsw_dbapi as dbapi  # noqa: F401
        import apsw
    except Exception as exc:
        record("SQLAlchemy integration via _apsw_dbapi", True,
               f"skipped (app package not on path: {type(exc).__name__})")
        return True

    dek = bytes.fromhex("00112233445566778899aabbccddeeff" * 2)
    hexkey = dek.hex()
    tmp = tempfile.mkdtemp(prefix="preflight_sa_")
    db_path = os.path.join(tmp, "sa_enc.db")

    def creator():
        conn = apsw.Connection(db_path)
        cur = conn.cursor()
        cur.execute(f'PRAGMA key="x\'{hexkey}\'"')
        cur.execute('PRAGMA cipher="sqlcipher"')
        cur.close()
        return dbapi.connect_apsw(conn)

    class B(DeclarativeBase):
        pass

    # 用 Column API 避免 Mapped 字符串注解在函数作用域解析失败
    class T(B):
        __tablename__ = "t"
        id = Column(Integer, primary_key=True)
        v = Column(String(32))

    try:
        engine = create_engine("sqlite://", module=dbapi, creator=creator)
        B.metadata.create_all(engine)
        with Session(engine) as s:
            s.add(T(v="round-trip"))
            s.commit()
            got = s.execute(select(T)).scalar_one()
            assert got.v == "round-trip"
        engine.dispose()
        ok, detail = True, "encrypted ORM round-trip"
    except Exception as exc:  # pragma: no cover
        ok, detail = False, f"{type(exc).__name__}: {exc}"

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return record("SQLAlchemy integration via _apsw_dbapi", ok, detail)


def main() -> int:
    section("platform")
    print(f"  python: {sys.version.split()[0]} ({platform.system()} {platform.machine()})")
    print(f"  impl:   {platform.python_implementation()}")

    section("step 1 — driver import")
    a = check_import()

    section("step 2 — encryption effectiveness (Multiple Ciphers)")
    b = check_encryption() if a else False

    section("step 3 — target packaging wheels on PyPI")
    c = check_target_wheel()

    section("step 4 — SQLAlchemy integration (advisory)")
    d = check_sqlalchemy_integration() if a else False

    section("verdict")
    go = a and b and c
    print(f"  {'GO  — driver viable' if go else 'NO-GO — resolve above failures'}")
    print(f"  (step 4 advisory: {'ok' if d else 'see above'})")
    return 0 if go else 1


if __name__ == "__main__":
    sys.exit(main())
