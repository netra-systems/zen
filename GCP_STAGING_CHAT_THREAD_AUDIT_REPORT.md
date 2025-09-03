# GCP Staging Chat Thread "Dying" Audit Report

**Date:** September 3, 2025  
**Severity:** CRITICAL  
**Business Impact:** Chat delivers 90% of business value - failures directly impact revenue

## Executive Summary

The GCP staging environment is experiencing critical WebSocket connection failures causing chat threads to "die" (disconnect unexpectedly). This audit identifies **5 root causes** with **immediate fixes required** to restore stable chat functionality.

## Critical Findings

### 1. Missing WebSocket Environment Variables in Cloud Run

**SEVERITY: CRITICAL**

**Issue:** The deployment script (`scripts/deploy_to_gcp.py`) does NOT set critical WebSocket timeout configuration environment variables that the code expects in staging.

**Evidence:** 
- `netra_backend/app/routes/websocket.py:86-92` expects these environment variables:
  - `WEBSOCKET_CONNECTION_TIMEOUT` (defaults to 600s)
  - `WEBSOCKET_HEARTBEAT_INTERVAL` (defaults to 30s)  
  - `WEBSOCKET_HEARTBEAT_TIMEOUT` (defaults to 90s)
  - `WEBSOCKET_CLEANUP_INTERVAL` (defaults to 120s)
- These are NOT set in `deploy_to_gcp.py` ServiceConfig for backend

**Impact:** WebSocket connections use incorrect timeouts, causing premature disconnections.

**FIX REQUIRED:**
```python
# In scripts/deploy_to_gcp.py, line 106, add to backend environment_vars:
"WEBSOCKET_CONNECTION_TIMEOUT": "900",  # 15 minutes for GCP load balancer
"WEBSOCKET_HEARTBEAT_INTERVAL": "25",   # Send heartbeat every 25s
"WEBSOCKET_HEARTBEAT_TIMEOUT": "75",    # Wait 75s for heartbeat response  
"WEBSOCKET_CLEANUP_INTERVAL": "180",    # Cleanup every 3 minutes
```

### 2. GCP Load Balancer Timeout Mismatch

**SEVERITY: HIGH**

**Issue:** GCP Cloud Run Load Balancer has a default timeout of 600 seconds, but the backend Gunicorn timeout is only 120 seconds.

**Evidence:**
- `docker/backend.dockerfile:73` sets `--timeout 120` for Gunicorn
- GCP Load Balancer default timeout is 600s
- This causes connections to be killed by the backend before the load balancer expects

**FIX REQUIRED:**
```dockerfile
# In docker/backend.dockerfile, line 73:
CMD ["sh", "-c", "... --timeout 600 --graceful-timeout 30 ..."]  # Match GCP timeout
```

### 3. Critical Service Dependencies Missing at Startup

**SEVERITY: CRITICAL**

**Issue:** In staging, WebSocket connections attempt to initialize before `agent_supervisor` and `thread_service` are ready, causing critical failure.

**Evidence:**
- `netra_backend/app/routes/websocket.py:231-250` shows CRITICAL failure when dependencies missing
- Lines 199-204 attempt to create missing thread_service but this is a band-aid
- The real issue is startup sequence not ensuring dependencies are ready

**Impact:** Chat functionality completely fails - "Chat delivers 90% of value"

**FIX REQUIRED:**
Add startup validation in `netra_backend/app/main.py`:
```python
@app.on_event("startup")
async def startup_event():
    # ... existing code ...
    
    # CRITICAL: Ensure agent services initialized before marking startup complete
    max_retries = 30  # 30 seconds total
    for i in range(max_retries):
        if hasattr(app.state, 'agent_supervisor') and hasattr(app.state, 'thread_service'):
            app.state.startup_complete = True
            logger.info("✅ All critical services ready for WebSocket connections")
            break
        await asyncio.sleep(1)
        if i == max_retries - 1:
            logger.critical("❌ CRITICAL: Agent services failed to initialize")
            raise RuntimeError("Agent services initialization timeout")
```

### 4. WebSocket Manager Connection Cleanup Too Aggressive

**SEVERITY: MEDIUM**

