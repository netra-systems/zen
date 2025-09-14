## 🧪 COMPREHENSIVE TEST STRATEGY - WebSocket Event Structure Validation

Based on root cause analysis identifying `unified_manager.py` wrapping business data incorrectly, here is the detailed test strategy to reproduce and validate fixes:

### Root Cause Confirmed ✅
**Primary Issue:** `unified_manager.py` incorrectly wraps business event data, causing validation failures for tool_name, execution_time, and results fields in WebSocket events.

**Test Strategy:** Create failing tests that reproduce the exact validation errors, then verify proper event structure after remediation.

## 📋 TEST PLAN - Phase 1: Validation Failure Reproduction

### 1. Event Structure Validation Test Suite
**Purpose:** Create comprehensive tests that fail initially due to incorrect event wrapping, then pass after fix

**Files to Create/Update:**
- `tests/unit/websocket_core/test_event_structure_validation.py` (NEW)
- `tests/integration/websocket_core/test_real_agent_event_structures.py` (NEW)
- `tests/mission_critical/test_websocket_event_structure_golden_path.py` (UPDATE)

### 2. Failing Test Design (Must Fail Initially)

#### Test 1: Tool Executing Event Structure Validation
```python
@pytest.mark.asyncio
async def test_tool_executing_event_structure_validation():
    """Test tool_executing event contains required business fields.

    FAILS INITIALLY: unified_manager.py wraps data incorrectly
    PASSES AFTER FIX: Business data properly preserved
    """
    # Simulate real agent tool execution event
    business_event_data = {
        "type": "tool_executing",
        "tool_name": "search_analyzer",
        "tool_args": {"query": "test search"},
        "execution_id": "exec_123",
        "timestamp": time.time()
    }

    # Test that WebSocket manager preserves business structure
    manager = UnifiedWebSocketManager()
    wrapped_event = await manager._wrap_for_transmission(business_event_data)

    # CRITICAL VALIDATIONS (currently failing)
    assert "tool_name" in wrapped_event, "tool_name missing from wrapped event"
    assert wrapped_event["tool_name"] == "search_analyzer", "tool_name value incorrect"
    assert "tool_args" in wrapped_event, "tool_args missing from wrapped event"
    assert isinstance(wrapped_event["tool_args"], dict), "tool_args not dict type"
```

#### Test 2: Tool Completed Event Structure Validation
```python
@pytest.mark.asyncio
async def test_tool_completed_event_structure_validation():
    """Test tool_completed event contains execution results and metrics.

    FAILS INITIALLY: Business data wrapped incorrectly by unified_manager.py
    PASSES AFTER FIX: Results and execution_time properly preserved
    """
    business_event_data = {
        "type": "tool_completed",
        "tool_name": "search_analyzer",
        "results": {
            "found_items": 5,
            "top_result": "Critical finding"
        },
        "execution_time": 2.34,
        "success": True,
        "execution_id": "exec_123"
    }

    # Test WebSocket transmission preserves business data
    manager = UnifiedWebSocketManager()
    wrapped_event = await manager._wrap_for_transmission(business_event_data)

    # CRITICAL VALIDATIONS (currently failing)
    assert "tool_name" in wrapped_event, "tool_name missing"
    assert "results" in wrapped_event, "results missing from event"
    assert "execution_time" in wrapped_event, "execution_time missing"
    assert wrapped_event["execution_time"] == 2.34, "execution_time value incorrect"
    assert isinstance(wrapped_event["results"], dict), "results not dict type"
```

#### Test 3: Agent Started Event Structure
```python
@pytest.mark.asyncio
async def test_agent_started_event_structure_validation():
    """Test agent_started contains proper user context and identifiers."""
    business_event_data = {
        "type": "agent_started",
        "user_id": "test_user_123",
        "thread_id": "thread_456",
        "agent_name": "DataHelperAgent",
        "task_description": "Analyze user request",
        "timestamp": time.time()
    }

    manager = UnifiedWebSocketManager()
    wrapped_event = await manager._wrap_for_transmission(business_event_data)

    # Validate critical fields preserved
    assert "user_id" in wrapped_event, "user_id missing"
    assert "thread_id" in wrapped_event, "thread_id missing"
    assert "agent_name" in wrapped_event, "agent_name missing"
    assert wrapped_event["type"] == "agent_started", "event type incorrect"
```

### 3. Integration Tests with Real Agent Workflows

