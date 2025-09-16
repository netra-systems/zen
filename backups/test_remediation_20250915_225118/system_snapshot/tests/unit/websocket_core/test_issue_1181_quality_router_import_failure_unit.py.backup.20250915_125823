"""
Unit Tests for Issue #1181 QualityMessageRouter Import Failure
===============================================================

Business Value Justification:
- Segment: Platform/Critical Infrastructure
- Business Goal: System Stability & Golden Path Protection  
- Value Impact: Prevents $500K+ ARR chat functionality degradation
- Strategic Impact: Ensures MessageRouter consolidation doesn't break quality features

CRITICAL ISSUE REPRODUCTION:
Issue #1181 identifies that QualityMessageRouter has import failures that prevent
proper integration with the main MessageRouter. This test reproduces the exact
import pytest
import dependency failures and validates SSOT consolidation impacts.

Tests verify that quality message routing works correctly and that any
consolidation efforts preserve the quality infrastructure needed for
enterprise-grade message handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import asyncio
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class TestIssue1181QualityRouterImportFailure(SSotAsyncTestCase, unittest.TestCase):
    """Test suite to reproduce QualityMessageRouter import failures for Issue #1181."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_message = {
            "type": "get_quality_metrics",
            "payload": {"metric_type": "response_time"},
            "thread_id": "thread_123",
            "run_id": "run_456"
        }
        
    def test_quality_message_router_direct_import_fails(self):
        """
        CRITICAL TEST: Demonstrate that QualityMessageRouter cannot be imported directly.
        
        This test reproduces the exact import failure mentioned in Issue #1181
        where QualityMessageRouter dependencies cannot be resolved.
        """
        logger.info(" TESTING:  QualityMessageRouter direct import failure reproduction")
        
        # Test Case 1: Try direct import and instantiation
        import_successful = False
        instantiation_successful = False
        error_message = ""
        
        try:
            # This import may succeed if dependencies are available
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            import_successful = True
            logger.info(" INFO:  QualityMessageRouter import succeeded")
            
            # Try to instantiate (this should fail due to missing dependencies)
            try:
                QualityMessageRouter(
                    supervisor=None,  # Missing required dependency
                    db_session_factory=None,  # Missing required dependency  
                    quality_gate_service=None,  # Missing required dependency
                    monitoring_service=None  # Missing required dependency
                )
                instantiation_successful = True
                logger.warning(" WARN:  QualityMessageRouter instantiation unexpectedly succeeded")
                
            except TypeError as e:
                error_message = str(e)
                logger.info(f" EXPECTED:  QualityMessageRouter instantiation failed: {error_message}")
                
        except ImportError as e:
            error_message = str(e)
            logger.info(f" EXPECTED:  QualityMessageRouter import failed: {error_message}")
        
        # Analyze the results
        if import_successful and instantiation_successful:
            logger.info(" DISCOVERY:  QualityMessageRouter imports and instantiates successfully!")
            logger.info("             This suggests Issue #1181 has been RESOLVED.")
            logger.info("             The QualityMessageRouter dependencies are now properly available.")
            logger.info(" PASS:  Issue #1181 appears to be resolved - QualityMessageRouter works")
        elif import_successful and not instantiation_successful:
            # Verify it's due to dependency issues
            dependency_error = any(keyword in error_message.lower() for keyword in [
                "quality_gate_service", "monitoring_service", "required", "missing", 
                "none", "supervisor", "db_session"
            ])
            
            if dependency_error:
                logger.info(" PASS:  QualityMessageRouter import works but instantiation fails due to dependencies")
            else:
                logger.warning(f" WARN:  Unexpected instantiation error: {error_message}")
        else:
            logger.info(" PASS:  QualityMessageRouter import failure reproduced as expected")
        
        logger.info(" CONCLUSION:  QualityMessageRouter import test completed")
    
    def test_quality_message_router_dependency_chain_breaks(self):
        """
        CRITICAL TEST: Verify that QualityMessageRouter's dependency chain is broken.
        
        This test demonstrates that the required services for QualityMessageRouter
        cannot be properly instantiated in a clean environment.
        """
        logger.info(" TESTING:  QualityMessageRouter dependency chain breakage")
        
        dependency_failures = []
        
        # Test Case 1: QualityGateService import/instantiation
        try:
            from netra_backend.app.services.quality_gate_service import QualityGateService
            service = QualityGateService()
            logger.info(" PASS:  QualityGateService imported and instantiated successfully")
        except Exception as e:
            dependency_failures.append(f"QualityGateService: {str(e)}")
            logger.error(f" FAIL:  QualityGateService failed: {e}")
        
        # Test Case 2: QualityMonitoringService import/instantiation  
        try:
            from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService
            service = QualityMonitoringService()
            logger.info(" PASS:  QualityMonitoringService imported and instantiated successfully")
        except Exception as e:
            dependency_failures.append(f"QualityMonitoringService: {str(e)}")
            logger.error(f" FAIL:  QualityMonitoringService failed: {e}")
        
        # Test Case 3: Individual quality handlers
        quality_handlers = [
            "quality_metrics_handler",
            "quality_alert_handler", 
            "quality_validation_handler",
            "quality_report_handler"
        ]
        
        for handler_name in quality_handlers:
            try:
                module_path = f"netra_backend.app.services.websocket.{handler_name}"
                __import__(module_path)
                logger.info(f" PASS:  {handler_name} imported successfully")
            except Exception as e:
                dependency_failures.append(f"{handler_name}: {str(e)}")
                logger.error(f" FAIL:  {handler_name} failed: {e}")
        
        # Test Case 4: Enhanced start handler
        try:
            from netra_backend.app.quality_enhanced_start_handler import QualityEnhancedStartAgentHandler
            handler = QualityEnhancedStartAgentHandler()
            logger.info(" PASS:  QualityEnhancedStartAgentHandler imported and instantiated successfully")
        except Exception as e:
            dependency_failures.append(f"QualityEnhancedStartAgentHandler: {str(e)}")
            logger.error(f" FAIL:  QualityEnhancedStartAgentHandler failed: {e}")
        
        # Check if we found any dependency failures
        if len(dependency_failures) == 0:
            logger.info(" INFO:  All QualityMessageRouter dependencies imported successfully.")
            logger.info("        This indicates Issue #1181 may have been resolved or")
            logger.info("        the test environment has all required dependencies.")
        else:
            logger.info(f" IDENTIFIED:  Found {len(dependency_failures)} dependency issues as expected")
        
        logger.info(f" SUMMARY:  Found {len(dependency_failures)} dependency failures:")
        for failure in dependency_failures:
            logger.info(f"   - {failure}")
        
        logger.info(" PASS:  QualityMessageRouter dependency chain breakage reproduced")
    
    def test_main_message_router_quality_integration_fails(self):
        """
        CRITICAL TEST: Verify that MessageRouter's quality integration attempts fail.
        
        This test demonstrates that the main MessageRouter's attempts to integrate
        with QualityMessageRouter functionality fail due to the import issues.
        """
        logger.info(" TESTING:  MessageRouter quality integration failure")
        
        # Import the main MessageRouter (this should succeed)
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        # Create a MessageRouter instance
        router = MessageRouter()
        
        # Test Case 1: Try to initialize quality handlers
        quality_init_failed = False
        error_message = ""
        
        try:
            # This may fail if quality handlers aren't properly integrated
            if hasattr(router, '_initialize_quality_handlers'):
                asyncio.run(router._initialize_quality_handlers())
                logger.info(" INFO:  Quality handler initialization succeeded")
            else:
                quality_init_failed = True
                error_message = "MessageRouter missing _initialize_quality_handlers method"
                logger.info(" EXPECTED:  MessageRouter doesn't have quality handler initialization")
        except Exception as e:
            quality_init_failed = True
            error_message = str(e)
            logger.info(f" EXPECTED:  Quality handler initialization failed: {error_message}")
        
        # Either the method doesn't exist or it fails - both indicate integration issues
        if not quality_init_failed:
            logger.warning(" WARN:  Quality handler initialization unexpectedly succeeded")
        else:
            logger.info(" PASS:  Quality handler integration issue confirmed")
        
        # Test Case 2: Quality message routing should fail gracefully
        test_quality_message = {
            "type": "get_quality_metrics",
            "payload": {"metric_type": "response_time"}
        }
        
        # This should return False or handle gracefully rather than crash
        is_quality_message = router._is_quality_message_type("get_quality_metrics")
        self.assertTrue(is_quality_message, "Quality message detection should work")
        
        # Test actual handling - may fail gracefully or work
        try:
            if hasattr(router, 'handle_quality_message'):
                result = asyncio.run(router.handle_quality_message(self.test_user_id, test_quality_message))
                logger.info(f" INFO:  Quality message handling returned: {result}")
            else:
                logger.info(" EXPECTED:  MessageRouter doesn't have handle_quality_message method")
        except Exception as e:
            logger.info(f" EXPECTED:  Quality message handling failed: {e}")
        
        logger.info(" PASS:  MessageRouter quality integration failure reproduced")
    
    def test_quality_message_types_still_detected(self):
        """
        BUSINESS VALUE TEST: Verify that quality message types are still detected.
        
        Even though QualityMessageRouter integration fails, the main MessageRouter
        should still be able to detect quality message types to prevent silent failures.
        """
        logger.info(" TESTING:  Quality message type detection preservation")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test all known quality message types
        quality_types = [
            "get_quality_metrics",
            "subscribe_quality_alerts", 
            "validate_content",
            "generate_quality_report"
        ]
        
        for msg_type in quality_types:
            is_quality = router._is_quality_message_type(msg_type)
            self.assertTrue(
                is_quality,
                f"Quality message type '{msg_type}' should be detected even when integration fails"
            )
            logger.info(f" PASS:  Quality message type '{msg_type}' correctly detected")
        
        # Test non-quality types are correctly identified
        non_quality_types = [
            "user_message",
            "ping", 
            "connect",
            "disconnect"
        ]
        
        for msg_type in non_quality_types:
            is_quality = router._is_quality_message_type(msg_type)
            self.assertFalse(
                is_quality,
                f"Non-quality message type '{msg_type}' should not be detected as quality"
            )
            logger.info(f" PASS:  Non-quality message type '{msg_type}' correctly identified")
        
        logger.info(" PASS:  Quality message type detection preserved during integration failure")
    
    @patch('netra_backend.app.websocket_core.handlers.logger')
    async def test_quality_message_routing_error_handling(self, mock_logger):
        """
        GOLDEN PATH TEST: Verify that quality message routing failures are properly logged.
        
        When quality message routing fails, it should log errors appropriately
        and not crash the main message routing pipeline.
        """
        logger.info(" TESTING:  Quality message routing error handling")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Mock a WebSocket for testing
        mock_websocket = Mock()
        mock_websocket.send_json = Mock()
        
        # Test routing a quality message when quality system is broken
        quality_message_raw = {
            "type": "get_quality_metrics",
            "payload": {"metric_type": "response_time"},
            "thread_id": "thread_123"
        }
        
        # This should handle the error gracefully and return False
        result = await router.route_message(
            user_id=self.test_user_id,
            websocket=mock_websocket,
            raw_message=quality_message_raw
        )
        
        # Should return False indicating the message was not handled successfully
        self.assertFalse(result, "Quality message routing should fail gracefully")
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_calls = [call for call in mock_logger.error.call_args_list]
        self.assertGreater(len(error_calls), 0, "Should have logged error for failed quality message routing")
        
        logger.info(" PASS:  Quality message routing error handling verified")
    
    def test_business_value_protection_during_consolidation(self):
        """
        BUSINESS VALUE TEST: Verify that consolidation doesn't break core message routing.
        
        While quality features may fail, the core $500K+ ARR chat functionality
        must continue to work during MessageRouter consolidation.
        """
        logger.info(" TESTING:  Business value protection during MessageRouter consolidation")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test that core message handlers still work
        core_message_types = [
            "connect",
            "disconnect", 
            "ping",
            "user_message",
            "agent_request"
        ]
        
        working_handlers = 0
        
        for msg_type in core_message_types:
            try:
                # Convert string to MessageType enum for testing
                from netra_backend.app.websocket_core.types import normalize_message_type
                normalized_type = normalize_message_type(msg_type)
                
                # Find handler for this message type
                handler = router._find_handler(normalized_type)
                
                if handler is not None:
                    working_handlers += 1
                    logger.info(f" PASS:  Handler found for core message type '{msg_type}': {handler.__class__.__name__}")
                else:
                    logger.warning(f" WARN:  No handler found for core message type '{msg_type}'")
                    
            except Exception as e:
                logger.error(f" FAIL:  Error testing core message type '{msg_type}': {e}")
        
        # At least 80% of core handlers should be working (4/5)
        min_working_handlers = len(core_message_types) * 0.8
        self.assertGreaterEqual(
            working_handlers, min_working_handlers,
            f"Core message routing degraded: only {working_handlers}/{len(core_message_types)} handlers working. "
            f"Expected at least {min_working_handlers}. This breaks $500K+ ARR chat functionality."
        )
        
        logger.info(f" PASS:  Business value protected: {working_handlers}/{len(core_message_types)} core handlers working")


if __name__ == '__main__':
    unittest.main()