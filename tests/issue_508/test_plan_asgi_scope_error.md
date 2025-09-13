# Issue #508 - GCP ASGI Scope Error Test Plan

## 🚨 CRITICAL: WebSocket ASGI Scope Error Testing Strategy

### Overview
Comprehensive test plan for resolving `'URL' object has no attribute 'query_params'` errors in GCP Cloud Run environment affecting WebSocket functionality and $500K+ ARR chat functionality.

### Error Context
- **Primary Error**: `CRITICAL: ASGI scope error in WebSocket exclusion: 'URL' object has no attribute 'query_params'`
- **Locations**: middleware_setup.py:576, websocket_ssot.py:385, smd.py:878
- **Environment**: GCP Cloud Run staging
- **Impact**: Chat functionality failures (90% of platform value)

---

## 🎯 Phase 1: Unit Tests - ASGI Scope Interface Validation

### Test File: `tests/unit/test_asgi_scope_interface_issue_508.py`

**Purpose**: Validate ASGI scope object interface handling and FastAPI vs Starlette URL object compatibility

#### Test Cases:

1. **test_fastapi_request_url_has_query_params**
   - Create FastAPI Request object
   - Verify `.url.query_params` attribute exists and is accessible
   - Validate query parameter parsing works correctly
   - **Expected**: PASS - FastAPI Request.url should have query_params

2. **test_starlette_url_missing_query_params**
   - Create raw Starlette URL object 
   - Attempt to access `.query_params` attribute
   - **Expected**: FAIL initially (AttributeError) - this reproduces the error
   - Validate fallback to `.query` attribute works

3. **test_websocket_url_object_type_detection**
   - Test different URL object types in WebSocket context
   - Verify attribute detection logic in websocket_ssot.py:385
   - **Expected**: Can differentiate between FastAPI and Starlette URL objects

4. **test_asgi_scope_malformation_scenarios**
   - Simulate malformed ASGI scopes that could cause URL object corruption
   - Test middleware_setup.py URL object handling
   - **Expected**: Graceful degradation without crashes

5. **test_query_params_access_patterns**
   - Test multiple ways to access query parameters safely
   - Validate both `.query_params` and `.query` fallback methods
   - **Expected**: Consistent parameter extraction regardless of URL object type

#### Implementation Strategy:
```python
import pytest
from fastapi import Request, WebSocket
from starlette.datastructures import URL
from unittest.mock import Mock

class TestASGIScopeInterface:
    def test_fastapi_request_url_has_query_params(self):
        # Will PASS - shows working case
        
    def test_starlette_url_missing_query_params(self):
        # Will FAIL initially - reproduces the error
        
    def test_websocket_url_object_type_detection(self):
        # Will FAIL initially if detection logic is flawed
```

---

## 🎯 Phase 2: Integration Tests - WebSocket ASGI Middleware Processing

### Test File: `tests/integration/test_websocket_asgi_middleware_issue_508.py`

**Purpose**: Test WebSocket ASGI middleware processing without Docker dependency

#### Test Cases:

1. **test_websocket_exclusion_middleware_with_malformed_scope**
   - Simulate malformed ASGI scope in WebSocket exclusion middleware
   - Test middleware_setup.py error handling at line 576
   - **Expected**: FAIL initially - reproduces middleware crash

2. **test_websocket_ssot_query_param_extraction**
   - Test websocket_ssot.py query parameter extraction logic
   - Simulate both working and broken URL objects
   - **Expected**: FAIL initially for broken URL objects

3. **test_asgi_scope_passthrough_safety**
   - Test safe ASGI scope passthrough when URL objects are malformed
   - Validate error recovery in middleware stack
   - **Expected**: Graceful degradation without cascading failures

4. **test_websocket_middleware_ordering**
   - Validate middleware processing order doesn't corrupt ASGI scopes
   - Test interaction between different middleware layers
   - **Expected**: Stable scope objects throughout middleware stack

5. **test_gcp_cloud_run_asgi_simulation**
   - Simulate GCP Cloud Run ASGI environment characteristics
   - Test URL object state under Cloud Run conditions
   - **Expected**: FAIL initially if Cloud Run-specific issues exist

#### Implementation Strategy:
```python
from netra_backend.app.core.middleware_setup import WebSocketExclusionMiddleware
from netra_backend.app.routes.websocket_ssot import extract_query_params

class TestWebSocketASGIMiddleware:
    async def test_websocket_exclusion_middleware_with_malformed_scope(self):
        # Will FAIL initially - reproduces middleware error
        
    async def test_websocket_ssot_query_param_extraction(self):
        # Will FAIL initially for malformed URL objects
```

---

## 🎯 Phase 3: Staging GCP E2E Tests - WebSocket Connection Validation

### Test File: `tests/e2e/test_gcp_websocket_asgi_issue_508.py`

**Purpose**: End-to-end validation of WebSocket functionality in GCP staging environment

#### Test Cases:

1. **test_gcp_staging_websocket_connection_establishment**
   - Establish WebSocket connection to GCP staging environment
   - Validate connection succeeds without ASGI scope errors
   - **Expected**: FAIL initially if ASGI scope error persists

2. **test_websocket_auth_flow_with_query_params**
   - Test WebSocket authentication flow with query parameters
   - Validate query parameter parsing in GCP environment
   - **Expected**: FAIL initially if query_params access fails

