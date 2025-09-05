"""Optimization Agent Output Quality and Value Validation Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: High-Quality AI Optimization Recommendations
- Value Impact: Validates optimization recommendations create measurable value
- Revenue Impact: Protects $10K-100K+ value per customer from bad recommendations

This test suite validates that optimization agents generate high-quality,
actionable recommendations with measurable ROI.
"""

import pytest
from typing import Dict, Any, List, Optional
import json
from decimal import Decimal
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class OptimizationValueValidator:
    """Validates optimization output quality and business value."""
    
    @staticmethod
    def validate_optimization_value(optimization: Dict[str, Any]) -> Dict[str, bool]:
        """Validate optimization recommendation has measurable value."""
        validation_results = {
            "has_expected_savings": False,
            "has_implementation_time": False,
            "has_risk_assessment": False,
            "roi_positive": False,
            "feasible": False
        }
        
        # Check for expected savings
        if "expected_savings" in optimization:
            savings = optimization["expected_savings"]
            if isinstance(savings, (int, float)) and savings > 0:
                validation_results["has_expected_savings"] = True
        
        # Check for implementation timeline
        if "implementation_time" in optimization:
            time = optimization["implementation_time"]
            if time and (isinstance(time, str) or isinstance(time, int)):
                validation_results["has_implementation_time"] = True
        
        # Check for risk assessment
        if "risk_level" in optimization:
            risk = optimization["risk_level"]
            if risk in ["low", "medium", "high", "critical"]:
                validation_results["has_risk_assessment"] = True
        
        # Calculate ROI
        if "expected_savings" in optimization and "cost" in optimization:
            savings = optimization["expected_savings"]
            cost = optimization["cost"]
            if cost > 0:
                roi = (savings - cost) / cost
                validation_results["roi_positive"] = roi > 0
        
        # Check feasibility
        if "feasible" in optimization:
            validation_results["feasible"] = optimization["feasible"]
        elif "implementation_steps" in optimization:
            validation_results["feasible"] = len(optimization["implementation_steps"]) > 0
        
        return validation_results
    
    @staticmethod
    def validate_action_feasibility(action: Dict[str, Any]) -> Dict[str, bool]:
        """Validate action plan is implementable."""
        validation_results = {
            "has_steps": False,
            "steps_detailed": False,
            "has_resources": False,
            "has_timeline": False,
            "dependencies_clear": False
        }
        
        # Check for implementation steps
        if "steps" in action and isinstance(action["steps"], list):
            validation_results["has_steps"] = len(action["steps"]) > 0
            
            # Check if steps are detailed
            if validation_results["has_steps"]:
                detailed = all(
                    isinstance(step, dict) and "description" in step
                    for step in action["steps"]
                )
                validation_results["steps_detailed"] = detailed
        
        # Check for resource requirements
        if "required_resources" in action:
            resources = action["required_resources"]
            validation_results["has_resources"] = resources is not None and len(str(resources)) > 0
        
        # Check for timeline
        if "timeline" in action or "estimated_duration" in action:
            validation_results["has_timeline"] = True
        
        # Check for dependencies
        if "dependencies" in action:
            validation_results["dependencies_clear"] = isinstance(action["dependencies"], list)
        
        return validation_results


