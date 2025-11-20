from flask_restx import Namespace, Resource, fields
from extensions import db
from models.user import User
from flask import Response, request, url_for
import json
from PIL import Image
import io
import time
import random
import string


ns = Namespace('user', description='User operations')

# 统一返回函数
def make_response(data):
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )

# 定义更新用户信息的数据模型
update_user_model = ns.model('UpdateUser', {
    'name': fields.String(description='用户姓名'),
    'email': fields.String(description='用户邮箱'),
    'phone': fields.String(description='用户电话')
})

# 定义修改密码的数据模型
change_password_model = ns.model('ChangePassword', {
    'current_password': fields.String(required=True, description='当前密码'),
    'new_password': fields.String(required=True, description='新密码'),
    'confirm_password': fields.String(required=True, description='确认新密码')
})

# ==================== 修改基本信息 ====================
@ns.route('/<string:user_id>')
class UserUpdate(Resource):
    @ns.expect(update_user_model)
    def put(self, user_id):
        """修改用户基本信息"""
        user = User.query.get(user_id)
        if not user:
            return make_response({"code": 404, "msg": "用户不存在"})

        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求数据为空"})

        modified = False

        # 检查邮箱是否重复
        if "email" in data and data["email"] != user.email:
            exists = User.query.filter(User.email == data["email"], User.user_id != user.user_id).first()
            if exists:
                return make_response({"code": 400, "msg": "邮箱已被其他用户使用"})
            user.email = data["email"]
            modified = True

        if "name" in data and data["name"] != user.name:
            user.name = data["name"]
            modified = True

        if "phone" in data and data["phone"] != user.phone:
            user.phone = data["phone"]
            modified = True

        if not modified:
            return make_response({"code": 400, "msg": "提交的数据和原数据相同，无需修改"})

        try:
            db.session.commit()
            return make_response({"code": 200, "msg": "用户信息更新成功"})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"更新失败：{str(e)}"})

# ==================== 修改密码 ====================
@ns.route('/<string:user_id>/password')
class PasswordChange(Resource):
    @ns.expect(change_password_model)
    def put(self, user_id):
        """修改用户密码"""
        user = User.query.get(user_id)
        if not user:
            return make_response({"code": 404, "msg": "用户不存在"})

        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求数据为空"})

        current_password = data.get("current_password")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if not current_password or not new_password or not confirm_password:
            return make_response({"code": 400, "msg": "缺少必填字段"})

        if not user.check_password(current_password):
            return make_response({"code": 400, "msg": "当前密码不正确"})

        if new_password != confirm_password:
            return make_response({"code": 400, "msg": "两次输入的新密码不一致"})

        user.set_password(new_password)
        try:
            db.session.commit()
            return make_response({"code": 200, "msg": "密码修改成功"})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"密码修改失败：{str(e)}"})

# ==================== 获取用户信息 ====================
@ns.route('/<string:user_id>/info')
class UserInfo(Resource):
    def get(self, user_id):
        """获取用户基本信息"""
        user = User.query.get(user_id)
        if not user:
            return make_response({"code": 404, "msg": "用户不存在", "data": {}})

        # 如果有头像，生成带时间戳的 URL 避免缓存
        avatar_url = None
        if user.avatar:
            timestamp = int(time.time())
            avatar_name = f"avatar_{timestamp}.jpg"
            avatar_url = url_for('useravatarview_with_name', user_id=user.user_id, filename=avatar_name, _external=True)

        user_data = {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "avatar_url": avatar_url,
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None
        }

        return make_response({"code": 200, "msg": "获取成功", "data": user_data})
# ==================== 上传头像 ====================
@ns.route('/<string:user_id>/avatar')
class UserAvatar(Resource):
    def post(self, user_id):
        """上传或更新用户头像"""
        user = User.query.get(user_id)
        if not user:
            return make_response({"code": 404, "msg": "用户不存在"})

        if 'avatar' not in request.files:
            return make_response({"code": 400, "msg": "请上传头像文件"})

        file = request.files['avatar']
        try:
            # 压缩图片
            img = Image.open(file)
            img = img.convert('RGB')
            img.thumbnail((256, 256))

            # 保存到二进制
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85)
            user.avatar = img_bytes.getvalue()

            db.session.commit()

            # 生成带时间戳的头像 URL，避免缓存
            timestamp = int(time.time())
            avatar_name = f"avatar_{timestamp}.jpg"
            avatar_url = url_for('useravatarview_with_name', user_id=user.user_id, filename=avatar_name, _external=True)

            return make_response({"code": 200, "msg": "头像上传成功", "data": {"url": avatar_url}})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"头像上传失败：{str(e)}"})

# ==================== 获取头像 ====================
@ns.route('/<string:user_id>/avatar/view/<string:filename>', endpoint='useravatarview_with_name')
class UserAvatarView(Resource):
    def get(self, user_id, filename=None):
        """获取用户头像（返回图片）"""
        user = User.query.get(user_id)
        if not user or not user.avatar:
            return make_response({"code": 404, "msg": "用户头像不存在"})

        return Response(user.avatar, mimetype='image/jpeg')
