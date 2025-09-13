# Issue #620 SSOT ExecutionEngine Migration - Comprehensive Test Strategy

**Created:** 2025-09-12  
**Issue:** Issue #620 - Test strategy for SSOT ExecutionEngine migration to UserExecutionEngine  
**Business Impact:** $500K+ ARR protection during SSOT migration  
**Priority:** P0 - Mission Critical  

## Executive Summary

This document outlines a comprehensive test strategy for validating Issue #565 SSOT ExecutionEngine migration from multiple deprecated implementations to a single UserExecutionEngine SSOT. The tests are designed to:

1. **Reproduce the Issue:** Demonstrate current SSOT violations and namespace conflicts  
2. **Validate the Fix:** Ensure migration to UserExecutionEngine resolves issues  
3. **Golden Path Protection:** Guarantee core user flow (login → get AI responses) works during migration  
4. **WebSocket Events Validation:** Verify all 5 critical WebSocket events function correctly  

**Test Execution Strategy:** NON-DOCKER focused tests (unit, integration non-docker, E2E staging GCP remote)

## Test Categories and Execution Strategy

### Test Execution Hierarchy (NON-DOCKER FOCUSED)

```
Priority 1: Unit Tests (No Docker Required)
├── Namespace conflict reproduction 
├── Import resolution validation
├── Constructor compatibility tests
└── SSOT compliance verification

Priority 2: Integration Tests (Non-Docker)
├── Agent execution flow validation
├── WebSocket event delivery
├── User context isolation
└── Factory pattern compliance  

Priority 3: E2E Tests (Staging GCP)
├── Golden path user flow
├── Multi-user concurrency
├── WebSocket events end-to-end
└── Production-like validation
```

## 1. Issue Reproduction Tests (Must Fail Before Fix)

### 1.1 Namespace Conflict Reproduction Tests

**File:** `tests/issue_620/test_ssot_namespace_conflicts.py`
**Purpose:** Demonstrate multiple ExecutionEngine classes cause conflicts
**Expected:** FAIL before migration, PASS after migration

```python
def test_execution_engine_namespace_conflicts():
    """REPRODUCTION TEST: Multiple ExecutionEngine implementations cause namespace conflicts.
    
    This test MUST FAIL before migration to demonstrate the issue.
    This test MUST PASS after migration when only UserExecutionEngine exists.
    """
    
    # Test 1: Multiple import sources
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine as DeprecatedEngine
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    
    # EXPECTED FAILURE POINT: Different classes with same name
    assert DeprecatedEngine != UserExecutionEngine  # Should fail - same class after migration
    
    # Test 2: Constructor signature conflicts
    # Deprecated: ExecutionEngine(registry, websocket_bridge, user_context=None)
    # SSOT: UserExecutionEngine(context, agent_factory, websocket_emitter)
    
    deprecated_params = inspect.signature(DeprecatedEngine.__init__).parameters
    ssot_params = inspect.signature(UserExecutionEngine.__init__).parameters
    
    # EXPECTED FAILURE: Different constructor signatures
    assert deprecated_params != ssot_params  # Should fail after migration (same signature)

def test_import_resolution_consistency():
    """REPRODUCTION TEST: Same import paths resolve to different classes.
    
    This demonstrates the SSOT violation where identical import statements
    can resolve to different ExecutionEngine implementations.
    """
    
    # Get all files that import ExecutionEngine
    execution_engine_imports = find_execution_engine_imports()
    
    imported_classes = []
    for file_path in execution_engine_imports:
        # Import ExecutionEngine from each file's context
        imported_class = import_execution_engine_from_file(file_path)
        imported_classes.append((file_path, imported_class))
    
    # EXPECTED FAILURE: Different classes from same import
    unique_classes = set(cls for _, cls in imported_classes)
    assert len(unique_classes) == 1, f"SSOT VIOLATION: {len(unique_classes)} different ExecutionEngine classes found"
```

### 1.2 User Context Isolation Failure Tests

