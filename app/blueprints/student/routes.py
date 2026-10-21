import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from app.models import db, StudentProfile, Resume, Application, Internship
from app.decorators import role_required
from app.services.uploads import save_profile_picture, save_resume
from app.validators import validate_indian_phone

student_bp = Blueprint('student', __name__)


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

    # Recent applications
    recent_apps = student.applications.order_by(Application.applied_at.desc()).limit(5).all()

    # Recommended internships based on skills
    skills_list = student.get_skills_list()
    recommended = []
    if skills_list:
        for intern in Internship.query.filter_by(status='active').limit(20).all():
            req_skills = intern.get_skills_list()
            matched = set(s.lower() for s in skills_list) & set(s.lower() for s in req_skills)
            if matched:
                recommended.append((intern, len(matched)))
        recommended.sort(key=lambda x: x[1], reverse=True)
        recommended = [r[0] for r in recommended[:4]]
    else:
        recommended = Internship.query.filter_by(status='active').order_by(Internship.created_at.desc()).limit(4).all()

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
        graduation_year = request.form.get('graduation_year')
        cgpa = request.form.get('cgpa')
        skills = request.form.get('skills', '').strip()
        bio = request.form.get('bio', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        github_url = request.form.get('github_url', '').strip()
        preferred_domain = request.form.get('preferred_domain', '').strip()
        preferred_location = request.form.get('preferred_location', '').strip()
        preferred_duration = request.form.get('preferred_duration', '').strip()

        if not full_name or not phone:
            flash('Full Name and Phone Number are required.', 'danger')
            return redirect(url_for('student.profile'))

        is_valid_phone, phone_err, norm_phone = validate_indian_phone(phone)
        if not is_valid_phone:
            flash(phone_err, 'danger')
            return redirect(url_for('student.profile'))

        # Safely parse numeric fields without HTTP 500 crashes
        parsed_grad_year = None
        if graduation_year and str(graduation_year).strip():
            try:
                parsed_grad_year = int(str(graduation_year).strip())
            except (ValueError, TypeError):
                flash('Graduation year must be a valid integer.', 'danger')
                return redirect(url_for('student.profile'))

        parsed_cgpa = None
        if cgpa and str(cgpa).strip():
            try:
                cgpa_val = float(str(cgpa).strip())
                if cgpa_val < 0 or cgpa_val > 10:
                    flash('CGPA must be between 0 and 10.', 'danger')
                    return redirect(url_for('student.profile'))
                parsed_cgpa = cgpa_val
            except (ValueError, TypeError):
                flash('CGPA must be a valid decimal number.', 'danger')
                return redirect(url_for('student.profile'))

        if not student:
            student = StudentProfile(user_id=current_user.id)
            db.session.add(student)

        student.full_name = full_name
        student.phone = norm_phone
        student.college_name = college_name
        student.degree = degree
        student.graduation_year = parsed_grad_year
        student.cgpa = parsed_cgpa
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
            pic_name = save_profile_picture(pic_file, student.id)
            if pic_name:
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
    if not student:
        flash('Please complete your profile before uploading a resume.', 'warning')
        return redirect(url_for('student.profile'))

    if 'resume_file' not in request.files:
        flash('No file selected.', 'warning')
        return redirect(url_for('student.profile'))

    file = request.files['resume_file']
    is_valid, err_msg, res_info = save_resume(file, student.id)
    if not is_valid:
        flash(err_msg, 'danger')
        return redirect(url_for('student.profile'))

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
        filename=res_info['filename'],
        original_name=res_info['original_name'],
        file_path=res_info['file_path'],
        file_size=res_info['file_size'],
        is_primary=make_primary
    )
    db.session.add(new_resume)
    db.session.commit()

    flash('Resume uploaded successfully!', 'success')
    return redirect(url_for('student.profile'))


@student_bp.route('/resume/download/<int:resume_id>')
@login_required
def download_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    # Permission check: student owner, applied company, or admin
    is_owner = (
        current_user.is_student
        and current_user.student_profile is not None
        and resume.student_id == current_user.student_profile.id
    )
    is_admin = current_user.is_admin
    is_authorized_company = False

    if current_user.is_company and current_user.company_profile is not None:
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

    resume_folder = current_app.config['RESUME_FOLDER']
    file_path = os.path.join(resume_folder, resume.filename)
    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(
        resume_folder,
        resume.filename,
        as_attachment=True,
        download_name=resume.original_name
    )


@student_bp.route('/resume/delete/<int:resume_id>', methods=['POST'])
@login_required
@role_required('student')
def delete_resume(resume_id):
    student = current_user.student_profile
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('student.profile'))

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

    apps = query.order_by(Application.applied_at.desc()).all()
    return render_template('student/applications.html', applications=apps, current_status=status_filter)
