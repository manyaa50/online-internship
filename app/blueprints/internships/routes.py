import os
import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Internship, InternshipCategory, Application, Resume, Company, Notification, ScamCheck
from app.decorators import role_required
from app.utils import validate_resume_upload

internships_bp = Blueprint('internships', __name__)


@internships_bp.route('/')
def list_internships():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '').strip()
    category_id = request.args.get('category', type=int)
    location_type = request.args.get('location_type', '').strip()
    location_city = request.args.get('city', '').strip()
    stipend_type = request.args.get('stipend_type', '').strip()
    min_stipend = request.args.get('min_stipend', type=float)

    # Base query: only active listings
    query = Internship.query.filter(Internship.status == 'active')

    if keyword:
        search_filter = f"%{keyword}%"
        query = query.join(Company).filter(
            (Internship.title.ilike(search_filter)) |
            (Internship.description.ilike(search_filter)) |
            (Internship.skills_required.ilike(search_filter)) |
            (Company.company_name.ilike(search_filter))
        )

    if category_id:
        query = query.filter(Internship.category_id == category_id)

    if location_type:
        query = query.filter(Internship.location_type == location_type)

    if location_city:
        query = query.filter(Internship.location_city.ilike(f"%{location_city}%"))

    if stipend_type:
        query = query.filter(Internship.stipend_type == stipend_type)

    if min_stipend is not None and min_stipend > 0:
        query = query.filter(Internship.stipend_amount >= min_stipend)

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
        selected_category=category_id,
        selected_location_type=location_type,
        selected_city=location_city,
        selected_stipend_type=stipend_type,
        min_stipend=min_stipend
    )


@internships_bp.route('/<int:internship_id>')
def detail(internship_id):
    internship = Internship.query.get_or_404(internship_id)

    # If internship is flagged or closed, only company owner or admin can view
    if internship.status != 'active':
        is_owner = (current_user.is_authenticated and current_user.is_company and internship.company_id == current_user.company_profile.id)
        is_admin = (current_user.is_authenticated and current_user.is_admin)
        if not (is_owner or is_admin):
            flash('This internship listing is currently unavailable or under administrative review.', 'warning')
            return redirect(url_for('internships.list_internships'))

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
        is_valid, err_msg, meta = validate_resume_upload(new_resume_file)
        if not is_valid:
            flash(err_msg, 'danger')
            return redirect(url_for('internships.detail', internship_id=internship.id))

        unique_name = f"resume_{student.id}_{uuid.uuid4().hex[:8]}.{meta['ext']}"
        save_dir = current_app.config['RESUME_FOLDER']
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, unique_name)

        new_resume_file.save(save_path)
        selected_resume = Resume(
            student_id=student.id,
            filename=unique_name,
            original_name=meta['original_name'],
            file_path=f"instance/uploads/resumes/{unique_name}",
            file_size=meta['file_size'],
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
    notif = Notification(
        user_id=internship.company.user_id,
        title=f"New Candidate Applied: {internship.title}",
        message=f"{student.full_name} has submitted an application for '{internship.title}'.",
        category="application",
        link_url=url_for('company.applicants', internship_id=internship.id)
    )
    db.session.add(notif)

    # Notification for student
    student_notif = Notification(
        user_id=current_user.id,
        title="Application Submitted",
        message=f"You successfully applied for '{internship.title}' at {internship.company.company_name}.",
        category="application",
        link_url=url_for('student.applications')
    )
    db.session.add(student_notif)

    db.session.commit()
    flash('Congratulations! Your application has been successfully submitted.', 'success')
    return redirect(url_for('student.applications'))
