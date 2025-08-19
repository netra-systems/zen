# Critical Unified Tests Runner

## Overview

The Critical Unified Tests Runner executes the 10 most critical E2E tests that validate the core functionality of the Netra Apex platform. These tests ensure that essential user journeys work correctly with real services.

## Business Value

- **Revenue Impact**: $500K+ MRR (Critical path validation for enterprise customers)
- **Segment**: Enterprise + Mid-tier
- **Goal**: Comprehensive real-service integration validation
- **Strategic Impact**: System reliability directly impacts customer retention and enterprise sales

## The 10 Critical Tests

1. **OAuth Endpoint Validation** (`test_oauth_endpoint_validation_real.py`)
   - Tests OAuth endpoints across Auth, Backend, Frontend with real service communication
   - Validates Google OAuth integration and token exchange

2. **WebSocket Auth Multi-Service** (`test_websocket_auth_multiservice.py`)
   - Tests WebSocket authentication across multiple services
   - Validates real-time communication security

3. **Complete OAuth Chat Journey** (`test_complete_oauth_chat_journey.py`)
   - End-to-end user journey from OAuth login to chat functionality
   - Critical user experience validation

4. **JWT Cross-Service Validation** (`test_jwt_cross_service_validation.py`)
   - Tests JWT token validation across Auth and Backend services
   - Ensures secure service-to-service communication

5. **WebSocket Concurrent Ordering** (`test_websocket_concurrent_ordering.py`)
   - Tests message ordering under concurrent load
   - Critical for real-time chat reliability

6. **Auth Service Recovery** (`test_auth_service_recovery.py`)
   - Tests system recovery when Auth service fails/restarts
   - Ensures system resilience

7. **Database User Sync** (`test_database_user_sync.py`)
   - Tests user data synchronization between Auth and Backend databases
   - Critical for data consistency

8. **Rate Limiting Unified Real** (`test_rate_limiting_unified_real.py`)
   - Tests rate limiting across all services with real traffic
   - Protects against abuse and ensures fair usage

9. **Session Persistence Restart Real** (`test_session_persistence_restart_real.py`)
   - Tests session persistence across service restarts
   - Critical for user experience continuity

10. **Multi-Session Management** (`test_multi_session_management.py`)
    - Tests handling of multiple concurrent user sessions
    - Essential for enterprise multi-user scenarios

## Usage

### Quick Start

**Windows:**
```cmd
run_critical_tests.bat
```

**Unix/Linux/macOS:**
```bash
./run_critical_tests.sh
```

### Python Direct

```bash
python tests/unified/e2e/run_critical_unified_tests.py
```

### Advanced Options

```bash
# Skip service startup (if services already running)
python tests/unified/e2e/run_critical_unified_tests.py --skip-service-start

# Custom output file
python tests/unified/e2e/run_critical_unified_tests.py --output /path/to/results.json

# Quiet mode (less verbose output)
python tests/unified/e2e/run_critical_unified_tests.py --quiet
```

## Service Requirements

The runner requires the following services to be available:

1. **Auth Service** (port 8081 or 8083)
   - Health endpoint: `http://localhost:8081/health`
   - Alternative: `http://localhost:8083/health`

2. **Backend Service** (port 8000)
   - Health endpoint: `http://localhost:8000/health/`

The runner will automatically:
- Check if services are already running
- Start services if needed using `RealServicesManager`
- Validate service health before running tests
- Clean up services after tests complete

## Output and Reporting

### Console Output

The runner provides real-time progress updates and a comprehensive summary:

```
================================================================================
CRITICAL UNIFIED TESTS - EXECUTION SUMMARY
================================================================================
Total Tests: 10
Passed: 8
Failed: 2
Success Rate: 80.0%
Total Duration: 245.3s
Services Started: Yes
Timestamp: 2025-08-19T16:30:45.123456+00:00

TEST NAME                                STATUS     DURATION  
------------------------------------------------------------
test_oauth_endpoint_validation_real.py   PASSED     24.5s     
test_websocket_auth_multiservice.py      FAILED     18.2s     
    Error: Connection timeout after 15s
...

Enterprise SLA Compliance (95%): ✗ FAIL
================================================================================
```

