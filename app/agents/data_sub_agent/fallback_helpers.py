"""Fallback Data Provider Helper Functions

Helper functions for fallback data providers to maintain 450-line limit.
Contains utility functions for data analysis and processing.

Business Value: Modular helper functions for reliable fallback operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FallbackDataHelpers:
    """Helper class for fallback data processing operations."""
    
    @staticmethod
    def extract_baseline_metrics(baseline: Dict) -> Dict[str, Any]:
        """Extract metrics from baseline data."""
        return {
            'avg_response_time': baseline.get('avg_response_time', 100),
            'error_rate': baseline.get('error_rate', 0.01),
            'throughput': baseline.get('throughput', 1000)
        }
    
    @staticmethod
    def create_performance_from_baseline(baseline: Dict) -> Dict[str, Any]:
        """Create performance metrics from baseline data."""
        metrics = FallbackDataHelpers.extract_baseline_metrics(baseline)
        return {
            'metrics': metrics,
            'method': 'historical_baseline',
            'data_source': 'cached_baseline'
        }
    
    @staticmethod
    def extract_hourly_distribution(activity_data: List[Dict]) -> Dict[int, int]:
        """Extract hourly distribution from activity data."""
        hourly_distribution = {}
        for activity in activity_data:
            hour = FallbackDataHelpers._extract_hour_from_activity(activity)
            if hour is not None:
                hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
        return hourly_distribution
    
    @staticmethod
    def _extract_hour_from_activity(activity: Dict) -> Optional[int]:
        """Extract hour from single activity entry."""
        timestamp_str = activity.get('timestamp')
        if not timestamp_str:
            return None
        return FallbackDataHelpers._parse_timestamp_hour(timestamp_str)
    
    @staticmethod
    def _parse_timestamp_hour(timestamp_str: str) -> Optional[int]:
        """Parse hour from timestamp string."""
        try:
            return datetime.fromisoformat(timestamp_str).hour
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def calculate_peak_hour(hourly_distribution: Dict[int, int]) -> int:
        """Calculate peak hour from distribution."""
        if not hourly_distribution:
            return 0
        return max(hourly_distribution, key=hourly_distribution.get)
    
    @staticmethod
    def build_pattern_data(peak_hour: int, hourly_distribution: Dict, 
                          activity_data: List) -> Dict:
        """Build pattern data dictionary."""
        return {
            'peak_hour': peak_hour,
            'hourly_distribution': hourly_distribution,
            'total_activities': len(activity_data)
        }
    
    @staticmethod
    def create_activity_analysis_result(patterns: Dict) -> Dict[str, Any]:
        """Create activity analysis result structure."""
        return {
            'patterns': patterns,
            'method': 'activity_analysis',
            'data_source': 'cached_activity'
        }
    
    @staticmethod
    def compute_individual_costs(usage: Dict[str, float]) -> Dict[str, float]:
        """Compute individual resource costs."""
        return {
            'cpu_cost': usage.get('cpu_usage', 0) * 0.001,
            'memory_cost': usage.get('memory_usage', 0) * 0.0005,
            'storage_cost': usage.get('storage_usage', 0) * 0.0001
        }
    
    @staticmethod
    def build_cost_analysis_response(cost_breakdown: Dict[str, float], 
                                   total_cost: float) -> Dict[str, Any]:
        """Build cost analysis response structure."""
        return FallbackDataHelpers._create_cost_response_dict(
            cost_breakdown, total_cost
        )
    
    @staticmethod
    def _create_cost_response_dict(cost_breakdown: Dict[str, float],
                                  total_cost: float) -> Dict[str, Any]:
        """Create cost response dictionary."""
        return {
            'cost_breakdown': cost_breakdown,
            'total_cost': total_cost,
            'method': 'usage_estimation',
            'data_source': 'resource_monitor'
        }
    
    @staticmethod
    def count_error_categories(errors: List[Dict]) -> tuple:
        """Count errors by type and severity."""
        error_types = {}
        severity_counts = {}
        for error in errors:
            FallbackDataHelpers._increment_error_type_count(error_types, error)
            FallbackDataHelpers._increment_severity_count(severity_counts, error)
        return error_types, severity_counts
    
    @staticmethod
    def _increment_error_type_count(error_types: Dict, error: Dict) -> None:
        """Increment count for error type."""
        error_type = error.get('type', 'unknown')
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    @staticmethod
    def _increment_severity_count(severity_counts: Dict, error: Dict) -> None:
        """Increment count for error severity."""
        severity = error.get('severity', 'medium')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    @staticmethod
    def build_error_summary(error_types: Dict, severity_counts: Dict, 
                          errors: List) -> Dict:
        """Build error summary dictionary."""
        return {
            'by_type': error_types,
            'by_severity': severity_counts,
            'total_errors': len(errors)
        }
    
    @staticmethod
    def create_error_analysis_result(error_summary: Dict, errors: List) -> Dict[str, Any]:
        """Create error analysis result structure."""
        return {
            'error_summary': error_summary,
            'error_count': len(errors),
            'method': 'log_analysis',
            'data_source': 'application_logs'
        }


class FallbackSystemIntegrations:
    """System integration helpers for fallback providers."""
    
    @staticmethod
    async def calculate_system_baseline_metrics() -> Dict[str, Any]:
        """Calculate baseline metrics from system monitoring."""
        from app.core.system_health_monitor import system_health_monitor
        system_stats = await system_health_monitor.get_current_stats()
        return FallbackSystemIntegrations._build_baseline_metrics(system_stats)
    
    @staticmethod
    def _build_baseline_metrics(system_stats: Dict) -> Dict[str, Any]:
        """Build baseline metrics from system stats."""
        return {
            'metrics': {
                'avg_response_time': system_stats.get('avg_response_time', 150),
                'error_rate': system_stats.get('error_rate', 0.02),
                'throughput': system_stats.get('throughput', 800)
            },
            'method': 'system_baseline',
            'data_source': 'system_monitor'
        }
    
    @staticmethod
    async def derive_patterns_from_system_metrics() -> Dict[str, Any]:
        """Derive patterns from system-level metrics."""
        from app.core.system_health_monitor import system_health_monitor
        system_usage = await system_health_monitor.get_usage_patterns()
        return FallbackSystemIntegrations._build_system_patterns(system_usage)
    
    @staticmethod
    def _build_system_patterns(system_usage: Dict) -> Dict[str, Any]:
        """Build system patterns from usage data."""
        return {
            'patterns': {
                'cpu_pattern': system_usage.get('cpu_pattern', {}),
                'memory_pattern': system_usage.get('memory_pattern', {}),
                'request_pattern': system_usage.get('request_pattern', {})
            },
            'method': 'system_derived',
            'data_source': 'system_monitor'
        }
    
    @staticmethod
    async def get_current_resource_usage() -> Dict[str, float]:
        """Get current resource usage for cost calculation."""
        from app.core.system_health_monitor import system_health_monitor
        return await system_health_monitor.get_resource_usage()
    
    @staticmethod
    async def get_recent_error_logs() -> List[Dict]:
        """Get recent error logs with proper error handling."""
        from app.core.error_logging import error_logger
        return await error_logger.get_recent_errors(hours=24)