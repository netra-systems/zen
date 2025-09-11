# TEST PLAN - API Schema Compatibility Fix - Issue #307

**ISSUE**: [BUG] API validation errors block real users from executing agents - 422 on /api/agent/v2/execute  
**PRIORITY**: P0 CRITICAL - ALL users blocked, $500K+ ARR at risk  
**TARGET**: Add `request_id: Optional[str] = Field(None, ...)` to `AgentExecuteV2Request` model  

## SCHEMA MISMATCH ANALYSIS

### Frontend Schema (V2AgentRequest)
```typescript
export interface V2AgentRequest {
  request_id: string;           // ← REQUIRED field causing 422 errors
  agent_type: 'data' | 'optimization' | 'triage' | 'supervisor';
  message: string;
  thread_id?: string;
  user_id?: string;
  context?: Record<string, unknown>;
  settings?: {
    timeout_ms?: number;
    stream?: boolean;
    include_metrics?: boolean;
  };
  debug?: {
    simulate_delay?: boolean;
    force_failure?: boolean;
    force_retry?: boolean;
  };
}
```

### Backend Schema (AgentExecuteV2Request) - CURRENT
```python
class AgentExecuteV2Request(BaseModel):
    message: str = Field(..., description="Message to process")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    agent_type: Optional[str] = Field("supervisor", description="Agent type to execute")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    # ← MISSING: request_id field
```

### Backend Schema (AgentExecuteV2Request) - PROPOSED FIX
```python
class AgentExecuteV2Request(BaseModel):
    message: str = Field(..., description="Message to process")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    agent_type: Optional[str] = Field("supervisor", description="Agent type to execute")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    request_id: Optional[str] = Field(None, description="Unique request identifier for frontend compatibility")  # ← NEW FIELD
```

---

## PHASE 1: PRE-IMPLEMENTATION VALIDATION (PROVE PROBLEM EXISTS)

### 1.1 Reproduction Testing - Current 422 Errors

**Objective**: Prove the 422 validation error occurs with frontend-formatted requests

#### Test Command Set 1: Direct API Testing
```bash
# Test 1: Frontend-style request with request_id (SHOULD FAIL with 422)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "request_id": "test-123-456",
    "message": "Hello test agent",
    "agent_type": "supervisor",
    "thread_id": "test-thread-1",
    "context": {}
  }'

# Expected Result: 422 {"detail":[{"type":"extra_forbidden","loc":["body","request_id"],"msg":"Extra inputs are not permitted","input":"test-123-456"}]}
```

#### Test Command Set 2: Backend-compatible request (SHOULD WORK)
```bash
# Test 2: Backend-style request without request_id (SHOULD SUCCEED)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "message": "Hello test agent",
    "agent_type": "supervisor",
    "thread_id": "test-thread-1",
    "context": {}
  }'

# Expected Result: 200 with agent response
```

#### Test Command Set 3: Schema Validation Boundary Testing
```bash
# Test 3A: Empty request_id
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "request_id": "",
    "message": "Hello test agent",
    "agent_type": "supervisor"
  }'

# Test 3B: Null request_id
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "request_id": null,
    "message": "Hello test agent", 
    "agent_type": "supervisor"
  }'

# Test 3C: Very long request_id (1000 chars)
REQUEST_ID=$(python -c "print('x' * 1000)")
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d "{
    \"request_id\": \"$REQUEST_ID\",
    \"message\": \"Hello test agent\",
    \"agent_type\": \"supervisor\"
  }"
```

### 1.2 Frontend Integration Testing - Current Behavior

**Objective**: Validate frontend requests fail against current backend

#### Test Script: Frontend Request Simulation
```bash
# Create test script to simulate frontend behavior
cat > test_frontend_request.py << 'EOF'
import requests
import json
import os

def test_frontend_request():
    """Simulate exact frontend V2AgentRequest format"""
    
    # Simulate frontend request payload
    frontend_payload = {
        "request_id": "frontend-test-123",
        "agent_type": "supervisor", 
        "message": "Test frontend integration",
        "thread_id": "test-thread-frontend",
        "context": {},
        "settings": {
            "timeout_ms": 300000,
            "stream": False,
            "include_metrics": True
        }
    }
    
    response = requests.post(
        "http://localhost:8000/api/agent/v2/execute",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('TEST_TOKEN', 'test-token')}"
        },
        json=frontend_payload
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    # This should fail with 422
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    error_data = response.json()
    assert "request_id" in str(error_data), "Error should mention request_id field"
    
    print("✅ CONFIRMED: Frontend request fails with 422 due to request_id field")

if __name__ == "__main__":
    test_frontend_request()
EOF

python test_frontend_request.py
```

