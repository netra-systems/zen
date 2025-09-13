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
        
        # Handle known unpicklable types
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