# AI Academic Polisher — 架构全景图

> 一套代码，两个灵魂（Server / Desktop 双模式）

## 系统总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户浏览器                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │LoginView │  │MainView  │  │AdminApp  │  │ErrorToast│            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘            │
│       │   ┌─────────┴──────────┐   │                                │
│       │   │ EditorPanel        │   ├─ UserManagementTab             │
│       │   │ ResultPanel        │   ├─ ApiConfigTab                  │
│       │   │ Sidebar            │   ├─ ThemeSettingsTab              │
│       │   │ TopHeader          │   └─ SystemSettingsTab             │
│       │   │ ConfigSwitcher     │                                    │
│       │   └─────────┬──────────┘   │                                │
│       │         taskStore (Pinia)  │                                │
│       └─────────┬──────────────────┘                                │
│            api/index.js                                             │
│         HTTP REST + SSE ↕                                           │
└─────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────────────┐
│  Flask Backend          │                                           │
│  ┌──────────────────────┴──────────────────────────────┐            │
│  │              Routes (Blueprint)                      │            │
│  │  auth.py (/api/auth)                                │            │
│  │  task.py (/api/tasks)                               │            │
│  │  admin.py (/api/admin)                              │            │
│  └──────┬──────────┬──────────┬────────────────────────┘            │
│         │          │          │                                      │
│  ┌──────┴───┐ ┌────┴─────┐ ┌─┴──────────────┐                      │
│  │UserSvc   │ │TaskSvc   │ │ApiConfigSvc    │                      │
│  └──────────┘ └────┬─────┘ └────────────────┘                      │
│                    │ enqueue                                        │
│              ┌─────┴─────┐                                          │
│              │ RQ Queue  │ ←── Redis (ai_tasks)                     │
│              │ [Server]  │     [Desktop: MemoryQueue]               │
│              └─────┬─────┘                                          │
└────────────────────┼────────────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────────────┐
│  RQ Worker [Server] / MemoryQueue Worker Thread [Desktop]           │
│              ┌─────┴──────────┐                                     │
│              │ worker_engine  │                                      │
│              │ process_task() │                                      │
│              └──┬──────────┬──┘                                     │
│     ┌───────────┴──┐  ┌───┴────────────┐  ┌──────────────┐         │
│     │TextProcessor │  │DocxProcessor   │  │PdfProcessor  │         │
│     └──────┬───────┘  └───┬────────────┘  └──────┬───────┘         │
│            └──────┬───────┴──────────────────────┘                  │
│           BaseTaskProcessor                                         │
│            ┌──────┴───────────────────────┐                         │
│     ┌──────┴──────┐  ┌──────────────────┐ │                        │
│     │ AIService   │  │ProgressPublisher │ │                        │
│     │ ┌─────────┐ │  │ (Redis Pub/Sub)  │ │                        │
│     │ │AIClient │ │  └──────────────────┘ │                        │
│     │ │Prompt   │ │  ┌──────────────────┐ │                        │
│     │ │Builder  │ │  │CancellationCheck │ │                        │
│     │ │Response │ │  │ (Redis Signal)   │ │                        │
│     │ │Extractor│ │  └──────────────────┘ │                        │
│     │ │Retry    │ │                       │                        │
│     │ │Policy   │ │                       │                        │
│     │ └─────────┘ │                       │                        │
│     └─────────────┘                       │                        │
└───────────────────────────────────────────┘                        │
                                                                      │
