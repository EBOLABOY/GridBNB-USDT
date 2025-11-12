"""
首页运行状态API

提供交易系统的实时运行状态、统计数据和交易对信息。
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends
from src.fastapi_app.dependencies import get_current_active_user
from src.database import User

logger = logging.getLogger(__name__)

router = APIRouter()


def get_system_uptime() -> str:
    """获取系统运行时间（简化版）"""
    # TODO: 实现真实的系统启动时间跟踪
    return "运行中"


def get_trader_stats(traders: Dict) -> Dict[str, Any]:
    """
    从交易器获取统计数据

    Args:
        traders: 交易器字典 {symbol: trader}

    Returns:
        统计数据字典
    """
    if not traders:
        return {
            "total_profit": 0.0,
            "profit_rate": 0.0,
            "today_profit": 0.0,
            "total_trades": 0,
            "active_symbols": 0,
            "system_status": "stopped",
        }

    total_profit = 0.0
    total_trades = 0
    active_count = 0

    for symbol, trader in traders.items():
        try:
            # 获取交易器状态
            if hasattr(trader, 'is_running') and trader.is_running:
                active_count += 1

            # 获取盈亏
            if hasattr(trader, 'profit_tracker') and trader.profit_tracker:
                total_profit += trader.profit_tracker.get('total_profit', 0)

            # 获取交易次数
            if hasattr(trader, 'trade_count'):
                total_trades += trader.trade_count

        except Exception as e:
            logger.error(f"获取交易器 {symbol} 状态失败: {e}")

    # 计算收益率（简化版）
    profit_rate = 0.0
    if hasattr(list(traders.values())[0], 'initial_capital') if traders else False:
        try:
            initial_capital = sum(
                getattr(t, 'initial_capital', 0) for t in traders.values()
            )
            if initial_capital > 0:
                profit_rate = (total_profit / initial_capital) * 100
        except Exception:
            pass

    return {
        "total_profit": round(total_profit, 2),
        "profit_rate": round(profit_rate, 2),
        "today_profit": round(total_profit * 0.1, 2),  # 简化：假设今日为总盈亏的10%
        "total_trades": total_trades,
        "active_symbols": active_count,
        "system_status": "running" if active_count > 0 else "stopped",
    }


def get_symbol_status(traders: Dict) -> list:
    """
    获取各交易对的状态

    Args:
        traders: 交易器字典

    Returns:
        交易对状态列表
    """
    symbol_list = []

    for symbol, trader in traders.items():
        try:
            # 获取当前价格
            current_price = 0.0
            if hasattr(trader, 'current_price'):
                current_price = trader.current_price
            elif hasattr(trader, 'get_current_price'):
                current_price = trader.get_current_price()

            # 获取24h涨跌（简化版）
            change_24h = 0.0

            # 获取仓位
            position = 0.0
            if hasattr(trader, 'position_ratio'):
                position = trader.position_ratio
            elif hasattr(trader, 'get_position_ratio'):
                position = trader.get_position_ratio()

            # 获取盈亏
            profit = 0.0
            if hasattr(trader, 'profit_tracker') and trader.profit_tracker:
                profit = trader.profit_tracker.get('total_profit', 0)

            # 状态
            status = "active" if (hasattr(trader, 'is_running') and trader.is_running) else "inactive"

            # 最后交易时间
            last_trade_time = "未知"
            if hasattr(trader, 'last_trade_time') and trader.last_trade_time:
                time_diff = datetime.now() - trader.last_trade_time
                if time_diff < timedelta(minutes=1):
                    last_trade_time = "刚刚"
                elif time_diff < timedelta(hours=1):
                    last_trade_time = f"{int(time_diff.total_seconds() / 60)}分钟前"
                else:
                    last_trade_time = f"{int(time_diff.total_seconds() / 3600)}小时前"

            symbol_list.append({
                "symbol": symbol,
                "currentPrice": round(current_price, 2),
                "change24h": round(change_24h, 2),
                "position": round(position, 2),
                "profit": round(profit, 2),
                "status": status,
                "lastTradeTime": last_trade_time,
            })

        except Exception as e:
            logger.error(f"获取交易对 {symbol} 状态失败: {e}")
            # 添加默认数据
            symbol_list.append({
                "symbol": symbol,
                "currentPrice": 0.0,
                "change24h": 0.0,
                "position": 0.0,
                "profit": 0.0,
                "status": "error",
                "lastTradeTime": "错误",
            })

    return symbol_list


def get_recent_trades(traders: Dict, limit: int = 5) -> list:
    """
    获取最近的交易记录

    Args:
        traders: 交易器字典
        limit: 返回数量限制

    Returns:
        交易记录列表
    """
    all_trades = []

    for symbol, trader in traders.items():
        try:
            # 获取交易历史
            if hasattr(trader, 'trade_history') and trader.trade_history:
                for trade in trader.trade_history[-limit:]:
                    all_trades.append({
                        "id": trade.get('id', 0),
                        "symbol": symbol,
                        "side": trade.get('side', 'unknown'),
                        "price": trade.get('price', 0.0),
                        "amount": trade.get('amount', 0.0),
                        "profit": trade.get('profit', 0.0),
                        "time": trade.get('timestamp', '未知'),
                    })

        except Exception as e:
            logger.error(f"获取交易对 {symbol} 交易历史失败: {e}")

    # 按时间排序（最新的在前）
    all_trades.sort(key=lambda x: x.get('time', ''), reverse=True)

    return all_trades[:limit]


@router.get("/status", summary="获取系统运行状态")
async def get_dashboard_status(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    获取首页展示的系统运行状态

    包括：
    - 核心指标（总盈亏、收益率、今日盈亏、交易次数）
    - 系统状态（运行状态、活跃交易对、运行时间）
    - 交易对状态列表
    - 最近交易记录
    """
    try:
        # 从app.state获取交易器
        traders = getattr(request.app.state, 'traders', {})

        # 获取统计数据
        stats = get_trader_stats(traders)

        # 获取交易对状态
        symbol_status = get_symbol_status(traders)

        # 获取最近交易
        recent_trades = get_recent_trades(traders, limit=10)

        # 系统运行时间
        uptime = get_system_uptime()

        return {
            "success": True,
            "data": {
                # 核心指标
                "dashboard": stats,

                # 系统信息
                "system": {
                    "status": stats["system_status"],
                    "active_symbols": stats["active_symbols"],
                    "uptime": uptime,
                    "last_update": datetime.now().isoformat(),
                },

                # 交易对状态
                "symbols": symbol_status,

                # 最近交易
                "recent_trades": recent_trades,

                # 性能指标（占位）
                "performance": {
                    "cpu_usage": 15.6,  # TODO: 实现真实的系统监控
                    "memory_usage": 25.0,
                    "memory_total": 2048,
                    "memory_used": 512,
                    "api_latency": 45,
                },
            }
        }

    except Exception as e:
        logger.error(f"获取运行状态失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "dashboard": {
                    "total_profit": 0.0,
                    "profit_rate": 0.0,
                    "today_profit": 0.0,
                    "total_trades": 0,
                    "active_symbols": 0,
                    "system_status": "error",
                },
                "system": {
                    "status": "error",
                    "active_symbols": 0,
                    "uptime": "未知",
                    "last_update": datetime.now().isoformat(),
                },
                "symbols": [],
                "recent_trades": [],
                "performance": {
                    "cpu_usage": 0,
                    "memory_usage": 0,
                    "memory_total": 0,
                    "memory_used": 0,
                    "api_latency": 0,
                },
            }
        }


@router.get("/quick-stats", summary="快速统计（轻量级）")
async def get_quick_stats(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    轻量级快速统计接口（用于频繁轮询）

    仅返回核心指标，减少计算开销
    """
    try:
        traders = getattr(request.app.state, 'traders', {})
        stats = get_trader_stats(traders)

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"获取快速统计失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }
