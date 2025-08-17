"""
Metrics middleware helper functions.
Extracted from metrics_middleware.py to maintain 8-line function limits.
"""

import asyncio
import time
import traceback
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime, UTC

from app.logging_config import central_logger
from app.services.metrics.agent_metrics_models import FailureType

logger = central_logger.get_logger(__name__)


class AgentNameExtractor:
    """Functions to extract agent names from various contexts."""
    
    @staticmethod
    def extract_from_self_attribute(args: tuple) -> Optional[str]:
        """Extract agent name from self.name attribute."""
        if args and hasattr(args[0], 'name'):
            return args[0].name
        return None
    
    @staticmethod
    def extract_from_class_name(args: tuple) -> Optional[str]:
        """Extract agent name from class name."""
        if args and hasattr(args[0], '__class__'):
            return args[0].__class__.__name__
        return None
    
    @staticmethod
    def extract_from_kwargs(kwargs: dict, keys: List[str]) -> Optional[str]:
        """Extract agent name from kwargs using key list."""
        for key in keys:
            if key in kwargs:
                return str(kwargs[key])
        return None
    
    @staticmethod
    def extract_from_function_module(func: Callable) -> str:
        """Extract agent name from function module and name."""
        module_name = func.__module__.split('.')[-1] if func.__module__ else "unknown"
        return f"{module_name}_{func.__name__}"
    
    @staticmethod
    def get_default_kwargs_keys() -> List[str]:
        """Get default kwargs keys to search for agent name."""
        return ['agent_name', 'name', 'agent_id']


class OperationTypeDetector:
    """Functions to detect operation types from function names."""
    
    @staticmethod
    def detect_execution_type(func_name: str) -> bool:
        """Check if function is execution type."""
        execution_keywords = ['execute', 'run', 'process']
        return any(keyword in func_name.lower() for keyword in execution_keywords)
    
    @staticmethod
    def detect_validation_type(func_name: str) -> bool:
        """Check if function is validation type."""
        validation_keywords = ['validate', 'check']
        return any(keyword in func_name.lower() for keyword in validation_keywords)
    
    @staticmethod
    def detect_analysis_type(func_name: str) -> bool:
        """Check if function is analysis type."""
        analysis_keywords = ['analyze', 'compute', 'calculate']
        return any(keyword in func_name.lower() for keyword in analysis_keywords)
    
    @staticmethod
    def detect_data_retrieval_type(func_name: str) -> bool:
        """Check if function is data retrieval type."""
        retrieval_keywords = ['fetch', 'get', 'retrieve']
        return any(keyword in func_name.lower() for keyword in retrieval_keywords)
    
    @staticmethod
    def detect_notification_type(func_name: str) -> bool:
        """Check if function is notification type."""
        notification_keywords = ['send', 'notify', 'broadcast']
        return any(keyword in func_name.lower() for keyword in notification_keywords)


class FailureClassifier:
    """Functions to classify failure types from errors."""
    
    @staticmethod
    def is_timeout_error(error_type: str, message: str) -> bool:
        """Check if error is timeout related."""
        return "timeout" in error_type or "timeout" in message
    
    @staticmethod
    def is_validation_error(error_type: str, message: str) -> bool:
        """Check if error is validation related."""
        return "validation" in error_type or "validation" in message
    
    @staticmethod
    def is_websocket_error(error_type: str, message: str) -> bool:
        """Check if error is websocket related."""
        return "websocket" in error_type or "websocket" in message
    
    @staticmethod
    def is_resource_error(message: str) -> bool:
        """Check if error is resource related."""
        return "memory" in message or "resource" in message
    
    @staticmethod
    def is_dependency_error(message: str) -> bool:
        """Check if error is dependency related."""
        return "connection" in message or "network" in message


class PerformanceUtils:
    """Functions for performance monitoring."""
    
    @staticmethod
    def get_memory_usage_mb() -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except (ImportError, Exception):
            return 0.0
    
    @staticmethod
    def get_cpu_usage_percent() -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except (ImportError, Exception):
            return 0.0
    
    @staticmethod
    def calculate_execution_time_ms(start_time: float) -> float:
        """Calculate execution time in milliseconds."""
        return (time.time() - start_time) * 1000
    
    @staticmethod
    def calculate_memory_delta(memory_before: float, memory_after: float) -> float:
        """Calculate memory usage delta."""
        return max(0, memory_after - memory_before)
    
    @staticmethod
    def calculate_throughput(batch_size: int, execution_time_ms: float) -> float:
        """Calculate throughput in items per second."""
        if execution_time_ms <= 0:
            return 0
        return batch_size / (execution_time_ms / 1000)


