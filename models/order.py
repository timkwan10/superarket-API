from extensions import db
from datetime import datetime
from models.address import Address  # 导入Address模型

class Order(db.Model):
    __tablename__ = "orders"
    order_id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(20), nullable=False, comment="关联用户ID")
    address_id = db.Column(db.Integer, db.ForeignKey("addresses.id"), nullable=False, comment="关联地址ID")
    delivery_slot = db.Column(db.String(50), nullable=False, comment="配送时段")
    payment_method = db.Column(db.String(50), nullable=False, comment="支付方式")
    item_total = db.Column(db.Float, nullable=False, comment="商品总价")
    tax = db.Column(db.Float, nullable=False, comment="税费")
    delivery_fee = db.Column(db.Float, nullable=False, comment="配送费")
    discount = db.Column(db.Float, nullable=False, comment="折扣金额")
    grand_total = db.Column(db.Float, nullable=False, comment="订单总计")

    # ⭐ 新增备注字段
    remark = db.Column(db.String(255), nullable=True, comment="订单备注")
    coupon_id = db.Column(db.String(255), nullable=True, comment="使用的优惠券ID")

    status = db.Column(db.String(20), default="pending", comment="订单状态：pending/paid/delivered等")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联地址表
    address = db.relationship("Address", backref="orders")
