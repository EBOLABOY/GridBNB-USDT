import logging
import os
import time
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Callable, Coroutine, Optional, Tuple, TypeVar

import psutil
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.utils.logging_config import setup_structlog, get_logger

T = TypeVar("T")


def format_trade_message(
    side: str,
    symbol: str,
    price: float,
    amount: float,
    total: float,
    grid_size: float,
    base_asset: str,
    quote_asset: str,
    retry_count: Optional[Tuple[int, int]] = None,
) -> str:
    """格式化交易消息为美观的文本格式

    Args:
        side: 交易方向 ('buy' 或 'sell')
        symbol: 交易对
        price: 交易价格
        amount: 交易数量
        total: 交易总额
        grid_size: 网格大小
        base_asset: 基础货币名称
        quote_asset: 计价货币名称
        retry_count: 重试次数，格式为 (当前次数, 最大次数)

    Returns:
        格式化后的消息文本
    """
    # 使用emoji增加可读性
    direction_emoji = "🟢" if side == "buy" else "🔴"
    direction_text = "买入" if side == "buy" else "卖出"

    # 构建消息主体
    message = f"""
{direction_emoji} {direction_text} {symbol}
━━━━━━━━━━━━━━━━━━━━
💰 价格：{price:.2f} {quote_asset}
📊 数量：{amount:.4f} {base_asset}
💵 金额：{total:.2f} {quote_asset}
📈 网格：{grid_size}%
"""

    # 如果有重试信息，添加重试次数
    if retry_count:
        current, max_retries = retry_count
        message += f"🔄 尝试：{current}/{max_retries}次\n"

    # 添加时间戳
    message += f"⏰ 时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"

    return message


def send_pushplus_message(
    content: str, title: str = "交易信号通知", timeout: int = settings.PUSHPLUS_TIMEOUT
) -> None:
    """发送 PushPlus 推送通知

    Args:
        content: 通知内容
        title: 通知标题
        timeout: 请求超时时间(秒)
    """
    if not settings.PUSHPLUS_TOKEN:
        logging.error("未配置PUSHPLUS_TOKEN，无法发送通知")
        return

    url = os.getenv("PUSHPLUS_URL", "https://www.pushplus.plus/send")
    data = {
        "token": settings.PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "txt",  # 使用文本模板
    }
    try:
        logging.info(f"正在发送推送通知: {title}")
        response = requests.post(url, data=data, timeout=timeout)
        response_json = response.json()

        if response.status_code == 200 and response_json.get("code") == 200:
            logging.info(f"消息推送成功: {content}")
        else:
            logging.error(f"消息推送失败: 状态码={response.status_code}, 响应={response_json}")
    except Exception as e:
        logging.error(f"消息推送异常: {str(e)}", exc_info=True)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def safe_fetch(method: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
    """带重试的安全异步请求包装器

    Args:
        method: 要执行的异步方法
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        方法的返回值

    Raises:
        Exception: 重试失败后抛出原异常
    """
    try:
        return await method(*args, **kwargs)
    except Exception as e:
        logging.error(f"请求失败: {str(e)}")
        raise


def debug_watcher() -> (
    Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]
):
    """资源监控装饰器

    装饰异步函数以监控其执行时间和内存使用。

    Returns:
        装饰器函数
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start = time.time()
            mem_before = psutil.virtual_memory().used
            logging.debug(f"[DEBUG] 开始执行 {func.__name__}")

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                cost = time.time() - start
                mem_used = psutil.virtual_memory().used - mem_before
                logging.debug(
                    f"[DEBUG] {func.__name__} 执行完成 | "
                    f"耗时: {cost:.3f}s | 内存变化: {mem_used / 1024 / 1024:.2f}MB"
                )

        return wrapper

    return decorator


class LogConfig:
    """日志配置类"""

    SINGLE_LOG: bool = True  # 强制单文件模式
    BACKUP_DAYS: int = 2  # 保留2天日志
    LOG_DIR: str = os.path.dirname(__file__)  # 与main.py相同目录
    LOG_LEVEL: int = logging.INFO

    @staticmethod
    def setup_logger() -> None:
        """配置日志系统 - 使用 structlog

        设置 structlog 结构化日志系统，支持 JSON 输出到文件。
        """
        # 创建日志文件路径
        log_file = os.path.join(LogConfig.LOG_DIR, "trading_system.log")

        # 设置 structlog
        logger = setup_structlog(
            log_level="INFO",  # 使用 INFO 级别
            log_file=log_file
        )

        logger.info(
            "logging_initialized",
            log_level="INFO",
            log_file=log_file
        )

    @staticmethod
    def clean_old_logs() -> None:
        """清理过期的日志文件

        删除超过保留期限的日志文件。
        """
        if not os.path.exists(LogConfig.LOG_DIR):
            return
        now = time.time()
        for fname in os.listdir(LogConfig.LOG_DIR):
            if LogConfig.SINGLE_LOG and fname != "trading_system.log":
                continue
            path = os.path.join(LogConfig.LOG_DIR, fname)
            if os.stat(path).st_mtime < now - LogConfig.BACKUP_DAYS * 86400:
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"删除旧日志失败 {fname}: {str(e)}")
