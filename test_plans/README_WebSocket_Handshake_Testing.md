# WebSocket Authentication Handshake Test Plan

## Overview

This comprehensive test plan addresses the critical WebSocket authentication handshake issue identified through five whys analysis. The root cause is that the current implementation violates RFC 6455 by performing authentication AFTER accepting the WebSocket connection, when it should happen DURING the handshake phase.

**Business Impact**: $500K+ ARR at risk due to WebSocket authentication failures breaking chat functionality (90% of platform value).

## Root Cause Summary

**Current (Broken) Flow:**
1. `websocket.accept()` called first
2. JWT token extracted from headers AFTER accept
3. Authentication validation happens post-connection
4. This violates RFC 6455 subprotocol negotiation requirements
5. Results in 1011 errors and connection failures

**Correct (RFC 6455) Flow:**
1. Extract JWT from `Sec-WebSocket-Protocol` header BEFORE accept
2. Validate JWT token DURING handshake phase  
3. Negotiate subprotocol response BEFORE accept
4. `websocket.accept(subprotocol="negotiated-protocol")` with proper subprotocol
5. Complete authentication context setup AFTER accept

## Test Plan Structure

### 1. Unit Tests (`TestWebSocketSubprotocolNegotiation`)
- **Purpose**: Test RFC 6455 subprotocol negotiation compliance
- **Expected**: Should initially FAIL, demonstrating RFC violations
- **Validates**: 
  - JWT extraction from various header formats
  - Subprotocol negotiation timing
  - Malformed header handling
  - 1011 error prevention

### 2. Integration Tests (`TestWebSocketHandshakeAuthenticationFlow`)
- **Purpose**: Test complete handshake flow with real WebSocket connections
- **Expected**: Should initially FAIL, proving handshake timing issues
- **Validates**:
  - Authentication BEFORE accept() calls
  - Concurrent connection handling
  - Cloud Run race condition prevention
  - Proper error handling without 1011 errors

### 3. E2E Tests (`TestWebSocketAuthenticationE2E`)
- **Purpose**: Test complete user journey from auth to agent response
- **Expected**: Should demonstrate business value impact
- **Validates**:
  - Complete Golden Path functionality (login → AI responses)
  - WebSocket event delivery (all 5 critical events)
  - Graceful authentication failure handling
  - Cloud Run environment simulation

### 4. Performance Tests (`TestWebSocketHandshakePerformance`)
- **Purpose**: Ensure fix doesn't introduce performance regression
- **Expected**: Should maintain current performance levels
- **Validates**:
  - JWT extraction performance
  - Subprotocol negotiation performance
  - Memory usage optimization

### 5. Remediation Validation (`TestWebSocketHandshakeRemediationValidation`)
- **Purpose**: Validate fix implementation works correctly
- **Expected**: Should PASS after fix is implemented
- **Validates**:
  - Correct RFC 6455 handshake sequence
  - 1011 error elimination
  - Golden Path functionality preservation

## Test Execution

### Quick Start
```bash
# Run the complete test suite with automated phases
./scripts/run_websocket_handshake_tests.py
```

### Manual Execution

#### Phase 1: Demonstrate Issue (Tests Should FAIL)
```bash
# Run tests that prove the handshake issue exists
python -m pytest test_plans/websocket_auth_handshake_comprehensive_test_plan.py \
  -k "test_websocket_handshake_timing_violation_detection" -v
```

#### Phase 2: RFC 6455 Compliance
```bash
# Test subprotocol negotiation compliance
python -m pytest test_plans/websocket_auth_handshake_comprehensive_test_plan.py \
  -k "TestWebSocketSubprotocolNegotiation" -v
```

#### Phase 3: Integration Testing
```bash
# Test with real WebSocket connections (requires Docker)
python -m pytest test_plans/websocket_auth_handshake_comprehensive_test_plan.py \
  -k "TestWebSocketHandshakeAuthenticationFlow" -v --real-services
```

#### Phase 4: E2E Business Value
```bash
# Test complete user journey (requires real services)
python -m pytest test_plans/websocket_auth_handshake_comprehensive_test_plan.py \
  -k "TestWebSocketAuthenticationE2E" -v --real-services -m mission_critical
```