**File:** `tests/issue_620/test_user_context_contamination.py`
**Purpose:** Demonstrate user data contamination between sessions
**Expected:** FAIL before migration, PASS after migration

```python
async def test_user_context_contamination_reproduction():
    """REPRODUCTION TEST: Global state causes user data contamination.
    
    This test demonstrates the security vulnerability where user data
    leaks between sessions due to shared global state in deprecated ExecutionEngine.
    """
    
    # Create two different user contexts
    user1_context = UserExecutionContext(user_id="user1", thread_id="thread1", run_id="run1")
    user2_context = UserExecutionContext(user_id="user2", thread_id="thread2", run_id="run2")
    
    # Using deprecated ExecutionEngine (should cause contamination)
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    
    engine1 = ExecutionEngine(mock_registry, mock_websocket_bridge, user1_context)
    engine2 = ExecutionEngine(mock_registry, mock_websocket_bridge, user2_context)
    
    # Execute agents for both users simultaneously
    task1 = asyncio.create_task(execute_user1_agent(engine1, user1_context))
    task2 = asyncio.create_task(execute_user2_agent(engine2, user2_context))
    
    result1, result2 = await asyncio.gather(task1, task2)
    
    # EXPECTED FAILURE: User 1's data appears in User 2's results (contamination)
    user1_data_in_user2_result = check_for_user_data_contamination(result2, user1_context)
    assert not user1_data_in_user2_result, "CRITICAL SECURITY VIOLATION: User data contamination detected"
    
    # EXPECTED FAILURE: WebSocket events sent to wrong user
    websocket_event_contamination = check_websocket_event_contamination(user1_context, user2_context)
    assert not websocket_event_contamination, "CRITICAL: WebSocket events sent to wrong user"
```

### 1.3 Factory Pattern Violation Tests

**File:** `tests/issue_620/test_factory_pattern_violations.py`
**Purpose:** Demonstrate factory pattern SSOT violations
**Expected:** FAIL before migration, PASS after migration

```python
def test_multiple_execution_engine_factories():
    """REPRODUCTION TEST: Multiple factory patterns create different ExecutionEngine types.
    
    This demonstrates SSOT violations where different factory methods
    create incompatible ExecutionEngine instances.
    """
    
    # Test different factory patterns
    factory1_engine = create_execution_engine_factory_method1()
    factory2_engine = create_execution_engine_factory_method2()
    direct_engine = ExecutionEngine(registry, websocket_bridge)
    
    # EXPECTED FAILURE: Different types from different factory methods
    assert type(factory1_engine) == type(factory2_engine) == type(direct_engine), \
        "SSOT VIOLATION: Multiple ExecutionEngine types from different factories"
    
    # EXPECTED FAILURE: Different capabilities/methods
    factory1_methods = set(dir(factory1_engine))
    factory2_methods = set(dir(factory2_engine))
    direct_methods = set(dir(direct_engine))
    
    assert factory1_methods == factory2_methods == direct_methods, \
        "SSOT VIOLATION: Different ExecutionEngine capabilities"
```

## 2. Migration Validation Tests (Must Pass After Fix)

### 2.1 SSOT Compliance Validation Tests

**File:** `tests/issue_620/test_ssot_compliance_validation.py`
**Purpose:** Verify successful migration to UserExecutionEngine SSOT
**Expected:** FAIL before migration, PASS after migration

