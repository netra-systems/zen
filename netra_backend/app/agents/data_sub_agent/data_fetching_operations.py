# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514  
# Context: Data fetching operations module (450-line compliance)
# Git: 8-18-25-AM | Modernizing to standard agent patterns
# Change: Create | Scope: Module | Risk: Low
# Session: data-sub-agent-modernization | Seq: 3
# Review: Complete | Score: 100
# ================================
"""
Data Fetching Operations

High-level data operations for availability checks, metrics, and validation.
Builds on DataFetchingCore for complex business logic operations.

Business Value: Structured data operations with validation and business logic.
"""

from typing import Dict, List, Optional, Any

from app.logging_config import central_logger
from netra_backend.app.data_fetching_core import DataFetchingCore

logger = central_logger.get_logger(__name__)


class DataFetchingOperations(DataFetchingCore):
    """High-level data operations with business logic."""
    
    async def check_data_availability(
        self, 
        user_id: int, 
        start_time, 
        end_time
    ) -> Dict[str, Any]:
        """Check if data is available for the specified user and time range"""
        query = self._build_availability_query(user_id, start_time, end_time)
        cache_key = self._build_availability_cache_key(user_id, start_time, end_time)
        data = await self.fetch_clickhouse_data(query, cache_key)
        return self._process_availability_result(data)
    
    def _build_availability_query(self, user_id: int, start_time, end_time) -> str:
        """Build query for checking data availability."""
        return f"""
        SELECT 
            COUNT(*) as total_records,
            MIN(timestamp) as earliest_record,
            MAX(timestamp) as latest_record,
            COUNT(DISTINCT workload_id) as unique_workloads
        FROM workload_events 
        WHERE user_id = {user_id}
        AND timestamp BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
        """
    
    def _build_availability_cache_key(self, user_id: int, start_time, end_time) -> str:
        """Build cache key for availability query."""
        return f"data_availability:{user_id}:{start_time.isoformat()}:{end_time.isoformat()}"
    
    def _process_availability_result(self, data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Process availability query result."""
        if not data or not data[0]['total_records']:
            return self._build_unavailable_response()
        return self._build_available_response(data[0])
    
    def _build_unavailable_response(self) -> Dict[str, Any]:
        """Build response for unavailable data."""
        return {
            "available": False,
            "message": "No data available for the specified criteria"
        }
    
    def _build_available_response(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Build response for available data."""
        return {
            "available": True,
            "total_records": record['total_records'],
            "earliest_record": record['earliest_record'],
            "latest_record": record['latest_record'],
            "unique_workloads": record['unique_workloads']
        }
    
    async def get_available_metrics(self, user_id: int) -> List[str]:
        """Get list of available metrics for a user"""
        query = self._build_metrics_query(user_id)
        cache_key = f"available_metrics:{user_id}"
        data = await self.fetch_clickhouse_data(query, cache_key)
        return self._process_metrics_result(data)
    
    def _build_metrics_query(self, user_id: int) -> str:
        """Build query for extracting available metrics."""
        return f"""
        SELECT DISTINCT 
            arrayJoin(JSONExtractKeys(metrics)) as metric_name
        FROM workload_events 
        WHERE user_id = {user_id}
        AND isNotNull(metrics)
        ORDER BY metric_name
        """
    
    def _process_metrics_result(self, data: Optional[List[Dict[str, Any]]]) -> List[str]:
        """Process metrics query result."""
        if not data:
            return self._get_default_metrics()
        return [row['metric_name'] for row in data if row['metric_name']]
    
    def _get_default_metrics(self) -> List[str]:
        """Get default metrics when no user-specific metrics found."""
        return ["latency_ms", "throughput", "cost_cents", "error_rate"]
    
    async def get_workload_list(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of workloads for a user"""
        query = self._build_workload_list_query(user_id, limit)
        cache_key = self._build_workload_cache_key(user_id, limit)
        data = await self.fetch_clickhouse_data(query, cache_key)
        return data or []
    
    def _build_workload_list_query(self, user_id: int, limit: int) -> str:
        """Build query for getting workload list."""
        return f"""
        SELECT 
            workload_id,
            COUNT(*) as event_count,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen,
            AVG(JSONExtractFloat(metrics, 'cost_cents')) as avg_cost
        FROM workload_events 
        WHERE user_id = {user_id}
        AND workload_id IS NOT NULL
        GROUP BY workload_id
        ORDER BY last_seen DESC
        LIMIT {limit}
        """
    
    def _build_workload_cache_key(self, user_id: int, limit: int) -> str:
        """Build cache key for workload list query."""
        return f"workload_list:{user_id}:{limit}"