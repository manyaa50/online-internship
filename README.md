# Smart Online Internship Management System with Scam Prevention

A complete, production-ready web application built for a **BCA final-year project**. It features role-based access control for **Students**, **Companies**, and **Administrators**, and incorporates an automated **Scam Detection & Prevention Engine** (`scam_detector.py`) that screens every internship posting in real time using weighted heuristic analysis.

---

## 🚀 Key Modules & System Highlights

1. **Role-Based Access Control (RBAC):**
   - **Student:** Profile & resume management, search/filter opportunities, real-time safety audit badges, 1-click apply, application tracking, scam reporting.
   - **Company:** Corporate registration, administrative verification, internship posting & lifecycle management, automated scam screening preview, candidate status pipeline & feedback.
   - **Administrator:** Verification audit queue, quarantine of flagged scam listings, manual override or delisting, user account management (blocking fraudulent accounts), resolution of community scam reports.

2. **Core Scam Detection Engine (`app/scam_detector.py`):**
   - **Upfront Payment Heuristic (Weight: 35):** Flags registration fees, security deposits, training charges, laptop deposits, and payment demands.
   - **Unrealistic Claims & Stipends (Weight: 25):** Flags guaranteed job promises, 100% placement claims, "no interview needed", and exorbitant stipends (> ₹60,000/mo).
   - **Suspicious Contact Channels (Weight: 20):** Flags company postings using generic free emails (`@gmail.com`, `@yahoo.com`), and off-platform chat redirects (`Telegram`, `WhatsApp only`).
   - **Link Verification (Weight: 20):** Detects URL shorteners (`bit.ly`, `tinyurl`, `t.me`), IP-based addresses, and domain mismatches.
   - **Urgency & Panic Words (Weight: 15):** Flags "limited seats", "apply within 1 hour", and artificial scarcity pressure.
   - **Vagueness Check (Weight: 15):** Flags listings under 30 words with no responsibilities or concrete skills.
   - **Scoring & Actions:**
     - **Low (0 - 30):** Safe & published directly with a verified green safety badge.
     - **Medium (31 - 60):** Published with a cautionary advisory banner highlighting specific warning triggers.
     - **High (61 - 100):** Auto-quarantined into the admin review queue. Hidden from student listings until admin approval.

3. **In-App Notification Center:**
   - Real-time notifications for company verification outcomes, application status updates, scam warnings, and report resolutions with unread count in navbar.

---

## 🛠️ Tech Stack & Requirements

- **Backend:** Python 3.10+ with Flask (Flask-Login, Flask-WTF, Flask-SQLAlchemy, PyMySQL, Werkzeug)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons
- **Database:** MySQL 5.7+ / 8.0+ (runs on XAMPP, WAMP, or standalone MySQL)

---

## ⚙️ Setup Instructions for XAMPP / MySQL

### Step 1: Start MySQL in XAMPP
1. Open the **XAMPP Control Panel**.
2. Click **Start** next to the **MySQL** module (port `3306`).
   *(Optional: Start Apache if you want to use phpMyAdmin at `http://localhost/phpmyadmin`)*.

### Step 2: Create the Database & Import Schema
You can either import `schema.sql` via phpMyAdmin or via command prompt:

#### Option A: Via phpMyAdmin:
1. Open your browser and go to `http://localhost/phpmyadmin`.
2. Click **New** on the left menu, enter database name: `smart_internship_db`, and click **Create**.
3. Select `smart_internship_db`, click the **Import** tab at the top.
4. Click **Choose File**, select `schema.sql` from this project folder, and click **Import**.

#### Option B: Via Command Line / PowerShell (XAMPP default path):
```powershell
C:\xampp\mysql\bin\mysql.exe -u root -e "CREATE DATABASE IF NOT EXISTS smart_internship_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
C:\xampp\mysql\bin\mysql.exe -u root smart_internship_db < schema.sql
```

*(Note: If using WAMP or custom MySQL, adjust the credentials in `.env` if your root user has a password).*

---

## 💻 Running the Application

### Step 1: Create and Activate Virtual Environment
Open a terminal in the project directory (`C:\Users\Admin\Desktop\SmartInternshipSystem`):

```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Populate Database with Seed Data
Run the seeder script. This creates categories, the administrator account, sample verified companies, sample students, legitimate internships, and **2 deliberately flagged scam postings** to demo the detector:

```powershell
python seed.py
```

### Step 4: Launch the Server
```powershell
python run.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 🔑 Default Credentials for Testing & Viva Demo

