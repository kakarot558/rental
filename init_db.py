"""
Run this script once to initialize the database and create the default admin user.
Usage: python init_db.py
"""
from app import init_db

if __name__ == '__main__':
    init_db()
    print("✅ Database initialized successfully!")
    print("👤 Default admin credentials:")
    print("   Username: admin")
    print("   Password: Admin@1234")
    print("\n⚠️  IMPORTANT: Change the admin password after first login!")