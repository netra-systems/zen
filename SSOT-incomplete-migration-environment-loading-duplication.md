# SSOT-incomplete-migration-environment-loading-duplication

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/189
**Progress Tracker:** SSOT-incomplete-migration-environment-loading-duplication.md
**Status:** Step 0 Complete - Issue Created

## Critical SSOT Violation Discovered

**Problem:** Environment loading patterns duplicated across backend and auth service causing staging configuration failures that prevent users from logging in and getting AI responses.

## Key Files Affected
- `netra_backend/app/main.py:22-98` - Backend environment loading
- `auth_service/main.py:30-52` - Auth service environment loading  
- `netra_backend/app/core/lifespan_manager.py` - Backend startup management
- Various staging configuration files

## SSOT Violations Identified
1. **Environment Loading Duplication**: Each service has different logic for loading .env files and detecting staging environment
2. **Staging Detection Inconsistency**: Different staging environment detection patterns
3. **Startup Sequence Duplication**: Different lifespan management approaches
4. **Configuration Source Inconsistency**: Services may use different config sources in staging

## Business Impact
- JWT secret mismatches between services
- Database connection inconsistencies
- Authentication failures due to credential inconsistencies
- Staging deployment reliability issues
- **Directly blocks $500K+ ARR chat functionality**

## Proposed SSOT Solution
Create unified shared modules:
- `/shared/startup_environment_manager.py` - Centralized environment loading
- `/shared/service_startup_coordinator.py` - Unified service startup coordination
- `/shared/staging_configuration.py` - Staging-specific configuration management

## Step 1.1 COMPLETE: Existing Tests Discovered

### Critical Existing Tests Found:
**MUST PASS after SSOT refactor:**

1. **auth_service/tests/test_environment_loading.py** - GOLDEN STANDARD
   - `test_main_loads_env_before_imports()` - Critical environment loading validation
   - `test_jwt_secret_required_in_production()` - Production environment JWT validation
   - `test_isolated_environment_integration()` - AuthEnvironment integration

2. **netra_backend/tests/startup/test_comprehensive_startup.py**
   - Complete startup validation suite including environment, auth, database, Redis

3. **tests/integration/golden_path/test_configuration_environment_comprehensive.py**
   - `TestIsolatedEnvironmentManagement` - Environment variable precedence testing
   - Cross-environment configuration validation

### Test Gaps Identified:
- **Cross-Service Environment Loading Consistency** - No tests validate identical logic across services
- **Staging Detection Race Conditions** - No tests for consistent staging detection
- **SSOT Environment Manager Integration** - No tests for unified environment manager

### Pre-Refactor Test Commands:
```bash
python -m pytest auth_service/tests/test_environment_loading.py -v
python -m pytest netra_backend/tests/startup/test_comprehensive_startup.py -v
python -m pytest tests/integration/golden_path/test_configuration_environment_comprehensive.py::TestIsolatedEnvironmentManagement -v
```

## Process Progress
- [x] Step 0: Discover Next SSOT Issue (SSOT AUDIT) - COMPLETE
- [x] Step 1.1: Discover Existing Tests - COMPLETE
- [ ] Step 1.2: Plan New Tests  
- [ ] Step 2: Execute Test Plan  
- [ ] Step 3: Plan Remediation
- [ ] Step 4: Execute Remediation
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## Next Actions
1. ✅ Discover existing tests protecting startup/staging functionality - COMPLETE
2. Plan new tests to validate SSOT refactor - IN PROGRESS
3. Execute test plan
4. Plan and execute SSOT remediation
5. Validate all tests pass
6. Create PR for closure