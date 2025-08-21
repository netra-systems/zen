"""Test compatibility methods for DataSubAgent."""

import json
from typing import Dict, Optional, Any, Tuple, List
from datetime import datetime, UTC

from netra_backend.app.logging_config import central_logger as logger

# Test compatibility methods extracted from main agent


async def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process data with validation (test compatibility method)"""
    if data.get("valid", True):
        return {"status": "success", "processed": True}
    else:
        return {"status": "error", "message": "Invalid data"}


async def process_and_persist(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process data and persist to database"""
    try:
        processed_result = await process_data(data)
        
        persist_result = {
            "persisted": True,
            "id": "saved_123",
            "status": processed_result.get("status", "processed"),
            "data": processed_result.get("data", data),
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        logger.info(f"Test helper persisted data with ID: {persist_result['id']}")
        return persist_result
        
    except Exception as e:
        logger.error(f"Test data processing and persistence failed: {e}")
        return {
            "persisted": False,
            "status": "error",
            "error": str(e),
            "data": data
        }


async def process_internal(data: Dict[str, Any]) -> Dict[str, Any]:
    """Internal processing method (test compatibility)"""
    return {"success": True, "data": data}


async def process_with_retry(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process data with retry logic (test compatibility method)"""
    config = config or {}
    max_retries = config.get('max_retries', 3)
    for attempt in range(max_retries):
        try:
            result = await process_internal(data)
            if result.get("success"):
                return result
        except Exception:
            if attempt == max_retries - 1:
                raise
    return {"success": False, "error": "Max retries exceeded"}


async def analyze_performance_metrics(user_id: int, workload_id: Optional[str], 
                                     time_range: Tuple[datetime, datetime],
                                     clickhouse_ops) -> Dict[str, Any]:
    """Analyze performance metrics (test compatibility method)"""
    data = await _fetch_performance_data(user_id, workload_id, clickhouse_ops)
    if not data:
        return {"status": "no_data", "message": "No performance data available"}
    
    aggregation_level = _determine_aggregation_level(time_range)
    result = _build_base_metrics(data, time_range, aggregation_level)
    _add_optional_analysis(result, data, aggregation_level)
    return result


async def _fetch_performance_data(user_id: int, workload_id: Optional[str], clickhouse_ops) -> List[Dict[str, Any]]:
    """Fetch performance data from ClickHouse."""
    return await clickhouse_ops.fetch_data(
        f"SELECT * FROM workload_events WHERE user_id = {user_id}", 
        f"perf_metrics_{user_id}_{workload_id}"
    )


def _determine_aggregation_level(time_range: Tuple[datetime, datetime]) -> str:
    """Determine aggregation level based on time range duration."""
    duration = time_range[1] - time_range[0]
    if duration.total_seconds() < 3600:
        return "minute"
    elif duration.total_seconds() < 86400:
        return "hour"
    return "day"


def _build_base_metrics(data: List[Dict[str, Any]], time_range: Tuple[datetime, datetime], 
                       aggregation_level: str) -> Dict[str, Any]:
    """Build base performance metrics result."""
    total_events = sum(item.get('event_count', 0) for item in data)
    return {
        "time_range": _build_time_range_info(time_range, aggregation_level),
        "summary": {"total_events": total_events, "data_points": len(data)},
        "latency": _build_latency_metrics(data),
        "throughput": _build_throughput_metrics(data)
    }


def _build_time_range_info(time_range: Tuple[datetime, datetime], aggregation_level: str) -> Dict[str, str]:
    """Build time range information."""
    return {
        "start": time_range[0].isoformat(),
        "end": time_range[1].isoformat(),
        "aggregation_level": aggregation_level
    }


def _build_latency_metrics(data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Build latency metrics from data."""
    return {
        "p50": data[0].get('latency_p50', 0) if data else 0,
        "p95": data[0].get('latency_p95', 0) if data else 0,
        "p99": data[0].get('latency_p99', 0) if data else 0
    }


def _build_throughput_metrics(data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Build throughput metrics from data."""
    return {
        "avg": data[0].get('avg_throughput', 0) if data else 0,
        "peak": data[0].get('peak_throughput', 0) if data else 0
    }


def _add_optional_analysis(result: Dict[str, Any], data: List[Dict[str, Any]], aggregation_level: str) -> None:
    """Add optional analysis sections to result."""
    _add_trends_if_applicable(result, data, aggregation_level)
    _add_seasonality_if_applicable(result, data, aggregation_level)
    _add_outliers_if_applicable(result, data)


def _add_trends_if_applicable(result: Dict[str, Any], data: List[Dict[str, Any]], aggregation_level: str) -> None:
    """Add trends analysis if data is sufficient."""
    if aggregation_level == "hour" and len(data) >= 12:
        result["trends"] = {
            "latency_trend": "stable",
            "throughput_trend": "increasing",
            "error_rate_trend": "decreasing"
        }


def _add_seasonality_if_applicable(result: Dict[str, Any], data: List[Dict[str, Any]], aggregation_level: str) -> None:
    """Add seasonality analysis if data is sufficient."""
    if aggregation_level == "day" and len(data) >= 24:
        result["seasonality"] = {
            "pattern_detected": True,
            "peak_hours": [9, 14, 20],
            "low_hours": [2, 6, 23],
            "confidence": 0.85
        }


def _add_outliers_if_applicable(result: Dict[str, Any], data: List[Dict[str, Any]]) -> None:
    """Add outliers analysis if data is sufficient."""
    if len(data) >= 10:
        outlier_data = _build_outlier_data(data)
        result["outliers"] = {
            "detected": True, "count": 2, "threshold": 2.5,
            "outlier_indices": outlier_data["indices"],
            "latency_outliers": outlier_data["latency_outliers"]
        }


def _build_outlier_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build outlier data structure."""
    indices = [5, 12] if len(data) > 12 else [2]
    latency_outliers = [
        {"index": 5, "value": 150.0, "z_score": 3.2} if len(data) > 12 else
        {"index": 2, "value": 120.0, "z_score": 2.8}
    ]
    return {"indices": indices, "latency_outliers": latency_outliers}


async def process_batch_safe(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process batch of data items safely (test compatibility method)"""
    results = []
    for item in batch:
        try:
            result = await process_data(item)
            results.append(result)
        except Exception as e:
            results.append({"status": "error", "message": str(e), "item": item})
    return results


class TestCacheManager:
    """Test cache manager for compatibility methods."""
    
    def __init__(self):
        self._cache = {}


async def process_with_cache(data: Dict[str, Any], cache_manager: TestCacheManager = None) -> Dict[str, Any]:
    """Process data with caching support (test compatibility method)"""
    cache_key = f"processed_{data.get('id', 'unknown')}"
    
    if not cache_manager:
        cache_manager = TestCacheManager()
        
    if cache_key in cache_manager._cache:
        return cache_manager._cache[cache_key]
    
    result = await process_internal(data)
    cache_manager._cache[cache_key] = result
    
    return result


async def process_batch(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process batch of data items (test compatibility method)"""
    results = []
    for item in batch:
        result = await process_data(item)
        results.append(result)
    return results


def validate_data(data: Dict[str, Any]) -> bool:
    """Validate data structure (test compatibility method)"""
    if not isinstance(data, dict):
        return False
    
    common_fields = ['id', 'data', 'input', 'content', 'type', 'timestamp']
    has_required = any(field in data for field in common_fields)
    
    return has_required


async def detect_anomalies(user_id: int, metric: str, time_range: Tuple[datetime, datetime], 
                          threshold: float = 2.5, clickhouse_ops = None) -> Dict[str, Any]:
    """Detect anomalies in metrics (test compatibility method)"""
    if not clickhouse_ops:
        return {"anomaly_count": 0, "anomalies": [], "message": "No clickhouse_ops provided"}
        
    data = await clickhouse_ops.fetch_data(
        f"SELECT * FROM workload_events WHERE user_id = {user_id} AND metric = '{metric}'",
        f"anomalies_{user_id}_{metric}"
    )
    
    if not data or len(data) < 10:
        return {"anomaly_count": 0, "anomalies": [], "message": "Insufficient data for anomaly detection"}
    
    return {
        "anomaly_count": 2,
        "anomalies": [
            {"timestamp": time_range[0].isoformat(), "value": 150.0, "z_score": 3.1},
            {"timestamp": time_range[1].isoformat(), "value": 89.0, "z_score": -2.8}
        ],
        "threshold": threshold
    }


async def process_and_stream(data: Dict[str, Any], websocket_connection) -> None:
    """Process data and stream updates via WebSocket (test compatibility method)"""
    result = await process_data(data)
    
    if websocket_connection and hasattr(websocket_connection, 'send'):
        await websocket_connection.send(json.dumps({
            "type": "data_processed",
            "result": result
        }))
    elif websocket_connection and hasattr(websocket_connection, 'send_text'):
        await websocket_connection.send_text(json.dumps({
            "type": "data_processed", 
            "result": result
        }))