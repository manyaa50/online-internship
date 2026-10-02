from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, ScamReport, Internship, Company, Notification, User
from app.decorators import role_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/submit', methods=['GET', 'POST'])
@login_required
@role_required('student')
def submit_report():
    internship_id = request.args.get('internship_id', type=int)
    company_id = request.args.get('company_id', type=int)

    internship = Internship.query.get(internship_id) if internship_id else None
    company = Company.query.get(company_id) if company_id else (internship.company if internship else None)

    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        description = request.form.get('description', '').strip()
        evidence_link = request.form.get('evidence_link', '').strip()
        intern_id = request.form.get('internship_id', type=int)
        comp_id = request.form.get('company_id', type=int)

        if not reason or not description:
            flash('Please select a reason and provide a description of the issue.', 'warning')
            return render_template('reports/submit.html', internship=internship, company=company)

        student = current_user.student_profile
        report = ScamReport(
            reported_by_student_id=student.id,
            internship_id=intern_id if intern_id else None,
            company_id=comp_id if comp_id else (internship.company_id if internship else None),
            reason=reason,
            description=description,
            evidence_link=evidence_link,
            status='open'
        )
        db.session.add(report)

        # Notify Admins about new report
        admins = User.query.filter_by(role='admin').all()
        target_name = internship.title if internship else (company.company_name if company else 'Entity')
        for admin_user in admins:
            notif = Notification(
                user_id=admin_user.id,
                title="🚨 New Scam Report Filed",
                message=f"Student {student.full_name} reported '{target_name}' for '{reason}'.",
                category="report",
                link_url=url_for('admin.reports')
            )
            db.session.add(notif)

        db.session.commit()
        flash('Thank you for helping keep our platform safe. Your report has been submitted to the admin team.', 'success')
        
        if internship:
            return redirect(url_for('internships.detail', internship_id=internship.id))
        return redirect(url_for('student.dashboard'))

    return render_template('reports/submit.html', internship=internship, company=company)


@reports_bp.route('/my-reports')
@login_required
@role_required('student')
def my_reports():
    student = current_user.student_profile
    reports_list = student.reports.order_by(ScamReport.created_at.desc()).all()
    return render_template('reports/my_reports.html', reports=reports_list)
