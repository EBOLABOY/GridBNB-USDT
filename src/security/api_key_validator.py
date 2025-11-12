"""
API 密钥权限验证模块

提供 Binance API 密钥权限的验证功能,确保密钥具有正确的权限设置。

安全检查项:
1. 密钥是否有效
2. 是否启用了现货交易权限
3. 是否禁用了提现权限
4. 是否启用了 IP 白名单(推荐)
5. 密钥的有效期

使用方法:
from src.security.api_key_validator import APIKeyValidator

    # 初始化验证器
    validator = APIKeyValidator(api_key, api_secret)

    # 验证权限
    is_valid, issues = await validator.validate_permissions()

    if is_valid:
        print("API 密钥权限配置正确")
    else:
        print(f"权限配置问题: {issues}")
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import ccxt.async_support as ccxt


class APIKeyValidator:
    """
    API 密钥权限验证器

    验证 Binance API 密钥的权限配置是否符合安全要求。
    """

    # 安全配置要求
    REQUIRED_PERMISSIONS = {
        "spot": True,  # 必须启用现货交易
        "enableWithdrawals": False,  # 必须禁用提现
        "enableReading": True,  # 必须启用读取
        "enableSpotAndMarginTrading": True,  # 必须启用现货交易
    }

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        初始化验证器

        Args:
            api_key: Binance API Key
            api_secret: Binance API Secret
            testnet: 是否使用测试网
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # 初始化交易所客户端
        self.exchange = ccxt.binance(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )

        if testnet:
            self.exchange.set_sandbox_mode(True)

        self.api_key = api_key
        self.testnet = testnet

    async def validate_permissions(self) -> Tuple[bool, List[str]]:
        """
        验证 API 密钥权限

        Returns:
            Tuple[is_valid, issues]: 验证是否通过和发现的问题列表
        """
        issues = []

        try:
            # 1. 验证密钥是否有效
            is_valid_key = await self._check_key_validity()
            if not is_valid_key:
                issues.append("API 密钥无效或已过期")
                return False, issues

            self.logger.info("✓ API 密钥有效")

            # 2. 检查账户权限
            permissions = await self._get_api_permissions()
            if permissions:
                permission_issues = self._validate_required_permissions(permissions)
                issues.extend(permission_issues)

            # 3. 检查IP限制(可选但推荐)
            ip_restricted = await self._check_ip_restriction()
            if not ip_restricted:
                issues.append("警告: 未启用 IP 白名单,建议启用以提高安全性")

            # 4. 检查密钥有效期
            expiry_issue = await self._check_key_expiry()
            if expiry_issue:
                issues.append(expiry_issue)

            # 5. 检查是否有危险权限
            dangerous_permissions = await self._check_dangerous_permissions()
            if dangerous_permissions:
                issues.extend(dangerous_permissions)

            # 如果只有IP警告,仍然认为是通过的
            critical_issues = [i for i in issues if not i.startswith("警告")]
            is_valid = len(critical_issues) == 0

            if is_valid:
                self.logger.info("✓ API 密钥权限验证通过")
            else:
                self.logger.warning(f"✗ API 密钥权限验证失败: {critical_issues}")

            return is_valid, issues

        except Exception as e:
            self.logger.error(f"验证 API 权限时发生错误: {e}", exc_info=True)
            issues.append(f"验证过程出错: {str(e)}")
            return False, issues

    async def _check_key_validity(self) -> bool:
        """
        检查密钥是否有效

        Returns:
            bool: 密钥是否有效
        """
        try:
            # 尝试获取账户信息
            await self.exchange.fetch_balance()
            return True
        except ccxt.AuthenticationError:
            return False
        except Exception as e:
            self.logger.error(f"检查密钥有效性失败: {e}")
            return False

    async def _get_api_permissions(self) -> Optional[Dict]:
        """
        获取 API 权限配置

        Returns:
            dict: 权限配置,失败返回 None
        """
        try:
            # Binance API: GET /sapi/v1/account/apiRestrictions
            result = await self.exchange.sapi_get_account_apirestrictions()
            return result
        except Exception as e:
            self.logger.error(f"获取 API 权限配置失败: {e}")
            return None

    def _validate_required_permissions(self, permissions: Dict) -> List[str]:
        """
        验证必需的权限配置

        Args:
            permissions: API 权限配置

        Returns:
            List[str]: 发现的问题列表
        """
        issues = []

        # 检查现货交易权限
        if not permissions.get("enableSpotAndMarginTrading", False):
            issues.append("错误: 未启用现货交易权限")

        # 检查提现权限(必须禁用)
        if permissions.get("enableWithdrawals", False):
            issues.append("严重错误: 启用了提现权限,存在安全风险!")

        # 检查读取权限
        if not permissions.get("enableReading", False):
            issues.append("错误: 未启用读取权限")

        # 检查是否限制为现货交易
        trading_authority_expiration_time = permissions.get("tradingAuthorityExpirationTime")
        if trading_authority_expiration_time and trading_authority_expiration_time < 0:
            # -1 表示永久,0 表示禁用
            pass  # 正常情况
        elif trading_authority_expiration_time == 0:
            issues.append("错误: 交易权限已禁用")

        return issues

    async def _check_ip_restriction(self) -> bool:
        """
        检查是否启用了 IP 限制

        Returns:
            bool: 是否启用了 IP 限制
        """
        try:
            permissions = await self._get_api_permissions()
            if not permissions:
                return False

            # 检查 IP 限制
            ip_restrict = permissions.get("ipRestrict", False)
            return ip_restrict

        except Exception as e:
            self.logger.error(f"检查 IP 限制失败: {e}")
            return False

    async def _check_key_expiry(self) -> Optional[str]:
        """
        检查密钥是否即将过期

        Returns:
            Optional[str]: 如果有过期问题则返回警告信息,否则返回 None
        """
        try:
            permissions = await self._get_api_permissions()
            if not permissions:
                return None

            # 检查创建时间和有效期
            # create_time = permissions.get("createTime")  # 预留字段,暂未使用
            trading_expiry = permissions.get("tradingAuthorityExpirationTime")

            if trading_expiry and trading_expiry > 0:
                # 转换为日期
                expiry_date = datetime.fromtimestamp(trading_expiry / 1000)
                now = datetime.now()

                days_until_expiry = (expiry_date - now).days

                if days_until_expiry < 0:
                    return "错误: API 密钥已过期"
                elif days_until_expiry < 30:
                    return f"警告: API 密钥将在 {days_until_expiry} 天后过期"

            return None

        except Exception as e:
            self.logger.error(f"检查密钥过期时间失败: {e}")
            return None

    async def _check_dangerous_permissions(self) -> List[str]:
        """
        检查是否有危险的权限配置

        Returns:
            List[str]: 危险权限列表
        """
        issues = []

        try:
            permissions = await self._get_api_permissions()
            if not permissions:
                return issues

            # 检查合约交易(不应该启用)
            if permissions.get("enableFutures", False):
                issues.append("警告: 启用了合约交易权限,建议仅启用现货交易")

            # 检查杠杆交易(不应该启用)
            if permissions.get("enableMargin", False):
                issues.append("警告: 启用了杠杆交易权限,建议仅启用现货交易")

            # 检查期权交易(不应该启用)
            if permissions.get("enableVanillaOptions", False):
                issues.append("警告: 启用了期权交易权限,建议仅启用现货交易")

            return issues

        except Exception as e:
            self.logger.error(f"检查危险权限失败: {e}")
            return []

    async def get_permission_summary(self) -> Dict:
        """
        获取权限配置摘要

        Returns:
            dict: 权限配置摘要
        """
        try:
            permissions = await self._get_api_permissions()
            if not permissions:
                return {}

            summary = {
                "api_key_prefix": self.api_key[:8] + "...",
                "create_time": permissions.get("createTime"),
                "spot_trading": permissions.get("enableSpotAndMarginTrading", False),
                "withdrawals": permissions.get("enableWithdrawals", False),
                "reading": permissions.get("enableReading", False),
                "ip_restricted": permissions.get("ipRestrict", False),
                "futures": permissions.get("enableFutures", False),
                "margin": permissions.get("enableMargin", False),
                "permissions_bitmask": permissions.get("permissionsBitmask", 0),
            }

            return summary

        except Exception as e:
            self.logger.error(f"获取权限摘要失败: {e}")
            return {}

    async def close(self):
        """关闭交易所连接"""
        try:
            await self.exchange.close()
        except Exception as e:
            self.logger.error(f"关闭连接失败: {e}")


async def validate_api_key(api_key: str, api_secret: str, verbose: bool = True) -> bool:
    """
    便捷函数: 验证 API 密钥权限

    Args:
        api_key: Binance API Key
        api_secret: Binance API Secret
        verbose: 是否打印详细信息

    Returns:
        bool: 验证是否通过
    """
    validator = APIKeyValidator(api_key, api_secret)

    try:
        is_valid, issues = await validator.validate_permissions()

        if verbose:
            if is_valid:
                print("✓ API 密钥权限验证通过")

                # 显示权限摘要
                summary = await validator.get_permission_summary()
                print("\n权限配置摘要:")
                print(f"  - 现货交易: {'✓' if summary.get('spot_trading') else '✗'}")
                print(
                    f"  - 提现权限: {'✗ (已启用,危险!)' if summary.get('withdrawals') else '✓ (已禁用)'}"
                )
                print(f"  - IP 限制: {'✓' if summary.get('ip_restricted') else '✗ (未启用)'}")
            else:
                print("✗ API 密钥权限验证失败")
                print("\n发现的问题:")
                for issue in issues:
                    if issue.startswith("警告"):
                        print(f"  ⚠ {issue}")
                    else:
                        print(f"  ✗ {issue}")

        return is_valid

    finally:
        await validator.close()


if __name__ == "__main__":
    import os
    import sys

    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO)

    # 从环境变量加载 API 密钥
    load_dotenv()

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print("错误: 请在 .env 文件中配置 BINANCE_API_KEY 和 BINANCE_API_SECRET")
        sys.exit(1)

    print("=== Binance API 密钥权限验证 ===\n")

    # 运行验证
    is_valid = asyncio.run(validate_api_key(api_key, api_secret, verbose=True))

    if is_valid:
        print("\n✓ 验证通过,可以安全使用")
        sys.exit(0)
    else:
        print("\n✗ 验证失败,请检查并修正权限配置")
        sys.exit(1)
