"""
OKX交易所适配器

实现OKX交易所的完整功能，包括：
- 现货交易
- 余币宝（理财）功能
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


class OKXAdapter(BaseExchangeAdapter):
    """
    OKX交易所适配器

    支持功能：
    - ✅ 现货交易
    - ✅ 余币宝（理财）
    - ✅ 账户划转

    OKX特性：
    - 需要额外的 passphrase 参数
    - 理财功能称为"余币宝"（Savings）
    - 账户类型：trading(交易)、funding(资金)
    """

    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        初始化OKX适配器

        Args:
            api_key: API密钥
            api_secret: API密钥密码
            **kwargs: 必须包含 'passphrase' (OKX特有)
        """
        super().__init__(api_key, api_secret, **kwargs)

        # OKX必须提供passphrase
        self.passphrase = kwargs.get('passphrase')
        if not self.passphrase:
            raise ValueError("OKX 需要提供 'passphrase' 参数")

    @property
    def exchange_type(self) -> ExchangeType:
        return ExchangeType.OKX

    @property
    def capabilities(self) -> ExchangeCapabilities:
        """OKX支持现货交易和理财功能"""
        return ExchangeCapabilities([
            ExchangeFeature.SPOT_TRADING,
            ExchangeFeature.FUNDING_ACCOUNT,
        ])

    async def initialize(self) -> None:
        """初始化OKX连接"""
        self.logger.info("正在初始化OKX交易所连接...")

        self._exchange = ccxt.okx({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'password': self.passphrase,  # OKX特有
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })

        # 加载市场数据
        await self._exchange.load_markets()

        # 验证连接
        balance = await self._exchange.fetch_balance()
        self.logger.info(
            f"✅ OKX连接成功 | "
            f"账户资产: {len([k for k, v in balance['free'].items() if float(v) > 0])} 种"
        )

    async def close(self) -> None:
        """关闭连接"""
        if self._exchange:
            await self._exchange.close()
            self.logger.info("OKX连接已关闭")

    # ==================== 核心交易接口实现 ====================

    async def fetch_balance(self, account_type: str = 'spot') -> Dict[str, Any]:
        """
        获取账户余额

        OKX账户类型映射：
        - 'spot' -> 'trading' (交易账户)
        - 'funding' -> 'funding' (资金账户)
        """
        # OKX的现货账户叫 'trading'
        okx_account_type = 'trading' if account_type == 'spot' else account_type
        return await self._exchange.fetch_balance({'type': okx_account_type})

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

    async def fetch_my_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]:
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

    # ==================== OKX理财功能实现 ====================

    async def fetch_funding_balance(self) -> Dict[str, float]:
        """
        获取OKX余币宝余额

        OKX理财账户余额查询接口
        """
        try:
            self.logger.debug("获取OKX余币宝余额...")

            # OKX使用 privateGetFinanceSavingsBalance 接口
            response = await self._exchange.privateGetFinanceSavingsBalance()

            # 解析响应
            balances = {}
            if response.get('code') == '0' and 'data' in response:
                for item in response['data']:
                    asset = item.get('ccy')
                    earnings = float(item.get('earnings', 0))  # 理财余额
                    if earnings > 0:
                        balances[asset] = earnings

            self.logger.debug(f"余币宝余额: {balances}")
            return balances

        except Exception as e:
            self.logger.error(f"获取OKX余币宝余额失败: {e}")
            # OKX可能不支持或API有变化，返回空字典
            return {}

    async def transfer_to_funding(self, asset: str, amount: float) -> bool:
        """
        申购OKX余币宝

        Args:
            asset: 资产名称 (如 'USDT')
            amount: 申购数量

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"申购OKX余币宝 | 资产: {asset} | 数量: {amount}")

            # OKX申购接口
            response = await self._exchange.privatePostFinanceSavingsPurchaseRedempt({
                'ccy': asset,
                'amt': str(amount),
                'side': 'purchase',  # purchase=申购, redempt=赎回
                'rate': '0.01'  # 利率（需根据实际情况调整）
            })

            if response.get('code') == '0':
                self.logger.info(f"✅ 申购成功 | {asset}: {amount}")
                return True
            else:
                self.logger.error(f"申购失败: {response.get('msg')}")
                return False

        except Exception as e:
            self.logger.error(f"申购OKX余币宝失败: {e}")
            return False

    async def transfer_to_spot(self, asset: str, amount: float) -> bool:
        """
        从OKX余币宝赎回到交易账户

        Args:
            asset: 资产名称
            amount: 赎回数量

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"赎回OKX余币宝 | 资产: {asset} | 数量: {amount}")

            # OKX赎回接口
            response = await self._exchange.privatePostFinanceSavingsPurchaseRedempt({
                'ccy': asset,
                'amt': str(amount),
                'side': 'redempt',  # redempt=赎回
                'rate': '0.01'
            })

            if response.get('code') == '0':
                self.logger.info(f"✅ 赎回成功 | {asset}: {amount}")
                return True
            else:
                self.logger.error(f"赎回失败: {response.get('msg')}")
                return False

        except Exception as e:
            self.logger.error(f"赎回OKX余币宝失败: {e}")
            return False

    # ==================== OKX特定工具方法 ====================

    def get_exchange_symbol(self, symbol: str) -> str:
        """
        OKX交易对格式转换

        标准格式 'BTC/USDT' -> OKX格式 'BTC-USDT'
        注意：CCXT已经自动处理此转换，这里保留以防需要手动处理
        """
        return symbol.replace('/', '-')

    async def transfer_between_accounts(
        self,
        asset: str,
        amount: float,
        from_account: str,
        to_account: str
    ) -> bool:
        """
        OKX账户间划转

        Args:
            asset: 资产
            amount: 数量
            from_account: 源账户 ('trading', 'funding')
            to_account: 目标账户 ('trading', 'funding')

        Returns:
            是否成功
        """
        try:
            response = await self._exchange.privatePostAssetTransfer({
                'ccy': asset,
                'amt': str(amount),
                'from': from_account,
                'to': to_account,
                'type': '0'  # 0=账户内划转
            })

            if response.get('code') == '0':
                self.logger.info(
                    f"✅ 划转成功 | {asset}: {amount} | "
                    f"{from_account} -> {to_account}"
                )
                return True
            else:
                self.logger.error(f"划转失败: {response.get('msg')}")
                return False

        except Exception as e:
            self.logger.error(f"账户划转失败: {e}")
            return False
