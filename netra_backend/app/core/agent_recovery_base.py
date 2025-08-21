"""
Base agent recovery strategy abstract class and common functionality.
Provides the foundation for all agent-specific recovery strategies.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from netra_backend.app.core.error_recovery import RecoveryContext, ErrorRecoveryManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.agent_recovery_types import AgentRecoveryConfig

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
        self._log_recovery_start(context, assessment)
        result = await self._execute_recovery_cascade(context, assessment)
        if result is not None:
            return result
        await self._handle_recovery_failure(context, assessment)
    
    def _log_recovery_start(self, context: RecoveryContext, assessment: Dict[str, Any]) -> None:
        """Log recovery start with context and assessment."""
        logger.info(
            f"Starting recovery for {self.config.agent_type.value}",
            operation_id=context.operation_id,
            assessment=assessment
        )
    
    async def _execute_recovery_cascade(self, context: RecoveryContext, assessment: Dict[str, Any]) -> Optional[Any]:
        """Execute recovery strategies in cascade order."""
        primary_result = await self._try_primary_recovery(context, assessment)
        if primary_result is not None:
            return primary_result
        fallback_result = await self._try_fallback_recovery(context, assessment)
        if fallback_result is not None:
            return fallback_result
        return await self._try_degraded_recovery(context, assessment)
    
    async def _try_primary_recovery(self, context: RecoveryContext, assessment: Dict[str, Any]) -> Optional[Any]:
        """Try primary recovery if enabled."""
        if assessment.get('try_primary_recovery', True):
            primary_result = await self.execute_primary_recovery(context)
            if primary_result is not None:
                logger.info(f"Primary recovery succeeded for {context.operation_id}")
                return primary_result
        return None
    
    async def _try_fallback_recovery(self, context: RecoveryContext, assessment: Dict[str, Any]) -> Optional[Any]:
        """Try fallback recovery if enabled."""
        if assessment.get('try_fallback_recovery', True) and self.config.fallback_enabled:
            fallback_result = await self.execute_fallback_recovery(context)
            if fallback_result is not None:
                logger.info(f"Fallback recovery succeeded for {context.operation_id}")
                return fallback_result
        return None
    
    async def _try_degraded_recovery(self, context: RecoveryContext, assessment: Dict[str, Any]) -> Optional[Any]:
        """Try degraded mode recovery if enabled."""
        if assessment.get('try_degraded_mode', True) and self.config.allow_degraded_mode:
            degraded_result = await self.execute_degraded_mode(context)
            if degraded_result is not None:
                logger.warning(f"Degraded mode recovery for {context.operation_id}")
                return degraded_result
        return None
    
    async def _handle_recovery_failure(self, context: RecoveryContext, assessment: Dict[str, Any]) -> None:
        """Handle complete recovery failure."""
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
        intervention_data = self._build_intervention_data(context, assessment)
        self._log_manual_intervention_request(intervention_data)
    
    def _build_intervention_data(self, context: RecoveryContext, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Build intervention data for manual escalation."""
        return {
            'operation_id': context.operation_id,
            'agent_type': self.config.agent_type.value,
            'error_summary': str(context.error),
            'assessment': assessment,
            'timestamp': context.started_at.isoformat(),
            'priority': self.config.priority.value
        }
    
    def _log_manual_intervention_request(self, intervention_data: Dict[str, Any]) -> None:
        """Log manual intervention request."""
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
        normalized_message = error_message.lower()
        base_analysis = self._get_base_error_analysis(normalized_message)
        severity_indicators = self._extract_severity_indicators(normalized_message)
        base_analysis['severity_indicators'] = severity_indicators
        return base_analysis
    
    def _get_base_error_analysis(self, error_message: str) -> Dict[str, Any]:
        """Get base error type analysis."""
        return {
            'is_timeout': 'timeout' in error_message,
            'is_connection_error': self._is_connection_error(error_message),
            'is_validation_error': self._is_validation_error(error_message),
            'is_resource_error': self._is_resource_error(error_message),
            'is_permission_error': self._is_permission_error(error_message)
        }
    
    def _is_connection_error(self, error_message: str) -> bool:
        """Check if error is connection-related."""
        connection_terms = ['connection', 'network', 'tcp']
        return any(term in error_message for term in connection_terms)
    
    def _is_validation_error(self, error_message: str) -> bool:
        """Check if error is validation-related."""
        validation_terms = ['validation', 'invalid', 'malformed']
        return any(term in error_message for term in validation_terms)
    
    def _is_resource_error(self, error_message: str) -> bool:
        """Check if error is resource-related."""
        resource_terms = ['memory', 'cpu', 'disk', 'resource']
        return any(term in error_message for term in resource_terms)
    
    def _is_permission_error(self, error_message: str) -> bool:
        """Check if error is permission-related."""
        permission_terms = ['permission', 'unauthorized', 'forbidden']
        return any(term in error_message for term in permission_terms)
    
    def _extract_severity_indicators(self, error_message: str) -> List[str]:
        """Extract severity indicators from error message."""
        indicators = []
        if 'critical' in error_message or 'fatal' in error_message:
            indicators.append('critical')
        if 'warning' in error_message:
            indicators.append('warning')
        return indicators
    
    async def _wait_with_backoff(self, attempt: int) -> None:
        """Wait with exponential backoff."""
        delay = self.config.retry_delay_base * (2 ** attempt)
        await asyncio.sleep(min(delay, 30))  # Cap at 30 seconds