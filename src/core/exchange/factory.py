"""
交易所工厂模块

提供统一的交易所实例创建接口，根据配置自动实例化对应的交易所适配器。
采用工厂模式 + 单例模式，确保每种交易所只有一个全局实例。
"""

from typing import Dict, Optional
from src.core.exchange.base import BaseExchangeAdapter, ExchangeType
from src.core.exchange.binance_adapter import BinanceAdapter
from src.core.exchange.okx_adapter import OKXAdapter
import logging


class ExchangeFactory:
    """
    交易所工厂类

    职责：
    1. 根据配置创建交易所适配器实例
    2. 管理交易所实例生命周期（单例模式）
    3. 提供统一的实例获取接口

    使用示例：
        ```python
        # 创建币安实例
        binance = ExchangeFactory.create(
            ExchangeType.BINANCE,
            api_key="xxx",
            api_secret="yyy"
        )

        # 创建OKX实例
        okx = ExchangeFactory.create(
            ExchangeType.OKX,
            api_key="xxx",
            api_secret="yyy",
            passphrase="zzz"  # OKX特有
        )

        # 获取已创建的实例（单例）
        binance_again = ExchangeFactory.get_instance(ExchangeType.BINANCE)
        assert binance is binance_again  # True
        ```
    """

    _instances: Dict[ExchangeType, BaseExchangeAdapter] = {}
    _logger = logging.getLogger("ExchangeFactory")

    # 交易所类型到适配器类的映射
    _ADAPTER_REGISTRY = {
        ExchangeType.BINANCE: BinanceAdapter,
        ExchangeType.OKX: OKXAdapter,
        # 未来扩展：
        # ExchangeType.BYBIT: BybitAdapter,
        # ExchangeType.HUOBI: HuobiAdapter,
    }

    @classmethod
    def create(
        cls,
        exchange_type: ExchangeType,
        api_key: str,
        api_secret: str,
        **kwargs
    ) -> BaseExchangeAdapter:
        """
        创建交易所适配器实例（单例）

        Args:
            exchange_type: 交易所类型
            api_key: API密钥
            api_secret: API密钥密码
            **kwargs: 交易所特定参数（如OKX的passphrase）

        Returns:
            交易所适配器实例

        Raises:
            ValueError: 不支持的交易所类型
        """
        # 检查是否已存在实例
        if exchange_type in cls._instances:
            cls._logger.warning(
                f"{exchange_type.value} 实例已存在，返回现有实例"
            )
            return cls._instances[exchange_type]

        # 查找对应的适配器类
        adapter_class = cls._ADAPTER_REGISTRY.get(exchange_type)
        if not adapter_class:
            raise ValueError(
                f"不支持的交易所类型: {exchange_type.value}\n"
                f"支持的交易所: {[e.value for e in cls._ADAPTER_REGISTRY.keys()]}"
            )

        # 创建实例
        cls._logger.info(f"创建 {exchange_type.value} 适配器实例...")
        instance = adapter_class(
            api_key=api_key,
            api_secret=api_secret,
            **kwargs
        )

        # 缓存实例
        cls._instances[exchange_type] = instance

        cls._logger.info(f"✅ {exchange_type.value} 适配器创建成功")
        return instance

    @classmethod
    def get_instance(cls, exchange_type: ExchangeType) -> Optional[BaseExchangeAdapter]:
        """
        获取已创建的交易所实例

        Args:
            exchange_type: 交易所类型

        Returns:
            交易所适配器实例，如果未创建则返回 None
        """
        return cls._instances.get(exchange_type)

    @classmethod
    def has_instance(cls, exchange_type: ExchangeType) -> bool:
        """检查是否已创建指定交易所实例"""
        return exchange_type in cls._instances

    @classmethod
    async def close_all(cls) -> None:
        """关闭所有交易所连接"""
        cls._logger.info("正在关闭所有交易所连接...")

        for exchange_type, instance in cls._instances.items():
            try:
                await instance.close()
                cls._logger.info(f"✅ {exchange_type.value} 连接已关闭")
            except Exception as e:
                cls._logger.error(f"关闭 {exchange_type.value} 连接失败: {e}")

        cls._instances.clear()
        cls._logger.info("所有交易所连接已关闭")

    @classmethod
    def clear_instances(cls) -> None:
        """清空实例缓存（用于测试）"""
        cls._instances.clear()

    @classmethod
    def register_adapter(
        cls,
        exchange_type: ExchangeType,
        adapter_class: type
    ) -> None:
        """
        注册新的交易所适配器（用于扩展）

        Args:
            exchange_type: 交易所类型
            adapter_class: 适配器类（必须继承自 BaseExchangeAdapter）
        """
        if not issubclass(adapter_class, BaseExchangeAdapter):
            raise TypeError(
                f"{adapter_class.__name__} 必须继承自 BaseExchangeAdapter"
            )

        cls._ADAPTER_REGISTRY[exchange_type] = adapter_class
        cls._logger.info(
            f"✅ 注册适配器: {exchange_type.value} -> {adapter_class.__name__}"
        )

    @classmethod
    def get_supported_exchanges(cls) -> list[str]:
        """获取所有支持的交易所列表"""
        return [exchange.value for exchange in cls._ADAPTER_REGISTRY.keys()]


# ==================== 便捷创建函数 ====================

async def create_exchange_from_config(config: Dict) -> BaseExchangeAdapter:
    """
    从配置字典创建交易所实例

    Args:
        config: 配置字典，必须包含:
            - 'exchange': 交易所名称 ('binance', 'okx')
            - 'api_key': API密钥
            - 'api_secret': API密钥密码
            - 其他交易所特定参数

    Returns:
        已初始化的交易所适配器实例

    示例：
        ```python
        config = {
            'exchange': 'okx',
            'api_key': 'xxx',
            'api_secret': 'yyy',
            'passphrase': 'zzz'
        }
        exchange = await create_exchange_from_config(config)
        ```
    """
    exchange_name = config.get('exchange', '').lower()

    # 转换为 ExchangeType 枚举
    try:
        exchange_type = ExchangeType(exchange_name)
    except ValueError:
        raise ValueError(
            f"不支持的交易所: {exchange_name}\n"
            f"支持的交易所: {ExchangeFactory.get_supported_exchanges()}"
        )

    # 提取认证参数
    api_key = config.get('api_key') or config.get('BINANCE_API_KEY') or config.get('OKX_API_KEY')
    api_secret = config.get('api_secret') or config.get('BINANCE_API_SECRET') or config.get('OKX_API_SECRET')

    if not api_key or not api_secret:
        raise ValueError("缺少 API 密钥配置")

    # 提取额外参数
    extra_params = {}
    if exchange_type == ExchangeType.OKX:
        passphrase = config.get('passphrase') or config.get('OKX_PASSPHRASE')
        if not passphrase:
            raise ValueError("OKX 需要提供 'passphrase' 参数")
        extra_params['passphrase'] = passphrase

    # 创建实例
    instance = ExchangeFactory.create(
        exchange_type,
        api_key,
        api_secret,
        **extra_params
    )

    # 初始化连接
    await instance.initialize()

    return instance
