import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory
from flask_login import login_required, current_user
from app.models import db, Company, Internship, InternshipCategory, Application, ScamCheck, User, CompanyVerification
from app.decorators import role_required, company_verified_required
from app.scam_detector import ScamDetector
from app.services.notifications import notify
from app.services.uploads import save_company_logo, save_verification_doc
from app.validators import (
    validate_verification_document,
    validate_email_address,
    validate_indian_phone,
    validate_gstin,
    validate_internship_form
)

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

        # Validate official email
        is_valid_email, email_err, norm_email = validate_email_address(official_email)
        if not is_valid_email:
            flash(f"Invalid official company email: {email_err}", 'danger')
            return render_template('company/profile.html', company=company)

        # Validate Indian phone number
        is_valid_phone, phone_err, norm_phone = validate_indian_phone(phone)
        if not is_valid_phone:
            flash(phone_err, 'danger')
            return render_template('company/profile.html', company=company)

        # Validate Indian GSTIN if provided
        norm_gst = None
        if registration_gst:
            is_valid_gst, gst_err, norm_gst = validate_gstin(registration_gst)
            if not is_valid_gst:
                flash(gst_err, 'danger')
                return render_template('company/profile.html', company=company)

        company.company_name = company_name
        company.website = website
        company.official_email = norm_email
        company.phone = norm_phone
        company.address = address
        company.city = city
        company.state = state
        company.country = country
        company.registration_gst_number = norm_gst
        company.description = description
        company.contact_person_name = contact_person
        company.contact_person_designation = contact_designation

        # Handle Logo upload
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            logo_name = save_company_logo(logo_file, company.id)
            if logo_name:
                company.logo = logo_name

        # Handle Verification Document upload
        doc_file = request.files.get('verification_document')
        if doc_file and doc_file.filename:
            is_valid, err_msg, doc_info = save_verification_doc(doc_file, company.id)
            if not is_valid:
                flash(err_msg, 'danger')
                verifications = company.verifications.order_by(CompanyVerification.created_at.desc()).all() if company else []
                return render_template('company/profile.html', company=company, verifications=verifications)
            company.verification_document = doc_info['filename']

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


@company_bp.route('/document')
@login_required
@role_required('company')
def view_document():
    company = current_user.company_profile
    if not company or not company.verification_document:
        flash('No verification document has been uploaded.', 'warning')
        return redirect(url_for('company.profile'))

    docs_folder = current_app.config['DOCS_FOLDER']
    file_path = os.path.join(docs_folder, company.verification_document)
    if not os.path.isfile(file_path):
        flash('Verification document file not found on server.', 'danger')
        return redirect(url_for('company.profile'))

    return send_from_directory(
        docs_folder,
        company.verification_document,
        as_attachment=False
    )


