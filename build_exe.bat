@echo off
chcp 65001 >nul 2>&1
title AI Academic Polisher - Build EXE

echo ========================================
echo   AI Academic Polisher - Windows EXE Builder
echo ========================================
echo.

:: ========== Check Node.js ==========
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    echo   https://nodejs.org/
    pause
    exit /b 1
)

:: ========== Build frontend if needed ==========
if not exist "app\frontend\dist\index.html" (
    echo [INFO] Building frontend...
    pushd app\frontend
    call npm install --silent 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed.
        popd
        pause
        exit /b 1
    )
    call npm run build
    if %errorlevel% neq 0 (
        echo [ERROR] Frontend build failed.
        popd
        pause
        exit /b 1
    )
    popd
    echo [OK] Frontend built.
) else (
    echo [OK] Frontend already built, skipping.
)

:: ========== Install PyInstaller if missing ==========
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: ========== Build EXE ==========
echo.
echo Building EXE...
pyinstaller AcademicPolisher.spec --noconfirm --clean

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed. Check the error messages above.
    pause
    exit /b 1
)

:: ========== Copy .env ==========
if exist ".env.desktop.example" (
    copy /Y .env.desktop.example dist\AcademicPolisher\.env >nul
    echo [OK] Copied .env.desktop.example to dist\AcademicPolisher\.env
) else (
    echo [INFO] No .env.desktop.example found. Create .env manually next to AcademicPolisher.exe
)

echo.
echo ========================================
echo   Build complete!
echo   Output: dist\AcademicPolisher\
echo   Usage:
echo     1. Edit dist\AcademicPolisher\.env (set your API key)
echo     2. Double-click dist\AcademicPolisher\AcademicPolisher.exe
echo ========================================
pause