┌─────────────────────────────────────────────────────────────────────┘
│  数据层
│  ┌──────────────────────────────────────────────────────────────────┐
│  │ Server 模式                    │ Desktop 模式                     │
│  ├──────────────────────────────────────────────────────────────────┤
│  │ MySQL                          │ SQLite                          │
│  │  User / Task / ApiConfig /     │  (同表结构, LONGTEXT→Text)       │
│  │  SystemSetting                 │                                 │
│  ├──────────────────────────────────────────────────────────────────┤
│  │ Redis                          │ MemoryRedis (内存字典)            │
│  │  - RQ 任务队列 (ai_tasks)       │  - KV / Hash / Set / PubSub    │
│  │  - Pub/Sub 进度推送             │  - 线程安全 (threading.Lock)     │
│  │  - 取消信号 / 文本哈希 / DOCX标记│                                 │
│  ├──────────────────────────────────────────────────────────────────┤
│  │ RQ Queue (独立 Worker 进程)     │ MemoryQueue (守护线程)           │
│  └──────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
app/
├── main.py                          # Flask 入口
├── run_worker.py                    # RQ Worker 入口
├── backend/
│   ├── __init__.py                  # create_app() 工厂
│   ├── config.py                    # Config / DEPLOY_MODE / WorkerConfig / SSEConfig / RedisConfig
│   ├── extensions.py                # db, redis_client, task_queue (工厂: 按模式创建)
│   ├── memory_backend.py            # MemoryRedis (Desktop 模式内存 Redis 替代)
│   ├── memory_queue.py              # MemoryQueue (Desktop 模式内存任务队列+守护线程)
│   ├── prompts_config.py            # 提示词加载 & 策略配置
│   ├── worker_engine.py             # process_task() 任务分发
│   ├── model/
│   │   ├── models.py                # User, Task, ApiConfig, SystemSetting
│   │   └── init_db.py               # 建表 & 初始数据
│   ├── routes/
│   │   ├── auth.py                  # /api/auth/*
│   │   ├── task.py                  # /api/tasks/*
│   │   └── admin.py                 # /api/admin/*
│   ├── services/
│   │   ├── user_service.py          # 用户认证 & 管理
│   │   ├── task_service.py          # 任务 CRUD & 入队
│   │   ├── api_config_service.py    # API配置解析 & 测试
│   │   ├── ai_service_refactored.py # AI调用 (流式/同步)
│   │   ├── ai_client.py             # OpenAI SDK 封装
│   │   ├── prompt_builder.py        # 提示词构建 & API参数
│   │   ├── response_extractor.py    # AI响应文本提取
│   │   ├── retry_policy.py          # 重试策略
│   │   ├── progress_publisher.py    # Redis Pub/Sub 进度
│   │   └── cancellation_checker.py  # 取消信号检测
│   ├── processors/
│   │   ├── base_processor.py        # 抽象基类 (模板方法)
│   │   ├── text_processor.py        # 文本任务处理
│   │   ├── docx_processor.py        # DOCX任务处理
│   │   └── pdf_processor.py         # PDF任务处理
│   └── utils/
│       ├── helpers.py               # 文本切片, 标题提取
│       ├── docx_service.py          # DOCX读写工具
│       ├── text_hash.py             # 文本去重哈希
│       ├── decorators.py            # @require_admin
│       ├── logging_config.py        # 日志配置
│       └── redis_cleanup.py         # Redis清理
└── frontend/
    └── src/
        ├── main.js / admin.js       # Vue入口
        ├── App.vue / AdminApp.vue   # 根组件
        ├── api/index.js             # HTTP + SSE 客户端
        ├── assets/
        │   ├── style.css            # 主应用样式
        │   └── admin-shared.css     # 管理后台共享样式
        ├── stores/taskStore.js      # Pinia 全局状态
        ├── stores/sseManager.js     # SSE 连接生命周期管理
        ├── views/                   # LoginView, MainView
        └── components/
            ├── admin/               # 管理后台 tab 组件
            │   ├── UserManagementTab.vue
            │   ├── ApiConfigTab.vue
            │   ├── ThemeSettingsTab.vue
            │   └── SystemSettingsTab.vue
            └── (Editor, Result, Sidebar, Header, Config, Toast)
