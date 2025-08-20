"""Factory Status Service.

Provides real-time factory status metrics and reports.
Implements production-ready metrics collection and analysis.
Module follows 450-line limit with 25-line function limit.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.core.exceptions_service import ServiceError
from app.logging_config import central_logger
from .metrics_collectors import (
    SystemMetricsCollector,
    GitMetricsCollector,
    CodeQualityMetricsCollector,
    PerformanceMetricsCollector
)
from .health_calculator import HealthScoreCalculator

logger = central_logger.get_logger(__name__)


class FactoryStatusService:
    """Real factory status metrics and reporting service."""
    
    def __init__(self):
        """Initialize factory status service."""
        self.metrics_cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.last_update: Optional[datetime] = None
        self._init_collectors()
    
    def _init_collectors(self) -> None:
        """Initialize all metrics collectors."""
        self.system_collector = SystemMetricsCollector()
        self.git_collector = GitMetricsCollector()
        self.quality_collector = CodeQualityMetricsCollector()
        self.performance_collector = PerformanceMetricsCollector()
        self.health_calculator = HealthScoreCalculator()
    
    async def get_factory_status(self) -> Dict[str, Any]:
        """Get comprehensive factory status report."""
        try:
            await self._ensure_fresh_metrics()
            return await self._build_status_response()
        except Exception as e:
            logger.error(f"Failed to get factory status: {e}")
            raise ServiceError(f"Factory status retrieval failed: {str(e)}")
    
    async def _ensure_fresh_metrics(self) -> None:
        """Ensure metrics are fresh by refreshing if needed."""
        if await self._should_refresh_cache():
            await self._refresh_metrics()
    
    async def _build_status_response(self) -> Dict[str, Any]:
        """Build the factory status response dictionary."""
        return {
            "status": "operational",
            "timestamp": datetime.now(),
            "metrics": self.metrics_cache,
            "health_score": await self._calculate_health_score()
        }
    
    async def _should_refresh_cache(self) -> bool:
        """Check if metrics cache needs refreshing."""
        if not self.last_update:
            return True
        return datetime.now() - self.last_update > self.cache_ttl
    
    async def _refresh_metrics(self):
        """Refresh all factory metrics."""
        self.metrics_cache = await self._collect_all_metrics()
        self.last_update = datetime.now()
    
    async def _collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all factory metrics into dictionary."""
        return {
            "system": await self.system_collector.collect(),
            "git": await self.git_collector.collect(),
            "code_quality": await self.quality_collector.collect(),
            "performance": await self.performance_collector.collect()
        }
    
    async def _calculate_health_score(self) -> float:
        """Calculate overall factory health score."""
        return self.health_calculator.calculate(self.metrics_cache)