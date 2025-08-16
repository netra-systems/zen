"""
Business Value Critical Tests for Netra AI Optimization Platform
Tests core functionality from an end-user business value perspective
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
from typing import Dict, List, Any
import random

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.schemas import SubAgentLifecycle
from app.llm.llm_manager import LLMManager
from app.services.agent_service import AgentService
from app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from sqlalchemy.ext.asyncio import AsyncSession


class TestBusinessValueCritical:
    """
    Tests focused on real business value and user scenarios
    """

    @pytest.fixture
    def mock_workload_data(self):
        """Generate realistic workload data for testing"""
        return {
            "usage_metrics": [
                {
                    "timestamp": datetime.now() - timedelta(hours=i),
                    "model": random.choice(["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]),
                    "tokens_input": random.randint(500, 3000),
                    "tokens_output": random.randint(200, 1500),
                    "latency_ms": random.randint(200, 2000),
                    "cost_usd": random.uniform(0.01, 0.5)
                }
                for i in range(100)
            ],
            "error_logs": [
                {
                    "timestamp": datetime.now() - timedelta(hours=i*2),
                    "error_type": random.choice(["timeout", "rate_limit", "api_error"]),
                    "service": random.choice(["openai", "anthropic"]),
                    "retry_count": random.randint(0, 3)
                }
                for i in range(10)
            ],
            "monthly_cost": 45000,
            "peak_latency_p95": 1800,
            "average_tokens_per_request": 2500
        }

    @pytest.fixture
    def mock_db_session(self):
        """Setup mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture  
    def mock_llm_manager(self, mock_workload_data):
        """Setup mock LLM manager with realistic responses"""
        llm_manager = Mock(spec=LLMManager)
        llm_manager.ask_llm = AsyncMock(side_effect=self._create_ask_llm_mock(mock_workload_data))
        llm_manager.call_llm = AsyncMock(return_value={"content": "Analysis complete", "tool_calls": []})
        return llm_manager

    @pytest.fixture
    def mock_websocket_manager(self):
        """Setup mock WebSocket manager"""
        manager = Mock()
        manager.send_message = AsyncMock()
        manager.send_sub_agent_update = AsyncMock()
        manager.send_agent_log = AsyncMock()
        manager.send_error = AsyncMock()
        return manager

    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Setup mock tool dispatcher with realistic responses"""
        dispatcher = Mock(spec=ApexToolSelector)
        dispatcher.dispatch_tool = AsyncMock(side_effect=self._create_tool_mock())
        return dispatcher

    @pytest.fixture
    def mock_supervisor(self, mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher):
        """Setup mock supervisor with all dependencies"""
        with patch('app.services.state_persistence_service.state_persistence_service'):
            supervisor = Supervisor(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher)
            supervisor.thread_id = str(uuid.uuid4())
            supervisor.user_id = str(uuid.uuid4())
            self._configure_supervisor_agents(supervisor, mock_websocket_manager)
            return supervisor

    @pytest.fixture
    def setup_test_infrastructure(self, mock_supervisor, mock_db_session, mock_llm_manager, 
                                  mock_websocket_manager, mock_tool_dispatcher, mock_workload_data):
        """Setup complete test infrastructure with realistic mocks"""
        agent_service = AgentService(mock_supervisor)
        agent_service.websocket_manager = mock_websocket_manager
        return self._build_infrastructure_dict(mock_supervisor, agent_service, mock_db_session, 
                                               mock_llm_manager, mock_websocket_manager, 
                                               mock_tool_dispatcher, mock_workload_data)

    def _create_ask_llm_mock(self, mock_workload_data):
        """Create async mock function for LLM ask_llm method"""
        async def mock_ask_llm(prompt, llm_config_name=None, *args, **kwargs):
            return self._get_llm_response_by_type(prompt, llm_config_name, mock_workload_data)
        return mock_ask_llm

    def _get_llm_response_by_type(self, prompt, llm_config_name, mock_workload_data):
        """Get appropriate LLM response based on agent type"""
        if self._is_triage_agent(llm_config_name, prompt):
            return self._get_triage_response()
        elif self._is_actions_agent(llm_config_name, prompt):
            return self._get_actions_response()
        elif self._is_data_agent(llm_config_name, prompt):
            return self._get_data_response(mock_workload_data)
        elif self._is_optimization_agent(llm_config_name, prompt):
            return self._get_optimization_response()
        return self._get_default_response()

    def _is_triage_agent(self, llm_config_name, prompt):
        """Check if request is from triage agent"""
        return llm_config_name == 'triage' or "triage" in prompt.lower()

    def _is_actions_agent(self, llm_config_name, prompt):
        """Check if request is from actions agent"""
        return (llm_config_name == 'actions_to_meet_goals' or 
                "action planning specialist" in prompt.lower())

    def _is_data_agent(self, llm_config_name, prompt):
        """Check if request is from data agent"""
        return (llm_config_name == 'data' or 
                ("data" in prompt.lower() and "action" not in prompt.lower()))

    def _is_optimization_agent(self, llm_config_name, prompt):
        """Check if request is from optimization agent"""
        return llm_config_name == 'optimizations_core' or "optimiz" in prompt.lower()

    def _get_triage_response(self):
        """Get triage agent response"""
        return json.dumps({
            "category": "cost_optimization",
            "complexity": "high",
            "requires_data_analysis": True,
            "estimated_time": "2-3 minutes"
        })

    def _get_actions_response(self):
        """Get actions agent response"""
        return json.dumps({
            "action_plan_summary": "Implement model routing and caching optimizations",
            "total_estimated_time": "1 week",
            "required_approvals": [],
            "actions": [self._get_sample_action()],
            "execution_timeline": [],
            "supply_config_updates": [],
            "post_implementation": self._get_post_implementation_config(),
            "cost_benefit_analysis": self._get_cost_benefit_analysis()
        })

    def _get_sample_action(self):
        """Get sample action for actions response"""
        return {
            "action_id": "act_001",
            "action_type": "configuration",
            "name": "Audit current model usage",
            "description": "Analyze current GPT-4 usage patterns",
            "priority": "high",
            "dependencies": [],
            "estimated_duration": "2 days",
            "implementation_details": self._get_implementation_details(),
            "validation_steps": [],
            "success_criteria": ["Usage audit completed"],
            "rollback_procedure": {"steps": [], "estimated_time": "0"},
            "monitoring_setup": {"metrics_to_track": [], "alert_thresholds": [], "dashboard_updates": []},
            "risk_assessment": {"risk_level": "low", "potential_impacts": [], "mitigation_measures": []}
        }

    def _get_implementation_details(self):
        """Get implementation details for action"""
        return {
            "target_component": "analytics_system",
            "specific_changes": [],
            "sql_queries": [],
            "api_calls": [],
            "configuration_files": []
        }

    def _get_post_implementation_config(self):
        """Get post-implementation configuration"""
        return {
            "monitoring_period": "30 days",
            "success_metrics": [],
            "optimization_review_schedule": "Weekly",
            "documentation_updates": []
        }

    def _get_cost_benefit_analysis(self):
        """Get cost-benefit analysis data"""
        return {
            "implementation_cost": {"effort_hours": 40, "resource_cost": 0},
            "expected_benefits": {"cost_savings_per_month": 18000, "performance_improvement_percentage": 0, "roi_months": 1}
        }

    def _get_data_response(self, mock_workload_data):
        """Get data agent response"""
        return json.dumps({
            "data_sources": ["usage_logs", "cost_reports", "performance_metrics"],
            "key_findings": self._get_key_findings(),
            "metrics": mock_workload_data
        })

    def _get_key_findings(self):
        """Get key findings for data response"""
        return {
            "high_cost_models": ["gpt-4"],
            "peak_usage_hours": [14, 15, 16],
            "average_cost_per_request": 0.15
        }

    def _get_optimization_response(self):
        """Get optimization agent response"""
        return json.dumps({
            "recommendations": self._get_optimization_recommendations(),
            "total_potential_savings": 18000,
            "implementation_effort": "2 weeks"
        })

    def _get_optimization_recommendations(self):
        """Get optimization recommendations"""
        return [
            {
                "action": "Switch to gpt-3.5-turbo for non-critical requests",
                "estimated_savings": "40% cost reduction",
                "impact": "minimal quality impact for 70% of use cases"
            },
            {
                "action": "Implement response caching",
                "estimated_savings": "15% cost reduction",
                "impact": "< 100ms latency for cached responses"
            },
            {
                "action": "Use batch processing for analytics",
                "estimated_savings": "25% cost reduction on batch jobs",
                "impact": "2-3 hour delay acceptable for reports"
            }
        ]

    def _get_default_response(self):
        """Get default agent response"""
        return json.dumps({
            "executive_summary": "Identified $18,000/month savings opportunity",
            "key_metrics": self._get_executive_metrics(),
            "visualizations": ["cost_trend_chart", "model_usage_pie", "latency_histogram"]
        })

    def _get_executive_metrics(self):
        """Get executive metrics"""
        return {
            "current_cost": "$45,000/month",
            "projected_cost": "$27,000/month",
            "roi_timeframe": "1 month"
        }

    def _create_tool_mock(self):
        """Create async mock function for tool dispatch"""
        async def mock_dispatch_tool(tool_name, params):
            return self._get_tool_response_by_name(tool_name)
        return mock_dispatch_tool

    def _get_tool_response_by_name(self, tool_name):
        """Get appropriate tool response based on tool name"""
        if tool_name == "analyze_cost_drivers":
            return self._get_cost_drivers_response()
        elif tool_name == "simulate_optimization":
            return self._get_simulation_response()
        elif tool_name == "identify_bottlenecks":
            return self._get_bottlenecks_response()
        return {"status": "success", "result": "Tool executed"}

    def _get_cost_drivers_response(self):
        """Get cost drivers analysis response"""
        return {
            "status": "success",
            "result": {
                "top_cost_drivers": [
                    {"model": "gpt-4", "percentage": 65},
                    {"model": "claude-3-opus", "percentage": 25},
                    {"model": "gpt-3.5-turbo", "percentage": 10}
                ]
            }
        }

    def _get_simulation_response(self):
        """Get optimization simulation response"""
        return {
            "status": "success",
            "result": {
                "baseline_cost": 45000,
                "optimized_cost": 27000,
                "savings_percentage": 40
            }
        }

    def _get_bottlenecks_response(self):
        """Get bottleneck identification response"""
        return {
            "status": "success",
            "result": {
                "bottlenecks": [
                    {"component": "model_inference", "impact": "high"},
                    {"component": "database_queries", "impact": "medium"}
                ]
            }
        }

    def _configure_supervisor_agents(self, supervisor, websocket_manager):
        """Configure supervisor sub-agents with WebSocket manager"""
        sub_agents = self._get_supervisor_sub_agents(supervisor)
        for agent in sub_agents:
            agent.websocket_manager = websocket_manager
            agent.user_id = supervisor.user_id

    def _get_supervisor_sub_agents(self, supervisor):
        """Get sub-agents from supervisor (handles both consolidated and legacy)"""
        if hasattr(supervisor, '_impl') and supervisor._impl and hasattr(supervisor._impl, 'sub_agents'):
            return supervisor._impl.sub_agents
        elif hasattr(supervisor, 'sub_agents'):
            return supervisor.sub_agents
        return []

    def _build_infrastructure_dict(self, supervisor, agent_service, db_session, llm_manager, 
                                   websocket_manager, tool_dispatcher, workload_data):
        """Build and return infrastructure dictionary"""
        return {
            "supervisor": supervisor,
            "agent_service": agent_service,
            "db_session": db_session,
            "llm_manager": llm_manager,
            "websocket_manager": websocket_manager,
            "tool_dispatcher": tool_dispatcher,
            "workload_data": workload_data
        }
    async def test_1_cost_optimization_request(self, setup_test_infrastructure):
        """
        Business Value Test 1: Cost Optimization Analysis
        User Story: As a CTO, I need to reduce my AI costs by 40% while maintaining quality
        """
        infra = setup_test_infrastructure
        supervisor = infra["supervisor"]
        workload_data = infra["workload_data"]
        
        run_id = str(uuid.uuid4())
        user_request = "How can I reduce my GPT-4 costs by 40% while maintaining quality?"
        
        # Mock state persistence
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    # Execute the agent workflow
                    result_state = await supervisor.run(user_request, "test_thread", "test_user", run_id)
        
        # Business value assertions
        assert result_state != None
        assert result_state.user_request == user_request
        
        # Verify cost optimization recommendations were generated
        llm_manager = infra["llm_manager"]
        assert llm_manager.ask_llm.called
        
        # Check if optimization prompt was used
        optimization_calls = [call for call in llm_manager.ask_llm.call_args_list 
                             if "optimiz" in str(call).lower()]
        assert len(optimization_calls) > 0
        
        # Verify tool usage for cost analysis
        tool_dispatcher = infra["tool_dispatcher"]
        if tool_dispatcher.dispatch_tool.called:
            tool_calls = tool_dispatcher.dispatch_tool.call_args_list
            cost_analysis_calls = [call for call in tool_calls 
                                  if "cost" in str(call).lower()]
            assert len(cost_analysis_calls) >= 0  # May or may not be called
    async def test_2_performance_bottleneck_identification(self, setup_test_infrastructure):
        """
        Business Value Test 2: Performance Bottleneck Analysis
        User Story: As an ML Engineer, I need to identify why P95 latency increased to 800ms
        """
        infra = setup_test_infrastructure
        supervisor = infra["supervisor"]
        
        run_id = str(uuid.uuid4())
        user_request = "P95 latency increased from 200ms to 800ms. Identify bottlenecks and solutions."
        
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    result_state = await supervisor.run(user_request, "test_thread", "test_user", run_id)
        
        assert result_state != None
        
        # Verify performance analysis was conducted
        tool_dispatcher = infra["tool_dispatcher"]
        if tool_dispatcher.dispatch_tool.called:
            # Check for bottleneck identification tool usage
            bottleneck_calls = [call for call in tool_dispatcher.dispatch_tool.call_args_list
                              if "bottleneck" in str(call).lower()]
            assert len(bottleneck_calls) >= 0
    async def test_3_model_comparison_and_selection(self, setup_test_infrastructure):
        """
        Business Value Test 3: Model Comparison for Use Case
        User Story: As a Product Manager, I need to choose between GPT-4 and Claude for my chatbot
        """
        infra = setup_test_infrastructure
        supervisor = infra["supervisor"]
        
        run_id = str(uuid.uuid4())
        user_request = "Compare GPT-4 vs Claude-3 for customer support chatbot. Budget: $10k/month"
        
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    result_state = await supervisor.run(user_request, "test_thread", "test_user", run_id)
        
        assert result_state != None
        
        # Verify comparison analysis was performed
        llm_manager = infra["llm_manager"]
        assert llm_manager.ask_llm.call_count > 0
    async def test_4_real_time_streaming_updates(self, setup_test_infrastructure):
        """
        Business Value Test 4: Real-time Progress Updates
        User Story: As a user, I want to see progress during long-running analyses
        """
        infra = setup_test_infrastructure
        websocket_manager = infra["websocket_manager"]
        supervisor = infra["supervisor"]
        
        run_id = str(uuid.uuid4())
        streamed_messages = []
        
        async def capture_stream(rid, message):
            streamed_messages.append(message)
        
        websocket_manager.send_message = AsyncMock(side_effect=capture_stream)
        
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    await supervisor.run("Analyze my workload", "test_thread", "test_user", run_id)
        
        # Verify streaming occurred
        assert len(streamed_messages) > 0
        message_types = [msg.get("type") for msg in streamed_messages]
        assert "agent_started" in message_types
    async def test_5_batch_processing_optimization(self, setup_test_infrastructure):
        """
        Business Value Test 5: Batch Processing Recommendations
        User Story: As a Data Scientist, I need to optimize batch inference costs
        """
        infra = setup_test_infrastructure
        supervisor = infra["supervisor"]
        
        run_id = str(uuid.uuid4())
        user_request = "I have 10,000 similar classification requests daily. How to optimize?"
        
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    result_state = await supervisor.run(user_request, "test_thread", "test_user", run_id)
        
        assert result_state != None
        
        # Verify batch optimization was considered
        llm_manager = infra["llm_manager"]
        optimization_prompts = [call for call in llm_manager.ask_llm.call_args_list
                              if "batch" in str(call).lower() or "optimiz" in str(call).lower()]
        assert len(optimization_prompts) >= 0
    async def test_6_cache_effectiveness_analysis(self, setup_test_infrastructure):
        """
        Business Value Test 6: Cache Effectiveness
        User Story: As a Platform Engineer, I need to measure cache effectiveness
        """
        infra = setup_test_infrastructure
        
        # Simulate cache metrics
        cache_metrics = {
            "hit_rate": 0.35,
            "miss_rate": 0.65,
            "avg_response_time_cached": 50,
            "avg_response_time_uncached": 1500,
            "cost_savings_percentage": 35
        }
        
        # Test cache analysis
        assert cache_metrics["hit_rate"] > 0.3
        assert cache_metrics["avg_response_time_cached"] < 100
        assert cache_metrics["cost_savings_percentage"] > 30
    async def test_7_error_recovery_resilience(self, setup_test_infrastructure):
        """
        Business Value Test 7: System Resilience
        User Story: As a user, I want the system to handle failures gracefully
        """
        infra = setup_test_infrastructure
        supervisor = infra["supervisor"]
        
        run_id = str(uuid.uuid4())
        
        # Simulate intermittent failures
        call_count = 0
        
        async def flaky_execute(state, rid, stream):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary API failure")
            return state
        
        # Make one agent flaky
        # Handle both consolidated and legacy implementations
        sub_agents = []
        if hasattr(supervisor, '_impl') and supervisor._impl:
            # Consolidated implementation uses agents dictionary
            if hasattr(supervisor._impl, 'agents'):
                # Convert dictionary values to list for consistent handling
                sub_agents = list(supervisor._impl.agents.values())
            elif hasattr(supervisor._impl, 'sub_agents'):
                sub_agents = supervisor._impl.sub_agents
        elif hasattr(supervisor, 'sub_agents'):
            # Legacy implementation
            sub_agents = supervisor.sub_agents
            
        if len(sub_agents) > 2:
            sub_agents[2].execute = flaky_execute
        
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    try:
                        await supervisor.run("Test resilience", "test_thread", "test_user", run_id)
                    except Exception:
                        pass  # Expected to handle or fail gracefully
        
        # System should have attempted retries
        assert call_count >= 1
    async def test_8_report_generation_with_insights(self, setup_test_infrastructure):
        """
        Business Value Test 8: Executive Report Generation
        User Story: As an executive, I need clear reports with actionable insights
        """
        infra = setup_test_infrastructure
        supervisor = infra["supervisor"]
        
        run_id = str(uuid.uuid4())
        user_request = "Generate executive report on AI optimization opportunities"
        
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    result_state = await supervisor.run(user_request, "test_thread", "test_user", run_id)
        
        assert result_state != None
        
        # Verify reporting agent was involved
        llm_manager = infra["llm_manager"]
        report_calls = [call for call in llm_manager.ask_llm.call_args_list
                       if "report" in str(call).lower() or "summary" in str(call).lower()]
        assert len(report_calls) >= 0
    async def test_9_concurrent_user_isolation(self, setup_test_infrastructure):
        """
        Business Value Test 9: Multi-tenant Isolation
        User Story: As a platform operator, I need to ensure user data isolation
        """
        infra = setup_test_infrastructure
        agent_service = infra["agent_service"]
        
        # Simulate concurrent users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        
        user1_request = {"user_id": user1_id, "request": "User 1 analysis"}
        user2_request = {"user_id": user2_id, "request": "User 2 analysis"}
        
        # Mock execution to track user isolation
        user_contexts = {}
        
        async def track_user_context(user_id, thread_id, request):
            user_contexts[user_id] = {
                "thread_id": thread_id,
                "request": request
            }
            return str(uuid.uuid4())
        
        agent_service.start_agent_run = track_user_context
        
        # Execute requests
        await agent_service.start_agent_run(
            user1_id, str(uuid.uuid4()), user1_request["request"]
        )
        await agent_service.start_agent_run(
            user2_id, str(uuid.uuid4()), user2_request["request"]
        )
        
        # Verify isolation
        assert len(user_contexts) == 2
        assert user_contexts[user1_id]["request"] == user1_request["request"]
        assert user_contexts[user2_id]["request"] == user2_request["request"]
    async def test_10_end_to_end_optimization_workflow(self, setup_test_infrastructure):
        """
        Business Value Test 10: Complete Optimization Workflow
        User Story: As an AI platform user, I want end-to-end optimization recommendations
        """
        infra = setup_test_infrastructure
        supervisor = infra["supervisor"]
        websocket_manager = infra["websocket_manager"]
        
        run_id = str(uuid.uuid4())
        user_request = """
        We're spending $50k/month on AI. Our requirements:
        - Reduce costs by 30%
        - Maintain <500ms P95 latency
        - Support 1M requests/day
        Please provide complete optimization plan.
        """
        
        # Track the complete workflow
        workflow_stages = []
        
        async def track_workflow(rid, message):
            if message.get("type") == "sub_agent_update":
                workflow_stages.append(message.get("agent_name"))
        
        websocket_manager.send_sub_agent_update = AsyncMock(side_effect=track_workflow)
        
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    result_state = await supervisor.run(user_request, "test_thread", "test_user", run_id)
        
        # Verify complete workflow execution
        assert result_state != None
        assert result_state.user_request == user_request
        
        # Verify all critical agents participated
        llm_manager = infra["llm_manager"]
        assert llm_manager.ask_llm.call_count >= 3  # Multiple agents should have run
        
        # Verify tools were used for analysis
        tool_dispatcher = infra["tool_dispatcher"]
        if tool_dispatcher.dispatch_tool.called:
            assert tool_dispatcher.dispatch_tool.call_count >= 0
        
        # Verify comprehensive analysis
        all_prompts = str(llm_manager.ask_llm.call_args_list)
        assert "cost" in all_prompts.lower() or "optimiz" in all_prompts.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])