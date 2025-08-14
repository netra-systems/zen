"""Fallback data providers for data sub agent operations.

Provides real implementations for fallback data sources when primary systems fail.
"""

from typing import Any, Dict, List
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
        hourly_distribution = {}
        
        for activity in activity_data:
            timestamp_str = activity.get('timestamp')
            if timestamp_str:
                try:
                    hour = datetime.fromisoformat(timestamp_str).hour
                    hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
                except (ValueError, TypeError):
                    continue
        
        peak_hour = max(hourly_distribution, key=hourly_distribution.get) if hourly_distribution else 0
        
        return {
            'patterns': {
                'peak_hour': peak_hour,
                'hourly_distribution': hourly_distribution,
                'total_activities': len(activity_data)
            },
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
        error_types = {}
        severity_counts = {}
        
        for error in errors:
            error_type = error.get('type', 'unknown')
            severity = error.get('severity', 'medium')
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'error_summary': {
                'by_type': error_types,
                'by_severity': severity_counts,
                'total_errors': len(errors)
            },
            'error_count': len(errors),
            'method': 'log_analysis',
            'data_source': 'application_logs'
        }