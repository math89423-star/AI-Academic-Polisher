# Docker 部署指南

## 架构说明

本项目采用多容器架构，各服务独立部署：

```
┌─────────────────────────────────────────────┐
│              Nginx Gateway                  │
│         (端口 80, 8080)                     │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────┐
│   Frontend  │  │   Backend   │
│  (Node.js)  │  │  (Python)   │
│   Nginx     │  │  Gunicorn   │
└─────────────┘  └──────┬──────┘
                        │
                ┌───────┴────────┐
                │                │
         ┌──────▼──────┐  ┌──────▼──────┐
         │    MySQL    │  │    Redis    │
         │  (数据库)   │  │   (缓存)    │
         └─────────────┘  └─────────────┘
```

## 容器列表

| 容器名称 | 服务 | 端口 | 说明 |
|---------|------|------|------|
| academic-polisher_nginx | Nginx | 80, 8080 | 反向代理和静态文件服务 |
| academic-polisher_frontend | Frontend | 内部 | Vue 3 前端应用 |
| academic-polisher_backend | Backend | 5000 | Flask API + RQ Workers |
| academic-polisher_mysql | MySQL | 3306 | 数据库 |
| academic-polisher_redis | Redis | 6379 | 任务队列和缓存 |

## 快速启动

### 1. 一键启动（推荐）

```bash
./docker.sh up
```

### 2. 手动启动

```bash
docker-compose up -d --build
```

## 常用命令

```bash
# 启动所有服务
./docker.sh up

# 停止所有服务
./docker.sh down

# 重启服务
./docker.sh restart

# 查看日志
./docker.sh logs

# 查看容器状态
./docker.sh ps

# 重新构建镜像
./docker.sh build

# 清理所有数据（危险操作）
./docker.sh clean
```

## 单独操作容器

```bash
# 重启单个容器
docker-compose restart backend
docker-compose restart frontend

# 查看单个容器日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 进入容器
docker exec -it academic-polisher_backend bash
docker exec -it academic-polisher_frontend sh

# 重新构建单个容器
docker-compose build --no-cache backend
docker-compose up -d backend
```

## 文件结构

```
.
├── Dockerfile.backend          # 后端 Dockerfile
├── Dockerfile.frontend         # 前端 Dockerfile
├── docker-compose.yml          # 容器编排配置
├── docker.sh                   # 一键启动脚本
├── docker-backend.sh           # 后端容器启动脚本
├── nginx/
│   └── nginx.conf             # Nginx 配置
├── app/
│   ├── backend/               # 后端源码
│   └── frontend/              # 前端源码
└── .env                       # 环境变量配置
```

## 环境变量配置

确保 `.env` 文件包含以下配置：

```env
# 数据库配置
DB_HOST=mysql
DB_PORT=3306
DB_NAME=academic-polisher
DB_USER=root
DB_PASSWORD=your_password

# Redis 配置
REDIS_URL=redis://redis:6379/0

# API 配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 端口说明

- **80**: 生产环境访问端口（前端 + API）
- **8080**: 开发环境访问端口（支持热重载）
- **5000**: 后端 API 直接访问（仅内部）
- **3306**: MySQL 数据库
- **6379**: Redis 缓存

## 访问地址

- 生产环境: http://localhost
- 开发环境: http://localhost:8080
- 后端 API: http://localhost/api/
- 健康检查: http://localhost/health

## 故障排查

### 1. 容器无法启动

```bash
# 查看容器日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器状态
docker-compose ps
```

### 2. 前端无法访问后端

检查 nginx 配置中的 upstream 是否正确：
- `academic-polisher_backend:5000` (后端)
- `academic-polisher_frontend:80` (前端)

### 3. 数据库连接失败

确保 `.env` 中的 `DB_HOST=mysql`（容器名称）

### 4. Redis 连接失败

确保 `.env` 中的 `REDIS_URL=redis://redis:6379/0`（容器名称）

### 5. 重新构建镜像

```bash
# 清理旧镜像
docker-compose down
docker-compose build --no-cache

# 重新启动
docker-compose up -d
```

## 数据持久化

以下目录会持久化到宿主机：

- `./mysql_data` - MySQL 数据
- `./redis_data` - Redis 数据
- `./uploads` - 上传文件
- `./outputs` - 输出文件
- `./logs` - 日志文件

## 性能优化

### 后端 Worker 数量

编辑 `docker-backend.sh` 中的 `WORKER_COUNT` 变量：

```bash
WORKER_COUNT=16  # 根据服务器性能调整
```

### Gunicorn 配置

编辑 `docker-backend.sh` 中的 gunicorn 参数：

```bash
gunicorn -k gthread -w 4 --threads 50 -b 0.0.0.0:5000 "main:app"
```

## 开发模式

如需在开发模式下运行前端（支持热重载）：

1. 在宿主机启动前端开发服务器：
```bash
cd app/frontend
npm run dev
```

2. 访问 http://localhost:8080（Nginx 会代理到开发服务器）

## 生产部署建议

1. 使用环境变量管理敏感信息
2. 配置 HTTPS（修改 nginx.conf）
3. 设置合适的资源限制（docker-compose.yml）
4. 定期备份数据库和 Redis
5. 配置日志轮转
6. 监控容器健康状态

## 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
./docker.sh build
./docker.sh up
```
