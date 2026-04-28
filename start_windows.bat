@echo off
chcp 65001 >nul 2>&1
title AI 学术润色系统 - 启动中...

echo ============================================
echo    AI 学术润色系统 - Windows 一键启动
echo ============================================
echo.

:: ========== 检测 Python ==========
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10 以上版本
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ========== 创建虚拟环境 ==========
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo [信息] 首次运行，正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [OK] 虚拟环境创建完成
    set FIRST_RUN=1
) else (
    set FIRST_RUN=0
)

:: ========== 激活虚拟环境 ==========
call venv\Scripts\activate.bat

:: ========== 安装 Python 依赖 ==========
if "%FIRST_RUN%"=="1" (
    echo.
    echo [信息] 正在安装 Python 依赖（首次较慢，请耐心等待）...
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [错误] Python 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo [OK] Python 依赖安装完成
)

:: ========== 构建前端 ==========
if not exist "app\frontend\dist\index.html" (
    echo.
    echo [信息] 正在构建前端页面...

    where node >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未检测到 Node.js，请先安装 Node.js 18 以上版本
        echo 下载地址: https://nodejs.org/
        pause
        exit /b 1
    )

    pushd app\frontend
    call npm install --silent 2>nul
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败
        popd
        pause
        exit /b 1
    )
    call npm run build
    if %errorlevel% neq 0 (
        echo [错误] 前端构建失败
        popd
        pause
        exit /b 1
    )
    popd
    echo [OK] 前端构建完成
) else (
    echo [OK] 前端已构建，跳过
)

:: ========== 启动服务 ==========
echo.
echo ============================================
echo    启动完成！正在打开浏览器...
echo    访问地址: http://127.0.0.1:5000
echo    管理后台: http://127.0.0.1:5000/admin
echo    按 Ctrl+C 停止服务
echo ============================================
echo.

set DEPLOY_MODE=desktop
start http://127.0.0.1:5000
cd app
python main.py

pause
