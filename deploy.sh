#!/bin/bash

echo "====================================================="
echo "  🚀 AI 极速学术润色系统 (Docker 全栈集群) 全量部署"
echo "====================================================="

if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件！请先配置好参数。"
    exit 1
fi

echo "📁 检查并创建数据持久化目录..."
mkdir -p outputs uploads mysql_data redis_data

echo "🛑 停止并清理旧集群..."
docker compose down

echo "📦 正在拉起集群..."
docker compose up -d --build

# 🟢 优化：删除了 sleep 15，直接让 Python 脚本自己去智能等待 MySQL
echo "🛠️ 正在执行系统数据初始化..."
docker exec -it aipolish_server python backend/model/init_db.py

echo "====================================================="
echo "🎉 全量部署大功告成！"
echo "====================================================="