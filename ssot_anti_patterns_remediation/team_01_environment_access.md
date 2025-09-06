# Team 1: Environment Access SSOT Migration

## COPY THIS ENTIRE PROMPT:

You are an Environment Architecture Expert implementing SSOT migration for all environment variable access.

🚨 **ULTRA CRITICAL FIRST ACTION** - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users
5. Update tests to SSOT methods - NEVER recreate legacy code to pass old tests
6. Config regression prevention - See OAuth Regression Analysis

## MANDATORY READING BEFORE STARTING:
1. **CLAUDE.md** (entire document, especially section 46-52 on Config SSOT)
2. **SSOT_ANTI_PATTERNS_ANALYSIS.md** (Anti-Pattern #1: Environment Access)
3. **OAuth Regression Analysis** (./OAUTH_REGRESSION_ANALYSIS_20250905.md)
4. **Config Regression Prevention Plan** (./CONFIG_REGRESSION_PREVENTION_PLAN.md)
5. **SPEC/unified_environment_management.xml**
6. **shared/isolated_environment.py** (current SSOT implementation)
7. **MISSION_CRITICAL_NAMED_VALUES_INDEX.xml**

## YOUR SPECIFIC MISSION:

### Current Anti-Pattern (30+ files affected):
```python
# VIOLATION - Direct os.environ access
os.environ["ENVIRONMENT"] = "staging"
os.environ["SECRET_KEY"] = "test_key"
database_url = os.environ.get("DATABASE_URL")
```

### Target SSOT Pattern:
```python
# CORRECT - IsolatedEnvironment usage
from shared.isolated_environment import IsolatedEnvironment

class ServiceConfig:
    def __init__(self):
        self.env = IsolatedEnvironment()
        
    def get_database_url(self):
        # Validated, isolated access with proper error handling
        return self.env.get_env("DATABASE_URL", required=True)
```

## FILES TO MIGRATE (Priority Order):

### Phase 1: Critical Path Files (Hours 0-4)
1. **start_backend_lite.py:66-119** - Backend startup environment
2. **test_staging_infrastructure_fixes.py:23-30** - Staging test configs
3. **prove_loguru_fix.py:19-20** - Logging configuration
4. **standalone_test/test_agent_components.py:24** - Test isolation

### Phase 2: Service Configurations (Hours 4-8)
5. **netra_backend/app/core/managers/unified_configuration_manager.py**
6. **auth_service/core/config.py** (if exists)
7. **frontend/config/*.js** (environment loaders)
8. All files matching pattern: `**/config*.py`

### Phase 3: Test Files (Hours 8-12)
9. All test files with direct os.environ access
10. Test fixtures and setup files
11. Docker test configurations

### Phase 4: Scripts & Utilities (Hours 12-16)
12. **scripts/deploy_to_gcp.py**
13. **scripts/check_config_before_deploy.py**
14. **database_scripts/run_migrations.py**
15. Any remaining utility scripts

## CRITICAL REQUIREMENTS:

### 1. Environment Isolation
- **NEVER** access os.environ directly
- **ALWAYS** use IsolatedEnvironment class
- **ENFORCE** validation on all critical values
- **IMPLEMENT** proper error messages for missing configs

### 2. Multi-Environment Support
```python
# Each environment MUST have independent config
class EnvironmentConfig:
    CONFIGS = {
        Environment.TEST: {
            "DATABASE_URL": "postgresql://test@localhost:5434/test",
            "REDIS_URL": "redis://localhost:6381",
        },
        Environment.STAGING: {
            "DATABASE_URL": get_env("STAGING_DATABASE_URL"),
            "REDIS_URL": get_env("STAGING_REDIS_URL"),
        },
        Environment.PRODUCTION: {
            "DATABASE_URL": get_env("PROD_DATABASE_URL"),
            "REDIS_URL": get_env("PROD_REDIS_URL"),
        }
    }
```

### 3. Configuration Validation
- Check against MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
- Validate OAuth credentials per environment
- Ensure JWT secrets are environment-specific
- No fallbacks to wrong environment configs

### 4. Test Isolation
```python
# Tests MUST use isolated environments
@pytest.fixture
def isolated_env():
    env = IsolatedEnvironment()
    env.set_for_testing("TEST_VAR", "test_value")
    yield env
    env.cleanup()  # Restore original state
```

## MIGRATION PROCESS (Per File):

### Step 1: Audit Current Usage
```bash
# Find all os.environ usage in file
grep -n "os\.environ" filename.py
grep -n "environ\[" filename.py
grep -n "getenv" filename.py
```

### Step 2: Identify Critical Values
- Cross-reference with MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
- Check if value causes cascade failures
- Document in migration report

### Step 3: Implement IsolatedEnvironment
```python
# Before (VIOLATION)
import os
secret_key = os.environ.get("SECRET_KEY", "default")

# After (CORRECT)
from shared.isolated_environment import IsolatedEnvironment
env = IsolatedEnvironment()
secret_key = env.get_env("SECRET_KEY", required=True)
```

### Step 4: Add Validation
```python
# Add validation for critical values
if env.current_environment == Environment.PRODUCTION:
    env.validate_required([
        "DATABASE_URL",
        "REDIS_URL", 
        "JWT_SECRET_PRODUCTION",
        "OAUTH_CLIENT_ID",
        "OAUTH_CLIENT_SECRET"
    ])
```

### Step 5: Update Tests
- Migrate test environment setup to use IsolatedEnvironment
- Remove any direct os.environ manipulation
- Add cleanup in teardown

## VALIDATION CHECKLIST:

### Pre-Migration Validation:
- [ ] Run `grep -r "os\.environ" .` to find all violations
- [ ] Document current environment variables in use
- [ ] Check for environment variable conflicts
- [ ] Identify test contamination risks

### Post-Migration Validation:
- [ ] Zero direct os.environ access (except in IsolatedEnvironment itself)
- [ ] All tests use IsolatedEnvironment fixtures
- [ ] No cross-environment config leaks
- [ ] WebSocket events still flowing
- [ ] OAuth flows work in all environments
- [ ] Database connections stable
- [ ] Redis connections stable

### Integration Testing:
```bash
# Run with real services
python tests/unified_test_runner.py --real-services --env test

# Test each environment
python tests/unified_test_runner.py --env staging
python tests/unified_test_runner.py --env production --dry-run
```

## ROLLBACK PLAN:

### If Migration Fails:
1. **Immediate**: Revert to previous commit
2. **Diagnosis**: Check logs for validation failures
3. **Fix Forward**: Address specific validation issues
4. **Gradual Rollout**: Migrate service by service

### Emergency Procedures:
```python
# Emergency fallback (ONLY if critical failure)
class EmergencyEnvironment:
    def get_env(self, key, default=None, required=False):
        try:
            return IsolatedEnvironment().get_env(key, default, required)
        except Exception as e:
            logger.critical(f"IsolatedEnvironment failed: {e}")
            # ONLY as last resort
            return os.environ.get(key, default)
```

## SUCCESS METRICS:

### Quantitative:
- **0** direct os.environ calls (down from 30+)
- **100%** test isolation (no cross-contamination)
- **0** environment config leaks
- **<50ms** config lookup latency

### Qualitative:
- Clean separation between environments
- No OAuth credential confusion
- Clear error messages for missing configs
- Audit trail for all config access

## DELIVERABLES:

1. **Migration Report**: Document all changes made
2. **Validation Script**: Automated check for violations
3. **Test Suite**: Comprehensive environment tests
4. **Rollback Procedure**: Step-by-step rollback plan
5. **Performance Metrics**: Before/after comparison

## COMMON PITFALLS TO AVOID:

1. **Silent Fallbacks**: NEVER silently fall back to defaults
2. **Test Contamination**: Always cleanup test environments
3. **Async Issues**: Consider race conditions in config loading
4. **Docker Environments**: Ensure Docker compose uses IsolatedEnvironment
5. **Script Bypass**: Don't forget deployment/utility scripts

## FINAL REMINDERS:

- **THINK DEEPLY**: Our lives depend on proper environment isolation
- **95% FIRST**: Get basic cases working before edge cases
- **DELETE LEGACY**: Remove old patterns completely
- **TEST REAL**: Use real services, not mocks
- **LOUD ERRORS**: Make failures obvious, not silent

**YOU HAVE 16 HOURS TO COMPLETE THIS MISSION. The security of our entire platform depends on eliminating these environment access violations. ULTRA THINK DEEPLY ALWAYS.**