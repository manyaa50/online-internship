from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app import limiter
from app.models import db, User, StudentProfile, Company, Notification
from app.services.notifications import notify
from app.validators import (
    is_safe_redirect_url,
    validate_email_address,
    validate_indian_phone,
    validate_gstin,
    validate_password
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_company:
            return redirect(url_for('company.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        # Generic failure message to prevent email enumeration attacks
        if not user or not user.check_password(password):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Your account has been deactivated or blocked. Please contact support.', 'danger')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.display_name}!', 'success')

        # Open Redirect Prevention: strictly validate next target
        next_page = request.args.get('next')
        if next_page and is_safe_redirect_url(next_page):
            return redirect(next_page)

        # Fallback to role-specific safe default destination
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif user.is_company:
            return redirect(url_for('company.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        role = request.form.get('role', 'student').strip().lower()
        email_raw = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone_raw = request.form.get('phone', '').strip()

        # 1. Role validation
        if role not in ['student', 'company']:
            flash('Invalid role selected.', 'danger')
            return render_template('auth/register.html')

        # 2. Required fields presence check
        if not email_raw or not password or not phone_raw:
            flash('Please fill in all mandatory fields.', 'warning')
            return render_template('auth/register.html')

        # 3. Email validation via email-validator
        is_valid_email, email_err, norm_email = validate_email_address(email_raw)
        if not is_valid_email:
            flash(email_err, 'danger')
            return render_template('auth/register.html')

        # 4. Indian phone number validation
        is_valid_phone, phone_err, norm_phone = validate_indian_phone(phone_raw)
        if not is_valid_phone:
            flash(phone_err, 'danger')
            return render_template('auth/register.html')

        # 5. Password complexity validation (minimum 8 characters, at least 1 letter and 1 digit)
        is_valid_pass, pass_err = validate_password(password)
        if not is_valid_pass:
            flash(pass_err, 'warning')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        existing_user = User.query.filter_by(email=norm_email).first()
        if existing_user:
            flash('An account with this email already exists. Please log in.', 'info')
            return redirect(url_for('auth.login'))

        # Create user with secure password hash
        new_user = User(email=norm_email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()  # obtain new_user.id

        if role == 'student':
            full_name = request.form.get('full_name', '').strip()
            college_name = request.form.get('college_name', '').strip()
            degree = request.form.get('degree', '').strip()

            if not full_name:
                flash('Please provide your full name.', 'warning')
                db.session.rollback()
                return render_template('auth/register.html')

            student = StudentProfile(
                user_id=new_user.id,
                full_name=full_name,
                phone=norm_phone,
                college_name=college_name,
                degree=degree
            )
            db.session.add(student)

            notify(
                user_id=new_user.id,
                title="Welcome to SmartIntern!",
                message="Your student account has been created. Complete your profile and upload your resume to start applying safely.",
                category="general",
                link_url=url_for('student.profile')
            )

        elif role == 'company':
            company_name = request.form.get('company_name', '').strip()
            website = request.form.get('website', '').strip()
            official_email_raw = request.form.get('official_email', norm_email).strip()
            gst_no = request.form.get('registration_gst_number', '').strip()
            contact_person = request.form.get('contact_person_name', '').strip()

            if not company_name:
                flash('Please provide the company name.', 'warning')
                db.session.rollback()
                return render_template('auth/register.html')

            # Validate official company email
            is_valid_off_email, off_err, norm_off_email = validate_email_address(official_email_raw)
            if not is_valid_off_email:
                flash(f"Invalid official company email: {off_err}", 'danger')
                db.session.rollback()
                return render_template('auth/register.html')

            # Validate Indian GSTIN if provided
            norm_gst = None
            if gst_no:
                is_valid_gst, gst_err, norm_gst = validate_gstin(gst_no)
                if not is_valid_gst:
                    flash(gst_err, 'danger')
                    db.session.rollback()
                    return render_template('auth/register.html')

            company = Company(
                user_id=new_user.id,
                company_name=company_name,
                phone=norm_phone,
                official_email=norm_off_email,
                website=website,
                registration_gst_number=norm_gst,
                contact_person_name=contact_person,
                verification_status='pending'
            )
            db.session.add(company)

            notify(
                user_id=new_user.id,
                title="Company Account Registered",
                message="Your company profile has been submitted for administrative verification. You can post internships once verified.",
                category="verification",
                link_url=url_for('company.profile')
            )

        db.session.commit()
        flash('Registration successful! You can now log in with your credentials.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('index'))


@auth_bp.route('/notifications')
@login_required
def notifications():
    user_notifications = current_user.notifications.all()
    # Mark as read when visited
    for n in user_notifications:
        n.is_read = True
    db.session.commit()
    return render_template('notifications/list.html', notifications=user_notifications)


@auth_bp.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})
