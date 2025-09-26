# app.py
from flask import Flask, request, jsonify
from extensions import db
import config
from routes.register import register_bp
from routes.login import login_bp
from routes.address import address_bp
from routes.user import user_bp
from routes.product import product_bp
from routes.cart import cart_bp
from routes.order import order_bp
from routes.webhook import webhook_bp

app = Flask(__name__)
app.config.from_object(config)
app.config['DEBUG'] = True   # 打开调试模式
db.init_app(app)
app.register_blueprint(register_bp)
app.register_blueprint(login_bp)
app.register_blueprint(address_bp)
app.register_blueprint(user_bp)
app.register_blueprint(product_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(order_bp)
app.register_blueprint(webhook_bp)

with app.app_context():
    db.create_all()  # 创建数据表

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
