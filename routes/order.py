from flask_restx import Namespace, Resource, fields
from extensions import db
from models.order import Order
from models.orderitem import OrderItem
from models.address import Address
from models.cart import ShoppingCart
import stripe
from flask import Response
import json
from datetime import datetime
from datetime import timedelta
from flask import request
from models.product import Product, ProductImage

# Stripe 配置（建议使用环境变量存储）
stripe.api_key = "sk_test_51Rj9qR00sr4YVvA6TiOStw5xJ6HUJMFrdDTkgK3R3jY7xlJo3gBYHGirpia91stTdKTxCfaisaBFYghZMF9o9kj100NnL2sQfN"

ns = Namespace('order', description='Order operations')

def generate_order_id():
    today = datetime.now().strftime("%Y%m%d")

    # 查询今日最大订单号
    last_order = Order.query.filter(Order.order_id.like(f"{today}%")) \
                            .order_by(Order.order_id.desc()) \
                            .first()

    if last_order:
        # 取出最后四位序号
        last_seq = int(last_order.order_id[-4:])
        new_seq = last_seq + 1
    else:
        new_seq = 1

    # 新的订单号（补齐4位）
    return f"{today}{new_seq:04d}"

# 地址模型
address_model = ns.model('Address', {
    'recipient_name': fields.String(required=True, description='收件人姓名'),
    'contact_number': fields.String(required=True, description='联系电话'),
    'street_address': fields.String(required=True, description='街道地址'),
    'apartment': fields.String(description='公寓/楼号'),
    'city': fields.String(required=True, description='城市'),
    'state': fields.String(required=True, description='省/州'),
    'postal_code': fields.String(required=True, description='邮政编码'),
    'country': fields.String(required=True, description='国家'),
    'is_default': fields.Boolean(description='是否默认地址', default=False)
})

# 商品明细模型
order_item_model = ns.model('OrderItem', {
    'product_id': fields.String(required=True, description='商品ID'),
    'quantity': fields.Integer(required=True, description='商品数量'),
    'price': fields.Float(required=True, description='商品单价')
})

# 创建订单请求模型
create_order_model = ns.model('CreateOrder', {
    'user_id': fields.String(required=True, description='用户ID'),
    'address_id': fields.String(description='已有地址ID'),
    'delivery_slot': fields.String(required=True, description='配送时间段'),
    'payment_method': fields.String(required=True, description='支付方式'),
    'item_total': fields.Float(required=True, description='商品总额'),
    'tax': fields.Float(required=True, description='税费'),
    'delivery_fee': fields.Float(required=True, description='配送费'),
    'discount': fields.Float(required=True, description='折扣'),
    'grand_total': fields.Float(required=True, description='订单总金额'),
    'coupon_id': fields.String(description='优惠券ID'),

    # 新增备注字段
    'remark': fields.String(description='订单备注'),

    # 新增地址简化版字段，只保留收件人和电话
    'recipient_name': fields.String(description='新地址收件人'),
    'contact_number': fields.String(description='新地址联系电话'),
    'is_default': fields.Boolean(description='是否默认地址', default=False),

})


