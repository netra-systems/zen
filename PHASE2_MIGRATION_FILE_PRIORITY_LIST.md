# Phase 2 Migration File Priority Classification

**Date:** 2025-09-16  
**Purpose:** Specific file-by-file migration priority for Golden Path Phase 2 factory migration  
**Total Estimated Files:** 155+ files requiring migration from `get_agent_instance_factory()` to `create_agent_instance_factory(user_context)`

## Phase 2A: Critical Production Files (Priority 1 - IMMEDIATE)

### 🔴 Core Infrastructure Files

**1. Agent Factory Definition**
- `/netra_backend/app/agents/supervisor/agent_instance_factory.py`
  - **Contains:** Deprecated function definition that needs to stay but be properly secured
  - **Risk:** HIGH - Central factory implementation
  - **Migration:** Update documentation and error messages, ensure proper security blocking

**2. Production Dependencies & Routes**
- `/netra_backend/app/dependencies.py`
- `/netra_backend/app/routes/websocket.py` 
- `/netra_backend/app/routes/demo_websocket.py`
- Any FastAPI route handlers using factory pattern

**3. Core Service Integration**
- Files in `/netra_backend/app/services/` that use factory
- WebSocket integration files
- Agent execution pipeline files

### 🔴 Agent Execution Pipeline

**4. Supervisor Agent Integration**
- `/netra_backend/app/agents/supervisor_agent_modern.py` (if uses pattern)
- `/netra_backend/app/agents/supervisor/execution_engine_factory.py` (if uses pattern)
- `/netra_backend/app/agents/supervisor/workflow_orchestrator.py` (if uses pattern)

## Phase 2B: Test Infrastructure (Priority 2 - HIGH)

### 🔵 Mission Critical Tests

**1. Golden Path Validation**
- `/tests/mission_critical/test_golden_path_phase2_user_isolation_violations.py`
- `/tests/mission_critical/test_websocket_mission_critical_fixed.py`
- `/tests/mission_critical/test_websocket_agent_events_suite.py` (if uses pattern)

### 🔵 Integration Tests (Est. ~40 files)

**2. Agent Execution Integration**
- `/tests/integration/test_agent_execution_flow_integration.py`
- `/tests/integration/test_agent_execution_business_value.py`
- `/tests/integration/test_agent_websocket_integration_comprehensive.py`
- `/tests/integration/test_multi_user_message_isolation.py`
- `/tests/integration/test_supervisor_agent_multi_user_isolation.py`
- `/tests/integration/test_supervisor_ssot_system_conflicts.py`

**3. Agent Factory Integration Tests**
- `/tests/integration/agents/test_agent_factory_user_isolation_integration.py`
- `/tests/integration/agents/test_agent_factory_user_isolation_compliance.py`
- `/tests/integration/agents/test_issue_1142_golden_path_startup_contamination.py`

**4. WebSocket Integration Tests**
- `/tests/integration/websocket/test_websocket_user_isolation_1116.py`
- `/tests/integration/agent_websocket_coordination/test_agent_factory_websocket_bridge_integration.py`

**5. Agent Golden Path Tests**
- `/tests/integration/agent_golden_path/test_multi_user_message_isolation_integration.py`
- `/tests/integration/agent_golden_path/test_multi_user_concurrent_message_processing.py`
- `/tests/integration/agent_golden_path/test_message_processing_pipeline.py`
- `/tests/integration/agent_golden_path/test_message_pipeline_integration.py`
- `/tests/integration/agent_golden_path/test_agent_websocket_events_comprehensive.py`
- `/tests/integration/agent_golden_path/test_websocket_event_sequence_integration.py`
- `/tests/integration/agent_golden_path/test_agent_response_quality_integration.py`
- `/tests/integration/agent_golden_path/test_golden_path_performance_integration.py`
- `/tests/integration/agent_golden_path/test_agent_message_pipeline_end_to_end.py`