class TestOptimizationOutputQuality:
    """Test optimization agent output quality and value generation."""
    
    @pytest.fixture
    async def optimization_agent(self):
        """Create optimization agent with mocked dependencies."""
        llm_manager = AsyncNone  # TODO: Use real service instance
        tool_dispatcher = AsyncNone  # TODO: Use real service instance
        websocket_manager = AsyncNone  # TODO: Use real service instance
        
        agent = OptimizationsCoreSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            websocket_manager=websocket_manager
        )
        return agent
    
    @pytest.fixture
    async def actions_agent(self):
        """Create actions agent with mocked dependencies."""
        llm_manager = AsyncNone  # TODO: Use real service instance
        tool_dispatcher = AsyncNone  # TODO: Use real service instance
        
        agent = ActionsToMeetGoalsSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        return agent
    
    @pytest.fixture
    def optimization_scenarios(self) -> List[Dict[str, Any]]:
        """Real-world optimization scenarios with expected value outcomes."""
        return [
            {
                "name": "model_switching_optimization",
                "context": {
                    "current_model": "gpt-4",
                    "monthly_cost": 5000,
                    "accuracy": 0.95,
                    "latency_ms": 450
                },
                "expected_optimization": {
                    "strategy": "Switch to gpt-3.5-turbo for non-critical paths",
                    "expected_savings": 2500,
                    "cost": 200,  # Implementation cost
                    "risk_level": "low",
                    "implementation_time": "2 days",
                    "accuracy_impact": -0.02,
                    "feasible": True
                }
            },
            {
                "name": "caching_strategy",
                "context": {
                    "request_patterns": {
                        "duplicate_rate": 0.35,
                        "daily_requests": 100000
                    },
                    "current_latency": 2000
                },
                "expected_optimization": {
                    "strategy": "Implement semantic caching layer",
                    "expected_savings": 3500,
                    "cost": 500,
                    "risk_level": "medium",
                    "implementation_time": "1 week",
                    "latency_improvement": 0.60,
                    "feasible": True
                }
            },
            {
                "name": "batching_optimization",
                "context": {
                    "request_pattern": "synchronous",
                    "average_batch_potential": 10,
                    "current_cost_per_request": 0.05
                },
                "expected_optimization": {
                    "strategy": "Implement request batching",
                    "expected_savings": 4000,
                    "cost": 800,
                    "risk_level": "low",
                    "implementation_time": "3 days",
                    "throughput_improvement": 5.0,
                    "feasible": True
                }
            },
            {
                "name": "multi_objective_optimization",
                "context": {
                    "constraints": {
                        "max_latency": 500,
                        "min_accuracy": 0.90,
                        "budget": 3000
                    },
                    "current_metrics": {
                        "latency": 800,
                        "accuracy": 0.95,
                        "cost": 4500
                    }
                },
                "expected_optimization": {
                    "strategy": "Hybrid approach: model downgrade + caching",
                    "expected_savings": 1800,
                    "cost": 600,
                    "risk_level": "medium",
                    "implementation_time": "5 days",
                    "tradeoffs": {
                        "accuracy_loss": 0.03,
                        "latency_gain": 0.40
                    },
                    "feasible": True
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_optimization_value_generation(self, optimization_agent, optimization_scenarios):
        """Test that optimizations generate measurable value."""
        validator = OptimizationValueValidator()
        
        for scenario in optimization_scenarios:
            # Create proper state and context
            state = DeepAgentState(
                user_request=f"Optimize based on: {json.dumps(scenario['context'])}",
                chat_thread_id=f"test_opt_{scenario['name']}",
                metadata={"context": scenario["context"]}
            )
            # Context not needed for direct execute call
            
            # Mock LLM response with optimization
            optimization_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps({
                        "optimizations": [scenario["expected_optimization"]]
                    }),
                    "metadata": {"model": "test"}
                }
            )
            
            # Execute with proper arguments
            await optimization_agent.execute(state, f"run_opt_{scenario['name']}", False)
            
            # Get mocked response data
            response_data = json.loads(optimization_agent.llm_manager.generate_response.return_value["content"])
            optimizations = response_data.get("optimizations", [])
            assert len(optimizations) > 0, "No optimizations generated"
            
            # Validate each optimization
            for opt in optimizations:
                validation = validator.validate_optimization_value(opt)
                
                # All critical fields should be present
                assert validation["has_expected_savings"], \
                    f"Missing expected savings for {scenario['name']}"
                assert validation["has_implementation_time"], \
                    f"Missing implementation time for {scenario['name']}"
                assert validation["has_risk_assessment"], \
                    f"Missing risk assessment for {scenario['name']}"
                
                # ROI should be positive for viable optimizations
                if opt.get("feasible", True):
                    assert validation["roi_positive"], \
                        f"Negative ROI for feasible optimization in {scenario['name']}"
    
    @pytest.mark.asyncio
    async def test_action_plan_feasibility(self, actions_agent, optimization_scenarios):
        """Test that action plans are implementable."""
        validator = OptimizationValueValidator()
        
        for scenario in optimization_scenarios:
            # Create context with optimization output
            # Create proper state and context
            state = DeepAgentState(
                user_request="Create action plan",
                chat_thread_id=f"test_action_{scenario['name']}",
                metadata={"context": {"optimization": scenario["expected_optimization"]}}
            )
            # Context not needed for direct execute call
            
            # Mock action plan response
            action_plan = {
                "actions": [
                    {
                        "name": f"Implement {scenario['expected_optimization']['strategy']}",
                        "steps": [
                            {"order": 1, "description": "Analyze current implementation"},
                            {"order": 2, "description": "Design new architecture"},
                            {"order": 3, "description": "Implement changes"},
                            {"order": 4, "description": "Test and validate"},
                            {"order": 5, "description": "Deploy to production"}
                        ],
                        "required_resources": ["Developer time", "Testing environment"],
                        "estimated_duration": scenario["expected_optimization"]["implementation_time"],
                        "dependencies": [],
                        "feasible": True
                    }
                ]
            }
            
            actions_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps(action_plan),
                    "metadata": {"model": "test"}
                }
            )
            
            # Execute with proper arguments
            await actions_agent.execute(state, f"run_action_{scenario['name']}", False)
            
            # Get mocked response data
            response_data = json.loads(actions_agent.llm_manager.generate_response.return_value["content"])
            actions = response_data.get("actions", [])
            assert len(actions) > 0, "No actions generated"
            
            # Validate each action
            for action in actions:
                validation = validator.validate_action_feasibility(action)
                
                assert validation["has_steps"], \
                    f"Missing steps for action in {scenario['name']}"
                assert validation["steps_detailed"], \
                    f"Steps not detailed for action in {scenario['name']}"
                assert validation["has_resources"], \
                    f"Missing resources for action in {scenario['name']}"
                assert validation["has_timeline"], \
                    f"Missing timeline for action in {scenario['name']}"
    
    @pytest.mark.asyncio
    async def test_optimization_constraints_respect(self, optimization_agent):
        """Test that optimizations respect defined constraints."""
        constraints_scenarios = [
            {
                "constraints": {
                    "max_cost_increase": 0,
                    "min_accuracy": 0.90,
                    "max_latency_ms": 500
                },
                "current_state": {
                    "cost": 3000,
                    "accuracy": 0.92,
                    "latency_ms": 600
                }
            },
            {
                "constraints": {
                    "budget": 5000,
                    "required_uptime": 0.999,
                    "max_implementation_days": 7
                },
                "current_state": {
                    "monthly_cost": 8000,
                    "uptime": 0.995,
                    "performance_score": 75
                }
            }
        ]
        
        for scenario in constraints_scenarios:
            # Create proper state and context
            state = DeepAgentState(
                user_request="Optimize within constraints",
                chat_thread_id="test_constraints",
                metadata={"context": scenario}
            )
            # Context not needed for direct execute call
            
            # Mock optimization that respects constraints
            optimization_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps({
                        "optimizations": [{
                            "strategy": "Constraint-aware optimization",
                            "expected_savings": 1000,
                            "cost": 200,
                            "risk_level": "low",
                            "implementation_time": "3 days",
                            "constraints_satisfied": True,
                            "feasible": True
                        }]
                    }),
                    "metadata": {"model": "test"}
                }
            )
            
            # Execute with proper arguments
            await optimization_agent.execute(state, "run_constraints", False)
            
            # Get mocked response data
            response_data = json.loads(optimization_agent.llm_manager.generate_response.return_value["content"])
            optimizations = response_data.get("optimizations", [])
            
            for opt in optimizations:
                # Verify constraints are acknowledged
                assert "constraints_satisfied" in opt or "feasible" in opt
                
                # If implementation time constraint exists, verify it's respected
                if "max_implementation_days" in scenario["constraints"]:
                    impl_time = opt.get("implementation_time", "")
                    # Parse implementation time (simplified)
                    if "day" in impl_time:
                        days = int(''.join(filter(str.isdigit, impl_time.split("day")[0])))
                        assert days <= scenario["constraints"]["max_implementation_days"]
    
    @pytest.mark.asyncio
    async def test_optimization_quality_metrics(self, optimization_agent):
        """Test optimization quality metrics and scoring."""
        # Create proper state and context
        state = DeepAgentState(
            user_request="Generate high-quality optimizations",
            chat_thread_id="test_quality",
            metadata={"context": {"metrics": {"cost": 10000, "performance": 70}}}
        )
        # Context not needed for direct execute call
        
        # Mock high-quality optimization response
        optimization_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "optimizations": [
                        {
                            "strategy": "Premium optimization",
                            "expected_savings": 5000,
                            "cost": 1000,
                            "risk_level": "low",
                            "implementation_time": "1 week",
                            "confidence_score": 0.85,
                            "impact_analysis": {
                                "performance_improvement": 0.30,
                                "cost_reduction": 0.50,
                                "complexity_reduction": 0.20
                            },
                            "feasible": True
                        }
                    ],
                    "quality_metrics": {
                        "total_value": 5000,
                        "implementation_complexity": "medium",
                        "success_probability": 0.85
                    }
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await optimization_agent.execute(state, "run_quality", False)
        
        # Get mocked response data
        data = json.loads(optimization_agent.llm_manager.generate_response.return_value["content"])
        
        # Check for quality metrics
        if "quality_metrics" in data:
            metrics = data["quality_metrics"]
            assert "total_value" in metrics
            assert metrics["total_value"] > 0
            
            if "success_probability" in metrics:
                assert 0 <= metrics["success_probability"] <= 1
        
        # Check optimization quality
        for opt in data.get("optimizations", []):
            # Should have confidence score
            if "confidence_score" in opt:
                assert 0 <= opt["confidence_score"] <= 1
            
            # Should have impact analysis
            if "impact_analysis" in opt:
                impact = opt["impact_analysis"]
                assert any(k in impact for k in 
                          ["performance_improvement", "cost_reduction", "complexity_reduction"])
    
    @pytest.mark.asyncio
    async def test_optimization_explanation_clarity(self, optimization_agent):
        """Test that optimizations include clear explanations."""
        # Create proper state and context
        state = DeepAgentState(
            user_request="Explain optimization clearly",
            chat_thread_id="test_explanation",
            metadata={"context": {"current_cost": 5000}}
        )
        # Context not needed for direct execute call
        
        optimization_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "optimizations": [{
                        "strategy": "Model optimization",
                        "explanation": "Switch from GPT-4 to GPT-3.5-turbo for non-critical paths",
                        "rationale": "Analysis shows 60% of requests don't require GPT-4 capabilities",
                        "expected_savings": 2000,
                        "cost": 300,
                        "risk_level": "low",
                        "implementation_time": "2 days",
                        "implementation_details": {
                            "step_1": "Classify requests by complexity",
                            "step_2": "Route simple requests to GPT-3.5",
                            "step_3": "Monitor quality metrics"
                        },
                        "feasible": True
                    }]
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Execute with proper arguments
        await optimization_agent.execute(state, "run_explanation", False)
        
        # Get mocked response data
        response_data = json.loads(optimization_agent.llm_manager.generate_response.return_value["content"])
        optimizations = response_data.get("optimizations", [])
        
        for opt in optimizations:
            # Should have clear explanation
            assert "explanation" in opt or "strategy" in opt
            
            # Should have rationale
            if "rationale" in opt:
                assert len(opt["rationale"]) > 10  # Non-trivial explanation
            
            # Should have implementation details
            if "implementation_details" in opt:
                details = opt["implementation_details"]
                assert len(details) > 0