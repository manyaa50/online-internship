"""End-to-end internship posting test — run with: venv\Scripts\python.exe test_internship_flow.py"""
from app import create_app
from app.models import db, Company, InternshipCategory, Internship, ScamCheck
from app.scam_detector import ScamDetector
from datetime import date, timedelta
import json, sys

app = create_app()
with app.app_context():
    # Step 1: Sync schema
    db.create_all()
    print("Step 1: Schema synced OK")

    # Step 2: Verify company and categories
    company = Company.query.filter_by(verification_status='approved').first()
    cat = InternshipCategory.query.first()
    assert company, "No approved company found!"
    assert cat, "No categories found!"
    print(f"Step 2: Company='{company.company_name}', Cat='{cat.name}'")

    # Step 3: Run scam detector
    posting_data = {
        'title': 'Python Backend Developer Intern (Test)',
        'description': 'We are looking for a motivated Python Flask intern to collaborate with our core engineering team on REST API development and database design.',
        'responsibilities': '1. Build RESTful APIs\n2. Write unit tests\n3. Optimize SQL queries',
        'eligibility': 'BCA or B.Tech CSE students graduating 2026 or 2027, minimum 65% aggregate.',
        'skills_required': 'Python, Flask, MySQL, Git',
        'stipend_type': 'paid',
        'stipend_amount': 18000.0,
        'contact_email': company.official_email,
        'contact_phone': company.phone or ''
    }
    scan = ScamDetector.evaluate_posting(posting_data, company=company)
    level = scan['risk_level']
    score = scan['risk_score']
    print(f"Step 3: Scam scan = {level} ({score}/100)")

    # Step 4: Create internship with all new fields
    intern = Internship(
        company_id=company.id,
        category_id=cat.id,
        title=posting_data['title'],
        description=posting_data['description'],
        responsibilities=posting_data['responsibilities'],
        eligibility=posting_data['eligibility'],
        skills_required=posting_data['skills_required'],
        duration_weeks=12,
        duration_text='3 Months',
        location_type='remote',
        location_city='Remote',
        stipend_type='paid',
        stipend_amount=18000.0,
        openings_count=3,
        start_date=date.today() + timedelta(days=30),
        application_deadline=date.today() + timedelta(days=21),
        application_instructions='Email your resume to hr@company.com with subject: Intern Application',
        contact_email=company.official_email,
        contact_phone=company.phone or '',
        status='active' if level != 'High' else 'flagged'
    )
    db.session.add(intern)
    db.session.flush()

    db.session.add(ScamCheck(
        internship_id=intern.id,
        risk_score=score,
        risk_level=level,
        triggered_rules=json.dumps(scan['triggered_rules']),
        summary_notes=scan['summary_notes'],
        is_reviewed_by_admin=(level == 'Low'),
        admin_verdict='approved' if level == 'Low' else 'pending'
    ))
    db.session.commit()
    print("Step 4: Internship + ScamCheck saved to DB")

    # Step 5: Verify persistence by re-querying
    saved = Internship.query.filter_by(title=posting_data['title']).first()
    assert saved is not None, "Internship not found after commit!"
    assert saved.start_date is not None, "start_date not persisted!"
    assert saved.application_instructions, "application_instructions not persisted!"
    assert saved.scam_check is not None, "ScamCheck not linked!"
    assert saved.company_id == company.id, "company_id mismatch!"

    print(f"Step 5: Verified — ID={saved.id}, status={saved.status}")
    print(f"        start_date={saved.start_date}")
    print(f"        instructions='{saved.application_instructions[:50]}...'")
    print(f"        scam risk={saved.scam_check.risk_level}")
    print(f"        total internships in DB: {Internship.query.count()}")
    print()
    print("ALL TESTS PASSED — internship posting workflow is fully functional")
