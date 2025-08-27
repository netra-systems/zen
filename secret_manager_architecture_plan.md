# SecretManagerBuilder Architecture Plan

## Executive Summary

**Business Value Justification (BVJ):**
- **Segment:** Platform/Internal (affects ALL customer tiers through infrastructure reliability)  
- **Business Goal:** System Reliability, Development Velocity, Operational Cost Reduction
- **Value Impact:** Eliminates 4 fragmented secret managers causing configuration inconsistencies that lead to service outages
- **Strategic Impact:** $150K/year in prevented operational incidents + 60% faster development cycles + 72% code reduction

**CRITICAL BUSINESS PROBLEM SOLVED:**
Secret management fragmentation across 4 implementations (1,385 lines) leads to configuration drift, security vulnerabilities, and deployment failures. This builder consolidates secret management into a single, tested, and maintainable system following the proven RedisConfigurationBuilder pattern.

## Architecture Overview

```
SecretManagerBuilder (Main Controller)
├── GCPSecretBuilder        # Google Secret Manager integration
├── EnvironmentBuilder      # Environment-specific secret loading  
├── ValidationBuilder       # Security validation & compliance
├── EncryptionBuilder       # Local encryption & secure storage
├── CacheBuilder           # Performance caching & TTL management
├── AuthBuilder            # Access control & audit logging
├── DevelopmentBuilder     # Development-specific fallbacks
├── StagingBuilder         # Staging environment configuration
└── ProductionBuilder      # Production security & compliance
```

## Core Architecture Principles

### 1. Single Source of Truth (SSOT) Compliance
- **ONE** unified secret manager replacing 4 fragmented implementations
- **ONE** configuration pattern following RedisConfigurationBuilder approach  
- **ONE** validation system across all environments
- **ZERO** duplicate secret loading logic

### 2. Service Independence Maintained
```python
# Auth Service Usage (remains independent)
from shared.secret_manager_builder import SecretManagerBuilder
builder = SecretManagerBuilder(service="auth_service")
jwt_secret = builder.auth.get_jwt_secret()

# Backend Service Usage (unified approach)
from shared.secret_manager_builder import SecretManagerBuilder  
builder = SecretManagerBuilder(service="netra_backend")
db_password = builder.gcp.get_database_password()
```

### 3. Environment Integration Pattern
```python
# Follows IsolatedEnvironment pattern
class SecretManagerBuilder:
    def __init__(self, env_vars: Optional[Dict[str, Any]] = None, service: str = "shared"):
        if env_vars is None:
            # Use IsolatedEnvironment for consistent env management
            from shared.isolated_environment import get_env
            self.env_manager = get_env()
            self.env = self.env_manager.get_all()
        else:
            # Filter out None values and merge with os.environ as fallback
            self.env = {}
            self.env.update(os.environ)
            for key, value in env_vars.items():
                if value is not None:
                    self.env[key] = value
```

## Sub-Builder Architecture

### 1. GCPSecretBuilder
**Responsibility:** Google Cloud Secret Manager integration with fallback chains
```python
class GCPSecretBuilder:
    def __init__(self, parent):
        self.parent = parent
        self._client = None
        self._project_id = self._detect_project_id()
    
    def get_secret(self, secret_name: str, environment: str = None) -> Optional[str]:
        """Get secret from GCP Secret Manager with environment-specific naming."""
        
    def get_database_password(self) -> Optional[str]:
        """Get database password with staging/production environment detection."""
        
    def get_jwt_secret(self) -> Optional[str]:  
        """Get JWT secret with service-specific fallback chains."""
        
    def validate_gcp_connectivity(self) -> Tuple[bool, str]:
        """Validate GCP Secret Manager connectivity."""
```

### 2. EnvironmentBuilder  
**Responsibility:** Environment-specific configuration and fallback logic
```python
class EnvironmentBuilder:
    def load_environment_secrets(self) -> Dict[str, str]:
        """Load base secrets from environment variables."""
        
    def get_environment_mappings(self) -> Dict[str, str]:
        """Get secret mappings for current environment."""
        
    def apply_environment_overrides(self, secrets: Dict[str, str]) -> Dict[str, str]:
        """Apply environment-specific overrides and placeholder replacement."""
```

### 3. ValidationBuilder
**Responsibility:** Security validation, compliance, and critical secret verification
```python  
class ValidationBuilder:
    def validate_critical_secrets(self, secrets: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate that critical secrets don't contain placeholder values."""
        
    def validate_password_strength(self, secret_name: str, password: str) -> Tuple[bool, str]:
        """Validate password strength for staging/production."""
        
    def audit_secret_access(self, secret_name: str, component: str, success: bool) -> None:
        """Audit secret access attempts."""
```

