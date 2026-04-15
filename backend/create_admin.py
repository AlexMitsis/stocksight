#!/usr/bin/env python3
"""
Script to create an admin test account for development.
Usage: docker compose exec backend python create_admin.py
"""

from app.core.database import SessionLocal
from app.models.database import User
from app.services.auth_service import auth_service

def create_admin():
    db = SessionLocal()

    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.email == 'admin@test.com').first()

        if admin:
            print('✅ Admin account already exists!')
            print(f'   Email: admin@test.com')
            print(f'   Password: Admin123!')
            return

        # Create admin user
        hashed_password = auth_service.hash_password('Admin123!')
        admin = User(
            email='admin@test.com',
            hashed_password=hashed_password,
            country='US',
            preferred_currency='USD',
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print('✅ Admin account created successfully!')
        print(f'   Email: admin@test.com')
        print(f'   Password: Admin123!')
        print(f'   User ID: {admin.id}')

    except Exception as e:
        print(f'❌ Error creating admin account: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    create_admin()
