# 🧪 COMPREHENSIVE TEST PLAN - Issue #1126 WebSocket Factory SSOT Violations

## 🎯 **TEST STRATEGY OVERVIEW**

Following reports/testing/TEST_CREATION_GUIDE.md and CLAUDE.md best practices, this comprehensive test plan will **validate the resolution of WebSocket factory dual pattern fragmentation** and **protect $500K+ ARR Golden Path functionality**.

### **Test Philosophy: Tests That FAIL Until Fixed**
✅ **Real Business Value Tests** - Validate actual user workflows
✅ **SSOT Violation Detection** - Tests FAIL when dual patterns exist
✅ **Golden Path Protection** - Ensure chat functionality remains intact
✅ **Regression Prevention** - Monitor for future violations

---

## 📋 **PHASE 1: Unit Tests - Import Validation**

### **Critical Import Failure Detection**
```python
# tests/unit/websocket_factory_ssot/test_deprecated_factory_import_validation.py

async def test_websocket_manager_factory_import_should_fail():
    """
    🚨 CRITICAL: This test MUST FAIL until Issue #1126 is resolved.

    Validates that deprecated WebSocketManagerFactory import fails,
    proving dual pattern has been eliminated.
    """
    with pytest.raises(ImportError) as exc_info:
        from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

    assert "No module named" in str(exc_info.value)
    # Proves SSOT violation is resolved

async def test_canonical_websocket_manager_import_works():
    """
    ✅ VALIDATION: Canonical SSOT import path functions correctly.
    """
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
    assert callable(get_websocket_manager)
```

**Expected Results:**
- **BEFORE Resolution:** Import tests PASS (factory still exists) ❌
- **AFTER Resolution:** Import tests FAIL (factory removed) ✅

---

## 📋 **PHASE 2: Integration Tests - Event Delivery Validation**

### **Golden Path Event Delivery Protection**
```python
# tests/integration/websocket_factory_ssot/test_websocket_events_post_resolution.py

async def test_all_five_websocket_events_delivered_post_ssot():
    """
    🚨 MISSION CRITICAL: All 5 business-critical WebSocket events MUST be delivered.

    Validates SSOT consolidation doesn't break core business value delivery.
    """
    required_events = [
        "agent_started", "agent_thinking", "tool_executing",
        "tool_completed", "agent_completed"
    ]

    result = await execute_agent_with_websocket_monitoring(
        agent="triage_agent",
        message="SSOT validation test"
    )

    for event_type in required_events:
        assert result.events.get(event_type, 0) > 0, (
            f"BUSINESS CRITICAL: WebSocket event '{event_type}' not delivered. "
            f"SSOT consolidation may have broken $500K+ ARR functionality."
        )

async def test_websocket_manager_user_isolation_post_ssot():
    """
    🔒 SECURITY: Multi-user isolation still works after SSOT consolidation.
    """
    user1_manager = await get_websocket_manager(create_test_user_context("user1"))
    user2_manager = await get_websocket_manager(create_test_user_context("user2"))

    # Ensure separate instances (no singleton contamination)
    assert user1_manager is not user2_manager
    assert user1_manager.user_context.user_id != user2_manager.user_context.user_id
```

---

## 📋 **PHASE 3: E2E Staging Tests - Golden Path Validation**

### **Complete User Workflow Validation**
```python
# tests/e2e/staging/test_websocket_factory_golden_path_validation.py

@pytest.mark.e2e
@pytest.mark.staging
async def test_complete_user_chat_flow_post_ssot_resolution():
    """
    🌟 GOLDEN PATH: Complete user chat flow in staging environment.

    Validates complete $500K+ ARR user experience works correctly
    after WebSocket factory SSOT consolidation.
    """
    staging_url = "wss://auth.staging.netrasystems.ai"
    user_token = await create_staging_user_session()

    async with StagingWebSocketClient(staging_url, user_token) as client:
        await client.send_json({
            "type": "message",
            "content": "Optimize my AWS costs",
            "thread_id": await client.create_thread()
        })

        events = await client.collect_events(timeout=60)

        # Validate business-critical event sequence
        event_types = [e["type"] for e in events]
        assert "agent_started" in event_types
        assert "agent_completed" in event_types

        # Validate business value delivered
        final_response = events[-1]
        assert final_response["type"] == "agent_completed"
        assert "recommendations" in final_response.get("data", {})
```

---

## 📋 **PHASE 4: Regression Prevention**

