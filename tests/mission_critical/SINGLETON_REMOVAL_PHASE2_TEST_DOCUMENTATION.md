# Singleton Removal Phase 2 Test Suite Documentation

## Business Value Justification

**Segment:** Enterprise/Platform  
**Business Goal:** Concurrent User Support & System Stability  
**Value Impact:** Enables 10+ concurrent users without data leakage, blocking, or performance degradation  
**Strategic Impact:** Foundation for enterprise scalability and multi-tenant isolation  

## Executive Summary

This comprehensive test suite validates the critical architectural requirement of removing singleton patterns that prevent proper concurrent user isolation. **All tests in this suite are EXPECTED TO FAIL** with the current singleton-based architecture, serving as validation criteria for the singleton removal work.

## Current Architectural Problems

### 1. WebSocketManager Singleton (`netra_backend/app/websocket_core/manager.py`)

**Problem:** Lines 60, 76-79, 797-827
```python
class WebSocketManager:
    _instance: Optional['WebSocketManager'] = None
    
    def __new__(cls) -> 'WebSocketManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

def get_websocket_manager() -> WebSocketManager:
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
```

**Business Impact:**
- All users share the same WebSocket manager instance
- User A receives User B's agent events and notifications
- Connection state mixing causes message routing failures
- Memory accumulates globally instead of per-user cleanup

**Required Fix:**
```python
# Replace singleton with factory
def create_websocket_manager(user_context: UserContext) -> WebSocketManager:
    return WebSocketManager(user_context=user_context)

# Or use dependency injection container
@injectable
class WebSocketManager:
    def __init__(self, user_context: UserContext):
        self.user_context = user_context
        # Per-user state initialization
```

### 2. AgentWebSocketBridge Singleton (`netra_backend/app/services/agent_websocket_bridge.py`)

**Problem:** Lines 101, 104-108, 2150-2162
```python
class AgentWebSocketBridge(MonitorableComponent):
    _instance: Optional['AgentWebSocketBridge'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'AgentWebSocketBridge':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

async def get_agent_websocket_bridge() -> AgentWebSocketBridge:
    global _bridge_instance
    if _bridge_instance is None:
        async with AgentWebSocketBridge._lock:
            if _bridge_instance is None:
                _bridge_instance = AgentWebSocketBridge()
    return _bridge_instance
```

**Business Impact:**
- WebSocket notifications sent to all users instead of target user
- Run ID to thread ID mappings shared across users
- Agent death notifications broadcast globally
- Thread resolution failures due to shared state

**Required Fix:**
```python
# Replace with per-user bridge factory
async def create_agent_websocket_bridge(
    user_context: UserContext,
    websocket_manager: WebSocketManager
) -> AgentWebSocketBridge:
    return AgentWebSocketBridge(
        user_context=user_context,
        websocket_manager=websocket_manager
    )
```

### 3. AgentExecutionRegistry Singleton (`netra_backend/app/orchestration/agent_execution_registry.py`)

**Problem:** Lines 78-92
```python
class AgentExecutionRegistry:
    _instance: Optional['AgentExecutionRegistry'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'AgentExecutionRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Business Impact:**
- Agent executions mixed up between users
- Execution contexts shared causing data leakage
- Race conditions in shared registry state
- Performance bottleneck as single registry handles all users

**Required Fix:**
```python
# Replace with per-request registry
async def create_agent_execution_registry(
    request_context: RequestContext
) -> AgentExecutionRegistry:
    return AgentExecutionRegistry(request_context=request_context)
