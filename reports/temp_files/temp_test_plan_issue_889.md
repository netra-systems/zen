# Issue #889 WebSocket Manager Duplication - Comprehensive Test Plan

**Agent Session:** agent-session-2025-09-15-1505
**Created:** 2025-09-15
**Priority:** P2 (Production Staging Impact)
**Business Impact:** Affects $500K+ ARR Golden Path chat functionality

## Executive Summary

Issue #889 represents a multi-layered architectural inconsistency where WebSocket manager instances are being duplicated for the same user (specifically `demo-user-001`), violating SSOT principles and creating security risks through shared state. This test plan creates comprehensive coverage to:

1. **Reproduce the duplication issue** (failing tests initially)
2. **Validate user isolation failures** (regulatory compliance risk)
3. **Test factory pattern bypass scenarios** (architectural violations)
4. **Ensure proper manager lifecycle** (prevent memory leaks)

## Root Cause Analysis Summary

From examining `/c/GitHub/netra-apex/netra_backend/app/websocket_core/websocket_manager.py`:

### Core Issues Identified:
1. **Registry Key Inconsistency**: `_get_user_key()` function has multiple fallback mechanisms that can generate different keys for the same logical user
2. **Factory Pattern Bypass**: Multiple code paths create managers without using the user-scoped registry
3. **Enum Instance Sharing**: WebSocketManagerMode enum instances shared between users (lines 380-400)
4. **Fallback Manager Creation**: Emergency fallback managers bypass normal registry validation
5. **User Context Validation**: Weak validation allows contaminated or null contexts

### Business Risk:
- **Security**: User isolation failures violate HIPAA, SOC2, SEC compliance
- **Performance**: Memory leaks from duplicate managers
- **Reliability**: State contamination between users affects chat functionality

---

## Test Strategy Overview

### Test Categories (Following TEST_CREATION_GUIDE.md):

1. **Unit Tests**: Pure logic validation (factory patterns, registry logic)
2. **Integration Tests**: Real service integration without Docker
3. **E2E Staging Tests**: Production scenario validation on GCP

### Test Execution Approach:
- **MUST FAIL INITIALLY**: All tests designed to reproduce existing violations
- **Real Services**: No mocks for integration/E2E tests
- **Staging Environment**: Use `https://auth.staging.netrasystems.ai`
- **SSOT Compliance**: All tests inherit from `SSotAsyncTestCase`

---

## Detailed Test Plan

### 1. Unit Tests - Factory Pattern and Registry Logic

**File:** `/c/GitHub/netra-apex/tests/unit/test_issue_889_websocket_manager_duplication_unit.py`

#### Test Cases:

##### 1.1 Registry Key Consistency Tests
```python
@pytest.mark.unit
async def test_user_key_generation_consistency(self):
    """
    MUST FAIL INITIALLY: Validate that same logical user generates consistent registry keys

    Root Cause: _get_user_key() has non-deterministic fallbacks that can create
    different keys for the same user, leading to registry misses and duplication.
    """
    # Test with same user_id but different context objects
    user_context_1 = create_test_user_context_with_id("demo-user-001")
    user_context_2 = create_test_user_context_with_id("demo-user-001")

    key_1 = _get_user_key(user_context_1)
    key_2 = _get_user_key(user_context_2)

    # WILL FAIL: Keys should be identical for same user_id
    self.assertEqual(key_1, key_2,
        f"Same user_id should generate identical registry keys. "
        f"Key 1: {key_1}, Key 2: {key_2}. "
        f"Non-deterministic key generation causes manager duplication.")

@pytest.mark.unit
async def test_null_context_key_stability(self):
    """
    MUST FAIL INITIALLY: Null contexts should generate stable keys

    Root Cause: Multiple null context calls may generate different keys
    """
    key_1 = _get_user_key(None)
    key_2 = _get_user_key(None)

    # WILL FAIL: Should be same key for null contexts
    self.assertEqual(key_1, key_2)
```

