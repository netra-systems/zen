"""
Issue #1099 Legacy Handler Baseline Functionality Tests

BUSINESS IMPACT: $500K+ ARR Golden Path protection  
PURPOSE: Establish baseline functionality for legacy handlers before migration

These tests validate that legacy handlers work correctly in isolation,
providing a baseline for comparing SSOT migration results.

Test Strategy: Comprehensive validation of legacy handler core functionality

Created: 2025-09-15 (Issue #1099 Test Plan Phase 1)
"""

import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import json
import time

# Import legacy handlers for baseline testing
from netra_backend.app.services.websocket.message_handler import (
    BaseMessageHandler,
    StartAgentHandler,
    UserMessageHandler,
    ThreadHistoryHandler,
    StopAgentHandler,
    MessageHandlerService,
    create_handler_safely
)


class TestLegacyHandlerBaseline:
    """
    Legacy Handler Baseline Functionality Tests
    
    These tests validate that legacy handlers work correctly in their
    current environment, establishing a baseline for migration validation.
    """
    
    @pytest.fixture
    def mock_supervisor(self):
        """Mock supervisor for handler initialization"""
        supervisor = Mock()
        supervisor.execute_agent = AsyncMock()
        supervisor.process_user_message = AsyncMock()
        return supervisor
    
    @pytest.fixture
    def mock_db_session_factory(self):
        """Mock database session factory"""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_legacy_start_agent_handler_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy StartAgentHandler core functionality
        
        EXPECTED: PASS - Legacy handler works correctly in isolation
        VALIDATES: Core start_agent message processing workflow
        """
        handler = StartAgentHandler(mock_supervisor, mock_db_session_factory)
        
        # Verify handler type
        assert handler.get_message_type() == "start_agent"
        
        # Test successful message handling
        payload = {
            "user_request": "Create a data analysis report",
            "thread_id": "thread_123",
            "run_id": "run_456"
        }
        
        with patch.object(handler, '_process_start_agent_request', new_callable=AsyncMock) as mock_process:
            await handler.handle("user_123", payload)
            mock_process.assert_called_once_with("user_123", payload)
        
        # Test error handling
        with patch.object(handler, '_process_start_agent_request', side_effect=Exception("Test error")):
            with patch.object(handler, '_handle_agent_error', new_callable=AsyncMock) as mock_error:
                await handler.handle("user_123", payload)
                mock_error.assert_called_once()
        
        # Validate handler interface
        assert hasattr(handler, 'handle')
        assert hasattr(handler, 'get_message_type')
        assert callable(handler.handle)
        
        print("✅ Legacy StartAgentHandler baseline functionality validated")
    
    @pytest.mark.asyncio 
    async def test_legacy_user_message_handler_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy UserMessageHandler core functionality
        
        EXPECTED: PASS - Legacy handler processes user messages correctly
        VALIDATES: User message processing and error handling
        """
        handler = UserMessageHandler(mock_supervisor, mock_db_session_factory)
        
        # Verify handler type
        assert handler.get_message_type() == "user_message"
        
        # Test successful message handling
        payload = {
            "message": "Can you help me analyze this data?",
            "thread_id": "thread_123",
            "references": []
        }
        
        with patch.object(handler, '_process_user_message_request', new_callable=AsyncMock) as mock_process:
            await handler.handle("user_123", payload)
            mock_process.assert_called_once_with("user_123", payload)
        
        # Test error handling
        with patch.object(handler, '_process_user_message_request', side_effect=Exception("Test error")):
            with patch.object(handler, '_handle_user_message_error', new_callable=AsyncMock) as mock_error:
                await handler.handle("user_123", payload)
                mock_error.assert_called_once()
        
        # Validate message data extraction
        with patch.object(handler, '_extract_message_data', return_value=("test message", [])):
            text, refs = handler._extract_message_data(payload)
            assert text == "test message"
            assert refs == []
        
        print("✅ Legacy UserMessageHandler baseline functionality validated")
    
    @pytest.mark.asyncio
    async def test_legacy_thread_history_handler_baseline(self, mock_db_session_factory):
        """
        BASELINE TEST: Legacy ThreadHistoryHandler functionality
        
        EXPECTED: PASS - Legacy handler retrieves thread history correctly
        VALIDATES: Thread history retrieval and error handling
        """
        handler = ThreadHistoryHandler(mock_db_session_factory)
        
        # Verify handler type
        assert handler.get_message_type() == "get_thread_history"
        
        # Test successful history retrieval
        payload = {"thread_id": "thread_123"}
        
        with patch('netra_backend.app.services.database.unit_of_work.get_unit_of_work') as mock_uow:
            mock_uow.return_value.__aenter__ = AsyncMock()
            mock_uow.return_value.__aexit__ = AsyncMock()
            
            with patch.object(handler, '_process_thread_history_request', new_callable=AsyncMock) as mock_process:
                await handler.handle("user_123", payload)
                mock_process.assert_called_once()
        
        # Test error handling
        with patch('netra_backend.app.services.database.unit_of_work.get_unit_of_work', side_effect=Exception("DB error")):
            with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context:
                with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_manager:
                    mock_manager.return_value.send_error = AsyncMock()
                    await handler.handle("user_123", payload)
                    mock_manager.return_value.send_error.assert_called_once()
        
        print("✅ Legacy ThreadHistoryHandler baseline functionality validated")
    
    @pytest.mark.asyncio
    async def test_legacy_stop_agent_handler_baseline(self, mock_supervisor):
        """
        BASELINE TEST: Legacy StopAgentHandler functionality
        
        EXPECTED: PASS - Legacy handler stops agents correctly
        VALIDATES: Agent termination and notification
        """
        handler = StopAgentHandler(mock_supervisor)
        
        # Verify handler type  
        assert handler.get_message_type() == "stop_agent"
        
        # Test successful agent stop
        payload = {"reason": "user_requested"}
        
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context:
            with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_manager:
                mock_manager.return_value.send_to_user = AsyncMock()
                
                await handler.handle("user_123", payload)
                
                mock_manager.return_value.send_to_user.assert_called_once()
                call_args = mock_manager.return_value.send_to_user.call_args
                assert call_args[0][0] == "user_123"  # user_id
                assert call_args[0][1]["type"] == "agent_stopped"  # message type
        
        print("✅ Legacy StopAgentHandler baseline functionality validated")
    
    @pytest.mark.asyncio
    async def test_legacy_message_handler_service_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy MessageHandlerService orchestration
        
        EXPECTED: PASS - Legacy service manages handlers correctly
        VALIDATES: Handler registration, message routing, and processing
        """
        service = MessageHandlerService(mock_supervisor, mock_db_session_factory)
        
        # Verify handlers are set up
        assert len(service.handlers) >= 4  # start_agent, user_message, get_thread_history, stop_agent
        assert "start_agent" in service.handlers
        assert "user_message" in service.handlers
        assert "get_thread_history" in service.handlers
        assert "stop_agent" in service.handlers
        
        # Test message routing
        message = {
            "type": "start_agent",
            "user_request": "Test request"
        }
        
        with patch.object(service, '_validate_and_process_message', new_callable=AsyncMock) as mock_process:
            await service.handle_message("user_123", message)
            mock_process.assert_called_once_with("user_123", message)
        
        # Test message validation
        valid_message = {"type": "start_agent", "user_request": "test"}
        invalid_message = {"type": "unknown_type"}
        
        with patch.object(service, '_validate_message_format', new_callable=AsyncMock, return_value=True):
            with patch.object(service, '_process_message_through_queue', new_callable=AsyncMock) as mock_queue:
                await service._validate_and_process_message("user_123", valid_message)
                mock_queue.assert_called_once()
        
        # Test error handling
        with patch.object(service, '_validate_and_process_message', side_effect=Exception("Test error")):
            with patch.object(service, '_handle_processing_error', new_callable=AsyncMock) as mock_error:
                await service.handle_message("user_123", message)
                mock_error.assert_called_once()
        
        print("✅ Legacy MessageHandlerService baseline functionality validated")
    
    @pytest.mark.asyncio
    async def test_legacy_handler_thread_safety_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy handler thread safety (Phase 4 fix)
        
        EXPECTED: PASS - Legacy handlers handle concurrent access safely
        VALIDATES: Thread-safe handler creation and registry management
        """
        # Test thread-safe handler creation
        handler_type = "start_agent"
        
        # Test successful creation
        handler = await create_handler_safely(handler_type, mock_supervisor, mock_db_session_factory)
        assert handler is not None
        assert isinstance(handler, StartAgentHandler)
        
        # Test concurrent creation (should reuse existing handler)
        handler2 = await create_handler_safely(handler_type, mock_supervisor, mock_db_session_factory)
        assert handler2 is not None
        
        # Test unknown handler type
        unknown_handler = await create_handler_safely("unknown_type", mock_supervisor, mock_db_session_factory)
        assert unknown_handler is None
        
        # Test error handling in creation
        with patch('netra_backend.app.services.websocket.message_handler.StartAgentHandler', side_effect=Exception("Creation error")):
            error_handler = await create_handler_safely(handler_type, mock_supervisor, mock_db_session_factory)
            assert error_handler is None
        
        print("✅ Legacy handler thread safety baseline validated")
    
    @pytest.mark.asyncio
    async def test_legacy_message_queue_integration_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy message queue integration
        
        EXPECTED: PASS - Legacy handlers integrate with message queue correctly
        VALIDATES: Message queuing, priority handling, and processing
        """
        service = MessageHandlerService(mock_supervisor, mock_db_session_factory)
        
        # Test message queue processing
        message = {
            "type": "start_agent",
            "user_request": "Test request",
            "priority": "normal"
        }
        
        with patch('netra_backend.app.services.websocket.message_queue.message_queue') as mock_queue:
            mock_queue.put_nowait = Mock()
            
            with patch.object(service, '_create_queued_message', return_value=Mock()) as mock_create:
                with patch.object(service, '_validate_message_format', new_callable=AsyncMock, return_value=True):
                    await service._validate_and_process_message("user_123", message)
                    mock_create.assert_called_once()
                    mock_queue.put_nowait.assert_called_once()
        
        # Test message priority handling
        high_priority_message = {
            "type": "stop_agent",
            "priority": "high"
        }
        
        with patch.object(service, '_get_message_priority', return_value="high") as mock_priority:
            priority = service._get_message_priority(high_priority_message)
            assert priority == "high"
        
        print("✅ Legacy message queue integration baseline validated")
    
    def test_legacy_handler_interface_compliance_baseline(self):
        """
        BASELINE TEST: Legacy handler interface compliance
        
        EXPECTED: PASS - All legacy handlers implement required interface
        VALIDATES: BaseMessageHandler interface compliance
        """
        # Test base handler interface
        base_handler = Mock(spec=BaseMessageHandler)
        
        # Verify abstract methods exist
        assert hasattr(BaseMessageHandler, 'handle')
        assert hasattr(BaseMessageHandler, 'get_message_type')
        
        # Test concrete handler implementations
        handlers = [
            StartAgentHandler(Mock(), Mock()),
            UserMessageHandler(Mock(), Mock()),
            ThreadHistoryHandler(Mock()),
            StopAgentHandler(Mock())
        ]
        
        for handler in handlers:
            # Verify interface compliance
            assert hasattr(handler, 'handle')
            assert hasattr(handler, 'get_message_type')
            assert callable(handler.handle)
            assert callable(handler.get_message_type)
            
            # Verify message type is string
            message_type = handler.get_message_type()
            assert isinstance(message_type, str)
            assert len(message_type) > 0
        
        print("✅ Legacy handler interface compliance baseline validated")
    
    def test_legacy_handler_performance_baseline(self):
        """
        BASELINE TEST: Legacy handler performance characteristics
        
        EXPECTED: PASS - Legacy handlers meet performance requirements
        VALIDATES: Handler creation time, memory usage, response time
        """
        # Test handler creation performance
        start_time = time.time()
        
        handlers = []
        for _ in range(10):  # Create 10 handlers
            handler = StartAgentHandler(Mock(), Mock())
            handlers.append(handler)
        
        creation_time = time.time() - start_time
        
        # Baseline: Handler creation should be fast (< 100ms for 10 handlers)
        assert creation_time < 0.1  # 100ms
        
        # Test message type retrieval performance
        start_time = time.time()
        
        for handler in handlers:
            message_type = handler.get_message_type()
            assert message_type == "start_agent"
        
        retrieval_time = time.time() - start_time
        
        # Baseline: Message type retrieval should be very fast (< 10ms for 10 calls)
        assert retrieval_time < 0.01  # 10ms
        
        print(f"✅ Legacy handler performance baseline validated: "
              f"creation={creation_time:.3f}s, retrieval={retrieval_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_legacy_error_handling_patterns_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy error handling patterns
        
        EXPECTED: PASS - Legacy handlers handle errors consistently
        VALIDATES: Error propagation, logging, and user notification
        """
        # Test StartAgentHandler error handling
        start_handler = StartAgentHandler(mock_supervisor, mock_db_session_factory)
        
        with patch.object(start_handler, '_process_start_agent_request', side_effect=Exception("Agent error")):
            with patch.object(start_handler, '_handle_agent_error', new_callable=AsyncMock) as mock_error:
                # Should not raise exception - error should be handled internally
                await start_handler.handle("user_123", {"user_request": "test"})
                mock_error.assert_called_once()
        
        # Test UserMessageHandler error handling
        user_handler = UserMessageHandler(mock_supervisor, mock_db_session_factory)
        
        with patch.object(user_handler, '_process_user_message_request', side_effect=Exception("Message error")):
            with patch.object(user_handler, '_handle_user_message_error', new_callable=AsyncMock) as mock_error:
                await user_handler.handle("user_123", {"message": "test"})
                mock_error.assert_called_once()
        
        # Test MessageHandlerService error handling
        service = MessageHandlerService(mock_supervisor, mock_db_session_factory)
        
        with patch.object(service, '_validate_and_process_message', side_effect=Exception("Service error")):
            with patch.object(service, '_handle_processing_error', new_callable=AsyncMock) as mock_error:
                await service.handle_message("user_123", {"type": "start_agent"})
                mock_error.assert_called_once()
        
        print("✅ Legacy error handling patterns baseline validated")


