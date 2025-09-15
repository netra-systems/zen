"""SerializationSanitizer: Pickle/JSON Serialization Safety Utility

This module provides utilities to sanitize objects for safe serialization,
preventing pickle module errors when caching agent execution results.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability & Performance  
- Value Impact: Prevents cache serialization failures that degrade performance
- Revenue Impact: Maintains $500K+ ARR by preventing agent pipeline errors

Issue #585 Remediation:
- Filter unpicklable objects (agent instances, closures, threads)
- Sanitize complex nested structures
- Preserve essential data while removing problematic references
- Enable proper Redis caching for performance optimization

Architecture:
- SerializableData: Clean data containers for agent results
- ObjectSanitizer: Deep object sanitization utilities  
- PickleValidator: Pre-validation before cache storage
- Result transformers: Clean result patterns for optimization agents
"""

import pickle
import json
import types
import inspect
import logging
import contextvars
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from copy import deepcopy

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Types that cannot be reliably pickled
UNPICKLABLE_TYPES = {
    # Function and method types
    types.FunctionType,
    types.MethodType,
    types.BuiltinFunctionType,
    types.BuiltinMethodType,
    types.LambdaType,

    # Code and frame types
    types.CodeType,
    types.FrameType,
    types.TracebackType,

    # Generator and coroutine types
    types.GeneratorType,
    types.CoroutineType,
    types.AsyncGeneratorType,

    # Module types
    types.ModuleType,

    # ContextVar types (Issue #1211)
    contextvars.ContextVar,
    contextvars.Token,
    contextvars.Context,
}

# Additional unpicklable patterns by name/module
UNPICKLABLE_PATTERNS = {
    # Thread-related
    'thread', 'threading', 'asyncio', 'concurrent',
    # Database connections
    'session', 'connection', 'pool', 'engine',
    # Agent instances (often contain unpicklable references)
    'agent', 'executor', 'dispatcher', 'manager',
    # WebSocket connections
    'websocket', 'socket', 'client', 'emitter',
    # File handles
    'file', 'io', '_io',
    # ContextVar patterns (Issue #1211)
    'contextvar', 'contextvars', '_contextvars',
    # Async context patterns
    'context', 'token', 'trace_context', 'logging_context',
}


@dataclass
class SerializableAgentResult:
    """Clean, serializable container for agent execution results.
    
    This replaces complex AgentExecutionResult objects that may contain
    unpicklable references (agent instances, WebSocket connections, etc.)
    with a clean data structure safe for Redis caching.
    """
    
    # Core execution metadata
    success: bool
    agent_name: str
    duration: float
    error: Optional[str] = None
    
    # Clean result data (primitives and serializable objects only)
    output_data: Optional[Dict[str, Any]] = None
    optimization_insights: Optional[List[Dict[str, Any]]] = None
    cost_analysis: Optional[Dict[str, Union[str, int, float]]] = None
    recommendations: Optional[List[str]] = None
    
    # Execution context (safe identifiers only)
    user_id: Optional[str] = None
    thread_id: Optional[str] = None 
    run_id: Optional[str] = None
    execution_timestamp: Optional[str] = None
    
    # Performance metrics
    execution_stats: Optional[Dict[str, Union[int, float]]] = None
    
    # Validation metadata
    sanitized_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    original_type: Optional[str] = None
    removed_fields: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_agent_result(cls, result: Any) -> 'SerializableAgentResult':
        """Create clean SerializableAgentResult from complex agent result.
        
        Args:
            result: Original agent execution result (may contain unpicklable objects)
            
        Returns:
            SerializableAgentResult: Clean, serializable result data
        """
        try:
            # Extract basic fields safely
            success = getattr(result, 'success', False) if hasattr(result, 'success') else bool(result)
            agent_name = getattr(result, 'agent_name', 'unknown_agent')
            duration = getattr(result, 'duration', 0.0)
            error = getattr(result, 'error', None)
            
            # Extract execution context safely
            user_id = getattr(result, 'user_id', None)
            thread_id = getattr(result, 'thread_id', None)
            run_id = getattr(result, 'run_id', None)
            
            # Extract timestamp
            execution_timestamp = None
            if hasattr(result, 'execution_timestamp'):
                ts = result.execution_timestamp
                if hasattr(ts, 'isoformat'):
                    execution_timestamp = ts.isoformat()
                elif isinstance(ts, str):
                    execution_timestamp = ts
            
            # Safely extract and sanitize data
            output_data = None
            if hasattr(result, 'data') and result.data:
                output_data = ObjectSanitizer.sanitize_object(result.data)
            
            # Extract metadata safely  
            metadata = getattr(result, 'metadata', {})
            if isinstance(metadata, dict):
                clean_metadata = ObjectSanitizer.sanitize_object(metadata)
                
                # Extract specific optimization data
                optimization_insights = clean_metadata.get('optimization_insights')
                cost_analysis = clean_metadata.get('cost_analysis')
                recommendations = clean_metadata.get('recommendations')
                execution_stats = clean_metadata.get('execution_stats')
            else:
                optimization_insights = None
                cost_analysis = None  
                recommendations = None
                execution_stats = None
            
            # Track what type was sanitized
            original_type = type(result).__name__
            
            return cls(
                success=success,
                agent_name=agent_name,
                duration=duration,
                error=error,
                output_data=output_data,
                optimization_insights=optimization_insights,
                cost_analysis=cost_analysis,
                recommendations=recommendations,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                execution_timestamp=execution_timestamp,
                execution_stats=execution_stats,
                original_type=original_type,
                removed_fields=[]  # Will be populated by sanitizer if needed
            )
            
        except Exception as e:
            logger.error(f"Error creating SerializableAgentResult from {type(result)}: {e}")
            # Return minimal safe result
            return cls(
                success=False,
                agent_name='unknown_agent',
                duration=0.0,
                error=f"Serialization error: {str(e)}",
                original_type=type(result).__name__ if result else 'None'
            )


