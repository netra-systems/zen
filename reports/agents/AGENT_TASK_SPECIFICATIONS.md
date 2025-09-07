# AGENT TASK SPECIFICATIONS
## Detailed Instructions for Each Parallel Test Update Agent
### Date: 2025-09-02

---

## AGENT 1: CORE BACKEND UNIT TESTS SPECIALIST

### Mission Statement:
Update all unit tests in `netra_backend/tests/unit/` to implement proper per-user request isolation using UserExecutionContext pattern.

### Specific Files to Update:
```
netra_backend/tests/unit/
├── test_agent_factory.py
├── test_execution_engine.py
├── test_tool_dispatcher.py
├── test_websocket_manager.py
└── test_database_sessions.py
```

### Required Changes Checklist:
- [ ] Replace all `AgentRegistry.get_agent()` calls with `AgentInstanceFactory.create_agent()`
- [ ] Add `UserExecutionContext` fixture to all test classes
- [ ] Update mock objects to include user context
- [ ] Add assertions verifying user_id propagation
- [ ] Remove any global state variables
- [ ] Add cleanup methods for context disposal

### Code Transformation Examples:

#### Before:
```python
def test_agent_execution():
    agent = AgentRegistry.get_agent("test_agent")
    result = agent.execute({"prompt": "test"})
    assert result.status == "success"
```

#### After:
```python
def test_agent_execution(user_context):
    agent = AgentInstanceFactory.create_agent("test_agent", user_context)
    result = agent.execute({"prompt": "test"}, user_context)
    assert result.status == "success"
    assert result.user_id == user_context.user_id
    assert result.request_id == user_context.request_id
```

### Validation Script:
```python
# Run after updates to verify compliance
python scripts/validate_unit_test_isolation.py --path netra_backend/tests/unit/
```

---

## AGENT 2: INTEGRATION TESTS SPECIALIST

### Mission Statement:
Enhance integration tests to validate end-to-end request isolation across multiple components simultaneously.

### Specific Test Scenarios to Add:
1. **Concurrent User Execution Test**
2. **Cross-Service Isolation Test**
3. **Resource Contention Test**
4. **Session Lifecycle Test**
5. **Cleanup Verification Test**

### Required Test Template:
```python
@pytest.mark.asyncio
async def test_concurrent_user_execution():
    """Verify multiple users can execute simultaneously without interference."""
    NUM_USERS = 10
    NUM_REQUESTS_PER_USER = 5
    
    # Create unique contexts for each user
    user_contexts = [
        UserExecutionContext.create_for_user(
            user_id=f"user-{i}",
            session_id=f"session-{i}",
            request_id=f"req-{i}-{j}"
        )
        for i in range(NUM_USERS)
        for j in range(NUM_REQUESTS_PER_USER)
    ]
    
    # Execute all requests concurrently
    tasks = [
        execute_integration_flow(context)
        for context in user_contexts
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Validate isolation
    for i, result in enumerate(results):
        assert not isinstance(result, Exception)
        expected_user = f"user-{i // NUM_REQUESTS_PER_USER}"
        assert result.user_id == expected_user
        
    # Verify no data leakage
    unique_sessions = set(r.session_id for r in results)
    assert len(unique_sessions) == NUM_USERS
```

### Files to Create/Update:
- `tests/integration/test_concurrent_isolation.py`
- `tests/integration/test_cross_service_isolation.py`
- `tests/integration/test_resource_cleanup.py`
- `tests/integration/test_session_lifecycle.py`

---

## AGENT 3: WEBSOCKET TESTS SPECIALIST

### Mission Statement:
Ensure all WebSocket tests validate proper event isolation and prevent cross-user event leakage.

### Critical Validation Points:
1. Events reach only intended user
2. Connection pool properly isolates connections
3. Disconnection cleans up user resources
4. Broadcast events respect user permissions
5. Error events don't leak information

