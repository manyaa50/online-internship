"""
tests/test_private_resumes.py
=============================
Comprehensive test suite for Group 2 (Private Resumes):
  1. Private resume storage configuration (outside app/static).
  2. Public static URL access rejection (404 on /static/uploads/resumes/...).
  3. Valid PDF signature (%PDF) validation.
  4. Valid DOCX signature (PK / ZIP) validation.
  5. Invalid file signature with valid extension (.pdf / .docx) rejection.
  6. Unsupported file extensions rejection.
  7. Empty file (0 bytes) rejection.
  8. File pointer reset after validation.
  9. Authorized vs unauthorized resume downloads (Owner, Admin, Authorized Company,
     Unauthorized Student, Unauthorized Company, Unauthenticated).
  10. 413 Payload Too Large error handling (friendly message, no stack trace).
  11. Migration script (scripts/migrate_resumes.py) functionality, collision handling,
      and idempotency.
"""
import io
import os
import shutil
import tempfile
import zipfile
import pytest
from pathlib import Path
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config import Config
from app.models import db, User, StudentProfile, Resume, Company, Internship, InternshipCategory, Application
from app.utils import validate_resume_upload
from scripts import migrate_resumes


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def create_valid_pdf_bytes():
    return b"%PDF-1.4\n1 0 obj\n<< /Title (Test Resume) >>\nendobj\ntrailer\n<<>>\n%%EOF"


def create_valid_docx_bytes():
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
        zf.writestr('word/document.xml', '<?xml version="1.0"?><document>Test</document>')
    return bio.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='session')
