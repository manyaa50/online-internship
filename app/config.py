import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base Configuration Class for Smart Internship System"""
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes')
    DEBUG = FLASK_DEBUG

    # SECRET_KEY has no hardcoded fallback; must be provided in environment or .env
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Database Configuration (XAMPP / WAMP MySQL default: root user, no password, localhost:3306)
    # Can also fallback to sqlite:///smart_internship.db if MySQL server is not active
    MYSQL_USER = os.getenv('DB_USER', 'root')
    MYSQL_PASSWORD = os.getenv('DB_PASSWORD', '')
    MYSQL_HOST = os.getenv('DB_HOST', 'localhost')
    MYSQL_PORT = os.getenv('DB_PORT', '3306')
    MYSQL_NAME = os.getenv('DB_NAME', 'smart_internship_db')
    
    # Default to MySQL with PyMySQL connector
    DEFAULT_MYSQL_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_NAME}?charset=utf8mb4"
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', DEFAULT_MYSQL_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    }

    # Uploads Configuration
    # Profile pictures and logos remain public in app/static/uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    # Private resume storage outside app/static
    RESUME_FOLDER = os.path.join(BASE_DIR, 'instance', 'uploads', 'resumes')
    # Private company verification document storage outside app/static
    DOCS_FOLDER = os.path.join(BASE_DIR, 'instance', 'uploads', 'company_docs')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB max upload
    ALLOWED_RESUME_EXTENSIONS = {'pdf', 'docx'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    ALLOWED_DOCS_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PER_PAGE = 8  # Pagination items count

    # Rate Limiting configuration
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'true').lower() in ('true', '1', 'yes')
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'

    # Portal Support & Company Contact Details (Configurable via environment)
    COMPANY_CONTACT_EMAIL = os.getenv('COMPANY_CONTACT_EMAIL', 'contact@smartintern-placeholder.example.com')
    COMPANY_CONTACT_PHONE = os.getenv('COMPANY_CONTACT_PHONE', '+91 (000) 000-0000 / +91 98765-00000')
    COMPANY_CONTACT_ADDRESS = os.getenv('COMPANY_CONTACT_ADDRESS', 'Plot No. 000, Innovation Tech Park, 4th Floor, Suite 404, Outer Ring Road, Bengaluru, Karnataka 560103, India')
