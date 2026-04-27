"""
用户服务层

负责用户认证、权限检查等业务逻辑
"""
from backend.model.models import User
from backend.extensions import db


class UserService:
    """用户服务"""

    def __init__(self, db_session=None):
        self.db = db_session or db

    def authenticate_user(self, username: str) -> User:
        """
        验证普通用户

        Args:
            username: 用户名

        Returns:
            User: 用户对象

        Raises:
            ValueError: 用户不存在或已被封禁
        """
        if not username or not username.strip():
            raise ValueError("用户名不能为空")

        user = User.query.filter_by(username=username, role='user').first()

        if not user:
            raise ValueError("该账号未注册，请联系管理员分配")

        if not user.is_active:
            raise ValueError("该账户已被管理员封禁")

        return user

    def authenticate_admin(self, username: str, password: str) -> User:
        """
        验证管理员

        Args:
            username: 用户名
            password: 密码

        Returns:
            User: 管理员对象

        Raises:
            ValueError: 认证失败
        """
        if not username or not password:
            raise ValueError("用户名和密码不能为空")

        admin = User.query.filter_by(username=username, role='admin').first()

        if not admin or not admin.check_password(password):
            raise ValueError("管理员账号或密码错误")

        return admin

    def check_admin(self, username: str) -> bool:
        """
        检查是否为管理员

        Args:
            username: 用户名

        Returns:
            bool: 是否为管理员
        """
        if not username:
            return False

        user = User.query.filter_by(username=username).first()
        return user and user.role == 'admin'

    def create_user(self, username: str, role: str = 'user', password: str = None, api_config_id: int = None) -> User:
        """
        创建用户

        Args:
            username: 用户名
            role: 角色 (user/admin)
            password: 密码（管理员必需）
            api_config_id: API配置ID

        Returns:
            User: 创建的用户对象

        Raises:
            ValueError: 用户名已存在或参数错误
        """
        if User.query.filter_by(username=username).first():
            raise ValueError("该用户名已存在")

        try:
            new_user = User(
                username=username,
                role=role,
                api_config_id=api_config_id if api_config_id else None
            )

            if role == 'admin' and password:
                new_user.set_password(password)

            self.db.session.add(new_user)
            self.db.session.commit()

            return new_user

        except Exception as e:
            self.db.session.rollback()
            raise

    def update_user_api_config(self, username: str, mode: str, api_config_id: int = None) -> User:
        """
        更新用户API配置

        Args:
            username: 用户名
            mode: 配置模式 (standard/strict/legacy)
            api_config_id: API配置ID

        Returns:
            User: 更新后的用户对象

        Raises:
            ValueError: 用户不存在
        """
        user = User.query.filter_by(username=username).first()
        if not user:
            raise ValueError("用户不存在")

        try:
            if mode == 'standard':
                user.api_config_id_standard = api_config_id
            elif mode == 'strict':
                user.api_config_id_strict = api_config_id
            else:
                # 兼容旧版单一线路配置
                user.api_config_id = api_config_id

            self.db.session.commit()
            return user

        except Exception as e:
            self.db.session.rollback()
            raise

    def delete_user(self, username: str) -> dict:
        """
        删除用户及其所有任务

        Args:
            username: 用户名

        Returns:
            dict: 操作结果

        Raises:
            ValueError: 用户不存在
        """
        from backend.model.models import Task

        user = User.query.filter_by(username=username).first()
        if not user:
            raise ValueError("用户不存在")

        try:
            # 删除用户的所有任务
            Task.query.filter_by(user_id=user.id).delete()

            # 删除用户
            self.db.session.delete(user)
            self.db.session.commit()

            return {"message": f"用户 {username} 及其所有记录已彻底清除"}

        except Exception as e:
            self.db.session.rollback()
            raise
