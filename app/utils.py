"""
app/utils.py
============
Shared utility and validation functions for SmartInternshipSystem.
"""
import os
import re
import zipfile
from datetime import datetime, date
from urllib.parse import urlsplit, unquote
from werkzeug.utils import secure_filename
from flask import current_app
import email_validator

from app.models import db, InternshipCategory


# ═══════════════════════════════════════════════════════════════════════════════
# URL & Security Validation
# ═══════════════════════════════════════════════════════════════════════════════

def is_safe_redirect_url(target):
    """
    Validates that a redirect target URL is a safe local relative path to prevent
    open redirect attacks.

    Requirements:
      - Must be a non-empty string.
      - Must start with exactly one '/' (reject '//', '///').
      - Cannot contain backslashes ('\\' or '%5C' or '%5c').
      - Cannot contain ASCII control characters (< 32 or == 127).
      - Cannot have a URL scheme (e.g. http:, https:, javascript:, data:).
      - Cannot have a netloc (hostname or domain).
      - Unquoted target must also adhere to all safety checks.

    Returns:
        bool: True if safe to redirect to, False otherwise.
    """
    if not target or not isinstance(target, str):
        return False

    trimmed = target.strip()
    if not trimmed:
        return False

    # Check for control characters in raw string
    if any(ord(c) < 32 or ord(c) == 127 for c in trimmed):
        return False

    # Reject backslash tricks in raw string
    if '\\' in trimmed or '%5c' in trimmed.lower():
        return False

    # Must start with exactly one '/'
    if not trimmed.startswith('/') or trimmed.startswith('//'):
        return False

    # Reject encoded protocol-relative double slash
    if '%2f%2f' in trimmed.lower():
        return False

    try:
        parsed = urlsplit(trimmed)
    except Exception:
        return False

    # Must not have a scheme (e.g., http, https, javascript, data)
    if parsed.scheme:
        return False

    # Must not have a netloc (hostname/authority)
    if parsed.netloc:
        return False

    # Also inspect URL-decoded representation
    unquoted = unquote(trimmed)
    if any(ord(c) < 32 or ord(c) == 127 for c in unquoted):
        return False
    if '\\' in unquoted or unquoted.startswith('//') or not unquoted.startswith('/'):
        return False

    try:
        unquoted_parsed = urlsplit(unquoted)
        if unquoted_parsed.scheme or unquoted_parsed.netloc:
            return False
    except Exception:
        return False

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Input & Credential Validation
# ═══════════════════════════════════════════════════════════════════════════════

def validate_email_address(email):
    """
    Validates an email address using email-validator.

    Returns:
        tuple (is_valid: bool, error_message: str, normalized_email: str)
    """
    if not email or not str(email).strip():
        return False, "Email address is required.", ""

    raw = str(email).strip().lower()
    try:
        valid = email_validator.validate_email(raw, check_deliverability=False)
        return True, "", valid.normalized
    except email_validator.EmailNotValidError as e:
        return False, f"Invalid email format: {str(e)}", ""


def validate_indian_phone(phone):
    """
    Validates an Indian phone number format:
    10-digit mobile number starting with 6, 7, 8, or 9,
    optionally prefixed with '+91', '91', or '0', with optional spaces or hyphens.

    Returns:
        tuple (is_valid: bool, error_message: str, normalized_phone: str)
    """
    if not phone or not str(phone).strip():
        return False, "Phone number is required.", ""

    raw = str(phone).strip()
    # Strip whitespace and hyphens for regex checking
    cleaned = re.sub(r'[\s\-]+', '', raw)

    match = re.match(r'^(?:\+91|91|0)?([6-9]\d{9})$', cleaned)
    if not match:
        return False, "Invalid Indian phone number. Please enter a valid 10-digit mobile number.", ""

    return True, "", raw


def validate_gstin(gst_number):
    """
    Validates an Indian Goods and Services Tax Identification Number (GSTIN)
    using a loose but meaningful 15-character format check:
      - 2 digits: State code
      - 5 alphabets + 4 digits + 1 alphabet: PAN
      - 1 alphanumeric entity code
      - 1 character: 'Z' by default
      - 1 alphanumeric checksum character

    Returns:
        tuple (is_valid: bool, error_message: str, normalized_gstin: str)
    """
    if not gst_number or not str(gst_number).strip():
        return False, "GSTIN is required.", ""

    normalized = str(gst_number).strip().upper()
    gst_regex = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if not re.match(gst_regex, normalized):
        return False, "Invalid Indian GSTIN format. Expected 15-character alphanumeric format (e.g. 29ABCDE1234F1Z5).", ""

    return True, "", normalized


