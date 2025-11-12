"""
交易历史路由

提供交易历史查询、统计等功能。
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from src.fastapi_app.dependencies import get_current_active_user
from src.database import User

logger = logging.getLogger(__name__)

router = APIRouter()


class TradeRecord(BaseModel):
    """交易记录模型"""
    id: int
    symbol: str
    side: str
    price: float
    amount: float
    total: float
    profit: float
    fee: float
    timestamp: str
    order_id: Optional[str] = None
    notes: Optional[str] = None


class TradesResponse(BaseModel):
    """交易历史响应模型"""
    total: int
    trades: List[TradeRecord]
    page: int
    page_size: int
    summary: Dict[str, Any]


def get_all_trades(
    traders: Dict,
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    从交易器获取所有交易记录

    Args:
        traders: 交易器字典
        symbol: 交易对筛选
        side: 方向筛选（buy/sell）
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        交易记录列表
    """
    all_trades = []

    for trader_symbol, trader in traders.items():
        # 交易对筛选
        if symbol and trader_symbol != symbol:
            continue

        try:
            # 获取交易历史
            if hasattr(trader, 'trade_history') and trader.trade_history:
                for idx, trade in enumerate(trader.trade_history):
                    # 方向筛选
                    if side and trade.get('side', '').lower() != side.lower():
                        continue

                    # 时间筛选
                    trade_time = trade.get('timestamp', '')
                    if start_time and trade_time < start_time:
                        continue
                    if end_time and trade_time > end_time:
                        continue

                    # 构建交易记录
                    all_trades.append({
                        "id": trade.get('id', idx),
                        "symbol": trader_symbol,
                        "side": trade.get('side', 'unknown'),
                        "price": trade.get('price', 0.0),
                        "amount": trade.get('amount', 0.0),
                        "total": trade.get('price', 0.0) * trade.get('amount', 0.0),
                        "profit": trade.get('profit', 0.0),
                        "fee": trade.get('fee', 0.0),
                        "timestamp": trade_time,
                        "order_id": trade.get('order_id'),
                        "notes": trade.get('notes'),
                    })

        except Exception as e:
            logger.error(f"获取交易对 {trader_symbol} 交易历史失败: {e}")

    # 按时间排序（最新的在前）
    all_trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    return all_trades


def calculate_trade_summary(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算交易统计信息

    Args:
        trades: 交易记录列表

    Returns:
        统计信息字典
    """
    if not trades:
        return {
            "total_count": 0,
            "buy_count": 0,
            "sell_count": 0,
            "total_profit": 0.0,
            "total_fee": 0.0,
            "total_volume": 0.0,
            "win_rate": 0.0,
            "avg_profit": 0.0,
        }

    buy_count = sum(1 for t in trades if t['side'].lower() == 'buy')
    sell_count = sum(1 for t in trades if t['side'].lower() == 'sell')
    total_profit = sum(t['profit'] for t in trades)
    total_fee = sum(t.get('fee', 0.0) for t in trades)
    total_volume = sum(t['total'] for t in trades)

    # 胜率计算
    profitable_trades = sum(1 for t in trades if t['profit'] > 0)
    win_rate = (profitable_trades / len(trades) * 100) if trades else 0.0

    # 平均盈亏
    avg_profit = total_profit / len(trades) if trades else 0.0

    return {
        "total_count": len(trades),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "total_profit": round(total_profit, 2),
        "total_fee": round(total_fee, 2),
        "total_volume": round(total_volume, 2),
        "win_rate": round(win_rate, 2),
        "avg_profit": round(avg_profit, 2),
    }


@router.get("/list", response_model=TradesResponse, summary="获取交易历史")
async def get_trades(
    request: Request,
    symbol: Optional[str] = Query(None, description="交易对筛选"),
    side: Optional[str] = Query(None, description="方向筛选(buy/sell)"),
    start_time: Optional[str] = Query(None, description="开始时间（ISO格式）"),
    end_time: Optional[str] = Query(None, description="结束时间（ISO格式）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=10, le=500, description="每页条数"),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取交易历史列表（分页）

    - 支持按交易对筛选
    - 支持按买卖方向筛选
    - 支持时间���围筛选
    - 返回统计信息
    """
    try:
        # 从app.state获取交易器
        traders = getattr(request.app.state, 'traders', {})

        # 获取所有交易
        all_trades = get_all_trades(
            traders,
            symbol=symbol,
            side=side,
            start_time=start_time,
            end_time=end_time,
        )

        # 计算统计信息
        summary = calculate_trade_summary(all_trades)

        # 分页
        total = len(all_trades)
        start = (page - 1) * page_size
        end = start + page_size
        trades = all_trades[start:end]

        return TradesResponse(
            total=total,
            trades=[TradeRecord(**t) for t in trades],
            page=page,
            page_size=page_size,
            summary=summary,
        )

    except Exception as e:
        logger.error(f"获取交易历史失败: {e}")
        return TradesResponse(
            total=0,
            trades=[],
            page=page,
            page_size=page_size,
            summary=calculate_trade_summary([]),
        )


@router.get("/symbols", summary="获取有交易记录的交易对列表")
async def get_trade_symbols(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有有交易记录的交易对列表
    """
    try:
        traders = getattr(request.app.state, 'traders', {})

        symbols = []
        for symbol, trader in traders.items():
            if hasattr(trader, 'trade_history') and trader.trade_history:
                symbols.append({
                    "symbol": symbol,
                    "trade_count": len(trader.trade_history),
                })

        return {
            "success": True,
            "symbols": symbols,
        }

    except Exception as e:
        logger.error(f"获取交易对列表失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "symbols": [],
        }


@router.get("/statistics", summary="获取交易统计信息")
async def get_trade_statistics(
    request: Request,
    symbol: Optional[str] = Query(None, description="交易对"),
    period: str = Query("all", description="统计周期(today/week/month/all)"),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取交易统计信息

    - 按时间周期统计
    - 支持单个交易对或全部
    """
    try:
        traders = getattr(request.app.state, 'traders', {})

        # 计算时间范围
        now = datetime.now()
        start_time = None

        if period == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif period == "week":
            start_time = (now - timedelta(days=7)).isoformat()
        elif period == "month":
            start_time = (now - timedelta(days=30)).isoformat()

        # 获取交易记录
        all_trades = get_all_trades(
            traders,
            symbol=symbol,
            start_time=start_time,
        )

        # 计算统计
        summary = calculate_trade_summary(all_trades)

        # 按日期分组统计
        daily_stats = {}
        for trade in all_trades:
            try:
                trade_date = datetime.fromisoformat(trade['timestamp']).date().isoformat()
                if trade_date not in daily_stats:
                    daily_stats[trade_date] = {
                        "date": trade_date,
                        "count": 0,
                        "profit": 0.0,
                        "volume": 0.0,
                    }
                daily_stats[trade_date]["count"] += 1
                daily_stats[trade_date]["profit"] += trade['profit']
                daily_stats[trade_date]["volume"] += trade['total']
            except Exception:
                pass

        # 转换为列表并排序
        daily_list = sorted(daily_stats.values(), key=lambda x: x['date'], reverse=True)

        return {
            "success": True,
            "summary": summary,
            "daily_stats": daily_list[:30],  # 最多返回30天
        }

    except Exception as e:
        logger.error(f"获取交易统计失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "summary": calculate_trade_summary([]),
            "daily_stats": [],
        }


__all__ = ['router']
