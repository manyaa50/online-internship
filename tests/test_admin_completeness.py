"""
tests/test_admin_completeness.py
================================
Comprehensive test suite for Group 3 (Admin Completeness):
  1. Company appeals authorization (admin-only).
  2. Valid appeal approve transition (internship -> active, scam_check -> reviewed & approved, company notified).
  3. Valid appeal reject transition (internship -> rejected, scam_check -> reviewed & rejected, company and students notified).
  4. Duplicate / invalid appeal resolution prevention (already-reviewed appeals rejected).
  5. Flagged review synchronization with pending appeals.
  6. Company moderation cascade: blocking company user sets active postings to 'closed' and notifies students.
  7. Company moderation cascade: revoking company verification sets active postings to 'closed' and notifies students.
  8. Prevention of unintended student notifications (only affected applicants notified, no duplicate pairs).
  9. Admin permission checks & self-block protection.
  10. Public listing protection: unapproved company postings excluded from /internships/.
  11. Public listing protection: blocked/inactive company user postings excluded from /internships/.
  12. Public listing protection: non-active postings excluded from /internships/.
  13. Home page protection: featured internships filter unapproved companies, inactive users, and non-active postings.
  14. Direct URL access protection: detail page returns 404 for ineligible postings to students and guests.
  15. Direct URL access allowance: admin and owning company can view detail page of ineligible postings.
  16. Application refusal on ineligible postings (returns 404).
  17. System Information page: authorization (admin-only), core model totals, risk counts, report status counts,
      and recent admin actions audit log.
  18. Automatic flagging: posting reaches >= 3 open reports transitions to 'flagged' and notifies admin once.
  19. Automatic flagging: subsequent reports (>= 4) do not send duplicate auto-flagging notifications.
"""
from datetime import datetime, date, timedelta, timezone
import pytest
from app import create_app
from app.config import Config
from app.models import (
    db, User, Admin, StudentProfile, Company, CompanyVerification,
    Internship, InternshipCategory, ScamCheck, ScamReport, Notification, Application, Resume
)


# ═══════════════════════════════════════════════════════════════════════════════
# Test Application Fixture
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='function')
def app():
    """Create test application with in-memory SQLite database for each test."""
    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SECRET_KEY = 'test-secret-key-admin-group3'
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
    u = User(email=email, role=role, is_active=is_active)
    u.set_password(password)
    db.session.add(u)
    db.session.flush()
    return u


def create_admin(email='admin@smartintern.org'):
    u = create_user(email, role='admin')
    adm = Admin(user_id=u.id, full_name='Platform Admin', phone='9876543210')
    db.session.add(adm)
    db.session.flush()
    return u, adm


def create_student(email='student@smartintern.org', full_name='Alice Student'):
    u = create_user(email, role='student')
    s = StudentProfile(user_id=u.id, full_name=full_name, phone='9876543211')
    db.session.add(s)
    db.session.flush()

    res = Resume(
        student_id=s.id,
        filename='alice_resume.pdf',
        original_name='alice_resume.pdf',
        file_path='instance/uploads/resumes/alice_resume.pdf',
        file_size=1024,
        is_primary=True
    )
    db.session.add(res)
    db.session.flush()
    return u, s, res


def create_company(email='company@smartintern.org', name='Acme Corp', verification_status='approved', is_active=True):
    u = create_user(email, role='company', is_active=is_active)
    c = Company(
        user_id=u.id,
        company_name=name,
        official_email=email,
        phone='9876543212',
        verification_status=verification_status
    )
    db.session.add(c)
    db.session.flush()
    return u, c


def create_category(name='Software Engineering'):
    cat = InternshipCategory.query.filter_by(name=name).first()
    if not cat:
        cat = InternshipCategory(name=name, description='Engineering roles')
        db.session.add(cat)
        db.session.flush()
    return cat


def create_internship(company, category=None, title='Software Engineer Intern', status='active', risk_score=20, risk_level='Low'):
    if not category:
        category = create_category()

    intern = Internship(
        company_id=company.id,
        category_id=category.id,
        title=title,
        description='Exciting software engineering role with great mentorship.',
        eligibility='BCA/MCA/BTech',
        skills_required='Python, Flask, SQL',
        duration_weeks=12,
        duration_text='3 Months',
        location_type='remote',
        stipend_type='paid',
        stipend_amount=15000.0,
        application_deadline=date.today() + timedelta(days=30),
        contact_email=company.official_email,
        status=status
    )
    db.session.add(intern)
    db.session.flush()

    check = ScamCheck(
        internship_id=intern.id,
        risk_score=risk_score,
        risk_level=risk_level,
        triggered_rules='[]',
        disclaimer='Automated rule-based risk assessment. This result is not proof of fraud or legitimacy.',
        admin_verdict='pending',
        appeal_status='none'
    )
    db.session.add(check)
    db.session.flush()
    return intern, check


