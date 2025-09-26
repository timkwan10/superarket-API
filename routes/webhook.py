import stripe
from flask import Blueprint, request, jsonify
from extensions import db
from models.order import Order

webhook_bp = Blueprint("stripe_webhook", __name__)

# 你的 Webhook 签名秘钥（Dashboard -> Developers -> Webhooks -> Signing secret）
STRIPE_WEBHOOK_SECRET = "whsec_up7ULq2apMbJQ5LYmgwY4JOfZYytNRGc"

@webhook_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        # ✅ 验证签名
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    # ✅ 处理不同事件
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if order_id:
            order = Order.query.filter_by(order_id=order_id).first()
            if order:
                order.status = "PAID"   # 更新为已支付
                db.session.commit()
                print(f"✅ 订单 {order_id} 已更新为已支付")
    elif event["type"] == "payment_intent.payment_failed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        if order_id:
            order = Order.query.filter_by(order_id=order_id).first()
            if order:
                order.status = "FAILED"
                db.session.commit()
                print(f"❌ 订单 {order_id} 支付失败")

    return jsonify({"status": "success"}), 200
