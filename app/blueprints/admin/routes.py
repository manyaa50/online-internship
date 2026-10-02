from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (
    db, User, Admin, StudentProfile, Company, CompanyVerification,
    Internship, InternshipCategory, ScamCheck, ScamReport, Notification
)
from app.decorators import role_required

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

        notif = Notification(
            user_id=company.user_id,
            title="🎉 Company Verification Approved!",
            message="Your company profile has been verified by the administrator. You may now post internships.",
            category="verification",
            link_url=url_for('company.create_internship')
        )
        db.session.add(notif)
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

        notif = Notification(
            user_id=company.user_id,
            title="Company Verification Rejected",
            message=f"Your verification was not approved. Reason: {reason or 'Invalid documents'}. You can update your profile and resubmit.",
            category="verification",
            link_url=url_for('company.profile')
        )
        db.session.add(notif)
        flash(f'Company "{company.company_name}" has been marked as rejected.', 'warning')

    db.session.commit()
    return redirect(url_for('admin.verifications'))


@admin_bp.route('/flagged-internships')
@login_required
@role_required('admin')
def flagged_internships():
    flagged_list = (
        Internship.query
        .join(ScamCheck)
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

    if action == 'approve':
        internship.status = 'active'
        if scam_check:
            scam_check.admin_verdict = 'approved'
            scam_check.is_reviewed_by_admin = True
            scam_check.admin_notes = notes or "Admin manually reviewed and approved listing for public visibility."

        notif = Notification(
            user_id=internship.company.user_id,
            title="Internship Posting Approved",
            message=f"Your internship '{internship.title}' has been reviewed and approved by admin.",
            category="admin",
            link_url=url_for('internships.detail', internship_id=internship.id)
        )
        db.session.add(notif)
        flash(f'Internship "{internship.title}" approved and published.', 'success')

    elif action == 'reject':
        internship.status = 'rejected'
        if scam_check:
            scam_check.admin_verdict = 'rejected'
            scam_check.is_reviewed_by_admin = True
            scam_check.admin_notes = notes or "Rejected due to violation of platform safety guidelines."

        notif = Notification(
            user_id=internship.company.user_id,
            title="Internship Posting Rejected",
            message=f"Your internship '{internship.title}' was rejected by the admin due to high scam risk score and policy violation.",
            category="admin",
            link_url=url_for('company.manage_internships')
        )
        db.session.add(notif)
        flash(f'Internship "{internship.title}" has been rejected and delisted.', 'danger')

    db.session.commit()
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

    user.is_active = not user.is_active
    status_str = "unblocked" if user.is_active else "blocked"
    db.session.commit()
    flash(f'User {user.email} has been {status_str}.', 'info')
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

    report.status = status
    report.admin_resolution = resolution
    report.resolved_at = datetime.now(timezone.utc)

    # If action is also to delist the reported internship
    if request.form.get('delist_internship') and report.internship:
        report.internship.status = 'rejected'
        flash(f'Internship "{report.internship.title}" has been delisted.', 'warning')

    # Notify student who reported it
    notif = Notification(
        user_id=report.student.user_id,
        title="Scam Report Update",
        message=f"Your report regarding {report.internship.title if report.internship else 'a company'} was reviewed. Resolution: {resolution}",
        category="report"
    )
    db.session.add(notif)
    db.session.commit()
    flash('Report updated and reporter notified.', 'success')
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
