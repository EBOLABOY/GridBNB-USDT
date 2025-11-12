"""
交易所抽象基类模块

提供统一的交易所接口定义，所有交易所适配器必须实现此接口。
支持核心交易功能和可选的扩展功能（如理财）。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging


class ExchangeType(Enum):
    """支持的交易所类型"""
    BINANCE = "binance"
    OKX = "okx"
    BYBIT = "bybit"  # 预留
    HUOBI = "huobi"  # 预留


class ExchangeFeature(Enum):
    """交易所支持的功能特性"""
    SPOT_TRADING = "spot_trading"           # 现货交易（必须）
    FUNDING_ACCOUNT = "funding_account"     # 理财账户（可选）
    MARGIN_TRADING = "margin_trading"       # 杠杆交易（可选）
    FUTURES_TRADING = "futures_trading"     # 合约交易（可选）
    STAKING = "staking"                     # 质押（可选）


class ExchangeCapabilities:
    """
    交易所能力描述类

    用于声明特定交易所支持哪些功能，不支持的功能会自动降级处理。
    """

    def __init__(self, supported_features: List[ExchangeFeature]):
        self.supported_features = set(supported_features)

    def supports(self, feature: ExchangeFeature) -> bool:
        """检查是否支持某项功能"""
        return feature in self.supported_features

    def require(self, feature: ExchangeFeature) -> None:
        """断言必须支持某项功能，否则抛出异常"""
        if not self.supports(feature):
            raise NotImplementedError(
                f"当前交易所不支持功能: {feature.value}"
            )


class BaseExchangeAdapter(ABC):
    """
    交易所适配器抽象基类

    所有交易所适配器（Binance, OKX等）必须继承此类并实现所有抽象方法。
    提供统一的交易接口，隐藏交易所之间的差异。

    职责：
    1. 定义统一的交易所操作接口
    2. 声明交易所能力（capabilities）
    3. 提供默认的降级处理逻辑
    """

    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        初始化交易所适配器

        Args:
            api_key: API密钥
            api_secret: API密钥密码
            **kwargs: 交易所特定的额外参数（如OKX的passphrase）
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.extra_params = kwargs
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._exchange = None  # CCXT交易所实例
        self._capabilities: Optional[ExchangeCapabilities] = None

    @property
    @abstractmethod
    def exchange_type(self) -> ExchangeType:
        """返回交易所类型"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ExchangeCapabilities:
        """返回交易所支持的功能列表"""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化交易所连接

        - 创建CCXT实例
        - 加载市场数据
        - 验证API密钥
        - 同步服务器时间
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭交易所连接"""
        pass

    # ==================== 核心交易接口（必须实现） ====================

    @abstractmethod
    async def fetch_balance(self, account_type: str = 'spot') -> Dict[str, Any]:
        """
        获取账户余额

        Args:
            account_type: 账户类型 ('spot', 'margin', 'futures')

        Returns:
            统一格式的余额字典:
            {
                'free': {'USDT': 1000.0, 'BTC': 0.5},
                'used': {'USDT': 100.0, 'BTC': 0.1},
                'total': {'USDT': 1100.0, 'BTC': 0.6}
            }
        """
        pass

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取交易对行情

        Args:
            symbol: 交易对符号 (统一格式: 'BTC/USDT')

        Returns:
            行情字典，包含 'last', 'bid', 'ask', 'volume' 等
        """
        pass

    @abstractmethod
    async def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """
        获取订单簿

        Args:
            symbol: 交易对符号
            limit: 深度档位数量

        Returns:
            订单簿字典，包含 'bids' 和 'asks'
        """
        pass

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建订单

        Args:
            symbol: 交易对符号
            order_type: 订单类型 ('limit', 'market')
            side: 买卖方向 ('buy', 'sell')
            amount: 数量
            price: 价格（市价单可为None）
            params: 额外参数

        Returns:
            订单信息字典
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """取消订单"""
        pass

    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """查询订单状态"""
        pass

    @abstractmethod
    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取未成交订单"""
        pass

    @abstractmethod
    async def fetch_my_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取成交历史"""
        pass

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100
    ) -> List[List]:
        """
        获取K线数据

        Args:
            symbol: 交易对
            timeframe: 时间周期 ('1m', '5m', '1h', '1d' 等)
            limit: 数量

        Returns:
            K线数组: [[timestamp, open, high, low, close, volume], ...]
        """
        pass

    # ==================== 精度和限制相关 ====================

    @abstractmethod
    def amount_to_precision(self, symbol: str, amount: float) -> str:
        """将数量调整为交易所要求的精度"""
        pass

    @abstractmethod
    def price_to_precision(self, symbol: str, price: float) -> str:
        """将价格调整为交易所要求的精度"""
        pass

    @abstractmethod
    async def load_markets(self, reload: bool = False) -> Dict[str, Any]:
        """加载市场信息"""
        pass

    def get_market_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取交易对市场信息"""
        if self._exchange and hasattr(self._exchange, 'markets'):
            return self._exchange.markets.get(symbol)
        return None

    # ==================== 可选功能接口（提供默认降级实现） ====================

    async def fetch_funding_balance(self) -> Dict[str, float]:
        """
        获取理财账户余额（可选功能）

        Returns:
            资产余额字典: {'USDT': 1000.0, 'BTC': 0.5}

        Raises:
            NotImplementedError: 如果交易所不支持理财功能
        """
        if not self.capabilities.supports(ExchangeFeature.FUNDING_ACCOUNT):
            self.logger.warning(
                f"{self.exchange_type.value} 不支持理财功能，返回空余额"
            )
            return {}

        # 子类必须重写此方法
        raise NotImplementedError(
            f"{self.__class__.__name__} 必须实现 fetch_funding_balance"
        )

    async def transfer_to_funding(self, asset: str, amount: float) -> bool:
        """
        转账到理财账户（可选功能）

        Args:
            asset: 资产名称
            amount: 转账数量

        Returns:
            是否成功
        """
        if not self.capabilities.supports(ExchangeFeature.FUNDING_ACCOUNT):
            self.logger.warning(
                f"{self.exchange_type.value} 不支持理财功能，跳过转账"
            )
            return False

        raise NotImplementedError(
            f"{self.__class__.__name__} 必须实现 transfer_to_funding"
        )

    async def transfer_to_spot(self, asset: str, amount: float) -> bool:
        """
        从理财账户转回现货（可选功能）

        Args:
            asset: 资产名称
            amount: 转账数量

        Returns:
            是否成功
        """
        if not self.capabilities.supports(ExchangeFeature.FUNDING_ACCOUNT):
            self.logger.warning(
                f"{self.exchange_type.value} 不支持理财功能，跳过转账"
            )
            return False

        raise NotImplementedError(
            f"{self.__class__.__name__} 必须实现 transfer_to_spot"
        )

    # ==================== 工具方法 ====================

    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化交易对符号为统一格式

        Args:
            symbol: 原始交易对符号

        Returns:
            标准格式: 'BTC/USDT'
        """
        # 默认实现：已经是标准格式
        return symbol

    def get_exchange_symbol(self, symbol: str) -> str:
        """
        转换为交易所特定格式

        Args:
            symbol: 标准格式交易对 'BTC/USDT'

        Returns:
            交易所格式（如OKX的 'BTC-USDT'）
        """
        # 默认实现：CCXT会自动处理
        return symbol

    async def health_check(self) -> Tuple[bool, str]:
        """
        健康检查

        Returns:
            (是否健康, 状态描述)
        """
        try:
            # 简单的ping测试
            await self.fetch_ticker('BTC/USDT')
            return True, "健康"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(exchange={self.exchange_type.value})>"
