"""Authentication Trace Logger - Enhanced Debug Logging for Auth Flows

This module provides comprehensive, structured logging for authentication-related operations
to enable 10x better debugging of auth failures, especially the 403 "Not authenticated" errors.

Business Value Justification (BVJ):
- Segment: Platform Security & Reliability (all tiers)
- Business Goal: Reduce authentication debugging time from hours to minutes  
- Value Impact: Enables rapid diagnosis of auth issues that block user access
- Strategic Impact: Foundation for reliable authentication across all services

Key Features:
1. Structured logging with correlation IDs for cross-service tracing
2. Authentication state tracking throughout the request lifecycle
3. Detailed error context with actionable debugging steps
4. Performance metrics for auth operations
5. Security-aware logging (no secrets in logs)
"""

import json
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
import time
import traceback

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class AuthTraceContext:
    """Comprehensive context for authentication trace logging."""
    user_id: str
    request_id: str
    correlation_id: str
    operation: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    auth_state: str = "unknown"
    session_info: Dict[str, Any] = field(default_factory=dict)
    error_context: Optional[Dict[str, Any]] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    debug_hints: List[str] = field(default_factory=list)


class AuthTraceLogger:
    """Enhanced authentication trace logger with structured context."""
    
    def __init__(self):
        self.operation_start_times: Dict[str, float] = {}
    
    def start_operation(self, 
                       user_id: str, 
                       request_id: str, 
                       correlation_id: str, 
                       operation: str,
                       additional_context: Optional[Dict[str, Any]] = None) -> AuthTraceContext:
        """Start tracking an authentication operation with comprehensive context.
        
        Args:
            user_id: User identifier (could be 'system' for service calls)
            request_id: Unique request identifier  
            correlation_id: Cross-service correlation identifier
            operation: Name of the authentication operation being performed
            additional_context: Additional context information
            
        Returns:
            AuthTraceContext: Context object for this operation
        """
        self.operation_start_times[request_id] = time.time()
        
        context = AuthTraceContext(
            user_id=user_id,
            request_id=request_id,
            correlation_id=correlation_id,
            operation=operation,
            auth_state="starting"
        )
        
        if additional_context:
            context.session_info.update(additional_context)
        
        # Add debugging hints based on user_id
        if user_id == "system":
            context.debug_hints.extend([
                "user_id='system' indicates service-to-service authentication",
                "Check SERVICE_SECRET and inter-service auth configuration",
                "Verify that service authentication middleware is properly configured"
            ])
        
        logger.info(
            f"🚀 AUTH_TRACE_START: {operation} for user_id='{user_id}' | "
            f"Request: {request_id} | Correlation: {correlation_id} | "
            f"Context: {asdict(context)}"
        )
        
        return context
    
    def log_success(self, context: AuthTraceContext, additional_info: Optional[Dict[str, Any]] = None):
        """Log successful authentication operation with performance metrics.
        
        Args:
            context: Authentication trace context
            additional_info: Additional information about the success
        """
        # Calculate operation duration
        if context.request_id in self.operation_start_times:
            duration = time.time() - self.operation_start_times[context.request_id]
            context.performance_metrics["duration_seconds"] = round(duration, 4)
            del self.operation_start_times[context.request_id]
        
        context.auth_state = "success"
        if additional_info:
            context.session_info.update(additional_info)
        
        logger.info(
            f"✅ AUTH_TRACE_SUCCESS: {context.operation} completed for user_id='{context.user_id}' | "
            f"Duration: {context.performance_metrics.get('duration_seconds', 'unknown')}s | "
            f"Request: {context.request_id} | Correlation: {context.correlation_id} | "
            f"Context: {asdict(context)}"
        )
        
        # Special logging for system user successes
        if context.user_id == "system":
            logger.info(
                f"🔧 SYSTEM_AUTH_SUCCESS: Service-to-service authentication succeeded for operation '{context.operation}' | "
                f"This indicates proper inter-service configuration | "
                f"Request: {context.request_id}"
            )
    
    def dump_all_context_safely(self, 
                               context: AuthTraceContext, 
                               error: Optional[Exception] = None,
                               additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Safely dump ALL available context and IDs with null checks.
        
        Args:
            context: Authentication trace context
            error: Optional exception
            additional_context: Additional context
            
        Returns:
            Comprehensive context dictionary with all available information
        """
        try:
            comprehensive_context = {
                # Core IDs and identifiers
                "ids": {
                    "user_id": getattr(context, 'user_id', None) or "unknown",
                    "request_id": getattr(context, 'request_id', None) or "unknown", 
                    "correlation_id": getattr(context, 'correlation_id', None) or "unknown",
                    "operation": getattr(context, 'operation', None) or "unknown",
                    "session_id": additional_context.get('session_id') if additional_context else None,
                    "thread_id": additional_context.get('thread_id') if additional_context else None,
                    "run_id": additional_context.get('run_id') if additional_context else None
                },
                
                # Timestamps and timing
                "timing": {
                    "timestamp": getattr(context, 'timestamp', None),
                    "timestamp_iso": getattr(context, 'timestamp', datetime.now(timezone.utc)).isoformat() if hasattr(context, 'timestamp') else datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": context.performance_metrics.get('duration_seconds') if hasattr(context, 'performance_metrics') and context.performance_metrics else None
                },
                
                # Authentication state
                "auth_state": {
                    "current_state": getattr(context, 'auth_state', None) or "unknown",
                    "user_type": "system" if (getattr(context, 'user_id', None) == "system") else "regular",
                    "is_service_call": (getattr(context, 'user_id', None) or "").startswith("system"),
                    "auth_indicators": self._extract_auth_indicators(context, error)
                },
                
                # Error information (if provided)
                "error_info": self._extract_error_info_safely(error) if error else None,
                
                # Session information
                "session_info": dict(getattr(context, 'session_info', {})) if hasattr(context, 'session_info') else {},
                
                # Performance metrics
                "performance": dict(getattr(context, 'performance_metrics', {})) if hasattr(context, 'performance_metrics') else {},
                
                # Debug hints
                "debug_hints": list(getattr(context, 'debug_hints', [])) if hasattr(context, 'debug_hints') else [],
                
                # Additional context if provided
                "additional": dict(additional_context) if additional_context else {},
                
                # System environment indicators
                "environment": {
                    "is_development": self._is_development_env(),
                    "is_staging": self._is_staging_env(),
                    "is_production": self._is_production_env()
                },
                
                # Request context (try to extract from various sources)
                "request_context": self._extract_request_context_safely(additional_context)
            }
            
            # Remove None values to clean up the output
            return self._clean_none_values(comprehensive_context)
            
        except Exception as dump_error:
            logger.warning(f"Failed to dump comprehensive context: {dump_error}")
            return {
                "context_dump_error": str(dump_error),
                "basic_user_id": getattr(context, 'user_id', None) if context else "no_context",
                "basic_operation": getattr(context, 'operation', None) if context else "no_context"
            }
    
    def _extract_auth_indicators(self, context: AuthTraceContext, error: Optional[Exception]) -> Dict[str, Any]:
        """Safely extract authentication indicators."""
        try:
            indicators = {}
            
            if error:
                error_str = str(error).lower()
                indicators.update({
                    "has_403_error": "403" in error_str,
                    "has_401_error": "401" in error_str,
                    "has_not_authenticated": "not authenticated" in error_str,
                    "has_permission_denied": "permission denied" in error_str or "access denied" in error_str,
                    "has_jwt_error": "jwt" in error_str or "token" in error_str,
                    "error_suggests_auth_failure": self._is_authentication_error(error)
                })
                
            user_id = getattr(context, 'user_id', None)
            if user_id:
                indicators.update({
                    "user_id_is_system": user_id == "system",
                    "user_id_starts_with_system": user_id.startswith("system"),
                    "user_id_length": len(user_id),
                    "user_id_pattern": user_id[:15] + "..." if len(user_id) > 15 else user_id
                })
                
            return indicators
            
        except Exception as e:
            return {"extraction_error": str(e)}
    
    def _extract_error_info_safely(self, error: Exception) -> Dict[str, Any]:
        """Safely extract error information."""
        try:
            return {
                "type": type(error).__name__,
                "message": str(error),
                "module": getattr(error, '__module__', None),
                "args": list(error.args) if hasattr(error, 'args') else [],
                "traceback_available": hasattr(error, '__traceback__') and error.__traceback__ is not None
            }
        except Exception:
            return {"error_extraction_failed": "Could not safely extract error info"}
    
    def _extract_request_context_safely(self, additional_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Safely extract request context information."""
        try:
            if not additional_context:
                return {}
                
            request_info = {}
            
            # Look for common request context keys
            context_keys = [
                'request_method', 'request_path', 'request_headers', 'user_agent',
                'remote_addr', 'request_size', 'response_status', 'function_name',
                'module_name', 'line_number', 'file_path'
            ]
            
            for key in context_keys:
                if key in additional_context:
                    request_info[key] = additional_context[key]
                    
            return request_info
            
        except Exception:
            return {"request_context_extraction_failed": True}
    
    def _is_development_env(self) -> bool:
        """Check if running in development environment."""
        try:
            import os
            env = os.getenv('ENVIRONMENT', '').lower()
            return env in ['development', 'dev', 'local']
        except Exception:
            return False
    
    def _is_staging_env(self) -> bool:
        """Check if running in staging environment."""
        try:
            import os
            env = os.getenv('ENVIRONMENT', '').lower()
            return env in ['staging', 'stage']
        except Exception:
            return False
    
    def _is_production_env(self) -> bool:
        """Check if running in production environment."""
        try:
            import os
            env = os.getenv('ENVIRONMENT', '').lower()
            return env in ['production', 'prod']
        except Exception:
            return False
    
    def _clean_none_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively clean None values from dictionary."""
        try:
            if isinstance(data, dict):
                cleaned = {}
                for k, v in data.items():
                    if v is not None:
                        if isinstance(v, dict):
                            cleaned_nested = self._clean_none_values(v)
                            if cleaned_nested:  # Only add if not empty
                                cleaned[k] = cleaned_nested
                        else:
                            cleaned[k] = v
                return cleaned
            else:
                return data
        except Exception:
            return data or {}
    
    def log_failure(self, 
                   context: AuthTraceContext, 
                   error: Exception, 
                   additional_context: Optional[Dict[str, Any]] = None):
        """Log authentication failure with comprehensive debugging context.
        
        Args:
            context: Authentication trace context
            error: Exception that caused the failure
            additional_context: Additional context about the failure
        """
        # Calculate operation duration safely
        try:
            if hasattr(context, 'request_id') and context.request_id and context.request_id in self.operation_start_times:
                duration = time.time() - self.operation_start_times[context.request_id]
                if not hasattr(context, 'performance_metrics'):
                    context.performance_metrics = {}
                context.performance_metrics["duration_seconds"] = round(duration, 4)
                del self.operation_start_times[context.request_id]
        except Exception as timing_error:
            logger.debug(f"Failed to calculate operation duration: {timing_error}")
        
        # Safely update auth state
        try:
            context.auth_state = "failed"
        except Exception:
            pass
            
        # Safely build error context
        try:
            if not hasattr(context, 'error_context'):
                context.error_context = {}
                
            context.error_context.update({
                "error_type": type(error).__name__ if error else "unknown",
                "error_message": str(error) if error else "no_error_provided",
                "is_auth_error": self._is_authentication_error(error) if error else False,
                "is_permission_error": self._is_permission_error(error) if error else False,
                "stack_trace": traceback.format_exc() if logger.isEnabledFor(10) and error else None
            })
            
            if additional_context:
                context.error_context.update(additional_context)
                
        except Exception as context_error:
            logger.warning(f"Failed to build error context: {context_error}")
        
        # Add specific debugging hints based on error type and user
        try:
            self._add_error_specific_hints(context, error)
        except Exception as hint_error:
            logger.warning(f"Failed to add debugging hints: {hint_error}")
        
        # COMPREHENSIVE CONTEXT DUMP - This is the key enhancement
        try:
            comprehensive_dump = self.dump_all_context_safely(context, error, additional_context)
            
            logger.error(
                f"❌ AUTH_TRACE_FAILURE: {getattr(context, 'operation', 'unknown')} failed for user_id='{getattr(context, 'user_id', 'unknown')}' | "
                f"Error: {error} | Duration: {context.performance_metrics.get('duration_seconds', 'unknown') if hasattr(context, 'performance_metrics') else 'unknown'}s | "
                f"Request: {getattr(context, 'request_id', 'unknown')} | Correlation: {getattr(context, 'correlation_id', 'unknown')} | "
                f"COMPREHENSIVE_CONTEXT_DUMP: {comprehensive_dump}"
            )
            
        except Exception as log_error:
            # Fallback logging if comprehensive dump fails
            logger.error(
                f"❌ AUTH_TRACE_FAILURE: Operation failed | Error: {error} | "
                f"Context dump failed: {log_error} | "
                f"Basic context: user_id={getattr(context, 'user_id', 'unknown')}, "
                f"operation={getattr(context, 'operation', 'unknown')}"
            )
        
        # Extra debugging for 403 "Not authenticated" errors with comprehensive context
        try:
            error_str = str(error) if error else ""
            if "403" in error_str and "Not authenticated" in error_str:
                comprehensive_dump = self.dump_all_context_safely(context, error, additional_context)
                
                logger.error(
                    f"🔴 CRITICAL_AUTH_FAILURE: 403 'Not authenticated' error detected! | "
                    f"User: '{getattr(context, 'user_id', 'unknown')}' | Operation: '{getattr(context, 'operation', 'unknown')}' | "
                    f"This is the exact error you're debugging! | "
                    f"Request: {getattr(context, 'request_id', 'unknown')} | Correlation: {getattr(context, 'correlation_id', 'unknown')} | "
                    f"ALL_CONTEXT_AND_IDS: {comprehensive_dump}"
                )
                
                if getattr(context, 'user_id', None) == "system":
                    logger.error(
                        f"🚨 SYSTEM_USER_AUTH_FAILURE: The 'system' user failed authentication! | "
                        f"This indicates a service-to-service authentication problem. | "
                        f"Check: SERVICE_SECRET, JWT_SECRET, authentication middleware, inter-service config | "
                        f"Request: {getattr(context, 'request_id', 'unknown')} | "
                        f"SYSTEM_USER_CONTEXT: {comprehensive_dump}"
                    )
        except Exception as critical_error:
            logger.error(
                f"🔴 CRITICAL_AUTH_FAILURE: 403 error detected but failed to log details: {critical_error} | "
                f"Original error: {error}"
            )
    
    def log_state_change(self, 
                        context: AuthTraceContext, 
                        new_state: str, 
                        details: Optional[Dict[str, Any]] = None):
        """Log authentication state changes during an operation.
        
        Args:
            context: Authentication trace context
            new_state: New authentication state
            details: Additional details about the state change
        """
        old_state = context.auth_state
        context.auth_state = new_state
        
        if details:
            context.session_info.update(details)
        
        logger.debug(
            f"🔄 AUTH_STATE_CHANGE: {context.operation} state changed from '{old_state}' to '{new_state}' | "
            f"User: '{context.user_id}' | Request: {context.request_id} | "
            f"Details: {details or 'none'}"
        )
    
    def _is_authentication_error(self, error: Exception) -> bool:
        """Check if error is authentication-related."""
        error_str = str(error).lower()
        auth_keywords = [
            "not authenticated", "authentication failed", "invalid token",
            "token expired", "unauthorized", "401", "403"
        ]
        return any(keyword in error_str for keyword in auth_keywords)
    
    def _is_permission_error(self, error: Exception) -> bool:
        """Check if error is permission-related."""
        error_str = str(error).lower()
        permission_keywords = [
            "permission denied", "access denied", "forbidden", 
            "insufficient privileges", "403"
        ]
        return any(keyword in error_str for keyword in permission_keywords)
    
    def _add_error_specific_hints(self, context: AuthTraceContext, error: Exception):
        """Add error-specific debugging hints to the context."""
        try:
            error_str = str(error).lower() if error else "unknown_error"
            
            if "403" in error_str and "not authenticated" in error_str:
                context.debug_hints.extend([
                    "403 'Not authenticated' suggests JWT validation failed",
                    "Check authentication middleware configuration",
                    "Verify JWT_SECRET consistency across services",
                    "Check if token is being passed correctly in headers",
                    "Verify token format and expiration",
                    "Look for authentication dependency injection issues",
                    "Check if auth middleware is processing requests properly"
                ])
            
            if context.user_id == "system" and self._is_authentication_error(error):
                context.debug_hints.extend([
                    "System user auth failure indicates service-to-service problem",
                    "Check SERVICE_SECRET environment variable",
                    "Verify inter-service authentication configuration",
                    "Check if service ID headers are being passed correctly",
                    "Review service authentication middleware setup",
                    "Validate that 'system' user has proper service permissions",
                    "Check if authentication bypass is needed for system operations"
                ])
            
            if "session" in context.operation.lower() and self._is_authentication_error(error):
                context.debug_hints.extend([
                    "Session-related auth failure may indicate database auth issues",
                    "Check if request-scoped session factory auth is configured",
                    "Verify database connection authentication",
                    "Check if session isolation is properly configured",
                    "Validate that session creation doesn't require user authentication",
                    "Check if database user has proper permissions"
                ])
                
            # Additional hints for specific error patterns
            if "not authenticated" in error_str:
                context.debug_hints.extend([
                    "'Not authenticated' often means missing or invalid JWT token",
                    "Check request headers for Authorization: Bearer <token>",
                    "Verify token hasn't expired or been revoked",
                    "Check if authentication middleware is enabled on this route"
                ])
                
        except Exception as hint_error:
            logger.warning(f"Failed to add error-specific hints: {hint_error}")
            context.debug_hints.append(f"Error hint generation failed: {hint_error}")


# Global instance for use across the application
auth_tracer = AuthTraceLogger()


# Utility functions for enhanced debugging
def log_authentication_context_dump(user_id: str, 
                                   request_id: str, 
                                   operation: str,
                                   error: Optional[Exception] = None,
                                   **additional_context):
    """Utility function to quickly dump authentication context for debugging.
    
    Args:
        user_id: User identifier
        request_id: Request identifier
        operation: Operation being performed
        error: Optional error that occurred
        **additional_context: Additional context to include
    """
    try:
        try:
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            correlation_id = UnifiedIdGenerator.generate_base_id("debug_corr")
        except ImportError:
            correlation_id = f"debug_{int(time.time())}"
        
        context = AuthTraceContext(
            user_id=user_id,
            request_id=request_id, 
            correlation_id=correlation_id,
            operation=operation
        )
        
        if error:
            auth_tracer.log_failure(context, error, additional_context)
        else:
            comprehensive_dump = auth_tracer.dump_all_context_safely(context, None, additional_context)
            logger.info(
                f"🔍 AUTH_CONTEXT_DUMP: {operation} for user '{user_id}' | "
                f"Request: {request_id} | Correlation: {correlation_id} | "
                f"FULL_CONTEXT: {comprehensive_dump}"
            )
            
    except Exception as dump_error:
        logger.error(
            f"Failed to dump authentication context: {dump_error} | "
            f"user_id={user_id}, operation={operation}, error={error}"
        )


def trace_auth_operation(user_id: str, 
                        request_id: str, 
                        correlation_id: str, 
                        operation: str):
    """Decorator for tracing authentication operations.
    
    Usage:
        @trace_auth_operation("user123", "req456", "corr789", "create_session")
        async def my_auth_function():
            # function implementation
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = auth_tracer.start_operation(user_id, request_id, correlation_id, operation)
            try:
                result = await func(*args, **kwargs)
                auth_tracer.log_success(context, {"result_type": type(result).__name__})
                return result
            except Exception as e:
                auth_tracer.log_failure(context, e, {"function_name": func.__name__})
                raise
        return wrapper
    return decorator