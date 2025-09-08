"""
Tool Dispatcher Integration Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete tool dispatch system integration delivers consistent results
- Value Impact: End-to-end integration enables reliable AI-powered business insights
- Strategic Impact: System integration stability ensures consistent user experience and business value

CRITICAL: These tests validate complete integration across all dispatcher components,
ensuring AI agents can reliably coordinate tool execution to deliver business value.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from netra_backend.app.agents.tool_dispatcher import (
    UnifiedToolDispatcherFactory,
    create_request_scoped_tool_dispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.registry.universal_registry import ToolRegistry
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase


class BusinessWorkflowTool(BaseTool):
    """Business workflow tool that simulates multi-step business processes."""
    
    def __init__(self, name: str, workflow_type: str, dependencies: List[str] = None):
        self.name = name
        self.description = f"Business workflow tool: {name} ({workflow_type})"
        self.workflow_type = workflow_type
        self.dependencies = dependencies or []
        self.execution_history = []
        
    def _run(self, *args, **kwargs):
        """Sync version."""
        return asyncio.run(self._arun(*args, **kwargs))
        
    async def _arun(self, *args, **kwargs):
        """Async version with business workflow simulation."""
        # Record execution
        self.execution_history.append({
            "timestamp": datetime.now(timezone.utc),
            "parameters": kwargs
        })
        
        # Simulate workflow processing based on type
        if self.workflow_type == "data_collection":
            return await self._data_collection_workflow(**kwargs)
        elif self.workflow_type == "analysis":
            return await self._analysis_workflow(**kwargs)
        elif self.workflow_type == "optimization":
            return await self._optimization_workflow(**kwargs)
        elif self.workflow_type == "reporting":
            return await self._reporting_workflow(**kwargs)
        else:
            return await self._generic_workflow(**kwargs)
    
    async def _data_collection_workflow(self, **kwargs):
        """Data collection workflow simulation."""
        await asyncio.sleep(0.08)  # Simulate data gathering
        
        return {
            "success": True,
            "workflow_type": "data_collection",
            "tool_name": self.name,
            "data_collected": {
                "sources": ["AWS CloudWatch", "Application Logs", "Database Metrics"],
                "time_range": kwargs.get("time_range", "last_30_days"),
                "data_points": 15420,
                "collection_status": "complete"
            },
            "quality_metrics": {
                "completeness": 0.94,
                "accuracy": 0.97,
                "freshness": "< 5 minutes"
            },
            "next_steps": ["analysis", "optimization"]
        }
    
    async def _analysis_workflow(self, **kwargs):
        """Analysis workflow simulation."""
        await asyncio.sleep(0.12)  # Simulate analysis processing
        
        return {
            "success": True,
            "workflow_type": "analysis",
            "tool_name": self.name,
            "analysis_results": {
                "patterns_identified": 23,
                "anomalies_detected": 5,
                "trends": [
                    {"metric": "response_time", "trend": "increasing", "impact": "medium"},
                    {"metric": "error_rate", "trend": "stable", "impact": "low"},
                    {"metric": "cost_per_request", "trend": "decreasing", "impact": "positive"}
                ],
                "insights": [
                    "Peak usage hours: 2-4 PM EST",
                    "Database queries are the primary bottleneck", 
                    "Caching effectiveness has improved 34%"
                ]
            },
            "confidence_score": 0.87,
            "dependencies_met": self._check_dependencies_met(kwargs),
            "next_steps": ["optimization", "reporting"]
        }
    
    async def _optimization_workflow(self, **kwargs):
        """Optimization workflow simulation."""
        await asyncio.sleep(0.15)  # Simulate optimization processing
        
        return {
            "success": True,
            "workflow_type": "optimization",
            "tool_name": self.name,
            "optimization_results": {
                "recommendations": [
                    {
                        "category": "performance",
                        "action": "Implement query caching for top 10 queries",
                        "impact": "25% response time reduction",
                        "effort": "2 dev days"
                    },
                    {
                        "category": "cost",
                        "action": "Right-size EC2 instances based on usage",
                        "impact": "$3,200/month savings",
                        "effort": "4 hours maintenance window"
                    }
                ],
                "priority_matrix": {
                    "high_impact_low_effort": 3,
                    "high_impact_high_effort": 2,
                    "low_impact_low_effort": 5,
                    "low_impact_high_effort": 1
                }
            },
            "business_value": "Improved performance and reduced operational costs",
            "implementation_timeline": "2-3 weeks",
            "dependencies_met": self._check_dependencies_met(kwargs)
        }
    
    async def _reporting_workflow(self, **kwargs):
        """Reporting workflow simulation."""
        await asyncio.sleep(0.06)  # Simulate report generation
        
        return {
            "success": True,
            "workflow_type": "reporting", 
            "tool_name": self.name,
            "report_generated": {
                "report_type": kwargs.get("report_type", "executive_summary"),
                "sections": ["Executive Summary", "Key Metrics", "Recommendations", "Next Steps"],
                "format": "interactive_dashboard",
                "stakeholders": ["Engineering Team", "Product Management", "Executive Leadership"],
                "delivery_status": "ready_for_distribution"
            },
            "metrics_summary": {
                "cost_optimization_potential": "$8,450/month",
                "performance_improvement": "32% faster response times",
                "reliability_score": "99.7% uptime achieved"
            },
            "dependencies_met": self._check_dependencies_met(kwargs)
        }
    
    async def _generic_workflow(self, **kwargs):
        """Generic workflow for other business processes.""" 
        await asyncio.sleep(0.07)
        
        return {
            "success": True,
            "workflow_type": "generic",
            "tool_name": self.name,
            "workflow_results": {
                "process_completed": True,
                "business_outcome": "Workflow executed successfully",
                "metrics": {"efficiency": "high", "accuracy": "96%"}
            }
        }
    
    def _check_dependencies_met(self, kwargs: Dict[str, Any]) -> bool:
        """Check if workflow dependencies are satisfied."""
        if not self.dependencies:
            return True
            
        # Simulate dependency checking
        completed_workflows = kwargs.get("completed_workflows", [])
        return all(dep in completed_workflows for dep in self.dependencies)


class ComprehensiveUserContext:
    """Comprehensive user context for integration testing."""
    
    def __init__(self, user_id: str, user_type: str = "enterprise"):
        self.user_id = user_id
        self.user_type = user_type
        self.request_id = f"req_{int(datetime.now(timezone.utc).timestamp())}_{user_id}"
        self.session_id = f"session_{user_id}_{user_type}"
        self.created_at = datetime.now(timezone.utc)
        
        # Set user-type specific attributes
        if user_type == "enterprise":
            self.permissions = [
                "read", "write", "execute_tools", "view_analytics", 
                "manage_resources", "access_billing", "admin_functions"
            ]
            self.features_enabled = [
                "advanced_analytics", "cost_optimization", "security_scanning",
                "compliance_monitoring", "custom_workflows", "priority_support"
            ]
            self.limits = {"api_calls_per_hour": 10000, "concurrent_executions": 50}
        elif user_type == "professional":
            self.permissions = ["read", "write", "execute_tools", "view_analytics"]
            self.features_enabled = ["basic_analytics", "cost_optimization", "standard_workflows"] 
            self.limits = {"api_calls_per_hour": 1000, "concurrent_executions": 10}
        else:  # free tier
            self.permissions = ["read", "execute_tools"]
            self.features_enabled = ["basic_workflows"]
            self.limits = {"api_calls_per_hour": 100, "concurrent_executions": 2}
            
        self.metadata = {
            "user_type": user_type,
            "onboarding_completed": True,
            "last_active": datetime.now(timezone.utc).isoformat(),
            "feature_flags": {
                "beta_features": user_type == "enterprise",
                "experimental_tools": user_type in ["enterprise", "professional"]
            }
        }
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions
    
    def has_feature_access(self, feature: str) -> bool:
        """Check if user has access to specific feature."""
        return feature in self.features_enabled


class EnterpriseWebSocketManager:
    """Enterprise-grade WebSocket manager for integration testing."""
    
    def __init__(self):
        self.events_sent = []
        self.user_connections = {}
        self.event_history = {}
        self.connection_status = {}
        
    async def notify_tool_executing(self, tool_name: str, user_id: str = None, **kwargs):
        """Enhanced tool executing notification with enterprise features."""
        event = {
            "event_type": "tool_executing",
            "event_id": f"exec_{len(self.events_sent)}",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "routing_metadata": {
                "source": "unified_tool_dispatcher",
                "priority": "normal",
                "requires_acknowledgment": kwargs.get("critical", False)
            },
            "business_context": {
                "workflow_step": kwargs.get("workflow_step"),
                "business_impact": kwargs.get("business_impact", "medium"),
                "estimated_duration": kwargs.get("estimated_duration", "< 30s")
            },
            "payload": kwargs
        }
        
        self.events_sent.append(event)
        await self._route_to_user_connection(event, user_id)
        
    async def notify_tool_completed(self, tool_name: str, result: Any, user_id: str = None, **kwargs):
        """Enhanced tool completed notification with enterprise features."""
        event = {
            "event_type": "tool_completed",
            "event_id": f"comp_{len(self.events_sent)}",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "routing_metadata": {
                "source": "unified_tool_dispatcher",
                "priority": "high",  # Completed events are high priority
                "delivery_confirmation": True
            },
            "business_context": {
                "workflow_step": kwargs.get("workflow_step"),
                "success": self._extract_success_status(result),
                "business_value_delivered": self._extract_business_value(result)
            },
            "result": result,
            "payload": kwargs
        }
        
        self.events_sent.append(event)
        await self._route_to_user_connection(event, user_id)
    
    async def _route_to_user_connection(self, event: Dict, user_id: str):
        """Route event to user's WebSocket connection."""
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(event)
            
            # Track event history
            if user_id not in self.event_history:
                self.event_history[user_id] = []
            self.event_history[user_id].append(event)
    
    def _extract_success_status(self, result: Any) -> bool:
        """Extract success status from tool result."""
        if hasattr(result, 'success'):
            return result.success
        if isinstance(result, dict):
            return result.get('success', True)
        return True
    
    def _extract_business_value(self, result: Any) -> str:
        """Extract business value description from result."""
        if isinstance(result, dict):
            if 'business_value' in result:
                return result['business_value']
            elif 'optimization_results' in result:
                return "Optimization insights delivered"
            elif 'analysis_results' in result:
                return "Business analysis completed"
        return "Business process completed"
    
    def get_user_events(self, user_id: str) -> List[Dict]:
        """Get all events for a specific user."""
        return self.user_connections.get(user_id, [])
    
    def get_workflow_events(self, user_id: str, workflow_type: str) -> List[Dict]:
        """Get events for specific workflow type."""
        user_events = self.get_user_events(user_id)
        return [e for e in user_events if workflow_type in str(e.get("payload", {}))]


