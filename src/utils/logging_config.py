"""
Structlog 日志配置模块

提供结构化日志功能，支持 JSON 输出和控制台格式化输出
"""

import structlog
import logging
import sys
from pathlib import Path


def setup_structlog(log_level: str = "INFO", log_file: str = None):
    """
    配置 structlog

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
    """

    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        stream=sys.stdout
    )

    # 配置 structlog 处理器链
    processors = [
        # 添加日志级别
        structlog.stdlib.add_log_level,
        # 添加时间戳
        structlog.processors.TimeStamper(fmt="iso"),
        # 添加调用位置信息（可选，性能开销较大）
        # structlog.processors.CallsiteParameterAdder(
        #     parameters=[
        #         structlog.processors.CallsiteParameter.FILENAME,
        #         structlog.processors.CallsiteParameter.LINENO,
        #     ]
        # ),
        # 添加堆栈信息（仅错误级别）
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # 格式化为 JSON（生产环境）或美化输出（开发环境）
        structlog.processors.JSONRenderer() if log_file else structlog.dev.ConsoleRenderer()
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 如果指定了日志文件，添加文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(
            logging.Formatter('%(message)s')  # structlog 已格式化
        )
        logging.getLogger().addHandler(file_handler)

    return structlog.get_logger()


def get_logger(name: str = None):
    """
    获取结构化日志器

    Args:
        name: 日志器名称（通常是模块名）

    Returns:
        structlog.BoundLogger
    """
    return structlog.get_logger(name)
