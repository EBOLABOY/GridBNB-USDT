"""
GridTrader核心功能单元测试
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import time
import json
import os
import tempfile

# 导入被测试的模块
from src.core.trader import GridTrader
from src.config.settings import TradingConfig, settings


@pytest.fixture
def mock_exchange():
    """创建模拟的交易所客户端"""
    exchange = MagicMock()
    exchange.exchange = MagicMock()
    exchange.exchange.market.return_value = {
        'precision': {'amount': 3, 'price': 2},
        'base': 'BNB',
        'quote': 'USDT'
    }
    exchange.exchange.amount_to_precision = MagicMock(side_effect=lambda symbol, amount: round(amount, 3))
    exchange.exchange.price_to_precision = MagicMock(side_effect=lambda symbol, price: round(price, 2))
    return exchange


@pytest.fixture
def mock_config():
    """创建模拟的配置"""
    config = TradingConfig()
    return config


@pytest.fixture
def mock_trader(mock_exchange, mock_config):
    """创建模拟的GridTrader实例"""
    with patch('src.core.trader.AdvancedRiskManager'), \
         patch('src.core.trader.OrderTracker'), \
         patch('src.core.trader.TradingMonitor'):
        # S1策略已移除,不再需要mock
        trader = GridTrader(mock_exchange, mock_config, 'BNB/USDT')
        trader.base_price = 600.0
        trader.grid_size = 2.0
        trader.amount_precision = 3
        trader.price_precision = 2
        return trader


class TestGridCalculations:
    """测试网格计算相关功能"""
    
    def test_get_upper_band(self, mock_trader):
        """测试上轨计算"""
        mock_trader.base_price = 600.0
        mock_trader.grid_size = 2.0  # 2%
        
        expected = 600.0 * (1 + 0.02)  # 612.0
        assert mock_trader._get_upper_band() == expected
        
    def test_get_lower_band(self, mock_trader):
        """测试下轨计算"""
        mock_trader.base_price = 600.0
        mock_trader.grid_size = 2.0  # 2%
        
        expected = 600.0 * (1 - 0.02)  # 588.0
        assert mock_trader._get_lower_band() == expected
        
    def test_grid_bands_with_different_sizes(self, mock_trader):
        """测试不同网格大小的上下轨计算"""
        mock_trader.base_price = 500.0
        
        # 测试5%网格
        mock_trader.grid_size = 5.0
        assert mock_trader._get_upper_band() == 525.0
        assert mock_trader._get_lower_band() == 475.0
        
        # 测试1%网格
        mock_trader.grid_size = 1.0
        assert mock_trader._get_upper_band() == 505.0
        assert mock_trader._get_lower_band() == 495.0


class TestPrecisionHandling:
    """测试精度处理功能"""
    
    def test_adjust_amount_precision(self, mock_trader):
        """测试数量精度调整"""
        # 测试正常情况
        amount = 1.23456789
        result = mock_trader._adjust_amount_precision(amount)
        assert result == 1.235  # 3位小数精度
        
    def test_adjust_price_precision(self, mock_trader):
        """测试价格精度调整"""
        # 测试正常情况
        price = 123.456789
        result = mock_trader._adjust_price_precision(price)
        assert result == 123.46  # 2位小数精度
        
    def test_precision_with_none_values(self, mock_trader):
        """测试精度为None时的处理"""
        mock_trader.amount_precision = None
        mock_trader.price_precision = None
        
        # 应该使用默认精度
        amount_result = mock_trader._adjust_amount_precision(1.23456)
        price_result = mock_trader._adjust_price_precision(123.456)
        
        assert amount_result == 1.235  # 默认3位小数
        assert price_result == 123.46  # 默认2位小数


class TestStateManagement:
    """测试状态管理功能"""
    
    def test_save_and_load_state(self, mock_trader):
        """测试状态保存和加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 设置临时状态文件路径
            state_file = os.path.join(temp_dir, 'test_state.json')
            mock_trader.state_file_path = state_file
            
            # 设置一些状态
            mock_trader.base_price = 650.0
            mock_trader.grid_size = 3.5
            mock_trader.highest = 680.0
            mock_trader.lowest = 620.0
            mock_trader.last_grid_adjust_time = time.time()
            
            # 保存状态
            mock_trader._save_state()
            
            # 验证文件存在
            assert os.path.exists(state_file)
            
            # 重置状态
            mock_trader.base_price = 0
            mock_trader.grid_size = 0
            mock_trader.highest = None
            mock_trader.lowest = None
            
            # 加载状态
            mock_trader._load_state()
            
            # 验证状态恢复
            assert mock_trader.base_price == 650.0
            assert mock_trader.grid_size == 3.5
            assert mock_trader.highest == 680.0
            assert mock_trader.lowest == 620.0
            
    def test_load_state_file_not_exists(self, mock_trader):
        """测试状态文件不存在时的处理"""
        mock_trader.state_file_path = '/nonexistent/path/state.json'
        
        # 应该不抛出异常
        mock_trader._load_state()
        
    def test_save_state_invalid_path(self, mock_trader):
        """测试无效路径时的状态保存"""
        mock_trader.state_file_path = '/invalid/path/state.json'
        
        # 应该不抛出异常，但会记录错误日志
        mock_trader._save_state()


class TestConfigValidation:
    """测试配置验证功能"""
    
    def test_trading_config_validation(self):
        """测试TradingConfig的验证逻辑"""
        # 正常情况应该不抛出异常
        config = TradingConfig()
        assert settings.MIN_POSITION_RATIO < settings.MAX_POSITION_RATIO
        assert config.GRID_PARAMS['min'] <= config.GRID_PARAMS['max']


if __name__ == '__main__':
    pytest.main([__file__])
