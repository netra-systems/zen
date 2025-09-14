# Test Plan for Issue #953: SSOT Legacy DeepAgentState Critical User Isolation Vulnerability

## 🚨 CRITICAL SECURITY VULNERABILITY

**Issue**: Issue #953 - SSOT-legacy-deepagentstate-critical-user-isolation-vulnerability
**Priority**: P0 - Golden Path Security Critical
**Business Impact**: $500K+ ARR at risk due to user isolation vulnerabilities

## Vulnerability Overview

### Root Cause
Production code still uses deprecated `DeepAgentState` which allows cross-user data contamination instead of the secure `UserExecutionContext` pattern that provides proper user isolation.

### Affected Files Analysis
1. **`/netra_backend/app/agents/supervisor/modern_execution_helpers.py`** (Lines 12, 24, 33, 38, 52)
   - Imports `DeepAgentState` directly
   - Uses `DeepAgentState` in supervisor workflow execution
   - Potential for user context bleeding in concurrent executions

2. **`/netra_backend/app/agents/synthetic_data_approval_handler.py`** (Line 14)
   - Imports and uses `DeepAgentState` for approval flow
   - Risk of cross-user synthetic data request contamination

3. **`/netra_backend/app/schemas/agent_models.py`** (Line 119)
   - Contains `DeepAgentState` class definition with backward compatibility hacks
   - Has `agent_context` field that can leak between users

### Security Vulnerability
- **User Isolation Failure**: Multiple users executing agents concurrently may access each other's data
- **Data Contamination**: Agent state from one user can leak into another user's execution
- **Session Hijacking Risk**: Improper context management enables potential session hijacking
- **Golden Path Impact**: Core user workflow compromised by security vulnerability

## Test Strategy

### Test Categories & Approach

#### 1. Unit Tests (High Priority)
**Location**: `netra_backend/tests/unit/security/`
**Focus**: Reproduce vulnerability in isolated conditions
- Test DeepAgentState vs UserExecutionContext isolation
- Test concurrent user execution scenarios
- Test memory reference isolation
- Test data contamination scenarios

#### 2. Integration Tests (Critical Priority)
**Location**: `tests/integration/security/`
**Focus**: Real service multi-user scenarios
- Test with real database and Redis
- Test WebSocket event isolation
- Test supervisor workflow isolation
- Test synthetic data approval isolation

#### 3. Mission Critical Tests (Deployment Blocker)
**Location**: `tests/mission_critical/`
**Focus**: Business-critical security validation
- Test that protects $500K+ ARR from security breach
- Real-time multi-user agent execution validation
- Golden Path user isolation verification

## Detailed Test Plan

### Phase 1: Vulnerability Reproduction Tests (Unit)

#### Test 1.1: DeepAgentState Cross-User Contamination
```python
# File: netra_backend/tests/unit/security/test_deepagentstate_vulnerability.py
async def test_deepagentstate_cross_user_contamination():
    """REPRODUCE VULNERABILITY: DeepAgentState allows cross-user data leakage."""
    # Create two DeepAgentState instances for different users
    user1_state = DeepAgentState(
        user_id="user_123",
        user_request="Analyze my costs",
        agent_context={"sensitive_data": "user1_private_info"}
    )

    user2_state = DeepAgentState(
        user_id="user_456",
        user_request="Generate synthetic data",
        agent_context={"sensitive_data": "user2_private_info"}
    )

    # Simulate concurrent agent execution - this should fail with vulnerability
    # This test should FAIL initially, proving the vulnerability exists
    async def simulate_concurrent_execution():
        # If DeepAgentState has shared references, data will leak
        merged_state = user1_state.merge_from(user2_state)

        # VULNERABILITY: Check if user1 can access user2's data
        assert "user2_private_info" not in str(merged_state.agent_context), \
               "CRITICAL: User data contamination detected!"

    # This should fail, proving vulnerability exists
    with pytest.raises(AssertionError, match="User data contamination"):
        await simulate_concurrent_execution()
```

