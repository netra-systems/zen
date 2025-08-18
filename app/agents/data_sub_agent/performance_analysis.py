"""Performance metrics analysis operations."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger


class PerformanceAnalysisOperations:
    """Handles performance metrics analysis with proper type safety."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
    
    async def analyze_performance_metrics(
        self,
        user_id: int,
        workload_id: Optional[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze performance metrics from ClickHouse."""
        return await self._execute_performance_analysis(user_id, workload_id, time_range)

    async def _execute_performance_analysis(
        self,
        user_id: int,
        workload_id: Optional[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Execute the performance analysis workflow."""
        params = self._build_query_params(time_range, user_id, workload_id)
        data = await self._fetch_performance_data(params)
        return self._handle_performance_result(data, time_range, params['aggregation'])
    
    def _build_query_params(self, time_range: Tuple[datetime, datetime], user_id: int, workload_id: Optional[str]) -> Dict[str, Any]:
        """Build query parameters for performance analysis."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        return {
            'start_time': start_time, 'end_time': end_time, 'aggregation': aggregation,
            'user_id': user_id, 'workload_id': workload_id
        }
    
    async def _fetch_performance_data(self, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Fetch performance data using query parameters."""
        query = self._build_performance_query(
            params['user_id'], params['workload_id'], params['start_time'], params['end_time'], params['aggregation']
        )
        cache_key = self._create_cache_key("perf_metrics", params['user_id'], params['workload_id'], params['start_time'], params['end_time'])
        return await self._fetch_cached_data(query, cache_key)
    
    def _handle_performance_result(self, data: Optional[List[Dict[str, Any]]], time_range: Tuple[datetime, datetime], aggregation: str) -> Dict[str, Any]:
        """Handle performance analysis result."""
        if not data:
            return self._create_no_data_response("No performance metrics found")
        return self._process_performance_data(data, time_range, aggregation)

    def _determine_aggregation_level(self, start_time: datetime, end_time: datetime) -> str:
        """Determine appropriate aggregation level based on time range."""
        time_diff = self._calculate_time_difference(start_time, end_time)
        return self._select_aggregation_by_duration(time_diff)

    def _calculate_time_difference(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate time difference in seconds."""
        return (end_time - start_time).total_seconds()

    def _select_aggregation_by_duration(self, time_diff: float) -> str:
        """Select aggregation level based on duration."""
        return self._get_aggregation_by_time_threshold(time_diff)

    def _get_aggregation_by_time_threshold(self, time_diff: float) -> str:
        """Get aggregation based on time thresholds."""
        if time_diff <= 3600:  # 1 hour
            return "minute"
        elif time_diff <= 86400:  # 1 day
            return "hour"
        return "day"
    
    def _build_performance_query(
        self,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        aggregation: str
    ) -> str:
        """Build performance metrics query."""
        return self._delegate_performance_query_build(
            user_id, workload_id, start_time, end_time, aggregation
        )

    def _delegate_performance_query_build(
        self,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        aggregation: str
    ) -> str:
        """Delegate performance query building to query builder."""
        return self.query_builder.build_performance_metrics_query(
            user_id, workload_id, start_time, end_time, aggregation
        )
    
    def _create_cache_key(
        self,
        prefix: str,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Create cache key for query results."""
        return self._build_cache_key_string(prefix, user_id, workload_id, start_time, end_time)

    def _build_cache_key_string(
        self,
        prefix: str,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Build cache key string from components."""
        return f"{prefix}:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}"

    async def _fetch_cached_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch data with caching support."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _create_no_data_response(self, message: str) -> Dict[str, Any]:
        """Create standardized no data response."""
        return {"status": "no_data", "message": message}
    
    def _process_performance_data(
        self,
        data: List[Dict[str, Any]],
        time_range: Tuple[datetime, datetime],
        aggregation: str
    ) -> Dict[str, Any]:
        """Process performance metrics data."""
        processor = self._create_performance_processor()
        return self._delegate_performance_processing(processor, data, time_range, aggregation)

    def _create_performance_processor(self):
        """Create performance data processor instance."""
        from .performance_data_processor import PerformanceDataProcessor
        return PerformanceDataProcessor(None)  # Will be injected

    def _delegate_performance_processing(
        self,
        processor,
        data: List[Dict[str, Any]],
        time_range: Tuple[datetime, datetime],
        aggregation: str
    ) -> Dict[str, Any]:
        """Delegate processing to performance processor."""
        return processor.process_performance_data(data, time_range, aggregation)