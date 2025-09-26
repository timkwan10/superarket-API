from flask import Blueprint, request, jsonify
from extensions import db
from models.user import User

user_bp = Blueprint("user", __name__)

# 修改基本信息（姓名、邮箱、电话）
@user_bp.route("/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"code": 1, "message": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"code": 1, "message": "No data provided"}), 400

    # 修改字段
    if "name" in data:
        user.name = data["name"]
    if "email" in data:
        user.email = data["email"]
    if "phone" in data:
        user.phone = data["phone"]

    db.session.commit()
    return jsonify({"code": 0, "message": "User updated successfully"})

@user_bp.route("/users/<user_id>/password", methods=["PUT"])
def change_password(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"code": 1, "message": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"code": 1, "message": "No data provided"}), 400

    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not current_password or not new_password or not confirm_password:
        return jsonify({"code": 1, "message": "Missing required fields"}), 400

    if not user.check_password(current_password):
        return jsonify({"code": 1, "message": "Current password is incorrect"}), 400

    if new_password != confirm_password:
        return jsonify({"code": 1, "message": "Passwords do not match"}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"code": 0, "message": "Password updated successfully"})