```python
def test_single_execution_engine_import_source():
    """VALIDATION TEST: All ExecutionEngine imports resolve to UserExecutionEngine.
    
    This test validates that the migration successfully converted all
    deprecated ExecutionEngine imports to UserExecutionEngine.
    """
    
    # Find all ExecutionEngine import statements
    execution_engine_imports = scan_for_execution_engine_imports()
    
    for file_path, import_statement in execution_engine_imports:
        # Validate import statement points to UserExecutionEngine
        assert "user_execution_engine" in import_statement or "UserExecutionEngine as ExecutionEngine" in import_statement, \
            f"MIGRATION INCOMPLETE: {file_path} still uses deprecated ExecutionEngine import"
    
    # Validate no remaining deprecated imports
    deprecated_imports = scan_for_deprecated_execution_engine_imports()
    assert len(deprecated_imports) == 0, f"MIGRATION INCOMPLETE: {len(deprecated_imports)} deprecated imports remain"

async def test_user_context_isolation_after_migration():
    """VALIDATION TEST: UserExecutionEngine provides complete user isolation.
    
    This test validates that after migration, user contexts are completely isolated
    with no data contamination between concurrent users.
    """
    
    # Create multiple user contexts
    user_contexts = [
        UserExecutionContext(user_id=f"user{i}", thread_id=f"thread{i}", run_id=f"run{i}")
        for i in range(5)
    ]
    
    # Create UserExecutionEngine instances for each user
    engines = []
    for context in user_contexts:
        # Post-migration: Import should resolve to UserExecutionEngine
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        engine = await ExecutionEngine.create_from_legacy(
            registry=mock_registry,
            websocket_bridge=mock_websocket_bridge,
            user_context=context
        )
        engines.append(engine)
    
    # Execute agents simultaneously for all users
    tasks = []
    for i, (engine, context) in enumerate(zip(engines, user_contexts)):
        task = asyncio.create_task(execute_isolated_agent(engine, context, f"test_data_user_{i}"))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # Validate complete isolation
    for i, result in enumerate(results):
        expected_user_data = f"test_data_user_{i}"
        assert expected_user_data in str(result), f"User {i} data missing from result"
        
        # Validate no other user's data is present
        for j in range(len(user_contexts)):
            if i != j:
                other_user_data = f"test_data_user_{j}"
                assert other_user_data not in str(result), \
                    f"ISOLATION VIOLATION: User {j} data found in User {i} result"
```

### 2.2 Constructor Compatibility Tests

**File:** `tests/issue_620/test_constructor_compatibility.py`
**Purpose:** Verify legacy constructor compatibility works
**Expected:** FAIL before migration, PASS after migration

```python
async def test_legacy_constructor_compatibility():
    """VALIDATION TEST: Legacy constructor calls work with UserExecutionEngine.
    
    This test validates that the migration maintains backward compatibility
    for existing ExecutionEngine constructor calls.
    """
    
    # Test legacy constructor pattern (should work after migration)
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
    
    # Legacy pattern: ExecutionEngine(registry, websocket_bridge, user_context=None)
    user_context = UserExecutionContext(user_id="test_user", thread_id="test_thread", run_id="test_run")
    
    # Should work via create_from_legacy compatibility bridge
    engine = await ExecutionEngine.create_from_legacy(
        registry=mock_registry,
        websocket_bridge=mock_websocket_bridge,
        user_context=user_context
    )
    
    assert engine is not None, "Legacy constructor compatibility failed"
    assert isinstance(engine, UserExecutionEngine), "Legacy constructor should return UserExecutionEngine"
    
    # Test legacy methods still work
    assert hasattr(engine, 'execute_agent'), "execute_agent method missing"
    assert hasattr(engine, 'get_execution_stats'), "get_execution_stats method missing"
    assert hasattr(engine, 'cleanup'), "cleanup method missing"
    
    # Test user context is properly set
    assert engine.get_user_context() == user_context, "User context not properly set in legacy compatibility"
```

## 3. Golden Path Protection Tests

### 3.1 Core User Flow Tests (NON-DOCKER)

**File:** `tests/issue_620/test_golden_path_protection.py`
**Purpose:** Ensure login → get AI responses flow works during migration
**Expected:** PASS throughout migration

