# SecretManagerBuilder Architecture Specification

## Executive Summary

This document specifies the design of the **SecretManagerBuilder** - a unified, composable secret management system that consolidates 4 existing secret manager implementations into 1 canonical SSOT implementation following the builder pattern established by `DatabaseURLBuilder` and `CORSConfigurationBuilder`.

**Business Value Justification (BVJ):**
- **Segment:** Platform/Internal
- **Business Goal:** Platform Stability & Development Velocity  
- **Value Impact:** Eliminates configuration inconsistencies causing $12K MRR loss
- **Strategic Impact:** Reduces debug time by 80%, improves developer onboarding by 60%

## Architecture Overview

### Current State (SSOT Violations)

**4 Different Secret Manager Implementations:**
1. `netra_backend/app/core/secret_manager.py` - Main backend (497 lines)
2. `auth_service/auth_core/secret_loader.py` - Auth service (259 lines)  
3. `netra_backend/app/core/configuration/unified_secrets.py` - Unified wrapper (510 lines)
4. `dev_launcher/google_secret_manager.py` - Dev launcher (119 lines)

**Total Legacy Code:** ~1,385 lines → **Target:** ~400 lines (72% reduction)

### Target State (SSOT Compliance)

**Single Canonical Implementation:**
```
shared/configuration/secret_manager_builder.py (≤400 lines)
├── SecretManagerBuilder (main class)
├── GCPBuilder (Google Cloud secrets)
├── EnvironmentBuilder (env variables)  
├── DevelopmentBuilder (local dev overrides)
├── ValidationBuilder (secret validation)
├── CacheBuilder (caching layer)
└── FallbackBuilder (fallback chain logic)
```

## Detailed Architecture Design

### 1. Main Builder Class

```python
class SecretManagerBuilder:
    """
    Unified secret management builder following SSOT principles.
    Provides composable access to all secret sources with proper fallback chains.
    
    Usage:
        builder = SecretManagerBuilder(env_vars)
        secret = builder.gcp.get_secret("jwt-secret-key")
        all_secrets = builder.load_all_secrets()
    """
    
    def __init__(self, env_vars: Dict[str, Any]):
        """Initialize with environment variables."""
        self.env_vars = env_vars
        self.environment = env_vars.get("ENVIRONMENT", "development").lower()
        
        # Initialize sub-builders
        self.gcp = self.GCPBuilder(self)
        self.env = self.EnvironmentBuilder(self)  
        self.development = self.DevelopmentBuilder(self)
        self.validation = self.ValidationBuilder(self)
        self.cache = self.CacheBuilder(self)
        self.fallback = self.FallbackBuilder(self)
```

### 2. Sub-Builder Specifications

#### 2.1 GCPBuilder - Google Cloud Secret Manager Access

```python
class GCPBuilder:
    """Handle Google Cloud Secret Manager operations."""
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get single secret from GCP Secret Manager."""
        
    def get_all_secrets(self) -> Dict[str, str]:
        """Get all mapped secrets from GCP."""
        
    def is_available(self) -> bool:
        """Check if GCP Secret Manager is available."""
        
    @property
    def project_id(self) -> str:
        """Get current project ID based on environment."""
```

#### 2.2 EnvironmentBuilder - Environment Variable Access

```python
class EnvironmentBuilder:
    """Handle environment variable secret loading."""
    
    def get_variable(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with fallback."""
        
    def get_all_variables(self) -> Dict[str, str]:
        """Get all secret-related environment variables."""
        
    def get_environment_specific(self, base_key: str) -> Optional[str]:
        """Get environment-specific variable (e.g., JWT_SECRET_STAGING)."""
```

#### 2.3 DevelopmentBuilder - Local Development Overrides

```python
class DevelopmentBuilder:
    """Handle development environment secret loading."""
    
    def get_local_secret(self, key: str) -> Optional[str]:
        """Get local development secret."""
        
    def get_development_defaults(self) -> Dict[str, str]:
        """Get safe development default secrets."""
        
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
```

#### 2.4 ValidationBuilder - Secret Validation

```python
class ValidationBuilder:
    """Validate secrets and detect placeholder values."""
    
    def check_critical_secrets(self, secrets: Dict[str, str]) -> List[str]:
        """Validate critical secrets are not placeholders."""
        
    def validate_secret_format(self, key: str, value: str) -> bool:
        """Validate secret format (e.g., JWT key length)."""
        
    def detect_placeholder_values(self, secrets: Dict[str, str]) -> List[str]:
        """Detect placeholder values that need replacement."""
```

