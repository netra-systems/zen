# Issue #1126 WebSocket Factory SSOT Violations - Comprehensive TEST PLAN

## 🎯 **TEST PLAN OVERVIEW**

**Issue:** [#1126 SSOT-WebSocket-Factory-Dual-Pattern-Fragmentation](https://github.com/netra-systems/netra-apex/issues/1126)
**Business Impact:** 🚨 **MISSION CRITICAL** - $500K+ ARR Golden Path blocked by WebSocket factory SSOT fragmentation
**Status:** Technical resolution complete, merge conflicts in PR #1135 require resolution

### **Test Objectives**
1. **DETECT VIOLATIONS:** Create tests that FAIL when SSOT violations exist
2. **VALIDATE RESOLUTION:** Ensure tests PASS after dual pattern elimination
3. **PREVENT REGRESSION:** Establish monitoring for future SSOT violations
4. **GOLDEN PATH PROTECTION:** Validate $500K+ ARR functionality remains intact

---

## 📋 **TEST STRATEGY BREAKDOWN**

### **Phase 1: Unit Tests - Import Validation & Deprecation Detection**
**Purpose:** Detect import path fragmentation and validate factory deprecation

#### **Test Suite 1.1: Import Failure Detection**
```python
# tests/unit/websocket_factory_ssot/test_deprecated_factory_import_validation.py
async def test_websocket_manager_factory_import_should_fail():
    """
    CRITICAL: This test MUST FAIL until Issue #1126 is resolved.

    Validates that deprecated WebSocketManagerFactory import fails,
    proving dual pattern has been eliminated.
    """
    with pytest.raises(ImportError) as exc_info:
        from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

    assert "No module named" in str(exc_info.value)
    # Test demonstrates SSOT violation is resolved

async def test_create_websocket_manager_function_deprecated():
    """
    CRITICAL: Validates deprecated factory function is no longer available.
    """
    with pytest.raises(ImportError):
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
```

#### **Test Suite 1.2: SSOT Import Path Validation**
```python
# tests/unit/websocket_factory_ssot/test_canonical_import_enforcement.py
async def test_canonical_websocket_manager_import_works():
    """
    CRITICAL: Validates canonical SSOT import path functions correctly.
    """
    # This import MUST work after resolution
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

    assert callable(get_websocket_manager)
    # Proves SSOT path is functional

async def test_websocket_manager_direct_instantiation():
    """
    Validates direct WebSocketManager instantiation (SSOT compliant).
    """
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManagerMode

    # Direct instantiation should work without factory
    manager = WebSocketManager(mode=WebSocketManagerMode.UNIFIED)
    assert manager is not None
```

### **Phase 2: Integration Tests - WebSocket Event Delivery Validation**
**Purpose:** Ensure SSOT consolidation doesn't break critical business functionality

#### **Test Suite 2.1: Golden Path Event Delivery**
```python
# tests/integration/websocket_factory_ssot/test_websocket_events_post_resolution.py
async def test_all_five_websocket_events_delivered_post_ssot():
    """
    MISSION CRITICAL: All 5 business-critical WebSocket events MUST be delivered.

    This test validates that SSOT consolidation doesn't break the core
    business value delivery mechanism.
    """
    required_events = [
        "agent_started",
        "agent_thinking",
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]

    # Execute agent with real WebSocket connection
    result = await execute_agent_with_websocket_monitoring(
        agent="triage_agent",
        message="SSOT validation test"
    )

    # Validate ALL events delivered
    for event_type in required_events:
        assert result.events.get(event_type, 0) > 0, (
            f"BUSINESS CRITICAL: WebSocket event '{event_type}' not delivered. "
            f"SSOT consolidation may have broken $500K+ ARR functionality."
        )

async def test_websocket_manager_user_isolation_post_ssot():
    """
    CRITICAL: Validates multi-user isolation still works after SSOT consolidation.
    """
    user1_context = create_test_user_context("user1")
    user2_context = create_test_user_context("user2")

    manager1 = await get_websocket_manager(user1_context)
    manager2 = await get_websocket_manager(user2_context)

    # Ensure separate instances (no singleton contamination)
    assert manager1 is not manager2
    assert manager1.user_context.user_id != manager2.user_context.user_id
```

#### **Test Suite 2.2: WebSocket Factory Pattern Compliance**
```python
# tests/integration/websocket_factory_ssot/test_factory_pattern_validation.py
async def test_websocket_manager_factory_instantiation_consistency():
    """
    Validates factory pattern creates consistent, isolated instances.
    """
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

    # Create multiple managers for same user
    user_context = create_test_user_context("consistency_test")

    manager1 = await get_websocket_manager(user_context)
    manager2 = await get_websocket_manager(user_context)

    # Should get same instance for same user (factory caching)
    assert manager1 is manager2
    assert manager1.user_context.user_id == user_context.user_id

async def test_websocket_manager_connection_state_isolation():
    """
    CRITICAL: Validates connection state isolation between users.
    """
    user1_manager = await get_websocket_manager(create_test_user_context("user1"))
    user2_manager = await get_websocket_manager(create_test_user_context("user2"))

    # Simulate connection for user1
    await user1_manager.connect("ws://test-connection")

    # User2 connection state should be independent
    assert not user2_manager.is_connected()
    assert user1_manager.is_connected()
```

### **Phase 3: E2E Staging Tests - Golden Path Validation**
**Purpose:** Validate complete user workflow with real staging environment

#### **Test Suite 3.1: Golden Path End-to-End Validation**
```python
# tests/e2e/staging/test_websocket_factory_golden_path_validation.py
@pytest.mark.e2e
@pytest.mark.staging
async def test_complete_user_chat_flow_post_ssot_resolution():
    """
    GOLDEN PATH: Complete user chat flow validation in staging environment.

    This test validates the complete $500K+ ARR user experience works
    correctly after WebSocket factory SSOT consolidation.
    """
    # Connect to staging environment
    staging_url = "wss://auth.staging.netrasystems.ai"

    # Create real user session
    user_token = await create_staging_user_session()

    async with StagingWebSocketClient(staging_url, user_token) as client:
        # Send chat message
        await client.send_json({
            "type": "message",
            "content": "Optimize my AWS costs",
            "thread_id": await client.create_thread()
        })

        # Collect all WebSocket events
        events = await client.collect_events(timeout=60)

        # Validate business-critical event sequence
        event_types = [e["type"] for e in events]
        assert "agent_started" in event_types
        assert "agent_completed" in event_types

        # Validate business value delivered
        final_response = events[-1]
        assert final_response["type"] == "agent_completed"
        assert "recommendations" in final_response.get("data", {})

@pytest.mark.e2e
@pytest.mark.staging
async def test_multi_user_concurrent_chat_isolation():
    """
    CRITICAL: Multi-user isolation in real staging environment.
    """
    staging_url = "wss://auth.staging.netrasystems.ai"

    # Create two concurrent user sessions
    user1_token = await create_staging_user_session("user1")
    user2_token = await create_staging_user_session("user2")

    async with StagingWebSocketClient(staging_url, user1_token) as client1, \
               StagingWebSocketClient(staging_url, user2_token) as client2:

        # Send simultaneous messages
        await asyncio.gather(
            client1.send_json({"type": "message", "content": "User 1 request"}),
            client2.send_json({"type": "message", "content": "User 2 request"})
        )

        # Collect responses for both users
        user1_events = await client1.collect_events(timeout=30)
        user2_events = await client2.collect_events(timeout=30)

        # Validate no cross-contamination
        assert len(user1_events) > 0
        assert len(user2_events) > 0

        # Ensure events are properly isolated (no shared thread_ids)
        user1_thread_ids = {e.get("thread_id") for e in user1_events if e.get("thread_id")}
        user2_thread_ids = {e.get("thread_id") for e in user2_events if e.get("thread_id")}

        assert len(user1_thread_ids.intersection(user2_thread_ids)) == 0
```

### **Phase 4: Regression Prevention Tests**
**Purpose:** Establish monitoring to prevent future SSOT violations

#### **Test Suite 4.1: SSOT Compliance Monitoring**
```python
# tests/regression/websocket_factory_ssot/test_ssot_violation_prevention.py
async def test_websocket_import_path_monitoring():
    """
    MONITORING: Detect if dual import patterns are reintroduced.
    """
    import inspect
    import pkgutil

    websocket_modules = []

    # Scan all websocket_core modules
    import netra_backend.app.websocket_core as websocket_package
    for _, module_name, _ in pkgutil.iter_modules(websocket_package.__path__):
        if "factory" in module_name.lower():
            websocket_modules.append(module_name)

    # Should only have canonical modules, no factory duplicates
    allowed_factory_modules = [
        "user_execution_context",  # Canonical factory location
    ]

    forbidden_modules = [m for m in websocket_modules if m not in allowed_factory_modules]

    assert len(forbidden_modules) == 0, (
        f"SSOT VIOLATION: Forbidden factory modules detected: {forbidden_modules}. "
        f"This indicates dual pattern fragmentation has been reintroduced."
    )

async def test_websocket_manager_class_uniqueness():
    """
    MONITORING: Ensure only one WebSocketManager implementation exists.
    """
    import sys
    import types

    websocket_manager_classes = []

    # Scan all loaded modules for WebSocketManager classes
    for module_name, module in sys.modules.items():
        if module_name.startswith("netra_backend.app.websocket"):
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    "websocket" in attr_name.lower() and
                    "manager" in attr_name.lower()):
                    websocket_manager_classes.append({
                        'class': attr,
                        'module': module_name,
                        'name': attr_name
                    })

    # Should have exactly one canonical WebSocketManager
    manager_classes = [c for c in websocket_manager_classes if c['name'] == 'WebSocketManager']

    assert len(manager_classes) == 1, (
        f"SSOT VIOLATION: Multiple WebSocketManager implementations detected: {manager_classes}. "
        f"This indicates SSOT consolidation has been compromised."
    )
```

---

## 🚀 **TEST EXECUTION STRATEGY**

### **Execution Order**
1. **Unit Tests First:** Validate import patterns and deprecation
2. **Integration Tests:** Ensure functionality remains intact
3. **E2E Staging Tests:** Validate complete user experience
4. **Regression Tests:** Establish ongoing monitoring

### **Expected Test Results**

#### **BEFORE Issue #1126 Resolution:**
- ❌ `test_websocket_manager_factory_import_should_fail()` - PASSES (factory still exists)
- ❌ `test_create_websocket_manager_function_deprecated()` - PASSES (function still exists)
- ✅ `test_all_five_websocket_events_delivered_post_ssot()` - PASSES (events work)
- ⚠️ `test_websocket_manager_user_isolation_post_ssot()` - MAY FAIL (dual patterns)

#### **AFTER Issue #1126 Resolution:**
- ✅ `test_websocket_manager_factory_import_should_fail()` - FAILS (factory removed)
- ✅ `test_create_websocket_manager_function_deprecated()` - FAILS (function removed)
- ✅ `test_all_five_websocket_events_delivered_post_ssot()` - PASSES (events work)
- ✅ `test_websocket_manager_user_isolation_post_ssot()` - PASSES (isolation secure)

### **Test Execution Commands**

```bash
# Unit Tests - Import Validation
python tests/unified_test_runner.py --category unit --pattern "*websocket_factory_ssot*"

# Integration Tests - Event Delivery
python tests/unified_test_runner.py --category integration --pattern "*websocket_factory_ssot*" --real-services

# E2E Staging Tests - Golden Path
python tests/unified_test_runner.py --category e2e --pattern "*websocket_factory_golden_path*" --env staging

# Mission Critical - Complete Validation
python tests/mission_critical/test_issue_1100_websocket_ssot_mission_critical.py

# Regression Prevention
python tests/unified_test_runner.py --category regression --pattern "*ssot_violation_prevention*"
```

---

## 📊 **SUCCESS CRITERIA**

### **Immediate Success Indicators**
- ✅ **Import Failures:** Deprecated factory imports fail with ImportError
- ✅ **Canonical Success:** SSOT import paths work correctly
- ✅ **Event Delivery:** All 5 WebSocket events delivered consistently
- ✅ **User Isolation:** Multi-user sessions remain properly isolated

### **Business Value Protection**
- ✅ **Golden Path Functional:** Complete user chat flow works in staging
- ✅ **Performance Maintained:** No degradation in WebSocket performance
- ✅ **Security Preserved:** User isolation and data protection intact
- ✅ **Monitoring Established:** Regression prevention tests active

### **Long-term Monitoring**
- ✅ **SSOT Compliance:** Ongoing validation of single source patterns
- ✅ **Import Path Monitoring:** Detection of dual pattern reintroduction
- ✅ **Business Continuity:** Continuous validation of $500K+ ARR functionality

---

## 🔧 **IMPLEMENTATION NOTES**

### **Test Framework Requirements**
- Use `test_framework/base_integration_test.py` for integration tests
- Use `test_framework/websocket_helpers.py` for WebSocket testing utilities
- Use real services (no mocks) for integration and E2E tests
- Follow `reports/testing/TEST_CREATION_GUIDE.md` best practices

### **Staging Environment Setup**
- WebSocket endpoint: `wss://auth.staging.netrasystems.ai`
- Use staging authentication tokens
- Validate against real staging infrastructure
- Monitor for WebSocket connection stability

### **Business Value Justification (BVJ)**
- **Segment:** ALL (Free → Enterprise) - Platform Infrastructure
- **Business Goal:** Eliminate SSOT violations blocking Golden Path reliability
- **Value Impact:** Ensure $500K+ ARR WebSocket infrastructure remains functional
- **Strategic Impact:** Prevent technical debt from compromising business value delivery

---

**CRITICAL REMINDER:** These tests MUST demonstrate the issue exists before resolution and PASS after resolution. The test plan serves as both validation and regression prevention for Issue #1126 WebSocket factory SSOT violations.