##### 1.2 Manager Registry Isolation Tests
```python
@pytest.mark.unit
async def test_demo_user_001_duplication_reproduction(self):
    """
    MUST FAIL INITIALLY: Reproduce exact duplication pattern for demo-user-001

    This test specifically targets the user mentioned in GCP logs.
    """
    reset_manager_registry()  # Start clean

    # Create multiple contexts for demo-user-001 (simulating multiple requests)
    contexts = [
        create_test_user_context_with_id("demo-user-001")
        for _ in range(3)
    ]

    managers = []
    for context in contexts:
        manager = get_websocket_manager(context)
        managers.append(manager)

    # Validate manager registry state
    registry_status = await get_manager_registry_status()
    registered_count = registry_status['total_registered_managers']

    # WILL FAIL: Should have only 1 manager for demo-user-001
    self.assertEqual(registered_count, 1,
        f"Expected 1 manager for demo-user-001, found {registered_count}. "
        f"This reproduces the GCP log violation: 'Multiple manager instances for user demo-user-001'")

    # WILL FAIL: All manager instances should be identical (same object)
    manager_ids = [id(m) for m in managers]
    unique_managers = len(set(manager_ids))
    self.assertEqual(unique_managers, 1,
        f"Expected all manager instances to be identical objects, found {unique_managers} unique instances. "
        f"Manager IDs: {manager_ids}")
```

##### 1.3 User Isolation Validation Tests
```python
@pytest.mark.unit
async def test_cross_user_isolation_violation_detection(self):
    """
    MUST FAIL INITIALLY: Detect shared state between different users

    Root Cause: Managers may share enum instances, causing state contamination
    """
    reset_manager_registry()

    # Create managers for different users
    user_1_context = create_test_user_context_with_id("user-001")
    user_2_context = create_test_user_context_with_id("user-002")

    manager_1 = get_websocket_manager(user_1_context)
    manager_2 = get_websocket_manager(user_2_context)

    # Check for shared object references (critical security violation)
    shared_attributes = []
    critical_attrs = ['mode', 'user_context', '_state', '_cache']

    for attr in critical_attrs:
        if hasattr(manager_1, attr) and hasattr(manager_2, attr):
            attr_1 = getattr(manager_1, attr)
            attr_2 = getattr(manager_2, attr)

            if attr_1 is attr_2 and attr_1 is not None:
                shared_attributes.append(attr)

    # WILL FAIL: No attributes should be shared between users
    self.assertEqual(len(shared_attributes), 0,
        f"CRITICAL ISOLATION VIOLATION: Attributes shared between users: {shared_attributes}. "
        f"This violates HIPAA, SOC2, SEC compliance requirements.")
```

### 2. Integration Tests - Real Service Integration (Non-Docker)

**File:** `/c/GitHub/netra-apex/tests/integration/test_issue_889_websocket_manager_duplication_integration.py`

#### Test Cases:

##### 2.1 Manager Lifecycle with Real UserExecutionContext
```python
@pytest.mark.integration
@pytest.mark.real_services
async def test_real_user_context_manager_duplication(self, real_services_fixture):
    """
    MUST FAIL INITIALLY: Test duplication with real UserExecutionContext factory

    Business Value: Validates factory patterns work correctly with real dependencies
    """
    from netra_backend.app.core.user_context.factory import UserExecutionContextFactory

    # Create real user contexts through factory
    real_contexts = []
    for i in range(3):
        context = UserExecutionContextFactory.create_context(
            user_id="integration-test-user-001",
            request_id=f"req-{i}",
            thread_id="thread-integration-001"
        )
        real_contexts.append(context)

    # Get managers using real contexts
    managers = []
    for context in real_contexts:
        manager = get_websocket_manager(context)
        managers.append(manager)

    # Validate single manager instance
    manager_objects = set(id(m) for m in managers)

    # WILL FAIL: Should reuse same manager for same logical user
    self.assertEqual(len(manager_objects), 1,
        f"Expected single manager instance for same user, found {len(manager_objects)} instances. "
        f"This indicates registry key inconsistency with real UserExecutionContext.")

@pytest.mark.integration
@pytest.mark.real_services
async def test_concurrent_user_session_isolation(self, real_services_fixture):
    """
    MUST FAIL INITIALLY: Test isolation with concurrent user sessions

    Business Value: Simulates production concurrent user patterns
    """
    import asyncio

    async def create_user_session(user_id: str):
        """Simulate user session creation"""
        context = UserExecutionContextFactory.create_context(
            user_id=user_id,
            request_id=f"concurrent-{user_id}-{time.time()}",
            thread_id=f"thread-{user_id}"
        )

        manager = get_websocket_manager(context)

        # Simulate WebSocket operations
        if hasattr(manager, 'emit'):
            await manager.emit('agent_started', {'user_id': user_id})

        return {
            'user_id': user_id,
            'manager': manager,
            'context': context
        }

    # Create concurrent sessions for multiple users
    users = ['concurrent-user-001', 'concurrent-user-002', 'demo-user-001']

    tasks = [create_user_session(user_id) for user_id in users]
    sessions = await asyncio.gather(*tasks)

    # Validate isolation between sessions
    isolation_violations = []

    for i, session_a in enumerate(sessions):
        for session_b in sessions[i+1:]:
            # Check for shared manager instances
            if session_a['manager'] is session_b['manager']:
                isolation_violations.append({
                    'user_a': session_a['user_id'],
                    'user_b': session_b['user_id'],
                    'violation': 'shared_manager_instance'
                })

    # WILL FAIL: No isolation violations should exist
    self.assertEqual(len(isolation_violations), 0,
        f"CONCURRENT USER ISOLATION VIOLATIONS: {isolation_violations}. "
        f"Shared manager instances between users violate security requirements.")
```

