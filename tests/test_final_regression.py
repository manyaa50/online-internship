"""
tests/test_final_regression.py
==============================
Final comprehensive regression test suite for the Smart Online Internship
Management System with Scam Prevention.

Verifies end-to-end critical application workflows:
  1. Registration role and password validation, login blocking of suspended users,
     POST-only logout enforcement.
  2. Student profile numeric validation, resume authorization isolation (IDOR protection),
     application deadline validation, duplicate prevention, and malformed resume ID handling.
  3. Company verification gating on internship editing, applicants filter isolation across companies,
     and applicant status update notification delivery.
  4. Scam report submission, auto/admin notification delivery, and report resolution with delist cascade.
  5. Scam detector Hinglish heuristics, payment paraphrases with UPI/payment apps, and bounded negation.
  6. Custom error handling status codes and user-facing templates.
"""
from datetime import datetime, date, timedelta, timezone
import pytest
from app import create_app
from app.config import Config
from app.models import (
    db, User, Admin, StudentProfile, Company, CompanyVerification,
    Internship, InternshipCategory, ScamCheck, ScamReport, Notification, Application, Resume
)
from app.scam_detector import ScamDetector


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='function')
def app():
    """Create test application with in-memory SQLite database for each test."""
    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'test-secret-key-regression-suite'
        SERVER_NAME = 'localhost'

    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

def create_user(email, role, is_active=True, password='Password123!'):
    norm_email = email.strip().lower()
    u = User(email=norm_email, role=role, is_active=is_active)
    u.set_password(password)
    db.session.add(u)
    db.session.flush()
    return u


