"""
Unit tests for WebSocket authentication variable scoping fixes.

This test suite validates that the is_production variable scoping bug
identified in Issue #147 has been properly fixed.

Bug Description:
- Line 119: Variable used before declaration (UnboundLocalError)
- Line 151: Variable declaration
- Fix: Move declaration before usage

Business Value Justification:
- Segment: Platform/Internal - WebSocket Infrastructure  
- Business Goal: Prevent Golden Path blocking authentication failures
- Value Impact: Ensures WebSocket connections work in staging environment
- Revenue Impact: Prevents $120K+ MRR blocking failures from authentication bugs
"""

import unittest
from unittest.mock import MagicMock, patch
import pytest

from netra_backend.app.websocket_core.unified_websocket_auth import extract_e2e_context_from_websocket


class TestWebSocketAuthScoping(unittest.TestCase):
    """Test variable scoping fixes in WebSocket authentication."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_websocket = MagicMock()
        self.mock_websocket.headers = {"test-header": "test-value"}
    
    @patch('netra_backend.app.websocket_core.unified_websocket_auth.get_env')
    def test_staging_environment_e2e_context_extraction_no_scoping_error(self, mock_get_env):
        """
        Test that staging environment E2E context extraction doesn't cause UnboundLocalError.
        
        This test specifically validates the fix for Issue #147 where is_production
        was used before declaration, causing UnboundLocalError in staging environments.
        """
        # Configure mock environment for staging with E2E conditions
        mock_get_env.return_value = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-backend-staging",
            "K_SERVICE": "netra-backend-staging",
            "E2E_TESTING": "1",  # This triggers the problematic code path
            "STAGING_E2E_TEST": "1"
        }
        
        # This should NOT raise UnboundLocalError after the fix
        try:
            result = extract_e2e_context_from_websocket(self.mock_websocket)
            
            # Verify the result is valid E2E context
            self.assertIsInstance(result, dict)
            self.assertTrue(result.get("is_e2e_testing", False))
            self.assertEqual(result.get("environment"), "staging")
            self.assertTrue(result.get("bypass_enabled", False))
            
            # Verify staging environment detection worked
            detection_method = result.get("detection_method", {})
            self.assertTrue(detection_method.get("via_environment", False))
            
        except UnboundLocalError as e:
            if "is_production" in str(e):
                self.fail(f"Variable scoping bug still exists: {e}")
            else:
                # Re-raise if it's a different UnboundLocalError
                raise
                
    @patch('netra_backend.app.websocket_core.unified_websocket_auth.get_env')
    def test_production_environment_blocks_e2e_bypass_correctly(self, mock_get_env):
        """
        Test that production environment correctly blocks E2E bypass.
        
        This ensures the security fix works correctly and is_production variable
        is properly declared and used.
        """
        # Configure mock environment for production
        mock_get_env.return_value = {
            "ENVIRONMENT": "production",
            "GOOGLE_CLOUD_PROJECT": "netra-production",
            "K_SERVICE": "netra-backend-prod",
            "E2E_TESTING": "1",  # Attempting E2E bypass
            "STAGING_E2E_TEST": "1"
        }
        
        # Should not raise UnboundLocalError and should block E2E bypass
        result = extract_e2e_context_from_websocket(self.mock_websocket)
        
        # In production, E2E bypass should be blocked
        self.assertIsNone(result, "Production environment should block E2E bypass")
        
    @patch('netra_backend.app.websocket_core.unified_websocket_auth.get_env')
    def test_development_environment_allows_e2e_context(self, mock_get_env):
        """
        Test that development environment allows E2E context extraction.
        """
        # Configure mock environment for development
        mock_get_env.return_value = {
            "ENVIRONMENT": "development",
            "GOOGLE_CLOUD_PROJECT": "netra-dev",
            "K_SERVICE": "netra-backend-dev",
            "E2E_TESTING": "1"
        }
        
        # Should work without scoping errors
        result = extract_e2e_context_from_websocket(self.mock_websocket)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("is_e2e_testing", False))
        self.assertEqual(result.get("environment"), "development")
        
    def test_variable_declaration_order_validation(self):
        """
        Test that validates the actual source code has correct variable ordering.
        
        This is a meta-test that checks the source code structure to ensure
        the variable scoping fix is maintained.
        """
        import inspect
        from netra_backend.app.websocket_core.unified_websocket_auth import extract_e2e_context_from_websocket
        
        # Get the source code of the function
        source_lines = inspect.getsourcelines(extract_e2e_context_from_websocket)[0]
        
        is_production_declaration_line = None
        is_production_usage_line = None
        
        for i, line in enumerate(source_lines):
            # Find declaration
            if 'is_production = current_env' in line and 'production' in line:
                is_production_declaration_line = i
            # Find usage
            elif 'not is_production' in line and 'Extra safety check' in line:
                is_production_usage_line = i
                
        # Validate that declaration comes before usage
        self.assertIsNotNone(is_production_declaration_line, 
                           "Could not find is_production declaration")
        self.assertIsNotNone(is_production_usage_line,
                           "Could not find is_production usage")
        self.assertLess(is_production_declaration_line, is_production_usage_line,
                       "is_production must be declared before usage to prevent UnboundLocalError")


if __name__ == '__main__':
    unittest.main()