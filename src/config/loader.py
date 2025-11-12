"""
配置加载器 (Config Loader)

实现混合配置加载策略：
1. 启动时从数据库加载所有配置到内存缓存
2. 提供 reload() 方法手动刷新缓存
3. 三级优先级：数据库 > .env > 默认值
4. API密钥不存入数据库，仅从.env读取

使用方式：
    from src.config.loader import config_loader

    # 获取配置值
    value = config_loader.get('INITIAL_GRID')

    # 刷新缓存
    config_loader.reload()
"""

import os
import json
import logging
from typing import Any, Optional, Dict
from dotenv import load_dotenv

from src.database.connection import db_manager
from src.database.models import Configuration, ConfigStatusEnum
from src.config.config_definitions import ALL_CONFIGS, get_config_by_key

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器 - 混合模式（启动时加载 + 缓存 + reload）"""

    # API密钥配置列表（这些配置不从数据库读取，只从.env读取）
    API_KEY_CONFIGS = {
        'BINANCE_API_KEY', 'BINANCE_API_SECRET',
        'BINANCE_TESTNET_API_KEY', 'BINANCE_TESTNET_API_SECRET',
        'OKX_API_KEY', 'OKX_API_SECRET', 'OKX_PASSPHRASE',
        'OKX_TESTNET_API_KEY', 'OKX_TESTNET_API_SECRET', 'OKX_TESTNET_PASSPHRASE',
        'AI_API_KEY',
        'WEB_USER', 'WEB_PASSWORD',  # Web认证凭据也从.env读取
    }

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._loaded = False
        self._default_values: Dict[str, str] = {}

        # 构建默认值字典（从 config_definitions.py）
        for config_def in ALL_CONFIGS:
            self._default_values[config_def['config_key']] = config_def['default_value']

        # 首次加载配置
        self.reload()

    def reload(self):
        """重新从数据库加载所有配置到缓存"""
        try:
            logger.info("正在从数据库加载配置...")
            new_cache = {}

            with db_manager.get_session() as session:
                # 查询所有活跃配置
                configs = session.query(Configuration).filter(
                    Configuration.status == ConfigStatusEnum.ACTIVE
                ).all()

                for config in configs:
                    # 跳过API密钥配置
                    if config.config_key in self.API_KEY_CONFIGS:
                        continue

                    # 解析配置值
                    parsed_value = self._parse_value(
                        config.config_value,
                        config.data_type
                    )
                    new_cache[config.config_key] = parsed_value

            # 原子性更新缓存
            self._cache = new_cache
            self._loaded = True

            logger.info(f"✓ 成功加载 {len(self._cache)} 个配置项到缓存")

        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            if not self._loaded:
                # 首次加载失败，使用默认值
                logger.warning("使用默认配置值")
                self._cache = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（三级优先级）

        优先级：
        1. API密钥配置 -> 从.env读取
        2. 其他配置 -> 数据库缓存 > .env > 默认值 > default参数

        Args:
            key: 配置键
            default: 如果所有来源都没有，返回此默认值

        Returns:
            配置值
        """
        # 1. API密钥配置直接从环境变量读取
        if key in self.API_KEY_CONFIGS:
            return os.getenv(key, default or '')

        # 2. 尝试从缓存读取（数据库配置）
        if key in self._cache:
            return self._cache[key]

        # 3. 尝试从.env读取
        env_value = os.getenv(key)
        if env_value is not None:
            # 根据配置定义解析类型
            try:
                config_def = get_config_by_key(key)
                return self._parse_value(env_value, config_def['data_type'])
            except ValueError:
                # 配置键不在定义中，返回原始字符串
                return env_value

        # 4. 使用配置定义中的默认值
        if key in self._default_values:
            default_value = self._default_values[key]
            # 解析默认值
            try:
                config_def = get_config_by_key(key)
                return self._parse_value(default_value, config_def['data_type'])
            except Exception:
                return default_value

        # 5. 返回函数参数的默认值
        return default

    def get_all(self, include_api_keys: bool = False) -> Dict[str, Any]:
        """
        获取所有配置（用于导出）

        Args:
            include_api_keys: 是否包含API密钥配置

        Returns:
            配置字典
        """
        all_configs = self._cache.copy()

        if include_api_keys:
            # 添加API密钥配置（从.env读取）
            for key in self.API_KEY_CONFIGS:
                value = os.getenv(key)
                if value:
                    all_configs[key] = value

        return all_configs

    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值（仅更新缓存，不写入数据库）

        注意：要持久化配置，应该通过API端点更新数据库

        Args:
            key: 配置键
            value: 配置值

        Returns:
            是否成功
        """
        if key in self.API_KEY_CONFIGS:
            logger.warning(f"API密钥配置 {key} 不应通过ConfigLoader设置，请直接修改.env文件")
            return False

        self._cache[key] = value
        return True

    def _parse_value(self, value: str, data_type: str) -> Any:
        """
        根据数据类型解析配置值

        Args:
            value: 字符串形式的配置值
            data_type: 数据类型（string/number/boolean/json）

        Returns:
            解析后的值
        """
        if data_type == 'string':
            return str(value)

        elif data_type == 'number':
            # 尝试转换为浮点数或整数
            try:
                if '.' in str(value):
                    return float(value)
                else:
                    return int(value)
            except (ValueError, TypeError):
                logger.warning(f"无法将 '{value}' 转换为数字，返回原始值")
                return value

        elif data_type == 'boolean':
            # 布尔值转换
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)

        elif data_type == 'json':
            # JSON解析
            if isinstance(value, (dict, list)):
                return value
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"无法解析JSON: {value}")
                return {}

        else:
            # 未知类型，返回原始值
            return value

    def is_loaded(self) -> bool:
        """检查配置是否已加载"""
        return self._loaded

    def get_cache_size(self) -> int:
        """获取缓存中的配置项数量"""
        return len(self._cache)

    def clear_cache(self):
        """清空缓存（用于测试）"""
        self._cache = {}
        self._loaded = False


# 全局配置加载器实例
config_loader = ConfigLoader()


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """便捷函数：获取配置值"""
    return config_loader.get(key, default)


def reload_config():
    """便捷函数：重新加载配置"""
    config_loader.reload()


def get_all_configs(include_api_keys: bool = False) -> Dict[str, Any]:
    """便捷函数：获取所有配置"""
    return config_loader.get_all(include_api_keys)


if __name__ == '__main__':
    # 测试代码
    print("ConfigLoader 测试")
    print("=" * 60)

    # 测试获取配置
    print(f"INITIAL_GRID: {config_loader.get('INITIAL_GRID')}")
    print(f"MIN_TRADE_AMOUNT: {config_loader.get('MIN_TRADE_AMOUNT')}")
    print(f"SYMBOLS: {config_loader.get('SYMBOLS')}")
    print(f"ENABLE_STOP_LOSS: {config_loader.get('ENABLE_STOP_LOSS')}")
    print(f"GRID_PARAMS_JSON: {config_loader.get('GRID_PARAMS_JSON')}")

    # 测试API密钥配置
    print(f"\nBINANCE_API_KEY: {config_loader.get('BINANCE_API_KEY', '(未设置)')[:10]}...")

    # 缓存信息
    print(f"\n缓存状态:")
    print(f"  已加载: {config_loader.is_loaded()}")
    print(f"  配置数量: {config_loader.get_cache_size()}")

    print("\n✓ 测试完成")
