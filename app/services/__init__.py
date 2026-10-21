"""
app.services
============
Shared domain and infrastructure services for SmartInternshipSystem.
Provides consolidated notifications and secure upload handling.
"""
from app.services.notifications import notify
from app.services.uploads import (
    save_resume,
    save_verification_doc,
    save_public_image,
    save_profile_picture,
    save_company_logo,
)

__all__ = [
    'notify',
    'save_resume',
    'save_verification_doc',
    'save_public_image',
    'save_profile_picture',
    'save_company_logo',
]
