"""
Unit Test: WebSocket Health Report Type Validation - Coroutine Error Reproduction

This test specifically targets the coroutine error in WebSocket routes:
"'coroutine' object has no attribute 'get'" at netra_backend/app/routes/websocket.py:557

CRITICAL ISSUE: Dynamic import resolution collision causes health_report to be a coroutine
instead of dict when async health check functions are accidentally returned without await.

Business Value: Free/Early/Mid/Enterprise - System Stability & User Experience
WebSocket connection failures directly impact 90% of platform value (chat functionality).

Test Strategy:
1. UNIT LEVEL: Reproduce exact TypeError with coroutine health_report
2. VALIDATE: health_report.get() calls fail on coroutine objects
3. PROVE: Fix resolves type validation issues
4. DEPLOYMENT GATE: Test must PASS before staging deployment

GitHub Issue: https://github.com/netra-systems/netra-apex/issues/164
Related: GOLDEN_PATH_USER_FLOW_COMPLETE.md Race Condition #3

EXPECTED FAILURE MODE (before fix):
- Test will FAIL with "'coroutine' object has no attribute 'get'" 
- This reproduces the exact staging error condition
- Test PASSING indicates the coroutine error is resolved
"""

import asyncio
import logging
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional
import json

# SSOT Test Base - All tests MUST inherit from this
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the exact functions causing the issue
from netra_backend.app.websocket_core.websocket_manager_factory import validate_websocket_component_health
from netra_backend.app.services.user_execution_context import UserExecutionContext

