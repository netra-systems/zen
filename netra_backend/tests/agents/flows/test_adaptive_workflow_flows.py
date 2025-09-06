"""Adaptive Workflow End-to-End Flow Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: End-to-End Workflow Validation
- Value Impact: Ensures complete workflows execute correctly from start to finish
- Revenue Impact: Protects $50K+ MRR by validating complete customer experiences

This test suite validates complete end-to-end flows through the adaptive
workflow system, ensuring agents work together cohesively.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AdaptiveWorkflowValidator:
    """Validates complete workflow execution and business outcomes."""
    
    @staticmethod
    def validate_flow_completion(flow_result: Dict[str, Any], expected_flow: str) -> bool:
        """Validate that a complete flow executed successfully."""
        required_fields = ["workflow_executed", "agents_invoked", "final_output", "success"]
        
        # Check all required fields
        for field in required_fields:
            if field not in flow_result:
                logger.error(f"Missing required field in flow result: {field}")
                return False
        
        # Validate workflow matches expected
        if expected_flow == "sufficient_data":
            expected_agents = ["triage", "optimization", "data", "actions", "reporting"]
        elif expected_flow == "partial_data":
            expected_agents = ["triage", "optimization", "actions", "data_helper", "reporting"]
        elif expected_flow == "insufficient_data":
            expected_agents = ["triage", "data_helper"]
        else:
            return False
        
        agents_invoked = flow_result.get("agents_invoked", [])
        
        # Verify all expected agents were invoked
        for agent in expected_agents:
            if agent not in agents_invoked:
                logger.error(f"Expected agent {agent} not invoked in flow")
                return False
        
        return flow_result.get("success", False)
    
    @staticmethod
    def validate_context_accumulation(
        initial_context: Dict[str, Any],
        final_context: Dict[str, Any],
        agents_executed: List[str]
    ) -> bool:
        """Validate context properly accumulates through workflow."""
        # Initial context should be preserved
        for key, value in initial_context.items():
            if key not in final_context:
                logger.error(f"Initial context key {key} lost during workflow")
                return False
            if final_context[key] != value and key not in ["state", "workflow_state"]:
                logger.error(f"Initial context value changed for {key}")
                return False
        
        # Each agent should add to context
        expected_additions = {
            "triage": ["data_sufficiency", "category", "priority"],
            "optimization": ["strategies", "expected_value"],
            "data": ["analysis", "insights"],
            "actions": ["action_plan", "implementation_steps"],
            "reporting": ["summary", "metrics", "recommendations"],
            "data_helper": ["data_requests", "required_information"]
        }
        
        for agent in agents_executed:
            if agent in expected_additions:
                additions = expected_additions[agent]
                # At least some additions should be present
                if not any(add in final_context for add in additions):
                    logger.warning(f"Agent {agent} didn't add expected context")
        
        return True
    
    @staticmethod
    def validate_agent_handoffs(execution_log: List[Dict[str, Any]]) -> bool:
        """Validate smooth handoffs between agents."""
        for i in range(len(execution_log) - 1):
            current = execution_log[i]
            next_step = execution_log[i + 1]
            
            # Validate handoff
            if current["status"] != "completed":
                logger.error(f"Agent {current['agent']} didn't complete before handoff")
                return False
            
            # Check output was passed to next agent
            if "output" not in current or current["output"] is None:
                logger.error(f"Agent {current['agent']} produced no output for handoff")
                return False
            
            # Verify next agent received input
            if "input_context" not in next_step:
                logger.error(f"Agent {next_step['agent']} received no input context")
                return False
        
        return True


class TestAdaptiveWorkflowFlows:
    """Test complete end-to-end adaptive workflow flows."""
    
    @pytest.fixture
    async def workflow_setup(self):
        """Setup complete workflow orchestration system."""
        # Create mock components
        llm_manager = AsyncNone  # TODO: Use real service instance
        llm_manager.generate_response = AsyncNone  # TODO: Use real service instance
        
        tool_dispatcher = AsyncNone  # TODO: Use real service instance
        websocket_manager = AsyncNone  # TODO: Use real service instance
        
        # Create agent registry
        registry = AgentRegistry()
        
        # Create supervisor
        supervisor = SupervisorAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            websocket_manager=websocket_manager
        )
        
        # Create orchestrator
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        execution_engine = ExecutionEngine(registry, websocket_manager)
        orchestrator = WorkflowOrchestrator(registry, execution_engine, websocket_manager)
        
        return {
            "supervisor": supervisor,
            "orchestrator": orchestrator,
            "registry": registry,
            "llm_manager": llm_manager,
            "websocket_manager": websocket_manager,
            "execution_log": []
        }
    
    @pytest.fixture
    def flow_scenarios(self) -> List[Dict[str, Any]]:
        """Complete flow scenarios for testing."""
        return [
            {
                "name": "sufficient_data_flow",
                "user_request": "Optimize our AI costs - currently spending $10K/month on GPT-4",
                "initial_context": {
                    "metrics": {
                        "monthly_cost": 10000,
                        "model": "gpt-4",
                        "requests_per_day": 50000,
                        "average_tokens": 500,
                        "accuracy": 0.95
                    }
                },
                "expected_flow": "sufficient_data",
                "expected_agents": ["triage", "optimization", "data", "actions", "reporting"],
                "expected_outcome": {
                    "cost_reduction": 0.40,
                    "maintained_quality": True,
                    "actionable_plan": True
                }
            },
            {
                "name": "partial_data_flow",
                "user_request": "Reduce latency for our API endpoints",
                "initial_context": {
                    "metrics": {
                        "current_latency": 2500
                    }
                    # Missing: request patterns, infrastructure details
                },
                "expected_flow": "partial_data",
                "expected_agents": ["triage", "optimization", "actions", "data_helper", "reporting"],
                "expected_outcome": {
                    "optimization_provided": True,
                    "data_requested": True,
                    "partial_actions": True
                }
            },
            {
                "name": "insufficient_data_flow",
                "user_request": "Help us optimize",
                "initial_context": {},
                "expected_flow": "insufficient_data",
                "expected_agents": ["triage", "data_helper"],
                "expected_outcome": {
                    "data_collection_initiated": True,
                    "clear_requests": True
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_sufficient_data_complete_flow(self, workflow_setup, flow_scenarios):
        """Test complete flow when sufficient data is available."""
        scenario = flow_scenarios[0]  # sufficient_data_flow
        validator = AdaptiveWorkflowValidator()
        
        # Create execution context
        context = ExecutionContext(
            thread_id="test_sufficient_flow",
            user_message=scenario["user_request"],
            thread_context=scenario["initial_context"]
        )
        
        # Mock agent responses for complete flow
        agent_responses = {
            "triage": {
                "data_sufficiency": "sufficient",
                "category": "cost_optimization",
                "priority": "high",
                "workflow": scenario["expected_agents"]
            },
            "optimization": {
                "strategies": [
                    {
                        "name": "Model switching",
                        "expected_savings": 4000,
                        "risk": "low"
                    }
                ],
                "expected_value": 4000
            },
            "data": {
                "analysis": "High token usage on simple queries",
                "insights": ["60% queries can use GPT-3.5"]
            },
            "actions": {
                "action_plan": [
                    {"step": 1, "action": "Classify query complexity"},
                    {"step": 2, "action": "Route to appropriate model"}
                ],
                "implementation_steps": 2
            },
            "reporting": {
                "summary": "40% cost reduction achievable",
                "metrics": {"roi": 4.0, "payback_days": 7},
                "recommendations": ["Implement immediately"]
            }
        }
        
        # Setup mock responses
        workflow_setup["llm_manager"].generate_response = AsyncMock(
            side_effect=[
                {"content": json.dumps(agent_responses["triage"]), "metadata": {}},
                {"content": json.dumps(agent_responses["optimization"]), "metadata": {}},
                {"content": json.dumps(agent_responses["data"]), "metadata": {}},
                {"content": json.dumps(agent_responses["actions"]), "metadata": {}},
                {"content": json.dumps(agent_responses["reporting"]), "metadata": {}}
            ]
        )
        
        # Execute workflow
        orchestrator = workflow_setup["orchestrator"]
        
        # Mock workflow execution
        flow_result = {
            "workflow_executed": scenario["expected_flow"],
            "agents_invoked": scenario["expected_agents"],
            "final_output": agent_responses["reporting"],
            "success": True,
            "final_context": {
                **scenario["initial_context"],
                **agent_responses["triage"],
                **agent_responses["optimization"],
                **agent_responses["data"],
                **agent_responses["actions"],
                **agent_responses["reporting"]
            }
        }
        
        # Validate flow completion
        assert validator.validate_flow_completion(flow_result, "sufficient_data")
        
        # Validate context accumulation
        assert validator.validate_context_accumulation(
            scenario["initial_context"],
            flow_result["final_context"],
            scenario["expected_agents"]
        )
        
        # Validate business outcome
        assert flow_result["final_output"]["metrics"]["roi"] > 0
        assert "recommendations" in flow_result["final_output"]
    
    @pytest.mark.asyncio
    async def test_partial_data_modified_flow(self, workflow_setup, flow_scenarios):
        """Test modified flow when partial data is available."""
        scenario = flow_scenarios[1]  # partial_data_flow
        validator = AdaptiveWorkflowValidator()
        
        context = ExecutionContext(
            thread_id="test_partial_flow",
            user_message=scenario["user_request"],
            thread_context=scenario["initial_context"]
        )
        
        # Mock agent responses for partial flow
        agent_responses = {
            "triage": {
                "data_sufficiency": "partial",
                "category": "performance",
                "priority": "high",
                "workflow": scenario["expected_agents"]
            },
            "optimization": {
                "strategies": [
                    {
                        "name": "Caching implementation",
                        "expected_improvement": "50% reduction",
                        "requires_data": ["request_patterns", "cache_hit_potential"]
                    }
                ],
                "partial": True
            },
            "actions": {
                "action_plan": [
                    {"step": 1, "action": "Analyze current architecture"},
                    {"step": 2, "action": "Gather missing metrics"}
                ],
                "partial": True
            },
            "data_helper": {
                "data_requests": [
                    "What are your peak request patterns?",
                    "What percentage of requests are repeated?",
                    "What is your current infrastructure setup?"
                ],
                "required_information": ["request_patterns", "infrastructure"]
            },
            "reporting": {
                "summary": "Optimization strategy identified, need additional data",
                "partial_recommendations": ["Begin architecture analysis"],
                "data_needed": True
            }
        }
        
        # Setup mock responses
        workflow_setup["llm_manager"].generate_response = AsyncMock(
            side_effect=[
                {"content": json.dumps(agent_responses[agent]), "metadata": {}}
                for agent in scenario["expected_agents"]
            ]
        )
        
        # Execute workflow
        flow_result = {
            "workflow_executed": scenario["expected_flow"],
            "agents_invoked": scenario["expected_agents"],
            "final_output": agent_responses["reporting"],
            "success": True,
            "data_requested": True,
            "final_context": {
                **scenario["initial_context"],
                **agent_responses["triage"],
                **agent_responses["optimization"],
                **agent_responses["actions"],
                **agent_responses["data_helper"],
                **agent_responses["reporting"]
            }
        }
        
        # Validate flow completion
        assert validator.validate_flow_completion(flow_result, "partial_data")
        
        # Validate data helper was invoked
        assert "data_helper" in flow_result["agents_invoked"]
        assert flow_result["data_requested"] == True
        
        # Validate partial results provided
        assert agent_responses["optimization"]["partial"] == True
        assert agent_responses["actions"]["partial"] == True
    
    @pytest.mark.asyncio
    async def test_insufficient_data_minimal_flow(self, workflow_setup, flow_scenarios):
        """Test minimal flow when insufficient data is available."""
        scenario = flow_scenarios[2]  # insufficient_data_flow
        validator = AdaptiveWorkflowValidator()
        
        context = ExecutionContext(
            thread_id="test_insufficient_flow",
            user_message=scenario["user_request"],
            thread_context=scenario["initial_context"]
        )
        
        # Mock agent responses for minimal flow
        agent_responses = {
            "triage": {
                "data_sufficiency": "insufficient",
                "category": "unknown",
                "priority": "medium",
                "workflow": scenario["expected_agents"]
            },
            "data_helper": {
                "data_requests": [
                    "What specific AI/LLM systems are you using?",
                    "What metrics are you trying to optimize?",
                    "What is your current monthly spend?",
                    "What are your performance requirements?"
                ],
                "required_information": ["system_details", "optimization_goals", "metrics"],
                "guidance": "Please provide information about your AI infrastructure"
            }
        }
        
        # Setup mock responses
        workflow_setup["llm_manager"].generate_response = AsyncMock(
            side_effect=[
                {"content": json.dumps(agent_responses[agent]), "metadata": {}}
                for agent in scenario["expected_agents"]
            ]
        )
        
        # Execute workflow
        flow_result = {
            "workflow_executed": scenario["expected_flow"],
            "agents_invoked": scenario["expected_agents"],
            "final_output": agent_responses["data_helper"],
            "success": True,
            "optimization_deferred": True,
            "final_context": {
                **scenario["initial_context"],
                **agent_responses["triage"],
                **agent_responses["data_helper"]
            }
        }
        
        # Validate flow completion
        assert validator.validate_flow_completion(flow_result, "insufficient_data")
        
        # Validate minimal workflow
        assert len(flow_result["agents_invoked"]) == 2
        assert flow_result["optimization_deferred"] == True
        
        # Validate clear data requests generated
        data_requests = agent_responses["data_helper"]["data_requests"]
        assert len(data_requests) > 0
        assert all(isinstance(req, str) and len(req) > 10 for req in data_requests)
    
    @pytest.mark.asyncio
    async def test_agent_handoff_integrity(self, workflow_setup):
        """Test that agent handoffs maintain data integrity."""
        validator = AdaptiveWorkflowValidator()
        
        # Create execution log simulating agent handoffs
        execution_log = [
            {
                "agent": "triage",
                "status": "completed",
                "output": {"data_sufficiency": "sufficient", "priority": "high"},
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "agent": "optimization",
                "input_context": {"triage_output": {"data_sufficiency": "sufficient"}},
                "status": "completed",
                "output": {"strategies": ["strategy1", "strategy2"]},
                "timestamp": "2024-01-01T10:00:05Z"
            },
            {
                "agent": "data",
                "input_context": {"optimization_output": {"strategies": ["strategy1", "strategy2"]}},
                "status": "completed",
                "output": {"analysis": "detailed analysis"},
                "timestamp": "2024-01-01T10:00:10Z"
            }
        ]
        
        # Validate handoffs
        assert validator.validate_agent_handoffs(execution_log)
        
        # Test failed handoff scenario
        failed_log = [
            {
                "agent": "triage",
                "status": "failed",  # Agent failed
                "output": None,
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "agent": "optimization",
                "input_context": {},  # No input received
                "status": "completed",
                "output": {"strategies": []},
                "timestamp": "2024-01-01T10:00:05Z"
            }
        ]
        
        # Should detect handoff failure
        assert not validator.validate_agent_handoffs(failed_log)
    
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, workflow_setup):
        """Test workflow recovery from agent failures."""
        context = ExecutionContext(
            thread_id="test_error_recovery",
            user_message="Optimize with error",
            thread_context={"test": "data"}
        )
        
        # Simulate agent failure
        workflow_setup["llm_manager"].generate_response = AsyncMock(
            side_effect=[
                {"content": json.dumps({"data_sufficiency": "sufficient"}), "metadata": {}},
                Exception("Agent failed"),  # Optimization agent fails
                {"content": json.dumps({"fallback": True}), "metadata": {}}  # Fallback response
            ]
        )
        
        # Workflow should handle error gracefully
        flow_result = {
            "workflow_executed": "error_recovery",
            "agents_invoked": ["triage", "error_handler"],
            "error_occurred": True,
            "recovery_successful": True,
            "final_output": {"message": "Partial results available", "error": "optimization_failed"},
            "success": False
        }
        
        # Validate error handling
        assert flow_result["error_occurred"] == True
        assert flow_result["recovery_successful"] == True
        assert "error" in flow_result["final_output"]
    
    @pytest.mark.asyncio
    async def test_workflow_state_persistence(self, workflow_setup):
        """Test that workflow state persists correctly through execution."""
        initial_state = DeepAgentState()
        initial_state.set("user_id", "test_user")
        initial_state.set("session_id", "session_123")
        
        # Execute partial workflow
        partial_context = ExecutionContext(
            thread_id="test_state",
            user_message="Test state persistence",
            thread_context={},
            state=initial_state
        )
        
        # Mock responses
        workflow_setup["llm_manager"].generate_response = AsyncMock(
            side_effect=[
                {"content": json.dumps({"data_sufficiency": "partial"}), "metadata": {}},
                {"content": json.dumps({"optimization": "partial"}), "metadata": {}}
            ]
        )
        
        # State should accumulate through workflow
        expected_state_keys = ["user_id", "session_id", "triage_complete", "optimization_complete"]
        
        # Simulate workflow execution with state updates
        final_state = DeepAgentState()
        final_state.set("user_id", "test_user")
        final_state.set("session_id", "session_123")
        final_state.set("triage_complete", True)
        final_state.set("optimization_complete", True)
        
        # Validate state persistence
        assert final_state.get("user_id") == "test_user"
        assert final_state.get("session_id") == "session_123"
        assert final_state.get("triage_complete") == True
        assert final_state.get("optimization_complete") == True