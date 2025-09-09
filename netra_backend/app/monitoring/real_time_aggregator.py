"""Real-Time Aggregator - SSOT for Live Metrics Aggregation

This module provides real-time metrics aggregation capabilities for the Netra platform,
enabling live business intelligence and performance monitoring.

Business Value Justification (BVJ):
- Segment: Platform/Internal + All customer segments
- Business Goal: Enable data-driven optimization and proactive issue detection  
- Value Impact: Real-time metrics prevent outages and enable performance optimization
- Strategic Impact: Foundation for SLA compliance and customer transparency

SSOT Compliance:
- Integrates with existing monitoring infrastructure
- Uses standardized metric data structures
- Provides unified interface for metrics aggregation
"""

import asyncio
import statistics
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class AggregationType(Enum):
    """Types of aggregation functions."""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    PERCENTILE = "percentile"
    RATE = "rate"


@dataclass
class MetricPoint:
    """Individual metric data point."""
    timestamp: datetime
    value: Union[int, float]
    tags: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedMetric:
    """Aggregated metric result."""
    metric_name: str
    aggregation_type: str
    value: Union[int, float]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    sample_count: int = 0


@dataclass
class BusinessKPI:
    """Business Key Performance Indicator."""
    kpi_name: str
    value: Union[int, float]
    unit: str
    timestamp: datetime
    target_value: Optional[Union[int, float]] = None
    variance: Optional[float] = None
    trend: str = "stable"  # "increasing", "decreasing", "stable"