def validate_password(password):
    """
    Enforces minimum 8 characters, at least one letter, and at least one digit.

    Returns:
        tuple (is_valid: bool, error_message: str)
    """
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit."
    return True, ""


# ═══════════════════════════════════════════════════════════════════════════════
# Internship Form Validation (Shared between Create and Edit)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_internship_form(form_data, company=None):
    """
    Shared validator for create_internship and edit_internship routes.
    Safely validates and parses:
      - Required fields and minimum text lengths
      - Application deadlines in the future (> today)
      - Non-negative stipend amount
      - Valid integer durations and openings
      - Valid domain category in database
      - Valid contact email and phone

    Never raises uncaught exceptions or triggers HTTP 500 errors.

    Returns:
        tuple (is_valid: bool, errors: list[str], cleaned_data: dict)
    """
    errors = []
    cleaned = {}

    # Title
    title = str(form_data.get('title', '') or '').strip()
    if not title or len(title) < 5:
        errors.append("Internship title is required and must be at least 5 characters.")
    cleaned['title'] = title[:150]

    # Category
    cat_raw = form_data.get('category_id')
    cleaned['category_id'] = None
    if cat_raw is not None and str(cat_raw).strip():
        try:
            cat_val = int(str(cat_raw).strip())
            if cat_val > 0:
                cat_obj = db.session.get(InternshipCategory, cat_val)
                if cat_obj:
                    cleaned['category_id'] = cat_val
                else:
                    errors.append("Selected domain category does not exist.")
            else:
                errors.append("Please select a valid domain category.")
        except (ValueError, TypeError):
            errors.append("Invalid category format.")
    else:
        errors.append("Please select a domain category.")

    # Description
    description = str(form_data.get('description', '') or '').strip()
    if not description or len(description) < 50:
        errors.append("Detailed job description is required (minimum 50 characters).")
    cleaned['description'] = description

    # Responsibilities
    cleaned['responsibilities'] = str(form_data.get('responsibilities', '') or '').strip()

    # Eligibility
    eligibility = str(form_data.get('eligibility', '') or '').strip()
    if not eligibility:
        errors.append("Eligibility criteria are required.")
    cleaned['eligibility'] = eligibility

    # Skills Required
    skills = str(form_data.get('skills_required', '') or '').strip()
    if not skills:
        errors.append("Skills required field cannot be empty.")
    cleaned['skills_required'] = skills

    # Application Deadline (must be in the future)
    deadline_raw = str(form_data.get('application_deadline', '') or '').strip()
    cleaned['application_deadline'] = None
    if not deadline_raw:
        errors.append("Application deadline date is required.")
    else:
        try:
            deadline_date = datetime.strptime(deadline_raw, '%Y-%m-%d').date()
            if deadline_date <= date.today():
                errors.append("Application deadline must be a future date.")
            else:
                cleaned['application_deadline'] = deadline_date
        except (ValueError, TypeError):
            errors.append("Invalid application deadline date format (YYYY-MM-DD expected).")

    # Start Date (optional)
    start_date_raw = str(form_data.get('start_date', '') or '').strip()
    cleaned['start_date'] = None
    if start_date_raw:
        try:
            cleaned['start_date'] = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            errors.append("Invalid start date format (YYYY-MM-DD expected).")

    # Stipend Type & Amount
    stipend_type = str(form_data.get('stipend_type', 'paid') or 'paid').strip().lower()
    if stipend_type not in ('paid', 'unpaid'):
        stipend_type = 'paid'
    cleaned['stipend_type'] = stipend_type

    stipend_raw = form_data.get('stipend_amount')
    if stipend_raw is None or str(stipend_raw).strip() == '':
        stipend_raw = form_data.get('stipend', '0')
    cleaned['stipend_amount'] = 0.0
    if stipend_type == 'paid':
        try:
            val = float(str(stipend_raw).strip()) if stipend_raw is not None and str(stipend_raw).strip() else 0.0
            if val < 0:
                errors.append("Stipend amount cannot be negative.")
            else:
                cleaned['stipend_amount'] = val
        except (ValueError, TypeError):
            errors.append("Stipend amount must be a valid non-negative number.")
    else:
        cleaned['stipend_amount'] = 0.0

    # Duration Weeks
    dur_raw = form_data.get('duration_weeks', '8')
    cleaned['duration_weeks'] = 8
    try:
        dur_val = int(str(dur_raw).strip()) if dur_raw is not None and str(dur_raw).strip() else 8
        if dur_val < 1 or dur_val > 104:
            errors.append("Duration in weeks must be between 1 and 104.")
        else:
            cleaned['duration_weeks'] = dur_val
    except (ValueError, TypeError):
        errors.append("Duration in weeks must be an integer between 1 and 104.")

    dur_text = str(form_data.get('duration_text', '') or '').strip()
    cleaned['duration_text'] = dur_text if dur_text else f"{cleaned['duration_weeks']} Weeks"

    # Openings Count
    openings_raw = form_data.get('openings_count')
    if openings_raw is None or str(openings_raw).strip() == '':
        openings_raw = form_data.get('openings', '1')
    cleaned['openings_count'] = 1
    try:
        op_val = int(str(openings_raw).strip()) if openings_raw is not None and str(openings_raw).strip() else 1
        if op_val < 1:
            errors.append("Number of openings must be at least 1.")
        else:
            cleaned['openings_count'] = op_val
    except (ValueError, TypeError):
        errors.append("Number of openings must be a positive integer.")

    # Location Mode & City
    location_type = str(form_data.get('location_type', 'remote') or 'remote').strip().lower()
    if location_type not in ('remote', 'on-site', 'hybrid'):
        location_type = 'remote'
    cleaned['location_type'] = location_type

    location_city = str(form_data.get('location_city', '') or '').strip()
    if location_type in ('on-site', 'hybrid') and not location_city:
        errors.append("City/location is required for On-site and Hybrid work modes.")
    cleaned['location_city'] = location_city

    # Contact Email
    contact_email = str(form_data.get('contact_email', '') or '').strip()
    if not contact_email and company:
        contact_email = company.official_email
    if not contact_email:
        errors.append("Contact email is required.")
        cleaned['contact_email'] = ""
    else:
        is_valid_email, err_email, norm_email = validate_email_address(contact_email)
        if not is_valid_email:
            errors.append(f"Invalid contact email: {err_email}")
            cleaned['contact_email'] = contact_email
        else:
            cleaned['contact_email'] = norm_email

    # Contact Phone
    contact_phone = str(form_data.get('contact_phone', '') or '').strip()
    if not contact_phone and company and company.phone:
        contact_phone = company.phone
    if contact_phone:
        is_valid_phone, err_phone, norm_phone = validate_indian_phone(contact_phone)
        if not is_valid_phone:
            errors.append(f"Invalid contact phone: {err_phone}")
        cleaned['contact_phone'] = contact_phone
    else:
        cleaned['contact_phone'] = ""

    # Application Instructions
    cleaned['application_instructions'] = str(form_data.get('application_instructions', '') or '').strip()

    is_valid = len(errors) == 0
    return is_valid, errors, cleaned


