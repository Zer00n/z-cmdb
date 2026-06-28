"""
SQLite 静态加密 — 信封加密核心（envelope）

PRD §3 密码学设计实现。两层密钥：
  - DEK (Data Encryption Key)：32 字节随机数，SQLCipher/MC 的真实库密钥，
    永不明文落盘，解锁后仅驻留内存。
  - KEK (Key Encryption Key)：管理员口令经 Argon2id 派生（每记录独立 salt），
    用 AES-256-GCM 包裹/解包 DEK。
  - 每个「有解锁权限的管理员」一条 wrapped-DEK 记录，外加一条恢复码记录，
    全部存于加密库之外的 keystore 文件。

安全约束（不得违反，见操作指南 §0）：
  - keystore 只存密文 + salt + nonce + 参数，单独泄露无害。
  - 信封层只用 cryptography.AESGCM + argon2-cffi.hash_secret_raw，不自研密码学。
  - AES-GCM nonce 每次 wrap 重新生成 12 字节，永不复用。
  - DEK / 口令 / 恢复码绝不进日志、绝不落盘明文。
"""
from __future__ import annotations

import base64
import json
import logging
import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# ── KDF 参数（Argon2id，记入 keystore 以便未来调参）───────────────────────────
# 与 app/core/security.py 的密码哈希参数一致；KEK 输出 32 字节。
ARGON = dict(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32)

# AES-256-GCM：12 字节 nonce（标准），32 字节密钥
_NONCE_LEN = 12
_DEK_LEN = 32
_KEK_LEN = 32

KEYSTORE_VERSION = 1
KDF_TYPE = "argon2id"
CIPHER = "AES-256-GCM"

# keystore 中可编址的固定 kid
RECOVERY_KID = "recovery"


def _user_kid(username: str) -> str:
    """管理员记录按 user:<username> 编址（PRD §3.5）。"""
    return f"user:{username}"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 纯密码学函数 ──────────────────────────────────────────────────────────────


def new_dek() -> bytes:
    """生成 32 字节随机 DEK（SQLCipher/MC raw key）。"""
    return secrets.token_bytes(_DEK_LEN)


def derive_kek(secret: str, salt: bytes) -> bytes:
    """Argon2id 从口令 + salt 派生 32 字节 KEK。"""
    return hash_secret_raw(
        secret=secret.encode("utf-8"),
        salt=salt,
        time_cost=ARGON["time_cost"],
        memory_cost=ARGON["memory_cost"],
        parallelism=ARGON["parallelism"],
        hash_len=ARGON["hash_len"],
        type=Type.ID,
    )


def wrap_dek(dek: bytes, kek: bytes) -> tuple[bytes, bytes]:
    """用 KEK 经 AES-256-GCM 包裹 DEK。返回 (nonce, ciphertext)。

    nonce 每次重新生成 12 字节，永不复用（操作指南 §0.3）。
    """
    if len(kek) != _KEK_LEN:
        raise ValueError(f"KEK must be {_KEK_LEN} bytes, got {len(kek)}")
    if len(dek) != _DEK_LEN:
        raise ValueError(f"DEK must be {_DEK_LEN} bytes, got {len(dek)}")
    nonce = secrets.token_bytes(_NONCE_LEN)
    ct = AESGCM(kek).encrypt(nonce, dek, associated_data=None)
    return nonce, ct


def unwrap_dek(ct: bytes, kek: bytes, nonce: bytes) -> bytes:
    """用 KEK 经 AES-256-GCM 解包 DEK。口令错误 → GCM 校验失败抛 InvalidTag。

    调用方应捕获 InvalidTag 并返回统一的「解锁失败」，不泄露原因。
    """
    return AESGCM(kek).decrypt(nonce, ct, associated_data=None)


def new_salt() -> bytes:
    """每条记录独立的 Argon2id salt（16 字节）。"""
    return secrets.token_bytes(16)


def secure_wipe(buf) -> None:
    """尽力清零内存中的密钥缓冲。

    Python 不可变 bytes 无法真正清零（可能被解释器复制/驻留），这里仅对
    bytearray/mutable 序列做原地覆盖，作为「尽力而为」的防护。
    真正的内存清零需配合运行态加固（超出本期范围，见 PRD §1 非目标）。
    """
    try:
        for i in range(len(buf)):
            buf[i] = 0
    except Exception:  # noqa: BLE001 — 不可变对象清零失败属预期
        pass


# ── 恢复码 ────────────────────────────────────────────────────────────────────


def generate_recovery_code() -> tuple[str, str]:
    """生成一次性恢复码：32 字节高熵 → base32 分组，便于人工抄录。

    返回 (展示用分组串, 派生 KEK 用的归一化 secret)。
    归一化 secret == normalize_recovery_code(展示串)，确保 build/unwrap 两端
    用同一字符串派生 KEK；展示串仅用于人工抄录，比对时再 normalize。
    """
    raw = secrets.token_bytes(32)
    # base32 全大写、去掉填充，按 4 字符分组
    b32 = base64.b32encode(raw).decode("ascii").rstrip("=")
    grouped = "-".join(b32[i : i + 4] for i in range(0, len(b32), 4))
    normalized = normalize_recovery_code(grouped)
    return grouped, normalized


def normalize_recovery_code(code: str) -> str:
    """归一化恢复码：去连字符/空格、转大写，便于用户输入比对。"""
    return code.replace("-", "").replace(" ", "").upper()


# ── keystore 数据结构 ─────────────────────────────────────────────────────────


