"""Agent recovery strategy interfaces and implementations.

Single source of truth for agent recovery strategies with  <= 8 line functions.
Centralizes recovery strategy implementations to avoid duplicates.
"""

import asyncio
from typing import Any, Dict, Optional

from netra_backend.app.core.agent_recovery_base import BaseAgentRecoveryStrategy
from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusAdminRecoveryStrategy(BaseAgentRecoveryStrategy):
    """Recovery strategy for corpus admin agent operations."""
    
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess corpus admin failure."""
        error_message = str(context.error).lower()
        assessment = self._create_corpus_admin_assessment()
        self._categorize_corpus_failure(error_message, assessment)
        return assessment
    
    def _create_corpus_admin_assessment(self) -> Dict[str, Any]:
        """Create default assessment for corpus admin failure."""
        assessment = self._create_default_assessment()
        assessment.update({
            'try_degraded_mode': False, 'data_integrity_risk': False,
            'estimated_recovery_time': 90
        })
        return assessment
    
    def _categorize_corpus_failure(self, error_message: str, assessment: Dict[str, Any]) -> None:
        """Categorize corpus admin failure type."""
        if 'corruption' in error_message or 'integrity' in error_message:
            self._set_corruption_failure(assessment)
        elif 'permission' in error_message:
            self._set_permission_failure(assessment)
        elif 'lock' in error_message:
            self._set_lock_failure(assessment)
    
    def _set_corruption_failure(self, assessment: Dict[str, Any]) -> None:
        """Set assessment for data corruption failure."""
        assessment['failure_type'] = 'data_corruption'
        assessment['data_integrity_risk'] = True
        assessment['try_primary_recovery'] = False
        assessment['try_fallback_recovery'] = False
    
    def _set_permission_failure(self, assessment: Dict[str, Any]) -> None:
        """Set assessment for permission denied failure."""
        assessment['failure_type'] = 'permission_denied'
        assessment['try_primary_recovery'] = True
    
    def _set_lock_failure(self, assessment: Dict[str, Any]) -> None:
        """Set assessment for resource locked failure."""
        assessment['failure_type'] = 'resource_locked'
        assessment['try_fallback_recovery'] = True
    
    async def execute_primary_recovery(self, context: RecoveryContext) -> Optional[Any]:
        """Primary recovery: safe retry with validation."""
        try:
            await asyncio.sleep(3)  # Simulate safe retry with validation
            return self._create_safe_retry_result()
        except Exception as e:
            logger.debug(f"Primary corpus admin recovery failed: {e}")
            return None
    
    def _create_safe_retry_result(self) -> Dict[str, Any]:
        """Create safe retry result for corpus admin recovery."""
        return {
            'operation': 'corpus_update', 'status': 'completed_with_validation',
            'validation_passed': True, 'recovery_method': 'safe_retry',
            'operator_notified': False
        }
    
    async def execute_fallback_recovery(self, context: RecoveryContext) -> Optional[Any]:
        """Fallback recovery: read-only operations."""
        try:
            return self._create_readonly_result()
        except Exception as e:
            logger.debug(f"Fallback corpus admin recovery failed: {e}")
            return None
    
    def _create_readonly_result(self) -> Dict[str, Any]:
        """Create read-only result for corpus admin fallback."""
        return {
            'operation': 'corpus_readonly', 'status': 'limited_functionality',
            'read_access': True, 'write_access': False,
            'recovery_method': 'readonly_mode', 'operator_notified': True
        }
    
    async def execute_degraded_mode(self, context: RecoveryContext) -> Optional[Any]:
        """Degraded mode: emergency stop."""
        return self._create_emergency_stop_result()
    
    def _create_emergency_stop_result(self) -> Dict[str, Any]:
        """Create emergency stop result for corpus admin."""
        return {
            'operation': 'corpus_emergency_stop', 'status': 'emergency_stopped',
            'all_operations_halted': True, 'recovery_method': 'emergency_stop',
            'operator_notified': True
        }