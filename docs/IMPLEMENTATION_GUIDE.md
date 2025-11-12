# 项目优化实施详细指南

> **目标读者**: 开发者/运维人员
> **难度**: 中级
> **预计总时间**: 5-7天（可分阶段实施）
> **当前进度**: 阶段1 ✅ 已完成，阶段2-4 待实施

---

## 📋 总体规划

| 阶段 | 内容 | 优先级 | 时间 | 状态 |
|------|------|--------|------|------|
| 阶段1 | 快速改进（健康检查、版本信息、配置验证） | 🔴 高 | 30分钟 | ✅ 已完成 |
| 阶段2 | 日志系统升级（structlog） | 🔴 高 | 1-2天 | ⏸️ 待实施 |
| 阶段3 | 错误告警系统（多渠道） | 🔴 高 | 2-3天 | ⏸️ 待实施 |
| 阶段4 | 配置热重载 | 🟡 中 | 2天 | ⏸️ 待实施 |

---

## 🎯 阶段2: 日志系统升级（详细步骤）

### 为什么需要升级？

**当前问题**:
- 日志是纯文本，难以解析和分析
- 缺少结构化上下文信息
- 不支持日志聚合工具（ELK、Loki等）

**升级后的好处**:
```python
# 之前 (纯文本)
logger.info(f"订单执行成功: BNB/USDT buy 680.5")

# 之后 (JSON结构化)
logger.info("order_executed", symbol="BNB/USDT", side="buy", price=680.5)
# 输出: {"event": "order_executed", "symbol": "BNB/USDT", "side": "buy", "price": 680.5, "timestamp": "2025-10-20T18:30:00"}
```

---

### 步骤 2.1: 安装 structlog

```bash
# 1. 激活虚拟环境
# Windows:
.\.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. 安装 structlog
pip install structlog python-json-logger

# 3. 更新 requirements.txt
pip freeze | grep structlog >> requirements.txt
pip freeze | grep python-json-logger >> requirements.txt

# 或手动添加到 requirements.txt:
# structlog>=24.1.0
# python-json-logger>=2.0.7
```

**验证安装**:
```bash
python -c "import structlog; print(structlog.__version__)"
# 应输出: 24.1.0 或更高版本
```

---

### 步骤 2.2: 创建 structlog 配置文件

**创建文件**: `src/utils/logging_config.py`

```python
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
```

---

### 步骤 2.3: 更新 helpers.py

**编辑文件**: `src/utils/helpers.py`

**找到 `LogConfig` 类**，在文件开头添加导入：

```python
# 在文件顶部添加
from src.utils.logging_config import setup_structlog, get_logger
```

**更新 `LogConfig.setup_logging()` 方法**:

```python
@classmethod
def setup_logging(cls):
    """配置日志系统 - 使用 structlog"""
    # 创建日志目录
    os.makedirs(cls.LOG_DIR, exist_ok=True)
    log_file = os.path.join(cls.LOG_DIR, cls.LOG_FILE)

    # 设置 structlog
    logger = setup_structlog(
        log_level=cls.LOG_LEVEL,
        log_file=log_file
    )

    logger.info(
        "logging_initialized",
        log_level=cls.LOG_LEVEL,
        log_file=log_file
    )

    return logger
```

---

### 步骤 2.4: 更新主程序使用 structlog

**编辑文件**: `src/main.py`

**找到日志初始化部分**（大约第45行），修改为：

```python
# 之前
from src.utils.helpers import LogConfig
LogConfig.setup_logging()
logger = logging.getLogger(__name__)

# 之后
from src.utils.logging_config import setup_structlog, get_logger

# 初始化 structlog
setup_structlog(log_level="INFO", log_file="logs/trading_system.log")
logger = get_logger(__name__)
```

**更新日志调用示例**:

```python
# 之前
logger.info(f"交易系统启动")
logger.info(f"运行中的交易对: {SYMBOLS_LIST}")

# 之后
logger.info("trading_system_started")
logger.info(
    "trading_pairs_loaded",
    symbols=SYMBOLS_LIST,
    count=len(SYMBOLS_LIST)
)
```

---

### 步骤 2.5: 逐步迁移其他模块（可选）

**优先迁移的模块**:
1. `src/core/trader.py` - 核心交易逻辑
2. `src/core/exchange_client.py` - API 调用
3. `src/strategies/risk_manager.py` - 风险管理

