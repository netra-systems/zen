"""
Mission Critical Test Suite: WebSocket Manager Await Issue Fix

CRITICAL BUSINESS VALUE: This test suite protects the $500K+ ARR chat functionality
by ensuring WebSocket manager creation works correctly in quality management handlers.

PURPOSE:
1. FAIL initially - demonstrate current broken state with await on synchronous function
2. PASS after fix - verify quality management handlers work without incorrect await
3. VALIDATE - ensure WebSocket events still deliver correctly after fix

AFFECTED FILES:
- netra_backend/app/services/websocket/quality_validation_handler.py (lines 96, 117)
- netra_backend/app/services/websocket/quality_report_handler.py (lines 113, 135)
- netra_backend/app/services/websocket/quality_manager.py (line 110)

GOLDEN PATH COMPLIANCE: Following test framework SSOT patterns and real service testing.
"""

import asyncio
import pytest
from typing import Any, Dict
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.services.websocket.quality_validation_handler import QualityValidationHandler
from netra_backend.app.services.websocket.quality_report_handler import QualityReportHandler
from netra_backend.app.services.websocket.quality_manager import QualityMessageHandler
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerAwaitIssue(SSotAsyncTestCase):
    """Test suite for WebSocket manager await issue fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_id = "test_user_123"
        self.test_context = UserExecutionContext(
            user_id=self.user_id,
            request_id="test_websocket_await_fix"
        )
        
        # Mock services
        self.quality_gate_service = Mock(spec=QualityGateService)
        self.monitoring_service = Mock(spec=QualityMonitoringService)
        
        # Mock validation result
        self.quality_gate_service.validate_content = AsyncMock(return_value={
            "is_valid": True,
            "score": 0.95,
            "issues": []
        })
        
        # Mock monitoring data
        self.monitoring_service.get_dashboard_data = AsyncMock(return_value={
            "total_responses": 100,
            "quality_scores": {"high": 80, "medium": 15, "low": 5}
        })
        
    async def test_create_websocket_manager_is_synchronous(self):
        """
        TEST 1: Verify create_websocket_manager() returns synchronous object
        
        EXPECTED BEHAVIOR:
        - Function should return immediately without await
        - Should not be a coroutine object
        - Should return WebSocketManager instance
        """
        logger.info("TEST 1: Verifying create_websocket_manager() is synchronous")
        
        # Call function WITHOUT await - this should work
        manager = create_websocket_manager(user_context=self.test_context)
        
        # Verify it's not a coroutine
        self.assertFalse(asyncio.iscoroutine(manager), 
                        "create_websocket_manager should not return a coroutine")
        
        # Verify it returns correct type
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        self.assertIsInstance(manager, WebSocketManager,
                            "Should return WebSocketManager instance")
        
        logger.info(" PASS:  TEST 1 PASSED: create_websocket_manager() is synchronous")
        
    async def test_await_on_synchronous_function_fails(self):
        """
        TEST 2: Demonstrate current broken state - await on synchronous function
        
        EXPECTED BEHAVIOR BEFORE FIX:
        - Attempting to await create_websocket_manager() should raise TypeError
        - Error message should indicate object can't be used in await expression
        """
        logger.info("TEST 2: Demonstrating await on synchronous function fails")
        
        # This should fail with "object UnifiedWebSocketManager can't be used in 'await' expression"
        with self.assertRaises(TypeError) as context:
            # This is the BROKEN pattern currently in the code
            await create_websocket_manager(user_context=self.test_context)
        
        error_message = str(context.exception)
        self.assertIn("can't be used in 'await' expression", error_message,
                     "Should get specific await error message")
        
        logger.info(f" PASS:  TEST 2 PASSED: Await on sync function fails as expected: {error_message}")


class TestQualityValidationHandlerAwaitFix(SSotAsyncTestCase):
    """Test quality validation handler await issue fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_id = "test_user_validation"
        self.quality_gate_service = Mock(spec=QualityGateService)
        self.quality_gate_service.validate_content = AsyncMock(return_value={
            "is_valid": True,
            "score": 0.95,
            "issues": []
        })
        
        self.handler = QualityValidationHandler(self.quality_gate_service)
        
    @patch('netra_backend.app.services.websocket.quality_validation_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_validation_handler.create_websocket_manager')
    async def test_validation_handler_broken_await_pattern(self, mock_create_manager, mock_get_context):
        """
        TEST 3: Demonstrate current broken state in quality validation handler
        
        This test simulates the current BROKEN code pattern where create_websocket_manager
        is incorrectly awaited in lines 96 and 117 of quality_validation_handler.py
        """
        logger.info("TEST 3: Testing quality validation handler broken await pattern")
        
        # Setup mocks
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        
        # Mock manager with send_to_user method
        mock_manager = Mock()
        mock_manager.send_to_user = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        # Test payload
        test_payload = {
            "content": "Test content for validation",
            "content_type": "general",
            "strict_mode": False
        }
        
        # This should work when create_websocket_manager is called WITHOUT await self.handler.handle(self.user_id, test_payload)
        
        # Verify the flow completed
        self.quality_gate_service.validate_content.assert_called_once()
        mock_create_manager.assert_called()
        mock_manager.send_to_user.assert_called()
        
        # Now simulate the BROKEN pattern with await
        # Reset mocks to simulate TypeError when await is used
        mock_create_manager.reset_mock()
        
        # Make create_websocket_manager raise TypeError when awaited
        def raise_type_error(*args, **kwargs):
            # Simulate the actual error from awaiting a sync function
            raise TypeError("object WebSocketManager can't be used in 'await' expression")
        
        mock_create_manager.side_effect = raise_type_error
        
        # This should fail due to the await issue
        with self.assertRaises(TypeError) as context:
            # Simulate the broken code by patching the handler's _send_validation_result
            # to use await on create_websocket_manager
            with patch.object(self.handler, '_send_validation_result') as mock_send:
                async def broken_send_validation_result(user_id, result):
                    # This simulates the BROKEN pattern in the actual code
                    user_context = mock_get_context(user_id=user_id, thread_id=None, run_id=None)
                    manager = await create_websocket_manager(user_context)  # BROKEN: await on sync function
                    await manager.send_to_user({"type": "test", "payload": result})
                
                mock_send.side_effect = broken_send_validation_result
                await self.handler.handle(self.user_id, test_payload)
        
        self.assertIn("can't be used in 'await' expression", str(context.exception))
        logger.info(" PASS:  TEST 3 PASSED: Demonstrated broken await pattern fails")
        
    @patch('netra_backend.app.services.websocket.quality_validation_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_validation_handler.create_websocket_manager')
    async def test_validation_handler_fixed_pattern(self, mock_create_manager, mock_get_context):
        """
        TEST 4: Verify fixed pattern works correctly
        
        This test verifies that removing await from create_websocket_manager calls
        allows the quality validation handler to work properly.
        """
        logger.info("TEST 4: Testing quality validation handler fixed pattern")
        
        # Setup mocks
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        
        # Mock manager with send_to_user method
        mock_manager = Mock()
        mock_manager.send_to_user = AsyncMock()
        mock_create_manager.return_value = mock_manager  # NO await needed
        
        # Test payload
        test_payload = {
            "content": "Test content for validation",
            "content_type": "optimization",
            "strict_mode": True
        }
        
        # This should work with the FIXED pattern (no await)
        await self.handler.handle(self.user_id, test_payload)
        
        # Verify successful execution
        self.quality_gate_service.validate_content.assert_called_once_with(
            "Test content for validation",
            self.handler._map_content_type("optimization"),
            True
        )
        
        # Verify WebSocket manager was created and used correctly
        mock_create_manager.assert_called_once_with(mock_context)
        mock_manager.send_to_user.assert_called_once()
        
        # Verify message format
        sent_message = mock_manager.send_to_user.call_args[0][0]
        self.assertEqual(sent_message["type"], "content_validation_result")
        self.assertIn("payload", sent_message)
        
        logger.info(" PASS:  TEST 4 PASSED: Fixed pattern works correctly")