```python
async def test_golden_path_login_to_ai_response():
    """GOLDEN PATH TEST: Complete user flow from login to AI response.
    
    This test validates that the core business value (90% of platform value)
    continues to work throughout the SSOT migration process.
    """
    
    # Step 1: User Authentication (simulated)
    user_context = create_authenticated_user_context("test_user_golden_path")
    
    # Step 2: Agent Execution Setup (post-migration pattern)
    try:
        # Try new UserExecutionEngine pattern first
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        engine = await ExecutionEngine.create_from_legacy(
            registry=get_real_agent_registry(),
            websocket_bridge=get_real_websocket_bridge(),
            user_context=user_context
        )
    except ImportError:
        # Fallback to deprecated pattern during migration
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        
        engine = ExecutionEngine(
            registry=get_real_agent_registry(),
            websocket_bridge=get_real_websocket_bridge(),
            user_context=user_context
        )
    
    # Step 3: Execute AI Agent (real agent, non-docker)
    agent_context = AgentExecutionContext(
        agent_name="triage_agent",
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        run_id=user_context.run_id,
        user_input="What is the weather like today?",
        metadata={"test_case": "golden_path_protection"}
    )
    
    # Step 4: Execute and validate response
    start_time = time.time()
    result = await engine.execute_agent(agent_context, user_context)
    execution_time = time.time() - start_time
    
    # Validate core business requirements
    assert result.success, f"GOLDEN PATH FAILURE: Agent execution failed: {result.error}"
    assert result.data is not None, "GOLDEN PATH FAILURE: No AI response data"
    assert execution_time < 30.0, f"GOLDEN PATH FAILURE: Response too slow: {execution_time}s"
    
    # Validate AI response substance (not just technical success)
    ai_response = result.data.get('response', '')
    assert len(ai_response) > 10, "GOLDEN PATH FAILURE: AI response too short/empty"
    assert "weather" in ai_response.lower(), "GOLDEN PATH FAILURE: AI response not relevant to query"
    
    # Step 5: Cleanup
    await engine.cleanup()
    
    logger.info(f"✅ GOLDEN PATH PROTECTED: User login → AI response in {execution_time:.2f}s")

async def test_golden_path_websocket_events():
    """GOLDEN PATH TEST: All 5 critical WebSocket events are delivered.
    
    This test ensures that the core chat experience (WebSocket events)
    continues to work during SSOT migration.
    """
    
    user_context = create_authenticated_user_context("test_user_websocket_events")
    
    # Setup WebSocket event capture
    websocket_events_captured = []
    
    class MockWebSocketBridge:
        async def notify_agent_started(self, run_id, agent_name, metadata):
            websocket_events_captured.append(("agent_started", agent_name))
            
        async def notify_agent_thinking(self, run_id, agent_name, reasoning, step_number=None):
            websocket_events_captured.append(("agent_thinking", agent_name))
            
        async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters):
            websocket_events_captured.append(("tool_executing", tool_name))
            
        async def notify_tool_completed(self, run_id, agent_name, tool_name, result):
            websocket_events_captured.append(("tool_completed", tool_name))
            
        async def notify_agent_completed(self, run_id, agent_name, result, execution_time_ms):
            websocket_events_captured.append(("agent_completed", agent_name))
    
    mock_bridge = MockWebSocketBridge()
    
    # Create execution engine with mock bridge
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
    
    engine = await ExecutionEngine.create_from_legacy(
        registry=get_real_agent_registry(),
        websocket_bridge=mock_bridge,
        user_context=user_context
    )
    
    # Execute agent that should trigger all WebSocket events
    agent_context = AgentExecutionContext(
        agent_name="supervisor_agent",  # Agent that uses tools
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        run_id=user_context.run_id,
        user_input="Analyze the current system status",
        metadata={"test_case": "websocket_events_validation"}
    )
    
    result = await engine.execute_agent(agent_context, user_context)
    
    # Validate all 5 critical WebSocket events were delivered
    event_types = [event[0] for event in websocket_events_captured]
    
    required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
    
    for required_event in required_events:
        assert required_event in event_types, \
            f"GOLDEN PATH FAILURE: Required WebSocket event '{required_event}' not delivered"
    
    # Validate event sequence
    assert event_types[0] == "agent_started", "GOLDEN PATH FAILURE: agent_started must be first event"
    assert event_types[-1] == "agent_completed", "GOLDEN PATH FAILURE: agent_completed must be last event"
    
    logger.info(f"✅ GOLDEN PATH WEBSOCKET EVENTS: All {len(required_events)} critical events delivered")
```

