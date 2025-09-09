"""Integration tests for real tool execution dispatching workflows.

These tests validate complete tool execution workflows using real components,
ensuring the tool dispatcher, execution engine, registry, and WebSocket systems
work together correctly for business-critical tool operations.

Business Value: Platform/Internal - System Integration
Validates that all tool execution components integrate correctly for reliable operation.

Test Coverage:
- Complete tool dispatch workflow with real tool registry
- Tool execution engine integration with dispatcher
- WebSocket notification integration throughout workflow
- Tool factory patterns with real user context
- Multi-tool workflow orchestration
- Real service integration without mocks
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    create_request_scoped_dispatcher,
)
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications,
)
from netra_backend.app.core.registry.universal_registry import UniversalRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.unified_tool_registry.models import ToolExecutionResult
from langchain_core.tools import BaseTool


class RealBusinessAnalyticsTool(BaseTool):
    """Real business analytics tool that simulates complex business operations."""
    
    name = "business_analytics"
    description = "Comprehensive business analytics and KPI analysis"
    
    def __init__(self, analytics_config: Dict[str, Any] = None):
        super().__init__()
        self.analytics_config = analytics_config or {
            "supported_metrics": ["revenue", "customer_acquisition", "churn", "ltv"],
            "data_sources": ["crm", "finance", "marketing"],
            "analysis_depth": "comprehensive"
        }
        self.execution_count = 0
        self.analysis_cache = {}
        
    def _run(self, query: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(query, **kwargs))
        
    async def _arun(self, query: str, **kwargs) -> str:
        """Advanced asynchronous business analytics execution."""
        self.execution_count += 1
        context = kwargs.get('context')
        
        # Multi-phase analytics processing
        analysis_phases = [
            "data_extraction",
            "metric_calculation", 
            "trend_analysis",
            "insight_generation",
            "recommendation_synthesis"
        ]
        
        phase_results = {}
        
        for phase in analysis_phases:
            await asyncio.sleep(0.01)  # Simulate processing time
            
            if phase == "data_extraction":
                phase_results[phase] = {
                    "sources_accessed": self.analytics_config["data_sources"],
                    "records_processed": 15000 + (self.execution_count * 1000),
                    "data_quality_score": 0.94
                }
            elif phase == "metric_calculation":
                phase_results[phase] = {
                    "metrics_calculated": self.analytics_config["supported_metrics"],
                    "calculation_time_ms": 45.2,
                    "accuracy_confidence": 0.97
                }
            elif phase == "trend_analysis":
                phase_results[phase] = {
                    "trends_detected": ["growth", "seasonal_variation", "market_shift"],
                    "correlation_strength": 0.83,
                    "forecast_horizon_months": 6
                }
            elif phase == "insight_generation":
                phase_results[phase] = {
                    "insights_generated": 12,
                    "priority_insights": 4,
                    "actionable_recommendations": 8
                }
            else:  # recommendation_synthesis
                phase_results[phase] = {
                    "recommendations": [
                        "Optimize customer acquisition in Q2",
                        "Focus retention efforts on high-value segments",
                        "Expand marketing in emerging channels"
                    ],
                    "impact_score": 8.7,
                    "implementation_complexity": "medium"
                }
                
        # Generate comprehensive result
        analytics_result = {
            "query": query,
            "execution_id": self.execution_count,
            "user_id": context.user_id if context else "unknown",
            "phases_completed": phase_results,
            "summary": {
                "total_phases": len(analysis_phases),
                "processing_time_ms": len(analysis_phases) * 10,
                "data_quality": "high",
                "confidence_score": 0.91,
                "business_impact": "significant"
            },
            "metadata": {
                "tool_version": "2.1.0",
                "analysis_depth": self.analytics_config["analysis_depth"],
                "timestamp": time.time(),
                "cache_key": f"analytics_{hash(query)}_{self.execution_count}"
            }
        }
        
        # Store in cache for potential reuse
        cache_key = analytics_result["metadata"]["cache_key"]
        self.analysis_cache[cache_key] = analytics_result
        
        return json.dumps(analytics_result)


class RealDataVisualizationTool(BaseTool):
    """Real data visualization tool for creating business charts and dashboards."""
    
    name = "data_visualization"
    description = "Advanced data visualization and dashboard creation"
    
    def __init__(self, viz_config: Dict[str, Any] = None):
        super().__init__()
        self.viz_config = viz_config or {
            "chart_types": ["bar", "line", "scatter", "heatmap", "treemap"],
            "output_formats": ["svg", "png", "interactive"],
            "styling_themes": ["corporate", "modern", "minimal"]
        }
        self.execution_count = 0
        self.dashboard_cache = {}
        
    def _run(self, data_source: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(data_source, **kwargs))
        
    async def _arun(self, data_source: str, **kwargs) -> str:
        """Advanced asynchronous data visualization creation."""
        self.execution_count += 1
        context = kwargs.get('context')
        viz_type = kwargs.get('visualization_type', 'dashboard')
        
        # Multi-step visualization process
        viz_steps = [
            "data_analysis",
            "chart_selection", 
            "layout_design",
            "styling_application",
            "interactivity_setup",
            "export_generation"
        ]
        
        step_results = {}
        
        for step in viz_steps:
            await asyncio.sleep(0.008)  # Simulate processing time
            
            if step == "data_analysis":
                step_results[step] = {
                    "data_source": data_source,
                    "data_points": 8500 + (self.execution_count * 500),
                    "dimensions": 12,
                    "data_completeness": 0.96
                }
            elif step == "chart_selection":
                step_results[step] = {
                    "recommended_charts": self.viz_config["chart_types"][:3],
                    "primary_chart": "interactive_dashboard",
                    "chart_complexity": "advanced"
                }
            elif step == "layout_design":
                step_results[step] = {
                    "layout_type": "grid_responsive",
                    "sections": 6,
                    "responsive_breakpoints": ["mobile", "tablet", "desktop"]
                }
            elif step == "styling_application":
                step_results[step] = {
                    "theme_applied": self.viz_config["styling_themes"][0],
                    "color_palette": "business_professional",
                    "font_optimization": True
                }
            elif step == "interactivity_setup":
                step_results[step] = {
                    "interactive_elements": ["filters", "drill_down", "hover_details"],
                    "real_time_updates": True,
                    "export_options": True
                }
            else:  # export_generation
                step_results[step] = {
                    "formats_generated": self.viz_config["output_formats"],
                    "file_sizes_kb": {"svg": 245, "png": 1200, "interactive": 850},
                    "quality_score": 0.94
                }
                
        # Generate comprehensive visualization result
        viz_result = {
            "data_source": data_source,
            "visualization_type": viz_type,
            "execution_id": self.execution_count,
            "user_id": context.user_id if context else "unknown",
            "steps_completed": step_results,
            "dashboard": {
                "title": f"Business Dashboard - {data_source}",
                "charts_count": len(self.viz_config["chart_types"]),
                "interactivity_level": "high",
                "mobile_optimized": True,
                "load_time_ms": 245
            },
            "output": {
                "primary_format": "interactive",
                "file_paths": {
                    "dashboard": f"/dashboards/business_{self.execution_count}.html",
                    "charts": f"/charts/set_{self.execution_count}/",
                    "exports": f"/exports/dashboard_{self.execution_count}/"
                },
                "sharing_enabled": True
            },
            "metadata": {
                "tool_version": "3.2.1",
                "processing_time_ms": len(viz_steps) * 8,
                "cache_enabled": True,
                "timestamp": time.time()
            }
        }
        
        # Store in dashboard cache
        cache_key = f"dashboard_{data_source}_{self.execution_count}"
        self.dashboard_cache[cache_key] = viz_result
        
        return json.dumps(viz_result)


class RealReportGeneratorTool(BaseTool):
    """Real report generator that creates comprehensive business reports."""
    
    name = "report_generator"
    description = "Comprehensive business report generation and formatting"
    
    def __init__(self, report_config: Dict[str, Any] = None):
        super().__init__()
        self.report_config = report_config or {
            "report_types": ["executive_summary", "detailed_analysis", "dashboard_report"],
            "output_formats": ["pdf", "docx", "html"],
            "templates": ["corporate", "executive", "technical"]
        }
        self.execution_count = 0
        self.reports_generated = {}
        
    def _run(self, report_spec: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(report_spec, **kwargs))
        
    async def _arun(self, report_spec: str, **kwargs) -> str:
        """Advanced asynchronous report generation."""
        self.execution_count += 1
        context = kwargs.get('context')
        
        # Multi-phase report generation
        generation_phases = [
            "content_analysis",
            "template_selection",
            "data_integration",
            "narrative_generation",
            "visualization_embedding",
            "formatting_optimization",
            "quality_review"
        ]
        
        phase_outputs = {}
        
        for phase in generation_phases:
            await asyncio.sleep(0.012)  # Simulate processing time
            
            if phase == "content_analysis":
                phase_outputs[phase] = {
                    "report_spec": report_spec,
                    "sections_identified": 8,
                    "data_requirements": ["analytics", "visualizations", "metrics"],
                    "estimated_length_pages": 15
                }
            elif phase == "template_selection":
                phase_outputs[phase] = {
                    "selected_template": self.report_config["templates"][0],
                    "customizations_applied": 12,
                    "branding_elements": True
                }
            elif phase == "data_integration":
                phase_outputs[phase] = {
                    "data_sources_integrated": 4,
                    "metrics_included": 25,
                    "charts_embedded": 8,
                    "data_freshness_hours": 2
                }
            elif phase == "narrative_generation":
                phase_outputs[phase] = {
                    "executive_summary": "Generated comprehensive business insights...",
                    "key_findings": 6,
                    "recommendations": 4,
                    "narrative_quality_score": 0.89
                }
            elif phase == "visualization_embedding":
                phase_outputs[phase] = {
                    "charts_embedded": 8,
                    "tables_included": 5,
                    "interactive_elements": 3,
                    "visual_appeal_score": 0.93
                }
            elif phase == "formatting_optimization":
                phase_outputs[phase] = {
                    "layout_optimized": True,
                    "responsive_design": True,
                    "accessibility_compliant": True,
                    "print_optimized": True
                }
            else:  # quality_review
                phase_outputs[phase] = {
                    "grammar_check": "passed",
                    "data_accuracy": "validated",
                    "formatting_consistency": "approved",
                    "overall_quality_score": 0.96
                }
                
        # Generate final report result
        report_result = {
            "report_specification": report_spec,
            "execution_id": self.execution_count,
            "user_id": context.user_id if context else "unknown",
            "generation_phases": phase_outputs,
            "report_details": {
                "title": f"Business Report - {report_spec}",
                "pages": 15,
                "sections": 8,
                "charts": 8,
                "tables": 5,
                "executive_summary_words": 450,
                "total_words": 7500
            },
            "output_files": {
                "pdf": f"/reports/business_report_{self.execution_count}.pdf",
                "docx": f"/reports/business_report_{self.execution_count}.docx", 
                "html": f"/reports/business_report_{self.execution_count}.html"
            },
            "delivery": {
                "generation_time_ms": len(generation_phases) * 12,
                "file_sizes_mb": {"pdf": 5.2, "docx": 3.8, "html": 2.1},
                "ready_for_distribution": True
            },
            "metadata": {
                "tool_version": "4.1.0",
                "template_used": self.report_config["templates"][0],
                "quality_assurance": "completed",
                "timestamp": time.time()
            }
        }
        
        # Store generated report
        report_key = f"report_{self.execution_count}_{int(time.time())}"
        self.reports_generated[report_key] = report_result
        
        return json.dumps(report_result)


class IntegratedWorkflowWebSocketManager:
    """WebSocket manager that tracks complete workflow events."""
    
    def __init__(self):
        self.workflow_events = []
        self.user_workflows = {}
        self.tool_executions = {}
        self.workflow_completions = {}
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send event and track workflow progress."""
        event_record = {
            "event_type": event_type,
            "data": data.copy(),
            "timestamp": time.time(),
            "event_id": str(uuid.uuid4())
        }
        
        self.workflow_events.append(event_record)
        
        # Track user workflows
        user_id = data.get("user_id")
        if user_id:
            if user_id not in self.user_workflows:
                self.user_workflows[user_id] = []
            self.user_workflows[user_id].append(event_record)
            
        # Track tool executions
        tool_name = data.get("tool_name")
        if tool_name:
            if tool_name not in self.tool_executions:
                self.tool_executions[tool_name] = []
            self.tool_executions[tool_name].append(event_record)
            
        return True
        
    def get_workflow_summary(self, user_id: str) -> Dict[str, Any]:
        """Get workflow summary for user."""
        user_events = self.user_workflows.get(user_id, [])
        
        tool_executions = {}
        for event in user_events:
            tool_name = event["data"].get("tool_name")
            if tool_name:
                if tool_name not in tool_executions:
                    tool_executions[tool_name] = {"executing": 0, "completed": 0}
                    
                if event["event_type"] == "tool_executing":
                    tool_executions[tool_name]["executing"] += 1
                elif event["event_type"] == "tool_completed":
                    tool_executions[tool_name]["completed"] += 1
                    
        return {
            "user_id": user_id,
            "total_events": len(user_events),
            "tool_executions": tool_executions,
            "workflow_complete": self._is_workflow_complete(tool_executions)
        }
        
    def _is_workflow_complete(self, tool_executions: Dict[str, Dict[str, int]]) -> bool:
        """Check if workflow is complete."""
        for tool_data in tool_executions.values():
            if tool_data["executing"] != tool_data["completed"]:
                return False
        return len(tool_executions) > 0


