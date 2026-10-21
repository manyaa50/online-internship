"""
app.services.uploads
====================
Shared file upload management service for SmartInternshipSystem.
Consolidates storage logic and file validations for:
  - Private student resumes (stored in instance/uploads/resumes)
  - Private company verification documents (stored in instance/uploads/company_docs)
  - Public profile pictures and company logos (stored in app/static/uploads)
"""
import os
import uuid
from flask import current_app
from app.validators import validate_resume_upload, validate_verification_document


def save_resume(file_storage, student_id, dest_folder=None):
    """
    Validates and securely stores a student's resume in private instance storage.

    Parameters:
        file_storage: FileStorage object from request.files.
        student_id (int): StudentProfile ID.
        dest_folder (str, optional): Target directory path. Defaults to app config RESUME_FOLDER.

    Returns:
        tuple (is_valid: bool, error_message: str, file_info: dict or None)
        Where file_info contains:
          - 'filename': unique stored filename
          - 'original_name': sanitized original filename
          - 'file_path': relative storage path (instance/uploads/resumes/<filename>)
          - 'file_size': size in bytes
          - 'ext': file extension
          - 'absolute_path': absolute filesystem path where file was saved
    """
    is_valid, err_msg, meta = validate_resume_upload(file_storage)
    if not is_valid:
        return False, err_msg, None

    unique_filename = f"resume_{student_id}_{uuid.uuid4().hex[:8]}.{meta['ext']}"
    save_dir = dest_folder or current_app.config.get(
        'RESUME_FOLDER',
        os.path.join(current_app.instance_path, 'uploads', 'resumes')
    )
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, unique_filename)

    file_storage.save(save_path)

    file_info = {
        'filename': unique_filename,
        'original_name': meta['original_name'],
        'file_path': f"instance/uploads/resumes/{unique_filename}",
        'file_size': meta['file_size'],
        'ext': meta['ext'],
        'absolute_path': save_path
    }
    return True, "", file_info


def save_verification_doc(file_storage, company_id, dest_folder=None):
    """
    Validates and securely stores a company verification document in private instance storage.

    Parameters:
        file_storage: FileStorage object from request.files.
        company_id (int): Company ID.
        dest_folder (str, optional): Target directory path. Defaults to app config DOCS_FOLDER.

    Returns:
        tuple (is_valid: bool, error_message: str, file_info: dict or None)
        Where file_info contains:
          - 'filename': unique stored filename
          - 'original_name': sanitized original filename
          - 'file_path': relative storage path (instance/uploads/company_docs/<filename>)
          - 'file_size': size in bytes
          - 'ext': file extension
          - 'absolute_path': absolute filesystem path where file was saved
    """
    is_valid, err_msg, meta = validate_verification_document(file_storage)
    if not is_valid:
        return False, err_msg, None

    unique_filename = f"doc_{company_id}_{uuid.uuid4().hex[:8]}.{meta['ext']}"
    save_dir = dest_folder or current_app.config.get(
        'DOCS_FOLDER',
        os.path.join(current_app.instance_path, 'uploads', 'company_docs')
    )
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, unique_filename)

    file_storage.save(save_path)

    file_info = {
        'filename': unique_filename,
        'original_name': meta['original_name'],
        'file_path': f"instance/uploads/company_docs/{unique_filename}",
        'file_size': meta['file_size'],
        'ext': meta['ext'],
        'absolute_path': save_path
    }
    return True, "", file_info


def save_public_image(file_storage, prefix, entity_id, dest_folder=None, allowed_extensions=None):
    """
    Validates extension and stores a public image (profile picture or company logo)
    in the static uploads directory.

    Parameters:
        file_storage: FileStorage object from request.files.
        prefix (str): Filename prefix (e.g. 'avatar', 'comp').
        entity_id (int): Associated entity ID (student ID or company ID).
        dest_folder (str, optional): Target directory. Defaults to app config UPLOAD_FOLDER.
        allowed_extensions (set, optional): Allowed image extensions.

    Returns:
        str or None: The unique saved filename, or None if the file was missing or invalid.
    """
    if not file_storage or not getattr(file_storage, 'filename', None) or not file_storage.filename.strip():
        return None

    filename = file_storage.filename.strip()
    if '.' not in filename:
        return None

    ext = filename.rsplit('.', 1)[-1].lower()
    allowed = allowed_extensions or current_app.config.get(
        'ALLOWED_IMAGE_EXTENSIONS',
        {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    )
    if ext not in allowed:
        return None

    unique_filename = f"{prefix}_{entity_id}_{uuid.uuid4().hex[:8]}.{ext}"
    save_dir = dest_folder or current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(current_app.root_path, 'static', 'uploads')
    )
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, unique_filename)

    file_storage.save(save_path)
    return unique_filename


def save_profile_picture(file_storage, student_id, dest_folder=None):
    """Stores student avatar image in public uploads."""
    return save_public_image(file_storage, 'avatar', student_id, dest_folder)


def save_company_logo(file_storage, company_id, dest_folder=None):
    """Stores company logo image in public uploads."""
    return save_public_image(file_storage, 'comp', company_id, dest_folder)


__all__ = [
    'save_resume',
    'save_verification_doc',
    'save_public_image',
    'save_profile_picture',
    'save_company_logo',
    'validate_resume_upload',
    'validate_verification_document',
]
