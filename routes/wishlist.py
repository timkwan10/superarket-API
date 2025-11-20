from flask_restx import Namespace, Resource, fields
from extensions import db
from models.wishlist import Wishlist
from models.product import Product
from models.user import User
from flask import request, Response
import json
from flask_restx import reqparse

ns = Namespace('wishlist', description='Wishlist operations')

# 请求体模型
add_to_wishlist_model = ns.model('AddToWishlist', {
    'user_id': fields.String(required=True, description='用户ID'),
    'product_id': fields.String(required=True, description='商品ID')
})

# 通用响应函数
def make_response(data):
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )

# ================== 添加商品到心愿单 ==================
@ns.route('/add')
class AddToWishlist(Resource):
    @ns.expect(add_to_wishlist_model)
    def post(self):
        """添加商品到心愿单"""
        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求体不能为空"})

        user_id = data.get('user_id')
        product_id = data.get('product_id')

        if not user_id or not product_id:
            return make_response({"code": 400, "msg": "user_id 和 product_id 为必填项"})

        try:
            # ✅ 检查用户是否存在
            user = User.query.get(user_id)
            if not user:
                return make_response({"code": 404, "msg": "用户不存在，请重新登录"})

            # ✅ 检查商品是否存在
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "商品不存在"})

            # ✅ 检查是否已在心愿单中
            existing_item = Wishlist.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()

            if existing_item:
                return make_response({"code": 200, "msg": "商品已在心愿单中"})

            # ✅ 添加新商品到心愿单
            new_item = Wishlist(user_id=user_id, product_id=product_id)
            db.session.add(new_item)
            db.session.commit()

            return make_response({
                "code": 200,
                "msg": "商品已成功添加到心愿单",
                "data": {
                    "user_id": new_item.user_id,
                    "product_id": new_item.product_id,
                    "added_at": str(new_item.added_at)
                }
            })

        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"添加失败：{str(e)}"})


# ================== 获取心愿单列表 ==================
# 分页参数解析器（Swagger 显示）
pagination_parser = reqparse.RequestParser()
pagination_parser.add_argument('page', type=int, default=1, required=False, help='页码（默认 1）')
pagination_parser.add_argument('page_size', type=int, default=10, required=False, help='每页数量（默认 10）')

@ns.route('/<string:user_id>')
class GetWishlist(Resource):
    @ns.doc(params={
        "user_id": "用户 ID"
    })
    @ns.expect(pagination_parser)
    def get(self, user_id):
        """根据用户ID获取心愿单商品列表（支持分页）"""
        try:
            # 获取分页参数
            try:
                page = int(request.args.get("page", 1))
                page_size = int(request.args.get("page_size", 10))
            except ValueError:
                return make_response({"code": 400, "msg": "分页参数必须为整数"})

            query = Wishlist.query.filter_by(user_id=user_id).order_by(Wishlist.added_at.desc())
            total_items = query.count()

            # 分页查询
            wishlist_items = query.offset((page - 1) * page_size).limit(page_size).all()

            data = []
            for item in wishlist_items:
                product = item.product

                data.append({
                    "product_id": item.product_id,
                    "product_name": product.name if product else None,
                    "price": product.price if product else None,

                    # 🔥 新增：返回一张产品封面图片 URL
                    "image_url": (
                        f"http://47.113.100.224:8000/{product.cover_image}"
                        if product and product.cover_image else None
                    ),

                    "added_at": item.added_at.isoformat()
                })

            return make_response({
                "code": 200,
                "msg": "查询成功",
                "data": {
                    "user_id": user_id,
                    "wishlist_items": data,
                    "total_items": total_items,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_items + page_size - 1) // page_size
                }
            })

        except Exception as e:
            return make_response({"code": 500, "msg": f"查询失败：{str(e)}"})


# ================== 删除心愿单商品 ==================
delete_wishlist_item_model = ns.model('DeleteWishlistItem', {
    'user_id': fields.String(required=True, description='用户ID'),
    'product_id': fields.String(required=True, description='商品ID')
})

@ns.route('/delete')
class DeleteWishlistItem(Resource):
    @ns.expect(delete_wishlist_item_model)
    def delete(self):
        """从心愿单中删除单个商品"""
        data = ns.payload
        if not data:
            return make_response({"code": 400, "msg": "请求体不能为空"})

        user_id = data.get('user_id')
        product_id = data.get('product_id')

        if not user_id or not product_id:
            return make_response({"code": 400, "msg": "user_id 和 product_id 为必填项"})

        try:
            item = Wishlist.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()

            # 如果心愿单商品不存在
            if not item:
                return make_response({
                    "code": 404,
                    "msg": "该商品不在心愿单中"
                })

            # 删除记录
            db.session.delete(item)
            db.session.commit()

            return make_response({
                "code": 200,
                "msg": "删除成功",
                "data": {
                    "user_id": user_id,
                    "product_id": product_id
                }
            })

        except Exception as e:
            db.session.rollback()
            return make_response({
                "code": 500,
                "msg": f"删除失败：{str(e)}"
            })