# ═══════════════════════════════════════════════════════════════════════════════
# File Upload Validators
# ═══════════════════════════════════════════════════════════════════════════════

def validate_resume_upload(file_storage, max_size=None, allowed_extensions=None):
    """
    Validates an uploaded resume file:
      1. Checks if a file and filename were provided.
      2. Validates the file extension against allowed formats (default: PDF, DOCX).
      3. Checks for empty files (0 bytes) and file size limits (default: MAX_CONTENT_LENGTH).
      4. Validates magic bytes / file signature:
         - PDF must start with %PDF.
         - DOCX must start with PK and be a valid ZIP archive.
      5. Resets the file pointer to position 0 before returning.

    Returns:
        tuple (is_valid: bool, error_message: str, metadata: dict or None)
        Where metadata contains:
          {'original_name': str, 'ext': str, 'file_size': int}
    """
    if file_storage is None or not getattr(file_storage, 'filename', None) or not file_storage.filename.strip():
        return False, "No file selected. Please choose a resume to upload.", None

    filename = file_storage.filename.strip()
    if '.' not in filename:
        return False, "File has no extension. Allowed formats: PDF, DOCX.", None

    ext = filename.rsplit('.', 1)[-1].lower()

    if allowed_extensions is None:
        try:
            allowed_extensions = current_app.config.get('ALLOWED_RESUME_EXTENSIONS', {'pdf', 'docx'})
        except Exception:
            allowed_extensions = {'pdf', 'docx'}

    if ext not in allowed_extensions:
        return False, f"Invalid file format '.{ext}'. Allowed formats: PDF, DOCX.", None

    if max_size is None:
        try:
            max_size = current_app.config.get('MAX_CONTENT_LENGTH', 8 * 1024 * 1024)
        except Exception:
            max_size = 8 * 1024 * 1024

    try:
        # Check file size
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)

        if file_size == 0:
            return False, "The uploaded file is empty. Please upload a valid document.", None

        if file_size > max_size:
            max_mb = max_size // (1024 * 1024)
            return False, f"File size exceeds the {max_mb}MB limit.", None

        # Check signature (magic bytes)
        header = file_storage.read(1024)
        file_storage.seek(0)

        if ext == 'pdf':
            if not header.startswith(b'%PDF'):
                return False, "Invalid PDF file. The file signature does not match a valid PDF document.", None
        elif ext == 'docx':
            if not header.startswith(b'PK'):
                return False, "Invalid DOCX file. The file signature does not match a valid Word document.", None
            try:
                if not zipfile.is_zipfile(file_storage):
                    return False, "Corrupted DOCX file. The file is not a valid ZIP archive.", None
            except Exception:
                return False, "Corrupted DOCX file. The file is not a valid ZIP archive.", None
            finally:
                file_storage.seek(0)

        safe_name = secure_filename(filename) or f"resume.{ext}"
        meta = {
            'original_name': safe_name,
            'ext': ext,
            'file_size': file_size
        }
        return True, "", meta

    finally:
        # Guarantee file pointer reset
        try:
            file_storage.seek(0)
        except Exception:
            pass


