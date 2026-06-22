@echo off
chcp 65001 >nul
title CMDB Lite Dev Server

echo.
echo ============================================
echo   CMDB Lite Dev Server
echo ============================================
echo.

:: Check venv
if not exist "backend\.venv\Scripts\activate.bat" (
    echo [ERROR] backend\.venv not found. Please run first:
    echo   cd backend
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

:: Check node_modules
if not exist "frontend\node_modules" (
    echo [ERROR] frontend\node_modules not found. Please run first:
    echo   cd frontend
    echo   pnpm install
    pause
    exit /b 1
)

echo [1/2] Starting backend (FastAPI . http://localhost:8000) ...
start "CMDB-Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && set PYTHONPATH=. && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait for backend to start
timeout /t 2 /nobreak >nul

echo [2/2] Starting frontend (Vite . http://localhost:5173) ...
start "CMDB-Frontend" cmd /k "cd /d %~dp0frontend && pnpm dev"

echo.
echo ============================================
echo   Done!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Close this window will NOT stop services.
echo Close the corresponding terminal windows instead.
echo.
pause
