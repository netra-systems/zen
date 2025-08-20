"""
Metric publisher module for alerts and notifications.
Handles publishing operations with 25-line function limit.
"""

from typing import Dict
from collections import deque

from app.logging_config import central_logger
from .agent_metrics_models import AgentOperationRecord, AgentMetrics

logger = central_logger.get_logger(__name__)


class MetricPublisher:
    """Handles metric publishing and alert operations."""
    
    def __init__(self, alert_thresholds: Dict[str, float]):
        self.error_rate_threshold = alert_thresholds.get('error_rate', 0.2)
        self.timeout_threshold = alert_thresholds.get('timeout', 30.0)
        self.memory_threshold_mb = alert_thresholds.get('memory', 1024.0)
        self.cpu_threshold_percent = alert_thresholds.get('cpu', 80.0)
    
    async def check_alert_conditions(self, record: AgentOperationRecord, agent_metrics: AgentMetrics) -> None:
        """Check if alert conditions are met."""
        agent_name = record.agent_name
        await self._check_error_rate_alert(agent_name, agent_metrics)
        await self._check_timeout_alert(agent_name, record.execution_time_ms)
        await self._check_resource_alerts(agent_name, record)
    
    async def _check_error_rate_alert(self, agent_name: str, metrics: AgentMetrics) -> None:
        """Check and trigger error rate alert if needed."""
        if metrics.error_rate > self.error_rate_threshold:
            await self._trigger_error_rate_alert(agent_name, metrics.error_rate)
    
    async def _check_timeout_alert(self, agent_name: str, execution_time_ms: float) -> None:
        """Check and trigger timeout alert if needed."""
        timeout_ms = self.timeout_threshold * 1000
        if execution_time_ms > timeout_ms:
            await self._trigger_timeout_alert(agent_name, execution_time_ms)
    
    async def _check_resource_alerts(self, agent_name: str, record: AgentOperationRecord) -> None:
        """Check and trigger resource-related alerts."""
        await self._check_memory_alert(agent_name, record.memory_usage_mb)
        await self._check_cpu_alert(agent_name, record.cpu_usage_percent)
    
    async def _check_memory_alert(self, agent_name: str, memory_mb: float) -> None:
        """Check and trigger memory alert if needed."""
        if memory_mb > self.memory_threshold_mb:
            await self._trigger_memory_alert(agent_name, memory_mb)
    
    async def _check_cpu_alert(self, agent_name: str, cpu_percent: float) -> None:
        """Check and trigger CPU alert if needed."""
        if cpu_percent > self.cpu_threshold_percent:
            await self._trigger_cpu_alert(agent_name, cpu_percent)
    
    async def _trigger_error_rate_alert(self, agent_name: str, error_rate: float) -> None:
        """Trigger alert for high error rate."""
        logger.warning(
            f"HIGH ERROR RATE ALERT: Agent {agent_name} has error rate of {error_rate:.2%}"
        )
    
    async def _trigger_timeout_alert(self, agent_name: str, execution_time_ms: float) -> None:
        """Trigger alert for operation timeout."""
        logger.warning(
            f"TIMEOUT ALERT: Agent {agent_name} operation took {execution_time_ms:.0f}ms"
        )
    
    async def _trigger_memory_alert(self, agent_name: str, memory_mb: float) -> None:
        """Trigger alert for high memory usage."""
        logger.warning(
            f"MEMORY ALERT: Agent {agent_name} using {memory_mb:.0f}MB memory"
        )
    
    async def _trigger_cpu_alert(self, agent_name: str, cpu_percent: float) -> None:
        """Trigger alert for high CPU usage."""
        logger.warning(
            f"CPU ALERT: Agent {agent_name} using {cpu_percent:.1f}% CPU"
        )