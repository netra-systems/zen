# Execution Pattern Test Strategy
**Test Strategy for DeepAgentState → UserExecutionContext Migration**

**Version**: 1.0  
**Created**: 2025-09-03  
**Purpose**: Ensure perfect user isolation and system reliability during execution pattern migration

---

## 1. Critical Test Categories

### User Isolation Tests
Validates zero data leakage between concurrent users and perfect request-scoped execution.

### WebSocket Event Tests  
Ensures all 5 critical events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) reach the correct user in real-time.

### Performance Tests
Validates system handles 10+ concurrent users without degradation and resource exhaustion protection.

### Security Tests
Confirms no cross-user data exposure, permission boundaries, and secure resource cleanup.

### Migration Tests
Verifies factory patterns completely replace singletons and legacy patterns are eliminated.

---

## 2. Top 10 Most Critical Test Cases

### 1. **Complete User Context Isolation**
**What it validates**: Multiple users executing agents simultaneously have zero state sharing  
**Pass criteria**: No shared variables, contexts, or memory between user executions  
```python
async def test_complete_user_isolation():
    # Execute same agent for 3 users concurrently
    contexts = [create_user_context(f"user_{i}") for i in range(3)]
    agents = [factory.create_agent(SearchAgent, ctx) for ctx in contexts]
    
    results = await asyncio.gather(*[
        agent.execute(f"search user {i} specific query") 
        for i, agent in enumerate(agents)
    ])
    
    # Verify no cross-contamination
    assert all(f"user {i}" in result for i, result in enumerate(results))
```

### 2. **WebSocket Event Delivery Accuracy** 
**What it validates**: WebSocket events reach ONLY the intended user  
**Pass criteria**: Event routing is 100% accurate across concurrent users  
```python
async def test_websocket_isolation():
    user1_events = []
    user2_events = []
    
    # Create isolated emitters for each user
    emitter1 = factory.create_websocket_emitter("user1")
    emitter2 = factory.create_websocket_emitter("user2")
    
    # Execute agents and capture events
    await asyncio.gather(
        execute_with_event_capture(agent1, user1_events),
        execute_with_event_capture(agent2, user2_events)
    )
    
    # Verify event isolation
    assert all("user1" in event.get("user_id") for event in user1_events)
    assert all("user2" in event.get("user_id") for event in user2_events)
```

### 3. **Factory Pattern Singleton Elimination**
**What it validates**: No singleton patterns remain in execution path  
**Pass criteria**: All instances are request-scoped, zero global state  
```python
def test_no_singleton_instances():
    # Create multiple execution contexts
    ctx1 = create_user_context("user1") 
    ctx2 = create_user_context("user2")
    
    # Create agents
    agent1 = factory.create_agent(SupervisorAgent, ctx1)
    agent2 = factory.create_agent(SupervisorAgent, ctx2)
    
    # Verify different instances
    assert agent1 is not agent2
    assert agent1.tool_dispatcher is not agent2.tool_dispatcher
    assert agent1.websocket_emitter is not agent2.websocket_emitter
```

### 4. **Resource Cleanup Validation**
**What it validates**: All per-request resources are properly released  
**Pass criteria**: Memory usage returns to baseline after request completion  
```python
async def test_resource_cleanup():
    baseline_memory = get_memory_usage()
    
    # Execute 10 agent requests
    for i in range(10):
        context = create_user_context(f"user_{i}")
        agent = factory.create_agent(TestAgent, context)
        await agent.execute("test task")
        # Explicit cleanup
        await cleanup_context(context)
    
    # Verify memory returned to baseline
    final_memory = get_memory_usage()
    assert final_memory <= baseline_memory + MEMORY_TOLERANCE
```

### 5. **Concurrent User Performance**
**What it validates**: System handles 10+ users without performance degradation  
**Pass criteria**: Response time < 5s for each user, no timeouts  
```python
async def test_concurrent_performance():
    num_users = 12
    tasks = []
    
    for i in range(num_users):
        context = create_user_context(f"user_{i}")
        agent = factory.create_agent(SupervisorAgent, context)
        task = measure_execution_time(agent.execute("complex task"))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # Verify all completed within time limit
    assert all(execution_time < 5.0 for execution_time in results)
```

### 6. **Critical WebSocket Event Sequence**
**What it validates**: All 5 critical events are sent in correct order  
**Pass criteria**: Events appear: started → thinking → tool_executing → tool_completed → completed  
```python
async def test_websocket_event_sequence():
    events = []
    context = create_user_context("user1")
    
    # Mock WebSocket to capture events
    mock_emitter = MockWebSocketEmitter(events)
    context.websocket_emitter = mock_emitter
    
    agent = factory.create_agent(SupervisorAgent, context)
    await agent.execute("task requiring tools")
    
    # Verify critical event sequence
    event_types = [e["type"] for e in events]
    expected = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
    assert event_types == expected
```

### 7. **Tool Dispatcher Isolation**
**What it validates**: Tool execution is completely isolated per user  
**Pass criteria**: Tool executions don't interfere across users  
```python
async def test_tool_dispatcher_isolation():
    # Create contexts for two users
    ctx1 = create_user_context("user1")
    ctx2 = create_user_context("user2")
    
    # Create isolated tool dispatchers
    dispatcher1 = factory.create_tool_dispatcher(ctx1)
    dispatcher2 = factory.create_tool_dispatcher(ctx2)
    
    # Execute same tool concurrently
    result1, result2 = await asyncio.gather(
        dispatcher1.execute_tool("search", {"query": "python"}),
        dispatcher2.execute_tool("search", {"query": "java"})
    )
    
    # Verify isolated results
    assert "python" in str(result1).lower()
    assert "java" in str(result2).lower()
```

