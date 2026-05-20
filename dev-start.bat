@echo off
chcp 65001 >nul
title CMDB Lite 开发环境

echo.
echo ============================================
echo   CMDB Lite 开发环境启动
echo ============================================
echo.

:: 检查 venv 是否存在
if not exist "backend\.venv\Scripts\activate.bat" (
    echo [错误] 未找到 backend\.venv，请先执行：
    echo   cd backend
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

:: 检查 node_modules 是否存在
if not exist "frontend\node_modules" (
    echo [错误] 未找到 frontend\node_modules，请先执行：
    echo   cd frontend
    echo   pnpm install
    pause
    exit /b 1
)

echo [1/2] 启动后端 (FastAPI · http://localhost:8000) ...
start "CMDB-Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && set PYTHONPATH=. && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待后端启动
timeout /t 2 /nobreak >nul

echo [2/2] 启动前端 (Vite · http://localhost:5173) ...
start "CMDB-Frontend" cmd /k "cd /d %~dp0frontend && pnpm dev"

echo.
echo ============================================
echo   启动完成！
echo   后端: http://localhost:8000
echo   前端: http://localhost:5173
echo   API文档: http://localhost:8000/docs
echo ============================================
echo.
echo 关闭此窗口不会停止服务，请直接关闭对应终端窗口。
echo.
pause
