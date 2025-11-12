"""
配置项定义 - 中央配置清单

定义所有可配置项的元数据，包括：
- 显示名称、描述
- 数据类型和默认值
- 验证规则
- 配置分类
- 是否敏感、是否必填、是否需要重启

这个文件是配置管理的"单一真相来源"，用于：
1. 数据库初始化
2. 前端表单生成
3. 配置验证
"""

from typing import Dict, Any, List
from src.database.models import ConfigTypeEnum

# 配置项定义结构
ConfigDefinition = Dict[str, Any]


# ============================================================================
# 交易所配置 (EXCHANGE)
# ============================================================================
EXCHANGE_CONFIGS: List[ConfigDefinition] = [
    {
        "config_key": "EXCHANGE",
        "display_name": "交易所选择",
        "description": "当前使用的交易所，支持 binance 或 okx",
        "config_type": ConfigTypeEnum.EXCHANGE,
        "data_type": "string",
        "default_value": "binance",
        "validation_rules": {
            "enum": ["binance", "okx"],
            "required": True
        },
        "is_required": True,
        "is_sensitive": False,
        "requires_restart": True,
    },
    {
        "config_key": "TESTNET_MODE",
        "display_name": "测试网模式",
        "description": "是否使用测试网（模拟盘），开启后使用测试币，不影响真实资金",
        "config_type": ConfigTypeEnum.EXCHANGE,
        "data_type": "boolean",
        "default_value": "false",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": True,
    },
    {
        "config_key": "HTTP_PROXY",
        "display_name": "HTTP代理",
        "description": "网络代理地址（可选），格式: http://host:port 或 socks5://host:port",
        "config_type": ConfigTypeEnum.EXCHANGE,
        "data_type": "string",
        "default_value": "",
        "validation_rules": {
            "pattern": r"^(https?|socks5)://.*:\d+$",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": True,
    },
    {
        "config_key": "API_TIMEOUT",
        "display_name": "API超时时间",
        "description": "API请求超时时间（毫秒）",
        "config_type": ConfigTypeEnum.EXCHANGE,
        "data_type": "number",
        "default_value": "60000",
        "validation_rules": {
            "type": "integer",
            "min": 5000,
            "max": 120000
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "ENABLE_SAVINGS_FUNCTION",
        "display_name": "启用理财功能",
        "description": "是否启用自动理财功能（Binance Simple Earn / OKX Earn）",
        "config_type": ConfigTypeEnum.EXCHANGE,
        "data_type": "boolean",
        "default_value": "true",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
]


# ============================================================================
# 交易策略配置 (TRADING)
# ============================================================================
TRADING_CONFIGS: List[ConfigDefinition] = [
    {
        "config_key": "SYMBOLS",
        "display_name": "交易对列表",
        "description": "要交易的币对，多个用逗号分隔（如: BNB/USDT,ETH/USDT）",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "string",
        "default_value": "BNB/USDT",
        "validation_rules": {
            "pattern": r"^[A-Z]+/[A-Z]+(,[A-Z]+/[A-Z]+)*$",
            "required": True
        },
        "is_required": True,
        "is_sensitive": False,
        "requires_restart": True,
    },
    {
        "config_key": "INITIAL_GRID",
        "display_name": "初始网格大小",
        "description": "初始网格大小（百分比），范围 0.1-10%",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "number",
        "default_value": "2.0",
        "validation_rules": {
            "type": "float",
            "min": 0.1,
            "max": 10.0
        },
        "is_required": True,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "MIN_TRADE_AMOUNT",
        "display_name": "最小交易金额",
        "description": "单笔交易最小金额（USDT），Binance最低10 USDT",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "number",
        "default_value": "20.0",
        "validation_rules": {
            "type": "float",
            "min": 10.0,
            "max": 10000.0
        },
        "is_required": True,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "INITIAL_PARAMS_JSON",
        "display_name": "交易对特定参数",
        "description": "按交易对设置的初始参数（JSON格式），如: {\"BNB/USDT\": {\"initial_base_price\": 600.0, \"initial_grid\": 2.0}}",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "json",
        "default_value": "{}",
        "validation_rules": {
            "type": "object",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "INITIAL_PRINCIPAL",
        "display_name": "初始本金",
        "description": "初始本金（USDT），设置为0时自动检测账户总资产",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "number",
        "default_value": "0",
        "validation_rules": {
            "type": "float",
            "min": 0
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "GRID_PARAMS_JSON",
        "display_name": "网格参数配置",
        "description": "网格策略参数（JSON），包含 initial/min/max 和波动率映射",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "json",
        "default_value": "{\"initial\": 2.0, \"min\": 1.0, \"max\": 4.0}",
        "validation_rules": {
            "type": "object",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "GRID_CONTINUOUS_PARAMS_JSON",
        "display_name": "连续网格调整参数",
        "description": "连续网格调整参数（JSON），base_grid/center_volatility/sensitivity_k",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "json",
        "default_value": "{\"base_grid\": 2.5, \"center_volatility\": 0.25, \"sensitivity_k\": 10.0}",
        "validation_rules": {
            "type": "object",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "DYNAMIC_INTERVAL_PARAMS_JSON",
        "display_name": "动态时间间隔参数",
        "description": "根据波动率调整交易间隔（JSON），波动率越高交易频率越高",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "json",
        "default_value": "{\"default_interval_hours\": 1.0, \"volatility_to_interval_hours\": [{\"range\": [0, 0.10], \"interval_hours\": 1.0}, {\"range\": [0.10, 0.20], \"interval_hours\": 0.5}, {\"range\": [0.20, 0.30], \"interval_hours\": 0.25}, {\"range\": [0.30, 999], \"interval_hours\": 0.125}]}",
        "validation_rules": {
            "type": "object",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "ENABLE_VOLUME_WEIGHTING",
        "display_name": "启用成交量加权",
        "description": "是否根据成交量调整交易决策权重",
        "config_type": ConfigTypeEnum.TRADING,
        "data_type": "boolean",
        "default_value": "true",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
]


# ============================================================================
# 风控配置 (RISK)
# ============================================================================
RISK_CONFIGS: List[ConfigDefinition] = [
    {
        "config_key": "MAX_POSITION_RATIO",
        "display_name": "最大仓位比例",
        "description": "全局最大仓位比例（0-1之间的小数）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "0.9",
        "validation_rules": {
            "type": "float",
            "min": 0.5,
            "max": 1.0
        },
        "is_required": True,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "MIN_POSITION_RATIO",
        "display_name": "最小仓位比例",
        "description": "全局最小仓位比例（底仓保护，0-1之间的小数）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "0.1",
        "validation_rules": {
            "type": "float",
            "min": 0.0,
            "max": 0.5
        },
        "is_required": True,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "POSITION_LIMITS_JSON",
        "display_name": "交易对仓位限制",
        "description": "为不同交易对设置不同的仓位上下限（JSON格式），如: {\"BNB/USDT\": {\"min\": 0.20, \"max\": 0.80}}",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "json",
        "default_value": "{}",
        "validation_rules": {
            "type": "object",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "ENABLE_STOP_LOSS",
        "display_name": "启用止损机制",
        "description": "是否启用止损机制（价格止损和回撤止盈）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "boolean",
        "default_value": "false",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "STOP_LOSS_PERCENTAGE",
        "display_name": "价格止损比例",
        "description": "价格止损比例（百分比），当价格下跌超过此比例时触发止损",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "15.0",
        "validation_rules": {
            "type": "float",
            "min": 0,
            "max": 50
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "TAKE_PROFIT_DRAWDOWN",
        "display_name": "回撤止盈比例",
        "description": "回撤止盈比例（百分比），当盈利从最高点回撤超过此比例时触发止盈",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "20.0",
        "validation_rules": {
            "type": "float",
            "min": 0,
            "max": 100
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "ALLOCATION_STRATEGY",
        "display_name": "资金分配策略",
        "description": "全局资金分配策略：equal(均分)/weighted(加权)/dynamic(动态)",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "string",
        "default_value": "equal",
        "validation_rules": {
            "enum": ["equal", "weighted", "dynamic"]
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "GLOBAL_MAX_USAGE",
        "display_name": "全局最大资金使用率",
        "description": "全局最大资金使用率（0-1之间的小数）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "0.95",
        "validation_rules": {
            "type": "float",
            "min": 0.5,
            "max": 1.0
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "ALLOCATION_WEIGHTS",
        "display_name": "资金分配权重",
        "description": "加权分配策略的权重配置（JSON），仅当strategy=weighted时使用",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "json",
        "default_value": "{}",
        "validation_rules": {
            "type": "object",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "REBALANCE_INTERVAL",
        "display_name": "重新平衡间隔",
        "description": "动态重新平衡间隔（秒），默认1小时",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "3600",
        "validation_rules": {
            "type": "integer",
            "min": 300,
            "max": 86400
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
]


# ============================================================================
# 趋势识别配置 (RISK - 也是风控的一部分)
# ============================================================================
TREND_CONFIGS: List[ConfigDefinition] = [
    {
        "config_key": "ENABLE_TREND_DETECTION",
        "display_name": "启用趋势识别",
        "description": "是否启用趋势识别功能，根据市场趋势自动调整交易策略",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "boolean",
        "default_value": "true",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "TREND_EMA_SHORT",
        "display_name": "EMA短周期",
        "description": "EMA短周期参数，用于快速捕捉价格变化（建议: 10-30）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "20",
        "validation_rules": {
            "type": "integer",
            "min": 5,
            "max": 200
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "TREND_EMA_LONG",
        "display_name": "EMA长周期",
        "description": "EMA长周期参数，用于判断长期趋势（建议: 30-100）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "50",
        "validation_rules": {
            "type": "integer",
            "min": 5,
            "max": 200
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "TREND_ADX_PERIOD",
        "display_name": "ADX计算周期",
        "description": "ADX计算周期，用于衡量趋势强度（标准值: 14）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "14",
        "validation_rules": {
            "type": "integer",
            "min": 7,
            "max": 30
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "TREND_STRONG_THRESHOLD",
        "display_name": "强趋势阈值",
        "description": "强趋势阈值（0-100），超过此值认为是强趋势（建议: 50-70）",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "60.0",
        "validation_rules": {
            "type": "float",
            "min": 0,
            "max": 100
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "TREND_DETECTION_INTERVAL",
        "display_name": "趋势检测间隔",
        "description": "趋势检测间隔（秒），建议300-600秒",
        "config_type": ConfigTypeEnum.RISK,
        "data_type": "number",
        "default_value": "300",
        "validation_rules": {
            "type": "integer",
            "min": 60,
            "max": 3600
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
]


# ============================================================================
# AI策略配置 (AI)
# ============================================================================
AI_CONFIGS: List[ConfigDefinition] = [
    {
        "config_key": "AI_ENABLED",
        "display_name": "启用AI辅助",
        "description": "是否启用AI辅助交易决策",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "boolean",
        "default_value": "false",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "AI_PROVIDER",
        "display_name": "AI提供商",
        "description": "AI服务提供商：openai 或 anthropic",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "string",
        "default_value": "openai",
        "validation_rules": {
            "enum": ["openai", "anthropic"]
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "AI_MODEL",
        "display_name": "AI模型",
        "description": "使用的AI模型名称（如 gpt-4-turbo, claude-3-opus-20240229）",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "string",
        "default_value": "gpt-4-turbo",
        "validation_rules": {
            "type": "string"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "AI_OPENAI_BASE_URL",
        "display_name": "OpenAI Base URL",
        "description": "OpenAI自定义Base URL（可选，用于第三方API）",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "string",
        "default_value": "",
        "validation_rules": {
            "type": "string",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "AI_CONFIDENCE_THRESHOLD",
        "display_name": "AI置信度阈值",
        "description": "AI置信度阈值（0-100），低于此值不采用AI建议",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "number",
        "default_value": "70",
        "validation_rules": {
            "type": "integer",
            "min": 0,
            "max": 100
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "AI_TRIGGER_INTERVAL",
        "display_name": "AI触发间隔",
        "description": "AI分析触发间隔（秒），建议900秒（15分钟）",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "number",
        "default_value": "900",
        "validation_rules": {
            "type": "integer",
            "min": 60,
            "max": 3600
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "AI_MAX_CALLS_PER_DAY",
        "display_name": "每日最大AI调用次数",
        "description": "每日最大AI调用次数限制，防止费用过高",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "number",
        "default_value": "100",
        "validation_rules": {
            "type": "integer",
            "min": 1,
            "max": 1000
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "AI_FALLBACK_TO_GRID",
        "display_name": "AI失败时回退到网格",
        "description": "AI分析失败时是否自动回退到网格策略",
        "config_type": ConfigTypeEnum.AI,
        "data_type": "boolean",
        "default_value": "true",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
]


# ============================================================================
# 通知配置 (NOTIFICATION)
# ============================================================================
NOTIFICATION_CONFIGS: List[ConfigDefinition] = [
    {
        "config_key": "TELEGRAM_BOT_TOKEN",
        "display_name": "Telegram Bot Token",
        "description": "Telegram机器人Token（可选）",
        "config_type": ConfigTypeEnum.NOTIFICATION,
        "data_type": "string",
        "default_value": "",
        "validation_rules": {
            "type": "string",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": True,
        "requires_restart": False,
    },
    {
        "config_key": "TELEGRAM_CHAT_ID",
        "display_name": "Telegram Chat ID",
        "description": "Telegram聊天ID（可选）",
        "config_type": ConfigTypeEnum.NOTIFICATION,
        "data_type": "string",
        "default_value": "",
        "validation_rules": {
            "type": "string",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "PUSHPLUS_TOKEN",
        "display_name": "PushPlus Token",
        "description": "PushPlus通知Token（可选）",
        "config_type": ConfigTypeEnum.NOTIFICATION,
        "data_type": "string",
        "default_value": "",
        "validation_rules": {
            "type": "string",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": True,
        "requires_restart": False,
    },
    {
        "config_key": "WEBHOOK_URL",
        "display_name": "Webhook URL",
        "description": "Webhook通知URL（可选）",
        "config_type": ConfigTypeEnum.NOTIFICATION,
        "data_type": "string",
        "default_value": "",
        "validation_rules": {
            "type": "string",
            "pattern": r"^https?://.*",
            "optional": True
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
]


# ============================================================================
# 系统配置 (SYSTEM)
# ============================================================================
SYSTEM_CONFIGS: List[ConfigDefinition] = [
    {
        "config_key": "LOG_LEVEL",
        "display_name": "日志级别",
        "description": "系统日志级别：DEBUG/INFO/WARNING/ERROR/CRITICAL",
        "config_type": ConfigTypeEnum.SYSTEM,
        "data_type": "string",
        "default_value": "INFO",
        "validation_rules": {
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
    {
        "config_key": "DEBUG_MODE",
        "display_name": "调试模式",
        "description": "是否启用调试模式（会输出详细日志）",
        "config_type": ConfigTypeEnum.SYSTEM,
        "data_type": "boolean",
        "default_value": "false",
        "validation_rules": {
            "type": "boolean"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": True,
    },
    {
        "config_key": "SAVINGS_PRECISIONS",
        "display_name": "理财精度配置",
        "description": "不同资产的理财操作精度（JSON），如: {\"USDT\": 2, \"BNB\": 6}",
        "config_type": ConfigTypeEnum.SYSTEM,
        "data_type": "json",
        "default_value": "{\"USDT\": 2, \"BNB\": 6, \"DEFAULT\": 8}",
        "validation_rules": {
            "type": "object"
        },
        "is_required": False,
        "is_sensitive": False,
        "requires_restart": False,
    },
]


# ============================================================================
# 汇总所有配置
# ============================================================================
ALL_CONFIGS: List[ConfigDefinition] = (
    EXCHANGE_CONFIGS +
    TRADING_CONFIGS +
    RISK_CONFIGS +
    TREND_CONFIGS +
    AI_CONFIGS +
    NOTIFICATION_CONFIGS +
    SYSTEM_CONFIGS
)


def get_config_by_key(config_key: str) -> ConfigDefinition:
    """根据配置键获取配置定义"""
    for config in ALL_CONFIGS:
        if config['config_key'] == config_key:
            return config
    raise ValueError(f"配置键不存在: {config_key}")


def get_configs_by_type(config_type: ConfigTypeEnum) -> List[ConfigDefinition]:
    """根据配置类型获取配置列表"""
    return [config for config in ALL_CONFIGS if config['config_type'] == config_type]
