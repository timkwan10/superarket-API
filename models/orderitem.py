from extensions import db
from datetime import datetime

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    order_id = db.Column(db.String(50), db.ForeignKey("orders.order_id"), nullable=False)
    product_id = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    order = db.relationship("Order", backref="items")
