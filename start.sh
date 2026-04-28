#!/bin/bash

# ==========================================
# AI Academic Polisher - 部署脚本
# 支持 Docker 部署和裸机部署
# ==========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 检查 docker compose
find_compose() {
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        return 1
    fi
}

ACTION=${1:-help}

case $ACTION in

# ==========================================
# Docker 部署命令
# ==========================================
up|start)
    find_compose || error "未找到 docker compose，请先安装 Docker"
    if [ ! -f .env ]; then
        cp .env.server.example .env
        warn "已从 .env.server.example 创建 .env，请先编辑配置再重新运行"
        exit 0
    fi
    echo "正在构建并启动所有容器..."
    $COMPOSE_CMD up -d --build
    info "所有服务已启动"
    echo "  访问地址: http://localhost"
    echo "  查看日志: bash start.sh logs"
    ;;

down|stop)
    find_compose || error "未找到 docker compose"
    $COMPOSE_CMD down
    info "所有服务已停止"
    ;;

restart)
    find_compose || error "未找到 docker compose"
    $COMPOSE_CMD restart
    info "所有服务已重启"
    ;;

logs)
    find_compose || error "未找到 docker compose"
    $COMPOSE_CMD logs -f
    ;;

ps|status)
    find_compose || error "未找到 docker compose"
    $COMPOSE_CMD ps
    ;;

build)
    find_compose || error "未找到 docker compose"
    $COMPOSE_CMD build --no-cache
    info "镜像构建完成"
    ;;

clean)
    find_compose || error "未找到 docker compose"
    read -p "警告: 这将删除所有容器和数据！确认? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        $COMPOSE_CMD down -v --rmi all
        info "清理完成"
    else
        echo "已取消"
    fi
    ;;

# ==========================================
# 裸机部署命令
# ==========================================
init)
    echo "=========================================="
    echo "  裸机部署初始化"
    echo "=========================================="

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        error "未找到 python3，请先安装 Python 3.10+"
    fi
    info "Python3: $(python3 --version)"

    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        error "未找到 node，请先安装 Node.js 18+"
    fi
    info "Node.js: $(node --version)"

    # 复制 .env
    if [ ! -f .env ]; then
        cp .env.server.example .env
        warn "已创建 .env，请编辑其中的数据库密码和 API Key"
    else
        info ".env 已存在，跳过"
    fi

    # 创建虚拟环境
    if [ ! -d venv ]; then
        warn "创建 Python 虚拟环境..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    info "虚拟环境已激活"

    # 安装 Python 依赖
    warn "安装 Python 依赖..."
    pip install -r app/requirements.txt -q
    info "Python 依赖安装完成"

    # 构建前端
    if [ ! -f app/frontend/dist/index.html ]; then
        warn "构建前端..."
        cd app/frontend && npm install --silent && npm run build && cd ../..
    fi
    info "前端构建完成"

    echo ""
    echo "=========================================="
    echo "  初始化完成！"
    echo "  1. 编辑 .env 配置数据库和 API Key"
    echo "  2. 确保 MySQL 和 Redis 已启动"
    echo "  3. 运行: bash start.sh run"
    echo "=========================================="
    ;;

run)
    if [ ! -d venv ]; then
        error "请先运行 bash start.sh init"
    fi
    source venv/bin/activate
    info "启动后端服务..."
    cd app && python main.py
    ;;

# ==========================================
# 帮助
# ==========================================
help|*)
    echo "用法: bash start.sh <command>"
    echo ""
    echo "Docker 部署:"
    echo "  up/start   - 构建并启动所有容器"
    echo "  down/stop  - 停止并删除所有容器"
    echo "  restart    - 重启所有容器"
    echo "  logs       - 查看实时日志"
    echo "  ps/status  - 查看容器状态"
    echo "  build      - 重新构建镜像"
    echo "  clean      - 清理所有容器和数据"
    echo ""
    echo "裸机部署:"
    echo "  init       - 初始化环境 (venv + 依赖 + 前端构建)"
    echo "  run        - 启动服务"
    ;;

esac
