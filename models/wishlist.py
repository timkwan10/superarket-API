# models/wishlist.py
from extensions import db
from datetime import datetime

class Wishlist(db.Model):
    __tablename__ = 'wishlist'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), db.ForeignKey('users.user_id'), nullable=False)
    product_id = db.Column(db.String(64), db.ForeignKey('products.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系可选
    product = db.relationship('Product', backref='wishlisted_by')
    user = db.relationship('User', backref='wishlist_items')
