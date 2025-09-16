# Comprehensive Auth-WebSocket Integration Test Plan

**Business Value Justification:**
- **Segment:** Platform/Internal - Testing Infrastructure + All Users
- **Business Goal:** Ensure $500K+ ARR auth-websocket-agent integration works reliably
- **Value Impact:** Validates 90% of platform value (chat functionality) works end-to-end
- **Strategic Impact:** Prevents production auth failures that would cause complete platform outage

## Executive Summary

This test plan creates comprehensive, NON-DOCKER tests that reproduce the real infrastructure issues identified in staging environments, specifically:

1. **Infrastructure Header Stripping Issue**: Cloud Run load balancers stripping authentication headers
2. **SSOT Auth Policy Violations**: E2E bypass not working in staging environments  
3. **WebSocket Event Delivery Failures**: Silent failures preventing chat functionality
4. **Race Conditions**: Auth handshake timing issues in distributed environments

## Authentication Pathways Identified

Based on analysis of `unified_authentication_service.py` and `unified_jwt_protocol_handler.py`, there are **6 authentication pathways** to test:

### Primary Authentication Methods (4 pathways)
1. **Authorization Header**: `Authorization: Bearer <jwt_token>`
2. **WebSocket Subprotocol jwt.**: `Sec-WebSocket-Protocol: jwt.<base64url_token>`
3. **WebSocket Subprotocol jwt-auth.**: `Sec-WebSocket-Protocol: jwt-auth.<token>`
4. **WebSocket Subprotocol bearer.**: `Sec-WebSocket-Protocol: bearer.<token>`

### Staging/E2E Methods (2 pathways)  
5. **E2E Bypass Mode**: E2E context with bypass enabled for testing
6. **Query Parameter Fallback**: `?token=<jwt_token>` (compatibility mode)

## Test Architecture

### Unit Tests (Non-Docker)
**Location:** `tests/unit/auth_websocket/`

#### Test Files to Create:

1. **`test_unified_authentication_service_unit.py`**
   ```python
   """
   Unit tests for UnifiedAuthenticationService - SSOT authentication logic
   
   Tests individual authentication methods without external dependencies.
   """
   
   class TestUnifiedAuthenticationService:
       async def test_authenticate_token_jwt_format_validation(self):
           """Test JWT format validation catches malformed tokens"""
       
       async def test_authentication_context_tracking(self):
           """Test context (REST/WebSocket/etc.) is properly tracked"""
           
       async def test_e2e_bypass_creation(self):
           """Test E2E bypass creates valid mock auth results"""
           
       async def test_extract_user_id_from_e2e_token_patterns(self):
           """Test extraction of user IDs from E2E token patterns"""
   ```

2. **`test_unified_jwt_protocol_handler_unit.py`**
   ```python
   """
   Unit tests for UnifiedJWTProtocolHandler - All 6 authentication pathways
   
   Tests JWT extraction from various WebSocket sources without network calls.
   """
   
   class TestUnifiedJWTProtocolHandler:
       def test_extract_from_authorization_header(self):
           """Test pathway #1: Authorization header extraction"""
           
       def test_extract_from_subprotocol_jwt_format(self):
           """Test pathway #2: jwt.<token> subprotocol extraction"""
           
       def test_extract_from_subprotocol_jwt_auth_format(self):
           """Test pathway #3: jwt-auth.<token> subprotocol extraction"""
           
       def test_extract_from_subprotocol_bearer_format(self):
           """Test pathway #4: bearer.<token> subprotocol extraction"""
           
       def test_extract_from_query_parameters(self):
           """Test pathway #6: Query parameter fallback extraction"""
           
       def test_base64url_decoding_with_padding_variations(self):
           """Test base64url decoding handles missing padding correctly"""
           
       def test_normalize_jwt_for_validation_consistency(self):
           """Test token normalization produces consistent output"""
   ```

3. **`test_websocket_auth_result_unit.py`**
   ```python
   """
   Unit tests for AuthResult class and WebSocket-specific validation
   """
   
   class TestAuthResultWebSocketIntegration:
       def test_auth_result_to_dict_compatibility(self):
           """Test AuthResult.to_dict() produces expected format"""
           
       def test_auth_result_error_codes_standardization(self):
           """Test error codes are consistent across auth pathways"""
           
       def test_auth_result_metadata_preservation(self):
           """Test metadata from WebSocket context is preserved"""
   ```

