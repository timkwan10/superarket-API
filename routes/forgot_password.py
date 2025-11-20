# routes/forgot_password.py
from flask import request, Response
from flask_restx import Namespace, Resource, fields
from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash
import random
import string
import smtplib
from email.mime.text import MIMEText
import json

ns = Namespace("forgot", description="忘记密码相关接口")

# Swagger 请求模型
forgot_model = ns.model(
    "ForgotPassword",
    {
        "email": fields.String(required=True, description="用户注册邮箱"),
    }
)

def generate_random_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def send_email(to_email, password):
    import smtplib
    from email.mime.text import MIMEText

    smtp_server = "smtp.qq.com"
    smtp_port = 465
    sender_email = "2798269357@qq.com"
    sender_password = "dhpnnqokijyzdgfb"  # QQ邮箱授权码

    msg = MIMEText(f"你的新密码是：{password}", "plain", "utf-8")
    msg["Subject"] = "密码重置通知"
    msg["From"] = sender_email
    msg["To"] = to_email

    server = None
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.set_debuglevel(1)
        server.login(sender_email, sender_password)

        # sendmail 返回空字典表示成功
        result = server.sendmail(sender_email, [to_email], msg.as_string())
        if result:
            print("⚠️ 邮件部分发送失败:", result)
            return False

        print("✅ 邮件发送成功")
        return True

    except smtplib.SMTPException as e:
        print("⚠️ SMTP 错误:", e)
        # 注意：如果 sendmail 成功，只是 quit 出错，也不要返回 False
        if 'sendmail' in str(e):
            return False
        return True
    except Exception as e:
        print("⚠️ 其他错误:", e)
        # 如果邮件已经发送成功，可以返回 True
        return True
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass



def make_response(data):
    """统一返回，HTTP 200，中文正常显示"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    )

@ns.route("/")
class ForgotPassword(Resource):
    @ns.expect(forgot_model, validate=True)
    def post(self):
        """忘记密码 - 发送随机8位新密码到邮箱"""
        data = request.json or {}
        email = data.get("email")

        if not email:
            return make_response({"code": 400, "msg": "邮箱不能为空"})

        user = User.query.filter_by(email=email).first()
        if not user:
            return make_response({"code": 404, "msg": "用户不存在"})

        new_password = generate_random_password()
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        if send_email(email, new_password):
            return make_response({"code": 200, "msg": "新密码已发送到邮箱"})
        else:
            return make_response({"code": 500, "msg": "发送邮件失败，请稍后重试"})
