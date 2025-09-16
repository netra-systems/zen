# DEV MODE Integration Tests

Comprehensive integration tests to verify everything works together in DEV MODE.

## Overview

This test suite validates the complete Netra system in development mode, testing:

- **CORS Configuration**: Cross-origin request handling across all services
- **Complete User Journeys**: Login → Message → Response workflows
- **Multi-Service Integration**: Service coordination, health, and error recovery
- **Performance Monitoring**: Resource usage and response time validation
- **WebSocket Communication**: Real-time messaging and connection management

## Test Files

### Core Test Suites

1. **`test_cors_configuration.py`** - CORS validation and endpoint testing
2. **`test_complete_user_journey.py`** - End-to-end user workflow simulation  
3. **`test_multi_service_integration.py`** - Service coordination and monitoring
4. **`dev_mode_integration_utils.py`** - Supporting utilities and helpers

### Test Coverage

Each test file follows the 300-line limit and 8-line function constraints while providing comprehensive coverage:

- ✅ Real service interactions (not mocked)
- ✅ CORS headers and preflight validation
- ✅ Complete user workflows with performance monitoring
- ✅ Service coordination and dependency validation
- ✅ Error recovery and resilience testing
- ✅ Resource management and performance monitoring

## Quick Start

### Prerequisites

1. **Development Environment**: Ensure dev launcher is properly configured
2. **Services Running**: Backend (8000), Auth (8081), Frontend (3001)
3. **Environment Variables**:
   ```bash
   export TESTING=1
   export CORS_ORIGINS="*"
   export ENVIRONMENT=development
   ```

### Running Tests

```bash
# Run all integration tests
python -m pytest tests/unified/e2e/test_cors_configuration.py -v
python -m pytest tests/unified/e2e/test_complete_user_journey.py -v
python -m pytest tests/unified/e2e/test_multi_service_integration.py -v

# Run with coverage
python -m pytest tests/unified/e2e/ --cov=app --cov-report=html

# Run specific test categories
python -m pytest tests/unified/e2e/ -k "cors" -v
python -m pytest tests/unified/e2e/ -k "user_journey" -v
python -m pytest tests/unified/e2e/ -k "service_integration" -v
```

### Using Test Runner

```bash
# Integration level testing
python unified_test_runner.py --level integration --no-coverage --fast-fail

# E2E testing with real services
python unified_test_runner.py --level e2e --env development
```

## Test Structure

### CORS Configuration Tests (`test_cors_configuration.py`)

**Purpose**: Validates CORS configuration across all services to prevent access failures.

**Key Tests**:
- `test_backend_cors_endpoints()` - Tests CORS headers on backend endpoints
- `test_auth_service_cors_endpoints()` - Validates auth service CORS configuration
- `test_preflight_options_requests()` - Tests OPTIONS preflight handling
- `test_websocket_cors_validation()` - WebSocket CORS validation
- `test_cross_service_cors_coordination()` - Multi-service CORS consistency
- `test_cors_performance_monitoring()` - CORS performance impact
- `test_cors_error_scenarios()` - Error handling and recovery

**Configuration**:
```python
CORSTestConfig(
    backend_url="http://localhost:8000",
    auth_url="http://localhost:8081", 
    frontend_url="http://localhost:3001",
    test_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ]
)
```

### Complete User Journey Tests (`test_complete_user_journey.py`)

**Purpose**: Validates complete user workflows from login to chat response.

**Key Tests**:
- `test_single_user_complete_journey()` - Full login → message → response flow
- `test_multi_user_session_isolation()` - Multiple users with session isolation
- `test_error_recovery_scenarios()` - Error handling and recovery across services
- `test_performance_monitoring()` - Performance baseline validation
- `test_service_startup_coordination()` - Service initialization coordination

**Performance Thresholds**:
```python
{
    "login_time": 5.0,           # Login should complete in < 5s
    "websocket_connect": 3.0,    # WebSocket connection < 3s
    "message_response": 10.0,    # Message response < 10s
    "total_journey": 30.0        # Complete journey < 30s
}
```

