"""
应用配置模块
使用 Pydantic Settings v2 管理所有配置项
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

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/cmdb.db"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_SECRET_FILE: str = ""          # Docker secrets 文件路径
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    @property
    def jwt_secret(self) -> str:
        """优先从 secrets 文件读取，否则用环境变量"""
        if self.JWT_SECRET_FILE:
            secret_path = Path(self.JWT_SECRET_FILE)
            if secret_path.exists():
                return secret_path.read_text(encoding="utf-8").strip()
        return self.JWT_SECRET

    # 文件上传
    UPLOAD_MAX_SIZE_MB: int = 50

    # 日志
    LOG_LEVEL: str = "INFO"

    # 应用
    APP_ENV: str = "development"
    APP_TITLE: str = "CMDB Lite"
    APP_VERSION: str = "0.1.0"

    # CORS（开发期允许前端 dev server）
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def db_path(self) -> Path:
        """解析数据库文件的绝对路径（跨平台）"""
        url = self.DATABASE_URL
        if url.startswith("sqlite:///"):
            relative = url[len("sqlite:///"):]
            # 相对于 backend/ 目录
            base = Path(__file__).parent.parent.parent
            return base / relative
        return Path(url)

    @property
    def upload_max_bytes(self) -> int:
        return self.UPLOAD_MAX_SIZE_MB * 1024 * 1024


settings = Settings()
