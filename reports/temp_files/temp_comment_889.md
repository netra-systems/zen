## 🧪 Issue #889 WebSocket Manager Duplication - Comprehensive Test Plan

**Agent Session:** `agent-session-2025-09-15-1505`
**Created:** 2025-09-15
**Priority:** P2 (Production Staging Impact)
**Business Impact:** Affects $500K+ ARR Golden Path chat functionality

---

## 📋 Executive Summary

Created comprehensive test plan to reproduce and validate WebSocket manager duplication violations. Analysis reveals **multi-layered architectural inconsistency** where `demo-user-001` gets multiple manager instances due to:

1. **Registry Key Inconsistency** - `_get_user_key()` generates different keys for same logical user
2. **Factory Pattern Bypass** - Multiple code paths avoid user-scoped registry
3. **Enum Instance Sharing** - WebSocketManagerMode shared between users (compliance violation)
4. **Fallback Manager Creation** - Emergency fallbacks bypass validation

**Security Risk:** User isolation failures violate HIPAA, SOC2, SEC compliance requirements.

---

## 🔬 Test Strategy Overview

### Test Categories (Per `TEST_CREATION_GUIDE.md`)

| Test Type | Purpose | Infrastructure | Mocks | Expected Result |
|-----------|---------|----------------|-------|-----------------|
| **Unit Tests** | Factory/registry logic | None | External only | ❌ **MUST FAIL** - Reproduce duplication |
| **Integration Tests** | Real service integration | Local services | External APIs only | ❌ **MUST FAIL** - Registry inconsistencies |
| **E2E Staging Tests** | Production scenarios | Full GCP staging | None | ❌ **MUST FAIL** - Cross-session contamination |

**Key Principle:** All tests **MUST FAIL INITIALLY** to reproduce exact GCP log violations, then PASS after architectural fix.

---

## 🎯 Detailed Test Cases

### 1. Unit Tests - `/tests/unit/test_issue_889_websocket_manager_duplication_unit.py`

#### **Core Registry Logic Violations**
```python
@pytest.mark.unit
async def test_demo_user_001_duplication_reproduction(self):
    """
    MUST FAIL INITIALLY: Reproduce exact duplication pattern for demo-user-001

    Root Cause: _get_user_key() non-deterministic fallbacks create different
    keys for same user, causing registry misses and manager duplication.
    """
    reset_manager_registry()

    # Create multiple contexts for demo-user-001 (simulating multiple requests)
    contexts = [create_test_user_context_with_id("demo-user-001") for _ in range(3)]

    managers = [get_websocket_manager(context) for context in contexts]

    # WILL FAIL: Should have only 1 manager for demo-user-001
    registry_status = await get_manager_registry_status()
    self.assertEqual(registry_status['total_registered_managers'], 1,
        f"Expected 1 manager for demo-user-001, found {registry_status['total_registered_managers']}. "
        f"This reproduces GCP log: 'Multiple manager instances for user demo-user-001'")

    # WILL FAIL: All instances should be identical objects
    manager_ids = [id(m) for m in managers]
    self.assertEqual(len(set(manager_ids)), 1,
        f"Expected identical manager instances, found {len(set(manager_ids))} unique objects.")
```

#### **User Isolation Security Tests**
```python
@pytest.mark.unit
async def test_cross_user_isolation_violation_detection(self):
    """
    MUST FAIL INITIALLY: Detect shared state between users (compliance violation)

    Security Risk: Shared enum instances cause state contamination between users
    """
    user_1_mgr = get_websocket_manager(create_test_user_context_with_id("user-001"))
    user_2_mgr = get_websocket_manager(create_test_user_context_with_id("user-002"))

    # Check for shared object references (CRITICAL security violation)
    shared_attributes = []
    for attr in ['mode', '_state', '_cache', 'user_context']:
        if hasattr(user_1_mgr, attr) and hasattr(user_2_mgr, attr):
            if getattr(user_1_mgr, attr) is getattr(user_2_mgr, attr):
                shared_attributes.append(attr)

    # WILL FAIL: No attributes should be shared between users
    self.assertEqual(len(shared_attributes), 0,
        f"CRITICAL ISOLATION VIOLATION: Shared attributes {shared_attributes} "
        f"violate HIPAA, SOC2, SEC compliance requirements.")
```

### 2. Integration Tests - `/tests/integration/test_issue_889_websocket_manager_duplication_integration.py`

