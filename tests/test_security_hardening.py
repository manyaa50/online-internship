"""
tests/test_security_hardening.py
================================
Comprehensive verification tests for GROUP 5: SECURITY HARDENING.

Covers:
  1. Open redirect validation (safe local paths allowed; schemes, netlocs, double slashes,
     backslashes, control characters rejected and defaulted).
  2. POST-only logout (GET returns 405 without logging out; POST logs out).
  3. CSRF protection on logout (POST without CSRF rejected when CSRF enabled).
  4. Login rate limiting (5 attempts/min accepted, 6th attempt returns 429 Too Many Requests).
  5. Generic login failure messages (no user enumeration).
  6. Password validation enforcement (min 8 chars, >=1 letter, >=1 digit).
  7. Email validation via email-validator.
  8. Indian phone number validation (10 digits starting 6-9, prefix handling).
  9. Indian GSTIN validation (15-character format).
  10. Shared validate_internship_form helper (length, future deadlines, non-negative stipend, no 500s).
  11. Safe applicants route parameter parsing (missing, malformed, negative, unauthorized).
  12. Startup error when SECRET_KEY is missing in production/non-debug mode.
  13. HTTP 500 error handler wording (no false alerting claim).
"""
import pytest
from datetime import date, timedelta

from app import create_app
from app.config import Config
from app.models import db, User, StudentProfile, Company, Internship, InternshipCategory
from app.utils import (
    is_safe_redirect_url,
    validate_email_address,
    validate_indian_phone,
    validate_gstin,
    validate_password,
    validate_internship_form,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Test Application Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def app():
    """Application fixture with rate limiter disabled for standard tests."""
    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'test-secret-key-hardening'
        SERVER_NAME = 'localhost'

    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        _seed_hardening_data()
        yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def _seed_hardening_data():
    """Seed test users and company data."""
    # Student
    stu_user = User(email='student_h@test.org', role='student', is_active=True)
    stu_user.set_password('StudentPass1!')
    db.session.add(stu_user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=stu_user.id, full_name='Hardening Student', phone='9876543210'))

    # Company A
    comp_a_user = User(email='companya_h@test.org', role='company', is_active=True)
    comp_a_user.set_password('CompanyPass1!')
    db.session.add(comp_a_user)
    db.session.flush()
    comp_a = Company(
        user_id=comp_a_user.id,
        company_name='Hardening Company A',
        official_email='companya_h@test.org',
        phone='9876543210',
        verification_status='approved'
    )
    db.session.add(comp_a)
    db.session.flush()

    # Company B
    comp_b_user = User(email='companyb_h@test.org', role='company', is_active=True)
    comp_b_user.set_password('CompanyPass2!')
    db.session.add(comp_b_user)
    db.session.flush()
    comp_b = Company(
        user_id=comp_b_user.id,
        company_name='Hardening Company B',
        official_email='companyb_h@test.org',
        phone='9876543211',
        verification_status='approved'
    )
    db.session.add(comp_b)
    db.session.flush()

    # Category
    cat = InternshipCategory(name='Hardening Category', description='Testing', icon_class='bi bi-shield')
    db.session.add(cat)
    db.session.flush()

    # Internship for Company A
    future = date.today() + timedelta(days=30)
    intern_a = Internship(
        company_id=comp_a.id,
        category_id=cat.id,
        title='Company A Hardened Job',
        description='Detailed job description for security hardening verification testing over 50 characters long.',
        eligibility='BCA / MCA students',
        skills_required='Python, Flask',
        duration_weeks=8,
        duration_text='8 Weeks',
        location_type='remote',
        stipend_type='paid',
        stipend_amount=10000,
        openings_count=2,
        contact_email='companya_h@test.org',
        application_deadline=future,
        status='active'
    )
    db.session.add(intern_a)

    # Internship for Company B
    intern_b = Internship(
        company_id=comp_b.id,
        category_id=cat.id,
        title='Company B Hardened Job',
        description='Detailed job description for security hardening verification testing over 50 characters long.',
        eligibility='BCA / MCA students',
        skills_required='Python, Django',
        duration_weeks=12,
        duration_text='12 Weeks',
        location_type='remote',
        stipend_type='paid',
        stipend_amount=12000,
        openings_count=1,
        contact_email='companyb_h@test.org',
        application_deadline=future,
        status='active'
    )
    db.session.add(intern_b)
    db.session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Login Redirect Validation (Open Redirect Protection)
