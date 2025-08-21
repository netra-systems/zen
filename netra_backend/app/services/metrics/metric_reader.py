"""
Metric reader module for accessing and filtering metric data.
Handles data retrieval operations with 25-line function limit.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

from netra_backend.app.services.metrics.agent_metrics_models import AgentOperationRecord, AgentMetrics


class MetricReader:
    """Handles metric data reading operations."""
    
    def __init__(self, operation_records: deque, agent_metrics: Dict[str, AgentMetrics]):
        self._operation_records = operation_records
        self._agent_metrics = agent_metrics
    
    def get_agent_metrics(self, agent_name: str) -> Optional[AgentMetrics]:
        """Get current metrics for an agent."""
        return self._agent_metrics.get(agent_name)
    
    def get_all_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all agents."""
        return dict(self._agent_metrics)
    
    def get_recent_operations(self, agent_name: Optional[str], hours: int) -> List[AgentOperationRecord]:
        """Get recent operations within time window."""
        cutoff_time = self._calculate_cutoff_time(hours)
        recent_ops = self._filter_by_time_and_agent(cutoff_time, agent_name)
        return self._sort_operations_by_time(recent_ops)
    
    def _calculate_cutoff_time(self, hours: int) -> datetime:
        """Calculate cutoff time for filtering."""
        from datetime import UTC
        return datetime.now(UTC) - timedelta(hours=hours)
    
    def _filter_by_time_and_agent(self, cutoff_time: datetime, agent_name: Optional[str]) -> List[AgentOperationRecord]:
        """Filter operations by time window and agent."""
        filtered_ops = []
        for record in self._operation_records:
            if self._matches_filter_criteria(record, cutoff_time, agent_name):
                filtered_ops.append(record)
        return filtered_ops
    
    def _matches_filter_criteria(self, record: AgentOperationRecord, cutoff_time: datetime, agent_name: Optional[str]) -> bool:
        """Check if operation matches filter criteria."""
        if record.start_time < cutoff_time:
            return False
        return agent_name is None or record.agent_name == agent_name
    
    def _sort_operations_by_time(self, operations: List[AgentOperationRecord]) -> List[AgentOperationRecord]:
        """Sort operations by start time in descending order."""
        return sorted(operations, key=lambda x: x.start_time, reverse=True)
    
    def filter_recent_records(self, cutoff_time: datetime, max_size: int) -> deque:
        """Filter and return recent operation records."""
        filtered_records = deque(maxlen=max_size)
        for record in self._operation_records:
            if record.start_time >= cutoff_time:
                filtered_records.append(record)
        return filtered_records
    
    def count_active_agents(self) -> int:
        """Count agents with at least one operation."""
        return len([m for m in self._agent_metrics.values() if m.total_operations > 0])
    
    def count_unhealthy_agents(self, health_threshold: float = 0.7) -> int:
        """Count agents with health score below threshold."""
        from .agent_metrics_models import calculate_health_score
        unhealthy_count = 0
        for metrics in self._agent_metrics.values():
            if calculate_health_score(metrics) < health_threshold:
                unhealthy_count += 1
        return unhealthy_count