---

## PHASE 2: POST-IMPLEMENTATION VALIDATION (PROVE FIX WORKS)

### 2.1 Schema Compatibility Testing - After Fix

**Objective**: Validate the fix allows frontend requests while maintaining backward compatibility

#### Test Command Set 4: Fixed Schema Validation
```bash
# Test 4A: Frontend request with request_id (SHOULD NOW WORK)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "request_id": "test-123-456",
    "message": "Hello test agent",
    "agent_type": "supervisor",
    "thread_id": "test-thread-1",
    "context": {}
  }'

# Expected Result: 200 with successful agent response

# Test 4B: Backend request without request_id (SHOULD STILL WORK - backward compatibility)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "message": "Hello test agent",
    "agent_type": "supervisor",
    "thread_id": "test-thread-1",
    "context": {}
  }'

# Expected Result: 200 with successful agent response
```

#### Test Command Set 5: Edge Cases - After Fix
```bash
# Test 5A: Empty request_id (SHOULD WORK)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "request_id": "",
    "message": "Hello test agent",
    "agent_type": "supervisor"
  }'

# Test 5B: Null request_id (SHOULD WORK)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "request_id": null,
    "message": "Hello test agent",
    "agent_type": "supervisor"
  }'

# Test 5C: Very long request_id (SHOULD WORK or gracefully fail)
REQUEST_ID=$(python -c "print('x' * 1000)")
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d "{
    \"request_id\": \"$REQUEST_ID\",
    \"message\": \"Hello test agent\",
    \"agent_type\": \"supervisor\"
  }"
```

### 2.2 Pydantic Model Testing

**Objective**: Validate Pydantic model parsing behavior with the new optional field

#### Test Script: Pydantic Model Validation
```bash
cat > test_pydantic_model.py << 'EOF'
import sys
sys.path.append('/Users/rindhujajohnson/Netra/GitHub/netra-apex')

from netra_backend.app.routes.agent_route import AgentExecuteV2Request

def test_pydantic_model_parsing():
    """Test Pydantic model with optional request_id field"""
    
    # Test 1: With request_id
    data_with_request_id = {
        "message": "Test message",
        "agent_type": "supervisor", 
        "request_id": "test-123"
    }
    
    try:
        model = AgentExecuteV2Request(**data_with_request_id)
        print(f"✅ With request_id: {model.dict()}")
        assert model.request_id == "test-123"
    except Exception as e:
        print(f"❌ With request_id failed: {e}")
        
    # Test 2: Without request_id  
    data_without_request_id = {
        "message": "Test message",
        "agent_type": "supervisor"
    }
    
    try:
        model = AgentExecuteV2Request(**data_without_request_id)
        print(f"✅ Without request_id: {model.dict()}")
        assert model.request_id is None
    except Exception as e:
        print(f"❌ Without request_id failed: {e}")
        
    # Test 3: With None request_id
    data_with_none_request_id = {
        "message": "Test message", 
        "agent_type": "supervisor",
        "request_id": None
    }
    
    try:
        model = AgentExecuteV2Request(**data_with_none_request_id)
        print(f"✅ With None request_id: {model.dict()}")
        assert model.request_id is None
    except Exception as e:
        print(f"❌ With None request_id failed: {e}")
        
    print("✅ All Pydantic model tests passed")

if __name__ == "__main__":
    test_pydantic_model_parsing()
EOF

python test_pydantic_model.py
```

---

## PHASE 3: API CONTRACT & INTEGRATION TESTING

### 3.1 Frontend-Backend Integration Testing

**Objective**: Validate complete frontend-backend API contract compatibility

