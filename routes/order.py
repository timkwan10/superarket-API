from flask import Blueprint, request, jsonify
from models.order import Order
from models.address import Address# 1. 模型类名首字母大写（符合Python类命名规范）
from extensions import db

order_bp = Blueprint("order", __name__)


@order_bp.route("/api/create-order", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空，需为JSON格式"}), 400

    # 1. 校验用户ID
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id 为必填项"}), 400

    # 2. 处理配送地址：用user_address作为变量名，避免与模型类Address冲突
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

    user_address = None  # 2. 变量名改为user_address，避免与模型类Address重名
    if address_id:
        # 3. 用大写的Address模型类调用query（核心修复）
        user_address = Address.query.filter_by(id=address_id, user_id=user_id).first()
        if not user_address:
            return jsonify({"error": "地址不存在或不属于该用户"}), 404
    else:
        # 校验新地址必填字段
        required_address_fields = ["recipient_name", "contact_number", "street_address", "city", "state", "postal_code",
                                   "country"]
        for field in required_address_fields:
            if not new_address_data[field]:
                return jsonify({"error": f"新地址的「{field}」为必填项"}), 400

        # 处理默认地址逻辑（用Address模型类）
        if new_address_data["is_default"]:
            Address.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})

        # 创建新地址（用Address模型类实例化）
        user_address = Address(user_id=user_id, **new_address_data)
        db.session.add(user_address)
        db.session.flush()  # 获取新地址的id

    # 3. 校验订单其他必填字段
    required_order_fields = ["delivery_slot", "payment_method", "item_total", "tax", "delivery_fee", "discount",
                             "grand_total"]
    for field in required_order_fields:
        # 第一步：先判断字段是否存在于data中
        if field not in data:
            return jsonify({"error": f"订单字段「{field}」为必填项"}), 400

        # 第二步：针对数字类型字段，单独判断“是否为有效数字”（避免0.0被误判）
        field_value = data[field]
        if field in ["item_total", "tax", "delivery_fee", "discount", "grand_total"]:
            # 检查是否为数字（int/float），且不是None/空字符串
            if not isinstance(field_value, (int, float)) or field_value is None:
                return jsonify({"error": f"订单字段「{field}」必须为有效数字"}), 400
        # 非数字字段（如delivery_slot、payment_method）仍用非空校验
        else:
            if not field_value:
                return jsonify({"error": f"订单字段「{field}」为必填项"}), 400

    # 4. 后续金额格式转换（可保留，双重保障）
    try:
        item_total = float(data["item_total"])
        tax = float(data["tax"])
        delivery_fee = float(data["delivery_fee"])  # 0.0 转float正常
        discount = float(data["discount"])
        grand_total = float(data["grand_total"])
    except (ValueError, TypeError):
        return jsonify({"error": "金额字段必须为有效数字"}), 400

    # 5. 校验支付方式合法性
    valid_payment_methods = ["Credit/Debit Card", "Apple Pay/Google Pay", "Alipay", "WeChat Pay"]
    if data["payment_method"] not in valid_payment_methods:
        return jsonify({"error": "支付方式不合法"}), 400

    # 6. 创建订单（用大写的Order模型类实例化，核心修复）
    new_order = Order(
        user_id=user_id,
        address_id=user_address.id,  # 使用修正后的变量名
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
            "created_at": new_order.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"创建订单失败：{str(e)}"}), 500


@order_bp.route("/api/addresses/<string:user_id>", methods=["GET"])
def get_user_addresses(user_id):
    if not user_id:
        return jsonify({"error": "user_id 不能为空"}), 400
    # 用大写的Address模型类查询（修复）
    addresses = Address.query.filter_by(user_id=user_id).all()
    result = []
    for addr in addresses:
        result.append({
            "id": addr.id,
            "recipient_name": addr.recipient_name,
            "contact_number": addr.contact_number,
            "street_address": addr.street_address,
            "city": addr.city,
            "state": addr.state,
            "postal_code": addr.postal_code,
            "is_default": addr.is_default,
            "created_at": addr.created_at.isoformat()
        })
    return jsonify({
        "message": "查询成功",
        "addresses": result,
        "total": len(result)
    }), 200

@order_bp.route("/api/orders/<string:user_id>", methods=["GET"])
def get_history_orders(user_id):
    """
    查询用户历史订单
    返回字段：订单编号、创建日期、订单总价
    """
    # 1. 校验用户ID
    if not user_id:
        return jsonify({"error": "user_id 为必填项"}), 400

    try:
        # 2. 查询该用户的所有订单（按创建时间倒序，最新的在前）
        orders = Order.query.filter_by(user_id=user_id)\
                            .order_by(Order.created_at.desc())\
                            .with_entities(
                                Order.order_id,
                                Order.created_at,
                                Order.grand_total
                            ).all()

        # 3. 格式化订单数据
        order_list = []
        for order in orders:
            order_list.append({
                "order_id": order.order_id,  # 订单编号
                "date": order.created_at.strftime("%Y-%m-%d %H:%M:%S"),  # 格式化日期
                "total_price": round(order.grand_total, 2)  # 保留两位小数
            })

        # 4. 返回结果
        return jsonify({
            "message": "查询成功",
            "user_id": user_id,
            "order_count": len(order_list),  # 订单总数
            "orders": order_list
        }), 200

    except Exception as e:
        return jsonify({"error": f"查询失败：{str(e)}"}), 500
