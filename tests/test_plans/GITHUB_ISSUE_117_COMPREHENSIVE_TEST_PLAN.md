# GitHub Issue #117 Remediation - Comprehensive Test Plan

**Issue**: 3 of 4 critical tests failing: WebSocket 1011 errors + agent execution timeouts  
**Created**: 2025-09-09  
**Business Impact**: $120K+ MRR - Core chat functionality broken  
**Priority**: P1 Critical - Deployment blocking  

## Context from Previous Analysis

### Root Causes Identified:
1. **WebSocket JSON Serialization**: SSOT violation with 6+ duplicate functions causing serialization failures
2. **Agent Execution Message Routing**: Missing `execute_agent` message type handling in message router
3. **WebSocket Bridge Integration**: AgentWebSocketBridge + ExecutionEngine incomplete connection causing timeouts

### Failing Test Status:
- ✅ **1/4 Tests Passing**: Basic connectivity working
- ❌ **3/4 Tests Failing**: WebSocket 1011 errors + agent execution timeouts  
- **Time to Fix**: Estimated 4-6 hours with proper test coverage

## Business Value Justification (BVJ)

- **Segment**: All (Free, Early, Mid, Enterprise) - Platform-wide issue
- **Business Goal**: Restore core chat functionality and eliminate deployment blockers
- **Value Impact**: Users cannot interact with agents effectively due to WebSocket failures
- **Strategic/Revenue Impact**: $120K+ MRR at risk; blocks all new deployments until resolved

## Test Plan Structure

Following TEST_CREATION_GUIDE.md patterns and CLAUDE.md SSOT requirements:

### Test Categories:
1. **Unit Tests** (No Docker) - Fast feedback on individual components
2. **Integration Tests** (Local services) - Component interaction validation  
3. **E2E Staging Tests** (Real GCP) - End-to-end validation in staging environment

### Test Strategy: Failing Tests First
- Create tests that **RELIABLY FAIL** to reproduce exact issues
- Implement fixes to make tests pass
- Validate fixes don't introduce regressions

## Priority Area 1: WebSocket JSON Serialization SSOT Violations

### Test Suite: `tests/unit/websocket/test_websocket_json_ssot_violations_reproduction.py`

**Purpose**: Reproduce and validate fixes for SSOT violations in WebSocket JSON handling

#### Test Cases:

```python
class TestWebSocketJSONSSOTViolations:
    """Unit tests to reproduce and fix WebSocket JSON SSOT violations."""
    
    def test_duplicate_serialization_functions_identified(self):
        """FAILING TEST: Should identify all 6+ duplicate JSON serialization functions."""
        # EXPECTED TO FAIL: Multiple functions doing the same serialization
        # Test scans codebase and identifies duplicate functions
        assert False  # Will fail until duplicates are consolidated
        
    def test_agent_state_serialization_consistency(self):
        """FAILING TEST: DeepAgentState serialization should be consistent across all usages."""
        # Test that DeepAgentState serializes identically everywhere
        # Currently fails due to different serialization approaches
        
    def test_websocket_message_serialization_ssot(self):
        """FAILING TEST: WebSocket message serialization should use single method."""
        # Test that all WebSocket messages use the same serialization approach
        # Currently fails due to scattered serialization logic
        
    def test_frontend_message_type_conversion_unified(self):
        """FAILING TEST: Frontend message type conversion should be unified."""
        # Test message type conversion uses single source of truth
        # Currently fails due to multiple conversion functions
```

#### Success Criteria:
- All 6+ duplicate functions identified and catalogued
- Single SSOT function for WebSocket JSON serialization identified
- DeepAgentState serialization standardized
- Frontend message type conversion unified

#### Expected Business Value:
- Eliminates WebSocket serialization inconsistencies
- Reduces technical debt by removing duplicate code
- Prevents future serialization-related failures

### Test Suite: `tests/integration/websocket/test_websocket_json_integration_fixes.py`

**Purpose**: Validate WebSocket JSON works with real database and Redis connections

#### Test Cases:

