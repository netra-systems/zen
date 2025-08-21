"""
Business Value Test Fixtures - Mock Setup and Data Generation
Provides all fixtures and mock configurations for business value critical tests
"""

import pytest
import json
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path


class BusinessValueFixtures:
    """Centralized fixture provider for business value tests"""

    @pytest.fixture
    def mock_workload_data(self):
        """Generate realistic workload data for testing"""
        usage_metrics = self._generate_usage_metrics()
        error_logs = self._generate_error_logs()
        return self._build_workload_data(usage_metrics, error_logs)

    def _generate_usage_metrics(self):
        """Generate usage metrics for workload data"""
        models = ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]
        return [self._create_usage_metric(i, models) for i in range(100)]

    def _create_usage_metric(self, i, models):
        """Create single usage metric entry"""
        return {
            "timestamp": datetime.now() - timedelta(hours=i),
            "model": random.choice(models),
            "tokens_input": random.randint(500, 3000),
            "tokens_output": random.randint(200, 1500),
            "latency_ms": random.randint(200, 2000),
            "cost_usd": random.uniform(0.01, 0.5)
        }

    def _generate_error_logs(self):
        """Generate error logs for workload data"""
        error_types = ["timeout", "rate_limit", "api_error"]
        services = ["openai", "anthropic"]
        return [self._create_error_log(i, error_types, services) for i in range(10)]

    def _create_error_log(self, i, error_types, services):
        """Create single error log entry"""
        return {
            "timestamp": datetime.now() - timedelta(hours=i*2),
            "error_type": random.choice(error_types),
            "service": random.choice(services),
            "retry_count": random.randint(0, 3)
        }

    def _build_workload_data(self, usage_metrics, error_logs):
        """Build complete workload data dictionary"""
        return {
            "usage_metrics": usage_metrics,
            "error_logs": error_logs,
            "monthly_cost": 45000,
            "peak_latency_p95": 1800,
            "average_tokens_per_request": 2500
        }

    @pytest.fixture
    def mock_db_session(self):
        """Setup mock database session"""
        session = AsyncMock(spec=AsyncSession)
        self._configure_db_session(session)
        return session

    def _configure_db_session(self, session):
        """Configure database session mocks"""
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

    @pytest.fixture  
    def mock_llm_manager(self, mock_workload_data):
        """Setup mock LLM manager with realistic responses"""
        llm_manager = Mock(spec=LLMManager)
        ask_llm_mock = self._create_ask_llm_mock(mock_workload_data)
        call_llm_mock = self._create_call_llm_mock()
        self._configure_llm_manager(llm_manager, ask_llm_mock, call_llm_mock)
        return llm_manager

    def _create_ask_llm_mock(self, mock_workload_data):
        """Create async mock function for LLM ask_llm method"""
        async def mock_ask_llm(prompt, llm_config_name=None, *args, **kwargs):
            return self._get_llm_response_by_type(prompt, llm_config_name, mock_workload_data)
        return mock_ask_llm

    def _create_call_llm_mock(self):
        """Create async mock for call_llm method"""
        return AsyncMock(return_value={"content": "Analysis complete", "tool_calls": []})

    def _configure_llm_manager(self, llm_manager, ask_llm_mock, call_llm_mock):
        """Configure LLM manager with mocks"""
        llm_manager.ask_llm = ask_llm_mock
        llm_manager.call_llm = call_llm_mock

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
        action = self._get_sample_action()
        post_impl = self._get_post_implementation_config()
        cost_benefit = self._get_cost_benefit_analysis()
        return self._build_actions_response(action, post_impl, cost_benefit)

    def _build_actions_response(self, action, post_impl, cost_benefit):
        """Build complete actions response"""
        return json.dumps({
            "action_plan_summary": "Implement model routing and caching optimizations",
            "total_estimated_time": "1 week",
            "required_approvals": [],
            "actions": [action],
            "execution_timeline": [],
            "supply_config_updates": [],
            "post_implementation": post_impl,
            "cost_benefit_analysis": cost_benefit
        })

    def _get_sample_action(self):
        """Get sample action for actions response"""
        impl_details = self._get_implementation_details()
        risk_assessment = self._get_risk_assessment()
        monitoring_setup = self._get_monitoring_setup()
        return self._build_sample_action(impl_details, risk_assessment, monitoring_setup)

    def _build_sample_action(self, impl_details, risk_assessment, monitoring_setup):
        """Build complete sample action"""
        return {
            "action_id": "act_001",
            "action_type": "configuration",
            "name": "Audit current model usage",
            "description": "Analyze current GPT-4 usage patterns",
            "priority": "high",
            "dependencies": [],
            "estimated_duration": "2 days",
            "implementation_details": impl_details,
            "validation_steps": [],
            "success_criteria": ["Usage audit completed"],
            "rollback_procedure": {"steps": [], "estimated_time": "0"},
            "monitoring_setup": monitoring_setup,
            "risk_assessment": risk_assessment
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

    def _get_risk_assessment(self):
        """Get risk assessment for action"""
        return {
            "risk_level": "low",
            "potential_impacts": [],
            "mitigation_measures": []
        }

    def _get_monitoring_setup(self):
        """Get monitoring setup for action"""
        return {
            "metrics_to_track": [],
            "alert_thresholds": [],
            "dashboard_updates": []
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
            "expected_benefits": {
                "cost_savings_per_month": 18000,
                "performance_improvement_percentage": 0,
                "roi_months": 1
            }
        }

    def _get_data_response(self, mock_workload_data):
        """Get data agent response"""
        key_findings = self._get_key_findings()
        return json.dumps({
            "data_sources": ["usage_logs", "cost_reports", "performance_metrics"],
            "key_findings": key_findings,
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
        recommendations = self._get_optimization_recommendations()
        return json.dumps({
            "recommendations": recommendations,
            "total_potential_savings": 18000,
            "implementation_effort": "2 weeks"
        })

    def _get_optimization_recommendations(self):
        """Get optimization recommendations"""
        return [
            self._get_model_switch_recommendation(),
            self._get_caching_recommendation(),
            self._get_batch_processing_recommendation()
        ]

    def _get_model_switch_recommendation(self):
        """Get model switch recommendation"""
        return {
            "action": "Switch to gpt-3.5-turbo for non-critical requests",
            "estimated_savings": "40% cost reduction",
            "impact": "minimal quality impact for 70% of use cases"
        }

    def _get_caching_recommendation(self):
        """Get caching recommendation"""
        return {
            "action": "Implement response caching",
            "estimated_savings": "15% cost reduction",
            "impact": "< 100ms latency for cached responses"
        }

    def _get_batch_processing_recommendation(self):
        """Get batch processing recommendation"""
        return {
            "action": "Use batch processing for analytics",
            "estimated_savings": "25% cost reduction on batch jobs",
            "impact": "2-3 hour delay acceptable for reports"
        }

    def _get_default_response(self):
        """Get default agent response"""
        exec_metrics = self._get_executive_metrics()
        return json.dumps({
            "executive_summary": "Identified $18,000/month savings opportunity",
            "key_metrics": exec_metrics,
            "visualizations": ["cost_trend_chart", "model_usage_pie", "latency_histogram"]
        })

    def _get_executive_metrics(self):
        """Get executive metrics"""
        return {
            "current_cost": "$45,000/month",
            "projected_cost": "$27,000/month",
            "roi_timeframe": "1 month"
        }

    @pytest.fixture
    def mock_websocket_manager(self):
        """Setup mock WebSocket manager"""
        manager = Mock()
        self._configure_websocket_manager(manager)
        return manager

    def _configure_websocket_manager(self, manager):
        """Configure WebSocket manager mocks"""
        manager.send_message = AsyncMock()
        manager.send_sub_agent_update = AsyncMock()
        manager.send_agent_log = AsyncMock()
        manager.send_error = AsyncMock()

    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Setup mock tool dispatcher with realistic responses"""
        dispatcher = Mock(spec=ApexToolSelector)
        tool_mock = self._create_tool_mock()
        dispatcher.dispatch_tool = AsyncMock(side_effect=tool_mock)
        return dispatcher

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

    @pytest.fixture
    def mock_supervisor(self, mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher):
        """Setup mock supervisor with all dependencies"""
        with patch('app.services.state_persistence_service.state_persistence_service'):
            supervisor = Supervisor(mock_db_session, mock_llm_manager, 
                                   mock_websocket_manager, mock_tool_dispatcher)
            self._configure_supervisor_basic(supervisor)
            self._configure_supervisor_agents(supervisor, mock_websocket_manager)
            return supervisor

    def _configure_supervisor_basic(self, supervisor):
        """Configure supervisor basic properties"""
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())

    def _configure_supervisor_agents(self, supervisor, websocket_manager):
        """Configure supervisor sub-agents with WebSocket manager"""
        sub_agents = self._get_supervisor_sub_agents(supervisor)
        for agent in sub_agents:
            self._configure_single_agent(agent, websocket_manager, supervisor.user_id)

    def _configure_single_agent(self, agent, websocket_manager, user_id):
        """Configure single agent with required properties"""
        agent.websocket_manager = websocket_manager
        agent.user_id = user_id

    def _get_supervisor_sub_agents(self, supervisor):
        """Get sub-agents from supervisor (handles both consolidated and legacy)"""
        if hasattr(supervisor, '_impl') and supervisor._impl and hasattr(supervisor._impl, 'sub_agents'):
            return supervisor._impl.sub_agents
        elif hasattr(supervisor, 'sub_agents'):
            return supervisor.sub_agents
        return []

    @pytest.fixture
    def setup_test_infrastructure(self, mock_supervisor, mock_db_session, mock_llm_manager, 
                                  mock_websocket_manager, mock_tool_dispatcher, mock_workload_data):
        """Setup complete test infrastructure with realistic mocks"""
        agent_service = AgentService(mock_supervisor)
        agent_service.websocket_manager = mock_websocket_manager
        return self._build_infrastructure_dict(mock_supervisor, agent_service, mock_db_session, 
                                               mock_llm_manager, mock_websocket_manager, 
                                               mock_tool_dispatcher, mock_workload_data)

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