### Required Test Pattern:
```python
class TestWebSocketIsolation:
    async def test_event_routing_isolation(self):
        """Events must route only to intended recipients."""
        pool = WebSocketConnectionPool()
        
        # Setup multiple user connections
        users = {}
        for i in range(5):
            user_id = f"user-{i}"
            conn_id = f"conn-{i}"
            users[user_id] = {
                'context': UserExecutionContext.create_for_user(
                    user_id=user_id,
                    websocket_connection_id=conn_id
                ),
                'events': []
            }
            await pool.register_connection(user_id, conn_id)
        
        # Send targeted events
        for user_id in users:
            event = {"type": "test", "data": f"private-{user_id}"}
            await pool.send_to_user(user_id, event)
        
        # Verify isolation
        for user_id, data in users.items():
            received = await pool.get_user_events(user_id)
            assert len(received) == 1
            assert received[0]['data'] == f"private-{user_id}"
            
        # Test broadcast with permissions
        await pool.broadcast_to_authorized(
            event={"type": "announcement"},
            permission_check=lambda u: u.startswith("user-1")
        )
        
        # Only user-1 should receive broadcast
        assert len(await pool.get_user_events("user-1")) == 2
        assert len(await pool.get_user_events("user-2")) == 1
```

### Files to Update:
- All files matching `**/test_websocket*.py`
- `tests/mission_critical/test_websocket_bridge_isolation.py`
- `netra_backend/tests/services/test_websocket_isolation.py`

---

## AGENT 4: DATABASE & SESSION TESTS SPECIALIST

### Mission Statement:
Validate database session isolation ensuring no session sharing or transaction bleeding between requests.

### Core Principles to Enforce:
1. Each request gets a unique session
2. Sessions are properly disposed after use
3. Transactions don't affect other users
4. Connection pool respects user boundaries
5. No implicit session reuse

### Required Test Implementation:
```python
class TestDatabaseIsolation:
    @pytest.fixture
    async def isolated_session_factory(self):
        """Factory for creating isolated sessions."""
        from netra_backend.database.session_manager import IsolatedSessionFactory
        
        factory = IsolatedSessionFactory()
        yield factory
        await factory.cleanup_all()
    
    async def test_session_isolation(self, isolated_session_factory):
        """Each request must get its own session."""
        context1 = UserExecutionContext.create_for_user("user1")
        context2 = UserExecutionContext.create_for_user("user2")
        
        session1 = await isolated_session_factory.create_session(context1)
        session2 = await isolated_session_factory.create_session(context2)
        
        # Sessions must be different
        assert session1 is not session2
        assert id(session1) != id(session2)
        
        # Test transaction isolation
        async with session1.begin():
            session1.add(UserData(user_id="user1", data="private1"))
            
        async with session2.begin():
            session2.add(UserData(user_id="user2", data="private2"))
        
        # Verify no cross-contamination
        user1_data = await session1.query(UserData).filter_by(user_id="user1").all()
        user2_data = await session2.query(UserData).filter_by(user_id="user2").all()
        
        assert len(user1_data) == 1
        assert len(user2_data) == 1
        assert user1_data[0].data == "private1"
        assert user2_data[0].data == "private2"
        
    async def test_session_cleanup(self, isolated_session_factory):
        """Sessions must be properly cleaned up."""
        context = UserExecutionContext.create_for_user("test-user")
        
        # Track active sessions
        initial_count = isolated_session_factory.active_session_count()
        
        # Create and use session
        async with isolated_session_factory.create_session(context) as session:
            assert isolated_session_factory.active_session_count() == initial_count + 1
            # Do work
            pass
        
        # Session should be cleaned up
        assert isolated_session_factory.active_session_count() == initial_count
```

### Files to Update:
- `tests/netra_backend/database/test_session_isolation.py`
- `tests/unit/test_session_isolation.py`
- `netra_backend/tests/database/test_connection_pool.py`

---

## AGENT 5: AGENT & TOOL TESTS SPECIALIST

### Mission Statement:
Update all agent and tool tests to use instance factories with proper user context isolation.

### Key Patterns to Implement:
1. Agent instance creation per user
2. Tool executor isolation
3. State management per request
4. Concurrent execution validation
5. Resource cleanup verification

