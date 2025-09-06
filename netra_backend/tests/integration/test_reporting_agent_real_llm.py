"""Integration tests for ReportingSubAgent with REAL LLM usage.

These tests validate actual report generation and data visualization using real LLM,
real services, and actual system components - NO MOCKS.

Business Value: Ensures accurate and insightful reporting for decision-making.
"""""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Real environment configuration
env = IsolatedEnvironment()


@pytest.fixture
async def real_llm_manager():
    """Get real LLM manager instance with actual API credentials."""
    from netra_backend.app.core.config import get_settings
    settings = get_settings()
    llm_manager = LLMManager(settings)
    yield llm_manager


    @pytest.fixture
    async def real_tool_dispatcher():
        """Get real tool dispatcher with actual tools loaded."""
        dispatcher = ToolDispatcher()
        return dispatcher


    @pytest.fixture
    async def real_reporting_agent(real_llm_manager, real_tool_dispatcher):
        """Create real ReportingSubAgent instance."""
        agent = ReportingSubAgent(
        llm_manager=real_llm_manager,
        tool_dispatcher=real_tool_dispatcher,
        websocket_manager=None  # Real websocket in production
        )
        yield agent
    # Cleanup not needed for tests


        class TestReportingSubAgentRealLLM:
            """Test suite for ReportingSubAgent with real LLM interactions."""

            @pytest.mark.integration
            @pytest.mark.real_llm
            async def test_executive_summary_generation_with_insights(
            self, real_reporting_agent, db_session
            ):
                """Test 1: Generate executive summary with actionable insights using real LLM."""
        # Comprehensive data for executive reporting
                state = DeepAgentState(
                run_id="test_report_001",
                user_query="Generate an executive summary of our AI operations for Q4 2024",
                triage_result={
                "intent": "executive_reporting",
                "entities": ["Q4", "2024", "summary"],
                "confidence": 0.95
                },
                data_result={
                "quarterly_metrics": {
                "total_cost": 285000,
                "cost_trend": "+12%",
                "total_requests": 45000000,
                "avg_latency_ms": 125,
                "uptime_percentage": 99.87,
                "error_rate": 0.0013
                },
                "model_usage": {
                "gpt-4": {"requests": 15000000, "cost": 180000, "satisfaction": 0.96},
                "gpt-3.5-turbo": {"requests": 25000000, "cost": 75000, "satisfaction": 0.91},
                "claude-2": {"requests": 5000000, "cost": 30000, "satisfaction": 0.94}
                },
                "key_achievements": [
                "Reduced latency by 35% through caching",
                "Implemented multi-region deployment",
                "Achieved SOC2 compliance"
                ],
                "challenges": [
                "Cost overrun of 12% vs budget",
                "3 critical incidents in November",
                "Scaling limitations in EU region"
                ]
                }
                )

        # Execute real LLM report generation
                await real_reporting_agent.execute(state, state.run_id, stream_updates=False)

        # Get result from state
                result = state.report_result

        # Validate executive summary structure
                assert result["status"] == "success"
                assert "executive_summary" in result

                summary = result["executive_summary"]
                assert "overview" in summary
                assert "key_metrics" in summary
                assert "achievements" in summary
                assert "challenges" in summary
                assert "recommendations" in summary

        # Verify insights generation
                assert "insights" in result
                insights = result["insights"]
                assert len(insights) >= 3

                for insight in insights:
                    assert "finding" in insight
                    assert "impact" in insight
                    assert "recommendation" in insight
                    assert "priority" in insight

        # Check for data-driven conclusions
                    assert "cost_analysis" in result
                    assert "performance_trends" in result
                    assert "risk_assessment" in result

                    logger.info(f"Generated executive summary with {len(insights)} key insights")

                    @pytest.mark.integration
                    @pytest.mark.real_llm
                    async def test_comparative_analysis_report_generation(
                    self, real_reporting_agent, db_session
                    ):
                        """Test 2: Generate comparative analysis reports using real LLM."""
        # Multi-period comparison data
                        state = DeepAgentState(
                        run_id="test_report_002",
                        user_query="Compare this month's AI performance against last month and industry benchmarks",
                        triage_result={
                        "intent": "comparative_analysis",
                        "entities": ["performance", "monthly", "benchmarks"],
                        "confidence": 0.92
                        },
                        data_result={
                        "current_month": {
                        "period": "January 2024",
                        "cost_per_request": 0.0063,
                        "latency_p50": 95,
                        "latency_p99": 450,
                        "success_rate": 0.9987,
                        "throughput_rps": 1250
                        },
                        "previous_month": {
                        "period": "December 2023",
                        "cost_per_request": 0.0071,
                        "latency_p50": 110,
                        "latency_p99": 520,
                        "success_rate": 0.9975,
                        "throughput_rps": 1100
                        },
                        "industry_benchmarks": {
                        "cost_per_request": 0.0068,
                        "latency_p50": 100,
                        "latency_p99": 400,
                        "success_rate": 0.9980,
                        "throughput_rps": 1000
                        },
                        "detailed_breakdown": {
                        "api_categories": ["chat", "completion", "embedding", "moderation"],
                        "geographic_distribution": ["us-east", "eu-west", "ap-south"],
                        "customer_segments": ["enterprise", "mid-market", "startup"]
                        }
                        }
                        )

        # Execute comparative analysis
                        await real_reporting_agent.execute(state, state.run_id, stream_updates=False)

        # Get result from state
                        result = state.report_result

                        assert result["status"] == "success"
                        assert "comparative_analysis" in result

                        analysis = result["comparative_analysis"]
                        assert "month_over_month" in analysis
                        assert "benchmark_comparison" in analysis
                        assert "trend_analysis" in analysis

        # Verify percentage changes calculated
                        mom = analysis["month_over_month"]
                        assert "cost_change_percentage" in mom
                        assert "latency_improvement_percentage" in mom
                        assert "throughput_change_percentage" in mom

        # Check benchmark positioning
                        benchmark = analysis["benchmark_comparison"]
                        assert "performance_rating" in benchmark
                        assert "competitive_position" in benchmark
                        assert "areas_of_excellence" in benchmark
                        assert "improvement_areas" in benchmark

        # Verify visualizations suggested
                        assert "visualization_recommendations" in result
                        vizs = result["visualization_recommendations"]
                        assert any("chart" in v.lower() or "graph" in v.lower() for v in vizs)

                        logger.info(f"Generated comparative analysis with {len(analysis)} comparison dimensions")

                        @pytest.mark.integration
                        @pytest.mark.real_llm
                        async def test_anomaly_detection_and_alerting_report(
                        self, real_reporting_agent, db_session
                        ):
                            """Test 3: Generate anomaly detection and alerting reports using real LLM."""
        # Data with anomalies
                            state = DeepAgentState(
                            run_id="test_report_003",
                            user_query="Analyze anomalies in our AI system over the past week and generate alerts",
                            triage_result={
                            "intent": "anomaly_reporting",
                            "entities": ["anomalies", "alerts", "weekly"],
                            "confidence": 0.89
                            },
                            data_result={
                            "time_series_data": [
                            {"timestamp": "2024-01-15T10:00:00", "requests": 1200, "errors": 2, "latency": 95},
                            {"timestamp": "2024-01-15T11:00:00", "requests": 1250, "errors": 3, "latency": 98},
                            {"timestamp": "2024-01-15T12:00:00", "requests": 450, "errors": 89, "latency": 850},  # Anomaly
                            {"timestamp": "2024-01-15T13:00:00", "requests": 1180, "errors": 2, "latency": 92},
                            {"timestamp": "2024-01-16T03:00:00", "requests": 3500, "errors": 5, "latency": 105},  # Traffic spike
                            {"timestamp": "2024-01-17T15:00:00", "requests": 1300, "errors": 145, "latency": 450},  # Error spike
                            ],
                            "baseline_metrics": {
                            "normal_request_range": [800, 1500],
                            "normal_error_rate": 0.002,
                            "normal_latency_range": [80, 150]
                            },
                            "system_events": [
                            {"timestamp": "2024-01-15T11:45:00", "event": "Database failover initiated"},
                            {"timestamp": "2024-01-16T02:30:00", "event": "New deployment completed"},
                            {"timestamp": "2024-01-17T14:55:00", "event": "Rate limiter configuration changed"}
                            ]
                            }
                            )

        # Execute anomaly detection reporting
                            await real_reporting_agent.execute(state, state.run_id, stream_updates=False)

        # Get result from state
                            result = state.report_result

                            assert result["status"] == "success"
                            assert "anomalies_detected" in result

                            anomalies = result["anomalies_detected"]
                            assert len(anomalies) >= 3  # Should detect the injected anomalies

                            for anomaly in anomalies:
                                assert "timestamp" in anomaly
                                assert "type" in anomaly
                                assert "severity" in anomaly
                                assert "metrics_affected" in anomaly
                                assert "deviation_percentage" in anomaly

        # Verify correlation with events
                                assert "event_correlations" in result
                                correlations = result["event_correlations"]
                                assert len(correlations) > 0

        # Check alert generation
                                assert "alerts_generated" in result
                                alerts = result["alerts_generated"]
                                assert len(alerts) > 0

                                for alert in alerts:
                                    assert "priority" in alert
                                    assert "title" in alert
                                    assert "description" in alert
                                    assert "recommended_action" in alert

        # Verify root cause analysis
                                    assert "root_cause_analysis" in result
                                    rca = result["root_cause_analysis"]
                                    assert len(rca) > 0

                                    logger.info(f"Detected {len(anomalies)} anomalies and generated {len(alerts)} alerts")

                                    @pytest.mark.integration
                                    @pytest.mark.real_llm
                                    async def test_cost_breakdown_and_attribution_report(
                                    self, real_reporting_agent, db_session
                                    ):
                                        """Test 4: Generate detailed cost breakdown and attribution reports using real LLM."""
        # Detailed cost data
                                        state = DeepAgentState(
                                        run_id="test_report_004",
                                        user_query="Generate a detailed cost breakdown report with attribution to teams and projects",
                                        triage_result={
                                        "intent": "cost_reporting",
                                        "entities": ["cost", "breakdown", "attribution"],
                                        "confidence": 0.94
                                        },
                                        data_result={
                                        "total_cost": 125000,
                                        "cost_by_model": {
                                        "gpt-4": 75000,
                                        "gpt-3.5-turbo": 30000,
                                        "claude-2": 15000,
                                        "embeddings": 5000
                                        },
                                        "cost_by_team": {
                                        "product": 45000,
                                        "engineering": 35000,
                                        "customer_support": 25000,
                                        "marketing": 15000,
                                        "research": 5000
                                        },
                                        "cost_by_project": {
                                        "chatbot_v2": 40000,
                                        "search_enhancement": 30000,
                                        "content_generation": 25000,
                                        "data_analysis": 20000,
                                        "testing": 10000
                                        },
                                        "usage_patterns": {
                                        "peak_hours_percentage": 65,
                                        "batch_processing_percentage": 30,
                                        "real_time_percentage": 70,
                                        "cached_requests_percentage": 15
                                        },
                                        "cost_trends": {
                                        "monthly_growth_rate": 0.15,
                                        "projected_next_month": 143750,
                                        "budget_variance": 0.08
                                        }
                                        }
                                        )

        # Execute cost reporting
                                        await real_reporting_agent.execute(state, state.run_id, stream_updates=False)

        # Get result from state
                                        result = state.report_result

                                        assert result["status"] == "success"
                                        assert "cost_breakdown" in result

                                        breakdown = result["cost_breakdown"]
                                    assert "by_model" in breakdown
                                    assert "by_team" in breakdown
                                    assert "by_project" in breakdown

        # Verify attribution analysis
                                    assert "attribution_analysis" in result
                                    attribution = result["attribution_analysis"]
                                    assert "top_consumers" in attribution
                                    assert "cost_efficiency_scores" in attribution

        # Check for optimization opportunities
                                    assert "cost_optimization_opportunities" in result
                                    opportunities = result["cost_optimization_opportunities"]
                                    assert len(opportunities) >= 3

                                    for opp in opportunities:
                                        assert "area" in opp
                                        assert "potential_savings" in opp
                                        assert "implementation_effort" in opp
                                        assert "recommendation" in opp

        # Verify forecasting
                                        assert "cost_forecast" in result
                                        forecast = result["cost_forecast"]
                                        assert "next_month_projection" in forecast
                                        assert "quarterly_projection" in forecast
                                        assert "confidence_interval" in forecast

        # Check for budget alerts
                                        assert "budget_status" in result
                                        budget = result["budget_status"]
                                        assert "current_utilization" in budget
                                        assert "days_until_limit" in budget or "within_budget" in budget

                                        logger.info(f"Generated cost report with {len(opportunities)} optimization opportunities")

                                        @pytest.mark.integration
                                        @pytest.mark.real_llm
                                        async def test_custom_kpi_dashboard_generation(
                                        self, real_reporting_agent, db_session
                                        ):
                                            """Test 5: Generate custom KPI dashboards with real-time metrics using real LLM."""
        # Custom KPI requirements
                                            state = DeepAgentState(
                                            run_id="test_report_005",
                                            user_query="Create a custom KPI dashboard focusing on customer experience metrics and AI quality",
                                            triage_result={
                                            "intent": "dashboard_creation",
                                            "entities": ["KPI", "customer_experience", "quality"],
                                            "confidence": 0.91
                                            },
                                            data_result={
                                            "customer_metrics": {
                                            "satisfaction_score": 4.6,
                                            "response_time_seconds": 1.2,
                                            "resolution_rate": 0.89,
                                            "escalation_rate": 0.11,
                                            "repeat_query_rate": 0.23,
                                            "nps_score": 72
                                            },
                                            "quality_metrics": {
                                            "accuracy_score": 0.94,
                                            "hallucination_rate": 0.002,
                                            "context_relevance": 0.91,
                                            "response_completeness": 0.88,
                                            "factual_correctness": 0.96,
                                            "tone_appropriateness": 0.93
                                            },
                                            "operational_metrics": {
                                            "availability": 0.9987,
                                            "error_rate": 0.0013,
                                            "avg_latency_ms": 125,
                                            "concurrent_users": 5420,
                                            "cache_hit_rate": 0.35
                                            },
                                            "trending_data": {
                                            "satisfaction_trend": "+0.3 pts/month",
                                            "accuracy_trend": "+0.02 pts/month",
                                            "cost_trend": "-5%/month",
                                            "usage_trend": "+18%/month"
                                            },
                                            "user_preferences": {
                                            "refresh_interval": "real-time",
                                            "visualization_types": ["gauge", "line_chart", "heatmap"],
                                            "alert_thresholds": {
                                            "satisfaction": 4.5,
                                            "error_rate": 0.002,
                                            "latency": 200
                                            }
                                            }
                                            }
                                            )

        # Execute dashboard generation
                                            await real_reporting_agent.execute(state, state.run_id, stream_updates=False)

        # Get result from state
                                            result = state.report_result

                                            assert result["status"] == "success"
                                            assert "dashboard_configuration" in result

                                            dashboard = result["dashboard_configuration"]
                                            assert "kpi_widgets" in dashboard
                                            assert "layout" in dashboard
                                            assert "refresh_settings" in dashboard

        # Verify KPI widgets
                                            widgets = dashboard["kpi_widgets"]
                                            assert len(widgets) >= 5

                                            for widget in widgets:
                                                assert "metric_name" in widget
                                                assert "current_value" in widget
                                                assert "target_value" in widget
                                                assert "visualization_type" in widget
                                                assert "status" in widget  # green/yellow/red

        # Check for drill-down capabilities
                                                assert "drill_down_paths" in result
                                                drill_downs = result["drill_down_paths"]
                                                assert len(drill_downs) > 0

        # Verify alert configurations
                                                assert "alert_rules" in result
                                                alerts = result["alert_rules"]
                                                assert len(alerts) >= 3

                                                for alert in alerts:
                                                    assert "metric" in alert
                                                    assert "condition" in alert
                                                    assert "threshold" in alert
                                                    assert "notification_channel" in alert

        # Check for insights and narratives
                                                    assert "kpi_narratives" in result
                                                    narratives = result["kpi_narratives"]
                                                    assert len(narratives) >= 3

        # Verify export capabilities
                                                    assert "export_formats" in result
                                                    assert "pdf" in result["export_formats"]
                                                    assert "csv" in result["export_formats"]

                                                    logger.info(f"Generated dashboard with {len(widgets)} KPI widgets and {len(alerts)} alert rules")


                                                    if __name__ == "__main__":
    # Run tests with real services
                                                        asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))