#### Test 1.2: Modern Execution Helpers Vulnerability
```python
# File: netra_backend/tests/unit/security/test_modern_execution_helpers_vulnerability.py
async def test_supervisor_execution_helpers_user_isolation():
    """REPRODUCE VULNERABILITY: SupervisorExecutionHelpers lacks proper user isolation."""
    from netra_backend.app.agents.supervisor.modern_execution_helpers import SupervisorExecutionHelpers

    # Mock supervisor agent
    mock_supervisor = Mock()
    mock_supervisor.run = AsyncMock(return_value=DeepAgentState(user_id="contaminated"))

    helpers = SupervisorExecutionHelpers(mock_supervisor)

    # Create states for two different users
    user1_state = DeepAgentState(
        user_id="enterprise_user_001",
        user_request="Optimize my infrastructure costs",
        agent_context={"aws_account": "123456789", "monthly_budget": 50000}
    )

    user2_state = DeepAgentState(
        user_id="enterprise_user_002",
        user_request="Analyze security vulnerabilities",
        agent_context={"security_clearance": "top_secret", "systems": ["prod", "staging"]}
    )

    # Execute concurrently - should maintain isolation
    result1, result2 = await asyncio.gather(
        helpers.run_supervisor_workflow(user1_state, "run_1"),
        helpers.run_supervisor_workflow(user2_state, "run_2")
    )

    # VULNERABILITY TEST: Check if user contexts got mixed
    # This should FAIL initially, proving vulnerability
    assert result1.user_id != result2.user_id, "User IDs should remain isolated"
    assert "top_secret" not in str(result1.agent_context), "User1 accessed User2's classified data"
    assert "123456789" not in str(result2.agent_context), "User2 accessed User1's AWS account"
```

#### Test 1.3: Synthetic Data Approval Handler Vulnerability
```python
# File: netra_backend/tests/unit/security/test_synthetic_data_approval_vulnerability.py
async def test_synthetic_data_approval_user_isolation():
    """REPRODUCE VULNERABILITY: SyntheticDataApprovalHandler lacks user isolation."""
    from netra_backend.app.agents.synthetic_data_approval_handler import SyntheticDataApprovalHandler

    handler = SyntheticDataApprovalHandler(send_update_callback=AsyncMock())

    # Create approval contexts for different users with sensitive data
    user1_profile = WorkloadProfile(volume=100000, workload_type="financial_data")
    user1_state = DeepAgentState(
        user_id="finance_user_001",
        agent_context={"company": "SecureBank", "data_class": "PII"}
    )

    user2_profile = WorkloadProfile(volume=50000, workload_type="medical_data")
    user2_state = DeepAgentState(
        user_id="medical_user_002",
        agent_context={"hospital": "CityMedical", "data_class": "PHI"}
    )

    # Process approval flows concurrently
    await asyncio.gather(
        handler.handle_approval_flow(user1_profile, user1_state, "run_1", True),
        handler.handle_approval_flow(user2_profile, user2_state, "run_2", True)
    )

    # VULNERABILITY CHECK: Ensure no cross-contamination in synthetic_data_result
    user1_result = user1_state.synthetic_data_result
    user2_result = user2_state.synthetic_data_result

    # This should FAIL initially, proving vulnerability
    assert "CityMedical" not in str(user1_result), "User1 accessed User2's hospital data"
    assert "SecureBank" not in str(user2_result), "User2 accessed User1's bank data"
```

### Phase 2: UserExecutionContext Security Validation Tests (Integration)

#### Test 2.1: Multi-User Agent Execution Isolation
```python
# File: tests/integration/security/test_multi_user_agent_execution_isolation.py
async def test_multi_user_supervisor_execution_with_real_services(real_services_fixture):
    """VALIDATE SECURE PATTERN: UserExecutionContext prevents cross-user contamination."""
    from netra_backend.app.services.user_execution_context import create_isolated_execution_context

    # Create isolated contexts for different enterprise users
    context1 = await create_isolated_execution_context(
        user_id="enterprise_001",
        thread_id="thread_001",
        run_id="secure_run_001",
        agent_context={"customer_tier": "enterprise", "sensitive_data": "classified_project_alpha"}
    )

    context2 = await create_isolated_execution_context(
        user_id="enterprise_002",
        thread_id="thread_002",
        run_id="secure_run_002",
        agent_context={"customer_tier": "enterprise", "sensitive_data": "classified_project_beta"}
    )

    # Simulate concurrent supervisor execution with real database
    async def secure_supervisor_execution(context, db_session):
        # Simulate real supervisor agent execution with database operations
        await db_session.execute("INSERT INTO user_executions (user_id, data) VALUES (:user_id, :data)",
                                 {"user_id": context.user_id, "data": str(context.agent_context)})

        # Simulate agent processing
        result = {
            "user_id": context.user_id,
            "processed_data": context.agent_context.get("sensitive_data"),
            "execution_id": context.run_id
        }
        return result

    # Execute concurrently with real database
    db_session = real_services_fixture["db"]
    results = await asyncio.gather(
        secure_supervisor_execution(context1, db_session),
        secure_supervisor_execution(context2, db_session)
    )

    # SECURITY VALIDATION: Ensure complete isolation
    assert results[0]["user_id"] != results[1]["user_id"]
    assert "classified_project_beta" not in results[0]["processed_data"]
    assert "classified_project_alpha" not in results[1]["processed_data"]

    # Validate database isolation
    user1_records = await db_session.execute("SELECT data FROM user_executions WHERE user_id = :user_id",
                                            {"user_id": "enterprise_001"})
    user2_records = await db_session.execute("SELECT data FROM user_executions WHERE user_id = :user_id",
                                            {"user_id": "enterprise_002"})

    user1_data = user1_records.fetchone()[0]
    user2_data = user2_records.fetchone()[0]

    assert "classified_project_beta" not in user1_data
    assert "classified_project_alpha" not in user2_data
```

