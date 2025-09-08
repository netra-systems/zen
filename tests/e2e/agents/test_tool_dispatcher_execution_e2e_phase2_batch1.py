"""
Tool Dispatcher Execution E2E Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool execution delivers real business value in production environment
- Value Impact: E2E execution validation ensures AI agents provide reliable business insights
- Strategic Impact: Execution reliability in real environments drives user adoption and retention

CRITICAL: These tests validate complete tool execution flow with real services and authentication,
ensuring AI agents can execute tools to deliver consistent business value to real users.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import (
    ToolInput,
    ToolResult,
    ToolStatus,
    ToolExecuteResponse
)
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user


class EnterpriseProductionTool(BaseTool):
    """Enterprise-grade production tool for E2E execution testing."""
    
    def __init__(self, name: str, execution_complexity: str, business_domain: str):
        self.name = name
        self.description = f"Enterprise {business_domain} tool: {name} ({execution_complexity} complexity)"
        self.execution_complexity = execution_complexity
        self.business_domain = business_domain
        self.execution_metrics = {"calls": 0, "successes": 0, "failures": 0}
        
    def _run(self, *args, **kwargs):
        """Sync version.""" 
        return asyncio.run(self._arun(*args, **kwargs))
        
    async def _arun(self, *args, **kwargs):
        """Async version with enterprise-grade execution patterns."""
        self.execution_metrics["calls"] += 1
        
        try:
            # Simulate complexity-based execution time
            execution_times = {
                "simple": 0.1,
                "standard": 0.3,
                "complex": 0.8,
                "enterprise": 1.5
            }
            
            processing_time = execution_times.get(self.execution_complexity, 0.5)
            await asyncio.sleep(processing_time)
            
            # Execute business domain logic
            if self.business_domain == "financial_optimization":
                result = await self._financial_optimization_execution(**kwargs)
            elif self.business_domain == "operational_analytics":
                result = await self._operational_analytics_execution(**kwargs)
            elif self.business_domain == "risk_management":
                result = await self._risk_management_execution(**kwargs)
            else:
                result = await self._generic_enterprise_execution(**kwargs)
            
            self.execution_metrics["successes"] += 1
            return result
            
        except Exception as e:
            self.execution_metrics["failures"] += 1
            raise
    
    async def _financial_optimization_execution(self, **kwargs):
        """Enterprise financial optimization execution."""
        # Simulate complex financial analysis
        await asyncio.sleep(0.2)
        
        return {
            "execution_success": True,
            "business_domain": "financial_optimization", 
            "tool_name": self.name,
            "complexity_level": self.execution_complexity,
            "financial_analysis": {
                "portfolio_value": kwargs.get("portfolio_value", 2500000.0),
                "optimization_model": "modern_portfolio_theory",
                "risk_metrics": {
                    "value_at_risk_95": 125000.0,
                    "sharpe_ratio": 1.42,
                    "beta": 0.87,
                    "alpha": 0.045
                },
                "optimization_results": {
                    "recommended_reallocation": {
                        "equities": 0.65,
                        "bonds": 0.25, 
                        "alternatives": 0.10
                    },
                    "expected_annual_return": 0.082,
                    "expected_volatility": 0.156,
                    "improvement_over_current": 0.013
                },
                "implementation_timeline": "2-3 weeks",
                "regulatory_compliance": "fully_compliant"
            },
            "business_recommendations": [
                "Implement gradual reallocation over 6-week period",
                "Establish automated rebalancing triggers",
                "Set up risk monitoring dashboards", 
                "Schedule quarterly optimization reviews"
            ],
            "execution_metadata": {
                "processing_time_ms": int(kwargs.get("processing_time", 800)),
                "data_sources": ["market_data", "portfolio_holdings", "risk_models"],
                "model_confidence": 0.94
            }
        }
    
    async def _operational_analytics_execution(self, **kwargs):
        """Enterprise operational analytics execution."""
        await asyncio.sleep(0.25)
        
        return {
            "execution_success": True,
            "business_domain": "operational_analytics",
            "tool_name": self.name,
            "complexity_level": self.execution_complexity,
            "operational_insights": {
                "efficiency_metrics": {
                    "overall_efficiency": 0.847,
                    "process_automation_rate": 0.73,
                    "error_rate": 0.0023,
                    "customer_satisfaction": 8.6
                },
                "performance_analysis": {
                    "throughput_improvement": 0.34,
                    "cost_reduction": 0.18,
                    "quality_score": 9.2,
                    "delivery_time_improvement": 0.28
                },
                "bottleneck_identification": [
                    {
                        "process": "order_fulfillment",
                        "bottleneck": "inventory_management",
                        "impact": "high",
                        "resolution_timeline": "4-6 weeks"
                    },
                    {
                        "process": "customer_onboarding", 
                        "bottleneck": "document_verification",
                        "impact": "medium",
                        "resolution_timeline": "2-3 weeks"
                    }
                ]
            },
            "optimization_roadmap": [
                "Implement AI-powered inventory forecasting",
                "Automate document verification workflow",
                "Deploy real-time performance monitoring",
                "Establish continuous improvement processes"
            ],
            "roi_projections": {
                "year_1": {"cost_savings": 245000, "efficiency_gain": 0.22},
                "year_2": {"cost_savings": 380000, "efficiency_gain": 0.31},
                "year_3": {"cost_savings": 520000, "efficiency_gain": 0.42}
            }
        }
    
    async def _risk_management_execution(self, **kwargs):
        """Enterprise risk management execution."""
        await asyncio.sleep(0.35)
        
        return {
            "execution_success": True,
            "business_domain": "risk_management",
            "tool_name": self.name,
            "complexity_level": self.execution_complexity,
            "risk_assessment": {
                "overall_risk_score": 6.8,  # out of 10
                "risk_categories": {
                    "operational": {"score": 5.2, "trend": "stable", "priority": "medium"},
                    "financial": {"score": 4.1, "trend": "improving", "priority": "low"},
                    "regulatory": {"score": 7.3, "trend": "stable", "priority": "high"},
                    "cybersecurity": {"score": 8.9, "trend": "worsening", "priority": "critical"},
                    "market": {"score": 6.5, "trend": "volatile", "priority": "medium"}
                },
                "critical_risks": [
                    {
                        "risk_id": "CYBER-001",
                        "category": "cybersecurity",
                        "description": "Increased phishing attempts targeting executives",
                        "probability": 0.75,
                        "impact": "high",
                        "mitigation_status": "in_progress"
                    },
                    {
                        "risk_id": "REG-003",
                        "category": "regulatory",
                        "description": "New data privacy regulations affecting EU operations",
                        "probability": 0.95,
                        "impact": "medium",
                        "mitigation_status": "planned"
                    }
                ]
            },
            "mitigation_strategies": [
                "Deploy advanced email security with AI threat detection",
                "Implement zero-trust network architecture",
                "Establish regulatory compliance monitoring system",
                "Create incident response automation workflows"
            ],
            "business_continuity": {
                "recovery_time_objective": "4 hours",
                "recovery_point_objective": "1 hour", 
                "business_impact_analysis": "completed",
                "disaster_recovery_testing": "quarterly"
            }
        }
    
    async def _generic_enterprise_execution(self, **kwargs):
        """Generic enterprise execution for other domains."""
        await asyncio.sleep(0.15)
        
        return {
            "execution_success": True,
            "business_domain": "generic_enterprise",
            "tool_name": self.name,
            "complexity_level": self.execution_complexity,
            "enterprise_results": {
                "process_completed": True,
                "business_outcome": f"Enterprise {self.execution_complexity} execution completed successfully",
                "key_metrics": {
                    "efficiency": 0.89,
                    "quality": 0.93,
                    "user_satisfaction": 8.4
                }
            }
        }


class ProductionWebSocketEventStream:
    """Production-grade WebSocket event stream for E2E execution testing."""
    
    def __init__(self):
        self.event_stream = []
        self.user_streams = {}
        self.execution_traces = {}
        
    async def notify_tool_executing(self, tool_name: str, user_id: str = None, **kwargs):
        """Production tool executing notification with execution tracing."""
        event = {
            "stream_event": "tool_executing",
            "event_id": f"exec_trace_{len(self.event_stream)}",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_trace": {
                "phase": "initialization", 
                "expected_duration": kwargs.get("expected_duration", "unknown"),
                "complexity": kwargs.get("complexity_level", "standard"),
                "business_domain": kwargs.get("business_domain", "general")
            },
            "production_context": {
                "environment": "e2e_production",
                "monitoring": "enabled",
                "tracing": "full",
                "business_criticality": "high"
            },
            "payload": kwargs
        }
        
        self.event_stream.append(event)
        await self._route_to_user_stream(event, user_id)
        
        # Start execution tracing
        if tool_name not in self.execution_traces:
            self.execution_traces[tool_name] = {
                "start_time": datetime.now(timezone.utc),
                "events": [event],
                "status": "executing"
            }
    
    async def notify_tool_completed(self, tool_name: str, result: Any, user_id: str = None, **kwargs):
        """Production tool completed notification with execution tracing."""
        event = {
            "stream_event": "tool_completed",
            "event_id": f"comp_trace_{len(self.event_stream)}",
            "tool_name": tool_name,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_trace": {
                "phase": "completion",
                "success": self._extract_success(result),
                "business_value": self._extract_business_value(result),
                "execution_duration": self._calculate_duration(tool_name)
            },
            "production_context": {
                "environment": "e2e_production",
                "result_validation": "passed",
                "business_impact": "delivered",
                "monitoring_status": "healthy"
            },
            "result": result,
            "payload": kwargs
        }
        
        self.event_stream.append(event)
        await self._route_to_user_stream(event, user_id)
        
        # Complete execution tracing
        if tool_name in self.execution_traces:
            self.execution_traces[tool_name]["events"].append(event)
            self.execution_traces[tool_name]["status"] = "completed"
            self.execution_traces[tool_name]["end_time"] = datetime.now(timezone.utc)
    
    async def _route_to_user_stream(self, event: Dict, user_id: str):
        """Route event to user-specific stream."""
        if user_id:
            if user_id not in self.user_streams:
                self.user_streams[user_id] = []
            self.user_streams[user_id].append(event)
    
    def _extract_success(self, result: Any) -> bool:
        """Extract success status from execution result."""
        if hasattr(result, 'success'):
            return result.success
        if isinstance(result, dict):
            return result.get('execution_success', result.get('success', True))
        return True
    
    def _extract_business_value(self, result: Any) -> str:
        """Extract business value from execution result."""
        if isinstance(result, dict):
            domain = result.get('business_domain', 'general')
            if domain == 'financial_optimization':
                return 'Financial optimization and portfolio insights delivered'
            elif domain == 'operational_analytics':
                return 'Operational efficiency insights and improvement roadmap delivered'
            elif domain == 'risk_management':
                return 'Risk assessment and mitigation strategies delivered'
        return 'Business insights and recommendations delivered'
    
    def _calculate_duration(self, tool_name: str) -> Optional[str]:
        """Calculate execution duration for tracing."""
        if tool_name in self.execution_traces:
            start_time = self.execution_traces[tool_name]["start_time"]
            duration = datetime.now(timezone.utc) - start_time
            return f"{duration.total_seconds():.2f}s"
        return None
    
    def get_user_stream(self, user_id: str) -> List[Dict]:
        """Get event stream for specific user."""
        return self.user_streams.get(user_id, [])
    
    def get_execution_trace(self, tool_name: str) -> Optional[Dict]:
        """Get execution trace for specific tool."""
        return self.execution_traces.get(tool_name)
    
    def get_stream_metrics(self) -> Dict[str, Any]:
        """Get production stream metrics."""
        return {
            "total_events": len(self.event_stream),
            "active_users": len(self.user_streams),
            "completed_executions": len([t for t in self.execution_traces.values() if t["status"] == "completed"]),
            "average_execution_time": self._calculate_average_execution_time()
        }
    
    def _calculate_average_execution_time(self) -> Optional[float]:
        """Calculate average execution time across all tools."""
        completed_traces = [t for t in self.execution_traces.values() if t["status"] == "completed" and "end_time" in t]
        if not completed_traces:
            return None
        
        total_time = sum((t["end_time"] - t["start_time"]).total_seconds() for t in completed_traces)
        return total_time / len(completed_traces)


class TestToolExecutionEngineRealServiceE2E(SSotBaseTestCase):
    """Test tool execution engine with real services in E2E environment."""
    
    @pytest.mark.e2e
    async def test_authenticated_financial_optimization_execution_e2e(self):
        """Test authenticated financial optimization tool execution end-to-end."""
        # Create authenticated financial analyst user
        auth_token, user_data = await create_authenticated_user(
            environment="test",
            user_id="e2e_financial_analyst",
            email="financial.analyst@enterprise.com",
            permissions=["read", "write", "execute_tools", "view_analytics", "financial_data_access"]
        )
        
        websocket_stream = ProductionWebSocketEventStream()
        execution_engine = ToolExecutionEngine(websocket_manager=websocket_stream)
        
        # Create enterprise financial optimization tool
        financial_tool = EnterpriseProductionTool(
            "portfolio_optimizer_pro",
            "enterprise",
            "financial_optimization"
        )
        
        # Execute financial optimization with realistic parameters
        financial_params = {
            "portfolio_value": 5000000.0,  # $5M portfolio
            "risk_tolerance": "moderate_aggressive",
            "investment_horizon": "long_term",
            "rebalancing_frequency": "quarterly",
            "tax_optimization": True,
            "esg_constraints": True,
            "user_context": {"user_id": "e2e_financial_analyst", "auth_token": auth_token}
        }
        
        tool_input = ToolInput(
            tool_name="portfolio_optimizer_pro",
            kwargs=financial_params
        )
        
        result = await execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=financial_tool,
            kwargs=financial_params
        )
        
        # Verify successful financial execution
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        
        # Verify comprehensive financial results
        financial_data = result.result
        assert financial_data["execution_success"] is True
        assert financial_data["business_domain"] == "financial_optimization"
        assert "financial_analysis" in financial_data
        assert "optimization_results" in financial_data["financial_analysis"]
        
        # Verify quantified financial metrics
        analysis = financial_data["financial_analysis"]
        assert "risk_metrics" in analysis
        assert analysis["risk_metrics"]["sharpe_ratio"] > 0
        assert analysis["optimization_results"]["expected_annual_return"] > 0
        
        # Verify business recommendations
        assert "business_recommendations" in financial_data
        assert len(financial_data["business_recommendations"]) >= 3
        
        # Verify WebSocket event stream
        user_events = websocket_stream.get_user_stream("e2e_financial_analyst")
        assert len(user_events) >= 2  # executing + completed
        
        executing_event = user_events[0]
        assert executing_event["stream_event"] == "tool_executing"
        assert executing_event["execution_trace"]["business_domain"] == "financial_optimization"
        
        completed_event = user_events[1]
        assert completed_event["stream_event"] == "tool_completed"
        assert "Financial optimization" in completed_event["execution_trace"]["business_value"]
        
        # Verify execution tracing
        execution_trace = websocket_stream.get_execution_trace("portfolio_optimizer_pro")
        assert execution_trace is not None
        assert execution_trace["status"] == "completed"
        assert "end_time" in execution_trace
    
    @pytest.mark.e2e
    async def test_authenticated_complex_operational_analytics_execution_e2e(self):
        """Test authenticated complex operational analytics execution end-to-end."""
        # Create authenticated operations manager user
        auth_token, user_data = await create_authenticated_user(
            environment="test",
            user_id="e2e_operations_manager",
            email="operations.manager@enterprise.com",
            permissions=["read", "write", "execute_tools", "operational_data_access", "process_optimization"]
        )
        
        websocket_stream = ProductionWebSocketEventStream()
        execution_engine = ToolExecutionEngine(websocket_manager=websocket_stream)
        
        # Create complex operational analytics tool
        operations_tool = EnterpriseProductionTool(
            "operational_intelligence_engine",
            "complex",
            "operational_analytics"
        )
        
        # Execute with comprehensive operational parameters
        operational_params = {
            "analysis_scope": "enterprise_wide",
            "time_horizon": "quarterly_with_projections",
            "include_predictive_analytics": True,
            "process_optimization": True,
            "cost_benefit_analysis": True,
            "stakeholder_impact_assessment": True,
            "implementation_roadmap": True,
            "user_context": {"user_id": "e2e_operations_manager", "auth_token": auth_token}
        }
        
        # Create agent state for operational context
        operational_state = DeepAgentState(
            user_request="Perform comprehensive operational analysis with optimization recommendations"
        )
        
        run_id = "e2e_operational_intelligence"
        
        # Execute with state management
        response = await execution_engine.execute_with_state(
            tool=operations_tool,
            tool_name="operational_intelligence_engine",
            parameters=operational_params,
            state=operational_state,
            run_id=run_id
        )
        
        # Verify successful operational execution
        assert hasattr(response, 'success')
        assert response.success is True
        
        # Verify comprehensive operational insights
        operational_data = response.result
        assert "operational_insights" in operational_data
        assert "performance_analysis" in operational_data["operational_insights"]
        assert "bottleneck_identification" in operational_data["operational_insights"]
        
        # Verify quantified business impact
        insights = operational_data["operational_insights"]
        assert "efficiency_metrics" in insights
        assert insights["efficiency_metrics"]["overall_efficiency"] > 0
        assert "roi_projections" in operational_data
        
        # Verify actionable optimization roadmap
        assert "optimization_roadmap" in operational_data
        roadmap = operational_data["optimization_roadmap"]
        assert len(roadmap) >= 3  # Multiple optimization steps
        
        # Verify WebSocket event stream with operational context
        user_events = websocket_stream.get_user_stream("e2e_operations_manager")
        assert len(user_events) >= 2
        
        completed_event = next(e for e in user_events if e["stream_event"] == "tool_completed")
        assert "operational efficiency insights" in completed_event["execution_trace"]["business_value"].lower()
        
        # Verify execution trace includes complexity handling
        execution_trace = websocket_stream.get_execution_trace("operational_intelligence_engine")
        assert execution_trace is not None
        duration_str = execution_trace.get("events", [{}])[-1].get("execution_trace", {}).get("execution_duration")
        if duration_str:
            duration = float(duration_str.rstrip('s'))
            assert duration >= 0.8  # Complex execution should take reasonable time
    
    @pytest.mark.e2e
    async def test_authenticated_concurrent_multi_domain_execution_e2e(self):
        """Test authenticated concurrent execution across multiple business domains."""
        # Create multiple domain expert users
        domain_experts = [
            ("e2e_financial_expert", "financial.expert@enterprise.com", ["financial_data_access"]),
            ("e2e_operations_expert", "operations.expert@enterprise.com", ["operational_data_access"]),
            ("e2e_risk_expert", "risk.expert@enterprise.com", ["risk_data_access"])
        ]
        
        # Authenticate all users
        authenticated_users = []
        for user_id, email, extra_permissions in domain_experts:
            auth_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=user_id,
                email=email,
                permissions=["read", "write", "execute_tools"] + extra_permissions
            )
            authenticated_users.append((user_id, auth_token, user_data))
        
        websocket_stream = ProductionWebSocketEventStream()
        
        # Create domain-specific enterprise tools
        domain_tools = [
            ("portfolio_risk_analyzer", "standard", "financial_optimization"),
            ("process_efficiency_optimizer", "complex", "operational_analytics"),
            ("enterprise_risk_assessor", "enterprise", "risk_management")
        ]
        
        # Create execution engines for each domain
        execution_engines = []
        for i, (user_id, auth_token, user_data) in enumerate(authenticated_users):
            engine = ToolExecutionEngine(websocket_manager=websocket_stream)
            tool_name, complexity, domain = domain_tools[i]
            tool = EnterpriseProductionTool(tool_name, complexity, domain)
            execution_engines.append((engine, tool, user_id, auth_token, domain))
        
        # Execute tools concurrently across all domains
        concurrent_tasks = []
        for engine, tool, user_id, auth_token, domain in execution_engines:
            # Create domain-specific parameters
            if domain == "financial_optimization":
                params = {
                    "analysis_type": "comprehensive_portfolio_risk",
                    "market_scenarios": ["bull", "bear", "sideways"],
                    "user_context": {"user_id": user_id, "auth_token": auth_token}
                }
            elif domain == "operational_analytics":
                params = {
                    "optimization_focus": "end_to_end_processes",
                    "performance_benchmarking": True,
                    "user_context": {"user_id": user_id, "auth_token": auth_token}
                }
            else:  # risk_management
                params = {
                    "risk_assessment_depth": "enterprise_wide",
                    "regulatory_compliance": True,
                    "user_context": {"user_id": user_id, "auth_token": auth_token}
                }
            
            tool_input = ToolInput(tool_name=tool.name, kwargs=params)
            task = engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=tool,
                kwargs=params
            )
            concurrent_tasks.append((task, user_id, tool.name, domain))
        
        # Wait for all concurrent executions
        results = await asyncio.gather(
            *[task for task, _, _, _ in concurrent_tasks],
            return_exceptions=True
        )
        
        # Verify all concurrent executions succeeded
        for i, (result, (_, user_id, tool_name, domain)) in enumerate(zip(results, concurrent_tasks)):
            assert not isinstance(result, Exception), f"Task {i} for {user_id} failed: {result}"
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.SUCCESS
            
            # Verify domain-specific results
            result_data = result.result
            assert result_data["execution_success"] is True
            assert result_data["business_domain"] == domain
            
            # Verify domain-specific content
            if domain == "financial_optimization":
                assert "financial_analysis" in result_data
                assert "risk_metrics" in result_data["financial_analysis"]
            elif domain == "operational_analytics":
                assert "operational_insights" in result_data
                assert "efficiency_metrics" in result_data["operational_insights"]
            else:  # risk_management
                assert "risk_assessment" in result_data
                assert "mitigation_strategies" in result_data
        
        # Verify user isolation in WebSocket streams
        for user_id, _, _ in authenticated_users:
            user_events = websocket_stream.get_user_stream(user_id)
            assert len(user_events) >= 2  # executing + completed
            
            # Verify all events belong to this user
            for event in user_events:
                assert event["user_id"] == user_id
        
        # Verify stream metrics for production monitoring
        stream_metrics = websocket_stream.get_stream_metrics()
        assert stream_metrics["total_events"] >= 6  # 3 users * 2 events each
        assert stream_metrics["active_users"] == 3
        assert stream_metrics["completed_executions"] == 3
        assert stream_metrics["average_execution_time"] is not None
        assert stream_metrics["average_execution_time"] > 0