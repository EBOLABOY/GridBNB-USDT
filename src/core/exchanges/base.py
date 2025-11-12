"""
交易所抽象基类和接口定义

该模块定义了所有交易所必须实现的接口，以及提供了通用功能的基类实现。

设计模式：
- 接口隔离原则：将不同功能拆分为独立接口
- 模板方法模式：定义算法骨架，子类实现细节
- 适配器模式：统一不同交易所的API差异

作者: GridBNB Team
版本: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
import time


# ============================================================================
# 交易所能力枚举
# ============================================================================

class ExchangeCapabilities(Enum):
    """交易所能力枚举"""
    SPOT_TRADING = "spot_trading"           # 现货交易
    MARGIN_TRADING = "margin_trading"       # 杠杆交易
    FUTURES_TRADING = "futures_trading"     # 期货交易
    SAVINGS = "savings"                     # 理财功能
    LENDING = "lending"                     # 借贷功能
    STAKING = "staking"                     # 质押功能
    WEBSOCKET = "websocket"                 # WebSocket支持


# ============================================================================
# 核心接口定义
# ============================================================================

class IMarketData(ABC):
    """市场数据接口"""

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> dict:
        """
        获取交易对行情

        Args:
            symbol: 交易对符号，例如 'BNB/USDT'

        Returns:
            dict: 标准化的行情数据
                {
                    'symbol': str,
                    'last': float,      # 最新价
                    'bid': float,       # 买一价
                    'ask': float,       # 卖一价
                    'volume': float,    # 24小时成交量
                    'timestamp': int    # 时间戳（毫秒）
                }
        """
        pass

    @abstractmethod
    async def fetch_order_book(self, symbol: str, limit: int = 5) -> dict:
        """
        获取订单簿

        Args:
            symbol: 交易对符号
            limit: 深度档位数量

        Returns:
            dict: 订单簿数据
                {
                    'bids': [[price, amount], ...],
                    'asks': [[price, amount], ...],
                    'timestamp': int
                }
        """
        pass

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: Optional[int] = None
    ) -> List[List[Union[int, float]]]:
        """
        获取K线数据

        Args:
            symbol: 交易对符号
            timeframe: 时间周期，例如 '1h', '1d'
            limit: 数据条数

        Returns:
            List: K线数据 [[timestamp, open, high, low, close, volume], ...]
        """
        pass


class IBasicTrading(ABC):
    """基础交易接口"""

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[dict] = None
    ) -> dict:
        """
        创建订单

        Args:
            symbol: 交易对符号
            type: 订单类型 ('limit', 'market')
            side: 交易方向 ('buy', 'sell')
            amount: 数量
            price: 价格（市价单可为None）
            params: 额外参数

        Returns:
            dict: 标准化的订单数据
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> dict:
        """取消订单"""
        pass

    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> dict:
        """查询订单"""
        pass

    @abstractmethod
    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[dict]:
        """查询未成交订单"""
        pass

    @abstractmethod
    async def fetch_balance(self, params: Optional[dict] = None) -> dict:
        """
        获取账户余额

        Returns:
            dict: 余额数据
                {
                    'free': {'USDT': 1000.0, 'BNB': 10.0},
                    'used': {'USDT': 100.0},
                    'total': {'USDT': 1100.0, 'BNB': 10.0}
                }
        """
        pass


class ISavingsFeature(ABC):
    """理财功能接口（可选功能）"""

    @abstractmethod
    async def fetch_funding_balance(self) -> Dict[str, float]:
        """
        获取理财账户余额

        Returns:
            dict: 资产余额映射 {'USDT': 100.0, 'BNB': 5.0}
        """
        pass

    @abstractmethod
    async def transfer_to_savings(self, asset: str, amount: float) -> dict:
        """
        从现货账户申购理财

        Args:
            asset: 资产名称
            amount: 申购金额

        Returns:
            dict: 操作结果
        """
        pass

    @abstractmethod
    async def transfer_to_spot(self, asset: str, amount: float) -> dict:
        """
        从理财账户赎回到现货

        Args:
            asset: 资产名称
            amount: 赎回金额

        Returns:
            dict: 操作结果
        """
        pass


class IPrecision(ABC):
    """精度处理接口"""

    @abstractmethod
    def get_symbol_precision(self, symbol: str) -> Dict[str, int]:
        """
        获取交易对精度

        Returns:
            dict: {'amount': 6, 'price': 2}
        """
        pass

    @abstractmethod
    def adjust_amount_precision(self, symbol: str, amount: float) -> Union[float, str]:
        """调整数量精度"""
        pass

    @abstractmethod
    def adjust_price_precision(self, symbol: str, price: float) -> Union[float, str]:
        """调整价格精度"""
        pass


