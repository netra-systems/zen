"""Fallback data providers for data sub agent operations.

Provides real implementations for fallback data sources when primary systems fail.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FallbackDataProvider:
    """Provides fallback data from alternative sources."""
    
    def __init__(self, cache_manager=None):
        """Initialize fallback data provider."""
        self.cache_manager = cache_manager
    
    async def get_performance_metrics_fallback(self, run_id: str) -> Dict[str, Any]:
        """Get performance metrics from system monitoring."""
        try:
            # Get baseline from cache
            if self.cache_manager:
                baseline = await self.cache_manager.get('performance_baseline')
                if baseline:
                    return self._create_performance_from_baseline(baseline)
            
            # Calculate from system monitoring
            return await self._calculate_system_baseline_metrics()
            
        except Exception as e:
            logger.warning(f"Performance metrics fallback failed: {e}")
            raise
    
    async def get_usage_patterns_fallback(self, run_id: str) -> Dict[str, Any]:
        """Get usage patterns from activity logs."""
        try:
            # Try cached activity data
            if self.cache_manager:
                activity = await self.cache_manager.get('recent_usage_activity')
                if activity:
                    return self._analyze_patterns_from_activity(activity)
            
            # Derive from system metrics
            return await self._derive_patterns_from_system_metrics()
            
        except Exception as e:
            logger.warning(f"Usage patterns fallback failed: {e}")
            raise
    
    async def get_cost_analysis_fallback(self, run_id: str) -> Dict[str, Any]:
        """Get cost analysis from resource usage estimates."""
        try:
            resource_usage = await self._get_current_resource_usage()
            return await self._calculate_cost_from_usage(resource_usage)
            
        except Exception as e:
            logger.warning(f"Cost analysis fallback failed: {e}")
            raise
    
    async def get_error_analysis_fallback(self, run_id: str) -> Dict[str, Any]:
        """Get error analysis from application logs."""
        try:
            from app.core.error_logging import error_logger
            recent_errors = await error_logger.get_recent_errors(hours=24)
            return self._summarize_error_data(recent_errors)
            
        except Exception as e:
            logger.warning(f"Error analysis fallback failed: {e}")
            raise
    
    def _create_performance_from_baseline(self, baseline: Dict) -> Dict[str, Any]:
        """Create performance metrics from baseline data."""
        return {
            'metrics': {
                'avg_response_time': baseline.get('avg_response_time', 100),
                'error_rate': baseline.get('error_rate', 0.01),
                'throughput': baseline.get('throughput', 1000)
            },
            'method': 'historical_baseline',
            'data_source': 'cached_baseline'
        }
    
    async def _calculate_system_baseline_metrics(self) -> Dict[str, Any]:
        """Calculate baseline metrics from system monitoring."""
        from app.core.system_health_monitor import system_health_monitor
        system_stats = await system_health_monitor.get_current_stats()
        
        return {
            'metrics': {
                'avg_response_time': system_stats.get('avg_response_time', 150),
                'error_rate': system_stats.get('error_rate', 0.02),
                'throughput': system_stats.get('throughput', 800)
            },
            'method': 'system_baseline',
            'data_source': 'system_monitor'
        }
    
    def _analyze_patterns_from_activity(self, activity_data: List[Dict]) -> Dict[str, Any]:
        """Analyze usage patterns from activity data."""
        hourly_distribution = self._extract_hourly_distribution(activity_data)
        peak_hour = self._calculate_peak_hour(hourly_distribution)
        patterns = self._build_pattern_data(peak_hour, hourly_distribution, activity_data)
        return self._create_activity_analysis_result(patterns)
    
    def _extract_hourly_distribution(self, activity_data: List[Dict]) -> Dict[int, int]:
        """Extract hourly distribution from activity data."""
        hourly_distribution = {}
        for activity in activity_data:
            hour = self._extract_hour_from_activity(activity)
            if hour is not None:
                hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
        return hourly_distribution
    
    def _extract_hour_from_activity(self, activity: Dict) -> Optional[int]:
        """Extract hour from single activity entry."""
        timestamp_str = activity.get('timestamp')
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str).hour
        except (ValueError, TypeError):
            return None
    
    def _calculate_peak_hour(self, hourly_distribution: Dict[int, int]) -> int:
        """Calculate peak hour from distribution."""
        if not hourly_distribution:
            return 0
        return max(hourly_distribution, key=hourly_distribution.get)
    
    def _build_pattern_data(self, peak_hour: int, hourly_distribution: Dict, activity_data: List) -> Dict:
        """Build pattern data dictionary."""
        return {
            'peak_hour': peak_hour,
            'hourly_distribution': hourly_distribution,
            'total_activities': len(activity_data)
        }
    
    def _create_activity_analysis_result(self, patterns: Dict) -> Dict[str, Any]:
        """Create activity analysis result structure."""
        return {
            'patterns': patterns,
            'method': 'activity_analysis',
            'data_source': 'cached_activity'
        }
    
    async def _derive_patterns_from_system_metrics(self) -> Dict[str, Any]:
        """Derive patterns from system-level metrics."""
        from app.core.system_health_monitor import system_health_monitor
        system_usage = await system_health_monitor.get_usage_patterns()
        
        return {
            'patterns': {
                'cpu_pattern': system_usage.get('cpu_pattern', {}),
                'memory_pattern': system_usage.get('memory_pattern', {}),
                'request_pattern': system_usage.get('request_pattern', {})
            },
            'method': 'system_derived',
            'data_source': 'system_monitor'
        }
    
    async def _get_current_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage for cost calculation."""
        from app.core.system_health_monitor import system_health_monitor
        return await system_health_monitor.get_resource_usage()
    
    async def _calculate_cost_from_usage(self, usage: Dict[str, float]) -> Dict[str, Any]:
        """Calculate cost estimates from resource usage."""
        # Standard cloud pricing rates
        cpu_cost = usage.get('cpu_usage', 0) * 0.001
        memory_cost = usage.get('memory_usage', 0) * 0.0005
        storage_cost = usage.get('storage_usage', 0) * 0.0001
        
        total_cost = cpu_cost + memory_cost + storage_cost
        
        return {
            'cost_breakdown': {
                'cpu_cost': cpu_cost,
                'memory_cost': memory_cost,
                'storage_cost': storage_cost
            },
            'total_cost': total_cost,
            'method': 'usage_estimation',
            'data_source': 'resource_monitor'
        }
    
    def _summarize_error_data(self, errors: List[Dict]) -> Dict[str, Any]:
        """Summarize error data for analysis."""
        error_types, severity_counts = self._count_error_categories(errors)
        error_summary = self._build_error_summary(error_types, severity_counts, errors)
        return self._create_error_analysis_result(error_summary, errors)
    
    def _count_error_categories(self, errors: List[Dict]) -> tuple:
        """Count errors by type and severity."""
        error_types = {}
        severity_counts = {}
        for error in errors:
            self._increment_error_type_count(error_types, error)
            self._increment_severity_count(severity_counts, error)
        return error_types, severity_counts
    
    def _increment_error_type_count(self, error_types: Dict, error: Dict) -> None:
        """Increment count for error type."""
        error_type = error.get('type', 'unknown')
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    def _increment_severity_count(self, severity_counts: Dict, error: Dict) -> None:
        """Increment count for error severity."""
        severity = error.get('severity', 'medium')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    def _build_error_summary(self, error_types: Dict, severity_counts: Dict, errors: List) -> Dict:
        """Build error summary dictionary."""
        return {
            'by_type': error_types,
            'by_severity': severity_counts,
            'total_errors': len(errors)
        }
    
    def _create_error_analysis_result(self, error_summary: Dict, errors: List) -> Dict[str, Any]:
        """Create error analysis result structure."""
        return {
            'error_summary': error_summary,
            'error_count': len(errors),
            'method': 'log_analysis',
            'data_source': 'application_logs'
        }