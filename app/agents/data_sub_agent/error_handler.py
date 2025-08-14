"""Error handler specific to Data Sub Agent operations.

Provides specialized error recovery for data analysis operations including
ClickHouse query failures, data fetching errors, and metric calculation issues.
"""

import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta

from app.core.error_recovery import (
    CompensationAction,
    RecoveryContext,
    OperationType
)
from app.core.error_codes import ErrorSeverity
from app.agents.error_handler import AgentError, ErrorContext, global_error_handler
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataSubAgentError(AgentError):
    """Specific error type for data sub agent operations."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        query_info: Optional[Dict] = None,
        context: Optional[ErrorContext] = None
    ):
        """Initialize data sub agent error."""
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=True
        )
        self.operation = operation
        self.query_info = query_info or {}


class ClickHouseQueryError(DataSubAgentError):
    """Error when ClickHouse queries fail."""
    
    def __init__(
        self,
        query: str,
        error_details: str,
        context: Optional[ErrorContext] = None
    ):
        """Initialize ClickHouse query error."""
        super().__init__(
            message=f"ClickHouse query failed: {error_details}",
            operation="clickhouse_query",
            query_info={'query': query, 'error': error_details},
            context=context
        )
        self.query = query
        self.error_details = error_details


class DataFetchingError(DataSubAgentError):
    """Error when data fetching operations fail."""
    
    def __init__(
        self,
        data_source: str,
        time_range: Dict,
        context: Optional[ErrorContext] = None
    ):
        """Initialize data fetching error."""
        super().__init__(
            message=f"Data fetching failed from {data_source}",
            operation="data_fetching",
            query_info={'source': data_source, 'time_range': time_range},
            context=context
        )
        self.data_source = data_source
        self.time_range = time_range


class MetricsCalculationError(DataSubAgentError):
    """Error when metrics calculation fails."""
    
    def __init__(
        self,
        metric_type: str,
        data_size: int,
        context: Optional[ErrorContext] = None
    ):
        """Initialize metrics calculation error."""
        super().__init__(
            message=f"Metrics calculation failed for {metric_type}",
            operation="metrics_calculation",
            query_info={'metric_type': metric_type, 'data_size': data_size},
            context=context
        )
        self.metric_type = metric_type
        self.data_size = data_size


class DataAnalysisCompensation(CompensationAction):
    """Compensation action for data analysis operations."""
    
    def __init__(self, cache_manager, data_store):
        """Initialize with cache and data store managers."""
        self.cache_manager = cache_manager
        self.data_store = data_store
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute compensation for data analysis operations."""
        try:
            # Clean up partial results
            temp_data_keys = context.metadata.get('temp_data_keys', [])
            if temp_data_keys:
                await self._cleanup_temp_data(temp_data_keys)
            
            # Invalidate related cache entries
            cache_keys = context.metadata.get('cache_keys', [])
            if cache_keys:
                await self.cache_manager.invalidate_keys(cache_keys)
            
            logger.info(f"Data analysis compensation completed: {context.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Data analysis compensation failed: {e}")
            return False
    
    def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate data analysis operations."""
        return context.operation_type in [
            OperationType.DATABASE_READ,
            OperationType.CACHE_OPERATION
        ]
    
    async def _cleanup_temp_data(self, temp_keys: List[str]) -> None:
        """Clean up temporary data entries."""
        for key in temp_keys:
            try:
                await self.data_store.delete(key)
                logger.debug(f"Cleaned up temp data: {key}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp data {key}: {e}")


class DataSubAgentErrorHandler:
    """Specialized error handler for data sub agent."""
    
    def __init__(self, clickhouse_client=None, cache_manager=None):
        """Initialize data sub agent error handler."""
        self.clickhouse_client = clickhouse_client
        self.cache_manager = cache_manager
        self.query_fallbacks = {
            'performance_metrics': self._fallback_performance_metrics,
            'usage_patterns': self._fallback_usage_patterns,
            'cost_analysis': self._fallback_cost_analysis,
            'error_analysis': self._fallback_error_analysis,
        }
    
    async def handle_clickhouse_error(
        self,
        query: str,
        query_type: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle ClickHouse query failures with fallback strategies."""
        context = ErrorContext(
            agent_name="data_sub_agent",
            operation_name="clickhouse_query",
            run_id=run_id,
            additional_data={
                'query': query,
                'query_type': query_type,
                'original_error': str(original_error)
            }
        )
        
        error = ClickHouseQueryError(query, str(original_error), context)
        
        try:
            # Try query simplification first
            simplified_result = await self._try_simplified_query(query, query_type)
            if simplified_result:
                logger.info(
                    f"ClickHouse query recovered with simplification",
                    run_id=run_id,
                    query_type=query_type
                )
                return simplified_result
            
            # Try fallback data source
            fallback_func = self.query_fallbacks.get(query_type)
            if fallback_func:
                fallback_result = await fallback_func(run_id)
                logger.info(
                    f"ClickHouse query recovered with fallback data",
                    run_id=run_id,
                    query_type=query_type
                )
                return fallback_result
            
            # If no fallback available, use cached data
            cached_result = await self._try_cached_fallback(query_type, run_id)
            if cached_result:
                return cached_result
            
            raise error
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def handle_data_fetching_error(
        self,
        data_source: str,
        time_range: Dict,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle data fetching failures."""
        context = ErrorContext(
            agent_name="data_sub_agent",
            operation_name="data_fetching",
            run_id=run_id,
            additional_data={
                'data_source': data_source,
                'time_range': time_range,
                'original_error': str(original_error)
            }
        )
        
        error = DataFetchingError(data_source, time_range, context)
        
        try:
            # Try alternative time range
            alternative_result = await self._try_alternative_time_range(
                data_source, time_range, run_id
            )
            if alternative_result:
                return alternative_result
            
            # Try cached data
            cached_result = await self._try_cached_data(data_source, time_range)
            if cached_result:
                return cached_result
            
            # Use synthetic data as last resort
            synthetic_result = await self._generate_synthetic_data(
                data_source, time_range
            )
            return synthetic_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def handle_metrics_calculation_error(
        self,
        metric_type: str,
        data: List[Dict],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle metrics calculation failures."""
        context = ErrorContext(
            agent_name="data_sub_agent",
            operation_name="metrics_calculation",
            run_id=run_id,
            additional_data={
                'metric_type': metric_type,
                'data_size': len(data),
                'original_error': str(original_error)
            }
        )
        
        error = MetricsCalculationError(metric_type, len(data), context)
        
        try:
            # Try simplified calculation
            simplified_result = await self._try_simplified_calculation(
                metric_type, data
            )
            if simplified_result:
                return simplified_result
            
            # Use approximation methods
            approximation_result = await self._try_approximation_calculation(
                metric_type, data
            )
            return approximation_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def _try_simplified_query(
        self,
        original_query: str,
        query_type: str
    ) -> Optional[Dict[str, Any]]:
        """Try a simplified version of the failed query."""
        try:
            # Remove complex aggregations and joins
            simplified_query = self._simplify_query(original_query, query_type)
            
            if simplified_query and self.clickhouse_client:
                result = await self.clickhouse_client.execute(simplified_query)
                return {
                    'data': result,
                    'method': 'simplified_query',
                    'query': simplified_query
                }
        except Exception as e:
            logger.debug(f"Simplified query also failed: {e}")
        
        return None
    
    def _simplify_query(self, query: str, query_type: str) -> str:
        """Create a simplified version of the query."""
        # Basic query simplification strategies
        simplified = query.lower()
        
        # Remove complex aggregations
        if 'group by' in simplified:
            # Limit grouping to simple cases
            simplified = simplified.split('group by')[0] + ' LIMIT 1000'
        
        # Remove joins for some query types
        if 'join' in simplified and query_type in ['performance_metrics']:
            # Convert to simple single-table query
            simplified = self._convert_to_single_table_query(simplified)
        
        # Add time limits to prevent long-running queries
        if 'where' in simplified:
            simplified += ' AND toDate(timestamp) >= today() - 7'
        else:
            simplified += ' WHERE toDate(timestamp) >= today() - 7'
        
        return simplified
    
    def _convert_to_single_table_query(self, query: str) -> str:
        """Convert complex join query to single table query."""
        # Extract main table and basic columns
        if 'from' in query:
            parts = query.split('from')
            select_part = parts[0]
            from_part = parts[1].split('join')[0]  # Take only first table
            
            return f"{select_part} FROM {from_part} LIMIT 1000"
        
        return query
    
    async def _try_cached_fallback(
        self,
        query_type: str,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try to use cached data as fallback."""
        if not self.cache_manager:
            return None
        
        try:
            cache_key = f"data_analysis:{query_type}:fallback"
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                logger.info(
                    f"Using cached fallback data",
                    run_id=run_id,
                    query_type=query_type
                )
                return {
                    'data': cached_data,
                    'method': 'cached_fallback',
                    'cache_key': cache_key
                }
        except Exception as e:
            logger.debug(f"Cache fallback failed: {e}")
        
        return None
    
    async def _try_alternative_time_range(
        self,
        data_source: str,
        original_range: Dict,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try fetching data with alternative time range."""
        try:
            # Try shorter time range
            start_date = datetime.fromisoformat(original_range['start_date'])
            end_date = datetime.fromisoformat(original_range['end_date'])
            
            # Reduce range by half
            duration = end_date - start_date
            new_end = start_date + duration / 2
            
            alternative_range = {
                'start_date': start_date.isoformat(),
                'end_date': new_end.isoformat()
            }
            
            # Attempt data fetch with reduced range
            # This would call the actual data fetching service
            result = await self._fetch_data_with_range(data_source, alternative_range)
            
            if result:
                logger.info(
                    f"Data fetched with reduced time range",
                    run_id=run_id,
                    original_days=(end_date - start_date).days,
                    reduced_days=(new_end - start_date).days
                )
                return {
                    'data': result,
                    'method': 'reduced_time_range',
                    'time_range': alternative_range
                }
        except Exception as e:
            logger.debug(f"Alternative time range failed: {e}")
        
        return None
    
    async def _try_cached_data(
        self,
        data_source: str,
        time_range: Dict
    ) -> Optional[Dict[str, Any]]:
        """Try to use cached data for the request."""
        if not self.cache_manager:
            return None
        
        try:
            cache_key = f"data:{data_source}:{time_range['start_date']}:{time_range['end_date']}"
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                return {
                    'data': cached_data,
                    'method': 'cached_data',
                    'cache_key': cache_key
                }
        except Exception as e:
            logger.debug(f"Cached data lookup failed: {e}")
        
        return None
    
    async def _generate_synthetic_data(
        self,
        data_source: str,
        time_range: Dict
    ) -> Dict[str, Any]:
        """Generate synthetic data as last resort."""
        # Create basic synthetic data structure
        start_date = datetime.fromisoformat(time_range['start_date'])
        end_date = datetime.fromisoformat(time_range['end_date'])
        
        # Generate daily data points
        synthetic_data = []
        current_date = start_date
        
        while current_date <= end_date:
            synthetic_data.append({
                'timestamp': current_date.isoformat(),
                'value': 0,  # Default values
                'count': 0,
                'source': data_source,
                'synthetic': True
            })
            current_date += timedelta(days=1)
        
        logger.warning(
            f"Generated synthetic data for {data_source}",
            data_points=len(synthetic_data)
        )
        
        return {
            'data': synthetic_data,
            'method': 'synthetic_generation',
            'warning': 'This is synthetic data due to data source unavailability'
        }
    
    async def _try_simplified_calculation(
        self,
        metric_type: str,
        data: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Try simplified metrics calculation."""
        try:
            if metric_type == 'performance_metrics':
                # Simple average calculation
                values = [item.get('value', 0) for item in data if 'value' in item]
                if values:
                    avg_value = sum(values) / len(values)
                    return {
                        'average': avg_value,
                        'count': len(values),
                        'method': 'simplified_average'
                    }
            
            elif metric_type == 'usage_patterns':
                # Simple count-based patterns
                total_count = len(data)
                return {
                    'total_events': total_count,
                    'method': 'simplified_count'
                }
            
            # Add more simplified calculations as needed
            
        except Exception as e:
            logger.debug(f"Simplified calculation failed: {e}")
        
        return None
    
    async def _try_approximation_calculation(
        self,
        metric_type: str,
        data: List[Dict]
    ) -> Dict[str, Any]:
        """Use approximation methods for metrics calculation."""
        # Sampling-based approximation
        sample_size = min(1000, len(data))
        sampled_data = data[:sample_size]
        
        if metric_type == 'performance_metrics':
            values = [item.get('value', 0) for item in sampled_data]
            return {
                'approximate_average': sum(values) / len(values) if values else 0,
                'sample_size': sample_size,
                'total_size': len(data),
                'method': 'sampling_approximation'
            }
        
        # Default approximation
        return {
            'total_records': len(data),
            'sample_records': sample_size,
            'method': 'basic_approximation'
        }
    
    async def _fetch_data_with_range(
        self,
        data_source: str,
        time_range: Dict
    ) -> Optional[List[Dict]]:
        """Fetch data with specific time range (placeholder for actual implementation)."""
        # This would implement actual data fetching logic
        # For now, return None to indicate fetching not available
        return None
    
    # Fallback methods for specific query types
    async def _fallback_performance_metrics(self, run_id: str) -> Dict[str, Any]:
        """Fallback for performance metrics queries."""
        return {
            'metrics': {
                'avg_response_time': 0,
                'error_rate': 0,
                'throughput': 0
            },
            'method': 'default_fallback',
            'warning': 'Using default performance metrics'
        }
    
    async def _fallback_usage_patterns(self, run_id: str) -> Dict[str, Any]:
        """Fallback for usage pattern queries."""
        return {
            'patterns': [],
            'method': 'default_fallback',
            'warning': 'No usage patterns available'
        }
    
    async def _fallback_cost_analysis(self, run_id: str) -> Dict[str, Any]:
        """Fallback for cost analysis queries."""
        return {
            'cost_breakdown': {},
            'total_cost': 0,
            'method': 'default_fallback',
            'warning': 'Cost analysis unavailable'
        }
    
    async def _fallback_error_analysis(self, run_id: str) -> Dict[str, Any]:
        """Fallback for error analysis queries."""
        return {
            'error_summary': {},
            'error_count': 0,
            'method': 'default_fallback',
            'warning': 'Error analysis unavailable'
        }


# Global data sub agent error handler instance
data_sub_agent_error_handler = DataSubAgentErrorHandler()