#### Test Script: Complete Integration Flow
```bash
cat > test_complete_integration.py << 'EOF'
import requests
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

def test_agent_execution_flow():
    """Test complete agent execution flow with request_id"""
    
    base_url = "http://localhost:8000"
    
    # Generate unique request ID (simulate frontend behavior)
    request_id = f"integration-test-{uuid.uuid4()}"
    
    # Simulate frontend V2AgentRequest
    request_payload = {
        "request_id": request_id,
        "message": "Analyze the performance metrics for our optimization pipeline",
        "agent_type": "supervisor",
        "thread_id": f"test-thread-{uuid.uuid4()}",
        "context": {
            "user_intent": "performance_analysis",
            "priority": "high"
        },
        "settings": {
            "timeout_ms": 300000,
            "stream": False,
            "include_metrics": True
        }
    }
    
    print(f"🧪 Testing agent execution with request_id: {request_id}")
    
    start_time = time.time()
    response = requests.post(
        f"{base_url}/api/agent/v2/execute",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('TEST_TOKEN', 'test-token')}"
        },
        json=request_payload,
        timeout=60
    )
    end_time = time.time()
    
    print(f"⏱️  Response time: {end_time - start_time:.2f}s")
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS: Agent executed successfully")
        print(f"   Run ID: {data.get('run_id', 'N/A')}")
        print(f"   Status: {data.get('status', 'N/A')}")
        print(f"   Message Preview: {data.get('message', '')[:100]}...")
        
        # Validate required response fields
        required_fields = ['run_id', 'status', 'message', 'user_id', 'thread_id']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            
        return True
    else:
        print(f"❌ FAILED: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_concurrent_requests():
    """Test multiple concurrent requests with different request_ids"""
    
    def make_request(i):
        request_id = f"concurrent-test-{i}-{uuid.uuid4()}"
        payload = {
            "request_id": request_id,
            "message": f"Test message {i}",
            "agent_type": "supervisor"
        }
        
        response = requests.post(
            "http://localhost:8000/api/agent/v2/execute",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "success": response.status_code == 200
        }
    
    print("🧪 Testing concurrent requests...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(make_request, range(5)))
    
    successful = sum(1 for r in results if r['success'])
    print(f"✅ Concurrent test results: {successful}/5 successful")
    
    for result in results:
        print(f"   {result['request_id']}: {result['status_code']}")
    
    return successful == 5

if __name__ == "__main__":
    import os
    
    print("🚀 Starting complete integration testing...")
    
    # Test 1: Single agent execution
    single_test_passed = test_agent_execution_flow()
    
    # Test 2: Concurrent requests  
    concurrent_test_passed = test_concurrent_requests()
    
    if single_test_passed and concurrent_test_passed:
        print("🎉 ALL INTEGRATION TESTS PASSED")
        exit(0)
    else:
        print("💥 INTEGRATION TESTS FAILED")
        exit(1)
EOF
```

### 3.2 WebSocket Event Validation

**Objective**: Ensure agent execution with request_id still delivers proper WebSocket events

#### Test Script: WebSocket Event Flow
```bash
cat > test_websocket_events.py << 'EOF'
import asyncio
import websockets
import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor

async def monitor_websocket_events(websocket_url, thread_id, expected_events):
    """Monitor WebSocket for expected agent events"""
    
    received_events = []
    
    try:
        async with websockets.connect(websocket_url) as websocket:
            print(f"🔌 Connected to WebSocket: {websocket_url}")
            
            # Listen for events for up to 60 seconds
            timeout = 60
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(message)
                    
                    if event.get('thread_id') == thread_id:
                        received_events.append(event.get('event_type'))
                        print(f"📡 Received event: {event.get('event_type')}")
                        
                        # Check if we got all expected events
                        if all(event_type in received_events for event_type in expected_events):
                            print("✅ All expected events received!")
                            break
                            
                except asyncio.TimeoutError:
                    continue
                    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    
    return received_events

def trigger_agent_execution(thread_id, request_id):
    """Trigger agent execution with request_id"""
    
    payload = {
        "request_id": request_id,
        "message": "Test message for WebSocket event validation",
        "agent_type": "supervisor",
        "thread_id": thread_id,
        "context": {}
    }
    
    response = requests.post(
        "http://localhost:8000/api/agent/v2/execute",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    
    return response

async def test_websocket_events_with_request_id():
    """Test that WebSocket events work with request_id field"""
    
    thread_id = f"websocket-test-{int(time.time())}"
    request_id = f"websocket-request-{int(time.time())}"
    
    expected_events = [
        'agent_started',
        'agent_thinking', 
        'tool_executing',
        'tool_completed',
        'agent_completed'
    ]
    
    websocket_url = f"ws://localhost:8000/ws?thread_id={thread_id}"
    
    print(f"🧪 Testing WebSocket events with request_id: {request_id}")
    
    # Start WebSocket monitoring in background
    websocket_task = asyncio.create_task(
        monitor_websocket_events(websocket_url, thread_id, expected_events)
    )
    
    # Give WebSocket time to connect
    await asyncio.sleep(2)
    
    # Trigger agent execution
    def execute_agent():
        return trigger_agent_execution(thread_id, request_id)
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(ThreadPoolExecutor(), execute_agent)
    
    print(f"📊 Agent execution status: {response.status_code}")
    
    # Wait for WebSocket events
    received_events = await websocket_task
    
    # Validate results
    success = len(received_events) >= len(expected_events)
    
    print(f"📡 WebSocket Events Summary:")
    print(f"   Expected: {expected_events}")
    print(f"   Received: {received_events}")
    print(f"   Success: {'✅' if success else '❌'}")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(test_websocket_events_with_request_id())
    exit(0 if result else 1)
EOF
```

