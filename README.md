# Smart Online Internship Management System with Scam Prevention

An intelligent web application built for a **BCA final-year project**. It features role-based access control for **Students**, **Companies**, and **Administrators**, and incorporates a multi-layer automated **Scam Detection Engine** (`app/scam_detector.py`) that evaluates every internship posting in real time using weighted heuristic analysis and text normalization.

---

## Key Modules & System Architecture

### 1. Role-Based Access Control (RBAC)
- **Student:**
  - Complete student profile with degree, college, location preferences, and contact details.
  - Multi-resume management with private storage and primary resume selection.
  - Browse and filter internships with pagination, duration range (weeks), domain categories, work mode, eligibility keywords, and skills.
  - Safety audit cards showing risk level, transparent rule breakdown, and disclaimer.
  - One-click application modal with optional immediate resume upload and cover letter.
  - Real-time application lifecycle tracking (Applied, Under Review, Selected, Rejected, Completed).
  - Scam reporting mechanism with reason categorization and evidence links.
- **Company:**
  - Company registration with official email and Indian GSTIN validation.
  - Mandatory administrative verification workflow before posting internships.
  - Secure verification document upload (PDF/PNG/JPG) with magic-byte validation.
  - Internship lifecycle management (Draft, Active, Flagged, Closed, Rejected).
  - Pre-publication scam detector screening with instant risk score feedback.
  - Appeal submission for flagged internships with administrator resolution tracking.
  - Candidate pipeline review, feedback notes, and status management.
- **Administrator:**
  - Executive dashboard with platform analytics, pending verifications, flagged postings, and open reports.
  - Company verification review queue with authorized document preview, approval, and rejection reasons.
  - Moderation cascades: revoking company verification or blocking employer accounts automatically sets active postings to `closed` and notifies affected student applicants.
  - Flagged internships audit queue with side-by-side detector explanation, company appeal notes, and approve/reject actions.
  - User moderation (activate/block students and employers).
  - Scam report investigation center with option to quarantine/delist listings.
  - Domain categories management and audit trails.

---

## Scam Detection Engine (`app/scam_detector.py`)

The automated safety engine scores internship postings against 10 weighted heuristic rules (0–100 risk score) with bounded contextual negation handling and leetspeak/obfuscation text normalization:

| # | Rule Name | Weight | Triggers & Heuristics |
|---|:---|:---:|:---|
| 1 | **Upfront Payment Demands** | **35** | Registration fees, security deposits, training charges, laptop deposits, and payment demands via UPI, GPay, PhonePe, or Paytm. Excludes bounded negations (e.g., *"no registration fee"*, *"free of cost"*). |
| 2 | **Credential / Sensitive-Data Requests** | **35** | Requests for bank account numbers, OTP, PIN, CVV, passwords, Aadhaar, PAN card, or UPI ID paired with action verbs (*"provide"*, *"submit"*, *"verify"*). Excludes contextual negations. |
| 3 | **Unrealistic Offers & Excessive Stipend** | **25** | Unrealistic claims (*"guaranteed job"*, *"100% placement"*, *"earn per week"*, *"no interview needed"*), or monthly stipends exceeding ₹60,000 without commensurate requirements. |
| 4 | **Suspicious Links & Shorteners** | **20** | Known URL shorteners (`bit.ly`, `tinyurl.com`, `t.me`), raw IP addresses, and suspicious off-platform redirect domains. |
| 5 | **Contact Safety** | **20** | Free public email domains (`@gmail.com`, `@yahoo.com`) used by company postings, and off-platform chat redirects (*"WhatsApp only"*, *"Telegram only"*). |
| 6 | **Urgency & Pressure Tactics** | **25** | Artificial scarcity pressure (*"limited seats"*, *"hurry"*, *"apply within 1 hour"*, *"offer expires today"*). |
| 7 | **Vague Content** | **15** | Postings under 30 words with no defined responsibilities, concrete tasks, or technical skills. |
| 8 | **Spam Repetition** | **20** | Excessive word repetition and spam keywords (*"earn money"*, *"work from home"*, repeated symbols). |
| 9 | **Duplicate Listing Similarity** | **30** | Word-bigram Jaccard similarity across existing postings from the same employer to detect spam replication. |
| 10 | **Suspicious Instructions** | **20** | Application instructions requesting off-platform payments, external WhatsApp/Telegram chat links, or sensitive data sharing. |

