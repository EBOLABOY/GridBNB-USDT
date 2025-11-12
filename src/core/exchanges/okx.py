"""
OKX交易所实现

提供OKX交易所的完整功能支持，包括：
- 现货交易
- Earn 理财功能
- 账户类型转换
- 精度处理

作者: GridBNB Team
版本: 1.0.0
"""

import ccxt.async_support as ccxt
import time
import uuid
from typing import Dict, Optional
from src.core.exchanges.base import (
    BaseExchange,
    ISavingsFeature,
    ExchangeCapabilities
)
from src.core.exchanges.factory import ExchangeConfig


class OKXExchange(BaseExchange, ISavingsFeature):
    """
    OKX交易所实现

    特性：
    - 现货交易支持
    - Earn 理财功能
    - 多账户类型管理
    """

    # OKX账户类型映射
    ACCOUNT_TYPES = {
        'spot': '18',      # 交易账户
        'funding': '6',    # 资金账户
        'savings': '6'     # 理财使用资金账户
    }

    def __init__(self, config: ExchangeConfig):
        """
        初始化OKX交易所

        Args:
            config: 交易所配置
        """
        super().__init__('okx', config)

        # OKX理财余额缓存
        self.funding_balance_cache = {'timestamp': 0, 'data': {}}

        self.logger.info("OKX交易所初始化完成")

    def _create_ccxt_instance(self):
        """创建OKX CCXT实例"""
        config = self.config.to_ccxt_config()

        return ccxt.okx({
            **config,
            'options': {
                'defaultType': 'spot',
            }
        })

    @property
    def capabilities(self):
        """OKX支持的功能"""
        return [
            ExchangeCapabilities.SPOT_TRADING,
            ExchangeCapabilities.SAVINGS,
            ExchangeCapabilities.MARGIN_TRADING,
            ExchangeCapabilities.FUTURES_TRADING,
        ]

    # ========================================================================
    # 理财功能实现 (ISavingsFeature)
    # ========================================================================

    async def fetch_funding_balance(self) -> Dict[str, float]:
        """
        获取OKX资金账户余额

        Returns:
            dict: 资产余额映射
        """
        if not self.config.enable_savings:
            return {}

        now = time.time()

        # 缓存检查
        if now - self.funding_balance_cache['timestamp'] < self.cache_ttl:
            return self.funding_balance_cache['data']

        try:
            # 获取资金账户余额
            result = await self.exchange.private_get_asset_balances({
                'ccy': ''  # 空表示获取所有币种
            })

            balances = {}
            if result.get('code') == '0' and result.get('data'):
                for item in result['data']:
                    asset = item['ccy']
                    amount = float(item.get('bal', 0))
                    if amount > 0:
                        balances[asset] = amount

            # 更新缓存
            self.funding_balance_cache = {
                'timestamp': now,
                'data': balances
            }

            self.logger.debug(f"资金账户余额: {balances}")
            return balances

        except Exception as e:
            self.logger.error(f"获取资金账户余额失败: {e}")
            return self.funding_balance_cache.get('data', {})

    async def transfer_to_savings(self, asset: str, amount: float) -> dict:
        """
        从交易账户转入资金账户（OKX的理财需要先转入资金账户）

        Args:
            asset: 资产名称
            amount: 转账金额

        Returns:
            dict: 操作结果
        """
        if not self.config.enable_savings:
            raise RuntimeError("理财功能未启用")

        try:
            # OKX的转账接口
            params = {
                'ccy': asset,
                'amt': str(amount),
                'from': self.ACCOUNT_TYPES['spot'],    # 从交易账户
                'to': self.ACCOUNT_TYPES['funding'],   # 到资金账户
                'type': '0',  # 内部转账
                'clientId': str(uuid.uuid4())[:32]  # 客户端ID，确保唯一性
            }

            self.logger.info(f"转入资金账户: {amount} {asset}")
            result = await self.exchange.private_post_asset_transfer(params)

            # 清除缓存
            self._clear_balance_cache()

            if result.get('code') == '0':
                self.logger.info(f"转账成功: {result}")
                return result
            else:
                raise Exception(f"转账失败: {result.get('msg', 'Unknown error')}")

        except Exception as e:
            self.logger.error(f"转入资金账户失败: {e}")
            raise

    async def transfer_to_spot(self, asset: str, amount: float) -> dict:
        """
        从资金账户转回交易账户

        Args:
            asset: 资产名称
            amount: 转账金额

        Returns:
            dict: 操作结果
        """
        if not self.config.enable_savings:
            raise RuntimeError("理财功能未启用")

        try:
            params = {
                'ccy': asset,
                'amt': str(amount),
                'from': self.ACCOUNT_TYPES['funding'],  # 从资金账户
                'to': self.ACCOUNT_TYPES['spot'],       # 到交易账户
                'type': '0',
                'clientId': str(uuid.uuid4())[:32]
            }

            self.logger.info(f"转回交易账户: {amount} {asset}")
            result = await self.exchange.private_post_asset_transfer(params)

            # 清除缓存
            self._clear_balance_cache()

            if result.get('code') == '0':
                self.logger.info(f"转账成功: {result}")
                return result
            else:
                raise Exception(f"转账失败: {result.get('msg', 'Unknown error')}")

        except Exception as e:
            self.logger.error(f"转回交易账户失败: {e}")
            raise

    # ========================================================================
    # OKX特定辅助方法
    # ========================================================================

    def _clear_balance_cache(self):
        """清除余额缓存"""
        self.balance_cache = {'timestamp': 0, 'data': None}
        self.funding_balance_cache = {'timestamp': 0, 'data': {}}

    async def get_account_balance(self, account_type: str = 'spot') -> dict:
        """
        获取指定账户类型的余额

        Args:
            account_type: 账户类型 ('spot', 'funding', 'savings')

        Returns:
            dict: 余额数据
        """
        try:
            if account_type == 'funding' or account_type == 'savings':
                return await self.fetch_funding_balance()
            else:
                return await self.fetch_balance()
        except Exception as e:
            self.logger.error(f"获取账户余额失败: {e}")
            return {}
