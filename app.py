from flask import Flask
from flask_restx import Api
from extensions import db
import config
from flask import Flask, Response

# 导入蓝图和命名空间
from routes.register import ns as register_ns
from routes.login import ns as login_ns
from routes.address import ns as address_ns
from routes.user import ns as user_ns
from routes.product import ns as product_ns
from routes.cart import ns as cart_ns
from routes.order import ns as order_ns
from routes.forgot_password import ns as forgot_ns
from routes.coupon import ns as coupon_ns
from routes.seller_address import ns as seller_address_ns
from routes.wishlist import ns as wishlist_ns
from routes.webhook import ns as webhook_ns
from routes.notification import ns as notification_ns

app = Flask(__name__)
app.config.from_object(config)
app.config['DEBUG'] = True
app.config['JSON_AS_ASCII'] = False

db.init_app(app)

# 创建 Flask-RESTX API
api = Api(
    app,
    version='1.0',
    title='My API',
    description='API 文档（Swagger UI）',
    doc='/swagger/'  # Swagger UI访问地址
)

@app.route("/payment-success")
def payment_success():
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>支付成功</title></head>
    <body style="text-align:center;margin-top:50px;font-family:sans-serif;">
        <h1 style="color:green;">支付成功 🎉</h1>
        <p>请返回 App 查看订单详情</p>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.route("/payment-failed")
def payment_failed():
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>支付失败</title></head>
    <body style="text-align:center;margin-top:50px;font-family:sans-serif;">
        <h1 style="color:red;">支付失败 ❌</h1>
        <p>请返回 App 重试或选择其他支付方式</p>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")

# 注册命名空间
api.add_namespace(register_ns, path='/register')
api.add_namespace(login_ns, path='/login')
api.add_namespace(address_ns, path='/address')
api.add_namespace(user_ns, path='/user')
api.add_namespace(product_ns, path='/product')
api.add_namespace(cart_ns, path='/cart')
api.add_namespace(order_ns, path='/order')
api.add_namespace(forgot_ns, path='/forgot')
api.add_namespace(coupon_ns, path='/coupon')
api.add_namespace(seller_address_ns, path='/seller')
api.add_namespace(wishlist_ns, path='/wishlist')
api.add_namespace(webhook_ns, path='/webhook')
api.add_namespace(notification_ns, path='/notification')

with app.app_context():
    db.create_all()  # 创建数据表

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
