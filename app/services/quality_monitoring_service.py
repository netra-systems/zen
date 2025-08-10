"""Quality Monitoring Service for Real-time AI Quality Tracking

This service provides comprehensive monitoring, alerting, and reporting for AI output quality,
enabling real-time detection of quality degradation and AI slop patterns at scale.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import json
import statistics
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.logging_config import central_logger
from app.redis_manager import RedisManager
from app.db.clickhouse import ClickHouseManager
from app.services.quality_gate_service import QualityLevel, ContentType, QualityMetrics
from app.core.exceptions import NetraException

logger = central_logger.get_logger(__name__)


class AlertSeverity(Enum):
    """Severity levels for quality alerts"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to track"""
    QUALITY_SCORE = "quality_score"
    SLOP_DETECTION_RATE = "slop_detection_rate"
    RETRY_RATE = "retry_rate"
    FALLBACK_RATE = "fallback_rate"
    USER_SATISFACTION = "user_satisfaction"
    RESPONSE_TIME = "response_time"
    TOKEN_EFFICIENCY = "token_efficiency"
    ERROR_RATE = "error_rate"


@dataclass
class QualityAlert:
    """Alert for quality issues"""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    metric_type: MetricType
    agent: str
    message: str
    current_value: float
    threshold: float
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class QualityTrend:
    """Trend analysis for quality metrics"""
    metric_type: MetricType
    period: str  # "hour", "day", "week"
    trend_direction: str  # "improving", "degrading", "stable"
    change_percentage: float
    current_average: float
    previous_average: float
    forecast_next_period: float
    confidence: float


