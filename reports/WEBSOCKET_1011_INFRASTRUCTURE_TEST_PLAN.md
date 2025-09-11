# WebSocket 1011 Infrastructure Failure Test Plan

**CRITICAL MISSION:** Systematically reproduce and isolate WebSocket 1011 internal errors blocking Golden Path functionality (90% of business value)

**BUSINESS VALUE JUSTIFICATION:**
- **Segment:** Platform/Internal - Critical infrastructure testing
- **Business Goal:** Restore Golden Path WebSocket functionality for chat value delivery 
- **Value Impact:** Enables real-time AI interactions that drive customer conversions
- **Strategic Impact:** Unblocks $120K+ MRR at risk from WebSocket infrastructure failures

## Executive Summary

**CURRENT STATUS:** 2/4 P1 critical tests passing - need to reach 4/4
**PRIMARY BLOCKER:** GCP Cloud Run infrastructure-level WebSocket proxy configuration causing 1011 internal errors
**ROOT HYPOTHESIS:** Infrastructure vs application layer issue separation needed

**FAILING TESTS:**
1. `test_001_websocket_connection_real` - WebSocket 1011 internal error
2. `test_002_websocket_authentication_real` - WebSocket 1011 internal error  
3. `test_023_streaming_partial_results_real` - TIMEOUT (dependent on WebSocket stability)
4. `test_025_critical_event_delivery_real` - TIMEOUT (dependent on WebSocket stability)

## Test Plan Architecture

### Phase 1: Infrastructure Isolation Tests (Unit-style, No Docker)

**Purpose:** Isolate GCP Cloud Run WebSocket proxy configuration issues from application code

#### Test Suite 1.1: WebSocket Proxy Configuration Validation
```python
# File: tests/unit/infrastructure/test_websocket_proxy_configuration.py

class TestWebSocketProxyConfiguration:
    """Tests WebSocket proxy layer configuration without application dependencies."""
    
    @pytest.mark.unit
    async def test_gcp_load_balancer_websocket_upgrade_headers(self):
        """Test #1.1.1: Validate GCP Load Balancer WebSocket upgrade header handling"""
        # EXPECTED FAILURE: 1011 internal error during WebSocket upgrade
        # SUCCESS CRITERIA: Proper Upgrade: websocket header processing
    
    @pytest.mark.unit  
    async def test_cloud_run_websocket_timeout_configuration(self):
        """Test #1.1.2: Validate Cloud Run WebSocket timeout settings"""
        # EXPECTED FAILURE: Connection timeouts or 1011 errors
        # SUCCESS CRITERIA: Connections sustained for >30 seconds
        
    @pytest.mark.unit
    async def test_websocket_subprotocol_negotiation(self):
        """Test #1.1.3: Test WebSocket subprotocol negotiation (jwt-auth)"""
        # EXPECTED FAILURE: Subprotocol rejection causing 1011
        # SUCCESS CRITERIA: Proper jwt-auth subprotocol acceptance
```

#### Test Suite 1.2: Network Layer Diagnostics
```python
# File: tests/unit/infrastructure/test_network_layer_diagnostics.py

class TestNetworkLayerDiagnostics:
    """Low-level network diagnostics for WebSocket infrastructure."""
    
    @pytest.mark.unit
    async def test_tcp_websocket_handshake_timing(self):
        """Test #1.2.1: Measure TCP handshake timing for WebSocket connections"""
        # EXPECTED OUTCOME: Identify timing failures causing 1011
        
    @pytest.mark.unit
    async def test_ssl_tls_websocket_certificate_chain(self):
        """Test #1.2.2: Validate SSL/TLS certificate chain for WebSocket endpoints"""
        # EXPECTED FAILURE: Certificate validation issues
        
    @pytest.mark.unit
    async def test_http_to_websocket_upgrade_flow(self):
        """Test #1.2.3: Test HTTP->WebSocket upgrade flow step-by-step"""
        # EXPECTED FAILURE: 1011 during upgrade process
```

### Phase 2: Application Layer Integration Tests (Non-Docker)

**Purpose:** Test application WebSocket handling with real services (but not Docker dependencies)

#### Test Suite 2.1: WebSocket Authentication Layer
```python
# File: tests/integration/websocket/test_websocket_auth_layer.py

class TestWebSocketAuthLayer:
    """Test WebSocket authentication handling with real auth service."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_websocket_authentication_flow(self, real_auth_service):
        """Test #2.1.1: JWT token validation through WebSocket connection"""
        # EXPECTED FAILURE: Auth succeeds but 1011 error after authentication
        # SUCCESS CRITERIA: Authentication completes, connection remains stable
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_auth_token_refresh_during_connection(self, real_auth_service):
        """Test #2.1.2: Token refresh during active WebSocket connection"""
        # EXPECTED FAILURE: Token refresh triggers 1011 disconnection
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_auth_isolation(self, real_auth_service):
        """Test #2.1.3: Multiple user WebSocket authentication isolation"""
        # EXPECTED FAILURE: Cross-user contamination or 1011 errors
```