```python
class TestWebSocketJSONIntegrationFixes:
    """Integration tests for WebSocket JSON with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_json_with_real_database_session(self, real_services_fixture):
        """FAILING TEST: WebSocket JSON should work with real database sessions."""
        # Test WebSocket message processing with active database connections
        # EXPECTED TO FAIL: Current JSON serialization doesn't handle DB sessions properly
        
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_state_persistence_and_serialization(self, real_services_fixture):
        """FAILING TEST: Agent state should persist and serialize consistently."""
        # Test that agent state is saved to database and serialized for WebSocket
        # EXPECTED TO FAIL: Inconsistent serialization between DB and WebSocket
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_json_processing(self, real_services_fixture):
        """FAILING TEST: Multiple WebSocket connections should handle JSON consistently."""
        # Test concurrent WebSocket connections with JSON message processing
        # EXPECTED TO FAIL: Race conditions in JSON serialization
```

#### Success Criteria:
- WebSocket JSON works with database sessions without serialization errors
- Agent state persists and serializes consistently between database and WebSocket
- Concurrent WebSocket connections handle JSON without race conditions

### Test Suite: `tests/e2e/websocket/test_websocket_json_staging_validation.py`

**Purpose**: Validate WebSocket JSON works in real staging environment

#### Test Cases:

```python
class TestWebSocketJSONStagingValidation:
    """E2E validation of WebSocket JSON in staging environment."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_services
    async def test_websocket_json_staging_connectivity(self, staging_config):
        """FAILING TEST: WebSocket JSON should work in staging GCP environment."""
        # Test WebSocket connection and JSON message processing in staging
        # EXPECTED TO FAIL: Current 1011 errors due to serialization issues
        
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_agent_execution_json_serialization_staging(self, staging_config, real_llm):
        """FAILING TEST: Agent execution should serialize properly in staging."""
        # Test complete agent execution with JSON serialization in staging
        # EXPECTED TO FAIL: Agent execution fails due to serialization errors
```

#### Success Criteria:
- WebSocket connections work in staging without 1011 errors
- Agent execution completes with proper JSON serialization
- All 5 critical WebSocket events serialize correctly

## Priority Area 2: Agent Execution Message Routing

### Test Suite: `tests/unit/message_routing/test_execute_agent_message_type_reproduction.py`

**Purpose**: Reproduce and fix missing `execute_agent` message type handling

#### Test Cases:

```python
class TestExecuteAgentMessageTypeReproduction:
    """Unit tests to reproduce missing execute_agent message type handling."""
    
    def test_execute_agent_message_type_handler_missing(self):
        """FAILING TEST: Should identify missing execute_agent message type handler."""
        # Test that message router has handler for execute_agent message type
        # EXPECTED TO FAIL: Handler is missing, causing agent execution timeouts
        
    def test_message_router_handle_execute_agent(self):
        """FAILING TEST: Message router should handle execute_agent messages."""
        # Test message router can process execute_agent message type
        # EXPECTED TO FAIL: No handler exists for this message type
        
    def test_agent_execution_message_routing_complete(self):
        """FAILING TEST: Agent execution should route through message system properly."""
        # Test that agent execution request routes through message system
        # EXPECTED TO FAIL: Message routing incomplete for agent execution
```

#### Success Criteria:
- Missing `execute_agent` message type handler identified
- Message router updated to handle `execute_agent` messages
- Agent execution requests route properly through message system

### Test Suite: `tests/integration/message_routing/test_agent_execution_routing_integration.py`

**Purpose**: Validate agent execution routing with real services

#### Test Cases:

```python
class TestAgentExecutionRoutingIntegration:
    """Integration tests for agent execution message routing."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_message_routing_with_database(self, real_services_fixture):
        """FAILING TEST: Agent execution routing should work with real database."""
        # Test agent execution request routing with database persistence
        # EXPECTED TO FAIL: Message routing failures prevent database operations
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execute_agent_websocket_message_flow(self, real_services_fixture):
        """FAILING TEST: execute_agent message should flow through WebSocket system."""
        # Test complete message flow from WebSocket to agent execution
        # EXPECTED TO FAIL: Missing message routing prevents flow completion
```

#### Success Criteria:
- Agent execution messages route properly with database operations
- WebSocket message flow works end-to-end for agent execution
- Message persistence works correctly during agent execution

### Test Suite: `tests/e2e/message_routing/test_agent_execution_staging_e2e.py`

**Purpose**: Validate agent execution routing in staging environment

#### Test Cases:

```python
class TestAgentExecutionStagingE2E:
    """E2E validation of agent execution routing in staging."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_services
    async def test_complete_agent_execution_routing_staging(self, staging_config):
        """FAILING TEST: Complete agent execution should work in staging."""
        # Test full agent execution flow in staging environment
        # EXPECTED TO FAIL: Message routing failures prevent completion
        
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_agent_execution_with_real_llm_routing(self, staging_config, real_llm):
        """FAILING TEST: Agent execution with real LLM should route properly."""
        # Test agent execution with actual LLM calls in staging
        # EXPECTED TO FAIL: Message routing issues prevent LLM integration
```

