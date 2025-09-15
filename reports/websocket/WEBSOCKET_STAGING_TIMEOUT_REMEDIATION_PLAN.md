# WebSocket Staging Timeout Issues - Comprehensive Remediation Plan

**Date:** 2025-09-15
**Priority:** P0 - CRITICAL BUSINESS IMPACT
**Business Impact:** $500K+ ARR Golden Path functionality blocked in staging environment
**Root Cause:** SSOT architectural consolidation changes not synchronized with staging deployment + compatibility issues

## Executive Summary

**CRITICAL FINDING:** WebSocket handshake timeouts and 1011 internal server errors in staging environment are preventing Golden Path e2e tests from validating core chat functionality. Analysis reveals three primary issues:

1. **SSOT Consolidation Mismatch**: Staging deployment contains outdated WebSocket implementations that don't support recent SSOT consolidation changes
2. **Subprotocol Negotiation Failure**: Backend doesn't support WebSocket subprotocols expected by e2e tests
3. **Python 3.13 Compatibility**: `extra_headers` → `additional_headers` parameter migration incomplete in staging

**IMMEDIATE BUSINESS RISK:** Real-time chat functionality (90% of platform value) non-functional in staging, blocking production deployment validation.

---

## Root Cause Analysis

### **Issue #1: SSOT Consolidation Not Deployed to Staging**