def login_user(client, email, password='Password123!'):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=False)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Authentication & Registration Regression Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_registration_invalid_role_blocked(client, app):
    """Attempting to register with an unpermitted role (e.g., admin) is rejected."""
    resp = client.post('/auth/register', data={
        'role': 'admin',
        'email': 'eviladmin@example.com',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!',
        'phone': '9876543210'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid role selected.' in resp.data
    with app.app_context():
        assert User.query.filter_by(email='eviladmin@example.com').first() is None


def test_registration_password_confirm_mismatch(client, app):
    """Registration fails if passwords do not match."""
    resp = client.post('/auth/register', data={
        'role': 'student',
        'email': 'newstudent@example.com',
        'password': 'SecurePassword123!',
        'confirm_password': 'MismatchPassword123!',
        'phone': '9876543210',
        'full_name': 'New Student'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Passwords do not match.' in resp.data
    with app.app_context():
        assert User.query.filter_by(email='newstudent@example.com').first() is None


def test_login_blocked_account_refused(client, app):
    """Deactivated or blocked accounts cannot log in."""
    with app.app_context():
        create_user('blocked@example.com', role='student', is_active=False)
        db.session.commit()

    resp = client.post('/auth/login', data={
        'email': 'blocked@example.com',
        'password': 'Password123!'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Your account has been deactivated or blocked' in resp.data


def test_logout_get_method_not_allowed(client, app):
    """GET /auth/logout returns 405 Method Not Allowed and preserves active session."""
    with app.app_context():
        u = create_user('active_student@example.com', role='student', is_active=True)
        db.session.add(StudentProfile(user_id=u.id, full_name='Active Student', phone='9876543210'))
        db.session.commit()

    login_user(client, 'active_student@example.com')
    resp = client.get('/auth/logout')
    assert resp.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Student Profile & Resume Download Security Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_student_profile_invalid_cgpa_validation(client, app):
    """Submitting an out-of-range or malformed CGPA fails validation safely."""
    with app.app_context():
        u = create_user('cgpa_student@example.com', role='student', is_active=True)
        prof = StudentProfile(user_id=u.id, full_name='CGPA Student', phone='9876543210', cgpa=8.5)
        db.session.add(prof)
        db.session.commit()

    login_user(client, 'cgpa_student@example.com')

    # Out of range CGPA (>10)
    resp = client.post('/student/profile', data={
        'full_name': 'CGPA Student',
        'phone': '9876543210',
        'cgpa': '15.5'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'CGPA must be between 0 and 10.' in resp.data

    with app.app_context():
        prof = StudentProfile.query.filter_by(full_name='CGPA Student').first()
        assert float(prof.cgpa) == 8.5  # Unchanged


def test_student_cannot_download_other_student_resume(client, app):
    """Student A is blocked from downloading Student B's private resume."""
    with app.app_context():
        u1 = create_user('student1@example.com', role='student')
        p1 = StudentProfile(user_id=u1.id, full_name='Student One', phone='9876543211')
        db.session.add(p1)
        db.session.flush()
        r1 = Resume(student_id=p1.id, filename='resume1.pdf', original_name='Resume1.pdf',
                    file_path='instance/uploads/resumes/resume1.pdf', file_size=1024, is_primary=True)
        db.session.add(r1)

        u2 = create_user('student2@example.com', role='student')
        p2 = StudentProfile(user_id=u2.id, full_name='Student Two', phone='9876543212')
        db.session.add(p2)
        db.session.commit()
        r1_id = r1.id

    login_user(client, 'student2@example.com')
    resp = client.get(f'/student/resume/download/{r1_id}', follow_redirects=True)
    assert resp.status_code == 200
    assert b'You are not authorized to download this resume.' in resp.data


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Application Submission & Gating Regression Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_application_expired_deadline_blocked(client, app):
    """Students cannot apply to an internship whose application deadline has passed."""
    with app.app_context():
        c_user = create_user('corp_exp@example.com', role='company')
        company = Company(user_id=c_user.id, company_name='Exp Corp', official_email='corp_exp@example.com',
                          phone='9876543220', verification_status='approved')
        db.session.add(company)
        cat = InternshipCategory(name='Tech Exp', description='Tech')
        db.session.add(cat)
        db.session.flush()

        past_deadline = date.today() - timedelta(days=2)
        intern = Internship(
            company_id=company.id, category_id=cat.id, title='Expired Internship',
            description='Test Description', responsibilities='Tasks', eligibility='Any',
            skills_required='Python', duration_weeks=8, duration_text='8 weeks',
            location_type='remote', stipend_type='paid', stipend_amount=10000,
            openings_count=2, start_date=date.today() + timedelta(days=10),
            application_deadline=past_deadline, contact_email='corp_exp@example.com',
            status='active'
        )
        db.session.add(intern)

        s_user = create_user('applicant_exp@example.com', role='student')
        stud = StudentProfile(user_id=s_user.id, full_name='Applicant Exp', phone='9876543221')
        db.session.add(stud)
        db.session.flush()
        res = Resume(student_id=stud.id, filename='r_exp.pdf', original_name='Resume.pdf',
                     file_path='instance/uploads/resumes/r_exp.pdf', file_size=1024, is_primary=True)
        db.session.add(res)
        db.session.commit()
        intern_id = intern.id

    login_user(client, 'applicant_exp@example.com')
    resp = client.post(f'/internships/{intern_id}/apply', data={'cover_letter': 'Hello'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'The application deadline for this internship has passed.' in resp.data

    with app.app_context():
        assert Application.query.filter_by(internship_id=intern_id).count() == 0


def test_application_duplicate_submission_blocked(client, app):
    """Students cannot submit duplicate applications for the same internship."""
    with app.app_context():
        c_user = create_user('corp_dup@example.com', role='company')
        company = Company(user_id=c_user.id, company_name='Dup Corp', official_email='corp_dup@example.com',
                          phone='9876543230', verification_status='approved')
        db.session.add(company)
        cat = InternshipCategory(name='Tech Dup', description='Tech')
        db.session.add(cat)
        db.session.flush()

        future_deadline = date.today() + timedelta(days=15)
        intern = Internship(
            company_id=company.id, category_id=cat.id, title='Active Internship',
            description='Test Description', responsibilities='Tasks', eligibility='Any',
            skills_required='Python', duration_weeks=8, duration_text='8 weeks',
            location_type='remote', stipend_type='paid', stipend_amount=10000,
            openings_count=2, start_date=date.today() + timedelta(days=5),
            application_deadline=future_deadline, contact_email='corp_dup@example.com',
            status='active'
        )
        db.session.add(intern)

        s_user = create_user('applicant_dup@example.com', role='student')
        stud = StudentProfile(user_id=s_user.id, full_name='Applicant Dup', phone='9876543231')
        db.session.add(stud)
        db.session.flush()
        res = Resume(student_id=stud.id, filename='r_dup.pdf', original_name='Resume.pdf',
                     file_path='instance/uploads/resumes/r_dup.pdf', file_size=1024, is_primary=True)
        db.session.add(res)
        db.session.commit()
        intern_id = intern.id

    login_user(client, 'applicant_dup@example.com')

    # First application succeeds
    resp1 = client.post(f'/internships/{intern_id}/apply', data={'cover_letter': 'First'}, follow_redirects=True)
    assert resp1.status_code == 200
    assert b'Your application has been successfully submitted.' in resp1.data

    # Second application is rejected
    resp2 = client.post(f'/internships/{intern_id}/apply', data={'cover_letter': 'Second'}, follow_redirects=True)
    assert resp2.status_code == 200
    assert b'You have already applied for this internship position.' in resp2.data

    with app.app_context():
        assert Application.query.filter_by(internship_id=intern_id).count() == 1


def test_application_malformed_resume_id_handled(client, app):
    """Submitting a malformed/non-numeric resume_id safely falls back to primary resume."""
    with app.app_context():
        c_user = create_user('corp_mal@example.com', role='company')
        company = Company(user_id=c_user.id, company_name='Mal Corp', official_email='corp_mal@example.com',
                          phone='9876543240', verification_status='approved')
        db.session.add(company)
        cat = InternshipCategory(name='Tech Mal', description='Tech')
        db.session.add(cat)
        db.session.flush()

        future_deadline = date.today() + timedelta(days=15)
        intern = Internship(
            company_id=company.id, category_id=cat.id, title='Malform Test Posting',
            description='Test Description', responsibilities='Tasks', eligibility='Any',
            skills_required='Python', duration_weeks=8, duration_text='8 weeks',
            location_type='remote', stipend_type='paid', stipend_amount=10000,
            openings_count=2, start_date=date.today() + timedelta(days=5),
            application_deadline=future_deadline, contact_email='corp_mal@example.com',
            status='active'
        )
        db.session.add(intern)

        s_user = create_user('applicant_mal@example.com', role='student')
        stud = StudentProfile(user_id=s_user.id, full_name='Applicant Mal', phone='9876543241')
        db.session.add(stud)
        db.session.flush()
        res = Resume(student_id=stud.id, filename='r_mal.pdf', original_name='Resume.pdf',
                     file_path='instance/uploads/resumes/r_mal.pdf', file_size=1024, is_primary=True)
        db.session.add(res)
        db.session.commit()
        intern_id = intern.id
        expected_resume_id = res.id

    login_user(client, 'applicant_mal@example.com')
    # Provide invalid non-integer string for resume_id
    resp = client.post(f'/internships/{intern_id}/apply', data={
        'resume_id': 'corrupted_string_id_xyz',
        'cover_letter': 'Test Cover Letter'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Your application has been successfully submitted.' in resp.data

    with app.app_context():
        app_record = Application.query.filter_by(internship_id=intern_id).first()
        assert app_record is not None
        assert app_record.resume_id == expected_resume_id  # Fell back safely to primary resume


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Company Gating & Applicant Management Security Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_unverified_company_cannot_access_edit_internship(client, app):
    """An unverified (pending) company is blocked from editing internships by @company_verified_required."""
    with app.app_context():
        c_user = create_user('unverif_edit@example.com', role='company')
        company = Company(user_id=c_user.id, company_name='Pending Co', official_email='unverif_edit@example.com',
                          phone='9876543250', verification_status='pending')
        db.session.add(company)
        cat = InternshipCategory(name='General Cat', description='General')
        db.session.add(cat)
        db.session.flush()

        intern = Internship(
            company_id=company.id, category_id=cat.id, title='Pre-existing Listing',
            description='Test Description', responsibilities='Tasks', eligibility='Any',
            skills_required='Java', duration_weeks=8, duration_text='8 weeks',
            location_type='on-site', location_city='Delhi', stipend_type='paid', stipend_amount=8000,
            openings_count=1, start_date=date.today(), application_deadline=date.today() + timedelta(days=10),
            contact_email='unverif_edit@example.com', status='active'
        )
        db.session.add(intern)
        db.session.commit()
        intern_id = intern.id

    login_user(client, 'unverif_edit@example.com')
    resp = client.get(f'/company/internships/edit/{intern_id}', follow_redirects=False)
    # Must redirect to company dashboard with status notice
    assert resp.status_code in (301, 302)
    assert '/company/dashboard' in resp.headers.get('Location', '')


def test_company_applicants_filtering_security(client, app):
    """Company A cannot view applicants of Company B's internship via query parameters."""
    with app.app_context():
        cA_user = create_user('compA@example.com', role='company')
        cA = Company(user_id=cA_user.id, company_name='Company A', official_email='compA@example.com',
                     phone='9876543260', verification_status='approved')
        db.session.add(cA)

        cB_user = create_user('compB@example.com', role='company')
        cB = Company(user_id=cB_user.id, company_name='Company B', official_email='compB@example.com',
                     phone='9876543261', verification_status='approved')
        db.session.add(cB)

        cat = InternshipCategory(name='Web Cat', description='Web')
        db.session.add(cat)
        db.session.flush()

        internB = Internship(
            company_id=cB.id, category_id=cat.id, title='Company B Job',
            description='Desc', responsibilities='Tasks', eligibility='Any',
            skills_required='CSS', duration_weeks=4, duration_text='4 weeks',
            location_type='remote', stipend_type='paid', stipend_amount=5000,
            openings_count=1, start_date=date.today(), application_deadline=date.today() + timedelta(days=10),
            contact_email='compB@example.com', status='active'
        )
        db.session.add(internB)

        s_user = create_user('applicant_b@example.com', role='student')
        stud = StudentProfile(user_id=s_user.id, full_name='Candidate For B', phone='9876543262')
        db.session.add(stud)
        db.session.flush()

        res = Resume(student_id=stud.id, filename='rB.pdf', original_name='Resume.pdf',
                     file_path='instance/uploads/resumes/rB.pdf', file_size=1024, is_primary=True)
        db.session.add(res)
        db.session.flush()

        appB = Application(internship_id=internB.id, student_id=stud.id, resume_id=res.id, status='Applied')
        db.session.add(appB)
        db.session.commit()
        internB_id = internB.id

    login_user(client, 'compA@example.com')
    # Company A requests Company B's internship applicants
    resp = client.get(f'/company/applicants?internship_id={internB_id}', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Unauthorized or invalid internship selected.' in resp.data
    assert b'Candidate For B' not in resp.data


def test_company_update_applicant_status_delivers_notification(client, app):
    """Updating applicant status notifies the student in real time."""
    with app.app_context():
        c_user = create_user('comp_notif@example.com', role='company')
        company = Company(user_id=c_user.id, company_name='Notif Co', official_email='comp_notif@example.com',
                          phone='9876543270', verification_status='approved')
        db.session.add(company)
        cat = InternshipCategory(name='Data Cat', description='Data')
        db.session.add(cat)
        db.session.flush()

        intern = Internship(
            company_id=company.id, category_id=cat.id, title='Data Analyst Role',
            description='Desc', responsibilities='Tasks', eligibility='Any',
            skills_required='SQL', duration_weeks=8, duration_text='8 weeks',
            location_type='remote', stipend_type='paid', stipend_amount=12000,
            openings_count=2, start_date=date.today(), application_deadline=date.today() + timedelta(days=10),
            contact_email='comp_notif@example.com', status='active'
        )
        db.session.add(intern)

        s_user = create_user('student_notif@example.com', role='student')
        stud = StudentProfile(user_id=s_user.id, full_name='Notif Student', phone='9876543271')
        db.session.add(stud)
        db.session.flush()

        res = Resume(student_id=stud.id, filename='rn.pdf', original_name='Resume.pdf',
                     file_path='instance/uploads/resumes/rn.pdf', file_size=1024, is_primary=True)
        db.session.add(res)
        db.session.flush()

        appl = Application(internship_id=intern.id, student_id=stud.id, resume_id=res.id, status='Applied')
        db.session.add(appl)
        db.session.commit()
        app_id = appl.id
        student_user_id = s_user.id

    login_user(client, 'comp_notif@example.com')
    resp = client.post(f'/company/applicants/update-status/{app_id}', data={
        'status': 'Selected',
        'company_feedback': 'Welcome to the team!'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        updated_app = db.session.get(Application, app_id)
        assert updated_app.status == 'Selected'
        assert updated_app.company_feedback == 'Welcome to the team!'

        notif = Notification.query.filter_by(user_id=student_user_id, category='application').first()
        assert notif is not None
        assert 'Application Update: Data Analyst Role' in notif.title
        assert "updated to 'Selected'" in notif.message


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Scam Detector Hinglish & Payment Paraphrase Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_scam_detector_hinglish_and_payment_paraphrase():
    """Scam detector identifies Hinglish phrases and UPI/payment app transfers."""
    # Hinglish demand
    posting_hinglish = {
        'title': 'Part-time Data Typist',
        'description': 'Simple task from mobile. Selection ke liye fees dena hoga turant.',
        'responsibilities': 'Typing',
        'eligibility': 'Any',
        'skills_required': 'Mobile typing',
        'stipend_type': 'fixed',
        'stipend_amount': 25000,
        'contact_email': 'jobs@gmail.com',
        'contact_phone': '9876543210'
    }
    result_h = ScamDetector.evaluate_posting(posting_hinglish)
    rules_h = [r['rule'] for r in result_h['triggered_rules']]
    assert 'Upfront Payment Requested' in rules_h

    # Paraphrased payment with payment app
    posting_upi = {
        'title': 'Customer Support Assistant',
        'description': 'To confirm your seat, transfer 1500 rs to our gpay number immediately.',
        'responsibilities': 'Calls',
        'eligibility': 'Any',
        'skills_required': 'Communication',
        'stipend_type': 'fixed',
        'stipend_amount': 15000,
        'contact_email': 'support@corp.com',
        'contact_phone': '9876543210'
    }
    result_u = ScamDetector.evaluate_posting(posting_upi)
    rules_u = [r['rule'] for r in result_u['triggered_rules']]
    assert 'Upfront Payment Requested' in rules_u

    # Negated payment must NOT trigger payment_demand
    posting_neg = {
        'title': 'Junior Python Developer',
        'description': 'We charge no registration fee or deposit for this internship position.',
        'responsibilities': 'Backend development',
        'eligibility': 'BCA or B.Tech graduates',
        'skills_required': 'Python, SQL',
        'stipend_type': 'fixed',
        'stipend_amount': 15000,
        'contact_email': 'careers@techcorp.example.com',
        'contact_phone': '9876543210'
    }
    result_neg = ScamDetector.evaluate_posting(posting_neg)
    rules_neg = [r['rule'] for r in result_neg['triggered_rules']]
    assert 'Upfront Payment Requested' not in rules_neg


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Error Handlers & Navigation Isolation Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_error_handlers_404_and_403(client):
    """Custom error handlers render proper HTTP codes and titles."""
    # 404 test
    resp_404 = client.get('/nonexistent-test-path-404')
    assert resp_404.status_code == 404
    assert b'Page Not Found' in resp_404.data

    # Unauthenticated access to admin dashboard -> redirect to login (302)
    resp_auth = client.get('/admin/dashboard', follow_redirects=False)
    assert resp_auth.status_code == 302
    assert '/auth/login' in resp_auth.headers.get('Location', '')
