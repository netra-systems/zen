"""
Tool Dispatcher Core Integration Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure tool dispatcher integrates properly with real system components
- Value Impact: Real component integration enables reliable AI tool execution for users
- Strategic Impact: Integration stability directly impacts user trust and platform reliability

CRITICAL: These tests validate tool dispatcher integration with real components
without requiring full service infrastructure, ensuring AI agents can reliably
execute tools to deliver business insights.
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
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.registry.universal_registry import ToolRegistry
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class RealBusinessTool(BaseTool):
    """Real business tool that simulates actual business logic patterns."""
    
    def __init__(self, name: str, business_domain: str = "cost_optimization"):
        self.name = name
        self.description = f"Real {business_domain} tool: {name}"
        self.business_domain = business_domain
        
    def _run(self, *args, **kwargs):
        """Sync version."""
        return self._execute(*args, **kwargs)
        
    async def _arun(self, *args, **kwargs):
        """Async version with realistic business processing."""
        # Simulate realistic business processing time
        await asyncio.sleep(0.1)
        
        # Simulate real business logic patterns
        if self.business_domain == "cost_optimization":
            return await self._cost_optimization_logic(**kwargs)
        elif self.business_domain == "security_analysis":
            return await self._security_analysis_logic(**kwargs)
        else:
            return await self._generic_business_logic(**kwargs)
            
    async def _cost_optimization_logic(self, **kwargs):
        """Realistic cost optimization business logic."""
        # Simulate data processing delay
        await asyncio.sleep(0.05)
        
        return {
            "success": True,
            "analysis_type": "cost_optimization",
            "current_monthly_spend": kwargs.get("current_spend", 45000.0),
            "optimization_opportunities": [
                {
                    "service": "EC2",
                    "current_cost": 15000.0,
                    "potential_savings": 4500.0,
                    "confidence": 0.89,
                    "actions": ["Rightsize instances", "Use reserved instances"]
                },
                {
                    "service": "S3", 
                    "current_cost": 2000.0,
                    "potential_savings": 600.0,
                    "confidence": 0.94,
                    "actions": ["Implement lifecycle policies", "Use IA storage class"]
                }
            ],
            "total_potential_savings": 5100.0,
            "roi_estimate": 3.2,
            "implementation_timeline": "2-4 weeks",
            "business_impact": "HIGH"
        }
    
    async def _security_analysis_logic(self, **kwargs):
        """Realistic security analysis business logic."""
        await asyncio.sleep(0.08)
        
        return {
            "success": True,
            "analysis_type": "security_analysis",
            "security_score": 7.5,
            "vulnerabilities_found": 12,
            "critical_issues": [
                {
                    "type": "exposed_credentials",
                    "severity": "HIGH",
                    "affected_resources": ["RDS instance prod-db-1"],
                    "remediation": "Rotate credentials and enable secrets manager"
                },
                {
                    "type": "open_security_groups", 
                    "severity": "MEDIUM",
                    "affected_resources": ["sg-12345", "sg-67890"],
                    "remediation": "Restrict ingress rules to specific IP ranges"
                }
            ],
            "compliance_status": {
                "SOC2": "COMPLIANT",
                "GDPR": "NEEDS_ATTENTION", 
                "HIPAA": "NOT_APPLICABLE"
            },
            "business_risk": "MEDIUM"
        }
    
    async def _generic_business_logic(self, **kwargs):
        """Generic business logic for other domains."""
        await asyncio.sleep(0.06)
        
        return {
            "success": True,
            "analysis_type": "generic_business",
            "domain": self.business_domain,
            "processed_parameters": kwargs,
            "business_metrics": {
                "efficiency_score": 8.2,
                "cost_impact": "POSITIVE",
                "time_savings": "40%"
            },
            "recommendations": [
                "Implement automated monitoring",
                "Establish regular review cycles",
                "Create actionable dashboards"
            ]
        }
    
    def _execute(self, *args, **kwargs):
        """Fallback sync execution."""
        return {"success": True, "sync_execution": True, "tool_name": self.name}


class RealUserExecutionContext:
    """Real user execution context that matches production patterns."""
    
    def __init__(self, user_id: str, environment: str = "integration"):
        self.user_id = user_id
        self.request_id = f"req-{int(datetime.now(timezone.utc).timestamp())}-{user_id}"
        self.session_id = f"session-{user_id}-{environment}"
        self.environment = environment
        self.created_at = datetime.now(timezone.utc)
        self.metadata = {
            "test_type": "integration",
            "environment": environment,
            "user_tier": "enterprise",
            "features_enabled": ["cost_optimization", "security_analysis", "compliance_monitoring"]
        }
        self.permissions = ["read", "write", "execute_tools", "view_analytics", "manage_resources"]
        
    def has_permission(self, permission: str) -> bool:
        """Check user permissions."""
        return permission in self.permissions
    
    def get_context_data(self) -> Dict[str, Any]:
        """Get full context data."""
        return {
            "user_id": self.user_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "environment": self.environment,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "permissions": self.permissions
        }


class RealWebSocketNotifier:
    """Real WebSocket notifier that follows production patterns."""
    
    def __init__(self):
        self.events_sent = []
        self.user_sessions = {}
        self.connection_active = True
        
    async def notify_tool_executing(self, tool_name: str, user_id: str = None, **kwargs):
        """Send tool executing notification with real event structure."""
        if not self.connection_active:
            return
            
        event = {
            "type": "tool_executing",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": f"exec-{len(self.events_sent)}",
            "metadata": kwargs
        }
        
        self.events_sent.append(event)
        
        # Simulate real WebSocket routing
        if user_id and user_id in self.user_sessions:
            self.user_sessions[user_id].append(event)
            
    async def notify_tool_completed(self, tool_name: str, result: Any, user_id: str = None, **kwargs):
        """Send tool completed notification with real event structure.""" 
        if not self.connection_active:
            return
            
        event = {
            "type": "tool_completed",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": f"comp-{len(self.events_sent)}",
            "result": result,
            "metadata": kwargs
        }
        
        self.events_sent.append(event)
        
        if user_id and user_id in self.user_sessions:
            self.user_sessions[user_id].append(event)
    
    def create_user_session(self, user_id: str):
        """Create user session for event routing."""
        self.user_sessions[user_id] = []
        
    def get_user_events(self, user_id: str) -> List[Dict]:
        """Get events for specific user."""
        return self.user_sessions.get(user_id, [])


class TestToolDispatcherRealComponentIntegration(SSotBaseTestCase):
    """Test tool dispatcher integration with real system components."""
    
    @pytest.mark.integration
    async def test_integration_with_real_tool_registry(self):
        """Test dispatcher integration with real ToolRegistry component."""
        user_context = RealUserExecutionContext("registry-integration-user")
        websocket_notifier = RealWebSocketNotifier()
        websocket_notifier.create_user_session(user_context.user_id)
        
        # Create real business tools
        cost_tool = RealBusinessTool("aws_cost_analyzer", "cost_optimization")
        security_tool = RealBusinessTool("security_scanner", "security_analysis")
        
        # Create dispatcher with real registry integration
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_notifier,
            tools=[cost_tool, security_tool]
        )
        
        # Verify real registry integration
        assert hasattr(dispatcher, 'registry')
        assert isinstance(dispatcher.registry, ToolRegistry)
        
        # Test tool registration in real registry
        assert dispatcher.has_tool("aws_cost_analyzer") is True
        assert dispatcher.has_tool("security_scanner") is True
        
        # Execute tool through real registry
        result = await dispatcher.dispatch(
            "aws_cost_analyzer",
            current_spend=50000.0,
            account_id="123456789"
        )
        
        # Verify real registry provided the tool correctly
        assert result.status.name == "SUCCESS"  # Using real ToolStatus enum
        assert "cost_optimization" in str(result.result)
        assert "potential_savings" in str(result.result)
        
        # Verify WebSocket integration worked
        user_events = websocket_notifier.get_user_events(user_context.user_id)
        assert len(user_events) >= 2  # executing + completed
        
        executing_event = next(e for e in user_events if e["type"] == "tool_executing")
        assert executing_event["tool_name"] == "aws_cost_analyzer"
        assert executing_event["user_id"] == user_context.user_id
    
    @pytest.mark.integration
    async def test_integration_with_real_execution_engine(self):
        """Test dispatcher integration with real UnifiedToolExecutionEngine."""
        user_context = RealUserExecutionContext("execution-integration-user")
        websocket_notifier = RealWebSocketNotifier()
        websocket_notifier.create_user_session(user_context.user_id)
        
        # Create realistic business scenario tools
        tools = [
            RealBusinessTool("compliance_checker", "security_analysis"),
            RealBusinessTool("resource_optimizer", "cost_optimization"),
            RealBusinessTool("performance_analyzer", "performance_monitoring")
        ]
        
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_notifier,
            tools=tools
        )
        
        # Verify real execution engine integration
        assert hasattr(dispatcher, 'executor')
        assert isinstance(dispatcher.executor, UnifiedToolExecutionEngine)
        
        # Test complex business scenario execution
        business_state = DeepAgentState(
            user_request="Perform comprehensive infrastructure analysis for cost and security optimization"
        )
        run_id = f"business-analysis-{int(datetime.now(timezone.utc).timestamp())}"
        
        # Execute multiple tools through real execution engine
        results = []
        for tool_name in ["compliance_checker", "resource_optimizer", "performance_analyzer"]:
            response = await dispatcher.dispatch_tool(
                tool_name=tool_name,
                parameters={
                    "environment": "production",
                    "scope": "comprehensive",
                    "priority": "high"
                },
                state=business_state,
                run_id=run_id
            )
            results.append(response)
        
        # Verify all executions succeeded through real engine
        for i, response in enumerate(results):
            assert hasattr(response, 'success')
            assert response.success is True
            assert hasattr(response, 'result')
            assert response.result is not None
            
            # Verify business value in results
            result_str = str(response.result)
            assert "success" in result_str
            assert "analysis_type" in result_str
        
        # Verify real execution engine sent proper WebSocket events
        user_events = websocket_notifier.get_user_events(user_context.user_id)
        assert len(user_events) >= 6  # 3 tools * 2 events each
        
        # Verify event ordering and content
        executing_events = [e for e in user_events if e["type"] == "tool_executing"]
        completed_events = [e for e in user_events if e["type"] == "tool_completed"]
        assert len(executing_events) == 3
        assert len(completed_events) == 3
    
    @pytest.mark.integration
    async def test_real_websocket_event_integration_flow(self):
        """Test complete WebSocket event integration flow with realistic business scenarios."""
        user_context = RealUserExecutionContext("websocket-integration-user")
        websocket_notifier = RealWebSocketNotifier()
        websocket_notifier.create_user_session(user_context.user_id)
        
        # Create business tools that generate rich events
        enterprise_tool = RealBusinessTool("enterprise_cost_analyzer", "cost_optimization")
        
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_notifier,
            tools=[enterprise_tool]
        )
        
        # Execute tool with enterprise-level parameters
        enterprise_params = {
            "accounts": ["prod-123", "staging-456", "dev-789"],
            "services": ["EC2", "RDS", "S3", "Lambda", "EKS"],
            "time_range": {"start": "2024-01-01", "end": "2024-02-01"},
            "analysis_depth": "comprehensive",
            "include_recommendations": True,
            "cost_allocation_tags": {"Environment": "prod", "Team": "platform"},
            "budget_constraints": {"monthly_limit": 75000.0}
        }
        
        result = await dispatcher.dispatch(
            "enterprise_cost_analyzer",
            **enterprise_params
        )
        
        # Verify successful execution
        assert result.status.name == "SUCCESS"
        
        # Verify rich business results
        result_str = str(result.result)
        assert "optimization_opportunities" in result_str
        assert "potential_savings" in result_str
        assert "business_impact" in result_str
        
        # Verify WebSocket events contain rich business context
        user_events = websocket_notifier.get_user_events(user_context.user_id)
        assert len(user_events) >= 2
        
        executing_event = user_events[0]
        assert executing_event["type"] == "tool_executing"
        assert executing_event["tool_name"] == "enterprise_cost_analyzer"
        assert "metadata" in executing_event
        
        completed_event = user_events[1]
        assert completed_event["type"] == "tool_completed" 
        assert "result" in completed_event
        assert "optimization_opportunities" in str(completed_event["result"])
    
    @pytest.mark.integration
    async def test_multi_user_concurrent_real_component_integration(self):
        """Test concurrent multi-user execution with real components."""
        # Create multiple realistic user contexts
        user_contexts = [
            RealUserExecutionContext(f"enterprise-user-{i}")
            for i in range(1, 4)
        ]
        
        websocket_notifier = RealWebSocketNotifier()
        
        # Create user sessions and dispatchers
        dispatchers = []
        for user_context in user_contexts:
            websocket_notifier.create_user_session(user_context.user_id)
            
            # Each user gets different business tools based on their needs
            user_tools = [
                RealBusinessTool(f"cost_tool_{user_context.user_id}", "cost_optimization"),
                RealBusinessTool(f"security_tool_{user_context.user_id}", "security_analysis")
            ]
            
            dispatcher = await create_request_scoped_tool_dispatcher(
                user_context=user_context,
                websocket_manager=websocket_notifier,
                tools=user_tools
            )
            dispatchers.append((dispatcher, user_context))
        
        # Execute tools concurrently for all users
        concurrent_tasks = []
        for dispatcher, user_context in dispatchers:
            # Cost analysis task
            cost_task = dispatcher.dispatch(
                f"cost_tool_{user_context.user_id}",
                user_id=user_context.user_id,
                analysis_type="monthly_optimization"
            )
            
            # Security analysis task  
            security_task = dispatcher.dispatch(
                f"security_tool_{user_context.user_id}",
                user_id=user_context.user_id,
                scan_depth="comprehensive"
            )
            
            concurrent_tasks.extend([(cost_task, user_context, "cost"), (security_task, user_context, "security")])
        
        # Wait for all concurrent executions
        task_results = await asyncio.gather(
            *[task for task, _, _ in concurrent_tasks], 
            return_exceptions=True
        )
        
        # Verify all executions succeeded
        for i, (result, (_, user_context, analysis_type)) in enumerate(zip(task_results, concurrent_tasks)):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert result.status.name == "SUCCESS"
            
            # Verify business results for each analysis type
            result_str = str(result.result)
            if analysis_type == "cost":
                assert "cost_optimization" in result_str
                assert "potential_savings" in result_str
            else:  # security
                assert "security_analysis" in result_str
                assert "vulnerabilities_found" in result_str or "security_score" in result_str
        
        # Verify each user got their own isolated events
        for _, user_context in dispatchers:
            user_events = websocket_notifier.get_user_events(user_context.user_id)
            assert len(user_events) >= 4  # 2 tools * 2 events each
            
            # Verify events are user-specific
            for event in user_events:
                assert event["user_id"] == user_context.user_id
                assert user_context.user_id in event["tool_name"]
    
    @pytest.mark.integration
    async def test_real_error_handling_integration_across_components(self):
        """Test error handling integration across real components."""
        user_context = RealUserExecutionContext("error-handling-user")
        websocket_notifier = RealWebSocketNotifier()
        websocket_notifier.create_user_session(user_context.user_id)
        
        # Create a tool that will fail in realistic ways
        class FailingBusinessTool(RealBusinessTool):
            def __init__(self, name: str, failure_mode: str):
                super().__init__(name, "cost_optimization")
                self.failure_mode = failure_mode
                
            async def _arun(self, *args, **kwargs):
                await asyncio.sleep(0.05)  # Realistic processing delay
                
                if self.failure_mode == "timeout":
                    await asyncio.sleep(30)  # Simulate timeout
                elif self.failure_mode == "api_error":
                    raise Exception("AWS API rate limit exceeded: 429 Too Many Requests")
                elif self.failure_mode == "permission_error":
                    raise PermissionError("Insufficient permissions to access billing data")
                elif self.failure_mode == "data_error":
                    raise ValueError("Invalid account ID format: must be 12 digits")
                else:
                    raise Exception(f"Unknown error in {self.failure_mode} mode")
        
        # Create tools with different failure modes
        failing_tools = [
            FailingBusinessTool("api_error_tool", "api_error"),
            FailingBusinessTool("permission_error_tool", "permission_error"),
            FailingBusinessTool("data_error_tool", "data_error")
        ]
        
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_notifier,
            tools=failing_tools
        )
        
        # Test error handling for each failure mode
        error_results = []
        for tool in failing_tools:
            result = await dispatcher.dispatch(
                tool.name,
                account_id="invalid-account",
                test_error_handling=True
            )
            error_results.append((tool.failure_mode, result))
        
        # Verify errors are handled properly across all components
        for failure_mode, result in error_results:
            assert result.status.name == "ERROR"
            assert result.message is not None
            
            # Verify error contains relevant business context
            error_msg = result.message.lower()
            if failure_mode == "api_error":
                assert "api" in error_msg or "rate limit" in error_msg
            elif failure_mode == "permission_error":
                assert "permission" in error_msg or "access" in error_msg  
            elif failure_mode == "data_error":
                assert "invalid" in error_msg or "format" in error_msg
        
        # Verify WebSocket events were still sent for failed executions
        user_events = websocket_notifier.get_user_events(user_context.user_id)
        assert len(user_events) >= 3  # At least one executing event per tool
        
        # Verify error events contain useful information
        executing_events = [e for e in user_events if e["type"] == "tool_executing"]
        assert len(executing_events) == 3  # All tools should have started
        
        # Some tools may have completed events with error status
        completed_events = [e for e in user_events if e["type"] == "tool_completed"]
        for event in completed_events:
            # Completed events for failed tools should indicate error
            assert event["tool_name"] in [tool.name for tool in failing_tools]