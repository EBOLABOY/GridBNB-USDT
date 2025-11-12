"""
配置管理相关测试
"""
import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from src.config.settings import Settings, TradingConfig, FLIP_THRESHOLD, settings


class TestSettings:
    """测试Settings类"""
    
    def test_settings_with_env_vars(self):
        """测试从环境变量读取设置"""
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': 'test_' + 'x' * 60,
            'BINANCE_API_SECRET': 'test_' + 'y' * 60,
            'PUSHPLUS_TOKEN': 'test_token',
            'SYMBOLS': 'ETH/USDT',
            'INITIAL_PRINCIPAL': '2000.0'
        }):
            settings = Settings()
            assert settings.BINANCE_API_KEY == 'test_' + 'x' * 60
            assert settings.BINANCE_API_SECRET == 'test_' + 'y' * 60
            assert settings.PUSHPLUS_TOKEN == 'test_token'
            assert settings.SYMBOLS == 'ETH/USDT'
            assert settings.INITIAL_PRINCIPAL == 2000.0
    
    def test_settings_defaults(self):
        """测试默认值"""
        # 使用64位测试密钥以满足验证器要求
        test_api_key = 'test_' + 'x' * 60
        test_api_secret = 'test_' + 'y' * 60
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': test_api_key,
            'BINANCE_API_SECRET': test_api_secret
        }, clear=True):
            settings = Settings()
            assert settings.SYMBOLS == 'BNB/USDT'
            assert settings.INITIAL_GRID == 2.0
            assert settings.MIN_TRADE_AMOUNT == 20.0

    def test_settings_required_fields_present(self):
        """测试必需字段存在时的处理"""
        # 使用64位测试密钥以满足验证器要求
        test_api_key = 'test_' + 'x' * 60
        test_api_secret = 'test_' + 'y' * 60
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': test_api_key,
            'BINANCE_API_SECRET': test_api_secret
        }):
            # 有必需字段时应该正常创建
            settings = Settings()
            assert settings.BINANCE_API_KEY == test_api_key
            assert settings.BINANCE_API_SECRET == test_api_secret


class TestTradingConfig:
    """测试TradingConfig类"""
    
    def test_config_initialization(self):
        """测试配置初始化"""
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': 'test_' + 'x' * 60,
            'BINANCE_API_SECRET': 'test_' + 'y' * 60
        }):
            config = TradingConfig()
            # 现在这些配置直接从 settings 获取
            assert settings.SYMBOLS == 'BNB/USDT'
            assert settings.INITIAL_GRID == 2.0
            assert 'position_limit' in config.RISK_PARAMS
    
    def test_config_validation_position_ratios(self):
        """测试仓位比例验证"""
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': 'test_' + 'x' * 60,
            'BINANCE_API_SECRET': 'test_' + 'y' * 60
        }):
            # 正常情况
            config = TradingConfig()
            assert settings.MIN_POSITION_RATIO < settings.MAX_POSITION_RATIO
    
    def test_config_validation_grid_params(self):
        """测试网格参数验证"""
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': 'test_' + 'x' * 60,
            'BINANCE_API_SECRET': 'test_' + 'y' * 60
        }):
            config = TradingConfig()
            assert config.GRID_PARAMS['min'] <= config.GRID_PARAMS['max']
    
    def test_grid_volatility_ranges(self):
        """测试网格波动率范围配置"""
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': 'test_' + 'x' * 60,
            'BINANCE_API_SECRET': 'test_' + 'y' * 60
        }):
            config = TradingConfig()
            ranges = config.GRID_PARAMS['volatility_threshold']['ranges']
            
            # 验证范围配置的完整性
            assert len(ranges) > 0
            for range_config in ranges:
                assert 'range' in range_config
                assert 'grid' in range_config
                assert len(range_config['range']) == 2
                assert range_config['grid'] > 0


class TestUtilityFunctions:
    """测试工具函数"""
    
    def test_flip_threshold_calculation(self):
        """测试翻转阈值计算"""
        # 测试不同网格大小的阈值计算
        assert FLIP_THRESHOLD(2.0) == (2.0 / 5) / 100  # 0.004
        assert FLIP_THRESHOLD(5.0) == (5.0 / 5) / 100  # 0.01
        assert FLIP_THRESHOLD(1.0) == (1.0 / 5) / 100  # 0.002
    
    def test_flip_threshold_edge_cases(self):
        """测试翻转阈值的边界情况"""
        # 测试零值
        assert FLIP_THRESHOLD(0) == 0
        
        # 测试负值（虽然实际不应该出现）
        assert FLIP_THRESHOLD(-1.0) == -0.002


if __name__ == '__main__':
    pytest.main([__file__])