### Required Implementation:
```python
class TestAgentIsolation:
    @pytest.fixture
    def agent_factory(self):
        """Provide isolated agent factory."""
        from netra_backend.app.agents.factories import AgentInstanceFactory
        return AgentInstanceFactory()
    
    async def test_agent_instance_isolation(self, agent_factory):
        """Each user gets separate agent instances."""
        context1 = UserExecutionContext.create_for_user("user1")
        context2 = UserExecutionContext.create_for_user("user2")
        
        # Create agents for different users
        agent1 = agent_factory.create_agent("research_agent", context1)
        agent2 = agent_factory.create_agent("research_agent", context2)
        
        # Agents must be different instances
        assert agent1 is not agent2
        assert agent1.user_context.user_id == "user1"
        assert agent2.user_context.user_id == "user2"
        
        # Execute concurrently
        result1, result2 = await asyncio.gather(
            agent1.execute({"query": "test1"}),
            agent2.execute({"query": "test2"})
        )
        
        # Verify isolation
        assert result1.user_id == "user1"
        assert result2.user_id == "user2"
        assert result1.execution_id != result2.execution_id

class TestToolIsolation:
    async def test_tool_executor_isolation(self):
        """Tool executors must be request-scoped."""
        from netra_backend.app.tools.factories import ToolExecutorFactory
        
        factory = ToolExecutorFactory()
        context1 = UserExecutionContext.create_for_user("user1")
        context2 = UserExecutionContext.create_for_user("user2")
        
        executor1 = factory.create_executor(context1)
        executor2 = factory.create_executor(context2)
        
        # Execute same tool for different users
        result1 = await executor1.execute("web_search", {"query": "python"})
        result2 = await executor2.execute("web_search", {"query": "java"})
        
        # Verify isolation
        assert result1.user_context.user_id == "user1"
        assert result2.user_context.user_id == "user2"
        
        # Verify execution history isolation
        history1 = executor1.get_execution_history()
        history2 = executor2.get_execution_history()
        
        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0].query == "python"
        assert history2[0].query == "java"
```

### Files to Update:
- `tests/netra_backend/agents/test_agent_isolation.py`
- `tests/netra_backend/agents/test_execution_isolation.py`
- `netra_backend/tests/agents/test_request_scoped_tool_dispatcher.py`

---

## AGENT 6: MISSION CRITICAL TESTS SPECIALIST

### Mission Statement:
Ensure mission-critical paths have comprehensive isolation validation with stress testing.

### Required Stress Tests:
```python
class TestMissionCriticalIsolation:
    @pytest.mark.stress
    async def test_high_concurrency_isolation(self):
        """System must handle 100+ concurrent users."""
        NUM_USERS = 100
        REQUESTS_PER_USER = 10
        
        async def user_workload(user_id):
            """Simulate realistic user workload."""
            results = []
            for i in range(REQUESTS_PER_USER):
                context = UserExecutionContext.create_for_user(
                    user_id=user_id,
                    request_id=f"{user_id}-req-{i}"
                )
                
                # Execute various operations
                agent_result = await execute_agent(context)
                ws_result = await send_websocket_event(context)
                db_result = await query_database(context)
                
                results.append({
                    'agent': agent_result,
                    'ws': ws_result,
                    'db': db_result
                })
            
            return user_id, results
        
        # Execute all users concurrently
        tasks = [user_workload(f"user-{i}") for i in range(NUM_USERS)]
        user_results = await asyncio.gather(*tasks)
        
        # Validate complete isolation
        for user_id, results in user_results:
            for result in results:
                assert result['agent'].user_id == user_id
                assert result['ws'].user_id == user_id
                assert result['db'].user_id == user_id
        
        # Verify no resource leaks
        assert get_active_sessions_count() == 0
        assert get_active_websocket_count() == 0
        assert get_memory_usage() < initial_memory * 1.1  # Max 10% increase
    
    @pytest.mark.security
    async def test_cross_user_access_prevention(self):
        """Verify cross-user access is impossible."""
        user1_context = UserExecutionContext.create_for_user("user1")
        user2_context = UserExecutionContext.create_for_user("user2")
        
        # User1 creates private data
        await create_private_data(user1_context, "secret-data")
        
        # User2 attempts to access
        with pytest.raises(PermissionDeniedError):
            await access_private_data(user2_context, "user1")
        
        # Verify audit log
        audit_entries = get_security_audit_log()
        assert any(
            e.event_type == "UNAUTHORIZED_ACCESS_ATTEMPT" 
            and e.target_user == "user1" 
            and e.requesting_user == "user2"
            for e in audit_entries
        )
```

### Files to Update:
- `tests/mission_critical/test_concurrent_user_isolation.py`
- `tests/mission_critical/test_websocket_bridge_isolation.py`
- `tests/mission_critical/test_websocket_agent_events_suite.py`

---

