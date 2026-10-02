from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*allowed_roles):
    """
    Decorator to restrict view access to specific user roles.
    Example: @role_required('admin') or @role_required('student', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to view this page.', 'warning')
                return redirect(url_for('auth.login'))

            if not current_user.is_active:
                flash('Your account has been deactivated or blocked by an administrator.', 'danger')
                return redirect(url_for('auth.logout'))

            if current_user.role not in allowed_roles:
                flash('Access denied: You do not have permissions to access that section.', 'danger')
                if current_user.is_admin:
                    return redirect(url_for('admin.dashboard'))
                elif current_user.is_company:
                    return redirect(url_for('company.dashboard'))
                elif current_user.is_student:
                    return redirect(url_for('student.dashboard'))
                return redirect(url_for('index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def company_verified_required(f):
    """
    Decorator to ensure a company is approved by admin before posting/managing internships.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_company:
            flash('Company access required.', 'danger')
            return redirect(url_for('auth.login'))

        company = current_user.company_profile
        if not company or not company.is_verified:
            status = company.verification_status if company else 'unregistered'
            if status == 'pending':
                flash('Your company verification is under review by the administrator. Posting internships will be unlocked once approved.', 'info')
            elif status == 'rejected':
                flash('Your company registration was rejected. Please review feedback in your profile.', 'danger')
            else:
                flash('Please complete your company profile for verification.', 'warning')
            return redirect(url_for('company.dashboard'))

        return f(*args, **kwargs)
    return decorated_function
