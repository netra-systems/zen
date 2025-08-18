# 🔴 CRITICAL: Database Architecture for Auth Separation

## 📋 EXECUTIVE SUMMARY

**🚨 READ THIS FIRST**: The presence of user tables and `hashed_password` fields in BOTH the auth service database AND the main backend database is **100% CORRECT and INTENTIONAL**.

### Key Points:
1. ✅ **Two user tables are REQUIRED** - auth service has the master, main backend has a synchronized copy
2. ✅ **hashed_password in userbase table is CORRECT** - it's managed by auth service, not main backend
3. ✅ **This is NOT duplication** - it's a deliberate architectural pattern for performance and reliability
4. ⚠️ **Main backend NEVER writes auth fields** - only reads synchronized data from auth service
5. 🔄 **Auth service owns and synchronizes** user authentication data to main backend

## ✅ CORRECT: Having User Tables in BOTH Databases

**IMPORTANT**: Having user tables in both the auth service database AND the main backend database is **CORRECT and INTENTIONAL**. This is NOT a mistake or duplication error.

## Database Separation Strategy

### Two Separate Databases with Synchronized User Data

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTH SERVICE DATABASE                      │
│                  (Managed by Auth Service)                   │
│                                                              │
│  Tables:                                                     │
│  - users (MASTER copy of all user data)                    │
│  - sessions                                                  │
│  - oauth_tokens                                             │
│  - refresh_tokens                                           │
│  - password_resets                                          │
│  - login_attempts                                           │
│                                                              │
│  ⚠️ ONLY the auth service writes to these tables            │
│  📍 This is the AUTHORITATIVE source for user data          │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  MAIN BACKEND DATABASE                       │
│                  (Managed by Main Backend)                   │
│                                                              │
│  Tables:                                                     │
│  - userbase (SYNCHRONIZED copy of auth users) ✅ CORRECT   │
│  - secrets (user settings/preferences)                      │
│  - tool_usage_logs                                          │
│  - agent_sessions                                           │
│  - corpus_data                                              │
│  - ... (all business logic tables)                          │
│                                                              │
│  ⚠️ Main backend manages business fields only               │
│  📍 Auth fields are synchronized FROM auth service          │
└──────────────────────────────────────────────────────────────┘
```

## User Table Synchronization Pattern

### Data Flow (This is CORRECT Architecture)
```
Auth Service DB          Main Backend DB
    users       ------>     userbase
   (master)              (synchronized copy)
                         
   📍 WRITES              📍 RECEIVES UPDATES
   📍 OWNS AUTH DATA      📍 OWNS BUSINESS DATA
```

### Synchronization Rules
1. Auth service is the ONLY source of truth for user authentication
2. Main backend's `userbase` table is synchronized FROM auth service
3. Synchronization happens via:
   - Auth service webhooks on user create/update
   - Periodic sync jobs
   - Real-time event streaming (production)

## Why We Need User Tables in BOTH Databases

### 🤔 Question: "Why not just query the auth service for user data?"

**Answer**: Performance, reliability, and data locality. Here's why the dual-table approach is CORRECT:

### 1. **Performance & Scalability**
```
❌ BAD: Query auth service for every operation
Frontend → Main Backend → Auth Service (for user data) → Main Backend → Response
(200ms+ latency per request)

✅ GOOD: Local user data with auth validation
Frontend → Main Backend → Validate token with auth service → Use local user data → Response
(50ms latency, cached validation)
```

### 2. **Data Locality for Business Logic**
```sql
-- ✅ EFFICIENT: Join local tables without network calls
SELECT u.full_name, u.plan_tier, ul.tool_name, ul.cost_cents
FROM userbase u
JOIN tool_usage_logs ul ON u.id = ul.user_id
WHERE u.plan_tier = 'enterprise';

-- ❌ SLOW: Would require external API calls for each user
```

### 3. **Reliability & Resilience**
- If auth service is temporarily down, business operations can continue
- User profile data (name, plan, permissions) remains available
- Only authentication fails gracefully, not the entire application

### 4. **Database Constraints & Referential Integrity**
```sql
-- ✅ WORKS: Foreign key constraints within same database
tool_usage_logs.user_id → userbase.id (FOREIGN KEY)
secrets.user_id → userbase.id (FOREIGN KEY)
agent_sessions.user_id → userbase.id (FOREIGN KEY)

