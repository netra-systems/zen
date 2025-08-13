"""Unified data operations module - combines data fetching and analysis operations."""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .data_fetching import DataFetching
from .data_analysis_ops import DataAnalysisOperations
from .insights_generator import InsightsGenerator


class DataOperations:
    """Unified interface for data operations - combines fetching and analysis"""
    
    def __init__(self) -> None:
        self.data_fetching = DataFetching()
        self.analysis_ops = DataAnalysisOperations(self.data_fetching)
        self.insights_generator = InsightsGenerator()
    
    # Delegate basic data operations to DataFetching
    async def get_cached_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        return await self.data_fetching.get_cached_schema(table_name)
    
    async def fetch_clickhouse_data(self, query: str, cache_key: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        return await self.data_fetching.fetch_clickhouse_data(query, cache_key)
    
    async def check_data_availability(self, user_id: int, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        return await self.data_fetching.check_data_availability(user_id, start_time, end_time)
    
    async def get_available_metrics(self, user_id: int) -> List[str]:
        return await self.data_fetching.get_available_metrics(user_id)
    
    async def get_workload_list(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.data_fetching.get_workload_list(user_id, limit)
    
    async def validate_query_parameters(self, user_id: int, workload_id: Optional[str], metrics: List[str]) -> Dict[str, Any]:
        return await self.data_fetching.validate_query_parameters(user_id, workload_id, metrics)
    
    # Delegate analysis operations to DataAnalysisOperations
    async def analyze_performance_metrics(self, user_id: int, workload_id: Optional[str], time_range: Tuple[datetime, datetime], query_builder: Any, analysis_engine: Any) -> Dict[str, Any]:
        return await self.analysis_ops.analyze_performance_metrics(
            user_id, workload_id, time_range, query_builder, analysis_engine
        )
    
    async def detect_anomalies(self, user_id: int, metric_name: str, time_range: Tuple[datetime, datetime], query_builder: Any, z_score_threshold: float = 2.0) -> Dict[str, Any]:
        return await self.analysis_ops.detect_anomalies(
            user_id, metric_name, time_range, query_builder, z_score_threshold
        )
    
    async def analyze_correlations(self, user_id: int, metrics: List[str], time_range: Tuple[datetime, datetime], query_builder: Any) -> Dict[str, Any]:
        return await self.analysis_ops.analyze_correlations(
            user_id, metrics, time_range, query_builder
        )
    
    async def analyze_usage_patterns(self, user_id: int, query_builder: Any, days_back: int = 30) -> Dict[str, Any]:
        return await self.analysis_ops.analyze_usage_patterns(
            user_id, query_builder, days_back
        )
    
    async def generate_insights(self, performance_data: Dict[str, Any], usage_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.insights_generator.generate_insights(performance_data, usage_data)