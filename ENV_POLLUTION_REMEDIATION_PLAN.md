# Environment Pollution Remediation Plan
Generated: 2025-08-30

## Overview
This plan addresses the critical environment pollution issues identified in the audit, prioritizing security and stability.

## Phase 1: Critical Security Fixes (Immediate - Day 1)

### 1.1 Remove Test Auth Bypasses from Production Code
**File**: `netra_backend/app/websocket_core/auth.py`
**Actions**:
```python
# Create separate test-only auth handler
# Move all test bypass logic to tests/helpers/auth_test_helper.py
# Production code should NEVER check for TESTING, E2E_TESTING, or AUTH_FAST_TEST_MODE
```

### 1.2 Add Startup Environment Validation
**File**: Create `netra_backend/app/core/environment_validator.py`
**Actions**:
```python
def validate_environment_at_startup():
    """Fail fast if test variables detected in production."""
    environment = os.getenv('ENVIRONMENT', '').lower()
    
    if environment in ['staging', 'production']:
        forbidden_vars = [
            'TESTING', 'E2E_TESTING', 'AUTH_FAST_TEST_MODE',
            'PYTEST_CURRENT_TEST', 'ALLOW_DEV_AUTH_BYPASS',
            'WEBSOCKET_AUTH_BYPASS'
        ]
        
        violations = [var for var in forbidden_vars if os.getenv(var)]
        if violations:
            raise EnvironmentError(
                f"CRITICAL: Test variables detected in {environment}: {violations}"
            )
```

### 1.3 Emergency Staging Config Fix
**File**: `.env.staging`
**Actions**:
- Replace all localhost references with proper staging URLs
- Add clear warnings about template nature
- Create `.env.staging.example` as safe template

## Phase 2: Environment Isolation (Days 2-5)

### 2.1 Create Environment Boundary Service
**File**: `netra_backend/app/core/environment_boundary.py`
```python
class EnvironmentBoundary:
    """Enforces strict environment separation."""
    
    ALLOWED_VARS = {
        'development': {...},  # All vars allowed
        'testing': {...},      # Test-specific vars
        'staging': {...},      # Staging-only vars
        'production': {...}    # Production-only vars
    }
    
    def validate_configuration(self):
        """Validate all env vars against allowlist."""
        pass
```

### 2.2 Remove Pytest Detection from Runtime
**Files**: 
- `netra_backend/app/startup_module.py`
- All files with `'pytest' in sys.modules` checks

**Actions**:
- Replace pytest detection with explicit test mode flag
- Use dependency injection for test vs production services
- Create test-specific startup path

### 2.3 Implement Configuration Profiles
**File**: `netra_backend/app/core/config_profiles.py`
```python
class ConfigProfile:
    """Environment-specific configuration profiles."""
    
    @staticmethod
    def load_profile(environment: str):
        """Load configuration for specific environment."""
        profiles = {
            'development': DevelopmentProfile(),
            'testing': TestingProfile(),
            'staging': StagingProfile(),
            'production': ProductionProfile()
        }
        return profiles[environment]
```

## Phase 3: Configuration Hardening (Days 6-10)

### 3.1 Secure Configuration Loading
**File**: Update `netra_backend/app/core/isolated_environment.py`
```python
def _auto_load_env_file(self) -> None:
    """Load env file with strict validation."""
    environment = self._get_validated_environment()
    
    if environment in ['staging', 'production']:
        # NEVER load .env files in staging/production
        if Path('.env').exists():
            raise EnvironmentError(
                f".env file detected in {environment} - this is forbidden"
            )
        return
```

### 3.2 Database Connection Validation
**File**: `netra_backend/app/db/clickhouse_base.py`
```python
def _validate_connection_for_environment(self):
    """Ensure connection parameters match environment."""
    environment = self._get_validated_environment()
    
    if environment in ['staging', 'production']:
        if 'localhost' in self.host or '127.0.0.1' in self.host:
            raise ValueError(
                f"Localhost connection attempted in {environment}"
            )
```

