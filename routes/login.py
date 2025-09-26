# routes/login.py
from flask import Blueprint, request, jsonify
from extensions import db
from models.user import User
from werkzeug.security import check_password_hash
import jwt
import datetime

login_bp = Blueprint("login", __name__)

SECRET_KEY = "123456"  # 可以放到 config.py

@login_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email_or_phone = data.get("email_or_phone")
    password = data.get("password")

    if not email_or_phone or not password:
        return jsonify({"msg": "参数不完整"}), 400

    # 支持邮箱或手机号登录
    user = User.query.filter((User.email==email_or_phone) | (User.phone==email_or_phone)).first()
    if not user:
        return jsonify({"msg": "用户不存在"}), 404

    if not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "密码错误"}), 401

    # 生成 token（有效期 1 天）
    payload = {
        "user_id": user.user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return jsonify({"msg": "登录成功", "token": token, "user_id": user.user_id})
