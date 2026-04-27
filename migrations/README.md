# 数据库迁移说明

## 迁移脚本：add_api_type_to_api_configs.sql

### 执行方法

#### 方法1：通过 MySQL 容器执行
```bash
docker exec -i aipolish_mysql mysql -uroot -p123456 ai_polisher < migrations/add_api_type_to_api_configs.sql
```

#### 方法2：进入容器手动执行
```bash
docker exec -it aipolish_mysql mysql -uroot -p123456 ai_polisher
```
然后复制粘贴 SQL 内容执行。

#### 方法3：使用 MySQL 客户端
```bash
mysql -h 127.0.0.1 -P 3306 -uroot -p123456 ai_polisher < migrations/add_api_type_to_api_configs.sql
```

### 迁移内容

添加 `api_type` 字段到 `api_configs` 表，支持三种 API 类型：
- `official`: 官方 API (OpenAI/Anthropic等)
- `proxy`: 三方代理商 API (默认值)
- `ollama`: Ollama 本地模型

### 验证迁移

执行后可以通过以下 SQL 验证：
```sql
DESC api_configs;
SELECT * FROM api_configs;
```
