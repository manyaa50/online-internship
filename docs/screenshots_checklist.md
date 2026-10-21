# Screenshot Checklist for Project Report
## Smart Online Internship Management System with Scam Prevention

This checklist documents every implemented screen in the application to capture for the **BCA Final-Year Project Report**, presentation slides, and viva demonstration. Each entry specifies the exact URL route, required user role, UI elements that must be visible, and the prerequisite data needed to capture the screenshot effectively.

---

### Summary Checklist Matrix

| Screen ID | Screen Title | Route / Endpoint | User Role | Priority |
|:---|:---|:---|:---|:---:|
| **SCR-PUB-01** | Landing Home Page & Safety Overview | `GET /` | Guest / Public | High |
| **SCR-PUB-02** | Internship Search with Multi-Facet Filters | `GET /internships/` | Guest / Public | High |
| **SCR-PUB-03** | Opportunity Detail & Automated Safety Audit Card | `GET /internships/<id>` | Guest / Public | High |
| **SCR-PUB-04** | User Authentication & Quick-Login Pills | `GET /auth/login` | Guest / Public | High |
| **SCR-PUB-05** | Dual-Role Registration (Student vs Company) | `GET /auth/register` | Guest / Public | High |
| **SCR-STU-01** | Student Dashboard & Key Application Metrics | `GET /student/dashboard` | Student | High |
| **SCR-STU-02** | Student Profile & Private Resumes Management | `GET /student/profile` | Student | High |
| **SCR-STU-03** | One-Click Application Modal with Resume Select | `POST /internships/apply/<id>` | Student | High |
| **SCR-STU-04** | Candidate Application Pipeline Tracking | `GET /student/applications` | Student | High |
| **SCR-STU-05** | Whistleblower Scam Reports History | `GET /reports/my-reports` | Student | Medium |
| **SCR-STU-06** | In-App Notifications Feed & Unread Alerts | `GET /auth/notifications` | Student / All | Medium |
| **SCR-COM-01** | Employer Dashboard & Verification Status | `GET /company/dashboard` | Company | High |
| **SCR-COM-02** | Company Profile & Verification Document Upload | `GET /company/profile` | Company | High |
| **SCR-COM-03** | Post Internship Form with Form Validation | `GET /company/post-internship` | Company | High |
| **SCR-COM-04** | Live Scam Screening Interception & Alert | `POST /company/post-internship` | Company | High |
| **SCR-COM-05** | Manage Internships & Flagged Appeal Submission | `GET /company/manage-internships` | Company | High |
| **SCR-COM-06** | Candidate Review & Authorized CV Serving | `GET /company/applicants/<id>` | Company | High |
| **SCR-ADM-01** | Administrator Executive Dashboard | `GET /admin/dashboard` | Administrator | High |
| **SCR-ADM-02** | Company Verification Audit Queue & Document Preview | `GET /admin/verifications` | Administrator | High |
| **SCR-ADM-03** | Quarantined Postings & Company Appeal Review | `GET /admin/flagged-internships` | Administrator | High |
| **SCR-ADM-04** | Community Scam Reports Investigation Center | `GET /admin/reports` | Administrator | High |
| **SCR-ADM-05** | Company Moderation Directory & Suspension Cascade | `GET /admin/companies` | Administrator | Medium |
| **SCR-ADM-06** | Student Accounts Moderation Directory | `GET /admin/students` | Administrator | Medium |
| **SCR-ADM-07** | Domain Categories Taxonomy Management | `GET /admin/categories` | Administrator | Medium |
| **SCR-ADM-08** | System Diagnostics & Audit Action Ledger | `GET /admin/system-info` | Administrator | High |

---

### Detailed Screenshot Specifications

#### 1. Public & Guest Role

