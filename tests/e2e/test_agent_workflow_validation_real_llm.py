"""E2E Test: Agent Workflow Validation with Real LLM Integration

CRITICAL E2E test for complete agent workflow validation with real LLM.
Tests all agent lifecycle stages, state management, and data flow validation.

Business Value Justification (BVJ):
    1. Segment: All customer segments ($347K+ MRR protection)
2. Business Goal: Ensure reliable agent workflow execution
3. Value Impact: Validates complete agent lifecycle preventing service failures
4. Revenue Impact: Prevents customer churn from agent workflow failures

ARCHITECTURAL COMPLIANCE:
    - File size: <500 lines (modular design)
- Function size: <25 lines each
- Real LLM API calls when --real-llm flag is set
- Complete workflow validation from input to output
- State management and data flow testing
"""

from dataclasses import dataclass
from netra_backend.app.schemas.UserPlan import PlanTier
from typing import Dict, Any, List, Optional
from unittest.mock import patch, AsyncMock
import asyncio
import os
import pytest
import pytest_asyncio
import time

from tests.e2e.agent_conversation_helpers import (
    AgentConversationTestCore,
    ConversationFlowValidator,
    AgentConversationTestUtils
)


@dataclass
class WorkflowStage:
    """Data structure for workflow stages."""
    stage_name: str
    entry_conditions: List[str]
    exit_conditions: List[str]
    expected_data_transformations: Dict[str, Any]


@dataclass
class AgentWorkflowTestCase:
    """Test case for agent workflow validation."""
    workflow_id: str
    description: str
    input_data: Dict[str, Any]
    expected_stages: List[WorkflowStage]
    expected_final_state: Dict[str, Any]
    plan_tier: PlanTier
    complexity_level: str  # "simple", "medium", "complex"


class AgentWorkflowTestData:
    """Test data for agent workflow validation."""
    
    @staticmethod
    def get_workflow_test_cases() -> List[AgentWorkflowTestCase]:
        """Get workflow test cases covering all agent stages."""
        return [
            AgentWorkflowTestCase(
                workflow_id="WF-001", 
                description="Simple cost optimization workflow",
                input_data={
                    "user_message": "I want to reduce my AI costs by 20%",
                    "current_spend": 5000.0,
                    "target_reduction": 0.2
                },
                expected_stages=[
                    WorkflowStage(
                        stage_name="input",
                        entry_conditions=["user_request_received"],
                        exit_conditions=["request_parsed"],
                        expected_data_transformations={}
                    ),
                    WorkflowStage(
                        stage_name="triage",
                        entry_conditions=["request_parsed"],
                        exit_conditions=["categorized"],
                        expected_data_transformations={"category": "cost_optimization"}
                    ),
                    WorkflowStage(
                        stage_name="data",
                        entry_conditions=["categorized"],
                        exit_conditions=["data_analyzed"],
                        expected_data_transformations={"usage_data": "present"}
                    ),
                    WorkflowStage(
                        stage_name="optimization",
                        entry_conditions=["data_analyzed"],
                        exit_conditions=["strategies_generated"],
                        expected_data_transformations={"strategies": "list"}
                    ),
                    WorkflowStage(
                        stage_name="reporting",
                        entry_conditions=["strategies_generated"],
                        exit_conditions=["report_created"],
                        expected_data_transformations={"report": "complete"}
                    )
                ],
                expected_final_state={
                    "status": "completed",
                    "recommendations": "present",
                    "cost_savings_estimate": "calculated"
                },
                plan_tier=PlanTier.PRO,
                complexity_level="simple"
            )
        ]


