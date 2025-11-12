import os
from dotenv import load_dotenv
import logging
import json
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Union
from pydantic import field_validator, ConfigDict

load_dotenv()

class Settings(BaseSettings):
    """应用程序设置类，使用Pydantic进行类型验证和环境变量管理"""

    # --- 交易所选择配置 (企业级多交易所支持) ---
    EXCHANGE: str = "binance"  # 选择交易所: binance, okx

    # --- 测试网/模拟盘配置 ---
    TESTNET_MODE: bool = False  # 是否使用测试网（模拟盘）

    # --- 从 .env 文件读取的必需配置 ---
    # Binance API（实盘）
    BINANCE_API_KEY: str = ""  # 添加默认值以便测试
    BINANCE_API_SECRET: str = ""  # 添加默认值以便测试

    # Binance 测试网 API（可选，仅在 TESTNET_MODE=true 时使用）
    BINANCE_TESTNET_API_KEY: str = ""
    BINANCE_TESTNET_API_SECRET: str = ""

    # OKX API（实盘，如果使用OKX）
    OKX_API_KEY: str = ""
    OKX_API_SECRET: str = ""
    OKX_PASSPHRASE: str = ""  # OKX特有参数

    # OKX 测试网 API（可选，仅在 TESTNET_MODE=true 时使用）
    OKX_TESTNET_API_KEY: str = ""
    OKX_TESTNET_API_SECRET: str = ""
    OKX_TESTNET_PASSPHRASE: str = ""

    # --- 策略核心配置 (从 .env 读取) ---
    SYMBOLS: str = "BNB/USDT"  # 从 .env 读取交易对列表字符串

    # 按交易对设置的初始参数 (JSON格式)
    INITIAL_PARAMS_JSON: Dict[str, Dict[str, float]] = {}

    INITIAL_GRID: float = 2.0  # 全局默认网格大小
    MIN_TRADE_AMOUNT: float = 20.0

    # --- 初始状态设置 (从 .env 读取) ---
    INITIAL_PRINCIPAL: float = 0.0

    # --- 🆕 全局资金分配器配置 (从 .env 读取) ---
    ALLOCATION_STRATEGY: str = "equal"  # 分配策略: equal / weighted / dynamic
    GLOBAL_MAX_USAGE: float = 0.95  # 全局最大资金使用率 (0-1之间)
    ALLOCATION_WEIGHTS: Dict[str, float] = {}  # 权重配置（仅当strategy=weighted时使用）
    REBALANCE_INTERVAL: int = 3600  # 动态重新平衡间隔（秒），默认1小时

    # --- 可选配置 (从 .env 读取) ---
    PUSHPLUS_TOKEN: Optional[str] = None

    # --- 新增：告警系统配置 (阶段3优化) ---
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    WEBHOOK_URL: Optional[str] = None

    # 理财功能开关
    ENABLE_SAVINGS_FUNCTION: bool = True

    WEB_USER: Optional[str] = None
    WEB_PASSWORD: Optional[str] = None
    HTTP_PROXY: Optional[str] = None

    # --- 理财精度配置 (从JSON字符串解析) ---
    SAVINGS_PRECISIONS: Dict[str, int] = {'USDT': 2, 'BNB': 6, 'DEFAULT': 8}

    # --- 新增：从 .env 读取的高级策略配置 ---
    GRID_PARAMS_JSON: Dict = {}
    GRID_CONTINUOUS_PARAMS_JSON: Dict = {}
    DYNAMIC_INTERVAL_PARAMS_JSON: Dict = {}
    ENABLE_VOLUME_WEIGHTING: bool = True

    # --- AI辅助交易配置 ---
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "openai"  # openai / anthropic
    AI_MODEL: str = "gpt-4-turbo"
    AI_API_KEY: Optional[str] = None
    AI_OPENAI_BASE_URL: Optional[str] = None
    AI_CONFIDENCE_THRESHOLD: int = 70
    AI_TRIGGER_INTERVAL: int = 900  # 秒 (15分钟)
    AI_MAX_CALLS_PER_DAY: int = 100
    AI_FALLBACK_TO_GRID: bool = True

    # --- 止损配置 ---
    ENABLE_STOP_LOSS: bool = False  # 默认禁用，需要用户主动启用
    STOP_LOSS_PERCENTAGE: float = 15.0  # 价格止损比例 (%)
    TAKE_PROFIT_DRAWDOWN: float = 20.0  # 回撤止盈比例 (%)

    # --- 趋势识别配置 🆕 ---
    ENABLE_TREND_DETECTION: bool = True  # 默认启用趋势识别
    TREND_EMA_SHORT: int = 20  # EMA短周期
    TREND_EMA_LONG: int = 50  # EMA长周期
    TREND_ADX_PERIOD: int = 14  # ADX计算周期
    TREND_STRONG_THRESHOLD: float = 60.0  # 强趋势阈值
    TREND_DETECTION_INTERVAL: int = 300  # 趋势检测间隔（秒）

    # --- 交易对特定仓位限制配置 🆕 (Issue #51) ---
    POSITION_LIMITS_JSON: Dict[str, Dict[str, float]] = {}  # 每个交易对的仓位限制

    @field_validator('INITIAL_PARAMS_JSON', mode='before')
    @classmethod
    def parse_initial_params(cls, value):
        """解析按交易对设置的初始参数JSON字符串"""
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("INITIAL_PARAMS_JSON 格式无效，必须是合法的JSON字符串。")
        return value if value else {}  # 如果为空，返回空字典

    @field_validator('ALLOCATION_WEIGHTS', mode='before')
    @classmethod
    def parse_allocation_weights(cls, value):
        """解析权重配置JSON字符串"""
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("ALLOCATION_WEIGHTS 格式无效，必须是合法的JSON字符串。")
        return value if value else {}

    @field_validator('GRID_PARAMS_JSON', 'GRID_CONTINUOUS_PARAMS_JSON', 'DYNAMIC_INTERVAL_PARAMS_JSON', mode='before')
    @classmethod
    def parse_strategy_params_json(cls, value):
        """通用验证器，用于将策略相关的JSON字符串解析为字典"""
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"策略参数格式无效，必须是合法的JSON字符串。收到的值: {value}")
        return value if value else {}

    @field_validator('SAVINGS_PRECISIONS', mode='before')
    @classmethod
    def parse_savings_precisions(cls, value):
        """自定义验证器，用于将JSON字符串解析为字典"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("SAVINGS_PRECISIONS 格式无效，必须是合法的JSON字符串。")
        return value

    @field_validator('POSITION_LIMITS_JSON', mode='before')
    @classmethod
    def parse_position_limits(cls, value):
        """解析交易对特定仓位限制JSON字符串"""
        if isinstance(value, str) and value:
            try:
                parsed = json.loads(value)
                # 验证每个交易对配置的格式
                for symbol, limits in parsed.items():
                    # 验证必需字段
                    if 'min' not in limits or 'max' not in limits:
                        raise ValueError(
                            f"交易对 {symbol} 的仓位限制必须包含 'min' 和 'max' 字段。"
                            f"示例: {{\"BNB/USDT\": {{\"min\": 0.20, \"max\": 0.80}}}}"
                        )

                    min_ratio = float(limits['min'])
                    max_ratio = float(limits['max'])

                    # 验证逻辑关系
                    if min_ratio >= max_ratio:
                        raise ValueError(
                            f"交易对 {symbol} 的最小仓位({min_ratio})不能大于等于最大仓位({max_ratio})"
                        )

                    # 验证数值范围
                    if min_ratio < 0 or min_ratio > 1:
                        raise ValueError(
                            f"交易对 {symbol} 的最小仓位({min_ratio})必须在 0-1 之间"
                        )
                    if max_ratio < 0 or max_ratio > 1:
                        raise ValueError(
                            f"交易对 {symbol} 的最大仓位({max_ratio})必须在 0-1 之间"
                        )

                    # 警告：配置过于极端
                    if min_ratio > 0.5:
                        logging.warning(
                            f"交易对 {symbol} 的最小仓位设置过高({min_ratio:.1%})，"
                            f"可能限制灵活性"
                        )
                    if max_ratio < 0.3:
                        logging.warning(
                            f"交易对 {symbol} 的最大仓位设置过低({max_ratio:.1%})，"
                            f"可能限制盈利空间"
                        )

                return parsed
            except json.JSONDecodeError:
                raise ValueError(
                    "POSITION_LIMITS_JSON 格式无效，必须是合法的JSON字符串。"
                    "示例: {\"BNB/USDT\": {\"min\": 0.20, \"max\": 0.80}}"
                )
        return value if value else {}

    # --- 新增验证器：增强环境变量验证 ---

    @field_validator('BINANCE_API_KEY')
    @classmethod
    def validate_api_key(cls, v, info):
        """验证 Binance API Key 格式（仅当使用 Binance 交易所时）"""
        # 测试环境下允许空值
        if os.getenv('PYTEST_CURRENT_TEST'):
            return v

        # 从环境变量直接读取交易所配置（避免依赖字段验证顺序）
        exchange = os.getenv('EXCHANGE', 'binance').lower()

        # 只在使用 Binance 交易所时进行验证
        if exchange == 'binance':
            if not v:
                raise ValueError("BINANCE_API_KEY 不能为空（当前使用 Binance 交易所）")
            if len(v) < 64:
                raise ValueError(f"BINANCE_API_KEY 格式无效: 长度应至少64位，当前 {len(v)} 位")

        return v

    @field_validator('BINANCE_API_SECRET')
    @classmethod
    def validate_api_secret(cls, v, info):
        """验证 Binance API Secret 格式（仅当使用 Binance 交易所时）"""
        # 测试环境下允许空值
        if os.getenv('PYTEST_CURRENT_TEST'):
            return v

        # 从环境变量直接读取交易所配置（避免依赖字段验证顺序）
        exchange = os.getenv('EXCHANGE', 'binance').lower()

        # 只在使用 Binance 交易所时进行验证
        if exchange == 'binance':
            if not v:
                raise ValueError("BINANCE_API_SECRET 不能为空（当前使用 Binance 交易所）")
            if len(v) < 64:
                raise ValueError(f"BINANCE_API_SECRET 格式无效: 长度应至少64位，当前 {len(v)} 位")

        return v

    @field_validator('OKX_API_KEY')
    @classmethod
    def validate_okx_api_key(cls, v, info):
        """验证 OKX API Key 格式（仅当使用 OKX 交易所时）"""
        # 测试环境下允许空值
        if os.getenv('PYTEST_CURRENT_TEST'):
            return v

        # 从环境变量直接读取交易所配置（避免依赖字段验证顺序）
        exchange = os.getenv('EXCHANGE', 'binance').lower()

        # 只在使用 OKX 交易所时进行验证
        if exchange == 'okx':
            if not v:
                raise ValueError("OKX_API_KEY 不能为空（当前使用 OKX 交易所）")
            if len(v) < 32:
                raise ValueError(f"OKX_API_KEY 格式无效: 长度应至少32位，当前 {len(v)} 位")

        return v

    @field_validator('OKX_API_SECRET')
    @classmethod
    def validate_okx_api_secret(cls, v, info):
        """验证 OKX API Secret 格式（仅当使用 OKX 交易所时）"""
        # 测试环境下允许空值
        if os.getenv('PYTEST_CURRENT_TEST'):
            return v

        # 从环境变量直接读取交易所配置（避免依赖字段验证顺序）
        exchange = os.getenv('EXCHANGE', 'binance').lower()

        # 只在使用 OKX 交易所时进行验证
        if exchange == 'okx':
            if not v:
                raise ValueError("OKX_API_SECRET 不能为空（当前使用 OKX 交易所）")
            if len(v) < 32:
                raise ValueError(f"OKX_API_SECRET 格式无效: 长度应至少32位，当前 {len(v)} 位")

        return v

    @field_validator('OKX_PASSPHRASE')
    @classmethod
    def validate_okx_passphrase(cls, v, info):
        """验证 OKX Passphrase（仅当使用 OKX 交易所时）"""
        # 测试环境下允许空值
        if os.getenv('PYTEST_CURRENT_TEST'):
            return v

        # 从环境变量直接读取交易所配置（避免依赖字段验证顺序）
        exchange = os.getenv('EXCHANGE', 'binance').lower()

        # 只在使用 OKX 交易所时进行验证
        if exchange == 'okx':
            if not v:
                raise ValueError("OKX_PASSPHRASE 不能为空（当前使用 OKX 交易所）")

        return v

    @field_validator('MIN_TRADE_AMOUNT')
    @classmethod
    def validate_min_trade_amount(cls, v):
        """验证最小交易金额"""
        if v < 10:
            raise ValueError(f"MIN_TRADE_AMOUNT 必须 >= 10 USDT (Binance 最小限制)，当前设置为 {v}")
        if v > 10000:
            logging.warning(f"MIN_TRADE_AMOUNT 设置过高 ({v} USDT)，建议在 10-1000 之间")
        return v

    @field_validator('INITIAL_GRID')
    @classmethod
    def validate_initial_grid(cls, v):
        """验证初始网格大小"""
        if v < 0.1 or v > 10:
            raise ValueError(f"INITIAL_GRID 必须在 0.1-10% 之间，当前设置为 {v}%")
        if v < 1.0:
            logging.warning(f"INITIAL_GRID 设置过小 ({v}%)，可能导致频繁交易和高手续费")
        return v

    @field_validator('SYMBOLS')
    @classmethod
    def validate_symbols(cls, v):
        """验证交易对列表格式"""
        if not v:
            raise ValueError("SYMBOLS 不能为空")
        symbols = [s.strip() for s in v.split(',')]
        for symbol in symbols:
            if '/' not in symbol:
                raise ValueError(f"交易对格式无效: {symbol}，应为 'BASE/QUOTE' 格式 (如 BNB/USDT)")
            base, quote = symbol.split('/')
            if not base or not quote:
                raise ValueError(f"交易对格式无效: {symbol}")
        return v

    @field_validator('INITIAL_PRINCIPAL')
    @classmethod
    def validate_initial_principal(cls, v):
        """验证初始本金（允许0表示自动检测）"""
        if v < 0:
            raise ValueError(f"INITIAL_PRINCIPAL 不能为负数，当前设置为 {v}")
        if v == 0:
            logging.info("INITIAL_PRINCIPAL 设置为0，将在运行时自动检测账户总资产")
        elif v > 0 and v < 100:
            logging.warning(f"INITIAL_PRINCIPAL 设置过小 ({v} USDT)，建议至少 500 USDT")
        return v

    @field_validator('AI_PROVIDER')
    @classmethod
    def validate_ai_provider(cls, v):
        """验证AI提供商"""
        valid_providers = ['openai', 'anthropic']
        if v not in valid_providers:
            raise ValueError(f"AI_PROVIDER 必须是 {valid_providers} 之一，当前设置为 {v}")
        return v

    @field_validator('AI_CONFIDENCE_THRESHOLD')
    @classmethod
    def validate_ai_confidence(cls, v):
        """验证AI置信度阈值"""
        if v < 0 or v > 100:
            raise ValueError(f"AI_CONFIDENCE_THRESHOLD 必须在 0-100 之间，当前设置为 {v}")
        if v < 50:
            logging.warning(f"AI_CONFIDENCE_THRESHOLD 设置过低 ({v}%)，建议至少50%")
        return v

    @field_validator('AI_TRIGGER_INTERVAL')
    @classmethod
    def validate_ai_trigger_interval(cls, v):
        """验证AI触发间隔"""
        if v < 60:
            raise ValueError(f"AI_TRIGGER_INTERVAL 不能小于60秒，当前设置为 {v}")
        if v < 300:
            logging.warning(f"AI_TRIGGER_INTERVAL 设置过短 ({v}秒)，可能导致频繁调用AI")
        return v

    @field_validator('AI_MAX_CALLS_PER_DAY')
    @classmethod
    def validate_ai_max_calls(cls, v):
        """验证每日最大AI调用次数"""
        if v < 1:
            raise ValueError(f"AI_MAX_CALLS_PER_DAY 必须至少为1，当前设置为 {v}")
        if v > 500:
            logging.warning(f"AI_MAX_CALLS_PER_DAY 设置过高 ({v})，可能产生高额费用")
        return v

    # --- 🆕 全局资金分配器验证器 ---

    @field_validator('ALLOCATION_STRATEGY')
    @classmethod
    def validate_allocation_strategy(cls, v):
        """验证资金分配策略"""
        valid_strategies = ['equal', 'weighted', 'dynamic']
        if v not in valid_strategies:
            raise ValueError(f"ALLOCATION_STRATEGY 必须是 {valid_strategies} 之一，当前设置为 {v}")
        return v

    @field_validator('GLOBAL_MAX_USAGE')
    @classmethod
    def validate_global_max_usage(cls, v):
        """验证全局最大资金使用率"""
        if v < 0.5 or v > 1.0:
            raise ValueError(f"GLOBAL_MAX_USAGE 必须在 0.5-1.0 之间，当前设置为 {v}")
        if v < 0.8:
            logging.warning(f"GLOBAL_MAX_USAGE 设置过低 ({v:.1%})，可能导致资金利用率不足")
        return v

    @field_validator('REBALANCE_INTERVAL')
    @classmethod
    def validate_rebalance_interval(cls, v):
        """验证重新平衡间隔"""
        if v < 300:
            raise ValueError(f"REBALANCE_INTERVAL 不能小于300秒（5分钟），当前设置为 {v}")
        if v < 1800:
            logging.warning(f"REBALANCE_INTERVAL 设置过短 ({v}秒)，可能导致频繁重新平衡")
        return v

    # --- 🆕 止损配置验证器 ---

    @field_validator('STOP_LOSS_PERCENTAGE')
    @classmethod
    def validate_stop_loss_percentage(cls, v):
        """验证价格止损比例"""
        if v < 0 or v > 50:
            raise ValueError(f"STOP_LOSS_PERCENTAGE 必须在 0-50 之间，当前设置为 {v}")
        if v > 0 and v < 5:
            logging.warning(f"STOP_LOSS_PERCENTAGE 设置过小 ({v}%)，可能频繁触发止损")
        return v

    @field_validator('TAKE_PROFIT_DRAWDOWN')
    @classmethod
    def validate_take_profit_drawdown(cls, v):
        """验证回撤止盈比例"""
        if v < 0 or v > 100:
            raise ValueError(f"TAKE_PROFIT_DRAWDOWN 必须在 0-100 之间，当前设置为 {v}")
        if v > 0 and v < 10:
            logging.warning(f"TAKE_PROFIT_DRAWDOWN 设置过小 ({v}%)，可能过于敏感")
        return v

    # --- 🆕 趋势识别配置验证器 ---

    @field_validator('TREND_EMA_SHORT', 'TREND_EMA_LONG')
    @classmethod
    def validate_ema_periods(cls, v, info):
        """验证EMA周期"""
        field_name = info.field_name
        if v < 5 or v > 200:
            raise ValueError(f"{field_name} 必须在 5-200 之间，当前设置为 {v}")
        return v

    @field_validator('TREND_STRONG_THRESHOLD')
    @classmethod
    def validate_trend_threshold(cls, v):
        """验证趋势强度阈值"""
        if v < 0 or v > 100:
            raise ValueError(f"TREND_STRONG_THRESHOLD 必须在 0-100 之间，当前设置为 {v}")
        if v < 40:
            logging.warning("TREND_STRONG_THRESHOLD 过低可能导致过度限制交易")
        return v

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        """验证日志级别，支持字符串(INFO/DEBUG等)或整数"""
        if isinstance(v, str):
            # 字符串映射到logging常量
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL
            }
            level = level_map.get(v.upper())
            if level is None:
                raise ValueError(f"LOG_LEVEL 必须是 DEBUG/INFO/WARNING/ERROR/CRITICAL 之一，当前值: {v}")
            return level
        elif isinstance(v, int):
            # 验证整数值是否有效
            valid_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
            if v not in valid_levels:
                raise ValueError(f"LOG_LEVEL 整数值必须是有效的logging级别，当前值: {v}")
            return v
        else:
            raise ValueError(f"LOG_LEVEL 必须是字符串或整数，当前类型: {type(v)}")

    # --- 固定配置 (不常修改，保留在代码中) ---
    MIN_POSITION_PERCENT: float = 0.05
    MAX_POSITION_PERCENT: float = 0.15
    MAX_POSITION_RATIO: float = 0.9
    MIN_POSITION_RATIO: float = 0.1
    COOLDOWN: int = 60
    SAFETY_MARGIN: float = 0.95
    AUTO_ADJUST_BASE_PRICE: bool = False
    PUSHPLUS_TIMEOUT: int = 5
    LOG_LEVEL: Union[int, str] = logging.INFO  # 支持字符串(INFO/DEBUG等)或整数
    DEBUG_MODE: bool = False
    API_TIMEOUT: int = 10000
    RECV_WINDOW: int = 5000
    RISK_CHECK_INTERVAL: int = 300
    MAX_RETRIES: int = 5
    RISK_FACTOR: float = 0.1
    VOLATILITY_WINDOW: int = 52  # 52日窗口
    VOLATILITY_EWMA_LAMBDA: float = 0.94  # EWMA衰减因子 (RiskMetrics标准)
    VOLATILITY_HYBRID_WEIGHT: float = 0.7  # EWMA权重，传统波动率权重为0.3

    # --- 交易限制配置 ---
    MIN_NOTIONAL_VALUE: float = 10.0  # 最小订单名义价值 (quote currency)
    MIN_AMOUNT_LIMIT: float = 0.0001  # 最小交易数量
    MAX_SINGLE_TRANSFER: float = 5000.0  # 单次最大划转金额
    POSITION_SCALE_FACTOR: float = 0.2

    # 常量化魔术数字
    SPOT_FUNDS_TARGET_RATIO: float = 0.16
    MIN_BNB_TRANSFER: float = 0.01

    model_config = ConfigDict(
        env_file="config/.env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'  # 忽略额外的字段
    )

# 创建全局设置实例
settings = Settings()

# 提供一个解析后的列表，方便使用
SYMBOLS_LIST = [s.strip() for s in settings.SYMBOLS.split(',') if s.strip()]

# 保留必要的向后兼容性常量，但建议逐步迁移到 settings.XXX 的形式
FLIP_THRESHOLD = lambda grid_size: (grid_size / 5) / 100  # 网格大小的1/5的1%

class TradingConfig:
    """
    交易配置类，现在只包含从settings派生或转换而来的复杂策略参数。
    简单的配置项直接从全局的 settings 对象获取。

    这个类的职责：
    1. 将JSON格式的策略参数转换为Python字典
    2. 为复杂的策略参数提供默认值
    3. 进行配置验证
    """

    RISK_PARAMS = {
        'position_limit': settings.MAX_POSITION_RATIO
    }

    # 将硬编码的字典替换为从 settings 中获取，如果为空则使用默认值
    GRID_PARAMS = settings.GRID_PARAMS_JSON if settings.GRID_PARAMS_JSON else {
        'initial': settings.INITIAL_GRID,
        'min': 1.0,  # 网格大小的绝对最小值
        'max': 4.0,  # 网格大小的绝对最大值
        'volatility_threshold': {
            'ranges': [
                # --- 更直接、更敏感的波动率-网格映射关系 ---
                {'range': [0, 0.10], 'grid': 1.0},      # 波动率 0% 到 10% (不含)，网格 1.0%
                {'range': [0.10, 0.20], 'grid': 2.0},   # 波动率 10% 到 20% (不含)，网格 2.0%
                {'range': [0.20, 0.30], 'grid': 3.0},   # 波动率 20% 到 30% (不含)，网格 3.0%
                {'range': [0.30, 0.40], 'grid': 4.0},   # 波动率 30% 到 40% (不含)，网格 4.0%
                {'range': [0.40, 999], 'grid': 4.0}     # 波动率 40% 及以上，统一使用最大网格 4.0%
            ]
        }
    }

    # 连续网格调整参数
    GRID_CONTINUOUS_PARAMS = settings.GRID_CONTINUOUS_PARAMS_JSON if settings.GRID_CONTINUOUS_PARAMS_JSON else {
        'base_grid': 2.5,          # 波动率处于中心点时，我们期望的基础网格大小 (例如 2.5%)
        'center_volatility': 0.25, # 我们定义的市场"正常"波动率水平 (例如 0.25 或 25%)
        'sensitivity_k': 10.0      # 灵敏度系数k。k越大，网格对波动率变化的反应越剧烈。
                                   # k=10.0 意味着波动率每变化1%(0.01)，网格大小变化 0.1% (10.0 * 0.01)
    }

    # 成交量加权波动率计算开关
    ENABLE_VOLUME_WEIGHTING = settings.ENABLE_VOLUME_WEIGHTING

    # 动态时间间隔参数（使用配置合并策略）
    # 默认配置
    _DEFAULT_DYNAMIC_INTERVAL_PARAMS = {
        'default_interval_hours': 1.0,  # 默认间隔
        'volatility_to_interval_hours': [
            {'range': [0, 0.10], 'interval_hours': 1.0},      # 波动率 < 10%，每 1 小时检查一次
            {'range': [0.10, 0.20], 'interval_hours': 0.5},   # 波动率 10-20%，每 30 分钟检查一次
            {'range': [0.20, 0.30], 'interval_hours': 0.25},  # 波动率 20-30%，每 15 分钟检查一次
            {'range': [0.30, 999], 'interval_hours': 0.125},  # 波动率 > 30%，每 7.5 分钟检查一次
        ]
    }

    # 合并用户配置（如果有）
    DYNAMIC_INTERVAL_PARAMS = _DEFAULT_DYNAMIC_INTERVAL_PARAMS.copy()
    if settings.DYNAMIC_INTERVAL_PARAMS_JSON:
        DYNAMIC_INTERVAL_PARAMS.update(settings.DYNAMIC_INTERVAL_PARAMS_JSON)

    # 保留的策略相关基础值
    BASE_AMOUNT = 50.0  # 基础交易金额（可调整）

    def __init__(self):
        # 添加配置验证
        if settings.MIN_POSITION_RATIO >= settings.MAX_POSITION_RATIO:
            raise ValueError("底仓比例不能大于或等于最大仓位比例")

        if self.GRID_PARAMS['min'] > self.GRID_PARAMS['max']:
            raise ValueError("网格最小值不能大于最大值")

        # API密钥验证已由Pydantic在settings实例化时自动完成

        # 验证数值范围
        if settings.INITIAL_PRINCIPAL < 0:
            raise ValueError("INITIAL_PRINCIPAL不能为负数")

        # INITIAL_BASE_PRICE已移除，现在使用INITIAL_PARAMS_JSON中的交易对特定配置
        
    # Removed unused update methods (update_risk_params, update_grid_params, 
    # update_symbol, update_initial_base_price, update_risk_check_interval, 
    # update_max_retries, update_risk_factor, update_base_amount, 
    # update_min_trade_amount, update_max_position_ratio, 
    # update_min_position_ratio, update_all)

    # Removed unused validate_config method
# End of class definition 
