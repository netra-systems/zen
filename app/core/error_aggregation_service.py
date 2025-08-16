"""Main error aggregation system service.

Coordinates error processing, trend analysis, and alerting through
a unified interface. Provides the main entry point for error aggregation.
"""

import asyncio
from typing import Any, Dict, Optional

from app.core.error_aggregation_base import ErrorData
from app.core.error_aggregation_handlers import ErrorAggregator
from app.core.error_aggregation_metrics import AlertEngine, MetricsReporter
from app.core.error_aggregation_patterns import ErrorTrendAnalyzer
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorAggregationSystem:
    """Main error aggregation and alerting system."""
    
    def __init__(self):
        """Initialize aggregation system."""
        self.aggregator = ErrorAggregator()
        self.trend_analyzer = ErrorTrendAnalyzer()
        self.alert_engine = AlertEngine()
        self.metrics_reporter = MetricsReporter(self.aggregator, self.alert_engine)
        
        # Processing control
        self.processing_active = False
        self.process_task: Optional[asyncio.Task] = None
        self.process_interval = 30  # seconds
    
    async def process_error(self, error_data: ErrorData) -> None:
        """Process single error through aggregation pipeline."""
        pattern = self.aggregator.add_error(error_data)
        trend = self._analyze_pattern_trend(pattern)
        alerts = self.alert_engine.evaluate_pattern(pattern, trend)
        
        self._log_alerts(alerts)
    
    def _analyze_pattern_trend(self, pattern):
        """Analyze trend for pattern."""
        return self.trend_analyzer.analyze_pattern_trend(
            pattern, self.aggregator.error_history
        )
    
    def _log_alerts(self, alerts) -> None:
        """Log generated alerts."""
        for alert in alerts:
            logger.warning(f"Error alert generated: {alert.message}")
    
    async def start_processing(self) -> None:
        """Start background processing."""
        if self.processing_active:
            return
        
        self.processing_active = True
        self.process_task = asyncio.create_task(self._processing_loop())
        logger.info("Error aggregation processing started")
    
    async def stop_processing(self) -> None:
        """Stop background processing."""
        self.processing_active = False
        
        if self.process_task:
            await self._cancel_process_task()
        
        logger.info("Error aggregation processing stopped")
    
    async def _cancel_process_task(self) -> None:
        """Cancel the processing task safely."""
        self.process_task.cancel()
        try:
            await self.process_task
        except asyncio.CancelledError:
            pass
    
    async def _processing_loop(self) -> None:
        """Background processing loop."""
        while self.processing_active:
            try:
                await self._process_all_patterns()
                await asyncio.sleep(self.process_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error aggregation processing error: {e}")
                await asyncio.sleep(self.process_interval)
    
    async def _process_all_patterns(self) -> None:
        """Process all current patterns for trends and alerts."""
        patterns = self.aggregator.get_patterns_in_window(60)
        
        for pattern in patterns:
            trend = self._analyze_pattern_trend(pattern)
            self.alert_engine.evaluate_pattern(pattern, trend)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and metrics."""
        base_status = self.metrics_reporter.get_system_status()
        base_status['processing_active'] = self.processing_active
        
        return base_status


# Global error aggregation system instance
error_aggregation_system = ErrorAggregationSystem()