**迁移模板**:

```python
# 在文件顶部
from src.utils.logging_config import get_logger

# 替换原有的 logger
# 之前:
# import logging
# logger = logging.getLogger(__name__)

# 之后:
logger = get_logger(__name__)

# 更新关键日志点
# 订单执行
logger.info(
    "order_executed",
    symbol=self.symbol,
    side=side,
    price=price,
    amount=amount,
    order_id=order.get('id'),
    execution_time_ms=execution_time
)

# 错误日志
logger.error(
    "order_failed",
    symbol=self.symbol,
    side=side,
    error=str(e),
    retry_count=retry
)
```

---

### 步骤 2.6: 测试日志系统

```bash
# 1. 启动程序
python src/main.py

# 2. 检查日志文件
cat logs/trading_system.log

# 应看到 JSON 格式的日志:
# {"event": "trading_system_started", "timestamp": "2025-10-20T18:30:00", ...}

# 3. 使用 jq 工具解析（可选）
cat logs/trading_system.log | jq .

# 4. 查询特定事件
cat logs/trading_system.log | jq 'select(.event == "order_executed")'
```

---

### 步骤 2.7: 配置日志轮转（可选）

**安装 logrotate（Linux）**:

```bash
# 创建配置文件
sudo nano /etc/logrotate.d/gridbnb

# 添加内容:
/path/to/GridBNB-USDT/logs/trading_system.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 your_user your_group
}
```

**或使用 Python 的 RotatingFileHandler**:

```python
# 在 setup_structlog() 中
from logging.handlers import RotatingFileHandler

if log_file:
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
```

---

## 🎯 阶段3: 错误告警系统（详细步骤）

### 为什么需要？

- 当前只有 PushPlus 一个渠道
- 无法区分告警级别
- 不支持双向交互

---

### 步骤 3.1: 创建告警管理器基础架构

**创建文件**: `src/services/alerting.py`

```python
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
```

---

### 步骤 3.2: 配置 Telegram Bot（可选）

**3.2.1 创建 Telegram Bot**

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置 Bot 名称和用户名
4. 获得 Bot Token（类似 `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）

**3.2.2 获取 Chat ID**

1. 将 Bot 添加到你的频道或群组
2. 发送一条消息
3. 访问：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. 查找 `"chat":{"id": <CHAT_ID>}`

**3.2.3 添加到 .env**

```bash
# Telegram 告警配置
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="-1001234567890"
```

---

### 步骤 3.3: 在配置中添加 Telegram 支持

**编辑文件**: `src/config/settings.py`

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # 新增：Telegram 配置
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    WEBHOOK_URL: Optional[str] = None
```

---

### 步骤 3.4: 在主程序中初始化告警系统

**编辑文件**: `src/main.py`

```python
# 在导入部分添加
from src.services.alerting import setup_alerts, get_alert_manager, AlertLevel

# 在 main() 函数开头初始化告警
async def main():
    # ... 现有代码 ...

    # 设置告警系统
    alert_manager = setup_alerts(
        pushplus_token=settings.PUSHPLUS_TOKEN,
        telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
        telegram_chat_id=settings.TELEGRAM_CHAT_ID,
        webhook_url=settings.WEBHOOK_URL
    )

    # 发送启动通知
    await alert_manager.send_alert(
        AlertLevel.INFO,
        "系统启动",
        f"GridBNB 交易系统已启动\n交易对: {', '.join(SYMBOLS_LIST)}"
    )
```

---

### 步骤 3.5: 在关键位置添加告警

**示例：在 trader.py 中添加错误告警**

```python
# 在 trader.py 顶部导入
from src.services.alerting import get_alert_manager, AlertLevel

# 在错误处理处添加告警
async def execute_order(self, side, amount, price=None):
    try:
        # ... 交易逻辑 ...
        pass
    except Exception as e:
        # 发送错误告警
        alert_manager = get_alert_manager()
        await alert_manager.send_alert(
            AlertLevel.ERROR,
            "订单执行失败",
            f"交易对: {self.symbol}\n方向: {side}\n错误: {str(e)}",
            symbol=self.symbol,
            side=side,
            amount=amount,
            error=str(e)
        )
        raise
```

**示例：连续失败告警**

