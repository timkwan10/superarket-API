from extensions import db
from datetime import datetime

class ShoppingCart(db.Model):
    __tablename__ = "shopping_carts"  # 表名

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="购物车项唯一ID")
    user_id = db.Column(
        db.String(20),
        db.ForeignKey("users.user_id", ondelete="CASCADE"),  # 关联用户表的user_id
        nullable=False,
        comment="用户ID（外键）"
    )
    product_id = db.Column(
        db.String(20),
        nullable=False,
        comment="商品ID"
    )
    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        comment="商品数量"
    )
    price = db.Column(
        db.Float,
        nullable=False,
        default=0.0,
        comment="商品单价"
    )
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="添加时间"
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="最后更新时间"
    )

    # 关联用户表（反向引用：通过user.carts可访问该用户的所有购物车项）
    user = db.relationship("User", backref=db.backref("carts", lazy=True, cascade="all, delete-orphan"))

    # 约束：同一用户的同一商品只能有一条记录（避免重复添加）
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uk_user_product"),
        db.CheckConstraint("quantity > 0", name="chk_quantity_positive"),  # 确保数量为正整数
        db.CheckConstraint("price >= 0", name="chk_price_nonnegative")      # 确保价格非负
    )

    def __repr__(self):
        return f"<ShoppingCart {self.user_id}: {self.product_id} x {self.quantity} @ {self.price}>"