##### 2.2 Memory Leak and Resource Management Tests
```python
@pytest.mark.integration
async def test_manager_registry_memory_leak_detection(self):
    """
    MUST FAIL INITIALLY: Detect memory leaks from duplicate managers

    Business Value: Prevents resource exhaustion in production
    """
    import gc
    import psutil
    import os

    process = psutil.Process(os.getpid())
    baseline_memory = process.memory_info().rss
    baseline_registry_size = len(_USER_MANAGER_REGISTRY)

    # Create many manager instances for different users
    created_managers = []
    for i in range(100):
        context = create_test_user_context_with_id(f"memory-test-user-{i}")
        manager = get_websocket_manager(context)
        created_managers.append(manager)

    current_memory = process.memory_info().rss
    current_registry_size = len(_USER_MANAGER_REGISTRY)

    memory_growth = current_memory - baseline_memory
    registry_growth = current_registry_size - baseline_registry_size

    # WILL FAIL: Registry should grow by exactly 100 (one per unique user)
    self.assertEqual(registry_growth, 100,
        f"Expected registry to grow by 100 users, grew by {registry_growth}. "
        f"This indicates duplicate entries or registry leaks.")

    # Memory growth should be reasonable (less than 50MB for 100 managers)
    memory_growth_mb = memory_growth / (1024 * 1024)
    self.assertLess(memory_growth_mb, 50,
        f"Memory grew by {memory_growth_mb:.2f}MB for 100 managers. "
        f"Excessive growth may indicate memory leaks from duplication.")
```

### 3. E2E Staging Tests - Production Scenario Validation

**File:** `/c/GitHub/netra-apex/tests/e2e/staging/test_issue_889_websocket_manager_duplication_e2e_comprehensive.py`

#### Test Cases:

##### 3.1 Golden Path Multi-User Validation
```python
@pytest.mark.e2e
async def test_staging_golden_path_demo_user_001_isolation(self):
    """
    MUST FAIL INITIALLY: Validate demo-user-001 isolation in complete Golden Path

    Business Value: Protects $500K+ ARR Golden Path functionality
    Expected Pattern: GCP logs show "Multiple manager instances for user demo-user-001"
    """
    staging_url = "https://auth.staging.netrasystems.ai"
    violations_detected = []

    # Execute Golden Path for demo-user-001 multiple times concurrently
    golden_path_sessions = []

    async def execute_demo_user_golden_path(session_id: str):
        """Execute complete Golden Path for demo-user-001"""
        try:
            # Step 1: Authentication
            ws_client = WebSocketTestClient(
                base_url=f"wss://staging.netrasystems.ai/ws",
                auth_url=staging_url
            )

            connection_context = {
                'user_id': 'demo-user-001',  # Exact user from GCP logs
                'session_id': session_id,
                'scenario': 'golden_path_validation'
            }

            connection = await ws_client.connect_with_context(connection_context)

            # Step 2: Send chat message (90% of business value)
            chat_message = {
                'type': 'agent_request',
                'agent': 'triage_agent',
                'message': f'Test optimization from session {session_id}',
                'user_id': 'demo-user-001'
            }

            await connection.send(json.dumps(chat_message))

            # Step 3: Validate all 5 WebSocket events (mission critical)
            events = await wait_for_agent_completion(
                connection,
                timeout_seconds=45,
                expected_events=[
                    'agent_started',
                    'agent_thinking',
                    'tool_executing',
                    'tool_completed',
                    'agent_completed'
                ]
            )

            return {
                'session_id': session_id,
                'status': 'success',
                'events_received': events,
                'connection': connection
            }

        except Exception as e:
            return {
                'session_id': session_id,
                'status': 'failed',
                'error': str(e)
            }

    # Run 5 concurrent Golden Path sessions for demo-user-001
    session_tasks = []
    for i in range(5):
        task = asyncio.create_task(
            execute_demo_user_golden_path(f"demo-session-{i}")
        )
        session_tasks.append(task)

    sessions = await asyncio.gather(*session_tasks, return_exceptions=True)

    # Analyze sessions for violations
    successful_sessions = [s for s in sessions if isinstance(s, dict) and s.get('status') == 'success']
    failed_sessions = [s for s in sessions if isinstance(s, dict) and s.get('status') == 'failed']

    # Check for cross-session event contamination (indicates shared managers)
    for i, session_a in enumerate(successful_sessions):
        for session_b in successful_sessions[i+1:]:
            events_a = session_a.get('events_received', [])
            events_b = session_b.get('events_received', [])

            # Look for session ID contamination in events
            session_a_id = session_a['session_id']
            session_b_id = session_b['session_id']

            contaminated_a = [e for e in events_a if session_b_id in str(e)]
            contaminated_b = [e for e in events_b if session_a_id in str(e)]

            if contaminated_a or contaminated_b:
                violations_detected.append({
                    'violation_type': 'cross_session_contamination',
                    'session_a': session_a_id,
                    'session_b': session_b_id,
                    'contaminated_events': contaminated_a + contaminated_b
                })

    # WILL FAIL: No violations should exist after fix
    self.assertEqual(len(violations_detected), 0,
        f"CRITICAL STAGING VIOLATIONS: Cross-session contamination detected for demo-user-001. "
        f"This reproduces the GCP log pattern and violates user isolation. "
        f"Violations: {violations_detected}. "
        f"Successful sessions: {len(successful_sessions)}, Failed: {len(failed_sessions)}")

    # Validate Golden Path success rate
    total_sessions = len(session_tasks)
    success_rate = (len(successful_sessions) / total_sessions) * 100

    self.assertGreaterEqual(success_rate, 80.0,
        f"Golden Path success rate too low: {success_rate:.1f}% ({len(successful_sessions)}/{total_sessions}). "
        f"Low success rate may indicate WebSocket manager duplication affecting functionality.")
```

