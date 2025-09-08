"""Degradation strategy implementations for different service types.

This module contains concrete implementations of degradation strategies
for database, LLM, and WebSocket services.
"""

from typing import Any, Dict, List, Set

from netra_backend.app.core.degradation_types import (
    DegradationLevel,
    DegradationStrategy,
)
# WebSocket manager import moved to function level to avoid import-time initialization
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseDegradationStrategy(DegradationStrategy):
    """Degradation strategy for database operations."""
    
    def __init__(self, read_replicas: List[str], cache_manager):
        """Initialize with read replicas and cache."""
        self.read_replicas = read_replicas
        self.cache_manager = cache_manager
        self.current_replica_index = 0
    
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade database operations based on level."""
        if level == DegradationLevel.REDUCED:
            return await self._use_read_replica(context)
        elif level == DegradationLevel.MINIMAL:
            return await self._use_cache_only(context)
        elif level == DegradationLevel.EMERGENCY:
            return await self._return_default_data(context)
        return None
    
    async def can_restore_service(self) -> bool:
        """Check if primary database is available."""
        try:
            return await self._test_database_connection()
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False
    
    async def _test_database_connection(self) -> bool:
        """Test primary database connection."""
        from netra_backend.app.db.postgres import get_postgres_client
        db_client = await get_postgres_client()
        if db_client:
            await db_client.execute("SELECT 1")
            return True
        return False
    
    async def _use_read_replica(self, context: Dict[str, Any]) -> Any:
        """Use read replica for operations."""
        replica = self._get_next_replica()
        logger.info(f"Using read replica: {replica}")
        return {'data': 'replica_data', 'source': 'replica'}
    
    def _get_next_replica(self) -> str:
        """Get next available replica in round-robin."""
        replica = self.read_replicas[self.current_replica_index]
        self.current_replica_index = (
            (self.current_replica_index + 1) % len(self.read_replicas)
        )
        return replica
    
    async def _use_cache_only(self, context: Dict[str, Any]) -> Any:
        """Use cached data only."""
        cache_key = context.get('cache_key', 'default')
        try:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                return self._format_cache_response(cached_data)
        except Exception as e:
            logger.warning(f"Cache access failed: {e}")
        return await self._return_default_data(context)
    
    def _format_cache_response(self, cached_data: Any) -> Dict[str, Any]:
        """Format cached data response."""
        logger.info("Serving from cache only")
        return {
            'data': cached_data,
            'source': 'cache',
            'stale': True
        }
    
    async def _return_default_data(self, context: Dict[str, Any]) -> Any:
        """Return default/static data."""
        logger.warning("Returning default data due to database unavailability")
        return {
            'data': {'status': 'service_degraded'},
            'source': 'default',
            'message': 'Service temporarily degraded'
        }


class LLMDegradationStrategy(DegradationStrategy):
    """Degradation strategy for LLM operations."""
    
    def __init__(self, fallback_models: List[str], template_responses: Dict[str, str]):
        """Initialize with fallback models and templates."""
        self.fallback_models = fallback_models
        self.template_responses = template_responses
        self.current_model_index = 0
    
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade LLM operations based on level."""
        if level == DegradationLevel.REDUCED:
            return await self._use_smaller_model(context)
        elif level == DegradationLevel.MINIMAL:
            return await self._use_template_response(context)
        elif level == DegradationLevel.EMERGENCY:
            return await self._return_error_message(context)
        return None
    
    async def can_restore_service(self) -> bool:
        """Check if primary LLM is available."""
        try:
            return await self._test_llm_connection()
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False
    
    async def _test_llm_connection(self) -> bool:
        """Test primary LLM connection."""
        from netra_backend.app.llm.llm_manager import llm_manager
        if llm_manager and llm_manager.enabled:
            response = await llm_manager.complete("test", max_tokens=1)
            return response is not None
        return False
    
    async def _use_smaller_model(self, context: Dict[str, Any]) -> Any:
        """Use smaller/faster model."""
        if self.fallback_models:
            model = self._get_next_fallback_model()
            return self._format_fallback_response(model)
        return await self._use_template_response(context)
    
    def _get_next_fallback_model(self) -> str:
        """Get next fallback model in round-robin."""
        model = self.fallback_models[self.current_model_index]
        self.current_model_index = (
            (self.current_model_index + 1) % len(self.fallback_models)
        )
        return model
    
    def _format_fallback_response(self, model: str) -> Dict[str, Any]:
        """Format fallback model response."""
        logger.info(f"Using fallback model: {model}")
        return {
            'response': 'Simplified response from fallback model',
            'model': model,
            'degraded': True
        }
    
    async def _use_template_response(self, context: Dict[str, Any]) -> Any:
        """Use pre-defined template responses."""
        intent = context.get('intent', 'general')
        template = self._get_template_for_intent(intent)
        logger.info("Using template response due to LLM unavailability")
        return {
            'response': template,
            'source': 'template',
            'degraded': True
        }
    
    def _get_template_for_intent(self, intent: str) -> str:
        """Get template response for given intent."""
        return self.template_responses.get(
            intent,
            self.template_responses.get('general', 'Service unavailable')
        )
    
    async def _return_error_message(self, context: Dict[str, Any]) -> Any:
        """Return service unavailable message."""
        return {
            'response': 'I apologize, but AI services are temporarily unavailable. Please try again later.',
            'source': 'error',
            'service_available': False
        }


class WebSocketDegradationStrategy(DegradationStrategy):
    """Degradation strategy for WebSocket operations."""
    
    def __init__(self, polling_fallback: bool = True):
        """Initialize with polling fallback option."""
        self.polling_fallback = polling_fallback
        self.degraded_connections: Set[str] = set()
    
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade WebSocket operations based on level."""
        if level == DegradationLevel.REDUCED:
            return await self._reduce_message_frequency(context)
        elif level == DegradationLevel.MINIMAL:
            return await self._switch_to_polling(context)
        elif level == DegradationLevel.EMERGENCY:
            return await self._disable_real_time_updates(context)
        return None
    
    async def can_restore_service(self) -> bool:
        """Check if WebSocket service can be restored."""
        try:
            return await self._test_websocket_health()
        except Exception as e:
            logger.warning(f"WebSocket health check failed: {e}")
            return False
    
    async def _test_websocket_health(self) -> bool:
        """Test WebSocket manager health."""
        from netra_backend.app.websocket_core.manager import websocket_manager
        if websocket_manager and hasattr(websocket_manager, 'core'):
            stats = websocket_manager.get_stats()
            return stats.total_errors < 10  # Configurable threshold
        return False
    
    async def _reduce_message_frequency(self, context: Dict[str, Any]) -> Any:
        """Reduce message frequency to conserve resources."""
        connection_id = context.get('connection_id')
        self.degraded_connections.add(connection_id)
        logger.info(f"Reducing message frequency for connection {connection_id}")
        return {
            'action': 'frequency_reduced',
            'interval': 5.0,
            'degraded': True
        }
    
    async def _switch_to_polling(self, context: Dict[str, Any]) -> Any:
        """Switch to HTTP polling instead of WebSocket."""
        if self.polling_fallback:
            logger.info("Switching to HTTP polling fallback")
            return {
                'action': 'polling_fallback',
                'poll_interval': 10.0,
                'endpoint': '/api/poll'
            }
        return await self._disable_real_time_updates(context)
    
    async def _disable_real_time_updates(self, context: Dict[str, Any]) -> Any:
        """Disable real-time updates entirely."""
        logger.warning("Disabling real-time updates")
        return {
            'action': 'disabled',
            'message': 'Real-time updates temporarily disabled'
        }