### Multi-Service Integration Tests (`test_multi_service_integration.py`)

**Purpose**: Tests service coordination, health monitoring, and error recovery.

**Key Tests**:
- `test_service_initialization_sequence()` - Proper service startup order
- `test_service_health_monitoring()` - Comprehensive health validation
- `test_cross_service_communication()` - Inter-service communication patterns
- `test_service_error_recovery()` - Graceful error handling
- `test_performance_under_load()` - Load testing and performance validation
- `test_resource_management()` - Resource usage monitoring

**Service Configuration**:
```python
{
    "backend": ServiceConfig(
        name="backend",
        url="http://localhost:8000", 
        dependencies=["database"]
    ),
    "auth": ServiceConfig(
        name="auth",
        url="http://localhost:8081",
        dependencies=["database"]
    ),
    "frontend": ServiceConfig(
        name="frontend", 
        url="http://localhost:3001",
        dependencies=["backend", "auth"]
    )
}
```

## Utilities (`dev_mode_integration_utils.py`)

### Core Utilities

**CORSTestHelper**: CORS validation and testing utilities
```python
# Validate CORS headers
cors_valid = CORSTestHelper.validate_cors_headers(response.headers, origin)

# Test CORS endpoint
result = await CORSTestHelper.test_cors_endpoint(client, url, origin)
```

**UserSimulator**: Complete user interaction simulation
```python
# Create user simulator
user = UserSimulator("http://localhost:8000", "http://localhost:8081")

# Simulate login
login_result = await user.simulate_login()

# Simulate API requests
api_result = await user.simulate_api_request("/api/threads")

# Execute complete journey
journey_result = await user.simulate_user_journey(journey_steps)
```

**ServiceHealthChecker**: Service monitoring and health validation
```python
# Monitor services
checker = ServiceHealthChecker({
    "backend": "http://localhost:8000",
    "auth": "http://localhost:8081"
})

# Check single service
health = await checker.check_service_health("backend")

# Check all services
summary = await checker.check_all_services()

# Get availability metrics
availability = checker.get_service_availability("backend", time_window_minutes=60)
```

**WebSocketTestHelper**: WebSocket connection testing
```python
# Test WebSocket connection
ws_helper = WebSocketTestHelper("ws://localhost:8000/ws")

# Connect and test
if await ws_helper.connect(auth_token="token"):
    await ws_helper.send_message({"type": "test", "content": "hello"})
    response = await ws_helper.receive_message()
    await ws_helper.disconnect()
```

**PerformanceMonitor**: Performance metrics collection
```python
# Monitor performance
monitor = PerformanceMonitor()

# Time requests
start = monitor.start_request()
# ... make request ...
monitor.end_request(start, success=True)

# Get metrics
metrics = monitor.get_metrics()
print(f"Success rate: {metrics.success_rate():.2%}")
print(f"Average response time: {metrics.avg_response_time:.2f}s")
```

## Error Scenarios

### Common Test Failures

1. **CORS Failures**:
   ```
   AssertionError: Origin http://localhost:3001 not allowed for /auth/config
   ```
   **Solution**: Check CORS_ORIGINS environment variable and service configuration

2. **Service Unavailable**:
   ```
   AssertionError: Service backend not healthy: {'error': 'Connection refused'}
   ```
   **Solution**: Ensure all services are running via dev launcher

3. **Performance Threshold Exceeded**:
   ```
   AssertionError: Login too slow: 7.23s
   ```
   **Solution**: Check system resources and service performance

4. **WebSocket Connection Failures**:
   ```
   AssertionError: WebSocket connection failed: {'error': 'Connection timeout'}
   ```
   **Solution**: Verify WebSocket endpoint configuration and authentication

### Debugging Tips

1. **Enable Verbose Logging**:
   ```bash
   python -m pytest tests/unified/e2e/ -v -s --log-cli-level=DEBUG
   ```

