"""
scripts/migrate_company_docs.py
===============================
Idempotent migration script to add `companies.verification_document` column
for Group 4 (Company Verification Documents).

Safe for repeated runs; does not drop or overwrite existing tables or data.
"""
import sys
from pathlib import Path
import sqlalchemy as sa

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app


def run_migration(app=None, engine=None):
    """
    Checks if `verification_document` exists on `companies` table.
    Adds it if missing; skips safely if already present.
    Returns: dict {'added': bool, 'skipped': bool}
    """
    if app is None:
        app = create_app()

    if engine is None:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        engine = sa.create_engine(uri, **engine_options)

    stats = {'added': False, 'skipped': False}

    with app.app_context():
        with engine.connect() as conn:
            dialect = engine.dialect.name
            inspector = sa.inspect(engine)
            existing_tables = inspector.get_table_names()

            if 'companies' not in existing_tables:
                print("[WARN] Table 'companies' does not exist yet. Run schema.sql first.")
                stats['skipped'] = True
                return stats

            existing_cols = {col['name'] for col in inspector.get_columns('companies')}

            if 'verification_document' in existing_cols:
                print("[SKIP] Column 'companies.verification_document' already exists.")
                stats['skipped'] = True
            else:
                col_type = "VARCHAR(255) NULL" if dialect == 'mysql' else "VARCHAR(255)"
                sql = f"ALTER TABLE companies ADD COLUMN verification_document {col_type}"
                print(f"[APPLY] Executing: {sql}")
                conn.execute(sa.text(sql))
                conn.commit()
                print("[SUCCESS] Column 'companies.verification_document' added successfully.")
                stats['added'] = True

    return stats


if __name__ == '__main__':
    try:
        res = run_migration()
        print(f"[DONE] Migration result: {res}")
        sys.exit(0)
    except Exception as e:
        print(f"[FATAL] Migration error: {e}", file=sys.stderr)
        sys.exit(1)
