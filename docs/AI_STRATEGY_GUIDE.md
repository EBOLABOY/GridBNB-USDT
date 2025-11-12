# AI辅助交易策略使用指南

## 概述

AI辅助交易策略是GridBNB-USDT交易系统的高级功能,它结合技术指标、市场情绪和AI分析来增强交易决策。该策略与现有的动态网格策略协同工作,提供更智能的交易建议。

## 核心功能

### 1. 技术指标分析
- **RSI (相对强弱指标)**: 检测超买/超卖状态
- **MACD (指数平滑移动平均线)**: 识别趋势和动量变化
- **布林带 (Bollinger Bands)**: 评估价格波动范围和突破
- **EMA (指数移动平均线)**: 20期和50期EMA分析
- **成交量分析**: 检测异常成交量和价量配合

### 2. 市场情绪数据
- **Fear & Greed Index**: 从Alternative.me获取加密市场情绪指标
- **综合情绪判断**: 基于多个维度的市场情绪分析
- **1小时缓存**: 减少API调用并提高响应速度

### 3. AI分析引擎
- **多模型支持**: 支持OpenAI (GPT-4, GPT-3.5) 和 Anthropic (Claude)
- **智能触发机制**:
  - 时间间隔触发 (默认15分钟)
  - 技术指标重大变化 (MACD金叉/死叉, RSI突破阈值, 布林带突破)
  - 市场异常波动 (1小时内价格变动超过5%)
- **结构化提示词**: 包含完整的市场数据、技术指标、持仓状态和网格策略信息
- **智能响应解析**: 自动提取和验证AI建议

### 4. 风险控制
- **置信度阈值**: 只执行置信度高于设定阈值的建议 (默认70%)
- **每日调用限制**: 防止过度调用AI产生高额费用 (默认100次/天)
- **金额比例限制**: AI建议的交易金额不超过总资产的30%
- **建议验证**: 自动验证止损/止盈价格的合理性
- **风控协同**: 与现有的AdvancedRiskManager协同工作

## 配置说明

### 环境变量配置

在`.env`文件中添加以下配置:

```bash
# ========== AI辅助交易配置 ==========
# 是否启用AI辅助交易策略 (true/false)
AI_ENABLED=false

# AI提供商: openai / anthropic
AI_PROVIDER=openai

# AI模型
# OpenAI: gpt-4-turbo, gpt-3.5-turbo
# Anthropic: claude-3-opus-20240229, claude-3-sonnet-20240229
AI_MODEL=gpt-4-turbo

# AI API密钥
# OpenAI: 从 https://platform.openai.com/api-keys 获取
# Anthropic: 从 https://console.anthropic.com/settings/keys 获取
AI_API_KEY=sk-your-api-key-here

# AI建议置信度阈值 (0-100)
# 只有置信度高于此阈值的建议才会被执行
AI_CONFIDENCE_THRESHOLD=70

# AI触发间隔 (秒)
# 每隔多久检查一次是否需要调用AI分析
# 建议: 900 (15分钟) 或 1800 (30分钟)
AI_TRIGGER_INTERVAL=900

# 每日最大AI调用次数
# 防止过度调用产生高额费用
AI_MAX_CALLS_PER_DAY=100

# AI失败时是否回退到纯网格策略 (true/false)
AI_FALLBACK_TO_GRID=true
```

### 配置参数详解

#### AI_ENABLED
- **类型**: Boolean
- **默认值**: false
- **说明**: 是否启用AI辅助交易策略。设置为`true`后,系统会在满足触发条件时调用AI进行分析。

#### AI_PROVIDER
- **类型**: String
- **可选值**: `openai`, `anthropic`
- **默认值**: openai
- **说明**: AI服务提供商选择。

#### AI_MODEL
- **类型**: String
- **OpenAI可选值**:
  - `gpt-4-turbo`: 最强性能,费用较高
  - `gpt-3.5-turbo`: 性价比高,响应快
- **Anthropic可选值**:
  - `claude-3-opus-20240229`: 最强性能
  - `claude-3-sonnet-20240229`: 平衡性能和成本
- **说明**: 选择具体的AI模型。

#### AI_API_KEY
- **类型**: String
- **说明**: AI服务的API密钥。
- **获取方式**:
  - OpenAI: https://platform.openai.com/api-keys
  - Anthropic: https://console.anthropic.com/settings/keys

#### AI_CONFIDENCE_THRESHOLD
- **类型**: Integer (0-100)
- **默认值**: 70
- **说明**: AI建议的最低置信度要求。低于此阈值的建议将被忽略。
- **建议值**: 50-80之间

#### AI_TRIGGER_INTERVAL
- **类型**: Integer (秒)
- **默认值**: 900 (15分钟)
- **说明**: AI分析的最小时间间隔。
- **建议值**:
  - 900秒 (15分钟) - 适中频率
  - 1800秒 (30分钟) - 降低调用频率和成本
  - 600秒 (10分钟) - 更频繁的分析 (可能增加成本)