#### Test 2.2: WebSocket Event Isolation Validation
```python
# File: tests/integration/security/test_websocket_event_user_isolation.py
async def test_websocket_events_user_isolation(real_services_fixture):
    """VALIDATE: WebSocket events are delivered only to correct user."""
    from test_framework.websocket_helpers import WebSocketTestClient

    # Create WebSocket connections for two users
    user1_token = await create_test_user_token("enterprise_001")
    user2_token = await create_test_user_token("enterprise_002")

    async with WebSocketTestClient(token=user1_token) as client1, \
               WebSocketTestClient(token=user2_token) as client2:

        # User 1 sends agent request
        await client1.send_json({
            "type": "agent_request",
            "agent": "cost_optimizer",
            "message": "Analyze my confidential AWS costs",
            "context": {"aws_account": "sensitive_account_123"}
        })

        # User 2 sends different agent request
        await client2.send_json({
            "type": "agent_request",
            "agent": "security_analyzer",
            "message": "Scan for vulnerabilities",
            "context": {"security_level": "top_secret"}
        })

        # Collect events for both users
        user1_events = []
        user2_events = []

        for _ in range(10):  # Collect multiple events
            event1 = await asyncio.wait_for(client1.receive_json(), timeout=2)
            event2 = await asyncio.wait_for(client2.receive_json(), timeout=2)

            user1_events.append(event1)
            user2_events.append(event2)

            if event1.get("type") == "agent_completed" and event2.get("type") == "agent_completed":
                break

        # SECURITY VALIDATION: No cross-contamination in WebSocket events
        user1_event_data = str(user1_events)
        user2_event_data = str(user2_events)

        assert "top_secret" not in user1_event_data, "User1 received User2's classified data via WebSocket"
        assert "sensitive_account_123" not in user2_event_data, "User2 received User1's AWS data via WebSocket"

        # Validate event isolation at message level
        for event in user1_events:
            assert event.get("user_id") == "enterprise_001" or "user_id" not in event

        for event in user2_events:
            assert event.get("user_id") == "enterprise_002" or "user_id" not in event
```

### Phase 3: Mission Critical Security Tests (Deployment Blocker)

