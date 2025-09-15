"""
Comprehensive Unit Test Suite for UnifiedErrorHandler

MISSION CRITICAL: This class is the SSOT for ALL error handling across the platform.
Error handling failures can cascade through the entire system and break business value delivery.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability & Error Consistency
- Value Impact: Prevents error-related cascade failures, ensures consistent error experience
- Strategic Impact: Single source of truth for all error patterns (API, Agent, WebSocket, Database)

Coverage Requirements:
- 100% line coverage of UnifiedErrorHandler core methods
- All error classification patterns (Database, Validation, Network, Agent, WebSocket, etc.)
- Recovery strategy selection and execution
- Error context creation and processing
- Debug information extraction (development vs production)
- Integration with domain-specific handlers (API, Agent, WebSocket)
- Metrics tracking and error statistics
- Security validations for debug information

Test Categories:
- Happy Path Tests: Standard error handling works correctly
- Classification Tests: Errors are categorized correctly 
- Recovery Tests: Recovery strategies are selected and executed properly
- Context Tests: Error context is created and passed correctly
- Security Tests: Debug information is properly sanitized
- Integration Tests: Domain-specific handlers work correctly
- Metrics Tests: Error statistics and tracking work correctly
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, Request

# SSOT imports using absolute paths
from netra_backend.app.core.unified_error_handler import (
    UnifiedErrorHandler,
    APIErrorHandler, 
    AgentErrorHandler,
    WebSocketErrorHandler,
    RecoveryStrategy,
    RetryRecoveryStrategy,
    FallbackRecoveryStrategy,
    api_error_handler,
    agent_error_handler,
    websocket_error_handler,
    handle_error,
    handle_exception,
    get_http_status_code,
    get_error_statistics
)
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.error_response_models import ErrorResponse
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext


@pytest.mark.unit
class TestUnifiedErrorHandlerInitialization:
    """Test UnifiedErrorHandler initialization and configuration."""
    
    def test_unified_error_handler_initializes_with_defaults(self):
        """Test UnifiedErrorHandler initializes with proper default configuration."""
        handler = UnifiedErrorHandler()
        
        assert handler.max_history == 1000
        assert len(handler.error_history) == 0
        assert 'total_errors' in handler._error_metrics
        assert 'recovery_attempts' in handler._error_metrics
        assert handler._error_metrics['total_errors'] == 0
        
    def test_unified_error_handler_initializes_recovery_strategies(self):
        """Test recovery strategies are properly initialized."""
        handler = UnifiedErrorHandler()
        
        assert 'retry' in handler._recovery_strategies
        assert 'database_retry' in handler._recovery_strategies
        assert 'llm_retry' in handler._recovery_strategies
        assert 'network_retry' in handler._recovery_strategies
        
        assert isinstance(handler._recovery_strategies['retry'], RetryRecoveryStrategy)
        assert isinstance(handler._recovery_strategies['database_retry'], RetryRecoveryStrategy)
        
    def test_unified_error_handler_initializes_status_mappings(self):
        """Test HTTP status code mappings are properly initialized."""
        handler = UnifiedErrorHandler()
        
        assert handler._status_mappings[ErrorCode.VALIDATION_ERROR] == 422
        assert handler._status_mappings[ErrorCode.AUTHENTICATION_FAILED] == 401
        assert handler._status_mappings[ErrorCode.DATABASE_ERROR] == 500
        assert handler._status_mappings['VALIDATION_ERROR'] == 422  # String mapping


@pytest.mark.unit  
class TestUnifiedErrorHandlerErrorClassification:
    """Test error classification and categorization."""
    
    def setup_method(self):
        """Setup fresh handler for each test."""
        self.handler = UnifiedErrorHandler()
        
    def test_classify_database_error_correctly(self):
        """Test database errors are classified correctly."""
        error = SQLAlchemyError("Database connection failed")
        context = ErrorContext(trace_id="test-123", operation="database_query")
        
        error_info = self.handler._classify_error(error, context)
        
        assert error_info['category'] == ErrorCategory.DATABASE
        assert error_info['error_type'] == 'SQLAlchemyError'
        assert error_info['is_recoverable'] is True
        assert 'error_id' in error_info
        
    def test_classify_validation_error_correctly(self):
        """Test validation errors are classified correctly."""
        error = ValidationError("Invalid input format", [])
        context = ErrorContext(trace_id="test-123", operation="validation")
        
        error_info = self.handler._classify_error(error, context)
        
        assert error_info['category'] == ErrorCategory.VALIDATION
        assert error_info['severity'] == ErrorSeverity.MEDIUM
        assert error_info['is_recoverable'] is False
        
    def test_classify_agent_error_correctly(self):
        """Test agent errors are classified correctly."""
        error = AgentError(
            message="Agent execution failed",
            severity=ErrorSeverity.HIGH,
            recoverable=True
        )
        context = ErrorContext(trace_id="test-123", operation="agent_execution")
        
        error_info = self.handler._classify_error(error, context)
        
        assert error_info['category'] == ErrorCategory.PROCESSING
        assert error_info['is_recoverable'] is True
        
    def test_classify_http_error_correctly(self):
        """Test HTTP errors are classified correctly."""
        error = HTTPException(status_code=404, detail="Not found")
        context = ErrorContext(trace_id="test-123", operation="api_request")
        
        error_info = self.handler._classify_error(error, context)
        
        assert error_info['category'] == ErrorCategory.NETWORK
        assert error_info['message'] == "Not found"
        
    def test_classify_timeout_error_correctly(self):
        """Test timeout errors are classified correctly."""
        error = asyncio.TimeoutError("Operation timed out")
        context = ErrorContext(trace_id="test-123", operation="async_operation")
        
        error_info = self.handler._classify_error(error, context)
        
        assert error_info['category'] == ErrorCategory.TIMEOUT
        assert error_info['severity'] == ErrorSeverity.LOW
        assert error_info['is_recoverable'] is True


@pytest.mark.unit
class TestUnifiedErrorHandlerRecoveryStrategies():
    """Test recovery strategy selection and execution."""
    
    def setup_method(self):
        """Setup fresh handler for each test."""
        self.handler = UnifiedErrorHandler()
        
    def test_select_database_recovery_strategy(self):
        """Test database errors select database retry strategy."""
        error = SQLAlchemyError("Connection lost")
        
        strategy = self.handler._select_recovery_strategy(error)
        
        assert strategy == self.handler._recovery_strategies['database_retry']
        
    def test_select_llm_recovery_strategy(self):
        """Test LLM/Agent errors select LLM retry strategy."""
        error = AgentError("LLM API rate limited", ErrorSeverity.MEDIUM)
        
        strategy = self.handler._select_recovery_strategy(error)
        
        assert strategy == self.handler._recovery_strategies['llm_retry']
        
    def test_select_network_recovery_strategy(self):
        """Test network errors select network retry strategy."""
        error = HTTPException(status_code=503, detail="Service unavailable")
        
        strategy = self.handler._select_recovery_strategy(error)
        
        assert strategy == self.handler._recovery_strategies['network_retry']
        
    @pytest.mark.asyncio
    async def test_attempt_recovery_with_recoverable_error(self):
        """Test recovery is attempted for recoverable errors."""
        error = asyncio.TimeoutError("Request timed out")
        context = ErrorContext(trace_id="test-123", operation="test_operation")
        
        # Mock operation that succeeds on retry
        async def mock_operation():
            return "success"
        
        result = await self.handler._attempt_recovery(error, context, mock_operation)
        
        # Should attempt recovery and succeed (mocked)
        assert self.handler._error_metrics['recovery_attempts'] > 0
        
    @pytest.mark.asyncio
    async def test_no_recovery_for_non_recoverable_error(self):
        """Test recovery is not attempted for non-recoverable errors."""
        error = ValidationError("Invalid format", [])
        context = ErrorContext(trace_id="test-123", operation="validation")
        
        async def mock_operation():
            return "success"
        
        result = await self.handler._attempt_recovery(error, context, mock_operation)
        
        assert result is None  # No recovery attempted
        
    @pytest.mark.asyncio
    async def test_recovery_updates_metrics_on_success(self):
        """Test successful recovery updates metrics correctly."""
        initial_recovery_attempts = self.handler._error_metrics['recovery_attempts']
        initial_recovery_successes = self.handler._error_metrics['recovery_successes']
        
        error = asyncio.TimeoutError("Timeout")
        context = ErrorContext(trace_id="test-123", operation="test")
        
        # Mock successful recovery
        with patch.object(self.handler._recovery_strategies['retry'], 'attempt_recovery', 
                          return_value="recovered_result"):
            result = await self.handler._attempt_recovery(error, context, lambda: "test")
        
        assert self.handler._error_metrics['recovery_attempts'] == initial_recovery_attempts + 1
        assert self.handler._error_metrics['recovery_successes'] == initial_recovery_successes + 1


@pytest.mark.unit
class TestUnifiedErrorHandlerDebugInformation():
    """Test debug information extraction and security."""
    
    def setup_method(self):
        """Setup fresh handler for each test."""
        self.handler = UnifiedErrorHandler()
        
    @patch('shared.isolated_environment.get_environment_manager')
    def test_extract_debug_info_in_development(self, mock_env_manager):
        """Test debug info is extracted in development environment."""
        # Mock development environment
        mock_env = Mock()
        mock_env.is_production.return_value = False
        mock_env.is_development.return_value = True
        mock_env.is_staging.return_value = False
        mock_env_manager.return_value = mock_env
        
        try:
            raise ValueError("Test error for debugging")
        except ValueError as error:
            debug_info = self.handler._extract_debug_info(error)
        
        assert 'error_type' in debug_info
        assert debug_info['error_type'] == 'ValueError'
        assert 'error_module' in debug_info
        
    @patch('shared.isolated_environment.get_environment_manager')
    def test_no_debug_info_in_production(self, mock_env_manager):
        """Test debug info is not extracted in production environment."""
        # Mock production environment
        mock_env = Mock()
        mock_env.is_production.return_value = True
        mock_env.is_development.return_value = False
        mock_env.is_staging.return_value = False
        mock_env_manager.return_value = mock_env
        
        error = ValueError("Test error")
        debug_info = self.handler._extract_debug_info(error)
        
        assert debug_info == {}  # No debug info in production
        
    def test_sanitize_file_path_removes_absolute_paths(self):
        """Test file paths are sanitized for security."""
        absolute_path = "/home/user/sensitive/project/netra_backend/app/core/module.py"
        
        sanitized = self.handler._sanitize_file_path(absolute_path)
        
        assert not sanitized.startswith("/home/user")
        assert "sensitive" not in sanitized


@pytest.mark.unit
class TestUnifiedErrorHandlerErrorResponse():
    """Test error response creation and formatting."""
    
    def setup_method(self):
        """Setup fresh handler for each test.""" 
        self.handler = UnifiedErrorHandler()
        
    def test_handle_netra_exception_creates_proper_response(self):
        """Test NetraException creates properly formatted ErrorResponse."""
        from netra_backend.app.core.error_details import ErrorDetails
        
        error_details = ErrorDetails(
            code=ErrorCode.VALIDATION_ERROR,
            message="Validation failed",
            user_message="Please check your input",
            details={"field": "email", "issue": "invalid format"}
        )
        
        error = NetraException(error_details=error_details)
        context = ErrorContext(trace_id="test-123", operation="validation")
        
        response = self.handler._handle_netra_exception(error, context)
        
        assert isinstance(response, ErrorResponse)
        assert response.trace_id == "test-123"
        assert response.message == "Validation failed"
        assert response.user_message == "Please check your input"
        
    def test_handle_validation_error_creates_proper_response(self):
        """Test ValidationError creates properly formatted ErrorResponse."""
        # Create mock validation error with proper structure
        mock_error = Mock(spec=ValidationError)
        mock_error.errors = Mock(return_value=[
            {"loc": ("field", "email"), "msg": "Invalid email format", "type": "value_error"}
        ])
        
        context = ErrorContext(trace_id="test-456", operation="input_validation")
        
        response = self.handler._handle_validation_error(mock_error, context)
        
        assert isinstance(response, ErrorResponse)
        assert response.error_code == ErrorCode.VALIDATION_ERROR.value
        assert response.trace_id == "test-456"
        assert "validation_errors" in response.details
        
    def test_handle_database_error_creates_proper_response(self):
        """Test SQLAlchemy error creates properly formatted ErrorResponse."""
        error = IntegrityError("Constraint violation", None, None)
        context = ErrorContext(trace_id="test-789", operation="database_insert")
        
        response = self.handler._handle_database_error(error, context)
        
        assert isinstance(response, ErrorResponse)
        assert response.error_code == ErrorCode.DATABASE_CONSTRAINT_VIOLATION.value
        assert "Database constraint violation" in response.message
        
    def test_handle_http_exception_creates_proper_response(self):
        """Test HTTPException creates properly formatted ErrorResponse."""
        error = HTTPException(status_code=404, detail="Resource not found")
        context = ErrorContext(trace_id="test-404", operation="api_request")
        
        response = self.handler._handle_http_exception(error, context)
        
        assert isinstance(response, ErrorResponse)
        assert response.error_code == ErrorCode.RECORD_NOT_FOUND.value
        assert response.message == "Resource not found"
        assert response.details["status_code"] == 404


@pytest.mark.unit
class TestUnifiedErrorHandlerMetrics():
    """Test error metrics tracking and statistics."""
    
    def setup_method(self):
        """Setup fresh handler for each test."""
        self.handler = UnifiedErrorHandler()
        
    def test_store_error_updates_metrics(self):
        """Test storing error updates metrics correctly."""
        error_info = {
            'error_id': 'test-123',
            'error': ValueError("Test error"),
            'category': ErrorCategory.VALIDATION,
            'severity': ErrorSeverity.MEDIUM,
            'timestamp': datetime.now(timezone.utc),
            'is_recoverable': False,
            'error_type': 'ValueError'
        }
        
        initial_count = self.handler._error_metrics['total_errors']
        
        self.handler._store_error(error_info)
        
        assert self.handler._error_metrics['total_errors'] == initial_count + 1
        assert len(self.handler.error_history) == 1
        assert self.handler._error_metrics['errors_by_category']['validation'] == 1
        assert self.handler._error_metrics['errors_by_severity']['medium'] == 1
        
    def test_error_history_respects_max_size(self):
        """Test error history is limited by max_history setting."""
        # Create handler with small max history
        handler = UnifiedErrorHandler(max_history=3)
        
        # Add more errors than max history
        for i in range(5):
            error_info = {
                'error_id': f'test-{i}',
                'error': ValueError(f"Test error {i}"),
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.MEDIUM, 
                'timestamp': datetime.now(timezone.utc),
                'is_recoverable': False,
                'error_type': 'ValueError'
            }
            handler._store_error(error_info)
        
        # Should only keep last 3 errors
        assert len(handler.error_history) == 3
        assert handler.error_history[0]['error_id'] == 'test-2'  # Oldest kept
        assert handler.error_history[-1]['error_id'] == 'test-4'  # Newest
        
    def test_get_error_statistics_returns_comprehensive_data(self):
        """Test error statistics include all relevant metrics."""
        # Add some test errors
        for category in [ErrorCategory.DATABASE, ErrorCategory.VALIDATION]:
            error_info = {
                'error_id': f'test-{category.value}',
                'error': Exception("Test"),
                'category': category,
                'severity': ErrorSeverity.MEDIUM,
                'timestamp': datetime.now(timezone.utc),
                'is_recoverable': True,
                'error_type': 'Exception'
            }
            self.handler._store_error(error_info)
        
        stats = self.handler.get_error_statistics()
        
        assert 'total_errors' in stats
        assert 'recovery_attempts' in stats
        assert 'recovery_successes' in stats
        assert 'success_rate' in stats
        assert 'errors_by_category' in stats
        assert 'errors_by_severity' in stats
        assert stats['total_errors'] >= 2


@pytest.mark.unit
class TestUnifiedErrorHandlerIntegration():
    """Test integration with domain-specific handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_error_end_to_end(self):
        """Test complete error handling flow."""
        handler = UnifiedErrorHandler()
        error = ValueError("Test validation error")
        context = ErrorContext(trace_id="test-e2e", operation="test_operation")
        
        result = await handler.handle_error(error, context)
        
        assert isinstance(result, ErrorResponse)
        assert result.trace_id == "test-e2e"
        assert len(handler.error_history) == 1
        assert handler._error_metrics['total_errors'] == 1
        
    def test_api_error_handler_initialization(self):
        """Test APIErrorHandler initializes correctly."""
        unified_handler = UnifiedErrorHandler()
        api_handler = APIErrorHandler(unified_handler)
        
        assert api_handler._handler == unified_handler
        
    def test_agent_error_handler_initialization(self):
        """Test AgentErrorHandler initializes correctly."""
        unified_handler = UnifiedErrorHandler()
        agent_handler = AgentErrorHandler(unified_handler)
        
        assert agent_handler._handler == unified_handler
        assert hasattr(agent_handler, 'recovery_coordinator')
        
    def test_websocket_error_handler_initialization(self):
        """Test WebSocketErrorHandler initializes correctly."""
        unified_handler = UnifiedErrorHandler()
        ws_handler = WebSocketErrorHandler(unified_handler)
        
        assert ws_handler._handler == unified_handler
        
    @pytest.mark.asyncio
    async def test_websocket_error_handler_formats_response_correctly(self):
        """Test WebSocketErrorHandler returns properly formatted response."""
        unified_handler = UnifiedErrorHandler()
        ws_handler = WebSocketErrorHandler(unified_handler)
        
        error = ValueError("WebSocket error")
        
        result = await ws_handler.handle_websocket_error(
            error, 
            connection_id="conn-123",
            message_type="chat_message"
        )
        
        assert result["type"] == "error"
        assert "error_code" in result
        assert "message" in result
        assert "trace_id" in result
        assert "recoverable" in result
        

