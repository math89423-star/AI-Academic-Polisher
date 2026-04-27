"""
管理员路由（重构版）

使用UserService、ApiConfigService和装饰器
"""
from flask import Blueprint, request, jsonify
from backend.services.user_service import UserService
from backend.services.api_config_service import ApiConfigService
from backend.utils.decorators import require_admin
from backend.utils.logging_config import get_logger

admin_bp = Blueprint('admin', __name__)
user_service = UserService()
api_config_service = ApiConfigService()
logger = get_logger(__name__)


# === 用户管理 ===

@admin_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    """获取所有用户列表"""
    from backend.model.models import User

    users = User.query.all()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "usage_count": u.usage_count,
        "api_config_id": u.api_config_id,
        "api_config_id_standard": u.api_config_id_standard,
        "api_config_id_strict": u.api_config_id_strict
    } for u in users])


@admin_bp.route('/users', methods=['POST'])
@require_admin
def add_user():
    """创建新用户"""
    data = request.json

    try:
        user = user_service.create_user(
            username=data['new_username'],
            role=data.get('role', 'user'),
            password=data.get('password'),
            api_config_id=data.get('api_config_id')
        )

        logger.info(f"管理员创建用户: {user.username}")
        return jsonify({"message": "账号创建成功"}), 201

    except ValueError as e:
        logger.warning(f"创建用户失败: {str(e)}")
        return jsonify({"error": str(e)}), 400


@admin_bp.route('/users/update_config', methods=['POST'])
@require_admin
def update_user_api_config():
    """更新用户API配置"""
    data = request.json

    try:
        user = user_service.update_user_api_config(
            username=data['target_username'],
            mode=data.get('mode', 'legacy'),
            api_config_id=data.get('api_config_id')
        )

        logger.info(f"更新用户 {user.username} 的API配置")
        return jsonify({"message": "配置更新成功"}), 200

    except ValueError as e:
        logger.warning(f"更新配置失败: {str(e)}")
        return jsonify({"error": str(e)}), 404


@admin_bp.route('/users/<string:target_username>', methods=['DELETE'])
@require_admin
def delete_user(target_username):
    """删除用户"""
    try:
        result = user_service.delete_user(target_username)
        logger.info(f"管理员删除用户: {target_username}")
        return jsonify(result), 200

    except ValueError as e:
        logger.warning(f"删除用户失败: {str(e)}")
        return jsonify({"error": str(e)}), 404


# === API 渠道管理 ===

@admin_bp.route('/api_configs', methods=['GET'])
@require_admin
def list_api_configs():
    """获取所有API配置"""
    configs = api_config_service.get_all_configs()
    return jsonify(configs), 200


@admin_bp.route('/api_configs', methods=['POST'])
@require_admin
def add_api_config():
    """创建API配置"""
    data = request.json

    try:
        config = api_config_service.create_config(
            name=data.get('name', ''),
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model_name=data.get('model_name', 'gpt-3.5-turbo')
        )

        logger.info(f"管理员创建API配置: {config.name}")
        return jsonify({"message": "API线路创建成功"}), 201

    except ValueError as e:
        logger.warning(f"创建API配置失败: {str(e)}")
        return jsonify({"error": str(e)}), 400


@admin_bp.route('/api_configs/<int:config_id>', methods=['DELETE'])
@require_admin
def delete_api_config(config_id):
    """删除API配置"""
    try:
        result = api_config_service.delete_config(config_id)
        logger.info(f"管理员删除API配置: {config_id}")
        return jsonify(result), 200

    except ValueError as e:
        logger.warning(f"删除API配置失败: {str(e)}")
        return jsonify({"error": str(e)}), 404


@admin_bp.route('/users/batch_update_config', methods=['POST'])
@require_admin
def batch_update_user_config():
    """批量更新用户线路配置"""
    data = request.json
    usernames = data.get('usernames', [])
    mode = data.get('mode')
    api_config_id = data.get('api_config_id')

    if not usernames or not mode:
        return jsonify({"error": "参数不完整"}), 400

    try:
        from backend.model.models import User

        users = User.query.filter(User.username.in_(usernames)).all()

        for user in users:
            user_service.update_user_api_config(
                username=user.username,
                mode=mode,
                api_config_id=api_config_id
            )

        logger.info(f"批量更新 {len(users)} 个用户的{mode}模式线路")
        return jsonify({"message": f"已批量更新 {len(users)} 个用户的{mode}模式线路"}), 200

    except Exception as e:
        logger.error(f"批量更新失败: {str(e)}")
        return jsonify({"error": str(e)}), 500
