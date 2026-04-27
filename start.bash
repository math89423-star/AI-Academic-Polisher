#!/bin/bash

# ==========================================
# AIpolish 统一启动脚本
# ==========================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "🚀 AI 极速学术润色系统 - 启动中..."
echo "=========================================="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 错误: 找不到 .env 文件"
    exit 1
fi

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ 错误: Docker 未运行，请先启动 Docker"
    exit 1
fi

# 启动 Docker Compose
echo "📦 正在启动 Docker 容器..."
docker-compose up -d

echo ""
echo "=========================================="
echo "✅ 系统启动成功！"
echo "=========================================="
echo "📍 后端 API: http://localhost:5000"
echo "📍 前端界面: http://localhost:5173"
echo "📍 MySQL: localhost:3306"
echo "📍 Redis: localhost:6379"
echo ""
echo "💡 查看日志: docker-compose logs -f"
echo "💡 停止服务: docker-compose down"
echo "=========================================="
