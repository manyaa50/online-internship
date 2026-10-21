"""
tests/test_scam_detector.py
===========================
Comprehensive test suite and labeled evaluation dataset for ScamDetector.

Covers:
  1. Text normalization (lowercase, zero-width removal, obfuscated punctuation, leetspeak 1->i, 0->o, @->a, 3->e).
  2. Bounded negation handling ('no', 'not', 'zero', 'without', 'never', 'free of' within 4 words).
  3. Credential-rule precision (UPI ID & account number require nearby action verbs).
  4. URL shorteners (verified removal of youtu.be and linktr.ee; retention of bit.ly, etc.).
  5. Payment paraphrases (rupee amount, payment apps GPay/PhonePe/Paytm/UPI, Hinglish phrases).
  6. Disclaimer consistency ("Automated rule-based risk assessment...").
  7. Labeled evaluation dataset with 36 distinct examples spanning:
     - Scam
     - Legitimate
     - Negated
     - Obfuscated
     - Paraphrased
"""
import pytest
from app.scam_detector import ScamDetector


# ═══════════════════════════════════════════════════════════════════════════════
# Labeled Evaluation Dataset (36 Examples)
# ═══════════════════════════════════════════════════════════════════════════════

LABELED_DATASET = [
    # ── Category 1: Scam Postings (7 examples) ──────────────────────────────
    {
        'id': 1,
        'category': 'scam',
        'expected_label': 'scam',
        'expected_risk_levels': ['High'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Full Stack Developer Intern - Joining Kit Fee Required',
            'description': (
                'We are hiring Full Stack Developers for immediate client deployment. '
                'Candidate must pay security deposit of ₹3,000 before receiving laptop kit and offer letter. '
                'Deposit will be refunded upon project completion.'
            ),
            'responsibilities': 'Develop web applications using React and Node.js.',
            'eligibility': 'BCA, B.Tech, or MCA students.',
            'skills_required': 'React, Node.js, MongoDB',
            'stipend_type': 'paid',
            'stipend_amount': 25000.0,
            'contact_email': 'hiring@fullstackdevs.org',
            'application_instructions': 'Pay to confirm your seat immediately.'
        }
    },
    {
        'id': 2,
        'category': 'scam',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Junior Python Backend Intern',
            'description': (
                'Exciting Python backend opportunity working on microservices. '
                'Mandatory registration fee of Rs 500 payable to confirm seat before technical onboarding.'
            ),
            'responsibilities': 'Write and debug Python REST APIs.',
            'eligibility': 'Computer science students with Python fundamentals.',
            'skills_required': 'Python, Flask, SQLite',
            'stipend_type': 'paid',
            'stipend_amount': 15000.0,
            'contact_email': 'contact@pythontech.in',
            'application_instructions': 'Submit registration fee receipt with your resume.'
        }
    },
    {
        'id': 3,
        'category': 'scam',
        'expected_label': 'scam',
        'expected_risk_levels': ['High'],
        'required_rules': ['Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'HR Operations Assistant Intern',
            'description': (
                'Manage employee records and onboarding documents. '
                'To confirm your application, please share your OTP and send bank account details to our coordinator immediately.'
            ),
            'responsibilities': 'Assist HR team in background verification and records.',
            'eligibility': 'Any graduate student with good organizational skills.',
            'skills_required': 'Excel, Communication',
            'stipend_type': 'paid',
            'stipend_amount': 12000.0,
            'contact_email': 'hr@operationscorp.com',
            'application_instructions': 'Send your aadhaar number and phone number.'
        }
    },
    {
        'id': 4,
        'category': 'scam',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Unrealistic Guarantees or Excessive Stipend'],
        'posting': {
            'title': 'Easy Data Entry Assistant Intern',
            'description': (
                'Simple copy paste work from home. Guaranteed job with 100% placement assurance. '
                'Earn ₹20,000 per day with direct selection without interview needed. Direct selection without interview.'
            ),
            'responsibilities': 'Copy text from PDF to Word files daily.',
            'eligibility': 'No experience no skills needed earn daily.',
            'skills_required': 'Typing',
            'stipend_type': 'paid',
            'stipend_amount': 60000.0,
            'contact_email': 'fastwork@gmail.com',
            'application_instructions': 'Apply right now.'
        }
    },
    {
        'id': 5,
        'category': 'scam',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Suspicious or Unverified Contact Channels'],
        'posting': {
            'title': 'Frontend Web Developer Intern',
            'description': (
                'Urgent hiring today only! Limited seats available for frontend developers. '
                'Do not email, message on WhatsApp only to +91 99999 88888 or DM on Telegram at t.me/fastinterns to claim offer letter.'
            ),
            'responsibilities': 'Design user interfaces with HTML and CSS.',
            'eligibility': 'Open to all college students.',
            'skills_required': 'HTML, CSS, JavaScript',
            'stipend_type': 'paid',
            'stipend_amount': 20000.0,
            'contact_email': 'jobs@gmail.com',
            'application_instructions': 'WhatsApp your resume to 9999988888.'
        }
    },
    {
        'id': 6,
        'category': 'scam',
        'expected_label': 'scam',
        'expected_risk_levels': ['High'],
        'required_rules': ['Suspicious Application Instructions'],
        'posting': {
            'title': 'Software Development Trainee',
            'description': (
                'Join our global engineering trainee cohort. Work on scalable distributed systems with senior staff.'
            ),
            'responsibilities': 'Code reviews and feature engineering in Java.',
            'eligibility': 'Final year students pursuing computer applications.',
            'skills_required': 'Java, Spring Boot, SQL',
            'stipend_type': 'paid',
            'stipend_amount': 22000.0,
            'contact_email': 'trainee@globaldev.com',
            'application_instructions': 'Pay rs 1000 application fee and download app to register.'
        }
    },
    {
        'id': 7,
        'category': 'scam',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Unrealistic Guarantees or Excessive Stipend'],
        'posting': {
            'title': 'Entry Level Junior Developer',
            'description': (
                'Astonishing entry level opening with high payout. '
                'We offer guaranteed placement and excessive remuneration for simple tasks.'
            ),
            'responsibilities': 'Assist in testing simple internal web pages.',
            'eligibility': 'Open to freshers without assessment.',
            'skills_required': 'Basic computer literacy',
            'stipend_type': 'paid',
            'stipend_amount': 95000.0,  # Extreme stipend (> 60,000)
            'contact_email': 'contact@entrylevelcareers.com',
            'application_instructions': 'Register today.'
        }
    },

    # ── Category 2: Legitimate Postings (8 examples) ────────────────────────
    {
        'id': 8,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Junior Python Web Developer Intern',
            'description': (
                'We are seeking a motivated Python intern to join our engineering team. '
                'You will assist in developing RESTful APIs using Flask and SQLAlchemy, '
                'participate in agile sprints, write clean unit tests, and collaborate with '
                'front-end engineers to deliver robust features.'
            ),
            'responsibilities': (
                'Write clean modular Python code. Participate in daily standups and code reviews. '
                'Debug database queries and write automated pytest test cases.'
            ),
            'eligibility': 'Pursuing BCA, MCA, or B.Tech in Computer Science with minimum 60% aggregate.',
            'skills_required': 'Python, Flask, SQLAlchemy, Git, Relational Databases',
            'stipend_type': 'paid',
            'stipend_amount': 15000.0,
            'contact_email': 'careers@acmesoftware.org',
            'application_instructions': 'Submit your GitHub profile and resume through the campus portal.'
        }
    },
    {
        'id': 9,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Data Science & Analytics Intern',
            'description': (
                'Acme Insights is looking for a Data Analytics intern to analyze user telemetry and product metrics. '
                'You will write SQL queries, clean raw CSV datasets using pandas, and build visualization dashboards '
                'for executive decision making.'
            ),
            'responsibilities': (
                'Extract data from MySQL databases. Clean and transform unstructured data using pandas. '
                'Create interactive charts in Tableau or Matplotlib.'
            ),
            'eligibility': 'Pre-final or final year students with strong statistical knowledge.',
            'skills_required': 'Python, Pandas, SQL, Data Visualization, Statistics',
            'stipend_type': 'paid',
            'stipend_amount': 18000.0,
            'contact_email': 'internships@acmeinsights.io',
            'application_instructions': 'Attach your latest academic transcripts and portfolio link.'
        }
    },
    {
        'id': 10,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'UI/UX Product Design Intern',
            'description': (
                'Join our product design guild to craft seamless user experiences for enterprise cloud tools. '
                'You will design wireframes, high-fidelity mockups, and interactive prototypes in Figma, '
                'and conduct user feedback interviews.'
            ),
            'responsibilities': (
                'Create design systems and UI components in Figma. Conduct usability testing with customer cohorts. '
                'Coordinate with developers during component handover.'
            ),
            'eligibility': 'Students with an active Behance or Dribbble design portfolio.',
            'skills_required': 'Figma, Adobe XD, Wireframing, User Research, Prototyping',
            'stipend_type': 'paid',
            'stipend_amount': 16000.0,
            'contact_email': 'designteam@studiocraft.co',
            'application_instructions': 'Provide a link to your Figma or Behance design portfolio.'
        }
    },
    {
        'id': 11,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Technical Content Writer Intern',
            'description': (
                'We are hiring a technical content writer to draft developer tutorials, API documentation, '
                'and architectural blogs explaining cloud-native software architecture clearly to student developers.'
            ),
            'responsibilities': (
                'Research modern software frameworks. Write engaging, accurate technical walkthroughs. '
                'Proofread documentation for grammar and clarity.'
            ),
            'eligibility': 'Demonstrated technical writing capability and excellent written English.',
            'skills_required': 'Technical Writing, Markdown, Git, Software Concepts',
            'stipend_type': 'paid',
            'stipend_amount': 12000.0,
            'contact_email': 'editor@devpublishers.org',
            'application_instructions': 'Share two published technical writing samples.'
        }
    },
    {
        'id': 12,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Mobile Application Development Intern (Flutter)',
            'description': (
                'Develop cross-platform mobile application modules using Flutter and Dart. '
                'You will integrate REST endpoints, manage local state with BLoC or Provider, '
                'and ensure responsive UI rendering on diverse Android and iOS screen sizes.'
            ),
            'responsibilities': (
                'Build mobile screens in Flutter. Connect REST services with json serialization. '
                'Test application builds on emulators and physical test devices.'
            ),
            'eligibility': 'Enrolled in Computer Applications or Information Technology degree.',
            'skills_required': 'Flutter, Dart, Mobile App Architecture, RESTful Services',
            'stipend_type': 'paid',
            'stipend_amount': 20000.0,
            'contact_email': 'mobileleads@appinnovators.net',
            'application_instructions': 'Submit an APK or GitHub repository link of a Flutter project.'
        }
    },
    {
        'id': 13,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'FinTech Backend Integration Intern (API Development)',
            'description': (
                'Work on our payment gateway integration engine. Candidates will write unit tests for account number format '
                'validation and UPI ID protocol handlers. You will work on database schema design for transaction logs.'
            ),
            'responsibilities': (
                'Design MySQL tables for ledger records. Implement unit tests verifying account number formats. '
                'Test payment callback webhook endpoints in local sandbox environment.'
            ),
            'eligibility': 'Sound knowledge of backend databases and API protocols.',
            'skills_required': 'Python, SQL, Payment Gateway APIs, Unit Testing',
            'stipend_type': 'paid',
            'stipend_amount': 22000.0,
            'contact_email': 'recruiting@fintechscale.io',
            'application_instructions': 'Apply with your resume through our portal.'
        }
    },
    {
        'id': 14,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Cloud DevOps & Infrastructure Intern',
            'description': (
                'Learn automated deployment pipelines with our site reliability engineering team. '
                'You will containerize Python microservices with Docker, write GitHub Actions workflows, '
                'and inspect server metrics.'
            ),
            'responsibilities': (
                'Author Dockerfiles for test environments. Configure CI/CD linting and test workflows. '
                'Monitor server uptime using Grafana dashboards.'
            ),
            'eligibility': 'Basic familiarity with Linux commands and Git version control.',
            'skills_required': 'Linux, Docker, CI/CD, Bash Scripting, Git',
            'stipend_type': 'paid',
            'stipend_amount': 17000.0,
            'contact_email': 'infra@cloudopsplatform.com',
            'application_instructions': 'Share your GitHub handle and resume.'
        }
    },
    {
        'id': 15,
        'category': 'legitimate',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested', 'Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Machine Learning Research Intern',
            'description': (
                'Research computer vision algorithms for automated plant leaf disease detection. '
                'You will train convolutional neural networks using PyTorch, benchmark inference speeds, '
                'and document experimental results in technical reports.'
            ),
            'responsibilities': (
                'Annotate image datasets. Train deep learning models with PyTorch. '
                'Evaluate classification precision, recall, and F1 scores.'
            ),
            'eligibility': 'Enrolled in Bachelor or Master degree in computer science or AI.',
            'skills_required': 'Python, PyTorch, OpenCV, Deep Learning',
            'stipend_type': 'paid',
            'stipend_amount': 25000.0,
            'contact_email': 'lab@airesearchinstitute.org',
            'application_instructions': 'Provide relevant machine learning course projects or papers.'
        }
    },

    # ── Category 3: Negated Postings (8 examples) ───────────────────────────
    {
        'id': 16,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Junior Software Tester Intern (QA)',
            'description': (
                'We are hiring software testing interns for automated regression suites. '
                'Please note that we require no registration fee from any candidate. Selection is purely merit-based.'
            ),
            'responsibilities': 'Execute manual test cases and write automated Selenium scripts.',
            'eligibility': 'Candidates with keen attention to detail.',
            'skills_required': 'Manual Testing, Selenium, Python, Test Cases',
            'stipend_type': 'paid',
            'stipend_amount': 14000.0,
            'contact_email': 'qa@qualitysystems.org',
            'application_instructions': 'Apply directly via our student recruitment form.'
        }
    },
    {
        'id': 17,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Frontend Developer Intern',
            'description': (
                'Build interactive web dashboards using Vue.js and Tailwind CSS. '
                'You will participate in user story refinement and sprint planning with senior developers. '
                'Selected candidates do not pay any security deposit. No training fee is required.'
            ),
            'responsibilities': 'Develop Vue components and integrate backend APIs for our clients.',
            'eligibility': 'Students with knowledge of HTML, CSS, and modern JavaScript.',
            'skills_required': 'Vue.js, Tailwind CSS, JavaScript, Git',
            'stipend_type': 'paid',
            'stipend_amount': 15000.0,
            'contact_email': 'hr@vuecreations.net',
            'application_instructions': 'Submit your GitHub portfolio.'
        }
    },
    {
        'id': 18,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Database Administrator Intern',
            'description': (
                'Assist in tuning MySQL queries and maintaining database backup routines. '
                'This internship features zero application fee and zero registration charges for college applicants.'
            ),
            'responsibilities': 'Monitor query performance and index optimization.',
            'eligibility': 'Students studying database management systems.',
            'skills_required': 'MySQL, SQL Query Optimization, Database Indexing',
            'stipend_type': 'paid',
            'stipend_amount': 16000.0,
            'contact_email': 'dbteam@enterprisedata.co',
            'application_instructions': 'Apply with your academic resume.'
        }
    },
    {
        'id': 19,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Full Stack Java Intern',
            'description': (
                'Develop enterprise Spring Boot services and microservices. '
                'All training and developer kits are free of any training fee or kit charges.'
            ),
            'responsibilities': 'Implement Java controllers and service layers.',
            'eligibility': 'BCA or B.Tech students with Java programming skills.',
            'skills_required': 'Java, Spring Boot, Hibernate, MySQL',
            'stipend_type': 'paid',
            'stipend_amount': 18000.0,
            'contact_email': 'careers@javatechsolutions.org',
            'application_instructions': 'Upload your resume and code samples.'
        }
    },
    {
        'id': 20,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Cybersecurity Operations Intern',
            'description': (
                'Learn threat intelligence and security log auditing with our SOC team. '
                'Note: Our team will never ask for your account number or OTP. Always report suspicious recruiters.'
            ),
            'responsibilities': 'Analyze system audit logs and report anomalous traffic.',
            'eligibility': 'Interest in cybersecurity and network fundamentals.',
            'skills_required': 'Networking, Linux, Wireshark, Log Analysis',
            'stipend_type': 'paid',
            'stipend_amount': 20000.0,
            'contact_email': 'security@cyberdefenders.io',
            'application_instructions': 'Apply via official portal link.'
        }
    },
    {
        'id': 21,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Node.js Backend Developer Intern',
            'description': (
                'Build asynchronous services using Express.js and Redis caching. '
                'Candidates can begin their internship journey without any registration fee or upfront payment.'
            ),
            'responsibilities': 'Write unit tests and optimize API latency.',
            'eligibility': 'Knowledge of JavaScript and asynchronous event loops.',
            'skills_required': 'Node.js, Express, Redis, MongoDB',
            'stipend_type': 'paid',
            'stipend_amount': 19000.0,
            'contact_email': 'hiring@nodeworks.net',
            'application_instructions': 'Share your resume and GitHub links.'
        }
    },
    {
        'id': 22,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Angular Frontend Developer Intern',
            'description': (
                'Develop enterprise single-page applications using Angular and TypeScript. '
                'Security Warning: Do not pay via GPay or transfer money to anyone claiming to represent our company.'
            ),
            'responsibilities': 'Create reusable Angular components and services.',
            'eligibility': 'Proficiency in TypeScript and component architecture.',
            'skills_required': 'Angular, TypeScript, RxJS, HTML5',
            'stipend_type': 'paid',
            'stipend_amount': 17000.0,
            'contact_email': 'talent@angulardevelopers.org',
            'application_instructions': 'Send your resume directly.'
        }
    },
    {
        'id': 23,
        'category': 'negated',
        'expected_label': 'legitimate',
        'expected_risk_levels': ['Low'],
        'forbidden_rules': ['Sensitive Credential or Financial Data Requested', 'Suspicious Application Instructions'],
        'posting': {
            'title': 'API Systems Quality Intern',
            'description': (
                'Review API specifications and run automated integration suites. '
                'Our recruitment process is completely free for all students.'
            ),
            'responsibilities': 'Execute Postman collections and analyze response payloads.',
            'eligibility': 'Computer science undergraduates.',
            'skills_required': 'Postman, REST APIs, JSON, Git',
            'stipend_type': 'paid',
            'stipend_amount': 16000.0,
            'contact_email': 'hr@qualityapis.com',
            'application_instructions': 'Submit resume. We never request OTP or bank details from students.'
        }
    },

    # ── Category 4: Obfuscated Postings (6 examples) ────────────────────────
    {
        'id': 24,
        'category': 'obfuscated',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Web Development Intern - Fast Onboarding',
            'description': (
                'Great web development opportunity. Mandatory r.e.g.i.s.t.r.a.t.i.o.n f..e..e before onboarding kit is dispatched. '
                'Candidate must p.a.y to confirm slot.'
            ),
            'responsibilities': 'Build websites and landing pages.',
            'eligibility': 'Any college student.',
            'skills_required': 'HTML, CSS',
            'stipend_type': 'paid',
            'stipend_amount': 15000.0,
            'contact_email': 'recruiter@quickcareers.org',
            'application_instructions': 'Pay fee online.'
        }
    },
    {
        'id': 25,
        'category': 'obfuscated',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Backend Engineering Trainee',
            'description': (
                'Exciting project in backend engineering. '
                'Candidate must p@y r3g1strat10n f33 of rs 500 to c0nf1rm slot before batch starts.'
            ),
            'responsibilities': 'Assist in database integration.',
            'eligibility': 'Open to freshers.',
            'skills_required': 'Python',
            'stipend_type': 'paid',
            'stipend_amount': 18000.0,
            'contact_email': 'onboarding@devcohort.in',
            'application_instructions': 'Pay to confirm.'
        }
    },
    {
        'id': 26,
        'category': 'obfuscated',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Remote Data Entry Associate',
            'description': (
                'Work from home data entry. Must pay r\u200be\u200bg\u200bi\u200bs\u200bt\u200br\u200ba\u200bt\u200bi\u200bo\u200bn fee '
                'of ₹1000 before receiving data files.'
            ),
            'responsibilities': 'Enter data in online spreadsheets.',
            'eligibility': 'Anyone with basic computer access.',
            'skills_required': 'Typing',
            'stipend_type': 'paid',
            'stipend_amount': 12000.0,
            'contact_email': 'office@remoteworks.org',
            'application_instructions': 'Complete registration deposit.'
        }
    },
    {
        'id': 27,
        'category': 'obfuscated',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Sensitive Credential or Financial Data Requested'],
        'posting': {
            'title': 'Operations Verification Trainee',
            'description': (
                'Review customer registration workflows. '
                'Please s3nd 0tp and share b@nk acc0unt details to HR for verification.'
            ),
            'responsibilities': 'Process customer records.',
            'eligibility': 'College students.',
            'skills_required': 'Communication',
            'stipend_type': 'paid',
            'stipend_amount': 14000.0,
            'contact_email': 'support@verifyhub.net',
            'application_instructions': 'Share OTP when called.'
        }
    },
    {
        'id': 28,
        'category': 'obfuscated',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Digital Marketing Campaign Intern',
            'description': (
                'Run social media advertising campaigns. '
                'S.e.c.u.r.i.t.y d.e.p.o.s.i.t of 2000 inr required for campaign toolkit activation.'
            ),
            'responsibilities': 'Publish promotional posts.',
            'eligibility': 'All students eligible.',
            'skills_required': 'Social Media',
            'stipend_type': 'paid',
            'stipend_amount': 15000.0,
            'contact_email': 'campaigns@socialpromo.co',
            'application_instructions': 'Send deposit proof.'
        }
    },
    {
        'id': 29,
        'category': 'obfuscated',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested', 'Artificial Urgency & Scarcity Tactics'],
        'posting': {
            'title': 'Creative Copywriting Assistant',
            'description': (
                'Write articles and social media blurbs. '
                'Hurry 0nly 1 sp0t left! P@y before joining to reserve your onboarding kit.'
            ),
            'responsibilities': 'Draft short blog articles.',
            'eligibility': 'Good writing skills.',
            'skills_required': 'Copywriting',
            'stipend_type': 'paid',
            'stipend_amount': 10000.0,
            'contact_email': 'copy@contentstudio.net',
            'application_instructions': 'Pay to book seat.'
        }
    },

    # ── Category 5: Paraphrased Postings (7 examples) ───────────────────────
    {
        'id': 30,
        'category': 'paraphrased',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Junior React Developer Intern',
            'description': (
                'Work on modern React dashboards. '
                'Selected applicant must pay via GPay to confirm acceptance of offer.'
            ),
            'responsibilities': 'Create frontend components.',
            'eligibility': 'Knowledge of JavaScript.',
            'skills_required': 'React, JavaScript',
            'stipend_type': 'paid',
            'stipend_amount': 20000.0,
            'contact_email': 'hr@reactinnovate.io',
            'application_instructions': 'GPay transaction ID required.'
        }
    },
    {
        'id': 31,
        'category': 'paraphrased',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Graphic Design Associate Intern',
            'description': (
                'Design social media flyers and marketing assets. '
                'Please transfer 1000 INR through PhonePe to our administrative manager to secure your joining date.'
            ),
            'responsibilities': 'Design graphics using Photoshop or Canva.',
            'eligibility': 'Creative design mindset.',
            'skills_required': 'Photoshop, Graphic Design',
            'stipend_type': 'paid',
            'stipend_amount': 12000.0,
            'contact_email': 'graphics@visualdesigns.org',
            'application_instructions': 'Transfer via PhonePe.'
        }
    },
    {
        'id': 32,
        'category': 'paraphrased',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Operations Support Intern',
            'description': (
                'Coordinate logistics and customer emails. '
                'Candidate must send 500 rupees on Paytm for background verification check.'
            ),
            'responsibilities': 'Respond to customer support tickets.',
            'eligibility': 'High school or college graduates.',
            'skills_required': 'Customer Service, Email Writing',
            'stipend_type': 'paid',
            'stipend_amount': 11000.0,
            'contact_email': 'support@servicehub.org',
            'application_instructions': 'Paytm payment receipt must be uploaded.'
        }
    },
    {
        'id': 33,
        'category': 'paraphrased',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'SEO & Content Marketing Intern',
            'description': (
                'Optimize website blogs for search engines. '
                'Candidate must deposit ₹1500 before starting work to cover software toolkit license.'
            ),
            'responsibilities': 'Keyword research and blog updates.',
            'eligibility': 'Basic knowledge of SEO concepts.',
            'skills_required': 'SEO, Keyword Research, Content Strategy',
            'stipend_type': 'paid',
            'stipend_amount': 13000.0,
            'contact_email': 'seo@rankboosters.net',
            'application_instructions': 'Deposit ₹1500 to our company bank account.'
        }
    },
    {
        'id': 34,
        'category': 'paraphrased',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Data Annotation Trainee',
            'description': (
                'Label images and bounding boxes for machine learning training. '
                'Is internship training ke liye candidate ko paise dena hoga pehle.'
            ),
            'responsibilities': 'Label visual data accurately.',
            'eligibility': 'Open to all students.',
            'skills_required': 'Data Entry, Attention to Detail',
            'stipend_type': 'paid',
            'stipend_amount': 10000.0,
            'contact_email': 'datasets@annotationlab.org',
            'application_instructions': 'Paise transfer karke screenshot bhejein.'
        }
    },
    {
        'id': 35,
        'category': 'paraphrased',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Customer Support Trainee Intern',
            'description': (
                'Handle incoming customer calls and inquiries remotely. '
                'Laptop courier charges ke liye rupaye dena hoga joining se pehle.'
            ),
            'responsibilities': 'Answer incoming client queries politely.',
            'eligibility': 'Fluent in Hindi and English.',
            'skills_required': 'Communication, Phone Support',
            'stipend_type': 'paid',
            'stipend_amount': 12000.0,
            'contact_email': 'support@voicecare.net',
            'application_instructions': 'Rupaye jama karein.'
        }
    },
    {
        'id': 36,
        'category': 'paraphrased',
        'expected_label': 'scam',
        'expected_risk_levels': ['High', 'Medium'],
        'required_rules': ['Upfront Payment Requested'],
        'posting': {
            'title': 'Mobile Flutter Developer Intern',
            'description': (
                'Build mobile apps in Flutter. '
                'Transfer amount on UPI to our onboarding team before signing the agreement.'
            ),
            'responsibilities': 'Develop Flutter widgets and screens.',
            'eligibility': 'Basic Dart programming knowledge.',
            'skills_required': 'Flutter, Dart, Git',
            'stipend_type': 'paid',
            'stipend_amount': 18000.0,
            'contact_email': 'team@fluttercraft.io',
            'application_instructions': 'UPI payment confirmation required.'
        }
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Text Normalization Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_normalization_lowercase_and_whitespace():
    """Text is lowercased and repeated whitespace is collapsed."""
    raw = "  URGENT   HIRING   TODAY   ONLY  "
    normalized = ScamDetector.normalize_text(raw)
    assert normalized == "urgent hiring today only"


def test_normalization_removes_zero_width_characters():
    """Zero-width Unicode characters are cleanly stripped."""
    raw = "r\u200be\u200bg\u200bi\u200bs\u200bt\u200br\u200ba\u200bt\u200bi\u200bo\u200bn fee"
    normalized = ScamDetector.normalize_text(raw)
    assert normalized == "registration fee"


def test_normalization_collapses_obfuscated_dots_inside_words():
    """Single-character spaced dots and repeated dots inside words are collapsed."""
    assert ScamDetector.normalize_text("p.a.y.m.e.n.t required") == "payment required"
    assert ScamDetector.normalize_text("f..e..e is mandatory") == "fee is mandatory"
    assert ScamDetector.normalize_text("s.e.c.u.r.i.t.y deposit") == "security deposit"


def test_normalization_leetspeak_mappings_while_preserving_numbers():
    """
    Normalizes common leetspeak: 1->i, 0->o, @->a, 3->e in words,
    while preserving purely numeric amounts, currency contexts, and email domains.
    """
    # De-obfuscation in words
    assert "payment" in ScamDetector.normalize_text("p@yment")
    assert "security" in ScamDetector.normalize_text("s3cur1ty")
    assert "deposit" in ScamDetector.normalize_text("d3p0s1t")
    assert "account" in ScamDetector.normalize_text("acc0unt")
    assert "otp" in ScamDetector.normalize_text("0tp")

    # Preservation of numbers and currency amounts
    norm_amount = ScamDetector.normalize_text("pay rs 10000 stipend")
    assert "10000" in norm_amount
    assert "rs" in norm_amount

    norm_pct = ScamDetector.normalize_text("100% placement")
    assert "100%" in norm_pct

    norm_email = ScamDetector.normalize_text("contact hr@company.com")
    assert "hr@company.com" in norm_email


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Negation Handling Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("negated_phrase,keyword", [
    ("We charge no registration fee for candidates.", "registration fee"),
    ("Candidates do not need to pay security deposit.", "security deposit"),
    ("This internship is free of any training fee.", "training fee"),
    ("Zero application fee is charged to applicants.", "application fee"),
    ("Start your internship without any registration fee.", "registration fee"),
    ("We never request your account number.", "account number"),
    ("Our team will never ask for your otp.", "otp"),
])
def test_negation_suppresses_rule_matches(negated_phrase, keyword):
    """When a payment/credential keyword is preceded by negation within 4 words, rule is suppressed."""
    pos = negated_phrase.lower().find(keyword.lower())
    assert pos != -1
    assert ScamDetector._is_negated(negated_phrase.lower(), pos) is True


@pytest.mark.parametrize("affirmative_phrase,keyword", [
    ("Candidates must pay registration fee of 500.", "registration fee"),
    ("Security deposit is required before joining.", "security deposit"),
    ("Training fee must be deposited.", "training fee"),
    ("No experience needed. Candidates must pay registration fee of 500.", "registration fee"),
    ("Please share your account number.", "account number"),
    ("Send your otp to verify identity.", "otp"),
])
def test_affirmative_phrases_are_not_negated(affirmative_phrase, keyword):
    """Affirmative phrases or phrases where negation is in another sentence are NOT negated."""
    pos = affirmative_phrase.lower().find(keyword.lower())
    assert pos != -1
    assert ScamDetector._is_negated(affirmative_phrase.lower(), pos) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Credential Rule Precision Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_credential_rule_triggers_when_paired_with_action_verbs():
    """UPI ID and account number trigger credential rule when paired with share, send, provide, enter, submit."""
    verbs = ['share', 'send', 'provide', 'enter', 'submit']
    for v in verbs:
        posting = {
            'title': 'Test Role',
            'description': f'Please {v} your UPI ID and bank account number to HR to proceed with onboarding.',
            'responsibilities': 'Assisting team.',
            'eligibility': 'All graduates.',
            'skills_required': 'Excel',
            'stipend_type': 'paid',
            'stipend_amount': 10000,
            'contact_email': 'hr@legitco.org'
        }
        res = ScamDetector.evaluate_posting(posting)
        rule_names = [r['rule'] for r in res['triggered_rules']]
        assert 'Sensitive Credential or Financial Data Requested' in rule_names, f"Failed for verb {v}"


def test_credential_rule_does_not_trigger_for_ordinary_descriptions():
    """Ordinary discussions of UPI ID or account number in job duties do NOT trigger credential rule."""
    posting = {
        'title': 'FinTech Software Engineering Intern',
        'description': (
            'We build enterprise banking solutions. The intern will design SQL tables for user account number fields '
            'and implement algorithms to validate UPI ID checksums.'
        ),
        'responsibilities': 'Write automated test cases for payment API schemas and documentation.',
        'eligibility': 'Computer science students with SQL knowledge.',
        'skills_required': 'Python, SQL, REST APIs',
        'stipend_type': 'paid',
        'stipend_amount': 20000,
        'contact_email': 'careers@fintechfirm.com'
    }
    res = ScamDetector.evaluate_posting(posting)
    rule_names = [r['rule'] for r in res['triggered_rules']]
    assert 'Sensitive Credential or Financial Data Requested' not in rule_names


# ═══════════════════════════════════════════════════════════════════════════════
# 4. URL Shortener Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_youtube_and_linktree_removed_from_shorteners():
    """youtu.be and linktr.ee must NOT trigger the suspicious link shortener rule."""
    posting = {
        'title': 'Video Editor & Media Intern',
        'description': (
            'Edit product videos for our social channels. '
            'View our sample video at youtu.be/sample123 and see our portfolio at linktr.ee/companyportfolio.'
        ),
        'responsibilities': 'Video editing with Premiere Pro and After Effects.',
        'eligibility': 'Creative students with video portfolio.',
        'skills_required': 'Premiere Pro, After Effects',
        'stipend_type': 'paid',
        'stipend_amount': 15000,
        'contact_email': 'media@productionhouse.org'
    }
    res = ScamDetector.evaluate_posting(posting)
    rule_names = [r['rule'] for r in res['triggered_rules']]
    assert 'Shortened or Mismatched External Links' not in rule_names


def test_standard_url_shorteners_still_detected():
    """bit.ly, tinyurl.com, t.co, etc. are still detected as suspicious link shorteners."""
    for shortener in ['bit.ly/testjob', 'tinyurl.com/testjob', 't.co/testjob', 'is.gd/testjob']:
        posting = {
            'title': 'Marketing Intern',
            'description': f'Apply at {shortener} to reserve your interview slot immediately.',
            'responsibilities': 'Drafting social media posts.',
            'eligibility': 'Any student.',
            'skills_required': 'Communication',
            'stipend_type': 'paid',
            'stipend_amount': 10000,
            'contact_email': 'hr@acmeco.org'
        }
        res = ScamDetector.evaluate_posting(posting)
        rule_names = [r['rule'] for r in res['triggered_rules']]
        assert 'Shortened or Mismatched External Links' in rule_names


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Disclaimer Text Test
# ═══════════════════════════════════════════════════════════════════════════════

def test_disclaimer_text_matches_specification():
    """Disclaimer must be 'Automated rule-based risk assessment. This result is not proof of fraud or legitimacy.'"""
    expected_disclaimer = "Automated rule-based risk assessment. This result is not proof of fraud or legitimacy."
    assert ScamDetector.DISCLAIMER_TEXT == expected_disclaimer

    posting = {
        'title': 'Test Post',
        'description': 'A simple test description for testing disclaimer output.',
        'responsibilities': 'Tasks here.',
        'eligibility': 'Open.',
        'skills_required': 'Python',
        'contact_email': 'test@example.com'
    }
    res = ScamDetector.evaluate_posting(posting)
    assert res['disclaimer'] == expected_disclaimer


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Evaluation on 36 Labeled Dataset Examples (Individual Assertions)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize('example', LABELED_DATASET, ids=lambda ex: f"ex_{ex['id']:02d}_{ex['category']}_{ex['expected_label']}")
def test_individual_labeled_example(example):
    """
    Evaluates each labeled example individually against ScamDetector heuristics.
    Checks:
      - Risk level matches expected risk levels (e.g. ['Low'] for legitimate/negated, ['High', 'Medium'] for scam)
      - Required rules are triggered when specified
      - Forbidden rules are NOT triggered when specified
      - Expected binary label matches mapped prediction (score >= 31 -> scam, <= 30 -> legitimate)
    """
    posting = example['posting']
    res = ScamDetector.evaluate_posting(posting)
    risk_level = res['risk_level']
    risk_score = res['risk_score']
    triggered_rules = [r['rule'] for r in res['triggered_rules']]

    # 1. Check predicted risk level
    assert risk_level in example['expected_risk_levels'], (
        f"Example {example['id']} ({example['category']}) failed: "
        f"got risk_level='{risk_level}' (score={risk_score}), "
        f"expected one of {example['expected_risk_levels']}. "
        f"Triggered rules: {triggered_rules}"
    )

    # 2. Check binary label mapping (threshold: score >= 31 is scam, score <= 30 is legitimate)
    predicted_label = 'scam' if risk_score >= 31 else 'legitimate'
    assert predicted_label == example['expected_label'], (
        f"Example {example['id']} ({example['category']}) binary label mismatch: "
        f"predicted '{predicted_label}' (score={risk_score}), expected '{example['expected_label']}'."
    )

    # 3. Check required rules (if any)
    for req_rule in example.get('required_rules', []):
        assert req_rule in triggered_rules, (
            f"Example {example['id']} expected rule '{req_rule}' to trigger, "
            f"but triggered rules were: {triggered_rules}"
        )

    # 4. Check forbidden rules (if any)
    for forb_rule in example.get('forbidden_rules', []):
        assert forb_rule not in triggered_rules, (
            f"Example {example['id']} rule '{forb_rule}' should NOT trigger, "
            f"but it was triggered. All triggered: {triggered_rules}"
        )
