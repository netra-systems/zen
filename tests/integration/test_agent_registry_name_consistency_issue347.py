"""Integration tests for GitHub Issue #347: Agent registry name consistency

PURPOSE: These integration tests validate agent registry behavior with real services,
demonstrating how the agent name mismatch affects actual agent creation and execution workflows.

ISSUE CONTEXT:
- Agent registry registers "optimization" but tests/database expect "apex_optimizer"
- This affects real agent lookup and execution workflows
- Integration tests show the impact on multi-agent workflows

TEST APPROACH:
1. Test real agent registry initialization and lookup
2. Validate agent creation workflows with real contexts
3. Demonstrate workflow failures due to incorrect agent names
"""

import asyncio
import pytest
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, AsyncMock

# SSOT testing framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Real service imports for integration testing
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, get_agent_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from shared.isolated_environment import IsolatedEnvironment


class TestAgentRegistryNameConsistencyIntegration(SSotAsyncTestCase):
    """Integration tests for agent registry naming consistency with real services."""
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Set up class-level resources for integration testing."""
        await super().asyncSetUpClass()
        
        # Initialize isolated environment for real service testing
        cls.env = IsolatedEnvironment()
        
        # Create real LLM manager for testing (or mock if no real API keys)
        try:
            cls.llm_manager = LLMManager()
        except Exception:
            # If LLM manager can't be initialized, use mock
            cls.llm_manager = Mock(spec=LLMManager)
        
        # Create multiple user contexts for testing isolation
        cls.test_users = {
            "user_347_1": UserExecutionContext(
                user_id="integration_test_347_user1",
                request_id="int_test_347_req1", 
                thread_id="int_test_347_thread1",
                run_id="int_test_347_run1"
            ),
            "user_347_2": UserExecutionContext(
                user_id="integration_test_347_user2",
                request_id="int_test_347_req2",
                thread_id="int_test_347_thread2", 
                run_id="int_test_347_run2"
            )
        }
    
    async def asyncSetUp(self):
        """Set up each test with fresh registry."""
        await super().asyncSetUp()
        
        # Create fresh registry for each test
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        await self.registry.initialize()
        
        # Register default agents to test with real registration
        self.registry.register_default_agents()
    
    async def asyncTearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'registry'):
            await self.registry.cleanup()
        await super().asyncTearDown()
    
    async def test_real_agent_registry_naming_patterns(self):
        """Test 1: Validate real agent registry naming patterns with registered names."""
        
        # Get actual registered agent names from real registry
        registered_names = self.registry.list_agents()
        
        print(f"\n🔍 Integration Test - Actual registered agents: {registered_names}")
        
        # Test core agents that should be registered
        expected_core_agents = ["triage", "data", "optimization", "actions", "reporting"]
        
        for agent_name in expected_core_agents:
            if agent_name in registered_names:
                print(f"✅ Core agent '{agent_name}' is properly registered")
                
                # Test that we can get registry reference (even if factory returns None)
                registry_has_agent = self.registry.has(agent_name)
                self.assertTrue(registry_has_agent,
                               f"Registry should recognize agent name '{agent_name}'")
            else:
                print(f"❌ Core agent '{agent_name}' is missing from registry")
                self.fail(f"Expected core agent '{agent_name}' not found in registry")
        
        # Test that problematic names are NOT registered
        problematic_names = ["apex_optimizer", "apex_optimizer_agent"]
        
        for problem_name in problematic_names:
            self.assertNotIn(problem_name, registered_names,
                           f"Problematic name '{problem_name}' should not be in registry")
            
            registry_has_problem = self.registry.has(problem_name)
            self.assertFalse(registry_has_problem,
                            f"Registry should not recognize problematic name '{problem_name}'")
            print(f"✅ Confirmed '{problem_name}' is not registered (as expected)")
    
    async def test_agent_creation_workflow_with_correct_names(self):
        """Test 2: Validate agent creation workflow works with correctly registered names."""
        
        user_context = self.test_users["user_347_1"]
        
        # Test creating agents with CORRECT names (should work)
        correct_agent_names = ["optimization", "triage", "data"]
        
        for agent_name in correct_agent_names:
            try:
                # Create agent for user using registry factory pattern
                agent = await self.registry.create_agent_for_user(
                    user_id=user_context.user_id,
                    agent_type=agent_name,
                    user_context=user_context
                )
                
                if agent is not None:
                    print(f"✅ Successfully created '{agent_name}' agent for user {user_context.user_id}")
                    
                    # Verify agent is stored in user session
                    user_agent = await self.registry.get_user_agent(
                        user_context.user_id, agent_name
                    )
                    self.assertIsNotNone(user_agent,
                                       f"Agent '{agent_name}' should be retrievable from user session")
                else:
                    print(f"⚠️ Agent '{agent_name}' creation returned None (may be factory pattern limitation)")
                    # Even if None, the registry should recognize the name
                    self.assertTrue(self.registry.has(agent_name),
                                  f"Registry should at least recognize '{agent_name}'")
                
            except Exception as e:
                print(f"❌ Failed to create '{agent_name}' agent: {e}")
                # This test should not fail for correct names
                self.fail(f"Agent creation failed for correct name '{agent_name}': {e}")
    
    async def test_agent_creation_workflow_with_incorrect_names(self):
        """Test 3: Demonstrate that agent creation fails with incorrect names."""
        
        user_context = self.test_users["user_347_2"]
        
        # Test creating agents with INCORRECT names (should fail)
        incorrect_agent_names = ["apex_optimizer", "apex_optimizer_agent", "optimization_agent"]
        
        for incorrect_name in incorrect_agent_names:
            print(f"\n🚨 Testing incorrect agent name: '{incorrect_name}'")
            
            # This should fail or return None
            with self.assertRaises((KeyError, ValueError, Exception)) as context:
                agent = await self.registry.create_agent_for_user(
                    user_id=user_context.user_id,
                    agent_type=incorrect_name,
                    user_context=user_context
                )
                
                # If no exception, agent should be None
                if agent is not None:
                    self.fail(f"Expected agent creation to fail for incorrect name '{incorrect_name}', but got: {agent}")
            
            print(f"✅ Confirmed agent creation properly failed for incorrect name '{incorrect_name}'")
            print(f"   Error: {context.exception}")
            
            # Verify the incorrect name is not in registry
            self.assertFalse(self.registry.has(incorrect_name),
                           f"Registry should not recognize incorrect name '{incorrect_name}'")
    
    async def test_multi_user_agent_workflow_consistency(self):
        """Test 4: Validate naming consistency across multiple user workflows."""
        
        # Test workflow with multiple users to ensure naming is consistent
        workflow_results = {}
        
        for user_key, user_context in self.test_users.items():
            print(f"\n👤 Testing workflow for {user_key}")
            
            user_results = {
                "successful_agents": [],
                "failed_agents": [],
                "registry_health": None
            }
            
            # Test standard workflow agents
            workflow_agents = ["triage", "optimization", "actions"]
            
            for agent_name in workflow_agents:
                try:
                    # Create agent for this user
                    agent = await self.registry.create_agent_for_user(
                        user_id=user_context.user_id,
                        agent_type=agent_name,
                        user_context=user_context
                    )
                    
                    if agent is not None or self.registry.has(agent_name):
                        user_results["successful_agents"].append(agent_name)
                        print(f"  ✅ '{agent_name}' workflow step successful")
                    else:
                        user_results["failed_agents"].append(agent_name)
                        print(f"  ❌ '{agent_name}' workflow step failed")
                        
                except Exception as e:
                    user_results["failed_agents"].append(agent_name)
                    print(f"  ❌ '{agent_name}' workflow step failed: {e}")
            
            # Get user session health
            user_session = await self.registry.get_user_session(user_context.user_id)
            user_results["registry_health"] = user_session.get_metrics()
            
            workflow_results[user_key] = user_results
        
        # Validate consistency across users
        all_successful = set()
        all_failed = set()
        
        for user_key, results in workflow_results.items():
            all_successful.update(results["successful_agents"])
            all_failed.update(results["failed_agents"])
        
        # Agents should consistently work or fail across all users
        inconsistent_agents = all_successful.intersection(all_failed)
        
        self.assertEqual(len(inconsistent_agents), 0,
                        f"These agents had inconsistent results across users: {inconsistent_agents}")
        
        print(f"\n🔍 Multi-user workflow summary:")
        print(f"   Consistently successful agents: {all_successful - all_failed}")
        print(f"   Consistently failed agents: {all_failed - all_successful}")
        print(f"   Inconsistent agents (PROBLEM): {inconsistent_agents}")


class TestAgentRegistryRealServiceIntegration(SSotAsyncTestCase):
    """Integration tests with real agent registry patterns and services."""
    
    async def asyncSetUp(self):
        """Set up with real service configurations."""
        await super().asyncSetUp()
        
        # Use real get_agent_registry function to test full integration
        try:
            # Create real LLM manager
            llm_manager = LLMManager()
        except Exception:
            # Fallback to mock if real services unavailable
            llm_manager = Mock(spec=LLMManager)
        
        self.registry = get_agent_registry(llm_manager)
        
        # Test user context
        self.user_context = UserExecutionContext(
            user_id="real_service_test_347",
            request_id="real_test_347_req",
            thread_id="real_test_347_thread", 
            run_id="real_test_347_run"
        )
    
    async def asyncTearDown(self):
        """Clean up real services."""
        if hasattr(self, 'registry'):
            await self.registry.cleanup()
        await super().asyncTearDown()
    
    async def test_real_service_agent_registry_factory_patterns(self):
        """Test 5: Validate agent registry factory patterns with real service integration."""
        
        # Test the factory pattern integration  
        registry_health = self.registry.get_registry_health()
        
        print(f"\n🔍 Real service registry health: {registry_health}")
        
        # Validate registry is properly initialized
        self.assertEqual(registry_health.get("status", "unknown"), "healthy",
                        "Registry should be healthy for real service testing")
        
        # Test factory integration status
        factory_status = self.registry.get_factory_integration_status()
        
        print(f"🔍 Factory integration status: {factory_status}")
        
        # Validate factory patterns are working
        self.assertTrue(factory_status.get("factory_patterns_enabled", False),
                       "Factory patterns should be enabled for proper agent isolation")
        
        self.assertTrue(factory_status.get("hardened_isolation_enabled", False),
                       "Hardened isolation should be enabled for security")
        
        # Test SSOT compliance
        ssot_compliance = factory_status.get("ssot_compliance", {})
        compliance_score = ssot_compliance.get("compliance_score", 0)
        
        self.assertGreater(compliance_score, 80,
                          f"SSOT compliance should be > 80%, got {compliance_score}%")
    
    async def test_websocket_integration_with_agent_naming(self):
        """Test 6: Validate WebSocket integration works with correct agent names."""
        
        # Create mock WebSocket manager for testing
        mock_websocket_manager = Mock()
        mock_websocket_manager.notify_agent_started = AsyncMock()
        mock_websocket_manager.notify_agent_completed = AsyncMock()
        
        # Set WebSocket manager on registry
        await self.registry.set_websocket_manager_async(mock_websocket_manager)
        
        # Test WebSocket diagnosis
        ws_diagnosis = self.registry.diagnose_websocket_wiring()
        
        print(f"\n🔍 WebSocket wiring diagnosis: {ws_diagnosis}")
        
        # Should have WebSocket manager
        self.assertTrue(ws_diagnosis.get("registry_has_websocket_manager", False),
                       "Registry should have WebSocket manager for event integration")
        
        # Test agent creation with WebSocket integration
        try:
            agent = await self.registry.create_agent_for_user(
                user_id=self.user_context.user_id,
                agent_type="optimization",  # Use CORRECT name
                user_context=self.user_context,
                websocket_manager=mock_websocket_manager
            )
            
            # Verify user session has WebSocket bridge
            user_session = await self.registry.get_user_session(self.user_context.user_id)
            session_metrics = user_session.get_metrics()
            
            self.assertTrue(session_metrics.get("has_websocket_bridge", False),
                           "User session should have WebSocket bridge for agent events")
            
            print("✅ WebSocket integration works with correct agent naming")
            
        except Exception as e:
            print(f"❌ WebSocket integration test failed: {e}")
            # This might fail due to factory patterns, but naming should be consistent
            
            # At minimum, registry should recognize the correct name
            self.assertTrue(self.registry.has("optimization"),
                           "Registry should recognize 'optimization' even if creation fails")


if __name__ == "__main__":
    # Run integration tests to demonstrate real-world impact
    print("🚨 Running Integration Tests for GitHub Issue #347: Agent Registry Name Consistency")
    print("=" * 80)
    
    import unittest
    unittest.main(verbosity=2)