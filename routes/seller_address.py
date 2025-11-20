from flask_restx import Namespace, Resource, fields
from extensions import db
from flask import request, Response
from models.seller_address import SellerAddress  # ✅ 新建 SellerAddress 模型
import json

ns = Namespace('seller_address', description='商家发货地址操作')

# 🔹 发货地址模型（Swagger 文档）
seller_address_model = ns.model('SellerAddress', {
    'contact_name': fields.String(required=True, description='联系人姓名'),
    'contact_phone': fields.String(required=True, description='联系电话'),
    'street_address': fields.String(required=True, description='街道地址'),
    'apartment': fields.String(description='楼栋/房号'),
    'city': fields.String(required=True, description='城市'),
    'state': fields.String(required=True, description='省/州'),
    'postal_code': fields.String(required=True, description='邮政编码'),
    'country': fields.String(required=True, description='国家'),
    'is_default': fields.Boolean(description='是否为默认发货地址', default=False)
})


def make_response(data):
    """统一返回 JSON 格式"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )


# 🧩 获取/添加 商家发货地址
@ns.route('/<string:seller_id>')
class SellerAddressList(Resource):
    def get(self, seller_id):
        """获取商家所有发货地址"""
        try:
            addresses = SellerAddress.query.filter_by(seller_id=seller_id).all()
            result = []
            for addr in addresses:
                result.append({
                    "id": addr.id,
                    "contact_name": addr.contact_name,
                    "contact_phone": addr.contact_phone,
                    "street_address": addr.street_address,
                    "apartment": addr.apartment,
                    "city": addr.city,
                    "state": addr.state,
                    "postal_code": addr.postal_code,
                    "country": addr.country,
                    "is_default": addr.is_default,
                })
            return make_response({"code": 200, "msg": "获取发货地址成功", "data": result})
        except Exception as e:
            return make_response({"code": 500, "msg": f"获取发货地址失败：{str(e)}", "data": None})

    @ns.expect(seller_address_model)
    def post(self, seller_id):
        """商家添加发货地址"""
        data = request.get_json() or {}
        if not data:
            return make_response({"code": 400, "msg": "请求参数为空", "data": None})

        try:
            # ✅ 验证商家是否存在
            # seller = Seller.query.get(seller_id)
            # if not seller:
            #     return make_response({"code": 404, "msg": "商家不存在", "data": None})

            # 若设置为默认地址，则取消原有默认地址
            if data.get("is_default", False):
                SellerAddress.query.filter_by(seller_id=seller_id, is_default=True).update({"is_default": False})

            new_addr = SellerAddress(
                seller_id=seller_id,
                contact_name=data["contact_name"],
                contact_phone=data["contact_phone"],
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
                "msg": "发货地址添加成功",
                "data": {"id": new_addr.id}
            })
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"添加发货地址失败：{str(e)}", "data": None})


# 🧩 修改 / 删除 商家发货地址
@ns.route('/<string:seller_id>/<int:address_id>')
class SellerAddressDetail(Resource):
    @ns.expect(seller_address_model)
    def put(self, seller_id, address_id):
        """商家修改发货地址"""
        data = request.get_json() or {}
        if not data:
            return make_response({"code": 400, "msg": "请求参数为空", "data": None})

        addr = SellerAddress.query.filter_by(seller_id=seller_id, id=address_id).first()
        if not addr:
            return make_response({"code": 404, "msg": "发货地址不存在", "data": None})

        try:
            # 若设置为默认地址，则取消原有默认地址
            if data.get("is_default", False):
                SellerAddress.query.filter_by(seller_id=seller_id, is_default=True).update({"is_default": False})

            # 更新字段
            addr.contact_name = data.get("contact_name", addr.contact_name)
            addr.contact_phone = data.get("contact_phone", addr.contact_phone)
            addr.street_address = data.get("street_address", addr.street_address)
            addr.apartment = data.get("apartment", addr.apartment)
            addr.city = data.get("city", addr.city)
            addr.state = data.get("state", addr.state)
            addr.postal_code = data.get("postal_code", addr.postal_code)
            addr.country = data.get("country", addr.country)
            addr.is_default = data.get("is_default", addr.is_default)

            db.session.commit()
            return make_response({"code": 200, "msg": "发货地址更新成功", "data": {"id": addr.id}})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"更新发货地址失败：{str(e)}", "data": None})

    def delete(self, seller_id, address_id):
        """删除商家发货地址"""
        addr = SellerAddress.query.filter_by(seller_id=seller_id, id=address_id).first()
        if not addr:
            return make_response({"code": 404, "msg": "发货地址不存在", "data": None})

        try:
            db.session.delete(addr)
            db.session.commit()
            return make_response({"code": 200, "msg": "发货地址删除成功", "data": {"id": address_id}})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"删除发货地址失败：{str(e)}", "data": None})


# 🧩 获取单个商家发货地址详情（用户可用）
@ns.route('/<string:seller_id>/<int:address_id>/detail')
class SellerAddressInfo(Resource):
    def get(self, seller_id, address_id):
        """获取单个商家发货地址详情"""
        try:
            addr = SellerAddress.query.filter_by(seller_id=seller_id, id=address_id).first()
            if not addr:
                return make_response({"code": 404, "msg": "发货地址不存在", "data": None})

            data = {
                "id": addr.id,
                "contact_name": addr.contact_name,
                "contact_phone": addr.contact_phone,
                "street_address": addr.street_address,
                "apartment": addr.apartment,
                "city": addr.city,
                "state": addr.state,
                "postal_code": addr.postal_code,
                "country": addr.country,
                "is_default": addr.is_default,
            }
            return make_response({"code": 200, "msg": "获取发货地址详情成功", "data": data})
        except Exception as e:
            return make_response({"code": 500, "msg": f"获取发货地址详情失败：{str(e)}", "data": None})
