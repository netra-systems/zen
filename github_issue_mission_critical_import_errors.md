# GitHub Issue: Mission Critical Test Import Errors

## Title
Mission Critical Test Import Errors Preventing E2E and Critical Test Execution

## Labels
bug, test-failure, mission-critical, import-error

## Issue Body

### Summary
Multiple import errors are preventing mission critical test execution, blocking critical test validation for the Golden Path functionality. This impacts our ability to validate the core business value delivery (chat functionality).

### Error Details
When running `python -m pytest tests/mission_critical/ -v --tb=short`, the following import errors occur:

#### 1. WebSocket Manager Import Error
```
ImportError: cannot import name 'get_websocket_manager' from 'netra_backend.app.websocket_core'
```
- **File:** `tests/mission_critical/test_websocket_agent_events_suite.py:6`
- **Impact:** Prevents WebSocket event validation tests

#### 2. VPC Connectivity Module Missing
```
ModuleNotFoundError: No module named 'infrastructure.vpc_connectivity_fix'
```
- **File:** `tests/mission_critical/test_vpc_connectivity.py:3`
- **Impact:** Cannot test VPC connectivity requirements

#### 3. Test User Context Import Error
```
ImportError: cannot import name 'create_test_user_context' from 'netra_backend.app.websocket_core.canonical_import_patterns'
```
- **File:** `tests/mission_critical/test_singleton_removal_phase2.py:8`
- **Impact:** Prevents user isolation validation tests

#### 4. Windows Resource Module Error
```
ModuleNotFoundError: No module named 'resource'
```
- **File:** `tests/mission_critical/test_vpc_connectivity.py:4`
- **Impact:** Windows compatibility issue (resource module is Unix-only)

#### 5. WebSocket Manager Factory Import Error
```
ImportError: cannot import name 'create_websocket_manager' from 'netra_backend.app.websocket_core.websocket_manager_factory'
```
- **File:** `tests/mission_critical/test_websocket_silent_failures.py:7`
- **Impact:** Prevents WebSocket factory pattern tests

### Impact Assessment
- **Test Collection:** 10 errors out of 1046 tests collected
- **Business Impact:** Cannot validate Golden Path user flow (login → AI responses)
- **Critical Functionality Blocked:** WebSocket events, user isolation, VPC connectivity
- **Environment:** Windows 11, Python 3.12.4

### Expected Behavior
All mission critical tests should import successfully and execute to validate:
1. WebSocket agent events (90% of platform value)
2. User isolation and factory patterns
3. VPC connectivity for staging deployment
4. Silent failure prevention

### Reproduction Steps
1. Navigate to project root: `C:\netra-apex`
2. Run: `python -m pytest tests/mission_critical/ -v --tb=short`
3. Observe import errors preventing test execution

### Priority
**High Priority** - These are mission critical tests that validate core business functionality and Golden Path user flow.

### Related Documentation
- `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md` - Complete user journey requirements
- `CLAUDE.md` - Golden Path priority: users login → get AI responses
- `reports/DEFINITION_OF_DONE_CHECKLIST.md` - WebSocket module requirements

### Environment Details
- **OS:** Windows 11
- **Python:** 3.12.4
- **Branch:** develop-long-lived
- **Working Directory:** C:\netra-apex

### Command Used
```bash
python -m pytest tests/mission_critical/ -v --tb=short
```

### Next Steps
1. Fix import paths for WebSocket manager functions
2. Create or fix missing infrastructure modules
3. Address Windows compatibility issues
4. Validate all mission critical tests can execute
5. Ensure Golden Path validation is functional