```

## Test Suite Structure

### 1. Test Categories

#### Category 1: Concurrent User Execution Isolation
- **File:** `test_singleton_removal_phase2.py` - Lines 180-350
- **Tests:** 3 tests covering WebSocket, Registry, and Bridge isolation
- **Expected Failures:** All tests fail due to singleton state sharing
- **Validation:** 10+ users execute simultaneously without data mixing

#### Category 2: WebSocket Event User Isolation  
- **File:** `test_singleton_removal_phase2.py` - Lines 351-530
- **Tests:** 2 tests covering event routing and death notifications
- **Expected Failures:** Events broadcast to all users instead of target user
- **Validation:** User-specific events only reach intended recipients

#### Category 3: Factory Pattern Validation
- **File:** `test_singleton_removal_phase2.py` - Lines 531-670
- **Tests:** 3 tests covering manager, bridge, and registry factories
- **Expected Failures:** Factories return same singleton instance
- **Validation:** Each factory call returns unique instance

#### Category 4: Memory Leak Prevention
- **File:** `test_singleton_removal_phase2.py` - Lines 671-800
- **Tests:** 2 tests covering bounded memory growth
- **Expected Failures:** Singleton accumulates unbounded memory
- **Validation:** Memory usage scales linearly with user count

#### Category 5: Race Condition Protection
- **File:** `test_singleton_removal_phase2.py` - Lines 801-950
- **Tests:** 2 tests covering concurrent modifications
- **Expected Failures:** Shared singleton state creates race conditions
- **Validation:** Concurrent operations don't interfere

#### Category 6: Performance Under Load
- **File:** `test_singleton_removal_phase2.py` - Lines 951-1100
- **Tests:** 2 tests covering performance scaling
- **Expected Failures:** Singleton bottlenecks degrade performance
- **Validation:** System handles 20+ users with linear performance

#### Category 7: Comprehensive Validation
- **File:** `test_singleton_removal_phase2.py` - Lines 1101-1300
- **Tests:** 1 comprehensive test combining all issues
- **Expected Failures:** Multiple singleton issues compound
- **Validation:** Realistic concurrent user workflows succeed

### 2. Test Helper Utilities

#### File: `helpers/singleton_test_helpers.py`
- **MockUserContext:** Complete user session representation (Lines 30-120)
- **IsolationTestResult:** Comprehensive test result analysis (Lines 130-200)
- **SingletonDetector:** Detects singleton patterns in runtime (Lines 210-320)
- **ConcurrentUserSimulator:** Simulates concurrent user workflows (Lines 330-650)
- **WebSocketEventCapture:** Captures and analyzes WebSocket events (Lines 660-760)
- **MemoryLeakDetector:** Detects memory leaks in concurrent scenarios (Lines 770-850)
- **PerformanceProfiler:** Profiles performance under concurrent load (Lines 860-1000)

## Expected Test Results with Current Architecture

### ❌ ALL TESTS WILL FAIL

1. **Concurrent User Execution Isolation**
   ```
   ASSERTION ERROR: SINGLETON FAILURE: 12 data leakage incidents detected.
   WebSocketManager singleton is sharing state between users.
   ```

2. **WebSocket Event User Isolation**
   ```
   ASSERTION ERROR: WEBSOCKET EVENT ISOLATION FAILURE: 8 event routing errors detected.
   Singleton WebSocket architecture is mixing user events.
   ```

3. **Factory Pattern Validation**
   ```
   ASSERTION ERROR: WEBSOCKET MANAGER FACTORY FAILURE: Factory returns shared instances.
   get_websocket_manager() must return unique instances per call.
   ```

4. **Memory Leak Prevention**
   ```
   ASSERTION ERROR: MEMORY LEAK FAILURE: WebSocket manager grew by 127.3MB after 100 users.
   Singleton pattern prevents proper memory cleanup.
   ```

5. **Race Condition Protection**
   ```
   ASSERTION ERROR: RACE CONDITION FAILURE: 15 race condition errors detected.
   Concurrent modifications to shared singleton state are not thread-safe.
   ```

6. **Performance Under Load**
   ```
   ASSERTION ERROR: PERFORMANCE DEGRADATION FAILURE: Response time increased by 4.2x.
   Singleton architecture creates performance bottlenecks.
   ```

7. **Comprehensive Validation**
   ```
   COMPREHENSIVE SINGLETON REMOVAL VALIDATION FAILED
   BUSINESS IMPACT: System cannot support concurrent users in production
   REQUIRED FIXES: Replace all singleton patterns with factory patterns
   ```

## Success Criteria (After Singleton Removal)

### ✅ ALL TESTS SHOULD PASS

1. **Component Isolation:** Each user gets unique component instances
2. **Data Isolation:** No data leakage between user sessions  
3. **Event Isolation:** WebSocket events only reach intended users
4. **Memory Efficiency:** Linear memory scaling with user count
5. **Performance Scaling:** Linear performance scaling with user count
6. **Concurrency Safety:** No race conditions in user-scoped components
7. **Factory Uniqueness:** Factory functions return unique instances

## Implementation Strategy

### Phase 1: Factory Pattern Implementation

1. **Replace Singleton Constructors**
   ```python
   # Before (Singleton)
   class WebSocketManager:
       _instance = None
       def __new__(cls): ...
   
   # After (Factory)
   @dataclass
   class UserContext:
       user_id: str
       session_id: str
   
   def create_websocket_manager(user_context: UserContext) -> WebSocketManager:
       return WebSocketManager(user_context)
   ```

2. **Implement User-Scoped State**
   ```python
   class WebSocketManager:
       def __init__(self, user_context: UserContext):
           self.user_context = user_context
           self.connections = {}  # Per-user connections
           self.user_connections = {}  # Per-user mapping
   ```

3. **Add Dependency Injection**
   ```python
   @injectable
   class AgentWebSocketBridge:
       def __init__(self, 
                    user_context: UserContext,
                    websocket_manager: WebSocketManager):
           self.user_context = user_context
           self.websocket_manager = websocket_manager
   ```

### Phase 2: Request Scoping

1. **Request-Scoped Components**
   ```python
   @request_scoped
   class AgentExecutionRegistry:
       def __init__(self, request_context: RequestContext):
           self.request_context = request_context
           self.active_runs = {}  # Per-request runs
   ```

2. **Session Management**
   ```python
   class UserSessionManager:
       def __init__(self):
           self.active_sessions: Dict[str, UserSession] = {}
       
       async def create_session(self, user_id: str) -> UserSession:
           session = UserSession(user_id)
           self.active_sessions[session.session_id] = session
           return session
   ```

### Phase 3: Integration Testing

1. **Run Test Suite:** `python -m pytest tests/mission_critical/test_singleton_removal_phase2.py -v`
2. **Validate Success:** All tests should pass
3. **Performance Testing:** Verify linear scaling with user count
4. **Load Testing:** Confirm system handles 50+ concurrent users

## Test Execution Instructions

### Running the Test Suite

```bash
# Run all singleton removal tests
python -m pytest tests/mission_critical/test_singleton_removal_phase2.py -v -s

