# 🚀 AI 极速学术润色系统 (AI Academic Polisher)

这是一个专为学术论文打磨而生的工业级、高并发 AI 润色系统。系统采用了现代化的前后端分离架构，支持纯文本的流式打字机输出，以及 **Word 文档（.docx）一键解析、并发润色与无损重排**。内置多套防查重应对策略，为用户提供极致的去 AI 化体验。

---

## 🛑 极其重要的前置环境警告 (READ ME FIRST)

在开始部署之前，请务必确认您的环境满足以下**硬性要求**，否则系统将绝对无法运行：

1. 🐧 **仅限 Linux 环境**：
   本系统的核心并发调度引擎使用了 `python-rq` (Redis Queue)。该库在底层强依赖 Linux 操作系统的 `fork()` 机制来创建子进程执行任务。**请绝对不要在 Windows 环境下运行本系统的后台 Worker，否则会导致进程崩溃或无法处理任务！** 强烈建议使用 Ubuntu、Debian 或 CentOS 系统进行部署。
2. 🗄️ **必须自行配置 MySQL 与 Redis**：
   本项目代码**不包含**数据库的自动化安装脚本。在运行任何 Python 代码之前，您**必须自行在服务器上安装、配置并启动 MySQL (8.0+) 和 Redis (6.0+)**。如果 Redis 没有在后台运行，所有的 SSE 流式推送和并发任务队列都会瞬间瘫痪。

---

## ✨ 核心特性

* **⚡ 极速高并发引擎**：针对长篇 Word 文档，底层采用 RQ 任务队列 + `ThreadPoolExecutor` (默认 15 并发)，将数万字论文切片并发请求，耗时从数分钟缩减至十秒级。
* **📄 Word 物理隔离解析**：底层调用 `LibreOffice Headless` 自动清洗各种来源不明、格式畸形的 `.docx` 或 WPS 文档。彻底过滤图表、公式，仅对正文进行提取和覆盖，**绝对不破坏原有的复杂排版**。
* **🌊 SSE 流式丝滑输出**：利用 Redis Pub/Sub 技术，突破传统 HTTP 阻塞，实现 AI 文本生成过程的实时流式推送（打字机效果）与毫秒级进度反馈。
* **🛡️ 灵活的防查重策略**：内置“标准平衡”、“极致降重”、“保守润色”等多套提示词策略，可热插拔式配置，精准狙击知网、Turnitin 等不同查重平台的检测算法。
* **🧪 双轨物理隔离架构**：自带生产环境 (`start_worker.bash`) 与测试沙盒 (`test/start_test.bash`) 启动脚本，端口、数据库、Redis 缓存库完美隔离，杜绝测试数据污染生产线。

---

## 🛠️ 保姆级部署指南

### 第一步：系统级底层依赖安装 (以 Ubuntu 为例)
在克隆代码之前，请先在您的 Linux 服务器上安装好必备的基础设施：

```bash
# 1. 更新系统包
sudo apt-get update

# 2. 安装 Redis 服务 (必须)
sudo apt-get install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 3. 安装 MySQL 服务 (必须)
sudo apt-get install -y mysql-server
# 安装完成后，请自行登录 MySQL 创建数据库账号和密码

# 4. 安装 LibreOffice (必须！用于系统自动修复畸形 Word 文档)
sudo apt-get install -y libreoffice-core libreoffice-writer
```
### 第二步：获取代码与安装 Python 依赖
请确保您的 Python 版本 >= 3.10。
```bash
git clone https://github.com/math89423-star/AIpolish.git
cd AIpolish

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖包
pip install -r requirements.txt
```

### 第三步：环境变量配置 (.env)
在项目根目录创建一个 .env 文件，并严格根据您刚才安装的 MySQL 和 Redis 信息进行填入：
```Ini
# 服务端运行端口 (生产环境)
APP_PORT=8030

# MySQL 数据库配置 (请确保账号密码正确，且 MySQL 服务已启动)
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ai_polisher

# Redis 配置 (强烈建议生产环境和测试环境使用不同的 db 编号，如 /0 和 /1)
REDIS_URL=redis://:your_redis_password@127.0.0.1:6379/0

# 系统初始化超级管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

### 第四步：初始化数据库
执行初始化脚本。系统会自动连接 MySQL，强制创建数据库和表结构，并写入 ```.env``` 中配置的超级管理员：
```bash
python backend/model/init_db.py
```

### 第五步：一键启动系统 (生产环境)
```bash
bash start_worker.bash
```