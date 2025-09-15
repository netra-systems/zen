# 🚨 TEST PLAN: Issue #1078 JWT SSOT Violations

## Executive Summary

This test plan creates **FAILING TESTS** to reproduce JWT SSOT violations identified in the analysis, focusing on:
1. **10 backend files with duplicate JWT implementations** 
2. **JWT secret access not restricted to auth service**
3. **Backend not using pure delegation to auth service**

**CRITICAL**: These tests are designed to **FAIL INITIALLY** to demonstrate current violations, then **PASS** after SSOT consolidation is implemented.

## Business Value Justification (BVJ)
- **Segment**: Platform/Enterprise (Security compliance)
- **Business Goal**: Eliminate security vulnerabilities and ensure HIPAA/SOC2/SEC compliance
- **Value Impact**: Prevents JWT secret mismatches causing 403 authentication failures
- **Revenue Impact**: Protects $500K+ ARR by ensuring reliable authentication system

---

## Test Strategy Overview

### Test Categories & Execution Methods
| Category | Test Count | Execution Method | Purpose |
|----------|------------|------------------|---------|
| **Unit Tests** | 8 tests | `python -m pytest tests/unit/auth/test_jwt_ssot_issue_1078.py -v` | Detect SSOT violations |
| **Integration Tests** | 6 tests | `python tests/unified_test_runner.py --category integration --test-pattern "*jwt*ssot*"` | Validate delegation patterns |
| **E2E Staging Tests** | 4 tests | `python tests/unified_test_runner.py --category e2e --staging` | End-to-end SSOT compliance |

### **NON-DOCKER COMPLIANCE**: All tests designed for unit, integration (non-docker), and staging GCP remote execution.

---

## 📋 Test File 1: Unit SSOT Violation Detection

**File**: `/tests/unit/auth/test_jwt_ssot_issue_1078_violations.py`

### Test Methods (All Should FAIL Initially)

#### 1. `test_detect_backend_jwt_direct_imports`
**Purpose**: Scan backend files for direct JWT library imports  
**Expected Initial State**: FAIL (violations exist)  
**Success Criteria**: No direct `import jwt`, `from jwt`, `import PyJWT` imports in backend

```python
def test_detect_backend_jwt_direct_imports(self):
    """FAILING TEST: Detect direct JWT imports in backend (Issue #1078)"""
    violations = self._scan_backend_files_for_patterns([
        "import jwt",
        "from jwt", 
        "import PyJWT",
        "from PyJWT"
    ])
    
    if violations:
        pytest.fail(f"JWT SSOT VIOLATION: Found {len(violations)} files with direct JWT imports")
    # This test should FAIL initially with current violations
```

#### 2. `test_detect_jwt_secret_direct_access`
**Purpose**: Find files directly accessing JWT secrets instead of using auth service  
**Expected Initial State**: FAIL (violations exist)  
**Success Criteria**: Only auth service accesses JWT_SECRET_KEY

```python
def test_detect_jwt_secret_direct_access(self):
    """FAILING TEST: Detect JWT secret access in backend (Issue #1078)"""
    secret_patterns = [
        "JWT_SECRET_KEY",
        "get_jwt_secret",
        "jwt_secret",
        "os.environ.*JWT_SECRET",
        "env.get.*JWT_SECRET"
    ]
    
    violations = self._scan_backend_files_for_patterns(secret_patterns)
    
    if violations:
        pytest.fail(f"JWT SECRET ACCESS VIOLATION: {len(violations)} files access JWT secrets directly")
```

#### 3. `test_detect_duplicate_jwt_validation_functions`
**Purpose**: Find multiple JWT validation function definitions  
**Expected Initial State**: FAIL (duplicates exist)  
**Success Criteria**: Only auth service has JWT validation functions

#### 4. `test_websocket_jwt_validation_uses_auth_service`
**Purpose**: Verify WebSocket JWT validation delegates to auth service  
**Expected Initial State**: FAIL (may have direct validation)  
**Success Criteria**: WebSocket uses `auth_client.validate_token_jwt()`

---

## 📋 Test File 2: Integration SSOT Compliance Validation