#### Phase 5: Post-Fix Validation (After Implementing Fix)
```bash
# These should PASS after fix is implemented
python -m pytest test_plans/websocket_auth_handshake_comprehensive_test_plan.py \
  -k "remediation_validation" -v
```

## Expected Test Results

### Before Fix Implementation
- **Unit Tests**: FAIL (proving RFC 6455 violations exist)
- **Integration Tests**: FAIL (demonstrating handshake timing issues)
- **E2E Tests**: FAIL or flaky (showing business impact)
- **Performance Tests**: PASS (baseline performance)
- **Remediation Tests**: FAIL (fix not implemented yet)

### After Fix Implementation
- **Unit Tests**: PASS (RFC 6455 compliance achieved)
- **Integration Tests**: PASS (proper handshake timing)
- **E2E Tests**: PASS (business value preserved)
- **Performance Tests**: PASS (no regression)
- **Remediation Tests**: PASS (fix validation successful)

## Implementation Guide

### Step 1: Modify WebSocket Route Handler

Current problematic code in `websocket_ssot.py`:
```python
# ❌ BROKEN: Accept first, authenticate later
await websocket.accept(subprotocol=accepted_subprotocol)
auth_result = await authenticate_websocket_ssot(websocket)
```

Fixed implementation:
```python
# ✅ CORRECT: Extract JWT and negotiate BEFORE accept
jwt_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(websocket)
if jwt_token:
    # Validate JWT BEFORE accepting connection
    auth_validation = await validate_jwt_token_during_handshake(jwt_token)
    if auth_validation.valid:
        # Negotiate subprotocol based on successful auth
        accepted_subprotocol = negotiate_websocket_subprotocol(["jwt-auth"])
        await websocket.accept(subprotocol=accepted_subprotocol)
        # Complete auth context setup AFTER accept
        auth_result = create_authenticated_context(auth_validation)
    else:
        # Reject connection with proper error
        await websocket.close(code=1008, reason="Authentication failed")
else:
    await websocket.close(code=1002, reason="Authentication required")
```

### Step 2: Update Authentication Flow

Modify `unified_websocket_auth.py`:
```python
async def authenticate_websocket_during_handshake(websocket: WebSocket) -> AuthHandshakeResult:
    """
    Authenticate WebSocket DURING handshake phase (before accept).
    
    This function extracts and validates JWT tokens before the WebSocket
    connection is accepted, ensuring RFC 6455 compliance.
    """
    # Extract JWT from subprotocol header
    jwt_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(websocket)
    
    if not jwt_token:
        return AuthHandshakeResult(success=False, reason="no_token")
    
    # Validate JWT without requiring accepted connection
    auth_service = get_unified_auth_service()
    validation_result = await auth_service.validate_jwt_token_with_business_context(
        jwt_token, 
        {"handshake_phase": True}
    )
    
    return AuthHandshakeResult(
        success=validation_result.get("valid", False),
        user_id=validation_result.get("user_id"),
        claims=validation_result.get("claims"),
        jwt_token=jwt_token
    )
```

### Step 3: Update All WebSocket Modes

Apply the fix to all modes in `websocket_ssot.py`:
- Main mode (`main_mode_handler`)
- Factory mode (`factory_mode_handler`) 
- Isolated mode (`isolated_mode_handler`)
- Legacy mode (`legacy_mode_handler`)

## Test Utilities

### WebSocket Handshake Validator
```python
from test_framework.websocket_handshake_test_utilities import WebSocketHandshakeValidator

validator = WebSocketHandshakeValidator()
# ... perform handshake operations ...
compliance_report = validator.get_compliance_report()
assert compliance_report["compliant"], f"RFC 6455 violations: {compliance_report['violations']}"
```

### Mock WebSocket Factory
```python
from test_framework.websocket_handshake_test_utilities import MockWebSocketFactory

# Create WebSocket with JWT in subprotocol
websocket = MockWebSocketFactory.create_websocket_with_jwt("valid_jwt_token")

# Create malformed WebSocket for error testing
error_websocket = MockWebSocketFactory.create_malformed_websocket("empty_jwt")
```

