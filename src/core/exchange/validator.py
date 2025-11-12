"""
交易所配置验证器

提供完整的配置验证、健康检查和诊断功能。
"""

from typing import Dict, List, Tuple, Optional
import logging
from src.config.settings import settings
from src.core.exchange import ExchangeType, ExchangeFactory


class ExchangeConfigValidator:
    """
    交易所配置验证器

    职责：
    1. 验证配置完整性
    2. 检查API密钥有效性
    3. 执行健康检查
    4. 生成诊断报告
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def validate_config(self) -> Tuple[bool, List[str], List[str]]:
        """
        验证交易所配置

        Returns:
            (是否有效, 错误列表, 警告列表)
        """
        self.issues.clear()
        self.warnings.clear()

        # 1. 验证交易所选择
        exchange_name = settings.EXCHANGE.lower()
        try:
            exchange_type = ExchangeType(exchange_name)
        except ValueError:
            self.issues.append(
                f"❌ 不支持的交易所: {exchange_name}\n"
                f"   支持的交易所: {ExchangeFactory.get_supported_exchanges()}"
            )
            return False, self.issues, self.warnings

        # 2. 验证API密钥
        self._validate_api_credentials(exchange_type)

        # 3. 验证理财功能配置
        self._validate_savings_config(exchange_type)

        # 4. 验证交易对配置
        self._validate_symbols_config()

        is_valid = len(self.issues) == 0
        return is_valid, self.issues, self.warnings

    def _validate_api_credentials(self, exchange_type: ExchangeType) -> None:
        """验证API密钥配置"""
        if exchange_type == ExchangeType.BINANCE:
            if not settings.BINANCE_API_KEY:
                self.issues.append("❌ 缺少 BINANCE_API_KEY 配置")
            if not settings.BINANCE_API_SECRET:
                self.issues.append("❌ 缺少 BINANCE_API_SECRET 配置")

        elif exchange_type == ExchangeType.OKX:
            if not settings.OKX_API_KEY:
                self.issues.append("❌ 缺少 OKX_API_KEY 配置")
            if not settings.OKX_API_SECRET:
                self.issues.append("❌ 缺少 OKX_API_SECRET 配置")
            if not settings.OKX_PASSPHRASE:
                self.issues.append("❌ 缺少 OKX_PASSPHRASE 配置")

    def _validate_savings_config(self, exchange_type: ExchangeType) -> None:
        """验证理财功能配置"""
        if not settings.ENABLE_SAVINGS_FUNCTION:
            self.warnings.append(
                "⚠️  理财功能已禁用 (ENABLE_SAVINGS_FUNCTION=false)\n"
                "   所有资金将保留在现货账户"
            )
            return

        # 币安和OKX都支持理财功能
        if exchange_type in [ExchangeType.BINANCE, ExchangeType.OKX]:
            self.logger.info(f"✅ {exchange_type.value} 支持理财功能")
        else:
            self.warnings.append(
                f"⚠️  {exchange_type.value} 可能不支持理财功能\n"
                f"   建议设置 ENABLE_SAVINGS_FUNCTION=false"
            )

    def _validate_symbols_config(self) -> None:
        """验证交易对配置"""
        symbols_str = settings.SYMBOLS
        if not symbols_str or symbols_str.strip() == "":
            self.issues.append("❌ 未配置交易对 (SYMBOLS 为空)")
            return

        symbols = [s.strip() for s in symbols_str.split(',')]
        if len(symbols) == 0:
            self.issues.append("❌ 交易对列表为空")
            return

        # 验证交易对格式
        for symbol in symbols:
            if '/' not in symbol:
                self.warnings.append(
                    f"⚠️  交易对格式可能不正确: {symbol}\n"
                    f"   标准格式应为: 'BTC/USDT'"
                )

    async def health_check(self) -> Tuple[bool, str]:
        """
        执行健康检查

        Returns:
            (是否健康, 状态描述)
        """
        try:
            exchange_type = ExchangeType(settings.EXCHANGE.lower())
        except ValueError:
            return False, f"不支持的交易所: {settings.EXCHANGE}"

        # 检查是否已有实例
        instance = ExchangeFactory.get_instance(exchange_type)
        if not instance:
            return False, "交易所实例未创建"

        # 执行健康检查
        return await instance.health_check()

    def print_validation_report(
        self,
        is_valid: bool,
        issues: List[str],
        warnings: List[str]
    ) -> None:
        """打印验证报告"""
        print("\n" + "=" * 60)
        print("📋 交易所配置验证报告")
        print("=" * 60)

        print(f"\n🏦 交易所: {settings.EXCHANGE.upper()}")
        print(f"💰 理财功能: {'启用' if settings.ENABLE_SAVINGS_FUNCTION else '禁用'}")
        print(f"📊 交易对: {settings.SYMBOLS}")

        if issues:
            print(f"\n❌ 发现 {len(issues)} 个错误:")
            for issue in issues:
                print(f"  {issue}")

        if warnings:
            print(f"\n⚠️  发现 {len(warnings)} 个警告:")
            for warning in warnings:
                print(f"  {warning}")

        if not issues and not warnings:
            print("\n✅ 配置验证通过，没有发现问题")

        print("\n" + "=" * 60)

        if not is_valid:
            print("❌ 配置无效，请修复上述错误后重试")
        else:
            print("✅ 配置有效，可以启动交易系统")

        print("=" * 60 + "\n")


# ==================== 便捷函数 ====================

async def validate_and_create_exchange():
    """
    验证配置并创建交易所实例

    Returns:
        交易所适配器实例

    Raises:
        ValueError: 配置验证失败
    """
    # 验证配置
    validator = ExchangeConfigValidator()
    is_valid, issues, warnings = validator.validate_config()

    # 打印报告
    validator.print_validation_report(is_valid, issues, warnings)

    if not is_valid:
        raise ValueError("交易所配置验证失败，请检查配置")

    # 创建配置字典
    exchange_name = settings.EXCHANGE.lower()
    config = {'exchange': exchange_name}

    if exchange_name == 'binance':
        config.update({
            'api_key': settings.BINANCE_API_KEY,
            'api_secret': settings.BINANCE_API_SECRET,
        })
    elif exchange_name == 'okx':
        config.update({
            'api_key': settings.OKX_API_KEY,
            'api_secret': settings.OKX_API_SECRET,
            'passphrase': settings.OKX_PASSPHRASE,
        })

    # 创建实例
    from src.core.exchange import create_exchange_from_config
    return await create_exchange_from_config(config)