| Role | Email Address | Password | Profile Name |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@smartintern.com` | `Admin@12345` | Dr. Rajesh V. Sharma |
| **Student** | `student@smartintern.com` | `Student@12345` | Aarav Sharma (BCA 3rd Year) |
| **Verified Company 1** | `hr@technovaglobal.com` | `Company@12345` | TechNova Global Solutions |
| **Verified Company 2** | `talent@cloudscalesystems.com` | `Company@12345` | CloudScale Systems |
| **Suspicious Company** | `fastjobscorp@gmail.com` | `Scam@12345` | Apex Career Ventures (Pending) |

*(Note: On the login page, you can also simply click the **Quick Test Credentials** pills to autofill any account with a single click!)*

---

## 🧪 Demo Walkthrough: Scam Detector in Action

### 1. Observing Automated Flagging (Pre-seeded Scam Postings)
1. Log in as **Administrator** (`admin@smartintern.com` / `Admin@12345`).
2. Navigate to **Flagged Postings (Scams)** in the top menu or click the red badge on the dashboard.
3. Observe **Listing 1: Online Data Entry & Form Filling**:
   - **Risk Score:** `80/100` (High Risk).
   - **Triggered Violations:** Upfront payment detected (`refundable amount registration fee`), Unrealistic earnings (`earn ₹30,000/week`, `no interview needed`), Generic email domain (`@gmail.com`), Off-platform redirect (`WhatsApp only`).
   - Notice that because it scored &ge; 61, its status was set to **Quarantined (Flagged)** and it does not show up on the public students list.
   - Click **Reject & Delist** or **Override & Approve** to observe administrative action.

### 2. Live Employer Posting & Real-Time Screening
1. Log in as verified company **TechNova Solutions** (`hr@technovaglobal.com` / `Company@12345`).
2. Go to **Post New Internship**.
3. Test creating a posting with suspicious text:
   - Title: `Urgent Java Intern - Guaranteed Placement`
   - Description: `Direct selection without interview. Selected candidates must pay registration fee of Rs 2000. Limited seats, apply within 1 hour! Contact only on whatsapp.`
   - Stipend: `80000`
4. Submit the posting.
5. Notice the system immediately displays a warning message that the posting was flagged by the safety engine with a score of `90+/100` and quarantined for administrator review!

### 3. Student Application & Warning View
1. Log in as **Student** (`student@smartintern.com` / `Student@12345`).
2. Click **Browse Internships**.
3. Open `Junior Social Media & Content Marketing Intern`:
   - Notice the **Caution Badge (Score: 35/100)**.
   - Expand the security audit box to see why: Free Gmail address was used instead of an authentic company domain.
4. Click **Apply for this Internship**:
   - Choose the pre-loaded resume or upload a new one.
   - Submit the application.
5. Navigate to **My Applications** to verify status tracking.

### 4. Reporting Fraud
1. On any internship detail page, click **Report this Posting**.
2. Select the violation category (e.g. *Demanded upfront payment*), provide notes, and submit.
3. Switch to the **Administrator** account to see the report instantly queued in **Scam Reports** with options to investigate, notify the student, or delist the company.

---

## 📁 Project Structure

```text
SmartInternshipSystem/
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
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   ├── js/
│   │   │   └── main.js
│   │   └── uploads/
│   │       ├── company_docs/
│   │       └── resumes/
│   ├── templates/
│   │   ├── admin/
│   │   │   ├── categories.html
│   │   │   ├── companies.html
│   │   │   ├── dashboard.html
│   │   │   ├── flagged_internships.html
│   │   │   ├── reports.html
│   │   │   ├── students.html
│   │   │   └── verifications.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── company/
│   │   │   ├── applicants.html
│   │   │   ├── dashboard.html
│   │   │   ├── manage_internships.html
│   │   │   ├── post_internship.html
│   │   │   └── profile.html
│   │   ├── internships/
│   │   │   ├── detail.html
│   │   │   └── list.html
│   │   ├── notifications/
│   │   │   └── list.html
│   │   ├── reports/
│   │   │   ├── my_reports.html
│   │   │   └── submit.html
│   │   ├── student/
│   │   │   ├── applications.html
│   │   │   ├── dashboard.html
│   │   │   └── profile.html
│   │   ├── base.html
│   │   └── home.html
│   ├── __init__.py
│   ├── config.py
│   ├── decorators.py
│   ├── models.py
│   └── scam_detector.py
├── .env
├── .env.example
├── .gitignore
├── AUDIT_LOG.md
├── README.md
├── requirements.txt
├── run.py
├── schema.sql
└── seed.py
```