##### `SCR-PUB-01`: Landing Home Page & Safety Overview
- **URL Route:** `http://127.0.0.1:5000/`
- **Role:** Guest / Unauthenticated
- **Key UI Elements Visible:**
  - Hero header with call-to-action buttons ("Browse Safe Internships", "Post an Opportunity").
  - Platform statistics counter (Total Active Postings, Registered Companies, Safety Verified Rate).
  - 10-Rule Scam Prevention Feature showcase cards.
  - Domain categories grid with icons (Web Development, Data Science, AI/ML, Marketing, etc.).
  - Global footer with placeholder company contact information (Email: `support@smartintern.example.com`, Phone: `+91 98765 43210`, Postal Address).
- **Prerequisite Data:** Seed data populated (`python seed.py`).

##### `SCR-PUB-02`: Internship Search with Multi-Facet Filters
- **URL Route:** `http://127.0.0.1:5000/internships/`
- **Role:** Guest or Student
- **Key UI Elements Visible:**
  - Search filter sidebar with:
    - Keyword text input.
    - Explicit Skills search field (e.g. `Python`, `SQL`).
    - Domain Category dropdown.
    - Duration range in weeks (Minimum Weeks and Maximum Weeks numeric inputs).
    - Work Mode filter (All, Remote, On-site, Hybrid).
  - Filtered opportunity cards showing company logo, title, stipend, duration badge.
  - **Safety Audit Badges:** Green badge (`Safe - Low Risk`) or Yellow badge (`Caution - Medium Risk`).
  - Active pagination bar preserving all filter query parameters.
- **Prerequisite Data:** Seeded database with listings across multiple categories and durations.

##### `SCR-PUB-03`: Opportunity Detail & Automated Safety Audit Card
- **URL Route:** `http://127.0.0.1:5000/internships/<id>` (e.g. `/internships/1`)
- **Role:** Guest or Student
- **Key UI Elements Visible:**
  - Internship title, employer name, location, stipend in INR, duration, openings.
  - Start date and application deadline.
  - Detailed responsibilities and eligibility requirements.
  - Application instructions block.
  - **Automated Safety Audit Assessment Card:**
    - Risk Score indicator (e.g. `15/100` Low Risk or `35/100` Medium Risk).
    - Transparent rule breakdown explaining why points were or were not triggered.
    - Standardized disclaimer: *"Automated rule-based risk assessment. This result is not proof of fraud or legitimacy."*
  - "Apply for this Internship" button (opens modal for logged-in students).
  - "Report this Posting" whistleblower link.
- **Prerequisite Data:** Capture once for a Low Risk posting (e.g., TechNova) and once for a Medium Risk posting (e.g., CloudScale).

##### `SCR-PUB-04`: User Authentication & Quick-Login Pills
- **URL Route:** `http://127.0.0.1:5000/auth/login`
- **Role:** Guest / Unauthenticated
- **Key UI Elements Visible:**
  - Login form with email and password fields.
  - Security Rate Limiting badge: *"Rate limited to 5 attempts per minute per IP"*.
  - **Quick Test Credentials Pills:** Clickable pills to pre-fill demo credentials for Admin (`admin@smartintern.com`), Student (`student@smartintern.com`), Verified Company (`hr@technovaglobal.com`), and Suspicious Company (`fastjobscorp@gmail.com`).
  - Safe redirect preservation.
- **Prerequisite Data:** Standard seed data.

##### `SCR-PUB-05`: Dual-Role Registration (Student vs Company)
- **URL Route:** `http://127.0.0.1:5000/auth/register`
- **Role:** Guest / Unauthenticated
- **Key UI Elements Visible:**
  - Tabbed interface to switch between **Student** and **Company** registration.
  - Student form fields: Full Name, Email, Password (with 8+ character letter/digit rule hint), Phone, College, Degree.
  - Company form fields: Company Name, Official Work Email, Phone, Website, **Registration / GSTIN Number** (with 15-character format hint), Contact Person Name.
- **Prerequisite Data:** None.

---

#### 2. Student Role