class ObjectSanitizer:
    """Utilities for sanitizing objects to remove unpicklable references."""
    
    @staticmethod
    def is_picklable(obj: Any) -> bool:
        """Check if an object can be safely pickled.

        Args:
            obj: Object to check for pickle compatibility

        Returns:
            bool: True if object can be pickled, False otherwise
        """
        try:
            pickle.dumps(obj)
            return True
        except (pickle.PickleError, TypeError, AttributeError) as e:
            logger.debug(f"Object not picklable: {type(obj).__name__} - {str(e)[:100]}")
            return False

    @staticmethod
    def _is_context_var_object(obj: Any) -> bool:
        """Check if object is a ContextVar, Token, or Context object.

        Args:
            obj: Object to check for ContextVar types

        Returns:
            bool: True if object is a ContextVar-related type
        """
        obj_type = type(obj)

        # Direct type check
        if obj_type in {contextvars.ContextVar, contextvars.Token, contextvars.Context}:
            return True

        # Module check for _contextvars types
        module_name = getattr(obj_type, '__module__', '')
        if module_name == '_contextvars':
            return True

        # Check if it's a ContextVar by duck typing
        if hasattr(obj, 'get') and hasattr(obj, 'set') and hasattr(obj, 'name'):
            if 'ContextVar' in str(type(obj)):
                return True

        # Check if it's a Token by duck typing
        if hasattr(obj, 'var') and hasattr(obj, 'old_value'):
            if 'Token' in str(type(obj)):
                return True

        return False

    @staticmethod
    def _extract_context_var_data(obj: Any) -> Dict[str, Any]:
        """Extract safe data from ContextVar-related objects.

        Args:
            obj: ContextVar, Token, or Context object

        Returns:
            Dict containing safe representation of the object's data
        """
        try:
            obj_type = type(obj)

            # Handle ContextVar objects
            if isinstance(obj, contextvars.ContextVar) or 'ContextVar' in str(obj_type):
                # Extract default value safely
                default_value = getattr(obj, 'default', contextvars.Token.MISSING)
                if default_value is contextvars.Token.MISSING:
                    safe_default = '<MISSING>'
                elif ObjectSanitizer.is_picklable(default_value):
                    safe_default = default_value
                else:
                    safe_default = f"<unpicklable {type(default_value).__name__}>"

                data = {
                    'type': 'ContextVar',
                    'name': getattr(obj, 'name', 'unknown'),
                    'default': safe_default,
                    'class_name': obj_type.__name__
                }

                # Try to get current value safely
                try:
                    current_value = obj.get()
                    if ObjectSanitizer.is_picklable(current_value):
                        data['current_value'] = current_value
                    else:
                        data['current_value'] = f"<unpicklable {type(current_value).__name__}>"
                except LookupError:
                    data['current_value'] = "<not_set>"
                except Exception as e:
                    data['current_value'] = f"<error: {str(e)[:50]}>"

                return data

            # Handle Token objects
            if isinstance(obj, contextvars.Token) or 'Token' in str(obj_type):
                data = {
                    'type': 'ContextVar.Token',
                    'class_name': obj_type.__name__
                }

                # Extract token information safely
                if hasattr(obj, 'var'):
                    var = obj.var
                    if hasattr(var, 'name'):
                        data['var_name'] = var.name
                    else:
                        data['var_name'] = str(var)

                if hasattr(obj, 'old_value'):
                    old_value = obj.old_value
                    if old_value is contextvars.Token.MISSING:
                        data['old_value'] = '<MISSING>'
                    elif ObjectSanitizer.is_picklable(old_value):
                        data['old_value'] = old_value
                    else:
                        data['old_value'] = f"<unpicklable {type(old_value).__name__}>"

                return data

            # Handle Context objects
            if isinstance(obj, contextvars.Context) or 'Context' in str(obj_type):
                data = {
                    'type': 'Context',
                    'class_name': obj_type.__name__
                }

                # Try to extract context items safely
                try:
                    context_items = {}
                    for var, value in obj.items():
                        var_name = getattr(var, 'name', str(var))
                        if ObjectSanitizer.is_picklable(value):
                            context_items[var_name] = value
                        else:
                            context_items[var_name] = f"<unpicklable {type(value).__name__}>"
                    data['items'] = context_items
                except Exception as e:
                    data['items'] = f"<error extracting items: {str(e)[:50]}>"

                return data

            # Fallback for unknown ContextVar-related types
            return {
                'type': 'unknown_contextvar_type',
                'class_name': obj_type.__name__,
                'module': getattr(obj_type, '__module__', 'unknown'),
                'repr': str(obj)[:100]
            }

        except Exception as e:
            logger.debug(f"Error extracting ContextVar data: {e}")
            return {
                'type': 'contextvar_extraction_error',
                'error': str(e)[:100],
                'class_name': type(obj).__name__
            }

    @staticmethod
    def _extract_logging_context_data(obj: Any) -> Dict[str, Any]:
        """Extract safe data from LoggingContext objects.

        Args:
            obj: LoggingContext object

        Returns:
            Dict containing safe representation of logging context data
        """
        try:
            data = {
                'type': 'LoggingContext',
                'class_name': type(obj).__name__
            }

            # Extract context values using get_context() method if available
            if hasattr(obj, 'get_context'):
                try:
                    context_values = obj.get_context()
                    if isinstance(context_values, dict):
                        data['context_values'] = ObjectSanitizer.sanitize_object(context_values)
                    else:
                        data['context_values'] = str(context_values)
                except Exception as e:
                    data['context_values'] = f"<error: {str(e)[:50]}>"

            # Extract filtered context if available
            if hasattr(obj, 'get_filtered_context'):
                try:
                    filtered_context = obj.get_filtered_context()
                    data['filtered_context'] = ObjectSanitizer.sanitize_object(filtered_context)
                except Exception as e:
                    data['filtered_context'] = f"<error: {str(e)[:50]}>"

            # Extract individual context vars if directly accessible
            context_vars = ['request_id', 'user_id', 'trace_id']
            for var_name in context_vars:
                if hasattr(obj, f'{var_name}_context'):
                    try:
                        context_var = getattr(obj, f'{var_name}_context')
                        if ObjectSanitizer._is_context_var_object(context_var):
                            data[f'{var_name}_context'] = ObjectSanitizer._extract_context_var_data(context_var)
                        else:
                            data[f'{var_name}_context'] = str(context_var)
                    except Exception:
                        data[f'{var_name}_context'] = '<error>'

            return data

        except Exception as e:
            logger.debug(f"Error extracting LoggingContext data: {e}")
            return {
                'type': 'logging_context_extraction_error',
                'error': str(e)[:100],
                'class_name': type(obj).__name__
            }

    @staticmethod
    def _extract_execution_engine_factory_data(obj: Any) -> Dict[str, Any]:
        """Extract safe data from ExecutionEngineFactory objects.

        Args:
            obj: ExecutionEngineFactory object

        Returns:
            Dict containing safe representation of factory data
        """
        try:
            data = {
                'type': 'ExecutionEngineFactory',
                'class_name': type(obj).__name__
            }

            # Extract factory metrics if available
            if hasattr(obj, 'get_factory_metrics'):
                try:
                    metrics = obj.get_factory_metrics()
                    data['factory_metrics'] = ObjectSanitizer.sanitize_object(metrics)
                except Exception as e:
                    data['factory_metrics'] = f"<error: {str(e)[:50]}>"

            # Extract basic configuration if available
            config_attrs = ['_factory_metrics', 'factory_id', 'creation_time']
            for attr in config_attrs:
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        if ObjectSanitizer.is_picklable(value):
                            data[attr] = value
                        else:
                            data[attr] = ObjectSanitizer.sanitize_object(value)
                    except Exception:
                        data[attr] = '<error>'

            # Extract component references safely
            component_attrs = ['websocket_bridge', 'database_session_manager', 'redis_manager']
            for attr in component_attrs:
                if hasattr(obj, attr):
                    try:
                        component = getattr(obj, attr)
                        if component is not None:
                            # Just store type and basic info, not the full object
                            data[f'{attr}_type'] = type(component).__name__
                            if hasattr(component, 'user_id'):
                                data[f'{attr}_user_id'] = getattr(component, 'user_id', 'unknown')
                        else:
                            data[f'{attr}_type'] = 'None'
                    except Exception:
                        data[f'{attr}_type'] = '<error>'

            return data

        except Exception as e:
            logger.debug(f"Error extracting ExecutionEngineFactory data: {e}")
            return {
                'type': 'execution_engine_factory_extraction_error',
                'error': str(e)[:100],
                'class_name': type(obj).__name__
            }

    @staticmethod
    def _extract_unified_trace_context_data(obj: Any) -> Dict[str, Any]:
        """Extract safe data from UnifiedTraceContext objects.

        Args:
            obj: UnifiedTraceContext object

        Returns:
            Dict containing safe representation of trace context data
        """
        try:
            data = {
                'type': 'UnifiedTraceContext',
                'class_name': type(obj).__name__
            }

            # Extract basic trace identifiers
            id_attrs = ['request_id', 'user_id', 'trace_id', 'correlation_id', 'thread_id']
            for attr in id_attrs:
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        if isinstance(value, (str, int, float, bool, type(None))):
                            data[attr] = value
                        else:
                            data[attr] = str(value)
                    except Exception:
                        data[attr] = '<error>'

            # Extract websocket context if available
            if hasattr(obj, 'to_websocket_context'):
                try:
                    websocket_context = obj.to_websocket_context()
                    data['websocket_context'] = ObjectSanitizer.sanitize_object(websocket_context)
                except Exception as e:
                    data['websocket_context'] = f"<error: {str(e)[:50]}>"

            # Extract spans safely
            if hasattr(obj, 'spans'):
                try:
                    spans = getattr(obj, 'spans', [])
                    if isinstance(spans, list):
                        data['spans_count'] = len(spans)
                        # Extract just basic info from first few spans
                        span_summaries = []
                        for span in spans[:3]:  # Limit to first 3 spans
                            if hasattr(span, 'operation_name'):
                                span_summaries.append({
                                    'operation': getattr(span, 'operation_name', 'unknown'),
                                    'start_time': str(getattr(span, 'start_time', 'unknown')),
                                    'end_time': str(getattr(span, 'end_time', 'unknown'))
                                })
                        data['span_summaries'] = span_summaries
                    else:
                        data['spans_count'] = 0
                except Exception as e:
                    data['spans_info'] = f"<error: {str(e)[:50]}>"

            # Extract events safely
            if hasattr(obj, 'events'):
                try:
                    events = getattr(obj, 'events', [])
                    if isinstance(events, list):
                        data['events_count'] = len(events)
                        # Extract just event names
                        event_names = []
                        for event in events[:5]:  # Limit to first 5 events
                            if isinstance(event, dict) and 'event_name' in event:
                                event_names.append(event['event_name'])
                        data['recent_events'] = event_names
                    else:
                        data['events_count'] = 0
                except Exception as e:
                    data['events_info'] = f"<error: {str(e)[:50]}>"

            return data

        except Exception as e:
            logger.debug(f"Error extracting UnifiedTraceContext data: {e}")
            return {
                'type': 'unified_trace_context_extraction_error',
                'error': str(e)[:100],
                'class_name': type(obj).__name__
            }

    @staticmethod
    def _extract_user_execution_context_data(obj: Any) -> Dict[str, Any]:
        """Extract safe data from UserExecutionContext objects.

        Args:
            obj: UserExecutionContext object

        Returns:
            Dict containing safe representation of user execution context data
        """
        try:
            data = {
                'type': 'UserExecutionContext',
                'class_name': type(obj).__name__
            }

            # Extract basic user context attributes
            basic_attrs = ['user_id', 'thread_id', 'run_id', 'request_id', 'websocket_client_id', 'operation_depth', 'parent_request_id']
            for attr in basic_attrs:
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        if isinstance(value, (str, int, float, bool, type(None))):
                            data[attr] = value
                        else:
                            data[attr] = str(value)
                    except Exception:
                        data[attr] = '<error>'

            # Extract timestamps
            if hasattr(obj, 'created_at'):
                try:
                    created_at = getattr(obj, 'created_at')
                    if hasattr(created_at, 'isoformat'):
                        data['created_at'] = created_at.isoformat()
                    else:
                        data['created_at'] = str(created_at)
                except Exception:
                    data['created_at'] = '<error>'

            # Extract dictionaries safely
            dict_attrs = ['agent_context', 'audit_metadata']
            for attr in dict_attrs:
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        if isinstance(value, dict):
                            data[attr] = ObjectSanitizer.sanitize_object(value)
                        else:
                            data[attr] = str(value)
                    except Exception:
                        data[attr] = '<error>'

            # Extract trace context if present
            if hasattr(obj, 'trace_context'):
                try:
                    trace_context = getattr(obj, 'trace_context')
                    if trace_context is not None:
                        data['trace_context'] = ObjectSanitizer._extract_unified_trace_context_data(trace_context)
                    else:
                        data['trace_context'] = None
                except Exception:
                    data['trace_context'] = '<error>'

            return data

        except Exception as e:
            logger.debug(f"Error extracting UserExecutionContext data: {e}")
            return {
                'type': 'user_execution_context_extraction_error',
                'error': str(e)[:100],
                'class_name': type(obj).__name__
            }
    
    @staticmethod
    def is_unpicklable_type(obj: Any) -> bool:
        """Check if object is of a known unpicklable type.

        Args:
            obj: Object to check

        Returns:
            bool: True if object is of an unpicklable type
        """
        obj_type = type(obj)

        # Check direct type match
        if obj_type in UNPICKLABLE_TYPES:
            return True

        # Check for ContextVar objects specifically (Issue #1211)
        if ObjectSanitizer._is_context_var_object(obj):
            return True

        # Check type name patterns
        type_name = obj_type.__name__.lower()
        module_name = getattr(obj_type, '__module__', '').lower()

        for pattern in UNPICKLABLE_PATTERNS:
            if pattern in type_name or pattern in module_name:
                return True

        # Check for specific problematic attributes
        if hasattr(obj, '__self__') and callable(obj):  # Bound methods
            return True

        if hasattr(obj, '__func__') and callable(obj):  # Unbound methods
            return True

        return False
    
    @staticmethod
    def get_safe_representation(obj: Any) -> Any:
        """Get a safe representation of an unpicklable object.
        
        Args:
            obj: Unpicklable object to represent
            
        Returns:
            Safe representation (string, dict, or primitive type)
        """
        try:
            # Handle ContextVar objects first (Issue #1211)
            if ObjectSanitizer._is_context_var_object(obj):
                return ObjectSanitizer._extract_context_var_data(obj)

            # Handle specific business objects (Issue #1211)
            obj_type_name = type(obj).__name__

            # LoggingContext objects
            if 'LoggingContext' in obj_type_name:
                return ObjectSanitizer._extract_logging_context_data(obj)

            # ExecutionEngineFactory objects
            if 'ExecutionEngineFactory' in obj_type_name:
                return ObjectSanitizer._extract_execution_engine_factory_data(obj)

            # UnifiedTraceContext objects
            if 'UnifiedTraceContext' in obj_type_name or 'TraceContext' in obj_type_name:
                return ObjectSanitizer._extract_unified_trace_context_data(obj)

            # UserExecutionContext objects
            if 'UserExecutionContext' in obj_type_name:
                return ObjectSanitizer._extract_user_execution_context_data(obj)

            # For agent instances, extract key information
            if hasattr(obj, 'agent_name'):
                return {
                    'type': 'agent_reference',
                    'agent_name': getattr(obj, 'agent_name', 'unknown'),
                    'class_name': type(obj).__name__
                }

            # For callable objects
            if callable(obj):
                return {
                    'type': 'callable_reference',
                    'name': getattr(obj, '__name__', 'unknown'),
                    'class_name': type(obj).__name__,
                    'module': getattr(obj, '__module__', 'unknown')
                }
            
            # For complex objects with __dict__
            if hasattr(obj, '__dict__'):
                safe_attrs = {}
                for key, value in obj.__dict__.items():
                    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        safe_attrs[key] = value
                    elif ObjectSanitizer._is_context_var_object(value):
                        # Extract ContextVar data instead of just marking as unpicklable
                        safe_attrs[key] = ObjectSanitizer._extract_context_var_data(value)
                    elif ObjectSanitizer.is_picklable(value):
                        safe_attrs[key] = value
                    else:
                        safe_attrs[key] = f"<unpicklable {type(value).__name__}>"

                return {
                    'type': 'object_reference',
                    'class_name': type(obj).__name__,
                    'attributes': safe_attrs
                }
            
            # Default string representation
            return f"<{type(obj).__name__} object>"
            
        except Exception as e:
            return f"<{type(obj).__name__} - repr error: {str(e)[:50]}>"
    
    @staticmethod
    def sanitize_object(obj: Any, max_depth: int = 5, current_depth: int = 0) -> Any:
        """Recursively sanitize an object to remove unpicklable references.
        
        Args:
            obj: Object to sanitize
            max_depth: Maximum recursion depth to prevent infinite loops
            current_depth: Current recursion depth
            
        Returns:
            Sanitized object safe for pickling/JSON serialization
        """
        # Prevent infinite recursion
        if current_depth > max_depth:
            return f"<max_depth_reached: {type(obj).__name__}>"
        
        # Handle None and primitive types
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Check if already picklable (optimization)
        if current_depth < 2 and ObjectSanitizer.is_picklable(obj):
            return obj
        
        # Handle ContextVar objects specifically (Issue #1211)
        if ObjectSanitizer._is_context_var_object(obj):
            return ObjectSanitizer._extract_context_var_data(obj)

        # Handle other known unpicklable types
        if ObjectSanitizer.is_unpicklable_type(obj):
            return ObjectSanitizer.get_safe_representation(obj)
        
        # Handle collections
        if isinstance(obj, (list, tuple)):
            sanitized_items = []
            for item in obj:
                try:
                    sanitized_item = ObjectSanitizer.sanitize_object(
                        item, max_depth, current_depth + 1
                    )
                    sanitized_items.append(sanitized_item)
                except Exception as e:
                    logger.debug(f"Error sanitizing list item: {e}")
                    sanitized_items.append(f"<sanitization_error: {type(item).__name__}>")
            
            return sanitized_items if isinstance(obj, list) else tuple(sanitized_items)
        
        if isinstance(obj, dict):
            sanitized_dict = {}
            for key, value in obj.items():
                try:
                    # Sanitize key (usually string, but could be complex)
                    clean_key = ObjectSanitizer.sanitize_object(
                        key, max_depth, current_depth + 1
                    )
                    
                    # Sanitize value
                    clean_value = ObjectSanitizer.sanitize_object(
                        value, max_depth, current_depth + 1
                    )
                    
                    # Convert key to string if it's not a basic type
                    if not isinstance(clean_key, (str, int, float, bool)):
                        clean_key = str(clean_key)
                    
                    sanitized_dict[clean_key] = clean_value
                    
                except Exception as e:
                    logger.debug(f"Error sanitizing dict item {key}: {e}")
                    sanitized_dict[str(key)] = f"<sanitization_error: {type(value).__name__}>"
            
            return sanitized_dict
        
        # Handle set
        if isinstance(obj, set):
            sanitized_items = []
            for item in obj:
                try:
                    sanitized_item = ObjectSanitizer.sanitize_object(
                        item, max_depth, current_depth + 1
                    )
                    sanitized_items.append(sanitized_item)
                except Exception:
                    sanitized_items.append(f"<sanitization_error: {type(item).__name__}>")
            return sanitized_items  # Convert to list for JSON compatibility
        
        # Handle datetime objects
        if hasattr(obj, 'isoformat'):
            try:
                return obj.isoformat()
            except Exception:
                pass
        
        # Handle dataclass objects
        if hasattr(obj, '__dataclass_fields__'):
            try:
                return ObjectSanitizer.sanitize_object(
                    asdict(obj), max_depth, current_depth + 1
                )
            except Exception as e:
                logger.debug(f"Error converting dataclass to dict: {e}")
        
        # Handle objects with __dict__
        if hasattr(obj, '__dict__'):
            try:
                obj_dict = {
                    'class_name': type(obj).__name__,
                    'attributes': ObjectSanitizer.sanitize_object(
                        obj.__dict__, max_depth, current_depth + 1
                    )
                }
                return obj_dict
            except Exception as e:
                logger.debug(f"Error processing object __dict__: {e}")
        
        # Fallback: try to convert to string
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__} object>"


