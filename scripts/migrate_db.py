"""
scripts/migrate_db.py
=====================
Idempotent database migration script for Smart Online Internship Management System.
Ensures that all required columns on `internships` and `scam_checks` tables exist:
  - internships.start_date (DATE NULL)
  - internships.application_instructions (TEXT NULL)
  - scam_checks.disclaimer (TEXT NULL)
  - scam_checks.appeal_note (TEXT NULL)
  - scam_checks.appeal_submitted_at (DATETIME NULL)
  - scam_checks.appeal_status (ENUM('none','pending','reviewed') NOT NULL DEFAULT 'none')

Safe for repeated runs; does not drop, overwrite, or reset existing tables or data.
"""
import sys
from pathlib import Path
import sqlalchemy as sa

# Ensure application root is in python path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app


def get_column_definitions(dialect_name: str):
    """
    Returns the table migration specifications formatted for the active SQL dialect.
    """
    if dialect_name == 'mysql':
        return [
            ('internships', 'start_date', 'DATE NULL'),
            ('internships', 'application_instructions', 'TEXT NULL'),
            ('scam_checks', 'disclaimer', 'TEXT NULL'),
            ('scam_checks', 'appeal_note', 'TEXT NULL'),
            ('scam_checks', 'appeal_submitted_at', 'DATETIME NULL'),
            ('scam_checks', 'appeal_status', "ENUM('none', 'pending', 'reviewed') NOT NULL DEFAULT 'none'"),
        ]
    else:
        # SQLite / generic fallback
        return [
            ('internships', 'start_date', 'DATE'),
            ('internships', 'application_instructions', 'TEXT'),
            ('scam_checks', 'disclaimer', 'TEXT'),
            ('scam_checks', 'appeal_note', 'TEXT'),
            ('scam_checks', 'appeal_submitted_at', 'DATETIME'),
            ('scam_checks', 'appeal_status', "VARCHAR(20) NOT NULL DEFAULT 'none'"),
        ]


def run_migration(app=None, engine=None):
    """
    Runs idempotent migration against the configured database.
    Returns a dict with execution statistics: {'added': [...], 'skipped': [...]}
    Raises Exception on failure.
    """
    if app is None:
        app = create_app()

    if engine is None:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        engine = sa.create_engine(uri, **engine_options)

    stats = {'added': [], 'skipped': []}

    with app.app_context():
        with engine.connect() as conn:
            dialect = engine.dialect.name
            print(f"[INFO] Connected to database ({dialect}). Inspecting schema...")

            migrations = get_column_definitions(dialect)
            inspector = sa.inspect(engine)
            existing_tables = inspector.get_table_names()

            # Group by table
            tables_to_check = set(table for table, _, _ in migrations)
            for tbl in tables_to_check:
                if tbl not in existing_tables:
                    raise RuntimeError(
                        f"Required table '{tbl}' does not exist in database. "
                        f"Please run schema.sql or db.create_all() first."
                    )

            for table_name, column_name, col_type in migrations:
                # Refresh column list for table
                current_columns = [c['name'] for c in inspector.get_columns(table_name)]
                if column_name in current_columns:
                    print(f"  [SKIP] {table_name}.{column_name} already exists.")
                    stats['skipped'].append(f"{table_name}.{column_name}")
                else:
                    print(f"  [MIGRATING] Adding column {table_name}.{column_name} ({col_type})...")
                    conn.execute(sa.text(f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {col_type}"))
                    conn.commit()
                    print(f"  [SUCCESS] Added {table_name}.{column_name}")
                    stats['added'].append(f"{table_name}.{column_name}")
                    # Re-inspect to keep inspector cache up to date
                    inspector = sa.inspect(engine)

    return stats


def main():
    print("=" * 60)
    print("Starting Database Schema Migration (SmartInternshipSystem)")
    print("=" * 60)
    try:
        stats = run_migration()
        print("-" * 60)
        print("Migration completed successfully.")
        print(f"Columns added:   {len(stats['added'])} ({', '.join(stats['added']) if stats['added'] else 'None'})")
        print(f"Columns skipped: {len(stats['skipped'])} ({', '.join(stats['skipped']) if stats['skipped'] else 'None'})")
        print("=" * 60)
        return 0
    except Exception as exc:
        print("-" * 60, file=sys.stderr)
        print(f"[ERROR] Migration failed: {exc}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
