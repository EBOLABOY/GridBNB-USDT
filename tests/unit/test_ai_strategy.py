"""
AI辅助交易策略单元测试

测试覆盖:
1. 技术指标计算
2. 市场情绪数据获取
3. AI提示词构建
4. AI响应解析
5. 建议验证
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.strategies.technical_indicators import TechnicalIndicators
from src.strategies.market_sentiment import MarketSentimentData
from src.strategies.ai_prompt import AIPromptBuilder


class TestTechnicalIndicators:
    """技术指标计算测试"""

    def setup_method(self):
        self.calculator = TechnicalIndicators()
        # 创建测试价格数据 (100个数据点)
        self.prices = [100 + i * 0.5 for i in range(100)]
        self.volumes = [1000 + i * 10 for i in range(100)]

    def test_calculate_rsi(self):
        """测试RSI计算"""
        result = self.calculator.calculate_rsi(self.prices, period=14)

        assert 'value' in result
        assert 'trend' in result
        assert 'signal' in result
        assert 0 <= result['value'] <= 100
        assert result['trend'] in ['oversold', 'neutral', 'overbought']
        assert result['signal'] in ['strong_buy', 'buy', 'neutral', 'sell', 'strong_sell']

    def test_calculate_rsi_insufficient_data(self):
        """测试RSI计算 - 数据不足"""
        short_prices = [100, 101, 102]
        result = self.calculator.calculate_rsi(short_prices, period=14)

        # 应该返回默认值
        assert result['value'] == 50.0
        assert result['trend'] == 'neutral'

    def test_calculate_macd(self):
        """测试MACD计算"""
        result = self.calculator.calculate_macd(self.prices)

        assert 'macd' in result
        assert 'signal' in result
        assert 'histogram' in result
        assert 'trend' in result
        assert 'crossover' in result
        assert result['trend'] in ['bullish', 'bearish', 'neutral']
        assert result['crossover'] in ['golden_cross', 'death_cross', 'none']

    def test_calculate_bollinger_bands(self):
        """测试布林带计算"""
        result = self.calculator.calculate_bollinger_bands(self.prices, period=20)

        assert 'upper' in result
        assert 'middle' in result
        assert 'lower' in result
        assert 'width' in result
        assert 'position' in result
        assert result['upper'] > result['middle'] > result['lower']
        assert result['position'] in ['above', 'upper', 'middle', 'lower', 'below']

    def test_calculate_ema(self):
        """测试EMA计算"""
        ema = self.calculator.calculate_ema(self.prices, period=20)

        assert isinstance(ema, float)
        assert ema > 0

    def test_calculate_volume_analysis(self):
        """测试成交量分析"""
        result = self.calculator.calculate_volume_analysis(
            self.volumes, self.prices, period=20
        )

        assert 'current_volume' in result
        assert 'avg_volume' in result
        assert 'volume_ratio' in result
        assert 'trend' in result
        assert result['trend'] in ['increasing', 'decreasing', 'normal']

    def test_calculate_all_indicators(self):
        """测试一次性计算所有指标"""
        result = self.calculator.calculate_all_indicators(self.prices, self.volumes)

        assert 'rsi' in result
        assert 'macd' in result
        assert 'bollinger_bands' in result
        assert 'ema_20' in result
        assert 'ema_50' in result
        assert 'volume_analysis' in result
        assert 'timestamp' in result

    def test_get_overall_signal(self):
        """测试综合信号判断"""
        indicators = self.calculator.calculate_all_indicators(self.prices, self.volumes)
        result = self.calculator.get_overall_signal(indicators)

        assert 'signal' in result
        assert 'score' in result
        assert 'bullish_count' in result
        assert 'bearish_count' in result
        assert result['signal'] in ['strong_buy', 'buy', 'neutral', 'sell', 'strong_sell']


class TestMarketSentiment:
    """市场情绪数据测试"""

    def setup_method(self):
        self.sentiment_data = MarketSentimentData()

    @pytest.mark.asyncio
    async def test_get_fear_greed_index_success(self):
        """测试Fear & Greed指数获取 - 成功"""
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'data': [
                {'value': '65', 'timestamp': '1234567890'},
                {'value': '60', 'timestamp': '1234567800'}
            ]
        })

        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            result = await self.sentiment_data.get_fear_greed_index()

            assert result is not None
            assert 'value' in result
            assert 'classification' in result
            assert 'trend' in result
            assert 0 <= result['value'] <= 100

    @pytest.mark.asyncio
    async def test_get_fear_greed_index_cache(self):
        """测试Fear & Greed指数 - 缓存机制"""
        # 设置缓存
        import datetime
        self.sentiment_data.fear_greed_cache = {
            'data': {'value': 50, 'classification': 'Neutral'},
            'timestamp': datetime.datetime.now(),
            'ttl': 3600
        }

        result = await self.sentiment_data.get_fear_greed_index()

        # 应该返回缓存数据
        assert result is not None
        assert result['value'] == 50

    @pytest.mark.asyncio
    async def test_get_comprehensive_sentiment(self):
        """测试综合市场情绪"""
        # Mock Fear & Greed数据
        self.sentiment_data.get_fear_greed_index = AsyncMock(return_value={
            'value': 70,
            'classification': 'Greed',
            'timestamp': '1234567890',
            'trend': 'increasing'
        })

        result = await self.sentiment_data.get_comprehensive_sentiment()

        assert 'fear_greed' in result
        assert 'overall_sentiment' in result
        assert 'confidence' in result
        assert result['overall_sentiment'] in ['bullish', 'bearish', 'neutral']


class TestAIPromptBuilder:
    """AI提示词构建器测试"""

    def setup_method(self):
        self.builder = AIPromptBuilder()
        self.test_data = {
            'symbol': 'BNB/USDT',
            'market_data': {
                'current_price': 600.0,
                '24h_change': 2.5,
                '24h_volume': 1000000,
                '24h_high': 610.0,
                '24h_low': 590.0
            },
            'technical_indicators': {
                'rsi': {'value': 65, 'trend': 'neutral', 'signal': 'neutral'},
                'macd': {
                    'macd': 1.5,
                    'signal': 1.2,
                    'histogram': 0.3,
                    'trend': 'bullish',
                    'crossover': 'none'
                },
                'bollinger_bands': {
                    'upper': 620,
                    'middle': 600,
                    'lower': 580,
                    'width': 40,
                    'position': 'middle'
                },
                'ema_20': 598,
                'ema_50': 595,
                'volume_analysis': {
                    'current_volume': 1100,
                    'avg_volume': 1000,
                    'volume_ratio': 1.1,
                    'trend': 'normal',
                    'signal': 'neutral'
                }
            },
            'third_party_signals': {
                'fear_greed': {
                    'value': 55,
                    'classification': 'Neutral',
                    'trend': 'stable'
                },
                'overall_sentiment': 'neutral'
            },
            'portfolio_status': {
                'total_value_usdt': 10000,
                'base_asset_value': 5000,
                'quote_asset_value': 5000,
                'position_ratio': 0.5,
                'unrealized_pnl': 100,
                'pnl_percentage': 1.0
            },
            'recent_trades': [],
            'grid_strategy_status': {
                'base_price': 600,
                'grid_size': 2.0,
                'upper_band': 612,
                'lower_band': 588,
                'current_volatility': 0.15,
                'next_buy_price': 588,
                'next_sell_price': 612
            },
            'risk_metrics': {
                'max_position_ratio': 0.9,
                'min_position_ratio': 0.1,
                'current_risk_state': 'ALLOW_ALL',
                'consecutive_losses': 0,
                'max_drawdown': 'N/A'
            }
        }

    def test_build_prompt(self):
        """测试提示词构建"""
        prompt = AIPromptBuilder.build_prompt(self.test_data)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert 'BNB/USDT' in prompt
        assert 'RSI' in prompt
        assert 'MACD' in prompt
        assert '布林带' in prompt
        assert 'JSON' in prompt

    def test_parse_ai_response_valid(self):
        """测试AI响应解析 - 有效JSON"""
        response_text = """
        Based on analysis, here is my recommendation:
        {
            "action": "buy",
            "confidence": 75,
            "suggested_amount_pct": 10,
            "reason": "技术指标显示上涨趋势",
            "risk_level": "medium",
            "time_horizon": "short",
            "stop_loss": 590,
            "take_profit": 620,
            "additional_notes": null
        }
        """

        result = AIPromptBuilder.parse_ai_response(response_text)

        assert result is not None
        assert result['action'] == 'buy'
        assert result['confidence'] == 75
        assert result['suggested_amount_pct'] == 10
        assert 'reason' in result

    def test_parse_ai_response_invalid(self):
        """测试AI响应解析 - 无效响应"""
        response_text = "This is not JSON"

        with pytest.raises(ValueError):
            AIPromptBuilder.parse_ai_response(response_text)

    def test_validate_suggestion_valid(self):
        """测试建议验证 - 有效建议"""
        suggestion = {
            'action': 'buy',
            'confidence': 75,
            'suggested_amount_pct': 15,
            'stop_loss': 590,
            'take_profit': 620
        }

        is_valid, error = AIPromptBuilder.validate_suggestion(
            suggestion, current_price=600, max_position=0.9
        )

        assert is_valid is True
        assert error is None

    def test_validate_suggestion_invalid_stop_loss(self):
        """测试建议验证 - 无效止损价"""
        suggestion = {
            'action': 'buy',
            'confidence': 75,
            'suggested_amount_pct': 15,
            'stop_loss': 610,  # 买入止损价应该低于当前价
            'take_profit': 620
        }

        is_valid, error = AIPromptBuilder.validate_suggestion(
            suggestion, current_price=600, max_position=0.9
        )

        assert is_valid is False
        assert error is not None

    def test_validate_suggestion_invalid_amount(self):
        """测试建议验证 - 无效金额比例"""
        suggestion = {
            'action': 'buy',
            'confidence': 75,
            'suggested_amount_pct': 35,  # 超过30%
            'stop_loss': 590,
            'take_profit': 620
        }

        is_valid, error = AIPromptBuilder.validate_suggestion(
            suggestion, current_price=600, max_position=0.9
        )

        assert is_valid is False
        assert '过高' in error

    def test_validate_suggestion_low_confidence(self):
        """测试建议验证 - 低置信度"""
        suggestion = {
            'action': 'buy',
            'confidence': 40,  # 低于50%
            'suggested_amount_pct': 10,
            'stop_loss': 590,
            'take_profit': 620
        }

        is_valid, error = AIPromptBuilder.validate_suggestion(
            suggestion, current_price=600, max_position=0.9
        )

        assert is_valid is False
        assert '低置信度' in error


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
