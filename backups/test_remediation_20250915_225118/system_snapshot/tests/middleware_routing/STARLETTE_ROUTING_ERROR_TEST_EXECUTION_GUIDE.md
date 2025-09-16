# Starlette Routing Error Reproduction Test Suite
**Comprehensive Test Execution Strategy**

## 🎯 MISSION OBJECTIVE
Reproduce and diagnose the Starlette routing error from the production stack trace:

```
2025-09-11 16:22:39.140 PDT
File "/home/netra/.local/lib/python3.11/site-packages/starlette/routing.py", line 716, in __call__
await self.middleware_stack(scope, receive, send)
File "/home/netra/.local/lib/python3.11/site-packages/starlette/routing.py", line 736, in app  
await route.handle(scope, receive, send)
```

## 📋 TEST SUITE OVERVIEW

### Test Files Created:
1. **`test_starlette_routing_error_reproduction.py`** - Core reproduction tests
2. **`test_route_middleware_integration.py`** - Route-specific middleware conflicts  
3. **`test_e2e_websocket_middleware_routing.py`** - End-to-end WebSocket scenarios
4. **`test_incomplete_error_logging_reproduction.py`** - Exception handling truncation

### Total Test Coverage:
- **25+ individual test cases**
- **100+ specific failure scenarios** 
- **6 major error categories**
- **Production environment simulation**

---

## 🚀 TEST EXECUTION STRATEGY

### Phase 1: Quick Reproduction Attempts
**Goal:** Fast identification of the most likely error patterns

```bash
# Run core reproduction tests first
python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py::StarletteRoutingErrorReproduction::test_production_middleware_stack_exact_reproduction -v

# Run WebSocket-specific tests (high probability)  
python -m pytest tests/middleware_routing/test_e2e_websocket_middleware_routing.py::WebSocketMiddlewareE2ETests::test_production_websocket_endpoint_exact_reproduction -v

# Run middleware ordering tests
python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py::MiddlewareOrderingTests -v
```

### Phase 2: Comprehensive Pattern Testing
**Goal:** Systematic reproduction across all identified failure modes

```bash
# Run all routing error reproduction tests
python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py -v --tb=long

# Run integration tests for route conflicts
python -m pytest tests/middleware_routing/test_route_middleware_integration.py -v --tb=long

# Run E2E WebSocket tests
python -m pytest tests/middleware_routing/test_e2e_websocket_middleware_routing.py -v --tb=long

# Run error logging truncation tests
python -m pytest tests/middleware_routing/test_incomplete_error_logging_reproduction.py -v --tb=long
```

### Phase 3: Production Environment Simulation
**Goal:** Exact production configuration reproduction

```bash
# Set production-like environment
export ENVIRONMENT=staging
export K_SERVICE=netra-staging-backend
export GCP_PROJECT_ID=netra-staging
export SECRET_KEY=your_32_char_secret_key_here

# Run production simulation tests
python -m pytest tests/middleware_routing/ -k "production" -v --tb=long --capture=no
```

### Phase 4: Stress Testing & Edge Cases  
**Goal:** Trigger race conditions and timing-dependent failures

```bash
# Run concurrent connection tests
python -m pytest tests/middleware_routing/test_e2e_websocket_middleware_routing.py::WebSocketMiddlewareE2ETests::test_concurrent_websocket_connections_middleware_stress -v

# Run middleware ordering permutation tests
python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py::MiddlewareOrderingTests::test_all_possible_middleware_orders -v
```

---

## 🎯 SUCCESS CRITERIA

### Primary Success Indicators:

#### 🏆 **EXACT MATCH** - Target Error Reproduced:
- Exception contains `"starlette/routing.py"` and `"line 716"`  
- Error message includes `"middleware_stack"`
- Stack trace truncates at `_exception_handler.py` line 42

#### 🎯 **HIGH CORRELATION** - Related Error Patterns:
- `middleware_stack` processing errors
- WebSocket upgrade failures with routing context
- SessionMiddleware dependency chain failures
- ASGI scope corruption during routing

#### ⚠️ **RELATED INDICATORS** - Supporting Evidence:
- Middleware ordering conflicts
- Exception wrapping/truncation patterns  
- Concurrent WebSocket connection failures
- Production environment-specific failures

