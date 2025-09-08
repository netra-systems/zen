# Deployment Verification Steps - Factory SSOT & Auth E2E Fixes

**Date**: 2025-01-08  
**Purpose**: Comprehensive verification steps for Factory SSOT validation and E2E Auth bypass fixes  
**Business Impact**: Validates restoration of $120K+ MRR WebSocket chat functionality testing in staging

## Pre-Deployment Checklist

### Code Changes Verification
- [ ] **Factory SSOT Enhancement**: `websocket_manager_factory.py` enhanced validation function deployed
- [ ] **E2E Context Extraction**: `unified_websocket_auth.py` E2E context extraction added
- [ ] **Auth Service E2E Bypass**: `unified_authentication_service.py` E2E bypass logic implemented
- [ ] **Integration Tests**: New comprehensive test suite created and passing locally

### Environment Configuration 
- [ ] **Staging E2E Variables**: All required environment variables configured (see `staging_environment_e2e_configuration.md`)
- [ ] **GCP Cloud Run**: Service updated with E2E environment variables
- [ ] **Load Balancer**: Header forwarding configured for E2E test headers
- [ ] **Secrets Management**: E2E OAuth simulation key created and accessible

## Deployment Steps

### 1. Deploy Code Changes
```bash
# Build and deploy backend service with fixes
python scripts/deploy_to_gcp.py \
    --project netra-staging \
    --service netra-backend \
    --build-local \
    --env-file .env.staging
```

### 2. Update Cloud Run Configuration
```bash
# Update service with E2E environment variables
gcloud run services update netra-backend \
    --platform managed \
    --region us-central1 \
    --set-env-vars="E2E_TESTING=1,STAGING_E2E_TEST=1,E2E_TEST_ENV=staging" \
    --project netra-staging
```

### 3. Restart Services for Configuration Reload
```bash
# Force new revision deployment to ensure env vars are loaded
gcloud run services replace-traffic netra-backend \
    --to-latest \
    --platform managed \
    --region us-central1 \
    --project netra-staging
```

## Post-Deployment Verification

### Phase 1: Service Health Verification

#### 1.1 Basic Service Health
```bash
# Check service is responding
curl -f "https://staging.netrasystems.ai/health" 

# Expected: HTTP 200 with health status
```

#### 1.2 E2E Configuration Detection
```bash
# Verify E2E configuration is loaded
curl -H "X-E2E-Test: true" \
     -H "X-Test-Environment: staging" \
     "https://staging.netrasystems.ai/health/e2e-status"

# Expected response:
# {
#   "e2e_testing_enabled": true,
#   "environment": "staging",
#   "e2e_detection_available": true
# }
```

#### 1.3 Environment Variable Verification
```bash
# Check deployed environment variables
gcloud run services describe netra-backend \
    --platform managed \
    --region us-central1 \
    --project netra-staging \
    --format="value(spec.template.spec.containers[0].env[].(name,value))" | \
    grep -E "(E2E_|STAGING_|ENVIRONMENT)"

# Expected output should include:
# ENVIRONMENT staging
# E2E_TESTING 1
# STAGING_E2E_TEST 1
# E2E_TEST_ENV staging
```

### Phase 2: Factory SSOT Validation Testing

#### 2.1 WebSocket Connection with Staging Patterns
```python
# Test script: test_factory_validation.py
import asyncio
import websockets
import json

async def test_factory_validation():
    headers = {
        'X-E2E-Test': 'true',
        'X-Test-Environment': 'staging',
        'Authorization': 'Bearer staging-e2e-user-003-test-token'
    }
    
    try:
        # This should NOT fail with 1011 Factory SSOT validation errors
        async with websockets.connect(
            'wss://staging.netrasystems.ai/websocket',
            extra_headers=headers,
            timeout=10
        ) as ws:
            print("✅ WebSocket connection successful - Factory validation working")
            
            # Wait for welcome message
            welcome = await asyncio.wait_for(ws.recv(), timeout=5)
            welcome_data = json.loads(welcome)
            
            if welcome_data.get('type') == 'connection_established':
                print("✅ Connection established message received")
                return True
            else:
                print(f"❌ Unexpected welcome message: {welcome_data}")
                return False
                
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1011:
            print(f"❌ Factory SSOT validation still failing (1011): {e.reason}")
            return False
        elif e.code == 1008:
            print(f"❌ Auth policy violation (1008): {e.reason}")
            return False
        else:
            print(f"❌ Unexpected WebSocket error ({e.code}): {e.reason}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

# Run the test
result = asyncio.run(test_factory_validation())
print(f"Factory validation test result: {'PASS' if result else 'FAIL'}")
```

