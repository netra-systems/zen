"""Metrics collection and storage for quality monitoring"""

import json
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.clickhouse import ClickHouseDatabase
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.quality_gate_service import ContentType, QualityMetrics

logger = central_logger.get_logger(__name__)


# Import MetricsCollector from canonical location - CONSOLIDATED
from netra_backend.app.monitoring.models import MetricsCollector as CoreMetricsCollector


class QualityMetricsCollector:
    """Collects and stores quality metrics"""
    
    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        clickhouse_manager: Optional[ClickHouseDatabase] = None,
        db_session: Optional[AsyncSession] = None
    ):
        self.redis_manager = redis_manager
        self.clickhouse_manager = clickhouse_manager
        self.db_session = db_session
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=1000))
    
    async def record_event(
        self, agent: str, content_type: ContentType,
        metrics: QualityMetrics, user_id: Optional[str] = None,
        thread_id: Optional[str] = None, run_id: Optional[str] = None
    ):
        """Record quality event"""
        event = self._create_event(
            agent, content_type, metrics, user_id, thread_id, run_id
        )
        self.metrics_buffer[agent].append(event)
        await self._store_event(event)
        logger.debug(f"Recorded event for {agent}: Score {metrics.overall_score:.2f}")
    
    def _create_event(
        self, agent: str, content_type: ContentType,
        metrics: QualityMetrics, user_id: str, thread_id: str, run_id: str
    ) -> Dict:
        """Create event dictionary"""
        return {
            'timestamp': datetime.now(UTC).isoformat(),
            'agent': agent,
            'content_type': content_type.value,
            'quality_score': metrics.overall_score,
            'quality_level': metrics.quality_level.value,
            'specificity': metrics.specificity_score,
            'actionability': metrics.actionability_score,
            'quantification': metrics.quantification_score,
            'word_count': metrics.word_count,
            'generic_phrases': metrics.generic_phrase_count,
            'circular_reasoning': metrics.circular_reasoning_detected,
            'hallucination_risk': metrics.hallucination_risk,
            'user_id': user_id,
            'thread_id': thread_id,
            'run_id': run_id
        }
    
    async def _store_event(self, event: Dict):
        """Store event in backends"""
        if self.redis_manager:
            await self.redis_manager.store_quality_event(event)
        if self.clickhouse_manager:
            await self._store_clickhouse(event)
    
    async def _store_clickhouse(self, event: Dict):
        """Store event in ClickHouse"""
        try:
            ch_event = self._format_for_clickhouse(event)
            await self.clickhouse_manager.insert_quality_event(ch_event)
        except Exception as e:
            logger.error(f"Error storing in ClickHouse: {str(e)}")
    
    def _format_for_clickhouse(self, event: Dict) -> Dict:
        """Format event for ClickHouse"""
        return {
            'timestamp': event['timestamp'],
            'agent_name': event['agent'],
            'content_type': event['content_type'],
            'quality_score': event['quality_score'],
            'quality_level': event['quality_level'],
            'metrics': json.dumps({
                'specificity': event.get('specificity', 0),
                'actionability': event.get('actionability', 0),
                'quantification': event.get('quantification', 0)
            }),
            'issues': json.dumps({
                'generic_phrases': event.get('generic_phrases', 0),
                'circular_reasoning': event.get('circular_reasoning', False),
                'hallucination_risk': event.get('hallucination_risk', 0)
            }),
            'user_id': event.get('user_id', ''),
            'thread_id': event.get('thread_id', ''),
            'run_id': event.get('run_id', '')
        }
    
    async def collect_from_sources(self):
        """Collect metrics from all sources"""
        await self._collect_from_redis()
        await self._collect_from_database()
    
    async def _collect_from_redis(self):
        """Collect metrics from Redis"""
        if not self.redis_manager:
            return
        try:
            metrics = await self.redis_manager.get_recent_quality_metrics()
            for metric in metrics:
                agent = metric.get('agent', 'unknown')
                self.metrics_buffer[agent].append(metric)
        except Exception as e:
            logger.error(f"Error collecting from Redis: {str(e)}")
    
    async def _collect_from_database(self):
        """Collect metrics from database"""
        if not self.db_session:
            return
        try:
            from netra_backend.app.db.models import AgentRun
            stmt = select(AgentRun).where(
                AgentRun.created_at > datetime.now(UTC) - timedelta(hours=1)
            ).limit(100)
            result = await self.db_session.execute(stmt)
            runs = result.scalars().all()
            self._process_agent_runs(runs)
        except Exception as e:
            logger.error(f"Error collecting from database: {str(e)}")
    
    def _process_agent_runs(self, runs):
        """Process agent runs for metrics"""
        for run in runs:
            if not run.metadata or 'quality_metrics' not in run.metadata:
                continue
            metric = {
                'agent': run.agent_name,
                'quality_score': run.metadata['quality_metrics'].get('score', 0.5),
                'quality_level': run.metadata['quality_metrics'].get('level', 'acceptable'),
                'timestamp': run.created_at.isoformat()
            }
            self.metrics_buffer[run.agent_name].append(metric)
    
    async def persist_metrics(self):
        """Persist metrics for historical analysis"""
        if self.clickhouse_manager:
            await self._batch_insert_clickhouse()
    
    async def _batch_insert_clickhouse(self):
        """Batch insert events to ClickHouse"""
        if not self.clickhouse_manager:
            return
        try:
            all_events = []
            for events in self.metrics_buffer.values():
                all_events.extend(list(events)[-10:])
            if all_events:
                formatted = [self._format_for_clickhouse(e) for e in all_events]
                await self.clickhouse_manager.batch_insert_quality_events(formatted)
        except Exception as e:
            logger.error(f"Error batch inserting: {str(e)}")
    
    def get_buffer(self) -> Dict:
        """Get metrics buffer"""
        return self.metrics_buffer
    
    def get_agent_events(self, agent: str, limit: int = 100) -> List[Dict]:
        """Get events for specific agent"""
        return list(self.metrics_buffer[agent])[-limit:]


# Export QualityMetricsCollector as MetricsCollector for compatibility
MetricsCollector = QualityMetricsCollector