@echo off
title StockBrief

set ROOT=%~dp0

echo.
echo  === StockBrief Starting ===
echo.

echo [1/3] Starting backend...
start "StockBrief-Backend" /MIN cmd /k "cd /d %ROOT%backend && python -m uvicorn api.app:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting frontend...
start "StockBrief-Frontend" /MIN cmd /k "cd /d %ROOT%frontend && npm run dev"

echo [3/3] Waiting 10 seconds...
timeout /t 10 /nobreak > nul

echo.
echo  Opening http://localhost:5173
echo.
start http://localhost:5173

echo  To stop: close StockBrief-Backend and StockBrief-Frontend windows.
echo.
pause
