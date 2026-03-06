# 🚀 AI 极速学术润色系统 (AI Academic Polisher)

这是一个专为学术论文打磨而生的工业级、高并发 AI 润色系统。系统采用了现代化的前后端分离架构，不仅支持纯文本的流式打字机视觉输出，还具备强大的 **Word 文档（.docx）一键解析、并发润色与无损重排**功能。

针对市面上各类严格的 AI 检测系统（如知网查重、Turnitin），系统内置了多套应对策略，通过高度可定制的提示词工程，为用户提供极致的去 AI 化体验。

## ✨ 核心特性

* **⚡ 极速高并发引擎**：针对长篇幅 Word 文档，底层采用 RQ 任务队列 + `ThreadPoolExecutor` (默认 15 并发)，将数万字的论文切片并发请求，耗时从几分钟缩减至十秒级。
* **📄 Word 物理隔离解析**：底层调用 `LibreOffice Headless` 自动清洗各种来源不明、格式畸形的 `.docx` 或 WPS 文档，保障 `python-docx` 解析 100% 成功率。彻底过滤图表、公式，仅对正文进行提取和覆盖，**绝对不破坏原有的复杂排版**。
* **🌊 SSE 流式丝滑输出**：利用 Redis Pub/Sub 技术，突破传统 HTTP 阻塞，实现 AI 文本生成过程的实时流式推送（打字机效果）与进度条实时反馈。
* **🛡️ 灵活的防查重策略**：内置“标准平衡”、“极致降重”、“保守润色”等多套提示词策略，可热插拔式配置，精准狙击不同查重平台的检测算法。
* **🧪 双轨物理隔离架构**：自带生产环境 (`start_worker.bash`) 与测试沙盒 (`start_test.bash`) 启动脚本，端口、数据库、Redis 缓存库完美隔离，杜绝测试数据污染生产线。

---

## 🏗️ 系统架构设计

本系统采用典型的微服务/异步任务架构：

1. **Web 核心 (Flask + Gunicorn)**：
   * 采用 `gthread` 模式运行，保障海量 Server-Sent Events (SSE) 长连接的稳定性，告别假死和阻塞。
2. **关系型数据库 (MySQL)**：
   * 负责存储用户鉴权信息、API 渠道配置、任务持久化记录。
   * 支持多 API 渠道分发与调用统计。
3. **缓存与消息中间件 (Redis)**：
   * **作用一**：作为 `python-rq` 的任务调度中间件，管理庞大的后台 AI 润色队列。
   * **作用二**：利用 Redis 哈希（Hash）和集合（Set）实现乱序并发下的 **“断点续写与状态保护”**。
   * **作用三**：作为 Pub/Sub 消息总线，将后台 Worker 的进度毫秒级推送到前端。

---

## 🛠️ 自行部署指南与注意事项

### 1. 环境依赖准备
在部署本系统前，请确保您的服务器已安装以下基础设施：
* **Python** 3.10+
* **MySQL** 8.0+ 
* **Redis** 6.0+ (务必保持后台运行)
* **LibreOffice** (⚠️ 极其重要，用于文档格式洗白)

> **安装 LibreOffice (Ubuntu/Debian 示例):**
> ```bash
> sudo apt-get update
> sudo apt-get install -y libreoffice-core libreoffice-writer
> ```

### 2. 获取代码与安装依赖
```bash
git clone https://github.com/math89423-star/AIpolish.git
cd AIpolish

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖包
pip install -r requirements.txt