from extensions import db

class SellerAddress(db.Model):
    __tablename__ = 'seller_addresses'

    id = db.Column(db.Integer, primary_key=True)
    # 🔹 外键改为 users.id
    seller_id = db.Column(db.String(64), db.ForeignKey('users.user_id'), nullable=False)
    contact_name = db.Column(db.String(50), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    street_address = db.Column(db.String(255), nullable=False)
    apartment = db.Column(db.String(100))
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    is_default = db.Column(db.Boolean, default=False)

    # 🔹 改为关联 User
    seller = db.relationship('User', backref='seller_addresses')
