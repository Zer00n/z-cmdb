"""
PEP 249 (DB-API 2.0) shim over `apsw`, so SQLAlchemy's ``pysqlite`` dialect can
drive an **encrypted** connection provided by ``apsw-sqlite3mc``.

Why this exists
---------------
``apsw`` is the most reliable source of SQLite3-Multiple-Ciphers encryption on
Windows (the ``sqlcipher3-binary`` package ships zero Windows wheels — see
``deploy/preflight_sqlcipher.py``). However ``apsw`` is *not* DB-API compliant
and its own ``dbapi2`` compatibility module was removed in 3.53. SQLAlchemy's
SQLite dialect requires a DB-API driver, so this module provides a focused
re-implementation covering exactly what the dialect uses.

Scope: only what SQLAlchemy 2.0's ``pysqlite`` dialect touches —
``paramstyle``/``sqlite_version`` module constants, ``connect()``,
``Connection.{cursor,commit,rollback,close,execute,executemany,isolation_level,...}``,
``Cursor.{execute,executemany,fetchone,fetchmany,fetchall,description,rowcount,lastrowid,close}``,
and the PEP 249 exception hierarchy mapped from ``apsw`` exceptions.

Transaction model
-----------------
``apsw`` connections are auto-commit by default (SQLite default). SQLAlchemy,
when given ``isolation_level = None`` (the value it sets itself on connect),
manages transactions by emitting ``BEGIN`` / ``COMMIT`` / ``ROLLBACK`` SQL.
We therefore stay out of transaction management and let those statements pass
through to SQLite unchanged.
"""
from __future__ import annotations

import threading
from typing import Any, Iterable, Sequence

import apsw

# ── Module-level DB-API constants ────────────────────────────────────────────

apsw_version: str = getattr(apsw, "__version__", "3.53.2.0")
sqlite_version: tuple[int, ...] = tuple(
    int(x) for x in apsw.sqlitelibversion().split(".")[:3]
)
sqlite_version_info: tuple[int, ...] = sqlite_version

# SQLite uses ? placeholders
paramstyle = "qmark"
# apsw connections can be used across threads (SQLite handles its own locking);
# we report level 1 (threads may share the module, not connections) which is
# what SQLAlchemy's sqlite dialect expects for safe pool behaviour.
threadsafety = 1


# ── PEP 249 exception hierarchy ──────────────────────────────────────────────


class Warning(Exception):  # noqa: N818 — PEP 249 mandates these names
    pass


class Error(Exception):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class DataError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


def _build_exc_map() -> dict[type, type[DatabaseError]]:
    """Map apsw exception classes → PEP 249 classes.

    apsw exposes one exception subclass per SQLite result code, all ultimately
    derived from ``apsw.SQLError`` (itself derived from ``apsw.Error``). We
    pick the most specific match available and fall back to DatabaseError.
    """
    # Specific overrides keyed by apsw class name suffix
    name_map = {
        "ConstraintError": IntegrityError,
        "IntegrityError": IntegrityError,
        "NotFoundError": OperationalError,
        "CannotOpenError": OperationalError,
        "BusyError": OperationalError,
        "LockedError": OperationalError,
        "IOError": OperationalError,
        "FullError": OperationalError,
        "ReadOnlyError": OperationalError,
        "CorruptError": DatabaseError,
        "NotADBError": DatabaseError,
        "SyntaxError": ProgrammingError,
        "TooBigError": DataError,
        "MismatchError": ProgrammingError,
        "BindingsError": ProgrammingError,
        "IncompleteError": ProgrammingError,
        "ExecTraceAbort": OperationalError,
        "ThreadingViolationError": InterfaceError,
        "ConnectionClosedError": InterfaceError,
        "CursorClosedError": InterfaceError,
    }
    mapping: dict[type, type[DatabaseError]] = {}
    for attr_name in dir(apsw):
        obj = getattr(apsw, attr_name, None)
        if isinstance(obj, type) and issubclass(obj, apsw.Error):
            key = name_map.get(attr_name, DatabaseError)
            mapping[obj] = key
    return mapping


_EXC_MAP = _build_exc_map()


