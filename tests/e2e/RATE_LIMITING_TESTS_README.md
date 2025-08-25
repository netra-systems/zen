# Comprehensive Rate Limiting Tests

This directory contains comprehensive rate limiting tests for the Netra Apex system, validating rate limiting across all services and components.

## Test Files

### `test_real_rate_limiting.py`
Contains two comprehensive rate limiting tests:

1. **`test_real_rate_limiting_with_redis_backend`** - Original test focusing on basic rate limiting flow
2. **`test_comprehensive_rate_limiting_system`** - Enhanced comprehensive test covering all requirements

### `rate_limiting_core.py`
Core supporting classes for basic rate limiting tests:
- `RedisManager` - Redis operations and counter management
- `MessageSender` - HTTP message sending for rate limit testing
- `UserManager` - User creation and tier management
- `RateLimitFlowValidator` - Validation of rate limiting flows

### `rate_limiting_advanced.py`
Advanced test components for comprehensive rate limiting validation:
- `APIRateLimitTester` - Tests API endpoint rate limits (Auth & Backend)
- `WebSocketRateLimitTester` - Tests WebSocket message rate limits
- `AgentThrottleTester` - Tests agent execution throttling
- `TierBasedRateLimitTester` - Tests Free vs Paid tier limits
- `DistributedRateLimitValidator` - Tests Redis-based distributed rate limiting
- `ResponseHeaderValidator` - Tests 429 responses and retry-after headers

## Test Coverage

The comprehensive rate limiting tests validate:

### 1. API Rate Limits
- **Auth Service Endpoints**: Tests rate limits on `/auth/me` and other auth endpoints
- **Backend API Endpoints**: Tests rate limits on `/api/chat/message` and other backend endpoints
- **Per-User Rate Limiting**: Validates individual user rate limit enforcement
- **Cross-Service Rate Limiting**: Tests rate limits across different services

### 2. WebSocket Rate Limiting
- **Message Rate Limits**: Tests WebSocket message sending rate limits
- **Connection Rate Limits**: Tests WebSocket connection establishment limits
- **Real-Time Rate Limit Responses**: Validates immediate rate limit feedback

### 3. Agent Execution Throttling
- **Agent Request Throttling**: Tests rapid agent execution request throttling
- **Workload-Based Throttling**: Tests throttling based on AI workload intensity
- **Multi-Agent Throttling**: Tests throttling across multiple agent types

### 4. User Tier-Based Rate Limits
- **Free Tier Limits**: Tests restrictive limits for free users
- **Paid Tier Limits**: Tests higher limits for paid users (Pro plan)
- **Tier Upgrade Testing**: Tests limit changes after tier upgrades
- **Conversion Testing**: Validates business logic for tier-based conversions

### 5. Distributed Rate Limiting
- **Redis Backend**: Tests Redis-based rate limit counters
- **Cross-Service Synchronization**: Tests rate limit sharing between services
- **Counter Consistency**: Validates distributed counter accuracy
- **Failover Behavior**: Tests rate limiting during Redis failures

### 6. HTTP Response Validation
- **429 Status Codes**: Tests proper 429 (Too Many Requests) responses
- **Retry-After Headers**: Validates proper Retry-After header values
- **Rate Limit Headers**: Tests X-RateLimit-* headers (Limit, Remaining, Reset)
- **Error Message Quality**: Tests user-friendly error messages

## Prerequisites

### Required Services
- **Redis**: Running on localhost:6379 for distributed rate limiting
- **Auth Service**: Running on localhost:8001
- **Backend Service**: Running on localhost:8000

### Environment Setup
```bash
# Start Redis (if not running)
redis-server

# Start services using dev launcher
python scripts/dev_launcher.py

# Or start services individually:
# Auth Service
cd auth_service && python main.py --host 0.0.0.0 --port 8001

# Backend Service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Running the Tests

### Run Original Rate Limiting Test
```bash
# Run basic rate limiting test
pytest tests/unified/e2e/test_real_rate_limiting.py::test_real_rate_limiting_with_redis_backend -v -s