#### **Real UserExecutionContext Factory Testing**
```python
@pytest.mark.integration
@pytest.mark.real_services
async def test_real_user_context_manager_duplication(self, real_services_fixture):
    """
    MUST FAIL INITIALLY: Test duplication with real UserExecutionContext factory

    Business Value: Validates factory patterns work with real dependencies
    """
    from netra_backend.app.core.user_context.factory import UserExecutionContextFactory

    # Create 3 real contexts for same logical user
    real_contexts = []
    for i in range(3):
        context = UserExecutionContextFactory.create_context(
            user_id="integration-test-user-001",
            request_id=f"req-{i}",
            thread_id="thread-integration-001"
        )
        real_contexts.append(context)

    managers = [get_websocket_manager(context) for context in real_contexts]
    manager_objects = set(id(m) for m in managers)

    # WILL FAIL: Should reuse same manager for same logical user
    self.assertEqual(len(manager_objects), 1,
        f"Expected single manager instance, found {len(manager_objects)} instances. "
        f"Registry key inconsistency with real UserExecutionContext.")
```

#### **Memory Leak Detection**
```python
@pytest.mark.integration
async def test_manager_registry_memory_leak_detection(self):
    """
    MUST FAIL INITIALLY: Detect memory leaks from duplicate managers

    Business Value: Prevents resource exhaustion in production
    """
    import psutil, os

    process = psutil.Process(os.getpid())
    baseline_memory = process.memory_info().rss
    baseline_registry = len(_USER_MANAGER_REGISTRY)

    # Create 100 managers for unique users
    for i in range(100):
        context = create_test_user_context_with_id(f"memory-test-user-{i}")
        get_websocket_manager(context)

    memory_growth_mb = (process.memory_info().rss - baseline_memory) / (1024 * 1024)
    registry_growth = len(_USER_MANAGER_REGISTRY) - baseline_registry

    # WILL FAIL: Registry should grow by exactly 100
    self.assertEqual(registry_growth, 100,
        f"Expected registry +100, actual +{registry_growth}. Indicates duplicate entries.")

    # Memory should be reasonable (<50MB for 100 managers)
    self.assertLess(memory_growth_mb, 50,
        f"Memory grew {memory_growth_mb:.2f}MB. May indicate duplication leaks.")
```

### 3. E2E Staging Tests - `/tests/e2e/staging/test_issue_889_websocket_manager_duplication_e2e_comprehensive.py`

#### **Golden Path Multi-User Validation**
```python
@pytest.mark.e2e
async def test_staging_golden_path_demo_user_001_isolation(self):
    """
    MUST FAIL INITIALLY: Validate demo-user-001 isolation in complete Golden Path

    Business Value: Protects $500K+ ARR Golden Path functionality
    Expected: GCP logs show "Multiple manager instances for user demo-user-001"
    """
    staging_url = "https://auth.staging.netrasystems.ai"
    violations_detected = []

    async def execute_demo_user_golden_path(session_id: str):
        """Execute complete Golden Path for demo-user-001"""
        ws_client = WebSocketTestClient(
            base_url="wss://staging.netrasystems.ai/ws",
            auth_url=staging_url
        )

        connection = await ws_client.connect_with_context({
            'user_id': 'demo-user-001',  # Exact user from GCP logs
            'session_id': session_id,
            'scenario': 'golden_path_validation'
        })

        # Send chat message (90% of business value)
        await connection.send(json.dumps({
            'type': 'agent_request',
            'agent': 'triage_agent',
            'message': f'Test optimization from session {session_id}',
            'user_id': 'demo-user-001'
        }))

        # Validate all 5 WebSocket events (mission critical)
        events = await wait_for_agent_completion(connection, timeout_seconds=45,
            expected_events=['agent_started', 'agent_thinking', 'tool_executing',
                           'tool_completed', 'agent_completed'])

        return {'session_id': session_id, 'events_received': events, 'connection': connection}

    # Run 5 concurrent Golden Path sessions for demo-user-001
    tasks = [asyncio.create_task(execute_demo_user_golden_path(f"demo-session-{i}"))
             for i in range(5)]
    sessions = await asyncio.gather(*tasks, return_exceptions=True)

    successful_sessions = [s for s in sessions if isinstance(s, dict) and 'events_received' in s]

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
        f"CRITICAL STAGING VIOLATIONS: Cross-session contamination for demo-user-001. "
        f"Reproduces GCP log pattern. Violations: {violations_detected}")

    # Validate Golden Path success rate
    success_rate = (len(successful_sessions) / len(tasks)) * 100
    self.assertGreaterEqual(success_rate, 80.0,
        f"Golden Path success rate: {success_rate:.1f}%. Low rate indicates duplication issues.")
```