#### Real Agent Execution Test (Non-Docker)
```python
@pytest.mark.integration
@pytest.mark.real_services
async def test_real_agent_websocket_event_structures():
    """Test real agent execution generates proper WebSocket event structures.

    Runs against staging GCP services - NO Docker required
    """
    # Setup authenticated user and WebSocket connection
    user_context = await create_test_user_context()
    websocket_client = await create_websocket_client(
        auth_token=user_context.auth_token,
        endpoint="wss://staging.netra-apex.com/api/v1/websocket"
    )

    # Trigger real agent execution via API
    agent_request = {
        "type": "execute_agent",
        "agent_type": "data_helper",
        "message": "Please search for test data and analyze results",
        "user_id": user_context.user_id,
        "thread_id": user_context.thread_id
    }

    # Send via HTTP API to trigger WebSocket events
    response = await http_client.post(
        "https://staging.netra-apex.com/api/v1/chat/agents/execute",
        json=agent_request,
        headers={"Authorization": f"Bearer {user_context.auth_token}"}
    )

    # Collect WebSocket events from real agent execution
    events = await collect_websocket_events(
        websocket_client,
        expected_types=["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
        timeout=30.0
    )

    # Validate each event structure
    for event in events:
        if event["type"] == "tool_executing":
            assert "tool_name" in event, f"tool_executing missing tool_name: {event}"
            assert "tool_args" in event, f"tool_executing missing tool_args: {event}"

        elif event["type"] == "tool_completed":
            assert "tool_name" in event, f"tool_completed missing tool_name: {event}"
            assert "results" in event, f"tool_completed missing results: {event}"
            assert "execution_time" in event, f"tool_completed missing execution_time: {event}"

        elif event["type"] == "agent_started":
            assert "user_id" in event, f"agent_started missing user_id: {event}"
            assert "thread_id" in event, f"agent_started missing thread_id: {event}"
```

### 4. Negative Test Cases (Edge Cases)

#### Test Invalid Event Wrapping
```python
@pytest.mark.asyncio
async def test_event_wrapping_preserves_all_fields():
    """Test that NO business fields are lost during WebSocket wrapping."""
    complex_business_event = {
        "type": "tool_completed",
        "tool_name": "complex_analyzer",
        "tool_version": "v2.1.0",
        "results": {
            "analysis_complete": True,
            "findings": ["item1", "item2"],
            "metadata": {"confidence": 0.95}
        },
        "execution_time": 5.67,
        "performance_metrics": {
            "memory_usage": "128MB",
            "cpu_time": "3.2s"
        },
        "success": True,
        "correlation_id": "corr_789"
    }

    manager = UnifiedWebSocketManager()
    wrapped_event = await manager._wrap_for_transmission(complex_business_event)

    # Verify ALL original fields preserved
    for key, value in complex_business_event.items():
        assert key in wrapped_event, f"Field {key} lost during wrapping"
        assert wrapped_event[key] == value, f"Field {key} value changed during wrapping"
```

## 📊 TEST EXECUTION STRATEGY

### Phase 1: Unit Tests (Immediate - No Docker)
```bash
# Run failing tests to confirm issue reproduction
python -m pytest tests/unit/websocket_core/test_event_structure_validation.py -v

# Expected result: Tests FAIL due to unified_manager.py wrapping issue
```

### Phase 2: Integration Tests (Staging GCP - No Docker)
```bash
# Run real agent workflow tests against staging
python -m pytest tests/integration/websocket_core/test_real_agent_event_structures.py -v --env=staging

# Tests use real staging services via HTTPS/WSS endpoints
```

### Phase 3: Mission Critical Validation
```bash
# Run updated mission critical tests
python tests/mission_critical/test_websocket_event_structure_golden_path.py

# Must pass 100% after unified_manager.py fix
```

## ✅ SUCCESS CRITERIA

### Before Fix (Tests Must Fail):
- [ ] `tool_name` missing from `tool_executing` events
- [ ] `results` missing from `tool_completed` events
- [ ] `execution_time` missing from `tool_completed` events
- [ ] Business data incorrectly nested/wrapped

### After Fix (Tests Must Pass):
- [ ] All 5 WebSocket events contain required business fields
- [ ] Event structure matches Golden Path requirements
- [ ] No business data lost during WebSocket transmission
- [ ] Real agent workflows generate properly structured events

## 🚀 IMPLEMENTATION TIMELINE

1. **Day 1:** Create failing unit tests (reproduce exact validation errors)
2. **Day 1:** Create integration tests with staging GCP services
3. **Day 2:** Update mission critical test suite with new validations
4. **Day 2:** Run test suite to confirm failures before fix
5. **Day 3:** Implement `unified_manager.py` fix based on test failures
6. **Day 3:** Validate all tests pass after remediation

**📋 Complete remediation plan:** [View Full Plan](https://github.com/netra-systems/netra-apex/blob/develop-long-lived/issue_1021_remediation_plan.md)

**⚡ Priority:** P0 CRITICAL - Blocks $500K+ ARR Golden Path validation
**🎯 Business Impact:** Enables proper validation of real-time chat functionality that delivers 90% of platform value
**🧪 Test Focus:** Comprehensive validation of WebSocket event structures without Docker dependencies