### Scoring & Risk Tiers
- **Low Risk (0 – 30):** Passed automated screening. Published immediately with a green safety badge.
- **Medium Risk (31 – 60):** Published with a cautionary advisory banner and standard disclaimer:
  > *"Automated rule-based risk assessment. This result is not proof of fraud or legitimacy."*
- **High Risk (61 – 100):** Auto-quarantined with status `flagged`. Hidden from student listings until reviewed and approved by an administrator.

---

## Security Architecture

- **Private Resume Storage:** Resumes are stored outside the public document root in `instance/uploads/resumes/`. Access is strictly controlled via an authorized route (`/student/resume/download/<id>`) that enforces ownership and applicant permissions.
- **Private Verification Documents:** Company compliance documents are stored in `instance/uploads/company_docs/` and accessible exclusively to administrators via `/admin/verifications/document/<company_id>`.
- **Public Uploads:** Profile pictures and company logos are stored in `app/static/uploads/` with sanitized, random UUID filenames.
- **CSRF Protection:** Flask-WTF protects all state-changing `POST` requests, including logouts and admin actions.
- **Rate Limiting:** Flask-Limiter throttles login attempts to 5 attempts per minute per client IP (`RATELIMIT_ENABLED=True`).
- **Open Redirect Prevention:** Safe relative URL validation strictly accepts paths starting with exactly one `/`, rejecting `//`, backslashes, control characters, schemes, and domain authorities.
- **Strict Password Validation:** Minimum 8 characters with at least one letter and at least one digit.
- **Format Validation:** Loose 15-character GSTIN validator and 10-digit Indian mobile phone number validator.

---

## Repository Structure

```text
online-internship/
├── app/
│   ├── blueprints/
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── company/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── internships/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── reports/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   └── student/
│   │       ├── __init__.py
│   │       └── routes.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── notifications.py    # Shared in-app notification dispatcher
│   │   └── uploads.py          # Consolidated upload handling (private vs public)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   ├── js/
│   │   │   └── main.js
│   │   └── uploads/            # Public static uploads (avatars, logos)
│   ├── templates/
│   │   ├── admin/              # Dashboard, verifications, flagged, reports, categories
│   │   ├── auth/               # Login, register, notifications
│   │   ├── company/            # Dashboard, post/edit, applicants, profile
│   │   ├── internships/        # Search/filter listing, detail view with safety card
│   │   ├── reports/            # Student scam report submission & history
│   │   ├── student/            # Dashboard, profile, applications
│   │   ├── base.html
│   │   └── home.html
│   ├── __init__.py             # Application factory & extension initialization
│   ├── config.py               # Environment configuration
│   ├── decorators.py           # Security decorators (role_required, company_verified_required)
│   ├── models.py               # SQLAlchemy database models & relationships
│   ├── scam_detector.py        # 10-rule heuristic scam risk engine
│   ├── utils.py                # Backwards-compatible validator re-exports
│   └── validators.py           # Consolidated input and file validators
├── instance/
│   └── uploads/
│       ├── company_docs/       # Private company verification documents
│       └── resumes/            # Private student resume files
├── scripts/
│   ├── evaluate_detector.py    # 36-sample labeled detector benchmark & metrics
│   ├── migrate_company_docs.py # Company docs instance storage migration
│   ├── migrate_db.py           # Idempotent database schema migration
│   └── migrate_resumes.py      # Resumes instance storage migration
├── tests/
│   ├── test_admin_completeness.py
│   ├── test_data_integrity_and_demo_readiness.py
│   ├── test_private_resumes.py
│   ├── test_scam_detector.py
│   ├── test_schema_sync.py
│   ├── test_security.py
│   ├── test_security_hardening.py
│   └── test_synopsis_gaps.py
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py                      # Application entry point
├── schema.sql                  # MySQL database schema definition
├── seed.py                     # Initial demo data populator
└── README.md
```