---

## ⚙️ Test Execution Commands

### **Phase 1 - Reproduction (All MUST FAIL):**
```bash
# Unit tests - Fast feedback on core violations
python tests/unified_test_runner.py --category unit \
  --test-file tests/unit/test_issue_889_websocket_manager_duplication_unit.py

# Integration tests - Real services (no Docker)
python tests/unified_test_runner.py --category integration \
  --test-file tests/integration/test_issue_889_websocket_manager_duplication_integration.py \
  --real-services

# E2E staging tests - Production validation
python tests/unified_test_runner.py --category e2e \
  --test-file tests/e2e/staging/test_issue_889_websocket_manager_duplication_e2e_comprehensive.py
```

### **Phase 2 - Validation (All MUST PASS after fix):**
Same commands, but tests validate:
- ✅ Single manager instance per user guaranteed
- ✅ User isolation maintained across all scenarios
- ✅ Golden Path success rate ≥90% with no contamination

---

## 🎯 Success Criteria

### **Reproduction Phase (Before Fix):**
| Test Category | Expected Failure | Validation |
|---------------|------------------|-------------|
| Unit | ❌ Registry key inconsistency | Different keys for same user_id |
| Unit | ❌ Manager duplication | Multiple instances for demo-user-001 |
| Integration | ❌ Real context duplication | Registry inconsistency with UserExecutionContext |
| Integration | ❌ Memory leak detection | Registry growth anomalies |
| E2E | ❌ Cross-session contamination | Events shared between sessions |
| E2E | ❌ Golden Path degradation | Success rate <80% |

### **Validation Phase (After Fix):**
| Test Category | Expected Success | Validation |
|---------------|------------------|-------------|
| Unit | ✅ Consistent registry keys | Same key for same user_id |
| Unit | ✅ Single manager instance | One object per user |
| Integration | ✅ Proper isolation | No shared state between users |
| Integration | ✅ Memory efficiency | Linear registry growth |
| E2E | ✅ Event isolation | No cross-session contamination |
| E2E | ✅ Golden Path reliability | Success rate ≥90% |

---

## 💼 Business Value Protection

### **Critical Functionality:**
- 🎯 **90% Platform Value** - Chat functionality isolation
- 💰 **$500K+ ARR** - Golden Path user flow reliability
- 🔒 **Regulatory Compliance** - HIPAA, SOC2, SEC user isolation
- ⚡ **System Stability** - Memory management and resource efficiency

### **Risk Mitigation:**
- **Security** - Multi-user isolation violations eliminated
- **Performance** - Memory leaks from duplicate managers prevented
- **Reliability** - State contamination between users resolved
- **Compliance** - Data separation requirements enforced

---

## 📁 Implementation Structure

### **Test Files to Create:**
```
tests/
├── unit/test_issue_889_websocket_manager_duplication_unit.py
├── integration/test_issue_889_websocket_manager_duplication_integration.py
└── e2e/staging/test_issue_889_websocket_manager_duplication_e2e_comprehensive.py
```

### **Framework Requirements:**
- ✅ Inherit from `SSotAsyncTestCase` (mandatory)
- ✅ Use `IsolatedEnvironment` for configuration
- ✅ Real services only (no mocks for integration/E2E)
- ✅ Staging environment: `https://auth.staging.netrasystems.ai`

---

## 🔄 Next Steps

1. **Create Unit Tests** - Reproduce registry key inconsistency and duplication patterns
2. **Create Integration Tests** - Validate with real UserExecutionContext factory
3. **Create E2E Staging Tests** - Production scenario validation on GCP staging
4. **Execute Reproduction Phase** - Confirm all tests fail as expected
5. **Architectural Fix Implementation** - Address root cause inconsistencies
6. **Execute Validation Phase** - Confirm all tests pass after fix

**Priority:** P2 - Production staging environment impact requires immediate attention to protect Golden Path functionality and regulatory compliance.

---

*This comprehensive test plan reproduces exact GCP log violations and validates architectural fixes for WebSocket manager duplication affecting core business functionality.*