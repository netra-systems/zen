# JWT Configuration Builder Architecture

**Business Value Justification (BVJ):**
- **Segment:** Platform/Internal
- **Business Goal:** Eliminate configuration inconsistencies causing authentication failures
- **Value Impact:** Prevents $12K MRR loss from JWT config mismatches between services
- **Strategic Impact:** Ensures reliable authentication for all customer segments

## 1. Problem Analysis

After analyzing the codebase, I've identified specific JWT configuration management issues despite the mature authentication system:

### 1.1 Configuration Duplication Points

**Identified Duplications:**
1. **JWT Settings Logic:**
   - `auth_service/auth_core/config.py` (lines 118-139): JWT algorithm, expiry settings
   - `shared/jwt_config.py` (lines 31-48): Identical JWT settings
   - `netra_backend/app/clients/auth_client_config.py`: OAuth-related JWT configuration

2. **Secret Management:**
   - `auth_service/auth_core/config.py` `get_jwt_secret()` (lines 45-57)
   - `shared/jwt_config.py` `get_jwt_secret_from_env()` (lines 51-75)
   - `netra_backend/app/core/secret_manager.py`: JWT secret handling (lines 439-441)

3. **Environment-Specific Logic:**
   - Each service replicates environment detection for JWT settings
   - Validation rules duplicated across services
   - Service-to-service auth headers scattered in multiple files

### 1.2 Environment-Specific Config Challenges

**Current Issues:**
- Environment detection happens in multiple places with different logic
- JWT secret validation rules vary between services
- Service credentials management scattered across `auth_client_core.py` and config files
- No unified way to handle staging vs production JWT requirements

### 1.3 Service Boundary Violations to Avoid

**Critical Constraints:**
- Auth Service must remain completely independent (SPEC/independent_services.xml)
- Backend Service cannot directly access auth_service configuration
- Shared configuration must not create service coupling
- Each service must maintain its own IsolatedEnvironment

## 2. Architecture Design

### 2.1 JWT Configuration Builder Location

**Decision: Place in `/shared/jwt_config_builder.py`**

**Rationale:**
- Respects microservice independence
- Accessible to both Auth Service and Backend Service
- Follows existing pattern (`shared/jwt_config.py`)
- Maintains SSOT principle within shared boundaries

### 2.2 Interface Design

```python
class JWTConfigurationBuilder:
    """Unified JWT configuration builder respecting service boundaries."""
    
    def __init__(self, env_manager, service_name: str):
        self.env_manager = env_manager  # IsolatedEnvironment instance
        self.service_name = service_name  # "auth_service" or "netra_backend"
    
    # Core Methods
    def build_complete_config(self) -> JWTConfiguration
    def build_token_config(self) -> TokenConfiguration  
    def build_service_auth_config(self) -> ServiceAuthConfiguration
    def validate_configuration(self) -> ConfigValidationResult
    
    # Environment-Specific
    def get_environment_overrides(self) -> Dict[str, Any]
    def is_production_grade(self) -> bool
    
    # Migration Support
    def get_legacy_compatibility_mappings(self) -> Dict[str, str]
```

**Key Data Structures:**
```python
@dataclass
class JWTConfiguration:
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    service_token_expire_minutes: int = 60
    environment: str
    service_name: str
    
@dataclass  
class ServiceAuthConfiguration:
    service_id: str
    service_secret: str
    headers: Dict[str, str]
    
@dataclass
class ConfigValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
```

### 2.3 Integration Points with Existing Systems

**Integration Architecture:**

1. **Auth Service Integration:**
   ```python
   # auth_service/auth_core/config.py - MODIFIED
   def get_jwt_config(self) -> JWTConfiguration:
       from shared.jwt_config_builder import JWTConfigurationBuilder
       builder = JWTConfigurationBuilder(get_env(), "auth_service")
       return builder.build_complete_config()
   ```

2. **Backend Service Integration:**
   ```python
   # netra_backend/app/clients/auth_client_core.py - MODIFIED
   def _get_jwt_config(self) -> JWTConfiguration:
       from shared.jwt_config_builder import JWTConfigurationBuilder
       builder = JWTConfigurationBuilder(get_env(), "netra_backend") 
       return builder.build_complete_config()
   ```

3. **Secret Manager Integration:**
   ```python
   # Unified secret resolution through builder
   builder.register_secret_resolver(SecretManager())
   ```

### 2.4 Service Boundaries Respect Mechanism

**Independence Guarantees:**
1. **No Cross-Service Database Access:** Each service uses its own IsolatedEnvironment
2. **No Direct Service Communication:** Builder only accesses environment variables and secrets
3. **Service-Specific Customization:** `service_name` parameter allows service-specific logic
4. **Backward Compatibility:** Existing service interfaces remain unchanged

## 3. Definition of Done

### 3.1 Functional Requirements
- [ ] **All JWT configurations accessible through single builder**
  - Auth Service can get complete JWT config via builder
  - Backend Service can get JWT config for auth client
  - Service-to-service auth headers centralized
  
