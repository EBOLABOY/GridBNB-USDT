"""
全局资金分配器模块

功能:
1. 统一管理多交易对的资金分配
2. 防止资金冲突
3. 提供灵活的分配策略
4. 实时监控全局仓位

作者: GridBNB-USDT Team
创建日期: 2025-10-24
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum

from src.config.settings import settings


class AllocationStrategy(Enum):
    """资金分配策略"""
    EQUAL = "equal"          # 平均分配
    WEIGHTED = "weighted"    # 按权重分配
    DYNAMIC = "dynamic"      # 动态分配（根据表现）


@dataclass
class TraderAllocation:
    """交易对资金分配"""
    symbol: str
    allocated_capital: float    # 分配的资本
    current_usage: float        # 当前使用量
    usage_ratio: float          # 使用率
    performance_score: float    # 表现评分（用于动态分配）


class GlobalFundAllocator:
    """
    全局资金分配器

    核心职责:
    1. 为每个交易对分配独立的资金池
    2. 确保全局资金使用不超限
    3. 提供资金申请审批机制
    4. 监控和报告资金使用情况

    示例:
        allocator = GlobalFundAllocator(
            symbols=['BNB/USDT', 'ETH/USDT'],
            total_capital=1000.0,
            strategy='equal'
        )

        # 检查交易是否允许
        if await allocator.check_trade_allowed('BNB/USDT', 100.0):
            # 执行交易
            await allocator.record_trade('BNB/USDT', 100.0, 'buy')
    """

    def __init__(
        self,
        symbols: List[str],
        total_capital: float,
        strategy: Literal['equal', 'weighted', 'dynamic'] = 'equal',
        weights: Optional[Dict[str, float]] = None,
        max_global_usage: float = 0.95
    ):
        """
        初始化全局资金分配器

        Args:
            symbols: 交易对列表
            total_capital: 总资本（USDT）
            strategy: 分配策略
            weights: 权重配置（仅当strategy='weighted'时使用）
            max_global_usage: 全局最大资金使用率（默认95%）
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        self.symbols = symbols
        self.total_capital = total_capital
        self.strategy = AllocationStrategy(strategy)
        self.max_global_usage = max_global_usage

        # 初始化分配
        self.allocations: Dict[str, TraderAllocation] = {}
        self._initialize_allocations(weights)

        # 交易者引用（后续注入）
        self.traders: Dict[str, any] = {}

        # 统计数据
        self.last_rebalance_time = time.time()
        self.rebalance_interval = 3600  # 1小时重新平衡一次

        self.logger.info(
            f"全局资金分配器初始化 | "
            f"总资本: {total_capital:.2f} USDT | "
            f"交易对数: {len(symbols)} | "
            f"策略: {strategy} | "
            f"全局限额: {max_global_usage:.1%}"
        )

    def _initialize_allocations(self, weights: Optional[Dict[str, float]]):
        """初始化资金分配"""
        if self.strategy == AllocationStrategy.EQUAL:
            # 平均分配
            per_symbol = self.total_capital / len(self.symbols)
            for symbol in self.symbols:
                self.allocations[symbol] = TraderAllocation(
                    symbol=symbol,
                    allocated_capital=per_symbol,
                    current_usage=0.0,
                    usage_ratio=0.0,
                    performance_score=1.0
                )

        elif self.strategy == AllocationStrategy.WEIGHTED:
            # 按权重分配
            if not weights:
                raise ValueError("权重分配策略需要提供weights参数")

            total_weight = sum(weights.values())
            for symbol in self.symbols:
                weight = weights.get(symbol, 1.0)
                allocated = self.total_capital * (weight / total_weight)

                self.allocations[symbol] = TraderAllocation(
                    symbol=symbol,
                    allocated_capital=allocated,
                    current_usage=0.0,
                    usage_ratio=0.0,
                    performance_score=1.0
                )

        elif self.strategy == AllocationStrategy.DYNAMIC:
            # 动态分配（初始平均，后续根据表现调整）
            per_symbol = self.total_capital / len(self.symbols)
            for symbol in self.symbols:
                self.allocations[symbol] = TraderAllocation(
                    symbol=symbol,
                    allocated_capital=per_symbol,
                    current_usage=0.0,
                    usage_ratio=0.0,
                    performance_score=1.0
                )

        # 打印分配结果
        for symbol, alloc in self.allocations.items():
            self.logger.info(
                f"分配 | {symbol}: {alloc.allocated_capital:.2f} USDT "
                f"({alloc.allocated_capital/self.total_capital:.1%})"
            )

    def register_trader(self, symbol: str, trader):
        """
        注册交易者

        Args:
            symbol: 交易对
            trader: GridTrader实例
        """
        if symbol not in self.symbols:
            raise ValueError(f"未知交易对: {symbol}")

        self.traders[symbol] = trader
        self.logger.debug(f"注册交易者: {symbol}")

    async def check_trade_allowed(
        self,
        symbol: str,
        required_amount: float,
        side: Literal['buy', 'sell']
    ) -> tuple[bool, str]:
        """
        检查交易是否允许

        Args:
            symbol: 交易对
            required_amount: 所需金额（USDT）
            side: 交易方向

        Returns:
            (是否允许, 拒绝原因)
        """
        if symbol not in self.allocations:
            return False, f"未知交易对: {symbol}"

        alloc = self.allocations[symbol]

        # 检查1: 交易对自身限额
        if side == 'buy':
            new_usage = alloc.current_usage + required_amount

            if new_usage > alloc.allocated_capital:
                self.logger.warning(
                    f"交易对限额不足 | {symbol} | "
                    f"当前: {alloc.current_usage:.2f} | "
                    f"需要: {required_amount:.2f} | "
                    f"限额: {alloc.allocated_capital:.2f}"
                )
                return False, f"交易对限额不足（已用{alloc.usage_ratio:.1%}）"

        # 检查2: 全局限额
        global_usage = await self._get_global_usage()

        if side == 'buy':
            projected_usage = global_usage + required_amount
            projected_ratio = projected_usage / self.total_capital

            if projected_ratio > self.max_global_usage:
                self.logger.warning(
                    f"全局限额不足 | "
                    f"当前: {global_usage:.2f} ({global_usage/self.total_capital:.1%}) | "
                    f"预计: {projected_usage:.2f} ({projected_ratio:.1%}) | "
                    f"限额: {self.max_global_usage:.1%}"
                )
                return False, f"全局资金限额不足（已用{global_usage/self.total_capital:.1%}）"

        return True, ""

    async def record_trade(
        self,
        symbol: str,
        amount: float,
        side: Literal['buy', 'sell']
    ):
        """
        记录交易，更新使用量

        Args:
            symbol: 交易对
            amount: 交易金额（USDT）
            side: 交易方向
        """
        if symbol not in self.allocations:
            self.logger.error(f"记录交易失败: 未知交易对 {symbol}")
            return

        alloc = self.allocations[symbol]

        if side == 'buy':
            alloc.current_usage += amount
        elif side == 'sell':
            alloc.current_usage = max(0, alloc.current_usage - amount)

        # 更新使用率
        alloc.usage_ratio = alloc.current_usage / alloc.allocated_capital

        self.logger.debug(
            f"交易记录 | {symbol} | {side} | "
            f"金额: {amount:.2f} | "
            f"当前使用: {alloc.current_usage:.2f} ({alloc.usage_ratio:.1%})"
        )

    async def _get_global_usage(self) -> float:
        """
        获取全局资金使用量

        Returns:
            已使用的总金额（USDT）
        """
        total_used = 0.0

        for symbol, trader in self.traders.items():
            try:
                # 获取该交易对持仓价值
                if hasattr(trader, '_get_pair_specific_assets_value'):
                    assets_value = await trader._get_pair_specific_assets_value()

                    # 计算已用资金 = 持仓价值 - 闲置USDT
                    balance = await trader.exchange.fetch_balance()
                    funding_balance = await trader.exchange.fetch_funding_balance()

                    quote_balance = (
                        float(balance.get('free', {}).get(trader.quote_asset, 0)) +
                        float(funding_balance.get(trader.quote_asset, 0))
                    )

                    # 持仓占用的资金
                    used = assets_value - quote_balance
                    total_used += max(0, used)

            except Exception as e:
                self.logger.error(f"获取{symbol}资金使用失败: {e}")

        return total_used

    async def rebalance_if_needed(self):
        """
        如果需要，重新平衡资金分配

        仅当strategy='dynamic'时有效
        """
        if self.strategy != AllocationStrategy.DYNAMIC:
            return

        current_time = time.time()
        if current_time - self.last_rebalance_time < self.rebalance_interval:
            return

        self.logger.info("开始动态资金重新平衡...")

        # 收集表现数据
        for symbol, trader in self.traders.items():
            if hasattr(trader, 'order_tracker'):
                # 计算表现评分（简单示例：基于盈亏率）
                total_profit = 0
                trades = trader.order_tracker.get_trade_history()

                for trade in trades[-20:]:  # 最近20笔
                    total_profit += trade.get('profit', 0)

                # 归一化评分 (0.5 - 2.0)
                score = 1.0 + (total_profit / self.total_capital)
                score = max(0.5, min(2.0, score))

                self.allocations[symbol].performance_score = score

        # 根据表现评分重新分配
        total_score = sum(
            alloc.performance_score
            for alloc in self.allocations.values()
        )

        for symbol, alloc in self.allocations.items():
            new_allocation = self.total_capital * (
                alloc.performance_score / total_score
            )

            old_allocation = alloc.allocated_capital
            alloc.allocated_capital = new_allocation

            self.logger.info(
                f"重新分配 | {symbol} | "
                f"{old_allocation:.2f} → {new_allocation:.2f} USDT | "
                f"评分: {alloc.performance_score:.2f}"
            )

        self.last_rebalance_time = current_time

    def get_allocation_status(self) -> Dict:
        """
        获取分配状态报告

        Returns:
            包含所有交易对分配情况的字典
        """
        report = {
            'total_capital': self.total_capital,
            'max_global_usage': self.max_global_usage,
            'strategy': self.strategy.value,
            'allocations': {}
        }

        for symbol, alloc in self.allocations.items():
            report['allocations'][symbol] = {
                'allocated': alloc.allocated_capital,
                'used': alloc.current_usage,
                'usage_ratio': alloc.usage_ratio,
                'available': alloc.allocated_capital - alloc.current_usage,
                'performance_score': alloc.performance_score
            }

        return report

    async def get_global_status_summary(self) -> str:
        """
        获取全局状态摘要（用于日志）

        Returns:
            格式化的状态字符串
        """
        global_usage = await self._get_global_usage()
        global_ratio = global_usage / self.total_capital

        summary = [
            f"\n{'='*60}",
            f"全局资金分配状态",
            f"{'='*60}",
            f"总资本: {self.total_capital:.2f} USDT",
            f"全局使用: {global_usage:.2f} USDT ({global_ratio:.1%})",
            f"全局限额: {self.max_global_usage:.1%}",
            f"剩余可用: {self.total_capital - global_usage:.2f} USDT",
            f"",
            f"各交易对分配:"
        ]

        for symbol, alloc in self.allocations.items():
            summary.append(
                f"  {symbol:12} | "
                f"分配: {alloc.allocated_capital:8.2f} | "
                f"已用: {alloc.current_usage:8.2f} ({alloc.usage_ratio:5.1%}) | "
                f"可用: {alloc.allocated_capital - alloc.current_usage:8.2f}"
            )

        summary.append(f"{'='*60}\n")

        return '\n'.join(summary)
