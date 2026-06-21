"""
Unified business exception hierarchy
Service layer only raises exception subclasses defined here; Router layer has no try/except
"""


class CMDBException(Exception):
    """Base class for business exceptions"""

    status_code: int = 400
    error_code: str = "CMDB_ERROR"

    def __init__(self, message: str = "Business error") -> None:
        self.message = message
        super().__init__(message)


# ── Resource exceptions ─────────────────────────────────────────


class AssetNotFoundError(CMDBException):
    status_code = 404
    error_code = "ASSET_NOT_FOUND"

    def __init__(self, message: str = "Asset not found") -> None:
        super().__init__(message)


class NotFoundError(CMDBException):
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)


class UserNotFoundError(CMDBException):
    status_code = 404
    error_code = "USER_NOT_FOUND"

    def __init__(self, message: str = "User not found") -> None:
        super().__init__(message)


class ScanBatchNotFoundError(CMDBException):
    status_code = 404
    error_code = "SCAN_BATCH_NOT_FOUND"

    def __init__(self, message: str = "Scan batch not found") -> None:
        super().__init__(message)


class TopologyNotFoundError(CMDBException):
    status_code = 404
    error_code = "TOPOLOGY_NOT_FOUND"

    def __init__(self, message: str = "Topology not found") -> None:
        super().__init__(message)


# ── Permission exceptions ───────────────────────────────────────


class PermissionDeniedError(CMDBException):
    status_code = 403
    error_code = "PERMISSION_DENIED"

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message)


class AuthenticationError(CMDBException):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class AccountLockedError(CMDBException):
    status_code = 423
    error_code = "ACCOUNT_LOCKED"

    def __init__(self, message: str = "Account locked") -> None:
        super().__init__(message)


# ── Validation exceptions ───────────────────────────────────────


class ValidationError(CMDBException):
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Data validation failed") -> None:
        super().__init__(message)


class DuplicateError(CMDBException):
    status_code = 409
    error_code = "DUPLICATE_ERROR"

    def __init__(self, message: str = "Duplicate data") -> None:
        super().__init__(message)


# ── File exceptions ─────────────────────────────────────────────


class FileTooLargeError(CMDBException):
    status_code = 413
    error_code = "FILE_TOO_LARGE"

    def __init__(self, message: str = "File exceeds size limit") -> None:
        super().__init__(message)


class InvalidFileTypeError(CMDBException):
    status_code = 415
    error_code = "INVALID_FILE_TYPE"

    def __init__(self, message: str = "Unsupported file type") -> None:
        super().__init__(message)


class NmapParseError(CMDBException):
    status_code = 422
    error_code = "NMAP_PARSE_ERROR"

    def __init__(self, message: str = "nmap XML parse failed") -> None:
        super().__init__(message)


# ── LLM exceptions ──────────────────────────────────────────────


class LLMCallError(CMDBException):
    status_code = 502
    error_code = "LLM_CALL_ERROR"

    def __init__(self, message: str = "LLM call failed") -> None:
        super().__init__(message)


class FeatureDisabledError(CMDBException):
    status_code = 403
    error_code = "FEATURE_DISABLED"

    def __init__(self, message: str = "Feature not enabled") -> None:
        super().__init__(message)
