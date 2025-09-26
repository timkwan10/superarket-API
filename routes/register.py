from flask import Blueprint, request, jsonify
from extensions import db
from models.user import User
import uuid

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')

    if not all([name, email, phone, password]):
        return jsonify({"msg": "参数不完整"}), 400

    # 检查用户是否已存在
    if User.query.filter((User.email == email) | (User.phone == phone)).first():
        return jsonify({"msg": "用户已存在"}), 400

    # 生成唯一user_id
    user_id = "U" + uuid.uuid4().hex[:10]

    # 创建User实例
    user = User(
        user_id=user_id,
        name=name,
        email=email,
        phone=phone
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "注册失败", "error": str(e)}), 500

    return jsonify({"msg": "注册成功", "user_id": user.user_id})
