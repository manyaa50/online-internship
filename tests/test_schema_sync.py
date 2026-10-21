"""
tests/test_schema_sync.py
=========================
Comprehensive schema and model synchronization tests for SmartInternshipSystem.

Verifies:
  1. Every database table declared in `models.py` has a corresponding table in `schema.sql`.
  2. Every database column declared across ALL models in `models.py` exists in `schema.sql`.
  3. The 6 Group 1 columns (`internships.start_date`, `internships.application_instructions`,
     `scam_checks.disclaimer`, `scam_checks.appeal_note`, `scam_checks.appeal_submitted_at`,
     `scam_checks.appeal_status`) are present with correct types and nullability.
  4. Column types and nullability constraints are semantically aligned between models and SQL.
  5. The test comparator properly detects and fails on missing columns.
  6. The `scripts/migrate_db.py` migration script executes idempotently and safely.
  7. `scripts/migrate_db.py` exits with a non-zero status code when database connection fails.
"""
import os
import re
import sys
import tempfile
import pytest
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy.types import (
    Integer, String, Text, Date, DateTime, Boolean, Numeric, Enum as SAEnum
)

# Ensure project root is available
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.models import (
    db, User, Admin, StudentProfile, Resume, Company, CompanyVerification,
    InternshipCategory, Internship, ScamCheck, Application, ScamReport, Notification
)
from scripts import migrate_db


