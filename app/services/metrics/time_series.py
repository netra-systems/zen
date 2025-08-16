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
from .time_series_aggregation import (
    aggregate_series_data, apply_aggregation_function, calculate_series_statistics,
    filter_points_by_time, calculate_storage_status
)

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
        return filter_points_by_time(points, start_time, end_time, limit)
    
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
        return await aggregate_series_data(raw_points, aggregation_func, interval_minutes)
    
    
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
        return await calculate_series_statistics(points)
    
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
        return calculate_storage_status(
            self._local_storage, self._subscribers, 
            self.retention_hours, self.redis_manager is not None
        )