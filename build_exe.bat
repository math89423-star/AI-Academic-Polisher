@echo off
title AIpolish - Build EXE

echo ========================================
echo   AIpolish Windows EXE Builder
echo ========================================
echo.

:: Check frontend build
if not exist "app\frontend\dist\index.html" (
    echo [ERROR] Frontend not built. Please run start_windows.bat first, or:
    echo   cd app\frontend ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
)

:: Install PyInstaller if missing
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building...
pyinstaller AIpolish.spec --noconfirm --clean

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed. Check the error messages above.
    pause
    exit /b 1
)

:: Copy .env.desktop.example to output
if exist ".env.desktop.example" (
    copy /Y .env.desktop.example dist\AIpolish\.env >nul
    echo Copied .env.desktop.example to dist\AIpolish\.env
) else (
    echo [INFO] No .env.desktop.example found. Create .env manually next to AIpolish.exe
)

echo.
echo ========================================
echo   Build complete!
echo   Output: dist\AIpolish\
echo   Usage:
echo     1. Edit dist\AIpolish\.env (set your API key)
echo     2. Double-click dist\AIpolish\AIpolish.exe
echo ========================================
pause
