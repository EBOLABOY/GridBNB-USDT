"""
币安交易所适配器

实现币安交易所的完整功能，包括：
- 现货交易
- 简单储蓄（理财）功能
- 账户划转
"""

from typing import Dict, List, Optional, Any
import ccxt.async_support as ccxt
from src.core.exchange.base import (
    BaseExchangeAdapter,
    ExchangeType,
    ExchangeFeature,
    ExchangeCapabilities
)


class BinanceAdapter(BaseExchangeAdapter):
    """
    币安交易所适配器

    支持功能：
    - ✅ 现货交易
    - ✅ 简单储蓄（理财）
    - ✅ 账户划转
    """

    @property
    def exchange_type(self) -> ExchangeType:
        return ExchangeType.BINANCE

    @property
    def capabilities(self) -> ExchangeCapabilities:
        """币安支持现货交易和理财功能"""
        return ExchangeCapabilities([
            ExchangeFeature.SPOT_TRADING,
            ExchangeFeature.FUNDING_ACCOUNT,
        ])

    async def initialize(self) -> None:
        """初始化币安连接"""
        self.logger.info("正在初始化币安交易所连接...")

        self._exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        })

        # 加载市场数据
        await self._exchange.load_markets()

        # 验证连接
        balance = await self._exchange.fetch_balance()
        self.logger.info(
            f"✅ 币安连接成功 | "
            f"账户资产: {len([k for k, v in balance['free'].items() if float(v) > 0])} 种"
        )

    async def close(self) -> None:
        """关闭连接"""
        if self._exchange:
            await self._exchange.close()
            self.logger.info("币安连接已关闭")

    # ==================== 核心交易接口实现 ====================

    async def fetch_balance(self, account_type: str = 'spot') -> Dict[str, Any]:
        """获取账户余额"""
        return await self._exchange.fetch_balance({'type': account_type})

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取行情"""
        return await self._exchange.fetch_ticker(symbol)

    async def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """获取订单簿"""
        return await self._exchange.fetch_order_book(symbol, limit)

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """创建订单"""
        # 币安特定：amount必须是字符串格式（CCXT会自动处理）
        return await self._exchange.create_order(
            symbol, order_type, side, amount, price, params
        )

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """取消订单"""
        return await self._exchange.cancel_order(order_id, symbol)

    async def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """查询订单"""
        return await self._exchange.fetch_order(order_id, symbol)

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取未成交订单"""
        return await self._exchange.fetch_open_orders(symbol)

    async def fetch_my_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取成交历史"""
        return await self._exchange.fetch_my_trades(symbol, limit=limit)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100
    ) -> List[List]:
        """获取K线数据"""
        return await self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    # ==================== 精度处理 ====================

    def amount_to_precision(self, symbol: str, amount: float) -> str:
        """调整数量精度"""
        return self._exchange.amount_to_precision(symbol, amount)

    def price_to_precision(self, symbol: str, price: float) -> str:
        """调整价格精度"""
        return self._exchange.price_to_precision(symbol, price)

    async def load_markets(self, reload: bool = False) -> Dict[str, Any]:
        """加载市场信息"""
        return await self._exchange.load_markets(reload)

    # ==================== 币安理财功能实现 ====================

    async def fetch_funding_balance(self) -> Dict[str, float]:
        """
        获取币安简单储蓄余额

        使用币安 sapi/v1/simple-earn/flexible/position 接口
        """
        try:
            self.logger.debug("获取币安理财账户余额...")

            # 调用币安简单储蓄API
            response = await self._exchange.sapiGetV1SimpleEarnFlexiblePosition()

            # 解析响应
            balances = {}
            if 'rows' in response:
                for item in response['rows']:
                    asset = item.get('asset')
                    total_amount = float(item.get('totalAmount', 0))
                    if total_amount > 0:
                        balances[asset] = total_amount

            self.logger.debug(f"理财余额: {balances}")
            return balances

        except Exception as e:
            self.logger.error(f"获取币安理财余额失败: {e}")
            return {}

    async def transfer_to_funding(self, asset: str, amount: float) -> bool:
        """
        申购币安简单储蓄

        Args:
            asset: 资产名称 (如 'USDT')
            amount: 申购数量

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"申购币安理财 | 资产: {asset} | 数量: {amount}")

            # 调用申购接口
            params = {
                'productId': 'USDT001',  # 币安活期产品ID（需要根据实际情况调整）
                'amount': amount,
                'autoSubscribe': True
            }

            response = await self._exchange.sapiPostV1SimpleEarnFlexibleSubscribe({
                'asset': asset,
                'amount': str(amount)
            })

            self.logger.info(f"✅ 申购成功 | {asset}: {amount}")
            return True

        except Exception as e:
            self.logger.error(f"申购币安理财失败: {e}")
            return False

    async def transfer_to_spot(self, asset: str, amount: float) -> bool:
        """
        从币安简单储蓄赎回到现货

        Args:
            asset: 资产名称
            amount: 赎回数量

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"赎回币安理财 | 资产: {asset} | 数量: {amount}")

            # 调用赎回接口
            response = await self._exchange.sapiPostV1SimpleEarnFlexibleRedeem({
                'asset': asset,
                'amount': str(amount)
            })

            self.logger.info(f"✅ 赎回成功 | {asset}: {amount}")
            return True

        except Exception as e:
            self.logger.error(f"赎回币安理财失败: {e}")
            return False

    # ==================== 币安特定工具方法 ====================

    async def get_account_status(self) -> Dict[str, Any]:
        """获取账户状态（币安特定）"""
        try:
            return await self._exchange.sapiGetV1AccountStatus()
        except Exception as e:
            self.logger.error(f"获取账户状态失败: {e}")
            return {}

    async def get_api_trading_status(self) -> Dict[str, Any]:
        """获取API交易状态（币安特定）"""
        try:
            return await self._exchange.sapiGetV1AccountApiTradingStatus()
        except Exception as e:
            self.logger.error(f"获取API交易状态失败: {e}")
            return {}