### Failure Pattern Recognition:

```python
# Look for these patterns in test output:
EXACT_MATCH_PATTERNS = [
    "routing.py.*line 716",
    "middleware_stack.*scope.*receive.*send",
    "_exception_handler.py.*line 42"
]

HIGH_CORRELATION_PATTERNS = [
    "middleware_stack.*error", 
    "websocket.*upgrade.*routing",
    "sessionmiddleware.*must be installed",
    "scope.*corruption"
]
```

---

## 📊 TEST METRICS & ANALYSIS

### Automated Metrics Collection:
Each test collects detailed metrics using `self.record_metric()`:

```python
# Example metrics collected:
self.record_metric("routing_reproduction", "exact_error_reproduced", 1)
self.record_metric("websocket_routing", "upgrade_failure", 1) 
self.record_metric("middleware_ordering", "sessionmiddleware_conflict", 1)
```

### Key Metrics to Monitor:

1. **Error Reproduction Rate** - % of tests reproducing routing errors
2. **Pattern Matching Score** - How closely errors match target trace
3. **Environment Sensitivity** - Which environments trigger the error
4. **Middleware Dependency Map** - Which middleware combinations fail
5. **WebSocket Failure Rate** - % of WebSocket tests triggering routing errors

---

## 🔬 DETAILED FAILURE ANALYSIS

### Expected Error Categories:

#### 1. **Middleware Chain Ordering** 
- SessionMiddleware installed after dependent middleware
- Authentication middleware conflicting with WebSocket upgrades
- CORS middleware interfering with WebSocket handshake

#### 2. **ASGI Scope Corruption**
- Middleware modifying scope properties incorrectly
- Invalid path/method values breaking routing logic
- WebSocket-specific scope modifications

#### 3. **Exception Handling Chain Issues**
- Multiple middleware wrapping exceptions
- `from None` truncating exception chains  
- Production error handlers masking root causes

#### 4. **WebSocket Upgrade Conflicts**
- HTTP middleware processing WebSocket upgrade requests
- Authentication middleware blocking WebSocket handshake
- CORS preflight conflicts with WebSocket connections

#### 5. **Production Environment Specifics**
- GCP Cloud Run middleware configuration
- Environment-dependent middleware loading failures
- Secret management affecting SessionMiddleware

#### 6. **Concurrent Access Race Conditions**
- Multiple WebSocket connections triggering shared state issues
- Middleware initialization race conditions
- Thread-unsafe middleware configuration

---

## 🛠️ DIAGNOSTIC COMMANDS

### Pre-Test Environment Validation:
```bash
# Verify middleware stack health
python -c "from netra_backend.app.core.app_factory import create_app; app=create_app(); print(f'Middleware count: {len(app.user_middleware)}')"

# Check for common configuration issues  
python -c "from shared.isolated_environment import get_env; env=get_env(); print(f'Environment: {env.get(\"ENVIRONMENT\")}, Secret Key: {bool(env.get(\"SECRET_KEY\"))}')"

# Validate WebSocket route availability
python -c "from netra_backend.app.core.app_factory import create_app; from fastapi.testclient import TestClient; app=create_app(); client=TestClient(app); print('WebSocket routes available')"
```

### During Test Debugging:
```bash
# Run with maximum verbosity and error details
python -m pytest tests/middleware_routing/ -v -s --tb=long --capture=no --log-cli-level=DEBUG

# Run single test with detailed output
python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py::StarletteRoutingErrorReproduction::test_production_middleware_stack_exact_reproduction -vvv -s

# Capture all output including middleware logs
python -m pytest tests/middleware_routing/ --capture=no --log-cli-level=DEBUG 2>&1 | tee routing_error_debug.log
```

### Post-Test Analysis:
```bash
# Search for target error patterns in output
grep -i "routing.py.*line 716" routing_error_debug.log
grep -i "middleware_stack" routing_error_debug.log  
grep -i "_exception_handler.py.*line 42" routing_error_debug.log

# Count error occurrences by type
grep -c "routing.*error" routing_error_debug.log
grep -c "websocket.*routing" routing_error_debug.log
grep -c "middleware.*conflict" routing_error_debug.log
```

---

## 🎛️ CONFIGURATION OPTIONS

