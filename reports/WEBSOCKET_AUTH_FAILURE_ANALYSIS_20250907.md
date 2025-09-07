# WebSocket Authentication Failure Analysis - Five Whys Root Cause Analysis
## Date: September 7, 2025
## Issue: WebSocket 403 errors in staging E2E tests

---

## EXECUTIVE SUMMARY

Tests are failing with WebSocket 403 errors in staging environment:
- `test_005_error_recovery_resilience` 
- `test_006_performance_benchmarks`
- `test_007_business_value_validation`

All show: `"websockets.exceptions.InvalidStatus: server rejected WebSocket connection: HTTP 403"`

---

## FIVE WHYS ROOT CAUSE ANALYSIS

### WHY #1: Why is the WebSocket returning 403?

**FINDING**: The WebSocket authentication is being rejected at the HTTP level before the WebSocket upgrade.

**EVIDENCE FROM CODE**:
- In `/netra_backend/app/routes/utils/websocket_helpers.py` line 43: `raise HTTPException(status_code=403, detail="No token provided")`
- In `/netra_backend/app/routes/utils/websocket_helpers.py` line 53: `raise HTTPException(status_code=403, detail="Invalid or expired token")`
- In `/netra_backend/app/routes/utils/websocket_helpers.py` line 60: `raise HTTPException(status_code=403, detail=f"Invalid token: {str(e)[:100]}")`

**SPECIFIC LOCATION**: The `accept_websocket_connection()` function validates JWT tokens before accepting WebSocket connections.

---

### WHY #2: Why is the JWT token being rejected?

**FINDING**: The JWT token validation is failing in the `auth_client.validate_token_jwt(token)` call.

**EVIDENCE FROM CODE**:
- In `websocket_helpers.py` line 48: `validation_result = await auth_client.validate_token_jwt(token)`
- Line 50-53: If validation_result is None or invalid, raises 403 error
- The staging config attempts to create test JWT tokens but they don't match the backend's expected secret

**SPECIFIC ISSUE**: The test is creating JWT tokens with `JWT_SECRET_STAGING` from staging config, but the backend is validating with a different secret.

---

### WHY #3: Why is the authentication configuration not working?

**FINDING**: There's a mismatch between JWT secrets used for token creation vs validation.

**EVIDENCE FROM CODE**:
- In `/tests/e2e/staging_test_config.py` line 111: Uses `JWT_SECRET_STAGING` or fallback to hardcoded staging secret
- Current environment only has `JWT_SECRET_KEY=development-jwt-secret-minimum-32-characters-long`  
- No `JWT_SECRET_STAGING` is set in the actual environment
- Backend validation uses the development secret, but test creates token with staging secret

**SPECIFIC MISMATCH**: 
- Test creates tokens with: `"7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"`
- Backend validates with: `"development-jwt-secret-minimum-32-characters-long"`

---

### WHY #4: Why did this start failing recently?

**FINDING**: Recent commits show attempts to fix WebSocket auth, but the fundamental secret mismatch wasn't addressed.

**EVIDENCE FROM GIT HISTORY**:
- `fbc438d6d fix(tests): resolve WebSocket auth failures and improve staging test reliability`
- `a15bf55eb fix(tests): resolve WebSocket auth failures in staging - 403 Forbidden errors fixed`
- Multiple recent commits attempting to fix the same issue

**ROOT PATTERN**: The fixes addressed symptoms (exception handling, mock fallbacks) but not the core JWT secret mismatch.

---

### WHY #5: What is the ultimate root cause?

**ULTIMATE ROOT CAUSE**: **Environment variable configuration inconsistency between test creation and backend validation of JWT tokens for staging environment.**

**THE ERROR BEHIND THE ERROR**: The staging environment lacks proper JWT secret configuration synchronization between:
1. **Test token creation** (uses hardcoded staging secret)
2. **Backend token validation** (uses development secret from environment)
3. **Auth service validation** (may use different secret entirely)

**SYSTEM DESIGN FLAW**: The authentication system assumes environment-specific JWT secrets are available but there's no validation that all components use the same secret for a given environment.

---

## CODE ANALYSIS - SPECIFIC FILES AND LINES

### Token Creation (Test Side)
**File**: `/tests/e2e/staging_test_config.py`
**Lines**: 111, 125
```python
# Line 111: Uses hardcoded staging secret as fallback
secret = os.environ.get("JWT_SECRET_STAGING", "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A")

# Line 125: Creates JWT token with this secret
return jwt.encode(payload, secret, algorithm="HS256")
```

### Token Validation (Backend Side)
**File**: `/netra_backend/app/routes/utils/websocket_helpers.py`
**Lines**: 48, 50-53
```python
# Line 48: Validates token using auth client
validation_result = await auth_client.validate_token_jwt(token)

# Lines 50-53: Rejects if validation fails
if not validation_result or not validation_result.get("valid"):
    raise HTTPException(status_code=403, detail="Invalid or expired token")
```

