"""
精细化风控机制测试
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.strategies.risk_manager import AdvancedRiskManager, RiskState
from src.config.settings import TradingConfig


@pytest.fixture
def mock_trader():
    """创建模拟的交易器实例"""
    trader = MagicMock()
    trader.config = TradingConfig()
    trader.logger = MagicMock()
    return trader


@pytest.fixture
def risk_manager(mock_trader):
    """创建风控管理器实例"""
    rm = AdvancedRiskManager(mock_trader)
    rm.logger = MagicMock()  # 模拟logger
    return rm


class TestRiskState:
    """测试风险状态枚举"""
    
    def test_risk_state_values(self):
        """测试风险状态枚举值"""
        assert RiskState.ALLOW_ALL.value == 0
        assert RiskState.ALLOW_SELL_ONLY.value == 1
        assert RiskState.ALLOW_BUY_ONLY.value == 2
    
    def test_risk_state_names(self):
        """测试风险状态名称"""
        assert RiskState.ALLOW_ALL.name == "ALLOW_ALL"
        assert RiskState.ALLOW_SELL_ONLY.name == "ALLOW_SELL_ONLY"
        assert RiskState.ALLOW_BUY_ONLY.name == "ALLOW_BUY_ONLY"


class TestAdvancedRiskManager:
    """测试高级风控管理器"""
    
    @pytest.mark.asyncio
    async def test_check_position_limits_normal_range(self, risk_manager):
        """测试正常仓位范围的风控检查"""
        # 模拟正常仓位比例 (50%)
        risk_manager._get_position_ratio = AsyncMock(return_value=0.5)
        
        # 模拟账户快照
        mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
        mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        assert result == RiskState.ALLOW_ALL
    
    @pytest.mark.asyncio
    async def test_check_position_limits_high_position(self, risk_manager):
        """测试高仓位的风控检查"""
        # 模拟高仓位比例 (95%)
        risk_manager._get_position_ratio = AsyncMock(return_value=0.95)

        # 模拟账户快照
        mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
        mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        assert result == RiskState.ALLOW_SELL_ONLY
    
    @pytest.mark.asyncio
    async def test_check_position_limits_low_position(self, risk_manager):
        """测试低仓位的风控检查"""
        # 模拟低仓位比例 (5%)
        risk_manager._get_position_ratio = AsyncMock(return_value=0.05)

        # 模拟账户快照
        mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
        mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        assert result == RiskState.ALLOW_BUY_ONLY
    
    @pytest.mark.asyncio
    async def test_check_position_limits_boundary_values(self, risk_manager):
        """测试边界值的风控检查"""
        # 模拟账户快照
        mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
        mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

        # 测试刚好等于最大仓位比例
        risk_manager._get_position_ratio = AsyncMock(return_value=0.9)
        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        assert result == RiskState.ALLOW_ALL

        # 测试刚好超过最大仓位比例
        risk_manager._get_position_ratio = AsyncMock(return_value=0.901)
        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        assert result == RiskState.ALLOW_SELL_ONLY

        # 测试刚好等于最小仓位比例
        risk_manager._get_position_ratio = AsyncMock(return_value=0.1)
        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        assert result == RiskState.ALLOW_ALL

        # 测试刚好低于最小仓位比例
        risk_manager._get_position_ratio = AsyncMock(return_value=0.099)
        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        assert result == RiskState.ALLOW_BUY_ONLY
    
    @pytest.mark.asyncio
    async def test_check_position_limits_exception_handling(self, risk_manager):
        """测试异常处理"""
        # 模拟获取仓位比例时抛出异常
        risk_manager._get_position_ratio = AsyncMock(side_effect=Exception("Test error"))

        # 模拟账户快照
        mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
        mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

        result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        # 异常时应该返回ALLOW_ALL以避免卡死
        assert result == RiskState.ALLOW_ALL
    
    @pytest.mark.asyncio
    async def test_multi_layer_check_backward_compatibility(self, risk_manager):
        """测试向后兼容的multi_layer_check方法"""
        # 模拟exchange的异步方法
        risk_manager.trader.exchange.fetch_balance = AsyncMock(return_value={'free': {'BNB': 1.0, 'USDT': 1000.0}})
        risk_manager.trader.exchange.fetch_funding_balance = AsyncMock(return_value={'BNB': 0.0, 'USDT': 0.0})

        # 测试正常范围
        risk_manager._get_position_ratio = AsyncMock(return_value=0.5)
        result = await risk_manager.multi_layer_check()
        assert result == False  # ALLOW_ALL -> False

        # 测试高仓位
        risk_manager._get_position_ratio = AsyncMock(return_value=0.95)
        result = await risk_manager.multi_layer_check()
        assert result == True  # ALLOW_SELL_ONLY -> True

        # 测试低仓位
        risk_manager._get_position_ratio = AsyncMock(return_value=0.05)
        result = await risk_manager.multi_layer_check()
        assert result == True  # ALLOW_BUY_ONLY -> True
    
    @pytest.mark.asyncio
    async def test_position_ratio_logging(self, risk_manager):
        """测试仓位比例变化时的日志记录"""
        # 模拟账户快照
        mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
        mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

        # 首次调用
        risk_manager._get_position_ratio = AsyncMock(return_value=0.5)
        await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)

        # 仓位比例变化不大，不应该记录日志
        risk_manager._get_position_ratio = AsyncMock(return_value=0.5005)
        await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)

        # 仓位比例变化较大，应该记录日志
        risk_manager._get_position_ratio = AsyncMock(return_value=0.52)
        await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
        
        # 验证日志调用（使用risk_manager自己的logger）
        assert risk_manager.logger.info.called


class TestRiskStateIntegration:
    """测试风控状态的集成场景"""
    
    @pytest.mark.asyncio
    async def test_risk_state_priority(self, risk_manager):
        """测试风控状态的优先级"""
        # 当仓位既超过上限又低于下限时（理论上不可能，但测试边界情况）
        # 应该优先检查上限
        with patch.object(risk_manager, '_get_position_ratio') as mock_ratio:
            # 模拟一个不可能的情况用于测试优先级
            mock_ratio.return_value = 1.5  # 150%仓位（不可能但用于测试）

            # 模拟账户快照
            mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
            mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

            result = await risk_manager.check_position_limits(mock_spot_balance, mock_funding_balance)
            # 应该返回ALLOW_SELL_ONLY，因为优先检查上限
            assert result == RiskState.ALLOW_SELL_ONLY
    
    def test_risk_state_string_representation(self):
        """测试风控状态的字符串表示"""
        assert str(RiskState.ALLOW_ALL) == "RiskState.ALLOW_ALL"
        assert str(RiskState.ALLOW_SELL_ONLY) == "RiskState.ALLOW_SELL_ONLY"
        assert str(RiskState.ALLOW_BUY_ONLY) == "RiskState.ALLOW_BUY_ONLY"


class TestSymbolSpecificPositionLimits:
    """测试交易对特定仓位限制功能 (Issue #51)"""

    @pytest.fixture
    def mock_trader_with_symbol(self):
        """创建带有交易对信息的模拟交易器"""
        trader = MagicMock()
        trader.config = TradingConfig()
        trader.logger = MagicMock()
        trader.symbol = "BNB/USDT"
        return trader

    @pytest.fixture
    def risk_manager_with_symbol(self, mock_trader_with_symbol):
        """创建带有交易对信息的风控管理器"""
        rm = AdvancedRiskManager(mock_trader_with_symbol)
        rm.logger = MagicMock()
        return rm

    @pytest.mark.asyncio
    async def test_symbol_specific_limits_bnb(self, risk_manager_with_symbol):
        """测试BNB使用交易对特定限制（20%-80%）"""
        # 模拟配置：BNB有特定限制 20%-80%
        with patch('src.strategies.risk_manager.settings') as mock_settings:
            mock_settings.POSITION_LIMITS_JSON = {
                "BNB/USDT": {"min": 0.20, "max": 0.80}
            }
            mock_settings.MAX_POSITION_RATIO = 0.9  # 全局限制
            mock_settings.MIN_POSITION_RATIO = 0.1  # 全局限制

            # 模拟账户快照
            mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
            mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

            # 测试1: 仓位比例50%，在BNB的20%-80%范围内 -> ALLOW_ALL
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.50)
            result = await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_ALL

            # 测试2: 仓位比例85%，超过BNB的80%上限 -> ALLOW_SELL_ONLY
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.85)
            result = await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_SELL_ONLY

            # 测试3: 仓位比例15%，低于BNB的20%下限 -> ALLOW_BUY_ONLY
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.15)
            result = await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_BUY_ONLY

    @pytest.mark.asyncio
    async def test_fallback_to_global_limits(self):
        """测试未配置特定限制的交易对回退到全局限制"""
        # 创建ETH交易器（没有特定限制）
        trader = MagicMock()
        trader.config = TradingConfig()
        trader.logger = MagicMock()
        trader.symbol = "ETH/USDT"  # 没有配置特定限制

        risk_manager = AdvancedRiskManager(trader)
        risk_manager.logger = MagicMock()

        # 模拟配置：只配置了BNB，ETH没有配置
        with patch('src.strategies.risk_manager.settings') as mock_settings:
            mock_settings.POSITION_LIMITS_JSON = {
                "BNB/USDT": {"min": 0.20, "max": 0.80}
            }
            mock_settings.MAX_POSITION_RATIO = 0.9  # 全局限制
            mock_settings.MIN_POSITION_RATIO = 0.1  # 全局限制

            # 模拟账户快照
            mock_spot_balance = {'free': {'ETH': 1.0, 'USDT': 1000.0}}
            mock_funding_balance = {'ETH': 0.0, 'USDT': 0.0}

            # 测试1: 仓位比例85%，低于全局90%上限 -> ALLOW_ALL
            risk_manager._get_position_ratio = AsyncMock(return_value=0.85)
            result = await risk_manager.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_ALL

            # 测试2: 仓位比例95%，超过全局90%上限 -> ALLOW_SELL_ONLY
            risk_manager._get_position_ratio = AsyncMock(return_value=0.95)
            result = await risk_manager.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_SELL_ONLY

            # 测试3: 仓位比例5%，低于全局10%下限 -> ALLOW_BUY_ONLY
            risk_manager._get_position_ratio = AsyncMock(return_value=0.05)
            result = await risk_manager.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_BUY_ONLY

    @pytest.mark.asyncio
    async def test_symbol_specific_boundary_values(self, risk_manager_with_symbol):
        """测试交易对特定限制的边界值"""
        # 模拟配置：BNB有特定限制 20%-80%
        with patch('src.strategies.risk_manager.settings') as mock_settings:
            mock_settings.POSITION_LIMITS_JSON = {
                "BNB/USDT": {"min": 0.20, "max": 0.80}
            }
            mock_settings.MAX_POSITION_RATIO = 0.9
            mock_settings.MIN_POSITION_RATIO = 0.1

            # 模拟账户快照
            mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
            mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

            # 测试刚好等于最大限制 80%
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.80)
            result = await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_ALL

            # 测试刚好超过最大限制 80.1%
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.801)
            result = await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_SELL_ONLY

            # 测试刚好等于最小限制 20%
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.20)
            result = await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_ALL

            # 测试刚好低于最小限制 19.9%
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.199)
            result = await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_BUY_ONLY

    @pytest.mark.asyncio
    async def test_symbol_specific_logging(self, risk_manager_with_symbol):
        """测试交易对特定限制的日志标注"""
        # 模拟配置：BNB有特定限制
        with patch('src.strategies.risk_manager.settings') as mock_settings:
            mock_settings.POSITION_LIMITS_JSON = {
                "BNB/USDT": {"min": 0.20, "max": 0.80}
            }
            mock_settings.MAX_POSITION_RATIO = 0.9
            mock_settings.MIN_POSITION_RATIO = 0.1

            # 模拟账户快照
            mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
            mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

            # 触发高仓位警告
            risk_manager_with_symbol._get_position_ratio = AsyncMock(return_value=0.85)
            await risk_manager_with_symbol.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )

            # 验证日志包含 [BNB/USDT特定] 标记
            risk_manager_with_symbol.logger.warning.assert_called()
            warning_call_args = risk_manager_with_symbol.logger.warning.call_args[0][0]
            assert "[BNB/USDT特定]" in warning_call_args

    @pytest.mark.asyncio
    async def test_empty_position_limits_config(self):
        """测试空配置时使用全局限制"""
        trader = MagicMock()
        trader.config = TradingConfig()
        trader.logger = MagicMock()
        trader.symbol = "BNB/USDT"

        risk_manager = AdvancedRiskManager(trader)
        risk_manager.logger = MagicMock()

        # 模拟配置：POSITION_LIMITS_JSON为空
        with patch('src.strategies.risk_manager.settings') as mock_settings:
            mock_settings.POSITION_LIMITS_JSON = {}  # 空配置
            mock_settings.MAX_POSITION_RATIO = 0.9
            mock_settings.MIN_POSITION_RATIO = 0.1

            # 模拟账户快照
            mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
            mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

            # 测试使用全局限制
            risk_manager._get_position_ratio = AsyncMock(return_value=0.95)
            result = await risk_manager.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_SELL_ONLY  # 超过全局90%

    @pytest.mark.asyncio
    async def test_multiple_symbols_different_limits(self):
        """测试多个交易对使用不同的限制"""
        # 模拟配置：BNB 20%-80%，ETH 5%-95%
        with patch('src.strategies.risk_manager.settings') as mock_settings:
            mock_settings.POSITION_LIMITS_JSON = {
                "BNB/USDT": {"min": 0.20, "max": 0.80},
                "ETH/USDT": {"min": 0.05, "max": 0.95}
            }
            mock_settings.MAX_POSITION_RATIO = 0.9
            mock_settings.MIN_POSITION_RATIO = 0.1

            # 测试BNB
            trader_bnb = MagicMock()
            trader_bnb.symbol = "BNB/USDT"
            trader_bnb.config = TradingConfig()
            trader_bnb.logger = MagicMock()
            rm_bnb = AdvancedRiskManager(trader_bnb)
            rm_bnb.logger = MagicMock()

            mock_spot_balance = {'free': {'BNB': 1.0, 'USDT': 1000.0}}
            mock_funding_balance = {'BNB': 0.0, 'USDT': 0.0}

            # BNB 85%仓位 -> 超过80%上限 -> ALLOW_SELL_ONLY
            rm_bnb._get_position_ratio = AsyncMock(return_value=0.85)
            result = await rm_bnb.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_SELL_ONLY

            # 测试ETH
            trader_eth = MagicMock()
            trader_eth.symbol = "ETH/USDT"
            trader_eth.config = TradingConfig()
            trader_eth.logger = MagicMock()
            rm_eth = AdvancedRiskManager(trader_eth)
            rm_eth.logger = MagicMock()

            # ETH 85%仓位 -> 低于95%上限 -> ALLOW_ALL
            rm_eth._get_position_ratio = AsyncMock(return_value=0.85)
            result = await rm_eth.check_position_limits(
                mock_spot_balance, mock_funding_balance
            )
            assert result == RiskState.ALLOW_ALL


if __name__ == '__main__':
    pytest.main([__file__])
