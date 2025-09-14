# Issue #488 WebSocket 404 Comprehensive Remediation Plan

**Issue:** WebSocket 404 endpoints in GCP staging environment  
**Business Impact:** $500K+ ARR Golden Path functionality at risk  
**Root Cause:** Deployment synchronization issue between local fixes and GCP staging  
**Plan Date:** 2025-09-14  
**Execution Priority:** P1 - Mission Critical  

## Executive Summary

Based on comprehensive audit findings, Issue #488 shows:
- ✅ **Code Status:** RESOLVED locally - All WebSocket routes properly configured
- ❌ **Deployment Status:** GCP staging not reflecting local fixes  
- 🎯 **Solution:** Deploy latest local fixes to GCP staging environment
- 🔍 **Validation:** Comprehensive endpoint and business value testing required

## Phase 1: Deployment Status Verification

### 1.1 Current GCP Staging Status Check

**Commands:**
```bash
# Check current deployment status
gcloud run services describe netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --format="value(spec.template.metadata.name,status.traffic[0].percent,status.url)"

# Check deployment revision details
gcloud run revisions list \
  --service=netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --limit=5
```

**Expected Output:**
```
netra-backend-staging-XXXXX-XXX  100  https://netra-backend-staging-uc.a.run.app
```

**Success Criteria:**
- [ ] Current revision identified
- [ ] Traffic allocation confirmed (should be 100% to latest)
- [ ] Service URL accessible

### 1.2 Compare Local vs Deployed Code

**Commands:**
```bash
# Check current git status and ensure we're on develop-long-lived
git status
git log --oneline -10

# Verify WebSocket routes are properly configured locally
python -c "
from netra_backend.app.main import app
from fastapi.routing import APIRoute
routes = [route for route in app.routes if hasattr(route, 'path')]
websocket_routes = [r for r in routes if 'websocket' in r.path.lower() or 'ws' in r.path]
for route in websocket_routes:
    print(f'{route.methods if hasattr(route, \"methods\") else \"WebSocket\"}: {route.path}')
"
```

**Expected Local Routes:**
```
WebSocket: /websocket
WebSocket: /ws/test  
GET: /ws/health
```

**Success Criteria:**
- [ ] Local WebSocket routes confirmed operational
- [ ] Current git branch is develop-long-lived
- [ ] No uncommitted changes that could affect deployment

### 1.3 Service Health Pre-Deployment

**Commands:**
```bash
# Test staging backend health
curl -s https://api.staging.netrasystems.ai/health | jq .

# Check current WebSocket endpoints (should show 404s)
curl -s https://api.staging.netrasystems.ai/websocket || echo "Expected 404 - confirms issue"
curl -s https://api.staging.netrasystems.ai/ws/test || echo "Expected 404 - confirms issue"
```

**Expected Output:**
```json
{
  "status": "ok",
  "timestamp": "2025-09-14T...",
  "version": "...",
  "environment": "staging"
}
```

**Success Criteria:**
- [ ] Backend health endpoint returns 200 OK
- [ ] WebSocket endpoints return 404 (confirming the issue)
- [ ] No service degradation before deployment

## Phase 2: Deployment Strategy

### 2.1 Pre-Deployment Validation

**Commands:**
```bash
# Run mission critical tests locally to ensure code quality
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_no_ssot_violations.py

# Validate configuration integrity
python scripts/check_architecture_compliance.py --module websocket

# Check for any deployment blockers
python scripts/query_string_literals.py validate "websocket"
```

**Success Criteria:**
- [ ] All mission critical tests pass locally
- [ ] No SSOT violations in WebSocket modules  
- [ ] Configuration compliance >95%
- [ ] No string literal validation errors

### 2.2 Deploy to GCP Staging

