"""
API配置服务层

负责API配置的管理
"""
from backend.model.models import ApiConfig, User
from backend.extensions import db


class ApiConfigService:
    """API配置服务"""

    def __init__(self, db_session=None):
        self.db = db_session or db

    def get_all_configs(self) -> list:
        """
        获取所有API配置

        Returns:
            list: 配置列表
        """
        configs = ApiConfig.query.all()
        return [{
            "id": c.id,
            "name": c.name,
            "api_key": c.api_key,
            "base_url": c.base_url,
            "model_name": c.model_name
        } for c in configs]

    def create_config(self, name: str, api_key: str, base_url: str, model_name: str = 'gpt-3.5-turbo') -> ApiConfig:
        """
        创建API配置

        Args:
            name: 配置名称
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称

        Returns:
            ApiConfig: 创建的配置对象

        Raises:
            ValueError: 配置名称已存在
        """
        try:
            new_conf = ApiConfig(
                name=name.strip(),
                api_key=api_key.strip(),
                base_url=base_url.strip(),
                model_name=model_name.strip()
            )

            self.db.session.add(new_conf)
            self.db.session.commit()

            return new_conf

        except Exception as e:
            self.db.session.rollback()
            raise ValueError("创建失败，请检查线路名称是否重复")

    def delete_config(self, config_id: int) -> dict:
        """
        删除API配置

        Args:
            config_id: 配置ID

        Returns:
            dict: 操作结果

        Raises:
            ValueError: 配置不存在
        """
        conf = ApiConfig.query.get(config_id)
        if not conf:
            raise ValueError("线路不存在")

        try:
            # 如果删除了线路，把正在使用该线路的用户回退到系统默认线路 (None)
            User.query.filter_by(api_config_id=config_id).update({'api_config_id': None})
            User.query.filter_by(api_config_id_standard=config_id).update({'api_config_id_standard': None})
            User.query.filter_by(api_config_id_strict=config_id).update({'api_config_id_strict': None})

            self.db.session.delete(conf)
            self.db.session.commit()

            return {"message": "线路已彻底销毁"}

        except Exception as e:
            self.db.session.rollback()
            raise

    def resolve_config(self, user: User, strategy: str) -> tuple:
        """
        根据用户和策略解析API配置

        Args:
            user: 用户对象
            strategy: 策略 (standard/strict)

        Returns:
            tuple: (api_key, base_url, model_name)
        """
        api_key, base_url, model_name = None, None, 'gpt-3.5-turbo'

        if user:
            # 优先使用用户的策略专属配置
            if strategy == 'strict' and user.api_config_id_strict:
                config = ApiConfig.query.get(user.api_config_id_strict)
                if config:
                    return config.api_key, config.base_url, config.model_name

            elif strategy == 'standard' and user.api_config_id_standard:
                config = ApiConfig.query.get(user.api_config_id_standard)
                if config:
                    return config.api_key, config.base_url, config.model_name

            # 如果策略专属配置不存在，回退到旧版单一配置
            if user.api_config:
                return user.api_config.api_key, user.api_config.base_url, user.api_config.model_name

        # 如果用户没有配置，使用系统默认配置
        default_config = ApiConfig.query.first()
        if default_config:
            return default_config.api_key, default_config.base_url, default_config.model_name

        return api_key, base_url, model_name
