from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.models import db, Internship, InternshipCategory, Application, Resume, Company, User
from app.decorators import role_required
from app.services.notifications import notify
from app.services.uploads import save_resume

internships_bp = Blueprint('internships', __name__)


@internships_bp.route('/')
def list_internships():
    # Safe page parameter parsing
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    keyword = request.args.get('keyword', '').strip()
    skills = request.args.get('skills', '').strip()
    eligibility = request.args.get('eligibility', '').strip()

    # Safe category parameter parsing
    category_id = None
    cat_raw = request.args.get('category')
    if cat_raw is not None and str(cat_raw).strip():
        try:
            category_id = int(str(cat_raw).strip())
        except (ValueError, TypeError):
            category_id = None

    location_type = request.args.get('location_type', '').strip()
    location_city = request.args.get('city', '').strip()
    stipend_type = request.args.get('stipend_type', '').strip()

    # Safe numeric validation: min_stipend
    min_stipend = None
    min_stip_raw = request.args.get('min_stipend')
    if min_stip_raw is not None and str(min_stip_raw).strip():
        try:
            val = float(str(min_stip_raw).strip())
            if val > 0:
                min_stipend = val
        except (ValueError, TypeError):
            min_stipend = None

    # Safe numeric validation: min_duration and max_duration in weeks
    min_duration = None
    min_dur_raw = request.args.get('min_duration')
    if min_dur_raw is not None and str(min_dur_raw).strip():
        try:
            val = int(str(min_dur_raw).strip())
            if val >= 0:
                min_duration = val
        except (ValueError, TypeError):
            min_duration = None

    max_duration = None
    max_dur_raw = request.args.get('max_duration')
    if max_dur_raw is not None and str(max_dur_raw).strip():
        try:
            val = int(str(max_dur_raw).strip())
            if val >= 0:
                max_duration = val
        except (ValueError, TypeError):
            max_duration = None

    # Base query: only active listings from approved companies with active user accounts
    query = (
        Internship.query
        .join(Company, Internship.company_id == Company.id)
        .join(User, Company.user_id == User.id)
        .filter(
            Internship.status == 'active',
            Company.verification_status == 'approved',
            User.is_active == True
        )
    )

    if keyword:
        search_filter = f"%{keyword}%"
        query = query.filter(
            (Internship.title.ilike(search_filter)) |
            (Internship.description.ilike(search_filter)) |
            (Internship.skills_required.ilike(search_filter)) |
            (Company.company_name.ilike(search_filter))
        )

    if skills:
        query = query.filter(Internship.skills_required.ilike(f"%{skills}%"))

    if eligibility:
        query = query.filter(Internship.eligibility.ilike(f"%{eligibility}%"))

    if category_id:
        query = query.filter(Internship.category_id == category_id)

    if location_type:
        query = query.filter(Internship.location_type == location_type)

    if location_city:
        query = query.filter(Internship.location_city.ilike(f"%{location_city}%"))

    if stipend_type:
        query = query.filter(Internship.stipend_type == stipend_type)

    if min_stipend is not None:
        query = query.filter(Internship.stipend_amount >= min_stipend)

    if min_duration is not None:
        query = query.filter(Internship.duration_weeks >= min_duration)

    if max_duration is not None:
        query = query.filter(Internship.duration_weeks <= max_duration)

    # Order by newest
    query = query.order_by(Internship.created_at.desc())

    per_page = current_app.config.get('PER_PAGE', 8)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    categories = InternshipCategory.query.order_by(InternshipCategory.name.asc()).all()

    return render_template(
        'internships/list.html',
        pagination=pagination,
        internships=pagination.items,
        categories=categories,
        keyword=keyword,
        skills=skills,
        eligibility=eligibility,
        selected_category=category_id,
        selected_location_type=location_type,
        selected_city=location_city,
        selected_stipend_type=stipend_type,
        min_stipend=min_stipend,
        min_duration=min_duration,
        max_duration=max_duration
    )


