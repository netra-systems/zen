## 📋 TEST PLAN - Agent Golden Path Unit Test Coverage (Issue #1081)

**Agent Session:** `agent-session-2025-09-15-1140` | **Phase:** Infrastructure Repair + Coverage Expansion

### 🎯 **Executive Summary**

Based on Five Whys root cause analysis, implementing two-phase strategy to achieve **85% agent golden path test coverage** protecting **$500K+ ARR** chat functionality.

**Current State:** 69% unit test success rate (20/29 passing)
**Target State:** 85% comprehensive coverage with infrastructure stability
**Business Impact:** Comprehensive protection of chat functionality (90% of platform value)

---

### 📊 **Phase 1: Infrastructure Repair (Days 1-3)**

**Goal:** Fix 31% unit test failure rate → Target 70%+ success rate

#### **Critical Infrastructure Issues to Fix:**

**1. Constructor Parameter Mismatches (13+ tests affected)**
```python
# Current broken pattern
UserExecutionContext(user_id, session_id)  # Deprecated post-SSOT migration

# Fixed pattern
user_context = await ContextFactory.create_isolated_context(user_id=user_id, session_id=session_id)
```

**2. WebSocket Async/Await Violations (47 violations)**
```python
# Fix async patterns
websocket_manager = await get_websocket_manager()  # Not websocket_manager = get_websocket_manager()
```

**3. Auth Service Fallback Configuration**
- Mock auth service for unit tests when real service unavailable
- Implement graceful degradation patterns

**4. Import Path Deprecation Updates**
- Update all deprecated agent and WebSocket import paths
- Align with current SSOT import registry

#### **Test Files to Repair:**
- `test_agent_message_processing_unit.py` (8 failing tests)
- `test_websocket_agent_integration_unit.py` (6 failing tests)
- `test_agent_execution_core_unit.py` (3 failing tests)
- `test_user_isolation_patterns_unit.py` (3 failing tests)

---

### 🚀 **Phase 2: Coverage Expansion (Days 4-10)**

**Goal:** Achieve 85% comprehensive coverage target

#### **New Test Suites to Create:**

**1. AgentMessageHandler Comprehensive Unit Tests**
```python
# test_agent_message_handler_comprehensive_unit.py
- test_message_processing_edge_cases()
- test_user_context_isolation()
- test_websocket_event_delivery()
- test_error_handling_patterns()
```

**2. WebSocket Events Validation (All 5 Critical Events)**
```python
# test_websocket_events_comprehensive_unit.py
- test_agent_started_event()
- test_agent_thinking_event()
- test_tool_executing_event()
- test_tool_completed_event()
- test_agent_completed_event()
```

**3. User Isolation Pattern Testing**
```python
# test_user_isolation_comprehensive_unit.py
- test_concurrent_user_execution()
- test_session_data_separation()
- test_memory_isolation_patterns()
```

**4. Agent Execution Core Logic**
```python
# test_agent_execution_comprehensive_unit.py
- test_execution_engine_workflows()
- test_supervisor_agent_coordination()
- test_pipeline_execution_patterns()
```

---

### 🛡️ **Business Value Protection**

**$500K+ ARR Protection Areas:**
- ✅ **Chat Message Processing** (90% of platform value)
- ✅ **Real-time WebSocket Events** (user experience critical)
- ✅ **Multi-user Isolation** (enterprise compliance: HIPAA, SOC2, SEC)
- ✅ **Agent Execution Reliability** (core business logic)

**Success Metrics:**
- **Infrastructure Stability:** >90% unit test success rate
- **Coverage Target:** 85% comprehensive agent component coverage
- **Business Protection:** Zero regression risk for golden path workflows
- **Enterprise Compliance:** Multi-user isolation patterns validated

---

### 🔧 **Technical Approach**

**Test Framework Compliance:**
- **SSOT BaseTestCase:** All tests inherit from established patterns
- **UserExecutionContext:** Follow current architecture for user isolation
- **No Docker Dependencies:** Unit/integration tests only, staging GCP for E2E
- **Real Service Integration:** Use staging environment for integration validation

**File Organization:**
```
tests/unit/agent_golden_path/
├── infrastructure_repair/
│   ├── test_agent_message_processing_fixed.py
│   ├── test_websocket_integration_fixed.py
│   └── test_user_isolation_fixed.py
└── coverage_expansion/
    ├── test_agent_message_handler_comprehensive.py
    ├── test_websocket_events_comprehensive.py
    └── test_agent_execution_comprehensive.py
```

---

### ⚡ **Risk Mitigation**

**Infrastructure Dependencies:**
- **Auth Service:** Implement fallback mocking for unit tests
- **WebSocket Managers:** Use factory patterns with proper async handling
- **User Context:** Follow SSOT migration patterns consistently

**Coordination with Related Issues:**
- **Issue #870**: Agent integration test patterns alignment
- **Issue #1059**: WebSocket infrastructure coordination
- **Issue #1116**: SSOT factory pattern consistency

---

### 📅 **Timeline & Deliverables**

**Week 1 (Days 1-3): Infrastructure Repair**
- Fix constructor and async/await patterns
- Repair 29 existing unit tests → 70%+ success rate
- Establish stable test foundation

**Week 1-2 (Days 4-10): Coverage Expansion**
- Create 16 new comprehensive test files
- Achieve 85% golden path coverage target
- Validate business value protection

**Success Validation:**
- Mission critical tests pass: `python tests/mission_critical/test_websocket_agent_events_suite.py`
- Coverage metrics: `python scripts/test_coverage_analysis.py --agent-golden-path`
- Staging validation: E2E tests on staging GCP environment

This test plan directly addresses the Five Whys root causes while establishing sustainable infrastructure protecting $500K+ ARR chat functionality.