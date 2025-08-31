# WebSocket JSON Requirements for Unified Handler

## MISSION CRITICAL: WebSocket JSON Analysis Results

This document outlines the specific JSON serialization requirements that any unified JSON handler MUST support for WebSocket functionality. These requirements are derived from analysis of the existing WebSocket code and are CRITICAL for maintaining chat functionality.

### Executive Summary

WebSocket functionality is the primary value delivery mechanism for Netra Apex (90% of user value), making JSON serialization absolutely critical. Any regression in WebSocket JSON handling will break the chat UI and user experience.

## Critical WebSocket Events (MUST WORK)

The following 5 WebSocket events are mission-critical and MUST serialize correctly:

### 1. `agent_started`
**Purpose**: User must see that agent execution has begun
**JSON Structure**:
```json
{
  "type": "agent_started",
  "payload": {
    "agent_name": "string",
    "run_id": "string", 
    "timestamp": "number (unix timestamp)"
  }
}
```

### 2. `agent_thinking`
**Purpose**: Real-time visibility into agent reasoning
**JSON Structure**:
```json
{
  "type": "agent_thinking",
  "payload": {
    "thought": "string",
    "agent_name": "string",
    "step_number": "number", 
    "total_steps": "number",
    "timestamp": "number"
  }
}
```

### 3. `tool_executing`
**Purpose**: Transparency into tool usage
**JSON Structure**:
```json
{
  "type": "tool_executing",
  "payload": {
    "tool_name": "string",
    "agent_name": "string",
    "timestamp": "number"
  }
}
```

### 4. `tool_completed`
**Purpose**: Display tool execution results
**JSON Structure**:
```json
{
  "type": "tool_completed",
  "payload": {
    "tool_name": "string",
    "agent_name": "string",
    "result": "object (can be complex nested structure)",
    "timestamp": "number"
  }
}
```

### 5. `agent_completed`
**Purpose**: User must know when agent execution is finished
**JSON Structure**:
```json
{
  "type": "agent_completed",
  "payload": {
    "agent_name": "string",
    "run_id": "string",
    "result": "object (can be complex nested structure)",
    "duration_ms": "number",
    "timestamp": "number"
  }
}
```

## Complex Object Serialization Requirements

### DeepAgentState Serialization
**Critical Requirement**: The `DeepAgentState` Pydantic model must serialize completely and correctly.

**Key Fields That Must Be Preserved**:
- `user_request`: string
- `run_id`: string  
- `step_count`: number
- `optimizations_result`: OptimizationsResult object
- `action_plan_result`: ActionPlanResult object
- `final_report`: string
- `messages`: array of message objects

**Sample Structure**:
```json
{
  "user_request": "Optimize our infrastructure costs",
  "run_id": "run-12345",
  "step_count": 5,
  "optimizations_result": {
    "optimization_type": "cost_optimization",
    "recommendations": ["Use reserved instances", "Implement auto-scaling"],
    "cost_savings": 1250.75,
    "performance_improvement": 15.5,
    "confidence_score": 0.92
  },
  "action_plan_result": {
    "action_plan_summary": "Implementation plan",
    "actions": [
      {"id": 1, "action": "Phase 1", "priority": "high"}
    ]
  },
  "final_report": "Analysis complete",
  "messages": [
    {"role": "user", "content": "Analyze costs"},
    {"role": "assistant", "content": "I'll analyze your costs"}
  ]
}
```

## Performance Requirements

### Synchronous Serialization
- **Requirement**: Simple messages must serialize in < 100ms
- **Requirement**: Complex DeepAgentState must serialize in < 2 seconds
- **Requirement**: Must not block the main thread

### Asynchronous Serialization  
- **Requirement**: Must complete within 5-second timeout
- **Requirement**: Must not block the event loop
- **Requirement**: Must use ThreadPoolExecutor for CPU-intensive operations
- **Requirement**: Timeout must return meaningful fallback response

### Concurrent Serialization
- **Requirement**: Must handle concurrent serialization safely
- **Requirement**: No data corruption between concurrent operations
- **Requirement**: Efficient resource utilization

## Error Recovery Requirements

### Serialization Failure Handling
- **MUST**: Never crash on serialization failure
- **MUST**: Provide fallback serialization for failed objects
- **MUST**: Return JSON-serializable error information
- **MUST**: Include debugging information in fallback

**Fallback Response Structure**:
```json
{
  "payload": "String representation of failed object",
  "type": "Object type name", 
  "serialization_error": "Description of what failed"
}
```

### Timeout Recovery
- **MUST**: Return timeout fallback within 5 seconds
- **MUST**: Include timeout information in response
- **MUST**: Increment timeout statistics

