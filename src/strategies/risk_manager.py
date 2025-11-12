import logging
import enum
from src.config.settings import settings


class RiskState(enum.Enum):
    """定义风险状态的枚举"""
    ALLOW_ALL = 0        # 允许所有操作
    ALLOW_SELL_ONLY = 1  # 只允许卖出 (仓位已满)
    ALLOW_BUY_ONLY = 2   # 只允许买入 (底仓保护)


class AdvancedRiskManager:
    def __init__(self, trader):
        self.trader = trader
        self.logger = logging.getLogger(self.__class__.__name__)
        # 初始化日志状态标记
        self._min_limit_warning_logged = False
        self._max_limit_warning_logged = False
    
    async def check_position_limits(self, spot_balance, funding_balance) -> RiskState:
        """检查仓位限制并返回相应的风险状态，同时控制日志频率

        优先使用交易对特定的仓位限制（如果配置了），否则使用全局限制。
        """
        try:
            position_ratio = await self._get_position_ratio(spot_balance, funding_balance) # 传递参数

            # 🆕 获取交易对特定的仓位限制（如果配置了）
            symbol_limits = settings.POSITION_LIMITS_JSON.get(self.trader.symbol)
            if symbol_limits:
                max_ratio = symbol_limits['max']
                min_ratio = symbol_limits['min']
                limit_type = f"[{self.trader.symbol}特定]"
            else:
                max_ratio = settings.MAX_POSITION_RATIO
                min_ratio = settings.MIN_POSITION_RATIO
                limit_type = "[全局]"

            # 保存上次的仓位比例
            if not hasattr(self, 'last_position_ratio'):
                self.last_position_ratio = position_ratio

            # 只在仓位比例变化超过0.1%时打印日志
            if abs(position_ratio - self.last_position_ratio) > 0.001:
                self.logger.info(
                    f"风控检查{limit_type} | "
                    f"当前仓位比例: {position_ratio:.2%} | "
                    f"最大允许比例: {max_ratio:.2%} | "
                    f"最小底仓比例: {min_ratio:.2%}"
                )
                self.last_position_ratio = position_ratio

            # 检查仓位是否超限
            if position_ratio > max_ratio:
                # 只有在没打印过日志时才打印
                if not self._max_limit_warning_logged:
                    self.logger.warning(
                        f"{limit_type}仓位超限 ({position_ratio:.2%} > {max_ratio:.2%})，"
                        f"暂停新的买入操作。"
                    )
                    self._max_limit_warning_logged = True  # 标记为已打印

                # 无论是否打印日志，都要重置另一个标记
                self._min_limit_warning_logged = False
                return RiskState.ALLOW_SELL_ONLY

            # 检查是否触发底仓保护
            elif position_ratio < min_ratio:
                # 只有在没打印过日志时才打印
                if not self._min_limit_warning_logged:
                    self.logger.warning(
                        f"{limit_type}底仓保护触发 ({position_ratio:.2%} < {min_ratio:.2%})，"
                        f"暂停新的卖出操作。"
                    )
                    self._min_limit_warning_logged = True  # 标记为已打印

                # 无论是否打印日志，都要重置另一个标记
                self._max_limit_warning_logged = False
                return RiskState.ALLOW_BUY_ONLY

            # 如果仓位在安全范围内
            else:
                # 如果之前有警告，现在恢复正常了，就打印一条恢复信息
                if self._min_limit_warning_logged or self._max_limit_warning_logged:
                    self.logger.info(
                        f"{limit_type}仓位已恢复至正常范围 ({position_ratio:.2%}，"
                        f"限制范围: {min_ratio:.2%} ~ {max_ratio:.2%})。"
                    )

                # 将所有日志标记重置为False
                self._min_limit_warning_logged = False
                self._max_limit_warning_logged = False
                return RiskState.ALLOW_ALL

        except Exception as e:
            self.logger.error(f"风控检查失败: {str(e)}")
            # 在异常情况下也重置标记，以防状态锁死
            self._min_limit_warning_logged = False
            self._max_limit_warning_logged = False
            return RiskState.ALLOW_ALL  # 出现异常时，默认为允许所有操作以避免卡死

    # 保留原方法以保持向后兼容性
    async def multi_layer_check(self):
        """向后兼容的方法，将新的风控状态转换为布尔值"""
        # 获取账户快照
        spot_balance = await self.trader.exchange.fetch_balance()
        funding_balance = await self.trader.exchange.fetch_funding_balance()

        risk_state = await self.check_position_limits(spot_balance, funding_balance)
        return risk_state != RiskState.ALLOW_ALL

    async def _get_position_value(self, spot_balance, funding_balance):
        # balance = await self.trader.exchange.fetch_balance() # 删除，使用参数
        # funding_balance = await self.trader.exchange.fetch_funding_balance() # 删除，使用参数
        if not self.trader.base_asset:
            self.trader.logger.error("基础资产信息未初始化")
            return 0
        base_amount = (
            float(spot_balance.get('free', {}).get(self.trader.base_asset, 0)) +
            float(funding_balance.get(self.trader.base_asset, 0))
        )
        current_price = await self.trader._get_latest_price()
        return base_amount * current_price

    async def _get_position_ratio(self, spot_balance, funding_balance):
        """获取当前仓位占总资产比例"""
        try:
            position_value = await self._get_position_value(spot_balance, funding_balance) # 传递参数
            # balance = await self.trader.exchange.fetch_balance() # 删除，使用参数
            # funding_balance = await self.trader.exchange.fetch_funding_balance() # 删除，使用参数

            quote_balance = (
                float(spot_balance.get('free', {}).get(self.trader.quote_asset, 0)) +
                float(funding_balance.get(self.trader.quote_asset, 0))
            )

            total_assets = position_value + quote_balance
            if total_assets == 0:
                return 0

            ratio = position_value / total_assets
            self.logger.debug(
                f"仓位计算 | "
                f"{self.trader.base_asset}价值: {position_value:.2f} {self.trader.quote_asset} | "
                f"{self.trader.quote_asset}余额: {quote_balance:.2f} | "
                f"总资产: {total_assets:.2f} | "
                f"仓位比例: {ratio:.2%}"
            )
            return ratio
        except Exception as e:
            self.logger.error(f"计算仓位比例失败: {str(e)}")
            return 0

    async def check_market_sentiment(self):
        """检查市场情绪指标"""
        try:
            fear_greed = await self._get_fear_greed_index()
            if fear_greed < 20:  # 极度恐惧
                # 注意：这里修改的是全局设置，会影响所有交易对
                settings.RISK_FACTOR *= 0.5  # 降低风险系数
            elif fear_greed > 80:  # 极度贪婪
                settings.RISK_FACTOR *= 1.2  # 提高风险系数
        except Exception as e:
            self.logger.error(f"获取市场情绪失败: {str(e)}") 