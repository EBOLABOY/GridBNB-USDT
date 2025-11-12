"""
AI提示词模板和数据封装模块

负责:
1. 将交易数据封装成结构化格式
2. 生成AI分析所需的提示词
3. 解析AI响应
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class AIPromptBuilder:
    """AI提示词构建器"""

    @staticmethod
    def build_analysis_data(
        symbol: str,
        market_data: Dict,
        technical_indicators: Dict,
        sentiment_data: Dict,
        portfolio: Dict,
        recent_trades: List[Dict],
        grid_status: Dict,
        risk_metrics: Dict,
        multi_timeframe: Optional[Dict] = None,  # 🆕 多时间周期数据
        orderbook: Optional[Dict] = None,  # 🆕 订单簿数据
        derivatives: Optional[Dict] = None,  # 🆕 衍生品数据
        correlation: Optional[Dict] = None  # 🆕 BTC相关性数据
    ) -> Dict:
        """
        构建发送给AI的结构化数据包（增强版）

        Args:
            symbol: 交易对
            market_data: 市场数据 (价格、成交量等)
            technical_indicators: 技术指标
            sentiment_data: 市场情绪数据
            portfolio: 持仓状态
            recent_trades: 最近交易记录
            grid_status: 网格策略状态
            risk_metrics: 风险指标
            multi_timeframe: 🆕 多时间周期分析数据
            orderbook: 🆕 订单簿深度数据
            derivatives: 🆕 衍生品数据（资金费率、持仓量）
            correlation: 🆕 BTC相关性数据

        Returns:
            结构化数据字典
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "market_data": market_data,
            "technical_indicators": technical_indicators,
            "third_party_signals": sentiment_data,
            "portfolio_status": portfolio,
            "recent_trades": recent_trades[-10:],  # 只保留最近10笔
            "grid_strategy_status": grid_status,
            "risk_metrics": risk_metrics
        }

        # 🆕 添加多时间周期数据
        if multi_timeframe:
            result["multi_timeframe_analysis"] = multi_timeframe

        # 🆕 添加订单簿数据
        if orderbook:
            result["orderbook_analysis"] = orderbook

        # 🆕 添加衍生品数据
        if derivatives:
            result["derivatives_data"] = derivatives

        # 🆕 添加BTC相关性数据
        if correlation:
            result["btc_correlation"] = correlation

        return result

    @staticmethod
    def build_prompt(data: Dict) -> str:
        """
        构建AI分析提示词

        Args:
            data: build_analysis_data返回的结构化数据

        Returns:
            完整的提示词字符串
        """
        md = data['market_data']
        ti = data['technical_indicators']
        fg = data['third_party_signals'].get('fear_greed', {})
        portfolio = data['portfolio_status']
        grid = data['grid_strategy_status']
        risk = data['risk_metrics']

        prompt = f"""你是一个专业的加密货币交易分析助手。请基于以下数据进行综合分析并给出交易建议。

**重要**: 你的角色是为一个运行中的网格交易系统提供"趋势判断和大局建议"。
- 网格策略会自动捕获小幅波动(1-4%),提供稳定收益
- 你的任务是识别更大的趋势机会,给出中长期的交易建议
- 你的建议应该与网格策略"协同"而非"替代"

【市场数据】
- 交易对: {data['symbol']}
- 当前价格: {md.get('current_price', 0):.2f} USDT
- 24小时涨跌: {md.get('24h_change', 0)}%
- 24小时成交量: {md.get('24h_volume', 0)}
- 24小时最高: {md.get('24h_high', 0):.2f} USDT
- 24小时最低: {md.get('24h_low', 0):.2f} USDT

{AIPromptBuilder._build_multi_timeframe_section(data)}

{AIPromptBuilder._build_orderbook_section(data)}

{AIPromptBuilder._build_derivatives_section(data)}

{AIPromptBuilder._build_correlation_section(data)}

【技术指标分析 (5分钟级别)】
1. RSI(14): {ti['rsi']['value']:.1f} ({ti['rsi']['trend']})
   - 信号: {ti['rsi']['signal']}

2. MACD:
   - MACD值: {ti['macd']['macd']:.4f}
   - 信号线: {ti['macd']['signal']:.4f}
   - 柱状图: {ti['macd']['histogram']:.4f}
   - 趋势: {ti['macd']['trend']}
   - 交叉状态: {ti['macd']['crossover']}

3. 布林带:
   - 上轨: {ti['bollinger_bands']['upper']:.2f} USDT
   - 中轨: {ti['bollinger_bands']['middle']:.2f} USDT
   - 下轨: {ti['bollinger_bands']['lower']:.2f} USDT
   - 带宽: {ti['bollinger_bands']['width']:.2f}
   - 价格位置: {ti['bollinger_bands']['position']}

4. 移动平均线:
   - EMA20: {ti['ema_20']:.2f} USDT
   - EMA50: {ti['ema_50']:.2f} USDT

5. 成交量分析:
   - 当前成交量: {ti['volume_analysis']['current_volume']:.2f}
   - 平均成交量: {ti['volume_analysis']['avg_volume']:.2f}
   - 成交量比率: {ti['volume_analysis']['volume_ratio']:.2f}x
   - 趋势: {ti['volume_analysis']['trend']}

【市场情绪】
- 恐惧贪婪指数: {fg.get('value', 50)} ({fg.get('classification', 'Unknown')})
- 情绪趋势: {fg.get('trend', 'unknown')}
- 综合情绪: {data['third_party_signals'].get('overall_sentiment', 'neutral')}

【当前持仓状态】
- 账户总价值: {portfolio.get('total_value_usdt', 0):.2f} USDT
- 基础资产价值: {portfolio.get('base_asset_value', 0):.2f} USDT
- 报价资产余额: {portfolio.get('quote_asset_value', 0):.2f} USDT
- 仓位比例: {portfolio.get('position_ratio', 0)*100:.1f}% (基础资产/总资产)
- 未实现盈亏: {portfolio.get('unrealized_pnl', 0):.2f} USDT ({portfolio.get('pnl_percentage', 0):.2f}%)

【网格策略运行状态】
⚠️ **重要**: 网格策略正在自动运行,会在以下价位自动交易:
- 基准价格: {grid.get('base_price', 0):.2f} USDT
- 网格大小: {grid.get('grid_size', 0):.2f}%
- 上轨(卖出触发): {grid.get('upper_band', 0):.2f} USDT
- 下轨(买入触发): {grid.get('lower_band', 0):.2f} USDT
- 当前波动率: {grid.get('current_volatility', 0):.2f}
- 下次网格买入价: {grid.get('next_buy_price', 0):.2f} USDT
- 下次网格卖出价: {grid.get('next_sell_price', 0):.2f} USDT

💡 **网格策略特点**:
- 会在价格上涨{grid.get('grid_size', 0):.2f}%时自动卖出
- 会在价格下跌{grid.get('grid_size', 0):.2f}%时自动买入
- 适合捕获横盘震荡行情的小幅波动

【风险控制指标】
- 最大仓位限制: {risk.get('max_position_ratio', 0)*100:.0f}%
- 最小仓位限制: {risk.get('min_position_ratio', 0)*100:.0f}%
- 当前风控状态: {risk.get('current_risk_state', 'UNKNOWN')}
- 连续亏损次数: {risk.get('consecutive_losses', 0)}
- 最大回撤: {risk.get('max_drawdown', 'N/A')}

【最近交易记录】
{AIPromptBuilder._format_recent_trades(data['recent_trades'])}

【分析要求】
作为"深度市场分析大脑",请综合分析当前市场环境,并给出建议。你现在拥有**远超普通交易员**的数据维度:

⚠️ **核心分析框架** (按重要性递减):

1. **多时间周期共振分析** (最重要！):
   - 日线、4小时、1小时三个周期是否一致?
   - 是否存在危险背离? (如：日线下跌但1H反弹 = 接飞刀风险)
   - 多周期共振信号最可靠，单周期信号需谨慎

2. **订单簿压力分析**:
   - 上方是否有大单墙阻力? 突破难度如何?
   - 下方支撑是否扎实? 回调空间多大?
   - 买卖失衡度显示真实压力方向

3. **衍生品数据验证**:
   - 资金费率是否显示过度多头/空头?
   - 持仓量变化是否支持价格趋势?
   - **关键组合判断**:
     * 价格上涨 + OI增加 = 趋势健康
     * 价格上涨 + OI下降 = ⚠️ 诱多风险
     * Funding Rate > 0.05% = 多头过度拥挤

4. **BTC联动性判断**:
   - 相关性高(>0.7)时，必须参考BTC走势
   - BTC下跌 + 高相关性 = 个币很难独善其身
   - BTC/个币背离 + 高相关性 = 警惕反转

5. **与网格策略的协同性**:
   - 网格策略会自动处理{grid.get('grid_size', 0):.2f}%左右的小幅波动
   - 你应该关注更大的趋势机会(>5-10%的价格变动)
   - 只在多维度数据共振时才建议交易

6. **综合风险评估**:
   - 仓位比例({portfolio.get('position_ratio', 0)*100:.1f}%)是否合理?
   - 是否值得在网格之外额外建仓?
   - 风险收益比是否足够吸引?

💡 **决策优先级**:
   震荡市场 (多时间周期不一致 + 订单簿平衡) → 建议 HOLD
   危险背离 (日线空头但1H多头 + 高相关性BTC下跌) → 强烈建议 HOLD/SELL
   完美共振 (三周期一致 + 订单簿支持 + OI健康 + BTC同向) → 可建议 BUY/SELL

【输出格式要求】
请严格按照以下JSON格式返回你的建议(只返回JSON,不要有其他文字):
{{
  "action": "buy/sell/hold",
  "confidence": 0-100之间的整数,
  "suggested_amount_pct": 10-25之间的整数(占总资产的百分比,因为是趋势交易建议更大仓位),
  "reason": "简要理由,说明为什么这是一个值得在网格之外额外操作的机会,不超过150字",
  "risk_level": "low/medium/high",
  "time_horizon": "short/medium/long",
  "stop_loss": 止损价格(数字)或null,
  "take_profit": 止盈价格(数字)或null,
  "additional_notes": "补充说明,特别是与网格策略的协同建议"
}}

注意:
- confidence低于60表示市场不明朗,建议hold让网格策略工作
- 只有在明确的趋势机会时才建议buy/sell
- suggested_amount_pct建议范围10%-25%(因为是趋势建议,金额应该比网格单次交易更大)
- 如果action是hold,suggested_amount_pct设为0
- 价格建议应考虑当前价格{md.get('current_price', 0):.2f} USDT
- **重要**: 在震荡市场中应该建议hold,让网格策略发挥优势
- **重要**: 只在明确的趋势信号(多指标共振+市场情绪一致)时才建议交易
"""

        return prompt

    @staticmethod
    def _format_recent_trades(trades: List[Dict]) -> str:
        """格式化最近交易记录"""
        if not trades:
            return "暂无交易记录"

        lines = []
        for i, trade in enumerate(trades[-5:], 1):  # 只显示最近5笔
            lines.append(
                f"{i}. {trade.get('time', 'N/A')} | "
                f"{trade.get('side', 'N/A')} | "
                f"价格: {trade.get('price', 0):.2f} | "
                f"数量: {trade.get('amount', 0):.4f} | "
                f"盈亏: {trade.get('pnl', 'N/A')}"
            )

        return "\n".join(lines)

    @staticmethod
    def parse_ai_response(response_text: str) -> Optional[Dict]:
        """
        解析AI响应

        Args:
            response_text: AI返回的文本

        Returns:
            解析后的建议字典,或None(解析失败)
        """
        try:
            # 尝试提取JSON部分
            # 有些AI可能在JSON前后添加说明文字
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("响应中未找到JSON")

            json_str = response_text[start:end]
            result = json.loads(json_str)

            # 验证必要字段
            required_fields = ['action', 'confidence', 'suggested_amount_pct', 'reason']
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"缺少必要字段: {field}")

            # 验证值的合理性
            if result['action'] not in ['buy', 'sell', 'hold']:
                raise ValueError(f"无效的action: {result['action']}")

            if not 0 <= result['confidence'] <= 100:
                raise ValueError(f"无效的confidence: {result['confidence']}")

            if not 0 <= result['suggested_amount_pct'] <= 50:
                raise ValueError(f"无效的suggested_amount_pct: {result['suggested_amount_pct']}")

            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"响应解析异常: {e}")

    @staticmethod
    def validate_suggestion(suggestion: Dict, current_price: float, max_position: float) -> Tuple[bool, Optional[str]]:
        """
        验证AI建议的合理性

        Args:
            suggestion: AI返回的建议
            current_price: 当前价格
            max_position: 最大仓位比例

        Returns:
            (是否通过验证, 失败原因)
        """
        # 检查止损价是否合理
        if suggestion.get('stop_loss') is not None:
            stop_loss = float(suggestion['stop_loss'])
            if suggestion['action'] == 'buy' and stop_loss >= current_price:
                return False, f"买入止损价{stop_loss}应低于当前价{current_price}"
            if suggestion['action'] == 'sell' and stop_loss <= current_price:
                return False, f"卖出止损价{stop_loss}应高于当前价{current_price}"

        # 检查止盈价是否合理
        if suggestion.get('take_profit') is not None:
            take_profit = float(suggestion['take_profit'])
            if suggestion['action'] == 'buy' and take_profit <= current_price:
                return False, f"买入止盈价{take_profit}应高于当前价{current_price}"
            if suggestion['action'] == 'sell' and take_profit >= current_price:
                return False, f"卖出止盈价{take_profit}应低于当前价{current_price}"

        # 检查金额比例
        amount_pct = suggestion['suggested_amount_pct']
        if amount_pct > 30:
            return False, f"建议金额比例过高: {amount_pct}%"

        # 检查置信度和行动的匹配
        if suggestion['confidence'] < 50 and suggestion['action'] != 'hold':
            return False, f"低置信度({suggestion['confidence']}%)不应建议交易"

        return True, None

    @staticmethod
    def _build_multi_timeframe_section(data: Dict) -> str:
        """
        构建多时间周期分析部分的 Prompt

        这是给AI最重要的"市场全景"信息
        """
        mtf = data.get('multi_timeframe_analysis')

        if not mtf:
            return "【多时间周期分析】\n⚠️ 数据暂时不可用\n"

        macro = mtf.get('macro_trend', {})
        meso = mtf.get('meso_trend', {})
        micro = mtf.get('micro_trend', {})
        overall = mtf.get('overall_context', {})

        section = f"""
【🔭 多时间周期分析 - 市场全景】
⚠️ **这是最重要的部分！不同时间周期给你"立体"的市场视角**

📅 宏观趋势 (日线级别 - 定大方向):
   状态: {macro.get('direction', 'unknown').upper()} ({macro.get('strength', 'weak')} strength)
   描述: {macro.get('description', 'N/A')}
   关键位: EMA200={macro.get('key_levels', {}).get('ema_200', 0):.2f},
         阻力={macro.get('key_levels', {}).get('resistance', 0):.2f},
         支撑={macro.get('key_levels', {}).get('support', 0):.2f}
   MACD状态: {macro.get('macd_state', 'neutral')}
   RSI状态: {macro.get('rsi_extreme', 'neutral')}

   💡 解读: {"日线多头，大方向向上" if macro.get('direction') == 'bullish' else
            "日线空头，大方向向下" if macro.get('direction') == 'bearish' else
            "日线震荡，方向不明"}

⏰ 中观波段 (4小时级别 - 看波段):
   波段方向: {meso.get('wave_direction', 'unknown').upper()}
   描述: {meso.get('description', 'N/A')}
   均线排列: {meso.get('ema_alignment', 'N/A')}
   MACD信号: {meso.get('macd_signal', 'N/A')}
   波段高点: {meso.get('recent_swing_high', 0):.2f}
   波段低点: {meso.get('recent_swing_low', 0):.2f}

   💡 解读: {"4小时上升波段" if meso.get('wave_direction') == 'upward' else
            "4小时下降波段" if meso.get('wave_direction') == 'downward' else
            "4小时横盘震荡"}

⚡ 微观入场点 (15分钟级别 - 找入场):
   入场信号: {micro.get('entry_signal', 'wait').upper()}
   描述: {micro.get('description', 'N/A')}
   RSI: {micro.get('rsi_value', 50):.1f}
   布林带位置: {micro.get('bb_position', 'middle')}
   成交量状态: {micro.get('volume_state', 'normal')}

   💡 解读: {"可能有买入机会" if micro.get('entry_signal') == 'buy_opportunity' else
            "可能有卖出机会" if micro.get('entry_signal') == 'sell_opportunity' else
            "等待更好的时机"}

🎯 综合判断:
   市场状态: {overall.get('market_state', 'unknown')}
   置信度: {overall.get('confidence_level', 'low').upper()}
   交易建议: {overall.get('trading_advice', 'N/A')}

   {"✨ 多周期共振信号:" if overall.get('resonance_signals') and len(overall.get('resonance_signals', [])) > 0 and overall['resonance_signals'][0] != "无特殊共振信号" else ""}
   {chr(10).join(f"   - {signal}" for signal in overall.get('resonance_signals', []) if signal != "无特殊共振信号")}

   📊 总结: {overall.get('summary', 'N/A')}

💡 **如何使用多时间周期信息**:
   1. 日线定大方向 → 如果日线多头，优先考虑做多；日线空头，谨慎做多
   2. 4小时看波段 → 确定当前是反弹还是回调
   3. 15分钟找入场点 → 寻找精准的买卖时机
   4. 共振信号最可靠 → 多个时间周期同时指向一个方向时，成功率最高
"""

        return section

    @staticmethod
    def _build_orderbook_section(data: Dict) -> str:
        """构建订单簿深度分析部分"""
        ob = data.get('orderbook_analysis')

        if not ob:
            return "【📖 订单簿深度分析】\n⚠️ 数据暂时不可用\n"

        section = f"""
【📖 订单簿深度分析 - 市场微观结构】
💡 **订单簿显示真实的买卖压力和大单墙**

价差与流动性:
- 买卖价差: {ob.get('spread', 0):.4f} USDT ({ob.get('spread_percent', 0):.4f}%)
- 买盘深度: {ob.get('buy_depth', 0):.2f} (上下1%范围内)
- 卖盘深度: {ob.get('sell_depth', 0):.2f}
- 深度比率: {ob.get('depth_ratio', 1):.2f} (买盘/卖盘)
- 买卖失衡度: {ob.get('imbalance', 0):.2%} {"(买盘强)" if ob.get('imbalance', 0) > 0 else "(卖盘强)" if ob.get('imbalance', 0) < 0 else "(平衡)"}

流动性信号: {ob.get('liquidity_signal', 'unknown').upper()}

上方阻力墙 (可能阻碍上涨):
{chr(10).join(f"   - 价格 {wall['price']:.2f} USDT: {wall['amount']:.0f} 单位 (距离 +{wall['distance_percent']:.2f}%)"
    for wall in ob.get('resistance_walls', [])) if ob.get('resistance_walls') else "   - 无明显大单墙"}

下方支撑墙 (可能支撑下跌):
{chr(10).join(f"   - 价格 {wall['price']:.2f} USDT: {wall['amount']:.0f} 单位 (距离 {wall['distance_percent']:.2f}%)"
    for wall in ob.get('support_walls', [])) if ob.get('support_walls') else "   - 无明显大单墙"}

交易洞察:
{ob.get('trading_insight', '暂无特别洞察')}

💡 **如何使用订单簿信息**:
- 大单墙是价格阻力或支撑的直接证据
- 买盘失衡>0.2 表示强买压，价格容易上涨
- 卖盘失衡<-0.2 表示强卖压，价格容易下跌
- 上方有大量抛压墙时，短期突破困难
"""

        return section

    @staticmethod
    def _build_derivatives_section(data: Dict) -> str:
        """构建衍生品数据部分"""
        deriv = data.get('derivatives_data', {})

        if not deriv:
            return "【💰 期货衍生品数据】\n⚠️ 数据暂时不可用\n"

        funding = deriv.get('funding_rate', {})
        oi = deriv.get('open_interest', {})

        # 解读资金费率
        funding_interpretation = ""
        if funding.get('current_rate', 0) > 0.05:
            funding_interpretation = "⚠️ 多头成本极高！可能面临空头反扑"
        elif funding.get('current_rate', 0) > 0.01:
            funding_interpretation = "多头情绪积极，但需警惕过度多头"
        elif funding.get('current_rate', 0) < -0.05:
            funding_interpretation = "⚠️ 空头成本极高！可能面临多头反攻"
        elif funding.get('current_rate', 0) < -0.01:
            funding_interpretation = "空头情绪积极，但需警惕过度空头"
        else:
            funding_interpretation = "资金费率中性，市场情绪平衡"

        # 解读持仓量
        oi_interpretation = ""
        oi_change = oi.get('24h_change', 0)
        if oi_change > 5:
            oi_interpretation = "大量资金进入，趋势可能继续"
        elif oi_change > 2:
            oi_interpretation = "资金稳定进入，市场活跃"
        elif oi_change < -5:
            oi_interpretation = "⚠️ 大量资金撤离，趋势可能反转"
        elif oi_change < -2:
            oi_interpretation = "资金逐渐撤离，关注趋势变化"
        else:
            oi_interpretation = "持仓量稳定，市场观望"

        section = f"""
【💰 期货衍生品数据 - 资金与持仓】
💡 **衍生品数据揭示大资金的真实动向**

资金费率 (Funding Rate):
- 当前费率: {funding.get('current_rate_display', 'N/A')} ({funding.get('sentiment', 'neutral')})
- 下次结算: {funding.get('next_funding_time', 'N/A')}
- 解读: {funding_interpretation}
{f"- ⚠️ 警告: {funding.get('warning', 'N/A')}" if funding.get('warning') else ""}

持仓量 (Open Interest):
- 当前持仓量: {oi.get('current_display', 'N/A')} 张
- 24小时变化: {oi.get('24h_change_display', 'N/A')} ({oi.get('trend', 'unknown')})
- 资金信号: {oi.get('signal', 'unknown').replace('_', ' ').upper()}
- 解读: {oi_interpretation}

💡 **如何使用衍生品数据**:
- 资金费率>0.05% 表示多头过度拥挤，易回调
- 资金费率<-0.05% 表示空头过度拥挤，易反弹
- 价格上涨+持仓量增加 = 趋势健康
- 价格上涨+持仓量下降 = ⚠️ 诱多风险
- 价格下跌+持仓量增加 = 下跌趋势加强
- 价格下跌+持仓量下降 = 可能接近底部
"""

        return section

    @staticmethod
    def _build_correlation_section(data: Dict) -> str:
        """构建BTC相关性分析部分"""
        corr = data.get('btc_correlation')

        if not corr:
            return "【₿ BTC相关性分析】\n⚠️ 数据暂时不可用\n"

        btc = corr.get('btc_current_state', {})
        target = corr.get('target_state', {})
        coef = corr.get('correlation_coefficient', 0)
        strength = corr.get('correlation_strength', 'unknown')

        # 相关性解读
        if strength == "high":
            corr_desc = f"高度相关 (系数{coef:.2f})，走势基本跟随BTC"
        elif strength == "medium":
            corr_desc = f"中度相关 (系数{coef:.2f})，部分受BTC影响"
        else:
            corr_desc = f"相关性低 (系数{coef:.2f})，走势相对独立"

        section = f"""
【₿ BTC关联性分析 - 大盘影响】
💡 **加密货币市场高度联动，BTC是风向标**

相关性强度:
- 相关系数: {coef:.3f}
- 相关强度: {strength.upper()}
- BTC主导性: {corr.get('btc_dominance_impact', 'unknown').replace('_', ' ').upper()}
- 解读: {corr_desc}

BTC当前状态:
- BTC价格: ${btc.get('price', 0):,.2f}
- 24H变化: {btc.get('24h_change', 0):+.2f}%
- 短期趋势: {btc.get('short_term_trend', 'unknown').replace('_', ' ').upper()}
- 动能状态: {btc.get('momentum', 'unknown').upper()}

目标币种 ({data.get('symbol', '')}) 状态:
- 24H变化: {target.get('24h_change', 0):+.2f}%
- 短期趋势: {target.get('short_term_trend', 'unknown').replace('_', ' ').upper()}
- 相对强度: {target.get('relative_strength', 'unknown').upper()}

{f"⚠️ 风险警告: {corr.get('risk_warning')}" if corr.get('risk_warning') else ""}

交易洞察:
{corr.get('trading_insight', '暂无特别洞察')}

💡 **如何使用BTC相关性**:
- 高相关性(>0.7) + BTC下跌 = ⚠️ 目标币种很难独善其身
- 高相关性(>0.7) + BTC上涨 = 可顺势操作目标币种
- BTC下跌但目标币种上涨 + 高相关性 = ⚠️ 背离风险，上涨可能不持续
- 低相关性(<0.4) = 目标币种有独立行情，可忽略BTC影响
"""

        return section
