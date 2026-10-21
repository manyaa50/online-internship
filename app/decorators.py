"""
Hardened security decorators for SmartInternshipSystem.
"""
from functools import wraps
from flask import abort, flash, redirect, url_for, request, jsonify
from flask_login import current_user


def role_required(*allowed_roles):
    """
    Restrict access to one or more user roles.
    Checks authentication, account active status, and role membership.
    Returns HTTP 403 for API-style requests (Accept: application/json).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Must be authenticated
            if not current_user.is_authenticated:
                if _wants_json():
                    return jsonify(error='Authentication required.'), 401
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.path))

            # 2. Account must be active (not suspended)
            if not current_user.is_active:
                if _wants_json():
                    return jsonify(error='Account suspended.'), 403
                flash('Your account has been suspended by an administrator. '
                      'Contact support for assistance.', 'danger')
                return redirect(url_for('auth.logout'))

            # 3. Role must be permitted
            if current_user.role not in allowed_roles:
                if _wants_json():
                    return jsonify(error='Insufficient permissions.'), 403
                flash('Access denied: You do not have permission to access that section.',
                      'danger')
                return _role_home_redirect()

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def company_verified_required(f):
    """
    Gate for internship creation and management endpoints.
    Enforces (in order):
      1. Must be a company account.
      2. Account must be active (not suspended).
      3. Company profile must exist.
      4. Company must be admin-approved (verification_status == 'approved').
    Never trusts company_id or status from the request — reads from DB session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Re-check authentication here too (defensive depth)
        if not current_user.is_authenticated or not current_user.is_company:
            if _wants_json():
                return jsonify(error='Company account required.'), 401
            flash('Company account required to access this page.', 'danger')
            return redirect(url_for('auth.login'))

        # Suspended company — cannot post or manage listings
        if not current_user.is_active:
            if _wants_json():
                return jsonify(error='Account suspended.'), 403
            flash('Your account has been suspended. '
                  'You cannot create or manage internships at this time.', 'danger')
            return redirect(url_for('auth.logout'))

        # Must have a company profile
        company = current_user.company_profile
        if not company:
            flash('Please complete your company profile before posting internships.', 'warning')
            return redirect(url_for('company.profile'))

        # Must be admin-approved
        if not company.is_verified:
            status = company.verification_status
            if status == 'pending':
                flash('Your company is under review by an administrator. '
                      'Internship posting will be unlocked once approved.', 'info')
            elif status == 'rejected':
                flash('Your company registration was rejected. '
                      'Please review the admin feedback in your profile and resubmit.', 'danger')
            else:
                flash('Your company profile must be verified before you can post internships.', 'warning')
            if _wants_json():
                return jsonify(error='Company not verified.'), 403
            return redirect(url_for('company.dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def ownership_required(model_class, id_kwarg='internship_id', owner_field='company_id',
                        owner_getter=None):
    """
    Generic ownership decorator.
    Fetches the resource, verifies it belongs to the current user's company,
    and attaches it to `g` for the view to use.
    Returns 404 (not found) rather than 403 (forbidden) to avoid ID enumeration.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resource_id = kwargs.get(id_kwarg)
            company = current_user.company_profile

            if not company:
                abort(404)

            owner_id = owner_getter(current_user) if owner_getter else company.id
            resource = model_class.query.filter_by(
                id=resource_id,
                **{owner_field: owner_id}
            ).first_or_404()

            kwargs['_owned_resource'] = resource
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wants_json():
    """True when the client signals it expects a JSON response."""
    return request.accept_mimetypes.best == 'application/json'


def _role_home_redirect():
    """Redirect user to their appropriate home page after an access denial."""
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    if current_user.is_company:
        return redirect(url_for('company.dashboard'))
    if current_user.is_student:
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('index'))
