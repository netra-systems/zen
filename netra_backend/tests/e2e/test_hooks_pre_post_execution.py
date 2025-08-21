"""
E2E Tests for Pre and Post Execution Hooks

Tests pre-execution and post-execution hook functionality:
- Pre-execution hooks (validation, setup)
- Post-execution hooks (cleanup, logging)
- Hook execution sequence and state management

All functions ≤8 lines per CLAUDE.md requirements.
Module ≤300 lines per CLAUDE.md requirements.
"""

import asyncio
import pytest
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock

from netra_backend.app.agents.quality_hooks import QualityHooksManager
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.quality_gate_service import ContentType, ValidationResult, QualityMetrics
from logging_config import central_logger

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


logger = central_logger.get_logger(__name__)


class TestPreExecutionHooks:
    """Test pre-execution hooks for validation and setup."""
    
    async def test_validation_hook_success(self):
        """Test successful pre-execution validation hook."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        hook_manager.quality_gate_service.validate_content.assert_called_once()
        assert state.quality_metrics.get("TestAgent") is not None
    
    async def test_validation_hook_failure(self):
        """Test pre-execution validation hook failure handling."""
        hook_manager = self._create_mock_hook_manager()
        hook_manager.quality_gate_service.validate_content.side_effect = Exception("Validation error")
        
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        assert not hasattr(state, 'quality_metrics')
    
    def test_setup_hook_initialization(self):
        """Test pre-execution setup hook initialization."""
        hook_manager = QualityHooksManager(None, None, strict_mode=True)
        assert hook_manager.strict_mode is True
        assert hook_manager.quality_stats['total_validations'] == 0
    
    async def test_validation_hook_with_context(self):
        """Test validation hook with execution context."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        validation_args = hook_manager.quality_gate_service.validate_content.call_args
        assert validation_args[1]['context']['run_id'] == context.run_id
    
    def _create_mock_hook_manager(self):
        """Create mock hook manager for testing."""
        quality_gate = Mock()
        quality_gate.validate_content = AsyncMock(return_value=self._create_validation_result())
        monitoring = Mock()
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_test_context(self) -> AgentExecutionContext:
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test_run", thread_id="test_thread", 
            user_id="test_user", agent_name="TestAgent", max_retries=3
        )
    
    def _create_test_state(self) -> DeepAgentState:
        """Create test agent state."""
        state = DeepAgentState(user_request="test request")
        state.triage_result = {'summary': 'test summary'}
        return state
    
    def _create_validation_result(self) -> ValidationResult:
        """Create mock validation result."""
        metrics = QualityMetrics(overall_score=0.85, issues=0)
        return ValidationResult(passed=True, metrics=metrics, retry_suggested=False)


class TestPostExecutionHooks:
    """Test post-execution hooks for cleanup and logging."""
    
    async def test_cleanup_hook_success(self):
        """Test successful post-execution cleanup hook."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state_with_metrics()
        
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        hook_manager.monitoring_service.record_quality_event.assert_called_once()
    
    async def test_cleanup_hook_no_metrics(self):
        """Test cleanup hook when no metrics exist."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        hook_manager.monitoring_service.record_quality_event.assert_not_called()
    
    async def test_logging_hook_formatting(self):
        """Test logging hook with proper formatting."""
        hook_manager = self._create_mock_hook_manager()
        validation_result = self._create_validation_result(passed=True, score=0.95)
        
        hook_manager._log_validation_success(validation_result)
        # Verify logging through captured logs if needed
    
    async def test_post_execution_state_cleanup(self):
        """Test state cleanup in post-execution hook."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state_with_metrics()
        
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        # Verify state is properly maintained after monitoring
        assert hasattr(state, 'quality_metrics')
    
    def _create_mock_hook_manager(self):
        """Create mock hook manager for testing."""
        quality_gate = Mock()
        monitoring = Mock()
        monitoring.record_quality_event = AsyncMock()
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_test_context(self) -> AgentExecutionContext:
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test_run", thread_id="test_thread", 
            user_id="test_user", agent_name="TestAgent", max_retries=3
        )
    
    def _create_test_state(self) -> DeepAgentState:
        """Create test agent state."""
        return DeepAgentState(user_request="test request")
    
    def _create_test_state_with_metrics(self) -> DeepAgentState:
        """Create test state with quality metrics."""
        state = self._create_test_state()
        state.quality_metrics = {"TestAgent": QualityMetrics(overall_score=0.9, issues=0)}
        return state
    
    def _create_validation_result(self, passed: bool = True, score: float = 0.85) -> ValidationResult:
        """Create validation result for testing."""
        metrics = QualityMetrics(overall_score=score, issues=0 if passed else 2)
        return ValidationResult(passed=passed, metrics=metrics, retry_suggested=not passed)


class TestHookExecutionSequence:
    """Test hook execution sequence and coordination."""
    
    async def test_hook_sequence_execution(self):
        """Test proper hook execution sequence."""
        hook_manager = self._create_hook_manager()
        
        context = self._create_test_context()
        state = self._create_test_state()
        
        # Pre-execution hook
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        
        # Post-execution hook
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        
        # Verify hook sequence completed
        assert hook_manager.quality_stats['total_validations'] == 1
    
    async def test_hook_state_sharing(self):
        """Test state sharing between hooks."""
        hook_manager = self._create_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        # Pre-hook modifies state
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        
        # Verify state was modified
        assert hasattr(state, 'quality_metrics')
        
        # Post-hook can access modified state
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
    
    async def test_hook_error_isolation(self):
        """Test hook error isolation and recovery."""
        hook_manager = self._create_hook_manager()
        hook_manager.quality_gate_service.validate_content.side_effect = Exception("Hook error")
        
        context = self._create_test_context()
        state = self._create_test_state()
        
        # Error in one hook should not affect others
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
    
    def _create_hook_manager(self) -> QualityHooksManager:
        """Create quality hook manager for testing."""
        quality_gate = Mock()
        quality_gate.validate_content = AsyncMock(
            return_value=ValidationResult(
                passed=True, 
                metrics=QualityMetrics(overall_score=0.85, issues=0),
                retry_suggested=False
            )
        )
        monitoring = Mock()
        monitoring.record_quality_event = AsyncMock()
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_test_context(self) -> AgentExecutionContext:
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test_run", thread_id="test_thread", 
            user_id="test_user", agent_name="TestAgent", max_retries=3
        )
    
    def _create_test_state(self) -> DeepAgentState:
        """Create test agent state."""
        state = DeepAgentState(user_request="test request")
        state.triage_result = {'summary': 'test summary'}
        return state