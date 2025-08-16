"""
Time Series Aggregation Functions

Extracted from time_series.py to maintain 300-line limit.
Provides aggregation and statistical analysis for time-series data.
"""

import statistics
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from app.schemas.Metrics import TimeSeriesPoint
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def aggregate_series_data(
    raw_points: List[TimeSeriesPoint],
    aggregation_func: str,
    interval_minutes: int = 5
) -> List[TimeSeriesPoint]:
    """Aggregate time-series data by time intervals"""
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
        aggregated_value = await apply_aggregation_function(values, aggregation_func)
        
        aggregated_points.append(TimeSeriesPoint(
            timestamp=bucket_time,
            value=aggregated_value,
            tags={"aggregation": aggregation_func, "interval_minutes": str(interval_minutes)}
        ))
    
    return sorted(aggregated_points, key=lambda x: x.timestamp)


async def apply_aggregation_function(values: List[float], func: str) -> float:
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


async def calculate_series_statistics(
    points: List[TimeSeriesPoint]
) -> Dict[str, Any]:
    """Get statistical summary of time-series data"""
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


def filter_points_by_time(
    points: List[TimeSeriesPoint],
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = None
) -> List[TimeSeriesPoint]:
    """Filter points by time range and apply limit"""
    filtered_points = points
    
    # Filter by time range
    if start_time or end_time:
        filtered_points = []
        for point in points:
            if start_time and point.timestamp < start_time:
                continue
            if end_time and point.timestamp > end_time:
                continue
            filtered_points.append(point)
    
    # Apply limit
    if limit:
        filtered_points = filtered_points[-limit:]
    
    return sorted(filtered_points, key=lambda x: x.timestamp)


def calculate_storage_status(local_storage: dict, subscribers: dict, retention_hours: int, redis_available: bool) -> Dict[str, Any]:
    """Calculate storage system status"""
    total_points = sum(len(points) for points in local_storage.values())
    
    return {
        "local_series_count": len(local_storage),
        "total_local_points": total_points,
        "redis_available": redis_available,
        "retention_hours": retention_hours,
        "active_subscribers": sum(len(subs) for subs in subscribers.values()),
        "memory_usage_estimate_mb": (total_points * 100) / (1024 * 1024)  # Rough estimate
    }