**File**: `/tests/integration/auth/test_jwt_ssot_issue_1078_integration.py`

### Test Methods (All Should FAIL Initially)

#### 1. `test_backend_auth_client_pure_delegation`
**Purpose**: Verify backend auth client only makes service calls, no direct JWT ops  
**Expected Initial State**: FAIL (may have direct JWT operations)  
**Success Criteria**: All JWT operations go through HTTP calls to auth service

```python
@pytest.mark.integration
async def test_backend_auth_client_pure_delegation(self, real_services_fixture):
    """FAILING TEST: Backend should use pure delegation to auth service"""
    
    # Mock HTTP requests to verify service calls
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value.json.return_value = {"valid": True, "payload": {"sub": "test"}}
        mock_post.return_value.status_code = 200
        
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        auth_client = AuthServiceClient()
        
        # Test token validation
        result = await auth_client.validate_token_jwt("test.jwt.token")
        
        # Verify HTTP call was made (not direct JWT operation)
        assert mock_post.called, "Should make HTTP call to auth service"
        
        # Verify no direct JWT library usage
        assert "jwt.decode" not in str(mock_post.call_args), "Should not use direct JWT operations"
```

#### 2. `test_websocket_user_context_extractor_ssot_compliance`
**Purpose**: Verify WebSocket JWT validation uses auth service  
**Expected Initial State**: FAIL (may have direct JWT decoding)  
**Success Criteria**: WebSocket JWT operations delegated to auth service

#### 3. `test_configuration_ssot_environment_access`
**Purpose**: Verify JWT configuration uses IsolatedEnvironment, not os.environ  
**Expected Initial State**: FAIL (may have direct environment access)  
**Success Criteria**: All JWT config through IsolatedEnvironment

---

## 📋 Test File 3: E2E Staging SSOT Validation

**File**: `/tests/e2e/auth/test_jwt_ssot_issue_1078_e2e_staging.py`

### Test Methods (All Should FAIL Initially)

#### 1. `test_end_to_end_jwt_flow_uses_auth_service`
**Purpose**: Validate complete JWT flow uses only auth service  
**Expected Initial State**: FAIL (may have mixed delegation)  
**Success Criteria**: End-to-end flow shows pure auth service delegation

```python
@pytest.mark.e2e
@pytest.mark.staging 
async def test_end_to_end_jwt_flow_uses_auth_service(self):
    """FAILING TEST: E2E JWT flow should use pure auth service delegation"""
    
    # Test with real staging auth service
    async with httpx.AsyncClient() as client:
        # Create test user token through auth service
        auth_response = await client.post(
            "https://auth.staging.netrasystems.ai/auth/login",
            json={"email": "test@example.com", "password": "test"}
        )
        token = auth_response.json().get("access_token")
        
        # Test WebSocket connection with JWT
        async with websockets.connect(
            "wss://api.staging.netrasystems.ai/ws",
            additional_headers={"Authorization": f"Bearer {token}"}
        ) as websocket:
            
            # Send test message
            await websocket.send(json.dumps({
                "type": "agent_request", 
                "message": "test"
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            # Verify successful authentication (proves SSOT compliance)
            assert data.get("type") != "auth_error", "JWT validation should succeed with auth service"
```

#### 2. `test_websocket_authentication_staging_consistency`
**Purpose**: Verify WebSocket auth works consistently with staging auth service  
**Expected Initial State**: FAIL (may have inconsistencies)  
**Success Criteria**: Consistent authentication behavior

---

## 📋 Test File 4: Performance & Security Validation

**File**: `/tests/integration/auth/test_jwt_ssot_issue_1078_performance.py`

### Test Methods

#### 1. `test_auth_service_jwt_performance_requirements`
**Purpose**: Verify SSOT JWT operations meet performance requirements  
**Expected Initial State**: FAIL (may be slow due to duplication)  
**Success Criteria**: <50ms token creation, <10ms validation

#### 2. `test_jwt_secret_synchronization_validation`
**Purpose**: Verify JWT secrets are synchronized across services  
**Expected Initial State**: FAIL (may have mismatches)  
**Success Criteria**: Consistent JWT secret usage

