# Run ID Session Behavior - Complete Guide

**Date:** 2025-01-08  
**Context:** Session management improvements for conversation continuity  
**Cross-links:** [Context Factory vs Getter Analysis](./CONTEXT_FACTORY_VS_GETTER_ANALYSIS.md), [SSOT UUID Remediation](../ssot/SSOT_UUID_REMEDIATION_COMPLETE_REPORT.md)

## Run ID Session Logic

The `run_id` parameter in session management determines conversation flow behavior. Understanding this logic is crucial for proper multi-turn agent conversations.

### Session Behavior Matrix

| Scenario | `thread_id` | `run_id` | Behavior | Use Case |
|----------|-------------|----------|----------|----------|
| **New Conversation** | New | `None` | Create new session with generated run_id | User starts fresh conversation |
| **Continue Conversation** | Existing | `None` | Use existing session's run_id | User continues same conversation |
| **Same Agent Run** | Existing | Matches existing | Continue same run | Agent processes multiple messages in same execution |
| **New Agent Run** | Existing | Different from existing | Update session with new run_id | New agent execution in same conversation |
| **Explicit Run** | Any | Provided | Use provided run_id | Explicit run control (testing, debugging) |

### Implementation Details

```python
# In UnifiedIdGenerator.get_or_create_user_session()

if session_exists:
    if run_id is None:
        # Continue with existing run_id (conversation continuity)
        session_run_id = existing_session["run_id"]
    elif run_id == existing_session["run_id"]:
        # Same run - perfect continuity
        session_run_id = existing_session["run_id"] 
    else:
        # New run within same thread - new agent execution
        session_run_id = run_id
        existing_session["run_id"] = session_run_id  # Update session
else:
    # New session
    session_run_id = run_id or generate_base_id(f"run_{operation}")
```

### Conversation Flow Examples

#### Example 1: Normal Multi-Turn Conversation
```python
# Message 1: User starts conversation
context1 = get_user_execution_context("user123", "thread_456")
# Result: thread_456, run_abc123, req_def456

# Message 2: User continues conversation  
context2 = get_user_execution_context("user123", "thread_456")
# Result: thread_456, run_abc123 (SAME RUN), req_ghi789 (new request)

# ✅ CORRECT: Same run_id maintains conversation state
```

#### Example 2: New Agent Execution in Same Thread
```python
# User starts conversation
context1 = get_user_execution_context("user123", "thread_456") 
# Result: thread_456, run_abc123, req_def456

# New agent execution (different run)
context2 = get_user_execution_context("user123", "thread_456", "run_xyz789")
# Result: thread_456, run_xyz789 (NEW RUN), req_ghi012

# ✅ CORRECT: Different run_id for new agent execution while preserving thread
```

#### Example 3: Explicit Run ID Control
```python
# Testing/debugging with specific run_id
context = get_user_execution_context("user123", "thread_456", "test_run_001")
# Result: thread_456, test_run_001, req_abc123

# Same explicit run_id continues same execution
context2 = get_user_execution_context("user123", "thread_456", "test_run_001") 
# Result: thread_456, test_run_001, req_def456 (same run continues)

# ✅ CORRECT: Explicit control for testing scenarios
```

## Cross-Referenced Issues Found

### 1. Agent Handler Still Using `create_user_execution_context` ❌
**File:** `websocket_core/agent_handler.py`  
**Issue:** Multiple calls to deprecated `create_user_execution_context`  
**Impact:** Breaks conversation continuity  

**Lines to fix:**
- Line 102: `context = create_user_execution_context(...)`
- Line 196: `context = create_user_execution_context(...)`  
- Line 265: `user_context = create_user_execution_context(...)`
- Line 310: `context = create_user_execution_context(...)`
- Line 353: `context = create_user_execution_context(...)`

**Fix:**
```python
# OLD (WRONG):
context = create_user_execution_context(user_id, thread_id, run_id)

# NEW (CORRECT):  
context = get_user_execution_context(user_id, thread_id, run_id)
```

### 2. Quality Handlers Using Deprecated Function ❌
**Files:** All `services/websocket/quality_*.py` files  
**Issue:** Import and use `create_user_execution_context`  
**Impact:** Quality system doesn't maintain conversation state  

