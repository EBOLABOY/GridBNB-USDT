"""
交易所工厂模式实现

提供统一的交易所创建和管理接口，支持：
- 动态注册交易所实现
- 统一的配置管理
- 单例模式支持

作者: GridBNB Team
版本: 1.0.0
"""

from typing import Dict, Type, Optional, List
from dataclasses import dataclass, field
from src.core.exchanges.base import IExchange
import logging


@dataclass
class ExchangeConfig:
    """
    交易所配置类

    使用 dataclass 简化配置管理，提供类型安全和默认值支持
    """

    # 基本配置
    exchange_name: str
    api_key: str
    api_secret: str

    # 可选配置
    passphrase: Optional[str] = None  # OKX等需要
    proxy: Optional[str] = None
    timeout: int = 60000  # 毫秒
    enable_rate_limit: bool = True

    # 功能开关
    enable_savings: bool = True
    enable_margin: bool = False
    enable_futures: bool = False

    # 自定义选项
    custom_options: Dict = field(default_factory=dict)

    # 调试选项
    verbose: bool = False

    def to_ccxt_config(self) -> dict:
        """
        转换为CCXT配置格式

        Returns:
            dict: CCXT可用的配置字典
        """
        config = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': self.enable_rate_limit,
            'timeout': self.timeout,
            'verbose': self.verbose,
        }

        # 添加代理
        if self.proxy:
            config['aiohttp_proxy'] = self.proxy

        # 添加passphrase（OKX需要）
        if self.passphrase:
            config['password'] = self.passphrase

        # 合并自定义选项
        if self.custom_options:
            config.update(self.custom_options)

        return config

    def validate(self) -> None:
        """
        验证配置有效性

        Raises:
            ValueError: 配置无效时抛出
        """
        if not self.exchange_name:
            raise ValueError("exchange_name 不能为空")

        if not self.api_key:
            raise ValueError("api_key 不能为空")

        if not self.api_secret:
            raise ValueError("api_secret 不能为空")

        # OKX必须有passphrase
        if self.exchange_name.lower() == 'okx' and not self.passphrase:
            raise ValueError("OKX交易所必须提供 passphrase")

        if self.timeout < 1000:
            raise ValueError("timeout 不能小于 1000ms")


class ExchangeFactory:
    """
    交易所工厂类

    采用工厂模式管理交易所实例的创建，支持：
    - 动态注册新交易所
    - 统一的实例创建接口
    - 配置验证

    示例:
        >>> factory = ExchangeFactory()
        >>> factory.register('binance', BinanceExchange)
        >>> config = ExchangeConfig(exchange_name='binance', api_key='...', api_secret='...')
        >>> exchange = factory.create('binance', config)
    """

    def __init__(self):
        """初始化工厂"""
        self._registry: Dict[str, Type[IExchange]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def register(self, name: str, exchange_class: Type[IExchange]) -> None:
        """
        注册交易所实现类

        Args:
            name: 交易所名称（小写，例如 'binance', 'okx'）
            exchange_class: 交易所实现类

        Raises:
            ValueError: 如果名称已存在或类不符合接口
        """
        name = name.lower()

        # 验证类是否实现了IExchange接口
        if not issubclass(exchange_class, IExchange):
            raise ValueError(
                f"交易所类 {exchange_class.__name__} 必须实现 IExchange 接口"
            )

        # 检查是否已注册
        if name in self._registry:
            self.logger.warning(f"交易所 '{name}' 已注册，将被覆盖")

        self._registry[name] = exchange_class
        self.logger.info(f"注册交易所: {name} -> {exchange_class.__name__}")

    def unregister(self, name: str) -> None:
        """
        取消注册交易所

        Args:
            name: 交易所名称
        """
        name = name.lower()
        if name in self._registry:
            del self._registry[name]
            self.logger.info(f"取消注册交易所: {name}")

    def create(self, name: str, config: ExchangeConfig) -> IExchange:
        """
        创建交易所实例

        Args:
            name: 交易所名称
            config: 交易所配置

        Returns:
            IExchange: 交易所实例

        Raises:
            ValueError: 交易所未注册或配置无效
        """
        name = name.lower()

        # 检查是否已注册
        if name not in self._registry:
            available = ', '.join(self.get_supported_exchanges())
            raise ValueError(
                f"交易所 '{name}' 未注册。\n"
                f"支持的交易所: {available}\n"
                f"请先调用 factory.register('{name}', ExchangeClass)"
            )

        # 验证配置
        try:
            config.validate()
        except ValueError as e:
            raise ValueError(f"交易所配置无效: {e}")

        # 创建实例
        exchange_class = self._registry[name]
        try:
            instance = exchange_class(config)
            self.logger.info(f"成功创建交易所实例: {name}")
            return instance
        except Exception as e:
            self.logger.error(f"创建交易所实例失败 {name}: {e}")
            raise

    def get_supported_exchanges(self) -> List[str]:
        """
        获取所有已注册的交易所列表

        Returns:
            List[str]: 交易所名称列表
        """
        return list(self._registry.keys())

    def is_registered(self, name: str) -> bool:
        """
        检查交易所是否已注册

        Args:
            name: 交易所名称

        Returns:
            bool: 是否已注册
        """
        return name.lower() in self._registry

    def get_exchange_class(self, name: str) -> Type[IExchange]:
        """
        获取交易所实现类（用于高级场景）

        Args:
            name: 交易所名称

        Returns:
            Type[IExchange]: 交易所类

        Raises:
            ValueError: 交易所未注册
        """
        name = name.lower()
        if name not in self._registry:
            raise ValueError(f"交易所 '{name}' 未注册")
        return self._registry[name]

    def __repr__(self) -> str:
        """字符串表示"""
        exchanges = ', '.join(self.get_supported_exchanges())
        return f"ExchangeFactory(registered={len(self._registry)}: [{exchanges}])"
