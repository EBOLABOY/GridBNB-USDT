"""
全局资金分配器单元测试

测试覆盖:
1. 初始化和资金分配
2. 交易限额检查
3. 资金记录
4. 动态重新平衡
5. 边界情况
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from src.strategies.global_allocator import (
    GlobalFundAllocator,
    AllocationStrategy,
    TraderAllocation
)


@pytest.fixture
def basic_allocator():
    """基础分配器（平均分配）"""
    return GlobalFundAllocator(
        symbols=['BNB/USDT', 'ETH/USDT', 'BTC/USDT'],
        total_capital=1200.0,
        strategy='equal',
        max_global_usage=0.95
    )


@pytest.fixture
def weighted_allocator():
    """权重分配器"""
    return GlobalFundAllocator(
        symbols=['BNB/USDT', 'ETH/USDT'],
        total_capital=1000.0,
        strategy='weighted',
        weights={'BNB/USDT': 2.0, 'ETH/USDT': 1.0}
    )


@pytest.fixture
def mock_trader():
    """模拟交易器"""
    trader = Mock()
    trader.symbol = 'BNB/USDT'
    trader.quote_asset = 'USDT'
    trader.base_asset = 'BNB'

    # 模拟exchange
    trader.exchange = Mock()
    trader.exchange.fetch_balance = AsyncMock(return_value={
        'free': {'USDT': 100.0, 'BNB': 0.5}
    })
    trader.exchange.fetch_funding_balance = AsyncMock(return_value={
        'USDT': 50.0,
        'BNB': 0.0
    })

    # 模拟资产价值计算
    trader._get_pair_specific_assets_value = AsyncMock(return_value=500.0)

    return trader


class TestInitialization:
    """测试初始化"""

    def test_equal_allocation(self, basic_allocator):
        """测试平均分配"""
        assert len(basic_allocator.allocations) == 3

        # 每个交易对应该分配 1200 / 3 = 400 USDT
        for symbol, alloc in basic_allocator.allocations.items():
            assert alloc.allocated_capital == 400.0
            assert alloc.current_usage == 0.0
            assert alloc.usage_ratio == 0.0

    def test_weighted_allocation(self, weighted_allocator):
        """测试权重分配"""
        # 总权重 = 2.0 + 1.0 = 3.0
        # BNB: 1000 * (2.0/3.0) = 666.67
        # ETH: 1000 * (1.0/3.0) = 333.33

        bnb_alloc = weighted_allocator.allocations['BNB/USDT']
        eth_alloc = weighted_allocator.allocations['ETH/USDT']

        assert abs(bnb_alloc.allocated_capital - 666.67) < 0.01
        assert abs(eth_alloc.allocated_capital - 333.33) < 0.01

    def test_invalid_strategy(self):
        """测试无效策略"""
        with pytest.raises(ValueError):
            GlobalFundAllocator(
                symbols=['BNB/USDT'],
                total_capital=1000.0,
                strategy='invalid'
            )

    def test_weighted_without_weights(self):
        """测试权重分配但未提供权重"""
        with pytest.raises(ValueError, match="需要提供weights参数"):
            GlobalFundAllocator(
                symbols=['BNB/USDT'],
                total_capital=1000.0,
                strategy='weighted'
            )


class TestTradeChecking:
    """测试交易检查"""

    @pytest.mark.asyncio
    async def test_buy_within_limit(self, basic_allocator):
        """测试买入在限额内"""
        # BNB/USDT分配了400 USDT，买入100应该允许
        allowed, reason = await basic_allocator.check_trade_allowed(
            'BNB/USDT',
            100.0,
            'buy'
        )

        assert allowed is True
        assert reason == ""

    @pytest.mark.asyncio
    async def test_buy_exceeds_symbol_limit(self, basic_allocator):
        """测试买入超过交易对限额"""
        # BNB/USDT分配了400 USDT，买入500应该拒绝
        allowed, reason = await basic_allocator.check_trade_allowed(
            'BNB/USDT',
            500.0,
            'buy'
        )

        assert allowed is False
        assert "交易对限额不足" in reason

    @pytest.mark.asyncio
    async def test_buy_exceeds_global_limit(self, basic_allocator, mock_trader):
        """测试买入超过全局限额"""
        # 注册mock trader
        basic_allocator.register_trader('BNB/USDT', mock_trader)

        # 模拟已经使用了900 USDT（75%）
        # 全局限额95% = 1140 USDT
        # 再买入300应该超限
        mock_trader._get_pair_specific_assets_value = AsyncMock(return_value=900.0)

        allowed, reason = await basic_allocator.check_trade_allowed(
            'BNB/USDT',
            300.0,
            'buy'
        )

        # 900 + 300 = 1200 (100%) > 1140 (95%)
        assert allowed is False
        assert "全局资金限额不足" in reason

    @pytest.mark.asyncio
    async def test_sell_always_allowed(self, basic_allocator):
        """测试卖出总是允许（不占用资金）"""
        allowed, reason = await basic_allocator.check_trade_allowed(
            'BNB/USDT',
            1000.0,  # 即使超限
            'sell'
        )

        assert allowed is True

    @pytest.mark.asyncio
    async def test_unknown_symbol(self, basic_allocator):
        """测试未知交易对"""
        allowed, reason = await basic_allocator.check_trade_allowed(
            'DOGE/USDT',  # 未配置的交易对
            100.0,
            'buy'
        )

        assert allowed is False
        assert "未知交易对" in reason


class TestTradeRecording:
    """测试交易记录"""

    @pytest.mark.asyncio
    async def test_record_buy(self, basic_allocator):
        """测试记录买入"""
        await basic_allocator.record_trade('BNB/USDT', 100.0, 'buy')

        alloc = basic_allocator.allocations['BNB/USDT']
        assert alloc.current_usage == 100.0
        assert alloc.usage_ratio == 100.0 / 400.0  # 25%

    @pytest.mark.asyncio
    async def test_record_sell(self, basic_allocator):
        """测试记录卖出"""
        # 先买入
        await basic_allocator.record_trade('BNB/USDT', 200.0, 'buy')

        # 再卖出
        await basic_allocator.record_trade('BNB/USDT', 80.0, 'sell')

        alloc = basic_allocator.allocations['BNB/USDT']
        assert alloc.current_usage == 120.0  # 200 - 80
        assert alloc.usage_ratio == 120.0 / 400.0  # 30%

    @pytest.mark.asyncio
    async def test_record_sell_below_zero(self, basic_allocator):
        """测试卖出不会低于0"""
        # 没有买入，直接卖出
        await basic_allocator.record_trade('BNB/USDT', 100.0, 'sell')

        alloc = basic_allocator.allocations['BNB/USDT']
        assert alloc.current_usage == 0.0  # 不会变成负数

    @pytest.mark.asyncio
    async def test_multiple_trades(self, basic_allocator):
        """测试多次交易"""
        # 买入 100
        await basic_allocator.record_trade('BNB/USDT', 100.0, 'buy')

        # 买入 150
        await basic_allocator.record_trade('BNB/USDT', 150.0, 'buy')

        # 卖出 50
        await basic_allocator.record_trade('BNB/USDT', 50.0, 'sell')

        alloc = basic_allocator.allocations['BNB/USDT']
        assert alloc.current_usage == 200.0  # 100 + 150 - 50
        assert alloc.usage_ratio == 0.5  # 50%


class TestGlobalUsage:
    """测试全局使用量计算"""

    @pytest.mark.asyncio
    async def test_global_usage_calculation(self, basic_allocator):
        """测试全局使用量计算"""
        # 创建3个mock traders
        traders = []
        for symbol in ['BNB/USDT', 'ETH/USDT', 'BTC/USDT']:
            trader = Mock()
            trader.symbol = symbol
            trader.quote_asset = 'USDT'

            trader.exchange = Mock()
            trader.exchange.fetch_balance = AsyncMock(return_value={
                'free': {'USDT': 50.0}
            })
            trader.exchange.fetch_funding_balance = AsyncMock(return_value={
                'USDT': 0.0
            })

            # 每个持仓200 USDT价值
            trader._get_pair_specific_assets_value = AsyncMock(return_value=250.0)

            basic_allocator.register_trader(symbol, trader)
            traders.append(trader)

        # 计算全局使用
        # 每个: 250(总资产) - 50(闲置USDT) = 200
        # 总共: 200 * 3 = 600
        global_usage = await basic_allocator._get_global_usage()
        assert global_usage == 600.0


class TestRebalancing:
    """测试动态重新平衡"""

    @pytest.mark.asyncio
    async def test_rebalance_not_for_equal_strategy(self, basic_allocator):
        """测试平均策略不触发重新平衡"""
        await basic_allocator.rebalance_if_needed()

        # 分配应该保持不变
        for alloc in basic_allocator.allocations.values():
            assert alloc.allocated_capital == 400.0

    @pytest.mark.asyncio
    async def test_rebalance_before_interval(self):
        """测试间隔时间未到不重新平衡"""
        allocator = GlobalFundAllocator(
            symbols=['BNB/USDT', 'ETH/USDT'],
            total_capital=1000.0,
            strategy='dynamic'
        )

        initial_bnb = allocator.allocations['BNB/USDT'].allocated_capital

        # 立即尝试重新平衡（间隔未到）
        await allocator.rebalance_if_needed()

        # 应该保持不变
        assert allocator.allocations['BNB/USDT'].allocated_capital == initial_bnb

    @pytest.mark.asyncio
    async def test_rebalance_dynamic_strategy(self):
        """测试动态策略重新平衡"""
        allocator = GlobalFundAllocator(
            symbols=['BNB/USDT', 'ETH/USDT'],
            total_capital=1000.0,
            strategy='dynamic'
        )

        # 模拟时间过去
        allocator.last_rebalance_time = 0

        # 设置不同的表现评分
        allocator.allocations['BNB/USDT'].performance_score = 2.0  # 表现好
        allocator.allocations['ETH/USDT'].performance_score = 0.5  # 表现差

        # 创建mock traders（避免实际计算）
        for symbol in ['BNB/USDT', 'ETH/USDT']:
            trader = Mock()
            trader.order_tracker = Mock()
            trader.order_tracker.get_trade_history = Mock(return_value=[])
            allocator.register_trader(symbol, trader)

        # 重新平衡
        await allocator.rebalance_if_needed()

        # BNB应该分配更多 (2.0 / 2.5 = 80%)
        # ETH应该分配更少 (0.5 / 2.5 = 20%)
        bnb_alloc = allocator.allocations['BNB/USDT'].allocated_capital
        eth_alloc = allocator.allocations['ETH/USDT'].allocated_capital

        assert abs(bnb_alloc - 800.0) < 1.0  # 约800
        assert abs(eth_alloc - 200.0) < 1.0  # 约200


class TestStatusReporting:
    """测试状态报告"""

    def test_allocation_status(self, basic_allocator):
        """测试分配状态报告"""
        status = basic_allocator.get_allocation_status()

        assert status['total_capital'] == 1200.0
        assert status['max_global_usage'] == 0.95
        assert status['strategy'] == 'equal'
        assert len(status['allocations']) == 3

        # 检查每个交易对状态
        for symbol in ['BNB/USDT', 'ETH/USDT', 'BTC/USDT']:
            alloc_status = status['allocations'][symbol]
            assert alloc_status['allocated'] == 400.0
            assert alloc_status['used'] == 0.0
            assert alloc_status['available'] == 400.0

    @pytest.mark.asyncio
    async def test_global_status_summary(self, basic_allocator):
        """测试全局状态摘要"""
        summary = await basic_allocator.get_global_status_summary()

        assert "全局资金分配状态" in summary
        assert "总资本: 1200.00 USDT" in summary
        assert "BNB/USDT" in summary
        assert "ETH/USDT" in summary
        assert "BTC/USDT" in summary


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_capital(self):
        """测试零本金"""
        with pytest.raises(ZeroDivisionError):
            GlobalFundAllocator(
                symbols=['BNB/USDT'],
                total_capital=0.0,
                strategy='equal'
            )

    def test_single_symbol(self):
        """测试单个交易对"""
        allocator = GlobalFundAllocator(
            symbols=['BNB/USDT'],
            total_capital=1000.0,
            strategy='equal'
        )

        # 应该分配全部资金
        assert allocator.allocations['BNB/USDT'].allocated_capital == 1000.0

    def test_many_symbols(self):
        """测试大量交易对"""
        symbols = [f'COIN{i}/USDT' for i in range(100)]

        allocator = GlobalFundAllocator(
            symbols=symbols,
            total_capital=10000.0,
            strategy='equal'
        )

        # 每个应该分配100 USDT
        for symbol in symbols:
            assert allocator.allocations[symbol].allocated_capital == 100.0

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, basic_allocator):
        """测试并发检查"""
        # 同时检查多个交易
        tasks = [
            basic_allocator.check_trade_allowed('BNB/USDT', 100.0, 'buy'),
            basic_allocator.check_trade_allowed('ETH/USDT', 150.0, 'buy'),
            basic_allocator.check_trade_allowed('BTC/USDT', 200.0, 'buy')
        ]

        results = await asyncio.gather(*tasks)

        # 所有应该都允许（未超限）
        assert all(allowed for allowed, _ in results)


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