##### 3.2 Production Load Pattern Simulation
```python
@pytest.mark.e2e
async def test_production_load_manager_duplication_detection(self):
    """
    MUST FAIL INITIALLY: Simulate production load patterns to trigger duplication

    Business Value: Validates system behavior under realistic load
    """
    staging_url = "https://auth.staging.netrasystems.ai"

    # Simulate production user patterns
    production_users = [
        {'user_id': 'demo-user-001', 'user_type': 'demo'},  # Known problematic user
        {'user_id': 'enterprise-001', 'user_type': 'enterprise'},
        {'user_id': 'premium-002', 'user_type': 'premium'},
        {'user_id': 'free-003', 'user_type': 'free'}
    ]

    async def simulate_user_load(user_config: dict, requests_per_user: int = 10):
        """Simulate realistic user load pattern"""
        user_id = user_config['user_id']
        user_sessions = []

        for request_num in range(requests_per_user):
            try:
                ws_client = WebSocketTestClient(
                    base_url=f"wss://staging.netrasystems.ai/ws",
                    auth_url=staging_url
                )

                connection = await ws_client.connect_with_context({
                    'user_id': user_id,
                    'request_num': request_num,
                    'user_type': user_config['user_type']
                })

                # Send typical chat message
                await connection.send(json.dumps({
                    'type': 'chat_message',
                    'content': f'Request {request_num} from {user_id}',
                    'user_id': user_id
                }))

                # Brief processing
                await asyncio.sleep(0.1)

                user_sessions.append({
                    'user_id': user_id,
                    'request_num': request_num,
                    'connection': connection,
                    'status': 'success'
                })

            except Exception as e:
                user_sessions.append({
                    'user_id': user_id,
                    'request_num': request_num,
                    'status': 'failed',
                    'error': str(e)
                })

        return user_sessions

    # Execute load simulation for all users
    load_tasks = []
    for user_config in production_users:
        task = asyncio.create_task(simulate_user_load(user_config))
        load_tasks.append(task)

    all_sessions = await asyncio.gather(*load_tasks)

    # Flatten results
    total_sessions = []
    for user_sessions in all_sessions:
        total_sessions.extend(user_sessions)

    successful_sessions = [s for s in total_sessions if s.get('status') == 'success']
    failed_sessions = [s for s in total_sessions if s.get('status') == 'failed']

    # Analyze for duplication patterns
    user_session_counts = {}
    for session in successful_sessions:
        user_id = session['user_id']
        user_session_counts[user_id] = user_session_counts.get(user_id, 0) + 1

    # Check demo-user-001 specifically
    demo_user_sessions = user_session_counts.get('demo-user-001', 0)

    # WILL FAIL: demo-user-001 should have normal session count
    expected_demo_sessions = 10  # Same as other users
    self.assertEqual(demo_user_sessions, expected_demo_sessions,
        f"demo-user-001 had {demo_user_sessions} successful sessions, expected {expected_demo_sessions}. "
        f"Deviation may indicate manager duplication affecting connection reliability. "
        f"All user session counts: {user_session_counts}")

    # Overall success rate validation
    total_expected = len(production_users) * 10  # 10 requests per user
    success_rate = (len(successful_sessions) / total_expected) * 100

    self.assertGreaterEqual(success_rate, 85.0,
        f"Production load success rate: {success_rate:.1f}% ({len(successful_sessions)}/{total_expected}). "
        f"Low success rate may indicate systemic issues with WebSocket manager duplication.")
```

