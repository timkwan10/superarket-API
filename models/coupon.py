import uuid
from datetime import datetime
from extensions import db

class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    discount_amount = db.Column(db.Float, default=0)
    discount_percent = db.Column(db.Float, default=0)
    min_order_amount = db.Column(db.Float, default=0)
    valid_until = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(255), nullable=True)

    # 图片二进制存储
    image = db.Column(db.LargeBinary, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    image_mime = db.Column(db.String(50), nullable=True)

    users = db.relationship("UserCoupon", back_populates="coupon", cascade="all, delete-orphan")

    def to_dict(self, base_url=None):
        return {
            "coupon_id": self.id,
            "name": self.name,
            "discount_amount": self.discount_amount,
            "discount_percent": self.discount_percent,
            "min_order_amount": self.min_order_amount,
            "valid_until": self.valid_until.strftime("%Y-%m-%d %H:%M:%S") if self.valid_until else "",
            "description": self.description,
            "image_url": f"{base_url}/coupon/image/{self.id}" if self.image and base_url else None
        }

class UserCoupon(db.Model):
    __tablename__ = "user_coupons"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(20), db.ForeignKey("users.user_id"), nullable=False)
    coupon_id = db.Column(db.String(36), db.ForeignKey("coupons.id"), nullable=False)
    status = db.Column(db.String(20), default="available")
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("coupons", cascade="all, delete-orphan"))
    coupon = db.relationship("Coupon", back_populates="users")
