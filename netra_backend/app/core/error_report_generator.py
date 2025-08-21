"""Error report generation utilities.

Provides comprehensive error reporting and analysis capabilities.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.core.error_logging_types import ErrorAggregation
from netra_backend.app.core.error_logger_core import ErrorLogger


class ErrorReportGenerator:
    """Generates comprehensive error reports."""
    
    def __init__(self, error_logger: ErrorLogger):
        """Initialize with error logger."""
        self.error_logger = error_logger
    
    def generate_summary_report(
        self,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Generate error summary report."""
        time_window = self._get_time_window(time_window)
        report_data = self._collect_report_data(time_window)
        return self._build_summary_report(report_data, time_window)
    
    def _get_time_window(self, time_window: Optional[timedelta]) -> timedelta:
        """Get time window, defaulting to 24 hours if None."""
        if time_window is None:
            return timedelta(hours=24)
        return time_window
    
    def _collect_report_data(self, time_window: timedelta) -> Dict[str, Any]:
        """Collect patterns and metrics for report."""
        patterns = self.error_logger.get_error_patterns(time_window)
        metrics = self.error_logger.get_metrics()
        summary_data = self._calculate_summary_metrics(patterns, time_window)
        return {'patterns': patterns, 'metrics': metrics, 'summary_data': summary_data}
    
    def _build_summary_report(self, report_data: Dict[str, Any], time_window: timedelta) -> Dict[str, Any]:
        """Build final summary report structure."""
        return {
            'report_period': self._format_report_period(time_window),
            'summary': report_data['summary_data'],
            'top_error_patterns': report_data['patterns'][:10],
            'metrics': report_data['metrics']
        }
    
    def _calculate_summary_metrics(
        self, 
        patterns: List[Dict[str, Any]], 
        time_window: timedelta
    ) -> Dict[str, Any]:
        """Calculate summary metrics from patterns."""
        total_errors = sum(pattern['count'] for pattern in patterns)
        critical_errors = self._count_critical_errors(patterns)
        error_rate = self._calculate_error_rate(total_errors, time_window)
        return self._build_summary_metrics_dict(total_errors, patterns, critical_errors, error_rate)
    
    def _build_summary_metrics_dict(self, total_errors: int, patterns: List[Dict[str, Any]], critical_errors: int, error_rate: float) -> Dict[str, Any]:
        """Build summary metrics dictionary."""
        return {
            'total_errors': total_errors,
            'unique_error_patterns': len(patterns),
            'critical_errors': critical_errors,
            'error_rate_per_hour': error_rate
        }
    
    def _count_critical_errors(self, patterns: List[Dict[str, Any]]) -> int:
        """Count critical errors from patterns."""
        return sum(
            pattern['severity_distribution'].get('critical', 0)
            for pattern in patterns
        )
    
    def _calculate_error_rate(self, total_errors: int, time_window: timedelta) -> float:
        """Calculate error rate per hour."""
        hours = time_window.total_seconds() / 3600
        return total_errors / hours if hours > 0 else 0
    
    def _format_report_period(self, time_window: timedelta) -> Dict[str, Any]:
        """Format report period information."""
        return {
            'duration_hours': time_window.total_seconds() / 3600,
            'end_time': datetime.now().isoformat()
        }
    
    def generate_detailed_report(
        self,
        error_signature: str
    ) -> Optional[Dict[str, Any]]:
        """Generate detailed report for specific error pattern."""
        aggregation = self.error_logger.error_aggregations.get(error_signature)
        if not aggregation:
            return None
        return self._build_detailed_report(error_signature, aggregation)
    
    def _build_detailed_report(self, error_signature: str, aggregation) -> Dict[str, Any]:
        """Build detailed report structure."""
        return {
            'error_signature': error_signature,
            'statistics': self._format_statistics(aggregation),
            'recent_occurrences': list(aggregation.recent_occurrences),
            'recommendations': self._generate_recommendations(aggregation)
        }
    
    def _format_statistics(self, aggregation: ErrorAggregation) -> Dict[str, Any]:
        """Format aggregation statistics."""
        basic_stats = self._get_basic_statistics(aggregation)
        component_stats = self._get_component_statistics(aggregation) 
        return {**basic_stats, **component_stats}
    
    def _get_basic_statistics(self, aggregation: ErrorAggregation) -> Dict[str, Any]:
        """Get basic aggregation statistics."""
        return {
            'total_occurrences': aggregation.count,
            'first_seen': aggregation.first_seen.isoformat(),
            'last_seen': aggregation.last_seen.isoformat()
        }
    
    def _get_component_statistics(self, aggregation: ErrorAggregation) -> Dict[str, Any]:
        """Get component-related statistics."""
        return {
            'affected_components': list(aggregation.affected_components),
            'affected_users_count': len(aggregation.affected_users),
            'severity_distribution': dict(aggregation.severity_distribution)
        }
    
    def _generate_recommendations(
        self,
        aggregation: ErrorAggregation
    ) -> List[str]:
        """Generate recommendations based on error pattern."""
        recommendations = []
        self._populate_all_recommendations(recommendations, aggregation)
        return recommendations
    
    def _populate_all_recommendations(self, recommendations: List[str], aggregation: ErrorAggregation) -> None:
        """Populate recommendations with all types."""
        self._add_frequency_recommendations(recommendations, aggregation)
        self._add_component_recommendations(recommendations, aggregation)
        self._add_severity_recommendations(recommendations, aggregation)
        self._add_user_impact_recommendations(recommendations, aggregation)
    
    def _add_frequency_recommendations(
        self, 
        recommendations: List[str], 
        aggregation: ErrorAggregation
    ) -> None:
        """Add frequency-based recommendations."""
        if aggregation.count > 100:
            self._add_circuit_breaker_recommendation(recommendations)
    
    def _add_circuit_breaker_recommendation(self, recommendations: List[str]) -> None:
        """Add circuit breaker recommendation."""
        recommendations.append(
            "High frequency error - consider implementing circuit breaker"
        )
    
    def _add_component_recommendations(
        self, 
        recommendations: List[str], 
        aggregation: ErrorAggregation
    ) -> None:
        """Add component-based recommendations."""
        if len(aggregation.affected_components) > 5:
            self._add_dependency_investigation_recommendation(recommendations)
    
    def _add_dependency_investigation_recommendation(self, recommendations: List[str]) -> None:
        """Add dependency investigation recommendation."""
        recommendations.append(
            "Error affects multiple components - investigate common dependencies"
        )
    
    def _add_severity_recommendations(
        self, 
        recommendations: List[str], 
        aggregation: ErrorAggregation
    ) -> None:
        """Add severity-based recommendations."""
        critical_count = aggregation.severity_distribution.get('critical', 0)
        if critical_count > 0:
            self._add_critical_investigation_recommendation(recommendations, critical_count)
    
    def _add_critical_investigation_recommendation(self, recommendations: List[str], critical_count: int) -> None:
        """Add critical investigation recommendation."""
        recommendations.append(
            f"Contains {critical_count} critical errors - prioritize investigation"
        )
    
    def _add_user_impact_recommendations(
        self, 
        recommendations: List[str], 
        aggregation: ErrorAggregation
    ) -> None:
        """Add user impact recommendations."""
        if len(aggregation.affected_users) > 50:
            self._add_emergency_response_recommendation(recommendations)
    
    def _add_emergency_response_recommendation(self, recommendations: List[str]) -> None:
        """Add emergency response recommendation."""
        recommendations.append(
            "High user impact - consider emergency response procedures"
        )


# Global error report generator instance  
from netra_backend.app.core.error_logger_core import error_logger
error_report_generator = ErrorReportGenerator(error_logger)