**6. Agent Response Integration Tests**
- `/tests/integration/agent_responses/test_response_quality_integration.py`
- `/tests/integration/agent_responses/test_agent_state_management_integration.py`
- `/tests/integration/agent_responses/test_agent_execution_integration.py`
- `/tests/integration/agent_responses/test_websocket_events_integration.py`

**7. Additional Integration Tests**
- `/tests/integration/test_websocket_agent_message_flow.py`
- `/tests/integration/test_websocket_agent_communication_integration.py`
- `/tests/integration/test_agent_message_error_recovery.py`
- `/tests/integration/test_agent_golden_path_messages.py`
- `/tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py`
- `/tests/integration/supervisor/test_supervisor_websocket_integration.py`
- `/tests/integration/ssot_validation/test_factory_pattern_user_isolation.py`

### 🔵 Unit Tests (Est. ~30 files)

**8. Agent Factory Unit Tests**
- `/tests/unit/test_agent_instance_factory_singleton_vulnerability.py`
- `/tests/unit/test_golden_path_agent_registry_issues.py`
- `/tests/unit/test_agent_factory_phase2_compliance.py`

**9. Agent-Specific Unit Tests**
- `/tests/unit/agents/test_agent_instance_factory_user_isolation.py`
- `/tests/unit/agents/test_agent_instance_factory_ssot_violations.py`
- `/tests/unit/agents/test_agent_instance_factory_ssot_migration.py`
- `/tests/unit/agents/test_agent_instance_factory_singleton_violations_1116.py`
- `/tests/unit/agents/test_ssot_migration_validation_1142.py`
- `/tests/unit/agents/test_ssot_factory_basic_validation_1142.py`
- `/tests/unit/agents/test_singleton_to_factory_migration_validation.py`
- `/tests/unit/agents/test_singleton_pattern_regression_1142.py`
- `/tests/unit/agents/test_issue_1142_startup_singleton_contamination.py`

**10. Supervisor Unit Tests**
- `/tests/unit/agents/supervisor/test_factory_pattern_user_isolation.py`
- `/tests/unit/agents/supervisor/test_agent_instance_factory_comprehensive.py`
- `/tests/unit/agents/supervisor/phase_3_4_validation/test_supervisor_ssot_compliance_validation.py`
- `/tests/unit/supervisor/test_supervisor_orchestration_ssot_validation.py`

**11. Backend Unit Tests**
- `/netra_backend/tests/unit/agents/supervisor/test_factory_pattern_user_isolation.py`
- `/netra_backend/tests/unit/agents/supervisor/test_agent_instance_factory_comprehensive.py`
- `/netra_backend/tests/unit/agents/test_supervisor_agent_ssot_comprehensive_unit.py`
- `/netra_backend/tests/unit/agents/test_ssot_user_contamination_violations.py`
- `/netra_backend/tests/unit/agents/test_ssot_factory_singleton_violations.py`
- `/netra_backend/tests/unit/demo/test_demo_websocket_bridge_interface.py`

**12. Backend Integration Tests**
- `/netra_backend/tests/integration/test_agent_execution_pipeline_integration.py`
- `/netra_backend/tests/integration/test_agent_execution_tool_pipeline_integration.py`
- `/netra_backend/tests/integration/startup/test_services_phase_comprehensive.py`
- `/netra_backend/tests/integration/golden_path/test_agent_factory_real_database_integration.py`

### 🔵 E2E Tests (Est. ~10 files)

**13. End-to-End Tests**
- `/tests/e2e/test_agent_pipeline_e2e.py`
- `/tests/e2e/test_golden_path_multi_user_concurrent.py`
- `/tests/e2e/supervisor/test_supervisor_orchestration_complete_e2e.py`

**14. Security & Multi-User Tests**
- `/tests/security/test_multi_user_supervisor_orchestration.py`
- `/tests/integration/agent_factory/test_multi_user_chat_isolation_1116.py`

