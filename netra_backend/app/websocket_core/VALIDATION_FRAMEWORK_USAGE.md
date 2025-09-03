# WebSocket Event Validation Framework Usage Guide

## Overview

The WebSocket Event Validation Framework provides comprehensive validation of the 5 critical WebSocket events required for substantive chat functionality:

1. **agent_started** - User sees agent began processing
2. **agent_thinking** - Real-time reasoning visibility  
3. **tool_executing** - Tool usage transparency
4. **tool_completed** - Tool results display
5. **agent_completed** - User knows response is ready

## Business Value

- **100% Event Delivery Validation**: Ensures no critical chat events are lost
- **Silent Failure Detection**: Identifies missing events that indicate system problems
- **Performance Monitoring**: Tracks event latency and delivery metrics
- **Error Recovery**: Circuit breaker and fallback mechanisms for reliability

## Quick Start

### 1. Enable Global Validation

```python
from netra_backend.app.websocket_core.validation_integration import enable_global_validation
from netra_backend.app.websocket_core.event_validation_framework import EventValidationLevel

# Enable validation at moderate level (recommended for production)
framework = enable_global_validation(EventValidationLevel.MODERATE)
```

### 2. Enhance Existing Components

```python
from netra_backend.app.websocket_core.validation_integration import (
    create_websocket_manager_validator,
    create_websocket_notifier_validator,
    create_tool_execution_validator
)

# Enhance WebSocket manager
validated_manager = create_websocket_manager_validator(
    websocket_manager, EventValidationLevel.MODERATE
)

# Enhance WebSocket notifier
validated_notifier = create_websocket_notifier_validator(
    websocket_notifier, EventValidationLevel.MODERATE
)

# Enhance tool execution engine
validated_engine = create_tool_execution_validator(
    tool_execution_engine, EventValidationLevel.MODERATE
)
```

### 3. Manual Event Validation

```python
from netra_backend.app.websocket_core.event_validation_framework import validate_websocket_event

# Validate individual events
event = {
    'type': 'agent_started',
    'payload': {
        'agent_name': 'test_agent',
        'run_id': 'run-123',
        'timestamp': time.time()
    },
    'thread_id': 'thread-123',
    'timestamp': time.time()
}

validated_event = await validate_websocket_event(event, {'thread_id': 'thread-123'})

if validated_event.validation_result == ValidationResult.VALID:
    print("Event is valid!")
else:
    print(f"Validation errors: {validated_event.validation_errors}")
```

## Validation Levels

### STRICT
- All validation rules must pass
- Blocks events with any validation failures
- Best for development and testing

### MODERATE (Recommended)
- Critical validations must pass
- Allows events with warnings to proceed
- Optimal balance for production

### PERMISSIVE
- Only blocks events with fatal errors
- Maximum compatibility with existing code
- Use when transitioning to validation

## Advanced Usage

### Validation Context Manager

```python
from netra_backend.app.websocket_core.validation_integration import validation_context

async with validation_context('thread-123', 'run-456') as ctx:
    # Validate events within context
    event = {'type': 'agent_started', 'payload': {...}}
    validated_event = await ctx['validate_event'](event)
    
    # Context automatically tracks sequence completion
```

### Custom Validation Callbacks

```python
async def on_validation_event(validated_event):
    if validated_event.validation_result == ValidationResult.ERROR:
        # Log to external monitoring system
        logger.error(f"Validation error: {validated_event.validation_errors}")

async def on_validation_error(validated_event):
    # Alert operations team
    alert_ops_team(validated_event)

framework = get_event_validation_framework()
framework.register_validation_callback(on_validation_event)
framework.register_error_callback(on_validation_error)
```

### Method Decoration

```python
from netra_backend.app.websocket_core.validation_integration import validation_decorator

class MyWebSocketHandler:
    @validation_decorator('agent_started', EventValidationLevel.MODERATE)
    async def handle_agent_started(self, context, message):
        # Method automatically validates events
        await self.websocket_manager.send_to_thread(
            context.thread_id, message
        )
```

## Event Validation Rules

### Agent Started Event
**Required Fields:**
- `agent_name`: Name of the agent
- `timestamp`: Event timestamp
- `thread_id`: Thread identifier
- `run_id`: Execution run identifier

**Validation:**
- All required fields must be present
- Timestamp must be reasonable (within 1 hour)
- Must be first event in sequence

### Agent Thinking Event  
**Required Fields:**
- `thought`: Reasoning text (minimum 5 characters)
- `agent_name`: Name of the agent
- `timestamp`: Event timestamp

**Validation:**
- Thought content cannot be empty
- Must contain meaningful reasoning text

### Tool Executing Event
**Required Fields:**
- `tool_name`: Name of tool being executed
- `agent_name`: Name of the agent
- `timestamp`: Event timestamp

**Optional Fields:**
- `parameters`: Tool parameters
- `tool_purpose`: Purpose description
- `estimated_duration_ms`: Expected duration

**Validation:**
- Tool name cannot be empty
- Must have matching tool_completed event

### Tool Completed Event
**Required Fields:**
- `tool_name`: Name of completed tool
- `agent_name`: Name of the agent  
- `timestamp`: Event timestamp

**Optional Fields:**
- `result`: Tool execution results
- `success`: Success/failure flag
- `duration_ms`: Actual execution duration

**Validation:**
- Must pair with tool_executing event
- Should indicate success/failure status

### Agent Completed Event
**Required Fields:**
- `agent_name`: Name of the agent
- `run_id`: Execution run identifier
- `timestamp`: Event timestamp

