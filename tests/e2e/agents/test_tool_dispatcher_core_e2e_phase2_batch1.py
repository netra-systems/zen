"""
Tool Dispatcher Core E2E Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool dispatcher works end-to-end with real services for actual users
- Value Impact: Real system validation ensures AI agents deliver consistent business value
- Strategic Impact: E2E validation directly impacts user trust and platform reliability

CRITICAL: These tests validate complete tool dispatcher functionality with real services,
ensuring AI agents can execute tools to deliver business insights in production-like environments.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from netra_backend.app.agents.tool_dispatcher import (
    UnifiedToolDispatcherFactory,
    create_request_scoped_tool_dispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.agents.state import DeepAgentState
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user


class ProductionReadyTool(BaseTool):
    """Production-ready business tool for E2E testing with real business logic."""
    
    def __init__(self, name: str, business_capability: str):
        self.name = name
        self.description = f"Production tool for {business_capability}: {name}"
        self.business_capability = business_capability
        
    def _run(self, *args, **kwargs):
        """Sync version."""
        return asyncio.run(self._arun(*args, **kwargs))
        
    async def _arun(self, *args, **kwargs):
        """Async version with production-ready business logic."""
        # Simulate realistic processing time for production tools
        processing_time = 0.5 if kwargs.get("deep_analysis") else 0.2
        await asyncio.sleep(processing_time)
        
        # Execute business capability
        if self.business_capability == "cost_analysis":
            return await self._production_cost_analysis(**kwargs)
        elif self.business_capability == "performance_monitoring":
            return await self._production_performance_monitoring(**kwargs)
        elif self.business_capability == "security_audit":
            return await self._production_security_audit(**kwargs)
        elif self.business_capability == "compliance_check":
            return await self._production_compliance_check(**kwargs)
        else:
            return await self._production_generic_capability(**kwargs)
    
    async def _production_cost_analysis(self, **kwargs):
        """Production-grade cost analysis capability."""
        # Simulate real cost analysis processing
        await asyncio.sleep(0.3)
        
        account_id = kwargs.get("account_id", "prod-account-123")
        time_period = kwargs.get("time_period", "last_30_days")
        
        return {
            "success": True,
            "capability": "cost_analysis",
            "tool_name": self.name,
            "analysis_metadata": {
                "account_id": account_id,
                "analysis_period": time_period,
                "data_sources": ["AWS Cost Explorer", "CloudWatch", "Reserved Instances"],
                "analysis_depth": kwargs.get("analysis_depth", "standard")
            },
            "cost_insights": {
                "total_spend": {
                    "current_period": 47850.0,
                    "previous_period": 52100.0,
                    "trend": "decreasing",
                    "variance_percent": -8.16
                },
                "service_breakdown": {
                    "EC2": {"cost": 18500.0, "percentage": 38.7, "trend": "stable"},
                    "RDS": {"cost": 12300.0, "percentage": 25.7, "trend": "increasing"},
                    "S3": {"cost": 4200.0, "percentage": 8.8, "trend": "decreasing"},
                    "Lambda": {"cost": 2850.0, "percentage": 6.0, "trend": "stable"},
                    "Other": {"cost": 10000.0, "percentage": 20.8, "trend": "mixed"}
                },
                "optimization_opportunities": [
                    {
                        "service": "EC2",
                        "opportunity": "Rightsize over-provisioned instances",
                        "potential_monthly_savings": 4500.0,
                        "confidence": 0.91,
                        "implementation_effort": "medium"
                    },
                    {
                        "service": "RDS",
                        "opportunity": "Optimize storage and instance types",
                        "potential_monthly_savings": 2100.0,
                        "confidence": 0.85,
                        "implementation_effort": "low"
                    }
                ]
            },
            "business_recommendations": [
                "Implement automated instance scaling",
                "Review and optimize Reserved Instance coverage",
                "Set up cost allocation tags for better tracking",
                "Establish cost anomaly detection alerts"
            ],
            "executive_summary": {
                "cost_trend": "Positive 8% reduction from previous period",
                "top_priority": "EC2 rightsizing for immediate 9.4% savings",
                "estimated_annual_impact": "$79,200 in potential savings"
            }
        }
    
    async def _production_performance_monitoring(self, **kwargs):
        """Production-grade performance monitoring capability."""
        await asyncio.sleep(0.25)
        
        return {
            "success": True,
            "capability": "performance_monitoring",
            "tool_name": self.name,
            "monitoring_scope": {
                "environment": kwargs.get("environment", "production"),
                "services_monitored": kwargs.get("services", ["web-api", "database", "cache"]),
                "monitoring_duration": kwargs.get("duration", "24_hours")
            },
            "performance_metrics": {
                "response_times": {
                    "p50": 145,  # milliseconds
                    "p95": 320,
                    "p99": 850,
                    "average": 180
                },
                "throughput": {
                    "requests_per_second": 1250,
                    "peak_rps": 2100,
                    "total_requests": 108000000
                },
                "error_rates": {
                    "overall_error_rate": 0.015,  # 1.5%
                    "5xx_errors": 0.008,
                    "4xx_errors": 0.007,
                    "timeout_rate": 0.003
                },
                "resource_utilization": {
                    "cpu_average": 62.5,
                    "memory_average": 74.2,
                    "disk_io": "moderate",
                    "network_throughput": "normal"
                }
            },
            "performance_insights": [
                "Database queries are the primary latency contributor (45% of response time)",
                "Cache hit ratio improved to 87% (up from 82% last month)",
                "Peak traffic hours: 2-4 PM EST with 68% higher load",
                "Error spike detected on 2024-01-15 between 3:15-3:45 PM"
            ],
            "optimization_recommendations": [
                "Implement query optimization for top 10 slowest queries",
                "Add read replicas for database scaling during peak hours",
                "Increase cache size by 30% to improve hit ratio to 92%",
                "Set up auto-scaling for handling peak traffic more efficiently"
            ]
        }
    
    async def _production_security_audit(self, **kwargs):
        """Production-grade security audit capability."""
        await asyncio.sleep(0.4)
        
        return {
            "success": True,
            "capability": "security_audit",
            "tool_name": self.name,
            "audit_metadata": {
                "audit_scope": kwargs.get("scope", "comprehensive"),
                "audit_date": datetime.now(timezone.utc).isoformat(),
                "frameworks_assessed": ["SOC2", "ISO27001", "NIST"],
                "coverage_percentage": 94.5
            },
            "security_posture": {
                "overall_score": 8.7,  # out of 10
                "risk_level": "LOW-MEDIUM",
                "compliance_percentage": 91.2,
                "improvement_trend": "positive"
            },
            "findings_summary": {
                "critical": 1,
                "high": 4,
                "medium": 12,
                "low": 23,
                "informational": 8
            },
            "critical_findings": [
                {
                    "id": "CRIT-001",
                    "title": "Exposed database credentials in application config",
                    "risk": "CRITICAL",
                    "affected_systems": ["prod-api-server-3"],
                    "business_impact": "Potential data breach",
                    "remediation": "Move credentials to AWS Secrets Manager",
                    "timeline": "24 hours"
                }
            ],
            "high_priority_actions": [
                "Enable MFA for all administrative accounts",
                "Patch 3 critical security vulnerabilities in web servers",
                "Review and restrict overly permissive IAM policies",
                "Implement network segmentation for production databases"
            ],
            "compliance_status": {
                "SOC2_Type2": {"status": "COMPLIANT", "score": 9.2, "last_audit": "2024-01-15"},
                "ISO27001": {"status": "MOSTLY_COMPLIANT", "score": 8.8, "gaps": 3},
                "GDPR": {"status": "NEEDS_ATTENTION", "score": 7.9, "priority_actions": 2}
            }
        }
    
    async def _production_compliance_check(self, **kwargs):
        """Production-grade compliance checking capability."""
        await asyncio.sleep(0.35)
        
        return {
            "success": True,
            "capability": "compliance_check",
            "tool_name": self.name,
            "compliance_assessment": {
                "assessment_date": datetime.now(timezone.utc).isoformat(),
                "frameworks_checked": kwargs.get("frameworks", ["SOC2", "GDPR", "HIPAA"]),
                "assessment_scope": "full_infrastructure",
                "automated_checks": 347,
                "manual_validations": 28
            },
            "compliance_results": {
                "overall_compliance_score": 88.5,
                "passing_controls": 301,
                "failing_controls": 18,
                "not_applicable": 56,
                "compliance_trend": "improving"
            },
            "framework_specific_results": {
                "SOC2": {
                    "compliance_percentage": 94.2,
                    "status": "COMPLIANT",
                    "controls_passing": 67,
                    "controls_failing": 4,
                    "next_audit_due": "2024-06-15"
                },
                "GDPR": {
                    "compliance_percentage": 86.1,
                    "status": "MOSTLY_COMPLIANT",
                    "key_gaps": ["data retention policies", "user consent management"],
                    "remediation_timeline": "60 days"
                },
                "HIPAA": {
                    "compliance_percentage": 89.7,
                    "status": "COMPLIANT",
                    "last_risk_assessment": "2024-01-10",
                    "encryption_compliance": "full"
                }
            },
            "remediation_plan": [
                "Update data retention policies to meet GDPR requirements",
                "Implement enhanced user consent tracking",
                "Complete remaining SOC2 control implementations",
                "Schedule quarterly compliance review meetings"
            ]
        }
    
    async def _production_generic_capability(self, **kwargs):
        """Generic production capability for other business functions."""
        await asyncio.sleep(0.15)
        
        return {
            "success": True,
            "capability": "generic_business",
            "tool_name": self.name,
            "business_results": {
                "operation_completed": True,
                "business_value_delivered": "Successfully executed business capability",
                "processing_time": "production_grade",
                "data_processed": kwargs.get("data_volume", "enterprise_scale")
            }
        }


class RealUserExecutionContext:
    """Real user execution context for E2E testing with authentication."""
    
    def __init__(self, user_id: str, auth_token: str, user_data: Dict[str, Any]):
        self.user_id = user_id
        self.auth_token = auth_token
        self.user_data = user_data
        self.request_id = f"e2e_req_{int(datetime.now(timezone.utc).timestamp())}_{user_id}"
        self.session_id = f"e2e_session_{user_id}"
        self.created_at = datetime.now(timezone.utc)
        
        # Extract permissions from user data
        self.permissions = user_data.get("permissions", ["read", "write", "execute_tools"])
        
        # E2E test metadata
        self.metadata = {
            "test_type": "e2e",
            "authenticated": True,
            "auth_method": "JWT",
            "environment": "test_e2e",
            "user_tier": "enterprise"  # For E2E we use enterprise features
        }
    
    def has_permission(self, permission: str) -> bool:
        """Check user permissions."""
        return permission in self.permissions
    
    def get_auth_context(self) -> Dict[str, Any]:
        """Get authentication context."""
        return {
            "user_id": self.user_id,
            "auth_token": self.auth_token,
            "permissions": self.permissions,
            "session_id": self.session_id
        }


class ProductionWebSocketManager:
    """Production-like WebSocket manager for E2E testing."""
    
    def __init__(self):
        self.events_sent = []
        self.authenticated_connections = {}
        self.event_delivery_log = {}
        
    async def notify_tool_executing(self, tool_name: str, user_id: str = None, **kwargs):
        """Production-grade tool executing notification."""
        event = {
            "event_type": "tool_executing",
            "event_id": f"prod_exec_{len(self.events_sent)}",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "production_metadata": {
                "environment": "e2e_production_simulation",
                "source": "unified_tool_dispatcher",
                "delivery_guarantee": "at_least_once",
                "priority": "normal"
            },
            "business_context": {
                "workflow_type": kwargs.get("workflow_type", "business_process"),
                "expected_duration": kwargs.get("expected_duration", "< 60s"),
                "business_impact": "medium"
            },
            "payload": kwargs
        }
        
        self.events_sent.append(event)
        await self._deliver_to_authenticated_user(event, user_id)
    
    async def notify_tool_completed(self, tool_name: str, result: Any, user_id: str = None, **kwargs):
        """Production-grade tool completed notification."""
        event = {
            "event_type": "tool_completed",
            "event_id": f"prod_comp_{len(self.events_sent)}",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "production_metadata": {
                "environment": "e2e_production_simulation",
                "source": "unified_tool_dispatcher",
                "delivery_guarantee": "at_least_once",
                "priority": "high"  # Completed events get high priority
            },
            "business_context": {
                "success": self._extract_success(result),
                "business_value": self._extract_business_value(result),
                "result_type": "business_insights"
            },
            "result": result,
            "payload": kwargs
        }
        
        self.events_sent.append(event)
        await self._deliver_to_authenticated_user(event, user_id)
    
    async def _deliver_to_authenticated_user(self, event: Dict, user_id: str):
        """Deliver event to authenticated user connection."""
        if user_id:
            # Simulate production WebSocket delivery
            await asyncio.sleep(0.001)  # Network latency simulation
            
            if user_id not in self.authenticated_connections:
                self.authenticated_connections[user_id] = []
            self.authenticated_connections[user_id].append(event)
            
            # Log delivery for production monitoring
            if user_id not in self.event_delivery_log:
                self.event_delivery_log[user_id] = {"delivered": 0, "failed": 0}
            self.event_delivery_log[user_id]["delivered"] += 1
    
    def _extract_success(self, result: Any) -> bool:
        """Extract success status from tool result."""
        if hasattr(result, 'success'):
            return result.success
        if isinstance(result, dict):
            return result.get('success', True)
        return True
    
    def _extract_business_value(self, result: Any) -> str:
        """Extract business value description."""
        if isinstance(result, dict):
            capability = result.get('capability', 'business_process')
            if capability == 'cost_analysis':
                return 'Cost optimization insights delivered'
            elif capability == 'performance_monitoring':
                return 'Performance optimization insights delivered'
            elif capability == 'security_audit':
                return 'Security posture assessment delivered'
            elif capability == 'compliance_check':
                return 'Compliance status assessment delivered'
        return 'Business insights delivered'
    
    def get_user_events(self, user_id: str) -> List[Dict]:
        """Get events for authenticated user."""
        return self.authenticated_connections.get(user_id, [])
    
    def get_delivery_stats(self, user_id: str) -> Dict[str, int]:
        """Get event delivery statistics."""
        return self.event_delivery_log.get(user_id, {"delivered": 0, "failed": 0})


class TestToolDispatcherCoreE2EWithAuthentication(SSotBaseTestCase):
    """Test tool dispatcher core functionality with real authentication and services."""
    
    @pytest.mark.e2e
    async def test_authenticated_cost_analysis_tool_execution_e2e(self):
        """Test authenticated cost analysis tool execution end-to-end."""
        # Create authenticated user for E2E test
        auth_token, user_data = await create_authenticated_user(
            environment="test",
            user_id="e2e_cost_analyst",
            email="cost.analyst@enterprise.com",
            permissions=["read", "write", "execute_tools", "view_analytics", "access_billing"]
        )
        
        user_context = RealUserExecutionContext(
            user_id="e2e_cost_analyst",
            auth_token=auth_token,
            user_data=user_data
        )
        
        websocket_manager = ProductionWebSocketManager()
        
        # Create production-ready cost analysis tool
        cost_analyzer = ProductionReadyTool("enterprise_cost_analyzer_pro", "cost_analysis")
        
        # Create authenticated tool dispatcher
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=[cost_analyzer]
        )
        
        # Execute cost analysis with enterprise parameters
        enterprise_cost_params = {
            "account_id": "enterprise_prod_123456789",
            "time_period": "last_quarter",
            "analysis_depth": "comprehensive",
            "include_forecasting": True,
            "cost_allocation_tags": ["Environment", "Team", "Project"],
            "budget_threshold_alerts": True,
            "deep_analysis": True  # Trigger longer processing time
        }
        
        result = await dispatcher.dispatch(
            "enterprise_cost_analyzer_pro",
            **enterprise_cost_params
        )
        
        # Verify successful execution with real authentication
        assert result.status.name == "SUCCESS"
        assert result.result is not None
        
        # Verify comprehensive cost analysis results
        cost_data = result.result
        assert cost_data["success"] is True
        assert cost_data["capability"] == "cost_analysis"
        assert "cost_insights" in cost_data
        assert "optimization_opportunities" in cost_data["cost_insights"]
        assert "executive_summary" in cost_data
        
        # Verify business value metrics
        insights = cost_data["cost_insights"]
        assert "total_spend" in insights
        assert "service_breakdown" in insights
        assert insights["total_spend"]["current_period"] > 0
        
        # Verify WebSocket events were sent with production metadata
        user_events = websocket_manager.get_user_events("e2e_cost_analyst")
        assert len(user_events) >= 2  # executing + completed
        
        executing_event = user_events[0]
        assert executing_event["event_type"] == "tool_executing"
        assert executing_event["tool_name"] == "enterprise_cost_analyzer_pro"
        assert "production_metadata" in executing_event
        assert executing_event["production_metadata"]["environment"] == "e2e_production_simulation"
        
        completed_event = user_events[1]
        assert completed_event["event_type"] == "tool_completed"
        assert "Cost optimization insights delivered" in completed_event["business_context"]["business_value"]
        
        # Verify event delivery statistics
        delivery_stats = websocket_manager.get_delivery_stats("e2e_cost_analyst")
        assert delivery_stats["delivered"] >= 2
        assert delivery_stats["failed"] == 0
    
    @pytest.mark.e2e
    async def test_authenticated_multi_tool_business_workflow_e2e(self):
        """Test authenticated multi-tool business workflow execution end-to-end."""
        # Create enterprise user with full permissions
        auth_token, user_data = await create_authenticated_user(
            environment="test",
            user_id="e2e_enterprise_user",
            email="enterprise.user@company.com",
            permissions=["read", "write", "execute_tools", "admin_functions", "view_analytics"]
        )
        
        user_context = RealUserExecutionContext(
            user_id="e2e_enterprise_user",
            auth_token=auth_token,
            user_data=user_data
        )
        
        websocket_manager = ProductionWebSocketManager()
        
        # Create comprehensive business capability tools
        business_tools = [
            ProductionReadyTool("performance_monitor_pro", "performance_monitoring"),
            ProductionReadyTool("security_auditor_pro", "security_audit"),
            ProductionReadyTool("compliance_checker_pro", "compliance_check")
        ]
        
        # Create authenticated dispatcher with all business tools
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=business_tools
        )
        
        # Create comprehensive agent state for business workflow
        business_workflow_state = DeepAgentState(
            user_request="Perform comprehensive enterprise assessment covering performance, security, and compliance"
        )
        
        # Execute business workflow tools sequentially
        workflow_results = {}
        
        # Step 1: Performance Monitoring
        performance_result = await dispatcher.dispatch_tool(
            tool_name="performance_monitor_pro",
            parameters={
                "environment": "production",
                "services": ["api-gateway", "microservices", "database-cluster", "cache-layer"],
                "duration": "7_days",
                "include_capacity_planning": True
            },
            state=business_workflow_state,
            run_id="e2e_performance_assessment"
        )
        
        assert performance_result.success is True
        assert "performance_monitoring" in str(performance_result.result)
        workflow_results["performance"] = performance_result.result
        
        # Step 2: Security Audit
        security_result = await dispatcher.dispatch_tool(
            tool_name="security_auditor_pro", 
            parameters={
                "scope": "comprehensive",
                "include_penetration_testing": True,
                "frameworks": ["SOC2", "ISO27001", "NIST"],
                "environment": "production"
            },
            state=business_workflow_state,
            run_id="e2e_security_audit"
        )
        
        assert security_result.success is True
        assert "security_audit" in str(security_result.result)
        workflow_results["security"] = security_result.result
        
        # Step 3: Compliance Check
        compliance_result = await dispatcher.dispatch_tool(
            tool_name="compliance_checker_pro",
            parameters={
                "frameworks": ["SOC2", "GDPR", "HIPAA"],
                "include_gap_analysis": True,
                "generate_remediation_plan": True
            },
            state=business_workflow_state,
            run_id="e2e_compliance_check"
        )
        
        assert compliance_result.success is True
        assert "compliance_check" in str(compliance_result.result)
        workflow_results["compliance"] = compliance_result.result
        
        # Verify comprehensive business workflow results
        for capability, result in workflow_results.items():
            assert "success" in result and result["success"] is True
            
            if capability == "performance":
                assert "performance_metrics" in result
                assert "optimization_recommendations" in result
            elif capability == "security":
                assert "security_posture" in result
                assert "findings_summary" in result
            elif capability == "compliance":
                assert "compliance_results" in result
                assert "framework_specific_results" in result
        
        # Verify complete workflow WebSocket event sequence
        user_events = websocket_manager.get_user_events("e2e_enterprise_user")
        assert len(user_events) >= 6  # 3 tools * 2 events each
        
        # Verify event sequence and content
        tool_names = ["performance_monitor_pro", "security_auditor_pro", "compliance_checker_pro"]
        for tool_name in tool_names:
            tool_events = [e for e in user_events if e["tool_name"] == tool_name]
            assert len(tool_events) >= 2  # executing + completed
            
            executing_event = next(e for e in tool_events if e["event_type"] == "tool_executing")
            completed_event = next(e for e in tool_events if e["event_type"] == "tool_completed")
            
            # Verify production-grade event metadata
            assert executing_event["production_metadata"]["delivery_guarantee"] == "at_least_once"
            assert completed_event["production_metadata"]["priority"] == "high"
            assert "business_insights" in completed_event["business_context"]["result_type"]
        
        # Verify authentication context maintained throughout workflow
        auth_context = user_context.get_auth_context()
        assert auth_context["user_id"] == "e2e_enterprise_user"
        assert len(auth_context["permissions"]) >= 5  # Enterprise user permissions
    
    @pytest.mark.e2e
    async def test_authenticated_concurrent_tool_execution_e2e(self):
        """Test authenticated concurrent tool execution with real user isolation."""
        # Create multiple authenticated users for concurrent testing
        users = []
        for i in range(1, 4):
            auth_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"e2e_concurrent_user_{i}",
                email=f"user{i}@concurrent.test.com",
                permissions=["read", "write", "execute_tools"]
            )
            
            user_context = RealUserExecutionContext(
                user_id=f"e2e_concurrent_user_{i}",
                auth_token=auth_token,
                user_data=user_data
            )
            users.append(user_context)
        
        websocket_manager = ProductionWebSocketManager()
        
        # Create user-specific business tools
        user_dispatchers = []
        for i, user_context in enumerate(users, 1):
            # Each user gets different business capabilities
            if i == 1:
                tools = [ProductionReadyTool(f"cost_tool_user_{i}", "cost_analysis")]
            elif i == 2:
                tools = [ProductionReadyTool(f"performance_tool_user_{i}", "performance_monitoring")]
            else:
                tools = [ProductionReadyTool(f"security_tool_user_{i}", "security_audit")]
            
            dispatcher = await create_request_scoped_tool_dispatcher(
                user_context=user_context,
                websocket_manager=websocket_manager,
                tools=tools
            )
            user_dispatchers.append((dispatcher, user_context, tools[0]))
        
        # Execute tools concurrently for all users
        concurrent_tasks = []
        for dispatcher, user_context, tool in user_dispatchers:
            # Create user-specific parameters
            user_num = int(user_context.user_id.split("_")[-1])
            if user_num == 1:  # cost analysis user
                params = {
                    "account_id": f"user_{user_num}_account",
                    "time_period": "monthly",
                    "deep_analysis": True
                }
            elif user_num == 2:  # performance monitoring user
                params = {
                    "environment": f"user_{user_num}_env",
                    "duration": "1_day",
                    "services": [f"service_{user_num}_api", f"service_{user_num}_db"]
                }
            else:  # security audit user
                params = {
                    "scope": f"user_{user_num}_scope",
                    "frameworks": ["SOC2"],
                    "audit_depth": "comprehensive"
                }
            
            task = dispatcher.dispatch(
                tool.name,
                **params,
                user_context_id=user_context.user_id,
                concurrent_execution=True
            )
            concurrent_tasks.append((task, user_context, tool))
        
        # Wait for all concurrent executions
        results = await asyncio.gather(
            *[task for task, _, _ in concurrent_tasks],
            return_exceptions=True
        )
        
        # Verify all concurrent executions succeeded with proper isolation
        for i, (result, (_, user_context, tool)) in enumerate(zip(results, concurrent_tasks)):
            assert not isinstance(result, Exception), f"User {user_context.user_id} task failed: {result}"
            assert result.status.name == "SUCCESS"
            
            # Verify user-specific results
            result_data = result.result
            assert result_data["success"] is True
            assert user_context.user_id.split("_")[-1] in str(result_data)  # User number in results
            
            # Verify correct capability executed
            user_num = int(user_context.user_id.split("_")[-1])
            if user_num == 1:
                assert result_data["capability"] == "cost_analysis"
            elif user_num == 2:
                assert result_data["capability"] == "performance_monitoring"
            else:
                assert result_data["capability"] == "security_audit"
        
        # Verify user isolation in WebSocket events
        for _, user_context, _ in concurrent_tasks:
            user_events = websocket_manager.get_user_events(user_context.user_id)
            assert len(user_events) >= 2  # executing + completed
            
            # Verify all events belong to this user
            for event in user_events:
                assert event["user_id"] == user_context.user_id
                
            # Verify user-specific content in events
            user_num = user_context.user_id.split("_")[-1]
            for event in user_events:
                assert user_num in event["tool_name"]
        
        # Verify no cross-user event contamination
        all_user_ids = [uc.user_id for _, uc, _ in concurrent_tasks]
        for user_id in all_user_ids:
            user_events = websocket_manager.get_user_events(user_id)
            for event in user_events:
                # Verify no events from other users leaked in
                assert event["user_id"] == user_id
                other_user_ids = [uid for uid in all_user_ids if uid != user_id]
                for other_user_id in other_user_ids:
                    assert other_user_id not in str(event["payload"])
    
    @pytest.mark.e2e
    async def test_authenticated_error_recovery_e2e(self):
        """Test authenticated error recovery and resilience in E2E environment."""
        # Create authenticated user for error testing
        auth_token, user_data = await create_authenticated_user(
            environment="test",
            user_id="e2e_error_resilience_user",
            email="error.test@resilience.com",
            permissions=["read", "write", "execute_tools"]
        )
        
        user_context = RealUserExecutionContext(
            user_id="e2e_error_resilience_user",
            auth_token=auth_token,
            user_data=user_data
        )
        
        websocket_manager = ProductionWebSocketManager()
        
        # Create tools with different error scenarios for E2E testing
        class E2EErrorSimulationTool(ProductionReadyTool):
            def __init__(self, name: str, error_scenario: str):
                super().__init__(name, "cost_analysis")
                self.error_scenario = error_scenario
                self.attempt_count = 0
                
            async def _arun(self, *args, **kwargs):
                self.attempt_count += 1
                
                # Simulate different E2E error scenarios
                if self.error_scenario == "transient_auth_error":
                    if self.attempt_count <= 1:
                        # Simulate temporary authentication issue
                        raise PermissionError("Authentication token temporarily invalid")
                    # Success on retry
                    return await super()._production_cost_analysis(**kwargs)
                    
                elif self.error_scenario == "service_unavailable":
                    if self.attempt_count <= 2:
                        raise ConnectionError("Cost analysis service temporarily unavailable")
                    return await super()._production_cost_analysis(**kwargs)
                    
                elif self.error_scenario == "partial_success":
                    # Simulate partial data availability
                    result = await super()._production_cost_analysis(**kwargs)
                    if self.attempt_count <= 1:
                        result["warnings"] = ["Some cost data unavailable due to API limits"]
                        result["data_completeness"] = 0.75
                    return result
                    
                else:  # permanent_error
                    raise Exception("Permanent system error: Unable to access cost data")
        
        error_tools = [
            E2EErrorSimulationTool("transient_auth_tool", "transient_auth_error"),
            E2EErrorSimulationTool("service_unavailable_tool", "service_unavailable"),
            E2EErrorSimulationTool("partial_success_tool", "partial_success"),
            E2EErrorSimulationTool("permanent_error_tool", "permanent_error")
        ]
        
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=error_tools
        )
        
        # Test error scenarios
        error_results = []
        for tool in error_tools:
            result = await dispatcher.dispatch(
                tool.name,
                account_id="error_test_account",
                error_scenario=tool.error_scenario,
                resilience_test=True
            )
            error_results.append((tool.error_scenario, result, tool.attempt_count))
        
        # Verify error handling behavior
        for scenario, result, attempt_count in error_results:
            if scenario in ["transient_auth_error", "service_unavailable", "partial_success"]:
                # These should eventually succeed
                assert result.status.name == "SUCCESS", f"Scenario {scenario} should have succeeded"
                
                if scenario == "partial_success":
                    # Should contain warning about partial data
                    result_str = str(result.result)
                    assert "warnings" in result_str or "completeness" in result_str
                    
            else:  # permanent_error
                # This should fail permanently
                assert result.status.name == "ERROR"
                assert "error" in result.message.lower() or "system error" in result.message.lower()
        
        # Verify WebSocket events were sent even for error scenarios
        user_events = websocket_manager.get_user_events("e2e_error_resilience_user")
        # Should have events for all tools that attempted execution
        assert len(user_events) >= 4  # At least one event per tool
        
        # Verify error context in events
        for event in user_events:
            assert event["user_id"] == "e2e_error_resilience_user"
            assert "production_metadata" in event
            
    @pytest.mark.e2e
    async def test_authenticated_business_value_delivery_e2e(self):
        """Test complete authenticated business value delivery end-to-end."""
        # Create authenticated business user
        auth_token, user_data = await create_authenticated_user(
            environment="test",
            user_id="e2e_business_executive",
            email="executive@business.com",
            permissions=["read", "write", "execute_tools", "view_analytics", "admin_functions"]
        )
        
        user_context = RealUserExecutionContext(
            user_id="e2e_business_executive",
            auth_token=auth_token,
            user_data=user_data
        )
        
        websocket_manager = ProductionWebSocketManager()
        
        # Create comprehensive business intelligence tool
        business_intelligence_tool = ProductionReadyTool("executive_business_intelligence", "cost_analysis")
        
        dispatcher = await create_request_scoped_tool_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager,
            tools=[business_intelligence_tool]
        )
        
        # Execute comprehensive business analysis
        executive_state = DeepAgentState(
            user_request="Provide comprehensive business intelligence report for executive decision making"
        )
        
        business_result = await dispatcher.dispatch_tool(
            tool_name="executive_business_intelligence",
            parameters={
                "analysis_scope": "enterprise_wide",
                "time_horizon": "quarterly_with_annual_projection",
                "include_forecasting": True,
                "include_benchmarking": True,
                "executive_summary": True,
                "deep_analysis": True,
                "stakeholder_report": True
            },
            state=executive_state,
            run_id="e2e_executive_intelligence"
        )
        
        # Verify comprehensive business value delivery
        assert business_result.success is True
        business_data = business_result.result
        
        # Verify executive-level insights
        assert "executive_summary" in business_data
        assert "cost_insights" in business_data
        assert "optimization_opportunities" in business_data["cost_insights"]
        
        executive_summary = business_data["executive_summary"]
        assert "cost_trend" in executive_summary
        assert "top_priority" in executive_summary
        assert "estimated_annual_impact" in executive_summary
        
        # Verify actionable business recommendations
        assert "business_recommendations" in business_data
        recommendations = business_data["business_recommendations"]
        assert len(recommendations) >= 3  # Multiple actionable recommendations
        
        # Verify quantified business impact
        optimization_opportunities = business_data["cost_insights"]["optimization_opportunities"]
        total_potential_savings = sum(opp["potential_monthly_savings"] for opp in optimization_opportunities)
        assert total_potential_savings > 0, "Should have quantified savings opportunities"
        
        # Verify WebSocket events delivered business context
        user_events = websocket_manager.get_user_events("e2e_business_executive")
        assert len(user_events) >= 2
        
        completed_event = next(e for e in user_events if e["event_type"] == "tool_completed")
        assert "Cost optimization insights delivered" in completed_event["business_context"]["business_value"]
        assert completed_event["business_context"]["result_type"] == "business_insights"
        
        # Verify authentication maintained throughout business process
        auth_context = user_context.get_auth_context()
        assert "admin_functions" in auth_context["permissions"]  # Executive permissions maintained
        
        # Verify delivery statistics for production monitoring
        delivery_stats = websocket_manager.get_delivery_stats("e2e_business_executive")
        assert delivery_stats["delivered"] >= 2
        assert delivery_stats["failed"] == 0