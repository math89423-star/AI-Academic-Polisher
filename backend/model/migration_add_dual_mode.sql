-- 添加双模式线路配置字段
ALTER TABLE users ADD COLUMN api_config_id_standard INT NULL;
ALTER TABLE users ADD COLUMN api_config_id_strict INT NULL;

-- 添加外键约束
ALTER TABLE users ADD CONSTRAINT fk_users_api_config_standard
    FOREIGN KEY (api_config_id_standard) REFERENCES api_configs(id) ON DELETE SET NULL;

ALTER TABLE users ADD CONSTRAINT fk_users_api_config_strict
    FOREIGN KEY (api_config_id_strict) REFERENCES api_configs(id) ON DELETE SET NULL;
