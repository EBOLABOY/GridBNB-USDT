"""
FastAPI 应用模块

这个模块包含了迁移自 aiohttp 的 FastAPI 应用。
"""

__all__ = ['create_app']

from src.fastapi_app.main import create_app
