"""
配置文件热重载模块

使用 watchdog 监听 .env 文件变化,自动重新加载配置
"""

import os
import logging
from pathlib import Path
from typing import Dict, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from dotenv import load_dotenv
import time
import asyncio

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变更处理器"""

    def __init__(self, config_file: str, callback: Callable):
        """
        初始化配置文件监听器

        Args:
            config_file: 配置文件路径（如 .env）
            callback: 配置变更时的回调函数
        """
        self.config_file = Path(config_file).resolve()
        self.callback = callback
        self.last_modified = time.time()
        self._debounce_seconds = 1.0  # 防抖时间（秒）

    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return

        # 检查是否是目标配置文件
        if Path(event.src_path).resolve() == self.config_file:
            # 防抖处理：避免短时间内多次触发
            current_time = time.time()
            if current_time - self.last_modified < self._debounce_seconds:
                return

            self.last_modified = current_time
            logger.info(f"检测到配置文件变更: {self.config_file}")

            try:
                # 调用回调函数
                self.callback()
            except Exception as e:
                logger.error(f"配置重载失败: {e}", exc_info=True)


class ConfigWatcher:
    """配置文件监听器"""

    def __init__(self, config_file: str = "config/.env"):
        """
        初始化配置监听器

        Args:
            config_file: 配置文件路径（相对于项目根目录）
        """
        # 获取项目根目录
        project_root = Path(__file__).resolve().parent.parent.parent
        self.config_file = project_root / config_file

        if not self.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")

        self.observer: Optional[Observer] = None
        self.callbacks: Dict[str, Callable] = {}

        logger.info(f"配置监听器已初始化: {self.config_file}")

    def add_callback(self, name: str, callback: Callable):
        """
        添加配置变更回调函数

        Args:
            name: 回调函数名称（用于标识）
            callback: 回调函数（无参数）
        """
        self.callbacks[name] = callback
        logger.info(f"已添加配置变更回调: {name}")

    def remove_callback(self, name: str):
        """移除配置变更回调函数"""
        if name in self.callbacks:
            del self.callbacks[name]
            logger.info(f"已移除配置变更回调: {name}")

    def _reload_config(self):
        """重新加载配置文件"""
        logger.info("开始重新加载配置...")

        # 1. 重新加载 .env 文件
        load_dotenv(self.config_file, override=True)
        logger.info("✅ .env 文件已重新加载")

        # 2. 执行所有回调函数
        for name, callback in self.callbacks.items():
            try:
                logger.info(f"执行回调: {name}")
                callback()
            except Exception as e:
                logger.error(f"回调 {name} 执行失败: {e}", exc_info=True)

        logger.info("配置重载完成")

    def start(self):
        """启动配置文件监听"""
        if self.observer is not None:
            logger.warning("配置监听器已在运行中")
            return

        # 创建事件处理器
        event_handler = ConfigFileHandler(
            str(self.config_file),
            self._reload_config
        )

        # 创建观察者
        self.observer = Observer()

        # 监听配置文件所在目录
        watch_dir = str(self.config_file.parent)
        self.observer.schedule(event_handler, watch_dir, recursive=False)

        # 启动观察者
        self.observer.start()
        logger.info(f"✅ 配置监听器已启动，监听目录: {watch_dir}")

    def stop(self):
        """停止配置文件监听"""
        if self.observer is None:
            logger.warning("配置监听器未运行")
            return

        self.observer.stop()
        self.observer.join()
        self.observer = None
        logger.info("配置监听器已停止")

    def is_running(self) -> bool:
        """检查监听器是否在运行"""
        return self.observer is not None and self.observer.is_alive()


# 全局单例
_config_watcher: Optional[ConfigWatcher] = None


def get_config_watcher(config_file: str = "config/.env") -> ConfigWatcher:
    """获取全局配置监听器"""
    global _config_watcher
    if _config_watcher is None:
        _config_watcher = ConfigWatcher(config_file)
    return _config_watcher


def setup_config_watcher(
    config_file: str = "config/.env",
    callbacks: Optional[Dict[str, Callable]] = None
) -> ConfigWatcher:
    """
    设置配置监听器

    Args:
        config_file: 配置文件路径
        callbacks: 回调函数字典 {name: callback}

    Returns:
        ConfigWatcher 实例
    """
    watcher = get_config_watcher(config_file)

    if callbacks:
        for name, callback in callbacks.items():
            watcher.add_callback(name, callback)

    watcher.start()
    return watcher
