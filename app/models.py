import json
from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('student', 'company', 'admin', name='user_roles'), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    admin_profile = db.relationship('Admin', backref='user', uselist=False, cascade='all, delete-orphan')
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    company_profile = db.relationship('Company', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan', lazy='dynamic', order_by='Notification.created_at.desc()')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_company(self):
        return self.role == 'company'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def display_name(self):
        if self.is_admin and self.admin_profile:
            return self.admin_profile.full_name
        if self.is_student and self.student_profile:
            return self.student_profile.full_name
        if self.is_company and self.company_profile:
            return self.company_profile.company_name
        return self.email.split('@')[0]

    def unread_notifications_count(self):
        return self.notifications.filter_by(is_read=False).count()

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    verifications = db.relationship('CompanyVerification', backref='reviewed_by_admin', lazy='dynamic')


class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    college_name = db.Column(db.String(200), nullable=True)
    degree = db.Column(db.String(100), nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    cgpa = db.Column(db.Numeric(4, 2), nullable=True)
    skills = db.Column(db.Text, nullable=True)  # Comma-separated tags
    bio = db.Column(db.Text, nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    preferred_domain = db.Column(db.String(100), nullable=True)
    preferred_location = db.Column(db.String(100), nullable=True)
    preferred_duration = db.Column(db.String(50), nullable=True)
    profile_pic = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    resumes = db.relationship('Resume', backref='student', cascade='all, delete-orphan', lazy='dynamic', order_by='Resume.uploaded_at.desc()')
    applications = db.relationship('Application', backref='student', cascade='all, delete-orphan', lazy='dynamic', order_by='Application.applied_at.desc()')
    reports = db.relationship('ScamReport', backref='student', cascade='all, delete-orphan', lazy='dynamic')

    def get_skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    def primary_resume(self):
        primary = self.resumes.filter_by(is_primary=True).first()
        if not primary:
            primary = self.resumes.first()
        return primary


class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    is_primary = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=utc_now)

    applications = db.relationship('Application', backref='resume', lazy='dynamic')


class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    website = db.Column(db.String(255), nullable=True)
    official_email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), default='India')
    registration_gst_number = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    contact_person_name = db.Column(db.String(100), nullable=True)
    contact_person_designation = db.Column(db.String(100), nullable=True)
    logo = db.Column(db.String(255), default='default_company.png')
    verification_status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name='verification_statuses'),
        default='pending',
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    verifications = db.relationship('CompanyVerification', backref='company', cascade='all, delete-orphan', lazy='dynamic', order_by='CompanyVerification.created_at.desc()')
    internships = db.relationship('Internship', backref='company', cascade='all, delete-orphan', lazy='dynamic', order_by='Internship.created_at.desc()')
    reports = db.relationship('ScamReport', backref='company', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def is_verified(self):
        return self.verification_status == 'approved'


class CompanyVerification(db.Model):
    __tablename__ = 'company_verifications'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', name='verif_status'), default='pending', nullable=False)
    review_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)


class InternshipCategory(db.Model):
    __tablename__ = 'internship_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_class = db.Column(db.String(50), default='bi bi-briefcase')

    internships = db.relationship('Internship', backref='category', lazy='dynamic')


class Internship(db.Model):
    __tablename__ = 'internships'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('internship_categories.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    responsibilities = db.Column(db.Text, nullable=True)
    eligibility = db.Column(db.Text, nullable=False)
    skills_required = db.Column(db.Text, nullable=False)
    duration_weeks = db.Column(db.Integer, default=8)
    duration_text = db.Column(db.String(50), nullable=False)  # e.g., "3 Months", "6 Months"
    location_type = db.Column(db.Enum('remote', 'on-site', 'hybrid', name='loc_types'), default='remote')
    location_city = db.Column(db.String(100), nullable=True)
    stipend_type = db.Column(db.Enum('paid', 'unpaid', 'performance-based', name='stipend_types'), default='paid')
    stipend_amount = db.Column(db.Numeric(10, 2), default=0.00)
    stipend_currency = db.Column(db.String(10), default='INR')
    openings_count = db.Column(db.Integer, default=1)
    start_date = db.Column(db.Date, nullable=True)
    application_deadline = db.Column(db.Date, nullable=False)
    application_instructions = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(150), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=True)
    status = db.Column(
        db.Enum('active', 'flagged', 'closed', 'rejected', name='internship_statuses'),
        default='active',
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    scam_check = db.relationship('ScamCheck', backref='internship', uselist=False, cascade='all, delete-orphan')
    applications = db.relationship('Application', backref='internship', cascade='all, delete-orphan', lazy='dynamic', order_by='Application.applied_at.desc()')
    reports = db.relationship('ScamReport', backref='internship', cascade='all, delete-orphan', lazy='dynamic')

    def get_skills_list(self):
        if not self.skills_required:
            return []
        return [s.strip() for s in self.skills_required.split(',') if s.strip()]

    @property
    def is_open(self):
        return self.status == 'active' and (self.application_deadline >= datetime.now().date())


class ScamCheck(db.Model):
    __tablename__ = 'scam_checks'

    id = db.Column(db.Integer, primary_key=True)
    internship_id = db.Column(db.Integer, db.ForeignKey('internships.id', ondelete='CASCADE'), unique=True, nullable=False)
    risk_score = db.Column(db.Integer, nullable=False, default=0)
    risk_level = db.Column(db.Enum('Low', 'Medium', 'High', name='risk_levels'), nullable=False, default='Low')
    triggered_rules = db.Column(db.Text, nullable=False, default='[]')  # JSON array
    summary_notes = db.Column(db.Text, nullable=True)
    is_reviewed_by_admin = db.Column(db.Boolean, default=False)
    admin_verdict = db.Column(db.Enum('pending', 'approved', 'rejected', name='admin_verdicts'), default='pending')
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def get_rules_list(self):
        try:
            return json.loads(self.triggered_rules) if self.triggered_rules else []
        except Exception:
            return []


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    internship_id = db.Column(db.Integer, db.ForeignKey('internships.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    cover_letter = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum('Applied', 'Under Review', 'Selected', 'Rejected', 'Completed', name='app_statuses'),
        default='Applied',
        nullable=False,
        index=True
    )
    company_feedback = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'internship_id', name='uq_student_internship_app'),
    )


class ScamReport(db.Model):
    __tablename__ = 'scam_reports'

    id = db.Column(db.Integer, primary_key=True)
    reported_by_student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    internship_id = db.Column(db.Integer, db.ForeignKey('internships.id', ondelete='CASCADE'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True)
    reason = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence_link = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('open', 'investigating', 'resolved', 'dismissed', name='report_statuses'), default='open', nullable=False)
    admin_resolution = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    resolved_at = db.Column(db.DateTime, nullable=True)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.Enum('application', 'verification', 'scam_alert', 'report', 'admin', 'general', name='notif_categories'), default='general')
    link_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
