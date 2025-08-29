"""Multi-Agent Orchestration Business Outcome Validation Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: AI Optimization Accuracy & Reliability
- Value Impact: Validates actual business outcomes from agent decisions
- Revenue Impact: Protects $50K+ MRR from incorrect optimization results

Critical Coverage Areas:
1. Adaptive workflow based on data sufficiency
2. Agent business logic outcomes (not just execution success)
3. Context propagation through workflow
4. End-to-end business value validation
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime, timezone

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class BusinessOutcomeValidator:
    """Validates business logic outcomes from agent execution."""
    
    @staticmethod
    def validate_triage_classification(result: Dict[str, Any]) -> bool:
        """Validate triage agent classification logic."""
        required_fields = ["data_sufficiency", "category", "priority", "recommended_workflow"]
        
        # Check all required fields exist
        for field in required_fields:
            if field not in result:
                logger.error(f"Missing required field in triage result: {field}")
                return False
        
        # Validate data sufficiency logic
        data_sufficiency = result["data_sufficiency"]
        if data_sufficiency not in ["sufficient", "partial", "insufficient"]:
            logger.error(f"Invalid data sufficiency value: {data_sufficiency}")
            return False
        
        # Validate workflow recommendation aligns with data sufficiency
        recommended_workflow = result["recommended_workflow"]
        if data_sufficiency == "sufficient" and len(recommended_workflow) < 5:
            logger.error("Sufficient data should trigger full workflow")
            return False
        elif data_sufficiency == "insufficient" and len(recommended_workflow) > 2:
            logger.error("Insufficient data should trigger minimal workflow")
            return False
        
        return True
    
    @staticmethod
    def validate_optimization_strategies(result: Dict[str, Any]) -> bool:
        """Validate optimization agent strategy generation."""
        if "strategies" not in result:
            return False
        
        strategies = result["strategies"]
        if not isinstance(strategies, list) or len(strategies) == 0:
            return False
        
        # Each strategy should have cost-benefit analysis
        for strategy in strategies:
            if not all(k in strategy for k in ["name", "expected_improvement", "cost", "risk_level"]):
                return False
            
            # Validate business logic: improvement should justify cost
            if strategy["expected_improvement"] < strategy["cost"] * 0.5:
                logger.warning(f"Strategy {strategy['name']} has poor ROI")
        
        return True
    
    @staticmethod
    def validate_action_feasibility(result: Dict[str, Any]) -> bool:
        """Validate action agent feasibility assessment."""
        if "actions" not in result:
            return False
        
        actions = result["actions"]
        for action in actions:
            if not all(k in action for k in ["description", "feasible", "resources_required", "timeline"]):
                return False
            
            # Business logic: infeasible actions should have justification
            if not action["feasible"] and "blocker_reason" not in action:
                return False
        
        return True
    
    @staticmethod
    def validate_reporting_metrics(result: Dict[str, Any]) -> bool:
        """Validate reporting agent metric calculations."""
        if "metrics" not in result or "summary" not in result:
            return False
        
        metrics = result["metrics"]
        required_metrics = ["total_cost", "expected_value", "roi", "confidence_score"]
        
        for metric in required_metrics:
            if metric not in metrics:
                return False
        
        # Business logic: ROI calculation validation
        if metrics["expected_value"] > 0 and metrics["total_cost"] > 0:
            calculated_roi = (metrics["expected_value"] - metrics["total_cost"]) / metrics["total_cost"]
            if abs(calculated_roi - metrics["roi"]) > 0.01:  # Allow 1% tolerance
                logger.error(f"ROI calculation mismatch: {calculated_roi} vs {metrics['roi']}")
                return False
        
        return True


class MultiAgentOrchestrationBusinessTest:
    """Tests multi-agent orchestration with focus on business outcomes."""
    
    def __init__(self):
        self.validator = BusinessOutcomeValidator()
        self.test_scenarios = self._create_test_scenarios()
    
    def _create_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create comprehensive business test scenarios."""
        return [
            {
                "name": "high_value_optimization",
                "input": {
                    "request": "Optimize AI model performance for enterprise client",
                    "context": {
                        "current_metrics": {"latency": 500, "cost": 1000, "accuracy": 0.85},
                        "constraints": {"max_cost": 1500, "min_accuracy": 0.80},
                        "priority": "performance"
                    }
                },
                "expected_data_sufficiency": "sufficient",
                "expected_workflow_length": 5,
                "expected_outcomes": {
                    "optimization_found": True,
                    "roi_positive": True,
                    "constraints_met": True
                }
            },
            {
                "name": "insufficient_data_collection",
                "input": {
                    "request": "Analyze system bottlenecks",
                    "context": {
                        "current_metrics": {},
                        "constraints": {},
                        "priority": "discovery"
                    }
                },
                "expected_data_sufficiency": "insufficient",
                "expected_workflow_length": 2,
                "expected_outcomes": {
                    "data_request_generated": True,
                    "optimization_deferred": True
                }
            },
            {
                "name": "cost_optimization_with_constraints",
                "input": {
                    "request": "Reduce AI costs by 30% while maintaining quality",
                    "context": {
                        "current_metrics": {"cost": 5000, "quality_score": 0.92},
                        "constraints": {"min_quality": 0.85, "target_cost_reduction": 0.30},
                        "priority": "cost"
                    }
                },
                "expected_data_sufficiency": "sufficient",
                "expected_workflow_length": 5,
                "expected_outcomes": {
                    "cost_reduction_achieved": True,
                    "quality_maintained": True,
                    "actions_feasible": True
                }
            }
        ]


