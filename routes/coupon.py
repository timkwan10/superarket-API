from flask_restx import Namespace, Resource, fields
from extensions import db
from models.coupon import Coupon, UserCoupon
from flask import Response
import json, os
from datetime import datetime, timedelta
from flask import request
from werkzeug.utils import secure_filename
from flask_restx import reqparse
from werkzeug.datastructures import FileStorage
from flask import send_file
import io
from datetime import timezone, timedelta

ns = Namespace('coupon', description='Coupon operations')
BASE_URL = "http://47.113.100.224:8000"


add_coupon_parser = reqparse.RequestParser()
add_coupon_parser.add_argument('name', type=str, required=True, help='优惠券名称', location='form')
add_coupon_parser.add_argument('discount_amount', type=float, required=False, default=0, location='form')
add_coupon_parser.add_argument('discount_percent', type=float, required=False, default=0, location='form')
add_coupon_parser.add_argument('min_order_amount', type=float, required=False, default=0, location='form')
add_coupon_parser.add_argument('valid_days', type=int, required=False, default=30, location='form')
add_coupon_parser.add_argument('image', type=FileStorage, location='files', required=False, help='优惠券图片')


# ✅ 统一返回格式函数
def make_response(code, msg, data=None):
    return Response(
        json.dumps({"code": code, "msg": msg, "data": data or {}}, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )


# ================== Swagger 模型 ==================
add_coupon_model = ns.model('AddCoupon', {
    'name': fields.String(required=True, description='优惠券名称'),
    'discount_amount': fields.Float(description='折扣金额', default=0),
    'discount_percent': fields.Float(description='折扣百分比', default=0),
    'min_order_amount': fields.Float(description='最低订单金额', default=0),
    'valid_days': fields.Integer(description='有效天数', default=30),
    'image': fields.Raw(required=False, description='优惠券图片文件')  # 文件上传
})

assign_coupon_model = ns.model('AssignCoupon', {
    'coupon_id': fields.String(required=True, description='优惠券ID'),
    'user_id': fields.String(required=True, description='用户ID')
})

use_coupon_model = ns.model('UseCoupon', {
    'user_id': fields.String(required=True, description='用户ID'),
    'coupon_id': fields.String(required=True, description='优惠券ID'),
    'order_amount': fields.Float(required=True, description='订单金额')
})


# ================== 添加优惠券 ==================
@ns.route('/add')
class AddCoupon(Resource):
    @ns.expect(add_coupon_parser)
    def post(self):
        args = add_coupon_parser.parse_args()
        try:
            image_file = args.get('image')
            image_data = None
            image_filename = None
            image_mime = None

            if image_file:
                image_data = image_file.read()
                image_filename = secure_filename(image_file.filename)
                image_mime = image_file.mimetype

            coupon = Coupon(
                name=args['name'],
                discount_amount=args.get('discount_amount', 0),
                discount_percent=args.get('discount_percent', 0),
                min_order_amount=args.get('min_order_amount', 0),
                valid_until=datetime.utcnow() + timedelta(days=args.get('valid_days', 30)),  # 存储 UTC
                image=image_data,
                image_filename=image_filename,
                image_mime=image_mime
            )
            db.session.add(coupon)
            db.session.commit()

            # 转为北京时间
            created_at_local = coupon.created_at + timedelta(hours=8)
            valid_until_local = coupon.valid_until + timedelta(hours=8)

            return make_response(200, "优惠券添加成功", {
                "coupon": {
                    **coupon.to_dict(base_url=BASE_URL),
                    "created_at": created_at_local.strftime("%Y-%m-%d %H:%M:%S"),
                    "valid_until": valid_until_local.strftime("%Y-%m-%d %H:%M:%S")
                }
            })

        except Exception as e:
            db.session.rollback()
            return make_response(500, "优惠券添加失败", {"error": str(e)})

# ================== 发放优惠券给用户 ==================
@ns.route('/assign')
class AssignCoupon(Resource):
    @ns.expect(assign_coupon_model)
    def post(self):
        """发放优惠券给用户"""
        data = ns.payload
        try:
            existing = UserCoupon.query.filter_by(
                user_id=data['user_id'],
                coupon_id=data['coupon_id']
            ).first()

            if existing:
                return make_response(400, "用户已拥有该优惠券")

            user_coupon = UserCoupon(
                user_id=data['user_id'],
                coupon_id=data['coupon_id'],
                status='available'
            )
            db.session.add(user_coupon)
            db.session.commit()

            return make_response(200, "优惠券已成功发放", {
                "user_id": user_coupon.user_id,
                "coupon_id": user_coupon.coupon_id,
                "status": user_coupon.status
            })

        except Exception as e:
            db.session.rollback()
            return make_response(500, "发放优惠券失败", {"error": str(e)})


# ================== 查询用户优惠券 ==================
@ns.route('/user/<string:user_id>')
class GetUserCoupons(Resource):
    def get(self, user_id):
        try:
            user_coupons = UserCoupon.query.filter_by(user_id=user_id).all()
            coupons_data = []
            for uc in user_coupons:
                coupon = Coupon.query.get(uc.coupon_id)
                coupon_dict = coupon.to_dict(base_url=BASE_URL)
                coupon_dict["status"] = uc.status
                # 转北京时间
                if coupon.created_at:
                    coupon_dict["created_at"] = (coupon.created_at + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                if coupon.valid_until:
                    coupon_dict["valid_until"] = (coupon.valid_until + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                coupons_data.append(coupon_dict)

            return make_response(200, "查询成功", {
                "user_id": user_id,
                "total": len(coupons_data),
                "coupons": coupons_data
            })
        except Exception as e:
            return make_response(500, "查询失败", {"error": str(e)})


# ================== 使用优惠券 ==================
@ns.route('/use')
class UseCoupon(Resource):
    @ns.expect(ns.model('UseCoupon', {
        'user_id': fields.String(required=True),
        'coupon_id': fields.String(required=True),
        'order_amount': fields.Float(required=True)
    }))
    def post(self):
        data = request.json
        try:
            # 查询可用优惠券
            user_coupon = UserCoupon.query.filter_by(
                user_id=data['user_id'],
                coupon_id=data['coupon_id'],
                status='available'
            ).first()

            if not user_coupon:
                return make_response(404, "优惠券不可用或不存在")

            coupon = Coupon.query.get(data['coupon_id'])
            order_amount = float(data['order_amount'])

            if order_amount < coupon.min_order_amount:
                return make_response(400, f"订单金额不足最低使用条件 {coupon.min_order_amount}")

            # 计算折扣，但不修改状态
            discount = order_amount * coupon.discount_percent if coupon.discount_percent > 0 else coupon.discount_amount
            final_amount = max(order_amount - discount, 0)
            delivery = 0 if order_amount >= 500 else 100
            grand_total = final_amount + delivery

            return make_response(200, "优惠券可用", {
                "original_amount": order_amount,
                "discount": discount,
                "delivery": delivery,
                "final_amount": final_amount,
                "grand_total": grand_total,
                "coupon_image": f"{BASE_URL}/coupon/image/{coupon.id}" if coupon.image else None
            })

        except Exception as e:
            return make_response(500, "优惠券使用失败", {"error": str(e)})


@ns.route('/image/<string:coupon_id>')
class CouponImage(Resource):
    def get(self, coupon_id):
        coupon = Coupon.query.get(coupon_id)
        if not coupon or not coupon.image:
            return make_response(404, "图片不存在")

        return send_file(
            io.BytesIO(coupon.image),
            mimetype=coupon.image_mime,
            as_attachment=False,
            download_name=coupon.image_filename
        )
