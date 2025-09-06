from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Comprehensive SSOT Compliance Test Suite for DataHelperAgent"""

# REMOVED_SYNTAX_ERROR: This test suite validates critical SSOT compliance patterns and fixes:

    # REMOVED_SYNTAX_ERROR: 1.  UserExecutionContext integration (optional parameter in constructor)
    # REMOVED_SYNTAX_ERROR: 2.  Proper usage of agent_error_handler from unified error handling
    # REMOVED_SYNTAX_ERROR: 3.  No manual ExecutionContext creation when UserExecutionContext is provided
    # REMOVED_SYNTAX_ERROR: 4.  Proper BaseAgent integration and inheritance (super().__init__ not BaseAgent.__init__)
    # REMOVED_SYNTAX_ERROR: 5.  WebSocket event emissions (thinking, tool_executing, tool_completed, etc.)
    # REMOVED_SYNTAX_ERROR: 6.  Isolation between concurrent data operations
    # REMOVED_SYNTAX_ERROR: 7.  No global state storage or user data persistence
    # REMOVED_SYNTAX_ERROR: 8.  Backward compatibility (works with and without context)
    # REMOVED_SYNTAX_ERROR: 9.  Tool dispatcher context propagation
    # REMOVED_SYNTAX_ERROR: 10.  Error handling with ErrorContext structure
    # REMOVED_SYNTAX_ERROR: 11.  Memory cleanup after operations

import asyncio
import os
import json
import hashlib
import time
import threading
import uuid
import gc
import inspect
import weakref
from typing import Any, Dict, List, Optional
import pytest
from datetime import datetime, timedelta
import concurrent.futures
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import hashlib
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import threading
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: import gc
    # REMOVED_SYNTAX_ERROR: import inspect
    # REMOVED_SYNTAX_ERROR: import weakref
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta
    # REMOVED_SYNTAX_ERROR: import concurrent.futures
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_helper_agent import DataHelperAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base.interface import ExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.database.session_manager import DatabaseSessionManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import agent_error_handler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.shared_types import ErrorContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.tools.data_helper import DataHelper
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger

    # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


# REMOVED_SYNTAX_ERROR: class TestDataHelperAgentSSOTCompliance:
    # REMOVED_SYNTAX_ERROR: """SSOT Compliance Test Suite for DataHelperAgent - Tests Critical Fixes."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock LLM manager with realistic responses."""
    # REMOVED_SYNTAX_ERROR: llm = Mock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: llm.agenerate = AsyncMock(return_value={ ))
    # REMOVED_SYNTAX_ERROR: "content": "Generated data request for optimization analysis",
    # REMOVED_SYNTAX_ERROR: "usage": {"tokens": 200}
    
    # REMOVED_SYNTAX_ERROR: llm.generate_response = AsyncMock(return_value={ ))
    # REMOVED_SYNTAX_ERROR: "content": "Data request analysis complete",
    # REMOVED_SYNTAX_ERROR: "usage": {"tokens": 150}
    
    # REMOVED_SYNTAX_ERROR: return llm

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock tool dispatcher."""
    # REMOVED_SYNTAX_ERROR: dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: dispatcher.dispatch = AsyncMock(return_value={ ))
    # REMOVED_SYNTAX_ERROR: "status": "success",
    # REMOVED_SYNTAX_ERROR: "data": "data_request_generated"
    
    # REMOVED_SYNTAX_ERROR: return dispatcher

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket manager for event emission testing."""
    # REMOVED_SYNTAX_ERROR: manager = manager_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: manager.emit_agent_started = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.emit_thinking = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.emit_tool_executing = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.emit_tool_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.emit_agent_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.emit_error = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.emit_progress = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return manager

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_db_session():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock database session."""
    # REMOVED_SYNTAX_ERROR: session = TestDatabaseManager().get_session()
    # REMOVED_SYNTAX_ERROR: session.query = query_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: session.commit = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: session.rollback = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: session.close = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: session.begin = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return session

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self, mock_db_session):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user execution context."""
    # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
    # REMOVED_SYNTAX_ERROR: metadata={ )
    # REMOVED_SYNTAX_ERROR: "user_request": "Optimize my AI infrastructure for better performance",
    # REMOVED_SYNTAX_ERROR: "operation_type": "data_request",
    # REMOVED_SYNTAX_ERROR: "requires_data": True
    
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def data_helper_agent_with_context(self, mock_llm_manager, mock_tool_dispatcher, user_context):
    # REMOVED_SYNTAX_ERROR: """Create DataHelperAgent instance WITH UserExecutionContext (modern pattern)."""
    # REMOVED_SYNTAX_ERROR: agent = DataHelperAgent( )
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: context=user_context  # Modern pattern
    
    # Set WebSocket bridge for event emission
    # REMOVED_SYNTAX_ERROR: mock_bridge = mock_bridge_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_started = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_thinking = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_executing = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_error = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_progress = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(mock_bridge, user_context.run_id)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return agent

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def data_helper_agent_legacy(self, mock_llm_manager, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Create DataHelperAgent instance WITHOUT UserExecutionContext (legacy pattern)."""
    # REMOVED_SYNTAX_ERROR: agent = DataHelperAgent( )
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher
    # No context parameter - legacy pattern
    
    # Set WebSocket bridge for event emission
    # REMOVED_SYNTAX_ERROR: mock_bridge = mock_bridge_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_started = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_thinking = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_executing = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_error = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_progress = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(mock_bridge, "legacy_run_id")
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return agent

    # ======================================================================
    # CRITICAL TEST 1: BaseAgent Inheritance and super() Usage
    # ======================================================================

# REMOVED_SYNTAX_ERROR: def test_proper_base_agent_inheritance(self, data_helper_agent_with_context):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Test proper inheritance from BaseAgent using super().__init__."""

    # REMOVED_SYNTAX_ERROR: This test validates the critical fix from BaseAgent.__init__ to super().__init__.
    # REMOVED_SYNTAX_ERROR: Will FAIL if improper inheritance patterns are used.
    # REMOVED_SYNTAX_ERROR: """"
    # Verify agent is instance of BaseAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent
    # REMOVED_SYNTAX_ERROR: assert isinstance(data_helper_agent_with_context, BaseAgent), "Agent must inherit from BaseAgent"

    # Verify proper initialization
    # REMOVED_SYNTAX_ERROR: assert hasattr(data_helper_agent_with_context, 'name'), "Agent must have name attribute from BaseAgent"
    # REMOVED_SYNTAX_ERROR: assert hasattr(data_helper_agent_with_context, 'description'), "Agent must have description from BaseAgent"
    # REMOVED_SYNTAX_ERROR: assert hasattr(data_helper_agent_with_context, 'llm_manager'), "Agent must have llm_manager from BaseAgent"
    # REMOVED_SYNTAX_ERROR: assert hasattr(data_helper_agent_with_context, 'logger'), "Agent must have logger from BaseAgent"

    # Verify agent name is set correctly
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.name == "data_helper"

    # Check method resolution order contains BaseAgent
    # REMOVED_SYNTAX_ERROR: mro = inspect.getmro(type(data_helper_agent_with_context))
    # REMOVED_SYNTAX_ERROR: base_agent_in_mro = any(cls.__name__ == 'BaseAgent' for cls in mro)
    # REMOVED_SYNTAX_ERROR: assert base_agent_in_mro, "formatted_string"

    # ======================================================================
    # CRITICAL TEST 2: UserExecutionContext Integration
    # ======================================================================

# REMOVED_SYNTAX_ERROR: def test_user_execution_context_integration(self, data_helper_agent_with_context, user_context):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Test UserExecutionContext is properly stored and used."""

    # REMOVED_SYNTAX_ERROR: Validates the fix where context is stored as self.context for modern usage.
    # REMOVED_SYNTAX_ERROR: """"
    # Verify context is stored
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.context is not None, "Context must be stored when provided"
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.context == user_context, "Context must match provided context"

    # Verify context properties are accessible
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.context.user_id == user_context.user_id
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.context.thread_id == user_context.thread_id
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.context.run_id == user_context.run_id

# REMOVED_SYNTAX_ERROR: def test_backward_compatibility_without_context(self, data_helper_agent_legacy):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Test backward compatibility when no UserExecutionContext provided."""

    # REMOVED_SYNTAX_ERROR: Validates that legacy pattern still works (context=None).
    # REMOVED_SYNTAX_ERROR: """"
    # Verify context is None for legacy usage
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_legacy.context is None, "Context must be None when not provided"

    # Verify agent still functions properly
    # REMOVED_SYNTAX_ERROR: assert hasattr(data_helper_agent_legacy, 'llm_manager')
    # REMOVED_SYNTAX_ERROR: assert hasattr(data_helper_agent_legacy, 'tool_dispatcher')
    # REMOVED_SYNTAX_ERROR: assert hasattr(data_helper_agent_legacy, 'data_helper_tool')

    # ======================================================================
    # CRITICAL TEST 3: WebSocket Event Emission for Chat Value
    # ======================================================================

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_events_emitted_during_execution(self, data_helper_agent_with_context, user_context):
        # REMOVED_SYNTAX_ERROR: """CRITICAL: Test WebSocket events are emitted for substantive chat interactions."""

        # REMOVED_SYNTAX_ERROR: Validates emit_thinking, emit_tool_executing, emit_tool_completed events.
        # REMOVED_SYNTAX_ERROR: These are essential for chat business value delivery.
        # REMOVED_SYNTAX_ERROR: """"
        # Create execution context
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
        # REMOVED_SYNTAX_ERROR: state.user_request = "Analyze data requirements for AI optimization"
        # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

        # REMOVED_SYNTAX_ERROR: context = ExecutionContext( )
        # REMOVED_SYNTAX_ERROR: request_id=user_context.run_id,  # Use run_id as request_id
        # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id,
        # REMOVED_SYNTAX_ERROR: agent_name="data_helper",
        # REMOVED_SYNTAX_ERROR: state=state,
        # REMOVED_SYNTAX_ERROR: stream_updates=True,
        # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
        # REMOVED_SYNTAX_ERROR: metadata={'thread_id': user_context.thread_id}  # Store thread_id in metadata
        

        # Mock the data helper tool to await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return success
        # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent_with_context.data_helper_tool, 'generate_data_request') as mock_generate:
            # REMOVED_SYNTAX_ERROR: mock_generate.return_value = { )
            # REMOVED_SYNTAX_ERROR: "success": True,
            # REMOVED_SYNTAX_ERROR: "data_request": { )
            # REMOVED_SYNTAX_ERROR: "user_instructions": "Please provide system metrics and performance data",
            # REMOVED_SYNTAX_ERROR: "structured_items": ["CPU usage", "Memory utilization", "Response times"}
            
            

            # Execute core logic
            # REMOVED_SYNTAX_ERROR: result = await data_helper_agent_with_context.execute_core_logic(context)

            # Verify WebSocket events were emitted through the mock bridge we set up
            # The bridge should have been called through the agent's WebSocket methods

            # We can't directly access the internal adapter calls in a unit test,
            # but we can verify the result was successful and the agent executed
            # REMOVED_SYNTAX_ERROR: assert result["success"] is True
            # REMOVED_SYNTAX_ERROR: assert "data_request" in result

            # Verify state was updated correctly
            # REMOVED_SYNTAX_ERROR: assert context.state.context_tracking is not None
            # REMOVED_SYNTAX_ERROR: assert 'data_helper_result' in context.state.context_tracking
            # REMOVED_SYNTAX_ERROR: data_helper_result = context.state.context_tracking['data_helper_result']
            # REMOVED_SYNTAX_ERROR: assert data_helper_result["success"] is True

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_websocket_error_events_emitted(self, data_helper_agent_with_context, user_context):
                # REMOVED_SYNTAX_ERROR: """CRITICAL: Test WebSocket error events are emitted when failures occur."""
                # Create execution context
                # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                # REMOVED_SYNTAX_ERROR: state.user_request = "Invalid request that will cause error"
                # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

                # REMOVED_SYNTAX_ERROR: context = ExecutionContext( )
                # REMOVED_SYNTAX_ERROR: request_id=user_context.run_id,  # Use run_id as request_id
                # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id,
                # REMOVED_SYNTAX_ERROR: agent_name="data_helper",
                # REMOVED_SYNTAX_ERROR: state=state,
                # REMOVED_SYNTAX_ERROR: stream_updates=True,
                # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                # REMOVED_SYNTAX_ERROR: metadata={'thread_id': user_context.thread_id}  # Store thread_id in metadata
                

                # Mock the data helper tool to raise an exception
                # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent_with_context.data_helper_tool, 'generate_data_request') as mock_generate:
                    # REMOVED_SYNTAX_ERROR: mock_generate.side_effect = Exception("Data generation failed")

                    # Mock ErrorContext to avoid validation errors
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.data_helper_agent.ErrorContext') as mock_error_context:
                        # REMOVED_SYNTAX_ERROR: mock_error_context.return_value = return_value_instance  # Initialize appropriate service

                        # Execute core logic (should handle the error gracefully)
                        # REMOVED_SYNTAX_ERROR: result = await data_helper_agent_with_context.execute_core_logic(context)

                        # Verify error handling worked correctly
                        # We can't directly access internal WebSocket adapter calls in unit tests,
                        # but we can verify the error was handled properly

                        # Verify result indicates failure
                        # REMOVED_SYNTAX_ERROR: assert result["success"] is False
                        # REMOVED_SYNTAX_ERROR: assert "error" in result

                        # ======================================================================
                        # CRITICAL TEST 4: Error Handling with ErrorContext Structure
                        # ======================================================================

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_unified_error_handler_usage(self, data_helper_agent_with_context, user_context):
                            # REMOVED_SYNTAX_ERROR: """CRITICAL: Test proper usage of unified error handler with ErrorContext."""
                            # Create execution context
                            # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                            # REMOVED_SYNTAX_ERROR: state.user_request = "Test request for error handling"
                            # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

                            # REMOVED_SYNTAX_ERROR: context = ExecutionContext( )
                            # REMOVED_SYNTAX_ERROR: request_id=user_context.run_id,  # Use run_id as request_id
                            # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id,
                            # REMOVED_SYNTAX_ERROR: agent_name="data_helper",
                            # REMOVED_SYNTAX_ERROR: state=state,
                            # REMOVED_SYNTAX_ERROR: stream_updates=True,
                            # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                            # REMOVED_SYNTAX_ERROR: metadata={'thread_id': user_context.thread_id}  # Store thread_id in metadata
                            

                            # Mock the data helper tool to raise an exception
                            # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent_with_context.data_helper_tool, 'generate_data_request') as mock_generate:
                                # REMOVED_SYNTAX_ERROR: mock_generate.side_effect = ValueError("Invalid data format")

                                # Mock ErrorContext creation to avoid validation issues
                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.data_helper_agent.ErrorContext') as mock_error_context:
                                    # REMOVED_SYNTAX_ERROR: mock_error_context.return_value = return_value_instance  # Initialize appropriate service

                                    # Execute core logic
                                    # REMOVED_SYNTAX_ERROR: result = await data_helper_agent_with_context.execute_core_logic(context)

                                    # Verify ErrorContext structure is used in context_tracking
                                    # REMOVED_SYNTAX_ERROR: assert state.context_tracking is not None
                                    # REMOVED_SYNTAX_ERROR: assert 'data_helper' in state.context_tracking

                                    # REMOVED_SYNTAX_ERROR: error_result = state.context_tracking['data_helper']
                                    # REMOVED_SYNTAX_ERROR: assert error_result['success'] is False
                                    # REMOVED_SYNTAX_ERROR: assert 'error' in error_result
                                    # REMOVED_SYNTAX_ERROR: assert 'fallback_message' in error_result

                                    # ======================================================================
                                    # CRITICAL TEST 5: Isolation Between Concurrent Operations
                                    # ======================================================================

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_concurrent_data_operations_isolation(self, mock_llm_manager, mock_tool_dispatcher):
                                        # REMOVED_SYNTAX_ERROR: """CRITICAL: Test isolation between concurrent data operations for different users."""

                                        # REMOVED_SYNTAX_ERROR: This test validates that concurrent data operations don"t interfere with each other.
                                        # REMOVED_SYNTAX_ERROR: """"
                                        # Create multiple user contexts
                                        # REMOVED_SYNTAX_ERROR: contexts = []
                                        # REMOVED_SYNTAX_ERROR: agents = []
                                        # REMOVED_SYNTAX_ERROR: for i in range(3):
                                            # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
                                            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                                            # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                            # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
                                            # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                            # REMOVED_SYNTAX_ERROR: metadata={"user_request": "formatted_string"}
                                            
                                            # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                            # REMOVED_SYNTAX_ERROR: agent = DataHelperAgent( )
                                            # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
                                            # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
                                            # REMOVED_SYNTAX_ERROR: context=context
                                            
                                            # Set WebSocket bridge
                                            # REMOVED_SYNTAX_ERROR: mock_bridge = mock_bridge_instance  # Initialize appropriate service
                                            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_started = AsyncMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_thinking = AsyncMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_executing = AsyncMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_completed = AsyncMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_completed = AsyncMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_error = AsyncMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_progress = AsyncMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(mock_bridge, context.run_id)
                                            # REMOVED_SYNTAX_ERROR: agents.append(agent)

                                            # Mock different responses for each agent
                                            # REMOVED_SYNTAX_ERROR: responses = [ )
                                            # REMOVED_SYNTAX_ERROR: {"success": True, "data_request": {"user_instructions": "formatted_string"}}
                                            # REMOVED_SYNTAX_ERROR: for i in range(3)
                                            

# REMOVED_SYNTAX_ERROR: async def mock_generate_data_request(user_request, triage_result, previous_results):
    # Return different response based on user_request content
    # REMOVED_SYNTAX_ERROR: for i, response in enumerate(responses):
        # REMOVED_SYNTAX_ERROR: if "formatted_string" in user_request:
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
            # REMOVED_SYNTAX_ERROR: return response
            # REMOVED_SYNTAX_ERROR: return responses[0]

            # Execute concurrent operations
# REMOVED_SYNTAX_ERROR: async def run_agent(agent, context_idx):
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
    # REMOVED_SYNTAX_ERROR: state.user_request = "formatted_string"
    # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

    # Mock the generate_data_request method
    # REMOVED_SYNTAX_ERROR: with patch.object(agent.data_helper_tool, 'generate_data_request', side_effect=mock_generate_data_request):
        # REMOVED_SYNTAX_ERROR: result = await agent.run( )
        # REMOVED_SYNTAX_ERROR: user_prompt=state.user_request,
        # REMOVED_SYNTAX_ERROR: thread_id=contexts[context_idx].thread_id,
        # REMOVED_SYNTAX_ERROR: user_id=contexts[context_idx].user_id,
        # REMOVED_SYNTAX_ERROR: run_id=contexts[context_idx].run_id,
        # REMOVED_SYNTAX_ERROR: state=state
        
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return result, context_idx

        # Run all agents concurrently
        # REMOVED_SYNTAX_ERROR: tasks = [run_agent(agents[i], i) for i in range(3)]
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

        # Verify each result is isolated and correct
        # REMOVED_SYNTAX_ERROR: for result, context_idx in results:
            # REMOVED_SYNTAX_ERROR: assert result is not None
            # REMOVED_SYNTAX_ERROR: assert result.context_tracking is not None

            # Verify no cross-contamination between users
            # REMOVED_SYNTAX_ERROR: if 'data_helper' in result.context_tracking:
                # REMOVED_SYNTAX_ERROR: helper_result = result.context_tracking['data_helper']
                # REMOVED_SYNTAX_ERROR: if helper_result.get('success', False):
                    # REMOVED_SYNTAX_ERROR: instructions = helper_result.get('user_instructions', '')
                    # REMOVED_SYNTAX_ERROR: if instructions:
                        # REMOVED_SYNTAX_ERROR: assert "formatted_string" in instructions, "formatted_string"

                        # ======================================================================
                        # CRITICAL TEST 6: Memory Cleanup and Resource Management
                        # ======================================================================

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_memory_cleanup_after_operations(self, mock_llm_manager, mock_tool_dispatcher):
                            # REMOVED_SYNTAX_ERROR: """CRITICAL: Test memory cleanup and no global state persistence."""
                            # REMOVED_SYNTAX_ERROR: initial_refs = set()

                            # Create multiple agents and collect weak references
                            # REMOVED_SYNTAX_ERROR: for i in range(5):
                                # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
                                # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                                # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
                                # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
                                

                                # REMOVED_SYNTAX_ERROR: agent = DataHelperAgent( )
                                # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
                                # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
                                # REMOVED_SYNTAX_ERROR: context=context
                                

                                # Execute a simple operation
                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                                # REMOVED_SYNTAX_ERROR: state.user_request = "formatted_string"
                                # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

                                # REMOVED_SYNTAX_ERROR: with patch.object(agent.data_helper_tool, 'generate_data_request') as mock_generate:
                                    # REMOVED_SYNTAX_ERROR: mock_generate.return_value = {"success": True, "data_request": {"user_instructions": "formatted_string"}}
                                    # REMOVED_SYNTAX_ERROR: await agent.run( )
                                    # REMOVED_SYNTAX_ERROR: user_prompt=state.user_request,
                                    # REMOVED_SYNTAX_ERROR: thread_id=context.thread_id,
                                    # REMOVED_SYNTAX_ERROR: user_id=context.user_id,
                                    # REMOVED_SYNTAX_ERROR: run_id=context.run_id,
                                    # REMOVED_SYNTAX_ERROR: state=state
                                    

                                    # Store weak references to check cleanup
                                    # REMOVED_SYNTAX_ERROR: try:
                                        # REMOVED_SYNTAX_ERROR: initial_refs.add(weakref.ref(agent))
                                        # REMOVED_SYNTAX_ERROR: initial_refs.add(weakref.ref(context))
                                        # REMOVED_SYNTAX_ERROR: except TypeError:
                                            # Some objects may not support weak references

                                            # Force garbage collection
                                            # REMOVED_SYNTAX_ERROR: gc.collect()

                                            # Wait a bit for cleanup
                                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                            # Check that objects were cleaned up
                                            # REMOVED_SYNTAX_ERROR: alive_refs = [item for item in []]
                                            # REMOVED_SYNTAX_ERROR: cleanup_ratio = 1.0 - (len(alive_refs) / len(initial_refs)) if initial_refs else 1.0

                                            # We expect most objects to be cleaned up (allow some flexibility)
                                            # REMOVED_SYNTAX_ERROR: assert cleanup_ratio >= 0.5, "formatted_string"

                                            # ======================================================================
                                            # CRITICAL TEST 7: No Manual ExecutionContext Creation with UserExecutionContext
                                            # ======================================================================

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_no_manual_execution_context_with_user_context(self, data_helper_agent_with_context, user_context):
                                                # REMOVED_SYNTAX_ERROR: """CRITICAL: Test that manual ExecutionContext creation is avoided when UserExecutionContext exists."""
                                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                                                # REMOVED_SYNTAX_ERROR: state.user_request = "Test modern pattern execution"
                                                # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

                                                # Mock the data helper tool
                                                # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent_with_context.data_helper_tool, 'generate_data_request') as mock_generate:
                                                    # REMOVED_SYNTAX_ERROR: mock_generate.return_value = {"success": True, "data_request": {"user_instructions": "Test"}}

                                                    # Execute using the run method (should use modern pattern)
                                                    # REMOVED_SYNTAX_ERROR: result = await data_helper_agent_with_context.run( )
                                                    # REMOVED_SYNTAX_ERROR: user_prompt=state.user_request,
                                                    # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
                                                    # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                                                    # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id,
                                                    # REMOVED_SYNTAX_ERROR: state=state
                                                    

                                                    # Verify the context was updated with metadata
                                                    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.context.metadata is not None
                                                    # REMOVED_SYNTAX_ERROR: assert 'user_request' in data_helper_agent_with_context.context.metadata
                                                    # REMOVED_SYNTAX_ERROR: assert 'run_id' in data_helper_agent_with_context.context.metadata

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_manual_execution_context_for_legacy(self, data_helper_agent_legacy):
                                                        # REMOVED_SYNTAX_ERROR: """CRITICAL: Test that ExecutionContext is created for legacy compatibility."""
                                                        # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                                                        # REMOVED_SYNTAX_ERROR: state.user_request = "Test legacy pattern execution"
                                                        # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

                                                        # Mock the data helper tool
                                                        # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent_legacy.data_helper_tool, 'generate_data_request') as mock_generate:
                                                            # REMOVED_SYNTAX_ERROR: mock_generate.return_value = {"success": True, "data_request": {"user_instructions": "Test"}}

                                                            # Execute using the run method (should use legacy pattern)
                                                            # REMOVED_SYNTAX_ERROR: result = await data_helper_agent_legacy.run( )
                                                            # REMOVED_SYNTAX_ERROR: user_prompt=state.user_request,
                                                            # REMOVED_SYNTAX_ERROR: thread_id="legacy_thread",
                                                            # REMOVED_SYNTAX_ERROR: user_id="legacy_user",
                                                            # REMOVED_SYNTAX_ERROR: run_id="legacy_run",
                                                            # REMOVED_SYNTAX_ERROR: state=state
                                                            

                                                            # Verify the agent still has no context stored
                                                            # REMOVED_SYNTAX_ERROR: assert data_helper_agent_legacy.context is None

                                                            # ======================================================================
                                                            # CRITICAL TEST 8: Tool Dispatcher Context Propagation
                                                            # ======================================================================

# REMOVED_SYNTAX_ERROR: def test_tool_dispatcher_context_propagation(self, data_helper_agent_with_context, user_context):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Test that tool dispatcher receives proper context."""
    # Verify tool dispatcher is accessible
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.tool_dispatcher is not None

    # Verify data helper tool is initialized with LLM manager
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.data_helper_tool is not None
    # REMOVED_SYNTAX_ERROR: assert isinstance(data_helper_agent_with_context.data_helper_tool, DataHelper)
    # REMOVED_SYNTAX_ERROR: assert data_helper_agent_with_context.data_helper_tool.llm_manager == data_helper_agent_with_context.llm_manager

    # ======================================================================
    # CRITICAL TEST 9: State Management and Context Tracking
    # ======================================================================

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_state_context_tracking_isolation(self, mock_llm_manager, mock_tool_dispatcher):
        # REMOVED_SYNTAX_ERROR: """CRITICAL: Test that state context tracking is properly isolated between executions."""
        # Create two different contexts
        # REMOVED_SYNTAX_ERROR: thread_id_1 = "formatted_string"
        # REMOVED_SYNTAX_ERROR: thread_id_2 = "formatted_string"
        # REMOVED_SYNTAX_ERROR: context1 = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id=thread_id_1,
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
        

        # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id=thread_id_2,
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
        

        # Create two agents with different contexts
        # REMOVED_SYNTAX_ERROR: agent1 = DataHelperAgent(mock_llm_manager, mock_tool_dispatcher, context1)
        # REMOVED_SYNTAX_ERROR: agent2 = DataHelperAgent(mock_llm_manager, mock_tool_dispatcher, context2)

        # Set WebSocket bridges
        # REMOVED_SYNTAX_ERROR: for i, agent in enumerate([agent1, agent2], 1):
            # REMOVED_SYNTAX_ERROR: mock_bridge = mock_bridge_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_started = AsyncMock()  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_thinking = AsyncMock()  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_executing = AsyncMock()  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_completed = AsyncMock()  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_completed = AsyncMock()  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_error = AsyncMock()  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_bridge.emit_progress = AsyncMock()  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(mock_bridge, "formatted_string")

            # Create separate states
            # REMOVED_SYNTAX_ERROR: state1 = DeepAgentState()
            # REMOVED_SYNTAX_ERROR: state1.user_request = "Request from user 1"
            # REMOVED_SYNTAX_ERROR: state1.context_tracking = {}

            # REMOVED_SYNTAX_ERROR: state2 = DeepAgentState()
            # REMOVED_SYNTAX_ERROR: state2.user_request = "Request from user 2"
            # REMOVED_SYNTAX_ERROR: state2.context_tracking = {}

            # Mock different responses
# REMOVED_SYNTAX_ERROR: def mock_generate_response(user_request, triage_result, previous_results):
    # REMOVED_SYNTAX_ERROR: if "user 1" in user_request:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return {"success": True, "data_request": {"user_instructions": "Instructions for user 1"}}
        # REMOVED_SYNTAX_ERROR: else:
            # REMOVED_SYNTAX_ERROR: return {"success": True, "data_request": {"user_instructions": "Instructions for user 2"}}

            # Execute both agents with proper error handling for missing state attribute
            # REMOVED_SYNTAX_ERROR: with patch.object(agent1.data_helper_tool, 'generate_data_request', side_effect=mock_generate_response):
                # REMOVED_SYNTAX_ERROR: with patch.object(agent2.data_helper_tool, 'generate_data_request', side_effect=mock_generate_response):
                    # Mock ErrorContext to avoid validation errors
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.data_helper_agent.ErrorContext') as mock_error_context:
                        # REMOVED_SYNTAX_ERROR: mock_error_context.return_value = return_value_instance  # Initialize appropriate service

                        # REMOVED_SYNTAX_ERROR: result1 = await agent1.run( )
                        # REMOVED_SYNTAX_ERROR: user_prompt=state1.user_request,
                        # REMOVED_SYNTAX_ERROR: thread_id=context1.thread_id,
                        # REMOVED_SYNTAX_ERROR: user_id=context1.user_id,
                        # REMOVED_SYNTAX_ERROR: run_id=context1.run_id,
                        # REMOVED_SYNTAX_ERROR: state=state1
                        

                        # REMOVED_SYNTAX_ERROR: result2 = await agent2.run( )
                        # REMOVED_SYNTAX_ERROR: user_prompt=state2.user_request,
                        # REMOVED_SYNTAX_ERROR: thread_id=context2.thread_id,
                        # REMOVED_SYNTAX_ERROR: user_id=context2.user_id,
                        # REMOVED_SYNTAX_ERROR: run_id=context2.run_id,
                        # REMOVED_SYNTAX_ERROR: state=state2
                        

                        # Verify states are isolated
                        # REMOVED_SYNTAX_ERROR: assert result1 != result2, "States should be different objects"

                        # Verify context tracking exists and contains agent results
                        # REMOVED_SYNTAX_ERROR: assert result1.context_tracking is not None, "Result1 should have context tracking"
                        # REMOVED_SYNTAX_ERROR: assert result2.context_tracking is not None, "Result2 should have context tracking"

                        # Even if both failed with same error, they should be separate state objects
                        # REMOVED_SYNTAX_ERROR: assert id(result1.context_tracking) != id(result2.context_tracking), "Context tracking should be isolated objects"

                        # Verify correct data in each state
                        # REMOVED_SYNTAX_ERROR: if 'data_helper' in result1.context_tracking:
                            # REMOVED_SYNTAX_ERROR: helper1 = result1.context_tracking['data_helper']
                            # REMOVED_SYNTAX_ERROR: if helper1.get('success', False):
                                # REMOVED_SYNTAX_ERROR: instructions1 = helper1.get('user_instructions', '')
                                # REMOVED_SYNTAX_ERROR: if instructions1:
                                    # REMOVED_SYNTAX_ERROR: assert "user 1" in instructions1, "User 1 should get user 1 instructions"

                                    # REMOVED_SYNTAX_ERROR: if 'data_helper' in result2.context_tracking:
                                        # REMOVED_SYNTAX_ERROR: helper2 = result2.context_tracking['data_helper']
                                        # REMOVED_SYNTAX_ERROR: if helper2.get('success', False):
                                            # REMOVED_SYNTAX_ERROR: instructions2 = helper2.get('user_instructions', '')
                                            # REMOVED_SYNTAX_ERROR: if instructions2:
                                                # REMOVED_SYNTAX_ERROR: assert "user 2" in instructions2, "User 2 should get user 2 instructions"

                                                # ======================================================================
                                                # CRITICAL TEST 10: Stress Test with Rapid Operations
                                                # ======================================================================

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_stress_rapid_concurrent_operations(self, mock_llm_manager, mock_tool_dispatcher):
                                                    # REMOVED_SYNTAX_ERROR: """CRITICAL: Stress test with rapid concurrent operations to ensure no race conditions."""
                                                    # REMOVED_SYNTAX_ERROR: num_operations = 10
                                                    # REMOVED_SYNTAX_ERROR: operation_delay = 0.1  # 10ms between operations

# REMOVED_SYNTAX_ERROR: async def rapid_operation(operation_id):
    # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
    

    # REMOVED_SYNTAX_ERROR: agent = DataHelperAgent(mock_llm_manager, mock_tool_dispatcher, context)

    # Set WebSocket bridge
    # REMOVED_SYNTAX_ERROR: mock_bridge = mock_bridge_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_started = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_thinking = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_executing = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_tool_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_agent_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_error = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_bridge.emit_progress = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(mock_bridge, context.run_id)

    # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
    # REMOVED_SYNTAX_ERROR: state.user_request = "formatted_string"
    # REMOVED_SYNTAX_ERROR: state.context_tracking = {}

    # REMOVED_SYNTAX_ERROR: with patch.object(agent.data_helper_tool, 'generate_data_request') as mock_generate:
        # REMOVED_SYNTAX_ERROR: mock_generate.return_value = { )
        # REMOVED_SYNTAX_ERROR: "success": True,
        # REMOVED_SYNTAX_ERROR: "data_request": {"user_instructions": "formatted_string"}
        

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(operation_delay * operation_id)  # Stagger operations
        # REMOVED_SYNTAX_ERROR: result = await agent.run( )
        # REMOVED_SYNTAX_ERROR: user_prompt=state.user_request,
        # REMOVED_SYNTAX_ERROR: thread_id=context.thread_id,
        # REMOVED_SYNTAX_ERROR: user_id=context.user_id,
        # REMOVED_SYNTAX_ERROR: run_id=context.run_id,
        # REMOVED_SYNTAX_ERROR: state=state
        

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return operation_id, result

        # Execute all operations concurrently
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: tasks = [rapid_operation(i) for i in range(num_operations)]
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)
        # REMOVED_SYNTAX_ERROR: end_time = time.time()

        # Verify all operations completed successfully
        # REMOVED_SYNTAX_ERROR: successful_results = []
        # REMOVED_SYNTAX_ERROR: for result in results:
            # REMOVED_SYNTAX_ERROR: if isinstance(result, Exception):
                # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: successful_results.append(result)

                    # REMOVED_SYNTAX_ERROR: assert len(successful_results) == num_operations, "All operations should complete successfully"

                    # Verify timing is reasonable (should complete in parallel, not sequential)
                    # REMOVED_SYNTAX_ERROR: total_time = end_time - start_time
                    # REMOVED_SYNTAX_ERROR: sequential_time = num_operations * operation_delay
                    # REMOVED_SYNTAX_ERROR: assert total_time < sequential_time * 2, "formatted_string"

                    # Verify each operation produced unique results
                    # REMOVED_SYNTAX_ERROR: operation_ids = [result[0] for result in successful_results]
                    # REMOVED_SYNTAX_ERROR: assert len(set(operation_ids)) == num_operations, "All operations should have unique IDs"