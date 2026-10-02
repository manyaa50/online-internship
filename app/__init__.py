import os
from flask import Flask, render_template
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from app.config import Config
from app.models import db, User, Internship, InternshipCategory, ScamReport, Company

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESUME_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOCS_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Global template context processor
    @app.context_processor
    def inject_global_data():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = current_user.unread_notifications_count()
        
        categories = []
        try:
            categories = InternshipCategory.query.order_by(InternshipCategory.name.asc()).all()
        except Exception:
            pass

        return {
            'unread_notifications_count': unread_count,
            'all_categories': categories,
            'app_name': 'SmartIntern'
        }

    # Register Blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.student.routes import student_bp
    from app.blueprints.company.routes import company_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.internships.routes import internships_bp
    from app.blueprints.reports.routes import reports_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(company_bp, url_prefix='/company')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(internships_bp, url_prefix='/internships')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    # Home Route
    @app.route('/')
    def index():
        featured_internships = []
        total_postings = 0
        total_companies = 0
        scam_prevented_count = 0
        categories = []
        try:
            # Only display active low/medium risk postings on public home
            featured_internships = (
                Internship.query
                .filter(Internship.status == 'active')
                .order_by(Internship.created_at.desc())
                .limit(6)
                .all()
            )
            total_postings = Internship.query.count()
            total_companies = Company.query.filter_by(verification_status='approved').count()
            scam_prevented_count = Internship.query.filter(Internship.status.in_(['flagged', 'rejected'])).count()
            categories = InternshipCategory.query.all()
        except Exception:
            pass

        return render_template(
            'home.html',
            featured_internships=featured_internships,
            total_postings=total_postings,
            total_companies=total_companies,
            scam_prevented_count=scam_prevented_count,
            categories=categories
        )

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('base.html', error_code=403, error_title="Access Forbidden",
                               error_msg="You do not have permission to access this resource."), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', error_code=404, error_title="Page Not Found",
                               error_msg="The page you requested does not exist or has been removed."), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('base.html', error_code=500, error_title="Server Error",
                               error_msg="An unexpected error occurred. Our engineers have been alerted."), 500

    return app
