"""
Metric formatter module for preparing and formatting metric data.
Handles data formatting operations with 25-line function limit.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from .agent_metrics_models import AgentOperationRecord, FailureType


class MetricFormatter:
    """Handles metric data formatting operations."""
    
    def finalize_operation_record(self, record: AgentOperationRecord, completion_data: Dict[str, Any]) -> None:
        """Finalize operation record with completion data."""
        self._set_basic_completion_data(record, completion_data)
        self._set_resource_usage_data(record, completion_data)
        self._calculate_execution_time(record)
        self._update_record_metadata(record, completion_data.get('metadata'))
    
    def _set_basic_completion_data(self, record: AgentOperationRecord, data: Dict[str, Any]) -> None:
        """Set basic completion data on record."""
        from datetime import UTC
        record.end_time = datetime.now(UTC)
        record.success = data.get('success', True)
        record.failure_type = data.get('failure_type')
        record.error_message = data.get('error_message')
    
    def _set_resource_usage_data(self, record: AgentOperationRecord, data: Dict[str, Any]) -> None:
        """Set resource usage data on record."""
        record.memory_usage_mb = data.get('memory_usage_mb', 0.0)
        record.cpu_usage_percent = data.get('cpu_usage_percent', 0.0)
    
    def _calculate_execution_time(self, record: AgentOperationRecord) -> None:
        """Calculate and set execution time for record."""
        if record.end_time and record.start_time:
            duration = record.end_time - record.start_time
            record.execution_time_ms = duration.total_seconds() * 1000
    
    def _update_record_metadata(self, record: AgentOperationRecord, metadata: Optional[Dict[str, Any]]) -> None:
        """Update record metadata if provided."""
        if metadata:
            record.metadata.update(metadata)
    
    def create_timeout_completion_data(self, timeout_duration_ms: float) -> Dict[str, Any]:
        """Create completion data for timeout scenario."""
        return {
            'success': False,
            'failure_type': FailureType.TIMEOUT,
            'error_message': f"Operation timed out after {timeout_duration_ms}ms"
        }
    
    def create_validation_error_completion_data(self, validation_error: str) -> Dict[str, Any]:
        """Create completion data for validation error scenario."""
        return {
            'success': False,
            'failure_type': FailureType.VALIDATION_ERROR,
            'error_message': validation_error
        }
    
    def format_system_overview(self, operation_stats: Dict[str, Any], agent_stats: Dict[str, Any], system_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format system overview combining all stats."""
        return {
            **operation_stats,
            **agent_stats,
            **system_stats
        }