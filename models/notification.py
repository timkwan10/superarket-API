from extensions import db
from datetime import datetime


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)  # 接收用户ID
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    image_data = db.Column(db.LargeBinary, nullable=True)  # 图片二进制
    image_name = db.Column(db.String(255), nullable=True)  # 图片原始文件名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
