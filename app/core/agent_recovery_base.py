"""
Base agent recovery strategy abstract class and common functionality.
Provides the foundation for all agent-specific recovery strategies.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.core.error_recovery import RecoveryContext, ErrorRecoveryManager
from app.logging_config import central_logger
from .agent_recovery_types import AgentRecoveryConfig

logger = central_logger.get_logger(__name__)


class BaseAgentRecoveryStrategy(ABC):
    """Abstract base class for agent recovery strategies."""
    
    def __init__(self, config: AgentRecoveryConfig):
        """Initialize with agent recovery configuration."""
        self.config = config
        self.recovery_manager = ErrorRecoveryManager()
    
    @abstractmethod
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess the failure and determine recovery approach."""
        pass
    
    @abstractmethod
    async def execute_primary_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Execute the primary recovery strategy."""
        pass
    
    @abstractmethod
    async def execute_fallback_recovery(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Execute fallback recovery if primary fails."""
        pass
    
    @abstractmethod
    async def execute_degraded_mode(
        self,
        context: RecoveryContext
    ) -> Optional[Any]:
        """Execute in degraded mode as last resort."""
        pass
    
    async def recover(self, context: RecoveryContext) -> Any:
        """Execute recovery strategy with escalation."""
        assessment = await self.assess_failure(context)
        
        logger.info(
            f"Starting recovery for {self.config.agent_type.value}",
            operation_id=context.operation_id,
            assessment=assessment
        )
        
        # Try primary recovery
        if assessment.get('try_primary_recovery', True):
            primary_result = await self.execute_primary_recovery(context)
            if primary_result is not None:
                logger.info(f"Primary recovery succeeded for {context.operation_id}")
                return primary_result
        
        # Try fallback recovery
        if assessment.get('try_fallback_recovery', True) and self.config.fallback_enabled:
            fallback_result = await self.execute_fallback_recovery(context)
            if fallback_result is not None:
                logger.info(f"Fallback recovery succeeded for {context.operation_id}")
                return fallback_result
        
        # Try degraded mode
        if assessment.get('try_degraded_mode', True) and self.config.allow_degraded_mode:
            degraded_result = await self.execute_degraded_mode(context)
            if degraded_result is not None:
                logger.warning(f"Degraded mode recovery for {context.operation_id}")
                return degraded_result
        
        # If all recovery attempts failed
        if self.config.require_manual_intervention:
            await self._trigger_manual_intervention(context, assessment)
        
        logger.error(f"All recovery attempts failed for {context.operation_id}")
        raise Exception(f"Recovery failed for {self.config.agent_type.value}")
    
    async def _trigger_manual_intervention(
        self,
        context: RecoveryContext,
        assessment: Dict[str, Any]
    ) -> None:
        """Trigger manual intervention for complex failures."""
        intervention_data = {
            'operation_id': context.operation_id,
            'agent_type': self.config.agent_type.value,
            'error_summary': str(context.error),
            'assessment': assessment,
            'timestamp': context.started_at.isoformat(),
            'priority': self.config.priority.value
        }
        
        # In a real system, this would notify operators
        logger.critical(
            f"Manual intervention required for {self.config.agent_type.value}",
            intervention_data=intervention_data
        )
    
    def _create_default_assessment(self) -> Dict[str, Any]:
        """Create default failure assessment."""
        return {
            'failure_type': 'unknown',
            'try_primary_recovery': True,
            'try_fallback_recovery': True,
            'try_degraded_mode': True,
            'estimated_recovery_time': 30  # seconds
        }
    
    def _analyze_error_message(self, error_message: str) -> Dict[str, Any]:
        """Analyze error message for common patterns."""
        error_message = error_message.lower()
        analysis = {
            'is_timeout': 'timeout' in error_message,
            'is_connection_error': any(term in error_message for term in ['connection', 'network', 'tcp']),
            'is_validation_error': any(term in error_message for term in ['validation', 'invalid', 'malformed']),
            'is_resource_error': any(term in error_message for term in ['memory', 'cpu', 'disk', 'resource']),
            'is_permission_error': any(term in error_message for term in ['permission', 'unauthorized', 'forbidden']),
            'severity_indicators': []
        }
        
        # Add severity indicators
        if 'critical' in error_message or 'fatal' in error_message:
            analysis['severity_indicators'].append('critical')
        if 'warning' in error_message:
            analysis['severity_indicators'].append('warning')
        
        return analysis
    
    async def _wait_with_backoff(self, attempt: int) -> None:
        """Wait with exponential backoff."""
        delay = self.config.retry_delay_base * (2 ** attempt)
        await asyncio.sleep(min(delay, 30))  # Cap at 30 seconds