# PARALLEL AGENT TEST UPDATE PLAN
## Per-User Request Isolation Pattern Implementation
### Date: 2025-09-02

---

## EXECUTIVE SUMMARY

This plan orchestrates parallel agent execution to update all test suites with the latest per-user request isolation patterns. The goal is to ensure every test properly validates request isolation, preventing data leakage between concurrent users.

### Scope:
- **Test Files to Update**: ~150+ test files across all services
- **Parallel Agents**: 8 specialized agents working concurrently
- **Estimated Time**: 2-3 hours with parallel execution
- **Success Criteria**: 100% test pass rate with isolation validation

---

## PHASE 1: AGENT TASK DISTRIBUTION

### Agent 1: Core Backend Unit Tests
**Scope**: `netra_backend/tests/unit/**`
**Focus**: Update unit tests to use UserExecutionContext
**Key Patterns**:
```python
# Before (WRONG):
agent = AgentRegistry.get_agent("test_agent")

# After (CORRECT):
user_context = UserExecutionContext.create_for_user(user_id="test-user-123")
agent = agent_instance_factory.create_agent("test_agent", user_context)
```

**Specific Tasks**:
1. Replace all AgentRegistry.get_agent() with factory pattern
2. Add UserExecutionContext to all test fixtures
3. Validate isolation with concurrent test scenarios
4. Remove any global state references

---

### Agent 2: Integration Tests
**Scope**: `tests/integration/**`
**Focus**: End-to-end request isolation validation
**Key Patterns**:
```python
# Add isolation verification
async def test_concurrent_user_isolation():
    user1_context = UserExecutionContext.create_for_user("user-1")
    user2_context = UserExecutionContext.create_for_user("user-2")
    
    # Execute concurrently
    results = await asyncio.gather(
        execute_with_context(user1_context),
        execute_with_context(user2_context)
    )
    
    # Verify no cross-contamination
    assert results[0].user_id == "user-1"
    assert results[1].user_id == "user-2"
```

**Specific Tasks**:
1. Add concurrent user simulation tests
2. Verify WebSocket event isolation
3. Test database session isolation
4. Validate resource cleanup

---

### Agent 3: WebSocket Tests
**Scope**: `**/test_websocket*.py`, `**/websocket/**`
**Focus**: WebSocket event routing isolation
**Key Patterns**:
```python
# Ensure WebSocket manager uses user context
websocket_manager = WebSocketConnectionPool()
user_context = UserExecutionContext.create_for_user(
    user_id="test-user",
    websocket_connection_id="ws-conn-123"
)
emitter = websocket_manager.create_emitter(user_context)

# Verify events go only to correct user
emitter.emit_event("test_event", {"data": "test"})
assert_event_received_by_user("test-user", "test_event")
assert_no_event_received_by_user("other-user", "test_event")
```

**Specific Tasks**:
1. Update all WebSocket tests to use connection pool
2. Add cross-user event leakage detection
3. Verify connection cleanup on disconnect
4. Test concurrent WebSocket connections

---

### Agent 4: Database & Session Tests
**Scope**: `**/database/**`, `**/test_*session*.py`
**Focus**: Database session isolation per request
**Key Patterns**:
```python
# Each request gets isolated session
async def test_database_isolation():
    async with create_request_session() as session1:
        async with create_request_session() as session2:
            # Sessions must be different instances
            assert session1 is not session2
            
            # Changes in one don't affect the other
            session1.add(TestModel(data="user1"))
            session2.add(TestModel(data="user2"))
            
            # Verify isolation
            assert session1.query(TestModel).count() == 1
            assert session2.query(TestModel).count() == 1
```

**Specific Tasks**:
1. Remove all shared session references
2. Add session lifecycle validation
3. Test transaction isolation
4. Verify proper session disposal

---

### Agent 5: Agent & Tool Tests
**Scope**: `**/agents/**`, `**/tools/**`
**Focus**: Agent instance and tool executor isolation
**Key Patterns**:
```python
# Tool dispatcher with user context
tool_dispatcher = ToolDispatcherFactory.create_for_user(user_context)

# Each user gets separate tool instances
async def test_tool_isolation():
    dispatcher1 = ToolDispatcherFactory.create_for_user(context1)
    dispatcher2 = ToolDispatcherFactory.create_for_user(context2)
    
    # Execute same tool for different users
    result1 = await dispatcher1.execute_tool("calculator", {"op": "add"})
    result2 = await dispatcher2.execute_tool("calculator", {"op": "multiply"})
    
    # Verify no shared state
    assert dispatcher1._execution_history != dispatcher2._execution_history
```

**Specific Tasks**:
1. Update all agent creation to use factory
2. Add tool executor isolation tests
3. Verify agent state isolation
4. Test concurrent tool execution

---

