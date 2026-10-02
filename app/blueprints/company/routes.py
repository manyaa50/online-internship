import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import db, Company, Internship, InternshipCategory, Application, ScamCheck, Notification, User, CompanyVerification
from app.decorators import role_required, company_verified_required
from app.scam_detector import ScamDetector

company_bp = Blueprint('company', __name__)


@company_bp.route('/dashboard')
@login_required
@role_required('company')
def dashboard():
    company = current_user.company_profile
    if not company:
        flash('Please fill in your company details.', 'warning')
        return redirect(url_for('company.profile'))

    # Stats
    total_postings = company.internships.count()
    active_postings = company.internships.filter_by(status='active').count()
    flagged_postings = company.internships.filter_by(status='flagged').count()

    # Total applications received
    total_applications = (
        Application.query.join(Internship)
        .filter(Internship.company_id == company.id)
        .count()
    )
    pending_applications = (
        Application.query.join(Internship)
        .filter(Internship.company_id == company.id, Application.status.in_(['Applied', 'Under Review']))
        .count()
    )

    recent_postings = company.internships.order_by(Internship.created_at.desc()).limit(5).all()
    recent_applications = (
        Application.query.join(Internship)
        .filter(Internship.company_id == company.id)
        .order_by(Application.applied_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'company/dashboard.html',
        company=company,
        total_postings=total_postings,
        active_postings=active_postings,
        flagged_postings=flagged_postings,
        total_applications=total_applications,
        pending_applications=pending_applications,
        recent_postings=recent_postings,
        recent_applications=recent_applications
    )


@company_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('company')
def profile():
    company = current_user.company_profile

    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        website = request.form.get('website', '').strip()
        official_email = request.form.get('official_email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        country = request.form.get('country', 'India').strip()
        registration_gst = request.form.get('registration_gst_number', '').strip()
        description = request.form.get('description', '').strip()
        contact_person = request.form.get('contact_person_name', '').strip()
        contact_designation = request.form.get('contact_person_designation', '').strip()

        if not company_name or not official_email or not phone:
            flash('Company Name, Official Email, and Phone are mandatory.', 'warning')
            return render_template('company/profile.html', company=company)

        company.company_name = company_name
        company.website = website
        company.official_email = official_email
        company.phone = phone
        company.address = address
        company.city = city
        company.state = state
        company.country = country
        company.registration_gst_number = registration_gst
        company.description = description
        company.contact_person_name = contact_person
        company.contact_person_designation = contact_designation

        # Handle Logo upload
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            ext = logo_file.filename.rsplit('.', 1)[-1].lower()
            if ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
                logo_name = f"comp_{company.id}_{uuid.uuid4().hex[:8]}.{ext}"
                logo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], logo_name)
                logo_file.save(logo_path)
                company.logo = logo_name

        # If company was rejected and they updated their profile, reset status to pending for review
        if company.verification_status == 'rejected' and request.form.get('resubmit_verification'):
            company.verification_status = 'pending'
            verif_entry = CompanyVerification(
                company_id=company.id,
                status='pending',
                review_notes="Company resubmitted profile for re-verification."
            )
            db.session.add(verif_entry)
            flash('Profile updated and resubmitted for admin verification.', 'info')
        else:
            flash('Company profile updated successfully.', 'success')

        db.session.commit()
        return redirect(url_for('company.profile'))

    verifications = company.verifications.order_by(CompanyVerification.created_at.desc()).all() if company else []
    return render_template('company/profile.html', company=company, verifications=verifications)


