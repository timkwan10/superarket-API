from extensions import db

class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(20), db.ForeignKey('users.user_id'), unique=True, nullable=False)

    email_promotion = db.Column(db.Boolean, default=False)   # 是否开启邮件推广
    push_enable = db.Column(db.Boolean, default=False)       # 是否开启推送通知

    updated_at = db.Column(db.DateTime,
                           server_default=db.func.now(),
                           onupdate=db.func.now())

    # 可选：返回字典方便序列化
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "email_promotion": self.email_promotion,
            "push_enable": self.push_enable,
            "updated_at": self.updated_at
        }
