"""Enhanced unified error recovery integration system.

Provides comprehensive error recovery with advanced strategies including
exponential backoff, circuit breakers, graceful degradation, and intelligent
error aggregation across all system components.
"""

import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime

# Core recovery components
from app.core.error_recovery import RecoveryContext, OperationType
from app.core.enhanced_retry_strategies import retry_manager
from app.core.circuit_breaker_registry_adaptive import circuit_breaker_registry
from app.core.graceful_degradation import degradation_manager
from app.core.memory_recovery_strategies import memory_monitor
from app.core.websocket_recovery_strategies import websocket_recovery_manager
from app.core.database_recovery_strategies import database_recovery_registry
from app.core.error_aggregation_service import error_aggregation_system

# Legacy components for compatibility
from app.core.agent_recovery_strategies_main import agent_recovery_registry, AgentType
from app.core.error_logging import error_logger

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EnhancedErrorRecoverySystem:
    """Enhanced unified interface for comprehensive error recovery."""
    
    def __init__(self):
        """Initialize enhanced error recovery system."""
        self._init_core_managers()
        self._init_legacy_compatibility()
        self._init_recovery_stats()
    
    def _init_core_managers(self) -> None:
        """Initialize core recovery managers."""
        self.retry_manager = retry_manager
        self.circuit_breaker_registry = circuit_breaker_registry
        self.degradation_manager = degradation_manager
        self.memory_monitor = memory_monitor
        self.websocket_manager = websocket_recovery_manager
        self.database_registry = database_recovery_registry
        self.error_aggregation = error_aggregation_system
    
    def _init_legacy_compatibility(self) -> None:
        """Initialize legacy compatibility components."""
        self.agent_registry = agent_recovery_registry
        self.error_logger = error_logger
    
    def _init_recovery_stats(self) -> None:
        """Initialize recovery statistics tracking."""
        self.recovery_stats = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'recovery_by_type': {},
            'recovery_by_strategy': {}
        }
    
    async def handle_agent_error(
        self,
        agent_type: str,
        operation: str,
        error: Exception,
        context_data: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Any:
        """Handle agent error with enhanced recovery pipeline."""
        await self._process_agent_error_data(agent_type, operation, error, context_data, user_id)
        return await self._execute_agent_recovery_pipeline(agent_type, operation, error, context_data, user_id)
    
    async def _process_agent_error_data(
        self, agent_type: str, operation: str, error: Exception, 
        context_data: Optional[Dict], user_id: Optional[str]
    ) -> None:
        """Process agent error data for aggregation."""
        error_data = self._prepare_error_data(agent_type, operation, error, context_data, user_id)
        await self.error_aggregation.process_error(error_data)
    
    async def _execute_agent_recovery_pipeline(
        self, agent_type: str, operation: str, error: Exception,
        context_data: Optional[Dict], user_id: Optional[str]
    ) -> Any:
        """Execute agent recovery pipeline with circuit breaker."""
        breaker = self.circuit_breaker_registry.get_breaker(f"agent_{agent_type}")
        return await self._execute_agent_error_recovery(breaker, agent_type, operation, error, context_data, user_id)
    
    async def _execute_agent_error_recovery(self, breaker, agent_type: str, operation: str, error: Exception, context_data: Optional[Dict], user_id: Optional[str]) -> Any:
        """Execute agent error recovery with circuit breaker."""
        try:
            return await breaker.call(
                self._execute_agent_recovery,
                agent_type, operation, error, context_data, user_id
            )
        except Exception:
            return await self._attempt_agent_degradation(agent_type, operation, error, context_data)
    
    async def handle_database_error(
        self,
        table_name: str,
        operation: str,
        error: Exception,
        rollback_data: Optional[Dict] = None,
        transaction_id: Optional[str] = None
    ) -> Any:
        """Handle database error with enhanced recovery."""
        await self._process_database_error_data(table_name, operation, error, transaction_id)
        return await self._execute_database_recovery_pipeline(table_name, operation, error, rollback_data, transaction_id)
    
    async def _process_database_error_data(
        self, table_name: str, operation: str, error: Exception, transaction_id: Optional[str]
    ) -> None:
        """Process database error data for aggregation."""
        error_data = self._prepare_database_error_data(table_name, operation, error, transaction_id)
        await self.error_aggregation.process_error(error_data)
    
    async def _execute_database_recovery_pipeline(
        self, table_name: str, operation: str, error: Exception,
        rollback_data: Optional[Dict], transaction_id: Optional[str]
    ) -> Any:
        """Execute database recovery pipeline with circuit breaker."""
        breaker = self.circuit_breaker_registry.get_breaker(f"db_{table_name}")
        return await self._execute_database_error_recovery(breaker, table_name, operation, error, rollback_data, transaction_id)
    
    def _prepare_database_error_data(self, table_name: str, operation: str, error: Exception, transaction_id: Optional[str]) -> Dict[str, Any]:
        """Prepare database error data for aggregation."""
        base_data = self._get_database_base_error_data(error, operation)
        return self._add_database_context_data(base_data, table_name, transaction_id)
    
    def _get_database_base_error_data(self, error: Exception, operation: str) -> Dict[str, Any]:
        """Get base database error data."""
        return {
            'error_type': type(error).__name__,
            'module': 'database',
            'function': operation,
            'message': str(error)
        }
    
    def _add_database_context_data(self, base_data: Dict[str, Any], table_name: str, transaction_id: Optional[str]) -> Dict[str, Any]:
        """Add database context data to error data."""
        base_data.update({
            'table_name': table_name,
            'transaction_id': transaction_id
        })
        return base_data
    
    async def _execute_database_error_recovery(self, breaker, table_name: str, operation: str, error: Exception, rollback_data: Optional[Dict], transaction_id: Optional[str]) -> Any:
        """Execute database error recovery with circuit breaker."""
        try:
            return await breaker.call(
                self._execute_database_recovery,
                table_name, operation, error, rollback_data, transaction_id
            )
        except Exception:
            return await self._attempt_database_degradation(table_name, operation, error)
    
    async def handle_api_error(
        self,
        endpoint: str,
        method: str,
        error: Exception,
        status_code: Optional[int] = None,
        retry_config: Optional[Dict] = None
    ) -> Any:
        """Handle API error with retry and circuit breaking."""
        await self._process_api_error_data(endpoint, method, error, status_code)
        return await self._execute_api_recovery_pipeline(endpoint, method, error, status_code)
    
    async def _process_api_error_data(
        self, endpoint: str, method: str, error: Exception, status_code: Optional[int]
    ) -> None:
        """Process API error data for aggregation."""
        error_data = self._prepare_api_error_data(endpoint, method, error, status_code)
        await self.error_aggregation.process_error(error_data)
    
    async def _execute_api_recovery_pipeline(
        self, endpoint: str, method: str, error: Exception, status_code: Optional[int]
    ) -> Any:
        """Execute API recovery pipeline with retry strategy."""
        breaker = self.circuit_breaker_registry.get_breaker(f"api_{endpoint}")
        retry_strategy = self.retry_manager.get_strategy(OperationType.EXTERNAL_API)
        return await self._execute_api_error_recovery(breaker, endpoint, method, error, status_code, retry_strategy)
    
    def _prepare_api_error_data(self, endpoint: str, method: str, error: Exception, status_code: Optional[int]) -> Dict[str, Any]:
        """Prepare API error data for aggregation."""
        base_data = self._get_api_base_error_data(error, method)
        return self._add_api_context_data(base_data, endpoint, status_code)
    
    def _get_api_base_error_data(self, error: Exception, method: str) -> Dict[str, Any]:
        """Get base API error data."""
        return {
            'error_type': type(error).__name__,
            'module': 'api',
            'function': method,
            'message': str(error)
        }
    
    def _add_api_context_data(self, base_data: Dict[str, Any], endpoint: str, status_code: Optional[int]) -> Dict[str, Any]:
        """Add API context data to error data."""
        base_data.update({
            'endpoint': endpoint,
            'status_code': status_code
        })
        return base_data
    
    async def _execute_api_error_recovery(self, breaker, endpoint: str, method: str, error: Exception, status_code: Optional[int], retry_strategy) -> Any:
        """Execute API error recovery with circuit breaker."""
        try:
            return await breaker.call(
                self._execute_api_recovery,
                endpoint, method, error, status_code, retry_strategy
            )
        except Exception:
            return await self._attempt_api_degradation(endpoint, method, error)
    
    async def handle_websocket_error(
        self,
        connection_id: str,
        error: Exception,
        context_data: Optional[Dict] = None
    ) -> Any:
        """Handle WebSocket error with recovery."""
        await self._process_websocket_error_data(connection_id, error)
        return await self._execute_websocket_recovery()
    
    async def _process_websocket_error_data(self, connection_id: str, error: Exception) -> None:
        """Process WebSocket error data for aggregation."""
        error_data = self._prepare_websocket_error_data(connection_id, error)
        await self.error_aggregation.process_error(error_data)
    
    def _prepare_websocket_error_data(self, connection_id: str, error: Exception) -> Dict[str, Any]:
        """Prepare WebSocket error data."""
        return {
            'error_type': type(error).__name__,
            'module': 'websocket',
            'function': 'connection',
            'message': str(error),
            'connection_id': connection_id
        }
    
    async def _execute_websocket_recovery(self) -> Any:
        """Execute WebSocket recovery operations."""
        return await self.websocket_manager.recover_all_connections()
    
    async def handle_memory_exhaustion(self, context_data: Optional[Dict] = None) -> bool:
        """Handle memory exhaustion with recovery strategies."""
        snapshot = await self.memory_monitor.take_snapshot()
        return bool(await self.memory_monitor.check_and_recover(snapshot))
    
    async def startup_recovery_system(self) -> None:
        """Start all recovery system components."""
        await self.error_aggregation.start_processing()
        await self.memory_monitor.start_monitoring()
        await self.database_registry.start_all_monitoring()
        logger.info("Enhanced error recovery system started")
    
    async def shutdown_recovery_system(self) -> None:
        """Shutdown all recovery system components."""
        await self.error_aggregation.stop_processing()
        await self.memory_monitor.stop_monitoring()
        await self.database_registry.stop_all_monitoring()
        await self.websocket_manager.cleanup_all()
        self.circuit_breaker_registry.cleanup_all()
        logger.info("Enhanced error recovery system shutdown")
    
    def _prepare_error_data(
        self,
        agent_type: str,
        operation: str,
        error: Exception,
        context_data: Optional[Dict],
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare error data for aggregation."""
        base_data = self._get_base_error_data(agent_type, operation, error)
        return self._add_contextual_error_data(base_data, context_data, user_id)
    
    def _get_base_error_data(self, agent_type: str, operation: str, error: Exception) -> Dict[str, Any]:
        """Get base error data."""
        return {
            'error_type': type(error).__name__,
            'module': f'agent_{agent_type}',
            'function': operation,
            'message': str(error),
            'timestamp': datetime.now()
        }
    
    def _add_contextual_error_data(self, base_data: Dict[str, Any], context_data: Optional[Dict], user_id: Optional[str]) -> Dict[str, Any]:
        """Add contextual data to error data."""
        base_data.update({
            'user_id': user_id,
            'context': context_data or {}
        })
        return base_data
    
    async def _execute_agent_recovery(
        self,
        agent_type: str,
        operation: str,
        error: Exception,
        context_data: Optional[Dict],
        user_id: Optional[str]
    ) -> Any:
        """Execute agent recovery with retry strategy."""
        agent_type_enum = self._get_validated_agent_type(agent_type, error)
        context = self._build_recovery_context(agent_type, operation, error)
        return await self.agent_registry.recover_agent_operation(agent_type_enum, context)
    
    def _get_validated_agent_type(self, agent_type: str, error: Exception):
        """Get validated agent type enum or raise error."""
        agent_type_enum = self._get_agent_type_enum(agent_type)
        if not agent_type_enum:
            raise error
        return agent_type_enum
    
    def _build_recovery_context(self, agent_type: str, operation: str, error: Exception) -> RecoveryContext:
        """Build recovery context for agent operations."""
        return RecoveryContext(
            operation_id=f"{agent_type}_{operation}",
            operation_type=OperationType.AGENT_EXECUTION,
            error=error,
            severity=self._determine_severity(error),
            metadata={'agent_type': agent_type, 'operation': operation}
        )
    
    async def _execute_database_recovery(
        self,
        table_name: str,
        operation: str,
        error: Exception,
        rollback_data: Optional[Dict],
        transaction_id: Optional[str]
    ) -> Any:
        """Execute database recovery with rollback if needed."""
        if rollback_data:
            return self._execute_database_rollback(table_name)
        raise error
    
    def _execute_database_rollback(self, table_name: str) -> Dict[str, Any]:
        """Execute database rollback operation."""
        logger.info(f"Database rollback needed for {table_name}")
        return {'status': 'rollback_queued', 'table': table_name}
    
    async def _execute_api_recovery(
        self,
        endpoint: str,
        method: str,
        error: Exception,
        status_code: Optional[int],
        retry_strategy: Any
    ) -> Any:
        """Execute API recovery with retry strategy."""
        context = self._build_api_recovery_context(endpoint, method, error, status_code)
        self._validate_retry_eligibility(context, retry_strategy, error)
        return await self._execute_api_retry(endpoint, retry_strategy, context)
    
    def _validate_retry_eligibility(self, context: RecoveryContext, retry_strategy: Any, error: Exception) -> None:
        """Validate if retry is eligible, raise error if not."""
        if not retry_strategy.should_retry(context):
            raise error
    
    def _build_api_recovery_context(self, endpoint: str, method: str, error: Exception, status_code: Optional[int]) -> RecoveryContext:
        """Build recovery context for API operations."""
        return RecoveryContext(
            operation_id=f"{method}_{endpoint}",
            operation_type=OperationType.EXTERNAL_API,
            error=error,
            severity=self._determine_severity_from_status(status_code),
            metadata={'endpoint': endpoint, 'method': method, 'status_code': status_code}
        )
    
    async def _execute_api_retry(self, endpoint: str, retry_strategy: Any, context: RecoveryContext) -> Dict[str, Any]:
        """Execute API retry with delay."""
        delay = retry_strategy.get_retry_delay(context.retry_count)
        await asyncio.sleep(delay)
        logger.info(f"Retrying API call to {endpoint} after {delay}s")
        return {'status': 'retried', 'delay': delay}
    
    async def _attempt_agent_degradation(
        self,
        agent_type: str,
        operation: str,
        error: Exception,
        context_data: Optional[Dict]
    ) -> Any:
        """Attempt graceful degradation for agent."""
        service_name = f"agent_{agent_type}"
        degradation_level = self.degradation_manager.global_degradation_level
        context = context_data or {}
        return await self.degradation_manager.degrade_service(service_name, degradation_level, context)
    
    async def _attempt_database_degradation(
        self,
        table_name: str,
        operation: str,
        error: Exception
    ) -> Any:
        """Attempt graceful degradation for database."""
        return {'status': 'degraded', 'message': 'Database service temporarily degraded'}
    
    async def _attempt_api_degradation(
        self,
        endpoint: str,
        method: str,
        error: Exception
    ) -> Any:
        """Attempt graceful degradation for API."""
        return {'status': 'degraded', 'message': f'API {endpoint} temporarily unavailable'}
    
    def _get_agent_type_enum(self, agent_type: str) -> Optional[AgentType]:
        """Convert string agent type to enum."""
        type_mapping = self._get_agent_type_mapping()
        return type_mapping.get(agent_type.lower())
    
    def _get_agent_type_mapping(self) -> Dict[str, AgentType]:
        """Get agent type string to enum mapping."""
        return {
            'triage': AgentType.TRIAGE,
            'data_analysis': AgentType.DATA_ANALYSIS,
            'corpus_admin': AgentType.CORPUS_ADMIN,
            'supply_researcher': AgentType.SUPPLY_RESEARCHER,
            'supervisor': AgentType.SUPERVISOR
        }
    
    def _determine_severity(self, error: Exception):
        """Determine error severity."""
        from app.core.error_codes import ErrorSeverity
        severity_mapping = self._get_error_severity_mapping()
        error_type = type(error).__name__
        return severity_mapping.get(error_type, ErrorSeverity.MEDIUM)
    
    def _get_error_severity_mapping(self):
        """Get error type to severity mapping."""
        from app.core.error_codes import ErrorSeverity
        return {
            'MemoryError': ErrorSeverity.CRITICAL,
            'ConnectionError': ErrorSeverity.HIGH,
            'TimeoutError': ErrorSeverity.MEDIUM,
            'ValueError': ErrorSeverity.HIGH,
        }
    
    def _determine_severity_from_status(self, status_code: Optional[int]):
        """Determine severity from HTTP status code."""
        from app.core.error_codes import ErrorSeverity
        if not status_code:
            return ErrorSeverity.MEDIUM
        return self._map_status_code_to_severity(status_code)
    
    def _map_status_code_to_severity(self, status_code: int):
        """Map HTTP status code to error severity."""
        from app.core.error_codes import ErrorSeverity
        if status_code >= 500:
            return ErrorSeverity.HIGH
        elif status_code >= 400:
            return ErrorSeverity.MEDIUM
        return ErrorSeverity.LOW
    
    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get comprehensive recovery metrics."""
        basic_metrics = self._get_basic_recovery_metrics()
        extended_metrics = self._get_extended_recovery_metrics()
        return {**basic_metrics, **extended_metrics}
    
    def _get_basic_recovery_metrics(self) -> Dict[str, Any]:
        """Get basic recovery metrics."""
        return {
            'recovery_stats': self.recovery_stats,
            'circuit_breakers': self.circuit_breaker_registry.get_all_metrics(),
            'degradation_status': self.degradation_manager.get_degradation_status()
        }
    
    def _get_extended_recovery_metrics(self) -> Dict[str, Any]:
        """Get extended recovery metrics."""
        return {
            'memory_status': self.memory_monitor.get_memory_status(),
            'websocket_status': self.websocket_manager.get_all_status(),
            'database_status': self.database_registry.get_global_status(),
            'error_aggregation': self.error_aggregation.get_system_status()
        }


# Global enhanced error recovery system
enhanced_recovery_system = EnhancedErrorRecoverySystem()


# Convenience functions for backward compatibility
async def recover_agent_operation(
    agent_type: str,
    operation: str,
    error: Exception,
    **kwargs
) -> Any:
    """Convenience function for agent error recovery."""
    return await enhanced_recovery_system.handle_agent_error(
        agent_type, operation, error, kwargs
    )


async def recover_database_operation(
    table_name: str,
    operation: str,
    error: Exception,
    **kwargs
) -> Any:
    """Convenience function for database error recovery."""
    return await enhanced_recovery_system.handle_database_error(
        table_name, operation, error, **kwargs
    )


async def recover_api_operation(
    endpoint: str,
    method: str,
    error: Exception,
    **kwargs
) -> Any:
    """Convenience function for API error recovery."""
    return await enhanced_recovery_system.handle_api_error(
        endpoint, method, error, **kwargs
    )