##### `SCR-STU-01`: Student Dashboard & Key Application Metrics
- **URL Route:** `http://127.0.0.1:5000/student/dashboard`
- **Role:** Student (`student@smartintern.com` / `Student@12345`)
- **Key UI Elements Visible:**
  - Welcome greeting: *"Welcome back, Aarav Sharma"*.
  - Application metric cards: Total Applications, Under Review, Selected, Completed.
  - Recent Applications table showing employer, title, applied date, status badge.
  - Recommended Verified Internships carousel/list matching student's preferred domain.
- **Prerequisite Data:** Student account with at least 2 submitted applications.

##### `SCR-STU-02`: Student Profile & Private Resumes Management
- **URL Route:** `http://127.0.0.1:5000/student/profile`
- **Role:** Student
- **Key UI Elements Visible:**
  - Personal details form (College, Degree, CGPA, Skills tags, LinkedIn/GitHub links).
  - Profile picture / avatar upload preview.
  - **Private Resumes Management Section:**
    - List of uploaded resumes with filename, upload date, and file size.
    - Primary Resume indicator badge (`Default`).
    - "Set Primary" button.
    - **"Download"** button (served securely via private instance storage route `/student/resume/download/<id>`).
    - "Upload New Resume" form (PDF, DOCX accepted; validated with magic bytes).
- **Prerequisite Data:** Student profile with at least one uploaded resume file.

##### `SCR-STU-03`: One-Click Application Modal
- **URL Route:** Triggered on `http://127.0.0.1:5000/internships/<id>`
- **Role:** Student
- **Key UI Elements Visible:**
  - Modal overlay titled *"Apply for [Internship Title]"*.
  - Radio button group allowing student to choose between existing saved resumes.
  - Alternative file upload input to attach a fresh resume directly inside the modal.
  - Cover letter text area.
  - "Submit Application" button.
- **Prerequisite Data:** Student viewing an active internship detail page.

##### `SCR-STU-04`: Candidate Application Pipeline Tracking
- **URL Route:** `http://127.0.0.1:5000/student/applications`
- **Role:** Student
- **Key UI Elements Visible:**
  - Comprehensive table of all applications submitted by the student.
  - Columns: Internship Title, Company Name, Applied Date, Current Status, Action / Notes.
  - Color-coded status badges: `Applied` (Blue), `Under Review` (Yellow), `Selected` (Green), `Rejected` (Red).
  - "View Employer Feedback" modal button when feedback notes are provided.
- **Prerequisite Data:** Seeded applications across multiple status states.

##### `SCR-STU-05`: Whistleblower Scam Reports History
- **URL Route:** `http://127.0.0.1:5000/reports/my-reports`
- **Role:** Student
- **Key UI Elements Visible:**
  - Table of scam reports filed by the logged-in student.
  - Reported entity (Internship title or Company name), violation reason, report date.
  - Investigation status badge (`open`, `investigating`, `resolved`, `dismissed`).
  - Administrator resolution notes display.
- **Prerequisite Data:** Student has submitted at least one report via `/reports/submit`.

##### `SCR-STU-06`: In-App Notifications Feed & Unread Alerts
- **URL Route:** `http://127.0.0.1:5000/auth/notifications`
- **Role:** Student / Any Role
- **Key UI Elements Visible:**
  - Reactive red pill counter on navbar bell icon showing unread count.
  - Full notifications feed with category badges: `application`, `verification`, `scam_alert`, `report`.
  - Notification title, message body, relative timestamp.
  - Action deep-link button (e.g. "View Application", "View Detail").
  - "Mark as Read" action buttons.
- **Prerequisite Data:** Triggered notifications (e.g. welcome notification, application status update).

---

#### 3. Company Role

