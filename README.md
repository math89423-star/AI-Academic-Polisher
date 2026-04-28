# AI 极速学术润色系统 (AI Academic Polisher)

专为学术论文打磨而生的高并发 AI 润色系统。前后端分离架构，支持纯文本流式输出和 Word/PDF 文档一键并发润色。内置多套防查重策略，提示词热插拔配置。支持 Linux 服务器部署和 Windows 桌面免配置运行双模式。

---

## 环境要求

### 服务器模式 (Linux)

| 依赖 | 版本 | 说明 |
|------|------|------|
| Linux | Ubuntu/Debian/CentOS | RQ Worker 依赖 `fork()` |
| Python | >= 3.10 | |
| MySQL | >= 8.0 | 需自行安装配置 |
| Redis | >= 6.0 | SSE 推送 + 任务队列 + 取消信号 |
| Node.js | >= 18 | 前端构建 |

### 桌面模式 (Windows/macOS/Linux)

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.10 | |
| Node.js | >= 18 | 仅前端构建时需要 |

桌面模式无需 MySQL、Redis，使用 SQLite + 内存队列自动运行。

---

## 技术栈

**后端**: Flask + SQLAlchemy + RQ (Redis Queue) + Redis Pub/Sub  
**后端 (桌面模式)**: Flask + SQLAlchemy (SQLite) + 内存队列/Pub/Sub  
**前端**: Vue 3 + Pinia + Vite  
**AI**: OpenAI 兼容 API (支持官方/代理/Ollama)  
**部署**: 双模式 — Gunicorn + Nginx (服务器) / Flask 内置服务器 (桌面)

---

## 核心特性

- **双模式部署**: 服务器模式 (MySQL + Redis + RQ) 与桌面模式 (SQLite + 内存队列) 自动切换，Windows 开箱即用
- **高并发引擎**: RQ 任务队列 + ThreadPoolExecutor 并发切片，长文本/大文档处理耗时从分钟级降至秒级
- **Word/PDF 无损润色**: 解析 .docx/.pdf 段落级并发处理，保留原始排版格式
- **SSE 流式输出**: Redis/内存 Pub/Sub 实时推送，打字机效果 + 毫秒级进度反馈
- **防查重策略**: 标准/极致等多套提示词策略，热插拔配置，针对不同查重平台优化
- **管理后台**: 用户管理、API 线路管理、主题配置、批量操作

---

## 架构概览

系统支持两种运行模式，通过 `DEPLOY_MODE` 环境变量控制（默认 `auto`，Windows 自动选择桌面模式）：

### 服务器模式 (server)

```
浏览器 (Vue 3 + Pinia)
  │  HTTP REST + SSE
  ▼
Flask Routes (auth / task / admin)
  │  延迟创建服务实例
  ▼
Services (TaskService / UserService / ApiConfigService)
  │  入队
  ▼
Redis Queue (ai_tasks)
  │
  ▼
RQ Worker → worker_engine.process_task()
  │  工厂模式选择处理器
  ├─ TextTaskProcessor (短文本流式 / 长文本并发切片)
  ├─ DocxTaskProcessor (段落级并发处理)
  └─ PdfTaskProcessor  (PDF 文本提取 + 并发处理)
       │
       ├─ AIService → AIClient → OpenAI API
       ├─ ProgressPublisher → Redis Pub/Sub → SSE → 浏览器
       └─ CancellationChecker → Redis 取消信号
```

### 桌面模式 (desktop)

```
浏览器 (Vue 3 + Pinia)
  │  HTTP REST + SSE
  ▼
Flask Routes (同上)
  │
  ▼
Services → MemoryQueue (内存任务队列)
  │  后台线程执行
  ▼
worker_engine.process_task()
  │  工厂模式选择处理器 (同上)
  │
  ├─ AIService → AIClient → OpenAI API
  ├─ ProgressPublisher → MemoryRedis Pub/Sub → SSE → 浏览器
  └─ CancellationChecker → 内存取消信号
  
数据库: SQLite (自动创建)
```

详细架构图和函数依赖关系见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 项目结构

```
app/
├── main.py                     # Flask 入口
├── run_worker.py               # RQ Worker 入口 (仅服务器模式)
├── backend/
│   ├── __init__.py             # create_app() 工厂
│   ├── config.py               # 配置 + RedisKeyManager + 模式检测
│   ├── extensions.py           # db, redis_client, task_queue
│   ├── memory_backend.py       # MemoryRedis (桌面模式 Redis 替代)
│   ├── memory_queue.py         # MemoryQueue (桌面模式任务队列)
│   ├── prompts_config.py       # 提示词加载
│   ├── worker_engine.py        # 任务分发
│   ├── model/                  # SQLAlchemy 模型
│   ├── routes/                 # API 路由 (auth/task/admin)
│   ├── services/               # 业务逻辑层
│   ├── processors/             # 任务处理器 (text/docx/pdf)
│   │   ├── text_processor.py   # 纯文本处理
│   │   ├── docx_processor.py   # Word 文档处理
│   │   └── pdf_processor.py    # PDF 文档处理
│   └── utils/                  # 工具函数
└── frontend/
    └── src/
        ├── api/index.js        # HTTP + SSE 客户端
        ├── stores/
        │   ├── taskStore.js    # Pinia 状态管理
        │   └── sseManager.js   # SSE 连接管理
        ├── views/              # 页面组件
        └── components/         # UI 组件
```

---

## 快速部署 (服务器模式)

### 1. 安装系统依赖 (Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y redis-server mysql-server libreoffice-core libreoffice-writer
sudo systemctl enable redis-server && sudo systemctl start redis-server
```

### 2. 安装项目依赖

```bash
git clone https://github.com/math89423-star/AIpolish.git
cd AIpolish
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env`:

```ini
APP_PORT=8030

DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ai_polisher

REDIS_URL=redis://:your_redis_password@127.0.0.1:6379/0

ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

### 4. 初始化数据库

```bash
python backend/model/init_db.py
```

### 5. 启动

```bash
bash start_worker.bash
```

---

## Windows 桌面模式

Windows 下无需安装 MySQL、Redis 等外部服务，开箱即用。系统自动检测 Windows 环境并切换为桌面模式。

### 启动步骤

```bash
git clone https://github.com/math89423-star/AIpolish.git
cd AIpolish
pip install -r requirements.txt
cd app
python main.py
```

启动后自动绑定 `127.0.0.1:5000`，SQLite 数据库文件自动创建于项目目录。

### 说明

- 无需设置 `DEPLOY_MODE` 环境变量，Windows 下自动选择 `desktop` 模式
- 如需在 Linux/macOS 上使用桌面模式，设置 `DEPLOY_MODE=desktop`
- 桌面模式使用内存队列替代 Redis Queue，适合单用户本地使用
- 在 `.env` 中配置 `ADMIN_USERNAME`、`ADMIN_PASSWORD` 和 AI API 相关参数即可