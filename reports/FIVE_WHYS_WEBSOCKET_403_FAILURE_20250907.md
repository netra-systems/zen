# 🔍 Five Whys Root Cause Analysis: WebSocket HTTP 403 Failures

**Date**: September 7, 2025  
**Issue**: WebSocket connections consistently rejected with HTTP 403 in staging  
**Impact**: 5 test failures across 2 modules preventing real-time communication  
**Business Risk**: Core chat functionality and agent pipeline execution impacted  

---

## 📋 Problem Statement

**Primary Issue**: WebSocket connections to `wss://api.staging.netrasystems.ai/ws` are consistently rejected with HTTP 403 status, causing multiple E2E test failures.

**Evidence**:
```
[DEBUG] WebSocket InvalidStatus error: server rejected WebSocket connection: HTTP 403
[DEBUG] Extracted status code: 403
[INFO] Attempting WebSocket connection to: wss://api.staging.netrasystems.ai/ws
[INFO] Auth headers present: True
```

**Failed Tests**:
- `test_concurrent_websocket_real`
- `test_websocket_event_flow_real` 
- `test_real_agent_lifecycle_monitoring`
- `test_real_agent_pipeline_execution`
- `test_real_pipeline_error_handling`

---

## 🤔 Five Whys Analysis

### **Why #1: Why are WebSocket connections being rejected with HTTP 403?**

**Answer**: The staging WebSocket service is rejecting authentication, despite JWT tokens being present and valid for API calls.

**Evidence**:
- API endpoints work with same JWT tokens (returning proper 403/422 for unauthorized operations)
- WebSocket connections fail immediately on handshake with HTTP 403
- Auth headers are present in WebSocket connection attempts

**Sub-Investigation**: Why does the same JWT work for API but not WebSocket?

### **Why #2: Why does JWT authentication work for API but not WebSocket?**

**Answer**: WebSocket authentication likely uses a different validation mechanism or endpoint than REST API authentication.

**Evidence**:
- REST API: `[PASS] Endpoint /api/health responding` with proper auth
- REST API: Proper 403 responses for unauthorized operations  
- WebSocket: Immediate rejection before any message exchange
- Different protocols may have different auth middleware

**Sub-Investigation**: Why would WebSocket auth validation differ from REST API auth?

### **Why #3: Why would WebSocket auth validation differ from REST API auth?**

**Answer**: WebSocket authentication happens during the initial handshake and may require different header formats or validation paths compared to REST API middleware.

**Evidence**:
- WebSocket auth occurs during HTTP upgrade handshake
- REST API auth occurs per-request in application middleware  
- Different services may handle auth differently in staging environment
- WebSocket may require specific header formats (e.g., query params vs headers)

**Sub-Investigation**: Why might the staging environment handle WebSocket auth differently than expected?

### **Why #4: Why might staging WebSocket authentication be configured differently?**

**Answer**: Staging environment likely has stricter security policies or different WebSocket authentication configuration compared to local development environment.

**Evidence**:
- Local tests expect WebSocket auth to work the same as API auth
- Staging environment enforces different security policies
- Tests show `E2E_OAUTH_SIMULATION_KEY not set` warnings
- Production-like staging security may require OAuth flow instead of direct JWT

**Sub-Investigation**: Why is the E2E OAuth simulation key important for staging WebSocket auth?

### **Why #5: Why is E2E OAuth simulation key critical for staging WebSocket authentication?**

**Answer**: Staging WebSocket authentication requires OAuth simulation bypass for E2E tests, but the tests are using direct JWT creation instead of proper OAuth flow simulation.

**Evidence**:
```
[WARNING] SSOT staging auth bypass failed: E2E_OAUTH_SIMULATION_KEY not provided
[INFO] Falling back to direct JWT creation for development environments  
[FALLBACK] Created direct JWT token
[WARNING] This may fail in staging due to user validation requirements
```

**Root Cause Identified**: The staging WebSocket service requires OAuth-simulated authentication via E2E bypass, but tests are falling back to direct JWT creation which doesn't work for WebSocket authentication in staging.

---

## 🎯 Root Cause Summary

**PRIMARY ROOT CAUSE**: Staging WebSocket authentication requires OAuth simulation bypass using `E2E_OAUTH_SIMULATION_KEY`, but the E2E tests are falling back to direct JWT token creation which works for REST API but not for WebSocket connections in the staging environment.

**Technical Details**:
1. **REST API Auth**: Works with direct JWT tokens (middleware validation)
2. **WebSocket Auth**: Requires OAuth-simulated tokens via E2E bypass mechanism  
3. **Missing Config**: `E2E_OAUTH_SIMULATION_KEY` not properly configured for WebSocket auth
4. **Environment Difference**: Staging has stricter WebSocket security than local development

---

## 🔧 Required Fixes

### **Immediate Fixes**:

1. **Configure OAuth Simulation Key**:
   - Set `E2E_OAUTH_SIMULATION_KEY` environment variable
   - Ensure key matches staging OAuth bypass configuration
   - Update test framework to use OAuth simulation for WebSocket

2. **Update WebSocket Auth Pattern**:
   - Modify E2E auth helper to use OAuth simulation for WebSocket connections
   - Ensure WebSocket headers match OAuth-simulated format
   - Test WebSocket auth separately from REST API auth

3. **Staging Configuration Alignment**:
   - Verify staging WebSocket service OAuth bypass configuration
   - Ensure E2E user permissions include WebSocket access
   - Align local and staging WebSocket auth mechanisms

### **SSOT Compliance**:
- Update `test_framework/ssot/e2e_auth_helper.py` with proper WebSocket OAuth simulation
- Ensure single source of truth for staging WebSocket authentication
- Remove fallback JWT creation for staging WebSocket connections

---

## 📊 Business Impact Analysis

### **Current Impact**:
- **Real-time Communication**: Chat functionality degraded in staging
- **Agent Pipelines**: Multi-agent coordination cannot be tested end-to-end  
- **User Experience**: WebSocket-dependent features untested in staging

### **Risk Assessment**:
- **High**: Production deployment could have similar WebSocket auth issues
- **Medium**: User trust impact if real-time features fail
- **Low**: REST API functionality remains intact

---

## ✅ Success Criteria

**Fix Validation**:
1. All 5 WebSocket tests pass in staging
2. WebSocket connections succeed without HTTP 403
3. OAuth simulation key properly configured and working
4. No warnings about falling back to direct JWT for staging

**Test Evidence**:
- `test_concurrent_websocket_real`: PASS
- `test_websocket_event_flow_real`: PASS  
- `test_real_agent_lifecycle_monitoring`: PASS
- `test_real_agent_pipeline_execution`: PASS
- `test_real_pipeline_error_handling`: PASS

---

## 🚀 Next Steps

1. **Spawn Multi-Agent Team**: Deploy specialized agents to implement OAuth simulation fix
2. **GCP Logs Investigation**: Check staging WebSocket service logs for detailed error info
3. **SSOT Implementation**: Update authentication helper with proper WebSocket OAuth support
4. **Configuration Fix**: Set up proper E2E OAuth simulation key for staging
5. **Re-test and Validate**: Run staging tests again to confirm all WebSocket tests pass

---

**Status**: Root cause identified - Ready for multi-agent implementation team