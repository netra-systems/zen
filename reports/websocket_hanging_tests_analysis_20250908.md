# WebSocket Hanging Tests Root Cause Analysis

## Issue Description
Unit tests for WebSocket functionality are reported to be hanging during test execution, causing the test suite to timeout.

## Investigation Findings

### 1. Individual Test Analysis
- **Individual WebSocket tests run successfully** when executed in isolation
- Tests in `test_websocket_notifier_unit.py`, `test_websocket_notifier_business_logic_comprehensive.py`, etc. complete within expected timeframes (1-8 seconds)
- No hanging detected in specific test files when run individually

### 2. Unified Test Runner Timeout
- **Unified test runner times out** when running WebSocket-related tests
- Timeout occurs during test collection/execution phase, not in specific test methods
- This suggests the hanging is in **test runner infrastructure**, not individual tests

### 3. Root Cause Analysis: Background Task Management

After analyzing the WebSocketNotifier code, I identified several potential hanging issues:

#### A. Queue Processor Background Task (Lines 1182-1212)
```python
async def _process_event_queue(self) -> None:
    """Background task to process queued events."""
    while not self._shutdown and self.event_queue:  # POTENTIAL HANGING POINT
        # ... processing logic
```

**Issue**: The background queue processor may not exit cleanly if:
- `self._shutdown` flag is not properly set
- Event queue processing creates infinite loops
- Exception handling prevents proper task termination

#### B. Task Cancellation Issues (Lines 1261-1267)
```python
if self._queue_processor_task and not self._queue_processor_task.done():
    self._queue_processor_task.cancel()
    try:
        await self._queue_processor_task
    except asyncio.CancelledError:
        pass
```

**Issue**: Improper task cancellation can leave tasks hanging, especially on Windows with `GetQueuedCompletionStatus` operations.

#### C. AsyncIO Lock Contention (Line 84, 1155)
```python
self._processing_lock = asyncio.Lock()
# ...
async with self._processing_lock:  # POTENTIAL DEADLOCK
```

**Issue**: Lock contention during test execution can cause deadlocks if:
- Multiple tests create WebSocketNotifier instances
- Exception handling doesn't release locks properly
- Test fixtures don't properly clean up async resources

### 4. Windows-Specific AsyncIO Issues

The user's system is Windows, which has known asyncio issues:
- `_overlapped.GetQueuedCompletionStatus` hanging (mentioned in the issue)
- Windows event loop cleanup problems
- Background task management differences from Unix systems

## Identified Fixes

### Fix 1: Improve Background Task Cleanup
```python
async def shutdown(self) -> None:
    """Shutdown with aggressive cleanup."""
    self._shutdown = True
    
    # Force queue processing to stop
    if self._queue_processor_task:
        if not self._queue_processor_task.done():
            self._queue_processor_task.cancel()
            try:
                # Use shorter timeout for Windows compatibility  
                await asyncio.wait_for(self._queue_processor_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass  # Expected on cancellation
```

### Fix 2: Test Fixture Improvements
Add proper async cleanup to test fixtures:
```python
@pytest.fixture
async def websocket_notifier(self, mock_websocket_manager):
    notifier = WebSocketNotifier(mock_websocket_manager)
    yield notifier
    # CRITICAL: Ensure cleanup
    await notifier.shutdown()
```

### Fix 3: Prevent Queue Processor Auto-Start in Tests
```python
# In tests, disable automatic background tasks
notifier._auto_start_queue_processor = False
```

## Recommended Actions

### 1. Immediate Fix: Add Async Fixture Cleanup
Update all WebSocket test fixtures to properly clean up async resources.

### 2. Background Task Control
Add test-mode flag to disable automatic background task creation during unit tests.

### 3. Windows-Specific Timeout Handling
Implement shorter timeouts and more aggressive cleanup for Windows environments.

### 4. Test Runner Investigation  
Investigate why unified test runner has collection/execution issues while individual tests pass.

## Business Impact
- **High**: Blocking CI/CD pipeline due to hanging unit tests
- **User Experience**: Developers cannot run full test suite
- **Development Velocity**: Slowed by unreliable test execution

## Next Steps
1. Implement async fixture cleanup fixes
2. Add test-mode controls to WebSocketNotifier
3. Test fixes with unified test runner
4. Document proper async testing patterns

## Files Requiring Updates
- `netra_backend/tests/unit/agents/supervisor/test_websocket_notifier_*.py`
- `netra_backend/app/agents/supervisor/websocket_notifier.py`
- Test fixture base classes