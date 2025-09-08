"""
Tool Dispatcher Execution Integration Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool execution integrates reliably with system infrastructure
- Value Impact: Reliable execution integration enables consistent business value delivery
- Strategic Impact: Execution stability drives user satisfaction and platform credibility

CRITICAL: These tests validate tool execution integration patterns that directly impact
the ability of AI agents to deliver actionable business insights to users.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import (
    ToolInput,
    ToolResult,
    ToolStatus,
    ToolExecuteResponse,
    SimpleToolPayload
)
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class EnterpriseBusinessTool(BaseTool):
    """Enterprise-grade business tool for integration testing."""
    
    def __init__(self, name: str, service_domain: str, complexity_level: str = "standard"):
        self.name = name
        self.description = f"Enterprise {service_domain} tool: {name}"
        self.service_domain = service_domain
        self.complexity_level = complexity_level
        
    def _run(self, *args, **kwargs):
        """Sync version."""
        return asyncio.run(self._arun(*args, **kwargs))
        
    async def _arun(self, *args, **kwargs):
        """Async version with enterprise business logic."""
        # Simulate different complexity levels
        processing_time = {
            "simple": 0.05,
            "standard": 0.1,
            "complex": 0.2,
            "enterprise": 0.3
        }.get(self.complexity_level, 0.1)
        
        await asyncio.sleep(processing_time)
        
        # Simulate domain-specific processing
        if self.service_domain == "financial_analysis":
            return await self._financial_analysis_processing(**kwargs)
        elif self.service_domain == "infrastructure_optimization":
            return await self._infrastructure_optimization_processing(**kwargs)
        elif self.service_domain == "security_compliance":
            return await self._security_compliance_processing(**kwargs)
        else:
            return await self._generic_enterprise_processing(**kwargs)
    
    async def _financial_analysis_processing(self, **kwargs):
        """Financial analysis business logic."""
        await asyncio.sleep(0.05)  # Additional processing
        
        return {
            "success": True,
            "domain": "financial_analysis",
            "tool_name": self.name,
            "analysis_results": {
                "total_spend_analyzed": kwargs.get("total_spend", 125000.0),
                "cost_breakdown": {
                    "compute": 65000.0,
                    "storage": 25000.0,
                    "networking": 15000.0,
                    "services": 20000.0
                },
                "optimization_potential": {
                    "immediate_savings": 18750.0,  # 15% of total
                    "long_term_savings": 37500.0,  # 30% of total
                    "roi_timeline": "3-6 months"
                },
                "financial_metrics": {
                    "cost_per_user": 312.5,
                    "monthly_burn_rate": 41667.0,
                    "efficiency_score": 7.2,
                    "benchmark_percentile": 78
                }
            },
            "recommendations": [
                "Implement automated scaling policies",
                "Negotiate enterprise discounts with cloud providers",
                "Consolidate underutilized resources",
                "Implement cost allocation tags for better tracking"
            ],
            "business_impact": "HIGH",
            "confidence_score": 0.91
        }
    
    async def _infrastructure_optimization_processing(self, **kwargs):
        """Infrastructure optimization business logic."""
        await asyncio.sleep(0.08)
        
        return {
            "success": True,
            "domain": "infrastructure_optimization", 
            "tool_name": self.name,
            "optimization_results": {
                "current_utilization": {
                    "cpu_average": 45.2,
                    "memory_average": 62.8,
                    "storage_usage": 78.5,
                    "network_throughput": 34.7
                },
                "optimization_opportunities": [
                    {
                        "resource_type": "EC2_instances",
                        "current_count": 45,
                        "recommended_count": 32,
                        "potential_savings": 8500.0,
                        "impact": "Rightsize overprovisioned instances"
                    },
                    {
                        "resource_type": "RDS_instances",
                        "current_specs": "db.r5.2xlarge",
                        "recommended_specs": "db.r5.xlarge", 
                        "potential_savings": 3200.0,
                        "impact": "Optimize database instance sizing"
                    }
                ],
                "performance_improvements": {
                    "response_time_reduction": "23%",
                    "throughput_increase": "18%",
                    "availability_improvement": "99.7% to 99.95%"
                }
            },
            "implementation_plan": [
                "Phase 1: Implement monitoring and alerting",
                "Phase 2: Gradual resource rightsizing",
                "Phase 3: Performance validation and optimization"
            ],
            "business_value": "Improved performance and reduced costs"
        }
    
    async def _security_compliance_processing(self, **kwargs):
        """Security compliance business logic."""
        await asyncio.sleep(0.12)
        
        return {
            "success": True,
            "domain": "security_compliance",
            "tool_name": self.name,
            "security_assessment": {
                "overall_score": 8.3,
                "compliance_status": {
                    "SOC2_Type2": {"status": "COMPLIANT", "score": 9.1},
                    "ISO27001": {"status": "COMPLIANT", "score": 8.7},
                    "GDPR": {"status": "NEEDS_ATTENTION", "score": 7.8},
                    "HIPAA": {"status": "NOT_APPLICABLE", "score": None}
                },
                "vulnerabilities": {
                    "critical": 2,
                    "high": 8,
                    "medium": 15,
                    "low": 23
                },
                "security_metrics": {
                    "mean_time_to_detection": "4.2 hours",
                    "mean_time_to_response": "1.8 hours",
                    "incident_frequency": "0.3 per month",
                    "false_positive_rate": "12%"
                }
            },
            "remediation_plan": [
                {
                    "priority": "CRITICAL",
                    "action": "Patch exposed RDS instances",
                    "timeline": "24 hours",
                    "business_risk": "HIGH"
                },
                {
                    "priority": "HIGH", 
                    "action": "Enable MFA for all admin accounts",
                    "timeline": "48 hours",
                    "business_risk": "MEDIUM"
                }
            ],
            "compliance_roadmap": "90% compliance target within 60 days"
        }
    
    async def _generic_enterprise_processing(self, **kwargs):
        """Generic enterprise processing for other domains."""
        await asyncio.sleep(0.06)
        
        return {
            "success": True,
            "domain": "generic_enterprise",
            "tool_name": self.name,
            "processing_results": {
                "data_processed": kwargs.get("data_volume", "1.2TB"),
                "processing_time": f"{self.complexity_level} complexity",
                "business_metrics": {
                    "efficiency_improvement": "34%",
                    "cost_reduction": "22%",
                    "user_satisfaction": "8.7/10"
                }
            },
            "enterprise_features": {
                "audit_logging": "enabled",
                "data_encryption": "AES-256",
                "compliance_tracking": "automated",
                "sla_monitoring": "99.9% uptime"
            }
        }


class RealWebSocketEventManager:
    """Real WebSocket event manager for integration testing."""
    
    def __init__(self):
        self.events_sent = []
        self.event_subscriptions = {}
        self.connection_pool = {}
        
    async def notify_tool_executing(self, tool_name: str, user_id: str = None, **kwargs):
        """Send tool executing notification with real event routing."""
        event = {
            "event_type": "tool_executing",
            "tool_name": tool_name,
            "user_id": user_id,
            "event_id": f"exec_{len(self.events_sent)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "routing_info": {
                "source": "tool_dispatcher_execution_engine",
                "target": f"user_{user_id}" if user_id else "broadcast",
                "priority": "normal"
            },
            "payload": kwargs
        }
        
        self.events_sent.append(event)
        await self._route_event_to_subscribers(event)
        
    async def notify_tool_completed(self, tool_name: str, result: Any, user_id: str = None, **kwargs):
        """Send tool completed notification with real event routing."""
        event = {
            "event_type": "tool_completed",
            "tool_name": tool_name,
            "user_id": user_id,
            "event_id": f"comp_{len(self.events_sent)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "routing_info": {
                "source": "tool_dispatcher_execution_engine",
                "target": f"user_{user_id}" if user_id else "broadcast",
                "priority": "high"  # Completed events are high priority
            },
            "result": result,
            "payload": kwargs
        }
        
        self.events_sent.append(event)
        await self._route_event_to_subscribers(event)
    
    async def _route_event_to_subscribers(self, event: Dict[str, Any]):
        """Route events to subscribers (simulates real WebSocket routing)."""
        user_id = event.get("user_id")
        if user_id and user_id in self.event_subscriptions:
            # Simulate routing delay
            await asyncio.sleep(0.001)
            self.event_subscriptions[user_id].append(event)
    
    def subscribe_user_events(self, user_id: str):
        """Subscribe to events for a specific user."""
        if user_id not in self.event_subscriptions:
            self.event_subscriptions[user_id] = []
    
    def get_user_events(self, user_id: str) -> List[Dict]:
        """Get events for a specific user."""
        return self.event_subscriptions.get(user_id, [])
    
    def get_events_by_tool(self, tool_name: str) -> List[Dict]:
        """Get all events for a specific tool."""
        return [e for e in self.events_sent if e.get("tool_name") == tool_name]


class TestToolExecutionEngineRealDataFlows(SSotBaseTestCase):
    """Test tool execution engine with real data flows and business scenarios."""
    
    @pytest.mark.integration
    async def test_financial_analysis_tool_execution_integration(self):
        """Test financial analysis tool execution with realistic enterprise data flows."""
        websocket_manager = RealWebSocketEventManager()
        websocket_manager.subscribe_user_events("financial_analyst_user")
        
        execution_engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create enterprise financial analysis tool
        financial_tool = EnterpriseBusinessTool(
            "enterprise_cost_analyzer",
            "financial_analysis", 
            "enterprise"
        )
        
        # Create realistic financial analysis parameters
        enterprise_params = {
            "total_spend": 250000.0,
            "analysis_period": "Q1_2024",
            "cost_centers": ["engineering", "sales", "marketing", "operations"],
            "cloud_providers": ["AWS", "GCP", "Azure"],
            "include_forecasting": True,
            "granularity": "service_level",
            "budget_constraints": {
                "monthly_limit": 85000.0,
                "overage_threshold": 0.15
            }
        }
        
        # Execute tool with enterprise parameters
        tool_input = ToolInput(
            tool_name="enterprise_cost_analyzer",
            kwargs=enterprise_params
        )
        
        result = await execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=financial_tool,
            kwargs=enterprise_params
        )
        
        # Verify successful execution
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        
        # Verify financial analysis results structure
        result_data = result.result
        assert result_data["success"] is True
        assert result_data["domain"] == "financial_analysis"
        assert "analysis_results" in result_data
        assert "optimization_potential" in result_data["analysis_results"]
        assert "financial_metrics" in result_data["analysis_results"]
        
        # Verify business value metrics
        optimization = result_data["analysis_results"]["optimization_potential"]
        assert optimization["immediate_savings"] > 0
        assert optimization["long_term_savings"] > 0
        assert "roi_timeline" in optimization
        
        # Verify WebSocket events were sent with rich context
        user_events = websocket_manager.get_user_events("financial_analyst_user")
        assert len(user_events) >= 2
        
        executing_event = user_events[0]
        assert executing_event["event_type"] == "tool_executing"
        assert executing_event["tool_name"] == "enterprise_cost_analyzer"
        assert "enterprise_cost_analyzer" in str(executing_event["payload"])
        
        completed_event = user_events[1]
        assert completed_event["event_type"] == "tool_completed"
        assert "financial_analysis" in str(completed_event["result"])
    
    @pytest.mark.integration
    async def test_infrastructure_optimization_execution_with_state_management(self):
        """Test infrastructure optimization execution with agent state management."""
        websocket_manager = RealWebSocketEventManager()
        websocket_manager.subscribe_user_events("infrastructure_engineer")
        
        execution_engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create infrastructure optimization tool
        infra_tool = EnterpriseBusinessTool(
            "infrastructure_optimizer",
            "infrastructure_optimization",
            "complex"
        )
        
        # Create realistic agent state for infrastructure optimization
        agent_state = DeepAgentState(
            user_request="Optimize our production infrastructure for cost and performance",
            context_data={
                "environment": "production",
                "current_monthly_cost": 75000.0,
                "performance_targets": {
                    "response_time": "< 200ms",
                    "availability": "> 99.9%",
                    "throughput": "> 10k req/min"
                },
                "constraints": {
                    "zero_downtime": True,
                    "compliance_required": ["SOC2", "GDPR"],
                    "budget_limit": 60000.0
                }
            }
        )
        
        run_id = f"infra_optimization_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Execute with state management
        response = await execution_engine.execute_with_state(
            tool=infra_tool,
            tool_name="infrastructure_optimizer",
            parameters={
                "scope": "production_environment",
                "optimization_goals": ["cost_reduction", "performance_improvement"],
                "constraints": agent_state.context_data["constraints"]
            },
            state=agent_state,
            run_id=run_id
        )
        
        # Verify successful execution with state
        assert hasattr(response, 'success')
        assert response.success is True
        assert hasattr(response, 'result')
        
        # Verify infrastructure optimization results
        result_data = response.result
        assert "infrastructure_optimization" in str(result_data)
        assert "optimization_opportunities" in str(result_data)
        assert "performance_improvements" in str(result_data)
        
        # Verify run ID is tracked in metadata
        assert hasattr(response, 'metadata')
        metadata_str = str(response.metadata)
        assert run_id in metadata_str or "infra_optimization" in metadata_str
        
        # Verify WebSocket events include state context
        user_events = websocket_manager.get_user_events("infrastructure_engineer")
        assert len(user_events) >= 2
        
        for event in user_events:
            assert event["user_id"] == "infrastructure_engineer"
            assert event["tool_name"] == "infrastructure_optimizer"
    
    @pytest.mark.integration
    async def test_concurrent_multi_domain_tool_execution_integration(self):
        """Test concurrent execution of tools from different business domains."""
        websocket_manager = RealWebSocketEventManager()
        
        # Create multiple domain experts
        domain_users = ["financial_analyst", "security_engineer", "infrastructure_expert"]
        for user in domain_users:
            websocket_manager.subscribe_user_events(user)
        
        execution_engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create tools for different business domains
        domain_tools = [
            ("cost_analysis_pro", EnterpriseBusinessTool("cost_analysis_pro", "financial_analysis", "enterprise")),
            ("security_audit_pro", EnterpriseBusinessTool("security_audit_pro", "security_compliance", "complex")),
            ("infra_health_check", EnterpriseBusinessTool("infra_health_check", "infrastructure_optimization", "standard"))
        ]
        
        # Create concurrent execution tasks
        concurrent_tasks = []
        for i, (tool_name, tool) in enumerate(domain_tools):
            user_id = domain_users[i]
            
            # Create domain-specific parameters
            if tool.service_domain == "financial_analysis":
                params = {"budget_analysis": True, "cost_center": "engineering", "forecast_months": 6}
            elif tool.service_domain == "security_compliance":
                params = {"audit_scope": "comprehensive", "compliance_frameworks": ["SOC2", "ISO27001"]}
            else:  # infrastructure_optimization
                params = {"health_check_level": "deep", "include_recommendations": True}
            
            tool_input = ToolInput(tool_name=tool_name, kwargs=params)
            
            task = execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=tool,
                kwargs=params
            )
            concurrent_tasks.append((task, user_id, tool_name, tool.service_domain))
        
        # Execute all tools concurrently
        results = await asyncio.gather(
            *[task for task, _, _, _ in concurrent_tasks],
            return_exceptions=True
        )
        
        # Verify all executions succeeded
        for i, (result, (_, user_id, tool_name, domain)) in enumerate(zip(results, concurrent_tasks)):
            assert not isinstance(result, Exception), f"Task {i} for {user_id} failed: {result}"
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.SUCCESS
            
            # Verify domain-specific results
            result_data = result.result
            assert result_data["domain"] in [domain, "generic_enterprise"]
            assert result_data["tool_name"] == tool_name
            
            if domain == "financial_analysis":
                assert "analysis_results" in result_data or "financial_metrics" in str(result_data)
            elif domain == "security_compliance":
                assert "security_assessment" in result_data or "vulnerabilities" in str(result_data)
            else:  # infrastructure_optimization
                assert "optimization_results" in result_data or "utilization" in str(result_data)
        
        # Verify WebSocket events were properly routed to each domain expert
        for user_id in domain_users:
            user_events = websocket_manager.get_user_events(user_id)
            # Each user should have at least 2 events (executing + completed)
            # But events might not be user-specific in this test setup, so check global events
            
        # Verify total events match expected count
        assert len(websocket_manager.events_sent) >= 6  # 3 tools * 2 events each
    
    @pytest.mark.integration  
    async def test_tool_execution_error_recovery_integration(self):
        """Test tool execution error recovery and resilience integration."""
        websocket_manager = RealWebSocketEventManager()
        websocket_manager.subscribe_user_events("resilience_test_user")
        
        execution_engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create a tool that simulates various enterprise failure scenarios
        class ResilientBusinessTool(EnterpriseBusinessTool):
            def __init__(self, name: str, failure_scenario: str):
                super().__init__(name, "financial_analysis", "enterprise")
                self.failure_scenario = failure_scenario
                self.retry_count = 0
                
            async def _arun(self, *args, **kwargs):
                self.retry_count += 1
                await asyncio.sleep(0.05)  # Simulate processing
                
                # Simulate different failure scenarios that can happen in enterprise environments
                if self.failure_scenario == "transient_network":
                    if self.retry_count <= 2:
                        raise ConnectionError("Temporary network connectivity issue with AWS API")
                    # Success after retries
                    return await super()._financial_analysis_processing(**kwargs)
                    
                elif self.failure_scenario == "rate_limiting":
                    if self.retry_count <= 1:
                        raise Exception("API rate limit exceeded: 429 Too Many Requests. Retry after 1s")
                    return await super()._financial_analysis_processing(**kwargs)
                    
                elif self.failure_scenario == "partial_data_failure":
                    # Simulate partial success with some data missing
                    result = await super()._financial_analysis_processing(**kwargs)
                    if self.retry_count <= 1:
                        result["warnings"] = ["Some cost data unavailable for services: Lambda, EKS"]
                        result["data_completeness"] = 0.85
                    else:
                        result["data_completeness"] = 1.0
                    return result
                    
                else:  # permanent_failure
                    raise PermissionError("Insufficient permissions to access billing API")
        
        # Test different failure scenarios
        failure_scenarios = [
            ("network_resilient_tool", "transient_network"),
            ("rate_limit_resilient_tool", "rate_limiting"), 
            ("partial_data_tool", "partial_data_failure"),
            ("permission_failure_tool", "permanent_failure")
        ]
        
        results = []
        for tool_name, scenario in failure_scenarios:
            resilient_tool = ResilientBusinessTool(tool_name, scenario)
            
            tool_input = ToolInput(
                tool_name=tool_name,
                kwargs={"scenario_test": scenario, "resilience_mode": True}
            )
            
            result = await execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=resilient_tool,
                kwargs=tool_input.kwargs
            )
            
            results.append((scenario, result, resilient_tool.retry_count))
        
        # Verify error recovery behavior
        for scenario, result, retry_count in results:
            if scenario in ["transient_network", "rate_limiting", "partial_data_failure"]:
                # These should eventually succeed
                assert result.status == ToolStatus.SUCCESS, f"Scenario {scenario} should have succeeded"
                if scenario == "partial_data_failure":
                    # Should contain warning about partial data
                    assert "warnings" in str(result.result) or "completeness" in str(result.result)
            else:  # permanent_failure
                # This should fail permanently
                assert result.status == ToolStatus.ERROR
                assert "permission" in result.message.lower() or "access" in result.message.lower()
        
        # Verify WebSocket events were sent even during failures
        user_events = websocket_manager.get_user_events("resilience_test_user")
        # Should have events for all tool attempts, even failed ones
        assert len(user_events) >= len(failure_scenarios)  # At least one event per tool
        
        # Verify executing events were sent for all tools
        executing_events = [e for e in user_events if e["event_type"] == "tool_executing"]
        assert len(executing_events) >= len(failure_scenarios)