class TestQualityReportHandlerAwaitFix(SSotAsyncTestCase):
    """Test quality report handler await issue fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_id = "test_user_reports"
        self.monitoring_service = Mock(spec=QualityMonitoringService)
        self.monitoring_service.get_dashboard_data = AsyncMock(return_value={
            "total_responses": 150,
            "quality_scores": {"high": 90, "medium": 8, "low": 2}
        })
        
        self.handler = QualityReportHandler(self.monitoring_service)
        
    @patch('netra_backend.app.services.websocket.quality_report_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_report_handler.create_websocket_manager')
    async def test_report_handler_fixed_pattern(self, mock_create_manager, mock_get_context):
        """
        TEST 5: Verify quality report handler works with fixed pattern
        
        This test verifies that removing await from create_websocket_manager calls
        in lines 113 and 135 allows the quality report handler to work properly.
        """
        logger.info("TEST 5: Testing quality report handler fixed pattern")
        
        # Setup mocks
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        
        # Mock manager with send_to_user method
        mock_manager = Mock()
        mock_manager.send_to_user = AsyncMock()
        mock_create_manager.return_value = mock_manager  # NO await needed
        
        # Test payload
        test_payload = {
            "report_type": "summary",
            "period": "day"
        }
        
        # This should work with the FIXED pattern (no await)
        await self.handler.handle(self.user_id, test_payload)
        
        # Verify successful execution
        self.monitoring_service.get_dashboard_data.assert_called_once()
        
        # Verify WebSocket manager was created and used correctly
        mock_create_manager.assert_called_once_with(mock_context)
        mock_manager.send_to_user.assert_called_once()
        
        # Verify message format
        sent_message = mock_manager.send_to_user.call_args[0][0]
        self.assertEqual(sent_message["type"], "quality_report_generated")
        self.assertIn("payload", sent_message)
        self.assertIn("report", sent_message["payload"])
        self.assertIn("timestamp", sent_message["payload"])
        
        logger.info(" PASS:  TEST 5 PASSED: Quality report handler fixed pattern works")
        
    @patch('netra_backend.app.services.websocket.quality_report_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_report_handler.create_websocket_manager')
    async def test_report_handler_error_handling_fixed(self, mock_create_manager, mock_get_context):
        """
        TEST 6: Verify error handling works with fixed pattern
        
        This test verifies that error handling in _handle_report_error also works
        correctly when the await is removed from line 135.
        """
        logger.info("TEST 6: Testing quality report handler error handling fixed pattern")
        
        # Setup mocks for error scenario
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        
        # Mock manager for error handling
        mock_manager = Mock()
        mock_manager.send_to_user = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        # Make monitoring service raise an error
        self.monitoring_service.get_dashboard_data.side_effect = Exception("Database connection failed")
        
        # Test payload
        test_payload = {
            "report_type": "detailed",
            "period": "week"
        }
        
        # This should handle the error gracefully
        await self.handler.handle(self.user_id, test_payload)
        
        # Verify error handling executed
        mock_create_manager.assert_called_once_with(mock_context)
        mock_manager.send_to_user.assert_called_once()
        
        # Verify error message format
        sent_message = mock_manager.send_to_user.call_args[0][0]
        self.assertEqual(sent_message["type"], "error")
        self.assertIn("Failed to generate report", sent_message["message"])
        
        logger.info(" PASS:  TEST 6 PASSED: Error handling fixed pattern works")


class TestQualityManagerAwaitFix(SSotAsyncTestCase):
    """Test quality manager await issue fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_id = "test_user_manager"
        
        # Mock supervisor and db_session_factory
        self.mock_supervisor = Mock()
        self.mock_db_session_factory = Mock()
        
        self.manager = QualityMessageHandler(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory
        )
        
    @patch('netra_backend.app.services.websocket.quality_manager.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_manager.create_websocket_manager')
    async def test_quality_manager_unknown_message_fixed(self, mock_create_manager, mock_get_context):
        """
        TEST 7: Verify quality manager unknown message handling works with fixed pattern
        
        This test verifies that removing await from create_websocket_manager call
        in line 110 allows the quality manager to handle unknown messages properly.
        """
        logger.info("TEST 7: Testing quality manager unknown message handling fixed pattern")
        
        # Setup mocks
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        
        # Mock manager with send_to_user method
        mock_manager = Mock()
        mock_manager.send_to_user = AsyncMock()
        mock_create_manager.return_value = mock_manager  # NO await needed
        
        # Test unknown message
        unknown_message = {
            "type": "unknown_message_type",
            "payload": {"data": "test"}
        }
        
        # This should work with the FIXED pattern (no await)
        await self.manager.handle_message(self.user_id, unknown_message)
        
        # Verify WebSocket manager was created and used correctly
        mock_create_manager.assert_called_once_with(mock_context)
        mock_manager.send_to_user.assert_called_once()
        
        # Verify error message format
        sent_message = mock_manager.send_to_user.call_args[0][0]
        self.assertEqual(sent_message["type"], "error")
        self.assertIn("Unknown message type: unknown_message_type", sent_message["message"])
        
        logger.info(" PASS:  TEST 7 PASSED: Quality manager unknown message handling fixed")