@pytest.mark.unit
class TestUnifiedErrorHandlerGlobalFunctions():
    """Test global convenience functions."""
    
    @pytest.mark.asyncio
    async def test_global_handle_error_function(self):
        """Test global handle_error function works correctly."""
        error = ValueError("Global test error")
        
        result = await handle_error(error)
        
        assert isinstance(result, ErrorResponse)
        assert result.error_code == ErrorCode.INTERNAL_ERROR.value
        
    def test_global_get_http_status_code_function(self):
        """Test global get_http_status_code function works correctly."""
        status = get_http_status_code(ErrorCode.VALIDATION_ERROR)
        assert status == 422
        
        status = get_http_status_code("VALIDATION_ERROR")
        assert status == 422
        
    def test_global_get_error_statistics_function(self):
        """Test global get_error_statistics function works correctly."""
        stats = get_error_statistics()
        
        assert 'total_errors' in stats
        assert 'recovery_attempts' in stats
        assert isinstance(stats['total_errors'], int)


@pytest.mark.unit
class TestRetryRecoveryStrategy():
    """Test retry recovery strategy implementation."""
    
    @pytest.mark.asyncio
    async def test_retry_recovery_strategy_succeeds(self):
        """Test retry recovery strategy executes successfully."""
        strategy = RetryRecoveryStrategy(max_retries=2, base_delay=0.01)  # Fast for testing
        
        error = asyncio.TimeoutError("Temporary failure")
        context = ErrorContext(trace_id="test-retry", operation="test")
        
        call_count = 0
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Still failing")
            return "success"
        
        result = await strategy.attempt_recovery(error, context, mock_operation)
        
        # Should succeed on second attempt
        assert result == "success"
        assert call_count == 2
        
    @pytest.mark.asyncio 
    async def test_retry_recovery_strategy_respects_max_retries(self):
        """Test retry recovery strategy respects max retry limit."""
        strategy = RetryRecoveryStrategy(max_retries=1, base_delay=0.01)
        
        error = asyncio.TimeoutError("Persistent failure") 
        context = ErrorContext(trace_id="test-retry", operation="test", retry_count=2)  # Already exceeded
        
        async def mock_operation():
            return "should_not_be_called"
        
        result = await strategy.attempt_recovery(error, context, mock_operation)
        
        # Should not attempt recovery due to exceeded retry count
        assert result is None


@pytest.mark.unit
class TestFallbackRecoveryStrategy():
    """Test fallback recovery strategy implementation."""
    
    @pytest.mark.asyncio
    async def test_fallback_recovery_strategy_executes(self):
        """Test fallback recovery strategy executes fallback operation."""
        async def fallback_op():
            return "fallback_result"
        
        strategy = FallbackRecoveryStrategy(fallback_op)
        
        error = ValueError("Primary operation failed")
        context = ErrorContext(trace_id="test-fallback", operation="test")
        
        result = await strategy.attempt_recovery(error, context)
        
        assert result == "fallback_result"
        
    @pytest.mark.asyncio
    async def test_fallback_recovery_strategy_handles_fallback_failure(self):
        """Test fallback recovery strategy handles fallback operation failure."""
        async def failing_fallback_op():
            raise Exception("Fallback also failed")
        
        strategy = FallbackRecoveryStrategy(failing_fallback_op)
        
        error = ValueError("Primary operation failed")
        context = ErrorContext(trace_id="test-fallback", operation="test")
        
        result = await strategy.attempt_recovery(error, context)
        
        assert result is None  # Should return None when fallback fails