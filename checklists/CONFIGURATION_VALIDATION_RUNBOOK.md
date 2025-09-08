# Configuration Validation Runbook

## Critical Configuration Hierarchy

```
1. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml (Ultimate source of truth)
2. Environment-specific configs (.env.staging, .env.production)  
3. Service-specific configs (configuration.py files)
4. Shared configs (isolated_environment.py)
5. Runtime configs (command line args, env vars)
```

## Pre-Validation Checklist

### Step 1: Check Mission Critical Values
```bash
# Open and review the critical values index
cat SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml | head -100
```
Key values to verify:
- [ ] SERVICE_ID = "netra-backend" (no timestamps!)
- [ ] Frontend URLs (NEXT_PUBLIC_*)
- [ ] OAuth credentials per environment
- [ ] JWT secret configuration

### Step 2: Environment Isolation Check
```bash
# Ensure no config leakage between environments
grep -r "staging" . --include="*.production" 
grep -r "production" . --include="*.staging"
grep -r "localhost" . --include="*.production"
```

### Step 3: Direct Environment Access Audit
```bash
# Find violations of IsolatedEnvironment pattern
grep -r "os\.environ\[" . --include="*.py" | grep -v isolated_environment
grep -r "os\.getenv" . --include="*.py" | grep -v isolated_environment
```

## Service-Specific Validation

### Backend Service Configuration
```python
# Validate backend configuration
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager

config = UnifiedConfigurationManager()
print(f"Environment: {config.environment}")
print(f"Service ID: {config.service_id}")  # MUST be "netra-backend"
print(f"Auth URL: {config.auth_service_url}")
print(f"Database URL: {config.database_url}")
print(f"Redis URL: {config.redis_url}")

# Check for hardcoded values
assert config.service_id == "netra-backend", "SERVICE_ID must be stable!"
assert "timestamp" not in config.service_id, "No timestamps in SERVICE_ID!"
```

### Auth Service Configuration
```python
# Validate auth configuration
from auth_service.auth_core.configuration import AuthConfig

config = AuthConfig()
print(f"Environment: {config.ENVIRONMENT}")
print(f"OAuth Client ID: {config.GOOGLE_CLIENT_ID[:10]}...")  # Partial for security
print(f"JWT Secret Set: {bool(config.JWT_SECRET_KEY)}")
print(f"Database URL: {config.DATABASE_URL}")

# Verify OAuth credentials exist
assert config.GOOGLE_CLIENT_ID, "OAuth Client ID missing!"
assert config.GOOGLE_CLIENT_SECRET, "OAuth Client Secret missing!"
```

### Frontend Configuration
```bash
# Check frontend environment files
for env in staging production; do
  echo "=== Frontend $env ==="
  cat frontend/.env.$env | grep -E "NEXT_PUBLIC_"
done

# Verify URLs match expected patterns
grep "NEXT_PUBLIC_API_URL" frontend/.env.staging | grep -q "staging"
grep "NEXT_PUBLIC_API_URL" frontend/.env.production | grep -v "staging"
```

## Common Configuration Issues

### Issue 1: Missing OAuth Credentials
**Symptoms**: 503 errors, auth service won't start
**Diagnosis**:
```bash
# Check if OAuth vars are set
cat auth_service/.env.staging | grep GOOGLE_CLIENT
cat auth_service/.env.production | grep GOOGLE_CLIENT
```
**Fix**:
```bash
# Add to appropriate .env file
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Issue 2: Wrong Environment URLs
**Symptoms**: Staging hitting production or vice versa
**Diagnosis**:
```python
from shared.isolated_environment import IsolatedEnvironment
env = IsolatedEnvironment()
print(f"Current env: {env.get('ENVIRONMENT')}")
print(f"API URL: {env.get('API_URL')}")
```
**Fix**: Update environment-specific .env files

### Issue 3: SERVICE_ID Instability
**Symptoms**: Authentication fails periodically
**Diagnosis**:
```bash
grep -r "SERVICE_ID.*datetime" . --include="*.py"
grep -r "SERVICE_ID.*uuid" . --include="*.py"
```
**Fix**: Hardcode to "netra-backend" everywhere

### Issue 4: Database Connection Strings
**Symptoms**: Can't connect to database
**Diagnosis**:
```python
# Check connection string format
from netra_backend.app.db.database_manager import DatabaseManager
manager = DatabaseManager()
print(f"DB URL: {manager.database_url}")
# Should be: postgresql://user:pass@host:port/dbname
```
**Fix**: Ensure proper URL format with credentials

### Issue 5: Redis Configuration
**Symptoms**: Session/cache issues
**Diagnosis**:
```python
from netra_backend.app.db.redis_manager import RedisManager
manager = RedisManager()
print(f"Redis URL: {manager.redis_url}")
# Should be: redis://host:port/db
```
**Fix**: Update REDIS_URL in environment

## Environment-Specific Configurations

### Development Environment
```bash
# Local development defaults
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/netra_dev
REDIS_URL=redis://localhost:6379/0
API_URL=http://localhost:8000
AUTH_URL=http://localhost:8081
FRONTEND_URL=http://localhost:3000
```

### Staging Environment
```bash
# Staging cloud services
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/netra_staging
REDIS_URL=redis://staging-redis:6379/0
API_URL=https://api.staging.netrasystems.ai
AUTH_URL=https://auth.staging.netrasystems.ai
FRONTEND_URL=https://staging.netrasystems.ai
```

### Production Environment
```bash
# Production cloud services
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@prod-db:5432/netra_prod
REDIS_URL=redis://prod-redis:6379/0
API_URL=https://api.netrasystems.ai
AUTH_URL=https://auth.netrasystems.ai
FRONTEND_URL=https://netrasystems.ai
```

## CORS Configuration Validation

```python
# Check CORS settings
from shared.cors_config_builder import CORSConfigBuilder