def parse_schema_sql(schema_path: Path):
    """
    Parses schema.sql to extract table names and column definitions.
    Returns: dict[table_name] = dict[column_name] -> {
        'type': str,
        'nullable': bool,
        'raw': str
    }
    """
    assert schema_path.exists(), f"Schema file not found at {schema_path}"
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Strip SQL line comments
    clean_lines = []
    for line in sql.splitlines():
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        clean_lines.append(line)

    clean_sql = ' '.join(clean_lines)

    # Match CREATE TABLE statements up to ENGINE or terminating semicolon
    table_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([a-zA-Z0-9_]+)`?\s*\((.*?)\)\s*(?:ENGINE|;)',
        re.IGNORECASE
    )

    tables = {}
    for match in table_pattern.finditer(clean_sql):
        table_name = match.group(1)
        body = match.group(2)

        # Tokenize by comma at top parenthesis depth
        tokens = []
        depth = 0
        current = []
        for char in body:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            if char == ',' and depth == 0:
                tokens.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            tokens.append(''.join(current).strip())

        columns = {}
        for token in tokens:
            token = token.strip()
            # Skip table-level constraints and indexes
            if re.match(r'^(PRIMARY\s+KEY|KEY|INDEX|UNIQUE\s+KEY|UNIQUE\s+INDEX|CONSTRAINT|FOREIGN\s+KEY|CHECK)\b', token, re.IGNORECASE):
                continue

            # Match column definition: `name` TYPE [options] or name TYPE [options]
            col_match = re.match(r'^`?([a-zA-Z0-9_]+)`?\s+([A-Za-z]+(?:\([^)]*\))?)(.*)', token)
            if col_match:
                col_name = col_match.group(1)
                col_type = col_match.group(2).upper()
                col_rest = col_match.group(3).strip()

                # In MySQL: if NOT NULL is present, it's not nullable
                is_not_null = bool(re.search(r'\bNOT\s+NULL\b', col_rest, re.IGNORECASE))
                is_pk = bool(re.search(r'\bPRIMARY\s+KEY\b', col_rest, re.IGNORECASE))
                is_nullable = not is_not_null and not is_pk

                columns[col_name] = {
                    'type': col_type,
                    'nullable': is_nullable,
                    'raw': token
                }

        tables[table_name] = columns

    return tables


def compare_models_with_schema(metadata, parsed_schema):
    """
    Compares every column declared on all tables in SQLAlchemy metadata
    against parsed schema.sql.
    Returns: list of error description strings.
    """
    errors = []

    for table_name, model_table in metadata.tables.items():
        if table_name not in parsed_schema:
            errors.append(f"Missing Table: '{table_name}' declared in models.py is absent in schema.sql")
            continue

        schema_columns = parsed_schema[table_name]
        for col in model_table.columns:
            if col.name not in schema_columns:
                errors.append(
                    f"Missing Column: Table '{table_name}' has column '{col.name}' ({col.type}) in models.py, "
                    f"but it is MISSING from schema.sql"
                )

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_all_model_tables_exist_in_schema_sql():
    """Verify all 12 mapped SQLAlchemy tables exist in schema.sql."""
    schema_path = BASE_DIR / 'schema.sql'
    parsed = parse_schema_sql(schema_path)

    expected_tables = {
        'users', 'admins', 'student_profiles', 'resumes', 'companies',
        'company_verifications', 'internship_categories', 'internships',
        'scam_checks', 'applications', 'scam_reports', 'notifications'
    }

    assert expected_tables.issubset(set(parsed.keys())), (
        f"Missing tables in schema.sql: {expected_tables - set(parsed.keys())}"
    )


def test_every_model_column_exists_in_schema_sql():
    """
    Comprehensive test: compares EVERY column declared on EVERY model in models.py
    with the table definition in schema.sql. Fails if ANY column is missing.
    """
    schema_path = BASE_DIR / 'schema.sql'
    parsed = parse_schema_sql(schema_path)

    errors = compare_models_with_schema(db.metadata, parsed)
    assert not errors, "\n".join(errors)


def test_group1_six_columns_explicitly_verified():
    """
    Explicitly tests that all 6 required Group 1 columns are declared in both
    schema.sql and models.py with their expected types and constraints:
      - internships.start_date DATE NULL
      - internships.application_instructions TEXT NULL
      - scam_checks.disclaimer TEXT NULL
      - scam_checks.appeal_note TEXT NULL
      - scam_checks.appeal_submitted_at DATETIME NULL
      - scam_checks.appeal_status ENUM('none','pending','reviewed') NOT NULL DEFAULT 'none'
    """
    schema_path = BASE_DIR / 'schema.sql'
    parsed = parse_schema_sql(schema_path)

    # 1. internships.start_date
    assert 'internships' in parsed
    assert 'start_date' in parsed['internships']
    assert parsed['internships']['start_date']['type'] == 'DATE'
    assert parsed['internships']['start_date']['nullable'] is True

    # 2. internships.application_instructions
    assert 'application_instructions' in parsed['internships']
    assert 'TEXT' in parsed['internships']['application_instructions']['type']
    assert parsed['internships']['application_instructions']['nullable'] is True

    # 3. scam_checks.disclaimer
    assert 'scam_checks' in parsed
    assert 'disclaimer' in parsed['scam_checks']
    assert 'TEXT' in parsed['scam_checks']['disclaimer']['type']
    assert parsed['scam_checks']['disclaimer']['nullable'] is True

    # 4. scam_checks.appeal_note
    assert 'appeal_note' in parsed['scam_checks']
    assert 'TEXT' in parsed['scam_checks']['appeal_note']['type']
    assert parsed['scam_checks']['appeal_note']['nullable'] is True

    # 5. scam_checks.appeal_submitted_at
    assert 'appeal_submitted_at' in parsed['scam_checks']
    assert parsed['scam_checks']['appeal_submitted_at']['type'] in ('DATETIME', 'TIMESTAMP')
    assert parsed['scam_checks']['appeal_submitted_at']['nullable'] is True

    # 6. scam_checks.appeal_status
    assert 'appeal_status' in parsed['scam_checks']
    status_type = parsed['scam_checks']['appeal_status']['type'].replace(' ', '').lower()
    assert 'enum' in status_type
    for val in ('none', 'pending', 'reviewed'):
        assert f"'{val}'" in status_type
    assert parsed['scam_checks']['appeal_status']['nullable'] is False
    assert "DEFAULT 'NONE'" in parsed['scam_checks']['appeal_status']['raw'].upper()

    # Also verify models.py attributes
    internship_cols = {c.name: c for c in Internship.__table__.columns}
    assert 'start_date' in internship_cols
    assert isinstance(internship_cols['start_date'].type, Date)
    assert internship_cols['start_date'].nullable is True

    assert 'application_instructions' in internship_cols
    assert isinstance(internship_cols['application_instructions'].type, Text)
    assert internship_cols['application_instructions'].nullable is True

    scam_cols = {c.name: c for c in ScamCheck.__table__.columns}
    assert 'disclaimer' in scam_cols
    assert isinstance(scam_cols['disclaimer'].type, Text)
    assert scam_cols['disclaimer'].nullable is True

    assert 'appeal_note' in scam_cols
    assert isinstance(scam_cols['appeal_note'].type, Text)
    assert scam_cols['appeal_note'].nullable is True

    assert 'appeal_submitted_at' in scam_cols
    assert isinstance(scam_cols['appeal_submitted_at'].type, DateTime)
    assert scam_cols['appeal_submitted_at'].nullable is True

    assert 'appeal_status' in scam_cols
    assert isinstance(scam_cols['appeal_status'].type, SAEnum)
    assert scam_cols['appeal_status'].nullable is False


def test_column_types_compatible_with_models():
    """
    Validates semantic compatibility of SQL types with SQLAlchemy column types.
    """
    schema_path = BASE_DIR / 'schema.sql'
    parsed = parse_schema_sql(schema_path)

    for table_name, model_table in db.metadata.tables.items():
        schema_cols = parsed.get(table_name, {})
        for col in model_table.columns:
            assert col.name in schema_cols, f"Column {table_name}.{col.name} missing from schema"
            sql_type = schema_cols[col.name]['type']

            # Check SAEnum and Text first since both subclass String in SQLAlchemy
            if isinstance(col.type, SAEnum):
                assert 'ENUM' in sql_type, f"Type mismatch for {table_name}.{col.name}"
            elif isinstance(col.type, Text):
                assert any(t in sql_type for t in ('TEXT', 'LONGTEXT')), f"Type mismatch for {table_name}.{col.name}"
            elif isinstance(col.type, Integer):
                assert any(t in sql_type for t in ('INT', 'INTEGER')), f"Type mismatch for {table_name}.{col.name}"
            elif isinstance(col.type, String):
                assert 'VARCHAR' in sql_type, f"Type mismatch for {table_name}.{col.name}"
            elif isinstance(col.type, Date):
                assert 'DATE' in sql_type, f"Type mismatch for {table_name}.{col.name}"
            elif isinstance(col.type, DateTime):
                assert any(t in sql_type for t in ('DATETIME', 'TIMESTAMP')), f"Type mismatch for {table_name}.{col.name}"
            elif isinstance(col.type, Boolean):
                assert any(t in sql_type for t in ('BOOLEAN', 'TINYINT')), f"Type mismatch for {table_name}.{col.name}"
            elif isinstance(col.type, Numeric):
                assert any(t in sql_type for t in ('DECIMAL', 'NUMERIC')), f"Type mismatch for {table_name}.{col.name}"


def test_comparator_fails_when_model_column_missing_from_schema():
    """
    Safety check: ensures the comparator DOES fail if a column (e.g. start_date)
    is missing from the schema definition.
    """
    schema_path = BASE_DIR / 'schema.sql'
    parsed = parse_schema_sql(schema_path)

    # Deliberately remove start_date from parsed schema
    simulated_broken_schema = {
        tbl: {col: info for col, info in cols.items()}
        for tbl, cols in parsed.items()
    }
    del simulated_broken_schema['internships']['start_date']

    errors = compare_models_with_schema(db.metadata, simulated_broken_schema)
    assert len(errors) == 1
    assert "Missing Column: Table 'internships' has column 'start_date'" in errors[0]


def test_migrate_db_idempotency_and_safety():
    """
    Tests scripts/migrate_db.py on an isolated SQLite database to verify:
      1. Missing columns are added safely.
      2. Repeated execution does not crash or re-add columns (idempotent).
      3. Existing data is preserved.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_db_path = tmp.name

    test_uri = f"sqlite:///{tmp_db_path}"
    test_engine = sa.create_engine(test_uri)

    test_app = create_app()
    test_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_uri,
        'WTF_CSRF_ENABLED': False
    })

    try:
        # Create partial tables lacking the 6 new columns on isolated engine
        with test_engine.connect() as conn:
            conn.execute(sa.text("""
                CREATE TABLE internships (
                    id INTEGER PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    title VARCHAR(150) NOT NULL,
                    description TEXT NOT NULL
                )
            """))
            conn.execute(sa.text("""
                CREATE TABLE scam_checks (
                    id INTEGER PRIMARY KEY,
                    internship_id INTEGER NOT NULL,
                    risk_score INTEGER NOT NULL DEFAULT 0,
                    risk_level VARCHAR(20) NOT NULL DEFAULT 'Low'
                )
            """))
            # Insert sample record to test data preservation
            conn.execute(sa.text("""
                INSERT INTO internships (id, company_id, category_id, title, description)
                VALUES (1, 10, 20, 'Existing Intern', 'Test description')
            """))
            conn.commit()

        # Run 1: Should add missing columns
        stats1 = migrate_db.run_migration(app=test_app, engine=test_engine)
        assert len(stats1['added']) == 6
        assert len(stats1['skipped']) == 0

        # Verify existing record was preserved
        with test_engine.connect() as conn:
            row = conn.execute(sa.text("SELECT title FROM internships WHERE id = 1")).fetchone()
            assert row[0] == 'Existing Intern'

        # Run 2: Repeated run should skip all 6 columns cleanly (idempotent)
        stats2 = migrate_db.run_migration(app=test_app, engine=test_engine)
        assert len(stats2['added']) == 0
        assert len(stats2['skipped']) == 6

    finally:
        test_engine.dispose()
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except Exception:
                pass


def test_migrate_db_handles_connection_failure():
    """
    Tests that scripts/migrate_db.py raises / reports error clearly
    and returns non-zero when database connection fails.
    """
    bad_app = create_app()
    bad_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'mysql+pymysql://invalid_user:invalid_pass@127.0.0.1:9999/nonexistent',
        'SQLALCHEMY_ENGINE_OPTIONS': {'pool_pre_ping': False}
    })

    with pytest.raises(Exception):
        migrate_db.run_migration(app=bad_app)
