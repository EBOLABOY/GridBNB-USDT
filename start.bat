@echo off
REM GridBNB-USDT 启动脚本 (Windows)
REM 企业级启动方式，自动处理路径问题

echo ================================================
echo GridBNB-USDT 多币种网格交易机器人
echo ================================================
echo.

REM 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    echo [信息] 检测到虚拟环境，正在激活...
    call .venv\Scripts\activate.bat
) else (
    echo [警告] 未检测到虚拟环境
)

REM 检查配置文件
if not exist "config\.env" (
    echo [错误] 未找到配置文件 config\.env
    echo [提示] 请先复制 config\.env.example 为 config\.env 并配置
    pause
    exit /b 1
)

echo [信息] 正在启动交易机器人...
echo.

REM 使用企业级启动方式
python src/main.py

pause