---

## 🚀 Test Execution Plan

### Phase 1: Violation Detection (Should FAIL)
```bash
# Run violation detection tests (expected to FAIL)
python -m pytest tests/unit/auth/test_jwt_ssot_issue_1078_violations.py -v
python -m pytest tests/integration/auth/test_jwt_ssot_issue_1078_integration.py -v

# Expected: All tests FAIL, proving violations exist
```

### Phase 2: Integration Testing (Should FAIL)
```bash
# Run integration tests with real services
python tests/unified_test_runner.py --category integration --test-pattern "*jwt*ssot*1078*" --real-services

# Expected: Tests FAIL due to incomplete delegation
```

### Phase 3: E2E Staging Validation (Should FAIL)
```bash
# Run E2E tests on staging GCP
python tests/unified_test_runner.py --category e2e --staging --test-pattern "*jwt*ssot*1078*"

# Expected: Tests FAIL due to JWT inconsistencies
```

### Phase 4: Post-Remediation Validation (Should PASS)
```bash
# After SSOT consolidation implementation
python -m pytest tests/unit/auth/test_jwt_ssot_issue_1078_violations.py -v
# Expected: All tests PASS, proving SSOT compliance
```

---

## 🎯 Success Criteria Definition

### SSOT Compliance Achieved When:

1. **No Direct JWT Imports**: Backend contains no `import jwt` or `from jwt` statements
2. **Pure Delegation**: All JWT operations in backend go through `auth_client.validate_token_jwt()`
3. **Secret Access Restricted**: Only auth service accesses `JWT_SECRET_KEY`
4. **Single Implementation**: Only auth service has JWT validation functions
5. **Configuration SSOT**: JWT config uses `IsolatedEnvironment`, not `os.environ`
6. **Performance Standards**: Token operations meet <50ms creation, <10ms validation
7. **E2E Consistency**: Staging tests pass with consistent auth behavior

### Validation Metrics:
- **Unit Tests**: 8/8 passing (100% SSOT compliance)
- **Integration Tests**: 6/6 passing (100% delegation verified) 
- **E2E Tests**: 4/4 passing (100% end-to-end consistency)
- **Performance**: <50ms token ops, <10ms validation
- **Security**: Zero JWT secret leakage outside auth service

---

## 📝 Implementation Guide

### Test File Structure:
```
tests/
├── unit/auth/
│   └── test_jwt_ssot_issue_1078_violations.py      # Violation detection
├── integration/auth/
│   ├── test_jwt_ssot_issue_1078_integration.py    # Delegation validation
│   └── test_jwt_ssot_issue_1078_performance.py    # Performance testing
└── e2e/auth/
    └── test_jwt_ssot_issue_1078_e2e_staging.py    # End-to-end validation
```

### Test Base Classes:
- Unit: `SSotBaseTestCase` from `test_framework.ssot.base_test_case`
- Integration: `BaseIntegrationTest` with `real_services_fixture`
- E2E: `BaseE2ETest` with staging environment configuration

### Execution Commands:
- **Quick Validation**: `python -m pytest tests/unit/auth/test_jwt_ssot_issue_1078_violations.py`
- **Full Integration**: `python tests/unified_test_runner.py --test-pattern "*1078*"`
- **Staging E2E**: `python tests/unified_test_runner.py --category e2e --staging --test-pattern "*1078*"`

---

## 🔍 Expected Violations to Detect

Based on the analysis, these tests will identify:

1. **Configuration Files**: JWT secret access in backend config schemas
2. **WebSocket Components**: Direct JWT validation in user context extraction
3. **Client Code**: Mixed delegation patterns in auth client
4. **Middleware**: JWT secret access in auth middleware
5. **Dependencies**: Direct environment access for JWT configuration

**CRITICAL**: These failing tests will prove the need for SSOT consolidation and guide the remediation implementation.

---

*Test Plan Created: 2025-09-15*  
*Issue: #1078 JWT SSOT Violations*  
*Execution: Non-Docker (Unit/Integration/Staging E2E)*  
*Status: Ready for Implementation*