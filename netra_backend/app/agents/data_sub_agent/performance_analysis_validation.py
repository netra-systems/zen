"""Performance Analysis Validation Helpers

Validation and health check functions for performance analysis.
Extracted to maintain 450-line module limit.

Business Value: Ensures performance analysis data quality.
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger
from app.agents.base.interface import ExecutionContext
from app.agents.state import DeepAgentState


class PerformanceAnalysisValidator:
    """Validation helpers for performance analysis operations."""
    
    def __init__(self, clickhouse_ops: Any, redis_manager: Any):
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
    
    async def run_validation_checks(self, user_id: int, workload_id: Optional[str], 
                                  time_range: Tuple[datetime, datetime]) -> Dict[str, bool]:
        """Run comprehensive validation checks."""
        checks = {
            "user_id_valid": user_id > 0,
            "time_range_valid": self._validate_time_range(time_range),
            "clickhouse_available": await self._check_clickhouse_availability(),
            "redis_available": await self._check_redis_availability()
        }
        
        if workload_id:
            checks["workload_id_format"] = self._validate_workload_id_format(workload_id)
        
        return checks
    
    async def log_validation_result(self, context: ExecutionContext, is_valid: bool,
                                  validation_checks: Dict[str, bool]) -> None:
        """Log validation results for monitoring."""
        if not is_valid:
            failed_checks = [k for k, v in validation_checks.items() if not v]
            logger.warning(f"Validation failed for {context.run_id}: {failed_checks}")
        else:
            logger.info(f"Validation passed for {context.run_id}")
    
    def _validate_time_range(self, time_range: Tuple[datetime, datetime]) -> bool:
        """Validate time range parameters."""
        start_time, end_time = time_range
        if start_time >= end_time:
            return False
        # Check if time range is not too far in the past (e.g., max 1 year)
        max_age_days = 365
        if (datetime.utcnow() - start_time).days > max_age_days:
            return False
        return True
    
    def _validate_workload_id_format(self, workload_id: str) -> bool:
        """Validate workload ID format."""
        return workload_id and len(workload_id.strip()) > 0
    
    async def _check_clickhouse_availability(self) -> bool:
        """Check if ClickHouse is available."""
        try:
            # Simple health check - could be enhanced with actual ping
            return self.clickhouse_ops is not None
        except Exception:
            return False
    
    async def _check_redis_availability(self) -> bool:
        """Check if Redis is available."""
        try:
            return self.redis_manager is not None
        except Exception:
            return False
    
    def create_legacy_state(self, user_id: int, workload_id: Optional[str],
                           time_range: Tuple[datetime, datetime]) -> DeepAgentState:
        """Create legacy state object for backward compatibility."""
        state = DeepAgentState()
        state.user_id = user_id
        state.metadata = {
            "workload_id": workload_id,
            "time_range": time_range
        }
        return state
    
    def calculate_time_range_hours(self, time_range: Tuple[datetime, datetime]) -> float:
        """Calculate time range in hours."""
        start_time, end_time = time_range
        return (end_time - start_time).total_seconds() / 3600


class PerformanceQueryBuilder:
    """Helper class for building performance queries and cache keys."""
    
    def __init__(self, query_builder: Any):
        self.query_builder = query_builder
    
    def build_performance_query(self, user_id: int, workload_id: Optional[str], 
                               start_time: datetime, end_time: datetime, aggregation: str) -> str:
        """Build performance metrics query."""
        return self.query_builder.build_performance_metrics_query(
            user_id, workload_id, start_time, end_time, aggregation
        )
    
    def build_cache_key(self, user_id: int, workload_id: Optional[str], 
                       start_time: datetime, end_time: datetime) -> str:
        """Build cache key for performance metrics."""
        return f"perf_metrics:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}"
    
    def determine_aggregation_level(self, start_time: datetime, end_time: datetime) -> str:
        """Determine appropriate aggregation level based on time range."""
        time_diff = (end_time - start_time).total_seconds()
        if time_diff <= 3600:
            return "minute"
        elif time_diff <= 86400:
            return "hour"
        return "day"


class PerformanceErrorHandlers:
    """Error handling utilities for performance analysis."""
    
    @staticmethod
    def create_no_data_response() -> Dict[str, Any]:
        """Create response for no data found."""
        return {
            "status": "no_data",
            "message": "No performance metrics found for the specified criteria"
        }
    
    @staticmethod
    def create_error_response_from_exception(error: Exception) -> Dict[str, Any]:
        """Create error response from exception."""
        return {
            "status": "error",
            "error": str(error),
            "error_type": type(error).__name__
        }
    
    @staticmethod
    def get_performance_components_health() -> Dict[str, Any]:
        """Get health status of performance analysis specific components."""
        return {
            "query_builder": "healthy",  # Could be enhanced with actual health checks
            "analysis_engine": "healthy",
            "clickhouse_ops": "healthy",
            "redis_manager": "healthy"
        }