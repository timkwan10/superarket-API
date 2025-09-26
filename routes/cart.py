from flask import Blueprint, jsonify, request
from models.cart import ShoppingCart
from extensions import db

cart_bp = Blueprint("cart", __name__)


@cart_bp.route('/api/add-to-cart', methods=['POST'])
def add_to_cart():
    # 1. 从请求体获取JSON数据
    data = request.get_json()
    if not data:  # 处理空请求体
        return jsonify({"error": "请求体不能为空，需为JSON格式"}), 400

    # 2. 提取参数（并设置默认值）
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)  # 默认为1

    # 3. 参数校验
    if not user_id or not product_id:
        return jsonify({"error": "user_id 和 product_id 为必填项"}), 400

    # 校验quantity是否为正整数
    try:
        quantity = int(quantity)  # 尝试转为整数（防止传入字符串）
        if quantity <= 0:
            return jsonify({"error": "数量必须为正整数"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "数量必须为有效的整数"}), 400

    try:
        # 4. 检查购物车中是否已有该商品
        cart_item = ShoppingCart.query.filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()

        if cart_item:
            # 已存在则更新数量
            cart_item.quantity += quantity
        else:
            # 不存在则创建新记录
            cart_item = ShoppingCart(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart_item)

        # 5. 提交事务
        db.session.commit()

        # 6. 返回成功响应
        return jsonify({
            "message": "商品已成功添加到购物车",
            "data": {
                "user_id": cart_item.user_id,
                "product_id": cart_item.product_id,
                "quantity": cart_item.quantity,
                "updated_at": cart_item.updated_at  # 可选：返回更新时间
            }
        }), 200

    except Exception as e:
        # 出错时回滚事务，避免数据不一致
        db.session.rollback()
        return jsonify({"error": f"操作失败：{str(e)}"}), 500

@cart_bp.route('/api/cart/<string:user_id>', methods=['GET'])
def get_cart_by_user(user_id):
    """
    根据用户ID查询购物车列表
    返回格式：包含商品ID和对应数量的列表
    """
    # 1. 参数校验（确保user_id不为空）
    if not user_id:
        return jsonify({"error": "user_id 不能为空"}), 400

    try:
        # 2. 查询该用户的所有购物车项
        # 只查询需要的字段（product_id和quantity），优化性能
        cart_items = ShoppingCart.query.filter_by(user_id=user_id).with_entities(
            ShoppingCart.product_id,
            ShoppingCart.quantity
        ).all()

        # 3. 格式化返回数据（转换为字典列表）
        cart_list = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity
            }
            for item in cart_items
        ]

        # 4. 返回结果（包含总数量便于前端展示）
        return jsonify({
            "message": "查询成功",
            "data": {
                "user_id": user_id,
                "cart_items": cart_list,
                "total_items": len(cart_list)  # 购物车商品种类总数
            }
        }), 200

    except Exception as e:
        # 处理数据库查询异常
        return jsonify({"error": f"查询失败：{str(e)}"}), 500
