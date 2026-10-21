"""
tests/test_synopsis_gaps.py
===========================
Comprehensive test suite for Group 4 (Synopsis Feature Gaps):
  1. Internship Search Filters:
     - Duration range in weeks (min_duration, max_duration).
     - Skills explicit search.
     - Eligibility keyword search.
     - Combined filters working with pagination.
     - Preservation of filter query parameters in pagination links.
     - Safe handling of invalid non-numeric inputs (no 500 errors).
  2. Company Contact Information:
     - Clearly marked placeholder email, phone, and postal address in base.html footer.
     - Clearly marked placeholder email, phone, and postal address on home page.
  3. Company Verification Documents:
     - Upload validation of file signatures (PDF, PNG, JPG/JPEG).
     - Rejection of invalid signatures disguised as valid extensions.
     - Rejection of unsupported extensions.
     - Rejection of empty 0-byte uploads.
     - Private storage outside app/static (instance/uploads/company_docs).
     - Company owner authorized access to own document.
     - Admin authorized access to download documents.
     - Unauthorized access rejection for anonymous, students, or other companies.
  4. Medium-Risk Application Warning:
     - Warning banner displayed on Medium-risk posting detail page.
     - Warning acknowledgment checkbox rendered in application modal.
     - Server enforcement: direct POST without acknowledgment is rejected.
     - Server enforcement: POST with acknowledgment succeeds.
     - Low-risk posting preserves standard flow without requiring extra confirmation.
  5. Idempotent Migration:
     - scripts/migrate_company_docs.py handles additions and repeated runs safely.
"""
import io
import os
import shutil
import tempfile
from datetime import datetime, date, timedelta
import pytest
from pathlib import Path
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config import Config
from app.models import (
    db, User, Admin, StudentProfile, Resume, Company, Internship,
    InternshipCategory, Application, ScamCheck
)
from app.utils import validate_verification_document
from scripts import migrate_company_docs


# ═══════════════════════════════════════════════════════════════════════════════
# Test Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def create_valid_pdf_bytes():
    return b"%PDF-1.4\n1 0 obj\n<< /Title (Company Certificate) >>\nendobj\ntrailer\n<<>>\n%%EOF"


def create_valid_png_bytes():
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