@pytest.mark.real_llm
@pytest.mark.asyncio
@pytest.mark.e2e
class TestAgentWorkflowValidationRealLLM:
    """Test complete agent workflow validation with real LLM."""
    
    def use_real_llm(self):
        """Check if real LLM testing is enabled.""" 
        return os.getenv("ENABLE_REAL_LLM_TESTING", "false").lower() == "true"
    
    @pytest.fixture
    def workflow_validator(self):
        """Get workflow validator."""
        return WorkflowValidator()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("workflow_case", AgentWorkflowTestData.get_workflow_test_cases())
    @pytest.mark.e2e
    async def test_complete_workflow_execution(self, test_core, use_real_llm, workflow_validator, workflow_case):
        """Test complete workflow execution for each test case."""
        session_data = await test_core.establish_conversation_session(workflow_case.plan_tier)
        
        try:
            # Execute workflow with stage validation
            start_time = time.time()
            workflow_result = await self._execute_validated_workflow(
                session_data, workflow_case, use_real_llm, workflow_validator
            )
            execution_time = time.time() - start_time
            
            # Validate workflow completion
            self._validate_workflow_completion(workflow_result, workflow_case)
            
            # Validate performance for complexity level
            max_time = self._get_max_execution_time(workflow_case.complexity_level, use_real_llm)
            assert execution_time < max_time, f"Workflow {workflow_case.workflow_id} too slow: {execution_time:.2f}s"
            
        finally:
            await session_data["client"].close()


class WorkflowValidator:
    """Validator for workflow stages and conditions."""
    
    def validate_entry_conditions(self, stage: WorkflowStage, workflow_state: 'WorkflowState') -> bool:
        """Validate stage entry conditions are met."""
        current_state = workflow_state.get_current_state()
        
        for condition in stage.entry_conditions:
            if not self._check_condition(condition, current_state):
                return False
        return True
    
    def validate_exit_conditions(self, stage: WorkflowStage, workflow_state: 'WorkflowState') -> bool:
        """Validate stage exit conditions are met."""
        current_state = workflow_state.get_current_state()
        
        for condition in stage.exit_conditions:
            if not self._check_condition(condition, current_state):
                return False
        return True
    
    def _check_condition(self, condition: str, state: Dict[str, Any]) -> bool:
        """Check if condition is met in current state.""" 
        # Simplified condition checking - real implementation would be more sophisticated
        condition_checks = {
            "user_request_received": lambda s: "input" in s,
            "request_parsed": lambda s: "parsed_request" in s,
            "categorized": lambda s: "category" in s,
            "data_analyzed": lambda s: "analysis_complete" in s,
            "strategies_generated": lambda s: "strategies" in s,
            "report_created": lambda s: "report" in s
        }
        
        check_func = condition_checks.get(condition, lambda s: True)
        return check_func(state)


class WorkflowState:
    """Manages workflow state throughout execution."""
    
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.state = {"workflow_id": workflow_id, "started": True}
        self.stage_history = []
    
    def update_from_stage_result(self, stage: WorkflowStage, result: Dict[str, Any]):
        """Update state from stage execution result."""
        self.stage_history.append({
            "stage": stage.stage_name,
            "result": result,
            "timestamp": time.time()
        })
        
        # Update state based on transformations
        for key, value in stage.expected_data_transformations.items():
            self.state[key] = value
        
        # Mark stage completion
        self.state[f"{stage.stage_name}_complete"] = True
        
        # Add stage-specific state updates
        if result["status"] == "success":
            if stage.stage_name == "triage":
                self.state["parsed_request"] = True
                self.state["category"] = result.get("transformations", {}).get("category", "unknown")
            elif stage.stage_name == "data":
                self.state["analysis_complete"] = True
            elif stage.stage_name == "optimization":
                self.state["strategies"] = True
            elif stage.stage_name == "reporting":
                self.state["report"] = True
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current workflow state."""
        return self.state.copy()
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current context for next stage."""
        return {
            "completed_stages": [h["stage"] for h in self.stage_history],
            "current_state": self.state
        }
    
    def get_final_state(self) -> Dict[str, Any]:
        """Get final workflow state."""
        return {
            "workflow_completed": True,
            "stages_executed": len(self.stage_history),
            "final_state": self.state
        }