### Integration Tests (Non-Docker)
**Location:** `tests/integration/auth_websocket/`

#### Test Files to Create:

1. **`test_auth_websocket_handshake_integration.py`**
   ```python
   """
   Integration tests for auth-websocket handshake WITHOUT Docker
   
   Uses service abstractions to test authentication flow integration.
   """
   
   class TestAuthWebSocketHandshakeIntegration(BaseIntegrationTest):
       async def test_successful_auth_handshake_all_pathways(self, service_abstraction):
           """Test successful authentication via all 6 pathways"""
           
       async def test_infrastructure_header_stripping_reproduction(self, service_abstraction):
           """REPRODUCE: Cloud Run load balancer stripping headers"""
           
       async def test_ssot_auth_policy_violation_reproduction(self, service_abstraction):
           """REPRODUCE: E2E bypass not working in staging-like environment"""
           
       async def test_websocket_auth_race_condition_detection(self, service_abstraction):
           """Test auth handshake timing under simulated latency"""
           
       async def test_auth_failure_recovery_patterns(self, service_abstraction):
           """Test system recovery from various auth failure modes"""
   ```

2. **`test_user_execution_context_creation_integration.py`**
   ```python
   """
   Integration tests for UserExecutionContext creation after auth success
   
   Tests factory pattern isolation and state management.
   """
   
   class TestUserExecutionContextCreationIntegration(BaseIntegrationTest):
       async def test_user_context_factory_isolation(self, service_abstraction):
           """Test multi-user context isolation via factory pattern"""
           
       async def test_preliminary_connection_id_preservation(self, service_abstraction):
           """Test state machine continuity with preliminary connection IDs"""
           
       async def test_defensive_context_creation_fallbacks(self, service_abstraction):
           """Test fallback mechanisms prevent 1011 WebSocket errors"""
   ```

3. **`test_websocket_event_delivery_integration.py`**
   ```python
   """
   Integration tests for WebSocket event delivery after successful auth
   
   Tests that all 5 critical events are delivered to authenticated users.
   """
   
   class TestWebSocketEventDeliveryIntegration(BaseIntegrationTest):
       async def test_five_critical_events_delivery(self, service_abstraction):
           """Test all 5 events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed"""
           
       async def test_event_delivery_user_isolation(self, service_abstraction):
           """Test events only delivered to correct authenticated user"""
           
       async def test_event_delivery_silent_failure_detection(self, service_abstraction):
           """Test detection of silent WebSocket event delivery failures"""
   ```

### E2E Tests on Staging GCP
**Location:** `tests/e2e/staging/auth_websocket/`

#### Test Files to Create:

1. **`test_staging_infrastructure_auth_validation.py`**
   ```python
   """
   E2E tests on staging GCP to validate real infrastructure behavior
   
   Tests actual Cloud Run, load balancers, and staging auth service.
   """
   
   @pytest.mark.e2e
   @pytest.mark.staging
   class TestStagingInfrastructureAuthValidation:
       async def test_staging_load_balancer_header_preservation(self):
           """Test GCP load balancer preserves all auth headers"""
           
       async def test_staging_auth_service_connectivity(self):
           """Test staging auth service responds to validation requests"""
           
       async def test_staging_websocket_auth_end_to_end(self):
           """Test complete auth-websocket flow on staging infrastructure"""
           
       async def test_staging_e2e_bypass_functionality(self):
           """Test E2E bypass works in staging environment"""
   ```

2. **`test_staging_websocket_agent_integration.py`**
   ```python
   """
   E2E tests for complete staging auth-websocket-agent integration
   
   Tests the complete Golden Path: auth → websocket → agent → events
   """
   
   @pytest.mark.e2e
   @pytest.mark.staging
   @pytest.mark.mission_critical
   class TestStagingWebSocketAgentIntegration:
       async def test_staging_complete_golden_path_flow(self):
           """Test complete Golden Path on staging: auth → websocket → agent → 5 events"""
           
       async def test_staging_multi_user_isolation(self):
           """Test multi-user auth isolation on staging infrastructure"""
           
       async def test_staging_auth_websocket_agent_performance(self):
           """Test performance of complete flow under realistic staging load"""
   ```

## Test Categories and Execution Strategy

### Execution Commands

