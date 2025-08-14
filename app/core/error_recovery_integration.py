"""Integration module for comprehensive error recovery system.

Provides unified interface for error recovery across all system components
with automatic strategy selection and comprehensive monitoring.
"""

import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime

from app.core.error_recovery import (
    RecoveryContext,
    OperationType,
    recovery_manager,
    recovery_executor
)
from app.core.agent_recovery_strategies import (
    AgentType,
    agent_recovery_registry
)
from app.core.error_logging import (
    error_logger,
    log_agent_error,
    log_database_error,
    log_api_error
)
from app.services.transaction_manager import transaction_manager
from app.services.compensation_engine import compensation_engine, saga_orchestrator
from app.services.database.rollback_manager import rollback_manager
from app.agents.error_handler import global_error_handler
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UnifiedErrorRecoverySystem:
    """Unified interface for comprehensive error recovery."""
    
    def __init__(self):
        """Initialize unified error recovery system."""
        self.recovery_manager = recovery_manager
        self.recovery_executor = recovery_executor
        self.transaction_manager = transaction_manager
        self.compensation_engine = compensation_engine
        self.saga_orchestrator = saga_orchestrator
        self.rollback_manager = rollback_manager
        self.agent_registry = agent_recovery_registry
        self.error_logger = error_logger
        
        # Integration statistics
        self.recovery_stats = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'recovery_by_type': {},
            'recovery_by_agent': {}
        }
    
    async def handle_agent_error(
        self,
        agent_type: str,
        operation: str,
        error: Exception,
        context_data: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Any:
        """Handle agent error with full recovery pipeline."""
        # Log error with comprehensive context
        error_id = log_agent_error(
            agent_type=agent_type,
            operation=operation,
            error=error,
            user_id=user_id,
            **(context_data or {})
        )
        
        try:
            # Create recovery context
            recovery_context = RecoveryContext(
                operation_id=error_id,
                operation_type=OperationType.AGENT_EXECUTION,
                error=error,
                severity=self._determine_severity(error),
                metadata={
                    'agent_type': agent_type,
                    'operation': operation,
                    'user_id': user_id,
                    **(context_data or {})
                }
            )
            
            # Try agent-specific recovery strategy
            agent_type_enum = self._get_agent_type_enum(agent_type)
            if agent_type_enum:
                result = await self.agent_registry.recover_agent_operation(
                    agent_type_enum, recovery_context
                )
                
                self._update_recovery_stats(agent_type, True)
                self.error_logger.log_recovery_attempt(
                    recovery_context, 'agent_specific_recovery', True
                )
                
                return result
            
            # Fallback to general recovery
            result = await self.recovery_executor.attempt_recovery(recovery_context)
            
            success = result.success if result else False
            self._update_recovery_stats(agent_type, success)
            
            if success:
                self.error_logger.log_recovery_attempt(
                    recovery_context, 'general_recovery', True
                )
                return result.result_data
            else:
                self.error_logger.log_recovery_attempt(
                    recovery_context, 'general_recovery', False,
                    {'error_message': result.error_message if result else 'Unknown error'}
                )
                raise error
            
        except Exception as recovery_error:
            self._update_recovery_stats(agent_type, False)
            logger.error(f"Recovery failed for agent {agent_type}: {recovery_error}")
            raise recovery_error
    
    async def handle_database_error(
        self,
        table_name: str,
        operation: str,
        error: Exception,
        rollback_data: Optional[Dict] = None,
        transaction_id: Optional[str] = None
    ) -> Any:
        """Handle database error with transaction management."""
        # Log database error
        error_id = log_database_error(
            table_name=table_name,
            operation=operation,
            error=error,
            transaction_id=transaction_id
        )
        
        try:
            # If part of transaction, handle with transaction manager
            if transaction_id:
                await self.transaction_manager.rollback_transaction(transaction_id)
                logger.info(f"Rolled back transaction: {transaction_id}")
                return {'status': 'rolled_back', 'transaction_id': transaction_id}
            
            # If rollback data provided, use rollback manager
            if rollback_data:
                session_id = await self.rollback_manager.create_rollback_session({
                    'error_id': error_id,
                    'table_name': table_name,
                    'operation': operation
                })
                
                await self.rollback_manager.add_rollback_operation(
                    session_id=session_id,
                    table_name=table_name,
                    operation_type=operation,
                    rollback_data=rollback_data
                )
                
                success = await self.rollback_manager.execute_rollback_session(session_id)
                
                if success:
                    logger.info(f"Database rollback successful: {error_id}")
                    return {'status': 'rolled_back', 'session_id': session_id}
                else:
                    logger.error(f"Database rollback failed: {error_id}")
            
            # Fallback: log and re-raise
            raise error
            
        except Exception as recovery_error:
            logger.error(f"Database recovery failed: {recovery_error}")
            raise recovery_error
    
    async def handle_api_error(
        self,
        endpoint: str,
        method: str,
        error: Exception,
        status_code: Optional[int] = None,
        retry_config: Optional[Dict] = None
    ) -> Any:
        """Handle API error with retry and circuit breaking."""
        # Log API error
        error_id = log_api_error(
            endpoint=endpoint,
            method=method,
            error=error,
            status_code=status_code
        )
        
        try:
            # Create recovery context
            recovery_context = RecoveryContext(
                operation_id=error_id,
                operation_type=OperationType.EXTERNAL_API,
                error=error,
                severity=self._determine_severity_from_status(status_code),
                metadata={
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': status_code
                }
            )
            
            # Check circuit breaker
            circuit_breaker = self.recovery_manager.get_circuit_breaker(endpoint)
            if not circuit_breaker.should_allow_request():
                raise Exception(f"Circuit breaker open for {endpoint}")
            
            # Attempt recovery
            result = await self.recovery_executor.attempt_recovery(recovery_context)
            
            if result.success:
                circuit_breaker.record_success()
                return result.result_data
            else:
                circuit_breaker.record_failure()
                raise error
                
        except Exception as recovery_error:
            logger.error(f"API recovery failed for {endpoint}: {recovery_error}")
            raise recovery_error
    
    async def handle_compensation_required(
        self,
        operation_id: str,
        compensation_data: Dict[str, Any],
        operation_type: OperationType
    ) -> bool:
        """Handle operations requiring compensation."""
        try:
            # Create recovery context for compensation
            recovery_context = RecoveryContext(
                operation_id=operation_id,
                operation_type=operation_type,
                error=Exception("Compensation required"),
                severity=self._determine_severity(Exception("Compensation required")),
                metadata=compensation_data
            )
            
            # Create compensation action
            action_id = await self.compensation_engine.create_compensation_action(
                operation_id=operation_id,
                context=recovery_context,
                compensation_data=compensation_data
            )
            
            # Execute compensation
            success = await self.compensation_engine.execute_compensation(action_id)
            
            self.error_logger.log_recovery_attempt(
                recovery_context, 'compensation', success,
                {'action_id': action_id}
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Compensation failed for operation {operation_id}: {e}")
            return False
    
    async def execute_saga_transaction(
        self,
        saga_name: str,
        steps: List[Dict[str, Any]],
        metadata: Optional[Dict] = None
    ) -> bool:
        """Execute saga transaction with automatic compensation."""
        try:
            # Convert steps to SagaStep objects
            from app.services.compensation_engine import SagaStep
            
            saga_steps = []
            for i, step in enumerate(steps):
                saga_step = SagaStep(
                    step_id=f"step_{i}",
                    name=step['name'],
                    forward_action=step['forward_action'],
                    compensation_action=step['compensation_action'],
                    forward_params=step.get('forward_params', {}),
                    compensation_params=step.get('compensation_params', {})
                )
                saga_steps.append(saga_step)
            
            # Create and execute saga
            saga_id = await self.saga_orchestrator.create_saga(
                name=saga_name,
                steps=saga_steps,
                metadata=metadata
            )
            
            success = await self.saga_orchestrator.execute_saga(saga_id)
            
            # Log saga result
            logger.info(
                f"Saga transaction {'completed' if success else 'failed'}: {saga_name}",
                saga_id=saga_id,
                steps_count=len(steps)
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Saga transaction failed: {saga_name}: {e}")
            return False
    
    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get comprehensive recovery metrics."""
        return {
            'unified_system': self.recovery_stats,
            'error_patterns': self.error_logger.get_error_patterns(),
            'logging_metrics': self.error_logger.get_metrics(),
            'circuit_breakers': {
                name: {
                    'state': cb.state,
                    'failure_count': cb.failure_count,
                    'last_failure': cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for name, cb in self.recovery_manager.circuit_breakers.items()
            }
        }
    
    def generate_recovery_report(self) -> Dict[str, Any]:
        """Generate comprehensive recovery report."""
        from app.core.error_logging import error_report_generator
        
        summary_report = error_report_generator.generate_summary_report()
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'error_summary': summary_report,
            'recovery_metrics': self.get_recovery_metrics(),
            'system_health': {
                'active_transactions': len(self.transaction_manager.active_transactions),
                'active_compensations': len(self.compensation_engine.active_compensations),
                'active_sagas': len(self.saga_orchestrator.active_sagas),
                'active_rollbacks': len(self.rollback_manager.active_sessions)
            }
        }
    
    def _get_agent_type_enum(self, agent_type: str) -> Optional[AgentType]:
        """Convert string agent type to enum."""
        type_mapping = {
            'triage': AgentType.TRIAGE,
            'triage_sub_agent': AgentType.TRIAGE,
            'data_analysis': AgentType.DATA_ANALYSIS,
            'data_sub_agent': AgentType.DATA_ANALYSIS,
            'corpus_admin': AgentType.CORPUS_ADMIN,
            'corpus_admin_sub_agent': AgentType.CORPUS_ADMIN,
            'supply_researcher': AgentType.SUPPLY_RESEARCHER,
            'supervisor': AgentType.SUPERVISOR,
            'optimization': AgentType.OPTIMIZATION,
            'reporting': AgentType.REPORTING,
            'synthetic_data': AgentType.SYNTHETIC_DATA,
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
            'TypeError': ErrorSeverity.HIGH,
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
    
    def _update_recovery_stats(self, agent_type: str, success: bool) -> None:
        """Update recovery statistics."""
        self.recovery_stats['total_recoveries'] += 1
        
        if success:
            self.recovery_stats['successful_recoveries'] += 1
        else:
            self.recovery_stats['failed_recoveries'] += 1
        
        if agent_type not in self.recovery_stats['recovery_by_agent']:
            self.recovery_stats['recovery_by_agent'][agent_type] = {
                'total': 0, 'successful': 0, 'failed': 0
            }
        
        stats = self.recovery_stats['recovery_by_agent'][agent_type]
        stats['total'] += 1
        if success:
            stats['successful'] += 1
        else:
            stats['failed'] += 1


# Global unified error recovery system
unified_recovery_system = UnifiedErrorRecoverySystem()


# Convenience functions for common operations
async def recover_agent_operation(
    agent_type: str,
    operation: str,
    error: Exception,
    **kwargs
) -> Any:
    """Convenience function for agent error recovery."""
    return await unified_recovery_system.handle_agent_error(
        agent_type, operation, error, kwargs
    )


async def recover_database_operation(
    table_name: str,
    operation: str,
    error: Exception,
    **kwargs
) -> Any:
    """Convenience function for database error recovery."""
    return await unified_recovery_system.handle_database_error(
        table_name, operation, error, **kwargs
    )


async def recover_api_operation(
    endpoint: str,
    method: str,
    error: Exception,
    **kwargs
) -> Any:
    """Convenience function for API error recovery."""
    return await unified_recovery_system.handle_api_error(
        endpoint, method, error, **kwargs
    )