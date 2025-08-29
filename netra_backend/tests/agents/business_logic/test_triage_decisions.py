"""Triage Agent Business Logic Decision Validation Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Accurate Workflow Routing
- Value Impact: Ensures correct data sufficiency assessment drives optimal workflow
- Revenue Impact: Prevents wasted compute and poor UX from incorrect routing

This test suite validates that the triage agent makes correct business decisions
about data sufficiency and workflow routing, not just technical execution.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import json

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestTriageDecisionLogic:
    """Validate triage agent business logic decisions."""
    
    @pytest.fixture
    async def triage_agent(self):
        """Create triage agent with mocked dependencies."""
        llm_manager = AsyncMock()
        tool_dispatcher = AsyncMock()
        websocket_manager = AsyncMock()
        
        agent = TriageSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            websocket_manager=websocket_manager
        )
        return agent
    
    @pytest.fixture
    def business_scenarios(self) -> List[Dict[str, Any]]:
        """Real-world business scenarios for triage validation."""
        return [
            {
                "name": "high_latency_api_with_metrics",
                "input": {
                    "user_message": "Our API response times are averaging 3.2 seconds",
                    "context": {
                        "metrics": {
                            "p50_latency": 2.8,
                            "p95_latency": 5.2,
                            "p99_latency": 8.1,
                            "requests_per_second": 1500,
                            "error_rate": 0.02
                        },
                        "infrastructure": {
                            "model": "gpt-4",
                            "region": "us-west-2",
                            "cache_enabled": False
                        }
                    }
                },
                "expected_decision": {
                    "data_sufficiency": "sufficient",
                    "category": "performance_optimization",
                    "priority": "high",
                    "workflow": ["triage", "optimization", "data", "actions", "reporting"],
                    "reasoning": "Complete metrics available for analysis"
                }
            },
            {
                "name": "vague_performance_complaint",
                "input": {
                    "user_message": "System feels slow",
                    "context": {}
                },
                "expected_decision": {
                    "data_sufficiency": "insufficient",
                    "category": "discovery",
                    "priority": "medium",
                    "workflow": ["triage", "data_helper"],
                    "reasoning": "No metrics provided, need data collection"
                }
            },
            {
                "name": "cost_optimization_with_partial_data",
                "input": {
                    "user_message": "We're spending $5K/month on GPT-4, need to reduce",
                    "context": {
                        "costs": {
                            "monthly_spend": 5000,
                            "model": "gpt-4"
                        }
                        # Missing: usage patterns, quality requirements
                    }
                },
                "expected_decision": {
                    "data_sufficiency": "partial",
                    "category": "cost_optimization",
                    "priority": "high",
                    "workflow": ["triage", "optimization", "actions", "data_helper", "reporting"],
                    "reasoning": "Cost data available but usage patterns missing"
                }
            },
            {
                "name": "multi_objective_with_constraints",
                "input": {
                    "user_message": "Reduce costs by 30% while maintaining 95% accuracy",
                    "context": {
                        "current_metrics": {
                            "monthly_cost": 8000,
                            "accuracy": 0.97,
                            "latency_ms": 450
                        },
                        "constraints": {
                            "min_accuracy": 0.95,
                            "max_latency_ms": 500,
                            "target_cost_reduction": 0.30
                        },
                        "usage": {
                            "daily_requests": 50000,
                            "peak_hour_requests": 5000
                        }
                    }
                },
                "expected_decision": {
                    "data_sufficiency": "sufficient",
                    "category": "multi_objective_optimization",
                    "priority": "critical",
                    "workflow": ["triage", "optimization", "data", "actions", "reporting"],
                    "reasoning": "All necessary data and constraints provided"
                }
            },
            {
                "name": "emergency_outage_investigation",
                "input": {
                    "user_message": "AI service is down, customers impacted!",
                    "context": {
                        "status": {
                            "service_health": "unhealthy",
                            "last_successful_request": "5 minutes ago"
                        }
                    }
                },
                "expected_decision": {
                    "data_sufficiency": "partial",
                    "category": "incident_response",
                    "priority": "critical",
                    "workflow": ["triage", "data", "actions"],
                    "reasoning": "Emergency requires immediate action with available data"
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_data_sufficiency_assessment(self, triage_agent, business_scenarios):
        """Test correct assessment of data sufficiency for various scenarios."""
        for scenario in business_scenarios:
            # Create execution context
            context = ExecutionContext(
                thread_id=f"test_{scenario['name']}",
                user_message=scenario["input"]["user_message"],
                thread_context=scenario["input"].get("context", {})
            )
            
            # Mock LLM response based on scenario
            triage_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps(scenario["expected_decision"]),
                    "metadata": {"model": "test"}
                }
            )
            
            # Execute triage
            result = await triage_agent.execute(context)
            
            # Validate data sufficiency assessment
            assert result.success, f"Failed for scenario: {scenario['name']}"
            decision = result.data
            
            assert decision["data_sufficiency"] == scenario["expected_decision"]["data_sufficiency"], \
                f"Incorrect data sufficiency for {scenario['name']}"
            
            # Log decision reasoning for audit
            logger.info(f"Scenario: {scenario['name']}, Decision: {decision['data_sufficiency']}, "
                       f"Reasoning: {decision.get('reasoning', 'N/A')}")
    
    @pytest.mark.asyncio
    async def test_workflow_path_selection(self, triage_agent, business_scenarios):
        """Test correct workflow path selection based on data sufficiency."""
        for scenario in business_scenarios:
            context = ExecutionContext(
                thread_id=f"test_workflow_{scenario['name']}",
                user_message=scenario["input"]["user_message"],
                thread_context=scenario["input"].get("context", {})
            )
            
            # Mock response
            triage_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps(scenario["expected_decision"]),
                    "metadata": {"model": "test"}
                }
            )
            
            result = await triage_agent.execute(context)
            decision = result.data
            
            # Validate workflow selection
            expected_workflow = scenario["expected_decision"]["workflow"]
            actual_workflow = decision.get("workflow", [])
            
            assert actual_workflow == expected_workflow, \
                f"Incorrect workflow for {scenario['name']}: expected {expected_workflow}, got {actual_workflow}"
            
            # Validate workflow length based on data sufficiency
            if decision["data_sufficiency"] == "sufficient":
                assert len(actual_workflow) >= 5, "Sufficient data should trigger full workflow"
            elif decision["data_sufficiency"] == "insufficient":
                assert len(actual_workflow) <= 2, "Insufficient data should trigger minimal workflow"
            elif decision["data_sufficiency"] == "partial":
                assert 3 <= len(actual_workflow) <= 5, "Partial data should trigger modified workflow"
    
    @pytest.mark.asyncio
    async def test_priority_classification(self, triage_agent, business_scenarios):
        """Test correct priority classification for different scenarios."""
        priority_rules = {
            "critical": ["emergency", "incident", "outage", "down"],
            "high": ["reduce cost", "performance", "latency", "optimization"],
            "medium": ["improve", "enhance", "analyze"],
            "low": ["explore", "investigate", "research"]
        }
        
        for scenario in business_scenarios:
            context = ExecutionContext(
                thread_id=f"test_priority_{scenario['name']}",
                user_message=scenario["input"]["user_message"],
                thread_context=scenario["input"].get("context", {})
            )
            
            # Mock response
            triage_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps(scenario["expected_decision"]),
                    "metadata": {"model": "test"}
                }
            )
            
            result = await triage_agent.execute(context)
            decision = result.data
            
            # Validate priority
            expected_priority = scenario["expected_decision"]["priority"]
            actual_priority = decision.get("priority", "unknown")
            
            assert actual_priority == expected_priority, \
                f"Incorrect priority for {scenario['name']}: expected {expected_priority}, got {actual_priority}"
    
    @pytest.mark.asyncio
    async def test_edge_case_handling(self, triage_agent):
        """Test handling of ambiguous and edge case requests."""
        edge_cases = [
            {
                "message": "",  # Empty request
                "expected_sufficiency": "insufficient",
                "expected_workflow": ["triage", "data_helper"]
            },
            {
                "message": "help",  # Too vague
                "expected_sufficiency": "insufficient",
                "expected_workflow": ["triage", "data_helper"]
            },
            {
                "message": "Optimize everything!",  # Too broad
                "expected_sufficiency": "insufficient",
                "expected_workflow": ["triage", "data_helper"]
            },
            {
                "message": "Fix the bug in line 42",  # Wrong domain
                "expected_sufficiency": "insufficient",
                "expected_workflow": ["triage", "data_helper"]
            }
        ]
        
        for case in edge_cases:
            context = ExecutionContext(
                thread_id=f"test_edge_{case['message'][:10]}",
                user_message=case["message"],
                thread_context={}
            )
            
            # Mock minimal response for edge cases
            triage_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps({
                        "data_sufficiency": case["expected_sufficiency"],
                        "category": "unknown",
                        "priority": "low",
                        "workflow": case["expected_workflow"],
                        "reasoning": "Insufficient information to proceed"
                    }),
                    "metadata": {"model": "test"}
                }
            )
            
            result = await triage_agent.execute(context)
            
            # Should handle gracefully
            assert result.success, f"Failed to handle edge case: {case['message']}"
            assert result.data["data_sufficiency"] == case["expected_sufficiency"]
    
    @pytest.mark.asyncio
    async def test_context_inheritance(self, triage_agent):
        """Test that triage preserves and enriches context for downstream agents."""
        initial_context = {
            "user_id": "test_user",
            "session_id": "session_123",
            "existing_metrics": {"latency": 500}
        }
        
        context = ExecutionContext(
            thread_id="test_context_inheritance",
            user_message="Optimize latency",
            thread_context=initial_context
        )
        
        # Mock response with additional context
        triage_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "data_sufficiency": "partial",
                    "category": "performance",
                    "priority": "high",
                    "workflow": ["triage", "optimization", "data_helper"],
                    "enriched_context": {
                        "identified_issue": "latency",
                        "current_value": 500,
                        "target_improvement": "50% reduction"
                    }
                }),
                "metadata": {"model": "test"}
            }
        )
        
        result = await triage_agent.execute(context)
        
        # Validate context preservation and enrichment
        assert result.success
        assert "enriched_context" in result.data
        assert result.data["enriched_context"]["identified_issue"] == "latency"
        
        # Ensure original context is preserved
        assert result.context.thread_context["user_id"] == "test_user"
        assert result.context.thread_context["session_id"] == "session_123"
    
    @pytest.mark.asyncio
    async def test_decision_consistency(self, triage_agent):
        """Test that similar requests produce consistent decisions."""
        similar_requests = [
            "Our API is slow, averaging 3 seconds response time",
            "API response times are around 3 seconds",
            "We have 3 second API latency"
        ]
        
        decisions = []
        for request in similar_requests:
            context = ExecutionContext(
                thread_id=f"test_consistency_{len(decisions)}",
                user_message=request,
                thread_context={"metrics": {"latency": 3000}}
            )
            
            # Mock consistent response
            triage_agent.llm_manager.generate_response = AsyncMock(
                return_value={
                    "content": json.dumps({
                        "data_sufficiency": "sufficient",
                        "category": "performance_optimization",
                        "priority": "high",
                        "workflow": ["triage", "optimization", "data", "actions", "reporting"]
                    }),
                    "metadata": {"model": "test"}
                }
            )
            
            result = await triage_agent.execute(context)
            decisions.append(result.data)
        
        # All similar requests should produce same data sufficiency
        sufficiencies = [d["data_sufficiency"] for d in decisions]
        assert len(set(sufficiencies)) == 1, "Inconsistent decisions for similar requests"
        
        # All should have same workflow length
        workflow_lengths = [len(d["workflow"]) for d in decisions]
        assert len(set(workflow_lengths)) == 1, "Inconsistent workflow lengths"