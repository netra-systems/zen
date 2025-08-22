# WebSocket Test Suite Implementation Plan

## Overview
Comprehensive WebSocket test suite aligned with SPEC/websockets.xml and SPEC/websocket_communication.xml specifications, focusing on unified interservice connections using REAL dev launcher running services.

## Test Suite Components

### 1. Test: WebSocket Connection Lifecycle with Auth
**File**: `test_websocket_lifecycle_auth.py`
**Objective**: Validate complete WebSocket connection lifecycle with proper JWT authentication
**Coverage**:
- Connection establishment before first message (SPEC requirement)
- JWT token validation during handshake
- Database session handling in WebSocket endpoints (avoid Depends() pattern)
- Persistent connection through component re-renders
- Graceful connection cleanup on disconnect

### 2. Test: Event Structure Consistency
**File**: `test_event_structure_consistency.py`
**Objective**: Ensure all WebSocket messages use consistent {type, payload} structure
**Coverage**:
- Validate JSON-first communication (no string messages)
- Check for double/triple JSON wrapping issues
- Verify event structure matches frontend expectations
- Test all event types from event catalog

### 3. Test: Missing Event Implementation
**File**: `test_missing_events_implementation.py`
**Objective**: Verify backend sends all events expected by frontend unified system
**Coverage**:
- agent_thinking events with intermediate reasoning
- partial_result events for streaming content
- tool_executing events when tools start
- final_report events with comprehensive results
- Proper agent_started payload (run_id, agent_name, timestamp)

### 4. Test: UI Layer Timing Requirements
**File**: `test_ui_layer_timing.py`
**Objective**: Validate events reach appropriate UI layers within timing constraints
**Coverage**:
- Fast layer events (<100ms): agent_started, tool_executing
- Medium layer events (<1s): agent_thinking, partial_result
- Slow layer events (>1s): agent_completed, final_report
- Event ordering and accumulation

### 5. Test: Service Discovery Integration
**File**: `test_websocket_service_discovery.py`
**Objective**: Validate WebSocket configuration discovery from backend
**Coverage**:
- Backend provides WebSocket config via service discovery
- Frontend discovers and loads config at startup
- Config includes proper auth integration with SecurityService
- WebSocket URL construction and validation

### 6. Test: Multi-Service WebSocket Coherence
**File**: `test_multi_service_websocket_coherence.py`
**Objective**: Test WebSocket communication across all microservices
**Coverage**:
- Main backend WebSocket endpoints
- Auth service WebSocket integration
- Frontend WebSocket client connection
- Message routing between services
- Session isolation between different users

### 7. Test: WebSocket Resilience and Recovery
**File**: `test_websocket_resilience_recovery.py`
**Objective**: Validate WebSocket connection resilience
**Coverage**:
- Automatic reconnection on network failure
- Message queuing during disconnection
- Token refresh during active connection
- Backend service restart recovery
- Malformed payload handling

## Multi-Agent Execution Plan

### Agent 1: Test Suite Writer
**Responsibility**: Implement all 7 test files
**Tasks**:
- Create test fixtures for WebSocket connections
- Implement comprehensive test cases
- Use real services via dev_launcher
- Follow TDD principles from SPEC/learnings/testing.xml

### Agent 2: Test Suite Reviewer
**Responsibility**: Review test implementation for compliance
**Tasks**:
- Verify alignment with XML specifications
- Check for proper async/await usage
- Validate no test stubs (per SPEC/no_test_stubs.xml)
- Ensure type safety compliance

### Agent 3: Test Runner & System Fixer
**Responsibility**: Run tests and fix system issues
**Tasks**:
- Execute test suite with real services
- Identify and fix WebSocket implementation gaps
- Update backend event emissions
- Align message structures

### Agent 4: Final Review & Validation
**Responsibility**: Triple-check all work
**Tasks**:
- Verify all tests pass consistently
- Check for regressions
- Update relevant XML specs with learnings
- Generate final compliance report

## Success Criteria

1. **All tests pass** with real services running via dev_launcher
2. **100% event coverage** - all events from SPEC/websocket_communication.xml implemented
3. **Timing requirements met** - UI layers receive events within specified windows
4. **No silent failures** - all errors properly raised and handled
5. **Consistent message structure** - {type, payload} format throughout
6. **Proper auth integration** - JWT validation without hanging
7. **Service independence** - microservices remain 100% independent

## Execution Timeline

1. **Phase 1**: Test Suite Implementation (Agent 1) - 30 minutes
2. **Phase 2**: Review & Refinement (Agent 2) - 15 minutes  
3. **Phase 3**: Run & Fix (Agent 3) - 45 minutes
4. **Phase 4**: Final Validation (Agent 4) - 15 minutes

Total estimated time: ~2 hours

## Key Dependencies

- dev_launcher.py running all services
- Valid test JWT tokens
- Database connections initialized
- WebSocket client libraries
- Test configuration from TEST_CONFIG

## Risk Mitigation

- **Risk**: Services fail to start
  - **Mitigation**: Use startup.xml learnings for proper initialization

- **Risk**: Database session issues in WebSocket
  - **Mitigation**: Follow correct pattern from SPEC/websockets.xml

- **Risk**: Token validation hanging
  - **Mitigation**: Apply websocket_message_paradox.xml learnings

- **Risk**: Event structure mismatches
  - **Mitigation**: Strict validation against websocket_communication.xml