-- ❌ IMPOSSIBLE: Cross-service foreign keys
tool_usage_logs.user_id → auth_service.users.id (NOT POSSIBLE)
```

## Field Ownership and Synchronization

### ✅ SYNCHRONIZED Fields (Auth Service → Main Backend)
```sql
-- These fields are synchronized FROM auth service TO main backend
-- Auth service WRITES, main backend RECEIVES
id                  -- User ID (primary key)
email               -- User email (used for login)
hashed_password     -- Password hash ✅ CORRECT in userbase table
email_verified      -- Email verification status
created_at          -- User creation timestamp
is_active           -- Account active status
```

**CRITICAL**: The `hashed_password` field in the main backend's `userbase` table is **CORRECT**. It's managed by the auth service and synchronized to the main backend. The main backend NEVER directly writes to this field.

### 🔒 Auth Service EXCLUSIVE Fields (NOT in Main Backend)
```sql
-- These fields exist ONLY in auth service database
mfa_enabled         -- Multi-factor auth status
mfa_secret          -- MFA secret key
last_login          -- Last login timestamp
password_changed_at -- Password change timestamp
failed_login_count  -- Failed login attempts
account_locked      -- Account lock status
sessions            -- Active sessions
oauth_tokens        -- OAuth provider tokens
refresh_tokens      -- Refresh tokens
password_resets     -- Password reset tokens
```

### 🏢 Main Backend EXCLUSIVE Fields (Business Logic)
```sql
-- These fields exist ONLY in main backend and are managed by main backend
full_name           -- User display name
picture             -- Profile picture URL
role                -- Application role (standard_user, admin, etc.)
permissions         -- Application permissions
plan_tier           -- Subscription plan (free, pro, enterprise)
plan_expires_at     -- Plan expiration date
plan_started_at     -- Plan start date
auto_renew          -- Auto-renewal setting
payment_status      -- Payment status (active, suspended, etc.)
trial_period        -- Trial period days
feature_flags       -- Enabled features
tool_permissions    -- Tool access permissions
is_developer        -- Developer status flag
is_superuser        -- Superuser flag
updated_at          -- Record update timestamp (in main DB)
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

## 🚨 IMPORTANT: What Developers Should Know

### When You See the `userbase` Table in Main Backend

**✅ THIS IS CORRECT** - Don't be alarmed by:
- The presence of a `userbase` table in the main backend database
- The `hashed_password` field in the `userbase` table
- User records being duplicated between auth service and main backend

**🔄 THIS IS SYNCHRONIZED DATA** - The `userbase` table is:
- A synchronized copy of user data from the auth service
- Maintained by the auth service through webhooks and sync jobs
- Used for local business logic and performance optimization

### What You CAN Do
```python
# ✅ READ user data for business logic
user = db.query(User).filter(User.id == user_id).first()
if user.plan_tier == "enterprise":
    # Grant enterprise features

# ✅ UPDATE business fields only
user.plan_tier = "pro"
user.feature_flags = {"advanced_ai": True}
db.commit()

# ✅ CREATE relationships with user
log = ToolUsageLog(user_id=user.id, tool_name="data_analysis")
db.add(log)
db.commit()
```

### What You CANNOT Do
```python
# ❌ NEVER write to auth fields
user.hashed_password = hash_password(new_password)  # FORBIDDEN!
user.email = "new@email.com"  # FORBIDDEN!
user.is_active = False  # FORBIDDEN!

# ❌ NEVER create users directly
user = User(email="test@example.com", hashed_password=hash_password("123"))  # FORBIDDEN!
db.add(user)  # This will break synchronization!

# ❌ NEVER authenticate directly
if verify_password(password, user.hashed_password):  # FORBIDDEN!
    # This bypasses the auth service!
```

## Common Pitfalls

### 1. Misunderstanding the userbase Table
❌ **WRONG**: "The userbase table shouldn't have hashed_password"
✅ **CORRECT**: "The userbase table is synchronized from auth service"

### 2. Password Operations in Main Backend
❌ **NEVER** store, hash, or verify passwords in main backend
✅ **ALWAYS** use auth_client for password operations

### 3. Direct User Creation
❌ **NEVER** create users directly in main backend
✅ **ALWAYS** create users through auth service

### 4. Session Validation
❌ **NEVER** validate sessions locally using hashed_password
✅ **ALWAYS** validate with auth service using tokens

### 5. Auth Field Modifications
❌ **NEVER** change email, password, or auth status in main backend
✅ **ALWAYS** change auth fields through auth service

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

## 🔍 Quick Troubleshooting

### "I see hashed_password in the main backend - is this wrong?"
**NO!** This is correct. The auth service synchronizes this field to the main backend for reference, but the main backend never writes to it.

### "Should I remove the userbase table to avoid duplication?"
**NO!** The userbase table is essential for:
- Performance (local queries instead of API calls)
- Reliability (works when auth service is down)
- Database relationships (foreign keys to other tables)

### "Can I authenticate users using the local hashed_password?"
**NO!** Always use the auth service for authentication. The local hashed_password is for reference only.

### "Why do we need both databases?"
**Separation of concerns**:
- Auth service = Authentication, security, user management
- Main backend = Business logic, application features, data processing

## Final Checklist

Before any database change involving users:
- [ ] Am I only modifying business logic fields?
- [ ] Am I avoiding ALL authentication fields?
- [ ] Are migrations only touching allowed fields?
- [ ] Are tests using auth service for authentication?
- [ ] Is user creation going through auth service?
- [ ] Is password handling going through auth service?
- [ ] Do I understand that userbase table is CORRECT and NECESSARY?

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