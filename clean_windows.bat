@echo off
chcp 65001 >nul 2>&1
title AI 学术润色系统 - 卸载清理

echo ============================================
echo    AI 学术润色系统 - 卸载清理工具
echo ============================================
echo.
echo 本工具仅清理以下内容：
echo   - venv\          (Python 虚拟环境)
echo   - app\frontend\node_modules\  (前端依赖)
echo   - app\frontend\dist\          (前端构建产物)
echo   - app\data\                   (SQLite 数据库)
echo   - __pycache__                 (Python 缓存)
echo.
echo 不会删除：
echo   - 系统 Python / Node.js 环境
echo   - 项目源代码
echo   - 你的 .env 配置文件
echo   - uploads / outputs 目录中的文件
echo.

set /p CONFIRM=确认清理以上内容？(Y/N):
if /i not "%CONFIRM%"=="Y" (
    echo 已取消。
    pause
    exit /b 0
)

echo.

:: ========== 删除虚拟环境 ==========
if exist "venv" (
    echo [清理] 删除 venv\ ...
    rmdir /s /q "venv"
    echo [OK] 虚拟环境已删除
) else (
    echo [跳过] venv\ 不存在
)

:: ========== 删除前端依赖 ==========
if exist "app\frontend\node_modules" (
    echo [清理] 删除 app\frontend\node_modules\ ...
    rmdir /s /q "app\frontend\node_modules"
    echo [OK] 前端依赖已删除
) else (
    echo [跳过] node_modules\ 不存在
)

:: ========== 删除前端构建产物 ==========
if exist "app\frontend\dist" (
    echo [清理] 删除 app\frontend\dist\ ...
    rmdir /s /q "app\frontend\dist"
    echo [OK] 前端构建产物已删除
) else (
    echo [跳过] dist\ 不存在
)

:: ========== 删除 SQLite 数据库 ==========
if exist "app\data" (
    echo [清理] 删除 app\data\ ...
    rmdir /s /q "app\data"
    echo [OK] SQLite 数据库已删除
) else (
    echo [跳过] app\data\ 不存在
)

:: ========== 删除 Python 缓存 ==========
echo [清理] 清除 __pycache__ ...
for /d /r "app" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)
echo [OK] Python 缓存已清除

echo.
echo ============================================
echo    清理完成！下次双击 start_windows.bat
echo    会重新安装所有依赖。
echo ============================================
pause