##### `SCR-COM-01`: Employer Dashboard & Verification Status
- **URL Route:** `http://127.0.0.1:5000/company/dashboard`
- **Role:** Verified Company (`hr@technovaglobal.com` / `Company@12345`)
- **Key UI Elements Visible:**
  - Company name header with verified badge: *"TechNova Global Solutions (Verified)"*.
  - Metric cards: Total Postings, Active Postings, Total Applicants, Selected Interns.
  - Quick action buttons ("Post New Internship", "Manage Postings", "Review Candidates").
  - Recent applicant submissions table.
- **Prerequisite Data:** Verified company with active postings and candidate applications.

##### `SCR-COM-02`: Company Profile & Verification Document Upload
- **URL Route:** `http://127.0.0.1:5000/company/profile`
- **Role:** Company
- **Key UI Elements Visible:**
  - Corporate profile form (official email, phone, website, address, contact person).
  - Validated Indian GSTIN display.
  - Company logo upload preview.
  - **Company Compliance & Verification Section:**
    - Current verification badge (`approved`, `pending`, or `rejected`).
    - Secure Document Upload input (PDF, PNG, JPG proof of registration).
    - Verification history table showing review timestamps and administrative notes.
- **Prerequisite Data:** Logged in as company.

##### `SCR-COM-03`: Post Internship Form with Validation
- **URL Route:** `http://127.0.0.1:5000/company/post-internship`
- **Role:** Verified Company
- **Key UI Elements Visible:**
  - Comprehensive opportunity authoring form:
    - Title, Domain Category dropdown.
    - Detailed description (50+ characters required).
    - Key responsibilities, Eligibility criteria, Technical skills.
    - Duration in weeks, Location mode (Remote / On-site / Hybrid), City.
    - Stipend type (Paid / Unpaid) and monthly INR stipend amount.
    - Number of openings, projected Start Date, future Application Deadline.
    - Application instructions and contact details.
  - CSRF protection token (hidden).
- **Prerequisite Data:** Company must have `verification_status='approved'`.

##### `SCR-COM-04`: Live Scam Screening Interception & Alert
- **URL Route:** Triggered on `POST /company/post-internship`
- **Role:** Company
- **Key UI Elements Visible:**
  - Form submission response showing the **Scam Detector Interception Flash**:
    - High-Risk banner: *"Your internship has been flagged as High Risk (Risk Score: 85/100) and placed under administrative quarantine. It will not be visible to students until reviewed."*
    - Notice indicating specific rules triggered (e.g. upfront fee demand or off-platform chat).
- **Prerequisite Data:** Post test internship with text: *"Selected candidates must pay a registration fee of Rs 2000. Contact on whatsapp only."*

##### `SCR-COM-05`: Manage Internships & Flagged Appeal Submission
- **URL Route:** `http://127.0.0.1:5000/company/manage-internships`
- **Role:** Company
- **Key UI Elements Visible:**
  - Table of all postings published by the employer.
  - Status badges: `active` (Green), `flagged` (Red), `closed` (Secondary).
  - Risk scores column (e.g. `10/100`, `85/100`).
  - Active/Closed toggle buttons.
  - **"Submit Appeal"** button for flagged postings opening the appeal modal with note textarea.
- **Prerequisite Data:** Employer having both active and flagged postings.

##### `SCR-COM-06`: Candidate Review & Authorized CV Serving
- **URL Route:** `http://127.0.0.1:5000/company/applicants/<internship_id>`
- **Role:** Company
- **Key UI Elements Visible:**
  - Table of student applicants for the specific internship.
  - Candidate Name, College, Degree, CGPA, Applied Date.
  - "View Cover Letter" modal button.
  - **"Download Resume" link** (verifies employer ownership; serves PDF from `instance/uploads/resumes/`).
  - Application Status update dropdown (`Applied`, `Under Review`, `Selected`, `Rejected`, `Completed`).
  - Employer feedback text box and "Update Status" button.
- **Prerequisite Data:** An internship that has received student applications.

---

#### 4. Administrator Role