**Primary Deployment Command:**
```bash
# Deploy with local build and comprehensive checks
python scripts/deploy_to_gcp_actual.py \
  --project netra-staging \
  --build-local \
  --check-secrets \
  --check-apis \
  --timeout 900 \
  --verbose

# Alternative if timeout issues (use wrapper):
python scripts/deploy_gcp_with_timeout.py \
  --project netra-staging \
  --build-local \
  --timeout 1200
```

**Deployment Monitoring:**
```bash
# Monitor deployment progress
gcloud run operations list \
  --region=us-central1 \
  --project=netra-staging \
  --filter="metadata.target.service=netra-backend-staging" \
  --limit=5

# Follow deployment logs
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"netra-backend-staging\"" \
  --project=netra-staging \
  --limit=50 \
  --format="value(timestamp,textPayload)"
```

**Success Criteria:**
- [ ] Deployment completes without errors
- [ ] New revision receives 100% traffic
- [ ] Container starts successfully
- [ ] No critical errors in logs

### 2.3 Deployment Validation

**Commands:**
```bash
# Verify new revision is active
gcloud run services describe netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --format="value(status.latestReadyRevisionName,status.traffic[0].revisionName)"

# Test health endpoint immediately after deployment
curl -s https://api.staging.netrasystems.ai/health | jq .

# Wait 60 seconds for service to fully initialize, then test WebSocket health
sleep 60
curl -s https://api.staging.netrasystems.ai/ws/health | jq .
```

**Success Criteria:**
- [ ] Latest revision matches traffic revision
- [ ] Health endpoint returns 200 within 30 seconds
- [ ] WebSocket health endpoint returns 200 within 60 seconds
- [ ] No 503 or 502 errors during warmup

## Phase 3: Endpoint Validation

### 3.1 WebSocket Endpoint Testing

**Test Commands:**
```bash
# Test the working endpoint that should now be available
curl -s https://api.staging.netrasystems.ai/websocket \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" || echo "WebSocket upgrade attempt"

# Test WebSocket health endpoint  
curl -s https://api.staging.netrasystems.ai/ws/health | jq .

# Test WebSocket test endpoint
curl -s https://api.staging.netrasystems.ai/ws/test | jq .
```

**WebSocket Connection Test (Python):**
```bash
# Create temporary WebSocket test script
cat > /tmp/websocket_test.py << 'EOF'
import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "wss://api.staging.netrasystems.ai/websocket"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            # Send a test message
            await websocket.send('{"type": "ping"}')
            response = await websocket.recv()
            print(f"✅ Received: {response}")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    sys.exit(0 if result else 1)
EOF

# Run WebSocket connection test
python /tmp/websocket_test.py
```

**Success Criteria:**
- [ ] `/websocket` endpoint accepts WebSocket upgrades
- [ ] `/ws/health` returns 200 with health data  
- [ ] `/ws/test` returns 200 with test response
- [ ] WebSocket connection establishes successfully
- [ ] No 404, 500, or connection refused errors

### 3.2 Route Configuration Verification

**Commands:**
```bash
# Test route availability with verbose output
curl -v https://api.staging.netrasystems.ai/websocket 2>&1 | head -20
curl -v https://api.staging.netrasystems.ai/ws/health 2>&1 | head -20
curl -v https://api.staging.netrasystems.ai/ws/test 2>&1 | head -20

# Check for routing errors in logs
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"netra-backend-staging\" AND (textPayload:\"404\" OR textPayload:\"websocket\" OR textPayload:\"routing\")" \
  --project=netra-staging \
  --limit=20 \
  --format="value(timestamp,textPayload)"
```

**Success Criteria:**
- [ ] HTTP responses show proper routing (not 404)
- [ ] Connection upgrade headers accepted
- [ ] No routing errors in application logs
- [ ] Response times <1 second for HTTP endpoints

## Phase 4: Mission Critical Test Re-execution

### 4.1 WebSocket Agent Events Test Suite

