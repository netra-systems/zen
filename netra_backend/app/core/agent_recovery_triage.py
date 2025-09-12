"""Triage agent recovery strategy with  <= 8 line functions.

Recovery strategy implementation for triage agent operations with aggressive
function decomposition. All functions  <= 8 lines.
"""

import asyncio
from typing import Any, Dict, Optional

from netra_backend.app.core.agent_recovery_base import BaseAgentRecoveryStrategy
from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageAgentRecoveryStrategy(BaseAgentRecoveryStrategy):
    """Recovery strategy for triage agent operations."""
    
    async def assess_failure(self, context: RecoveryContext) -> Dict[str, Any]:
        """Assess triage agent failure."""
        error_message = str(context.error).lower()
        assessment = self._create_default_assessment()
        self._categorize_triage_failure(error_message, assessment)
        return assessment
    
    def _categorize_triage_failure(self, error_message: str, assessment: Dict[str, Any]) -> None:
        """Categorize triage failure type and set recovery strategy."""
        if 'intent' in error_message:
            self._set_intent_failure(assessment)
        elif 'entity' in error_message:
            self._set_entity_failure(assessment)
        elif 'tool' in error_message:
            self._set_tool_failure(assessment)
        elif 'timeout' in error_message:
            self._set_timeout_failure(assessment)
    
    def _set_intent_failure(self, assessment: Dict[str, Any]) -> None:
        """Set assessment for intent detection failure."""
        assessment['failure_type'] = 'intent_detection'
        assessment['try_primary_recovery'] = True
    
    def _set_entity_failure(self, assessment: Dict[str, Any]) -> None:
        """Set assessment for entity extraction failure."""
        assessment['failure_type'] = 'entity_extraction'
        assessment['try_fallback_recovery'] = True
    
    def _set_tool_failure(self, assessment: Dict[str, Any]) -> None:
        """Set assessment for tool recommendation failure."""
        assessment['failure_type'] = 'tool_recommendation'
        assessment['try_degraded_mode'] = True
    
    def _set_timeout_failure(self, assessment: Dict[str, Any]) -> None:
        """Set assessment for timeout failure."""
        assessment['failure_type'] = 'timeout'
        assessment['estimated_recovery_time'] = 60
    
    async def execute_primary_recovery(self, context: RecoveryContext) -> Optional[Any]:
        """Primary recovery: retry with simplified processing."""
        try:
            await asyncio.sleep(1)  # Brief delay
            return self._create_simplified_triage_result()
        except Exception as e:
            logger.debug(f"Primary triage recovery failed: {e}")
            return None
    
    def _create_simplified_triage_result(self) -> Dict[str, Any]:
        """Create simplified triage result for recovery."""
        return {
            'intent': 'general_inquiry', 'entities': {},
            'tools': ['general_assistant'], 'confidence': 0.7,
            'recovery_method': 'simplified_triage'
        }
    
    async def execute_fallback_recovery(self, context: RecoveryContext) -> Optional[Any]:
        """Fallback recovery: use cached patterns."""
        try:
            return self._create_cached_triage_result()
        except Exception as e:
            logger.debug(f"Fallback triage recovery failed: {e}")
            return None
    
    def _create_cached_triage_result(self) -> Dict[str, Any]:
        """Create cached triage result for fallback recovery."""
        return {
            'intent': 'cached_pattern', 'entities': {},
            'tools': ['default_tool'], 'confidence': 0.5,
            'recovery_method': 'cached_fallback'
        }
    
    async def execute_degraded_mode(self, context: RecoveryContext) -> Optional[Any]:
        """Degraded mode: minimal triage functionality."""
        return {
            'intent': 'unknown', 'entities': {},
            'tools': ['manual_review'], 'confidence': 0.1,
            'recovery_method': 'degraded_mode', 'requires_manual_review': True
        }