from flask_restx import Namespace, Resource, fields,reqparse
from flask import request, Response
from extensions import db
from models.user_settings import UserSettings
from models.notification import Notification
from werkzeug.datastructures import FileStorage
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

notification_model = ns.model('Notification', {
    'user_id': fields.String(required=True, description='用户ID'),
    'title': fields.String(required=True, description='通知标题'),
    'content': fields.String(description='通知内容'),
    'image_url': fields.String(description='通知图片URL')
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
        """启用或禁用 Push 通知 """

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

# ===========================
# 发布通知
# ===========================
notification_parser = ns.parser()
notification_parser.add_argument('user_id', type=str, required=True, location='form')
notification_parser.add_argument('title', type=str, required=True, location='form')
notification_parser.add_argument('content', type=str, required=False, location='form')
notification_parser.add_argument('image', type=FileStorage, required=False, location='files')

@ns.route('/publish')
class PublishNotification(Resource):
    @ns.expect(notification_parser)
    def post(self):
        """发布通知给指定用户"""
        args = notification_parser.parse_args()
        user_id = args.get('user_id')
        title = args.get('title')
        content = args.get('content')
        image_file = args.get('image')

        if not user_id or not title:
            return make_response({"code": 400, "msg": "参数不完整"})

        notif = Notification(
            user_id=user_id,
            title=title,
            content=content
        )

        if image_file:
            notif.image_data = image_file.read()
            notif.image_name = image_file.filename

        db.session.add(notif)
        db.session.commit()

        return make_response({
            "code": 200,
            "msg": "通知发布成功",
            "data": {
                "id": notif.id,
                "title": notif.title,
                "content": notif.content,
                "image_url": f"/notification/image/{notif.id}" if notif.image_data else None,
                "created_at": notif.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })

# ===========================
# 获取用户通知列表（分页）
# ===========================
import base64
from datetime import timedelta
from extensions import db
from models.notification import Notification
from flask import Response, send_file
from io import BytesIO
BASE_URL = "http://47.113.100.224:8000"

# 图片访问路由
@ns.route('/image/<int:id>')
class NotificationImage(Resource):
    def get(self, id):
        """查看单个通知照片"""
        notif = Notification.query.get(id)
        if not notif or not notif.image_data:
            return make_response({"code": 404, "msg": "图片不存在"})

        ext = notif.image_name.split('.')[-1].lower()
        mimetype = "image/png"
        if ext in ('jpg', 'jpeg'):
            mimetype = "image/jpeg"
        elif ext == 'gif':
            mimetype = "image/gif"

        return send_file(BytesIO(notif.image_data), mimetype=mimetype, download_name=notif.image_name)


# 分页通知列表
parser = reqparse.RequestParser()
parser.add_argument('page', type=int, default=1, help='页码')
parser.add_argument('page_size', type=int, default=10, help='每页数量')

@ns.route('/list/<string:user_id>')
class NotificationList(Resource):
    @ns.expect(parser)
    def get(self, user_id):
        """获取指定用户通知列表（支持分页）"""
        args = parser.parse_args()
        page = args.get('page', 1)
        page_size = args.get('page_size', 10)

        pagination = Notification.query.filter_by(user_id=user_id) \
            .order_by(Notification.created_at.desc()) \
            .paginate(page=page, per_page=page_size, error_out=False)

        data_list = []
        for n in pagination.items:
            # 调整时间 +8小时
            created_time = None
            if n.created_at:
                created_time = (n.created_at + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

            # 返回可访问 URL
            image_url = f"{BASE_URL}/notification/image/{n.id}" if n.image_data else None

            data_list.append({
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "image_url": image_url,
                "created_at": created_time
            })

        return make_response({
            "code": 200,
            "msg": "success",
            "data": {
                "total": pagination.total,
                "page": pagination.page,
                "page_size": pagination.per_page,
                "pages": pagination.pages,
                "notifications": data_list
            }
        })

# ===========================
# 发送通知给所有启用 Push 的用户
# ===========================
push_publish_parser = ns.parser()
push_publish_parser.add_argument('title', type=str, required=True, location='form')
push_publish_parser.add_argument('content', type=str, required=False, location='form')
push_publish_parser.add_argument('image', type=FileStorage, required=False, location='files')

@ns.route('/publish/push')
class PublishPushNotification(Resource):
    @ns.expect(push_publish_parser)
    def post(self):
        """发送通知给所有启用 Push 的用户"""
        args = push_publish_parser.parse_args()
        title = args.get('title')
        content = args.get('content')
        image_file = args.get('image')

        if not title:
            return make_response({"code": 400, "msg": "标题不能为空"})

        # 查询所有启用 push 的用户
        users = UserSettings.query.filter_by(push_enable=True).all()
        if not users:
            return make_response({"code": 200, "msg": "没有启用 Push 的用户"})

        image_bytes = None
        image_name = None
        if image_file:
            image_bytes = image_file.read()
            image_name = image_file.filename

        notifications = []
        for u in users:
            notif = Notification(
                user_id=u.user_id,
                title=title,
                content=content
            )
            if image_bytes:
                notif.image_data = image_bytes  # 直接使用已读的字节
                notif.image_name = image_name

            db.session.add(notif)
            notifications.append(notif)

        db.session.commit()

        return make_response({
            "code": 200,
            "msg": f"成功发送给 {len(notifications)} 个启用 Push 的用户"
        })


# ===========================
# 发送通知给所有启用 Email Promotion 的用户
# ===========================
email_publish_parser = ns.parser()
email_publish_parser.add_argument('title', type=str, required=True, location='form')
email_publish_parser.add_argument('content', type=str, required=False, location='form')
email_publish_parser.add_argument('image', type=FileStorage, required=False, location='files')

@ns.route('/publish/email')
class PublishEmailNotification(Resource):
    @ns.expect(email_publish_parser)
    def post(self):
        """发送通知给所有启用 Email Promotion 的用户"""
        args = email_publish_parser.parse_args()
        title = args.get('title')
        content = args.get('content')
        image_file = args.get('image')

        if not title:
            return make_response({"code": 400, "msg": "标题不能为空"})

        # 查询所有启用 email promotion 的用户
        users = UserSettings.query.filter_by(email_promotion=True).all()
        if not users:
            return make_response({"code": 200, "msg": "没有启用 Email Promotion 的用户"})

        image_bytes = None
        image_name = None
        if image_file:
            image_bytes = image_file.read()
            image_name = image_file.filename

        notifications = []
        for u in users:
            notif = Notification(
                user_id=u.user_id,
                title=title,
                content=content
            )
            if image_bytes:
                notif.image_data = image_bytes  # 直接使用已读的字节
                notif.image_name = image_name

            db.session.add(notif)
            notifications.append(notif)

        db.session.commit()

        return make_response({
            "code": 200,
            "msg": f"成功发送给 {len(notifications)} 个启用 Email Promotion 的用户"
        })