#### 2.2 Run Factory Validation Test
```bash
python test_factory_validation.py

# Expected output:
# ✅ WebSocket connection successful - Factory validation working
# ✅ Connection established message received  
# Factory validation test result: PASS
```

### Phase 3: E2E Auth Bypass Testing

#### 3.1 WebSocket Authentication with E2E Context
```python
# Test script: test_e2e_auth_bypass.py
import asyncio
import websockets
import json

async def test_e2e_auth_bypass():
    headers = {
        'X-E2E-Test': 'true',
        'X-Test-Environment': 'staging',
        'X-Test-Type': 'e2e',
        'Authorization': 'Bearer staging-e2e-user-003-invalid-jwt-should-bypass'
    }
    
    try:
        async with websockets.connect(
            'wss://staging.netrasystems.ai/websocket',
            extra_headers=headers,
            timeout=10
        ) as ws:
            print("✅ WebSocket connection with invalid JWT successful - E2E bypass working")
            
            # Send a test message to trigger message-level authentication
            test_message = {
                "type": "chat",
                "content": "Test E2E message flow",
                "thread_id": "test-thread-e2e"
            }
            
            await ws.send(json.dumps(test_message))
            print("✅ Message sent successfully")
            
            # Wait for agent processing events (not 1008 policy violation)
            events_received = []
            for i in range(5):
                try:
                    event = await asyncio.wait_for(ws.recv(), timeout=10)
                    event_data = json.loads(event)
                    events_received.append(event_data.get('type', 'unknown'))
                    print(f"✅ Received event: {event_data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    break
            
            expected_events = ['agent_started', 'agent_thinking', 'agent_completed']
            received_expected = any(event in events_received for event in expected_events)
            
            if received_expected:
                print("✅ E2E auth bypass successful - received agent processing events")
                return True
            else:
                print(f"❌ No expected agent events received. Got: {events_received}")
                return False
                
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:
            print(f"❌ E2E auth bypass failed - still getting policy violation (1008): {e.reason}")
            return False
        else:
            print(f"❌ Unexpected WebSocket error ({e.code}): {e.reason}")
            return False
    except Exception as e:
        print(f"❌ E2E test failed: {e}")
        return False

# Run the test
result = asyncio.run(test_e2e_auth_bypass())
print(f"E2E auth bypass test result: {'PASS' if result else 'FAIL'}")
```

#### 3.2 Run E2E Auth Bypass Test
```bash
python test_e2e_auth_bypass.py

# Expected output:
# ✅ WebSocket connection with invalid JWT successful - E2E bypass working
# ✅ Message sent successfully
# ✅ Received event: agent_started
# ✅ Received event: agent_thinking
# ✅ Received event: tool_executing
# ✅ Received event: tool_completed
# ✅ Received event: agent_completed
# ✅ E2E auth bypass successful - received agent processing events
# E2E auth bypass test result: PASS
```

### Phase 4: Integration Test Suite

#### 4.1 Run Comprehensive Integration Tests
```bash
# Run the new integration test suite
python -m pytest tests/integration/test_factory_ssot_e2e_validation_fixes.py -v

# Expected output:
# ✅ test_staging_uuid_fallback_pattern_validation PASSED
# ✅ test_standard_uuid_pattern_validation PASSED  
# ✅ test_e2e_user_pattern_validation PASSED
# ✅ test_production_strict_validation_still_works PASSED
# ✅ test_e2e_context_extraction_from_headers PASSED
# ✅ test_e2e_bypass_in_authentication_service PASSED
# ✅ test_complete_websocket_flow_with_e2e_bypass PASSED
# ✅ test_websocket_manager_creation_with_enhanced_validation PASSED
```

#### 4.2 Run Staging E2E Test Suite
```bash
# Run the original failing tests that should now pass
python tests/unified_test_runner.py \
    --category e2e \
    --env staging \
    --real-services \
    --target-modules test_websocket_events_staging test_agent_pipeline_staging

# Expected: All previously failing tests should now pass
# No 1011 Factory SSOT validation errors
# No 1008 SSOT Auth failed errors  
```

### Phase 5: Monitoring and Log Verification

