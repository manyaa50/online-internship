import os
import sys
import json
from datetime import datetime, date, timedelta, timezone

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import create_app
from app.models import (
    db, User, Admin, StudentProfile, Resume, Company, CompanyVerification,
    InternshipCategory, Internship, ScamCheck, ScamReport, Notification, Application
)
from app.scam_detector import ScamDetector


def seed_database(app_instance=None):
    """
    Idempotent database seeder for development, automated testing, and demonstration.
    - Safely creates required initial categories, administrative accounts, student profiles,
      sample employers, legitimate postings, and flagged heuristic test cases.
    - Safe to run repeatedly without creating duplicate rows or overwriting existing user data.
    - Never prints plaintext passwords or secrets to console or logs.
    """
    target_app = app_instance or create_app()

    with target_app.app_context():
        print("[*] Verifying database schema...")
        db.create_all()

        print("[*] Reconciling seed categories and accounts...")

        # -----------------------------------------------------------------
        # 1. Categories (Idempotent by name)
        # -----------------------------------------------------------------
        categories_data = [
            ("Web Development", "Frontend, backend, and full stack web technologies.", "bi bi-code-slash"),
            ("Data Science & AI", "Machine learning, data analysis, deep learning, and NLP.", "bi bi-cpu"),
            ("Mobile App Development", "Android, iOS, Flutter, and React Native engineering.", "bi bi-phone"),
            ("Cloud & DevOps", "AWS, Azure, Docker, Kubernetes, and CI/CD pipelines.", "bi bi-cloud-arrow-up"),
            ("UI/UX Design", "User research, wireframing, Figma, and interactive prototyping.", "bi bi-palette"),
            ("Cybersecurity", "Network security, ethical hacking, and threat mitigation.", "bi bi-shield-lock"),
            ("Digital Marketing", "SEO, performance marketing, social media, and analytics.", "bi bi-megaphone"),
            ("Business & Finance", "Market research, financial modeling, and business development.", "bi bi-graph-up-arrow")
        ]

        cat_objs = {}
        for name, desc, icon in categories_data:
            cat = InternshipCategory.query.filter_by(name=name).first()
            if not cat:
                cat = InternshipCategory(name=name, description=desc, icon_class=icon)
                db.session.add(cat)
                db.session.flush()
            cat_objs[name] = cat

        # -----------------------------------------------------------------
        # 2. Administrator Account (Idempotent by email)
        # -----------------------------------------------------------------
        admin_user = User.query.filter_by(email='admin@smartintern.com').first()
        if not admin_user:
            admin_user = User(
                email='admin@smartintern.com',
                role='admin',
                is_active=True
            )
            admin_user.set_password(os.getenv('SEED_ADMIN_PASSWORD', 'Admin@12345'))
            db.session.add(admin_user)
            db.session.flush()

        admin_profile = Admin.query.filter_by(user_id=admin_user.id).first()
        if not admin_profile:
            admin_profile = Admin(
                user_id=admin_user.id,
                full_name='Dr. Rajesh V. Sharma (System Admin)',
                phone='+91 98765 00001'
            )
            db.session.add(admin_profile)
            db.session.flush()

        # -----------------------------------------------------------------
        # 3. Sample Companies (Idempotent by email/user_id)
        # -----------------------------------------------------------------
        # Company 1: TechNova Solutions
        c1_user = User.query.filter_by(email='hr@technovaglobal.com').first()
        if not c1_user:
            c1_user = User(email='hr@technovaglobal.com', role='company', is_active=True)
            c1_user.set_password(os.getenv('SEED_COMPANY_PASSWORD', 'Company@12345'))
            db.session.add(c1_user)
            db.session.flush()

        comp1 = Company.query.filter_by(user_id=c1_user.id).first()
        if not comp1:
            comp1 = Company(
                user_id=c1_user.id,
                company_name="TechNova Global Solutions",
                website="https://technovaglobal.com",
                official_email="hr@technovaglobal.com",
                phone="+91 98234 56781",
                address="Level 5, Cyber Gateway, HITEC City",
                city="Hyderabad",
                state="Telangana",
                country="India",
                registration_gst_number="36AABCT8521F1ZX",
                description="TechNova is a software consulting firm engineering cloud and full-stack enterprise platforms for global clients.",
                contact_person_name="Ananya Sen",
                contact_person_designation="Head of University Relations",
                verification_status="approved"
            )
            db.session.add(comp1)
            db.session.flush()

        # Company 2: CloudScale Networks
        c2_user = User.query.filter_by(email='talent@cloudscalesystems.com').first()
        if not c2_user:
            c2_user = User(email='talent@cloudscalesystems.com', role='company', is_active=True)
            c2_user.set_password(os.getenv('SEED_COMPANY_PASSWORD', 'Company@12345'))
            db.session.add(c2_user)
            db.session.flush()

        comp2 = Company.query.filter_by(user_id=c2_user.id).first()
        if not comp2:
            comp2 = Company(
                user_id=c2_user.id,
                company_name="CloudScale Systems",
                website="https://cloudscalesystems.com",
                official_email="talent@cloudscalesystems.com",
                phone="+91 98111 22334",
                address="Tower B, Prestige Tech Park, Marathahalli",
                city="Bengaluru",
                state="Karnataka",
                country="India",
                registration_gst_number="29AAACS4123K1ZT",
                description="CloudScale engineers next-gen Kubernetes cloud management tools and enterprise observability infrastructure.",
                contact_person_name="Vikramaditya Roy",
                contact_person_designation="Senior Engineering Director",
                verification_status="approved"
            )
            db.session.add(comp2)
            db.session.flush()

        # Company 3: Suspicious/Unverified Fixture for Heuristic Detection Tests
        c3_user = User.query.filter_by(email='fastjobscorp@gmail.com').first()
        if not c3_user:
            c3_user = User(email='fastjobscorp@gmail.com', role='company', is_active=True)
            c3_user.set_password(os.getenv('SEED_SCAM_PASSWORD', 'Scam@12345'))
            db.session.add(c3_user)
            db.session.flush()

        comp3 = Company.query.filter_by(user_id=c3_user.id).first()
        if not comp3:
            comp3 = Company(
                user_id=c3_user.id,
                company_name="Apex Career Ventures",
                website="http://free-careers-apex.blogspot.com",
                official_email="fastjobscorp@gmail.com",
                phone="+91 90000 11111",
                address="Plot 10, Unknown Gali",
                city="New Delhi",
                state="Delhi",
                country="India",
                registration_gst_number="UNVERIFIED_GST",
                description="Recruitment agency promising fast hiring and immediate placements for college students.",
                contact_person_name="Rahul Verma",
                contact_person_designation="Agent",
                verification_status="pending"
            )
            db.session.add(comp3)
            db.session.flush()

        # Verification logs
        if not CompanyVerification.query.filter_by(company_id=comp1.id).first():
            db.session.add(CompanyVerification(
                company_id=comp1.id,
                admin_id=admin_profile.id,
                status='approved',
                review_notes="Verified corporate registration and valid GST records."
            ))
        if not CompanyVerification.query.filter_by(company_id=comp2.id).first():
            db.session.add(CompanyVerification(
                company_id=comp2.id,
                admin_id=admin_profile.id,
                status='approved',
                review_notes="Verified LinkedIn presence, official domain email and Ministry of Corporate Affairs filing."
            ))

        # -----------------------------------------------------------------
        # 4. Sample Student Account (Idempotent by email/user_id)
        # -----------------------------------------------------------------
        s_user = User.query.filter_by(email='student@smartintern.com').first()
        if not s_user:
            s_user = User(email='student@smartintern.com', role='student', is_active=True)
            s_user.set_password(os.getenv('SEED_STUDENT_PASSWORD', 'Student@12345'))
            db.session.add(s_user)
            db.session.flush()

        student = StudentProfile.query.filter_by(user_id=s_user.id).first()
        if not student:
            student = StudentProfile(
                user_id=s_user.id,
                full_name="Aarav Sharma",
                phone="+91 98450 12345",
                college_name="National Institute of Computer Applications",
                degree="Bachelor of Computer Applications (BCA)",
                graduation_year=2026,
                cgpa=8.85,
                skills="Python, Flask, JavaScript, SQL, HTML5, Bootstrap, Git, REST APIs",
                bio="Motivated 3rd-year BCA undergraduate with a solid foundation in backend Python engineering and relational databases. Seeking practical internship experience in software engineering.",
                linkedin_url="https://linkedin.com/in/aarav-sharma",
                github_url="https://github.com/aarav-sharma",
                preferred_domain="Web Development",
                preferred_location="Remote",
                preferred_duration="3 to 6 Months"
            )
            db.session.add(student)
            db.session.flush()

        sample_resume = Resume.query.filter_by(student_id=student.id).first()
        if not sample_resume:
            sample_resume = Resume(
                student_id=student.id,
                filename="sample_bca_resume.pdf",
                original_name="Aarav_Sharma_BCA_Resume.pdf",
                file_path="instance/uploads/resumes/sample_bca_resume.pdf",
                file_size=245000,
                is_primary=True
            )
            db.session.add(sample_resume)
            db.session.flush()

        # -----------------------------------------------------------------
        # 5. Legitimate Postings (Low Risk Score: 0/100)
        # -----------------------------------------------------------------
        legit_postings = [
            {
                'company': comp1,
                'category': cat_objs["Web Development"],
                'title': "Python Backend Developer Intern",
                'description': "We are seeking an enthusiastic Python / Flask intern to collaborate with our core product engineering team. You will assist in developing robust RESTful APIs, optimizing relational database schemas, and writing modular unit tests.",
                'responsibilities': "1. Build and maintain server-side web application logic using Flask and SQLAlchemy.\n2. Design clean, normalized MySQL database tables and optimize slow queries.\n3. Integrate third-party web services and implement token-based API authentication.\n4. Write clear technical documentation and participate in daily scrum standups.",
                'eligibility': "Enrolled in BCA, B.Tech CSE/IT, or MCA graduating in 2026 or 2027 with minimum 65% aggregate. Strong fundamentals in Object-Oriented Programming and Data Structures.",
                'skills_required': "Python, Flask, SQL, MySQL, Git, REST APIs",
                'duration_text': "3 Months",
                'duration_weeks': 12,
                'location_type': "remote",
                'location_city': "Remote / Work From Home",
                'stipend_type': "paid",
                'stipend_amount': 22000.00,
                'deadline': date.today() + timedelta(days=25),
                'contact_email': "careers@technovaglobal.com",
                'contact_phone': "+91 98234 56781"
            },
            {
                'company': comp2,
                'category': cat_objs["Cloud & DevOps"],
                'title': "DevOps & Cloud Automation Intern",
                'description': "CloudScale Systems is looking for a Cloud Engineering Intern passionate about Linux, containers, and deployment automation. You will gain hands-on mentorship deploying containerized microservices to cloud environments.",
                'responsibilities': "1. Assist senior DevOps engineers in drafting Dockerfiles and managing Docker Compose clusters.\n2. Build automated GitHub Actions CI/CD pipelines for automated testing and builds.\n3. Monitor cloud health metrics, logs, and system alerts.\n4. Participate in infrastructure-as-code automation.",
                'eligibility': "Penultimate or final year BCA / B.Tech / BSc IT students with a solid understanding of Linux command-line, networking fundamentals, and bash scripting.",
                'skills_required': "Linux, Docker, Git, CI/CD, Python, Shell Scripting",
                'duration_text': "6 Months",
                'duration_weeks': 24,
                'location_type': "hybrid",
                'location_city': "Bengaluru",
                'stipend_type': "paid",
                'stipend_amount': 28000.00,
                'deadline': date.today() + timedelta(days=30),
                'contact_email': "university-hiring@cloudscalesystems.com",
                'contact_phone': "+91 98111 22334"
            },
            {
                'company': comp1,
                'category': cat_objs["UI/UX Design"],
                'title': "UI/UX Product Design Intern",
                'description': "Join our product design team to create delightful, accessible digital interfaces for modern web and mobile applications. You will conduct user journey research and build high-fidelity wireframes in Figma.",
                'responsibilities': "1. Design responsive UI components adhering to design systems.\n2. Create interactive prototypes for user testing and stakeholder feedback.\n3. Collaborate closely with frontend software engineers during handoff.\n4. Conduct usability testing sessions with student focus groups.",
                'eligibility': "Design, BCA, or computer science students with a portfolio showcasing web or mobile app UI projects in Figma.",
                'skills_required': "Figma, Wireframing, Prototyping, HTML5/CSS3 basics, User Research",
                'duration_text': "3 Months",
                'duration_weeks': 12,
                'location_type': "remote",
                'location_city': "Remote",
                'stipend_type': "paid",
                'stipend_amount': 18000.00,
                'deadline': date.today() + timedelta(days=18),
                'contact_email': "design-hiring@technovaglobal.com",
                'contact_phone': "+91 98234 56781"
            }
        ]

        for item in legit_postings:
            existing = Internship.query.filter_by(company_id=item['company'].id, title=item['title']).first()
            if not existing:
                intern = Internship(
                    company_id=item['company'].id,
                    category_id=item['category'].id,
                    title=item['title'],
                    description=item['description'],
                    responsibilities=item['responsibilities'],
                    eligibility=item['eligibility'],
                    skills_required=item['skills_required'],
                    duration_text=item['duration_text'],
                    duration_weeks=item['duration_weeks'],
                    location_type=item['location_type'],
                    location_city=item['location_city'],
                    stipend_type=item['stipend_type'],
                    stipend_amount=item['stipend_amount'],
                    application_deadline=item['deadline'],
                    contact_email=item['contact_email'],
                    contact_phone=item['contact_phone'],
                    status='active'
                )
                db.session.add(intern)
                db.session.flush()

                scan = ScamDetector.evaluate_posting({
                    'title': intern.title,
                    'description': intern.description,
                    'responsibilities': intern.responsibilities,
                    'eligibility': intern.eligibility,
                    'skills_required': intern.skills_required,
                    'stipend_type': intern.stipend_type,
                    'stipend_amount': float(intern.stipend_amount),
                    'contact_email': intern.contact_email,
                    'contact_phone': intern.contact_phone
                }, company=item['company'])

                scam_rec = ScamCheck(
                    internship_id=intern.id,
                    risk_score=scan['risk_score'],
                    risk_level=scan['risk_level'],
                    triggered_rules=json.dumps(scan['triggered_rules']),
                    summary_notes=scan['summary_notes'],
                    disclaimer=scan.get('disclaimer', ScamDetector.DISCLAIMER_TEXT),
                    is_reviewed_by_admin=True,
                    admin_verdict='approved'
                )
                db.session.add(scam_rec)

        # -----------------------------------------------------------------
        # 6. Deliberately Flagged Scam Postings (To Demo Detector & Flagging)
        # -----------------------------------------------------------------
        # Scam Demo 1: Upfront Fee + WhatsApp only + Unrealistic Claims
        scam1_title = "Online Data Entry & Form Filling - Earn ₹30,000/week! No Interview Needed"
        scam1_desc = (
            "Golden opportunity for all students! Earn per day from home with zero coding experience. "
            "Guaranteed job placement directly upon joining. Urgent hiring today only with limited seats! "
            "Selected candidates must submit a refundable amount registration fee of ₹1,500 for account activation "
            "and software kit verification charges. Hurry only 2 spots left!"
        )
        scam1_resp = "Simply copy paste data into web portals and submit daily reports. Contact only on WhatsApp to confirm selection."
        scam1_contact = "urgentjobsdesk@gmail.com"

        if not Internship.query.filter_by(company_id=comp3.id, title=scam1_title).first():
            scan1 = ScamDetector.evaluate_posting({
                'title': scam1_title,
                'description': scam1_desc,
                'responsibilities': scam1_resp,
                'eligibility': "Any student, no qualification or technical background required.",
                'skills_required': "Typing, WhatsApp messaging",
                'stipend_type': "paid",
                'stipend_amount': 120000.00,
                'contact_email': scam1_contact,
                'contact_phone': "+91 99999 88888"
            }, company=comp3)

            scam_intern1 = Internship(
                company_id=comp3.id,
                category_id=cat_objs["Web Development"].id,
                title=scam1_title,
                description=scam1_desc,
                responsibilities=scam1_resp,
                eligibility="Open to everyone. No test, no interview needed.",
                skills_required="Basic typing",
                duration_text="1 Month",
                duration_weeks=4,
                location_type="remote",
                location_city="Online",
                stipend_type="paid",
                stipend_amount=120000.00,
                application_deadline=date.today() + timedelta(days=5),
                contact_email=scam1_contact,
                contact_phone="+91 99999 88888",
                status='flagged'
            )
            db.session.add(scam_intern1)
            db.session.flush()

            db.session.add(ScamCheck(
                internship_id=scam_intern1.id,
                risk_score=scan1['risk_score'],
                risk_level=scan1['risk_level'],
                triggered_rules=json.dumps(scan1['triggered_rules']),
                summary_notes=scan1['summary_notes'],
                disclaimer=scan1.get('disclaimer', ScamDetector.DISCLAIMER_TEXT),
                is_reviewed_by_admin=False,
                admin_verdict='pending'
            ))

        # Scam Demo 2: Security Deposit + Telegram Link + Shortened URL
        scam2_title = "Immediate Web Developer Intern - 100% Placement Guaranteed (Pay to Confirm)"
        scam2_desc = (
            "We have urgent openings for junior developers. Direct selection without interview. "
            "To confirm seat, candidate must pay security deposit of ₹3,000 as refundable training fee. "
            "Apply within 1 hour before link expires: bit.ly/web-intern-reg. "
            "DM on Telegram at t.me/fastcareerhub to claim offer letter immediately."
        )

        if not Internship.query.filter_by(company_id=comp3.id, title=scam2_title).first():
            scan2 = ScamDetector.evaluate_posting({
                'title': scam2_title,
                'description': scam2_desc,
                'responsibilities': "Work on live client portals immediately with guaranteed stipend.",
                'eligibility': "Any BCA / B.Tech student",
                'skills_required': "HTML, CSS",
                'stipend_type': "paid",
                'stipend_amount': 75000.00,
                'contact_email': "hr.expresscareers@yahoo.com",
                'contact_phone': "+91 97777 66666"
            }, company=comp3)

            scam_intern2 = Internship(
                company_id=comp3.id,
                category_id=cat_objs["Web Development"].id,
                title=scam2_title,
                description=scam2_desc,
                responsibilities="Website editing and remote tasks.",
                eligibility="All college students eligible.",
                skills_required="HTML",
                duration_text="2 Months",
                duration_weeks=8,
                location_type="remote",
                location_city="Work from home",
                stipend_type="paid",
                stipend_amount=75000.00,
                application_deadline=date.today() + timedelta(days=3),
                contact_email="hr.expresscareers@yahoo.com",
                contact_phone="+91 97777 66666",
                status='flagged'
            )
            db.session.add(scam_intern2)
            db.session.flush()

            db.session.add(ScamCheck(
                internship_id=scam_intern2.id,
                risk_score=scan2['risk_score'],
                risk_level=scan2['risk_level'],
                triggered_rules=json.dumps(scan2['triggered_rules']),
                summary_notes=scan2['summary_notes'],
                disclaimer=scan2.get('disclaimer', ScamDetector.DISCLAIMER_TEXT),
                is_reviewed_by_admin=False,
                admin_verdict='pending'
            ))

        # -----------------------------------------------------------------
        # 7. Sample Medium-Risk Posting (Published with Warning Badge)
        # -----------------------------------------------------------------
        med_title = "Junior Social Media & Content Marketing Intern"
        med_desc = (
            "We are looking for a marketing enthusiast to write creative posts and interact with community members. "
            "Apply today as limited seats are available for our upcoming campaign. "
            "Candidates can reach out directly to our hiring team."
        )

        if not Internship.query.filter_by(company_id=comp1.id, title=med_title).first():
            scan_med = ScamDetector.evaluate_posting({
                'title': med_title,
                'description': med_desc,
                'responsibilities': "Draft social media updates and research trending hashtags.",
                'eligibility': "Good written communication skills in English.",
                'skills_required': "Social Media, Content Writing",
                'stipend_type': "paid",
                'stipend_amount': 8000.00,
                'contact_email': "technovahrdesk@gmail.com",
                'contact_phone': "+91 98234 56781"
            }, company=comp1)

            med_intern = Internship(
                company_id=comp1.id,
                category_id=cat_objs["Digital Marketing"].id,
                title=med_title,
                description=med_desc,
                responsibilities="Draft social media updates and research trending hashtags.",
                eligibility="Good written communication skills in English.",
                skills_required="Social Media, Content Writing",
                duration_text="2 Months",
                duration_weeks=8,
                location_type="remote",
                location_city="Remote",
                stipend_type="paid",
                stipend_amount=8000.00,
                application_deadline=date.today() + timedelta(days=14),
                contact_email="technovahrdesk@gmail.com",
                contact_phone="+91 98234 56781",
                status='active'
            )
            db.session.add(med_intern)
            db.session.flush()

            db.session.add(ScamCheck(
                internship_id=med_intern.id,
                risk_score=scan_med['risk_score'],
                risk_level=scan_med['risk_level'],
                triggered_rules=json.dumps(scan_med['triggered_rules']),
                summary_notes=scan_med['summary_notes'],
                disclaimer=scan_med.get('disclaimer', ScamDetector.DISCLAIMER_TEXT),
                is_reviewed_by_admin=False,
                admin_verdict='approved'
            ))

        # -----------------------------------------------------------------
        # 8. Sample Application for Student
        # -----------------------------------------------------------------
        first_legit = Internship.query.filter_by(title="Python Backend Developer Intern").first()
        if first_legit and student and sample_resume:
            existing_app = Application.query.filter_by(
                internship_id=first_legit.id,
                student_id=student.id
            ).first()
            if not existing_app:
                app_record = Application(
                    internship_id=first_legit.id,
                    student_id=student.id,
                    resume_id=sample_resume.id,
                    cover_letter="I am excited to apply for the Python Backend Developer Internship at TechNova. My experience in Flask and MySQL aligns closely with your tech stack.",
                    status="Under Review",
                    company_feedback="Candidate resume shortlisted for technical phone interview."
                )
                db.session.add(app_record)

        # -----------------------------------------------------------------
        # 9. Sample Scam Report
        # -----------------------------------------------------------------
        scam1_rec = Internship.query.filter_by(title=scam1_title).first()
        if scam1_rec and student and comp3:
            existing_report = ScamReport.query.filter_by(
                reported_by_student_id=student.id,
                internship_id=scam1_rec.id
            ).first()
            if not existing_report:
                scam_report = ScamReport(
                    reported_by_student_id=student.id,
                    internship_id=scam1_rec.id,
                    company_id=comp3.id,
                    reason="Demanded upfront registration fee on WhatsApp",
                    description="The recruiter messaged me saying I have been selected without any interview, but demanded ₹1,500 via UPI as a mandatory training kit deposit before sending the offer letter.",
                    evidence_link="https://drive.google.com/demo-chat-screenshot",
                    status="open"
                )
                db.session.add(scam_report)

        db.session.commit()
        print("[OK] Database seed verification complete (idempotent):")
        print("   - Seed user accounts verified (admin, student, employers)")
        print("   - Seed categories, listings, and moderation records verified")
        print("   - No plaintext passwords or secrets exposed in logs")


if __name__ == '__main__':
    seed_database()
