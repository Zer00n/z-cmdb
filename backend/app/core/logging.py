"""
日志配置模块
JSON 格式输出到 stdout，Docker 友好
"""
import logging
import sys
from typing import Any

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """将日志记录格式化为 JSON 字符串"""

    def format(self, record: logging.LogRecord) -> str:
        import json
        import traceback

        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 附加 extra 字段（如 user_id、ip 等）
        _RESERVED = frozenset({
            "name", "msg", "args", "levelname", "levelno",
            "pathname", "filename", "module", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread",
            "threadName", "processName", "process", "message",
            "taskName",
        })
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                log_data[key] = value

        # 异常信息
        if record.exc_info:
            log_data["exception"] = traceback.format_exception(*record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_logging() -> None:
    """初始化全局日志配置，在 main.py 启动时调用一次"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有 handler，避免重复
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    # 降低第三方库的日志噪音
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.APP_ENV == "development" else logging.WARNING
    )