def validate_verification_document(file_storage, max_size=None, allowed_extensions=None):
    """
    Validates an uploaded company verification document:
      1. Checks file presence and filename.
      2. Validates file extension against allowed formats (PDF, PNG, JPG, JPEG).
      3. Checks for empty files (0 bytes) and file size limits (default: MAX_CONTENT_LENGTH).
      4. Validates magic bytes / file signature:
         - PDF must start with %PDF.
         - PNG must start with \\x89PNG\\r\\n\\x1a\\n.
         - JPG / JPEG must start with \\xff\\xd8\\xff.
      5. Resets file pointer before returning.

    Returns:
        tuple (is_valid: bool, error_message: str, metadata: dict or None)
        Where metadata contains:
          {'original_name': str, 'ext': str, 'file_size': int}
    """
    if file_storage is None or not getattr(file_storage, 'filename', None) or not file_storage.filename.strip():
        return False, "No file selected. Please choose a verification document to upload.", None

    filename = file_storage.filename.strip()
    if '.' not in filename:
        return False, "File has no extension. Allowed formats: PDF, PNG, JPG, JPEG.", None

    ext = filename.rsplit('.', 1)[-1].lower()

    if allowed_extensions is None:
        try:
            allowed_extensions = current_app.config.get('ALLOWED_DOCS_EXTENSIONS', {'pdf', 'png', 'jpg', 'jpeg'})
        except Exception:
            allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}

    if ext not in allowed_extensions:
        return False, f"Invalid file format '.{ext}'. Allowed formats: PDF, PNG, JPG, JPEG.", None

    if max_size is None:
        try:
            max_size = current_app.config.get('MAX_CONTENT_LENGTH', 8 * 1024 * 1024)
        except Exception:
            max_size = 8 * 1024 * 1024

    try:
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)

        if file_size == 0:
            return False, "The uploaded verification document is empty. Please upload a valid document.", None

        if file_size > max_size:
            max_mb = max_size // (1024 * 1024)
            return False, f"Document file size exceeds the {max_mb}MB limit.", None

        header = file_storage.read(16)
        file_storage.seek(0)

        if ext == 'pdf':
            if not header.startswith(b'%PDF'):
                return False, "Invalid PDF file. The file signature does not match a valid PDF document.", None
        elif ext == 'png':
            if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                return False, "Invalid PNG image. The file signature does not match a valid PNG file.", None
        elif ext in ('jpg', 'jpeg'):
            if not header.startswith(b'\xff\xd8\xff'):
                return False, "Invalid JPG/JPEG image. The file signature does not match a valid JPEG file.", None

        safe_name = secure_filename(filename) or f"document.{ext}"
        meta = {
            'original_name': safe_name,
            'ext': ext,
            'file_size': file_size
        }
        return True, "", meta

    finally:
        try:
            file_storage.seek(0)
        except Exception:
            pass