### Agent 6: Mission Critical Tests
**Scope**: `tests/mission_critical/**`
**Focus**: Critical path isolation validation
**Key Patterns**:
```python
# Mission critical must validate ALL isolation points
class TestCriticalIsolation:
    def test_complete_request_isolation(self):
        # Test all components together
        user_context = UserExecutionContext.create_for_user("critical-user")
        
        # Validate each layer
        assert_agent_isolation(user_context)
        assert_websocket_isolation(user_context)
        assert_database_isolation(user_context)
        assert_tool_isolation(user_context)
        
        # Stress test with concurrent load
        run_concurrent_isolation_test(users=10, requests_per_user=100)
```

**Specific Tasks**:
1. Add comprehensive isolation test suite
2. Stress test with high concurrency
3. Validate security boundaries
4. Test resource exhaustion scenarios

---

### Agent 7: E2E & API Tests
**Scope**: `tests/e2e/**`, `tests/api/**`
**Focus**: Full request lifecycle isolation
**Key Patterns**:
```python
# E2E must simulate real user requests
async def test_e2e_user_isolation():
    # Create test users
    user1 = await create_test_user("user1")
    user2 = await create_test_user("user2")
    
    # Authenticate separately
    token1 = await authenticate(user1)
    token2 = await authenticate(user2)
    
    # Execute concurrent requests
    async with aiohttp.ClientSession() as session:
        task1 = execute_agent_request(session, token1, "agent1")
        task2 = execute_agent_request(session, token2, "agent2")
        
        results = await asyncio.gather(task1, task2)
        
    # Verify complete isolation
    assert results[0]["user_id"] == user1.id
    assert results[1]["user_id"] == user2.id
    assert no_data_leakage(results[0], results[1])
```

**Specific Tasks**:
1. Add multi-user E2E scenarios
2. Test API authentication isolation
3. Verify response isolation
4. Test rate limiting per user

---

### Agent 8: Service-Specific Tests
**Scope**: `auth_service/tests/**`, `analytics_service/tests/**`, `frontend/tests/**`
**Focus**: Service boundary isolation
**Key Patterns**:
```python
# Each service maintains its own isolation
# Auth Service
def test_auth_token_isolation():
    token1 = generate_token(user_id="user1")
    token2 = generate_token(user_id="user2")
    
    # Tokens must be unique and isolated
    assert decode_token(token1)["user_id"] == "user1"
    assert decode_token(token2)["user_id"] == "user2"
    assert token1 != token2

# Analytics Service
def test_analytics_data_isolation():
    # Events must be tagged with user context
    track_event("page_view", user_context=context1)
    track_event("page_view", user_context=context2)
    
    # Query must respect user boundaries
    events1 = query_events(user_id="user1")
    events2 = query_events(user_id="user2")
    
    assert len(events1) == 1
    assert len(events2) == 1
    assert events1[0].user_id != events2[0].user_id
```

**Specific Tasks**:
1. Update service-specific isolation patterns
2. Add cross-service isolation tests
3. Verify JWT/session isolation
4. Test service-to-service communication

---

## PHASE 2: EXECUTION STRATEGY

### Parallel Execution Plan:
```bash
# Launch all agents simultaneously
python scripts/launch_test_update_agents.py \
    --agents 8 \
    --pattern "request_isolation" \
    --parallel \
    --validate-after-update
```

### Agent Coordination:
1. **Central Coordinator**: Monitors progress and handles conflicts
2. **Shared Lock File**: Prevents file conflicts between agents
3. **Progress Tracking**: Real-time dashboard of update status
4. **Validation Queue**: Tests run after each batch of updates

---

## PHASE 3: VALIDATION & VERIFICATION

### Success Criteria:
1. ✅ All tests updated with UserExecutionContext pattern
2. ✅ No direct AgentRegistry.get_agent() calls remain
3. ✅ All WebSocket tests validate user isolation
4. ✅ Database sessions properly scoped per request
5. ✅ Concurrent user tests added to all critical paths
6. ✅ 100% test pass rate after updates

### Validation Commands:
```bash
# Run comprehensive isolation validation
python tests/unified_test_runner.py \
    --category isolation \
    --real-services \
    --concurrent-users 10

# Verify no isolation violations
python scripts/check_isolation_patterns.py --strict

# Run security audit
python scripts/security_audit.py --focus isolation
```

---

## PHASE 4: COMMON PATTERNS TO IMPLEMENT

### Pattern 1: Test Fixture with User Context
```python
@pytest.fixture
async def user_context():
    """Create isolated user context for tests."""
    context = UserExecutionContext.create_for_user(
        user_id=f"test-user-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
        request_id=f"request-{uuid.uuid4()}"
    )
    yield context
    # Cleanup if needed
    await cleanup_user_context(context)
```

### Pattern 2: Concurrent User Testing
```python
async def test_concurrent_users(num_users=5):
    """Test multiple users executing simultaneously."""
    contexts = [
        UserExecutionContext.create_for_user(f"user-{i}")
        for i in range(num_users)
    ]
    
    tasks = [
        execute_user_request(context)
        for context in contexts
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify each user's results are isolated
    for i, result in enumerate(results):
        assert result.user_id == f"user-{i}"
        assert result.session_id == contexts[i].session_id
        
    # Verify no cross-contamination
    assert len(set(r.session_id for r in results)) == num_users
```