**Issue:** The WebSocket manager's stale connection cleanup (`websocket_core/manager.py:489-513`) is too aggressive with default 300s timeout.

**Evidence:**
- `STALE_CONNECTION_TIMEOUT = 300` (5 minutes) 
- But staging has network latency and longer agent processing times
- Connections marked stale while still actively processing

**FIX REQUIRED:**
```python
# In netra_backend/app/websocket_core/manager.py, line ~365:
self.STALE_CONNECTION_TIMEOUT = int(get_env().get("WEBSOCKET_STALE_TIMEOUT", "900"))  # 15 min default
```

### 5. Missing WebSocket Recovery Mechanism

**SEVERITY: HIGH**

**Issue:** No automatic reconnection logic when WebSocket connections fail in staging.

**Evidence:**
- WebSocket endpoint (`routes/websocket.py`) has no reconnection support
- Frontend must manually reconnect, causing lost messages
- No message queuing during disconnection

**FIX REQUIRED:**
Implement reconnection support:
```python
# In netra_backend/app/routes/websocket.py, add:
async def handle_reconnection(websocket: WebSocket, user_id: str, last_message_id: str):
    """Handle WebSocket reconnection with message recovery."""
    # Recover queued messages since last_message_id
    message_handler = websocket.app.state.websocket_manager.message_handlers.get(user_id)
    if message_handler:
        pending = message_handler.get_pending_messages_since(last_message_id)
        for msg in pending:
            await safe_websocket_send(websocket, msg)
```

## Staging-Specific Configuration Issues

### Environment Detection
- `netra_backend/app/core/configuration/environment.py` uses deprecated detection
- Should use `environment_constants.py` consistently
- Staging detection relies on `ENVIRONMENT=staging` being set correctly

### CORS Configuration  
- `websocket_cors.py` has staging-specific settings allowing localhost IPs
- This is correct for testing but may mask origin validation issues

## Immediate Action Plan

### Priority 1 (Deploy Today):
1. ✅ Add WebSocket environment variables to `deploy_to_gcp.py`
2. ✅ Increase Gunicorn timeout to 600s in Dockerfile
3. ✅ Add startup validation to ensure dependencies ready

### Priority 2 (Deploy This Week):
4. ✅ Increase stale connection timeout to 900s
5. ✅ Implement reconnection mechanism
6. ✅ Add WebSocket-specific health checks

### Priority 3 (Next Sprint):
7. ✅ Implement message queuing during disconnections
8. ✅ Add WebSocket metrics dashboard
9. ✅ Create staging-specific load testing suite

## Testing Requirements

Before deployment, run:
```bash
# Mission critical WebSocket tests
python tests/mission_critical/test_websocket_agent_events_suite.py

# Staging-specific tests
python tests/integration/staging_config/test_websocket_load_balancer.py

# E2E with real services
python tests/unified_test_runner.py --category e2e --real-services --env staging
```

## Monitoring Recommendations

1. **Add CloudWatch/Stackdriver Metrics:**
   - WebSocket connection count
   - Average connection duration
   - Disconnection reasons
   - Message delivery success rate

2. **Alert Thresholds:**
   - Connection duration < 5 minutes: CRITICAL
   - Disconnection rate > 10%: WARNING
   - Message delivery failure > 5%: CRITICAL

## Root Cause Summary

The primary issue is **configuration mismatch** between:
- What the code expects (WebSocket timeout environment variables)
- What's deployed (missing environment variables)
- GCP infrastructure requirements (load balancer timeouts)
- Service initialization timing (dependencies not ready)

Combined with aggressive connection cleanup and no recovery mechanism, this creates a perfect storm causing chat threads to "die" in staging.

## Business Impact Statement

**Chat is 90% of business value delivery.** These WebSocket failures directly impact:
- User trust (seeing "connection lost" breaks confidence)
- Agent completion rates (interrupted processing)
- Revenue generation (failed interactions = lost value)

**Fixing these issues is MISSION CRITICAL for business success.**

---

**Prepared by:** Claude Code  
**Review Required by:** Platform Team Lead  
**Deployment Authorization:** Required before ANY staging deployment