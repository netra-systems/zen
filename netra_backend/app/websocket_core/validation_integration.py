"""
WebSocket Event Validation Integration - Hooks for existing components

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Reliability & Chat Quality
- Value Impact: Seamless integration of validation framework with existing WebSocket components
- Strategic Impact: Zero-disruption deployment of validation with automatic fallback

Integration Points:
- WebSocketManager: Validates outgoing events
- WebSocketNotifier: Validates agent lifecycle events  
- AgentWebSocketBridge: Validates agent communication events
- UnifiedToolExecutionEngine: Validates tool execution events

Architecture: Wrapper pattern with validation injection, preserves existing APIs.
"""

import asyncio
import functools
import time
from typing import Any, Dict, List, Optional, Callable, Union
import inspect
from contextlib import asynccontextmanager

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.event_validation_framework import (
    EventValidationFramework,
    EventValidationLevel,
    ValidatedEvent,
    ValidationResult,
    get_event_validation_framework,
    validate_websocket_event
)

logger = central_logger.get_logger(__name__)


class WebSocketValidationWrapper:
    """Wrapper that adds validation to existing WebSocket components."""
    
    def __init__(self, wrapped_component: Any, validation_level: EventValidationLevel = EventValidationLevel.MODERATE):
        self.wrapped_component = wrapped_component
        self.validation_framework = get_event_validation_framework(validation_level)
        self.validation_enabled = True
        self.fallback_on_validation_failure = True
        
        # Track validation stats
        self.validation_stats = {
            'total_events': 0,
            'validated_events': 0,
            'validation_failures': 0,
            'bypassed_events': 0
        }
        
    def __getattr__(self, name):
        """Delegate all other attributes to wrapped component."""
        return getattr(self.wrapped_component, name)
    
    async def _validate_and_send(self, original_method: Callable, event_data: Dict[str, Any], 
                               context: Dict[str, Any] = None, *args, **kwargs) -> Any:
        """Validate event and call original method."""
        self.validation_stats['total_events'] += 1
        
        if not self.validation_enabled:
            self.validation_stats['bypassed_events'] += 1
            return await original_method(*args, **kwargs)
        
        try:
            # Extract context information
            context = context or {}
            if 'thread_id' not in context and args:
                # Try to extract thread_id from first argument if it looks like one
                if isinstance(args[0], str) and len(args[0]) > 10:
                    context['thread_id'] = args[0]
            
            # Validate the event
            validated_event = await self.validation_framework.validate_event(event_data, context)
            self.validation_stats['validated_events'] += 1
            
            # Check validation result
            if validated_event.validation_result == ValidationResult.CRITICAL:
                self.validation_stats['validation_failures'] += 1
                
                if self.fallback_on_validation_failure:
                    # Log but still send the event
                    logger.error(f"CRITICAL validation failure for {event_data.get('type', 'unknown')}: "
                               f"{validated_event.validation_errors}")
                    # Still call original method as fallback
                    return await original_method(*args, **kwargs)
                else:
                    # Block the event
                    logger.error(f"BLOCKED event due to critical validation failure: {validated_event.validation_errors}")
                    return False
            
            elif validated_event.validation_result in [ValidationResult.ERROR, ValidationResult.WARNING]:
                # Log warnings/errors but continue
                level = "ERROR" if validated_event.validation_result == ValidationResult.ERROR else "WARNING"
                logger.log(getattr(logger, level.lower()), 
                          f"{level} in event validation: {validated_event.validation_errors + validated_event.validation_warnings}")
            
            # Call original method
            return await original_method(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Validation wrapper error: {e}")
            self.validation_stats['validation_failures'] += 1
            
            # Fallback to original method on validation errors
            return await original_method(*args, **kwargs)


def create_websocket_manager_validator(websocket_manager, validation_level: EventValidationLevel = EventValidationLevel.MODERATE):
    """Create a validation-enhanced WebSocket manager."""
    
    class ValidatedWebSocketManager(WebSocketValidationWrapper):
        """WebSocket manager with integrated validation."""
        
        def __init__(self, manager, validation_level):
            super().__init__(manager, validation_level)
        
        async def send_to_thread(self, thread_id: str, message: Union[Dict[str, Any], str], **kwargs) -> bool:
            """Send message to thread with validation."""
            # Convert string messages to dict
            if isinstance(message, str):
                try:
                    import json
                    message = json.loads(message)
                except:
                    message = {"type": "raw_message", "content": message}
            
            # Ensure message has required fields
            if not isinstance(message, dict):
                message = {"type": "unknown", "payload": message}
            
            # Add metadata if missing
            if 'timestamp' not in message:
                message['timestamp'] = time.time()
            if 'thread_id' not in message:
                message['thread_id'] = thread_id
            
            context = {
                'thread_id': thread_id,
                'component': 'WebSocketManager',
                'method': 'send_to_thread'
            }
            
            return await self._validate_and_send(
                self.wrapped_component.send_to_thread,
                message,
                context,
                thread_id,
                message,
                **kwargs
            )
        
        async def broadcast(self, message: Dict[str, Any], room: str = None, **kwargs) -> bool:
            """Broadcast message with validation."""
            # Ensure message has required fields
            if 'timestamp' not in message:
                message['timestamp'] = time.time()
            if 'type' not in message:
                message['type'] = 'broadcast'
            
            context = {
                'thread_id': room or 'broadcast',
                'component': 'WebSocketManager',
                'method': 'broadcast'
            }
            
            return await self._validate_and_send(
                self.wrapped_component.broadcast,
                message,
                context,
                message,
                room,
                **kwargs
            )
    
    return ValidatedWebSocketManager(websocket_manager, validation_level)


def create_websocket_notifier_validator(websocket_notifier, validation_level: EventValidationLevel = EventValidationLevel.MODERATE):
    """Create a validation-enhanced WebSocket notifier."""
    
    class ValidatedWebSocketNotifier(WebSocketValidationWrapper):
        """WebSocket notifier with integrated validation."""
        
        def __init__(self, notifier, validation_level):
            super().__init__(notifier, validation_level)
        
        async def send_agent_started(self, context, *args, **kwargs) -> None:
            """Send agent started event with validation."""
            event_data = {
                'type': 'agent_started',
                'payload': {
                    'agent_name': context.agent_name,
                    'run_id': context.run_id,
                    'timestamp': time.time()
                },
                'thread_id': context.thread_id,
                'timestamp': time.time()
            }
            
            validation_context = {
                'thread_id': context.thread_id,
                'run_id': context.run_id,
                'component': 'WebSocketNotifier',
                'method': 'send_agent_started'
            }
            
            return await self._validate_and_send(
                self.wrapped_component.send_agent_started,
                event_data,
                validation_context,
                context,
                *args,
                **kwargs
            )
        
        async def send_agent_thinking(self, context, thought: str, *args, **kwargs) -> None:
            """Send agent thinking event with validation."""
            event_data = {
                'type': 'agent_thinking',
                'payload': {
                    'thought': thought,
                    'agent_name': context.agent_name,
                    'run_id': context.run_id,
                    'timestamp': time.time()
                },
                'thread_id': context.thread_id,
                'timestamp': time.time()
            }
            
            validation_context = {
                'thread_id': context.thread_id,
                'run_id': context.run_id,
                'component': 'WebSocketNotifier',
                'method': 'send_agent_thinking'
            }
            
            return await self._validate_and_send(
                self.wrapped_component.send_agent_thinking,
                event_data,
                validation_context,
                context,
                thought,
                *args,
                **kwargs
            )
        
        async def send_tool_executing(self, context, tool_name: str, *args, **kwargs) -> None:
            """Send tool executing event with validation."""
            event_data = {
                'type': 'tool_executing',
                'payload': {
                    'tool_name': tool_name,
                    'agent_name': context.agent_name,
                    'run_id': context.run_id,
                    'timestamp': time.time()
                },
                'thread_id': context.thread_id,
                'timestamp': time.time()
            }
            
            validation_context = {
                'thread_id': context.thread_id,
                'run_id': context.run_id,
                'component': 'WebSocketNotifier',
                'method': 'send_tool_executing'
            }
            
            return await self._validate_and_send(
                self.wrapped_component.send_tool_executing,
                event_data,
                validation_context,
                context,
                tool_name,
                *args,
                **kwargs
            )
        
        async def send_tool_completed(self, context, tool_name: str, result: dict = None, *args, **kwargs) -> None:
            """Send tool completed event with validation."""
            event_data = {
                'type': 'tool_completed',
                'payload': {
                    'tool_name': tool_name,
                    'agent_name': context.agent_name,
                    'run_id': context.run_id,
                    'result': result or {},
                    'timestamp': time.time()
                },
                'thread_id': context.thread_id,
                'timestamp': time.time()
            }
            
            validation_context = {
                'thread_id': context.thread_id,
                'run_id': context.run_id,
                'component': 'WebSocketNotifier',
                'method': 'send_tool_completed'
            }
            
            return await self._validate_and_send(
                self.wrapped_component.send_tool_completed,
                event_data,
                validation_context,
                context,
                tool_name,
                result,
                *args,
                **kwargs
            )
        
        async def send_agent_completed(self, context, result: dict = None, duration_ms: float = 0, *args, **kwargs) -> None:
            """Send agent completed event with validation."""
            event_data = {
                'type': 'agent_completed',
                'payload': {
                    'agent_name': context.agent_name,
                    'run_id': context.run_id,
                    'result': result or {},
                    'duration_ms': duration_ms,
                    'timestamp': time.time()
                },
                'thread_id': context.thread_id,
                'timestamp': time.time()
            }
            
            validation_context = {
                'thread_id': context.thread_id,
                'run_id': context.run_id,
                'component': 'WebSocketNotifier',
                'method': 'send_agent_completed'
            }
            
            return await self._validate_and_send(
                self.wrapped_component.send_agent_completed,
                event_data,
                validation_context,
                context,
                result,
                duration_ms,
                *args,
                **kwargs
            )
    
    return ValidatedWebSocketNotifier(websocket_notifier, validation_level)


def create_tool_execution_validator(tool_execution_engine, validation_level: EventValidationLevel = EventValidationLevel.MODERATE):
    """Create a validation-enhanced tool execution engine."""
    
    class ValidatedToolExecutionEngine(WebSocketValidationWrapper):
        """Tool execution engine with integrated validation."""
        
        def __init__(self, engine, validation_level):
            super().__init__(engine, validation_level)
        
        async def execute_tool(self, tool_input, context=None, *args, **kwargs):
            """Execute tool with validation of WebSocket events."""
            # Get tool name for validation context
            tool_name = getattr(tool_input, 'tool_name', 'unknown_tool')
            thread_id = getattr(context, 'thread_id', 'unknown') if context else 'unknown'
            run_id = getattr(context, 'run_id', None) if context else None
            
            # Validate tool_executing event (if WebSocket notifications are enabled)
            if hasattr(self.wrapped_component, 'websocket_bridge') and self.wrapped_component.websocket_bridge:
                tool_executing_event = {
                    'type': 'tool_executing',
                    'payload': {
                        'tool_name': tool_name,
                        'agent_name': getattr(context, 'agent_name', 'unknown') if context else 'unknown',
                        'timestamp': time.time()
                    },
                    'thread_id': thread_id,
                    'timestamp': time.time()
                }
                
                validation_context = {
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'component': 'ToolExecutionEngine',
                    'method': 'execute_tool_start'
                }
                
                # Validate but don't block execution
                try:
                    await self.validation_framework.validate_event(tool_executing_event, validation_context)
                except Exception as e:
                    logger.warning(f"Tool executing validation failed: {e}")
            
            # Execute the tool
            start_time = time.time()
            try:
                result = await self.wrapped_component.execute_tool(tool_input, context, *args, **kwargs)
                success = True
            except Exception as e:
                result = {'error': str(e), 'success': False}
                success = False
                raise
            finally:
                # Validate tool_completed event
                if hasattr(self.wrapped_component, 'websocket_bridge') and self.wrapped_component.websocket_bridge:
                    duration_ms = (time.time() - start_time) * 1000
                    tool_completed_event = {
                        'type': 'tool_completed',
                        'payload': {
                            'tool_name': tool_name,
                            'agent_name': getattr(context, 'agent_name', 'unknown') if context else 'unknown',
                            'result': result if success else {'error': 'Tool execution failed'},
                            'success': success,
                            'duration_ms': duration_ms,
                            'timestamp': time.time()
                        },
                        'thread_id': thread_id,
                        'timestamp': time.time()
                    }
                    
                    validation_context = {
                        'thread_id': thread_id,
                        'run_id': run_id,
                        'component': 'ToolExecutionEngine', 
                        'method': 'execute_tool_complete'
                    }
                    
                    try:
                        await self.validation_framework.validate_event(tool_completed_event, validation_context)
                    except Exception as e:
                        logger.warning(f"Tool completed validation failed: {e}")
            
            return result
    
    return ValidatedToolExecutionEngine(tool_execution_engine, validation_level)


# Integration utility functions

async def enhance_component_with_validation(component: Any, component_type: str = None, 
                                          validation_level: EventValidationLevel = EventValidationLevel.MODERATE) -> Any:
    """Enhance any WebSocket component with validation."""
    if component_type is None:
        component_type = type(component).__name__
    
    # Route to appropriate validator based on component type
    if 'WebSocketManager' in component_type:
        return create_websocket_manager_validator(component, validation_level)
    elif 'WebSocketNotifier' in component_type:
        return create_websocket_notifier_validator(component, validation_level)
    elif 'ToolExecutionEngine' in component_type or 'ToolDispatcher' in component_type:
        return create_tool_execution_validator(component, validation_level)
    else:
        # Generic wrapper for unknown component types
        logger.warning(f"Unknown component type {component_type}, using generic validation wrapper")
        return WebSocketValidationWrapper(component, validation_level)


def validation_decorator(event_type: str, validation_level: EventValidationLevel = EventValidationLevel.MODERATE):
    """Decorator to add validation to individual methods."""
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract context for validation
            context_info = {
                'component': func.__module__,
                'method': func.__name__,
                'event_type': event_type
            }
            
            # Try to extract thread_id from arguments
            if args and hasattr(args[1] if len(args) > 1 else None, 'thread_id'):
                context_info['thread_id'] = args[1].thread_id
            elif 'thread_id' in kwargs:
                context_info['thread_id'] = kwargs['thread_id']
            
            # Create event data for validation
            event_data = {
                'type': event_type,
                'timestamp': time.time(),
                'thread_id': context_info.get('thread_id', 'unknown'),
                'payload': {
                    'method': func.__name__,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
            }
            
            # Validate the event
            try:
                await validate_websocket_event(event_data, context_info)
            except Exception as e:
                logger.warning(f"Validation decorator failed for {func.__name__}: {e}")
            
            # Call original function
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run validation in background
            context_info = {
                'component': func.__module__,
                'method': func.__name__,
                'event_type': event_type
            }
            
            event_data = {
                'type': event_type,
                'timestamp': time.time(),
                'payload': {
                    'method': func.__name__,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
            }
            
            # Run validation in background (fire and forget)
            try:
                loop = asyncio.get_event_loop()
                asyncio.create_task(validate_websocket_event(event_data, context_info))
            except:
                pass  # Ignore if no event loop
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def validation_context(thread_id: str, run_id: str = None):
    """Context manager for validation with automatic sequence tracking."""
    framework = get_event_validation_framework()
    
    # Start sequence tracking
    sequence = framework.sequence_validator.start_sequence(thread_id, run_id)
    
    try:
        yield {
            'thread_id': thread_id,
            'run_id': run_id,
            'sequence': sequence,
            'validate_event': lambda event, ctx=None: framework.validate_event(event, {**(ctx or {}), 'thread_id': thread_id, 'run_id': run_id})
        }
    finally:
        # Generate final report
        status = framework.get_sequence_status(thread_id)
        if status:
            logger.info(f"Validation sequence completed for thread {thread_id}: {status}")


# Global validation hooks

def enable_global_validation(validation_level: EventValidationLevel = EventValidationLevel.MODERATE):
    """Enable global validation for all WebSocket components."""
    framework = get_event_validation_framework(validation_level)
    logger.info(f"Global WebSocket validation enabled at level: {validation_level}")
    return framework


def disable_global_validation():
    """Disable global validation."""
    global _framework_instance
    if _framework_instance:
        _framework_instance.validation_enabled = False
        logger.info("Global WebSocket validation disabled")


def get_validation_statistics() -> Dict[str, Any]:
    """Get comprehensive validation statistics."""
    framework = get_event_validation_framework()
    metrics = framework.get_performance_metrics()
    
    return {
        'performance_metrics': {
            'total_events': metrics.total_events,
            'successful_events': metrics.successful_events,
            'failed_events': metrics.failed_events,
            'average_latency_ms': metrics.average_latency_ms,
            'events_per_second': metrics.events_per_second,
            'sequence_completion_rate': metrics.sequence_completion_rate
        },
        'circuit_breaker': {
            'state': framework.circuit_breaker_state,
            'failure_count': framework.failure_count,
            'failure_threshold': framework.failure_threshold
        },
        'sequences': {
            'active': len(framework.sequence_validator.active_sequences),
            'completed': len(framework.sequence_validator.completed_sequences)
        },
        'validation_level': framework.validation_level
    }