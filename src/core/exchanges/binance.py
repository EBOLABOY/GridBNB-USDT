"""
币安交易所实现

提供币安交易所的完整功能支持，包括：
- 现货交易
- Simple Earn 理财功能
- 精度处理
- 时间同步

作者: GridBNB Team
版本: 1.0.0
"""

import ccxt.async_support as ccxt
import asyncio
import time
from typing import Dict, Optional
from src.core.exchanges.base import (
    BaseExchange,
    ISavingsFeature,
    ExchangeCapabilities
)
from src.core.exchanges.factory import ExchangeConfig
from src.config.settings import settings


class BinanceExchange(BaseExchange, ISavingsFeature):
    """
    币安交易所实现

    特性：
    - 完整的现货交易支持
    - Simple Earn 理财功能
    - 灵活的精度处理
    - 自动时间同步
    """

    def __init__(self, config: ExchangeConfig):
        """
        初始化币安交易所

        Args:
            config: 交易所配置
        """
        # 调用基类初始化
        super().__init__('binance', config)

        # 币安特定配置
        self.savings_precisions = settings.SAVINGS_PRECISIONS

        # 理财余额缓存
        self.funding_balance_cache = {'timestamp': 0, 'data': {}}

        self.logger.info("币安交易所初始化完成")

    def _create_ccxt_instance(self):
        """创建币安CCXT实例"""
        return ccxt.binance({
            **self.config.to_ccxt_config(),
            'options': {
                'defaultType': 'spot',
                'fetchMarkets': {
                    'spot': True,
                    'margin': self.config.enable_margin,
                    'swap': False,
                    'future': False
                },
                'recvWindow': 5000,
                'adjustForTimeDifference': True,
                'warnOnFetchOpenOrdersWithoutSymbol': False,
                'createMarketBuyOrderRequiresPrice': False
            }
        })

    @property
    def capabilities(self):
        """币安支持的功能"""
        caps = [
            ExchangeCapabilities.SPOT_TRADING,
            ExchangeCapabilities.SAVINGS,
        ]
        if self.config.enable_margin:
            caps.append(ExchangeCapabilities.MARGIN_TRADING)
        return caps

    # ========================================================================
    # 理财功能实现 (ISavingsFeature)
    # ========================================================================

    async def fetch_funding_balance(self) -> Dict[str, float]:
        """
        获取币安 Simple Earn 理财余额（支持分页）

        Returns:
            dict: 资产余额映射 {'USDT': 100.0, 'BNB': 5.0}
        """
        if not self.config.enable_savings:
            return {}

        now = time.time()

        # 缓存检查
        if now - self.funding_balance_cache['timestamp'] < self.cache_ttl:
            return self.funding_balance_cache['data']

        all_balances = {}
        current_page = 1
        size_per_page = 100

        try:
            while True:
                params = {'current': current_page, 'size': size_per_page}
                result = await self.exchange.sapi_get_simple_earn_flexible_position(params)

                rows = result.get('rows', [])
                if not rows:
                    break

                for item in rows:
                    asset = item['asset']
                    amount = float(item.get('totalAmount', 0) or 0)
                    if asset in all_balances:
                        all_balances[asset] += amount
                    else:
                        all_balances[asset] = amount

                if len(rows) < size_per_page:
                    break

                current_page += 1
                await asyncio.sleep(0.1)

            # 更新缓存
            self.funding_balance_cache = {
                'timestamp': now,
                'data': all_balances
            }

            self.logger.debug(f"理财余额: {all_balances}")
            return all_balances

        except Exception as e:
            self.logger.error(f"获取理财余额失败: {e}")
            return self.funding_balance_cache.get('data', {})

    async def transfer_to_savings(self, asset: str, amount: float) -> dict:
        """
        从现货账户申购活期理财

        Args:
            asset: 资产名称 (例如 'USDT', 'BNB')
            amount: 申购金额

        Returns:
            dict: 操作结果
        """
        if not self.config.enable_savings:
            raise RuntimeError("理财功能未启用")

        try:
            # 获取产品ID
            product_id = await self._get_flexible_product_id(asset)

            # 格式化金额
            formatted_amount = self._format_savings_amount(asset, amount)

            params = {
                'asset': asset,
                'amount': formatted_amount,
                'productId': product_id,
                'timestamp': int(time.time() * 1000 + self.time_diff)
            }

            self.logger.info(f"申购理财: {formatted_amount} {asset}")
            result = await self.exchange.sapi_post_simple_earn_flexible_subscribe(params)

            # 清除缓存
            self._clear_balance_cache()

            self.logger.info(f"申购成功: {result}")
            return result

        except Exception as e:
            self.logger.error(f"申购理财失败: {e}")
            raise

    async def transfer_to_spot(self, asset: str, amount: float) -> dict:
        """
        从活期理财赎回到现货账户

        Args:
            asset: 资产名称
            amount: 赎回金额

        Returns:
            dict: 操作结果
        """
        if not self.config.enable_savings:
            raise RuntimeError("理财功能未启用")

        try:
            # 获取产品ID
            product_id = await self._get_flexible_product_id(asset)

            # 格式化金额
            formatted_amount = self._format_savings_amount(asset, amount)

            params = {
                'asset': asset,
                'amount': formatted_amount,
                'productId': product_id,
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'redeemType': 'FAST'  # 快速赎回
            }

            self.logger.info(f"赎回理财: {formatted_amount} {asset}")
            result = await self.exchange.sapi_post_simple_earn_flexible_redeem(params)

            # 清除缓存
            self._clear_balance_cache()

            self.logger.info(f"赎回成功: {result}")
            return result

        except Exception as e:
            self.logger.error(f"赎回理财失败: {e}")
            raise

    # ========================================================================
    # 币安特定辅助方法
    # ========================================================================

    async def _get_flexible_product_id(self, asset: str) -> str:
        """
        获取指定资产的活期理财产品ID

        Args:
            asset: 资产名称

        Returns:
            str: 产品ID

        Raises:
            ValueError: 未找到可用产品
        """
        try:
            params = {
                'asset': asset,
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'current': 1,
                'size': 100,
            }
            result = await self.exchange.sapi_get_simple_earn_flexible_list(params)
            products = result.get('rows', [])

            for product in products:
                if product['asset'] == asset and product['status'] == 'PURCHASING':
                    self.logger.debug(f"找到理财产品: {asset} -> {product['productId']}")
                    return product['productId']

            raise ValueError(f"未找到 {asset} 的可用活期理财产品")

        except Exception as e:
            self.logger.error(f"获取理财产品ID失败: {e}")
            raise

    def _format_savings_amount(self, asset: str, amount: float) -> str:
        """
        根据配置格式化理财金额

        Args:
            asset: 资产名称
            amount: 金额

        Returns:
            str: 格式化后的金额字符串
        """
        precision = self.savings_precisions.get(
            asset,
            self.savings_precisions['DEFAULT']
        )
        return f"{float(amount):.{precision}f}"

    def _clear_balance_cache(self):
        """清除余额缓存"""
        self.balance_cache = {'timestamp': 0, 'data': None}
        self.funding_balance_cache = {'timestamp': 0, 'data': {}}
