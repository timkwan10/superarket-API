from flask_restx import Namespace, Resource, fields
from flask import request, Response
import stripe
from extensions import db
from models.order import Order
from models.coupon import UserCoupon
from datetime import datetime
import json
from models.cart import ShoppingCart


ns = Namespace('stripe-webhook', description='Stripe 支付回调接口')

# Webhook 签名秘钥
STRIPE_WEBHOOK_SECRET = "whsec_5a4PuCx7KxqUMxAyfbKeHA0PQZTBuMYP"

SUPPORTED_EVENTS = [
    "checkout.session.completed",
    "payment_intent.payment_failed"
]


def make_response(data):
    """统一返回格式，HTTP 永远 200"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    )


def mark_coupon_used(user_id, coupon_id):
    """标记用户优惠券为已使用"""
    try:
        user_coupon = UserCoupon.query.filter_by(
            user_id=user_id,
            coupon_id=coupon_id,
            status='available'   # 只修改未使用的
        ).first()

        if not user_coupon:
            print(f"⚠️ 用户 {user_id} 的优惠券 {coupon_id} 不存在或已使用")
            return False

        user_coupon.status = 'used'
        user_coupon.used_at = datetime.utcnow()

        db.session.commit()
        print(f"🎉 优惠券 {coupon_id} 已成功标记为 used")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ 优惠券标记为 used 时发生数据库错误：{str(e)}")
        return False


@ns.route('/callback')
class StripeWebhook(Resource):
    def post(self):
        """Stripe 支付成功/失败回调（由 Stripe 自动调用）"""

        payload = request.data
        sig_header = request.headers.get("Stripe-Signature")

        # 1. 校验 Stripe 签名
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            print("❌ Stripe 回调：Payload 无效")
            return make_response({"code": 1, "msg": "Invalid payload"})
        except stripe.error.SignatureVerificationError:
            print("❌ Stripe 回调：签名校验失败")
            return make_response({"code": 1, "msg": "Invalid signature"})

        event_type = event.get("type")
        session_data = event.get("data", {}).get("object", {})

        # 不处理未注册事件
        if event_type not in SUPPORTED_EVENTS:
            print(f"⚠️ 忽略事件：{event_type}")
            return make_response({"code": 0, "msg": f"Ignored event: {event_type}"})

        # 订单 ID
        order_id = session_data.get("metadata", {}).get("order_id")
        if not order_id:
            print("❌ 无 order_id")
            return make_response({"code": 1, "msg": "Missing order_id in metadata"})

        try:
            order = Order.query.filter_by(order_id=order_id).first()
            if not order:
                print(f"❌ 订单不存在：{order_id}")
                return make_response({"code": 1, "msg": f"Order {order_id} not found"})

            # 2. 支付成功
            # 2. 支付成功
            if event_type == "checkout.session.completed":
                try:
                    # 更新订单状态
                    order.status = "paid"
                    db.session.add(order)

                    # 如果订单使用了优惠券 → 标记为 used
                    if order.coupon_id:
                        mark_coupon_used(order.user_id, order.coupon_id)

                    # ✅ 清空用户购物车
                    ShoppingCart.query.filter_by(user_id=order.user_id).delete()
                    print(f"🗑 用户 {order.user_id} 的购物车已清空")

                    # 提交事务
                    db.session.commit()
                    print(f"🎉 支付成功，订单 {order_id} → PAID")

                    return make_response({"code": 200, "msg": "支付成功", "order_id": order_id})

                except Exception as e:
                    db.session.rollback()
                    print("🔥 数据库更新失败:", str(e))
                    return make_response({"code": 1, "msg": f"Database error: {str(e)}"})

            # 3. 支付失败
            elif event_type == "payment_intent.payment_failed":
                order.status = "failed"
                db.session.commit()

                print(f"❌ 支付失败！订单 {order_id} 已标记为 FAILED")
                print(f"📢 回调结果：支付失败，已通知前端（前端可再次查询订单状态）")

                return make_response({
                    "code": 200,
                    "msg": "支付失败",
                    "order_id": order_id
                })

        except Exception as e:
            db.session.rollback()
            print(f"🔥 数据库异常: {str(e)}")
            return make_response({"code": 1, "msg": f"Database error: {str(e)}"})