```python
# 在连续失败达到阈值时
if self.continuous_failures >= 5:
    alert_manager = get_alert_manager()
    await alert_manager.send_alert(
        AlertLevel.CRITICAL,
        "连续失败告警",
        f"交易对 {self.symbol} 已连续失败 {self.continuous_failures} 次",
        symbol=self.symbol,
        failures=self.continuous_failures
    )
```

---

### 步骤 3.6: 测试告警系统

```python
# 创建测试脚本: test_alerts.py

import asyncio
from src.services.alerting import setup_alerts, AlertLevel

async def test_alerts():
    # 初始化（使用你的真实 Token）
    alert_manager = setup_alerts(
        pushplus_token="YOUR_PUSHPLUS_TOKEN",
        telegram_bot_token="YOUR_TELEGRAM_BOT_TOKEN",
        telegram_chat_id="YOUR_CHAT_ID"
    )

    # 测试不同级别的告警
    await alert_manager.send_alert(
        AlertLevel.WARNING,
        "测试告警 - WARNING",
        "这是一条 WARNING 级别的测试消息"
    )

    await asyncio.sleep(2)

    await alert_manager.send_alert(
        AlertLevel.ERROR,
        "测试告警 - ERROR",
        "这是一条 ERROR 级别的测试消息",
        test_key="test_value"
    )

    await asyncio.sleep(2)

    await alert_manager.send_alert(
        AlertLevel.CRITICAL,
        "测试告警 - CRITICAL",
        "这是一条 CRITICAL 级别的测试消息"
    )

if __name__ == "__main__":
    asyncio.run(test_alerts())
```

**运行测试**:
```bash
python test_alerts.py
```

---

## 🎯 阶段4: 配置热重载（详细步骤）

### 步骤 4.1: 安装 watchdog

```bash
pip install watchdog

# 更新 requirements.txt
echo "watchdog>=4.0.0" >> requirements.txt
```

---

### 步骤 4.2: 创建配置监听器

**创建文件**: `src/services/config_watcher.py`

```python
"""
配置文件热重载

监听 .env 文件变化，自动重新加载配置
"""

import os
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class ConfigReloadHandler(FileSystemEventHandler):
    """配置文件变化处理器"""

    def __init__(self, callback=None):
        self.callback = callback
        self.last_reload = 0
        self.reload_delay = 2  # 防抖延迟（秒）

    def on_modified(self, event):
        if event.is_directory:
            return

        # 只监听 .env 文件
        if event.src_path.endswith('.env'):
            current_time = time.time()
            if current_time - self.last_reload < self.reload_delay:
                return  # 防抖：忽略短时间内的重复事件

            self.last_reload = current_time
            logger.info(f"检测到配置文件变化: {event.src_path}")

            try:
                # 重新加载配置
                new_settings = Settings()
                logger.info("配置已重新加载")

                # 调用回调函数
                if self.callback:
                    self.callback(new_settings)

            except Exception as e:
                logger.error(f"配置重新加载失败: {e}")


class ConfigWatcher:
    """配置文件监听器"""

    def __init__(self, config_dir: str, callback=None):
        self.config_dir = Path(config_dir)
        self.callback = callback
        self.observer = None

    def start(self):
        """启动监听"""
        if self.observer is not None:
            logger.warning("配置监听器已在运行")
            return

        event_handler = ConfigReloadHandler(callback=self.callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.config_dir), recursive=False)
        self.observer.start()

        logger.info(f"配置文件监听已启动: {self.config_dir}")

    def stop(self):
        """停止监听"""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("配置文件监听已停止")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
```

---

### 步骤 4.3: 在主程序中集成配置监听

**编辑文件**: `src/main.py`

```python
# 导入
from src.services.config_watcher import ConfigWatcher

# 在 main() 函数中
async def main():
    # ... 现有初始化代码 ...

    # 定义配置重新加载回调
    def on_config_reload(new_settings):
        logger.info(
            "config_reloaded",
            min_trade_amount=new_settings.MIN_TRADE_AMOUNT,
            initial_grid=new_settings.INITIAL_GRID
        )

        # 发送告警通知
        alert_manager = get_alert_manager()
        asyncio.create_task(alert_manager.send_alert(
            AlertLevel.WARNING,
            "配置已重新加载",
            f"MIN_TRADE_AMOUNT: {new_settings.MIN_TRADE_AMOUNT}\n"
            f"INITIAL_GRID: {new_settings.INITIAL_GRID}"
        ))

        # TODO: 更新 trader 实例的配置
        # 这需要在 trader 类中添加 update_config() 方法

    # 启动配置监听
    config_watcher = ConfigWatcher(
        config_dir="config",
        callback=on_config_reload
    )
    config_watcher.start()

    try:
        # ... 现有运行代码 ...
        pass
    finally:
        # 清理资源
        config_watcher.stop()
```

