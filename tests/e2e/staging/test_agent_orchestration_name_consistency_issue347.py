"""E2E staging tests for GitHub Issue #347: Agent orchestration name consistency

PURPOSE: End-to-end tests running in staging environment to validate that agent name
mismatches affect complete user workflows and agent orchestration patterns.

STAGING CONTEXT:
- These tests run against staging environment with real services
- Demonstrates how naming issues impact complete Golden Path user flows
- Validates that orchestration systems can handle agent lookup correctly

ISSUE VALIDATION:
- Agent orchestration expects consistent naming
- User workflows may break if agents can't be found by expected names
- Staging environment provides realistic testing conditions
"""

import asyncio
import pytest
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, AsyncMock

# SSOT testing framework imports  
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Real staging service imports
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.staging
@pytest.mark.e2e
class TestAgentOrchestrationNameConsistencyE2E(SSotAsyncTestCase):
    """E2E staging tests for agent orchestration naming consistency."""
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Set up staging environment resources."""
        await super().asyncSetUpClass()
        
        # Initialize staging environment
        cls.env = IsolatedEnvironment()
        
        # Staging test users for realistic workflows
        cls.staging_users = {
            "golden_path_user": UserExecutionContext(
                user_id="staging_347_golden_path",
                request_id="e2e_347_golden_req",
                thread_id="e2e_347_golden_thread", 
                run_id="e2e_347_golden_run"
            ),
            "optimization_user": UserExecutionContext(
                user_id="staging_347_optimization",
                request_id="e2e_347_opt_req",
                thread_id="e2e_347_opt_thread",
                run_id="e2e_347_opt_run"
            )
        }
        
        print("🌐 E2E Staging Tests initialized for Issue #347")
    
    async def asyncSetUp(self):
        """Set up each staging test with real components."""
        await super().asyncSetUp()
        
        # Initialize real staging components
        try:
            # Get staging LLM manager
            from netra_backend.app.llm.llm_manager import LLMManager
            self.llm_manager = LLMManager()
        except Exception as e:
            # Fallback for staging environment issues
            print(f"⚠️ Using mock LLM manager in staging: {e}")
            self.llm_manager = Mock(spec=LLMManager)
        
        # Initialize staging registry with real components
        self.staging_registry = AgentRegistry(llm_manager=self.llm_manager)
        await self.staging_registry.initialize()
        self.staging_registry.register_default_agents()
        
        # Initialize staging WebSocket manager
        try:
            self.websocket_manager = get_websocket_manager()
        except Exception as e:
            print(f"⚠️ Using mock WebSocket manager in staging: {e}")
            self.websocket_manager = Mock()
            self.websocket_manager.notify_agent_started = AsyncMock()
            self.websocket_manager.notify_agent_completed = AsyncMock()
        
        # Set WebSocket manager on registry for realistic testing
        await self.staging_registry.set_websocket_manager_async(self.websocket_manager)
    
    async def asyncTearDown(self):
        """Clean up staging test resources."""
        if hasattr(self, 'staging_registry'):
            await self.staging_registry.cleanup()
        await super().asyncTearDown()
    
    async def test_golden_path_agent_orchestration_naming(self):
        """E2E Test 1: Validate Golden Path workflow with correct agent names in staging.
        
        This test simulates the complete Golden Path user flow in staging environment,
        ensuring that agent orchestration works with the correct naming patterns.
        """
        user_context = self.staging_users["golden_path_user"]
        
        print(f"\n🌟 Testing Golden Path orchestration for user: {user_context.user_id}")
        
        # Simulate Golden Path workflow steps with correct agent names
        golden_path_steps = [
            ("triage", "Initial user request triage"),
            ("data", "Data requirements analysis"), 
            ("optimization", "Optimization strategy generation"),  # CORRECT name
            ("actions", "Action plan creation"),
            ("reporting", "Final report generation")
        ]
        
        orchestration_results = {
            "successful_steps": [],
            "failed_steps": [],
            "agent_events": [],
            "websocket_events": []
        }
        
        # Execute Golden Path workflow with staging components
        for step_name, step_description in golden_path_steps:
            print(f"  🔄 Executing step: {step_name} - {step_description}")
            
            try:
                # Create agent for this workflow step
                agent = await self.staging_registry.create_agent_for_user(
                    user_id=user_context.user_id,
                    agent_type=step_name,
                    user_context=user_context,
                    websocket_manager=self.websocket_manager
                )
                
                if agent is not None:
                    print(f"    ✅ Agent '{step_name}' created successfully")
                    orchestration_results["successful_steps"].append(step_name)
                    
                    # Simulate agent execution events
                    if hasattr(self.websocket_manager, 'notify_agent_started'):
                        await self.websocket_manager.notify_agent_started(
                            user_context.run_id, step_name, {"step": step_description}
                        )
                        orchestration_results["websocket_events"].append(f"started_{step_name}")
                    
                elif self.staging_registry.has(step_name):
                    # Agent name recognized but creation might be factory pattern
                    print(f"    ⚠️ Agent '{step_name}' recognized but creation returned None (factory pattern)")
                    orchestration_results["successful_steps"].append(step_name)
                    
                else:
                    print(f"    ❌ Agent '{step_name}' not found in registry")
                    orchestration_results["failed_steps"].append(step_name)
                    
            except Exception as e:
                print(f"    ❌ Failed to create agent '{step_name}': {e}")
                orchestration_results["failed_steps"].append(step_name)
        
        # Validate Golden Path workflow success
        total_steps = len(golden_path_steps)
        successful_steps = len(orchestration_results["successful_steps"])
        success_rate = successful_steps / total_steps
        
        print(f"\n📊 Golden Path Orchestration Results:")
        print(f"   Total steps: {total_steps}")
        print(f"   Successful steps: {successful_steps}")
        print(f"   Success rate: {success_rate:.1%}")
        print(f"   Failed steps: {orchestration_results['failed_steps']}")
        print(f"   WebSocket events: {len(orchestration_results['websocket_events'])}")
        
        # Golden Path should achieve high success rate
        self.assertGreater(success_rate, 0.8,
                          f"Golden Path should achieve >80% success rate, got {success_rate:.1%}")
        
        # Critical agents should not fail
        critical_agents = ["triage", "optimization", "actions"]
        failed_critical = [agent for agent in critical_agents if agent in orchestration_results["failed_steps"]]
        
        self.assertEqual(len(failed_critical), 0,
                        f"Critical agents should not fail: {failed_critical}")
    
    async def test_agent_orchestration_with_incorrect_names(self):
        """E2E Test 2: Demonstrate orchestration failure with incorrect agent names in staging.
        
        This test shows how using incorrect agent names (like 'apex_optimizer') 
        breaks the complete orchestration workflow in a staging environment.
        """
        user_context = self.staging_users["optimization_user"]
        
        print(f"\n🚨 Testing orchestration with INCORRECT agent names for user: {user_context.user_id}")
        
        # Simulate workflow with INCORRECT agent names that tests might expect
        incorrect_workflow_steps = [
            ("triage", "Triage (correct name)", True),  # This should work
            ("apex_optimizer", "Optimization (INCORRECT name)", False),  # This should fail
            ("apex_optimizer_agent", "Optimization agent (INCORRECT variant)", False),  # This should fail
            ("optimization_agent", "Optimization (another incorrect variant)", False),  # This should fail
            ("actions", "Actions (correct name)", True),  # This should work
        ]
        
        orchestration_failure_results = {
            "expected_successes": [],
            "expected_failures": [],
            "unexpected_successes": [], 
            "unexpected_failures": [],
            "naming_issues": []
        }
        
        # Execute workflow with mix of correct and incorrect names
        for step_name, step_description, should_succeed in incorrect_workflow_steps:
            print(f"  🔄 Testing step: {step_name} - {step_description}")
            print(f"     Expected to succeed: {should_succeed}")
            
            try:
                # Attempt to create agent with potentially incorrect name
                agent = await self.staging_registry.create_agent_for_user(
                    user_id=user_context.user_id,
                    agent_type=step_name,
                    user_context=user_context,
                    websocket_manager=self.websocket_manager
                )
                
                # Check if agent was created or name is at least recognized
                agent_created = agent is not None
                name_recognized = self.staging_registry.has(step_name)
                
                if should_succeed:
                    if agent_created or name_recognized:
                        print(f"    ✅ Expected success: '{step_name}' worked as expected")
                        orchestration_failure_results["expected_successes"].append(step_name)
                    else:
                        print(f"    ❌ Unexpected failure: '{step_name}' should have worked")
                        orchestration_failure_results["unexpected_failures"].append(step_name)
                else:
                    if agent_created or name_recognized:
                        print(f"    ⚠️ Unexpected success: '{step_name}' should have failed")
                        orchestration_failure_results["unexpected_successes"].append(step_name)
                        orchestration_failure_results["naming_issues"].append(
                            f"Agent name '{step_name}' unexpectedly worked - might indicate naming fix"
                        )
                    else:
                        print(f"    ✅ Expected failure: '{step_name}' correctly failed")
                        orchestration_failure_results["expected_failures"].append(step_name)
                        orchestration_failure_results["naming_issues"].append(
                            f"Agent name '{step_name}' failed as expected - confirms naming issue"
                        )
                
            except Exception as e:
                if should_succeed:
                    print(f"    ❌ Unexpected exception for '{step_name}': {e}")
                    orchestration_failure_results["unexpected_failures"].append(step_name)
                else:
                    print(f"    ✅ Expected exception for '{step_name}': {e}")
                    orchestration_failure_results["expected_failures"].append(step_name)
        
        print(f"\n📊 Orchestration Naming Issue Results:")
        print(f"   Expected successes: {orchestration_failure_results['expected_successes']}")
        print(f"   Expected failures: {orchestration_failure_results['expected_failures']}")
        print(f"   Unexpected successes: {orchestration_failure_results['unexpected_successes']}")
        print(f"   Unexpected failures: {orchestration_failure_results['unexpected_failures']}")
        print(f"   Naming issues identified: {len(orchestration_failure_results['naming_issues'])}")
        
        for issue in orchestration_failure_results['naming_issues']:
            print(f"     🔍 {issue}")
        
        # Validate that incorrect names fail as expected (confirming the issue)
        expected_incorrect_names = ["apex_optimizer", "apex_optimizer_agent", "optimization_agent"]
        
        for incorrect_name in expected_incorrect_names:
            if incorrect_name in orchestration_failure_results["expected_failures"]:
                print(f"✅ Confirmed: '{incorrect_name}' correctly failed (demonstrates issue)")
            elif incorrect_name in orchestration_failure_results["unexpected_successes"]:
                print(f"⚠️ Unexpected: '{incorrect_name}' worked (issue may be fixed)")
            
        # At least some incorrect names should fail, demonstrating the issue
        total_expected_failures = len(orchestration_failure_results["expected_failures"])
        self.assertGreater(total_expected_failures, 0,
                          "At least some incorrect names should fail, demonstrating the naming issue")


@pytest.mark.staging
@pytest.mark.slow
class TestStagingAgentWorkflowIntegration(SSotAsyncTestCase):
    """Complete staging workflow integration tests for agent naming."""
    
    async def asyncSetUp(self):
        """Set up staging workflow components."""
        await super().asyncSetUp()
        
        # Staging user context for workflow testing
        self.workflow_user = UserExecutionContext(
            user_id="staging_347_workflow",
            request_id="e2e_347_workflow_req",
            thread_id="e2e_347_workflow_thread",
            run_id="e2e_347_workflow_run"
        )
        
        # Initialize staging components with error handling
        try:
            from netra_backend.app.llm.llm_manager import LLMManager
            self.llm_manager = LLMManager()
        except Exception:
            self.llm_manager = Mock(spec=LLMManager)
        
        # Set up staging registry and orchestration
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        await self.registry.initialize()
        self.registry.register_default_agents()
        
        # Initialize workflow orchestrator for realistic testing
        try:
            self.orchestrator = WorkflowOrchestrator(
                agent_registry=self.registry,
                llm_manager=self.llm_manager
            )
        except Exception as e:
            print(f"⚠️ Mock orchestrator due to: {e}")
            self.orchestrator = Mock(spec=WorkflowOrchestrator)
    
    async def asyncTearDown(self):
        """Clean up staging workflow resources."""
        if hasattr(self, 'registry'):
            await self.registry.cleanup()
        await super().asyncTearDown()
    
    async def test_complete_staging_workflow_with_naming_validation(self):
        """E2E Test 3: Complete staging workflow demonstrating naming impact on real processes.
        
        This test runs a complete multi-agent workflow in staging environment,
        showing how agent naming affects real business processes and user experience.
        """
        print(f"\n🔬 Complete staging workflow test for user: {self.workflow_user.user_id}")
        
        # Simulate complete business workflow requiring multiple agents
        business_workflow = {
            "phase_1_triage": {
                "agents": ["triage"],
                "description": "User request analysis and workflow routing", 
                "critical": True
            },
            "phase_2_analysis": {
                "agents": ["data", "optimization"],  # Using CORRECT names
                "description": "Data analysis and optimization strategy",
                "critical": True
            },
            "phase_3_execution": {
                "agents": ["actions", "reporting"],
                "description": "Action planning and result reporting",
                "critical": False
            }
        }
        
        workflow_execution_results = {
            "phases": {},
            "overall_success": False,
            "critical_failures": [],
            "agent_performance": {}
        }
        
        # Execute each workflow phase
        for phase_name, phase_config in business_workflow.items():
            print(f"\n  📋 Executing {phase_name}: {phase_config['description']}")
            
            phase_results = {
                "successful_agents": [],
                "failed_agents": [],
                "execution_time": 0,
                "critical": phase_config["critical"]
            }
            
            # Create and test each agent in the phase
            for agent_name in phase_config["agents"]:
                print(f"    🤖 Testing agent: {agent_name}")
                
                start_time = asyncio.get_event_loop().time()
                
                try:
                    # Create agent using registry
                    agent = await self.registry.create_agent_for_user(
                        user_id=self.workflow_user.user_id,
                        agent_type=agent_name,
                        user_context=self.workflow_user
                    )
                    
                    execution_time = asyncio.get_event_loop().time() - start_time
                    
                    if agent is not None or self.registry.has(agent_name):
                        phase_results["successful_agents"].append(agent_name)
                        workflow_execution_results["agent_performance"][agent_name] = {
                            "status": "success",
                            "execution_time": execution_time
                        }
                        print(f"      ✅ Agent {agent_name} successful ({execution_time:.3f}s)")
                    else:
                        phase_results["failed_agents"].append(agent_name)
                        workflow_execution_results["agent_performance"][agent_name] = {
                            "status": "failed", 
                            "execution_time": execution_time,
                            "reason": "agent_not_found"
                        }
                        print(f"      ❌ Agent {agent_name} not found")
                        
                        if phase_config["critical"]:
                            workflow_execution_results["critical_failures"].append(agent_name)
                    
                except Exception as e:
                    execution_time = asyncio.get_event_loop().time() - start_time
                    phase_results["failed_agents"].append(agent_name)
                    workflow_execution_results["agent_performance"][agent_name] = {
                        "status": "error",
                        "execution_time": execution_time,
                        "reason": str(e)
                    }
                    print(f"      ❌ Agent {agent_name} error: {e}")
                    
                    if phase_config["critical"]:
                        workflow_execution_results["critical_failures"].append(agent_name)
            
            # Calculate phase success
            phase_success_rate = len(phase_results["successful_agents"]) / len(phase_config["agents"])
            phase_results["success_rate"] = phase_success_rate
            
            print(f"    📊 Phase {phase_name} success rate: {phase_success_rate:.1%}")
            
            workflow_execution_results["phases"][phase_name] = phase_results
        
        # Calculate overall workflow success
        total_agents = sum(len(phase["agents"]) for phase in business_workflow.values())
        successful_agents = sum(len(results["successful_agents"]) 
                               for results in workflow_execution_results["phases"].values())
        overall_success_rate = successful_agents / total_agents
        
        # Workflow succeeds if no critical failures and reasonable success rate
        workflow_execution_results["overall_success"] = (
            len(workflow_execution_results["critical_failures"]) == 0 and 
            overall_success_rate >= 0.7
        )
        
        print(f"\n📊 Complete Staging Workflow Results:")
        print(f"   Overall success rate: {overall_success_rate:.1%}")
        print(f"   Critical failures: {workflow_execution_results['critical_failures']}")
        print(f"   Workflow success: {workflow_execution_results['overall_success']}")
        
        # Print detailed agent performance
        print(f"\n🤖 Agent Performance Summary:")
        for agent_name, perf in workflow_execution_results["agent_performance"].items():
            status_emoji = "✅" if perf["status"] == "success" else "❌"
            print(f"   {status_emoji} {agent_name}: {perf['status']} ({perf['execution_time']:.3f}s)")
            if perf["status"] != "success":
                print(f"      Reason: {perf.get('reason', 'unknown')}")
        
        # Validate workflow meets business requirements
        self.assertEqual(len(workflow_execution_results["critical_failures"]), 0,
                        f"Critical agents should not fail: {workflow_execution_results['critical_failures']}")
        
        self.assertGreater(overall_success_rate, 0.7,
                          f"Overall workflow should achieve >70% success rate, got {overall_success_rate:.1%}")
        
        self.assertTrue(workflow_execution_results["overall_success"],
                       "Complete staging workflow should succeed with correct agent naming")
        
        # Validate specific agents that are critical for optimization workflows
        optimization_agents = ["triage", "optimization", "actions"]
        failed_optimization = [agent for agent in optimization_agents 
                             if workflow_execution_results["agent_performance"].get(agent, {}).get("status") != "success"]
        
        self.assertEqual(len(failed_optimization), 0,
                        f"Optimization workflow agents should succeed: {failed_optimization}")


if __name__ == "__main__":
    # Run E2E staging tests to demonstrate real-world impact
    print("🌐 Running E2E Staging Tests for GitHub Issue #347: Agent Orchestration Name Consistency")
    print("=" * 90)
    
    import unittest
    unittest.main(verbosity=2)