#### 5.1 Check Deployment Logs
```bash
# Check for successful startup logs
gcloud logs read "resource.type=cloud_run_revision" \
    --filter="resource.labels.service_name=netra-backend" \
    --limit=50 \
    --format="value(timestamp,jsonPayload.message)" | \
    grep -E "(ENHANCED STAGING|E2E BYPASS|UnifiedAuthenticationService)"

# Expected log entries:
# "UnifiedAuthenticationService initialized - SSOT authentication enforced"
# "ENHANCED STAGING: Using comprehensive staging validation"  
# "E2E BYPASS: Creating mock auth result for user staging-e2e-user-..."
```

#### 5.2 Monitor for Error Patterns
```bash
# Check for lingering 1011/1008 errors
gcloud logs read "resource.type=cloud_run_revision" \
    --filter="resource.labels.service_name=netra-backend" \
    --filter="jsonPayload.message:(1011 OR 1008)" \
    --limit=20

# Expected: No recent 1011 Factory SSOT or 1008 Auth policy errors
```

#### 5.3 Verify E2E Detection Logs
```bash
# Check E2E context detection is working
gcloud logs read "resource.type=cloud_run_revision" \
    --filter="resource.labels.service_name=netra-backend" \
    --filter="jsonPayload.message:(E2E CONTEXT DETECTED)" \
    --limit=10

# Expected: Evidence of E2E context detection during test runs
```

## Production Safety Verification

### 6.1 Production Environment Check
```bash
# Verify production does NOT have E2E variables (critical security check)
gcloud run services describe netra-backend \
    --platform managed \
    --region us-central1 \
    --project netra-production \
    --format="value(spec.template.spec.containers[0].env[].(name,value))" | \
    grep -E "E2E_"

# Expected: No E2E environment variables in production
# If any E2E variables found in production: IMMEDIATELY REMOVE THEM
```

### 6.2 Production WebSocket Test
```python
# Verify production still requires real authentication
import asyncio
import websockets

async def test_production_security():
    headers = {
        'X-E2E-Test': 'true',  # E2E header should be ignored in production
        'Authorization': 'Bearer invalid-jwt-token'
    }
    
    try:
        async with websockets.connect(
            'wss://production.netrasystems.ai/websocket',  
            extra_headers=headers,
            timeout=5
        ) as ws:
            print("❌ SECURITY ISSUE: Production accepted invalid JWT with E2E header")
            return False
            
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:
            print("✅ Production correctly rejected invalid JWT (1008 policy violation)")
            return True
        else:
            print(f"❌ Unexpected production error: {e.code} {e.reason}")
            return False

result = asyncio.run(test_production_security())
print(f"Production security test: {'PASS' if result else 'FAIL'}")
```

## Rollback Plan

### If Verification Fails

#### 1. Immediate Rollback
```bash
# Revert to previous working revision
gcloud run services update-traffic netra-backend \
    --to-revisions=PREVIOUS_REVISION=100 \
    --platform managed \
    --region us-central1 \
    --project netra-staging
```

#### 2. Remove E2E Environment Variables
```bash
# Remove E2E environment variables if causing issues  
gcloud run services update netra-backend \
    --remove-env-vars="E2E_TESTING,STAGING_E2E_TEST,E2E_TEST_ENV" \
    --platform managed \
    --region us-central1 \
    --project netra-staging
```

#### 3. Emergency Monitoring
```bash
# Monitor service health during rollback
watch -n 10 'curl -f "https://staging.netrasystems.ai/health" || echo "Service unhealthy"'
```

## Success Criteria

### ✅ Deployment Successful If:

1. **Service Health**: All health check endpoints return 200 OK
2. **Factory Validation**: WebSocket connections succeed without 1011 errors
3. **E2E Auth Bypass**: Invalid JWTs with E2E context connect successfully in staging
4. **Integration Tests**: All new integration tests pass
5. **E2E Test Suite**: Original failing tests now pass
6. **Production Security**: Production still rejects E2E bypass attempts
7. **Monitoring**: Log patterns show enhanced validation and E2E bypass working

### ❌ Rollback Required If:

1. **Service Degradation**: Health checks failing or error rates increased
2. **Factory Validation Still Failing**: Still seeing 1011 WebSocket errors
3. **E2E Auth Still Broken**: Still seeing 1008 policy violations in staging
4. **Production Compromise**: E2E bypass somehow enabled in production
5. **Regression**: Previously working functionality now broken

---

**Estimated Verification Time**: 45-60 minutes  
**Critical Success Metric**: 40% staging E2E test failure rate reduced to <5%  
**Business Impact**: Restoration of WebSocket chat functionality testing capability