3. **test_websocket_agent_events_in_gcp**
   - Test complete WebSocket agent event flow in GCP staging
   - Validate all 5 critical events (agent_started, agent_thinking, etc.)
   - **Expected**: FAIL initially if underlying ASGI issues block events

4. **test_websocket_load_under_gcp_conditions**
   - Simulate multiple concurrent WebSocket connections
   - Test ASGI scope handling under load in GCP environment
   - **Expected**: Identify any race conditions or scope corruption issues

5. **test_websocket_error_recovery_in_gcp**
   - Test WebSocket error recovery when ASGI scope errors occur
   - Validate system doesn't cascade fail from single scope error
   - **Expected**: Graceful degradation and recovery

#### Implementation Strategy:
```python
import websockets
import pytest
from test_framework.gcp_integration import GCPStagingEnvironment

class TestGCPWebSocketASGI:
    async def test_gcp_staging_websocket_connection_establishment(self):
        # Will FAIL initially if ASGI error blocks connections
        
    async def test_websocket_auth_flow_with_query_params(self):
        # Will FAIL initially if query_params parsing broken
```

---

## 🎯 Test Execution Strategy

### Phase 1: Quick Feedback Loop (Unit Tests)
```bash
# Run unit tests to validate ASGI scope interface handling
python -m pytest tests/unit/test_asgi_scope_interface_issue_508.py -v

# Expected initial failures to reproduce the error:
# - test_starlette_url_missing_query_params: FAIL (AttributeError)
# - test_websocket_url_object_type_detection: FAIL (logic flaws)
```

### Phase 2: Integration Validation (Non-Docker)
```bash
# Run integration tests for WebSocket ASGI middleware
python -m pytest tests/integration/test_websocket_asgi_middleware_issue_508.py -v

# Expected initial failures:
# - test_websocket_exclusion_middleware_with_malformed_scope: FAIL (middleware crash)
# - test_websocket_ssot_query_param_extraction: FAIL (URL object errors)
```

### Phase 3: End-to-End GCP Validation
```bash
# Run GCP staging tests (requires staging environment)
python -m pytest tests/e2e/test_gcp_websocket_asgi_issue_508.py -v

# Expected initial failures:
# - test_gcp_staging_websocket_connection_establishment: FAIL (ASGI errors)
# - test_websocket_auth_flow_with_query_params: FAIL (query_params access)
```

---

## 🎯 Success Criteria

### Unit Test Success Criteria:
- [ ] All ASGI scope interface tests pass
- [ ] URL object type detection works reliably
- [ ] Query parameter access has proper fallback mechanisms
- [ ] No AttributeError exceptions for missing query_params

### Integration Test Success Criteria:
- [ ] WebSocket middleware handles malformed scopes gracefully
- [ ] ASGI scope passthrough works safely
- [ ] Middleware ordering preserves scope integrity
- [ ] GCP Cloud Run simulation passes without errors

### E2E Test Success Criteria:
- [ ] WebSocket connections establish successfully in GCP staging
- [ ] Authentication flow with query parameters works
- [ ] All 5 critical WebSocket agent events are delivered
- [ ] System handles multiple concurrent connections
- [ ] Error recovery works without cascading failures

---

## 🎯 Root Cause Hypothesis Testing

### Hypothesis 1: Starlette URL Object vs FastAPI Request.url
- **Test**: Compare URL object interfaces in different contexts
- **Validation**: Unit tests for object type detection and attribute access

### Hypothesis 2: Middleware Ordering Corruption
- **Test**: ASGI scope state preservation through middleware stack
- **Validation**: Integration tests for middleware processing order

### Hypothesis 3: GCP Cloud Run Environment Specifics
- **Test**: Simulate Cloud Run ASGI environment characteristics
- **Validation**: E2E tests in actual GCP staging environment

### Hypothesis 4: Async/Concurrency Race Conditions
- **Test**: Multiple concurrent WebSocket connections with ASGI scope access
- **Validation**: Load testing in integration and E2E phases

---

## 🎯 Implementation Timeline

### Immediate (Next 2 hours):
1. Create unit tests that FAIL to reproduce the AttributeError
2. Implement basic ASGI scope interface validation
3. Test URL object type detection logic

### Short-term (Next 4 hours):
1. Build integration tests for WebSocket middleware processing
2. Test ASGI scope handling under various error conditions
3. Validate middleware stack behavior

### Medium-term (Next 6 hours):
1. Deploy E2E tests to validate GCP staging environment
2. Test complete WebSocket flow with authentication
3. Validate error recovery and graceful degradation

---

## 🎯 Business Impact Validation

### Chat Functionality Testing:
- [ ] WebSocket connection establishment
- [ ] Real-time agent event delivery
- [ ] Authentication flow with query parameters
- [ ] Multi-user concurrent sessions
- [ ] Error recovery without service interruption

### Revenue Protection Testing:
- [ ] Validate $500K+ ARR functionality remains operational
- [ ] Test core user workflows end-to-end
- [ ] Ensure no degradation in response quality
- [ ] Verify system stability under normal load

---

**Generated by Claude Code for Issue #508 - GCP ASGI Scope Error Resolution**