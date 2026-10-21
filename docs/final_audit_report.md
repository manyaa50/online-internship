# Final Regression Audit Report: Smart Online Internship Management System with Scam Prevention

**Academic Evaluation Context:** Final Year Bachelor of Computer Applications (BCA) Capstone Project  
**Tech Stack:** Python Flask, MySQL / SQLAlchemy ORM, Jinja2, Bootstrap 5, Flask-WTF, Flask-Login, Flask-Limiter  
**Audit Date:** October 2026  
**Auditor:** Automated Regression Engine & Security Audit  

---

## 1. Executive Summary & Project Assessment

This comprehensive regression audit was conducted on the **Smart Online Internship Management System with Scam Prevention** to verify end-to-end functionality, security controls, role-based boundaries, data integrity, and error handling across all user workflows.

### Demonstration Readiness Assessment
> [!IMPORTANT]
> **Academic Demonstration Readiness:** The system is **thoroughly prepared and well-suited for a final-year BCA project demonstration and viva voce examination**.
> All 8 core functional workflows operate cleanly with zero crashes, robust input validation, server-side authorization enforcement, and defensive error pages.
> 
> **Production Disclaimer:** The application is **not claimed to be an enterprise production system**. It is an academic prototype designed to showcase modern web engineering practices, role-based workflows, and automated scam prevention heuristics.

---

## 2. Features Verified Across Workflows

### Workflow 1: Authentication, Access Control, and Rate Limiting
- **Registration Flow:**
  - Mandatory field validation across student and employer registrations.
  - Role validation strictly permits `student` and `company` (rejecting unauthorized roles such as `admin`).
  - Email format verification via `email-validator` with automated lowercasing and domain validation.
  - Indian phone number validation (10-digit formats with optional `+91` or `0` prefix, valid telecom prefixes `[6-9]`).
  - Password complexity enforcement (minimum 8 characters with at least one letter and one numeric digit).
  - Password and confirm-password equivalence check.
  - Duplicate email detection with safe flash notice.
- **Login & Rate Limiting:**
  - Password verification via Werkzeug `check_password_hash`.
  - Generic authentication failure response (`Invalid email or password. Please try again.`) preventing account enumeration.
  - Account suspension enforcement: Deactivated/blocked users (`is_active=False`) are blocked from logging in with an explicit deactivation alert.
  - Rate limiting via Flask-Limiter: Restricts POST attempts to **5 requests per minute per IP address**, returning a custom HTTP 429 page upon threshold breach.
- **Safe Redirect Handling:**
  - Strictly accepts relative redirects starting with exactly one forward slash `/` (e.g., `/student/dashboard`).
  - Rejects protocol-relative URLs (`//example.com`), URLs with external schemes (`https://attacker.com`), backslashes (`\attacker.com`), control characters, and malformed targets, defaulting safely to role dashboards.
- **Logout:**
  - POST-only route (`/auth/logout`) guarded by CSRF tokens; GET requests return `405 Method Not Allowed` while preserving the active session.

### Workflow 2: Student Pipeline, Resumes, and Application Submissions
- **Profile Management:**
  - Updating name, contact number, degree, skills, bio, and social links.
  - Safe numeric parsing for graduation year and CGPA (0.00 to 10.00 scale) preventing HTTP 500 server crashes on malformed inputs.
- **Private Resume Storage & Authorized Serving:**
  - Magic-byte verification for resume files: Validates `%PDF-` for PDF and `PK\x03\x04` for DOCX (rejecting renamed executables or malicious text scripts).
  - Isolation: Files stored in instance directory (`instance/uploads/resumes/`) rather than public static web trees.
  - Access Control: Only the resume owner, the hiring company for an active application, or an administrator can download the resume. Unauthorized downloads redirect to the homepage with a security alert.
- **Search & Filter Operations:**
  - Search by keyword (title, description, skills, company name), category, location type (`remote`, `on-site`, `hybrid`), city, stipend type, minimum stipend, and duration range.
  - Safe parsing of pagination parameters (`page`) and query numbers without exceptions on non-integer inputs.
  - Query parameters preserved across pagination controls (`Previous`, page numbers, `Next`).
- **Application Submission:**
  - Expiry validation: Refuses applications after `application_deadline < today`.
  - Duplicate prevention: Blocks repeated applications for the same internship.
  - Medium-risk safety warning: Requires explicit student acknowledgement checkbox before permitting application to medium-risk listings.
  - In-modal resume upload with magic-byte validation and fallback to student primary resume.
- **Application Tracking:**
  - Student application dashboard displaying real-time status (`Applied`, `Under Review`, `Selected`, `Rejected`, `Completed`).