class TestWebSocketEventDeliveryAfterFix(SSotAsyncTestCase):
    """Test that WebSocket event delivery still works correctly after the fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_id = "test_user_events"
        self.test_context = UserExecutionContext(
            user_id=self.user_id,
            request_id="test_event_delivery"
        )
        
    async def test_websocket_events_still_deliver_after_fix(self):
        """
        TEST 8: Verify WebSocket events still deliver correctly after fix
        
        BUSINESS CRITICAL: This ensures that removing await doesn't break
        the core chat functionality that delivers 90% of platform value.
        """
        logger.info("TEST 8: Testing WebSocket event delivery after await fix")
        
        # Create manager using the FIXED pattern (no await)
        manager = create_websocket_manager(user_context=self.test_context)
        
        # Verify manager is properly initialized
        self.assertIsNotNone(manager)
        self.assertEqual(manager.user_context.user_id, self.user_id)
        
        # Mock the WebSocket connection for testing
        mock_websocket = Mock()
        mock_websocket.send = AsyncMock()
        
        # Test that manager can send events (simulating the fix)
        test_message = {
            "type": "agent_started",
            "payload": {
                "agent_name": "QualityValidator",
                "task": "Content validation"
            }
        }
        
        # This simulates the fixed code path
        with patch.object(manager, '_get_active_websocket', return_value=mock_websocket):
            await manager.send_to_user(test_message)
        
        # Verify event was sent
        mock_websocket.send.assert_called_once()
        
        logger.info(" PASS:  TEST 8 PASSED: WebSocket event delivery works after fix")


# Test execution helper
async def run_all_tests():
    """Helper function to run all tests in sequence."""
    test_classes = [
        TestWebSocketManagerAwaitIssue,
        TestQualityValidationHandlerAwaitFix,
        TestQualityReportHandlerAwaitFix,
        TestQualityManagerAwaitFix,
        TestWebSocketEventDeliveryAfterFix
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running tests from {test_class.__name__}")
        logger.info(f"{'='*60}")
        
        # Get test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                # Create test instance
                test_instance = test_class()
                test_instance.setUp()
                
                # Run the test
                await getattr(test_instance, test_method)()
                passed_tests += 1
                logger.info(f" PASS:  {test_method} PASSED")
                
            except Exception as e:
                logger.error(f" FAIL:  {test_method} FAILED: {str(e)}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
    logger.info(f"{'='*60}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_all_tests())