```

## 双模式架构 (DEPLOY_MODE)

> 一套代码，两个灵魂 — 通过 `DEPLOY_MODE` 环境变量自动切换运行模式

### 模式判定

```python
# config.py → _resolve_deploy_mode()
DEPLOY_MODE = env("DEPLOY_MODE", "auto")  # auto / server / desktop
# auto 模式: Windows → desktop, Linux → server
```

### 模式对比

| 维度 | Server 模式 (Linux) | Desktop 模式 (Windows) |
|------|---------------------|------------------------|
| 数据库 | MySQL (LONGTEXT) | SQLite (db.Text) |
| 缓存/消息 | Redis | MemoryRedis (内存字典+Lock) |
| 任务队列 | RQ Queue + 独立 Worker 进程 | MemoryQueue + 守护线程 |
| 启动方式 | Gunicorn + rq worker | Flask threading on 127.0.0.1 |
| 建表 | init_db.py (MySQL CREATE DATABASE) | create_app() 内 db.create_all() |
| 清理 | redis_cleanup.py 定期清理 | 无需清理 (进程退出即释放) |

### 关键实现

```
extensions.py (工厂模式)
  │
  ├─ DEPLOY_MODE == "server"
  │   ├─ redis_client = Redis(host, port, db)
  │   └─ task_queue   = rq.Queue("ai_tasks", connection=redis_client)
  │
  └─ DEPLOY_MODE == "desktop"
      ├─ redis_client = MemoryRedis()        ← memory_backend.py
      └─ task_queue   = MemoryQueue()        ← memory_queue.py

MemoryRedis (memory_backend.py)
  ├─ 线程安全: threading.Lock 保护所有操作
  ├─ KV: get/set/delete/exists/expire/keys
  ├─ Hash: hset/hget/hgetall/hdel
  ├─ Set: sadd/srem/smembers/sismember
  └─ PubSub: publish/subscribe (queue.Queue + threading.Lock)

MemoryQueue (memory_queue.py)
  ├─ 内置 queue.Queue + daemon worker thread
  ├─ enqueue(func, *args) → 放入队列
  ├─ set_app(app) → 注入 Flask app context
  └─ worker loop: 取任务 → with app.app_context(): func(*args)
```

### Desktop 模式启动流程

```
app/main.py
  │
  ├─ create_app()
  │   ├─ SQLAlchemy bind = sqlite:///ai_polisher.db
  │   ├─ db.create_all()  (自动建表)
  │   └─ 自动创建 admin 用户
  │
  ├─ memory_queue.set_app(app)
  ├─ memory_queue.start_worker()  ← 守护线程
  │
  └─ app.run(host="127.0.0.1", threaded=True)
```

## 后端函数依赖图

### 请求处理链路

```
HTTP Request
  │
  ├─ auth.py
  │   ├─ user_login()        → UserService.authenticate_user()  → User model
  │   ├─ admin_login()       → UserService.authenticate_admin() → User model
  │   └─ get_public_theme()  → SystemSetting.query
  │
  ├─ task.py
  │   ├─ create_task()       → TaskService.create_text_task()   → Task model → task_queue.enqueue()
  │   ├─ upload_docx()       → TaskService.create_docx_task()   → Task model → task_queue.enqueue()
  │   ├─ stream_results()    → redis_client.pubsub()            → SSE Generator
  │   ├─ cancel_task()       → TaskService.cancel_task()        → redis_client.set(cancel:*)
  │   ├─ resume_task()       → TaskService.resume_task()        → task_queue.enqueue()
  │   ├─ delete_task()       → TaskService.delete_task()        → db.session.delete()
  │   ├─ delete_all_tasks()  → TaskService.delete_all_tasks()   → 批量删除非进行中任务
  │   ├─ check_duplicate()   → check_duplicate_text()           → redis_client (text_hash:*)
  │   └─ get_strategies()    → UserService.get_user_strategies()
  │
  └─ admin.py
      ├─ CRUD users          → UserService.*
      ├─ CRUD api_configs    → ApiConfigService.*
      └─ theme management    → SystemSetting model