@dataclass
class AgentQualityProfile:
    """Quality profile for an individual agent"""
    agent_name: str
    total_requests: int
    average_quality_score: float
    quality_distribution: Dict[QualityLevel, int]
    slop_detection_count: int
    retry_count: int
    fallback_count: int
    average_response_time: float
    last_updated: datetime
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class QualityMonitoringService:
    """Service for monitoring AI output quality at scale"""
    
    # Thresholds for alerts
    ALERT_THRESHOLDS = {
        MetricType.QUALITY_SCORE: {
            AlertSeverity.WARNING: 0.5,
            AlertSeverity.ERROR: 0.4,
            AlertSeverity.CRITICAL: 0.3
        },
        MetricType.SLOP_DETECTION_RATE: {
            AlertSeverity.WARNING: 0.1,  # 10% slop
            AlertSeverity.ERROR: 0.2,    # 20% slop
            AlertSeverity.CRITICAL: 0.3  # 30% slop
        },
        MetricType.RETRY_RATE: {
            AlertSeverity.WARNING: 0.15,
            AlertSeverity.ERROR: 0.25,
            AlertSeverity.CRITICAL: 0.4
        },
        MetricType.FALLBACK_RATE: {
            AlertSeverity.WARNING: 0.1,
            AlertSeverity.ERROR: 0.2,
            AlertSeverity.CRITICAL: 0.3
        },
        MetricType.ERROR_RATE: {
            AlertSeverity.WARNING: 0.05,
            AlertSeverity.ERROR: 0.1,
            AlertSeverity.CRITICAL: 0.2
        }
    }
    
    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        clickhouse_manager: Optional[ClickHouseManager] = None,
        db_session: Optional[AsyncSession] = None
    ):
        """Initialize the quality monitoring service"""
        self.redis_manager = redis_manager
        self.clickhouse_manager = clickhouse_manager
        self.db_session = db_session
        
        # In-memory metrics storage for real-time access
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.alert_history = deque(maxlen=500)
        self.active_alerts: Dict[str, QualityAlert] = {}
        
        # Agent profiles
        self.agent_profiles: Dict[str, AgentQualityProfile] = {}
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task = None
        
        # WebSocket subscribers for real-time updates
        self.subscribers: Set[str] = set()
        
        logger.info("Quality Monitoring Service initialized")
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start the monitoring loop"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
        logger.info(f"Started quality monitoring with {interval_seconds}s interval")
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped quality monitoring")
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect metrics from all sources
                await self._collect_metrics()
                
                # Analyze trends
                trends = await self._analyze_trends()
                
                # Check thresholds and generate alerts
                alerts = await self._check_thresholds()
                
                # Update agent profiles
                await self._update_agent_profiles()
                
                # Broadcast updates to subscribers
                await self._broadcast_updates({
                    'trends': trends,
                    'alerts': alerts,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Store metrics for historical analysis
                await self._persist_metrics()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
            
            await asyncio.sleep(interval)
    
    async def record_quality_event(
        self,
        agent_name: str,
        content_type: ContentType,
        metrics: QualityMetrics,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None
    ):
        """Record a quality event for monitoring"""
        try:
            event = {
                'timestamp': datetime.utcnow().isoformat(),
                'agent': agent_name,
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
            
            # Add to buffer for real-time processing
            self.metrics_buffer[agent_name].append(event)
            
            # Store in Redis for short-term access
            if self.redis_manager:
                await self.redis_manager.store_quality_event(event)
            
            # Store in ClickHouse for long-term analysis
            if self.clickhouse_manager:
                await self._store_in_clickhouse(event)
            
            # Check for immediate alerts
            await self._check_immediate_alerts(agent_name, metrics)
            
            logger.debug(f"Recorded quality event for {agent_name}: Score {metrics.overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error recording quality event: {str(e)}")
    
    async def _collect_metrics(self):
        """Collect metrics from various sources"""
        try:
            # Collect from Redis
            if self.redis_manager:
                redis_metrics = await self.redis_manager.get_recent_quality_metrics()
                for metric in redis_metrics:
                    agent = metric.get('agent', 'unknown')
                    self.metrics_buffer[agent].append(metric)
            
            # Collect from database if available
            if self.db_session:
                # Query recent agent runs for quality metrics
                pass  # Implement based on your database schema
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
    
    async def _analyze_trends(self) -> List[QualityTrend]:
        """Analyze trends in quality metrics"""
        trends = []
        
        try:
            for agent_name, events in self.metrics_buffer.items():
                if len(events) < 10:  # Need minimum data points
                    continue
                
                # Analyze quality score trend
                recent_scores = [e['quality_score'] for e in list(events)[-50:]]
                older_scores = [e['quality_score'] for e in list(events)[-100:-50]]
                
                if recent_scores and older_scores:
                    recent_avg = statistics.mean(recent_scores)
                    older_avg = statistics.mean(older_scores)
                    
                    change_pct = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
                    
                    trend_direction = "improving" if change_pct > 5 else "degrading" if change_pct < -5 else "stable"
                    
                    # Simple linear forecast
                    forecast = recent_avg + (recent_avg - older_avg) * 0.5
                    
                    trend = QualityTrend(
                        metric_type=MetricType.QUALITY_SCORE,
                        period="hour",
                        trend_direction=trend_direction,
                        change_percentage=change_pct,
                        current_average=recent_avg,
                        previous_average=older_avg,
                        forecast_next_period=min(1.0, max(0.0, forecast)),
                        confidence=0.7 if len(recent_scores) > 20 else 0.5
                    )
                    trends.append(trend)
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
        
        return trends
    
    async def _check_thresholds(self) -> List[QualityAlert]:
        """Check metrics against thresholds and generate alerts"""
        new_alerts = []
        
        try:
            for agent_name, events in self.metrics_buffer.items():
                if not events:
                    continue
                
                recent_events = list(events)[-20:]  # Check last 20 events
                
                # Check quality score
                avg_quality = statistics.mean([e['quality_score'] for e in recent_events])
                alert = self._create_alert_if_needed(
                    MetricType.QUALITY_SCORE,
                    avg_quality,
                    agent_name,
                    f"Average quality score {avg_quality:.2f} for {agent_name}"
                )
                if alert:
                    new_alerts.append(alert)
                
                # Check slop detection rate
                slop_count = sum(1 for e in recent_events if e['quality_level'] in ['poor', 'unacceptable'])
                slop_rate = slop_count / len(recent_events)
                alert = self._create_alert_if_needed(
                    MetricType.SLOP_DETECTION_RATE,
                    slop_rate,
                    agent_name,
                    f"Slop detection rate {slop_rate:.1%} for {agent_name}"
                )
                if alert:
                    new_alerts.append(alert)
                
                # Check for circular reasoning pattern
                circular_count = sum(1 for e in recent_events if e.get('circular_reasoning', False))
                if circular_count > 3:
                    alert = QualityAlert(
                        id=f"circular_{agent_name}_{datetime.utcnow().timestamp()}",
                        timestamp=datetime.utcnow(),
                        severity=AlertSeverity.WARNING,
                        metric_type=MetricType.QUALITY_SCORE,
                        agent=agent_name,
                        message=f"Repeated circular reasoning detected in {agent_name}",
                        current_value=circular_count,
                        threshold=3,
                        details={'recent_count': circular_count}
                    )
                    new_alerts.append(alert)
            
            # Store new alerts
            for alert in new_alerts:
                self.active_alerts[alert.id] = alert
                self.alert_history.append(alert)
            
        except Exception as e:
            logger.error(f"Error checking thresholds: {str(e)}")
        
        return new_alerts
    
    def _create_alert_if_needed(
        self,
        metric_type: MetricType,
        current_value: float,
        agent_name: str,
        message: str
    ) -> Optional[QualityAlert]:
        """Create an alert if threshold is exceeded"""
        if metric_type not in self.ALERT_THRESHOLDS:
            return None
        
        thresholds = self.ALERT_THRESHOLDS[metric_type]
        
        for severity in [AlertSeverity.CRITICAL, AlertSeverity.ERROR, AlertSeverity.WARNING]:
            if severity in thresholds:
                threshold = thresholds[severity]
                
                # For quality score, alert if below threshold
                # For rates, alert if above threshold
                if metric_type == MetricType.QUALITY_SCORE:
                    if current_value < threshold:
                        return QualityAlert(
                            id=f"{metric_type.value}_{agent_name}_{datetime.utcnow().timestamp()}",
                            timestamp=datetime.utcnow(),
                            severity=severity,
                            metric_type=metric_type,
                            agent=agent_name,
                            message=message,
                            current_value=current_value,
                            threshold=threshold
                        )
                else:
                    if current_value > threshold:
                        return QualityAlert(
                            id=f"{metric_type.value}_{agent_name}_{datetime.utcnow().timestamp()}",
                            timestamp=datetime.utcnow(),
                            severity=severity,
                            metric_type=metric_type,
                            agent=agent_name,
                            message=message,
                            current_value=current_value,
                            threshold=threshold
                        )
        
        return None
    
    async def _check_immediate_alerts(self, agent_name: str, metrics: QualityMetrics):
        """Check for immediate alert conditions"""
        # Critical quality failure
        if metrics.overall_score < 0.3:
            alert = QualityAlert(
                id=f"critical_quality_{agent_name}_{datetime.utcnow().timestamp()}",
                timestamp=datetime.utcnow(),
                severity=AlertSeverity.CRITICAL,
                metric_type=MetricType.QUALITY_SCORE,
                agent=agent_name,
                message=f"Critical quality failure in {agent_name}: Score {metrics.overall_score:.2f}",
                current_value=metrics.overall_score,
                threshold=0.3,
                details={'issues': metrics.issues}
            )
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            
            # Broadcast critical alert immediately
            await self._broadcast_critical_alert(alert)
    
    async def _update_agent_profiles(self):
        """Update quality profiles for each agent"""
        try:
            for agent_name, events in self.metrics_buffer.items():
                if not events:
                    continue
                
                recent_events = list(events)[-100:]  # Analyze last 100 events
                
                # Calculate statistics
                quality_scores = [e['quality_score'] for e in recent_events]
                quality_distribution = defaultdict(int)
                for e in recent_events:
                    quality_distribution[e['quality_level']] += 1
                
                # Identify issues
                issues = []
                if statistics.mean(quality_scores) < 0.5:
                    issues.append("Low average quality score")
                
                generic_phrase_avg = statistics.mean([e.get('generic_phrases', 0) for e in recent_events])
                if generic_phrase_avg > 2:
                    issues.append("High frequency of generic phrases")
                
                circular_count = sum(1 for e in recent_events if e.get('circular_reasoning', False))
                if circular_count > 5:
                    issues.append("Frequent circular reasoning")
                
                # Generate recommendations
                recommendations = []
                if statistics.mean(quality_scores) < 0.5:
                    recommendations.append("Review and enhance agent prompts for specificity")
                
                if any(e.get('hallucination_risk', 0) > 0.5 for e in recent_events):
                    recommendations.append("Implement fact-checking mechanisms")
                
                low_actionability = statistics.mean([e.get('actionability', 0) for e in recent_events]) < 0.5
                if low_actionability:
                    recommendations.append("Add concrete action steps to outputs")
                
                # Create or update profile
                profile = AgentQualityProfile(
                    agent_name=agent_name,
                    total_requests=len(recent_events),
                    average_quality_score=statistics.mean(quality_scores),
                    quality_distribution=dict(quality_distribution),
                    slop_detection_count=sum(1 for e in recent_events if e['quality_level'] in ['poor', 'unacceptable']),
                    retry_count=0,  # Would need to track this separately
                    fallback_count=0,  # Would need to track this separately
                    average_response_time=0,  # Would need to track this separately
                    last_updated=datetime.utcnow(),
                    issues=issues,
                    recommendations=recommendations
                )
                
                self.agent_profiles[agent_name] = profile
                
        except Exception as e:
            logger.error(f"Error updating agent profiles: {str(e)}")
    
    async def _broadcast_updates(self, updates: Dict[str, Any]):
        """Broadcast updates to subscribers"""
        if not self.subscribers:
            return
        
        try:
            # This would integrate with your WebSocket manager
            # For now, just log
            logger.debug(f"Broadcasting updates to {len(self.subscribers)} subscribers")
        except Exception as e:
            logger.error(f"Error broadcasting updates: {str(e)}")
    
    async def _broadcast_critical_alert(self, alert: QualityAlert):
        """Broadcast critical alerts immediately"""
        try:
            logger.critical(f"CRITICAL ALERT: {alert.message}")
            # Would integrate with WebSocket manager for real-time alerts
        except Exception as e:
            logger.error(f"Error broadcasting critical alert: {str(e)}")
    
    async def _persist_metrics(self):
        """Persist metrics for historical analysis"""
        try:
            if self.redis_manager:
                # Store aggregated metrics in Redis
                for agent_name, profile in self.agent_profiles.items():
                    await self.redis_manager.store_agent_profile(
                        agent_name,
                        asdict(profile)
                    )
            
            if self.clickhouse_manager:
                # Batch insert events to ClickHouse
                all_events = []
                for events in self.metrics_buffer.values():
                    all_events.extend(list(events)[-10:])  # Store recent events
                
                if all_events:
                    await self._batch_insert_clickhouse(all_events)
            
        except Exception as e:
            logger.error(f"Error persisting metrics: {str(e)}")
    
    async def _store_in_clickhouse(self, event: Dict[str, Any]):
        """Store individual event in ClickHouse"""
        if not self.clickhouse_manager:
            return
        
        try:
            # Format for ClickHouse table
            ch_event = {
                'timestamp': event['timestamp'],
                'agent_name': event['agent'],
                'content_type': event['content_type'],
                'quality_score': event['quality_score'],
                'quality_level': event['quality_level'],
                'metrics': json.dumps({
                    'specificity': event['specificity'],
                    'actionability': event['actionability'],
                    'quantification': event['quantification']
                }),
                'issues': json.dumps({
                    'generic_phrases': event['generic_phrases'],
                    'circular_reasoning': event['circular_reasoning'],
                    'hallucination_risk': event['hallucination_risk']
                }),
                'user_id': event.get('user_id', ''),
                'thread_id': event.get('thread_id', ''),
                'run_id': event.get('run_id', '')
            }
            
            await self.clickhouse_manager.insert_quality_event(ch_event)
            
        except Exception as e:
            logger.error(f"Error storing in ClickHouse: {str(e)}")
    
    async def _batch_insert_clickhouse(self, events: List[Dict[str, Any]]):
        """Batch insert events to ClickHouse"""
        if not self.clickhouse_manager or not events:
            return
        
        try:
            formatted_events = []
            for event in events:
                formatted_events.append({
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
                })
            
            await self.clickhouse_manager.batch_insert_quality_events(formatted_events)
            
        except Exception as e:
            logger.error(f"Error batch inserting to ClickHouse: {str(e)}")
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            # Overall statistics
            all_scores = []
            for events in self.metrics_buffer.values():
                all_scores.extend([e['quality_score'] for e in events])
            
            overall_stats = {
                'average_quality': statistics.mean(all_scores) if all_scores else 0,
                'total_events': len(all_scores),
                'active_alerts': len([a for a in self.active_alerts.values() if not a.resolved]),
                'critical_alerts': len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL and not a.resolved])
            }
            
            # Agent rankings
            agent_rankings = sorted(
                self.agent_profiles.items(),
                key=lambda x: x[1].average_quality_score,
                reverse=True
            )
            
            # Recent alerts
            recent_alerts = list(self.alert_history)[-10:]
            
            # Quality distribution
            quality_distribution = defaultdict(int)
            for events in self.metrics_buffer.values():
                for e in events:
                    quality_distribution[e['quality_level']] += 1
            
            return {
                'overall_stats': overall_stats,
                'agent_profiles': {name: asdict(profile) for name, profile in agent_rankings[:10]},
                'recent_alerts': [asdict(alert) for alert in recent_alerts],
                'quality_distribution': dict(quality_distribution),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return {}
    
    async def get_agent_report(self, agent_name: str, period_hours: int = 24) -> Dict[str, Any]:
        """Get detailed report for a specific agent"""
        try:
            if agent_name not in self.agent_profiles:
                return {'error': f'No data for agent {agent_name}'}
            
            profile = self.agent_profiles[agent_name]
            events = list(self.metrics_buffer[agent_name])
            
            # Time-based analysis
            cutoff_time = datetime.utcnow() - timedelta(hours=period_hours)
            recent_events = [e for e in events if datetime.fromisoformat(e['timestamp']) > cutoff_time]
            
            if not recent_events:
                return {'error': f'No recent data for agent {agent_name}'}
            
            # Calculate detailed metrics
            quality_scores = [e['quality_score'] for e in recent_events]
            
            hourly_averages = {}
            for e in recent_events:
                hour = datetime.fromisoformat(e['timestamp']).replace(minute=0, second=0, microsecond=0)
                if hour not in hourly_averages:
                    hourly_averages[hour] = []
                hourly_averages[hour].append(e['quality_score'])
            
            hourly_stats = {
                hour.isoformat(): {
                    'average': statistics.mean(scores),
                    'min': min(scores),
                    'max': max(scores),
                    'count': len(scores)
                }
                for hour, scores in hourly_averages.items()
            }
            
            return {
                'agent_name': agent_name,
                'period_hours': period_hours,
                'profile': asdict(profile),
                'statistics': {
                    'total_events': len(recent_events),
                    'average_quality': statistics.mean(quality_scores),
                    'median_quality': statistics.median(quality_scores),
                    'std_dev': statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0,
                    'min_quality': min(quality_scores),
                    'max_quality': max(quality_scores)
                },
                'hourly_stats': hourly_stats,
                'recent_issues': profile.issues,
                'recommendations': profile.recommendations,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting agent report: {str(e)}")
            return {'error': str(e)}
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            logger.info(f"Alert {alert_id} resolved")
            return True
        return False
    
    async def subscribe_to_updates(self, subscriber_id: str):
        """Subscribe to real-time quality updates"""
        self.subscribers.add(subscriber_id)
        logger.info(f"Subscriber {subscriber_id} added")
    
    async def unsubscribe_from_updates(self, subscriber_id: str):
        """Unsubscribe from real-time quality updates"""
        self.subscribers.discard(subscriber_id)
        logger.info(f"Subscriber {subscriber_id} removed")