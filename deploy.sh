#!/bin/bash
# 赋予脚本执行权限：chmod +x deploy.sh

echo "====================================================="
echo "  🚀 AI 极速学术润色系统 (Docker 全栈集群) 一键部署"
echo "====================================================="

if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件！请先创建 .env 文件并配置好参数。"
    exit 1
fi

echo "📁 检查并创建数据持久化目录..."
mkdir -p outputs uploads mysql_data redis_data

if ! command -v docker &> /dev/null; then
    echo "❌ 未检测到 Docker，请先安装 Docker 环境!"
    exit 1
fi

echo "🛑 停止并清理正在运行的旧集群..."
docker compose down

echo "📦 正在构建并启动服务 (MySQL, Redis, AIPolish-App)..."
docker compose up -d --build

echo "⏳ 等待 MySQL 数据库引擎就绪 (约 15 秒)..."
sleep 15

echo "🛠️ 正在执行系统数据初始化 (建库建表与注入管理员)..."
docker exec -it aipolish_server python backend/model/init_db.py

echo "====================================================="
echo "🎉 部署大功告成！全栈服务已在后台稳定运行。"
echo "🌐 Web 访问地址: 你的服务器IP:8020"
echo "====================================================="