@echo off
chcp 65001 >nul
echo ========================================
echo   First Story - Stopping services
echo ========================================
echo.

:: Kill frontend dev server (port 5173)
echo [1/2] Stopping frontend server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo       Killed PID %%a
)

:: Kill backend server (port 8000)
echo [2/2] Stopping backend server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo       Killed PID %%a
)

echo.
echo ========================================
echo   Services stopped.
echo ========================================
echo   Browser tabs may still be open.
echo   Close them manually if needed.
echo ========================================
echo.
pause