def login(client, email, password='Password123!'):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════════════

def test_appeal_authorization_requires_admin(app, client):
    """Anonymous, student, and company users cannot resolve appeals."""
    with app.app_context():
        admin_u, _ = create_admin()
        stud_u, stud_p, _ = create_student()
        comp_u, comp = create_company()
        intern, check = create_internship(comp, status='flagged', risk_score=75, risk_level='High')
        check.appeal_note = "Valid company registration documents provided."
        check.appeal_submitted_at = datetime.now(timezone.utc)
        check.appeal_status = 'pending'
        db.session.commit()
        intern_id = intern.id

    # 1. Anonymous user redirected to login
    resp = client.post(f'/admin/appeals/{intern_id}/approve')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']

    # 2. Student user rejected (redirected with access denied or 403 with JSON)
    login(client, 'student@smartintern.org')
    resp = client.post(f'/admin/appeals/{intern_id}/approve', follow_redirects=True)
    assert resp.status_code == 200
    assert b"Access denied" in resp.data

    resp_json = client.post(f'/admin/appeals/{intern_id}/approve', headers={'Accept': 'application/json'})
    assert resp_json.status_code == 403

    # 3. Company user rejected
    client.post('/auth/logout')
    login(client, 'company@smartintern.org')
    resp = client.post(f'/admin/appeals/{intern_id}/approve', follow_redirects=True)
    assert resp.status_code == 200
    assert b"Access denied" in resp.data

    resp_json = client.post(f'/admin/appeals/{intern_id}/approve', headers={'Accept': 'application/json'})
    assert resp_json.status_code == 403


