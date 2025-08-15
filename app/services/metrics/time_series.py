"""
Time-series storage and real-time monitoring for corpus metrics
Handles time-based data storage, aggregation, and real-time updates
"""

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
import statistics
import json

from app.logging_config import central_logger
from app.schemas.Metrics import TimeSeriesPoint, MetricType
from app.redis_manager import RedisManager

logger = central_logger.get_logger(__name__)


class TimeSeriesStorage:
    """Manages time-series data storage and retrieval"""
    
    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        retention_hours: int = 168  # 7 days default
    ):
        self.redis_manager = redis_manager
        self.retention_hours = retention_hours
        self._local_storage = defaultdict(lambda: deque(maxlen=10000))
        self._aggregations = defaultdict(dict)
        self._subscribers = defaultdict(list)
    
    async def store_point(
        self,
        series_key: str,
        point: TimeSeriesPoint,
        persist_to_redis: bool = True
    ):
        """Store a time-series data point"""
        # Store locally
        self._local_storage[series_key].append(point)
        
        # Store in Redis if available
        if persist_to_redis and self.redis_manager:
            await self._store_redis_point(series_key, point)
        
        # Trigger real-time updates
        await self._notify_subscribers(series_key, point)
        
        logger.debug(f"Stored time-series point for {series_key}")
    
    async def _store_redis_point(self, series_key: str, point: TimeSeriesPoint):
        """Store point in Redis with TTL"""
        try:
            redis_key = f"timeseries:{series_key}"
            point_data = {
                "timestamp": point.timestamp.isoformat(),
                "value": point.value,
                "tags": json.dumps(point.tags)
            }
            
            # Use Redis sorted set with timestamp as score
            score = point.timestamp.timestamp()
            await self.redis_manager.zadd(redis_key, {json.dumps(point_data): score})
            
            # Set TTL for automatic cleanup
            await self.redis_manager.expire(redis_key, self.retention_hours * 3600)
        except Exception as e:
            logger.error(f"Failed to store point in Redis: {str(e)}")
    
    async def get_series(
        self,
        series_key: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[TimeSeriesPoint]:
        """Retrieve time-series data"""
        # Try Redis first if available
        if self.redis_manager:
            redis_data = await self._get_redis_series(series_key, start_time, end_time, limit)
            if redis_data:
                return redis_data
        
        # Fall back to local storage
        return await self._get_local_series(series_key, start_time, end_time, limit)
    
    async def _get_redis_series(
        self,
        series_key: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: Optional[int]
    ) -> List[TimeSeriesPoint]:
        """Get series data from Redis"""
        try:
            redis_key = f"timeseries:{series_key}"
            
            min_score = start_time.timestamp() if start_time else "-inf"
            max_score = end_time.timestamp() if end_time else "+inf"
            
            raw_data = await self.redis_manager.zrangebyscore(
                redis_key, min_score, max_score, withscores=True
            )
            
            points = []
            for data_json, score in raw_data:
                try:
                    data = json.loads(data_json)
                    point = TimeSeriesPoint(
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        value=data["value"],
                        tags=json.loads(data["tags"])
                    )
                    points.append(point)
                except Exception as e:
                    logger.warning(f"Failed to parse Redis point: {str(e)}")
                    continue
            
            # Apply limit if specified
            if limit:
                points = points[-limit:]
            
            return sorted(points, key=lambda x: x.timestamp)
        except Exception as e:
            logger.error(f"Failed to get series from Redis: {str(e)}")
            return []
    
    async def _get_local_series(
        self,
        series_key: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: Optional[int]
    ) -> List[TimeSeriesPoint]:
        """Get series data from local storage"""
        points = list(self._local_storage[series_key])
        
        # Filter by time range
        if start_time or end_time:
            filtered_points = []
            for point in points:
                if start_time and point.timestamp < start_time:
                    continue
                if end_time and point.timestamp > end_time:
                    continue
                filtered_points.append(point)
            points = filtered_points
        
        # Apply limit
        if limit:
            points = points[-limit:]
        
        return sorted(points, key=lambda x: x.timestamp)
    
    async def aggregate_series(
        self,
        series_key: str,
        aggregation_func: str,
        interval_minutes: int = 5,
        time_range_hours: int = 1
    ) -> List[TimeSeriesPoint]:
        """Aggregate time-series data by time intervals"""
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=time_range_hours)
        
        raw_points = await self.get_series(series_key, start_time, end_time)
        
        if not raw_points:
            return []
        
        # Group points by time intervals
        interval_seconds = interval_minutes * 60
        grouped_points = defaultdict(list)
        
        for point in raw_points:
            # Calculate interval bucket
            timestamp_seconds = int(point.timestamp.timestamp())
            interval_bucket = (timestamp_seconds // interval_seconds) * interval_seconds
            bucket_time = datetime.fromtimestamp(interval_bucket, UTC)
            
            grouped_points[bucket_time].append(point.value)
        
        # Apply aggregation function
        aggregated_points = []
        for bucket_time, values in grouped_points.items():
            aggregated_value = await self._apply_aggregation(values, aggregation_func)
            
            aggregated_points.append(TimeSeriesPoint(
                timestamp=bucket_time,
                value=aggregated_value,
                tags={"aggregation": aggregation_func, "interval_minutes": str(interval_minutes)}
            ))
        
        return sorted(aggregated_points, key=lambda x: x.timestamp)
    
    async def _apply_aggregation(self, values: List[float], func: str) -> float:
        """Apply aggregation function to values"""
        if not values:
            return 0.0
        
        if func == "mean" or func == "avg":
            return statistics.mean(values)
        elif func == "sum":
            return sum(values)
        elif func == "min":
            return min(values)
        elif func == "max":
            return max(values)
        elif func == "median":
            return statistics.median(values)
        elif func == "count":
            return len(values)
        else:
            logger.warning(f"Unknown aggregation function: {func}, using mean")
            return statistics.mean(values)
    
    def subscribe_to_updates(self, series_key: str, callback: Callable):
        """Subscribe to real-time updates for a series"""
        self._subscribers[series_key].append(callback)
        logger.debug(f"Added subscriber for series {series_key}")
    
    def unsubscribe_from_updates(self, series_key: str, callback: Callable):
        """Unsubscribe from real-time updates"""
        if callback in self._subscribers[series_key]:
            self._subscribers[series_key].remove(callback)
            logger.debug(f"Removed subscriber for series {series_key}")
    
    async def _notify_subscribers(self, series_key: str, point: TimeSeriesPoint):
        """Notify subscribers of new data points"""
        callbacks = self._subscribers.get(series_key, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(series_key, point)
                else:
                    callback(series_key, point)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {str(e)}")
    
    async def get_series_statistics(
        self,
        series_key: str,
        time_range_hours: int = 1
    ) -> Dict[str, Any]:
        """Get statistical summary of time-series data"""
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=time_range_hours)
        
        points = await self.get_series(series_key, start_time, end_time)
        
        if not points:
            return {"count": 0, "error": "No data available"}
        
        values = [point.value for point in points]
        
        stats = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "first_timestamp": points[0].timestamp.isoformat(),
            "last_timestamp": points[-1].timestamp.isoformat(),
            "time_span_minutes": (points[-1].timestamp - points[0].timestamp).total_seconds() / 60
        }
        
        if len(values) > 1:
            stats["std_dev"] = statistics.stdev(values)
            stats["variance"] = statistics.variance(values)
        
        return stats
    
    async def cleanup_old_data(self):
        """Clean up old time-series data"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=self.retention_hours)
        
        # Clean local storage
        for series_key, points in self._local_storage.items():
            filtered_points = deque(maxlen=points.maxlen)
            for point in points:
                if point.timestamp >= cutoff_time:
                    filtered_points.append(point)
            self._local_storage[series_key] = filtered_points
        
        # Redis cleanup is handled by TTL
        logger.info(f"Cleaned up time-series data older than {self.retention_hours} hours")
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get storage system status"""
        total_points = sum(len(points) for points in self._local_storage.values())
        
        return {
            "local_series_count": len(self._local_storage),
            "total_local_points": total_points,
            "redis_available": self.redis_manager is not None,
            "retention_hours": self.retention_hours,
            "active_subscribers": sum(len(subs) for subs in self._subscribers.values()),
            "memory_usage_estimate_mb": (total_points * 100) / (1024 * 1024)  # Rough estimate
        }