# Team C: QA Agent - ReportingSubAgent Resilience Testing Strategy

## COPY THIS ENTIRE PROMPT:

You are a QA Engineer designing comprehensive test strategy for the enhanced ReportingSubAgent resilience features.

CRITICAL: All tests must validate the EXISTING ReportingSubAgent class remains the SINGLE SOURCE OF TRUTH for reporting while gaining resilience capabilities.

## MANDATORY FIRST ACTIONS:

1. READ `reporting_crash_audit_and_plan.md` - Failure scenarios
2. READ `tests/mission_critical/test_websocket_agent_events_suite.py` - Critical tests
3. READ `netra_backend/app/agents/reporting_sub_agent.py` - Current implementation
4. READ `CLAUDE.md` Section 7.3 - Test requirements (REAL SERVICES, NO MOCKS)
5. READ `test_framework/unified_docker_manager.py` - Docker operations
6. ANALYZE existing reporting tests for gaps
7. VERIFY unified test infrastructure is available

## YOUR QA TASK:

### 1. Test Coverage Matrix

```python
# Location: tests/mission_critical/test_reporting_resilience.py

class TestReportingResilience:
    """Comprehensive resilience testing for ReportingSubAgent"""
    
    # Test Categories:
    # A. Crash Prevention (10 scenarios)
    # B. Progressive Degradation (5 levels)
    # C. Checkpoint Recovery (8 scenarios)
    # D. Data Helper Fallback (6 scenarios)
    # E. Performance Under Failure (5 benchmarks)
    # F. Concurrent Execution (10 users)
    # G. Legacy Compatibility (all existing tests pass)
```

### 2. Critical Test Scenarios

**A. Crash Prevention Tests**
```python
@pytest.mark.critical
async def test_missing_all_required_data():
    """Verify no crash when ALL required data is missing"""
    context = create_test_context(metadata={})  # No data
    agent = ReportingSubAgent(context)
    
    # MUST NOT raise exception
    result = await agent.execute(context, stream_updates=True)
    
    assert result['success'] == True  # Still returns success
    assert result['level'] == 'FALLBACK'
    assert 'report' in result  # Always has output
    assert result['recovery_performed'] == True

@pytest.mark.critical
async def test_partial_data_graceful_degradation():
    """Verify progressive degradation with partial data"""
    context = create_test_context(metadata={
        'triage_result': {...},
        'data_result': {...}
        # Missing: optimizations, action_plan
    })
    
    result = await agent.execute(context)
    assert result['level'] == 'BASIC'
    assert 'missing_data' in result
    assert result['missing_data'] == ['optimizations_result', 'action_plan_result']

@pytest.mark.critical  
async def test_serialization_error_recovery():
    """Verify recovery from Pydantic serialization errors"""
    context = create_test_context(metadata={
        'action_plan_result': ComplexPydanticModel()  # Will fail serialization
    })
    
    result = await agent.execute(context)
    assert result['success'] == True
    assert 'fallback_used' in result['metadata']
```

**B. Checkpoint Recovery Tests**
```python
@pytest.mark.critical
async def test_checkpoint_resume_after_crash():
    """Verify report generation resumes from checkpoint"""
    run_id = 'test_run_123'
    
    # Simulate partial completion
    await checkpoint_manager.save_section(run_id, 'summary', {...})
    await checkpoint_manager.save_section(run_id, 'data_analysis', {...})
    
    # Simulate crash and restart
    agent = ReportingSubAgent(create_context(run_id=run_id))
    result = await agent.execute(context)
    
    # Should resume, not restart
    assert result['checkpoints_loaded'] == 2
    assert 'summary' in result['report']
    assert 'data_analysis' in result['report']

@pytest.mark.critical
async def test_checkpoint_cleanup_after_success():
    """Verify checkpoints are cleaned up after successful completion"""
    result = await agent.execute(context)
    assert result['success'] == True
    
    # Checkpoints should be gone
    checkpoints = await checkpoint_manager.load_progress(context.run_id)
    assert len(checkpoints) == 0
```

**C. Data Helper Fallback Tests**
```python
@pytest.mark.critical
async def test_automatic_data_helper_trigger():
    """Verify data_helper is triggered on insufficient data"""
    context = create_test_context(metadata={'triage_result': {'data_sufficiency': 'insufficient'}})
    
    with patch('workflow_orchestrator.execute_data_helper_fallback') as mock_fallback:
        result = await agent.execute(context)
        
        # Verify fallback was triggered
        mock_fallback.assert_called_once()
        assert result['fallback_triggered'] == True
        assert result['data_request'] is not None

@pytest.mark.critical
async def test_data_helper_result_integration():
    """Verify data_helper results are integrated into report"""
    # First execution triggers data_helper
    result1 = await agent.execute(context_insufficient)
    assert result1['level'] == 'FALLBACK'
    
    # Add data_helper results to context
    context_with_data = add_data_helper_results(context_insufficient, result1['data_request'])
    
    # Second execution uses collected data
    result2 = await agent.execute(context_with_data)
    assert result2['level'] in ['BASIC', 'STANDARD', 'FULL']
```

**D. Performance Tests**
```python
@pytest.mark.performance
async def test_checkpoint_overhead():
    """Verify checkpoint operations add <100ms overhead"""
    start = time.time()
    result = await agent.execute(context, enable_checkpoints=True)
    with_checkpoints = time.time() - start
    
    start = time.time()
    result = await agent.execute(context, enable_checkpoints=False)
    without_checkpoints = time.time() - start
    
    overhead = with_checkpoints - without_checkpoints
    assert overhead < 0.1, f"Checkpoint overhead {overhead}s exceeds 100ms"

@pytest.mark.performance
async def test_recovery_time():
    """Verify recovery completes within 5 seconds"""
    # Simulate failure
    with simulate_failure('LLM_TIMEOUT'):
        start = time.time()
        result = await agent.execute(context)
        recovery_time = time.time() - start
        
        assert result['success'] == True
        assert recovery_time < 5.0
```

