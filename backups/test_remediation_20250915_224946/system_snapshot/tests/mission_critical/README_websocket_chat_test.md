# WebSocket Chat Flow Complete Test Suite

## 🎯 Purpose

This test suite validates the **MOST CRITICAL** functionality in Netra Apex - real-time WebSocket events during chat processing. This is our primary value delivery channel worth $500K+ ARR.

## 🚨 Business Impact

**If this test fails, users see a "blank screen" during AI processing**, leading to:
- User confusion and frustration
- Support tickets asking "Is it working?"
- Poor conversion from Free to Paid tiers
- High abandonment rates during agent processing

## 📋 The 7 Critical WebSocket Events

This test validates that ALL of these events are sent during chat processing:

1. **`agent_started`** - User sees agent began processing
2. **`agent_thinking`** - Real-time reasoning visibility  
3. **`tool_executing`** - Tool usage transparency
4. **`tool_completed`** - Tool results display
5. **`agent_completed`** - User knows when done
6. **`partial_result`** - Intermediate updates (valuable but optional)
7. **`error_event`** - Graceful error handling (when applicable)

## 🏃‍♂️ Quick Start

### Prerequisites

1. **Backend Service Running:**
   ```bash
   cd netra_backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Dependencies Installed:**
   ```bash
   pip install pytest websockets loguru
   ```

### Run the Critical Test

```bash
# Run just the main critical test
python tests/mission_critical/test_websocket_chat_flow_complete.py

# Or use pytest for detailed output
pytest tests/mission_critical/test_websocket_chat_flow_complete.py::TestWebSocketChatFlowComplete::test_chat_sends_all_seven_critical_events -v -s
```

### Run All WebSocket Chat Tests

```bash
# Run complete suite
pytest tests/mission_critical/test_websocket_chat_flow_complete.py -v

# Run with real-time output
pytest tests/mission_critical/test_websocket_chat_flow_complete.py -v -s --tb=short
```

## 🧪 Test Structure

### `TestWebSocketChatFlowComplete`

- **`test_chat_sends_all_seven_critical_events()`** - Main critical test
- **`test_concurrent_chats_isolated_events()`** - Multi-user isolation
- **`test_agent_failure_sends_error_events()`** - Error handling
- **`test_websocket_reconnection_preserves_flow()`** - Connection resilience
- **`test_websocket_event_timing_performance()`** - Performance validation

### `WebSocketEventCapture`

Rigorous event validation system that:
- Captures all WebSocket events with millisecond precision
- Validates event sequence and timing
- Ensures tool events are properly paired
- Generates detailed validation reports

### `WebSocketChatTester` 

Real WebSocket client that:
- Uses actual WebSocket connections (NO MOCKS)
- Simulates realistic user chat interactions
- Handles authentication and reconnection
- Provides detailed event capture and analysis

## 📊 Expected Output

### ✅ Successful Test Run

```
✅ WebSocket connected: chat-test-user-123
📤 Sent chat message: Analyze my system performance...
✅ Agent completion detected for chat-test-user-123

===============================================================================
WEBSOCKET EVENT VALIDATION REPORT - chat-test-user-123
===============================================================================
Status: ✅ PASSED
Total Events: 8
Event Types: 5
Duration: 12.456s

CRITICAL EVENT COVERAGE:
  ✅ agent_started: 1
  ✅ agent_thinking: 2
  ✅ tool_executing: 1
  ✅ tool_completed: 1
  ✅ agent_completed: 1

EVENT TIMELINE:
  0.123s: agent_started - Agent is starting to process your request
  0.456s: agent_thinking - I need to analyze the system performance...
  2.789s: tool_executing - Running performance analysis tool
  8.234s: tool_completed - Performance analysis complete
 12.456s: agent_completed - Analysis complete with recommendations

✅ CRITICAL TEST PASSED: All WebSocket events validated for chat flow
```

### ❌ Failed Test Run

```
❌ WEBSOCKET EVENT VALIDATION REPORT - chat-test-user-456
===============================================================================
Status: ❌ FAILED
Total Events: 3
Event Types: 2

CRITICAL EVENT COVERAGE:
  ✅ agent_started: 1
  ❌ agent_thinking: 0
  ❌ tool_executing: 0
  ❌ tool_completed: 0
  ✅ agent_completed: 1

FAILURES:
  ❌ CRITICAL: Missing required events: {'agent_thinking', 'tool_executing', 'tool_completed'}
  ❌ CRITICAL: Invalid event sequence
```

## 🔧 Troubleshooting

### Common Issues

1. **Backend Not Running**
   ```
   ❌ WebSocket connection failed: [Errno 61] Connect call failed
   ```
   **Solution:** Start the backend service first

2. **Missing Events**
   ```
   ❌ CRITICAL: Missing required events: {'tool_executing'}
   ```
   **Solution:** Check WebSocket integration in MessageHandlerService

3. **Authentication Errors**
   ```
   ❌ WebSocket authentication failed: Invalid token
   ```
   **Solution:** Ensure test JWT token handling is configured

### Debug Mode

Run with debug logging:
```bash
pytest tests/mission_critical/test_websocket_chat_flow_complete.py -v -s --log-cli-level=INFO
```

## 📈 Performance Benchmarks

Expected performance targets:
- **First Event:** < 2 seconds
- **Tool Events:** < 10 seconds per tool
- **Total Processing:** < 30 seconds
- **Concurrent Sessions:** 3+ without interference

## 🚀 Integration with CI/CD

Add to your pipeline:
```yaml
- name: Run Critical WebSocket Tests
  run: |
    # Start backend
    cd netra_backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    sleep 10
    
    # Run tests
    pytest tests/mission_critical/test_websocket_chat_flow_complete.py::TestWebSocketChatFlowComplete::test_chat_sends_all_seven_critical_events -v
    
    # Stop backend
    pkill -f uvicorn
```

## 📝 Test Customization

### Custom Event Types

Add to `WebSocketEventCapture.CRITICAL_EVENTS`:
```python
CRITICAL_EVENTS = {
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed",
    "custom_event"  # Add your event
}
```

### Custom Timeouts

Modify test timeouts:
```python
# Wait longer for completion
completion_success = await chat_tester.wait_for_agent_completion(timeout=60.0)

# Faster first event requirement  
assert first_event_time < 1.0, f"First event too slow: {first_event_time:.2f}s"
```

## 🎖️ Success Criteria

This test PASSES when:
- ✅ All 7 critical events are captured
- ✅ Events arrive in logical order
- ✅ Tool events are properly paired
- ✅ Events arrive within performance targets
- ✅ Multiple concurrent sessions work independently
- ✅ Error scenarios are handled gracefully

## 🆘 Getting Help

If tests consistently fail:

1. **Check the logs** - Look for WebSocket connection errors
2. **Verify backend health** - Ensure `/ws/health` endpoint responds
3. **Test WebSocket manually** - Use browser dev tools or wscat
4. **Review MessageHandlerService** - Ensure WebSocket manager is passed through
5. **Check agent registry** - Verify WebSocket enhancement is applied

---

**Remember: This test validates our core user experience. If it fails, users are seeing a broken product!**