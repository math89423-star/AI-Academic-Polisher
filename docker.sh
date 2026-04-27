#!/bin/bash

# ==========================================
# Docker Compose 一键启动脚本
# ==========================================

set -e

echo "=========================================="
echo "🚀 AI 极速学术润色系统 - Docker 部署脚本"
echo "=========================================="

# 检查 docker-compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: 未找到 docker-compose 或 docker compose 命令"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 使用 docker compose 或 docker-compose
COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
fi

# 解析命令行参数
ACTION=${1:-up}

case $ACTION in
    up|start)
        echo "📦 正在构建并启动所有容器..."
        $COMPOSE_CMD up -d --build
        echo ""
        echo "✅ 所有服务已启动！"
        echo "🌐 访问地址: http://localhost"
        echo "📊 查看日志: $COMPOSE_CMD logs -f"
        ;;

    down|stop)
        echo "🛑 正在停止所有容器..."
        $COMPOSE_CMD down
        echo "✅ 所有服务已停止"
        ;;

    restart)
        echo "🔄 正在重启所有容器..."
        $COMPOSE_CMD restart
        echo "✅ 所有服务已重启"
        ;;

    logs)
        echo "📋 查看实时日志 (Ctrl+C 退出)..."
        $COMPOSE_CMD logs -f
        ;;

    ps|status)
        echo "📊 容器运行状态:"
        $COMPOSE_CMD ps
        ;;

    build)
        echo "🔨 重新构建所有镜像..."
        $COMPOSE_CMD build --no-cache
        echo "✅ 镜像构建完成"
        ;;

    clean)
        echo "🧹 清理所有容器、镜像和数据卷..."
        read -p "⚠️  警告: 这将删除所有数据！确认继续? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            $COMPOSE_CMD down -v --rmi all
            echo "✅ 清理完成"
        else
            echo "❌ 已取消"
        fi
        ;;

    *)
        echo "用法: $0 {up|down|restart|logs|ps|build|clean}"
        echo ""
        echo "命令说明:"
        echo "  up/start   - 构建并启动所有容器"
        echo "  down/stop  - 停止并删除所有容器"
        echo "  restart    - 重启所有容器"
        echo "  logs       - 查看实时日志"
        echo "  ps/status  - 查看容器状态"
        echo "  build      - 重新构建镜像"
        echo "  clean      - 清理所有容器和数据"
        exit 1
        ;;
esac