### 3.2 Multi-User Concurrency Protection Tests

**File:** `tests/issue_620/test_multi_user_concurrency_protection.py`
**Purpose:** Ensure concurrent users work during migration
**Expected:** PASS throughout migration

```python
async def test_concurrent_users_golden_path():
    """GOLDEN PATH TEST: Multiple users can use system simultaneously.
    
    This test ensures that the platform can support multiple concurrent users
    throughout the SSOT migration process.
    """
    
    num_concurrent_users = 5
    user_contexts = [
        create_authenticated_user_context(f"concurrent_user_{i}")
        for i in range(num_concurrent_users)
    ]
    
    # Create tasks for concurrent user sessions
    async def simulate_user_session(user_context, user_id):
        """Simulate complete user session."""
        
        # Import with migration compatibility
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        engine = await ExecutionEngine.create_from_legacy(
            registry=get_real_agent_registry(),
            websocket_bridge=get_real_websocket_bridge(),
            user_context=user_context
        )
        
        # Execute multiple agents for this user
        agents_to_test = ["triage_agent", "data_helper_agent"]
        user_results = []
        
        for agent_name in agents_to_test:
            agent_context = AgentExecutionContext(
                agent_name=agent_name,
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=f"{user_context.run_id}_{agent_name}",
                user_input=f"Test query for {agent_name} from user {user_id}",
                metadata={"user_session": user_id, "concurrent_test": True}
            )
            
            result = await engine.execute_agent(agent_context, user_context)
            user_results.append((agent_name, result))
        
        await engine.cleanup()
        return (user_id, user_results)
    
    # Execute all user sessions concurrently
    start_time = time.time()
    tasks = [
        asyncio.create_task(simulate_user_session(context, i))
        for i, context in enumerate(user_contexts)
    ]
    
    all_user_results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Validate all users succeeded
    for user_id, user_results in all_user_results:
        for agent_name, result in user_results:
            assert result.success, f"CONCURRENT USER FAILURE: User {user_id} agent {agent_name} failed"
            
            # Validate user data isolation
            user_specific_data = f"user {user_id}"
            assert user_specific_data in str(result.data), \
                f"ISOLATION FAILURE: User {user_id} data not found in result"
    
    # Validate no cross-user contamination
    for user_id, user_results in all_user_results:
        for agent_name, result in user_results:
            for other_user_id in range(num_concurrent_users):
                if other_user_id != user_id:
                    other_user_data = f"user {other_user_id}"
                    assert other_user_data not in str(result.data), \
                        f"CONTAMINATION FAILURE: User {other_user_id} data found in User {user_id} result"
    
    logger.info(f"✅ CONCURRENT USERS PROTECTED: {num_concurrent_users} users in {total_time:.2f}s")
```

## 4. WebSocket Events Validation Tests

### 4.1 WebSocket Event Integrity Tests

**File:** `tests/issue_620/test_websocket_event_integrity.py`
**Purpose:** Ensure WebSocket events work correctly during migration
**Expected:** PASS throughout migration

