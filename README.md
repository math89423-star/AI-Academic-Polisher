# AI 极速学术润色系统 (AI Academic Polisher)

专为学术论文打磨而生的高并发 AI 润色系统。前后端分离架构，支持纯文本流式输出和 Word 文档一键并发润色。内置多套防查重策略，提示词热插拔配置。

---

## 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Linux | Ubuntu/Debian/CentOS | RQ Worker 依赖 `fork()`，不支持 Windows |
| Python | >= 3.10 | |
| MySQL | >= 8.0 | 需自行安装配置 |
| Redis | >= 6.0 | SSE 推送 + 任务队列 + 取消信号 |
| Node.js | >= 18 | 前端构建 |

---

## 技术栈

**后端**: Flask + SQLAlchemy + RQ (Redis Queue) + Redis Pub/Sub  
**前端**: Vue 3 + Pinia + Vite  
**AI**: OpenAI 兼容 API (支持官方/代理/Ollama)  
**部署**: Gunicorn + Nginx

---

## 核心特性

- **高并发引擎**: RQ 任务队列 + ThreadPoolExecutor 并发切片，长文本/大文档处理耗时从分钟级降至秒级
- **Word 无损润色**: 解析 .docx 段落级并发处理，保留原始排版格式
- **SSE 流式输出**: Redis Pub/Sub 实时推送，打字机效果 + 毫秒级进度反馈
- **防查重策略**: 标准/极致等多套提示词策略，热插拔配置，针对不同查重平台优化
- **管理后台**: 用户管理、API 线路管理、主题配置、批量操作

---

## 架构概览

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
  └─ DocxTaskProcessor (段落级并发处理)
       │
       ├─ AIService → AIClient → OpenAI API
       ├─ ProgressPublisher → Redis Pub/Sub → SSE → 浏览器
       └─ CancellationChecker → Redis 取消信号
```

详细架构图和函数依赖关系见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 项目结构

```
app/
├── main.py                     # Flask 入口
├── run_worker.py               # RQ Worker 入口
├── backend/
│   ├── __init__.py             # create_app() 工厂
│   ├── config.py               # 配置 + RedisKeyManager
│   ├── extensions.py           # db, redis_client, task_queue
│   ├── prompts_config.py       # 提示词加载
│   ├── worker_engine.py        # 任务分发
│   ├── model/                  # SQLAlchemy 模型
│   ├── routes/                 # API 路由 (auth/task/admin)
│   ├── services/               # 业务逻辑层
│   ├── processors/             # 任务处理器 (text/docx)
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

## 快速部署

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