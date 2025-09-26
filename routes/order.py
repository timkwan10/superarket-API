import stripe
from flask import Blueprint, request, jsonify
from models.order import Order
from models.address import Address
from extensions import db

order_bp = Blueprint("order", __name__)

# Stripe 配置（建议用环境变量存储）
stripe.api_key = "sk_test_51Rj9qR00sr4YVvA6TiOStw5xJ6HUJMFrdDTkgK3R3jY7xlJo3gBYHGirpia91stTdKTxCfaisaBFYghZMF9o9kj100NnL2sQfN"  # ✅ 你的 Stripe Secret Key


@order_bp.route("/api/create-order", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空，需为JSON格式"}), 400

    # 1. 校验用户ID
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id 为必填项"}), 400

    # 2. 地址逻辑（和你之前一样）
    address_id = data.get("address_id")
    new_address_data = {
        "recipient_name": data.get("recipient_name"),
        "contact_number": data.get("contact_number"),
        "street_address": data.get("street_address"),
        "apartment": data.get("apartment"),
        "city": data.get("city"),
        "state": data.get("state"),
        "postal_code": data.get("postal_code"),
        "country": data.get("country"),
        "is_default": data.get("is_default", False)
    }

    user_address = None
    if address_id:
        user_address = Address.query.filter_by(id=address_id, user_id=user_id).first()
        if not user_address:
            return jsonify({"error": "地址不存在或不属于该用户"}), 404
    else:
        required_address_fields = ["recipient_name", "contact_number", "street_address", "city", "state", "postal_code", "country"]
        for field in required_address_fields:
            if not new_address_data[field]:
                return jsonify({"error": f"新地址的「{field}」为必填项"}), 400

        if new_address_data["is_default"]:
            Address.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})

        user_address = Address(user_id=user_id, **new_address_data)
        db.session.add(user_address)
        db.session.flush()

    # 3. 校验订单字段
    required_order_fields = ["delivery_slot", "payment_method", "item_total", "tax", "delivery_fee", "discount", "grand_total"]
    for field in required_order_fields:
        if field not in data:
            return jsonify({"error": f"订单字段「{field}」为必填项"}), 400

    try:
        item_total = float(data["item_total"])
        tax = float(data["tax"])
        delivery_fee = float(data["delivery_fee"])
        discount = float(data["discount"])
        grand_total = float(data["grand_total"])
    except (ValueError, TypeError):
        return jsonify({"error": "金额字段必须为有效数字"}), 400

    valid_payment_methods = ["Credit/Debit Card", "Apple Pay/Google Pay", "Alipay", "WeChat Pay"]
    if data["payment_method"] not in valid_payment_methods:
        return jsonify({"error": "支付方式不合法"}), 400

    # 4. 创建订单
    new_order = Order(
        user_id=user_id,
        address_id=user_address.id,
        delivery_slot=data["delivery_slot"],
        payment_method=data["payment_method"],
        item_total=item_total,
        tax=tax,
        delivery_fee=delivery_fee,
        discount=discount,
        grand_total=grand_total
    )

    try:
        db.session.add(new_order)
        db.session.commit()

        # ✅ 5. 创建 Stripe Checkout Session
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],   # 你也可以加上 'alipay', 'wechat_pay'
                line_items=[{
                    "price_data": {
                        "currency": "usd",  # 根据实际情况设置币种
                        "product_data": {
                            "name": f"Order #{new_order.order_id}"
                        },
                        "unit_amount": int(grand_total * 100),  # Stripe 要求金额单位是分
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="myapp://payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="myapp://payment-cancel",
                metadata={"order_id": new_order.order_id}  # ✅ 把订单号传进去，方便 webhook 回调更新状态
            )
            payment_url = checkout_session.url
        except Exception as stripe_err:
            return jsonify({"error": f"Stripe 创建支付链接失败: {str(stripe_err)}"}), 500

        # ✅ 6. 返回订单信息 + 支付链接
        return jsonify({
            "message": "订单创建成功",
            "order_id": new_order.order_id,
            "address": {
                "id": user_address.id,
                "recipient_name": user_address.recipient_name,
                "street_address": user_address.street_address,
                "is_default": user_address.is_default
            },
            "grand_total": new_order.grand_total,
            "status": new_order.status,
            "created_at": new_order.created_at.isoformat(),
            "payment_url": payment_url   # ✅ 前端跳转这个链接完成支付
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"创建订单失败：{str(e)}"}), 500
