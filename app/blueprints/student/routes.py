import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, StudentProfile, Resume, Application, Internship, Notification, Company
from app.decorators import role_required

student_bp = Blueprint('student', __name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_RESUME_EXTENSIONS']


@student_bp.route('/dashboard')
@login_required
@role_required('student')
def dashboard():
    student = current_user.student_profile
    if not student:
        flash('Please complete your profile to continue.', 'info')
        return redirect(url_for('student.profile'))

    # Stats
    total_apps = student.applications.count()
    under_review = student.applications.filter_by(status='Under Review').count()
    selected = student.applications.filter_by(status='Selected').count()
    rejected = student.applications.filter_by(status='Rejected').count()

    recent_apps = student.applications.order_by(Application.applied_at.desc()).limit(5).all()

    # Recommended internships based on preferred domain or skills
    recommended = []
    if student.preferred_domain or student.skills:
        query = Internship.query.filter(Internship.status == 'active')
        if student.preferred_domain:
            query = query.filter(
                (Internship.title.ilike(f"%{student.preferred_domain}%")) |
                (Internship.description.ilike(f"%{student.preferred_domain}%"))
            )
        recommended = query.order_by(Internship.created_at.desc()).limit(4).all()

    if not recommended:
        recommended = Internship.query.filter(Internship.status == 'active').order_by(Internship.created_at.desc()).limit(4).all()

    return render_template(
        'student/dashboard.html',
        student=student,
        total_apps=total_apps,
        under_review=under_review,
        selected=selected,
        rejected=rejected,
        recent_apps=recent_apps,
        recommended=recommended
    )


@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('student')
def profile():
    student = current_user.student_profile

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        college_name = request.form.get('college_name', '').strip()
        degree = request.form.get('degree', '').strip()
        grad_year = request.form.get('graduation_year')
        cgpa = request.form.get('cgpa')
        skills = request.form.get('skills', '').strip()
        bio = request.form.get('bio', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        github_url = request.form.get('github_url', '').strip()
        preferred_domain = request.form.get('preferred_domain', '').strip()
        preferred_location = request.form.get('preferred_location', '').strip()
        preferred_duration = request.form.get('preferred_duration', '').strip()

        if not full_name or not phone:
            flash('Full Name and Phone are required.', 'warning')
            return render_template('student/profile.html', student=student)

        student.full_name = full_name
        student.phone = phone
        student.college_name = college_name
        student.degree = degree
        student.graduation_year = int(grad_year) if grad_year and grad_year.isdigit() else None
        student.cgpa = float(cgpa) if cgpa else None
        student.skills = skills
        student.bio = bio
        student.linkedin_url = linkedin_url
        student.github_url = github_url
        student.preferred_domain = preferred_domain
        student.preferred_location = preferred_location
        student.preferred_duration = preferred_duration

        # Profile Picture Upload
        pic_file = request.files.get('profile_pic')
        if pic_file and pic_file.filename:
            ext = pic_file.filename.rsplit('.', 1)[-1].lower()
            if ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
                pic_name = f"avatar_{student.id}_{uuid.uuid4().hex[:8]}.{ext}"
                pic_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pic_name)
                pic_file.save(pic_path)
                student.profile_pic = pic_name

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.profile'))

    resumes = student.resumes.order_by(Resume.uploaded_at.desc()).all() if student else []
    return render_template('student/profile.html', student=student, resumes=resumes)


@student_bp.route('/resume/upload', methods=['POST'])
@login_required
@role_required('student')
def upload_resume():
    student = current_user.student_profile
    if 'resume_file' not in request.files:
        flash('No file selected.', 'warning')
        return redirect(url_for('student.profile'))

    file = request.files['resume_file']
    if file.filename == '':
        flash('No file chosen.', 'warning')
        return redirect(url_for('student.profile'))

    if file and allowed_file(file.filename):
        original_name = secure_filename(file.filename)
        ext = original_name.rsplit('.', 1)[1].lower()
        unique_filename = f"resume_{student.id}_{uuid.uuid4().hex[:8]}.{ext}"
        save_path = os.path.join(current_app.config['RESUME_FOLDER'], unique_filename)

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > current_app.config['MAX_CONTENT_LENGTH']:
            flash('File size exceeds the 8MB limit.', 'danger')
            return redirect(url_for('student.profile'))

        file.save(save_path)

        # If it's the first resume or marked primary, reset others
        is_first = student.resumes.count() == 0
        if is_first:
            make_primary = True
        else:
            make_primary = bool(request.form.get('is_primary'))

        if make_primary:
            Resume.query.filter_by(student_id=student.id).update({'is_primary': False})

        new_resume = Resume(
            student_id=student.id,
            filename=unique_filename,
            original_name=original_name,
            file_path=save_path,
            file_size=file_size,
            is_primary=make_primary
        )
        db.session.add(new_resume)
        db.session.commit()

        flash('Resume uploaded successfully!', 'success')
    else:
        flash('Invalid file format. Only PDF and DOCX files are permitted.', 'danger')

    return redirect(url_for('student.profile'))


@student_bp.route('/resume/download/<int:resume_id>')
@login_required
def download_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    # Permission check: student owner, applied company, or admin
    is_owner = (current_user.is_student and resume.student_id == current_user.student_profile.id)
    is_admin = current_user.is_admin
    is_authorized_company = False

    if current_user.is_company:
        # Check if the student applied to any internship belonging to this company
        company = current_user.company_profile
        has_app = Application.query.join(Internship).filter(
            Application.resume_id == resume.id,
            Internship.company_id == company.id
        ).first()
        if has_app:
            is_authorized_company = True

    if not (is_owner or is_admin or is_authorized_company):
        flash('You are not authorized to download this resume.', 'danger')
        return redirect(url_for('index'))

    return send_from_directory(
        current_app.config['RESUME_FOLDER'],
        resume.filename,
        as_attachment=True,
        download_name=resume.original_name
    )


@student_bp.route('/resume/delete/<int:resume_id>', methods=['POST'])
@login_required
@role_required('student')
def delete_resume(resume_id):
    student = current_user.student_profile
    resume = Resume.query.filter_by(id=resume_id, student_id=student.id).first_or_404()

    # If linked to applications, we keep the file or block deletion
    if resume.applications.count() > 0:
        flash('Cannot delete this resume because it has been used in existing internship applications.', 'warning')
        return redirect(url_for('student.profile'))

    file_path = os.path.join(current_app.config['RESUME_FOLDER'], resume.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.session.delete(resume)
    db.session.commit()
    flash('Resume removed successfully.', 'info')
    return redirect(url_for('student.profile'))


@student_bp.route('/applications')
@login_required
@role_required('student')
def applications():
    student = current_user.student_profile
    status_filter = request.args.get('status')

    query = student.applications
    if status_filter:
        query = query.filter_by(status=status_filter)

    all_apps = query.order_by(Application.applied_at.desc()).all()
    return render_template('student/applications.html', applications=all_apps, active_status=status_filter)