def _translate(exc: BaseException) -> DatabaseError:
    """Convert an apsw exception into the closest PEP 249 class."""
    for cls, dbapi_cls in _EXC_MAP.items():
        if isinstance(exc, cls):
            return dbapi_cls(str(exc))
    return DatabaseError(str(exc))


# ── Cursor ───────────────────────────────────────────────────────────────────


class Cursor:
    """DB-API cursor wrapping an apsw cursor."""

    def __init__(self, connection: "Connection", apsw_cursor: Any) -> None:
        self.connection = connection
        self._cur = apsw_cursor
        self._desc: list[tuple] | None = None
        self.rowcount: int = -1
        self.lastrowid: Any = None
        self.arraysize: int = 1
        self._closed = False

    # ── description ──
    @property
    def description(self) -> list[tuple] | None:
        return self._desc

    def _desc_via_query_info(self, sql: str) -> list[tuple] | None:
        """空结果 fallback：apsw 对 0 行查询 execute 后立即 ExecutionComplete，
        ``get_description()`` 不可取。改用 ``apsw.ext.query_info`` 静态分析 SQL
        取列（不执行、不 complete），补齐标准 sqlite3「空结果亦有列描述」语义。
        """
        try:
            from apsw import ext
            qi = ext.query_info(self.connection._apsw, sql)
            full = qi.description
        except Exception:
            return None
        if full:
            return [(col[0], None, None, None, None, None, None) for col in full]
        return None

    def _refresh_desc(self, sql: str) -> None:
        try:
            full = self._cur.get_description()
            self._desc = (
                [(col[0], None, None, None, None, None, None) for col in full]
                if full else None
            )
        except apsw.ExecutionCompleteError:
            # 空结果：cursor 已 complete，fallback 到静态列分析
            self._desc = self._desc_via_query_info(sql)
        except Exception:
            self._desc = None

    # ── execution ──
    def execute(self, operation: str, parameters: Any = ()) -> "Cursor":  # noqa: A002
        if self._closed:
            raise _translate(apsw.CursorClosedError("cursor closed"))
        try:
            self._cur.execute(operation, parameters)
        except apsw.Error as exc:
            raise _translate(exc) from exc
        self._refresh_desc(operation)
        # For non-SELECT statements, derive rowcount + lastrowid
        if self._desc is None:
            self.rowcount = self.connection._apsw.changes()
            self.lastrowid = self.connection._apsw.last_insert_rowid()
        else:
            self.rowcount = -1
        return self

    def executemany(
        self,
        operation: str,
        seq_of_parameters: Iterable[Sequence[Any]],
    ) -> "Cursor":
        if self._closed:
            raise _translate(apsw.CursorClosedError("cursor closed"))
        try:
            self._cur.executemany(operation, list(seq_of_parameters))
        except apsw.Error as exc:
            raise _translate(exc) from exc
        self._refresh_desc(operation)
        self.rowcount = self.connection._apsw.changes() if self._desc is None else -1
        return self

    # ── fetching ──
    def fetchone(self) -> tuple | None:
        if self._closed:
            raise _translate(apsw.CursorClosedError("cursor closed"))
        try:
            row = next(self._cur, None)  # apsw cursors are iterators
        except apsw.Error as exc:
            raise _translate(exc) from exc
        return row

    def fetchmany(self, size: int | None = None) -> list[tuple]:
        n = size if size is not None else self.arraysize
        rows: list[tuple] = []
        for _ in range(n):
            row = self.fetchone()
            if row is None:
                break
            rows.append(tuple(row))
        return rows

    def fetchall(self) -> list[tuple]:
        rows: list[tuple] = []
        while True:
            row = self.fetchone()
            if row is None:
                break
            rows.append(tuple(row))
        return rows

    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None:
                return
            yield tuple(row)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._cur.close()
            except Exception:
                pass

    # no-op stubs required by DB-API
    def setinputsizes(self, sizes: Any) -> None:  # noqa: ARG002
        pass

    def setoutputsize(self, index: int, size: int | None = None) -> None:  # noqa: ARG002
        pass


# ── Connection ───────────────────────────────────────────────────────────────


