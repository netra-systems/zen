#!/usr/bin/env python3
"""
Issue #991 Interface Gaps Resolution Verification Test

This test verifies that the missing interface methods have been successfully
implemented and that the agent registry interface gaps are resolved.

Test Type: Integration (verifies real interface functionality)
Business Impact: Protects $500K+ ARR Golden Path functionality
Technical Impact: Validates SSOT agent registry consolidation
"""

import unittest
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry


class TestAgentRegistryInterfaceGapsResolved(unittest.TestCase):
    """Verify that Issue #991 interface gaps have been resolved."""

    def setUp(self):
        """Set up test with real AgentRegistry instance."""
        self.registry = AgentRegistry()

    def test_all_missing_methods_now_exist(self):
        """Test that all previously missing interface methods now exist."""
        # These were the four missing methods identified in Issue #991
        required_methods = [
            'get_agent_by_name',
            'get_agent_by_id', 
            'is_agent_available',
            'get_agent_metadata'
        ]
        
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(self.registry, method_name),
                    f"Method {method_name} should now exist but doesn't"
                )
                
                # Verify it's actually callable
                method = getattr(self.registry, method_name)
                self.assertTrue(
                    callable(method),
                    f"Method {method_name} exists but is not callable"
                )

    def test_get_agent_by_name_functionality(self):
        """Test get_agent_by_name method works correctly."""
        # Test with non-existent agent (should return None)
        result = self.registry.get_agent_by_name("non_existent_agent")
        self.assertIsNone(result, "Non-existent agent should return None")
        
        # Test with empty name (should return None)
        result = self.registry.get_agent_by_name("")
        self.assertIsNone(result, "Empty name should return None")

    def test_get_agent_by_id_functionality(self):
        """Test get_agent_by_id method works correctly."""
        # Test with non-existent ID (should return None)
        result = self.registry.get_agent_by_id("non_existent_id")
        self.assertIsNone(result, "Non-existent ID should return None")
        
        # Test with empty ID (should return None)
        result = self.registry.get_agent_by_id("")
        self.assertIsNone(result, "Empty ID should return None")

    def test_is_agent_available_functionality(self):
        """Test is_agent_available method works correctly."""
        # Test with known available agent type
        result = self.registry.is_agent_available("supervisor_agent")
        self.assertTrue(result, "supervisor_agent should be available")
        
        # Test with unknown agent type
        result = self.registry.is_agent_available("unknown_agent")
        self.assertFalse(result, "unknown_agent should not be available")
        
        # Test with empty type
        result = self.registry.is_agent_available("")
        self.assertFalse(result, "Empty agent type should not be available")

    def test_get_agent_metadata_functionality(self):
        """Test get_agent_metadata method works correctly."""
        # Test with known agent type
        metadata = self.registry.get_agent_metadata("supervisor_agent")
        self.assertIsInstance(metadata, dict, "Metadata should be a dictionary")
        self.assertIn("name", metadata, "Metadata should include name")
        self.assertIn("description", metadata, "Metadata should include description")
        self.assertEqual(metadata["name"], "Supervisor Agent")
        
        # Test with unknown agent type
        metadata = self.registry.get_agent_metadata("unknown_agent")
        self.assertIsInstance(metadata, dict, "Unknown agent should still return dict")
        self.assertIn("name", metadata, "Unknown agent metadata should include name")
        
        # Test with empty type
        metadata = self.registry.get_agent_metadata("")
        self.assertEqual(metadata, {}, "Empty agent type should return empty dict")

    def test_interface_parity_golden_path_protection(self):
        """Test that interface provides necessary methods for Golden Path."""
        # These are the core methods needed for Golden Path user flow
        golden_path_methods = [
            ('is_agent_available', 'supervisor_agent'),
            ('get_agent_metadata', 'supervisor_agent'),
            ('get_agent_by_name', 'supervisor'),
            ('get_agent_by_id', 'test_id')
        ]
        
        for method_name, test_arg in golden_path_methods:
            with self.subTest(method=method_name, arg=test_arg):
                method = getattr(self.registry, method_name)
                
                # Should not raise exceptions
                try:
                    result = method(test_arg)
                    self.assertIsNotNone(
                        result if method_name.startswith('is_') or method_name.startswith('get_agent_metadata') else True,
                        f"Method {method_name} should return a valid result"
                    )
                except Exception as e:
                    self.fail(f"Method {method_name} raised unexpected exception: {e}")

    def test_websocket_integration_support(self):
        """Test that the interface supports WebSocket integration requirements."""
        # WebSocket integration requires agent availability checking
        self.assertTrue(
            self.registry.is_agent_available("supervisor_agent"),
            "WebSocket requires supervisor_agent availability"
        )
        
        # WebSocket integration requires metadata access
        metadata = self.registry.get_agent_metadata("supervisor_agent")
        self.assertTrue(
            metadata.get("supports_websocket", False),
            "Supervisor agent should support WebSocket integration"
        )


if __name__ == "__main__":
    unittest.main()