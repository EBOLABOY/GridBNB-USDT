"""
SSE (Server-Sent Events) 实时推送路由

提供配置更新的实时推送通知。
"""

import logging
import asyncio
import json
from typing import Set

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from src.fastapi_app.dependencies import get_current_active_user, get_current_user_from_query
from src.database import User

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局连接管理
_active_connections: Set[asyncio.Queue] = set()


async def broadcast_event(event_type: str, data: dict):
    """
    广播事件到所有连接的客户端

    Args:
        event_type: 事件类型（config_updated/config_deleted/system_restart等）
        data: 事件数据
    """
    message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    # 移除已关闭的连接
    closed_connections = set()

    for queue in _active_connections:
        try:
            await queue.put(message)
        except Exception as e:
            logger.warning(f"发送SSE消息失败: {e}")
            closed_connections.add(queue)

    # 清理已关闭的连接
    _active_connections.difference_update(closed_connections)

    logger.debug(f"SSE广播: {event_type}, 活跃连接: {len(_active_connections)}")


async def event_generator(user: User):
    """
    SSE 事件生成器

    Args:
        user: 当前用户
    """
    # 创建消息队列
    queue = asyncio.Queue()
    _active_connections.add(queue)

    logger.info(f"新SSE连接: user={user.username}")

    # 发送初始连接成功消息
    yield f"event: connected\ndata: {json.dumps({'message': 'SSE connection established'})}\n\n"

    try:
        # 保持连接并发送消息
        while True:
            try:
                # 等待消息（30秒超时）
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield message
            except asyncio.TimeoutError:
                # 发送心跳消息保持连接
                yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        logger.info(f"SSE连接取消: user={user.username}")
    except Exception as e:
        logger.error(f"SSE连接错误: {e}")
    finally:
        # 清理连接
        _active_connections.discard(queue)
        logger.info(f"SSE连接关闭: user={user.username}, 剩余连接: {len(_active_connections)}")


@router.get("/events", summary="SSE 事件流")
async def sse_events(
    current_user: User = Depends(get_current_user_from_query)
):
    """
    SSE事件流端点

    客户端示例:
    ```javascript
    const token = localStorage.getItem('token');
    const eventSource = new EventSource(`/api/sse/events?token=${token}`);

    eventSource.addEventListener('config_updated', (event) => {
        console.log('Config updated:', event.data);
    });
    ```
    """
    return StreamingResponse(
        event_generator(current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


# 导出广播函数供其他模块使用
__all__ = ['router', 'broadcast_event']
