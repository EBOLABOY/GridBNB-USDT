from datetime import datetime
# 可能需要导入 GridTrader 以进行类型提示，但这会再次引入循环依赖
# from trader import GridTrader # 暂时注释掉

class TradingMonitor:
    def __init__(self, trader):
        """初始化交易监控器。

        Args:
            trader: GridTrader 的实例。
        """
        self.trader = trader # 保持对 trader 实例的引用
        self.trade_history = [] # 存储交易历史记录

    async def get_current_status(self):
        """获取当前的交易状态。"""
        # 注意：确保 GridTrader 类中有这些属性和方法
        total_assets = 0
        position_ratio = 0
        volatility = 0
        win_rate = 0

        # 安全地调用 trader 的方法，处理可能的异常或属性缺失
        try:
            # 确认 GridTrader 中获取交易对资产的方法名
            if hasattr(self.trader, '_get_pair_specific_assets_value') and callable(getattr(self.trader, '_get_pair_specific_assets_value')):
                total_assets = await self.trader._get_pair_specific_assets_value()
            elif hasattr(self.trader, 'total_assets'): # 备选：直接访问属性
                 total_assets = self.trader.total_assets
        except Exception as e:
            print(f"Error getting total assets in monitor: {e}")
            # 可以设置默认值或记录错误

        try:
            # 使用风控管理器获取仓位比例，需要先获取账户快照
            if hasattr(self.trader, 'risk_manager') and hasattr(self.trader.risk_manager, '_get_position_ratio'):
                spot_balance = await self.trader.exchange.fetch_balance()
                funding_balance = await self.trader.exchange.fetch_funding_balance()
                position_ratio = await self.trader.risk_manager._get_position_ratio(spot_balance, funding_balance)
        except Exception as e:
            print(f"Error getting position ratio in monitor: {e}")

        try:
            if hasattr(self.trader, '_calculate_volatility') and callable(getattr(self.trader, '_calculate_volatility')):
                 volatility = await self.trader._calculate_volatility()
        except Exception as e:
            print(f"Error getting volatility in monitor: {e}")

        try:
            if hasattr(self.trader, 'calculate_win_rate') and callable(getattr(self.trader, 'calculate_win_rate')):
                 win_rate = await self.trader.calculate_win_rate()
        except Exception as e:
            print(f"Error getting win rate in monitor: {e}")

        return {
            "timestamp": datetime.now().isoformat(),
            "symbol": getattr(self.trader, 'symbol', 'N/A'), # 添加交易对信息
            "base_price": getattr(self.trader, 'base_price', 0),
            "current_price": getattr(self.trader, 'current_price', 0),
            "grid_size": getattr(self.trader, 'grid_size', 0),
            "volatility": volatility,
            "win_rate": win_rate,
            "total_assets": total_assets,
            "position_ratio": position_ratio,
            # 可以添加更多状态信息
            "initialized": getattr(self.trader, 'initialized', False),
            "active_buy_order": getattr(self.trader.active_orders, 'buy', None),
            "active_sell_order": getattr(self.trader.active_orders, 'sell', None),
            "highest_price_monitor": getattr(self.trader, 'highest', None),
            "lowest_price_monitor": getattr(self.trader, 'lowest', None),
        }

    def add_trade(self, trade):
        """添加一笔交易到历史记录。

        Args:
            trade (dict): 包含交易信息的字典。
        """
        # 可以添加对 trade 结构的基本验证
        required_keys = ['timestamp', 'side', 'price', 'amount', 'order_id']
        if not all(key in trade for key in required_keys):
            print(f"Warning: Invalid trade format received: {trade}")
            return

        self.trade_history.append(trade)
        # 限制历史记录的大小
        max_history = 50
        if len(self.trade_history) > max_history:
            self.trade_history.pop(0) # 移除最旧的记

    def get_trade_history(self, limit=10):
         """获取最近的交易历史记录。

         Args:
             limit (int): 返回的记录数量。

         Returns:
             list: 最近的交易记录列表。
         """
         return self.trade_history[-limit:] 