#### Success Criteria:
- Complete agent execution works in staging environment
- Agent execution with real LLM calls routes properly
- No timeouts during agent execution in staging

## Priority Area 3: WebSocket Bridge Integration

### Test Suite: `tests/unit/websocket_bridge/test_agent_websocket_bridge_connection_reproduction.py`

**Purpose**: Reproduce and fix WebSocket bridge connection issues

#### Test Cases:

```python
class TestAgentWebSocketBridgeConnectionReproduction:
    """Unit tests to reproduce WebSocket bridge connection issues."""
    
    def test_agent_websocket_bridge_initialization_missing(self):
        """FAILING TEST: AgentWebSocketBridge should be properly initialized."""
        # Test that AgentWebSocketBridge is initialized in ExecutionEngine
        # EXPECTED TO FAIL: Bridge not properly connected to ExecutionEngine
        
    def test_websocket_bridge_event_delivery(self):
        """FAILING TEST: WebSocket bridge should deliver all 5 critical events."""
        # Test bridge delivers agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        # EXPECTED TO FAIL: Bridge not connected, events not delivered
        
    def test_execution_engine_websocket_integration(self):
        """FAILING TEST: ExecutionEngine should integrate with WebSocket bridge."""
        # Test ExecutionEngine has proper WebSocket bridge integration
        # EXPECTED TO FAIL: Integration incomplete or missing
```

#### Success Criteria:
- AgentWebSocketBridge properly initialized in ExecutionEngine
- All 5 critical WebSocket events delivered through bridge
- ExecutionEngine WebSocket integration complete

### Test Suite: `tests/integration/websocket_bridge/test_websocket_bridge_real_services_integration.py`

**Purpose**: Validate WebSocket bridge with real services

#### Test Cases:

```python
class TestWebSocketBridgeRealServicesIntegration:
    """Integration tests for WebSocket bridge with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_bridge_with_real_connections(self, real_services_fixture):
        """FAILING TEST: WebSocket bridge should work with real WebSocket connections."""
        # Test bridge delivers events through real WebSocket connections
        # EXPECTED TO FAIL: Bridge not properly connected to real WebSocket system
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_websocket_event_delivery(self, real_services_fixture):
        """FAILING TEST: Agent execution should deliver WebSocket events via bridge."""
        # Test complete agent execution delivers all WebSocket events
        # EXPECTED TO FAIL: Bridge not delivering events during execution
```

#### Success Criteria:
- WebSocket bridge works with real WebSocket connections
- Agent execution delivers all WebSocket events through bridge
- Real-time event delivery works without timeouts

### Test Suite: `tests/e2e/websocket_bridge/test_websocket_bridge_staging_e2e.py`

**Purpose**: Validate WebSocket bridge in staging environment

#### Test Cases:

```python
class TestWebSocketBridgeStagingE2E:
    """E2E validation of WebSocket bridge in staging."""
    
    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.real_services
    async def test_websocket_bridge_staging_event_delivery(self, staging_config):
        """FAILING TEST: WebSocket bridge should deliver events in staging."""
        # Test bridge delivers all 5 critical events in staging environment
        # EXPECTED TO FAIL: Bridge integration incomplete in staging
        
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_complete_agent_workflow_websocket_events_staging(self, staging_config, real_llm):
        """FAILING TEST: Complete agent workflow should deliver WebSocket events in staging."""
        # Test full agent workflow with WebSocket event delivery in staging
        # EXPECTED TO FAIL: WebSocket bridge not working properly in staging
```

#### Success Criteria:
- WebSocket bridge delivers events properly in staging
- Complete agent workflows deliver all WebSocket events
- No event delivery failures or timeouts in staging

## Test Execution Strategy

### Phase 1: Reproduction (Expected Failures)
```bash
# Run all failing tests to confirm issues exist
python tests/unified_test_runner.py --test-file tests/unit/websocket/test_websocket_json_ssot_violations_reproduction.py
python tests/unified_test_runner.py --test-file tests/unit/message_routing/test_execute_agent_message_type_reproduction.py
python tests/unified_test_runner.py --test-file tests/unit/websocket_bridge/test_agent_websocket_bridge_connection_reproduction.py
```