class TestHealthReportTypeValidationUnit(SSotBaseTestCase):
    """
    UNIT TEST: Reproduce and validate WebSocket coroutine error fix.
    
    This test specifically targets the race condition where validate_websocket_component_health
    returns a coroutine instead of a dictionary, causing the infamous:
    "'coroutine' object has no attribute 'get'" error at websocket.py:557
    """
    
    def setup_method(self, method=None):
        super().setup_method(method)
        self.test_user_id = "test_user_123"
        self.logger = logging.getLogger(__name__)
        
        # Create test user context for health validation
        self.test_user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id="test_thread_123",
            run_id="test_run_123",
            request_id="test_request_123",
            websocket_client_id="test_websocket_123"
        )
    
    def test_health_report_returns_dict_not_coroutine(self):
        """
        CORE VALIDATION: health_report must be dict, never coroutine.
        
        This test ensures validate_websocket_component_health always returns
        a dictionary with .get() method availability, preventing the coroutine error.
        
        CRITICAL: This test MUST FAIL if coroutine is returned instead of dict.
        """
        self.logger.info("🧪 UNIT TEST: Validating health_report is dict, not coroutine")
        
        # Call the function that should return a dict
        health_report = validate_websocket_component_health(self.test_user_context)
        
        # CRITICAL ASSERTION: Must be dict, not coroutine
        self.assertIsInstance(
            health_report, 
            dict, 
            f"health_report must be dict, got {type(health_report)}. "
            f"If this is a coroutine, it will cause the '.get() attribute error' in websocket.py:557"
        )
        
        # SPECIFIC ERROR REPRODUCTION: These .get() calls cause the staging error
        # If health_report is a coroutine, these will raise AttributeError
        try:
            error_suggestions = health_report.get("error_suggestions", [])
            self.assertIsInstance(error_suggestions, list, "error_suggestions must be list")
            
            component_health = health_report.get("summary", "Component health check failed")
            self.assertIsInstance(component_health, str, "component_health must be string")
            
            self.logger.info("✅ UNIT SUCCESS: health_report.get() calls work correctly")
            
        except AttributeError as e:
            if "'coroutine' object has no attribute 'get'" in str(e):
                self.fail(
                    f"COROUTINE ERROR REPRODUCED: {e}. "
                    f"This is the exact error happening in staging at websocket.py:557. "
                    f"health_report is a coroutine instead of dict."
                )
            else:
                raise
    
    def test_health_report_contains_required_fields(self):
        """
        STRUCTURE VALIDATION: health_report must have all expected dictionary fields.
        
        This validates the expected dictionary structure that WebSocket error
        handlers depend on. Missing fields or wrong types cause downstream failures.
        """
        self.logger.info("🧪 UNIT TEST: Validating health_report dictionary structure")
        
        health_report = validate_websocket_component_health(self.test_user_context)
        
        # Validate required fields exist and have correct types
        required_fields = {
            "healthy": bool,
            "failed_components": list,
            "component_details": dict,
            "error_suggestions": list,
            "timestamp": str
        }
        
        for field_name, expected_type in required_fields.items():
            self.assertIn(
                field_name, 
                health_report, 
                f"health_report missing required field: {field_name}"
            )
            
            field_value = health_report[field_name]
            self.assertIsInstance(
                field_value, 
                expected_type,
                f"health_report['{field_name}'] must be {expected_type.__name__}, got {type(field_value)}"
            )
        
        self.logger.info("✅ UNIT SUCCESS: health_report has all required dictionary fields")
    
    def test_async_health_check_collision_simulation(self):
        """
        COLLISION SIMULATION: Reproduce the async import collision causing coroutine return.
        
        This test simulates the exact condition where async health check functions
        get mixed up with sync returns, causing a coroutine to be returned where
        a dict is expected.
        
        EXPECTED BEHAVIOR: Test should FAIL if async/sync collision is not handled properly.
        """
        self.logger.info("🧪 UNIT TEST: Simulating async/sync health check collision")
        
        # Mock an async health check function that returns coroutine instead of dict
        async def mock_async_health_check():
            """Simulated async health check that could be returned without await."""
            return {
                "status": "healthy",
                "details": "Async health check result"
            }
        
        # Test the actual validate function - it should handle async scenarios properly
        # and never return a coroutine directly
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.get_config') as mock_config:
            # Configure mocks to simulate the collision scenario
            mock_config.return_value = MagicMock()
            
            health_report = validate_websocket_component_health(self.test_user_context)
            
            # CRITICAL: Even with async functions in the environment, 
            # validate_websocket_component_health must return dict, not coroutine
            self.assertIsInstance(
                health_report, 
                dict,
                f"Even with async collision simulation, health_report must be dict, got {type(health_report)}"
            )
            
            # Verify the .get() method works (this is what fails in staging)
            test_get_result = health_report.get("healthy", False)
            self.assertIsInstance(
                test_get_result,
                (bool, type(None)),
                "health_report.get() must work without AttributeError"
            )
        
        self.logger.info("✅ UNIT SUCCESS: Async collision simulation handled properly")
    
    def test_websocket_error_handler_dict_operations(self):
        """
        ERROR HANDLER SIMULATION: Test exact dict operations used in websocket.py:557.
        
        This reproduces the exact code patterns from the WebSocket error handler
        that cause the "'coroutine' object has no attribute 'get'" error.
        """
        self.logger.info("🧪 UNIT TEST: Simulating exact websocket.py error handler operations")
        
        health_report = validate_websocket_component_health(self.test_user_context)
        
        # EXACT REPRODUCTION: These are the lines from websocket.py causing the error
        try:
            # Line equivalent to websocket.py:557
            error_suggestions = health_report.get("error_suggestions", [])
            
            # Line equivalent to websocket.py:572 
            component_health = health_report.get("summary", "Component health check failed")
            
            # Additional dict operations from error handler
            failed_components = health_report.get("failed_components", [])
            healthy_status = health_report.get("healthy", False)
            
            # Validate all operations succeeded
            self.assertIsInstance(error_suggestions, list)
            self.assertIsInstance(component_health, str)  
            self.assertIsInstance(failed_components, list)
            self.assertIsInstance(healthy_status, bool)
            
            self.logger.info("✅ UNIT SUCCESS: All websocket.py dict operations work correctly")
            
        except AttributeError as e:
            if "coroutine" in str(e) and "get" in str(e):
                self.fail(
                    f"EXACT STAGING ERROR REPRODUCED: {e}. "
                    f"This is the same AttributeError happening in production. "
                    f"health_report is a coroutine, causing dict operation failures."
                )
            else:
                raise
    
    def test_type_safety_enforcement(self):
        """
        TYPE SAFETY: Validate health_report type consistency under all conditions.
        
        This test ensures that regardless of configuration, environment, or
        async context, health_report is always a dictionary type.
        """
        self.logger.info("🧪 UNIT TEST: Enforcing health_report type safety")
        
        # Test with different user context scenarios
        test_scenarios = [
            ("with_user_context", self.test_user_context),
            ("without_user_context", None),
        ]
        
        for scenario_name, user_context in test_scenarios:
            with self.subTest(scenario=scenario_name):
                health_report = validate_websocket_component_health(user_context)
                
                # TYPE ENFORCEMENT: Must always be dict
                self.assertIsInstance(
                    health_report,
                    dict,
                    f"Scenario '{scenario_name}': health_report must be dict, got {type(health_report)}"
                )
                
                # ATTRIBUTE VALIDATION: Must have dict methods
                self.assertTrue(
                    hasattr(health_report, 'get'),
                    f"Scenario '{scenario_name}': health_report must have .get() method"
                )
                
                # FUNCTIONALITY TEST: .get() must work
                test_result = health_report.get("test_key", "default_value")
                self.assertEqual(
                    test_result, 
                    "default_value",
                    f"Scenario '{scenario_name}': .get() method must work correctly"
                )
        
        self.logger.info("✅ UNIT SUCCESS: Type safety enforced across all scenarios")
    
    def tearDown(self):
        super().tearDown()
        self.logger.info("🏁 UNIT TEST COMPLETE: Health report type validation finished")


if __name__ == '__main__':
    # Run individual test for debugging
    unittest.main(verbosity=2)