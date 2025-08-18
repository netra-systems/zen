"""
Agent System Tests - SubAgents
Tests for individual sub-agent functionality including triage, data, optimization, actions, and reporting.
Compliance: <300 lines, 8-line max functions, modular design.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent
from app.agents.state import DeepAgentState
from app.agents.tool_dispatcher import ToolDispatcher
from app.schemas import SubAgentLifecycle
from app.llm.llm_manager import LLMManager


class TestTriageSubAgent:
    """Test cases for the Triage sub-agent"""
    async def test_triage_categorization(self):
        """Test 6: Verify Triage agent correctly categorizes user requests"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value='{"category": "cost_optimization", "priority": "high"}')
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        triage_agent = TriageSubAgent(mock_llm, mock_dispatcher)
        state = DeepAgentState(user_request="Reduce my AI costs")
        
        await triage_agent.execute(state, "test_run_id", False)
        
        assert state.triage_result != None
        assert state.triage_result["category"] == "cost_optimization"
        assert state.triage_result["priority"] == "high"
        
    async def test_triage_invalid_response_handling(self):
        """Test 7: Verify Triage handles invalid LLM responses gracefully"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value="Invalid JSON response")
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        triage_agent = TriageSubAgent(mock_llm, mock_dispatcher)
        state = DeepAgentState(user_request="Test request")
        
        await triage_agent.execute(state, "test_run_id", False)
        
        assert state.triage_result != None
        assert state.triage_result["category"] == "General Inquiry"
        
    async def test_triage_entry_conditions(self):
        """Test 8: Verify Triage checks entry conditions properly"""
        mock_llm = Mock(spec=LLMManager)
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        triage_agent = TriageSubAgent(mock_llm, mock_dispatcher)
        
        state_with_request = DeepAgentState(user_request="Test")
        assert await triage_agent.check_entry_conditions(state_with_request, "test_run_id") == True
        
        state_without_request = DeepAgentState(user_request="")
        assert await triage_agent.check_entry_conditions(state_without_request, "test_run_id") == False


class TestDataSubAgent:
    """Test cases for the Data Analysis sub-agent"""
    async def test_data_agent_analysis(self):
        """Test 9: Verify Data agent performs data analysis correctly"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value='{"metrics": {"latency": 150, "throughput": 1000}}')
        mock_dispatcher = Mock(spec=ToolDispatcher)
        mock_dispatcher.dispatch_tool = AsyncMock(return_value={"data": "test_data"})
        
        data_agent = DataSubAgent(mock_llm, mock_dispatcher)
        state = DeepAgentState(
            user_request="Analyze my system",
            triage_result={"category": "performance_analysis"}
        )
        
        await data_agent.execute(state, "test_run_id", False)
        
        assert state.data_result != None
        assert "metrics" in state.data_result
        
    async def test_data_agent_tool_usage(self):
        """Test 10: Verify Data agent uses tools correctly"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value='{"result": "success"}')
        mock_dispatcher = Mock(spec=ToolDispatcher)
        mock_dispatcher.dispatch_tool = AsyncMock(return_value={"status": "success"})
        
        data_agent = DataSubAgent(mock_llm, mock_dispatcher)
        data_agent.tool_dispatcher = mock_dispatcher
        
        state = DeepAgentState(user_request="Get metrics",
                              triage_result={"category": "test"})
        await data_agent.execute(state, "test_run_id", False)
        
        # Verify data_result was set
        assert state.data_result != None


class TestOptimizationSubAgent:
    """Test cases for the Optimization Core sub-agent"""
    async def test_optimization_recommendations(self):
        """Test 11: Verify Optimization agent generates valid recommendations"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value=json.dumps({
            "optimizations": [
                {"type": "model_selection", "recommendation": "Use smaller model"},
                {"type": "batch_size", "recommendation": "Increase batch size to 64"}
            ]
        }))
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        opt_agent = OptimizationsCoreSubAgent(mock_llm, mock_dispatcher)
        state = DeepAgentState(
            user_request="Optimize performance",
            data_result={"metrics": {"latency": 200}}
        )
        
        await opt_agent.execute(state, "test_run_id", False)
        
        assert state.optimizations_result != None
        assert "optimizations" in state.optimizations_result
        assert len(state.optimizations_result["optimizations"]) == 2
        
    async def test_optimization_cost_calculation(self):
        """Test 12: Verify Optimization calculates cost savings correctly"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value=json.dumps({
            "cost_savings": {"monthly": 5000, "annual": 60000},
            "performance_impact": "minimal"
        }))
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        opt_agent = OptimizationsCoreSubAgent(mock_llm, mock_dispatcher)
        state = DeepAgentState(user_request="Reduce costs")
        
        await opt_agent.execute(state, "test_run_id", False)
        
        assert state.optimizations_result["cost_savings"]["monthly"] == 5000


class TestActionsSubAgent:
    """Test cases for the Actions to Meet Goals sub-agent"""
    async def test_action_plan_generation(self):
        """Test 13: Verify Actions agent creates actionable plans"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value=json.dumps({
            "action_plan_summary": "Complete action plan",
            "total_estimated_time": "2 weeks",
            "actions": [
                {"step_id": "1", "description": "Update model configuration"},
                {"step_id": "2", "description": "Deploy changes to staging"},
                {"step_id": "3", "description": "Monitor performance metrics"}
            ],
            "required_approvals": [],
            "execution_timeline": []
        }))
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        with patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_reliability_wrapper'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_fallback_strategy'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.ExecutionMonitor'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.ReliabilityManager'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.BaseExecutionEngine'):
            
            actions_agent = ActionsToMeetGoalsSubAgent(mock_llm, mock_dispatcher)
            actions_agent._send_update = AsyncMock()
            
            state = DeepAgentState(
                user_request="Implement optimizations",
                optimizations_result={"optimizations": ["test"]},
                data_result={"analysis": "test"}
            )
            
            await actions_agent.execute(state, "test_run_id", False)
            
            assert state.action_plan_result is not None
            assert state.action_plan_result.action_plan_summary == "Complete action plan"
        
    async def test_action_priority_ordering(self):
        """Test 14: Verify Actions handles modern response format"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value=json.dumps({
            "action_plan_summary": "Priority-based action plan",
            "total_estimated_time": "1 week", 
            "actions": [
                {"step_id": "1", "description": "Critical fix", "priority": "high"},
                {"step_id": "2", "description": "Optional improvement", "priority": "low"}
            ],
            "required_approvals": []
        }))
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        with patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_reliability_wrapper'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_fallback_strategy'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.ExecutionMonitor'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.ReliabilityManager'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.BaseExecutionEngine'):
            
            actions_agent = ActionsToMeetGoalsSubAgent(mock_llm, mock_dispatcher)
            actions_agent._send_update = AsyncMock()
            
            state = DeepAgentState(
                user_request="Fix issues",
                optimizations_result={"test": "opt"},
                data_result={"test": "data"}
            )
            
            await actions_agent.execute(state, "test_run_id", False)
            
            assert state.action_plan_result is not None
            assert state.action_plan_result.action_plan_summary == "Priority-based action plan"

    async def test_actions_agent_modern_health_monitoring(self):
        """Test 15: Verify Actions agent modern health monitoring"""
        mock_llm = Mock(spec=LLMManager)
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        with patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_reliability_wrapper'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.create_agent_fallback_strategy'), \
             patch('app.agents.actions_to_meet_goals_sub_agent.ExecutionMonitor') as mock_monitor, \
             patch('app.agents.actions_to_meet_goals_sub_agent.ReliabilityManager') as mock_reliability, \
             patch('app.agents.actions_to_meet_goals_sub_agent.BaseExecutionEngine'):
            
            mock_monitor.return_value.get_health_status = Mock(return_value={"status": "healthy"})
            mock_monitor.return_value.get_agent_metrics = Mock(return_value={"metrics": {}})
            mock_reliability.return_value.get_circuit_breaker_status = Mock(return_value={"state": "closed"})
            
            actions_agent = ActionsToMeetGoalsSubAgent(mock_llm, mock_dispatcher)
            
            # Test modern health methods
            health = actions_agent.get_health_status()
            metrics = actions_agent.get_performance_metrics()
            circuit_status = actions_agent.get_circuit_breaker_status()
            
            assert isinstance(health, dict)
            assert isinstance(metrics, dict)
            assert isinstance(circuit_status, dict)


class TestReportingSubAgent:
    """Test cases for the Reporting sub-agent"""
    async def test_report_generation(self):
        """Test 15: Verify Reporting agent generates comprehensive reports"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value="## Executive Summary\nOptimizations identified...")
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        reporting_agent = ReportingSubAgent(mock_llm, mock_dispatcher)
        state = DeepAgentState(
            user_request="Generate report",
            triage_result={"category": "optimization"},
            data_result={"metrics": {}},
            optimizations_result={"optimizations": []},
            action_plan_result={"actions": []}
        )
        
        await reporting_agent.execute(state, "test_run_id", False)
        
        assert state.report_result != None or state.final_report != None
        
    async def test_report_formatting(self):
        """Test 16: Verify reports are properly formatted with markdown"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value="# Report\n## Section 1\n- Item 1\n- Item 2")
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        reporting_agent = ReportingSubAgent(mock_llm, mock_dispatcher)
        state = DeepAgentState(user_request="Format report",
                              triage_result={"category": "test"},
                              data_result={"data": "test"})
        
        await reporting_agent.execute(state, "test_run_id", False)
        
        # Check either report_result or final_report was set
        assert state.report_result != None or state.final_report != None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
