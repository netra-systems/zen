# Issue #517 Comprehensive Test Plan - Staging Service Outage and WebSocket Testing

**Issue**: E2E-DEPLOY-websocket-http500-staging-websocket-events (P0 Critical)  
**Status**: EVOLVED SCOPE - From HTTP 500 WebSocket errors to complete staging backend unavailability (HTTP 503)  
**Created**: 2025-09-12  
**Priority**: P0 Critical - Affects $500K+ ARR chat functionality  

## Executive Summary

Issue #517 has evolved from WebSocket-specific HTTP 500 errors to a complete staging backend service outage (HTTP 503). Root cause identified as missing `redis` module import in `/netra_backend/app/services/tool_permissions/rate_limiter.py` causing application startup failure.

### Current Status
- **Staging Backend**: HTTP 503 Service Unavailable
- **Root Cause**: `NameError: name 'redis' is not defined` in rate_limiter.py line 22
- **Impact**: Complete staging environment unavailable for WebSocket testing
- **Fix Status**: Import fix applied, awaiting redeployment

## Test Plan Strategy

### Phase 1: Infrastructure Diagnosis and Recovery (IMMEDIATE)

#### 1.1 Root Cause Validation Tests
**Objective**: Confirm the import fix resolves the staging outage

1. **Local Import Validation Test**
   ```bash
   # Validate rate_limiter.py imports without errors
   python -c "from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter; print('Import successful')"
   ```

2. **Local Backend Startup Test**
   ```bash
   # Test backend can start with the fix
   cd netra_backend && python -m netra_backend.app.main
   ```

3. **Staging Redeployment Test**
   ```bash
   # Deploy fixed version to staging
   python scripts/deploy_to_gcp.py --project netra-staging --build-local
   ```

#### 1.2 Staging Service Recovery Validation
**Objective**: Verify staging backend returns to operational state

1. **Health Endpoint Test**
   ```bash
   curl -w "%{http_code}\n" https://api.staging.netrasystems.ai/health
   # Expected: 200 (not 503)
   ```

2. **Service Startup Logs Validation**
   ```bash
   gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="netra-backend-staging"' --project netra-staging --limit 10 --freshness=10m
   # Expected: No NameError: name 'redis' is not defined
   ```

### Phase 2: WebSocket Connectivity Tests (POST-RECOVERY)

#### 2.1 Original Failing Tests Execution
**Objective**: Re-run the original failing WebSocket tests from Issue #517

1. **test_websocket_event_flow_real**
   ```bash
   python -m pytest tests/e2e/staging/ -k "test_websocket_event_flow_real" --env staging -v
   ```

2. **test_concurrent_websocket_real** 
   ```bash
   python -m pytest tests/e2e/staging/ -k "test_concurrent_websocket_real" --env staging -v
   ```

#### 2.2 WebSocket Handshake and ASGI Scope Tests
**Objective**: Validate HTTP 500 ASGI scope errors are resolved

1. **WebSocket Upgrade Handshake Test**
   ```python
   # Create test: tests/integration/test_websocket_handshake_staging.py
   async def test_websocket_handshake_succeeds():
       """Test WebSocket upgrade handshake completes without ASGI errors."""
       import websockets
       uri = "wss://api.staging.netrasystems.ai/ws"
       try:
           async with websockets.connect(uri) as websocket:
               # Test successful connection
               assert websocket.open
       except websockets.exceptions.InvalidStatusCode as e:
           pytest.fail(f"WebSocket handshake failed: {e}")
   ```

2. **ASGI Scope Validation Test**
   ```python
   # Validate ASGI scopes are properly handled
   async def test_websocket_asgi_scope_handling():
       """Test WebSocket requests have proper ASGI scope."""
       # Test WebSocket connections don't trigger HTTP 500 ASGI errors
   ```

#### 2.3 Golden Path WebSocket Events Tests  
**Objective**: Verify all 5 critical WebSocket events work in staging

1. **Agent WebSocket Events Integration Test**
   ```bash
   python tests/mission_critical/test_websocket_agent_events_suite.py --env staging
   ```

2. **Complete Agent Flow Test**
   ```python
   # Test all 5 events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
   async def test_golden_path_websocket_events_staging():
       """Test complete agent execution with all WebSocket events in staging."""
   ```

### Phase 3: Environment Variable Impact Tests

#### 3.1 PR #524 Environment Consolidation Validation
**Objective**: Ensure environment variable changes didn't break configuration

1. **NEXT_PUBLIC_WS_URL Configuration Test**
   ```bash
   # Verify WebSocket URL configuration is correct
   echo $NEXT_PUBLIC_WS_URL
   # Expected: wss://api.staging.netrasystems.ai/ws
   ```

2. **Backend Environment Variables Test**
   ```python
   # Test staging environment loads correctly
   from netra_backend.app.core.configuration.base import get_config
   config = get_config("staging")
   assert config.websocket_url == "wss://api.staging.netrasystems.ai/ws"
   ```