## AGENT 7: E2E & API TESTS SPECIALIST

### Mission Statement:
Validate complete request lifecycle from API entry to response with full isolation.

### Required E2E Scenarios:
```python
class TestE2EIsolation:
    @pytest.fixture
    async def test_client(self):
        """Provide authenticated test clients."""
        from httpx import AsyncClient
        async with AsyncClient(base_url="http://localhost:8000") as client:
            yield client
    
    async def test_complete_request_isolation(self, test_client):
        """Full request lifecycle must maintain isolation."""
        # Create test users
        users = []
        for i in range(5):
            user = await create_test_user(f"e2e-user-{i}")
            token = await authenticate_user(user)
            users.append({'user': user, 'token': token})
        
        # Execute concurrent API requests
        async def make_request(user_data):
            headers = {"Authorization": f"Bearer {user_data['token']}"}
            
            # Start agent execution
            response = await test_client.post(
                "/api/agents/execute",
                json={"agent": "research", "prompt": "test"},
                headers=headers
            )
            
            execution_id = response.json()["execution_id"]
            
            # Poll for results
            while True:
                status_response = await test_client.get(
                    f"/api/executions/{execution_id}",
                    headers=headers
                )
                
                if status_response.json()["status"] == "completed":
                    break
                    
                await asyncio.sleep(0.5)
            
            return status_response.json()
        
        # Execute all requests concurrently
        results = await asyncio.gather(*[
            make_request(user_data) for user_data in users
        ])
        
        # Validate isolation
        for i, result in enumerate(results):
            assert result["user_id"] == users[i]['user'].id
            assert result["execution_id"] is not None
            
        # Verify no cross-contamination in results
        execution_ids = [r["execution_id"] for r in results]
        assert len(set(execution_ids)) == len(execution_ids)  # All unique
    
    async def test_api_rate_limiting_per_user(self, test_client):
        """Rate limiting must be per-user, not global."""
        user1_token = await get_test_token("user1")
        user2_token = await get_test_token("user2")
        
        # User1 hits rate limit
        for _ in range(100):
            await test_client.get("/api/test", 
                                headers={"Authorization": f"Bearer {user1_token}"})
        
        # User1 should be rate limited
        response1 = await test_client.get("/api/test",
                                        headers={"Authorization": f"Bearer {user1_token}"})
        assert response1.status_code == 429
        
        # User2 should NOT be affected
        response2 = await test_client.get("/api/test",
                                        headers={"Authorization": f"Bearer {user2_token}"})
        assert response2.status_code == 200
```

### Files to Update:
- `tests/e2e/test_user_isolation.py`
- `tests/e2e/test_api_isolation.py`
- `tests/api/test_authentication_isolation.py`

---

## AGENT 8: SERVICE-SPECIFIC TESTS SPECIALIST

### Mission Statement:
Ensure each microservice maintains proper isolation boundaries.

### Service-Specific Requirements:

#### Auth Service:
```python
class TestAuthServiceIsolation:
    async def test_token_isolation(self):
        """Tokens must be user-specific and non-forgeable."""
        token1 = generate_token(user_id="user1", session_id="sess1")
        token2 = generate_token(user_id="user2", session_id="sess2")
        
        # Tokens must be unique
        assert token1 != token2
        
        # Decode and verify
        payload1 = decode_and_verify_token(token1)
        payload2 = decode_and_verify_token(token2)
        
        assert payload1["user_id"] == "user1"
        assert payload2["user_id"] == "user2"
        
        # Cross-validation should fail
        with pytest.raises(InvalidTokenError):
            validate_token_for_user(token1, "user2")
```

#### Analytics Service:
```python
class TestAnalyticsIsolation:
    async def test_event_tracking_isolation(self):
        """Events must be properly attributed to users."""
        context1 = UserExecutionContext.create_for_user("analytics-user1")
        context2 = UserExecutionContext.create_for_user("analytics-user2")
        
        # Track events
        await track_event("page_view", {"page": "/home"}, context1)
        await track_event("page_view", {"page": "/profile"}, context2)
        
        # Query events
        events1 = await query_user_events(context1.user_id)
        events2 = await query_user_events(context2.user_id)
        
        assert len(events1) == 1
        assert events1[0]["page"] == "/home"
        
        assert len(events2) == 1
        assert events2[0]["page"] == "/profile"
```

