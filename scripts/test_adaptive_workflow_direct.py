#!/usr/bin/env python3
"""
Direct test of the adaptive workflow without going through the API.
Tests the workflow orchestrator directly with different data sufficiency scenarios.
"""

import asyncio
import json
from typing import Dict, Any
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class DirectWorkflowTester:
    """Test the workflow orchestrator directly."""
    
    def __init__(self):
        self.orchestrator = None
        
    async def setup(self):
        """Set up the test environment."""
        # Create mock dependencies
        mock_registry = Mock()
        mock_execution = Mock()
        mock_websocket = Mock()
        
        # Create the orchestrator
        self.orchestrator = WorkflowOrchestrator(
            agent_registry=mock_registry,
            execution_engine=mock_execution,
            websocket_manager=mock_websocket
        )
        
        # Mock the agent execution to return test results
        self.orchestrator._execute_workflow_step = AsyncMock(side_effect=self._mock_execute_step)
        
        print("[U+2713] Workflow orchestrator initialized")
        
    async def _mock_execute_step(self, context, step):
        """Mock execution of a workflow step."""
        agent_name = step.agent_name
        
        # Return mock results based on agent type
        if agent_name == "triage":
            # Return triage result based on the user request
            user_request = context.user_prompt
            if "10,000 requests daily" in user_request:
                data_sufficiency = "sufficient"
            elif "5000 daily requests" in user_request:
                data_sufficiency = "partial"
            else:
                data_sufficiency = "insufficient"
                
            return Mock(
                success=True,
                result={
                    "category": "Workload Analysis",
                    "data_sufficiency": data_sufficiency,
                    "priority": "high",
                    "key_parameters": {
                        "workload_type": "inference",
                        "optimization_focus": "cost"
                    }
                },
                agent_name="triage",
                error=None
            )
        elif agent_name == "data_helper":
            return Mock(
                success=True,
                result={
                    "data_request": "Please provide the following data for optimization analysis:\n"
                                   "1. Current LLM model details\n"
                                   "2. Request volume metrics\n"
                                   "3. Latency measurements\n"
                                   "4. Cost breakdown\n"
                                   "5. Quality metrics"
                },
                agent_name="data_helper",
                error=None
            )
        else:
            # Return generic success for other agents
            return Mock(
                success=True,
                result={"status": "completed", "agent": agent_name},
                agent_name=agent_name,
                error=None
            )
    
    async def test_scenario(self, name: str, user_request: str, expected_sufficiency: str):
        """Test a specific scenario."""
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"Expected Data Sufficiency: {expected_sufficiency}")
        print(f"Request: {user_request[:100]}...")
        print(f"{'='*60}")
        
        # Create execution context
        context = AgentExecutionContext(
            thread_id=f"test-thread-{name.lower().replace(' ', '-')}",
            run_id=f"test-run-{name.lower().replace(' ', '-')}",
            user_prompt=user_request,
            user_id="test-user",
            stream_updates=False,
            state={}
        )
        
        try:
            # Execute the workflow
            results = await self.orchestrator.execute_standard_workflow(context)
            
            # Analyze results
            agent_sequence = [r.agent_name for r in results if r]
            
            print(f"[U+2713] Workflow executed successfully")
            print(f"  Agent sequence: {'  ->  '.join(agent_sequence)}")
            
            # Check if the workflow matches expected pattern
            if expected_sufficiency == "sufficient":
                expected_agents = ["triage", "optimization", "data", "actions", "reporting"]
            elif expected_sufficiency == "partial":
                expected_agents = ["triage", "optimization", "actions", "data_helper", "reporting"]
            else:  # insufficient
                expected_agents = ["triage", "data_helper"]
            
            # Verify the workflow followed the expected path
            if agent_sequence[:len(expected_agents)] == expected_agents:
                print(f"[U+2713] Workflow followed expected path for {expected_sufficiency} data")
                return True
            else:
                print(f"[U+2717] Unexpected workflow path")
                print(f"  Expected: {expected_agents}")
                print(f"  Got: {agent_sequence}")
                return False
                
        except Exception as e:
            print(f"[U+2717] Error executing workflow: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        print("\n" + "="*70)
        print("DIRECT ADAPTIVE WORKFLOW TEST")
        print("="*70)
        
        await self.setup()
        
        # Test scenarios
        scenarios = [
            {
                "name": "Sufficient Data Scenario",
                "request": "I have a chatbot using GPT-4 serving 10,000 requests daily. "
                           "Average latency is 800ms, cost per request is $0.05. "
                           "Peak hours are 9-11 AM and 2-4 PM. Quality score is 4.2/5.",
                "expected": "sufficient"
            },
            {
                "name": "Partial Data Scenario",
                "request": "We're using LLMs for customer service with about 5000 daily requests. "
                           "Response times feel slow. Need to reduce costs.",
                "expected": "partial"
            },
            {
                "name": "Insufficient Data Scenario",
                "request": "Help me optimize my AI workload",
                "expected": "insufficient"
            }
        ]
        
        results = []
        for scenario in scenarios:
            success = await self.test_scenario(
                scenario["name"],
                scenario["request"],
                scenario["expected"]
            )
            results.append({
                "name": scenario["name"],
                "success": success
            })
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        for r in results:
            status = "[U+2713]" if r["success"] else "[U+2717]"
            print(f"{status} {r['name']}")
        
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        print(f"\n{'='*70}")
        print(f"RESULT: {success_count}/{total_count} tests passed")
        print(f"{'='*70}")
        
        return success_count == total_count


async def main():
    """Main test function."""
    tester = DirectWorkflowTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    print("Starting Direct Workflow Tests...")
    exit_code = asyncio.run(main())
    sys.exit(exit_code)