- [ ] **Service boundaries respected**
  - No auth_service imports in netra_backend (except shared/)
  - No database connections in builder
  - Each service maintains own IsolatedEnvironment usage
  
- [ ] **Environment-specific settings properly handled**
  - Development, staging, production configurations
  - Proper secret validation per environment
  - Environment override capabilities
  
- [ ] **Backward compatibility maintained**
  - Existing `AuthConfig` methods work unchanged
  - Current `SharedJWTConfig` functions preserved
  - No breaking changes to auth_client_core.py interface

### 3.2 Quality Requirements
- [ ] **Tests pass with new builder**
  - All existing JWT-related tests pass
  - New builder has comprehensive test coverage
  - Integration tests validate cross-service consistency
  
- [ ] **Performance maintained**
  - No degradation in JWT token generation/validation
  - Configuration loading time unchanged
  - Memory usage similar to current implementation

### 3.3 Documentation Requirements  
- [ ] **Migration guide created**
  - Step-by-step migration instructions
  - Rollback procedures documented
  - Breaking change impact analysis

## 4. Legacy Code Removal Plan

### 4.1 Phase 1: Core Migration
**Files to Modify (NOT remove):**
- `auth_service/auth_core/config.py`: Replace JWT config methods with builder calls
- `netra_backend/app/clients/auth_client_core.py`: Use builder for service auth headers
- `shared/jwt_config.py`: Deprecate functions, redirect to builder

**Functions to Consolidate:**
- `AuthConfig.get_jwt_secret()` → `builder.build_complete_config().secret_key`
- `AuthConfig.get_jwt_algorithm()` → `builder.build_token_config().algorithm`
- `SharedJWTConfig.get_jwt_config_dict()` → `builder.build_complete_config()`

### 4.2 Phase 2: Service Auth Headers  
**Target Files:**
- `netra_backend/app/clients/auth_client_core.py` (lines 79-85, 99-112)
  - Consolidate `_get_service_auth_headers()` and `_get_request_headers()`
  - Use builder for service credential management

### 4.3 Phase 3: Secret Resolution
**Consolidation Targets:**
- Multiple `get_jwt_secret_from_env()` implementations
- Service credential resolution logic scattered across files
- Environment-specific validation rules

**Legacy Functions to Remove After Migration:**
```python
# shared/jwt_config.py - After v2.0
def get_jwt_secret_key()  # DEPRECATED - use builder
def get_jwt_algorithm()   # DEPRECATED - use builder
def get_access_token_expire_minutes()  # DEPRECATED - use builder

# auth_service/auth_core/config.py - After v2.0 
def get_jwt_algorithm()   # DEPRECATED - use builder
def get_jwt_access_expiry_minutes()  # DEPRECATED - use builder
```

## 5. Implementation Strategy

### 5.1 Development Phases

**Phase 1 (Foundation):**
- Create `shared/jwt_config_builder.py` with core builder
- Implement basic JWT configuration structures
- Add comprehensive validation logic
- Create backward-compatibility shims

**Phase 2 (Service Integration):**
- Modify Auth Service to use builder internally
- Update Backend Service auth client to use builder
- Maintain all existing method signatures

**Phase 3 (Legacy Cleanup):**
- Mark legacy methods as deprecated
- Add migration warnings
- Plan removal timeline

### 5.2 Risk Mitigation

**Authentication Continuity:**
- Feature flags for gradual rollout
- Fallback to legacy config if builder fails
- Comprehensive integration testing

**Service Independence:**
- Strict interface contracts
- No shared state between services
- Environment isolation maintained

### 5.3 Testing Strategy

**Test Categories:**
- Unit tests for builder logic
- Integration tests for service compatibility
- E2E tests for authentication flows
- Performance regression tests

## 6. Configuration Unification Benefits

**Immediate Benefits:**
1. **Single Source of Truth:** One place to change JWT settings
2. **Consistent Validation:** Same rules across all services  
3. **Environment Parity:** Identical config behavior in all environments
4. **Easier Debugging:** Centralized configuration logging

**Long-term Benefits:**
1. **Reduced Maintenance:** No more config drift between services
2. **Faster Onboarding:** New developers find config in one place
3. **Better Security:** Centralized secret validation and rotation support
4. **Simplified Testing:** Mock configurations centrally managed

**Business Impact:**
- **Prevents Revenue Loss:** Eliminates JWT config mismatch failures
- **Improves Customer Experience:** More reliable authentication
- **Reduces Support Load:** Fewer authentication-related tickets
- **Enables Growth:** Solid foundation for multi-service expansion

---

**Next Steps:**
1. Review and approve architecture plan
2. Begin Phase 1 implementation
3. Create comprehensive test suite
4. Document migration procedures
5. Plan gradual rollout strategy

This architecture maintains the mature JWT authentication system while solving the specific configuration management problems through a centralized, service-boundary-respecting builder pattern.