@company_bp.route('/internships/create', methods=['GET', 'POST'])
@login_required
@role_required('company')
@company_verified_required
def create_internship():
    company = current_user.company_profile
    categories = InternshipCategory.query.order_by(InternshipCategory.name.asc()).all()

    if request.method == 'POST':
        is_valid, errors, cleaned = validate_internship_form(request.form, company=company)

        if not is_valid:
            for err in errors:
                flash(err, 'danger')
            form_data = request.form.to_dict()
            return render_template('company/post_internship.html',
                                   categories=categories, company=company,
                                   form_data=form_data, is_edit=False)

        # ── Scam Detection ─────────────────────────────────────────────
        existing_descriptions = [
            i.description for i in
            Internship.query.filter(
                Internship.company_id != company.id,
                Internship.status == 'active'
            ).with_entities(Internship.description).limit(200).all()
        ]

        posting_data = {
            'title': cleaned['title'],
            'description': cleaned['description'],
            'responsibilities': cleaned['responsibilities'],
            'eligibility': cleaned['eligibility'],
            'skills_required': cleaned['skills_required'],
            'stipend_type': cleaned['stipend_type'],
            'stipend_amount': cleaned['stipend_amount'],
            'contact_email': cleaned['contact_email'],
            'contact_phone': cleaned['contact_phone'],
            'application_instructions': cleaned['application_instructions'],
        }
        scan_result = ScamDetector.evaluate_posting(
            posting_data, company=company,
            existing_descriptions=existing_descriptions
        )
        risk_score  = scan_result['risk_score']
        risk_level  = scan_result['risk_level']
        posting_status = 'flagged' if risk_level == 'High' else 'active'

        # ── Persist to DB ──────────────────────────────────────────────
        try:
            internship = Internship(
                company_id=company.id,
                category_id=cleaned['category_id'],
                title=cleaned['title'],
                description=cleaned['description'],
                responsibilities=cleaned['responsibilities'],
                eligibility=cleaned['eligibility'],
                skills_required=cleaned['skills_required'],
                duration_weeks=cleaned['duration_weeks'],
                duration_text=cleaned['duration_text'],
                location_type=cleaned['location_type'],
                location_city=cleaned['location_city'],
                stipend_type=cleaned['stipend_type'],
                stipend_amount=cleaned['stipend_amount'],
                openings_count=cleaned['openings_count'],
                start_date=cleaned['start_date'],
                application_deadline=cleaned['application_deadline'],
                application_instructions=cleaned['application_instructions'],
                contact_email=cleaned['contact_email'],
                contact_phone=cleaned['contact_phone'],
                status=posting_status
            )
            db.session.add(internship)
            db.session.flush()

            scam_record = ScamCheck(
                internship_id=internship.id,
                risk_score=risk_score,
                risk_level=risk_level,
                triggered_rules=json.dumps(scan_result['triggered_rules']),
                summary_notes=scan_result['summary_notes'],
                disclaimer=scan_result.get('disclaimer', ScamDetector.DISCLAIMER_TEXT),
                appeal_status='none'
            )
            db.session.add(scam_record)

            if risk_level == 'High':
                for admin_user in User.query.filter_by(role='admin').all():
                    notify(
                        user_id=admin_user.id,
                        title=f"High Risk Internship Posted: {internship.title}",
                        message=f"{company.company_name} posted an internship flagged as High Risk (Score: {risk_score}/100). Review required.",
                        category="scam_alert",
                        link_url=url_for('admin.flagged_internships')
                    )

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Internship creation failed: {e}')
            flash('A database error occurred while saving the internship. Please try again.', 'danger')
            form_data = request.form.to_dict()
            return render_template('company/post_internship.html',
                                   categories=categories, company=company,
                                   form_data=form_data, is_edit=False)

        # ── Success flash ──────────────────────────────────────────────
        if risk_level == 'High':
            flash(f'Internship submitted but flagged (risk score {risk_score}/100). '
                  'An admin will review it before it goes live.', 'warning')
        elif risk_level == 'Medium':
            flash(f'Internship published with a caution notice (score {risk_score}/100) '
                  'visible to students.', 'info')
        else:
            flash('Internship published and verified successfully! '
                  'Students can now discover and apply.', 'success')

        return redirect(url_for('company.manage_internships'))

    return render_template('company/post_internship.html',
                           categories=categories, company=company,
                           form_data={}, is_edit=False)


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
        is_valid, errors, cleaned = validate_internship_form(request.form, company=company)
        if not is_valid:
            for err in errors:
                flash(err, 'danger')
            form_data = request.form.to_dict()
            return render_template('company/post_internship.html',
                                   internship=internship,
                                   categories=categories,
                                   company=company,
                                   form_data=form_data,
                                   is_edit=True)

        internship.title              = cleaned['title']
        internship.category_id        = cleaned['category_id']
        internship.description        = cleaned['description']
        internship.responsibilities   = cleaned['responsibilities']
        internship.eligibility        = cleaned['eligibility']
        internship.skills_required    = cleaned['skills_required']
        internship.duration_text      = cleaned['duration_text']
        internship.duration_weeks     = cleaned['duration_weeks']
        internship.location_type      = cleaned['location_type']
        internship.location_city      = cleaned['location_city']
        internship.stipend_type       = cleaned['stipend_type']
        internship.stipend_amount     = cleaned['stipend_amount']
        internship.openings_count     = cleaned['openings_count']
        internship.start_date         = cleaned['start_date']
        internship.application_deadline = cleaned['application_deadline']
        internship.application_instructions = cleaned['application_instructions']
        internship.contact_email      = cleaned['contact_email']
        internship.contact_phone      = cleaned['contact_phone']

        # Re-screen with ScamDetector
        existing_descriptions = [
            i.description for i in
            Internship.query.filter(
                Internship.company_id != company.id,
                Internship.id != internship.id,
                Internship.status == 'active'
            ).with_entities(Internship.description).limit(200).all()
        ]
        posting_data = {
            'title': internship.title,
            'description': internship.description,
            'responsibilities': internship.responsibilities,
            'eligibility': internship.eligibility,
            'skills_required': internship.skills_required,
            'stipend_type': internship.stipend_type,
            'stipend_amount': float(internship.stipend_amount),
            'contact_email': internship.contact_email,
            'contact_phone': internship.contact_phone,
            'application_instructions': internship.application_instructions or '',
        }

        scan = ScamDetector.evaluate_posting(
            posting_data, company=company,
            existing_descriptions=existing_descriptions
        )
        
        if not internship.scam_check:
            internship.scam_check = ScamCheck(internship_id=internship.id)

        internship.scam_check.risk_score = scan['risk_score']
        internship.scam_check.risk_level = scan['risk_level']
        internship.scam_check.triggered_rules = json.dumps(scan['triggered_rules'])
        internship.scam_check.summary_notes = scan['summary_notes']
        internship.scam_check.disclaimer = scan.get('disclaimer', ScamDetector.DISCLAIMER_TEXT)
        
        if internship.scam_check.appeal_status == 'pending':
            internship.scam_check.appeal_status = 'none'
            internship.scam_check.appeal_note = None

        if scan['risk_level'] == 'High':
            internship.status = 'flagged'
            flash(f'Update saved: Warning - high risk score ({scan["risk_score"]}/100) triggered. Held for admin review.', 'warning')
        else:
            if internship.status == 'flagged' and scan['risk_level'] in ['Low', 'Medium']:
                internship.status = 'active'
            flash('Internship updated successfully!', 'success')

        db.session.commit()
        return redirect(url_for('company.manage_internships'))

    return render_template('company/post_internship.html', internship=internship, categories=categories, company=company, is_edit=True, form_data={})


