# Critical Database Connection Failures - Golden Path Audit Loop
## Date: 2025-09-09
## Issue Priority: CRITICAL ERROR

### Issue Selected:
**Critical Database Connection Failures in Staging Golden Path**

### Log Evidence:
- ERROR: Service dependency validation FAILED - 2 services failed, critical business functionality at risk
- database_postgres: Failed - Database connection failed: Textual SQL expression 'SELECT 1 as test_value' should be explicitly declared as text('SELECT 1 as test_value')
- database_redis: Failed - Redis connection failed: RedisManager.set() got an unexpected keyword argument 'expire_seconds'
- Phase phase_1_core validation failed for services: ['database_postgres', 'database_redis']

### Business Impact:
This directly blocks the Golden Path user flow as database connectivity is fundamental to all user operations.

## Five Whys Analysis Results:

**WHY 1:** Two specific API incompatibility errors: SQLAlchemy requires `text()` wrapper for raw SQL, Redis API changed `expire_seconds` to `ex`
**WHY 2:** Recent dependencies upgrade to SQLAlchemy 2.0.43+ and Redis 6.4.0+ with stricter API requirements
**WHY 3:** System lacks comprehensive dependency regression testing and staging/dev environment drift
**WHY 4:** Codebase violates SSOT principles - multiple scattered database operations instead of centralized patterns
**WHY 5:** Insufficient adherence to documented SSOT architecture combined with inadequate regression testing

**ROOT CAUSE:** Systematic violation of SSOT principles for database operations with legacy API usage incompatible with upgraded dependencies.

**KEY FILES AFFECTED:**
- `netra_backend/app/core/service_dependencies/health_check_validator.py:126`
- `netra_backend/tests/integration/test_factory_initialization_integration.py:185`
- 30+ files using legacy `"SELECT 1 as test_value"` pattern
- Multiple Redis operations using `expire_seconds` instead of `ex`

## Test Plan Created:

**4 Test Suites Designed:**
1. **Immediate Bug Reproduction** - `tests/integration/database/test_staging_api_compatibility.py`
2. **SSOT Database Operations** - `tests/integration/database/test_database_operations_ssot.py`  
3. **Golden Path E2E Database** - `tests/e2e/staging/test_golden_path_database_flow.py`
4. **Dependency Regression Prevention** - `tests/integration/dependencies/test_api_compatibility_regression.py`

**Key Test Requirements:**
- Tests must fail initially to prove bug detection
- Real database connections only (no mocks)
- E2E tests require authentication via `test_framework/ssot/e2e_auth_helper.py`
- Integration with unified_test_runner.py and Docker services

## Status Log:
### Step 0 - COMPLETED: Log analysis and issue identification
### Step 1 - COMPLETED: Five Whys Analysis (sub-agent completed)  
### Step 2 - COMPLETED: Test Plan Creation (comprehensive 4-suite plan created)
### Step 2.1 - COMPLETED: GitHub Issue Integration
**GitHub Issue Created:** https://github.com/netra-systems/netra-apex/issues/122
**Labels:** claude-code-generated-issue, bug

### Step 3 - IN PROGRESS: Execute Test Plan (spawning sub-agent)