**E. Concurrent Execution Tests**
```python
@pytest.mark.concurrent
async def test_10_concurrent_reports():
    """Verify 10 concurrent reports with mixed failure scenarios"""
    contexts = [
        create_context(user_id=f'user_{i}', scenario=FAILURE_SCENARIOS[i % len(FAILURE_SCENARIOS)])
        for i in range(10)
    ]
    
    # Execute all concurrently
    results = await asyncio.gather(*[
        agent.execute(ctx) for ctx in contexts
    ])
    
    # All must complete
    assert all(r['success'] == True for r in results)
    assert all('report' in r for r in results)
    
    # Verify isolation
    assert len(set(r.get('user_id') for r in results)) == 10
```

### 3. Failure Injection Framework

```python
class FailureInjector:
    """Inject specific failures for testing"""
    
    FAILURE_TYPES = {
        'MISSING_DATA': lambda ctx: ctx.metadata.clear(),
        'LLM_TIMEOUT': lambda: raise_timeout(),
        'REDIS_ERROR': lambda: disconnect_redis(),
        'SERIALIZATION': lambda: corrupt_pydantic_model(),
        'WEBSOCKET_FAIL': lambda: close_websocket(),
    }
    
    @contextmanager
    def inject(self, failure_type: str):
        """Context manager for failure injection"""
```

### 4. Test Data Scenarios

```python
# Location: tests/fixtures/reporting_test_data.py

TEST_SCENARIOS = {
    'FULL_DATA': {
        'triage_result': complete_triage_result(),
        'data_result': complete_data_result(),
        'optimizations_result': complete_optimizations(),
        'action_plan_result': complete_action_plan()
    },
    'PARTIAL_DATA': {
        'triage_result': complete_triage_result(),
        'data_result': partial_data_result(),
        # Missing others
    },
    'MINIMAL_DATA': {
        'triage_result': minimal_triage_result()
    },
    'CORRUPT_DATA': {
        'triage_result': 'not_a_dict',  # Wrong type
        'data_result': None,  # Null value
        'optimizations_result': circular_reference(),  # Can't serialize
    },
    'NO_DATA': {}
}
```

### 5. WebSocket Event Validation

```python
@pytest.mark.critical
async def test_websocket_events_during_recovery():
    """Verify all WebSocket events are sent during recovery"""
    events_captured = []
    
    async with websocket_listener(capture_to=events_captured):
        # Trigger failure and recovery
        with simulate_failure('LLM_TIMEOUT'):
            result = await agent.execute(context, stream_updates=True)
    
    # Verify critical events
    assert has_event(events_captured, 'agent_started')
    assert has_event(events_captured, 'agent_thinking', content='Validating')
    assert has_event(events_captured, 'agent_thinking', content='Retrying')
    assert has_event(events_captured, 'tool_executing')
    assert has_event(events_captured, 'tool_completed')
    assert has_event(events_captured, 'agent_completed')
```

### 6. Regression Test Suite

```python
@pytest.mark.regression
class TestReportingBackwardCompatibility:
    """Ensure existing functionality is preserved"""
    
    async def test_all_existing_tests_pass(self):
        """Run all existing reporting tests"""
        # Import and run existing test suite
        from tests.integration.agents.test_reporting_agent import *
        
    async def test_existing_api_contract(self):
        """Verify API remains compatible"""
        # Old usage pattern must still work
        agent = ReportingSubAgent(old_style_context)
        result = await agent.execute(old_style_params)
        assert_old_format_compatible(result)
```

### 7. Integration Test Suite

```python
@pytest.mark.integration
async def test_end_to_end_with_failures():
    """Full workflow with reporting failures and recovery"""
    
    # Start with real services
    async with real_services():
        # Execute full workflow
        supervisor = SupervisorAgent()
        
        # Inject failure at reporting stage
        with inject_failure_at('reporting', 'MISSING_DATA'):
            result = await supervisor.execute(user_request)
        
        # Verify workflow adapted
        assert result['workflow_adapted'] == True
        assert result['data_helper_invoked'] == True
        assert result['final_report'] is not None
```

## DELIVERABLES:

1. **test_reporting_resilience.py** - Complete test suite
2. **test_fixtures.py** - Test data and scenarios
3. **failure_injection.py** - Failure injection framework
4. **test_report.md** - Coverage and results report

## VALIDATION CHECKLIST:

- [ ] All crash scenarios covered
- [ ] Progressive degradation tested
- [ ] Checkpoint system validated
- [ ] Data helper fallback verified
- [ ] Performance benchmarks met
- [ ] Concurrent execution tested
- [ ] WebSocket events validated
- [ ] Backward compatibility confirmed
- [ ] Real services used (NO MOCKS)
- [ ] 100% of existing tests still pass

## TEST EXECUTION:

```bash
# Run resilience tests (uses UnifiedDockerManager automatically)
python tests/unified_test_runner.py --category reporting_resilience --real-services

# Run with failure injection
python tests/mission_critical/test_reporting_resilience.py --inject-failures

# Performance benchmarks
python tests/performance/test_reporting_performance.py --real-llm

# Full regression suite
python tests/regression/test_reporting_compatibility.py --all

# Verify WebSocket events
python tests/mission_critical/test_websocket_agent_events_suite.py

# Docker operations (if manual control needed)
python scripts/docker_manual.py status
```

Remember: ALL tests must use REAL SERVICES. Mocks are FORBIDDEN. The enhanced ReportingSubAgent must remain the SINGLE SOURCE OF TRUTH while gaining resilience.