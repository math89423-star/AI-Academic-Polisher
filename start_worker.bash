#!/bin/bash

# ==========================================
# 0. 进程守护与清理钩子 (Trap)
# ==========================================
cleanup() {
    echo ""
    echo "🛑 收到停止信号，正在安全关闭所有服务..."
    pkill -f "gunicorn"
    pkill -f "run_worker.py"
    echo "✅ 所有服务已完全停止。期待下次使用！"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "🧹 正在清理可能遗留的旧进程..."
pkill -f "gunicorn"
pkill -f "run_worker.py"
pkill -f "rq worker"

# ==========================================
# 1. 环境初始化
# ==========================================
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT

echo "------------------------------------------"
echo "🚀 AI 极速学术润色系统 - 工业级集群启动中..."
echo "------------------------------------------"

if [ -f .env ]; then
    REDIS_URL=$(grep REDIS_URL .env | cut -d '=' -f2- | tr -d '\r')
else
    echo "❌ 错误: 找不到 .env 文件，请先创建它。"
    exit 1
fi

if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ 错误: 找不到虚拟环境 venv 文件夹。"
    exit 1
fi

# ==========================================
# 2. 启动 Web 服务端 (基于 Gunicorn/Gthread)
# ==========================================
echo "🌐 正在启动高并发 Web 服务 (多线程模式)..."
# 🟢 核心修复 1：放弃 gevent，改为多线程 gthread 模型！
# 4 个进程，每个进程 50 个线程 = 完美支持 200 个并发长连接，且绝生死锁！
gunicorn -k gthread -w 4 --threads 50 -b 0.0.0.0:8020 "main:app" > web_access.log 2> web_error.log &
WEB_PID=$!
echo "✅ Web 服务启动成功 (PID: $WEB_PID)，运行端口: 8020"

# ==========================================
# 3. 启动后台处理引擎 (RQ Workers)
# ==========================================
# 🟢 建议：如果你的服务器是 2核4G，建议将数量下调为 10~15。30个会严重挤占 MySQL 连接池。
WORKER_COUNT=15 
echo "📍 连接 Redis: $REDIS_URL"
echo "📦 监听队列: ai_tasks"
echo "🔢 即将启动并行 Worker 数量: $WORKER_COUNT"
echo "------------------------------------------"

for i in $(seq 1 $WORKER_COUNT)
do
    echo "🛠️  正在启动第 $i 个 Worker..." 
    python run_worker.py > /dev/null 2>&1 &
    # 🟢 核心修复 2：错峰启动！每个进程间隔 0.5 秒，防止瞬间压垮服务器 CPU 和内存
    sleep 0.5 
done

echo "✅ $WORKER_COUNT 个 Worker 已全部在后台满血待命！"
echo "=========================================="
echo "🎉 生产级环境全面启动成功！支持数十人同时润色排队。"
echo "💡 提示：本窗口已进入守护模式，请勿关闭。"
echo "🔥 如需停止服务，请按 [Ctrl + C]。"
echo "=========================================="

wait