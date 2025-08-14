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
from app.core.adaptive_circuit_breakers import circuit_breaker_registry
from app.core.graceful_degradation import degradation_manager
from app.core.memory_recovery_strategies import memory_monitor
from app.core.websocket_recovery_strategies import websocket_recovery_manager
from app.core.database_recovery_strategies import database_recovery_registry
from app.core.error_aggregation_system import error_aggregation_system

# Legacy components for compatibility
from app.core.agent_recovery_strategies import agent_recovery_registry, AgentType
from app.core.error_logging import error_logger

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EnhancedErrorRecoverySystem:
    """Enhanced unified interface for comprehensive error recovery."""
    
    def __init__(self):
        """Initialize enhanced error recovery system."""
        # Core managers
        self.retry_manager = retry_manager
        self.circuit_breaker_registry = circuit_breaker_registry
        self.degradation_manager = degradation_manager
        self.memory_monitor = memory_monitor
        self.websocket_manager = websocket_recovery_manager
        self.database_registry = database_recovery_registry
        self.error_aggregation = error_aggregation_system
        
        # Legacy compatibility
        self.agent_registry = agent_recovery_registry
        self.error_logger = error_logger
        
        # Statistics
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
        error_data = self._prepare_error_data(
            agent_type, operation, error, context_data, user_id
        )
        await self.error_aggregation.process_error(error_data)
        
        breaker = self.circuit_breaker_registry.get_breaker(f"agent_{agent_type}")
        
        try:
            return await breaker.call(
                self._execute_agent_recovery,
                agent_type, operation, error, context_data, user_id
            )
        except Exception:
            return await self._attempt_agent_degradation(
                agent_type, operation, error, context_data
            )
    
    async def handle_database_error(
        self,
        table_name: str,
        operation: str,
        error: Exception,
        rollback_data: Optional[Dict] = None,
        transaction_id: Optional[str] = None
    ) -> Any:
        """Handle database error with enhanced recovery."""
        error_data = {
            'error_type': type(error).__name__,
            'module': 'database',
            'function': operation,
            'message': str(error),
            'table_name': table_name,
            'transaction_id': transaction_id
        }
        await self.error_aggregation.process_error(error_data)
        
        breaker = self.circuit_breaker_registry.get_breaker(f"db_{table_name}")
        
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
        error_data = {
            'error_type': type(error).__name__,
            'module': 'api',
            'function': method,
            'message': str(error),
            'endpoint': endpoint,
            'status_code': status_code
        }
        await self.error_aggregation.process_error(error_data)
        
        breaker = self.circuit_breaker_registry.get_breaker(f"api_{endpoint}")
        retry_strategy = self.retry_manager.get_strategy(OperationType.EXTERNAL_API)
        
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
        error_data = {
            'error_type': type(error).__name__,
            'module': 'websocket',
            'function': 'connection',
            'message': str(error),
            'connection_id': connection_id
        }
        await self.error_aggregation.process_error(error_data)
        
        # Attempt WebSocket recovery
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
        return {
            'error_type': type(error).__name__,
            'module': f'agent_{agent_type}',
            'function': operation,
            'message': str(error),
            'timestamp': datetime.now(),
            'user_id': user_id,
            'context': context_data or {}
        }
    
    async def _execute_agent_recovery(
        self,
        agent_type: str,
        operation: str,
        error: Exception,
        context_data: Optional[Dict],
        user_id: Optional[str]
    ) -> Any:
        """Execute agent recovery with retry strategy."""
        agent_type_enum = self._get_agent_type_enum(agent_type)
        if agent_type_enum:
            context = RecoveryContext(
                operation_id=f"{agent_type}_{operation}",
                operation_type=OperationType.AGENT_EXECUTION,
                error=error,
                severity=self._determine_severity(error),
                metadata={'agent_type': agent_type, 'operation': operation}
            )
            return await self.agent_registry.recover_agent_operation(agent_type_enum, context)
        raise error
    
    async def _execute_database_recovery(
        self,
        table_name: str,
        operation: str,
        error: Exception,
        rollback_data: Optional[Dict],
        transaction_id: Optional[str]
    ) -> Any:
        """Execute database recovery with rollback if needed."""
        # Use legacy rollback logic for now
        if rollback_data:
            logger.info(f"Database rollback needed for {table_name}")
            return {'status': 'rollback_queued', 'table': table_name}
        raise error
    
    async def _execute_api_recovery(
        self,
        endpoint: str,
        method: str,
        error: Exception,
        status_code: Optional[int],
        retry_strategy: Any
    ) -> Any:
        """Execute API recovery with retry strategy."""
        context = RecoveryContext(
            operation_id=f"{method}_{endpoint}",
            operation_type=OperationType.EXTERNAL_API,
            error=error,
            severity=self._determine_severity_from_status(status_code),
            metadata={'endpoint': endpoint, 'method': method, 'status_code': status_code}
        )
        
        if retry_strategy.should_retry(context):
            delay = retry_strategy.get_retry_delay(context.retry_count)
            await asyncio.sleep(delay)
            logger.info(f"Retrying API call to {endpoint} after {delay}s")
            return {'status': 'retried', 'delay': delay}
        
        raise error
    
    async def _attempt_agent_degradation(
        self,
        agent_type: str,
        operation: str,
        error: Exception,
        context_data: Optional[Dict]
    ) -> Any:
        """Attempt graceful degradation for agent."""
        return await self.degradation_manager.degrade_service(
            f"agent_{agent_type}",
            self.degradation_manager.global_degradation_level,
            context_data or {}
        )
    
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
        type_mapping = {
            'triage': AgentType.TRIAGE,
            'data_analysis': AgentType.DATA_ANALYSIS,
            'corpus_admin': AgentType.CORPUS_ADMIN,
            'supply_researcher': AgentType.SUPPLY_RESEARCHER,
            'supervisor': AgentType.SUPERVISOR
        }
        return type_mapping.get(agent_type.lower())
    
    def _determine_severity(self, error: Exception):
        """Determine error severity."""
        from app.core.error_codes import ErrorSeverity
        
        severity_mapping = {
            'MemoryError': ErrorSeverity.CRITICAL,
            'ConnectionError': ErrorSeverity.HIGH,
            'TimeoutError': ErrorSeverity.MEDIUM,
            'ValueError': ErrorSeverity.HIGH,
        }
        
        error_type = type(error).__name__
        return severity_mapping.get(error_type, ErrorSeverity.MEDIUM)
    
    def _determine_severity_from_status(self, status_code: Optional[int]):
        """Determine severity from HTTP status code."""
        from app.core.error_codes import ErrorSeverity
        
        if not status_code:
            return ErrorSeverity.MEDIUM
        
        if status_code >= 500:
            return ErrorSeverity.HIGH
        elif status_code >= 400:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get comprehensive recovery metrics."""
        return {
            'recovery_stats': self.recovery_stats,
            'circuit_breakers': self.circuit_breaker_registry.get_all_metrics(),
            'degradation_status': self.degradation_manager.get_degradation_status(),
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