**Commands:**
```bash
# Run the primary WebSocket test suite that was failing
python tests/mission_critical/test_websocket_agent_events_suite.py -v

# Run comprehensive WebSocket integration tests
python tests/integration/test_websocket_staging_connectivity.py -v

# Test WebSocket authentication integration
python tests/integration/auth/test_websocket_authentication_failures_issue_463.py -v
```

**Success Criteria:**
- [ ] All WebSocket agent event tests pass
- [ ] WebSocket connectivity tests successful
- [ ] Authentication integration tests pass
- [ ] Test execution time <5 minutes
- [ ] No connection timeout errors

### 4.2 End-to-End WebSocket Flow

**Commands:**
```bash
# Run E2E tests that include WebSocket functionality
python tests/e2e/test_websocket_dev_docker_connection.py --staging

# Run Golden Path validation
python -c "
import asyncio
import websockets
import json
from datetime import datetime

async def test_golden_path_websocket():
    uri = 'wss://api.staging.netrasystems.ai/websocket'
    try:
        async with websockets.connect(uri) as ws:
            # Test agent workflow simulation
            message = {
                'type': 'agent_execute',
                'data': {'message': 'test golden path'},
                'timestamp': datetime.now().isoformat()
            }
            await ws.send(json.dumps(message))
            
            # Wait for response
            response = await asyncio.wait_for(ws.recv(), timeout=30)
            response_data = json.loads(response)
            
            print(f'✅ Golden Path Test Success: {response_data}')
            return True
            
    except Exception as e:
        print(f'❌ Golden Path Test Failed: {e}')
        return False

asyncio.run(test_golden_path_websocket())
"
```

**Success Criteria:**
- [ ] E2E WebSocket tests complete successfully
- [ ] Golden Path WebSocket flow functional
- [ ] Agent event delivery confirmed
- [ ] Real-time communication established
- [ ] No timeout or connection errors

### 4.3 Load and Performance Testing

**Commands:**
```bash
# Test WebSocket under load (concurrent connections)
cat > /tmp/websocket_load_test.py << 'EOF'
import asyncio
import websockets
import json
import time

async def connect_and_test(connection_id):
    uri = "wss://api.staging.netrasystems.ai/websocket"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"type": "test", "id": connection_id}))
            response = await ws.recv()
            return f"Connection {connection_id}: Success"
    except Exception as e:
        return f"Connection {connection_id}: Failed - {e}"

async def load_test():
    tasks = [connect_and_test(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    for result in results:
        print(result)
    
    success_count = sum(1 for r in results if "Success" in r)
    print(f"Load Test: {success_count}/10 connections successful")
    return success_count >= 8  # 80% success rate required

if __name__ == "__main__":
    asyncio.run(load_test())
EOF

python /tmp/websocket_load_test.py
```

**Success Criteria:**
- [ ] 80%+ concurrent connections succeed
- [ ] Response times <3 seconds under load
- [ ] No server errors during load test
- [ ] Memory/CPU usage within limits

## Phase 5: Business Value Confirmation

### 5.1 Golden Path Functionality Testing

**Test Sequence:**
```bash
# 1. User Authentication Flow
echo "Testing user authentication..."
curl -s "https://auth.staging.netrasystems.ai/auth/config" | jq .

# 2. WebSocket Connection with Auth
echo "Testing authenticated WebSocket connection..."
python -c "
import asyncio
import websockets
import json

async def test_authenticated_websocket():
    # This would use actual JWT token in real test
    uri = 'wss://api.staging.netrasystems.ai/websocket'
    headers = {'Authorization': 'Bearer test-token'}
    
    try:
        async with websockets.connect(uri, extra_headers=headers) as ws:
            print('✅ Authenticated WebSocket connection established')
            
            # Test chat message flow
            chat_message = {
                'type': 'chat_message',
                'data': {'message': 'Hello, test the Golden Path'},
                'user_id': 'test-user'
            }
            await ws.send(json.dumps(chat_message))
            
            # Wait for agent response
            response = await asyncio.wait_for(ws.recv(), timeout=30)
            print(f'✅ Agent response received: {json.loads(response)[\"type\"]}')
            return True
            
    except Exception as e:
        print(f'❌ Authenticated WebSocket test failed: {e}')
        return False

asyncio.run(test_authenticated_websocket())
"

# 3. Health Check Golden Path
echo "Testing complete system health..."
curl -s https://api.staging.netrasystems.ai/health | jq .
curl -s https://auth.staging.netrasystems.ai/health | jq .
```