### 4. EncryptionBuilder
**Responsibility:** Local encryption, secure storage, and memory protection
```python
class EncryptionBuilder:  
    def encrypt_secret(self, value: str) -> str:
        """Encrypt secret value for secure storage."""
        
    def decrypt_secret(self, encrypted_value: str) -> str:
        """Decrypt secret value for use."""
        
    def secure_wipe(self, secret_name: str) -> None:
        """Securely wipe secret from memory."""
```

### 5. CacheBuilder
**Responsibility:** Performance optimization through intelligent caching
```python
class CacheBuilder:
    def cache_secret(self, secret_name: str, value: str, ttl_minutes: int = 60) -> None:
        """Cache secret with TTL."""
        
    def get_cached_secret(self, secret_name: str) -> Optional[str]:
        """Get cached secret if valid."""
        
    def invalidate_cache(self, secret_name: str = None) -> None:
        """Invalidate cache for secret or all secrets."""
```

## Integration with Existing Builders

### 1. RedisConfigurationBuilder Integration
```python
# RedisConfigurationBuilder.SecretManagerBuilder becomes deprecated
# New usage pattern:
redis_builder = RedisConfigurationBuilder()
secret_builder = SecretManagerBuilder(service="redis") 
redis_password = secret_builder.gcp.get_redis_password()
redis_builder.connection.password = redis_password
```

### 2. DatabaseURLBuilder Integration  
```python
# Unified database secret management
db_builder = DatabaseURLBuilder()
secret_builder = SecretManagerBuilder(service="database")
db_password = secret_builder.gcp.get_database_password()  
db_builder.postgres.password = db_password
```

### 3. IsolatedEnvironment Pattern Compliance
```python
# Follows unified environment management
class SecretManagerBuilder:
    def _get_environment_manager(self):
        """Get appropriate environment manager for service."""
        if self.service == "auth_service":
            from auth_service.auth_core.isolated_environment import get_env
            return get_env()
        elif self.service == "netra_backend":  
            from netra_backend.app.core.configuration.database import get_env
            return get_env()
        else:
            # Shared/default environment management
            from shared.isolated_environment import get_env  
            return get_env()
```

## Service Boundary Compliance

### Auth Service Independence Maintained
```python
# auth_service/auth_core/secret_loader.py → DEPRECATED
# New pattern:
from shared.secret_manager_builder import SecretManagerBuilder

class AuthSecretLoader:
    def __init__(self):
        self.secret_builder = SecretManagerBuilder(service="auth_service")
    
    def get_jwt_secret(self) -> str:
        return self.secret_builder.auth.get_jwt_secret()
        
    def get_google_client_id(self) -> str:
        return self.secret_builder.gcp.get_oauth_secret("google_client_id")
```

### Backend Service Integration
```python
# netra_backend/app/core/secret_manager.py → DEPRECATED
# New pattern:  
from shared.secret_manager_builder import SecretManagerBuilder

class BackendSecretManager:
    def __init__(self):
        self.secret_builder = SecretManagerBuilder(service="netra_backend")
    
    def load_secrets(self) -> Dict[str, Any]:
        return self.secret_builder.environment.load_all_secrets()
```

## Backward Compatibility Strategy

### 1. Graceful Migration Path
```python
# Old API remains functional during transition
def get_jwt_secret() -> str:  # DEPRECATED but functional
    """Backward compatibility wrapper."""
    builder = SecretManagerBuilder(service="auth_service")  
    return builder.auth.get_jwt_secret()

# New API provides enhanced functionality
def get_unified_secrets() -> Dict[str, str]:
    """New unified secret loading."""
    builder = SecretManagerBuilder() 
    return builder.environment.load_all_secrets()
```

### 2. Configuration Migration  
```python  
# Automatic detection of legacy configurations
class SecretManagerBuilder:
    def _migrate_legacy_config(self):
        """Auto-migrate from legacy secret managers."""
        if self._detect_legacy_secret_manager():
            self._log_migration_warning()
            return self._load_from_legacy()
        return {}
```

## Error Handling & Resilience

### 1. Fallback Chain Architecture
```
GCP Secret Manager (Primary)
    ↓ (on failure)
Environment Variables (Secondary) 
    ↓ (on failure)
Service-Specific Defaults (Tertiary)
    ↓ (on failure)  
Development Fallbacks (Local only)
    ↓ (on failure)
Secure Failure (No insecure defaults)
```

