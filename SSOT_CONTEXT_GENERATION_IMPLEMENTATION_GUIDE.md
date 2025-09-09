# SSOT Context Generation Implementation Guide

## Critical Issue: Thread_ID Inconsistency Root Cause

The WebSocket resource leak is fundamentally caused by **different thread_ids being generated for the same user context**, breaking cleanup operations. This guide provides step-by-step implementation to fix the SSOT violation.

## Current Problematic Pattern

### ❌ WRONG: Multiple Independent ID Generations
```python
# In WebSocketManagerFactory.py
thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
    user_id=user_id, operation="websocket_factory"
)
# Creates: thread_websocket_factory_1757372478799_528_584ef8a5

# In RequestScopedSessionFactory.py  
thread_id_2, _, _ = UnifiedIdGenerator.generate_user_context_ids(
    user_id=user_id, operation="session"  # DIFFERENT!
)
# Creates: thread_session_1757372479000_529_a1b2c3d4

# Result: DIFFERENT thread_ids for same user context!
```

### 🔍 Why This Breaks Cleanup
```python
# Manager stored with isolation key:
isolation_key_creation = f"{user_id}:thread_websocket_factory_1757372478799_528_584ef8a5"

# Cleanup attempts to find with different key:
isolation_key_cleanup = f"{user_id}:thread_session_1757372479000_529_a1b2c3d4"

# Lookup FAILS → Manager never cleaned up → Resource leak!
```

## Solution: Single Context Creation (SSOT Compliant)

### ✅ CORRECT: Single Source of Truth Pattern
```python
# Step 1: Single context creation at WebSocket entry point
def create_websocket_user_context(user_id: str, websocket_id: str = None) -> UserExecutionContext:
    """SSOT: Single context creation for all WebSocket operations"""
    thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
        user_id=user_id, 
        operation="websocket_session"  # CONSISTENT operation name
    )
    
    return UserExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id,
        websocket_connection_id=websocket_id or f"ws_{run_id}"
    )

# Step 2: Pass SAME context to ALL components
user_context = create_websocket_user_context(user_id, websocket_id)
ws_manager = await websocket_factory.create_manager(user_context)
db_session = await session_factory.create_session_from_context(user_context)
```

## Implementation Steps

### Step 1: Update UserExecutionContext with WebSocket Factory Method

**File**: `/netra_backend/app/services/user_execution_context.py`

```python
# Add to UserExecutionContext class:

@classmethod
def from_websocket_request(cls, 
                          user_id: str, 
                          websocket_id: Optional[str] = None,
                          additional_context: Optional[Dict[str, Any]] = None) -> 'UserExecutionContext':
    """
    SSOT: Create UserExecutionContext for WebSocket operations
    
    This is the SINGLE method that should be used to create contexts for
    WebSocket connections, ensuring consistent thread_id generation across
    all components.
    
    Args:
        user_id: The user identifier
        websocket_id: Optional WebSocket connection ID
        additional_context: Optional additional context data
        
    Returns:
        UserExecutionContext with consistent IDs for ALL WebSocket operations
    """
    from shared.id_generation.unified_id_generator import UnifiedIdGenerator
    
    # CRITICAL: Single call generates consistent ID set
    thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
        user_id=user_id,
        operation="websocket_session"  # CONSISTENT across all WebSocket ops
    )
    
    return cls(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id,
        websocket_connection_id=websocket_id or f"ws_conn_{run_id}",
        additional_context=additional_context or {}
    )
```

### Step 2: Update WebSocketManagerFactory

**File**: `/netra_backend/app/websocket_core/websocket_manager_factory.py`

```python
# Replace the problematic ID generation:

# BEFORE (lines ~98-101):
# thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
#     user_id=user_id,
#     operation="websocket_factory"
# )

# AFTER:
async def create_manager(self, user_context: Optional[UserExecutionContext] = None, 
                        user_id: Optional[str] = None,
                        websocket_id: Optional[str] = None) -> IsolatedWebSocketManager:
    """
    Create WebSocket manager with SSOT context generation
    
    Args:
        user_context: Pre-created context (preferred)
        user_id: User ID if context needs to be created
        websocket_id: WebSocket connection ID
        
    Returns:
        IsolatedWebSocketManager instance
    """
    # Use provided context OR create with SSOT method
    if user_context is None:
        if user_id is None:
            raise ValueError("Either user_context or user_id must be provided")
        user_context = UserExecutionContext.from_websocket_request(
            user_id=user_id,
            websocket_id=websocket_id
        )
    
    # Rest of the method remains the same, but uses consistent user_context
    logger.info(f"Creating WebSocket manager with consistent context: {user_context.thread_id}")
    
    # ... existing implementation
```

