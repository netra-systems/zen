"""
Time Series Aggregation Functions

Extracted from time_series.py to maintain 450-line limit.
Provides aggregation and statistical analysis for time-series data.
"""

import statistics
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Any, Optional
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
    grouped_points = _group_points_by_intervals(raw_points, interval_minutes)
    aggregated_points = await _create_aggregated_points(grouped_points, aggregation_func, interval_minutes)
    return sorted(aggregated_points, key=lambda x: x.timestamp)

def _group_points_by_intervals(raw_points: List[TimeSeriesPoint], interval_minutes: int) -> Dict[datetime, List[float]]:
    """Group time series points by time intervals."""
    interval_seconds = interval_minutes * 60
    grouped_points = defaultdict(list)
    for point in raw_points:
        bucket_time = _calculate_bucket_time(point, interval_seconds)
        grouped_points[bucket_time].append(point.value)
    return grouped_points

def _calculate_bucket_time(point: TimeSeriesPoint, interval_seconds: int) -> datetime:
    """Calculate time bucket for aggregation interval."""
    timestamp_seconds = int(point.timestamp.timestamp())
    interval_bucket = (timestamp_seconds // interval_seconds) * interval_seconds
    return datetime.fromtimestamp(interval_bucket, UTC)

async def _create_aggregated_points(grouped_points: Dict[datetime, List[float]], aggregation_func: str, interval_minutes: int) -> List[TimeSeriesPoint]:
    """Create aggregated time series points from grouped data."""
    aggregated_points = []
    for bucket_time, values in grouped_points.items():
        aggregated_value = await apply_aggregation_function(values, aggregation_func)
        point = _create_aggregated_point(bucket_time, aggregated_value, aggregation_func, interval_minutes)
        aggregated_points.append(point)
    return aggregated_points

def _create_aggregated_point(bucket_time: datetime, aggregated_value: float, aggregation_func: str, interval_minutes: int) -> TimeSeriesPoint:
    """Create single aggregated time series point."""
    return TimeSeriesPoint(
        timestamp=bucket_time,
        value=aggregated_value,
        tags={"aggregation": aggregation_func, "interval_minutes": str(interval_minutes)}
    )


async def apply_aggregation_function(values: List[float], func: str) -> float:
    """Apply aggregation function to values"""
    if not values:
        return 0.0
    result = _get_aggregation_result(values, func)
    if result is None:
        result = _handle_unknown_function(values, func)
    return result

def _get_aggregation_result(values: List[float], func: str) -> Optional[float]:
    """Get aggregation result for known functions."""
    function_map = _get_function_mapping()
    aggregation_func = function_map.get(func)
    return aggregation_func(values) if aggregation_func else None

def _get_function_mapping() -> Dict[str, callable]:
    """Get mapping of function names to implementation."""
    return {
        "mean": statistics.mean, "avg": statistics.mean,
        "sum": sum, "min": min, "max": max,
        "median": statistics.median, "count": len
    }

def _handle_unknown_function(values: List[float], func: str) -> float:
    """Handle unknown aggregation function."""
    logger.warning(f"Unknown aggregation function: {func}, using mean")
    return statistics.mean(values)


async def calculate_series_statistics(
    points: List[TimeSeriesPoint]
) -> Dict[str, Any]:
    """Get statistical summary of time-series data"""
    if not points:
        return {"count": 0, "error": "No data available"}
    values = [point.value for point in points]
    stats = _calculate_basic_statistics(values, points)
    _add_variance_statistics_if_needed(stats, values)
    return stats

def _calculate_basic_statistics(values: List[float], points: List[TimeSeriesPoint]) -> Dict[str, Any]:
    """Calculate basic statistical measures."""
    basic_stats = _get_basic_value_statistics(values)
    time_stats = _get_time_span_statistics(points)
    return {**basic_stats, **time_stats}

def _get_basic_value_statistics(values: List[float]) -> Dict[str, Any]:
    """Get basic value statistics."""
    return {
        "count": len(values), "min": min(values), "max": max(values),
        "mean": statistics.mean(values), "median": statistics.median(values)
    }

def _get_time_span_statistics(points: List[TimeSeriesPoint]) -> Dict[str, Any]:
    """Get time span statistics."""
    time_span_minutes = (points[-1].timestamp - points[0].timestamp).total_seconds() / 60
    return {
        "first_timestamp": points[0].timestamp.isoformat(),
        "last_timestamp": points[-1].timestamp.isoformat(),
        "time_span_minutes": time_span_minutes
    }

def _add_variance_statistics_if_needed(stats: Dict[str, Any], values: List[float]) -> None:
    """Add variance statistics if enough data points."""
    if len(values) > 1:
        stats["std_dev"] = statistics.stdev(values)
        stats["variance"] = statistics.variance(values)


def filter_points_by_time(
    points: List[TimeSeriesPoint],
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = None
) -> List[TimeSeriesPoint]:
    """Filter points by time range and apply limit"""
    filtered_points = _apply_time_range_filter(points, start_time, end_time)
    limited_points = _apply_limit_filter(filtered_points, limit)
    return sorted(limited_points, key=lambda x: x.timestamp)

def _apply_time_range_filter(points: List[TimeSeriesPoint], start_time: datetime, end_time: datetime) -> List[TimeSeriesPoint]:
    """Apply time range filtering to points."""
    if not start_time and not end_time:
        return points
    return [point for point in points if _point_in_time_range(point, start_time, end_time)]

def _point_in_time_range(point: TimeSeriesPoint, start_time: datetime, end_time: datetime) -> bool:
    """Check if point is within time range."""
    if start_time and point.timestamp < start_time:
        return False
    if end_time and point.timestamp > end_time:
        return False
    return True

def _apply_limit_filter(filtered_points: List[TimeSeriesPoint], limit: int) -> List[TimeSeriesPoint]:
    """Apply limit filter to points."""
    if limit:
        return filtered_points[-limit:]
    return filtered_points


def calculate_storage_status(local_storage: dict, subscribers: dict, retention_hours: int, redis_available: bool) -> Dict[str, Any]:
    """Calculate storage system status"""
    storage_stats = _calculate_storage_statistics(local_storage)
    subscriber_stats = _calculate_subscriber_statistics(subscribers)
    system_stats = _calculate_system_statistics(retention_hours, redis_available)
    return {**storage_stats, **subscriber_stats, **system_stats}

def _calculate_storage_statistics(local_storage: dict) -> Dict[str, Any]:
    """Calculate storage-related statistics."""
    total_points = sum(len(points) for points in local_storage.values())
    memory_usage_mb = (total_points * 100) / (1024 * 1024)  # Rough estimate
    return {
        "local_series_count": len(local_storage),
        "total_local_points": total_points,
        "memory_usage_estimate_mb": memory_usage_mb
    }

def _calculate_subscriber_statistics(subscribers: dict) -> Dict[str, int]:
    """Calculate subscriber-related statistics."""
    return {
        "active_subscribers": sum(len(subs) for subs in subscribers.values())
    }

def _calculate_system_statistics(retention_hours: int, redis_available: bool) -> Dict[str, Any]:
    """Calculate system-related statistics."""
    return {
        "retention_hours": retention_hours,
        "redis_available": redis_available
    }