```bash
# Unit Tests (Fast - No external dependencies)
python tests/unified_test_runner.py --category unit --path tests/unit/auth_websocket/

# Integration Tests (Service abstractions - No Docker)
python tests/unified_test_runner.py --category integration --path tests/integration/auth_websocket/ --no-docker

# E2E Staging Tests (Real infrastructure)
python tests/unified_test_runner.py --category e2e --env staging --path tests/e2e/staging/auth_websocket/
```

## Failing Test Patterns to Reproduce Infrastructure Issues

### Pattern 1: Infrastructure Header Stripping
```python
async def test_infrastructure_header_stripping_simulation():
    """
    FAILING TEST: Simulate Cloud Run load balancer stripping headers
    
    This test should FAIL until infrastructure header preservation is fixed.
    """
    # Simulate headers being stripped by load balancer
    original_headers = {
        "Authorization": "Bearer staging-jwt-token",
        "X-Forwarded-For": "10.0.0.1",
        "X-Cloud-Trace-Context": "trace-id"
    }
    
    # Simulate what reaches the backend after load balancer processing
    stripped_headers = {
        "X-Forwarded-For": "10.0.0.1",  # Load balancer preserves this
        "X-Cloud-Trace-Context": "trace-id"  # Load balancer preserves this
        # Authorization header MISSING - this is the bug
    }
    
    mock_websocket = create_mock_websocket(headers=stripped_headers)
    auth_service = UnifiedAuthenticationService()
    
    # This should FAIL until infrastructure is fixed
    with pytest.raises(AuthenticationError, match="No JWT token found"):
        auth_result, user_context = await auth_service.authenticate_websocket(mock_websocket)
```

### Pattern 2: SSOT Auth Policy Violation
```python
async def test_ssot_auth_policy_violation_reproduction():
    """
    FAILING TEST: Reproduce SSOT auth policy violation in staging-like environment
    
    This test should FAIL until E2E bypass propagation is fixed.
    """
    # Setup E2E context that should trigger bypass
    e2e_context = {
        "bypass_enabled": True,
        "test_environment": "staging",
        "user_id": "staging-e2e-user-001"
    }
    
    # Create staging-like WebSocket with E2E headers
    staging_headers = {
        "X-E2E-Test": "true",
        "X-Test-Environment": "staging", 
        "Authorization": "Bearer staging-e2e-jwt-token"
    }
    
    mock_websocket = create_mock_websocket(headers=staging_headers)
    auth_service = UnifiedAuthenticationService()
    
    # E2E bypass should work but currently fails in staging
    auth_result, user_context = await auth_service.authenticate_websocket(
        mock_websocket, 
        e2e_context=e2e_context
    )
    
    # This assertion should FAIL until E2E bypass propagation is fixed
    assert auth_result.success, "E2E bypass should work in staging environment"
    assert "e2e_bypass" in auth_result.metadata, "E2E bypass metadata should be present"
```

## WebSocket Event Delivery Validation

### Critical Events Testing (5 Required Events)
```python
class WebSocketEventValidator:
    """Validates all 5 critical WebSocket events are delivered"""
    
    REQUIRED_EVENTS = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    async def test_all_five_events_delivered_after_auth(self):
        """Test all 5 events delivered after successful authentication"""
        # Perform authentication
        auth_result, user_context = await self._authenticate_test_user()
        assert auth_result.success
        
        # Send agent request via authenticated WebSocket  
        agent_request = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": "Test message for event validation"
        }
        
        # Collect events with timeout
        events = await self._collect_websocket_events(timeout=30)
        
        # Validate all 5 events received
        event_types = [event.get("type") for event in events]
        for required_event in self.REQUIRED_EVENTS:
            assert required_event in event_types, f"Missing required event: {required_event}"
        
        # Validate event order
        assert event_types[0] == "agent_started", "First event should be agent_started"
        assert event_types[-1] == "agent_completed", "Last event should be agent_completed"
```

## Race Condition Testing

### Timing-Sensitive Test Patterns
```python
async def test_auth_websocket_race_condition_detection():
    """Test authentication handshake under various timing conditions"""
    
    # Test concurrent authentication attempts
    async def concurrent_auth_attempt(user_id: str):
        token = create_test_jwt_token(user_id=user_id)
        mock_websocket = create_mock_websocket_with_auth(token)
        auth_service = UnifiedAuthenticationService()
        return await auth_service.authenticate_websocket(mock_websocket)
    
    # Run multiple concurrent auth attempts
    results = await asyncio.gather(*[
        concurrent_auth_attempt(f"user-{i}") for i in range(10)
    ])
    
    # All should succeed without race conditions
    for auth_result, user_context in results:
        assert auth_result.success, "Concurrent auth should not fail due to race conditions"
        assert user_context is not None, "User context should be created successfully"
```