class Connection:
    """DB-API connection wrapping an apsw.Connection.

    The underlying apsw connection is created WITHOUT a key. The caller is
    expected to apply the encryption PRAGMAs (``PRAGMA key`` must be the very
    first statement) before this connection is handed to SQLAlchemy. We expose
    ``raw_apsw()`` for that one-time setup.
    """

    def __init__(self, apsw_connection: apsw.Connection) -> None:
        self._apsw = apsw_connection
        # SQLAlchemy sets this to None on connect; mirror sqlite3 semantics.
        self.isolation_level: str | None = None
        self.row_factory: Any = None
        self.text_factory: Any = None
        self._cursors: list[Cursor] = []
        self._lock = threading.Lock()

    @property
    def in_transaction(self) -> bool:
        try:
            return bool(self._apsw.getautocommit() is False)
        except Exception:
            return False

    @property
    def total_changes(self) -> int:
        return self._apsw.total_changes()

    def cursor(self) -> Cursor:
        if self._apsw is None:
            raise _translate(apsw.ConnectionClosedError("connection closed"))
        try:
            apsw_cur = self._apsw.cursor()
        except apsw.Error as exc:
            raise _translate(exc) from exc
        cur = Cursor(self, apsw_cur)
        self._cursors.append(cur)
        return cur

    # sqlite3-style convenience methods (used by SQLAlchemy in a few paths)
    def execute(self, operation: str, parameters: Any = ()) -> Cursor:  # noqa: A002
        cur = self.cursor()
        cur.execute(operation, parameters)
        return cur

    def executemany(
        self,
        operation: str,
        seq_of_parameters: Iterable[Sequence[Any]],
    ) -> Cursor:
        cur = self.cursor()
        cur.executemany(operation, seq_of_parameters)
        return cur

    def commit(self) -> None:
        # apsw auto-commits; SQLAlchemy emits COMMIT SQL explicitly. Staying
        # out of the way avoids double-commit issues.
        try:
            self._apsw.execute("COMMIT")
        except apsw.Error:
            # No active transaction — ignore, mirroring sqlite3 commit() behaviour
            pass

    def rollback(self) -> None:
        try:
            self._apsw.execute("ROLLBACK")
        except apsw.Error:
            pass

    def close(self) -> None:
        for cur in self._cursors:
            cur.close()
        self._cursors.clear()
        if self._apsw is not None:
            try:
                self._apsw.close()
            except apsw.Error:
                pass
            self._apsw = None

    def interrupts_handler(self) -> None:  # pragma: no cover - parity helper
        self._apsw.interrupt()

    # ── sqlite3 extension methods used by SQLAlchemy's pysqlite dialect ──
    def create_function(self, name: str, narg: int, func: Any, *, deterministic: bool = False) -> None:
        """sqlite3-style ``create_function`` bridged to apsw ``create_scalar_function``.

        apsw passes SQL args directly to the callable (no leading context), so
        the semantics line up with sqlite3 exactly.
        """
        try:
            self._apsw.create_scalar_function(
                name, func, numargs=(narg if narg is not None and narg >= 0 else -1),
                deterministic=deterministic,
            )
        except apsw.Error as exc:
            raise _translate(exc) from exc

    def create_collation(self, name: str, func: Any) -> None:
        """sqlite3-style ``create_collation`` bridged to apsw."""
        try:
            self._apsw.create_collation(name, func)
        except apsw.Error as exc:
            raise _translate(exc) from exc


# ── connect() factory ────────────────────────────────────────────────────────


def connect(database: str, **kwargs: Any) -> Connection:  # noqa: ARG001
    """
    DB-API ``connect`` entry point.

    NOTE: ``apsw-sqlite3mc`` encryption requires ``PRAGMA key`` to be the very
    first statement on a connection, so a plain ``connect(path)`` cannot apply
    the key in time. Callers therefore pass a pre-built apsw connection via
    :func:`connect_apsw` (used by our engine creator) rather than this function.
    This stub exists only to satisfy the DB-API module contract and the
    SQLAlchemy dialect's module probing.
    """
    raise NotSupportedError(
        "Use connect_apsw(apsw_connection) so PRAGMA key can be applied first."
    )


def connect_apsw(apsw_connection: apsw.Connection) -> Connection:
    """Wrap an already-keyed apsw connection into a DB-API Connection."""
    return Connection(apsw_connection)