##### `SCR-ADM-01`: Administrator Executive Dashboard
- **URL Route:** `http://127.0.0.1:5000/admin/dashboard`
- **Role:** Administrator (`admin@smartintern.com` / `Admin@12345`)
- **Key UI Elements Visible:**
  - Executive stat cards: Total Students, Total Companies, Pending Verifications, Total Postings, Flagged Postings, Open Scam Reports.
  - Attention Alerts: Direct badges for items requiring urgent review.
  - Recent Flagged Internships preview table with quick review links.
  - Recent Verification Requests preview table.
- **Prerequisite Data:** Seeded database with pending verifications and flagged listings.

##### `SCR-ADM-02`: Company Verification Audit Queue & Document Preview
- **URL Route:** `http://127.0.0.1:5000/admin/verifications`
- **Role:** Administrator
- **Key UI Elements Visible:**
  - Verification review queue with status filter pills (`All`, `Pending`, `Approved`, `Rejected`).
  - Table showing Company Name, Official Email, GSTIN, Contact Person, Submitted Date.
  - **"View Document"** button (serves private proof document via `/admin/verifications/document/<id>`).
  - **"Approve"** action button (modal with notes).
  - **"Reject"** action button (modal with formal rejection reason input).
- **Prerequisite Data:** At least one company with `verification_status='pending'`.

##### `SCR-ADM-03`: Quarantined Postings & Company Appeal Review
- **URL Route:** `http://127.0.0.1:5000/admin/flagged-internships`
- **Role:** Administrator
- **Key UI Elements Visible:**
  - Table of all quarantined high-risk postings (`status='flagged'`).
  - Company name, Posting title, High Risk score badge (e.g. `80/100`).
  - **Triggered Violations column:** Specific rules identified by the scam engine.
  - **Appeal Status column:** Shows if employer submitted an appeal (`Appeal: Pending`), displaying the company's appeal argument text and submission timestamp.
  - **"Approve & Restore"** button (restores listing to `active` and notifies company).
  - **"Reject & Delist"** button (marks status `rejected`, delists posting, and notifies company and enrolled applicants).
- **Prerequisite Data:** Pre-seeded scam postings (`seed.py`) with appeal submitted.

##### `SCR-ADM-04`: Community Scam Reports Investigation Center
- **URL Route:** `http://127.0.0.1:5000/admin/reports`
- **Role:** Administrator
- **Key UI Elements Visible:**
  - Table of student whistleblower reports.
  - Reporter student name, Target posting or company, Reason category, Description, Evidence link.
  - Status filter (`all`, `open`, `investigating`, `resolved`, `dismissed`).
  - "Resolve Report" action modal: Resolution notes text area, status selector, and **"Delist Associated Internship"** checkbox.
- **Prerequisite Data:** At least one open scam report filed.

##### `SCR-ADM-05`: Company Moderation Directory & Suspension Cascade
- **URL Route:** `http://127.0.0.1:5000/admin/companies`
- **Role:** Administrator
- **Key UI Elements Visible:**
  - Directory of all registered companies.
  - Verification status badges (`approved`, `pending`, `rejected`).
  - Account status badge (`Active` or `Suspended`).
  - **"Block Company"** / **"Activate"** toggle button.
  - *Demonstration of Moderation Cascade:* Blocking an employer automatically sets all their active postings to `closed` and alerts all student applicants.
- **Prerequisite Data:** Multiple registered company accounts.

##### `SCR-ADM-06`: Student Accounts Moderation Directory
- **URL Route:** `http://127.0.0.1:5000/admin/students`
- **Role:** Administrator
- **Key UI Elements Visible:**
  - Directory of registered student candidates.
  - Name, Email, College, Degree, Registration Date, Account State (`Active` / `Blocked`).
  - **"Suspend User"** / **"Activate User"** moderation buttons.
- **Prerequisite Data:** Multiple registered student accounts.

