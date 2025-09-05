"""Usage pattern analysis operations."""

from typing import Any, Dict, List

from netra_backend.app.logging_config import central_logger as logger


class UsageAnalysisOperations:
    """Handles usage pattern analysis with proper type safety."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager

    async def analyze_usage_patterns(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time."""
        return await self._execute_usage_analysis(user_id, days_back)

    async def _execute_usage_analysis(self, user_id: int, days_back: int) -> Dict[str, Any]:
        """Execute usage pattern analysis workflow."""
        data = await self._fetch_usage_data(user_id, days_back)
        return self._handle_usage_result(data, days_back)

    async def _fetch_usage_data(self, user_id: int, days_back: int) -> List[Dict[str, Any]]:
        """Fetch usage pattern data from database."""
        query = self._build_usage_patterns_query(user_id, days_back)
        cache_key = f"usage_patterns:{user_id}:{days_back}"
        return await self._fetch_cached_data(query, cache_key)

    def _handle_usage_result(
        self,
        data: List[Dict[str, Any]],
        days_back: int
    ) -> Dict[str, Any]:
        """Handle usage pattern analysis result."""
        if not data:
            return {"status": "no_data", "message": "No usage data available"}
        return self._process_usage_patterns(data, days_back)

    def _build_usage_patterns_query(self, user_id: int, days_back: int) -> str:
        """Build usage patterns query."""
        return self.query_builder.build_usage_patterns_query(user_id, days_back)

    async def _fetch_cached_data(self, query: str, cache_key: str) -> List[Dict[str, Any]]:
        """Fetch data with caching support."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _process_usage_patterns(self, data: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Process usage patterns data."""
        from netra_backend.app.agents.data_sub_agent.usage_pattern_processor import UsagePatternProcessor
        processor = UsagePatternProcessor()
        return processor.process_patterns(data, days_back)