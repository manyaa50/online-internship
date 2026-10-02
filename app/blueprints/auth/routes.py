from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, StudentProfile, Company, Notification

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
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

        if not user or not user.check_password(password):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Your account has been deactivated or blocked. Please contact support.', 'danger')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.display_name}!', 'success')

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

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
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()

        # Validation
        if role not in ['student', 'company']:
            flash('Invalid role selected.', 'danger')
            return render_template('auth/register.html')

        if not email or not password or not phone:
            flash('Please fill in all mandatory fields.', 'warning')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists. Please log in.', 'info')
            return redirect(url_for('auth.login'))

        # Create user
        new_user = User(email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()  # get user.id

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
                phone=phone,
                college_name=college_name,
                degree=degree
            )
            db.session.add(student)

            welcome_notif = Notification(
                user_id=new_user.id,
                title="Welcome to SmartIntern!",
                message="Your student account has been created. Complete your profile and upload your resume to start applying safely.",
                category="general",
                link_url=url_for('student.profile')
            )
            db.session.add(welcome_notif)

        elif role == 'company':
            company_name = request.form.get('company_name', '').strip()
            website = request.form.get('website', '').strip()
            official_email = request.form.get('official_email', email).strip().lower()
            gst_no = request.form.get('registration_gst_number', '').strip()
            contact_person = request.form.get('contact_person_name', '').strip()

            if not company_name:
                flash('Please provide the company name.', 'warning')
                db.session.rollback()
                return render_template('auth/register.html')

            company = Company(
                user_id=new_user.id,
                company_name=company_name,
                phone=phone,
                official_email=official_email,
                website=website,
                registration_gst_number=gst_no,
                contact_person_name=contact_person,
                verification_status='pending'
            )
            db.session.add(company)

            welcome_notif = Notification(
                user_id=new_user.id,
                title="Company Account Registered",
                message="Your company profile has been submitted for administrative verification. You can post internships once verified.",
                category="verification",
                link_url=url_for('company.profile')
            )
            db.session.add(welcome_notif)

        db.session.commit()
        flash('Registration successful! You can now log in with your credentials.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
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
