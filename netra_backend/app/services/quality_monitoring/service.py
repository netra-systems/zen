"""Main quality monitoring service"""

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.clickhouse import ClickHouseDatabase
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.quality_gate_service import ContentType, QualityMetrics
from netra_backend.app.services.quality_monitoring.alerts import QualityAlertManager
from netra_backend.app.services.quality_monitoring.analytics import TrendAnalyzer
from netra_backend.app.services.quality_monitoring.metrics import MetricsCollector
from netra_backend.app.services.quality_monitoring.models import (
    QualityAlert,
    QualityTrend,
)

logger = central_logger.get_logger(__name__)


class QualityMonitoringService:
    """Service for monitoring AI output quality at scale"""
    
    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        clickhouse_manager: Optional[ClickHouseDatabase] = None,
        db_session: Optional[AsyncSession] = None
    ):
        """Initialize the quality monitoring service"""
        self.redis_manager = redis_manager
        self.clickhouse_manager = clickhouse_manager
        self.db_session = db_session
        
        # Initialize components
        self.alert_manager = QualityAlertManager()
        self.metrics_collector = MetricsCollector(
            redis_manager, clickhouse_manager, db_session
        )
        self.trend_analyzer = TrendAnalyzer()
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task = None
        self.subscribers: Set[str] = set()
        
        logger.info("Quality Monitoring Service initialized")
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start the monitoring loop"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Started monitoring with {interval_seconds}s interval")
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        if not self.monitoring_active:
            return
        self.monitoring_active = False
        if self.monitoring_task:
            await self._cancel_monitoring_task()
        logger.info("Stopped quality monitoring")
    
    async def _cancel_monitoring_task(self):
        """Cancel monitoring task gracefully"""
        self.monitoring_task.cancel()
        try:
            await self.monitoring_task
        except asyncio.CancelledError:
            pass
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self._run_monitoring_cycle()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
            await asyncio.sleep(interval)
    
    async def _run_monitoring_cycle(self):
        """Run single monitoring cycle"""
        await self.metrics_collector.collect_from_sources()
        buffer = self.metrics_collector.get_buffer()
        trends = await self.trend_analyzer.analyze_trends(buffer)
        alerts = await self.alert_manager.check_thresholds(buffer)
        await self.trend_analyzer.update_agent_profiles(buffer)
        await self._broadcast_updates(trends, alerts)
        await self.metrics_collector.persist_metrics()
    
    async def _broadcast_updates(self, trends: List, alerts: List):
        """Broadcast updates to subscribers"""
        updates = {
            'trends': [self._serialize_trend(t) for t in trends],
            'alerts': [asdict(a) for a in alerts],
            'timestamp': datetime.now(UTC).isoformat()
        }
        if self.subscribers:
            logger.debug(f"Broadcasting to {len(self.subscribers)} subscribers")
    
    def _serialize_trend(self, trend: QualityTrend) -> Dict:
        """Serialize trend for broadcast"""
        return {
            'metric_type': trend.metric_type.value,
            'period': trend.period,
            'trend_direction': trend.trend_direction,
            'change_percentage': trend.change_percentage,
            'current_average': trend.current_average,
            'previous_average': trend.previous_average,
            'forecast_next_period': trend.forecast_next_period,
            'confidence': trend.confidence
        }
    
    async def record_quality_event(
        self, agent_name: str, content_type: ContentType,
        metrics: QualityMetrics, user_id: Optional[str] = None,
        thread_id: Optional[str] = None, run_id: Optional[str] = None
    ):
        """Record a quality event for monitoring"""
        try:
            await self.metrics_collector.record_event(
                agent_name, content_type, metrics,
                user_id, thread_id, run_id
            )
            await self.alert_manager.check_immediate_alert(agent_name, metrics)
        except Exception as e:
            logger.error(f"Error recording quality event: {str(e)}")
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            buffer = self.metrics_collector.get_buffer()
            active_alerts = self.alert_manager.active_alerts
            recent_alerts = self.alert_manager.get_recent_alerts()
            data = self.trend_analyzer.get_dashboard_data(buffer, active_alerts)
            data['recent_alerts'] = [asdict(a) for a in recent_alerts]
            return data
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return {}
    
    async def get_agent_report(
        self, agent_name: str, period_hours: int = 24
    ) -> Dict[str, Any]:
        """Get detailed report for a specific agent"""
        try:
            events = self.metrics_collector.get_agent_events(agent_name)
            return self.trend_analyzer.get_agent_report(
                agent_name, events, period_hours
            )
        except Exception as e:
            logger.error(f"Error getting agent report: {str(e)}")
            return {'error': str(e)}
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        return await self.alert_manager.acknowledge(alert_id)
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        return await self.alert_manager.resolve(alert_id)
    
    async def subscribe_to_updates(self, subscriber_id: str):
        """Subscribe to real-time quality updates"""
        self.subscribers.add(subscriber_id)
        logger.info(f"Subscriber {subscriber_id} added")
    
    async def unsubscribe_from_updates(self, subscriber_id: str):
        """Unsubscribe from real-time quality updates"""
        self.subscribers.discard(subscriber_id)
        logger.info(f"Subscriber {subscriber_id} removed")