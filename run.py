import os
from app import create_app
from app.models import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        try:
            # Test database connection and create tables if needed
            db.create_all()
            print("[OK] Database connection verified and tables synchronized.")
        except Exception as e:
            print(f"[WARNING] Could not connect to primary database. Error: {e}")
            print("[INFO] Ensure your MySQL server (XAMPP / WAMP) is running on port 3306,")
            print("   or set DATABASE_URL environment variable.")

    port = int(os.environ.get('PORT', 5000))
    print(f"[*] Starting Smart Internship System at http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=True)