class RealTimeAggregator:
    """SSOT Real-Time Metrics Aggregator.
    
    This class provides comprehensive real-time metrics aggregation capabilities,
    enabling live business intelligence and performance monitoring across the
    entire Netra platform.
    
    Key Features:
    - Real-time metric aggregation with various functions (sum, avg, min, max, etc.)
    - Business KPI calculation and tracking
    - Windowed aggregations with configurable time windows
    - High-performance metric storage and retrieval
    - Integration with existing monitoring infrastructure
    """
    
    def __init__(self, redis_prefix: str = "netra:metrics:aggregated"):
        """Initialize the real-time aggregator."""
        self.redis_prefix = redis_prefix
        self.metric_buffers = defaultdict(lambda: deque(maxlen=10000))  # Ring buffers
        self.aggregation_cache = {}
        self.business_kpi_cache = {}
        logger.info("RealTimeAggregator initialized for live metrics processing")
    
    async def aggregate_metrics(
        self,
        metrics: List[MetricPoint],
        aggregation_type: str = "average",
        time_window_seconds: int = 60,
        group_by_tags: Optional[List[str]] = None
    ) -> List[AggregatedMetric]:
        """Aggregate a list of metrics with specified aggregation function.
        
        Args:
            metrics: List of metric points to aggregate
            aggregation_type: Type of aggregation (sum, average, min, max, count)
            time_window_seconds: Time window for aggregation in seconds
            group_by_tags: Optional tags to group metrics by
            
        Returns:
            List of aggregated metrics
        """
        if not metrics:
            return []
        
        # Group metrics by name and specified tags
        grouped_metrics = defaultdict(list)
        
        for metric in metrics:
            # Create grouping key
            group_key = f"metric_aggregation"
            if hasattr(metric, 'metric_type'):
                group_key = metric.metric_type
            elif hasattr(metric, 'name'):
                group_key = metric.name
                
            if group_by_tags:
                tag_parts = []
                for tag in group_by_tags:
                    if tag in metric.tags:
                        tag_parts.append(f"{tag}:{metric.tags[tag]}")
                if tag_parts:
                    group_key += f":{':'.join(tag_parts)}"
            
            grouped_metrics[group_key].append(metric)
        
        # Perform aggregation for each group
        results = []
        current_time = datetime.now(timezone.utc)
        window_start = current_time - timedelta(seconds=time_window_seconds)
        
        for group_key, group_metrics in grouped_metrics.items():
            # Filter metrics within time window
            windowed_metrics = [
                m for m in group_metrics 
                if m.timestamp >= window_start
            ]
            
            if not windowed_metrics:
                continue
            
            # Extract values for aggregation
            values = [m.value for m in windowed_metrics]
            
            # Perform aggregation
            aggregated_value = await self._perform_aggregation(values, aggregation_type)
            
            # Combine tags from all metrics in group
            combined_tags = {}
            for m in windowed_metrics:
                combined_tags.update(m.tags)
            
            # Create aggregated metric
            aggregated = AggregatedMetric(
                metric_name=group_key,
                aggregation_type=aggregation_type,
                value=aggregated_value,
                timestamp=current_time,
                tags=combined_tags,
                window_start=window_start,
                window_end=current_time,
                sample_count=len(windowed_metrics)
            )
            
            results.append(aggregated)
        
        # Cache results in Redis for real services
        try:
            cache_key = f"{self.redis_prefix}:aggregation:{int(current_time.timestamp())}"
            cache_data = {
                "aggregation_type": aggregation_type,
                "time_window_seconds": time_window_seconds,
                "results_count": len(results),
                "results": [
                    {
                        "metric_name": r.metric_name,
                        "value": r.value,
                        "sample_count": r.sample_count,
                        "timestamp": r.timestamp.isoformat()
                    } for r in results
                ]
            }
            await redis_manager.set_json(cache_key, cache_data, expire=3600)
            logger.debug(f"Aggregated {len(results)} metric groups with {aggregation_type}")
        except Exception as e:
            logger.warning(f"Failed to cache aggregation results: {e}")
        
        return results
    
    async def _perform_aggregation(
        self, 
        values: List[Union[int, float]], 
        aggregation_type: str
    ) -> Union[int, float]:
        """Perform the actual aggregation calculation.
        
        Args:
            values: List of numeric values to aggregate
            aggregation_type: Type of aggregation to perform
            
        Returns:
            Aggregated value
        """
        if not values:
            return 0
        
        if aggregation_type == "sum":
            return sum(values)
        elif aggregation_type == "average":
            return statistics.mean(values)
        elif aggregation_type == "min":
            return min(values)
        elif aggregation_type == "max":
            return max(values)
        elif aggregation_type == "count":
            return len(values)
        elif aggregation_type == "median":
            return statistics.median(values)
        elif aggregation_type.startswith("p"):
            # Percentile (e.g., "p95", "p99")
            try:
                percentile = int(aggregation_type[1:])
                return self._calculate_percentile(values, percentile)
            except ValueError:
                logger.warning(f"Invalid percentile format: {aggregation_type}")
                return statistics.mean(values)
        else:
            logger.warning(f"Unknown aggregation type: {aggregation_type}, using average")
            return statistics.mean(values)
    
    def _calculate_percentile(
        self, 
        values: List[Union[int, float]], 
        percentile: int
    ) -> Union[int, float]:
        """Calculate percentile for a list of values.
        
        Args:
            values: List of numeric values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not values:
            return 0
            
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_values):
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        else:
            return sorted_values[f]
    
    async def calculate_business_kpis(
        self,
        metrics: List[MetricPoint],
        kpi_definitions: Dict[str, Dict[str, Any]]
    ) -> List[BusinessKPI]:
        """Calculate business Key Performance Indicators from metrics.
        
        Args:
            metrics: List of metric points to analyze
            kpi_definitions: KPI calculation definitions
            
        Returns:
            List of calculated business KPIs
        """
        if not metrics or not kpi_definitions:
            return []
        
        results = []
        current_time = datetime.now(timezone.utc)
        
        for kpi_name, kpi_config in kpi_definitions.items():
            try:
                # Extract KPI configuration
                metric_filter = kpi_config.get("metric_filter", {})
                calculation = kpi_config.get("calculation", "sum")
                unit = kpi_config.get("unit", "count")
                target_value = kpi_config.get("target")
                
                # Filter metrics for this KPI
                filtered_metrics = self._filter_metrics(metrics, metric_filter)
                
                if not filtered_metrics:
                    continue
                
                # Calculate KPI value
                values = [m.value for m in filtered_metrics]
                kpi_value = await self._perform_aggregation(values, calculation)
                
                # Calculate variance from target if target is defined
                variance = None
                if target_value is not None:
                    variance = ((kpi_value - target_value) / target_value) * 100
                
                # Determine trend (simplified - would use historical data in production)
                trend = "stable"
                if variance is not None:
                    if variance > 5:
                        trend = "increasing"
                    elif variance < -5:
                        trend = "decreasing"
                
                # Create Business KPI
                kpi = BusinessKPI(
                    kpi_name=kpi_name,
                    value=kpi_value,
                    unit=unit,
                    timestamp=current_time,
                    target_value=target_value,
                    variance=variance,
                    trend=trend
                )
                
                results.append(kpi)
                logger.debug(f"Calculated KPI {kpi_name}: {kpi_value} {unit}")
                
            except Exception as e:
                logger.error(f"Failed to calculate KPI {kpi_name}: {e}")
                continue
        
        # Cache KPIs in Redis
        try:
            cache_key = f"{self.redis_prefix}:kpis:{int(current_time.timestamp())}"
            cache_data = {
                "timestamp": current_time.isoformat(),
                "kpis_count": len(results),
                "kpis": [
                    {
                        "kpi_name": k.kpi_name,
                        "value": k.value,
                        "unit": k.unit,
                        "target_value": k.target_value,
                        "variance": k.variance,
                        "trend": k.trend
                    } for k in results
                ]
            }
            await redis_manager.set_json(cache_key, cache_data, expire=3600)
        except Exception as e:
            logger.warning(f"Failed to cache KPI results: {e}")
        
        return results
    
    def _filter_metrics(
        self,
        metrics: List[MetricPoint],
        metric_filter: Dict[str, Any]
    ) -> List[MetricPoint]:
        """Filter metrics based on filter criteria.
        
        Args:
            metrics: List of metrics to filter
            metric_filter: Filter criteria
            
        Returns:
            Filtered list of metrics
        """
        filtered = metrics
        
        # Filter by metric type if specified
        if "metric_type" in metric_filter:
            target_type = metric_filter["metric_type"]
            filtered = [
                m for m in filtered 
                if hasattr(m, 'metric_type') and m.metric_type == target_type
            ]
        
        # Filter by tags if specified
        if "tags" in metric_filter:
            for tag_name, tag_value in metric_filter["tags"].items():
                filtered = [
                    m for m in filtered
                    if m.tags.get(tag_name) == tag_value
                ]
        
        # Filter by time range if specified
        if "time_range_seconds" in metric_filter:
            time_range = metric_filter["time_range_seconds"]
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=time_range)
            filtered = [
                m for m in filtered
                if m.timestamp >= cutoff_time
            ]
        
        # Filter by value range if specified
        if "value_range" in metric_filter:
            min_val = metric_filter["value_range"].get("min")
            max_val = metric_filter["value_range"].get("max")
            
            if min_val is not None:
                filtered = [m for m in filtered if m.value >= min_val]
            if max_val is not None:
                filtered = [m for m in filtered if m.value <= max_val]
        
        return filtered
    
    async def get_aggregation_history(
        self,
        metric_name: str,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical aggregation data for a metric.
        
        Args:
            metric_name: Name of the metric
            hours_back: How many hours of history to retrieve
            
        Returns:
            List of historical aggregation data
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        history = []
        
        try:
            # Search Redis for historical aggregations
            search_pattern = f"{self.redis_prefix}:aggregation:*"
            keys = await redis_manager.scan_keys(search_pattern)
            
            for key in keys:
                try:
                    data = await redis_manager.get_json(key)
                    if data and "results" in data:
                        for result in data["results"]:
                            if result.get("metric_name") == metric_name:
                                result_time = datetime.fromisoformat(result["timestamp"])
                                if start_time <= result_time <= end_time:
                                    history.append(result)
                except Exception as e:
                    logger.debug(f"Error processing history key {key}: {e}")
            
            # Sort by timestamp
            history.sort(key=lambda x: x["timestamp"])
            
        except Exception as e:
            logger.error(f"Failed to retrieve aggregation history: {e}")
        
        return history
    
    async def clear_cache(self) -> None:
        """Clear aggregation cache (for testing/cleanup)."""
        try:
            # Clear Redis cache
            pattern = f"{self.redis_prefix}:*"
            keys = await redis_manager.scan_keys(pattern)
            if keys:
                await redis_manager.delete_keys(keys)
            
            # Clear local caches
            self.aggregation_cache.clear()
            self.business_kpi_cache.clear()
            self.metric_buffers.clear()
            
            logger.info("Cleared all aggregation caches")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# Create global instance for SSOT access
real_time_aggregator = RealTimeAggregator()

# Export for direct module access
__all__ = [
    "RealTimeAggregator", 
    "MetricPoint", 
    "AggregatedMetric", 
    "BusinessKPI", 
    "AggregationType",
    "real_time_aggregator"
]