### Step 3: Update RequestScopedSessionFactory

**File**: `/netra_backend/app/database/request_scoped_session_factory.py`

```python
# Add method to use existing context instead of generating new IDs:

def create_session_from_context(self, user_context: UserExecutionContext) -> RequestScopedSession:
    """
    Create database session using existing UserExecutionContext
    
    This prevents the SSOT violation of generating new thread_ids
    when a valid context already exists.
    
    Args:
        user_context: Existing context with consistent IDs
        
    Returns:
        RequestScopedSession using the provided context
    """
    logger.info(f"Creating session from existing context: {user_context.thread_id}")
    
    session = RequestScopedSession(
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,  # USE EXISTING thread_id
        request_id=user_context.request_id,  # USE EXISTING request_id
        session=self._create_database_session()
    )
    
    self._register_session(session)
    return session

# Update existing create_session method to use SSOT when no context provided:
def create_session(self, user_id: str, operation: str = "database_session") -> RequestScopedSession:
    """Create session with SSOT ID generation (use only when no context exists)"""
    
    # Generate IDs using consistent operation naming
    thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
        user_id=user_id,
        operation=operation  # Keep for backward compatibility
    )
    
    # Create temporary context for consistency
    temp_context = UserExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id
    )
    
    return self.create_session_from_context(temp_context)
```

### Step 4: Update WebSocket Entry Points

**File**: `/netra_backend/app/core/websocket_message_handler.py` (or main WebSocket handler)

```python
# Update WebSocket connection establishment:

async def handle_websocket_connection(websocket: WebSocket, user_id: str):
    """Handle new WebSocket connection with SSOT context"""
    
    # CRITICAL: Create context ONCE at entry point
    user_context = UserExecutionContext.from_websocket_request(
        user_id=user_id,
        websocket_id=f"ws_{uuid.uuid4().hex[:8]}"
    )
    
    logger.info(f"WebSocket connection established with context: {user_context.thread_id}")
    
    try:
        # Pass SAME context to all components
        ws_manager = await websocket_manager_factory.create_manager(user_context)
        db_session = await session_factory.create_session_from_context(user_context)
        
        # Store context for cleanup operations
        websocket.user_context = user_context
        
        # Continue with connection handling...
        
    except Exception as e:
        logger.error(f"WebSocket connection failed for context {user_context.thread_id}: {e}")
        await websocket.close()

async def handle_websocket_disconnect(websocket: WebSocket):
    """Handle WebSocket disconnection with consistent context"""
    
    if hasattr(websocket, 'user_context'):
        user_context = websocket.user_context
        
        # Use SAME context for cleanup that was used for creation
        isolation_key = f"{user_context.user_id}:{user_context.thread_id}"
        await websocket_manager_factory.cleanup_manager(isolation_key)
        
        logger.info(f"WebSocket cleanup completed for context: {user_context.thread_id}")
```

### Step 5: Fix Isolation Key Generation

**File**: `/netra_backend/app/websocket_core/websocket_manager_factory.py`

```python
def _generate_isolation_key(self, user_context: UserExecutionContext) -> str:
    """
    Generate CONSISTENT isolation key for manager storage and retrieval
    
    CRITICAL: Always use thread_id for consistency, not connection_id fallbacks
    that may not exist during cleanup operations.
    """
    # ALWAYS use thread_id - it's guaranteed to exist and be consistent
    isolation_key = f"{user_context.user_id}:{user_context.thread_id}"
    
    logger.debug(f"Generated isolation key: {isolation_key}")
    return isolation_key

# Update cleanup methods to use same key generation:
async def cleanup_manager(self, isolation_key: str = None, user_context: UserExecutionContext = None):
    """Cleanup manager using consistent isolation key"""
    
    if isolation_key is None and user_context is not None:
        isolation_key = self._generate_isolation_key(user_context)
    
    logger.info(f"Cleaning up manager with key: {isolation_key}")
    # ... existing cleanup logic
```

