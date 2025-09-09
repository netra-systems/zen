"""Error Tracker - SSOT for Error Monitoring and Tracking

This module provides comprehensive error tracking and monitoring capabilities
following SSOT principles. It integrates with existing monitoring services
to provide a unified error tracking interface.

Business Value Justification (BVJ):
- Segment: Mid & Enterprise (error tracking and monitoring)
- Business Goal: Reduce MTTR by 40% through comprehensive error tracking
- Value Impact: Proactive error detection and resolution improves system reliability
- Strategic Impact: Enhanced error visibility supports premium service tiers

SSOT Compliance:
- Integrates with existing GCPErrorService as SSOT for error reporting
- Uses existing ErrorFormatter for consistent error formatting
- Provides unified interface for error tracking across all services
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.monitoring.gcp_error_service import GCPErrorService
from netra_backend.app.services.monitoring.error_formatter import ErrorFormatter
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    WEBSOCKET = "websocket"
    AGENT_EXECUTION = "agent_execution"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error tracking."""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    thread_id: Optional[str] = None
    service_name: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackedError:
    """Tracked error with full context."""
    error_id: str
    message: str
    error_type: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime
    context: ErrorContext
    stack_trace: Optional[str] = None
    count: int = 1
    first_occurrence: Optional[datetime] = None
    last_occurrence: Optional[datetime] = None
    resolution_status: str = "open"
    tags: List[str] = field(default_factory=list)


