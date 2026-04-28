# AI 极速学术润色系统 (AI Academic Polisher)

专为学术论文打磨而生的 AI 润色系统。支持纯文本流式输出和 Word/PDF 文档一键并发润色。内置多套防查重策略，提示词热插拔配置。

系统支持两种部署模式：
- **Server 模式** — Linux 服务器 Docker 一键部署，MySQL + Redis + Nginx 全栈
- **Desktop 模式** — Windows 打包为 EXE，SQLite + 内存队列，开箱即用

---

## 核心特性

- 双模式部署：服务器 (Docker) 与桌面 (EXE) 自动切换
- 高并发引擎：RQ 任务队列 + ThreadPoolExecutor 并发切片
- Word/PDF 无损润色：段落级并发处理，保留原始排版
- SSE 流式输出：实时推送，打字机效果
- 防查重策略：标准/极致等多套提示词，热插拔配置
- 管理后台：用户管理、API 线路管理、主题配置

---

## Server 模式部署 (Linux)

### 前置要求

在开始之前，请确保服务器已安装 Docker 和 Docker Compose：

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker && sudo systemctl start docker
```

> 其他发行版请参考 [Docker 官方文档](https://docs.docker.com/engine/install/)

### 部署步骤

```bash
# 1. 克隆仓库
git clone https://github.com/math89423-star/AIpolish.git
cd AIpolish

# 2. 启动（首次会自动创建 .env 并提示编辑）
bash start.sh up
```

首次运行会从 `.env.server.example` 自动创建 `.env`，请编辑以下关键配置：

```ini
# 数据库密码（MySQL 容器会自动使用此密码初始化）
DB_PASSWORD=your-db-password

# AI API 配置
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini

# 管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
```

编辑完成后重新运行：

```bash
bash start.sh up
```

启动后访问 `http://服务器IP`，管理后台 `http://服务器IP/admin`。

### 常用命令

| 命令 | 说明 |
|------|------|
| `bash start.sh up` | 构建并启动所有容器 |
| `bash start.sh down` | 停止并删除容器 |
| `bash start.sh restart` | 重启所有容器 |
| `bash start.sh logs` | 查看实时日志 |
| `bash start.sh ps` | 查看容器状态 |
| `bash start.sh build` | 重新构建镜像 |
| `bash start.sh clean` | 清理所有容器和数据 |

---

## Desktop 模式部署 (Windows)

Desktop 模式无需 MySQL、Redis，打包为单个 EXE 分发。

### 前置要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.10 | 打包环境 |
| Node.js | >= 18 | 前端构建 |

### 打包步骤

```bash
# 1. 克隆仓库
git clone https://github.com/math89423-star/AIpolish.git
cd AIpolish

# 2. 一键打包（自动构建前端 + 生成 EXE）
build_exe.bat
```

打包完成后 `dist\AIpolish\` 目录即为可分发产物。

### 使用方式

1. 编辑 `dist\AIpolish\.env`，填入 API Key
2. 双击 `AIpolish.exe` 启动
3. 浏览器访问 `http://127.0.0.1:5000`
4. 管理后台 `http://127.0.0.1:5000/admin`

> 默认管理员账号密码在 `.env` 中配置，首次启动自动创建。如需修改密码，删除 `data\ai_polisher.db` 后重启即可重建。

---

## 技术栈

**后端**: Flask + SQLAlchemy + RQ (Redis Queue) + Redis Pub/Sub
**后端 (桌面模式)**: Flask + SQLAlchemy (SQLite) + 内存队列/Pub/Sub
**前端**: Vue 3 + Pinia + Vite
**AI**: OpenAI 兼容 API (支持官方/代理/Ollama)
**部署**: Docker Compose (服务器) / PyInstaller EXE (桌面)

---

## 项目结构

```
app/
├── main.py                     # Flask 入口
├── run_worker.py               # RQ Worker 入口 (仅服务器模式)
├── backend/
│   ├── __init__.py             # create_app() 工厂
│   ├── config.py               # 配置 + 模式检测
│   ├── extensions.py           # db, redis_client, task_queue
│   ├── paths.py                # 路径管理 (打包/运行时)
│   ├── memory_backend.py       # MemoryRedis (桌面模式)
│   ├── memory_queue.py         # MemoryQueue (桌面模式)
│   ├── worker_engine.py        # 任务分发
│   ├── model/                  # SQLAlchemy 模型
│   ├── routes/                 # API 路由 (auth/task/admin)
│   ├── services/               # 业务逻辑层
│   ├── processors/             # 任务处理器 (text/docx/pdf)
│   └── utils/                  # 工具函数
└── frontend/
    └── src/
        ├── api/index.js        # HTTP + SSE 客户端
        ├── stores/             # Pinia 状态管理
        ├── views/              # 页面组件
        └── components/         # UI 组件
```