#### 3.2 SSOT Configuration Compliance Test
**Objective**: Verify SSOT changes didn't introduce configuration conflicts

1. **Configuration SSOT Validation**
   ```bash
   python scripts/check_architecture_compliance.py --focus configuration
   ```

2. **Import Registry Validation**
   ```bash
   python -c "from SSOT_IMPORT_REGISTRY import validate_imports; validate_imports()"
   ```

### Phase 4: Regression Prevention Tests

#### 4.1 Import Dependency Tests
**Objective**: Prevent similar import-related startup failures

1. **All Critical Imports Test**
   ```bash
   # Test all critical service imports
   python scripts/validate_all_imports.py --service netra_backend
   ```

2. **Redis Client Import Test**
   ```python
   # Specific test for Redis-related imports
   def test_redis_imports_complete():
       """Test all Redis-related imports work correctly."""
       from netra_backend.app.services.redis_client import get_redis_client
       from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
       # Should not raise ImportError
   ```

#### 4.2 Startup Process Validation
**Objective**: Ensure deterministic startup sequence works

1. **Application Factory Test**
   ```python
   def test_app_factory_creates_app():
       """Test application factory creates app without import errors."""
       from netra_backend.app.core.app_factory import create_app
       app = create_app()
       assert app is not None
   ```

2. **Route Registration Test**
   ```python
   def test_route_registration_completes():
       """Test all routes register without import errors."""
       # Validate route import chain doesn't break
   ```

## Test Execution Priority

### HIGH PRIORITY (Run First)
1. **Phase 1**: Infrastructure recovery - critical for all other tests
2. **Phase 2.1**: Original failing WebSocket tests - validate Issue #517 resolution
3. **Phase 2.3**: Golden Path events - protect $500K+ ARR functionality

### MEDIUM PRIORITY (Run After High)
1. **Phase 2.2**: ASGI scope validation - technical debt resolution
2. **Phase 3**: Environment variable validation - prevent configuration regressions

### LOW PRIORITY (Run for Completeness)
1. **Phase 4**: Regression prevention - technical improvement

## Success Criteria

### ✅ CRITICAL SUCCESS CRITERIA (Must Pass)
- [ ] Staging backend returns HTTP 200 on /health endpoint
- [ ] `test_websocket_event_flow_real` passes in staging environment  
- [ ] `test_concurrent_websocket_real` passes in staging environment
- [ ] All 5 WebSocket events delivered: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- [ ] No ASGI scope-related HTTP 500 errors in staging logs

### ✅ IMPORTANT SUCCESS CRITERIA (Should Pass)
- [ ] WebSocket handshake completes successfully
- [ ] Environment variable configuration loads correctly
- [ ] SSOT compliance maintained
- [ ] No import-related startup errors

### ✅ NICE-TO-HAVE SUCCESS CRITERIA (Bonus)
- [ ] All regression prevention tests pass
- [ ] Import validation covers all critical services
- [ ] Startup process fully deterministic

## Risk Assessment

### HIGH RISK
- **Staging remains down**: If import fix doesn't work, WebSocket testing blocked
- **Configuration drift**: Environment changes may have introduced other issues

### MEDIUM RISK  
- **Test environment differences**: Local fixes may not reflect staging behavior
- **Race conditions**: WebSocket tests may still have timing issues

### LOW RISK
- **Test framework issues**: Unified test runner syntax issues are non-critical
- **Performance impact**: Import changes should not affect performance

## Execution Timeline

### Immediate (0-2 hours)
- [ ] Apply import fix and redeploy staging
- [ ] Validate staging service recovery
- [ ] Run original failing WebSocket tests

### Short-term (2-8 hours)  
- [ ] Complete WebSocket connectivity validation
- [ ] Run Golden Path WebSocket events tests
- [ ] Validate environment variable configuration

### Medium-term (1-2 days)
- [ ] Complete regression prevention tests
- [ ] Update test documentation
- [ ] Create monitoring for similar issues

## Test Environment Requirements

### Infrastructure
- **GCP Staging Environment**: Primary test target
- **No Docker Dependency**: Focus on staging GCP remote services
- **Real Services Only**: No mocks - validate actual system behavior

### Access Requirements
- GCP staging project access
- Staging environment credentials
- WebSocket test client capabilities

### Monitoring
- GCP Cloud Run logs access
- Health endpoint monitoring
- WebSocket connection monitoring

---

## Post-Testing Documentation

After test completion, update:
- [ ] Issue #517 with test results
- [ ] Master WIP Status with staging health
- [ ] Test execution guide with lessons learned
- [ ] Import validation procedures

**This test plan prioritizes restoring staging functionality first, then validating the original WebSocket issues are resolved, ensuring business continuity while addressing technical debt.**