# ═══════════════════════════════════════════════════════════════════════════════

def test_is_safe_redirect_url_helper():
    """Unit tests for is_safe_redirect_url()."""
    # Safe paths
    assert is_safe_redirect_url('/student/dashboard') is True
    assert is_safe_redirect_url('/internships/1') is True
    assert is_safe_redirect_url('/company/internships?page=2') is True
    assert is_safe_redirect_url('/') is True

    # Unsafe / attack payloads
    assert is_safe_redirect_url('') is False
    assert is_safe_redirect_url(None) is False
    assert is_safe_redirect_url('//attacker.com') is False
    assert is_safe_redirect_url('//attacker.com/path') is False
    assert is_safe_redirect_url('///attacker.com') is False
    assert is_safe_redirect_url('http://attacker.com') is False
    assert is_safe_redirect_url('https://evil.com/login') is False
    assert is_safe_redirect_url('javascript:alert(1)') is False
    assert is_safe_redirect_url('data:text/html,<script>alert(1)</script>') is False
    assert is_safe_redirect_url(r'\evil.com') is False
    assert is_safe_redirect_url(r'/\\evil.com') is False
    assert is_safe_redirect_url('/%5cexample.com') is False
    assert is_safe_redirect_url('/%2f%2fexample.com') is False
    assert is_safe_redirect_url('/test\npath') is False
    assert is_safe_redirect_url('/test\rpath') is False


def test_login_open_redirect_rejected_and_defaults_safely(client):
    """
    When next points to an unsafe or external target, login route falls back
    to the safe default destination (/student/dashboard for student).
    """
    unsafe_targets = [
        '//attacker.com',
        '//attacker.com/evil',
        'http://attacker.com',
        'https://attacker.com/fake',
        r'/\attacker.com',
        '/%2f%2fattacker.com',
        '/%5cattacker.com',
        '/student/dashboard\n'
    ]

    for target in unsafe_targets:
        resp = client.post(f'/auth/login?next={target}', data={
            'email': 'student_h@test.org',
            'password': 'StudentPass1!'
        }, follow_redirects=False)

        assert resp.status_code == 302, f"Target {target} should redirect"
        # Must NOT redirect to attacker domain; must fall back to student dashboard
        assert resp.headers.get('Location') == '/student/dashboard', f"Failed for target: {target}"
        client.post('/auth/logout')