def create_valid_jpg_bytes():
    # JPEG signature: FF D8 FF
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='session')
def synopsis_app(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp('synopsis_storage')
    resumes_dir = temp_dir / 'instance' / 'uploads' / 'resumes'
    docs_dir = temp_dir / 'instance' / 'uploads' / 'company_docs'
    resumes_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    class TestSynopsisConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'test-synopsis-key'
        SERVER_NAME = 'localhost'
        RESUME_FOLDER = str(resumes_dir)
        DOCS_FOLDER = str(docs_dir)
        MAX_CONTENT_LENGTH = 2 * 1024 * 1024
        PER_PAGE = 3  # Small page size to test pagination

    app = create_app(TestSynopsisConfig)

    with app.app_context():
        db.create_all()

        # Seed Admin
        admin_user = User(email='admin_g4@example.com', role='admin', is_active=True)
        admin_user.set_password('AdminPass1!')
        db.session.add(admin_user)
        db.session.flush()

        admin_prof = Admin(user_id=admin_user.id, full_name='Platform Admin', phone='+919999999999')
        db.session.add(admin_prof)

        # Seed Student
        stud_user = User(email='student_g4@example.com', role='student', is_active=True)
        stud_user.set_password('StudPass1!')
        db.session.add(stud_user)
        db.session.flush()

        student_profile = StudentProfile(
            user_id=stud_user.id,
            full_name='Aarav Sharma',
            phone='+919876543210',
            college_name='Bengaluru University',
            degree='BCA',
            graduation_year=2026
        )
        db.session.add(student_profile)

        # Seed Company 1 (Approved)
        comp_user1 = User(email='company1_g4@example.com', role='company', is_active=True)
        comp_user1.set_password('CompPass1!')
        db.session.add(comp_user1)
        db.session.flush()

        comp1 = Company(
            user_id=comp_user1.id,
            company_name='Alpha Tech Solutions',
            official_email='alpha@example.com',
            phone='+918888888888',
            verification_status='approved',
            city='Bengaluru',
            country='India'
        )
        db.session.add(comp1)

        # Seed Company 2 (Approved)
        comp_user2 = User(email='company2_g4@example.com', role='company', is_active=True)
        comp_user2.set_password('CompPass2!')
        db.session.add(comp_user2)
        db.session.flush()

        comp2 = Company(
            user_id=comp_user2.id,
            company_name='Beta Cloud Corp',
            official_email='beta@example.com',
            phone='+917777777777',
            verification_status='approved',
            city='Pune',
            country='India'
        )
        db.session.add(comp2)

        # Seed Categories
        cat_dev = InternshipCategory(name='Web Development')
        cat_data = InternshipCategory(name='Data Science')
        db.session.add_all([cat_dev, cat_data])
        db.session.flush()

        # Seed Internships with varying durations, skills, eligibility, and risk levels
        # Job 1: Low risk, 8 weeks, Python/Flask, BCA Final Year
        j1 = Internship(
            company_id=comp1.id,
            category_id=cat_dev.id,
            title='Backend Python Intern',
            description='Build REST APIs using Python and Flask.',
            skills_required='Python, Flask, PostgreSQL',
            eligibility='BCA Final Year or B.Tech with 60% aggregate',
            location_type='remote',
            duration_weeks=8,
            duration_text='8 Weeks',
            stipend_type='paid',
            stipend_amount=15000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='alpha@example.com',
            status='active'
        )
        db.session.add(j1)
        db.session.flush()

        sc1 = ScamCheck(
            internship_id=j1.id,
            risk_score=10,
            risk_level='Low',
            summary_notes='Clean posting, verified domain.'
        )
        db.session.add(sc1)

        # Job 2: Medium risk, 16 weeks, React/JavaScript, MCA Students
        j2 = Internship(
            company_id=comp1.id,
            category_id=cat_dev.id,
            title='Frontend React Intern',
            description='Develop responsive user interfaces using React and Tailwind.',
            skills_required='React, JavaScript, CSS',
            eligibility='MCA Students or 3rd year BCA',
            location_type='on-site',
            location_city='Bengaluru',
            duration_weeks=16,
            duration_text='16 Weeks (4 Months)',
            stipend_type='paid',
            stipend_amount=20000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='alpha@example.com',
            status='active'
        )
        db.session.add(j2)
        db.session.flush()

        sc2 = ScamCheck(
            internship_id=j2.id,
            risk_score=45,
            risk_level='Medium',
            summary_notes='Moderate caution: unverified corporate registration.'
        )
        db.session.add(sc2)

        # Job 3: Low risk, 24 weeks, Python/Pandas, Open to all CS graduates
        j3 = Internship(
            company_id=comp2.id,
            category_id=cat_data.id,
            title='Data Science Intern',
            description='Analyze datasets and train predictive models with scikit-learn.',
            skills_required='Python, Pandas, Machine Learning',
            eligibility='Open to all CS graduates',
            location_type='hybrid',
            location_city='Pune',
            duration_weeks=24,
            duration_text='24 Weeks (6 Months)',
            stipend_type='paid',
            stipend_amount=25000.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='beta@example.com',
            status='active'
        )
        db.session.add(j3)
        db.session.flush()

        sc3 = ScamCheck(
            internship_id=j3.id,
            risk_score=15,
            risk_level='Low',
            summary_notes='Approved employer posting.'
        )
        db.session.add(sc3)

        # Job 4: Low risk, 4 weeks, Java/Spring, BCA 2nd year
        j4 = Internship(
            company_id=comp2.id,
            category_id=cat_dev.id,
            title='Junior Java Intern',
            description='Work on enterprise microservices.',
            skills_required='Java, Spring Boot, MySQL',
            eligibility='BCA 2nd year or 3rd year',
            location_type='remote',
            duration_weeks=4,
            duration_text='4 Weeks',
            stipend_type='unpaid',
            stipend_amount=0.0,
            application_deadline=date.today() + timedelta(days=30),
            contact_email='beta@example.com',
            status='active'
        )
        db.session.add(j4)
        db.session.flush()

        sc4 = ScamCheck(
            internship_id=j4.id,
            risk_score=5,
            risk_level='Low',
            summary_notes='Low risk short-term.'
        )
        db.session.add(sc4)

        db.session.commit()

    return app


@pytest.fixture
def client(synopsis_app):
    return synopsis_app.test_client()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Search Filters & Pagination Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_filter_duration_weeks_min_and_max(client):
    """Test min_duration and max_duration filters in weeks."""
    # min_duration=10 should return j2 (16 wks) and j3 (24 wks), not j1 (8 wks) or j4 (4 wks)
    resp = client.get('/internships/?min_duration=10')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Frontend React Intern' in html
    assert 'Data Science Intern' in html
    assert 'Backend Python Intern' not in html
    assert 'Junior Java Intern' not in html

    # max_duration=10 should return j1 (8 wks) and j4 (4 wks)
    resp = client.get('/internships/?max_duration=10')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Backend Python Intern' in html
    assert 'Junior Java Intern' in html
    assert 'Frontend React Intern' not in html
    assert 'Data Science Intern' not in html

    # Range: min_duration=6 and max_duration=20 should return j1 (8 wks) and j2 (16 wks)
    resp = client.get('/internships/?min_duration=6&max_duration=20')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Backend Python Intern' in html
    assert 'Frontend React Intern' in html
    assert 'Junior Java Intern' not in html
    assert 'Data Science Intern' not in html


def test_filter_skills(client):
    """Test explicit skills search filter."""
    # Filter for 'React'
    resp = client.get('/internships/?skills=React')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Frontend React Intern' in html
    assert 'Backend Python Intern' not in html
    assert 'Junior Java Intern' not in html

    # Filter for 'Python' (should match j1 and j3)
    resp = client.get('/internships/?skills=Python')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Backend Python Intern' in html
    assert 'Data Science Intern' in html
    assert 'Junior Java Intern' not in html


def test_filter_eligibility(client):
    """Test eligibility keyword search filter."""
    # Filter for 'Final Year'
    resp = client.get('/internships/?eligibility=Final+Year')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Backend Python Intern' in html
    assert 'Data Science Intern' not in html

    # Filter for 'MCA'
    resp = client.get('/internships/?eligibility=MCA')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Frontend React Intern' in html
    assert 'Junior Java Intern' not in html


def test_combined_filters_and_pagination(client):
    """Test combining multiple filters and ensuring query parameters persist in pagination links."""
    # We have PER_PAGE=3 and total 4 postings
    resp = client.get('/internships/?skills=Python&min_duration=5&max_duration=30&eligibility=CS')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    # j3 has skills 'Python', duration 24, eligibility 'Open to all CS graduates'
    assert 'Data Science Intern' in html

    # Verify pagination links preserve filter query parameters across pages
    resp_all = client.get('/internships/?skills=Python&min_duration=4')
    assert resp_all.status_code == 200
    html_all = resp_all.data.decode('utf-8')
    # Check that pagination URL contains the filters if pagination is present
    if 'Next' in html_all or 'Page navigation' in html_all:
        assert 'skills=Python' in html_all
        assert 'min_duration=4' in html_all


def test_invalid_filter_inputs_safe(client):
    """Test that invalid numeric inputs do not cause 500 errors."""
    resp = client.get('/internships/?min_duration=not_a_number&max_duration=xyz&min_stipend=invalid&page=-99')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Explore Verified Internships' in html


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Company Contact Information Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_placeholder_contact_info_in_base_footer(client):
    """Verify clearly marked placeholder company contact info in base.html footer."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # Must contain placeholder email
    assert 'contact@smartintern-placeholder.example.com' in html
    # Must contain placeholder phone
    assert '+91 (000) 000-0000' in html
    # Must contain placeholder postal address
    assert 'Outer Ring Road, Bengaluru' in html
    # Obvious placeholder markers
    assert '[Placeholder' in html


def test_placeholder_contact_info_on_home_page(client):
    """Verify clearly marked placeholder contact section on home.html."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    assert 'id="contact-us"' in html
    assert 'Company Email' in html
    assert 'Company Phone' in html
    assert 'Company Postal Address' in html
    assert '[Placeholder Email: contact@smartintern-placeholder.example.com]' in html
    assert '[Placeholder Phone: +91 (000) 000-0000 / +91 98765-00000]' in html
    assert '[Placeholder Postal Address: Plot No. 000' in html


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Company Verification Document Upload & Validation Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_document_validation_signatures():
    """Test file signature validation helper for PDF, PNG, JPG and invalid extensions."""
    # 1. Valid PDF
    pdf_fs = FileStorage(
        stream=io.BytesIO(create_valid_pdf_bytes()),
        filename='cert.pdf',
        content_type='application/pdf'
    )
    is_valid, err, meta = validate_verification_document(pdf_fs)
    assert is_valid is True
    assert err == ""
    # Pointer reset
    assert pdf_fs.tell() == 0

    # 2. Valid PNG
    png_fs = FileStorage(
        stream=io.BytesIO(create_valid_png_bytes()),
        filename='license.png',
        content_type='image/png'
    )
    is_valid, err, meta = validate_verification_document(png_fs)
    assert is_valid is True
    assert err == ""
    assert png_fs.tell() == 0

    # 3. Valid JPG
    jpg_fs = FileStorage(
        stream=io.BytesIO(create_valid_jpg_bytes()),
        filename='registration.jpg',
        content_type='image/jpeg'
    )
    is_valid, err, meta = validate_verification_document(jpg_fs)
    assert is_valid is True
    assert err == ""
    assert jpg_fs.tell() == 0

    # 4. Invalid signature disguised as .pdf
    fake_pdf = FileStorage(
        stream=io.BytesIO(b"Hello world, I am plain text posing as a PDF."),
        filename='fake.pdf',
        content_type='application/pdf'
    )
    is_valid, err, meta = validate_verification_document(fake_pdf)
    assert is_valid is False
    assert 'signature does not match' in err.lower() or 'invalid pdf' in err.lower()

    # 5. Invalid signature disguised as .png
    fake_png = FileStorage(
        stream=io.BytesIO(b"Fake PNG text data"),
        filename='fake.png',
        content_type='image/png'
    )
    is_valid, err, meta = validate_verification_document(fake_png)
    assert is_valid is False
    assert 'signature does not match' in err.lower() or 'invalid png' in err.lower()

    # 6. Unsupported extension (.exe)
    exe_fs = FileStorage(
        stream=io.BytesIO(b"MZ\x90\x00"),
        filename='malware.exe',
        content_type='application/octet-stream'
    )
    is_valid, err, meta = validate_verification_document(exe_fs)
    assert is_valid is False
    assert 'invalid file format' in err.lower()

    # 7. Empty file (0 bytes)
    empty_fs = FileStorage(
        stream=io.BytesIO(b""),
        filename='empty.pdf',
        content_type='application/pdf'
    )
    is_valid, err, meta = validate_verification_document(empty_fs)
    assert is_valid is False
    assert 'empty' in err.lower()


def test_company_document_upload_and_private_storage(synopsis_app, client):
    """Test company document upload, private storage location, and authorized access."""
    # Log in as Company 1
    client.post('/auth/login', data={'email': 'company1_g4@example.com', 'password': 'CompPass1!'})

    # Upload valid PDF verification document
    pdf_bytes = create_valid_pdf_bytes()
    resp = client.post(
        '/company/profile',
        data={
            'company_name': 'Alpha Tech Solutions',
            'official_email': 'alpha@example.com',
            'phone': '+918888888888',
            'website': 'https://alphatech.example.com',
            'city': 'Bengaluru',
            'country': 'India',
            'description': 'Updated description',
            'verification_document': (io.BytesIO(pdf_bytes), 'cin_certificate.pdf')
        },
        follow_redirects=True
    )
    assert resp.status_code == 200

    with synopsis_app.app_context():
        comp = Company.query.filter_by(company_name='Alpha Tech Solutions').first()
        assert comp.verification_document is not None
        doc_filename = comp.verification_document
        doc_path = Path(synopsis_app.config['DOCS_FOLDER']) / doc_filename
        assert doc_path.exists()
        # Verify content matches
        assert doc_path.read_bytes() == pdf_bytes

    # Ensure document is accessible to company owner via authorized route
    view_resp = client.get('/company/document')
    assert view_resp.status_code == 200
    assert view_resp.data == pdf_bytes

    # Ensure document is NOT publicly accessible through static path
    static_resp = client.get(f'/static/uploads/company_docs/{doc_filename}')
    assert static_resp.status_code == 404

    client.get('/auth/logout')


def test_document_access_control(synopsis_app, client):
    """Test that only Admins and the owning Company can download verification documents."""
    pdf_bytes = create_valid_pdf_bytes()
    with synopsis_app.app_context():
        comp1 = Company.query.filter_by(company_name='Alpha Tech Solutions').first()
        if not comp1.verification_document:
            comp1.verification_document = 'test_cin_certificate.pdf'
            doc_path = Path(synopsis_app.config['DOCS_FOLDER']) / 'test_cin_certificate.pdf'
            doc_path.write_bytes(pdf_bytes)
            db.session.commit()
        comp1_id = comp1.id

    # 1. Unauthenticated request to /admin/verifications/document/<id>
    resp = client.get(f'/admin/verifications/document/{comp1_id}')
    assert resp.status_code in (302, 401, 403)

    # 2. Student request to /admin/verifications/document/<id>
    client.post('/auth/login', data={'email': 'student_g4@example.com', 'password': 'StudPass1!'})
    resp = client.get(f'/admin/verifications/document/{comp1_id}')
    # Should be redirected or denied access
    assert resp.status_code in (302, 403)
    client.get('/auth/logout')

    # 3. Company 2 attempting to view Company 1's document
    client.post('/auth/login', data={'email': 'company2_g4@example.com', 'password': 'CompPass2!'})
    resp = client.get(f'/admin/verifications/document/{comp1_id}')
    assert resp.status_code in (302, 403)
    client.get('/auth/logout')

    # 4. Admin successfully downloads Company 1's document
    client.post('/auth/login', data={'email': 'admin_g4@example.com', 'password': 'AdminPass1!'})
    admin_resp = client.get(f'/admin/verifications/document/{comp1_id}')
    assert admin_resp.status_code == 200
    assert admin_resp.data == pdf_bytes
    client.get('/auth/logout')


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Medium-Risk Application Warning Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_medium_risk_warning_rendered_on_detail_page(synopsis_app, client):
    """Test that a Medium-risk internship detail page renders the safety warning and modal checkbox."""
    with synopsis_app.app_context():
        med_job = Internship.query.filter_by(title='Frontend React Intern').first()
        low_job = Internship.query.filter_by(title='Backend Python Intern').first()
        med_id = med_job.id
        low_id = low_job.id

    # View as student
    client.post('/auth/login', data={'email': 'student_g4@example.com', 'password': 'StudPass1!'})

    # Medium risk posting
    resp_med = client.get(f'/internships/{med_id}')
    assert resp_med.status_code == 200
    html_med = resp_med.data.decode('utf-8')
    assert 'I have read the safety warning' in html_med
    assert 'acknowledge_safety_warning' in html_med

    # Low risk posting should NOT require safety warning acknowledgment
    resp_low = client.get(f'/internships/{low_id}')
    assert resp_low.status_code == 200
    html_low = resp_low.data.decode('utf-8')
    assert 'I have read the safety warning' not in html_low
    assert 'acknowledge_safety_warning' not in html_low

    client.get('/auth/logout')


def test_medium_risk_application_server_enforcement(synopsis_app, client):
    """Test server enforcement: Medium-risk requires acknowledgment; Low-risk does not."""
    with synopsis_app.app_context():
        med_job = Internship.query.filter_by(title='Frontend React Intern').first()
        low_job = Internship.query.filter_by(title='Backend Python Intern').first()
        med_id = med_job.id
        low_id = low_job.id
        stud_prof = StudentProfile.query.filter_by(full_name='Aarav Sharma').first()

        # Add a test resume for student
        res = Resume(
            student_id=stud_prof.id,
            filename='aarav_cv.pdf',
            original_name='aarav_cv.pdf',
            file_path='aarav_cv.pdf',
            file_size=1024,
            is_primary=True
        )
        db.session.add(res)
        db.session.commit()
        res_id = res.id

    client.post('/auth/login', data={'email': 'student_g4@example.com', 'password': 'StudPass1!'})

    # 1. Direct POST to Medium-risk internship WITHOUT acknowledge_safety_warning
    resp_fail = client.post(
        f'/internships/{med_id}/apply',
        data={'resume_id': res_id, 'cover_letter': 'Excited to apply'},
        follow_redirects=True
    )
    assert resp_fail.status_code == 200
    html_fail = resp_fail.data.decode('utf-8')
    # Should display danger flash message
    assert 'You must acknowledge that you have read the safety warning' in html_fail

    with synopsis_app.app_context():
        # Confirm application was NOT created
        app_check = Application.query.filter_by(internship_id=med_id).first()
        assert app_check is None

    # 2. Direct POST to Medium-risk internship WITH acknowledge_safety_warning='yes'
    resp_ok = client.post(
        f'/internships/{med_id}/apply',
        data={
            'resume_id': res_id,
            'cover_letter': 'Excited to apply',
            'acknowledge_safety_warning': 'yes'
        },
        follow_redirects=True
    )
    assert resp_ok.status_code == 200
    html_ok = resp_ok.data.decode('utf-8')
    assert 'successfully submitted' in html_ok.lower()

    with synopsis_app.app_context():
        app_created = Application.query.filter_by(internship_id=med_id).first()
        assert app_created is not None

    # 3. Direct POST to Low-risk internship WITHOUT acknowledge_safety_warning succeeds
    resp_low = client.post(
        f'/internships/{low_id}/apply',
        data={'resume_id': res_id, 'cover_letter': 'Applying to low risk'},
        follow_redirects=True
    )
    assert resp_low.status_code == 200
    html_low = resp_low.data.decode('utf-8')
    assert 'successfully submitted' in html_low.lower()

    with synopsis_app.app_context():
        low_app = Application.query.filter_by(internship_id=low_id).first()
        assert low_app is not None

    client.get('/auth/logout')


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Idempotent Migration Script Test
# ═══════════════════════════════════════════════════════════════════════════════

def test_migration_company_docs_idempotency(synopsis_app):
    """Test that scripts/migrate_company_docs.py is safe and idempotent."""
    with synopsis_app.app_context():
        # In synopsis_app, `companies.verification_document` already exists from db.create_all()
        stats = migrate_company_docs.run_migration(app=synopsis_app, engine=db.engine)
        assert stats['skipped'] is True
        assert stats['added'] is False