**Success Criteria:**
- [ ] User authentication system operational
- [ ] Authenticated WebSocket connections succeed
- [ ] Chat message flow functional
- [ ] Agent responses delivered via WebSocket
- [ ] All service health checks pass

### 5.2 Multi-User Isolation Testing

**Commands:**
```bash
# Test multiple user contexts simultaneously
cat > /tmp/multi_user_test.py << 'EOF'
import asyncio
import websockets
import json
import uuid

async def user_session(user_id):
    uri = "wss://api.staging.netrasystems.ai/websocket"
    try:
        async with websockets.connect(uri) as ws:
            # Send user-specific message
            message = {
                "type": "user_message", 
                "user_id": user_id,
                "data": {"message": f"Hello from {user_id}"}
            }
            await ws.send(json.dumps(message))
            
            # Wait for response
            response = await asyncio.wait_for(ws.recv(), timeout=15)
            response_data = json.loads(response)
            
            # Verify user isolation
            if response_data.get('user_id') == user_id:
                return f"✅ User {user_id}: Proper isolation"
            else:
                return f"❌ User {user_id}: Isolation failed"
                
    except Exception as e:
        return f"❌ User {user_id}: Connection failed - {e}"

async def test_multi_user_isolation():
    users = [f"test-user-{i}" for i in range(5)]
    tasks = [user_session(user) for user in users]
    results = await asyncio.gather(*tasks)
    
    for result in results:
        print(result)
    
    success_count = sum(1 for r in results if "✅" in r)
    print(f"Multi-user test: {success_count}/5 users properly isolated")
    return success_count >= 4

if __name__ == "__main__":
    asyncio.run(test_multi_user_isolation())
EOF

python /tmp/multi_user_test.py
```

**Success Criteria:**
- [ ] Multiple concurrent user sessions supported
- [ ] User isolation properly maintained
- [ ] No cross-user data leakage
- [ ] 80%+ user sessions succeed
- [ ] Response times <5 seconds per user

### 5.3 WebSocket Event Delivery Validation

**Commands:**
```bash
# Test all 5 critical WebSocket events
python -c "
import asyncio
import websockets
import json

async def test_websocket_events():
    uri = 'wss://api.staging.netrasystems.ai/websocket'
    
    try:
        async with websockets.connect(uri) as ws:
            # Simulate agent execution request
            request = {
                'type': 'agent_execute',
                'data': {'agent': 'triage', 'message': 'Test all events'}
            }
            await ws.send(json.dumps(request))
            
            # Collect events
            events_received = []
            timeout_count = 0
            
            while len(events_received) < 5 and timeout_count < 3:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10)
                    event = json.loads(response)
                    events_received.append(event.get('type', 'unknown'))
                    print(f'✅ Event received: {event.get(\"type\")}')
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print('⏱️ Timeout waiting for event')
            
            # Verify critical events
            expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            received_critical = [e for e in expected_events if e in events_received]
            
            print(f'Critical events received: {len(received_critical)}/5')
            print(f'Events: {received_critical}')
            
            return len(received_critical) >= 3  # At least 3/5 critical events
            
    except Exception as e:
        print(f'❌ WebSocket event test failed: {e}')
        return False

asyncio.run(test_websocket_events())
"
```

**Success Criteria:**
- [ ] At least 3/5 critical WebSocket events received
- [ ] Event delivery within 30 seconds
- [ ] Events contain proper structure and data
- [ ] No event delivery failures or exceptions

