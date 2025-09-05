# WebSocket V2 Factory Pattern Migration Plan

## Critical Security Migration - Phase 1: Core Services

### Overview
Migrating from singleton `get_websocket_manager()` to factory pattern `create_websocket_manager(user_context)` to ensure complete user isolation and prevent data leakage in multi-user environments.

## Migration Strategy

### Phase 1: Critical Services (Immediate)

#### 1. message_processing.py
**Current State:**
```python
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()  # GLOBAL SINGLETON - SECURITY RISK
```

**Migration Requirements:**
- Remove global manager instantiation
- Pass UserExecutionContext through all function calls
- Create manager per request using factory pattern

**Implementation:**
```python
from netra_backend.app.websocket_core import create_websocket_manager

async def process_message(message: Dict, user_context: UserExecutionContext):
    manager = create_websocket_manager(user_context)
    # Process with isolated manager
```

#### 2. message_handlers.py
**Current State:**
```python
manager = get_websocket_manager()  # Line 69 - GLOBAL SINGLETON
```

**Migration Requirements:**
- Inject manager via constructor or method parameters
- Ensure all handler methods receive user context

#### 3. routes/websocket.py
**Current State:**
- Multiple calls to `get_websocket_manager()` throughout
- Lines: 183, 547, 782, 828, 877, 1126

**Migration Requirements:**
- Extract user context from WebSocket connection
- Create manager per connection/request
- Pass manager through WebSocket lifecycle

### Phase 2: High Priority Services

#### 4. agent_websocket_bridge.py
**Migration Points:**
- Line 279: `websocket_manager = get_websocket_manager()`
- Line 2388: `manager = get_websocket_manager()`

**Requirements:**
- Update bridge initialization to accept user context
- Ensure all agent executions use isolated managers

#### 5. agent_service_core.py
**Migration Points:**
- Lines 190, 195, 343, 370, 394: Multiple `get_websocket_manager()` calls

**Requirements:**
- Thread user context through service methods
- Create manager per agent execution

#### 6. websocket_core/agent_handler.py
**Migration Points:**
- 6 occurrences of `get_websocket_manager()`

**Requirements:**
- Update handler to use factory pattern
- Ensure proper context isolation

### Phase 3: Support Services

#### 7. dependencies.py
- Update dependency injection to provide isolated managers
- Ensure proper scoping per request

#### 8. thread_service.py
- Remove global manager
- Pass context through thread operations

#### 9. websocket_event_router.py
- Update routing to use factory pattern

## Implementation Steps

### Step 1: Create Migration Helper
```python
# shared/websocket_migration_helper.py
def migrate_to_factory_manager(user_context: UserExecutionContext):
    """Helper to ensure proper factory usage"""
    if not user_context:
        raise ValueError("UserExecutionContext required for WebSocket manager")
    return create_websocket_manager(user_context)
```

### Step 2: Update Each Service
For each service:
1. Remove global `get_websocket_manager()` imports
2. Import `create_websocket_manager`
3. Update all functions to accept `user_context`
4. Create manager using factory pattern
5. Update tests to mock factory pattern

### Step 3: Validation Tests
Create comprehensive tests to verify:
- No shared state between users
- Proper isolation of WebSocket events
- No data leakage across contexts
- Concurrent user handling

## Critical Success Criteria

### Must Have
1. ✅ All 9 services migrated to factory pattern
2. ✅ No global WebSocket manager instances
3. ✅ UserExecutionContext passed to all WebSocket operations
4. ✅ Zero cross-user event leakage
5. ✅ All existing tests passing with factory pattern

### Security Validation
- Multi-user concurrent testing
- Event isolation verification
- Memory leak testing
- Race condition testing

## Risk Mitigation

### Potential Issues
1. **Breaking Changes**: Some APIs may need signature updates
2. **Test Updates**: All mocks need factory pattern updates
3. **Performance**: Per-request manager creation overhead

### Mitigation Strategy
1. Use backward compatibility wrappers during transition
2. Update tests incrementally per service
3. Implement manager pooling if performance issues arise

## Timeline

### Day 1 (Today)
- ✅ Analysis complete
- ⏳ Begin Phase 1 critical services
- ⏳ message_processing.py migration
- ⏳ message_handlers.py migration

### Day 2
- Phase 1 completion
- Phase 2 high priority services
- Integration testing

### Day 3
- Phase 3 support services
- Comprehensive testing
- Performance validation

## Success Metrics

1. **Security**: Zero cross-user data leakage incidents
2. **Performance**: < 5% overhead from factory pattern
3. **Stability**: All tests passing, no regressions
4. **Coverage**: 100% of WebSocket operations use factory pattern

## Next Immediate Action
Begin migration of `message_processing.py` as the most critical service handling all user messages.