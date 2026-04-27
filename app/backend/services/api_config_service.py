"""
API配置服务层

负责API配置的管理
"""
from backend.model.models import ApiConfig, User
from backend.extensions import db
import httpx
import asyncio


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
            "model_name": c.model_name,
            "api_type": c.api_type
        } for c in configs]

    def create_config(self, name: str, api_key: str, base_url: str, model_name: str = 'gpt-3.5-turbo', api_type: str = 'proxy') -> ApiConfig:
        """
        创建API配置

        Args:
            name: 配置名称
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
            api_type: API类型 (official/proxy/ollama)

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
                model_name=model_name.strip(),
                api_type=api_type.strip()
            )

            self.db.session.add(new_conf)
            self.db.session.commit()

            return new_conf

        except Exception as e:
            self.db.session.rollback()
            raise ValueError("创建失败，请检查线路名称是否重复")

    def update_config(self, config_id: int, name: str, api_key: str, base_url: str, model_name: str, api_type: str) -> ApiConfig:
        conf = ApiConfig.query.get(config_id)
        if not conf:
            raise ValueError("线路不存在")

        try:
            conf.name = name.strip()
            conf.api_key = api_key.strip()
            conf.base_url = base_url.strip()
            conf.model_name = model_name.strip()
            conf.api_type = api_type.strip()
            self.db.session.commit()
            return conf
        except Exception:
            self.db.session.rollback()
            raise ValueError("更新失败，请检查线路名称是否重复")

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

    async def test_api_connection(self, api_key: str, base_url: str, model_name: str, api_type: str) -> dict:
        """
        测试API连接

        Args:
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
            api_type: API类型 (official/proxy/ollama)

        Returns:
            dict: 测试结果 {"success": bool, "message": str}
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if api_type == 'ollama':
                    # Ollama 测试：调用 /api/tags 获取模型列表
                    test_url = f"{base_url.rstrip('/')}/api/tags"
                    response = await client.get(test_url)

                    if response.status_code == 200:
                        data = response.json()
                        models = [m.get('name') for m in data.get('models', [])]
                        if model_name in models:
                            return {"success": True, "message": f"连接成功，模型 {model_name} 可用"}
                        else:
                            return {"success": False, "message": f"连接成功但模型 {model_name} 不存在，可用模型: {', '.join(models[:5])}"}
                    else:
                        return {"success": False, "message": f"连接失败: HTTP {response.status_code}"}

                else:
                    # OpenAI 兼容 API 测试：调用 /v1/models
                    test_url = f"{base_url.rstrip('/')}/models"
                    headers = {"Authorization": f"Bearer {api_key}"}
                    response = await client.get(test_url, headers=headers)

                    if response.status_code == 200:
                        return {"success": True, "message": "连接成功，API 可用"}
                    elif response.status_code == 401:
                        return {"success": False, "message": "API Key 无效或已过期"}
                    elif response.status_code == 404:
                        return {"success": False, "message": "API 端点不存在，请检查 Base URL"}
                    else:
                        return {"success": False, "message": f"连接失败: HTTP {response.status_code}"}

        except httpx.TimeoutException:
            return {"success": False, "message": "连接超时，请检查网络或 Base URL"}
        except httpx.ConnectError:
            return {"success": False, "message": "无法连接到服务器，请检查 Base URL"}
        except Exception as e:
            return {"success": False, "message": f"测试失败: {str(e)}"}