### Business Value Validator
```python
from test_framework.websocket_handshake_test_utilities import WebSocketBusinessValueValidator

# Validate Golden Path preservation
results = await WebSocketBusinessValueValidator.validate_golden_path_preservation(
    websocket_client_factory, 
    jwt_token
)
assert results["golden_path_preserved"], f"Business value at risk: {results['errors']}"
```

## Business Value Protection

### Golden Path Requirements
The fix MUST preserve these critical business flows:

1. **User Authentication**: Users can connect with valid JWT tokens
2. **WebSocket Events**: All 5 critical events delivered (`agent_started`, `agent_thinking`, `tool_executing`, `tool_completed`, `agent_completed`)
3. **Agent Responses**: AI agents return meaningful, actionable responses
4. **Real-time Interaction**: Chat experience remains responsive and reliable
5. **Error Handling**: Authentication failures handled gracefully without 1011 errors

### Revenue Impact Monitoring
- **Chat Functionality Score**: Must remain ≥80% for revenue protection
- **Enterprise Customer Impact**: Zero tolerance for authentication failures
- **Golden Path Availability**: 99.9% uptime required for $500K+ ARR protection

## Troubleshooting

### Common Issues

#### Tests Failing Unexpectedly
```bash
# Check if Docker services are running
docker ps

# Restart test environment
python scripts/refresh_dev_services.py refresh --services backend auth

# Run with detailed logging
python -m pytest test_plans/websocket_auth_handshake_comprehensive_test_plan.py -v -s --log-cli-level=DEBUG
```

#### Authentication Service Issues
```bash
# Verify auth service is responding
curl http://localhost:8081/health

# Check JWT configuration
python scripts/query_string_literals.py validate "JWT_SECRET_KEY"
```

#### WebSocket Connection Issues
```bash
# Test WebSocket endpoint directly
wscat -c "ws://localhost:8000/ws/main" -H "sec-websocket-protocol: jwt.test_token"

# Check WebSocket manager status
curl http://localhost:8000/ws/health
```

### Performance Issues
If performance tests fail after implementing the fix:

1. **Profile JWT extraction**: Use `WebSocketPerformanceProfiler` to identify bottlenecks
2. **Cache validation results**: Implement caching for repeated JWT validations
3. **Optimize subprotocol negotiation**: Minimize string operations during handshake
4. **Monitor memory usage**: Ensure no memory leaks in authentication context creation

## Success Criteria

### Technical Criteria
- [ ] All unit tests pass (RFC 6455 compliance)
- [ ] All integration tests pass (proper handshake timing)
- [ ] All E2E tests pass (business value preserved)
- [ ] No performance regression (≤5% increase in latency)
- [ ] Zero 1011 errors in error scenarios

### Business Criteria  
- [ ] Golden Path functionality preserved (login → AI responses)
- [ ] Chat functionality score ≥80%
- [ ] Enterprise customer authentication success rate ≥99%
- [ ] WebSocket event delivery reliability ≥99.9%
- [ ] No revenue impact during deployment

## Deployment Strategy

### Pre-Deployment
1. Run complete test suite locally
2. Validate in staging environment with real user scenarios
3. Performance benchmark with production-like load
4. Create rollback plan

### Deployment
1. Deploy to staging first
2. Monitor business metrics for 24 hours
3. Validate with subset of real users
4. Gradual rollout to production

### Post-Deployment
1. Monitor WebSocket connection success rates
2. Track chat functionality business metrics
3. Watch for any 1011 error increases
4. Validate Golden Path availability

## Support

For questions about this test plan or implementation:

1. **Test Execution Issues**: Check test runner logs and Docker service status
2. **Business Impact Concerns**: Review Golden Path preservation test results
3. **Performance Questions**: Analyze performance profiler reports
4. **RFC 6455 Compliance**: Refer to handshake sequence validation results

**Remember**: This test plan is designed to fail initially, proving the issue exists. Success is measured by tests passing AFTER the proper RFC 6455 fix is implemented while preserving all business value.