@echo off
setlocal enabledelayedexpansion
:: ============================================================
:: Z-CMDB — Double-click to start (Windows)
:: ============================================================
chcp 65001 >nul
cd /d "%~dp0"
set "PY=python\python.exe"
set "PYTHONIOENCODING=utf-8"
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

:: 加密模型（PRD §6）：迁移移到解锁/setup 之后，启动前不再跑 alembic。
:: 应用以 LOCKED 启动；浏览器打开后进入 setup（首次）或解锁页。
:: 无人值守可设 CMDB_UNLOCK_PASSWORD 环境变量自动解锁（绝不写入 .env）。
echo.
echo ============================================================
echo  Z-CMDB 启动中 ...
echo  访问地址: http://%HOST%:%PORT%
echo ============================================================
if not exist "data\keystore.json" (
    echo.
    echo  [首次部署] 数据库尚未加密，需在浏览器完成初始化：
    echo    1. 浏览器打开后进入 Setup 页面
    echo    2. 设置管理员用户名和口令（^>=12位，含大小写+数字+特殊字符）
    echo    3. 系统会生成一次性恢复码 —— 务必立即离线保存！
    echo       恢复码是所有口令丢失时的唯一出路，丢失=数据不可读。
    echo    4. 初始化完成后自动进入正常模式
) else (
    echo.
    echo  [升级启动] 数据库已加密，需解锁后使用：
    echo    - 浏览器打开后输入管理员口令解锁
    echo    - 或设置 CMDB_UNLOCK_PASSWORD 环境变量自动解锁
    echo.
    echo  !! 重要：请确认已备份以下文件 !!
    echo    data\cmdb.db       （加密数据库）
    echo    data\keystore.json （密钥信封，丢失=数据不可读）
    echo    .env               （JWT 密钥配置）
)
echo.
echo ============================================================
if defined CMDB_UNLOCK_PASSWORD echo  [INFO] CMDB_UNLOCK_PASSWORD detected: will auto-unlock on startup.

:: ── 后台：轮询健康检查，就绪后开浏览器，然后自退 ──
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 30;$i++){try{Invoke-WebRequest -UseBasicParsing 'http://%HOST%:%PORT%/api/health' -TimeoutSec 1 | Out-Null; Start-Process 'http://%HOST%:%PORT%'; break}catch{Start-Sleep 1}}"

:: ── 前台运行 uvicorn —— 关闭本窗口即停止服务 ──
echo.
echo ============================================================
echo  Z-CMDB starting at http://%HOST%:%PORT%
echo  浏览器会自动打开；关闭本窗口即停止服务。
echo ============================================================
"%PY%" -m uvicorn app.main:app --host %HOST% --port %PORT% --workers 1
