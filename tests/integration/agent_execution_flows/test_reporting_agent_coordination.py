"""
Test Reporting Agent Coordination Integration

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (Focus on Mid/Enterprise for comprehensive reports)
- Business Goal: Ensure reporting agent delivers actionable, well-formatted business insights
- Value Impact: Translates technical analysis into executive-ready business communications
- Strategic Impact: Enables customer success by providing clear, actionable reports that drive decision-making

Tests the reporting agent's coordination with other agents for generating
executive summaries, technical reports, and actionable recommendations.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)


class TestReportingAgentCoordination(BaseIntegrationTest):
    """Integration tests for reporting agent coordination."""

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_reporting_agent_data_synthesis_coordination(self, real_services_fixture):
        """Test reporting agent coordination for synthesizing data from multiple sources."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="executive_user_800",
            thread_id="thread_1100", 
            session_id="session_1400",
            workspace_id="executive_workspace_700"
        )
        
        # Mock input data from multiple agents
        multi_source_data = {
            "data_helper_results": {
                "cost_data": {"total_monthly": 25000, "trend": "increasing"},
                "usage_metrics": {"cpu_avg": 65, "memory_avg": 78},
                "collection_timestamp": "2024-01-15T10:00:00Z"
            },
            "triage_results": {
                "priority_issues": ["high_cost_growth", "resource_waste"],
                "urgency_level": "high",
                "business_impact": "significant"
            },
            "optimization_results": {
                "identified_savings": 8500,
                "recommendations": [
                    {"type": "rightsizing", "impact": "high", "savings": 5000},
                    {"type": "reserved_instances", "impact": "medium", "savings": 3500}
                ],
                "implementation_timeline": "2-6 weeks"
            }
        }
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "synthesized_report": {
                "executive_summary": {
                    "key_findings": [
                        "Monthly cloud costs of $25,000 showing upward trend",
                        "Identified $8,500 monthly cost reduction opportunity (34% savings)",
                        "Implementation can begin immediately with high-impact rightsizing"
                    ],
                    "business_impact": {
                        "current_annual_cost": 300000,
                        "potential_annual_savings": 102000,
                        "roi_percentage": 34
                    },
                    "recommendations": [
                        "Immediate action: Implement EC2 rightsizing for $5,000 monthly savings",
                        "Strategic planning: Reserved instance strategy for additional $3,500 savings"
                    ]
                },
                "technical_details": {
                    "cost_breakdown": multi_source_data["data_helper_results"]["cost_data"],
                    "optimization_details": multi_source_data["optimization_results"]["recommendations"]
                },
                "synthesis_quality": "high",
                "data_sources_integrated": 3
            }
        })
        
        reporting_agent = ReportingSubAgent(
            user_context=user_context,
            llm_client=mock_llm
        )
        
        # Act - Execute data synthesis
        result = await reporting_agent.execute_multi_source_synthesis(
            input_data=multi_source_data,
            report_type="executive_summary",
            synthesis_mode="comprehensive"
        )
        
        # Assert - Verify data synthesis coordination
        assert result is not None
        assert result.status == "success"
        
        synthesized = result.result["synthesized_report"]
        assert synthesized["data_sources_integrated"] == 3
        assert synthesized["synthesis_quality"] == "high"
        
        # Verify executive summary contains business value
        exec_summary = synthesized["executive_summary"]
        assert "roi_percentage" in exec_summary["business_impact"]
        assert exec_summary["business_impact"]["roi_percentage"] > 30
        assert len(exec_summary["key_findings"]) >= 3

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_reporting_agent_audience_customization_coordination(self, real_services_fixture):
        """Test reporting agent coordination for different audience-specific reports."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="multi_audience_user_801",
            thread_id="thread_1101",
            session_id="session_1401", 
            workspace_id="multi_audience_workspace_701"
        )
        
        base_analysis_data = {
            "cost_analysis": {"total_savings": 12000, "complexity": "medium"},
            "technical_details": {"instances": 75, "storage": "200TB", "networks": 15},
            "timeline": {"implementation": "8 weeks", "roi_realization": "12 weeks"}
        }
        
        # Mock audience-specific coordinators
        mock_exec_coordinator = AsyncMock()
        mock_exec_coordinator.format_for_executives = AsyncMock(return_value={
            "executive_format": {
                "headline": "34% Cost Reduction Opportunity Identified",
                "business_impact": "$144,000 annual savings with 12-week ROI",
                "action_required": "Approve optimization initiative",
                "risk_level": "Low"
            }
        })
        
        mock_tech_coordinator = AsyncMock() 
        mock_tech_coordinator.format_for_technical = AsyncMock(return_value={
            "technical_format": {
                "implementation_steps": ["EC2 analysis", "Instance rightsizing", "Reserved instance planning"],
                "resource_requirements": {"engineer_hours": 40, "testing_time": "2 weeks"},
                "technical_risks": ["Service disruption during migration"],
                "monitoring_requirements": ["CloudWatch dashboards", "Cost alerts"]
            }
        })
        
        mock_llm = AsyncMock()
        audience_responses = {
            "executive": {
                "status": "success",
                "executive_report": "High-level business impact summary with clear ROI",
                "format": "executive_dashboard"
            },
            "technical": {
                "status": "success", 
                "technical_report": "Detailed implementation guide with technical specifications",
                "format": "technical_documentation"
            }
        }
        
        def audience_specific_response(*args, **kwargs):
            # Determine audience from context
            context_str = str(kwargs).lower()
            if "executive" in context_str:
                return audience_responses["executive"]
            else:
                return audience_responses["technical"]
        
        mock_llm.generate_response = AsyncMock(side_effect=audience_specific_response)
        
        reporting_agent = ReportingSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            executive_coordinator=mock_exec_coordinator,
            technical_coordinator=mock_tech_coordinator
        )
        
        # Act - Generate reports for different audiences
        executive_result = await reporting_agent.execute_audience_specific_report(
            analysis_data=base_analysis_data,
            target_audience="executive",
            format_requirements="high_level_summary"
        )
        
        technical_result = await reporting_agent.execute_audience_specific_report(
            analysis_data=base_analysis_data,
            target_audience="technical",
            format_requirements="detailed_implementation"
        )
        
        # Assert - Verify audience-specific coordination
        assert executive_result is not None
        assert executive_result.status == "success"
        assert executive_result.result["format"] == "executive_dashboard"
        
        assert technical_result is not None
        assert technical_result.status == "success"
        assert technical_result.result["format"] == "technical_documentation"
        
        # Verify coordinators were called
        mock_exec_coordinator.format_for_executives.assert_called()
        mock_tech_coordinator.format_for_technical.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_reporting_agent_visualization_coordination(self, real_services_fixture):
        """Test reporting agent coordination with visualization components."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="visual_user_802",
            thread_id="thread_1102",
            session_id="session_1402",
            workspace_id="visual_workspace_702"
        )
        
        # Mock visualization coordinator
        mock_viz_coordinator = AsyncMock()
        mock_viz_coordinator.generate_cost_charts = AsyncMock(return_value={
            "charts": [
                {"type": "line_chart", "title": "Monthly Cost Trend", "data_points": 12},
                {"type": "pie_chart", "title": "Cost by Service", "segments": 8},
                {"type": "bar_chart", "title": "Savings Opportunities", "categories": 5}
            ],
            "chart_urls": [
                "https://charts.api/cost_trend_chart_123.png",
                "https://charts.api/service_breakdown_456.png", 
                "https://charts.api/savings_opportunities_789.png"
            ]
        })
        
        report_data = {
            "cost_trends": {"monthly_data": [20000, 22000, 25000, 28000]},
            "service_breakdown": {"ec2": 15000, "rds": 8000, "s3": 5000},
            "savings_opportunities": {"rightsizing": 6000, "reserved": 4000, "storage": 2000}
        }
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "visual_report": {
                "narrative": "Cost analysis reveals 28% month-over-month growth with significant optimization potential",
                "chart_integration": {
                    "trend_chart_embedded": True,
                    "breakdown_chart_embedded": True,
                    "opportunities_chart_embedded": True
                },
                "visual_storytelling": {
                    "opening": "Cost trajectory analysis",
                    "problem": "Unsustainable growth pattern identified",
                    "solution": "Multi-faceted optimization approach",
                    "outcome": "34% cost reduction achievable"
                },
                "visualization_quality": "high"
            }
        })
        
        reporting_agent = ReportingSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            visualization_coordinator=mock_viz_coordinator
        )
        
        # Act - Generate visual report
        result = await reporting_agent.execute_visual_report_generation(
            report_data=report_data,
            visualization_requirements=["cost_trends", "service_breakdown", "savings_opportunities"],
            visual_style="executive_dashboard"
        )
        
        # Assert - Verify visualization coordination
        assert result is not None
        assert result.status == "success"
        
        visual_report = result.result["visual_report"]
        assert visual_report["visualization_quality"] == "high"
        
        chart_integration = visual_report["chart_integration"]
        assert chart_integration["trend_chart_embedded"] is True
        assert chart_integration["breakdown_chart_embedded"] is True
        
        # Verify visualization coordinator was used
        mock_viz_coordinator.generate_cost_charts.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_reporting_agent_delivery_coordination(self, real_services_fixture):
        """Test reporting agent coordination with delivery systems."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="delivery_user_803",
            thread_id="thread_1103", 
            session_id="session_1403",
            workspace_id="delivery_workspace_703"
        )
        
        # Mock delivery coordinators
        mock_email_coordinator = AsyncMock()
        mock_email_coordinator.send_report_email = AsyncMock(return_value={
            "delivery_status": "sent",
            "email_id": "email_456",
            "recipients": ["ceo@company.com", "cto@company.com"],
            "delivery_time": "2024-01-15T11:30:00Z"
        })
        
        mock_dashboard_coordinator = AsyncMock()
        mock_dashboard_coordinator.publish_to_dashboard = AsyncMock(return_value={
            "dashboard_url": "https://netra.app/dashboard/report_789",
            "publish_status": "live",
            "access_permissions": ["executive", "finance"]
        })
        
        mock_pdf_coordinator = AsyncMock()
        mock_pdf_coordinator.generate_pdf_report = AsyncMock(return_value={
            "pdf_url": "https://storage.netra.app/reports/cost_analysis_202401.pdf",
            "file_size": "2.4MB",
            "page_count": 12
        })
        
        report_content = {
            "title": "Q4 2024 Cloud Cost Optimization Analysis",
            "executive_summary": "Comprehensive analysis identifying $144k annual savings",
            "detailed_findings": "Full technical analysis and recommendations",
            "appendices": "Supporting data and methodology"
        }
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "delivery_coordination": {
                "email_prepared": True,
                "dashboard_formatted": True,
                "pdf_generated": True,
                "multi_channel_delivery": True
            },
            "delivery_summary": {
                "channels_used": 3,
                "primary_recipients": 2,
                "backup_storage": True,
                "access_tracking": True
            }
        })
        
        reporting_agent = ReportingSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            email_coordinator=mock_email_coordinator,
            dashboard_coordinator=mock_dashboard_coordinator,
            pdf_coordinator=mock_pdf_coordinator
        )
        
        # Act - Execute multi-channel delivery
        result = await reporting_agent.execute_multi_channel_delivery(
            report_content=report_content,
            delivery_channels=["email", "dashboard", "pdf"],
            recipients=["executive", "finance"],
            delivery_priority="high"
        )
        
        # Assert - Verify delivery coordination
        assert result is not None
        assert result.status == "success"
        
        delivery_coord = result.result["delivery_coordination"]
        assert delivery_coord["multi_channel_delivery"] is True
        assert delivery_coord["email_prepared"] is True
        assert delivery_coord["dashboard_formatted"] is True
        assert delivery_coord["pdf_generated"] is True
        
        # Verify all coordinators were used
        mock_email_coordinator.send_report_email.assert_called()
        mock_dashboard_coordinator.publish_to_dashboard.assert_called()
        mock_pdf_coordinator.generate_pdf_report.assert_called()

    @pytest.mark.integration
    @pytest.mark.sub_agent_coordination
    async def test_reporting_agent_follow_up_coordination(self, real_services_fixture):
        """Test reporting agent coordination with follow-up and monitoring systems."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="followup_user_804",
            thread_id="thread_1104",
            session_id="session_1404",
            workspace_id="followup_workspace_704"
        )
        
        # Mock follow-up coordinator
        mock_followup_coordinator = AsyncMock()
        mock_followup_coordinator.schedule_implementation_tracking = AsyncMock(return_value={
            "tracking_scheduled": True,
            "milestones": [
                {"milestone": "Week 2", "task": "EC2 rightsizing analysis", "owner": "DevOps"},
                {"milestone": "Week 4", "task": "Reserved instance planning", "owner": "Finance"},
                {"milestone": "Week 8", "task": "Implementation completion", "owner": "DevOps"}
            ],
            "monitoring_dashboard": "https://netra.app/tracking/implementation_456"
        })
        
        mock_followup_coordinator.create_progress_alerts = AsyncMock(return_value={
            "alerts_configured": True,
            "alert_types": ["milestone_delay", "cost_variance", "implementation_blocker"],
            "notification_channels": ["email", "slack", "dashboard"]
        })
        
        initial_report_data = {
            "recommendations": [
                {"id": "rec_001", "type": "rightsizing", "timeline": "2 weeks", "owner": "DevOps"},
                {"id": "rec_002", "type": "reserved_instances", "timeline": "4 weeks", "owner": "Finance"}
            ],
            "expected_outcomes": {
                "monthly_savings": 8500,
                "implementation_duration": "8 weeks"
            }
        }
        
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "status": "success",
            "follow_up_coordination": {
                "tracking_system_integrated": True,
                "progress_monitoring_enabled": True,
                "stakeholder_notifications_configured": True,
                "success_metrics_defined": True
            },
            "follow_up_plan": {
                "weekly_progress_reports": True,
                "milestone_check_ins": True,
                "roi_tracking": True,
                "issue_escalation": True
            }
        })
        
        reporting_agent = ReportingSubAgent(
            user_context=user_context,
            llm_client=mock_llm,
            followup_coordinator=mock_followup_coordinator
        )
        
        # Act - Execute follow-up coordination
        result = await reporting_agent.execute_follow_up_coordination(
            initial_report=initial_report_data,
            follow_up_requirements=["progress_tracking", "milestone_monitoring", "roi_measurement"],
            stakeholders=["executive", "finance", "devops"]
        )
        
        # Assert - Verify follow-up coordination
        assert result is not None
        assert result.status == "success"
        
        followup_coord = result.result["follow_up_coordination"]
        assert followup_coord["tracking_system_integrated"] is True
        assert followup_coord["progress_monitoring_enabled"] is True
        assert followup_coord["stakeholder_notifications_configured"] is True
        
        followup_plan = result.result["follow_up_plan"]
        assert followup_plan["weekly_progress_reports"] is True
        assert followup_plan["roi_tracking"] is True
        
        # Verify follow-up coordinator was used
        mock_followup_coordinator.schedule_implementation_tracking.assert_called()
        mock_followup_coordinator.create_progress_alerts.assert_called()