```

### Worker 任务处理链路

```
RQ Worker 接收任务
  │
  worker_engine.process_task(task_id)
  │
  ├─ _get_processor(task)  ─── 工厂方法
  │   ├─ task_type == "text" → TextTaskProcessor
  │   ├─ task_type == "docx" → DocxTaskProcessor
  │   └─ task_type == "pdf"  → PdfTaskProcessor
  │
  └─ processor.run()  ─── 模板方法 (BaseTaskProcessor)
      │
      ├─ initialize_ai_service()
      │   ├─ ApiConfigService.resolve_config(user, strategy)
      │   └─ AIService(api_key, base_url, model)
      │
      ├─ update_task_status("processing")
      │
      ├─ process()  ─── 抽象方法，子类实现
      │   │
      │   ├─ [TextTaskProcessor.process()]
      │   │   ├─ 短文本: _process_short_text()
      │   │   │   └─ ai_service.generate_stream()
      │   │   │       ├─ PromptBuilder.build_prompt()
      │   │   │       ├─ AIClient.create_completion(stream=True)
      │   │   │       ├─ ProgressPublisher.publish_stream()
      │   │   │       └─ ResponseExtractor.extract_clean_text_stream()
      │   │   └─ 长文本: _process_long_text()
      │   │       ├─ split_text_into_chunks()
      │   │       └─ ThreadPoolExecutor → _process_single_chunk() × N
      │   │           ├─ CancellationChecker.is_cancelled()
      │   │           ├─ ai_service.generate_sync()
      │   │           │   ├─ AIClient.create_completion(stream=False)
      │   │           │   └─ ResponseExtractor.extract_clean_text()
      │   │           │       ├─ PromptBuilder.build_extractor_prompt()
      │   │           │       └─ AIClient.create_completion()  ← 二次调用
      │   │           └─ ProgressPublisher.publish_block()
      │   │
      │   └─ [DocxTaskProcessor.process()]
      │       ├─ _extract_paragraphs()
      │       │   └─ is_paragraph_needs_polishing()  (docx_service)
      │       ├─ _process_paragraphs_concurrent()
      │       │   └─ ThreadPoolExecutor → _process_single_paragraph() × N
      │       │       ├─ CancellationChecker.is_cancelled()
      │       │       ├─ ai_service.generate_sync()
      │       │       └─ ProgressPublisher.publish_progress()
      │       ├─ _apply_results()
      │       │   └─ replace_paragraph_text()  (docx_service)
      │       └─ _save_document()
      │
      ├─ update_task_status("completed" / "failed")
      └─ ProgressPublisher.publish_done() / publish_error()
```

### AI 调用内部依赖

```
AIService
  ├─ generate_stream(text, mode, strategy, publisher)
  │   ├─ PromptBuilder.build_prompt(text, mode, strategy)
  │   │   └─ prompts_config.load_strategy_prompt(strategy)
  │   ├─ APIParameterGenerator.get_api_params(strategy)
  │   ├─ RetryPolicy.execute_with_retry(fn, max_retries)
  │   ├─ AIClient.create_completion(messages, stream=True, **params)
  │   │   └─ openai.OpenAI(api_key, base_url).chat.completions.create()
  │   └─ ResponseExtractor.extract_clean_text_stream(chunks)
  │
  └─ generate_sync(text, mode, strategy)
      ├─ PromptBuilder.build_prompt(text, mode, strategy)
      ├─ RetryPolicy.execute_with_retry(fn, max_retries)
      ├─ AIClient.create_completion(messages, stream=False, **params)
      └─ ResponseExtractor.extract_clean_text(raw_text)
          ├─ 正则提取 (优先)
          └─ 回退: PromptBuilder.build_extractor_prompt()
                   → AIClient.create_completion()  ← 二次AI调用
```

## 前端组件依赖图

```
main.js ──→ App.vue
             │
             ├─ 未登录 → LoginView.vue
             │            └─ authAPI.login()
             │
             └─ 已登录 → MainView.vue
                          ├─ TopHeader.vue      ─→ taskStore (用户信息, 登出)
                          ├─ ConfigSwitcher.vue  ─→ taskStore (策略切换)
                          ├─ Sidebar.vue         ─→ taskStore (任务列表, 切换, 删除)
                          ├─ EditorPanel.vue     ─→ taskStore (创建任务, 上传DOCX)
                          └─ ResultPanel.vue     ─→ taskStore (润色结果, 取消, 重试)

