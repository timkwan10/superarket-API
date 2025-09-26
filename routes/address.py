from flask import Blueprint, jsonify, request
from models.address import Address
from extensions import db


address_bp = Blueprint("address", __name__)

@address_bp.route("/addresses/<user_id>", methods=["GET"])
def get_addresses(user_id):
    addresses = Address.query.filter_by(user_id=user_id).all()
    result = []
    for addr in addresses:
        result.append({
            "id": addr.id,
            "recipient_name": addr.recipient_name,
            "contact_number": addr.contact_number,
            "street_address": addr.street_address,
            "apartment": addr.apartment,
            "city": addr.city,
            "state": addr.state,
            "postal_code": addr.postal_code,
            "country": addr.country,
            "is_default": addr.is_default,
        })
    return jsonify({"code": 0, "message": "success", "data": result})

@address_bp.route("/addresses/<user_id>", methods=["POST"])
def add_address(user_id):
    data = request.get_json()

    # 如果设置了默认地址，需要把其他的默认取消
    if data.get("is_default", False):
        Address.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})

    new_addr = Address(
        user_id=user_id,
        recipient_name=data["recipient_name"],
        contact_number=data["contact_number"],
        street_address=data["street_address"],
        apartment=data.get("apartment"),
        city=data["city"],
        state=data["state"],
        postal_code=data["postal_code"],
        country=data["country"],
        is_default=data.get("is_default", False)
    )
    db.session.add(new_addr)
    db.session.commit()

    return jsonify({"code": 0, "message": "address added successfully"})