#### Frontend Service:
```python
class TestFrontendIsolation:
    async def test_session_storage_isolation(self):
        """Frontend sessions must be user-isolated."""
        session1 = create_frontend_session(user_id="frontend-user1")
        session2 = create_frontend_session(user_id="frontend-user2")
        
        # Store user-specific data
        session1.set("theme", "dark")
        session2.set("theme", "light")
        
        # Verify isolation
        assert session1.get("theme") == "dark"
        assert session2.get("theme") == "light"
        
        # Sessions should have different IDs
        assert session1.session_id != session2.session_id
```

### Files to Update:
- `auth_service/tests/test_token_isolation.py`
- `analytics_service/tests/test_event_isolation.py`
- `frontend/tests/test_session_isolation.py`

---

## COMMON UTILITIES FOR ALL AGENTS

### Shared Test Fixtures:
```python
# test_framework/fixtures/isolation_fixtures.py

@pytest.fixture
async def user_context():
    """Provide isolated user context."""
    context = UserExecutionContext.create_for_user(
        user_id=f"test-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
        request_id=f"request-{uuid.uuid4()}"
    )
    yield context
    await cleanup_context(context)

@pytest.fixture
async def isolated_database():
    """Provide isolated database session."""
    from netra_backend.database.isolation import IsolatedDatabase
    db = IsolatedDatabase()
    yield db
    await db.cleanup()

@pytest.fixture
async def websocket_pool():
    """Provide isolated WebSocket pool."""
    from netra_backend.websocket.pool import IsolatedWebSocketPool
    pool = IsolatedWebSocketPool()
    yield pool
    await pool.cleanup_all()
```

### Validation Helpers:
```python
# test_framework/validators/isolation_validators.py

def assert_no_cross_contamination(results: List[Any], user_field: str = "user_id"):
    """Verify results have no cross-user contamination."""
    user_ids = [getattr(r, user_field) for r in results]
    unique_ids = set(user_ids)
    
    assert len(unique_ids) == len(results), \
        f"Cross-contamination detected: {len(results)} results but only {len(unique_ids)} unique users"

def assert_proper_cleanup(before_count: int, after_count: int, resource_name: str):
    """Verify resources were properly cleaned up."""
    assert after_count <= before_count, \
        f"{resource_name} leak detected: {after_count} > {before_count}"

async def validate_concurrent_isolation(
    num_users: int,
    operation: Callable,
    validation: Callable
):
    """Helper for concurrent isolation testing."""
    contexts = [
        UserExecutionContext.create_for_user(f"user-{i}")
        for i in range(num_users)
    ]
    
    results = await asyncio.gather(*[
        operation(ctx) for ctx in contexts
    ])
    
    for i, (ctx, result) in enumerate(zip(contexts, results)):
        validation(ctx, result, i)
```

---

## EXECUTION MONITORING

### Progress Tracking Script:
```python
# scripts/monitor_test_updates.py

import asyncio
from pathlib import Path
import json

class TestUpdateMonitor:
    def __init__(self, num_agents: int):
        self.num_agents = num_agents
        self.progress = {f"agent_{i+1}": 0 for i in range(num_agents)}
        self.completed_files = set()
        self.failed_files = set()
    
    async def monitor_progress(self):
        """Monitor and report progress."""
        while True:
            self.update_progress()
            self.display_dashboard()
            
            if self.is_complete():
                self.generate_final_report()
                break
                
            await asyncio.sleep(10)
    
    def update_progress(self):
        """Check actual file updates."""
        for agent_id in self.progress:
            completed = self.count_updated_files(agent_id)
            total = self.count_total_files(agent_id)
            self.progress[agent_id] = (completed / total) * 100 if total > 0 else 0
    
    def display_dashboard(self):
        """Display progress dashboard."""
        print("\n" + "="*50)
        print("TEST UPDATE PROGRESS")
        print("="*50)
        
        for agent_id, progress in self.progress.items():
            bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
            print(f"{agent_id}: {bar} {progress:.1f}%")
        
        print(f"\nCompleted Files: {len(self.completed_files)}")
        print(f"Failed Files: {len(self.failed_files)}")
        print("="*50)

if __name__ == "__main__":
    monitor = TestUpdateMonitor(num_agents=8)
    asyncio.run(monitor.monitor_progress())
```

---

END OF SPECIFICATIONS