### **SSOT Compliance Monitoring**
```python
# tests/regression/websocket_factory_ssot/test_ssot_violation_prevention.py

async def test_websocket_import_path_monitoring():
    """
    🔍 MONITORING: Detect if dual import patterns are reintroduced.
    """
    import pkgutil
    import netra_backend.app.websocket_core as websocket_package

    websocket_modules = []
    for _, module_name, _ in pkgutil.iter_modules(websocket_package.__path__):
        if "factory" in module_name.lower():
            websocket_modules.append(module_name)

    # Should only have canonical modules, no factory duplicates
    allowed_factory_modules = ["user_execution_context"]  # Canonical location
    forbidden_modules = [m for m in websocket_modules if m not in allowed_factory_modules]

    assert len(forbidden_modules) == 0, (
        f"SSOT VIOLATION: Forbidden factory modules detected: {forbidden_modules}"
    )
```

---

## 🚀 **TEST EXECUTION STRATEGY**

### **Execution Commands**
```bash
# Unit Tests - Import Validation
python tests/unified_test_runner.py --category unit --pattern "*websocket_factory_ssot*"

# Integration Tests - Event Delivery (with real services)
python tests/unified_test_runner.py --category integration --pattern "*websocket_factory_ssot*" --real-services

# E2E Staging Tests - Golden Path
python tests/unified_test_runner.py --category e2e --pattern "*websocket_factory_golden_path*" --env staging

# Mission Critical Validation
python tests/mission_critical/test_issue_1100_websocket_ssot_mission_critical.py

# Regression Prevention
python tests/unified_test_runner.py --category regression --pattern "*ssot_violation_prevention*"
```

### **Expected Test Behavior**

#### **🔴 BEFORE Issue #1126 Resolution (Tests Demonstrate Problem):**
- ❌ `test_websocket_manager_factory_import_should_fail()` → **PASSES** (factory exists - problem!)
- ❌ `test_create_websocket_manager_function_deprecated()` → **PASSES** (function exists - problem!)
- ✅ `test_all_five_websocket_events_delivered_post_ssot()` → **PASSES** (events work)
- ⚠️ `test_websocket_manager_user_isolation_post_ssot()` → **MAY FAIL** (dual patterns cause issues)

#### **✅ AFTER Issue #1126 Resolution (Tests Validate Fix):**
- ✅ `test_websocket_manager_factory_import_should_fail()` → **FAILS** (factory removed - fixed!)
- ✅ `test_create_websocket_manager_function_deprecated()` → **FAILS** (function removed - fixed!)
- ✅ `test_all_five_websocket_events_delivered_post_ssot()` → **PASSES** (events still work)
- ✅ `test_websocket_manager_user_isolation_post_ssot()` → **PASSES** (isolation secure)

---

## 📊 **SUCCESS CRITERIA**

### **✅ Technical Validation**
- **Import Failures:** Deprecated factory imports fail with ImportError
- **Canonical Success:** SSOT import paths work correctly
- **Event Delivery:** All 5 WebSocket events delivered consistently
- **User Isolation:** Multi-user sessions remain properly isolated

### **💰 Business Value Protection**
- **Golden Path Functional:** Complete user chat flow works in staging
- **Performance Maintained:** No degradation in WebSocket performance
- **Security Preserved:** User isolation and data protection intact
- **$500K+ ARR Protected:** Core chat functionality remains reliable

### **🔄 Long-term Monitoring**
- **SSOT Compliance:** Ongoing validation of single source patterns
- **Import Path Monitoring:** Detection of dual pattern reintroduction
- **Business Continuity:** Continuous validation of revenue functionality

---

## 📝 **BUSINESS VALUE JUSTIFICATION (BVJ)**

- **Segment:** ALL (Free → Enterprise) - Platform Infrastructure
- **Business Goal:** Eliminate SSOT violations blocking Golden Path reliability
- **Value Impact:** Ensure $500K+ ARR WebSocket infrastructure remains functional
- **Strategic Impact:** Prevent technical debt from compromising business value delivery

---

## 🔗 **Related Documentation**

- **📋 Complete Test Plan:** [ISSUE_1126_WEBSOCKET_FACTORY_SSOT_TEST_PLAN.md](./ISSUE_1126_WEBSOCKET_FACTORY_SSOT_TEST_PLAN.md)
- **🧪 Test Creation Guide:** [reports/testing/TEST_CREATION_GUIDE.md](./reports/testing/TEST_CREATION_GUIDE.md)
- **🎯 CLAUDE.md:** Prime directives for development and testing

---

**🎯 CRITICAL REMINDER:** These tests serve as both **validation tools** and **regression prevention** for Issue #1126. They MUST demonstrate the problem exists before resolution and PASS after successful SSOT consolidation.