# Staging Deployment Validation Plan - Issue #1177 Supervisor Consolidation

## Step 6: Staging Deploy Validation

### 6.1 Deployment Command
```bash
python scripts/deploy_to_gcp_actual.py --project netra-staging --service backend --build-local
```

### 6.2 Expected Changes in Staging
The deployment will include the supervisor consolidation changes:

1. **Consolidated Supervisor Agent**: Single `supervisor_agent_modern.py` with streamlined execution
2. **Simplified Agent Registry**: Removed redundant supervisor registrations
3. **WebSocket Integration**: Preserved all 5 critical events in the consolidated agent
4. **Configuration Updates**: Updated references to use consolidated supervisor

### 6.3 Validation Checklist

#### 6.3.1 Deployment Health
- [ ] Cloud Run service deploys successfully
- [ ] Service reaches healthy state (no restart loops)
- [ ] All environment variables properly loaded
- [ ] VPC connector connectivity established

#### 6.3.2 Service Startup Validation
- [ ] WebSocket manager initializes without errors
- [ ] Database connections establish successfully
- [ ] Agent registry loads with consolidated supervisor
- [ ] Authentication integration works

#### 6.3.3 Critical Functionality Tests
```bash
# Test WebSocket connection
python -c "
import asyncio
import websockets
import json

async def test_websocket():
    uri = 'wss://api-staging.netrasystems.ai/ws'
    try:
        async with websockets.connect(uri) as websocket:
            print('WebSocket connection successful')
            # Test ping
            await websocket.send(json.dumps({'type': 'ping'}))
            response = await websocket.recv()
            print(f'Response: {response}')
    except Exception as e:
        print(f'WebSocket test failed: {e}')

asyncio.run(test_websocket())
"

# Test supervisor agent execution
python -c "
import requests
import json

# Test agent execution endpoint
payload = {
    'message': 'Test supervisor agent execution',
    'user_id': 'test-user-123'
}

try:
    response = requests.post(
        'https://staging.netrasystems.ai/api/agents/execute',
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    print(f'Agent execution status: {response.status_code}')
    if response.status_code == 200:
        result = response.json()
        print(f'Response: {result}')
    else:
        print(f'Error: {response.text}')
except Exception as e:
    print(f'Agent execution test failed: {e}')
"
```

#### 6.3.4 Log Validation
Check for these patterns in Cloud Run logs:
- ✅ `SupervisorAgent initialized successfully`
- ✅ `WebSocket events configured: 5 events`
- ✅ `Agent registry loaded: 1 supervisor agent`
- ❌ No `CRITICAL` or `ERROR` level logs during startup
- ❌ No supervisor-related import errors
- ❌ No WebSocket event delivery failures

#### 6.3.5 WebSocket Events Validation
Verify all 5 critical events are delivered:
1. `agent_started` - User sees agent began processing
2. `agent_thinking` - Real-time reasoning visibility
3. `tool_executing` - Tool usage transparency
4. `tool_completed` - Tool results display
5. `agent_completed` - User knows response is ready

### 6.4 Expected Performance Improvements
With supervisor consolidation:
- **Reduced Memory Usage**: ~10-15% reduction from eliminating redundant supervisor instances
- **Faster Agent Registration**: Single registration instead of multiple
- **Cleaner WebSocket Events**: Unified event delivery pipeline
- **Simplified Debugging**: Single supervisor execution path

### 6.5 Rollback Plan
If critical issues are found:
```bash
# Emergency rollback to previous revision
gcloud run services update netra-backend-staging \
  --project netra-staging \
  --region us-central1 \
  --revision [PREVIOUS_REVISION]
```

### 6.6 Success Criteria
- ✅ Deployment completes without errors
- ✅ Service health checks pass
- ✅ WebSocket connections establish successfully
- ✅ Agent execution returns valid responses
- ✅ All 5 WebSocket events are delivered
- ✅ No regression in response time or functionality
- ✅ Memory usage shows expected reduction

### 6.7 GitHub Issue Update Template
```markdown
## Step 6: Staging Deployment - COMPLETED ✅

### Deployment Status
- **Service**: netra-backend-staging
- **Revision**: [REVISION_ID]
- **Deployment Time**: [TIMESTAMP]
- **Status**: ✅ SUCCESS / ❌ FAILED

### Health Validation
- **Service Health**: ✅ Healthy
- **WebSocket**: ✅ Connected
- **Agent Execution**: ✅ Functional
- **Memory Usage**: ✅ Reduced by [X]%

### Test Results
- **WebSocket Events**: ✅ All 5 events delivered
- **Agent Response**: ✅ Valid responses
- **Performance**: ✅ No regressions

### Log Summary
- **Startup**: Clean, no errors
- **Agent Registry**: ✅ 1 supervisor agent loaded
- **WebSocket Events**: ✅ 5 events configured

**Ready for final wrap-up confirmation** ✅
```

## Manual Execution Steps

Since automated deployment requires approval, manual execution is needed:

1. **Deploy to staging**:
   ```bash
   python scripts/deploy_to_gcp_actual.py --project netra-staging --service backend --build-local
   ```

2. **Monitor deployment**:
   ```bash
   gcloud run services describe netra-backend-staging --project netra-staging --region us-central1
   ```

3. **Check service logs**:
   ```bash
   gcloud logs read "resource.type=cloud_run_revision" --project netra-staging --limit 50
   ```

4. **Run validation tests** (as documented above)

5. **Update GitHub issue** with results

## Risk Assessment
- **Low Risk**: Consolidation maintains all existing functionality
- **Rollback Available**: Previous revision can be restored immediately
- **Monitoring**: Full observability of deployment and functionality
- **Validation**: Comprehensive test suite ensures no regressions