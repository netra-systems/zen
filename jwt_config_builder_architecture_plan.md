# JWT Configuration Builder Architecture Integration Plan

## Executive Summary

This document specifies the design of the **JWT Configuration Builder** - a unified, environment-aware JWT/authentication configuration system that consolidates scattered JWT settings across the Netra platform into one canonical SSOT implementation following the established builder pattern.

**Business Value Justification (BVJ):**
- **Segment:** Platform/Internal (affects ALL customer segments)
- **Business Goal:** Prevent $12K MRR loss from JWT configuration mismatches
- **Value Impact:** Eliminates authentication failures between auth_service and backend
- **Strategic Impact:** Ensures reliable authentication foundation for growth

## Current State Analysis

### JWT Configuration Scatter Problem

**Current JWT configurations are scattered across multiple locations:**

1. **`auth_service/auth_core/core/jwt_handler.py`** (947 lines)
   - Uses: `JWT_ACCESS_EXPIRY_MINUTES`, `JWT_REFRESH_EXPIRY_DAYS`, `JWT_SERVICE_EXPIRY_MINUTES`
   - Environment detection: Complex multi-source detection
   - Secret handling: Production-specific validation rules

2. **`netra_backend/app/core/auth_constants.py`** (226 lines) 
   - Uses: `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (different variable name!)
   - Hard-coded defaults: `DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30`
   - Contains outdated environment variable mappings

3. **`shared/jwt_config.py`** (163 lines)
   - Uses: Hard-coded values (no environment variables)
   - `get_access_token_expire_minutes() -> 15` (hard-coded!)
   - `get_jwt_secret_from_env()` - Basic secret loading

4. **`netra_backend/app/clients/auth_client_core.py`** (1201 lines)
   - Service-to-service auth headers: `X-Service-ID`, `X-Service-Secret`
   - Different credential resolution pattern than auth_service

### CRITICAL Configuration Inconsistencies

**From failing test `test_jwt_config_builder_critical.py`:**

1. **Environment Variable Name Mismatches:**
   - auth_service uses: `JWT_ACCESS_EXPIRY_MINUTES`
   - Documentation expects: `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`  
   - shared/jwt_config.py: Hard-coded 15 minutes (ignores environment)

2. **Service-to-Service Authentication Mismatches:**
   - Different `SERVICE_ID`/`SERVICE_SECRET` resolution between services
   - Auth headers constructed differently across services

3. **Environment-Specific Configuration Gaps:**
   - Auth service validates secrets per environment, shared config doesn't
   - Different validation rules cause staging/production failures

## Target State Architecture

### JWT Configuration Builder Pattern

**Single Canonical Implementation at `/shared/jwt_config_builder.py`:**

```python
class JWTConfigurationBuilder:
    """
    Unified JWT configuration builder following DatabaseURLBuilder and RedisConfigurationBuilder patterns.
    
    Provides organized access to all JWT configurations:
    - connection.get_jwt_secret_key()
    - token.get_access_token_config()
    - token.get_refresh_token_config()
    - service.get_service_auth_config()
    - validation.validate_configuration()
    - environment_detection.detect_environment()
    """
```

### Sub-Builder Architecture

Following the pattern established by `RedisConfigurationBuilder`:

#### 1. **ConnectionBuilder** - JWT Secret Management
```python
class ConnectionBuilder:
    """Manages JWT secret key resolution with proper fallback chains."""
    
    def get_jwt_secret_key(self) -> str:
        """Get JWT secret with environment-specific validation."""
        
    def validate_jwt_secret(self, secret: str) -> Tuple[bool, str]:
        """Validate JWT secret meets security requirements."""
        
    @property
    def secret_info(self) -> JWTSecretInfo:
        """Get comprehensive JWT secret information."""
```

#### 2. **TokenBuilder** - JWT Token Configuration  
```python
class TokenBuilder:
    """Manages JWT token expiry and configuration settings."""
    
    def get_access_token_config(self) -> JWTTokenConfig:
        """Get access token configuration with environment awareness."""
        
    def get_refresh_token_config(self) -> JWTTokenConfig:
        """Get refresh token configuration."""
        
    def get_service_token_config(self) -> JWTTokenConfig:
        """Get service-to-service token configuration."""
```

#### 3. **ServiceBuilder** - Service-to-Service Authentication
```python
class ServiceBuilder:
    """Manages service-to-service authentication configuration."""
    
    def get_service_auth_config(self) -> ServiceAuthConfig:
        """Get service authentication configuration."""
        
    def get_service_headers(self) -> Dict[str, str]:
        """Get standardized service auth headers."""
        
    def validate_service_credentials(self) -> Tuple[bool, str]:
        """Validate service credentials are properly configured."""