2. **Check Service Health**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8081/health
   curl http://localhost:3001/
   ```

3. **Validate CORS Configuration**:
   ```bash
   curl -H "Origin: http://localhost:3001" -X OPTIONS http://localhost:8000/health
   ```

4. **Monitor Resource Usage**:
   ```bash
   # Check memory/CPU usage during tests
   ps aux | grep python
   ```

## Performance Expectations

### Response Time Targets

- **Health Checks**: < 1 second
- **Auth Operations**: < 5 seconds
- **API Requests**: < 3 seconds  
- **WebSocket Connection**: < 3 seconds
- **Complete User Journey**: < 30 seconds

### Resource Usage Limits

- **Memory per Service**: < 500 MB
- **CPU Usage**: < 80%
- **Availability Target**: > 95%
- **CORS Preflight**: < 1 second

### Load Testing Thresholds

- **Concurrent Users**: 5-10 users
- **Test Duration**: 30 seconds
- **Success Rate**: > 80%
- **Average Response Time**: < 10 seconds

## Integration with CI/CD

### GitHub Actions Integration

```yaml
- name: Run DEV Mode Integration Tests
  run: |
    python -m pytest tests/unified/e2e/test_cors_configuration.py --junit-xml=test-results/cors.xml
    python -m pytest tests/unified/e2e/test_complete_user_journey.py --junit-xml=test-results/journey.xml
    python -m pytest tests/unified/e2e/test_multi_service_integration.py --junit-xml=test-results/integration.xml
```

### Test Runner Integration

```bash
# Fast development feedback
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Complete E2E validation
python unified_test_runner.py --level e2e --real-llm --env staging
```

## Best Practices

### Test Development

1. **Follow 300/8 Rule**: Max 300 lines per file, 8 lines per function
2. **Real Over Mock**: Test real services, minimize mocking
3. **Performance Aware**: Include performance assertions in all tests
4. **Error Recovery**: Test both success and failure scenarios
5. **Resource Cleanup**: Ensure proper cleanup in test teardown

### Test Execution

1. **Service Startup**: Ensure all services are running before tests
2. **Environment Isolation**: Use dedicated test environment variables
3. **Parallel Execution**: Tests are designed for concurrent execution
4. **Resource Monitoring**: Monitor system resources during test runs
5. **Failure Investigation**: Check service logs when tests fail

### Maintenance

1. **Regular Updates**: Update performance thresholds based on system changes
2. **Service Configuration**: Keep service URLs and endpoints current
3. **Error Scenarios**: Add new error scenarios as they're discovered
4. **Performance Baselines**: Update baselines after performance improvements
5. **Documentation**: Keep README updated with new test patterns

## Troubleshooting

### Environment Issues

1. **Check Environment Variables**:
   ```bash
   env | grep -E "(TESTING|CORS_ORIGINS|ENVIRONMENT)"
   ```

2. **Verify Service Status**:
   ```bash
   python scripts/dev_launcher.py --status
   ```

3. **Check Port Availability**:
   ```bash
   netstat -tulpn | grep -E "(8000|8081|3001)"
   ```

### Test-Specific Issues

1. **CORS Test Failures**: Verify middleware configuration and environment variables
2. **User Journey Failures**: Check authentication flow and token generation
3. **Service Integration Failures**: Validate service health and dependencies
4. **Performance Failures**: Monitor system resources and adjust thresholds

### Recovery Procedures

1. **Service Restart**: Restart dev launcher if services are unresponsive
2. **Environment Reset**: Clear environment variables and restart
3. **Cache Clear**: Clear any cached test data or connections
4. **Port Cleanup**: Kill processes using test ports if needed

---

For additional support, see:
- [Testing Specification](../../../SPEC/testing.xml)
- [CORS Configuration](../../../SPEC/cors_configuration.xml)
- [WebSocket Specification](../../../SPEC/websockets.xml)
- [Dev Launcher Guide](../../../dev_launcher/README.md)