### 3.3 Create Configuration Validator Script
**File**: `scripts/validate_environment_config.py`
```python
def validate_all_environments():
    """Validate configuration files for all environments."""
    # Check for localhost in staging/production configs
    # Verify no test flags in production configs
    # Ensure secrets are not hardcoded
    pass
```

## Phase 4: Testing Infrastructure Separation (Days 11-15)

### 4.1 Create Test-Only Auth System
**File**: `tests/infrastructure/test_auth_system.py`
```python
class TestAuthenticationSystem:
    """Completely separate auth system for tests."""
    # No shared code with production auth
    # Clear test-only implementation
```

### 4.2 Implement Feature Flags
**File**: `netra_backend/app/core/feature_flags.py`
```python
class FeatureFlags:
    """Replace environment checks with feature flags."""
    
    def is_enabled(self, feature: str) -> bool:
        """Check if feature is enabled for environment."""
        # No more if TESTING or if pytest checks
        pass
```

### 4.3 Build-Time Code Separation
**Actions**:
- Create separate build pipelines for test vs production
- Use conditional compilation or imports
- Ensure test code never ships to production

## Implementation Schedule

| Week | Phase | Priority | Risk if Delayed |
|------|-------|----------|-----------------|
| Day 1 | Phase 1 | CRITICAL | Security breach |
| Days 2-5 | Phase 2 | HIGH | Operational failures |
| Days 6-10 | Phase 3 | MEDIUM | Configuration errors |
| Days 11-15 | Phase 4 | LOW | Technical debt |

## Success Metrics

1. **Zero test flags in production** - Automated check at startup
2. **No localhost in staging** - Configuration validator passes
3. **Clean environment separation** - Audit script shows no violations
4. **Auth bypass eliminated** - Security scan passes
5. **Pytest detection removed** - No runtime module checks

## Testing Plan

### Unit Tests
- Test environment validator with various configurations
- Test configuration profiles for each environment
- Test auth system without bypass logic

### Integration Tests
- Test startup fails with wrong environment vars
- Test services reject localhost in staging
- Test auth properly enforces in all environments

### E2E Tests
- Separate E2E test infrastructure
- No shared auth bypass with production
- Clear test vs production boundaries

## Rollback Plan

If issues arise during implementation:
1. Keep old code paths with deprecation warnings
2. Use feature flags to gradually migrate
3. Monitor for any auth or connection failures
4. Have emergency revert procedure ready

## Monitoring and Alerts

### Add Monitoring For:
1. Test environment variables in production
2. Localhost connection attempts in staging
3. Auth bypass activation in non-test environments
4. Configuration mismatches at startup

### Alert Thresholds:
- CRITICAL: Any test flag in production
- HIGH: Localhost in staging config
- MEDIUM: Missing required environment vars
- LOW: Deprecated code path usage

## Documentation Updates

1. Update environment setup documentation
2. Create environment configuration guide
3. Document test infrastructure separation
4. Add troubleshooting for common issues

## Validation Checklist

Before considering remediation complete:

- [ ] All test auth bypasses removed from production code
- [ ] Startup validation prevents test flags in production
- [ ] No localhost references in staging configurations
- [ ] Pytest detection eliminated from runtime code
- [ ] Environment boundaries enforced via allowlists
- [ ] Configuration profiles implemented for each environment
- [ ] Test infrastructure completely separated
- [ ] Monitoring and alerts configured
- [ ] Documentation updated
- [ ] All tests passing in clean environments

## Risk Mitigation

1. **Gradual Rollout**: Implement changes incrementally
2. **Feature Flags**: Use flags to control new behavior
3. **Extensive Testing**: Test each phase thoroughly
4. **Monitoring**: Watch for unexpected behaviors
5. **Communication**: Keep team informed of changes

## Next Steps

1. Get approval for remediation plan
2. Create JIRA tickets for each phase
3. Assign Phase 1 for immediate implementation
4. Schedule Phase 2-4 based on sprint capacity
5. Set up monitoring before deployment
6. Plan gradual rollout strategy