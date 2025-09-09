# Real WebSocket Testing Suite - Multi-User Isolation Security

## Overview

This directory contains the **Real WebSocket Testing Suite** that implements comprehensive multi-user isolation security tests using ONLY real WebSocket connections to backend services.

**CRITICAL: NO MOCKS ALLOWED** per CLAUDE.md requirements. All tests use real WebSocket connections with proper JWT authentication.

## Business Value Justification

- **Segment**: Platform/Internal - Multi-user chat security infrastructure
- **Business Goal**: Prevent user data leaks in multi-tenant AI environment (GDPR compliance)
- **Value Impact**: Protects user privacy in real-time AI interactions
- **Revenue Impact**: Prevents security breaches that destroy customer trust and business

## Architecture

### Core Components

1. **`test_framework/ssot/real_websocket_test_client.py`**
   - SSOT real WebSocket test client with authentication
   - User isolation validation (fails hard on violations)
   - Event capture and security validation
   - NO MOCKS - connects to actual backend services

2. **`test_framework/ssot/real_websocket_connection_manager.py`**
   - Manages multiple authenticated WebSocket connections
   - Concurrent multi-user isolation testing
   - Comprehensive violation detection and reporting
   - Stress testing under high concurrent load

3. **`tests/e2e/websocket/test_real_multi_user_websocket_isolation.py`**
   - Critical security tests for multi-user isolation
   - Tests FAIL HARD when isolation violations detected
   - Validates that User A's data never leaks to User B
   - Real WebSocket connections with JWT authentication

4. **`tests/e2e/websocket/test_isolation_violation_detection.py`**
   - Meta-tests that verify violation detection works
   - Ensures security validation is reliable
   - Tests the tests (validation of security mechanisms)

## Critical Security Features

### ✅ Multi-User Isolation Validation
- **User Event Isolation**: Events sent to User A are NOT received by User B
- **Private Data Protection**: User-specific data cannot leak between accounts  
- **Authentication Boundary Enforcement**: Each connection operates only within authenticated user context
- **Concurrent Session Isolation**: Isolation maintained under high concurrent load

### ✅ Fail-Hard Security Validation
- Tests **IMMEDIATELY FAIL** when isolation violations detected
- `SecurityError` raised for critical violations
- Comprehensive violation reporting and tracking
- No false positives - security failures are real failures

### ✅ Real Service Integration
- Connects to actual backend WebSocket services
- Uses real JWT authentication from E2EAuthHelper
- Integrates with Docker test infrastructure
- NO MOCKS - validates real-world behavior

## Test Categories

### 1. Core Isolation Tests (`test_real_multi_user_websocket_isolation.py`)

#### `test_two_user_event_isolation_critical()`
**MOST CRITICAL TEST**: Validates that events sent to User A are NOT received by User B.
- Creates 2 authenticated WebSocket connections
- User A sends private event with sensitive data
- Verifies User B does NOT receive User A's event
- **FAILS HARD** if cross-user event leak detected

#### `test_concurrent_user_data_isolation()`
Validates private user data isolation under concurrent operations.
- Creates 5 concurrent authenticated users
- Each sends private data (secrets, account info)
- Validates no cross-user data contamination
- **FAILS HARD** if private data leaks between users

#### `test_authentication_boundary_isolation()`
Validates authentication contexts are strictly isolated.
- Creates users with different permission levels
- Verifies each connection operates only within its auth context
- Validates JWT token isolation
- **FAILS HARD** if authentication boundaries crossed

#### `test_high_concurrency_isolation_stress()`
Stress tests isolation under heavy concurrent load.
- Creates 10 concurrent users sending 5 events each
- Validates isolation maintained under stress
- Comprehensive violation detection
- **FAILS HARD** if isolation fails under normal load

#### `test_agent_event_isolation_during_execution()`
**CRITICAL FOR CHAT**: Validates agent execution events are isolated.
- User A triggers agent execution
- Verifies User B does NOT receive User A's agent events
- Protects AI interaction privacy
- **FAILS HARD** if agent events leak between users

#### `test_websocket_connection_hijacking_prevention()`
Validates WebSocket connections cannot be hijacked.
- Tests that users cannot impersonate other users
- Validates connection security
- Prevents session takeover attacks
- **FAILS HARD** if hijacking possible

### 2. Violation Detection Tests (`test_isolation_violation_detection.py`)

Meta-tests that verify our security validation works correctly:

- `test_client_detects_user_id_mismatch()`: Verifies client detects wrong user IDs
- `test_assert_no_violations_fails_when_violations_exist()`: Verifies assertions fail when violations present
- `test_connection_manager_detects_violations()`: Verifies manager reports violations correctly
- `test_security_error_raised_on_critical_violations()`: Verifies SecurityError works

## Usage Examples