```

#### 4. **ValidationBuilder** - Configuration Validation
```python
class ValidationBuilder:
    """Validates JWT configuration consistency and security."""
    
    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate complete JWT configuration."""
        
    def check_environment_consistency(self) -> List[str]:
        """Check for environment-specific configuration issues."""
        
    def detect_configuration_conflicts(self) -> List[str]:
        """Detect conflicting JWT configuration values."""
```

#### 5. **EnvironmentBuilder** - Environment-Aware Configuration
```python
class EnvironmentBuilder:
    """Manages environment-specific JWT configuration."""
    
    def get_development_config(self) -> Dict[str, Any]:
        """Get JWT configuration for development."""
        
    def get_staging_config(self) -> Dict[str, Any]:
        """Get JWT configuration for staging."""
        
    def get_production_config(self) -> Dict[str, Any]:
        """Get JWT configuration for production."""
```

## Integration Points

### 1. Auth Service Integration

**`auth_service/auth_core/core/jwt_handler.py` refactoring:**

```python
# BEFORE (current implementation)
class JWTHandler:
    def __init__(self):
        self.secret = self._get_jwt_secret()
        self.service_secret = AuthConfig.get_service_secret()
        # ... complex initialization

# AFTER (using JWT Configuration Builder)
class JWTHandler:
    def __init__(self):
        from shared.jwt_config_builder import JWTConfigurationBuilder
        self._jwt_builder = JWTConfigurationBuilder(get_env().get_all())
        
        self.secret = self._jwt_builder.connection.get_jwt_secret_key()
        self.service_secret = self._jwt_builder.service.get_service_secret()
        # ... simplified initialization using builder
```

### 2. Backend Service Integration

**`netra_backend/app/clients/auth_client_core.py` refactoring:**

```python
# BEFORE (current implementation)
class AuthServiceClient:
    def _get_service_auth_headers(self) -> Dict[str, str]:
        headers = {}
        if self.service_id and self.service_secret:
            headers["X-Service-ID"] = self.service_id
            headers["X-Service-Secret"] = self.service_secret
        return headers

# AFTER (using JWT Configuration Builder)  
class AuthServiceClient:
    def _get_service_auth_headers(self) -> Dict[str, str]:
        from shared.jwt_config_builder import JWTConfigurationBuilder
        jwt_builder = JWTConfigurationBuilder(os.environ)
        return jwt_builder.service.get_service_headers()
```

### 3. Shared Configuration Integration

**Replace `shared/jwt_config.py` entirely:**

```python
# TOMBSTONE: shared/jwt_config.py - replaced by JWT Configuration Builder
# Legacy functions for backward compatibility only
from shared.jwt_config_builder import JWTConfigurationBuilder

def get_jwt_secret_key(env_manager) -> str:
    """DEPRECATED: Use JWTConfigurationBuilder instead."""
    builder = JWTConfigurationBuilder(env_manager.get_all())
    return builder.connection.get_jwt_secret_key()
```

## Environment Variable Standardization

### Canonical Environment Variable Names

**Primary Environment Variables (SSOT):**
```bash
# JWT Secret Management
JWT_SECRET_KEY=<secret>                    # Primary JWT secret
JWT_ALGORITHM=HS256                        # JWT algorithm (default: HS256)

# Token Expiry Configuration
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15         # Standardized variable name
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7            # Refresh token expiry
JWT_SERVICE_TOKEN_EXPIRE_MINUTES=60        # Service token expiry

# Service-to-Service Authentication  
SERVICE_ID=netra-backend                   # Service identifier
SERVICE_SECRET=<secret>                    # Service secret key

# Environment Detection
ENVIRONMENT=development|staging|production # Environment identifier
```

**Legacy Variable Support (with deprecation warnings):**
```bash
# Legacy variables supported with warnings
JWT_ACCESS_EXPIRY_MINUTES              # DEPRECATED: Use JWT_ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_EXPIRY_DAYS               # DEPRECATED: Use JWT_REFRESH_TOKEN_EXPIRE_DAYS
JWT_SERVICE_EXPIRY_MINUTES            # DEPRECATED: Use JWT_SERVICE_TOKEN_EXPIRE_MINUTES
JWT_SECRET                            # DEPRECATED: Use JWT_SECRET_KEY
```

## Service Boundary Compliance

### Auth Service Independence Maintained

**Auth service integration:**
- Uses `/shared/jwt_config_builder.py` (cross-service import - acceptable)
- Maintains own `IsolatedEnvironment` for environment access
- No dependencies on `netra_backend` specific code
- Full independence while using shared JWT configuration logic

### Backend Service Integration

**Backend service integration:**
- Integrates through existing configuration patterns
- Replaces scattered JWT constants with unified builder
- Maintains existing external interfaces
- Uses builder through dependency injection pattern

### Cross-Service Consistency Guarantees

**All services use identical configuration:**
- Same environment variable resolution
- Same validation rules
- Same fallback logic  
- Same service authentication patterns

## Legacy Module Removal Plan

### Phase 1: Implementation (Week 1)

**Create new implementation:**
1. Create `/shared/jwt_config_builder.py` with full builder pattern
2. Implement all sub-builders following `RedisConfigurationBuilder` pattern  
3. Add comprehensive unit and integration tests

### Phase 2: Integration (Week 1)

**Integrate with existing services:**
1. **auth_service:** Refactor `JWTHandler` to use builder
2. **netra_backend:** Update `AuthServiceClient` and auth constants
3. **shared:** Add backward compatibility wrappers

### Phase 3: Validation (Week 2)

**Comprehensive testing:**
1. Run failing test `test_jwt_config_builder_critical.py` - should now PASS
2. Execute full regression test suite
3. Validate in development, staging, and production environments

### Phase 4: Legacy Removal (Week 2)

**Clean up legacy code:**

#### Files to REFACTOR (keep but simplify):
1. **`auth_service/auth_core/core/jwt_handler.py`**
   - Replace direct environment access with JWT builder
   - Simplify initialization logic (~200 lines reduction)

2. **`netra_backend/app/core/auth_constants.py`**
   - Remove duplicate JWT constants
   - Keep only constants not covered by builder (~50 lines reduction)

3. **`netra_backend/app/clients/auth_client_core.py`**
   - Replace custom service auth logic with builder
   - Standardize header construction (~100 lines reduction)

#### Files to REPLACE entirely:
1. **`shared/jwt_config.py`** → **`shared/jwt_config_builder.py`**
   - Complete replacement with builder pattern
   - Backward compatibility wrappers for existing imports
   - (~163 lines → ~400 lines with full builder functionality)

#### Configuration Files to UPDATE:
1. **Environment variable documentation**
2. **Deployment configuration templates**
3. **Development launcher configuration**

## Risk Mitigation Strategy

### High Risk: Breaking Authentication

**Risk:** JWT configuration changes break existing authentication  
**Mitigation:** 
- Comprehensive backward compatibility
- Extensive integration testing
- Staged rollout (development → staging → production)
- Rollback plan with original configurations

### Medium Risk: Environment Inconsistency

**Risk:** Different environments end up with different JWT configurations  
**Mitigation:**
- Environment-specific validation in builder
- Automated configuration consistency checks
- Staging environment validation before production deployment

### Medium Risk: Service Integration Failures

**Risk:** Service-to-service authentication breaks during migration  
**Mitigation:**
- Service authentication integration testing
- Cross-service validation tests
- Blue-green deployment with traffic splitting

### Low Risk: Performance Impact

**Risk:** Builder pattern adds authentication overhead  
**Mitigation:**
- Caching of configuration values
- Lazy initialization patterns
- Performance benchmarking

## Service Integration Testing Strategy

### Critical Path Authentication Flows

**Test scenarios that must continue working:**

1. **User Authentication Flow:**
   - Frontend → Backend → Auth Service
   - JWT token generation and validation
   - Token refresh operations

2. **Service-to-Service Authentication:**
   - Backend → Auth Service API calls
   - Service token generation and validation
   - Cross-service header authentication

3. **WebSocket Authentication:**
   - JWT token validation for WebSocket connections
   - Real-time authentication state management
   - Token expiry handling in persistent connections

### Integration Test Requirements

**Pre-deployment validation:**
```bash
# Critical authentication tests
python unified_test_runner.py --category integration --filter jwt_config
python unified_test_runner.py --category api --filter authentication
python unified_test_runner.py --env staging --filter jwt_token

# Cross-service authentication tests
python -m pytest tests/integration/test_jwt_config_builder_critical.py -v
python -m pytest tests/e2e/test_auth_jwt_*.py -v
python -m pytest tests/integration/critical_paths/test_*jwt*.py -v
```

**Success criteria:**
- All existing JWT-related tests pass
- New consistency test `test_jwt_config_builder_critical.py` passes
- No authentication failures in staging environment
- Service-to-service authentication maintains 100% success rate

## Implementation Success Metrics

### Immediate Success (Week 1-2)
- **Configuration Consistency:** Zero JWT configuration mismatches between services
- **Test Success:** `test_jwt_config_builder_critical.py` passes with 0 failures
- **Backward Compatibility:** All existing authentication flows work without changes
- **Code Reduction:** ~300 lines of scattered configuration code eliminated

### Short-term Success (Month 1)
- **Authentication Reliability:** Zero authentication failures due to configuration mismatches
- **Development Experience:** JWT configuration debugging time reduced by 60%
- **Deployment Stability:** Zero staging deployment failures due to JWT configuration issues
- **Service Consistency:** All services use identical JWT configuration patterns

### Long-term Success (Quarter 1)
- **Business Impact:** $12K MRR risk eliminated through reliable authentication
- **Platform Stability:** JWT-related incidents reduced by 90%
- **Technical Debt:** JWT configuration technical debt score improved to >95%
- **Developer Productivity:** New developer onboarding time reduced by 30 minutes

## Conclusion

The JWT Configuration Builder eliminates critical authentication configuration inconsistencies that cause $12K MRR loss through service failures. By following the established builder pattern and maintaining service boundaries, this implementation ensures reliable, consistent JWT configuration across the entire Netra platform.

**Total Impact:**
- **Risk Elimination:** $12K monthly MRR risk from authentication failures
- **Code Consolidation:** ~400 lines of scattered configuration into one canonical builder
- **Platform Stability:** Consistent JWT configuration across all services and environments
- **Developer Experience:** Simplified JWT debugging and configuration management

**Next Steps:** Proceed to implementation following the phased approach outlined above, with continuous integration testing to ensure zero breaking changes to existing authentication flows.