### 8. **Database Session Isolation**
**What it validates**: Database sessions are isolated per request  
**Pass criteria**: No shared database state between user contexts  
```python
async def test_database_isolation():
    # Create two users with different data
    ctx1 = create_user_context("user1")
    ctx2 = create_user_context("user2")
    
    # Create test data for each user
    await create_user_data(ctx1, {"key": "value1"})
    await create_user_data(ctx2, {"key": "value2"})
    
    # Query data through isolated sessions
    data1 = await get_user_data(ctx1, "key")
    data2 = await get_user_data(ctx2, "key")
    
    # Verify isolation
    assert data1 == "value1"
    assert data2 == "value2"
```

### 9. **Error Handling Isolation**
**What it validates**: Errors in one user's execution don't affect others  
**Pass criteria**: One user's errors don't crash or impact other users  
```python
async def test_error_isolation():
    # Create contexts
    ctx1 = create_user_context("user1")  # Will succeed
    ctx2 = create_user_context("user2")  # Will fail
    ctx3 = create_user_context("user3")  # Will succeed
    
    # Execute tasks - one will fail
    results = await asyncio.gather(
        safe_execute(factory.create_agent(WorkingAgent, ctx1), "good task"),
        safe_execute(factory.create_agent(FailingAgent, ctx2), "bad task"),
        safe_execute(factory.create_agent(WorkingAgent, ctx3), "good task"),
        return_exceptions=True
    )
    
    # Verify only one failed, others succeeded
    assert isinstance(results[1], Exception)  # user2 failed
    assert results[0] is not None  # user1 succeeded
    assert results[2] is not None  # user3 succeeded
```

### 10. **End-to-End Migration Validation**
**What it validates**: Complete system works with new execution patterns  
**Pass criteria**: Full user journey works from API to WebSocket response  
```python
async def test_e2e_migration_validation():
    # Simulate complete user request through API
    response = await api_client.post("/agent/execute", {
        "agent_type": "supervisor",
        "query": "analyze my data",
        "user_id": "test_user"
    })
    
    # Verify proper response structure
    assert response.status_code == 200
    assert "execution_id" in response.json()
    
    # Wait for WebSocket events
    events = await websocket_client.receive_events(timeout=30)
    
    # Verify all critical events received
    event_types = [e["type"] for e in events]
    required_events = ["agent_started", "agent_completed"]
    assert all(event in event_types for event in required_events)
```

---

## 3. Test Automation Plan

### CI/CD Integration
**Trigger**: Every commit to critical-remediation-20250823 branch  
**Pipeline Stages**:
1. **Fast Feedback** (2 min): Unit + smoke tests
2. **Integration** (10 min): Docker + API + WebSocket tests  
3. **User Isolation** (15 min): Concurrent user isolation tests
4. **E2E Validation** (30 min): Full system tests with real LLM

### Regression Suite
**Daily**: Full test suite execution  
**Pre-merge**: Critical isolation tests + WebSocket events  
**Post-deploy**: E2E validation in staging environment  

### Performance Monitoring
**Continuous**: Resource usage monitoring during tests  
**Alerting**: Memory leaks, response time degradation, event delivery failures  
**Baselines**: Establish performance benchmarks for 1, 5, 10+ concurrent users

---

## 4. Acceptance Criteria Checklist

### Technical Criteria
- [ ] **Zero Singleton Patterns**: No global state in execution path
- [ ] **Perfect User Isolation**: No data leakage between user contexts  
- [ ] **WebSocket Event Accuracy**: 100% correct event routing
- [ ] **Resource Cleanup**: Memory usage returns to baseline after requests
- [ ] **Performance**: Sub-5s response time for 10+ concurrent users
- [ ] **Error Isolation**: Failures in one user don't affect others
- [ ] **Factory Pattern**: All instances created through factories
- [ ] **Context Propagation**: UserExecutionContext flows through entire execution chain

### Business Criteria
- [ ] **Chat Experience**: Real-time progress updates via WebSocket events
- [ ] **User Isolation**: Complete data separation between users
- [ ] **Scalability**: Supports 10+ concurrent users reliably  
- [ ] **Reliability**: No system crashes under concurrent load
- [ ] **Responsiveness**: Users see immediate feedback when starting agents

### Security Criteria  
- [ ] **Data Isolation**: No cross-user data exposure
- [ ] **Permission Boundaries**: Tool access properly scoped to users
- [ ] **Resource Limits**: Per-user resource consumption limits enforced
- [ ] **Secure Cleanup**: Sensitive data properly cleared after requests
- [ ] **Session Isolation**: Database sessions isolated per user

---

## Implementation Priority

**Phase 1** (Critical): User isolation + WebSocket events  
**Phase 2** (High): Performance + resource management  
**Phase 3** (Medium): Advanced error handling + edge cases

**Success Metrics**:
- **Zero** cross-user data leakage incidents
- **100%** WebSocket event delivery accuracy  
- **<5s** response time for 95th percentile
- **10+** concurrent users supported reliably

This test strategy ensures the execution pattern migration delivers on business value (perfect user isolation for substantive AI interactions) while maintaining system reliability and performance.