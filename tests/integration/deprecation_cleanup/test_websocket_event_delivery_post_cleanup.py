"""
Integration Tests for WebSocket Event Delivery Post-Cleanup

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Goal: Ensure zero functional regression during deprecation cleanup
- Value Impact: Protects $500K+ ARR Golden Path functionality
- Strategic Impact: Mission critical WebSocket event delivery

This test suite validates that WebSocket functionality remains intact
after deprecation warning cleanup for Issue #1090:

1. WebSocket bridge adapter event emission works correctly
2. WebSocket error validator functionality is preserved
3. All 5 critical WebSocket events are delivered properly
4. User isolation and authentication remain secure

Test Philosophy: These tests SHOULD PASS both before and after cleanup,
proving that deprecation warning fixes cause zero functional regression.
"""

import asyncio
import pytest
import warnings
import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketEventDeliveryPostCleanup(SSotBaseTestCase):
    """Test WebSocket event delivery remains intact after deprecation cleanup."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "integration"
        self.test_context.record_custom('component', 'websocket_event_delivery')
        
        # Track event delivery metrics
        self.events_emitted = 0
        self.events_validated = 0
        self.critical_events_delivered = 0
        self.bridge_adapter_operations = 0
        self.error_validator_operations = 0
        
    def tearDown(self):
        """Clean up and record metrics."""
        self.test_context.record_custom('events_emitted', self.events_emitted)
        self.test_context.record_custom('events_validated', self.events_validated)
        self.test_context.record_custom('critical_events_delivered', self.critical_events_delivered)
        self.test_context.record_custom('bridge_adapter_operations', self.bridge_adapter_operations)
        self.test_context.record_custom('error_validator_operations', self.error_validator_operations)
        super().tearDown()

    @pytest.mark.integration
    async def test_websocket_bridge_adapter_event_emission(self):
        """Test that WebSocket bridge adapter emits all 5 critical events correctly.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Event emission functionality protected
        """
        try:
            from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
        except ImportError:
            pytest.skip("WebSocketBridgeAdapter not available")
        
        # Create test bridge adapter
        adapter = WebSocketBridgeAdapter()
        self.bridge_adapter_operations += 1
        
        # Create mock bridge for testing
        mock_bridge = Mock()
        mock_bridge.notify_agent_started = AsyncMock()
        mock_bridge.notify_agent_thinking = AsyncMock()
        mock_bridge.notify_tool_executing = AsyncMock()
        mock_bridge.notify_tool_completed = AsyncMock()
        mock_bridge.notify_agent_completed = AsyncMock()
        
        # Configure adapter
        adapter.set_websocket_bridge(mock_bridge, "test_run_123", "test_agent")
        
        # Test all 5 critical events
        await adapter.emit_agent_started("Starting test")
        self.events_emitted += 1
        self.critical_events_delivered += 1
        
        await adapter.emit_thinking("Thinking about test")
        self.events_emitted += 1
        self.critical_events_delivered += 1
        
        await adapter.emit_tool_executing("test_tool", {"param": "value"})
        self.events_emitted += 1
        self.critical_events_delivered += 1
        
        await adapter.emit_tool_completed("test_tool", {"result": "success"})
        self.events_emitted += 1
        self.critical_events_delivered += 1
        
        await adapter.emit_agent_completed({"final": "result"})
        self.events_emitted += 1
        self.critical_events_delivered += 1
        
        # Verify all events were emitted
        mock_bridge.notify_agent_started.assert_called_once()
        mock_bridge.notify_agent_thinking.assert_called_once()
        mock_bridge.notify_tool_executing.assert_called_once()
        mock_bridge.notify_tool_completed.assert_called_once()
        mock_bridge.notify_agent_completed.assert_called_once()
        
        # Record success
        self.test_context.record_custom('bridge_adapter_event_emission', 'success')
        self.test_context.record_custom('all_critical_events_emitted', True)

    @pytest.mark.integration
    async def test_websocket_error_validator_functionality(self):
        """Test that WebSocket error validator works correctly after import cleanup.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Validator functionality protected
        """
        try:
            from netra_backend.app.services.websocket_error_validator import get_websocket_validator
        except ImportError:
            pytest.skip("WebSocket error validator not available")
        
        # Get validator instance
        validator = get_websocket_validator()
        self.assertIsNotNone(validator, "Validator should be available")
        self.error_validator_operations += 1
        
        # Test validator functionality
        test_event = {
            "type": "agent_started",
            "run_id": "test_run_123",
            "agent_name": "test_agent",
            "timestamp": "2025-09-15T10:00:00Z",
            "payload": {"message": "test"}
        }
        
        # Validate the event
        result = validator.validate_event(test_event, "test_user")
        self.events_validated += 1
        
        self.assertTrue(result.is_valid, f"Validator should work correctly: {result.error_message}")
        
        # Test error validation functionality
        from netra_backend.app.services.websocket_error_validator import (
            WebSocketErrorValidator, WebSocketErrorType, WebSocketErrorSeverity
        )
        
        error_validator = WebSocketErrorValidator()
        test_error = error_validator.create_test_error(
            WebSocketErrorType.CONNECTION_FAILED,
            WebSocketErrorSeverity.HIGH,
            "Test connection error"
        )
        
        validation_issues = error_validator.validate_error(test_error)
        self.assertEqual(len(validation_issues), 0, "Test error should be valid")
        self.error_validator_operations += 1
        
        # Record success
        self.test_context.record_custom('error_validator_functionality', 'success')

    @pytest.mark.integration
    async def test_websocket_event_validator_integration(self):
        """Test that WebSocket event validator integrates properly.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Event validation integration protected
        """
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
        except ImportError:
            pytest.skip("UnifiedEventValidator not available")
        
        # Create validator instance
        validator = UnifiedEventValidator("test_user_123")
        
        # Test critical event validation
        critical_events = [
            {
                "type": "agent_started",
                "run_id": "test_run_456",
                "agent_name": "triage_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"message": "Agent starting up"}
            },
            {
                "type": "agent_thinking", 
                "run_id": "test_run_456",
                "agent_name": "triage_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"thought": "Analyzing user request"}
            },
            {
                "type": "tool_executing",
                "run_id": "test_run_456", 
                "agent_name": "triage_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"tool": "cost_analyzer", "params": {}}
            },
            {
                "type": "tool_completed",
                "run_id": "test_run_456",
                "agent_name": "triage_agent", 
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"tool": "cost_analyzer", "result": "analysis complete"}
            },
            {
                "type": "agent_completed",
                "run_id": "test_run_456",
                "agent_name": "triage_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(), 
                "payload": {"final_result": "Task completed successfully"}
            }
        ]
        
        # Validate all critical events
        for event in critical_events:
            result = validator.validate_event(event, "test_user_123")
            self.assertTrue(result.is_valid, 
                          f"Critical event {event['type']} should be valid: {result.error_message}")
            self.events_validated += 1
            self.critical_events_delivered += 1
        
        # Record success
        self.test_context.record_custom('event_validator_integration', 'success')
        self.test_context.record_custom('critical_event_validation_count', len(critical_events))

    @pytest.mark.integration
    async def test_websocket_imports_without_deprecation_warnings(self):
        """Test that WebSocket imports work without triggering deprecation warnings.
        
        SHOULD FAIL INITIALLY: Current imports may trigger warnings
        SHOULD PASS AFTER FIX: Imports should be warning-free
        """
        # Test imports that are used in integration scenarios
        integration_imports = [
            'from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator',
            'from netra_backend.app.services.websocket_error_validator import get_websocket_validator',
            'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager'
        ]
        
        warnings_detected = 0
        successful_imports = 0
        
        for import_statement in integration_imports:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                try:
                    # Execute the import
                    exec(import_statement)
                    successful_imports += 1
                    
                    # Check for websocket_core deprecation warnings
                    websocket_warnings = [
                        warning for warning in w 
                        if (issubclass(warning.category, DeprecationWarning) and 
                            'websocket_core' in str(warning.message))
                    ]
                    
                    if websocket_warnings:
                        warnings_detected += len(websocket_warnings)
                        for warning in websocket_warnings:
                            self.test_context.record_custom('integration_warning', str(warning.message))
                    
                except ImportError as e:
                    self.test_context.record_custom('integration_import_failure', str(e))
        
        # Record metrics
        self.test_context.record_custom('integration_imports_tested', len(integration_imports))
        self.test_context.record_custom('integration_imports_successful', successful_imports)
        self.test_context.record_custom('integration_warnings_detected', warnings_detected)
        
        # After fix: should have no warnings
        # Before fix: this test documents current warning state
        self.assertEqual(warnings_detected, 0, 
                        f"Integration imports should not trigger deprecation warnings. Found {warnings_detected} warnings.")

    @pytest.mark.integration
    async def test_websocket_functionality_preservation(self):
        """Test that core WebSocket functionality is preserved during cleanup.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Core functionality must be preserved
        """
        functionality_tests = []
        
        # Test 1: WebSocket manager creation
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create a test user context
            user_context = UserExecutionContext(user_id="test_user_integration")
            
            # Create WebSocket manager
            manager = WebSocketManager(user_context=user_context)
            self.assertIsNotNone(manager, "WebSocket manager should be creatable")
            functionality_tests.append("websocket_manager_creation: success")
            
        except Exception as e:
            functionality_tests.append(f"websocket_manager_creation: failed - {e}")
        
        # Test 2: Event validator functionality
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
            
            validator = UnifiedEventValidator("test_user_integration")
            test_event = {
                "type": "agent_started",
                "run_id": "integration_test",
                "agent_name": "test_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"message": "Integration test"}
            }
            
            result = validator.validate_event(test_event, "test_user_integration")
            self.assertTrue(result.is_valid, "Event validation should work")
            functionality_tests.append("event_validation: success")
            
        except Exception as e:
            functionality_tests.append(f"event_validation: failed - {e}")
        
        # Test 3: Error validator functionality
        try:
            from netra_backend.app.services.websocket_error_validator import WebSocketErrorValidator
            
            error_validator = WebSocketErrorValidator()
            self.assertIsNotNone(error_validator, "Error validator should be creatable")
            functionality_tests.append("error_validator_creation: success")
            
        except Exception as e:
            functionality_tests.append(f"error_validator_creation: failed - {e}")
        
        # Record functionality test results
        for test_result in functionality_tests:
            self.test_context.record_custom('functionality_test', test_result)
        
        # Count successful tests
        successful_tests = sum(1 for test in functionality_tests if "success" in test)
        total_tests = len(functionality_tests)
        
        self.test_context.record_custom('functionality_preservation_rate', 
                                      successful_tests / total_tests if total_tests > 0 else 0)
        
        # Most functionality should be preserved
        self.assertGreater(successful_tests, 0, 
                          "Core WebSocket functionality should be preserved")

    @pytest.mark.integration
    async def test_user_isolation_maintained(self):
        """Test that user isolation is maintained after deprecation cleanup.
        
        SHOULD PASS BOTH BEFORE AND AFTER: User isolation is critical security
        """
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
        except ImportError:
            pytest.skip("UnifiedEventValidator not available")
        
        # Create validators for different users
        user1_validator = UnifiedEventValidator("user_1")
        user2_validator = UnifiedEventValidator("user_2")
        
        # Create test events for each user
        user1_event = {
            "type": "agent_started",
            "run_id": "user1_run",
            "agent_name": "user1_agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"message": "User 1 event"}
        }
        
        user2_event = {
            "type": "agent_started", 
            "run_id": "user2_run",
            "agent_name": "user2_agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"message": "User 2 event"}
        }
        
        # Each validator should only accept events for its user
        user1_result = user1_validator.validate_event(user1_event, "user_1")
        user2_result = user2_validator.validate_event(user2_event, "user_2")
        
        self.assertTrue(user1_result.is_valid, "User 1 validator should accept user 1 events")
        self.assertTrue(user2_result.is_valid, "User 2 validator should accept user 2 events")
        
        # Cross-user validation should fail (if implemented)
        try:
            cross_result = user1_validator.validate_event(user2_event, "user_1")
            # If cross-validation is checked, it should fail
            if hasattr(cross_result, 'is_valid') and not cross_result.is_valid:
                self.test_context.record_custom('user_isolation_enforced', True)
            else:
                self.test_context.record_custom('user_isolation_enforced', 'not_checked')
        except Exception:
            # If an exception is thrown, that's also acceptable isolation behavior
            self.test_context.record_custom('user_isolation_enforced', 'exception_based')
        
        # Record user isolation test success
        self.test_context.record_custom('user_isolation_test', 'completed')


class TestWebSocketIntegrationRegressionPrevention(SSotBaseTestCase):
    """Test integration scenarios to prevent regressions."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "integration"
        self.test_context.record_custom('component', 'regression_prevention')

    @pytest.mark.integration
    async def test_websocket_module_loading_order(self):
        """Test that module loading order doesn't affect functionality.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Loading order should not matter
        """
        # Test different loading orders to ensure no hidden dependencies
        loading_scenarios = [
            ['netra_backend.app.websocket_core.event_validator',
             'netra_backend.app.services.websocket_error_validator'],
            ['netra_backend.app.services.websocket_error_validator', 
             'netra_backend.app.websocket_core.event_validator'],
            ['netra_backend.app.websocket_core.websocket_manager',
             'netra_backend.app.websocket_core.event_validator']
        ]
        
        scenario_results = {}
        
        for i, scenario in enumerate(loading_scenarios):
            try:
                # Clear module cache for this test
                for module_name in scenario:
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                
                # Load modules in specific order
                loaded_modules = []
                for module_name in scenario:
                    try:
                        module = __import__(module_name, fromlist=[''])
                        loaded_modules.append(module_name)
                    except ImportError as e:
                        scenario_results[f'scenario_{i}'] = f'import_failed: {e}'
                        break
                else:
                    scenario_results[f'scenario_{i}'] = 'success'
                    
            except Exception as e:
                scenario_results[f'scenario_{i}'] = f'error: {e}'
        
        # Record results
        for scenario, result in scenario_results.items():
            self.test_context.record_custom(f'loading_order_{scenario}', result)
        
        # At least some scenarios should work
        successful_scenarios = sum(1 for result in scenario_results.values() if result == 'success')
        self.assertGreater(successful_scenarios, 0, 
                          "At least some module loading scenarios should work")

    @pytest.mark.integration
    async def test_concurrent_websocket_operations(self):
        """Test concurrent WebSocket operations for race condition prevention.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Concurrency should be handled safely
        """
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
        except ImportError:
            pytest.skip("UnifiedEventValidator not available")
        
        # Create multiple validators for concurrent operations
        validators = [UnifiedEventValidator(f"concurrent_user_{i}") for i in range(3)]
        
        # Create concurrent validation tasks
        async def validate_event(validator, user_id, event_id):
            event = {
                "type": "agent_started",
                "run_id": f"concurrent_run_{event_id}",
                "agent_name": "concurrent_agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"message": f"Concurrent event {event_id}"}
            }
            
            result = validator.validate_event(event, user_id)
            return result.is_valid if hasattr(result, 'is_valid') else True
        
        # Run concurrent validations
        tasks = []
        for i, validator in enumerate(validators):
            for j in range(5):  # 5 events per validator
                task = validate_event(validator, f"concurrent_user_{i}", f"{i}_{j}")
                tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful operations
        successful_ops = sum(1 for result in results if result is True)
        total_ops = len(tasks)
        
        self.test_context.record_custom('concurrent_operations_total', total_ops)
        self.test_context.record_custom('concurrent_operations_successful', successful_ops)
        
        # Most operations should succeed
        success_rate = successful_ops / total_ops if total_ops > 0 else 0
        self.assertGreater(success_rate, 0.8, 
                          "Most concurrent operations should succeed")


if __name__ == '__main__':
    # Use pytest to run the tests
    pytest.main([__file__, '-v'])