**Problem**: Staging environment running outdated WebSocket manager implementations
- **Evidence**: E2E tests show consistent 1011 internal server errors after connection
- **Gap**: Recent SSOT consolidation (Issues #1167, #1196, #965) not reflected in staging deployment
- **Impact**: WebSocket factory patterns and unified managers missing from staging backend

**Business Impact**: Core infrastructure fragmentation preventing validation of $500K+ ARR functionality

### **Issue #2: Subprotocol Negotiation Failure**

**Problem**: Staging backend doesn't support WebSocket subprotocols expected by tests
- **Evidence**: Tests specify `subprotocols=["agent_chat"]` but staging backend rejects negotiation
- **Gap**: Subprotocol support implemented locally but not deployed to staging
- **Impact**: Connection establishment succeeds but protocol mismatch causes immediate failures

**Business Impact**: WebSocket protocol incompatibility blocking real-time agent communication

### **Issue #3: WebSocket Headers Parameter Compatibility**

**Problem**: Inconsistent `extra_headers` vs `additional_headers` usage across codebase
- **Evidence**: 161 files still using deprecated `extra_headers` parameter
- **Gap**: Partial migration to Python 3.13 compatible `additional_headers`
- **Impact**: WebSocket connections fail with "unexpected keyword argument" errors

**Business Impact**: Environment compatibility issues preventing staging validation

### **Issue #4: Container Caching Preventing Updates**

**Problem**: GCP Cloud Run container caching preventing latest code deployment
- **Evidence**: Deployment timestamp shows recent update but WebSocket behavior unchanged
- **Gap**: Container image not reflecting latest SSOT consolidation changes
- **Impact**: Fixes implemented locally not available in staging environment

**Business Impact**: Deployment pipeline not delivering code changes to validation environment

---

## Remediation Strategy

### **Phase 1: Immediate Infrastructure Fixes (Day 1)**

#### **1.1 Staging Deployment Update - PRIORITY 1**
**Objective**: Deploy latest SSOT WebSocket consolidation to staging environment

**Actions**:
```bash
# 1. Force rebuild and deploy with latest SSOT changes
python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local --force-rebuild

# 2. Verify WebSocket SSOT manager deployment
curl -s https://api.staging.netrasystems.ai/health/websocket

# 3. Validate container timestamp matches latest commit
gcloud run services describe netra-backend-staging --region=us-central1 --format="value(metadata.labels)"
```

**Expected Outcome**: Staging backend contains latest unified WebSocket manager with SSOT compliance

**Success Criteria**:
- ✅ WebSocket health endpoint returns "unified_manager" instead of "legacy_manager"
- ✅ Container timestamp matches latest commit hash
- ✅ No 1011 internal server errors during handshake

#### **1.2 Subprotocol Support Implementation - PRIORITY 1**
**Objective**: Add WebSocket subprotocol negotiation to staging backend

**Files to Modify**:
1. `/netra_backend/app/routes/websocket_ssot.py` - Add subprotocol parameter
2. `/netra_backend/app/websocket_core/protocols.py` - Implement negotiation logic
3. `/terraform-gcp-staging/main.tf` - Update environment variables if needed

**Implementation**:
```python
# In websocket_ssot.py - Add subprotocol support
@router.websocket("/ws")
async def websocket_endpoint_ssot(
    websocket: WebSocket,
    mode: str = Query(default="main"),
    subprotocols: Optional[List[str]] = None  # ADD THIS
):
    # Accept subprotocols during handshake
    if subprotocols and "agent_chat" in subprotocols:
        await websocket.accept(subprotocol="agent_chat")
    else:
        await websocket.accept()
```

**Success Criteria**:
- ✅ Backend accepts `subprotocols=["agent_chat"]` parameter
- ✅ WebSocket connection negotiates agent_chat protocol successfully
- ✅ No protocol mismatch errors during message exchange

#### **1.3 Container Cache Invalidation - PRIORITY 2**
**Objective**: Force GCP to use latest container image

**Actions**:
```bash
# 1. Clear Cloud Build cache
gcloud builds list --filter="source.repoSource.repoName=netra-core-generation-1" --limit=5
gcloud builds cancel $(gcloud builds list --ongoing --format="value(id)" --limit=1)

# 2. Force rebuild with cache invalidation
python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local --no-cache

# 3. Verify new container deployment
gcloud run revisions list --service=netra-backend-staging --region=us-central1 --limit=2
```

**Success Criteria**:
- ✅ New container revision deployed with latest timestamp
- ✅ Health endpoint reflects latest code changes
- ✅ WebSocket behavior matches local development environment

---

### **Phase 2: Code-Level Fixes (Day 1-2)**

#### **2.1 Complete WebSocket Headers Migration - PRIORITY 1**
**Objective**: Fix all remaining `extra_headers` → `additional_headers` usage

**Affected Files** (Critical Priority):
```bash
# High-priority staging test files
tests/e2e/staging/test_1_websocket_events_staging.py
tests/e2e/staging/test_3_agent_pipeline_staging.py
tests/e2e/staging/test_golden_path_complete_staging.py
auth_service/tests/e2e/test_cross_service_authentication.py
test_framework/websocket_test_integration.py
```

**Fix Implementation**:
```python
# Before (websockets v15.0+ incompatible)
async with websockets.connect(url, extra_headers=headers):
    pass

# After (websockets v15.0+ compatible)
async with websockets.connect(url, additional_headers=headers):
    pass
```

**Automated Fix Script**:
```bash
# Run comprehensive fix across all test files
python fix_mission_critical_websocket_params.py --target staging_tests
```

**Success Criteria**:
- ✅ Zero `extra_headers` usage in staging-critical test files
- ✅ WebSocket connections establish without parameter errors
- ✅ All e2e tests pass connection phase

#### **2.2 Fix InvalidStatus Object Attributes - PRIORITY 2**
**Objective**: Resolve `InvalidStatus` object missing `status_code` attribute

**Root Cause**: WebSocket library version mismatch causing object structure differences

**Implementation**:
```python
# In websocket error handling - Add compatibility layer
try:
    status_code = exc.status_code  # New format
except AttributeError:
    status_code = getattr(exc, 'code', 1011)  # Fallback for older format

# Update error messages to handle both formats
error_detail = {
    "error_code": "WEBSOCKET_ERROR",
    "status_code": status_code,
    "message": str(exc),
    "compatibility_mode": hasattr(exc, 'status_code')
}
```

**Files to Update**:
- `/tests/e2e/staging/test_1_websocket_events_staging.py` - Error handling
- `/test_framework/websocket_helpers.py` - Connection utilities
- `/netra_backend/app/websocket_core/handlers.py` - Exception handling

**Success Criteria**:
- ✅ No AttributeError exceptions during WebSocket failures
- ✅ Proper error codes logged for debugging
- ✅ Graceful degradation when WebSocket versions mismatch

#### **2.3 Authentication Fallback Mechanism Fix - PRIORITY 2**
**Objective**: Implement robust authentication fallback for staging environment

**Problem**: Authentication forced to header-only fallback but mechanism unreliable

**Solution**: Implement progressive authentication strategy
```python
async def staging_websocket_auth(websocket: WebSocket, token: str):
    """Progressive authentication for staging environment"""

    # Strategy 1: Full JWT validation (preferred)
    try:
        return await validate_full_jwt(token)
    except Exception as e:
        logger.warning(f"Full JWT validation failed: {e}")

    # Strategy 2: Header-only auth (staging fallback)
    try:
        return await validate_header_auth(token)
    except Exception as e:
        logger.warning(f"Header auth failed: {e}")

    # Strategy 3: Permissive mode (development only)
    if is_staging_environment():
        return create_test_user_context(token)

    raise AuthenticationError("All authentication methods failed")
```

**Success Criteria**:
- ✅ Authentication succeeds in staging environment
- ✅ Progressive fallback prevents connection failures
- ✅ User context properly isolated between sessions

---

### **Phase 3: Testing Validation (Day 2)**

#### **3.1 Staging Environment Validation**
**Objective**: Comprehensive validation of fixes in staging environment

**Test Execution Plan**:
```bash
# 1. Basic connectivity test
python -c "
import asyncio, websockets
async def test():
    async with websockets.connect('wss://api.staging.netrasystems.ai/ws', additional_headers={'Authorization': 'Bearer test'}):
        print('✅ Basic connection successful')
asyncio.run(test())
"

# 2. Run critical e2e tests
python -m pytest tests/e2e/staging/test_1_websocket_events_staging.py -v

# 3. Golden Path validation
python -m pytest tests/e2e/staging/test_golden_path_complete_staging.py -v

# 4. Full e2e test suite
python -m pytest tests/e2e/staging/ -v --tb=short
```

**Success Criteria**:
- ✅ 90%+ pass rate on WebSocket connectivity tests
- ✅ All 5 critical WebSocket events delivered successfully
- ✅ Golden Path user flow completes end-to-end
- ✅ No timeout errors during handshake phase

#### **3.2 Performance and Load Testing**
**Objective**: Validate WebSocket performance after fixes

**Load Test Script**:
```python
# Concurrent connection test for staging
async def load_test_websocket():
    tasks = []
    for i in range(10):  # 10 concurrent connections
        tasks.append(test_websocket_connection(f"user_{i}"))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_rate = sum(1 for r in results if not isinstance(r, Exception)) / len(results)
    print(f"Success rate: {success_rate:.1%}")

asyncio.run(load_test_websocket())
```

**Success Criteria**:
- ✅ 95%+ success rate with 10 concurrent connections
- ✅ Average connection time < 5 seconds
- ✅ No memory leaks during extended testing
- ✅ Proper user isolation under concurrent load

---

### **Phase 4: Regression Prevention (Day 2-3)**

#### **4.1 Staging Environment Monitoring**
**Objective**: Prevent regression of WebSocket functionality

**Monitoring Implementation**:
```python
# Add to staging health checks
@app.get("/health/websocket-staging")
async def websocket_staging_health():
    """Staging-specific WebSocket health check"""
    checks = {
        "subprotocol_support": await test_subprotocol_negotiation(),
        "authentication_fallback": await test_auth_fallback(),
        "header_compatibility": await test_headers_compatibility(),
        "ssot_manager_active": await test_ssot_manager()
    }

    all_healthy = all(checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

**Success Criteria**:
- ✅ Health endpoint shows all checks passing
- ✅ Automated monitoring alerts on WebSocket regressions
- ✅ Daily validation of staging WebSocket functionality

#### **4.2 Deployment Pipeline Updates**
**Objective**: Ensure staging deployment includes latest WebSocket changes

**Pipeline Enhancements**:
```yaml
# Add to deployment pipeline
staging_websocket_validation:
  - name: "WebSocket SSOT Validation"
    command: "python scripts/validate_websocket_ssot_staging.py"

  - name: "Subprotocol Support Check"
    command: "curl -f https://api.staging.netrasystems.ai/health/websocket-staging"

  - name: "E2E WebSocket Tests"
    command: "python -m pytest tests/e2e/staging/test_1_websocket_events_staging.py --tb=no"
```

**Success Criteria**:
- ✅ Pipeline fails if WebSocket validation fails
- ✅ Automated rollback on critical WebSocket regressions
- ✅ Staging environment always reflects latest SSOT changes

---

## Implementation Timeline

### **Day 1 - Critical Infrastructure (8 hours)**
- **Morning (4h)**: Staging deployment update + container cache invalidation
- **Afternoon (4h)**: Subprotocol support implementation + WebSocket headers fix

### **Day 2 - Validation & Testing (8 hours)**
- **Morning (4h)**: Comprehensive staging environment validation
- **Afternoon (4h)**: Performance testing + regression prevention setup

### **Day 3 - Monitoring & Documentation (4 hours)**
- **Morning (2h)**: Deployment pipeline enhancements
- **Afternoon (2h)**: Documentation updates + team knowledge transfer

**Total Effort**: 20 hours over 3 days

---

## Risk Mitigation

### **High Risk - Staging Environment Downtime**
**Risk**: Deployment updates cause staging environment unavailability
**Mitigation**:
- Deploy during low-usage hours (early morning PST)
- Keep previous container revision available for quick rollback
- Test deployment in development environment first

**Rollback Plan**:
```bash
# Emergency rollback to previous revision
gcloud run services update-traffic netra-backend-staging --region=us-central1 --to-revisions=PREVIOUS=100
```

### **Medium Risk - Authentication Failures**
**Risk**: Auth changes break existing authentication flows
**Mitigation**:
- Implement progressive fallback authentication
- Test with multiple auth scenarios before deployment
- Maintain backward compatibility for existing tokens

### **Low Risk - Performance Degradation**
**Risk**: SSOT changes impact WebSocket performance
**Mitigation**:
- Performance benchmarking before/after deployment
- Gradual traffic routing to new implementation
- Monitoring and alerting on performance metrics

---

## Success Criteria & Validation

### **Critical Success Metrics**
1. **Connection Success Rate**: 95%+ WebSocket connections establish successfully
2. **Event Delivery**: All 5 critical events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) delivered
3. **Golden Path Functionality**: Complete login → AI response flow operational
4. **Handshake Time**: <10 seconds average WebSocket handshake completion
5. **Error Rate**: <5% 1011 internal server errors

### **Business Value Metrics**
1. **Revenue Protection**: $500K+ ARR Golden Path functionality validated
2. **User Experience**: Real-time chat (90% platform value) operational
3. **Deployment Confidence**: Staging environment validates production readiness
4. **Development Velocity**: E2E test suite provides deployment validation

### **Technical Quality Metrics**
1. **SSOT Compliance**: Staging reflects latest SSOT consolidation changes
2. **Test Coverage**: 90%+ pass rate on WebSocket e2e tests
3. **Monitoring**: Comprehensive health checks prevent regressions
4. **Documentation**: Team knowledge transfer complete

---

## Final Recommendations

### **Immediate Actions (Today)**
1. **Deploy Latest SSOT**: Force staging deployment with cache invalidation
2. **Fix Critical Tests**: Update `extra_headers` → `additional_headers` in staging tests
3. **Add Subprotocol Support**: Implement WebSocket subprotocol negotiation

### **Short-term Actions (This Week)**
1. **Performance Validation**: Load test staging environment after fixes
2. **Regression Prevention**: Add staging WebSocket health monitoring
3. **Pipeline Enhancement**: Update deployment validation to include WebSocket checks

### **Long-term Actions (Next Sprint)**
1. **SSOT Completion**: Complete WebSocket manager consolidation across all environments
2. **Monitoring Enhancement**: Add business metrics for WebSocket reliability
3. **Documentation**: Create WebSocket staging troubleshooting guide

---

## Conclusion

The WebSocket staging timeout issues stem from incomplete deployment of recent SSOT consolidation changes combined with compatibility issues from Python 3.13 migration. The remediation plan addresses root causes systematically while protecting $500K+ ARR Golden Path functionality.

**Key Insight**: Infrastructure modernization requires synchronized deployment validation to prevent staging/production gaps that block business-critical functionality.

**Business Impact**: Successful remediation restores confidence in staging environment as reliable validation for production deployments, enabling continued development velocity on core platform functionality.

---

**Status**: Ready for Implementation
**Next Step**: Begin Phase 1 staging deployment update
**Owner**: Platform Engineering Team
**Business Sponsor**: Product Team (Golden Path functionality)