## Testing the Fix

### Unit Test for Consistent ID Generation
```python
def test_consistent_thread_id_generation():
    """Verify SSOT context generation produces consistent IDs"""
    user_id = "test-user-123"
    
    # Create context using SSOT method
    context1 = UserExecutionContext.from_websocket_request(user_id)
    context2 = UserExecutionContext.from_websocket_request(user_id)
    
    # Different contexts should have different IDs (as expected)
    assert context1.thread_id != context2.thread_id
    
    # But within same context, thread_id and run_id should be consistent
    assert context1.run_id in context1.thread_id
    assert context2.run_id in context2.thread_id

def test_isolation_key_consistency():
    """Verify isolation keys are consistent for same context"""
    factory = WebSocketManagerFactory()
    context = UserExecutionContext.from_websocket_request("test-user")
    
    key1 = factory._generate_isolation_key(context)
    key2 = factory._generate_isolation_key(context)
    
    # Same context should generate identical isolation keys
    assert key1 == key2
    assert context.thread_id in key1
```

### Integration Test for Manager Lifecycle
```python
async def test_manager_creation_and_cleanup_with_ssot_context():
    """Test complete manager lifecycle with SSOT context"""
    factory = WebSocketManagerFactory()
    user_id = "integration-test-user"
    
    # Create context using SSOT method
    context = UserExecutionContext.from_websocket_request(user_id)
    
    # Create manager
    manager = await factory.create_manager(context)
    assert manager is not None
    
    # Verify manager is tracked
    manager_count = await factory.get_user_manager_count(user_id)
    assert manager_count == 1
    
    # Cleanup using SAME context
    isolation_key = factory._generate_isolation_key(context)
    await factory.cleanup_manager(isolation_key)
    
    # Verify cleanup succeeded
    final_count = await factory.get_user_manager_count(user_id)
    assert final_count == 0  # Should be 0 if cleanup worked
```

## Migration Strategy

### Phase 1: Add New Methods (Backward Compatible)
1. Add `UserExecutionContext.from_websocket_request()` method
2. Add `RequestScopedSessionFactory.create_session_from_context()` method
3. Update isolation key generation for consistency
4. Deploy and test - should not break existing functionality

### Phase 2: Update WebSocket Entry Points
1. Update main WebSocket handlers to use SSOT context creation
2. Modify WebSocketManagerFactory to prefer provided contexts
3. Add logging to track context usage patterns
4. Deploy with monitoring

### Phase 3: Remove Legacy Patterns
1. Remove old ID generation calls in WebSocket components
2. Add warnings for deprecated usage patterns
3. Update all tests to use new SSOT patterns
4. Final deployment with complete fix

## Success Validation

### Log Messages to Monitor
```bash
# GOOD: Should see consistent thread_ids
"Creating WebSocket manager with consistent context: thread_websocket_session_1757409218490_123_abc123"
"WebSocket cleanup completed for context: thread_websocket_session_1757409218490_123_abc123"

# BAD: Should NOT see thread_id mismatches
"Thread ID mismatch: run_id contains 'websocket_factory_123' but thread_id is 'thread_session_456'"
```

### Metrics to Track
1. **Thread ID Mismatch Errors**: Should drop to 0
2. **Manager Cleanup Success Rate**: Should reach >95%
3. **Emergency Cleanup Frequency**: Should decrease significantly
4. **Average Manager Count per User**: Should remain stable

This SSOT context generation fix addresses the fundamental architectural issue causing WebSocket resource leaks. By ensuring consistent thread_id generation across all components, cleanup operations can successfully find and remove managers, preventing resource accumulation.

---

**Implementation Priority**: CRITICAL  
**Estimated Implementation Time**: 4-6 hours  
**Risk Level**: LOW (Backward compatible approach)  
**Business Impact**: HIGH (Resolves chat service blocking issue)