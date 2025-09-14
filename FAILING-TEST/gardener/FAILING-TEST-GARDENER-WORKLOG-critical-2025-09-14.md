# Failing Test Gardener Worklog - Critical Tests
**Date**: 2025-09-14  
**Focus**: Critical Tests  
**Status**: In Progress  

## Issues Discovered

### Issue 1: Docker Build and Infrastructure Failures
**Category**: Infrastructure/Docker  
**Severity**: P0 - Critical (Blocking test execution)  
**Description**: Docker build failures preventing test execution
**Details**:
- Docker compose build failing with checksum calculation errors
- Docker disk space warnings
- Affects all test categories requiring Docker services
- Error: `failed to compute cache key: failed to calculate checksum of ref 9x73yk`

**Impact**: 
- Mission critical tests cannot run due to Docker dependency
- Unit tests failing due to infrastructure issues
- Complete test suite execution blocked

**Logs**:
```
WARNING: Failed to build images: backend.alpine.Dockerfile:69
target alpine-test-backend: failed to solve: failed to compute cache key: failed to calculate checksum of ref 9x73yk
```

### Issue 2: SSOT WebSocket Manager Violations
**Category**: SSOT Compliance  
**Severity**: P1 - High (SSOT violations)  
**Description**: Multiple WebSocket Manager classes found
**Details**:
- SSOT WARNING: Found other WebSocket Manager classes
- Multiple protocol and manager implementations exist
- Violates SSOT principles

**Classes Found**:
- netra_backend.app.websocket_core.websocket_manager.WebSocketManagerMode
- netra_backend.app.websocket_core.websocket_manager.WebSocketManagerProtocol
- netra_backend.app.websocket_core.unified_manager.WebSocketManagerMode
- netra_backend.app.websocket_core.protocols.WebSocketManagerProtocol
- netra_backend.app.websocket_core.protocols.WebSocketManagerProtocolValidator

### Issue 3: Unit Test Category Failures
**Category**: Unit Tests  
**Severity**: P1 - High (Test execution failure)  
**Description**: Unit test category failed during execution
**Details**:
- Stopping execution: SkipReason.CATEGORY_FAILED
- Duration: 15.84s before failure
- Mission critical tests skipped due to this failure

### Issue 4: Test Infrastructure Issues
**Category**: Test Infrastructure  
**Severity**: P2 - Medium (Development impact)  
**Description**: Various test infrastructure warnings and issues
**Details**:
- PostgreSQL service not found via port discovery
- Using regular os.environ instead of isolated environment (TEMP_DEBUG warnings)
- Test report generation successful but execution failed

## Next Steps
1. Address Docker build and disk space issues
2. Investigate unit test failures specifically
3. Run individual critical test files to bypass infrastructure issues
4. Document specific test failures for GitHub issue creation

## Test Execution Summary
- Environment: test
- Total Duration: 15.84s
- Categories Executed: 2
- Results:
  - unit: FAILED (15.84s)
  - mission_critical: SKIPPED (0.00s)
- Overall: FAILED