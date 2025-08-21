"""Analytics metrics collector for comprehensive system analytics.

Business Value Justification (BVJ):
- Segment: Enterprise (advanced analytics and monitoring requirements)  
- Business Goal: Comprehensive analytics collection for business intelligence
- Value Impact: Enables data-driven optimization and performance insights
- Revenue Impact: Supports enterprise analytics needs and operational excellence
"""

import asyncio
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict, deque
import json

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class AnalyticsCollector:
    """Collects and aggregates analytics data across the system."""

    def __init__(self, max_buffer_size: int = 5000):
        self.max_buffer_size = max_buffer_size
        self.redis_client = None
        self._metrics_buffer = deque(maxlen=max_buffer_size)
        self._aggregation_cache = defaultdict(lambda: defaultdict(int))
        self._event_counts = defaultdict(int)

    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client

    async def collect_user_interaction(
        self, 
        user_id: str, 
        interaction_type: str,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> None:
        """Collect user interaction analytics."""
        try:
            event_data = {
                "event_type": "user_interaction",
                "user_id": user_id,
                "tenant_id": tenant_id,
                "interaction_type": interaction_type,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            redis = await self._get_redis()
            analytics_key = f"analytics:interactions:{datetime.now(UTC).strftime('%Y%m%d')}"
            await redis.lpush(analytics_key, json.dumps(event_data))
            await redis.expire(analytics_key, 3600 * 24 * 90)
            
            # Update cache
            self._event_counts[interaction_type] += 1
            self._metrics_buffer.append(event_data)
            
            logger.debug(f"Collected user interaction: {interaction_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Error collecting user interaction: {str(e)}")

    async def collect_system_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
        tenant_id: Optional[str] = None
    ) -> None:
        """Collect system-level metrics."""
        try:
            metric_data = {
                "event_type": "system_metric",
                "metric_name": metric_name,
                "value": value,
                "tags": tags or {},
                "tenant_id": tenant_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            redis = await self._get_redis()
            metrics_key = f"analytics:metrics:{datetime.now(UTC).strftime('%Y%m%d')}"
            await redis.lpush(metrics_key, json.dumps(metric_data))
            await redis.expire(metrics_key, 3600 * 24 * 30)  # 30 days for metrics
            
            # Update aggregation cache
            self._aggregation_cache[metric_name]["count"] += 1
            self._aggregation_cache[metric_name]["total"] += value
            
            logger.debug(f"Collected system metric: {metric_name} = {value}")
        except Exception as e:
            logger.error(f"Error collecting system metric: {str(e)}")

    async def collect_business_event(
        self,
        event_name: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> None:
        """Collect business-level events for analytics."""
        try:
            business_event = {
                "event_type": "business_event", 
                "event_name": event_name,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "event_data": event_data,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            redis = await self._get_redis()
            events_key = f"analytics:business_events:{datetime.now(UTC).strftime('%Y%m%d')}"
            await redis.lpush(events_key, json.dumps(business_event))
            await redis.expire(events_key, 3600 * 24 * 365)  # 1 year for business events
            
            self._event_counts[event_name] += 1
            
            logger.debug(f"Collected business event: {event_name}")
        except Exception as e:
            logger.error(f"Error collecting business event: {str(e)}")

    async def get_interaction_summary(
        self, 
        days: int = 7,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary of user interactions."""
        try:
            redis = await self._get_redis()
            interaction_counts = defaultdict(int)
            
            for i in range(days):
                date = datetime.now(UTC) - timedelta(days=i)
                daily_key = f"analytics:interactions:{date.strftime('%Y%m%d')}"
                interactions = await redis.lrange(daily_key, 0, -1)
                
                for interaction_raw in interactions:
                    try:
                        interaction = json.loads(interaction_raw)
                        # Filter by tenant if specified
                        if tenant_id and interaction.get("tenant_id") != tenant_id:
                            continue
                        interaction_counts[interaction["interaction_type"]] += 1
                    except Exception:
                        continue
            
            total_interactions = sum(interaction_counts.values())
            
            return {
                "period_days": days,
                "total_interactions": total_interactions,
                "interaction_breakdown": dict(interaction_counts),
                "tenant_id": tenant_id
            }
        except Exception as e:
            logger.error(f"Error getting interaction summary: {str(e)}")
            return {"period_days": days, "total_interactions": 0, "interaction_breakdown": {}}

    async def get_metric_aggregates(
        self,
        metric_name: str,
        days: int = 7,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregated metrics for a specific metric."""
        try:
            redis = await self._get_redis()
            values = []
            
            for i in range(days):
                date = datetime.now(UTC) - timedelta(days=i)
                daily_key = f"analytics:metrics:{date.strftime('%Y%m%d')}"
                metrics = await redis.lrange(daily_key, 0, -1)
                
                for metric_raw in metrics:
                    try:
                        metric = json.loads(metric_raw)
                        if metric["metric_name"] == metric_name:
                            # Filter by tenant if specified  
                            if tenant_id and metric.get("tenant_id") != tenant_id:
                                continue
                            values.append(metric["value"])
                    except Exception:
                        continue
            
            if not values:
                return {
                    "metric_name": metric_name,
                    "count": 0,
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "sum": 0
                }
            
            return {
                "metric_name": metric_name,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "sum": sum(values),
                "tenant_id": tenant_id
            }
        except Exception as e:
            logger.error(f"Error getting metric aggregates: {str(e)}")
            return {"metric_name": metric_name, "count": 0, "min": 0, "max": 0, "avg": 0, "sum": 0}

    async def get_business_event_counts(
        self,
        event_name: Optional[str] = None,
        days: int = 7,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get counts of business events."""
        try:
            redis = await self._get_redis()
            event_counts = defaultdict(int)
            
            for i in range(days):
                date = datetime.now(UTC) - timedelta(days=i)
                daily_key = f"analytics:business_events:{date.strftime('%Y%m%d')}"
                events = await redis.lrange(daily_key, 0, -1)
                
                for event_raw in events:
                    try:
                        event = json.loads(event_raw)
                        # Filter by specific event name if specified
                        if event_name and event["event_name"] != event_name:
                            continue
                        # Filter by tenant if specified
                        if tenant_id and event.get("tenant_id") != tenant_id:
                            continue
                        event_counts[event["event_name"]] += 1
                    except Exception:
                        continue
            
            return {
                "period_days": days,
                "event_counts": dict(event_counts),
                "total_events": sum(event_counts.values()),
                "filtered_by_event": event_name,
                "tenant_id": tenant_id
            }
        except Exception as e:
            logger.error(f"Error getting business event counts: {str(e)}")
            return {"period_days": days, "event_counts": {}, "total_events": 0}

    def get_cached_metrics(self) -> Dict[str, Any]:
        """Get cached metrics and event counts."""
        return {
            "event_counts": dict(self._event_counts),
            "aggregation_cache": {
                metric_name: {
                    "count": data["count"],
                    "average": data["total"] / data["count"] if data["count"] > 0 else 0
                }
                for metric_name, data in self._aggregation_cache.items()
            },
            "buffer_size": len(self._metrics_buffer)
        }

    async def flush_buffer(self) -> None:
        """Flush any cached data (for testing or shutdown)."""
        try:
            logger.info("Flushing analytics collector buffer")
            self._metrics_buffer.clear()
            self._aggregation_cache.clear()
            self._event_counts.clear()
        except Exception as e:
            logger.error(f"Error flushing analytics buffer: {str(e)}")