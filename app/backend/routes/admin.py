"""
管理员路由（重构版）

使用UserService、ApiConfigService和装饰器
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify
from backend.services.user_service import UserService
from backend.services.api_config_service import ApiConfigService
from backend.utils.decorators import require_admin
from backend.utils.logging_config import get_logger
from werkzeug.utils import secure_filename
import asyncio
import json
import os

admin_bp = Blueprint('admin', __name__)
logger = get_logger(__name__)

def _user_service() -> UserService:
    return UserService()

def _api_config_service() -> ApiConfigService:
    return ApiConfigService()


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
        "api_config_id_strict": u.api_config_id_strict,
        "can_use_strict": u.can_use_strict
    } for u in users])


@admin_bp.route('/users', methods=['POST'])
@require_admin
def add_user():
    """创建新用户"""
    data = request.json

    try:
        user = _user_service().create_user(
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
        user = _user_service().update_user_api_config(
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
        result = _user_service().delete_user(target_username)
        logger.info(f"管理员删除用户: {target_username}")
        return jsonify(result), 200

    except ValueError as e:
        logger.warning(f"删除用户失败: {str(e)}")
        return jsonify({"error": str(e)}), 404


@admin_bp.route('/users/update_strict_permission', methods=['POST'])
@require_admin
def update_strict_permission():
    """更新用户极致模式权限"""
    data = request.json
    target_username = data.get('target_username')
    can_use_strict = data.get('can_use_strict', False)

    from backend.model.models import User
    user = User.query.filter_by(username=target_username).first()
    if not user:
        return jsonify({"error": "用户不存在"}), 404

    user.can_use_strict = can_use_strict
    from backend.extensions import db
    db.session.commit()
    logger.info(f"更新用户 {target_username} 极致模式权限: {can_use_strict}")
    return jsonify({"message": "权限更新成功"}), 200


# === API 渠道管理 ===

@admin_bp.route('/api_configs', methods=['GET'])
@require_admin
def list_api_configs():
    """获取所有API配置"""
    configs = _api_config_service().get_all_configs()
    return jsonify(configs), 200


@admin_bp.route('/api_configs', methods=['POST'])
@require_admin
def add_api_config():
    """创建API配置"""
    data = request.json

    try:
        config = _api_config_service().create_config(
            name=data.get('name', ''),
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model_name=data.get('model_name', 'gpt-3.5-turbo'),
            api_type=data.get('api_type', 'proxy')
        )

        logger.info(f"管理员创建API配置: {config.name}")
        return jsonify({"message": "API线路创建成功"}), 201

    except ValueError as e:
        logger.warning(f"创建API配置失败: {str(e)}")
        return jsonify({"error": str(e)}), 400


@admin_bp.route('/api_configs/<int:config_id>', methods=['PUT'])
@require_admin
def update_api_config(config_id):
    """更新API配置"""
    data = request.json

    try:
        config = _api_config_service().update_config(
            config_id=config_id,
            name=data.get('name', ''),
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model_name=data.get('model_name', ''),
            api_type=data.get('api_type', 'proxy')
        )

        logger.info(f"管理员更新API配置: {config.name}")
        return jsonify({"message": "配置更新成功"}), 200

    except ValueError as e:
        logger.warning(f"更新API配置失败: {str(e)}")
        return jsonify({"error": str(e)}), 400


@admin_bp.route('/api_configs/<int:config_id>', methods=['DELETE'])
@require_admin
def delete_api_config(config_id):
    """删除API配置"""
    try:
        result = _api_config_service().delete_config(config_id)
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
            _user_service().update_user_api_config(
                username=user.username,
                mode=mode,
                api_config_id=api_config_id
            )

        logger.info(f"批量更新 {len(users)} 个用户的{mode}模式线路")
        return jsonify({"message": f"已批量更新 {len(users)} 个用户的{mode}模式线路"}), 200

    except Exception as e:
        logger.error(f"批量更新失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/api_configs/test_all', methods=['POST'])
@require_admin
def test_all_api_configs():
    """一键测试全部API配置连接"""
    try:
        configs = _api_config_service().get_all_configs()
        if not configs:
            return jsonify({"results": [], "message": "没有可测试的API配置"}), 200

        results: list[dict] = []
        for cfg in configs:
            try:
                result = asyncio.run(_api_config_service().test_api_connection(
                    api_key=cfg.get('api_key', ''),
                    base_url=cfg.get('base_url', ''),
                    model_name=cfg.get('model_name', ''),
                    api_type=cfg.get('api_type', 'proxy')
                ))
                results.append({"id": cfg['id'], "name": cfg['name'], **result})
            except Exception as e:
                results.append({"id": cfg['id'], "name": cfg['name'], "success": False, "message": str(e)})

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"批量API连接测试: {success_count}/{len(results)} 成功")
        return jsonify({"results": results, "message": f"{success_count}/{len(results)} 个配置连接成功"}), 200

    except Exception as e:
        logger.error(f"批量API连接测试失败: {str(e)}")
        return jsonify({"success": False, "message": f"测试异常: {str(e)}"}), 500


@admin_bp.route('/api_configs/test', methods=['POST'])
@require_admin
def test_api_config():
    """测试API配置连接"""
    data = request.json

    try:
        result = asyncio.run(_api_config_service().test_api_connection(
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model_name=data.get('model_name', ''),
            api_type=data.get('api_type', 'proxy')
        ))

        logger.info(f"API连接测试: {result['message']}")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"API连接测试失败: {str(e)}")
        return jsonify({"success": False, "message": f"测试异常: {str(e)}"}), 500


# === 主题管理 ===

@admin_bp.route('/theme', methods=['GET'])
@require_admin
def get_theme():
    """获取当前主题配置"""
    from backend.model.models import SystemSetting
    setting = SystemSetting.query.filter_by(key='theme').first()
    if setting and setting.value:
        return jsonify(json.loads(setting.value)), 200
    return jsonify({"primary_color": "#3b82f6", "bg_type": "color", "bg_value": "#f1f5f9"}), 200


@admin_bp.route('/theme', methods=['POST'])
@require_admin
def save_theme():
    """保存主题配置"""
    from backend.model.models import SystemSetting
    from backend.extensions import db

    data = request.json
    setting = SystemSetting.query.filter_by(key='theme').first()

    if not setting:
        setting = SystemSetting(key='theme')
        db.session.add(setting)

    setting.value = json.dumps(data)
    db.session.commit()

    logger.info(f"管理员更新主题配置")
    return jsonify({"message": "主题保存成功"}), 200


@admin_bp.route('/theme/upload', methods=['POST'])
@require_admin
def upload_theme_bg():
    """上传主题背景图"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "文件名为空"}), 400

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../uploads')
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    url = f"/uploads/{filename}"
    logger.info(f"管理员上传主题背景图: {filename}")
    return jsonify({"url": url}), 200
