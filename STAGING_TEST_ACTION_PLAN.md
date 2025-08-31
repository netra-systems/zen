# Staging Test Infrastructure Action Plan

## Executive Summary
The staging infrastructure is operational (all services returning 200 OK), but the test suite cannot execute due to configuration and environment issues. This action plan addresses the root causes to enable comprehensive E2E testing against staging.

## Current Status

### ✅ Working
- API Health: 200 OK (https://api.staging.netrasystems.ai/health)
- Auth Service: 200 OK (https://auth.staging.netrasystems.ai/health)
- Frontend: 200 OK (https://app.staging.netrasystems.ai)

### ❌ Issues
1. **Unified Test Runner**: Failed due to missing Redis password configuration for staging environment
2. **Direct Test Execution**: Module import issues due to Python path configuration
3. **Pytest with Environment**: Tests skip even when `ENVIRONMENT=staging` is set
4. **OAuth Simulation**: Missing `E2E_OAUTH_SIMULATION_KEY` for test authentication

## Action Plan

### 1. Environment Configuration Issues
**Problem**: Redis password missing for staging environment
```
ConfigurationError: CONFIGURATION_ERROR: Password is required for staging environment
```

**Actions**:
- [ ] Create `.env.staging` file with proper Redis credentials
- [ ] Update configuration manager to load staging-specific environment variables
- [ ] Ensure GCP secrets are accessible for staging environment
- [ ] Add Redis password to staging configuration

### 2. Python Module Path Issues
**Problem**: Tests can't import `netra_backend` modules
```
ModuleNotFoundError: No module named 'netra_backend'
```

**Actions**:
- [ ] Add PYTHONPATH export to test runner scripts
- [ ] Update `pytest.ini` with proper python paths
- [ ] Create wrapper script that sets up environment before running tests
- [ ] Fix absolute imports in test files

### 3. Test Framework Updates
**Problem**: Tests skip when `ENVIRONMENT=staging` is set
```
SKIPPED [1] tests\e2e\test_staging_e2e_comprehensive.py:74: These tests only run against staging environment (set ENVIRONMENT=staging)
```

**Actions**:
- [ ] Fix environment variable detection in test decorators
- [ ] Update `conftest.py` to properly handle staging environment
- [ ] Ensure test fixtures work with staging configuration
- [ ] Review pytest mark conditions

### 4. Missing E2E Bypass Key
**Problem**: OAuth simulation requires `E2E_OAUTH_SIMULATION_KEY`
```python
if not os.getenv("E2E_OAUTH_SIMULATION_KEY"):
    print("ERROR: E2E_OAUTH_SIMULATION_KEY environment variable not set")
```

**Actions**:
- [ ] Document the bypass key requirement
- [ ] Add key to staging environment variables
- [ ] Update test documentation with setup instructions
- [ ] Create secure key management process

### 5. Automated Test Runner
**Actions**:
- [ ] Create `run_staging_tests.py` script that:
  - Sets all required environment variables
  - Configures Python path
  - Handles Windows/Unix differences
  - Provides clear error messages
  - Runs tests in correct order

**Script Template**:
```python
import os
import sys
import subprocess

# Set environment
os.environ["ENVIRONMENT"] = "staging"
os.environ["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
os.environ["E2E_OAUTH_SIMULATION_KEY"] = "your-bypass-key"

# Run tests
subprocess.run([sys.executable, "-m", "pytest", "tests/e2e", "-v"])
```

### 6. WebSocket Testing
**Problem**: WebSocket tests need proper authentication and event tracking

**Actions**:
- [ ] Ensure WebSocket client handles staging auth tokens
- [ ] Add retry logic for WebSocket connections
- [ ] Implement proper event tracking for validation
- [ ] Test WebSocket message flow end-to-end

### 7. Comprehensive Validation
**Actions**:
- [ ] Create staging health check dashboard
- [ ] Add monitoring for test execution
- [ ] Set up alerts for staging test failures
- [ ] Document all staging test requirements

### 8. Quick Fixes Needed
**Immediate Actions**:
- [ ] Set `ENVIRONMENT=staging` in test scripts
- [ ] Add `E2E_OAUTH_SIMULATION_KEY` to environment
- [ ] Fix Unicode encoding issues in test output (Windows)
- [ ] Update import paths in test files

## Priority Order

1. **Immediate** (Today)
   - Fix environment variables
   - Add E2E_OAUTH_SIMULATION_KEY
   - Set PYTHONPATH

2. **High** (This Week)
   - Create test runner script
   - Fix Python paths
   - Update Redis configuration

3. **Medium** (Next Sprint)
   - Update test framework
   - Add WebSocket validation
   - Create monitoring dashboard

4. **Low** (Backlog)
   - Add comprehensive monitoring
   - Document best practices
   - Create CI/CD integration

## Success Criteria
- [ ] All staging services pass health checks
- [ ] Test suite runs without import errors
- [ ] WebSocket tests validate agent events
- [ ] OAuth simulation works with bypass key
- [ ] Comprehensive E2E tests pass >90%

## Test Commands

### Quick Health Check
```bash
curl -s https://api.staging.netrasystems.ai/health | jq .
curl -s https://auth.staging.netrasystems.ai/health | jq .
```

### Run Staging Tests
```bash
# Windows
set ENVIRONMENT=staging
set E2E_OAUTH_SIMULATION_KEY=your-key
set PYTHONPATH=%CD%
python -m pytest tests/e2e/test_staging_e2e_comprehensive.py -v

# Unix/Linux
export ENVIRONMENT=staging
export E2E_OAUTH_SIMULATION_KEY=your-key
export PYTHONPATH=$(pwd)
python -m pytest tests/e2e/test_staging_e2e_comprehensive.py -v
```

### Mission Critical Tests
```bash
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Notes
- The staging infrastructure itself is healthy and responding
- Main blocker is test configuration, not the actual services
- OAuth simulation is for testing only, does not bypass real authentication
- All tests should use real services, no mocks for staging/production

## Next Steps
1. Implement quick fixes for environment variables
2. Create automated test runner script
3. Run comprehensive test suite
4. Document results and iterate

---
*Generated: 2025-08-31*
*Status: Action Required*
*Owner: Platform Team*