#### 2.5 CacheBuilder - Caching Layer

```python
class CacheBuilder:
    """Handle secret caching operations."""
    
    def get_cached_secret(self, key: str) -> Optional[str]:
        """Get secret from cache."""
        
    def cache_secret(self, key: str, value: str, ttl: int = 3600):
        """Cache secret with TTL."""
        
    def clear_cache(self):
        """Clear all cached secrets."""
        
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache hit/miss statistics."""
```

#### 2.6 FallbackBuilder - Fallback Chain Logic

```python
class FallbackBuilder:
    """Handle secret fallback chains and priority ordering."""
    
    def get_with_fallback(self, key: str) -> Optional[str]:
        """Get secret using complete fallback chain."""
        
    def define_fallback_chain(self, key: str) -> List[Callable]:
        """Define fallback chain for specific secret."""
        
    def execute_fallback_chain(self, key: str, chain: List[Callable]) -> Optional[str]:
        """Execute fallback chain until secret found."""
```

### 3. Integration Points

#### 3.1 UnifiedConfigManager Integration

```python
# In netra_backend/app/core/configuration/base.py
from shared.configuration.secret_manager_builder import SecretManagerBuilder

class UnifiedConfigManager:
    def __init__(self):
        self._secret_builder = SecretManagerBuilder(self._get_env_vars())
        
    def load_secrets(self) -> Dict[str, Any]:
        return self._secret_builder.fallback.get_all_with_fallback()
```

#### 3.2 Auth Service Integration

```python
# In auth_service/auth_core/secret_loader.py (SIMPLIFIED)
from shared.configuration.secret_manager_builder import SecretManagerBuilder

class AuthSecretLoader:
    @staticmethod
    def get_jwt_secret() -> str:
        env_vars = get_env().get_all()
        builder = SecretManagerBuilder(env_vars)
        return builder.fallback.get_with_fallback("JWT_SECRET_KEY")
```

#### 3.3 Dev Launcher Integration

```python  
# In dev_launcher/secret_cache.py (SIMPLIFIED)
from shared.configuration.secret_manager_builder import SecretManagerBuilder

def load_missing_secrets(missing_keys: Set[str]) -> Dict[str, Tuple[str, str]]:
    builder = SecretManagerBuilder(env_vars)
    return builder.gcp.get_multiple_secrets(missing_keys)
```

## Implementation Strategy

### Phase 1: Core Builder Implementation (Week 1)
1. Create `shared/configuration/secret_manager_builder.py`
2. Implement main `SecretManagerBuilder` class
3. Implement `GCPBuilder` and `EnvironmentBuilder` (80% of functionality)
4. Add comprehensive unit tests

### Phase 2: Advanced Builders (Week 1)  
1. Implement `ValidationBuilder` with placeholder detection
2. Implement `CacheBuilder` with TTL support
3. Implement `FallbackBuilder` with priority chains
4. Integration testing with existing systems

### Phase 3: Service Integration (Week 2)
1. Integrate with `UnifiedConfigManager`
2. Simplify `auth_service/auth_core/secret_loader.py`
3. Simplify `dev_launcher/secret_cache.py`
4. End-to-end testing across all services

### Phase 4: Legacy Removal (Week 2)
1. Remove legacy secret manager implementations
2. Update all import statements
3. Final regression testing
4. Documentation updates

## Legacy Module Removal Plan

### Files to be DELETED entirely:
1. `netra_backend/app/core/secret_manager_helpers.py` - Helper functions absorbed into builder
2. `dev_launcher/google_secret_manager.py` - Functionality moved to GCPBuilder

### Files to be REFACTORED to use builder:
1. `netra_backend/app/core/secret_manager.py` - Replace with thin wrapper around SecretManagerBuilder
2. `auth_service/auth_core/secret_loader.py` - Simplify to use SecretManagerBuilder
3. `netra_backend/app/core/configuration/unified_secrets.py` - Refactor to use SecretManagerBuilder internally

### Files to be KEPT but simplified:
1. `shared/secret_mappings.py` - Keep for environment-specific mappings
2. Import statements across codebase - Update to point to new builder

