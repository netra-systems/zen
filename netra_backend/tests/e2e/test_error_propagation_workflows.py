"""
E2E Tests for Error Propagation and Real Workflow Integration

Tests error propagation through layers and real workflow integration:
- Error propagation through middleware layers
- Recovery coordination across different layers
- Real workflow integration points
- Agent workflow hooks integration

All functions ≤8 lines per CLAUDE.md requirements.
Module ≤300 lines per CLAUDE.md requirements.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request, Response
from logging_config import central_logger

from netra_backend.app.agents.quality_hooks import QualityHooksManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.core.agent_reliability_mixin import AgentReliabilityMixin
from netra_backend.app.core.exceptions_auth import NetraSecurityException

# Add project root to path
from netra_backend.app.middleware.security_middleware import SecurityMiddleware
from netra_backend.app.services.quality_gate_service import (
    QualityMetrics,
    ValidationResult,
)

# Add project root to path

logger = central_logger.get_logger(__name__)


class TestErrorPropagationThroughLayers:
    """Test error propagation through middleware layers."""
    
    async def test_authentication_error_propagation(self):
        """Test authentication error propagation."""
        middleware = self._create_security_middleware()
        
        # Simulate authentication failure
        middleware.track_auth_attempt("192.168.1.1", success=False)
        
        # Verify error is tracked
        assert middleware.failed_auth_ips.get("192.168.1.1", 0) == 1
    
    async def test_validation_error_propagation(self):
        """Test validation error propagation through layers."""
        middleware = self._create_security_middleware()
        
        with patch.object(middleware.input_validator, 'validate_input') as validate_mock:
            validate_mock.side_effect = NetraSecurityException("Validation failed")
            
            with pytest.raises(NetraSecurityException):
                middleware._validate_decoded_body(b"test data")
    
    async def test_rate_limit_error_propagation(self):
        """Test rate limit error propagation."""
        from fastapi import HTTPException
        
        middleware = self._create_security_middleware()
        
        with pytest.raises(HTTPException) as exc_info:
            middleware._raise_rate_limit_exception("Rate limit exceeded")
        
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers
    
    async def test_circuit_breaker_error_propagation(self):
        """Test circuit breaker error propagation."""
        middleware = self._create_security_middleware()
        
        # Simulate multiple authentication failures to trigger pattern
        for i in range(12):  # Exceed typical thresholds
            middleware.track_auth_attempt("192.168.1.1", success=False)
        
        # Verify suspicious IP detection
        assert middleware.is_ip_suspicious("192.168.1.1")
    
    def _create_security_middleware(self) -> SecurityMiddleware:
        """Create security middleware instance for testing."""
        return SecurityMiddleware(None)


class TestRecoveryCoordinationAcrossLayers:
    """Test recovery coordination across different layers."""
    
    async def test_hook_middleware_recovery_coordination(self):
        """Test recovery coordination between hooks and middleware."""
        hook_manager = self._create_hook_manager()
        mixin = self._create_reliability_mixin()
        
        async def failing_operation():
            raise ValueError("Test error")
        
        # Test that error propagates and recovery is attempted
        with pytest.raises(ValueError):
            await mixin.execute_with_reliability(failing_operation, "test_op")
        
        # Verify error was recorded
        assert len(mixin.error_history) == 1
    
    async def test_multi_layer_error_handling(self):
        """Test error handling across multiple layers."""
        hook_manager = self._create_hook_manager()
        middleware = self._create_security_middleware()
        mixin = self._create_reliability_mixin()
        
        # Simulate error in hook layer
        context = self._create_test_context()
        state = self._create_test_state()
        
        with patch.object(hook_manager.quality_gate_service, 'validate_content') as validate_mock:
            validate_mock.side_effect = Exception("Hook error")
            
            # Error should be handled gracefully
            await hook_manager.quality_validation_hook(context, "TestAgent", state)
            
            # State should not have metrics due to error
            assert not hasattr(state, 'quality_metrics')
    
    async def test_recovery_strategy_coordination(self):
        """Test recovery strategy coordination between components."""
        mixin = self._create_reliability_mixin()
        
        async def custom_recovery(error, context):
            return {"recovered": True, "strategy": "custom", "error": str(error)}
        
        # Register custom recovery strategy
        mixin.register_recovery_strategy("coordinated_op", custom_recovery)
        
        async def failing_operation():
            raise ConnectionError("Network failure")
        
        # Test coordinated recovery
        result = await mixin.execute_with_reliability(failing_operation, "coordinated_op")
        assert result["recovered"] is True
        assert result["strategy"] == "custom"
    
    async def test_fallback_chain_coordination(self):
        """Test fallback chain coordination across layers."""
        mixin = self._create_reliability_mixin()
        
        # Test default fallback strategies
        llm_fallback = await mixin._default_llm_recovery(ValueError("LLM error"), {})
        db_fallback = await mixin._default_db_recovery(ConnectionError("DB error"), {})
        api_fallback = await mixin._default_api_recovery(TimeoutError("API timeout"), {})
        
        # Verify all fallbacks provide recovery
        assert llm_fallback["fallback_used"] is True
        assert db_fallback["fallback_used"] is True
        assert api_fallback["fallback_used"] is True
    
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
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_security_middleware(self) -> SecurityMiddleware:
        """Create security middleware instance for testing."""
        return SecurityMiddleware(None)
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()
    
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


class TestRealWorkflowIntegration:
    """Test real workflow integration points."""
    
    async def test_agent_workflow_hooks_integration(self):
        """Test agent workflows integrate with hook system."""
        hook_manager = self._create_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        # Test pre-execution hook
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        
        # Test post-execution hook
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        
        # Verify workflow completed successfully
        assert hook_manager.quality_stats['total_validations'] == 1
    
    async def test_middleware_agent_coordination(self):
        """Test middleware coordination with agent systems."""
        middleware = self._create_security_middleware()
        mixin = self._create_reliability_mixin()
        
        # Test that middleware and agent reliability work together
        async def test_operation():
            return "success"
        
        # Simulate agent operation with reliability
        result = await mixin.execute_with_reliability(test_operation, "test_op")
        assert result == "success"
        
        # Verify operation was tracked
        assert len(mixin.operation_times) == 1
    
    async def test_complete_request_processing_chain(self):
        """Test complete request processing through all layers."""
        hook_manager = self._create_hook_manager()
        middleware = self._create_security_middleware()
        
        # Simulate complete request processing
        request = self._create_mock_request()
        
        # Pre-processing validation
        middleware._validate_headers(request)
        
        # Agent processing with hooks
        context = self._create_test_context()
        state = self._create_test_state()
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        
        # Post-processing
        response = Mock(spec=Response)
        response.headers = {}
        middleware._add_security_headers(response)
        
        # Verify complete chain
        assert "X-Security-Middleware" in response.headers
        assert hook_manager.quality_stats['total_validations'] == 1
    
    async def test_end_to_end_error_recovery(self):
        """Test end-to-end error recovery across all components."""
        hook_manager = self._create_hook_manager()
        middleware = self._create_security_middleware()
        mixin = self._create_reliability_mixin()
        
        # Simulate error in the middle of processing chain
        async def failing_workflow():
            # Pre-processing (middleware layer)
            request = self._create_mock_request()
            middleware._validate_headers(request)
            
            # Agent processing with error
            async def failing_operation():
                raise ValueError("Workflow error")
            
            return await mixin.execute_with_reliability(failing_operation, "workflow_op")
        
        # Test that error is handled and recorded
        with pytest.raises(ValueError):
            await failing_workflow()
        
        # Verify error was captured in reliability system
        assert len(mixin.error_history) == 1
        assert mixin.error_history[0].message == "Workflow error"
    
    async def test_quality_gates_with_middleware_security(self):
        """Test quality gates integration with middleware security."""
        hook_manager = self._create_hook_manager()
        middleware = self._create_security_middleware()
        
        request = self._create_mock_request()
        middleware._validate_headers(request)
        context = self._create_test_context()
        state = self._create_test_state()
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        assert hasattr(state, 'quality_metrics')
    
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
    
    def _create_security_middleware(self) -> SecurityMiddleware:
        """Create security middleware instance for testing."""
        return SecurityMiddleware(None)
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()
    
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
    
    def _create_mock_request(self) -> Mock:
        """Create mock request for testing."""
        request = Mock(spec=Request)
        request.headers = {}
        request.method = "GET"
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com")
        request.url.path = "/test"
        return request