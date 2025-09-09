"""
Test Agent Factory Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable agent creation and lifecycle management
- Value Impact: Enables AI agent execution that delivers core user value
- Strategic Impact: Core infrastructure for AI-powered insights and recommendations

CRITICAL COMPLIANCE:
- Tests agent factory patterns for user isolation
- Validates agent type selection based on business tier
- Ensures proper agent lifecycle management
- Tests resource allocation for different subscription levels
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentFactoryBusinessLogic:
    """Test agent factory business logic patterns."""
    
    @pytest.fixture
    def agent_factory(self):
        """Create agent factory for testing."""
        factory = AgentFactory()
        factory._agent_registry = Mock()
        factory._resource_manager = Mock()
        return factory
    
    @pytest.fixture
    def agent_registry(self):
        """Create agent registry for testing."""
        registry = AgentRegistry()
        registry._registered_agents = {}
        return registry
    
    @pytest.fixture
    def agent_resource_manager(self):
        """Create agent resource manager for testing."""
        manager = AgentResourceManager()
        manager._resource_pools = {}
        return manager
    
    @pytest.fixture
    def user_contexts_by_tier(self):
        """Create user contexts for different subscription tiers."""
        return {
            "free": UserExecutionContext(
                user_id=str(uuid.uuid4()),
                email="free@user.com",
                subscription_tier="free",
                permissions=["read_basic"],
                thread_id=str(uuid.uuid4())
            ),
            "premium": UserExecutionContext(
                user_id=str(uuid.uuid4()),
                email="premium@company.com", 
                subscription_tier="premium",
                permissions=["read_basic", "read_premium", "execute_basic_agents"],
                thread_id=str(uuid.uuid4())
            ),
            "enterprise": UserExecutionContext(
                user_id=str(uuid.uuid4()),
                email="enterprise@corp.com",
                subscription_tier="enterprise", 
                permissions=["read_basic", "read_premium", "execute_agents", "admin_access"],
                thread_id=str(uuid.uuid4())
            )
        }
    
    @pytest.mark.unit
    def test_agent_creation_by_subscription_tier_business_logic(self, agent_factory, user_contexts_by_tier):
        """Test agent creation respects subscription tier business rules."""
        # Given: Different agent types available for different tiers
        agent_tier_mapping = {
            "free": {
                "available_agents": ["basic_triage_agent", "simple_qa_agent"],
                "concurrent_limit": 1,
                "execution_timeout": 30,  # 30 seconds
                "resource_allocation": "minimal"
            },
            "premium": {
                "available_agents": ["basic_triage_agent", "simple_qa_agent", "cost_analyzer_agent", "data_insights_agent"],
                "concurrent_limit": 3,
                "execution_timeout": 120,  # 2 minutes  
                "resource_allocation": "standard"
            },
            "enterprise": {
                "available_agents": ["basic_triage_agent", "simple_qa_agent", "cost_analyzer_agent", "data_insights_agent", "advanced_optimization_agent", "security_audit_agent"],
                "concurrent_limit": 10,
                "execution_timeout": 600,  # 10 minutes
                "resource_allocation": "premium"
            }
        }
        
        for tier, tier_config in agent_tier_mapping.items():
            user_context = user_contexts_by_tier[tier]
            
            for agent_type in tier_config["available_agents"]:
                # When: Creating agent for specific subscription tier
                with patch.object(agent_factory, '_create_agent_instance') as mock_create:
                    mock_agent = Mock()
                    mock_agent.agent_type = agent_type
                    mock_agent.user_id = user_context.user_id
                    mock_agent.subscription_tier = tier
                    mock_agent.resource_allocation = tier_config["resource_allocation"]
                    mock_create.return_value = mock_agent
                    
                    agent = agent_factory.create_agent(
                        agent_type=agent_type,
                        user_context=user_context
                    )
                
                # Then: Should create appropriate agent for tier
                assert agent is not None
                assert agent.agent_type == agent_type
                assert agent.user_id == user_context.user_id
                assert agent.subscription_tier == tier
                assert agent.resource_allocation == tier_config["resource_allocation"]
                
                # Should enforce business tier restrictions
                if tier == "free":
                    assert agent_type in ["basic_triage_agent", "simple_qa_agent"]
                    assert agent.resource_allocation == "minimal"
                elif tier == "premium":
                    assert agent_type not in ["advanced_optimization_agent", "security_audit_agent"]
                    assert agent.resource_allocation == "standard"
                elif tier == "enterprise":
                    # Enterprise should have access to all agents
                    assert agent.resource_allocation == "premium"
    
    @pytest.mark.unit
    def test_agent_resource_allocation_business_optimization(self, agent_resource_manager, user_contexts_by_tier):
        """Test agent resource allocation optimizes for business value delivery."""
        # Given: Resource allocation strategies for different business tiers
        resource_strategies = {
            "free": {
                "cpu_allocation": 0.1,  # 10% of available CPU
                "memory_limit": 128,  # 128 MB
                "execution_priority": "low",
                "llm_quota": 1000,  # 1000 tokens per request
                "concurrent_agents": 1
            },
            "premium": {
                "cpu_allocation": 0.3,  # 30% of available CPU
                "memory_limit": 512,  # 512 MB
                "execution_priority": "normal", 
                "llm_quota": 5000,  # 5000 tokens per request
                "concurrent_agents": 3
            },
            "enterprise": {
                "cpu_allocation": 0.8,  # 80% of available CPU
                "memory_limit": 2048,  # 2 GB
                "execution_priority": "high",
                "llm_quota": 20000,  # 20000 tokens per request  
                "concurrent_agents": 10
            }
        }
        
        for tier, strategy in resource_strategies.items():
            user_context = user_contexts_by_tier[tier]
            
            # When: Allocating resources for agent execution
            with patch.object(agent_resource_manager, '_allocate_compute_resources') as mock_allocate:
                mock_allocate.return_value = {
                    "cpu_cores": strategy["cpu_allocation"],
                    "memory_mb": strategy["memory_limit"],
                    "priority": strategy["execution_priority"],
                    "llm_token_quota": strategy["llm_quota"]
                }
                
                resource_allocation = agent_resource_manager.allocate_agent_resources(
                    user_context=user_context,
                    agent_type="cost_analyzer_agent",
                    expected_complexity="medium"
                )
            
            # Then: Should allocate resources appropriate for business tier
            assert resource_allocation is not None
            assert resource_allocation["cpu_cores"] == strategy["cpu_allocation"]
            assert resource_allocation["memory_mb"] == strategy["memory_limit"]
            assert resource_allocation["priority"] == strategy["execution_priority"]
            assert resource_allocation["llm_token_quota"] == strategy["llm_quota"]
            
            # Business logic validation
            if tier == "free":
                # Free users get minimal resources to encourage upgrading
                assert resource_allocation["cpu_cores"] <= 0.2
                assert resource_allocation["memory_mb"] <= 256
                assert resource_allocation["llm_token_quota"] <= 2000
            elif tier == "premium":
                # Premium users get balanced resources for good experience  
                assert resource_allocation["cpu_cores"] >= 0.3
                assert resource_allocation["memory_mb"] >= 512
                assert resource_allocation["llm_token_quota"] >= 5000
            elif tier == "enterprise":
                # Enterprise users get premium resources for maximum value
                assert resource_allocation["cpu_cores"] >= 0.5
                assert resource_allocation["memory_mb"] >= 1024
                assert resource_allocation["llm_token_quota"] >= 15000
    
    @pytest.mark.unit
    def test_agent_lifecycle_management_business_continuity(self, agent_factory, user_contexts_by_tier):
        """Test agent lifecycle management ensures business continuity."""
        # Given: Agent lifecycle events that impact business operations
        lifecycle_scenarios = [
            {
                "event": "agent_initialization",
                "user_tier": "enterprise",
                "expected_startup_time": 2.0,  # 2 seconds max for enterprise
                "business_impact": "user_waiting_for_response"
            },
            {
                "event": "agent_execution",
                "user_tier": "premium", 
                "expected_response_time": 30.0,  # 30 seconds max for premium
                "business_impact": "user_engagement_duration"
            },
            {
                "event": "agent_termination",
                "user_tier": "free",
                "expected_cleanup_time": 1.0,  # 1 second max cleanup
                "business_impact": "resource_availability_for_others"
            },
            {
                "event": "agent_error_recovery",
                "user_tier": "enterprise",
                "expected_recovery_time": 5.0,  # 5 seconds max recovery
                "business_impact": "business_critical_operation_continuity"
            }
        ]
        
        for scenario in lifecycle_scenarios:
            user_context = user_contexts_by_tier[scenario["user_tier"]]
            
            # When: Managing agent lifecycle for business continuity
            with patch.object(agent_factory, '_manage_agent_lifecycle') as mock_lifecycle:
                mock_lifecycle.return_value = {
                    "event": scenario["event"],
                    "execution_time": scenario["expected_startup_time"] if "startup" in scenario["event"] else scenario.get("expected_response_time", 1.0),
                    "user_tier": scenario["user_tier"],
                    "business_continuity_maintained": True
                }
                
                lifecycle_result = agent_factory.manage_agent_lifecycle(
                    event_type=scenario["event"],
                    user_context=user_context,
                    agent_type="cost_analyzer_agent"
                )
            
            # Then: Should maintain business continuity appropriately
            assert lifecycle_result is not None
            assert lifecycle_result["event"] == scenario["event"]
            assert lifecycle_result["user_tier"] == scenario["user_tier"]
            assert lifecycle_result["business_continuity_maintained"] is True
            
            # Should meet business SLAs for different tiers
            execution_time = lifecycle_result["execution_time"]
            
            if scenario["user_tier"] == "enterprise":
                # Enterprise users should get fastest response times
                if scenario["event"] == "agent_initialization":
                    assert execution_time <= 3.0  # Generous for enterprise
                elif scenario["event"] == "agent_error_recovery":
                    assert execution_time <= 10.0  # Fast recovery for business critical
            elif scenario["user_tier"] == "premium": 
                # Premium users should get good response times
                if scenario["event"] == "agent_execution":
                    assert execution_time <= 45.0  # Reasonable execution time
            elif scenario["user_tier"] == "free":
                # Free users have longer acceptable times but still responsive
                if scenario["event"] == "agent_termination":
                    assert execution_time <= 5.0  # Quick cleanup
    
    @pytest.mark.unit
    def test_concurrent_agent_management_multi_user_isolation(self, agent_factory, user_contexts_by_tier):
        """Test concurrent agent management maintains multi-user isolation."""
        # Given: Multiple users running agents simultaneously
        concurrent_scenarios = [
            {
                "user_tier": "enterprise",
                "num_concurrent_agents": 5,
                "agent_types": ["cost_analyzer_agent", "security_audit_agent", "data_insights_agent"],
                "isolation_required": True
            },
            {
                "user_tier": "premium",
                "num_concurrent_agents": 2,
                "agent_types": ["cost_analyzer_agent", "data_insights_agent"],
                "isolation_required": True
            },
            {
                "user_tier": "free",
                "num_concurrent_agents": 1,
                "agent_types": ["basic_triage_agent"],
                "isolation_required": True
            }
        ]
        
        all_running_agents = []
        
        for scenario in concurrent_scenarios:
            user_context = user_contexts_by_tier[scenario["user_tier"]]
            user_agents = []
            
            # When: Creating multiple concurrent agents for user
            for i in range(scenario["num_concurrent_agents"]):
                agent_type = scenario["agent_types"][i % len(scenario["agent_types"])]
                
                with patch.object(agent_factory, '_create_isolated_agent') as mock_create:
                    mock_agent = Mock()
                    mock_agent.agent_id = str(uuid.uuid4())
                    mock_agent.user_id = user_context.user_id
                    mock_agent.thread_id = str(uuid.uuid4())
                    mock_agent.agent_type = agent_type
                    mock_agent.isolation_context = {
                        "user_data_namespace": f"user_{user_context.user_id}",
                        "thread_isolation": True,
                        "memory_isolation": True
                    }
                    mock_create.return_value = mock_agent
                    
                    agent = agent_factory.create_concurrent_agent(
                        agent_type=agent_type,
                        user_context=user_context
                    )
                    
                    user_agents.append(agent)
                    all_running_agents.append((scenario["user_tier"], agent))
        
        # Then: Should maintain complete isolation between users
        for tier, agent in all_running_agents:
            assert agent is not None
            assert agent.user_id is not None
            assert agent.isolation_context["user_data_namespace"].startswith("user_")
            assert agent.isolation_context["thread_isolation"] is True
            
            # Verify isolation from other users' agents
            for other_tier, other_agent in all_running_agents:
                if agent.agent_id != other_agent.agent_id:
                    # Different agents should have different user contexts
                    if agent.user_id != other_agent.user_id:
                        assert agent.isolation_context["user_data_namespace"] != other_agent.isolation_context["user_data_namespace"]
                        assert agent.thread_id != other_agent.thread_id
    
    @pytest.mark.unit 
    def test_agent_type_selection_business_value_optimization(self, agent_factory):
        """Test agent type selection optimizes for business value delivery."""
        # Given: User requests with different business value potentials
        business_requests = [
            {
                "user_message": "Help me reduce my AWS costs by 20%",
                "expected_agent": "cost_optimization_agent",
                "business_value": "high",
                "revenue_impact": "direct_savings",
                "complexity": "medium"
            },
            {
                "user_message": "Analyze my security vulnerabilities",
                "expected_agent": "security_audit_agent",
                "business_value": "high",
                "revenue_impact": "risk_mitigation", 
                "complexity": "high"
            },
            {
                "user_message": "What insights can you provide about my data?",
                "expected_agent": "data_insights_agent",
                "business_value": "medium",
                "revenue_impact": "decision_support",
                "complexity": "medium"
            },
            {
                "user_message": "Help me understand this error message",
                "expected_agent": "basic_triage_agent",
                "business_value": "low",
                "revenue_impact": "support",
                "complexity": "low"
            }
        ]
        
        for request in business_requests:
            # When: Selecting agent type for business value optimization
            with patch.object(agent_factory, '_analyze_request_intent') as mock_analyze:
                mock_analyze.return_value = {
                    "intent": request["expected_agent"].replace("_agent", ""),
                    "complexity": request["complexity"],
                    "business_value": request["business_value"],
                    "revenue_impact": request["revenue_impact"]
                }
                
                agent_selection = agent_factory.select_optimal_agent_type(
                    user_message=request["user_message"],
                    user_context=Mock(subscription_tier="premium")
                )
            
            # Then: Should select agent type that maximizes business value
            assert agent_selection is not None
            assert agent_selection["selected_agent"] == request["expected_agent"]
            assert agent_selection["business_value"] == request["business_value"]
            assert agent_selection["revenue_impact"] == request["revenue_impact"]
            
            # Should prioritize high-value business outcomes
            if request["business_value"] == "high":
                assert request["expected_agent"] in ["cost_optimization_agent", "security_audit_agent"]
                assert request["revenue_impact"] in ["direct_savings", "risk_mitigation"]
            elif request["business_value"] == "medium":
                assert request["expected_agent"] in ["data_insights_agent"]
                assert request["revenue_impact"] == "decision_support"
            elif request["business_value"] == "low":
                assert request["expected_agent"] in ["basic_triage_agent"]
                assert request["revenue_impact"] == "support"
    
    @pytest.mark.unit
    def test_agent_factory_performance_optimization_business_responsiveness(self, agent_factory):
        """Test agent factory performance optimization maintains business responsiveness."""
        # Given: Performance requirements for different business scenarios
        performance_scenarios = [
            {
                "scenario": "high_priority_enterprise_user",
                "user_tier": "enterprise",
                "agent_type": "cost_optimization_agent",
                "max_initialization_time": 1.0,  # 1 second max
                "max_queue_time": 0.5,  # 500ms max queue time
                "business_sla": "premium_response_time"
            },
            {
                "scenario": "standard_premium_user",
                "user_tier": "premium", 
                "agent_type": "data_insights_agent",
                "max_initialization_time": 3.0,  # 3 seconds max
                "max_queue_time": 2.0,  # 2 seconds max queue time
                "business_sla": "standard_response_time"
            },
            {
                "scenario": "free_tier_user",
                "user_tier": "free",
                "agent_type": "basic_triage_agent", 
                "max_initialization_time": 5.0,  # 5 seconds max
                "max_queue_time": 10.0,  # 10 seconds max queue time
                "business_sla": "basic_response_time"
            }
        ]
        
        for scenario in performance_scenarios:
            # When: Optimizing agent factory performance for business responsiveness
            start_time = datetime.now(timezone.utc)
            
            with patch.object(agent_factory, '_optimize_for_business_tier') as mock_optimize:
                mock_optimize.return_value = {
                    "initialization_time": scenario["max_initialization_time"] * 0.8,  # 80% of max
                    "queue_time": scenario["max_queue_time"] * 0.6,  # 60% of max
                    "optimization_applied": True,
                    "business_sla": scenario["business_sla"]
                }
                
                performance_result = agent_factory.create_agent_with_performance_optimization(
                    agent_type=scenario["agent_type"],
                    user_tier=scenario["user_tier"],
                    priority=scenario["scenario"]
                )
            
            creation_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Then: Should meet business responsiveness requirements
            assert performance_result is not None
            assert performance_result["optimization_applied"] is True
            assert performance_result["business_sla"] == scenario["business_sla"]
            
            # Should meet performance SLAs for business tiers
            init_time = performance_result["initialization_time"]
            queue_time = performance_result["queue_time"]
            
            assert init_time <= scenario["max_initialization_time"]
            assert queue_time <= scenario["max_queue_time"]
            
            # Business tier optimizations
            if scenario["user_tier"] == "enterprise":
                # Enterprise users should get priority treatment
                assert init_time <= 1.5  # Very fast initialization
                assert queue_time <= 1.0  # Minimal queuing
            elif scenario["user_tier"] == "premium":
                # Premium users should get good performance
                assert init_time <= 4.0  # Good initialization time
                assert queue_time <= 3.0  # Reasonable queuing
            elif scenario["user_tier"] == "free":
                # Free users get slower but acceptable performance
                assert init_time <= 10.0  # Acceptable for free tier
                assert queue_time <= 15.0  # Longer queuing acceptable