def make_response(data):
    """统一返回 JSON，中文不转义，HTTP 状态码固定 200"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )

@ns.route('/create-order')
class CreateOrder(Resource):
    @ns.expect(create_order_model)
    def post(self):
        """创建订单并生成 Stripe 支付链接（自动读取购物车商品）"""
        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求体不能为空"})

        user_id = data.get("user_id")
        if not user_id:
            return make_response({"code": 400, "msg": "user_id 为必填项"})

        # =========== 地址处理 ===========
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

        if address_id:
            user_address = Address.query.filter_by(id=address_id, user_id=user_id).first()
            if not user_address:
                return make_response({"code": 401, "msg": "地址不存在或不属于该用户"})
        else:
            required_fields = ["recipient_name", "contact_number", "street_address", "city", "state", "postal_code", "country"]
            for field in required_fields:
                if not new_address_data[field]:
                    return make_response({"code": 401, "msg": f"新地址的「{field}」为必填项"})

            if new_address_data["is_default"]:
                Address.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})

            user_address = Address(user_id=user_id, **new_address_data)
            db.session.add(user_address)
            db.session.flush()

        # =========== 读取购物车 ===========
        cart_items = ShoppingCart.query.filter_by(user_id=user_id).all()
        if not cart_items or len(cart_items) == 0:
            return make_response({"code": 401, "msg": "购物车为空，无法创建订单"})

        # 计算金额
        item_total = 0
        order_items_data = []
        for cart_item in cart_items:
            product = Product.query.filter_by(id=cart_item.product_id).first()
            if not product:
                continue
            price = product.price  # 或使用 product.discount_price
            quantity = cart_item.quantity
            item_total += price * quantity

            order_items_data.append({
                "product_id": product.id,
                "product_name": product.name,
                "quantity": quantity,
                "price": price
            })

        tax = 0  # 可根据规则计算
        delivery_fee = data.get("delivery_fee", 0)
        discount = data.get("discount", 0)
        grand_total = item_total + tax + delivery_fee - discount

        # =========== 生成订单号 ===========
        new_order_id = generate_order_id()

        # =========== 创建订单 ===========
        new_order = Order(
            order_id=new_order_id,
            user_id=user_id,
            address_id=user_address.id,
            delivery_slot=data["delivery_slot"],
            payment_method=data["payment_method"],
            item_total=item_total,
            tax=tax,
            delivery_fee=delivery_fee,
            discount=discount,
            grand_total=grand_total,
            remark=data.get("remark", ""),
            coupon_id=data.get("coupon_id")
        )

        try:
            db.session.add(new_order)
            db.session.flush()

            # 写入订单商品
            for item in order_items_data:
                order_item = OrderItem(
                    order_id=new_order.order_id,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    price=item["price"]
                )
                db.session.add(order_item)

            # 提交事务
            db.session.commit()

            # =========== Stripe ===========
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"Order #{new_order.order_id}"},
                        "unit_amount": int(grand_total * 100),
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="http://47.113.100.224:8000/payment-success",
                cancel_url="http://47.113.100.224:8000/payment-failed",
                metadata={"order_id": new_order.order_id}
            )

            return make_response({
                "code": 200,
                "msg": "订单创建成功",
                "data": {
                    "order_id": new_order.order_id,
                    "items_count": len(order_items_data),
                    "payment_url": checkout_session.url
                }
            })

        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"创建订单失败：{str(e)}"})


@ns.route('/detail/<string:order_id>')
class OrderDetail(Resource):
    def get(self, order_id):
        """获取订单详情（含商品 subtotal 总价、商品名称和图片 URL）"""
        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            return make_response({"code": 404, "msg": "订单不存在"})

        BASE_URL = "http://47.113.100.224:8000/"  # 图片前缀

        # 地址信息
        address_info = None
        if order.address:
            address = order.address
            address_info = {
                "recipient_name": address.recipient_name,
                "contact_number": address.contact_number,
                "street_address": address.street_address,
                "apartment": address.apartment,
                "city": address.city,
                "state": address.state,
                "postal_code": address.postal_code,
                "country": address.country,
            }

        # 商品 items（含 product_name 和 image_url）
        items = []
        subtotal = 0
        for item in order.items:
            product = Product.query.filter_by(id=item.product_id).first()
            if product:
                if product.cover_image:
                    image_url = BASE_URL + product.cover_image
                elif product.images and len(product.images) > 0:
                    image_url = BASE_URL + product.images[0].image_path
                else:
                    image_url = None
                product_name = product.name
                sku = product.sku
            else:
                image_url = None
                product_name = None
                sku = None

            items.append({
                "product_id": item.product_id,
                "product_name": product_name,
                "sku": sku,
                "quantity": item.quantity,
                "price": item.price,
                "subtotal": item.quantity * item.price,
                "image_url": image_url
            })
            subtotal += item.price * item.quantity

        return make_response({
            "code": 200,
            "msg": "获取订单详情成功",
            "data": {
                "order_id": order.order_id,
                "user_id": order.user_id,
                "address": address_info,
                "delivery_slot": order.delivery_slot,
                "payment_method": order.payment_method,
                "item_total": order.item_total,
                "tax": order.tax,
                "delivery_fee": order.delivery_fee,
                "discount": order.discount,
                "grand_total": order.grand_total,
                "status": order.status,
                "created_at": (order.created_at + timedelta(hours=8)).strftime("%b%d,%Y,%I:%M %p"),
                "coupon_id": order.coupon_id,
                "items": items,
                "items_count": len(items)
            }
        })


from flask_restx import reqparse

# 分页参数解析器
pagination_parser = reqparse.RequestParser()
pagination_parser.add_argument('page', type=int, default=1, help='当前页码（默认 1）')
pagination_parser.add_argument('page_size', type=int, default=10, help='每页数量（默认 10）')


@ns.route('/history/<string:user_id>')
class OrderHistory(Resource):

    @ns.expect(pagination_parser)
    def get(self, user_id):
        """获取用户的历史订单（含商品图片 URL，支持分页）"""

        # 获取分页参数
        args = pagination_parser.parse_args()
        page = args.get("page", 1)
        page_size = args.get("page_size", 10)

        BASE_URL = "http://47.113.100.224:8000/"

        # 查询订单
        query = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc())
        total = query.count()
        orders = query.offset((page - 1) * page_size).limit(page_size).all()

        order_list = []
        for order in orders:
            items = []
            for item in order.items:
                product = Product.query.filter_by(id=item.product_id).first()

                if product:
                    if product.cover_image:
                        image_url = BASE_URL + product.cover_image
                    elif product.images:
                        image_url = BASE_URL + product.images[0].image_path
                    else:
                        image_url = None
                else:
                    image_url = None

                items.append({
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price,
                    "image_url": image_url
                })

            order_list.append({
                "order_id": order.order_id,
                "grand_total": order.grand_total,
                "status": order.status,
                "payment_method": order.payment_method,
                "delivery_slot": order.delivery_slot,
                "created_at": (order.created_at + timedelta(hours=8)).strftime("%m/%d/%y"),
                "items": items
            })

        return make_response({
            "code": 200,
            "msg": "获取历史订单成功",
            "data": {
                "orders": order_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        })


@ns.route('/delivery-slots')
class DeliverySlots(Resource):
    def get(self):
        """获取配送时间段列表"""

        # 你可以根据需要随时修改或从数据库加载
        delivery_slots = [
            "08:00-10:00",
            "10:00-12:00",
            "12:00-14:00",
            "14:00-16:00",
            "16:00-18:00"
        ]

        return make_response({
            "code": 200,
            "msg": "获取配送时间段成功",
            "data": delivery_slots
        })

@ns.route('/status/<int:order_id>')
class OrderStatus(Resource):
    def get(self, order_id):
        """获取订单状态"""
        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            return make_response({
                "code": 404,
                "msg": "订单不存在"
            })

        return make_response({
            "code": 200,
            "msg": "获取订单状态成功",
            "data": {
                "order_id": order.order_id,
                "status": order.status,
                "grand_total": order.grand_total,
                "coupon_id": order.coupon_id,
                "created_at": order.created_at.isoformat()
            }
        })