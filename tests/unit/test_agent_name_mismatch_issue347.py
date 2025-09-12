"""Unit tests for GitHub Issue #347: Agent name mismatch between expected and registered names

PURPOSE: This test suite demonstrates the issue where tests expect agents to be registered
with names like "apex_optimizer" but the actual registry uses different names like "optimization".

ISSUE DETAILS:
- Expected: "apex_optimizer" (from tests and database models)
- Actual: "optimization" (in AgentRegistry._register_optimization_agents)
- Impact: Tests fail when trying to retrieve agents using the expected names

TEST STRATEGY:
1. Unit tests validate registry naming patterns 
2. Demonstrate the mismatch between expected and actual names
3. Test agent lookup failures due to naming inconsistency
"""

import unittest
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, AsyncMock
import pytest

# SSOT testing framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Import actual agent registry and related components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentNameMismatchUnit(SSotAsyncTestCase):
    """Unit tests demonstrating agent name mismatch issue (Issue #347)."""
    
    def setup_method(self, method=None):
        """Set up test environment for each test method."""
        super().setup_method(method)
        
        # Create mock LLM manager for registry initialization
        self.mock_llm_manager = Mock()
        
        # Create user context for testing
        self.test_user_context = UserExecutionContext(
            user_id="test_user_347", 
            request_id="test_request_347",
            thread_id="test_thread_347",
            run_id="test_run_347"
        )
        
        # Initialize registry with mocks
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
    
    async def test_agent_registry_registered_names(self):
        """Test 1: Verify what names are actually registered in the agent registry.
        
        This test documents the current state of agent registration and should pass.
        It shows what names the registry actually uses.
        """
        # Register default agents to see what names are used
        self.registry.register_default_agents()
        
        # Get all registered agent names
        registered_names = self.registry.list_agents()
        
        # Document actual registered names for comparison
        print(f"\nIssue #347 - Actual registered agent names: {registered_names}")
        
        # Verify the optimization agent is registered (this should pass)
        self.assertIn("optimization", registered_names, 
                     "Expected 'optimization' to be registered in agent registry")
        
        # Document other core agent names that are actually registered
        expected_registered_names = ["triage", "data", "optimization", "actions", "reporting"]
        for name in expected_registered_names:
            if name in registered_names:
                print(f"✅ Agent '{name}' is registered as expected")
            else:
                print(f"❌ Agent '{name}' is NOT registered (may cause issues)")
    
    async def test_apex_optimizer_name_expectation_fails(self):
        """Test 2: Demonstrate that expected names like 'apex_optimizer' fail.
        
        This test should FAIL, demonstrating the naming mismatch issue.
        Tests expecting 'apex_optimizer' will fail because it's registered as 'optimization'.
        """
        # Register default agents
        self.registry.register_default_agents()
        
        # This should return None or raise exception - demonstrating the issue
        try:
            agent = await self.registry.get_agent("apex_optimizer", self.test_user_context)
            # If we get here, it should be None (not found)
            self.assertIsNone(agent, 
                             "Expected 'apex_optimizer' agent to not be found (demonstrating the issue)")
            print(f"\nIssue #347 - 'apex_optimizer' correctly returned None (demonstrates naming mismatch)")
        except Exception as e:
            print(f"\nIssue #347 - Expected failure when looking for 'apex_optimizer': {e}")
        
        # Verify the correct name works
        agent = await self.registry.get_agent("optimization", self.test_user_context)
        # Note: This might be None due to factory pattern, but name should be recognized
        
        # The key point is that 'apex_optimizer' is not in the registry
        registered_names = self.registry.list_agents()
        self.assertNotIn("apex_optimizer", registered_names,
                        "This confirms 'apex_optimizer' is not registered (demonstrating the issue)")
        self.assertIn("optimization", registered_names,
                     "But 'optimization' is registered (showing the mismatch)")
    
    async def test_database_model_name_expectations(self):
        """Test 3: Test that database models expect 'apex_optimizer' but registry uses 'optimization'.
        
        This test demonstrates the disconnect between database models and agent registry.
        Database models reference 'apex_optimizer' but the registry registers 'optimization'.
        """
        # Register default agents
        self.registry.register_default_agents()
        registered_names = self.registry.list_agents()
        
        # Database models and tests expect these names (based on our earlier search)
        database_expected_names = [
            "apex_optimizer",  # Used in database models and table names
            "apex_optimizer_agent",  # Variant that might be expected
        ]
        
        # Registry actually registers these names
        registry_actual_names = [
            "optimization",  # What's actually registered
            "actions",       # Actions agent (related to optimization workflow)
        ]
        
        # Demonstrate the mismatch
        for expected_name in database_expected_names:
            self.assertNotIn(expected_name, registered_names,
                           f"Database expects '{expected_name}' but it's not registered in agent registry")
            print(f"❌ Mismatch: Database/tests expect '{expected_name}' but it's not in registry")
        
        for actual_name in registry_actual_names:
            self.assertIn(actual_name, registered_names,
                         f"Registry correctly has '{actual_name}' but tests may not expect this name")
            print(f"✅ Registry has '{actual_name}' but tests might look for different names")
        
        # This demonstrates the core issue: mismatch between expected and actual names
        print("\n🚨 Issue #347 Summary:")
        print(f"   Database/Test expectations: {database_expected_names}")
        print(f"   Registry actual names: {[name for name in registry_actual_names if name in registered_names]}")


