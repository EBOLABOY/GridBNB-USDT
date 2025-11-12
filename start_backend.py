"""
临时后端启动脚本 - 使用8000端口
"""
from src.services.fastapi_server import start_fastapi_server

if __name__ == "__main__":
    # 使用8000端口启动，避免权限问题
    start_fastapi_server(port=8000)
