# Critical Test Runner

## Overview

The Critical Test Runner (`run_all_critical_tests.py`) is a production readiness validation tool that runs the most important tests for the Netra Apex platform. It validates critical user journeys and system functionality before deployment.

## Business Value

- **Protects $597K+ MRR** by preventing production failures
- **Validates complete user journeys** from signup to chat functionality  
- **Ensures system stability** across all microservices
- **Provides deployment confidence** with clear pass/fail criteria

## Usage

### Basic Usage

```bash
# Run all critical tests
python tests/unified/e2e/run_all_critical_tests.py

# List all configured critical tests
python tests/unified/e2e/run_all_critical_tests.py --list

# Show what would be run without executing
python tests/unified/e2e/run_all_critical_tests.py --dry-run
```

### Priority-Based Testing

```bash
# Run only P0 (Critical) tests
python tests/unified/e2e/run_all_critical_tests.py --priority P0

# Run only P1 (High) priority tests
python tests/unified/e2e/run_all_critical_tests.py --priority P1

# Run only P2 (Medium) priority tests
python tests/unified/e2e/run_all_critical_tests.py --priority P2
```

## Test Priorities

### P0 - CRITICAL (Must Pass for Production)
1. **Auth Integration Fixed** - Complete signup to chat user journey
2. **WebSocket Auth Integration** - Real-time communication with auth
3. **Cross-Service Auth Sync** - JWT validation across services
4. **Auth Service Independence** - Standalone auth service operation
5. **Database Sync Fixed** - Database consistency across services
6. **Health Cascade Prevention** - Service health and failure prevention

### P1 - HIGH (Important for User Experience)
7. **Session Persistence Fixed** - User session management
8. **Concurrent User Isolation** - Multi-user data isolation
9. **WebSocket Message Format** - Message structure validation
10. **Agent Lifecycle Events** - Agent execution WebSocket events

### P2 - MEDIUM (Nice to Have)
11. **Rate Limiting** - Rate limiting enforcement
12. **OAuth Integration** - OAuth login flow

## Exit Codes

- **0** - All critical tests passed (production ready)
- **1** - Critical test failures detected (do not deploy)
- **130** - User interrupted execution
- **1** - Fatal error occurred

## Output

The script provides:

1. **Real-time progress** - Shows each test as it runs
2. **Immediate feedback** - Pass/fail status with timing
3. **Comprehensive summary** - Overall results and business impact
4. **Detailed report** - JSON report saved to `test_reports/critical_tests_results.json`
5. **Deployment recommendation** - Clear deploy/don't deploy guidance

## Example Output

```
Netra Apex Critical Test Runner
   Validating production readiness...
Starting Critical Test Execution
Project Root: /path/to/netra-core-generation-1
Running 12 critical tests

[1/12] [TEST] Running: Auth Integration Fixed
   Priority: P0 - Complete user journey from signup to chat
   [PASS] PASSED in 5.2s

...

================================================================================
CRITICAL TESTS EXECUTION SUMMARY
================================================================================
[SUCCESS] PRODUCTION READY - ALL CRITICAL TESTS PASSED

Test Results:
   Total Tests: 12
   [PASS] Passed: 12
   [FAIL] Failed: 0
   [TIME] Timeout: 0
   [ERROR] Error: 0
   [SKIP] Skipped: 0
   Success Rate: 100.0%

Critical Tests (P0):
   [PASS] Passed: 6
   Total: 6
   Critical Success Rate: 100.0%

Business Impact:
   [PROTECTED] $597K+ MRR protected
   [VALIDATED] User journey validated
   [STABLE] Production stability assured

Deployment Status: [DEPLOY] READY FOR DEPLOYMENT
================================================================================

[SUCCESS] All critical tests passed - Production ready!
```

## Integration with CI/CD

The script is designed for CI/CD integration:

- **Clear exit codes** for automated decision making
- **JSON reports** for further processing
- **Timeout handling** prevents hanging builds
- **Parallel execution** for speed

## Test Configuration

Critical tests are configured in the script with:

- **Priority level** (P0/P1/P2)
- **Test file path** or specific test method
- **Description** of what the test validates
- **Timeout settings** for reliability

## Troubleshooting

### Common Issues

1. **Test timeouts** - Services may not be running
2. **Import errors** - Dependencies may not be installed
3. **Connection failures** - Database/service connectivity issues

### Prerequisites

- All services running (Auth, Backend, Frontend)
- Database connections available
- Test dependencies installed
- Proper environment configuration

## Maintenance

The test configuration should be updated when:

- New critical paths are identified
- Test files are renamed or moved
- Priority levels change
- New services are added

## Related Files

- `CRITICAL_INTEGRATION_TEST_PLAN.md` - Detailed test implementation plan
- `run_all_e2e_tests.py` - General E2E test runner
- `test_critical_unified_flows.py` - Core critical test implementations