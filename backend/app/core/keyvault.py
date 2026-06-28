"""
运行态密钥持有 + 应用状态机（LOCKED / UNLOCKED）

PRD §4 状态机实现。模块级单例，进程内全局唯一：
  - LOCKED：DB 引擎未初始化，SessionLocal 为空。仅放行 /api/health、解锁、
    setup 接口与解锁页静态资源；其余路由由锁中间件返回 423。
  - UNLOCKED：DEK 在内存，引擎已建（database.init_engine），正常路由可用。

注意（PRD §1 非目标）：解锁后 DEK 与解密页驻留内存，能 dump 进程内存者可得
明文——这是本方案明确不防御的。lock() 时清除内存中的 DEK 引用（尽力清零，
Python 不可变对象无法保证真清零）。
"""
from __future__ import annotations

import threading
from enum import Enum


class VaultState(str, Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"


_lock = threading.Lock()
_state: VaultState = VaultState.LOCKED
# 运行态 DEK（hex 形式，用于 PRAGMA key）。仅 UNLOCKED 时非空。
_dek_hex: str | None = None
# 标记本次进程是否已对加密库执行过迁移（首次解锁后跑一次）
_migrated: bool = False


def unlock_with_dek(dek_hex: str) -> None:
    """记录运行态 DEK 并切到 UNLOCKED。由 key_service 在成功解开 DEK 后调用。"""
    global _state, _dek_hex
    with _lock:
        _dek_hex = dek_hex
        _state = VaultState.UNLOCKED


def lock() -> None:
    """清除运行态 DEK 并切回 LOCKED（尽力清零）。"""
    global _state, _dek_hex, _migrated
    with _lock:
        _dek_hex = None
        _state = VaultState.LOCKED
        _migrated = False


def is_unlocked() -> bool:
    return _state is VaultState.UNLOCKED


def current_state() -> VaultState:
    return _state


def get_dek_hex() -> str | None:
    """返回运行态 DEK（hex）。LOCKED 时为 None。

    供 database.init_engine 与 alembic/env.py 构造已 key 的引擎使用。
    """
    return _dek_hex


def mark_migrated() -> None:
    """标记加密库已完成迁移（首次解锁后调用，避免重复迁移）。"""
    global _migrated
    with _lock:
        _migrated = True


def has_migrated() -> bool:
    return _migrated
