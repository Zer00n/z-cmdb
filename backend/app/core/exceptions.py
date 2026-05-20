"""
统一业务异常体系
Service 层只抛这里定义的异常子类，Router 层不写 try/except
"""


class CMDBException(Exception):
    """业务异常基类"""

    status_code: int = 400
    error_code: str = "CMDB_ERROR"

    def __init__(self, message: str = "业务错误") -> None:
        self.message = message
        super().__init__(message)


# ── 资源类异常 ──────────────────────────────────────────────


class AssetNotFoundError(CMDBException):
    status_code = 404
    error_code = "ASSET_NOT_FOUND"

    def __init__(self, message: str = "资产不存在") -> None:
        super().__init__(message)


class NotFoundError(CMDBException):
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message)


class UserNotFoundError(CMDBException):
    status_code = 404
    error_code = "USER_NOT_FOUND"

    def __init__(self, message: str = "用户不存在") -> None:
        super().__init__(message)


class ScanBatchNotFoundError(CMDBException):
    status_code = 404
    error_code = "SCAN_BATCH_NOT_FOUND"

    def __init__(self, message: str = "扫描批次不存在") -> None:
        super().__init__(message)


class TopologyNotFoundError(CMDBException):
    status_code = 404
    error_code = "TOPOLOGY_NOT_FOUND"

    def __init__(self, message: str = "拓扑图不存在") -> None:
        super().__init__(message)


# ── 权限类异常 ──────────────────────────────────────────────


class PermissionDeniedError(CMDBException):
    status_code = 403
    error_code = "PERMISSION_DENIED"

    def __init__(self, message: str = "权限不足") -> None:
        super().__init__(message)


class AuthenticationError(CMDBException):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str = "认证失败") -> None:
        super().__init__(message)


class AccountLockedError(CMDBException):
    status_code = 423
    error_code = "ACCOUNT_LOCKED"

    def __init__(self, message: str = "账号已锁定") -> None:
        super().__init__(message)


# ── 校验类异常 ──────────────────────────────────────────────


class ValidationError(CMDBException):
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "数据校验失败") -> None:
        super().__init__(message)


class DuplicateError(CMDBException):
    status_code = 409
    error_code = "DUPLICATE_ERROR"

    def __init__(self, message: str = "数据已存在") -> None:
        super().__init__(message)


# ── 文件类异常 ──────────────────────────────────────────────


class FileTooLargeError(CMDBException):
    status_code = 413
    error_code = "FILE_TOO_LARGE"

    def __init__(self, message: str = "文件超过大小限制") -> None:
        super().__init__(message)


class InvalidFileTypeError(CMDBException):
    status_code = 415
    error_code = "INVALID_FILE_TYPE"

    def __init__(self, message: str = "不支持的文件类型") -> None:
        super().__init__(message)


class NmapParseError(CMDBException):
    status_code = 422
    error_code = "NMAP_PARSE_ERROR"

    def __init__(self, message: str = "nmap XML 解析失败") -> None:
        super().__init__(message)


# ── LLM 类异常 ──────────────────────────────────────────────


class LLMCallError(CMDBException):
    status_code = 502
    error_code = "LLM_CALL_ERROR"

    def __init__(self, message: str = "LLM 调用失败") -> None:
        super().__init__(message)