---

### 步骤 4.4: 在 Trader 中添加配置更新方法

**编辑文件**: `src/core/trader.py`

```python
# 添加配置更新方法
def update_config(self, new_settings):
    """
    热更新配置

    允许动态更新的配置项:
    - min_trade_amount: 最小交易金额
    - initial_grid: 初始网格大小（仅在下次调整时生效）
    """
    old_min_trade_amount = self.config.MIN_TRADE_AMOUNT
    old_initial_grid = self.config.INITIAL_GRID

    # 更新配置
    self.config = new_settings

    # 记录变化
    self.logger.info(
        "config_updated",
        old_min_trade_amount=old_min_trade_amount,
        new_min_trade_amount=new_settings.MIN_TRADE_AMOUNT,
        old_initial_grid=old_initial_grid,
        new_initial_grid=new_settings.INITIAL_GRID
    )
```

---

### 步骤 4.5: 测试配置热重载

```bash
# 1. 启动程序
python src/main.py

# 2. 在另一个终端修改配置
nano config/.env
# 修改 MIN_TRADE_AMOUNT=30.0

# 3. 保存文件
# 查看程序日志，应看到:
# {"event": "config_reloaded", "min_trade_amount": 30.0, ...}

# 4. 应该收到告警通知（PushPlus/Telegram）
```

---

## 📊 完整实施时间表

| 日期 | 阶段 | 任务 | 时间 |
|------|------|------|------|
| Day 1 | 阶段2 | 安装 structlog 并配置 | 2小时 |
| Day 1-2 | 阶段2 | 更新日志调用 | 6小时 |
| Day 2 | 阶段3 | 创建告警管理器 | 3小时 |
| Day 3 | 阶段3 | 配置 Telegram Bot | 2小时 |
| Day 3 | 阶段3 | 集成到现有代码 | 3小时 |
| Day 4 | 阶段4 | 实现配置热重载 | 4小时 |
| Day 4 | 测试 | 全面测试所有功能 | 2小时 |

**总计**: 约 22 小时（4天工作日）

---

## ✅ 验收标准

### 阶段2验收
- [ ] structlog 安装成功
- [ ] 日志输出为 JSON 格式
- [ ] 可以用 jq 工具解析日志
- [ ] 关键操作有结构化上下文

### 阶段3验收
- [ ] PushPlus 告警正常
- [ ] Telegram 告警正常（如配置）
- [ ] 错误级别自动路由到不同渠道
- [ ] 告警包含完整上下文信息

### 阶段4验收
- [ ] 修改 .env 文件自动重新加载
- [ ] 收到配置重载通知
- [ ] 新配置立即生效
- [ ] 无需重启程序

---

## 🆘 常见问题

### Q1: structlog 安装失败
```bash
# 尝试升级 pip
python -m pip install --upgrade pip

# 使用镜像源
pip install structlog -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: Telegram Bot 收不到消息
1. 检查 Bot Token 是否正确
2. 检查 Chat ID 是否正确（负数要保留负号）
3. 确认 Bot 已添加到频道/群组
4. 检查网络连接（Telegram 在某些地区需要代理）

### Q3: 配置热重载不生效
1. 确认 watchdog 已安装：`pip list | grep watchdog`
2. 检查配置文件路径是否正确
3. 查看日志是否有 "配置文件变化" 消息
4. 确认防抖延迟（2秒内的重复修改会被忽略）

---

## 📚 参考文档

- [structlog 官方文档](https://www.structlog.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [watchdog 文档](https://python-watchdog.readthedocs.io/)
- [项目优化建议](OPTIMIZATION_RECOMMENDATIONS.md)

---

**文档版本**: 1.0
**创建时间**: 2025-10-20
**最后更新**: 2025-10-20
**维护者**: GridBNB Team