## Rollback Plan (If Deployment Fails)

### Immediate Rollback Commands

```bash
# Get current and previous revisions
CURRENT_REVISION=$(gcloud run services describe netra-backend-staging --region=us-central1 --project=netra-staging --format="value(status.latestReadyRevisionName)")
PREVIOUS_REVISION=$(gcloud run revisions list --service=netra-backend-staging --region=us-central1 --project=netra-staging --limit=2 --format="value(metadata.name)" | tail -1)

# Rollback to previous revision
gcloud run services update-traffic netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --to-revisions=$PREVIOUS_REVISION=100

# Verify rollback
curl -s https://api.staging.netrasystems.ai/health | jq .
```

### Rollback Validation

```bash
# Confirm service health after rollback
python tests/mission_critical/test_no_ssot_violations.py
curl -s https://api.staging.netrasystems.ai/health | jq .status
```

**Rollback Success Criteria:**
- [ ] Previous revision receiving 100% traffic
- [ ] Health endpoints return 200 OK
- [ ] No degradation in core functionality

## Success Metrics and Acceptance Criteria

### Phase 1 Success Metrics
- [ ] Current deployment status identified
- [ ] Local vs deployed code comparison complete
- [ ] Service health baseline established

### Phase 2 Success Metrics  
- [ ] Deployment completes without errors
- [ ] New revision active with 100% traffic
- [ ] Health endpoints responsive within 60 seconds

### Phase 3 Success Metrics
- [ ] All WebSocket endpoints return proper responses (not 404)
- [ ] WebSocket connections establish successfully
- [ ] Route configuration verified

### Phase 4 Success Metrics
- [ ] Mission critical WebSocket tests pass 100%
- [ ] E2E WebSocket flow functional
- [ ] Load testing shows 80%+ success rate

### Phase 5 Success Metrics
- [ ] Golden Path user flow operational
- [ ] Multi-user isolation confirmed
- [ ] All 5 critical WebSocket events delivered

## Post-Remediation Monitoring

### Ongoing Monitoring Commands
```bash
# Set up log monitoring for WebSocket issues
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"netra-backend-staging\" AND (textPayload:\"websocket\" OR textPayload:\"404\" OR severity>=ERROR)" \
  --project=netra-staging \
  --format="value(timestamp,severity,textPayload)" \
  --follow

# Monitor WebSocket connection metrics  
curl -s https://api.staging.netrasystems.ai/ws/health | jq '.connections.active'
```

### Success Thresholds for Ongoing Health
- WebSocket endpoint 99.9% uptime
- <1% connection failure rate
- <2 second average response time
- Zero 404 errors for WebSocket routes

## Risk Assessment

### Low Risk Items
- ✅ Code changes already validated locally
- ✅ Standard GCP deployment process
- ✅ Rollback plan available

### Medium Risk Items  
- ⚠️ WebSocket connections during deployment transition
- ⚠️ User sessions during service restart
- ⚠️ Potential caching issues with new routes

### High Risk Items
- 🚨 Complete WebSocket functionality failure
- 🚨 Auth integration breaking during deployment  
- 🚨 Database connection issues post-deployment

### Risk Mitigation
- Deploy during low-traffic period
- Monitor logs continuously during deployment
- Have rollback commands ready
- Test auth integration immediately after deployment

## Conclusion

This comprehensive remediation plan addresses Issue #488 through systematic deployment validation, endpoint testing, and business value confirmation. The plan prioritizes minimal risk deployment while ensuring maximum business value protection for the $500K+ ARR Golden Path functionality.

**Estimated Execution Time:** 2-3 hours  
**Business Impact:** Critical - Restores WebSocket functionality  
**Confidence Level:** High - Local fixes confirmed working  

---

*Plan prepared by: Netra Apex System Remediation Team*  
*Date: 2025-09-14*  
*Review Status: Ready for Execution*