from flask_restx import Namespace, Resource, fields
from flask import request, Response
from extensions import db
from models.user import User
import uuid
import json

ns = Namespace('register', description='User registration operations')

register_model = ns.model('Register', {
    'name': fields.String(required=True, description='用户姓名'),
    'email': fields.String(required=True, description='邮箱'),
    'phone': fields.String(required=True, description='手机号'),
    'password': fields.String(required=True, description='密码')
})

def make_response(data):
    """HTTP 状态码固定 200，错误信息通过 JSON code 返回"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=200,  # 这里固定 200
        mimetype='application/json'
    )

@ns.route('/')
class Register(Resource):
    @ns.expect(register_model)
    def post(self):
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')

        if not all([name, email, phone, password]):
            return make_response({"code": 400, "msg": "参数不完整", "user_id": None})

        if User.query.filter((User.email == email) | (User.phone == phone)).first():
            return make_response({"code": 400, "msg": "用户已存在", "user_id": None})

        user_id = "U" + uuid.uuid4().hex[:10]
        user = User(user_id=user_id, name=name, email=email, phone=phone)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
            return make_response({"code": 200, "msg": "注册成功", "data": {"user_id": user.user_id}})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"注册失败：{str(e)}", "user_id": None})