builder = CORSConfigBuilder()
config = builder.build()
print(f"Allowed origins: {config['allow_origins']}")

# Should include appropriate URLs for environment
# Staging: https://staging.netrasystems.ai
# Production: https://netrasystems.ai
```

## Secret Management Validation

### JWT Secret Consistency
```python
# Verify JWT secret is consistent across services
from shared.jwt_secret_manager import JWTSecretManager

manager = JWTSecretManager()
secret = manager.get_secret()
print(f"JWT Secret Length: {len(secret)}")
print(f"JWT Secret Hash: {hash(secret)}")  # Should be same across services
```


## Configuration Dependency Map

Critical dependencies that must align:
```
Frontend NEXT_PUBLIC_API_URL → Backend listening address
Frontend NEXT_PUBLIC_AUTH_URL → Auth service listening address  
Frontend NEXT_PUBLIC_WS_URL → Backend WebSocket endpoint
Backend AUTH_SERVICE_URL → Auth service internal address
Backend SERVICE_ID → Auth service expected service IDs
All services JWT_SECRET → Must be identical
```

## Validation Scripts

### Quick Validation
```bash
# Run configuration compliance check
python scripts/check_architecture_compliance.py --config-only

# Check auth configuration
python scripts/check_auth_ssot_compliance.py
```

### Deep Validation
```python
# config_validator.py
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
from auth_service.auth_core.configuration import AuthConfig

def validate_all_configs():
    errors = []
    
    # Check backend
    backend_config = UnifiedConfigurationManager()
    if backend_config.service_id != "netra-backend":
        errors.append("SERVICE_ID is not stable")
    
    # Check auth
    auth_config = AuthConfig()
    if not auth_config.GOOGLE_CLIENT_ID:
        errors.append("OAuth credentials missing")
    
    # Check environment consistency
    env = IsolatedEnvironment()
    if env.get('ENVIRONMENT') not in ['development', 'staging', 'production']:
        errors.append(f"Invalid environment: {env.get('ENVIRONMENT')}")
    
    return errors

errors = validate_all_configs()
if errors:
    print("Configuration errors found:")
    for error in errors:
        print(f"  - {error}")
else:
    print("All configurations valid!")
```

## Recovery Procedures

### When Configuration is Corrupted
1. Stop all services
2. Backup current configs
3. Reset to known good state:
   ```bash
   git checkout -- */.env*
   git checkout -- */configuration.py
   ```
4. Re-apply environment-specific values
5. Validate with scripts above
6. Restart services incrementally

### When Services Can't Communicate
1. Check SERVICE_ID stability
2. Verify JWT secrets match
3. Check network connectivity
4. Validate CORS settings
5. Review service discovery endpoints

## Configuration Checklist

Before deployment:
- [ ] All mission critical values verified
- [ ] Environment isolation confirmed
- [ ] No direct os.environ access
- [ ] OAuth credentials present
- [ ] JWT secret consistent
- [ ] URLs match environment
- [ ] CORS properly configured
- [ ] Database connections valid
- [ ] Redis connections valid
- [ ] SERVICE_ID = "netra-backend"
- [ ] No hardcoded secrets
- [ ] Configuration tests pass

Validated by: _______________
Date/Time: _______________
Environment: _______________