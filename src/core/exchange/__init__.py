"""
交易所模块统一导出接口

提供简洁的导入方式：
    from src.core.exchange import ExchangeFactory, create_exchange_from_config
    from src.core.exchange import ExchangeType, ExchangeFeature
"""

from src.core.exchange.base import (
    BaseExchangeAdapter,
    ExchangeType,
    ExchangeFeature,
    ExchangeCapabilities,
)

from src.core.exchange.binance_adapter import BinanceAdapter
from src.core.exchange.okx_adapter import OKXAdapter

from src.core.exchange.factory import (
    ExchangeFactory,
    create_exchange_from_config,
)

__all__ = [
    # 基础类
    'BaseExchangeAdapter',
    'ExchangeType',
    'ExchangeFeature',
    'ExchangeCapabilities',

    # 具体适配器
    'BinanceAdapter',
    'OKXAdapter',

    # 工厂类和便捷函数
    'ExchangeFactory',
    'create_exchange_from_config',
]

# 版本信息
__version__ = '1.0.0'