```python
async def test_websocket_events_during_migration():
    """WEBSOCKET TEST: All WebSocket events delivered correctly during migration.
    
    This test validates that WebSocket event delivery remains intact
    during the SSOT migration process.
    """
    
    # Test both pre and post migration patterns
    test_patterns = [
        {
            "name": "UserExecutionEngine Pattern",
            "import_path": "netra_backend.app.agents.supervisor.user_execution_engine",
            "class_name": "UserExecutionEngine",
            "use_legacy_compat": True
        }
    ]
    
    for pattern in test_patterns:
        logger.info(f"Testing WebSocket events with {pattern['name']}")
        
        user_context = create_authenticated_user_context(f"websocket_test_{pattern['name']}")
        
        # Create execution engine using pattern
        module = importlib.import_module(pattern["import_path"])
        ExecutionEngineClass = getattr(module, pattern["class_name"])
        
        if pattern.get("use_legacy_compat"):
            engine = await ExecutionEngineClass.create_from_legacy(
                registry=get_real_agent_registry(),
                websocket_bridge=create_websocket_event_monitor(),
                user_context=user_context
            )
        else:
            engine = ExecutionEngineClass(
                registry=get_real_agent_registry(),
                websocket_bridge=create_websocket_event_monitor(),
                user_context=user_context
            )
        
        # Execute agent and monitor events
        agent_context = AgentExecutionContext(
            agent_name="triage_agent",
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            user_input="Test WebSocket event delivery",
            metadata={"websocket_test": pattern["name"]}
        )
        
        with WebSocketEventMonitor() as monitor:
            result = await engine.execute_agent(agent_context, user_context)
            
            # Validate all required events
            events_received = monitor.get_events()
            required_events = ["agent_started", "agent_thinking", "agent_completed"]
            
            for required_event in required_events:
                matching_events = [e for e in events_received if e["type"] == required_event]
                assert len(matching_events) > 0, \
                    f"WEBSOCKET FAILURE: {required_event} not received with {pattern['name']}"
            
            # Validate event order
            event_types = [e["type"] for e in events_received]
            assert event_types[0] == "agent_started", "First event must be agent_started"
            assert event_types[-1] == "agent_completed", "Last event must be agent_completed"
        
        await engine.cleanup()
        logger.info(f"✅ WebSocket events validated for {pattern['name']}")

class WebSocketEventMonitor:
    """Monitor WebSocket events during testing."""
    
    def __init__(self):
        self.events = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def get_events(self):
        return self.events
        
    def on_event(self, event_type, data):
        self.events.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })
```

## 5. E2E Staging Tests (GCP Remote)

### 5.1 Production-Like Validation Tests

**File:** `tests/issue_620/test_e2e_staging_validation.py`
**Purpose:** Validate migration in production-like environment
**Expected:** PASS throughout migration