@internships_bp.route('/<int:internship_id>')
def detail(internship_id):
    internship = Internship.query.get_or_404(internship_id)
    company = internship.company
    company_user = company.user if company else None

    # Check ownership or admin status
    is_owner = (
        current_user.is_authenticated
        and current_user.is_company
        and current_user.company_profile is not None
        and internship.company_id == current_user.company_profile.id
    )
    is_admin = current_user.is_authenticated and current_user.is_admin

    is_publicly_eligible = (
        internship.status == 'active'
        and company is not None
        and company.verification_status == 'approved'
        and company_user is not None
        and company_user.is_active is True
    )

    # Refuse access and avoid leaking private details if not eligible
    if not is_publicly_eligible and not (is_owner or is_admin):
        abort(404)

    existing_application = None
    student_resumes = []

    if current_user.is_authenticated and current_user.is_student:
        student = current_user.student_profile
        if student:
            existing_application = Application.query.filter_by(
                internship_id=internship.id,
                student_id=student.id
            ).first()
            student_resumes = student.resumes.order_by(Resume.uploaded_at.desc()).all()

    # Get scam rules list if available
    triggered_rules = []
    if internship.scam_check:
        triggered_rules = internship.scam_check.get_rules_list()

    return render_template(
        'internships/detail.html',
        internship=internship,
        existing_application=existing_application,
        student_resumes=student_resumes,
        triggered_rules=triggered_rules,
        today=date.today()
    )


@internships_bp.route('/<int:internship_id>/apply', methods=['POST'])
@login_required
@role_required('student')
def apply(internship_id):
    internship = Internship.query.get_or_404(internship_id)
    company = internship.company
    company_user = company.user if company else None

    # Refuse access if posting or company is not publicly eligible
    is_publicly_eligible = (
        internship.status == 'active'
        and company is not None
        and company.verification_status == 'approved'
        and company_user is not None
        and company_user.is_active is True
    )
    if not is_publicly_eligible:
        abort(404)

    student = current_user.student_profile

    if not student:
        flash('Please fill in your profile before applying.', 'warning')
        return redirect(url_for('student.profile'))

    # Check if deadline passed
    if internship.application_deadline < date.today():
        flash('The application deadline for this internship has passed.', 'danger')
        return redirect(url_for('internships.detail', internship_id=internship.id))

    # Check if active
    if internship.status != 'active':
        flash('Applications for this posting are currently closed.', 'warning')
        return redirect(url_for('internships.detail', internship_id=internship.id))

    # Medium-risk safety warning enforcement (server-side verification)
    if internship.scam_check and internship.scam_check.risk_level == 'Medium':
        acknowledged = request.form.get('acknowledge_safety_warning')
        if not acknowledged or str(acknowledged).lower() not in ('1', 'true', 'yes', 'on'):
            flash('You must acknowledge that you have read the safety warning before applying to a Medium-risk internship.', 'danger')
            return redirect(url_for('internships.detail', internship_id=internship.id))

    # Prevent duplicate application
    existing = Application.query.filter_by(
        internship_id=internship.id,
        student_id=student.id
    ).first()
    if existing:
        flash('You have already applied for this internship position.', 'info')
        return redirect(url_for('internships.detail', internship_id=internship.id))

    resume_id = request.form.get('resume_id')
    cover_letter = request.form.get('cover_letter', '').strip()

    # Check if new resume was uploaded right in the modal
    new_resume_file = request.files.get('new_resume')
    selected_resume = None

    if new_resume_file and new_resume_file.filename:
        is_valid, err_msg, res_info = save_resume(new_resume_file, student.id)
        if not is_valid:
            flash(err_msg, 'danger')
            return redirect(url_for('internships.detail', internship_id=internship.id))

        selected_resume = Resume(
            student_id=student.id,
            filename=res_info['filename'],
            original_name=res_info['original_name'],
            file_path=res_info['file_path'],
            file_size=res_info['file_size'],
            is_primary=False
        )
        db.session.add(selected_resume)
        db.session.flush()

    elif resume_id:
        selected_resume = Resume.query.filter_by(id=int(resume_id), student_id=student.id).first()

    if not selected_resume:
        selected_resume = student.primary_resume()

    if not selected_resume:
        flash('Please attach or upload a resume to complete your application.', 'warning')
        return redirect(url_for('internships.detail', internship_id=internship.id))

    application = Application(
        internship_id=internship.id,
        student_id=student.id,
        resume_id=selected_resume.id,
        cover_letter=cover_letter,
        status='Applied'
    )
    db.session.add(application)

    # In-app notification for the company
    notify(
        user_id=internship.company.user_id,
        title=f"New Candidate Applied: {internship.title}",
        message=f"{student.full_name} has submitted an application for '{internship.title}'.",
        category="application",
        link_url=url_for('company.applicants', internship_id=internship.id)
    )

    # Notification for student
    notify(
        user_id=current_user.id,
        title="Application Submitted",
        message=f"You successfully applied for '{internship.title}' at {internship.company.company_name}.",
        category="application",
        link_url=url_for('student.applications')
    )

    db.session.commit()
    flash('Congratulations! Your application has been successfully submitted.', 'success')
    return redirect(url_for('student.applications'))