---

## Setup & Installation Instructions

### Prerequisites
- Python 3.10+
- MySQL Server 5.7+ / 8.0+ (via XAMPP, WAMP, Docker, or standalone MySQL)

### Step 1: Clone Repository & Create Virtual Environment
```powershell
# Navigate to project root
cd online-internship

# Create Python virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate virtual environment (Linux/macOS)
# source venv/bin/activate
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Configure your credentials in `.env`:
```ini
FLASK_APP=run.py
FLASK_DEBUG=false
SECRET_KEY=replace-with-a-secure-random-key-in-production

# MySQL Database Configuration (Defaults for XAMPP / WAMP)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=smart_internship_db

# Security & Rate Limiting
RATELIMIT_ENABLED=true
RATELIMIT_STORAGE_URI=memory://

# Portal Support & Company Contact Details (Optional)
# COMPANY_CONTACT_EMAIL=contact@smartintern-placeholder.example.com
# COMPANY_CONTACT_PHONE=+91 (000) 000-0000 / +91 98765-00000
# COMPANY_CONTACT_ADDRESS=Plot No. 000, Innovation Tech Park, Bengaluru, Karnataka, India
```

### Step 4: Create MySQL Database & Initialize Schema
Using the MySQL CLI or phpMyAdmin:
```powershell
# Create Database
mysql -u root -e "CREATE DATABASE IF NOT EXISTS smart_internship_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Import Schema
mysql -u root smart_internship_db < schema.sql
```

### Step 5: Run Database Migrations (Idempotent)
Verify and apply all schema updates:
```powershell
python scripts/migrate_db.py
```

### Step 6: Seed Demo Data
Populate demo categories, users, legitimate postings, and flagged scam examples:
```powershell
python seed.py
```

### Step 7: Start the Application
```powershell
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## Development Test Accounts & Seed Credentials

> [!IMPORTANT]
> **Local Testing & Demonstration Only:** The accounts below are created strictly for local academic demonstration, viva evaluation, and automated test execution. All public-facing login autofill buttons, shortcuts, and bypass mechanisms have been eliminated. In accordance with data integrity principles, `seed.py` creates these initial fixtures without exposing plaintext passwords in server logs.

| Role | Email Address | Development Password | Profile / Purpose |
|:---|:---|:---|:---|
| **System Administrator** | `admin@smartintern.com` | `Admin@12345` | System telemetry, verification audit, scam review |
| **Student** | `student@smartintern.com` | `Student@12345` | Application pipeline, resume submission, scam reports |
| **Verified Employer 1** | `hr@technovaglobal.com` | `Company@12345` | Approved company with active legitimate postings |
| **Verified Employer 2** | `talent@cloudscalesystems.com` | `Company@12345` | Approved company with DevOps/Cloud postings |
| **Suspicious Employer** | `fastjobscorp@gmail.com` | `Scam@12345` | Unverified company fixture for testing scam heuristics |

*(Note: These development fixtures are populated via idempotent `python seed.py`.)*

---

## Testing & Evaluation

### Run Test Suites (161 Automated Tests across 8 Test Suites)
```powershell
pytest
```
Covers:
- `test_admin_completeness.py`: Moderation cascades, appeal workflows, report thresholds.
- `test_data_integrity_and_demo_readiness.py`: Dynamic dashboard calculations, test fixture separation, absence of demo shortcuts.
- `test_private_resumes.py`: Resume storage isolation, authorized serving, migration safety.
- `test_scam_detector.py`: Heuristics, weights, negation handling, leetspeak normalization.
- `test_schema_sync.py`: Table columns, nullability, seed compatibility.
- `test_security.py`: Role authorization, IDOR protection, CSRF enforcement.
- `test_security_hardening.py`: Open redirects, login rate limiting, password enforcement, form validation.
- `test_synopsis_gaps.py`: Search filters, company documents, footer placeholders.

### Run Scam Detector Benchmark
```powershell
python scripts/evaluate_detector.py
```
Evaluates the detector across 36 labeled examples (scam, legitimate, negated, obfuscated, paraphrased) and prints confusion matrix, precision, recall, and F1-score.
