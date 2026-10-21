"""
app/utils.py
============
Shared utility and validation functions for SmartInternshipSystem.
Maintains backwards compatibility by re-exporting validators from app.validators.
"""
from app.validators import (
    is_safe_redirect_url,
    validate_email_address,
    validate_indian_phone,
    validate_gstin,
    validate_password,
    validate_internship_form,
    validate_resume_upload,
    validate_verification_document,
)

__all__ = [
    'is_safe_redirect_url',
    'validate_email_address',
    'validate_indian_phone',
    'validate_gstin',
    'validate_password',
    'validate_internship_form',
    'validate_resume_upload',
    'validate_verification_document',
]
