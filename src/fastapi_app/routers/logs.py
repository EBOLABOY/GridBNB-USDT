"""
日志查看路由

提供系统日志查询、实时日志流等功能。
"""

import logging
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.fastapi_app.dependencies import get_current_active_user
from src.database import User

logger = logging.getLogger(__name__)

router = APIRouter()

# 日志文件路径
LOGS_DIR = Path("logs")
DEFAULT_LOG_FILE = LOGS_DIR / "gridbnb.log"


class LogEntry(BaseModel):
    """日志条目模型"""
    timestamp: str
    level: str
    message: str
    event: Optional[str] = None
    extra: Optional[dict] = None


class LogsResponse(BaseModel):
    """日志响应模型"""
    total: int
    logs: List[LogEntry]
    page: int
    page_size: int


def parse_log_line(line: str) -> Optional[LogEntry]:
    """
    解析日志行（支持JSON和普通文本格式）

    Args:
        line: 日志行

    Returns:
        LogEntry或None
    """
    line = line.strip()
    if not line:
        return None

    try:
        # 尝试解析JSON格式日志
        data = json.loads(line)
        return LogEntry(
            timestamp=data.get('timestamp', ''),
            level=data.get('level', 'info').upper(),
            message=data.get('message', ''),
            event=data.get('event'),
            extra={k: v for k, v in data.items()
                   if k not in ['timestamp', 'level', 'message', 'event']}
        )
    except json.JSONDecodeError:
        # 普通文本日志，尝试解析基本格式
        # 格式示例: 2025-10-20 15:30:45 INFO: message
        parts = line.split(' ', 3)
        if len(parts) >= 4:
            timestamp = f"{parts[0]}T{parts[1]}"
            level = parts[2].rstrip(':').upper()
            message = parts[3] if len(parts) > 3 else ''
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                event=None,
                extra=None
            )
        else:
            # 无法解析，作为纯消息返回
            return LogEntry(
                timestamp=datetime.now().isoformat(),
                level='INFO',
                message=line,
                event=None,
                extra=None
            )


def read_log_file(
    log_file: Path,
    level: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 100
) -> List[LogEntry]:
    """
    读取日志文件

    Args:
        log_file: 日志文件路径
        level: 日志级别筛选
        keyword: 关键字搜索
        limit: 返回最大条数

    Returns:
        日志条目列表
    """
    if not log_file.exists():
        return []

    logs = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 读取最后N行
            lines = f.readlines()

            # 倒序处理（最新的在前）
            for line in reversed(lines):
                if len(logs) >= limit:
                    break

                entry = parse_log_line(line)
                if not entry:
                    continue

                # 日志级别筛选
                if level and entry.level != level.upper():
                    continue

                # 关键字搜索
                if keyword:
                    keyword_lower = keyword.lower()
                    if (keyword_lower not in entry.message.lower() and
                        (not entry.event or keyword_lower not in entry.event.lower())):
                        continue

                logs.append(entry)

    except Exception as e:
        logger.error(f"读取日志文件失败: {e}")

    return logs


@router.get("/list", response_model=LogsResponse, summary="获取日志列表")
async def get_logs(
    level: Optional[str] = Query(None, description="日志级别筛选(DEBUG/INFO/WARNING/ERROR/CRITICAL)"),
    keyword: Optional[str] = Query(None, description="关键字搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=10, le=500, description="每页条数"),
    log_file: str = Query("gridbnb.log", description="日志文件名"),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取日志列表（分页）

    - 支持按日志级别筛选
    - 支持关键字搜索
    - 倒序返回（最新的在前）
    """
    # 验证日志级别
    if level and level.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        raise HTTPException(status_code=400, detail="Invalid log level")

    # 构建日志文件路径
    log_path = LOGS_DIR / log_file

    # 安全检查：防止路径遍历
    if not log_path.resolve().is_relative_to(LOGS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid log file path")

    # 读取日志
    all_logs = read_log_file(
        log_path,
        level=level,
        keyword=keyword,
        limit=page_size * 10  # 读取多一些以支持筛选
    )

    # 分页
    total = len(all_logs)
    start = (page - 1) * page_size
    end = start + page_size
    logs = all_logs[start:end]

    return LogsResponse(
        total=total,
        logs=logs,
        page=page,
        page_size=page_size
    )


@router.get("/files", summary="获取日志文件列表")
async def list_log_files(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取所有日志文件列表
    """
    if not LOGS_DIR.exists():
        return {"files": []}

    try:
        files = []
        for file_path in LOGS_DIR.glob("*.log"):
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        # 按修改时间倒序排序
        files.sort(key=lambda x: x['modified'], reverse=True)

        return {"files": files}
    except Exception as e:
        logger.error(f"获取日志文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def log_stream_generator(
    log_file: Path,
    level: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """
    实时日志流生成器

    Args:
        log_file: 日志文件路径
        level: 日志级别筛选
        keyword: 关键字搜索
    """
    try:
        # 发送初始历史日志（最后50条）
        initial_logs = read_log_file(log_file, level=level, keyword=keyword, limit=50)
        for log_entry in reversed(initial_logs):  # 正序发送
            yield f"data: {log_entry.model_dump_json()}\n\n"

        # 实时监控日志文件（简化版，生产环境建议使用watchdog库）
        last_position = log_file.stat().st_size if log_file.exists() else 0

        while True:
            try:
                if log_file.exists():
                    current_size = log_file.stat().st_size

                    if current_size > last_position:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            last_position = f.tell()

                        for line in new_lines:
                            entry = parse_log_line(line)
                            if not entry:
                                continue

                            # 日志级别筛选
                            if level and entry.level != level.upper():
                                continue

                            # 关键字搜索
                            if keyword:
                                keyword_lower = keyword.lower()
                                if (keyword_lower not in entry.message.lower() and
                                    (not entry.event or keyword_lower not in entry.event.lower())):
                                    continue

                            yield f"data: {entry.model_dump_json()}\n\n"

                # 等待1秒再检查
                await asyncio.sleep(1)

                # 发送心跳
                yield ": heartbeat\n\n"

            except Exception as e:
                logger.error(f"日志流错误: {e}")
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("日志流连接取消")
    except Exception as e:
        logger.error(f"日志流错误: {e}")


@router.get("/stream", summary="实时日志流")
async def stream_logs(
    level: Optional[str] = Query(None, description="日志级别筛选"),
    keyword: Optional[str] = Query(None, description="关键字搜索"),
    log_file: str = Query("gridbnb.log", description="日志文件名"),
    current_user: User = Depends(get_current_active_user),
):
    """
    实时日志流（SSE）

    客户端示例:
    ```javascript
    const eventSource = new EventSource('/api/logs/stream?log_file=gridbnb.log');
    eventSource.onmessage = (event) => {
        const log = JSON.parse(event.data);
        console.log(log);
    };
    ```
    """
    # 验证日志级别
    if level and level.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        raise HTTPException(status_code=400, detail="Invalid log level")

    # 构建日志文件路径
    log_path = LOGS_DIR / log_file

    # 安全检查
    if not log_path.resolve().is_relative_to(LOGS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid log file path")

    return StreamingResponse(
        log_stream_generator(log_path, level=level, keyword=keyword),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


__all__ = ['router']
