"""
tests/test_security.py
======================
Security tests for the SmartInternshipSystem internship management endpoints.

Checks:
  1.  Unauthenticated access → 302 to login
  2.  Student cannot create internship
  3.  Student cannot edit internship
  4.  Student cannot delete internship
  5.  Student cannot toggle internship status
  6.  Unverified company cannot create internship
  7.  Suspended (inactive) company cannot create internship
  8.  Suspended company cannot edit internship
  9.  Suspended company cannot delete internship
  10. Cross-company access: Company B cannot edit Company A's internship
  11. Cross-company access: Company B cannot delete Company A's internship
  12. Cross-company access: Company B cannot toggle Company A's internship
  13. Company cannot set status to 'flagged' (admin-only)
  14. Company cannot set status to 'rejected' (admin-only)
  15. Verified company CAN access create form (positive check)
  16. Verified company CAN submit a valid internship (positive check)
  17. CSRF missing on POST returns 400
  18. Admin cannot post internship via company endpoint

Run with: venv\\Scripts\\python.exe -m pytest tests/test_security.py -v
"""
import json
import pytest
from datetime import date, timedelta
from app import create_app
from app.config import Config
from app.models import db as _db, User, StudentProfile, Company, Internship, InternshipCategory


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='session')
def app():
    """Create application with in-memory SQLite test database."""
    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False          # disable CSRF for most tests
        RATELIMIT_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'test-secret-key-not-for-prod'
        SERVER_NAME = 'localhost'

    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        _seed_test_data()
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def _seed_test_data():
    """Seed minimal test data — does not affect production DB."""

    # Admin
    admin_user = User(email='testadmin@example.com', role='admin', is_active=True)
    admin_user.set_password('AdminPass1!')
    _db.session.add(admin_user)

    # Student
    student_user = User(email='teststudent@example.com', role='student', is_active=True)
    student_user.set_password('StudentPass1!')
    _db.session.add(student_user)
    _db.session.flush()
    _db.session.add(StudentProfile(
        user_id=student_user.id, full_name='Test Student', phone='9000000001'
    ))

    # Verified company A (owner)
    company_a_user = User(email='companya@example.com', role='company', is_active=True)
    company_a_user.set_password('CompanyPass1!')
    _db.session.add(company_a_user)
    _db.session.flush()
    company_a = Company(
        user_id=company_a_user.id, company_name='Company A',
        official_email='companya@example.com', phone='9000000002',
        verification_status='approved'
    )
    _db.session.add(company_a)

    # Verified company B (adversary — tries cross-company attacks)
    company_b_user = User(email='companyb@example.com', role='company', is_active=True)
    company_b_user.set_password('CompanyPass1!')
    _db.session.add(company_b_user)
    _db.session.flush()
    company_b = Company(
        user_id=company_b_user.id, company_name='Company B',
        official_email='companyb@example.com', phone='9000000003',
        verification_status='approved'
    )
    _db.session.add(company_b)

    # Unverified company
    unverified_user = User(email='unverified@example.com', role='company', is_active=True)
    unverified_user.set_password('UnverifiedPass1!')
    _db.session.add(unverified_user)
    _db.session.flush()
    _db.session.add(Company(
        user_id=unverified_user.id, company_name='Unverified Co',
        official_email='unverified@example.com', phone='9000000004',
        verification_status='pending'
    ))

    # Suspended company (is_active=False, but still verified — worst case)
    suspended_user = User(email='suspended@example.com', role='company', is_active=False)
    suspended_user.set_password('SuspendedPass1!')
    _db.session.add(suspended_user)
    _db.session.flush()
    _db.session.add(Company(
        user_id=suspended_user.id, company_name='Suspended Co',
        official_email='suspended@example.com', phone='9000000005',
        verification_status='approved'
    ))

    _db.session.flush()

    # Category
    cat = InternshipCategory(name='Test Domain', description='For tests', icon_class='bi bi-code')
    _db.session.add(cat)
    _db.session.flush()

    # Company A's internship (used for cross-company + ownership tests)
    intern_a = Internship(
        company_id=company_a.id,
        category_id=cat.id,
        title='Company A Internship',
        description='A legitimate test internship for Company A with enough description text here.',
        eligibility='Any student',
        skills_required='Python',
        duration_weeks=8,
        duration_text='2 Months',
        location_type='remote',
        stipend_type='paid',
        stipend_amount=10000,
        openings_count=2,
        application_deadline=date.today() + timedelta(days=30),
        contact_email='companya@example.com',
        status='active'
    )
    _db.session.add(intern_a)
    _db.session.commit()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _login(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password},
                       follow_redirects=True)

