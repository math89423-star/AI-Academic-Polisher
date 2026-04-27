-- 添加 api_type 字段到 api_configs 表
-- 执行时间: 2026-04-27

ALTER TABLE api_configs
ADD COLUMN api_type VARCHAR(20) NOT NULL DEFAULT 'proxy'
COMMENT 'API类型: official(官方API), proxy(三方代理商), ollama(本地模型)';

-- 为现有数据设置默认值
UPDATE api_configs SET api_type = 'proxy' WHERE api_type IS NULL;
