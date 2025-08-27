# WebSocket Core Functionality Tests

This directory contains comprehensive WebSocket tests focusing on **CORE BASIC FUNCTIONALITY** that the entire Netra platform depends on.

## Overview

These tests validate fundamental WebSocket operations with real connections (no mocking) to ensure production-like behavior validation.

## Test Files

### `test_concurrent_connections.py` - Test #7 [HIGH PRIORITY - P1]
**Purpose**: Multiple simultaneous connections per user (multi-tab/device scenarios)

**Business Impact**: Enables power users with multiple browser tabs - critical for Enterprise segment retention

**Test Scenarios**:
- Same user opens 5+ concurrent connections (multi-tab simulation)
- Messages broadcast to all user connections
- Connection limits per user enforced properly
- Independent connection lifecycle management
- One connection failure doesn't affect others
- Resource cleanup when connections close

**Key Classes**:
- `ConcurrentConnectionManager`: Manages multiple WebSocket connections
- `ConcurrentMessageBroadcaster`: Handles message broadcasting tests
- `ConcurrentConnectionValidator`: Validates connection behavior
- `ConnectionLimitManager`: Tests connection limits and enforcement

## Running Tests

### Individual Test Execution
```bash
# Run concurrent connection tests
python tests/unified/websocket/run_concurrent_test.py

# Verbose output
python tests/unified/websocket/run_concurrent_test.py --verbose

# Dry run (show what would be tested)
python tests/unified/websocket/run_concurrent_test.py --dry-run
```

### Via pytest
```bash
# Run specific test file
python -m pytest tests/unified/websocket/test_concurrent_connections.py -v

# Run all websocket tests
python -m pytest tests/unified/websocket/ -v

# Run with coverage
python -m pytest tests/unified/websocket/ --cov=app.websocket_handler
```

### Via Test Runner
```bash
# Integration level tests (includes websocket tests)
python test_runner.py --level integration --no-coverage --fast-fail
```

## Test Requirements

### Performance
- Each test must complete in < 5 seconds
- No mocking of core WebSocket functionality
- Real connections to actual backend services

### Coverage
- Happy path scenarios
- Error conditions and edge cases
- Resource cleanup validation
- Connection state management

### Environment
- Requires running backend service (localhost:8000)
- Requires test database setup
- Uses real JWT tokens for authentication

## Business Value Justification (BVJ)

**Segment**: Growth & Enterprise customers
**Business Goal**: Reliable real-time communication
**Value Impact**: Prevents WebSocket issues affecting user experience
**Revenue Impact**: Ensures real-time features work for paying customers ($99-999/month recurring)

## Compliance

- Follows `SPEC/unified_system_testing.xml`
- Adheres to `SPEC/websockets.xml` requirements
- Implements `SPEC/conventions.xml` patterns
- Maximum 300 lines per test file
- Maximum 8 lines per function (where feasible)

## Integration Points

### Dependencies
- `jwt_token_helpers.py`: JWT token creation and validation
- `real_websocket_client.py`: Real WebSocket client implementation
- `real_client_types.py`: Connection types and configurations

### Test Data
- Uses dynamically generated test users
- Creates temporary connections for isolation
- Implements proper cleanup patterns

## Expected Outcomes

- **Immediate**: Identify and fix critical WebSocket concurrency bugs
- **Short-term**: Achieve 100% coverage of concurrent connection scenarios
- **Long-term**: Stable foundation for multi-user, multi-device support

## Anti-Patterns Avoided

- ❌ Mocking WebSocket connections in integration tests
- ❌ Testing implementation details instead of behavior
- ❌ Overly complex test scenarios for basic functions
- ❌ Silent test failures or auto-passing tests
- ❌ Tests that don't validate real functionality

## Success Metrics

- All tests pass consistently
- Tests execute in < 5 seconds each
- Zero false positives or silent failures
- Real bugs discovered and fixed
- Comprehensive coverage of concurrent scenarios