"""
交易所模块工具函数和自定义异常

提供：
- 自定义异常类
- 通用工具函数
- 错误处理辅助

作者: GridBNB Team
版本: 1.0.0
"""


# ============================================================================
# 自定义异常
# ============================================================================

class ExchangeError(Exception):
    """交易所基础异常类"""

    def __init__(self, message: str, exchange_name: str = None, code: str = None):
        self.message = message
        self.exchange_name = exchange_name
        self.code = code
        super().__init__(self.message)

    def __str__(self):
        parts = [f"ExchangeError: {self.message}"]
        if self.exchange_name:
            parts.append(f"Exchange: {self.exchange_name}")
        if self.code:
            parts.append(f"Code: {self.code}")
        return ' | '.join(parts)


class InsufficientFundsError(ExchangeError):
    """资金不足异常"""

    def __init__(self, message: str = "资金不足", **kwargs):
        super().__init__(message, **kwargs)


class NetworkError(ExchangeError):
    """网络错误异常"""

    def __init__(self, message: str = "网络连接失败", **kwargs):
        super().__init__(message, **kwargs)


class InvalidOrderError(ExchangeError):
    """无效订单异常"""

    def __init__(self, message: str = "订单参数无效", **kwargs):
        super().__init__(message, **kwargs)


class RateLimitError(ExchangeError):
    """API限流异常"""

    def __init__(self, message: str = "API请求频率超限", **kwargs):
        super().__init__(message, **kwargs)


class AuthenticationError(ExchangeError):
    """认证失败异常"""

    def __init__(self, message: str = "API密钥认证失败", **kwargs):
        super().__init__(message, **kwargs)


# ============================================================================
# 工具函数
# ============================================================================

def safe_float(value, default: float = 0.0) -> float:
    """
    安全地将值转换为浮点数

    Args:
        value: 待转换的值
        default: 转换失败时的默认值

    Returns:
        float: 转换后的浮点数
    """
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """
    安全地将值转换为整数

    Args:
        value: 待转换的值
        default: 转换失败时的默认值

    Returns:
        int: 转换后的整数
    """
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def format_amount(amount: float, precision: int = 8) -> str:
    """
    格式化金额，去除末尾无意义的零

    Args:
        amount: 金额
        precision: 精度

    Returns:
        str: 格式化后的字符串

    Example:
        >>> format_amount(1.00000000, 8)
        '1'
        >>> format_amount(1.23000000, 8)
        '1.23'
    """
    formatted = f"{amount:.{precision}f}"
    # 去除末尾的零和小数点
    return formatted.rstrip('0').rstrip('.')


def validate_symbol(symbol: str) -> bool:
    """
    验证交易对符号格式

    Args:
        symbol: 交易对符号

    Returns:
        bool: 格式是否正确

    Example:
        >>> validate_symbol('BNB/USDT')
        True
        >>> validate_symbol('BNBUSDT')
        False
    """
    return '/' in symbol and len(symbol.split('/')) == 2


def parse_symbol(symbol: str) -> tuple:
    """
    解析交易对符号

    Args:
        symbol: 交易对符号，例如 'BNB/USDT'

    Returns:
        tuple: (base_asset, quote_asset)

    Raises:
        ValueError: 格式不正确时

    Example:
        >>> parse_symbol('BNB/USDT')
        ('BNB', 'USDT')
    """
    if not validate_symbol(symbol):
        raise ValueError(f"无效的交易对格式: {symbol}，应为 'BASE/QUOTE' 格式")

    base, quote = symbol.split('/')
    return base.strip(), quote.strip()


def normalize_precision(precision_value) -> int:
    """
    标准化精度值

    不同交易所返回的精度格式可能不同：
    - 有的返回小数位数（例如 8）
    - 有的返回最小步长（例如 0.00000001）

    Args:
        precision_value: 原始精度值

    Returns:
        int: 标准化的小数位数

    Example:
        >>> normalize_precision(8)
        8
        >>> normalize_precision(0.01)
        2
        >>> normalize_precision(0.00000001)
        8
    """
    if isinstance(precision_value, int):
        return precision_value

    if isinstance(precision_value, float):
        # 计算小数位数
        if precision_value >= 1:
            return 0
        # 将步长转换为小数位数
        precision_str = f"{precision_value:.10f}"
        decimal_part = precision_str.split('.')[1] if '.' in precision_str else ''
        # 去除末尾的零
        decimal_part = decimal_part.rstrip('0')
        return len(decimal_part)

    # 默认返回8位精度
    return 8


def build_order_params(
    symbol: str,
    type: str,
    side: str,
    amount: float,
    price: float = None,
    time_in_force: str = None,
    client_order_id: str = None
) -> dict:
    """
    构建标准订单参数

    Args:
        symbol: 交易对符号
        type: 订单类型 ('limit', 'market')
        side: 交易方向 ('buy', 'sell')
        amount: 数量
        price: 价格（市价单可选）
        time_in_force: 有效期类型（GTC, IOC, FOK）
        client_order_id: 客户端订单ID

    Returns:
        dict: 订单参数字典
    """
    params = {
        'symbol': symbol,
        'type': type,
        'side': side,
        'amount': amount,
    }

    if price is not None:
        params['price'] = price

    if time_in_force:
        params['timeInForce'] = time_in_force

    if client_order_id:
        params['clientOrderId'] = client_order_id

    return params