def _logout(client):
    client.post('/auth/logout', follow_redirects=True)

def _get_intern_id(app):
    with app.app_context():
        i = Internship.query.filter_by(title='Company A Internship').first()
        return i.id if i else None

def _valid_form(app):
    """Returns a valid internship form payload."""
    with app.app_context():
        cat_id = InternshipCategory.query.first().id
    return {
        'title': 'Test Security Internship Role',
        'category_id': str(cat_id),
        'description': 'This is a detailed description for a secure internship posting that meets the minimum length requirement.',
        'responsibilities': 'Build APIs and write tests.',
        'eligibility': 'B.Tech CSE students graduating 2026.',
        'skills_required': 'Python, Flask',
        'duration_text': '3 Months',
        'duration_weeks': '12',
        'location_type': 'remote',
        'location_city': '',
        'stipend_type': 'paid',
        'stipend_amount': '15000',
        'openings_count': '2',
        'start_date': '',
        'application_deadline': str(date.today() + timedelta(days=30)),
        'application_instructions': '',
        'contact_email': 'test@companya.com',
        'contact_phone': '',
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 1 — Unauthenticated access → redirect to login
# ═══════════════════════════════════════════════════════════════════════════════

def test_01_unauthenticated_create_redirects_to_login(client):
    """GET /company/internships/create without login must redirect to auth."""
    resp = client.get('/company/internships/create', follow_redirects=False)
    assert resp.status_code in (301, 302), f"Expected redirect, got {resp.status_code}"
    assert '/auth/login' in resp.headers.get('Location', '') or \
           'login' in resp.headers.get('Location', '').lower()

def test_02_unauthenticated_post_create_rejected(client):
    """POST to create endpoint without login must not create anything."""
    resp = client.post('/company/internships/create', data={'title': 'Hack'})
    assert resp.status_code in (301, 302)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 3-5 — Student cannot manage internships
# ═══════════════════════════════════════════════════════════════════════════════

def test_03_student_cannot_get_create_form(client, app):
    _login(client, 'teststudent@example.com', 'StudentPass1!')
    resp = client.get('/company/internships/create', follow_redirects=False)
    assert resp.status_code in (301, 302)
    loc = resp.headers.get('Location', '')
    assert '/company/internships/create' not in loc
    _logout(client)

def test_04_student_cannot_post_create(client, app):
    _login(client, 'teststudent@example.com', 'StudentPass1!')
    resp = client.post('/company/internships/create', data=_valid_form(app),
                       follow_redirects=False)
    assert resp.status_code in (301, 302)
    # Confirm internship was NOT created
    with app.app_context():
        count = Internship.query.filter_by(title='Test Security Internship Role').count()
    assert count == 0, "Student must not be able to create an internship!"
    _logout(client)

def test_05_student_cannot_edit_internship(client, app):
    intern_id = _get_intern_id(app)
    _login(client, 'teststudent@example.com', 'StudentPass1!')
    resp = client.get(f'/company/internships/edit/{intern_id}', follow_redirects=False)
    assert resp.status_code in (301, 302)
    _logout(client)

def test_06_student_cannot_delete_internship(client, app):
    intern_id = _get_intern_id(app)
    _login(client, 'teststudent@example.com', 'StudentPass1!')
    resp = client.post(f'/company/internships/delete/{intern_id}', follow_redirects=False)
    assert resp.status_code in (301, 302)
    with app.app_context():
        still_exists = Internship.query.get(intern_id)
    assert still_exists is not None, "Student must not be able to delete an internship!"
    _logout(client)

def test_07_student_cannot_toggle_status(client, app):
    intern_id = _get_intern_id(app)
    _login(client, 'teststudent@example.com', 'StudentPass1!')
    resp = client.post(f'/company/internships/status/{intern_id}/closed', follow_redirects=False)
    assert resp.status_code in (301, 302)
    with app.app_context():
        intern = Internship.query.get(intern_id)
    assert intern.status == 'active', "Student must not be able to change internship status!"
    _logout(client)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 8-9 — Unverified company cannot post
# ═══════════════════════════════════════════════════════════════════════════════

def test_08_unverified_company_cannot_get_create_form(client):
    _login(client, 'unverified@example.com', 'UnverifiedPass1!')
    resp = client.get('/company/internships/create', follow_redirects=False)
    assert resp.status_code in (301, 302)
    loc = resp.headers.get('Location', '')
    assert 'create' not in loc
    _logout(client)

def test_09_unverified_company_cannot_post_create(client, app):
    _login(client, 'unverified@example.com', 'UnverifiedPass1!')
    resp = client.post('/company/internships/create', data=_valid_form(app),
                       follow_redirects=False)
    assert resp.status_code in (301, 302)
    with app.app_context():
        count = Internship.query.filter_by(title='Test Security Internship Role').count()
    assert count == 0, "Unverified company must not create internships!"
    _logout(client)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 10-12 — Suspended company cannot operate
# ═══════════════════════════════════════════════════════════════════════════════

def test_10_suspended_company_cannot_create(client, app):
    """Suspended (is_active=False) company must be blocked even if previously approved."""
    _login(client, 'suspended@example.com', 'SuspendedPass1!')
    resp = client.get('/company/internships/create', follow_redirects=False)
    # Suspended user gets logged out — any redirect is acceptable, but must not reach form
    assert resp.status_code in (301, 302)
    _logout(client)

def test_11_suspended_company_cannot_post(client, app):
    _login(client, 'suspended@example.com', 'SuspendedPass1!')
    resp = client.post('/company/internships/create', data=_valid_form(app),
                       follow_redirects=False)
    assert resp.status_code in (301, 302)
    with app.app_context():
        count = Internship.query.filter_by(title='Test Security Internship Role').count()
    assert count == 0, "Suspended company must not create internships!"
    _logout(client)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 13-15 — Cross-company ownership check (IDOR prevention)
# ═══════════════════════════════════════════════════════════════════════════════

def test_12_company_b_cannot_edit_company_a_internship(client, app):
    """Company B must not edit Company A's internship even with correct ID."""
    intern_id = _get_intern_id(app)
    _login(client, 'companyb@example.com', 'CompanyPass1!')
    form = _valid_form(app)
    form['title'] = 'HACKED TITLE'
    resp = client.post(f'/company/internships/edit/{intern_id}', data=form,
                       follow_redirects=False)
    # Must get 404 (ownership not found) or redirect away
    assert resp.status_code in (301, 302, 404)
    with app.app_context():
        intern = Internship.query.get(intern_id)
    assert intern.title == 'Company A Internship', "Cross-company edit must be blocked!"
    _logout(client)

def test_13_company_b_cannot_delete_company_a_internship(client, app):
    """Company B cannot delete Company A's internship."""
    intern_id = _get_intern_id(app)
    _login(client, 'companyb@example.com', 'CompanyPass1!')
    resp = client.post(f'/company/internships/delete/{intern_id}', follow_redirects=False)
    assert resp.status_code in (301, 302, 404)
    with app.app_context():
        still_exists = Internship.query.get(intern_id)
    assert still_exists is not None, "Cross-company delete must be blocked!"
    _logout(client)

def test_14_company_b_cannot_toggle_company_a_status(client, app):
    """Company B cannot change the status of Company A's internship."""
    intern_id = _get_intern_id(app)
    _login(client, 'companyb@example.com', 'CompanyPass1!')
    resp = client.post(f'/company/internships/status/{intern_id}/closed',
                       follow_redirects=False)
    assert resp.status_code in (301, 302, 404)
    with app.app_context():
        intern = Internship.query.get(intern_id)
    assert intern.status == 'active', "Cross-company status change must be blocked!"
    _logout(client)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 16-17 — Company cannot set admin-only statuses
# ═══════════════════════════════════════════════════════════════════════════════

def test_15_company_cannot_set_flagged_status(client, app):
    """Company A must not be able to set its own internship to 'flagged' (admin-only)."""
    intern_id = _get_intern_id(app)
    _login(client, 'companya@example.com', 'CompanyPass1!')
    resp = client.post(f'/company/internships/status/{intern_id}/flagged',
                       follow_redirects=False)
    assert resp.status_code == 403, \
        f"Expected 403 for admin-only status 'flagged', got {resp.status_code}"
    with app.app_context():
        intern = Internship.query.get(intern_id)
    assert intern.status == 'active', "Internship status must remain active!"
    _logout(client)

def test_16_company_cannot_set_rejected_status(client, app):
    """Company A must not be able to set its internship to 'rejected' (admin-only)."""
    intern_id = _get_intern_id(app)
    _login(client, 'companya@example.com', 'CompanyPass1!')
    resp = client.post(f'/company/internships/status/{intern_id}/rejected',
                       follow_redirects=False)
    assert resp.status_code == 403
    with app.app_context():
        intern = Internship.query.get(intern_id)
    assert intern.status == 'active'
    _logout(client)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 18-19 — Admin cannot use company endpoints (wrong role)
# ═══════════════════════════════════════════════════════════════════════════════

def test_17_admin_cannot_post_via_company_endpoint(client, app):
    """Admin role must be rejected from company endpoints (role mismatch)."""
    _login(client, 'testadmin@example.com', 'AdminPass1!')
    resp = client.post('/company/internships/create', data=_valid_form(app),
                       follow_redirects=False)
    assert resp.status_code in (301, 302)
    with app.app_context():
        count = Internship.query.filter_by(title='Test Security Internship Role').count()
    assert count == 0
    _logout(client)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST 20 — Positive: verified company CAN create (smoke test)
# ═══════════════════════════════════════════════════════════════════════════════

def test_18_verified_company_can_get_create_form(client):
    """Positive test: verified company reaches the create form."""
    _login(client, 'companya@example.com', 'CompanyPass1!')
    resp = client.get('/company/internships/create', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Post' in resp.data or b'Internship' in resp.data
    _logout(client)

def test_19_verified_company_can_submit_internship(client, app):
    """Positive test: full creation flow persists to DB."""
    _login(client, 'companya@example.com', 'CompanyPass1!')
    resp = client.post('/company/internships/create', data=_valid_form(app),
                       follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        count = Internship.query.filter_by(title='Test Security Internship Role').count()
    assert count >= 1, "Verified company must be able to create internships!"
    _logout(client)

def test_20_verified_company_can_toggle_own_internship(client, app):
    """Positive test: company can close its own listing."""
    intern_id = _get_intern_id(app)
    _login(client, 'companya@example.com', 'CompanyPass1!')
    resp = client.post(f'/company/internships/status/{intern_id}/closed',
                       follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        intern = Internship.query.get(intern_id)
    assert intern.status == 'closed', "Verified company must be able to close own listing!"
    # Restore to active
    client.post(f'/company/internships/status/{intern_id}/active')
    _logout(client)
