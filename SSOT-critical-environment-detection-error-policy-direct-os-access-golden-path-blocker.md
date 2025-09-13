# SSOT-critical-environment-detection-error-policy-direct-os-access-golden-path-blocker

**GitHub Issue:** [#675](https://github.com/netra-systems/netra-apex/issues/675)
**Priority:** P0 - Critical/Blocking
**Status:** In Progress
**Created:** 2025-09-12

## Issue Summary
Critical SSOT violation in ErrorPolicy class with 15+ direct `os.getenv()` calls bypassing IsolatedEnvironment SSOT pattern. This blocks golden path by causing environment detection failures across all core services.

## Critical Files
- **Primary:** `netra_backend/app/core/exceptions/error_policy.py` (Lines 82-83, 116-123, 131-138, 146-156)
- **SSOT Target:** `dev_launcher/isolated_environment.py` (IsolatedEnvironment class)

## Golden Path Impact
- **Authentication Failures:** JWT secret mismatches due to wrong environment configuration
- **WebSocket Connection Issues:** Environment-dependent connection parameters fail
- **Database Connection Failures:** Wrong database URLs selected
- **Service Cascade Failures:** All environment-dependent configs affected

## Business Impact
- **Revenue Risk:** $500K+ ARR at risk due to authentication/service failures
- **User Experience:** Users cannot login → get AI responses (golden path broken)
- **System Reliability:** Foundation-level environment detection affects all services

## Progress Tracking

### ✅ Completed Steps
- [x] **Step 0.1:** SSOT Audit completed - Critical violation identified
- [x] **Step 0.2:** GitHub Issue #675 created
- [x] **Step 0.3:** IND tracking document created
- [x] **Step 1.1:** Test discovery completed - **CRITICAL FINDING: ZERO test coverage for ErrorPolicy**
- [x] **Step 1.2:** Test strategy planned - 45 new tests required

### 🔄 Current Step
- [ ] **Step 2:** Execute test plan for new SSOT tests (20% focus)

### 📋 Upcoming Steps
- [ ] **Step 3:** Plan SSOT remediation
- [ ] **Step 4:** Execute SSOT remediation plan
- [ ] **Step 5:** Test fix loop - prove system stability
- [ ] **Step 6:** Create PR and close issue

## Technical Details

### Current SSOT Violations
```python
# Lines 82-83: Environment detection
env_var = os.getenv('ENVIRONMENT', '').lower()
netra_env = os.getenv('NETRA_ENV', '').lower()

# Lines 116-122: Production detection
os.getenv('GCP_PROJECT', '').endswith('-prod')
'prod' in os.getenv('DATABASE_URL', '').lower()
'prod' in os.getenv('REDIS_URL', '').lower()
os.getenv('SERVICE_ENV') == 'production'

# Lines 131-137: Staging detection
os.getenv('GCP_PROJECT', '').endswith('-staging')
'staging' in os.getenv('DATABASE_URL', '').lower()
'staging' in os.getenv('REDIS_URL', '').lower()

# Lines 146-154: Testing detection
'pytest' in os.getenv('_', '').lower()
os.getenv('POSTGRES_PORT') in ['5434', '5433']
os.getenv('REDIS_PORT') in ['6381', '6380']
bool(os.getenv('CI'))
bool(os.getenv('TESTING'))
```

### Required SSOT Pattern
All environment access must go through `IsolatedEnvironment.get_env()` method instead of direct `os.getenv()` calls.

## Test Strategy

### 🚨 CRITICAL DISCOVERY: ZERO ErrorPolicy Test Coverage
**Finding:** ErrorPolicy class has **NO dedicated test coverage** despite being foundation for environment detection across ALL services.

### Test Categories Required (45 Total Tests)
1. **Unit Tests (20 tests)**: ErrorPolicy core functionality
   - Environment detection methods
   - Production/staging/testing environment identification
   - Edge cases and failure modes
   - SSOT compliance validation

2. **Integration Tests (15 tests)**: ErrorPolicy + IsolatedEnvironment
   - SSOT environment access patterns
   - Backward compatibility validation
   - Service integration scenarios
   - Configuration management integration

3. **E2E Tests (10 tests)**: Golden path validation
   - Complete user login → AI response flow
   - Staging environment validation
   - Authentication service integration
   - WebSocket connection validation

### Test Execution Strategy
- **No Docker Required**: Unit, integration (no Docker), E2E on staging GCP
- **Real Services**: Integration/E2E use real databases and services
- **SSOT Validation**: Tests verify all environment access through IsolatedEnvironment
- **Regression Prevention**: Existing mission critical tests continue to pass

### Success Criteria
- **100% Unit Coverage**: All ErrorPolicy public methods tested
- **Golden Path Validation**: Complete user flow works in staging
- **SSOT Compliance**: Zero os.getenv() calls remain
- **Regression Prevention**: All environment detection scenarios validated

## Remediation Plan
1. **Replace os.getenv() calls** with IsolatedEnvironment.get_env()
2. **Maintain existing logic** for environment detection
3. **Ensure backward compatibility** for all environment types
4. **Add comprehensive tests** for all environment scenarios
5. **Validate golden path** functionality after changes

## Success Criteria
- [ ] All 15+ `os.getenv()` calls replaced with IsolatedEnvironment access
- [ ] All existing tests continue to pass
- [ ] New SSOT compliance tests pass
- [ ] Golden path user flow works end-to-end
- [ ] Environment detection works correctly in dev/staging/production

## Notes
- **Foundation Impact:** ErrorPolicy is used by ALL core services
- **Cascade Effect:** Single class affects auth, database, WebSocket, config systems
- **Production Risk:** Environment misdetection could cause data corruption
- **SSOT Compliance:** Core violation of established SSOT principles

---
*Last Updated: 2025-09-12*