#!/bin/bash

# ==========================================
# 测试环境专属启动脚本 (绝对隔离生产环境)
# ==========================================

cleanup() {
    echo ""
    echo "🛑 收到停止信号，正在安全关闭【测试环境】..."
    pkill -f "gunicorn.*8030"
    pkill -f "run_worker_test.py"
    echo "✅ 测试服务已完全停止，生产环境未受影响！"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "🧹 正在清理可能遗留的测试进程..."
pkill -f "gunicorn.*8030"
pkill -f "run_worker_test.py"

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT

echo "------------------------------------------"
echo "🧪 AI 极速学术润色系统 - 【测试沙盒】启动中..."
echo "------------------------------------------"

if [ -f .env ]; then
    REDIS_URL=$(grep REDIS_URL .env | cut -d '=' -f2- | tr -d '\r')
else
    echo "❌ 错误: 找不到 .env 文件"
    exit 1
fi

source venv/bin/activate

# ==========================================
# 启动测试 Web 服务 (运行在 8030 端口)
# ==========================================
echo "🌐 正在启动测试 Web 服务 (端口 8030)..."
# 测试环境不需要开太多资源，2个进程即可
gunicorn -k gthread -w 2 --threads 10 -b 0.0.0.0:8030 "main:app" > test_web_access.log 2> test_web_error.log &
WEB_PID=$!
echo "✅ 测试 Web 启动成功 (PID: $WEB_PID)"

# ==========================================
# 启动测试 Worker (运行 run_worker_test.py)
# ==========================================
WORKER_COUNT=3 # 测试环境开3个 Worker 就够了
echo "📍 连接测试 Redis: $REDIS_URL"

for i in $(seq 1 $WORKER_COUNT)
do
    # 🟢 调用重命名后的专属脚本
    python run_worker_test.py > /dev/null 2>&1 &
    sleep 0.5 
done

echo "✅ $WORKER_COUNT 个测试 Worker 已就绪！"
echo "=========================================="
echo "🎉 测试沙盒启动成功！请通过 http://你的IP:8030 访问。"
echo "🔥 按 [Ctrl + C] 仅关闭测试环境。"
echo "=========================================="

wait