**Optional Fields:**
- `result`: Final results
- `duration_ms`: Total execution duration
- `final_status`: Final status
- `summary`: Execution summary

**Validation:**
- Must be final event in sequence
- Run ID must match sequence

## Sequence Validation

The framework validates complete event sequences:

### Valid Sequence Examples
1. Full sequence: `agent_started → agent_thinking → tool_executing → tool_completed → agent_completed`
2. No tools: `agent_started → agent_thinking → agent_completed`
3. No thinking: `agent_started → tool_executing → tool_completed → agent_completed`

### Sequence Constraints
- Must start with `agent_started`
- Must end with `agent_completed` or `agent_failed`
- Tool events must be properly paired
- Maximum gap between events: 30 seconds
- Maximum total sequence duration: 5 minutes

## Performance Monitoring

### Get Validation Statistics

```python
from netra_backend.app.websocket_core.validation_integration import get_validation_statistics

stats = get_validation_statistics()
print(f"Total events validated: {stats['performance_metrics']['total_events']}")
print(f"Average latency: {stats['performance_metrics']['average_latency_ms']:.2f}ms")
print(f"Success rate: {stats['performance_metrics']['successful_events'] / stats['performance_metrics']['total_events'] * 100:.1f}%")
```

### Performance Metrics
- **Total Events**: Number of events validated
- **Successful Events**: Events that passed validation
- **Failed Events**: Events that failed validation
- **Average Latency**: Average validation time
- **Events Per Second**: Validation throughput
- **Sequence Completion Rate**: Percentage of completed sequences

## Error Recovery

### Circuit Breaker
The framework includes a circuit breaker that:
- Opens after 10 consecutive failures
- Switches to bypass mode to prevent cascading failures
- Automatically recovers after 60 seconds
- Provides graceful degradation

### Silent Failure Detection

```python
framework = get_event_validation_framework()

# Check for missing events
failures = framework.detect_silent_failures('thread-123')
if failures:
    logger.error(f"Silent failures detected: {failures}")

# Get validation report
report = framework.generate_validation_report('thread-123')
if not report['sequence_status']['sequence_complete']:
    logger.warning("Incomplete event sequence detected")
```

## Event Replay and Debugging

### Event History

```python
# Get all events for a thread
history = framework.get_thread_history('thread-123')
for event in history:
    print(f"{event.timestamp}: {event.event_type} - {event.validation_result}")
```

### Event Replay

```python
# Replay events for analysis
start_time = time.time() - 3600  # Last hour
replayed_events = await framework.replay_events(
    'thread-123', start_time=start_time
)

for event in replayed_events:
    print(f"Replayed: {event.event_type} - {event.validation_errors}")
```

## Integration with Existing Code

### Drop-in Replacement
The validation framework is designed as a drop-in enhancement:

```python
# Original code
websocket_manager = WebSocketManager()
await websocket_manager.send_to_thread('thread-123', message)

# Enhanced with validation - same API
validated_manager = create_websocket_manager_validator(websocket_manager)
await validated_manager.send_to_thread('thread-123', message)  # Now validated!
```

### Fallback Behavior
- If validation fails, the original method is still called (configurable)
- No breaking changes to existing functionality
- Graceful degradation ensures reliability

## Best Practices

### Production Deployment
1. Start with `MODERATE` validation level
2. Monitor validation statistics for baselines
3. Set up alerting for validation failures
4. Use error callbacks for operational visibility

### Development
1. Use `STRICT` validation level for thorough testing
2. Add validation to integration tests
3. Check validation reports in CI/CD
4. Use event replay for debugging

### Performance
1. Validation adds ~1-5ms latency per event
2. Circuit breaker prevents performance degradation
3. Metrics collection is lightweight
4. Event buffer limits memory usage

## Troubleshooting

### Common Issues

**High Validation Failures**
```python
# Check validation statistics
stats = get_validation_statistics()
if stats['performance_metrics']['failed_events'] > 100:
    # Investigate validation errors
    report = framework.generate_validation_report()
    print(f"Circuit breaker state: {report['framework_status']['circuit_breaker_state']}")
```

**Missing Events**
```python
# Detect silent failures
failures = framework.detect_silent_failures('thread-123')
if 'missing required events' in str(failures):
    # Check if all required events are being sent
    sequence_status = framework.get_sequence_status('thread-123')
    print(f"Required events present: {sequence_status['required_events_present']}")
```

**Performance Issues**
```python
# Check validation latency
stats = get_validation_statistics()
if stats['performance_metrics']['average_latency_ms'] > 10:
    # Consider reducing validation level or optimizing
    print(f"High latency: {stats['performance_metrics']['average_latency_ms']:.2f}ms")
```

### Debug Logging
Enable debug logging to see detailed validation information:

```python
import logging
logging.getLogger('netra_backend.app.websocket_core.event_validation_framework').setLevel(logging.DEBUG)
```

## API Reference

### Classes
- `EventValidationFramework`: Main framework class
- `EventValidator`: Individual event validation
- `EventSequenceValidator`: Sequence-level validation
- `ValidatedEvent`: Container for validation results

### Functions
- `validate_websocket_event()`: Validate single event
- `get_event_validation_framework()`: Get framework instance
- `enable_global_validation()`: Enable global validation
- `get_validation_statistics()`: Get performance stats

### Integration
- `create_websocket_manager_validator()`: Enhance WebSocket manager
- `create_websocket_notifier_validator()`: Enhance notifier
- `create_tool_execution_validator()`: Enhance tool execution
- `enhance_component_with_validation()`: Generic enhancement
- `validation_decorator`: Method decoration
- `validation_context`: Context manager