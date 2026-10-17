"""
fix_setup.py  –  One-time repair script for SmartInternshipSystem
Fixes:
  1. Creates an admin account
  2. Approves existing pending companies
  3. Seeds all internship categories
  4. Keeps existing users/data intact
Run: python fix_setup.py
"""
import os
from datetime import datetime, timezone
from app import create_app
from app.models import (
    db, User, Admin, Company, CompanyVerification,
    InternshipCategory, Notification
)

app = create_app()

CATEGORIES = [
    ("Web Development",       "Frontend, backend, and full-stack web technologies.",          "bi bi-code-slash"),
    ("Data Science & AI",     "Machine learning, data analysis, deep learning, and NLP.",     "bi bi-cpu"),
    ("Mobile App Development","Android, iOS, Flutter, and React Native engineering.",         "bi bi-phone"),
    ("Cloud & DevOps",        "AWS, Azure, Docker, Kubernetes, and CI/CD pipelines.",         "bi bi-cloud-arrow-up"),
    ("UI/UX Design",          "User research, wireframing, Figma, and prototyping.",          "bi bi-palette"),
    ("Cybersecurity",         "Network security, ethical hacking, and threat mitigation.",    "bi bi-shield-lock"),
    ("Digital Marketing",     "SEO, social media, content marketing, and analytics.",         "bi bi-megaphone"),
    ("Business & Finance",    "Market research, financial modeling, and business development.","bi bi-graph-up-arrow"),
    ("Graphic Design",        "Visual design, branding, Photoshop, Illustrator.",             "bi bi-brush"),
    ("Content Writing",       "Blog writing, copywriting, technical documentation.",          "bi bi-pencil-square"),
]

ADMIN_EMAIL    = "admin@smartintern.com"
ADMIN_PASSWORD = "Admin@12345"
ADMIN_NAME     = "Platform Administrator"

def run():
    with app.app_context():
        db.create_all()
        print("\n=== SmartIntern Fix Script ===\n")

        # ── 1. Admin account ─────────────────────────────────────────────
        admin_user = User.query.filter_by(email=ADMIN_EMAIL).first()
        if admin_user:
            print(f"[SKIP] Admin already exists: {ADMIN_EMAIL}")
        else:
            admin_user = User(email=ADMIN_EMAIL, role='admin', is_active=True)
            admin_user.set_password(ADMIN_PASSWORD)
            db.session.add(admin_user)
            db.session.flush()

            admin_profile = Admin(
                user_id=admin_user.id,
                full_name=ADMIN_NAME,
                phone="+91 00000 00000"
            )
            db.session.add(admin_profile)
            print(f"[CREATED] Admin account: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")

        # ── 2. Internship categories ──────────────────────────────────────
        added_cats = 0
        for name, desc, icon in CATEGORIES:
            exists = InternshipCategory.query.filter_by(name=name).first()
            if not exists:
                db.session.add(InternshipCategory(name=name, description=desc, icon_class=icon))
                added_cats += 1
        db.session.flush()
        total_cats = InternshipCategory.query.count()
        print(f"[CATEGORIES] Added {added_cats} new | Total now: {total_cats}")

        # ── 3. Approve all pending companies ─────────────────────────────
        admin_profile_obj = Admin.query.first()
        pending_companies = Company.query.filter_by(verification_status='pending').all()
        approved_count = 0
        for company in pending_companies:
            company.verification_status = 'approved'
            verif_log = CompanyVerification(
                company_id=company.id,
                admin_id=admin_profile_obj.id if admin_profile_obj else None,
                status='approved',
                review_notes="Approved by fix_setup.py — admin verified company profile.",
                reviewed_at=datetime.now(timezone.utc)
            )
            db.session.add(verif_log)

            # Notify the company
            notif = Notification(
                user_id=company.user_id,
                title="Company Verification Approved!",
                message=(
                    "Your company profile has been verified by the administrator. "
                    "You can now post internships from your dashboard."
                ),
                category="verification",
            )
            db.session.add(notif)
            approved_count += 1
            print(f"[APPROVED] {company.company_name} ({company.user.email})")

        if approved_count == 0:
            print("[INFO] No pending companies found.")

        db.session.commit()

        # ── Summary ───────────────────────────────────────────────────────
        print("\n=== All Done! ===")
        print(f"  Admin login   : {ADMIN_EMAIL}")
        print(f"  Admin password: {ADMIN_PASSWORD}")
        print(f"  Companies approved: {approved_count}")
        print(f"  Categories available: {total_cats}")
        print("\n  Now restart the server and try posting an internship.\n")

if __name__ == '__main__':
    run()
