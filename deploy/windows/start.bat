@echo off
setlocal enabledelayedexpansion
:: ============================================================
:: Z-CMDB — Double-click to start (Windows)
:: ============================================================
cd /d "%~dp0"
set "PY=python\python.exe"
set "HOST=127.0.0.1"
set "PORT=8000"

:: Allow port override via first argument
if not "%~1"=="" set "PORT=%~1"

:: Ensure data directory exists
if not exist "data" mkdir "data"

:: Port pre-check
netstat -ano 2>nul | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [ERROR] Port %PORT% is already in use. Close the other process or use: start.bat ^<port^>
    pause
    exit /b 1
)

:: Generate .env on first run (idempotent)
if not exist ".env" (
    "%PY%" -c "import secrets;open('.env','w').write('APP_ENV=production\nDATABASE_URL=sqlite:///./data/cmdb.db\nJWT_SECRET='+secrets.token_urlsafe(48)+'\nCORS_ORIGINS=[\"http://%HOST%:%PORT%\"]\n')"
    echo [INFO] Generated .env with random JWT_SECRET
)

:: Run migrations
echo [INFO] Running database migrations ...
"%PY%" -m alembic upgrade head
if %errorlevel% neq 0 (
    echo [ERROR] Database migration failed!
    pause
    exit /b 1
)

:: ── 后台：轮询健康检查，就绪后开浏览器，然后自退 ──
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 30;$i++){try{Invoke-WebRequest -UseBasicParsing 'http://%HOST%:%PORT%/api/health' -TimeoutSec 1 | Out-Null; Start-Process 'http://%HOST%:%PORT%'; break}catch{Start-Sleep 1}}"

:: ── 前台运行 uvicorn —— 关闭本窗口即停止服务 ──
echo.
echo ============================================================
echo  Z-CMDB starting at http://%HOST%:%PORT%
echo  浏览器会自动打开；关闭本窗口即停止服务。
echo ============================================================
"%PY%" -m uvicorn app.main:app --host %HOST% --port %PORT% --workers 1
