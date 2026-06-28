"""
Application configuration module
Uses Pydantic Settings v2 to manage all configuration items
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "sqlite:///./data/cmdb.db"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_SECRET_FILE: str = ""          # Docker secrets file path
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    @property
    def jwt_secret(self) -> str:
        """Prefer reading from secrets file, fall back to env variable"""
        if self.JWT_SECRET_FILE:
            secret_path = Path(self.JWT_SECRET_FILE)
            if secret_path.exists():
                return secret_path.read_text(encoding="utf-8").strip()
        return self.JWT_SECRET

    # File upload
    UPLOAD_MAX_SIZE_MB: int = 50

    # Logging
    LOG_LEVEL: str = "INFO"

    # Application
    APP_ENV: str = "development"
    APP_TITLE: str = "Z-CMDB Lite"
    APP_VERSION: str = "0.6.5"

    # CORS (allow frontend dev server during development)
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Initial admin password (used on first startup; random if left empty)
    INITIAL_ADMIN_PASSWORD: str = ""

    # Refresh cookie Secure flag (False by default; set to true in production HTTPS)
    COOKIE_SECURE: bool = False

    @property
    def db_path(self) -> Path:
        """Resolve the absolute path of the database file (cross-platform)"""
        url = self.DATABASE_URL
        if url.startswith("sqlite:///"):
            relative = url[len("sqlite:///"):]
            # Relative to the backend/ directory
            base = Path(__file__).parent.parent.parent
            return base / relative
        return Path(url)

    @property
    def upload_max_bytes(self) -> int:
        return self.UPLOAD_MAX_SIZE_MB * 1024 * 1024


settings = Settings()


def validate_runtime_secrets() -> None:
    """生产环境密钥校验，在应用启动事件中调用。"""
    import logging
    _logger = logging.getLogger(__name__)
    is_prod = settings.APP_ENV.lower() in ("production", "prod")
    weak = settings.jwt_secret in ("", "change-me-in-production") or len(settings.jwt_secret) < 32

    if weak:
        msg = (
            "JWT_SECRET is using the default/weak value. "
            "Set a strong JWT_SECRET (>=32 random chars) or JWT_SECRET_FILE."
        )
        if is_prod:
            raise RuntimeError(msg + " Refusing to start in production.")
        _logger.warning(msg)
