# AI Academic Polisher

专为学术论文打磨而生的 AI 润色系统。支持纯文本流式输出和 Word/PDF 文档一键并发润色，内置多套防查重策略，提示词热插拔配置。

系统支持两种部署模式：
- **Server 模式** — Linux 服务器 Docker 一键部署，MySQL + Redis + Nginx 全栈
- **Desktop 模式** — Windows 打包为 EXE，SQLite + 内存队列，开箱即用

> 架构详情请参阅 [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 核心特性

- 双模式部署：服务器 (Docker) 与桌面 (EXE) 一套代码自动切换
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
git clone https://github.com/math89423-star/AI-Academic-Polisher.git
cd AI-Academic-Polisher

# 2. 启动（首次会自动创建 .env 并提示编辑）
bash start.sh up
```

首次运行会从 `.env.server.example` 自动创建 `.env`，请编辑以下关键配置：

```ini
# 数据库密码（MySQL 容器会自动使用此密码初始化）
DB_PASSWORD=your-db-password

# AI API 配置（支持 OpenAI 官方 / 代理 / Ollama）
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini

# 管理员账号（首次启动自动创建，默认密码 123456）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=123456
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

Desktop 模式无需 MySQL、Redis，打包为单个 EXE 目录分发。

### 前置要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.10 | 打包环境 |
| Node.js | >= 18 | 前端构建 |

### 打包步骤

```bash
# 1. 克隆仓库
git clone -b dev https://github.com/math89423-star/AI-Academic-Polisher.git
cd AI-Academic-Polisher

# 2. 安装 Python 依赖
pip install -r app/requirements.txt

# 3. 一键打包（自动构建前端 + 生成 EXE）
# Windows 下双击 build_exe.bat，或在命令行运行：
build_exe.bat
```

打包完成后 `dist\AcademicPolisher\` 目录即为可分发产物。

### 使用方式

1. 将 `.env.desktop.example` 复制到 `dist\AcademicPolisher\.env`
2. 编辑 `.env`，填入你的 AI API Key 和其他配置
3. 双击 `AcademicPolisher.exe` 启动
4. 浏览器自动打开 `http://127.0.0.1:5000`
5. 管理后台 `http://127.0.0.1:5000/admin`

> 默认管理员账号 `admin`，密码 `123456`（在 `.env` 中配置）。
> 如需重置密码，删除 `data\ai_polisher.db` 后重启即可重建。

---

## 技术栈

| 层 | Server 模式 | Desktop 模式 |
|----|------------|-------------|
| 后端 | Flask + SQLAlchemy + RQ + Redis Pub/Sub | Flask + SQLAlchemy (SQLite) + 内存队列/Pub/Sub |
| 前端 | Vue 3 + Pinia + Vite | 同左（打包进 EXE） |
| AI | OpenAI 兼容 API（官方 / 代理 / Ollama） | 同左 |
| 部署 | Docker Compose | PyInstaller EXE |

---

## 项目结构

```
app/
├── main.py                     # Flask 入口
├── run_worker.py               # RQ Worker 入口 (仅 Server 模式)
├── backend/
│   ├── __init__.py             # create_app() 工厂
│   ├── config.py               # 配置 + 模式检测
│   ├── extensions.py           # db, redis_client, task_queue
│   ├── paths.py                # 路径管理 (打包/运行时)
│   ├── memory_backend.py       # MemoryRedis (Desktop 模式)
│   ├── memory_queue.py         # MemoryQueue (Desktop 模式)
│   ├── worker_engine.py        # 任务分发
│   ├── prompts_config.py       # 提示词加载 & 策略配置
│   ├── prompts/                # 提示词文件 (Markdown 格式，热插拔)
│   │   ├── cn_standard.md      # 中文标准润色
│   │   ├── cn_strict.md        # 中文极致降重
│   │   ├── en_standard.md      # 英文标准润色
│   │   ├── en_strict.md        # 英文极致降重
│   │   ├── extractor.md        # 结果提取提示词
│   │   └── continuation.md     # 续写提示词
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

### 自定义提示词

提示词以 Markdown 文件存放在 `app/backend/prompts/` 目录下，修改后无需重启即可生效。策略在 `prompts_config.py` 中注册，每个策略指定中英文各一个提示词文件。