### Phase 2: Integration Validation (With Docker)
```bash
# Run integration tests with real services
python tests/unified_test_runner.py --real-services --test-file tests/integration/websocket/test_websocket_json_integration_fixes.py
python tests/unified_test_runner.py --real-services --test-file tests/integration/message_routing/test_agent_execution_routing_integration.py  
python tests/unified_test_runner.py --real-services --test-file tests/integration/websocket_bridge/test_websocket_bridge_real_services_integration.py
```

### Phase 3: Staging E2E Validation (GCP)
```bash
# Run E2E tests in staging environment
python tests/unified_test_runner.py --env staging --category e2e --test-file tests/e2e/websocket/test_websocket_json_staging_validation.py
python tests/unified_test_runner.py --env staging --category e2e --test-file tests/e2e/message_routing/test_agent_execution_staging_e2e.py
python tests/unified_test_runner.py --env staging --category e2e --test-file tests/e2e/websocket_bridge/test_websocket_bridge_staging_e2e.py
```

### Phase 4: Mission Critical Validation
```bash
# Run mission critical tests to ensure no regressions
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_websocket_json_requirements.py
```

## Test Success Criteria

### Unit Tests:
- **WebSocket JSON SSOT**: All duplicate functions identified and consolidated
- **Message Routing**: Missing `execute_agent` handler identified and implemented  
- **WebSocket Bridge**: Bridge initialization and connection validated

### Integration Tests:
- **Real Services**: All tests pass with Docker services running
- **Database Integration**: WebSocket JSON works with database sessions
- **Message Flow**: Complete message flow works end-to-end

### E2E Staging Tests:  
- **Staging Connectivity**: WebSocket connections work without 1011 errors
- **Agent Execution**: Complete agent execution works with proper event delivery
- **Performance**: All operations complete within acceptable timeouts

### Mission Critical Validation:
- **All 5 WebSocket Events**: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- **No Regressions**: Existing functionality continues to work
- **Performance**: Response times meet business requirements

## Implementation Timeline

### Hour 1-2: Test Creation
- Create all unit test files with failing tests
- Set up test fixtures and helpers
- Validate tests fail as expected (reproducing issues)

### Hour 3-4: Fix Implementation  
- Consolidate WebSocket JSON serialization functions (SSOT compliance)
- Implement missing `execute_agent` message type handler
- Connect AgentWebSocketBridge to ExecutionEngine properly

### Hour 5-6: Validation & Documentation
- Run integration tests with Docker services
- Execute E2E staging tests for final validation
- Update documentation and learnings

## Risk Mitigation

### Test Reliability:
- Use real services in integration/E2E tests (no mocks per CLAUDE.md)
- Include retry logic for network operations
- Validate test environment health before execution

### Regression Prevention:
- Run full mission critical test suite after fixes
- Validate existing functionality continues to work
- Monitor performance metrics during testing

### Rollback Plan:
- Keep current implementation as backup
- Test rollback procedures
- Document rollback triggers and processes

## Related Documentation

- [TEST_CREATION_GUIDE.md](/Users/anthony/Documents/GitHub/netra-apex/reports/testing/TEST_CREATION_GUIDE.md) - SSOT test patterns
- [TEST_ARCHITECTURE_VISUAL_OVERVIEW.md](/Users/anthony/Documents/GitHub/netra-apex/tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md) - Test infrastructure  
- [Mission Critical Test Suite](/Users/anthony/Documents/GitHub/netra-apex/tests/mission_critical/test_websocket_agent_events_suite.py) - Critical WebSocket validation
- [WebSocket 1011 Error Tests](/Users/anthony/Documents/GitHub/netra-apex/tests/e2e/websocket/test_websocket_1011_error_reproduction.py) - Existing error reproduction

## Final Validation Checklist

Before marking GitHub issue #117 as resolved:

- [ ] All unit tests pass (reproduce → fix cycle complete)  
- [ ] All integration tests pass with real Docker services
- [ ] All E2E staging tests pass without 1011 errors or timeouts
- [ ] Mission critical test suite passes (no regressions)
- [ ] Performance metrics meet business requirements
- [ ] Documentation updated with learnings and fixes implemented
- [ ] Rollback procedures tested and documented

---

**Remember**: These tests are designed to FAIL initially - they reproduce the exact issues identified in GitHub issue #117. The value comes from creating reliable failing tests that validate the fixes work correctly once implemented.