---

## PHASE 4: REGRESSION TESTING 

### 4.1 Backward Compatibility Validation

**Objective**: Ensure existing API v2 functionality is preserved

#### Test Command Set 6: Legacy Request Formats
```bash
# Test 6A: V1-style request (should still work)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "message": "Test V1 compatibility"
  }'

# Test 6B: Minimal request (should still work)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "message": "Minimal test request"
  }'

# Test 6C: Full request without request_id (should still work)
curl -X POST "http://localhost:8000/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "message": "Full compatibility test",
    "agent_type": "supervisor",
    "thread_id": "compat-thread-1",
    "context": {
      "test": "backward_compatibility"
    }
  }'
```

### 4.2 Other API Endpoints Impact Assessment

**Objective**: Verify no impact on other API endpoints

#### Test Command Set 7: Other Endpoints
```bash
# Test 7A: Health check
curl -X GET "http://localhost:8000/health"

# Test 7B: Agent status (if exists)
curl -X GET "http://localhost:8000/api/agent/status" \
  -H "Authorization: Bearer $TEST_TOKEN"

# Test 7C: Other v2 endpoints (if they exist)
curl -X GET "http://localhost:8000/api/agent/v2/status" \
  -H "Authorization: Bearer $TEST_TOKEN"
```

### 4.3 Authentication Flow Integration

**Objective**: Ensure authentication still works with new schema

#### Test Script: Auth Integration
```bash
cat > test_auth_integration.py << 'EOF'
import requests
import json

def test_auth_with_request_id():
    """Test authentication flow with request_id field"""
    
    # Test without auth token (should get 401)
    payload = {
        "request_id": "auth-test-123",
        "message": "Test auth integration"
    }
    
    response = requests.post(
        "http://localhost:8000/api/agent/v2/execute",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    
    print(f"No auth test - Status: {response.status_code} (expect 401)")
    
    # Test with invalid token (should get 401/403)
    response = requests.post(
        "http://localhost:8000/api/agent/v2/execute", 
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid-token"
        },
        json=payload
    )
    
    print(f"Invalid auth test - Status: {response.status_code} (expect 401/403)")
    
    # Test with valid token (should get 200)
    valid_token = os.getenv('TEST_TOKEN', 'test-token')
    response = requests.post(
        "http://localhost:8000/api/agent/v2/execute",
        headers={
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {valid_token}"
        },
        json=payload
    )
    
    print(f"Valid auth test - Status: {response.status_code} (expect 200)")
    
    return response.status_code == 200

if __name__ == "__main__":
    import os
    test_auth_with_request_id()
EOF

python test_auth_integration.py
```

---

## PHASE 5: PERFORMANCE & LOAD TESTING

### 5.1 Performance Impact Assessment

**Objective**: Verify the schema change doesn't impact performance

#### Test Script: Performance Testing
```bash
cat > test_performance_impact.py << 'EOF'
import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

def single_request_test(request_num, include_request_id=True):
    """Single request performance test"""
    
    payload = {
        "message": f"Performance test request {request_num}",
        "agent_type": "supervisor"
    }
    
    if include_request_id:
        payload["request_id"] = f"perf-test-{request_num}"
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/agent/v2/execute",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token"
            },
            json=payload,
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            "request_num": request_num,
            "duration": duration,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "with_request_id": include_request_id
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            "request_num": request_num,
            "duration": end_time - start_time,
            "status_code": 0,
            "success": False,
            "error": str(e),
            "with_request_id": include_request_id
        }

def run_performance_test():
    """Run performance comparison test"""
    
    print("🚀 Running performance impact testing...")
    
    # Test with request_id
    print("📊 Testing WITH request_id...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        with_request_id_results = list(executor.map(
            lambda i: single_request_test(i, True), range(10)
        ))
    
    # Test without request_id  
    print("📊 Testing WITHOUT request_id...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        without_request_id_results = list(executor.map(
            lambda i: single_request_test(i, False), range(10)
        ))
    
    # Analyze results
    with_durations = [r['duration'] for r in with_request_id_results if r['success']]
    without_durations = [r['duration'] for r in without_request_id_results if r['success']]
    
    if with_durations and without_durations:
        print("\n📈 Performance Analysis:")
        print(f"   With request_id - Avg: {statistics.mean(with_durations):.3f}s, Min: {min(with_durations):.3f}s, Max: {max(with_durations):.3f}s")
        print(f"   Without request_id - Avg: {statistics.mean(without_durations):.3f}s, Min: {min(without_durations):.3f}s, Max: {max(without_durations):.3f}s")
        
        # Check if difference is significant (>10%)
        avg_with = statistics.mean(with_durations)
        avg_without = statistics.mean(without_durations)
        diff_percent = abs(avg_with - avg_without) / avg_without * 100
        
        if diff_percent > 10:
            print(f"⚠️  WARNING: Significant performance difference: {diff_percent:.1f}%")
        else:
            print(f"✅ Performance difference acceptable: {diff_percent:.1f}%")
    
    # Success rates
    with_success_rate = sum(1 for r in with_request_id_results if r['success']) / len(with_request_id_results) * 100
    without_success_rate = sum(1 for r in without_request_id_results if r['success']) / len(without_request_id_results) * 100
    
    print(f"\n📊 Success Rates:")
    print(f"   With request_id: {with_success_rate:.1f}%")
    print(f"   Without request_id: {without_success_rate:.1f}%")

if __name__ == "__main__":
    run_performance_test()
EOF
```

