# Comprehensive Test Plan: WebSocket Authentication Protocol Mismatch

**Issue:** WebSocket authentication failures in staging causing message routing cascade failures  
**Root Cause:** Frontend using `['jwt-auth', 'jwt.token']` protocol array instead of expected `jwt.${token}` format  
**Impact:** Golden Path user flow broken ($500K+ ARR chat functionality)  
**GitHub Issue:** #171  

## Executive Summary

This test plan provides comprehensive validation for WebSocket authentication protocol mismatch issues that are breaking the critical Golden Path user flow in staging environments. The tests are specifically designed to **FAIL initially** to prove they catch the real issue, then **PASS** after fixes are applied.

### Key Testing Strategy
- **Test-Driven Bug Fix:** Tests fail first, proving they detect the issue
- **Real Service Integration:** No mocks for critical authentication flows
- **Staging Environment Focus:** Validate actual GCP Cloud Run conditions
- **Cascade Failure Coverage:** Test both auth failure AND message routing impacts
- **Multi-User Concurrency:** Verify isolation between concurrent users

---

## 1. UNIT TESTS - Protocol Parsing and JWT Extraction

### 1.1. WebSocket Protocol Format Parsing Tests
**Purpose:** Validate backend protocol parsing logic handles both correct and incorrect formats
**Location:** `/netra_backend/tests/unit/websocket_core/test_websocket_protocol_parsing.py`

#### Test Specifications:

```python
class TestWebSocketProtocolParsing:
    """Unit tests for WebSocket protocol format parsing - DESIGNED TO FAIL INITIALLY"""
    
    def test_jwt_protocol_format_extraction_success(self):
        """
        Test successful JWT token extraction from correct protocol format
        
        Expected Format: ['jwt-auth', 'jwt.eyJ0eXAiOiJKV1QiLCJhbGc...']
        Should Extract: eyJ0eXAiOiJKV1QiLCJhbGc...
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (unit test)
        STATUS: Should PASS after fix
        """
    
    def test_jwt_protocol_format_extraction_failure_array_format(self):
        """
        Test JWT token extraction failure with array format (CURRENT BUG)
        
        Current Bug Format: ['jwt', 'eyJ0eXAiOiJKV1QiLCJhbGc...'] (as separate elements)
        Expected Behavior: Should fail to extract token
        
        DIFFICULTY: Low (5 minutes)  
        REAL SERVICES: No (unit test)
        STATUS: Should FAIL initially (reproduces bug), then behavior varies after fix
        """
    
    def test_subprotocol_jwt_prefix_validation(self):
        """
        Test validation of jwt. prefix in subprotocol strings
        
        Valid: 'jwt.token_data'
        Invalid: 'jwt token_data', 'bearer.token_data', 'token_data'
        
        DIFFICULTY: Low (3 minutes)
        REAL SERVICES: No (unit test)  
        STATUS: Should FAIL initially, PASS after fix
        """
    
    def test_base64url_token_decoding_validation(self):
        """
        Test base64url decoding of JWT tokens from subprotocol
        
        Tests encoding/decoding consistency with frontend implementation
        
        DIFFICULTY: Medium (10 minutes)
        REAL SERVICES: No (unit test)
        STATUS: Should PASS (not part of bug, but validates fix compatibility)
        """
```

### 1.2. JWT Token Validation Unit Tests
**Purpose:** Validate JWT token extraction and validation logic
**Location:** `/netra_backend/tests/unit/services/test_unified_authentication_protocol_parsing.py`

#### Test Specifications:

```python
class TestUnifiedAuthenticationProtocolParsing:
    """Unit tests for authentication service protocol parsing"""
    
    def test_websocket_jwt_extraction_from_subprotocols_success(self):
        """
        Test successful JWT extraction from WebSocket subprotocols
        
        Input: Mock WebSocket with subprotocols=['jwt-auth', 'jwt.validtoken123']
        Expected: Extract 'validtoken123'
        
        DIFFICULTY: Low (7 minutes)
        REAL SERVICES: No (mocked WebSocket)
        STATUS: Should FAIL initially, PASS after fix
        """
    
    def test_websocket_jwt_extraction_no_token_found(self):
        """
        Test handling when no JWT token found in subprotocols (CURRENT BUG SCENARIO)
        
        Input: Mock WebSocket with subprotocols=['jwt', 'tokendata'] (incorrect format)
        Expected: Return NO_TOKEN error code
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (mocked WebSocket)
        STATUS: Should PASS initially (correctly identifies no token), should still PASS after fix
        """
    
    def test_authentication_result_error_codes(self):
        """
        Test proper error codes returned for different auth failure scenarios
        
        Validates error_code field matches expected values for different failure types
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (mocked inputs)
        STATUS: Should PASS (validates error handling consistency)
        """
```