### JSON Output

Detailed results are saved to `test_reports/critical_tests_results.json`:

```json
{
  "total_tests": 10,
  "passed_tests": 8,
  "failed_tests": 2,
  "success_rate": 80.0,
  "total_duration": 245.3,
  "results": [
    {
      "name": "test_oauth_endpoint_validation_real.py",
      "passed": true,
      "duration": 24.5,
      "error_message": "",
      "exit_code": 0
    }
  ],
  "services_started": true,
  "timestamp": "2025-08-19T16:30:45.123456+00:00"
}
```

## Enterprise SLA Compliance

The runner checks for **95% success rate** which is required for Enterprise SLA compliance. This ensures:
- System reliability meets enterprise standards
- Critical user journeys are functional
- Platform is ready for production deployment

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed
- **130**: Interrupted by user (Ctrl+C)
- **Other**: Unexpected error during execution

## Architecture

### Key Components

1. **CriticalTestRunner**: Main orchestrator class
2. **TestResult**: Individual test result data structure
3. **TestSuiteResult**: Complete suite execution results
4. **RealServicesManager**: Service lifecycle management
5. **Health Checks**: Service availability validation

### Execution Flow

1. **Service Startup**: Check/start Auth and Backend services
2. **Health Validation**: Ensure all services are responding
3. **Parallel Execution**: Run tests in controlled batches (max 3 concurrent)
4. **Result Collection**: Gather individual test results
5. **Summary Generation**: Create comprehensive execution report
6. **Service Cleanup**: Stop services if started by runner

### Error Handling

- **Timeout Protection**: 5-minute timeout per test
- **Service Validation**: Pre-execution health checks
- **Graceful Cleanup**: Proper service shutdown
- **Exception Handling**: Comprehensive error reporting

## Troubleshooting

### Common Issues

1. **Services Not Starting**
   - Check if ports 8000, 8081, 8083 are available
   - Verify environment variables are set correctly
   - Ensure Python dependencies are installed

2. **Tests Timing Out**
   - Check service health endpoints
   - Verify database connections
   - Monitor system resources

3. **Import Errors**
   - Ensure PYTHONPATH includes project root
   - Verify all dependencies are installed
   - Check for circular imports

### Debug Mode

For debugging, run with increased verbosity:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG python tests/unified/e2e/run_critical_unified_tests.py

# Run individual test for debugging
python -m pytest tests/unified/e2e/test_oauth_endpoint_validation_real.py -v -s
```

## Development

### Adding New Critical Tests

1. Create test file in `tests/unified/e2e/`
2. Add filename to `_get_critical_test_files()` method
3. Ensure test follows critical test patterns:
   - Real service integration
   - Comprehensive error handling
   - Business value justification
   - ≤8 line functions, <300 lines total

### Modifying Test Execution

The runner uses controlled parallelism (batch size 3) to:
- Avoid resource contention
- Ensure reliable results
- Maintain test isolation
- Provide manageable execution times

## Integration

### CI/CD Pipeline

```yaml
- name: Run Critical Tests
  run: |
    python tests/unified/e2e/run_critical_unified_tests.py
    if [ $? -ne 0 ]; then
      echo "Critical tests failed - blocking deployment"
      exit 1
    fi
```

### Monitoring Integration

The JSON output can be integrated with monitoring systems:
- Success rate tracking
- Performance monitoring
- Alert on SLA violations
- Historical trend analysis

## Performance Characteristics

- **Typical Duration**: 3-5 minutes for all 10 tests
- **Parallel Execution**: 3 tests maximum concurrent
- **Resource Usage**: Moderate (real services required)
- **Reliability**: Designed for CI/CD environments

## Security Considerations

- Uses test environment configurations
- Isolated from production data
- Temporary service instances
- No persistent state modifications