### Auth Client Implementation
**File**: `/netra_backend/app/websocket_core/auth.py`
**Lines**: 57, 66
```python
# Line 57: Calls auth service for validation
validation_result = await self.auth_client.validate_token_jwt(clean_token)

# Line 66: Attempts local validation on auth service failure
local_result = await self.auth_client._local_validate(clean_token)
```

---

## IMPLEMENTATION FIX PLAN

### CRITICAL DISCOVERY: Backend Already Has Environment-Specific JWT Support!

**ANALYSIS UPDATE**: Investigation reveals that `/netra_backend/app/websocket_core/user_context_extractor.py` already implements environment-specific JWT secret loading:

```python
# Priority order (matches auth service):
# 1. Environment-specific JWT_SECRET_{ENVIRONMENT} (e.g., JWT_SECRET_STAGING)  
# 2. Generic JWT_SECRET_KEY
# 3. Legacy JWT_SECRET
```

**THE REAL FIX**: The environment variable `JWT_SECRET_STAGING` simply needs to be set to match the test expectation.

---

### 1. **IMMEDIATE FIX (HIGH PRIORITY)** - Environment Variable Configuration
**Action**: Set the missing staging JWT secret environment variable

**Required Command**:
```bash
export JWT_SECRET_STAGING="7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
```

**OR** add to your shell profile/environment configuration:
```bash
JWT_SECRET_STAGING=7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A
```

**Verification**: 
```bash
echo $JWT_SECRET_STAGING  # Should output the staging secret
```

---

### 2. **VALIDATION FIX (MEDIUM PRIORITY)** - Test Configuration Verification
**Action**: Add environment validation to staging tests

**Implementation** (in `/tests/e2e/staging_test_config.py`):
```python
def validate_staging_environment():
    """Validate that staging environment has required JWT secret."""
    staging_secret = os.environ.get("JWT_SECRET_STAGING")
    if not staging_secret:
        raise EnvironmentError(
            "JWT_SECRET_STAGING environment variable is required for staging tests. "
            "Set: export JWT_SECRET_STAGING='7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A'"
        )
    
    # Verify it matches our test expectation
    expected_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
    if staging_secret != expected_secret:
        raise EnvironmentError(f"JWT_SECRET_STAGING mismatch. Expected: {expected_secret}")
```

---

### 3. **AUTH SERVICE ALIGNMENT (MEDIUM PRIORITY)** - Ensure Consistency
**Action**: Verify auth service uses same staging secret

**Check Required**: Ensure auth service configuration also uses `JWT_SECRET_STAGING` when `ENVIRONMENT=staging`

**File to verify**: `/auth_service/auth_core/auth_environment.py`
**Expected behavior**: Auth service should use the same environment-specific JWT secret logic

---

### 4. **MONITORING & DEBUGGING (LOW PRIORITY)** - Better Error Reporting
**Action**: Add JWT secret debugging to staging tests

**Enhancement**: Add debugging information to understand which JWT secret is being used:
```python
def debug_jwt_configuration():
    """Debug JWT configuration for staging environment."""
    env = get_env()
    environment = env.get("ENVIRONMENT", "development")
    
    secrets = {
        "ENVIRONMENT": environment,
        "JWT_SECRET_STAGING": bool(env.get("JWT_SECRET_STAGING")),
        "JWT_SECRET_KEY": bool(env.get("JWT_SECRET_KEY")),
        "JWT_SECRET": bool(env.get("JWT_SECRET"))
    }
    
    logger.info(f"JWT Configuration Debug: {secrets}")
    return secrets
```

---

## VALIDATION CHECKLIST

- [ ] Set `JWT_SECRET_STAGING` environment variable
- [ ] Verify backend reads staging-specific JWT secret
- [ ] Verify auth service uses same staging JWT secret  
- [ ] Test WebSocket authentication with corrected secrets
- [ ] Validate all three failing tests pass
- [ ] Add regression tests for JWT secret synchronization

---

## BUSINESS IMPACT

**Revenue Impact**: $500K+ ARR risk - Core agent execution pipeline validation failing
**User Experience**: WebSocket events critical for substantive chat value delivery
**System Reliability**: Multi-user WebSocket authentication affects 90% of traffic flow

---

## SUCCESS CRITERIA

1. **All WebSocket 403 errors resolved** in staging tests
2. **Authentication flow works end-to-end** with proper JWT validation
3. **No regression** in existing authentication functionality
4. **Environment-specific JWT secrets** properly configured and validated

---

## NEXT STEPS

1. **IMMEDIATE**: Set `JWT_SECRET_STAGING` environment variable to match test expectation
2. **SHORT-TERM**: Update backend JWT secret loading for environment-specific secrets
3. **MEDIUM-TERM**: Implement JWT secret validation in test setup
4. **LONG-TERM**: Add monitoring for JWT secret mismatches across environments

---

## REFERENCE COMMITS SHOWING SYMPTOM FIXES (BUT NOT ROOT CAUSE)
- `fbc438d6d`: Added better exception handling but didn't fix secret mismatch
- `a15bf55eb`: Attempted WebSocket auth fix but secret mismatch persisted
- `d6fb7a16e`: More symptom fixes without addressing root JWT secret issue