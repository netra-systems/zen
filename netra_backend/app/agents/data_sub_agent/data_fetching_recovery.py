"""Data fetching recovery strategies.

Handles data source failures with alternative time ranges and cached data.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.error_types import DataFetchingError
from netra_backend.app.agents.error_handler import ErrorContext

logger = central_logger.get_logger(__name__)


class DataFetchingRecoveryManager:
    """Manages data fetching recovery strategies."""
    
    def __init__(self, cache_manager=None):
        """Initialize data fetching recovery manager."""
        self.cache_manager = cache_manager
    
    async def handle_fetching_failure(
        self,
        data_source: str,
        time_range: Dict,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle data fetching failures with recovery strategies."""
        context = self._create_error_context(data_source, time_range, run_id, original_error)
        error = DataFetchingError(data_source, time_range, context)
        return await self._execute_recovery_with_fallback(data_source, time_range, run_id, error)
    
    async def _execute_recovery_with_fallback(
        self, data_source: str, time_range: Dict, run_id: str, error: DataFetchingError
    ) -> Dict[str, Any]:
        """Execute recovery strategies with error fallback."""
        try:
            return await self._attempt_recovery_strategies(data_source, time_range, run_id)
        except Exception as fallback_error:
            logger.error(f"Data fetching recovery failed: {fallback_error}")
            raise error
    
    async def _attempt_recovery_strategies(self, data_source: str, time_range: Dict, run_id: str) -> Dict[str, Any]:
        """Attempt various recovery strategies in order."""
        alternative_result = await self._try_alternative_time_range(data_source, time_range, run_id)
        if alternative_result:
            return alternative_result
        cached_result = await self._try_cached_data(data_source, time_range)
        if cached_result:
            return cached_result
        return await self._generate_synthetic_data(data_source, time_range)
    
    def _create_error_context(
        self, data_source: str, time_range: Dict, run_id: str, error: Exception
    ) -> ErrorContext:
        """Create error context for data fetching failures."""
        return ErrorContext(
            agent_name="data_sub_agent",
            operation_name="data_fetching",
            run_id=run_id,
            additional_data={
                'data_source': data_source,
                'time_range': time_range,
                'original_error': str(error)
            }
        )
    
    async def _try_alternative_time_range(
        self, data_source: str, original_range: Dict, run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try fetching data with reduced time range."""
        try:
            alternative_range = self._calculate_reduced_range(original_range)
            result = await self._fetch_data_with_range(data_source, alternative_range)
            return self._create_alternative_result(result, alternative_range)
        except Exception as e:
            logger.debug(f"Alternative time range failed: {e}")
            return None
    
    def _calculate_reduced_range(self, original_range: Dict) -> Dict:
        """Calculate reduced time range."""
        start_date = datetime.fromisoformat(original_range['start_date'])
        end_date = datetime.fromisoformat(original_range['end_date'])
        
        # Reduce range by half
        duration = end_date - start_date
        new_end = start_date + duration / 2
        
        return {
            'start_date': start_date.isoformat(),
            'end_date': new_end.isoformat()
        }
    
    async def _try_cached_data(
        self, data_source: str, time_range: Dict
    ) -> Optional[Dict[str, Any]]:
        """Try to use cached data."""
        if not self.cache_manager:
            return None
        try:
            return await self._lookup_cached_data(data_source, time_range)
        except Exception as e:
            logger.debug(f"Cached data lookup failed: {e}")
            return None
    
    def _build_cache_key(self, data_source: str, time_range: Dict) -> str:
        """Build cache key for data request."""
        return f"data:{data_source}:{time_range['start_date']}:{time_range['end_date']}"
    
    async def _generate_synthetic_data(
        self, data_source: str, time_range: Dict
    ) -> Dict[str, Any]:
        """Generate synthetic data as last resort."""
        start_date = datetime.fromisoformat(time_range['start_date'])
        end_date = datetime.fromisoformat(time_range['end_date'])
        synthetic_data = self._create_daily_data_points(start_date, end_date, data_source)
        logger.warning(f"Generated synthetic data for {data_source}")
        return self._create_synthetic_result(synthetic_data)
    
    def _create_daily_data_points(
        self, start_date: datetime, end_date: datetime, data_source: str
    ) -> List[Dict]:
        """Create daily data points for synthetic data."""
        synthetic_data = []
        current_date = start_date
        while current_date <= end_date:
            synthetic_data.append(self._create_data_point(current_date, data_source))
            current_date += timedelta(days=1)
        return synthetic_data
    
    async def _fetch_data_with_range(
        self, data_source: str, time_range: Dict
    ) -> Optional[List[Dict]]:
        """Fetch data with specific time range."""
        # This would implement actual data fetching logic
        # Returns None to indicate fetching not available in fallback
        return None
    
    def _create_alternative_result(self, result: Optional[List[Dict]], alternative_range: Dict) -> Optional[Dict[str, Any]]:
        """Create result dict for alternative time range fetch."""
        if not result:
            return None
        logger.info(f"Data fetched with reduced time range")
        return {
            'data': result,
            'method': 'reduced_time_range',
            'time_range': alternative_range
        }
    
    async def _lookup_cached_data(self, data_source: str, time_range: Dict) -> Optional[Dict[str, Any]]:
        """Lookup cached data and create result."""
        cache_key = self._build_cache_key(data_source, time_range)
        cached_data = await self.cache_manager.get(cache_key)
        if not cached_data:
            return None
        return {
            'data': cached_data,
            'method': 'cached_data',
            'cache_key': cache_key
        }
    
    def _create_synthetic_result(self, synthetic_data: List[Dict]) -> Dict[str, Any]:
        """Create result dict for synthetic data."""
        return {
            'data': synthetic_data,
            'method': 'synthetic_generation',
            'warning': 'Synthetic data due to source unavailability'
        }
    
    def _create_data_point(self, current_date: datetime, data_source: str) -> Dict:
        """Create single data point for synthetic data."""
        return {
            'timestamp': current_date.isoformat(),
            'value': 0,
            'count': 0,
            'source': data_source,
            'synthetic': True
        }