## Phase 2C: Examples and Utilities (Priority 3 - MEDIUM)

### 🟡 Example Files

**15. Code Examples**
- `/examples/agent_instance_factory_usage.py`
  - **Pattern:** Transform into educational example showing both deprecated and correct patterns
  - **Value:** Teaching tool for developers

### 🟡 Utility Scripts

**16. Development Scripts**
- `/scripts/load_test_isolation.py`
  - **Pattern:** Update to use proper user context for load testing
  - **Risk:** LOW - Only affects development/testing

### 🟡 Documentation & References

**17. Documentation Files**
- Any `.md` files with code examples showing deprecated patterns
- README files with outdated factory usage examples
- Development guide documentation

## Special Migration Considerations

### Files Requiring Special Handling

**1. Test Files That Validate Deprecated Behavior**
- Some test files specifically test that `get_agent_instance_factory()` returns singleton instances
- These need to be updated to test the new security error behavior instead
- Example: `/tests/unit/agents/supervisor/test_factory_pattern_user_isolation.py`

**2. Files with Multiple Factory Usages**
- Some files create multiple factory instances in different contexts
- Need to ensure each usage gets appropriate user context
- May require refactoring to pass user context through call chains

**3. Mock and Test Infrastructure**
- Test mocks may need updates to work with new factory patterns
- Test utilities may need user context creation helpers
- Fixture creation for common user context scenarios

### Migration Patterns by File Type

**1. Production Code Pattern:**
```python
# Extract user context from request/WebSocket
user_context = UserExecutionContext.from_request_supervisor(
    user_id=request.user_id,
    thread_id=websocket_thread_id,
    run_id=generate_unique_run_id()
)
factory = create_agent_instance_factory(user_context)
```

**2. Test Code Pattern:**
```python
# Create test-specific user context
test_user_context = UserExecutionContext.from_request_supervisor(
    user_id="test_user",
    thread_id="test_thread",
    run_id=f"test_run_{uuid.uuid4()}"
)
factory = create_agent_instance_factory(test_user_context)
```

**3. Multi-User Test Pattern:**
```python
# Create separate contexts for isolation testing
contexts = [
    UserExecutionContext.from_request_supervisor(
        user_id=f"user_{i}",
        thread_id=f"thread_{i}",
        run_id=f"run_{i}_{uuid.uuid4()}"
    ) for i in range(num_users)
]
factories = [create_agent_instance_factory(ctx) for ctx in contexts]
```

## Validation Checkpoints

### Per-File Validation
- [ ] File compiles without import errors
- [ ] All tests for that file pass
- [ ] No new deprecation warnings
- [ ] User context properly created and used

### Per-Phase Validation
- [ ] Phase 2A: Golden Path end-to-end test passes
- [ ] Phase 2B: Full test suite passes with no regressions
- [ ] Phase 2C: Examples demonstrate best practices

### Final Validation
- [ ] Zero files using `get_agent_instance_factory()`
- [ ] All mission critical tests pass
- [ ] Performance benchmarks maintained
- [ ] Enterprise compliance verified

## Implementation Priority Order

### Week 1: Phase 2A (Critical Production)
1. Day 1: `/netra_backend/app/agents/supervisor/agent_instance_factory.py`
2. Day 2: Core routes and dependencies
3. Day 3: Agent execution pipeline files

### Week 2: Phase 2B (Test Infrastructure)
1. Day 1: Mission critical tests
2. Day 2-3: Integration tests (agent execution and factory)
3. Day 4: Unit tests and WebSocket tests
4. Day 5: E2E tests and security tests

### Week 3: Phase 2C (Examples and Utilities)
1. Day 1: Example files and scripts
2. Day 2: Documentation updates
3. Day 3: Final validation and compliance verification

This prioritization ensures that business-critical functionality is protected first, followed by comprehensive test coverage validation, and finally examples and utilities that support development best practices.