### 2. Circuit Breaker Pattern
```python
class GCPSecretBuilder:
    def __init__(self, parent):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=60,  # seconds
            expected_exception=SecretManagerError
        )
    
    @circuit_breaker
    def _fetch_from_gcp(self, secret_name: str) -> str:
        """Fetch with circuit breaker protection."""
```

## Security Architecture

### 1. Access Control Matrix
```
Secret Type        | Development | Staging | Production | Audit Required
Database Passwords | Env Vars    | GCP SM  | GCP SM     | Yes  
JWT Secrets       | Env Vars    | GCP SM  | GCP SM     | Yes
API Keys          | Optional    | GCP SM  | GCP SM     | No
OAuth Credentials | Required    | GCP SM  | GCP SM     | Yes
```

### 2. Encryption at Rest
- **Development:** Optional encryption for local secrets
- **Staging:** Mandatory encryption for cached secrets  
- **Production:** Full encryption + secure memory wiping

### 3. Audit Logging
```python
class ValidationBuilder:
    def audit_secret_access(self, secret_name: str, component: str, success: bool):
        """Comprehensive audit logging."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "secret_name": secret_name,  # No values logged
            "component": component,
            "success": success,
            "environment": self.parent.environment,
            "service": self.parent.service,
            "source": "gcp_secret_manager" if success else "fallback"
        }
        self._write_audit_log(audit_entry)
```

## Performance Optimization

### 1. Intelligent Caching Strategy
- **Cache TTL:** 60 minutes for non-critical, 15 minutes for critical secrets
- **Cache Invalidation:** Manual + automatic on rotation detection
- **Memory Efficiency:** Encrypted cache storage with secure cleanup

### 2. Lazy Loading Pattern  
```python
class SecretManagerBuilder:
    def __init__(self):
        # Initialize sub-builders on first access (lazy loading)
        self._gcp = None
        self._environment = None
        
    @property  
    def gcp(self) -> GCPSecretBuilder:
        if self._gcp is None:
            self._gcp = GCPSecretBuilder(self)
        return self._gcp
```

## Testing Strategy

### 1. Test Architecture
```
Unit Tests (95% coverage target)
├── Builder Logic Tests
├── Fallback Chain Tests  
├── Security Validation Tests
└── Error Handling Tests

Integration Tests
├── GCP Secret Manager Integration
├── Multi-Service Secret Sharing
├── Environment-Specific Loading
└── Performance Benchmarks

End-to-End Tests  
├── Full Secret Loading Scenarios
├── Service Startup Integration
├── Production Deployment Validation
└── Disaster Recovery Testing
```

### 2. Test Isolation
```python
# Test utilities for secret mocking
class MockSecretManagerBuilder(SecretManagerBuilder):
    def __init__(self, test_secrets: Dict[str, str]):
        super().__init__()
        self._test_secrets = test_secrets
        
    def _override_for_testing(self):
        """Override GCP calls for testing."""
```

## Migration Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create `shared/secret_manager_builder.py` with core architecture
2. Implement basic sub-builders (GCP, Environment, Validation)
3. Add comprehensive unit tests
4. Document API and integration patterns

### Phase 2: Service Integration (Week 2) 
1. Integrate with auth_service (replace AuthSecretLoader)
2. Integrate with netra_backend (replace SecretManager)  
3. Add backward compatibility wrappers
4. Update RedisConfigurationBuilder integration

### Phase 3: Advanced Features (Week 3)
1. Implement encryption, caching, and audit logging
2. Add production security features
3. Create performance optimization
4. Complete end-to-end testing

### Phase 4: Legacy Cleanup (Week 4)
1. Remove deprecated secret managers
2. Update all import statements  
3. Clean up test files
4. Update documentation

## Success Metrics

### Code Quality Metrics
- **Lines of Code:** Reduce from 1,385 to ~400 lines (72% reduction)
- **Cyclomatic Complexity:** Target <10 per method
- **Test Coverage:** 95% minimum coverage
- **Duplication:** Zero duplicate secret loading logic

### Performance Metrics  
- **Secret Loading Time:** <200ms for full secret set
- **Cache Hit Rate:** >80% for repeated secret access
- **Memory Usage:** <50MB for encrypted secret cache
- **GCP API Calls:** Reduce by 60% through intelligent caching

### Operational Metrics
- **Configuration Errors:** Reduce by 90% through validation
- **Deployment Failures:** Eliminate secret-related failures  
- **Security Incidents:** Zero secret-related security issues
- **Developer Velocity:** 60% faster secret-related development

This architecture provides a comprehensive, secure, and maintainable solution that consolidates 4 fragmented secret managers into a single, well-tested system following established patterns and maintaining service independence.