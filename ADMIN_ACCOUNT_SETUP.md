# Admin Test Account Setup

## Quick Access Account for Testing

An admin/test account has been configured for easy development and testing access.

### Account Credentials

```
Email: admin@test.com
Password: Admin123!
```

### Creating the Account

Run this command from your project root:

```bash
docker compose exec backend python create_admin.py
```

This will create the admin account if it doesn't already exist.

### Manual Account Creation (Alternative)

If you need to create the account manually or create additional test accounts:

```bash
docker compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.database import User
from app.services.auth_service import auth_service

db = SessionLocal()

# Create user
hashed_password = auth_service.hash_password('YourPassword123!')
user = User(
    email='yourtest@example.com',
    hashed_password=hashed_password,
    country='US',
    preferred_currency='USD',
    is_active=True
)
db.add(user)
db.commit()
print(f'User created: {user.email}')
db.close()
"
```

### Using the Account

1. Navigate to http://localhost:3000/login
2. Enter the admin credentials
3. You'll be redirected to the dashboard

### What You Can Access

Once logged in with the admin account, you have access to:

- ✅ **Dashboard** - Main application page
- ✅ **Chat Interface** - Stock analysis AI chat
- ✅ **Profile Settings** - View and edit account info
- ✅ **Change Password** - Update your password
- ✅ **Change Email** - Update your email address

### Security Note

⚠️ **Important**: This is a development/test account only.

- **Do NOT use this account in production**
- **Do NOT use this password for real accounts**
- **Delete or change credentials before deploying to production**

For production:
1. Create accounts through the signup flow
2. Use strong, unique passwords
3. Enable OAuth (Google/GitHub) - see `OAUTH_SETUP_GUIDE.md`
4. Consider implementing email verification
5. Consider implementing 2FA

---

## Multiple Test Accounts

You can create multiple test accounts for testing different scenarios:

```bash
# Create another test user
docker compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.database import User
from app.services.auth_service import auth_service

db = SessionLocal()
user = User(
    email='user2@test.com',
    hashed_password=auth_service.hash_password('Test1234!'),
    country='DE',  # Different country
    preferred_currency='EUR',  # Different currency
    is_active=True
)
db.add(user)
db.commit()
db.close()
print('Test user 2 created: user2@test.com / Test1234!')
"
```

---

## Troubleshooting

### "Email already registered"

The account already exists. You can:
1. Use the existing credentials to log in
2. Reset the password using the forgot password flow
3. Delete the user from the database and recreate it

### Cannot connect to database

Make sure Docker containers are running:

```bash
docker compose ps
docker compose up -d
```

### Permission errors

Make sure you're running the command from the project root directory where `docker-compose.yml` is located.
