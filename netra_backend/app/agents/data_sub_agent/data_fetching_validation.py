# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514  
# Context: Data fetching validation module (450-line compliance)
# Git: 8-18-25-AM | Modernizing to standard agent patterns
# Change: Create | Scope: Module | Risk: Low
# Session: data-sub-agent-modernization | Seq: 4
# Review: Complete | Score: 100
# ================================
"""
Data Fetching Validation

Parameter validation and data integrity checks for data fetching operations.
Ensures data quality and prevents invalid operations.

Business Value: Data integrity validation prevents errors and improves reliability.
"""

from typing import Dict, List, Optional, Any

from netra_backend.app.logging_config import central_logger
from netra_backend.app.data_fetching_operations import DataFetchingOperations

logger = central_logger.get_logger(__name__)


class DataFetchingValidation(DataFetchingOperations):
    """Parameter validation and data integrity operations."""
    
    async def validate_query_parameters(
        self, 
        user_id: int, 
        workload_id: Optional[str],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Validate query parameters against available data"""
        validation_result = self._init_validation_result()
        
        if not await self._validate_user_exists(user_id, validation_result):
            return validation_result
        
        await self._validate_workload_id(user_id, workload_id, validation_result)
        await self._validate_metrics(user_id, metrics, validation_result)
        return validation_result
    
    def _init_validation_result(self) -> Dict[str, Any]:
        """Initialize validation result structure."""
        return {
            "valid": True,
            "issues": [],
            "suggestions": []
        }
    
    async def _validate_user_exists(self, user_id: int, validation_result: Dict[str, Any]) -> bool:
        """Validate that user exists in the data."""
        user_check_query = f"SELECT COUNT(*) as count FROM workload_events WHERE user_id = {user_id}"
        user_data = await self.fetch_clickhouse_data(user_check_query)
        
        if not user_data or user_data[0]['count'] == 0:
            validation_result["valid"] = False
            validation_result["issues"].append(f"No data found for user_id: {user_id}")
            return False
        return True
    
    async def _validate_workload_id(self, user_id: int, workload_id: Optional[str], validation_result: Dict[str, Any]) -> None:
        """Validate workload_id if specified."""
        if not workload_id:
            return
        
        workload_data = await self._check_workload_exists(user_id, workload_id)
        if not workload_data or workload_data[0]['count'] == 0:
            self._add_workload_validation_issues(workload_id, validation_result)
    
    async def _check_workload_exists(self, user_id: int, workload_id: str) -> Optional[List[Dict[str, Any]]]:
        """Check if workload exists for user."""
        workload_check_query = f"""
        SELECT COUNT(*) as count 
        FROM workload_events 
        WHERE user_id = {user_id} AND workload_id = '{workload_id}'
        """
        return await self.fetch_clickhouse_data(workload_check_query)
    
    def _add_workload_validation_issues(self, workload_id: str, validation_result: Dict[str, Any]) -> None:
        """Add workload validation issues to result."""
        validation_result["issues"].append(f"No data found for workload_id: {workload_id}")
        validation_result["suggestions"].append("Try without specifying workload_id")
    
    async def _validate_metrics(self, user_id: int, metrics: List[str], validation_result: Dict[str, Any]) -> None:
        """Validate metrics against available metrics."""
        available_metrics = await self.get_available_metrics(user_id)
        invalid_metrics = [m for m in metrics if m not in available_metrics]
        
        if invalid_metrics:
            self._add_metrics_validation_issues(invalid_metrics, available_metrics, validation_result)
    
    def _add_metrics_validation_issues(self, invalid_metrics: List[str], available_metrics: List[str], validation_result: Dict[str, Any]) -> None:
        """Add metrics validation issues to result."""
        validation_result["issues"].append(f"Invalid metrics: {invalid_metrics}")
        validation_result["suggestions"].append(f"Available metrics: {available_metrics}")