## Message Type Conversion Requirements

### Frontend Compatibility
WebSocket messages often need backend-to-frontend type conversion using `get_frontend_message_type()`:

**Examples**:
- `agent_status_update` → frontend equivalent
- `tool_execution_started` → frontend equivalent  
- `sub_agent_completed` → frontend equivalent

**Requirement**: All message dicts with `type` field must have type converted before serialization.

## Unicode and Special Character Requirements

### International Support
- **MUST**: Handle Unicode characters correctly (Chinese, Arabic, Cyrillic, etc.)
- **MUST**: Preserve emojis in JSON serialization
- **MUST**: Handle special characters (@, #, $, %, etc.)
- **MUST**: Support `ensure_ascii=False` option for optimal Unicode handling

### Example Content Types
```json
{
  "content": "Analysis complete! 🎉 Results: áéíóú ñ çÇ 中文 русский",
  "emojis": ["🚀", "💡", "⚡", "🌟"],
  "languages": ["English", "Español", "中文", "العربية"]
}
```

## DateTime Serialization Requirements

### Consistent Format
- **MUST**: Handle `datetime` objects in payloads
- **MUST**: Convert to JSON-compatible format (ISO string or Unix timestamp)
- **MUST**: Preserve timezone information where applicable

### Supported DateTime Formats
```json
{
  "timestamp": "datetime object → string or number",
  "created_at": "ISO string",
  "unix_timestamp": "number",
  "date_array": ["array of datetime objects"]
}
```

## Large Message Requirements

### Size Handling
- **MUST**: Handle messages up to 100KB without failure
- **MUST**: Serialize large nested structures efficiently
- **MUST**: Not cause memory issues during serialization

### Performance Expectations
- Large messages (100KB): < 5 seconds
- Very large messages (1MB): < 10 seconds
- Must be JSON-serializable regardless of size

## WebSocket Manager Integration Requirements

### Serialization Methods
The unified handler must support these WebSocket manager methods:

1. **`_serialize_message_safely(message)`** - Synchronous fallback serialization
2. **`_serialize_message_safely_async(message)`** - Async serialization with timeout
3. **Message type conversion** - Backend to frontend type mapping
4. **Error recovery** - Fallback serialization for failed objects

### Integration Points
- `send_to_thread()` method uses serialization internally
- `send_to_user()` method relies on serialization 
- `broadcast_to_all()` method needs serialization
- All WebSocket sending methods depend on JSON serialization

## Test Coverage Requirements

### Critical Test Categories
1. **All 5 critical events** must have serialization tests
2. **DeepAgentState serialization** with complex nested objects
3. **Performance tests** for sync/async serialization  
4. **Error recovery tests** with failing objects
5. **Unicode/special character tests** 
6. **Large message tests**
7. **Concurrent serialization tests**
8. **Timeout handling tests**

### Test Files Created
- `test_websocket_json_agent_events.py` - Core event serialization tests
- `test_websocket_unified_json_handler.py` - Unified handler specific tests  
- `test_websocket_json_performance.py` - Performance and timeout tests
- `test_websocket_json_requirements.py` - Requirements validation tests

## Risk Assessment

### Critical Risks
1. **Chat UI Breakage**: Any serialization failure breaks user experience
2. **Performance Regression**: Slow serialization makes chat unresponsive  
3. **Data Loss**: Incomplete serialization loses important information
4. **Memory Issues**: Large object serialization could cause memory problems

### Mitigation Strategies  
1. **Comprehensive Testing**: All requirements have corresponding tests
2. **Error Recovery**: Robust fallback serialization prevents crashes
3. **Performance Monitoring**: Timeout handling prevents blocking
4. **Type Safety**: Strong typing prevents serialization errors

## Implementation Recommendations

### For Unified JSON Handler
1. **Reuse existing logic**: Build on `WebSocketManager._serialize_message_safely*` methods
2. **Maintain compatibility**: Ensure all existing WebSocket functionality works
3. **Add monitoring**: Track serialization performance and errors
4. **Error reporting**: Provide detailed error information for debugging

### Testing Strategy
1. **Run all tests** before deploying unified handler
2. **Performance benchmarks** must meet current requirements
3. **Load testing** with realistic WebSocket message volumes  
4. **Regression testing** to ensure no functionality is broken

## Conclusion

WebSocket JSON serialization is MISSION CRITICAL for Netra Apex. The unified JSON handler must meet all requirements outlined in this document to maintain the chat functionality that delivers 90% of user value. Any deviation from these requirements risks breaking the core user experience.

The comprehensive test suite provides validation that these requirements are met and should be used to verify any unified JSON handler implementation.