---

## 2. INTEGRATION TESTS - Frontend-Backend Protocol Negotiation

### 2.1. WebSocket Connection Integration Tests  
**Purpose:** Test real WebSocket connections between frontend and backend with actual protocol negotiation
**Location:** `/netra_backend/tests/integration/websocket_core/test_websocket_auth_protocol_integration.py`

#### Test Specifications:

```python
class TestWebSocketAuthProtocolIntegration:
    """Integration tests for WebSocket authentication protocol - REAL SERVICES ONLY"""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_with_correct_protocol_format(self):
        """
        Test WebSocket connection with correct protocol format
        
        Protocol: ['jwt-auth', 'jwt.base64url_encoded_token']  
        Expected: Successful connection and authentication
        
        DIFFICULTY: Medium (15 minutes)
        REAL SERVICES: Yes (Docker backend + real JWT)
        STATUS: Should PASS (validates correct implementation)
        """
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_connection_with_incorrect_protocol_format_bug_reproduction(self):
        """
        Test WebSocket connection with incorrect protocol format (REPRODUCES CURRENT BUG)
        
        Protocol: ['jwt', 'base64url_encoded_token'] (as separate elements - current bug)
        Expected: Connection failure with NO_TOKEN error
        
        DIFFICULTY: Medium (15 minutes)
        REAL SERVICES: Yes (Docker backend + real JWT)
        STATUS: Should FAIL initially (connection times out), PASS after fix (proper error handling)
        """
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_handshake_timeout_reproduction(self):
        """
        Test reproduction of handshake timeout scenario from staging
        
        Simulates exact staging conditions causing handshake timeouts
        
        DIFFICULTY: High (25 minutes) 
        REAL SERVICES: Yes (Docker with GCP-like network conditions)
        STATUS: Should FAIL initially (timeout), PASS after fix
        """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_routing_after_auth_failure_cascade(self):
        """
        Test message routing behavior after authentication failure
        
        Validates that auth failures don't cascade to message routing errors
        
        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes (full WebSocket + message routing stack)
        STATUS: Should FAIL initially (cascade failures), PASS after fix
        """
```

### 2.2. Authentication Service Integration Tests
**Purpose:** Test authentication service integration with WebSocket connections
**Location:** `/netra_backend/tests/integration/services/test_websocket_unified_auth_integration.py`

#### Test Specifications:

```python
class TestWebSocketUnifiedAuthIntegration:
    """Integration tests for WebSocket + unified auth service"""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_auth_with_real_jwt_tokens(self):
        """
        Test WebSocket authentication with real JWT tokens
        
        Uses actual JWT generation and validation services
        
        DIFFICULTY: Medium (15 minutes)
        REAL SERVICES: Yes (Auth service + JWT validator)
        STATUS: Should FAIL initially (protocol mismatch), PASS after fix
        """
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_websocket_auth_circuit_breaker_behavior(self):
        """
        Test circuit breaker behavior with repeated auth failures
        
        Validates circuit breaker doesn't trigger unnecessarily due to protocol issues
        
        DIFFICULTY: High (20 minutes)
        REAL SERVICES: Yes (full auth stack)
        STATUS: Should FAIL initially (unnecessary circuit breaking), improve after fix
        """
```

---

## 3. E2E STAGING TESTS - Complete Golden Path Validation

### 3.1. Staging Environment WebSocket E2E Tests
**Purpose:** Test complete user journey in actual staging environment with GCP Cloud Run
**Location:** `/tests/e2e/staging/test_websocket_auth_golden_path_staging.py`

#### Test Specifications:

```python
class TestWebSocketAuthGoldenPathStaging:
    """E2E tests for WebSocket authentication in staging - MISSION CRITICAL"""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    async def test_complete_golden_path_user_flow_staging(self):
        """
        Test complete Golden Path: login → WebSocket connection → AI response
        
        Full user journey:
        1. User login via OAuth
        2. WebSocket connection with JWT
        3. Send chat message
        4. Receive AI agent response
        
        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes (staging GCP Cloud Run environment)
        STATUS: Should FAIL initially (WebSocket connection timeout), PASS after fix
        """
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_websocket_connection_gcp_cloud_run_environment(self):
        """
        Test WebSocket connection specifically in GCP Cloud Run environment
        
        Validates connection behavior with GCP networking and container constraints
        
        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes (staging GCP deployment)
        STATUS: Should FAIL initially (handshake timeout), PASS after fix
        """
    
    @pytest.mark.e2e
    @pytest.mark.staging  
    async def test_concurrent_user_websocket_connections_staging(self):
        """
        Test multiple concurrent users connecting to WebSocket in staging
        
        Validates user isolation and protocol handling under concurrent load
        
        DIFFICULTY: Very High (35 minutes)
        REAL SERVICES: Yes (staging environment)
        STATUS: Should FAIL initially (connection failures), PASS after fix
        """
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_websocket_heartbeat_and_reconnection_staging(self):
        """
        Test WebSocket heartbeat and reconnection behavior in staging
        
        Validates connection stability and recovery from network interruptions
        
        DIFFICULTY: High (25 minutes) 
        REAL SERVICES: Yes (staging with network simulation)
        STATUS: May FAIL initially (connection instability), improve after fix
        """
```

### 3.2. Frontend-Backend Integration E2E Tests
**Purpose:** Test real frontend WebSocket client against staging backend  
**Location:** `/frontend/__tests__/e2e/websocket-auth-protocol-staging.test.tsx`

#### Test Specifications:

```typescript
describe('WebSocket Authentication Protocol E2E - Staging', () => {
  
  test('Frontend WebSocket client connects to staging backend successfully', async () => {
    /*
     * Test real frontend WebSocket service connecting to staging backend
     * 
     * Uses actual frontend WebSocket client implementation
     * Connects to real staging backend endpoint
     * 
     * DIFFICULTY: High (30 minutes)
     * REAL SERVICES: Yes (frontend client + staging backend)
     * STATUS: Should FAIL initially (protocol mismatch), PASS after fix
     */
  });
  
  test('Frontend WebSocket protocol format matches backend expectations', async () => {
    /*
     * Test protocol format sent by frontend matches backend parsing logic
     * 
     * Validates frontend sends: ['jwt-auth', 'jwt.token']
     * Backend expects: jwt.token extraction from subprotocol
     * 
     * DIFFICULTY: Medium (20 minutes) 
     * REAL SERVICES: Yes (protocol inspection)
     * STATUS: Should FAIL initially (format mismatch), PASS after fix
     */
  });
  
  test('Frontend handles WebSocket authentication errors properly', async () => {
    /*
     * Test frontend error handling for WebSocket auth failures
     * 
     * Validates user experience when authentication fails
     * 
     * DIFFICULTY: Medium (15 minutes)
     * REAL SERVICES: Yes (error simulation)
     * STATUS: Should improve after fix (better error handling)
     */
  });
});
```

---

## 4. TEST SUITE ORGANIZATION AND EXECUTION STRATEGY

### 4.1. Test Categories and Execution Order

#### **Priority 1: Unit Tests (Fast Feedback - 2-5 minutes each)**
```bash
# Protocol parsing validation
python -m pytest netra_backend/tests/unit/websocket_core/test_websocket_protocol_parsing.py -v

# Authentication service unit tests  
python -m pytest netra_backend/tests/unit/services/test_unified_authentication_protocol_parsing.py -v
```

#### **Priority 2: Integration Tests (Medium Feedback - 15-25 minutes each)**  
```bash
# WebSocket connection integration
python -m pytest netra_backend/tests/integration/websocket_core/test_websocket_auth_protocol_integration.py -v --real-services

# Authentication service integration
python -m pytest netra_backend/tests/integration/services/test_websocket_unified_auth_integration.py -v --real-services
```

#### **Priority 3: E2E Tests (Comprehensive Validation - 25-45 minutes each)**
```bash
# Staging environment E2E tests
python -m pytest tests/e2e/staging/test_websocket_auth_golden_path_staging.py -v --staging

# Frontend E2E tests
npm run test:e2e:staging
```

### 4.2. Test Execution Matrix