# With markers
pytest -m "e2e and redis" tests/unified/e2e/test_real_rate_limiting.py::test_real_rate_limiting_with_redis_backend -v -s
```

### Run Comprehensive Rate Limiting Test
```bash
# Run comprehensive rate limiting test
pytest tests/unified/e2e/test_real_rate_limiting.py::test_comprehensive_rate_limiting_system -v -s

# With markers
pytest -m "e2e and redis and comprehensive" tests/unified/e2e/test_real_rate_limiting.py::test_comprehensive_rate_limiting_system -v -s
```

### Run All Rate Limiting Tests
```bash
# Run both tests
pytest tests/unified/e2e/test_real_rate_limiting.py -v -s

# Run with test runner
python test_runner.py --level e2e --include-patterns "*rate_limiting*"
```

## Test Execution Times

- **Basic Test**: ~60-70 seconds (includes 60-second rate limit reset wait)
- **Comprehensive Test**: ~80-90 seconds (covers all components with timeouts)

## Expected Results

### Successful Test Output
```
Testing API rate limits...
Testing WebSocket rate limits...
Testing agent throttling...
Testing tier-based limits...
Testing distributed rate limiting...
Testing 429 response headers...
Comprehensive rate limiting test completed in 85.23s
Test results: {
    'api_limits': {'auth_limited': True, 'backend_limited': True},
    'websocket_limits': {'tested': True, 'limited': True},
    'agent_throttling': {'tested': True, 'throttled': True},
    'tier_limits': {'tested': True, 'free_limited': True, 'paid_higher': True},
    'distributed': {'tested': True, 'synced': True},
    'response_headers': {'tested': True, 'retry_after': True}
}
```

### Business Value Validation
The tests validate critical business requirements:
- **Fair Usage Control**: Prevents infrastructure abuse
- **Tier-Based Conversion**: Drives Free → Paid upgrades
- **System Stability**: Protects against overload
- **User Experience**: Proper error handling and messaging

## Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```
   Redis connection failed: [Errno 111] Connection refused
   ```
   **Solution**: Start Redis server: `redis-server`

2. **Service Not Running**
   ```
   httpx.ConnectError: Connection refused
   ```
   **Solution**: Start required services using `python scripts/dev_launcher.py`

3. **WebSocket Timeout**
   ```
   websockets.exceptions.ConnectionClosed
   ```
   **Solution**: Check WebSocket endpoint configuration and service health

4. **Rate Limits Not Triggered**
   ```
   AssertionError: No API rate limiting detected
   ```
   **Solution**: Check rate limit configuration in middleware and services

### Debug Mode
Run tests with debug output:
```bash
pytest tests/unified/e2e/test_real_rate_limiting.py -v -s --log-cli-level=DEBUG
```

## Integration with Test Runner

The rate limiting tests integrate with the unified test runner:

```bash
# Run as part of E2E test suite
python test_runner.py --level e2e

# Run rate limiting tests specifically
python test_runner.py --level integration --include-patterns "*rate*"
```

## Performance Targets

- **API Rate Limit Detection**: < 5 seconds per service
- **WebSocket Rate Limiting**: < 15 seconds
- **Agent Throttling**: < 10 seconds
- **Tier-based Testing**: < 20 seconds
- **Distributed Validation**: < 5 seconds
- **Header Validation**: < 10 seconds
- **Total Test Time**: < 90 seconds

## Business Impact

These tests protect:
- **$50K+ MRR** through infrastructure cost prevention
- **25-40%** free-to-paid conversion rate through strategic rate limiting
- **System reliability** through abuse prevention
- **User experience** through proper error handling

## Compliance

- **ARCHITECTURAL**: Functions ≤8 lines, files ≤300 lines
- **PERFORMANCE**: Tests complete within time limits
- **RELIABILITY**: Real services, no mocking for critical paths
- **BUSINESS VALUE**: Direct validation of monetization features