```python
@pytest.mark.e2e
@pytest.mark.staging
async def test_e2e_staging_execution_engine_migration():
    """E2E STAGING TEST: Full migration validation in production-like environment.
    
    This test validates the SSOT migration using real staging GCP environment
    without docker dependencies.
    """
    
    # Connect to staging GCP environment
    staging_config = get_staging_gcp_config()
    
    # Create real user context for staging
    real_user_context = await create_staging_user_context("e2e_migration_test_user")
    
    # Test execution engine in staging
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
    
    # Create engine with staging services
    engine = await ExecutionEngine.create_from_legacy(
        registry=get_staging_agent_registry(staging_config),
        websocket_bridge=get_staging_websocket_bridge(staging_config),
        user_context=real_user_context
    )
    
    # Execute real agent in staging environment
    agent_context = AgentExecutionContext(
        agent_name="supervisor_agent",
        user_id=real_user_context.user_id,
        thread_id=real_user_context.thread_id,
        run_id=real_user_context.run_id,
        user_input="Perform system health check in staging",
        metadata={"e2e_test": True, "environment": "staging"}
    )
    
    # Execute with staging services (no docker)
    start_time = time.time()
    result = await engine.execute_agent(agent_context, real_user_context)
    execution_time = time.time() - start_time
    
    # Validate staging execution
    assert result.success, f"E2E STAGING FAILURE: Agent execution failed: {result.error}"
    assert result.data is not None, "E2E STAGING FAILURE: No response data"
    assert execution_time < 60.0, f"E2E STAGING FAILURE: Response too slow: {execution_time}s"
    
    # Validate real AI response
    response_data = result.data.get('response', '')
    assert len(response_data) > 20, "E2E STAGING FAILURE: AI response too short"
    
    # Cleanup staging resources
    await engine.cleanup()
    await cleanup_staging_user_context(real_user_context)
    
    logger.info(f"✅ E2E STAGING VALIDATED: Migration successful in {execution_time:.2f}s")

@pytest.mark.e2e
@pytest.mark.staging
async def test_e2e_staging_websocket_events():
    """E2E STAGING TEST: WebSocket events in production-like environment.
    
    This test validates WebSocket event delivery in staging GCP environment.
    """
    
    staging_config = get_staging_gcp_config()
    real_user_context = await create_staging_user_context("e2e_websocket_test_user")
    
    # Setup real WebSocket connection to staging
    websocket_connection = await establish_staging_websocket_connection(
        user_id=real_user_context.user_id,
        config=staging_config
    )
    
    try:
        # Create engine with real staging WebSocket
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        engine = await ExecutionEngine.create_from_legacy(
            registry=get_staging_agent_registry(staging_config),
            websocket_bridge=get_staging_websocket_bridge(staging_config),
            user_context=real_user_context
        )
        
        # Monitor WebSocket events
        received_events = []
        
        def on_websocket_event(event_data):
            received_events.append(event_data)
            
        websocket_connection.on('agent_event', on_websocket_event)
        
        # Execute agent
        agent_context = AgentExecutionContext(
            agent_name="triage_agent",
            user_id=real_user_context.user_id,
            thread_id=real_user_context.thread_id,
            run_id=real_user_context.run_id,
            user_input="Test WebSocket events in staging",
            metadata={"e2e_websocket_test": True}
        )
        
        result = await engine.execute_agent(agent_context, real_user_context)
        
        # Wait for all WebSocket events
        await asyncio.sleep(2.0)
        
        # Validate WebSocket events received
        assert len(received_events) > 0, "E2E STAGING WEBSOCKET FAILURE: No events received"
        
        # Validate specific events
        event_types = [e.get('type', '') for e in received_events]
        required_events = ["agent_started", "agent_completed"]
        
        for required_event in required_events:
            assert required_event in event_types, \
                f"E2E STAGING WEBSOCKET FAILURE: {required_event} not received"
        
        # Cleanup
        await engine.cleanup()
        
    finally:
        await websocket_connection.disconnect()
        await cleanup_staging_user_context(real_user_context)
    
    logger.info(f"✅ E2E STAGING WEBSOCKET: {len(received_events)} events delivered")
```

## 6. Test Execution Schedule and Commands

### 6.1 Test Execution Order

```bash
# Phase 1: Reproduction Tests (MUST FAIL before migration)
python -m pytest tests/issue_620/test_ssot_namespace_conflicts.py -v
python -m pytest tests/issue_620/test_user_context_contamination.py -v  
python -m pytest tests/issue_620/test_factory_pattern_violations.py -v

# Phase 2: Golden Path Protection (MUST PASS throughout)
python -m pytest tests/issue_620/test_golden_path_protection.py -v
python -m pytest tests/issue_620/test_multi_user_concurrency_protection.py -v

# Phase 3: WebSocket Event Validation (MUST PASS throughout)
python -m pytest tests/issue_620/test_websocket_event_integrity.py -v

# Phase 4: Migration Validation (MUST PASS after migration)
python -m pytest tests/issue_620/test_ssot_compliance_validation.py -v
python -m pytest tests/issue_620/test_constructor_compatibility.py -v

# Phase 5: E2E Staging Validation (MUST PASS after migration)
python -m pytest tests/issue_620/test_e2e_staging_validation.py -m staging -v
```

### 6.2 Continuous Validation Commands

```bash
# Run all Issue #620 tests
python -m pytest tests/issue_620/ -v --tb=short

# Run with coverage
python -m pytest tests/issue_620/ -v --cov=netra_backend.app.agents.supervisor --cov-report=html

# Run only non-docker tests
python -m pytest tests/issue_620/ -v -m "not docker"

# Run staging E2E tests
python -m pytest tests/issue_620/ -v -m staging --no-cov
```

## 7. Success Criteria and Validation Gates

