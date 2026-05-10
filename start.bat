@echo off
chcp 65001 > nul
title StockBrief

echo.
echo  ===================================
echo   StockBrief 시작
echo  ===================================
echo.

:: 프로젝트 루트 (이 .bat 파일 위치 기준)
set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%frontend

:: 이미 실행 중인지 확인
powershell -Command "try { Invoke-WebRequest http://localhost:8000/health -UseBasicParsing -TimeoutSec 1 | Out-Null; Write-Host '[경고] 백엔드가 이미 실행 중입니다.' } catch {}"

:: ── 백엔드 시작 ──────────────────────────────────────
echo [1/3] 백엔드 서버 시작 중...
start "StockBrief-Backend" /MIN cmd /k "cd /d %BACKEND% && python -m uvicorn api.app:app --host 127.0.0.1 --port 8000"

:: ── 프론트엔드 시작 ──────────────────────────────────
echo [2/3] 프론트엔드 서버 시작 중...
start "StockBrief-Frontend" /MIN cmd /k "cd /d %FRONTEND% && npm run dev"

:: ── 백엔드 준비 대기 (최대 30초) ─────────────────────
echo [3/3] 서버 준비 대기 중...
set /a COUNT=0
:WAIT
timeout /t 1 /nobreak > nul
set /a COUNT+=1
powershell -Command "try { Invoke-WebRequest http://localhost:8000/health -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" > nul 2>&1
if %errorlevel%==0 goto READY
if %COUNT% geq 30 goto TIMEOUT
goto WAIT

:READY
echo.
echo  ===================================
echo   준비 완료!
echo   백엔드  : http://localhost:8000
echo   프론트  : http://localhost:5173
echo  ===================================
echo.
:: 프론트엔드도 완전히 뜰 시간을 2초 더 줌
timeout /t 2 /nobreak > nul
start http://localhost:5173
goto END

:TIMEOUT
echo.
echo  [오류] 백엔드가 30초 안에 응답하지 않았습니다.
echo  백엔드 창에서 오류 메시지를 확인하세요.
echo.

:END
pause