### Basic Multi-User Isolation Test
```python
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager

async def test_basic_isolation():
    manager = RealWebSocketConnectionManager(
        backend_url="ws://localhost:8000",
        environment="test"
    )
    
    # Create 2 authenticated connections
    async with manager.managed_connections(count=2) as connection_ids:
        user_a_id, user_b_id = connection_ids
        
        # Get clients
        user_a = manager.get_connection(user_a_id)
        user_b = manager.get_connection(user_b_id)
        
        # User A sends private data
        await user_a.send_event("private_data", {
            "secret": "User A's private information"
        })
        
        # Verify User B does NOT receive it
        try:
            events = await user_b.wait_for_events(
                event_types={"private_data"}, 
                timeout=5.0
            )
            if events:
                pytest.fail("VIOLATION: User B received User A's private data!")
        except asyncio.TimeoutError:
            # Good - User B should not receive User A's events
            pass
        
        # Verify no violations
        user_a.assert_no_isolation_violations()
        user_b.assert_no_isolation_violations()
```

### Comprehensive Isolation Testing
```python
from test_framework.ssot.real_websocket_connection_manager import (
    RealWebSocketConnectionManager, 
    IsolationTestType
)

async def test_comprehensive_isolation():
    manager = RealWebSocketConnectionManager()
    
    async with manager.managed_connections(count=5) as connection_ids:
        # Run all isolation test types
        test_types = [
            IsolationTestType.EVENT_ISOLATION,
            IsolationTestType.USER_DATA_ISOLATION, 
            IsolationTestType.AUTHENTICATION_ISOLATION,
            IsolationTestType.CONCURRENT_SESSION_ISOLATION
        ]
        
        for test_type in test_types:
            result = await manager.test_user_isolation(test_type=test_type)
            
            # Will raise SecurityError if violations detected
            assert result.test_passed, f"{test_type.value} failed"
        
        # Verify no global violations
        manager.assert_no_violations()
```

## Running the Tests

### Prerequisites
1. Docker services must be running (`docker-compose up -d`)
2. Backend and auth services must be healthy
3. JWT authentication properly configured

### Run All Isolation Tests
```bash
pytest tests/e2e/websocket/test_real_multi_user_websocket_isolation.py -v
```

### Run Specific Critical Test
```bash
pytest tests/e2e/websocket/test_real_multi_user_websocket_isolation.py::TestRealMultiUserWebSocketIsolation::test_two_user_event_isolation_critical -v
```

### Run Violation Detection Verification
```bash
pytest tests/e2e/websocket/test_isolation_violation_detection.py -v
```

### Run with Real Services
```bash
pytest tests/e2e/websocket/ --real-services -v
```

## Expected Behavior

### ✅ PASS Scenarios
- Each user only receives their own events
- Private data remains isolated between users
- Authentication boundaries are respected
- No cross-user contamination under concurrent load
- Violation detection works correctly

### ❌ FAIL Scenarios (Security Violations)
- User A receives events meant for User B
- Private data leaks between user accounts
- Authentication contexts get mixed
- Session hijacking succeeds
- Isolation fails under concurrent load

## Integration with Existing Systems

### E2EAuthHelper Integration
- Uses `test_framework.ssot.e2e_auth_helper` for JWT authentication
- Creates authenticated users with proper permissions
- Validates token-based isolation

### Docker Test Infrastructure
- Integrates with `UnifiedDockerManager`
- Requires real backend and auth services
- Automatic service health checking

### Unified Test Runner Integration
```bash
python tests/unified_test_runner.py --category e2e --real-services
```

## Monitoring and Metrics

### Connection Metrics
- Connection establishment time
- Authentication duration  
- Events sent/received counts
- Violation detection accuracy

### Isolation Metrics
- Total users tested concurrently
- Events validated for isolation
- Violation detection rate
- Test execution duration

## Compliance and Security

### CLAUDE.md Compliance
- ✅ Real services only (NO MOCKS)
- ✅ E2E tests use authentication
- ✅ Tests fail hard when isolation violated
- ✅ Multi-user system validation

### Security Standards
- ✅ User data privacy protection (GDPR)
- ✅ Multi-tenant isolation validation
- ✅ Authentication boundary enforcement
- ✅ Session security validation

## Troubleshooting

### Common Issues

**Test fails with "Docker services not available"**
- Ensure Docker is running: `docker-compose up -d`
- Check service health: `docker-compose ps`

**Authentication failures**
- Verify JWT secret configuration
- Check auth service is responding
- Validate E2E test credentials

**False isolation violations**
- Check event user_id fields are populated correctly
- Verify WebSocket message routing
- Validate authentication context

### Debug Mode
Set `WEBSOCKET_DEBUG=1` environment variable for detailed logging.

## Future Enhancements

1. **Performance Testing**: Add WebSocket performance benchmarks
2. **Chaos Engineering**: Random connection failures and recovery
3. **Load Testing**: Scale to 100+ concurrent users
4. **Real Production Testing**: Staging environment validation

## Conclusion

This Real WebSocket Testing Suite provides comprehensive security validation for multi-user isolation in the Netra platform. It ensures that user privacy is protected and that AI interactions remain confidential between users.

The tests use real WebSocket connections and proper authentication to validate actual system behavior, providing confidence that the platform maintains strict user isolation in production environments.