from flask_restx import Namespace, Resource, fields
from flask import request, Response
from extensions import db
from models.user import User
from werkzeug.security import check_password_hash
import jwt
import datetime
from sqlalchemy import or_
import json

SECRET_KEY = "123456"  # 建议放到 config.py

ns = Namespace('login', description='User login operations')

# 登录请求模型
login_model = ns.model('Login', {
    'email_or_phone': fields.String(required=True, description='邮箱或手机号'),
    'password': fields.String(required=True, description='密码')
})

def make_response(data):
    """统一返回，HTTP 200，中文正常显示"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    )

@ns.route('/')
class Login(Resource):
    @ns.expect(login_model)
    def post(self):
        """用户登录"""
        data = request.get_json() or {}
        email_or_phone = data.get("email_or_phone")
        password = data.get("password")

        if not email_or_phone or not password:
            return make_response({"code": 400, "msg": "参数不完整", "token": None, "user_id": None})

        # 支持邮箱或手机号登录
        user = User.query.filter(
            or_(User.email == email_or_phone, User.phone == email_or_phone)
        ).first()
        if not user:
            return make_response({"code": 404, "msg": "用户不存在", "token": None, "user_id": None})

        if not check_password_hash(user.password_hash, password):
            return make_response({"code": 401, "msg": "密码错误", "token": None, "user_id": None})

        # 生成 token（有效期 1 天）
        payload = {
            "user_id": user.user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        if isinstance(token, bytes):  # PyJWT <2.0 返回 bytes
            token = token.decode("utf-8")

        return make_response({
            "code": 200,
            "msg": "登录成功",
            "data": {
            "token": token,
            "user_id": user.user_id
        }})