#### Test Suite 2.2: WebSocket Message Flow Without Agents
```python
# File: tests/integration/websocket/test_websocket_message_flow.py

class TestWebSocketMessageFlow:
    """Test basic WebSocket message flow without agent complexity."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_simple_ping_pong_websocket_flow(self, real_backend):
        """Test #2.2.1: Basic ping/pong message flow"""
        # EXPECTED FAILURE: Messages send but 1011 error during response
        # SUCCESS CRITERIA: Bidirectional message flow sustained
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_lifecycle_events(self, real_backend):
        """Test #2.2.2: Connection establishment and close events"""
        # EXPECTED FAILURE: 1011 during connection lifecycle transitions
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_handling_recovery(self, real_backend):
        """Test #2.2.3: Error handling and recovery patterns"""
        # EXPECTED FAILURE: 1011 errors not recovered gracefully
```

### Phase 3: E2E Staging Infrastructure Validation

**Purpose:** Test complete WebSocket flow against GCP staging environment

#### Test Suite 3.1: GCP Staging Infrastructure Tests
```python
# File: tests/e2e/staging/test_websocket_infrastructure_validation.py

class TestWebSocketInfrastructureValidation:
    """Direct testing of GCP staging WebSocket infrastructure."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_gcp_staging_websocket_load_balancer_direct(self):
        """Test #3.1.1: Direct test of GCP Load Balancer WebSocket handling"""
        # EXPECTED FAILURE: 1011 internal error from load balancer
        # SUCCESS CRITERIA: Load balancer properly forwards WebSocket traffic
        
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_cloud_run_websocket_instance_scaling(self):
        """Test #3.1.2: WebSocket behavior during Cloud Run instance scaling"""
        # EXPECTED FAILURE: 1011 during scaling events
        
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_websocket_connection_persistence(self):
        """Test #3.1.3: WebSocket connection persistence across infrastructure"""
        # EXPECTED FAILURE: Connections dropped with 1011 errors
```

#### Test Suite 3.2: Progressive WebSocket Agent Integration
```python
# File: tests/e2e/staging/test_progressive_websocket_agent_integration.py

class TestProgressiveWebSocketAgentIntegration:
    """Progressive integration of WebSocket events with agent execution."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_minimal_agent_websocket_events(self):
        """Test #3.2.1: Minimal agent execution with WebSocket event delivery"""
        # EXPECTED FAILURE: Agent executes but WebSocket events fail with 1011
        # SUCCESS CRITERIA: All 5 critical events delivered successfully
        
    @pytest.mark.e2e
    @pytest.mark.staging  
    async def test_streaming_response_websocket_stability(self):
        """Test #3.2.2: Streaming responses through WebSocket connections"""
        # EXPECTED FAILURE: Stream starts but 1011 error during transmission
        
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_critical_event_delivery_reliability(self):
        """Test #3.2.3: Reliability of critical WebSocket event delivery"""
        # EXPECTED FAILURE: Events sent but not delivered due to 1011 errors
```

## Test Implementation Strategy

### 1. Infrastructure vs Application Layer Separation

**KEY PRINCIPLE:** Tests must definitively prove whether 1011 errors originate from:
- **Infrastructure Layer:** GCP Load Balancer, Cloud Run WebSocket proxy configuration
- **Application Layer:** Backend WebSocket handling, authentication, or agent integration

### 2. Progressive Failure Isolation

```
Unit Tests (Infrastructure) → Integration Tests (App Layer) → E2E Tests (Full Stack)
```

Each layer builds upon the previous, allowing precise isolation of failure points.

### 3. Expected Failure Patterns

#### Infrastructure Layer Failures:
- **1011 Internal Error during WebSocket upgrade**
- **Connection timeouts during handshake**
- **SSL/TLS certificate validation failures**
- **Load balancer WebSocket proxy misconfigurations**

#### Application Layer Failures:
- **Authentication succeeds but connection drops**
- **Message routing failures**
- **Agent execution triggers connection drops**
- **Event delivery pipeline failures**

### 4. Success Criteria Definition

#### Phase 1 Success (Infrastructure):
- [ ] WebSocket connections establish without 1011 errors
- [ ] SSL/TLS handshake completes successfully
- [ ] HTTP->WebSocket upgrade succeeds
- [ ] Connection sustained for >30 seconds

#### Phase 2 Success (Application):
- [ ] Authentication completes without connection drops
- [ ] Bidirectional message flow works reliably
- [ ] Connection lifecycle managed properly
- [ ] Error recovery patterns function