class TestRealToolExecutionDispatchingWorkflows(SSotAsyncTestCase):
    """Integration tests for real tool execution dispatching workflows."""
    
    def setUp(self):
        """Set up real workflow test environment."""
        super().setUp()
        
        # Create user contexts
        self.primary_user_context = UserExecutionContext(
            user_id="workflow_user_001",
            run_id=f"workflow_run_{int(time.time() * 1000)}",
            thread_id="workflow_thread_001",
            session_id="workflow_session_001",
            metadata={"plan_tier": "enterprise", "roles": ["user", "analyst"]}
        )
        
        self.secondary_user_context = UserExecutionContext(
            user_id="workflow_user_002",
            run_id=f"workflow_run_{int(time.time() * 1000) + 1}",
            thread_id="workflow_thread_002",
            session_id="workflow_session_002",
            metadata={"plan_tier": "mid", "roles": ["user"]}
        )
        
        # Create WebSocket manager for workflow tracking
        self.websocket_manager = IntegratedWorkflowWebSocketManager()
        
        # Create real business tools
        self.analytics_tool = RealBusinessAnalyticsTool({
            "supported_metrics": ["revenue", "growth", "efficiency", "satisfaction"],
            "data_sources": ["crm", "finance", "operations", "marketing"],
            "analysis_depth": "enterprise"
        })
        
        self.visualization_tool = RealDataVisualizationTool({
            "chart_types": ["executive_dashboard", "detailed_charts", "interactive_reports"],
            "output_formats": ["interactive", "pdf", "svg"],
            "styling_themes": ["corporate", "executive"]
        })
        
        self.report_tool = RealReportGeneratorTool({
            "report_types": ["executive_summary", "detailed_analysis", "board_presentation"],
            "output_formats": ["pdf", "pptx", "html"],
            "templates": ["executive", "board", "technical"]
        })
        
        # Create real tool registry
        self.tool_registry = UniversalRegistry[BaseTool]("WorkflowToolRegistry")
        self.tool_registry.register("analytics", self.analytics_tool, 
                                   tags=["business", "analytics", "enterprise"])
        self.tool_registry.register("visualization", self.visualization_tool,
                                   tags=["visualization", "dashboard", "reporting"])
        self.tool_registry.register("reporting", self.report_tool,
                                   tags=["reporting", "documents", "executive"])
        
    async def tearDown(self):
        """Clean up workflow test environment."""
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.primary_user_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.secondary_user_context.user_id)
        
        await super().tearDown()
        
    # ===================== COMPLETE WORKFLOW INTEGRATION TESTS =====================
        
    async def test_complete_business_intelligence_workflow(self):
        """Test complete business intelligence workflow with real tools."""
        # Create dispatcher with real tools and WebSocket integration
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.primary_user_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool, self.visualization_tool, self.report_tool]
        )
        
        # Phase 1: Business Analytics
        analytics_result = await dispatcher.execute_tool(
            "business_analytics",
            {
                "query": "Q4 business performance analysis",
                "metrics": ["revenue", "growth", "efficiency"],
                "depth": "comprehensive"
            }
        )
        
        self.assertTrue(analytics_result.success)
        analytics_data = json.loads(analytics_result.result)
        self.assertIn("phases_completed", analytics_data)
        self.assertEqual(len(analytics_data["phases_completed"]), 5)
        
        # Phase 2: Data Visualization (using analytics results)
        visualization_result = await dispatcher.execute_tool(
            "data_visualization",
            {
                "data_source": "Q4_analytics_results",
                "visualization_type": "executive_dashboard",
                "interactive": True
            }
        )
        
        self.assertTrue(visualization_result.success)
        viz_data = json.loads(visualization_result.result)
        self.assertIn("dashboard", viz_data)
        self.assertIn("charts_count", viz_data["dashboard"])
        
        # Phase 3: Report Generation (using both analytics and visualization)
        report_result = await dispatcher.execute_tool(
            "report_generator",
            {
                "report_spec": "Q4 Executive Business Review",
                "include_analytics": True,
                "include_visualizations": True,
                "format": "executive"
            }
        )
        
        self.assertTrue(report_result.success)
        report_data = json.loads(report_result.result)
        self.assertIn("report_details", report_data)
        self.assertGreater(report_data["report_details"]["pages"], 10)
        
        # Verify complete workflow in WebSocket events
        workflow_summary = self.websocket_manager.get_workflow_summary(self.primary_user_context.user_id)
        
        self.assertTrue(workflow_summary["workflow_complete"])
        self.assertEqual(len(workflow_summary["tool_executions"]), 3)
        
        # Verify each tool completed successfully
        for tool_name, execution_data in workflow_summary["tool_executions"].items():
            self.assertEqual(
                execution_data["executing"],
                execution_data["completed"],
                f"Tool {tool_name} should have equal executing and completed events"
            )
            
        await dispatcher.cleanup()
        
    async def test_tool_registry_integration_with_dispatcher(self):
        """Test integration between tool registry and dispatcher."""
        # Create dispatcher factory with tool registry
        factory = UnifiedToolDispatcherFactory()
        factory.set_tool_registry(self.tool_registry)
        
        dispatcher = await factory.create_dispatcher(
            user_context=self.primary_user_context,
            websocket_manager=self.websocket_manager
        )
        
        # Verify tools from registry are available
        available_tools = dispatcher.get_available_tools()
        
        # Should have tools from registry
        expected_tools = ["analytics", "visualization", "reporting"]
        for expected_tool in expected_tools:
            self.assertIn(expected_tool, available_tools)
            self.assertTrue(dispatcher.has_tool(expected_tool))
            
        # Execute tools from registry
        for tool_name in expected_tools:
            if tool_name == "analytics":
                result = await dispatcher.execute_tool(tool_name, {"query": "registry_test_analytics"})
            elif tool_name == "visualization":
                result = await dispatcher.execute_tool(tool_name, {"data_source": "registry_test_data"})
            else:  # reporting
                result = await dispatcher.execute_tool(tool_name, {"report_spec": "registry_test_report"})
                
            self.assertTrue(result.success, f"Tool {tool_name} execution should succeed")
            
        await factory.cleanup_all_dispatchers()
        
    async def test_enhanced_tool_execution_engine_integration(self):
        """Test integration with enhanced tool execution engine."""
        # Create execution engine with WebSocket integration
        execution_engine = UnifiedToolExecutionEngine(
            websocket_bridge=self.websocket_manager
        )
        
        # Create dispatcher and enhance it
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.primary_user_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool]
        )
        
        enhanced_dispatcher = await enhance_tool_dispatcher_with_notifications(
            tool_dispatcher=dispatcher,
            websocket_manager=self.websocket_manager,
            enable_notifications=True
        )
        
        self.assertTrue(enhanced_dispatcher._websocket_enhanced)
        
        # Execute tool through enhanced dispatcher
        result = await enhanced_dispatcher.execute_tool(
            "business_analytics",
            {"query": "enhanced_execution_test", "depth": "standard"}
        )
        
        self.assertTrue(result.success)
        
        # Verify enhanced execution generated proper events
        workflow_summary = self.websocket_manager.get_workflow_summary(self.primary_user_context.user_id)
        self.assertGreater(workflow_summary["total_events"], 0)
        
        await dispatcher.cleanup()
        
    async def test_concurrent_multi_tool_workflow_execution(self):
        """Test concurrent execution of multi-tool workflows."""
        # Create dispatchers for different users
        primary_dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.primary_user_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool, self.visualization_tool, self.report_tool]
        )
        
        secondary_dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.secondary_user_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool, self.visualization_tool]
        )
        
        # Execute concurrent workflows
        primary_tasks = [
            primary_dispatcher.execute_tool("business_analytics", {"query": "primary_analytics"}),
            primary_dispatcher.execute_tool("data_visualization", {"data_source": "primary_data"}),
            primary_dispatcher.execute_tool("report_generator", {"report_spec": "primary_report"})
        ]
        
        secondary_tasks = [
            secondary_dispatcher.execute_tool("business_analytics", {"query": "secondary_analytics"}),
            secondary_dispatcher.execute_tool("data_visualization", {"data_source": "secondary_data"})
        ]
        
        # Execute all tasks concurrently
        all_results = await asyncio.gather(
            *primary_tasks, *secondary_tasks,
            return_exceptions=True
        )
        
        # Verify all executions succeeded
        for i, result in enumerate(all_results):
            self.assertNotIsInstance(result, Exception, f"Task {i} should not raise exception")
            self.assertTrue(result.success, f"Task {i} should succeed")
            
        # Verify workflow isolation
        primary_summary = self.websocket_manager.get_workflow_summary(self.primary_user_context.user_id)
        secondary_summary = self.websocket_manager.get_workflow_summary(self.secondary_user_context.user_id)
        
        self.assertEqual(len(primary_summary["tool_executions"]), 3)
        self.assertEqual(len(secondary_summary["tool_executions"]), 2)
        
        # Verify both workflows completed
        self.assertTrue(primary_summary["workflow_complete"])
        self.assertTrue(secondary_summary["workflow_complete"])
        
        await primary_dispatcher.cleanup()
        await secondary_dispatcher.cleanup()
        
    # ===================== TOOL FACTORY AND CONTEXT INTEGRATION =====================
        
    async def test_tool_factory_patterns_with_user_context(self):
        """Test tool factory patterns with proper user context propagation."""
        # Create factory function for user-specific tool
        def create_user_analytics_tool(user_context: UserExecutionContext) -> RealBusinessAnalyticsTool:
            # Configure tool based on user context
            user_config = {
                "supported_metrics": ["revenue", "growth"] if user_context.metadata.get("plan_tier") == "mid" 
                                   else ["revenue", "growth", "efficiency", "satisfaction", "predictive"],
                "data_sources": ["basic"] if user_context.metadata.get("plan_tier") == "mid"
                               else ["crm", "finance", "operations", "marketing", "external"],
                "analysis_depth": user_context.metadata.get("plan_tier", "basic")
            }
            
            tool = RealBusinessAnalyticsTool(user_config)
            return tool
            
        # Register factory
        self.tool_registry.register_factory("user_analytics", create_user_analytics_tool)
        
        # Create dispatcher with factory
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.primary_user_context,
            websocket_bridge=self.websocket_manager
        )
        
        await dispatcher._populate_tools_from_registry(self.tool_registry)
        
        # Create user-specific tool instance
        user_tool = self.tool_registry.create_instance("user_analytics", self.primary_user_context)
        self.assertIsNotNone(user_tool)
        
        # Verify user-specific configuration
        self.assertEqual(user_tool.analytics_config["analysis_depth"], "enterprise")
        self.assertIn("predictive", user_tool.analytics_config["supported_metrics"])
        
        # Test with different user (mid tier)
        mid_tier_tool = self.tool_registry.create_instance("user_analytics", self.secondary_user_context)
        self.assertEqual(mid_tier_tool.analytics_config["analysis_depth"], "mid")
        self.assertNotIn("predictive", mid_tier_tool.analytics_config["supported_metrics"])
        
        await dispatcher.cleanup()
        
    async def test_request_scoped_dispatcher_context_manager(self):
        """Test request-scoped dispatcher with context manager pattern."""
        workflow_results = []
        
        # Use context manager for automatic cleanup
        async with create_request_scoped_dispatcher(
            user_context=self.primary_user_context,
            websocket_manager=self.websocket_manager,
            tools=[self.analytics_tool, self.report_tool]
        ) as dispatcher:
            
            # Execute workflow within scope
            analytics_result = await dispatcher.execute_tool(
                "business_analytics",
                {"query": "scoped_analytics_test"}
            )
            
            workflow_results.append(analytics_result)
            
            report_result = await dispatcher.execute_tool(
                "report_generator", 
                {"report_spec": "scoped_report_test"}
            )
            
            workflow_results.append(report_result)
            
            # Verify dispatcher is active within scope
            self.assertTrue(dispatcher._is_active)
            
        # Verify automatic cleanup occurred
        self.assertFalse(dispatcher._is_active)
        
        # Verify results are still valid
        for result in workflow_results:
            self.assertTrue(result.success)
            
    # ===================== ERROR HANDLING AND RESILIENCE =====================
            
    async def test_workflow_resilience_with_tool_failures(self):
        """Test workflow resilience when individual tools fail."""
        # Create a tool that will fail
        class FailingTool(BaseTool):
            name = "failing_tool"
            description = "Tool that always fails"
            
            def _run(self, **kwargs):
                return asyncio.run(self._arun(**kwargs))
                
            async def _arun(self, **kwargs):
                raise RuntimeError("Simulated tool failure")
                
        failing_tool = FailingTool()
        
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.primary_user_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool, failing_tool, self.report_tool]
        )
        
        # Execute workflow with mixed success/failure
        results = []
        
        # This should succeed
        analytics_result = await dispatcher.execute_tool(
            "business_analytics",
            {"query": "resilience_test"}
        )
        results.append(("analytics", analytics_result))
        
        # This should fail
        failing_result = await dispatcher.execute_tool("failing_tool", {})
        results.append(("failing", failing_result))
        
        # This should succeed despite previous failure
        report_result = await dispatcher.execute_tool(
            "report_generator",
            {"report_spec": "resilience_report"}
        )
        results.append(("report", report_result))
        
        # Verify mixed results
        self.assertTrue(results[0][1].success)  # Analytics succeeded
        self.assertFalse(results[1][1].success)  # Failing tool failed
        self.assertTrue(results[2][1].success)   # Report succeeded despite failure
        
        # Verify workflow continued despite failure
        workflow_summary = self.websocket_manager.get_workflow_summary(self.primary_user_context.user_id)
        self.assertGreater(workflow_summary["total_events"], 4)  # Should have events for all attempts
        
        await dispatcher.cleanup()
        
    async def test_tool_execution_performance_monitoring(self):
        """Test performance monitoring during tool execution workflows."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.primary_user_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool, self.visualization_tool, self.report_tool]
        )
        
        # Execute tools and measure performance
        performance_data = []
        
        tools_to_test = [
            ("business_analytics", {"query": "performance_test_analytics"}),
            ("data_visualization", {"data_source": "performance_test_data"}),
            ("report_generator", {"report_spec": "performance_test_report"})
        ]
        
        for tool_name, params in tools_to_test:
            start_time = time.time()
            
            result = await dispatcher.execute_tool(tool_name, params)
            
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            performance_data.append({
                "tool_name": tool_name,
                "success": result.success,
                "execution_time_ms": execution_time_ms,
                "result_size": len(str(result.result)) if result.result else 0
            })
            
        # Verify performance metrics
        for perf_data in performance_data:
            self.assertTrue(perf_data["success"])
            self.assertGreater(perf_data["execution_time_ms"], 0)
            self.assertLess(perf_data["execution_time_ms"], 10000)  # Should complete within 10 seconds
            self.assertGreater(perf_data["result_size"], 100)  # Should produce substantial results
            
        # Verify dispatcher metrics
        dispatcher_metrics = dispatcher.get_metrics()
        self.assertEqual(dispatcher_metrics["tools_executed"], 3)
        self.assertEqual(dispatcher_metrics["successful_executions"], 3)
        self.assertEqual(dispatcher_metrics["failed_executions"], 0)
        self.assertGreater(dispatcher_metrics["total_execution_time_ms"], 0)
        
        await dispatcher.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])