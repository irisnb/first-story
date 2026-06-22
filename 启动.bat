@echo off
chcp 65001 >nul
echo ========================================
echo   First Story - Starting...
echo ========================================
echo.

:: Start backend
echo [1/3] Starting backend...
cd /d "%~dp0backend"
start /b python -m uvicorn app.main:app --reload --port 8000 >nul 2>&1

:: Start frontend
echo [2/3] Starting frontend...
cd /d "%~dp0frontend"
start /b npm run dev >nul 2>&1

:: Wait for services
echo [3/3] Waiting for services...
timeout /t 5 /nobreak >nul

:: Open browser
echo Opening browser...
start http://localhost:5173

echo.
echo ========================================
echo   Done! Browser opened.
echo ========================================
echo.
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API:      http://localhost:8000/docs
echo.
echo   Close this window will NOT stop services.
echo.
pause