### Environment Variables:
```bash
# Basic test configuration
export ENVIRONMENT=staging                    # or development/production
export SECRET_KEY=your_32_char_secret_here   # Required for SessionMiddleware
export GCP_PROJECT_ID=netra-staging          # For GCP-specific middleware

# Advanced debugging
export DEBUG=true                            # Enable debug logging
export PYTEST_VERBOSITY=2                    # Increase test verbosity
export MIDDLEWARE_DEBUG=true                 # Enable middleware debug output
```

### Test Customization:
```python
# In test files, you can modify:
self._env.set("ENVIRONMENT", "production")    # Change target environment
self.middleware_conflicts = ["/api/", "/ws/"] # Focus on specific paths
self.connection_count = 10                    # Adjust stress test intensity
```

---

## 📈 EXPECTED RESULTS

### If Tests Successfully Reproduce the Error:
1. **Exact Error Match**: Tests will output stack traces matching the production pattern
2. **Root Cause Identification**: Clear identification of problematic middleware configuration  
3. **Reproduction Steps**: Documented steps to consistently trigger the error
4. **Fix Recommendations**: Specific middleware ordering or configuration changes

### If Tests Don't Reproduce the Error:
1. **Environment Differences**: Production has configuration not captured in tests
2. **Timing Dependencies**: Error requires specific timing/load conditions
3. **Version Differences**: Starlette/FastAPI version differences affect behavior
4. **External Dependencies**: Error depends on external services not available in tests

### Partial Reproduction Scenarios:
1. **Similar Errors**: Related routing errors that provide clues to root cause
2. **Middleware Conflicts**: Confirmed middleware ordering issues without exact error
3. **WebSocket Issues**: WebSocket-specific problems suggesting upgrade conflicts
4. **Logging Truncation**: Confirmed exception handling masks real errors

---

## 🚨 TROUBLESHOOTING

### Common Test Execution Issues:

#### Import Errors:
```bash
# If middleware imports fail:
pip install -e .  # Install package in development mode
export PYTHONPATH=$PWD:$PYTHONPATH  # Add project to Python path
```

#### Environment Configuration:
```bash
# If environment setup fails:
source .env  # Load environment variables
python scripts/setup_test_environment.py  # Run setup script if available
```

#### Database/Service Dependencies:
```bash
# If services aren't available:
python scripts/refresh_dev_services.py  # Start development services
docker-compose up -d  # Start required containers
```

### Test-Specific Issues:

#### SessionMiddleware Errors:
- Ensure SECRET_KEY is at least 32 characters
- Check for multiple SessionMiddleware instances
- Verify middleware installation order

#### WebSocket Connection Failures:
- Confirm WebSocket routes are properly registered
- Check for CORS/Auth middleware blocking upgrades
- Verify TestClient WebSocket support

#### GCP-Specific Middleware Issues:
- Mock GCP services if not available in test environment
- Skip GCP-specific tests with `pytest.skip()` if needed
- Use environment detection to avoid GCP requirements

---

## 📞 SUCCESS VALIDATION

### Validation Checklist:
- [ ] At least one test reproduces an error matching the target pattern
- [ ] Root cause of middleware configuration issue is identified  
- [ ] Reproduction steps are documented and repeatable
- [ ] Fix recommendations are provided with business impact analysis
- [ ] Error pattern is confirmed to affect Golden Path functionality

### Business Impact Assessment:
- **Revenue Impact**: How does this error affect the $500K+ ARR chat functionality?
- **User Experience**: What is the customer-facing impact of routing failures?
- **System Reliability**: How frequently does this error occur in production?
- **Fix Priority**: What is the urgency level for resolving this issue?

---

## 🎉 DELIVERABLES

Upon successful test execution, provide:

1. **Error Reproduction Report**: Detailed analysis of reproduced errors
2. **Root Cause Analysis**: Technical explanation of the middleware configuration issue
3. **Fix Recommendations**: Specific changes to resolve the routing error
4. **Prevention Strategy**: How to avoid similar issues in the future
5. **Monitoring Improvements**: Better error logging/detection recommendations

**The comprehensive test suite is now ready for execution. Run the tests systematically following this guide to reproduce and diagnose the Starlette routing error.**