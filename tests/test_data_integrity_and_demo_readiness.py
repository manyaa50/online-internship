"""
tests/test_data_integrity_and_demo_readiness.py
================================================
Test suite for Data-Integrity and Demonstration-Readiness Cleanup:
  1. Removal of public-facing demo login buttons, autofill helpers, shortcuts, and plaintext demo passwords.
  2. Truthful risk-result wording and prominent disclaimers on detail, listing, and home pages.
  3. Dashboard totals calculated from real database queries (Student, Company, Admin, Home).
  4. Seed database idempotency and duplication prevention across repeated executions.
  5. Configurable portal and company contact information.
"""
from datetime import date, timedelta
import pytest
from app import create_app
from app.config import Config
from app.models import (
    db, User, Admin, StudentProfile, Company,
    InternshipCategory, Internship, ScamCheck, Application, Resume
)
from seed import seed_database


# ═══════════════════════════════════════════════════════════════════════════════
# Test App & Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='function')
def app():
    """Create test application with in-memory SQLite database for testing."""
    class TestDataIntegrityConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'test-data-integrity-key'
        SERVER_NAME = 'localhost'

    app_instance = create_app(TestDataIntegrityConfig)

    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_user(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Demo Shortcuts & Autofill Removal Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_login_page_demo_shortcuts_and_autofill_removed(client):
    """
    Verify that public-facing login interface does not contain quick-login buttons,
    autofill pills, demo credentials shortcuts, or publicly visible plaintext passwords.
    """
    resp = client.get('/auth/login')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # No autofill helper scripts or buttons
    assert 'fillDemoCredentials' not in html
    assert 'quick-login' not in html
    assert 'Quick Test Credentials' not in html
    assert 'Click to Autofill' not in html

    # Plaintext demo passwords must NOT be displayed on public login page
    assert 'Admin@12345' not in html
    assert 'Student@12345' not in html
    assert 'Company@12345' not in html
    assert 'Scam@12345' not in html

    # Legitimate password input field exists
    assert 'type="password"' in html
    assert 'name="password"' in html
    assert 'name="email"' in html


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Truthful Risk-Result Wording & Disclaimer Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_truthful_risk_wording_and_disclaimer_on_internship_detail(app, client):
    """
    Verify that low-risk internships are presented with truthful wording
    and that a low-risk score is explicitly disclaimed as not being proof of safety.
    """
    with app.app_context():
        cat = InternshipCategory(name="Engineering", description="Software engineering")
        db.session.add(cat)
        db.session.flush()

        u = User(email='comp_truth@test.org', role='company', is_active=True)
        u.set_password('Password123!')
        db.session.add(u)
        db.session.flush()

        comp = Company(
            user_id=u.id,
            company_name='Truthful Corp',
            official_email='comp_truth@test.org',
            phone='+91 99999 11111',
            verification_status='approved'
        )
        db.session.add(comp)
        db.session.flush()

        intern = Internship(
            company_id=comp.id,
            category_id=cat.id,
            title='Backend Python Trainee',
            description='Work on backend microservices with Python and Flask.',
            responsibilities='Write code and tests.',
            eligibility='BCA students',
            skills_required='Python, Flask',
            duration_weeks=12,
            duration_text='12 Weeks',
            location_type='remote',
            stipend_type='paid',
            stipend_amount=15000.0,
            application_deadline=date.today() + timedelta(days=20),
            contact_email='comp_truth@test.org',
            status='active'
        )
        db.session.add(intern)
        db.session.flush()

        scam_check = ScamCheck(
            internship_id=intern.id,
            risk_score=10,
            risk_level='Low',
            summary_notes='No scam heuristics triggered.',
            disclaimer='Automated rule-based risk assessment. This result is not proof of fraud or legitimacy.'
        )
        db.session.add(scam_check)
        db.session.commit()
        intern_id = intern.id

    resp = client.get(f'/internships/{intern_id}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # Must contain truthful risk label
    assert 'Low Risk' in html

    # Must NOT claim absolute/guaranteed safety
    assert '100% safe' not in html.lower()
    assert 'guaranteed safe' not in html.lower()

    # Must display the prominent disclaimer
    assert 'Automated rule-based risk assessment. This result is not proof of fraud or legitimacy.' in html


def test_truthful_risk_wording_on_public_listings_and_home(app, client):
    """
    Verify that public listings and home page render 'Low Risk' badges
    rather than declaring absolute safety.
    """
    with app.app_context():
        cat = InternshipCategory(name="Design", description="Product design")
        db.session.add(cat)
        db.session.flush()

        u = User(email='design_truth@test.org', role='company', is_active=True)
        u.set_password('Password123!')
        db.session.add(u)
        db.session.flush()

        comp = Company(
            user_id=u.id,
            company_name='Design Studio',
            official_email='design_truth@test.org',
            phone='+91 99999 22222',
            verification_status='approved'
        )
        db.session.add(comp)
        db.session.flush()

        intern = Internship(
            company_id=comp.id,
            category_id=cat.id,
            title='UI Design Apprentice',
            description='Create UI mockups in Figma.',
            responsibilities='Design interfaces.',
            eligibility='Design students',
            skills_required='Figma',
            duration_weeks=8,
            duration_text='8 Weeks',
            location_type='remote',
            stipend_type='paid',
            stipend_amount=12000.0,
            application_deadline=date.today() + timedelta(days=20),
            contact_email='design_truth@test.org',
            status='active'
        )
        db.session.add(intern)
        db.session.flush()

        scam_check = ScamCheck(
            internship_id=intern.id,
            risk_score=5,
            risk_level='Low',
            summary_notes='Low risk.',
            disclaimer='Automated rule-based risk assessment. This result is not proof of fraud or legitimacy.'
        )
        db.session.add(scam_check)
        db.session.commit()

    # 1. Listing Page
    resp_list = client.get('/internships/')
    assert resp_list.status_code == 200
    html_list = resp_list.data.decode('utf-8')
    assert 'Low Risk (5/100)' in html_list
    assert 'Safe (5/100)' not in html_list

    # 2. Home Page
    resp_home = client.get('/')
    assert resp_home.status_code == 200
    html_home = resp_home.data.decode('utf-8')
    assert 'Featured Opportunities' in html_home
    assert 'Featured Safe Internships' not in html_home
    assert 'Low Risk (5/100)' in html_home


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Dashboard Counts from Real Database Queries Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_student_dashboard_counts_calculated_from_database(app, client):
    """
    Verify that student dashboard totals reflect actual database records and update dynamically.
    """
    with app.app_context():
        u = User(email='stud_dash@test.org', role='student', is_active=True)
        u.set_password('Password123!')
        db.session.add(u)
        db.session.flush()

        student = StudentProfile(
            user_id=u.id,
            full_name='Dashboard Student',
            phone='+91 99999 33333',
            degree='BCA'
        )
        db.session.add(student)
        db.session.flush()

        comp_user = User(email='comp_dash@test.org', role='company', is_active=True)
        comp_user.set_password('Password123!')
        db.session.add(comp_user)
        db.session.flush()

        comp = Company(
            user_id=comp_user.id,
            company_name='Dashboard Corp',
            official_email='comp_dash@test.org',
            phone='+91 99999 44444',
            verification_status='approved'
        )
        db.session.add(comp)
        db.session.flush()

        cat = InternshipCategory(name="Analytics", description="Data analytics")
        db.session.add(cat)
        db.session.flush()

        i1 = Internship(
            company_id=comp.id, category_id=cat.id, title='Analyst 1',
            description='Test description long enough to pass validation', responsibilities='Test', eligibility='Test',
            skills_required='SQL', duration_weeks=12, duration_text='12 Weeks', location_type='remote',
            stipend_type='paid', stipend_amount=10000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='comp_dash@test.org', status='active'
        )
        i2 = Internship(
            company_id=comp.id, category_id=cat.id, title='Analyst 2',
            description='Test description long enough to pass validation', responsibilities='Test', eligibility='Test',
            skills_required='SQL', duration_weeks=12, duration_text='12 Weeks', location_type='remote',
            stipend_type='paid', stipend_amount=10000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='comp_dash@test.org', status='active'
        )
        db.session.add_all([i1, i2])
        db.session.flush()

        # Student Resume
        res = Resume(
            student_id=student.id,
            filename='resume.pdf',
            original_name='resume.pdf',
            file_path='instance/uploads/resumes/resume.pdf',
            file_size=1024,
            is_primary=True
        )
        db.session.add(res)
        db.session.flush()

        # 1 Under Review application, 1 Selected application
        app1 = Application(internship_id=i1.id, student_id=student.id, resume_id=res.id, status='Under Review')
        app2 = Application(internship_id=i2.id, student_id=student.id, resume_id=res.id, status='Selected')
        db.session.add_all([app1, app2])
        db.session.commit()

    login_user(client, 'stud_dash@test.org', 'Password123!')
    resp = client.get('/student/dashboard')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # Total applications = 2
    assert '<div class="stat-value">2</div>' in html
    # Under Review = 1, Selected = 1
    assert '<div class="stat-value">1</div>' in html


def test_company_dashboard_counts_calculated_from_database(app, client):
    """
    Verify that company dashboard calculates posting and application counts directly from database queries.
    """
    with app.app_context():
        u = User(email='comp_stats@test.org', role='company', is_active=True)
        u.set_password('Password123!')
        db.session.add(u)
        db.session.flush()

        comp = Company(
            user_id=u.id,
            company_name='Stats Corp',
            official_email='comp_stats@test.org',
            phone='+91 99999 55555',
            verification_status='approved'
        )
        db.session.add(comp)
        db.session.flush()

        cat = InternshipCategory(name="Web", description="Web tech")
        db.session.add(cat)
        db.session.flush()

        # Create 2 active postings and 1 flagged posting
        p1 = Internship(
            company_id=comp.id, category_id=cat.id, title='Active Role 1',
            description='Test description long enough to pass validation', responsibilities='Test', eligibility='Test',
            skills_required='Flask', duration_weeks=12, duration_text='12 Weeks', location_type='remote',
            stipend_type='paid', stipend_amount=15000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='comp_stats@test.org', status='active'
        )
        p2 = Internship(
            company_id=comp.id, category_id=cat.id, title='Active Role 2',
            description='Test description long enough to pass validation', responsibilities='Test', eligibility='Test',
            skills_required='Flask', duration_weeks=12, duration_text='12 Weeks', location_type='remote',
            stipend_type='paid', stipend_amount=15000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='comp_stats@test.org', status='active'
        )
        p3 = Internship(
            company_id=comp.id, category_id=cat.id, title='Flagged Role',
            description='Test description long enough to pass validation', responsibilities='Test', eligibility='Test',
            skills_required='Flask', duration_weeks=12, duration_text='12 Weeks', location_type='remote',
            stipend_type='paid', stipend_amount=15000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='comp_stats@test.org', status='flagged'
        )
        db.session.add_all([p1, p2, p3])
        # Create 1 Student and 1 Application
        su = User(email='applicant@test.org', role='student', is_active=True)
        su.set_password('Password123!')
        db.session.add(su)
        db.session.flush()

        sp = StudentProfile(user_id=su.id, full_name='Applicant Candidate', phone='+91 99999 00000')
        db.session.add(sp)
        db.session.flush()

        res = Resume(student_id=sp.id, filename='app_res.pdf', original_name='res.pdf', file_path='instance/uploads/resumes/res.pdf', file_size=1024, is_primary=True)
        db.session.add(res)
        db.session.flush()

        app1 = Application(internship_id=p1.id, student_id=sp.id, resume_id=res.id, status='Under Review')
        db.session.add(app1)

        db.session.commit()

    login_user(client, 'comp_stats@test.org', 'Password123!')
    resp = client.get('/company/dashboard')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # Total Postings = 3
    assert 'Total Postings' in html
    assert '<div class="stat-value">3</div>' in html
    # Active Postings = 2
    assert 'Active Postings' in html
    assert '<div class="stat-value">2</div>' in html
    # Total Applicants = 1
    assert 'Total Applicants' in html
    assert 'Pending Review' in html
    assert '<div class="stat-value">1</div>' in html


def test_admin_dashboard_counts_calculated_from_database(app, client):
    """
    Verify that admin dashboard calculates totals dynamically from database queries.
    """
    with app.app_context():
        admin_u = User(email='admin_stats@test.org', role='admin', is_active=True)
        admin_u.set_password('AdminPass123!')
        db.session.add(admin_u)
        db.session.flush()

        admin_p = Admin(user_id=admin_u.id, full_name='Telemetry Admin', phone='+91 99999 66666')
        db.session.add(admin_p)

        # 2 Students
        for i in range(2):
            su = User(email=f'stud_cnt_{i}@test.org', role='student', is_active=True)
            su.set_password('Pass123!')
            db.session.add(su)
            db.session.flush()
            db.session.add(StudentProfile(user_id=su.id, full_name=f'Student {i}', phone='+91 99999 77777'))

        # 1 Approved Company, 1 Pending Company
        cu1 = User(email='c_appr@test.org', role='company', is_active=True)
        cu1.set_password('Pass123!')
        db.session.add(cu1)
        db.session.flush()
        db.session.add(Company(user_id=cu1.id, company_name='Appr Corp', official_email='c_appr@test.org', phone='+91 99999 88888', verification_status='approved'))

        cu2 = User(email='c_pend@test.org', role='company', is_active=True)
        cu2.set_password('Pass123!')
        db.session.add(cu2)
        db.session.flush()
        db.session.add(Company(user_id=cu2.id, company_name='Pend Corp', official_email='c_pend@test.org', phone='+91 99999 88889', verification_status='pending'))

        db.session.commit()

    login_user(client, 'admin_stats@test.org', 'AdminPass123!')
    resp = client.get('/admin/dashboard')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # Total Students = 2
    assert '<div class="stat-label">Students</div>' in html
    assert '<div class="stat-value">2</div>' in html
    # Total Companies = 2
    assert '<div class="stat-label">Companies</div>' in html
    # Pending Verification = 1
    assert '<div class="stat-label">Pending Verif.</div>' in html
    assert '<div class="stat-value">1</div>' in html


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Seed Database Idempotency & Repeatability Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_seed_database_is_idempotent_and_creates_no_duplicates(app):
    """
    Verify that seed_database can be executed multiple times without raising integrity errors,
    without duplicating records, and without modifying existing records.
    """
    with app.app_context():
        # First execution: Populate seed data
        seed_database(app)

        users_count_1 = User.query.count()
        companies_count_1 = Company.query.count()
        students_count_1 = StudentProfile.query.count()
        categories_count_1 = InternshipCategory.query.count()
        internships_count_1 = Internship.query.count()
        scam_checks_count_1 = ScamCheck.query.count()
        applications_count_1 = Application.query.count()

        assert users_count_1 >= 4
        assert companies_count_1 >= 3
        assert students_count_1 >= 1
        assert categories_count_1 == 8
        assert internships_count_1 >= 6

        # Second execution: Re-run seed logic on existing database
        seed_database(app)

        # Row counts must remain exactly the same (no duplicate records)
        assert User.query.count() == users_count_1
        assert Company.query.count() == companies_count_1
        assert StudentProfile.query.count() == students_count_1
        assert InternshipCategory.query.count() == categories_count_1
        assert Internship.query.count() == internships_count_1
        assert ScamCheck.query.count() == scam_checks_count_1
        assert Application.query.count() == applications_count_1

        # Third execution: Repeated run is safe
        seed_database(app)
        assert User.query.count() == users_count_1


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Configurable Contact Information Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_configurable_contact_information_renders_properly(app, client):
    """
    Verify that contact details are configurable through app.config and rendered properly.
    """
    # 1. Default configuration
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '[Placeholder Email: contact@smartintern-placeholder.example.com]' in html
    assert '[Placeholder Phone: +91 (000) 000-0000 / +91 98765-00000]' in html

    # 2. Custom configuration overrides
    app.config['COMPANY_CONTACT_EMAIL'] = 'support@college-internships.edu'
    app.config['COMPANY_CONTACT_PHONE'] = '+91 80 1234 5678'
    app.config['COMPANY_CONTACT_ADDRESS'] = 'Academic Block 3, University Campus, Bengaluru, India'

    resp_custom = client.get('/')
    assert resp_custom.status_code == 200
    html_custom = resp_custom.data.decode('utf-8')
    assert '[Placeholder Email: support@college-internships.edu]' in html_custom
    assert '[Placeholder Phone: +91 80 1234 5678]' in html_custom
    assert '[Placeholder Postal Address: Academic Block 3, University Campus, Bengaluru, India]' in html_custom
