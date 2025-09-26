from extensions import db
import uuid
from datetime import datetime

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.String(50), primary_key=True, default=lambda: "P" + uuid.uuid4().hex[:12])
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    sku = db.Column(db.String(100))
    status = db.Column(db.String(20))
    price = db.Column(db.Float)
    discount_price = db.Column(db.Float)
    stock_quantity = db.Column(db.Integer)
    low_stock_alert = db.Column(db.Integer)
    inventory_status = db.Column(db.String(20))
    short_description = db.Column(db.Text)
    full_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship("ProductImage", backref="product", cascade="all, delete-orphan")

class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(50), db.ForeignKey("products.id"))
    image_path = db.Column(db.String(255), nullable=False)
