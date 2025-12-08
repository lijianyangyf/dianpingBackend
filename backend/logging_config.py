# backend/logging_config.py
import logging
import os
from logging.handlers import RotatingFileHandler

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日志格式（JSON 格式更利于日志系统抓取）
LOG_FORMAT = (
    '{"time": "%(asctime)s", '
    '"level": "%(levelname)s", '
    '"logger": "%(name)s", '
    '"traceId": "%(traceId)s", '
    '"message": %(message)s}'
)

class TraceIdFilter(logging.Filter):
    """为每条日志注入 traceId"""
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "traceId"):
            record.traceId = "-"
        return True


def setup_logging():
    """初始化全局日志系统"""

    # 防止重复初始化
    if logging.getLogger().handlers:
        return

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()

    # 应用 traceId 过滤器
    logger.addFilter(TraceIdFilter())

    formatter = logging.Formatter(LOG_FORMAT)

    # -------------------------
    # INFO / DEBUG 日志文件
    # -------------------------
    info_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app-info.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # -------------------------
    # ERROR 日志文件
    # -------------------------
    error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app-error.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # -------------------------
    # 控制台输出
    # -------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 添加 handler
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    logger.info("日志系统初始化完成")