@company_bp.route('/internships/create', methods=['GET', 'POST'])
@login_required
@role_required('company')
@company_verified_required
def create_internship():
    company = current_user.company_profile
    categories = InternshipCategory.query.order_by(InternshipCategory.name.asc()).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id')
        description = request.form.get('description', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        eligibility = request.form.get('eligibility', '').strip()
        skills = request.form.get('skills_required', '').strip()
        duration_text = request.form.get('duration_text', '3 Months').strip()
        duration_weeks = request.form.get('duration_weeks', 12)
        location_type = request.form.get('location_type', 'remote')
        location_city = request.form.get('location_city', '').strip()
        stipend_type = request.form.get('stipend_type', 'paid')
        stipend_amount = request.form.get('stipend_amount', 0)
        openings_count = request.form.get('openings_count', 1)
        deadline_str = request.form.get('application_deadline')
        contact_email = request.form.get('contact_email', company.official_email).strip()
        contact_phone = request.form.get('contact_phone', company.phone).strip()

        # Validation
        if not title or not category_id or not description or not eligibility or not deadline_str:
            flash('Please complete all required fields.', 'warning')
            return render_template('company/post_internship.html', categories=categories)

        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid deadline date format. Please use YYYY-MM-DD.', 'danger')
            return render_template('company/post_internship.html', categories=categories)

        try:
            stipend_amt = float(stipend_amount) if stipend_type == 'paid' else 0.0
        except ValueError:
            stipend_amt = 0.0

        posting_data = {
            'title': title,
            'description': description,
            'responsibilities': responsibilities,
            'eligibility': eligibility,
            'skills_required': skills,
            'stipend_type': stipend_type,
            'stipend_amount': stipend_amt,
            'contact_email': contact_email,
            'contact_phone': contact_phone
        }

        # Run automated Scam Detection Engine
        scan_result = ScamDetector.evaluate_posting(posting_data, company=company)
        risk_score = scan_result['risk_score']
        risk_level = scan_result['risk_level']
        triggered_rules_json = json.dumps(scan_result['triggered_rules'])

        # Determine initial posting status based on risk level
        if risk_level == 'High':
            posting_status = 'flagged'
        else:
            posting_status = 'active'

        # Create Internship Record
        internship = Internship(
            company_id=company.id,
            category_id=int(category_id),
            title=title,
            description=description,
            responsibilities=responsibilities,
            eligibility=eligibility,
            skills_required=skills,
            duration_weeks=int(duration_weeks) if duration_weeks else 8,
            duration_text=duration_text,
            location_type=location_type,
            location_city=location_city,
            stipend_type=stipend_type,
            stipend_amount=stipend_amt,
            openings_count=int(openings_count) if openings_count else 1,
            application_deadline=deadline,
            contact_email=contact_email,
            contact_phone=contact_phone,
            status=posting_status
        )
        db.session.add(internship)
        db.session.flush()

        # Create Scam Check Record
        scam_check = ScamCheck(
            internship_id=internship.id,
            risk_score=risk_score,
            risk_level=risk_level,
            triggered_rules=triggered_rules_json,
            summary_notes=scan_result['summary_notes'],
            is_reviewed_by_admin=(risk_level == 'Low'),
            admin_verdict='approved' if risk_level == 'Low' else 'pending'
        )
        db.session.add(scam_check)

        # Notify Admins if high risk
        if risk_level == 'High':
            admins = User.query.filter_by(role='admin').all()
            for admin_user in admins:
                notif = Notification(
                    user_id=admin_user.id,
                    title="⚠️ Scam Alert: High Risk Internship Flagged",
                    message=f"Internship '{title}' by {company.company_name} triggered high scam score ({risk_score}/100) and has been held.",
                    category="scam_alert",
                    link_url=url_for('admin.flagged_internships')
                )
                db.session.add(notif)

            flash(f'Notice: Your posting scored a high risk rating ({risk_score}/100) on our automated safety scanner and has been queued for administrator review.', 'warning')
        elif risk_level == 'Medium':
            flash(f'Your internship has been published! Note: Safety scanner detected minor warnings (Score: {risk_score}/100) displayed to students.', 'info')
        else:
            flash('Internship verified by safety screening and published successfully!', 'success')

        db.session.commit()
        return redirect(url_for('company.manage_internships'))

    return render_template('company/post_internship.html', categories=categories, company=company)


@company_bp.route('/internships')
@login_required
@role_required('company')
def manage_internships():
    company = current_user.company_profile
    internships = company.internships.order_by(Internship.created_at.desc()).all()
    return render_template('company/manage_internships.html', internships=internships, company=company)


@company_bp.route('/internships/edit/<int:internship_id>', methods=['GET', 'POST'])
@login_required
@role_required('company')
def edit_internship(internship_id):
    company = current_user.company_profile
    internship = Internship.query.filter_by(id=internship_id, company_id=company.id).first_or_404()
    categories = InternshipCategory.query.order_by(InternshipCategory.name.asc()).all()

    if request.method == 'POST':
        internship.title = request.form.get('title', '').strip()
        internship.category_id = int(request.form.get('category_id'))
        internship.description = request.form.get('description', '').strip()
        internship.responsibilities = request.form.get('responsibilities', '').strip()
        internship.eligibility = request.form.get('eligibility', '').strip()
        internship.skills_required = request.form.get('skills_required', '').strip()
        internship.duration_text = request.form.get('duration_text', '3 Months').strip()
        internship.duration_weeks = int(request.form.get('duration_weeks', 12))
        internship.location_type = request.form.get('location_type', 'remote')
        internship.location_city = request.form.get('location_city', '').strip()
        internship.stipend_type = request.form.get('stipend_type', 'paid')
        
        try:
            internship.stipend_amount = float(request.form.get('stipend_amount', 0)) if internship.stipend_type == 'paid' else 0.0
        except ValueError:
            internship.stipend_amount = 0.0

        internship.openings_count = int(request.form.get('openings_count', 1))
        deadline_str = request.form.get('application_deadline')
        if deadline_str:
            internship.application_deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

        internship.contact_email = request.form.get('contact_email', company.official_email).strip()
        internship.contact_phone = request.form.get('contact_phone', company.phone).strip()

        # Re-screen with ScamDetector
        posting_data = {
            'title': internship.title,
            'description': internship.description,
            'responsibilities': internship.responsibilities,
            'eligibility': internship.eligibility,
            'skills_required': internship.skills_required,
            'stipend_type': internship.stipend_type,
            'stipend_amount': float(internship.stipend_amount),
            'contact_email': internship.contact_email,
            'contact_phone': internship.contact_phone
        }

        scan = ScamDetector.evaluate_posting(posting_data, company=company)
        
        if not internship.scam_check:
            internship.scam_check = ScamCheck(internship_id=internship.id)

        internship.scam_check.risk_score = scan['risk_score']
        internship.scam_check.risk_level = scan['risk_level']
        internship.scam_check.triggered_rules = json.dumps(scan['triggered_rules'])
        internship.scam_check.summary_notes = scan['summary_notes']

        if scan['risk_level'] == 'High':
            internship.status = 'flagged'
            flash(f'Update saved: Warning - high risk score ({scan["risk_score"]}/100) triggered. Held for admin review.', 'warning')
        else:
            if internship.status == 'flagged' and scan['risk_level'] in ['Low', 'Medium']:
                internship.status = 'active'
            flash('Internship updated successfully!', 'success')

        db.session.commit()
        return redirect(url_for('company.manage_internships'))

    return render_template('company/post_internship.html', internship=internship, categories=categories, company=company, is_edit=True)


@company_bp.route('/internships/status/<int:internship_id>/<string:new_status>', methods=['POST'])
@login_required
@role_required('company')
def toggle_status(internship_id, new_status):
    company = current_user.company_profile
    internship = Internship.query.filter_by(id=internship_id, company_id=company.id).first_or_404()

    if new_status in ['active', 'closed']:
        internship.status = new_status
        db.session.commit()
        flash(f'Internship status changed to {new_status}.', 'success')
    else:
        flash('Invalid status action.', 'danger')

    return redirect(url_for('company.manage_internships'))


@company_bp.route('/internships/delete/<int:internship_id>', methods=['POST'])
@login_required
@role_required('company')
def delete_internship(internship_id):
    company = current_user.company_profile
    internship = Internship.query.filter_by(id=internship_id, company_id=company.id).first_or_404()

    db.session.delete(internship)
    db.session.commit()
    flash('Internship listing deleted.', 'info')
    return redirect(url_for('company.manage_internships'))


@company_bp.route('/applicants')
@login_required
@role_required('company')
def applicants():
    company = current_user.company_profile
    internship_id = request.args.get('internship_id')
    status_filter = request.args.get('status')

    query = Application.query.join(Internship).filter(Internship.company_id == company.id)

    if internship_id:
        query = query.filter(Application.internship_id == int(internship_id))
    if status_filter:
        query = query.filter(Application.status == status_filter)

    applications_list = query.order_by(Application.applied_at.desc()).all()
    company_internships = company.internships.all()

    return render_template(
        'company/applicants.html',
        applications=applications_list,
        internships=company_internships,
        selected_internship=int(internship_id) if internship_id else None,
        selected_status=status_filter
    )


@company_bp.route('/applicants/update-status/<int:app_id>', methods=['POST'])
@login_required
@role_required('company')
def update_application_status(app_id):
    company = current_user.company_profile
    application = (
        Application.query.join(Internship)
        .filter(Application.id == app_id, Internship.company_id == company.id)
        .first_or_404()
    )

    new_status = request.form.get('status')
    feedback = request.form.get('company_feedback', '').strip()

    valid_statuses = ['Applied', 'Under Review', 'Selected', 'Rejected', 'Completed']
    if new_status in valid_statuses:
        application.status = new_status
        if feedback:
            application.company_feedback = feedback

        # Send in-app notification to the student
        notif = Notification(
            user_id=application.student.user_id,
            title=f"Application Update: {application.internship.title}",
            message=f"Your application status at {company.company_name} has been updated to '{new_status}'.",
            category="application",
            link_url=url_for('student.applications')
        )
        db.session.add(notif)
        db.session.commit()
        flash(f'Application status updated to {new_status} and student notified.', 'success')
    else:
        flash('Invalid status value.', 'danger')

    return redirect(request.referrer or url_for('company.applicants'))
