# AI Academic Polisher

> **Disclaimer**: 本工具仅供辅助学术写作与语言润色使用，旨在帮助作者提升论文的表达质量与可读性。使用者应确保最终提交的学术成果符合所在机构的学术诚信规范，本工具不应被用于规避学术诚信审查。因使用本工具产生的任何学术责任由使用者自行承担，开发者不对此承担任何法律责任。

专为学术论文打磨而生的 AI 润色系统。支持纯文本流式输出和 Word/PDF 文档一键并发润色，内置多套润色风格策略，提示词热插拔配置。

---

## 一、项目介绍

### 核心特性

- **双模式部署** — 一套代码自动切换：服务器 (Docker) 与桌面 (EXE)
- **高并发引擎** — RQ 任务队列 + ThreadPoolExecutor 并发切片处理
- **Word/PDF 无损润色** — 段落级并发处理，保留原始排版格式
- **SSE 流式输出** — 实时推送润色结果，打字机效果
- **多风格润色策略** — 标准/深度改写等多套提示词，Markdown 格式热插拔
- **管理后台** — 用户管理、API 线路管理、主题配置、系统设置

### 双模式说明

| 模式 | 适用场景 | 基础设施 |
|------|---------|---------|
| **Server** | Linux 服务器多人使用 | Docker Compose (MySQL + Redis + Nginx)，经测试支持数十人团队协作 |
| **Desktop** | Windows 本地单人使用 | 单 EXE (SQLite + 内存队列)，开箱即用 |

---

## 二、数据实证

> 以下为 **2026 年 4 月最新测试结果**，润色模型为 `gemini-3.1-pro-preview`，润色后提交至主流文本检测平台评估写作自然度。

### PaperPass 检测

润色后 AIGC 识别率从 **75.24%** 降至 **0.41%**

![PaperPass 数据报告](docs/PaperPass数据报告.png)

### 维普检测

润色后 AIGC 识别率从 **42.79%** 降至 **3.34%**

![维普数据报告](docs/维普数据报告.png)

### 朱雀 AI 检测（报告一）

英文润色后 AIGC 识别率从 **100%** 降至 **0%**

![朱雀 AI 检查数据报告 1](docs/朱雀AI检查数据报告1.png)

### 朱雀 AI 检测（报告二）

中文润色后 AIGC 识别率从 **100%** 降至 **0%**

![朱雀 AI 检查数据报告 2](docs/朱雀AI检查数据报告2.png)

---

## 三、安装部署

### Server 模式 (Linux)

#### 前置要求

```bash
# Ubuntu / Debian 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker && sudo systemctl start docker
```

> 其他发行版请参考 [Docker 官方文档](https://docs.docker.com/engine/install/)

#### 部署步骤

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

#### 常用命令

| 命令 | 说明 |
|------|------|
| `bash start.sh up` | 构建并启动所有容器 |
| `bash start.sh down` | 停止并删除容器 |
| `bash start.sh restart` | 重启所有容器 |
| `bash start.sh logs` | 查看实时日志 |
| `bash start.sh ps` | 查看容器状态 |
| `bash start.sh build` | 重新构建镜像 |
| `bash start.sh clean` | 清理所有容器和数据 |

### Desktop 模式 (Windows)

Desktop 模式无需 MySQL、Redis，打包为单个 EXE 目录分发。

#### 前置要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.10 | 打包环境 |
| Node.js | >= 18 | 前端构建 |

#### 打包步骤

```bash
# 1. 克隆仓库
git clone https://github.com/math89423-star/AI-Academic-Polisher.git
cd AI-Academic-Polisher

# 2. 安装 Python 依赖
pip install -r app/requirements.txt

# 3. 一键打包（自动构建前端 + 生成 EXE）
build_exe.bat
```

打包完成后 `dist\AcademicPolisher\` 目录即为可分发产物。

#### 使用方式

1. 将 `.env.desktop.example` 复制到 `dist\AcademicPolisher\.env`
2. 编辑 `.env`，填入你的 AI API Key 和其他配置
3. 双击 `AcademicPolisher.exe` 启动
4. 浏览器自动打开 `http://127.0.0.1:5000`
5. 管理后台 `http://127.0.0.1:5000/admin`

> 默认管理员账号 `admin`，密码 `123456`（在 `.env` 中配置）。
> 如需重置密码，删除 `data\ai_polisher.db` 后重启即可重建。

---

## 四、架构与技术栈

### 技术栈

| 层 | Server 模式 | Desktop 模式 |
|----|------------|-------------|
| 后端 | Flask + SQLAlchemy + RQ + Redis Pub/Sub | Flask + SQLAlchemy (SQLite) + 内存队列/Pub/Sub |
| 前端 | Vue 3 + Pinia + Vite | 同左（打包进 EXE） |
| AI | OpenAI 兼容 API（官方 / 代理 / Ollama） | 同左 |
| 部署 | Docker Compose (Nginx + Gunicorn) | PyInstaller EXE |

### 项目结构

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
│   ├── prompts/                # 提示词文件 (Markdown, 热插拔)
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

> 完整架构图、双模式实现细节、数据流图、代码依赖分析等请查看 **[ARCHITECTURE.md](ARCHITECTURE.md)**

---

## License

本项目基于 [MIT License](LICENSE) 开源。