@company_bp.route('/internships/status/<int:internship_id>/<string:new_status>', methods=['POST'])
@login_required
@role_required('company')
@company_verified_required
def toggle_status(internship_id, new_status):
    company = current_user.company_profile
    internship = Internship.query.filter_by(
        id=internship_id, company_id=company.id
    ).first_or_404()

    COMPANY_ALLOWED_STATUSES = {'active', 'closed'}
    if new_status not in COMPANY_ALLOWED_STATUSES:
        abort(403)

    if internship.status in ('flagged', 'rejected') and new_status == 'active':
        flash('This listing is under administrator review and cannot be re-activated manually.', 'warning')
        return redirect(url_for('company.manage_internships'))

    internship.status = new_status
    db.session.commit()
    flash(f'Internship status changed to "{new_status}".', 'success')
    return redirect(url_for('company.manage_internships'))


@company_bp.route('/internships/appeal/<int:internship_id>', methods=['POST'])
@login_required
@role_required('company')
def appeal_scam_flag(internship_id):
    company = current_user.company_profile
    internship = Internship.query.filter_by(
        id=internship_id, company_id=company.id
    ).first_or_404()

    if internship.status not in ('flagged', 'rejected'):
        flash('Only flagged or rejected listings may be appealed.', 'warning')
        return redirect(url_for('company.manage_internships'))

    if not internship.scam_check:
        flash('No scam assessment found for this listing.', 'warning')
        return redirect(url_for('company.manage_internships'))

    if internship.scam_check.appeal_status == 'pending':
        flash('Your appeal is already under review. Please wait for the admin decision.', 'info')
        return redirect(url_for('company.manage_internships'))

    appeal_text = request.form.get('appeal_note', '').strip()
    if not appeal_text or len(appeal_text) < 30:
        flash('Please provide a detailed appeal message (minimum 30 characters).', 'danger')
        return redirect(url_for('company.manage_internships'))

    appeal_text = appeal_text[:2000]

    internship.scam_check.appeal_note = appeal_text
    internship.scam_check.appeal_submitted_at = datetime.utcnow()
    internship.scam_check.appeal_status = 'pending'

    for admin_user in User.query.filter_by(role='admin').all():
        notify(
            user_id=admin_user.id,
            title=f'Appeal Submitted: {internship.title}',
            message=(f'{company.company_name} submitted an appeal for the flagged internship '
                     f'"{internship.title}". Please review.'),
            category='scam_alert',
            link_url=url_for('admin.flagged_internships')
        )

    db.session.commit()
    flash('Your appeal has been submitted. An administrator will review it and respond.', 'success')
    return redirect(url_for('company.manage_internships'))


@company_bp.route('/internships/delete/<int:internship_id>', methods=['POST'])
@login_required
@role_required('company')
@company_verified_required
def delete_internship(internship_id):
    company = current_user.company_profile
    internship = Internship.query.filter_by(
        id=internship_id, company_id=company.id
    ).first_or_404()

    db.session.delete(internship)
    db.session.commit()
    flash('Internship listing deleted.', 'info')
    return redirect(url_for('company.manage_internships'))


@company_bp.route('/applicants')
@login_required
@role_required('company')
def applicants():
    company = current_user.company_profile
    internship_id_raw = request.args.get('internship_id')
    status_filter = request.args.get('status')

    query = Application.query.join(Internship).filter(Internship.company_id == company.id)
    selected_internship_id = None

    if internship_id_raw is not None and str(internship_id_raw).strip():
        raw_str = str(internship_id_raw).strip()
        try:
            parsed_id = int(raw_str)
            if parsed_id <= 0:
                flash('Internship ID must be a positive integer.', 'warning')
                query = query.filter(db.false())
            else:
                owned = Internship.query.filter_by(id=parsed_id, company_id=company.id).first()
                if not owned:
                    flash('Unauthorized or invalid internship selected.', 'warning')
                    query = query.filter(db.false())
                else:
                    selected_internship_id = parsed_id
                    query = query.filter(Application.internship_id == parsed_id)
        except (ValueError, TypeError):
            flash('Invalid internship ID format.', 'warning')
            query = query.filter(db.false())

    if status_filter:
        query = query.filter(Application.status == status_filter)

    applications_list = query.order_by(Application.applied_at.desc()).all()
    company_internships = company.internships.all()

    return render_template(
        'company/applicants.html',
        applications=applications_list,
        internships=company_internships,
        selected_internship=selected_internship_id,
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

        notify(
            user_id=application.student.user_id,
            title=f"Application Update: {application.internship.title}",
            message=f"Your application status at {company.company_name} has been updated to '{new_status}'.",
            category="application",
            link_url=url_for('student.applications')
        )
        db.session.commit()
        flash(f'Application status updated to {new_status} and student notified.', 'success')
    else:
        flash('Invalid status value.', 'danger')

    return redirect(request.referrer or url_for('company.applicants'))