#### Phase 3 Success (E2E):
- [ ] GCP staging infrastructure handles WebSocket traffic
- [ ] Agent execution delivers all 5 critical events
- [ ] Streaming responses work without 1011 errors
- [ ] Critical event delivery is 100% reliable

## Test Configuration & Environment

### Required Test Infrastructure

#### Non-Docker Tests (Phases 1-2):
```python
# Configuration for non-Docker tests
WEBSOCKET_TEST_CONFIG = {
    "staging_websocket_url": "wss://netra-staging.uc.r.appspot.com/ws",
    "staging_backend_url": "https://netra-staging.uc.r.appspot.com",
    "auth_service_url": "https://netra-staging.uc.r.appspot.com/auth",
    "test_timeouts": {
        "connection": 30,
        "authentication": 15,
        "message_response": 10
    }
}
```

#### E2E Staging Tests (Phase 3):
```python
# Full staging environment configuration
STAGING_E2E_CONFIG = {
    "environment": "staging",
    "real_llm": False,  # Use staging LLM endpoint
    "real_auth": True,  # Use real OAuth flows
    "real_websocket": True,  # Use real WebSocket connections
    "infrastructure_monitoring": True  # Enable infrastructure metrics
}
```

### Test Data & Authentication

#### Test User Creation:
```python
# SSOT test user for WebSocket testing
WEBSOCKET_TEST_USERS = {
    "websocket_test_user_1": {
        "email": "websocket-test-1@netra-testing.example.com",
        "subscription": "enterprise",
        "permissions": ["websocket_access", "agent_execution"]
    },
    "websocket_test_user_2": {
        "email": "websocket-test-2@netra-testing.example.com", 
        "subscription": "early",
        "permissions": ["websocket_access"]
    }
}
```

## Implementation Files Structure

```
tests/
├── unit/infrastructure/
│   ├── test_websocket_proxy_configuration.py
│   ├── test_network_layer_diagnostics.py
│   └── test_gcp_load_balancer_websocket.py
├── integration/websocket/
│   ├── test_websocket_auth_layer.py
│   ├── test_websocket_message_flow.py
│   └── test_websocket_error_recovery.py
├── e2e/staging/
│   ├── test_websocket_infrastructure_validation.py
│   ├── test_progressive_websocket_agent_integration.py
│   └── test_websocket_1011_reproduction_suite.py
└── test_framework/
    ├── websocket_infrastructure_helpers.py
    ├── gcp_websocket_diagnostics.py
    └── websocket_1011_reproduction_utilities.py
```

## Expected Outcomes & Next Steps

### If Infrastructure Layer Tests Fail:
**Root Cause:** GCP Cloud Run WebSocket proxy configuration
**Actions Required:**
1. Review GCP Load Balancer WebSocket settings
2. Validate Cloud Run WebSocket timeout configurations  
3. Check SSL/TLS certificate chain for WebSocket endpoints
4. Review WebSocket subprotocol handling in load balancer

### If Application Layer Tests Fail:
**Root Cause:** Backend WebSocket handling or authentication
**Actions Required:**
1. Review WebSocket authentication middleware
2. Validate message routing and event delivery pipelines
3. Check agent execution WebSocket integration
4. Review error handling and recovery patterns

### If E2E Tests Fail:
**Root Cause:** Integration between infrastructure and application
**Actions Required:**
1. Review staging environment configuration
2. Validate end-to-end WebSocket event delivery
3. Check agent execution with real WebSocket connections
4. Review monitoring and observability for WebSocket failures

## Risk Mitigation

### Windows Asyncio Compatibility:
- Enhanced timeout handling for Windows + GCP cross-network connections
- Retry logic for Windows asyncio issues
- Alternative connection patterns for Windows environments

### Test Flakiness Prevention:
- Deterministic test ordering
- Proper connection cleanup
- Infrastructure readiness checks
- Clear failure vs success criteria

### Infrastructure Monitoring:
- Real-time WebSocket connection metrics
- GCP Load Balancer logs integration
- Cloud Run instance scaling monitoring
- SSL/TLS handshake timing measurements

## Compliance & Standards

### CLAUDE.md Compliance:
- ✅ Real services testing (no mocks except limited unit tests)
- ✅ E2E tests use authentication (JWT/OAuth flows)
- ✅ SSOT patterns from test_framework/ssot/
- ✅ Strongly typed contexts and validation
- ✅ Business value justification for each test

### Test Quality Standards:
- All tests MUST fail hard with clear error messages
- No silent failures or false positives
- 0-second execution tests automatically fail
- Infrastructure vs application layer separation
- Progressive testing strategy validation

---

**DELIVERABLE STATUS:** ✅ Comprehensive test plan ready for implementation
**NEXT ACTION:** Begin implementation with Phase 1 Infrastructure Isolation Tests
**SUCCESS METRIC:** Achieve 4/4 P1 critical tests passing, unblocking Golden Path functionality