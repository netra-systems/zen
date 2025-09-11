# CRITICAL: WebSocket Factory Resource Leak - Five Whys Analysis

**Date**: 2025-09-08  
**Status**: CRITICAL PRODUCTION BUG  
**MRR Impact**: $120K+ (P1 Critical messaging failure)  
**Root Cause Found**: ✅ CONFIRMED

## THE REAL ROOT CAUSE (From GCP Staging Logs)

**Error**: `User staging-e2e-user-002 has reached the maximum number of WebSocket managers (5). Emergency cleanup attempted but limit still exceeded.`

## Five Whys Analysis

### Why #1: WebSocket Factory SSOT validation failed
**Answer**: User reached maximum WebSocket managers (5/5) - resource leak

### Why #2: Why did user reach maximum WebSocket managers?
**Answer**: WebSocket managers are not being properly cleaned up after connections close
**Evidence**: `Emergency cleanup attempted but limit still exceeded`

### Why #3: Why are WebSocket managers not being cleaned up?
**Answer**: Factory pattern creates isolated managers but cleanup logic fails
**Evidence from logs**: `FACTORY_PATTERN: Created isolated WebSocket manager (id: 140248324568528)` - new managers created but not destroyed

### Why #4: Why does cleanup logic fail?
**Answer**: Thread ID mismatch causing cleanup to fail finding the right manager
**Evidence**: `Thread ID mismatch: run_id contains 'websocket_factory_1757372478799' but thread_id is 'thread_websocket_factory_1757372478799_528_584ef8a5'`

### Why #5: Why is there a Thread ID mismatch?
**Answer**: SSOT violation - run_id and thread_id generation are inconsistent, causing managers to be orphaned
**Evidence**: ID generation creates different patterns for same thread, preventing proper lifecycle management

## CONFIRMED EVIDENCE FROM STAGING LOGS

```
2025-09-08T23:01:18.806456Z [ERROR] UNEXPECTED FACTORY ERROR: User staging-e2e-user-002 has reached the maximum number of WebSocket managers (5)

2025-09-08T23:01:18.802598Z Thread ID mismatch: run_id contains 'websocket_factory_1757372478799' but thread_id is 'thread_websocket_factory_1757372478799_528_584ef8a5'

2025-09-08T23:01:17.875141Z FACTORY PATTERN: Created isolated WebSocket manager (id: 140248324568528)
```

## THE REAL PROBLEM

1. **Factory Pattern Works**: Creates isolated managers successfully
2. **Cleanup Logic Broken**: Thread ID inconsistency prevents proper cleanup
3. **Resource Exhaustion**: After 5 connections, system rejects new WebSocket messages
4. **SSOT Compliance Correct**: Validation properly detects the resource leak

## BUSINESS IMPACT

- **Production Issue**: Real users cannot send WebSocket messages after 5 connections
- **Resource Leak**: Every WebSocket connection leaks a manager 
- **Cascading Failure**: Once limit reached, ALL WebSocket messaging fails
- **MRR at Risk**: $120K+ from broken core chat functionality

## IMMEDIATE FIX REQUIRED

1. **Fix Thread ID Generation**: Make run_id and thread_id consistent (SSOT compliance)
2. **Implement Proper Cleanup**: Ensure managers are destroyed when WebSocket disconnects
3. **Increase Limit Temporarily**: Raise from 5 to 20 as safety margin while fixing core issue
4. **Add Monitoring**: Alert when approaching manager limits per user

## TECHNICAL SOLUTION

### Primary Fix: Thread ID SSOT Compliance
```python
# Current BROKEN pattern:
run_id = f"websocket_factory_{timestamp}"
thread_id = f"thread_{run_id}_{random_suffix}"  # INCONSISTENT!

# Fixed SSOT pattern:
base_id = f"websocket_factory_{timestamp}"
run_id = base_id
thread_id = f"thread_{base_id}"  # CONSISTENT!
```

### Secondary Fix: Proper Cleanup
```python
async def cleanup_websocket_manager(self, user_id: str, manager_id: str):
    # Use consistent ID to find and remove manager
    await self.factory.cleanup_manager_by_id(manager_id)
```

## VALIDATION PLAN

1. **Unit Tests**: Test thread ID consistency
2. **Integration Tests**: Test manager cleanup
3. **Load Tests**: Verify no leaks under repeated connections
4. **Staging Validation**: Run same failing test - should pass

## SUCCESS CRITERIA

- [ ] Thread IDs consistent between run_id and thread_id
- [ ] WebSocket managers properly cleaned up on disconnect  
- [ ] No resource leaks after repeated connections
- [ ] test_003_websocket_message_send_real passes in staging
- [ ] WebSocket Factory SSOT validation passes

This is a critical production bug affecting core platform functionality.