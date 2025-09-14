## TEST PLAN - Issue #845 SSOT AgentRegistry Duplication

### Test Objectives
1. **Demonstrate Import Conflicts:** Show that importing both registries causes namespace conflicts
2. **WebSocket Integration Failures:** Prove that different WebSocket patterns cause event delivery failures
3. **Agent Factory Inconsistencies:** Show that factory patterns differ between implementations
4. **Golden Path Validation:** Verify that consolidation fixes the 5 critical WebSocket events

### Test Suite Structure

#### Test 1: Import Conflict Detection
**File:** `tests/integration/test_issue_845_registry_duplication.py`
**Purpose:** Demonstrate that both registries can be imported but cause conflicts
- Import both AgentRegistry implementations
- Show that they have different interfaces and capabilities
- Validate that using wrong registry breaks WebSocket events

#### Test 2: WebSocket Event Integration Test
**File:** `tests/integration/test_issue_845_websocket_events.py`
**Purpose:** Show WebSocket event delivery differences between registries
- Test basic registry with WebSocket manager integration
- Test advanced registry with WebSocket bridge factory pattern
- Verify that only advanced registry delivers all 5 critical events

#### Test 3: Agent Factory Pattern Validation
**File:** `tests/integration/test_issue_845_factory_patterns.py`
**Purpose:** Demonstrate factory pattern differences
- Show basic registry uses simple instantiation
- Show advanced registry uses proper user isolation with factory patterns
- Validate multi-user context isolation

#### Test 4: Golden Path End-to-End Validation
**File:** `tests/e2e/test_issue_845_golden_path_validation.py`
**Purpose:** Prove that SSOT consolidation fixes Golden Path functionality
- Test user login → agent processing → AI response flow
- Validate all 5 WebSocket events are delivered in correct sequence
- Ensure no import resolution failures at runtime

### Success Criteria
1. **FAILING TESTS:** Initial tests should FAIL with basic registry showing the issue
2. **PASSING TESTS:** After SSOT consolidation, all tests should PASS with advanced registry
3. **WebSocket Events:** All 5 critical events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) delivered
4. **No Import Conflicts:** Single import path resolves to advanced registry consistently
5. **Golden Path Functional:** End-to-end user flow works without WebSocket failures