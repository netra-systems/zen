"""Refactored Data Sub Agent Error Handler - Main coordination layer.

Coordinates between specialized recovery managers for different operation types.
Maintains compatibility with existing interface while using modular components.
"""

import asyncio
from typing import Any, Dict, List

from app.core.error_recovery import CompensationAction, RecoveryContext, OperationType
from app.agents.error_handler import global_error_handler
from app.logging_config import central_logger

# Import modular components
from .error_types import DataSubAgentError, ClickHouseQueryError, DataFetchingError, MetricsCalculationError
from .clickhouse_recovery import ClickHouseRecoveryManager
from .data_fetching_recovery import DataFetchingRecoveryManager
from .metrics_recovery import MetricsRecoveryManager
from .fallback_providers import FallbackDataProvider

logger = central_logger.get_logger(__name__)


class DataAnalysisCompensation(CompensationAction):
    """Compensation action for data analysis operations."""
    
    def __init__(self, cache_manager, data_store):
        """Initialize with cache and data store managers."""
        self.cache_manager = cache_manager
        self.data_store = data_store
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute compensation for data analysis operations."""
        try:
            await self._cleanup_temp_data(context.metadata.get('temp_data_keys', []))
            await self._invalidate_cache_entries(context.metadata.get('cache_keys', []))
            
            logger.info(f"Data analysis compensation completed: {context.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Data analysis compensation failed: {e}")
            return False
    
    def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate data analysis operations."""
        return context.operation_type in [OperationType.DATABASE_READ, OperationType.CACHE_OPERATION]
    
    async def _cleanup_temp_data(self, temp_keys: List[str]) -> None:
        """Clean up temporary data entries."""
        for key in temp_keys:
            try:
                await self.data_store.delete(key)
                logger.debug(f"Cleaned up temp data: {key}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp data {key}: {e}")
    
    async def _invalidate_cache_entries(self, cache_keys: List[str]) -> None:
        """Invalidate related cache entries."""
        if cache_keys and self.cache_manager:
            await self.cache_manager.invalidate_keys(cache_keys)


class DataSubAgentErrorHandler:
    """Main error handler coordinating specialized recovery managers."""
    
    def __init__(self, clickhouse_client=None, cache_manager=None):
        """Initialize error handler with specialized managers."""
        self.clickhouse_recovery = ClickHouseRecoveryManager(clickhouse_client, cache_manager)
        self.data_fetching_recovery = DataFetchingRecoveryManager(cache_manager)
        self.metrics_recovery = MetricsRecoveryManager()
        self.fallback_provider = FallbackDataProvider(cache_manager)
        
        # Legacy query fallbacks mapping
        self.query_fallbacks = {
            'performance_metrics': self.fallback_provider.get_performance_metrics_fallback,
            'usage_patterns': self.fallback_provider.get_usage_patterns_fallback,
            'cost_analysis': self.fallback_provider.get_cost_analysis_fallback,
            'error_analysis': self.fallback_provider.get_error_analysis_fallback,
        }
    
    async def handle_clickhouse_error(
        self,
        query: str,
        query_type: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle ClickHouse query failures with fallback strategies."""
        try:
            # Try recovery strategies first
            recovery_result = await self.clickhouse_recovery.handle_query_failure(
                query, query_type, run_id, original_error
            )
            if recovery_result:
                return recovery_result
            
            # Try fallback data provider
            fallback_func = self.query_fallbacks.get(query_type)
            if fallback_func:
                fallback_result = await fallback_func(run_id)
                logger.info(f"ClickHouse query recovered with fallback data")
                return fallback_result
            
            # If all else fails, raise the error
            raise ClickHouseQueryError(query, str(original_error))
            
        except Exception as error:
            await self._handle_unrecoverable_error(error, run_id)
            raise
    
    async def handle_data_fetching_error(
        self,
        data_source: str,
        time_range: Dict,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle data fetching failures."""
        try:
            return await self.data_fetching_recovery.handle_fetching_failure(
                data_source, time_range, run_id, original_error
            )
        except Exception as error:
            await self._handle_unrecoverable_error(error, run_id)
            raise
    
    async def handle_metrics_calculation_error(
        self,
        metric_type: str,
        data: List[Dict],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle metrics calculation failures."""
        try:
            return await self.metrics_recovery.handle_calculation_failure(
                metric_type, data, run_id, original_error
            )
        except Exception as error:
            await self._handle_unrecoverable_error(error, run_id)
            raise
    
    async def _handle_unrecoverable_error(self, error: Exception, run_id: str) -> None:
        """Handle errors that cannot be recovered."""
        if isinstance(error, DataSubAgentError) and error.context:
            await global_error_handler.handle_error(error, error.context)
        else:
            logger.error(f"Unrecoverable data sub agent error: {error}")


# Global data sub agent error handler instance
data_sub_agent_error_handler = DataSubAgentErrorHandler()