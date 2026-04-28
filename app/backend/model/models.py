from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.extensions import db

class ApiConfig(db.Model):
    __tablename__ = 'api_configs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    model_name = db.Column(db.String(100), default='gpt-3.5-turbo')
    api_type = db.Column(db.String(20), default='proxy', nullable=False)  # 'official', 'proxy', 'ollama'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default='user')
    usage_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    can_use_strict = db.Column(db.Boolean, default=False)
    api_config_id = db.Column(db.Integer, db.ForeignKey('api_configs.id'), nullable=True)
    api_config = db.relationship('ApiConfig', foreign_keys=[api_config_id], backref=db.backref('users_legacy', lazy=True))

    # 双模式线路配置
    api_config_id_standard = db.Column(db.Integer, db.ForeignKey('api_configs.id'), nullable=True)
    api_config_id_strict = db.Column(db.Integer, db.ForeignKey('api_configs.id'), nullable=True)
    api_config_standard = db.relationship('ApiConfig', foreign_keys=[api_config_id_standard], backref=db.backref('users_standard', lazy=True))
    api_config_strict = db.relationship('ApiConfig', foreign_keys=[api_config_id_strict], backref=db.backref('users_strict', lazy=True))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

from backend.config import Config

if Config.DEPLOY_MODE == 'desktop':
    LONGTEXT = db.Text
else:
    from sqlalchemy.dialects.mysql import LONGTEXT


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    title = db.Column(db.String(100))
    original_text = db.Column(LONGTEXT, nullable=True)
    polished_text = db.Column(LONGTEXT)
    mode = db.Column(db.String(10), default='zh')
    status = db.Column(db.String(20), default='pending')
    
    # 保存用户选择的策略配置（如 'standard', 'strict'）
    strategy = db.Column(db.String(50), default='standard')
    
    # 🟢 补全缺失的字段，否则上传会直接报错
    task_type = db.Column(db.String(20), default='text') # 'text' 或 'docx'
    file_path = db.Column(db.String(255), nullable=True) 
    result_file_path = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)