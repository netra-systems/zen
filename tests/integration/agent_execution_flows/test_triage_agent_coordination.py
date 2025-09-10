"""
Test Triage Agent Coordination Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure triage agent properly routes and prioritizes customer requests
- Value Impact: Optimizes resource allocation and ensures high-priority requests get proper attention
- Strategic Impact: Critical for user experience - proper triage ensures customers get appropriate level of service

Tests the triage agent's coordination with other agents including request classification,
priority assignment, and routing decisions to appropriate specialized agents.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)


class TestTriageAgentCoordination(BaseIntegrationTest):
    """Integration tests for triage agent coordination."""

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_triage_agent_request_classification_coordination(self, real_services_fixture):
        """Test triage agent coordination for request classification and routing."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_600",
            thread_id="thread_900",
            session_id="session_1200",
            workspace_id="workspace_500"
        )
        
        mock_llm = AsyncMock()
        triage_scenarios = [
            # High-priority cost optimization request
            {
                "input": "Our AWS bill increased by 300% this month, need immediate cost analysis",
                "expected_priority": "high",
                "expected_route": "apex_optimizer",
                "expected_urgency": "immediate"
            },
            # Medium-priority data request
            {
                "input": "Can you show me last quarter's usage trends?", 
                "expected_priority": "medium",
                "expected_route": "data_helper",
                "expected_urgency": "standard"
            },
            # Low-priority general inquiry
            {
                "input": "What features does your platform offer?",
                "expected_priority": "low", 
                "expected_route": "simple_response",
                "expected_urgency": "low"
            }
        ]
        
        # Mock LLM responses for different scenarios
        def create_triage_response(scenario):
            return {
                "status": "success",
                "classification": {
                    "priority": scenario["expected_priority"],
                    "urgency": scenario["expected_urgency"],
                    "category": "cost_optimization" if "cost" in scenario["input"] else "data_request",
                    "confidence": 0.9
                },
                "routing": {
                    "recommended_agent": scenario["expected_route"],
                    "reasoning": f"Based on {scenario['expected_priority']} priority classification",
                    "estimated_time": "5 minutes" if scenario["expected_priority"] == "high" else "15 minutes"
                }
            }
        
        triage_agent = GoalsTriageSubAgent(
            user_context=user_context,
            llm_client=mock_llm
        )
        
        # Act & Assert - Test each triage scenario
        for scenario in triage_scenarios:
            mock_llm.generate_response = AsyncMock(return_value=create_triage_response(scenario))
            
            result = await triage_agent.execute_triage_classification(
                request=scenario["input"],
                coordination_mode="priority_based"
            )
            
            assert result is not None
            assert result.status == "success"
            
            classification = result.result["classification"]
            routing = result.result["routing"]
            
            assert classification["priority"] == scenario["expected_priority"]
            assert classification["urgency"] == scenario["expected_urgency"]
            assert routing["recommended_agent"] == scenario["expected_route"]

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_triage_agent_load_balancing_coordination(self, real_services_fixture):
        """Test triage agent coordination with load balancing across specialized agents."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_601",
            thread_id="thread_901",
            session_id="session_1201",
            workspace_id="workspace_501"
        )
        
        # Mock agent load monitor
        mock_load_monitor = MagicMock()
        mock_load_monitor.get_agent_load = MagicMock(side_effect=lambda agent_type: {
            "apex_optimizer": {"current_load": 0.8, "queue_length": 5},
            "data_helper": {"current_load": 0.3, "queue_length": 1},
            "reporting": {"current_load": 0.6, "queue_length": 3}
        }.get(agent_type, {"current_load": 0.0, "queue_length": 0}))
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "triage_decision": {
                "primary_route": "data_helper",  # Less loaded
                "alternative_route": "apex_optimizer", 
                "load_balancing_applied": True,
                "reasoning": "Routing to data_helper due to lower current load (0.3 vs 0.8)"
            }
        })
        
        triage_agent = GoalsTriageSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            load_monitor=mock_load_monitor
        )
        
        # Act - Execute triage with load balancing
        result = await triage_agent.execute_load_balanced_triage(
            request="Analyze our infrastructure costs and generate report",
            enable_load_balancing=True
        )
        
        # Assert - Verify load balancing coordination
        assert result is not None
        assert result.status == "success"
        
        triage_decision = result.result["triage_decision"]
        assert triage_decision["load_balancing_applied"] is True
        assert triage_decision["primary_route"] == "data_helper"  # Less loaded agent
        
        # Verify load monitor was consulted
        mock_load_monitor.get_agent_load.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination 
    async def test_triage_agent_escalation_coordination(self, real_services_fixture):
        """Test triage agent coordination for request escalation scenarios."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_602",
            thread_id="thread_902", 
            session_id="session_1202",
            workspace_id="workspace_502"
        )
        
        mock_escalation_manager = AsyncMock()
        mock_escalation_manager.should_escalate = AsyncMock(return_value={
            "escalate": True,
            "escalation_level": "supervisor",
            "reason": "Complex multi-service cost optimization requiring advanced analysis"
        })
        
        mock_escalation_manager.create_escalation = AsyncMock(return_value={
            "escalation_id": "esc_123",
            "assigned_agent": "supervisor_agent",
            "priority": "high",
            "estimated_resolution": "30 minutes"
        })
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "escalation_analysis": {
                "complexity_score": 0.95,
                "requires_multiple_agents": True,
                "estimated_effort": "high",
                "escalation_recommended": True
            }
        })
        
        triage_agent = GoalsTriageSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            escalation_manager=mock_escalation_manager
        )
        
        # Act - Execute triage with escalation
        complex_request = """
        We need comprehensive cost optimization across AWS, Azure, and GCP.
        Analyze current spend, identify savings opportunities, create migration plan,
        and provide ROI projections for next 12 months with risk assessment.
        """
        
        result = await triage_agent.execute_escalation_triage(
            request=complex_request,
            escalation_enabled=True
        )
        
        # Assert - Verify escalation coordination
        assert result is not None
        assert result.status == "success"
        
        escalation_analysis = result.result["escalation_analysis"]
        assert escalation_analysis["escalation_recommended"] is True
        assert escalation_analysis["complexity_score"] >= 0.9
        
        # Verify escalation manager coordination
        mock_escalation_manager.should_escalate.assert_called()
        mock_escalation_manager.create_escalation.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_triage_agent_multi_step_workflow_coordination(self, real_services_fixture):
        """Test triage agent coordination for multi-step workflow planning."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_603",
            thread_id="thread_903",
            session_id="session_1203",
            workspace_id="workspace_503"
        )
        
        mock_workflow_planner = AsyncMock()
        mock_workflow_planner.create_workflow_plan = AsyncMock(return_value={
            "workflow_id": "wf_456",
            "steps": [
                {"step": 1, "agent": "data_helper", "task": "collect_usage_data", "estimated_time": "5min"},
                {"step": 2, "agent": "apex_optimizer", "task": "analyze_optimization_opportunities", "estimated_time": "15min"},
                {"step": 3, "agent": "reporting", "task": "generate_executive_summary", "estimated_time": "10min"}
            ],
            "total_estimated_time": "30min",
            "dependencies_mapped": True
        })
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "workflow_analysis": {
                "requires_multi_step": True,
                "complexity": "medium",
                "agent_coordination_needed": True,
                "sequence_dependencies": ["data_collection", "analysis", "reporting"]
            }
        })
        
        triage_agent = GoalsTriageSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            workflow_planner=mock_workflow_planner
        )
        
        # Act - Execute triage for multi-step workflow
        result = await triage_agent.execute_workflow_triage(
            request="Create comprehensive cost optimization report with recommendations",
            enable_workflow_planning=True
        )
        
        # Assert - Verify workflow coordination  
        assert result is not None
        assert result.status == "success"
        
        workflow_analysis = result.result["workflow_analysis"] 
        assert workflow_analysis["requires_multi_step"] is True
        assert workflow_analysis["agent_coordination_needed"] is True
        
        # Verify workflow planner coordination
        mock_workflow_planner.create_workflow_plan.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_triage_agent_feedback_loop_coordination(self, real_services_fixture):
        """Test triage agent coordination with feedback loops for continuous improvement."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_604",
            thread_id="thread_904",
            session_id="session_1204", 
            workspace_id="workspace_504"
        )
        
        mock_feedback_collector = AsyncMock()
        mock_feedback_collector.collect_routing_feedback = AsyncMock()
        mock_feedback_collector.update_routing_model = AsyncMock(return_value={
            "model_updated": True,
            "accuracy_improvement": 0.05,
            "confidence_increase": 0.03
        })
        
        # Historical routing data for feedback
        historical_routing_data = [
            {"request_type": "cost_optimization", "routed_to": "apex_optimizer", "success": True, "satisfaction": 0.9},
            {"request_type": "data_query", "routed_to": "data_helper", "success": True, "satisfaction": 0.85},
            {"request_type": "cost_optimization", "routed_to": "data_helper", "success": False, "satisfaction": 0.4}  # Mis-routed
        ]
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success", 
            "triage_with_feedback": {
                "routing_decision": "apex_optimizer",
                "confidence": 0.92,
                "feedback_incorporated": True,
                "learning_applied": "Previous cost optimization requests routed to apex_optimizer had higher success rates"
            }
        })
        
        triage_agent = GoalsTriageSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            feedback_collector=mock_feedback_collector,
            historical_data=historical_routing_data
        )
        
        # Act - Execute triage with feedback learning
        result = await triage_agent.execute_feedback_enhanced_triage(
            request="Help optimize our cloud infrastructure costs",
            enable_feedback_learning=True
        )
        
        # Simulate feedback collection after execution
        await triage_agent.collect_execution_feedback(
            execution_result=result,
            user_satisfaction=0.95,
            routing_accuracy=True
        )
        
        # Assert - Verify feedback coordination
        assert result is not None
        assert result.status == "success"
        
        triage_result = result.result["triage_with_feedback"]
        assert triage_result["feedback_incorporated"] is True
        assert triage_result["confidence"] > 0.9
        assert triage_result["routing_decision"] == "apex_optimizer"
        
        # Verify feedback collector coordination
        mock_feedback_collector.collect_routing_feedback.assert_called()
        mock_feedback_collector.update_routing_model.assert_called()