#### AI_MAX_CALLS_PER_DAY
- **类型**: Integer
- **默认值**: 100
- **说明**: 每日最大AI调用次数,用于控制成本。
- **成本估算** (以GPT-4-turbo为例):
  - 每次调用约0.02-0.05 USD
  - 100次/天 ≈ 2-5 USD/天 ≈ 60-150 USD/月

#### AI_FALLBACK_TO_GRID
- **类型**: Boolean
- **默认值**: true
- **说明**: 当AI调用失败时,是否继续使用网格策略交易。

## 工作流程

### 1. 触发检查
系统在主交易循环的"周期性维护模块"中检查是否应该触发AI分析:

```python
# 1. 时间间隔触发
if now - last_trigger_time >= AI_TRIGGER_INTERVAL:
    trigger AI analysis

# 2. 技术指标重大变化
if MACD golden_cross or death_cross:
    trigger AI analysis
if RSI crosses 30 or 70:
    trigger AI analysis
if price breaks Bollinger Bands:
    trigger AI analysis

# 3. 市场异常波动
if price_change_1h > 5%:
    trigger AI analysis
```

### 2. 数据收集
触发后,系统收集以下数据:
- 最近100根5分钟K线数据
- 计算所有技术指标
- 获取Fear & Greed Index
- 读取当前持仓状态
- 获取最近10笔交易记录
- 读取网格策略状态

### 3. AI分析
将收集的数据封装成结构化提示词,发送给AI模型进行分析。

AI返回的建议包含:
```json
{
  "action": "buy/sell/hold",
  "confidence": 75,
  "suggested_amount_pct": 12,
  "reason": "MACD金叉且RSI处于中性区间,市场情绪偏多",
  "risk_level": "medium",
  "time_horizon": "short",
  "stop_loss": 590.0,
  "take_profit": 620.0,
  "additional_notes": null
}
```

### 4. 建议验证
系统自动验证AI建议:
- 置信度是否 >= AI_CONFIDENCE_THRESHOLD
- 止损/止盈价格是否合理
- 建议金额比例是否 <= 30%
- 是否与风控许可冲突

### 5. 执行交易
如果建议通过验证且风控允许,系统会执行AI建议的交易:
- 计算实际交易金额 (总资产 × suggested_amount_pct%)
- 检查账户余额
- 执行市价单
- 记录AI交易
- 发送通知

## 使用示例

### 示例1: 启用OpenAI GPT-4

```bash
AI_ENABLED=true
AI_PROVIDER=openai
AI_MODEL=gpt-4-turbo
AI_API_KEY=sk-proj-xxxxxxxxxxxxx
AI_CONFIDENCE_THRESHOLD=70
AI_TRIGGER_INTERVAL=900
AI_MAX_CALLS_PER_DAY=100
AI_FALLBACK_TO_GRID=true
```

### 示例2: 使用Anthropic Claude (更经济)

```bash
AI_ENABLED=true
AI_PROVIDER=anthropic
AI_MODEL=claude-3-sonnet-20240229
AI_API_KEY=sk-ant-xxxxxxxxxxxxx
AI_CONFIDENCE_THRESHOLD=75
AI_TRIGGER_INTERVAL=1800
AI_MAX_CALLS_PER_DAY=50
AI_FALLBACK_TO_GRID=true
```

### 示例3: 保守模式 (高置信度要求)

```bash
AI_ENABLED=true
AI_PROVIDER=openai
AI_MODEL=gpt-4-turbo
AI_API_KEY=sk-proj-xxxxxxxxxxxxx
AI_CONFIDENCE_THRESHOLD=80  # 更高的置信度要求
AI_TRIGGER_INTERVAL=1800    # 更长的触发间隔
AI_MAX_CALLS_PER_DAY=50     # 更少的调用次数
AI_FALLBACK_TO_GRID=true
```

## 运行日志示例

启用AI策略后,您会在日志中看到类似输出:

```
2025-10-21 14:30:00 | INFO | GridTrader[BNB/USDT] | AI辅助策略已启用
2025-10-21 14:45:00 | INFO | GridTrader[BNB/USDT] | 触发AI分析 | 原因: time_interval
2025-10-21 14:45:15 | INFO | AITradingStrategy | AI分析完成 | 建议: buy | 置信度: 75% | 金额: 12%
2025-10-21 14:45:15 | INFO | GridTrader[BNB/USDT] | AI建议 | 操作: buy | 置信度: 75% | 金额比例: 12% | 理由: MACD金叉,RSI中性
2025-10-21 14:45:16 | INFO | GridTrader[BNB/USDT] | 执行AI建议交易 | 方向: buy | 价格: 600.50 | 数量: 2.0 | 金额: 1200 USDT
2025-10-21 14:45:17 | INFO | GridTrader[BNB/USDT] | AI交易执行成功 | 订单ID: 123456789
```

