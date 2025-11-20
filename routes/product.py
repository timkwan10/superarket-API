import os
import uuid
from flask import request, Response, current_app
from flask_restx import Namespace, Resource
from extensions import db
from models.product import Product, ProductImage
from datetime import timezone, timedelta
import json
from datetime import datetime
import random
import string

ns = Namespace('product', description='Product management operations')

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
BASE_URL = "http://47.113.100.224:8000"  # 服务器地址
MEASURE_UNITS = ["个", "盒", "箱", "斤", "瓶"]
STATUS_OPTIONS = ["上架", "下架"]
BRAND_OPTIONS = ["品牌A", "品牌B", "品牌C", "品牌D"]

# ================== 工具函数 ==================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def make_response(data):
    """统一返回 JSON，中文不转义，HTTP 状态码固定 200"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        mimetype='application/json',
        status=200
    )

def to_full_url(path):
    """拼接完整 URL，并替换 Windows 的反斜杠为 /"""
    if not path:
        return None
    normalized_path = path.replace("\\", "/")
    return f"{BASE_URL}/{normalized_path}"

def auto_inventory_status(stock_quantity, low_stock_alert=5):
    """根据库存数量自动生成库存状态"""
    if stock_quantity == 0:
        return 'out_of_stock'
    elif stock_quantity <= low_stock_alert:
        return 'low_stock'
    else:
        return 'in_stock'

# ================== 产品选项接口 ==================
@ns.route('/options')
class ProductOptions(Resource):
    """返回可选的计量单位、状态和品牌"""
    def get(self):
        try:
            options = {
                "sku": MEASURE_UNITS,
                "status": STATUS_OPTIONS,
                "brand": BRAND_OPTIONS
            }
            return make_response({
                "code": 200,
                "msg": "获取成功",
                "data": options
            })
        except Exception as e:
            return make_response({
                "code": 500,
                "msg": f"获取选项失败：{str(e)}",
                "data": {}
            })

# ================== 添加产品请求参数 ==================
add_product_parser = ns.parser()
add_product_parser.add_argument('user_id', type=str, required=True, location='form', help="所属用户ID")
add_product_parser.add_argument('name', type=str, required=True, location='form', help="产品名称")
add_product_parser.add_argument('category', type=str, required=True, location='form', help="产品分类")
add_product_parser.add_argument('brand', type=str, location='form')
add_product_parser.add_argument('status', type=str, location='form')
add_product_parser.add_argument('price', type=float, location='form')
add_product_parser.add_argument('discount_price', type=float, location='form')
add_product_parser.add_argument('stock_quantity', type=int, location='form')
add_product_parser.add_argument('low_stock_alert', type=int, location='form')
add_product_parser.add_argument('sku', type=str, required=True, location='form', help="计量单位")
add_product_parser.add_argument('short_description', type=str, location='form')
add_product_parser.add_argument('full_description', type=str, location='form')
add_product_parser.add_argument('cover', type='FileStorage', location='files', required=False, help="封面图片")

# ================== 上传产品详情图片 ==================
upload_image_parser = ns.parser()
upload_image_parser.add_argument(
    'images',
    type='FileStorage',
    location='files',
    required=True,
    help="选择要上传的图片文件（产品详情图）"
)

# ================== 产品列表 & 添加产品 ==================
@ns.route('/')
class ProductList(Resource):
    @ns.doc('get_products')
    @ns.param('category', '产品分类', enum=['all', 'fresh_produce', 'pantry', 'frozen'], default='all')
    @ns.param('page', '页码（从 1 开始）', default=1)
    @ns.param('page_size', '每页条数', default=10)
    @ns.param('keyword', '产品名称关键字（可选，支持模糊搜索）')
    def get(self):
        """获取产品列表（支持分类、分页和模糊搜索）"""
        try:
            category = request.args.get('category', 'all').lower()
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))
            keyword = request.args.get('keyword', '').strip()  # 新增模糊搜索字段

            query = Product.query
            if category != 'all':
                query = query.filter(Product.category.ilike(category))

            if keyword:
                query = query.filter(Product.name.ilike(f"%{keyword}%"))

            pagination = query.paginate(page=page, per_page=page_size, error_out=False)
            products = pagination.items

            result = []
            for p in products:
                cover_url = to_full_url(p.cover_image) if p.cover_image else None
                result.append({
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "price": p.price,
                    "image": cover_url,
                    "sku": p.sku,
                    "inventory_status": p.inventory_status
                })

            return make_response({
                "code": 200,
                "msg": "获取成功",
                "data": {
                    "products": result,
                    "pagination": {
                        "page": pagination.page,
                        "page_size": pagination.per_page,
                        "total": pagination.total,
                        "pages": pagination.pages
                    }
                }
            })
        except Exception as e:
            return make_response({"code": 500, "msg": f"获取产品列表失败：{str(e)}", "data": {}})

    @ns.doc('add_product')
    @ns.expect(add_product_parser)
    def post(self):
        """添加新产品（可上传封面图片） form-data"""
        try:
            name = request.form.get('name')
            category = request.form.get('category')
            brand = request.form.get('brand')
            status = request.form.get('status')
            price = request.form.get('price', type=float)
            discount_price = request.form.get('discount_price', type=float)
            stock_quantity = request.form.get('stock_quantity', type=int, default=0)
            low_stock_alert = request.form.get('low_stock_alert', type=int, default=5)
            sku = request.form.get('sku')
            short_description = request.form.get('short_description')
            full_description = request.form.get('full_description')
            user_id = request.form.get('user_id')

            if not name or price is None or not sku or not user_id:
                return make_response({"code": 401, "msg": "名称、价格、计量单位和用户ID为必填", "data": {}})

            from models.user import User
            user = User.query.get(user_id)
            if not user:
                return make_response({"code": 404, "msg": "用户不存在", "data": {}})

            inventory_status = auto_inventory_status(stock_quantity, low_stock_alert)

            product = Product(
                name=name,
                category=category,
                brand=brand,
                sku=sku,
                status=status,
                price=price,
                discount_price=discount_price,
                stock_quantity=stock_quantity,
                low_stock_alert=low_stock_alert,
                inventory_status=inventory_status,
                short_description=short_description,
                full_description=full_description,
                user_id=user_id
            )

            # 处理封面图片
            cover = request.files.get('cover')
            if cover and allowed_file(cover.filename):
                save_dir = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(save_dir, exist_ok=True)
                filename = f"{uuid.uuid4().hex}_{cover.filename}"
                file_path = os.path.join(save_dir, filename)
                cover.save(file_path)
                rel_path = f"static/uploads/{filename}"
                product.cover_image = rel_path
                new_image = ProductImage(product_id=product.id, image_path=rel_path)
                db.session.add(new_image)

            db.session.add(product)
            db.session.commit()

            # ===== 转换 created_at 为北京时间 =====
            created_at_local = product.created_at + timedelta(hours=8)

            return make_response({
                "code": 200,
                "msg": "产品添加成功",
                "data": {
                    "id": product.id,
                    "sku": sku,
                    "user_id": user_id,
                    "created_at": created_at_local.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"添加产品失败：{str(e)}", "data": {}})

# ================== 单独上传产品图片 ==================
# ================== 多图上传参数 ==================
upload_images_parser = ns.parser()
upload_images_parser.add_argument(
    'images',
    type='FileStorage',
    location='files',  # 一定要是 files
    required=True,
    help='选择要上传的产品图片',
    action='append'   # 支持多文件
)


@ns.route('/<string:product_id>/upload_images')
class ProductImagesUpload(Resource):
    @ns.expect(upload_images_parser)
    def post(self, product_id):
        """单独上传多张产品图片"""
        try:
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "产品不存在"})

            # 获取上传的多张图片
            images = request.files.getlist('images')
            if not images:
                return make_response({"code": 400, "msg": "未选择图片"})

            saved_data = []
            save_dir = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(save_dir, exist_ok=True)

            for image in images:
                if image and allowed_file(image.filename):
                    filename = f"{uuid.uuid4().hex}_{image.filename}"
                    file_path = os.path.join(save_dir, filename)
                    image.save(file_path)

                    rel_path = f"static/uploads/{filename}"
                    new_image = ProductImage(product_id=product.id, image_path=rel_path)
                    db.session.add(new_image)
                    db.session.flush()  # 立即刷新，让 new_image.id 被生成
                    saved_data.append({
                        "image_id": new_image.id,
                        "url": f"{request.host_url}{rel_path}"
                    })

            db.session.commit()

            return make_response({
                "code": 200,
                "msg": "图片上传成功",
                "data": saved_data
            })

        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"图片上传失败：{str(e)}"})


cover_parser = ns.parser()
cover_parser.add_argument(
    'cover',
    type='FileStorage',
    location='files',
    required=True,
    help='选择封面图片'
)

@ns.route('/<string:product_id>/cover')
class ProductCover(Resource):
    @ns.expect(cover_parser)
    def post(self, product_id):
        """上传或更新封面图片"""
        try:
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "产品不存在"})

            cover = request.files.get('cover')
            if not cover or not allowed_file(cover.filename):
                return make_response({"code": 400, "msg": "未选择封面图片或文件类型不允许"})

            save_dir = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(save_dir, exist_ok=True)
            filename = f"{uuid.uuid4().hex}_{cover.filename}"
            file_path = os.path.join(save_dir, filename)
            cover.save(file_path)
            rel_path = f"static/uploads/{filename}"

            # 更新 product 表封面
            product.cover_image = rel_path
            # 添加到 ProductImage 表
            new_image = ProductImage(product_id=product.id, image_path=rel_path)
            db.session.add(new_image)
            db.session.commit()

            return make_response({
                "code": 200,
                "msg": "封面上传成功",
                "data": {"image_id": new_image.id, "cover_url": f"{request.host_url}{rel_path}"}
            })
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"封面上传失败：{str(e)}"})


# ================== 删除单张图片 ==================
@ns.route('/<string:product_id>/images/<string:image_id>/delete')
class ProductImageDelete(Resource):
    def delete(self, product_id, image_id):
        """删除单张产品图片"""
        try:
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "产品不存在"})

            image = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
            if not image:
                return make_response({"code": 404, "msg": "图片不存在"})

            # 删除服务器上的文件
            file_path = os.path.join(current_app.root_path, image.image_path)
            if os.path.exists(file_path):
                os.remove(file_path)

            db.session.delete(image)
            db.session.commit()

            return make_response({"code": 200, "msg": "图片删除成功"})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"图片删除失败：{str(e)}"})



# ================== 产品详情 ==================
@ns.route('/<string:product_id>')
class ProductDetail(Resource):
    def get(self, product_id):
        """获取产品详情"""
        try:
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "产品未找到", "data": {}})

            # 过滤掉封面图，只保留详情图
            detail_images = [
                {
                    "id": img.id,
                    "url": to_full_url(img.image_path),
                    "name": f"image{i + 1}"
                }
                for i, img in enumerate(product.images)
                if img.image_path != product.cover_image
            ]

            return make_response({
                "code": 200,
                "msg": "获取成功",
                "data": {
                    "user_id": product.user_id,
                    "id": product.id,
                    "name": product.name,
                    "category": product.category,
                    "brand": product.brand,
                    "sku": product.sku,
                    "status": product.status,
                    "price": product.price,
                    "discount_price": product.discount_price,
                    "stock_quantity": product.stock_quantity,
                    "low_stock_alert": product.low_stock_alert,
                    "inventory_status": product.inventory_status,
                    "short_description": product.short_description,
                    "full_description": product.full_description,
                    "cover_image": to_full_url(product.cover_image),
                    "images": detail_images,
                    "created_at": product.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        except Exception as e:
            return make_response({"code": 500, "msg": f"获取产品详情失败：{str(e)}", "data": {}})

# ================== 编辑产品 ==================
@ns.route('/<string:product_id>/edit')
class ProductEdit(Resource):
    @ns.expect(add_product_parser)
    def put(self, product_id):
        """编辑产品信息（不修改图片） form-data"""
        try:
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "产品不存在"})

            data = request.form
            for field in ['name', 'category', 'brand', 'status', 'price', 'discount_price',
                          'stock_quantity', 'low_stock_alert', 'short_description', 'full_description']:
                if field in data:
                    value = data.get(field)
                    if field in ['price', 'discount_price']:
                        value = float(value) if value else None
                    elif field in ['stock_quantity', 'low_stock_alert']:
                        value = int(value) if value else None
                    setattr(product, field, value)

            # 编辑时自动更新库存状态
            product.inventory_status = auto_inventory_status(product.stock_quantity, product.low_stock_alert)

            db.session.commit()
            return make_response({"code": 200, "msg": "产品信息更新成功"})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"产品更新失败：{str(e)}"})

# ================== 删除产品 ==================
@ns.route('/<string:product_id>/delete')
class ProductDelete(Resource):
    def delete(self, product_id):
        """删除产品（包括图片）"""
        try:
            product = Product.query.get(product_id)
            if not product:
                return make_response({"code": 404, "msg": "产品不存在"})

            # 删除关联图片文件
            for img in product.images:
                file_path = os.path.join(current_app.root_path, img.image_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                db.session.delete(img)

            db.session.delete(product)
            db.session.commit()
            return make_response({"code": 200, "msg": "产品删除成功"})
        except Exception as e:
            db.session.rollback()
            return make_response({"code": 500, "msg": f"产品删除失败：{str(e)}"})