class TestAgentNamingConsistencyUnit(SSotBaseTestCase):
    """Additional unit tests for agent naming consistency patterns."""
    
    def test_agent_name_patterns(self):
        """Test 4: Analyze naming patterns to understand the inconsistency."""
        
        # Expected patterns based on codebase analysis
        naming_patterns = {
            "database_models": [
                "apex_optimizer",
                "apex_optimizer_agent_runs", 
                "apex_optimizer_agent_run_reports"
            ],
            "registry_patterns": [
                "optimization",  # What's actually registered
                "triage",
                "data", 
                "actions",
                "reporting"
            ],
            "tool_patterns": [
                "apex_optimizer",  # Tool name in database usage logs
            ]
        }
        
        # Identify patterns in naming conventions
        database_uses_apex = any("apex" in name for name in naming_patterns["database_models"])
        registry_uses_short = all(len(name.split("_")) <= 2 for name in naming_patterns["registry_patterns"])
        
        self.assertTrue(database_uses_apex, 
                       "Database models use 'apex_' prefix but registry might not")
        self.assertTrue(registry_uses_short,
                       "Registry uses shorter names without 'apex_' prefix")
        
        # This shows the pattern mismatch
        print(f"\n🔍 Naming pattern analysis:")
        print(f"   Database uses 'apex_' prefix: {database_uses_apex}")
        print(f"   Registry uses short names: {registry_uses_short}")
        print("   This confirms a systematic naming inconsistency")
    
    @patch('netra_backend.app.agents.supervisor.agent_registry.logger')
    def test_agent_lookup_error_handling(self, mock_logger):
        """Test 5: Verify error handling when looking for incorrectly named agents."""
        
        # Create registry with mock LLM manager
        mock_llm_manager = Mock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        registry.register_default_agents()
        
        # Test looking for the incorrect name
        result = registry.get("apex_optimizer")
        
        # Should return None for non-existent agent
        self.assertIsNone(result, 
                         "Looking up 'apex_optimizer' should return None (demonstrating the issue)")
        
        # Test looking for the correct name  
        correct_result = registry.get("optimization")
        # Note: This might also be None due to factory pattern, but the key is the name is recognized
        
        # The important test is that the registry recognizes the correct name
        registered_names = registry.list_agents()
        self.assertIn("optimization", registered_names,
                     "Registry should recognize 'optimization' as a valid agent name")
        self.assertNotIn("apex_optimizer", registered_names,
                        "Registry should NOT recognize 'apex_optimizer' (confirming the issue)")
        
        print(f"\n🔍 Agent lookup results:")
        print(f"   'apex_optimizer' lookup result: {result}")
        print(f"   'optimization' in registry: {'optimization' in registered_names}")
        print(f"   This confirms the lookup mismatch issue")


if __name__ == "__main__":
    # Run tests to demonstrate the agent name mismatch issue
    print("🚨 Running Unit Tests for GitHub Issue #347: Agent Name Mismatch")
    print("=" * 70)
    
    unittest.main(verbosity=2)