admin.js ──→ AdminApp.vue (登录 + Tab切换 + 共享apiConfigs)
             │
             ├─ 未登录 → 登录表单
             │
             └─ 已登录 → Tab 切换
                          ├─ UserManagementTab.vue    ─→ props: apiConfigs, adminUsername
                          ├─ ApiConfigTab.vue         ─→ props: adminUsername, emits: configs-updated
                          ├─ ThemeSettingsTab.vue     ─→ props: adminUsername
                          └─ SystemSettingsTab.vue    ─→ props: adminUsername

taskStore.js (Pinia)
  ├─ State:   tasks{}, currentTaskId, strategies[], eventSource, pendingCount
  ├─ Actions: createTask()    → taskAPI.createTask()    → startSSE()
  │           uploadDocx()    → taskAPI.uploadDocx()    → startSSE()
  │           startSSE()      → taskAPI.connectSSE()    → EventSource (SSE)
  │           cancelTask()    → taskAPI.cancelTask()
  │           resumeTask()    → taskAPI.resumeTask()    → startSSE()
  │           deleteTask()    → taskAPI.deleteTask()
  │           deleteAllTasks()→ taskAPI.deleteAllTasks()
  │           loadHistory()   → taskAPI.getHistory()
  │           loadStrategies()→ taskAPI.getStrategies()
  └─ Polling: startQueuePolling() → taskAPI.getQueueStatus() (每3秒)

