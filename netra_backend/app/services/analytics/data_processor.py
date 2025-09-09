"""Data processor for analytics transformations.

Business Value Justification (BVJ):
- Segment: Mid and Enterprise customers (advanced analytics)  
- Business Goal: Provide data transformation and processing capabilities
- Value Impact: Enables complex data analytics and business intelligence
- Revenue Impact: Supports premium analytics features and enterprise reporting
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataProcessor:
    """Handles data processing and transformations for analytics."""

    def __init__(self):
        """Initialize data processor."""
        self._processing_cache = {}

    async def transform_events_to_metrics(
        self,
        events: List[Dict[str, Any]],
        transformation_rules: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Transform raw events into analytical metrics.
        
        Args:
            events: List of raw event records
            transformation_rules: Optional rules for transformation
            
        Returns:
            List of transformed metric records
        """
        try:
            logger.debug(f"Transforming {len(events)} events to metrics")
            
            metrics = []
            transformation_rules = transformation_rules or {}
            
            # Group events by type for processing
            events_by_type = {}
            for event in events:
                event_type = event.get("event_type", "unknown")
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(event)
            
            # Process each event type
            for event_type, event_list in events_by_type.items():
                if event_type == "user_login":
                    login_metrics = await self._process_login_events(event_list)
                    metrics.extend(login_metrics)
                elif event_type == "page_view":
                    pageview_metrics = await self._process_pageview_events(event_list)
                    metrics.extend(pageview_metrics)
                elif event_type == "feature_usage":
                    feature_metrics = await self._process_feature_usage_events(event_list)
                    metrics.extend(feature_metrics)
                elif event_type == "user_logout":
                    logout_metrics = await self._process_logout_events(event_list)
                    metrics.extend(logout_metrics)
                else:
                    # Generic event processing
                    generic_metrics = await self._process_generic_events(event_list, event_type)
                    metrics.extend(generic_metrics)
            
            logger.debug(f"Generated {len(metrics)} metrics from {len(events)} events")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to transform events to metrics: {str(e)}")
            return []

    async def _process_login_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process login events into metrics."""
        metrics = []
        
        try:
            # Count logins by device type
            device_counts = {}
            unique_users = set()
            
            for event in events:
                user_id = event.get("user_id")
                event_data = event.get("event_data", {})
                device = event_data.get("device", "unknown")
                
                unique_users.add(user_id)
                device_counts[device] = device_counts.get(device, 0) + 1
            
            # Create metrics
            metrics.append({
                "metric_name": "login_count",
                "metric_value": len(events),
                "dimensions": {"event_type": "user_login"}
            })
            
            metrics.append({
                "metric_name": "unique_login_users",
                "metric_value": len(unique_users),
                "dimensions": {"event_type": "user_login"}
            })
            
            for device, count in device_counts.items():
                metrics.append({
                    "metric_name": "login_by_device",
                    "metric_value": count,
                    "dimensions": {"device": device, "event_type": "user_login"}
                })
            
        except Exception as e:
            logger.error(f"Failed to process login events: {str(e)}")
        
        return metrics

    async def _process_pageview_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process page view events into metrics."""
        metrics = []
        
        try:
            page_counts = {}
            total_duration = 0
            duration_count = 0
            
            for event in events:
                event_data = event.get("event_data", {})
                page = event_data.get("page", "unknown")
                duration = event_data.get("duration", 0)
                
                page_counts[page] = page_counts.get(page, 0) + 1
                
                if duration > 0:
                    total_duration += duration
                    duration_count += 1
            
            # Create metrics
            for page, count in page_counts.items():
                metrics.append({
                    "metric_name": "page_view_count",
                    "metric_value": count,
                    "dimensions": {"page": page, "event_type": "page_view"}
                })
            
            if duration_count > 0:
                avg_duration = total_duration / duration_count
                metrics.append({
                    "metric_name": "avg_page_duration",
                    "metric_value": avg_duration,
                    "dimensions": {"event_type": "page_view"}
                })
            
        except Exception as e:
            logger.error(f"Failed to process pageview events: {str(e)}")
        
        return metrics

    async def _process_feature_usage_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process feature usage events into metrics."""
        metrics = []
        
        try:
            feature_usage = {}
            feature_durations = {}
            
            for event in events:
                event_data = event.get("event_data", {})
                feature = event_data.get("feature", "unknown")
                duration = event_data.get("duration", 0)
                
                feature_usage[feature] = feature_usage.get(feature, 0) + 1
                
                if duration > 0:
                    if feature not in feature_durations:
                        feature_durations[feature] = []
                    feature_durations[feature].append(duration)
            
            # Create metrics
            for feature, count in feature_usage.items():
                metrics.append({
                    "metric_name": "feature_usage_count",
                    "metric_value": count,
                    "dimensions": {"feature": feature, "event_type": "feature_usage"}
                })
            
            for feature, durations in feature_durations.items():
                avg_duration = sum(durations) / len(durations)
                metrics.append({
                    "metric_name": "avg_feature_duration",
                    "metric_value": avg_duration,
                    "dimensions": {"feature": feature, "event_type": "feature_usage"}
                })
            
        except Exception as e:
            logger.error(f"Failed to process feature usage events: {str(e)}")
        
        return metrics

    async def _process_logout_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process logout events into metrics."""
        metrics = []
        
        try:
            session_durations = []
            unique_users = set()
            
            for event in events:
                user_id = event.get("user_id")
                event_data = event.get("event_data", {})
                session_duration = event_data.get("session_duration", 0)
                
                unique_users.add(user_id)
                
                if session_duration > 0:
                    session_durations.append(session_duration)
            
            # Create metrics
            metrics.append({
                "metric_name": "logout_count",
                "metric_value": len(events),
                "dimensions": {"event_type": "user_logout"}
            })
            
            if session_durations:
                avg_session_duration = sum(session_durations) / len(session_durations)
                metrics.append({
                    "metric_name": "avg_session_duration",
                    "metric_value": avg_session_duration,
                    "dimensions": {"event_type": "user_logout"}
                })
            
        except Exception as e:
            logger.error(f"Failed to process logout events: {str(e)}")
        
        return metrics

    async def _process_generic_events(
        self, 
        events: List[Dict[str, Any]], 
        event_type: str
    ) -> List[Dict[str, Any]]:
        """Process generic events into metrics."""
        metrics = []
        
        try:
            # Basic count metric for any event type
            metrics.append({
                "metric_name": f"{event_type}_count",
                "metric_value": len(events),
                "dimensions": {"event_type": event_type}
            })
            
            # Count unique users for this event type
            unique_users = set()
            for event in events:
                user_id = event.get("user_id")
                if user_id:
                    unique_users.add(user_id)
            
            if unique_users:
                metrics.append({
                    "metric_name": f"{event_type}_unique_users",
                    "metric_value": len(unique_users),
                    "dimensions": {"event_type": event_type}
                })
            
        except Exception as e:
            logger.error(f"Failed to process generic events for {event_type}: {str(e)}")
        
        return metrics

    async def aggregate_metrics_by_time(
        self,
        metrics: List[Dict[str, Any]],
        time_window: str = "hour"
    ) -> List[Dict[str, Any]]:
        """Aggregate metrics by time windows.
        
        Args:
            metrics: List of metric records
            time_window: Time window for aggregation ("hour", "day", "week")
            
        Returns:
            List of time-aggregated metrics
        """
        try:
            logger.debug(f"Aggregating {len(metrics)} metrics by {time_window}")
            
            aggregated = {}
            current_time = datetime.now(UTC)
            
            for metric in metrics:
                metric_name = metric.get("metric_name")
                metric_value = metric.get("metric_value", 0)
                dimensions = metric.get("dimensions", {})
                
                # Create time window key
                if time_window == "hour":
                    time_key = current_time.strftime("%Y-%m-%d %H:00")
                elif time_window == "day":
                    time_key = current_time.strftime("%Y-%m-%d")
                elif time_window == "week":
                    # Week starting Monday
                    week_start = current_time - timedelta(days=current_time.weekday())
                    time_key = week_start.strftime("%Y-%m-%d")
                else:
                    time_key = current_time.strftime("%Y-%m-%d %H:%M")
                
                # Create aggregation key
                agg_key = f"{time_key}_{metric_name}_{hash(str(sorted(dimensions.items())))}"
                
                if agg_key not in aggregated:
                    aggregated[agg_key] = {
                        "metric_name": metric_name,
                        "metric_value": 0,
                        "dimensions": {**dimensions, "time_window": time_key, "aggregation": time_window},
                        "record_count": 0
                    }
                
                aggregated[agg_key]["metric_value"] += metric_value
                aggregated[agg_key]["record_count"] += 1
            
            result = list(aggregated.values())
            logger.debug(f"Generated {len(result)} aggregated metrics")
            return result
            
        except Exception as e:
            logger.error(f"Failed to aggregate metrics by time: {str(e)}")
            return metrics

    async def calculate_derived_metrics(
        self,
        base_metrics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate derived metrics from base metrics.
        
        Args:
            base_metrics: List of base metric records
            
        Returns:
            List of derived metric records
        """
        try:
            logger.debug(f"Calculating derived metrics from {len(base_metrics)} base metrics")
            
            derived = []
            
            # Group metrics by name for calculations
            metrics_by_name = {}
            for metric in base_metrics:
                name = metric.get("metric_name")
                if name not in metrics_by_name:
                    metrics_by_name[name] = []
                metrics_by_name[name].append(metric)
            
            # Calculate ratios and rates
            if "login_count" in metrics_by_name and "unique_login_users" in metrics_by_name:
                total_logins = sum(m["metric_value"] for m in metrics_by_name["login_count"])
                unique_users = sum(m["metric_value"] for m in metrics_by_name["unique_login_users"])
                
                if unique_users > 0:
                    avg_logins_per_user = total_logins / unique_users
                    derived.append({
                        "metric_name": "avg_logins_per_user",
                        "metric_value": avg_logins_per_user,
                        "dimensions": {"calculation": "derived", "type": "ratio"}
                    })
            
            # Calculate engagement score
            engagement_factors = ["page_view_count", "feature_usage_count", "avg_session_duration"]
            engagement_values = []
            
            for factor in engagement_factors:
                if factor in metrics_by_name:
                    values = [m["metric_value"] for m in metrics_by_name[factor]]
                    if values:
                        engagement_values.append(sum(values) / len(values))
            
            if engagement_values:
                engagement_score = sum(engagement_values) / len(engagement_values)
                derived.append({
                    "metric_name": "user_engagement_score",
                    "metric_value": engagement_score,
                    "dimensions": {"calculation": "derived", "type": "composite_score"}
                })
            
            logger.debug(f"Generated {len(derived)} derived metrics")
            return derived
            
        except Exception as e:
            logger.error(f"Failed to calculate derived metrics: {str(e)}")
            return []