@dataclass
class KeyRecord:
    kid: str                 # user:<username> | recovery
    label: str               # 展示名
    salt: bytes              # Argon2id salt（明文无害）
    nonce: bytes             # AES-GCM nonce（明文无害）
    wrapped_dek: bytes       # AES-GCM 密文（明文无害：无 KEK 解不开）
    created_at: str = field(default_factory=_now_iso)
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "kid": self.kid,
            "label": self.label,
            "salt": _b64(self.salt),
            "nonce": _b64(self.nonce),
            "wrapped_dek": _b64(self.wrapped_dek),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KeyRecord":
        return cls(
            kid=d["kid"],
            label=d.get("label", d["kid"]),
            salt=_unb64(d["salt"]),
            nonce=_unb64(d["nonce"]),
            wrapped_dek=_unb64(d["wrapped_dek"]),
            created_at=d.get("created_at", _now_iso()),
            updated_at=d.get("updated_at"),
        )


@dataclass
class Keystore:
    version: int = KEYSTORE_VERSION
    kdf: dict = field(default_factory=lambda: {
        "type": KDF_TYPE,
        "memory_cost": ARGON["memory_cost"],
        "time_cost": ARGON["time_cost"],
        "parallelism": ARGON["parallelism"],
        "hash_len": ARGON["hash_len"],
    })
    cipher: str = CIPHER
    records: list[KeyRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "kdf": dict(self.kdf),
            "cipher": self.cipher,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Keystore":
        return cls(
            version=d.get("version", KEYSTORE_VERSION),
            kdf=d.get("kdf", {}),
            cipher=d.get("cipher", CIPHER),
            records=[KeyRecord.from_dict(r) for r in d.get("records", [])],
        )

    # ── 记录 CRUD（按 kid）──
    def get(self, kid: str) -> Optional[KeyRecord]:
        for r in self.records:
            if r.kid == kid:
                return r
        return None

    def upsert(self, record: KeyRecord) -> None:
        """新增或替换一条记录（同 kid 覆盖）。"""
        for i, r in enumerate(self.records):
            if r.kid == record.kid:
                record.created_at = r.created_at  # 保留首次创建时间
                record.updated_at = _now_iso()
                self.records[i] = record
                return
        self.records.append(record)

    def remove(self, kid: str) -> bool:
        before = len(self.records)
        self.records = [r for r in self.records if r.kid != kid]
        return len(self.records) < before

    def list_user_kids(self) -> list[str]:
        """所有管理员 kid（不含 recovery）。"""
        return [r.kid for r in self.records if r.kid != RECOVERY_KID]


# ── keystore 原子读写 ─────────────────────────────────────────────────────────


def load_keystore(path: str | Path) -> Keystore:
    """读取 keystore.json。文件不存在视为 needs_setup（调用方判断）。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"keystore not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return Keystore.from_dict(data)


def keystore_exists(path: str | Path) -> bool:
    return Path(path).exists()


def save_keystore(path: str | Path, ks: Keystore) -> None:
    """原子写：写临时文件后 os.replace，避免崩溃留下半截文件。

    权限收紧为 0600（仅属主读写，POSIX）；Windows 上 chmod 忽略但无害。
    keystore 内容均为密文，临时文件短暂存在无害（操作指南 §0.2）。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    payload = json.dumps(ks.to_dict(), indent=2, ensure_ascii=False)
    # 写临时文件并 fsync，确保崩溃后要么完整要么不存在
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(str(tmp), str(p))


# ── 高层便捷封装 ──────────────────────────────────────────────────────────────


def build_user_record(dek: bytes, username: str, password: str) -> KeyRecord:
    """用某管理员口令派生 KEK 并包裹 DEK → 一条 keystore 记录。"""
    salt = new_salt()
    kek = derive_kek(password, salt)
    nonce, wrapped = wrap_dek(dek, kek)
    secure_wipe(kek)  # KEK 用完即清
    return KeyRecord(
        kid=_user_kid(username),
        label=username,
        salt=salt,
        nonce=nonce,
        wrapped_dek=wrapped,
    )


def build_recovery_record(dek: bytes, recovery_secret: str) -> KeyRecord:
    """用恢复码派生 KEK 并包裹 DEK → recovery 记录。"""
    salt = new_salt()
    kek = derive_kek(recovery_secret, salt)
    nonce, wrapped = wrap_dek(dek, kek)
    secure_wipe(kek)
    return KeyRecord(
        kid=RECOVERY_KID,
        label="recovery",
        salt=salt,
        nonce=nonce,
        wrapped_dek=wrapped,
    )


def unwrap_for_user(ks: Keystore, username: str, password: str) -> bytes:
    """按 user:<username> 取记录，口令派生 KEK 解包 DEK。

    失败（记录不存在或口令错）统一抛 InvalidTag，调用方应转为通用错误。
    """
    rec = ks.get(_user_kid(username))
    if rec is None:
        # 记录不存在也抛 InvalidTag，避免用户名枚举（操作指南 §4.2）
        raise InvalidTag("no record")
    kek = derive_kek(password, rec.salt)
    try:
        dek = unwrap_dek(rec.wrapped_dek, kek, rec.nonce)
    finally:
        secure_wipe(kek)
    return dek


def unwrap_for_recovery(ks: Keystore, recovery_code: str) -> bytes:
    """按 recovery 记录，恢复码派生 KEK 解包 DEK。"""
    rec = ks.get(RECOVERY_KID)
    if rec is None:
        raise InvalidTag("no recovery record")
    secret = normalize_recovery_code(recovery_code)
    kek = derive_kek(secret, rec.salt)
    try:
        dek = unwrap_dek(rec.wrapped_dek, kek, rec.nonce)
    finally:
        secure_wipe(kek)
    return dek


def user_kid(username: str) -> str:
    """公开 _user_kid 供 key_service 编址。"""
    return _user_kid(username)