class ErrorTracker:
    """SSOT Error Tracker - comprehensive error monitoring and tracking.
    
    This class provides unified error tracking capabilities while using
    existing monitoring services as SSOT implementations.
    """
    
    def __init__(self):
        """Initialize ErrorTracker using SSOT pattern."""
        # Initialize GCP Error Service with fallback for testing
        try:
            from netra_backend.app.schemas.monitoring_schemas import GCPErrorServiceConfig
            config = GCPErrorServiceConfig()  # Use default config
            self._gcp_error_service = GCPErrorService(config)
        except Exception as e:
            logger.warning(f"Failed to initialize GCP Error Service: {e}")
            self._gcp_error_service = None
            
        self._error_formatter = ErrorFormatter()
        self._redis_client = None
        self._error_cache: Dict[str, TrackedError] = {}
        self._aggregation_window = 300  # 5 minutes
        logger.debug("ErrorTracker initialized using SSOT monitoring services")
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self._redis_client:
            self._redis_client = await redis_manager.get_client()
        return self._redis_client
    
    async def track_error(
        self,
        error: Union[Exception, str],
        context: Optional[ErrorContext] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        tags: Optional[List[str]] = None
    ) -> str:
        """Track an error with full context.
        
        Args:
            error: Exception object or error message string
            context: Error context information
            severity: Error severity level
            category: Error category for classification
            tags: Additional tags for error categorization
            
        Returns:
            Error ID for tracking
        """
        try:
            # Generate unique error ID
            error_id = str(uuid.uuid4())
            
            # Extract error information
            if isinstance(error, Exception):
                error_message = str(error)
                error_type = type(error).__name__
                stack_trace = self._extract_stack_trace(error)
            else:
                error_message = str(error)
                error_type = "StringError"
                stack_trace = None
            
            # Create tracked error
            tracked_error = TrackedError(
                error_id=error_id,
                message=error_message,
                error_type=error_type,
                severity=severity,
                category=category,
                timestamp=datetime.now(timezone.utc),
                context=context or ErrorContext(),
                stack_trace=stack_trace,
                first_occurrence=datetime.now(timezone.utc),
                last_occurrence=datetime.now(timezone.utc),
                tags=tags or []
            )
            
            # Store in cache for fast access
            self._error_cache[error_id] = tracked_error
            
            # Store in Redis for persistence
            await self._store_error_in_redis(tracked_error)
            
            # Report to GCP Error Service (SSOT) if available
            if self._gcp_error_service:
                await self._report_to_gcp_error_service(tracked_error)
            
            # Check for error patterns and aggregation
            await self._check_error_patterns(tracked_error)
            
            logger.info(f"Tracked error {error_id}: {error_message[:100]}")
            return error_id
            
        except Exception as e:
            logger.error(f"Failed to track error: {e}")
            # Return a fallback error ID so tracking doesn't break the main flow
            return f"fallback_{int(time.time())}"
    
    async def get_error(self, error_id: str) -> Optional[TrackedError]:
        """Get tracked error by ID.
        
        Args:
            error_id: Unique error identifier
            
        Returns:
            TrackedError object or None if not found
        """
        try:
            # Check cache first
            if error_id in self._error_cache:
                return self._error_cache[error_id]
            
            # Check Redis
            redis_client = await self._get_redis()
            error_data = await redis_client.get(f"error:{error_id}")
            
            if error_data:
                error_dict = json.loads(error_data)
                return self._dict_to_tracked_error(error_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get error {error_id}: {e}")
            return None
    
    async def get_errors_by_category(
        self,
        category: ErrorCategory,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TrackedError]:
        """Get errors filtered by category and time range.
        
        Args:
            category: Error category to filter by
            start_time: Start of time range (defaults to last 24 hours)
            end_time: End of time range (defaults to now)
            limit: Maximum number of errors to return
            
        Returns:
            List of TrackedError objects
        """
        try:
            if not start_time:
                start_time = datetime.now(timezone.utc) - timedelta(hours=24)
            if not end_time:
                end_time = datetime.now(timezone.utc)
            
            redis_client = await self._get_redis()
            
            # Get error IDs from Redis using pattern matching
            pattern = f"error:category:{category.value}:*"
            error_keys = await redis_client.keys(pattern)
            
            errors = []
            for key in error_keys[:limit]:
                error_data = await redis_client.get(key)
                if error_data:
                    error_dict = json.loads(error_data)
                    tracked_error = self._dict_to_tracked_error(error_dict)
                    
                    # Filter by time range
                    if start_time <= tracked_error.timestamp <= end_time:
                        errors.append(tracked_error)
            
            # Sort by timestamp descending
            errors.sort(key=lambda e: e.timestamp, reverse=True)
            return errors[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get errors by category {category}: {e}")
            return []
    
    async def get_error_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive error statistics.
        
        Args:
            start_time: Start of time range (defaults to last 24 hours)
            end_time: End of time range (defaults to now)
            
        Returns:
            Dictionary with error statistics
        """
        try:
            if not start_time:
                start_time = datetime.now(timezone.utc) - timedelta(hours=24)
            if not end_time:
                end_time = datetime.now(timezone.utc)
            
            redis_client = await self._get_redis()
            
            # Get all error keys
            error_keys = await redis_client.keys("error:*")
            
            # Initialize statistics
            stats = {
                "total_errors": 0,
                "errors_by_severity": {severity.value: 0 for severity in ErrorSeverity},
                "errors_by_category": {category.value: 0 for category in ErrorCategory},
                "errors_by_hour": {},
                "top_error_types": {},
                "errors_by_service": {},
                "resolution_status": {
                    "open": 0,
                    "investigating": 0,
                    "resolved": 0
                }
            }
            
            # Analyze each error
            for key in error_keys:
                error_data = await redis_client.get(key)
                if error_data:
                    error_dict = json.loads(error_data)
                    timestamp = datetime.fromisoformat(error_dict["timestamp"].replace("Z", "+00:00"))
                    
                    # Filter by time range
                    if start_time <= timestamp <= end_time:
                        stats["total_errors"] += 1
                        
                        # Count by severity
                        severity = error_dict.get("severity", "medium")
                        stats["errors_by_severity"][severity] = stats["errors_by_severity"].get(severity, 0) + 1
                        
                        # Count by category
                        category = error_dict.get("category", "unknown")
                        stats["errors_by_category"][category] = stats["errors_by_category"].get(category, 0) + 1
                        
                        # Count by hour
                        hour_key = timestamp.strftime("%Y-%m-%d %H:00")
                        stats["errors_by_hour"][hour_key] = stats["errors_by_hour"].get(hour_key, 0) + 1
                        
                        # Count by error type
                        error_type = error_dict.get("error_type", "Unknown")
                        stats["top_error_types"][error_type] = stats["top_error_types"].get(error_type, 0) + 1
                        
                        # Count by service
                        service_name = error_dict.get("context", {}).get("service_name", "unknown")
                        stats["errors_by_service"][service_name] = stats["errors_by_service"].get(service_name, 0) + 1
                        
                        # Count by resolution status
                        resolution_status = error_dict.get("resolution_status", "open")
                        stats["resolution_status"][resolution_status] = stats["resolution_status"].get(resolution_status, 0) + 1
            
            # Convert top error types to sorted list
            stats["top_error_types"] = sorted(
                stats["top_error_types"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Convert services to sorted list
            stats["errors_by_service"] = sorted(
                stats["errors_by_service"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get error statistics: {e}")
            return {
                "total_errors": 0,
                "error": str(e)
            }
    
    async def update_error_status(self, error_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update error resolution status.
        
        Args:
            error_id: Unique error identifier
            status: New resolution status (open, investigating, resolved)
            notes: Optional notes about the status change
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            tracked_error = await self.get_error(error_id)
            if not tracked_error:
                logger.warning(f"Error {error_id} not found for status update")
                return False
            
            # Update status
            tracked_error.resolution_status = status
            
            # Update in cache
            self._error_cache[error_id] = tracked_error
            
            # Update in Redis
            await self._store_error_in_redis(tracked_error)
            
            logger.info(f"Updated error {error_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update error status for {error_id}: {e}")
            return False
    
    async def aggregate_similar_errors(self, lookback_minutes: int = 60) -> Dict[str, List[str]]:
        """Aggregate similar errors within time window.
        
        Args:
            lookback_minutes: Time window for aggregation in minutes
            
        Returns:
            Dictionary mapping error signature to list of error IDs
        """
        try:
            lookback_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
            redis_client = await self._get_redis()
            
            # Get recent errors
            error_keys = await redis_client.keys("error:*")
            error_groups = {}
            
            for key in error_keys:
                error_data = await redis_client.get(key)
                if error_data:
                    error_dict = json.loads(error_data)
                    timestamp = datetime.fromisoformat(error_dict["timestamp"].replace("Z", "+00:00"))
                    
                    if timestamp >= lookback_time:
                        # Create error signature for grouping
                        signature = f"{error_dict['error_type']}:{error_dict['category']}:{error_dict['message'][:100]}"
                        
                        if signature not in error_groups:
                            error_groups[signature] = []
                        error_groups[signature].append(error_dict["error_id"])
            
            # Return only groups with multiple errors
            return {sig: ids for sig, ids in error_groups.items() if len(ids) > 1}
            
        except Exception as e:
            logger.error(f"Failed to aggregate similar errors: {e}")
            return {}
    
    async def cleanup_old_errors(self, retention_days: int = 30) -> int:
        """Clean up old errors beyond retention period.
        
        Args:
            retention_days: Number of days to retain errors
            
        Returns:
            Number of errors cleaned up
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
            redis_client = await self._get_redis()
            
            # Get all error keys
            error_keys = await redis_client.keys("error:*")
            cleaned_count = 0
            
            for key in error_keys:
                error_data = await redis_client.get(key)
                if error_data:
                    error_dict = json.loads(error_data)
                    timestamp = datetime.fromisoformat(error_dict["timestamp"].replace("Z", "+00:00"))
                    
                    if timestamp < cutoff_time:
                        await redis_client.delete(key)
                        error_id = error_dict["error_id"]
                        
                        # Remove from cache
                        self._error_cache.pop(error_id, None)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old errors")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old errors: {e}")
            return 0
    
    # Private helper methods
    
    def _extract_stack_trace(self, error: Exception) -> Optional[str]:
        """Extract stack trace from exception."""
        try:
            import traceback
            return traceback.format_exc()
        except Exception:
            return None
    
    async def _store_error_in_redis(self, tracked_error: TrackedError) -> None:
        """Store tracked error in Redis for persistence."""
        try:
            redis_client = await self._get_redis()
            
            # Convert to dictionary for JSON serialization
            error_dict = self._tracked_error_to_dict(tracked_error)
            
            # Store with multiple keys for efficient querying
            error_key = f"error:{tracked_error.error_id}"
            category_key = f"error:category:{tracked_error.category.value}:{tracked_error.error_id}"
            
            # Set expiration based on severity (critical errors kept longer)
            if tracked_error.severity == ErrorSeverity.CRITICAL:
                ttl = 90 * 24 * 3600  # 90 days
            elif tracked_error.severity == ErrorSeverity.HIGH:
                ttl = 60 * 24 * 3600  # 60 days
            else:
                ttl = 30 * 24 * 3600  # 30 days
            
            await redis_client.set(error_key, json.dumps(error_dict), ex=ttl)
            await redis_client.set(category_key, json.dumps(error_dict), ex=ttl)
            
        except Exception as e:
            logger.error(f"Failed to store error in Redis: {e}")
    
    async def _report_to_gcp_error_service(self, tracked_error: TrackedError) -> None:
        """Report error to GCP Error Service (SSOT)."""
        try:
            # Use existing GCP Error Service for SSOT compliance
            error_context = {
                "error_id": tracked_error.error_id,
                "severity": tracked_error.severity.value,
                "category": tracked_error.category.value,
                "user_id": tracked_error.context.user_id,
                "service_name": tracked_error.context.service_name or "error_tracker",
                "component": tracked_error.context.component,
                "operation": tracked_error.context.operation,
                "additional_context": tracked_error.context.additional_context
            }
            
            # Report using SSOT GCP Error Service
            await self._gcp_error_service.report_error(
                error_message=tracked_error.message,
                error_type=tracked_error.error_type,
                context=error_context,
                stack_trace=tracked_error.stack_trace
            )
            
        except Exception as e:
            logger.error(f"Failed to report error to GCP: {e}")
    
    async def _check_error_patterns(self, tracked_error: TrackedError) -> None:
        """Check for error patterns and potential incidents."""
        try:
            # Look for similar errors in the last 10 minutes
            lookback_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            redis_client = await self._get_redis()
            
            # Create pattern key
            pattern_key = f"pattern:{tracked_error.error_type}:{tracked_error.category.value}"
            
            # Increment error count for this pattern
            count = await redis_client.incr(pattern_key)
            await redis_client.expire(pattern_key, 600)  # 10 minute window
            
            # Alert thresholds based on severity
            thresholds = {
                ErrorSeverity.CRITICAL: 3,
                ErrorSeverity.HIGH: 5,
                ErrorSeverity.MEDIUM: 10,
                ErrorSeverity.LOW: 20
            }
            
            threshold = thresholds.get(tracked_error.severity, 10)
            
            if count >= threshold:
                logger.warning(f"Error pattern detected: {pattern_key} occurred {count} times in 10 minutes")
                # Could trigger incident creation or alerts here
                
        except Exception as e:
            logger.error(f"Failed to check error patterns: {e}")
    
    def _tracked_error_to_dict(self, tracked_error: TrackedError) -> Dict[str, Any]:
        """Convert TrackedError to dictionary for serialization."""
        return {
            "error_id": tracked_error.error_id,
            "message": tracked_error.message,
            "error_type": tracked_error.error_type,
            "severity": tracked_error.severity.value,
            "category": tracked_error.category.value,
            "timestamp": tracked_error.timestamp.isoformat(),
            "context": {
                "user_id": tracked_error.context.user_id,
                "request_id": tracked_error.context.request_id,
                "thread_id": tracked_error.context.thread_id,
                "service_name": tracked_error.context.service_name,
                "component": tracked_error.context.component,
                "operation": tracked_error.context.operation,
                "additional_context": tracked_error.context.additional_context
            },
            "stack_trace": tracked_error.stack_trace,
            "count": tracked_error.count,
            "first_occurrence": tracked_error.first_occurrence.isoformat() if tracked_error.first_occurrence else None,
            "last_occurrence": tracked_error.last_occurrence.isoformat() if tracked_error.last_occurrence else None,
            "resolution_status": tracked_error.resolution_status,
            "tags": tracked_error.tags
        }
    
    def _dict_to_tracked_error(self, error_dict: Dict[str, Any]) -> TrackedError:
        """Convert dictionary to TrackedError object."""
        context_dict = error_dict.get("context", {})
        context = ErrorContext(
            user_id=context_dict.get("user_id"),
            request_id=context_dict.get("request_id"),
            thread_id=context_dict.get("thread_id"),
            service_name=context_dict.get("service_name"),
            component=context_dict.get("component"),
            operation=context_dict.get("operation"),
            additional_context=context_dict.get("additional_context", {})
        )
        
        return TrackedError(
            error_id=error_dict["error_id"],
            message=error_dict["message"],
            error_type=error_dict["error_type"],
            severity=ErrorSeverity(error_dict["severity"]),
            category=ErrorCategory(error_dict["category"]),
            timestamp=datetime.fromisoformat(error_dict["timestamp"].replace("Z", "+00:00")),
            context=context,
            stack_trace=error_dict.get("stack_trace"),
            count=error_dict.get("count", 1),
            first_occurrence=datetime.fromisoformat(error_dict["first_occurrence"].replace("Z", "+00:00")) if error_dict.get("first_occurrence") else None,
            last_occurrence=datetime.fromisoformat(error_dict["last_occurrence"].replace("Z", "+00:00")) if error_dict.get("last_occurrence") else None,
            resolution_status=error_dict.get("resolution_status", "open"),
            tags=error_dict.get("tags", [])
        )


# Convenience functions for common use cases
async def track_error(
    error: Union[Exception, str],
    user_id: Optional[str] = None,
    service_name: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.UNKNOWN
) -> str:
    """Convenience function to track an error.
    
    Args:
        error: Exception object or error message
        user_id: Optional user ID for context
        service_name: Optional service name for context
        severity: Error severity level
        category: Error category
        
    Returns:
        Error ID for tracking
    """
    context = ErrorContext(
        user_id=user_id,
        service_name=service_name
    )
    
    tracker = ErrorTracker()
    return await tracker.track_error(error, context, severity, category)


__all__ = [
    'ErrorTracker',
    'ErrorSeverity',
    'ErrorCategory', 
    'ErrorContext',
    'TrackedError',
    'track_error'
]