| Test Suite | Environment | Services | Expected Initial Status | Post-Fix Status | Business Impact |
|------------|-------------|----------|-------------------------|-----------------|------------------|
| **Unit: Protocol Parsing** | Local | Mocks | ❌ FAIL | ✅ PASS | High - Validates core logic |
| **Unit: JWT Extraction** | Local | Mocks | ❌ FAIL | ✅ PASS | High - Validates auth logic |
| **Integration: WebSocket** | Docker | Real | ❌ FAIL | ✅ PASS | Critical - Real connection test |
| **Integration: Auth Service** | Docker | Real | ❌ FAIL | ✅ PASS | Critical - End-to-end auth |
| **E2E: Golden Path** | Staging | Real | ❌ FAIL | ✅ PASS | **MISSION CRITICAL** - $500K+ ARR |
| **E2E: Concurrent Users** | Staging | Real | ❌ FAIL | ✅ PASS | Critical - Multi-user validation |
| **E2E: Frontend Integration** | Staging | Real | ❌ FAIL | ✅ PASS | Critical - User experience |

### 4.3. Test Data and Configuration Management

#### **JWT Token Generation for Tests**
```python
# Real JWT tokens generated using production auth service
test_jwt_valid = await auth_service.create_access_token(user_id="test_user_123")
test_jwt_expired = await auth_service.create_access_token(user_id="test_user_123", expires_delta=-3600)
```

#### **WebSocket Protocol Test Cases**
```python
# Test protocol formats
PROTOCOL_FORMATS = {
    "correct_current": ["jwt-auth", "jwt.base64url_token"],
    "incorrect_bug": ["jwt", "base64url_token"],  # Current bug format
    "incorrect_bearer": ["Bearer", "raw_token"],
    "incorrect_no_prefix": ["auth", "token_data"]
}
```

#### **Staging Environment Configuration**
```python
STAGING_CONFIG = {
    "websocket_url": "wss://staging-backend-dot-netra-staging.uc.r.appspot.com/ws",
    "auth_endpoint": "https://staging-backend-dot-netra-staging.uc.r.appspot.com/auth",
    "timeout_settings": {
        "connection": 30,  # GCP Cloud Run timeout
        "handshake": 20,
        "message": 15
    }
}
```

---

## 5. STAGING ENVIRONMENT VALIDATION APPROACH

### 5.1. GCP Cloud Run Specific Tests

#### **Container Networking Tests**
```python
async def test_gcp_cloud_run_websocket_networking():
    """
    Test WebSocket connections through GCP Cloud Run networking
    
    Validates:
    - Container port mapping
    - Load balancer WebSocket support  
    - VPC connector accessibility
    - Container timeout settings
    """
```

#### **Authentication Service Integration**
```python
async def test_gcp_auth_service_websocket_integration():
    """
    Test auth service integration in GCP environment
    
    Validates:
    - Service-to-service communication
    - JWT token validation across services
    - Network latency impact on handshake
    """
```

### 5.2. Real Production-Like Conditions

#### **Network Latency Simulation**
```python  
async def test_websocket_auth_with_network_latency():
    """
    Test WebSocket authentication with simulated network latency
    
    Simulates real-world conditions that may affect handshake timing
    """
```

#### **Concurrent User Load Testing**
```python
async def test_concurrent_websocket_connections_load():
    """
    Test multiple concurrent WebSocket connections
    
    Validates system behavior under realistic user load
    """
```

---

## 6. TEST VALIDATION AND SUCCESS CRITERIA

### 6.1. Pre-Fix Validation (Tests Must Fail)
- [ ] Unit tests identify protocol parsing failures
- [ ] Integration tests reproduce connection timeouts  
- [ ] E2E tests fail on Golden Path user flow
- [ ] Staging tests demonstrate handshake failures
- [ ] All test failures correlate with known issue symptoms

### 6.2. Post-Fix Validation (Tests Must Pass)  
- [ ] Unit tests validate correct protocol parsing
- [ ] Integration tests establish successful WebSocket connections
- [ ] E2E tests complete full Golden Path user flow  
- [ ] Staging tests maintain stable connections
- [ ] No cascade failures from auth to message routing

### 6.3. Performance and Stability Criteria
- [ ] WebSocket connections establish within 10 seconds
- [ ] Authentication failures return proper error codes (not timeouts)
- [ ] Message routing operates independently of authentication status
- [ ] Concurrent users maintain isolated connection states
- [ ] Heartbeat and reconnection mechanisms function properly

