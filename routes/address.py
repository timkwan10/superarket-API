from flask_restx import Namespace, Resource, fields
from extensions import db
from models.address import Address
from flask import request, Response
from models.user import User
import json

ns = Namespace('address', description='Address operations')

# 地址模型（用于 Swagger 文档和输入验证）
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

def make_response(data):
    """统一返回 JSON，中文不转义，HTTP 状态码固定 200"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )

# GET /addresses/<user_id> 获取用户所有地址
@ns.route('/<string:user_id>')
class AddressList(Resource):
    def get(self, user_id):
        """获取用户所有地址"""
        try:
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
            return make_response({"code": 200, "msg": "获取地址成功", "data": result})
        except Exception as e:
            return make_response({"code": 500, "msg": f"获取地址失败：{str(e)}", "data": None})

    @ns.expect(address_model)
    def post(self, user_id):
        """添加新地址"""
        data = request.get_json() or {}
        if not data:
            return make_response({"code": 400, "msg": "请求参数为空", "data": None})

        try:
            # ✅ 验证用户是否存在
            user = User.query.get(user_id)
            if not user:
                return make_response({"code": 404, "msg": "用户不存在", "data": None})

            # 若新地址设置为默认地址，则取消原有默认地址
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

            return make_response({
                "code": 200,
                "msg": "地址添加成功",
                "data": {"id": new_addr.id}
            })

        except Exception as e:
            db.session.rollback()
            return make_response({
                "code": 500,
                "msg": f"添加地址失败：{str(e)}",
                "data": None
            })


@ns.route('/<string:user_id>/<int:address_id>')
class AddressDetail(Resource):
    @ns.expect(address_model)
    def put(self, user_id, address_id):
        """编辑用户地址"""
        data = request.get_json() or {}
        if not data:
            return make_response({"code": 400, "msg": "请求参数为空", "data": None})

        addr = Address.query.filter_by(user_id=user_id, id=address_id).first()
        if not addr:
            return make_response({"code": 404, "msg": "地址不存在", "data": None})

        try:
            # 如果编辑为默认地址，先把原来的默认地址取消
            if data.get("is_default", False):
                Address.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})

            # 更新字段
            addr.recipient_name = data.get("recipient_name", addr.recipient_name)
            addr.contact_number = data.get("contact_number", addr.contact_number)
            addr.street_address = data.get("street_address", addr.street_address)
            addr.apartment = data.get("apartment", addr.apartment)
            addr.city = data.get("city", addr.city)
            addr.state = data.get("state", addr.state)
            addr.postal_code = data.get("postal_code", addr.postal_code)
            addr.country = data.get("country", addr.country)
            addr.is_default = data.get("is_default", addr.is_default)

            db.session.commit()
            return make_response({"code": 200, "msg": "地址更新成功", "data": {"id": addr.id}})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"更新地址失败：{str(e)}", "data": None})

    def delete(self, user_id, address_id):
        """删除用户地址"""
        addr = Address.query.filter_by(user_id=user_id, id=address_id).first()
        if not addr:
            return make_response({"code": 404, "msg": "地址不存在", "data": None})

        try:
            db.session.delete(addr)
            db.session.commit()
            return make_response({"code": 200, "msg": "地址删除成功", "data": {"id": address_id}})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"删除地址失败：{str(e)}", "data": None})

@ns.route('/<string:user_id>/<int:address_id>/detail')
class AddressInfo(Resource):
    def get(self, user_id, address_id):
        """获取单个地址详情"""
        try:
            addr = Address.query.filter_by(user_id=user_id, id=address_id).first()
            if not addr:
                return make_response({"code": 404, "msg": "地址不存在", "data": None})

            data = {
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
            }
            return make_response({"code": 200, "msg": "获取地址详情成功", "data": data})
        except Exception as e:
            return make_response({"code": 500, "msg": f"获取地址详情失败：{str(e)}", "data": None})
