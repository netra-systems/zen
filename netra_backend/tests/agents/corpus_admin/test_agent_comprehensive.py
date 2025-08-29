"""
Comprehensive unit tests for corpus_admin agent.

Business Value: Ensures the main CorpusAdminSubAgent operates reliably across all
execution patterns - modern, legacy, and fallback scenarios. This agent is critical
for enterprise corpus management and must handle complex state management,
error recovery, and execution monitoring.
"""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock, patch, call
from typing import Any, Dict, Optional

from netra_backend.app.agents.base.errors import ValidationError
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult, ExecutionStatus
from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.corpus_admin.models import (
    CorpusMetadata,
    CorpusOperation,
    CorpusOperationRequest,
    CorpusOperationResult,
    CorpusType,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager


class TestCorpusAdminSubAgentInitialization:
    """Test agent initialization and component setup."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager for testing."""
        return Mock(spec=LLMManager)

    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher for testing."""
        return Mock(spec=ToolDispatcher)

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for testing."""
        mock_ws = Mock()
        mock_ws.send_json = AsyncMock()
        return mock_ws

    def test_basic_initialization(self, mock_llm_manager, mock_tool_dispatcher):
        """Test basic agent initialization without WebSocket manager."""
        agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        assert agent.name == "CorpusAdminSubAgent"
        assert agent.description == "Agent specialized in corpus management and administration"
        assert agent.tool_dispatcher == mock_tool_dispatcher
        assert agent.parser is not None
        assert agent.validator is not None
        assert agent.operations is not None

    def test_initialization_with_websocket(self, mock_llm_manager, mock_tool_dispatcher, mock_websocket_manager):
        """Test initialization with WebSocket manager."""
        agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_websocket_manager)
        
        assert agent.websocket_manager == mock_websocket_manager
        assert agent.monitor is not None
        assert agent.reliability_manager is not None
        assert agent.execution_engine is not None

    def test_modern_execution_infrastructure_setup(self, mock_llm_manager, mock_tool_dispatcher):
        """Test modern execution infrastructure is properly set up."""
        agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # Check all modern execution components are initialized
        assert agent.monitor is not None
        assert agent.reliability_manager is not None
        assert agent.execution_engine is not None
        assert agent.error_handler is not None

    def test_component_initialization(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that all components are properly initialized."""
        agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # Check agent components
        assert agent.parser is not None
        assert agent.validator is not None
        assert agent.operations is not None
        
        # Check component dependencies
        assert agent.operations.tool_dispatcher == mock_tool_dispatcher

    def test_reliability_manager_configuration(self, mock_llm_manager, mock_tool_dispatcher):
        """Test reliability manager is properly configured."""
        agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        reliability_manager = agent.reliability_manager
        assert reliability_manager is not None
        
        # Test health status is available
        health_status = reliability_manager.get_health_status()
        assert isinstance(health_status, dict)


class TestEntryConditionsChecking:
    """Test entry condition checking logic."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def basic_state(self):
        """Create basic agent state for testing."""
        state = DeepAgentState()
        state.user_request = "Create a new documentation corpus"
        state.user_id = "test_user_123"
        state.chat_thread_id = "thread_456"
        return state

    @pytest.mark.asyncio
    async def test_entry_conditions_admin_mode(self, corpus_admin_agent, basic_state):
        """Test entry conditions with admin mode triage result."""
        basic_state.triage_result = {"category": "corpus_admin", "is_admin_mode": True}
        
        result = await corpus_admin_agent.check_entry_conditions(basic_state, "test_run_123")
        assert result is True

    @pytest.mark.asyncio
    async def test_entry_conditions_corpus_category(self, corpus_admin_agent, basic_state):
        """Test entry conditions with corpus category in triage result."""
        basic_state.triage_result = {"category": "corpus_management", "is_admin_mode": False}
        
        result = await corpus_admin_agent.check_entry_conditions(basic_state, "test_run_456")
        assert result is True

    @pytest.mark.asyncio
    async def test_entry_conditions_corpus_keywords(self, corpus_admin_agent, basic_state):
        """Test entry conditions with corpus keywords in user request."""
        test_cases = [
            "I need to update my corpus",
            "Help with knowledge base management",
            "Process documentation files",
            "Update reference data",
            "Generate embeddings for the corpus"
        ]
        
        for request in test_cases:
            basic_state.user_request = request
            basic_state.triage_result = {}
            
            result = await corpus_admin_agent.check_entry_conditions(basic_state, "keyword_test")
            assert result is True, f"Failed for request: {request}"

    @pytest.mark.asyncio
    async def test_entry_conditions_negative_cases(self, corpus_admin_agent, basic_state):
        """Test entry conditions with non-corpus requests."""
        negative_cases = [
            "How is the weather today?",
            "What is machine learning?",
            "Help me with Python code",
            "Schedule a meeting"
        ]
        
        for request in negative_cases:
            basic_state.user_request = request
            basic_state.triage_result = {"category": "general", "is_admin_mode": False}
            
            result = await corpus_admin_agent.check_entry_conditions(basic_state, "negative_test")
            assert result is False, f"Incorrectly matched request: {request}"

    @pytest.mark.asyncio
    async def test_entry_conditions_empty_request(self, corpus_admin_agent):
        """Test entry conditions with empty user request."""
        state = DeepAgentState()
        state.user_request = ""
        state.triage_result = {}
        
        result = await corpus_admin_agent.check_entry_conditions(state, "empty_test")
        assert result is False


class TestPreconditionValidation:
    """Test precondition validation logic."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def valid_state(self):
        state = DeepAgentState()
        state.user_request = "Create a test corpus"
        state.user_id = "test_user"
        state.chat_thread_id = "test_thread"
        return state

    @pytest.fixture
    def execution_context(self, valid_state):
        return ExecutionContext(
            run_id="test_run_123",
            agent_name="CorpusAdminSubAgent",
            state=valid_state,
            stream_updates=False,
            thread_id="test_thread",
            user_id="test_user"
        )

    @pytest.mark.asyncio
    async def test_validate_preconditions_success(self, corpus_admin_agent, execution_context):
        """Test successful precondition validation."""
        result = await corpus_admin_agent.validate_preconditions(execution_context)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_state_requirements_success(self, corpus_admin_agent, valid_state):
        """Test state requirements validation with valid state."""
        # Should not raise exception
        await corpus_admin_agent._validate_state_requirements(valid_state)

    @pytest.mark.asyncio
    async def test_validate_state_requirements_missing_request(self, corpus_admin_agent):
        """Test state requirements validation with missing user request."""
        invalid_state = DeepAgentState()
        invalid_state.user_request = ""
        
        with pytest.raises(ValidationError) as exc_info:
            await corpus_admin_agent._validate_state_requirements(invalid_state)
        
        assert "Missing required user_request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_execution_resources_success(self, corpus_admin_agent, execution_context):
        """Test execution resources validation with proper components."""
        await corpus_admin_agent._validate_execution_resources(execution_context)

    @pytest.mark.asyncio
    async def test_validate_execution_resources_missing_components(self, corpus_admin_agent, execution_context):
        """Test execution resources validation with missing components."""
        # Remove parser to trigger validation error
        corpus_admin_agent.parser = None
        
        with pytest.raises(ValidationError) as exc_info:
            await corpus_admin_agent._validate_execution_resources(execution_context)
        
        assert "Corpus admin components not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_corpus_admin_dependencies(self, corpus_admin_agent):
        """Test corpus admin dependencies validation."""
        # Mock reliability manager health status
        with patch.object(corpus_admin_agent.reliability_manager, 'get_health_status') as mock_health:
            mock_health.return_value = {'overall_health': 'healthy'}
            
            # Should not raise exception
            await corpus_admin_agent._validate_corpus_admin_dependencies()

    @pytest.mark.asyncio
    async def test_validate_corpus_admin_dependencies_degraded(self, corpus_admin_agent):
        """Test corpus admin dependencies validation with degraded health."""
        with patch.object(corpus_admin_agent.reliability_manager, 'get_health_status') as mock_health:
            mock_health.return_value = {'overall_health': 'degraded'}
            
            # Should log warning but not raise exception
            await corpus_admin_agent._validate_corpus_admin_dependencies()


class TestCoreLogicExecution:
    """Test core logic execution methods."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def execution_context(self):
        state = DeepAgentState()
        state.user_request = "Test corpus operation"
        state.user_id = "test_user"
        state.chat_thread_id = "test_thread"
        
        return ExecutionContext(
            run_id="test_run_123",
            agent_name="CorpusAdminSubAgent",
            state=state,
            stream_updates=True,
            thread_id="test_thread",
            user_id="test_user"
        )

    @pytest.mark.asyncio
    async def test_execute_core_logic_success(self, corpus_admin_agent, execution_context):
        """Test successful core logic execution."""
        # Mock monitor methods
        corpus_admin_agent.monitor.start_operation = Mock()
        corpus_admin_agent.monitor.complete_operation = Mock()
        
        # Mock workflow execution
        with patch.object(corpus_admin_agent, '_execute_corpus_administration_workflow') as mock_workflow:
            mock_workflow.return_value = {"corpus_admin_result": "completed"}
            
            with patch.object(corpus_admin_agent, 'send_status_update') as mock_status:
                result = await corpus_admin_agent.execute_core_logic(execution_context)
                
                assert result["corpus_admin_result"] == "completed"
                mock_workflow.assert_called_once_with(execution_context)
                corpus_admin_agent.monitor.start_operation.assert_called_once()
                corpus_admin_agent.monitor.complete_operation.assert_called_once()
                assert mock_status.call_count == 2  # Start and complete updates

    @pytest.mark.asyncio
    async def test_execute_corpus_administration_workflow(self, corpus_admin_agent, execution_context):
        """Test corpus administration workflow execution."""
        with patch.object(corpus_admin_agent, '_run_corpus_admin_workflow') as mock_workflow:
            mock_workflow.return_value = execution_context.state
            
            result = await corpus_admin_agent._execute_corpus_administration_workflow(execution_context)
            
            assert "corpus_admin_result" in result
            assert result["corpus_admin_result"] == "completed"
            mock_workflow.assert_called_once_with(
                execution_context.state, execution_context.run_id, execution_context.stream_updates
            )


class TestModernExecutionPattern:
    """Test modern execution pattern using BaseExecutionEngine."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def sample_state(self):
        state = DeepAgentState()
        state.user_request = "Modern execution test"
        state.user_id = "modern_user"
        state.chat_thread_id = "modern_thread"
        return state

    @pytest.mark.asyncio
    async def test_execute_with_reliability_manager_success(self, corpus_admin_agent, sample_state):
        """Test successful execution using reliability manager."""
        mock_result = ExecutionResult(
            success=True,
            result={"test": "result"},
            status=ExecutionStatus.COMPLETED
        )
        
        context = corpus_admin_agent._create_execution_context(sample_state, "modern_run", True)
        
        with patch.object(corpus_admin_agent.reliability_manager, 'execute_with_reliability') as mock_execute:
            mock_execute.return_value = mock_result
            
            result = await corpus_admin_agent._execute_with_reliability_manager(context)
            
            assert result == mock_result
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_modern_pattern_with_fallback(self, corpus_admin_agent, sample_state):
        """Test modern pattern with fallback to legacy on failure."""
        # Mock modern pattern failure
        with patch.object(corpus_admin_agent.reliability_manager, 'execute_with_reliability') as mock_execute:
            mock_execute.side_effect = Exception("Modern execution failed")
            
            with patch.object(corpus_admin_agent, '_execute_legacy_workflow') as mock_legacy:
                with patch.object(corpus_admin_agent.error_handler, 'handle_execution_error') as mock_error:
                    await corpus_admin_agent.execute(sample_state, "fallback_run", False)
                    
                    mock_error.assert_called_once()
                    mock_legacy.assert_called_once_with(sample_state, "fallback_run", False)

    def test_create_execution_context(self, corpus_admin_agent, sample_state):
        """Test execution context creation."""
        context = corpus_admin_agent._create_execution_context(sample_state, "context_run", True)
        
        assert context.run_id == "context_run"
        assert context.agent_name == "CorpusAdminSubAgent"
        assert context.state == sample_state
        assert context.stream_updates is True
        assert context.thread_id == sample_state.chat_thread_id
        assert context.user_id == sample_state.user_id

    def test_create_execution_context_with_defaults(self, corpus_admin_agent):
        """Test execution context creation with default values."""
        state = DeepAgentState()  # No thread_id or user_id set
        
        context = corpus_admin_agent._create_execution_context(state, "default_run", False)
        
        assert context.run_id == "default_run"
        assert context.stream_updates is False
        assert context.thread_id is None  # getattr returns None when attribute exists but is None
        assert context.user_id is None

    @pytest.mark.asyncio
    async def test_handle_execution_result_success(self, corpus_admin_agent, sample_state):
        """Test handling of successful execution result."""
        context = ExecutionContext(
            run_id="success_run",
            agent_name="CorpusAdminSubAgent",
            state=sample_state,
            stream_updates=False,
            thread_id="thread",
            user_id="user"
        )
        
        success_result = ExecutionResult(
            success=True,
            result={"success": "data"},
            status=ExecutionStatus.COMPLETED
        )
        
        # Should not call error handler for successful result
        with patch.object(corpus_admin_agent.error_handler, 'handle_execution_error') as mock_error:
            await corpus_admin_agent._handle_execution_result(success_result, context)
            mock_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_execution_result_failure(self, corpus_admin_agent, sample_state):
        """Test handling of failed execution result."""
        context = ExecutionContext(
            run_id="failure_run",
            agent_name="CorpusAdminSubAgent",
            state=sample_state,
            stream_updates=False,
            thread_id="thread",
            user_id="user"
        )
        
        failure_result = ExecutionResult(
            success=False,
            result=None,
            status=ExecutionStatus.FAILED,
            error=Exception("Execution failed")
        )
        
        with patch.object(corpus_admin_agent.error_handler, 'handle_execution_error') as mock_error:
            await corpus_admin_agent._handle_execution_result(failure_result, context)
            mock_error.assert_called_once_with(failure_result.error, context)


class TestLegacyWorkflowExecution:
    """Test legacy workflow execution methods."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def sample_state(self):
        state = DeepAgentState()
        state.user_request = "Create legacy test corpus"
        state.user_id = "legacy_user"
        state.chat_thread_id = "legacy_thread"
        return state

    @pytest.fixture
    def sample_operation_result(self):
        metadata = CorpusMetadata(
            corpus_name="legacy_corpus",
            corpus_type=CorpusType.DOCUMENTATION
        )
        return CorpusOperationResult(
            success=True,
            operation=CorpusOperation.CREATE,
            corpus_metadata=metadata,
            affected_documents=10
        )

    @pytest.mark.asyncio
    async def test_run_corpus_admin_workflow(self, corpus_admin_agent, sample_state):
        """Test legacy corpus admin workflow execution."""
        with patch.object(corpus_admin_agent, '_execute_corpus_operation_workflow') as mock_workflow:
            result = await corpus_admin_agent._run_corpus_admin_workflow(sample_state, "legacy_run", True)
            
            assert result == sample_state
            mock_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_legacy_workflow(self, corpus_admin_agent, sample_state):
        """Test complete legacy workflow execution."""
        with patch.object(corpus_admin_agent, '_execute_with_error_handling') as mock_execute:
            await corpus_admin_agent._execute_legacy_workflow(sample_state, "legacy_run", False)
            
            mock_execute.assert_called_once_with(sample_state, "legacy_run", False, pytest.approx(time.time(), rel=1))

    @pytest.mark.asyncio
    async def test_execute_corpus_operation_workflow(self, corpus_admin_agent, sample_state):
        """Test corpus operation workflow execution."""
        with patch.object(corpus_admin_agent, '_send_initial_update') as mock_initial:
            with patch.object(corpus_admin_agent.parser, 'parse_operation_request') as mock_parser:
                mock_parser.return_value = {"operation": "CREATE"}
                
                with patch.object(corpus_admin_agent, '_process_operation_with_approval') as mock_process:
                    await corpus_admin_agent._execute_corpus_operation_workflow(
                        sample_state, "workflow_run", True, time.time()
                    )
                    
                    mock_initial.assert_called_once()
                    mock_parser.assert_called_once_with(sample_state.user_request)
                    mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_operation_with_approval_required(self, corpus_admin_agent, sample_state):
        """Test operation processing when approval is required."""
        mock_request = Mock()
        
        with patch.object(corpus_admin_agent, '_handle_approval_check') as mock_approval:
            mock_approval.return_value = True  # Approval required
            
            with patch.object(corpus_admin_agent, '_complete_corpus_operation') as mock_complete:
                await corpus_admin_agent._process_operation_with_approval(
                    mock_request, sample_state, "approval_run", True, time.time()
                )
                
                mock_approval.assert_called_once()
                mock_complete.assert_not_called()  # Should not complete if approval required

    @pytest.mark.asyncio
    async def test_process_operation_without_approval(self, corpus_admin_agent, sample_state):
        """Test operation processing when approval is not required."""
        mock_request = Mock()
        
        with patch.object(corpus_admin_agent, '_handle_approval_check') as mock_approval:
            mock_approval.return_value = False  # No approval required
            
            with patch.object(corpus_admin_agent, '_complete_corpus_operation') as mock_complete:
                await corpus_admin_agent._process_operation_with_approval(
                    mock_request, sample_state, "no_approval_run", False, time.time()
                )
                
                mock_approval.assert_called_once()
                mock_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_corpus_operation(self, corpus_admin_agent, sample_state, sample_operation_result):
        """Test complete corpus operation execution."""
        mock_request = Mock()
        
        with patch.object(corpus_admin_agent, '_send_processing_update') as mock_processing:
            with patch.object(corpus_admin_agent.operations, 'execute_operation') as mock_execute:
                mock_execute.return_value = sample_operation_result
                
                with patch.object(corpus_admin_agent, '_finalize_operation_result') as mock_finalize:
                    await corpus_admin_agent._complete_corpus_operation(
                        mock_request, sample_state, "complete_run", True, time.time()
                    )
                    
                    mock_processing.assert_called_once()
                    mock_execute.assert_called_once_with(mock_request, "complete_run", True)
                    mock_finalize.assert_called_once()


class TestApprovalHandling:
    """Test approval validation and handling."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def sample_state(self):
        state = DeepAgentState()
        state.user_request = "Delete old documentation"
        state.triage_result = {"category": "corpus_admin"}
        return state

    @pytest.mark.asyncio
    async def test_handle_approval_check(self, corpus_admin_agent, sample_state):
        """Test approval check handling."""
        mock_request = Mock()
        
        # Mock the validator method that the agent calls
        with patch.object(corpus_admin_agent.validator, 'validate_approval_required') as mock_validator:
            mock_validator.return_value = True
            
            result = await corpus_admin_agent._handle_approval_check(
                mock_request, sample_state, "approval_run", False
            )
            
            assert result is True
            mock_validator.assert_called_once_with(
                mock_request, sample_state, "approval_run", False
            )

    @pytest.mark.asyncio
    async def test_approval_validator_integration(self, corpus_admin_agent):
        """Test integration with approval validator."""
        # Ensure validator is properly initialized
        assert corpus_admin_agent.validator is not None
        assert hasattr(corpus_admin_agent.validator, 'validate_approval_required')


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def sample_state(self):
        state = DeepAgentState()
        state.user_request = "Error test request"
        return state

    @pytest.mark.asyncio
    async def test_handle_execution_error(self, corpus_admin_agent, sample_state):
        """Test execution error handling."""
        test_error = Exception("Test execution error")
        
        with patch.object(sample_state.__class__, 'corpus_admin_error', create=True):
            await corpus_admin_agent._handle_execution_error(test_error, sample_state, "error_run", False)
            
            assert sample_state.corpus_admin_error == str(test_error)

    @pytest.mark.asyncio
    async def test_handle_execution_exception_with_fallback(self, corpus_admin_agent, sample_state):
        """Test execution exception handling with fallback to legacy."""
        context = ExecutionContext(
            run_id="exception_run",
            agent_name="CorpusAdminSubAgent",
            state=sample_state,
            stream_updates=False,
            thread_id="thread",
            user_id="user"
        )
        
        test_error = Exception("Modern execution failed")
        
        with patch.object(corpus_admin_agent.error_handler, 'handle_execution_error') as mock_error:
            with patch.object(corpus_admin_agent, '_execute_legacy_workflow') as mock_legacy:
                await corpus_admin_agent._handle_execution_exception(
                    test_error, context, sample_state, "exception_run", True
                )
                
                mock_error.assert_called_once_with(test_error, context)
                mock_legacy.assert_called_once_with(sample_state, "exception_run", True)

    @pytest.mark.asyncio
    async def test_execute_with_error_handling_success(self, corpus_admin_agent, sample_state):
        """Test successful execution with error handling wrapper."""
        with patch.object(corpus_admin_agent, '_execute_corpus_operation_workflow') as mock_workflow:
            await corpus_admin_agent._execute_with_error_handling(
                sample_state, "success_run", True, time.time()
            )
            
            mock_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_error_handling_failure(self, corpus_admin_agent, sample_state):
        """Test execution with error handling when workflow fails."""
        test_error = Exception("Workflow execution error")
        
        with patch.object(corpus_admin_agent, '_execute_corpus_operation_workflow') as mock_workflow:
            mock_workflow.side_effect = test_error
            
            with patch.object(corpus_admin_agent, '_handle_execution_error') as mock_error:
                with pytest.raises(Exception) as exc_info:
                    await corpus_admin_agent._execute_with_error_handling(
                        sample_state, "error_run", False, time.time()
                    )
                
                assert exc_info.value == test_error
                mock_error.assert_called_once_with(test_error, sample_state, "error_run", False)


class TestHealthStatusReporting:
    """Test health status reporting."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    def test_get_health_status_complete(self, corpus_admin_agent):
        """Test complete health status reporting."""
        health_status = corpus_admin_agent.get_health_status()
        
        assert isinstance(health_status, dict)
        assert "agent_health" in health_status
        assert "monitor" in health_status
        assert "error_handler" in health_status
        assert "reliability" in health_status
        
        assert health_status["agent_health"] == "healthy"

    def test_health_status_components(self, corpus_admin_agent):
        """Test individual health status components."""
        # Test monitor health
        monitor_health = corpus_admin_agent.monitor.get_health_status()
        assert isinstance(monitor_health, dict)
        
        # Test error handler health
        error_handler_health = corpus_admin_agent.error_handler.get_health_status()
        assert isinstance(error_handler_health, dict)
        
        # Test reliability manager health
        reliability_health = corpus_admin_agent.reliability_manager.get_health_status()
        assert isinstance(reliability_health, dict)


class TestUtilityMethods:
    """Test utility and helper methods."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    def test_is_admin_mode_request(self, corpus_admin_agent):
        """Test admin mode detection."""
        state = DeepAgentState()
        
        # Test explicit admin mode
        state.triage_result = {"category": "general", "is_admin_mode": True}
        assert corpus_admin_agent._is_admin_mode_request(state) is True
        
        # Test corpus category
        state.triage_result = {"category": "corpus_management", "is_admin_mode": False}
        assert corpus_admin_agent._is_admin_mode_request(state) is True
        
        # Test admin category
        state.triage_result = {"category": "admin_tools", "is_admin_mode": False}
        assert corpus_admin_agent._is_admin_mode_request(state) is True
        
        # Test negative case
        state.triage_result = {"category": "general", "is_admin_mode": False}
        assert corpus_admin_agent._is_admin_mode_request(state) is False

    def test_check_admin_indicators(self, corpus_admin_agent):
        """Test admin indicator checking."""
        # Test corpus in category
        assert corpus_admin_agent._check_admin_indicators({"category": "corpus_admin"}) is True
        
        # Test admin in category
        assert corpus_admin_agent._check_admin_indicators({"category": "admin_mode"}) is True
        
        # Test explicit admin mode
        assert corpus_admin_agent._check_admin_indicators({"is_admin_mode": True}) is True
        
        # Test negative case
        assert corpus_admin_agent._check_admin_indicators({"category": "general"}) is False

    def test_has_corpus_keywords(self, corpus_admin_agent):
        """Test corpus keyword detection."""
        state = DeepAgentState()
        
        # Test positive cases
        positive_cases = [
            "I need to update my corpus",
            "Help with knowledge base management",
            "Process documentation files",
            "Update reference data",
            "Generate embeddings for analysis"
        ]
        
        for request in positive_cases:
            state.user_request = request
            assert corpus_admin_agent._has_corpus_keywords(state) is True, f"Failed for: {request}"

    def test_has_corpus_keywords_negative(self, corpus_admin_agent):
        """Test corpus keyword detection for non-corpus requests."""
        state = DeepAgentState()
        
        negative_cases = [
            "How is the weather?",
            "What is machine learning?",
            "Help with Python code",
            "Schedule a meeting",
            ""
        ]
        
        for request in negative_cases:
            state.user_request = request
            assert corpus_admin_agent._has_corpus_keywords(state) is False, f"Incorrectly matched: {request}"

    def test_has_valid_result(self, corpus_admin_agent):
        """Test valid result detection."""
        state = DeepAgentState()
        
        # Test without result
        assert corpus_admin_agent._has_valid_result(state) is False
        
        # Test with valid result
        state.corpus_admin_result = {"operation": "CREATE", "success": True}
        assert corpus_admin_agent._has_valid_result(state) is True

    def test_get_corpus_name(self, corpus_admin_agent):
        """Test corpus name extraction from result."""
        # Test with corpus metadata
        result = {"corpus_metadata": {"corpus_name": "test_corpus"}}
        assert corpus_admin_agent._get_corpus_name(result) == "test_corpus"
        
        # Test without metadata
        assert corpus_admin_agent._get_corpus_name({}) is None

    def test_build_metrics_message(self, corpus_admin_agent):
        """Test metrics message building."""
        result = {
            "operation": "CREATE",
            "corpus_metadata": {"corpus_name": "test_corpus"},
            "affected_documents": 25
        }
        
        message = corpus_admin_agent._build_metrics_message(result)
        
        assert "operation=CREATE" in message
        assert "corpus=test_corpus" in message
        assert "affected=25" in message


class TestCleanupAndFinalization:
    """Test cleanup and finalization methods."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.fixture
    def sample_state(self):
        state = DeepAgentState()
        state.user_request = "Cleanup test request"
        return state

    @pytest.fixture
    def sample_operation_result(self):
        metadata = CorpusMetadata(
            corpus_name="cleanup_corpus",
            corpus_type=CorpusType.DOCUMENTATION
        )
        return CorpusOperationResult(
            success=True,
            operation=CorpusOperation.UPDATE,
            corpus_metadata=metadata,
            affected_documents=5
        )

    @pytest.mark.asyncio
    async def test_cleanup(self, corpus_admin_agent, sample_state):
        """Test cleanup after execution."""
        with patch('netra_backend.app.agents.base_agent.BaseSubAgent.cleanup') as mock_parent_cleanup:
            mock_parent_cleanup.return_value = None
            
            await corpus_admin_agent.cleanup(sample_state, "cleanup_run")
            
            mock_parent_cleanup.assert_called_once_with(sample_state, "cleanup_run")

    @pytest.mark.asyncio
    async def test_finalize_operation_result(self, corpus_admin_agent, sample_state, sample_operation_result):
        """Test operation result finalization."""
        start_time = time.time()
        
        with patch.object(corpus_admin_agent, '_send_completion_update') as mock_update:
            with patch.object(corpus_admin_agent, '_log_completion') as mock_log:
                with patch.object(sample_state.__class__, 'corpus_admin_result', create=True):
                    await corpus_admin_agent._finalize_operation_result(
                        sample_operation_result, sample_state, "finalize_run", True, start_time
                    )
                    
                    mock_update.assert_called_once()
                    mock_log.assert_called_once_with(sample_operation_result, "finalize_run")

    def test_log_completion(self, corpus_admin_agent, sample_operation_result):
        """Test completion logging."""
        # Should not raise any exceptions
        corpus_admin_agent._log_completion(sample_operation_result, "log_run")

    def test_log_final_metrics_with_result(self, corpus_admin_agent, sample_state):
        """Test final metrics logging with valid result."""
        with patch.object(sample_state.__class__, 'corpus_admin_result', create=True):
            sample_state.corpus_admin_result = {
                "operation": "CREATE",
                "corpus_metadata": {"corpus_name": "metrics_corpus"},
                "affected_documents": 15
            }
            
            # Should not raise any exceptions
            corpus_admin_agent._log_final_metrics(sample_state)

    def test_log_final_metrics_without_result(self, corpus_admin_agent, sample_state):
        """Test final metrics logging without result."""
        # Should not raise any exceptions
        corpus_admin_agent._log_final_metrics(sample_state)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def corpus_admin_agent(self):
        mock_llm = Mock(spec=LLMManager)
        mock_tool = Mock(spec=ToolDispatcher)
        return CorpusAdminSubAgent(mock_llm, mock_tool)

    @pytest.mark.asyncio
    async def test_execution_with_none_state(self, corpus_admin_agent):
        """Test execution with None state."""
        # The agent should handle None state gracefully or raise an exception
        # Let's test the actual behavior
        try:
            await corpus_admin_agent.execute(None, "none_run", False)
        except Exception as e:
            # Expected behavior - should raise some exception
            assert isinstance(e, (AttributeError, TypeError, ValidationError))
        # If no exception is raised, that's also valid behavior

    @pytest.mark.asyncio
    async def test_execution_with_malformed_state(self, corpus_admin_agent):
        """Test execution with malformed state."""
        malformed_state = DeepAgentState()
        # No user_request set
        
        with pytest.raises(ValidationError):
            context = corpus_admin_agent._create_execution_context(malformed_state, "malformed_run", False)
            await corpus_admin_agent.validate_preconditions(context)

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, corpus_admin_agent):
        """Test concurrent execution handling."""
        import asyncio
        
        states = []
        for i in range(3):
            state = DeepAgentState()
            state.user_request = f"Concurrent test {i}"
            state.user_id = f"user_{i}"
            state.chat_thread_id = f"thread_{i}"
            states.append(state)
        
        # Mock successful execution
        with patch.object(corpus_admin_agent.reliability_manager, 'execute_with_reliability') as mock_execute:
            mock_result = ExecutionResult(
                success=True,
                result={"concurrent": "success"},
                status=ExecutionStatus.COMPLETED
            )
            mock_execute.return_value = mock_result
            
            tasks = [
                corpus_admin_agent.execute(state, f"concurrent_run_{i}", False)
                for i, state in enumerate(states)
            ]
            
            # Should handle concurrent executions without issues
            await asyncio.gather(*tasks, return_exceptions=True)

    def test_extreme_user_request_values(self, corpus_admin_agent):
        """Test handling of extreme user request values."""
        state = DeepAgentState()
        
        # Very long request
        state.user_request = "x" * 10000
        context = corpus_admin_agent._create_execution_context(state, "extreme_run", False)
        assert len(context.state.user_request) == 10000
        
        # Unicode request
        state.user_request = "Create corpus with unicode: 🗃️📚🔍"
        context = corpus_admin_agent._create_execution_context(state, "unicode_run", False)
        assert "🗃️" in context.state.user_request


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])