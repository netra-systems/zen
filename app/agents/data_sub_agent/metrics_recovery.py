"""Metrics calculation recovery strategies.

Handles metrics calculation failures with simplified algorithms and approximations.
"""

from typing import Any, Dict, Optional, List
from app.logging_config import central_logger
from .error_types import MetricsCalculationError
from app.agents.error_handler import ErrorContext

logger = central_logger.get_logger(__name__)


class MetricsRecoveryManager:
    """Manages metrics calculation recovery strategies."""
    
    def __init__(self):
        """Initialize metrics recovery manager."""
        self.calculation_strategies = {
            'performance_metrics': self._calculate_performance_metrics,
            'usage_patterns': self._calculate_usage_patterns,
            'cost_analysis': self._calculate_cost_metrics,
            'error_analysis': self._calculate_error_metrics
        }
    
    async def handle_calculation_failure(
        self,
        metric_type: str,
        data: List[Dict],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle metrics calculation failures with recovery strategies."""
        error = self._prepare_calculation_error(metric_type, data, run_id, original_error)
        return await self._execute_recovery_strategies(metric_type, data, error)
    
    def _create_error_context(
        self, metric_type: str, data: List[Dict], run_id: str, error: Exception
    ) -> ErrorContext:
        """Create error context for metrics calculation failures."""
        return ErrorContext(
            agent_name="data_sub_agent",
            operation_name="metrics_calculation",
            run_id=run_id,
            additional_data={
                'metric_type': metric_type,
                'data_size': len(data),
                'original_error': str(error)
            }
        )
    
    async def _try_simplified_calculation(
        self, metric_type: str, data: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Try simplified metrics calculation."""
        try:
            calculator = self.calculation_strategies.get(metric_type)
            if calculator:
                result = await calculator(data, simplified=True)
                result['method'] = 'simplified_calculation'
                return result
        except Exception as e:
            logger.debug(f"Simplified calculation failed: {e}")
        
        return None
    
    async def _try_approximation_calculation(
        self, metric_type: str, data: List[Dict]
    ) -> Dict[str, Any]:
        """Use approximation methods for metrics calculation."""
        sample_size = min(1000, len(data))
        sampled_data = data[:sample_size]
        result = await self._calculate_with_approximation(metric_type, sampled_data)
        return self._add_approximation_metadata(result, sample_size, len(data))
    
    async def _calculate_performance_metrics(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate performance metrics with fallback strategies."""
        values = self._extract_numeric_values(data, 'value')
        if not values:
            return {'average': 0, 'count': 0}
        if simplified or approximation:
            return self._calculate_simple_performance_metrics(values)
        return self._calculate_full_performance_metrics(values)
    
    async def _calculate_usage_patterns(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate usage patterns with fallback strategies."""
        if simplified or approximation:
            # Simple count-based patterns
            return {'total_events': len(data)}
        
        # More complex pattern analysis
        hourly_patterns = self._analyze_hourly_patterns(data)
        return {
            'total_events': len(data),
            'hourly_distribution': hourly_patterns
        }
    
    async def _calculate_cost_metrics(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate cost metrics with fallback strategies."""
        cost_values = [item.get('cost', 0) for item in data if 'cost' in item]
        
        if not cost_values:
            return {'total_cost': 0, 'count': 0}
        
        total_cost = sum(cost_values)
        
        if simplified or approximation:
            return {'total_cost': total_cost, 'count': len(cost_values)}
        
        return {
            'total_cost': total_cost,
            'average_cost': total_cost / len(cost_values),
            'count': len(cost_values)
        }
    
    async def _calculate_error_metrics(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate error metrics with fallback strategies."""
        error_types = {}
        for item in data:
            error_type = item.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if simplified or approximation:
            return {'error_count': len(data)}
        
        return {
            'error_count': len(data),
            'error_types': error_types,
            'unique_error_types': len(error_types)
        }
    
    def _analyze_hourly_patterns(self, data: List[Dict]) -> Dict[int, int]:
        """Analyze hourly patterns in data."""
        from datetime import datetime
        
        hourly_distribution = {}
        for item in data:
            timestamp = item.get('timestamp')
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp).hour
                    hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
                except (ValueError, TypeError):
                    continue
        
        return hourly_distribution
    
    def _basic_approximation(self, data: List[Dict]) -> Dict[str, Any]:
        """Basic approximation for unknown metric types."""
        return {
            'total_records': len(data),
            'has_data': len(data) > 0
        }