---

## Test Execution Strategy

### 1. Test Execution Order:
1. **Unit Tests First**: Fast feedback on core logic violations
2. **Integration Tests**: Validate with real services (non-Docker)
3. **E2E Staging Tests**: Production scenario validation

### 2. Test Commands:

```bash
# Unit tests - Fast feedback
python tests/unified_test_runner.py --category unit --test-file tests/unit/test_issue_889_websocket_manager_duplication_unit.py

# Integration tests - Real services (no Docker)
python tests/unified_test_runner.py --category integration --test-file tests/integration/test_issue_889_websocket_manager_duplication_integration.py --real-services

# E2E staging tests - Production validation
python tests/unified_test_runner.py --category e2e --test-file tests/e2e/staging/test_issue_889_websocket_manager_duplication_e2e_comprehensive.py
```

### 3. Success Criteria:

#### Phase 1 - Reproduction (All tests MUST FAIL):
- Unit tests detect registry key inconsistency
- Integration tests show manager duplication with real contexts
- E2E tests reproduce staging log violations

#### Phase 2 - Validation (All tests PASS after fix):
- Single manager instance per user guaranteed
- User isolation maintained across all scenarios
- Golden Path success rate ≥90% with no contamination

---

## Expected Test Results (Before Fix)

### Unit Tests:
- ❌ `test_user_key_generation_consistency`: Different keys for same user_id
- ❌ `test_demo_user_001_duplication_reproduction`: Multiple managers for demo-user-001
- ❌ `test_cross_user_isolation_violation_detection`: Shared enum instances

### Integration Tests:
- ❌ `test_real_user_context_manager_duplication`: Registry key inconsistency
- ❌ `test_concurrent_user_session_isolation`: Shared manager instances
- ❌ `test_manager_registry_memory_leak_detection`: Registry growth anomalies

### E2E Staging Tests:
- ❌ `test_staging_golden_path_demo_user_001_isolation`: Cross-session contamination
- ❌ `test_production_load_manager_duplication_detection`: Reliability impact

---

## Business Value Protection

### Critical Functionality Protected:
- **90% Platform Value**: Chat functionality isolation
- **$500K+ ARR**: Golden Path user flow reliability
- **Regulatory Compliance**: HIPAA, SOC2, SEC user isolation
- **System Stability**: Memory leak and resource management

### Risk Mitigation:
- **Security**: Multi-user isolation violations
- **Performance**: Memory leaks from duplicate managers
- **Reliability**: State contamination between users
- **Compliance**: Data separation requirements

---

## Implementation Notes

### Test Framework Requirements:
- Inherit from `SSotAsyncTestCase` (mandatory)
- Use `IsolatedEnvironment` for configuration
- Real services only (no mocks for integration/E2E)
- Staging environment: `https://auth.staging.netrasystems.ai`

### Test File Structure:
```
tests/
├── unit/test_issue_889_websocket_manager_duplication_unit.py
├── integration/test_issue_889_websocket_manager_duplication_integration.py
└── e2e/staging/test_issue_889_websocket_manager_duplication_e2e_comprehensive.py
```

### Dependencies:
- `test_framework.ssot.base_test_case.SSotAsyncTestCase`
- `test_framework.websocket_helpers.WebSocketTestClient`
- `netra_backend.app.websocket_core.websocket_manager.*`
- `shared.isolated_environment.IsolatedEnvironment`

This comprehensive test plan will reproduce the exact violations reported in Issue #889 and provide validation that fixes properly address the multi-layered architectural inconsistencies affecting WebSocket manager lifecycle and user isolation.