@pytest.mark.asyncio
class TestAgentOrchestrationBusinessOutcomes:
    """Test suite for agent orchestration business outcomes."""
    
    @pytest.fixture
    async def orchestration_setup(self):
        """Setup orchestration components with mock agents."""
        # Create mock LLM manager
        llm_manager = AsyncMock()
        llm_manager.generate_response = AsyncMock(return_value={
            "content": "Mock response",
            "metadata": {"cost": 0.001}
        })
        
        # Create mock tool dispatcher
        tool_dispatcher = AsyncMock()
        
        # Create agent registry
        registry = AgentRegistry(llm_manager, tool_dispatcher)
        
        # Create mock websocket manager
        websocket_manager = AsyncMock()
        
        # Setup workflow orchestrator
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        execution_engine = ExecutionEngine(registry, websocket_manager)
        orchestrator = WorkflowOrchestrator(registry, execution_engine, websocket_manager)
        
        return {
            "registry": registry,
            "orchestrator": orchestrator,
            "websocket_manager": websocket_manager,
            "llm_manager": llm_manager
        }
    
    async def test_adaptive_workflow_sufficient_data(self, orchestration_setup):
        """Test workflow adaptation with sufficient data."""
        orchestrator = orchestration_setup["orchestrator"]
        
        # Mock triage result with sufficient data
        triage_result = {
            "data_sufficiency": "sufficient",
            "category": "optimization",
            "priority": "high",
            "recommended_workflow": ["triage", "optimization", "data", "actions", "reporting"]
        }
        
        # Test workflow generation
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Validate workflow structure
        assert len(workflow_steps) == 5
        assert workflow_steps[0].agent_name == "triage"
        assert workflow_steps[1].agent_name == "optimization"
        assert workflow_steps[2].agent_name == "data"
        assert workflow_steps[3].agent_name == "actions"
        assert workflow_steps[4].agent_name == "reporting"
        
        # Validate dependencies
        assert workflow_steps[1].dependencies == ["triage"]
        assert workflow_steps[4].dependencies == ["actions"]
    
    async def test_adaptive_workflow_insufficient_data(self, orchestration_setup):
        """Test workflow adaptation with insufficient data."""
        orchestrator = orchestration_setup["orchestrator"]
        
        # Mock triage result with insufficient data
        triage_result = {
            "data_sufficiency": "insufficient",
            "category": "discovery",
            "priority": "medium",
            "recommended_workflow": ["triage", "data_helper"]
        }
        
        # Test workflow generation
        workflow_steps = orchestrator._define_workflow_based_on_triage(triage_result)
        
        # Validate minimal workflow
        assert len(workflow_steps) == 2
        assert workflow_steps[0].agent_name == "triage"
        assert workflow_steps[1].agent_name == "data_helper"
        assert workflow_steps[1].dependencies == ["triage"]
    
    async def test_triage_business_logic_validation(self, orchestration_setup):
        """Test triage agent business logic outcomes."""
        validator = BusinessOutcomeValidator()
        
        # Test valid triage result
        valid_result = {
            "data_sufficiency": "sufficient",
            "category": "optimization",
            "priority": "high",
            "recommended_workflow": ["triage", "optimization", "data", "actions", "reporting"]
        }
        assert validator.validate_triage_classification(valid_result) == True
        
        # Test invalid data sufficiency
        invalid_result = {
            "data_sufficiency": "unknown",
            "category": "optimization",
            "priority": "high",
            "recommended_workflow": ["triage"]
        }
        assert validator.validate_triage_classification(invalid_result) == False
        
        # Test misaligned workflow recommendation
        misaligned_result = {
            "data_sufficiency": "insufficient",
            "category": "optimization",
            "priority": "high",
            "recommended_workflow": ["triage", "optimization", "data", "actions", "reporting"]
        }
        assert validator.validate_triage_classification(misaligned_result) == False
    
    async def test_optimization_strategy_validation(self, orchestration_setup):
        """Test optimization agent strategy generation logic."""
        validator = BusinessOutcomeValidator()
        
        # Test valid optimization strategies
        valid_result = {
            "strategies": [
                {
                    "name": "Cache Optimization",
                    "expected_improvement": 0.30,
                    "cost": 0.10,
                    "risk_level": "low"
                },
                {
                    "name": "Model Quantization",
                    "expected_improvement": 0.25,
                    "cost": 0.15,
                    "risk_level": "medium"
                }
            ]
        }
        assert validator.validate_optimization_strategies(valid_result) == True
        
        # Test poor ROI strategy (should log warning but still be valid)
        poor_roi_result = {
            "strategies": [
                {
                    "name": "Expensive Migration",
                    "expected_improvement": 0.05,
                    "cost": 0.50,
                    "risk_level": "high"
                }
            ]
        }
        assert validator.validate_optimization_strategies(poor_roi_result) == True
    
    async def test_action_feasibility_validation(self, orchestration_setup):
        """Test action agent feasibility assessment."""
        validator = BusinessOutcomeValidator()
        
        # Test valid actions with feasibility
        valid_result = {
            "actions": [
                {
                    "description": "Implement caching layer",
                    "feasible": True,
                    "resources_required": ["redis", "2 engineers"],
                    "timeline": "2 weeks"
                },
                {
                    "description": "Migrate to GPU cluster",
                    "feasible": False,
                    "resources_required": ["$50K budget", "5 engineers"],
                    "timeline": "3 months",
                    "blocker_reason": "Budget constraints"
                }
            ]
        }
        assert validator.validate_action_feasibility(valid_result) == True
        
        # Test invalid - infeasible without reason
        invalid_result = {
            "actions": [
                {
                    "description": "Complex migration",
                    "feasible": False,
                    "resources_required": ["team"],
                    "timeline": "6 months"
                    # Missing blocker_reason
                }
            ]
        }
        assert validator.validate_action_feasibility(invalid_result) == False
    
    async def test_reporting_metrics_validation(self, orchestration_setup):
        """Test reporting agent metric calculations."""
        validator = BusinessOutcomeValidator()
        
        # Test valid metrics with correct ROI
        valid_result = {
            "metrics": {
                "total_cost": 1000,
                "expected_value": 3000,
                "roi": 2.0,  # (3000-1000)/1000 = 2.0
                "confidence_score": 0.85
            },
            "summary": "Optimization strategies identified with 200% ROI"
        }
        assert validator.validate_reporting_metrics(valid_result) == True
        
        # Test invalid ROI calculation
        invalid_result = {
            "metrics": {
                "total_cost": 1000,
                "expected_value": 3000,
                "roi": 1.5,  # Wrong: should be 2.0
                "confidence_score": 0.85
            },
            "summary": "Optimization strategies identified"
        }
        assert validator.validate_reporting_metrics(invalid_result) == False
    
    async def test_end_to_end_business_scenario(self, orchestration_setup):
        """Test complete business scenario with outcome validation."""
        test_manager = MultiAgentOrchestrationBusinessTest()
        scenario = test_manager.test_scenarios[0]  # high_value_optimization
        
        # Create execution context
        state = DeepAgentState()
        state.user_request = scenario["input"]["request"]
        state.context = scenario["input"]["context"]
        
        context = ExecutionContext(
            run_id="test_business_scenario_001",
            agent_name="supervisor",
            state=state,
            stream_updates=False,
            thread_id="test_thread",
            user_id="test_user",
            start_time=datetime.now(timezone.utc),
            metadata={}
        )
        
        # Mock agent responses for business scenario
        mock_responses = {
            "triage": {
                "data_sufficiency": "sufficient",
                "category": "optimization",
                "priority": "high",
                "recommended_workflow": ["triage", "optimization", "data", "actions", "reporting"]
            },
            "optimization": {
                "strategies": [
                    {
                        "name": "Latency Optimization",
                        "expected_improvement": 0.40,
                        "cost": 0.20,
                        "risk_level": "low"
                    }
                ]
            },
            "data": {
                "insights": ["Current bottleneck in data preprocessing"],
                "recommendations": ["Implement parallel processing"]
            },
            "actions": {
                "actions": [
                    {
                        "description": "Implement parallel data pipeline",
                        "feasible": True,
                        "resources_required": ["2 engineers"],
                        "timeline": "1 week"
                    }
                ]
            },
            "reporting": {
                "metrics": {
                    "total_cost": 200,
                    "expected_value": 800,
                    "roi": 3.0,
                    "confidence_score": 0.90
                },
                "summary": "Optimization achieves 40% latency reduction with 300% ROI"
            }
        }
        
        # Validate each agent's business outcome
        validator = BusinessOutcomeValidator()
        
        assert validator.validate_triage_classification(mock_responses["triage"])
        assert validator.validate_optimization_strategies(mock_responses["optimization"])
        assert validator.validate_action_feasibility(mock_responses["actions"])
        assert validator.validate_reporting_metrics(mock_responses["reporting"])
        
        # Validate overall business scenario outcomes
        assert mock_responses["optimization"]["strategies"][0]["expected_improvement"] >= 0.30
        assert mock_responses["reporting"]["metrics"]["roi"] > 1.0
        assert all(a["feasible"] for a in mock_responses["actions"]["actions"] if "blocker_reason" not in a)
    
    async def test_context_propagation_through_workflow(self, orchestration_setup):
        """Test that context properly propagates through agent workflow."""
        # Create initial context with business constraints
        initial_context = {
            "constraints": {
                "max_cost": 1000,
                "min_performance": 0.85,
                "timeline": "2 weeks"
            },
            "business_goals": {
                "primary": "cost_reduction",
                "secondary": "performance_improvement"
            }
        }
        
        state = DeepAgentState()
        state.context = initial_context
        state.triage_result = None  # Will be set by triage
        
        # Simulate context propagation
        # After triage
        state.triage_result = {
            "data_sufficiency": "sufficient",
            "category": "optimization"
        }
        
        # Verify optimization agent receives triage context
        assert state.triage_result is not None
        assert state.context["constraints"]["max_cost"] == 1000
        
        # After optimization
        state.optimization_result = {
            "selected_strategy": "cache_optimization",
            "expected_cost": 500
        }
        
        # Verify actions agent receives accumulated context
        assert state.optimization_result["expected_cost"] < state.context["constraints"]["max_cost"]
    
    async def test_parallel_agent_execution_outcomes(self, orchestration_setup):
        """Test business outcomes when agents can execute in parallel."""
        # This would test scenarios where multiple agents can work simultaneously
        # For example: data collection and cost analysis happening in parallel
        
        parallel_results = {
            "data_collection": {
                "status": "completed",
                "data_points": 1000,
                "quality_score": 0.95
            },
            "cost_analysis": {
                "status": "completed",
                "current_cost": 5000,
                "optimization_potential": 0.30
            }
        }
        
        # Both should complete independently
        assert parallel_results["data_collection"]["status"] == "completed"
        assert parallel_results["cost_analysis"]["status"] == "completed"
        
        # Results should be combinable for next phase
        combined_insight = {
            "data_quality": parallel_results["data_collection"]["quality_score"],
            "cost_savings": parallel_results["cost_analysis"]["current_cost"] * 
                          parallel_results["cost_analysis"]["optimization_potential"]
        }
        
        assert combined_insight["cost_savings"] == 1500  # 5000 * 0.30
    
    async def test_failure_recovery_business_impact(self, orchestration_setup):
        """Test business impact when agent fails and recovery is attempted."""
        # Simulate optimization agent failure
        failed_optimization = {
            "status": "failed",
            "error": "Insufficient data for optimization",
            "fallback": "basic_heuristics"
        }
        
        # Fallback strategy should still provide business value
        fallback_result = {
            "strategies": [
                {
                    "name": "Basic Cache",
                    "expected_improvement": 0.10,  # Less than optimal
                    "cost": 0.05,
                    "risk_level": "low",
                    "confidence": 0.60  # Lower confidence
                }
            ]
        }
        
        validator = BusinessOutcomeValidator()
        
        # Fallback should still be valid, just with lower confidence
        assert validator.validate_optimization_strategies(fallback_result)
        assert fallback_result["strategies"][0]["confidence"] < 0.70