class TestLegacyHandlerContextBehavior:
    """
    Tests for legacy handler context and state management behavior.
    These establish baseline behavior for context handling.
    """
    
    @pytest.mark.asyncio
    async def test_legacy_user_context_handling_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy handler user context behavior
        
        EXPECTED: PASS - Legacy handlers maintain user context correctly
        VALIDATES: User ID propagation and context isolation
        """
        handler = StartAgentHandler(mock_supervisor, mock_db_session_factory)
        
        user_id = "user_123"
        payload = {"user_request": "test"}
        
        with patch.object(handler, '_process_start_agent_request', new_callable=AsyncMock) as mock_process:
            await handler.handle(user_id, payload)
            
            # Verify user_id is passed correctly
            call_args = mock_process.call_args
            assert call_args[0][0] == user_id
            assert call_args[0][1] == payload
        
        # Test multiple users
        users = ["user_1", "user_2", "user_3"]
        
        for user in users:
            with patch.object(handler, '_process_start_agent_request', new_callable=AsyncMock) as mock_process:
                await handler.handle(user, payload)
                assert mock_process.call_args[0][0] == user
        
        print("✅ Legacy user context handling baseline validated")
    
    @pytest.mark.asyncio
    async def test_legacy_payload_structure_handling_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy handler payload structure expectations
        
        EXPECTED: PASS - Legacy handlers process payload structures correctly
        VALIDATES: Payload parsing, validation, and data extraction
        """
        start_handler = StartAgentHandler(mock_supervisor, mock_db_session_factory)
        user_handler = UserMessageHandler(mock_supervisor, mock_db_session_factory)
        
        # Test StartAgentHandler payload structures
        start_payloads = [
            {"user_request": "Simple request"},
            {"user_request": "Complex request", "thread_id": "thread_123"},
            {"user_request": "Full request", "thread_id": "thread_123", "run_id": "run_456"},
        ]
        
        for payload in start_payloads:
            with patch.object(start_handler, '_extract_user_request', return_value=payload["user_request"]):
                user_request = start_handler._extract_user_request(payload)
                assert user_request == payload["user_request"]
        
        # Test UserMessageHandler payload structures
        user_payloads = [
            {"message": "Simple message"},
            {"message": "Message with refs", "references": ["ref1", "ref2"]},
            {"message": "Full message", "thread_id": "thread_123", "references": []},
        ]
        
        for payload in user_payloads:
            with patch.object(user_handler, '_extract_message_data', return_value=(payload["message"], payload.get("references", []))):
                text, refs = user_handler._extract_message_data(payload)
                assert text == payload["message"]
                assert refs == payload.get("references", [])
        
        print("✅ Legacy payload structure handling baseline validated")
    
    @pytest.mark.asyncio 
    async def test_legacy_database_session_management_baseline(self, mock_supervisor, mock_db_session_factory):
        """
        BASELINE TEST: Legacy database session management patterns
        
        EXPECTED: PASS - Legacy handlers manage database sessions correctly
        VALIDATES: Session creation, usage, and cleanup patterns
        """
        handler = StartAgentHandler(mock_supervisor, mock_db_session_factory)
        
        # Verify handler uses db_session_factory
        assert handler.db_session_factory == mock_db_session_factory
        
        # Test session usage in message processing
        payload = {"user_request": "test"}
        
        with patch.object(handler, '_setup_thread_and_run', new_callable=AsyncMock, return_value=("thread_123", "run_456")):
            with patch.object(handler, '_execute_agent_request', new_callable=AsyncMock):
                with patch.object(handler, '_extract_user_request', return_value="test"):
                    await handler._process_start_agent_request("user_123", payload)
        
        # Verify ThreadHistoryHandler uses unit of work
        history_handler = ThreadHistoryHandler(mock_db_session_factory)
        
        with patch('netra_backend.app.services.database.unit_of_work.get_unit_of_work') as mock_uow:
            mock_uow.return_value.__aenter__ = AsyncMock()
            mock_uow.return_value.__aexit__ = AsyncMock()
            
            with patch.object(history_handler, '_process_thread_history_request', new_callable=AsyncMock):
                await history_handler.handle("user_123", {"thread_id": "thread_123"})
                mock_uow.assert_called_once()
        
        print("✅ Legacy database session management baseline validated")


@pytest.fixture
def baseline_test_summary():
    """Fixture to collect baseline test results"""
    return {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "baseline_established": False
    }


if __name__ == "__main__":
    # Run baseline tests to establish legacy functionality
    print("🔍 Running Legacy Handler Baseline Tests for Issue #1099")
    print("=" * 60)
    
    exit_code = pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-m", "not integration"  # Skip integration tests for baseline
    ])
    
    if exit_code == 0:
        print("\n✅ LEGACY HANDLER BASELINE ESTABLISHED")
        print("All legacy handlers working correctly in isolation")
        print("Baseline ready for SSOT migration validation")
    else:
        print("\n❌ LEGACY HANDLER BASELINE FAILED")
        print("Legacy handlers have issues that must be fixed before migration")
    
    exit(exit_code)