## 成本估算

### OpenAI GPT-4-turbo
- **输入Token**: ~1500 tokens/请求 × $0.01/1K tokens = $0.015
- **输出Token**: ~300 tokens/请求 × $0.03/1K tokens = $0.009
- **总计**: ~$0.024/请求
- **每日成本** (100次): ~$2.40/天 = ~$72/月

### OpenAI GPT-3.5-turbo
- **输入Token**: ~1500 tokens × $0.0015/1K = $0.00225
- **输出Token**: ~300 tokens × $0.002/1K = $0.0006
- **总计**: ~$0.003/请求
- **每日成本** (100次): ~$0.30/天 = ~$9/月

### Anthropic Claude-3-Sonnet
- **输入Token**: ~1500 tokens × $0.003/1K = $0.0045
- **输出Token**: ~300 tokens × $0.015/1K = $0.0045
- **总计**: ~$0.009/请求
- **每日成本** (100次): ~$0.90/天 = ~$27/月

## 最佳实践

### 1. 初期测试
- 从`AI_CONFIDENCE_THRESHOLD=80`开始,只执行高置信度建议
- 设置`AI_MAX_CALLS_PER_DAY=50`控制成本
- 监控1-2周,评估AI建议的准确性

### 2. 成本控制
- 使用GPT-3.5-turbo或Claude-3-Sonnet降低成本
- 增加`AI_TRIGGER_INTERVAL`减少调用频率
- 降低`AI_MAX_CALLS_PER_DAY`限制

### 3. 风险管理
- 始终启用`AI_FALLBACK_TO_GRID=true`
- 不要完全依赖AI,保持网格策略作为基础
- 定期查看AI交易日志和通知

### 4. 性能优化
- 在高波动市场中,可以降低`AI_TRIGGER_INTERVAL`到600秒
- 在稳定市场中,可以提高到1800-3600秒

## 故障排除

### 问题1: AI策略未启用
**症状**: 日志中没有AI相关输出

**解决方案**:
1. 检查`.env`中`AI_ENABLED=true`
2. 检查AI SDK是否安装: `pip install openai anthropic`
3. 查看日志是否有"AI策略模块未安装或导入失败"警告

### 问题2: AI调用失败
**症状**: 日志显示"AI调用失败"或"AI API调用失败"

**解决方案**:
1. 验证API密钥是否正确
2. 检查网络连接
3. 确认API配额未超限
4. 查看具体错误信息

### 问题3: 今日调用已达上限
**症状**: 日志显示"今日AI调用已达上限"

**解决方案**:
1. 等待第二天自动重置
2. 或增加`AI_MAX_CALLS_PER_DAY`值
3. 检查是否有异常频繁触发

### 问题4: AI建议被忽略
**症状**: AI给出建议但未执行

**可能原因**:
1. 置信度低于阈值
2. 建议验证失败 (止损/止盈价格不合理)
3. 风控状态不允许该方向交易
4. 账户余额不足

**解决方案**: 查看日志中的具体原因

## 注意事项

⚠️ **重要提醒**:

1. **AI不是万能的**: AI建议仅供参考,不保证盈利。务必结合自己的判断。

2. **成本控制**: 密切关注AI API的使用成本,避免产生意外高额费用。

3. **API密钥安全**:
   - 不要将`.env`文件提交到Git
   - 定期更换API密钥
   - 限制API密钥的权限范围

4. **测试环境**: 建议先在测试账户上运行,验证策略有效性后再用于实盘。

5. **监控和日志**: 定期查看AI交易日志和PushPlus通知,了解AI决策情况。

6. **网格策略协同**: AI策略是网格策略的补充,而非替代。保持网格策略的正常运行。

## 技术架构

### 模块结构
```
src/strategies/
├── ai_strategy.py           # AI策略核心逻辑
├── ai_prompt.py             # AI提示词构建和解析
├── technical_indicators.py  # 技术指标计算
└── market_sentiment.py      # 市场情绪数据获取
```

### 数据流
```
1. 主循环 (trader.py)
   ↓
2. 触发检查 (should_trigger)
   ↓
3. 数据收集 (_collect_analysis_data)
   ↓
4. 提示词构建 (AIPromptBuilder.build_prompt)
   ↓
5. AI调用 (_call_ai_model)
   ↓
6. 响应解析 (AIPromptBuilder.parse_ai_response)
   ↓
7. 建议验证 (AIPromptBuilder.validate_suggestion)
   ↓
8. 执行交易 (_execute_ai_trade)
```

## 更新日志

### v1.0.0 (2025-10-21)
- 初始版本发布
- 支持OpenAI和Anthropic
- 实现技术指标分析
- 集成Fear & Greed Index
- 添加智能触发机制
- 完整的风险控制

## 支持

如有问题或建议,请在GitHub仓库提交Issue:
https://github.com/langchou/GridBNB-USDT/issues