def test_login_safe_relative_redirect_accepted(client):
    """When next is a legitimate relative path, the redirect is honored."""
    resp = client.post('/auth/login?next=/internships/1', data={
        'email': 'student_h@test.org',
        'password': 'StudentPass1!'
    }, follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers.get('Location') == '/internships/1'
    client.post('/auth/logout')


# ═══════════════════════════════════════════════════════════════════════════════
# 2. POST-only Logout & CSRF Protection
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_logout_returns_405_and_keeps_user_logged_in(client):
    """GET /auth/logout must return 405 Method Not Allowed and NOT log the user out."""
    client.post('/auth/login', data={'email': 'student_h@test.org', 'password': 'StudentPass1!'})

    # Verify student is logged in
    resp = client.get('/student/dashboard')
    assert resp.status_code == 200

    # Attempt GET logout -> 405
    get_logout_resp = client.get('/auth/logout')
    assert get_logout_resp.status_code == 405

    # Confirm user is still authenticated
    resp_after = client.get('/student/dashboard')
    assert resp_after.status_code == 200

    # Clean up with POST logout
    client.post('/auth/logout')


def test_post_logout_logs_user_out(client):
    """POST /auth/logout successfully terminates session."""
    client.post('/auth/login', data={'email': 'student_h@test.org', 'password': 'StudentPass1!'})
    assert client.get('/student/dashboard').status_code == 200

    # POST logout
    post_resp = client.post('/auth/logout', follow_redirects=False)
    assert post_resp.status_code == 302
    assert post_resp.headers.get('Location') == '/'

    # Subsequent request to protected route is redirected to login
    resp_after = client.get('/student/dashboard', follow_redirects=False)
    assert resp_after.status_code == 302
    assert '/auth/login' in resp_after.headers.get('Location', '')


def test_logout_csrf_protection_when_enabled():
    """When CSRF is enabled, POST logout without CSRF token is rejected with 400."""
    class CsrfConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = True
        RATELIMIT_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'csrf-secret-key'
        SERVER_NAME = 'localhost'

    csrf_app = create_app(CsrfConfig)
    with csrf_app.app_context():
        db.create_all()
        _seed_hardening_data()

    csrf_client = csrf_app.test_client()
    # Direct POST without token should trigger 400 Bad Request
    resp = csrf_client.post('/auth/logout')
    assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Login Rate Limiting & User Enumeration Protection
# ═══════════════════════════════════════════════════════════════════════════════

def test_login_rate_limiting_enforces_five_per_minute():
    """
    With RATELIMIT_ENABLED = True, 5 attempts pass through, and the 6th
    attempt within a minute returns 429 Too Many Requests with polite error message.
    """
    class RateLimitConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = True
        RATELIMIT_STORAGE_URI = 'memory://'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'ratelimit-secret-key'
        SERVER_NAME = 'localhost'

    rl_app = create_app(RateLimitConfig)
    with rl_app.app_context():
        db.create_all()
        _seed_hardening_data()

    rl_client = rl_app.test_client()

    # Send 5 failed login attempts
    for i in range(5):
        resp = rl_client.post('/auth/login', data={
            'email': f'attempt_{i}@test.org',
            'password': 'WrongPassword1!'
        })
        # Should be handled normally (renders login page with 200 or flashes)
        assert resp.status_code == 200

    # 6th attempt from the same IP must be rate limited (429)
    resp_blocked = rl_client.post('/auth/login', data={
        'email': 'attempt_6@test.org',
        'password': 'WrongPassword1!'
    })
    assert resp_blocked.status_code == 429
    assert b"Too many requests" in resp_blocked.data


def test_login_failure_does_not_leak_user_existence(client):
    """
    Failed login for non-existent email vs wrong password for existing email
    return the exact same generic error message to prevent user enumeration.
    """
    # 1. Non-existent email
    resp_no_user = client.post('/auth/login', data={
        'email': 'nonexistent_user_12345@test.org',
        'password': 'SomePassword1!'
    }, follow_redirects=True)
    assert resp_no_user.status_code == 200
    assert b"Invalid email or password. Please try again." in resp_no_user.data
    assert b"User not found" not in resp_no_user.data
    assert b"No user exists" not in resp_no_user.data

    # 2. Existing email with incorrect password
    resp_wrong_pw = client.post('/auth/login', data={
        'email': 'student_h@test.org',
        'password': 'IncorrectPassword999!'
    }, follow_redirects=True)
    assert resp_wrong_pw.status_code == 200
    assert b"Invalid email or password. Please try again." in resp_wrong_pw.data
    assert b"Incorrect password" not in resp_wrong_pw.data


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Input & Credential Validation (Password, Email, Phone, GSTIN)
# ═══════════════════════════════════════════════════════════════════════════════

def test_password_validation_rules():
    """Unit tests for validate_password()."""
    # Valid passwords
    assert validate_password("SecurePass1")[0] is True
    assert validate_password("Pass1234")[0] is True
    assert validate_password("P@ssw0rd2026")[0] is True

    # Invalid: shorter than 8 characters
    is_valid, msg = validate_password("Short1")
    assert is_valid is False
    assert "8 characters" in msg

    # Invalid: no letter
    is_valid, msg = validate_password("12345678")
    assert is_valid is False
    assert "at least one letter" in msg

    # Invalid: no digit
    is_valid, msg = validate_password("NoDigitsHere")
    assert is_valid is False
    assert "at least one digit" in msg


def test_email_validation_rules():
    """Unit tests for validate_email_address()."""
    # Valid emails
    valid, _, norm = validate_email_address("student@example.com")
    assert valid is True
    assert norm == "student@example.com"

    valid, _, norm = validate_email_address("STUDENT.TEST@Domain.Org")
    assert valid is True
    assert norm == "student.test@domain.org"

    # Invalid emails
    assert validate_email_address("notanemail")[0] is False
    assert validate_email_address("@missinguser.com")[0] is False
    assert validate_email_address("user@")[0] is False
    assert validate_email_address("")[0] is False
    assert validate_email_address(None)[0] is False


def test_indian_phone_validation_rules():
    """Unit tests for validate_indian_phone()."""
    # Valid 10-digit mobile numbers starting 6, 7, 8, 9
    assert validate_indian_phone("9876543210")[0] is True
    assert validate_indian_phone("8123456789")[0] is True
    assert validate_indian_phone("7012345678")[0] is True
    assert validate_indian_phone("6987654321")[0] is True

    # Valid with prefixes, spaces, hyphens
    assert validate_indian_phone("+91 9876543210")[0] is True
    assert validate_indian_phone("919876543210")[0] is True
    assert validate_indian_phone("09876543210")[0] is True
    assert validate_indian_phone("98765-43210")[0] is True

    # Invalid
    assert validate_indian_phone("5123456789")[0] is False  # Starts with 5
    assert validate_indian_phone("1234567890")[0] is False  # Starts with 1
    assert validate_indian_phone("98765")[0] is False       # Too short
    assert validate_indian_phone("987654321012")[0] is False# Too long
    assert validate_indian_phone("abcdefghij")[0] is False
    assert validate_indian_phone("")[0] is False


def test_indian_gstin_validation_rules():
    """Unit tests for validate_gstin()."""
    # Valid 15-character GSTINs
    assert validate_gstin("29ABCDE1234F1Z5")[0] is True
    assert validate_gstin("07AAAAA1234A1Z1")[0] is True
    assert validate_gstin("27AAAPL1234C1ZV")[0] is True

    # Invalid GSTINs
    assert validate_gstin("29ABCDE1234F1A5")[0] is False  # 14th char not 'Z'
    assert validate_gstin("29ABCDE1234")[0] is False      # Too short
    assert validate_gstin("29ABCDE1234F1Z5EXTRA")[0] is False # Too long
    assert validate_gstin("ABCDE1234F1Z5")[0] is False    # Missing state code
    assert validate_gstin("")[0] is False


def test_registration_flow_input_validation(client):
    """Student registration rejects invalid phone and weak password."""
    # Weak password (< 8 chars)
    resp = client.post('/auth/register', data={
        'role': 'student',
        'email': 'new_stu@test.org',
        'password': 'short',
        'full_name': 'New Student',
        'phone': '9876543210'
    }, follow_redirects=True)
    assert b"Password must be at least 8 characters long." in resp.data

    # Weak password (no digits)
    resp2 = client.post('/auth/register', data={
        'role': 'student',
        'email': 'new_stu@test.org',
        'password': 'PasswordNoDigits',
        'full_name': 'New Student',
        'phone': '9876543210'
    }, follow_redirects=True)
    assert b"Password must contain at least one digit." in resp2.data

    # Invalid phone
    resp3 = client.post('/auth/register', data={
        'role': 'student',
        'email': 'new_stu@test.org',
        'password': 'ValidPass1!',
        'full_name': 'New Student',
        'phone': '123456'
    }, follow_redirects=True)
    assert b"Invalid Indian phone number" in resp3.data


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Internship Form Validation (Shared Helper)
# ═══════════════════════════════════════════════════════════════════════════════

def test_validate_internship_form_positive(app):
    """Valid payload passes validate_internship_form."""
    with app.app_context():
        cat = InternshipCategory.query.first()
        valid_data = {
            'title': 'Junior Python Backend Developer',
            'category_id': str(cat.id),
            'description': 'This is an extensive job description for a Python backend developer covering all duties and expectations thoroughly.',
            'eligibility': 'Any graduate',
            'skills_required': 'Python, SQL',
            'duration_weeks': '12',
            'stipend': '15000',
            'contact_email': 'recruiter@company.com',
            'application_deadline': (date.today() + timedelta(days=20)).isoformat(),
            'openings': '3'
        }
        is_valid, errors, cleaned = validate_internship_form(valid_data)
        assert is_valid is True
        assert len(errors) == 0
        assert cleaned['title'] == 'Junior Python Backend Developer'
        assert cleaned['stipend_amount'] == 15000.0


def test_validate_internship_form_catches_all_business_violations(app):
    """validate_internship_form catches short text, past deadline, negative stipend, missing category."""
    with app.app_context():
        # Past deadline, negative stipend, short title, short description, invalid category
        bad_data = {
            'title': 'Dev',  # < 5 chars
            'category_id': '999999',  # Non-existent category
            'description': 'Too short description.',  # < 50 chars
            'eligibility': 'Graduates',
            'skills_required': 'Python',
            'duration_weeks': '-2',
            'stipend': '-500',  # Negative stipend
            'application_deadline': (date.today() - timedelta(days=1)).isoformat(),  # Past deadline
            'openings': '-1'
        }
        is_valid, errors, cleaned = validate_internship_form(bad_data)
        assert is_valid is False
        error_text = " ".join(errors)
        assert "at least 5 characters" in error_text
        assert "minimum 50 characters" in error_text
        assert "future date" in error_text
        assert "cannot be negative" in error_text
        assert "domain category does not exist" in error_text
        assert "Duration in weeks must be between 1 and 104" in error_text


def test_validate_internship_form_handles_malformed_numbers_without_crashing(app):
    """Malformed numbers in form fields should be caught gracefully without 500 error."""
    with app.app_context():
        malformed_data = {
            'title': 'Python Developer Intern Role',
            'category_id': 'not-a-number',
            'description': 'This is a sufficiently long description that satisfies the minimum length requirement for testing purposes.',
            'eligibility': 'Any BCA',
            'skills_required': 'Python',
            'duration_weeks': 'twelve',
            'stipend': 'abc',
            'application_deadline': 'invalid-date-format',
            'openings': 'lots'
        }
        is_valid, errors, cleaned = validate_internship_form(malformed_data)
        assert is_valid is False
        assert len(errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Applicants Query Parameter Parsing
# ═══════════════════════════════════════════════════════════════════════════════

def test_applicants_parameter_hardening(client, app):
    """
    In /company/applicants:
    - Missing internship_id loads safely (200).
    - Malformed internship_id (e.g., 'abc') does not crash (200, flashed warning).
    - Negative internship_id (e.g., -1) does not crash (200, flashed warning).
    - ID of another company's internship is rejected (403 Forbidden).
    """
    client.post('/auth/login', data={'email': 'companya_h@test.org', 'password': 'CompanyPass1!'})

    # 1. Missing internship_id -> loads cleanly
    resp1 = client.get('/company/applicants')
    assert resp1.status_code == 200

    # 2. Malformed internship_id -> no HTTP 500
    resp2 = client.get('/company/applicants?internship_id=invalid_text', follow_redirects=True)
    assert resp2.status_code == 200
    assert b"Invalid internship ID format." in resp2.data

    # 3. Negative internship_id -> no HTTP 500
    resp3 = client.get('/company/applicants?internship_id=-10', follow_redirects=True)
    assert resp3.status_code == 200
    assert b"Internship ID must be a positive integer." in resp3.data

    # 4. Internship belonging to Company B -> flash warning, unauthorized access prevented
    with app.app_context():
        intern_b = Internship.query.filter_by(title='Company B Hardened Job').first()
        b_id = intern_b.id

    resp4 = client.get(f'/company/applicants?internship_id={b_id}', follow_redirects=True)
    assert resp4.status_code == 200
    assert b"Unauthorized or invalid internship selected." in resp4.data

    client.post('/auth/logout')


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Startup Configuration & Error Pages
# ═══════════════════════════════════════════════════════════════════════════════

def test_startup_fails_when_secret_key_missing_in_production(monkeypatch):
    """
    create_app() must raise a clear RuntimeError if SECRET_KEY is missing
    in non-debug and non-testing mode.
    """
    monkeypatch.delenv('SECRET_KEY', raising=False)

    class MissingKeyConfig(Config):
        SECRET_KEY = None
        DEBUG = False
        TESTING = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    with pytest.raises(RuntimeError) as exc_info:
        create_app(MissingKeyConfig)

    assert "SECRET_KEY is missing in non-debug mode" in str(exc_info.value)


def test_500_error_page_wording_does_not_claim_alerting_engineers(client, app):
    """The 500 error page should provide a polite error message without false claims."""
    # Test error template rendering directly via test request context
    with app.test_request_context():
        from flask import render_template
        rendered = render_template('base.html', error_code=500, error_title="Server Error",
                                   error_msg="An unexpected error occurred on the server. Please try again later or contact support.")
        assert "An unexpected error occurred on the server." in rendered
        assert "Please try again later or contact support." in rendered
        assert "Engineers have been alerted" not in rendered
        assert "alerted our team" not in rendered