api/index.js
  ├─ authAPI:  { login }
  └─ taskAPI:  { getHistory, getStrategies, checkDuplicate,
  │              createTask, uploadDocx, cancelTask, resumeTask,
  │              deleteTask, deleteAllTasks, getQueueStatus, connectSSE }
  └─ 基础URL:  /api/auth/* , /api/tasks/*
```

## 代码耦合分析

### ✅ 已修复的耦合问题

#### 1. **Redis Key 统一管理** (已修复)
```python
# 新增 RedisKeyManager，所有 key 生成集中管理
from backend.config import RedisKeyManager
RedisKeyManager.cancel_key(task_id)
RedisKeyManager.stream_channel(task_id)
RedisKeyManager.progress_key(task_id)
RedisKeyManager.docx_done_key(task_id)
```

#### 2. **ResponseExtractor 优化** (已修复)
```python
# 正则优先提取，仅在正则失败时回退到 AI 二次调用
cleaned = re.sub(r'^(润色结果|结果|输出)[:：]\s*', '', text)
cleaned = re.sub(r'^```[\w]*\n', '', cleaned)
if cleaned and len(cleaned) > 10:
    return cleaned  # 跳过 AI 调用
```

#### 3. **BaseTaskProcessor 依赖注入** (已修复)
```python
# redis_client 通过构造函数注入，不再从 extensions 全局导入
class BaseTaskProcessor(ABC):
    def __init__(self, task, redis_client):
        self.redis_client = redis_client
```

#### 4. **Routes 延迟服务创建** (已修复)
```python
# 不再模块级实例化，改为函数内延迟创建
def _task_service():
    return TaskService()
```

#### 5. **TaskService globals() 移除** (已修复)
```python
# 直接使用 extensions 导入，不再 globals() fallback
self.redis = redis or redis_client
self.queue = queue or task_queue
```

#### 6. **前端 SSE 逻辑抽离** (已修复)
```javascript
// stores/sseManager.js — 独立管理 SSE 生命周期
export function createSSEManager() { ... }
```

---

### ✅ 良好实践

1. **工厂模式**: `worker_engine._get_processor()` 根据任务类型选择处理器; `extensions.py` 根据 DEPLOY_MODE 创建对应后端实例
2. **策略模式**: `TextTaskProcessor` vs `DocxTaskProcessor` 继承 `BaseTaskProcessor`
3. **模板方法**: `BaseTaskProcessor.run()` 定义流程，子类实现 `process()`
4. **观察者模式**: Redis Pub/Sub 解耦进度推送
5. **无循环依赖**: 所有导入关系为有向无环图 (DAG)

---

### 🔧 重构优先级

| 优先级 | 问题 | 影响 | 工作量 |
|--------|------|------|--------|
| P0 | ResponseExtractor 二次调用 | 性能/成本 | 低 |
| P1 | 全局状态依赖 | 可测试性 | 中 |
| P2 | BaseTaskProcessor 拆分 | 可维护性 | 高 |
| P2 | TaskService 拆分 | 可维护性 | 中 |
| P3 | Redis Key 管理 | 可维护性 | 低 |
| P3 | Frontend Store 拆分 | 可维护性 | 中 |

---

## 数据流图

### 文本任务完整流程

```
用户输入文本
  │
  ├─ EditorPanel.vue → taskStore.createTask()
  │                     └─ taskAPI.createTask(username, text, mode, strategy)
  │
  ├─ Flask routes/task.py → create_task()
  │   ├─ check_duplicate_text(text)  → redis_client (text_hash:*)
  │   └─ TaskService.create_text_task()
  │       ├─ extract_title(text)
  │       ├─ Task.create(status="pending")
  │       ├─ store_text_hash(text)
  │       └─ task_queue.enqueue(process_task, task_id)
  │
  ├─ RQ Worker → worker_engine.process_task(task_id)
  │   ├─ TextTaskProcessor.run()
  │   │   ├─ initialize_ai_service()
  │   │   │   └─ ApiConfigService.resolve_config(user, strategy)
  │   │   ├─ update_task_status("processing")
  │   │   ├─ process()
  │   │   │   ├─ 短文本: ai_service.generate_stream()
  │   │   │   │   ├─ ProgressPublisher.publish_stream()
  │   │   │   │   └─ ResponseExtractor.extract_clean_text_stream()
  │   │   │   └─ 长文本: split_text_into_chunks()
  │   │   │       └─ ThreadPoolExecutor.map(_process_single_chunk)
  │   │   │           ├─ ai_service.generate_sync()
  │   │   │           └─ ProgressPublisher.publish_block()
  │   │   ├─ update_task_status("completed")
  │   │   └─ ProgressPublisher.publish_done()
  │   └─ 异常: ProgressPublisher.publish_error()
  │
  └─ Frontend SSE 接收
      ├─ taskAPI.connectSSE(taskId)
      │   └─ EventSource("/api/tasks/stream/{taskId}")
      │       └─ redis_client.pubsub().subscribe(f"progress:{taskId}")
      │
      └─ taskStore 更新
          ├─ event: stream    → 追加 polished_text
          ├─ event: block     → 追加 polished_text
          ├─ event: progress  → 更新进度条
          ├─ event: done      → status = "completed"
          └─ event: error     → status = "failed"
```

### DOCX 任务完整流程

```
用户上传 DOCX
  │
  ├─ EditorPanel.vue → taskStore.uploadDocx()
  │                     └─ taskAPI.uploadDocx(username, file, mode, strategy)
  │
  ├─ Flask routes/task.py → upload_docx()
  │   └─ TaskService.create_docx_task()
  │       ├─ file.save(UPLOAD_FOLDER)
  │       ├─ Task.create(task_type="docx", file_path=path)
  │       └─ task_queue.enqueue(process_task, task_id)
  │
  ├─ RQ Worker → worker_engine.process_task(task_id)
  │   └─ DocxTaskProcessor.run()
  │       ├─ initialize_ai_service()
  │       ├─ process()
  │       │   ├─ _extract_paragraphs()
  │       │   │   └─ is_paragraph_needs_polishing()  (过滤标题/空段)
  │       │   ├─ _process_paragraphs_concurrent()
  │       │   │   └─ ThreadPoolExecutor → _process_single_paragraph() × N
  │       │   │       ├─ 段落切片 (超长段落)
  │       │   │       ├─ ai_service.generate_sync()
  │       │   │       └─ ProgressPublisher.publish_progress()
  │       │   ├─ _apply_results()
  │       │   │   └─ replace_paragraph_text()
  │       │   └─ _save_document(RESULT_FOLDER)
  │       └─ ProgressPublisher.publish_done()
  │
  └─ Frontend 下载结果文件
      └─ ResultPanel.vue → <a :href="task.result_file_path">
```

---

## 关键技术决策

### 1. 为什么用 RQ + Redis 而非 Celery?
- **轻量**: RQ 代码简洁，无需复杂配置
- **Python 原生**: 任务函数直接序列化，无需额外协议
- **Redis 单一依赖**: 不需要 RabbitMQ/Kafka

### 2. 为什么用 SSE 而非 WebSocket?
- **单向推送**: 服务器 → 客户端，无需双向通信
- **自动重连**: EventSource 内置断线重连
- **HTTP 协议**: 无需额外端口，易于部署

### 3. 为什么用 ThreadPoolExecutor 而非 asyncio?
- **OpenAI SDK 同步**: 官方 SDK 基于 requests (同步)
- **简单**: 无需改写为 async/await
- **并发足够**: 长文本切片并发 (5-10 块) 已满足需求

### 4. 为什么用 Redis Pub/Sub 而非数据库轮询?
- **实时性**: 毫秒级延迟
- **解耦**: Worker 和 Flask 无需共享状态
- **扩展性**: 支持多 Worker 并发

### 5. 为什么做 Desktop 双模式而非独立分支?
- **一套代码**: 避免 server/desktop 两个分支长期分叉维护
- **工厂模式切换**: extensions.py 根据 DEPLOY_MODE 创建不同实例，上层代码零感知
- **零外部依赖**: Desktop 模式无需安装 Redis/MySQL，降低 Windows 用户门槛
- **MemoryRedis 接口兼容**: 实现与 redis-py 相同的方法签名，Processor/Publisher 无需修改
- **守护线程替代进程**: MemoryQueue 用 daemon thread 模拟 RQ Worker，单进程即可运行

---

## 安全边界

### 认证授权
```
routes/auth.py
  ├─ user_login()   → session['username'] = username
  └─ admin_login()  → session['admin'] = True

routes/admin.py
  └─ @require_admin  → 检查 session['admin']

routes/task.py
  └─ 检查 session['username']
```

### 文件上传安全
```python
# routes/task.py
ALLOWED_EXTENSIONS = {'docx'}
file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
secure_filename(file.filename)  # 防止路径穿越
```

### SQL 注入防护
```python
# 使用 SQLAlchemy ORM，参数化查询
User.query.filter_by(username=username).first()
```

### XSS 防护
```javascript
// 前端使用 Vue 模板，自动转义
{{ task.polished_text }}  // 自动 HTML 转义
```

---

## 性能瓶颈

### 1. ResponseExtractor 二次调用
**现状**: 同步生成失败时，再次调用 AI 提取文本  
**影响**: 长文本并发处理时，API 调用量翻倍  
**优化**: 使用 JSON mode 或优化提示词

### 2. DOCX 段落串行处理
**现状**: ThreadPoolExecutor 并发度受限于 `max_workers=5`  
**影响**: 大文档 (1000+ 段落) 处理慢  
**优化**: 动态调整并发度，或使用批量 API

### 3. Redis Pub/Sub 单点
**现状**: 所有进度消息通过单个 Redis 实例  
**影响**: 高并发时可能成为瓶颈  
**优化**: Redis Cluster 或消息队列 (Kafka)

---

## 扩展性考虑

### 水平扩展 (Server 模式)
- **Flask**: 多进程 (Gunicorn) + Nginx 负载均衡
- **RQ Worker**: 多实例监听同一队列
- **Redis**: Redis Cluster (分片)

### 垂直扩展
- **数据库**: Desktop SQLite → Server MySQL → PostgreSQL (按需升级)
- **文件存储**: 本地文件 → OSS (对象存储)
- **Desktop → Server**: 修改 DEPLOY_MODE + 迁移数据库即可切换

### 功能扩展
- **多模型支持**: 已支持 (ApiConfig 表)
- **多策略支持**: 已支持 (standard/strict)
- **插件化提示词**: 已实现 (prompts/*.md)

---

## 监控与可观测性

### 日志
```python
# utils/logging_config.py
- Flask 请求日志
- Worker 任务日志
- AI 调用日志 (含耗时)
```

### 指标 (建议添加)
- 任务队列长度 (RQ)
- 任务处理耗时 (P50/P95/P99)
- AI API 调用成功率
- SSE 连接数

### 告警 (建议添加)
- 任务失败率 > 10%
- 队列积压 > 100
- Redis 连接失败

---

## 部署架构

### Server 模式 (Linux)

```
┌─────────────────────────────────────────────────────────────┐
│  Nginx (反向代理)                                            │
│  ├─ /api/*        → Flask (Gunicorn)                        │
│  ├─ /static/*     → 静态文件                                 │
│  └─ /             → Vue SPA (index.html)                    │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│  Flask (Gunicorn)       │                                   │
│  ├─ workers=4           │                                   │
│  ├─ threads=2           │                                   │
│  └─ bind=0.0.0.0:5000   │                                   │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│  RQ Worker × N          │                                   │
│  ├─ rq worker ai_tasks  │                                   │
│  └─ 独立进程，可多实例    │                                   │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│  Redis (单实例 / Cluster)                                    │
│  ├─ RQ 队列                                                  │
│  ├─ Pub/Sub 通道                                             │
│  └─ 缓存 (文本哈希)                                           │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│  MySQL                                                      │
│  ├─ User                                                    │
│  ├─ Task                                                    │
│  ├─ ApiConfig                                               │
│  └─ SystemSetting                                           │
└─────────────────────────────────────────────────────────────┘
```

### Desktop 模式 (Windows)

```
┌─────────────────────────────────────────────────────────────┐
│  单进程 Flask (threaded=True, 127.0.0.1:5000)               │
│                                                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Flask Routes    │  │ MemoryRedis  │  │ MemoryQueue   │  │
│  │ (主线程)        │  │ (内存字典)    │  │ (守护线程)     │  │
│  └────────┬────────┘  └──────────────┘  └───────┬───────┘  │
│           │                                      │          │
│           └──────────── SQLite ──────────────────┘          │
│                      (ai_polisher.db)                        │
└─────────────────────────────────────────────────────────────┘
  无需安装 Redis / MySQL / Nginx，双击即用
```

---

## 总结

### 架构优势
✅ 双模式架构 — 一套代码适配 Server (Linux) 和 Desktop (Windows)  
✅ 清晰的分层架构 (Routes → Services → Processors)  
✅ 异步任务队列 (RQ) 解耦请求和处理  
✅ 实时进度推送 (SSE + Redis Pub/Sub)  
✅ 并发处理 (ThreadPoolExecutor)  
✅ 可扩展的策略系统 (提示词外置)  
✅ 无循环依赖  
✅ RedisKeyManager 统一管理所有 Redis key  
✅ 处理器通过构造函数注入 redis_client  
✅ Routes 使用延迟服务创建，支持测试替换  
✅ ResponseExtractor 正则优先，减少 AI 调用  
✅ 前端 SSE 逻辑抽离为独立 sseManager  

### 已解决的历史问题
~~P0: ResponseExtractor 二次 AI 调用~~ → 正则优先提取，仅回退时调用 AI  
~~P1: 缺乏依赖注入~~ → Routes 延迟创建服务，Processor 构造函数注入  
~~P2: God Object~~ → taskStore SSE 逻辑抽离，BaseTaskProcessor 注入解耦  
~~P3: Redis Key 硬编码~~ → RedisKeyManager 统一管理  
~~globals() hack~~ → TaskService 直接使用 extensions 导入

