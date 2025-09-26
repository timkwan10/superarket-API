import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models.product import Product, ProductImage
from PIL import Image

product_bp = Blueprint("product", __name__)

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@product_bp.route("/products", methods=["POST"])
def add_product():
    try:
        # 1. 获取表单字段
        name = request.form.get("name")
        category = request.form.get("category")
        brand = request.form.get("brand")
        sku = request.form.get("sku")
        status = request.form.get("status")
        price = request.form.get("price", type=float)
        discount_price = request.form.get("discount_price", type=float)
        stock_quantity = request.form.get("stock_quantity", type=int)
        low_stock_alert = request.form.get("low_stock_alert", type=int)
        inventory_status = request.form.get("inventory_status")
        short_description = request.form.get("short_description")
        full_description = request.form.get("full_description")

        if not name:
            return jsonify({"code": 1, "message": "Product name is required"}), 400

        new_product = Product(
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
        )

        db.session.add(new_product)
        db.session.flush()  # 提前生成 product.id

        # 2. 处理多图上传
        files = request.files.getlist("images")
        saved_paths = []
        if files:
            os.makedirs(os.path.join(current_app.root_path, UPLOAD_FOLDER), exist_ok=True)

            for file in files:
                if file and allowed_file(file.filename):
                    filename = f"{uuid.uuid4().hex}.jpg"
                    filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)

                    # 打开图片并压缩
                    img = Image.open(file)
                    img = img.convert("RGB")  # 确保是RGB
                    img.save(filepath, optimize=True, quality=70)  # 压缩质量 70%

                    rel_path = os.path.join(UPLOAD_FOLDER, filename)
                    saved_paths.append(rel_path)

                    db.session.add(ProductImage(product_id=new_product.id, image_path=rel_path))

        db.session.commit()

        return jsonify({
            "code": 0,
            "message": "Product added successfully",
            "data": {
                "id": new_product.id,
                "name": new_product.name,
                "images": saved_paths
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "message": str(e)}), 500

@product_bp.route("/products", methods=["GET"])
def get_products():
    products = Product.query.all()
    data = []
    for p in products:
        # 如果有图片，取第一张
        first_image = p.images[0].image_path if p.images else None
        data.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "image": first_image
        })
    return jsonify({
        "code": 0,
        "message": "Success",
        "data": data
    })

@product_bp.route("/products/<product_id>", methods=["GET"])
def get_product_detail(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"code": 1, "message": "Product not found"}), 404

    # 返回所有图片路径
    images = [img.image_path for img in product.images]

    return jsonify({
        "code": 0,
        "message": "Success",
        "data": {
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
            "images": images,
            "created_at": product.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    })