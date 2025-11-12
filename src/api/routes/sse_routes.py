"""
SSE (Server-Sent Events) 实时推送路由

提供配置更新的实时推送通知。
"""

import logging
import asyncio
from typing import Set
from aiohttp import web

from src.api.middleware import auth_required

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

# 全局连接管理
_active_connections: Set[asyncio.Queue] = set()


async def broadcast_event(event_type: str, data: dict):
    """广播事件到所有连接的客户端

    Args:
        event_type: 事件类型（config_updated/config_deleted/system_restart等）
        data: 事件数据
    """
    message = f"event: {event_type}\ndata: {str(data)}\n\n"

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


@routes.get('/api/sse/events')
@auth_required
async def sse_events(request: web.Request) -> web.StreamResponse:
    """SSE事件流端点

    客户端示例:
        const eventSource = new EventSource('/api/sse/events', {
            headers: {
                'Authorization': 'Bearer <token>'
            }
        });

        eventSource.addEventListener('config_updated', (event) => {
            console.log('Config updated:', event.data);
        });
    """
    # 创建 SSE 响应
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 禁用 nginx 缓冲
    response.headers['Connection'] = 'keep-alive'

    await response.prepare(request)

    # 创建消息队列
    queue = asyncio.Queue()
    _active_connections.add(queue)

    user = request['user']
    logger.info(f"新SSE连接: user={user.username}, IP={request.remote}")

    # 发送初始连接成功消息
    await response.write(
        f"event: connected\ndata: {{\"message\": \"SSE connection established\"}}\n\n".encode('utf-8')
    )

    try:
        # 保持连接并发送消息
        while True:
            # 等待消息（30秒超时）
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await response.write(message.encode('utf-8'))
            except asyncio.TimeoutError:
                # 发送心跳消息保持连接
                await response.write(b": heartbeat\n\n")

    except asyncio.CancelledError:
        logger.info(f"SSE连接取消: user={user.username}")
    except Exception as e:
        logger.error(f"SSE连接错误: {e}")
    finally:
        # 清理连接
        _active_connections.discard(queue)
        logger.info(
            f"SSE连接关闭: user={user.username}, "
            f"剩余连接: {len(_active_connections)}"
        )

    return response


@routes.post('/api/sse/broadcast')
@auth_required
async def broadcast_manual(request: web.Request) -> web.Response:
    """手动广播事件（用于测试）

    请求体:
        {
            "event_type": "test",
            "data": {"message": "Test event"}
        }
    """
    try:
        data = await request.json()
        event_type = data.get('event_type', 'message')
        event_data = data.get('data', {})

        await broadcast_event(event_type, event_data)

        return web.json_response({
            'message': 'Event broadcasted',
            'active_connections': len(_active_connections),
        })

    except Exception as e:
        logger.error(f"广播事件失败: {e}")
        return web.json_response(
            {'error': 'Failed to broadcast event', 'message': str(e)},
            status=500
        )


@routes.get('/api/sse/status')
@auth_required
async def sse_status(request: web.Request) -> web.Response:
    """获取SSE连接状态

    响应:
        {
            "active_connections": 5,
            "uptime": 12345
        }
    """
    return web.json_response({
        'active_connections': len(_active_connections),
        'message': 'SSE service is running',
    })


# 导出广播函数供其他模块使用
__all__ = ['routes', 'broadcast_event']
