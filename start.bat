@echo off
title StockBrief

set ROOT=%~dp0

echo.
echo  ===================================
echo   StockBrief 시작
echo  ===================================
echo.

echo [1/3] 백엔드 서버 시작...
start "StockBrief-Backend" /MIN cmd /k "cd /d "%ROOT%backend" && python -m uvicorn api.app:app --host 127.0.0.1 --port 8000"

echo [2/3] 프론트엔드 서버 시작...
start "StockBrief-Frontend" /MIN cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo [3/3] 서버 준비 대기 중 (10초)...
timeout /t 10 /nobreak > nul

echo.
echo  ===================================
echo   브라우저 오픈: http://localhost:5173
echo  ===================================
echo.
start http://localhost:5173

echo  종료하려면 작업표시줄의
echo  StockBrief-Backend / StockBrief-Frontend 창을 닫으세요.
echo.
pause