class PickleValidator:
    """Pre-validation utilities for pickle serialization."""
    
    @staticmethod
    def validate_for_caching(obj: Any) -> Tuple[bool, Optional[str]]:
        """Validate if an object is safe for Redis caching.
        
        Args:
            obj: Object to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Quick type check
            if ObjectSanitizer.is_unpicklable_type(obj):
                return False, f"Contains unpicklable type: {type(obj).__name__}"
            
            # Try actual pickle serialization
            if not ObjectSanitizer.is_picklable(obj):
                return False, "Object failed pickle serialization test"
            
            # Size check (Redis has memory limits)
            try:
                pickled_data = pickle.dumps(obj)
                size_mb = len(pickled_data) / (1024 * 1024)
                
                if size_mb > 50:  # 50MB limit for cache entries
                    return False, f"Object too large for caching: {size_mb:.2f}MB"
                    
            except Exception as e:
                return False, f"Error calculating size: {e}"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    @staticmethod
    def safe_pickle_dumps(obj: Any) -> Optional[bytes]:
        """Safely serialize object with automatic sanitization fallback.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Pickled bytes or None if serialization fails
        """
        try:
            # Try direct pickling first
            return pickle.dumps(obj)
        except Exception as e:
            logger.debug(f"Direct pickle failed: {e}, attempting sanitization")
            
            try:
                # Sanitize and try again
                sanitized_obj = ObjectSanitizer.sanitize_object(obj)
                return pickle.dumps(sanitized_obj)
            except Exception as sanitize_error:
                logger.error(f"Sanitization and pickle failed: {sanitize_error}")
                return None
    
    @staticmethod
    def safe_json_dumps(obj: Any) -> Optional[str]:
        """Safely serialize object to JSON with automatic sanitization fallback.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON string or None if serialization fails  
        """
        try:
            # Try direct JSON serialization first
            return json.dumps(obj, default=str)
        except Exception as e:
            logger.debug(f"Direct JSON failed: {e}, attempting sanitization")
            
            try:
                # Sanitize and try again
                sanitized_obj = ObjectSanitizer.sanitize_object(obj)
                return json.dumps(sanitized_obj, default=str)
            except Exception as sanitize_error:
                logger.error(f"Sanitization and JSON failed: {sanitize_error}")
                return None


# Utility functions for quick access
def sanitize_agent_result(result: Any) -> SerializableAgentResult:
    """Quick utility to create clean SerializableAgentResult.
    
    Args:
        result: Agent execution result to sanitize
        
    Returns:
        SerializableAgentResult: Clean, cacheable result
    """
    return SerializableAgentResult.from_agent_result(result)


def is_safe_for_caching(obj: Any) -> bool:
    """Quick check if object is safe for Redis caching.
    
    Args:
        obj: Object to check
        
    Returns:
        bool: True if safe for caching
    """
    is_valid, _ = PickleValidator.validate_for_caching(obj)
    return is_valid


def safe_serialize_for_cache(obj: Any) -> Optional[bytes]:
    """Quick serialization with automatic sanitization.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Pickled bytes or None if failed
    """
    return PickleValidator.safe_pickle_dumps(obj)


# Export public interface
__all__ = [
    'SerializableAgentResult',
    'ObjectSanitizer', 
    'PickleValidator',
    'sanitize_agent_result',
    'is_safe_for_caching',
    'safe_serialize_for_cache'
]