def test_valid_appeal_approval(app, client):
    """Admin approves pending appeal: sets status active, appeal reviewed, company notified."""
    with app.app_context():
        create_admin()
        comp_u, comp = create_company()
        intern, check = create_internship(comp, status='flagged', risk_score=75, risk_level='High')
        check.appeal_note = "We mistakenly used external test keyword. Legit posting."
        check.appeal_submitted_at = datetime.now(timezone.utc)
        check.appeal_status = 'pending'
        db.session.commit()
        intern_id = intern.id
        comp_user_id = comp_u.id

    login(client, 'admin@smartintern.org')
    resp = client.post(f'/admin/appeals/{intern_id}/approve', data={'admin_notes': 'Verified genuine company documentation.'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        updated_intern = db.session.get(Internship, intern_id)
        assert updated_intern.status == 'active'
        assert updated_intern.scam_check.appeal_status == 'reviewed'
        assert updated_intern.scam_check.admin_verdict == 'approved'
        assert updated_intern.scam_check.is_reviewed_by_admin is True

        # Verify company received notification
        notif = Notification.query.filter_by(user_id=comp_user_id, category='admin').first()
        assert notif is not None
        assert "Appeal Approved" in notif.title


def test_valid_appeal_rejection(app, client):
    """Admin rejects pending appeal: sets status rejected, appeal reviewed, company and applicants notified."""
    with app.app_context():
        create_admin()
        comp_u, comp = create_company()
        stud_u, stud_p, resume = create_student()
        intern, check = create_internship(comp, status='flagged', risk_score=80, risk_level='High')
        check.appeal_note = "Please unflag this posting immediately."
        check.appeal_submitted_at = datetime.now(timezone.utc)
        check.appeal_status = 'pending'

        # Existing student application
        app_item = Application(internship_id=intern.id, student_id=stud_p.id, resume_id=resume.id, status='Applied')
        db.session.add(app_item)
        db.session.commit()
        intern_id = intern.id
        comp_user_id = comp_u.id
        stud_user_id = stud_u.id

    login(client, 'admin@smartintern.org')
    resp = client.post(f'/admin/appeals/{intern_id}/reject', data={'admin_notes': 'Violated upfront payment policy.'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        updated_intern = db.session.get(Internship, intern_id)
        assert updated_intern.status == 'rejected'
        assert updated_intern.scam_check.appeal_status == 'reviewed'
        assert updated_intern.scam_check.admin_verdict == 'rejected'

        # Verify company notification
        comp_notif = Notification.query.filter_by(user_id=comp_user_id, category='admin').first()
        assert comp_notif is not None
        assert "Appeal Rejected" in comp_notif.title

        # Verify student applicant notification
        stud_notif = Notification.query.filter_by(user_id=stud_user_id, category='admin').first()
        assert stud_notif is not None
        assert "Delisted" in stud_notif.title


def test_duplicate_and_invalid_appeal_resolution_prevented(app, client):
    """Already reviewed appeals cannot be resolved again; invalid actions are rejected."""
    with app.app_context():
        create_admin()
        comp_u, comp = create_company()
        intern, check = create_internship(comp, status='rejected', risk_score=75, risk_level='High')
        check.appeal_status = 'reviewed'  # already reviewed
        db.session.commit()
        intern_id = intern.id

    login(client, 'admin@smartintern.org')

    # Attempt to resolve an already-reviewed appeal
    resp = client.post(f'/admin/appeals/{intern_id}/approve', follow_redirects=True)
    assert resp.status_code == 200
    assert b"This appeal is not pending or has already been reviewed" in resp.data

    with app.app_context():
        # Status remains untouched
        updated_intern = db.session.get(Internship, intern_id)
        assert updated_intern.status == 'rejected'

    # Attempt invalid action
    resp2 = client.post(f'/admin/appeals/{intern_id}/invalidaction', follow_redirects=True)
    assert resp2.status_code == 200
    assert b"Invalid appeal action" in resp2.data


def test_flagged_internships_html_displays_appeal_info(app, client):
    """admin/flagged_internships.html renders appeal_note and appeal_submitted_at."""
    with app.app_context():
        create_admin()
        comp_u, comp = create_company()
        intern, check = create_internship(comp, status='flagged', risk_score=85, risk_level='High')
        check.appeal_note = "UniqueAppealNoteTestingString123"
        check.appeal_submitted_at = datetime(2026, 10, 21, 14, 30, 0, tzinfo=timezone.utc)
        check.appeal_status = 'pending'
        db.session.commit()

    login(client, 'admin@smartintern.org')
    resp = client.get('/admin/flagged-internships')
    assert resp.status_code == 200
    assert b"UniqueAppealNoteTestingString123" in resp.data
    assert b"2026-10-21" in resp.data
    assert b"Pending Review" in resp.data or b"Appeal Pending" in resp.data
    assert b"Approve Appeal &amp; Restore" in resp.data or b"Approve Appeal" in resp.data


def test_blocking_company_user_cascades_to_active_internships_and_notifies_students(app, client):
    """When company user is blocked, active internships are closed and applicant students are notified."""
    with app.app_context():
        create_admin()
        comp_u, comp = create_company()
        stud1_u, stud1_p, res1 = create_student('s1@test.org', 'Student One')
        stud2_u, stud2_p, res2 = create_student('s2@test.org', 'Student Two')
        stud_unrelated_u, stud_unrelated_p, res_unr = create_student('unr@test.org', 'Unrelated Student')

        # Company has 2 active internships and 1 already closed
        intern1, _ = create_internship(comp, title='Active Posting 1', status='active')
        intern2, _ = create_internship(comp, title='Active Posting 2', status='active')
        intern3, _ = create_internship(comp, title='Already Closed Posting', status='closed')

        # stud1 applied to intern1 and intern2; stud2 applied to intern1
        db.session.add(Application(internship_id=intern1.id, student_id=stud1_p.id, resume_id=res1.id, status='Applied'))
        db.session.add(Application(internship_id=intern2.id, student_id=stud1_p.id, resume_id=res1.id, status='Applied'))
        db.session.add(Application(internship_id=intern1.id, student_id=stud2_p.id, resume_id=res2.id, status='Applied'))

        # Another company with active posting (unrelated)
        comp_other_u, comp_other = create_company('other@smartintern.org', 'Other Corp')
        intern_other, _ = create_internship(comp_other, title='Other Active', status='active')
        db.session.add(Application(internship_id=intern_other.id, student_id=stud_unrelated_p.id, resume_id=res_unr.id, status='Applied'))

        db.session.commit()
        comp_user_id = comp_u.id
        intern1_id = intern1.id
        intern2_id = intern2.id
        intern3_id = intern3.id
        intern_other_id = intern_other.id
        stud1_uid = stud1_u.id
        stud2_uid = stud2_u.id
        stud_unr_uid = stud_unrelated_u.id

    login(client, 'admin@smartintern.org')
    resp = client.post(f'/admin/user/toggle-block/{comp_user_id}', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        # Company user is blocked
        user = db.session.get(User, comp_user_id)
        assert user.is_active is False

        # Active postings cascaded to 'closed'
        assert db.session.get(Internship, intern1_id).status == 'closed'
        assert db.session.get(Internship, intern2_id).status == 'closed'
        assert db.session.get(Internship, intern3_id).status == 'closed'

        # Other company posting unaffected
        assert db.session.get(Internship, intern_other_id).status == 'active'

        # Student 1 received notifications for intern1 and intern2
        s1_notifs = Notification.query.filter_by(user_id=stud1_uid, category='admin').all()
        assert len(s1_notifs) == 2

        # Student 2 received notification for intern1
        s2_notifs = Notification.query.filter_by(user_id=stud2_uid, category='admin').all()
        assert len(s2_notifs) == 1

        # Unrelated student did not receive any notification
        unr_notifs = Notification.query.filter_by(user_id=stud_unr_uid, category='admin').all()
        assert len(unr_notifs) == 0


def test_revoking_company_verification_cascades_to_active_internships(app, client):
    """When company verification is rejected, active internships are closed and applicant students notified."""
    with app.app_context():
        create_admin()
        comp_u, comp = create_company(verification_status='approved')
        stud_u, stud_p, res = create_student()
        intern, _ = create_internship(comp, title='Posting Under Review', status='active')
        db.session.add(Application(internship_id=intern.id, student_id=stud_p.id, resume_id=res.id, status='Applied'))
        db.session.commit()
        comp_id = comp.id
        intern_id = intern.id
        stud_uid = stud_u.id

    login(client, 'admin@smartintern.org')
    resp = client.post(f'/admin/verifications/{comp_id}/reject', data={'rejection_reason': 'Invalid registration document.'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        comp = db.session.get(Company, comp_id)
        assert comp.verification_status == 'rejected'

        intern = db.session.get(Internship, intern_id)
        assert intern.status == 'closed'

        notif = Notification.query.filter_by(user_id=stud_uid, category='admin').first()
        assert notif is not None
        assert "closed" in notif.message.lower()


def test_admin_cannot_block_own_account(app, client):
    """Admin cannot toggle their own account to blocked."""
    with app.app_context():
        admin_u, _ = create_admin()
        admin_uid = admin_u.id
        db.session.commit()

    login(client, 'admin@smartintern.org')
    resp = client.post(f'/admin/user/toggle-block/{admin_uid}', follow_redirects=True)
    assert resp.status_code == 200
    assert b"cannot block your own administrator account" in resp.data

    with app.app_context():
        admin_u = db.session.get(User, admin_uid)
        assert admin_u.is_active is True


def test_public_listing_excludes_unapproved_companies(app, client):
    """Public listing (/internships/) excludes internships from pending/rejected companies."""
    with app.app_context():
        approved_u, approved_c = create_company('approved@test.org', 'Approved Co', verification_status='approved')
        pending_u, pending_c = create_company('pending@test.org', 'Pending Co', verification_status='pending')
        rejected_u, rejected_c = create_company('rejected@test.org', 'Rejected Co', verification_status='rejected')

        intern_appr, _ = create_internship(approved_c, title='Approved Company Job', status='active')
        intern_pend, _ = create_internship(pending_c, title='Pending Company Job', status='active')
        intern_rej, _ = create_internship(rejected_c, title='Rejected Company Job', status='active')
        db.session.commit()

    resp = client.get('/internships/')
    assert resp.status_code == 200
    assert b"Approved Company Job" in resp.data
    assert b"Pending Company Job" not in resp.data
    assert b"Rejected Company Job" not in resp.data


def test_public_listing_excludes_inactive_blocked_company_users(app, client):
    """Public listing excludes internships from blocked/inactive company accounts."""
    with app.app_context():
        active_u, active_c = create_company('active@test.org', 'Active Co', is_active=True)
        blocked_u, blocked_c = create_company('blocked@test.org', 'Blocked Co', is_active=False)

        intern_act, _ = create_internship(active_c, title='Active Employer Role', status='active')
        intern_blk, _ = create_internship(blocked_c, title='Blocked Employer Role', status='active')
        db.session.commit()

    resp = client.get('/internships/')
    assert resp.status_code == 200
    assert b"Active Employer Role" in resp.data
    assert b"Blocked Employer Role" not in resp.data


def test_public_listing_excludes_non_active_statuses(app, client):
    """Public listing excludes flagged, closed, or rejected postings."""
    with app.app_context():
        comp_u, comp = create_company()
        create_internship(comp, title='Live Active Posting', status='active')
        create_internship(comp, title='Quarantined Flagged Posting', status='flagged')
        create_internship(comp, title='Old Closed Posting', status='closed')
        create_internship(comp, title='Delisted Rejected Posting', status='rejected')
        db.session.commit()

    resp = client.get('/internships/')
    assert resp.status_code == 200
    assert b"Live Active Posting" in resp.data
    assert b"Quarantined Flagged Posting" not in resp.data
    assert b"Old Closed Posting" not in resp.data
    assert b"Delisted Rejected Posting" not in resp.data


def test_home_page_excludes_ineligible_postings(app, client):
    """Home page featured internships exclude unapproved companies, inactive users, and non-active statuses."""
    with app.app_context():
        appr_u, appr_c = create_company('appr@test.org', 'Appr Co', verification_status='approved', is_active=True)
        pend_u, pend_c = create_company('pend@test.org', 'Pend Co', verification_status='pending', is_active=True)
        inact_u, inact_c = create_company('inact@test.org', 'Inact Co', verification_status='approved', is_active=False)

        create_internship(appr_c, title='Home Valid Internship', status='active')
        create_internship(pend_c, title='Home Pending Internship', status='active')
        create_internship(inact_c, title='Home Inactive User Internship', status='active')
        create_internship(appr_c, title='Home Flagged Internship', status='flagged')
        db.session.commit()

    resp = client.get('/')
    assert resp.status_code == 200
    assert b"Home Valid Internship" in resp.data
    assert b"Home Pending Internship" not in resp.data
    assert b"Home Inactive User Internship" not in resp.data
    assert b"Home Flagged Internship" not in resp.data


def test_direct_url_protection_detail_returns_404_for_ineligible_postings(app, client):
    """Direct URL access to ineligible postings returns 404 for guests, students, and other companies."""
    with app.app_context():
        comp_u, comp = create_company(verification_status='pending')
        intern_pend, _ = create_internship(comp, title='Private Pending Post', status='active')

        comp_appr_u, comp_appr = create_company('appr2@test.org', 'Appr Co 2', verification_status='approved')
        intern_flag, _ = create_internship(comp_appr, title='Private Flagged Post', status='flagged')

        stud_u, _, _ = create_student()
        comp_other_u, comp_other = create_company('other2@test.org', 'Other Co 2')
        admin_u, _ = create_admin()

        db.session.commit()
        pend_id = intern_pend.id
        flag_id = intern_flag.id

    # 1. Anonymous user gets 404
    assert client.get(f'/internships/{pend_id}').status_code == 404
    assert client.get(f'/internships/{flag_id}').status_code == 404

    # 2. Student user gets 404
    login(client, 'student@smartintern.org')
    assert client.get(f'/internships/{pend_id}').status_code == 404
    assert client.get(f'/internships/{flag_id}').status_code == 404
    client.post('/auth/logout')

    # 3. Unrelated company gets 404
    login(client, 'other2@smartintern.org')
    assert client.get(f'/internships/{pend_id}').status_code == 404
    assert client.get(f'/internships/{flag_id}').status_code == 404
    client.post('/auth/logout')

    # 4. Owning company CAN view their own ineligible posting
    login(client, 'company@smartintern.org')
    resp_owner = client.get(f'/internships/{pend_id}')
    assert resp_owner.status_code == 200
    assert b"Private Pending Post" in resp_owner.data
    client.post('/auth/logout')

    # 5. Admin CAN view any ineligible posting
    login(client, 'admin@smartintern.org')
    resp_admin = client.get(f'/internships/{flag_id}')
    assert resp_admin.status_code == 200
    assert b"Private Flagged Post" in resp_admin.data


def test_apply_route_refuses_ineligible_postings(app, client):
    """Students cannot apply to postings from unapproved companies or non-active postings (returns 404)."""
    with app.app_context():
        comp_u, comp = create_company(verification_status='pending')
        intern_pend, _ = create_internship(comp, title='Pending Apply Test', status='active')
        stud_u, _, resume = create_student()
        db.session.commit()
        intern_id = intern_pend.id
        resume_id = resume.id

    login(client, 'student@smartintern.org')
    resp = client.post(f'/internships/{intern_id}/apply', data={'resume_id': resume_id, 'cover_letter': 'Hello'})
    assert resp.status_code == 404

    with app.app_context():
        assert Application.query.filter_by(internship_id=intern_id).count() == 0


def test_system_info_requires_admin(app, client):
    """System information route requires admin authorization."""
    with app.app_context():
        create_admin()
        create_student()
        create_company()
        db.session.commit()

    # Anonymous -> 302 to login
    resp = client.get('/admin/system-info')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']

    # Student -> redirected with access denied (or 403 with JSON)
    login(client, 'student@smartintern.org')
    resp = client.get('/admin/system-info', follow_redirects=True)
    assert resp.status_code == 200
    assert b"Access denied" in resp.data

    resp_json = client.get('/admin/system-info', headers={'Accept': 'application/json'})
    assert resp_json.status_code == 403
    client.post('/auth/logout')

    # Company -> redirected with access denied
    login(client, 'company@smartintern.org')
    resp = client.get('/admin/system-info', follow_redirects=True)
    assert resp.status_code == 200
    assert b"Access denied" in resp.data

    resp_json = client.get('/admin/system-info', headers={'Accept': 'application/json'})
    assert resp_json.status_code == 403


def test_system_info_metrics_and_recent_actions(app, client):
    """System info calculates accurate metrics, risk breakdowns, report counts, and 10 recent actions."""
    with app.app_context():
        admin_u, admin_p = create_admin()
        stud_u, stud_p, res = create_student()
        comp_u, comp = create_company(verification_status='approved')

        # Internships with different risk levels
        i_low, _ = create_internship(comp, title='Low Risk Intern', risk_score=10, risk_level='Low')
        i_med, _ = create_internship(comp, title='Med Risk Intern', risk_score=45, risk_level='Medium')
        i_high, _ = create_internship(comp, title='High Risk Intern', risk_score=80, risk_level='High')

        # Application
        app_item = Application(internship_id=i_low.id, student_id=stud_p.id, resume_id=res.id, status='Applied')
        db.session.add(app_item)

        # Reports with different statuses
        r1 = ScamReport(reported_by_student_id=stud_p.id, internship_id=i_high.id, reason='Fake job', description='Fee demand', status='open')
        r2 = ScamReport(reported_by_student_id=stud_p.id, internship_id=i_med.id, reason='Sus link', description='Telegram link', status='investigating')
        r3 = ScamReport(reported_by_student_id=stud_p.id, internship_id=i_low.id, reason='Other', description='Minor typo', status='resolved', admin_resolution='Resolved as benign', resolved_at=datetime.now(timezone.utc))
        db.session.add_all([r1, r2, r3])

        # Admin actions: CompanyVerification log
        v_log = CompanyVerification(
            company_id=comp.id,
            admin_id=admin_p.id,
            status='approved',
            review_notes='Verified tax filings',
            reviewed_at=datetime.now(timezone.utc)
        )
        db.session.add(v_log)

        # Admin actions: ScamCheck reviewed by admin
        i_high.scam_check.is_reviewed_by_admin = True
        i_high.scam_check.admin_verdict = 'rejected'
        i_high.scam_check.admin_notes = 'High scam probability'

        db.session.commit()

    login(client, 'admin@smartintern.org')
    resp = client.get('/admin/system-info')
    assert resp.status_code == 200

    # Check that counts and action types are present in HTML
    assert b"System Information & Telemetry" in resp.data
    assert b"Low Risk" in resp.data
    assert b"Medium Risk" in resp.data
    assert b"High Risk" in resp.data
    assert b"Company Verification" in resp.data
    assert b"Scam Report Resolution" in resp.data
    assert b"Scam Check Review / Appeal" in resp.data


def test_automatic_flagging_threshold_at_three_reports(app, client):
    """When an internship reaches 3 open reports, it is automatically flagged and admins notified."""
    with app.app_context():
        admin_u, _ = create_admin()
        stud1_u, stud1_p, _ = create_student('s1@test.org', 'Student One')
        stud2_u, stud2_p, _ = create_student('s2@test.org', 'Student Two')
        stud3_u, stud3_p, _ = create_student('s3@test.org', 'Student Three')
        comp_u, comp = create_company()
        intern, _ = create_internship(comp, title='Reported Position', status='active')
        db.session.commit()
        intern_id = intern.id
        admin_uid = admin_u.id

    # 1. Student 1 files open report -> count 1, remains active
    login(client, 's1@test.org')
    client.post('/reports/submit', data={
        'internship_id': intern_id,
        'reason': 'Demanded upfront payment or registration fee',
        'description': 'Recruiter asked for Rs 500 registration deposit.'
    }, follow_redirects=True)

    with app.app_context():
        intern = db.session.get(Internship, intern_id)
        assert intern.status == 'active'
        threshold_notifs = Notification.query.filter(
            Notification.user_id == admin_uid,
            Notification.title.ilike('%Automatically Flagged%')
        ).all()
        assert len(threshold_notifs) == 0

    # 2. Student 2 files open report -> count 2, remains active
    client.post('/auth/logout')
    login(client, 's2@test.org')
    client.post('/reports/submit', data={
        'internship_id': intern_id,
        'reason': 'Off-platform redirect (Asked to chat on Telegram/WhatsApp)',
        'description': 'Asked to move to Telegram bot.'
    }, follow_redirects=True)

    with app.app_context():
        intern = db.session.get(Internship, intern_id)
        assert intern.status == 'active'
        threshold_notifs = Notification.query.filter(
            Notification.user_id == admin_uid,
            Notification.title.ilike('%Automatically Flagged%')
        ).all()
        assert len(threshold_notifs) == 0

    # 3. Student 3 files open report -> count 3, transitions to 'flagged' and notifies admin!
    client.post('/auth/logout')
    login(client, 's3@test.org')
    client.post('/reports/submit', data={
        'internship_id': intern_id,
        'reason': 'Exaggerated promises / Fake job guarantee',
        'description': 'Guaranteed 50k per day without interview.'
    }, follow_redirects=True)

    with app.app_context():
        intern = db.session.get(Internship, intern_id)
        assert intern.status == 'flagged'
        threshold_notifs = Notification.query.filter(
            Notification.user_id == admin_uid,
            Notification.title.ilike('%Automatically Flagged%')
        ).all()
        assert len(threshold_notifs) == 1
        assert "Report Threshold" in threshold_notifs[0].title


def test_automatic_flagging_avoids_repeated_notifications_for_subsequent_reports(app, client):
    """Subsequent open reports after reaching threshold (e.g. 4th report) do not duplicate threshold notifications."""
    with app.app_context():
        admin_u, _ = create_admin()
        stud4_u, stud4_p, _ = create_student('s4@test.org', 'Student Four')
        comp_u, comp = create_company()
        intern, _ = create_internship(comp, title='Already Flagged Posting', status='flagged')

        # Add 3 pre-existing open reports
        for i in range(3):
            s_u, s_p, _ = create_student(f'pre{i}@test.org', f'Pre Student {i}')
            rep = ScamReport(reported_by_student_id=s_p.id, internship_id=intern.id, reason='Fake job', description='Fee demand', status='open')
            db.session.add(rep)

        # Baseline threshold notification count
        db.session.add(Notification(
            user_id=admin_u.id,
            title="Internship Automatically Flagged (Report Threshold)",
            message="Initial threshold alert",
            category="scam_alert"
        ))
        db.session.commit()
        intern_id = intern.id
        admin_uid = admin_u.id

    # Now Student 4 files a 4th report on this already-flagged posting
    login(client, 's4@test.org')
    client.post('/reports/submit', data={
        'internship_id': intern_id,
        'reason': 'Demanded upfront payment or registration fee',
        'description': 'Additional student reporting fee demand.'
    }, follow_redirects=True)

    with app.app_context():
        intern = db.session.get(Internship, intern_id)
        assert intern.status == 'flagged'
        # Check threshold notifications count: MUST STILL BE EXACTLY 1 (no duplicate notification)
        threshold_notifs = Notification.query.filter(
            Notification.user_id == admin_uid,
            Notification.title.ilike('%Automatically Flagged%')
        ).all()
        assert len(threshold_notifs) == 1
