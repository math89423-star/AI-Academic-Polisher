-- ==========================================
-- 1. 创建数据库并设置字符集 (支持中文和 Emoji)
-- ==========================================
SET NAMES utf8mb4;

-- ==========================================
-- 1. 创建数据库并设置字符集 (支持中文和 Emoji)
-- ==========================================
CREATE DATABASE IF NOT EXISTS ai_polisher 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE ai_polisher;

-- ==========================================
-- 2. 物理表结构初始化
-- ==========================================

-- 创建大模型 API 渠道配置表
CREATE TABLE IF NOT EXISTS api_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    api_key VARCHAR(255) NOT NULL,
    base_url VARCHAR(255) NOT NULL,
    model_name VARCHAR(100) DEFAULT 'gpt-3.5-turbo',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(256),
    role VARCHAR(20) DEFAULT 'user',
    usage_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    api_config_id INT NULL,
    api_config_id_standard INT NULL,
    api_config_id_strict INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (api_config_id) REFERENCES api_configs(id) ON DELETE SET NULL,
    FOREIGN KEY (api_config_id_standard) REFERENCES api_configs(id) ON DELETE SET NULL,
    FOREIGN KEY (api_config_id_strict) REFERENCES api_configs(id) ON DELETE SET NULL,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建润色任务表
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    title VARCHAR(100),
    original_text TEXT,
    polished_text MEDIUMTEXT, -- 润色后的文档可能较长，使用 MEDIUMTEXT 更安全
    mode VARCHAR(10) DEFAULT 'zh',
    status VARCHAR(20) DEFAULT 'pending',
    strategy VARCHAR(50) DEFAULT 'standard',
    task_type VARCHAR(20) DEFAULT 'text',
    file_path VARCHAR(255),
    result_file_path VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- 3. 注入系统默认与必配数据
-- ==========================================

-- 🟢 1. 载入专属 Gemini 线路配置
INSERT IGNORE INTO api_configs (name, api_key, base_url, model_name, created_at) 
VALUES (
    '硅基流动 Gemini', 
    'sk-NKC4yM6WFVLxKCzKaEmK5ISG73E0JQh0bsmaJnBbKlvxyPg6', 
    'https://api.devdove.site/v1', 
    'gemini-3.1-pro-preview', 
    NOW()
);

-- 🟢 2. 预设普通用户：张三 和 李四 (免密登录，自动绑定 Gemini 线路)
INSERT IGNORE INTO users (username, role, usage_count, is_active, api_config_id, created_at) 
VALUES 
(
    '周春花', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '高晓菊', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '罗秋燕', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '李川', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '阮青玉', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '代坤丽', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '罗祥龙', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '陈力铟', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '陈泽', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '秦胜', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '李建雪', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '向青芝', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '陈施宇', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '黄安', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '刘洋', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '唐莉', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '晏志灵', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '严川岚', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '李慢慢', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '黎海洋', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
),
(
    '柳清云', 
    'user', 
    0, 
    1, 
    (SELECT id FROM api_configs WHERE name = '硅基流动 Gemini' LIMIT 1),
    NOW()
);