# Run specific test categories
python -m pytest tests/mission_critical/test_singleton_removal_phase2.py -k "concurrent_user" -v

# Run with detailed output
python -m pytest tests/mission_critical/test_singleton_removal_phase2.py -v -s --tb=long

# Run comprehensive test only
python -m pytest tests/mission_critical/test_singleton_removal_phase2.py -k "comprehensive" -v
```

### Expected Output (Before Fixes)

```
=== FAILURES ===
test_concurrent_user_execution_isolation FAILED
test_websocket_event_user_isolation FAILED  
test_websocket_manager_factory_uniqueness FAILED
test_memory_leak_prevention FAILED
test_race_condition_protection FAILED
test_performance_degradation FAILED
test_comprehensive_singleton_removal_validation FAILED

=== 7 failed, 0 passed ===
```

### Expected Output (After Fixes)

```
=== test session starts ===
test_concurrent_user_execution_isolation PASSED
test_websocket_event_user_isolation PASSED
test_websocket_manager_factory_uniqueness PASSED  
test_memory_leak_prevention PASSED
test_race_condition_protection PASSED
test_performance_degradation PASSED
test_comprehensive_singleton_removal_validation PASSED

=== 7 passed, 0 failed ===
```

## Monitoring and Metrics

### Key Metrics to Track

1. **Isolation Success Rate:** % of users with perfect state isolation
2. **Memory Efficiency:** MB memory per concurrent user
3. **Performance Scaling:** Response time vs user count relationship
4. **Event Routing Accuracy:** % of events reaching correct users
5. **Concurrency Safety:** Race condition incidents per 1000 operations

### Continuous Validation

1. **CI/CD Integration:** Run tests on every commit
2. **Performance Regression Detection:** Alert on performance degradation
3. **Memory Leak Monitoring:** Track memory growth patterns
4. **Load Testing:** Regular tests with 50+ concurrent users

## Business Impact Analysis

### Current State (Singleton Architecture)
- **Maximum Concurrent Users:** 1-2 (with data leakage risk)
- **Memory Usage:** Unbounded growth with user count
- **Performance:** Exponential degradation with users
- **Data Security:** High risk of user data leakage
- **Enterprise Readiness:** Not suitable for production

### Target State (Factory Architecture) 
- **Maximum Concurrent Users:** 50+ (with perfect isolation)
- **Memory Usage:** Linear scaling with user count
- **Performance:** Linear scaling with user count  
- **Data Security:** Perfect user data isolation
- **Enterprise Readiness:** Production-ready multi-tenant system

## Conclusion

This test suite provides comprehensive validation for the critical singleton removal work required to enable concurrent user support. The tests serve as both:

1. **Requirements Validation:** Define exactly what concurrent user isolation means
2. **Implementation Validation:** Verify that singleton removal work is complete and correct

**All tests are expected to fail with the current architecture** and serve as the success criteria for the singleton removal implementation work.