## Service Abstraction Patterns (No Docker Required)

### Mock Service Creation
```python
from test_framework.service_abstraction import ServiceAbstraction

@pytest.fixture
async def service_abstraction():
    """Provide service abstractions for testing without Docker"""
    abstraction = ServiceAbstraction()
    
    # Configure mock auth service
    abstraction.configure_auth_service(
        response_mode="realistic",  # Realistic timing and responses
        failure_rate=0.05,          # 5% failure rate for testing robustness
        latency_ms=(100, 300)       # Variable latency like real service
    )
    
    # Configure mock WebSocket manager  
    abstraction.configure_websocket_manager(
        event_delivery_mode="reliable",
        max_connections=100,
        heartbeat_interval=30
    )
    
    return abstraction
```

## Test Data Patterns

### JWT Token Generation for Testing
```python
def create_test_jwt_tokens():
    """Create various JWT token formats for testing all pathways"""
    base_payload = {
        "sub": "test-user-123",
        "email": "test@netra.com", 
        "permissions": ["user", "websocket_access"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    
    # Valid JWT for testing
    valid_jwt = create_test_jwt_token(**base_payload)
    
    # E2E testing JWT
    e2e_jwt = create_test_jwt_token(
        user_id="staging-e2e-user-001",
        email="staging-e2e-user-001@e2e-test.netra.com",
        permissions=["user", "e2e_testing", "websocket_access"]
    )
    
    # Malformed JWTs for testing validation
    malformed_jwts = [
        "invalid.jwt",           # Wrong number of parts
        "header.payload",        # Missing signature  
        "",                      # Empty token
        "Bearer ",               # Bearer with no token
        "not-a-jwt-at-all"      # Random string
    ]
    
    return {
        "valid": valid_jwt,
        "e2e": e2e_jwt, 
        "malformed": malformed_jwts
    }
```

## Success Criteria

### Unit Tests (100% Pass Rate Required)
- All 6 authentication pathways extract tokens correctly
- JWT format validation catches all malformed tokens
- E2E bypass logic works in isolation
- Error handling prevents system crashes

### Integration Tests (95% Pass Rate Target)
- Auth-WebSocket handshake works via service abstractions
- Multi-user isolation maintained without Docker
- WebSocket events delivered reliably after authentication
- Race conditions detected and handled gracefully

### E2E Staging Tests (90% Pass Rate Target)
- Real staging infrastructure preserves auth headers
- Complete Golden Path works end-to-end on GCP
- Performance meets production requirements under load
- Silent failures detected and prevented

## Implementation Priority

### Phase 1 (P0 - Immediate): Critical Reproduction Tests
1. Create failing tests that reproduce infrastructure header stripping
2. Create failing tests that reproduce SSOT auth policy violations
3. Implement basic WebSocket event delivery validation

### Phase 2 (P1 - Within 1 Week): Complete Unit Coverage
1. Implement all 6 authentication pathway unit tests
2. Create comprehensive JWT protocol handler tests
3. Add auth result validation and error handling tests

### Phase 3 (P2 - Within 2 Weeks): Integration Testing
1. Implement auth-websocket handshake integration tests
2. Add user execution context creation tests
3. Create multi-user isolation validation tests

### Phase 4 (P3 - Within 3 Weeks): E2E Staging Validation
1. Create staging infrastructure validation tests
2. Implement complete Golden Path E2E tests
3. Add performance and load testing on staging

## Compliance with CLAUDE.md

### Business Value Focus
- Tests validate $500K+ ARR auth-websocket-agent integration
- Focus on Golden Path: users login → get AI responses
- 90% of platform value (chat functionality) validation

### SSOT Patterns  
- All tests use `test_framework/` SSOT utilities
- No duplicate authentication logic in tests
- Unified test runner for all execution

### Real Services First
- Integration tests use service abstractions (not mocks)
- E2E tests use real staging infrastructure  
- Only unit tests allowed to mock external dependencies

### WebSocket Event Priority
- All 5 critical events validated: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Event delivery is mission-critical test requirement
- Silent failure detection implemented

This comprehensive test plan provides thorough coverage of auth-websocket integration without requiring Docker containers, while focusing on reproducing and fixing the real infrastructure issues identified in the staging environment.