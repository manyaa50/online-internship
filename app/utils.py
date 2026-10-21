"""
app/utils.py
============
Shared utility and validation functions for SmartInternshipSystem.
"""
import os
import zipfile
from werkzeug.utils import secure_filename
from flask import current_app


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