class IExchange(IMarketData, IBasicTrading, IPrecision):
    """
    交易所顶层抽象接口

    所有交易所实现必须继承此接口，提供统一的API
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """交易所名称"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[ExchangeCapabilities]:
        """交易所支持的功能列表"""
        pass

    @abstractmethod
    async def load_markets(self) -> bool:
        """加载市场数据"""
        pass

    @abstractmethod
    async def sync_time(self) -> None:
        """同步服务器时间"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass

    def supports(self, capability: ExchangeCapabilities) -> bool:
        """
        检查是否支持某项功能

        Args:
            capability: 功能枚举

        Returns:
            bool: 是否支持
        """
        return capability in self.capabilities


# ============================================================================
# 基础实现类
# ============================================================================

class BaseExchange(IExchange):
    """
    交易所基类，提供通用功能的默认实现

    采用模板方法模式：
    - 定义通用算法骨架
    - 子类重写具体实现细节

    子类必须实现：
    - name 属性
    - capabilities 属性
    - _create_ccxt_instance() 方法
    """

    def __init__(self, exchange_name: str, config: 'ExchangeConfig'):
        """
        初始化基类

        Args:
            exchange_name: 交易所名称（对应CCXT的ID）
            config: 交易所配置
        """
        self._exchange_name = exchange_name
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{exchange_name}]")

        # 状态变量
        self.markets_loaded = False
        self.time_diff = 0  # 本地时间与服务器时间差（毫秒）

        # 缓存
        self.balance_cache = {'timestamp': 0, 'data': None}
        self.cache_ttl = 30  # 缓存有效期（秒）

        # 初始化CCXT实例（延迟到子类实现）
        self.exchange = self._create_ccxt_instance()

        self.logger.info(f"交易所 {self.name} 初始化完成")

    @abstractmethod
    def _create_ccxt_instance(self):
        """
        创建CCXT实例（子类必须实现）

        Returns:
            ccxt.Exchange: CCXT交易所实例
        """
        pass

    @property
    def name(self) -> str:
        """交易所名称"""
        return self._exchange_name

    # ------------------------------------------------------------------------
    # 市场数据实现（通用）
    # ------------------------------------------------------------------------

    async def load_markets(self) -> bool:
        """加载市场数据"""
        try:
            await self.sync_time()
            await self.exchange.load_markets()
            self.markets_loaded = True
            self.logger.info(f"市场数据加载成功，共 {len(self.exchange.markets)} 个交易对")
            return True
        except Exception as e:
            self.logger.error(f"加载市场数据失败: {e}")
            self.markets_loaded = False
            raise

    async def fetch_ticker(self, symbol: str) -> dict:
        """获取行情"""
        try:
            market = self.exchange.market(symbol)
            ticker = await self.exchange.fetch_ticker(market['id'])

            # 标准化输出
            return {
                'symbol': symbol,
                'last': float(ticker.get('last', 0)),
                'bid': float(ticker.get('bid', 0)),
                'ask': float(ticker.get('ask', 0)),
                'volume': float(ticker.get('baseVolume', 0)),
                'timestamp': ticker.get('timestamp', int(time.time() * 1000))
            }
        except Exception as e:
            self.logger.error(f"获取行情失败 {symbol}: {e}")
            raise

    async def fetch_order_book(self, symbol: str, limit: int = 5) -> dict:
        """获取订单簿"""
        try:
            market = self.exchange.market(symbol)
            order_book = await self.exchange.fetch_order_book(market['id'], limit=limit)
            return order_book
        except Exception as e:
            self.logger.error(f"获取订单簿失败 {symbol}: {e}")
            raise

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: Optional[int] = None
    ) -> List[List[Union[int, float]]]:
        """获取K线数据"""
        try:
            params = {}
            if limit:
                params['limit'] = limit
            return await self.exchange.fetch_ohlcv(symbol, timeframe, params=params)
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            raise

    # ------------------------------------------------------------------------
    # 交易功能实现（模板方法）
    # ------------------------------------------------------------------------

    async def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[dict] = None
    ) -> dict:
        """
        创建订单（模板方法）

        执行流程：
        1. 同步时间
        2. 调整精度
        3. 构建参数
        4. 执行下单
        5. 标准化输出
        """
        try:
            # 1. 同步时间
            await self.sync_time()

            # 2. 调整精度
            adjusted_amount = self.adjust_amount_precision(symbol, amount)
            adjusted_price = self.adjust_price_precision(symbol, price) if price else None

            # 3. 构建参数
            order_params = params or {}
            order_params.update({
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'recvWindow': 5000
            })

            # 4. 执行下单
            order = await self.exchange.create_order(
                symbol, type, side, adjusted_amount, adjusted_price, order_params
            )

            # 5. 标准化输出
            return self._normalize_order(order)

        except Exception as e:
            self.logger.error(f"创建订单失败: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str) -> dict:
        """取消订单"""
        try:
            params = {
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'recvWindow': 5000
            }
            return await self.exchange.cancel_order(order_id, symbol, params)
        except Exception as e:
            self.logger.error(f"取消订单失败: {e}")
            raise

    async def fetch_order(self, order_id: str, symbol: str) -> dict:
        """查询订单"""
        try:
            params = {
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'recvWindow': 5000
            }
            order = await self.exchange.fetch_order(order_id, symbol, params)
            return self._normalize_order(order)
        except Exception as e:
            self.logger.error(f"查询订单失败: {e}")
            raise

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[dict]:
        """查询未成交订单"""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return [self._normalize_order(order) for order in orders]
        except Exception as e:
            self.logger.error(f"查询未成交订单失败: {e}")
            raise

    async def fetch_balance(self, params: Optional[dict] = None) -> dict:
        """获取余额（带缓存）"""
        now = time.time()
        if now - self.balance_cache['timestamp'] < self.cache_ttl:
            return self.balance_cache['data']

        try:
            params = params or {}
            params['timestamp'] = int(time.time() * 1000 + self.time_diff)

            balance = await self.exchange.fetch_balance(params)

            self.balance_cache = {'timestamp': now, 'data': balance}
            return balance
        except Exception as e:
            self.logger.error(f"获取余额失败: {e}")
            # 返回空余额而非抛出异常
            return {'free': {}, 'used': {}, 'total': {}}

    # ------------------------------------------------------------------------
    # 精度处理实现
    # ------------------------------------------------------------------------

    def get_symbol_precision(self, symbol: str) -> Dict[str, int]:
        """获取交易对精度"""
        if not self.markets_loaded:
            raise RuntimeError("市场数据未加载，请先调用 load_markets()")

        market = self.exchange.market(symbol)
        return {
            'amount': market['precision'].get('amount', 8),
            'price': market['precision'].get('price', 8)
        }

    def adjust_amount_precision(self, symbol: str, amount: float) -> Union[float, str]:
        """调整数量精度"""
        try:
            return self.exchange.amount_to_precision(symbol, amount)
        except Exception as e:
            self.logger.warning(f"精度调整失败，使用默认精度: {e}")
            precision = self.get_symbol_precision(symbol)
            return float(f"{amount:.{precision['amount']}f}")

    def adjust_price_precision(self, symbol: str, price: float) -> Union[float, str]:
        """调整价格精度"""
        try:
            return self.exchange.price_to_precision(symbol, price)
        except Exception as e:
            self.logger.warning(f"价格精度调整失败，使用默认精度: {e}")
            precision = self.get_symbol_precision(symbol)
            return float(f"{price:.{precision['price']}f}")

    # ------------------------------------------------------------------------
    # 时间同步
    # ------------------------------------------------------------------------

    async def sync_time(self) -> None:
        """同步服务器时间"""
        try:
            server_time = await self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            self.time_diff = server_time - local_time
            self.logger.debug(f"时间同步完成，时差: {self.time_diff}ms")
        except Exception as e:
            self.logger.error(f"时间同步失败: {e}")

    # ------------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------------

    async def close(self) -> None:
        """关闭连接"""
        try:
            if self.exchange:
                await self.exchange.close()
                self.logger.info("交易所连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭连接失败: {e}")

    # ------------------------------------------------------------------------
    # 辅助方法（可被子类重写）
    # ------------------------------------------------------------------------

    def _normalize_order(self, raw_order: dict) -> dict:
        """
        标准化订单格式

        将交易所原始订单格式转换为统一格式
        子类可重写以适配特殊情况
        """
        return {
            'id': raw_order.get('id'),
            'symbol': raw_order.get('symbol'),
            'type': raw_order.get('type'),
            'side': raw_order.get('side'),
            'price': float(raw_order.get('price', 0)) if raw_order.get('price') else None,
            'amount': float(raw_order.get('amount', 0)),
            'filled': float(raw_order.get('filled', 0)),
            'remaining': float(raw_order.get('remaining', 0)),
            'status': raw_order.get('status'),
            'timestamp': raw_order.get('timestamp')
        }
