import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base Configuration Class for Smart Internship System"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'smart-internship-scam-prevention-secret-key-2026-bca')
    
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
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')
    DOCS_FOLDER = os.path.join(UPLOAD_FOLDER, 'company_docs')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB max upload
    ALLOWED_RESUME_EXTENSIONS = {'pdf', 'docx'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PER_PAGE = 8  # Pagination items count