### Workflow 3: Company Management, Verification, and Postings
- **Company Profile & Documents:**
  - Profile editing with Indian GSTIN regex validation (`\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}`) and official email validation.
  - Verification document upload: Magic-byte inspection for PDF (`%PDF-`), JPEG (`\xFF\xD8\xFF`), and PNG (`\x89PNG\r\n\x1a\n`) stored privately in `instance/uploads/company_docs/`.
  - Private document viewing endpoint guarded against unauthorized cross-company access.
- **Internship Creation & Gating:**
  - Gated by `@company_verified_required`: Unverified, pending, or rejected companies are prevented from posting or editing listings.
  - Form validation: Enforces minimum word counts (title >= 5 chars, description >= 30 chars, responsibilities >= 20 chars, eligibility >= 10 chars), positive numeric values for openings and stipend, and future application deadlines.
- **Automated Scam Pre-screening:**
  - Every created or edited internship is automatically screened through `ScamDetector.evaluate_posting`.
  - High-risk score (>= 61) immediately holds the listing in `'flagged'` status and notifies system administrators.
  - Medium-risk score (31–60) publishes with a caution badge and requires student acknowledgement before applying.
  - Low-risk score (<= 30) publishes directly as `'active'`.
- **Applicant Review & Notifications:**
  - Employer applicant review dashboard isolated to the authenticated company's listings.
  - Query parameter filtering hardened: Attempting to query another company's `internship_id` returns an unauthorized warning and excludes other applicants.
  - Updating candidate application status (`Selected`, `Rejected`, `Under Review`) delivers instant in-app notifications to the student.

### Workflow 4: Administrator Moderation, Appeals, and Auditing
- **Company Verification Workflow:**
  - Admin verification approval (`approved`) or rejection (`rejected`) with review notes.
  - Moderation cascade: Revoking or rejecting company verification automatically cascades active listings to `'closed'` and notifies affected student applicants.
- **User Blocking & Self-protection:**
  - Toggle user blocking (`is_active` inversion) for students and employers.
  - Self-protection: Admin cannot block their own administrative account.
  - Cascade: Blocking a company user closes all active postings and notifies enrolled applicants.
- **Internship Flagging & Appeals Review:**
  - Flagged listings review dashboard sorted by heuristic risk score.
  - Appeal submission by employer (minimum 30 characters explaining listing legitimacy).
  - Admin appeal review: Approving restores posting to `'active'` and notifies company; rejecting updates scam verdict, keeps listing `'rejected'`, and notifies applicants. Duplicate or already-resolved appeal re-evaluations are prevented.
- **Scam Reports & Automated Quarantine Threshold:**
  - Student report submission with reason, description, and optional evidence link.
  - Threshold rule: When an internship accumulates **3 or more open scam reports**, it is automatically quarantined to `'flagged'` status, and admins are notified once. Subsequent reports do not duplicate notifications.
- **System Information & Telemetry:**
  - Admin-only route (`/admin/system-info`) calculating dynamic database totals (users, students, companies, postings, applications, scam reports, risk scores, and the 10 most recent administrative audit actions).

### Workflow 5: Scam Detector Heuristics and Accuracy
- **Text Normalization:**
  - Converts text to lowercase and strips zero-width Unicode characters (`\u200b`–`\u200f`, `\ufeff`, `\u00ad`, `\u2060`).
  - Collapses punctuation obfuscation inside words (e.g. `p.a.y.m.e.n.t` -> `payment`).
  - Leetspeak token conversion (`1`->`i`, `0`->`o`, `@`->`a`, `3`->`e`) while preserving numeric amounts and currency markers.
- **Contextual Bounded Negation:**
  - Suppresses false positives when payment/credential keywords are preceded within 4 words by negative tokens (`no`, `not`, `zero`, `without`, `never`, `free of`), respecting sentence boundaries.
- **Credential Detection:**
  - Detects requests for OTP, passwords, NetBanking logins, Aadhaar numbers, PAN cards, CVV, PINs, and bank accounts paired with action verbs (`share`, `send`, `enter`, `submit`).
- **Payment Demand Paraphrases:**
  - Detects upfront fee terms (`registration fee`, `security deposit`, `training fee`, `laptop deposit`, `processing fee`, `fees dena hoga`).
  - Detects proximity matches between payment verbs (`pay`, `transfer`, `send`, `deposit`) and currency amounts or payment applications (`gpay`, `phonepe`, `paytm`, `upi`).
- **Truthful Risk Disclaimers:**
  - Replaced absolute safety claims with factual disclaimers: *"Automated rule-based risk assessment. This result is not proof of fraud or legitimacy."*