class ErrorHandler:
    """Functions for error handling and logging."""
    
    @staticmethod
    def extract_error_info(error: Exception) -> tuple[str, str]:
        """Extract error type and message."""
        error_type = type(error).__name__
        error_message = str(error)
        return error_type, error_message
    
    @staticmethod
    def create_error_metadata(error_type: str, func: Callable) -> Dict[str, str]:
        """Create error metadata dictionary."""
        return {
            "error_type": error_type,
            "function_name": func.__name__,
            "traceback": traceback.format_exc()
        }
    
    @staticmethod
    def format_error_message(error_type: str, error_message: str) -> str:
        """Format error message for logging."""
        return f"{error_type}: {error_message}"
    
    @staticmethod
    def log_operation_error(operation_id: str, error_type: str, error_message: str) -> None:
        """Log operation error."""
        logger.error(f"Operation {operation_id} failed: {error_type}: {error_message}")
    
    @staticmethod
    def log_timeout_error(operation_id: str, timeout_seconds: float) -> None:
        """Log timeout error."""
        logger.warning(f"Operation {operation_id} timed out after {timeout_seconds}s")


class BatchResultProcessor:
    """Functions for processing batch operation results."""
    
    @staticmethod
    def count_list_results(result: List[Any]) -> tuple[int, int]:
        """Count successful and failed items from list result."""
        successful_items = len([r for r in result if r])
        failed_items = len(result) - successful_items
        return successful_items, failed_items
    
    @staticmethod
    def count_dict_results(result: Dict[str, Any]) -> tuple[int, int]:
        """Count successful and failed items from dict result."""
        successful_items = result.get('successful', 0)
        failed_items = result.get('failed', 0)
        return successful_items, failed_items
    
    @staticmethod
    def count_single_result(result: Any) -> tuple[int, int]:
        """Count successful and failed items from single result."""
        successful_items = 1 if result else 0
        failed_items = 1 if not result else 0
        return successful_items, failed_items
    
    @staticmethod
    def create_batch_metadata(
        batch_size: int, 
        successful_items: int, 
        failed_items: int, 
        execution_time_ms: float,
        throughput: float
    ) -> Dict[str, Union[int, float]]:
        """Create batch operation metadata."""
        return {
            "batch_size": batch_size,
            "successful_items": successful_items,
            "failed_items": failed_items,
            "execution_time_ms": execution_time_ms,
            "throughput_items_per_second": throughput
        }
    
    @staticmethod
    def create_batch_result(
        result: Any, 
        successful_items: int, 
        failed_items: int, 
        execution_time_ms: float
    ) -> Dict[str, Any]:
        """Create batch operation result."""
        return {
            "result": result,
            "successful_items": successful_items,
            "failed_items": failed_items,
            "execution_time_ms": execution_time_ms
        }


class OperationMetadataBuilder:
    """Functions for building operation metadata."""
    
    @staticmethod
    def create_start_metadata(func: Callable) -> Dict[str, Any]:
        """Create metadata for operation start."""
        return {
            "function_name": func.__name__,
            "module": func.__module__,
            "start_time": datetime.now(UTC)
        }
    
    @staticmethod
    def create_success_metadata(execution_time_ms: float, result: Any) -> Dict[str, Any]:
        """Create metadata for successful operation."""
        return {
            "execution_time_ms": execution_time_ms,
            "result_type": type(result).__name__ if result else "None"
        }
    
    @staticmethod
    def create_context_metadata() -> Dict[str, bool]:
        """Create metadata for context manager."""
        return {"context_manager": True}
    
    @staticmethod
    def create_batch_start_metadata(batch_size: int) -> Dict[str, Any]:
        """Create metadata for batch operation start."""
        return {
            "batch_size": batch_size,
            "start_time": datetime.now(UTC)
        }


class TimeoutHandler:
    """Functions for handling timeouts."""
    
    @staticmethod
    def convert_timeout_to_ms(timeout_seconds: float) -> float:
        """Convert timeout from seconds to milliseconds."""
        return timeout_seconds * 1000
    
    @staticmethod
    async def execute_with_timeout(func: Callable, timeout_seconds: float, *args, **kwargs) -> Any:
        """Execute function with timeout."""
        return await asyncio.wait_for(
            func(*args, **kwargs), 
            timeout=timeout_seconds
        )
    
    @staticmethod
    async def execute_without_timeout(func: Callable, *args, **kwargs) -> Any:
        """Execute function without timeout."""
        return await func(*args, **kwargs)


class WrapperUtils:
    """Utility functions for decorators and wrappers."""
    
    @staticmethod
    def should_skip_tracking(enabled: bool) -> bool:
        """Check if tracking should be skipped."""
        return not enabled
    
    @staticmethod
    def is_async_function(func: Callable) -> bool:
        """Check if function is async."""
        return asyncio.iscoroutinefunction(func)
    
    @staticmethod
    def run_sync_as_async(async_wrapper: Callable, *args, **kwargs) -> Any:
        """Run sync function through async wrapper."""
        return asyncio.run(async_wrapper(*args, **kwargs))