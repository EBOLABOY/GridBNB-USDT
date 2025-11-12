"""
错误告警系统

支持多渠道告警：PushPlus、Telegram、Email、Webhook
"""

from enum import Enum
from typing import Dict, List, Optional
import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(ABC):
    """告警渠道抽象基类"""

    @abstractmethod
    async def send(self, level: AlertLevel, title: str, message: str, **context):
        """发送告警"""
        pass


class PushPlusChannel(AlertChannel):
    """PushPlus 渠道"""

    def __init__(self, token: str):
        self.token = token
        self.api_url = "http://www.pushplus.plus/send"

    async def send(self, level: AlertLevel, title: str, message: str, **context):
        if not self.token:
            return

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    'token': self.token,
                    'title': f"[{level.value.upper()}] {title}",
                    'content': message,
                    'template': 'html'
                }
                async with session.post(self.api_url, json=data) as response:
                    if response.status == 200:
                        logger.debug(f"PushPlus 告警发送成功: {title}")
                    else:
                        logger.warning(f"PushPlus 告警发送失败: {response.status}")
        except Exception as e:
            logger.error(f"PushPlus 发送异常: {e}")


class TelegramChannel(AlertChannel):
    """Telegram Bot 渠道"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async def send(self, level: AlertLevel, title: str, message: str, **context):
        if not self.bot_token or not self.chat_id:
            return

        try:
            # 根据级别选择 emoji
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }
            emoji = emoji_map.get(level, "📢")

            text = f"{emoji} **{level.value.upper()}** {emoji}\n\n"
            text += f"**{title}**\n\n"
            text += f"{message}\n\n"

            # 添加上下文信息
            if context:
                text += "**详细信息:**\n"
                for key, value in context.items():
                    text += f"• {key}: {value}\n"

            async with aiohttp.ClientSession() as session:
                data = {
                    'chat_id': self.chat_id,
                    'text': text,
                    'parse_mode': 'Markdown'
                }
                async with session.post(self.api_url, json=data) as response:
                    if response.status == 200:
                        logger.debug(f"Telegram 告警发送成功: {title}")
                    else:
                        logger.warning(f"Telegram 告警发送失败: {response.status}")
        except Exception as e:
            logger.error(f"Telegram 发送异常: {e}")


class WebhookChannel(AlertChannel):
    """Webhook 渠道（支持 Discord, Slack 等）"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, level: AlertLevel, title: str, message: str, **context):
        if not self.webhook_url:
            return

        try:
            payload = {
                "level": level.value,
                "title": title,
                "message": message,
                "context": context
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.debug(f"Webhook 告警发送成功: {title}")
                    else:
                        logger.warning(f"Webhook 告警发送失败: {response.status}")
        except Exception as e:
            logger.error(f"Webhook 发送异常: {e}")


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.channels: Dict[str, AlertChannel] = {}
        self._enabled = True

    def add_channel(self, name: str, channel: AlertChannel):
        """添加告警渠道"""
        self.channels[name] = channel
        logger.info(f"告警渠道已添加: {name}")

    def remove_channel(self, name: str):
        """移除告警渠道"""
        if name in self.channels:
            del self.channels[name]
            logger.info(f"告警渠道已移除: {name}")

    def enable(self):
        """启用告警"""
        self._enabled = True

    def disable(self):
        """禁用告警"""
        self._enabled = False

    async def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        channels: Optional[List[str]] = None,
        **context
    ):
        """
        发送告警

        Args:
            level: 告警级别
            title: 告警标题
            message: 告警消息
            channels: 指定渠道列表（None = 根据级别自动选择）
            **context: 额外的上下文信息
        """
        if not self._enabled:
            return

        # 根据级别自动选择渠道
        if channels is None:
            if level == AlertLevel.INFO:
                return  # INFO 级别不发送告警
            elif level == AlertLevel.WARNING:
                channels = ['pushplus']
            elif level == AlertLevel.ERROR:
                channels = ['pushplus', 'telegram']
            elif level == AlertLevel.CRITICAL:
                channels = list(self.channels.keys())  # 所有渠道

        # 并发发送到所有渠道
        tasks = []
        for channel_name in channels:
            if channel_name in self.channels:
                channel = self.channels[channel_name]
                tasks.append(channel.send(level, title, message, **context))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# 全局单例
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def setup_alerts(
    pushplus_token: Optional[str] = None,
    telegram_bot_token: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    webhook_url: Optional[str] = None
):
    """
    设置告警渠道

    Args:
        pushplus_token: PushPlus Token
        telegram_bot_token: Telegram Bot Token
        telegram_chat_id: Telegram Chat ID
        webhook_url: Webhook URL
    """
    manager = get_alert_manager()

    if pushplus_token:
        manager.add_channel('pushplus', PushPlusChannel(pushplus_token))

    if telegram_bot_token and telegram_chat_id:
        manager.add_channel('telegram', TelegramChannel(telegram_bot_token, telegram_chat_id))

    if webhook_url:
        manager.add_channel('webhook', WebhookChannel(webhook_url))

    return manager