### Workflow 6: Public Listing Access Restrictions
- Unapproved companies (`verification_status != 'approved'`) are excluded from public listings and home page featured cards.
- Inactive / blocked company accounts (`user.is_active == False`) are excluded from public listings.
- Closed, draft, flagged, and rejected postings are excluded from public browse listings.
- Direct detail URL access protection: Requesting `/internships/<id>` for an ineligible posting returns HTTP 404 for students and unauthenticated guests (permitted only for the owning employer and administrators).
- Direct application protection: Submitting POST to `/internships/<id>/apply` for an ineligible listing returns HTTP 404.

### Workflow 7: Database Synchronization, Migrations, and Storage Isolation
- Database schema matches `schema.sql` across all 12 tables.
- Migration script (`scripts/migrate_db.py`) runs idempotently without data loss.
- Storage migration scripts (`scripts/migrate_resumes.py`, `scripts/migrate_company_docs.py`) properly isolate private uploads into the `instance/` folder.
- Seed populator (`seed.py`) creates reproducible development fixtures without plaintext password logging.

### Workflow 8: Forms, Buttons, CSRF Protection, and Navigation
- 100% of POST forms across all HTML templates contain `csrf_token` hidden inputs.
- Navigation bar dynamically reflects authenticated user roles (Student Hub, Employer Portal, Admin Control).
- All alerts and modals render via Bootstrap 5 with accessible aria attributes.

---

## 3. Test Suites Executed & Actual Results

### Test Execution Summary
All tests were executed using `pytest` inside the Python 3.13 virtual environment (`venv\Scripts\python.exe`):

| Test Suite File | Test Count | Status | Focus Area |
|:---|:---:|:---:|:---|
| `tests/test_admin_completeness.py` | 18 | **PASSED** | Appeals, moderation cascades, public listing exclusion, auto-flagging threshold |
| `tests/test_data_integrity_and_demo_readiness.py` | 8 | **PASSED** | Dynamic dashboard totals, absence of demo shortcuts, truthful risk wording |
| `tests/test_final_regression.py` | 14 | **PASSED** | End-to-end regression workflows, edge cases, role gating, malformed inputs |
| `tests/test_private_resumes.py` | 18 | **PASSED** | Magic-byte resume validation, instance storage isolation, download authorization |
| `tests/test_scam_detector.py` | 58 | **PASSED** | Text normalization, leetspeak, bounded negation, Hinglish, 36 labeled benchmarks |
| `tests/test_schema_sync.py` | 7 | **PASSED** | Schema-model column alignment, migration script idempotency, type safety |
| `tests/test_security.py` | 20 | **PASSED** | RBAC authorization, cross-company IDOR prevention, admin-only status gates |
| `tests/test_security_hardening.py` | 19 | **PASSED** | Open redirects, login rate limiting, password complexity, form input hardening |
| `tests/test_synopsis_gaps.py` | 13 | **PASSED** | Search filter combinations, company doc upload/verification, safety warning gate |
| **Total Automated Tests** | **175** | **175 PASSED (100%)** | **Execution Duration: 42.78s** |

### Scam Detector Benchmark Results (`scripts/evaluate_detector.py`)
Execution of the standalone benchmark script against 36 curated, labeled test cases:

```
==============================================================================
      SCAM DETECTOR PERFORMANCE EVALUATION REPORT
==============================================================================
Total Labeled Examples in Dataset: 36
  True Positives  (TP) : 20   [Scams correctly caught]
  False Positives (FP) :  0   [Legitimate falsely flagged]
  True Negatives  (TN) : 16   [Legitimate/Negated correctly cleared]
  False Negatives (FN) :  0   [Scams missed]
------------------------------------------------------------------------------
  Accuracy  : 100.00%  (36/36)
  Precision : 100.00%  (TP / (TP + FP))
  Recall    : 100.00%  (TP / (TP + FN))
  F1-Score  : 100.00%
==============================================================================
```

---

## 4. Security & Robustness Issues Discovered and Fixed

During the regression audit, four specific defects and robustness gaps were discovered and fixed in the application code:

1. **Company Verification Bypass on Internship Editing (`app/blueprints/company/routes.py`):**
   - *Issue:* While `/company/internships/create`, `/status`, and `/delete` were protected by `@company_verified_required`, the `/internships/edit/<id>` endpoint previously lacked this decorator. A company whose verification was revoked or set to pending could still access the edit form.
   - *Fix:* Added `@company_verified_required` to `edit_internship` route. Unverified companies are now redirected to the dashboard with an informational alert.

