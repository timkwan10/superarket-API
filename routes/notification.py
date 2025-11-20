from flask_restx import Namespace, Resource, fields
from flask import request, Response
from extensions import db
from models.user_settings import UserSettings
from datetime import timedelta
import json

ns = Namespace('notification', description='Notification settings operations')

def make_response(data):
    """统一返回格式"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    )

# Swagger 模型定义
email_model = ns.model('EmailPromotion', {
    'user_id': fields.String(required=True, description='用户ID'),
    'enable': fields.Boolean(required=True, description='是否启用 Email Promotion')
})

push_model = ns.model('PushEnable', {
    'user_id': fields.String(required=True, description='用户ID'),
    'enable': fields.Boolean(required=True, description='是否启用 Push 通知')
})


# ===========================
# 1. 获取通知设置
# ===========================
@ns.route('/<string:user_id>')
class GetNotification(Resource):
    def get(self, user_id):
        """获取用户通知设置"""

        settings = UserSettings.query.filter_by(user_id=user_id).first()

        if not settings:
            return make_response({
                "code": 200,
                "msg": "success",
                "data": {
                    "email_promotion": False,
                    "push_enable": False,
                    "updated_at": None
                }
            })

        # 加8小时
        updated_time = None
        if settings.updated_at:
            updated_time = settings.updated_at.strftime("%Y-%m-%d %H:%M:%S")

        return make_response({
            "code": 200,
            "msg": "success",
            "data": {
                "email_promotion": settings.email_promotion,
                "push_enable": settings.push_enable,
                "updated_at": updated_time
            }
        })


# ===========================
# 2. 设置 Email Promotion
# ===========================
@ns.route('/email')
class SetEmailPromotion(Resource):
    @ns.expect(email_model)
    def post(self):
        """启用或禁用 Email Promotion"""

        data = request.json or {}
        user_id = data.get("user_id")
        enable = data.get("enable")

        if not user_id or enable is None:
            return make_response({"code": 400, "msg": "参数不完整"})

        settings = UserSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = UserSettings(user_id=user_id)

        settings.email_promotion = bool(enable)
        db.session.add(settings)
        db.session.commit()

        updated_time = settings.updated_at.strftime("%Y-%m-%d %H:%M:%S")

        return make_response({
            "code": 200,
            "msg": "Email Promotion 设置成功",
            "data": {
                "email_promotion": settings.email_promotion,
                "updated_at": updated_time
            }
        })


# ===========================
# 3. 设置 Push Enable
# ===========================
@ns.route('/push')
class SetPushEnable(Resource):
    @ns.expect(push_model)
    def post(self):
        """启用或禁用 Push 通知"""

        data = request.json or {}
        user_id = data.get("user_id")
        enable = data.get("enable")

        if not user_id or enable is None:
            return make_response({"code": 400, "msg": "参数不完整"})

        settings = UserSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = UserSettings(user_id=user_id)

        settings.push_enable = bool(enable)
        db.session.add(settings)
        db.session.commit()

        updated_time = settings.updated_at.strftime("%Y-%m-%d %H:%M:%S")

        return make_response({
            "code": 200,
            "msg": "Push 设置成功",
            "data": {
                "push_enable": settings.push_enable,
                "updated_at": updated_time
            }
        })
