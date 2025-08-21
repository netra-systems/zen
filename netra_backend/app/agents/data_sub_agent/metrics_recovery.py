"""Metrics calculation recovery strategies.

Handles metrics calculation failures with simplified algorithms and approximations.
"""

from typing import Any, Dict, Optional, List
from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.data_sub_agent.error_types import MetricsCalculationError
from netra_backend.app.agents.error_handler import ErrorContext

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
        self, metric_type: str, data: List[Dict], run_id: str, original_error: Exception
    ) -> Dict[str, Any]:
        """Handle metrics calculation failures with recovery strategies."""
        error = self._prepare_calculation_error(metric_type, data, run_id, original_error)
        return await self._execute_recovery_strategies(metric_type, data, error)
    
    def _create_error_context(
        self, metric_type: str, data: List[Dict], run_id: str, error: Exception
    ) -> ErrorContext:
        """Create error context for metrics calculation failures."""
        additional_data = self._build_error_context_data(metric_type, data, error)
        return self._build_error_context_object(run_id, additional_data)
    
    async def _try_simplified_calculation(
        self, metric_type: str, data: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Try simplified metrics calculation."""
        try:
            return await self._execute_simplified_calculation(metric_type, data)
        except Exception as e:
            self._log_calculation_failure(e)
            return None
    
    def _prepare_calculation_error(
        self, metric_type: str, data: List[Dict], run_id: str, original_error: Exception
    ) -> MetricsCalculationError:
        """Prepare calculation error with context."""
        context = self._create_error_context(metric_type, data, run_id, original_error)
        return MetricsCalculationError(metric_type, len(data), context)
    
    async def _execute_recovery_strategies(
        self, metric_type: str, data: List[Dict], error: MetricsCalculationError
    ) -> Dict[str, Any]:
        """Execute recovery strategies for failed calculations."""
        try:
            return await self._attempt_recovery_methods(metric_type, data)
        except Exception as fallback_error:
            logger.error(f"Metrics calculation recovery failed: {fallback_error}")
            raise error
    
    async def _calculate_with_approximation(
        self, metric_type: str, sampled_data: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate metrics using approximation methods."""
        calculator = self.calculation_strategies.get(metric_type)
        if calculator:
            return await calculator(sampled_data, approximation=True)
        return self._basic_approximation(sampled_data)
    
    def _add_approximation_metadata(
        self, result: Dict[str, Any], sample_size: int, total_size: int
    ) -> Dict[str, Any]:
        """Add approximation metadata to calculation results."""
        metadata = self._build_approximation_metadata(sample_size, total_size)
        result.update(metadata)
        return result
    
    def _extract_numeric_values(self, data: List[Dict], key: str) -> List[float]:
        """Extract numeric values from data for a given key."""
        return [item.get(key, 0) for item in data if key in item]
    
    def _calculate_simple_performance_metrics(self, values: List[float]) -> Dict[str, Any]:
        """Calculate simple performance metrics for approximation."""
        avg_value = sum(values) / len(values)
        return {'average': avg_value, 'count': len(values)}
    
    def _calculate_full_performance_metrics(self, values: List[float]) -> Dict[str, Any]:
        """Calculate full performance metrics with all statistics."""
        return {
            'average': sum(values) / len(values),
            'count': len(values),
            'min': min(values),
            'max': max(values)
        }
    
    async def _try_approximation_calculation(
        self, metric_type: str, data: List[Dict]
    ) -> Dict[str, Any]:
        """Use approximation methods for metrics calculation."""
        sample_size, sampled_data = self._prepare_sample_data(data)
        result = await self._calculate_with_approximation(metric_type, sampled_data)
        return self._add_approximation_metadata(result, sample_size, len(data))
    
    def _prepare_sample_data(self, data: List[Dict]) -> tuple[int, List[Dict]]:
        """Prepare sampled data for approximation calculation."""
        sample_size = min(1000, len(data))
        sampled_data = data[:sample_size]
        return sample_size, sampled_data
    
    async def _calculate_performance_metrics(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate performance metrics with fallback strategies."""
        values = self._extract_numeric_values(data, 'value')
        if not values:
            return self._get_empty_performance_metrics()
        return self._select_performance_calculation_method(values, simplified, approximation)
    
    def _get_empty_performance_metrics(self) -> Dict[str, Any]:
        """Get empty performance metrics result."""
        return {'average': 0, 'count': 0}
    
    async def _calculate_usage_patterns(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate usage patterns with fallback strategies."""
        if simplified or approximation:
            return {'total_events': len(data)}
        return self._build_usage_patterns_result(data)
    
    async def _calculate_cost_metrics(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate cost metrics with fallback strategies."""
        cost_values = self._extract_numeric_values(data, 'cost')
        if not cost_values:
            return {'total_cost': 0, 'count': 0}
        return self._select_cost_calculation_method(cost_values, simplified, approximation)
    
    async def _calculate_error_metrics(
        self, data: List[Dict], simplified: bool = False, approximation: bool = False
    ) -> Dict[str, Any]:
        """Calculate error metrics with fallback strategies."""
        if simplified or approximation:
            return {'error_count': len(data)}
        return self._build_error_metrics_result(data)
    
    def _analyze_hourly_patterns(self, data: List[Dict]) -> Dict[int, int]:
        """Analyze hourly patterns in data."""
        hourly_distribution = {}
        for item in data:
            self._add_hour_to_distribution(item, hourly_distribution)
        return hourly_distribution
    
    def _basic_approximation(self, data: List[Dict]) -> Dict[str, Any]:
        """Basic approximation for unknown metric types."""
        return {
            'total_records': len(data),
            'has_data': len(data) > 0
        }
    
    def _build_full_cost_metrics(self, total_cost: float, cost_values: List[float]) -> Dict[str, Any]:
        """Build full cost metrics with all calculations."""
        return {
            'total_cost': total_cost,
            'average_cost': total_cost / len(cost_values),
            'count': len(cost_values)
        }
    
    def _count_error_types(self, data: List[Dict]) -> Dict[str, int]:
        """Count error types from data items."""
        error_types = {}
        self._process_error_type_counts(data, error_types)
        return error_types
    
    def _process_error_type_counts(self, data: List[Dict], error_types: Dict[str, int]) -> None:
        """Process data items to count error types."""
        for item in data:
            error_type = item.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
    
    def _extract_hour_from_timestamp(self, timestamp: Optional[str]) -> Optional[int]:
        """Extract hour from timestamp string safely."""
        from datetime import datetime
        if not timestamp:
            return None
        return self._parse_timestamp_hour(timestamp)
    
    def _build_error_context_data(
        self, metric_type: str, data: List[Dict], error: Exception
    ) -> Dict[str, Any]:
        """Build error context additional data."""
        return {
            'metric_type': metric_type,
            'data_size': len(data),
            'original_error': str(error)
        }
    
    async def _execute_simplified_calculation(
        self, metric_type: str, data: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Execute simplified calculation if calculator exists."""
        calculator = self.calculation_strategies.get(metric_type)
        if not calculator:
            return None
        return await self._call_calculator_with_method(calculator, data, 'simplified_calculation')
    
    async def _attempt_recovery_methods(
        self, metric_type: str, data: List[Dict]
    ) -> Dict[str, Any]:
        """Attempt recovery methods in sequence."""
        simplified_result = await self._try_simplified_calculation(metric_type, data)
        if simplified_result:
            return simplified_result
        return await self._try_approximation_calculation(metric_type, data)
    
    def _build_approximation_metadata(self, sample_size: int, total_size: int) -> Dict[str, Any]:
        """Build approximation metadata dictionary."""
        return {
            'method': 'sampling_approximation',
            'sample_size': sample_size,
            'total_size': total_size
        }
    
    def _select_performance_calculation_method(
        self, values: List[float], simplified: bool, approximation: bool
    ) -> Dict[str, Any]:
        """Select appropriate performance calculation method."""
        if simplified or approximation:
            return self._calculate_simple_performance_metrics(values)
        return self._calculate_full_performance_metrics(values)
    
    def _build_usage_patterns_result(self, data: List[Dict]) -> Dict[str, Any]:
        """Build usage patterns result with hourly distribution."""
        hourly_patterns = self._analyze_hourly_patterns(data)
        return {
            'total_events': len(data),
            'hourly_distribution': hourly_patterns
        }
    
    def _select_cost_calculation_method(
        self, cost_values: List[float], simplified: bool, approximation: bool
    ) -> Dict[str, Any]:
        """Select appropriate cost calculation method."""
        total_cost = sum(cost_values)
        if simplified or approximation:
            return {'total_cost': total_cost, 'count': len(cost_values)}
        return self._build_full_cost_metrics(total_cost, cost_values)
    
    def _build_error_metrics_result(self, data: List[Dict]) -> Dict[str, Any]:
        """Build error metrics result with error type analysis."""
        error_types = self._count_error_types(data)
        return {
            'error_count': len(data),
            'error_types': error_types,
            'unique_error_types': len(error_types)
        }
    
    def _add_hour_to_distribution(self, item: Dict, hourly_distribution: Dict[int, int]) -> None:
        """Add hour from item timestamp to hourly distribution."""
        hour = self._extract_hour_from_timestamp(item.get('timestamp'))
        if hour is not None:
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
    
    def _parse_timestamp_hour(self, timestamp: str) -> Optional[int]:
        """Parse hour from timestamp string with error handling."""
        from datetime import datetime
        try:
            return datetime.fromisoformat(timestamp).hour
        except (ValueError, TypeError):
            return None
    
    def _build_error_context_object(self, run_id: str, additional_data: Dict[str, Any]) -> ErrorContext:
        """Build ErrorContext object with standard agent data."""
        return ErrorContext(
            agent_name="data_sub_agent",
            operation_name="metrics_calculation",
            run_id=run_id,
            additional_data=additional_data
        )
    
    async def _call_calculator_with_method(
        self, calculator, data: List[Dict], method_name: str
    ) -> Dict[str, Any]:
        """Call calculator and add method name to result."""
        result = await calculator(data, simplified=True)
        result['method'] = method_name
        return result
    
    def _log_calculation_failure(self, error: Exception) -> None:
        """Log simplified calculation failure."""
        logger.debug(f"Simplified calculation failed: {error}")