2. **Unhandled `ValueError` HTTP 500 on Malformed `resume_id` (`app/blueprints/internships/routes.py`):**
   - *Issue:* In `apply()`, the POST parameter `resume_id` was cast directly via `int(resume_id)`. Tampered, corrupted, or non-numeric form payloads produced an unhandled `ValueError`, causing an HTTP 500 server error.
   - *Fix:* Wrapped the integer parsing in a `try...except (ValueError, TypeError)` block that falls back safely to the student's primary resume or prompts the user without crashing.

3. **Defensive Guard Against Missing Profiles on Document Routes (`app/blueprints/student/routes.py`):**
   - *Issue:* In `download_resume`, `upload_resume`, and `delete_resume`, code directly accessed `current_user.student_profile.id` or `current_user.company_profile.id`. In edge cases where a user authenticated with a role but had an incomplete profile record, this would raise an `AttributeError`.
   - *Fix:* Added explicit null checks (`current_user.student_profile is not None` and `current_user.company_profile is not None`) before querying IDs.

4. **Legacy SQLAlchemy 1.x Query Modernization (`app/blueprints/reports/routes.py` & `tests/test_security.py`):**
   - *Issue:* Usage of `Internship.query.get(id)` triggered `LegacyAPIWarning` in SQLAlchemy 2.0.
   - *Fix:* Modernized calls to use `db.session.get(Internship, id)` and `db.session.get(Company, id)`, eliminating deprecation warnings.

---

## 5. Known Limitations & Technical Constraints

To maintain full transparency, the following design constraints and scope boundaries are noted:

1. **Headless Execution Environment:**
   - Automated testing was conducted via pytest, unit tests, and the Flask WSGI test client. Browser-level end-to-end automation (such as Selenium WebDriver or Playwright) was not executed in this environment.
2. **Database Integration Testing:**
   - Automated test suites run in-memory SQLite for speed and test isolation. Live MySQL database interactions rely on MySQL Server 5.7+ / 8.0+ running locally (via XAMPP / WAMP) as outlined in the setup instructions.
3. **In-App Notification Scope:**
   - Notifications are stored in the database (`notifications` table) and rendered in the in-app notification center. Outbound SMTP email dispatch is not configured for external delivery in this offline BCA project configuration.
4. **Scam Detection Heuristic Boundaries:**
   - The detector relies on pattern matching, regex rules, Levenshtein/bigram similarity, and text normalization. While it achieves 100% on the 36-sample academic test suite, sophisticated zero-day fraud phrasing that omits known keywords requires human administrator inspection.

---

## 6. Manual Steps Required to Run the Project

Follow these steps in VS Code or Windows PowerShell to execute the project locally:

### Step 1: Open Terminal in Project Directory
```powershell
cd c:\Users\Lenovo\Desktop\online\online-internship
```

### Step 2: Activate Python Virtual Environment
If running scripts is restricted by PowerShell execution policy, run:
```powershell
# Set execution policy for the current process
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### Step 3: Configure Environment Variables
Ensure `.env` exists in the project root:
```ini
FLASK_APP=run.py
FLASK_DEBUG=false
SECRET_KEY=smart-internship-scam-prevention-secret-key-2026-bca

# MySQL Configuration (Defaults for local XAMPP / WAMP)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=smart_internship_db

# Rate Limiting
RATELIMIT_ENABLED=true
RATELIMIT_STORAGE_URI=memory://
```

### Step 4: Initialize MySQL Database (XAMPP / WAMP)
Start Apache and MySQL from the XAMPP Control Panel, then:
```powershell
# Create database
mysql -u root -e "CREATE DATABASE IF NOT EXISTS smart_internship_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Import schema
mysql -u root smart_internship_db < schema.sql

# Run database migrations
python scripts/migrate_db.py

# Seed development test data
python seed.py
```

### Step 5: Start the Development Server
```powershell
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

### Step 6: Run Automated Tests & Evaluation
```powershell
# Run all 175 automated unit and regression tests
pytest

# Run scam detector benchmark evaluation report
python scripts/evaluate_detector.py
```

---

## 7. Final Assessment for BCA Project Demonstration

The **Smart Online Internship Management System with Scam Prevention** fulfills all software engineering criteria expected of a final-year BCA capstone project:

- **Architecture:** Structured Model-View-Controller (MVC) pattern utilizing Flask application factory, modular blueprints, and shared services (`notifications`, `uploads`, `validators`).
- **Security Posture:** Role-based access control, CSRF token validation on all POST requests, magic-byte upload validation, private instance document storage, open redirect protection, and brute-force rate limiting.
- **Novel Feature:** Rule-based scam detection engine incorporating Unicode de-obfuscation, leetspeak normalization, Hinglish phrase detection, and bounded negation handling.
- **Verification:** 175 passing automated tests across 9 test suites ensuring regression-free operation.

The project is fully prepared for viva evaluation and demonstration.