def private_resume_app(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp('private_storage')
    resumes_dir = temp_dir / 'instance' / 'uploads' / 'resumes'
    resumes_dir.mkdir(parents=True, exist_ok=True)

    class TestPrivateConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'test-private-key'
        SERVER_NAME = 'localhost'
        RESUME_FOLDER = str(resumes_dir)
        MAX_CONTENT_LENGTH = 1024 * 1024  # 1 MB for testing

    application = create_app(TestPrivateConfig)

    with application.app_context():
        db.create_all()

        # Seed Admin
        admin = User(email='admin_priv@example.com', role='admin', is_active=True)
        admin.set_password('AdminPass1!')
        db.session.add(admin)

        # Seed Student A (Owner)
        student_a_user = User(email='student_a@example.com', role='student', is_active=True)
        student_a_user.set_password('Pass1!')
        db.session.add(student_a_user)
        db.session.flush()
        student_a = StudentProfile(user_id=student_a_user.id, full_name='Student A', phone='9000000001')
        db.session.add(student_a)
        db.session.flush()

        # Student A's physical resume in private storage
        resume_a_filename = 'resume_student_a_12345.pdf'
        with open(resumes_dir / resume_a_filename, 'wb') as f:
            f.write(create_valid_pdf_bytes())

        resume_a = Resume(
            student_id=student_a.id,
            filename=resume_a_filename,
            original_name='StudentA_Resume.pdf',
            file_path=f"instance/uploads/resumes/{resume_a_filename}",
            file_size=len(create_valid_pdf_bytes()),
            is_primary=True
        )
        db.session.add(resume_a)

        # Seed Student B (Unrelated Student)
        student_b_user = User(email='student_b@example.com', role='student', is_active=True)
        student_b_user.set_password('Pass1!')
        db.session.add(student_b_user)
        db.session.flush()
        student_b = StudentProfile(user_id=student_b_user.id, full_name='Student B', phone='9000000002')
        db.session.add(student_b)

        # Seed Company A (Target Company)
        comp_a_user = User(email='comp_a@example.com', role='company', is_active=True)
        comp_a_user.set_password('Pass1!')
        db.session.add(comp_a_user)
        db.session.flush()
        comp_a = Company(
            user_id=comp_a_user.id, company_name='Target Company A',
            official_email='comp_a@example.com', phone='9000000003', verification_status='approved'
        )
        db.session.add(comp_a)
        db.session.flush()

        # Seed Company B (Unrelated Company)
        comp_b_user = User(email='comp_b@example.com', role='company', is_active=True)
        comp_b_user.set_password('Pass1!')
        db.session.add(comp_b_user)
        db.session.flush()
        comp_b = Company(
            user_id=comp_b_user.id, company_name='Other Company B',
            official_email='comp_b@example.com', phone='9000000004', verification_status='approved'
        )
        db.session.add(comp_b)
        db.session.flush()

        # Category
        cat = InternshipCategory(name='General Tech', description='Tech roles', icon_class='bi bi-code')
        db.session.add(cat)
        db.session.flush()

        # Internship under Company A
        intern = Internship(
            company_id=comp_a.id, category_id=cat.id, title='Software Intern',
            description='Test description for intern', eligibility='BCA students',
            skills_required='Python', duration_text='3 Months', contact_email=comp_a.official_email,
            application_deadline=datetime_now_future(), status='active'
        )
        db.session.add(intern)
        db.session.flush()

        # Student A applies to Company A's internship with resume_a
        app_record = Application(
            internship_id=intern.id,
            student_id=student_a.id,
            resume_id=resume_a.id,
            status='Applied'
        )
        db.session.add(app_record)
        db.session.commit()

    yield application


def datetime_now_future():
    from datetime import date, timedelta
    return date.today() + timedelta(days=30)


@pytest.fixture()
def client(private_resume_app):
    return private_resume_app.test_client()


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests: Upload Validation & Signature Checking
# ═══════════════════════════════════════════════════════════════════════════════

def test_valid_pdf_signature():
    """Valid PDF content starting with %PDF is accepted."""
    pdf_data = create_valid_pdf_bytes()
    storage = FileStorage(stream=io.BytesIO(pdf_data), filename='resume.pdf')
    is_valid, msg, meta = validate_resume_upload(storage)

    assert is_valid is True
    assert msg == ""
    assert meta['ext'] == 'pdf'
    assert meta['original_name'] == 'resume.pdf'
    assert meta['file_size'] == len(pdf_data)


def test_valid_docx_signature():
    """Valid DOCX content starting with PK (ZIP archive) is accepted."""
    docx_data = create_valid_docx_bytes()
    storage = FileStorage(stream=io.BytesIO(docx_data), filename='my_cv.docx')
    is_valid, msg, meta = validate_resume_upload(storage)

    assert is_valid is True
    assert msg == ""
    assert meta['ext'] == 'docx'
    assert meta['original_name'] == 'my_cv.docx'
    assert meta['file_size'] == len(docx_data)


def test_invalid_signature_with_pdf_extension():
    """Spoofed file with .pdf extension but invalid signature is rejected."""
    fake_data = b"Hello, this is just plain text disguised as a PDF file."
    storage = FileStorage(stream=io.BytesIO(fake_data), filename='spoofed.pdf')
    is_valid, msg, meta = validate_resume_upload(storage)

    assert is_valid is False
    assert "Invalid PDF file" in msg
    assert meta is None


def test_invalid_signature_with_docx_extension():
    """Spoofed file with .docx extension but invalid signature is rejected."""
    fake_data = b"Hello, this is not a zip or PK file at all."
    storage = FileStorage(stream=io.BytesIO(fake_data), filename='spoofed.docx')
    is_valid, msg, meta = validate_resume_upload(storage)

    assert is_valid is False
    assert "Invalid DOCX file" in msg
    assert meta is None


def test_unsupported_extensions():
    """Files with unsupported extensions are rejected regardless of content."""
    for bad_name in ['virus.exe', 'script.sh', 'photo.png', 'text.txt', 'archive.tar']:
        storage = FileStorage(stream=io.BytesIO(b"%PDF-valid-signature"), filename=bad_name)
        is_valid, msg, meta = validate_resume_upload(storage)
        assert is_valid is False
        assert "Invalid file format" in msg or "Allowed formats" in msg


def test_empty_files():
    """0-byte files with valid extensions are rejected."""
    for empty_name in ['empty.pdf', 'empty.docx']:
        storage = FileStorage(stream=io.BytesIO(b""), filename=empty_name)
        is_valid, msg, meta = validate_resume_upload(storage)
        assert is_valid is False
        assert "empty" in msg.lower()


def test_upload_pointer_reset():
    """File storage pointer is always reset to 0 after validation checks."""
    test_cases = [
        (b"%PDF-1.4\nsome content", 'resume.pdf'),
        (create_valid_docx_bytes(), 'resume.docx'),
        (b"Not a real PDF", 'fake.pdf'),
        (b"Not a real docx", 'fake.docx'),
        (b"", 'empty.pdf'),
    ]
    for data, fname in test_cases:
        stream = io.BytesIO(data)
        storage = FileStorage(stream=stream, filename=fname)
        validate_resume_upload(storage)
        assert storage.tell() == 0, f"Pointer not reset for {fname}"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests: Private Storage & Access Control
# ═══════════════════════════════════════════════════════════════════════════════

def test_private_storage_configuration(private_resume_app):
    """Resume folder is strictly outside app/static and within instance directory."""
    resume_folder = private_resume_app.config['RESUME_FOLDER']
    static_folder = private_resume_app.static_folder

    assert 'static' not in Path(resume_folder).parts
    assert 'instance' in Path(resume_folder).parts
    assert 'resumes' in Path(resume_folder).parts
    assert not resume_folder.startswith(static_folder)


def test_resumes_not_accessible_via_static_url(client):
    """Resumes must return 404 if accessed via the public /static/ route."""
    response = client.get('/static/uploads/resumes/resume_student_a_12345.pdf')
    assert response.status_code == 404


def test_unauthenticated_cannot_download_resume(client, private_resume_app):
    """Unauthenticated access to resume download route redirects to login."""
    with private_resume_app.app_context():
        resume = Resume.query.first()
        res_id = resume.id

    client.post('/auth/logout')
    response = client.get(f'/student/resume/download/{res_id}')
    assert response.status_code == 302
    assert '/auth/login' in response.headers.get('Location', '')


def test_student_owner_can_download_resume(client, private_resume_app):
    """Owner student can download their own resume successfully."""
    with private_resume_app.app_context():
        resume = Resume.query.first()
        res_id = resume.id

    # Login as Student A (Owner)
    client.post('/auth/login', data={'email': 'student_a@example.com', 'password': 'Pass1!'})
    response = client.get(f'/student/resume/download/{res_id}')

    assert response.status_code == 200
    assert 'attachment' in response.headers.get('Content-Disposition', '')
    assert 'StudentA_Resume.pdf' in response.headers.get('Content-Disposition', '')
    assert response.data.startswith(b'%PDF')


def test_unauthorized_student_cannot_download_resume(client, private_resume_app):
    """Student B cannot download Student A's resume."""
    with private_resume_app.app_context():
        resume = Resume.query.first()
        res_id = resume.id

    # Login as Student B
    client.post('/auth/login', data={'email': 'student_b@example.com', 'password': 'Pass1!'})
    response = client.get(f'/student/resume/download/{res_id}', follow_redirects=False)

    # Must not receive the file (redirects or forbidden)
    assert response.status_code in (302, 403)
    assert response.data != create_valid_pdf_bytes()


def test_authorized_company_can_download_applicant_resume(client, private_resume_app):
    """Company A (where student applied) can download the resume."""
    with private_resume_app.app_context():
        resume = Resume.query.first()
        res_id = resume.id

    # Login as Company A
    client.post('/auth/login', data={'email': 'comp_a@example.com', 'password': 'Pass1!'})
    response = client.get(f'/student/resume/download/{res_id}')

    assert response.status_code == 200
    assert 'attachment' in response.headers.get('Content-Disposition', '')
    assert response.data.startswith(b'%PDF')


def test_unauthorized_company_cannot_download_resume(client, private_resume_app):
    """Company B (where student never applied) cannot download the resume."""
    with private_resume_app.app_context():
        resume = Resume.query.first()
        res_id = resume.id

    # Login as Company B
    client.post('/auth/login', data={'email': 'comp_b@example.com', 'password': 'Pass1!'})
    response = client.get(f'/student/resume/download/{res_id}', follow_redirects=False)

    assert response.status_code in (302, 403)
    assert response.data != create_valid_pdf_bytes()


def test_admin_can_download_any_resume(client, private_resume_app):
    """Administrator can download any resume for auditing."""
    with private_resume_app.app_context():
        resume = Resume.query.first()
        res_id = resume.id

    # Login as Admin
    client.post('/auth/login', data={'email': 'admin_priv@example.com', 'password': 'AdminPass1!'})
    response = client.get(f'/student/resume/download/{res_id}')

    assert response.status_code == 200
    assert 'attachment' in response.headers.get('Content-Disposition', '')
    assert response.data.startswith(b'%PDF')


def test_missing_physical_file_returns_404(client, private_resume_app):
    """If resume record exists in DB but file was removed from disk, return 404."""
    with private_resume_app.app_context():
        student = StudentProfile.query.first()
        ghost_resume = Resume(
            student_id=student.id,
            filename='ghost_file_does_not_exist.pdf',
            original_name='ghost.pdf',
            file_path='instance/uploads/resumes/ghost_file_does_not_exist.pdf',
            file_size=100
        )
        db.session.add(ghost_resume)
        db.session.commit()
        ghost_id = ghost_resume.id

    client.post('/auth/login', data={'email': 'admin_priv@example.com', 'password': 'AdminPass1!'})
    response = client.get(f'/student/resume/download/{ghost_id}')
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Payload Too Large (413) Handling Test
# ═══════════════════════════════════════════════════════════════════════════════

def test_payload_too_large_413_handler(client):
    """413 Request Entity Too Large error renders a friendly page without tracebacks."""
    # Login as student so request proceeds to form parsing
    client.post('/auth/login', data={'email': 'student_a@example.com', 'password': 'Pass1!'})

    # Post data exceeding MAX_CONTENT_LENGTH (configured to 1MB in private_resume_app)
    large_payload = {'resume_file': (io.BytesIO(b"A" * (2 * 1024 * 1024)), 'large.pdf')}
    response = client.post('/student/resume/upload', data=large_payload, content_type='multipart/form-data')

    assert response.status_code == 413
    assert b"413" in response.data
    assert b"File Too Large" in response.data or b"exceeds the allowed" in response.data
    assert b"Traceback" not in response.data


# ═══════════════════════════════════════════════════════════════════════════════
# Resume Migration Script Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_migrate_resumes_script_functionality(tmp_path):
    """Tests scripts/migrate_resumes.py file moving, collision safety, and idempotency."""
    src_dir = tmp_path / 'static_resumes'
    dest_dir = tmp_path / 'instance_resumes'
    src_dir.mkdir(parents=True)
    dest_dir.mkdir(parents=True)

    # 1. Create source test files
    valid_pdf = src_dir / 'candidate1.pdf'
    valid_pdf.write_bytes(create_valid_pdf_bytes())

    keep_file = src_dir / '.gitkeep'
    keep_file.write_text('')

    # Run 1: Should move candidate1.pdf and leave .gitkeep
    stats1 = migrate_resumes.migrate_resumes(src_dir=str(src_dir), dest_dir=str(dest_dir))
    assert len(stats1['moved']) == 1
    assert stats1['moved'][0][0] == 'candidate1.pdf'
    assert (dest_dir / 'candidate1.pdf').exists()
    assert not valid_pdf.exists()
    assert keep_file.exists()

    # Run 2: Repeated run should safely skip
    stats2 = migrate_resumes.migrate_resumes(src_dir=str(src_dir), dest_dir=str(dest_dir))
    assert len(stats2['moved']) == 0

    # Collision test: add new file with same name but different content at source
    colliding_pdf = src_dir / 'candidate1.pdf'
    colliding_pdf.write_bytes(b"%PDF-DIFFERENT-CONTENT-TEST")

    stats3 = migrate_resumes.migrate_resumes(src_dir=str(src_dir), dest_dir=str(dest_dir))
    assert len(stats3['collisions_resolved']) == 1
    assert stats3['collisions_resolved'][0][0] == 'candidate1.pdf'
    assert not colliding_pdf.exists()

    # Both copies must exist in destination without overwriting
    dest_files = [f.name for f in dest_dir.iterdir()]
    assert 'candidate1.pdf' in dest_files
    assert len(dest_files) == 2
