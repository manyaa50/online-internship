"""Run once: adds new columns to scam_checks table for appeal and disclaimer fields."""
from app import create_app
from app.models import db
import sqlalchemy as sa

app = create_app()
with app.app_context():
    conn = db.engine.connect()
    inspector = sa.inspect(db.engine)

    sc_cols = [c['name'] for c in inspector.get_columns('scam_checks')]
    print('scam_checks existing cols:', sc_cols)

    migrations = [
        ('disclaimer',            'TEXT'),
        ('appeal_note',           'TEXT'),
        ('appeal_submitted_at',   'DATETIME'),
        ('appeal_status',         'VARCHAR(20) NOT NULL DEFAULT "none"'),
    ]

    for col, coltype in migrations:
        if col not in sc_cols:
            conn.execute(sa.text(f'ALTER TABLE scam_checks ADD COLUMN {col} {coltype}'))
            print(f'  Added: {col}')
        else:
            print(f'  Already exists: {col}')

    conn.commit()
    conn.close()

    # Verify
    inspector2 = sa.inspect(db.engine)
    final_cols = [c['name'] for c in inspector2.get_columns('scam_checks')]
    print('scam_checks final cols:', final_cols)
    print('Migration complete.')
