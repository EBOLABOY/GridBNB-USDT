"""
企业级多交易所支持模块

该模块提供了统一的交易所抽象接口，支持多个交易所的集成。

核心组件：
- IExchange: 交易所抽象接口
- ExchangeFactory: 交易所工厂
- BinanceExchange, OKXExchange: 具体实现

设计原则：
- 面向接口编程
- 依赖注入
- 工厂模式
- 策略模式

使用示例：
    >>> from src.core.exchanges import get_exchange_factory, ExchangeConfig
    >>> factory = get_exchange_factory()
    >>> config = ExchangeConfig(exchange_name='binance', api_key='...', api_secret='...')
    >>> exchange = factory.create('binance', config)
    >>> await exchange.load_markets()

作者: GridBNB Team
版本: 1.0.0
"""

from .base import (
    IExchange,
    IBasicTrading,
    ISavingsFeature,
    IMarketData,
    IPrecision,
    BaseExchange,
    ExchangeCapabilities
)
from .factory import ExchangeFactory, ExchangeConfig
from .binance import BinanceExchange
from .okx import OKXExchange
from .utils import ExchangeError, InsufficientFundsError, NetworkError

__all__ = [
    # 接口
    'IExchange',
    'IBasicTrading',
    'ISavingsFeature',
    'IMarketData',
    'IPrecision',
    'BaseExchange',

    # 工厂
    'ExchangeFactory',
    'ExchangeConfig',
    'ExchangeCapabilities',

    # 具体实现
    'BinanceExchange',
    'OKXExchange',

    # 工具
    'ExchangeError',
    'InsufficientFundsError',
    'NetworkError',

    # 辅助函数
    'get_exchange_factory',
]

__version__ = '1.0.0'


def get_exchange_factory() -> ExchangeFactory:
    """
    获取配置好的交易所工厂实例（单例模式）

    Returns:
        ExchangeFactory: 已注册所有支持交易所的工厂实例

    Example:
        >>> factory = get_exchange_factory()
        >>> exchange = factory.create('binance', config)
    """
    if not hasattr(get_exchange_factory, '_instance'):
        factory = ExchangeFactory()

        # 注册所有支持的交易所
        factory.register('binance', BinanceExchange)
        factory.register('okx', OKXExchange)

        get_exchange_factory._instance = factory

    return get_exchange_factory._instance
