# 🔴 CRITICAL: Database Architecture for Auth Separation

## Database Separation Strategy

### Two Separate Databases

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTH SERVICE DATABASE                      │
│                  (Managed by Auth Service)                   │
│                                                              │
│  Tables:                                                     │
│  - users (master copy)                                      │
│  - sessions                                                  │
│  - oauth_tokens                                             │
│  - refresh_tokens                                           │
│  - password_resets                                          │
│  - login_attempts                                           │
│                                                              │
│  ⚠️ ONLY the auth service writes to these tables            │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  MAIN BACKEND DATABASE                       │
│                  (Managed by Main Backend)                   │
│                                                              │
│  Tables:                                                     │
│  - userbase (read-only mirror of auth users)               │
│  - secrets (user settings/preferences)                      │
│  - tool_usage_logs                                          │
│  - agent_sessions                                           │
│  - corpus_data                                              │
│  - ... (all business logic tables)                          │
│                                                              │
│  ⚠️ NEVER writes to authentication fields                   │
└──────────────────────────────────────────────────────────────┘
```

## User Table Synchronization

### Data Flow
```
Auth Service DB          Main Backend DB
    users       ------>     userbase
   (master)              (read-only mirror)
```

### Synchronization Rules
1. Auth service is the ONLY source of truth for user authentication
2. Main backend's `userbase` table is synchronized FROM auth service
3. Synchronization happens via:
   - Auth service webhooks on user create/update
   - Periodic sync jobs
   - Real-time event streaming (production)

## Field Ownership

### Auth Service OWNS These Fields
```sql
-- Only auth service can write these
hashed_password      -- Password hash
email               -- User email (used for login)
email_verified      -- Email verification status
mfa_enabled         -- Multi-factor auth status
mfa_secret          -- MFA secret key
last_login          -- Last login timestamp
password_changed_at -- Password change timestamp
failed_login_count  -- Failed login attempts
account_locked      -- Account lock status
```

### Main Backend OWNS These Fields
```sql
-- Only main backend can write these
full_name           -- User display name
picture             -- Profile picture URL
role                -- Application role
permissions         -- Application permissions
plan_tier           -- Subscription plan
feature_flags       -- Enabled features
tool_permissions    -- Tool access permissions
created_at          -- Record creation (in main DB)
updated_at          -- Record update (in main DB)
```

## Migration Guidelines

### Creating User-Related Migrations

#### ✅ CORRECT: Main Backend Migration
```python
def upgrade():
    # Add business logic fields only
    op.add_column('userbase', 
        sa.Column('plan_tier', sa.String(), nullable=True))
    op.add_column('userbase',
        sa.Column('feature_flags', sa.JSON(), nullable=True))
```

#### ❌ WRONG: Auth Fields in Main Backend
```python
def upgrade():
    # NEVER add auth fields to main backend!
    op.add_column('userbase',
        sa.Column('password_hash', sa.String()))  # WRONG!
    op.add_column('userbase',
        sa.Column('mfa_secret', sa.String()))     # WRONG!
```

## Database Access Patterns

### Reading User Data
```python
# ✅ CORRECT: Read from local database
user = db.query(User).filter(User.id == user_id).first()
print(f"User plan: {user.plan_tier}")
```

### Authenticating Users
```python
# ❌ WRONG: Direct authentication
user = db.query(User).filter(User.email == email).first()
if verify_password(password, user.hashed_password):  # NEVER DO THIS!
    # authenticate

# ✅ CORRECT: Use auth service
result = await auth_client.login(email, password)
if result and result.get("valid"):
    user_id = result.get("user_id")
    # Now fetch user from local DB for app data
    user = db.query(User).filter(User.id == user_id).first()
```

### Updating User Profile
```python
# ✅ CORRECT: Update business fields
user.plan_tier = "premium"
user.feature_flags = {"advanced_ai": True}
db.commit()

# ❌ WRONG: Update auth fields
user.hashed_password = hash_password(new_password)  # NEVER!
db.commit()

# ✅ CORRECT: Update password via auth service
await auth_client.change_password(user_id, old_password, new_password)
```

## User Creation Flow

### Complete Flow
1. User registers via auth service
2. Auth service creates user in auth DB
3. Auth service sends webhook to main backend
4. Main backend creates user record in userbase table
5. Main backend sets default plan/permissions

### Implementation
```python
# Webhook handler in main backend
@app.post("/webhooks/auth/user-created")
async def handle_user_created(data: dict, db: Session):
    """Handle user creation from auth service."""
    # Create local user record
    user = User(
        id=data["user_id"],
        email=data["email"],
        full_name=data.get("full_name"),
        # Set business defaults
        plan_tier="free",
        role="standard_user",
        permissions={},
        feature_flags={}
    )
    db.add(user)
    db.commit()
```

## Session Management

### Session Storage
- **Auth Service**: Manages authentication sessions
- **Main Backend**: Stores application state only

### Session Validation
```python
# Every request validates with auth service
async def get_current_user(token: str, db: Session):
    # 1. Validate token with auth service
    validation = await auth_client.validate_token(token)
    if not validation or not validation.get("valid"):
        raise Unauthorized()
    
    # 2. Get user from local DB
    user_id = validation.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # User exists in auth but not local - sync issue
        await sync_user_from_auth(user_id)
        user = db.query(User).filter(User.id == user_id).first()
    
    return user
```

## Common Pitfalls

### 1. Password in Main Backend
❌ **NEVER** store or process passwords in main backend
✅ **ALWAYS** use auth_client for password operations

### 2. Direct User Creation
❌ **NEVER** create users directly in main backend
✅ **ALWAYS** create users through auth service

### 3. Session Validation
❌ **NEVER** validate sessions locally
✅ **ALWAYS** validate with auth service

### 4. Email Changes
❌ **NEVER** change email in main backend
✅ **ALWAYS** change email through auth service

## Environment Configuration

### Auth Service Database
```env
# Auth service environment
AUTH_DB_HOST=auth-db.internal
AUTH_DB_NAME=auth_production
AUTH_DB_USER=auth_service
AUTH_DB_PASSWORD=<secret>
```

### Main Backend Database
```env
# Main backend environment
DB_HOST=main-db.internal
DB_NAME=netra_production
DB_USER=backend_service
DB_PASSWORD=<secret>

# Auth service connection
AUTH_SERVICE_URL=http://auth-service.internal:8001
AUTH_SERVICE_API_KEY=<secret>
```

## Monitoring and Alerts

### Critical Alerts
1. User exists in auth but not main backend
2. User data out of sync between databases
3. Auth webhook failures
4. Unauthorized password field access attempts

### Sync Health Checks
```python
async def check_user_sync_health():
    """Check if users are in sync."""
    # Get user count from auth service
    auth_users = await auth_client.get_user_count()
    
    # Get user count from local DB
    local_users = db.query(User).count()
    
    # Alert if mismatch
    if abs(auth_users - local_users) > 10:
        alert("User sync issue detected")
```

## Final Checklist

Before any database change involving users:
- [ ] Am I only modifying business logic fields?
- [ ] Am I avoiding ALL authentication fields?
- [ ] Are migrations only touching allowed fields?
- [ ] Are tests using auth service for authentication?
- [ ] Is user creation going through auth service?
- [ ] Is password handling going through auth service?

## Emergency Procedures

### If Auth Service is Down
1. Cache recent validations (5 min TTL)
2. Fail closed - deny access if uncertain
3. Log all failures for audit
4. Alert operations team immediately

### If Databases Out of Sync
1. Run manual sync job
2. Verify webhook configuration
3. Check for failed webhook deliveries
4. Reconcile differences with auth as source of truth