### Pattern 3: WebSocket Isolation Testing
```python
async def test_websocket_event_isolation():
    """Verify WebSocket events are user-isolated."""
    pool = WebSocketConnectionPool()
    
    # Create multiple user connections
    conn1 = await pool.register_connection("user1", "ws1")
    conn2 = await pool.register_connection("user2", "ws2")
    
    # Send events to specific users
    await pool.send_to_user("user1", {"event": "test1"})
    await pool.send_to_user("user2", {"event": "test2"})
    
    # Verify isolation
    assert conn1.received_events == [{"event": "test1"}]
    assert conn2.received_events == [{"event": "test2"}]
```

### Pattern 4: Database Session Isolation
```python
@pytest.mark.asyncio
async def test_database_session_isolation():
    """Verify database sessions are request-scoped."""
    from netra_backend.database.session_manager import RequestScopedSessionManager
    
    manager = RequestScopedSessionManager()
    
    # Create sessions for different requests
    session1 = await manager.create_session(request_id="req1")
    session2 = await manager.create_session(request_id="req2")
    
    # Sessions must be different instances
    assert session1 is not session2
    
    # Test transaction isolation
    async with session1.begin():
        session1.add(TestModel(name="item1"))
        
    async with session2.begin():
        session2.add(TestModel(name="item2"))
        
    # Verify isolation
    items1 = await session1.query(TestModel).all()
    items2 = await session2.query(TestModel).all()
    
    assert len(items1) == 1
    assert len(items2) == 1
    assert items1[0].name != items2[0].name
```

---

## ANTI-PATTERNS TO REMOVE

### ❌ Global State Access
```python
# WRONG - Never use global registries directly
agent = AgentRegistry.get_agent("my_agent")
tool = ToolRegistry.get_tool("calculator")

# CORRECT - Always use factories with context
agent = agent_factory.create_agent("my_agent", user_context)
tool = tool_factory.create_tool("calculator", user_context)
```

### ❌ Shared Session Usage
```python
# WRONG - Never share sessions
class TestService:
    def __init__(self):
        self.session = create_session()  # Shared across requests!

# CORRECT - Create per-request sessions
class TestService:
    async def handle_request(self, user_context):
        async with create_request_session(user_context) as session:
            # Use session only within request scope
            pass
```

### ❌ Singleton WebSocket Managers
```python
# WRONG - Never use singleton WebSocket managers
websocket_manager = WebSocketManager()  # Global singleton!

# CORRECT - Use connection pool with user context
pool = WebSocketConnectionPool()
emitter = pool.create_emitter(user_context)
```

---

## MONITORING & REPORTING

### Progress Tracking Dashboard:
```
┌─────────────────────────────────────────────┐
│  TEST UPDATE PROGRESS DASHBOARD             │
├─────────────────────────────────────────────┤
│ Agent 1 (Core Backend):  ████████░░ 80%    │
│ Agent 2 (Integration):   ██████░░░░ 60%    │
│ Agent 3 (WebSocket):     █████████░ 90%    │
│ Agent 4 (Database):      ███████░░░ 70%    │
│ Agent 5 (Agents/Tools):  ████████░░ 80%    │
│ Agent 6 (Mission Crit):  ██████████ 100%   │
│ Agent 7 (E2E/API):       █████░░░░░ 50%    │
│ Agent 8 (Services):      ███████░░░ 70%    │
├─────────────────────────────────────────────┤
│ Total Files Updated: 112/150                │
│ Tests Passing: 98%                          │
│ Isolation Violations Found: 3               │
│ Estimated Completion: 45 minutes            │
└─────────────────────────────────────────────┘
```

### Final Report Structure:
```markdown
# Test Update Completion Report
## Summary
- Total Files Updated: 150
- Patterns Applied: 4 core patterns
- Anti-patterns Removed: 247 instances
- New Tests Added: 89 isolation tests
- Test Coverage: 95% → 98%

## Isolation Validation Results
- Concurrent User Tests: ✅ All passing
- WebSocket Isolation: ✅ Verified
- Database Isolation: ✅ Confirmed
- Tool Isolation: ✅ Complete

## Remaining Work
- None - All tests updated successfully
```

---

## LAUNCH COMMAND

```bash
# Execute the parallel agent update plan
python scripts/execute_parallel_test_update.py \
    --plan PARALLEL_AGENT_TEST_UPDATE_PLAN.md \
    --agents 8 \
    --timeout 10800 \
    --validate-continuously \
    --report-interval 60 \
    --fail-fast false
```

---

## SUCCESS METRICS

1. **Zero Isolation Violations**: No test allows data leakage
2. **100% Pattern Compliance**: All tests use new patterns
3. **Performance**: <5% overhead from isolation
4. **Maintainability**: Clear, consistent patterns across all tests
5. **Documentation**: Every test documents its isolation strategy

---

END OF PLAN