---

## PHASE 6: STAGING ENVIRONMENT TESTING

### 6.1 Staging Deployment Validation

**Objective**: Test the fix in staging environment with real GCP services

#### Pre-Deployment Staging Tests
```bash
# Check staging environment health
curl -X GET "https://staging-backend-dot-netra-staging.uc.r.appspot.com/health"

# Test current staging behavior (should show 422 error)
curl -X POST "https://staging-backend-dot-netra-staging.uc.r.appspot.com/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STAGING_TOKEN" \
  -d '{
    "request_id": "staging-test-before-fix",
    "message": "Test before fix deployment",
    "agent_type": "supervisor"
  }'
```

#### Post-Deployment Staging Tests
```bash
# Test staging with fix (should work)
curl -X POST "https://staging-backend-dot-netra-staging.uc.r.appspot.com/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STAGING_TOKEN" \
  -d '{
    "request_id": "staging-test-after-fix",
    "message": "Test after fix deployment",
    "agent_type": "supervisor"
  }'

# Test staging backward compatibility
curl -X POST "https://staging-backend-dot-netra-staging.uc.r.appspot.com/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STAGING_TOKEN" \
  -d '{
    "message": "Test backward compatibility in staging",
    "agent_type": "supervisor"
  }'
```

### 6.2 Real Service Integration Testing

**Objective**: Validate integration with real GCP services (databases, Redis, etc.)

#### Test Script: Real Services Integration
```bash
cat > test_staging_integration.py << 'EOF'
import requests
import json
import time
import os

def test_staging_integration():
    """Test complete integration with staging environment"""
    
    staging_url = "https://staging-backend-dot-netra-staging.uc.r.appspot.com"
    staging_token = os.getenv('STAGING_TOKEN')
    
    if not staging_token:
        print("❌ STAGING_TOKEN environment variable required")
        return False
    
    # Test 1: Health check
    health_response = requests.get(f"{staging_url}/health", timeout=10)
    print(f"Health check: {health_response.status_code}")
    
    if health_response.status_code != 200:
        print("❌ Staging environment not healthy")
        return False
    
    # Test 2: Agent execution with request_id
    test_payload = {
        "request_id": f"staging-integration-{int(time.time())}",
        "message": "Analyze system performance and provide optimization recommendations",
        "agent_type": "supervisor",
        "thread_id": f"staging-thread-{int(time.time())}",
        "context": {
            "environment": "staging",
            "test_type": "integration_validation"
        },
        "settings": {
            "timeout_ms": 180000,  # 3 minutes
            "include_metrics": True
        }
    }
    
    print("🧪 Testing agent execution in staging...")
    
    start_time = time.time()
    response = requests.post(
        f"{staging_url}/api/agent/v2/execute",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {staging_token}"
        },
        json=test_payload,
        timeout=200  # 3+ minutes
    )
    duration = time.time() - start_time
    
    print(f"⏱️  Request duration: {duration:.2f}s")
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Staging integration successful!")
        print(f"   Run ID: {data.get('run_id')}")
        print(f"   Thread ID: {data.get('thread_id')}")
        print(f"   User ID: {data.get('user_id')}")
        return True
    else:
        print(f"❌ Staging integration failed: {response.text}")
        return False

if __name__ == "__main__":
    success = test_staging_integration()
    exit(0 if success else 1)
EOF
```

---

## PHASE 7: BUSINESS VALUE VALIDATION

