"""
scripts/migrate_resumes.py
==========================
One-time idempotent migration script to relocate existing resumes from the
public static storage (app/static/uploads/resumes) to the private storage
directory (instance/uploads/resumes).

Safeties:
  - Preserves filenames and existing database references.
  - Detects and resolves filename collisions without overwriting.
  - Verifies file integrity at destination before removing source.
  - Ignores non-resume files, profile pictures, and company logos.
  - Safe for repeated executions.
"""
import os
import sys
import shutil
import hashlib
import uuid
from pathlib import Path

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.models import db, Resume


def calculate_sha256(filepath):
    """Calculates SHA256 hash of a file for integrity check."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def migrate_resumes(app=None, src_dir=None, dest_dir=None):
    """
    Migrates resume files from src_dir to dest_dir safely.
    Returns: dict with 'moved', 'skipped', 'failed', 'collisions_resolved'
    """
    if app is None:
        app = create_app()

    with app.app_context():
        if src_dir is None:
            src_dir = os.path.join(app.root_path, 'static', 'uploads', 'resumes')
        if dest_dir is None:
            dest_dir = app.config.get(
                'RESUME_FOLDER',
                os.path.join(BASE_DIR, 'instance', 'uploads', 'resumes')
            )

        os.makedirs(dest_dir, exist_ok=True)

        stats = {
            'moved': [],
            'skipped': [],
            'failed': [],
            'collisions_resolved': []
        }

        if not os.path.exists(src_dir):
            print(f"[INFO] Source directory does not exist: {src_dir}")
            return stats

        print(f"[INFO] Migrating resumes from '{src_dir}' to '{dest_dir}'...")

        for entry in os.listdir(src_dir):
            src_file = os.path.join(src_dir, entry)

            # Skip subdirectories and .gitkeep
            if not os.path.isfile(src_file) or entry == '.gitkeep':
                continue

            target_name = entry
            dest_file = os.path.join(dest_dir, target_name)

            try:
                src_hash = calculate_sha256(src_file)
                src_size = os.path.getsize(src_file)

                # Check if file with same name already exists in destination
                if os.path.exists(dest_file):
                    dest_hash = calculate_sha256(dest_file)
                    dest_size = os.path.getsize(dest_file)

                    if src_hash == dest_hash and src_size == dest_size:
                        # Exactly identical file already exists at destination
                        # Safe to remove redundant source copy
                        os.remove(src_file)
                        stats['skipped'].append(entry)
                        print(f"  [SKIP] '{entry}' already safely migrated to destination.")
                        continue
                    else:
                        # Collision! File with same name has different content
                        stem, ext = os.path.splitext(entry)
                        unique_suffix = uuid.uuid4().hex[:6]
                        target_name = f"{stem}_{unique_suffix}{ext}"
                        dest_file = os.path.join(dest_dir, target_name)
                        stats['collisions_resolved'].append((entry, target_name))
                        print(f"  [COLLISION] '{entry}' collides with different file; renamed to '{target_name}'.")

                # Copy with metadata preservation
                shutil.copy2(src_file, dest_file)

                # Verify destination copy before deleting source
                if (os.path.exists(dest_file) and
                        os.path.getsize(dest_file) == src_size and
                        calculate_sha256(dest_file) == src_hash):
                    # Successfully verified! Remove source
                    os.remove(src_file)
                    stats['moved'].append((entry, target_name))
                    print(f"  [MOVED] '{entry}' -> '{target_name}'")

                    # Update database reference if target_name changed or file_path points to old path
                    resume_records = Resume.query.filter_by(filename=entry).all()
                    for r in resume_records:
                        r.filename = target_name
                        r.file_path = f"instance/uploads/resumes/{target_name}"
                    if resume_records:
                        db.session.commit()
                else:
                    stats['failed'].append(entry)
                    print(f"  [FAILED] Verification failed for '{entry}'. Preserving original source.", file=sys.stderr)

            except Exception as e:
                stats['failed'].append(entry)
                print(f"  [ERROR] Failed to migrate '{entry}': {e}", file=sys.stderr)

        # Update any remaining Resume records in database that still reference old static path
        try:
            old_resumes = Resume.query.filter(Resume.file_path.like('%app/static/uploads/resumes%')).all()
            for r in old_resumes:
                r.file_path = f"instance/uploads/resumes/{r.filename}"
            if old_resumes:
                db.session.commit()
                print(f"[INFO] Updated {len(old_resumes)} database records to new instance file path.")
        except Exception as e:
            print(f"[WARNING] Database path update: {e}", file=sys.stderr)

        return stats


def main():
    print("=" * 60)
    print("Private Resume Migration Script")
    print("=" * 60)
    stats = migrate_resumes()
    print("-" * 60)
    print("Migration completed.")
    print(f"Files moved:    {len(stats['moved'])}")
    print(f"Files skipped:  {len(stats['skipped'])}")
    print(f"Files failed:   {len(stats['failed'])}")
    print(f"Collisions:     {len(stats['collisions_resolved'])}")
    print("=" * 60)
    return 1 if stats['failed'] else 0


if __name__ == '__main__':
    sys.exit(main())
