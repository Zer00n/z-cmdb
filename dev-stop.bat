@echo off
chcp 65001 >nul
title CMDB Lite 停止服务

echo 正在停止 CMDB Lite 开发服务...

:: 关闭后端（uvicorn 进程）
taskkill /FI "WINDOWTITLE eq CMDB-Backend*" /F >nul 2>&1

:: 关闭前端（vite 进程）
taskkill /FI "WINDOWTITLE eq CMDB-Frontend*" /F >nul 2>&1

echo 服务已停止。
timeout /t 1 /nobreak >nul