##### `SCR-ADM-07`: Domain Categories Taxonomy Management
- **URL Route:** `http://127.0.0.1:5000/admin/categories`
- **Role:** Administrator
- **Key UI Elements Visible:**
  - Table of active internship domain categories with icon preview, name, description, and postings count.
  - "Add New Domain Category" form with category name, description, and Bootstrap icon class.
- **Prerequisite Data:** Standard seed data categories.

##### `SCR-ADM-08`: System Diagnostics & Audit Action Ledger
- **URL Route:** `http://127.0.0.1:5000/admin/system-info`
- **Role:** Administrator
- **Key UI Elements Visible:**
  - **Core Model Counts:** Total Users, Students, Companies, Internships, Applications, Reports.
  - **Internships by Risk Level:** Pie/bar chart metrics for Low Risk, Medium Risk, High Risk, and Unassessed.
  - **Report Status Counts:** Open, Investigating, Resolved, Dismissed.
  - **Upload Storage Health Check:** Verification of filesystem write permissions for `instance/uploads/resumes/`, `instance/uploads/company_docs/`, and `app/static/uploads/`.
  - **Recent Administrative Audit Action Ledger:** Table showing the 10 most recent administrative moderation actions synthesized from audit logs (timestamp, action type, target entity, outcome, notes).
- **Prerequisite Data:** Logged in as administrator after performing audit actions.

---

#### 5. Scam Detection Heuristic Demonstration Captures

##### `SCR-SCAM-01`: Legitimate Opportunity Clean Safety Card
- **Demonstration:** Inspect a verified legitimate posting (e.g. *Full Stack Python Intern*).
- **Visible:** Green safety badge, Risk Score `0/100`, rule inspection card confirming:
  - No payment demands detected.
  - Legitimate corporate email domain verified.
  - Realistic stipend aligned with industry norms.
  - Standard disclaimer displayed.

##### `SCR-SCAM-02`: Medium-Risk Advisory Banner & Caution Card
- **Demonstration:** Inspect a posting with minor safety triggers (e.g. *Junior Social Media Intern*).
- **Visible:** Yellow caution badge, Risk Score `35/100`, warning card explaining:
  - Contact safety rule triggered: Employer used generic `@gmail.com` address instead of official domain.
  - Advisory notice instructing students never to transfer money or share credentials.

##### `SCR-SCAM-03`: High-Risk Scam Quarantine & Admin Appeal Screen
- **Demonstration:** Inspect *Online Data Entry & Form Filling* on Admin Flagged queue.
- **Visible:** Red badge, Risk Score `80/100`, triggered violations:
  - Upfront registration fee demanded (`refundable amount registration fee`).
  - Exorbitant stipend claims (`₹30,000/week`, `no interview needed`).
  - Generic email and off-platform WhatsApp redirect.
  - Company appeal note arguing educational intent and administrator decision buttons.

##### `SCR-SCAM-04`: Student Whistleblower Reporting Interface
- **URL Route:** `http://127.0.0.1:5000/reports/submit?internship_id=1`
- **Role:** Student
- **Visible:** Scam reporting form with violation reason options ("Demanded upfront payment", "Asked for OTP/bank credentials", "Fake job offer", "Harassment"), incident description, evidence link field, and submission confirmation.

---

### Nonexistent / Out-of-Scope Features (Do Not Include in Report)

To maintain absolute academic honesty and align with the real code implementation, the following concepts are **not implemented** and must **not** be listed as completed screens in the project report:
1. **Payment Gateway Checkout Screen:** The platform strictly prohibits employers from demanding fees from students; hence no payment gateway integration (e.g. Razorpay/Stripe) exists.
2. **Video Calling / In-App Interview Room:** Interviews are arranged directly by employers; there is no WebRTC/video conferencing screen.
3. **SMS OTP Gateway:** All OTP/verification integrations are out-of-scope; authentication relies on secure hashed password sessions and rate-limited login.
4. **Third-Party Background Check API:** Company verification is managed directly through administrative document auditing within the portal, not via external credit/government API calls.