class TestCompleteToolDispatcherSystemIntegration(SSotBaseTestCase):
    """Test complete tool dispatcher system integration end-to-end."""
    
    @pytest.mark.integration
    async def test_multi_stage_business_workflow_integration(self):
        """Test multi-stage business workflow integration across all dispatcher components."""
        user_context = ComprehensiveUserContext("workflow_user", "enterprise")
        websocket_manager = EnterpriseWebSocketManager()
        
        # Create business workflow tools with dependencies
        workflow_tools = [
            BusinessWorkflowTool("data_collector", "data_collection"),
            BusinessWorkflowTool("business_analyzer", "analysis", ["data_collection"]),
            BusinessWorkflowTool("cost_optimizer", "optimization", ["analysis"]),
            BusinessWorkflowTool("executive_reporter", "reporting", ["optimization"])
        ]
        
        # Create unified dispatcher with all workflow tools
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=workflow_tools
        )
        
        # Execute complete business workflow
        workflow_state = DeepAgentState(
            user_request="Perform complete cost optimization analysis and generate executive report"
        )
        
        completed_workflows = []
        workflow_results = {}
        
        # Stage 1: Data Collection
        data_result = await dispatcher.dispatch_tool(
            tool_name="data_collector",
            parameters={
                "time_range": "last_quarter",
                "include_all_services": True,
                "workflow_step": "data_collection"
            },
            state=workflow_state,
            run_id="workflow_stage_1"
        )
        
        assert data_result.success is True
        assert "data_collection" in str(data_result.result)
        completed_workflows.append("data_collection")
        workflow_results["data_collection"] = data_result.result
        
        # Stage 2: Business Analysis (depends on data collection)
        analysis_result = await dispatcher.dispatch_tool(
            tool_name="business_analyzer",
            parameters={
                "data_source": "collected_data",
                "analysis_depth": "comprehensive",
                "completed_workflows": completed_workflows,
                "workflow_step": "analysis"
            },
            state=workflow_state,
            run_id="workflow_stage_2"
        )
        
        assert analysis_result.success is True
        assert "analysis" in str(analysis_result.result)
        completed_workflows.append("analysis")
        workflow_results["analysis"] = analysis_result.result
        
        # Stage 3: Cost Optimization (depends on analysis)
        optimization_result = await dispatcher.dispatch_tool(
            tool_name="cost_optimizer",
            parameters={
                "analysis_input": "business_analysis_results",
                "optimization_goals": ["cost_reduction", "performance_improvement"],
                "completed_workflows": completed_workflows,
                "workflow_step": "optimization"
            },
            state=workflow_state,
            run_id="workflow_stage_3"
        )
        
        assert optimization_result.success is True
        assert "optimization" in str(optimization_result.result)
        completed_workflows.append("optimization")
        workflow_results["optimization"] = optimization_result.result
        
        # Stage 4: Executive Reporting (depends on optimization)
        reporting_result = await dispatcher.dispatch_tool(
            tool_name="executive_reporter",
            parameters={
                "report_type": "executive_summary",
                "include_recommendations": True,
                "completed_workflows": completed_workflows,
                "workflow_step": "reporting"
            },
            state=workflow_state,
            run_id="workflow_stage_4"
        )
        
        assert reporting_result.success is True
        assert "reporting" in str(reporting_result.result)
        
        # Verify complete workflow integration
        user_events = websocket_manager.get_user_events(user_context.user_id)
        assert len(user_events) >= 8  # 4 stages * 2 events (executing + completed) each
        
        # Verify workflow progression in events
        workflow_steps = ["data_collection", "analysis", "optimization", "reporting"]
        for step in workflow_steps:
            step_events = websocket_manager.get_workflow_events(user_context.user_id, step)
            assert len(step_events) >= 2  # executing + completed for each step
        
        # Verify business value delivery
        assert "business_value" in str(optimization_result.result) or "recommendations" in str(optimization_result.result)
        assert "report_generated" in str(reporting_result.result)
    
    @pytest.mark.integration
    async def test_cross_component_error_handling_integration(self):
        """Test error handling integration across all dispatcher components."""
        user_context = ComprehensiveUserContext("error_test_user", "professional")
        websocket_manager = EnterpriseWebSocketManager()
        
        # Create tools with various failure modes that test different components
        class ComponentFailureTool(BusinessWorkflowTool):
            def __init__(self, name: str, failure_component: str):
                super().__init__(name, "analysis")
                self.failure_component = failure_component
                
            async def _arun(self, *args, **kwargs):
                await asyncio.sleep(0.05)
                
                if self.failure_component == "registry":
                    # Simulate registry-level failure
                    raise AttributeError("Tool not properly registered in registry")
                elif self.failure_component == "execution": 
                    # Simulate execution-level failure
                    raise RuntimeError("Tool execution engine encountered fatal error")
                elif self.failure_component == "websocket":
                    # Simulate WebSocket-level failure (tool succeeds but event fails)
                    result = await super()._analysis_workflow(**kwargs)
                    # This would normally cause WebSocket notification to fail
                    kwargs["simulate_websocket_failure"] = True
                    return result
                elif self.failure_component == "permission":
                    # Simulate permission-level failure
                    raise PermissionError("User lacks required permissions for this tool")
                else:
                    return await super()._analysis_workflow(**kwargs)
        
        failure_tools = [
            ComponentFailureTool("registry_failure_tool", "registry"),
            ComponentFailureTool("execution_failure_tool", "execution"),
            ComponentFailureTool("websocket_failure_tool", "websocket"),
            ComponentFailureTool("permission_failure_tool", "permission")
        ]
        
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=failure_tools
        )
        
        # Test error handling across components
        error_results = []
        for tool in failure_tools:
            try:
                result = await dispatcher.dispatch_tool(
                    tool_name=tool.name,
                    parameters={"test_component_failure": tool.failure_component},
                    state=DeepAgentState(user_request="Test error handling"),
                    run_id=f"error_test_{tool.failure_component}"
                )
                error_results.append((tool.failure_component, result, None))
            except Exception as e:
                error_results.append((tool.failure_component, None, e))
        
        # Verify error handling behavior
        for component, result, exception in error_results:
            if component == "websocket":
                # WebSocket failures shouldn't prevent tool success
                assert result is not None
                assert result.success is True
                # But the event routing issue should be detectable
            elif component == "permission":
                # Permission failures should be handled gracefully
                if result:
                    assert result.success is False
                    assert "permission" in str(result.error).lower()
                else:
                    assert isinstance(exception, PermissionError)
            else:  # registry or execution failures
                # These may cause exceptions or error results
                if result:
                    assert result.success is False
                else:
                    assert exception is not None
        
        # Verify WebSocket events were sent for tools that could execute
        user_events = websocket_manager.get_user_events(user_context.user_id)
        # Should have events for at least some tools, even if others failed
        assert len(user_events) >= 2  # At least one tool should have executed
    
    @pytest.mark.integration
    async def test_enterprise_multi_user_concurrent_workflow_integration(self):
        """Test enterprise-grade multi-user concurrent workflow integration."""
        # Create multiple enterprise users with different roles
        user_contexts = [
            ComprehensiveUserContext("cfo_user", "enterprise"),
            ComprehensiveUserContext("cto_user", "enterprise"), 
            ComprehensiveUserContext("devops_lead", "professional")
        ]
        
        websocket_manager = EnterpriseWebSocketManager()
        
        # Create role-specific workflow tools
        role_specific_workflows = {
            "cfo_user": [
                BusinessWorkflowTool("financial_analytics", "analysis"),
                BusinessWorkflowTool("cost_reporting", "reporting")
            ],
            "cto_user": [
                BusinessWorkflowTool("tech_performance_analysis", "analysis"),
                BusinessWorkflowTool("architecture_optimization", "optimization")
            ],
            "devops_lead": [
                BusinessWorkflowTool("infrastructure_monitoring", "data_collection"),
                BusinessWorkflowTool("deployment_optimization", "optimization")
            ]
        }
        
        # Create dispatchers for each user
        user_dispatchers = {}
        for user_context in user_contexts:
            tools = role_specific_workflows[user_context.user_id]
            dispatcher = await create_request_scoped_tool_dispatcher(
                user_context=user_context,
                websocket_manager=websocket_manager,
                tools=tools
            )
            user_dispatchers[user_context.user_id] = (dispatcher, user_context, tools)
        
        # Execute concurrent workflows for all users
        concurrent_tasks = []
        for user_id, (dispatcher, user_context, tools) in user_dispatchers.items():
            for tool in tools:
                # Create user-specific parameters
                if user_id == "cfo_user":
                    params = {"financial_scope": "enterprise", "include_forecasting": True}
                elif user_id == "cto_user":
                    params = {"tech_scope": "platform", "include_architecture_review": True}
                else:  # devops_lead
                    params = {"infrastructure_scope": "production", "monitoring_depth": "comprehensive"}
                
                task = dispatcher.dispatch_tool(
                    tool_name=tool.name,
                    parameters={
                        **params,
                        "user_role": user_id.split("_")[0],  # cfo, cto, devops
                        "concurrent_execution": True
                    },
                    state=DeepAgentState(user_request=f"Execute {tool.workflow_type} for {user_id}"),
                    run_id=f"{user_id}_{tool.name}_{int(datetime.now(timezone.utc).timestamp())}"
                )
                concurrent_tasks.append((task, user_id, tool.name, tool.workflow_type))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[task for task, _, _, _ in concurrent_tasks],
            return_exceptions=True
        )
        
        # Verify all concurrent executions succeeded
        for i, (result, (_, user_id, tool_name, workflow_type)) in enumerate(zip(results, concurrent_tasks)):
            assert not isinstance(result, Exception), f"Task {i} for {user_id}.{tool_name} failed: {result}"
            assert hasattr(result, 'success')
            assert result.success is True
            
            # Verify role-specific results
            result_str = str(result.result)
            assert workflow_type in result_str
            
            if "cfo" in user_id:
                assert "financial" in result_str or "cost" in result_str
            elif "cto" in user_id:
                assert "tech" in result_str or "performance" in result_str or "architecture" in result_str
            else:  # devops
                assert "infrastructure" in result_str or "monitoring" in result_str or "deployment" in result_str
        
        # Verify user isolation in WebSocket events
        for user_id in user_dispatchers.keys():
            user_events = websocket_manager.get_user_events(user_id)
            assert len(user_events) >= 4  # 2 tools * 2 events each
            
            # Verify all events belong to this user
            for event in user_events:
                assert event["user_id"] == user_id
                # Verify role-specific context in events
                if "cfo" in user_id:
                    assert "financial" in str(event["payload"]) or "cost" in str(event["payload"])
                elif "cto" in user_id:
                    assert "tech" in str(event["payload"]) or "architecture" in str(event["payload"])
                else:  # devops
                    assert "infrastructure" in str(event["payload"]) or "monitoring" in str(event["payload"])
        
        # Verify enterprise features in events
        all_events = websocket_manager.events_sent
        assert len(all_events) >= 12  # 3 users * 2 tools * 2 events each
        
        # Check enterprise event features
        for event in all_events:
            assert "routing_metadata" in event
            assert "business_context" in event
            assert event["routing_metadata"]["source"] == "unified_tool_dispatcher"