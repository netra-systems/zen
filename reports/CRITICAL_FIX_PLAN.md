# Critical Infrastructure Fix Plan

## Priority 1: JWT Secret Synchronization (BLOCKER)

### Problem
Auth service and backend service use different JWT secrets, breaking all authentication.

### Solution Architecture
Create a SINGLE canonical JWT secret source that both services MUST use.

### Implementation Steps

#### Step 1: Create Shared Secret Configuration
```python
# shared/jwt_secret_manager.py (NEW FILE)
class SharedJWTSecretManager:
    """
    CRITICAL: Single source of JWT secret for ALL services.
    This violates microservice independence but is REQUIRED for authentication.
    """
    @staticmethod
    def get_jwt_secret() -> str:
        # 1. Check GCP Secret Manager (staging/production)
        # 2. Check environment variable JWT_SECRET_KEY
        # 3. Fail loudly if not found
        pass
```

#### Step 2: Update Auth Service
```python
# auth_service/auth_core/config.py
from shared.jwt_secret_manager import SharedJWTSecretManager

@staticmethod
def get_jwt_secret() -> str:
    return SharedJWTSecretManager.get_jwt_secret()  # SINGLE SOURCE
```

#### Step 3: Update Backend Service
```python
# netra_backend/app/core/configuration/unified_secrets.py
from shared.jwt_secret_manager import SharedJWTSecretManager

def get_jwt_secret(self) -> str:
    return SharedJWTSecretManager.get_jwt_secret()  # SINGLE SOURCE
```

#### Step 4: Add Validation Test
```python
# tests/integration/test_jwt_secret_sync.py
def test_jwt_secrets_are_synchronized():
    """CRITICAL: Ensure both services use EXACT same JWT secret"""
    auth_secret = auth_service.get_jwt_secret()
    backend_secret = backend_service.get_jwt_secret()
    assert auth_secret == backend_secret
    assert len(auth_secret) >= 32  # Security requirement
```

## Priority 2: ClickHouse/Redis Mandatory Configuration

### Problem
ClickHouse and Redis are treated as optional but are actually required.

### Solution Architecture
Make these services MANDATORY in staging/production with proper validation.

### Implementation Steps

#### Step 1: Update Configuration Schema
```python
# netra_backend/app/schemas/config.py
class StagingConfig(AppConfig):
    """Staging-specific configuration with MANDATORY services"""
    
    @validator('clickhouse_native')
    def validate_clickhouse(cls, v):
        if not v.host:
            raise ValueError("ClickHouse host is REQUIRED in staging")
        return v
    
    @validator('redis')
    def validate_redis(cls, v):
        if not v.host:
            raise ValueError("Redis host is REQUIRED in staging")
        return v

class ProductionConfig(AppConfig):
    """Production-specific configuration with MANDATORY services"""
    # Same validators as staging
```

#### Step 2: Update Environment Validator
```python
# netra_backend/app/core/environment_validator.py
def validate_required_services(environment: str) -> bool:
    """Validate that required services are configured"""
    if environment in ["staging", "production"]:
        # MUST have ClickHouse
        if not config.clickhouse_native.host:
            raise ConfigurationError("ClickHouse is REQUIRED in {environment}")
        
        # MUST have Redis  
        if not config.redis.host:
            raise ConfigurationError("Redis is REQUIRED in {environment}")
    
    return True
```

#### Step 3: Add Deployment Pre-flight Check
```python
# scripts/deployment_preflight.py
def preflight_check():
    """Pre-deployment validation"""
    environment = get_environment()
    
    if environment in ["staging", "production"]:
        # Check ClickHouse connectivity
        assert can_connect_to_clickhouse(), "ClickHouse connection REQUIRED"
        
        # Check Redis connectivity
        assert can_connect_to_redis(), "Redis connection REQUIRED"
        
        # Check JWT secret is set
        assert get_jwt_secret(), "JWT_SECRET_KEY REQUIRED"
        
        # Check JWT secrets match between services
        assert validate_jwt_secret_sync(), "JWT secrets MUST match"
```

#### Step 4: Update Deployment Script
```python
# scripts/deploy_to_gcp.py
def deploy():
    # Run preflight checks FIRST
    if not preflight_check():
        raise DeploymentError("Pre-flight checks FAILED - deployment aborted")
    
    # Continue with deployment...
```

## Priority 3: Integration Testing

### Add End-to-End Authentication Test
```python
# tests/e2e/test_authentication_flow.py
async def test_full_authentication_flow():
    """Test complete auth flow across services"""
    # 1. Login via auth service
    token = await auth_client.login(email, password)
    
    # 2. Use token with backend service
    user = await backend_client.get_current_user(token)
    
    # 3. Verify user data matches
    assert user.email == email
```

### Add Service Dependency Test
```python
# tests/integration/test_required_services.py
def test_clickhouse_is_accessible():
    """ClickHouse MUST be accessible"""
    client = get_clickhouse_client()
    assert client.ping(), "ClickHouse is REQUIRED but not accessible"

def test_redis_is_accessible():
    """Redis MUST be accessible"""
    client = get_redis_client()
    assert client.ping(), "Redis is REQUIRED but not accessible"
```

## Implementation Order

### Phase 1: JWT Secret Fix (TODAY)
1. Create shared JWT secret manager
2. Update both services to use it
3. Add synchronization test
4. Deploy and verify

### Phase 2: Service Requirements (TODAY)
1. Update configuration schemas
2. Add environment validators
3. Create preflight checks
4. Update deployment script

### Phase 3: Testing (TOMORROW)
1. Add integration tests
2. Add e2e authentication test
3. Run full test suite
4. Document results

## Success Criteria

### JWT Secret Success
- [ ] Both services use EXACTLY the same JWT secret
- [ ] Authentication works end-to-end
- [ ] Test passes: `test_jwt_secrets_are_synchronized`

### ClickHouse/Redis Success  
- [ ] Services are marked REQUIRED in staging/production
- [ ] Deployment fails if services are not configured
- [ ] Preflight checks prevent bad deployments

### Overall Success
- [ ] Staging deployment completes successfully
- [ ] Authentication works in staging
- [ ] All required services are connected
- [ ] No "optional" warnings for critical services

## Risk Mitigation

### Rollback Plan
1. Keep current configuration as backup
2. Test changes in development first
3. Deploy to staging before production
4. Monitor logs for any issues

### Monitoring
1. Add alerts for JWT mismatch errors
2. Monitor ClickHouse/Redis connectivity
3. Track authentication success rate
4. Log all configuration validation failures