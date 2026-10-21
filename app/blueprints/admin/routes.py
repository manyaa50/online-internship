import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from app.models import (
    db, User, StudentProfile, Company, CompanyVerification,
    Internship, InternshipCategory, ScamCheck, ScamReport, Application
)
from app.decorators import role_required
from app.services.notifications import notify

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    total_students = StudentProfile.query.count()
    total_companies = Company.query.count()
    pending_verifications = Company.query.filter_by(verification_status='pending').count()
    total_postings = Internship.query.count()
    flagged_postings = Internship.query.filter_by(status='flagged').count()
    open_reports = ScamReport.query.filter_by(status='open').count()

    recent_flagged = (
        Internship.query.filter_by(status='flagged')
        .order_by(Internship.created_at.desc())
        .limit(5)
        .all()
    )
    recent_verifications = (
        Company.query.filter_by(verification_status='pending')
        .order_by(Company.created_at.desc())
        .limit(5)
        .all()
    )
    recent_reports = (
        ScamReport.query.filter_by(status='open')
        .order_by(ScamReport.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_companies=total_companies,
        pending_verifications=pending_verifications,
        total_postings=total_postings,
        flagged_postings=flagged_postings,
        open_reports=open_reports,
        recent_flagged=recent_flagged,
        recent_verifications=recent_verifications,
        recent_reports=recent_reports
    )


@admin_bp.route('/verifications')
@login_required
@role_required('admin')
def verifications():
    status_filter = request.args.get('status', 'pending')
    query = Company.query
    if status_filter != 'all':
        query = query.filter_by(verification_status=status_filter)

    companies_list = query.order_by(Company.created_at.desc()).all()
    return render_template('admin/verifications.html', companies=companies_list, current_status=status_filter)


@admin_bp.route('/verifications/<int:company_id>/<string:action>', methods=['POST'])
@login_required
@role_required('admin')
def verify_company(company_id, action):
    company = Company.query.get_or_404(company_id)
    notes = request.form.get('review_notes', '').strip()
    reason = request.form.get('rejection_reason', '').strip()

    admin_profile = current_user.admin_profile
    admin_id = admin_profile.id if admin_profile else None

    try:
        if action == 'approve':
            company.verification_status = 'approved'
            verif_log = CompanyVerification(
                company_id=company.id,
                admin_id=admin_id,
                status='approved',
                review_notes=notes or "Company documents and registration verified successfully.",
                reviewed_at=datetime.now(timezone.utc)
            )
            db.session.add(verif_log)

            notify(
                user_id=company.user_id,
                title="Company Verification Approved",
                message="Your company profile has been verified by the administrator. You may now post internships.",
                category="verification",
                link_url=url_for('company.create_internship')
            )
            flash(f'Company "{company.company_name}" has been approved.', 'success')

        elif action == 'reject':
            company.verification_status = 'rejected'
            verif_log = CompanyVerification(
                company_id=company.id,
                admin_id=admin_id,
                status='rejected',
                review_notes=notes,
                rejection_reason=reason or "Company registration or documentation could not be verified.",
                reviewed_at=datetime.now(timezone.utc)
            )
            db.session.add(verif_log)

            notify(
                user_id=company.user_id,
                title="Company Verification Rejected",
                message=f"Your verification was not approved. Reason: {reason or 'Invalid documents'}. You can update your profile and resubmit.",
                category="verification",
                link_url=url_for('company.profile')
            )

            # Moderation cascade: set company's active internships to 'closed'
            active_postings = Internship.query.filter_by(company_id=company.id, status='active').all()
            for posting in active_postings:
                posting.status = 'closed'

            if active_postings:
                posting_ids = [p.id for p in active_postings]
                affected_apps = Application.query.filter(Application.internship_id.in_(posting_ids)).all()
                notified_pairs = set()
                for app_item in affected_apps:
                    student_user_id = app_item.student.user_id
                    pair_key = (student_user_id, app_item.internship_id)
                    if pair_key not in notified_pairs:
                        notified_pairs.add(pair_key)
                        notify(
                            user_id=student_user_id,
                            title="Internship Posting Closed",
                            message=f"The internship '{app_item.internship.title}' at '{company.company_name}' has been closed because the company verification was revoked.",
                            category="admin"
                        )

            flash(f'Company "{company.company_name}" has been marked as rejected.', 'warning')

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing company verification: {str(e)}', 'danger')

    return redirect(url_for('admin.verifications'))


@admin_bp.route('/verifications/document/<int:company_id>')
@login_required
@role_required('admin')
def download_verification_document(company_id):
    company = Company.query.get_or_404(company_id)
    if not company.verification_document:
        flash('No verification document has been uploaded by this company.', 'warning')
        return redirect(url_for('admin.verifications'))

    docs_folder = current_app.config['DOCS_FOLDER']
    file_path = os.path.join(docs_folder, company.verification_document)
    if not os.path.isfile(file_path):
        flash('Verification document file not found on server.', 'danger')
        return redirect(url_for('admin.verifications'))

    return send_from_directory(
        docs_folder,
        company.verification_document,
        as_attachment=False
    )


@admin_bp.route('/flagged-internships')
@login_required
@role_required('admin')
def flagged_internships():
    flagged_list = (
        Internship.query
        .join(ScamCheck)
        .filter(Internship.status.in_(['flagged', 'rejected']))
        .order_by(ScamCheck.risk_score.desc(), Internship.created_at.desc())
        .all()
    )
    return render_template('admin/flagged_internships.html', internships=flagged_list)


@admin_bp.route('/flagged-internships/<int:internship_id>/<string:action>', methods=['POST'])
@login_required
@role_required('admin')
def review_flagged(internship_id, action):
    internship = Internship.query.get_or_404(internship_id)
    scam_check = internship.scam_check
    notes = request.form.get('admin_notes', '').strip()

    try:
        if action == 'approve':
            internship.status = 'active'
            if scam_check:
                scam_check.admin_verdict = 'approved'
                scam_check.is_reviewed_by_admin = True
                scam_check.admin_notes = notes or "Admin manually reviewed and approved listing for public visibility."
                if scam_check.appeal_status == 'pending':
                    scam_check.appeal_status = 'reviewed'

            notify(
                user_id=internship.company.user_id,
                title="Internship Posting Approved",
                message=f"Your internship '{internship.title}' has been reviewed and approved by admin.",
                category="admin",
                link_url=url_for('internships.detail', internship_id=internship.id)
            )
            flash(f'Internship "{internship.title}" approved and published.', 'success')

        elif action == 'reject':
            internship.status = 'rejected'
            if scam_check:
                scam_check.admin_verdict = 'rejected'
                scam_check.is_reviewed_by_admin = True
                scam_check.admin_notes = notes or "Rejected due to violation of platform safety guidelines."
                if scam_check.appeal_status == 'pending':
                    scam_check.appeal_status = 'reviewed'

            notify(
                user_id=internship.company.user_id,
                title="Internship Posting Rejected",
                message=f"Your internship '{internship.title}' was rejected by the admin due to high scam risk score and policy violation.",
                category="admin",
                link_url=url_for('company.manage_internships')
            )

            # Notify students who applied to this posting that it has been delisted
            for app_item in internship.applications:
                notify(
                    user_id=app_item.student.user_id,
                    title="Internship Posting Delisted",
                    message=f"The internship posting '{internship.title}' has been removed by platform administrators.",
                    category="admin"
                )

            flash(f'Internship "{internship.title}" has been rejected and delisted.', 'danger')

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing flagged internship: {str(e)}', 'danger')

    return redirect(url_for('admin.flagged_internships'))


@admin_bp.route('/appeals/<int:internship_id>/<string:action>', methods=['POST'])
@login_required
@role_required('admin')
def review_appeal(internship_id, action):
    if action not in ('approve', 'reject'):
        flash('Invalid appeal action specified.', 'danger')
        return redirect(url_for('admin.flagged_internships'))

    internship = Internship.query.get_or_404(internship_id)
    scam_check = internship.scam_check

    if not scam_check or scam_check.appeal_status != 'pending':
        flash('This appeal is not pending or has already been reviewed.', 'warning')
        return redirect(url_for('admin.flagged_internships'))

    notes = request.form.get('admin_notes', '').strip()

    try:
        scam_check.appeal_status = 'reviewed'
        scam_check.is_reviewed_by_admin = True
        scam_check.updated_at = datetime.now(timezone.utc)

        if action == 'approve':
            internship.status = 'active'
            scam_check.admin_verdict = 'approved'
            scam_check.admin_notes = notes or "Appeal reviewed and approved by administrator."

            notify(
                user_id=internship.company.user_id,
                title="Appeal Approved - Internship Restored",
                message=f"Your appeal for '{internship.title}' has been approved by admin. The listing is now active.",
                category="admin",
                link_url=url_for('internships.detail', internship_id=internship.id)
            )
            flash(f'Appeal for "{internship.title}" approved. Listing is now active.', 'success')

        elif action == 'reject':
            internship.status = 'rejected'
            scam_check.admin_verdict = 'rejected'
            scam_check.admin_notes = notes or "Appeal reviewed and rejected by administrator."

            notify(
                user_id=internship.company.user_id,
                title="Appeal Rejected",
                message=f"Your appeal for '{internship.title}' was reviewed and rejected. The listing remains delisted.",
                category="admin",
                link_url=url_for('company.manage_internships')
            )

            # Notify students who applied to this posting that it has been delisted
            for app_item in internship.applications:
                notify(
                    user_id=app_item.student.user_id,
                    title="Internship Posting Delisted",
                    message=f"The internship posting '{internship.title}' has been delisted following administrative appeal review.",
                    category="admin"
                )
            flash(f'Appeal for "{internship.title}" has been rejected.', 'warning')

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Database error processing appeal: {str(e)}', 'danger')

    return redirect(url_for('admin.flagged_internships'))


@admin_bp.route('/companies')
@login_required
@role_required('admin')
def companies():
    all_companies = Company.query.order_by(Company.created_at.desc()).all()
    return render_template('admin/companies.html', companies=all_companies)


@admin_bp.route('/students')
@login_required
@role_required('admin')
def students():
    all_students = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()
    return render_template('admin/students.html', students=all_students)


@admin_bp.route('/user/toggle-block/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user_block(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot block your own administrator account.', 'danger')
        return redirect(request.referrer or url_for('admin.dashboard'))

    try:
        user.is_active = not user.is_active
        status_str = "unblocked" if user.is_active else "blocked"

        # If user is a company and is being blocked, cascade moderation to postings
        if not user.is_active and user.company_profile:
            company = user.company_profile
            active_postings = Internship.query.filter_by(company_id=company.id, status='active').all()
            for posting in active_postings:
                posting.status = 'closed'

            if active_postings:
                posting_ids = [p.id for p in active_postings]
                affected_apps = Application.query.filter(Application.internship_id.in_(posting_ids)).all()
                notified_pairs = set()
                for app_item in affected_apps:
                    student_user_id = app_item.student.user_id
                    pair_key = (student_user_id, app_item.internship_id)
                    if pair_key not in notified_pairs:
                        notified_pairs.add(pair_key)
                        notify(
                            user_id=student_user_id,
                            title="Internship Posting Closed",
                            message=f"The internship '{app_item.internship.title}' at '{company.company_name}' has been closed because the employer account was suspended.",
                            category="admin"
                        )

        db.session.commit()
        flash(f'User {user.email} has been {status_str}.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred updating user: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('admin.dashboard'))


@admin_bp.route('/reports')
@login_required
@role_required('admin')
def reports():
    status_filter = request.args.get('status', 'all')
    query = ScamReport.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    all_reports = query.order_by(ScamReport.created_at.desc()).all()
    return render_template('admin/reports.html', reports=all_reports, current_status=status_filter)


@admin_bp.route('/reports/resolve/<int:report_id>', methods=['POST'])
@login_required
@role_required('admin')
def resolve_report(report_id):
    report = ScamReport.query.get_or_404(report_id)
    resolution = request.form.get('resolution', '').strip()
    status = request.form.get('status', 'resolved')

    try:
        report.status = status
        report.admin_resolution = resolution
        report.resolved_at = datetime.now(timezone.utc)

        # If action is also to delist the reported internship
        if request.form.get('delist_internship') and report.internship:
            report.internship.status = 'rejected'
            for app_item in report.internship.applications:
                notify(
                    user_id=app_item.student.user_id,
                    title="Internship Posting Delisted",
                    message=f"The internship posting '{report.internship.title}' was delisted after an investigation.",
                    category="admin"
                )
            flash(f'Internship "{report.internship.title}" has been delisted.', 'warning')

        # Notify student who reported it
        notify(
            user_id=report.student.user_id,
            title="Scam Report Update",
            message=f"Your report regarding {report.internship.title if report.internship else 'a company'} was reviewed. Resolution: {resolution}",
            category="report"
        )
        db.session.commit()
        flash('Report updated and reporter notified.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error resolving report: {str(e)}', 'danger')

    return redirect(url_for('admin.reports'))


@admin_bp.route('/categories', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        icon_class = request.form.get('icon_class', 'bi bi-briefcase').strip()

        if not name:
            flash('Category name is required.', 'warning')
        else:
            existing = InternshipCategory.query.filter_by(name=name).first()
            if existing:
                flash('Category with this name already exists.', 'warning')
            else:
                cat = InternshipCategory(name=name, description=description, icon_class=icon_class)
                db.session.add(cat)
                db.session.commit()
                flash('Category added successfully.', 'success')

        return redirect(url_for('admin.categories'))

    all_categories = InternshipCategory.query.order_by(InternshipCategory.name.asc()).all()
    return render_template('admin/categories.html', categories=all_categories)


@admin_bp.route('/system-info')
@login_required
@role_required('admin')
def system_info():
    error_message = None
    counts = {
        'total_users': 0,
        'total_students': 0,
        'total_companies': 0,
        'total_internships': 0,
        'total_applications': 0,
        'total_reports': 0,
    }
    risk_counts = {'Low': 0, 'Medium': 0, 'High': 0, 'Unassessed': 0}
    report_status_counts = {'open': 0, 'investigating': 0, 'resolved': 0, 'dismissed': 0}
    recent_admin_actions = []

    try:
        # Core Model Totals
        counts['total_users'] = User.query.count()
        counts['total_students'] = StudentProfile.query.count()
        counts['total_companies'] = Company.query.count()
        counts['total_internships'] = Internship.query.count()
        counts['total_applications'] = Application.query.count()
        counts['total_reports'] = ScamReport.query.count()

        # Internship counts by risk level
        for level in ['Low', 'Medium', 'High']:
            risk_counts[level] = ScamCheck.query.filter_by(risk_level=level).count()
        assessed_total = sum(risk_counts[lvl] for lvl in ['Low', 'Medium', 'High'])
        risk_counts['Unassessed'] = max(0, counts['total_internships'] - assessed_total)

        # Report counts by status
        for status_val in ['open', 'investigating', 'resolved', 'dismissed']:
            report_status_counts[status_val] = ScamReport.query.filter_by(status=status_val).count()

        # 10 most recent admin actions synthesized from existing audit records
        actions_list = []

        verifications = (
            CompanyVerification.query
            .filter(CompanyVerification.reviewed_at.isnot(None))
            .order_by(CompanyVerification.reviewed_at.desc())
            .limit(10)
            .all()
        )
        for v in verifications:
            company_name = v.company.company_name if v.company else "Unknown Company"
            actions_list.append({
                'action_type': 'Company Verification',
                'target': f"Company: {company_name}",
                'outcome': v.status.capitalize(),
                'details': v.review_notes or v.rejection_reason or 'No additional notes',
                'timestamp': v.reviewed_at,
                'badge_class': 'success' if v.status == 'approved' else 'danger'
            })

        resolved_reports = (
            ScamReport.query
            .filter(ScamReport.resolved_at.isnot(None))
            .order_by(ScamReport.resolved_at.desc())
            .limit(10)
            .all()
        )
        for r in resolved_reports:
            target_str = r.internship.title if r.internship else (r.company.company_name if r.company else "Report")
            actions_list.append({
                'action_type': 'Scam Report Resolution',
                'target': f"Report #{r.id} ({target_str})",
                'outcome': r.status.capitalize(),
                'details': r.admin_resolution or 'Resolved by admin',
                'timestamp': r.resolved_at,
                'badge_class': 'info' if r.status == 'resolved' else 'secondary'
            })

        reviewed_scams = (
            ScamCheck.query
            .filter(ScamCheck.is_reviewed_by_admin == True)
            .order_by(ScamCheck.updated_at.desc())
            .limit(10)
            .all()
        )
        for s in reviewed_scams:
            title = s.internship.title if s.internship else "Unknown Internship"
            outcome_str = s.admin_verdict.capitalize() if s.admin_verdict else "Reviewed"
            actions_list.append({
                'action_type': 'Scam Check Review / Appeal',
                'target': f"Internship: {title}",
                'outcome': outcome_str,
                'details': s.admin_notes or (f"Appeal Status: {s.appeal_status}"),
                'timestamp': s.updated_at,
                'badge_class': 'success' if s.admin_verdict == 'approved' else 'warning'
            })

        actions_list.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)
        recent_admin_actions = actions_list[:10]

    except Exception as e:
        error_message = f"Error retrieving system information telemetry: {str(e)}"

    return render_template(
        'admin/system_info.html',
        counts=counts,
        risk_counts=risk_counts,
        report_status_counts=report_status_counts,
        recent_admin_actions=recent_admin_actions,
        error_message=error_message
    )