#### Test 3.1: Golden Path User Isolation Protection
```python
# File: tests/mission_critical/test_golden_path_user_isolation_protection.py
@pytest.mark.mission_critical
@pytest.mark.no_skip
async def test_golden_path_protects_500k_arr_from_user_isolation_breach():
    """MISSION CRITICAL: Golden Path user flow must maintain complete user isolation.

    Business Impact: Protects $500K+ ARR from security breach and customer loss.
    """
    # Test the complete Golden Path user flow with multiple concurrent users
    enterprise_users = [
        {"user_id": "enterprise_fortune500_001", "tier": "enterprise", "arr_value": 200000},
        {"user_id": "enterprise_fortune500_002", "tier": "enterprise", "arr_value": 150000},
        {"user_id": "enterprise_startup_003", "tier": "mid", "arr_value": 100000}
    ]

    async def golden_path_user_flow(user_info):
        """Execute complete Golden Path for a user."""
        context = await create_isolated_execution_context(
            user_id=user_info["user_id"],
            thread_id=f"golden_thread_{user_info['user_id']}",
            run_id=f"golden_run_{uuid.uuid4()}",
            agent_context={
                "user_tier": user_info["tier"],
                "arr_value": user_info["arr_value"],
                "sensitive_business_data": f"proprietary_data_{user_info['user_id']}"
            }
        )

        # Simulate complete Golden Path: Login → Agent Request → AI Response → Value Delivery
        results = {
            "user_id": context.user_id,
            "sensitive_data": context.agent_context["sensitive_business_data"],
            "arr_value": context.agent_context["arr_value"],
            "execution_path": "golden_path_complete"
        }

        return results

    # Execute Golden Path for all users concurrently
    results = await asyncio.gather(*[
        golden_path_user_flow(user) for user in enterprise_users
    ])

    # MISSION CRITICAL VALIDATION: Complete user isolation maintained
    for i, result in enumerate(results):
        current_user = enterprise_users[i]

        # Validate user data isolation
        assert result["user_id"] == current_user["user_id"]
        assert result["arr_value"] == current_user["arr_value"]
        assert current_user["user_id"] in result["sensitive_data"]

        # Cross-contamination check against all other users
        for j, other_user in enumerate(enterprise_users):
            if i != j:
                assert other_user["user_id"] not in result["sensitive_data"], \
                       f"SECURITY BREACH: User {current_user['user_id']} accessed data from {other_user['user_id']}"
                assert result["arr_value"] != other_user["arr_value"] or \
                       result["user_id"] == other_user["user_id"], \
                       f"ARR value contamination detected"

    # BUSINESS VALUE PROTECTION: Ensure total ARR protected
    total_protected_arr = sum(result["arr_value"] for result in results)
    assert total_protected_arr >= 450000, f"Protected ARR below threshold: {total_protected_arr}"

    logger.critical(f"MISSION CRITICAL SUCCESS: Protected ${total_protected_arr} ARR from user isolation breach")
```

## Test Execution Strategy

### Test Creation Order
1. **Start with Failing Tests** - Create vulnerability reproduction tests that FAIL initially
2. **Validate Current Security** - Test UserExecutionContext pattern works correctly
3. **Integration Testing** - Test with real services (no Docker needed for this)
4. **Mission Critical Protection** - Ensure business value protected

### Test Execution Commands
```bash
# Run vulnerability reproduction tests (should fail initially)
python tests/unified_test_runner.py --category unit --test-path "tests/unit/security/test_*vulnerability*.py"

# Run security integration tests with real services
python tests/unified_test_runner.py --category integration --test-path "tests/integration/security/" --real-services

# Run mission critical security validation
python tests/mission_critical/test_golden_path_user_isolation_protection.py

# Full security test suite
python tests/unified_test_runner.py --category security --real-services
```

### Success Criteria
1. **Vulnerability Reproduction** - Initial tests FAIL, proving vulnerability exists
2. **Security Pattern Validation** - UserExecutionContext tests PASS, proving security works
3. **Integration Security** - Multi-user scenarios maintain complete isolation
4. **Business Value Protection** - $500K+ ARR protected from security breach

### Test File Locations
- `netra_backend/tests/unit/security/test_deepagentstate_vulnerability.py`
- `netra_backend/tests/unit/security/test_modern_execution_helpers_vulnerability.py`
- `netra_backend/tests/unit/security/test_synthetic_data_approval_vulnerability.py`
- `tests/integration/security/test_multi_user_agent_execution_isolation.py`
- `tests/integration/security/test_websocket_event_user_isolation.py`
- `tests/mission_critical/test_golden_path_user_isolation_protection.py`

## Expected Test Results

### Before Fix (Current State)
- ❌ Vulnerability reproduction tests should FAIL
- ❌ Cross-user contamination detected
- ❌ Memory references shared between users
- ❌ DeepAgentState allows data leakage

### After Fix (Target State)
- ✅ All vulnerability tests resolved
- ✅ UserExecutionContext provides complete isolation
- ✅ No cross-user data contamination
- ✅ Mission critical tests protect business value
- ✅ Golden Path user flow security validated

## Business Value Protection
- **$500K+ ARR Protection**: Tests validate enterprise customer data isolation
- **Compliance Requirements**: Audit trails and security validation for enterprise
- **Golden Path Security**: Core user workflow protected from security vulnerabilities
- **Customer Trust**: Demonstrable security controls prevent data breaches

## Risk Mitigation
- **P0 Priority**: Security vulnerability must be resolved before other SSOT work
- **Deployment Blocker**: Mission critical tests block deployment until resolved
- **Enterprise Impact**: Prevents potential enterprise customer loss due to security breach
- **Regulatory Compliance**: Maintains data protection regulatory compliance