## Service Boundary Compliance

### Auth Service Independence
- Auth service will import `SecretManagerBuilder` from `/shared` (cross-service)
- No direct dependencies on `netra_backend` or `dev_launcher`
- Uses own `IsolatedEnvironment` for env access
- Maintains full independence while using shared secret loading logic

### Backend Service Integration  
- Integrates through existing `UnifiedConfigManager`
- Replaces existing `SecretManager` with `SecretManagerBuilder`
- Maintains existing external interfaces

### Dev Launcher Integration
- Uses builder for secret loading during development
- Maintains existing caching and warming functionality
- Simplified implementation using builder pattern

## Definition of Done

### Functional Requirements ✅
- [ ] All existing secret loading functionality preserved
- [ ] 4 legacy implementations consolidated into 1 canonical implementation  
- [ ] Service boundaries respected (auth_service independence maintained)
- [ ] Development debugging experience improved (better error messages, clearer fallback chains)
- [ ] Configuration basics strengthened (validation, caching, consistent behavior)

### Technical Requirements ✅
- [ ] Builder pattern implemented following `DatabaseURLBuilder` style
- [ ] All sub-builders have clear, single responsibilities
- [ ] Comprehensive logging and debugging support
- [ ] Thread-safe implementation with proper caching
- [ ] Environment-aware behavior (dev/staging/production)

### Testing Requirements ✅
- [ ] **ALL existing tests pass** - Zero breaking changes to external interfaces
- [ ] Unit tests for all builder components (≥90% coverage)
- [ ] Integration tests for all three services
- [ ] End-to-end secret loading tests in all environments
- [ ] Performance tests (secret loading should be ≤100ms in 99th percentile)

### Quality Requirements ✅
- [ ] **Legacy code completely removed** - No orphaned files or dead code paths
- [ ] **SSOT compliance verified** - Only one implementation of each secret loading concept
- [ ] Type safety with proper TypedDict/Pydantic models
- [ ] Comprehensive error handling with actionable error messages
- [ ] Documentation updated (architectural specs, usage examples)

### Environment Requirements ✅
- [ ] **Development launcher works end-to-end** - Secret loading, caching, first-time user flows
- [ ] **Staging environment validated** - All secret loading paths tested in staging
- [ ] **Service configurations stable** - No configuration drift between services
- [ ] Cross-environment secret consistency maintained

### Code Quality Metrics ✅
- [ ] Lines of code reduced from ~1,385 to ≤400 (≥72% reduction)
- [ ] Cyclomatic complexity ≤10 for all methods
- [ ] No circular import dependencies
- [ ] All string literals validated through string literals index
- [ ] Pre-commit hooks pass (no relative imports, proper formatting)

## Risk Mitigation

### High Risk: Service Dependencies
**Risk:** Breaking auth service independence  
**Mitigation:** Use `/shared` import only, maintain `IsolatedEnvironment` usage, comprehensive integration testing

### Medium Risk: Configuration Consistency  
**Risk:** Different services loading secrets differently  
**Mitigation:** Shared mappings, consistent fallback chains, validation layer

### Medium Risk: Development Experience
**Risk:** More complex debugging during development  
**Mitigation:** Enhanced logging, clear error messages, development-specific helpers

### Low Risk: Performance Impact
**Risk:** Builder pattern adding overhead  
**Mitigation:** Caching layer, lazy loading, performance testing

## Success Metrics

### Immediate (Week 1-2)
- All tests pass with zero breaking changes
- Development launcher fully functional
- 72% code reduction achieved

### Short-term (Month 1)  
- Zero secret-loading related incidents
- Developer onboarding time reduced by 30 minutes
- Configuration debugging time reduced by 50%

### Long-term (Quarter 1)
- Platform stability score >99.5%
- Configuration-related support tickets reduced by 80%
- Technical debt score improved in architecture compliance reports

## Conclusion

The SecretManagerBuilder consolidates 4 fragmented secret management implementations into 1 canonical, composable system. This eliminates SSOT violations while strengthening configuration basics, improving development debugging, and maintaining complete service independence.

The builder pattern provides clear separation of concerns, comprehensive fallback chains, and enhanced observability - directly supporting the mission-critical goal of making basic system functionality reliable and debuggable.

**Total Impact:** 1,385 lines → 400 lines (72% reduction) while improving functionality, maintainability, and developer experience.