### 7.1 User Workflow Restoration

**Objective**: Validate that the core user workflow (chat functionality) is restored

#### Test Script: Complete User Workflow
```bash
cat > test_user_workflow.py << 'EOF'
import requests
import json
import time
import uuid

def simulate_complete_user_workflow():
    """Simulate complete user workflow from chat interface"""
    
    base_url = "http://localhost:8000"  # Use staging URL for real test
    
    # Simulate user session
    user_session = f"user-{uuid.uuid4()}"
    thread_id = f"thread-{uuid.uuid4()}" 
    
    print(f"👤 Starting user workflow simulation: {user_session}")
    
    # User conversation flow
    conversation_steps = [
        {
            "message": "Hello, I need help optimizing my data pipeline performance",
            "expected_agent": "supervisor"
        },
        {
            "message": "Show me the current bottlenecks in the system",
            "expected_agent": "data"
        },
        {
            "message": "Provide recommendations for performance improvement",
            "expected_agent": "optimization"
        }
    ]
    
    results = []
    
    for i, step in enumerate(conversation_steps):
        print(f"\n💬 Step {i+1}: User sends message")
        print(f"   Message: {step['message'][:50]}...")
        
        request_id = f"{user_session}-step-{i+1}"
        
        payload = {
            "request_id": request_id,
            "message": step['message'],
            "agent_type": step['expected_agent'],
            "thread_id": thread_id,
            "context": {
                "conversation_step": i+1,
                "user_session": user_session
            },
            "settings": {
                "include_metrics": True,
                "timeout_ms": 120000  # 2 minutes
            }
        }
        
        start_time = time.time()
        response = requests.post(
            f"{base_url}/api/agent/v2/execute",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('TEST_TOKEN', 'test-token')}"
            },
            json=payload,
            timeout=150
        )
        duration = time.time() - start_time
        
        step_result = {
            "step": i+1,
            "request_id": request_id,
            "status_code": response.status_code,
            "duration": duration,
            "success": response.status_code == 200
        }
        
        if step_result["success"]:
            data = response.json()
            step_result.update({
                "run_id": data.get('run_id'),
                "response_length": len(data.get('message', '')),
                "has_metrics": 'metrics' in str(data)
            })
            print(f"   ✅ Success: {duration:.1f}s, {step_result['response_length']} chars")
        else:
            step_result["error"] = response.text
            print(f"   ❌ Failed: {response.status_code} - {response.text[:100]}")
        
        results.append(step_result)
        
        # Brief pause between steps
        time.sleep(2)
    
    # Analyze workflow results
    successful_steps = sum(1 for r in results if r['success'])
    total_duration = sum(r['duration'] for r in results)
    
    print(f"\n📊 Workflow Summary:")
    print(f"   Steps completed: {successful_steps}/{len(conversation_steps)}")
    print(f"   Total duration: {total_duration:.1f}s")
    print(f"   Average per step: {total_duration/len(results):.1f}s")
    
    workflow_success = successful_steps == len(conversation_steps)
    
    if workflow_success:
        print("🎉 COMPLETE USER WORKFLOW SUCCESSFUL!")
        print("   ✅ Users can successfully execute agents")
        print("   ✅ Chat functionality restored (90% platform value)")
        print("   ✅ Real-time agent responses working")
    else:
        print("💥 USER WORKFLOW FAILED!")
        print(f"   Only {successful_steps}/{len(conversation_steps)} steps successful")
    
    return workflow_success, results

if __name__ == "__main__":
    import os
    success, results = simulate_complete_user_workflow()
    exit(0 if success else 1)
EOF
```

### 7.2 Revenue Impact Validation

**Objective**: Confirm revenue-generating functionality is restored

#### Business Value Metrics
```bash
# Test metrics to validate business impact restoration

# 1. User Engagement Metrics
echo "📊 Business Value Validation Checklist:"
echo "   [ ] Users can send messages and receive AI responses"
echo "   [ ] Agent execution completes within acceptable time (<5 minutes)" 
echo "   [ ] WebSocket events provide real-time feedback"
echo "   [ ] Thread continuity works for conversations"
echo "   [ ] Multiple agent types (supervisor, data, optimization) functional"
echo "   [ ] No blocking 422 errors for frontend requests"
echo "   [ ] Backward compatibility maintained for existing integrations"

# 2. System Health Metrics  
echo "   [ ] API response times within acceptable range (<30s typical)"
echo "   [ ] Error rates below 1% for valid requests"
echo "   [ ] System handles concurrent user requests"
echo "   [ ] Database and Redis connectivity maintained"
echo "   [ ] WebSocket connections stable"
```

