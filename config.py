# config.py
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/freshmart'
SQLALCHEMY_TRACK_MODIFICATIONS = False
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}