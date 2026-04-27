#!/bin/bash

# ==========================================
# 0. 进程守护与清理钩子 (Trap)
# ==========================================
cleanup() {
    echo ""
    echo "🛑 收到停止信号，正在安全关闭所有服务..."
    pkill -f "gunicorn" || true
    pkill -f "run_worker.py" || true
    echo "✅ 所有服务已完全停止。期待下次使用！"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "🧹 正在清理可能遗留的旧进程..."
pkill -f "gunicorn" || true
pkill -f "run_worker.py" || true
pkill -f "rq worker" || true

# ==========================================
# 1. 环境初始化
# ==========================================
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT

echo "------------------------------------------"
echo "🚀 AI 极速学术润色系统 - Docker 生产集群内部启动中..."
echo "------------------------------------------"

if [ -f .env ]; then
    REDIS_URL=$(grep REDIS_URL .env | cut -d '=' -f2- | tr -d '\r')
else
    echo "❌ 错误: 找不到 .env 文件，请确保已将其映射入容器中。"
    exit 1
fi

# ==========================================
# 2. 启动 Web 服务端 (基于 Gunicorn/Gthread)
# ==========================================
echo "🌐 正在启动高并发 Web 服务 (多线程模式)..."
gunicorn -k gthread -w 4 --threads 50 -b 0.0.0.0:5000 "main:app" > web_access.log 2> web_error.log &
WEB_PID=$!
echo "✅ Web 服务启动成功 (PID: $WEB_PID)，运行端口: 5000"

# ==========================================
# 3. 启动后台处理引擎 (RQ Workers)
# ==========================================
WORKER_COUNT=16  # 降低 worker 数量，减少 Redis 连接压力 
echo "📍 连接 Redis: $REDIS_URL"
echo "📦 监听队列: ai_tasks"
echo "🔢 即将启动并行 Worker 数量: $WORKER_COUNT"
echo "------------------------------------------"

for i in $(seq 1 $WORKER_COUNT)
do
    # 🟢 致命修复：停止将日志扔进黑洞，改为追加到 worker.log 文件中！
    python run_worker.py >> worker.log 2>&1 &
    sleep 0.5 
done

echo "✅ $WORKER_COUNT 个 Worker 已全部在后台满血待命！"
echo "=========================================="
echo "🎉 生产级环境全面启动成功！支持数十人同时润色排队。"
echo "💡 提示：本窗口已进入守护模式，请勿关闭。"
echo "=========================================="

wait