---

## 7. TEST EXECUTION COMMANDS AND AUTOMATION

### 7.1. Quick Validation Suite (10 minutes)
```bash
# Fast feedback on core protocol logic
python -m pytest \
  netra_backend/tests/unit/websocket_core/test_websocket_protocol_parsing.py \
  netra_backend/tests/unit/services/test_unified_authentication_protocol_parsing.py \
  -v --tb=short
```

### 7.2. Integration Validation Suite (45 minutes) 
```bash
# Real service integration testing
python tests/unified_test_runner.py \
  --categories integration \
  --real-services \
  --include-pattern "*websocket*auth*protocol*" \
  --staging-config
```

### 7.3. Full E2E Golden Path Validation (90 minutes)
```bash
# Complete Golden Path testing
python tests/unified_test_runner.py \
  --categories e2e \
  --env staging \
  --include-pattern "*golden*path*" \
  --real-llm \
  --detailed-logging
```

### 7.4. Continuous Integration Integration
```yaml
# CI Pipeline Stage for WebSocket Auth Protocol Tests
websocket_auth_protocol_tests:
  stage: integration_tests
  script:
    - python -m pytest netra_backend/tests/unit/websocket_core/test_websocket_protocol_parsing.py --junitxml=unit_results.xml
    - python tests/unified_test_runner.py --categories integration --include-pattern "*websocket*auth*protocol*" --junitxml=integration_results.xml  
  artifacts:
    reports:
      junit:
        - unit_results.xml
        - integration_results.xml
  only:
    - merge_requests
    - staging
    - main
```

---

## 8. RISK MITIGATION AND ROLLBACK STRATEGY

### 8.1. Test Failure Analysis Process
1. **Immediate Triage:** Categorize failures as expected (pre-fix) vs unexpected  
2. **Root Cause Analysis:** Trace failures to specific protocol handling logic
3. **Impact Assessment:** Determine business impact of each failure type
4. **Fix Prioritization:** Address Golden Path blocking issues first

### 8.2. Rollback Testing Strategy
```python
async def test_rollback_compatibility():
    """
    Test that fixes maintain backward compatibility
    
    Validates that protocol changes don't break existing working connections
    """
```

### 8.3. Progressive Deployment Testing
```python
async def test_canary_deployment_websocket_behavior():
    """  
    Test WebSocket behavior during canary deployments
    
    Validates connection stability during gradual rollouts
    """
```

---

## 9. MONITORING AND OBSERVABILITY INTEGRATION

### 9.1. Test Metrics Collection
- **Connection Success Rate:** Percentage of successful WebSocket connections
- **Authentication Success Rate:** Percentage of successful JWT authentications  
- **Handshake Latency:** Time from connection initiation to completion
- **Error Code Distribution:** Breakdown of authentication error types

### 9.2. Alerting Integration
```python
async def test_monitoring_alert_integration():
    """
    Test integration with monitoring and alerting systems
    
    Validates that WebSocket auth failures trigger appropriate alerts
    """
```

---

## 10. BUSINESS VALUE VALIDATION

### 10.1. Golden Path Revenue Impact Testing
- **User Journey Completion Rate:** Percentage of users completing login → chat flow
- **Message Success Rate:** Percentage of messages successfully routed after authentication
- **User Experience Metrics:** Time to first successful AI response

### 10.2. Competitive Advantage Validation
```python
async def test_chat_functionality_business_value():
    """
    Test that WebSocket auth fixes enable substantive chat functionality
    
    Validates business value delivery through working AI interactions
    """
```

---

## CONCLUSION

This comprehensive test plan provides multi-layered validation of WebSocket authentication protocol mismatch issues, with tests specifically designed to:

1. **Fail Initially** - Proving they detect the real issue
2. **Pass After Fix** - Validating the solution works  
3. **Protect Business Value** - Ensuring $500K+ ARR chat functionality
4. **Scale to Production** - Working in real GCP Cloud Run environments

The test suite progresses from fast unit tests (2-5 minutes) through integration tests (15-25 minutes) to comprehensive E2E validation (25-45 minutes), providing both rapid feedback and thorough validation of the critical Golden Path user flow.

**CRITICAL SUCCESS CRITERION:** All E2E Golden Path tests must transition from FAILING to PASSING, demonstrating restored chat functionality and business value delivery.