### 7.1 Pre-Migration Success Criteria (MUST FAIL)
- [ ] `test_execution_engine_namespace_conflicts()` - FAILS (demonstrates issue)
- [ ] `test_import_resolution_consistency()` - FAILS (shows SSOT violation)
- [ ] `test_user_context_contamination_reproduction()` - FAILS (shows security issue)
- [ ] `test_multiple_execution_engine_factories()` - FAILS (shows factory violations)

### 7.2 Post-Migration Success Criteria (MUST PASS)
- [ ] `test_single_execution_engine_import_source()` - PASSES (SSOT compliance)
- [ ] `test_user_context_isolation_after_migration()` - PASSES (security fix)
- [ ] `test_legacy_constructor_compatibility()` - PASSES (backward compatibility)
- [ ] All golden path tests continue to PASS throughout migration

### 7.3 Continuous Success Criteria (MUST ALWAYS PASS)
- [ ] `test_golden_path_login_to_ai_response()` - PASSES (core business value)
- [ ] `test_golden_path_websocket_events()` - PASSES (WebSocket events)
- [ ] `test_concurrent_users_golden_path()` - PASSES (multi-user support)
- [ ] `test_websocket_events_during_migration()` - PASSES (WebSocket integrity)
- [ ] E2E staging tests - PASSES (production readiness)

## 8. Test Infrastructure and Utilities

### 8.1 Test Utilities

**File:** `tests/issue_620/test_utilities.py`

```python
def find_execution_engine_imports():
    """Find all ExecutionEngine import statements in the codebase."""
    pass

def import_execution_engine_from_file(file_path):
    """Import ExecutionEngine from specific file context."""
    pass

def check_for_user_data_contamination(result, user_context):
    """Check if user data from other contexts appears in result."""
    pass

def check_websocket_event_contamination(user1_context, user2_context):
    """Check if WebSocket events are sent to wrong users."""
    pass

def create_authenticated_user_context(user_id):
    """Create UserExecutionContext for testing."""
    pass

def get_real_agent_registry():
    """Get real AgentRegistry for non-docker testing."""
    pass

def get_real_websocket_bridge():
    """Get real WebSocketBridge for non-docker testing."""
    pass

def create_websocket_event_monitor():
    """Create WebSocket event monitor for testing."""
    pass
```

## 9. Risk Mitigation and Rollback Testing

### 9.1 Rollback Validation Tests

**File:** `tests/issue_620/test_rollback_validation.py`

```python
async def test_rollback_scenario():
    """ROLLBACK TEST: Validate system can rollback if migration fails.
    
    This test validates that if the SSOT migration encounters issues,
    the system can be safely rolled back to the previous state.
    """
    pass

async def test_partial_migration_state():
    """ROLLBACK TEST: System works during partial migration.
    
    This test validates that the system continues to function
    during partial migration states.
    """
    pass
```

## 10. Business Impact Monitoring

### 10.1 Business Value Protection Tests

**File:** `tests/issue_620/test_business_value_protection.py`

```python
async def test_500k_arr_functionality_protection():
    """BUSINESS TEST: $500K+ ARR functionality preserved during migration.
    
    This test validates that all revenue-critical functionality
    continues to work throughout the SSOT migration.
    """
    pass

async def test_chat_functionality_90_percent_value():
    """BUSINESS TEST: Chat functionality (90% platform value) preserved.
    
    This test validates that the core chat functionality that provides
    90% of the platform's business value continues to work.
    """
    pass
```

---

**CRITICAL SUCCESS FACTORS:**
1. **Reproduction Tests FAIL before migration** - Proves the issue exists
2. **Validation Tests PASS after migration** - Proves the fix works  
3. **Golden Path Tests ALWAYS PASS** - Protects core business value
4. **WebSocket Tests ALWAYS PASS** - Preserves real-time experience
5. **E2E Staging Tests PASS** - Validates production readiness

**BUSINESS IMPACT:** These tests protect $500K+ ARR while ensuring zero business disruption during the critical SSOT migration process.