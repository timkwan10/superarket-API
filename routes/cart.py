from itertools import product

from flask_restx import Namespace, Resource, fields
from extensions import db
from models.cart import ShoppingCart
from models.product import Product  # 假设你的商品表模型是 Product
from models.user import User
from flask import request, Response
import json

ns = Namespace('cart', description='Shopping Cart operations')
BASE_URL = "http://47.113.100.224:8000/"

# 请求体模型：添加商品到购物车
add_to_cart_model = ns.model('AddToCart', {
    'user_id': fields.String(required=True, description='用户ID'),
    'product_id': fields.String(required=True, description='商品ID'),
    'quantity': fields.Integer(description='数量', default=1)
})

# 返回的购物车项模型
cart_item_model = ns.model('CartItem', {
    'product_id': fields.String(description='商品ID'),
    'quantity': fields.Integer(description='数量')
})

# 返回购物车列表模型
cart_list_model = ns.model('CartList', {
    'user_id': fields.String(description='用户ID'),
    'cart_items': fields.List(fields.Nested(cart_item_model)),
    'total_items': fields.Integer(description='购物车商品种类总数')
})

def make_response(data):
    """统一返回 JSON，中文不转义，HTTP 状态码固定 200"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )


@ns.route('/add-to-cart')
class AddToCart(Resource):
    @ns.expect(add_to_cart_model)
    def post(self):
        """添加商品到购物车"""
        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求体不能为空，需为JSON格式"})

        user_id = data.get('user_id')
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if not user_id or not product_id:
            return make_response({"code": 400, "msg": "user_id 和 product_id 为必填项"})

        try:
            quantity = int(quantity)
            if quantity <= 0:
                return make_response({"code": 400, "msg": "数量必须为正整数"})
        except (ValueError, TypeError):
            return make_response({"code": 400, "msg": "数量必须为有效的整数"})

        try:
            # ✅ 1. 检查用户是否存在
            user = User.query.get(user_id)
            if not user:
                return make_response({"code": 404, "msg": "用户不存在，请重新登录"})

            # ✅ 2. 查询商品单价
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "商品不存在"})
            price = product.price

            # ✅ 3. 查询购物车中是否已有该商品
            cart_item = ShoppingCart.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()

            if cart_item:
                cart_item.quantity += quantity
                cart_item.price = price  # 更新价格，防止商品价格变化
            else:
                cart_item = ShoppingCart(
                    user_id=user_id,
                    product_id=product_id,
                    quantity=quantity,
                    price=price
                )
                db.session.add(cart_item)

            db.session.commit()

            return make_response({
                "code": 200,
                "msg": "商品已成功添加到购物车",
                "data": {
                    "user_id": cart_item.user_id,
                    "product_id": cart_item.product_id,
                    "quantity": cart_item.quantity,
                    "price": cart_item.price,
                    "updated_at": str(cart_item.updated_at)
                }
            })

        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"操作失败：{str(e)}"})


# GET /api/cart/<user_id> 查询用户购物车
@ns.route('/<string:user_id>')
class GetCart(Resource):
    def get(self, user_id):
        """根据用户ID查询购物车列表，并计算总价"""
        if not user_id:
            return make_response({"code": 400, "msg": "user_id 不能为空"})

        try:
            cart_items = ShoppingCart.query.filter_by(user_id=user_id).all()

            cart_list = []
            total_price = 0

            for item in cart_items:
                product = Product.query.get(item.product_id)
                if not product:
                    continue

                subtotal = item.price * item.quantity
                total_price += subtotal

                # 获取图片URL，如果没有图片就用默认图片
                image_path = None
                if product.images and product.images[0].image_path:
                    image_path = product.images[0].image_path
                elif product.cover_image:
                    image_path = product.cover_image
                else:
                    image_path = "null"  # 可改为你自己的默认图片

                cart_list.append({
                    "product_id": item.product_id,
                    "name": product.name,
                    "sku": product.sku,
                    "image": BASE_URL + image_path,
                    "quantity": item.quantity,
                    "price": item.price,
                    "subtotal": subtotal,
                    "stock_quantity": product.stock_quantity
                })

            return make_response({
                "code": 200,
                "msg": "查询成功",
                "data": {
                    "user_id": user_id,
                    "cart_items": cart_list,
                    "total_items": len(cart_list),
                    "total_price": total_price
                }
            })

        except Exception as e:
            return make_response({
                "code": 500,
                "msg": "查询失败",
                "data": {"error": str(e)}
            })


# ================== 删除购物车单个商品 ==================
delete_cart_item_model = ns.model('DeleteCartItem', {
    'user_id': fields.String(required=True, description='用户ID'),
    'product_id': fields.String(required=True, description='商品ID')
})

# ================== 删除购物车单个商品（通过 URL path 传参） ==================
@ns.route('/delete-item/<string:user_id>/<string:product_id>')
class DeleteCartItem(Resource):
    def delete(self, user_id, product_id):
        """删除购物车单个商品"""
        if not user_id or not product_id:
            return make_response({
                "code": 400,
                "msg": "user_id 和 product_id 为必填项",
                "data": {}
            })

        try:
            cart_item = ShoppingCart.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()

            if not cart_item:
                return make_response({
                    "code": 404,
                    "msg": "购物车中未找到该商品",
                    "data": {}
                })

            db.session.delete(cart_item)
            db.session.commit()

            return make_response({
                "code": 200,
                "msg": "商品已从购物车删除",
                "data": {"user_id": user_id, "product_id": product_id}
            })

        except Exception as e:
            db.session.rollback()
            return make_response({
                "code": 500,
                "msg": "删除失败",
                "data": {"error": str(e)}
            })



# ================== 删除购物车多个商品 ==================
delete_cart_items_model = ns.model('DeleteCartItems', {
    'user_id': fields.String(required=True, description='用户ID'),
    'product_ids': fields.List(fields.String, required=True, description='要删除的商品ID列表')
})

@ns.route('/delete-items')
class DeleteCartItems(Resource):
    @ns.expect(delete_cart_items_model)
    def delete(self):
        """删除购物车多个商品"""
        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求体不能为空，需为JSON格式"})

        user_id = data.get('user_id')
        product_ids = data.get('product_ids', [])

        if not user_id or not product_ids:
            return make_response({"code": 400, "msg": "user_id 和 product_ids 为必填项"})

        try:
            cart_items = ShoppingCart.query.filter(
                ShoppingCart.user_id == user_id,
                ShoppingCart.product_id.in_(product_ids)
            ).all()

            if not cart_items:
                return make_response({"code": 404, "msg": "购物车中未找到指定商品"})

            for item in cart_items:
                db.session.delete(item)

            db.session.commit()
            return make_response({"code": 200, "msg": f"{len(cart_items)} 个商品已从购物车删除"})

        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"删除失败：{str(e)}"})

# ================== 计算实际付款金额（不使用优惠券） ==================
calculate_payment_model = ns.model('CalculatePayment', {
    'total_price': fields.Float(required=True, description='购物车总价（不使用优惠券）')
})

@ns.route('/calculate-payment')
class CalculatePayment(Resource):
    @ns.expect(calculate_payment_model)
    def post(self):
        """计算实际付款金额（不使用优惠券）"""
        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求体不能为空"})

        try:
            total_price = float(data.get('total_price', 0))
            discount = 0  # 不使用优惠券，折扣为0

            # 运费计算
            delivery = 0 if total_price >= 500 else 100

            grand_total = total_price + delivery - discount

            return make_response({
                "code": 200,
                "msg": "计算成功",
                "data": {
                    "total_price": total_price,
                    "discount": discount,
                    "delivery": delivery,
                    "grand_total": grand_total
                }
            })

        except (ValueError, TypeError):
            return make_response({"code": 400, "msg": "total_price 必须为有效数字"})
        except Exception as e:
            return make_response({"code": 500, "msg": f"计算失败：{str(e)}"})

# ================== 编辑购物车商品数量 ==================
edit_cart_item_model = ns.model('EditCartItem', {
    'user_id': fields.String(required=True, description='用户ID'),
    'product_id': fields.String(required=True, description='商品ID'),
    'quantity': fields.Integer(required=True, description='修改后的数量，必须为正整数')
})

@ns.route('/edit-item')
class EditCartItem(Resource):
    @ns.expect(edit_cart_item_model)
    def patch(self):
        """编辑购物车商品数量"""
        data = ns.payload
        if not data:
            return make_response({
                "code": 400,
                "msg": "请求体不能为空，需为JSON格式",
                "data": {}
            })

        user_id = data.get('user_id')
        product_id = data.get('product_id')
        quantity = data.get('quantity')

        if not user_id or not product_id or quantity is None:
            return make_response({
                "code": 400,
                "msg": "user_id、product_id 和 quantity 都为必填项",
                "data": {}
            })

        try:
            quantity = int(quantity)
            if quantity <= 0:
                return make_response({
                    "code": 400,
                    "msg": "数量必须为正整数",
                    "data": {}
                })
        except (ValueError, TypeError):
            return make_response({
                "code": 400,
                "msg": "数量必须为有效整数",
                "data": {}
            })

        try:
            cart_item = ShoppingCart.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()

            if not cart_item:
                return make_response({
                    "code": 404,
                    "msg": "购物车中未找到该商品",
                    "data": {}
                })

            cart_item.quantity = quantity
            db.session.commit()

            return make_response({
                "code": 200,
                "msg": "购物车商品数量已更新",
                "data": {
                    "user_id": user_id,
                    "product_id": product_id,
                    "quantity": cart_item.quantity
                }
            })

        except Exception as e:
            db.session.rollback()
            return make_response({
                "code": 500,
                "msg": f"更新失败：{str(e)}",
                "data": {}
            })