**Fix needed in:**
- `quality_validation_handler.py`
- `quality_alert_handler.py` 
- `quality_metrics_handler.py`
- `quality_report_handler.py`
- `quality_message_router.py`

### 3. Agent Service Core Using Factory Pattern ❌
**File:** `services/agent_service_core.py`  
**Issue:** Uses `create_user_execution_context_factory` which creates new contexts  
**Impact:** Stop/error handling breaks session continuity  

**Lines to fix:**
- Line 89: Stop agent context creation
- Line 103: Fallback context creation  
- Line 122: Error handling context creation
- Line 142: JSON error context creation
- Line 161: Exception context creation

### 4. Import Statement Updates Needed ❌
**Cross-linking issue:** Many files import deprecated function  

**Files needing import updates:**
```python
# OLD:
from netra_backend.app.dependencies import create_user_execution_context

# NEW: 
from netra_backend.app.dependencies import get_user_execution_context
```

## Migration Strategy

### Phase 1: Critical WebSocket Handlers (Immediate)
1. **Update agent_handler.py** - Replace all `create_user_execution_context` calls
2. **Test conversation continuity** - Verify multi-turn conversations work
3. **Update imports** - Change to `get_user_execution_context`

### Phase 2: Quality Management System (This Sprint)  
1. **Update all quality handlers** - Replace deprecated calls
2. **Test quality features** - Ensure quality monitoring maintains state
3. **Remove deprecated imports**

### Phase 3: Agent Service Layer (Next Sprint)
1. **Update agent_service_core.py** - Fix stop/error handling
2. **Test agent lifecycle** - Verify stop/error scenarios maintain context
3. **Cleanup factory functions** - Remove unused factory patterns

### Phase 4: System-Wide Cleanup (Future)
1. **Add deprecation warnings** - Make deprecated calls visible
2. **Remove deprecated functions** - Clean up technical debt
3. **Add monitoring** - Track session health and continuity

## Testing Requirements

```python
def test_run_id_session_continuity():
    """Test that run_id logic maintains proper session behavior."""
    user_id = "test_user"
    thread_id = "conversation_123"
    
    # Test 1: No run_id - should create new session
    context1 = get_user_execution_context(user_id, thread_id)
    original_run_id = context1.run_id
    
    # Test 2: No run_id again - should reuse same run_id  
    context2 = get_user_execution_context(user_id, thread_id)
    assert context2.run_id == original_run_id  # Same conversation
    
    # Test 3: Explicit new run_id - should create new run
    new_run_id = "explicit_run_456"
    context3 = get_user_execution_context(user_id, thread_id, new_run_id)
    assert context3.run_id == new_run_id  # New agent execution
    assert context3.thread_id == thread_id  # Same thread
    
    # Test 4: Same explicit run_id - should continue same run
    context4 = get_user_execution_context(user_id, thread_id, new_run_id) 
    assert context4.run_id == new_run_id  # Same run continues
    assert context4.thread_id == thread_id  # Same thread
```

## Business Impact

### Before (Broken):
- Every message creates new context
- Conversations lose state between messages  
- Users frustrated with repeated information requests
- Agents can't build on previous interactions

### After (Fixed):
- ✅ **Conversation Continuity** - Messages maintain context
- ✅ **Agent Memory** - Agents remember previous interactions  
- ✅ **User Experience** - Natural multi-turn conversations
- ✅ **Resource Efficiency** - Reuse contexts instead of creating new ones

## Monitoring & Observability

Add monitoring for session health:
```python
# Session metrics to track
session_count = UnifiedIdGenerator.get_active_sessions_count()
expired_cleaned = UnifiedIdGenerator.cleanup_expired_sessions(24)

# Log session behavior for debugging
logger.info(f"Session retrieved: user={user_id}, thread={thread_id}, run={run_id}, reused={was_existing}")
```

---

## Summary

The `run_id` parameter enables sophisticated session management that supports:
- **Conversation continuity** (no run_id or matching run_id)
- **New agent executions** (different run_id) 
- **Explicit control** (testing/debugging scenarios)

**Next Actions:**
1. Fix agent_handler.py imports and calls (CRITICAL)
2. Update quality management system  
3. Test multi-turn conversation flows
4. Add session monitoring and cleanup

This cross-links with the broader architectural fixes in context creation patterns and SSOT compliance initiatives.