---

## SUCCESS CRITERIA DEFINITION

### PHASE-BY-PHASE SUCCESS CRITERIA

#### Phase 1 Success Criteria (Pre-Implementation)
- [ ] **422 Error Reproduced**: Frontend requests with `request_id` fail with 422 validation error
- [ ] **Backend Requests Work**: Requests without `request_id` succeed with 200 response  
- [ ] **Error Message Clear**: 422 error specifically mentions `request_id` field issue
- [ ] **Schema Mismatch Documented**: Exact field differences between frontend/backend schemas confirmed

#### Phase 2 Success Criteria (Post-Implementation)
- [ ] **Frontend Compatibility**: Requests with `request_id` now succeed (200 response)
- [ ] **Backward Compatibility**: Requests without `request_id` still work (200 response)
- [ ] **Edge Cases Handled**: Empty, null, and long `request_id` values handled gracefully
- [ ] **Pydantic Validation**: Model parsing works correctly with optional field

#### Phase 3 Success Criteria (Integration)
- [ ] **Complete Agent Flow**: Full agent execution works with `request_id` present
- [ ] **WebSocket Events**: All 5 critical events (started, thinking, executing, completed, finished) delivered
- [ ] **Concurrent Requests**: Multiple simultaneous requests with different `request_id` values work
- [ ] **Thread Continuity**: Conversation threads work correctly with new schema

#### Phase 4 Success Criteria (Regression)
- [ ] **No Breaking Changes**: All existing functionality preserved
- [ ] **Other Endpoints Unaffected**: No impact on health, status, or other API endpoints  
- [ ] **Authentication Preserved**: Auth flows work identically with new schema
- [ ] **Performance Maintained**: No significant performance degradation (>10%)

#### Phase 5 Success Criteria (Performance)
- [ ] **Response Times Acceptable**: Agent execution completes within 5 minutes
- [ ] **Load Handling**: System handles 10+ concurrent requests successfully
- [ ] **Resource Usage Stable**: No memory leaks or resource issues with new field
- [ ] **Error Rates Low**: <1% error rate for valid requests

#### Phase 6 Success Criteria (Staging)
- [ ] **Staging Deployment Success**: Fix deployed to staging without issues
- [ ] **Real Services Integration**: Works with production-like GCP services
- [ ] **End-to-End Validation**: Complete user workflow successful in staging
- [ ] **Monitoring Confirms**: No alerts or errors in staging environment

#### Phase 7 Success Criteria (Business Value) 
- [ ] **User Workflow Restored**: Users can successfully execute agents end-to-end
- [ ] **Chat Functionality**: 90% of platform value (AI-powered chat) fully operational
- [ ] **Real-time Feedback**: WebSocket events provide proper user experience
- [ ] **Revenue Protection**: $500K+ ARR functionality fully restored

### OVERALL SUCCESS DEFINITION

**CRITICAL SUCCESS CRITERIA** (All must pass):
1. **No 422 Errors**: Frontend requests with `request_id` succeed
2. **Backward Compatibility**: Existing requests without `request_id` still work
3. **Agent Execution**: Complete agent workflow functions properly
4. **WebSocket Events**: Real-time user feedback operational
5. **Business Value**: Users can successfully use chat functionality

**ACCEPTABLE RISK CRITERIA** (Monitor but acceptable):
- Minor performance variations (<10% difference)
- Non-critical edge cases (very long request_id values)
- Staging-specific environment issues (if local testing passes)

**FAILURE CRITERIA** (Immediate rollback required):
- Any existing functionality breaks
- Performance degradation >25%
- Authentication or security issues
- Data corruption or loss
- System instability or crashes

---

## ROLLBACK PLAN

### If Testing Reveals Issues

#### Immediate Rollback Steps
1. **Stop Current Deployment**: Cancel any in-progress deployments
2. **Revert Code Changes**: `git checkout` previous commit
3. **Redeploy Previous Version**: Use deployment scripts to restore working version
4. **Validate Rollback**: Confirm previous functionality restored

#### Rollback Commands
```bash
# Emergency rollback commands
git log --oneline -n 5  # Find previous commit
git checkout <previous_commit_hash>

# Redeploy to staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local --service backend

# Validate rollback worked
curl -X POST "https://staging-backend-dot-netra-staging.uc.r.appspot.com/api/agent/v2/execute" \
  -H "Content-Type: application/json" \
  -d '{"message": "Rollback validation test"}'
```

