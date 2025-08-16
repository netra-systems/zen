"""Error report generation utilities.

Provides comprehensive error reporting and analysis capabilities.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.error_logging_types import ErrorAggregation
from app.core.error_logger_core import ErrorLogger


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
        if time_window is None:
            time_window = timedelta(hours=24)
        
        patterns = self.error_logger.get_error_patterns(time_window)
        metrics = self.error_logger.get_metrics()
        
        summary_data = self._calculate_summary_metrics(patterns, time_window)
        
        return {
            'report_period': self._format_report_period(time_window),
            'summary': summary_data,
            'top_error_patterns': patterns[:10],
            'metrics': metrics
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
        
        return {
            'error_signature': error_signature,
            'statistics': self._format_statistics(aggregation),
            'recent_occurrences': list(aggregation.recent_occurrences),
            'recommendations': self._generate_recommendations(aggregation)
        }
    
    def _format_statistics(self, aggregation: ErrorAggregation) -> Dict[str, Any]:
        """Format aggregation statistics."""
        return {
            'total_occurrences': aggregation.count,
            'first_seen': aggregation.first_seen.isoformat(),
            'last_seen': aggregation.last_seen.isoformat(),
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
        
        self._add_frequency_recommendations(recommendations, aggregation)
        self._add_component_recommendations(recommendations, aggregation)
        self._add_severity_recommendations(recommendations, aggregation)
        self._add_user_impact_recommendations(recommendations, aggregation)
        
        return recommendations
    
    def _add_frequency_recommendations(
        self, 
        recommendations: List[str], 
        aggregation: ErrorAggregation
    ) -> None:
        """Add frequency-based recommendations."""
        if aggregation.count > 100:
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
            recommendations.append(
                "High user impact - consider emergency response procedures"
            )


# Global error report generator instance  
from app.core.error_logger_core import error_logger
error_report_generator = ErrorReportGenerator(error_logger)