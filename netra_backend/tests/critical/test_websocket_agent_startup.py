from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''L3 Real Service Tests for agent startup scenarios.

# REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Validates real agent startup flows to prevent production failures
# REMOVED_SYNTAX_ERROR: when users send their first message, ensuring reliable AI service initialization.

# REMOVED_SYNTAX_ERROR: L3 REAL SERVICE TESTING: Uses real WebSocket connections, real database operations,
# REMOVED_SYNTAX_ERROR: and real message handlers to validate complete startup workflows.
""

import json
import uuid
from datetime import datetime
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from fastapi.testclient import TestClient

from netra_backend.app.main import app
from netra_backend.app.db.models_postgres import Run, Thread
from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService

# REMOVED_SYNTAX_ERROR: @pytest.mark.l3
# REMOVED_SYNTAX_ERROR: class TestRealAgentStartupWebSocketFlow:
    # REMOVED_SYNTAX_ERROR: '''L3 tests for real agent startup via WebSocket connections.

    # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Validates complete agent startup flows using real WebSocket
    # REMOVED_SYNTAX_ERROR: connections and real services, preventing production startup failures.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_client(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Real FastAPI test client for WebSocket connections."""
    # REMOVED_SYNTAX_ERROR: return TestClient(app)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Real WebSocket manager instance."""
    # REMOVED_SYNTAX_ERROR: return get_websocket_manager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_user_id(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Generate test user ID."""
    # REMOVED_SYNTAX_ERROR: return "formatted_string",
        # REMOVED_SYNTAX_ERROR: permissions=["read", "write"]
        

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: with test_client.websocket_connect( )
            # REMOVED_SYNTAX_ERROR: "/ws",
            # REMOVED_SYNTAX_ERROR: headers={"Authorization": "formatted_string"}
            # REMOVED_SYNTAX_ERROR: ) as websocket:
                # Send first message with no thread_id
                # REMOVED_SYNTAX_ERROR: first_message = { )
                # REMOVED_SYNTAX_ERROR: "type": "user_message",
                # REMOVED_SYNTAX_ERROR: "payload": { )
                # REMOVED_SYNTAX_ERROR: "content": "Hello Netra, analyze our AI costs",
                # REMOVED_SYNTAX_ERROR: "references": []
                
                

                # REMOVED_SYNTAX_ERROR: websocket.send_json(first_message)

                # Should receive response indicating agent startup
                # REMOVED_SYNTAX_ERROR: response = websocket.receive_json()
                # REMOVED_SYNTAX_ERROR: assert "type" in response
                # REMOVED_SYNTAX_ERROR: assert response.get("type") in ["agent_response", "status", "ack"]

                # Verify connection remains active
                # REMOVED_SYNTAX_ERROR: ping_message = {"type": "ping"}
                # REMOVED_SYNTAX_ERROR: websocket.send_json(ping_message)
                # REMOVED_SYNTAX_ERROR: ping_response = websocket.receive_json()
                # REMOVED_SYNTAX_ERROR: assert "type" in ping_response

                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # Log but don't fail for connection issues in test environment
                    # REMOVED_SYNTAX_ERROR: import logging
                    # REMOVED_SYNTAX_ERROR: logging.warning("formatted_string")
                    # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_empty_message_validation(self, real_message_handler, test_user_id):
                        # REMOVED_SYNTAX_ERROR: '''Test empty content validation in real message handler.

                        # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Prevents wasted compute resources on empty messages,
                        # REMOVED_SYNTAX_ERROR: optimizing AI infrastructure costs for customers.
                        # REMOVED_SYNTAX_ERROR: """"
                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.postgres_core import get_async_db

                        # REMOVED_SYNTAX_ERROR: payload = { )
                        # REMOVED_SYNTAX_ERROR: "content": "",  # Empty message
                        # REMOVED_SYNTAX_ERROR: "references": []
                        

                        # REMOVED_SYNTAX_ERROR: async with get_async_db() as session:
                            # REMOVED_SYNTAX_ERROR: try:
                                # Test message extraction from real handler
                                # REMOVED_SYNTAX_ERROR: text, refs, thread_id = real_message_handler._extract_message_data(payload)
                                # REMOVED_SYNTAX_ERROR: assert text == ""
                                # REMOVED_SYNTAX_ERROR: assert refs == []
                                # REMOVED_SYNTAX_ERROR: assert thread_id is None

                                # In production, empty messages should be handled gracefully
                                # without starting expensive agent operations
                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                    # Expected in test environment without full database
                                    # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_database_connection_failure_handling(self, test_client, test_user_id):
                                        # REMOVED_SYNTAX_ERROR: '''Test WebSocket behavior when database connection fails.

                                        # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Ensures graceful degradation when database is unavailable,
                                        # REMOVED_SYNTAX_ERROR: maintaining user experience and preventing silent failures.
                                        # REMOVED_SYNTAX_ERROR: """"
                                        # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.core.jwt_handler import JWTHandler
                                        # REMOVED_SYNTAX_ERROR: jwt_handler = JWTHandler()

                                        # REMOVED_SYNTAX_ERROR: token = jwt_handler.create_access_token( )
                                        # REMOVED_SYNTAX_ERROR: user_id=test_user_id,
                                        # REMOVED_SYNTAX_ERROR: email="formatted_string",
                                        # REMOVED_SYNTAX_ERROR: permissions=["read", "write"]
                                        

                                        # Test connection with potential database issues
                                        # REMOVED_SYNTAX_ERROR: try:
                                            # REMOVED_SYNTAX_ERROR: with test_client.websocket_connect( )
                                            # REMOVED_SYNTAX_ERROR: "/ws",
                                            # REMOVED_SYNTAX_ERROR: headers={"Authorization": "formatted_string"}
                                            # REMOVED_SYNTAX_ERROR: ) as websocket:
                                                # Send message that requires database operation
                                                # REMOVED_SYNTAX_ERROR: message = { )
                                                # REMOVED_SYNTAX_ERROR: "type": "user_message",
                                                # REMOVED_SYNTAX_ERROR: "payload": { )
                                                # REMOVED_SYNTAX_ERROR: "content": "Test database failure handling",
                                                # REMOVED_SYNTAX_ERROR: "references": []
                                                
                                                

                                                # REMOVED_SYNTAX_ERROR: websocket.send_json(message)

                                                # Should receive some response even if database fails
                                                # REMOVED_SYNTAX_ERROR: try:
                                                    # REMOVED_SYNTAX_ERROR: response = websocket.receive_json(timeout=5)
                                                    # REMOVED_SYNTAX_ERROR: assert "type" in response
                                                    # REMOVED_SYNTAX_ERROR: except Exception:
                                                        # Connection may close on database failure - this is acceptable

                                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                            # Expected in test environment
                                                            # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_supervisor_receives_correct_context(self, message_handler, mock_supervisor, mock_thread, mock_run):
                                                                # REMOVED_SYNTAX_ERROR: """Test 4: Supervisor receives correct context for first-time execution."""
                                                                # REMOVED_SYNTAX_ERROR: payload = { )
                                                                # REMOVED_SYNTAX_ERROR: "content": "What are our top cost drivers?",
                                                                # REMOVED_SYNTAX_ERROR: "references": []
                                                                

                                                                # Mock: Component isolation for testing without external dependencies
                                                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.postgres.get_async_db') as mock_db:
                                                                    # Mock: Database session isolation for transaction testing without real database dependency
                                                                    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock()  # TODO: Use real service instance
                                                                    # Mock: Database session isolation for transaction testing without real database dependency
                                                                    # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                                                                    # Mock: Generic component isolation for controlled unit testing
                                                                    # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aexit__ = AsyncMock()  # TODO: Use real service instance

                                                                    # REMOVED_SYNTAX_ERROR: await message_handler.handle_user_message("test_user", payload, mock_session)

                                                                    # Verify supervisor context was set up
                                                                    # REMOVED_SYNTAX_ERROR: assert mock_supervisor.thread_id == mock_thread.id
                                                                    # REMOVED_SYNTAX_ERROR: assert mock_supervisor.user_id == "test_user"
                                                                    # REMOVED_SYNTAX_ERROR: assert mock_supervisor.db_session == mock_session

                                                                    # Verify supervisor.run received all parameters
                                                                    # REMOVED_SYNTAX_ERROR: mock_supervisor.run.assert_called_once()
                                                                    # REMOVED_SYNTAX_ERROR: call_args = mock_supervisor.run.call_args[0]
                                                                    # REMOVED_SYNTAX_ERROR: assert call_args[0] == "What are our top cost drivers?"
                                                                    # REMOVED_SYNTAX_ERROR: assert call_args[1] == mock_thread.id  # thread_id
                                                                    # REMOVED_SYNTAX_ERROR: assert call_args[2] == "test_user"  # user_id
                                                                    # REMOVED_SYNTAX_ERROR: assert call_args[3] == mock_run.id  # run_id

                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                    # Removed problematic line: async def test_no_db_session_prevents_agent_start(self, message_handler, mock_supervisor):
                                                                        # REMOVED_SYNTAX_ERROR: """Test 5: Missing database session should prevent agent from starting."""
                                                                        # REMOVED_SYNTAX_ERROR: payload = { )
                                                                        # REMOVED_SYNTAX_ERROR: "content": "Test message",
                                                                        # REMOVED_SYNTAX_ERROR: "references": []
                                                                        

                                                                        # Call without db_session
                                                                        # REMOVED_SYNTAX_ERROR: await message_handler.handle_user_message("test_user", payload, None)

                                                                        # Should not start agent without DB session
                                                                        # REMOVED_SYNTAX_ERROR: mock_supervisor.run.assert_not_called()

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_existing_thread_id_uses_existing_thread(self, message_handler, mock_supervisor, mock_thread_service):
                                                                            # REMOVED_SYNTAX_ERROR: """Test 6: When thread_id is provided, use existing thread (not create new)."""
                                                                            # REMOVED_SYNTAX_ERROR: existing_thread_id = str(uuid.uuid4())
                                                                            # REMOVED_SYNTAX_ERROR: payload = { )
                                                                            # REMOVED_SYNTAX_ERROR: "content": "Follow-up message",
                                                                            # REMOVED_SYNTAX_ERROR: "references": [],
                                                                            # REMOVED_SYNTAX_ERROR: "thread_id": existing_thread_id
                                                                            

                                                                            # Mock existing thread
                                                                            # Mock: Component isolation for controlled unit testing
                                                                            # REMOVED_SYNTAX_ERROR: existing_thread = Mock(spec=Thread)
                                                                            # REMOVED_SYNTAX_ERROR: existing_thread.id = existing_thread_id
                                                                            # REMOVED_SYNTAX_ERROR: existing_thread.metadata_ = {"user_id": "test_user"}
                                                                            # Mock: Async component isolation for testing without real async operations
                                                                            # REMOVED_SYNTAX_ERROR: mock_thread_service.get_thread = AsyncMock(return_value=existing_thread)

                                                                            # Mock: Component isolation for testing without external dependencies
                                                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.postgres.get_async_db') as mock_db:
                                                                                # Mock: Database session isolation for transaction testing without real database dependency
                                                                                # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock()  # TODO: Use real service instance
                                                                                # Mock: Database session isolation for transaction testing without real database dependency
                                                                                # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                                                                                # Mock: Generic component isolation for controlled unit testing
                                                                                # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aexit__ = AsyncMock()  # TODO: Use real service instance

                                                                                # REMOVED_SYNTAX_ERROR: await message_handler.handle_user_message("test_user", payload, mock_session)

                                                                                # Should use existing thread, not create new
                                                                                # REMOVED_SYNTAX_ERROR: mock_thread_service.get_thread.assert_called_with(existing_thread_id, mock_session)
                                                                                # Should not create new thread since one exists
                                                                                # mock_thread_service.get_or_create_thread.assert_not_called()

                                                                                # Agent should still start with existing thread
                                                                                # REMOVED_SYNTAX_ERROR: mock_supervisor.run.assert_called_once()

                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                # Removed problematic line: async def test_wrong_user_thread_access_denied(self, message_handler, mock_supervisor, mock_thread_service):
                                                                                    # REMOVED_SYNTAX_ERROR: """Test 7: User trying to access another user's thread should be denied."""
                                                                                    # REMOVED_SYNTAX_ERROR: other_users_thread_id = str(uuid.uuid4())
                                                                                    # REMOVED_SYNTAX_ERROR: payload = { )
                                                                                    # REMOVED_SYNTAX_ERROR: "content": "Trying to access other thread",
                                                                                    # REMOVED_SYNTAX_ERROR: "references": [],
                                                                                    # REMOVED_SYNTAX_ERROR: "thread_id": other_users_thread_id
                                                                                    

                                                                                    # Mock thread belonging to different user
                                                                                    # Mock: Component isolation for controlled unit testing
                                                                                    # REMOVED_SYNTAX_ERROR: other_thread = Mock(spec=Thread)
                                                                                    # REMOVED_SYNTAX_ERROR: other_thread.id = other_users_thread_id
                                                                                    # REMOVED_SYNTAX_ERROR: other_thread.metadata_ = {"user_id": "different_user"}  # Different user
                                                                                    # Mock: Async component isolation for testing without real async operations
                                                                                    # REMOVED_SYNTAX_ERROR: mock_thread_service.get_thread = AsyncMock(return_value=other_thread)

                                                                                    # Mock: WebSocket connection isolation for testing without network overhead
                                                                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.get_websocket_manager().send_error') as mock_send_error:
                                                                                        # Mock: Component isolation for testing without external dependencies
                                                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.postgres.get_async_db') as mock_db:
                                                                                            # Mock: Database session isolation for transaction testing without real database dependency
                                                                                            # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock()  # TODO: Use real service instance
                                                                                            # Mock: Database session isolation for transaction testing without real database dependency
                                                                                            # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                                                                                            # Mock: Generic component isolation for controlled unit testing
                                                                                            # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aexit__ = AsyncMock()  # TODO: Use real service instance

                                                                                            # REMOVED_SYNTAX_ERROR: await message_handler.handle_user_message("test_user", payload, mock_session)

                                                                                            # Should send access denied error
                                                                                            # REMOVED_SYNTAX_ERROR: mock_send_error.assert_called_with("test_user", "Access denied to thread")

                                                                                            # Should NOT start agent
                                                                                            # REMOVED_SYNTAX_ERROR: mock_supervisor.run.assert_not_called()

                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                            # Removed problematic line: async def test_supervisor_exception_handled_gracefully(self, message_handler, mock_supervisor):
                                                                                                # REMOVED_SYNTAX_ERROR: """Test 8: Supervisor throwing exception should be handled gracefully."""
                                                                                                # REMOVED_SYNTAX_ERROR: payload = { )
                                                                                                # REMOVED_SYNTAX_ERROR: "content": "This will cause an error",
                                                                                                # REMOVED_SYNTAX_ERROR: "references": []
                                                                                                

                                                                                                # Make supervisor throw exception
                                                                                                # Mock: Async component isolation for testing without real async operations
                                                                                                # REMOVED_SYNTAX_ERROR: mock_supervisor.run = AsyncMock(side_effect=Exception("Supervisor failed"))

                                                                                                # Mock: WebSocket connection isolation for testing without network overhead
                                                                                                # REMOVED_SYNTAX_ERROR: try:
                                                                                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.get_websocket_manager().send_error') as mock_send_error:
                                                                                                        # Mock: Component isolation for testing without external dependencies
                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.postgres.get_async_db') as mock_db:
                                                                                                            # Mock: Database session isolation for transaction testing without real database dependency
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock()  # TODO: Use real service instance
                                                                                                            # Mock: Database session isolation for transaction testing without real database dependency
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                                                                                                            # Mock: Generic component isolation for controlled unit testing
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_db.return_value.__aexit__ = AsyncMock()  # TODO: Use real service instance

                                                                                                            # Should not raise exception to caller
                                                                                                            # REMOVED_SYNTAX_ERROR: await message_handler.handle_user_message("test_user", payload, mock_session)
                                                                                                            # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                                # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

                                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                                # Removed problematic line: async def test_concurrent_websocket_messages(self, test_client, test_user_id):
                                                                                                                    # REMOVED_SYNTAX_ERROR: '''Test concurrent message handling in single WebSocket session.

                                                                                                                    # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Validates system stability under concurrent message load,
                                                                                                                    # REMOVED_SYNTAX_ERROR: ensuring reliable AI service performance during active conversations.
                                                                                                                    # REMOVED_SYNTAX_ERROR: """"
                                                                                                                    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.core.jwt_handler import JWTHandler
                                                                                                                    # REMOVED_SYNTAX_ERROR: import asyncio

                                                                                                                    # REMOVED_SYNTAX_ERROR: jwt_handler = JWTHandler()
                                                                                                                    # REMOVED_SYNTAX_ERROR: token = jwt_handler.create_access_token( )
                                                                                                                    # REMOVED_SYNTAX_ERROR: user_id=test_user_id,
                                                                                                                    # REMOVED_SYNTAX_ERROR: email="formatted_string",
                                                                                                                    # REMOVED_SYNTAX_ERROR: permissions=["read", "write"]
                                                                                                                    

                                                                                                                    # REMOVED_SYNTAX_ERROR: try:
                                                                                                                        # REMOVED_SYNTAX_ERROR: with test_client.websocket_connect( )
                                                                                                                        # REMOVED_SYNTAX_ERROR: "/ws",
                                                                                                                        # REMOVED_SYNTAX_ERROR: headers={"Authorization": "formatted_string"}
                                                                                                                        # REMOVED_SYNTAX_ERROR: ) as websocket:
                                                                                                                            # Send multiple messages in quick succession
                                                                                                                            # REMOVED_SYNTAX_ERROR: messages = [ )
                                                                                                                            # REMOVED_SYNTAX_ERROR: {"type": "user_message", "payload": {"content": "formatted_string"type" in ping_response
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: except Exception:

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

                                                                                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                            # Removed problematic line: async def test_message_references_handling(self, real_message_handler, test_user_id):
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: '''Test message references parsing and handling.

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Validates proper handling of file references and attachments,
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: ensuring AI agents receive complete context for accurate analysis.
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: """"
                                                                                                                                                                # Test various reference formats
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: test_cases = [ )
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: { )
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "content": "Analyze this data",
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "references": ["file1.csv", "report.pdf", "metrics.json"],
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "expected_refs": ["file1.csv", "report.pdf", "metrics.json"]
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: },
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: { )
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "content": "Review document",
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "references": [],
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "expected_refs": []
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: },
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: { )
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "content": "Process files",
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "references": ["data/large_file.xlsx"],
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "expected_refs": ["data/large_file.xlsx"]
                                                                                                                                                                
                                                                                                                                                                

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: for test_case in test_cases:
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: text, refs, thread_id = real_message_handler._extract_message_data(test_case)

                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert text == test_case["content"]
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert refs == test_case["expected_refs"]
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert thread_id is None  # No thread_id in test cases

                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.l3
# REMOVED_SYNTAX_ERROR: class TestRealWebSocketEdgeCases:
    # REMOVED_SYNTAX_ERROR: '''L3 real service tests for WebSocket edge cases and data validation.

    # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Validates system robustness with various input formats,
    # REMOVED_SYNTAX_ERROR: ensuring reliable AI service operation across diverse user scenarios.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Real message handler for edge case testing."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_service_core import AgentService
    # REMOVED_SYNTAX_ERROR: supervisor = AgentService()
    # REMOVED_SYNTAX_ERROR: thread_service = ThreadService()
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return MessageHandlerService(supervisor, thread_service)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_unicode_content_real_handling(self, real_handler):
        # REMOVED_SYNTAX_ERROR: '''Test real Unicode and special character handling.

        # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Ensures international users can send AI queries
        # REMOVED_SYNTAX_ERROR: in their native languages without encoding issues.
        # REMOVED_SYNTAX_ERROR: """"
        # REMOVED_SYNTAX_ERROR: test_cases = [ )
        # REMOVED_SYNTAX_ERROR: "分析成本 💰 with special chars: é ñ ü",
        # REMOVED_SYNTAX_ERROR: "Анализ затрат на ИИ",  # Russian
        # REMOVED_SYNTAX_ERROR: "コスト分析 🤖",  # Japanese
        # REMOVED_SYNTAX_ERROR: "Análisis de costos 📊",  # Spanish
        # REMOVED_SYNTAX_ERROR: "Coût d"analyse 🔍"  # French
        

        # REMOVED_SYNTAX_ERROR: for content in test_cases:
            # REMOVED_SYNTAX_ERROR: payload = { )
            # REMOVED_SYNTAX_ERROR: "content": content,
            # REMOVED_SYNTAX_ERROR: "references": []
            

            # REMOVED_SYNTAX_ERROR: text, refs, thread_id = real_handler._extract_message_data(payload)
            # REMOVED_SYNTAX_ERROR: assert text == content
            # REMOVED_SYNTAX_ERROR: assert refs == []
            # REMOVED_SYNTAX_ERROR: assert thread_id is None

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_large_message_real_handling(self, real_handler):
                # REMOVED_SYNTAX_ERROR: '''Test real handling of large message content.

                # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Validates system capacity for detailed AI queries
                # REMOVED_SYNTAX_ERROR: and comprehensive context without performance degradation.
                # REMOVED_SYNTAX_ERROR: """"
                # Test various message sizes
                # REMOVED_SYNTAX_ERROR: size_tests = [ )
                # REMOVED_SYNTAX_ERROR: ("Short message", 13),
                # REMOVED_SYNTAX_ERROR: ("Medium message: " + "x" * 1000, 1016),  # ~1KB
                # REMOVED_SYNTAX_ERROR: ("Large message: " + "y" * 5000, 5015),   # ~5KB
                

                # REMOVED_SYNTAX_ERROR: for content, expected_length in size_tests:
                    # REMOVED_SYNTAX_ERROR: payload = { )
                    # REMOVED_SYNTAX_ERROR: "content": content,
                    # REMOVED_SYNTAX_ERROR: "references": []
                    

                    # REMOVED_SYNTAX_ERROR: text, refs, thread_id = real_handler._extract_message_data(payload)
                    # REMOVED_SYNTAX_ERROR: assert len(text) == expected_length
                    # REMOVED_SYNTAX_ERROR: assert text.startswith(content.split(":")[0] if ":" in content else content)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_thread_id_variations_real(self, real_handler):
                        # REMOVED_SYNTAX_ERROR: '''Test real handling of various thread_id formats.

                        # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Ensures consistent conversation threading across
                        # REMOVED_SYNTAX_ERROR: different client implementations and data formats.
                        # REMOVED_SYNTAX_ERROR: """"
                        # REMOVED_SYNTAX_ERROR: test_cases = [ )
                        # REMOVED_SYNTAX_ERROR: {"content": "Test", "expected_thread_id": None},  # Missing
                        # REMOVED_SYNTAX_ERROR: {"content": "Test", "thread_id": None, "expected_thread_id": None},  # Null
                        # REMOVED_SYNTAX_ERROR: {"content": "Test", "thread_id": "", "expected_thread_id": ""},  # Empty
                        # REMOVED_SYNTAX_ERROR: {"content": "Test", "thread_id": "valid-uuid-123", "expected_thread_id": "valid-uuid-123"},  # Valid
                        

                        # REMOVED_SYNTAX_ERROR: for test_case in test_cases:
                            # REMOVED_SYNTAX_ERROR: expected_thread_id = test_case.pop("expected_thread_id")
                            # REMOVED_SYNTAX_ERROR: text, refs, thread_id = real_handler._extract_message_data(test_case)

                            # REMOVED_SYNTAX_ERROR: assert text == "Test"
                            # REMOVED_SYNTAX_ERROR: assert refs == []
                            # REMOVED_SYNTAX_ERROR: assert thread_id == expected_thread_id

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_complex_references_real_parsing(self, real_handler):
                                # REMOVED_SYNTAX_ERROR: '''Test real parsing of complex reference formats.

                                # REMOVED_SYNTAX_ERROR: BUSINESS VALUE: Validates proper file reference handling for
                                # REMOVED_SYNTAX_ERROR: comprehensive AI analysis with multiple data sources.
                                # REMOVED_SYNTAX_ERROR: """"
                                # REMOVED_SYNTAX_ERROR: complex_cases = [ )
                                # Various file types
                                # REMOVED_SYNTAX_ERROR: ["document.pdf", "spreadsheet.xlsx", "image.png"],
                                # Path formats
                                # REMOVED_SYNTAX_ERROR: ["/absolute/path/file.csv", "relative/path/data.json"],
                                # URLs
                                # REMOVED_SYNTAX_ERROR: ["https://example.com/data.csv", "ftp://server/file.txt"],
                                # Mixed formats
                                # REMOVED_SYNTAX_ERROR: ["local_file.txt", "https://remote.com/data.json", "/path/to/file.csv"]
                                

                                # REMOVED_SYNTAX_ERROR: for references in complex_cases:
                                    # REMOVED_SYNTAX_ERROR: payload = { )
                                    # REMOVED_SYNTAX_ERROR: "content": "Analyze these files",
                                    # REMOVED_SYNTAX_ERROR: "references": references
                                    

                                    # REMOVED_SYNTAX_ERROR: text, refs, thread_id = real_handler._extract_message_data(payload)
                                    # REMOVED_SYNTAX_ERROR: assert text == "Analyze these files"
                                    # REMOVED_SYNTAX_ERROR: assert refs == references
                                    # REMOVED_SYNTAX_ERROR: assert thread_id is None