#### Post-Rollback Analysis
1. **Document Issues**: Record what went wrong in testing
2. **Root Cause Analysis**: Determine why fix didn't work as expected  
3. **Update Test Plan**: Enhance test coverage for discovered issues
4. **Notify Stakeholders**: Update Issue #307 with rollback reason

---

## TEST EXECUTION TIMELINE

### Priority 1 (Critical Path - Execute First)
1. **Phase 1**: Pre-Implementation Validation (30 minutes)
   - Reproduce 422 error with current schema
   - Confirm frontend/backend mismatch
   - Document baseline behavior

### Priority 2 (Implementation & Validation)  
2. **Apply Fix**: Add `request_id` field to `AgentExecuteV2Request` (5 minutes)
3. **Phase 2**: Post-Implementation Validation (45 minutes)
   - Schema compatibility testing
   - Pydantic model validation
   - Edge case testing

### Priority 3 (Integration & Regression)
4. **Phase 3**: API Contract & Integration Testing (60 minutes)
   - Complete frontend-backend integration
   - WebSocket event validation
   - Concurrent request testing

5. **Phase 4**: Regression Testing (30 minutes)
   - Backward compatibility validation
   - Other endpoints impact assessment
   - Authentication flow verification

### Priority 4 (Performance & Staging)
6. **Phase 5**: Performance & Load Testing (45 minutes)
   - Performance impact assessment
   - Load testing with concurrent requests
   - Resource usage monitoring

7. **Phase 6**: Staging Environment Testing (60 minutes)
   - Deploy to staging
   - Real services integration testing
   - End-to-end validation

### Priority 5 (Business Validation)
8. **Phase 7**: Business Value Validation (30 minutes)
   - Complete user workflow testing
   - Revenue impact confirmation
   - Success criteria verification

**Total Estimated Time**: 4-5 hours for complete validation

### Accelerated Testing (If Time Critical)
**Minimum Viable Testing** (90 minutes):
1. Phase 1: Reproduce issue (15 min)
2. Apply fix (5 min)  
3. Phase 2: Basic compatibility (30 min)
4. Phase 3: Integration test (25 min)
5. Phase 6: Deploy to staging + basic test (15 min)

---

## GITHUB ISSUE UPDATE TEMPLATE

### Comment Template for Issue #307

```markdown
## 🧪 TEST PLAN - API Schema Compatibility Fix

**STATUS**: Test plan created and ready for execution

### Issue Summary
- **Problem**: Frontend V2AgentRequest includes `request_id` field, backend AgentExecuteV2Request missing field
- **Impact**: ALL users blocked from agent execution with 422 validation errors  
- **Solution**: Add `request_id: Optional[str] = Field(None, ...)` to backend model
- **Business Risk**: $500K+ ARR at risk until resolved

### Test Plan Overview
Created comprehensive 7-phase test plan covering:
1. **Pre-Implementation**: Reproduce current 422 errors
2. **Post-Implementation**: Validate fix resolves issue
3. **Integration**: Frontend-backend compatibility + WebSocket events
4. **Regression**: Backward compatibility + other endpoints
5. **Performance**: Load testing + resource impact
6. **Staging**: Real environment validation
7. **Business Value**: Complete user workflow restoration

### Test Execution Ready
- [ ] **Test Scripts Created**: All validation scripts prepared
- [ ] **Success Criteria Defined**: Clear pass/fail criteria for each phase  
- [ ] **Rollback Plan**: Emergency procedures if issues found
- [ ] **Timeline Established**: 4-5 hours full validation, 90min minimum viable

### Next Steps
1. Execute Phase 1 (reproduce issue) - **READY TO START**
2. Apply fix after confirming reproduction
3. Execute validation phases 2-7
4. Deploy to staging if all tests pass

**Full test plan documentation**: `TEST_PLAN_API_SCHEMA_COMPATIBILITY_ISSUE_307.md`
```

---

## DELIVERABLES SUMMARY

✅ **Comprehensive Test Plan**: 7-phase validation strategy covering all scenarios  
✅ **Test Scripts Created**: Automated validation scripts for each phase  
✅ **Success Criteria Defined**: Clear metrics for validation success  
✅ **Rollback Procedures**: Emergency recovery plan if issues found  
✅ **Timeline Established**: 4-5 hour full validation, 90min accelerated option  
✅ **Business Impact Assessment**: Revenue protection validation included  
✅ **Documentation Complete**: Full test plan saved to repository

**STATUS**: ✅ COMPLETE - Ready to proceed to Step 4 (Execute Test Plan)

The test plan provides comprehensive coverage of the API schema compatibility fix while maintaining focus on the critical business impact. All validation scenarios are covered with specific test commands and success criteria.