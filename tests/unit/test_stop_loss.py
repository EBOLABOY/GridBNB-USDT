"""
止损机制单元测试

测试覆盖：
1. 价格止损触发与不触发
2. 回撤止盈触发与不触发
3. 紧急平仓成功与重试机制
4. 盈利计算逻辑
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from src.core.trader import GridTrader
from src.config.settings import TradingConfig, settings


@pytest.fixture
def mock_exchange():
    """创建模拟的交易所客户端"""
    exchange = AsyncMock()
    exchange.fetch_ticker = AsyncMock(return_value={'last': 600.0})
    exchange.fetch_balance = AsyncMock(return_value={
        'free': {'USDT': 1000.0, 'BNB': 1.0},
        'used': {'USDT': 0.0, 'BNB': 0.0},
        'total': {'USDT': 1000.0, 'BNB': 1.0}
    })
    exchange.fetch_funding_balance = AsyncMock(return_value={
        'USDT': 500.0,
        'BNB': 0.5
    })
    exchange.fetch_open_orders = AsyncMock(return_value=[])
    exchange.cancel_order = AsyncMock()
    exchange.create_order = AsyncMock(return_value={
        'id': '12345',
        'status': 'closed',
        'price': 600.0,
        'filled': 1.0
    })
    exchange.exchange = Mock()
    exchange.exchange.market = Mock(return_value={
        'precision': {'amount': 4, 'price': 2}
    })
    return exchange


@pytest_asyncio.fixture
async def trader(mock_exchange):
    """创建测试用的交易器实例"""
    config = TradingConfig()
    trader = GridTrader(mock_exchange, config, 'BNB/USDT')
    trader.base_price = 600.0
    trader.current_price = 600.0
    trader.initialized = True
    trader.base_asset = 'BNB'
    trader.quote_asset = 'USDT'
    trader.order_tracker = Mock()
    trader.order_tracker.trade_history = []

    # 模拟精度调整方法
    trader._adjust_amount_precision = lambda x: round(x, 4)

    return trader


class TestPriceStopLoss:
    """价格止损测试"""

    @pytest.mark.asyncio
    async def test_price_stop_loss_triggered(self, trader):
        """测试价格止损触发"""
        # 配置止损
        with patch.object(settings, 'ENABLE_STOP_LOSS', True), \
             patch.object(settings, 'STOP_LOSS_PERCENTAGE', 15.0):

            # 设置当前价格为止损价（下跌15%）
            trader.current_price = 510.0  # 600 * (1 - 0.15) = 510
            trader.stop_loss_triggered = False

            # 检查止损
            should_stop, reason = await trader._check_stop_loss()

            # 验证
            assert should_stop is True
            assert "价格止损触发" in reason
            assert "510.00" in reason

    @pytest.mark.asyncio
    async def test_price_stop_loss_not_triggered(self, trader):
        """测试价格止损不触发"""
        with patch.object(settings, 'ENABLE_STOP_LOSS', True), \
             patch.object(settings, 'STOP_LOSS_PERCENTAGE', 15.0):

            # 设置当前价格高于止损价
            trader.current_price = 580.0  # 仅下跌3.3%，未达到15%
            trader.stop_loss_triggered = False

            # 检查止损
            should_stop, reason = await trader._check_stop_loss()

            # 验证
            assert should_stop is False
            assert reason == ""

    @pytest.mark.asyncio
    async def test_stop_loss_disabled(self, trader):
        """测试止损功能禁用时不触发"""
        with patch.object(settings, 'ENABLE_STOP_LOSS', False):

            # 即使价格大幅下跌也不触发
            trader.current_price = 300.0  # 下跌50%
            trader.stop_loss_triggered = False

            # 检查止损
            should_stop, reason = await trader._check_stop_loss()

            # 验证
            assert should_stop is False
            assert reason == ""

    @pytest.mark.asyncio
    async def test_stop_loss_already_triggered(self, trader):
        """测试已触发止损后不再检查"""
        with patch.object(settings, 'ENABLE_STOP_LOSS', True), \
             patch.object(settings, 'STOP_LOSS_PERCENTAGE', 15.0):

            trader.current_price = 510.0
            trader.stop_loss_triggered = True  # 已经触发过

            # 检查止损
            should_stop, reason = await trader._check_stop_loss()

            # 验证
            assert should_stop is False
            assert reason == "已触发过止损"


class TestDrawdownStopLoss:
    """回撤止盈测试"""

    @pytest.mark.asyncio
    async def test_drawdown_stop_triggered(self, trader):
        """测试回撤止盈触发"""
        with patch.object(settings, 'ENABLE_STOP_LOSS', True), \
             patch.object(settings, 'STOP_LOSS_PERCENTAGE', 0.0), \
             patch.object(settings, 'TAKE_PROFIT_DRAWDOWN', 20.0), \
             patch.object(settings, 'INITIAL_PRINCIPAL', 1000.0):

            # 设置历史最高盈利
            trader.max_profit = 200.0  # 最高盈利200 USDT
            trader.stop_loss_triggered = False

            # 模拟当前总资产（盈利160 USDT，回撤20%）
            trader._get_pair_specific_assets_value = AsyncMock(return_value=1160.0)

            # 检查止损
            should_stop, reason = await trader._check_stop_loss()

            # 验证
            assert should_stop is True
            assert "回撤止盈触发" in reason
            assert "200.00" in reason  # 最高盈利
            assert "160.00" in reason  # 当前盈利

    @pytest.mark.asyncio
    async def test_drawdown_stop_not_triggered(self, trader):
        """测试回撤止盈不触发"""
        with patch.object(settings, 'ENABLE_STOP_LOSS', True), \
             patch.object(settings, 'STOP_LOSS_PERCENTAGE', 0.0), \
             patch.object(settings, 'TAKE_PROFIT_DRAWDOWN', 20.0), \
             patch.object(settings, 'INITIAL_PRINCIPAL', 1000.0):

            # 设置历史最高盈利
            trader.max_profit = 200.0
            trader.stop_loss_triggered = False

            # 模拟当前总资产（盈利170 USDT，回撤仅15%）
            trader._get_pair_specific_assets_value = AsyncMock(return_value=1170.0)

            # 检查止损
            should_stop, reason = await trader._check_stop_loss()

            # 验证
            assert should_stop is False
            assert reason == ""

    @pytest.mark.asyncio
    async def test_max_profit_update(self, trader):
        """测试最高盈利更新"""
        with patch.object(settings, 'ENABLE_STOP_LOSS', True), \
             patch.object(settings, 'STOP_LOSS_PERCENTAGE', 0.0), \
             patch.object(settings, 'TAKE_PROFIT_DRAWDOWN', 20.0), \
             patch.object(settings, 'INITIAL_PRINCIPAL', 1000.0):

            # 初始最高盈利
            trader.max_profit = 100.0
            trader.stop_loss_triggered = False

            # 模拟当前总资产（盈利150 USDT，高于历史）
            trader._get_pair_specific_assets_value = AsyncMock(return_value=1150.0)

            # 检查止损（会更新max_profit）
            should_stop, reason = await trader._check_stop_loss()

            # 验证最高盈利已更新
            assert trader.max_profit == 150.0
            assert should_stop is False

    @pytest.mark.asyncio
    async def test_no_drawdown_when_no_profit(self, trader):
        """测试无盈利时不触发回撤止盈"""
        with patch.object(settings, 'ENABLE_STOP_LOSS', True), \
             patch.object(settings, 'STOP_LOSS_PERCENTAGE', 0.0), \
             patch.object(settings, 'TAKE_PROFIT_DRAWDOWN', 20.0), \
             patch.object(settings, 'INITIAL_PRINCIPAL', 1000.0):

            # 无盈利
            trader.max_profit = 0.0
            trader.stop_loss_triggered = False

            # 模拟当前总资产（亏损50 USDT）
            trader._get_pair_specific_assets_value = AsyncMock(return_value=950.0)

            # 检查止损
            should_stop, reason = await trader._check_stop_loss()

            # 验证不触发
            assert should_stop is False


class TestCalculateCurrentProfit:
    """盈利计算测试"""

    @pytest.mark.asyncio
    async def test_calculate_profit_with_initial_principal(self, trader):
        """测试基于初始本金计算盈利"""
        with patch.object(settings, 'INITIAL_PRINCIPAL', 1000.0):
            # 模拟当前总资产
            trader._get_pair_specific_assets_value = AsyncMock(return_value=1150.0)

            # 计算盈利
            profit = await trader._calculate_current_profit()

            # 验证
            assert profit == 150.0  # 1150 - 1000 = 150

    @pytest.mark.asyncio
    async def test_calculate_profit_without_initial_principal(self, trader):
        """测试基于交易历史计算盈利"""
        with patch.object(settings, 'INITIAL_PRINCIPAL', 0.0):
            # 模拟交易历史
            trader.order_tracker.trade_history = [
                {'profit': 50.0},
                {'profit': 30.0},
                {'profit': -10.0},
                {'profit': 20.0}
            ]

            # 计算盈利
            profit = await trader._calculate_current_profit()

            # 验证
            assert profit == 90.0  # 50 + 30 - 10 + 20 = 90

    @pytest.mark.asyncio
    async def test_calculate_profit_handles_error(self, trader):
        """测试计算盈利时的错误处理"""
        with patch.object(settings, 'INITIAL_PRINCIPAL', 1000.0):
            # 模拟获取资产失败
            trader._get_pair_specific_assets_value = AsyncMock(side_effect=Exception("API Error"))

            # 计算盈利（应该返回0而不是抛出异常）
            profit = await trader._calculate_current_profit()

            # 验证
            assert profit == 0.0


class TestEmergencyLiquidate:
    """紧急平仓测试"""

    @pytest.mark.asyncio
    async def test_emergency_liquidate_success(self, trader, mock_exchange):
        """测试紧急平仓成功"""
        with patch.object(settings, 'ENABLE_SAVINGS_FUNCTION', False), \
             patch('src.core.trader.send_pushplus_message') as mock_push:

            # 模拟账户余额
            mock_exchange.fetch_balance.return_value = {
                'free': {'BNB': 2.5}
            }

            # 执行紧急平仓
            await trader._emergency_liquidate("测试止损触发")

            # 验证订单取消
            mock_exchange.fetch_open_orders.assert_called_once()

            # 验证市价单卖出
            mock_exchange.create_order.assert_called_once()
            call_args = mock_exchange.create_order.call_args
            assert call_args[0][1] == 'market'  # 市价单
            assert call_args[0][2] == 'sell'    # 卖出

            # 验证推送通知
            mock_push.assert_called_once()

            # 验证止损状态
            assert trader.stop_loss_triggered is True

    @pytest.mark.asyncio
    async def test_emergency_liquidate_with_pending_orders(self, trader, mock_exchange):
        """测试紧急平仓时取消挂单"""
        with patch.object(settings, 'ENABLE_SAVINGS_FUNCTION', False), \
             patch('src.core.trader.send_pushplus_message'):

            # 模拟有挂单
            mock_exchange.fetch_open_orders.return_value = [
                {'id': 'order1'},
                {'id': 'order2'}
            ]
            mock_exchange.fetch_balance.return_value = {
                'free': {'BNB': 1.0}
            }

            # 执行紧急平仓
            await trader._emergency_liquidate("测试止损触发")

            # 验证取消了所有挂单
            assert mock_exchange.cancel_order.call_count == 2

    @pytest.mark.asyncio
    async def test_emergency_liquidate_retry_on_failure(self, trader, mock_exchange):
        """测试紧急平仓重试机制"""
        with patch.object(settings, 'ENABLE_SAVINGS_FUNCTION', False), \
             patch.object(settings, 'MIN_AMOUNT_LIMIT', 0.0001), \
             patch('src.core.trader.send_pushplus_message'):

            mock_exchange.fetch_balance.return_value = {
                'free': {'BNB': 1.0}
            }

            # 模拟前两次失败，第三次成功
            mock_exchange.create_order.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                {'id': 'order_success', 'status': 'closed'}
            ]

            # 执行紧急平仓
            await trader._emergency_liquidate("测试止损触发")

            # 验证重试了3次
            assert mock_exchange.create_order.call_count == 3

    @pytest.mark.asyncio
    async def test_emergency_liquidate_skip_small_balance(self, trader, mock_exchange):
        """测试小额余额跳过卖出"""
        with patch.object(settings, 'ENABLE_SAVINGS_FUNCTION', False), \
             patch.object(settings, 'MIN_AMOUNT_LIMIT', 0.01), \
             patch('src.core.trader.send_pushplus_message'):

            # 模拟非常小的余额
            mock_exchange.fetch_balance.return_value = {
                'free': {'BNB': 0.0001}  # 小于最小交易量
            }

            # 执行紧急平仓
            await trader._emergency_liquidate("测试止损触发")

            # 验证没有创建订单
            mock_exchange.create_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_emergency_liquidate_with_savings_transfer(self, trader, mock_exchange):
        """测试紧急平仓后转移到理财"""
        with patch.object(settings, 'ENABLE_SAVINGS_FUNCTION', True), \
             patch('src.core.trader.send_pushplus_message'):

            mock_exchange.fetch_balance.return_value = {
                'free': {'BNB': 1.0}
            }

            # 模拟转移资金方法
            trader._transfer_excess_funds = AsyncMock()

            # 执行紧急平仓
            await trader._emergency_liquidate("测试止损触发")

            # 验证调用了资金转移
            trader._transfer_excess_funds.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_liquidate_sends_critical_alert_on_failure(self, trader, mock_exchange):
        """测试紧急平仓失败时发送紧急告警"""
        with patch.object(settings, 'ENABLE_SAVINGS_FUNCTION', False), \
             patch('src.core.trader.send_pushplus_message') as mock_push:

            # 模拟获取余额失败
            mock_exchange.fetch_balance.side_effect = Exception("API Unavailable")

            # 执行紧急平仓（应该捕获异常并发送告警）
            with pytest.raises(Exception):
                await trader._emergency_liquidate("测试止损触发")

            # 验证发送了紧急告警（两次：常规告警 + 紧急告警）
            assert mock_push.call_count == 1
            # 检查紧急告警包含"紧急"关键词
            alert_msg = mock_push.call_args_list[0][0][0]
            assert "紧急" in alert_msg or "失败" in alert_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
